from pathlib import Path

SOURCE = Path("aura_project_context_compiler.py")
TESTS = Path("tests/test_aura_project_context_compiler.py")
ACCEPTANCE = Path("tests/test_aura_project_context_acceptance.py")
DOC = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
tests = TESTS.read_text(encoding="utf-8")
acceptance = ACCEPTANCE.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Receipt identity: normalize and STORE the canonical owner before digesting.
# ---------------------------------------------------------------------------
source = once(
    source,
    '    if _id(receipt.canonical_owner, "canonical_owner") != PROJECT_CANONICAL_OWNER:\n'
    '        raise ValueError("canonical_owner must remain the unified continuity owner")\n',
    '    canonical_owner = _id(receipt.canonical_owner, "canonical_owner")\n'
    '    if canonical_owner != PROJECT_CANONICAL_OWNER:\n'
    '        raise ValueError("canonical_owner must remain the unified continuity owner")\n'
    '    object.__setattr__(receipt, "canonical_owner", canonical_owner)\n',
    "receipt canonical owner normalization",
)

# ---------------------------------------------------------------------------
# Every authoritative canonical reference gets a drift-sensitive binding.
# Reuse the existing TemporalBinding plane; do not introduce another owner.
# ---------------------------------------------------------------------------
candidate_anchor = "\n\n@dataclass(frozen=True)\nclass ProjectContextCandidate:\n"
candidate_helpers = '''

def _canonical_reference_binding_kind(
    category: CandidateCategory,
) -> TemporalBindingKind:
    if category is CandidateCategory.SOURCE:
        return TemporalBindingKind.SOURCE_HASH
    if category is CandidateCategory.POLICY:
        return TemporalBindingKind.POLICY
    if category in {
        CandidateCategory.TEST,
        CandidateCategory.SCHEMA,
        CandidateCategory.FAILED_ATTEMPT,
        CandidateCategory.PROOF_OBLIGATION,
    }:
        return TemporalBindingKind.EVIDENCE
    return TemporalBindingKind.OWNER_RECORD


def _bind_candidate_reference_identity(candidate: Any) -> None:
    if (
        candidate.truth_class
        not in {CandidateTruthClass.EXACT_CURRENT, CandidateTruthClass.DERIVED_VERIFIED}
        or candidate.reference is None
    ):
        return
    reference_binding = TemporalBinding(
        _canonical_reference_binding_kind(candidate.category),
        candidate.reference.reference_id,
        candidate.reference.digest,
    )
    by_key = {item.key: item for item in candidate.temporal_bindings}
    existing = by_key.get(reference_binding.key)
    if existing is not None and existing.digest != reference_binding.digest:
        raise ValueError(
            "authoritative reference binding conflicts with canonical reference digest"
        )
    if existing is None:
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


@dataclass(frozen=True)
class ProjectContextCandidate:
'''
source = once(source, candidate_anchor, candidate_helpers, "canonical reference binding helpers")
source = once(
    source,
    '        _validate_candidate_reference(self)\n        _validate_candidate_authority(self)\n',
    '        _validate_candidate_reference(self)\n'
    '        _validate_candidate_authority(self)\n'
    '        _bind_candidate_reference_identity(self)\n',
    "canonical reference binding call",
)

# ---------------------------------------------------------------------------
# Cross-candidate temporal identity conflicts become ordinary conflict IDs, so
# the normal compiler receipt exposes them instead of materializing incoherent
# COMPLETE state. Public construction already re-runs _conflicts().
# ---------------------------------------------------------------------------
old_conflicts = '''def _conflicts(candidates: Mapping[str, ProjectContextCandidate]) -> set[str]:
    groups: dict[str, list[ProjectContextCandidate]] = {}
    for candidate in candidates.values():
        if (
            candidate.conflict_key
            and _problem(candidate) is None
            and candidate.reference is not None
        ):
            groups.setdefault(candidate.conflict_key, []).append(candidate)
    result: set[str] = set()
    for items in groups.values():
        if len(
            {item.reference.digest for item in items if item.reference is not None}
        ) > 1:
            result.update(item.candidate_id for item in items)
    return result
'''
new_conflicts = '''def _conflicts(candidates: Mapping[str, ProjectContextCandidate]) -> set[str]:
    groups: dict[str, list[ProjectContextCandidate]] = {}
    binding_groups: dict[str, list[tuple[ProjectContextCandidate, TemporalBinding]]] = {}
    for candidate in candidates.values():
        if (
            candidate.conflict_key
            and _problem(candidate) is None
            and candidate.reference is not None
        ):
            groups.setdefault(candidate.conflict_key, []).append(candidate)
        for binding in candidate.temporal_bindings:
            binding_groups.setdefault(binding.key, []).append((candidate, binding))
    result: set[str] = set()
    for items in groups.values():
        if len(
            {item.reference.digest for item in items if item.reference is not None}
        ) > 1:
            result.update(item.candidate_id for item in items)
    for items in binding_groups.values():
        if len({binding.to_dict()["digest"] for _, binding in items}) > 1:
            result.update(candidate.candidate_id for candidate, _ in items)
    return result


def _expired_binding_candidate_ids(
    candidates: Sequence[ProjectContextCandidate],
    freshness_timestamp_ms: int,
) -> set[str]:
    return {
        candidate.candidate_id
        for candidate in candidates
        if any(
            binding.expires_at_ms
            and freshness_timestamp_ms >= binding.expires_at_ms
            for binding in candidate.temporal_bindings
        )
    }
'''
source = once(source, old_conflicts, new_conflicts, "temporal conflict classification")

# ---------------------------------------------------------------------------
# Timestamp-aware selection: already-expired evidence remains receipt-visible
# as stale and cannot satisfy mandatory closure or optional selection.
# ---------------------------------------------------------------------------
source = once(
    source,
    '''def _selection_buckets(
    candidates: Sequence[ProjectContextCandidate],
    candidate_map: Mapping[str, ProjectContextCandidate],
) -> tuple[set[str], dict[str, set[str]]]:
    conflict_ids = _conflicts(candidate_map)
''',
    '''def _selection_buckets(
    candidates: Sequence[ProjectContextCandidate],
    candidate_map: Mapping[str, ProjectContextCandidate],
    freshness_timestamp_ms: int,
) -> tuple[set[str], set[str], dict[str, set[str]]]:
    conflict_ids = _conflicts(candidate_map)
    expired_ids = _expired_binding_candidate_ids(candidates, freshness_timestamp_ms)
''',
    "selection bucket signature",
)
source = once(
    source,
    '''    buckets["conflicting"].update(conflict_ids)
    for candidate in candidates:
''',
    '''    buckets["conflicting"].update(conflict_ids)
    buckets["stale"].update(expired_ids)
    for candidate in candidates:
''',
    "expired stale receipt bucket",
)
source = once(
    source,
    '''    return conflict_ids, buckets


def _mandatory_selection(
''',
    '''    return conflict_ids, expired_ids, buckets


def _mandatory_selection(
''',
    "selection bucket return",
)
source = once(
    source,
    '''    conflict_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
) -> tuple[set[str], set[str]]:
''',
    '''    conflict_ids: set[str],
    expired_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
) -> tuple[set[str], set[str]]:
''',
    "mandatory selection expired parameter",
)
source = once(
    source,
    '''        if item in conflict_ids or _problem(candidate_map[item]) is not None
''',
    '''        if item in conflict_ids
        or item in expired_ids
        or _problem(candidate_map[item]) is not None
''',
    "mandatory expired invalidation",
)
source = once(
    source,
    '''def _optional_candidates(
    candidates: Sequence[ProjectContextCandidate],
    mandatory: set[str],
    conflict_ids: set[str],
) -> list[ProjectContextCandidate]:
''',
    '''def _optional_candidates(
    candidates: Sequence[ProjectContextCandidate],
    mandatory: set[str],
    conflict_ids: set[str],
    expired_ids: set[str],
) -> list[ProjectContextCandidate]:
''',
    "optional candidates expired parameter",
)
source = once(
    source,
    '''            and item.candidate_id not in conflict_ids
            and _problem(item) is None
''',
    '''            and item.candidate_id not in conflict_ids
            and item.candidate_id not in expired_ids
            and _problem(item) is None
''',
    "optional candidates expired filter",
)
source = once(
    source,
    '''    conflict_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
    selected: set[str],
) -> None:
''',
    '''    conflict_ids: set[str],
    expired_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
    selected: set[str],
) -> None:
''',
    "consider optional expired parameter",
)
source = once(
    source,
    '''        member in conflict_ids or _problem(candidate_map[member]) is not None
        for member in closure
''',
    '''        member in conflict_ids
        or member in expired_ids
        or _problem(candidate_map[member]) is not None
        for member in closure
''',
    "optional closure expired invalidation",
)
source = once(
    source,
    '''    conflict_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
    selected: set[str],
) -> None:
    for candidate in _optional_candidates(candidates, mandatory, conflict_ids):
        _consider_optional_candidate(
            candidate,
            candidate_map,
            conflict_ids,
            buckets,
''',
    '''    conflict_ids: set[str],
    expired_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
    selected: set[str],
) -> None:
    for candidate in _optional_candidates(
        candidates, mandatory, conflict_ids, expired_ids
    ):
        _consider_optional_candidate(
            candidate,
            candidate_map,
            conflict_ids,
            expired_ids,
            buckets,
''',
    "extend optional expired threading",
)

# Validate timestamp before selection and thread temporal state through selection.
source = once(
    source,
    '''    candidate_map, edge_items = _validate_compile_context(
        repository_identity, candidates, edges, budget
    )
    conflict_ids, buckets = _selection_buckets(candidates, candidate_map)
    mandatory, selected = _mandatory_selection(
        candidates, candidate_map, conflict_ids, buckets, budget
    )
''',
    '''    candidate_map, edge_items = _validate_compile_context(
        repository_identity, candidates, edges, budget
    )
    freshness_timestamp_ms = _int(
        freshness_timestamp_ms,
        "freshness_timestamp_ms",
        maximum=2**63 - 1,
    )
    conflict_ids, expired_ids, buckets = _selection_buckets(
        candidates, candidate_map, freshness_timestamp_ms
    )
    mandatory, selected = _mandatory_selection(
        candidates,
        candidate_map,
        conflict_ids,
        expired_ids,
        buckets,
        budget,
    )
''',
    "compiler temporal selection setup",
)
source = once(
    source,
    '''        mandatory,
        conflict_ids,
        buckets,
        budget,
''',
    '''        mandatory,
        conflict_ids,
        expired_ids,
        buckets,
        budget,
''',
    "compiler optional temporal threading",
)

# ---------------------------------------------------------------------------
# Public constructor parity: clearer missing-reference error, reject selected
# temporal conflicts/expired bindings, and reconstruct compiler-derived PR1
# projection fields (freshness/purpose/warnings/etc.).
# ---------------------------------------------------------------------------
source = once(
    source,
    '''    reference_ids = {
        item.reference.reference_id
        for item in selected
        if item.reference is not None
    }
    if len(reference_ids) != len(selected):
        raise ValueError(
            "selected candidates must have unique canonical references"
        )
''',
    '''    if any(item.reference is None for item in selected):
        raise ValueError("selected candidate is missing canonical reference")
    reference_ids = {item.reference.reference_id for item in selected}
    if len(reference_ids) != len(selected):
        raise ValueError(
            "selected candidates must have unique canonical references"
        )
''',
    "selected missing reference attribution",
)
selection_guard = '''    selected_conflicts = _conflicts(selected_map)
    if selected_conflicts:
        raise ValueError(
            "selected candidates must not contain unresolved conflicts: "
            f"{sorted(selected_conflicts)}"
        )
    has_exact_answer_source = any(
'''
selection_guard_new = '''    selected_conflicts = _conflicts(selected_map)
    if selected_conflicts:
        raise ValueError(
            "selected candidates must not contain unresolved conflicts: "
            f"{sorted(selected_conflicts)}"
        )
    if compilation.selection_receipt.status is SelectionStatus.COMPLETE:
        if compilation.projection is None:
            raise ValueError("COMPLETE selection requires a projection timestamp")
        expired_ids = _expired_binding_candidate_ids(
            selected, compilation.projection.freshness_timestamp_ms
        )
        if expired_ids:
            raise ValueError(
                "selected temporal binding expired at compilation timestamp: "
                f"{sorted(expired_ids)}"
            )
    has_exact_answer_source = any(
'''
source = once(source, selection_guard, selection_guard_new, "public temporal parity")
source = once(
    source,
    '''        if tuple(ref.to_dict() for ref in actual_refs) != tuple(
            ref.to_dict() for ref in canonical_expected
        ):
            raise ValueError(
                f"projection {field_name} references do not match selected candidates"
            )


def _finalize_compilation(compilation: Any) -> None:
''',
    '''        if tuple(ref.to_dict() for ref in actual_refs) != tuple(
            ref.to_dict() for ref in canonical_expected
        ):
            raise ValueError(
                f"projection {field_name} references do not match selected candidates"
            )
    expected_projection = _projection(
        compilation.objective,
        projection.project_ref,
        compilation.repository_identity,
        selected,
        projection.freshness_timestamp_ms,
        _selection_warnings(compilation.selection_receipt),
    )
    if projection.to_dict() != expected_projection.to_dict():
        raise ValueError("projection derived fields do not match compiler reconstruction")


def _finalize_compilation(compilation: Any) -> None:
''',
    "public projection reconstruction parity",
)

# ---------------------------------------------------------------------------
# Provenance: prove every requested start, not merely discovered roots. Cycles
# are explicitly incomplete instead of disappearing from root detection.
# ---------------------------------------------------------------------------
prov_anchor = '''

def _provenance_summary(
    node_map: Mapping[str, ProjectContextCandidate],
    incoming: Mapping[str, Sequence[ProjectContextEdge]],
    seen: set[str],
    traversed: set[ProjectContextEdge],
) -> tuple[
'''
prov_helpers = '''

def _provenance_start_is_source_complete(
    start_id: str,
    node_map: Mapping[str, ProjectContextCandidate],
    incoming: Mapping[str, Sequence[ProjectContextEdge]],
    traversed: set[ProjectContextEdge],
) -> bool:
    memo: dict[str, bool] = {}
    visiting: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            return False
        visiting.add(node_id)
        predecessors = [
            edge for edge in incoming.get(node_id, ()) if edge in traversed
        ]
        candidate = node_map[node_id]
        if not predecessors:
            result = (
                candidate.category is CandidateCategory.SOURCE
                and candidate.truth_class is CandidateTruthClass.EXACT_CURRENT
            )
        else:
            result = all(
                edge.truth_class in _AUTHORITATIVE_EDGE_TRUTH
                and visit(edge.source_id)
                for edge in predecessors
            )
        visiting.remove(node_id)
        memo[node_id] = result
        return result

    return visit(start_id)


def _provenance_summary(
    starts: Sequence[str],
    node_map: Mapping[str, ProjectContextCandidate],
    incoming: Mapping[str, Sequence[ProjectContextEdge]],
    seen: set[str],
    traversed: set[ProjectContextEdge],
) -> tuple[
'''
source = once(source, prov_anchor, prov_helpers, "per-start provenance helper")
source = once(
    source,
    '''    roots_are_exact_sources = bool(root_ids) and all(
        node_map[node_id].category is CandidateCategory.SOURCE
        and node_map[node_id].truth_class is CandidateTruthClass.EXACT_CURRENT
        for node_id in root_ids
    )
    authoritative_path = all(
''',
    '''    starts_are_source_complete = bool(starts) and all(
        _provenance_start_is_source_complete(
            start_id, node_map, incoming, traversed
        )
        for start_id in starts
    )
    authoritative_path = all(
''',
    "per-start provenance completeness",
)
source = once(
    source,
    '        roots_are_exact_sources,\n        authoritative_path,\n',
    '        starts_are_source_complete,\n        authoritative_path,\n',
    "provenance summary return",
)
source = once(
    source,
    '    roots_are_exact_sources: bool,\n    authoritative_path: bool,\n',
    '    starts_are_source_complete: bool,\n    authoritative_path: bool,\n',
    "provenance result parameter",
)
source = once(
    source,
    '            roots_are_exact_sources and authoritative_path and not truncated\n',
    '            starts_are_source_complete and authoritative_path and not truncated\n',
    "provenance completeness gate",
)
source = once(
    source,
    '    summary = _provenance_summary(node_map, incoming, seen, traversed)\n',
    '    summary = _provenance_summary(starts, node_map, incoming, seen, traversed)\n',
    "provenance summary call",
)

# ---------------------------------------------------------------------------
# Regressions.
# ---------------------------------------------------------------------------
tests = once(
    tests,
    'from __future__ import annotations\n\nimport json\n',
    'from __future__ import annotations\n\nfrom dataclasses import replace\nimport json\n',
    "test replace import",
)

# Existing expiry test should compile while valid, then observe at exact expiry.
tests = once(
    tests,
    '''    bindings = tuple(TemporalBinding(kind, f"id-{index}", D[str(index + 2)], expires_at_ms=2_000) for index, kind in enumerate(TemporalBindingKind))
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True, bindings=bindings)
    current = {item.key: item.digest for item in bindings}
    freshness = validate_project_context_freshness(_compile((source,)), current_repository_identity=_repo(), current_bindings=current, observed_at_ms=2_000)
''',
    '''    expiry_ms = 1_786_180_000_010
    bindings = tuple(TemporalBinding(kind, f"id-{index}", D[str(index + 2)], expires_at_ms=expiry_ms) for index, kind in enumerate(TemporalBindingKind))
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True, bindings=bindings)
    result = _compile((source,))
    current = {
        item.key: item.digest
        for item in result.selected_candidates[0].temporal_bindings
    }
    freshness = validate_project_context_freshness(result, current_repository_identity=_repo(), current_bindings=current, observed_at_ms=expiry_ms)
''',
    "existing expiry test chronology",
)

regressions = r'''


def test_receipt_canonical_owner_is_normalized_before_digest() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    receipt = _compile((source,)).selection_receipt
    normalized = ProjectionSelectionReceipt(
        objective_digest=receipt.objective_digest,
        repository_identity_digest=receipt.repository_identity_digest,
        canonical_owner=" aura_unified_memory_continuity ",
        selected=receipt.selected,
        omitted_irrelevant=receipt.omitted_irrelevant,
        omitted_by_budget=receipt.omitted_by_budget,
        stale=receipt.stale,
        unavailable=receipt.unavailable,
        conflicting=receipt.conflicting,
        source_adapter_missing=receipt.source_adapter_missing,
        mandatory_evidence_missing=receipt.mandatory_evidence_missing,
        status=receipt.status,
        budget=receipt.budget,
    )
    assert normalized.canonical_owner == "aura_unified_memory_continuity"
    assert normalized.to_dict()["canonical_owner"] == "aura_unified_memory_continuity"


def test_public_constructor_rejects_forged_projection_aggregate_freshness() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"],
        answer_determining=True, freshness="BOUNDED",
    )
    result = _compile((source,))
    assert result.projection is not None
    forged = replace(result.projection, freshness_class="CURRENT", projection_digest="")
    with pytest.raises(ValueError, match="projection derived fields"):
        ProjectContextCompilation(
            objective=result.objective,
            objective_digest=result.objective_digest,
            repository_identity=result.repository_identity,
            projection=forged,
            selection_receipt=result.selection_receipt,
            selected_candidates=result.selected_candidates,
            graph_edges=result.graph_edges,
            admissible=result.admissible,
        )


def test_provenance_rootless_cycle_component_cannot_claim_source_complete() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    left = _candidate("decision:left", CandidateCategory.DECISION, D["3"])
    right = _candidate("decision:right", CandidateCategory.DECISION, D["4"])
    edges = (
        ProjectContextEdge("decision:left", "decision:right", "precedes", EdgeTruthClass.EXACT),
        ProjectContextEdge("decision:right", "decision:left", "precedes", EdgeTruthClass.EXACT),
    )
    result = _compile((source, left, right), edges)
    trace = trace_project_context_provenance(
        result, ("source:target", "decision:left"), max_hops=4, max_nodes=8
    )
    assert trace["exact_source_ids"] == ["source:target"]
    assert trace["truncated_frontier"] == []
    assert trace["authoritative_path"] is True
    assert trace["source_complete"] is False


def test_authoritative_reference_requires_live_reference_digest_observation() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    result = _compile((source,))
    selected_source = result.selected_candidates[0]
    assert selected_source.reference is not None
    reference_binding = next(
        item
        for item in selected_source.temporal_bindings
        if item.kind is TemporalBindingKind.SOURCE_HASH
        and item.binding_id == selected_source.reference.reference_id
    )
    missing = validate_project_context_freshness(
        result,
        current_repository_identity=_repo(),
        current_bindings={},
        observed_at_ms=1_786_180_000_001,
    )
    assert missing["valid"] is False
    assert f"binding_missing:{reference_binding.key}" in missing["reasons"]
    current = validate_project_context_freshness(
        result,
        current_repository_identity=_repo(),
        current_bindings={reference_binding.key: reference_binding.digest},
        observed_at_ms=1_786_180_000_001,
    )
    assert current["valid"] is True


def test_cross_candidate_temporal_binding_conflict_is_receipt_visible() -> None:
    left_binding = TemporalBinding(TemporalBindingKind.POLICY, "shared-policy", D["7"])
    right_binding = TemporalBinding(TemporalBindingKind.POLICY, "shared-policy", D["8"])
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"],
        answer_determining=True, bindings=(left_binding,),
    )
    proof = _candidate(
        "proof:result", CandidateCategory.PROOF_OBLIGATION, D["3"],
        bindings=(right_binding,),
    )
    result = _compile((source, proof))
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert set(result.selection_receipt.conflicting) == {"source:target", "proof:result"}
    assert set(result.selection_receipt.mandatory_evidence_missing) >= {"source:target", "proof:result"}
    assert result.projection is None


def test_public_constructor_rejects_cross_candidate_temporal_binding_conflict() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    proof = _candidate("proof:result", CandidateCategory.PROOF_OBLIGATION, D["3"])
    complete = _compile((source, proof))
    shared_left = TemporalBinding(TemporalBindingKind.POLICY, "shared-policy", D["7"])
    shared_right = TemporalBinding(TemporalBindingKind.POLICY, "shared-policy", D["8"])
    forged = tuple(
        replace(
            candidate,
            temporal_bindings=(*candidate.temporal_bindings, shared_left if candidate.candidate_id == "source:target" else shared_right),
        )
        for candidate in complete.selected_candidates
    )
    with pytest.raises(ValueError, match="unresolved conflicts"):
        ProjectContextCompilation(
            objective=complete.objective,
            objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity,
            projection=complete.projection,
            selection_receipt=complete.selection_receipt,
            selected_candidates=forged,
            graph_edges=complete.graph_edges,
            admissible=True,
        )


def test_expired_binding_is_stale_and_incomplete_at_compile_time() -> None:
    binding = TemporalBinding(
        TemporalBindingKind.LEASE,
        "expired-lease",
        D["7"],
        expires_at_ms=1_786_180_000_000,
    )
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"],
        answer_determining=True, bindings=(binding,),
    )
    result = _compile((source,))
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert result.selection_receipt.stale == ("source:target",)
    assert "source:target" in result.selection_receipt.mandatory_evidence_missing
    assert result.projection is None


def test_public_constructor_rejects_binding_expired_by_forged_projection_timestamp() -> None:
    binding = TemporalBinding(
        TemporalBindingKind.LEASE,
        "future-lease",
        D["7"],
        expires_at_ms=1_786_180_000_010,
    )
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"],
        answer_determining=True, bindings=(binding,),
    )
    result = _compile((source,))
    assert result.projection is not None
    forged = replace(
        result.projection,
        freshness_timestamp_ms=binding.expires_at_ms,
        projection_digest="",
    )
    with pytest.raises(ValueError, match="expired at compilation timestamp"):
        ProjectContextCompilation(
            objective=result.objective,
            objective_digest=result.objective_digest,
            repository_identity=result.repository_identity,
            projection=forged,
            selection_receipt=result.selection_receipt,
            selected_candidates=result.selected_candidates,
            graph_edges=result.graph_edges,
            admissible=result.admissible,
        )
'''
if "test_receipt_canonical_owner_is_normalized_before_digest" in tests:
    raise SystemExit("six-invariant regressions already present")
tests = tests.rstrip() + regressions + "\n"

# CodeRabbit auditability precondition for the edge-budget forged constructor test.
acceptance = once(
    acceptance,
    '''    complete = _compile((source, direct_test), edges)
    forged_receipt = ProjectionSelectionReceipt(
''',
    '''    complete = _compile((source, direct_test), edges)
    assert len(complete.graph_edges) == 2
    forged_receipt = ProjectionSelectionReceipt(
''',
    "edge budget precondition",
)

# Documentation: preserve IMPLEMENTING and describe the tightened temporal and provenance contracts.
temporal_anchor = (
    "Freshness validation compares the complete compiled repository identity and every selected temporal binding against current canonical observations. "
)
temporal_text = (
    temporal_anchor
    + "Every authoritative selected canonical reference is automatically represented by a drift-sensitive temporal binding over its exact canonical-reference digest, using the existing SOURCE_HASH, EVIDENCE, POLICY, or OWNER_RECORD binding classes according to evidence category. Cross-candidate binding definitions with the same key must agree; conflicting mandatory evidence is receipt-visible and prevents admission. A binding already expired at the compilation freshness timestamp is classified as stale before selection and prevents mandatory admission. "
)
doc = once(doc, temporal_anchor, temporal_text, "temporal documentation")
prov_anchor_doc = (
    "A trace is `source_complete` only when every retained provenance root is an `EXACT_CURRENT` `SOURCE`, every traversed path edge is `EXACT` or `DERIVED_VERIFIED`, and no predecessor frontier was truncated. "
)
prov_text_doc = (
    "A trace is `source_complete` only when every requested start's complete backward component terminates at `EXACT_CURRENT` `SOURCE` nodes through only `EXACT` or `DERIVED_VERIFIED` edges, no rootless or cyclic component remains unproved, and no predecessor frontier was truncated. "
)
doc = once(doc, prov_anchor_doc, prov_text_doc, "provenance documentation")

SOURCE.write_text(source, encoding="utf-8")
TESTS.write_text(tests, encoding="utf-8")
ACCEPTANCE.write_text(acceptance, encoding="utf-8")
DOC.write_text(doc, encoding="utf-8")
