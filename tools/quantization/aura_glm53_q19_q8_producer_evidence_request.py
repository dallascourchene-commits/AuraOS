#!/usr/bin/env python3
"""Q19: issue a non-executing producer-evidence request to the canonical Q8 owner.

D0 / HS1 / NONPROMOTING.

Exactly two post-cut other-Agent semantic surfaces define this request seam:
- Q18 / PR #761: current-generation bounded representative C2 proposal eligibility.
- NAV-14 / PR #768: progress-bound hydrated-version handoff candidate.

Neither parent proves that the NAV-14 hydrated material is an official GLM-5.3 tensor
payload or that a concrete E8 page was materialized from it. Historical PR #645
(Q8/Q9) already owns that provenance frontier and names four non-collapsible producer
witnesses. This module therefore does not mint a new producer relation. It only emits
a deterministic request capsule addressed to that owner, carrying the two evidence
domains separately and asking for exactly those four witnesses.

RequestReady != ProducerWitnessSatisfied.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
import re
from typing import Mapping

from tools.quantization.aura_glm53_current_generation_bounded_c2_proposal import (
    ELIGIBLE as Q18_ELIGIBLE,
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    SOURCE_SET_DIGEST,
    admit_current_generation_bounded_c2_proposal,
    current_q16_fixture,
    current_s1_fixture,
)

SCHEMA = "AURA_GLM53_Q19_Q8_PRODUCER_EVIDENCE_REQUEST_V1"
Q18_HEAD = "87fde6b21675c7876acc63f4ca30b2dda89970d0"
Q18_PROOF_RUN = 33436970079
Q18_PROOF_JOB = 99635635152
Q18_SOURCE_BLOB = "4cee26edaf0759fc80d31889ab9e4e268f9a4fbe"
Q18_RECEIPT = "c53acb3ff471dbe3971ee4e7a75b28c4316b50fba88a414f406b93c271c90230"

NAV14_HEAD = "6cdd1be40428250bffba20e924f664c7be585469"
NAV14_PROOF_RUN = 33437542974
NAV14_PROOF_JOB = 99637538062
NAV14_SOURCE_BLOB = "b1bdfb4c65281c314e658a6fb6fc8727a4b54245"
NAV14_READY = "PROGRESS_BOUND_HANDOFF_CANDIDATE"

Q8_OWNER_PR = 645
Q8_OWNER_HEAD = "89af53c33d6b8ce422c37245651b2d94bbdaf974"
Q8_OWNER_SOURCE_BLOB = "899bf0a39361dd9898f88791308f90b89ea0c660"
Q8_REQUIRED_WITNESSES = (
    "OFFICIAL_SOURCE_TENSOR_PAYLOAD_OBSERVATION",
    "EXACT_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION",
    "CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT",
    "BASELINE_SAME_OFFICIAL_SOURCE_TENSOR_SET_RELATION",
)

REQUEST_PURPOSE = "resolve-q18-nav14-source-to-concrete-page-producer-edge"
READY = "Q8_MATERIALIZATION_EVIDENCE_REQUEST_READY"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _digest(value: str, code: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(code)
    return value


def _text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


class RequestDisposition(str, Enum):
    READY = READY
    HOLD_Q18_PARENT = "HOLD_Q18_PARENT"
    HOLD_Q18_NOT_ELIGIBLE = "HOLD_Q18_NOT_ELIGIBLE"
    HOLD_NAV14_PARENT = "HOLD_NAV14_PARENT"
    HOLD_NAV14_NOT_READY = "HOLD_NAV14_NOT_READY"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"


@dataclass(frozen=True)
class ProgressBoundHandoffProjectionV1:
    parent_head: str
    proof_run: int
    proof_job: int
    progress_handoff_digest: str
    disposition: str
    subject_key: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str
    candidate_only: bool = True
    persistent_write_authorized: bool = False
    evidence_admitted: bool = False
    source_truth_proven: bool = False
    source_currentness_proven: bool = False
    read_currentness_proven: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _digest(self.progress_handoff_digest, "NAV14_PROGRESS_HANDOFF_DIGEST_INVALID")
        _digest(self.subject_key, "NAV14_SUBJECT_KEY_INVALID")
        _digest(self.evidence_generation_key, "NAV14_EVIDENCE_GENERATION_INVALID")
        _digest(self.material_digest, "NAV14_MATERIAL_DIGEST_INVALID")
        _text(self.exact_source_uri, "NAV14_SOURCE_URI_INVALID")
        if not isinstance(self.proof_run, int) or isinstance(self.proof_run, bool):
            raise ValueError("NAV14_PROOF_RUN_INVALID")
        if not isinstance(self.proof_job, int) or isinstance(self.proof_job, bool):
            raise ValueError("NAV14_PROOF_JOB_INVALID")

    @property
    def ceiling_breached(self) -> bool:
        return any((
            not self.candidate_only,
            self.persistent_write_authorized,
            self.evidence_admitted,
            self.source_truth_proven,
            self.source_currentness_proven,
            self.read_currentness_proven,
            self.effect_authorized,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
        ))


@dataclass(frozen=True)
class Q8ProducerEvidenceRequestReceiptV1:
    disposition: RequestDisposition
    reason: str
    q18_receipt_digest: str | None
    nav14_progress_handoff_digest: str | None
    request_purpose: str
    required_witnesses: tuple[str, ...]
    request_digest: str
    request_ready: bool
    cross_domain_source_relation_proven: bool = False
    official_source_tensor_payload_observed: bool = False
    exact_official_tensor_to_concrete_source_tensor_set_relation_proven: bool = False
    candidate_page_materialization_owner_receipt_observed: bool = False
    baseline_same_official_source_tensor_set_relation_proven: bool = False
    tensor_payload_bound: bool = False
    real_tensor_quantization_observed: bool = False
    model_execution_observed: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False


def _q18_ceiling_breached(q18: Mapping[str, object]) -> bool:
    return any(bool(q18.get(name)) for name in (
        "tensor_payload_bound",
        "real_tensor_quantization_observed",
        "model_execution_observed",
        "execution_authorized",
        "owner_host_execution_observed",
        "physical_io_performance_proven",
        "full_tensor_superiority_proven",
        "whole_model_superiority_proven",
        "quality_superiority_proven",
        "runtime_superiority_proven",
        "g2_admitted",
        "gate10_promoted",
        "semantic_k27_authority_minted",
        "native_private_transformer_kv_accessed",
    ))


def _validate_q18(q18: Mapping[str, object]) -> None:
    if q18.get("receipt_digest") != Q18_RECEIPT:
        raise ValueError("Q18_RECEIPT_IDENTITY_MISMATCH")
    reproduced = admit_current_generation_bounded_c2_proposal(current_q16_fixture(), current_s1_fixture())
    if reproduced.get("receipt_digest") != Q18_RECEIPT or dict(q18) != reproduced:
        raise ValueError("Q18_EXACT_SEMANTIC_SURFACE_MISMATCH")


def _classify_tree(*, q18_parent: bool, q18_eligible: bool, nav14_parent: bool, nav14_ready: bool, ceiling_ok: bool) -> RequestDisposition:
    if not q18_parent:
        return RequestDisposition.HOLD_Q18_PARENT
    if not q18_eligible:
        return RequestDisposition.HOLD_Q18_NOT_ELIGIBLE
    if not nav14_parent:
        return RequestDisposition.HOLD_NAV14_PARENT
    if not nav14_ready:
        return RequestDisposition.HOLD_NAV14_NOT_READY
    if not ceiling_ok:
        return RequestDisposition.HOLD_CLAIM_CEILING
    return RequestDisposition.READY


def _classify_rules(*, q18_parent: bool, q18_eligible: bool, nav14_parent: bool, nav14_ready: bool, ceiling_ok: bool) -> RequestDisposition:
    rules = (
        (not q18_parent, RequestDisposition.HOLD_Q18_PARENT),
        (not q18_eligible, RequestDisposition.HOLD_Q18_NOT_ELIGIBLE),
        (not nav14_parent, RequestDisposition.HOLD_NAV14_PARENT),
        (not nav14_ready, RequestDisposition.HOLD_NAV14_NOT_READY),
        (not ceiling_ok, RequestDisposition.HOLD_CLAIM_CEILING),
    )
    for condition, disposition in rules:
        if condition:
            return disposition
    return RequestDisposition.READY


def issue_q8_producer_evidence_request(
    *,
    q18: Mapping[str, object],
    nav14: ProgressBoundHandoffProjectionV1,
) -> Q8ProducerEvidenceRequestReceiptV1:
    _validate_q18(q18)
    nav14.validate_shape()

    q18_parent = True  # exact semantic Q18 is reproduced byte-for-byte above.
    q18_eligible = q18.get("disposition") == Q18_ELIGIBLE and bool(q18.get("bounded_c2_request_proposal_eligible"))
    nav14_parent = (
        nav14.parent_head == NAV14_HEAD
        and nav14.proof_run == NAV14_PROOF_RUN
        and nav14.proof_job == NAV14_PROOF_JOB
    )
    nav14_ready = nav14.disposition == NAV14_READY and nav14.candidate_only
    ceiling_ok = not _q18_ceiling_breached(q18) and not nav14.ceiling_breached

    a = _classify_tree(
        q18_parent=q18_parent,
        q18_eligible=q18_eligible,
        nav14_parent=nav14_parent,
        nav14_ready=nav14_ready,
        ceiling_ok=ceiling_ok,
    )
    b = _classify_rules(
        q18_parent=q18_parent,
        q18_eligible=q18_eligible,
        nav14_parent=nav14_parent,
        nav14_ready=nav14_ready,
        ceiling_ok=ceiling_ok,
    )
    if a != b:
        raise RuntimeError("Q19_DIFFERENT_J_CLASSIFIER_DIVERGENCE")

    ready = a is RequestDisposition.READY
    payload = {
        "schema": SCHEMA,
        "disposition": a.value,
        "request_ready": ready,
        "request_purpose": REQUEST_PURPOSE,
        "exact_two_semantic_parents": [Q18_HEAD, NAV14_HEAD],
        "parent_proof_coordinates": {
            "q18": [Q18_PROOF_RUN, Q18_PROOF_JOB],
            "nav14": [NAV14_PROOF_RUN, NAV14_PROOF_JOB],
        },
        "q18_domain": {
            "receipt_digest": q18.get("receipt_digest"),
            "official_repository": q18.get("official_repository"),
            "official_revision": q18.get("official_revision"),
            "source_set_digest": q18.get("source_set_digest"),
            "q16_receipt_digest": q18.get("q16_receipt_digest"),
            "s1_receipt_digest": q18.get("s1_receipt_digest"),
            "s1_source_admission_digest": q18.get("s1_source_admission_digest"),
            "s1_c2_request_digest": q18.get("s1_c2_request_digest"),
        },
        "nav14_domain": {
            "progress_handoff_digest": nav14.progress_handoff_digest,
            "subject_key": nav14.subject_key,
            "evidence_generation_key": nav14.evidence_generation_key,
            "material_digest": nav14.material_digest,
            "exact_source_uri": nav14.exact_source_uri,
        },
        "historical_owner_constraint": {
            "pr": Q8_OWNER_PR,
            "head": Q8_OWNER_HEAD,
            "source_blob": Q8_OWNER_SOURCE_BLOB,
            "required_witnesses": list(Q8_REQUIRED_WITNESSES),
        },
        "cross_domain_source_relation_proven": False,
        "official_source_tensor_payload_observed": False,
        "exact_official_tensor_to_concrete_source_tensor_set_relation_proven": False,
        "candidate_page_materialization_owner_receipt_observed": False,
        "baseline_same_official_source_tensor_set_relation_proven": False,
        "tensor_payload_bound": False,
        "real_tensor_quantization_observed": False,
        "model_execution_observed": False,
        "execution_authorized": False,
        "effect_authorized": False,
        "semantic_k27_authority_minted": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
        "laws": [
            "RequestReady!=ProducerWitnessSatisfied",
            "Q18ProposalEligible!=TensorPayloadBound",
            "ProgressBoundHydratedMaterial!=OfficialGLMTensorPayload",
            "CrossDomainRequest!=CrossDomainSourceRelation",
            "Q8WitnessNames!=Q8WitnessEvidence",
            "Q8MaterializationOwnerRemainsCanonical",
            "K27Coordinate!=ProducerAuthority",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ],
    }
    request_digest = _sha(payload)
    return Q8ProducerEvidenceRequestReceiptV1(
        disposition=a,
        reason=("EXACT_CURRENT_PARENTS_READY_FOR_CANONICAL_Q8_PRODUCER_EVIDENCE_REQUEST" if ready else a.value),
        q18_receipt_digest=str(q18.get("receipt_digest")) if q18.get("receipt_digest") else None,
        nav14_progress_handoff_digest=nav14.progress_handoff_digest,
        request_purpose=REQUEST_PURPOSE,
        required_witnesses=Q8_REQUIRED_WITNESSES,
        request_digest=request_digest,
        request_ready=ready,
    )


def current_q18_receipt() -> dict[str, object]:
    receipt = admit_current_generation_bounded_c2_proposal(current_q16_fixture(), current_s1_fixture())
    if receipt["receipt_digest"] != Q18_RECEIPT:
        raise RuntimeError("Q18_REPRODUCTION_DRIFT")
    return receipt


def nav14_projection_fixture() -> ProgressBoundHandoffProjectionV1:
    # Opaque identity-bearing values. Q19 does not infer that these equal Q18's byte domain.
    return ProgressBoundHandoffProjectionV1(
        parent_head=NAV14_HEAD,
        proof_run=NAV14_PROOF_RUN,
        proof_job=NAV14_PROOF_JOB,
        progress_handoff_digest="1" * 64,
        disposition=NAV14_READY,
        subject_key="2" * 64,
        evidence_generation_key="3" * 64,
        material_digest="4" * 64,
        exact_source_uri="https://example.invalid/nav14/material",
    )


def prove_different_j() -> int:
    checked = 0
    for q18_parent in (False, True):
        for q18_eligible in (False, True):
            for nav14_parent in (False, True):
                for nav14_ready in (False, True):
                    for ceiling_ok in (False, True):
                        a = _classify_tree(
                            q18_parent=q18_parent,
                            q18_eligible=q18_eligible,
                            nav14_parent=nav14_parent,
                            nav14_ready=nav14_ready,
                            ceiling_ok=ceiling_ok,
                        )
                        b = _classify_rules(
                            q18_parent=q18_parent,
                            q18_eligible=q18_eligible,
                            nav14_parent=nav14_parent,
                            nav14_ready=nav14_ready,
                            ceiling_ok=ceiling_ok,
                        )
                        if a != b:
                            raise AssertionError("Q19_DIFFERENT_J_MISMATCH")
                        checked += 1
    return checked


def main() -> None:
    receipt = issue_q8_producer_evidence_request(q18=current_q18_receipt(), nav14=nav14_projection_fixture())
    print(json.dumps(asdict(receipt), sort_keys=True, indent=2, default=lambda obj: obj.value if isinstance(obj, Enum) else obj))


if __name__ == "__main__":
    main()
