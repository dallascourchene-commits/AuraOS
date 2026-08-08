from __future__ import annotations

from dataclasses import replace
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
    ProjectContextCompilation,
    ProjectContextEdge,
    ProjectionBudget,
    ProjectionSelectionReceipt,
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
    origin_ref = reference.canonical_ref if reference is not None else f"canonical://{candidate_id}"
    return ProjectContextCandidate(
        candidate_id=candidate_id,
        category=category,
        source_adapter="adapter.project-context",
        origin_ref=origin_ref,
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
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
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
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    direct_test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    schema = _candidate("schema:direct", CandidateCategory.SCHEMA, D["4"], deps=("source:target",))
    policy = _candidate("policy:scope", CandidateCategory.POLICY, D["5"])
    optional = _candidate("relationship:optional", CandidateCategory.RELATIONSHIP, D["6"], relevance=1_000_000)
    result = _compile((optional, schema, source, policy, direct_test), budget=ProjectionBudget(max_nodes=4, max_edges=8))
    assert result.selection_receipt.status is SelectionStatus.COMPLETE
    assert set(result.selection_receipt.selected) == {"source:target", "test:direct", "schema:direct", "policy:scope"}
    assert result.selection_receipt.omitted_by_budget == ("relationship:optional",)


def test_budget_never_arbitrarily_clips_mandatory_closure() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    direct_test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    schema = _candidate("schema:direct", CandidateCategory.SCHEMA, D["4"], deps=("source:target",))
    result = _compile((source, direct_test, schema), budget=ProjectionBudget(max_nodes=2, max_edges=8))
    assert not result.admissible
    assert result.projection is None
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert set(result.selection_receipt.mandatory_evidence_missing) == {"source:target", "test:direct", "schema:direct", "source:selected"}
    assert result.selection_receipt.selected == ()


def test_missing_source_adapter_for_hard_evidence_yields_incomplete() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    missing_test = _candidate(
        "test:missing", CandidateCategory.TEST, D["3"],
        truth=CandidateTruthClass.UNAVAILABLE,
        authority=ContextAuthorityClass.ADVISORY_NONE,
        availability=CandidateAvailability.SOURCE_ADAPTER_MISSING,
    )
    result = _compile((source, missing_test))
    assert not result.admissible
    assert result.projection is None
    assert result.selection_receipt.source_adapter_missing == ("test:missing",)
    assert result.selection_receipt.mandatory_evidence_missing == ("test:missing",)


def test_stale_answer_determining_source_is_visible_and_not_admitted() -> None:
    stale_source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True,
        truth=CandidateTruthClass.STALE,
        authority=ContextAuthorityClass.ADVISORY_NONE,
        freshness="STALE",
    )
    result = _compile((stale_source,))
    assert not result.admissible
    assert result.selection_receipt.stale == ("source:target",)
    assert set(result.selection_receipt.mandatory_evidence_missing) == {"source:target", "source:selected"}
    assert result.projection is None


def test_incomplete_receipt_never_emits_or_exposes_pr1_projection() -> None:
    direct_test = _candidate("test:direct", CandidateCategory.TEST, D["3"])
    result = _compile((direct_test,))
    assert result.projection is None
    assert result.admissible is False
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert result.selection_receipt.mandatory_evidence_missing == ("source:selected",)
    assert result.headless_projection()["projection"] is None


def test_hand_constructed_incomplete_compilation_cannot_smuggle_projection() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    complete = _compile((source,))
    receipt = ProjectionSelectionReceipt(
        objective_digest=complete.objective_digest,
        repository_identity_digest=complete.repository_identity.identity_digest,
        canonical_owner=complete.selection_receipt.canonical_owner,
        selected=complete.selection_receipt.selected,
        omitted_irrelevant=(), omitted_by_budget=(), stale=(), unavailable=(), conflicting=(), source_adapter_missing=(),
        mandatory_evidence_missing=("source:selected",),
        status=SelectionStatus.INCOMPLETE,
        budget=complete.selection_receipt.budget,
    )
    with pytest.raises(ValueError, match="INCOMPLETE selection must not expose"):
        ProjectContextCompilation(
            project_ref="project:auraos-pr3",
            objective=complete.objective,
            objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity,
            projection=complete.projection,
            selection_receipt=receipt,
            selected_candidates=complete.selected_candidates,
            graph_edges=complete.graph_edges,
            admissible=False,
        )


def test_derived_verified_source_cannot_satisfy_exact_source_admission() -> None:
    derived = _candidate(
        "source:derived", CandidateCategory.SOURCE, D["2"], answer_determining=True,
        truth=CandidateTruthClass.DERIVED_VERIFIED,
        authority=ContextAuthorityClass.DERIVED_READ,
    )
    result = _compile((derived,))
    assert result.selection_receipt.selected == ("source:derived",)
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert result.selection_receipt.mandatory_evidence_missing == ("source:selected",)
    assert result.projection is None
    assert result.admissible is False


def test_optional_conflict_is_preserved_without_collapsing_to_truth() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    d1 = _candidate("decision:left", CandidateCategory.DECISION, D["3"], conflict_key="decision:scope")
    d2 = _candidate("decision:right", CandidateCategory.DECISION, D["4"], conflict_key="decision:scope")
    result = _compile((source, d1, d2))
    assert result.admissible
    assert result.selection_receipt.conflicting == ("decision:left", "decision:right")
    assert "decision:left" not in result.selection_receipt.selected
    assert "decision:right" not in result.selection_receipt.selected


def test_hard_conflict_makes_projection_incomplete() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    p1 = _candidate("policy:left", CandidateCategory.POLICY, D["3"], conflict_key="policy:authority")
    p2 = _candidate("policy:right", CandidateCategory.POLICY, D["4"], conflict_key="policy:authority")
    result = _compile((source, p1, p2))
    assert not result.admissible
    assert result.projection is None
    assert set(result.selection_receipt.conflicting) == {"policy:left", "policy:right"}
    assert set(result.selection_receipt.mandatory_evidence_missing) == {"policy:left", "policy:right"}


def test_headless_projection_never_contains_full_project_graph() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    optional = _candidate("decision:optional", CandidateCategory.DECISION, D["3"], relevance=0)
    result = _compile((source, optional))
    payload = result.headless_projection()
    assert payload["full_project_graph_included"] is False
    assert [node["candidate_id"] for node in payload["nodes"]] == ["source:target"]
    assert result.selection_receipt.omitted_irrelevant == ("decision:optional",)


def test_edge_truth_classes_remain_structurally_distinct() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    edges = (
        ProjectContextEdge("source:target", "test:direct", "verified_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("source:target", "test:direct", "suspected_link", EdgeTruthClass.HYPOTHESIS),
    )
    result = _compile((source, test), edges)
    assert {edge.truth_class for edge in result.graph_edges} == {EdgeTruthClass.EXACT, EdgeTruthClass.HYPOTHESIS}


def test_edge_budget_refuses_silent_graph_clipping() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    edges = (
        ProjectContextEdge("source:target", "test:direct", "verified_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("source:target", "test:direct", "constrains", EdgeTruthClass.EXACT),
    )
    with pytest.raises(ValueError, match="silent edge clipping is prohibited"):
        _compile((source, test), edges, budget=ProjectionBudget(max_nodes=4, max_edges=1))


def test_backward_provenance_is_bounded_and_source_complete_when_limits_allow() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    proof = _candidate("proof:result", CandidateCategory.PROOF_OBLIGATION, D["4"], deps=("test:direct",))
    edges = (
        ProjectContextEdge("source:target", "test:direct", "tested_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("test:direct", "proof:result", "proves", EdgeTruthClass.DERIVED_VERIFIED),
    )
    trace = trace_project_context_provenance(_compile((source, test, proof), edges), ("proof:result",), max_hops=4, max_nodes=8)
    assert trace["source_complete"] is True
    assert trace["bounded"] is True
    assert set(trace["node_ids"]) == {"source:target", "test:direct", "proof:result"}
    assert trace["source_ids"] == ["source:target"]
    assert trace["exact_source_ids"] == ["source:target"]
    assert trace["provenance_root_ids"] == ["source:target"]


def test_derived_source_root_cannot_claim_source_complete() -> None:
    exact = _candidate("source:exact", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    derived = _candidate(
        "source:derived", CandidateCategory.SOURCE, D["3"], required=True,
        truth=CandidateTruthClass.DERIVED_VERIFIED,
        authority=ContextAuthorityClass.DERIVED_READ,
    )
    proof = _candidate("proof:result", CandidateCategory.PROOF_OBLIGATION, D["4"], deps=("source:derived",))
    edge = ProjectContextEdge("source:derived", "proof:result", "supports", EdgeTruthClass.DERIVED_VERIFIED)
    result = _compile((exact, derived, proof), (edge,))
    assert result.admissible is True
    trace = trace_project_context_provenance(result, ("proof:result",))
    assert trace["source_reached"] is True
    assert trace["source_ids"] == ["source:derived"]
    assert trace["exact_source_ids"] == []
    assert trace["authoritative_path"] is True
    assert trace["source_complete"] is False


def test_backward_provenance_reports_truncation_instead_of_hiding_it() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    proof = _candidate("proof:result", CandidateCategory.PROOF_OBLIGATION, D["4"], deps=("test:direct",))
    edges = (
        ProjectContextEdge("source:target", "test:direct", "tested_by", EdgeTruthClass.EXACT),
        ProjectContextEdge("test:direct", "proof:result", "proves", EdgeTruthClass.EXACT),
    )
    trace = trace_project_context_provenance(_compile((source, test, proof), edges), ("proof:result",), max_hops=1, max_nodes=8)
    assert trace["source_complete"] is False
    assert trace["truncated_frontier"]


def test_backward_provenance_requires_every_root_to_reach_source() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    decision = _candidate("decision:root", CandidateCategory.DECISION, D["3"])
    proof = _candidate("proof:result", CandidateCategory.PROOF_OBLIGATION, D["4"])
    edges = (
        ProjectContextEdge("source:target", "proof:result", "supports", EdgeTruthClass.EXACT),
        ProjectContextEdge("decision:root", "proof:result", "constrains", EdgeTruthClass.EXACT),
    )
    trace = trace_project_context_provenance(_compile((source, decision, proof), edges), ("proof:result",), max_hops=4, max_nodes=8)
    assert trace["source_ids"] == ["source:target"]
    assert trace["provenance_root_ids"] == ["decision:root", "source:target"]
    assert trace["source_complete"] is False


def test_changed_answer_determining_source_binding_requires_recompile() -> None:
    binding = TemporalBinding(TemporalBindingKind.SOURCE_HASH, "target-source", D["7"])
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True, bindings=(binding,))
    freshness = validate_project_context_freshness(
        _compile((source,)), current_repository_identity=_repo(), current_bindings={binding.key: D["8"]}, observed_at_ms=1_786_180_000_001
    )
    assert freshness["valid"] is False
    assert freshness["recompile_required"] is True
    assert "binding_changed:SOURCE_HASH:target-source" in freshness["reasons"]
    assert freshness["mutation_performed"] is False


def test_repository_head_change_invalidates_projection() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    freshness = validate_project_context_freshness(
        _compile((source,)), current_repository_identity=_repo(head="c" * 40), current_bindings={}, observed_at_ms=1_786_180_000_001
    )
    assert freshness["valid"] is False
    assert "repository_identity_changed" in freshness["reasons"]


def test_all_temporal_binding_classes_are_explicit_and_expiry_fails_closed() -> None:
    expiry_ms = 1_786_180_000_010
    bindings = tuple(TemporalBinding(kind, f"id-{index}", D[str(index + 2)], expires_at_ms=expiry_ms) for index, kind in enumerate(TemporalBindingKind))
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True, bindings=bindings)
    result = _compile((source,))
    current = {
        item.key: item.digest
        for item in result.selected_candidates[0].temporal_bindings
    }
    freshness = validate_project_context_freshness(result, current_repository_identity=_repo(), current_bindings=current, observed_at_ms=expiry_ms)
    assert freshness["valid"] is False
    assert len([reason for reason in freshness["reasons"] if reason.startswith("binding_expired:")]) == len(bindings)


def test_bounded_reference_cannot_be_upgraded_to_current_projection() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True, freshness="BOUNDED")
    result = _compile((source,))
    assert result.projection is not None
    assert result.projection.freshness_class == "BOUNDED"


def test_memory_lifecycle_and_origin_authority_are_bound_at_candidate_creation() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    payload = source.to_dict()
    assert tuple(payload["memory_lifecycle"]) == MEMORY_LIFECYCLE_PHASES
    assert payload["origin_bound"] is True
    assert payload["authority_non_increasing"] is True
    assert payload["authority_class"] == "CANONICAL_READ"
    assert payload["origin_ref"] == payload["reference"]["canonical_ref"]


def test_authoritative_origin_claim_cannot_be_laundered_onto_reference() -> None:
    ref = _ref("ref:source:target", D["2"])
    with pytest.raises(ValueError, match="origin_ref must equal"):
        ProjectContextCandidate(
            candidate_id="source:target",
            category=CandidateCategory.SOURCE,
            source_adapter="adapter.project-context",
            origin_ref="forged://different-origin",
            authority_class=ContextAuthorityClass.CANONICAL_READ,
            truth_class=CandidateTruthClass.EXACT_CURRENT,
            reference=ref,
            answer_determining=True,
        )


def test_advisory_origin_mismatch_remains_non_authoritative_and_visible() -> None:
    ref = _ref("ref:advisory", D["2"])
    advisory = ProjectContextCandidate(
        candidate_id="relationship:advisory",
        category=CandidateCategory.RELATIONSHIP,
        source_adapter="adapter.project-context",
        origin_ref="summary://unbound-claim",
        authority_class=ContextAuthorityClass.ADVISORY_NONE,
        truth_class=CandidateTruthClass.ADVISORY,
        reference=ref,
    )
    assert advisory.to_dict()["origin_bound"] is False


def test_advisory_or_hypothesis_content_cannot_mint_authority() -> None:
    with pytest.raises(ValueError, match="cannot carry authority"):
        _candidate(
            "hypothesis:one", CandidateCategory.RELATIONSHIP, D["2"],
            truth=CandidateTruthClass.HYPOTHESIS,
            authority=ContextAuthorityClass.CANONICAL_READ,
        )


def test_one_canonical_reference_cannot_be_laundered_into_multiple_roles() -> None:
    ref = _ref("ref:shared", D["2"])
    left = ProjectContextCandidate(
        "source:left", CandidateCategory.SOURCE, "adapter.project-context", ref.canonical_ref,
        ContextAuthorityClass.CANONICAL_READ, CandidateTruthClass.EXACT_CURRENT,
        reference=ref, answer_determining=True,
    )
    right = ProjectContextCandidate(
        "decision:right", CandidateCategory.DECISION, "adapter.project-context", ref.canonical_ref,
        ContextAuthorityClass.CANONICAL_READ, CandidateTruthClass.EXACT_CURRENT,
        reference=ref, relevance_score=10,
    )
    with pytest.raises(ValueError, match="alias one canonical reference"):
        _compile((left, right))


def test_compilation_rejects_cross_field_objective_or_receipt_mismatch() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    result = _compile((source,))
    with pytest.raises(ValueError, match="objective_digest is not bound"):
        ProjectContextCompilation(
            project_ref="project:auraos-pr3",
            objective=result.objective, objective_digest=D["9"], repository_identity=result.repository_identity,
            projection=result.projection, selection_receipt=result.selection_receipt,
            selected_candidates=result.selected_candidates, graph_edges=result.graph_edges, admissible=result.admissible,
        )
    wrong_receipt = ProjectionSelectionReceipt(
        objective_digest=result.objective_digest,
        repository_identity_digest=D["10"],
        canonical_owner=result.selection_receipt.canonical_owner,
        selected=result.selection_receipt.selected,
        omitted_irrelevant=result.selection_receipt.omitted_irrelevant,
        omitted_by_budget=result.selection_receipt.omitted_by_budget,
        stale=result.selection_receipt.stale,
        unavailable=result.selection_receipt.unavailable,
        conflicting=result.selection_receipt.conflicting,
        source_adapter_missing=result.selection_receipt.source_adapter_missing,
        mandatory_evidence_missing=result.selection_receipt.mandatory_evidence_missing,
        status=result.selection_receipt.status,
        budget=result.selection_receipt.budget,
    )
    with pytest.raises(ValueError, match="repository identity is not bound"):
        ProjectContextCompilation(
            project_ref="project:auraos-pr3",
            objective=result.objective, objective_digest=result.objective_digest, repository_identity=result.repository_identity,
            projection=result.projection, selection_receipt=wrong_receipt,
            selected_candidates=result.selected_candidates, graph_edges=result.graph_edges, admissible=result.admissible,
        )


def test_selection_receipt_rejects_selected_omission_overlap() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    receipt = _compile((source,)).selection_receipt
    with pytest.raises(ValueError, match="selected ids as omitted_irrelevant"):
        ProjectionSelectionReceipt(
            objective_digest=receipt.objective_digest,
            repository_identity_digest=receipt.repository_identity_digest,
            canonical_owner=receipt.canonical_owner,
            selected=receipt.selected,
            omitted_irrelevant=receipt.selected,
            omitted_by_budget=(), stale=(), unavailable=(), conflicting=(), source_adapter_missing=(), mandatory_evidence_missing=(),
            status=SelectionStatus.COMPLETE, budget=receipt.budget,
        )


def test_source_first_identity_changes_when_exact_source_changes_but_not_for_advisory_noise() -> None:
    source_a = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    advisory_a = _candidate(
        "relationship:advisory", CandidateCategory.RELATIONSHIP, D["3"],
        truth=CandidateTruthClass.ADVISORY, authority=ContextAuthorityClass.ADVISORY_NONE, relevance=1_000,
    )
    first = _compile((source_a, advisory_a))
    advisory_b = _candidate(
        "relationship:advisory", CandidateCategory.RELATIONSHIP, D["4"],
        truth=CandidateTruthClass.ADVISORY, authority=ContextAuthorityClass.ADVISORY_NONE, relevance=1_000,
    )
    second = _compile((source_a, advisory_b))
    source_b = _candidate("source:target", CandidateCategory.SOURCE, D["5"], answer_determining=True)
    third = _compile((source_b, advisory_b))
    assert first.projection is not None and second.projection is not None and third.projection is not None
    assert first.projection.projection_digest == second.projection.projection_digest
    assert first.projection.projection_digest != third.projection.projection_digest


def test_projection_selection_receipt_schema_is_draft_2020_12_valid_and_accepts_output() -> None:
    schema = json.loads((ROOT / "schemas/aura_projection_selection_receipt_v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    test = _candidate("test:direct", CandidateCategory.TEST, D["3"], deps=("source:target",))
    Draft202012Validator(schema).validate(_compile((source, test)).selection_receipt.to_dict())


def test_duplicate_candidate_ids_and_unknown_edge_endpoints_fail_closed() -> None:
    source = _candidate("source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True)
    with pytest.raises(ValueError, match="duplicate candidate_id"):
        _compile((source, source))
    with pytest.raises(ValueError, match="outside the task-conditioned"):
        _compile((source,), (ProjectContextEdge("source:target", "missing:node", "points_to", EdgeTruthClass.EXACT),))


@pytest.mark.parametrize("bad_conflict_key", [None, 0, False])
def test_conflict_key_rejects_falsy_non_string_values(bad_conflict_key) -> None:
    with pytest.raises(TypeError, match="conflict_key must be a string"):
        _candidate(
            "decision:bad-conflict",
            CandidateCategory.DECISION,
            D["2"],
            conflict_key=bad_conflict_key,
        )


def test_reserved_missing_source_marker_cannot_be_candidate_id() -> None:
    reserved = _candidate(
        "source:selected",
        CandidateCategory.SOURCE,
        D["2"],
        answer_determining=True,
    )
    with pytest.raises(ValueError, match="reserved"):
        _compile((reserved,))


def test_current_binding_normalization_collision_fails_closed() -> None:
    binding = TemporalBinding(TemporalBindingKind.SOURCE_HASH, "target-source", D["7"])
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"],
        answer_determining=True, bindings=(binding,),
    )
    result = _compile((source,))
    with pytest.raises(ValueError, match="duplicate normalized keys"):
        validate_project_context_freshness(
            result, current_repository_identity=_repo(),
            current_bindings={f" {binding.key} ": D["8"], binding.key: binding.digest},
            observed_at_ms=1_786_180_000_001,
        )


def test_provenance_start_ids_must_fit_node_budget() -> None:
    first = _candidate(
        "source:first", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    second = _candidate(
        "source:second", CandidateCategory.SOURCE, D["3"], relevance=100
    )
    result = _compile((first, second))
    with pytest.raises(ValueError, match="start_ids exceed max_nodes"):
        trace_project_context_provenance(
            result, ("source:first", "source:second"), max_nodes=1
        )


def test_unknown_provenance_start_fails_closed() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    result = _compile((source,))
    with pytest.raises(ValueError, match="outside selected context"):
        trace_project_context_provenance(result, ("source:missing",))


def test_selection_receipt_digest_rejects_tamper_and_recomputes_when_blank() -> None:
    source = _candidate(
        "source:target", CandidateCategory.SOURCE, D["2"], answer_determining=True
    )
    receipt = _compile((source,)).selection_receipt
    kwargs = dict(
        objective_digest=receipt.objective_digest,
        repository_identity_digest=receipt.repository_identity_digest,
        canonical_owner=receipt.canonical_owner, selected=receipt.selected,
        omitted_irrelevant=receipt.omitted_irrelevant,
        omitted_by_budget=receipt.omitted_by_budget, stale=receipt.stale,
        unavailable=receipt.unavailable, conflicting=receipt.conflicting,
        source_adapter_missing=receipt.source_adapter_missing,
        mandatory_evidence_missing=receipt.mandatory_evidence_missing,
        status=receipt.status, budget=receipt.budget,
    )
    with pytest.raises(ValueError, match="receipt digest mismatch"):
        ProjectionSelectionReceipt(**kwargs, receipt_digest="0" * 64)
    recomputed = ProjectionSelectionReceipt(**kwargs, receipt_digest="")
    assert recomputed.receipt_digest == receipt.receipt_digest


def test_compile_rejects_non_exact_projection_budget() -> None:
    source = _candidate(
        "source:target",
        CandidateCategory.SOURCE,
        D["2"],
        answer_determining=True,
    )

    class DerivedBudget(ProjectionBudget):
        pass

    with pytest.raises(ValueError, match="budget must be exact ProjectionBudget"):
        _compile((source,), budget=DerivedBudget())


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
            project_ref="project:auraos-pr3",
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
            project_ref="project:auraos-pr3",
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
            project_ref="project:auraos-pr3",
            objective=result.objective,
            objective_digest=result.objective_digest,
            repository_identity=result.repository_identity,
            projection=forged,
            selection_receipt=result.selection_receipt,
            selected_candidates=result.selected_candidates,
            graph_edges=result.graph_edges,
            admissible=result.admissible,
        )


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

def test_derived_verified_candidate_cannot_claim_canonical_read_authority() -> None:
    with pytest.raises(ValueError, match="authority class does not match"):
        _candidate(
            "decision:derived-escalation",
            CandidateCategory.DECISION,
            D["8"],
            truth=CandidateTruthClass.DERIVED_VERIFIED,
            authority=ContextAuthorityClass.CANONICAL_READ,
        )


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
