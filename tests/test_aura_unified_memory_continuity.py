from __future__ import annotations

from dataclasses import replace
import math

import pytest

from aura_architect_loop import ACT_CAPSULE_VERSION, ActCapsule
from aura_event_contracts import PATCH_AUTHORITY, stable_digest
from aura_model_cognome import ModelEndpointIdentity
from aura_relationship_experience import RelationshipExperienceObservation
from aura_unified_memory_continuity import (
    UNIVERSAL_AGENT_KERNEL,
    ActCapsuleEnvelope,
    ArenaEvidenceItem,
    AuthorityEnvelope,
    ContinuityDelta,
    ContinuitySensitivityReceipt,
    EvidenceTruthClass,
    IntentPacket,
    LearningToReproofDecision,
    ModelExecutionPacket,
    ModelProfileRef,
    PredictionPacket,
    QDKTConsequentialAdmission,
    SemanticDefinition,
    SemanticLedger,
    commit_prediction,
    compile_act_capsule_envelope,
    compile_arena_evidence_slice,
    compile_continuity_delta,
    compile_model_execution_packet,
    derive_continuity_sensitivity_receipt,
    evaluate_learning_to_reproof,
    evaluate_qdkt_consequential_admission,
    observe_prediction,
    relationship_experience_kwargs,
)

HEAD = "a" * 40
SOURCE_DIGEST = "b" * 64
WORKING_TREE_DIGEST = "c" * 64
CODEMAP_DIGEST = "d" * 64


def _intent() -> IntentPacket:
    return IntentPacket.create(
        objective="Add unified manufactured-memory and continuity contracts",
        purpose="Preserve human intent and learn only from verified consequence",
        user_meaning="Use one governed lifecycle without a duplicate memory owner",
        mode="EXECUTE",
        arena="Coding",
        constraints=("exact current source", "bounded repair budget"),
        prohibitions=("automatic merge", "model-vote authority"),
        authority=AuthorityEnvelope(inspect=True, edit=True, test=True),
        acceptance_criteria=(
            "focused tests pass",
            "P0 remains immutable after P1",
            "continuity evidence remains proposal-only",
        ),
        required_evidence=("exact source", "focused tests", "independent verifier"),
        risk_class="architecture",
        cost_budget="bounded",
        context_budget="minimum sufficient",
        privacy_class="PROJECT",
        freshness_requirement="CURRENT_HEAD",
        output_contract="verified unified diff and Continuity Delta",
    )


def _semantic_ledger(intent: IntentPacket) -> SemanticLedger:
    return SemanticLedger.create(
        intent_digest=intent.intent_digest,
        definitions=(
            SemanticDefinition(
                term="memory",
                means=("active causal evidence for one task",),
                does_not_mean=("a second universal database",),
                source_refs=("handoff:memory-doctrine",),
            ),
            SemanticDefinition(
                term="continuity",
                means=("verified consequence and protected pathways",),
                does_not_mean=("automatic durable promotion",),
                source_refs=("handoff:continuity-doctrine",),
            ),
            SemanticDefinition(
                term="verified",
                means=("independently checked against exact evidence",),
                does_not_mean=("model self-assessment",),
                source_refs=("architecture:verification",),
            ),
        ),
    )


def _arena_slice(intent: IntentPacket):
    return compile_arena_evidence_slice(
        repository_head=HEAD,
        working_tree_digest=WORKING_TREE_DIGEST,
        codemap_digest=CODEMAP_DIGEST,
        objective_digest=intent.intent_digest,
        candidate_items=(
            ArenaEvidenceItem(
                evidence_ref="source:aura_architect_loop.ActCapsule",
                causal_reason="Preserve the canonical Act Capsule owner",
                truth_class=EvidenceTruthClass.EXACT_SOURCE,
                canonical_owner="aura_architect_loop",
                source_digest="act-source",
                freshness="CURRENT",
                required=True,
            ),
            ArenaEvidenceItem(
                evidence_ref="source:aura_model_cognome.ModelEndpointIdentity",
                causal_reason="Bind the exact provider/model endpoint",
                truth_class=EvidenceTruthClass.EXACT_SOURCE,
                canonical_owner="aura_model_cognome",
                source_digest="cognome-source",
                freshness="CURRENT",
                required=True,
            ),
            ArenaEvidenceItem(
                evidence_ref="noise:unrelated-demo",
                causal_reason="Does not alter this contract decision",
                truth_class=EvidenceTruthClass.INFERRED,
                canonical_owner="unrelated",
                source_digest="noise",
                freshness="CURRENT",
                required=False,
            ),
        ),
        required_refs=(
            "source:aura_architect_loop.ActCapsule",
            "source:aura_model_cognome.ModelEndpointIdentity",
        ),
        prohibitions=("no duplicate truth owner", "no automatic promotion"),
        required_verifiers=("pytest", "Coding Waboose"),
    )


def _act_envelope(intent: IntentPacket, ledger: SemanticLedger, arena_slice):
    legacy = ActCapsule(
        capsule_version=ACT_CAPSULE_VERSION,
        task_id="U2-U7",
        role="bounded_builder",
        objective=intent.objective,
        target_file="aura_unified_memory_continuity.py",
        target_symbol="IntentPacket",
        related_files=["aura_architect_loop.py", "aura_model_cognome.py"],
        acceptance="Focused and authority-boundary tests pass.",
        escalate_if=["public API must change", "scope expands"],
        constraints=["preserve canonical owners"],
    )
    return compile_act_capsule_envelope(
        legacy_act_capsule=legacy,
        intent=intent,
        semantic_ledger=ledger,
        arena_slice=arena_slice,
        allowed_files=(
            "aura_unified_memory_continuity.py",
            "tests/test_aura_unified_memory_continuity.py",
        ),
        allowed_symbols=("IntentPacket", "PredictionPacket"),
        prohibited_effects=(
            "commit without explicit publication authorization",
            "automatic pull request",
            "automatic merge",
            "automatic learning promotion",
        ),
        invariants=(
            "canonical human intent is model-independent",
            "P0 is committed before P1",
            "exact evidence remains recoverable",
        ),
        allowed_tools=("pytest", "Coding Waboose"),
        acceptance_bundle=("focused tests pass", "independent verifier evidence exists"),
        repair_budget=2,
        legal_outcomes=("EXECUTE", "VERIFY", "REPAIR", "ESCALATE", "REFUSE"),
        continuity_requirements=(
            "return a Continuity Delta",
            "preserve protected pathways",
        ),
        required_semantic_terms=("memory", "continuity", "verified"),
    )


def _profile(*, profile_suffix: str = "one", expires_at: float = 200.0) -> ModelProfileRef:
    endpoint = ModelEndpointIdentity.create(
        provider="test-provider",
        requested_model=f"test-model-{profile_suffix}",
        returned_model=f"test-model-{profile_suffix}",
        endpoint_fingerprint=f"fingerprint-{profile_suffix}",
        provider_revision=f"revision-{profile_suffix}",
        first_seen_at=1.0,
        last_seen_at=2.0,
    )
    return ModelProfileRef.create(
        endpoint_identity=endpoint,
        calibrated_at=10.0,
        expires_at=expires_at,
        evidence_refs=(f"probe:{profile_suffix}",),
        uncertainty=0.2,
    )


def _model_packet(
    intent,
    envelope,
    profile,
    *,
    disagreements=(),
    selected_role="bounded_builder",
    evidence_refs=("source:aura_architect_loop.ActCapsule",),
    tools_available=("pytest",),
):
    return compile_model_execution_packet(
        intent=intent,
        act_envelope=envelope,
        arena_slice=_arena_slice(intent),
        model_profile=profile,
        current_source_digest=SOURCE_DIGEST,
        provider_config_digest="provider-config",
        selected_role=selected_role,
        task_slice="one exact module and focused tests",
        prompt_structure=("universal kernel", "canonical task", "exact evidence"),
        evidence_refs=evidence_refs,
        context_order=("intent", "authority", "evidence", "acceptance"),
        examples=({"input": "bounded", "output": "verified diff"},),
        tools_available=tools_available,
        reasoning_budget="bounded",
        output_schema="unified_diff_plus_continuity_delta",
        uncertainty_requirements=("label unsupported claims",),
        stop_conditions=("scope expands", "source identity changes"),
        retry_policy="one local repair",
        escalation_policy="Council V3 or human review",
        disagreement_refs=disagreements,
        observed_at=50.0,
    )


def _prediction(intent, envelope, packet):
    return commit_prediction(
        intent=intent,
        act_envelope=envelope,
        model_execution_packet=packet,
        current_state_digest="state-before",
        proposed_transition="add deterministic integration contracts",
        expected_state_delta=("new adapter module", "new focused tests"),
        expected_evidence=("pytest passes", "Waboose receipt"),
        expected_cost={"tokens": 500, "repairs": 1},
        expected_risk=("authority expansion", "schema duplication"),
        producer_id="bounded-worker",
        committed_at=60.0,
    )


def _observation(intent, prediction):
    return observe_prediction(
        prediction=prediction,
        p0_digest=prediction.p0_digest,
        objective_digest=intent.intent_digest,
        purpose_digest=stable_digest(intent.purpose),
        repository_head=HEAD,
        source_digest=SOURCE_DIGEST,
        observed_state_delta=("new adapter module", "new focused tests"),
        observed_evidence_refs=("pytest:pass", "waboose:pass"),
        observed_cost={"tokens": 450, "repairs": 0},
        missing_measurements=("cross-provider latency",),
        observer_id="independent-harness",
        observed_at=70.0,
    )


def _receipt(intent, profile, packet, prediction, observation):
    return derive_continuity_sensitivity_receipt(
        prediction=prediction,
        observation=observation,
        current_repository_head=HEAD,
        current_source_digest=SOURCE_DIGEST,
        model_profile_digest=profile.profile_digest,
        model_execution_packet_digest=packet.packet_digest,
        prompt_runtime_digest="prompt-runtime",
        error_class="EXPECTED_VARIANCE",
        prediction_error=("token cost lower than P0",),
        consequence_dimensions=("correctness", "authority", "continuity"),
        protected_pathways=("human intent", "exact evidence", "merge authority"),
        mutation_budget=("one integration module", "one focused test module"),
        replay_burden=("focused pytest", "Coding Waboose"),
        raw_evidence_refs=("pytest:pass", "waboose:pass"),
        replacement_candidate_refs=(),
        uncertainty=0.1,
        producer_id="continuity-compiler",
        independent_verifier_id="independent-harness",
        verifier_evidence_refs=("pytest:pass", "waboose:pass"),
        human_disposition_ref="human-review:pending",
    )


def _vertical_fixture():
    intent = _intent()
    ledger = _semantic_ledger(intent)
    arena_slice = _arena_slice(intent)
    envelope = _act_envelope(intent, ledger, arena_slice)
    profile = _profile()
    packet = _model_packet(intent, envelope, profile)
    prediction = _prediction(intent, envelope, packet)
    observation = _observation(intent, prediction)
    receipt = _receipt(intent, profile, packet, prediction, observation)
    return intent, ledger, arena_slice, envelope, profile, packet, prediction, observation, receipt


def _approved_learning_decision(receipt: ContinuitySensitivityReceipt) -> LearningToReproofDecision:
    return evaluate_learning_to_reproof(
        relationship_id="rel-memory-continuity",
        relationship_digest="relationship-digest",
        repository_head=HEAD,
        current_source_digest=SOURCE_DIGEST,
        continuity_receipt=receipt,
        crucible_proposal_ref="crucible:proposal",
        current_reproof_ref="reproof:current",
        independent_verifier_ref=receipt.independent_verifier_id,
        human_disposition="APPROVED",
        human_disposition_ref="human:approved:fixture",
    )


def _relationship_observation(
    intent: IntentPacket,
    receipt: ContinuitySensitivityReceipt,
    decision: LearningToReproofDecision,
) -> RelationshipExperienceObservation:
    kwargs = relationship_experience_kwargs(
        decision=decision,
        outcome="SUCCESS",
        verifier_evidence_refs=(decision.independent_verifier_ref, "pytest:pass"),
        receipt_refs=(receipt.receipt_id,),
        source_refs=("source:aura_unified_memory_continuity.py",),
        working_tree_digest=WORKING_TREE_DIGEST,
        privacy_class="PROJECT",
        objective_digest=intent.intent_digest,
        reason="Verified bounded fixture.",
    )
    return RelationshipExperienceObservation.create(transaction_time=80.0, **kwargs)


def test_vertical_context_to_consequence_loop_preserves_existing_owners() -> None:
    (
        intent,
        _ledger,
        arena_slice,
        envelope,
        _profile_ref,
        packet,
        prediction,
        observation,
        receipt,
    ) = _vertical_fixture()

    assert arena_slice.excluded_refs == ("noise:unrelated-demo",)
    assert envelope.canonical_act_owner == "aura_architect_loop.ActCapsule"
    assert envelope.compatibility_adapter is True
    assert packet.intent_digest == intent.intent_digest
    assert prediction.p0_digest == observation.p0_digest
    assert receipt.proposal_only is True
    assert receipt.canonical_truth_owner is False
    assert receipt.promotion_authority is False
    assert receipt.patch_authority == PATCH_AUTHORITY
    assert "Absence of permission is not permission." in UNIVERSAL_AGENT_KERNEL


def test_relationship_experience_adapter_uses_existing_canonical_owner() -> None:
    intent, _, _, _, _, _, _, _, receipt = _vertical_fixture()
    decision = _approved_learning_decision(receipt)
    observation = _relationship_observation(intent, receipt, decision)
    assert observation.relationship_id == decision.relationship_id
    assert observation.promotion_authority is False
    assert observation.canonical_truth_owner is False


def test_same_canonical_intent_compiles_to_distinct_model_packets() -> None:
    intent = _intent()
    ledger = _semantic_ledger(intent)
    arena_slice = _arena_slice(intent)
    envelope = _act_envelope(intent, ledger, arena_slice)

    packet_one = _model_packet(intent, envelope, _profile(profile_suffix="one"))
    packet_two = _model_packet(intent, envelope, _profile(profile_suffix="two"))

    assert packet_one.intent_digest == packet_two.intent_digest == intent.intent_digest
    assert packet_one.packet_digest != packet_two.packet_digest
    assert packet_one.action_authority is False
    assert packet_two.action_authority is False


def test_cross_model_disagreement_increases_verification_not_vote_authority() -> None:
    intent = _intent()
    envelope = _act_envelope(intent, _semantic_ledger(intent), _arena_slice(intent))
    profile = _profile()

    ordinary = _model_packet(intent, envelope, profile)
    contrasted = _model_packet(
        intent,
        envelope,
        profile,
        disagreements=("critic:model-two",),
    )

    assert ordinary.required_verification_depth == 1
    assert contrasted.required_verification_depth == 2
    assert contrasted.action_authority is False


def test_expired_model_profile_fails_closed() -> None:
    intent = _intent()
    envelope = _act_envelope(intent, _semantic_ledger(intent), _arena_slice(intent))
    profile = _profile(expires_at=40.0)

    with pytest.raises(ValueError, match="not current"):
        _model_packet(intent, envelope, profile)


def test_saturation_fails_when_required_context_is_missing() -> None:
    intent = _intent()
    with pytest.raises(ValueError, match="missing required refs"):
        compile_arena_evidence_slice(
            repository_head=HEAD,
            working_tree_digest=WORKING_TREE_DIGEST,
            codemap_digest=CODEMAP_DIGEST,
            objective_digest=intent.intent_digest,
            candidate_items=(),
            required_refs=("source:missing",),
            prohibitions=(),
            required_verifiers=("pytest",),
        )


def test_stale_required_evidence_fails_closed() -> None:
    intent = _intent()
    with pytest.raises(ValueError, match="required evidence"):
        compile_arena_evidence_slice(
            repository_head=HEAD,
            working_tree_digest=WORKING_TREE_DIGEST,
            codemap_digest=CODEMAP_DIGEST,
            objective_digest=intent.intent_digest,
            candidate_items=(
                ArenaEvidenceItem(
                    evidence_ref="source:stale",
                    causal_reason="Would change the edit",
                    truth_class="EXACT_SOURCE",
                    canonical_owner="owner",
                    source_digest="digest",
                    freshness="STALE",
                    required=True,
                ),
            ),
            required_refs=("source:stale",),
            prohibitions=(),
            required_verifiers=("pytest",),
        )


def test_missing_semantic_term_blocks_act_capsule_compilation() -> None:
    intent = _intent()
    with pytest.raises(ValueError, match="missing required terms"):
        compile_act_capsule_envelope(
            legacy_act_capsule={"task_id": "one", "objective": intent.objective},
            intent=intent,
            semantic_ledger=_semantic_ledger(intent),
            arena_slice=_arena_slice(intent),
            allowed_files=(),
            allowed_symbols=(),
            prohibited_effects=("automatic merge",),
            invariants=("intent stable",),
            allowed_tools=(),
            acceptance_bundle=("tests pass",),
            repair_budget=0,
            legal_outcomes=("REFUSE",),
            continuity_requirements=("return delta",),
            required_semantic_terms=("nonexistent-term",),
        )


def test_p0_digest_cannot_be_rewritten_after_commit() -> None:
    intent, _, _, envelope, _, packet, prediction, _, _ = _vertical_fixture()
    with pytest.raises(ValueError, match="P0 was modified"):
        observe_prediction(
            prediction=prediction,
            p0_digest="tampered",
            objective_digest=intent.intent_digest,
            purpose_digest=stable_digest(intent.purpose),
            repository_head=HEAD,
            source_digest=SOURCE_DIGEST,
            observed_state_delta=("changed",),
            observed_evidence_refs=("test:pass",),
            observed_cost={},
            missing_measurements=(),
            observer_id="observer",
            observed_at=70.0,
        )
    assert prediction.act_capsule_digest == envelope.envelope_digest
    assert prediction.model_execution_packet_digest == packet.packet_digest


def test_p1_cannot_precede_p0() -> None:
    intent, _, _, _, _, _, prediction, _, _ = _vertical_fixture()
    with pytest.raises(ValueError, match="cannot precede"):
        observe_prediction(
            prediction=prediction,
            p0_digest=prediction.p0_digest,
            objective_digest=intent.intent_digest,
            purpose_digest=stable_digest(intent.purpose),
            repository_head=HEAD,
            source_digest=SOURCE_DIGEST,
            observed_state_delta=(),
            observed_evidence_refs=("test:pass",),
            observed_cost={},
            missing_measurements=(),
            observer_id="observer",
            observed_at=59.0,
        )


def test_continuity_receipt_rejects_self_verification() -> None:
    intent, _, _, _, profile, packet, prediction, observation, _ = _vertical_fixture()
    with pytest.raises(ValueError, match="independent P1 observer"):
        derive_continuity_sensitivity_receipt(
            prediction=prediction,
            observation=observation,
            current_repository_head=HEAD,
            current_source_digest=SOURCE_DIGEST,
            model_profile_digest=profile.profile_digest,
            model_execution_packet_digest=packet.packet_digest,
            prompt_runtime_digest="runtime",
            error_class="NONE",
            prediction_error=(),
            consequence_dimensions=("correctness",),
            protected_pathways=("authority",),
            mutation_budget=("one file",),
            replay_burden=("pytest",),
            raw_evidence_refs=("pytest:pass",),
            replacement_candidate_refs=(),
            uncertainty=0.0,
            producer_id="same",
            independent_verifier_id="same",
            verifier_evidence_refs=("pytest:pass",),
            human_disposition_ref="human:pending",
        )
    assert intent.intent_digest == prediction.objective_digest


def test_continuity_receipt_cannot_be_copied_across_head_or_source() -> None:
    _, _, _, _, profile, packet, prediction, observation, _ = _vertical_fixture()
    common = dict(
        prediction=prediction,
        observation=observation,
        current_source_digest=SOURCE_DIGEST,
        model_profile_digest=profile.profile_digest,
        model_execution_packet_digest=packet.packet_digest,
        prompt_runtime_digest="runtime",
        error_class="NONE",
        prediction_error=(),
        consequence_dimensions=("correctness",),
        protected_pathways=("authority",),
        mutation_budget=("one file",),
        replay_burden=("pytest",),
        raw_evidence_refs=("pytest:pass",),
        replacement_candidate_refs=(),
        uncertainty=0.0,
        producer_id="producer",
        independent_verifier_id="verifier",
        verifier_evidence_refs=("pytest:pass",),
        human_disposition_ref="human:pending",
    )
    with pytest.raises(ValueError, match="repository heads"):
        derive_continuity_sensitivity_receipt(
            current_repository_head="different-head",
            **common,
        )
    common["current_source_digest"] = "different-source"
    with pytest.raises(ValueError, match="source digests"):
        derive_continuity_sensitivity_receipt(
            current_repository_head=HEAD,
            **common,
        )


def test_non_finite_costs_and_uncertainty_fail_closed() -> None:
    intent, _, _, envelope, _, packet, _, _, _ = _vertical_fixture()
    with pytest.raises(ValueError):
        commit_prediction(
            intent=intent,
            act_envelope=envelope,
            model_execution_packet=packet,
            current_state_digest="state",
            proposed_transition="change",
            expected_state_delta=("change",),
            expected_evidence=("test",),
            expected_cost={"tokens": math.inf},
            expected_risk=("risk",),
            producer_id="producer",
            committed_at=1.0,
        )
    with pytest.raises(ValueError):
        ModelProfileRef.create(
            endpoint_identity=ModelEndpointIdentity.create(
                provider="provider",
                requested_model="model",
                first_seen_at=1.0,
                last_seen_at=2.0,
            ),
            calibrated_at=1.0,
            expires_at=2.0,
            evidence_refs=("probe",),
            uncertainty=math.nan,
        )


def test_learning_to_reproof_remains_closed_until_all_gates_exist() -> None:
    _, _, _, _, _, _, _, _, receipt = _vertical_fixture()
    closed = evaluate_learning_to_reproof(
        relationship_id="relationship",
        relationship_digest="digest",
        repository_head=HEAD,
        current_source_digest=SOURCE_DIGEST,
        continuity_receipt=receipt,
    )
    assert closed.eligible_for_relationship_experience is False
    assert "MISSING_CURRENT_REPROOF" in closed.blockers
    assert closed.promotion_authority is False

    open_decision = _approved_learning_decision(receipt)
    assert open_decision.eligible_for_relationship_experience is True
    assert open_decision.blockers == ()
    assert open_decision.proposal_only is True


def test_qdkt_consequential_admission_requires_every_governed_gate() -> None:
    intent, _, _, _, _, _, _, _, receipt = _vertical_fixture()
    closed_decision = evaluate_learning_to_reproof(
        relationship_id="relationship",
        relationship_digest="digest",
        repository_head=HEAD,
        current_source_digest=SOURCE_DIGEST,
        continuity_receipt=receipt,
    )
    closed = evaluate_qdkt_consequential_admission(
        continuity_receipt=receipt,
        learning_decision=closed_decision,
        relationship_experience=None,
        raw_evidence_refs=receipt.raw_evidence_refs,
        current_repository_head=HEAD,
        current_source_digest=SOURCE_DIGEST,
        purpose_compatible=True,
        privacy_compatible=True,
        consent_compatible=True,
        sovereignty_compatible=True,
    )
    assert closed.admitted is False
    assert "LEARNING_REPROOF_NOT_ELIGIBLE" in closed.blockers
    assert closed.crystallization_authority is False

    decision = _approved_learning_decision(receipt)
    relationship_observation = _relationship_observation(intent, receipt, decision)
    admitted = evaluate_qdkt_consequential_admission(
        continuity_receipt=receipt,
        learning_decision=decision,
        relationship_experience=relationship_observation,
        raw_evidence_refs=receipt.raw_evidence_refs,
        current_repository_head=HEAD,
        current_source_digest=SOURCE_DIGEST,
        purpose_compatible=True,
        privacy_compatible=True,
        consent_compatible=True,
        sovereignty_compatible=True,
    )
    assert admitted.admitted is True
    assert admitted.relationship_experience_ref == relationship_observation.observation_id
    assert admitted.proposal_only is True
    assert admitted.crystallization_authority is False


def test_authority_envelope_requires_monotonic_grants() -> None:
    with pytest.raises(ValueError, match="commit authority requires edit"):
        AuthorityEnvelope(commit=True)
    with pytest.raises(ValueError, match="publish_pr authority requires commit"):
        AuthorityEnvelope(edit=True, publish_pr=True)
    with pytest.raises(ValueError, match="merge authority requires publish_pr"):
        AuthorityEnvelope(edit=True, commit=True, merge=True)
    with pytest.raises(ValueError, match="production mutation authority requires edit"):
        AuthorityEnvelope(production_mutation=True)


def test_act_capsule_envelope_rejects_noncanonical_and_out_of_scope_capsules() -> None:
    intent = _intent()
    ledger = _semantic_ledger(intent)
    arena_slice = _arena_slice(intent)
    with pytest.raises(ValueError, match="complete canonical ActCapsule"):
        compile_act_capsule_envelope(
            legacy_act_capsule={"task_id": "incomplete"},
            intent=intent,
            semantic_ledger=ledger,
            arena_slice=arena_slice,
            allowed_files=(),
            allowed_symbols=(),
            prohibited_effects=("automatic merge",),
            invariants=("intent stable",),
            allowed_tools=(),
            acceptance_bundle=("tests pass",),
            repair_budget=0,
            legal_outcomes=("REFUSE",),
            continuity_requirements=("return delta",),
            required_semantic_terms=("memory",),
        )

    capsule = ActCapsule(
        capsule_version=ACT_CAPSULE_VERSION,
        task_id="outside-scope",
        role="bounded_builder",
        objective=intent.objective,
        target_file="outside.py",
        target_symbol="Outside",
    )
    with pytest.raises(ValueError, match="target_file is outside allowed_files"):
        compile_act_capsule_envelope(
            legacy_act_capsule=capsule,
            intent=intent,
            semantic_ledger=ledger,
            arena_slice=arena_slice,
            allowed_files=("inside.py",),
            allowed_symbols=("Outside",),
            prohibited_effects=("automatic merge",),
            invariants=("intent stable",),
            allowed_tools=(),
            acceptance_bundle=("tests pass",),
            repair_budget=0,
            legal_outcomes=("REFUSE",),
            continuity_requirements=("return delta",),
            required_semantic_terms=("memory",),
        )


def test_model_packet_rejects_role_tool_and_evidence_scope_expansion() -> None:
    intent = _intent()
    envelope = _act_envelope(intent, _semantic_ledger(intent), _arena_slice(intent))
    profile = _profile()
    with pytest.raises(ValueError, match="selected_role differs"):
        _model_packet(intent, envelope, profile, selected_role="unauthorized-role")
    with pytest.raises(ValueError, match="tools outside"):
        _model_packet(intent, envelope, profile, tools_available=("pytest", "shell"))
    with pytest.raises(ValueError, match="evidence outside"):
        _model_packet(intent, envelope, profile, evidence_refs=("source:unscoped",))


def test_prediction_is_deeply_immutable_and_revalidates_digest() -> None:
    intent, _, _, envelope, _, packet, prediction, _, _ = _vertical_fixture()
    with pytest.raises(TypeError):
        prediction.expected_cost["tokens"] = 999
    with pytest.raises(ValueError, match="P0 identity mismatch"):
        replace(prediction, proposed_transition="tampered after commitment")

    nested = commit_prediction(
        intent=intent,
        act_envelope=envelope,
        model_execution_packet=packet,
        current_state_digest="nested-state",
        proposed_transition="nested cost fixture",
        expected_state_delta=("change",),
        expected_evidence=("test",),
        expected_cost={"usage": {"tokens": 10}, "steps": [1, 2]},
        expected_risk=("risk",),
        producer_id="producer",
        committed_at=60.0,
    )
    with pytest.raises(TypeError):
        nested.expected_cost["usage"]["tokens"] = 11
    assert nested.expected_cost["steps"] == (1, 2)


def test_p1_requires_exact_committed_source_and_independent_observer() -> None:
    intent, _, _, _, _, _, prediction, _, _ = _vertical_fixture()
    common = dict(
        prediction=prediction,
        p0_digest=prediction.p0_digest,
        objective_digest=intent.intent_digest,
        purpose_digest=stable_digest(intent.purpose),
        observed_state_delta=("changed",),
        observed_evidence_refs=("pytest:pass",),
        observed_cost={},
        missing_measurements=(),
        observed_at=70.0,
    )
    with pytest.raises(ValueError, match="repository head differs"):
        observe_prediction(
            repository_head="different-head",
            source_digest=SOURCE_DIGEST,
            observer_id="independent",
            **common,
        )
    with pytest.raises(ValueError, match="source digest differs"):
        observe_prediction(
            repository_head=HEAD,
            source_digest="different-source",
            observer_id="independent",
            **common,
        )
    with pytest.raises(ValueError, match="cannot independently observe"):
        observe_prediction(
            repository_head=HEAD,
            source_digest=SOURCE_DIGEST,
            observer_id=prediction.producer_id,
            **common,
        )


def test_learning_reproof_rejects_stale_evidence_and_spoofed_verifier() -> None:
    _, _, _, _, _, _, _, _, receipt = _vertical_fixture()
    with pytest.raises(ValueError, match="repository head differs"):
        evaluate_learning_to_reproof(
            relationship_id="relationship",
            relationship_digest="digest",
            repository_head="stale-head",
            current_source_digest=SOURCE_DIGEST,
            continuity_receipt=receipt,
        )
    with pytest.raises(ValueError, match="verifier differs"):
        evaluate_learning_to_reproof(
            relationship_id="relationship",
            relationship_digest="digest",
            repository_head=HEAD,
            current_source_digest=SOURCE_DIGEST,
            continuity_receipt=receipt,
            independent_verifier_ref="spoofed-verifier",
        )


def test_qdkt_requires_canonical_relationship_and_complete_raw_evidence() -> None:
    intent, _, _, _, _, _, _, _, receipt = _vertical_fixture()
    decision = _approved_learning_decision(receipt)
    with pytest.raises(ValueError, match="canonical owner"):
        evaluate_qdkt_consequential_admission(
            continuity_receipt=receipt,
            learning_decision=decision,
            relationship_experience={"observation_id": "forged"},
            raw_evidence_refs=receipt.raw_evidence_refs,
            current_repository_head=HEAD,
            current_source_digest=SOURCE_DIGEST,
            purpose_compatible=True,
            privacy_compatible=True,
            consent_compatible=True,
            sovereignty_compatible=True,
        )
    relationship = _relationship_observation(intent, receipt, decision)
    with pytest.raises(ValueError, match="omitted continuity raw evidence"):
        evaluate_qdkt_consequential_admission(
            continuity_receipt=receipt,
            learning_decision=decision,
            relationship_experience=relationship,
            raw_evidence_refs=("unrelated:evidence",),
            current_repository_head=HEAD,
            current_source_digest=SOURCE_DIGEST,
            purpose_compatible=True,
            privacy_compatible=True,
            consent_compatible=True,
            sovereignty_compatible=True,
        )


def test_continuity_delta_updates_navigation_not_durable_memory() -> None:
    intent, _, _, envelope, _, _, _, _, receipt = _vertical_fixture()
    delta = compile_continuity_delta(
        objective_digest=intent.intent_digest,
        purpose_digest=stable_digest(intent.purpose),
        act_capsule_digest=envelope.envelope_digest,
        repository_head=HEAD,
        continuity_receipt_ref=receipt.receipt_id,
        decisions=("retain canonical owners",),
        changed_refs=("source:aura_unified_memory_continuity.py",),
        unchanged_protected_pathways=("human intent", "merge authority"),
        unresolved_refs=("cross-model benchmark",),
        next_required_actions=("human review",),
    )
    assert isinstance(delta, ContinuityDelta)
    assert delta.durable_lesson is False
    assert delta.promotion_authority is False


@pytest.mark.parametrize(
    "record_type",
    (
        ActCapsuleEnvelope,
        ModelExecutionPacket,
        PredictionPacket,
        ContinuitySensitivityReceipt,
        ContinuityDelta,
        LearningToReproofDecision,
        QDKTConsequentialAdmission,
    ),
)
def test_authority_boundaries_are_not_accidentally_promoted(record_type) -> None:
    intent, _ledger, _arena_slice, envelope, _profile, packet, prediction, _observation, receipt = (
        _vertical_fixture()
    )
    records = {
        ActCapsuleEnvelope: envelope,
        ModelExecutionPacket: packet,
        PredictionPacket: prediction,
        ContinuitySensitivityReceipt: receipt,
        ContinuityDelta: compile_continuity_delta(
            objective_digest=intent.intent_digest,
            purpose_digest=stable_digest(intent.purpose),
            act_capsule_digest=envelope.envelope_digest,
            repository_head=HEAD,
            continuity_receipt_ref=receipt.receipt_id,
            decisions=("retain",),
            changed_refs=(),
            unchanged_protected_pathways=("authority",),
            unresolved_refs=(),
            next_required_actions=("review",),
        ),
        LearningToReproofDecision: evaluate_learning_to_reproof(
            relationship_id="r",
            relationship_digest="d",
            repository_head=HEAD,
            current_source_digest=SOURCE_DIGEST,
            continuity_receipt=receipt,
        ),
        QDKTConsequentialAdmission: evaluate_qdkt_consequential_admission(
            continuity_receipt=receipt,
            learning_decision=evaluate_learning_to_reproof(
                relationship_id="r",
                relationship_digest="d",
                repository_head=HEAD,
                current_source_digest=SOURCE_DIGEST,
                continuity_receipt=receipt,
            ),
            relationship_experience=None,
            raw_evidence_refs=receipt.raw_evidence_refs,
            current_repository_head=HEAD,
            current_source_digest=SOURCE_DIGEST,
            purpose_compatible=False,
            privacy_compatible=False,
            consent_compatible=False,
            sovereignty_compatible=False,
        ),
    }
    payload = records[record_type].to_dict()
    for key in (
        "action_authority",
        "promotion_authority",
        "crystallization_authority",
        "canonical_truth_owner",
        "vsa_patch_authority",
    ):
        if key in payload:
            assert payload[key] is False
    if "patch_authority" in payload:
        assert payload["patch_authority"] == PATCH_AUTHORITY
