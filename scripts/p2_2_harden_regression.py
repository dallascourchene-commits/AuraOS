from pathlib import Path

path = Path("aura_planning_regression.py")
source = path.read_text(encoding="utf-8")

old = '''def _predicate_key(predicate: PredicateSpec) -> str:
    return canonical_json(predicate)
'''
new = '''def _action_conflicts(
    action: ActionSpec,
    predicates: Sequence[PredicateSpec],
) -> bool:
    """Return True when an action overwrites a still-protected requirement."""

    for effect in action.effects:
        for predicate in predicates:
            if effect.fact == predicate.fact and not _effect_satisfies(action, predicate):
                return True
    return False


def _predicate_key(predicate: PredicateSpec) -> str:
    return canonical_json(predicate)
'''
if source.count(old) != 1:
    raise SystemExit("action conflict insertion point not found")
source = source.replace(old, new, 1)

old = '''    queue: list[tuple[tuple[PredicateSpec, ...], tuple[str, ...]]] = [(initial_open, ())]
    visited: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
'''
new = '''    initial_protected = _dedupe_predicates(board.goal.desired_state)
    queue: list[
        tuple[tuple[PredicateSpec, ...], tuple[PredicateSpec, ...], tuple[str, ...]]
    ] = [(initial_open, initial_protected, ())]
    visited: set[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = set()
'''
if source.count(old) != 1:
    raise SystemExit("queue declaration not found")
source = source.replace(old, new, 1)

old = '''        open_predicates, selected_reversed = queue.pop(0)
        state_key = (
            tuple(_predicate_key(item) for item in open_predicates),
            selected_reversed,
        )
'''
new = '''        open_predicates, protected_predicates, selected_reversed = queue.pop(0)
        state_key = (
            tuple(_predicate_key(item) for item in open_predicates),
            tuple(_predicate_key(item) for item in protected_predicates),
            selected_reversed,
        )
'''
if source.count(old) != 1:
    raise SystemExit("queue unpack not found")
source = source.replace(old, new, 1)

old = '''        producers = tuple(action for action in actions if _effect_satisfies(action, target))
'''
new = '''        protected_requirements = _dedupe_predicates(
            (*open_predicates, *protected_predicates)
        )
        producers = tuple(
            action
            for action in actions
            if _effect_satisfies(action, target)
            and not _action_conflicts(action, protected_requirements)
        )
'''
if source.count(old) != 1:
    raise SystemExit("producer selection not found")
source = source.replace(old, new, 1)

old = '''            remaining = open_predicates[1:]
            regressed = _open_predicates((*remaining, *action.preconditions), initial_state)
            queue.append((regressed, (*selected_reversed, action.action_id)))
'''
new = '''            remaining = tuple(
                predicate
                for predicate in open_predicates
                if not _effect_satisfies(action, predicate)
            )
            protected_after = _dedupe_predicates(
                tuple(
                    predicate
                    for predicate in protected_predicates
                    if not _effect_satisfies(action, predicate)
                )
            )
            regressed = _open_predicates((*remaining, *action.preconditions), initial_state)
            queue.append(
                (regressed, protected_after, (*selected_reversed, action.action_id))
            )
'''
if source.count(old) != 1:
    raise SystemExit("regression expansion not found")
source = source.replace(old, new, 1)

old = '''        target = queue[0][0][0] if queue[0][0] else board.goal.desired_state[0]
        findings.append(
            RegressionFinding(
                RegressionFindingCode.DEPTH_LIMIT,
                target.fact,
                "maximum explored-node budget reached",
                tuple(reversed(queue[0][1])),
            )
        )
'''
new = '''        target = queue[0][0][0] if queue[0][0] else board.goal.desired_state[0]
        findings.append(
            RegressionFinding(
                RegressionFindingCode.DEPTH_LIMIT,
                target.fact,
                "maximum explored-node budget reached",
                tuple(reversed(queue[0][2])),
            )
        )
'''
if source.count(old) != 1:
    raise SystemExit("node budget queue access not found")
source = source.replace(old, new, 1)

path.write_text(source, encoding="utf-8")
