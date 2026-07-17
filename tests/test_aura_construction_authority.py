from dataclasses import replace

import pytest

from aura_event_contracts import ActorType, MeasurementClass
from aura_relational_authority import (
    ApprovalAttestation,
    AttestationDecision,
    AuthorityGrant,
    ChainedAuthorityReceipt,
    QuorumPolicy,
    RiskClass,
)
from aura_construction_contracts import (
    ConstructionAuthorityClass,
    ConstructionClaim,
    ConstructionEvidence,
    ConstructionEvidenceClass,
    ConstructionEvent,
    ConstructionPrivacyClass,
    ConstructionScope,
    GENESIS_CHAIN_DIGEST,
)
from aura_construction_state import replay_construction_events
from aura_construction_authority import (
    ConstructionActionRequest,
    ConstructionAuthorityResult,
    ConstructionGovernanceReplay,
    ConstructionReceiptBinding,
    create_construction_receipt,
    evaluate_construction_authority,
    verify_construction_receipts,
)

D = "a" * 32
D2 = "b" * 32


def fixtures():
    scope = ConstructionScope("P1", "Z1", "WP1")
    evidence = ConstructionEvidence.create(
        scope=scope,
        subject_id="wall",
        evidence_class=ConstructionEvidenceClass.DOCUMENT,
        source_ref="doc",
        payload_digest=D,
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=0.9,
        authority_class=ConstructionAuthorityClass.INFORMATIVE,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        observed_at=1,
        expires_at=50,
    )
    event1 = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        trace_id="trace",
        record=evidence,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        created_at=2,
    )
    claim = ConstructionClaim.create(
        scope=scope,
        subject_id="wall",
        predicate="installed",
        value_digest=D2,
        claimant_id="contractor",
        evidence_refs=(evidence.evidence_id,),
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=0.8,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        created_at=3,
        expires_at=50,
    )
    event2 = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=2,
        previous_chain_digest=event1.chain_digest,
        trace_id="trace",
        record=claim,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        parent_event_ids=(event1.event_id,),
        created_at=4,
    )
    state = replay_construction_events((event1, event2))
    request = ConstructionActionRequest.create(
        scope=scope,
        action_kind="release work package",
        policy_scope="construction/P1/Z1",
        capability_scope="construction.release",
        risk_class=RiskClass.HIGH,
        required_claim_ids=(claim.claim_id,),
        created_at=5,
        expires_at=40,
    )
    return state, request, claim


def quorum_policy():
    return QuorumPolicy.create(
        risk_class=RiskClass.HIGH,
        minimum_approval_count=1,
        required_functional_roles=("OWNER",),
        minimum_distinct_principals=1,
    )


def authority_material(request, *, decision=AttestationDecision.APPROVE, action_id=None):
    grant = AuthorityGrant.create(
        principal_id="owner-1",
        authorized_functional_roles=("OWNER",),
        policy_scopes=(request.policy_scope,),
        capability_scopes=(request.capability_scope,),
        valid_from=1,
        expires_at=35,
        externally_verified_authority_ref="authority-ref",
        verified_authority_refs=("authority-ref",),
        now=10,
    )
    attestation = ApprovalAttestation.create(
        action_id=request.action_id if action_id is None else action_id,
        action_payload_digest=request.action_digest,
        principal_id="owner-1",
        grant=grant,
        decision=decision,
        functional_role="OWNER",
        policy_scope=request.policy_scope,
        capability_scope=request.capability_scope,
        public_rationale="Reviewed against bounded construction evidence.",
        evidence_refs=request.required_claim_ids,
        externally_verified_attestation_ref="attestation-ref",
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        created_at=9,
        expires_at=30,
        now=10,
    )
    return (grant,), (attestation,), quorum_policy()


def governance_replay(request):
    grants, attestations, policy = authority_material(request)
    return ConstructionGovernanceReplay.create(
        grants=grants,
        attestations=attestations,
        quorum_policy=policy,
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
    )


def evaluate_ready(state, request):
    grants, attestations, policy = authority_material(request)
    return evaluate_construction_authority(
        request=request,
        state=state,
        grants=grants,
        attestations=attestations,
        quorum_policy=policy,
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        now=10,
    )


def receipt_for(state, request, result, decision, **overrides):
    kwargs = {
        "authority_result": result,
        "request": request,
        "state": state,
        "governance_decision": decision,
        "governance_replay": governance_replay(request),
        "ledger_id": "construction-authority/P1",
        "sequence_number": 1,
        "externally_verified_receipt_ref": "receipt-ref",
        "verified_receipt_bindings": {"receipt-ref": result.result_digest},
        "created_at": 11,
    }
    kwargs.update(overrides)
    return create_construction_receipt(**kwargs)


def test_request_identity_is_stable():
    _, first, _ = fixtures()
    _, second, _ = fixtures()
    assert first == second


def test_request_requires_claims():
    _, request, _ = fixtures()
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope,
            action_kind="x",
            policy_scope="construction/P1",
            capability_scope="construction.release",
            risk_class=RiskClass.HIGH,
            required_claim_ids=(),
            created_at=1,
            expires_at=2,
        )


def test_authorized_governance_plus_ready_evidence_is_digitally_ready():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    assert decision.authorized
    assert result.evidence_ready
    assert result.governance_authorized
    assert result.digitally_ready
    assert result.human_release_required
    assert not result.physical_work_authorized


def test_unauthorized_governance_fails_closed():
    state, request, _ = fixtures()
    result, decision = evaluate_construction_authority(
        request=request,
        state=state,
        grants=(),
        attestations=(),
        quorum_policy=quorum_policy(),
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        now=10,
    )
    assert not decision.authorized
    assert result.evidence_ready
    assert not result.governance_authorized
    assert not result.digitally_ready
    assert "governance_not_authorized" in result.missing_reasons


def test_rejection_attestation_blocks_authorization():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(request, decision=AttestationDecision.REJECT)
    result, decision = evaluate_construction_authority(
        request=request,
        state=state,
        grants=grants,
        attestations=attestations,
        quorum_policy=policy,
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        now=10,
    )
    assert not decision.authorized
    assert not result.digitally_ready


def test_project_mismatch_rejected():
    state, request, _ = fixtures()
    bad = ConstructionActionRequest.create(
        scope=ConstructionScope("P2"),
        action_kind="x",
        policy_scope="construction/P2",
        capability_scope="construction.release",
        risk_class=RiskClass.HIGH,
        required_claim_ids=request.required_claim_ids,
        created_at=5,
        expires_at=40,
    )
    with pytest.raises(ValueError):
        evaluate_construction_authority(
            request=bad,
            state=state,
            grants=(),
            attestations=(),
            quorum_policy=quorum_policy(),
            verified_authority_refs=("authority-ref",),
            verified_attestation_refs=("attestation-ref",),
            now=10,
        )


def test_expired_request_rejected():
    state, request, _ = fixtures()
    with pytest.raises(ValueError):
        evaluate_construction_authority(
            request=request,
            state=state,
            grants=(),
            attestations=(),
            quorum_policy=quorum_policy(),
            verified_authority_refs=("authority-ref",),
            verified_attestation_refs=("attestation-ref",),
            now=50,
        )


def test_unknown_required_claim_is_evidence_not_ready():
    state, request, _ = fixtures()
    bad = ConstructionActionRequest.create(
        scope=request.scope,
        action_kind="x",
        policy_scope="construction/P1",
        capability_scope="construction.release",
        risk_class=RiskClass.HIGH,
        required_claim_ids=("unknown",),
        created_at=5,
        expires_at=40,
    )
    grants, attestations, policy = authority_material(bad)
    result, decision = evaluate_construction_authority(
        request=bad,
        state=state,
        grants=grants,
        attestations=attestations,
        quorum_policy=policy,
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        now=10,
    )
    assert decision.authorized
    assert not result.evidence_ready
    assert not result.digitally_ready
    assert any("claim_not_uniquely_active" in item for item in result.missing_reasons)


def test_tampered_request_rejected():
    _, request, _ = fixtures()
    with pytest.raises(ValueError):
        replace(request, action_kind="changed")


def test_tampered_result_rejected():
    state, request, _ = fixtures()
    result, _ = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        replace(result, physical_work_authorized=True)


def test_injectable_governance_evaluator_is_not_supported():
    state, request, _ = fixtures()
    with pytest.raises(TypeError):
        evaluate_construction_authority(
            request=request,
            state=state,
            grants=(),
            attestations=(),
            quorum_policy=quorum_policy(),
            verified_authority_refs=("authority-ref",),
            verified_attestation_refs=("attestation-ref",),
            now=10,
            governance_evaluator=lambda **_: None,
        )


def test_mismatched_attestation_cannot_authorize_request():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(request, action_id="another-action")
    result, decision = evaluate_construction_authority(
        request=request,
        state=state,
        grants=grants,
        attestations=attestations,
        quorum_policy=policy,
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        now=10,
    )
    assert not decision.authorized
    assert not result.digitally_ready


def test_action_scope_must_match_project_and_domain():
    _, request, _ = fixtures()
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope, action_kind="x", policy_scope="other/P1",
            capability_scope="construction.release", risk_class=RiskClass.HIGH,
            required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
        )
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope, action_kind="x", policy_scope="construction/P1",
            capability_scope="other.release", risk_class=RiskClass.HIGH,
            required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
        )


def test_duplicate_normalized_claim_ids_fail_closed():
    _, request, _ = fixtures()
    claim_id = request.required_claim_ids[0]
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope, action_kind="x", policy_scope="construction/P1",
            capability_scope="construction.release", risk_class=RiskClass.HIGH,
            required_claim_ids=(claim_id, f" {claim_id} "), created_at=5, expires_at=40,
        )


def test_empty_verified_reference_sets_fail_closed():
    state, request, _ = fixtures()
    with pytest.raises(ValueError):
        evaluate_construction_authority(
            request=request, state=state, grants=(), attestations=(),
            quorum_policy=quorum_policy(), verified_authority_refs=(),
            verified_attestation_refs=("attestation-ref",), now=10,
        )
    with pytest.raises(ValueError):
        evaluate_construction_authority(
            request=request, state=state, grants=(), attestations=(),
            quorum_policy=quorum_policy(), verified_authority_refs=("authority-ref",),
            verified_attestation_refs=(), now=10,
        )


def test_result_report_claim_set_mismatch_is_rejected():
    state, request, _ = fixtures()
    result, _ = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        replace(result, required_claim_ids=("other",))


def test_result_scope_key_must_belong_to_project():
    state, request, _ = fixtures()
    result, _ = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        replace(result, scope_key="P2/Z1/WP1")


def test_receipt_requires_ready_result():
    state, request, _ = fixtures()
    result, decision = evaluate_construction_authority(
        request=request, state=state, grants=(), attestations=(),
        quorum_policy=quorum_policy(), verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",), now=10,
    )
    with pytest.raises(ValueError):
        receipt_for(state, request, result, decision)


def test_receipt_requires_external_ref_bound_to_exact_result_digest():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        receipt_for(
            state, request, result, decision,
            verified_receipt_bindings={"receipt-ref": "f" * 32},
        )


def test_receipt_binds_request_state_decision_and_result():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    receipt, binding = receipt_for(state, request, result, decision)
    assert receipt.record_id == result.result_id
    assert binding.request_digest == request.action_digest
    assert binding.state_digest == state.state_digest
    assert binding.governance_decision_digest == decision.decision_digest
    assert binding.authority_result_digest == result.result_digest
    assert binding.human_release_required
    assert binding.physical_work_authorized is False


def test_receipt_rejects_mismatched_request():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    other = ConstructionActionRequest.create(
        scope=request.scope, action_kind="different", policy_scope=request.policy_scope,
        capability_scope=request.capability_scope, risk_class=RiskClass.HIGH,
        required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
    )
    with pytest.raises(ValueError):
        receipt_for(state, other, result, decision)


def test_receipt_ledger_is_project_bound():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        receipt_for(state, request, result, decision, ledger_id="construction-authority/P2")


def test_receipt_cannot_be_issued_after_result_expiry():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        receipt_for(state, request, result, decision, created_at=result.expires_at)


def test_receipt_chain_verifies_against_results():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    receipt, _ = receipt_for(state, request, result, decision)
    verification = verify_construction_receipts(
        (receipt,), results_by_id={result.result_id: result}
    )
    assert verification.valid


def test_receipt_result_map_keys_are_verified():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    receipt, _ = receipt_for(state, request, result, decision)
    with pytest.raises(ValueError):
        verify_construction_receipts((receipt,), results_by_id={"wrong": result})


def test_binding_tampering_rejected():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    _, binding = receipt_for(state, request, result, decision)
    with pytest.raises(ValueError):
        replace(binding, chain_digest="f" * 32)


def test_action_request_round_trip_revalidates_identity():
    _, request, _ = fixtures()
    assert ConstructionActionRequest.from_dict(request.to_dict()) == request
    payload = request.to_dict()
    payload["policy_scope"] = "construction/P1/other"
    with pytest.raises(ValueError):
        ConstructionActionRequest.from_dict(payload)


def test_authority_result_round_trip_revalidates_nested_reports():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    assert ConstructionAuthorityResult.from_dict(
        result.to_dict(),
        request=request,
        state=state,
        governance_decision=decision,
    ) == result
    payload = result.to_dict()
    payload["readiness_reports"][0]["state_digest"] = "f" * 32
    with pytest.raises(ValueError):
        ConstructionAuthorityResult.from_dict(
            payload,
            request=request,
            state=state,
            governance_decision=decision,
        )


def test_receipt_binding_round_trip_revalidates_authority_boundary():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    _, binding = receipt_for(state, request, result, decision)
    assert ConstructionReceiptBinding.from_dict(binding.to_dict()) == binding
    payload = binding.to_dict()
    payload["proposal_only"] = False
    with pytest.raises(ValueError):
        ConstructionReceiptBinding.from_dict(payload)

def test_policy_scope_project_boundary_is_not_prefix_based():
    _, request, _ = fixtures()
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope, action_kind='x', policy_scope='construction/P1evil',
            capability_scope='construction.release', risk_class=RiskClass.HIGH,
            required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
        )


def test_empty_construction_capability_suffix_is_rejected():
    _, request, _ = fixtures()
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope, action_kind='x', policy_scope='construction/P1',
            capability_scope='construction.', risk_class=RiskClass.HIGH,
            required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
        )


def test_quorum_policy_risk_must_match_action_risk():
    state, request, _ = fixtures()
    low = QuorumPolicy.create(
        risk_class=RiskClass.LOW, minimum_approval_count=1,
        required_functional_roles=('OWNER',), minimum_distinct_principals=1,
    )
    with pytest.raises(ValueError):
        evaluate_construction_authority(
            request=request, state=state, grants=(), attestations=(),
            quorum_policy=low, verified_authority_refs=('authority-ref',),
            verified_attestation_refs=('attestation-ref',), now=10,
        )


def test_canonical_evaluator_rejects_cross_project_state():
    state, request, _ = fixtures()
    other_evidence = ConstructionEvidence.create(
        scope=ConstructionScope('P2'), subject_id='wall',
        evidence_class=ConstructionEvidenceClass.DOCUMENT, source_ref='doc',
        payload_digest=D, measurement_class=MeasurementClass.EMPIRICAL,
        confidence=.9, authority_class=ConstructionAuthorityClass.INFORMATIVE,
        privacy_class=ConstructionPrivacyClass.PROJECT, observed_at=1, expires_at=50,
    )
    other_event = ConstructionEvent.create(
        ledger_id='construction/P2', sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST, trace_id='t', record=other_evidence,
        actor_id='h', actor_type=ActorType.HUMAN, created_at=2,
    )
    other_state = replay_construction_events((other_event,))
    with pytest.raises(ValueError):
        evaluate_construction_authority(
            request=request, state=other_state, grants=(), attestations=(),
            quorum_policy=quorum_policy(), verified_authority_refs=('authority-ref',),
            verified_attestation_refs=('attestation-ref',), now=10,
        )


def test_verified_receipt_binding_keys_must_be_normalized():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        receipt_for(
            state, request, result, decision,
            verified_receipt_bindings={' receipt-ref ': result.result_digest},
        )


def test_verified_receipt_binding_digest_must_be_hex():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        receipt_for(
            state, request, result, decision,
            verified_receipt_bindings={'receipt-ref': 'not-a-digest'},
        )


def test_receipt_cannot_predate_authority_evaluation():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError):
        receipt_for(state, request, result, decision, created_at=result.evaluated_at - 1)


def test_action_policy_scope_cannot_target_a_sibling_zone():
    _, request, _ = fixtures()
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope, action_kind="x", policy_scope="construction/P1/Z2",
            capability_scope="construction.release", risk_class=RiskClass.HIGH,
            required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
        )


def test_action_policy_scope_cannot_target_a_sibling_work_package():
    _, request, _ = fixtures()
    with pytest.raises(ValueError):
        ConstructionActionRequest.create(
            scope=request.scope, action_kind="x", policy_scope="construction/P1/Z1/WP2",
            capability_scope="construction.release", risk_class=RiskClass.HIGH,
            required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
        )


def test_action_policy_scope_may_be_an_exact_ancestor_scope():
    _, request, _ = fixtures()
    project = ConstructionActionRequest.create(
        scope=request.scope, action_kind="x", policy_scope="construction/P1",
        capability_scope="construction.release", risk_class=RiskClass.HIGH,
        required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
    )
    zone = ConstructionActionRequest.create(
        scope=request.scope, action_kind="x", policy_scope="construction/P1/Z1",
        capability_scope="construction.release", risk_class=RiskClass.HIGH,
        required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
    )
    exact = ConstructionActionRequest.create(
        scope=request.scope, action_kind="x", policy_scope="construction/P1/Z1/WP1",
        capability_scope="construction.release", risk_class=RiskClass.HIGH,
        required_claim_ids=request.required_claim_ids, created_at=5, expires_at=40,
    )
    assert project.scope == zone.scope == exact.scope


def test_action_request_cannot_be_evaluated_before_creation():
    state, request, _ = fixtures()
    future = ConstructionActionRequest.create(
        scope=request.scope, action_kind=request.action_kind,
        policy_scope=request.policy_scope, capability_scope=request.capability_scope,
        risk_class=RiskClass.HIGH, required_claim_ids=request.required_claim_ids,
        created_at=12, expires_at=40,
    )
    with pytest.raises(ValueError):
        evaluate_construction_authority(
            request=future, state=state, grants=(), attestations=(),
            quorum_policy=quorum_policy(), verified_authority_refs=("authority-ref",),
            verified_attestation_refs=("attestation-ref",), now=10,
        )


def test_result_factory_is_reserved_for_the_canonical_evaluator():
    state, request, _ = fixtures()
    _, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError, match="canonical evaluator"):
        ConstructionAuthorityResult.create(
            request=request, state=state, governance_decision=decision, evaluated_at=10,
        )


def test_persisted_result_cannot_bypass_deterministic_readiness_replay_at_receipt_time():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    fake_report = replace(
        result.readiness_reports[0],
        ready=False,
        blockers=("forged",),
    )
    values = result.to_dict()
    values["readiness_reports"] = [fake_report.to_dict()]
    values["evidence_ready"] = False
    values["digitally_ready"] = False
    values["missing_reasons"] = [f"claim:{fake_report.claim_id}:forged"]
    values.pop("result_id")
    values.pop("result_digest")
    from aura_event_contracts import stable_digest, stable_id
    forged_payload = dict(values)
    forged = ConstructionAuthorityResult(
        result_id=stable_id("construction-authority-result", forged_payload),
        result_digest=stable_digest(forged_payload),
        project_id=values["project_id"], scope_key=values["scope_key"],
        request_id=values["request_id"], request_digest=values["request_digest"],
        required_claim_ids=tuple(values["required_claim_ids"]),
        state_digest=values["state_digest"],
        governance_decision_id=values["governance_decision_id"],
        governance_decision_digest=values["governance_decision_digest"],
        governance_authorized=values["governance_authorized"],
        evidence_ready=values["evidence_ready"], digitally_ready=values["digitally_ready"],
        readiness_reports=(fake_report,), missing_reasons=tuple(values["missing_reasons"]),
        evaluated_at=values["evaluated_at"], expires_at=values["expires_at"],
    )
    assert not forged.digitally_ready
    with pytest.raises(ValueError, match="deterministic readiness replay"):
        create_construction_receipt(
            authority_result=forged, request=request, state=state,
            governance_decision=decision, governance_replay=governance_replay(request),
            ledger_id="construction-authority/P1",
            sequence_number=1, externally_verified_receipt_ref="receipt-ref",
            verified_receipt_bindings={"receipt-ref": forged.result_digest},
            created_at=11,
        )


def test_public_receipt_binding_factory_rejects_foreign_ledger_receipt():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    from aura_relational_authority import ChainedAuthorityReceipt
    receipt = ChainedAuthorityReceipt.create(
        ledger_id="foreign-ledger", sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST, record_id=result.result_id,
        record_digest=result.result_digest, created_at=11,
    )
    with pytest.raises(ValueError, match="construction receipt must use ledger"):
        ConstructionReceiptBinding.create(
            authority_result=result, request=request, state=state,
            governance_decision=decision, governance_replay=governance_replay(request),
            chain_receipt=receipt,
            externally_verified_receipt_ref="receipt-ref",
            verified_receipt_bindings={"receipt-ref": result.result_digest},
            created_at=11,
        )


def test_public_receipt_binding_factory_rejects_backdated_chain_receipt():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    from aura_relational_authority import ChainedAuthorityReceipt
    receipt = ChainedAuthorityReceipt.create(
        ledger_id="construction-authority/P1", sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST, record_id=result.result_id,
        record_digest=result.result_digest, created_at=result.evaluated_at - 1,
    )
    with pytest.raises(ValueError, match="cannot predate"):
        ConstructionReceiptBinding.create(
            authority_result=result, request=request, state=state,
            governance_decision=decision, governance_replay=governance_replay(request),
            chain_receipt=receipt,
            externally_verified_receipt_ref="receipt-ref",
            verified_receipt_bindings={"receipt-ref": result.result_digest},
            created_at=11,
        )


def test_receipt_verifier_rejects_foreign_project_ledger():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    from aura_relational_authority import ChainedAuthorityReceipt
    receipt = ChainedAuthorityReceipt.create(
        ledger_id="construction-authority/P2", sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST, record_id=result.result_id,
        record_digest=result.result_digest, created_at=11,
    )
    with pytest.raises(ValueError, match="construction receipt must use ledger"):
        verify_construction_receipts((receipt,), results_by_id={result.result_id: result})


def test_receipt_verifier_rejects_receipt_after_result_expiry():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    from aura_relational_authority import ChainedAuthorityReceipt
    receipt = ChainedAuthorityReceipt.create(
        ledger_id="construction-authority/P1", sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST, record_id=result.result_id,
        record_digest=result.result_digest, created_at=result.expires_at,
    )
    with pytest.raises(ValueError, match="after authority expiry"):
        verify_construction_receipts((receipt,), results_by_id={result.result_id: result})


def test_receipt_replays_governance_lineage_and_rejects_missing_attestations():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    bad_replay = ConstructionGovernanceReplay.create(
        grants=governance_replay(request).grants,
        attestations=(),
        quorum_policy=quorum_policy(),
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
    )
    with pytest.raises(ValueError, match="lineage replay"):
        create_construction_receipt(
            authority_result=result, request=request, state=state,
            governance_decision=decision, governance_replay=bad_replay,
            ledger_id="construction-authority/P1", sequence_number=1,
            externally_verified_receipt_ref="receipt-ref",
            verified_receipt_bindings={"receipt-ref": result.result_digest},
            created_at=11,
        )


def test_governance_replay_requires_exact_tuple_material():
    replay = governance_replay(fixtures()[1])
    with pytest.raises(ValueError):
        replace(replay, grants=list(replay.grants))

def test_governance_replay_rejects_non_string_optional_identity_fields():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(request)
    with pytest.raises(ValueError):
        ConstructionGovernanceReplay.create(
            grants=grants, attestations=attestations, quorum_policy=policy,
            verified_authority_refs=('authority-ref',),
            verified_attestation_refs=('attestation-ref',),
            proposer_principal_id=123,
        )


def test_governance_replay_reference_order_is_canonical():
    replay = governance_replay(fixtures()[1])
    with pytest.raises(ValueError, match='canonical sorted order'):
        replace(replay, verified_authority_refs=('z-ref', 'a-ref'))


def test_revoked_authority_reference_fails_governance_closed():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(request)
    result, decision = evaluate_construction_authority(
        request=request, state=state, grants=grants, attestations=attestations,
        quorum_policy=policy, verified_authority_refs=('different-ref',),
        verified_attestation_refs=('attestation-ref',), now=10,
    )
    assert not decision.authorized
    assert not result.digitally_ready
    assert any('invalid_attestation' in reason for reason in result.missing_reasons)


def test_revoked_attestation_reference_fails_governance_closed():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(request)
    result, decision = evaluate_construction_authority(
        request=request, state=state, grants=grants, attestations=attestations,
        quorum_policy=policy, verified_authority_refs=('authority-ref',),
        verified_attestation_refs=('different-ref',), now=10,
    )
    assert not decision.authorized
    assert not result.digitally_ready


def test_reloaded_receipt_binding_can_be_revalidated_against_full_lineage():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    receipt, binding = receipt_for(state, request, result, decision)
    loaded = ConstructionReceiptBinding.from_dict(binding.to_dict())
    loaded.validate_against(
        authority_result=result, request=request, state=state,
        governance_decision=decision, governance_replay=governance_replay(request),
        chain_receipt=receipt,
        verified_receipt_bindings={'receipt-ref': result.result_digest},
    )


def test_reloaded_receipt_binding_rejects_wrong_external_digest_binding():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    receipt, binding = receipt_for(state, request, result, decision)
    with pytest.raises(ValueError):
        binding.validate_against(
            authority_result=result, request=request, state=state,
            governance_decision=decision, governance_replay=governance_replay(request),
            chain_receipt=receipt,
            verified_receipt_bindings={'receipt-ref': 'f' * 32},
        )


def test_persisted_authority_request_rejects_numeric_string_timestamp():
    _, request, _ = fixtures()
    payload = request.to_dict()
    payload['created_at'] = '5.0'
    with pytest.raises(ValueError, match='canonical finite float'):
        ConstructionActionRequest.from_dict(payload)


def test_persisted_authority_result_rejects_numeric_string_timestamp():
    state, request, _ = fixtures()
    result, _ = evaluate_ready(state, request)
    payload = result.to_dict()
    payload['evaluated_at'] = '10.0'
    with pytest.raises(ValueError, match='canonical finite float'):
        ConstructionAuthorityResult.from_dict(payload)


def test_persisted_receipt_binding_rejects_numeric_string_timestamp():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    _, binding = receipt_for(state, request, result, decision)
    payload = binding.to_dict()
    payload['created_at'] = '11.0'
    with pytest.raises(ValueError, match='canonical finite float'):
        ConstructionReceiptBinding.from_dict(payload)


def test_capability_scope_rejects_empty_wildcard_and_case_aliases():
    state, request, _ = fixtures()
    for scope_value in (
        'construction..release',
        'construction.*',
        'construction.Release',
        'construction.release.',
    ):
        with pytest.raises(ValueError, match='canonical construction.component'):
            ConstructionActionRequest.create(
                scope=request.scope, action_kind=request.action_kind,
                policy_scope=request.policy_scope, capability_scope=scope_value,
                risk_class=request.risk_class,
                required_claim_ids=request.required_claim_ids,
                created_at=5.0, expires_at=40.0,
            )


def test_authority_evaluation_rejects_boolean_and_string_time_aliases():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(request)
    for invalid_now in (True, '10.0'):
        with pytest.raises(ValueError, match='must be numeric'):
            evaluate_construction_authority(
                request=request, state=state, grants=grants,
                attestations=attestations, quorum_policy=policy,
                verified_authority_refs=('authority-ref',),
                verified_attestation_refs=('attestation-ref',),
                now=invalid_now,
            )


def test_receipt_wrapper_rejects_coerced_sequence_and_noncanonical_previous_digest():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    kwargs = dict(
        authority_result=result, request=request, state=state,
        governance_decision=decision, governance_replay=governance_replay(request),
        ledger_id='construction-authority/P1',
        externally_verified_receipt_ref='receipt-ref',
        verified_receipt_bindings={'receipt-ref': result.result_digest},
        created_at=11.0,
    )
    with pytest.raises(ValueError, match='positive integer'):
        create_construction_receipt(sequence_number='1', **kwargs)
    with pytest.raises(ValueError, match='hexadecimal digest'):
        create_construction_receipt(
            sequence_number=2, previous_chain_digest='not-a-digest', **kwargs
        )

def test_review_hardening_validation_helpers_fail_closed():
    import aura_construction_authority as authority
    import aura_construction_state as construction_state

    scope = ConstructionScope("P1", "Z1", "WP1")
    project_scope = ConstructionScope("P1")
    policy = QuorumPolicy.create(
        risk_class=RiskClass.LOW,
        minimum_approval_count=1,
        required_functional_roles=("OWNER",),
        minimum_distinct_principals=1,
    )
    replay_base = {
        "grants": (),
        "attestations": (),
        "quorum_policy": policy,
        "verified_authority_refs": ("authority-ref",),
        "verified_attestation_refs": ("attestation-ref",),
    }
    invalid_calls = (
        lambda: authority._text(None, "value"),
        lambda: authority._normalized_text_input("", "value"),
        lambda: authority._digest(None, "digest"),
        lambda: authority._digest("A" * 32, "digest"),
        lambda: authority._tuple_strings([], "items"),
        lambda: authority._tuple_strings(("a", "a"), "items"),
        lambda: authority._tuple_strings(("b", "a"), "items"),
        lambda: authority._tuple_strings((), "items", allow_empty=False),
        lambda: authority._normalized_unique("scalar", "items"),
        lambda: authority._normalized_unique((None,), "items"),
        lambda: authority._normalized_unique(("",), "items"),
        lambda: authority._normalized_unique((" a ", "a"), "items"),
        lambda: authority._normalized_unique((), "items", allow_empty=False),
        lambda: authority._verified_digest_bindings({}, "bindings"),
        lambda: authority._timestamp("1", "time"),
        lambda: authority._timestamp(float("inf"), "time"),
        lambda: authority._require_canonical_float(1, "time"),
        lambda: authority._validate_policy_scope(scope, "bad/P1"),
        lambda: authority._validate_policy_scope(scope, "construction/P2"),
        lambda: authority._validate_policy_scope(project_scope, "construction/P1/"),
        lambda: authority._validate_authority_boundary(
            proposal_only=False,
            human_release_required=True,
            physical_work_authorized=False,
            patch_authority=authority.PATCH_AUTHORITY,
            vsa_patch_authority=False,
        ),
        lambda: authority._validate_authority_boundary(
            proposal_only=True,
            human_release_required=True,
            physical_work_authorized=False,
            patch_authority="wrong",
            vsa_patch_authority=False,
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "grants": []}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "attestations": []}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "quorum_policy": object()}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "proposer_principal_id": None}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "normal_policy": object()}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "emergency_reason": None}
        ),
        lambda: construction_state._digest(None, "digest"),
        lambda: construction_state._digest("A" * 32, "digest"),
        lambda: construction_state._timestamp(float("inf"), "time"),
        lambda: construction_state._sequence_input("scalar", "items"),
        lambda: construction_state._tuple_strings([], "items"),
        lambda: construction_state._tuple_strings((None,), "items"),
        lambda: construction_state._tuple_strings((" a ",), "items"),
        lambda: construction_state._tuple_strings(("a", "a"), "items"),
        lambda: construction_state._tuple_strings(("b", "a"), "items"),
    )
    for call in invalid_calls:
        with pytest.raises(ValueError):
            call()

def _freshness_fixture():
    scope = ConstructionScope("P1", "Z1", "WP1")
    evidence = ConstructionEvidence.create(
        scope=scope,
        subject_id="wall",
        evidence_class=ConstructionEvidenceClass.DOCUMENT,
        source_ref="doc",
        payload_digest=D,
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=0.9,
        authority_class=ConstructionAuthorityClass.INFORMATIVE,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        observed_at=1,
        expires_at=12,
    )
    event1 = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        trace_id="trace-freshness",
        record=evidence,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        created_at=2,
    )
    claim = ConstructionClaim.create(
        scope=scope,
        subject_id="wall",
        predicate="installed",
        value_digest=D2,
        claimant_id="contractor",
        evidence_refs=(evidence.evidence_id,),
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=0.8,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        created_at=3,
        expires_at=20,
    )
    event2 = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=2,
        previous_chain_digest=event1.chain_digest,
        trace_id="trace-freshness",
        record=claim,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        parent_event_ids=(event1.event_id,),
        created_at=4,
    )
    state = replay_construction_events((event1, event2))
    request = ConstructionActionRequest.create(
        scope=scope,
        action_kind="release work package",
        policy_scope="construction/P1/Z1",
        capability_scope="construction.release",
        risk_class=RiskClass.HIGH,
        required_claim_ids=(claim.claim_id,),
        created_at=5,
        expires_at=40,
    )
    return state, request


def test_review_hardening_result_expiry_is_capped_by_evidence_freshness():
    state, request = _freshness_fixture()
    result, _ = evaluate_ready(state, request)
    assert result.digitally_ready is True
    assert result.expires_at == 12.0


def test_review_hardening_ready_result_deserialization_requires_context():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError, match="contextual lineage"):
        ConstructionAuthorityResult.from_dict(result.to_dict())
    loaded = ConstructionAuthorityResult.from_dict(
        result.to_dict(), request=request, state=state, governance_decision=decision
    )
    assert loaded == result


def test_review_hardening_evaluator_requires_exact_canonical_types():
    state, request, _ = fixtures()
    grants, attestations, _ = authority_material(request)
    with pytest.raises(ValueError, match="exact QuorumPolicy"):
        evaluate_construction_authority(
            request=request,
            state=state,
            grants=grants,
            attestations=attestations,
            quorum_policy=object(),
            verified_authority_refs=("authority-ref",),
            verified_attestation_refs=("attestation-ref",),
            now=10,
        )


def test_review_hardening_non_genesis_receipt_requires_verified_predecessor():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    first, _ = receipt_for(state, request, result, decision)
    with pytest.raises(ValueError, match="previous receipt or trusted checkpoint"):
        receipt_for(
            state,
            request,
            result,
            decision,
            sequence_number=2,
            previous_chain_digest=first.chain_digest,
            created_at=12,
        )
    second, binding = receipt_for(
        state,
        request,
        result,
        decision,
        sequence_number=2,
        previous_chain_digest=first.chain_digest,
        previous_receipt=first,
        created_at=12,
    )
    binding.validate_against(
        authority_result=result,
        request=request,
        state=state,
        governance_decision=decision,
        governance_replay=governance_replay(request),
        chain_receipt=second,
        verified_receipt_bindings={"receipt-ref": result.result_digest},
        previous_receipt=first,
    )


def test_review_hardening_receipt_verification_rejects_non_ready_results_by_default():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(
        request, decision=AttestationDecision.REJECT
    )
    result, _ = evaluate_construction_authority(
        request=request,
        state=state,
        grants=grants,
        attestations=attestations,
        quorum_policy=policy,
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        now=10,
    )
    receipt = ChainedAuthorityReceipt.create(
        ledger_id="construction-authority/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        record_id=result.result_id,
        record_digest=result.result_digest,
        created_at=11,
    )
    with pytest.raises(ValueError, match="digitally ready"):
        verify_construction_receipts((receipt,), results_by_id={result.result_id: result})
    continuity = verify_construction_receipts(
        (receipt,),
        results_by_id={result.result_id: result},
        require_digitally_ready=False,
    )
    assert continuity.valid is True
