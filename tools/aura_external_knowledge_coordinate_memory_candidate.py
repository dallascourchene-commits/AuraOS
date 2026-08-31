#!/usr/bin/env python3
"""EKI-1 -> WP03 coordinate-memory candidate projection.

D0 / HS1 / NONPROMOTING.

This relation consumes two independently owned planes:

* PR #730 / EKI-1 admits source-generation-bound external knowledge cards.
* PR #728 / WP03 defines the source-ready read contract for the existing
  ``aura-coordinate-memory-kv-v1@1.0.0`` store.

The missing relation is intentionally *not* a store writer.  It can project one
exact CURRENT L4 EKI card into a deterministic candidate row whose shape is
compatible with the WP03 reader, but a later canonical writer/currentness owner
must independently admit and mutate the persistent store.

Important boundaries:
- semantic identity stays the EKI semantic_id; source generation is separate;
- EKI's 27-trit locality key is preserved as routing metadata and is never
  cross-cast into WP03's optional 3-tuple placement_hint;
- READ_ONLY_REFERENCE_READY is not semantic truth or write authority;
- external standing remains evidence-only and cannot become instructions;
- this module never reads or mutates native/private transformer KV.
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

SCHEMA = "AURA-EKI-COORDINATE-MEMORY-CANDIDATE-v1"
READY = "COORDINATE_MEMORY_CANDIDATE_READY"
HOLD_CURRENT = "HOLD_CURRENT_EXTERNAL_GENERATION_REQUIRED"
HOLD_L4 = "HOLD_EXACT_L4_SOURCE_REQUIRED"
HOLD_AVAILABILITY = "HOLD_READ_ONLY_REFERENCE_AVAILABILITY_REQUIRED"
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


def _http_uri(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name}_MUST_BE_HTTP_URI")
    return value


def _k27_key(card: eki.ExternalKnowledgeCard) -> str:
    value = card.k27_locality
    if not isinstance(value, Mapping):
        raise ValueError("EKI_K27_LOCALITY_MAPPING_REQUIRED")
    if value.get("schema") != eki.K27_SCHEMA:
        raise ValueError("EKI_K27_SCHEMA_MISMATCH")
    trits = value.get("trits")
    prefix = value.get("operational_prefix")
    if not isinstance(trits, (tuple, list)) or len(trits) != 27:
        raise ValueError("EKI_K27_27_TRITS_REQUIRED")
    if any(type(v) is not int or v not in (0, 1, 2) for v in trits):
        raise ValueError("EKI_K27_TRITS_INVALID")
    if not isinstance(prefix, (tuple, list)) or tuple(trits[:13]) != tuple(prefix):
        raise ValueError("EKI_K27_OPERATIONAL_PREFIX_MISMATCH")
    if value.get("routing_only") is not True:
        raise ValueError("EKI_K27_MUST_BE_ROUTING_ONLY")
    if value.get("semantic_identity") not in (False, None) or value.get("authority") not in (False, None):
        raise ValueError("EKI_K27_CANNOT_MINT_IDENTITY_OR_AUTHORITY")
    return "".join(str(v) for v in trits)


def _validate_nonpromotion(card: eki.ExternalKnowledgeCard) -> None:
    if card.schema != eki.SCHEMA:
        raise ValueError("EXACT_EKI_CARD_SCHEMA_REQUIRED")
    if card.read_only_reference_authority is not True:
        raise ValueError("EKI_READ_ONLY_REFERENCE_AUTHORITY_REQUIRED")
    forbidden = (
        card.execution_authorized,
        card.provider_effect_authorized,
        card.semantic_k27_authority,
        card.native_private_transformer_kv_accessed,
        card.gate10_promoted,
        card.merge_deploy_spend_public_financial_human_effect_authorized,
    )
    if any(value is not False for value in forbidden):
        raise ValueError("EKI_CARD_CLAIM_CEILING_WIDENED")


@dataclass(frozen=True)
class CoordinateMemoryCandidateV1:
    schema: str
    semantic_key: str
    source_generation_id: str
    external_card_receipt_digest: str
    source_kind: str
    artifact_class: str
    source_uri: str
    exact_reopen_uri: str
    content_sha256: str
    eki_k27_locality_key: str
    wp03_placement_hint: None
    placement_mapping_required: bool
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
    source_revalidation_at_write_required: bool = True
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
class CoordinateMemoryCandidateDecisionV1:
    schema: str
    disposition: str
    reason_code: str
    external_card_receipt_digest: str
    candidate: CoordinateMemoryCandidateV1 | None
    semantic_key_preserved_from_eki: bool
    source_generation_separate_from_semantic_key: bool
    eki_k27_not_crosscast_to_wp03_placement: bool
    store_mutated: bool = False
    write_authority: bool = False
    semantic_truth_granted: bool = False
    effect_authority: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": SCHEMA, "decision": asdict(self)})


def project_external_knowledge_candidate(
    *,
    card: eki.ExternalKnowledgeCard,
    max_standing_chars: int = 4096,
) -> CoordinateMemoryCandidateDecisionV1:
    """Project one exact external card into a non-writing store candidate."""
    if isinstance(max_standing_chars, bool) or not isinstance(max_standing_chars, int) or max_standing_chars <= 0:
        raise ValueError("MAX_STANDING_CHARS_MUST_BE_POSITIVE_INT")
    if not isinstance(card, eki.ExternalKnowledgeCard):
        raise TypeError("EXTERNAL_KNOWLEDGE_CARD_REQUIRED")
    _validate_nonpromotion(card)

    card_digest = _sha256(card.receipt_digest, "EKI_CARD_RECEIPT_DIGEST")
    semantic_id = _sha256(card.semantic_id, "EKI_SEMANTIC_ID")

    common = dict(
        schema=SCHEMA,
        external_card_receipt_digest=card_digest,
        semantic_key_preserved_from_eki=True,
        source_generation_separate_from_semantic_key=True,
        eki_k27_not_crosscast_to_wp03_placement=True,
    )

    if card.currentness != eki.Currentness.CURRENT.value or card.generation_id is None:
        return CoordinateMemoryCandidateDecisionV1(
            disposition=HOLD_CURRENT,
            reason_code="PERSISTENT_CANDIDATE_REQUIRES_CURRENT_SOURCE_GENERATION",
            candidate=None,
            **common,
        )

    generation_id = _sha256(card.generation_id, "EKI_GENERATION_ID")
    if card.availability != eki.Availability.READ_ONLY_REFERENCE_READY.value:
        return CoordinateMemoryCandidateDecisionV1(
            disposition=HOLD_AVAILABILITY,
            reason_code="ONLY_READ_ONLY_REFERENCE_READY_ENTERS_COGNITION_CANDIDATE_LANE",
            candidate=None,
            **common,
        )

    if (
        card.admitted_hydration_level != int(eki.HydrationLevel.L4)
        or card.exact_reopen_uri is None
        or card.content_sha256 is None
    ):
        return CoordinateMemoryCandidateDecisionV1(
            disposition=HOLD_L4,
            reason_code="EXACT_REOPEN_URI_AND_CONTENT_DIGEST_REQUIRED_FOR_PERSISTENT_CANDIDATE",
            candidate=None,
            **common,
        )

    reopen_uri = _http_uri(card.exact_reopen_uri, "EKI_EXACT_REOPEN_URI")
    content_sha = _sha256(card.content_sha256, "EKI_CONTENT_SHA256")
    k27 = _k27_key(card)

    # Standing is source-admitted EKI material, not a model-authored summary.
    standing_payload = {
        "semantic_id": semantic_id,
        "source_generation_id": generation_id,
        "source_kind": card.source_kind,
        "artifact_class": card.artifact_class,
        "canonical_id": card.canonical_id,
        "canonical_uri": card.canonical_uri,
        "title": card.title,
        "advisory_only": card.advisory_only,
        "hydration": card.hydration,
    }
    standing = _canonical(standing_payload).decode("ascii")
    if len(standing) > max_standing_chars:
        return CoordinateMemoryCandidateDecisionV1(
            disposition=HOLD_SIZE,
            reason_code="SOURCE_ADMITTED_STANDING_EXCEEDS_COORDINATE_MEMORY_BOUND",
            candidate=None,
            **common,
        )

    cell = {
        "external_semantic_id": semantic_id,
        "source_generation_id": generation_id,
        "external_card_receipt_digest": card_digest,
        "source_kind": card.source_kind,
        "artifact_class": card.artifact_class,
        "currentness": card.currentness,
        "availability": card.availability,
        "admitted_hydration_level": card.admitted_hydration_level,
        "content_sha256": content_sha,
        "eki_k27_locality_key": k27,
        "eki_k27_routing_only": True,
        "wp03_placement_mapping_status": "UNMAPPED_NOT_REQUIRED_FOR_SEMANTIC_LOOKUP",
        "rights": card.rights,
        "security": card.security,
        "advisory_only": card.advisory_only,
    }
    reopen = {
        "uri": reopen_uri,
        "content_sha256": content_sha,
        "source_generation_id": generation_id,
        "external_card_receipt_digest": card_digest,
    }
    value_digest = _sha(
        {
            "domain": "AURA-EKI-COORDINATE-MEMORY-PROPOSED-VALUE-v1",
            "cell": cell,
            "standing": standing,
            "reopen": reopen,
            "successor": None,
        }
    )
    row_digest = _sha(
        {
            "domain": "AURA-EKI-COORDINATE-MEMORY-PROPOSED-ROW-v1",
            "K": semantic_id,
            "V_digest": value_digest,
            "source_generation_id": generation_id,
        }
    )
    candidate = CoordinateMemoryCandidateV1(
        schema=SCHEMA,
        semantic_key=semantic_id,
        source_generation_id=generation_id,
        external_card_receipt_digest=card_digest,
        source_kind=card.source_kind,
        artifact_class=card.artifact_class,
        source_uri=card.canonical_uri,
        exact_reopen_uri=reopen_uri,
        content_sha256=content_sha,
        eki_k27_locality_key=k27,
        wp03_placement_hint=None,
        placement_mapping_required=False,
        proposed_cell=cell,
        proposed_standing=standing,
        proposed_reopen=reopen,
        proposed_successor=None,
        proposed_value_digest=value_digest,
        proposed_row_digest=row_digest,
    )
    return CoordinateMemoryCandidateDecisionV1(
        disposition=READY,
        reason_code="CURRENT_EXACT_EKI_REFERENCE_PROJECTED_WITHOUT_STORE_MUTATION",
        candidate=candidate,
        **common,
    )
