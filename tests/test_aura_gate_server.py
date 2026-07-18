from __future__ import annotations

from base64 import urlsafe_b64encode
import http.client
import json
from pathlib import Path
import threading
import time
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import pytest

from aura_gate import GatePolicyManifest, gate_purpose_digest
from aura_gate_oidc import OIDCIdentityVerifier, OIDCProviderConfig, VerifiedGateIdentity
from aura_gate_server import (
    A2A_MEDIA_TYPE,
    A2A_VERSION,
    AGENT_CARD_PATH,
    HEALTH_PATH,
    MESSAGE_SEND_PATH,
    AuraGateHTTPServer,
    GateServerConfigError,
    create_private_server,
    load_server_config,
)

ISSUER = "https://issuer.example.test"
AUDIENCE = "aura-gate"
ACTOR_SALT = b"aura-gate-server-local-test-salt-2026-key"


def _b64url(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _jwk(private_key: rsa.RSAPrivateKey, *, kid: str = "server-key") -> dict[str, Any]:
    public = private_key.public_key().public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "key_ops": ["verify"],
        "n": _b64url(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
    }


def _token(
    private_key: rsa.RSAPrivateKey,
    *,
    subject: str = "private-upstream-subject",
    expires_offset: int = 300,
) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "kid": "server-key", "typ": "JWT"}
    claims = {
        "iss": ISSUER,
        "sub": subject,
        "aud": AUDIENCE,
        "iat": now - 10,
        "exp": now + expires_offset,
        "roles": ["operator"],
        "groups": ["aura-engineering"],
    }
    encoded_header = _b64url(json.dumps(header, sort_keys=True, separators=(",", ":")).encode())
    encoded_claims = _b64url(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{encoded_header}.{encoded_claims}.{_b64url(signature)}"


class FakeProtocolError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__("adapter detail must not cross HTTP boundary")


class FakeAdapter:
    def __init__(self) -> None:
        self.card_calls = 0
        self.a2a_calls: list[dict[str, Any]] = []
        self.error_code = ""

    def agent_card(self) -> dict[str, Any]:
        self.card_calls += 1
        return {
            "name": "Aura Gate",
            "url": "http://127.0.0.1/message:send",
            "protocolVersion": A2A_VERSION,
        }

    def handle_a2a(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        identity: VerifiedGateIdentity,
        protocol_version: str,
    ) -> dict[str, Any]:
        if self.error_code:
            raise FakeProtocolError(self.error_code)
        self.a2a_calls.append(
            {
                "method": method,
                "payload": payload,
                "identity": identity,
                "protocol_version": protocol_version,
            }
        )
        return {
            "id": "task-1",
            "status": {"state": "submitted"},
            "transport_actor_ref": identity.actor_ref,
        }


@pytest.fixture(scope="module")
def signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def running_server(signing_key: rsa.RSAPrivateKey):
    config = OIDCProviderConfig(
        issuer=ISSUER,
        audiences=(AUDIENCE,),
        jwks={"keys": [_jwk(signing_key)]},
        actor_salt=ACTOR_SALT,
        required_roles=("operator",),
        required_groups=("aura-engineering",),
        clock_skew_seconds=0,
        max_token_age_seconds=600,
    )
    adapter = FakeAdapter()
    server = create_private_server(
        adapter,
        OIDCIdentityVerifier(config),
        host="127.0.0.1",
        port=0,
        max_body_bytes=512,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, adapter
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(
    server: AuraGateHTTPServer,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    raw = response.read()
    result = response.status, {name.lower(): value for name, value in response.getheaders()}, json.loads(raw)
    connection.close()
    return result


def _auth_headers(signing_key: rsa.RSAPrivateKey, **extra: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token(signing_key)}",
        "A2A-Version": A2A_VERSION,
        **extra,
    }


def _message() -> dict[str, Any]:
    return {
        "messageId": "message-1",
        "role": "user",
        "parts": [{"kind": "text", "text": "Prepare the bounded Gate task"}],
    }


def _assert_a2a_error(value: dict[str, Any], code: str) -> None:
    assert value["message"] == code
    assert value["status"] in {
        "ALREADY_EXISTS",
        "INTERNAL",
        "INVALID_ARGUMENT",
        "NOT_FOUND",
        "PERMISSION_DENIED",
        "RESOURCE_EXHAUSTED",
        "UNAUTHENTICATED",
        "UNAVAILABLE",
        "UNIMPLEMENTED",
    }
    assert type(value["code"]) is int
    assert value["details"] == [
        {
            "@type": "type.googleapis.com/google.rpc.ErrorInfo",
            "reason": code.upper(),
            "domain": "aura-gate",
        }
    ]


def test_health_is_the_only_anonymous_route(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
) -> None:
    server, adapter = running_server

    status, headers, body = _request(server, "GET", HEALTH_PATH)
    assert status == 200
    assert body == {"ok": True, "service": "aura-gate", "version": "AURA_GATE_PRIVATE_HTTP_V1"}
    assert headers["cache-control"] == "no-store"

    status, headers, body = _request(
        server,
        "GET",
        AGENT_CARD_PATH,
        headers={"A2A-Version": A2A_VERSION},
    )
    assert status == 401
    assert body == {"error": {"code": "unauthorized"}}
    assert headers["www-authenticate"] == 'Bearer realm="aura-gate"'
    assert adapter.card_calls == 0


def test_authenticated_agent_card_requires_exact_version(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
) -> None:
    server, adapter = running_server
    authorization = {"Authorization": f"Bearer {_token(signing_key)}"}

    missing_status, _, missing = _request(server, "GET", AGENT_CARD_PATH, headers=authorization)
    wrong_status, _, wrong = _request(
        server,
        "GET",
        AGENT_CARD_PATH,
        headers={**authorization, "A2A-Version": "0.3"},
    )
    status, headers, card = _request(server, "GET", AGENT_CARD_PATH, headers=_auth_headers(signing_key))

    assert missing_status == 400
    assert missing == {"error": {"code": "invalid_headers"}}
    assert wrong_status == 400
    assert wrong == {"error": {"code": "unsupported_a2a_version"}}
    assert status == 200
    assert card["protocolVersion"] == A2A_VERSION
    assert headers["content-type"] == "application/json"
    assert adapter.card_calls == 1


def test_valid_a2a_dispatch_uses_only_transport_identity(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
) -> None:
    server, adapter = running_server
    payload = _message()
    headers = _auth_headers(signing_key, **{"Content-Type": A2A_MEDIA_TYPE})

    status, response_headers, result = _request(
        server,
        "POST",
        MESSAGE_SEND_PATH,
        body=json.dumps(payload).encode(),
        headers=headers,
    )

    assert status == 200
    assert response_headers["content-type"] == A2A_MEDIA_TYPE
    assert result["task"]["transport_actor_ref"].startswith("gate-actor:hmac-sha256:")
    assert len(adapter.a2a_calls) == 1
    call = adapter.a2a_calls[0]
    assert call["method"] == "message/send"
    assert call["payload"] == payload
    assert call["protocol_version"] == A2A_VERSION
    assert isinstance(call["identity"], VerifiedGateIdentity)


def test_task_status_and_cancel_use_a2a_v1_http_routes(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
) -> None:
    server, adapter = running_server
    headers = _auth_headers(signing_key)

    get_status, get_headers, get_result = _request(
        server,
        "GET",
        "/tasks/GATE-run-1?historyLength=0",
        headers=headers,
    )
    cancel_status, cancel_headers, cancel_result = _request(
        server,
        "POST",
        "/tasks/GATE-run-1:cancel",
        headers=headers,
    )

    assert get_status == 200
    assert cancel_status == 200
    assert get_headers["content-type"] == A2A_MEDIA_TYPE
    assert cancel_headers["content-type"] == A2A_MEDIA_TYPE
    assert get_result["task"]["id"] == "task-1"
    assert cancel_result["task"]["id"] == "task-1"
    assert adapter.a2a_calls[0]["method"] == "tasks/get"
    assert adapter.a2a_calls[0]["payload"] == {
        "id": "GATE-run-1",
        "historyLength": 0,
    }
    assert adapter.a2a_calls[1]["method"] == "tasks/cancel"
    assert adapter.a2a_calls[1]["payload"] == {"id": "GATE-run-1"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/tasks/GATE-run-1?historyLength=1"),
        ("GET", "/tasks/GATE-run-1?unknown=0"),
        ("POST", "/tasks/GATE-run-1:cancel?tenant=spoofed"),
        ("DELETE", "/tasks/GATE-run-1"),
    ],
)
def test_task_routes_reject_unsupported_shapes(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
    method: str,
    path: str,
) -> None:
    server, adapter = running_server

    status, _, _body = _request(
        server,
        method,
        path,
        headers=_auth_headers(signing_key),
    )

    assert status in {400, 405}
    assert adapter.a2a_calls == []


def test_oidc_verification_happens_before_body_dispatch(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
) -> None:
    server, adapter = running_server
    headers = {
        "Authorization": "Bearer not.a.valid-token",
        "A2A-Version": A2A_VERSION,
        "Content-Type": A2A_MEDIA_TYPE,
    }

    status, _, body = _request(server, "POST", MESSAGE_SEND_PATH, body=b"not-json", headers=headers)

    assert status == 401
    _assert_a2a_error(body, "unauthorized")
    assert not adapter.a2a_calls


@pytest.mark.parametrize(
    ("header_overrides", "body", "status", "code"),
    [
        ({"A2A-Version": "0.3", "Content-Type": A2A_MEDIA_TYPE}, b"{}", 400, "unsupported_a2a_version"),
        ({"A2A-Version": A2A_VERSION, "Content-Type": "application/json"}, b"{}", 415, "unsupported_media_type"),
        ({"A2A-Version": A2A_VERSION, "Content-Type": A2A_MEDIA_TYPE}, b"not-json", 400, "invalid_json"),
        ({"A2A-Version": A2A_VERSION, "Content-Type": A2A_MEDIA_TYPE}, b"[]", 400, "invalid_json"),
        (
            {"A2A-Version": A2A_VERSION, "Content-Type": A2A_MEDIA_TYPE},
            b'{"messageId":"one","messageId":"two"}',
            400,
            "invalid_json",
        ),
        ({"A2A-Version": A2A_VERSION, "Content-Type": A2A_MEDIA_TYPE}, b'{"score":NaN}', 400, "invalid_json"),
        ({"A2A-Version": A2A_VERSION, "Content-Type": A2A_MEDIA_TYPE}, b'{"score":1e9999}', 400, "invalid_json"),
    ],
)
def test_version_content_type_and_json_are_exact(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
    header_overrides: dict[str, str],
    body: bytes,
    status: int,
    code: str,
) -> None:
    server, adapter = running_server
    headers = {"Authorization": f"Bearer {_token(signing_key)}", **header_overrides}

    actual_status, _, response = _request(server, "POST", MESSAGE_SEND_PATH, body=body, headers=headers)

    assert actual_status == status
    _assert_a2a_error(response, code)
    assert not adapter.a2a_calls


@pytest.mark.parametrize(
    "spoof",
    [
        {"identity": {"actor_ref": "attacker"}},
        {"metadata": {"transportIdentity": "attacker"}},
        {"parts": [{"authorization": "Bearer attacker-token"}]},
        {"oidcToken": "attacker-token"},
    ],
)
def test_body_cannot_spoof_transport_identity_or_token(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
    spoof: dict[str, Any],
) -> None:
    server, adapter = running_server
    payload = {**_message(), **spoof}

    status, _, result = _request(
        server,
        "POST",
        MESSAGE_SEND_PATH,
        body=json.dumps(payload).encode(),
        headers=_auth_headers(signing_key, **{"Content-Type": A2A_MEDIA_TYPE}),
    )

    assert status == 400
    _assert_a2a_error(result, "identity_in_body")
    assert not adapter.a2a_calls


@pytest.mark.parametrize(
    "path",
    [
        "/forge",
        "/arena",
        "/architect",
        "/stage",
        "/verify",
        "/model",
        "/mcp",
        "/mcp/v1/tools/call",
    ],
)
def test_raw_internal_and_legacy_routes_are_not_found(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
    path: str,
) -> None:
    server, adapter = running_server

    status, _, body = _request(server, "GET", path, headers=_auth_headers(signing_key))

    assert status == 404
    assert body == {"error": {"code": "not_found"}}
    assert adapter.card_calls == 0
    assert not adapter.a2a_calls


def test_body_and_header_bounds_fail_before_dispatch(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
) -> None:
    server, adapter = running_server
    headers = _auth_headers(
        signing_key,
        **{"Content-Type": A2A_MEDIA_TYPE, "Content-Length": "513"},
    )
    status, _, body = _request(server, "POST", MESSAGE_SEND_PATH, headers=headers)
    assert status == 413
    _assert_a2a_error(body, "body_too_large")

    status, _, body = _request(
        server,
        "GET",
        AGENT_CARD_PATH,
        headers={**_auth_headers(signing_key), "X-Oversized": "x" * 16_000},
    )
    assert status == 431
    assert body == {"error": {"code": "headers_too_large"}}
    assert adapter.card_calls == 0
    assert not adapter.a2a_calls


def test_content_length_is_required_and_unambiguous(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
) -> None:
    server, adapter = running_server
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    connection.putrequest("POST", MESSAGE_SEND_PATH)
    for name, value in _auth_headers(signing_key, **{"Content-Type": A2A_MEDIA_TYPE}).items():
        connection.putheader(name, value)
    connection.endheaders(b"{}")
    response = connection.getresponse()
    body = json.loads(response.read())
    connection.close()

    assert response.status == 411
    _assert_a2a_error(body, "content_length_required")
    assert not adapter.a2a_calls


def test_adapter_bounded_error_has_safe_status_mapping(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    signing_key: rsa.RSAPrivateKey,
) -> None:
    server, adapter = running_server
    adapter.error_code = "purpose_not_allowed"

    status, _, body = _request(
        server,
        "POST",
        MESSAGE_SEND_PATH,
        body=json.dumps(_message()).encode(),
        headers=_auth_headers(signing_key, **{"Content-Type": A2A_MEDIA_TYPE}),
    )

    assert status == 403
    _assert_a2a_error(body, "purpose_not_allowed")


def test_security_and_cache_headers_are_consistent(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
) -> None:
    server, _adapter = running_server

    _, headers, _ = _request(server, "GET", HEALTH_PATH)

    assert headers["cache-control"] == "no-store"
    assert headers["pragma"] == "no-cache"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["content-security-policy"] == "default-src 'none'"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["cross-origin-resource-policy"] == "same-origin"
    assert headers["connection"] == "close"


def test_server_never_logs_or_echoes_token_and_body(
    running_server: tuple[AuraGateHTTPServer, FakeAdapter],
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    server, adapter = running_server
    secret_token = "not-a-valid.private.secret-token"
    secret_body = b'{"message":"private-body-value"}'

    status, _, body = _request(
        server,
        "POST",
        MESSAGE_SEND_PATH,
        body=secret_body,
        headers={
            "Authorization": f"Bearer {secret_token}",
            "A2A-Version": A2A_VERSION,
            "Content-Type": A2A_MEDIA_TYPE,
        },
    )

    captured = capsys.readouterr()
    rendered = json.dumps(body)
    assert status == 401
    assert secret_token not in rendered + captured.out + captured.err
    assert "private-body-value" not in rendered + captured.out + captured.err
    assert not caplog.records
    assert not adapter.a2a_calls


def _policy(name: str = "private-gate") -> GatePolicyManifest:
    objective = "Prepare a bounded private Aura Gate task"
    return GatePolicyManifest.create(
        name=name,
        allowed_purpose_digests=(gate_purpose_digest(objective),),
        allowed_capabilities=("FORGE.PREPARE",),
        allowed_files=("aura_gate.py",),
        allowed_destinations=("a2a://review-agent",),
        allowed_providers=("local",),
        allowed_models=("model-a",),
        allowed_data_classes=("PUBLIC",),
        allowed_egress_fields=("message",),
        allowed_retention_classes=("EPHEMERAL",),
        allowed_protocols=("A2A",),
        required_verifiers=("canonical_arena_verifier", "hotswap_readiness"),
        required_roles=("operator",),
        required_groups=("aura-engineering",),
    )


def _configuration_files(
    tmp_path: Path,
    signing_key: rsa.RSAPrivateKey,
) -> tuple[dict[str, str], Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "Aura_Staging").mkdir()
    state = tmp_path / "state"
    audit = tmp_path / "audit"
    siem = tmp_path / "siem"
    state.mkdir()
    audit.mkdir()
    siem.mkdir()
    policy_file = tmp_path / "policy.json"
    oidc_file = tmp_path / "oidc.json"
    jwks_file = tmp_path / "jwks.json"
    salt_file = tmp_path / "actor-salt.bin"
    policy_file.write_text(json.dumps(_policy().to_dict()), encoding="utf-8")
    oidc_file.write_text(
        json.dumps(
            {
                "issuer": ISSUER,
                "audiences": [AUDIENCE],
                "required_roles": ["operator"],
                "required_groups": ["aura-engineering"],
                "clock_skew_seconds": 30,
                "max_token_age_seconds": 600,
            }
        ),
        encoding="utf-8",
    )
    jwks_file.write_text(json.dumps({"keys": [_jwk(signing_key)]}), encoding="utf-8")
    salt_file.write_bytes(ACTOR_SALT)
    environ = {
        "AURA_GATE_REPO_ROOT": str(repo),
        "AURA_GATE_POLICY_FILE": str(policy_file),
        "AURA_GATE_OIDC_FILE": str(oidc_file),
        "AURA_GATE_JWKS_FILE": str(jwks_file),
        "AURA_GATE_ACTOR_SALT_FILE": str(salt_file),
        "AURA_GATE_STATE_ROOT": str(state),
        "AURA_GATE_AUDIT_ROOT": str(audit),
        "AURA_GATE_SIEM_ROOT": str(siem),
        "AURA_GATE_HOST": "127.0.0.1",
        "AURA_GATE_PORT": "8765",
    }
    return environ, policy_file, oidc_file


def test_loader_requires_and_resolves_all_local_configuration(
    tmp_path: Path,
    signing_key: rsa.RSAPrivateKey,
) -> None:
    environ, _policy_file, _oidc_file = _configuration_files(tmp_path, signing_key)

    config = load_server_config(environ)

    assert config.repo_root == Path(environ["AURA_GATE_REPO_ROOT"]).resolve()
    assert config.host == "127.0.0.1"
    assert config.port == 8765
    assert len(config.policies) == 1
    assert config.oidc_provider.issuer == ISSUER
    assert config.oidc_provider.audiences == (AUDIENCE,)


def test_loader_never_defaults_missing_credentials_or_paths() -> None:
    with pytest.raises(GateServerConfigError, match="missing_configuration"):
        load_server_config({})


@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "::", "8.8.8.8", "10.0.0.5", "192.168.1.5", "fd00::1", "example.com"],
)
def test_loader_refuses_public_or_ambiguous_bind(
    tmp_path: Path,
    signing_key: rsa.RSAPrivateKey,
    host: str,
) -> None:
    environ, _policy_file, _oidc_file = _configuration_files(tmp_path, signing_key)
    environ["AURA_GATE_HOST"] = host

    with pytest.raises(GateServerConfigError, match="host_not_private"):
        load_server_config(environ)


def test_loader_rejects_discovery_or_remote_jwks_configuration(
    tmp_path: Path,
    signing_key: rsa.RSAPrivateKey,
) -> None:
    environ, _policy_file, oidc_file = _configuration_files(tmp_path, signing_key)
    oidc_file.write_text(
        json.dumps(
            {
                "issuer": ISSUER,
                "audiences": [AUDIENCE],
                "discovery_url": "https://issuer.example.test/.well-known/openid-configuration",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(GateServerConfigError, match="oidc_config_invalid"):
        load_server_config(environ)


def test_loader_requires_explicit_selection_for_multiple_policies(
    tmp_path: Path,
    signing_key: rsa.RSAPrivateKey,
) -> None:
    environ, policy_file, _oidc_file = _configuration_files(tmp_path, signing_key)
    first = _policy("first")
    second = _policy("second")
    policy_file.write_text(
        json.dumps({"policies": [first.to_dict(), second.to_dict()]}),
        encoding="utf-8",
    )

    with pytest.raises(GateServerConfigError, match="policy_config_invalid"):
        load_server_config(environ)

    environ["AURA_GATE_POLICY_ID"] = second.policy_id
    selected = load_server_config(environ)
    assert selected.policies == (second,)


def test_direct_server_factory_refuses_public_bind(
    signing_key: rsa.RSAPrivateKey,
) -> None:
    verifier = OIDCIdentityVerifier(
        OIDCProviderConfig(
            issuer=ISSUER,
            audiences=(AUDIENCE,),
            jwks={"keys": [_jwk(signing_key)]},
            actor_salt=ACTOR_SALT,
        )
    )

    with pytest.raises(GateServerConfigError, match="host_not_private"):
        create_private_server(FakeAdapter(), verifier, host="0.0.0.0", port=8765)
