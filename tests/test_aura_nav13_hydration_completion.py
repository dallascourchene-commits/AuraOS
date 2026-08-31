from __future__ import annotations

from dataclasses import replace
import hashlib
import unittest

from tools.aura_fractal_k27 import K27Path
from tools.aura_nav13_lawfield import LawFieldOverlay, root_law_field
from tools.aura_nav13_minimum_hydration import (
    ROUTE_PROJECTION_SCHEMA,
    SOURCE_PROJECTION_SCHEMA,
    EpistemicRouteProjection,
    EvidenceRequirement,
    HydrationLevel,
    HydrationSourceProjection,
    PlanDisposition,
    compile_minimum_hydration_route,
)
from tools.aura_nav13_hydration_completion import (
    OBSERVATION_SCHEMA,
    CompletionDisposition,
    HydrationObservationProjection,
    bind_hydration_completion,
)


def d(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def law(*, generation: str = "law-g1"):
    return root_law_field(
        LawFieldOverlay(
            path=K27Path.parse("K27:/11.17.15"),
            owner_ref="owner:nav13",
            rule_generation=generation,
            hard_constraints_add=("NO_EFFECT",),
            allowed_actions_limit=("HYDRATE", "READ"),
            required_evidence_add=("REQ-A",),
            authority_scopes_limit=("NAVIGATE",),
            effect_scopes_limit=("READ_ONLY",),
            domain_roles=("EVIDENCE",),
            evidence_state_digest=d("evidence"),
            authority_state_digest=d("authority"),
            temporal_state_digest=d("temporal"),
            provider_policy_digest=d("provider"),
        )
    )


def plan_for(current_law=None):
    current_law = current_law or law()
    route = EpistemicRouteProjection(
        schema=ROUTE_PROJECTION_SCHEMA,
        state="EXTERNAL_UNHYDRATED",
        next_transition="HYDRATE_MINIMUM",
        route_receipt_digest=d("route"),
    )
    req = EvidenceRequirement(
        requirement_id="REQ-A",
        semantic_key="source:A",
        minimum_level=HydrationLevel.L3,
        currentness_required=True,
        exact_source_required=True,
    )
    source = HydrationSourceProjection(
        schema=SOURCE_PROJECTION_SCHEMA,
        semantic_key="source:A",
        subject_key=d("subject"),
        evidence_generation_key=d("generation"),
        knowledge_node_digest=d("node"),
        validation_fingerprint=d("validation"),
        reader_receipt_digest=d("reader"),
        knowledge_state="CURRENT_REFERENCE",
        reader_disposition="FOUND_VERIFIED",
        source_currentness="RESOLVED_CURRENT",
        available_level=HydrationLevel.L1,
        exact_source_uri="https://example.org/source-a?v=1",
        evidence_domain="EXTERNAL_RESEARCH",
        principal="navigator:nav13",
        k27_placement_hint=(1, 2, 3),
    )
    plan = compile_minimum_hydration_route(
        law=current_law,
        epistemic_route=route,
        requirements=(req,),
        sources=(source,),
    )
    assert plan.disposition is PlanDisposition.HYDRATE_MINIMUM
    assert len(plan.steps) == 1
    return plan


def observation(plan, **updates):
    step = plan.steps[0]
    base = dict(
        schema=OBSERVATION_SCHEMA,
        semantic_plan_digest=plan.semantic_plan_digest,
        step_semantic_identity=step.semantic_identity,
        semantic_key=step.semantic_key,
        requirement_ids=step.requirement_ids,
        subject_key=step.subject_key,
        evidence_generation_key=step.evidence_generation_key,
        knowledge_node_digest=step.knowledge_node_digest,
        validation_fingerprint=step.validation_fingerprint,
        exact_source_uri=step.exact_source_uri,
        achieved_level=step.target_level,
        material_digest=d("material"),
        materialization_receipt_digest=d("materialization-receipt"),
        currentness_witness_digest=d("currentness-witness"),
        currentness_generation="currentness:g1",
        source_currentness="RESOLVED_CURRENT",
        observer_ref="owner:external-hydrator",
        observer_generation="hydrator:g1",
    )
    base.update(updates)
    return HydrationObservationProjection(**base)


class HydrationCompletionBindingTests(unittest.TestCase):
    def test_exact_current_observation_binds_completion_without_promotion(self):
        current_law = law()
        plan = plan_for(current_law)
        obs = observation(plan)
        receipt = bind_hydration_completion(
            law=current_law,
            plan=plan,
            observations=(obs,),
        )
        self.assertEqual(CompletionDisposition.BOUND_COMPLETE, receipt.disposition)
        self.assertTrue(receipt.hydration_obligation_satisfied)
        self.assertEqual((plan.steps[0].semantic_identity,), receipt.completed_step_identities)
        self.assertEqual(("REQ-A",), receipt.requirement_ids)
        self.assertFalse(receipt.observer_authenticated_by_this_contract)
        self.assertFalse(receipt.source_truth_proven)
        self.assertFalse(receipt.evidence_admitted)
        self.assertFalse(receipt.authorization_issued)
        self.assertFalse(receipt.materialization_executed_by_this_contract)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.effect_executed)
        self.assertFalse(receipt.semantic_k27_authority)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)
        self.assertEqual(64, len(receipt.completion_digest))

    def test_missing_or_extra_observation_fails_closed(self):
        current_law = law()
        plan = plan_for(current_law)
        missing = bind_hydration_completion(law=current_law, plan=plan, observations=())
        self.assertEqual(CompletionDisposition.HOLD_OBSERVATION_SET_MISMATCH, missing.disposition)
        extra = replace(observation(plan), step_semantic_identity=d("other-step"))
        out = bind_hydration_completion(
            law=current_law,
            plan=plan,
            observations=(observation(plan), extra),
        )
        self.assertEqual(CompletionDisposition.HOLD_OBSERVATION_SET_MISMATCH, out.disposition)

    def test_plan_digest_substitution_rejected(self):
        current_law = law()
        plan = plan_for(current_law)
        out = bind_hydration_completion(
            law=current_law,
            plan=plan,
            observations=(observation(plan, semantic_plan_digest=d("wrong-plan")),),
        )
        self.assertEqual(CompletionDisposition.HOLD_STEP_IDENTITY_MISMATCH, out.disposition)

    def test_source_generation_substitution_rejected(self):
        current_law = law()
        plan = plan_for(current_law)
        out = bind_hydration_completion(
            law=current_law,
            plan=plan,
            observations=(observation(plan, evidence_generation_key=d("generation-v2")),),
        )
        self.assertEqual(CompletionDisposition.HOLD_SOURCE_GENERATION_MISMATCH, out.disposition)

    def test_stale_or_unknown_currentness_rejected(self):
        current_law = law()
        plan = plan_for(current_law)
        for state in ("STALE", "UNKNOWN"):
            with self.subTest(state=state):
                out = bind_hydration_completion(
                    law=current_law,
                    plan=plan,
                    observations=(observation(plan, source_currentness=state),),
                )
                self.assertEqual(CompletionDisposition.HOLD_CURRENTNESS_UNRESOLVED, out.disposition)

    def test_under_hydration_rejected(self):
        current_law = law()
        plan = plan_for(current_law)
        out = bind_hydration_completion(
            law=current_law,
            plan=plan,
            observations=(observation(plan, achieved_level=HydrationLevel.L2),),
        )
        self.assertEqual(CompletionDisposition.HOLD_LEVEL_INSUFFICIENT, out.disposition)

    def test_step_structure_substitution_rejected(self):
        current_law = law()
        plan = plan_for(current_law)
        for field, value in (
            ("semantic_key", "source:B"),
            ("requirement_ids", ("REQ-B",)),
            ("subject_key", d("other-subject")),
            ("knowledge_node_digest", d("other-node")),
            ("validation_fingerprint", d("other-validation")),
            ("exact_source_uri", "https://example.org/source-a?v=2"),
        ):
            with self.subTest(field=field):
                out = bind_hydration_completion(
                    law=current_law,
                    plan=plan,
                    observations=(observation(plan, **{field: value}),),
                )
                self.assertEqual(CompletionDisposition.HOLD_STEP_IDENTITY_MISMATCH, out.disposition)

    def test_lawfield_drift_rejected(self):
        original_law = law()
        plan = plan_for(original_law)
        changed_law = law(generation="law-g2")
        out = bind_hydration_completion(
            law=changed_law,
            plan=plan,
            observations=(observation(plan),),
        )
        self.assertEqual(CompletionDisposition.HOLD_STEP_IDENTITY_MISMATCH, out.disposition)
        self.assertFalse(out.hydration_obligation_satisfied)

    def test_non_hydration_plan_cannot_self_claim_completion(self):
        current_law = law()
        route = EpistemicRouteProjection(
            schema=ROUTE_PROJECTION_SCHEMA,
            state="KNOWN_CURRENT",
            next_transition="NONE",
            route_receipt_digest=d("route-ready"),
        )
        req = EvidenceRequirement(
            requirement_id="REQ-A",
            semantic_key="source:A",
            minimum_level=HydrationLevel.L3,
        )
        source = HydrationSourceProjection(
            schema=SOURCE_PROJECTION_SCHEMA,
            semantic_key="source:A",
            subject_key=d("subject"),
            evidence_generation_key=d("generation"),
            knowledge_node_digest=d("node"),
            validation_fingerprint=d("validation"),
            reader_receipt_digest=d("reader"),
            knowledge_state="CURRENT_REFERENCE",
            reader_disposition="FOUND_VERIFIED",
            source_currentness="RESOLVED_CURRENT",
            available_level=HydrationLevel.L3,
            exact_source_uri="https://example.org/source-a?v=1",
            evidence_domain="EXTERNAL_RESEARCH",
            principal="navigator:nav13",
        )
        ready = compile_minimum_hydration_route(
            law=current_law,
            epistemic_route=route,
            requirements=(req,),
            sources=(source,),
        )
        self.assertEqual(PlanDisposition.READY_NO_HYDRATION, ready.disposition)
        out = bind_hydration_completion(law=current_law, plan=ready, observations=())
        self.assertEqual(CompletionDisposition.HOLD_PLAN_NOT_HYDRATABLE, out.disposition)

    def test_observation_authority_widening_raises(self):
        plan = plan_for(law())
        for field in (
            "source_truth_proven",
            "evidence_admitted",
            "instruction_authority",
            "authorization_issued",
            "write_authority",
            "effect_authorized",
            "effect_executed",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "HYDRATION_OBSERVATION_EXCEEDED_NONPROMOTION_CEILING"):
                    observation(plan, **{field: True}).validate()

    def test_completion_identity_is_deterministic_and_currentness_witness_bearing(self):
        current_law = law()
        plan = plan_for(current_law)
        a = bind_hydration_completion(law=current_law, plan=plan, observations=(observation(plan),))
        b = bind_hydration_completion(law=current_law, plan=plan, observations=(observation(plan),))
        c = bind_hydration_completion(
            law=current_law,
            plan=plan,
            observations=(observation(plan, currentness_witness_digest=d("currentness-witness-v2")),),
        )
        self.assertEqual(a.completion_digest, b.completion_digest)
        self.assertNotEqual(a.completion_digest, c.completion_digest)


if __name__ == "__main__":
    unittest.main()
