from __future__ import annotations

from dataclasses import replace

import pytest

from aura_event_contracts import sanitize_payload
from aura_relational_authority import (
    ApprovalAttestation,
    AttestationDecision,
    AuthorityGrant,
    QuorumPolicy,
    RiskClass,
    TrustedCheckpoint,
    evaluate_governance,
    stable_digest,
    stable_id,
    verify_receipt_chain,
)
from aura_workflow_gates import WorkflowState, can_transition, evaluate_gate, get_gate

NOW = 1_800_000_000.0
ACTION_ID = "review-action"
ACTION_DIGEST = stable_digest({"patch": "exact"})
AUTH_REF = "authority:reviewer"
ATTEST_REFS = {"attestation:one", "attestation:two"}
CHECKPOINT_REF = "checkpoint:signed"


def make_grant(*, policy_scope: str = "workflow.commit", capability_scope: str = "commit") -> AuthorityGrant:
    return AuthorityGrant.create(
        principal_id="reviewer",
        authorized_functional_roles=("APPROVE",),
        policy_scopes=(policy_scope,),
        capability_scopes=(capability_scope,),
        valid_from=NOW - 100,
        expires_at=NOW + 1_000,
        externally_verified_authority_ref=AUTH_REF,
        verified_authority_refs={AUTH_REF},
        now=NOW,
    )


def make_attestation(
    grant: AuthorityGrant,
    *,
    attestation_ref: str = "attestation:one",
    created_at: float = NOW - 10,
    policy_scope: str = "workflow.commit",
    capability_scope: str = "commit",
) -> ApprovalAttestation:
    return ApprovalAttestation.create(
        action_id=ACTION_ID,
        action_payload_digest=ACTION_DIGEST,
        principal_id=grant.principal_id,
        grant=grant,
        decision=AttestationDecision.APPROVE,
        functional_role="APPROVE",
        policy_scope=policy_scope,
        capability_scope=capability_scope,
        public_rationale="Exact evidence supports this bounded action.",
        evidence_refs=("evidence:exact",),
        externally_verified_attestation_ref=attestation_ref,
        verified_authority_refs={AUTH_REF},
        verified_attestation_refs=ATTEST_REFS,
        created_at=created_at,
        expires_at=NOW + 500,
        now=NOW,
    )


def make_decision(*, policy_scope: str = "workflow.commit", capability_scope: str = "commit"):
    grant = make_grant(policy_scope=policy_scope, capability_scope=capability_scope)
    approval = make_attestation(
        grant, policy_scope=policy_scope, capability_scope=capability_scope
    )
    policy = QuorumPolicy.create(
        risk_class=RiskClass.LOW,
        minimum_approval_count=1,
        required_functional_roles=("APPROVE",),
        minimum_distinct_principals=1,
    )
    return evaluate_governance(
        action_id=ACTION_ID,
        action_payload_digest=ACTION_DIGEST,
        policy_scope=policy_scope,
        capability_scope=capability_scope,
        grants=(grant,),
        attestations=(approval,),
        quorum_policy=policy,
        verified_authority_refs={AUTH_REF},
        verified_attestation_refs=ATTEST_REFS,
        now=NOW,
    )


def reidentify_policy(policy: QuorumPolicy) -> QuorumPolicy:
    payload = policy.to_dict()
    payload.pop("policy_id")
    payload.pop("policy_digest")
    return replace(
        policy,
        policy_id=stable_id("quorum-policy", payload),
        policy_digest=stable_digest(payload),
    )


@pytest.mark.parametrize(
    "field_name",
    ("chain.of.thought", "model/chain-of-thought", "internal:scratchpad"),
)
def test_private_reasoning_punctuation_aliases_are_rejected(field_name: str) -> None:
    with pytest.raises(ValueError, match="private reasoning field"):
        sanitize_payload({field_name: "must not persist"})


def test_private_reasoning_acronym_does_not_block_unrelated_words() -> None:
    assert sanitize_payload({"mascot": "turtle"}) == {"mascot": "turtle"}


def test_punctuation_separated_secret_field_is_redacted() -> None:
    assert sanitize_payload({"api.key": "secret-value"}) == {
        "api.key": "[REDACTED]"
    }


def test_commit_gate_scope_cannot_be_downgraded_by_evidence() -> None:
    decision = make_decision(policy_scope="workflow.read", capability_scope="read")
    result = evaluate_gate(
        "HUMAN_APPROVED_FOR_COMMIT",
        {
            "verified": True,
            "tests_pass": True,
            "governance_decision": decision,
            "verified_governance_decision_ids": (decision.decision_id,),
            "requested_action_id": ACTION_ID,
            "requested_action_digest": ACTION_DIGEST,
            "required_policy_scope": "workflow.read",
            "required_capability_scope": "read",
            "authority_now": NOW,
        },
    )
    assert result["can_proceed"] is False
    assert result["required_policy_scope"] == "workflow.commit"
    assert result["required_capability_scope"] == "commit"


def test_string_human_approval_does_not_pass_legacy_gate() -> None:
    result = evaluate_gate(
        "HUMAN_APPROVED_FOR_COMMIT",
        {"human_approval": "false", "verified": True, "tests_pass": True},
    )
    assert result["can_proceed"] is False
    assert result["legacy_human_approval_used"] is False


def test_verified_decision_ids_must_be_a_collection() -> None:
    decision = make_decision()
    result = evaluate_gate(
        "HUMAN_APPROVED_FOR_COMMIT",
        {
            "verified": True,
            "tests_pass": True,
            "governance_decision": decision,
            "verified_governance_decision_ids": decision.decision_id,
            "requested_action_id": ACTION_ID,
            "requested_action_digest": ACTION_DIGEST,
            "authority_now": NOW,
        },
    )
    assert result["can_proceed"] is False
    assert any(
        "must be a collection" in item
        for item in result["authority_missing_reasons"]
    )


def test_patch_transition_order_matches_the_state_machine() -> None:
    assert can_transition(WorkflowState.AGENT_RUNNING, WorkflowState.PATCH_PROPOSED)
    assert can_transition(WorkflowState.REPAIR_REQUIRED, WorkflowState.PATCH_PROPOSED)
    assert not can_transition(WorkflowState.VERIFIED, WorkflowState.PATCH_PROPOSED)
    assert "prior_state_agent_running_or_repair" in get_gate(
        WorkflowState.PATCH_PROPOSED
    ).required_evidence


def test_duplicate_attestation_cannot_inflate_quorum() -> None:
    grant = make_grant()
    approval = make_attestation(grant)
    policy = QuorumPolicy.create(
        risk_class=RiskClass.LOW,
        minimum_approval_count=2,
        required_functional_roles=("APPROVE",),
        minimum_distinct_principals=1,
    )
    decision = evaluate_governance(
        action_id=ACTION_ID,
        action_payload_digest=ACTION_DIGEST,
        policy_scope="workflow.commit",
        capability_scope="commit",
        grants=(grant,),
        attestations=(approval, approval),
        quorum_policy=policy,
        verified_authority_refs={AUTH_REF},
        verified_attestation_refs=ATTEST_REFS,
        now=NOW,
    )
    assert decision.authorized is False
    assert decision.missing_quorum_count == 1
    assert any(
        item.startswith("duplicate_attestation:")
        for item in decision.authority_missing_reasons
    )


def test_same_principal_role_cannot_submit_multiple_counted_approvals() -> None:
    grant = make_grant()
    first = make_attestation(
        grant, attestation_ref="attestation:one", created_at=NOW - 10
    )
    second = make_attestation(
        grant, attestation_ref="attestation:two", created_at=NOW - 9
    )
    policy = QuorumPolicy.create(
        risk_class=RiskClass.LOW,
        minimum_approval_count=2,
        required_functional_roles=("APPROVE",),
        minimum_distinct_principals=1,
    )
    decision = evaluate_governance(
        action_id=ACTION_ID,
        action_payload_digest=ACTION_DIGEST,
        policy_scope="workflow.commit",
        capability_scope="commit",
        grants=(grant,),
        attestations=(first, second),
        quorum_policy=policy,
        verified_authority_refs={AUTH_REF},
        verified_attestation_refs=ATTEST_REFS,
        now=NOW,
    )
    assert decision.authorized is False
    assert decision.missing_quorum_count == 1
    assert (
        "duplicate_principal_role_approval:reviewer:APPROVE"
        in decision.authority_missing_reasons
    )


def test_attestation_cannot_be_backdated_before_grant() -> None:
    with pytest.raises(ValueError, match="predate"):
        make_attestation(make_grant(), created_at=NOW - 200)


def test_tampered_grant_is_rejected_before_attestation_creation() -> None:
    tampered = replace(make_grant(), principal_id="fabricated")
    with pytest.raises(ValueError, match="digest or ID"):
        make_attestation(tampered)


def test_future_governance_decision_is_not_active() -> None:
    future = replace(make_decision(), created_at=NOW + 100)
    payload = future.to_dict()
    payload.pop("decision_id")
    payload.pop("decision_digest")
    future = replace(
        future,
        decision_id=stable_id("governance-decision", payload),
        decision_digest=stable_digest(payload),
    )
    with pytest.raises(ValueError, match="not active yet"):
        future.validate_for_action(
            action_id=ACTION_ID,
            action_payload_digest=ACTION_DIGEST,
            policy_scope="workflow.commit",
            capability_scope="commit",
            now=NOW,
        )


def test_non_emergency_policy_rejects_emergency_only_fields() -> None:
    policy = QuorumPolicy.create(
        risk_class=RiskClass.LOW,
        minimum_approval_count=1,
        required_functional_roles=("APPROVE",),
        minimum_distinct_principals=1,
    )
    tampered = reidentify_policy(
        replace(policy, emergency_allowed_policy_scopes=("workflow.commit",))
    )
    with pytest.raises(ValueError, match="emergency policy scopes"):
        tampered.validate()


def test_tampered_trusted_checkpoint_is_rejected() -> None:
    checkpoint = TrustedCheckpoint.create(
        ledger_id="ledger-1",
        sequence_number=4,
        chain_digest="chain-4",
        externally_signed_checkpoint_ref=CHECKPOINT_REF,
        verified_checkpoint_refs={CHECKPOINT_REF},
        created_at=NOW,
    )
    result = verify_receipt_chain(
        (),
        trusted_checkpoint=replace(checkpoint, chain_digest="fabricated"),
        verified_checkpoint_refs={CHECKPOINT_REF},
    )
    assert result.valid is False
    assert any(
        item.startswith("invalid_trusted_checkpoint:") for item in result.errors
    )


def test_empty_suffix_is_anchored_to_trusted_checkpoint() -> None:
    checkpoint = TrustedCheckpoint.create(
        ledger_id="ledger-1",
        sequence_number=4,
        chain_digest="chain-4",
        externally_signed_checkpoint_ref=CHECKPOINT_REF,
        verified_checkpoint_refs={CHECKPOINT_REF},
        created_at=NOW,
    )
    result = verify_receipt_chain(
        (),
        trusted_checkpoint=checkpoint,
        verified_checkpoint_refs={CHECKPOINT_REF},
    )
    assert result.valid is True
    assert result.checkpoint_verified is True
    assert result.ledger_id == "ledger-1"
    assert result.final_sequence_number == 4
    assert result.final_chain_digest == "chain-4"
