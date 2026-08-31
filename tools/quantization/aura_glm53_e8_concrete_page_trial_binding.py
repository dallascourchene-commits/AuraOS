#!/usr/bin/env python3
"""Bind a Q3 quantized trial candidate to an exact PR628 E8 page set.

This closes candidate-side representation identity only. It does not prove that
pages came from the official GLM checkpoint, that the baseline covers the same
source tensor set, that the page set covers the whole model, or that any model
execution used these pages.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Sequence

from tools.quantization import aura_glm53_e8_indexed_expert_page_reference as e8
from tools.quantization import aura_glm53_quantized_representation_trial as q3

SCHEMA = "AURA_GLM53_E8_CONCRETE_PAGE_TRIAL_BINDING_V1"
PAGE_PARENT_SHA = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
TRIAL_PARENT_SHA = "c4f526714e89fc36c55230c55ab2f704695212dc"
PAGE_SOURCE_BLOB_SHA = "5df2cd69a1519b2626cb52c1d8f23a25504425d9"
TRIAL_SOURCE_BLOB_SHA = "87266d031f5a201559794428eff14d9ac8595a8c"
PARENT_ARTIFACT_IDS = (PAGE_PARENT_SHA, TRIAL_PARENT_SHA)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ConcreteE8PageSetIdentity:
    model_revision: str
    representation_revision: str
    scheme: str
    codebook_digest: str
    page_count: int
    total_source_weights: int
    total_serialized_bytes: int
    codec_bits_per_weight: float
    serialized_bits_per_weight: float
    source_tensor_set_digest: str
    page_set_digest: str
    representation_digest: str


@dataclass(frozen=True)
class ConcreteE8TrialBinding:
    schema: str
    parent_artifact_ids: tuple[str, str]
    page_parent_source_blob_sha: str
    trial_parent_source_blob_sha: str
    page_set_digest: str
    source_tensor_set_digest: str
    concrete_representation_digest: str
    q3_request_digest: str
    q3_candidate_sample_digest: str
    q3_comparison_digest: str
    independent_verifier_identity: str
    model_revision: str
    representation_revision: str
    page_count: int
    total_source_weights: int
    total_serialized_bytes: int
    codec_bits_per_weight: float
    serialized_bits_per_weight: float
    candidate_identity_bound_to_concrete_page_set: bool
    candidate_sample_bound_to_concrete_page_set: bool
    independent_verifier_bound_to_candidate_sample: bool
    q3_quality_retained_on_frozen_corpus: bool
    official_glm_source_authenticated: bool
    baseline_same_source_tensor_set_proven: bool
    whole_model_coverage_proven: bool
    page_set_executed_in_model: bool
    router_execution_observed: bool
    coding_quality_generalized_beyond_frozen_corpus: bool
    general_performance_winner_proven: bool
    owner_host_identity_authenticated: bool
    physical_io_attributed_exclusively: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_ready_for_owner_promotion: bool
    deployment_authorized: bool

    @property
    def receipt_sha256(self) -> str:
        return _sha(asdict(self))


def derive_concrete_e8_page_set(pages: Sequence[e8.PackedExpertPage]) -> ConcreteE8PageSetIdentity:
    pages = tuple(pages)
    if not pages:
        raise ValueError("EMPTY_E8_PAGE_SET")

    entries: list[dict[str, object]] = []
    source_entries: list[dict[str, object]] = []
    seen_slots: set[tuple[int, int, str]] = set()
    model_revision: str | None = None
    representation_revision: str | None = None
    total_weights = 0
    total_serialized_bytes = 0
    total_codec_bits = 0.0

    for page in pages:
        if not isinstance(page, e8.PackedExpertPage):
            raise ValueError("NON_PR628_PAGE")
        page.validate()
        # Exercise the canonical parser/decoder too; a digest-valid object with a
        # malformed binary header must not enter the page-set identity.
        e8.unpack_expert_page(page)
        ident = page.identity
        ident.validate()
        if ident.scheme != e8.SCHEME:
            raise ValueError("E8_SCHEME_MISMATCH")
        if model_revision is None:
            model_revision = ident.model_revision
            representation_revision = ident.representation_revision
        if ident.model_revision != model_revision:
            raise ValueError("MIXED_MODEL_REVISIONS")
        if ident.representation_revision != representation_revision:
            raise ValueError("MIXED_REPRESENTATION_REVISIONS")
        slot = (ident.layer_id, ident.expert_id, ident.tensor_role)
        if slot in seen_slots:
            raise ValueError("DUPLICATE_LOGICAL_PAGE_SLOT")
        seen_slots.add(slot)

        weights = math.prod(ident.source_shape)
        if weights <= 0:
            raise ValueError("EMPTY_SOURCE_TENSOR")
        total_weights += weights
        total_serialized_bytes += len(page.payload)
        total_codec_bits += page.codec_bits_per_weight * weights
        entries.append({
            "layer_id": ident.layer_id,
            "expert_id": ident.expert_id,
            "tensor_role": ident.tensor_role,
            "identity_digest": ident.digest(),
            "payload_sha256": page.payload_sha256,
            "source_tensor_sha256": ident.source_tensor_sha256,
            "source_shape": list(ident.source_shape),
            "block_size": ident.block_size,
            "codec_bits_per_weight": page.codec_bits_per_weight,
            "serialized_bits_per_weight": page.serialized_bits_per_weight,
        })
        source_entries.append({
            "layer_id": ident.layer_id,
            "expert_id": ident.expert_id,
            "tensor_role": ident.tensor_role,
            "source_tensor_sha256": ident.source_tensor_sha256,
            "source_shape": list(ident.source_shape),
        })

    assert model_revision is not None and representation_revision is not None
    entries.sort(key=lambda x: (x["layer_id"], x["expert_id"], x["tensor_role"], x["identity_digest"]))
    source_entries.sort(key=lambda x: (x["layer_id"], x["expert_id"], x["tensor_role"], x["source_tensor_sha256"]))
    source_digest = _sha({"schema": "AURA_GLM53_E8_SOURCE_TENSOR_SET_V1", "entries": source_entries})
    page_set_digest = _sha({
        "schema": "AURA_GLM53_E8_PAGE_SET_V1",
        "exact_parent_sha": PAGE_PARENT_SHA,
        "exact_parent_source_blob_sha": PAGE_SOURCE_BLOB_SHA,
        "scheme": e8.SCHEME,
        "codebook_digest": e8.codebook_digest(),
        "model_revision": model_revision,
        "representation_revision": representation_revision,
        "entries": entries,
    })
    codec_bpw = total_codec_bits / total_weights
    serialized_bpw = total_serialized_bytes * 8.0 / total_weights
    representation_digest = _sha({
        "schema": "AURA_GLM53_CONCRETE_E8_PAGE_SET_REPRESENTATION_V1",
        "page_set_digest": page_set_digest,
        "source_tensor_set_digest": source_digest,
        "exact_parent_sha": PAGE_PARENT_SHA,
        "exact_parent_source_blob_sha": PAGE_SOURCE_BLOB_SHA,
        "scheme": e8.SCHEME,
        "codebook_digest": e8.codebook_digest(),
        "model_revision": model_revision,
        "representation_revision": representation_revision,
        "total_source_weights": total_weights,
        "total_serialized_bytes": total_serialized_bytes,
        "serialized_bits_per_weight": serialized_bpw,
    })
    return ConcreteE8PageSetIdentity(
        model_revision=model_revision,
        representation_revision=representation_revision,
        scheme=e8.SCHEME,
        codebook_digest=e8.codebook_digest(),
        page_count=len(pages),
        total_source_weights=total_weights,
        total_serialized_bytes=total_serialized_bytes,
        codec_bits_per_weight=codec_bpw,
        serialized_bits_per_weight=serialized_bpw,
        source_tensor_set_digest=source_digest,
        page_set_digest=page_set_digest,
        representation_digest=representation_digest,
    )


def bind_concrete_e8_trial(
    *,
    pages: Sequence[e8.PackedExpertPage],
    request: q3.QuantizedTrialRequest,
    baseline_sample: q3.TrialSample,
    candidate_sample: q3.TrialSample,
    independent_verification: q3.IndependentVerification,
) -> ConcreteE8TrialBinding:
    page_set = derive_concrete_e8_page_set(pages)
    request.validate()
    candidate = request.candidate

    if candidate.model_revision != page_set.model_revision:
        raise ValueError("CANDIDATE_MODEL_NOT_CONCRETE_PAGE_MODEL")
    if candidate.representation_revision != page_set.representation_revision:
        raise ValueError("CANDIDATE_REVISION_NOT_CONCRETE_PAGE_REVISION")
    if candidate.representation_digest != page_set.representation_digest:
        raise ValueError("CANDIDATE_DIGEST_NOT_CONCRETE_PAGE_SET")
    if not math.isclose(candidate.nominal_bits_per_weight, page_set.serialized_bits_per_weight, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("CANDIDATE_BPW_NOT_EXACT_SERIALIZED_PAGE_SET_RATE")
    if candidate.static_weight_bytes != page_set.total_serialized_bytes:
        raise ValueError("CANDIDATE_BYTES_NOT_EXACT_SERIALIZED_PAGE_SET_BYTES")
    if candidate.quantized is not True:
        raise ValueError("CONCRETE_E8_CANDIDATE_MUST_BE_QUANTIZED")

    comparison = q3.compare_quantized_representation(
        request=request,
        baseline_sample=baseline_sample,
        candidate_sample=candidate_sample,
        independent_verification=independent_verification,
    )
    return ConcreteE8TrialBinding(
        schema=SCHEMA,
        parent_artifact_ids=PARENT_ARTIFACT_IDS,
        page_parent_source_blob_sha=PAGE_SOURCE_BLOB_SHA,
        trial_parent_source_blob_sha=TRIAL_SOURCE_BLOB_SHA,
        page_set_digest=page_set.page_set_digest,
        source_tensor_set_digest=page_set.source_tensor_set_digest,
        concrete_representation_digest=page_set.representation_digest,
        q3_request_digest=request.request_digest,
        q3_candidate_sample_digest=candidate_sample.sample_digest,
        q3_comparison_digest=comparison.comparison_digest,
        independent_verifier_identity=independent_verification.verifier_identity,
        model_revision=page_set.model_revision,
        representation_revision=page_set.representation_revision,
        page_count=page_set.page_count,
        total_source_weights=page_set.total_source_weights,
        total_serialized_bytes=page_set.total_serialized_bytes,
        codec_bits_per_weight=page_set.codec_bits_per_weight,
        serialized_bits_per_weight=page_set.serialized_bits_per_weight,
        candidate_identity_bound_to_concrete_page_set=True,
        candidate_sample_bound_to_concrete_page_set=True,
        independent_verifier_bound_to_candidate_sample=True,
        q3_quality_retained_on_frozen_corpus=comparison.candidate_quality_retained_on_frozen_corpus,
        official_glm_source_authenticated=False,
        baseline_same_source_tensor_set_proven=False,
        whole_model_coverage_proven=False,
        page_set_executed_in_model=False,
        router_execution_observed=False,
        coding_quality_generalized_beyond_frozen_corpus=False,
        general_performance_winner_proven=False,
        owner_host_identity_authenticated=False,
        physical_io_attributed_exclusively=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_ready_for_owner_promotion=False,
        deployment_authorized=False,
    )
