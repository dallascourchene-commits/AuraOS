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

from memory_city_coverage_membrane import (
    AdmissionMode,
    PositiveTrace,
    compile_coverage_certificate,
    compile_proof_carrying_typed_admission,
)
from memory_city_read_consequence import ReadWorldBinding, compile_read_consequence_certificate
from memory_city_support_hydration import SupportClosedHydration
from memory_city_typed_closure import REPROOF_SEMANTICS, TypedClosureCertificate, TypedClosureDisposition
from memory_city_effect_handoff_o13 import (
    D0,
    EffectHandoffEvidence,
    HandoffDecision,
    HandoffDisposition,
    HandoffVerificationContext,
    MutationBoundaryProjection,
    compile_effect_handoff,
    validate_read_certificate_integrity,
)


def hx(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def fixtures():
    hydration = SupportClosedHydration(
        status="READY_SUPPORT_CLOSED_HYDRATION_D0",
        support_cut=("a", "b"),
        missing_objects=(),
        selected_bytes=20,
        universe_bytes=100,
        hydration_fraction=0.2,
        plan_root=hx("plan"),
        receipt_root=hx("hydr"),
        support_root=hx("support"),
    )
    closure = TypedClosureCertificate(
        disposition=TypedClosureDisposition.READY,
        hydration=None,
        support_root=hydration.support_root,
        influence_root=hx("influence"),
        reproof_item_ids=("a", "b", "c"),
        horizon=2,
        transition_model_root=hx("transition"),
        future_congruence_root=hx("future"),
        receipt_root=hx("typed"),
        reproof_semantics=REPROOF_SEMANTICS,
    )
    binding = ReadWorldBinding(hydration, closure).binding_root
    program = hx("program")
    domain = hx("domain")
    positive = (PositiveTrace(binding, program, domain, 7, hx("trace"), True, True),)
    coverage = compile_coverage_certificate(
        program_root=program,
        sealed_domain_root=domain,
        generation=7,
        obligations=(binding,),
        positive=positive,
    )
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
    evidence = EffectHandoffEvidence(hx("owner"), hx("verifier"))
    mutation = MutationBoundaryProjection(
        "cell", 4, hx("cfg"), 8, 17, 17, "worker", 100, hx("transition-authority"), hx("resource-fence")
    )
    verification = HandoffVerificationContext(
        "cell", 4, hx("cfg"), 8, 17, 17, "worker", 100,
        hx("owner"), hx("verifier"), hx("transition-authority"), hx("resource-fence"), 50,
    )
    kwargs = dict(
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
    return cert, kwargs


class EffectHandoffO13Tests(unittest.TestCase):
    def test_valid_current_owner_state_routes_to_tecc_not_effect_ready(self):
        cert, kwargs = fixtures()
        decision = compile_effect_handoff(cert, **kwargs)
        self.assertIs(decision.disposition, HandoffDisposition.HOLD_TECC_REQUIRED_D0)
        self.assertEqual(decision.required_verifier_schema, "AURA-TECC-v1")
        self.assertFalse(decision.effect_authority)

    def test_current_owner_certificate_integrity_is_recomputable(self):
        cert, _ = fixtures()
        self.assertEqual(validate_read_certificate_integrity(cert), (True, "CURRENT_OWNER_READ_CERTIFICATE_CANONICAL"))

    def test_legacy_reproof_semantics_hold_at_t1(self):
        cert, kwargs = fixtures()
        kwargs["typed_closure"] = replace(kwargs["typed_closure"], reproof_semantics="")
        decision = compile_effect_handoff(cert, **kwargs)
        self.assertEqual(decision.reason, "READ_OWNER_AT_T1_HOLD_REPROOF_SEMANTICS")

    def test_t0_ready_binding_moved_at_t1_holds(self):
        cert, kwargs = fixtures()
        kwargs["typed_closure"] = replace(kwargs["typed_closure"], receipt_root=hx("moved-typed"))
        decision = compile_effect_handoff(cert, **kwargs)
        self.assertEqual(decision.reason, "READ_OWNER_AT_T1_HOLD_ACTIVE_WORLD_MEMBERSHIP")

    def test_holder_substitution_rebinds(self):
        cert, kwargs = fixtures()
        kwargs["mutation"] = replace(kwargs["mutation"], holder="attacker")
        decision = compile_effect_handoff(cert, **kwargs)
        self.assertIs(decision.disposition, HandoffDisposition.REBIND_REQUIRED)
        self.assertEqual(decision.reason, "LEASE_IDENTITY_MOVED")

    def test_expiry_extension_rebinds_even_if_still_unexpired(self):
        cert, kwargs = fixtures()
        kwargs["mutation"] = replace(kwargs["mutation"], expires_at=1000)
        decision = compile_effect_handoff(cert, **kwargs)
        self.assertIs(decision.disposition, HandoffDisposition.REBIND_REQUIRED)
        self.assertEqual(decision.reason, "LEASE_IDENTITY_MOVED")

    def test_unknown_or_extended_admission_is_not_owner_output(self):
        cert, kwargs = fixtures()
        admission = dict(kwargs["admission"])
        admission["schema"] = "UNKNOWN"
        kwargs["admission"] = admission
        self.assertEqual(compile_effect_handoff(cert, **kwargs).reason, "ADMISSION_NOT_EXACT_CURRENT_OWNER_OUTPUT")

    def test_missing_authority_field_is_not_owner_output(self):
        cert, kwargs = fixtures()
        admission = dict(kwargs["admission"])
        admission.pop("effect_authority")
        kwargs["admission"] = admission
        self.assertEqual(compile_effect_handoff(cert, **kwargs).reason, "ADMISSION_NOT_EXACT_CURRENT_OWNER_OUTPUT")

    def test_authority_bearing_read_certificate_holds(self):
        cert, kwargs = fixtures()
        decision = compile_effect_handoff(replace(cert, effect_authority=True), **kwargs)
        self.assertEqual(decision.reason, "READ_CERTIFICATE_AUTHORITY_ESCALATION")

    def test_forged_consequence_root_holds(self):
        cert, kwargs = fixtures()
        decision = compile_effect_handoff(replace(cert, consequence_root=hx("forged")), **kwargs)
        self.assertEqual(decision.reason, "READ_CERTIFICATE_CONSEQUENCE_ROOT_FORGED")

    def test_forged_read_receipt_holds(self):
        cert, kwargs = fixtures()
        decision = compile_effect_handoff(replace(cert, receipt_root=hx("forged-receipt")), **kwargs)
        self.assertEqual(decision.reason, "READ_CERTIFICATE_RECEIPT_ROOT_FORGED")

    def test_negative_timestamps_fail_construction(self):
        with self.assertRaises(ValueError):
            MutationBoundaryProjection("cell", 4, hx("cfg"), 8, 17, 17, "worker", -1, hx("ta"), hx("rf"))
        with self.assertRaises(ValueError):
            HandoffVerificationContext("cell", 4, hx("cfg"), 8, 17, 17, "worker", 100, hx("owner"), hx("ver"), hx("ta"), hx("rf"), -1)

    def test_expired_lease_holds(self):
        cert, kwargs = fixtures()
        kwargs["verification"] = replace(kwargs["verification"], now=100)
        self.assertEqual(compile_effect_handoff(cert, **kwargs).reason, "LEASE_EXPIRED")

    def test_uninstalled_fence_holds(self):
        cert, kwargs = fixtures()
        kwargs["mutation"] = replace(kwargs["mutation"], installed_fence_generation=16)
        kwargs["verification"] = replace(kwargs["verification"], installed_fence_generation=16)
        self.assertEqual(compile_effect_handoff(cert, **kwargs).reason, "FENCE_NOT_INSTALLED_CURRENT")

    def test_decision_cannot_claim_non_d0_authority(self):
        with self.assertRaises(ValueError):
            HandoffDecision(HandoffDisposition.HOLD, "x", authority="OTHER")

    def test_campaign_direct_script_entrypoint_runs_with_exact_oracle(self):
        script = ROOT / "tools" / "arena" / "campaign_memory_city_effect_handoff_o13.py"
        completed = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True, check=True)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["false_tecc_route"], 0)
        self.assertEqual(payload["false_hold"], 0)
        self.assertEqual(payload["disposition_mismatches"], 0)
        self.assertEqual(payload["reason_mismatches"], 0)
        self.assertEqual(payload["oracle_mismatches"], 0)
        self.assertTrue(payload["oracle_self_test_pass"])
        self.assertEqual(payload["effect_ready"], 0)
        self.assertEqual(payload["by_mode"]["3"]["rebind"], 3000)
        self.assertEqual(payload["by_mode"]["3"]["hold"], 0)
        self.assertEqual(payload["by_mode"]["4"]["rebind"], 3000)
        self.assertEqual(payload["by_mode"]["4"]["hold"], 0)


if __name__ == "__main__":
    unittest.main()
