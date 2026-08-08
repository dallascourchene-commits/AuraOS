from __future__ import annotations

from aura_ephemeral_workspace_contracts import CanonicalReference, RepositoryIdentity
from aura_project_context_compiler import (
    CandidateAvailability,
    CandidateCategory,
    CandidateTruthClass,
    ContextAuthorityClass,
    ProjectContextCandidate,
    ProjectionBudget,
    SelectionStatus,
    compile_project_context_projection,
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
    return ProjectContextCandidate(
        candidate_id="source:answer-determining",
        category=CandidateCategory.SOURCE,
        source_adapter="adapter.source",
        origin_ref="source://module.py:answer",
        authority_class=ContextAuthorityClass.CANONICAL_READ,
        truth_class=CandidateTruthClass.EXACT_CURRENT,
        reference=_ref("ref:source-answer", digest),
        relevance_score=100,
        answer_determining=True,
    )


def _compile(candidates: tuple[ProjectContextCandidate, ...]):
    return compile_project_context_projection(
        OBJECTIVE,
        project_ref=PROJECT_REF,
        repository_identity=_repo(),
        candidates=candidates,
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
