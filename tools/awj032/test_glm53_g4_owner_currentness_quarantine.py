from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g4_prefetch_plan_revalidation import (
    AXES,
    CurrentReuseContext,
    G3PlanProjection,
    HOLD_RECOMPUTE_G3,
    REVALIDATED_UNCHANGED,
    revalidate_g3_plan,
)
from tools.awj032.glm53_g4_owner_currentness_quarantine import (
    HOLD_OWNER_OBSERVATION_AUTH_REQUIRED,
    quarantine_caller_shaped_currentness,
    prove_quarantine_lattice,
)


def d(ch: str) -> str:
    return ch * 64


class GLM53G4OwnerCurrentnessQuarantineTests(unittest.TestCase):
    def plan(self, *, admitted_experts: tuple[int, ...] = (1, 4)) -> G3PlanProjection:
        return G3PlanProjection(
            g3_receipt_digest=d("a"),
            prediction_digest=d("b"),
            layer_id="moe.17",
            binding_digest="binding::glm53::rev::idx",
            admitted_experts=admitted_experts,
            prediction_generation="pred::17",
            calibration_generation="cal::17",
            policy_generation="policy::17",
            source_binding_generation="source::glm53::rev::idx",
            runtime_generation="runtime::vllm::glm53",
            cache_generation="cache::expert::17",
            storage_geometry_generation="storage::nvme::bw-window::17",
            host_profile_generation="host::pcie::gpu::17",
        )

    def echoed_current(self, plan: G3PlanProjection, **changes: str) -> CurrentReuseContext:
        values = {axis: getattr(plan, axis) for axis in AXES}
        values.update(changes)
        return CurrentReuseContext(**values)

    def test_reproduces_base_self_attestation_seam(self) -> None:
        plan = self.plan()
        caller_echo = self.echoed_current(plan)
        base = revalidate_g3_plan(plan=plan, current=caller_echo)
        self.assertEqual(base.disposition, REVALIDATED_UNCHANGED)
        self.assertTrue(base.reusable_without_recompute)

        repaired = quarantine_caller_shaped_currentness(plan=plan, current=caller_echo)
        self.assertEqual(repaired.disposition, HOLD_OWNER_OBSERVATION_AUTH_REQUIRED)
        self.assertTrue(repaired.structural_generation_match)
        self.assertTrue(repaired.independent_owner_observation_required)
        self.assertFalse(repaired.independently_resolved_currentness_proven)
        self.assertFalse(repaired.reusable_without_recompute)

    def test_any_real_label_drift_preserves_base_recompute_hold(self) -> None:
        plan = self.plan()
        for axis in AXES:
            with self.subTest(axis=axis):
                current = self.echoed_current(plan, **{axis: f"{getattr(plan, axis)}::new"})
                base = revalidate_g3_plan(plan=plan, current=current)
                repaired = quarantine_caller_shaped_currentness(plan=plan, current=current)
                self.assertEqual(base.disposition, HOLD_RECOMPUTE_G3)
                self.assertEqual(repaired.disposition, HOLD_RECOMPUTE_G3)
                self.assertEqual(repaired.changed_axes, (axis,))
                self.assertFalse(repaired.structural_generation_match)

    def test_abstention_plan_does_not_escape_currentness_quarantine(self) -> None:
        plan = self.plan(admitted_experts=())
        repaired = quarantine_caller_shaped_currentness(
            plan=plan,
            current=self.echoed_current(plan),
        )
        self.assertEqual(repaired.disposition, HOLD_OWNER_OBSERVATION_AUTH_REQUIRED)
        self.assertFalse(repaired.reusable_without_recompute)

    def test_complete_256_state_lattice_has_zero_reusable_states(self) -> None:
        proof = prove_quarantine_lattice(self.plan())
        self.assertEqual(
            proof,
            {
                "states": 256,
                "owner_observation_holds": 1,
                "recompute_holds": 255,
                "reusable": 0,
            },
        )

    def test_structural_equality_is_not_currentness_proof(self) -> None:
        plan = self.plan()
        repaired = quarantine_caller_shaped_currentness(
            plan=plan,
            current=self.echoed_current(plan),
        )
        self.assertTrue(repaired.structural_generation_match)
        self.assertFalse(repaired.independently_resolved_currentness_proven)

    def test_receipt_is_deterministic(self) -> None:
        plan = self.plan()
        a = quarantine_caller_shaped_currentness(plan=plan, current=self.echoed_current(plan))
        b = quarantine_caller_shaped_currentness(plan=plan, current=self.echoed_current(plan))
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_receipt_cannot_self_mint_currentness_or_reuse(self) -> None:
        plan = self.plan()
        receipt = quarantine_caller_shaped_currentness(plan=plan, current=self.echoed_current(plan))
        with self.assertRaises(ValueError):
            replace(receipt, independently_resolved_currentness_proven=True).validate_claim_ceiling()
        with self.assertRaises(ValueError):
            replace(receipt, reusable_without_recompute=True).validate_claim_ceiling()

    def test_receipt_cannot_widen_authority(self) -> None:
        plan = self.plan()
        receipt = quarantine_caller_shaped_currentness(plan=plan, current=self.echoed_current(plan))
        for field in (
            "plan_executed_by_this_contract",
            "transfer_effect_authorized",
            "native_route_mutated",
            "physical_io_proven",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(receipt, **{field: True}).validate_claim_ceiling()


if __name__ == "__main__":
    unittest.main()
