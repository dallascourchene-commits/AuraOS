import pytest

from aura_planning_board import (
    ActionSpec,
    AuthorityRequirement,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PredicateOperator,
    PredicateSpec,
    ReversibilityClass,
)
from aura_planning_regression import (
    RegressionFindingCode,
    predicate_satisfied,
    regress_board_goal,
)


def _action(
    action_id: str,
    *,
    preconditions: tuple[PredicateSpec, ...] = (),
    effects: tuple[EffectSpec, ...],
) -> ActionSpec:
    return ActionSpec(
        action_id=action_id,
        name=action_id,
        domain="test",
        preconditions=preconditions,
        effects=effects,
        verifier_ids=("verifier",),
        authority_requirement=AuthorityRequirement.HUMAN,
        reversibility=ReversibilityClass.REVERSIBLE,
    )


def _board(actions: tuple[ActionSpec, ...], desired: tuple[PredicateSpec, ...]) -> PlanningBoard:
    return PlanningBoard(
        board_id="board-regression",
        arena_id="test-arena",
        purpose_digest="purpose:regression",
        goal=GoalSpec("goal-regression", "Reach desired symbolic state", desired),
        actions=actions,
    )


def test_predicate_evaluation_preserves_eq_in_and_exists() -> None:
    state = {"mode": "safe", "ready": True}
    assert predicate_satisfied(PredicateSpec("mode", "safe"), state)
    assert predicate_satisfied(
        PredicateSpec("mode", ("safe", "dry_run"), PredicateOperator.IN), state
    )
    assert predicate_satisfied(
        PredicateSpec("ready", True, PredicateOperator.EXISTS), state
    )
    assert predicate_satisfied(
        PredicateSpec("missing", False, PredicateOperator.EXISTS), state
    )
    assert not predicate_satisfied(PredicateSpec("missing", True, PredicateOperator.EXISTS), state)


def test_backward_regression_returns_dependency_order_not_execution() -> None:
    prepare = _action(
        "prepare",
        effects=(EffectSpec("prepared", True),),
    )
    finish = _action(
        "finish",
        preconditions=(PredicateSpec("prepared", True),),
        effects=(EffectSpec("finished", True),),
    )
    report = regress_board_goal(
        _board((finish, prepare), (PredicateSpec("finished", True),)),
        initial_state={},
    )
    assert [candidate.action_ids for candidate in report.complete_candidates] == [
        ("prepare", "finish")
    ]
    assert report.complete_candidates[0].proposal_only is True


def test_already_satisfied_goal_returns_empty_candidate() -> None:
    action = _action("unused", effects=(EffectSpec("finished", True),))
    report = regress_board_goal(
        _board((action,), (PredicateSpec("finished", True),)),
        initial_state={"finished": True},
    )
    assert report.complete_candidates[0].action_ids == ()
    assert report.explored_nodes == 1


def test_regression_branches_deterministically_for_alternative_producers() -> None:
    first = _action("a-first", effects=(EffectSpec("finished", True),))
    second = _action("b-second", effects=(EffectSpec("finished", True),))
    report = regress_board_goal(
        _board((second, first), (PredicateSpec("finished", True),)),
        initial_state={},
    )
    assert [candidate.action_ids for candidate in report.complete_candidates] == [
        ("a-first",),
        ("b-second",),
    ]


def test_one_action_can_discharge_multiple_open_goal_predicates() -> None:
    action = _action(
        "compound",
        effects=(EffectSpec("left", True), EffectSpec("right", True)),
    )
    report = regress_board_goal(
        _board(
            (action,),
            (PredicateSpec("left", True), PredicateSpec("right", True)),
        ),
        initial_state={},
    )
    assert [candidate.action_ids for candidate in report.complete_candidates] == [
        ("compound",)
    ]


def test_missing_producer_is_reported_as_incomplete_candidate() -> None:
    report = regress_board_goal(
        _board(
            (_action("unrelated", effects=(EffectSpec("other", True),)),),
            (PredicateSpec("finished", True),),
        ),
        initial_state={},
    )
    assert report.complete_candidates == ()
    assert report.candidates[0].unresolved_predicates[0].fact == "finished"
    assert RegressionFindingCode.NO_PRODUCER in {finding.code for finding in report.findings}


def test_cycle_is_blocked_without_repeating_actions() -> None:
    action_a = _action(
        "a",
        preconditions=(PredicateSpec("b-ready", True),),
        effects=(EffectSpec("a-ready", True),),
    )
    action_b = _action(
        "b",
        preconditions=(PredicateSpec("a-ready", True),),
        effects=(EffectSpec("b-ready", True),),
    )
    report = regress_board_goal(
        _board((action_a, action_b), (PredicateSpec("a-ready", True),)),
        initial_state={},
    )
    assert report.complete_candidates == ()
    assert RegressionFindingCode.CYCLE_BLOCKED in {
        finding.code for finding in report.findings
    }
    assert all(len(candidate.action_ids) == len(set(candidate.action_ids)) for candidate in report.candidates)


def test_depth_and_node_budgets_are_strict_positive_integers() -> None:
    board = _board(
        (_action("a", effects=(EffectSpec("done", True),)),),
        (PredicateSpec("done", True),),
    )
    for field_name in ("max_depth", "max_candidates", "max_explored_nodes"):
        with pytest.raises(ValueError, match=field_name):
            regress_board_goal(board, {}, **{field_name: True})
        with pytest.raises(ValueError, match=field_name):
            regress_board_goal(board, {}, **{field_name: 0})


def test_report_is_deterministic_and_bound_to_board_and_state() -> None:
    board = _board(
        (_action("a", effects=(EffectSpec("done", True),)),),
        (PredicateSpec("done", True),),
    )
    first = regress_board_goal(board, {"seed": 1})
    second = regress_board_goal(board, {"seed": 1})
    changed_state = regress_board_goal(board, {"seed": 2})
    assert first.to_dict() == second.to_dict()
    assert first.board_digest == board.digest
    assert first.state_digest != changed_state.state_digest


def test_collection_goal_can_be_established_by_member_effect() -> None:
    action = _action("safe-mode", effects=(EffectSpec("mode", "safe"),))
    report = regress_board_goal(
        _board(
            (action,),
            (PredicateSpec("mode", ("safe", "dry_run"), PredicateOperator.IN),),
        ),
        initial_state={},
    )
    assert report.complete_candidates[0].action_ids == ("safe-mode",)


def test_regression_candidates_cannot_claim_execution_authority() -> None:
    from aura_planning_regression import RegressionCandidate

    with pytest.raises(ValueError, match="proposal_only"):
        RegressionCandidate(("a",), proposal_only=False)
    with pytest.raises(ValueError, match="boolean"):
        RegressionCandidate(("a",), proposal_only="true")  # type: ignore[arg-type]
