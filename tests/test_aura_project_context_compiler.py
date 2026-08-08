from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from aura_ephemeral_workspace_contracts import CanonicalReference, RepositoryIdentity
from aura_project_context_compiler import (
    CandidateAvailability,
    CandidateCategory,
    CandidateTruthClass,
    ContextAuthorityClass,
    EdgeTruthClass,
    MEMORY_LIFECYCLE_PHASES,
    ProjectContextCandidate,
    ProjectContextEdge,
    ProjectionBudget,
    SelectionStatus,
    TemporalBinding,
    TemporalBindingKind,
    compile_project_context_projection,
    trace_project_context_provenance,
    validate_project_context_freshness,
)

ROOT = Path(__file__).resolve().parents[1]
D = {str(i): f"{i:x}" * 64 for i in range(1, 16)}
HEAD = "a" * 40


def _repo(*, head: str = HEAD, tree: str = D["1"]) -> RepositoryIdentity:
    return RepositoryIdentity(
        "dallascourchene-commits/AuraOS",
        "refs/heads/main",
        head,
        tree,
    )


def _ref(name: str, digest: str, *, freshness: str = "CURRENT") -> CanonicalReference:
    return CanonicalReference(
        name,
        "canonical.owner",
        f"owner://{name}",
        digest,
        truth_class="EXACT",
        freshness_class=freshness,
        metadata={},
    )


def _candidate(
    candidate_id: str,
    category: CandidateCategory,
    digest: str,
    *,
    relevance: int = 100,
    required: bool = False,
    answer_determining: bool = False,
    deps: tuple[str, ...] = (),
    truth: CandidateTruthClass = CandidateTruthClass.EXACT_CURRENT,
    authority: ContextAuthorityClass = ContextAuthorityClass.CANONICAL_READ,
    availability: CandidateAvailability = CandidateAvailability.AVAILABLE,
    conflict_key: str = "",
    freshness: str = "CURRENT",
    bindings: tuple[TemporalBinding, ...] = (),
) -> ProjectContextCandidate:
    reference = None
    if availability is CandidateAvailability.AVAILABLE:
        reference = _ref(f"ref:{candidate_id}", digest, freshness=freshness)
    return ProjectContextCandidate(
        candidate_id=candidate_id,
        category=category,
        source_adapter="adapter.project-context",
        origin_ref=f"canonical://{candidate_id}",
        authority_class=authority,
        truth_class=truth,
        availability=availability,
        reference=reference,
        relevance_score=relevance,
        required=required,
        answer_determining=answer_determining,
        dependency_ids=deps,
        conflict_key=conflict_key,
        temporal_bindings=bindings,
    )


def _compile(candidates, edges=(), *, budget: ProjectionBudget | None = None):
    return compile_project_context_projection(
        "Fix the exact behavior without losing proof context.",
        project_ref="project:auraos-pr3",
        repository_identity=_repo(),
        candidates=tuple(candidates),
        edges=tuple(edges),
        budget=budget or ProjectionBudget(max_nodes=64, max_edges=256),
        freshness_timestamp_ms=1_786_180_000_000,
    )


def test_same_objective_and_exact_sources_are_deterministic_across_input_order() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    decision = _candidate("decision:accepted", CandidateCategory.DECISION, D["4"], relevance=80)
    edges = (
        ProjectContextEdge("source:target", "test:direct", "verified_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("decision:accepted", "source:target", "constrains", EdgeTruthClass.EXACT),
    )
    left = _compile((source, test, decision), edges)
    right = _compile((decision, source, test), tuple(reversed(edges)))

    assert left.admissible and right.admissible
    assert left.compilation_digest == right.compilation_digest
    assert left.selection_receipt.receipt_digest == right.selection_receipt.receipt_digest
    assert left.projection is not None and right.projection is not None
    assert left.projection.projection_digest == right.projection.projection_digest


def test_hard_inclusion_survives_optional_context_pressure() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    direct_test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    schema = _candidate("schema:direct", CandidateCategory.SCHEMA, D["4"], deps=("source:target",))
    policy = _candidate("policy:scope", CandidateCategory.POLICY, D["5"])
    optional = _candidate("relationship:optional", CandidateCategory.RELATIONSHIP, D["6"], relevance=1_000_000)

    result = _compile(
        (optional, schema, source, policy, direct_test),
        budget=ProjectionBudget(max_nodes=4, max_edges=8),
    )

    assert result.selection_receipt.status is SelectionStatus.COMPLETE
    assert set(result.selection_receipt.selected) == {
        "source:target", "test:direct", "schema:direct", "policy:scope"
    }
    assert result.selection_receipt.omitted_by_budget == ("relationship:optional",)


def test_budget_never_arbitrarily_clips_mandatory_closure() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    direct_test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    schema = _candidate("schema:direct", CandidateCategory.SCHEMA, D["4"], deps=("source:target",))

    result = _compile(
        (source, direct_test, schema), budget=ProjectionBudget(max_nodes=2, max_edges=8)
    )

    assert not result.admissible
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert set(result.selection_receipt.mandatory_evidence_missing) == {
        "source:target", "test:direct", "schema:direct"
    }
    assert result.selection_receipt.selected == ()


def test_missing_source_adapter_for_hard_evidence_yields_incomplete() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    missing_test = _candidate(
        "test:missing",
        CandidateCategory.TEST,
        D["3"],
        truth=CandidateTruthClass.UNAVAILABLE,
        authority=ContextAuthorityClass.ADVISORY_NONE,
        availability=CandidateAvailability.SOURCE_ADAPTER_MISSING,
    )

    result = _compile((source, missing_test))

    assert not result.admissible
    assert result.selection_receipt.source_adapter_missing == ("test:missing",)
    assert result.selection_receipt.mandatory_evidence_missing == ("test:missing",)


def test_stale_answer_determining_source_is_visible_and_not_admitted() -> None:
    stale_source = _candidate(
        "source:target",
        CandidateCategory.SOURCE,
        D["2"],
        answer_determining=True,
        truth=CandidateTruthClass.STALE,
        authority=ContextAuthorityClass.ADVISORY_NONE,
        freshness="STALE",
    )
    result = _compile((stale_source,))

    assert not result.admissible
    assert result.selection_receipt.stale == ("source:target",)
    assert result.selection_receipt.mandatory_evidence_missing == ("source:target",)
    assert result.projection is None


def test_optional_conflict_is_preserved_without_collapsing_to_truth() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    d1 = _candidate(
        "decision:left", CandidateCategory.DECISION, D["3"], conflict_key="decision:scope"
    )
    d2 = _candidate(
        "decision:right", CandidateCategory.DECISION, D["4"], conflict_key="decision:scope"
    )

    result = _compile((source, d1, d2))

    assert result.admissible
    assert result.selection_receipt.conflicting == ("decision:left", "decision:right")
    assert "decision:left" not in result.selection_receipt.selected
    assert "decision:right" not in result.selection_receipt.selected


def test_hard_conflict_makes_projection_incomplete() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    p1 = _candidate(
        "policy:left", CandidateCategory.POLICY, D["3"], conflict_key="policy:authority"
    )
    p2 = _candidate(
        "policy:right", CandidateCategory.POLICY, D["4"], conflict_key="policy:authority"
    )

    result = _compile((source, p1, p2))

    assert not result.admissible
    assert set(result.selection_receipt.conflicting) == {"policy:left", "policy:right"}
    assert set(result.selection_receipt.mandatory_evidence_missing) == {"policy:left", "policy:right"}


def test_headless_projection_never_contains_full_project_graph() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    optional = _candidate("decision:optional", CandidateCategory.DECISION, D["3"], relevance=0)
    result = _compile((source, optional))

    payload = result.headless_projection()
    assert payload["full_project_graph_included"] is False
    assert [node["candidate_id"] for node in payload["nodes"]] == ["source:target"]
    assert result.selection_receipt.omitted_irrelevant == ("decision:optional",)


def test_edge_truth_classes_remain_structurally_distinct() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    edges = (
        ProjectContextEdge("source:target", "test:direct", "verified_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("source:target", "test:direct", "suspected_link", EdgeTruthClass.HYPOTHESIS),
    )
    result = _compile((source, test), edges)

    classes = {edge.truth_class for edge in result.graph_edges}
    assert classes == {EdgeTruthClass.EXACT, EdgeTruthClass.HYPOTHESIS}


def test_backward_provenance_is_bounded_and_source_complete_when_limits_allow() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    proof = _candidate("proof:result", CandidateCategory.PROOF_OBLIGATION, D["4"], deps=("test:direct",))
    edges = (
        ProjectContextEdge("source:target", "test:direct", "tested_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("test:direct", "proof:result", "proves", EdgeTruthClass.DERIVED_VERIFIED),
    )
    result = _compile((source, test, proof), edges)

    trace = trace_project_context_provenance(result, ("proof:result",), max_hops=4, max_nodes=8)
    assert trace["source_complete"] is True
    assert trace["bounded"] is True
    assert set(trace["node_ids"]) == {"source:target", "test:direct", "proof:result"}
    assert trace["source_ids"] == ["source:target"]


def test_backward_provenance_reports_truncation_instead_of_hiding_it() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    proof = _candidate("proof:result", CandidateCategory.PROOF_OBLIGATION, D["4"], deps=("test:direct",))
    edges = (
        ProjectContextEdge("source:target", "test:direct", "tested_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("test:direct", "proof:result", "proves", EdgeTruthClass.EXACT),
    )
    result = _compile((source, test, proof), edges)

    trace = trace_project_context_provenance(result, ("proof:result",), max_hops=1, max_nodes=8)
    assert trace["source_complete"] is False
    assert trace["truncated_frontier"]


def test_changed_answer_determining_source_binding_requires_recompile() -> None:
    binding = TemporalBinding(TemporalBindingKind.SOURCE_HASH, "target-source", D["7"])
    source = _candidate(
        "source:target",
        CandidateCategory.SOURCE,
        D["2"],
        answer_determining=True,
        bindings=(binding,),
    )
    result = _compile((source,))

    freshness = validate_project_context_freshness(
        result,
        current_repository_identity=_repo(),
        current_bindings={binding.key: D["8"]},
        observed_at_ms=1_786_180_000_001,
    )
    assert freshness["valid"] is False
    assert freshness["recompile_required"] is True
    assert "binding_changed:SOURCE_HASH:target-source" in freshness["reasons"]
    assert freshness["mutation_performed"] is False


def test_repository_head_change_invalidates_projection() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    result = _compile((source,))
    freshness = validate_project_context_freshness(
        result,
        current_repository_identity=_repo(head="c" * 40),
        current_bindings={},
        observed_at_ms=1_786_180_000_001,
    )
    assert freshness["valid"] is False
    assert "repository_identity_changed" in freshness["reasons"]


def test_all_temporal_binding_classes_are_explicit_and_expiry_fails_closed() -> None:
    bindings = tuple(
        TemporalBinding(kind, f"id-{index}", D[str(index + 2)], expires_at_ms=2_000)
        for index, kind in enumerate(TemporalBindingKind)
    )
    source = _candidate(
        "source:target",
        CandidateCategory.SOURCE,
        D["2"],
        answer_determining=True,
        bindings=bindings,
    )
    result = _compile((source,))
    current = {item.key: item.digest for item in bindings}

    freshness = validate_project_context_freshness(
        result,
        current_repository_identity=_repo(),
        current_bindings=current,
        observed_at_ms=2_000,
    )
    assert freshness["valid"] is False
    assert len([reason for reason in freshness["reasons"] if reason.startswith("binding_expired:")]) == len(bindings)


def test_memory_lifecycle_and_origin_authority_are_bound_at_candidate_creation() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    payload = source.to_dict()
    assert tuple(payload["memory_lifecycle"]) == MEMORY_LIFECYCLE_PHASES
    assert payload["origin_bound"] is True
    assert payload["authority_non_increasing"] is True
    assert payload["authority_class"] == "CANONICAL_READ"


def test_advisory_or_hypothesis_content_cannot_mint_authority() -> None:
    with pytest.raises(ValueError, match="cannot carry authority"):
        _candidate(
            "hypothesis:one",
            CandidateCategory.RELATIONSHIP,
            D["2"],
            truth=CandidateTruthClass.HYPOTHESIS,
            authority=ContextAuthorityClass.CANONICAL_READ,
        )


def test_one_canonical_reference_cannot_be_laundered_into_multiple_roles() -> None:
    ref = _ref("ref:shared", D["2"])
    left = ProjectContextCandidate(
        "source:left", CandidateCategory.SOURCE, "adapter.project-context", "canonical://left",
        ContextAuthorityClass.CANONICAL_READ, CandidateTruthClass.EXACT_CURRENT,
        reference=ref, answer_determining=True,
    )
    right = ProjectContextCandidate(
        "decision:right", CandidateCategory.DECISION, "adapter.project-context", "canonical://right",
        ContextAuthorityClass.CANONICAL_READ, CandidateTruthClass.EXACT_CURRENT,
        reference=ref, relevance_score=10,
    )
    with pytest.raises(ValueError, match="alias one canonical reference"):
        _compile((left, right))


def test_source_first_identity_changes_when_exact_source_changes_but_not_for_advisory_noise() -> None:
    source_a = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    advisory_a = _candidate(
        "relationship:advisory",
        CandidateCategory.RELATIONSHIP,
        D["3"],
        truth=CandidateTruthClass.ADVISORY,
        authority=ContextAuthorityClass.ADVISORY_NONE,
        relevance=1_000,
    )
    first = _compile((source_a, advisory_a))

    advisory_b = _candidate(
        "relationship:advisory",
        CandidateCategory.RELATIONSHIP,
        D["4"],
        truth=CandidateTruthClass.ADVISORY,
        authority=ContextAuthorityClass.ADVISORY_NONE,
        relevance=1_000,
    )
    second = _compile((source_a, advisory_b))
    source_b = _candidate(
        "source:target", CandidateCategory.SOURCE, D["5"], answer_determining=True
    )
    third = _compile((source_b, advisory_b))

    assert first.projection is not None and second.projection is not None and third.projection is not None
    assert first.projection.projection_digest == second.projection.projection_digest
    assert first.projection.projection_digest != third.projection.projection_digest


def test_projection_selection_receipt_schema_is_draft_2020_12_valid_and_accepts_output() -> None:
    schema = json.loads(
        (ROOT / "schemas/aura_projection_selection_receipt_v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    result = _compile((source, test))
    Draft202012Validator(schema).validate(result.selection_receipt.to_dict())


def test_duplicate_candidate_ids_and_unknown_edge_endpoints_fail_closed() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    with pytest.raises(ValueError, match="duplicate candidate_id"):
        _compile((source, source))
    with pytest.raises(ValueError, match="outside the task-conditioned"):
        _compile(
            (source,),
            (ProjectContextEdge("source:target", "missing:node", "points_to", EdgeTruthClass.EXACT),),
        )
