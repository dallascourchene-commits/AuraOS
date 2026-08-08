from pathlib import Path

p = Path("aura_project_context_compiler.py")
s = p.read_text()

old = '''    if type(raw_bindings) not in (tuple, list):
        raise TypeError("temporal_bindings must be a bounded built-in tuple or list")
'''
new = '''    if type(raw_bindings) is not tuple:
        raise TypeError("temporal_bindings must be an exact immutable tuple")
'''
assert s.count(old) == 1, "temporal tuple anchor"
s = s.replace(old, new, 1)

old = '''    if existing is None:
        object.__setattr__(
            candidate,
            "temporal_bindings",
            tuple(
                sorted(
                    (*candidate.temporal_bindings, reference_binding),
                    key=lambda item: item.key,
                )
            ),
        )
'''
new = '''    if existing is None:
        if len(candidate.temporal_bindings) >= MAX_TEMPORAL_BINDINGS:
            raise ValueError(
                "temporal_bindings leaves no room for canonical-reference identity binding"
            )
        object.__setattr__(
            candidate,
            "temporal_bindings",
            tuple(
                sorted(
                    (*candidate.temporal_bindings, reference_binding),
                    key=lambda item: item.key,
                )
            ),
        )
        if len(candidate.temporal_bindings) > MAX_TEMPORAL_BINDINGS:
            raise ValueError("temporal_bindings exceeds the bounded record ceiling")
'''
assert s.count(old) == 1, "reference binding anchor"
s = s.replace(old, new, 1)

for old, new, label in (
    (
        '''    if type(raw_selected) not in (tuple, list):
        raise TypeError("selected_candidates must be a bounded built-in tuple or list")
''',
        '''    if type(raw_selected) is not tuple:
        raise TypeError("selected_candidates must be an exact immutable tuple")
''',
        "selected",
    ),
    (
        '''    if type(raw_edges) not in (tuple, list):
        raise TypeError("graph_edges must be a bounded built-in tuple or list")
''',
        '''    if type(raw_edges) is not tuple:
        raise TypeError("graph_edges must be an exact immutable tuple")
''',
        "graph",
    ),
    (
        '''    if type(edges) not in (tuple, list):
        raise TypeError("edges must be a sequence backed by an exact built-in tuple or list")
''',
        '''    if type(edges) is not tuple:
        raise TypeError("edges must be an exact immutable tuple")
''',
        "edges",
    ),
):
    assert s.count(old) == 1, label
    s = s.replace(old, new, 1)

old = '''    if isinstance(candidates, (str, bytes, bytearray)) or not isinstance(
        candidates, Sequence
    ):
        raise TypeError("candidates must be a sequence")
    if len(candidates) > MAX_CANDIDATES or any(
        type(item) is not ProjectContextCandidate for item in candidates
    ):
        raise ValueError(
            "candidates must be a bounded sequence of exact ProjectContextCandidate records"
        )
'''
new = '''    if type(candidates) is not tuple:
        raise TypeError("candidates must be an exact immutable tuple")
    if len(candidates) > MAX_CANDIDATES:
        raise ValueError("candidates exceed the bounded candidate ceiling")
    if any(type(item) is not ProjectContextCandidate for item in candidates):
        raise ValueError(
            "candidates must contain exact ProjectContextCandidate records"
        )
'''
assert s.count(old) == 1, "candidate input"
s = s.replace(old, new, 1)

old = '''    eligible = mandatory - invalid
    if len(eligible) > budget.max_nodes:
'''
new = '''    eligible = mandatory - invalid
    while True:
        orphaned = {
            candidate_id
            for candidate_id in eligible
            if any(
                dependency_id not in eligible
                for dependency_id in candidate_map[candidate_id].dependency_ids
            )
        }
        if not orphaned:
            break
        buckets["mandatory_evidence_missing"].update(orphaned)
        eligible.difference_update(orphaned)
    if len(eligible) > budget.max_nodes:
'''
assert s.count(old) == 1, "mandatory closure"
s = s.replace(old, new, 1)
p.write_text(s.rstrip() + "\n")

t = Path("tests/test_aura_project_context_compiler.py")
x = t.read_text().rstrip()
block = '''


def test_compile_rejects_mutable_candidate_list_before_traversal() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    with pytest.raises(TypeError, match="candidates must be an exact immutable tuple"):
        compile_project_context_projection(
            "Fix the exact behavior without losing proof context.",
            project_ref="project:auraos-pr3",
            repository_identity=_repo(), candidates=[source], edges=(),
            budget=ProjectionBudget(max_nodes=64, max_edges=256),
            freshness_timestamp_ms=1_786_180_000_000,
        )


def test_compile_rejects_mutable_edge_list_before_traversal() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    with pytest.raises(TypeError, match="edges must be an exact immutable tuple"):
        compile_project_context_projection(
            "Fix the exact behavior without losing proof context.",
            project_ref="project:auraos-pr3",
            repository_identity=_repo(), candidates=(source,), edges=[],
            budget=ProjectionBudget(max_nodes=64, max_edges=256),
            freshness_timestamp_ms=1_786_180_000_000,
        )


def test_compile_rejects_hostile_candidate_sequence_without_protocol_calls() -> None:
    class HostileCandidates:
        def __len__(self):
            raise AssertionError("hostile candidate length must not run")
        def __iter__(self):
            raise AssertionError("hostile candidate iterator must not run")
    with pytest.raises(TypeError, match="candidates must be an exact immutable tuple"):
        compile_project_context_projection(
            "Fix the exact behavior without losing proof context.",
            project_ref="project:auraos-pr3", repository_identity=_repo(),
            candidates=HostileCandidates(), edges=(),
            budget=ProjectionBudget(max_nodes=64, max_edges=256),
            freshness_timestamp_ms=1_786_180_000_000,
        )


def test_incomplete_mandatory_selection_remains_dependency_closed() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"],
        answer_determining=True, deps=("test:missing",),
    )
    result = _compile((source,))
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert result.projection is None
    assert result.selected_candidates == ()
    assert "test:missing" in result.selection_receipt.mandatory_evidence_missing
    assert "source:target" in result.selection_receipt.mandatory_evidence_missing


def test_authoritative_candidate_reserves_slot_for_reference_binding() -> None:
    bindings = tuple(
        TemporalBinding(TemporalBindingKind.LEASE, f"lease:{index}", f"{index + 1:064x}")
        for index in range(64)
    )
    with pytest.raises(ValueError, match="no room for canonical-reference identity binding"):
        _candidate(
            "source:target", CandidateCategory.SOURCE, D["2"],
            answer_determining=True, bindings=bindings,
        )
'''
assert "test_compile_rejects_mutable_candidate_list_before_traversal" not in x
t.write_text((x + block).rstrip() + "\n")

a = Path("tests/test_aura_project_context_acceptance.py")
y = a.read_text()
y = y.replace('match="selected_candidates must be a bounded built-in"', 'match="selected_candidates must be an exact immutable tuple"')
y = y.replace('match="graph_edges must be a bounded built-in"', 'match="graph_edges must be an exact immutable tuple"')
y = y.replace('match="temporal_bindings must be a bounded built-in"', 'match="temporal_bindings must be an exact immutable tuple"')
a.write_text(y.rstrip() + "\n")

d = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")
z = d.read_text()
z = z.replace(
    'Candidate input edges must be an exact built-in `tuple` or `list`; arbitrary custom `Sequence` implementations are rejected before calling their length, indexing, or iteration protocols.',
    'Candidate and edge inputs must be exact immutable built-in `tuple` values; mutable lists and arbitrary custom `Sequence` implementations are rejected before calling caller-controlled length, indexing, or iteration protocols.',
)
z = z.replace(
    'caller-controlled selected-candidate, graph-edge, or temporal-binding iterables are not materialized before exact finite-container and declared-length bounds are proven;',
    'caller-controlled candidate, selected-candidate, graph-edge, edge-input, or temporal-binding collections must be exact immutable tuples and satisfy declared-length bounds before traversal;',
)
d.write_text(z.rstrip() + "\n")
