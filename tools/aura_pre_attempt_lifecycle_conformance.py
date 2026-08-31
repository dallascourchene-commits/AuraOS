#!/usr/bin/env python3
"""O66: bind an epoch-serializable pre-attempt envelope to typed-witness lifecycle lineage.

D0 / HS1 / NONPROMOTING.

O65 remains the owner of proposal -> pre-attempt admission and its owner-state epoch.
Q20/PR705 remains the owner of proposal -> closed-world lifecycle relation; O62 remains
the owner of typed review/host/result terminality. This module owns only the missing
cross-parent lineage relation.

A valid relation means the lifecycle result is bound to the exact pre-attempt envelope
through proposal identity, a required pre-attempt artifact, source/authority/consequence
bindings, route/observer identity, and one stable relation-scoped owner epoch. It is not
an execution lease and does not require the lifecycle outcome to be successful.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol

from tools import aura_bounded_proposal_capsule as o63
from tools import aura_closed_world_result_lifecycle_gate as o62
from tools import aura_owner_resolved_proposal_lifecycle_bridge as q20
from tools import aura_pre_attempt_admission as o65

SCHEMA = "AURA-PRE-ATTEMPT-LIFECYCLE-CONFORMANCE-v1"
BOUND = "PRE_ATTEMPT_LIFECYCLE_LINEAGE_BOUND"

O65_HEAD = "7efca33d95f6dc39c4e159250d45373b260060ed"
O65_RUN = 33410032496
O65_JOB = 99546999922
Q20_HEAD = "22e72fd3de7b008752bbb5176347d61518f4e83a"
Q20_RUN = 33409821076
Q20_JOB = 99546289815
CONVERGENCE_COMMIT = "88502b4f44018de688386a7e71a5143a4471e28f"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: str | None, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value


class PreAttemptLifecycleOwnerResolver(o65.PreAttemptOwnerResolver, Protocol):
    """Owner resolver whose epoch spans the cross-parent lineage read set."""

    def resolve_pre_attempt_lifecycle_epoch(
        self, *, proposal_id: str, objective_id: str
    ) -> str | None: ...


@dataclass(frozen=True)
class PreAttemptLifecycleRelationReceipt:
    schema: str
    disposition: str
    reason_code: str
    relation_id: str | None
    proposal_id: str
    proposal_basis_digest: str
    pre_attempt_id: str | None
    pre_attempt_receipt_digest: str | None
    pre_attempt_owner_state_epoch: str | None
    pre_attempt_policy_generation: str | None
    relation_owner_epoch: str | None
    lifecycle_relation_receipt_digest: str | None
    lifecycle_policy_generation: str
    lifecycle_source_generation: str
    lifecycle_authority_scope: str
    lifecycle_objective_id: str
    lifecycle_attempt_id: str
    lifecycle_output_digest: str
    required_pre_attempt_ref: str | None
    pre_attempt_ref_present_in_model: bool
    pre_attempt_ref_required_by_policy: bool
    proposal_identity_bound: bool
    route_bound: bool
    observer_bound: bool
    lifecycle_relational_gates_bound: bool
    lifecycle_terminal_state: str
    lifecycle_reason_code: str
    semantic_commit_eligible: bool
    semantic_commit_key: str | None
    reusable_evidence_eligible: bool
    revalidation_required_at_effect_boundary: bool = True
    execution_authority_granted: bool = False
    execution_lease_minted: bool = False
    provider_effect_authority_granted: bool = False
    provider_effect_started: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect_authorized: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("O66_SCHEMA_MISMATCH")
        if self.disposition == BOUND:
            _required(self.relation_id, "RELATION_ID")
            _required(self.pre_attempt_id, "PRE_ATTEMPT_ID")
            _required(self.pre_attempt_owner_state_epoch, "PRE_ATTEMPT_OWNER_STATE_EPOCH")
            _required(self.relation_owner_epoch, "RELATION_OWNER_EPOCH")
            if not (
                self.pre_attempt_ref_present_in_model
                and self.pre_attempt_ref_required_by_policy
                and self.proposal_identity_bound
                and self.route_bound
                and self.observer_bound
                and self.lifecycle_relational_gates_bound
            ):
                raise ValueError("BOUND_O66_RECEIPT_REQUIRES_ALL_RELATIONAL_GATES")
        elif self.relation_id is not None:
            raise ValueError("UNBOUND_O66_RECEIPT_MUST_NOT_MINT_RELATION_ID")
        if self.revalidation_required_at_effect_boundary is not True:
            raise ValueError("O66_EFFECT_BOUNDARY_REVALIDATION_REQUIRED")
        forbidden = (
            self.execution_authority_granted,
            self.execution_lease_minted,
            self.provider_effect_authority_granted,
            self.provider_effect_started,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect_authorized,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("O66_RELATION_CANNOT_CARRY_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["receipt_digest"] = self.receipt_digest
        return body


def pre_attempt_artifact_ref(pre_attempt_id: str) -> str:
    return f"pre_attempt:{_required(pre_attempt_id, 'PRE_ATTEMPT_ID')}"


def _resolve_relation_epoch(
    *,
    owner_resolver: PreAttemptLifecycleOwnerResolver,
    proposal_id: str,
    objective_id: str,
) -> tuple[str | None, str | None]:
    try:
        value = owner_resolver.resolve_pre_attempt_lifecycle_epoch(
            proposal_id=proposal_id, objective_id=objective_id
        )
    except Exception:
        return None, "RELATION_OWNER_EPOCH_RESOLVER_ERROR"
    if value is None:
        return None, "RELATION_OWNER_EPOCH_UNAVAILABLE_OR_UNKNOWN"
    if not isinstance(value, str) or not value.strip():
        return None, "RELATION_OWNER_EPOCH_INVALID"
    return value, None


def _receipt(
    *,
    capsule: o63.ProposalCapsule,
    model: o62.ModelResultEnvelope,
    policy: o62.LifecyclePolicy,
    disposition: str,
    reason_code: str,
    relation_id: str | None = None,
    pre: o65.PreAttemptAdmissionReceipt | None = None,
    relation_epoch: str | None = None,
    lifecycle: q20.ProposalLifecycleRelationReceipt | None = None,
    required_ref: str | None = None,
    ref_present: bool = False,
    ref_required: bool = False,
    proposal_bound: bool = False,
    route_bound: bool = False,
    observer_bound: bool = False,
    lifecycle_bound: bool = False,
) -> PreAttemptLifecycleRelationReceipt:
    out = PreAttemptLifecycleRelationReceipt(
        schema=SCHEMA,
        disposition=disposition,
        reason_code=reason_code,
        relation_id=relation_id,
        proposal_id=capsule.proposal_id,
        proposal_basis_digest=capsule.proposal_basis_digest,
        pre_attempt_id=pre.pre_attempt_id if pre else None,
        pre_attempt_receipt_digest=pre.receipt_digest if pre else None,
        pre_attempt_owner_state_epoch=pre.owner_state_epoch if pre else None,
        pre_attempt_policy_generation=pre.policy_generation if pre else None,
        relation_owner_epoch=relation_epoch,
        lifecycle_relation_receipt_digest=lifecycle.receipt_digest if lifecycle else None,
        lifecycle_policy_generation=policy.policy_generation_ref,
        lifecycle_source_generation=policy.current_source_generation_ref,
        lifecycle_authority_scope=policy.authority_scope,
        lifecycle_objective_id=model.objective_id,
        lifecycle_attempt_id=model.attempt_id,
        lifecycle_output_digest=model.output_digest,
        required_pre_attempt_ref=required_ref,
        pre_attempt_ref_present_in_model=ref_present,
        pre_attempt_ref_required_by_policy=ref_required,
        proposal_identity_bound=proposal_bound,
        route_bound=route_bound,
        observer_bound=observer_bound,
        lifecycle_relational_gates_bound=lifecycle_bound,
        lifecycle_terminal_state=lifecycle.lifecycle_terminal_state if lifecycle else "HOLD",
        lifecycle_reason_code=lifecycle.lifecycle_reason_code if lifecycle else "NOT_EVALUATED",
        semantic_commit_eligible=lifecycle.semantic_commit_eligible if lifecycle else False,
        semantic_commit_key=lifecycle.semantic_commit_key if lifecycle else None,
        reusable_evidence_eligible=lifecycle.reusable_evidence_eligible if lifecycle else False,
    )
    out.validate_claim_ceiling()
    return out


def evaluate_pre_attempt_lifecycle_conformance(
    *,
    capsule: o63.ProposalCapsule,
    owner_resolver: PreAttemptLifecycleOwnerResolver | None,
    model: o62.ModelResultEnvelope,
    policy: o62.LifecyclePolicy,
    host: o62.HostExecutionReceipt | None = None,
    reviewer: o62.IndependentReviewReceipt | None = None,
) -> PreAttemptLifecycleRelationReceipt:
    """Bind an exact O65 pre-attempt envelope to an exact Q20/O62 lifecycle result.

    The relation epoch is independent of O65's internal proposal-scoped epoch. It must
    remain stable across both parent evaluations, preventing a lineage receipt from
    being assembled from relation operands that never coexisted. No caller booleans or
    K27 coordinates participate in any gate.
    """
    capsule.validate_integrity()
    model.validate()
    policy.validate()

    if owner_resolver is None:
        return _receipt(
            capsule=capsule, model=model, policy=policy,
            disposition="HOLD_RELATION_OWNER_UNAVAILABLE",
            reason_code="RELATION_OWNER_UNAVAILABLE",
        )

    epoch_before, epoch_error = _resolve_relation_epoch(
        owner_resolver=owner_resolver,
        proposal_id=capsule.proposal_id,
        objective_id=model.objective_id,
    )
    if epoch_error is not None:
        return _receipt(
            capsule=capsule, model=model, policy=policy,
            disposition=f"HOLD_{epoch_error}", reason_code=epoch_error,
        )

    pre = o65.admit_pre_attempt(capsule=capsule, owner_resolver=owner_resolver)
    if pre.disposition != o65.ELIGIBLE or pre.pre_attempt_id is None:
        return _receipt(
            capsule=capsule, model=model, policy=policy,
            disposition="HOLD_PRE_ATTEMPT_NOT_ELIGIBLE",
            reason_code=f"PRE_ATTEMPT_NOT_ELIGIBLE:{pre.reason_code}",
            pre=pre, relation_epoch=epoch_before,
        )

    if model.attempt_id == pre.pre_attempt_id:
        return _receipt(
            capsule=capsule, model=model, policy=policy,
            disposition="HOLD_PRE_ATTEMPT_ATTEMPT_IDENTITY_CROSSCAST",
            reason_code="PRE_ATTEMPT_ID_MUST_NOT_BECOME_EXECUTION_ATTEMPT_ID",
            pre=pre, relation_epoch=epoch_before,
        )

    required_ref = pre_attempt_artifact_ref(pre.pre_attempt_id)
    ref_present = required_ref in model.artifact_refs
    ref_required = required_ref in policy.required_artifact_refs
    proposal_bound = (
        pre.proposal_id == capsule.proposal_id
        and pre.proposal_basis_digest == capsule.proposal_basis_digest
    )
    route_bound = (
        pre.expected_route_fingerprint is not None
        and pre.expected_route_fingerprint == policy.expected_route_fingerprint
    )
    observer_bound = (
        pre.expected_observer_identity is not None
        and pre.expected_observer_identity == policy.expected_observer_identity
    )

    lifecycle = q20.evaluate_owner_resolved_proposal_lifecycle(
        capsule=capsule,
        owner_resolver=owner_resolver,
        model=model,
        policy=policy,
        host=host,
        reviewer=reviewer,
    )
    lifecycle_bound = (
        lifecycle.proposal_currentness_state == "CURRENT_NONEXECUTABLE"
        and lifecycle.proposal_ref_present
        and lifecycle.proposal_ref_required_by_policy
        and lifecycle.source_generation_bound_to_proposal
        and lifecycle.authority_scope_bound_to_proposal
        and lifecycle.consequence_key_bound_to_proposal
        and lifecycle.proposal_id == capsule.proposal_id
        and lifecycle.proposal_basis_digest == capsule.proposal_basis_digest
    )

    relational_failures = (
        (ref_present, "PRE_ATTEMPT_ARTIFACT_REF_MISSING_FROM_MODEL"),
        (ref_required, "PRE_ATTEMPT_NOT_REQUIRED_BY_LIFECYCLE_POLICY"),
        (proposal_bound, "PRE_ATTEMPT_PROPOSAL_IDENTITY_MISMATCH"),
        (route_bound, "PRE_ATTEMPT_LIFECYCLE_ROUTE_MISMATCH"),
        (observer_bound, "PRE_ATTEMPT_LIFECYCLE_OBSERVER_MISMATCH"),
        (lifecycle_bound, f"PROPOSAL_LIFECYCLE_RELATION_NOT_BOUND:{lifecycle.lifecycle_reason_code}"),
    )
    for passed, reason in relational_failures:
        if not passed:
            return _receipt(
                capsule=capsule, model=model, policy=policy,
                disposition=f"HOLD_{reason.split(':', 1)[0]}",
                reason_code=reason,
                pre=pre, relation_epoch=epoch_before, lifecycle=lifecycle,
                required_ref=required_ref, ref_present=ref_present, ref_required=ref_required,
                proposal_bound=proposal_bound, route_bound=route_bound,
                observer_bound=observer_bound, lifecycle_bound=lifecycle_bound,
            )

    epoch_after, final_epoch_error = _resolve_relation_epoch(
        owner_resolver=owner_resolver,
        proposal_id=capsule.proposal_id,
        objective_id=model.objective_id,
    )
    if final_epoch_error is not None:
        return _receipt(
            capsule=capsule, model=model, policy=policy,
            disposition=f"HOLD_{final_epoch_error}", reason_code=final_epoch_error,
            pre=pre, relation_epoch=epoch_before, lifecycle=lifecycle,
            required_ref=required_ref, ref_present=True, ref_required=True,
            proposal_bound=True, route_bound=True, observer_bound=True,
            lifecycle_bound=True,
        )
    if epoch_after != epoch_before:
        return _receipt(
            capsule=capsule, model=model, policy=policy,
            disposition="HOLD_RELATION_OWNER_EPOCH_CHANGED_DURING_EVALUATION",
            reason_code="RELATION_OWNER_EPOCH_CHANGED_DURING_EVALUATION",
            pre=pre, relation_epoch=epoch_after, lifecycle=lifecycle,
            required_ref=required_ref, ref_present=True, ref_required=True,
            proposal_bound=True, route_bound=True, observer_bound=True,
            lifecycle_bound=True,
        )

    identity = {
        "proposal_id": capsule.proposal_id,
        "proposal_basis_digest": capsule.proposal_basis_digest,
        "pre_attempt_id": pre.pre_attempt_id,
        "pre_attempt_receipt_digest": pre.receipt_digest,
        "pre_attempt_owner_state_epoch": pre.owner_state_epoch,
        "pre_attempt_policy_generation": pre.policy_generation,
        "relation_owner_epoch": epoch_before,
        "required_pre_attempt_ref": required_ref,
        "route": pre.expected_route_fingerprint,
        "observer": pre.expected_observer_identity,
        "lifecycle_relation_receipt_digest": lifecycle.receipt_digest,
        "lifecycle_policy_generation": policy.policy_generation_ref,
        "lifecycle_source_generation": policy.current_source_generation_ref,
        "lifecycle_authority_scope": policy.authority_scope,
        "lifecycle_objective_id": model.objective_id,
        "lifecycle_attempt_id": model.attempt_id,
        "lifecycle_output_digest": model.output_digest,
    }
    relation_id = _sha({"domain": SCHEMA, "identity": identity})
    return _receipt(
        capsule=capsule, model=model, policy=policy,
        disposition=BOUND,
        reason_code="EXACT_PRE_ATTEMPT_AND_LIFECYCLE_LINEAGE_BOUND_IN_ONE_RELATION_EPOCH",
        relation_id=relation_id,
        pre=pre, relation_epoch=epoch_before, lifecycle=lifecycle,
        required_ref=required_ref, ref_present=True, ref_required=True,
        proposal_bound=True, route_bound=True, observer_bound=True,
        lifecycle_bound=True,
    )


def main() -> None:
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "parents": {
                    "o65_head": O65_HEAD,
                    "o65_run": O65_RUN,
                    "o65_job": O65_JOB,
                    "q20_head": Q20_HEAD,
                    "q20_run": Q20_RUN,
                    "q20_job": Q20_JOB,
                    "convergence_commit": CONVERGENCE_COMMIT,
                },
                "laws": [
                    "EpochSerializablePreAttempt!=TypedWitnessLifecycleUntilExactLineageRelation",
                    "PreAttemptId!=ExecutionAttemptId",
                    "PreAttemptArtifactMustBePresentAndPolicyRequired",
                    "PreAttemptRouteAndObserverMustEqualLifecycleRouteAndObserver",
                    "ProposalSourceAuthorityAndConsequenceRemainOwnedByQ20",
                    "LifecycleTerminalityRemainsOwnedByO62",
                    "RelationMayBindFailureWithoutPromotingSuccess",
                    "StableRelationEpochDoesNotAuthorizeExecution",
                    "K27Coordinate!=PreAttemptCurrentness!=LifecycleEvidence!=Authority",
                ],
                "claim_ceiling": {
                    "execution_authority": False,
                    "execution_lease": False,
                    "provider_effect_authority": False,
                    "provider_effect_started": False,
                    "semantic_k27_authority": False,
                    "native_private_transformer_kv_access": False,
                    "gate10": False,
                    "merge_deploy_spend_public_financial_human_effect": False,
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
