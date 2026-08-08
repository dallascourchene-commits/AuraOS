from pathlib import Path

p = Path("aura_project_context_compiler.py")
s = p.read_text()
old = '''def _ids(values: Sequence[str], name: str, *, maximum: int) -> tuple[str, ...]:
    """Normalize, bound, deduplicate, and sort canonical identifiers."""
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"{name} must be a sequence")
    if len(values) > maximum:
        raise ValueError(f"{name} exceeds its item ceiling")
    result = tuple(_id(item, f"{name} item") for item in values)
'''
new = '''def _ids(values: tuple[str, ...], name: str, *, maximum: int) -> tuple[str, ...]:
    """Normalize a bounded immutable tuple of canonical identifiers."""
    if type(values) is not tuple:
        raise TypeError(f"{name} must be an exact immutable tuple")
    if len(values) > maximum:
        raise ValueError(f"{name} exceeds its item ceiling")
    result = tuple(_id(item, f"{name} item") for item in values)
'''
assert s.count(old) == 1, "ids helper anchor"
s = s.replace(old, new, 1)
old = '''def trace_project_context_provenance(
    compilation: ProjectContextCompilation,
    start_ids: Sequence[str],
'''
new = '''def trace_project_context_provenance(
    compilation: ProjectContextCompilation,
    start_ids: tuple[str, ...],
'''
assert s.count(old) == 1, "provenance annotation anchor"
s = s.replace(old, new, 1)
p.write_text(s.rstrip() + "\n")

t = Path("tests/test_aura_project_context_compiler.py")
x = t.read_text().rstrip()
block = '''


def test_dependency_ids_reject_hostile_sequence_before_protocol_calls() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)

    class HostileIds:
        def __len__(self):
            raise AssertionError("dependency id length must not run")
        def __iter__(self):
            raise AssertionError("dependency id iterator must not run")

    with pytest.raises(TypeError, match="dependency_ids must be an exact immutable tuple"):
        replace(source, dependency_ids=HostileIds())


def test_provenance_start_ids_reject_hostile_sequence_before_protocol_calls() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    compilation = _compile((source,))

    class HostileIds:
        def __len__(self):
            raise AssertionError("start id length must not run")
        def __iter__(self):
            raise AssertionError("start id iterator must not run")

    with pytest.raises(TypeError, match="start_ids must be an exact immutable tuple"):
        trace_project_context_provenance(compilation, HostileIds(), max_hops=4, max_nodes=8)
'''
assert "test_dependency_ids_reject_hostile_sequence_before_protocol_calls" not in x
t.write_text((x + block).rstrip() + "\n")

d = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")
y = d.read_text()
needle = '- caller-controlled candidate, selected-candidate, graph-edge, edge-input, or temporal-binding collections must be exact immutable tuples and satisfy declared-length bounds before traversal;\n'
repl = needle + '- bounded identifier vectors such as dependency IDs and provenance start IDs are likewise exact immutable tuples, so `_ids()` never trusts caller-defined sequence length or iteration protocols;\n'
assert y.count(needle) == 1, "doc ids anchor"
d.write_text(y.replace(needle, repl, 1).rstrip() + "\n")
