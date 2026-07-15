"""Immutable P6.2 contracts for QDKT inventory and dual-read evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
import re
from typing import Any, Mapping

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest, stable_id
from aura_qdkt_observations import QDKTTruthClass

QDKT_COMPATIBILITY_VERSION = "AURA_QDKT_COMPATIBILITY_P6_2"
QDKT_INVENTORY_VERSION = "AURA_QDKT_INVENTORY_P6_2"
QDKT_OWNERSHIP_VERSION = "AURA_QDKT_OWNERSHIP_P6_2"
QDKT_PATCH_AUTHORITY = False
QDKT_CURRENT_RESULT_OWNER = "quantum_dag.QuantumMerkleDAG"
QDKT_CANONICAL_EVIDENCE_OWNER = "aura_event_contracts.AppendOnlyEventStore"
QDKT_RECOMMENDATION = "RETAIN_LEGACY_DUAL_READ"

_ROOT_RE = re.compile(r"^[0-9A-F]{16}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{32}$")


class QDKTUseClass(str, Enum):
    GENERATOR_DEFINITION = "GENERATOR_DEFINITION"
    IMPORT = "IMPORT"
    CONSTRUCTOR = "CONSTRUCTOR"
    METHOD_CALL = "METHOD_CALL"
    ROOT_CONSUMER = "ROOT_CONSUMER"
    BELIEF_CONSUMER = "BELIEF_CONSUMER"
    PERSISTENCE = "PERSISTENCE"
    DISPLAY = "DISPLAY"
    TEST = "TEST"
    DOCUMENTATION = "DOCUMENTATION"


class QDKTInventoryImpact(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class QDKTInventoryReadiness(str, Enum):
    DUAL_READ_CANDIDATE = "DUAL_READ_CANDIDATE"
    TEST_ONLY = "TEST_ONLY"
    ARCHIVAL_ONLY = "ARCHIVAL_ONLY"
    DOCUMENTATION_ONLY = "DOCUMENTATION_ONLY"
    NO_MIGRATION_REQUIRED = "NO_MIGRATION_REQUIRED"


class QDKTDualReadStatus(str, Enum):
    VERIFIED = "VERIFIED"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    UNAVAILABLE = "UNAVAILABLE"
    MISMATCHED = "MISMATCHED"


class QDKTCompatibilityFindingCode(str, Enum):
    INVALID_LEGACY_RESULT = "INVALID_LEGACY_RESULT"
    INVALID_SOURCE_SNAPSHOT = "INVALID_SOURCE_SNAPSHOT"
    CANONICAL_EVIDENCE_UNAVAILABLE = "CANONICAL_EVIDENCE_UNAVAILABLE"
    CANONICAL_INTEGRITY_FAILED = "CANONICAL_INTEGRITY_FAILED"
    LEGACY_ROOT_MISMATCH = "LEGACY_ROOT_MISMATCH"
    LEGACY_BELIEF_MISMATCH = "LEGACY_BELIEF_MISMATCH"
    SOURCE_SNAPSHOT_MISMATCH = "SOURCE_SNAPSHOT_MISMATCH"
    DUPLICATE_MATCHING_EVIDENCE = "DUPLICATE_MATCHING_EVIDENCE"
    CONFLICTING_CANONICAL_EVIDENCE = "CONFLICTING_CANONICAL_EVIDENCE"
    STALE_CANONICAL_EVIDENCE = "STALE_CANONICAL_EVIDENCE"
    SOURCE_SNAPSHOT_NOT_SUPPLIED = "SOURCE_SNAPSHOT_NOT_SUPPLIED"


def _required(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional(value: Any, name: str) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    return value.strip()


def _enum(value: Any, enum_type: type[Enum], name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        raise ValueError(f"unsupported {name}") from exc


def _strict_legacy_result(value: Mapping[str, Any]) -> tuple[str, int]:
    if not isinstance(value, Mapping) or set(value) != {"root", "belief"}:
        raise ValueError("legacy_result must contain exactly root and belief")
    root = value.get("root")
    belief = value.get("belief")
    if type(root) is not str or not _ROOT_RE.fullmatch(root):
        raise ValueError("legacy_result.root is malformed")
    if type(belief) is not int or belief < 0:
        raise ValueError("legacy_result.belief must be a non-negative integer")
    return root, belief


@dataclass(frozen=True)
class QDKTInventoryEntry:
    entry_id: str
    file_path: str
    symbol: str
    line: int
    use_class: QDKTUseClass | str
    impact: QDKTInventoryImpact | str
    readiness: QDKTInventoryReadiness | str
    detail: str
    version: str = QDKT_INVENTORY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "file_path", _required(self.file_path, "file_path"))
        object.__setattr__(self, "symbol", _required(self.symbol, "symbol"))
        if type(self.line) is not int or self.line < 1:
            raise ValueError("line must be a positive integer")
        use_class = _enum(self.use_class, QDKTUseClass, "use_class")
        impact = _enum(self.impact, QDKTInventoryImpact, "impact")
        readiness = _enum(self.readiness, QDKTInventoryReadiness, "readiness")
        detail = _required(self.detail, "detail")
        object.__setattr__(self, "use_class", use_class)
        object.__setattr__(self, "impact", impact)
        object.__setattr__(self, "readiness", readiness)
        object.__setattr__(self, "detail", detail)
        if self.version != QDKT_INVENTORY_VERSION:
            raise ValueError("unsupported QDKT inventory version")
        if self.entry_id != stable_id("qdkt-use", self.identity_payload()):
            raise ValueError("entry_id does not match the canonical inventory identity")

    @classmethod
    def create(
        cls,
        *,
        file_path: str,
        symbol: str,
        line: int,
        use_class: QDKTUseClass | str,
        impact: QDKTInventoryImpact | str,
        readiness: QDKTInventoryReadiness | str,
        detail: str,
    ) -> "QDKTInventoryEntry":
        identity = {
            "file_path": _required(file_path, "file_path"),
            "symbol": _required(symbol, "symbol"),
            "line": line,
            "use_class": _enum(use_class, QDKTUseClass, "use_class").value,
            "impact": _enum(impact, QDKTInventoryImpact, "impact").value,
            "readiness": _enum(readiness, QDKTInventoryReadiness, "readiness").value,
            "detail": _required(detail, "detail"),
        }
        return cls(entry_id=stable_id("qdkt-use", identity), **identity)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "symbol": self.symbol,
            "line": self.line,
            "use_class": self.use_class.value,
            "impact": self.impact.value,
            "readiness": self.readiness.value,
            "detail": self.detail,
        }

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["use_class"] = self.use_class.value
        value["impact"] = self.impact.value
        value["readiness"] = self.readiness.value
        return value


@dataclass(frozen=True)
class QDKTInventoryReport:
    entries: tuple[QDKTInventoryEntry, ...]
    scanned_files: int
    ignored_files: int
    version: str = QDKT_INVENTORY_VERSION

    def __post_init__(self) -> None:
        if not all(isinstance(item, QDKTInventoryEntry) for item in self.entries):
            raise ValueError("entries contains an invalid inventory entry")
        canonical = tuple(
            sorted(
                self.entries,
                key=lambda item: (
                    item.file_path,
                    item.line,
                    item.use_class.value,
                    item.symbol,
                    item.entry_id,
                ),
            )
        )
        if len({item.entry_id for item in canonical}) != len(canonical):
            raise ValueError("inventory entries must have unique identities")
        object.__setattr__(self, "entries", canonical)
        for name in ("scanned_files", "ignored_files"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.version != QDKT_INVENTORY_VERSION:
            raise ValueError("unsupported QDKT inventory report version")

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [item.to_dict() for item in self.entries],
            "scanned_files": self.scanned_files,
            "ignored_files": self.ignored_files,
            "version": self.version,
        }


@dataclass(frozen=True)
class QDKTCompatibilityFinding:
    code: QDKTCompatibilityFindingCode | str
    detail: str
    event_ids: tuple[str, ...] = ()
    blocking: bool = True

    def __post_init__(self) -> None:
        code = _enum(self.code, QDKTCompatibilityFindingCode, "finding code")
        detail = _required(self.detail, "detail")
        if isinstance(self.event_ids, (str, bytes, bytearray)):
            raise ValueError("event_ids must be a sequence")
        event_ids = tuple(_required(item, "event_id") for item in self.event_ids)
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("event_ids must not contain duplicates")
        if type(self.blocking) is not bool:
            raise ValueError("blocking must be a boolean")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "detail", detail)
        object.__setattr__(self, "event_ids", event_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "detail": self.detail,
            "event_ids": list(self.event_ids),
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class QDKTOwnershipRecommendation:
    current_result_owner: str = QDKT_CURRENT_RESULT_OWNER
    canonical_evidence_owner: str = QDKT_CANONICAL_EVIDENCE_OWNER
    recommendation: str = QDKT_RECOMMENDATION
    redirect_ready: bool = False
    delete_legacy_ready: bool = False
    storage_transfer_ready: bool = False
    historical_backfill_ready: bool = False
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    qdkt_patch_authority: bool = QDKT_PATCH_AUTHORITY
    version: str = QDKT_OWNERSHIP_VERSION

    def __post_init__(self) -> None:
        _required(self.current_result_owner, "current_result_owner")
        _required(self.canonical_evidence_owner, "canonical_evidence_owner")
        if self.recommendation != QDKT_RECOMMENDATION:
            raise ValueError("unsupported QDKT ownership recommendation")
        if any(
            value is not False
            for value in (
                self.redirect_ready,
                self.delete_legacy_ready,
                self.storage_transfer_ready,
                self.historical_backfill_ready,
                self.vsa_patch_authority,
                self.qdkt_patch_authority,
            )
        ):
            raise ValueError("P6.2 must not authorize migration or patch authority")
        if self.proposal_only is not True or self.patch_authority != PATCH_AUTHORITY:
            raise ValueError("QDKT ownership authority boundary changed")
        if self.version != QDKT_OWNERSHIP_VERSION:
            raise ValueError("unsupported QDKT ownership version")

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QDKTDualReadEvidence:
    legacy_root: str
    legacy_belief: int
    status: QDKTDualReadStatus | str
    findings: tuple[QDKTCompatibilityFinding, ...]
    matching_event_ids: tuple[str, ...] = ()
    observation_id: str = ""
    payload_ref: str = ""
    payload_digest: str = ""
    source_snapshot_digest: str = ""
    source_count: int | None = None
    canonical_created_at: float | None = None
    inventory_digest: str = ""
    ownership_digest: str = ""
    truth_class: str = QDKTTruthClass.LEGACY_NONDETERMINISTIC_ADVISORY.value
    generator_replayed: bool = False
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    qdkt_patch_authority: bool = QDKT_PATCH_AUTHORITY
    version: str = QDKT_COMPATIBILITY_VERSION

    def __post_init__(self) -> None:
        root, belief = _strict_legacy_result(
            {"root": self.legacy_root, "belief": self.legacy_belief}
        )
        status = _enum(self.status, QDKTDualReadStatus, "dual-read status")
        if not all(isinstance(item, QDKTCompatibilityFinding) for item in self.findings):
            raise ValueError("findings contains an invalid compatibility finding")
        findings = tuple(
            sorted(
                self.findings,
                key=lambda item: (item.code.value, item.event_ids, item.detail),
            )
        )
        if isinstance(self.matching_event_ids, (str, bytes, bytearray)):
            raise ValueError("matching_event_ids must be a sequence")
        matching = tuple(_required(item, "matching_event_id") for item in self.matching_event_ids)
        if len(matching) != len(set(matching)):
            raise ValueError("matching_event_ids must not contain duplicates")
        for name in (
            "observation_id",
            "payload_ref",
            "payload_digest",
            "source_snapshot_digest",
            "inventory_digest",
            "ownership_digest",
        ):
            object.__setattr__(self, name, _optional(getattr(self, name), name))
        if self.source_snapshot_digest and not _DIGEST_RE.fullmatch(self.source_snapshot_digest):
            raise ValueError("source_snapshot_digest must be a canonical digest")
        if self.source_count is not None and (
            type(self.source_count) is not int or self.source_count < 0
        ):
            raise ValueError("source_count must be a non-negative integer or None")
        if self.canonical_created_at is not None and (
            isinstance(self.canonical_created_at, bool)
            or not isinstance(self.canonical_created_at, (int, float))
            or not math.isfinite(float(self.canonical_created_at))
        ):
            raise ValueError("canonical_created_at must be finite or None")
        if self.truth_class != QDKTTruthClass.LEGACY_NONDETERMINISTIC_ADVISORY.value:
            raise ValueError("QDKT truth class changed")
        if (
            self.generator_replayed is not False
            or self.proposal_only is not True
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.qdkt_patch_authority is not False
        ):
            raise ValueError("QDKT compatibility authority boundary changed")
        if status is QDKTDualReadStatus.VERIFIED:
            if findings or len(matching) != 1:
                raise ValueError("verified evidence requires exactly one clean match")
            for name in ("observation_id", "payload_ref", "payload_digest"):
                if not getattr(self, name):
                    raise ValueError(f"verified evidence requires {name}")
            if not self.source_snapshot_digest or self.source_count is None:
                raise ValueError("verified evidence requires source snapshot agreement")
        if status is QDKTDualReadStatus.ADVISORY_ONLY and not matching:
            raise ValueError("advisory evidence requires a canonical root/belief match")
        if self.version != QDKT_COMPATIBILITY_VERSION:
            raise ValueError("unsupported QDKT compatibility version")
        object.__setattr__(self, "legacy_root", root)
        object.__setattr__(self, "legacy_belief", belief)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "matching_event_ids", matching)
        if self.canonical_created_at is not None:
            object.__setattr__(self, "canonical_created_at", float(self.canonical_created_at))

    @property
    def legacy_result(self) -> dict[str, Any]:
        return {"root": self.legacy_root, "belief": self.legacy_belief}

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "legacy_result": self.legacy_result,
            "status": self.status.value,
            "findings": [item.to_dict() for item in self.findings],
            "matching_event_ids": list(self.matching_event_ids),
            "observation_id": self.observation_id,
            "payload_ref": self.payload_ref,
            "payload_digest": self.payload_digest,
            "source_snapshot_digest": self.source_snapshot_digest,
            "source_count": self.source_count,
            "canonical_created_at": self.canonical_created_at,
            "inventory_digest": self.inventory_digest,
            "ownership_digest": self.ownership_digest,
            "truth_class": self.truth_class,
            "generator_replayed": self.generator_replayed,
            "proposal_only": self.proposal_only,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "qdkt_patch_authority": self.qdkt_patch_authority,
            "version": self.version,
        }


def validate_legacy_result(value: Mapping[str, Any]) -> tuple[str, int]:
    """Strict public validator shared by the P6.2 read-only facade."""
    return _strict_legacy_result(value)


__all__ = [
    "QDKTCompatibilityFinding",
    "QDKTCompatibilityFindingCode",
    "QDKTInventoryEntry",
    "QDKTInventoryImpact",
    "QDKTInventoryReadiness",
    "QDKTInventoryReport",
    "QDKTOwnershipRecommendation",
    "QDKTDualReadEvidence",
    "QDKTDualReadStatus",
    "QDKTUseClass",
    "validate_legacy_result",
]
