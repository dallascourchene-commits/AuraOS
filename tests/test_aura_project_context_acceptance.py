from __future__ import annotations

from dataclasses import replace

import pytest

from aura_ephemeral_workspace_contracts import CanonicalReference, RepositoryIdentity
from aura_project_context_compiler import (
    CandidateAvailability,
    CandidateCategory,
    CandidateTruthClass,
    ContextAuthorityClass,
    EdgeTruthClass,
    ProjectContextCandidate,
    ProjectContextCompilation,
    ProjectContextEdge,
    ProjectionBudget,
    ProjectionSelectionReceipt,
    SelectionStatus,
    compile_project_context_projection,
    trace_project_context_provenance,
)


OBJECTIVE = "Correct the project conclusion from exact answer-determining source."
PROJECT_REF = "project:auraos-pr3-acceptance"
NOW_MS = 1_786_180_000_000


def _digest(char: str) -> str:
    return char * 64


def _repo() -> RepositoryIdentity:
    return RepositoryIdentity(
        "dallascourchene-commits/AuraOS",
        "refs/heads/main",
        "a" * 40,
        _digest("1"),
    )


def _ref(reference_id: str, digest: str) -> CanonicalReference:
    return CanonicalReference(
        reference_id,
        "canonical.owner",
        f"owner://{reference_id}",
        digest,
        truth_class="EXACT",
        freshness_class="CURRENT",
        metadata={},
    )


def _source(digest: str = _digest("2")) -> ProjectContextCandidate:
    reference = _ref("ref:source-answer", digest)
    return ProjectContextCandidate(
        candidate_id="source:answer-determining",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.source",
        origin_ref=reference.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=reference,
        relevance_score=100,
        answer_determining=True,
    )


def _compile(
    candidates: tuple[ProjectContextCandidate, ...],
    edges: tuple[ProjectContextEdge, ...] = (),
):
    return compile_project_context_projection(
        OBJECTIVE,
        project_ref=PROJECT_REF,
        repository_identity=_repo(),
        candidates=candidates,
        edges=edges,
        budget=ProjectionBudget(max_nodes=16, max_edges=32),
        freshness_timestamp_ms=NOW_MS,
    )


def test_source_first_fixture_corrects_conclusion_only_failure() -> None:
    """A conclusion-only retrieval can be wrong; exact source must win admission."""
    wrong_summary = ProjectContextCandidate(
        candidate_id="relationship:wrong-summary",
        category=CandidateCategory.RELATIONSHIP,
        source_adapter="adapter.summary",
        origin_ref="summary://conclusion-says-legacy-behavior",
        authority_class=ContextAuthorityClass.ADVISORY_NONE,
        truth_class=CandidateTruthClass.ADVISORY,
        reference=_ref("ref:wrong-summary", _digest("3")),
        relevance_score=1_000_000,
    )
    exact_source = _source()

    result = _compile((wrong_summary, exact_source))

    assert result.admissible is True
    assert result.selection_receipt.status is SelectionStatus.COMPLETE
    assert result.selection_receipt.selected == ("source:answer-determining",)
    assert result.selection_receipt.omitted_irrelevant == (
        "relationship:wrong-summary",
    )
    assert result.projection is not None
    assert result.projection.artifact_evidence_refs[0].reference_id == "ref:source-answer"
    assert result.projection.artifact_evidence_refs[0].digest == _digest("2")


def test_incomplete_fixture_never_exposes_canonical_projection() -> None:
    test_ref = _ref("ref:test-only", _digest("6"))
    direct_test = ProjectContextCandidate(
        candidate_id="test:only",
        category=CandidateCategory.TEST,
        source_adapter="adapter.test",
        origin_ref=test_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=test_ref,
    )

    result = _compile((direct_test,))

    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert result.admissible is False
    assert result.projection is None
    assert result.headless_projection()["projection"] is None


def test_derived_source_support_cannot_impersonate_exact_source() -> None:
    derived_ref = _ref("ref:derived-source", _digest("8"))
    derived_source = ProjectContextCandidate(
        candidate_id="source:derived",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.derived",
        origin_ref=derived_ref.canonical_ref,
        authority_class=ContextAuthorityClass.DERIVED_READ,
        truth_class=CandidateTruthClass.DERIVED_VERIFIED,
        reference=derived_ref,
        answer_determining=True,
    )

    result = _compile((derived_source,))

    assert result.selection_receipt.selected == ("source:derived",)
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert result.selection_receipt.mandatory_evidence_missing == ("source:selected",)
    assert result.projection is None
    assert result.admissible is False


def test_unrelated_exact_source_cannot_launder_derived_answer_source_into_complete() -> None:
    derived_ref = _ref("ref:derived-answer", _digest("8"))
    derived_answer = ProjectContextCandidate(
        candidate_id="source:derived-answer",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.derived",
        origin_ref=derived_ref.canonical_ref,
        authority_class=ContextAuthorityClass.DERIVED_READ,
        truth_class=CandidateTruthClass.DERIVED_VERIFIED,
        reference=derived_ref,
        relevance_score=100,
        answer_determining=True,
    )
    unrelated_ref = _ref("ref:unrelated-exact", _digest("a"))
    unrelated_exact = ProjectContextCandidate(
        candidate_id="source:unrelated-exact",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.source",
        origin_ref=unrelated_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=unrelated_ref,
        relevance_score=1_000,
        answer_determining=False,
    )

    result = _compile((derived_answer, unrelated_exact))

    assert set(result.selection_receipt.selected) == {
        "source:derived-answer",
        "source:unrelated-exact",
    }
    assert result.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert result.selection_receipt.mandatory_evidence_missing == ("source:selected",)
    assert result.projection is None
    assert result.admissible is False


def test_public_compilation_reproves_exact_answer_source_anchor() -> None:
    complete = _compile((_source(),))
    assert complete.projection is not None
    original = complete.selected_candidates[0]
    derived_semantics = ProjectContextCandidate(
        candidate_id=original.candidate_id,
        category=CandidateCategory.SOURCE,
        source_adapter=original.source_adapter,
        origin_ref=original.origin_ref,
        authority_class=ContextAuthorityClass.DERIVED_READ,
        truth_class=CandidateTruthClass.DERIVED_VERIFIED,
        reference=original.reference,
        relevance_score=original.relevance_score,
        answer_determining=True,
    )

    with pytest.raises(
        ValueError,
        match="COMPLETE selection requires an exact-current answer-determining source",
    ):
        ProjectContextCompilation(
            project_ref=PROJECT_REF,
            objective=complete.objective,
            objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity,
            projection=complete.projection,
            selection_receipt=complete.selection_receipt,
            selected_candidates=(derived_semantics,),
            graph_edges=complete.graph_edges,
            admissible=True,
        )


def test_public_compilation_rejects_advisory_projection_smuggling() -> None:
    complete = _compile((_source(),))
    assert complete.projection is not None
    source = complete.selected_candidates[0]
    advisory_ref = _ref("ref:advisory-smuggled", _digest("d"))
    advisory = ProjectContextCandidate(
        candidate_id="relationship:advisory-smuggled",
        category=CandidateCategory.RELATIONSHIP,
        source_adapter="adapter.summary",
        origin_ref="summary://advisory-smuggled",
        authority_class=ContextAuthorityClass.ADVISORY_NONE,
        truth_class=CandidateTruthClass.ADVISORY,
        reference=advisory_ref,
        relevance_score=1_000_000,
    )
    forged_receipt = ProjectionSelectionReceipt(
        objective_digest=complete.objective_digest,
        repository_identity_digest=complete.repository_identity.identity_digest,
        canonical_owner=complete.selection_receipt.canonical_owner,
        selected=(source.candidate_id, advisory.candidate_id),
        omitted_irrelevant=(),
        omitted_by_budget=(),
        stale=(),
        unavailable=(),
        conflicting=(),
        source_adapter_missing=(),
        mandatory_evidence_missing=(),
        status=SelectionStatus.COMPLETE,
        budget=complete.selection_receipt.budget,
    )
    forged_projection = replace(
        complete.projection,
        relationship_refs=(advisory_ref,),
        projection_digest="",
    )

    with pytest.raises(ValueError, match="selected candidates must remain compiler-eligible"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF,
            objective=complete.objective,
            objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity,
            projection=forged_projection,
            selection_receipt=forged_receipt,
            selected_candidates=(source, advisory),
            graph_edges=(),
            admissible=True,
        )


def test_authoritative_origin_is_reference_bound() -> None:
    reference = _ref("ref:bound-source", _digest("9"))
    with pytest.raises(ValueError, match="origin_ref must equal"):
        ProjectContextCandidate(
            candidate_id="source:forged-origin",
            category=CandidateCategory.SOURCE,
            source_adapter="adapter.source",
            origin_ref="source://forged-origin",
            authority_class=ContextAuthorityClass.CANONICAL_READ,
            truth_class=CandidateTruthClass.EXACT_CURRENT,
            reference=reference,
            answer_determining=True,
        )


def test_authority_non_increasing_is_computed_from_truth_and_authority() -> None:
    exact = _source()
    derived_ref = _ref("ref:derived-authority", _digest("b"))
    derived = ProjectContextCandidate(
        candidate_id="source:derived-authority",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.derived",
        origin_ref=derived_ref.canonical_ref,
        authority_class=ContextAuthorityClass.DERIVED_READ,
        truth_class=CandidateTruthClass.DERIVED_VERIFIED,
        reference=derived_ref,
    )
    advisory = ProjectContextCandidate(
        candidate_id="relationship:advisory-authority",
        category=CandidateCategory.RELATIONSHIP,
        source_adapter="adapter.summary",
        origin_ref="summary://advisory-authority",
        authority_class=ContextAuthorityClass.ADVISORY_NONE,
        truth_class=CandidateTruthClass.ADVISORY,
        reference=_ref("ref:advisory-authority", _digest("c")),
    )

    assert exact.authority_non_increasing is True
    assert derived.authority_non_increasing is True
    assert advisory.authority_non_increasing is True
    assert exact.to_dict()["authority_non_increasing"] is exact.authority_non_increasing
    assert derived.to_dict()["authority_non_increasing"] is derived.authority_non_increasing
    assert advisory.to_dict()["authority_non_increasing"] is advisory.authority_non_increasing


def test_shadow_ranker_disagreement_is_visible_and_non_authoritative() -> None:
    """A shadow VSA/HDC-style preference may disagree but cannot change selection."""
    exact_source = _source()
    shadow_preference = ProjectContextCandidate(
        candidate_id="relationship:shadow-ranker-prefers-summary",
        category=CandidateCategory.RELATIONSHIP,
        source_adapter="adapter.shadow-vsa",
        origin_ref="shadow-vsa://prefers:relationship:wrong-summary",
        authority_class=ContextAuthorityClass.ADVISORY_NONE,
        truth_class=CandidateTruthClass.ADVISORY,
        reference=_ref("ref:shadow-ranker-disagreement", _digest("4")),
        relevance_score=1_000_000,
    )

    result = _compile((shadow_preference, exact_source))

    assert result.selection_receipt.selected == ("source:answer-determining",)
    assert result.selection_receipt.omitted_irrelevant == (
        "relationship:shadow-ranker-prefers-summary",
    )
    visible = result.headless_projection()["selection_receipt"]
    assert "relationship:shadow-ranker-prefers-summary" in visible["omitted_irrelevant"]
    assert "relationship:shadow-ranker-prefers-summary" not in visible["selected"]
    assert result.selected_candidates[0].authority_class is ContextAuthorityClass.CANONICAL_READ


def test_memory_revision_revocation_and_rollback_remain_reconstructable() -> None:
    """Immutable compilations preserve revision lineage without a mutable project DB."""
    previous_source = _source(_digest("2"))
    previous = _compile((previous_source,))

    revised_source = _source(_digest("5"))
    revised = _compile((revised_source,))

    assert previous.compilation_digest != revised.compilation_digest
    assert previous.projection is not None and revised.projection is not None
    assert previous.projection.projection_digest != revised.projection.projection_digest
    assert previous.projection.artifact_evidence_refs[0].digest == _digest("2")
    assert revised.projection.artifact_evidence_refs[0].digest == _digest("5")

    revoked_source = ProjectContextCandidate(
        candidate_id="source:answer-determining",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.source",
        origin_ref="source://module.py:answer",
        authority_class=ContextAuthorityClass.ADVISORY_NONE,
        truth_class=CandidateTruthClass.UNAVAILABLE,
        availability=CandidateAvailability.UNAVAILABLE,
        reference=None,
        relevance_score=100,
        answer_determining=True,
    )
    revoked = _compile((revoked_source,))
    assert revoked.admissible is False
    assert revoked.projection is None
    assert revoked.selection_receipt.status is SelectionStatus.INCOMPLETE
    assert "source:answer-determining" in revoked.selection_receipt.unavailable
    assert "source:answer-determining" in revoked.selection_receipt.mandatory_evidence_missing

    rollback = _compile((previous_source,))
    assert rollback.compilation_digest == previous.compilation_digest
    assert rollback.projection is not None
    assert rollback.projection.projection_digest == previous.projection.projection_digest


def test_headless_accessible_projection_retains_exact_reference_identity() -> None:
    result = _compile((_source(),))
    payload = result.headless_projection()

    assert payload["full_project_graph_included"] is False
    assert payload["projection"]["artifact_evidence_refs"][0]["reference_id"] == "ref:source-answer"
    assert payload["projection"]["artifact_evidence_refs"][0]["digest"] == _digest("2")


def test_bounded_provenance_does_not_emit_dangling_truncated_edges() -> None:
    source = _source()
    test_ref = _ref("ref:test-direct", _digest("6"))
    test = ProjectContextCandidate(
        candidate_id="test:direct",
        category=CandidateCategory.TEST,
        source_adapter="adapter.test",
        origin_ref=test_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=test_ref,
        dependency_ids=("source:answer-determining",),
    )
    proof_ref = _ref("ref:proof-result", _digest("7"))
    proof = ProjectContextCandidate(
        candidate_id="proof:result",
        category=CandidateCategory.PROOF_OBLIGATION,
        source_adapter="adapter.proof",
        origin_ref=proof_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=proof_ref,
        dependency_ids=("test:direct",),
    )
    edges = (
        ProjectContextEdge(
            "source:answer-determining",
            "test:direct",
            "tested_by",
            EdgeTruthClass.EXACT,
        ),
        ProjectContextEdge(
            "test:direct",
            "proof:result",
            "proves",
            EdgeTruthClass.EXACT,
        ),
    )
    result = _compile((source, test, proof), edges)

    trace = trace_project_context_provenance(
        result,
        ("proof:result",),
        max_hops=4,
        max_nodes=2,
    )

    node_ids = set(trace["node_ids"])
    assert trace["source_complete"] is False
    assert trace["truncated_frontier"] == ["source:answer-determining"]
    assert all(
        edge["source_id"] in node_ids and edge["target_id"] in node_ids
        for edge in trace["edges"]
    )


def test_hypothesis_edge_can_reach_source_without_claiming_source_complete() -> None:
    source = _source()
    proof_ref = _ref("ref:proof-result", _digest("7"))
    proof = ProjectContextCandidate(
        candidate_id="proof:result",
        category=CandidateCategory.PROOF_OBLIGATION,
        source_adapter="adapter.proof",
        origin_ref=proof_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=proof_ref,
        dependency_ids=("source:answer-determining",),
    )
    result = _compile(
        (source, proof),
        (
            ProjectContextEdge(
                "source:answer-determining",
                "proof:result",
                "suspected_support",
                EdgeTruthClass.HYPOTHESIS,
            ),
        ),
    )

    trace = trace_project_context_provenance(result, ("proof:result",))

    assert trace["source_reached"] is True
    assert trace["authoritative_path"] is False
    assert trace["source_complete"] is False


def test_derived_source_root_is_not_source_complete_even_on_verified_edge() -> None:
    exact_source = _source()
    derived_ref = _ref("ref:derived-root", _digest("8"))
    derived_source = ProjectContextCandidate(
        candidate_id="source:derived-root",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.derived",
        origin_ref=derived_ref.canonical_ref,
        authority_class=ContextAuthorityClass.DERIVED_READ,
        truth_class=CandidateTruthClass.DERIVED_VERIFIED,
        reference=derived_ref,
        required=True,
    )
    proof_ref = _ref("ref:derived-proof", _digest("9"))
    proof = ProjectContextCandidate(
        candidate_id="proof:derived",
        category=CandidateCategory.PROOF_OBLIGATION,
        source_adapter="adapter.proof",
        origin_ref=proof_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=proof_ref,
        dependency_ids=("source:derived-root",),
    )
    result = _compile(
        (exact_source, derived_source, proof),
        (
            ProjectContextEdge(
                "source:derived-root",
                "proof:derived",
                "supports",
                EdgeTruthClass.DERIVED_VERIFIED,
            ),
        ),
    )

    assert result.admissible is True
    trace = trace_project_context_provenance(result, ("proof:derived",))
    assert trace["source_reached"] is True
    assert trace["exact_source_ids"] == []
    assert trace["authoritative_path"] is True
    assert trace["source_complete"] is False


def test_public_compilation_rejects_incomplete_dependency_closure() -> None:
    complete = _compile((_source(),))
    assert complete.projection is not None
    source = complete.selected_candidates[0]
    proof_ref = _ref("ref:dependency-proof", _digest("e"))
    proof = ProjectContextCandidate(
        candidate_id="proof:dependency-gap",
        category=CandidateCategory.PROOF_OBLIGATION,
        source_adapter="adapter.proof",
        origin_ref=proof_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=proof_ref,
        dependency_ids=("test:missing",),
    )
    forged_receipt = ProjectionSelectionReceipt(
        objective_digest=complete.objective_digest,
        repository_identity_digest=complete.repository_identity.identity_digest,
        canonical_owner=complete.selection_receipt.canonical_owner,
        selected=(source.candidate_id, proof.candidate_id),
        omitted_irrelevant=(), omitted_by_budget=(), stale=(), unavailable=(),
        conflicting=(), source_adapter_missing=(), mandatory_evidence_missing=(),
        status=SelectionStatus.COMPLETE, budget=complete.selection_receipt.budget,
    )
    forged_projection = replace(
        complete.projection,
        artifact_evidence_refs=(source.reference, proof_ref),
        projection_digest="",
    )
    with pytest.raises(ValueError, match="dependency closure is incomplete"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF,
            objective=complete.objective, objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity, projection=forged_projection,
            selection_receipt=forged_receipt, selected_candidates=(source, proof),
            graph_edges=(), admissible=True,
        )


def test_public_compilation_rejects_same_id_different_reference_identity() -> None:
    complete = _compile((_source(),))
    assert complete.projection is not None
    source = complete.selected_candidates[0]
    assert source.reference is not None
    forged_ref = CanonicalReference(
        source.reference.reference_id,
        source.reference.owner,
        source.reference.canonical_ref,
        _digest("f"),
        truth_class="EXACT",
        freshness_class="CURRENT",
        metadata={},
    )
    forged_projection = replace(
        complete.projection, artifact_evidence_refs=(forged_ref,), projection_digest=""
    )
    with pytest.raises(ValueError, match="artifact_evidence_refs references do not match"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF,
            objective=complete.objective, objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity, projection=forged_projection,
            selection_receipt=complete.selection_receipt,
            selected_candidates=complete.selected_candidates, graph_edges=(), admissible=True,
        )


def test_public_compilation_rejects_node_budget_bypass() -> None:
    source = _source()
    proof_ref = _ref("ref:budget-proof", _digest("e"))
    proof = ProjectContextCandidate(
        candidate_id="proof:budget", category=CandidateCategory.PROOF_OBLIGATION,
        source_adapter="adapter.proof", origin_ref=proof_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT, reference=proof_ref,
    )
    complete = _compile((source, proof))
    assert complete.projection is not None
    forged_receipt = ProjectionSelectionReceipt(
        objective_digest=complete.objective_digest,
        repository_identity_digest=complete.repository_identity.identity_digest,
        canonical_owner=complete.selection_receipt.canonical_owner,
        selected=complete.selection_receipt.selected, omitted_irrelevant=(),
        omitted_by_budget=(), stale=(), unavailable=(), conflicting=(),
        source_adapter_missing=(), mandatory_evidence_missing=(),
        status=SelectionStatus.COMPLETE, budget=ProjectionBudget(max_nodes=1, max_edges=32),
    )
    with pytest.raises(ValueError, match="node budget"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF,
            objective=complete.objective, objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity, projection=complete.projection,
            selection_receipt=forged_receipt, selected_candidates=complete.selected_candidates,
            graph_edges=complete.graph_edges, admissible=True,
        )


def test_public_compilation_rejects_edge_budget_bypass() -> None:
    source = _source()
    test_ref = _ref("ref:edge-budget-test", _digest("e"))
    direct_test = ProjectContextCandidate(
        candidate_id="test:edge-budget", category=CandidateCategory.TEST,
        source_adapter="adapter.test", origin_ref=test_ref.canonical_ref,
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT, reference=test_ref,
        dependency_ids=(source.candidate_id,),
    )
    edges = (
        ProjectContextEdge(source.candidate_id, direct_test.candidate_id, "tests", EdgeTruthClass.EXACT),
        ProjectContextEdge(source.candidate_id, direct_test.candidate_id, "supports", EdgeTruthClass.EXACT),
    )
    complete = _compile((source, direct_test), edges)
    assert len(complete.graph_edges) == 2
    forged_receipt = ProjectionSelectionReceipt(
        objective_digest=complete.objective_digest,
        repository_identity_digest=complete.repository_identity.identity_digest,
        canonical_owner=complete.selection_receipt.canonical_owner,
        selected=complete.selection_receipt.selected, omitted_irrelevant=(),
        omitted_by_budget=(), stale=(), unavailable=(), conflicting=(),
        source_adapter_missing=(), mandatory_evidence_missing=(),
        status=SelectionStatus.COMPLETE, budget=ProjectionBudget(max_nodes=16, max_edges=1),
    )
    with pytest.raises(ValueError, match="edge budget"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF,
            objective=complete.objective, objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity, projection=complete.projection,
            selection_receipt=forged_receipt, selected_candidates=complete.selected_candidates,
            graph_edges=complete.graph_edges, admissible=True,
        )


def test_public_compilation_rejects_reserved_source_selected_id() -> None:
    complete = _compile((_source(),))
    assert complete.projection is not None
    reserved = replace(
        complete.selected_candidates[0], candidate_id="source:selected"
    )
    forged_receipt = ProjectionSelectionReceipt(
        objective_digest=complete.objective_digest,
        repository_identity_digest=complete.repository_identity.identity_digest,
        canonical_owner=complete.selection_receipt.canonical_owner,
        selected=("source:selected",), omitted_irrelevant=(),
        omitted_by_budget=(), stale=(), unavailable=(), conflicting=(),
        source_adapter_missing=(), mandatory_evidence_missing=(),
        status=SelectionStatus.COMPLETE, budget=complete.selection_receipt.budget,
    )
    with pytest.raises(ValueError, match="candidate_id 'source:selected' is reserved"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF,
            objective=complete.objective, objective_digest=complete.objective_digest,
            repository_identity=complete.repository_identity, projection=complete.projection,
            selection_receipt=forged_receipt, selected_candidates=(reserved,),
            graph_edges=(), admissible=True,
        )

def test_public_compilation_rejects_low_level_tampered_nested_reference() -> None:
    complete = _compile((_source(),))
    assert complete.projection is not None
    source = complete.selected_candidates[0]
    assert source.reference is not None
    object.__setattr__(source.reference, "canonical_ref", None)
    object.__setattr__(source, "origin_ref", None)
    with pytest.raises(ValueError, match="canonical reference failed revalidation"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF, objective=complete.objective,
            objective_digest=complete.objective_digest, repository_identity=complete.repository_identity,
            projection=complete.projection, selection_receipt=complete.selection_receipt,
            selected_candidates=complete.selected_candidates, graph_edges=complete.graph_edges, admissible=True,
        )


def test_public_compilation_rejects_low_level_tampered_temporal_binding() -> None:
    complete = _compile((_source(),))
    source = complete.selected_candidates[0]
    object.__setattr__(source.temporal_bindings[0], "digest", None)
    with pytest.raises(ValueError, match="temporal binding failed revalidation"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF, objective=complete.objective,
            objective_digest=complete.objective_digest, repository_identity=complete.repository_identity,
            projection=complete.projection, selection_receipt=complete.selection_receipt,
            selected_candidates=complete.selected_candidates, graph_edges=complete.graph_edges, admissible=True,
        )

def test_public_compilation_rejects_unbounded_selected_candidate_iterable_without_consuming_it() -> None:
    complete = _compile((_source(),))

    class ExplodingSelected:
        def __iter__(self):
            raise AssertionError("selected candidate iterable must not be consumed")

    with pytest.raises(TypeError, match="selected_candidates must be an exact immutable tuple"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF, objective=complete.objective,
            objective_digest=complete.objective_digest, repository_identity=complete.repository_identity,
            projection=complete.projection, selection_receipt=complete.selection_receipt,
            selected_candidates=ExplodingSelected(), graph_edges=complete.graph_edges, admissible=True,
        )


def test_public_compilation_rejects_unbounded_graph_edge_iterable_without_consuming_it() -> None:
    complete = _compile((_source(),))

    class ExplodingEdges:
        def __iter__(self):
            raise AssertionError("graph edge iterable must not be consumed")

    with pytest.raises(TypeError, match="graph_edges must be an exact immutable tuple"):
        ProjectContextCompilation(
            project_ref=PROJECT_REF, objective=complete.objective,
            objective_digest=complete.objective_digest, repository_identity=complete.repository_identity,
            projection=complete.projection, selection_receipt=complete.selection_receipt,
            selected_candidates=complete.selected_candidates, graph_edges=ExplodingEdges(), admissible=True,
        )


def test_candidate_rejects_unbounded_temporal_binding_iterable_without_consuming_it() -> None:
    source = _source()

    class ExplodingBindings:
        def __iter__(self):
            raise AssertionError("temporal binding iterable must not be consumed")

    with pytest.raises(TypeError, match="temporal_bindings must be an exact immutable tuple"):
        replace(source, temporal_bindings=ExplodingBindings())
