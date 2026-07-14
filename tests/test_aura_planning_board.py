from types import SimpleNamespace

import pytest

from aura_planning_board import (
    ActionSpec,
    AuthorityRequirement,
    AuthoritySpec,
    ConstraintKind,
    ConstraintSpec,
    ContinuityEvidence,
    ContinuityLevel,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PredicateSpec,
    ResourceDemand,
    RetryPolicy,
    ReversibilityClass,
    TypedPort,
    VerifierRequirement,
    board_from_goap_plan,
    canonical_json,
    project_continuity,
)


def _board(*, with_receipt=True):
    goal = GoalSpec(
        goal_id="goal-1",
        description="Produce a verified bounded patch",
        desired_predicates=(
            PredicateSpec("goal-pred", "patch_verified", "equals", True),
        ),
        evidence_refs=("evidence:goal",),
    )
    action = ActionSpec(
        action_id="action-1",
        name="build_patch",
        domain="code",
        preconditions=(PredicateSpec("pre-1", "grounded", "equals", True),),
        effects=(EffectSpec("effect-1", "patch_verified", True),),
        constraints=(
            ConstraintSpec(
                "constraint-1",
                ConstraintKind.POLICY,
                "bounded edit only",
                evidence_ref="constraint:policy",
            ),
        ),
        ports=(TypedPort("diff", "output", "unified-diff"),),
        capability_requirements=("code.patch.propose",),
        verifier_requirements=(
            VerifierRequirement("pytest", "receipt:pytest" if with_receipt else None),
        ),
        authority=AuthoritySpec(
            AuthorityRequirement.NONE,
            policy_ref="policy:no-execution-authority",
        ),
        resource_demand=ResourceDemand(
            context_tokens=1000,
            estimated_cost=0.01,
            human_attention_minutes=2,
        ),
        reversibility=ReversibilityClass.REVERSIBLE,
        idempotency_key="patch:goal-1",
    )
    return PlanningBoard(
        board_id="board-1",
        goal=goal,
        actions=(action,),
        initial_state_ref="state:initial",
    )


def test_canonical_serialization_and_digest_are_deterministic():
    first = _board()
    second = _board()
    assert canonical_json(first) == canonical_json(second)
    assert first.digest == second.digest


def test_actions_and_board_are_permanently_proposal_only():
    with pytest.raises(ValueError, match="proposal_only"):
        ActionSpec(action_id="x", name="x", domain="code", proposal_only=False)
    board = _board()
    with pytest.raises(ValueError, match="proposal_only"):
        PlanningBoard(
            board_id="bad",
            goal=board.goal,
            actions=board.actions,
            initial_state_ref="state",
            proposal_only=False,
        )
    with pytest.raises(ValueError, match="boolean"):
        ActionSpec(action_id="x", name="x", domain="code", proposal_only="true")


def test_resource_measurements_are_finite_and_non_negative():
    for value in (-1, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            ResourceDemand(context_tokens=value)


def test_duplicate_and_unresolved_references_fail_closed():
    with pytest.raises(ValueError, match="duplicates"):
        RetryPolicy(fallback_action_ids=("same", "same"))

    board = _board()
    action = ActionSpec(
        action_id="broken",
        name="broken",
        domain="code",
        retry_policy=RetryPolicy(fallback_action_ids=("missing",)),
    )
    with pytest.raises(ValueError, match="unresolved"):
        PlanningBoard(
            board_id="broken",
            goal=board.goal,
            actions=(action,),
            initial_state_ref="state",
        )


def test_external_policy_classification_required_even_for_none():
    with pytest.raises(ValueError, match="policy_ref"):
        AuthoritySpec(AuthorityRequirement.NONE, policy_ref="")


def test_continuity_is_contiguous_and_requires_exact_refs():
    board = _board()
    result = project_continuity(
        board,
        ContinuityEvidence(
            grounding_refs=("evidence:goal",),
            authority_decision_refs=("decision:none-classified",),
            verifier_receipt_refs=("receipt:pytest",),
        ),
    )
    assert result.highest_level == ContinuityLevel.BC1_TYPED.value
    assert "BC2_CONSTRAINED" in result.blocking_reasons[0]
    assert ContinuityLevel.BC3_GROUNDED.value not in result.passed_levels

    complete = project_continuity(
        board,
        ContinuityEvidence(
            constraint_refs=("constraint:policy",),
            grounding_refs=("evidence:goal",),
            authority_decision_refs=("decision:none-classified",),
            verifier_receipt_refs=("receipt:pytest",),
        ),
    )
    assert complete.complete is True
    assert complete.passed_levels == tuple(level.value for level in ContinuityLevel)


def test_each_declared_verifier_requires_bound_receipt():
    board = _board(with_receipt=False)
    result = project_continuity(
        board,
        ContinuityEvidence(
            constraint_refs=("constraint:policy",),
            grounding_refs=("evidence:goal",),
            authority_decision_refs=("decision:none-classified",),
            verifier_receipt_refs=("some-unbound-receipt",),
        ),
    )
    assert result.highest_level == ContinuityLevel.BC4_AUTHORIZED.value
    assert "lack bound receipts" in result.blocking_reasons[0]


def test_goap_shadow_adapter_invents_neither_authority_nor_reversibility():
    action = SimpleNamespace(
        name="build_patch",
        domain="code",
        preconditions={"grounded": True},
        effects={"patch_proposed": True},
        cost=1.5,
        required_organ="code",
        must_pass_gates=("architect", "shadow", "verifier", "judge"),
    )
    plan = SimpleNamespace(
        plan_id="GOAL-123",
        goal="Build a bounded patch",
        actions=[action],
        final_state={"patch_proposed": True},
    )
    board = board_from_goap_plan(plan, initial_state_ref="state:goap")
    projected = board.actions[0]
    assert projected.authority is None
    assert projected.reversibility == ReversibilityClass.UNSPECIFIED.value
    assert projected.resource_demand.estimated_cost == 1.5
    assert all(item.receipt_ref is None for item in projected.verifier_requirements)
    assert board.proposal_only is True


def test_goap_projection_cannot_claim_bc5_without_runtime_receipts():
    action = SimpleNamespace(
        name="build_patch",
        domain="code",
        preconditions={},
        effects={"patch_proposed": True},
        cost=1.0,
        required_organ="code",
        must_pass_gates=("verifier",),
    )
    plan = SimpleNamespace(
        plan_id="GOAL-456",
        goal="Build patch",
        actions=[action],
        final_state={"patch_proposed": True},
    )
    result = project_continuity(board_from_goap_plan(plan, initial_state_ref="state"))
    assert result.highest_level == ContinuityLevel.BC4_AUTHORIZED.value
    assert "lack bound receipts" in result.blocking_reasons[0]
