"""Focused tests for Aura bilateral intent refinement contracts."""
from __future__ import annotations

import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_event_contracts import stable_digest  # noqa: E402
from aura_intent_refinement import (  # noqa: E402
    AmbiguityClass,
    ClarificationQuestion,
    ConfirmationStatus,
    GuardrailEnforcementClass,
    GuardrailHardness,
    GuardrailProposal,
    GuardrailSourceClass,
    HumanGuardrailDisposition,
    IntentConfirmationReceipt,
    IntentRefinementSession,
    IntentRevisionDelta,
    NegativeRequirementClass,
    PairedTeachBack,
    PlanRevisionClass,
    RefinementStage,
    authority_digest,
    compile_default_guardrails,
    detect_requirement_contradictions,
    extract_negative_requirements,
    guardrail_set_digest,
    refinement_capabilities,
)

HEAD = "598804b3dce8d39480d8494cf0144f872b01d9ca"
TREE = "tree-digest"
ALLOWED = (
    "aura_intent_refinement.py",
    "schemas/aura_intent_refinement.v1.schema.json",
    "tests/test_aura_intent_refinement.py",
)


def teach_back() -> PairedTeachBack:
    return PairedTeachBack.create(
        will_do=("Compile confirmed bilateral intent.",),
        will_not_do=("Grant patch, publication, or merge authority.",),
        will_preserve=("Canonical IntentPacket and SemanticLedger ownership.",),
        will_stop_or_escalate_if=("Meaning, scope, authority, or guardrails change.",),
        positive_examples=("A confirmed negative requirement remains in proof.",),
        negative_examples=("A model silently removes a human-added guardrail.",),
    )


def confirmed_guardrails() -> tuple[GuardrailProposal, ...]:
    return tuple(
        item if item.is_hard else item.with_human_disposition("CONFIRMED")
        for item in compile_default_guardrails(
            arena="CODING",
            affected_files=ALLOWED,
            affected_symbols=("IntentRefinementSession",),
        )
    )


def test_schema_lists_all_public_contracts():
    schema = json.loads(
        (REPO_ROOT / "schemas" / "aura_intent_refinement.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert {
        "IntentRefinementSession",
        "ClarificationQuestion",
        "GuardrailProposal",
        "PairedTeachBack",
        "IntentConfirmationReceipt",
        "IntentRevisionDelta",
        "NegativeRequirement",
    }.issubset(schema["$defs"])


def test_declares_no_parallel_owner_or_mutation_authority():
    capabilities = refinement_capabilities()
    assert all(
        capabilities[name] is False
        for name in (
            "memory_owner",
            "truth_owner",
            "policy_owner",
            "routing_owner",
            "verification_owner",
            "patch_authority",
            "production_mutation",
        )
    )
    assert capabilities["human_confirmation_required"] is True
    assert capabilities["canonical_outputs"] == [
        "aura_unified_memory_continuity.IntentPacket",
        "aura_unified_memory_continuity.SemanticLedger",
    ]


def test_negative_extraction_preserves_spans_and_classes():
    text = (
        "Do not merge automatically. Leave canonical geometry unchanged. "
        "Do not silently continue when the asset digest fails. "
        "Do not approve professional release. Do not include private project data in logs. "
        "Do not call paid providers. Do not weaken tests to make the patch pass. "
        "Do not touch files outside this subsystem. Do not deploy until the canary passes. "
        "Avoid adding another dependency."
    )
    requirements = extract_negative_requirements(text)
    assert [item.classification for item in requirements] == [
        NegativeRequirementClass.PROHIBITION.value,
        NegativeRequirementClass.PRESERVATION_INVARIANT.value,
        NegativeRequirementClass.FAILURE_BEHAVIOR.value,
        NegativeRequirementClass.AUTHORITY_DENIAL.value,
        NegativeRequirementClass.PRIVACY_RESTRICTION.value,
        NegativeRequirementClass.RESOURCE_RESTRICTION.value,
        NegativeRequirementClass.QUALITY_PROHIBITION.value,
        NegativeRequirementClass.SCOPE_BOUNDARY.value,
        NegativeRequirementClass.TEMPORAL_RESTRICTION.value,
        NegativeRequirementClass.SOFT_PREFERENCE.value,
    ]
    for item in requirements:
        assert text[item.source_start:item.source_end] == item.source_span
        assert item.statement == item.source_span


def test_negation_variants_and_dangling_scope():
    requirements = extract_negative_requirements(
        "Don't hide failures. Never self-verify. Continue without exposing secrets. Do not."
    )
    assert [item.operator for item in requirements] == ["don't", "never", "without", "do not"]
    assert requirements[2].classification == "PRIVACY_RESTRICTION"
    assert requirements[3].ambiguous is True


def test_positive_negative_contradiction_detection():
    conflicts = detect_requirement_contradictions(
        ("Automatically merge the pull request.",),
        ("Do not merge the pull request automatically.",),
    )
    assert len(conflicts) == 1
    assert "merge" in conflicts[0]["shared_terms"]


def test_default_guardrails_lock_atlas_and_add_construction_boundaries():
    coding = compile_default_guardrails(arena="CODING")
    hard = [item for item in coding if item.is_hard]
    assert len(hard) == 7
    assert all(item.source_class == "ATLAS_PROHIBITION" for item in hard)
    construction = {item.statement for item in compile_default_guardrails(arena="CONSTRUCTION")}
    assert "Do not authorize physical work." in construction
    assert "Do not release payment." in construction


def test_hard_guardrail_cannot_be_rejected():
    guardrail = GuardrailProposal.create(
        statement="A producing agent must not be its only verifier.",
        source_class=GuardrailSourceClass.ATLAS_PROHIBITION,
        source_refs=("ATLAS_SELF_VERIFICATION_BLOCK",),
        hardness=GuardrailHardness.HARD_ARCHITECTURAL,
        enforcement_class=GuardrailEnforcementClass.AUTHORITY,
        rationale="Independent verification is mandatory.",
        human_disposition=HumanGuardrailDisposition.ACKNOWLEDGED_HARD,
    )
    with pytest.raises(ValueError, match="cannot be rejected"):
        guardrail.with_human_disposition(HumanGuardrailDisposition.REJECTED_SOFT)


def test_question_and_teach_back_are_stable_and_immutable():
    question = ClarificationQuestion.create(
        ambiguity_class=AmbiguityClass.FAILURE_BEHAVIOR,
        question="How should a missing asset fail?",
        why_it_changes_execution="It selects fail-closed versus labelled fallback behavior.",
        candidate_answers=("Fail closed", "Labelled fallback"),
    )
    duplicate = ClarificationQuestion.create(
        ambiguity_class=AmbiguityClass.FAILURE_BEHAVIOR,
        question="How should a missing asset fail?",
        why_it_changes_execution="It selects fail-closed versus labelled fallback behavior.",
        candidate_answers=("Fail closed", "Labelled fallback"),
    )
    assert question.question_id == duplicate.question_id
    with pytest.raises(FrozenInstanceError):
        teach_back().will_do = ("mutated",)


def test_session_lifecycle_requires_bilateral_confirmation_and_current_head():
    session = IntentRefinementSession.create(
        repository_head=HEAD,
        working_tree_digest=TREE,
        arena="CODING",
        source_request="Build bilateral intent refinement.",
        created_at=100.0,
        expires_at=200.0,
    )
    with pytest.raises(ValueError, match="illegal refinement transition"):
        session.transition(RefinementStage.HUMAN_CONFIRMED, now=110.0)
    pending = session.transition(
        RefinementStage.ANALYZED,
        positive_requirements=("Compile the request.",),
        negative_requirements=("Do not publish.",),
        now=110.0,
    ).transition(RefinementStage.TEACH_BACK_PENDING, teach_back=teach_back(), now=120.0)
    confirmed = pending.transition(
        RefinementStage.HUMAN_CONFIRMED,
        confirmation_status=ConfirmationStatus.CONFIRMED,
        now=130.0,
    )
    assert confirmed.is_current(repository_head=HEAD, working_tree_digest=TREE, now=150.0)
    assert not confirmed.is_current(repository_head="moved", working_tree_digest=TREE, now=150.0)
    with pytest.raises(ValueError, match="confirmation receipt"):
        confirmed.transition(RefinementStage.COMPILED, now=140.0)


def test_confirmation_receipt_binds_digests_and_stales_on_change():
    guardrails = confirmed_guardrails()
    authority = {"commit": False, "push": False, "merge": False}
    receipt = IntentConfirmationReceipt.create(
        session_id="session-1",
        repository_head=HEAD,
        source_tree_digest=TREE,
        working_tree_clean_receipt="clean-receipt",
        source_request_digest=stable_digest("request"),
        positive_requirements=("Compile bilateral intent.",),
        negative_requirements=("Do not publish or merge.",),
        semantic_ledger_digest="semantic-digest",
        guardrails=guardrails,
        authority=authority,
        teach_back=teach_back(),
        allowed_paths=ALLOWED,
        runtime_profile_digest="runtime-profile",
        human_reviewer="Dallas",
        human_disposition="CONFIRMED",
        confirmed_at=100.0,
        expires_at=200.0,
        expires_or_stales_on=("repository head changes", "guardrails change"),
    )
    assert receipt.guardrail_set_digest == guardrail_set_digest(guardrails)
    assert receipt.authority_digest == authority_digest(authority)
    kwargs = dict(
        repository_head=HEAD,
        source_tree_digest=TREE,
        semantic_ledger_digest="semantic-digest",
        guardrail_set_digest=receipt.guardrail_set_digest,
        authority_digest=receipt.authority_digest,
        allowed_paths=ALLOWED,
        runtime_profile_digest="runtime-profile",
        now=150.0,
    )
    assert receipt.is_current(**kwargs)
    assert not receipt.is_current(**{**kwargs, "repository_head": "moved"})


def test_revision_classes_enforce_reconfirmation_and_council_replan():
    common = dict(
        parent_confirmation_id="confirmation-1",
        trigger_evidence=("incident-replay-1",),
        base_repository_head=HEAD,
        base_source_tree_digest=TREE,
        candidate_tree_digest="candidate-tree",
        allowed_paths=ALLOWED,
        generated_artifact_disposition="REGENERATE_FROM_FINAL_TREE",
    )
    with pytest.raises(ValueError, match="human reconfirmation"):
        IntentRevisionDelta.create(
            **common,
            revision_class=PlanRevisionClass.INTENT_AUTHORITY_SCOPE_CHANGE,
            scope_changed=True,
        )
    with pytest.raises(ValueError, match="Council"):
        IntentRevisionDelta.create(
            **common,
            revision_class=PlanRevisionClass.BOUNDED_PLAN_RESTRUCTURING,
        )
    delta = IntentRevisionDelta.create(
        **common,
        revision_class=PlanRevisionClass.INTENT_AUTHORITY_SCOPE_CHANGE,
        scope_changed=True,
        prior_confirmation_staled=True,
        requires_human_reconfirmation=True,
        requires_council_replan=True,
    )
    assert delta.prior_confirmation_staled is True
    assert delta.requires_human_reconfirmation is True
