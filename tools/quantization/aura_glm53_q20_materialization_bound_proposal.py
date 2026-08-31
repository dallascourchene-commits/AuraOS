#!/usr/bin/env python3
"""Q20: bind a representation-scoped proposal to execution-qualified materialization.

Exactly two semantic parents are consumed:
- Q19: a bounded 2.25-bpw representation-specific proposal basis.
- Q15: execution-qualified portable materialization evidence for the exact Q14
  canonical E8 canary page set.

The join closes a provenance edge only.  Q15's provider execution qualifies the
materialization evidence producer; it is not execution authority for the proposal,
model, inference, deployment, or any provider effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any

SCHEMA = "AURA_GLM53_Q20_MATERIALIZATION_BOUND_PROPOSAL_V1"

Q19_HEAD = "e54a4fba9a4b54e3afd4b0eb19124250183a1304"
Q19_RUN = 33407053398
Q19_JOB = 99537108141
Q19_RECEIPT_DIGEST = "4e96f101f91b3696cedd948aa98ef93b21647e91eeabe301ed97644f1459a616"
Q19_PROPOSAL_BASIS_DIGEST = "8b3f0d4ed5f92f2d41745b0f4136b64ff245525c4b533c6e2700b0b4335042cd"
Q19_REPRESENTATION_IDENTITY_DIGEST = "61048a6f227942b514a94a2e5ec46aacee32d9422f4fda7722adcd789213fb0c"
Q19_SOURCE_GATE_GENERATION = "9dab15c3a0bb0b9ad2408fdd54b09cfcfa1373d8"
Q19_DISPOSITION = "ELIGIBLE_BOUNDED_PROPOSAL"
Q19_SCOPE = "GLM53_Q6_2P25_CODEC_RATE_TWO_OFFICIAL_TILES"
Q19_E8_SCHEME = "AURA_E8_BALL10_16BIT_REF_V1"
Q19_SCALAR_SCHEME = "AURA_OPT_SYMMETRIC_4LEVEL_FP16_V1"

Q15_HEAD = "b4791c47f7e1b1a8078688b2721957fc4c863a90"
Q15_RUN = 33406119920
Q15_JOB = 99534015610
Q15_ARTIFACT_ID = 9763246083
Q15_ARTIFACT_DIGEST = "sha256:812aee1771143c2c598c2610c8387f9540af7341ed778377181c8e036db5116e"
Q15_PAGE_SET_DIGEST = "4811719dd71a1c8b3258000286955a7ae31895c46a0a34bbfcf5fec3717bdf41"

Q6_RECEIPT_DIGEST = "5173b6c1df5f6f889a7912574c51beac546b09a92457cc32ba5918a8f6bd28a4"
EXACT_CODEC_RATE_BPW = 2.25
ACCOUNTING_DOMAIN = "CODEC_PAYLOAD_ONLY"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")


@dataclass(frozen=True)
class Q19ProposalRef:
    head: str = Q19_HEAD
    run: int = Q19_RUN
    job: int = Q19_JOB
    receipt_digest: str = Q19_RECEIPT_DIGEST
    proposal_basis_digest: str = Q19_PROPOSAL_BASIS_DIGEST
    representation_identity_digest: str = Q19_REPRESENTATION_IDENTITY_DIGEST
    source_gate_generation: str = Q19_SOURCE_GATE_GENERATION
    disposition: str = Q19_DISPOSITION
    representation_scope: str = Q19_SCOPE
    q6_representation_scheme: str = Q19_E8_SCHEME
    scalar_scheme: str = Q19_SCALAR_SCHEME
    exact_codec_rate_bpw: float = EXACT_CODEC_RATE_BPW
    codec_rate_domain_only: bool = True
    container_rate_comparison_claimed: bool = False
    proposal_eligible: bool = True
    q18_1p25_proposal_mutated: bool = False
    q18_evidence_crosscast_into_q19: bool = False
    execution_authority_granted: bool = False
    effect_authority_granted: bool = False

    def validate(self) -> None:
        expected = (Q19_HEAD, Q19_RUN, Q19_JOB, Q19_RECEIPT_DIGEST, Q19_PROPOSAL_BASIS_DIGEST,
                    Q19_REPRESENTATION_IDENTITY_DIGEST, Q19_SOURCE_GATE_GENERATION)
        got = (self.head, self.run, self.job, self.receipt_digest, self.proposal_basis_digest,
               self.representation_identity_digest, self.source_gate_generation)
        if got != expected:
            raise ValueError("Q19_EXACT_TERMINAL_GENERATION_REQUIRED")
        for value, name in ((self.receipt_digest, "Q19_RECEIPT"),
                            (self.proposal_basis_digest, "Q19_PROPOSAL_BASIS"),
                            (self.representation_identity_digest, "Q19_REPRESENTATION_IDENTITY")):
            _sha256(value, name)
        if self.disposition != Q19_DISPOSITION or self.proposal_eligible is not True:
            raise ValueError("Q19_BOUNDED_PROPOSAL_ELIGIBILITY_REQUIRED")
        if self.representation_scope != Q19_SCOPE:
            raise ValueError("Q19_REPRESENTATION_SCOPE_DRIFT")
        if self.q6_representation_scheme != Q19_E8_SCHEME or self.scalar_scheme != Q19_SCALAR_SCHEME:
            raise ValueError("Q19_REPRESENTATION_SCHEME_DRIFT")
        if not math.isclose(float(self.exact_codec_rate_bpw), EXACT_CODEC_RATE_BPW, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("Q19_CODEC_RATE_DRIFT")
        if self.codec_rate_domain_only is not True or self.container_rate_comparison_claimed is not False:
            raise ValueError("Q19_ACCOUNTING_DOMAIN_CROSSCAST")
        if self.q18_1p25_proposal_mutated is not False or self.q18_evidence_crosscast_into_q19 is not False:
            raise ValueError("Q19_Q18_COLLISION_BOUNDARY_DRIFT")
        if self.execution_authority_granted is not False or self.effect_authority_granted is not False:
            raise ValueError("Q19_PROPOSAL_CANNOT_CARRY_EFFECT_AUTHORITY")


@dataclass(frozen=True)
class Q15MaterializationRef:
    head: str = Q15_HEAD
    run: int = Q15_RUN
    job: int = Q15_JOB
    artifact_id: int = Q15_ARTIFACT_ID
    artifact_digest: str = Q15_ARTIFACT_DIGEST
    page_set_digest: str = Q15_PAGE_SET_DIGEST
    execution_qualified_portable_materialization_evidence: bool = True
    full_representative_page_set_proven: bool = False
    model_execution_proven: bool = False
    inference_proven: bool = False
    generalized_quality_or_performance_proven: bool = False

    def validate(self) -> None:
        if (self.head, self.run, self.job, self.artifact_id, self.artifact_digest, self.page_set_digest) != (
            Q15_HEAD, Q15_RUN, Q15_JOB, Q15_ARTIFACT_ID, Q15_ARTIFACT_DIGEST, Q15_PAGE_SET_DIGEST
        ):
            raise ValueError("Q15_EXACT_TERMINAL_MATERIALIZATION_GENERATION_REQUIRED")
        if not self.artifact_digest.startswith("sha256:"):
            raise ValueError("Q15_ARTIFACT_DIGEST_DOMAIN_REQUIRED")
        _sha256(self.artifact_digest.split(":", 1)[1], "Q15_ARTIFACT")
        _sha256(self.page_set_digest, "Q15_PAGE_SET")
        if self.execution_qualified_portable_materialization_evidence is not True:
            raise ValueError("Q15_EXECUTION_QUALIFIED_MATERIALIZATION_REQUIRED")
        if any((self.full_representative_page_set_proven, self.model_execution_proven,
                self.inference_proven, self.generalized_quality_or_performance_proven)):
            raise ValueError("Q15_CLAIM_CEILING_WIDENED")


@dataclass(frozen=True)
class MaterializationBoundProposalReceipt:
    schema: str
    q19_head: str
    q19_run: int
    q19_job: int
    q19_receipt_digest: str
    q19_proposal_basis_digest: str
    q19_representation_identity_digest: str
    q15_head: str
    q15_run: int
    q15_job: int
    q15_artifact_id: int
    q15_artifact_digest: str
    q15_page_set_digest: str
    q6_receipt_digest: str
    q6_page_set_digest: str
    accounting_domain: str
    exact_codec_rate_bpw: float
    same_materialized_page_set_bound: bool
    q19_proposal_basis_preserved: bool
    q18_proposal_identity_preserved: bool
    execution_qualified_materialization_bound: bool
    materialization_relation_digest: str
    materialization_bound_proposal_basis_digest: str
    q15_provider_execution_is_proposal_execution_authority: bool
    full_representative_page_set_proven: bool
    model_execution_proven: bool
    inference_proven: bool
    model_quality_or_runtime_proven: bool
    execution_authority_granted: bool
    effect_authority_granted: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool
    reason: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def bind_materialization_to_proposal(
    *,
    q19: Q19ProposalRef,
    q15: Q15MaterializationRef,
    q6_receipt_digest: str,
    q6_page_set_digest: str,
    accounting_domain: str,
    exact_codec_rate_bpw: float,
) -> MaterializationBoundProposalReceipt:
    q19.validate()
    q15.validate()
    if q6_receipt_digest != Q6_RECEIPT_DIGEST:
        raise ValueError("Q6_EXACT_RECEIPT_REQUIRED")
    _sha256(q6_receipt_digest, "Q6_RECEIPT")
    if q6_page_set_digest != q15.page_set_digest:
        raise ValueError("Q6_Q15_PAGE_SET_RELATION_NOT_BOUND")
    _sha256(q6_page_set_digest, "Q6_PAGE_SET")
    if accounting_domain != ACCOUNTING_DOMAIN:
        raise ValueError("Q20_CODEC_ACCOUNTING_DOMAIN_REQUIRED")
    if not math.isclose(float(exact_codec_rate_bpw), EXACT_CODEC_RATE_BPW, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Q20_CODEC_RATE_MISMATCH")

    relation = _sha({
        "domain": "AURA-Q20-MATERIALIZATION-RELATION-v1",
        "q19_representation_identity_digest": q19.representation_identity_digest,
        "q6_receipt_digest": q6_receipt_digest,
        "q6_page_set_digest": q6_page_set_digest,
        "q15_proof_head": q15.head,
        "q15_artifact_digest": q15.artifact_digest,
        "q15_page_set_digest": q15.page_set_digest,
        "accounting_domain": accounting_domain,
        "exact_codec_rate_bpw": EXACT_CODEC_RATE_BPW,
    })
    bound_basis = _sha({
        "domain": "AURA-Q20-MATERIALIZATION-BOUND-PROPOSAL-BASIS-v1",
        "q19_proposal_basis_digest": q19.proposal_basis_digest,
        "materialization_relation_digest": relation,
        "q19_source_gate_generation": q19.source_gate_generation,
        "authority_ceiling": "NONEXECUTABLE_D0",
    })

    return MaterializationBoundProposalReceipt(
        schema=SCHEMA,
        q19_head=q19.head,
        q19_run=q19.run,
        q19_job=q19.job,
        q19_receipt_digest=q19.receipt_digest,
        q19_proposal_basis_digest=q19.proposal_basis_digest,
        q19_representation_identity_digest=q19.representation_identity_digest,
        q15_head=q15.head,
        q15_run=q15.run,
        q15_job=q15.job,
        q15_artifact_id=q15.artifact_id,
        q15_artifact_digest=q15.artifact_digest,
        q15_page_set_digest=q15.page_set_digest,
        q6_receipt_digest=q6_receipt_digest,
        q6_page_set_digest=q6_page_set_digest,
        accounting_domain=accounting_domain,
        exact_codec_rate_bpw=EXACT_CODEC_RATE_BPW,
        same_materialized_page_set_bound=True,
        q19_proposal_basis_preserved=True,
        q18_proposal_identity_preserved=True,
        execution_qualified_materialization_bound=True,
        materialization_relation_digest=relation,
        materialization_bound_proposal_basis_digest=bound_basis,
        q15_provider_execution_is_proposal_execution_authority=False,
        full_representative_page_set_proven=False,
        model_execution_proven=False,
        inference_proven=False,
        model_quality_or_runtime_proven=False,
        execution_authority_granted=False,
        effect_authority_granted=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
        reason="EXECUTION_QUALIFIED_PORTABLE_MATERIALIZATION_BOUND_TO_REPRESENTATION_PROPOSAL_BASIS",
    )


def exact_terminal_fixture() -> MaterializationBoundProposalReceipt:
    return bind_materialization_to_proposal(
        q19=Q19ProposalRef(),
        q15=Q15MaterializationRef(),
        q6_receipt_digest=Q6_RECEIPT_DIGEST,
        q6_page_set_digest=Q15_PAGE_SET_DIGEST,
        accounting_domain=ACCOUNTING_DOMAIN,
        exact_codec_rate_bpw=EXACT_CODEC_RATE_BPW,
    )


def main() -> None:
    receipt = exact_terminal_fixture()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "RepresentationProposalBasis!=MaterializationEvidenceUntilExactPageSetRelation",
        "Q15ProviderExecution!=ProposalExecutionAuthority",
        "MaterializationEvidence!=ModelExecution!=Inference",
        "NewRepresentationProposalMustNotMutatePriorRepresentationProposal",
        "K27Coordinate!=SourceCurrentness!=ProposalAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
