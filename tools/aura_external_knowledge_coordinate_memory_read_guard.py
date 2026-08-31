#!/usr/bin/env python3
"""EKI-R1: mandatory read-time currentness for EKI-derived WP03 candidates.

D0 / HS1 / NONPROMOTING / W3 ADDENDUM.

PR #735 owns projection of CURRENT_REFERENCE external knowledge into a non-writing
WP03-compatible candidate.  WP03 / PR #728 owns candidate-only snapshot reads.
This addendum owns only the missing use-boundary relation:

    current-at-projection/write != current-at-read.

PR #735's proposed row records ``knowledge_state=CURRENT_REFERENCE`` as historical
projection provenance.  That stored field is never accepted as a freshness witness.
Every EKI-derived read request produced here *must* require the ``source`` currentness
axis, and ``NOT_REQUIRED`` is invalid for an explicitly required source axis.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from tools.aura_external_cognition_resolve_adapter import (
    CurrentnessStatus,
    ExternalCognitionReadRequestV1,
    ExternalCognitionResolveAdapterV1,
    ReadValidationContextV1,
    ResolveDisposition,
)
from tools.aura_external_knowledge_coordinate_memory_candidate import CoordinateMemoryCandidateV2

SCHEMA = "AURA-EKI-WP03-READ-CURRENTNESS-GUARD-v1"
PR735_HEAD = "89a66cdb972d3eab19c9408356b7061d1529947d"
WP03_SEMANTIC_HEAD = "9865c42f3ada2520141bd2fe30a439ce160ce2f8"
SOURCE_AXIS = "source"
REQUIRED_CURRENTNESS_AXES = (SOURCE_AXIS,)
HEX = frozenset("0123456789abcdef")


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in HEX for ch in value.lower()):
        raise ValueError(f"{name}_MUST_BE_EXACT_SHA256_HEX")
    return value.lower()


def _validate_candidate(candidate: CoordinateMemoryCandidateV2) -> None:
    if not isinstance(candidate, CoordinateMemoryCandidateV2):
        raise TypeError("EKI_READ_COORDINATE_MEMORY_CANDIDATE_REQUIRED")
    if candidate.schema != "AURA-EKI-WP03-COORDINATE-MEMORY-CANDIDATE-v2":
        raise ValueError("EKI_READ_CANDIDATE_SCHEMA_MISMATCH")
    if candidate.candidate_only is not True or candidate.store_mutated is not False:
        raise ValueError("EKI_READ_REQUIRES_NONWRITING_CANDIDATE")
    if candidate.source_currentness_revalidation_at_write_required is not True:
        raise ValueError("EKI_READ_PARENT_CURRENTNESS_OBLIGATION_MISSING")
    if candidate.writer_admission_required is not True:
        raise ValueError("EKI_READ_WRITER_ADMISSION_CEILING_MISSING")
    if any(
        value is not False
        for value in (
            candidate.semantic_truth_granted,
            candidate.instruction_authority,
            candidate.write_authority,
            candidate.effect_authority,
            candidate.semantic_k27_authority,
            candidate.native_private_transformer_kv_accessed,
        )
    ):
        raise ValueError("EKI_READ_CANDIDATE_AUTHORITY_WIDENED")
    if candidate.proposed_row.get("K") != candidate.semantic_key:
        raise ValueError("EKI_READ_ROW_KEY_MISMATCH")
    value = candidate.proposed_row.get("V")
    if not isinstance(value, dict) or value.get("digest") != candidate.proposed_value_digest:
        raise ValueError("EKI_READ_ROW_VALUE_MISMATCH")

    # PR735 persists CURRENT_REFERENCE as projection provenance.  Pin that fact so
    # this guard cannot silently reinterpret another field as currentness.
    cell = value.get("cell")
    if not isinstance(cell, dict) or cell.get("knowledge_state") != "CURRENT_REFERENCE":
        raise ValueError("EKI_READ_PROJECTED_KNOWLEDGE_STATE_REQUIRED")
    try:
        standing = json.loads(value.get("standing"))
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("EKI_READ_PROJECTED_STANDING_MUST_BE_JSON") from exc
    if standing.get("knowledge_state") != "CURRENT_REFERENCE":
        raise ValueError("EKI_READ_STANDING_PROJECTED_STATE_REQUIRED")


@dataclass(frozen=True)
class EKIReadCurrentnessContractV1:
    schema: str
    pr735_head: str
    wp03_semantic_head: str
    semantic_key: str
    evidence_generation_key: str
    expected_value_digest: str
    required_currentness_axes: tuple[str, ...]
    persisted_knowledge_state_is_historical_projection_only: bool
    persisted_currentness_witness: bool
    candidate_only: bool
    instruction_authority: bool
    write_authority: bool
    effect_authority: bool
    request: ExternalCognitionReadRequestV1

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("EKI_READ_CONTRACT_SCHEMA_MISMATCH")
        if self.pr735_head != PR735_HEAD or self.wp03_semantic_head != WP03_SEMANTIC_HEAD:
            raise ValueError("EKI_READ_PARENT_GENERATION_MISMATCH")
        if self.required_currentness_axes != REQUIRED_CURRENTNESS_AXES:
            raise ValueError("EKI_READ_SOURCE_CURRENTNESS_AXIS_MANDATORY")
        if self.persisted_knowledge_state_is_historical_projection_only is not True:
            raise ValueError("EKI_READ_PROJECTED_STATE_MUST_BE_HISTORICAL_ONLY")
        if self.persisted_currentness_witness is not False:
            raise ValueError("EKI_READ_PERSISTED_ROW_CANNOT_WITNESS_CURRENTNESS")
        if self.candidate_only is not True:
            raise ValueError("EKI_READ_MUST_REMAIN_CANDIDATE_ONLY")
        if any(value is not False for value in (self.instruction_authority, self.write_authority, self.effect_authority)):
            raise ValueError("EKI_READ_CONTRACT_CANNOT_WIDEN_AUTHORITY")
        if self.request.semantic_key != self.semantic_key:
            raise ValueError("EKI_READ_REQUEST_KEY_MISMATCH")
        if self.request.expected_value_digest != self.expected_value_digest:
            raise ValueError("EKI_READ_REQUEST_VALUE_DIGEST_MISMATCH")
        if self.request.required_currentness_axes != REQUIRED_CURRENTNESS_AXES:
            raise ValueError("EKI_READ_REQUEST_SOURCE_CURRENTNESS_AXIS_MANDATORY")
        if self.request.responsibility != "SOURCE_BOUND_COORDINATE_MEMORY":
            raise ValueError("EKI_READ_MODEL_PREFIX_KV_WRONG_OWNER")


def build_currentness_required_read_contract(
    *,
    candidate: CoordinateMemoryCandidateV2,
    store_ref: str,
    store_generation: str,
    store_sha256: str,
    consumer_ref: str,
    consumer_generation: str,
    evidence_domain: str,
    principal: str,
    max_standing_chars: int = 4096,
) -> EKIReadCurrentnessContractV1:
    """Build the only lawful WP03 read request for an EKI-derived candidate."""
    _validate_candidate(candidate)
    if isinstance(max_standing_chars, bool) or not isinstance(max_standing_chars, int) or max_standing_chars <= 0:
        raise ValueError("EKI_READ_MAX_STANDING_CHARS_MUST_BE_POSITIVE_INT")
    request = ExternalCognitionReadRequestV1(
        store_ref=_required(store_ref, "EKI_READ_STORE_REF"),
        expected_store_generation=_required(store_generation, "EKI_READ_STORE_GENERATION"),
        expected_store_sha256=_sha256(store_sha256, "EKI_READ_STORE_SHA256"),
        semantic_key=candidate.semantic_key,
        expected_value_digest=candidate.proposed_value_digest,
        consumer_ref=_required(consumer_ref, "EKI_READ_CONSUMER_REF"),
        consumer_generation=_required(consumer_generation, "EKI_READ_CONSUMER_GENERATION"),
        evidence_domain=_required(evidence_domain, "EKI_READ_EVIDENCE_DOMAIN"),
        principal=_required(principal, "EKI_READ_PRINCIPAL"),
        required_currentness_axes=REQUIRED_CURRENTNESS_AXES,
        max_standing_chars=max_standing_chars,
        placement_hint=candidate.wp03_placement_hint,
        responsibility="SOURCE_BOUND_COORDINATE_MEMORY",
    )
    contract = EKIReadCurrentnessContractV1(
        schema=SCHEMA,
        pr735_head=PR735_HEAD,
        wp03_semantic_head=WP03_SEMANTIC_HEAD,
        semantic_key=candidate.semantic_key,
        evidence_generation_key=candidate.evidence_generation_key,
        expected_value_digest=candidate.proposed_value_digest,
        required_currentness_axes=REQUIRED_CURRENTNESS_AXES,
        persisted_knowledge_state_is_historical_projection_only=True,
        persisted_currentness_witness=False,
        candidate_only=True,
        instruction_authority=False,
        write_authority=False,
        effect_authority=False,
        request=request,
    )
    contract.validate()
    return contract


def resolve_with_read_currentness(
    *,
    adapter: ExternalCognitionResolveAdapterV1,
    contract: EKIReadCurrentnessContractV1,
    context: ReadValidationContextV1,
):
    """Resolve only after enforcing an independently supplied source-currentness axis."""
    contract.validate()
    source_status = context.currentness.get(SOURCE_AXIS, CurrentnessStatus.UNKNOWN)
    if source_status is CurrentnessStatus.NOT_REQUIRED:
        raise ValueError("EKI_READ_REQUIRED_SOURCE_AXIS_CANNOT_BE_NOT_REQUIRED")
    receipt = adapter.resolve(contract.request, context)
    if receipt.disposition is ResolveDisposition.FOUND_VERIFIED:
        if receipt.candidate is None or receipt.candidate.source_currentness != CurrentnessStatus.RESOLVED_CURRENT.value:
            raise ValueError("EKI_READ_VERIFIED_CANDIDATE_REQUIRES_RESOLVED_CURRENT_SOURCE")
        if any(
            value is not False
            for value in (
                receipt.candidate.instruction_authority,
                receipt.candidate.write_authority,
                receipt.candidate.effect_authority,
            )
        ):
            raise ValueError("EKI_READ_VERIFIED_CANDIDATE_AUTHORITY_WIDENED")
    return receipt


LAWS = (
    "CURRENT_REFERENCE@Projection!=Current@Read",
    "PersistedKnowledgeState!=CurrentnessWitness",
    "EKIDerivedRead=>RequiredCurrentnessAxis(source)",
    "Required(source)+NOT_REQUIRED(source)=>FailClosed",
    "ReadTimeCurrentnessMustBeIndependentOfPersistedRow",
    "K27Placement!=SemanticIdentity!=SourceCurrentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
