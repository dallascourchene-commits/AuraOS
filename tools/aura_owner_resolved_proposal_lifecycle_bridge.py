#!/usr/bin/env python3
"""Q20: bind owner-resolved proposal state to closed-world lifecycle evidence.

D0 / HS1 / NONPROMOTING.

This module is a relation owner only. O63 remains the owner of proposal identity and
currentness. O62 remains the owner of lifecycle/review/host-witness terminality.
Q20 proves that both refer to the same source generation, authority scope, exact
proposal artifact, and consequence key before O62 may evaluate the result.

A current proposal is never an execution lease. Host/review evidence must already
satisfy O62 when its policy requires them. K27 coordinates are deliberately absent
from all admission predicates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools import aura_bounded_proposal_capsule as o63
from tools import aura_closed_world_result_lifecycle_gate as o62

SCHEMA = "AURA-OWNER-RESOLVED-PROPOSAL-LIFECYCLE-BRIDGE-v1"
O63_SEMANTIC_HEAD = "1cdad597015615d1c34d236b271516196ac101cd"
O63_PROOF_HEAD = "70aa3db4f11d035b52a81992c05c052f59683377"
O63_RUN = 33407842585
O63_JOB = 99539751642
O62_SEMANTIC_HEAD = "51a31f9df1b13636f9878a4dcbb9dc2e3f8c757f"
O62_TEST_HEAD = "87253e487f110d7f119262c3a6159b296f90d62b"
O62_PROOF_HEAD = "2b74b7ceecbde0f16c3c68d3e81fab3d28a6c078"
O62_RUN = 33408547754
O62_JOB = 99542101386
CONVERGENCE_COMMIT = "66c2522c45a6d0da13ff232ad8c9cb9707159321"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def proposal_artifact_ref(capsule: o63.ProposalCapsule) -> str:
    capsule.validate_integrity()
    return f"proposal:{capsule.proposal_id}"


def proposal_consequence_key(
    capsule: o63.ProposalCapsule, *, objective_id: str, result_code: str
) -> str:
    capsule.validate_integrity()
    if not isinstance(objective_id, str) or not objective_id.strip():
        raise ValueError("OBJECTIVE_ID_REQUIRED")
    if not isinstance(result_code, str) or not result_code.strip():
        raise ValueError("RESULT_CODE_REQUIRED")
    return _sha(
        {
            "domain": "AURA-PROPOSAL-LIFECYCLE-CONSEQUENCE-v1",
            "proposal_id": capsule.proposal_id,
            "proposal_basis_digest": capsule.proposal_basis_digest,
            "objective_id": objective_id,
            "result_code": result_code,
        }
    )


@dataclass(frozen=True)
class ProposalLifecycleRelationReceipt:
    schema: str
    proposal_id: str
    proposal_basis_digest: str
    proposal_currentness_state: str
    proposal_currentness_reason: str
    model_objective_id: str
    model_attempt_id: str
    model_output_digest: str
    lifecycle_source_generation: str
    lifecycle_authority_scope: str
    proposal_ref_required: str
    proposal_ref_present: bool
    proposal_ref_required_by_policy: bool
    source_generation_bound_to_proposal: bool
    authority_scope_bound_to_proposal: bool
    consequence_key_bound_to_proposal: bool
    lifecycle_terminal_state: str
    lifecycle_reason_code: str
    semantic_commit_eligible: bool
    semantic_commit_key: str | None
    reusable_evidence_eligible: bool
    execution_authority_granted: bool = False
    provider_effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_human_effect_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def _relation(
    *,
    capsule: o63.ProposalCapsule,
    currentness: o63.ProposalCurrentnessDecision,
    model: o62.ModelResultEnvelope,
    policy: o62.LifecyclePolicy,
    proposal_ref_present: bool,
    proposal_ref_required_by_policy: bool,
    source_bound: bool,
    authority_bound: bool,
    consequence_bound: bool,
    terminal_state: str,
    reason_code: str,
    semantic_commit_eligible: bool = False,
    semantic_commit_key: str | None = None,
    reusable_evidence_eligible: bool = False,
) -> ProposalLifecycleRelationReceipt:
    return ProposalLifecycleRelationReceipt(
        schema=SCHEMA,
        proposal_id=capsule.proposal_id,
        proposal_basis_digest=capsule.proposal_basis_digest,
        proposal_currentness_state=currentness.state,
        proposal_currentness_reason=currentness.reason_code,
        model_objective_id=model.objective_id,
        model_attempt_id=model.attempt_id,
        model_output_digest=model.output_digest,
        lifecycle_source_generation=policy.current_source_generation_ref,
        lifecycle_authority_scope=policy.authority_scope,
        proposal_ref_required=proposal_artifact_ref(capsule),
        proposal_ref_present=proposal_ref_present,
        proposal_ref_required_by_policy=proposal_ref_required_by_policy,
        source_generation_bound_to_proposal=source_bound,
        authority_scope_bound_to_proposal=authority_bound,
        consequence_key_bound_to_proposal=consequence_bound,
        lifecycle_terminal_state=terminal_state,
        lifecycle_reason_code=reason_code,
        semantic_commit_eligible=semantic_commit_eligible,
        semantic_commit_key=semantic_commit_key,
        reusable_evidence_eligible=reusable_evidence_eligible,
    )


def evaluate_owner_resolved_proposal_lifecycle(
    *,
    capsule: o63.ProposalCapsule,
    owner_resolver: o63.ProposalOwnerResolver | None,
    model: o62.ModelResultEnvelope,
    policy: o62.LifecyclePolicy,
    host: o62.HostExecutionReceipt | None = None,
    reviewer: o62.IndependentReviewReceipt | None = None,
) -> ProposalLifecycleRelationReceipt:
    """Join O63 currentness with O62 lifecycle without widening either owner.

    Q20 fails before the lifecycle reducer when the model/policy does not bind the
    exact proposal consequence. Once those relational gates pass, O62 receives the
    original model/policy/host/reviewer values unchanged and remains the sole owner of
    terminality.
    """
    capsule.validate_integrity()
    model.validate()
    policy.validate()

    currentness = o63.revalidate_proposal_capsule(
        capsule=capsule, owner_resolver=owner_resolver
    )
    required_ref = proposal_artifact_ref(capsule)
    ref_present = required_ref in model.artifact_refs
    ref_required = required_ref in policy.required_artifact_refs
    source_bound = (
        capsule.basis.source_admission_generation
        == model.source_generation_ref
        == policy.current_source_generation_ref
    )
    authority_bound = (
        capsule.basis.authority_scope == model.authority_scope == policy.authority_scope
    )
    expected_consequence = proposal_consequence_key(
        capsule, objective_id=model.objective_id, result_code=model.result_code
    )
    consequence_bound = model.consequence_key == expected_consequence

    if currentness.state != "CURRENT_NONEXECUTABLE":
        return _relation(
            capsule=capsule, currentness=currentness, model=model, policy=policy,
            proposal_ref_present=ref_present, proposal_ref_required_by_policy=ref_required,
            source_bound=source_bound, authority_bound=authority_bound,
            consequence_bound=consequence_bound, terminal_state="HOLD",
            reason_code="PROPOSAL_NOT_CURRENT_OWNER_RESOLVED",
        )
    if not ref_present:
        return _relation(
            capsule=capsule, currentness=currentness, model=model, policy=policy,
            proposal_ref_present=False, proposal_ref_required_by_policy=ref_required,
            source_bound=source_bound, authority_bound=authority_bound,
            consequence_bound=consequence_bound, terminal_state="HOLD",
            reason_code="PROPOSAL_ARTIFACT_REF_MISSING_FROM_MODEL",
        )
    if not ref_required:
        return _relation(
            capsule=capsule, currentness=currentness, model=model, policy=policy,
            proposal_ref_present=True, proposal_ref_required_by_policy=False,
            source_bound=source_bound, authority_bound=authority_bound,
            consequence_bound=consequence_bound, terminal_state="HOLD",
            reason_code="PROPOSAL_NOT_REQUIRED_BY_LIFECYCLE_POLICY",
        )
    if not source_bound:
        return _relation(
            capsule=capsule, currentness=currentness, model=model, policy=policy,
            proposal_ref_present=True, proposal_ref_required_by_policy=True,
            source_bound=False, authority_bound=authority_bound,
            consequence_bound=consequence_bound, terminal_state="HOLD",
            reason_code="PROPOSAL_LIFECYCLE_SOURCE_GENERATION_MISMATCH",
        )
    if not authority_bound:
        return _relation(
            capsule=capsule, currentness=currentness, model=model, policy=policy,
            proposal_ref_present=True, proposal_ref_required_by_policy=True,
            source_bound=True, authority_bound=False,
            consequence_bound=consequence_bound, terminal_state="HOLD",
            reason_code="PROPOSAL_LIFECYCLE_AUTHORITY_SCOPE_MISMATCH",
        )
    if not consequence_bound:
        return _relation(
            capsule=capsule, currentness=currentness, model=model, policy=policy,
            proposal_ref_present=True, proposal_ref_required_by_policy=True,
            source_bound=True, authority_bound=True,
            consequence_bound=False, terminal_state="HOLD",
            reason_code="PROPOSAL_CONSEQUENCE_KEY_MISMATCH",
        )

    decision = o62.reduce_result_lifecycle(
        model=model, policy=policy, host=host, reviewer=reviewer
    )
    return _relation(
        capsule=capsule,
        currentness=currentness,
        model=model,
        policy=policy,
        proposal_ref_present=True,
        proposal_ref_required_by_policy=True,
        source_bound=True,
        authority_bound=True,
        consequence_bound=True,
        terminal_state=decision.terminal_state,
        reason_code=decision.reason_code,
        semantic_commit_eligible=decision.semantic_commit_eligible,
        semantic_commit_key=decision.semantic_commit_key,
        reusable_evidence_eligible=decision.reusable_evidence_eligible,
    )


def main() -> None:
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "parents": {
                    "o63_semantic_head": O63_SEMANTIC_HEAD,
                    "o63_run": O63_RUN,
                    "o62_semantic_head": O62_SEMANTIC_HEAD,
                    "o62_run": O62_RUN,
                    "convergence_commit": CONVERGENCE_COMMIT,
                },
                "laws": [
                    "CurrentProposalRequiresOwnerResolvedOperands",
                    "ProposalIdentityMustBindLifecycleConsequenceKey",
                    "ProposalSourceGenerationMustEqualLifecycleSourceGeneration",
                    "ProposalAuthorityScopeMustEqualLifecycleAuthorityScope",
                    "TypedExternalWitnessesRemainOwnedByClosedWorldLifecycle",
                    "CurrentProposal!=ExecutionLease!=EffectAuthority",
                    "K27Coordinate!=ProposalCurrentness!=LifecycleEvidence!=Authority",
                ],
                "claim_ceiling": {
                    "execution_authority": False,
                    "provider_effect_authority": False,
                    "semantic_k27_authority": False,
                    "native_private_transformer_kv_access": False,
                    "gate10": False,
                    "merge_deploy_spend_public_human_effect": False,
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
