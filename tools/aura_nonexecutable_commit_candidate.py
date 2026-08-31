#!/usr/bin/env python3
"""O66: compose a pre-attempt envelope with a proposal/lifecycle relation.

D0 / HS1 / NONPROMOTING.

O66 owns one narrow relation only. O65 remains the owner of owner-resolved
pre-attempt admission and concurrency. Q20 remains the owner of the exact proposal
<-> closed-world lifecycle relation. This module can mint only a deterministic,
NON-EXECUTABLE commit-candidate identity when both parent objects describe the same
proposal/source/authority consequence.

A commit candidate is not an execution lease, provider authorization, commit-time
authorization witness, or effect receipt. Every use at an external effect boundary
must be freshly revalidated by the appropriate effect owner.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

PRE_ATTEMPT_SCHEMA = "AURA-PRE-ATTEMPT-ADMISSION-RECEIPT-v1"
LIFECYCLE_RELATION_SCHEMA = "AURA-OWNER-RESOLVED-PROPOSAL-LIFECYCLE-BRIDGE-v1"
CANDIDATE_SCHEMA = "AURA-NONEXECUTABLE-COMMIT-CANDIDATE-v1"
PRE_ATTEMPT_ELIGIBLE = "PRE_ATTEMPT_ENVELOPE_ELIGIBLE"
CURRENT_PROPOSAL = "CURRENT_NONEXECUTABLE"
TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
CANDIDATE_ELIGIBLE = "NONEXECUTABLE_COMMIT_CANDIDATE_ELIGIBLE"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")


@dataclass(frozen=True)
class PreAttemptEnvelopeRef:
    """Semantic operands attested by the O65 owner at its terminal proof cut."""

    schema_version: str
    owner_ref: str
    semantic_generation: str
    disposition: str
    receipt_digest: str
    proposal_id: str
    proposal_basis_digest: str
    proposal_source_generation: str
    pre_attempt_id: str
    policy_generation: str
    policy_digest: str
    authority_scope: str
    expected_route_fingerprint: str
    expected_observer_identity: str
    action_parameters_digest: str
    resource_envelope_digest: str
    concurrency_scope_digest: str
    effect_ceiling_digest: str
    proposal_current: bool
    policy_current: bool
    concurrent_live_attempt_conflict: bool | None
    revalidation_required_at_effect_boundary: bool
    execution_authorized: bool
    execution_lease_minted: bool
    provider_effect_authorized: bool
    provider_effect_started: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_deploy_spend_public_financial_human_effect: bool

    def validate(self) -> None:
        if self.schema_version != PRE_ATTEMPT_SCHEMA:
            raise ValueError("PRE_ATTEMPT_SCHEMA_MISMATCH")
        for value, name in (
            (self.owner_ref, "PRE_ATTEMPT_OWNER_REF"),
            (self.semantic_generation, "PRE_ATTEMPT_SEMANTIC_GENERATION"),
            (self.proposal_source_generation, "PROPOSAL_SOURCE_GENERATION"),
            (self.policy_generation, "PRE_ATTEMPT_POLICY_GENERATION"),
            (self.authority_scope, "PRE_ATTEMPT_AUTHORITY_SCOPE"),
            (self.expected_route_fingerprint, "PRE_ATTEMPT_EXPECTED_ROUTE"),
            (self.expected_observer_identity, "PRE_ATTEMPT_EXPECTED_OBSERVER"),
        ):
            _required(value, name)
        for value, name in (
            (self.receipt_digest, "PRE_ATTEMPT_RECEIPT_DIGEST"),
            (self.proposal_id, "PRE_ATTEMPT_PROPOSAL_ID"),
            (self.proposal_basis_digest, "PRE_ATTEMPT_PROPOSAL_BASIS_DIGEST"),
            (self.pre_attempt_id, "PRE_ATTEMPT_ID"),
            (self.policy_digest, "PRE_ATTEMPT_POLICY_DIGEST"),
            (self.action_parameters_digest, "PRE_ATTEMPT_ACTION_PARAMETERS_DIGEST"),
            (self.resource_envelope_digest, "PRE_ATTEMPT_RESOURCE_ENVELOPE_DIGEST"),
            (self.concurrency_scope_digest, "PRE_ATTEMPT_CONCURRENCY_SCOPE_DIGEST"),
            (self.effect_ceiling_digest, "PRE_ATTEMPT_EFFECT_CEILING_DIGEST"),
        ):
            _sha256(value, name)
        if self.disposition != PRE_ATTEMPT_ELIGIBLE:
            raise ValueError("PRE_ATTEMPT_NOT_ELIGIBLE")
        if self.proposal_current is not True:
            raise ValueError("PRE_ATTEMPT_PROPOSAL_NOT_CURRENT")
        if self.policy_current is not True:
            raise ValueError("PRE_ATTEMPT_POLICY_NOT_CURRENT")
        if self.concurrent_live_attempt_conflict is not False:
            raise ValueError("PRE_ATTEMPT_CONCURRENCY_NOT_CLEAR")
        if self.revalidation_required_at_effect_boundary is not True:
            raise ValueError("PRE_ATTEMPT_EFFECT_BOUNDARY_REVALIDATION_REQUIRED")
        forbidden = (
            self.execution_authorized,
            self.execution_lease_minted,
            self.provider_effect_authorized,
            self.provider_effect_started,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("PRE_ATTEMPT_PARENT_EXCEEDS_NONPROMOTION_CEILING")

    @property
    def semantic_ref_digest(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": "AURA-O65-PRE-ATTEMPT-SEMANTIC-REF-v1",
                "owner_ref": self.owner_ref,
                "semantic_generation": self.semantic_generation,
                "receipt_digest": self.receipt_digest,
                "proposal_id": self.proposal_id,
                "proposal_basis_digest": self.proposal_basis_digest,
                "proposal_source_generation": self.proposal_source_generation,
                "pre_attempt_id": self.pre_attempt_id,
                "policy_generation": self.policy_generation,
                "policy_digest": self.policy_digest,
                "authority_scope": self.authority_scope,
                "expected_route_fingerprint": self.expected_route_fingerprint,
                "expected_observer_identity": self.expected_observer_identity,
                "action_parameters_digest": self.action_parameters_digest,
                "resource_envelope_digest": self.resource_envelope_digest,
                "concurrency_scope_digest": self.concurrency_scope_digest,
                "effect_ceiling_digest": self.effect_ceiling_digest,
            }
        )


@dataclass(frozen=True)
class ProposalLifecycleRelationRef:
    """Semantic operands attested by the Q20 relation owner at its terminal proof cut."""

    schema_version: str
    owner_ref: str
    semantic_generation: str
    receipt_digest: str
    proposal_id: str
    proposal_basis_digest: str
    proposal_currentness_state: str
    model_objective_id: str
    model_attempt_id: str
    model_output_digest: str
    lifecycle_source_generation: str
    lifecycle_authority_scope: str
    proposal_ref_present: bool
    proposal_ref_required_by_policy: bool
    source_generation_bound_to_proposal: bool
    authority_scope_bound_to_proposal: bool
    consequence_key_bound_to_proposal: bool
    lifecycle_terminal_state: str
    lifecycle_reason_code: str
    semantic_commit_eligible: bool
    semantic_commit_key: str | None
    execution_authority_granted: bool
    provider_effect_authority_granted: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_deploy_spend_public_human_effect_authorized: bool

    def validate(self) -> None:
        if self.schema_version != LIFECYCLE_RELATION_SCHEMA:
            raise ValueError("PROPOSAL_LIFECYCLE_RELATION_SCHEMA_MISMATCH")
        for value, name in (
            (self.owner_ref, "LIFECYCLE_RELATION_OWNER_REF"),
            (self.semantic_generation, "LIFECYCLE_RELATION_SEMANTIC_GENERATION"),
            (self.model_objective_id, "LIFECYCLE_MODEL_OBJECTIVE_ID"),
            (self.model_attempt_id, "LIFECYCLE_MODEL_ATTEMPT_ID"),
            (self.lifecycle_source_generation, "LIFECYCLE_SOURCE_GENERATION"),
            (self.lifecycle_authority_scope, "LIFECYCLE_AUTHORITY_SCOPE"),
            (self.lifecycle_reason_code, "LIFECYCLE_REASON_CODE"),
        ):
            _required(value, name)
        for value, name in (
            (self.receipt_digest, "LIFECYCLE_RELATION_RECEIPT_DIGEST"),
            (self.proposal_id, "LIFECYCLE_PROPOSAL_ID"),
            (self.proposal_basis_digest, "LIFECYCLE_PROPOSAL_BASIS_DIGEST"),
            (self.model_output_digest, "LIFECYCLE_MODEL_OUTPUT_DIGEST"),
        ):
            _sha256(value, name)
        if self.proposal_currentness_state != CURRENT_PROPOSAL:
            raise ValueError("LIFECYCLE_PROPOSAL_NOT_CURRENT")
        required_true = (
            self.proposal_ref_present,
            self.proposal_ref_required_by_policy,
            self.source_generation_bound_to_proposal,
            self.authority_scope_bound_to_proposal,
            self.consequence_key_bound_to_proposal,
            self.semantic_commit_eligible,
        )
        if any(value is not True for value in required_true):
            raise ValueError("LIFECYCLE_RELATIONAL_GATE_NOT_SATISFIED")
        if self.lifecycle_terminal_state != TERMINAL_SUCCESS:
            raise ValueError("LIFECYCLE_NOT_TERMINAL_SUCCESS")
        if self.semantic_commit_key is None:
            raise ValueError("LIFECYCLE_SEMANTIC_COMMIT_KEY_REQUIRED")
        _sha256(self.semantic_commit_key, "LIFECYCLE_SEMANTIC_COMMIT_KEY")
        forbidden = (
            self.execution_authority_granted,
            self.provider_effect_authority_granted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_human_effect_authorized,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("LIFECYCLE_PARENT_EXCEEDS_NONPROMOTION_CEILING")

    @property
    def semantic_ref_digest(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": "AURA-Q20-PROPOSAL-LIFECYCLE-SEMANTIC-REF-v1",
                "owner_ref": self.owner_ref,
                "semantic_generation": self.semantic_generation,
                "receipt_digest": self.receipt_digest,
                "proposal_id": self.proposal_id,
                "proposal_basis_digest": self.proposal_basis_digest,
                "model_objective_id": self.model_objective_id,
                "model_attempt_id": self.model_attempt_id,
                "model_output_digest": self.model_output_digest,
                "lifecycle_source_generation": self.lifecycle_source_generation,
                "lifecycle_authority_scope": self.lifecycle_authority_scope,
                "lifecycle_reason_code": self.lifecycle_reason_code,
                "semantic_commit_key": self.semantic_commit_key,
            }
        )


@dataclass(frozen=True)
class CommitCandidateReceipt:
    schema_version: str
    disposition: str
    reason_code: str
    proposal_id: str
    proposal_basis_digest: str
    commit_candidate_id: str | None
    pre_attempt_id: str
    semantic_commit_key: str
    authority_scope: str
    source_generation: str
    pre_attempt_policy_generation: str
    pre_attempt_policy_digest: str
    expected_route_fingerprint: str
    expected_observer_identity: str
    action_parameters_digest: str
    resource_envelope_digest: str
    concurrency_scope_digest: str
    effect_ceiling_digest: str
    pre_attempt_semantic_ref_digest: str
    lifecycle_semantic_ref_digest: str
    minimum_invalidated_cone: tuple[str, ...]
    revalidation_required_at_effect_boundary: bool = True
    execution_authorized: bool = False
    execution_lease_minted: bool = False
    commit_authorized: bool = False
    provider_effect_authorized: bool = False
    provider_effect_started: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.revalidation_required_at_effect_boundary is not True:
            raise ValueError("COMMIT_CANDIDATE_REQUIRES_EFFECT_BOUNDARY_REVALIDATION")
        forbidden = (
            self.execution_authorized,
            self.execution_lease_minted,
            self.commit_authorized,
            self.provider_effect_authorized,
            self.provider_effect_started,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("COMMIT_CANDIDATE_CANNOT_CARRY_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": CANDIDATE_SCHEMA, "receipt": asdict(self)})


def _hold(
    *, pre_attempt: PreAttemptEnvelopeRef, lifecycle: ProposalLifecycleRelationRef,
    reason_code: str, cone: tuple[str, ...]
) -> CommitCandidateReceipt:
    receipt = CommitCandidateReceipt(
        schema_version=CANDIDATE_SCHEMA,
        disposition=f"HOLD_{reason_code}",
        reason_code=reason_code,
        proposal_id=pre_attempt.proposal_id,
        proposal_basis_digest=pre_attempt.proposal_basis_digest,
        commit_candidate_id=None,
        pre_attempt_id=pre_attempt.pre_attempt_id,
        semantic_commit_key=lifecycle.semantic_commit_key or "0" * 64,
        authority_scope=pre_attempt.authority_scope,
        source_generation=pre_attempt.proposal_source_generation,
        pre_attempt_policy_generation=pre_attempt.policy_generation,
        pre_attempt_policy_digest=pre_attempt.policy_digest,
        expected_route_fingerprint=pre_attempt.expected_route_fingerprint,
        expected_observer_identity=pre_attempt.expected_observer_identity,
        action_parameters_digest=pre_attempt.action_parameters_digest,
        resource_envelope_digest=pre_attempt.resource_envelope_digest,
        concurrency_scope_digest=pre_attempt.concurrency_scope_digest,
        effect_ceiling_digest=pre_attempt.effect_ceiling_digest,
        pre_attempt_semantic_ref_digest=pre_attempt.semantic_ref_digest,
        lifecycle_semantic_ref_digest=lifecycle.semantic_ref_digest,
        minimum_invalidated_cone=cone,
    )
    receipt.validate_claim_ceiling()
    return receipt


def create_nonexecutable_commit_candidate(
    *, pre_attempt: PreAttemptEnvelopeRef, lifecycle: ProposalLifecycleRelationRef
) -> CommitCandidateReceipt:
    """Join two exact parent objects without granting commit/effect authority."""
    pre_attempt.validate()
    lifecycle.validate()

    if pre_attempt.proposal_id != lifecycle.proposal_id:
        return _hold(
            pre_attempt=pre_attempt, lifecycle=lifecycle,
            reason_code="PROPOSAL_ID_MISMATCH", cone=("proposal_identity",),
        )
    if pre_attempt.proposal_basis_digest != lifecycle.proposal_basis_digest:
        return _hold(
            pre_attempt=pre_attempt, lifecycle=lifecycle,
            reason_code="PROPOSAL_BASIS_MISMATCH", cone=("proposal_basis",),
        )
    if pre_attempt.proposal_source_generation != lifecycle.lifecycle_source_generation:
        return _hold(
            pre_attempt=pre_attempt, lifecycle=lifecycle,
            reason_code="SOURCE_GENERATION_MISMATCH", cone=("source_currentness",),
        )
    if pre_attempt.authority_scope != lifecycle.lifecycle_authority_scope:
        return _hold(
            pre_attempt=pre_attempt, lifecycle=lifecycle,
            reason_code="AUTHORITY_SCOPE_MISMATCH", cone=("authority_scope",),
        )

    identity = {
        "proposal_id": pre_attempt.proposal_id,
        "proposal_basis_digest": pre_attempt.proposal_basis_digest,
        "source_generation": pre_attempt.proposal_source_generation,
        "authority_scope": pre_attempt.authority_scope,
        "pre_attempt_id": pre_attempt.pre_attempt_id,
        "pre_attempt_policy_generation": pre_attempt.policy_generation,
        "pre_attempt_policy_digest": pre_attempt.policy_digest,
        "expected_route_fingerprint": pre_attempt.expected_route_fingerprint,
        "expected_observer_identity": pre_attempt.expected_observer_identity,
        "action_parameters_digest": pre_attempt.action_parameters_digest,
        "resource_envelope_digest": pre_attempt.resource_envelope_digest,
        "concurrency_scope_digest": pre_attempt.concurrency_scope_digest,
        "effect_ceiling_digest": pre_attempt.effect_ceiling_digest,
        "semantic_commit_key": lifecycle.semantic_commit_key,
        "lifecycle_model_objective_id": lifecycle.model_objective_id,
        "lifecycle_model_output_digest": lifecycle.model_output_digest,
        "pre_attempt_semantic_ref_digest": pre_attempt.semantic_ref_digest,
        "lifecycle_semantic_ref_digest": lifecycle.semantic_ref_digest,
    }
    receipt = CommitCandidateReceipt(
        schema_version=CANDIDATE_SCHEMA,
        disposition=CANDIDATE_ELIGIBLE,
        reason_code="EXACT_PRE_ATTEMPT_AND_LIFECYCLE_RELATION_COMMUTE",
        proposal_id=pre_attempt.proposal_id,
        proposal_basis_digest=pre_attempt.proposal_basis_digest,
        commit_candidate_id=_sha({"domain": CANDIDATE_SCHEMA, "identity": identity}),
        pre_attempt_id=pre_attempt.pre_attempt_id,
        semantic_commit_key=lifecycle.semantic_commit_key,
        authority_scope=pre_attempt.authority_scope,
        source_generation=pre_attempt.proposal_source_generation,
        pre_attempt_policy_generation=pre_attempt.policy_generation,
        pre_attempt_policy_digest=pre_attempt.policy_digest,
        expected_route_fingerprint=pre_attempt.expected_route_fingerprint,
        expected_observer_identity=pre_attempt.expected_observer_identity,
        action_parameters_digest=pre_attempt.action_parameters_digest,
        resource_envelope_digest=pre_attempt.resource_envelope_digest,
        concurrency_scope_digest=pre_attempt.concurrency_scope_digest,
        effect_ceiling_digest=pre_attempt.effect_ceiling_digest,
        pre_attempt_semantic_ref_digest=pre_attempt.semantic_ref_digest,
        lifecycle_semantic_ref_digest=lifecycle.semantic_ref_digest,
        minimum_invalidated_cone=(),
    )
    receipt.validate_claim_ceiling()
    return receipt


def main() -> None:
    print(
        json.dumps(
            {
                "schema": CANDIDATE_SCHEMA,
                "laws": [
                    "PreAttemptEligibility!=CommitAuthority",
                    "LifecycleTerminalSuccess!=EffectAuthority",
                    "CommitCandidate!=ExecutionLease!=EffectCommit",
                    "CommitCandidateRequiresSameProposalAcrossPreAttemptAndLifecycle",
                    "ProposalSourceAndAuthorityMustCommuteAcrossParents",
                    "PreAttemptRouteObserverResourceAndConcurrencyRemainIdentityBearing",
                    "EffectBoundaryRequiresFreshOwnerRevalidation",
                    "UnknownConcurrency!=NoConflict",
                    "LifecycleHostWitness!=FuturePreAttemptRoute",
                    "K27Coordinate!=CommitEligibility!=Authority",
                ],
                "claim_ceiling": {
                    "execution_authorized": False,
                    "execution_lease_minted": False,
                    "commit_authorized": False,
                    "provider_effect_authorized": False,
                    "provider_effect_started": False,
                    "semantic_k27_authority": False,
                    "native_private_transformer_kv_accessed": False,
                    "gate10_promoted": False,
                    "merge_deploy_spend_public_financial_human_effect": False,
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
