from pathlib import Path

SOURCE = Path("aura_project_context_compiler.py")
TESTS = Path("tests/test_aura_project_context_compiler.py")
DOC = Path("docs/AURA_SOURCE_FIRST_PROJECT_CONTEXT_PR3.md")


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
tests = TESTS.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")

# 1) Store the normalized canonical owner, not merely compare a normalized copy.
source = once(
    source,
    '    if _id(receipt.canonical_owner, "canonical_owner") != PROJECT_CANONICAL_OWNER:\n'
    '        raise ValueError("canonical_owner must remain the unified continuity owner")\n',
    '    canonical_owner = _id(receipt.canonical_owner, "canonical_owner")\n'
    '    if canonical_owner != PROJECT_CANONICAL_OWNER:\n'
    '        raise ValueError("canonical_owner must remain the unified continuity owner")\n'
    '    object.__setattr__(receipt, "canonical_owner", canonical_owner)\n',
    "receipt canonical owner",
)

# 2) Bind every authoritative canonical reference digest into temporal identity.
candidate_anchor = "\n\n@dataclass(frozen=True)\nclass ProjectContextCandidate:\n"
candidate_helper = '''

def _bind_candidate_reference_identity(candidate: Any) -> None:
    if (
        candidate.truth_class
        not in {CandidateTruthClass.EXACT_CURRENT, CandidateTruthClass.DERIVED_VERIFIED}
        or candidate.reference is None
    ):
        return
    reference_binding = TemporalBinding(
        TemporalBindingKind.SOURCE_HASH,
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
source = once(source, candidate_anchor, candidate_helper, "reference binding helper")
source = once(
    source,
    '        _validate_candidate_reference(self)\n        _validate_candidate_authority(self)\n',
    '        _validate_candidate_reference(self)\n'
    '        _validate_candidate_authority(self)\n'
    '        _bind_candidate_reference_identity(self)\n',
    "candidate reference binding call",
)

# 3) Selected temporal bindings must describe one coherent snapshot, and cannot
# already be expired at a COMPLETE projection's timestamp.
selection_anchor = '''

def _validate_compilation_selection(
    compilation: Any,
    selected: tuple[ProjectContextCandidate, ...],
    selected_map: Mapping[str, ProjectContextCandidate],
) -> None:
'''
selection_helper = '''

def _selected_temporal_binding_map(
    selected: Sequence[ProjectContextCandidate],
) -> dict[str, TemporalBinding]:
    bindings: dict[str, TemporalBinding] = {}
    for candidate in selected:
        for binding in candidate.temporal_bindings:
            existing = bindings.get(binding.key)
            if existing is not None and existing.to_dict() != binding.to_dict():
                raise ValueError(
                    "selected candidates contain conflicting temporal binding definitions"
                )
            bindings[binding.key] = binding
    return bindings


def _validate_compilation_selection(
    compilation: Any,
    selected: tuple[ProjectContextCandidate, ...],
    selected_map: Mapping[str, ProjectContextCandidate],
) -> None:
'''
source = once(source, selection_anchor, selection_helper, "selection temporal helper")
source = once(
    source,
    '''    selected_conflicts = _conflicts(selected_map)
    if selected_conflicts:
        raise ValueError(
            "selected candidates must not contain unresolved conflicts: "
            f"{sorted(selected_conflicts)}"
        )
    has_exact_answer_source = any(
''',
    '''    selected_conflicts = _conflicts(selected_map)
    if selected_conflicts:
        raise ValueError(
            "selected candidates must not contain unresolved conflicts: "
            f"{sorted(selected_conflicts)}"
        )
    selected_bindings = _selected_temporal_binding_map(selected)
    if compilation.selection_receipt.status is SelectionStatus.COMPLETE:
        if compilation.projection is None:
            raise ValueError("COMPLETE selection requires a projection timestamp")
        timestamp_ms = compilation.projection.freshness_timestamp_ms
        expired = sorted(
            key
            for key, binding in selected_bindings.items()
            if binding.expires_at_ms and timestamp_ms >= binding.expires_at_ms
        )
        if expired:
            raise ValueError(
                "selected temporal binding expired at compilation timestamp: "
                f"{expired}"
            )
    has_exact_answer_source = any(
''',
    "selection temporal validation",
)

# 4) Public construction must reproduce all compiler-derived projection fields,
# not merely reference buckets.
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
    "projection reconstruction parity",
)

# 5) Completeness must be proven independently for every requested provenance
# start. Rootless cycles therefore cannot disappear from the root calculation.
prov_anchor = '''

def _provenance_summary(
    node_map: Mapping[str, ProjectContextCandidate],
    incoming: Mapping[str, Sequence[ProjectContextEdge]],
    seen: set[str],
    traversed: set[ProjectContextEdge],
) -> tuple[
'''
prov_helper = '''

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
source = once(source, prov_anchor, prov_helper, "per-start provenance helper")
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
    "per-start completeness calculation",
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
    "source complete predicate",
)
source = once(
    source,
    '    summary = _provenance_summary(node_map, incoming, seen, traversed)\n',
    '    summary = _provenance_summary(starts, node_map, incoming, seen, traversed)\n',
    "provenance summary invocation",
)

# Tests: import dataclasses.replace for forged immutable records.
tests = once(
    tests,
    'from __future__ import annotations\n\nimport json\n',
    'from __future__ import annotations\n\nfrom dataclasses import replace\nimport json\n',
    "test replace import",
)

# Existing expiry test must compile before its binding expires, then observe at expiry.
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
    "expiry test chronology",
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


def test_cross_candidate_temporal_binding_conflict_fails_closed() -> None:
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
    with pytest.raises(ValueError, match="conflicting temporal binding definitions"):
        _compile((source, proof))


def test_compile_rejects_binding_already_expired_at_projection_timestamp() -> None:
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
    with pytest.raises(ValueError, match="expired at compilation timestamp"):
        _compile((source,))


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
    raise SystemExit("six-finding regressions unexpectedly already exist")
tests = tests.rstrip() + regressions + "\n"

# Keep human-readable governance honest during repair.
if "`READY_FOR_HUMAN_REVIEW`" in doc:
    doc = doc.replace("`READY_FOR_HUMAN_REVIEW`", "`IMPLEMENTING`", 1)

temporal_anchor = (
    "Freshness validation compares the complete compiled repository identity and every selected temporal binding against current canonical observations. "
)
temporal_text = (
    temporal_anchor
    + "Every authoritative selected canonical reference is automatically bound to its exact reference digest as a SOURCE_HASH temporal identity, so an empty live-observation map cannot silently bless external source drift. Cross-candidate binding definitions must agree, and a binding already expired at the projection freshness timestamp is rejected before admission. "
)
doc = once(doc, temporal_anchor, temporal_text, "temporal documentation")
prov_doc_anchor = (
    "A trace is `source_complete` only when every retained provenance root is an `EXACT_CURRENT` `SOURCE`, every traversed path edge is `EXACT` or `DERIVED_VERIFIED`, and no predecessor frontier was truncated. "
)
prov_doc_text = (
    "A trace is `source_complete` only when every requested start's complete backward component terminates at `EXACT_CURRENT` `SOURCE` nodes through only `EXACT` or `DERIVED_VERIFIED` edges, no rootless/cyclic component remains unproved, and no predecessor frontier was truncated. "
)
doc = once(doc, prov_doc_anchor, prov_doc_text, "provenance documentation")

SOURCE.write_text(source, encoding="utf-8")
TESTS.write_text(tests, encoding="utf-8")
DOC.write_text(doc, encoding="utf-8")
