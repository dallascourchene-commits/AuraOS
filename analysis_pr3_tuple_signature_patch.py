from pathlib import Path

p = Path("aura_project_context_compiler.py")
s = p.read_text()
replacements = {
    "def _compile_candidate_map(\n    candidates: Sequence[ProjectContextCandidate],\n": "def _compile_candidate_map(\n    candidates: tuple[ProjectContextCandidate, ...],\n",
    "def _compile_edge_items(\n    edges: Sequence[ProjectContextEdge],\n": "def _compile_edge_items(\n    edges: tuple[ProjectContextEdge, ...],\n",
    "def _validate_compile_context(\n    repository_identity: RepositoryIdentity,\n    candidates: Sequence[ProjectContextCandidate],\n    edges: Sequence[ProjectContextEdge],\n": "def _validate_compile_context(\n    repository_identity: RepositoryIdentity,\n    candidates: tuple[ProjectContextCandidate, ...],\n    edges: tuple[ProjectContextEdge, ...],\n",
    "    candidates: Sequence[ProjectContextCandidate],\n    edges: Sequence[ProjectContextEdge] = (),\n": "    candidates: tuple[ProjectContextCandidate, ...],\n    edges: tuple[ProjectContextEdge, ...] = (),\n",
}
for old, new in replacements.items():
    assert s.count(old) == 1, old
    s = s.replace(old, new, 1)
p.write_text(s.rstrip() + "\n")

d = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")
y = d.read_text()
needle = '- bounded identifier vectors such as dependency IDs and provenance start IDs are likewise exact immutable tuples, so `_ids()` never trusts caller-defined sequence length or iteration protocols;\n'
repl = needle + '- public compiler type signatures advertise the same immutable tuple contract enforced at runtime for candidate and edge inputs;\n'
assert y.count(needle) == 1
d.write_text(y.replace(needle, repl, 1).rstrip() + "\n")
