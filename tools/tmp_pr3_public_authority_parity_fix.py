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
    '''    ineligible_selected = {\n        item.candidate_id: problem\n        for item in selected\n        if (problem := _problem(item)) is not None\n    }\n''',
    '''    for item in selected:\n        _validate_candidate_reference(item)\n        _validate_candidate_authority(item)\n    ineligible_selected = {\n        item.candidate_id: problem\n        for item in selected\n        if (problem := _problem(item)) is not None\n    }\n''',
    "public authority parity validation",
)

regressions = r'''


def test_public_constructor_rejects_tampered_authoritative_origin() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    result = _compile((source,))
    tampered = replace(source)
    object.__setattr__(tampered, "origin_ref", "forged://different-origin")
    with pytest.raises(ValueError, match="origin_ref must equal"):
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


def test_public_constructor_rejects_tampered_authority_escalation() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    result = _compile((source,))
    tampered = replace(source)
    object.__setattr__(tampered, "authority_class", ContextAuthorityClass.DERIVED_READ)
    with pytest.raises(ValueError, match="authority class does not match"):
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
if "test_public_constructor_rejects_tampered_authoritative_origin" in tests:
    raise SystemExit("authority parity regressions already present")
tests = tests.rstrip() + regressions + "\n"

doc = once(
    doc,
    '''The public `ProjectContextCompilation` constructor also rejects a hand-assembled `INCOMPLETE` record that attempts to smuggle in a PR1 projection, independently re-proves the exact-current answer-determining source anchor for a hand-assembled `COMPLETE` record, revalidates every selected candidate against the same truth/availability/freshness eligibility boundary used by the compiler, and independently rejects the reserved `source:selected` missing-source marker. ''',
    '''The public `ProjectContextCompilation` constructor also rejects a hand-assembled `INCOMPLETE` record that attempts to smuggle in a PR1 projection, independently re-proves the exact-current answer-determining source anchor for a hand-assembled `COMPLETE` record, revalidates every selected candidate against the same reference, truth, availability, origin, authority, and freshness boundaries used by the compiler, and independently rejects the reserved `source:selected` missing-source marker. ''',
    "public parity documentation",
)

SOURCE.write_text(source, encoding="utf-8")
TESTS.write_text(tests, encoding="utf-8")
DOC.write_text(doc, encoding="utf-8")
