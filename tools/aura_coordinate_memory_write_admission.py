#!/usr/bin/env python3
"""Non-writing admission membrane for aura-coordinate-memory-kv-v1.

Objective E consumes the exact-green #735 external-knowledge coordinate-memory
candidate and applies the independently resolved currentness/admission discipline
from exact-green #395 before any persistent write can be considered.

This module is deliberately *not* a writer.  It inspects one exact immutable store
snapshot and emits only a deterministic plan or a typed HOLD.  No method accepts a
path, file handle, Drive reference, Git ref, network client, or mutation callback.

The current v1 store has one important representation limit: semantic K values are
unique, while a non-empty ``successor`` marks that same row as historical.  Because
#735 preserves one stable subject key across evidence generations, v1 cannot both
retain the old row and install a new current row under the same K.  A differing
resolved evidence generation therefore remains HOLD_SUPERSESSION_REPRESENTATION_REQUIRED
rather than being laundered into a lossy replacement.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping

from tools.aura_external_knowledge_coordinate_memory_candidate import (
    CoordinateMemoryCandidateV2,
    SCHEMA as CANDIDATE_SCHEMA,
)
from tools.aura_external_cognition_resolve_adapter import (
    SCHEMA_NAME as STORE_SCHEMA_NAME,
    SCHEMA_VERSION as STORE_SCHEMA_VERSION,
)

SCHEMA = "AURA-COORDINATE-MEMORY-WRITE-ADMISSION-v1"
SEMANTIC_KEY_MODE = "STABLE_SUBJECT_KEY"
VALUE_DIGEST_RECIPE = "AURA-EKI-WP03-PROPOSED-VALUE-v2"
ROW_DIGEST_RECIPE = "AURA-EKI-WP03-PROPOSED-ROW-v2"
HEX = frozenset("0123456789abcdef")


class WriteAdmissionDisposition(str, Enum):
    INSERT_NEW_PLAN = "INSERT_NEW_PLAN"
    NOOP_IDENTICAL_PLAN = "NOOP_IDENTICAL_PLAN"
    HOLD_CANDIDATE_CEILING = "HOLD_CANDIDATE_CEILING"
    HOLD_SCHEMA_POLICY = "HOLD_SCHEMA_POLICY"
    HOLD_STORE_INTEGRITY = "HOLD_STORE_INTEGRITY"
    HOLD_STORE_STALE = "HOLD_STORE_STALE"
    HOLD_CURRENTNESS_EVIDENCE_REQUIRED = "HOLD_CURRENTNESS_EVIDENCE_REQUIRED"
    HOLD_CURRENTNESS_EVIDENCE_MISMATCH = "HOLD_CURRENTNESS_EVIDENCE_MISMATCH"
    HOLD_CURRENTNESS_REOPEN = "HOLD_CURRENTNESS_REOPEN"
    HOLD_EXISTING_KEY_AMBIGUOUS = "HOLD_EXISTING_KEY_AMBIGUOUS"
    HOLD_EXISTING_GENERATION_UNRESOLVED = "HOLD_EXISTING_GENERATION_UNRESOLVED"
    HOLD_ROW_IDENTITY_CONFLICT = "HOLD_ROW_IDENTITY_CONFLICT"
    HOLD_SUPERSESSION_RELATION_REQUIRED = "HOLD_SUPERSESSION_RELATION_REQUIRED"
    HOLD_SUPERSESSION_REPRESENTATION_REQUIRED = "HOLD_SUPERSESSION_REPRESENTATION_REQUIRED"


class SupersessionRelation(str, Enum):
    NONE = "NONE"
    IDENTICAL_GENERATION = "IDENTICAL_GENERATION"
    PROPOSED_SUPERSEDES_EXISTING = "PROPOSED_SUPERSEDES_EXISTING"
    CONFLICT_REVIEW_REQUIRED = "CONFLICT_REVIEW_REQUIRED"


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
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _text(value, name).lower()
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _false(value: Any, name: str) -> bool:
    if value is not False:
        raise ValueError(f"{name}_MUST_REMAIN_FALSE")
    return False


@dataclass(frozen=True)
class CoordinateMemorySchemaPolicyV1:
    """Schema-owner policy input for *planning* only, never mutation authority."""

    schema_owner_ref: str
    schema_owner_generation: str
    policy_generation: str
    store_schema_name: str = STORE_SCHEMA_NAME
    store_schema_version: str = STORE_SCHEMA_VERSION
    candidate_schema: str = CANDIDATE_SCHEMA
    semantic_key_mode: str = SEMANTIC_KEY_MODE
    value_digest_recipe: str = VALUE_DIGEST_RECIPE
    row_digest_recipe: str = ROW_DIGEST_RECIPE
    insert_plan_sanctioned: bool = True
    identical_noop_plan_sanctioned: bool = True
    supersession_representation_sanctioned: bool = False
    store_mutation_authorized: bool = False
    write_effect_authorized: bool = False
    semantic_authority: bool = False

    def validate(self) -> None:
        _text(self.schema_owner_ref, "SCHEMA_OWNER_REF")
        _text(self.schema_owner_generation, "SCHEMA_OWNER_GENERATION")
        _text(self.policy_generation, "POLICY_GENERATION")
        if self.store_schema_name != STORE_SCHEMA_NAME or self.store_schema_version != STORE_SCHEMA_VERSION:
            raise ValueError("STORE_SCHEMA_POLICY_MISMATCH")
        if self.candidate_schema != CANDIDATE_SCHEMA:
            raise ValueError("CANDIDATE_SCHEMA_POLICY_MISMATCH")
        if self.semantic_key_mode != SEMANTIC_KEY_MODE:
            raise ValueError("SEMANTIC_KEY_MODE_MISMATCH")
        if self.value_digest_recipe != VALUE_DIGEST_RECIPE or self.row_digest_recipe != ROW_DIGEST_RECIPE:
            raise ValueError("DIGEST_RECIPE_POLICY_MISMATCH")
        if self.insert_plan_sanctioned is not True or self.identical_noop_plan_sanctioned is not True:
            raise ValueError("INSERT_AND_NOOP_PLANNING_MUST_BE_EXPLICITLY_SANCTIONED")
        # v1 has no lossless same-K historical/current representation.  This policy
        # type cannot override that structural fact.
        if self.supersession_representation_sanctioned is not False:
            raise ValueError("V1_SUPERSESSION_REPRESENTATION_NOT_AVAILABLE")
        _false(self.store_mutation_authorized, "STORE_MUTATION_AUTHORIZED")
        _false(self.write_effect_authorized, "WRITE_EFFECT_AUTHORIZED")
        _false(self.semantic_authority, "SEMANTIC_AUTHORITY")

    @property
    def policy_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "policy": asdict(self)})


@dataclass(frozen=True)
class WriteResolverExpectationV1:
    """Independent expectation for the resolver/currentness boundary."""

    resolver_ref: str
    resolver_generation: str
    source_currentness_ref: str
    source_currentness_generation: str
    subject_key: str
    proposed_evidence_generation_key: str
    candidate_id: str
    store_ref: str
    store_generation: str
    store_sha256: str
    authority: bool = False

    def validate(self) -> None:
        for value, name in (
            (self.resolver_ref, "RESOLVER_REF"),
            (self.resolver_generation, "RESOLVER_GENERATION"),
            (self.source_currentness_ref, "SOURCE_CURRENTNESS_REF"),
            (self.source_currentness_generation, "SOURCE_CURRENTNESS_GENERATION"),
            (self.store_ref, "STORE_REF"),
            (self.store_generation, "STORE_GENERATION"),
        ):
            _text(value, name)
        _sha256(self.subject_key, "SUBJECT_KEY")
        _sha256(self.proposed_evidence_generation_key, "PROPOSED_EVIDENCE_GENERATION_KEY")
        _sha256(self.candidate_id, "CANDIDATE_ID")
        _sha256(self.store_sha256, "STORE_SHA256")
        _false(self.authority, "EXPECTATION_AUTHORITY")

    @property
    def expectation_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "expectation": asdict(self)})


@dataclass(frozen=True)
class ResolvedWriteAdmissionEvidenceV1:
    """Resolver-produced evidence; caller booleans alone never earn admission."""

    resolver_ref: str
    resolver_generation: str
    source_currentness_ref: str
    source_currentness_generation: str
    subject_key: str
    proposed_evidence_generation_key: str
    candidate_id: str
    store_ref: str
    store_generation: str
    store_sha256: str
    existing_evidence_generation_key: str | None
    supersession_relation: SupersessionRelation
    proposed_source_current: bool
    observed_store_current: bool
    resolved_admitted: bool
    evidence_ref: str
    authority: bool = False
    write_effect_authorized: bool = False

    def validate(self) -> None:
        for value, name in (
            (self.resolver_ref, "RESOLVER_REF"),
            (self.resolver_generation, "RESOLVER_GENERATION"),
            (self.source_currentness_ref, "SOURCE_CURRENTNESS_REF"),
            (self.source_currentness_generation, "SOURCE_CURRENTNESS_GENERATION"),
            (self.store_ref, "STORE_REF"),
            (self.store_generation, "STORE_GENERATION"),
            (self.evidence_ref, "EVIDENCE_REF"),
        ):
            _text(value, name)
        _sha256(self.subject_key, "SUBJECT_KEY")
        _sha256(self.proposed_evidence_generation_key, "PROPOSED_EVIDENCE_GENERATION_KEY")
        _sha256(self.candidate_id, "CANDIDATE_ID")
        _sha256(self.store_sha256, "STORE_SHA256")
        if self.existing_evidence_generation_key is not None:
            _sha256(self.existing_evidence_generation_key, "EXISTING_EVIDENCE_GENERATION_KEY")
        if not isinstance(self.supersession_relation, SupersessionRelation):
            raise ValueError("SUPERSESSION_RELATION_MUST_BE_TYPED")
        for field in ("proposed_source_current", "observed_store_current", "resolved_admitted"):
            if type(getattr(self, field)) is not bool:
                raise ValueError(f"{field.upper()}_MUST_BE_BOOL")
        _false(self.authority, "EVIDENCE_AUTHORITY")
        _false(self.write_effect_authorized, "EVIDENCE_WRITE_EFFECT_AUTHORIZED")

    @property
    def evidence_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "evidence": asdict(self)})


@dataclass(frozen=True)
class CoordinateMemoryWriteAdmissionV1:
    disposition: WriteAdmissionDisposition
    reason_code: str
    store_ref: str
    observed_store_generation: str
    observed_store_sha256: str
    semantic_key: str
    proposed_evidence_generation_key: str
    proposed_value_digest: str
    candidate_id: str
    schema_policy_digest: str | None
    resolver_expectation_digest: str | None
    resolution_evidence_digest: str | None
    existing_value_digest: str | None = None
    existing_evidence_generation_key: str | None = None
    proposed_row: Mapping[str, Any] | None = None
    writer_execution_required: bool = True
    canonical_writer_missing: bool = True
    store_mutated: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    semantic_truth_granted: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    schema: str = SCHEMA

    def validate(self) -> None:
        if not isinstance(self.disposition, WriteAdmissionDisposition):
            raise ValueError("WRITE_DISPOSITION_MUST_BE_TYPED")
        _text(self.reason_code, "REASON_CODE")
        _text(self.store_ref, "STORE_REF")
        _text(self.observed_store_generation, "OBSERVED_STORE_GENERATION")
        _sha256(self.observed_store_sha256, "OBSERVED_STORE_SHA256")
        _sha256(self.semantic_key, "SEMANTIC_KEY")
        _sha256(self.proposed_evidence_generation_key, "PROPOSED_EVIDENCE_GENERATION_KEY")
        _sha256(self.proposed_value_digest, "PROPOSED_VALUE_DIGEST")
        _sha256(self.candidate_id, "CANDIDATE_ID")
        if self.schema_policy_digest is not None:
            _sha256(self.schema_policy_digest, "SCHEMA_POLICY_DIGEST")
        if self.resolver_expectation_digest is not None:
            _sha256(self.resolver_expectation_digest, "RESOLVER_EXPECTATION_DIGEST")
        if self.resolution_evidence_digest is not None:
            _sha256(self.resolution_evidence_digest, "RESOLUTION_EVIDENCE_DIGEST")
        if self.existing_value_digest is not None:
            _text(self.existing_value_digest, "EXISTING_VALUE_DIGEST")
        if self.existing_evidence_generation_key is not None:
            _sha256(self.existing_evidence_generation_key, "EXISTING_EVIDENCE_GENERATION_KEY")
        if self.writer_execution_required is not True or self.canonical_writer_missing is not True:
            raise ValueError("CANONICAL_WRITER_MUST_REMAIN_DOWNSTREAM")
        for field in (
            "store_mutated",
            "write_authority",
            "effect_authority",
            "semantic_truth_granted",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            _false(getattr(self, field), field.upper())
        if self.schema != SCHEMA:
            raise ValueError("WRITE_ADMISSION_SCHEMA_MISMATCH")

    @property
    def receipt_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "admission": asdict(self)})


def _candidate_ceiling_ok(candidate: CoordinateMemoryCandidateV2) -> bool:
    return all(
        (
            candidate.schema == CANDIDATE_SCHEMA,
            candidate.candidate_only is True,
            candidate.store_mutated is False,
            candidate.writer_admission_required is True,
            candidate.source_currentness_revalidation_at_write_required is True,
            candidate.existing_generation_check_at_write_required is True,
            candidate.supersession_resolution_at_write_required is True,
            candidate.semantic_truth_granted is False,
            candidate.instruction_authority is False,
            candidate.write_authority is False,
            candidate.effect_authority is False,
            candidate.semantic_k27_authority is False,
            candidate.native_private_transformer_kv_accessed is False,
        )
    )


def _parse_snapshot(snapshot_bytes: bytes) -> tuple[str, str, list[Mapping[str, Any]]]:
    if not isinstance(snapshot_bytes, (bytes, bytearray)):
        raise TypeError("SNAPSHOT_BYTES_REQUIRED")
    try:
        parsed = json.loads(bytes(snapshot_bytes).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("STORE_SNAPSHOT_MUST_BE_UTF8_JSON") from exc
    schema = parsed.get("schema", {})
    if isinstance(schema, str):
        name = schema
        version = parsed.get("version")
    elif isinstance(schema, Mapping):
        name = schema.get("name")
        version = schema.get("version")
    else:
        raise ValueError("STORE_SCHEMA_INVALID")
    rows = parsed.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ValueError("STORE_ROWS_MUST_BE_OBJECT_LIST")
    return str(name), str(version), list(rows)


def _resolution_matches(
    *,
    candidate: CoordinateMemoryCandidateV2,
    store_ref: str,
    store_generation: str,
    store_sha256: str,
    expectation: WriteResolverExpectationV1,
    evidence: ResolvedWriteAdmissionEvidenceV1,
) -> bool:
    expectation.validate()
    evidence.validate()
    return all(
        (
            evidence.resolver_ref == expectation.resolver_ref,
            evidence.resolver_generation == expectation.resolver_generation,
            evidence.source_currentness_ref == expectation.source_currentness_ref,
            evidence.source_currentness_generation == expectation.source_currentness_generation,
            evidence.subject_key == expectation.subject_key == candidate.semantic_key,
            evidence.proposed_evidence_generation_key
            == expectation.proposed_evidence_generation_key
            == candidate.evidence_generation_key,
            evidence.candidate_id == expectation.candidate_id == candidate.candidate_id,
            evidence.store_ref == expectation.store_ref == store_ref,
            evidence.store_generation == expectation.store_generation == store_generation,
            evidence.store_sha256 == expectation.store_sha256 == store_sha256,
        )
    )


def admit_coordinate_memory_write(
    *,
    candidate: CoordinateMemoryCandidateV2,
    snapshot_bytes: bytes,
    store_ref: str,
    store_generation: str,
    expected_store_sha256: str,
    schema_policy: CoordinateMemorySchemaPolicyV1 | None,
    resolver_expectation: WriteResolverExpectationV1 | None,
    resolution_evidence: ResolvedWriteAdmissionEvidenceV1 | None,
) -> CoordinateMemoryWriteAdmissionV1:
    """Inspect current state and emit a non-writing INSERT/NOOP/HOLD plan."""

    if not isinstance(candidate, CoordinateMemoryCandidateV2):
        raise TypeError("COORDINATE_MEMORY_CANDIDATE_V2_REQUIRED")
    _text(store_ref, "STORE_REF")
    _text(store_generation, "STORE_GENERATION")
    expected_sha = _sha256(expected_store_sha256, "EXPECTED_STORE_SHA256")
    actual_sha = hashlib.sha256(bytes(snapshot_bytes)).hexdigest()

    common = dict(
        store_ref=store_ref,
        observed_store_generation=store_generation,
        observed_store_sha256=actual_sha,
        semantic_key=candidate.semantic_key,
        proposed_evidence_generation_key=candidate.evidence_generation_key,
        proposed_value_digest=candidate.proposed_value_digest,
        candidate_id=candidate.candidate_id,
        schema_policy_digest=None if schema_policy is None else schema_policy.policy_digest,
        resolver_expectation_digest=None
        if resolver_expectation is None
        else resolver_expectation.expectation_digest,
        resolution_evidence_digest=None
        if resolution_evidence is None
        else resolution_evidence.evidence_digest,
    )

    def result(disposition: WriteAdmissionDisposition, reason: str, **extra: Any) -> CoordinateMemoryWriteAdmissionV1:
        receipt = CoordinateMemoryWriteAdmissionV1(
            disposition=disposition,
            reason_code=reason,
            **common,
            **extra,
        )
        receipt.validate()
        return receipt

    if not _candidate_ceiling_ok(candidate):
        return result(
            WriteAdmissionDisposition.HOLD_CANDIDATE_CEILING,
            "CANDIDATE_MUST_REMAIN_NONWRITING_AND_REVALIDATION_BOUND",
        )

    if actual_sha != expected_sha:
        return result(
            WriteAdmissionDisposition.HOLD_STORE_INTEGRITY,
            "OBSERVED_STORE_SHA256_DIFFERS_FROM_EXPECTATION",
        )

    name, version, rows = _parse_snapshot(snapshot_bytes)
    if name != STORE_SCHEMA_NAME or version != STORE_SCHEMA_VERSION:
        return result(
            WriteAdmissionDisposition.HOLD_STORE_STALE,
            "OBSERVED_STORE_SCHEMA_GENERATION_NOT_SUPPORTED",
        )

    if schema_policy is None:
        return result(
            WriteAdmissionDisposition.HOLD_SCHEMA_POLICY,
            "SCHEMA_OWNER_PLANNING_SANCTION_REQUIRED",
        )
    try:
        schema_policy.validate()
    except ValueError:
        return result(
            WriteAdmissionDisposition.HOLD_SCHEMA_POLICY,
            "SCHEMA_OWNER_POLICY_NOT_COMPATIBLE_WITH_V1_ADMISSION",
        )

    if resolver_expectation is None or resolution_evidence is None:
        return result(
            WriteAdmissionDisposition.HOLD_CURRENTNESS_EVIDENCE_REQUIRED,
            "INDEPENDENT_WRITE_CURRENTNESS_RESOLUTION_REQUIRED",
        )
    if not _resolution_matches(
        candidate=candidate,
        store_ref=store_ref,
        store_generation=store_generation,
        store_sha256=actual_sha,
        expectation=resolver_expectation,
        evidence=resolution_evidence,
    ):
        return result(
            WriteAdmissionDisposition.HOLD_CURRENTNESS_EVIDENCE_MISMATCH,
            "RESOLVED_WRITE_EVIDENCE_DOES_NOT_MATCH_INDEPENDENT_EXPECTATION",
        )
    if not (
        resolution_evidence.proposed_source_current
        and resolution_evidence.observed_store_current
        and resolution_evidence.resolved_admitted
    ):
        return result(
            WriteAdmissionDisposition.HOLD_CURRENTNESS_REOPEN,
            "PROPOSED_SOURCE_AND_STORE_MUST_BOTH_BE_INDEPENDENTLY_CURRENT",
        )

    same_key = [row for row in rows if row.get("K") == candidate.semantic_key]
    if len(same_key) > 1:
        return result(
            WriteAdmissionDisposition.HOLD_EXISTING_KEY_AMBIGUOUS,
            "V1_REQUIRES_UNIQUE_SEMANTIC_KEY",
        )

    if not same_key:
        if resolution_evidence.existing_evidence_generation_key is not None:
            return result(
                WriteAdmissionDisposition.HOLD_CURRENTNESS_EVIDENCE_MISMATCH,
                "RESOLVER_REPORTS_EXISTING_GENERATION_BUT_SNAPSHOT_HAS_NO_SUBJECT_ROW",
            )
        if resolution_evidence.supersession_relation is not SupersessionRelation.NONE:
            return result(
                WriteAdmissionDisposition.HOLD_CURRENTNESS_EVIDENCE_MISMATCH,
                "ABSENT_SUBJECT_CANNOT_CARRY_SUPERSESSION_RELATION",
            )
        return result(
            WriteAdmissionDisposition.INSERT_NEW_PLAN,
            "ABSENT_STABLE_SUBJECT_EXACT_CURRENTNESS_AND_SCHEMA_POLICY_ADMITTED",
            proposed_row=candidate.proposed_row,
        )

    row = same_key[0]
    value = row.get("V")
    if not isinstance(value, Mapping):
        return result(
            WriteAdmissionDisposition.HOLD_EXISTING_GENERATION_UNRESOLVED,
            "EXISTING_ROW_VALUE_NOT_STRUCTURED",
        )
    cell = value.get("cell")
    if not isinstance(cell, Mapping):
        return result(
            WriteAdmissionDisposition.HOLD_EXISTING_GENERATION_UNRESOLVED,
            "EXISTING_ROW_CELL_NOT_STRUCTURED",
        )
    existing_generation = cell.get("external_evidence_generation_key")
    if not isinstance(existing_generation, str):
        return result(
            WriteAdmissionDisposition.HOLD_EXISTING_GENERATION_UNRESOLVED,
            "EXISTING_ROW_LACKS_EXTERNAL_EVIDENCE_GENERATION_KEY",
            existing_value_digest=str(value.get("digest")) if value.get("digest") is not None else None,
        )
    try:
        existing_generation = _sha256(existing_generation, "EXISTING_EVIDENCE_GENERATION_KEY")
    except ValueError:
        return result(
            WriteAdmissionDisposition.HOLD_EXISTING_GENERATION_UNRESOLVED,
            "EXISTING_EVIDENCE_GENERATION_KEY_INVALID",
            existing_value_digest=str(value.get("digest")) if value.get("digest") is not None else None,
        )
    existing_digest = value.get("digest")
    if not isinstance(existing_digest, str) or not existing_digest:
        return result(
            WriteAdmissionDisposition.HOLD_ROW_IDENTITY_CONFLICT,
            "EXISTING_VALUE_DIGEST_REQUIRED",
            existing_evidence_generation_key=existing_generation,
        )

    if resolution_evidence.existing_evidence_generation_key != existing_generation:
        return result(
            WriteAdmissionDisposition.HOLD_CURRENTNESS_EVIDENCE_MISMATCH,
            "RESOLVED_EXISTING_GENERATION_DOES_NOT_MATCH_SNAPSHOT",
            existing_value_digest=existing_digest,
            existing_evidence_generation_key=existing_generation,
        )

    if existing_generation == candidate.evidence_generation_key:
        if resolution_evidence.supersession_relation is not SupersessionRelation.IDENTICAL_GENERATION:
            return result(
                WriteAdmissionDisposition.HOLD_SUPERSESSION_RELATION_REQUIRED,
                "IDENTICAL_GENERATION_RELATION_MUST_BE_EXPLICIT",
                existing_value_digest=existing_digest,
                existing_evidence_generation_key=existing_generation,
            )
        if existing_digest != candidate.proposed_value_digest or row != candidate.proposed_row:
            return result(
                WriteAdmissionDisposition.HOLD_ROW_IDENTITY_CONFLICT,
                "SAME_EVIDENCE_GENERATION_HAS_DIFFERENT_ROW_REPRESENTATION",
                existing_value_digest=existing_digest,
                existing_evidence_generation_key=existing_generation,
            )
        return result(
            WriteAdmissionDisposition.NOOP_IDENTICAL_PLAN,
            "EXACT_SAME_SUBJECT_GENERATION_AND_ROW_ALREADY_MATERIALIZED",
            existing_value_digest=existing_digest,
            existing_evidence_generation_key=existing_generation,
        )

    if resolution_evidence.supersession_relation is not SupersessionRelation.PROPOSED_SUPERSEDES_EXISTING:
        return result(
            WriteAdmissionDisposition.HOLD_SUPERSESSION_RELATION_REQUIRED,
            "DIFFERENT_EVIDENCE_GENERATIONS_REQUIRE_EXTERNAL_SUPERSESSION_RESOLUTION",
            existing_value_digest=existing_digest,
            existing_evidence_generation_key=existing_generation,
        )

    # Even exact externally resolved supersession cannot be executed losslessly in
    # schema v1: duplicate K is forbidden, but preserving the old row with a
    # successor and adding the new row would require two rows with the same K.
    return result(
        WriteAdmissionDisposition.HOLD_SUPERSESSION_REPRESENTATION_REQUIRED,
        "V1_UNIQUE_K_CANNOT_RETAIN_OLD_HISTORY_AND_INSTALL_NEW_CURRENT_GENERATION",
        existing_value_digest=existing_digest,
        existing_evidence_generation_key=existing_generation,
    )
