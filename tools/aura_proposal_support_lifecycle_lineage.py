#!/usr/bin/env python3
"""O67: attach bounded materialization/evidence support to an exact Q21 lifecycle lineage.

D0 / HS1 / NONPROMOTING.

Exactly two independently hosted semantic parents are consumed:
- O65-R / PR #708: bounded authority-scoped evidence support for the exact
  materialization-bound Q20 proposal basis.
- Q21 / PR #709: content-addressed pre-attempt <-> terminal lifecycle lineage
  for an exact proposal id and proposal-basis digest.

This relation proves only that the bounded support belongs to the same proposal
basis carried by the lineage. It does not resolve live proposal currentness,
prove host consumption/causality, reinterpret lifecycle terminality, authorize
execution or provider effects, mint K27 authority, access native/private KV,
promote Gate-10, merge, deploy, spend, or create public/financial/human effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "AURA-PROPOSAL-SUPPORT-LIFECYCLE-LINEAGE-v1"
O65R_SCHEMA = "AURA-AUTHORITY-MATERIALIZATION-PROPOSAL-CONFORMANCE-v2"
Q21_SCHEMA = "AURA-PRE-ATTEMPT-LIFECYCLE-LINEAGE-v1"
HEX = frozenset("0123456789abcdef")

O65R_SEMANTIC_HEAD = "fff1e38f78c54c387c1131543ce332d115ad7f5c"
O65R_PROOF_HEAD = "361b01579ab2debc34f4b836c3ea605de635a8c3"
O65R_RUN = 33411109692
O65R_JOB = 99550605797
O65R_WORKFLOW = "Aura O65-R Authority Materialization Proposal Conformance Proof"

Q21_SEMANTIC_HEAD = "e83d18126cae4e95abf679f74ee585e6a4025831"
Q21_RUN = 33410723482
Q21_JOB = 99549322339
Q21_WORKFLOW = "Aura Q21 Pre-Attempt Lifecycle Lineage"

Q20_MATERIALIZATION_RELATION_DIGEST = "45b20b3992b6dc1872776c368cb05e3cf27229732f2b183539c664776434d171"
Q20_MATERIALIZATION_BOUND_PROPOSAL_BASIS = "e94c482318e0c25ad7052328fcd6722ac85470ba756ac7d6e2056131f4ff0c0d"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value


@dataclass(frozen=True)
class BoundedProposalSupportProjection:
    schema: str
    semantic_head: str
    proof_head: str
    run_id: int
    job_id: int
    workflow_name: str
    proposal_basis_digest: str
    materialization_relation_digest: str
    proposal_representation_fingerprint: str
    authority_fingerprint: str
    admission_policy_fingerprint: str
    evidence_admission_fingerprint: str
    proposal_evidence_support_digest: str
    conformance_receipt_digest: str
    bounded_evidence_supports_exact_proposal: bool
    live_proposal_currentness_resolved: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_or_deployment_authorized: bool = False

    def validate(self) -> None:
        if self.schema != O65R_SCHEMA:
            raise ValueError("O67_O65R_SCHEMA_MISMATCH")
        if (
            self.semantic_head,
            self.proof_head,
            self.run_id,
            self.job_id,
            self.workflow_name,
        ) != (
            O65R_SEMANTIC_HEAD,
            O65R_PROOF_HEAD,
            O65R_RUN,
            O65R_JOB,
            O65R_WORKFLOW,
        ):
            raise ValueError("O67_O65R_EXACT_HOSTED_PARENT_REQUIRED")
        for value, name in (
            (self.proposal_basis_digest, "O65R_PROPOSAL_BASIS_DIGEST"),
            (self.materialization_relation_digest, "O65R_MATERIALIZATION_RELATION_DIGEST"),
            (self.proposal_representation_fingerprint, "O65R_PROPOSAL_REPRESENTATION_FINGERPRINT"),
            (self.authority_fingerprint, "O65R_AUTHORITY_FINGERPRINT"),
            (self.admission_policy_fingerprint, "O65R_ADMISSION_POLICY_FINGERPRINT"),
            (self.evidence_admission_fingerprint, "O65R_EVIDENCE_ADMISSION_FINGERPRINT"),
            (self.proposal_evidence_support_digest, "O65R_PROPOSAL_EVIDENCE_SUPPORT_DIGEST"),
            (self.conformance_receipt_digest, "O65R_CONFORMANCE_RECEIPT_DIGEST"),
        ):
            _sha256(value, name)
        if self.proposal_basis_digest != Q20_MATERIALIZATION_BOUND_PROPOSAL_BASIS:
            raise ValueError("O67_O65R_MATERIALIZATION_BOUND_BASIS_MISMATCH")
        if self.materialization_relation_digest != Q20_MATERIALIZATION_RELATION_DIGEST:
            raise ValueError("O67_O65R_MATERIALIZATION_RELATION_MISMATCH")
        if self.bounded_evidence_supports_exact_proposal is not True:
            raise ValueError("O67_O65R_BOUNDED_SUPPORT_REQUIRED")
        forbidden = (
            self.live_proposal_currentness_resolved,
            self.execution_authorized,
            self.provider_effect_authorized,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_or_deployment_authorized,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("O67_O65R_CLAIM_CEILING_WIDENED")


@dataclass(frozen=True)
class PreAttemptLifecycleLineageProjection:
    schema: str
    semantic_head: str
    run_id: int
    job_id: int
    workflow_name: str
    proposal_id: str
    proposal_basis_digest: str
    pre_attempt_id: str
    owner_state_epoch: str
    pre_attempt_policy_generation: str
    lifecycle_model_attempt_id: str
    lifecycle_model_output_digest: str
    lifecycle_semantic_commit_key: str
    lineage_digest: str
    lineage_receipt_digest: str
    proposal_identity_shared: bool
    lineage_association_bound: bool
    effect_boundary_revalidation_still_required: bool
    route_observer_to_host_witness_relation_proven: bool = False
    pre_attempt_caused_execution: bool = False
    pre_attempt_authorized_execution: bool = False
    terminal_result_retroactively_authorizes_pre_attempt: bool = False
    execution_lease_minted: bool = False
    execution_authority_granted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False

    def validate(self) -> None:
        if self.schema != Q21_SCHEMA:
            raise ValueError("O67_Q21_SCHEMA_MISMATCH")
        if (self.semantic_head, self.run_id, self.job_id, self.workflow_name) != (
            Q21_SEMANTIC_HEAD,
            Q21_RUN,
            Q21_JOB,
            Q21_WORKFLOW,
        ):
            raise ValueError("O67_Q21_EXACT_HOSTED_PARENT_REQUIRED")
        for value, name in (
            (self.proposal_id, "Q21_PROPOSAL_ID"),
            (self.proposal_basis_digest, "Q21_PROPOSAL_BASIS_DIGEST"),
            (self.pre_attempt_id, "Q21_PRE_ATTEMPT_ID"),
            (self.lifecycle_model_output_digest, "Q21_MODEL_OUTPUT_DIGEST"),
            (self.lifecycle_semantic_commit_key, "Q21_SEMANTIC_COMMIT_KEY"),
            (self.lineage_digest, "Q21_LINEAGE_DIGEST"),
            (self.lineage_receipt_digest, "Q21_LINEAGE_RECEIPT_DIGEST"),
        ):
            _sha256(value, name)
        _required(self.owner_state_epoch, "Q21_OWNER_STATE_EPOCH")
        _required(self.pre_attempt_policy_generation, "Q21_PRE_ATTEMPT_POLICY_GENERATION")
        _required(self.lifecycle_model_attempt_id, "Q21_MODEL_ATTEMPT_ID")
        if self.proposal_identity_shared is not True or self.lineage_association_bound is not True:
            raise ValueError("O67_Q21_EXACT_LINEAGE_ASSOCIATION_REQUIRED")
        if self.effect_boundary_revalidation_still_required is not True:
            raise ValueError("O67_Q21_EFFECT_BOUNDARY_REVALIDATION_REQUIRED")
        forbidden = (
            self.route_observer_to_host_witness_relation_proven,
            self.pre_attempt_caused_execution,
            self.pre_attempt_authorized_execution,
            self.terminal_result_retroactively_authorizes_pre_attempt,
            self.execution_lease_minted,
            self.execution_authority_granted,
            self.provider_effect_authority_granted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect_authorized,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("O67_Q21_CAUSAL_OR_EFFECT_CEILING_WIDENED")


@dataclass(frozen=True)
class ProposalSupportLifecycleLineageDecision:
    disposition: str
    reason_code: str
    proposal_id: str
    proposal_basis_digest: str
    materialization_relation_digest: str
    proposal_evidence_support_digest: str
    conformance_receipt_digest: str
    q21_lineage_digest: str
    q21_lineage_receipt_digest: str
    support_lineage_digest: str | None
    bounded_support_attached_to_exact_lineage: bool
    live_proposal_currentness_resolved: bool = False
    host_consumption_or_causality_proven: bool = False
    lifecycle_terminality_reinterpreted: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"schema": SCHEMA, "receipt": asdict(self)})


def attach_bounded_support_to_lineage(
    *, support: BoundedProposalSupportProjection,
    lineage: PreAttemptLifecycleLineageProjection,
) -> ProposalSupportLifecycleLineageDecision:
    support.validate()
    lineage.validate()

    base = dict(
        proposal_id=lineage.proposal_id,
        proposal_basis_digest=lineage.proposal_basis_digest,
        materialization_relation_digest=support.materialization_relation_digest,
        proposal_evidence_support_digest=support.proposal_evidence_support_digest,
        conformance_receipt_digest=support.conformance_receipt_digest,
        q21_lineage_digest=lineage.lineage_digest,
        q21_lineage_receipt_digest=lineage.lineage_receipt_digest,
    )
    if support.proposal_basis_digest != lineage.proposal_basis_digest:
        return ProposalSupportLifecycleLineageDecision(
            disposition="REVIEW",
            reason_code="PROPOSAL_BASIS_DIVERGENCE",
            support_lineage_digest=None,
            bounded_support_attached_to_exact_lineage=False,
            **base,
        )

    relation_digest = _sha(
        {
            "domain": SCHEMA,
            "o65r_parent": {
                "semantic_head": support.semantic_head,
                "proof_head": support.proof_head,
                "run": support.run_id,
                "job": support.job_id,
            },
            "q21_parent": {
                "semantic_head": lineage.semantic_head,
                "run": lineage.run_id,
                "job": lineage.job_id,
            },
            "proposal_id": lineage.proposal_id,
            "proposal_basis_digest": lineage.proposal_basis_digest,
            "materialization_relation_digest": support.materialization_relation_digest,
            "proposal_evidence_support_digest": support.proposal_evidence_support_digest,
            "o65r_conformance_receipt_digest": support.conformance_receipt_digest,
            "q21_lineage_digest": lineage.lineage_digest,
            "q21_lineage_receipt_digest": lineage.lineage_receipt_digest,
            "currentness_owner": "DELEGATED_UNRESOLVED",
            "host_causality_owner": "DELEGATED_UNPROVEN",
            "authority_ceiling": "BOUNDED_SUPPORT_LINEAGE_NONEXECUTABLE",
        }
    )
    return ProposalSupportLifecycleLineageDecision(
        disposition="EXACT_BOUNDED_SUPPORT_LINEAGE",
        reason_code="BOUNDED_MATERIALIZATION_SUPPORT_AND_Q21_LINEAGE_SHARE_EXACT_PROPOSAL_BASIS",
        support_lineage_digest=relation_digest,
        bounded_support_attached_to_exact_lineage=True,
        **base,
    )


def example_support() -> BoundedProposalSupportProjection:
    return BoundedProposalSupportProjection(
        schema=O65R_SCHEMA,
        semantic_head=O65R_SEMANTIC_HEAD,
        proof_head=O65R_PROOF_HEAD,
        run_id=O65R_RUN,
        job_id=O65R_JOB,
        workflow_name=O65R_WORKFLOW,
        proposal_basis_digest=Q20_MATERIALIZATION_BOUND_PROPOSAL_BASIS,
        materialization_relation_digest=Q20_MATERIALIZATION_RELATION_DIGEST,
        proposal_representation_fingerprint="1" * 64,
        authority_fingerprint="2" * 64,
        admission_policy_fingerprint="3" * 64,
        evidence_admission_fingerprint="4" * 64,
        proposal_evidence_support_digest="5" * 64,
        conformance_receipt_digest="6" * 64,
        bounded_evidence_supports_exact_proposal=True,
    )


def example_lineage() -> PreAttemptLifecycleLineageProjection:
    return PreAttemptLifecycleLineageProjection(
        schema=Q21_SCHEMA,
        semantic_head=Q21_SEMANTIC_HEAD,
        run_id=Q21_RUN,
        job_id=Q21_JOB,
        workflow_name=Q21_WORKFLOW,
        proposal_id="7" * 64,
        proposal_basis_digest=Q20_MATERIALIZATION_BOUND_PROPOSAL_BASIS,
        pre_attempt_id="8" * 64,
        owner_state_epoch="epoch:o67:stable",
        pre_attempt_policy_generation="policy:o67:v1",
        lifecycle_model_attempt_id="attempt:o67:1",
        lifecycle_model_output_digest="9" * 64,
        lifecycle_semantic_commit_key="a" * 64,
        lineage_digest="b" * 64,
        lineage_receipt_digest="c" * 64,
        proposal_identity_shared=True,
        lineage_association_bound=True,
        effect_boundary_revalidation_still_required=True,
    )


def main() -> int:
    result = attach_bounded_support_to_lineage(
        support=example_support(), lineage=example_lineage()
    )
    print(json.dumps({**asdict(result), "receipt_digest": result.receipt_digest}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
