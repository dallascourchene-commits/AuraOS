from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "arena"))

from memory_city_coverage_membrane import AdmissionMode, PositiveTrace, compile_coverage_certificate, compile_proof_carrying_typed_admission
from memory_city_read_consequence import ReadWorldBinding, compile_read_consequence_certificate
from memory_city_support_hydration import SupportClosedHydration
from memory_city_typed_closure import REPROOF_SEMANTICS, TypedClosureCertificate, TypedClosureDisposition
from memory_city_effect_handoff_o13 import (
    EffectHandoffEvidence,
    HandoffDisposition,
    HandoffVerificationContext,
    MutationBoundaryProjection,
    compile_effect_handoff,
)
from memory_city_consequence_refinement import (
    EffectIntent,
    EffectObligationProjection,
    compile_effect_refinement,
    effect_escalation_root,
)
from memory_city_effect_refinement_handoff_o14 import (
    EffectRefinementEvidence,
    EffectRefinementVerificationContext,
    compile_effect_refined_handoff,
)


def hx(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def fixtures(tag: str = "base"):
    hydration = SupportClosedHydration(
        status="READY_SUPPORT_CLOSED_HYDRATION_D0",
        support_cut=("a", "b"),
        missing_objects=(),
        selected_bytes=20,
        universe_bytes=100,
        hydration_fraction=0.2,
        plan_root=hx(f"plan:{tag}"),
        receipt_root=hx(f"hydr:{tag}"),
        support_root=hx(f"support:{tag}"),
    )
    closure = TypedClosureCertificate(
        disposition=TypedClosureDisposition.READY,
        hydration=None,
        support_root=hydration.support_root,
        influence_root=hx(f"influence:{tag}"),
        reproof_item_ids=("a", "b", "c"),
        horizon=2,
        transition_model_root=hx(f"transition:{tag}"),
        future_congruence_root=hx(f"future:{tag}"),
        receipt_root=hx(f"typed:{tag}"),
        reproof_semantics=REPROOF_SEMANTICS,
    )
    binding = ReadWorldBinding(hydration, closure).binding_root
    program = hx(f"program:{tag}")
    domain = hx(f"domain:{tag}")
    positive = (PositiveTrace(binding, program, domain, 7, hx(f"trace:{tag}"), True, True),)
    coverage = compile_coverage_certificate(program_root=program, sealed_domain_root=domain, generation=7, obligations=(binding,), positive=positive)
    cert = compile_read_consequence_certificate((ReadWorldBinding(hydration, closure),), coverage)
    admission = compile_proof_carrying_typed_admission(
        typed_closure_receipt_root=closure.receipt_root,
        coverage=coverage,
        support_root=hydration.support_root,
        influence_root=closure.influence_root,
        transition_model_root=closure.transition_model_root,
        future_congruence_root=closure.future_congruence_root,
        horizon=closure.horizon,
        mode=AdmissionMode.EFFECT_BOUND,
    )
    evidence = EffectHandoffEvidence(hx(f"owner:{tag}"), hx(f"verifier:{tag}"))
    mutation = MutationBoundaryProjection("cell", 4, hx(f"cfg:{tag}"), 8, 17, 17, "worker", 100, hx(f"transition-authority:{tag}"), hx(f"resource-fence:{tag}"))
    verification = HandoffVerificationContext("cell", 4, hx(f"cfg:{tag}"), 8, 17, 17, "worker", 100, hx(f"owner:{tag}"), hx(f"verifier:{tag}"), hx(f"transition-authority:{tag}"), hx(f"resource-fence:{tag}"), 50)
    base_kwargs = dict(
        hydration=hydration,
        typed_closure=closure,
        fixed_support_root=hydration.support_root,
        coverage=coverage,
        current_program_root=program,
        current_sealed_domain_root=domain,
        current_coverage_generation=7,
        admission=admission,
        evidence=evidence,
        mutation=mutation,
        verification=verification,
    )
    intent = EffectIntent(hx(f"intent:{tag}"), hx(f"effect-domain:{tag}"), hx(f"effect-program:{tag}"))
    projection = (EffectObligationProjection(binding, hx(f"obligation:{tag}"), hx(f"obligation-evidence:{tag}"), True, True, hx(f"nuisance:{tag}")),)
    plan = compile_effect_refinement(projection, cert, intent)
    child = plan.subclasses[0]
    refinement = EffectRefinementEvidence(plan, intent, child, hx(f"refinement-owner:{tag}"), hx(f"refinement-verifier:{tag}"))
    refinement_verification = EffectRefinementVerificationContext(
        binding,
        plan.plan_root,
        intent.binding_root,
        child.obligation_root,
        effect_escalation_root(plan, child),
        refinement.owner_receipt_root,
        refinement.verifier_receipt_root,
    )
    return cert, base_kwargs, refinement, refinement_verification


class EffectRefinementHandoffO14Tests(unittest.TestCase):
    def test_full_o13_to_o14_valid_path_routes_to_refined_tecc(self):
        cert, base_kwargs, refinement, current = fixtures()
        o13 = compile_effect_handoff(cert, **base_kwargs)
        o14 = compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current)
        self.assertIs(o13.disposition, HandoffDisposition.HOLD_TECC_REQUIRED_D0)
        self.assertIs(o14.disposition, HandoffDisposition.HOLD_TECC_REQUIRED_D0)
        self.assertNotEqual(o13.tecc_input_root, o14.tecc_input_root)
        self.assertFalse(o14.effect_authority)

    def test_o13_hold_propagates_before_refinement(self):
        cert, base_kwargs, refinement, current = fixtures()
        base_kwargs["verification"] = replace(base_kwargs["verification"], now=100)
        o14 = compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current)
        self.assertEqual(o14.reason, "LEASE_EXPIRED")

    def test_refinement_plan_move_holds(self):
        cert, base_kwargs, refinement, current = fixtures()
        current = replace(current, plan_root=hx("moved-plan"))
        self.assertEqual(compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current).reason, "REFINEMENT_PLAN_MOVED")

    def test_refinement_intent_move_holds(self):
        cert, base_kwargs, refinement, current = fixtures()
        current = replace(current, intent_binding_root=hx("moved-intent"))
        self.assertEqual(compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current).reason, "REFINEMENT_INTENT_MOVED")

    def test_refinement_obligation_move_holds(self):
        cert, base_kwargs, refinement, current = fixtures()
        current = replace(current, obligation_root=hx("moved-obligation"))
        self.assertEqual(compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current).reason, "REFINEMENT_OBLIGATION_MOVED")

    def test_refinement_escalation_move_holds(self):
        cert, base_kwargs, refinement, current = fixtures()
        current = replace(current, escalation_root=hx("moved-escalation"))
        self.assertEqual(compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current).reason, "REFINEMENT_ESCALATION_MOVED")

    def test_refinement_owner_receipt_move_holds(self):
        cert, base_kwargs, refinement, current = fixtures()
        current = replace(current, owner_receipt_root=hx("moved-owner"))
        self.assertEqual(compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current).reason, "REFINEMENT_OWNER_RECEIPT_STALE")

    def test_refinement_verifier_receipt_move_holds(self):
        cert, base_kwargs, refinement, current = fixtures()
        current = replace(current, verifier_receipt_root=hx("moved-verifier"))
        self.assertEqual(compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current).reason, "REFINEMENT_VERIFIER_RECEIPT_STALE")

    def test_active_read_binding_move_holds(self):
        cert, base_kwargs, refinement, current = fixtures()
        current = replace(current, read_binding_root=hx("detached-binding"))
        self.assertEqual(compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement, refinement_verification=current).reason, "REFINEMENT_READ_BINDING_STALE")

    def test_effect_refinement_change_changes_tecc_identity_while_o13_stays_same(self):
        cert, base_kwargs, refinement1, current1 = fixtures("pair")
        o13a = compile_effect_handoff(cert, **base_kwargs)
        intent2 = EffectIntent(hx("alt-intent"), refinement1.intent.effect_domain_root, refinement1.intent.program_root)
        binding = current1.read_binding_root
        projection2 = (EffectObligationProjection(binding, hx("alt-obligation"), hx("alt-evidence"), True, True, hx("alt-nuisance")),)
        plan2 = compile_effect_refinement(projection2, cert, intent2)
        child2 = plan2.subclasses[0]
        refinement2 = EffectRefinementEvidence(plan2, intent2, child2, hx("alt-ref-owner"), hx("alt-ref-verifier"))
        current2 = EffectRefinementVerificationContext(binding, plan2.plan_root, intent2.binding_root, child2.obligation_root, effect_escalation_root(plan2, child2), refinement2.owner_receipt_root, refinement2.verifier_receipt_root)
        o13b = compile_effect_handoff(cert, **base_kwargs)
        o14a = compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement1, refinement_verification=current1)
        o14b = compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement2, refinement_verification=current2)
        self.assertEqual(o13a.tecc_input_root, o13b.tecc_input_root)
        self.assertNotEqual(o14a.tecc_input_root, o14b.tecc_input_root)

    def test_nuisance_only_projection_change_does_not_split_refined_tecc(self):
        cert, base_kwargs, refinement1, current1 = fixtures("nuisance")
        binding = current1.read_binding_root
        projection2 = (EffectObligationProjection(binding, refinement1.child.obligation_root, refinement1.child.evidence_roots[0], True, True, hx("different-nuisance-only")),)
        plan2 = compile_effect_refinement(projection2, cert, refinement1.intent)
        child2 = plan2.subclasses[0]
        refinement2 = EffectRefinementEvidence(plan2, refinement1.intent, child2, refinement1.owner_receipt_root, refinement1.verifier_receipt_root)
        current2 = EffectRefinementVerificationContext(binding, plan2.plan_root, refinement1.intent.binding_root, child2.obligation_root, effect_escalation_root(plan2, child2), refinement2.owner_receipt_root, refinement2.verifier_receipt_root)
        a = compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement1, refinement_verification=current1)
        b = compile_effect_refined_handoff(cert, **base_kwargs, refinement=refinement2, refinement_verification=current2)
        self.assertEqual(a.tecc_input_root, b.tecc_input_root)

    def test_campaign_direct_script_entrypoint_runs(self):
        script = ROOT / "tools" / "arena" / "campaign_memory_city_effect_refinement_handoff_o14.py"
        completed = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True, check=True)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["counts"]["false_tecc"], 0)
        self.assertEqual(payload["counts"]["false_hold"], 0)
        self.assertEqual(payload["counts"]["refined_collision_pairs"], 0)
        self.assertEqual(payload["counts"]["nuisance_false_splits"], 0)


if __name__ == "__main__":
    unittest.main()
