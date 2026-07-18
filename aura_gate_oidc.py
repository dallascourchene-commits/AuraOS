"""Offline, fail-closed OIDC identity verification for Aura Gate.

Aura Gate deliberately does not perform OIDC discovery or fetch signing keys at
request time.  A deployment supplies an exact issuer, accepted audiences, and a
pinned public JWKS.  Successful verification produces a bounded authority
record: bearer tokens and raw claims never cross this module's public boundary.

This is a minimal ID-token profile.  It supports RS256 only; adding another
algorithm requires an explicit implementation and tests rather than accepting
whatever an untrusted JOSE header requests.
"""

from __future__ import annotations

from base64 import b64decode
from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import re
import time
from types import MappingProxyType
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

OIDC_IDENTITY_VERSION = "AURA_GATE_OIDC_IDENTITY_V1"
_SUPPORTED_ALGORITHM = "RS256"
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_TOKEN_BYTES = 64 * 1024
_MAX_HEADER_BYTES = 8 * 1024
_MAX_CLAIMS_BYTES = 48 * 1024
_MAX_IDENTITY_VALUES = 64
_MAX_IDENTITY_VALUE_BYTES = 256
_PRIVATE_RSA_PARAMETERS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth"})


class OIDCVerificationError(ValueError):
    """A token-independent, safe-to-report OIDC verification failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"OIDC identity verification failed: {code}")


def _fail(code: str) -> None:
    raise OIDCVerificationError(code)


def _require_text(value: Any, *, code: str, max_bytes: int = _MAX_IDENTITY_VALUE_BYTES) -> str:
    if type(value) is not str or not value or value != value.strip():
        _fail(code)
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        _fail(code)
    if len(encoded) > max_bytes:
        _fail(code)
    return value


def _decode_base64url(value: Any, *, code: str, max_bytes: int) -> bytes:
    if type(value) is not str or not value or "=" in value or _B64URL_RE.fullmatch(value) is None:
        _fail(code)
    try:
        decoded = b64decode(value + ("=" * (-len(value) % 4)), altchars=b"-_", validate=True)
    except (ValueError, TypeError):
        _fail(code)
    if not decoded or len(decoded) > max_bytes:
        _fail(code)
    return decoded


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite JSON number")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _decode_json_segment(value: str, *, code: str, max_bytes: int) -> dict[str, Any]:
    encoded = _decode_base64url(value, code=code, max_bytes=max_bytes)
    try:
        decoded = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeError, ValueError, TypeError):
        _fail(code)
    if type(decoded) is not dict:
        _fail(code)
    return decoded


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _config_values(value: Any, *, name: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a list or tuple of strings")
    items = tuple(value)
    if not allow_empty and not items:
        raise ValueError(f"{name} must not be empty")
    if len(items) > _MAX_IDENTITY_VALUES:
        raise ValueError(f"{name} exceeds the configured bound")
    for item in items:
        if type(item) is not str or not item or item != item.strip():
            raise ValueError(f"{name} must contain non-empty strings")
        if len(item.encode("utf-8")) > _MAX_IDENTITY_VALUE_BYTES:
            raise ValueError(f"{name} contains an oversized value")
    if len(items) != len(set(items)):
        raise ValueError(f"{name} cannot contain duplicates")
    return items


@dataclass(frozen=True, slots=True)
class OIDCProviderConfig:
    """Pinned provider material for an offline, single-issuer verifier."""

    issuer: str
    audiences: tuple[str, ...]
    jwks: Mapping[str, Any] = field(repr=False, compare=False, hash=False)
    actor_salt: str | bytes = field(repr=False, compare=False, hash=False)
    required_roles: tuple[str, ...] = ()
    required_groups: tuple[str, ...] = ()
    roles_claim: str = "roles"
    groups_claim: str = "groups"
    clock_skew_seconds: float = 60.0
    max_token_age_seconds: float | None = 3600.0
    jwks_digest: str = field(init=False)
    _keys_by_kid: Mapping[str, Mapping[str, Any]] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.issuer) is not str or not self.issuer or self.issuer != self.issuer.strip():
            raise ValueError("issuer must be a non-empty exact string")
        if len(self.issuer.encode("utf-8")) > 2048:
            raise ValueError("issuer exceeds the configured bound")

        audiences = _config_values(self.audiences, name="audiences")
        roles = _config_values(self.required_roles, name="required_roles", allow_empty=True)
        groups = _config_values(self.required_groups, name="required_groups", allow_empty=True)
        object.__setattr__(self, "audiences", audiences)
        object.__setattr__(self, "required_roles", roles)
        object.__setattr__(self, "required_groups", groups)

        for name in ("roles_claim", "groups_claim"):
            value = getattr(self, name)
            if type(value) is not str or not value or value != value.strip() or len(value) > 128:
                raise ValueError(f"{name} must be a bounded non-empty string")
        if self.roles_claim == self.groups_claim:
            raise ValueError("roles_claim and groups_claim must be distinct")

        if type(self.clock_skew_seconds) not in (int, float) or not math.isfinite(float(self.clock_skew_seconds)):
            raise ValueError("clock_skew_seconds must be a finite number")
        if not 0 <= float(self.clock_skew_seconds) <= 300:
            raise ValueError("clock_skew_seconds must be between zero and 300")
        object.__setattr__(self, "clock_skew_seconds", float(self.clock_skew_seconds))
        max_age = self.max_token_age_seconds
        if max_age is not None:
            if type(max_age) not in (int, float) or not math.isfinite(float(max_age)) or float(max_age) <= 0:
                raise ValueError("max_token_age_seconds must be a positive finite number or None")
            object.__setattr__(self, "max_token_age_seconds", float(max_age))

        salt = self.actor_salt.encode("utf-8") if type(self.actor_salt) is str else self.actor_salt
        if type(salt) is not bytes or len(salt) < 32 or len(set(salt)) < 8:
            raise ValueError("actor_salt must contain at least 32 nontrivial local bytes")
        object.__setattr__(self, "actor_salt", salt)

        if not isinstance(self.jwks, Mapping):
            raise ValueError("jwks must be a mapping")
        try:
            jwks_copy = json.loads(_canonical_json(self.jwks).decode("utf-8"))
        except (TypeError, ValueError, UnicodeError) as exc:
            raise ValueError("jwks must be canonical JSON data") from exc
        if type(jwks_copy) is not dict or type(jwks_copy.get("keys")) is not list or not jwks_copy["keys"]:
            raise ValueError("jwks must contain a non-empty keys array")
        key_index: dict[str, Mapping[str, Any]] = {}
        for key in jwks_copy["keys"]:
            if type(key) is not dict:
                raise ValueError("each jwks key must be a mapping")
            kid = key.get("kid")
            if type(kid) is not str or not kid or kid != kid.strip() or len(kid.encode("utf-8")) > 128:
                raise ValueError("each jwks key must have a bounded non-empty kid")
            if kid in key_index:
                raise ValueError("jwks cannot contain duplicate kid values")
            frozen_key = _freeze_json(key)
            key_index[kid] = frozen_key
        object.__setattr__(self, "jwks", _freeze_json(jwks_copy))
        object.__setattr__(self, "_keys_by_kid", MappingProxyType(key_index))
        object.__setattr__(self, "jwks_digest", _digest(_canonical_json(jwks_copy)))


@dataclass(frozen=True, slots=True)
class VerifiedGateIdentity:
    """Bounded OIDC authority metadata with no bearer token or raw subject."""

    actor_ref: str
    issuer: str
    audiences: tuple[str, ...]
    authorized_party: str | None
    roles: tuple[str, ...]
    groups: tuple[str, ...]
    issued_at: float
    expires_at: float
    not_before: float | None
    verified_at: float
    key_id: str
    token_digest: str
    claims_digest: str
    jwks_digest: str
    version: str = OIDC_IDENTITY_VERSION

    def authority_metadata(self) -> dict[str, Any]:
        """Return the complete safe-to-persist identity authority record."""

        return {
            "version": self.version,
            "actor_ref": self.actor_ref,
            "issuer": self.issuer,
            "audiences": list(self.audiences),
            "authorized_party": self.authorized_party,
            "roles": list(self.roles),
            "groups": list(self.groups),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "not_before": self.not_before,
            "verified_at": self.verified_at,
            "key_id": self.key_id,
            "token_digest": self.token_digest,
            "claims_digest": self.claims_digest,
            "jwks_digest": self.jwks_digest,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.authority_metadata()


class OIDCIdentityVerifier:
    """Verify compact RS256 JWTs using only a pinned :class:`OIDCProviderConfig`."""

    def __init__(self, config: OIDCProviderConfig) -> None:
        if type(config) is not OIDCProviderConfig:
            raise TypeError("config must be an OIDCProviderConfig")
        self._config = config

    def verify(
        self,
        token: str,
        expected_nonce: str | None = None,
        now: float | None = None,
    ) -> VerifiedGateIdentity:
        """Verify one ID token and return pseudonymous, bounded authority data."""

        try:
            return self._verify(token, expected_nonce=expected_nonce, now=now)
        except OIDCVerificationError:
            raise
        except Exception:
            # Library/parser internals must never turn attacker-controlled data
            # into an exception message or traceback chain at this boundary.
            raise OIDCVerificationError("malformed_token") from None

    def _verify(
        self,
        token: str,
        *,
        expected_nonce: str | None,
        now: float | None,
    ) -> VerifiedGateIdentity:
        if type(token) is not str or not token or not token.isascii() or len(token.encode("ascii")) > _MAX_TOKEN_BYTES:
            _fail("malformed_compact_jws")
        if any(character.isspace() for character in token):
            _fail("malformed_compact_jws")
        segments = token.split(".")
        if len(segments) != 3 or not all(segments):
            _fail("malformed_compact_jws")
        encoded_header, encoded_claims, encoded_signature = segments
        header = _decode_json_segment(encoded_header, code="malformed_header", max_bytes=_MAX_HEADER_BYTES)
        claims = _decode_json_segment(encoded_claims, code="malformed_claims", max_bytes=_MAX_CLAIMS_BYTES)

        algorithm = header.get("alg")
        if algorithm == "none":
            _fail("unsecured_algorithm")
        if algorithm != _SUPPORTED_ALGORITHM:
            _fail("unsupported_algorithm")
        kid = _require_text(header.get("kid"), code="missing_key_id", max_bytes=128)
        if "crit" in header or "b64" in header or any(name in header for name in ("jku", "jwk", "x5u", "x5c")):
            _fail("unsupported_header")
        if "typ" in header and header["typ"] != "JWT":
            _fail("unsupported_header")

        jwk = self._config._keys_by_kid.get(kid)
        if jwk is None:
            _fail("unknown_key_id")
        public_key = self._rsa_public_key(jwk)
        signature = _decode_base64url(encoded_signature, code="malformed_signature", max_bytes=16 * 1024)
        try:
            public_key.verify(
                signature,
                f"{encoded_header}.{encoded_claims}".encode("ascii"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except InvalidSignature:
            _fail("invalid_signature")
        except (TypeError, ValueError):
            _fail("invalid_signature")

        verified_at = time.time() if now is None else now
        if type(verified_at) not in (int, float) or not math.isfinite(float(verified_at)) or float(verified_at) < 0:
            _fail("invalid_verification_time")
        verified_at = float(verified_at)

        issuer = _require_text(claims.get("iss"), code="invalid_issuer", max_bytes=2048)
        if not hmac.compare_digest(issuer.encode("utf-8"), self._config.issuer.encode("utf-8")):
            _fail("invalid_issuer")
        audiences, authorized_party = self._validate_audience(claims)
        subject = _require_text(claims.get("sub"), code="invalid_subject")
        issued_at = self._numeric_date(claims, "iat", required=True)
        expires_at = self._numeric_date(claims, "exp", required=True)
        not_before = self._numeric_date(claims, "nbf", required=False)
        self._validate_times(
            issued_at=issued_at,
            expires_at=expires_at,
            not_before=not_before,
            now=verified_at,
        )
        self._validate_nonce(claims, expected_nonce)
        roles = self._claim_values(claims, self._config.roles_claim, code="invalid_roles")
        groups = self._claim_values(claims, self._config.groups_claim, code="invalid_groups")
        if not set(self._config.required_roles).issubset(roles):
            _fail("required_role_missing")
        if not set(self._config.required_groups).issubset(groups):
            _fail("required_group_missing")

        actor_basis = _canonical_json({"iss": issuer, "sub": subject})
        actor_ref = (
            "gate-actor:hmac-sha256:"
            + hmac.new(
                self._config.actor_salt,
                actor_basis,
                hashlib.sha256,
            ).hexdigest()
        )
        return VerifiedGateIdentity(
            actor_ref=actor_ref,
            issuer=issuer,
            audiences=audiences,
            authorized_party=authorized_party,
            roles=roles,
            groups=groups,
            issued_at=issued_at,
            expires_at=expires_at,
            not_before=not_before,
            verified_at=verified_at,
            key_id=kid,
            token_digest=_digest(token.encode("ascii")),
            claims_digest=_digest(_canonical_json(claims)),
            jwks_digest=self._config.jwks_digest,
        )

    @staticmethod
    def _rsa_public_key(jwk: Mapping[str, Any]) -> rsa.RSAPublicKey:
        if jwk.get("kty") != "RSA":
            _fail("jwk_type_mismatch")
        if "use" in jwk and jwk["use"] != "sig":
            _fail("jwk_use_mismatch")
        if "alg" in jwk and jwk["alg"] != _SUPPORTED_ALGORITHM:
            _fail("jwk_algorithm_mismatch")
        if _PRIVATE_RSA_PARAMETERS.intersection(jwk):
            _fail("jwk_private_material")
        if "key_ops" in jwk:
            key_ops = jwk["key_ops"]
            if type(key_ops) not in (list, tuple) or tuple(key_ops) != ("verify",):
                _fail("jwk_key_operations_mismatch")
        modulus_bytes = _decode_base64url(jwk.get("n"), code="invalid_jwk", max_bytes=2048)
        exponent_bytes = _decode_base64url(jwk.get("e"), code="invalid_jwk", max_bytes=8)
        modulus = int.from_bytes(modulus_bytes, "big")
        exponent = int.from_bytes(exponent_bytes, "big")
        if modulus.bit_length() < 2048 or exponent < 3 or exponent % 2 == 0 or exponent > 0xFFFFFFFF:
            _fail("invalid_jwk")
        try:
            return rsa.RSAPublicNumbers(exponent, modulus).public_key()
        except ValueError:
            _fail("invalid_jwk")

    def _validate_audience(self, claims: Mapping[str, Any]) -> tuple[tuple[str, ...], str | None]:
        raw = claims.get("aud")
        if type(raw) is str:
            audience_values = (raw,)
        elif type(raw) is list:
            audience_values = tuple(raw)
        else:
            _fail("invalid_audience")
        if not audience_values or len(audience_values) > 16:
            _fail("invalid_audience")
        audiences = tuple(_require_text(item, code="invalid_audience") for item in audience_values)
        if len(audiences) != len(set(audiences)):
            _fail("invalid_audience")
        accepted = set(audiences).intersection(self._config.audiences)
        if not accepted:
            _fail("invalid_audience")

        raw_azp = claims.get("azp")
        authorized_party: str | None = None
        if raw_azp is not None:
            authorized_party = _require_text(raw_azp, code="invalid_authorized_party")
            if authorized_party not in audiences or authorized_party not in self._config.audiences:
                _fail("invalid_authorized_party")
        if len(audiences) > 1 and authorized_party is None:
            _fail("authorized_party_required")
        if len(audiences) == 1 and authorized_party is not None and authorized_party != audiences[0]:
            _fail("invalid_authorized_party")
        return tuple(sorted(audiences)), authorized_party

    @staticmethod
    def _numeric_date(claims: Mapping[str, Any], name: str, *, required: bool) -> float | None:
        value = claims.get(name)
        if value is None and not required:
            return None
        if type(value) not in (int, float) or not math.isfinite(float(value)) or float(value) < 0:
            _fail(f"invalid_{name}")
        return float(value)

    def _validate_times(
        self,
        *,
        issued_at: float | None,
        expires_at: float | None,
        not_before: float | None,
        now: float,
    ) -> None:
        if issued_at is None or expires_at is None or expires_at <= issued_at:
            _fail("invalid_token_lifetime")
        skew = self._config.clock_skew_seconds
        if now >= expires_at + skew:
            _fail("token_expired")
        if issued_at > now + skew:
            _fail("token_issued_in_future")
        if not_before is not None and now + skew < not_before:
            _fail("token_not_active")
        max_age = self._config.max_token_age_seconds
        if max_age is not None and now - issued_at > max_age + skew:
            _fail("token_too_old")

    @staticmethod
    def _validate_nonce(claims: Mapping[str, Any], expected_nonce: str | None) -> None:
        actual_nonce = claims.get("nonce")
        if actual_nonce is not None:
            _require_text(actual_nonce, code="invalid_nonce", max_bytes=512)
        if expected_nonce is None:
            return
        expected = _require_text(expected_nonce, code="invalid_expected_nonce", max_bytes=512)
        if actual_nonce is None or not hmac.compare_digest(actual_nonce.encode("utf-8"), expected.encode("utf-8")):
            _fail("nonce_mismatch")

    @staticmethod
    def _claim_values(claims: Mapping[str, Any], name: str, *, code: str) -> tuple[str, ...]:
        raw = claims.get(name, [])
        if type(raw) is not list or len(raw) > _MAX_IDENTITY_VALUES:
            _fail(code)
        values = tuple(_require_text(item, code=code) for item in raw)
        if len(values) != len(set(values)):
            _fail(code)
        return tuple(sorted(values))


__all__ = [
    "OIDC_IDENTITY_VERSION",
    "OIDCIdentityVerifier",
    "OIDCProviderConfig",
    "OIDCVerificationError",
    "VerifiedGateIdentity",
]
