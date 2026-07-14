"""One-shot updater for the reviewed P2.2 open-predicate branching fix."""
from pathlib import Path

MODULE = Path("aura_planning_regression.py")
TESTS = Path("tests/test_aura_planning_regression_adversarial.py")

old_selection = '''        target = open_predicates[0]
        protected_requirements = _dedupe_predicates(
            (*open_predicates, *protected_predicates)
        )
        producers = tuple(
            action
            for action in actions
            if _effect_satisfies(action, target)
            and not _action_conflicts(action, protected_requirements)
        )
        if not producers:
'''
new_selection = '''        protected_requirements = _dedupe_predicates(
            (*open_predicates, *protected_predicates)
        )
        producer_options = tuple(
            (target, action)
            for target in open_predicates
            for action in actions
            if _effect_satisfies(action, target)
            and not _action_conflicts(action, protected_requirements)
        )
        producible_keys = {
            _predicate_key(target) for target, _action in producer_options
        }
        missing_targets = tuple(
            target
            for target in open_predicates
            if _predicate_key(target) not in producible_keys
        )
        if missing_targets:
            target = missing_targets[0]
'''

old_depth = '''        if len(selected_reversed) >= max_depth:
            candidates.append(
'''
new_depth = '''        if len(selected_reversed) >= max_depth:
            target = open_predicates[0]
            candidates.append(
'''

old_loop = '''        expanded = False
        for action in producers:
'''
new_loop = '''        expanded = False
        for target, action in producer_options:
'''

module_text = MODULE.read_text(encoding="utf-8")
for old, new, label in (
    (old_selection, new_selection, "target selection"),
    (old_depth, new_depth, "depth target"),
    (old_loop, new_loop, "producer loop"),
):
    count = module_text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one {label} block, found {count}")
    module_text = module_text.replace(old, new, 1)
MODULE.write_text(module_text, encoding="utf-8")

marker = "def test_target_selection_branches_across_all_open_predicates()"
test_text = TESTS.read_text(encoding="utf-8")
if marker in test_text:
    raise SystemExit("review regression test already exists")

test_text += '''


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
'''
TESTS.write_text(test_text, encoding="utf-8")
