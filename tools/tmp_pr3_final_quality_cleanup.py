from __future__ import annotations

import ast
from pathlib import Path

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

# Make the bounded pre-selection edge allowance explicit rather than hiding a
# magic multiplier in the guard. Final selected edges are still strictly capped
# by ProjectionBudget.max_edges.
source = once(
    source,
    'MAX_EDGES = 2048\nMAX_DEPENDENCIES = 64\n',
    'MAX_EDGES = 2048\n_EDGE_INPUT_EXPANSION_FACTOR = 4\nMAX_DEPENDENCIES = 64\n',
    "edge expansion constant",
)
source = once(
    source,
    '    if len(edge_items) > min(MAX_EDGES, budget.max_edges * 4) or any(\n',
    '    if len(edge_items) > min(\n        MAX_EDGES, budget.max_edges * _EDGE_INPUT_EXPANSION_FACTOR\n    ) or any(\n',
    "edge input ceiling",
)

# Encapsulate and validate the central CandidateCategory -> PR1 reference-field
# contract so future enum/PR1 changes fail explicitly instead of drifting.
category_anchor = '''_CATEGORY_PRIORITY = {
    category: index for index, category in enumerate(CandidateCategory)
}
'''
category_block = '''_PROJECTION_REFERENCE_FIELDS = frozenset(
    {
        "artifact_evidence_refs",
        "decision_refs",
        "rejected_alternative_refs",
        "unresolved_question_refs",
        "assumption_refs",
        "capability_refs",
        "relationship_refs",
        "blocker_refs",
        "next_action_refs",
    }
)


def _validate_projection_category_mapping() -> None:
    expected_categories = set(CandidateCategory)
    if set(_CATEGORY_FIELD) != expected_categories:
        raise RuntimeError("project-context category mapping is incomplete")
    mapped_fields = set(_CATEGORY_FIELD.values())
    if not mapped_fields.issubset(_PROJECTION_REFERENCE_FIELDS):
        raise RuntimeError("project-context category mapping uses an unsupported PR1 field")
    pr1_fields = set(ProjectContextProjection.__dataclass_fields__)
    if not mapped_fields.issubset(pr1_fields):
        raise RuntimeError("project-context category mapping is not present in PR1 projection")


def _projection_reference_field(category: CandidateCategory) -> str:
    try:
        return _CATEGORY_FIELD[category]
    except KeyError as exc:
        raise ValueError("candidate category has no PR1 projection field") from exc


_validate_projection_category_mapping()


_CATEGORY_PRIORITY = {
    category: index for index, category in enumerate(CandidateCategory)
}
'''
source = once(source, category_anchor, category_block, "category mapping validation")
source = source.replace(
    'expected_projection_refs[_CATEGORY_FIELD[item.category]].append(\n',
    'expected_projection_refs[_projection_reference_field(item.category)].append(\n',
)
source = source.replace(
    '        buckets[_CATEGORY_FIELD[candidate.category]].append(candidate.reference)\n',
    '        buckets[_projection_reference_field(candidate.category)].append(candidate.reference)\n',
)
source = source.replace(
    '        name: [] for name in set(_CATEGORY_FIELD.values())\n',
    '        name: [] for name in _PROJECTION_REFERENCE_FIELDS\n',
)

# Add concise production docstrings to every undocumented function/method. The
# text is intentionally short and invariant-focused; tests remain idiomatic
# pytest rather than being padded for the metric.
def doc_for(name: str) -> str:
    fixed = {
        "__post_init__": "Normalize and validate this immutable PR3 record after construction.",
        "to_dict": "Serialize this record into its deterministic dictionary representation.",
        "headless_projection": "Return the bounded client-safe projection payload.",
        "key": "Return the canonical temporal-binding key.",
        "origin_bound": "Report whether the claimed origin matches the canonical reference.",
        "authority_non_increasing": "Report whether the candidate preserves its allowed authority class.",
        "visit": "Visit one provenance node while detecting backward cycles.",
    }
    if name in fixed:
        return fixed[name]
    if name.startswith("_validate_"):
        return "Validate the corresponding PR3 invariant and fail closed on mismatch."
    if name.startswith("_normalize_"):
        return "Normalize the corresponding PR3 value into canonical form."
    if name.startswith("_canonical"):
        return "Canonicalize the corresponding PR3 structure deterministically."
    if name.startswith("_compile"):
        return "Compile the corresponding bounded PR3 structure from validated inputs."
    if name.startswith("_selection"):
        return "Compute deterministic project-context selection state."
    if name.startswith("_provenance"):
        return "Evaluate bounded provenance state without overclaiming completeness."
    if name.startswith("_projection"):
        return "Build or resolve the canonical PR1 project projection field."
    if name.startswith("_freshness"):
        return "Evaluate temporal freshness state for the compiled context."
    if name.startswith("_build"):
        return "Build the corresponding deterministic PR3 receipt structure."
    if name.startswith("_materialize"):
        return "Materialize the validated read-only project-context compilation."
    if name.startswith("_selected"):
        return "Resolve the selected bounded project-context subset."
    if name.startswith("_optional") or name.startswith("_consider_optional"):
        return "Evaluate optional context under the declared deterministic budget."
    if name.startswith("_mandatory"):
        return "Resolve mandatory context without silent clipping."
    if name.startswith("_extend"):
        return "Extend deterministic selection without exceeding declared bounds."
    if name == "compile_project_context_projection":
        return "Compile a deterministic source-first PR1 project-context projection."
    if name == "trace_project_context_provenance":
        return "Trace bounded backward provenance for selected project context."
    if name == "validate_project_context_freshness":
        return "Validate live repository and temporal identity against a compilation."
    if name == "_problem":
        return "Classify a candidate selection problem, if any."
    if name == "_closure":
        return "Compute deterministic dependency closure and missing dependencies."
    if name == "_conflicts":
        return "Identify unresolved content and temporal-binding conflicts."
    if name == "_expired_binding_candidate_ids":
        return "Identify candidates whose temporal bindings are already expired."
    if name == "_projection":
        return "Construct the canonical PR1 projection from selected exact references."
    if name == "_ids":
        return "Normalize, bound, deduplicate, and sort canonical identifiers."
    if name == "_text":
        return "Normalize bounded text into a canonical single-space form."
    if name == "_id":
        return "Normalize and validate a canonical identifier."
    if name == "_digest":
        return "Normalize and validate a lowercase SHA-256 digest."
    if name == "_enum":
        return "Normalize a value into the required enum class."
    if name == "_int":
        return "Validate a bounded integer while rejecting booleans."
    return "Enforce the corresponding deterministic PR3 helper contract."


tree = ast.parse(source)
lines = source.splitlines()
insertions: list[tuple[int, str]] = []
for node in ast.walk(tree):
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    if ast.get_docstring(node) is not None:
        continue
    first = node.body[0]
    indent = " " * first.col_offset
    insertions.append((first.lineno - 1, f'{indent}"""{doc_for(node.name)}"""'))
for index, text in sorted(insertions, reverse=True):
    lines.insert(index, text)
source = "\n".join(lines) + "\n"

# Regression: an optional endpoint omitted by the node budget makes its edge
# absent, while the omission remains attributable through the node receipt. PR3
# intentionally does not invent a second edge-omission receipt plane.
edge_test = r'''


def test_edge_to_budget_omitted_endpoint_is_absent_and_node_omission_is_visible() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    optional = _candidate(
        "decision:optional", CandidateCategory.DECISION, D["3"], relevance=1000
    )
    edge = ProjectContextEdge(
        "source:target", "decision:optional", "constrains", EdgeTruthClass.EXACT
    )
    result = _compile(
        (source, optional),
        (edge,),
        budget=ProjectionBudget(max_nodes=1, max_edges=8),
    )
    assert result.selection_receipt.omitted_by_budget == ("decision:optional",)
    assert result.graph_edges == ()
'''
if "test_edge_to_budget_omitted_endpoint_is_absent" in compiler_tests:
    raise SystemExit("edge omission regression already present")
compiler_tests = compiler_tests.rstrip() + edge_test + "\n"

# Regression: constructor rejects derived material attempting canonical-read
# authority. Preserve the useful serialization identity assertions already in
# the acceptance suite.
authority_test = r'''


def test_derived_verified_candidate_cannot_claim_canonical_read_authority() -> None:
    with pytest.raises(ValueError, match="authority class does not match"):
        _candidate(
            "decision:derived-escalation",
            CandidateCategory.DECISION,
            D["8"],
            truth=CandidateTruthClass.DERIVED_VERIFIED,
            authority=ContextAuthorityClass.CANONICAL_READ,
        )
'''
if "test_derived_verified_candidate_cannot_claim_canonical_read_authority" in acceptance_tests:
    raise SystemExit("derived authority regression already present")
acceptance_tests = acceptance_tests.rstrip() + authority_test + "\n"

# Document both maintainability decisions without changing the serialized
# receipt contract.
doc = once(
    doc,
    '''Optional candidates are ranked deterministically by declared relevance, then fixed category priority, then candidate ID. A candidate and its dependency closure are selected as a unit only when they fit.\n''',
    '''Optional candidates are ranked deterministically by declared relevance, then fixed category priority, then candidate ID. A candidate and its dependency closure are selected as a unit only when they fit. Candidate input edges may be accepted up to a bounded four-times selected-edge budget (never above the module-wide edge ceiling) so task-conditioned endpoint reduction can occur before the final selected graph is checked strictly against `max_edges`. An edge incident to an omitted node is absent from the selected graph; the existing node omission bucket remains the attributable reason, rather than introducing a second edge-omission receipt plane.\n''',
    "edge policy documentation",
)
doc = once(
    doc,
    '''PR3 does not change the PR1 serialized contract or PR2 runtime contract.\n''',
    '''The category-to-reference-field adapter is explicitly validated against every `CandidateCategory` and the current PR1 `ProjectContextProjection` dataclass fields at import time, so a future category or PR1 field change cannot silently drift the projection mapping.\n\nPR3 does not change the PR1 serialized contract or PR2 runtime contract.\n''',
    "category mapping documentation",
)

# Normalize EOF exactly: no trailing blank-line accumulation, one final newline.
source = source.rstrip() + "\n"
compiler_tests = compiler_tests.rstrip() + "\n"
acceptance_tests = acceptance_tests.rstrip() + "\n"
doc = doc.rstrip() + "\n"

SOURCE.write_text(source, encoding="utf-8")
COMPILER_TESTS.write_text(compiler_tests, encoding="utf-8")
ACCEPTANCE_TESTS.write_text(acceptance_tests, encoding="utf-8")
DOC.write_text(doc, encoding="utf-8")
