from pathlib import Path
import re

SOURCE = Path("aura_project_context_compiler.py")
COMPILER_TESTS = Path("tests/test_aura_project_context_compiler.py")
ACCEPTANCE_TESTS = Path("tests/test_aura_project_context_acceptance.py")
DOC = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
compiler_tests = COMPILER_TESTS.read_text(encoding="utf-8")
acceptance_tests = ACCEPTANCE_TESTS.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")

# Compilation owns project_ref independently; it is therefore included in its
# digest and can be rebound against the nested PR1 projection.
source = once(
    source,
    '''class ProjectContextCompilation:\n    objective: str\n    objective_digest: str\n''',
    '''class ProjectContextCompilation:\n    objective: str\n    project_ref: str\n    objective_digest: str\n''',
    "compilation project_ref field",
)
source = once(
    source,
    '''    object.__setattr__(\n        compilation,\n        "objective_digest",\n        _digest(compilation.objective_digest, "objective_digest"),\n    )\n''',
    '''    object.__setattr__(\n        compilation,\n        "project_ref",\n        _text(compilation.project_ref, "project_ref"),\n    )\n    object.__setattr__(\n        compilation,\n        "objective_digest",\n        _digest(compilation.objective_digest, "objective_digest"),\n    )\n''',
    "compilation project_ref normalization",
)
source = once(
    source,
    '''    if projection.objective_digest != compilation.objective_digest:\n        raise ValueError(\n            "projection objective is not bound to compilation"\n        )\n''',
    '''    if projection.project_ref != compilation.project_ref:\n        raise ValueError("projection project_ref is not bound to compilation")\n    if projection.objective_digest != compilation.objective_digest:\n        raise ValueError(\n            "projection objective is not bound to compilation"\n        )\n''',
    "projection project_ref parity",
)
source = once(
    source,
    '''        compilation.objective,\n        projection.project_ref,\n        compilation.repository_identity,\n''',
    '''        compilation.objective,\n        compilation.project_ref,\n        compilation.repository_identity,\n''',
    "expected projection project_ref",
)
source = once(
    source,
    '''            "objective": self.objective,\n            "objective_digest": self.objective_digest,\n''',
    '''            "objective": self.objective,\n            "project_ref": self.project_ref,\n            "objective_digest": self.objective_digest,\n''',
    "compilation serialized project_ref",
)
source = once(
    source,
    '''            "version": PROJECT_CONTEXT_COMPILATION_VERSION,\n            "objective_digest": self.objective_digest,\n''',
    '''            "version": PROJECT_CONTEXT_COMPILATION_VERSION,\n            "compilation_digest": self.compilation_digest,\n            "project_ref": self.project_ref,\n            "objective_digest": self.objective_digest,\n''',
    "headless compilation identity",
)
source = once(
    source,
    '''    return ProjectContextCompilation(\n        objective=objective,\n        objective_digest=objective_digest,\n''',
    '''    return ProjectContextCompilation(\n        objective=objective,\n        project_ref=project_ref,\n        objective_digest=objective_digest,\n''',
    "compiler materialization project_ref",
)

# Public COMPLETE construction re-proves the canonical reference binding rather
# than merely relying on the candidate constructor having run once.
selection_anchor = '''    has_exact_answer_source = any(\n        item.category is CandidateCategory.SOURCE\n        and item.truth_class is CandidateTruthClass.EXACT_CURRENT\n        and item.answer_determining\n        for item in selected\n    )\n'''
selection_replacement = '''    authoritative_unbound = sorted(\n        item.candidate_id\n        for item in selected\n        if item.truth_class in _ELIGIBLE_TRUTH\n        and item.reference is not None\n        and not any(\n            binding.kind is _canonical_reference_binding_kind(item.category)\n            and binding.binding_id == item.reference.reference_id\n            and binding.digest == item.reference.digest\n            for binding in item.temporal_bindings\n        )\n    )\n    if (\n        compilation.selection_receipt.status is SelectionStatus.COMPLETE\n        and authoritative_unbound\n    ):\n        raise ValueError(\n            "COMPLETE selection requires drift-sensitive canonical-reference bindings: "\n            f"{authoritative_unbound}"\n        )\n    has_exact_answer_source = any(\n        item.category is CandidateCategory.SOURCE\n        and item.truth_class is CandidateTruthClass.EXACT_CURRENT\n        and item.answer_determining\n        for item in selected\n    )\n'''
source = once(source, selection_anchor, selection_replacement, "public canonical binding parity")

# Export public payload discriminators/marker so clients never need magic strings.
source = once(
    source,
    '''    "PROJECT_CONTEXT_COMPILATION_VERSION",\n    "MEMORY_LIFECYCLE_PHASES",\n''',
    '''    "PROJECT_CONTEXT_COMPILATION_VERSION",\n    "PROJECT_CONTEXT_PROVENANCE_VERSION",\n    "PROJECT_CONTEXT_FRESHNESS_VERSION",\n    "MISSING_SELECTED_SOURCE_ID",\n    "MEMORY_LIFECYCLE_PHASES",\n''',
    "public exports",
)

# All focused-test public constructor fixtures are based on the module helpers' fixed project refs.
def add_project_ref(text: str, expression: str) -> str:
    pattern = re.compile(r"(?m)^(\s*)ProjectContextCompilation\(\n")
    def repl(match: re.Match[str]) -> str:
        indent = match.group(1)
        return f'{indent}ProjectContextCompilation(\n{indent}    project_ref={expression},\n'
    updated, count = pattern.subn(repl, text)
    if count == 0:
        raise SystemExit("no ProjectContextCompilation test constructors found")
    return updated

compiler_tests = add_project_ref(compiler_tests, '"project:auraos-pr3"')
acceptance_tests = add_project_ref(acceptance_tests, "PROJECT_REF")

compiler_regression = r'''


def test_public_constructor_binds_project_ref_into_compilation_identity() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    result = _compile((source,))
    assert result.projection is not None
    forged_projection = replace(
        result.projection,
        project_ref="project:other-context",
        projection_digest="",
    )
    with pytest.raises(ValueError, match="projection project_ref is not bound"):
        ProjectContextCompilation(
            project_ref=result.project_ref,
            objective=result.objective,
            objective_digest=result.objective_digest,
            repository_identity=result.repository_identity,
            projection=forged_projection,
            selection_receipt=result.selection_receipt,
            selected_candidates=result.selected_candidates,
            graph_edges=result.graph_edges,
            admissible=result.admissible,
        )


def test_headless_projection_carries_compilation_identity() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    result = _compile((source,))
    payload = result.headless_projection()
    assert payload["project_ref"] == result.project_ref
    assert payload["compilation_digest"] == result.compilation_digest
'''
if "test_public_constructor_binds_project_ref_into_compilation_identity" in compiler_tests:
    raise SystemExit("project-ref regression already present")
compiler_tests = compiler_tests.rstrip() + compiler_regression + "\n"

# Make the public-constructor authority parity test adversarial by removing the
# synthesized canonical binding after construction, then proving COMPLETE rejects it.
binding_regression = r'''


def test_public_constructor_rejects_authoritative_candidate_without_canonical_binding() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    result = _compile((source,))
    tampered = replace(source, temporal_bindings=())
    object.__setattr__(tampered, "temporal_bindings", ())
    with pytest.raises(ValueError, match="drift-sensitive canonical-reference bindings"):
        ProjectContextCompilation(
            project_ref=result.project_ref,
            objective=result.objective,
            objective_digest=result.objective_digest,
            repository_identity=result.repository_identity,
            projection=result.projection,
            selection_receipt=result.selection_receipt,
            selected_candidates=(tampered,),
            graph_edges=result.graph_edges,
            admissible=result.admissible,
        )
'''
compiler_tests = compiler_tests.rstrip() + binding_regression + "\n"

# Documentation: compilation identity owns project_ref and headless output is digest-bound.
doc = once(
    doc,
    '''An `INCOMPLETE` compilation has `projection: null`; the same is true through `headless_projection()`. ''',
    '''An `INCOMPLETE` compilation has `projection: null`; the same is true through `headless_projection()`. PR3's compilation record independently owns `project_ref`; that value is included in the compilation digest and the nested PR1 projection must match it, so a hand-built projection cannot silently substitute a different project identity. ''',
    "project identity documentation",
)
doc = once(
    doc,
    '''The complete repository/project topology is not sent to the client by default. Exact canonical references survive the headless path. ''',
    '''The complete repository/project topology is not sent to the client by default. The headless payload includes `project_ref` and `compilation_digest`, and exact canonical references survive the headless path. ''',
    "headless identity documentation",
)

SOURCE.write_text(source, encoding="utf-8")
COMPILER_TESTS.write_text(compiler_tests, encoding="utf-8")
ACCEPTANCE_TESTS.write_text(acceptance_tests, encoding="utf-8")
DOC.write_text(doc, encoding="utf-8")
