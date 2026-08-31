#!/usr/bin/env python3
"""Fail-closed evidence-transfer membrane for GLM-5.3 quantization representations.

Q6 is derived from two exact-green other-agent artifacts:
- Q4 equal-rate E8-vs-hypercube synthetic ablation; and
- Q5 concrete PR628 E8 expert-page -> packed-plan projection.

The contract prevents a result earned by one E8-family representation from being
attached to another representation merely because both are described as "E8".
Synthetic distortion evidence never becomes GLM tensor/task quality evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from tools.quantization.aura_glm53_e8_indexed_expert_page_reference import (
    INDEX_BITS as Q5_INDEX_BITS,
    SCHEME as Q5_SCHEME,
    VECTOR_DIM as Q5_VECTOR_DIM,
    codebook_digest as q5_codebook_digest,
)
from tools.quantization.aura_glm53_e8_page_plan_projection import (
    E8_EXACT_HEAD,
    E8_EXACT_RUN,
    SCALE_BITS_PER_GROUP as Q5_SCALE_BITS,
    SCALE_GROUP_WEIGHTS as Q5_SCALE_GROUP_WEIGHTS,
    e8_q2_representation,
    implementation_binding_digest as q5_implementation_binding_digest,
)

VERSION = "AURA_GLM53_QUANTIZATION_EVIDENCE_TRANSFER_V1"
Q4_EXACT_HEAD = "0330ee6c19d903f7e3d079996b5b87794b423411"
Q4_EXACT_RUN = 33369336878
Q5_EXACT_HEAD = "e342b5c1ab1dc51cb0c3d9b79b8fa3b83cae7192"
Q5_EXACT_RUN = 33369222880

Q4_SCHEME = "E8_ROOT_240_U8_V1"
Q4_CODEBOOK_SHA256 = "cc0261db332ac098bcfbed0a75a05c450eb24cc4e1daa81f1fa84be8356e24b3"
Q4_RECEIPT_SHA256 = "cac09fd77062163f1f4783af6b54bca9a6ba4bc0f0130c5835e3914ffe72066b"
Q4_VECTOR_DIM = 8
Q4_INDEX_BITS = 8
Q4_SCALE_GROUP_WEIGHTS = 64
Q4_SCALE_BITS = 16
Q4_CODEC_BPW = 1.25
SYNTHETIC_DISTORTION_SCOPE = "SYNTHETIC_DISTORTION_ONLY"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hex64(name: str, value: str) -> None:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("INVALID_SHA256:" + name)


@dataclass(frozen=True)
class QuantizationRepresentationIdentity:
    scheme: str
    codebook_digest: str
    vector_dim: int
    index_bits_per_vector: int
    scale_group_weights: int
    scale_bits_per_group: int
    codec_bits_per_weight: float
    implementation_binding_digest: str

    def validate(self) -> None:
        if not self.scheme.strip():
            raise ValueError("SCHEME_REQUIRED")
        _hex64("codebook_digest", self.codebook_digest)
        _hex64("implementation_binding_digest", self.implementation_binding_digest)
        for name in ("vector_dim", "index_bits_per_vector", "scale_group_weights", "scale_bits_per_group"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError("INVALID_POSITIVE_INT:" + name)
        if not math.isfinite(self.codec_bits_per_weight) or self.codec_bits_per_weight <= 0:
            raise ValueError("INVALID_CODEC_BPW")

    @property
    def identity_digest(self) -> str:
        self.validate()
        return _sha(asdict(self))


@dataclass(frozen=True)
class QuantizationEvidence:
    representation: QuantizationRepresentationIdentity
    evidence_scope: str
    evidence_receipt_digest: str
    glm53_tensor_evidence: bool
    coding_quality_evidence: bool
    runtime_evidence: bool

    def validate(self) -> None:
        self.representation.validate()
        _hex64("evidence_receipt_digest", self.evidence_receipt_digest)
        if self.evidence_scope != SYNTHETIC_DISTORTION_SCOPE:
            raise ValueError("UNSUPPORTED_EVIDENCE_SCOPE")
        if self.glm53_tensor_evidence or self.coding_quality_evidence or self.runtime_evidence:
            raise ValueError("SYNTHETIC_SCOPE_CANNOT_CLAIM_MODEL_OR_RUNTIME_EVIDENCE")


@dataclass(frozen=True)
class EvidenceTransferDisposition:
    version: str
    source_representation_digest: str
    target_representation_digest: str
    exact_representation_identity_match: bool
    geometry_family_label_match: bool
    source_evidence_scope: str
    disposition: str
    synthetic_distortion_evidence_transferable: bool
    glm53_tensor_gain_inherited: bool
    coding_quality_inherited: bool
    runtime_performance_inherited: bool
    semantic_k27_authority_minted: bool
    gate10_promoted: bool

    @property
    def disposition_digest(self) -> str:
        return _sha(asdict(self))


def q4_representation_identity() -> QuantizationRepresentationIdentity:
    # Q4 has no source-bound implementation manifest; bind its exact hosted receipt
    # as the implementation-evidence generation for this synthetic representation.
    return QuantizationRepresentationIdentity(
        scheme=Q4_SCHEME,
        codebook_digest=Q4_CODEBOOK_SHA256,
        vector_dim=Q4_VECTOR_DIM,
        index_bits_per_vector=Q4_INDEX_BITS,
        scale_group_weights=Q4_SCALE_GROUP_WEIGHTS,
        scale_bits_per_group=Q4_SCALE_BITS,
        codec_bits_per_weight=Q4_CODEC_BPW,
        implementation_binding_digest=Q4_RECEIPT_SHA256,
    )


def q4_synthetic_evidence() -> QuantizationEvidence:
    return QuantizationEvidence(
        representation=q4_representation_identity(),
        evidence_scope=SYNTHETIC_DISTORTION_SCOPE,
        evidence_receipt_digest=Q4_RECEIPT_SHA256,
        glm53_tensor_evidence=False,
        coding_quality_evidence=False,
        runtime_evidence=False,
    )


def q5_representation_identity() -> QuantizationRepresentationIdentity:
    rep = e8_q2_representation()
    return QuantizationRepresentationIdentity(
        scheme=Q5_SCHEME,
        codebook_digest=q5_codebook_digest(),
        vector_dim=Q5_VECTOR_DIM,
        index_bits_per_vector=Q5_INDEX_BITS,
        scale_group_weights=Q5_SCALE_GROUP_WEIGHTS,
        scale_bits_per_group=Q5_SCALE_BITS,
        codec_bits_per_weight=rep.effective_bits_per_weight,
        implementation_binding_digest=q5_implementation_binding_digest(),
    )


def classify_evidence_transfer(
    *, source: QuantizationEvidence, target: QuantizationRepresentationIdentity
) -> EvidenceTransferDisposition:
    source.validate()
    target.validate()
    exact = source.representation.identity_digest == target.identity_digest
    geometry_family = source.representation.scheme.startswith("E8_") and target.scheme.startswith("AURA_E8_")
    if exact:
        disposition = "SAME_REPRESENTATION_SYNTHETIC_EVIDENCE_ONLY"
    else:
        disposition = "DIFFERENT_REPRESENTATION_NO_EVIDENCE_TRANSFER"
    return EvidenceTransferDisposition(
        version=VERSION,
        source_representation_digest=source.representation.identity_digest,
        target_representation_digest=target.identity_digest,
        exact_representation_identity_match=exact,
        geometry_family_label_match=geometry_family,
        source_evidence_scope=source.evidence_scope,
        disposition=disposition,
        synthetic_distortion_evidence_transferable=exact,
        glm53_tensor_gain_inherited=False,
        coding_quality_inherited=False,
        runtime_performance_inherited=False,
        semantic_k27_authority_minted=False,
        gate10_promoted=False,
    )


def q4_to_q5_disposition() -> EvidenceTransferDisposition:
    return classify_evidence_transfer(source=q4_synthetic_evidence(), target=q5_representation_identity())


def main() -> None:
    out = q4_to_q5_disposition()
    print(json.dumps({**asdict(out), "disposition_digest": out.disposition_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
