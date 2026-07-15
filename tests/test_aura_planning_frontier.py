import pytest

from aura_event_contracts import stable_digest
from aura_planning_board import (
    ActionSpec,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PredicateSpec,
)
from aura_planning_frontier import (
    CandidateConvergence,
    ReplayFindingCode,
    replay_regression_frontier,
)
from aura_planning_regression import (
    RegressionCandidate,
    RegressionReport,
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
        domain="frontier-test",
        preconditions=preconditions,
        effects=effects,
        verifier_ids=("verifier",),
    )


def _board(actions: tuple[ActionSpec, ...], goal_fact: str = "finished") -> PlanningBoard:
    return PlanningBoard(
        board_id="board-frontier",
        arena_id="test-arena",
        purpose_digest="purpose:frontier",
        goal=GoalSpec(
            "goal-frontier",
            "Reach the symbolic goal",
            (PredicateSpec(goal_fact, True),),
        ),
        actions=actions,
    )


def _report(
    board: PlanningBoard,
    state: dict,
    candidates: tuple[RegressionCandidate, ...],
    *,
    board_id: str | None = None,
    board_digest: str | None = None,
    state_digest: str | None = None,
) -> RegressionReport:
    return RegressionReport(
        board_id=board_id or board.board_id,
        board_digest=board_digest or board.digest,
        state_digest=state_digest or stable_digest(state),
        candidates=candidates,
        findings=(),
        explored_nodes=1,
    )


def test_backward_chain_converges_under_forward_replay() -> None:
    prepare = _action(
        "prepare",
        effects=(EffectSpec("prepared", True),),
    )
    finish = _action(
        "finish",
        preconditions=(PredicateSpec("prepared", True),),
        effects=(EffectSpec("finished", True),),
    )
    board = _board((prepare, finish))
    regression = regress_board_goal(board, {})

    frontier = replay_regression_frontier(board, {}, regression)

    assert frontier.convergence_complete is True
    assert frontier.converged_candidates[0].action_ids == ("prepare", "finish")
    assert frontier.converged_candidates[0].proposal_only is True
    assert frontier.digest == frontier.digest


def test_binding_mismatches_fail_closed() -> None:
    action = _action("finish", effects=(EffectSpec("finished", True),))
    board = _board((action,))
    candidate = RegressionCandidate(("finish",))

    with pytest.raises(ValueError, match="board_id"):
        replay_regression_frontier(
            board,
            {},
            _report(board, {}, (candidate,), board_id="other-board"),
        )
    with pytest.raises(ValueError, match="board_digest"):
        replay_regression_frontier(
            board,
            {},
            _report(board, {}, (candidate,), board_digest="wrong-digest"),
        )
    with pytest.raises(ValueError, match="state_digest"):
        replay_regression_frontier(
            board,
            {},
            _report(board, {}, (candidate,), state_digest="wrong-state"),
        )


def test_unknown_action_fails_candidate_replay() -> None:
    action = _action("known", effects=(EffectSpec("finished", True),))
    board = _board((action,))
    frontier = replay_regression_frontier(
        board,
        {},
        _report(board, {}, (RegressionCandidate(("unknown",)),)),
    )

    assessment = frontier.assessments[0]
    assert assessment.converged is False
    assert assessment.applied_action_ids == ()
    assert assessment.findings[0].code is ReplayFindingCode.UNKNOWN_ACTION
    assert assessment.findings[0].action_id == "unknown"


def test_precondition_failure_identifies_exact_action_and_predicate() -> None:
    prepare = _action("prepare", effects=(EffectSpec("prepared", True),))
    finish = _action(
        "finish",
        preconditions=(PredicateSpec("prepared", True),),
        effects=(EffectSpec("finished", True),),
    )
    board = _board((prepare, finish))
    frontier = replay_regression_frontier(
        board,
        {},
        _report(board, {}, (RegressionCandidate(("finish", "prepare")),)),
    )

    assessment = frontier.assessments[0]
    assert assessment.converged is False
    assert assessment.applied_action_ids == ()
    finding = assessment.findings[0]
    assert finding.code is ReplayFindingCode.PRECONDITION_UNSATISFIED
    assert finding.action_id == "finish"
    assert finding.predicates == (PredicateSpec("prepared", True),)


def test_conflicting_duplicate_effects_fail_closed() -> None:
    ambiguous = _action(
        "ambiguous",
        effects=(EffectSpec("finished", True), EffectSpec("finished", False)),
    )
    board = _board((ambiguous,))
    frontier = replay_regression_frontier(
        board,
        {},
        _report(board, {}, (RegressionCandidate(("ambiguous",)),)),
    )

    assessment = frontier.assessments[0]
    assert assessment.converged is False
    assert assessment.applied_action_ids == ()
    assert assessment.findings[0].code is ReplayFindingCode.AMBIGUOUS_EFFECT


def test_identical_duplicate_effects_remain_deterministic() -> None:
    duplicate = _action(
        "duplicate",
        effects=(EffectSpec("finished", True), EffectSpec("finished", True)),
    )
    board = _board((duplicate,))
    frontier = replay_regression_frontier(
        board,
        {},
        _report(board, {}, (RegressionCandidate(("duplicate",)),)),
    )

    assert frontier.convergence_complete is True
    assert frontier.assessments[0].applied_action_ids == ("duplicate",)


def test_completed_path_must_still_satisfy_final_goal() -> None:
    unrelated = _action("unrelated", effects=(EffectSpec("other", True),))
    board = _board((unrelated,))
    frontier = replay_regression_frontier(
        board,
        {},
        _report(board, {}, (RegressionCandidate(("unrelated",)),)),
    )

    assessment = frontier.assessments[0]
    assert assessment.converged is False
    assert assessment.applied_action_ids == ("unrelated",)
    assert assessment.findings[0].code is ReplayFindingCode.GOAL_UNSATISFIED
    assert assessment.findings[0].predicates == (PredicateSpec("finished", True),)


def test_incomplete_backward_candidates_are_counted_but_not_replayed() -> None:
    finish = _action("finish", effects=(EffectSpec("finished", True),))
    board = _board((finish,))
    complete = RegressionCandidate(("finish",))
    incomplete = RegressionCandidate(
        (),
        unresolved_predicates=(PredicateSpec("missing", True),),
    )

    frontier = replay_regression_frontier(
        board,
        {},
        _report(board, {}, (incomplete, complete)),
    )

    assert frontier.ignored_incomplete_candidates == 1
    assert [item.action_ids for item in frontier.assessments] == [("finish",)]
    assert frontier.convergence_complete is True


def test_initially_satisfied_goal_converges_with_empty_path() -> None:
    noop = _action("noop", effects=(EffectSpec("other", True),))
    board = _board((noop,))
    state = {"finished": True}
    regression = regress_board_goal(board, state)

    frontier = replay_regression_frontier(board, state, regression)

    assert frontier.convergence_complete is True
    assert frontier.assessments[0].action_ids == ()
    assert frontier.assessments[0].applied_action_ids == ()


def test_duplicate_complete_paths_and_invalid_convergence_records_fail_closed() -> None:
    finish = _action("finish", effects=(EffectSpec("finished", True),))
    board = _board((finish,))
    duplicate = RegressionCandidate(("finish",))
    report = _report(board, {}, (duplicate, duplicate))

    with pytest.raises(ValueError, match="duplicate complete"):
        replay_regression_frontier(board, {}, report)
    with pytest.raises(ValueError, match="duplicates"):
        CandidateConvergence(
            ("finish", "finish"),
            (),
            False,
            "state-digest",
            findings=(),
        )
    with pytest.raises(ValueError, match="proposal_only"):
        CandidateConvergence(
            ("finish",),
            ("finish",),
            True,
            "state-digest",
            proposal_only=False,
        )
