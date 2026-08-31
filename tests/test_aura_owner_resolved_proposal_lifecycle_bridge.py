from __future__ import annotations

from dataclasses import replace
import unittest

from tools import aura_bounded_proposal_capsule as o63
from tools import aura_closed_world_result_lifecycle_gate as o62
from tools import aura_owner_resolved_proposal_lifecycle_bridge as q20

A="a"*64; B="b"*64; C="c"*64; D="d"*64; E="e"*64; F="f"*64
G="1"*64; H="2"*64; I="3"*64; J="4"*64; K="5"*64; L="6"*64


def basis() -> o63.ProposalBasis:
    eligibility=o63.EligibilityReceiptRef(
        owner_ref="owner:hard-gate-transition:v1",
        transition_id="transition:q20:source",
        domain_id="generic.bounded.c2",
        gate_scope_digest=A,
        source_currentness_root="source-current:q20",
        disposition=o63.ELIGIBILITY_DISPOSITION,
        receipt_digest=B,
        receipt_generation="source-gen-q20",
        policy_generation_ref="eligibility-policy-q20",
        proposal_eligible=True,
        execution_authorized=False,
        provider_effect_authorized=False,
    )
    return o63.ProposalBasis(
        schema_version=o63.BASIS_SCHEMA,
        domain_id="generic.bounded.c2",
        action_kind="REPRESENTATION_SCOPED_PROPOSAL",
        action_parameters_digest=C,
        scientific_scope_digest=D,
        scientific_evidence_generation="science-gen-q20",
        scientific_evidence_receipt_digest=E,
        source_scope_digest=F,
        source_admission_generation="source-gen-q20",
        source_admission_receipt_digest=G,
        request_id="request:q20",
        request_digest=H,
        resource_envelope_digest=I,
        eligibility=eligibility,
        currentness_roots=("source-current:q20","science-current:q20"),
        invalidators=("science-generation-change","source-generation-change","request-envelope-change"),
        authority_scope="D0_NONPROMOTING",
    )


class Resolver:
    def __init__(self, b: o63.ProposalBasis, *, source_current=True):
        self.b=b; self.source_current=source_current
    def resolve_eligibility(self, *, owner_ref, transition_id):
        if owner_ref==self.b.eligibility.owner_ref and transition_id==self.b.eligibility.transition_id:
            return self.b.eligibility
        return None
    def resolve_scientific_evidence(self, *, scope_digest):
        if scope_digest != self.b.scientific_scope_digest: return None
        return o63.ScientificEvidenceState(scope_digest,self.b.scientific_evidence_generation,self.b.scientific_evidence_receipt_digest)
    def resolve_source_admission(self, *, scope_digest):
        if scope_digest != self.b.source_scope_digest: return None
        return o63.SourceAdmissionState(scope_digest,self.b.source_admission_generation,self.b.source_admission_receipt_digest)
    def resolve_request(self, *, request_id):
        if request_id != self.b.request_id: return None
        return o63.RequestOwnerState(request_id,self.b.request_digest,self.b.action_parameters_digest,self.b.resource_envelope_digest)
    def currentness_root_is_current(self, *, root):
        if root == "source-current:q20": return self.source_current
        return True if root in self.b.currentness_roots else None
    def invalidator_is_triggered(self, *, invalidator):
        return False if invalidator in self.b.invalidators else None


def capsule_and_resolver():
    b=basis(); r=Resolver(b)
    g=o63.create_bounded_proposal_capsule(basis=b,producer_identity="worker-parent",owner_resolver=r)
    return g.capsule,r


def model_for(capsule: o63.ProposalCapsule, **changes) -> o62.ModelResultEnvelope:
    objective="Q20"
    result_code="PROPOSAL_LIFECYCLE_EVALUATED"
    pref=q20.proposal_artifact_ref(capsule)
    base=o62.ModelResultEnvelope(
        schema_version=o62.MODEL_SCHEMA,
        objective_id=objective,
        attempt_id="attempt-q20-1",
        worker_id="worker-q20",
        disposition="COMPLETED",
        result_code=result_code,
        claims=(o62.ClaimRef("claim-q20","PROPOSAL_LIFECYCLE_RELATION","bounded",(pref,)),),
        artifact_refs=(pref,"artifact:q20-result"),
        narrative=None,
        output_digest=J,
        source_generation_ref=capsule.basis.source_admission_generation,
        authority_scope=capsule.basis.authority_scope,
        consequence_key=q20.proposal_consequence_key(capsule,objective_id=objective,result_code=result_code),
    )
    return replace(base,**changes)


def policy_for(capsule: o63.ProposalCapsule, **changes) -> o62.LifecyclePolicy:
    base=o62.LifecyclePolicy(
        policy_generation_ref="q20-lifecycle-policy-v1",
        execution_required=False,
        physical_fanout_required=None,
        required_artifact_refs=(q20.proposal_artifact_ref(capsule),),
        required_claim_classes=("PROPOSAL_LIFECYCLE_RELATION",),
        current_source_generation_ref=capsule.basis.source_admission_generation,
        authority_scope=capsule.basis.authority_scope,
        validation_fingerprint=K,
        parent_validation_passed=True,
        contradiction_present=False,
        independent_review_required=False,
        hard_gates=(o62.HardGate("source-current",True),),
        expected_route_fingerprint=None,
        expected_observer_identity=None,
        host_receipt_authority_verified=False,
    )
    return replace(base,**changes)


class Q20ProposalLifecycleBridgeTests(unittest.TestCase):
    def test_exact_owner_resolved_proposal_can_reach_semantic_terminality_without_execution_authority(self):
        c,r=capsule_and_resolver(); m=model_for(c); p=policy_for(c)
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=p)
        self.assertEqual(out.proposal_currentness_state,"CURRENT_NONEXECUTABLE")
        self.assertEqual(out.lifecycle_terminal_state,"TERMINAL_SUCCESS")
        self.assertTrue(out.semantic_commit_eligible)
        self.assertIsNotNone(out.semantic_commit_key)
        self.assertFalse(out.execution_authority_granted)
        self.assertFalse(out.provider_effect_authority_granted)

    def test_stale_owner_currentness_blocks_before_lifecycle(self):
        c,_=capsule_and_resolver(); stale=Resolver(c.basis,source_current=False)
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=stale,model=model_for(c),policy=policy_for(c))
        self.assertEqual(out.lifecycle_terminal_state,"HOLD")
        self.assertEqual(out.lifecycle_reason_code,"PROPOSAL_NOT_CURRENT_OWNER_RESOLVED")
        self.assertFalse(out.semantic_commit_eligible)

    def test_missing_owner_resolver_blocks_before_lifecycle(self):
        c,_=capsule_and_resolver()
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=None,model=model_for(c),policy=policy_for(c))
        self.assertEqual(out.lifecycle_terminal_state,"HOLD")
        self.assertEqual(out.proposal_currentness_reason,"OWNER_RESOLVER_UNAVAILABLE")

    def test_k27_or_other_artifact_cannot_substitute_exact_proposal_ref(self):
        c,r=capsule_and_resolver(); m=model_for(c,artifact_refs=("k27:(4,3,8)","artifact:q20-result"))
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=policy_for(c))
        self.assertEqual(out.lifecycle_reason_code,"PROPOSAL_ARTIFACT_REF_MISSING_FROM_MODEL")
        self.assertFalse(out.proposal_ref_present)

    def test_policy_must_require_exact_proposal_ref(self):
        c,r=capsule_and_resolver(); p=policy_for(c,required_artifact_refs=("artifact:q20-result",))
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=model_for(c),policy=p)
        self.assertEqual(out.lifecycle_reason_code,"PROPOSAL_NOT_REQUIRED_BY_LIFECYCLE_POLICY")

    def test_source_generation_must_match_proposal_and_lifecycle(self):
        c,r=capsule_and_resolver(); m=model_for(c,source_generation_ref="other-source-gen")
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=policy_for(c))
        self.assertEqual(out.lifecycle_reason_code,"PROPOSAL_LIFECYCLE_SOURCE_GENERATION_MISMATCH")

    def test_authority_scope_must_match_proposal_and_lifecycle(self):
        c,r=capsule_and_resolver(); m=model_for(c,authority_scope="D9_EFFECT")
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=policy_for(c))
        self.assertEqual(out.lifecycle_reason_code,"PROPOSAL_LIFECYCLE_AUTHORITY_SCOPE_MISMATCH")

    def test_consequence_key_must_be_bound_to_exact_proposal(self):
        c,r=capsule_and_resolver(); m=model_for(c,consequence_key=L)
        out=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=policy_for(c))
        self.assertEqual(out.lifecycle_reason_code,"PROPOSAL_CONSEQUENCE_KEY_MISMATCH")

    def test_typed_review_remains_owned_by_o62(self):
        c,r=capsule_and_resolver(); m=model_for(c); p=policy_for(c,independent_review_required=True)
        missing=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=p)
        self.assertEqual(missing.lifecycle_terminal_state,"REVIEW")
        self.assertEqual(missing.lifecycle_reason_code,"DISTINCT_REVIEW_REQUIRED")
        review=o62.IndependentReviewReceipt(
            schema_version=o62.REVIEW_SCHEMA,objective_id=m.objective_id,reviewer_id="reviewer-other",
            source_generation_ref=p.current_source_generation_ref,authority_scope=p.authority_scope,
            validation_fingerprint=p.validation_fingerprint,disposition="APPROVE",receipt_digest=L,
        )
        good=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=p,reviewer=review)
        self.assertEqual(good.lifecycle_terminal_state,"TERMINAL_SUCCESS")

    def test_host_witness_remains_owned_by_o62(self):
        c,r=capsule_and_resolver(); m=model_for(c)
        p=policy_for(c,execution_required=True,expected_route_fingerprint="route:q20",expected_observer_identity="HOST",host_receipt_authority_verified=True)
        bad=o62.HostExecutionReceipt(
            schema_version=o62.HOST_SCHEMA,attempt_id=m.attempt_id,output_digest=m.output_digest,
            route_fingerprint="route:wrong",provider_effect_started=True,provider_effect_completed=True,
            physical_fanout_observed=None,transport_state="RETURNED",observer_identity="HOST",receipt_digest=L,
        )
        held=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=p,host=bad)
        self.assertEqual(held.lifecycle_reason_code,"HOST_ROUTE_FINGERPRINT_MISMATCH")
        good=replace(bad,route_fingerprint="route:q20")
        passed=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=p,host=good)
        self.assertEqual(passed.lifecycle_terminal_state,"TERMINAL_SUCCESS")
        self.assertFalse(passed.execution_authority_granted)

    def test_relation_receipt_is_deterministic_and_permanently_nonpromoting(self):
        c,r=capsule_and_resolver(); m=model_for(c); p=policy_for(c)
        first=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=p)
        second=q20.evaluate_owner_resolved_proposal_lifecycle(capsule=c,owner_resolver=r,model=m,policy=p)
        self.assertEqual(first.receipt_digest,second.receipt_digest)
        for key in (
            "execution_authority_granted","provider_effect_authority_granted",
            "semantic_k27_authority_minted","native_private_transformer_kv_accessed",
            "gate10_promoted","merge_deploy_spend_public_human_effect_authorized",
        ):
            self.assertFalse(getattr(first,key),key)


if __name__ == "__main__":
    unittest.main()
