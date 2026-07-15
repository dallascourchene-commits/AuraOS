"""Immutable P6.2 contracts for QDKT inventory and dual-read evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
from pathlib import PurePosixPath
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
_EVENT_ID_RE = re.compile(r"^event_[0-9a-f]{24}$")
_OBSERVATION_ID_RE = re.compile(r"^qdkt-observation_[0-9a-f]{24}$")
_PAYLOAD_REF_RE = re.compile(r"^payload_[0-9a-f]{24}$")
_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:/")


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
    UNPARSED_REFERENCE = "UNPARSED_REFERENCE"


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


def _tuple(value: Any, name: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence")
    try:
        return tuple(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a sequence") from exc


def _digest(value: Any, name: str, *, required: bool = False) -> str:
    text = _optional(value, name)
    if required and not text:
        raise ValueError(f"{name} must be a canonical digest")
    if text and not _DIGEST_RE.fullmatch(text):
        raise ValueError(f"{name} must be a canonical digest")
    return text


def _count(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer or None")
    return value


def _relative_path(value: Any, name: str = "file_path") -> str:
    text = _required(value, name).replace("\\", "/")
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or _DRIVE_PATH_RE.match(text)
        or text != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"{name} must be a normalized repository-relative path")
    return text


def _identifier(value: Any, name: str, pattern: re.Pattern[str], *, required: bool = False) -> str:
    text = _optional(value, name)
    if required and not text:
        raise ValueError(f"{name} must be a canonical identifier")
    if text and not pattern.fullmatch(text):
        raise ValueError(f"{name} must be a canonical identifier")
    return text


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
        object.__setattr__(self, "file_path", _relative_path(self.file_path))
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
            "file_path": _relative_path(file_path),
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
        entries = _tuple(self.entries, "entries")
        if not all(isinstance(item, QDKTInventoryEntry) for item in entries):
            raise ValueError("entries contains an invalid inventory entry")
        canonical = tuple(
            sorted(
                entries,
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
        if self.ignored_files > self.scanned_files:
            raise ValueError("ignored_files must not exceed scanned_files")
        if len({item.file_path for item in canonical}) > self.scanned_files:
            raise ValueError("inventory entries reference more files than were scanned")
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
        raw_ids = _tuple(self.event_ids, "event_ids")
        event_ids = tuple(_required(item, "event_id") for item in raw_ids)
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
        if self.current_result_owner != QDKT_CURRENT_RESULT_OWNER:
            raise ValueError("current QDKT result ownership changed")
        if self.canonical_evidence_owner != QDKT_CANONICAL_EVIDENCE_OWNER:
            raise ValueError("canonical QDKT evidence ownership changed")
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


QDKT_OWNERSHIP_DIGEST = QDKTOwnershipRecommendation().digest


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
    canonical_source_snapshot_digest: str = ""
    canonical_source_count: int | None = None
    requested_source_snapshot_digest: str = ""
    requested_source_count: int | None = None
    canonical_created_at: float | None = None
    inventory_digest: str = ""
    ownership_digest: str = QDKT_OWNERSHIP_DIGEST
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

        raw_findings = _tuple(self.findings, "findings")
        if not all(isinstance(item, QDKTCompatibilityFinding) for item in raw_findings):
            raise ValueError("findings contains an invalid compatibility finding")
        unique_findings = {
            (item.code.value, item.detail, item.event_ids, item.blocking): item
            for item in raw_findings
        }
        findings = tuple(
            sorted(
                unique_findings.values(),
                key=lambda item: (item.code.value, item.event_ids, item.detail, item.blocking),
            )
        )

        raw_matching = _tuple(self.matching_event_ids, "matching_event_ids")
        matching = tuple(
            _identifier(item, "matching_event_id", _EVENT_ID_RE, required=True)
            for item in raw_matching
        )
        if len(matching) != len(set(matching)):
            raise ValueError("matching_event_ids must not contain duplicates")

        observation_id = _identifier(
            self.observation_id,
            "observation_id",
            _OBSERVATION_ID_RE,
        )
        payload_ref = _identifier(self.payload_ref, "payload_ref", _PAYLOAD_REF_RE)
        object.__setattr__(self, "observation_id", observation_id)
        object.__setattr__(self, "payload_ref", payload_ref)
        object.__setattr__(
            self,
            "payload_digest",
            _digest(self.payload_digest, "payload_digest"),
        )
        object.__setattr__(
            self,
            "canonical_source_snapshot_digest",
            _digest(
                self.canonical_source_snapshot_digest,
                "canonical_source_snapshot_digest",
            ),
        )
        object.__setattr__(
            self,
            "requested_source_snapshot_digest",
            _digest(
                self.requested_source_snapshot_digest,
                "requested_source_snapshot_digest",
            ),
        )
        object.__setattr__(
            self,
            "inventory_digest",
            _digest(self.inventory_digest, "inventory_digest"),
        )
        ownership_digest = _digest(
            self.ownership_digest,
            "ownership_digest",
            required=True,
        )
        if ownership_digest != QDKT_OWNERSHIP_DIGEST:
            raise ValueError("ownership_digest does not match the P6.2 ownership boundary")
        object.__setattr__(self, "ownership_digest", ownership_digest)

        canonical_count = _count(self.canonical_source_count, "canonical_source_count")
        requested_count = _count(self.requested_source_count, "requested_source_count")
        object.__setattr__(self, "canonical_source_count", canonical_count)
        object.__setattr__(self, "requested_source_count", requested_count)
        if bool(self.canonical_source_snapshot_digest) != (canonical_count is not None):
            raise ValueError("canonical source snapshot digest and count must appear together")
        if bool(self.requested_source_snapshot_digest) != (requested_count is not None):
            raise ValueError("requested source snapshot digest and count must appear together")

        if self.canonical_created_at is not None and (
            isinstance(self.canonical_created_at, bool)
            or not isinstance(self.canonical_created_at, (int, float))
            or not math.isfinite(float(self.canonical_created_at))
            or float(self.canonical_created_at) < 0.0
        ):
            raise ValueError("canonical_created_at must be finite, non-negative, or None")

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

        metadata_flags = (
            bool(self.observation_id),
            bool(self.payload_ref),
            bool(self.payload_digest),
            bool(self.canonical_source_snapshot_digest),
            canonical_count is not None,
            self.canonical_created_at is not None,
        )
        if any(metadata_flags) and not all(metadata_flags):
            raise ValueError("canonical event metadata must be complete or absent")
        has_selected_metadata = all(metadata_flags)
        if len(matching) == 1 and not has_selected_metadata:
            raise ValueError("a single matching event requires complete canonical metadata")
        if len(matching) != 1 and has_selected_metadata:
            raise ValueError("canonical metadata requires exactly one selected event")

        blocking = tuple(item for item in findings if item.blocking)
        if status is QDKTDualReadStatus.VERIFIED:
            if findings or len(matching) != 1 or not has_selected_metadata:
                raise ValueError("verified evidence requires exactly one clean canonical match")
            if not self.requested_source_snapshot_digest:
                raise ValueError("verified evidence requires a requested source snapshot")
            if (
                self.requested_source_snapshot_digest
                != self.canonical_source_snapshot_digest
                or requested_count != canonical_count
            ):
                raise ValueError("verified evidence requires requested and canonical snapshot agreement")
        elif status is QDKTDualReadStatus.ADVISORY_ONLY:
            if len(matching) != 1 or not has_selected_metadata or blocking:
                raise ValueError("advisory evidence requires one non-blocking canonical match")
            if self.requested_source_snapshot_digest:
                raise ValueError("advisory evidence must not claim a requested source snapshot")
            if len(findings) != 1 or findings[0].code is not QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_NOT_SUPPLIED:
                raise ValueError("advisory evidence requires the source-snapshot warning")
        elif status is QDKTDualReadStatus.UNAVAILABLE:
            if matching or has_selected_metadata:
                raise ValueError("unavailable evidence must not select a canonical event")
            if len(findings) != 1 or findings[0].code is not QDKTCompatibilityFindingCode.CANONICAL_EVIDENCE_UNAVAILABLE:
                raise ValueError("unavailable evidence requires the unavailable finding")
            if not findings[0].blocking:
                raise ValueError("unavailable evidence must be blocking")
        elif status is QDKTDualReadStatus.MISMATCHED and not blocking:
            raise ValueError("mismatched evidence requires at least one blocking finding")

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
            "canonical_source_snapshot_digest": self.canonical_source_snapshot_digest,
            "canonical_source_count": self.canonical_source_count,
            "requested_source_snapshot_digest": self.requested_source_snapshot_digest,
            "requested_source_count": self.requested_source_count,
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
    "QDKT_OWNERSHIP_DIGEST",
    "QDKTDualReadEvidence",
    "QDKTDualReadStatus",
    "QDKTUseClass",
    "validate_legacy_result",
]
