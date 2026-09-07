from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any

D0 = "D0_NONPROMOTING"
SCHEMA = "AURA-PROJECT006-TRANSPORT-SOURCE-IDENTITY-BRIDGE-v1"


def canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return sha256(canon(value)).hexdigest()


def root_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} required")
    return value


@dataclass(frozen=True)
class DriveSourceIncarnation:
    file_id: str
    revision_id: str
    export_mime_type: str
    export_bytes: bytes

    def __post_init__(self) -> None:
        for name in ("file_id", "revision_id", "export_mime_type"):
            _id(getattr(self, name), name)
        if not isinstance(self.export_bytes, bytes):
            raise ValueError("export_bytes must be bytes")

    @property
    def export_root(self) -> str:
        return root_bytes(self.export_bytes)

    @property
    def incarnation_root(self) -> str:
        return digest({
            "schema": SCHEMA,
            "kind": "drive_source_incarnation",
            "file_id": self.file_id,
            "revision_id": self.revision_id,
            "export_mime_type": self.export_mime_type,
            "export_root": self.export_root,
        })


@dataclass(frozen=True)
class TransportCallback:
    kind: str
    command_id: str
    idempotency_key: str
    attempt_id: str
    source_envelope_digest: str
    schema_id: str
    state: str
    body_root: str
    outer_root: str
    result_digest: str | None = None
    response_sha256: str | None = None

    def __post_init__(self) -> None:
        for name in ("kind", "command_id", "idempotency_key", "attempt_id", "schema_id", "state"):
            _id(getattr(self, name), name)
        for name in ("source_envelope_digest", "body_root", "outer_root"):
            _root(getattr(self, name), name)
        if self.result_digest is not None:
            _root(self.result_digest, "result_digest")
        if self.response_sha256 is not None:
            _root(self.response_sha256, "response_sha256")


def parse_callback(raw: bytes) -> TransportCallback:
    if not isinstance(raw, bytes):
        raise ValueError("raw callback must be bytes")
    outer = json.loads(raw.decode("utf-8-sig"))
    body_text = outer.get("body")
    if not isinstance(body_text, str):
        raise ValueError("CALLBACK_BODY_REQUIRED")
    body = json.loads(body_text)
    receipt = body.get("executor_receipt") or {}
    return TransportCallback(
        kind=str(body.get("kind") or outer.get("kind") or ""),
        command_id=str(body.get("command_id") or ""),
        idempotency_key=str(body.get("idempotency_key") or ""),
        attempt_id=str(body.get("attempt_id") or ""),
        source_envelope_digest=str(body.get("source_envelope_digest") or ""),
        schema_id=str(body.get("schema_id") or ""),
        state=str(body.get("state") or ""),
        body_root=root_bytes(body_text.encode("utf-8")),
        outer_root=root_bytes(raw),
        result_digest=body.get("result_digest"),
        response_sha256=receipt.get("response_sha256"),
    )


@dataclass(frozen=True)
class DigestPreimageContract:
    contract_id: str
    normalization: str
    algorithm: str = "sha256"

    def __post_init__(self) -> None:
        _id(self.contract_id, "contract_id")
        if self.normalization not in {"UTF8_EXACT", "UTF8_NO_BOM_LF"}:
            raise ValueError("UNSUPPORTED_NORMALIZATION")
        if self.algorithm != "sha256":
            raise ValueError("UNSUPPORTED_DIGEST_ALGORITHM")


def recompute_transport_digest(source: DriveSourceIncarnation, contract: DigestPreimageContract) -> str:
    raw = source.export_bytes
    if contract.normalization == "UTF8_EXACT":
        payload = raw
    else:
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        payload = text.encode("utf-8")
    return root_bytes(payload)


@dataclass(frozen=True)
class AdmissionContext:
    command_id: str
    idempotency_key: str
    source_file_id: str
    source_revision_id: str
    expected_source_incarnation_root: str
    proof_bound_admission_root: str
    training_admission_root: str
    workcell_execution_root: str
    proof_authenticated: bool
    training_authenticated: bool
    workcell_current: bool

    def __post_init__(self) -> None:
        for name in ("command_id", "idempotency_key", "source_file_id", "source_revision_id"):
            _id(getattr(self, name), name)
        for name in ("expected_source_incarnation_root", "proof_bound_admission_root", "training_admission_root", "workcell_execution_root"):
            _root(getattr(self, name), name)
        for name in ("proof_authenticated", "training_authenticated", "workcell_current"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be bool")


class Disposition(str, Enum):
    BIND_OBSERVATION_D0 = "BIND_OBSERVATION_D0"
    HOLD = "HOLD"
    REBIND = "REBIND"
    REPROVE = "REPROVE"


@dataclass(frozen=True)
class SourceAdmissionDecision:
    disposition: Disposition
    reason: str
    observation_root: str | None = None
    independently_recomputed_transport_digest: str | None = None
    transport_digest_authority: bool = False
    effect_authority: bool = False
    training_authority: bool = False
    authority: str = D0
    gate10: bool = False

    def __post_init__(self) -> None:
        if self.observation_root is not None:
            _root(self.observation_root, "observation_root")
        if self.independently_recomputed_transport_digest is not None:
            _root(self.independently_recomputed_transport_digest, "independently_recomputed_transport_digest")
        if self.transport_digest_authority or self.effect_authority or self.training_authority or self.gate10 or self.authority != D0:
            raise ValueError("O17 decision cannot mint authority")


def validate_source_admission(*, source: DriveSourceIncarnation, ack: TransportCallback,
                              result: TransportCallback, ctx: AdmissionContext,
                              digest_contract: DigestPreimageContract | None) -> SourceAdmissionDecision:
    if (ack.kind, result.kind) != ("ACK", "RESULT"):
        return SourceAdmissionDecision(Disposition.HOLD, "TRANSPORT_PAIR_KIND_INVALID")
    if ack.attempt_id != result.attempt_id:
        return SourceAdmissionDecision(Disposition.HOLD, "TRANSPORT_ATTEMPT_DIVERGED")
    if ack.command_id != result.command_id or ack.idempotency_key != result.idempotency_key:
        return SourceAdmissionDecision(Disposition.HOLD, "TRANSPORT_COMMAND_LINEAGE_DIVERGED")
    if ack.source_envelope_digest != result.source_envelope_digest:
        return SourceAdmissionDecision(Disposition.HOLD, "TRANSPORT_REPORTED_SOURCE_DIGEST_DIVERGED")
    if (ack.command_id, ack.idempotency_key) != (ctx.command_id, ctx.idempotency_key):
        return SourceAdmissionDecision(Disposition.REBIND, "EXPECTED_COMMAND_LINEAGE_MOVED")
    if (source.file_id, source.revision_id) != (ctx.source_file_id, ctx.source_revision_id):
        return SourceAdmissionDecision(Disposition.REBIND, "DRIVE_SOURCE_INCARNATION_MOVED")
    if source.incarnation_root != ctx.expected_source_incarnation_root:
        return SourceAdmissionDecision(Disposition.REPROVE, "INDEPENDENT_SOURCE_INCARNATION_MOVED")
    if not ctx.proof_authenticated:
        return SourceAdmissionDecision(Disposition.HOLD, "PROOF_BOUND_ADMISSION_UNAUTHENTICATED")
    if not ctx.training_authenticated:
        return SourceAdmissionDecision(Disposition.HOLD, "TRAINING_ADMISSION_UNAUTHENTICATED")
    if not ctx.workcell_current:
        return SourceAdmissionDecision(Disposition.REBIND, "WORKCELL_EXECUTION_NOT_CURRENT")
    if digest_contract is None:
        return SourceAdmissionDecision(Disposition.HOLD, "UNRESOLVED_PREIMAGE_CONTRACT")
    computed = recompute_transport_digest(source, digest_contract)
    if computed != ack.source_envelope_digest:
        return SourceAdmissionDecision(Disposition.REPROVE, "TRANSPORT_DIGEST_PREIMAGE_MISMATCH", independently_recomputed_transport_digest=computed)
    observation_root = digest({
        "schema": SCHEMA,
        "kind": "proof_bound_transport_source_observation",
        "drive_source_incarnation_root": source.incarnation_root,
        "transport_source_digest": ack.source_envelope_digest,
        "digest_preimage_contract_id": digest_contract.contract_id,
        "attempt_id": ack.attempt_id,
        "command_id": ack.command_id,
        "idempotency_key": ack.idempotency_key,
        "ack_body_root": ack.body_root,
        "result_body_root": result.body_root,
        "proof_bound_admission_root": ctx.proof_bound_admission_root,
        "training_admission_root": ctx.training_admission_root,
        "workcell_execution_root": ctx.workcell_execution_root,
        "authority": D0,
        "transport_digest_authority": False,
        "effect_authority": False,
        "training_authority": False,
        "gate10": False,
    })
    return SourceAdmissionDecision(Disposition.BIND_OBSERVATION_D0,
                                   "INDEPENDENT_SOURCE_PREIMAGE_AND_DOWNSTREAM_PROOFS_BOUND",
                                   observation_root, computed)
