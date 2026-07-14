from dataclasses import dataclass

import pytest

from aura_planning_board import (
    ActionContinuityEvidence,
    ActionSpec,
    AuthorityRequirement,
    BoardContinuityLevel,
    ConstraintKind,
    ConstraintSpec,
    EffectSpec,
    PlanningBoard,
    PortCardinality,
    PortDirection,
    PortSpec,
    PredicateOperator,
    PredicateSpec,
    ResourceDemand,
    RetryPolicy,
    VerifierReceiptEvidence,
    ReversibilityClass,
    GoalSpec,
    action_spec_from_goal_action,
    planning_board_from_goal_plan,
    verify_board_continuity,
)


def _complete_action(action_id: str = "action-1") -> ActionSpec:
    return ActionSpec(
        action_id=action_id,
        name="bounded patch",
        domain="code",
        preconditions=(PredicateSpec("source_grounded", expected=True),),
        effects=(EffectSpec("patch_proposed", True),),
        input_ports=(PortSpec("source", "ExactSourceRef", PortDirection.INPUT),),
        output_ports=(
            PortSpec(
                "patch",
                "UnifiedDiff",
                PortDirection.OUTPUT,
                PortCardinality.ONE,
            ),
        ),
        required_capabilities=("code.patch.propose",),
        verifier_ids=("pytest",),
        authority_requirement=AuthorityRequirement.HUMAN,
        resource_demand=ResourceDemand(
            context_tokens=512,
            expected_latency_ms=1000,
            measurement_class="HEURISTIC",
        ),
        reversibility=ReversibilityClass.COMPENSATABLE,
        idempotency_key=f"idem:{action_id}",
        evidence_refs=("sidecar:source:abc",),
    )


def _board(action: ActionSpec | None = None) -> PlanningBoard:
    action = action or _complete_action()
    return PlanningBoard(
        board_id="board-1",
        arena_id="arena-code",
        purpose_digest="purpose:abc",
        goal=GoalSpec(
            goal_id="goal-1",
            objective="Produce a verified bounded patch",
            desired_state=(PredicateSpec("patch_verified", expected=True),),
        ),
        actions=(action,),
        current_state_refs=("state:1",),
    )


def test_contracts_are_deterministic_and_proposal_only() -> None:
    board = _board()
    assert board.digest == board.digest
    assert board.to_dict()["actions"][0]["proposal_only"] is True
    with pytest.raises(ValueError, match="proposal_only"):
        ActionSpec(
            action_id="x",
            name="x",
            domain="code",
            preconditions=(),
            effects=(EffectSpec("done", True),),
            verifier_ids=("v",),
            proposal_only=False,
        )
    with pytest.raises(ValueError, match="boolean"):
        ActionSpec(
            action_id="x",
            name="x",
            domain="code",
            preconditions=(),
            effects=(EffectSpec("done", True),),
            verifier_ids=("v",),
            proposal_only="true",  # type: ignore[arg-type]
        )


def test_resource_demand_rejects_invalid_measurements() -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        ResourceDemand(context_tokens=True)
    with pytest.raises(ValueError, match="finite and non-negative"):
        ResourceDemand(estimated_cost=float("nan"))
    with pytest.raises(ValueError, match="finite and non-negative"):
        ResourceDemand(human_attention_minutes=-1)
    with pytest.raises(ValueError, match="supplied together"):
        ResourceDemand(estimated_cost=1.0, measurement_class="HEURISTIC")
    with pytest.raises(ValueError, match="measurement_class"):
        ResourceDemand(context_tokens=1)


def test_port_direction_and_cardinality_are_enforced() -> None:
    with pytest.raises(ValueError, match="optional ports"):
        PortSpec(
            "maybe",
            "Thing",
            PortDirection.INPUT,
            cardinality=PortCardinality.OPTIONAL,
            required=True,
        )
    with pytest.raises(ValueError, match="INPUT direction"):
        ActionSpec(
            action_id="x",
            name="x",
            domain="code",
            preconditions=(),
            effects=(EffectSpec("done", True),),
            input_ports=(PortSpec("wrong", "Thing", PortDirection.OUTPUT),),
            verifier_ids=("v",),
        )


def test_continuity_passes_only_with_exact_external_evidence() -> None:
    board = _board()
    report = verify_board_continuity(
        board,
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("constraint-check:1",),
                grounded_evidence_refs=("sidecar:source:abc", "exact-source:1"),
                authority_decision_ids=("decision:1",),
                verifier_receipts=(VerifierReceiptEvidence("pytest", "receipt:1"),),
            ),
        ),
    )
    assert report.highest_contiguous_level is BoardContinuityLevel.BC5_VERIFIED
    assert report.continuity_complete is True
    assert report.findings == ()


def test_missing_authority_breaks_contiguous_progression() -> None:
    board = _board()
    report = verify_board_continuity(
        board,
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("constraint-check:1",),
                grounded_evidence_refs=("sidecar:source:abc", "exact-source:1"),
                verifier_receipts=(VerifierReceiptEvidence("pytest", "receipt:1"),),
            ),
        ),
    )
    assert BoardContinuityLevel.BC5_VERIFIED in report.passed_levels
    assert report.highest_contiguous_level is BoardContinuityLevel.BC3_GROUNDED
    assert report.continuity_complete is False
    assert {item.code for item in report.findings} == {"MISSING_AUTHORITY_DECISION"}


def test_unknown_fallback_fails_bc0() -> None:
    base = _complete_action()
    action = ActionSpec(
        **{
            **base.__dict__,
            "retry_policy": RetryPolicy(fallback_action_ids=("missing-action",)),
        }
    )
    report = verify_board_continuity(_board(action))
    assert BoardContinuityLevel.BC0_STRUCTURAL not in report.passed_levels
    assert report.highest_contiguous_level is None
    assert "UNKNOWN_FALLBACK_ACTION" in {item.code for item in report.findings}


@dataclass
class LegacyGoalAction:
    name: str = "build_patch"
    domain: str = "code"
    preconditions: dict = None  # type: ignore[assignment]
    effects: dict = None  # type: ignore[assignment]
    required_organ: str = "code"
    must_pass_gates: tuple = ("architect", "shadow", "verifier", "judge")

    def __post_init__(self) -> None:
        self.preconditions = {"source_grounded": True}
        self.effects = {"patch_proposed": True}


@dataclass
class LegacyGoalPlan:
    goal: str
    actions: list
    final_state: dict


def test_goap_adapter_preserves_proposal_semantics_without_inventing_authority() -> None:
    action = action_spec_from_goal_action(LegacyGoalAction())
    assert action.preconditions[0].fact == "source_grounded"
    assert action.effects[0].fact == "patch_proposed"
    assert action.required_capabilities == ("organ:code",)
    assert action.verifier_ids == (
        "gate:architect",
        "gate:shadow",
        "gate:verifier",
        "gate:judge",
    )
    assert action.authority_requirement is AuthorityRequirement.UNSPECIFIED
    assert action.reversibility is ReversibilityClass.UNSPECIFIED
    assert action.proposal_only is True


def test_goap_adapter_preserves_membership_precondition_semantics() -> None:
    legacy = LegacyGoalAction()
    legacy.preconditions = {"mode": ("safe", "dry_run")}
    action = action_spec_from_goal_action(legacy)
    assert action.preconditions[0].fact == "mode"
    assert action.preconditions[0].expected == ("safe", "dry_run")
    assert action.preconditions[0].operator is PredicateOperator.IN


def test_goal_plan_shadow_projection_is_stable_and_non_authoritative() -> None:
    plan = LegacyGoalPlan(
        goal="create verified patch",
        actions=[LegacyGoalAction()],
        final_state={"patch_verified": True},
    )
    first = planning_board_from_goal_plan(
        plan, arena_id="coding-arena", purpose_digest="purpose:123"
    )
    second = planning_board_from_goal_plan(
        plan, arena_id="coding-arena", purpose_digest="purpose:123"
    )
    assert first.board_id == second.board_id
    assert first.digest == second.digest
    assert first.actions[0].proposal_only is True


def test_evidence_rejects_duplicates_unknown_actions_and_string_sequences() -> None:
    board = _board()
    duplicate = ActionContinuityEvidence(action_id="action-1")
    with pytest.raises(ValueError, match="at most one"):
        verify_board_continuity(board, evidence=(duplicate, duplicate))
    with pytest.raises(ValueError, match="unknown action"):
        verify_board_continuity(
            board, evidence=(ActionContinuityEvidence(action_id="other"),)
        )
    with pytest.raises(ValueError, match="sequence"):
        verify_board_continuity(board, evidence="not-a-sequence")  # type: ignore[arg-type]


def test_authority_none_still_requires_external_policy_classification() -> None:
    base = _complete_action()
    action = ActionSpec(
        **{
            **base.__dict__,
            "authority_requirement": AuthorityRequirement.NONE,
        }
    )
    report = verify_board_continuity(
        _board(action),
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("constraint-check:1",),
                grounded_evidence_refs=("sidecar:source:abc",),
                verifier_receipts=(VerifierReceiptEvidence("pytest", "receipt:1"),),
            ),
        ),
    )
    assert BoardContinuityLevel.BC4_AUTHORIZED not in report.passed_levels
    assert "MISSING_AUTHORITY_DECISION" in {item.code for item in report.findings}


def test_each_declared_verifier_requires_its_own_bound_receipt() -> None:
    base = _complete_action()
    action = ActionSpec(
        **{
            **base.__dict__,
            "verifier_ids": ("pytest", "policy-check"),
        }
    )
    report = verify_board_continuity(
        _board(action),
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("constraint-check:1",),
                grounded_evidence_refs=("sidecar:source:abc",),
                authority_decision_ids=("decision:1",),
                verifier_receipts=(VerifierReceiptEvidence("pytest", "receipt:1"),),
            ),
        ),
    )
    assert BoardContinuityLevel.BC5_VERIFIED not in report.passed_levels
    assert "MISSING_VERIFIER_RECEIPT" in {item.code for item in report.findings}


def test_declared_grounding_refs_must_be_resolved_by_evidence_projection() -> None:
    board = _board()
    report = verify_board_continuity(
        board,
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("constraint-check:1",),
                grounded_evidence_refs=("different-sidecar",),
                authority_decision_ids=("decision:1",),
                verifier_receipts=(VerifierReceiptEvidence("pytest", "receipt:1"),),
            ),
        ),
    )
    assert BoardContinuityLevel.BC3_GROUNDED not in report.passed_levels
    assert "UNRESOLVED_GROUNDING_REFERENCE" in {
        item.code for item in report.findings
    }


def test_declared_blocking_constraint_refs_must_be_resolved() -> None:
    base = _complete_action()
    action = ActionSpec(
        **{
            **base.__dict__,
            "constraints": (
                ConstraintSpec(
                    constraint_id="budget-check",
                    kind=ConstraintKind.BUDGET,
                    description="Budget must be available",
                    evidence_refs=("budget:available",),
                ),
            ),
        }
    )
    board = _board(action)
    report = verify_board_continuity(
        board,
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("unrelated-check",),
                grounded_evidence_refs=("sidecar:source:abc",),
                authority_decision_ids=("decision:1",),
                verifier_receipts=(VerifierReceiptEvidence("pytest", "receipt:1"),),
            ),
        ),
    )
    assert BoardContinuityLevel.BC2_CONSTRAINED not in report.passed_levels
    assert "UNRESOLVED_CONSTRAINT_REFERENCE" in {
        finding.code for finding in report.findings
    }


def test_nonblocking_constraint_refs_do_not_block_bc2() -> None:
    base = _complete_action()
    action = ActionSpec(
        **{
            **base.__dict__,
            "constraints": (
                ConstraintSpec(
                    constraint_id="advisory",
                    kind=ConstraintKind.DOMAIN,
                    description="Advisory only",
                    evidence_refs=("advisory:1",),
                    blocking=False,
                ),
            ),
        }
    )
    board = _board(action)
    report = verify_board_continuity(
        board,
        evidence=(
            ActionContinuityEvidence(
                action_id="action-1",
                constrained_evidence_refs=("constraint-check:1",),
            ),
        ),
    )
    assert "UNRESOLVED_CONSTRAINT_REFERENCE" not in {
        finding.code for finding in report.findings
    }

