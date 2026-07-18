from __future__ import annotations

from base64 import urlsafe_b64encode
import json
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import pytest

from aura_gate_oidc import (
    OIDCIdentityVerifier,
    OIDCProviderConfig,
    OIDCVerificationError,
)

NOW = 1_800_000_000.0
ISSUER = "https://issuer.example.test"
AUDIENCE = "aura-gate"
ACTOR_SALT = b"aura-gate-local-test-salt-2026-rotation-key"
DUPLICATE_HEADER = b'{"alg":"RS256","alg":"RS256","kid":"key-1"}'


def _b64url(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _jwk(
    private_key: rsa.RSAPrivateKey,
    *,
    kid: str = "key-1",
    **overrides: Any,
) -> dict[str, Any]:
    public = private_key.public_key().public_numbers()
    value: dict[str, Any] = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "key_ops": ["verify"],
        "n": _b64url(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
        "e": _b64url(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
    }
    value.update(overrides)
    return value


def _claims(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "iss": ISSUER,
        "sub": "upstream-private-subject-42",
        "aud": AUDIENCE,
        "iat": NOW - 30,
        "exp": NOW + 300,
        "nonce": "browser-nonce",
        "roles": ["operator", "reviewer"],
        "groups": ["aura-engineering"],
    }
    value.update(overrides)
    return value


def _token(
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, Any] | None = None,
    *,
    kid: str | None = "key-1",
    alg: str = "RS256",
    header_overrides: dict[str, Any] | None = None,
) -> str:
    header: dict[str, Any] = {"typ": "JWT", "alg": alg}
    if kid is not None:
        header["kid"] = kid
    if header_overrides:
        header.update(header_overrides)
    encoded_header = _b64url(json.dumps(header, sort_keys=True, separators=(",", ":")).encode())
    encoded_claims = _b64url(json.dumps(claims or _claims(), sort_keys=True, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{encoded_header}.{encoded_claims}.{_b64url(signature)}"


def _config(
    keys: list[dict[str, Any]],
    *,
    audiences: tuple[str, ...] = (AUDIENCE,),
    actor_salt: bytes = ACTOR_SALT,
    required_roles: tuple[str, ...] = ("operator",),
    required_groups: tuple[str, ...] = ("aura-engineering",),
    clock_skew_seconds: float = 0.0,
    max_token_age_seconds: float | None = 600.0,
) -> OIDCProviderConfig:
    return OIDCProviderConfig(
        issuer=ISSUER,
        audiences=audiences,
        jwks={"keys": keys},
        actor_salt=actor_salt,
        required_roles=required_roles,
        required_groups=required_groups,
        clock_skew_seconds=clock_skew_seconds,
        max_token_age_seconds=max_token_age_seconds,
    )


@pytest.fixture(scope="module")
def key_one() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def key_two() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_valid_token_emits_only_bounded_pseudonymous_authority(
    key_one: rsa.RSAPrivateKey,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))
    bearer = _token(key_one)

    identity = verifier.verify(bearer, expected_nonce="browser-nonce", now=NOW)
    metadata = identity.to_dict()

    assert identity.actor_ref.startswith("gate-actor:hmac-sha256:")
    assert identity.issuer == ISSUER
    assert identity.audiences == (AUDIENCE,)
    assert identity.roles == ("operator", "reviewer")
    assert identity.groups == ("aura-engineering",)
    assert identity.token_digest.startswith("sha256:")
    assert identity.claims_digest.startswith("sha256:")
    assert metadata["verified_at"] == NOW
    rendered = json.dumps(metadata, sort_keys=True)
    assert bearer not in rendered
    assert "upstream-private-subject-42" not in rendered
    assert "browser-nonce" not in rendered
    assert "sub" not in metadata
    assert "claims" not in metadata


@pytest.mark.parametrize(
    ("alg", "kid", "code"),
    [
        ("none", "key-1", "unsecured_algorithm"),
        ("HS256", "key-1", "unsupported_algorithm"),
        ("RS256", None, "missing_key_id"),
        ("RS256", "unknown", "unknown_key_id"),
    ],
)
def test_algorithm_and_key_id_fail_closed(
    key_one: rsa.RSAPrivateKey,
    alg: str,
    kid: str | None,
    code: str,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError, match=code):
        verifier.verify(_token(key_one, alg=alg, kid=kid), now=NOW)


def test_bad_signature_fails_closed(
    key_one: rsa.RSAPrivateKey,
    key_two: rsa.RSAPrivateKey,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError, match="invalid_signature"):
        verifier.verify(_token(key_two), now=NOW)


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"kty": "EC"}, "jwk_type_mismatch"),
        ({"use": "enc"}, "jwk_use_mismatch"),
        ({"alg": "RS512"}, "jwk_algorithm_mismatch"),
        ({"key_ops": ["sign"]}, "jwk_key_operations_mismatch"),
    ],
)
def test_jwk_metadata_mismatch_fails_closed(
    key_one: rsa.RSAPrivateKey,
    overrides: dict[str, Any],
    code: str,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one, **overrides)]))

    with pytest.raises(OIDCVerificationError, match=code):
        verifier.verify(_token(key_one), now=NOW)


@pytest.mark.parametrize(
    ("claim_overrides", "code"),
    [
        ({"iss": "https://other.example.test"}, "invalid_issuer"),
        ({"aud": "other-gate"}, "invalid_audience"),
        ({"aud": [AUDIENCE, "secondary"]}, "authorized_party_required"),
        ({"aud": [AUDIENCE, "secondary"], "azp": "secondary"}, "invalid_authorized_party"),
        ({"aud": [AUDIENCE, True], "azp": AUDIENCE}, "invalid_audience"),
    ],
)
def test_issuer_audience_and_authorized_party_are_exact(
    key_one: rsa.RSAPrivateKey,
    claim_overrides: dict[str, Any],
    code: str,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError, match=code):
        verifier.verify(_token(key_one, _claims(**claim_overrides)), now=NOW)


def test_multiple_audiences_require_correct_azp(key_one: rsa.RSAPrivateKey) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)], audiences=(AUDIENCE, "secondary")))
    token = _token(key_one, _claims(aud=["secondary", AUDIENCE], azp=AUDIENCE))

    identity = verifier.verify(token, now=NOW)

    assert identity.audiences == (AUDIENCE, "secondary")
    assert identity.authorized_party == AUDIENCE


@pytest.mark.parametrize(
    ("claim_overrides", "code"),
    [
        ({"exp": NOW}, "token_expired"),
        ({"iat": NOW + 1}, "token_issued_in_future"),
        ({"nbf": NOW + 1}, "token_not_active"),
        ({"iat": NOW - 601}, "token_too_old"),
        ({"exp": True}, "invalid_exp"),
        ({"iat": False}, "invalid_iat"),
        ({"nbf": True}, "invalid_nbf"),
        ({"exp": NOW - 10, "iat": NOW}, "invalid_token_lifetime"),
    ],
)
def test_numeric_dates_and_time_window_fail_closed(
    key_one: rsa.RSAPrivateKey,
    claim_overrides: dict[str, Any],
    code: str,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError, match=code):
        verifier.verify(_token(key_one, _claims(**claim_overrides)), now=NOW)


def test_boolean_verification_time_is_not_numeric(key_one: rsa.RSAPrivateKey) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError, match="invalid_verification_time"):
        verifier.verify(_token(key_one), now=True)


@pytest.mark.parametrize(
    ("claims", "expected", "code"),
    [
        (_claims(nonce="actual"), "expected", "nonce_mismatch"),
        (_claims(nonce=True), None, "invalid_nonce"),
        (_claims(nonce="actual"), True, "invalid_expected_nonce"),
    ],
)
def test_nonce_validation_is_strict(
    key_one: rsa.RSAPrivateKey,
    claims: dict[str, Any],
    expected: Any,
    code: str,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError, match=code):
        verifier.verify(_token(key_one, claims), expected_nonce=expected, now=NOW)


@pytest.mark.parametrize(
    ("claim_overrides", "code"),
    [
        ({"roles": ["reviewer"]}, "required_role_missing"),
        ({"groups": []}, "required_group_missing"),
        ({"roles": "operator"}, "invalid_roles"),
        ({"groups": [True]}, "invalid_groups"),
    ],
)
def test_required_roles_and_groups_fail_closed(
    key_one: rsa.RSAPrivateKey,
    claim_overrides: dict[str, Any],
    code: str,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError, match=code):
        verifier.verify(_token(key_one, _claims(**claim_overrides)), now=NOW)


def test_pinned_key_rotation_and_actor_reference_are_deterministic(
    key_one: rsa.RSAPrivateKey,
    key_two: rsa.RSAPrivateKey,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one), _jwk(key_two, kid="key-2")]))
    first = verifier.verify(_token(key_one), now=NOW)
    rotated = verifier.verify(_token(key_two, kid="key-2"), now=NOW + 1)
    other_subject = verifier.verify(_token(key_one, _claims(sub="different-subject")), now=NOW)

    assert first.actor_ref == rotated.actor_ref
    assert first.actor_ref != other_subject.actor_ref
    assert first.key_id == "key-1"
    assert rotated.key_id == "key-2"
    assert first.token_digest != rotated.token_digest


def test_actor_salt_changes_pseudonym(key_one: rsa.RSAPrivateKey) -> None:
    token = _token(key_one)
    first = OIDCIdentityVerifier(_config([_jwk(key_one)])).verify(token, now=NOW)
    second = OIDCIdentityVerifier(
        _config([_jwk(key_one)], actor_salt=b"a-different-local-aura-gate-actor-salt-2026")
    ).verify(token, now=NOW)

    assert first.actor_ref != second.actor_ref


@pytest.mark.parametrize("salt", [b"short", b"x" * 32, True])
def test_nontrivial_local_actor_salt_is_required(
    key_one: rsa.RSAPrivateKey,
    salt: Any,
) -> None:
    with pytest.raises(ValueError, match="actor_salt"):
        _config([_jwk(key_one)], actor_salt=salt)


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jws",
        "a.b.c",
        "!!!!.e30.YQ",
        f"{_b64url(DUPLICATE_HEADER)}.e30.YQ",
    ],
)
def test_compact_jws_base64_and_json_errors_fail_closed(
    key_one: rsa.RSAPrivateKey,
    token: str,
) -> None:
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError):
        verifier.verify(token, now=NOW)


def test_failure_does_not_log_or_leak_token_or_claims(
    key_one: rsa.RSAPrivateKey,
    key_two: rsa.RSAPrivateKey,
    caplog: pytest.LogCaptureFixture,
) -> None:
    private_claims = _claims(sub="sensitive-subject", email="private@example.test")
    bearer = _token(key_two, private_claims)
    verifier = OIDCIdentityVerifier(_config([_jwk(key_one)]))

    with pytest.raises(OIDCVerificationError) as captured:
        verifier.verify(bearer, now=NOW)

    message = str(captured.value)
    assert bearer not in message
    assert "sensitive-subject" not in message
    assert "private@example.test" not in message
    assert not caplog.records
