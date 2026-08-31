#!/usr/bin/env python3
"""EKI-2: project exact EKI-1 L4 knowledge into WP03 candidate-only persistence.

D0 / HS1 / NONPROMOTING.

This bridge owns one relation only:

    EKI-1 generation-bound L4 card -> aura-coordinate-memory-kv-v1 candidate row.

It deliberately does *not* persist source CURRENTness as reusable truth.  The row
remembers which exact source generation EKI observed, how to reopen that generation,
and the generation-bound semantic identity.  WP03 must still receive independent
read-time currentness evidence before returning a verified candidate.

K27 is retained as routing/locality metadata only.  It is never the row's semantic
identity, a freshness witness, instruction authority, transformer MODEL_PREFIX_KV,
or effect permission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from tools.aura_external_knowledge_ingress import ExternalKnowledgeCard

SCHEMA = "AURA-EKI-PERSISTENT-CANDIDATE-PROJECTION-v1"
STORE_SCHEMA_NAME = "aura-coordinate-memory-kv-v1"
STORE_SCHEMA_VERSION = "1.0.0"
EKI1_HEAD = "719698bb456ace375205a92c859ef347655a178a"
WP03_HEAD = "1a871a9fc7ed6a3a27527aa2b042695c254c405b"
CONVERGENCE_HEAD = "712c213061665604af0e3d714ec24721b8acaf97"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=lambda obj: getattr(obj, "value", str(obj)),
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_hex(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _http_uri(value: str, name: str) -> str:
    value = _required(value, name)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name}_MUST_BE_HTTP_URI")
    return value


def _validate_nonpromotion(card: ExternalKnowledgeCard) -> None:
    if card.read_only_reference_authority is not True:
        raise ValueError("EKI2_REQUIRES_READ_ONLY_REFERENCE_AUTHORITY")
    forbidden = (
        card.execution_authorized,
        card.provider_effect_authorized,
        card.semantic_k27_authority,
        card.native_private_transformer_kv_accessed,
        card.gate10_promoted,
        card.merge_deploy_spend_public_financial_human_effect_authorized,
    )
    if any(value is not False for value in forbidden):
        raise ValueError("EKI2_EKI_CARD_CANNOT_WIDEN_AUTHORITY")


def _validate_k27(card: ExternalKnowledgeCard) -> str:
    locality = card.k27_locality
    if not isinstance(locality, Mapping):
        raise ValueError("EKI2_K27_LOCALITY_REQUIRED")
    if locality.get("routing_only") is not True:
        raise ValueError("EKI2_K27_MUST_BE_ROUTING_ONLY")
    if locality.get("semantic_identity") is not False or locality.get("authority") is not False:
        raise ValueError("EKI2_K27_CANNOT_MINT_IDENTITY_OR_AUTHORITY")
    key = locality.get("key")
    if not isinstance(key, str) or len(key) != 27 or any(ch not in "012" for ch in key):
        raise ValueError("EKI2_K27_KEY_MUST_BE_27_TRITS")
    trits = locality.get("trits")
    if tuple(trits or ()) != tuple(int(ch) for ch in key):
        raise ValueError("EKI2_K27_KEY_TRITS_MISMATCH")
    projection = card.projection_13d
    if not isinstance(projection, Mapping) or projection.get("semantic_authority") is not False:
        raise ValueError("EKI2_13D_PROJECTION_CANNOT_MINT_SEMANTIC_AUTHORITY")
    return key


def _validate_exact_l4(card: ExternalKnowledgeCard) -> Mapping[str, Any]:
    if card.schema != "AURA-EXTERNAL-KNOWLEDGE-INGRESS-v1":
        raise ValueError("EKI2_EKI_SCHEMA_MISMATCH")
    _sha256_hex(card.semantic_id, "EKI2_SEMANTIC_ID")
    generation_id = _sha256_hex(_required(card.generation_id, "EKI2_GENERATION_ID"), "EKI2_GENERATION_ID")
    if card.currentness != "CURRENT":
        raise ValueError("EKI2_REQUIRES_CURRENT_INGRESS_OBSERVATION")
    if card.admitted_hydration_level != 4:
        raise ValueError("EKI2_REQUIRES_EXACT_L4_HYDRATION")
    exact_uri = _http_uri(_required(card.exact_reopen_uri, "EKI2_EXACT_REOPEN_URI"), "EKI2_EXACT_REOPEN_URI")
    _sha256_hex(_required(card.content_sha256, "EKI2_CONTENT_SHA256"), "EKI2_CONTENT_SHA256")
    hydration = card.hydration
    if not isinstance(hydration, Mapping):
        raise ValueError("EKI2_HYDRATION_MAPPING_REQUIRED")
    l4 = hydration.get("L4")
    if not isinstance(l4, Mapping):
        raise ValueError("EKI2_L4_MATERIAL_REQUIRED")
    if l4.get("source_generation_id") != generation_id:
        raise ValueError("EKI2_L4_GENERATION_MISMATCH")
    _sha256_hex(_required(l4.get("material_digest"), "EKI2_L4_MATERIAL_DIGEST"), "EKI2_L4_MATERIAL_DIGEST")
    l0 = hydration.get("L0")
    if not isinstance(l0, Mapping) or l0.get("semantic_id") != card.semantic_id:
        raise ValueError("EKI2_L0_SEMANTIC_ID_MISMATCH")
    if _required(l0.get("canonical_uri"), "EKI2_L0_CANONICAL_URI") != card.canonical_uri:
        raise ValueError("EKI2_CANONICAL_URI_MISMATCH")
    if exact_uri != card.exact_reopen_uri:
        raise ValueError("EKI2_EXACT_REOPEN_URI_MISMATCH")
    _validate_nonpromotion(card)
    _validate_k27(card)
    return l4


@dataclass(frozen=True)
class PersistentCandidateProjection:
    schema: str
    eki1_head: str
    wp03_head: str
    convergence_head: str
    semantic_id: str
    generation_id: str
    semantic_key: str
    value_digest: str
    k27_key: str
    exact_reopen_uri: str
    content_sha256: str
    l4_material_digest: str
    eki_card_receipt_digest: str
    row: Mapping[str, Any]
    source_currentness_persisted: bool = False
    candidate_only: bool = True
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("EKI2_PROJECTION_SCHEMA_MISMATCH")
        if self.eki1_head != EKI1_HEAD or self.wp03_head != WP03_HEAD or self.convergence_head != CONVERGENCE_HEAD:
            raise ValueError("EKI2_PARENT_GENERATION_MISMATCH")
        _sha256_hex(self.semantic_id, "EKI2_PROJECTION_SEMANTIC_ID")
        _sha256_hex(self.generation_id, "EKI2_PROJECTION_GENERATION_ID")
        _sha256_hex(self.value_digest, "EKI2_VALUE_DIGEST")
        _sha256_hex(self.content_sha256, "EKI2_PROJECTION_CONTENT_SHA256")
        _sha256_hex(self.l4_material_digest, "EKI2_PROJECTION_L4_MATERIAL_DIGEST")
        _sha256_hex(self.eki_card_receipt_digest, "EKI2_CARD_RECEIPT_DIGEST")
        if self.semantic_key != f"external/eki/{self.semantic_id}/{self.generation_id}":
            raise ValueError("EKI2_SEMANTIC_KEY_MUST_BIND_SEMANTIC_AND_GENERATION")
        if len(self.k27_key) != 27 or any(ch not in "012" for ch in self.k27_key):
            raise ValueError("EKI2_PROJECTION_K27_INVALID")
        _http_uri(self.exact_reopen_uri, "EKI2_PROJECTION_EXACT_REOPEN_URI")
        if self.source_currentness_persisted is not False:
            raise ValueError("EKI2_PERSISTED_ROW_CANNOT_MINT_CURRENTNESS")
        if self.candidate_only is not True:
            raise ValueError("EKI2_PERSISTENCE_MUST_REMAIN_CANDIDATE_ONLY")
        if any(
            value is not False
            for value in (
                self.instruction_authority,
                self.write_authority,
                self.effect_authority,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
                self.gate10_promoted,
            )
        ):
            raise ValueError("EKI2_PERSISTENCE_CANNOT_WIDEN_AUTHORITY")
        if set(self.row) != {"K", "V"} or self.row.get("K") != self.semantic_key:
            raise ValueError("EKI2_ROW_KEY_MISMATCH")
        value = self.row.get("V")
        if not isinstance(value, Mapping) or set(value) != {"cell", "digest", "standing", "reopen", "successor"}:
            raise ValueError("EKI2_ROW_SHAPE_MISMATCH")
        if value.get("digest") != self.value_digest:
            raise ValueError("EKI2_ROW_VALUE_DIGEST_MISMATCH")
        if value.get("successor") is not None:
            raise ValueError("EKI2_INITIAL_PROJECTION_CANNOT_INVENT_SUCCESSOR")
        cell = value.get("cell")
        if not isinstance(cell, Mapping) or cell.get("k27_key") != self.k27_key:
            raise ValueError("EKI2_ROW_K27_CELL_MISMATCH")
        reopen = value.get("reopen")
        if not isinstance(reopen, Mapping):
            raise ValueError("EKI2_ROW_REOPEN_MAPPING_REQUIRED")
        if reopen.get("exact_source_uri") != self.exact_reopen_uri:
            raise ValueError("EKI2_ROW_REOPEN_URI_MISMATCH")
        if reopen.get("content_sha256") != self.content_sha256:
            raise ValueError("EKI2_ROW_REOPEN_CONTENT_DIGEST_MISMATCH")
        if reopen.get("source_generation_id") != self.generation_id:
            raise ValueError("EKI2_ROW_REOPEN_GENERATION_MISMATCH")

    @property
    def projection_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "projection": asdict(self)})


def project_eki_l4_to_candidate(
    card: ExternalKnowledgeCard,
    *,
    max_standing_chars: int = 4096,
) -> PersistentCandidateProjection:
    """Project one exact EKI L4 card into a generation-bound candidate row.

    The standing payload intentionally omits a reusable CURRENT truth bit.  It records
    the observed source generation and evidence needed to reopen it.  WP03 currentness
    must be supplied separately when a future consumer resolves this row.
    """
    if isinstance(max_standing_chars, bool) or not isinstance(max_standing_chars, int) or max_standing_chars <= 0:
        raise ValueError("EKI2_MAX_STANDING_CHARS_MUST_BE_POSITIVE_INT")
    l4 = _validate_exact_l4(card)
    generation_id = str(card.generation_id)
    k27_key = _validate_k27(card)
    semantic_key = f"external/eki/{card.semantic_id}/{generation_id}"
    l0 = card.hydration["L0"]

    standing_payload = {
        "schema": "AURA-EKI-PERSISTED-STANDING-v1",
        "source_kind": card.source_kind,
        "artifact_class": card.artifact_class,
        "title": card.title,
        "canonical_id": card.canonical_id,
        "canonical_uri": card.canonical_uri,
        "semantic_id": card.semantic_id,
        "source_generation_id": generation_id,
        "content_sha256": card.content_sha256,
        "thesis": l0.get("thesis"),
        "l4_material_digest": l4["material_digest"],
        "eki_card_receipt_digest": card.receipt_digest,
        "advisory_only": card.advisory_only,
        "source_currentness_persisted": False,
        "candidate_only": True,
        "instruction_authority": False,
        "write_authority": False,
        "effect_authority": False,
    }
    standing = _canonical(standing_payload).decode("ascii")
    if len(standing) > max_standing_chars:
        raise ValueError("EKI2_STANDING_HYDRATION_LIMIT_EXCEEDED")
    value_digest = hashlib.sha256(standing.encode("ascii")).hexdigest()

    row = {
        "K": semantic_key,
        "V": {
            "cell": {
                "k27_schema": card.k27_locality.get("schema"),
                "k27_key": k27_key,
                "routing_only": True,
                "semantic_identity": False,
                "authority": False,
            },
            "digest": value_digest,
            "standing": standing,
            "reopen": {
                "exact_source_uri": card.exact_reopen_uri,
                "content_sha256": card.content_sha256,
                "source_generation_id": generation_id,
                "eki_card_receipt_digest": card.receipt_digest,
            },
            "successor": None,
        },
    }

    projection = PersistentCandidateProjection(
        schema=SCHEMA,
        eki1_head=EKI1_HEAD,
        wp03_head=WP03_HEAD,
        convergence_head=CONVERGENCE_HEAD,
        semantic_id=card.semantic_id,
        generation_id=generation_id,
        semantic_key=semantic_key,
        value_digest=value_digest,
        k27_key=k27_key,
        exact_reopen_uri=str(card.exact_reopen_uri),
        content_sha256=str(card.content_sha256),
        l4_material_digest=str(l4["material_digest"]),
        eki_card_receipt_digest=card.receipt_digest,
        row=row,
    )
    projection.validate()
    return projection


def build_coordinate_store_snapshot(
    projections: Sequence[PersistentCandidateProjection],
) -> bytes:
    """Build one canonical WP03-compatible snapshot from distinct semantic rows."""
    rows: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for projection in projections:
        projection.validate()
        if projection.semantic_key in seen:
            raise ValueError("EKI2_DUPLICATE_SEMANTIC_KEY")
        seen.add(projection.semantic_key)
        rows.append(projection.row)
    rows.sort(key=lambda row: str(row["K"]))
    payload = {
        "schema": {"name": STORE_SCHEMA_NAME, "version": STORE_SCHEMA_VERSION},
        "rows": rows,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


LAWS = (
    "PersistedRow!=CurrentTruth",
    "SemanticID+SourceGeneration=>PersistentSemanticKey",
    "K27Placement!=SemanticIdentity!=SourceCurrentness!=Authority",
    "CachedIngressCard!=InstructionAuthority",
    "L4ExactReopen!=ExecutionAuthority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
    "ReadTimeCurrentnessMustBeReSupplied",
)
