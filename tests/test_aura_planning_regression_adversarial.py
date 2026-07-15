from aura_planning_board import (
    ActionSpec,
    AuthorityRequirement,
    EffectSpec,
    GoalSpec,
    PlanningBoard,
    PredicateSpec,
    ReversibilityClass,
)
from aura_planning_regression import regress_board_goal


def _action(
    action_id: str,
    *,
    preconditions: tuple[PredicateSpec, ...] = (),
    effects: tuple[EffectSpec, ...],
) -> ActionSpec:
    return ActionSpec(
        action_id=action_id,
        name=action_id,
        domain="adversarial-test",
        preconditions=preconditions,
        effects=effects,
        verifier_ids=("verifier",),
        authority_requirement=AuthorityRequirement.HUMAN,
        reversibility=ReversibilityClass.REVERSIBLE,
    )


def _board(actions: tuple[ActionSpec, ...], desired: tuple[PredicateSpec, ...]) -> PlanningBoard:
    return PlanningBoard(
        board_id="board-regression-adversarial",
        arena_id="test-arena",
        purpose_digest="purpose:regression-adversarial",
        goal=GoalSpec("goal-regression-adversarial", "Protect all desired facts", desired),
        actions=actions,
    )


def test_action_cannot_overwrite_another_open_goal() -> None:
    unsafe = _action(
        "unsafe",
        effects=(EffectSpec("left", True), EffectSpec("right", False)),
    )
    safe_right = _action("safe-right", effects=(EffectSpec("right", True),))
    report = regress_board_goal(
        _board(
            (unsafe, safe_right),
            (PredicateSpec("left", True), PredicateSpec("right", True)),
        ),
        {},
    )
    assert report.complete_candidates == ()


def test_action_cannot_overwrite_an_initially_satisfied_goal() -> None:
    unsafe = _action(
        "unsafe",
        effects=(EffectSpec("finished", True), EffectSpec("protected", False)),
    )
    report = regress_board_goal(
        _board(
            (unsafe,),
            (PredicateSpec("finished", True), PredicateSpec("protected", True)),
        ),
        {"protected": True},
    )
    assert report.complete_candidates == ()


def test_earlier_action_may_change_fact_restored_by_later_action() -> None:
    prepare = _action(
        "prepare",
        effects=(EffectSpec("prepared", True), EffectSpec("finished", False)),
    )
    finish = _action(
        "finish",
        preconditions=(PredicateSpec("prepared", True),),
        effects=(EffectSpec("finished", True),),
    )
    report = regress_board_goal(
        _board((prepare, finish), (PredicateSpec("finished", True),)),
        {},
    )
    assert [candidate.action_ids for candidate in report.complete_candidates] == [
        ("prepare", "finish")
    ]


def test_ambiguous_duplicate_effect_fact_fails_closed() -> None:
    ambiguous = _action(
        "ambiguous",
        effects=(EffectSpec("finished", True), EffectSpec("finished", False)),
    )
    report = regress_board_goal(
        _board((ambiguous,), (PredicateSpec("finished", True),)),
        {},
    )
    assert report.complete_candidates == ()


def test_duplicate_identical_effect_values_are_not_ambiguous() -> None:
    duplicate = _action(
        "duplicate",
        effects=(EffectSpec("finished", True), EffectSpec("finished", True)),
    )
    report = regress_board_goal(
        _board((duplicate,), (PredicateSpec("finished", True),)),
        {},
    )
    assert report.complete_candidates[0].action_ids == ("duplicate",)


def test_target_selection_branches_across_all_open_predicates() -> None:
    establish_x = _action(
        "a0-establish-x",
        effects=(EffectSpec("x", False),),
    )
    establish_z = _action(
        "a2-establish-z",
        preconditions=(PredicateSpec("x", False),),
        effects=(EffectSpec("z", True),),
    )
    report = regress_board_goal(
        _board(
            (establish_x, establish_z),
            (PredicateSpec("x", False), PredicateSpec("z", True)),
        ),
        {},
    )
    assert ("a0-establish-x", "a2-establish-z") in {
        candidate.action_ids for candidate in report.complete_candidates
    }
