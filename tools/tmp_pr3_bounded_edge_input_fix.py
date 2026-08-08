from pathlib import Path

SOURCE = Path("aura_project_context_compiler.py")
TESTS = Path("tests/test_aura_project_context_compiler.py")
DOC = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
tests = TESTS.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")

source = once(
    source,
    '''    """Compile the corresponding bounded PR3 structure from validated inputs."""\n    edge_items = tuple(edges)\n    if len(edge_items) > min(\n        MAX_EDGES, budget.max_edges * _EDGE_INPUT_EXPANSION_FACTOR\n    ) or any(\n        type(item) is not ProjectContextEdge for item in edge_items\n    ):\n        raise ValueError(\n            "edges must be a bounded sequence of exact ProjectContextEdge records"\n        )\n''',
    '''    """Compile the corresponding bounded PR3 structure from validated inputs."""\n    if isinstance(edges, (str, bytes, bytearray)) or not isinstance(edges, Sequence):\n        raise TypeError("edges must be a sequence")\n    edge_limit = min(MAX_EDGES, budget.max_edges * _EDGE_INPUT_EXPANSION_FACTOR)\n    if len(edges) > edge_limit:\n        raise ValueError("edges exceed the bounded edge-input ceiling")\n    if any(type(item) is not ProjectContextEdge for item in edges):\n        raise ValueError("edges must contain exact ProjectContextEdge records")\n    edge_items = tuple(edges)\n''',
    "bounded edge input validation",
)

regression = r'''


def test_edge_input_rejects_non_sequence_without_consuming_iterable() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )

    class ExplodingEdges:
        def __iter__(self):
            raise AssertionError("edge iterable must not be consumed before sequence validation")

    with pytest.raises(TypeError, match="edges must be a sequence"):
        compile_project_context_projection(
            "Fix the exact behavior without losing proof context.",
            project_ref="project:auraos-pr3",
            repository_identity=_repo(),
            candidates=(source,),
            edges=ExplodingEdges(),
            budget=ProjectionBudget(max_nodes=64, max_edges=256),
            freshness_timestamp_ms=1_786_180_000_000,
        )
'''
if "test_edge_input_rejects_non_sequence_without_consuming_iterable" in tests:
    raise SystemExit("bounded edge-input regression already present")
tests = tests.rstrip() + regression + "\n"

doc = once(
    doc,
    '''Candidate input edges may be accepted up to a bounded four-times selected-edge budget (never above the module-wide edge ceiling) so task-conditioned endpoint reduction can occur before the final selected graph is checked strictly against `max_edges`. ''',
    '''Candidate input edges must be a runtime `Sequence`; the compiler validates the sequence type and declared length before materialization or item traversal. They may be accepted up to a bounded four-times selected-edge budget (never above the module-wide edge ceiling) so task-conditioned endpoint reduction can occur before the final selected graph is checked strictly against `max_edges`. ''',
    "bounded edge documentation",
)

SOURCE.write_text(source.rstrip() + "\n", encoding="utf-8")
TESTS.write_text(tests.rstrip() + "\n", encoding="utf-8")
DOC.write_text(doc.rstrip() + "\n", encoding="utf-8")
