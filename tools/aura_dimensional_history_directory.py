"""AURA-MEMORY-01: non-writing dimensional history directory.

This module reconciles two independently useful memory identities:

* a stable subject key is the logical lookup/navigation handle;
* a versioned cognition record key is the immutable materialized-history handle.

The relation between them is explicit. It is never inferred from K27 locality,
timestamps, text similarity, hashes that merely look related, or a persisted
CURRENT label.

Functional navigation axes:
* Z: hydration depth L0..L4;
* Y: event-time + recorded-time bitemporal slicing;
* X: typed cross-domain edges;
* Scale: independent atomic -> universe zoom metadata.

K27 and other placement projections remain routing metadata only. This directory
never mutates the cognition store, proves source currentness, grants semantic
truth, executes tools/models, or accesses transformer KV state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from tools.aura_external_knowledge_store_writer import ExternalCognitionStoreRow

SCHEMA = "AURA-DIMENSIONAL-HISTORY-DIRECTORY-v1"
HEX = frozenset("0123456789abcdef")


class DirectoryError(ValueError):
    pass


class QueryDisposition(str, Enum):
    FOUND_HISTORY_CANDIDATE = "FOUND_HISTORY_CANDIDATE"
    NOT_FOUND = "NOT_FOUND"
    HOLD_AMBIGUOUS_PARALLEL_HISTORY = "HOLD_AMBIGUOUS_PARALLEL_HISTORY"
    HOLD_BROKEN_SUPERSESSION_EDGE = "HOLD_BROKEN_SUPERSESSION_EDGE"


class ScaleTier(str, Enum):
    ATOMIC = "ATOMIC"
    ARTIFACT = "ARTIFACT"
    ARENA = "ARENA"
    WORLD = "WORLD"
    UNIVERSE = "UNIVERSE"


ALLOWED_RELATIONS = frozenset(
    {
        "DEPENDS_ON",
        "DERIVED_FROM",
        "GROUNDED_IN",
        "VERIFIES",
        "IMPLEMENTS",
        "INDEPENDENT_OF",
        "MUST_NOT_AFFECT",
        "NOT_AUTHORIZED_BY",
        "CONTRADICTED_BY",
        "STALE_RELATIVE_TO",
    }
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DirectoryError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _text(value, name).lower()
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise DirectoryError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _instant(value: str, name: str) -> datetime:
    value = _text(value, name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DirectoryError(f"{name}_MUST_BE_ISO8601") from exc
    if parsed.tzinfo is None:
        raise DirectoryError(f"{name}_MUST_BE_OFFSET_AWARE")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class BitemporalStamp:
    event_at: str
    recorded_at: str

    def validate(self) -> None:
        _instant(self.event_at, "EVENT_AT")
        _instant(self.recorded_at, "RECORDED_AT")


@dataclass(frozen=True)
class CrossDomainEdge:
    relation: str
    target_subject_key: str
    edge_ref: str
    edge_generation: str
    authority: bool = False

    def validate(self) -> None:
        if self.relation not in ALLOWED_RELATIONS:
            raise DirectoryError("CROSS_DOMAIN_RELATION_NOT_TYPED")
        _sha256(self.target_subject_key, "TARGET_SUBJECT_KEY")
        _text(self.edge_ref, "EDGE_REF")
        _text(self.edge_generation, "EDGE_GENERATION")
        if self.authority is not False:
            raise DirectoryError("CROSS_DOMAIN_EDGE_CANNOT_GRANT_AUTHORITY")


@dataclass(frozen=True)
class ExactArchiveHandle:
    """Optional exact L4 cold-byte handle from an artifact-compression owner."""

    archive_ref: str
    codec_generation: str
    original_sha256: str
    responsibility: str = "ARTIFACT_COMPRESSION"
    compression_win_proven_for_this_object: bool = False
    semantic_truth: bool = False
    source_currentness_witness: bool = False
    transformer_kv_claim: bool = False

    def validate(self) -> None:
        _text(self.archive_ref, "ARCHIVE_REF")
        _text(self.codec_generation, "CODEC_GENERATION")
        _sha256(self.original_sha256, "ARCHIVE_ORIGINAL_SHA256")
        if self.responsibility != "ARTIFACT_COMPRESSION":
            raise DirectoryError("ARCHIVE_RESPONSIBILITY_MUST_REMAIN_ARTIFACT_COMPRESSION")
        if any(
            (
                self.semantic_truth,
                self.source_currentness_witness,
                self.transformer_kv_claim,
            )
        ):
            raise DirectoryError("ARCHIVE_HANDLE_CANNOT_WIDEN_MEMORY_AUTHORITY")


@dataclass(frozen=True)
class SubjectRecordBinding:
    """Explicit relation between stable logical identity and one version record.

    This is a relation record, not a self-authenticating truth certificate.
    """

    stable_subject_key: str
    evidence_generation_key: str
    candidate_id: str
    version_record_key: str
    record_generation: str
    binding_ref: str
    binding_generation: str
    relation: str = "SUBJECT_HAS_VERSION_RECORD"
    inferred_from_similarity: bool = False
    inferred_from_k27: bool = False
    inferred_from_time: bool = False
    semantic_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False

    def validate(self) -> None:
        _sha256(self.stable_subject_key, "STABLE_SUBJECT_KEY")
        _sha256(self.evidence_generation_key, "EVIDENCE_GENERATION_KEY")
        _sha256(self.candidate_id, "CANDIDATE_ID")
        _text(self.version_record_key, "VERSION_RECORD_KEY")
        _sha256(self.record_generation, "RECORD_GENERATION")
        _text(self.binding_ref, "BINDING_REF")
        _text(self.binding_generation, "BINDING_GENERATION")
        if self.relation != "SUBJECT_HAS_VERSION_RECORD":
            raise DirectoryError("SUBJECT_RECORD_RELATION_MISMATCH")
        if self.inferred_from_similarity or self.inferred_from_k27 or self.inferred_from_time:
            raise DirectoryError("SUBJECT_RECORD_BINDING_MUST_BE_EXPLICIT")
        if self.semantic_authority or self.write_authority or self.effect_authority:
            raise DirectoryError("SUBJECT_RECORD_BINDING_CANNOT_GRANT_AUTHORITY")

    @property
    def binding_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "binding": asdict(self)})


@dataclass(frozen=True)
class DimensionalHistoryEntry:
    stable_subject_key: str
    evidence_generation_key: str
    candidate_id: str
    version_record_key: str
    record_generation: str
    source_generation_id: str | None
    binding_digest: str
    temporal: BitemporalStamp
    hydration_level: int
    hydration: Mapping[str, Any]
    sector: str
    scale: ScaleTier
    cross_domain_edges: tuple[CrossDomainEdge, ...]
    supersedes_record_key: str | None
    exact_reopen: Mapping[str, Any]
    placement: Mapping[str, Any]
    archive: ExactArchiveHandle | None = None
    persisted_currentness_label: str | None = None
    currentness_witness: bool = False
    semantic_truth: bool = False
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    schema: str = SCHEMA

    def validate(self) -> None:
        _sha256(self.stable_subject_key, "ENTRY_STABLE_SUBJECT_KEY")
        _sha256(self.evidence_generation_key, "ENTRY_EVIDENCE_GENERATION_KEY")
        _sha256(self.candidate_id, "ENTRY_CANDIDATE_ID")
        _text(self.version_record_key, "ENTRY_VERSION_RECORD_KEY")
        _sha256(self.record_generation, "ENTRY_RECORD_GENERATION")
        if self.source_generation_id is not None:
            _text(self.source_generation_id, "ENTRY_SOURCE_GENERATION")
        _sha256(self.binding_digest, "ENTRY_BINDING_DIGEST")
        self.temporal.validate()
        if type(self.hydration_level) is not int or not 0 <= self.hydration_level <= 4:
            raise DirectoryError("HYDRATION_LEVEL_MUST_BE_L0_TO_L4")
        if not isinstance(self.hydration, Mapping):
            raise DirectoryError("HYDRATION_MUST_BE_MAPPING")
        expected = tuple(f"L{i}" for i in range(self.hydration_level + 1))
        if tuple(self.hydration.keys()) != expected:
            raise DirectoryError("HYDRATION_MUST_BE_CONTIGUOUS_FROM_L0")
        _text(self.sector, "SECTOR")
        if not isinstance(self.scale, ScaleTier):
            raise DirectoryError("SCALE_TIER_MUST_BE_TYPED")
        for edge in self.cross_domain_edges:
            edge.validate()
        if self.supersedes_record_key is not None:
            _text(self.supersedes_record_key, "SUPERSEDES_RECORD_KEY")
            if self.supersedes_record_key == self.version_record_key:
                raise DirectoryError("SELF_SUPERSESSION_FORBIDDEN")
        if not isinstance(self.exact_reopen, Mapping):
            raise DirectoryError("EXACT_REOPEN_MUST_BE_MAPPING")
        if not isinstance(self.placement, Mapping):
            raise DirectoryError("PLACEMENT_MUST_BE_MAPPING")
        if self.archive is not None:
            self.archive.validate()
        for name in (
            "currentness_witness",
            "semantic_truth",
            "instruction_authority",
            "write_authority",
            "effect_authority",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            if getattr(self, name) is not False:
                raise DirectoryError(f"{name.upper()}_MUST_REMAIN_FALSE")
        if self.schema != SCHEMA:
            raise DirectoryError("DIRECTORY_SCHEMA_MISMATCH")

    @property
    def entry_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "entry": asdict(self)})


def entry_from_versioned_row(
    *,
    row: ExternalCognitionStoreRow,
    binding: SubjectRecordBinding,
    temporal: BitemporalStamp,
    sector: str,
    scale: ScaleTier,
    cross_domain_edges: Sequence[CrossDomainEdge] = (),
    supersedes_record_key: str | None = None,
    archive: ExactArchiveHandle | None = None,
) -> DimensionalHistoryEntry:
    if not isinstance(row, ExternalCognitionStoreRow):
        raise TypeError("VERSIONED_COGNITION_ROW_REQUIRED")
    row.validate()
    binding.validate()
    temporal.validate()
    if binding.version_record_key != row.key:
        raise DirectoryError("BINDING_RECORD_KEY_MISMATCH")
    if binding.record_generation != row.record_generation:
        raise DirectoryError("BINDING_RECORD_GENERATION_MISMATCH")

    try:
        standing = json.loads(row.value["standing"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise DirectoryError("VERSION_ROW_STANDING_MUST_BE_JSON") from exc
    if standing.get("record_generation") != row.record_generation:
        raise DirectoryError("STANDING_RECORD_GENERATION_MISMATCH")
    level = standing.get("admitted_hydration_level")
    hydration = standing.get("hydration")
    if type(level) is not int or not 0 <= level <= 4:
        raise DirectoryError("ROW_HYDRATION_LEVEL_INVALID")
    if not isinstance(hydration, Mapping):
        raise DirectoryError("ROW_HYDRATION_MAPPING_REQUIRED")
    contiguous: dict[str, Any] = {}
    for i in range(level + 1):
        key = f"L{i}"
        if key not in hydration:
            raise DirectoryError("ROW_HYDRATION_NOT_CONTIGUOUS")
        contiguous[key] = hydration[key]

    cell = row.value["cell"]
    placement = {
        "placement_generation": row.placement_generation,
        "operational_13d": cell.get("operational_13d"),
        "k27_locality": cell.get("k27_locality"),
        "refresh_phase": cell.get("refresh_phase"),
        "routing_only": True,
        "semantic_identity": False,
        "authority": False,
    }
    entry = DimensionalHistoryEntry(
        stable_subject_key=binding.stable_subject_key,
        evidence_generation_key=binding.evidence_generation_key,
        candidate_id=binding.candidate_id,
        version_record_key=row.key,
        record_generation=row.record_generation,
        source_generation_id=row.source_generation_id,
        binding_digest=binding.binding_digest,
        temporal=temporal,
        hydration_level=level,
        hydration=contiguous,
        sector=_text(sector, "SECTOR"),
        scale=scale,
        cross_domain_edges=tuple(cross_domain_edges),
        supersedes_record_key=supersedes_record_key,
        exact_reopen=dict(row.value["reopen"]),
        placement=placement,
        archive=archive,
        persisted_currentness_label=standing.get("persisted_currentness_label"),
    )
    entry.validate()
    return entry


@dataclass(frozen=True)
class HistoryQueryReceipt:
    disposition: QueryDisposition
    stable_subject_key: str
    event_cut: str
    recorded_cut: str
    requested_hydration_level: int
    selected_record_key: str | None
    selected_entry_digest: str | None
    returned_hydration_level: int | None
    hydration_payload: Mapping[str, Any] | None
    cross_domain_edges: tuple[CrossDomainEdge, ...]
    scale: ScaleTier | None
    exact_reopen: Mapping[str, Any] | None
    archive: ExactArchiveHandle | None
    candidate_record_keys: tuple[str, ...]
    source_currentness_revalidation_required: bool = True
    timeline_is_source_truth: bool = False
    temporal_adjacency_is_causal_dependency: bool = False
    placement_is_semantic_identity: bool = False
    semantic_truth: bool = False
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "query": asdict(self)})


class DimensionalHistoryDirectory:
    def __init__(self, entries: Iterable[DimensionalHistoryEntry]) -> None:
        items = tuple(entries)
        for item in items:
            item.validate()
        keys = [item.version_record_key for item in items]
        if len(keys) != len(set(keys)):
            raise DirectoryError("DUPLICATE_VERSION_RECORD_KEY")
        self._entries = items
        self._index = {item.version_record_key: item for item in items}
        for item in items:
            if item.supersedes_record_key is not None:
                predecessor = self._index.get(item.supersedes_record_key)
                if predecessor is None:
                    raise DirectoryError("SUPERSESSION_PREDECESSOR_MISSING")
                if predecessor.stable_subject_key != item.stable_subject_key:
                    raise DirectoryError("SUPERSESSION_CANNOT_CROSS_STABLE_SUBJECT")

    def query(
        self,
        *,
        stable_subject_key: str,
        event_cut: str,
        recorded_cut: str,
        requested_hydration_level: int = 0,
    ) -> HistoryQueryReceipt:
        stable_subject_key = _sha256(stable_subject_key, "QUERY_STABLE_SUBJECT_KEY")
        event_dt = _instant(event_cut, "QUERY_EVENT_CUT")
        recorded_dt = _instant(recorded_cut, "QUERY_RECORDED_CUT")
        if type(requested_hydration_level) is not int or not 0 <= requested_hydration_level <= 4:
            raise DirectoryError("QUERY_HYDRATION_LEVEL_MUST_BE_L0_TO_L4")

        eligible = tuple(
            item
            for item in self._entries
            if item.stable_subject_key == stable_subject_key
            and _instant(item.temporal.event_at, "EVENT_AT") <= event_dt
            and _instant(item.temporal.recorded_at, "RECORDED_AT") <= recorded_dt
        )
        common = dict(
            schema=SCHEMA,
            stable_subject_key=stable_subject_key,
            event_cut=event_cut,
            recorded_cut=recorded_cut,
            requested_hydration_level=requested_hydration_level,
            candidate_record_keys=tuple(sorted(item.version_record_key for item in eligible)),
        )
        if not eligible:
            return HistoryQueryReceipt(
                disposition=QueryDisposition.NOT_FOUND,
                selected_record_key=None,
                selected_entry_digest=None,
                returned_hydration_level=None,
                hydration_payload=None,
                cross_domain_edges=(),
                scale=None,
                exact_reopen=None,
                archive=None,
                **common,
            )

        superseded = {
            item.supersedes_record_key
            for item in eligible
            if item.supersedes_record_key is not None
            and item.supersedes_record_key in {candidate.version_record_key for candidate in eligible}
        }
        terminals = tuple(item for item in eligible if item.version_record_key not in superseded)
        if len(terminals) != 1:
            return HistoryQueryReceipt(
                disposition=QueryDisposition.HOLD_AMBIGUOUS_PARALLEL_HISTORY,
                selected_record_key=None,
                selected_entry_digest=None,
                returned_hydration_level=None,
                hydration_payload=None,
                cross_domain_edges=(),
                scale=None,
                exact_reopen=None,
                archive=None,
                **common,
            )

        selected = terminals[0]
        returned_level = min(requested_hydration_level, selected.hydration_level)
        hydration = {f"L{i}": selected.hydration[f"L{i}"] for i in range(returned_level + 1)}
        return HistoryQueryReceipt(
            disposition=QueryDisposition.FOUND_HISTORY_CANDIDATE,
            selected_record_key=selected.version_record_key,
            selected_entry_digest=selected.entry_digest,
            returned_hydration_level=returned_level,
            hydration_payload=hydration,
            cross_domain_edges=selected.cross_domain_edges,
            scale=selected.scale,
            exact_reopen=selected.exact_reopen if returned_level == 4 else None,
            archive=selected.archive if returned_level == 4 else None,
            **common,
        )
