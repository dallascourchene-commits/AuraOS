"""Content-addressed, transport-agnostic federation envelopes for Model Cognome.

This module performs no network I/O. It validates allowlists, expiry, replay
nonces, payload digests, authority invariants, and optional external signatures.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping, MutableSet

from aura_model_cognome import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, canonical_json, stable_digest, stable_id

FEDERATION_VERSION = "AURA_MODEL_COGNOME_FEDERATION_V1"
Signer = Callable[[bytes], str]
Verifier = Callable[[bytes, str, str], bool]


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")
    return value


def _finite(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _identity_basis(*, sender_id: str, recipient_scope: str, nonce: str, payload_digest: str, created_at: float, expires_at: float) -> dict[str, Any]:
    return {
        "sender_id": sender_id,
        "recipient_scope": recipient_scope,
        "nonce": nonce,
        "payload_digest": payload_digest,
        "created_at": created_at,
        "expires_at": expires_at,
    }


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class FederationEnvelope:
    envelope_id: str
    sender_id: str
    recipient_scope: str
    nonce: str
    payload_digest: str
    payload: dict[str, Any]
    created_at: float
    expires_at: float
    signature: str
    signature_scheme: str
    version: str = FEDERATION_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    runtime_authority: bool = False
    automatic_import: bool = False

    def __post_init__(self) -> None:
        for name in ("envelope_id", "sender_id", "recipient_scope", "nonce", "payload_digest"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.version != FEDERATION_VERSION:
            raise ValueError("unsupported federation envelope version")
        if not str(self.signature_scheme).strip():
            raise ValueError("signature_scheme must not be empty")
        _finite(self.created_at, "created_at")
        _finite(self.expires_at, "expires_at")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be greater than created_at")
        _strict_bool(self.vsa_patch_authority, "vsa_patch_authority")
        _strict_bool(self.runtime_authority, "runtime_authority")
        _strict_bool(self.automatic_import, "automatic_import")
        expected_id = stable_id("federation-envelope", _identity_basis(
            sender_id=self.sender_id,
            recipient_scope=self.recipient_scope,
            nonce=self.nonce,
            payload_digest=self.payload_digest,
            created_at=self.created_at,
            expires_at=self.expires_at,
        ))
        if self.envelope_id != expected_id:
            raise ValueError("federation envelope ID mismatch")
        if stable_digest(self.payload) != self.payload_digest:
            raise ValueError("federation payload digest mismatch")
        if (
            self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority
            or self.runtime_authority
            or self.automatic_import
        ):
            raise ValueError("federation envelopes cannot carry runtime or patch authority")
        if self.signature_scheme == "UNSIGNED_LOCAL" and self.signature:
            raise ValueError("UNSIGNED_LOCAL envelopes cannot carry a signature")
        if self.signature_scheme != "UNSIGNED_LOCAL" and not self.signature:
            raise ValueError("signed federation envelopes require a signature")

    def signing_payload(self) -> bytes:
        value = {
            "version": self.version,
            "sender_id": self.sender_id,
            "recipient_scope": self.recipient_scope,
            "nonce": self.nonce,
            "payload_digest": self.payload_digest,
            "signature_scheme": self.signature_scheme,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "runtime_authority": self.runtime_authority,
            "automatic_import": self.automatic_import,
        }
        return canonical_json(value).encode("utf-8")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["envelope_digest"] = stable_digest(data)
        return data

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FederationEnvelope":
        packet = cls(
            envelope_id=str(value.get("envelope_id") or ""),
            sender_id=str(value.get("sender_id") or ""),
            recipient_scope=str(value.get("recipient_scope") or ""),
            nonce=str(value.get("nonce") or ""),
            payload_digest=str(value.get("payload_digest") or ""),
            payload=dict(value.get("payload") or {}),
            created_at=float(value.get("created_at") if value.get("created_at") is not None else 0.0),
            expires_at=float(value.get("expires_at") if value.get("expires_at") is not None else 0.0),
            signature=str(value.get("signature") or ""),
            signature_scheme=str(value.get("signature_scheme") or "UNSIGNED_LOCAL"),
            version=str(value.get("version") or FEDERATION_VERSION),
            patch_authority=str(value.get("patch_authority") or PATCH_AUTHORITY),
            vsa_patch_authority=_strict_bool(value.get("vsa_patch_authority", False), "vsa_patch_authority"),
            runtime_authority=_strict_bool(value.get("runtime_authority", False), "runtime_authority"),
            automatic_import=_strict_bool(value.get("automatic_import", False), "automatic_import"),
        )
        supplied_digest = str(value.get("envelope_digest") or "")
        if supplied_digest and supplied_digest != stable_digest(asdict(packet)):
            raise ValueError("federation envelope digest mismatch")
        return packet


def create_federation_envelope(
    payload: Mapping[str, Any],
    *,
    sender_id: str,
    recipient_scope: str,
    nonce: str,
    ttl_seconds: float = 3600.0,
    signer: Signer | None = None,
    signature_scheme: str = "EXTERNAL",
    allow_unsigned_local: bool = False,
    created_at: float | None = None,
) -> FederationEnvelope:
    if not sender_id or not recipient_scope or not nonce:
        raise ValueError("sender_id, recipient_scope, and nonce must not be empty")
    ttl = _finite(ttl_seconds, "ttl_seconds")
    if ttl <= 0:
        raise ValueError("ttl_seconds must be positive")
    clean = json.loads(canonical_json(dict(payload)))
    if clean.get("patch_authority") not in (None, PATCH_AUTHORITY):
        raise ValueError("federated payload patch authority is invalid")
    if clean.get("vsa_patch_authority") not in (None, False):
        raise ValueError("federated payload VSA authority is invalid")
    now = _finite(time.time() if created_at is None else created_at, "created_at")
    digest = stable_digest(clean)
    scheme = "UNSIGNED_LOCAL" if signer is None else str(signature_scheme)
    if signer is not None and scheme == "UNSIGNED_LOCAL":
        raise ValueError("signed envelopes cannot use UNSIGNED_LOCAL")
    basis = _identity_basis(
        sender_id=sender_id,
        recipient_scope=recipient_scope,
        nonce=nonce,
        payload_digest=digest,
        created_at=now,
        expires_at=now + ttl,
    )
    provisional = FederationEnvelope(
        envelope_id=stable_id("federation-envelope", basis),
        sender_id=sender_id,
        recipient_scope=recipient_scope,
        nonce=nonce,
        payload_digest=digest,
        payload=clean,
        created_at=now,
        expires_at=now + ttl,
        signature="" if signer is None else "PENDING_SIGNATURE",
        signature_scheme=scheme,
    )
    if signer is None:
        if not allow_unsigned_local:
            raise ValueError("a signer is required unless allow_unsigned_local is explicit")
        return provisional
    signature = str(signer(provisional.signing_payload()))
    if not signature:
        raise ValueError("signer returned an empty signature")
    return FederationEnvelope(**{**asdict(provisional), "signature": signature})


def validate_federation_envelope(
    envelope: FederationEnvelope | Mapping[str, Any],
    *,
    allowed_senders: Iterable[str],
    expected_recipient_scope: str,
    seen_nonces: MutableSet[str] | None = None,
    verifier: Verifier | None = None,
    allow_unsigned_local: bool = False,
    now: float | None = None,
) -> dict[str, Any]:
    try:
        packet = (
            envelope
            if isinstance(envelope, FederationEnvelope)
            else FederationEnvelope.from_mapping(envelope)
        )
    except (TypeError, ValueError) as exc:
        message = str(exc)
        code = "payload_digest_mismatch" if "payload digest" in message else "envelope_invalid"
        result = {
            "ok": False,
            "errors": [code],
            "error_detail": message,
            "proposal_only": True,
            "automatic_import": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        result["validation_digest"] = stable_digest(result)
        return result
    errors: list[str] = []
    allowed = {str(item) for item in allowed_senders}
    if packet.sender_id not in allowed:
        errors.append("sender_not_allowlisted")
    if packet.recipient_scope != expected_recipient_scope:
        errors.append("recipient_scope_mismatch")
    try:
        timestamp = _finite(time.time() if now is None else now, "validation time")
    except (TypeError, ValueError):
        errors.append("validation_time_invalid")
        timestamp = packet.created_at
    if "validation_time_invalid" not in errors and timestamp < packet.created_at:
        errors.append("envelope_not_yet_valid")
    if "validation_time_invalid" not in errors and timestamp >= packet.expires_at:
        errors.append("envelope_expired")
    if seen_nonces is not None and packet.nonce in seen_nonces:
        errors.append("replayed_nonce")
    if stable_digest(packet.payload) != packet.payload_digest:
        errors.append("payload_digest_mismatch")
    if packet.signature_scheme == "UNSIGNED_LOCAL":
        if not allow_unsigned_local:
            errors.append("unsigned_envelope_denied")
    elif verifier is None:
        errors.append("signature_verifier_missing")
    elif not verifier(packet.signing_payload(), packet.signature, packet.sender_id):
        errors.append("signature_invalid")
    valid = not errors
    if valid and seen_nonces is not None:
        seen_nonces.add(packet.nonce)
    result = {
        "ok": valid,
        "errors": errors,
        "envelope_id": packet.envelope_id,
        "sender_id": packet.sender_id,
        "recipient_scope": packet.recipient_scope,
        "payload_digest": packet.payload_digest,
        "proposal_only": True,
        "automatic_import": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    result["validation_digest"] = stable_digest(result)
    return result


def enqueue_federation_envelope(store: Any, envelope: FederationEnvelope) -> str:
    return str(store.enqueue_sync_event("COGNOME_FEDERATION_ENVELOPE", envelope.envelope_id, envelope.to_dict()))


def import_validated_envelope(
    store: Any,
    envelope: FederationEnvelope | Mapping[str, Any],
    *,
    allowed_senders: Iterable[str],
    expected_recipient_scope: str,
    seen_nonces: MutableSet[str] | None = None,
    verifier: Verifier | None = None,
    allow_unsigned_local: bool = False,
    staging_path: str | Path,
    now: float | None = None,
) -> dict[str, Any]:
    packet = envelope if isinstance(envelope, FederationEnvelope) else FederationEnvelope.from_mapping(envelope)
    validation_nonces = set(seen_nonces or ())
    validation = validate_federation_envelope(
        packet,
        allowed_senders=allowed_senders,
        expected_recipient_scope=expected_recipient_scope,
        seen_nonces=validation_nonces,
        verifier=verifier,
        allow_unsigned_local=allow_unsigned_local,
        now=now,
    )
    if not validation["ok"]:
        raise ValueError("federation envelope validation failed: " + ", ".join(validation["errors"]))
    destination = Path(staging_path).resolve()
    _atomic_write_json(destination, packet.payload)
    imported = store.import_bundle(destination)
    if seen_nonces is not None:
        seen_nonces.add(packet.nonce)
    return {
        "ok": True,
        "envelope_id": packet.envelope_id,
        "payload_digest": packet.payload_digest,
        "validation_digest": validation["validation_digest"],
        "import_result": imported,
        "automatic_import": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
