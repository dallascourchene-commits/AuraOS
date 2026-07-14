from pathlib import Path

path = Path("aura_planning_regression.py")
source = path.read_text(encoding="utf-8")

if "def _effect_value_satisfies" in source:
    raise SystemExit(0)

old = '''def _effect_satisfies(action: ActionSpec, predicate: PredicateSpec) -> bool:
    for effect in action.effects:
        if effect.fact != predicate.fact:
            continue
        if predicate.operator is PredicateOperator.EXISTS:
            if predicate.expected is True:
                return True
            continue
        if predicate.operator is PredicateOperator.EQ and effect.value == predicate.expected:
            return True
        if predicate.operator is PredicateOperator.IN:
            try:
                if effect.value in predicate.expected:
                    return True
            except TypeError:
                continue
    return False


def _action_conflicts(
    action: ActionSpec,
    predicates: Sequence[PredicateSpec],
) -> bool:
    """Return True when an action overwrites a still-protected requirement."""

    for effect in action.effects:
        for predicate in predicates:
            if effect.fact == predicate.fact and not _effect_satisfies(action, predicate):
                return True
    return False
'''
new = '''def _effect_value_satisfies(value: Any, predicate: PredicateSpec) -> bool:
    if predicate.operator is PredicateOperator.EXISTS:
        return predicate.expected is True
    if predicate.operator is PredicateOperator.EQ:
        return value == predicate.expected
    if predicate.operator is PredicateOperator.IN:
        try:
            return value in predicate.expected
        except TypeError:
            return False
    raise ValueError(f"unsupported predicate operator: {predicate.operator}")


def _effect_satisfies(action: ActionSpec, predicate: PredicateSpec) -> bool:
    matching = tuple(effect for effect in action.effects if effect.fact == predicate.fact)
    if not matching:
        return False
    values = {canonical_json(effect.value) for effect in matching}
    if len(values) != 1:
        return False
    return _effect_value_satisfies(matching[0].value, predicate)


def _action_conflicts(
    action: ActionSpec,
    predicates: Sequence[PredicateSpec],
) -> bool:
    """Return True when an action ambiguously overwrites a protected requirement."""

    by_fact: dict[str, list[Any]] = {}
    for effect in action.effects:
        by_fact.setdefault(effect.fact, []).append(effect.value)
    for predicate in predicates:
        values = by_fact.get(predicate.fact)
        if values is None:
            continue
        canonical_values = {canonical_json(value) for value in values}
        if len(canonical_values) != 1:
            return True
        if not _effect_value_satisfies(values[0], predicate):
            return True
    return False
'''
if source.count(old) != 1:
    raise SystemExit("weak effect semantics block not found")
source = source.replace(old, new, 1)
path.write_text(source, encoding="utf-8")
