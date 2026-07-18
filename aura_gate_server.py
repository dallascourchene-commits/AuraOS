"""Private stdlib HTTP boundary for Aura Gate's A2A protocol adapter.

Only a fixed health route, an authenticated Agent Card route, and authenticated
A2A message/task routes are exposed.  Identity always comes
from a verified transport bearer token; request bodies cannot supply or replace
it.  The server performs no OIDC discovery and never fetches signing keys.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import sys
from typing import Any, Protocol
from urllib.parse import parse_qs, urlsplit

from aura_gate import GatePolicyManifest
from aura_gate_oidc import OIDCIdentityVerifier, OIDCProviderConfig, VerifiedGateIdentity

GATE_HTTP_VERSION = "AURA_GATE_PRIVATE_HTTP_V1"
A2A_VERSION = "1.0"
A2A_MEDIA_TYPE = "application/a2a+json"
HEALTH_PATH = "/health"
AGENT_CARD_PATH = "/.well-known/agent-card.json"
MESSAGE_SEND_PATH = "/message:send"
_TASK_ROUTE_RE = re.compile(r"^/tasks/(?P<task_id>[A-Za-z0-9][A-Za-z0-9._-]{0,255})(?P<cancel>:cancel)?$")

_MAX_HEADER_BYTES = 16 * 1024
_MAX_HEADER_COUNT = 64
_MAX_AUTHORIZATION_BYTES = 12 * 1024
_DEFAULT_MAX_BODY_BYTES = 1024 * 1024
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_CONFIG_FILE_BYTES = 4 * 1024 * 1024
_MAX_CONFIG_TEXT_BYTES = 4096
_SAFE_PROTOCOL_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_IDENTITY_SPOOF_KEYS = frozenset(
    {
        "access_token",
        "actor_ref",
        "authorization",
        "bearer_token",
        "identity",
        "id_token",
        "oidc_token",
        "transport_identity",
        "verified_identity",
    }
)
_REQUIRED_ENV = {
    "repo_root": "AURA_GATE_REPO_ROOT",
    "policy_file": "AURA_GATE_POLICY_FILE",
    "oidc_file": "AURA_GATE_OIDC_FILE",
    "jwks_file": "AURA_GATE_JWKS_FILE",
    "actor_salt_file": "AURA_GATE_ACTOR_SALT_FILE",
    "state_root": "AURA_GATE_STATE_ROOT",
    "audit_root": "AURA_GATE_AUDIT_ROOT",
    "siem_root": "AURA_GATE_SIEM_ROOT",
    "host": "AURA_GATE_HOST",
    "port": "AURA_GATE_PORT",
}


class _ProtocolAdapter(Protocol):
    def agent_card(self) -> dict[str, Any]: ...

    def handle_a2a(
        self,
        method: str,
        payload: Mapping[str, Any],
        *,
        identity: VerifiedGateIdentity,
        protocol_version: str,
    ) -> dict[str, Any]: ...


class GateServerConfigError(ValueError):
    """A bounded configuration failure that does not disclose file contents."""

    _CODES = frozenset(
        {
            "actor_salt_invalid",
            "audit_root_invalid",
            "config_file_invalid",
            "host_not_private",
            "jwks_invalid",
            "missing_configuration",
            "oidc_config_invalid",
            "policy_config_invalid",
            "port_invalid",
            "repo_root_invalid",
            "siem_root_invalid",
            "staging_root_invalid",
            "state_root_invalid",
        }
    )

    def __init__(self, code: str) -> None:
        bounded = code if code in self._CODES else "config_file_invalid"
        self.code = bounded
        super().__init__(f"Aura Gate server configuration denied: {bounded}")


def _config_fail(code: str) -> None:
    raise GateServerConfigError(code)


def _normalized_key(value: str) -> str:
    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    return re.sub(r"[^a-z0-9]+", "_", camel_split.lower()).strip("_")


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite number")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _strict_json_object(value: bytes, *, config: bool = False) -> dict[str, Any]:
    try:
        decoded = json.loads(
            value.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError, RecursionError):
        if config:
            _config_fail("config_file_invalid")
        raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_json") from None
    if type(decoded) is not dict:
        if config:
            _config_fail("config_file_invalid")
        raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_json")
    nodes = 0

    def validate(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > 20_000 or depth > 32:
            raise ValueError("JSON structure exceeds boundary")
        if item is None or type(item) in (bool, int, str):
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError("non-finite JSON number")
            return
        if type(item) is list:
            for nested in item:
                validate(nested, depth + 1)
            return
        if type(item) is dict:
            for nested in item.values():
                validate(nested, depth + 1)
            return
        raise ValueError("unsupported JSON value")

    try:
        validate(decoded, 0)
    except (ValueError, RecursionError):
        if config:
            _config_fail("config_file_invalid")
        raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_json") from None
    return decoded


def _json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise _RequestDenied(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error") from None
    if len(encoded) > _MAX_RESPONSE_BYTES:
        raise _RequestDenied(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error")
    return encoded


def _contains_identity_spoof(value: Any) -> bool:
    if type(value) is dict:
        for key, nested in value.items():
            if _normalized_key(key) in _IDENTITY_SPOOF_KEYS or _contains_identity_spoof(nested):
                return True
    elif type(value) is list:
        return any(_contains_identity_spoof(item) for item in value)
    return False


def _is_private_host(host: str) -> bool:
    if type(host) is not str or not host or host != host.strip():
        return False
    try:
        if len(host.encode("utf-8")) > 255:
            return False
    except UnicodeError:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if address.is_unspecified or address.is_multicast:
        return False
    # This proof carries bearer credentials over a stdlib HTTP socket and has
    # no TLS terminator.  "Private" therefore means single-node loopback only,
    # not a cleartext RFC1918/ULA LAN bind.  A future reverse-proxy profile must
    # make trusted-proxy and TLS authority explicit before widening this rule.
    return address.is_loopback


def _required_path(value: str, *, code: str, directory: bool) -> Path:
    if type(value) is not str or not value or value != value.strip():
        _config_fail(code)
    try:
        encoded_size = len(value.encode("utf-8"))
    except UnicodeError:
        _config_fail(code)
    if encoded_size > _MAX_CONFIG_TEXT_BYTES or "\x00" in value:
        _config_fail(code)
    try:
        resolved = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        _config_fail(code)
    if directory and not resolved.is_dir():
        _config_fail(code)
    if not directory and not resolved.is_file():
        _config_fail(code)
    return resolved


def _read_bounded(path: Path, *, code: str) -> bytes:
    try:
        size = path.stat().st_size
        if not 0 < size <= _MAX_CONFIG_FILE_BYTES:
            _config_fail(code)
        value = path.read_bytes()
    except OSError:
        _config_fail(code)
    if not value or len(value) != size:
        _config_fail(code)
    return value


def _load_json_file(path: Path, *, code: str) -> dict[str, Any]:
    value = _read_bounded(path, code=code)
    try:
        return _strict_json_object(value, config=True)
    except GateServerConfigError:
        _config_fail(code)


@dataclass(frozen=True, slots=True)
class AuraGateServerConfig:
    """Resolved private deployment inputs with pinned identity material."""

    repo_root: Path
    policy_file: Path
    oidc_file: Path
    jwks_file: Path
    actor_salt_file: Path = field(repr=False)
    state_root: Path
    audit_root: Path
    siem_root: Path
    host: str
    port: int
    policies: tuple[GatePolicyManifest, ...]
    oidc_provider: OIDCProviderConfig = field(repr=False)
    max_body_bytes: int = _DEFAULT_MAX_BODY_BYTES
    version: str = GATE_HTTP_VERSION

    def __post_init__(self) -> None:
        if not _is_private_host(self.host):
            _config_fail("host_not_private")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            _config_fail("port_invalid")
        if type(self.max_body_bytes) is not int or not 1 <= self.max_body_bytes <= 16 * 1024 * 1024:
            _config_fail("config_file_invalid")
        if not self.policies or any(type(policy) is not GatePolicyManifest for policy in self.policies):
            _config_fail("policy_config_invalid")
        if len({policy.policy_id for policy in self.policies}) != len(self.policies):
            _config_fail("policy_config_invalid")
        if type(self.oidc_provider) is not OIDCProviderConfig or self.version != GATE_HTTP_VERSION:
            _config_fail("oidc_config_invalid")


def load_server_config(environ: Mapping[str, str] | None = None) -> AuraGateServerConfig:
    """Load exact local deployment files; no discovery or network fetch occurs."""

    source = os.environ if environ is None else environ
    if not isinstance(source, Mapping):
        _config_fail("missing_configuration")
    raw: dict[str, str] = {}
    for name, environment_name in _REQUIRED_ENV.items():
        value = source.get(environment_name)
        if type(value) is not str or not value or value != value.strip():
            _config_fail("missing_configuration")
        raw[name] = value

    repo_root = _required_path(raw["repo_root"], code="repo_root_invalid", directory=True)
    if not (repo_root / ".git").exists():
        _config_fail("repo_root_invalid")
    staging_root = repo_root / "Aura_Staging"
    if not staging_root.is_dir() or not os.access(staging_root, os.W_OK):
        _config_fail("staging_root_invalid")
    policy_file = _required_path(raw["policy_file"], code="policy_config_invalid", directory=False)
    oidc_file = _required_path(raw["oidc_file"], code="oidc_config_invalid", directory=False)
    jwks_file = _required_path(raw["jwks_file"], code="jwks_invalid", directory=False)
    salt_file = _required_path(raw["actor_salt_file"], code="actor_salt_invalid", directory=False)
    state_root = _required_path(raw["state_root"], code="state_root_invalid", directory=True)
    audit_root = _required_path(raw["audit_root"], code="audit_root_invalid", directory=True)
    siem_root = _required_path(raw["siem_root"], code="siem_root_invalid", directory=True)
    if len({state_root, audit_root, siem_root}) != 3:
        _config_fail("audit_root_invalid")

    policy_document = _load_json_file(policy_file, code="policy_config_invalid")
    raw_policies: Any
    if set(policy_document) == {"policies"}:
        raw_policies = policy_document["policies"]
        if type(raw_policies) is not list:
            _config_fail("policy_config_invalid")
    else:
        raw_policies = [policy_document]
    try:
        policies = tuple(GatePolicyManifest.from_mapping(value) for value in raw_policies)
    except (ValueError, TypeError, KeyError):
        _config_fail("policy_config_invalid")
    if not policies:
        _config_fail("policy_config_invalid")
    selected_policy_id = source.get("AURA_GATE_POLICY_ID")
    if selected_policy_id is not None:
        if (
            type(selected_policy_id) is not str
            or not selected_policy_id
            or selected_policy_id != selected_policy_id.strip()
        ):
            _config_fail("policy_config_invalid")
        policies = tuple(policy for policy in policies if policy.policy_id == selected_policy_id)
        if len(policies) != 1:
            _config_fail("policy_config_invalid")
    elif len(policies) != 1:
        _config_fail("policy_config_invalid")

    oidc_document = _load_json_file(oidc_file, code="oidc_config_invalid")
    required_oidc = {"issuer", "audiences"}
    optional_oidc = {
        "clock_skew_seconds",
        "groups_claim",
        "max_token_age_seconds",
        "required_groups",
        "required_roles",
        "roles_claim",
    }
    if not required_oidc.issubset(oidc_document) or not set(oidc_document).issubset(required_oidc | optional_oidc):
        _config_fail("oidc_config_invalid")
    for list_field in ("audiences", "required_roles", "required_groups"):
        if list_field in oidc_document and type(oidc_document[list_field]) is not list:
            _config_fail("oidc_config_invalid")
    jwks_document = _load_json_file(jwks_file, code="jwks_invalid")
    actor_salt = _read_bounded(salt_file, code="actor_salt_invalid")
    try:
        oidc_provider = OIDCProviderConfig(
            issuer=oidc_document["issuer"],
            audiences=tuple(oidc_document["audiences"]),
            jwks=jwks_document,
            actor_salt=actor_salt,
            required_roles=tuple(oidc_document.get("required_roles", ())),
            required_groups=tuple(oidc_document.get("required_groups", ())),
            roles_claim=oidc_document.get("roles_claim", "roles"),
            groups_claim=oidc_document.get("groups_claim", "groups"),
            clock_skew_seconds=oidc_document.get("clock_skew_seconds", 60.0),
            max_token_age_seconds=oidc_document.get("max_token_age_seconds", 3600.0),
        )
    except (ValueError, TypeError, KeyError):
        _config_fail("oidc_config_invalid")

    if len(raw["port"]) > 5 or not raw["port"].isascii() or not raw["port"].isdigit():
        _config_fail("port_invalid")
    port = int(raw["port"])
    return AuraGateServerConfig(
        repo_root=repo_root,
        policy_file=policy_file,
        oidc_file=oidc_file,
        jwks_file=jwks_file,
        actor_salt_file=salt_file,
        state_root=state_root,
        audit_root=audit_root,
        siem_root=siem_root,
        host=raw["host"],
        port=port,
        policies=policies,
        oidc_provider=oidc_provider,
    )


class _RequestDenied(Exception):
    def __init__(self, status: HTTPStatus, code: str) -> None:
        self.status = status
        self.code = code
        super().__init__(code)


class AuraGateHTTPServer(ThreadingHTTPServer):
    """A private, dependency-injected Aura Gate HTTP server."""

    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False

    def __init__(
        self,
        server_address: tuple[str, int],
        adapter: _ProtocolAdapter,
        identity_verifier: OIDCIdentityVerifier,
        *,
        max_body_bytes: int = _DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        host, port = server_address
        if not _is_private_host(host):
            _config_fail("host_not_private")
        if type(port) is not int or not 0 <= port <= 65535:
            _config_fail("port_invalid")
        if not callable(getattr(adapter, "agent_card", None)) or not callable(getattr(adapter, "handle_a2a", None)):
            raise TypeError("adapter does not implement the Aura Gate protocol surface")
        if type(identity_verifier) is not OIDCIdentityVerifier:
            raise TypeError("identity_verifier must be an OIDCIdentityVerifier")
        if type(max_body_bytes) is not int or not 1 <= max_body_bytes <= 16 * 1024 * 1024:
            _config_fail("config_file_invalid")
        self.adapter = adapter
        self.identity_verifier = identity_verifier
        self.max_body_bytes = max_body_bytes
        self.address_family = (
            socket.AF_INET6 if isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address) else socket.AF_INET
        )
        super().__init__(server_address, AuraGateRequestHandler)

    def get_request(self) -> tuple[socket.socket, Any]:
        connection, address = super().get_request()
        connection.settimeout(5.0)
        return connection, address

    def handle_error(self, _request: Any, _client_address: Any) -> None:
        # socketserver's default traceback can expose request-processing state.
        # HTTP responses and the canonical Gate audit ledger are the only
        # reporting surfaces for this boundary.
        return


class AuraGateRequestHandler(BaseHTTPRequestHandler):
    """Fixed-route request handler that never logs bearer or request data."""

    protocol_version = "HTTP/1.1"
    server_version = "AuraGate"
    sys_version = ""

    @property
    def gate_server(self) -> AuraGateHTTPServer:
        return self.server  # type: ignore[return-value]

    def version_string(self) -> str:
        return "AuraGate"

    def log_message(self, _format: str, *args: Any) -> None:
        # BaseHTTPRequestHandler logs request targets.  Aura Gate's canonical
        # audit trail lives behind the adapter, never in HTTP access logs.
        return

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        # Header parsing can fail before do_GET/do_POST.  Replace stdlib's HTML
        # error body with the same deterministic, no-store JSON boundary.
        del message, explain
        try:
            status = HTTPStatus(code)
        except ValueError:
            status = HTTPStatus.BAD_REQUEST
        safe_code = {
            HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE: "headers_too_large",
            HTTPStatus.REQUEST_URI_TOO_LONG: "request_target_too_large",
            HTTPStatus.HTTP_VERSION_NOT_SUPPORTED: "unsupported_http_version",
        }.get(status, "bad_request")
        self._send_error(status, safe_code)

    def handle_expect_100(self) -> bool:
        # Do not invite a client to transmit a body before transport identity,
        # framing, and protocol headers have been checked by the normal path.
        self._request_body_consumed = True
        self._send_error(HTTPStatus.EXPECTATION_FAILED, "expectation_not_supported")
        return False

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._handle("PUT")

    def do_PATCH(self) -> None:
        self._handle("PATCH")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    def do_HEAD(self) -> None:
        self._handle("HEAD")

    def do_OPTIONS(self) -> None:
        self._handle("OPTIONS")

    def _handle(self, method: str) -> None:
        self._request_body_consumed = False
        self._a2a_request = False
        try:
            self._validate_header_bounds()
            target = urlsplit(self.path)
            if target.scheme or target.netloc or target.fragment or not target.path.startswith("/"):
                raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_request_target")
            path = target.path
            query = target.query
            self._a2a_request = bool(path == MESSAGE_SEND_PATH or _TASK_ROUTE_RE.fullmatch(path))
            if method == "GET" and path == HEALTH_PATH and not query:
                self._require_no_request_body()
                self._send_json(
                    HTTPStatus.OK,
                    {"ok": True, "service": "aura-gate", "version": GATE_HTTP_VERSION},
                    media_type="application/json",
                )
                return

            identity = self._authenticate()
            if method == "GET" and path == AGENT_CARD_PATH and not query:
                self._require_a2a_version()
                self._require_no_request_body()
                card = self.gate_server.adapter.agent_card()
                if type(card) is not dict:
                    raise _RequestDenied(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error")
                self._send_json(HTTPStatus.OK, card, media_type="application/json")
                return
            if method == "POST" and path == MESSAGE_SEND_PATH and not query:
                version = self._require_a2a_version()
                self._require_content_type()
                message = self._read_json_body()
                if _contains_identity_spoof(message):
                    raise _RequestDenied(HTTPStatus.BAD_REQUEST, "identity_in_body")
                result = self.gate_server.adapter.handle_a2a(
                    "message/send",
                    message,
                    identity=identity,
                    protocol_version=version,
                )
                if type(result) is not dict:
                    raise _RequestDenied(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error")
                self._send_json(
                    HTTPStatus.OK,
                    {"task": result},
                    media_type=A2A_MEDIA_TYPE,
                )
                return
            task_route = _TASK_ROUTE_RE.fullmatch(path)
            if task_route is not None:
                task_id = task_route.group("task_id")
                cancel = task_route.group("cancel") is not None
                version = self._require_a2a_version()
                if method == "GET" and not cancel:
                    self._require_no_request_body()
                    payload: dict[str, Any] = {"id": task_id}
                    if query:
                        try:
                            parameters = parse_qs(
                                query,
                                keep_blank_values=True,
                                strict_parsing=True,
                                max_num_fields=1,
                            )
                        except ValueError:
                            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_query") from None
                        if set(parameters) != {"historyLength"} or len(parameters["historyLength"]) != 1:
                            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_query")
                        history = parameters["historyLength"][0]
                        if not history.isascii() or not history.isdigit() or len(history) > 3:
                            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_query")
                        if int(history) != 0:
                            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_query")
                        payload["historyLength"] = 0
                    result = self.gate_server.adapter.handle_a2a(
                        "tasks/get",
                        payload,
                        identity=identity,
                        protocol_version=version,
                    )
                elif method == "POST" and cancel and not query:
                    self._require_no_request_body()
                    result = self.gate_server.adapter.handle_a2a(
                        "tasks/cancel",
                        {"id": task_id},
                        identity=identity,
                        protocol_version=version,
                    )
                else:
                    raise _RequestDenied(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")
                if type(result) is not dict:
                    raise _RequestDenied(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error")
                self._send_json(
                    HTTPStatus.OK,
                    {"task": result},
                    media_type=A2A_MEDIA_TYPE,
                )
                return
            if path in {AGENT_CARD_PATH, MESSAGE_SEND_PATH, HEALTH_PATH}:
                raise _RequestDenied(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed")
            raise _RequestDenied(HTTPStatus.NOT_FOUND, "not_found")
        except _RequestDenied as denied:
            self._send_error(denied.status, denied.code)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if type(code) is str and _SAFE_PROTOCOL_CODE_RE.fullmatch(code) is not None:
                raw_status = getattr(exc, "http_status", None)
                allowed_statuses = {400, 401, 403, 404, 409, 413, 415, 422, 429, 500, 503}
                status = HTTPStatus(raw_status) if type(raw_status) is int and raw_status in allowed_statuses else None
                self._send_error(status or self._protocol_status(code), code)
            else:
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error")

    @staticmethod
    def _protocol_status(code: str) -> HTTPStatus:
        if code.endswith(("_not_found", "_missing")):
            return HTTPStatus.NOT_FOUND
        if code.endswith(("_forbidden", "_not_allowed", "_expired", "_revoked")):
            return HTTPStatus.FORBIDDEN
        if code.endswith(("_conflict", "_replay", "_already_used")):
            return HTTPStatus.CONFLICT
        if code.endswith(("_too_large", "_budget_exceeded")):
            return HTTPStatus.UNPROCESSABLE_ENTITY
        return HTTPStatus.BAD_REQUEST

    def _validate_header_bounds(self) -> None:
        raw_headers = getattr(self.headers, "_headers", ())
        if len(raw_headers) > _MAX_HEADER_COUNT:
            raise _RequestDenied(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "headers_too_large")
        total = 0
        for name, value in raw_headers:
            try:
                total += len(name.encode("ascii")) + len(value.encode("latin-1")) + 4
            except UnicodeError:
                raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_headers") from None
        if total > _MAX_HEADER_BYTES:
            raise _RequestDenied(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "headers_too_large")

    def _one_header(self, name: str, *, required: bool) -> str | None:
        values = self.headers.get_all(name, failobj=[])
        if len(values) > 1 or (required and len(values) != 1):
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_headers")
        return values[0] if values else None

    def _authenticate(self) -> VerifiedGateIdentity:
        values = self.headers.get_all("Authorization", failobj=[])
        if len(values) != 1:
            raise _RequestDenied(HTTPStatus.UNAUTHORIZED, "unauthorized")
        value = values[0]
        if type(value) is not str or len(value.encode("latin-1")) > _MAX_AUTHORIZATION_BYTES:
            raise _RequestDenied(HTTPStatus.UNAUTHORIZED, "unauthorized")
        if not value.startswith("Bearer ") or value.count(" ") != 1:
            raise _RequestDenied(HTTPStatus.UNAUTHORIZED, "unauthorized")
        token = value[7:]
        if not token or token != token.strip():
            raise _RequestDenied(HTTPStatus.UNAUTHORIZED, "unauthorized")
        try:
            return self.gate_server.identity_verifier.verify(token)
        except Exception:
            raise _RequestDenied(HTTPStatus.UNAUTHORIZED, "unauthorized") from None

    def _require_a2a_version(self) -> str:
        version = self._one_header("A2A-Version", required=True)
        if version != A2A_VERSION:
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "unsupported_a2a_version")
        return version

    def _require_content_type(self) -> None:
        content_type = self._one_header("Content-Type", required=True)
        if content_type != A2A_MEDIA_TYPE:
            raise _RequestDenied(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "unsupported_media_type")
        if self.headers.get("Content-Encoding") is not None:
            raise _RequestDenied(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "unsupported_content_encoding")

    def _require_no_request_body(self) -> None:
        if self.headers.get("Transfer-Encoding") is not None:
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_content_length")
        content_length = self._one_header("Content-Length", required=False)
        if content_length is not None and content_length != "0":
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "unexpected_request_body")
        self._request_body_consumed = True

    def _read_json_body(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding") is not None:
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_content_length")
        content_lengths = self.headers.get_all("Content-Length", failobj=[])
        if not content_lengths:
            raise _RequestDenied(HTTPStatus.LENGTH_REQUIRED, "content_length_required")
        if len(content_lengths) != 1:
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_content_length")
        raw_length = content_lengths[0]
        if len(raw_length) > 20 or not raw_length.isascii() or not raw_length.isdigit():
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_content_length")
        length = int(raw_length)
        if length <= 0:
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "invalid_content_length")
        if length > self.gate_server.max_body_bytes:
            raise _RequestDenied(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_too_large")
        try:
            body = self.rfile.read(length)
        except (OSError, TimeoutError):
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "content_length_mismatch") from None
        self._request_body_consumed = True
        if len(body) != length:
            raise _RequestDenied(HTTPStatus.BAD_REQUEST, "content_length_mismatch")
        return _strict_json_object(body)

    def _send_error(self, status: HTTPStatus, code: str) -> None:
        self._discard_bounded_request_body()
        headers: dict[str, str] = {}
        if status == HTTPStatus.UNAUTHORIZED:
            headers["WWW-Authenticate"] = 'Bearer realm="aura-gate"'
        if getattr(self, "_a2a_request", False):
            rpc_code, rpc_status = {
                HTTPStatus.BAD_REQUEST: (3, "INVALID_ARGUMENT"),
                HTTPStatus.UNAUTHORIZED: (16, "UNAUTHENTICATED"),
                HTTPStatus.FORBIDDEN: (7, "PERMISSION_DENIED"),
                HTTPStatus.NOT_FOUND: (5, "NOT_FOUND"),
                HTTPStatus.METHOD_NOT_ALLOWED: (12, "UNIMPLEMENTED"),
                HTTPStatus.CONFLICT: (6, "ALREADY_EXISTS"),
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE: (3, "INVALID_ARGUMENT"),
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE: (3, "INVALID_ARGUMENT"),
                HTTPStatus.UNPROCESSABLE_ENTITY: (3, "INVALID_ARGUMENT"),
                HTTPStatus.TOO_MANY_REQUESTS: (8, "RESOURCE_EXHAUSTED"),
                HTTPStatus.SERVICE_UNAVAILABLE: (14, "UNAVAILABLE"),
            }.get(status, (13, "INTERNAL"))
            payload = {
                "code": rpc_code,
                "message": code,
                "status": rpc_status,
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                        "reason": code.upper(),
                        "domain": "aura-gate",
                    }
                ],
            }
            self._send_json(
                status,
                payload,
                media_type=A2A_MEDIA_TYPE,
                extra_headers=headers,
            )
            return
        self._send_json(
            status,
            {"error": {"code": code}},
            media_type="application/json",
            extra_headers=headers,
        )

    def _discard_bounded_request_body(self) -> None:
        """Drain a small framed body so Windows can deliver an early error response."""

        if getattr(self, "_request_body_consumed", False):
            return
        self._request_body_consumed = True
        try:
            if self.headers.get("Transfer-Encoding") is not None:
                return
            lengths = self.headers.get_all("Content-Length", failobj=[])
            if len(lengths) != 1:
                # A client may already have sent a small unframed body. Drain
                # the bytes currently available so Windows does not replace
                # the deterministic 411/400 response with a TCP reset.
                original_timeout = self.connection.gettimeout()
                self.connection.settimeout(0.05)
                try:
                    self.rfile.read1(self.gate_server.max_body_bytes + 1)
                except (OSError, TimeoutError):
                    pass
                finally:
                    self.connection.settimeout(original_timeout)
                return
            raw = lengths[0]
            if not raw.isascii() or not raw.isdigit() or len(raw) > 20:
                return
            remaining = int(raw)
            if remaining <= 0 or remaining > self.gate_server.max_body_bytes:
                return
            original_timeout = self.connection.gettimeout()
            self.connection.settimeout(0.5)
            try:
                while remaining:
                    chunk = self.rfile.read(min(remaining, 64 * 1024))
                    if not chunk:
                        return
                    remaining -= len(chunk)
            finally:
                self.connection.settimeout(original_timeout)
        except (AttributeError, OSError, TimeoutError, ValueError):
            return

    def _send_json(
        self,
        status: HTTPStatus,
        value: Any,
        *,
        media_type: str,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        try:
            body = _json_bytes(value)
        except _RequestDenied:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
            body = b'{"error":{"code":"internal_error"}}'
            media_type = "application/json"
        self.send_response(int(status))
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Connection", "close")
        if extra_headers:
            for name, header_value in extra_headers.items():
                self.send_header(name, header_value)
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return


def create_private_server(
    adapter: _ProtocolAdapter,
    identity_verifier: OIDCIdentityVerifier,
    *,
    host: str,
    port: int,
    max_body_bytes: int = _DEFAULT_MAX_BODY_BYTES,
) -> AuraGateHTTPServer:
    """Create, but do not start, one dependency-injected private server."""

    return AuraGateHTTPServer(
        (host, port),
        adapter,
        identity_verifier,
        max_body_bytes=max_body_bytes,
    )


def create_configured_server(
    config: AuraGateServerConfig,
    adapter: _ProtocolAdapter,
) -> AuraGateHTTPServer:
    """Bind loaded deployment identity material to an injected Gate adapter."""

    if type(config) is not AuraGateServerConfig:
        raise TypeError("config must be an AuraGateServerConfig")
    return create_private_server(
        adapter,
        OIDCIdentityVerifier(config.oidc_provider),
        host=config.host,
        port=config.port,
        max_body_bytes=config.max_body_bytes,
    )


def serve_configured(config: AuraGateServerConfig, adapter: _ProtocolAdapter) -> None:
    """Run the private boundary until its process receives a shutdown signal."""

    with create_configured_server(config, adapter) as server:
        server.serve_forever(poll_interval=0.25)


def create_standalone_server(config: AuraGateServerConfig) -> AuraGateHTTPServer:
    """Assemble canonical Gate owners for the standalone private deployment."""

    if type(config) is not AuraGateServerConfig:
        raise TypeError("config must be an AuraGateServerConfig")
    from aura_forge import AuraForgeRuntime
    from aura_gate import AuraGateRuntime, GateLeaseStore
    from aura_gate_adapters import AuraGateProtocolAdapter
    from aura_gate_audit import GateAuditLedger

    forge = AuraForgeRuntime(config.repo_root)
    lease_store = GateLeaseStore(config.state_root / "aura_gate_leases.sqlite3")
    audit = GateAuditLedger(config.audit_root, export_root=config.siem_root)
    runtime = AuraGateRuntime(
        forge=forge,
        policies=config.policies,
        lease_store=lease_store,
        audit=audit,
    )
    endpoint_host = f"[{config.host}]" if ":" in config.host else config.host
    adapter = AuraGateProtocolAdapter(
        runtime,
        a2a_endpoint_url=f"http://{endpoint_host}:{config.port}",
    )
    return create_configured_server(config, adapter)


def main() -> int:
    """Load only explicit local configuration and serve the private boundary."""

    try:
        config = load_server_config()
        with create_standalone_server(config) as server:
            server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        return 0
    except GateServerConfigError as exc:
        sys.stderr.write(f"Aura Gate server did not start: {exc.code}\n")
        return 2
    except Exception:
        # Startup internals can contain file paths or provider material.  Keep
        # this CLI boundary deliberately generic; operators use local logs and
        # explicit diagnostics rather than an exception dump with secrets.
        sys.stderr.write("Aura Gate server did not start: startup_failed\n")
        return 1
    return 0


__all__ = [
    "A2A_MEDIA_TYPE",
    "A2A_VERSION",
    "AGENT_CARD_PATH",
    "GATE_HTTP_VERSION",
    "HEALTH_PATH",
    "MESSAGE_SEND_PATH",
    "AuraGateHTTPServer",
    "AuraGateServerConfig",
    "GateServerConfigError",
    "create_configured_server",
    "create_private_server",
    "create_standalone_server",
    "load_server_config",
    "main",
    "serve_configured",
]


if __name__ == "__main__":
    raise SystemExit(main())
