#!/usr/bin/env python3
"""Current EKI owner -> WP03 coordinate-memory candidate projection.

D0 / HS1 / NONPROMOTING.

Semantic parents:
* PR #731: source-resolvable external knowledge nodes with stable subject_key,
  mutable evidence_generation_key, explicit CURRENT_REFERENCE state, validation
  fingerprint, L0..L4 hydration and routing-only coordinate projections.
* PR #728: source-ready reader for aura-coordinate-memory-kv-v1@1.0.0.

This module projects one CURRENT_REFERENCE/L4 node into a deterministic candidate
row compatible with the WP03 reader. It never mutates the persistent store.
A canonical writer must revalidate currentness, inspect any existing generation
for the same subject key, resolve supersession, and independently admit the write.

K27 (x,y,z) may be carried as a WP03 placement hint because the current #731
projection and #728 request use the same bounded 3-tuple shape. Placement remains
routing metadata only; it never replaces the stable subject key or grants truth,
currentness, instruction, write, effect, or semantic K27 authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping
from urllib.parse import urlparse

from tools import aura_external_knowledge_ingress as eki
from tools.aura_external_cognition_resolve_adapter import (
    READER_IMPLEMENTATION,
    SCHEMA_NAME as STORE_SCHEMA_NAME,
    SCHEMA_VERSION as STORE_SCHEMA_VERSION,
)

SCHEMA = "AURA-EKI-WP03-COORDINATE-MEMORY-CANDIDATE-v2"
READY = "COORDINATE_MEMORY_CANDIDATE_READY"
HOLD_CURRENT = "HOLD_CURRENT_EXTERNAL_REFERENCE_REQUIRED"
HOLD_L4 = "HOLD_EXACT_L4_HYDRATION_REQUIRED"
HOLD_SIZE = "HOLD_COORDINATE_MEMORY_STANDING_BOUND_EXCEEDED"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _httpish_uri(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "git", "doi", "arxiv", "hf"}:
        raise ValueError(f"{name}_UNSUPPORTED_SCHEME")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError(f"{name}_HOST_REQUIRED")
    return value


def _validate_nonpromotion(node: eki.ExternalKnowledgeNode) -> None:
    node.validate()
    if node.schema != eki.SCHEMA:
        raise ValueError("EXACT_CURRENT_EKI_SCHEMA_REQUIRED")
    forbidden = (
        node.code_execution_authorized,
        node.model_download_authorized,
        node.remote_code_authorized,
        node.network_write_authorized,
        node.provider_effect_authorized,
        node.semantic_k27_authority,
        node.native_private_transformer_kv_accessed,
    )
    if any(value is not False for value in forbidden):
        raise ValueError("EKI_NODE_CLAIM_CEILING_WIDENED")
    if node.tool_use_requires_separate_admission is not True:
        raise ValueError("TOOL_USE_MUST_REMAIN_SEPARATELY_ADMITTED")


def _placement(node: eki.ExternalKnowledgeNode) -> tuple[int, int, int]:
    node.coordinate.validate()
    xyz = node.coordinate.k27_xyz
    if len(xyz) != 3 or any(type(v) is not int or v < 0 or v >= 27 for v in xyz):
        raise ValueError("EKI_K27_XYZ_INVALID")
    return tuple(xyz)


@dataclass(frozen=True)
class CoordinateMemoryCandidateV2:
    schema: str
    semantic_key: str
    evidence_generation_key: str
    external_node_digest: str
    validation_fingerprint: str
    source_provider: str
    source_kind: str
    source_uri: str
    exact_reopen_uri: str
    content_sha256: str
    wp03_placement_hint: tuple[int, int, int]
    proposed_cell: Mapping[str, Any]
    proposed_standing: str
    proposed_reopen: Mapping[str, Any]
    proposed_successor: None
    proposed_value_digest: str
    proposed_row_digest: str
    store_schema_name: str = STORE_SCHEMA_NAME
    store_schema_version: str = STORE_SCHEMA_VERSION
    intended_reader: str = READER_IMPLEMENTATION
    candidate_only: bool = True
    store_mutated: bool = False
    writer_admission_required: bool = True
    source_currentness_revalidation_at_write_required: bool = True
    existing_generation_check_at_write_required: bool = True
    supersession_resolution_at_write_required: bool = True
    semantic_truth_granted: bool = False
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def candidate_id(self) -> str:
        return _sha({"domain": SCHEMA, "candidate": asdict(self)})

    @property
    def proposed_row(self) -> Mapping[str, Any]:
        return {
            "K": self.semantic_key,
            "V": {
                "cell": dict(self.proposed_cell),
                "digest": self.proposed_value_digest,
                "standing": self.proposed_standing,
                "reopen": dict(self.proposed_reopen),
                "successor": None,
            },
        }


@dataclass(frozen=True)
class CoordinateMemoryCandidateDecisionV2:
    schema: str
    disposition: str
    reason_code: str
    subject_key: str
    evidence_generation_key: str
    external_node_digest: str
    candidate: CoordinateMemoryCandidateV2 | None
    stable_subject_key_preserved: bool
    evidence_generation_separate_from_subject: bool
    k27_carried_as_routing_placement_only: bool
    store_mutated: bool = False
    write_authority: bool = False
    semantic_truth_granted: bool = False
    effect_authority: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "decision": asdict(self)})


def project_external_knowledge_candidate(
    *,
    node: eki.ExternalKnowledgeNode,
    max_standing_chars: int = 4096,
) -> CoordinateMemoryCandidateDecisionV2:
    """Project one exact current EKI node into a non-writing WP03 candidate."""
    if isinstance(max_standing_chars, bool) or not isinstance(max_standing_chars, int) or max_standing_chars <= 0:
        raise ValueError("MAX_STANDING_CHARS_MUST_BE_POSITIVE_INT")
    if not isinstance(node, eki.ExternalKnowledgeNode):
        raise TypeError("EXTERNAL_KNOWLEDGE_NODE_REQUIRED")
    _validate_nonpromotion(node)

    subject_key = _sha256(node.subject_key, "EKI_SUBJECT_KEY")
    evidence_key = _sha256(node.evidence_generation_key, "EKI_EVIDENCE_GENERATION_KEY")
    node_digest = _sha256(node.node_digest, "EKI_NODE_DIGEST")
    validation = _sha256(node.validation_fingerprint, "EKI_VALIDATION_FINGERPRINT")

    common = dict(
        schema=SCHEMA,
        subject_key=subject_key,
        evidence_generation_key=evidence_key,
        external_node_digest=node_digest,
        stable_subject_key_preserved=True,
        evidence_generation_separate_from_subject=True,
        k27_carried_as_routing_placement_only=True,
    )

    if (
        node.knowledge_state is not eki.KnowledgeState.CURRENT_REFERENCE
        or node.read_only_reference_admissible is not True
    ):
        return CoordinateMemoryCandidateDecisionV2(
            disposition=HOLD_CURRENT,
            reason_code="PERSISTENT_CANDIDATE_REQUIRES_CURRENT_READ_ONLY_REFERENCE",
            candidate=None,
            **common,
        )

    levels = tuple(item.level for item in node.hydration)
    if levels != ("L0", "L1", "L2", "L3", "L4"):
        return CoordinateMemoryCandidateDecisionV2(
            disposition=HOLD_L4,
            reason_code="PERSISTENT_CANDIDATE_REQUIRES_CONTIGUOUS_EXACT_L0_TO_L4_HYDRATION",
            candidate=None,
            **common,
        )

    exact_uri = _httpish_uri(node.observation.exact_source_uri, "EKI_EXACT_SOURCE_URI")
    content_sha = _sha256(node.observation.content_digest, "EKI_CONTENT_DIGEST")
    placement = _placement(node)

    standing_payload = {
        "subject_key": subject_key,
        "evidence_generation_key": evidence_key,
        "external_node_digest": node_digest,
        "validation_fingerprint": validation,
        "provider": node.subject.provider,
        "source_kind": node.subject.source_kind,
        "canonical_id": node.subject.canonical_id,
        "canonical_uri": node.subject.canonical_uri,
        "knowledge_state": node.knowledge_state.value,
        "hydration": [
            {
                "level": item.level,
                "data": dict(item.data),
                "derivation_method": item.derivation_method,
                "source_excerpt_digest": item.source_excerpt_digest,
                "digest": item.digest,
            }
            for item in node.hydration
        ],
    }
    standing = _canonical(standing_payload).decode("ascii")
    if len(standing) > max_standing_chars:
        return CoordinateMemoryCandidateDecisionV2(
            disposition=HOLD_SIZE,
            reason_code="SOURCE_ADMITTED_STANDING_EXCEEDS_COORDINATE_MEMORY_BOUND",
            candidate=None,
            **common,
        )

    cell = {
        "external_subject_key": subject_key,
        "external_evidence_generation_key": evidence_key,
        "external_node_digest": node_digest,
        "validation_fingerprint": validation,
        "provider": node.subject.provider,
        "source_kind": node.subject.source_kind,
        "canonical_id": node.subject.canonical_id,
        "canonical_uri": node.subject.canonical_uri,
        "knowledge_state": node.knowledge_state.value,
        "content_sha256": content_sha,
        "k27_xyz": list(placement),
        "k27_routing_only": True,
        "subject_trits_13d": list(node.coordinate.subject_trits_13d),
        "evidence_trits_13d": list(node.coordinate.evidence_trits_13d),
        "toroidal_xyz_mod27": list(node.coordinate.toroidal_xyz_mod27),
        "tesseract_vertex": list(node.coordinate.tesseract_vertex),
        "invalidation_triggers": list(node.invalidation_triggers),
        "tool_use_requires_separate_admission": True,
    }
    reopen = {
        "uri": exact_uri,
        "content_sha256": content_sha,
        "subject_key": subject_key,
        "evidence_generation_key": evidence_key,
        "external_node_digest": node_digest,
        "validation_fingerprint": validation,
    }
    value_digest = _sha(
        {
            "domain": "AURA-EKI-WP03-PROPOSED-VALUE-v2",
            "cell": cell,
            "standing": standing,
            "reopen": reopen,
            "successor": None,
        }
    )
    row_digest = _sha(
        {
            "domain": "AURA-EKI-WP03-PROPOSED-ROW-v2",
            "K": subject_key,
            "V_digest": value_digest,
            "evidence_generation_key": evidence_key,
        }
    )
    candidate = CoordinateMemoryCandidateV2(
        schema=SCHEMA,
        semantic_key=subject_key,
        evidence_generation_key=evidence_key,
        external_node_digest=node_digest,
        validation_fingerprint=validation,
        source_provider=node.subject.provider,
        source_kind=node.subject.source_kind,
        source_uri=node.subject.canonical_uri,
        exact_reopen_uri=exact_uri,
        content_sha256=content_sha,
        wp03_placement_hint=placement,
        proposed_cell=cell,
        proposed_standing=standing,
        proposed_reopen=reopen,
        proposed_successor=None,
        proposed_value_digest=value_digest,
        proposed_row_digest=row_digest,
    )
    return CoordinateMemoryCandidateDecisionV2(
        disposition=READY,
        reason_code="CURRENT_EXACT_EKI_NODE_PROJECTED_WITHOUT_STORE_MUTATION",
        candidate=candidate,
        **common,
    )
