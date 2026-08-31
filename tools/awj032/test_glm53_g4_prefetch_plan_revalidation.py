from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g4_prefetch_plan_revalidation import (
    AXES,
    G3PlanProjection,
    CurrentReuseContext,
    G4RevalidationReceipt,
    HOLD_RECOMPUTE_G3,
    REVALIDATED_UNCHANGED,
    changed_axes_table,
    changed_axes_tree,
    prove_finite_drift_lattice,
    revalidate_g3_plan,
)


def d(ch: str) -> str:
    return ch * 64


class GLM53G4PrefetchPlanRevalidationTests(unittest.TestCase):
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

    def current(self, plan: G3PlanProjection | None = None, **changes: str) -> CurrentReuseContext:
        p = plan or self.plan()
        values = {axis: getattr(p, axis) for axis in AXES}
        values.update(changes)
        return CurrentReuseContext(**values)

    def test_unchanged_plan_revalidates_without_execution(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan(plan=plan, current=self.current(plan))
        self.assertEqual(receipt.disposition, REVALIDATED_UNCHANGED)
        self.assertEqual(receipt.changed_axes, ())
        self.assertTrue(receipt.reusable_without_recompute)
        self.assertFalse(receipt.recompute_g3_required)
        self.assertFalse(receipt.plan_executed_by_this_contract)
        self.assertFalse(receipt.transfer_effect_authorized)
        self.assertFalse(receipt.physical_io_proven)

    def test_every_single_axis_drift_holds(self) -> None:
        plan = self.plan()
        for axis in AXES:
            with self.subTest(axis=axis):
                receipt = revalidate_g3_plan(
                    plan=plan,
                    current=self.current(plan, **{axis: f"{getattr(plan, axis)}::new"}),
                )
                self.assertEqual(receipt.disposition, HOLD_RECOMPUTE_G3)
                self.assertEqual(receipt.changed_axes, (axis,))
                self.assertTrue(receipt.recompute_g3_required)
                self.assertFalse(receipt.reusable_without_recompute)

    def test_multiple_drift_axes_are_canonical(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan(
            plan=plan,
            current=self.current(
                plan,
                policy_generation="policy::18",
                cache_generation="cache::18",
                host_profile_generation="host::18",
            ),
        )
        self.assertEqual(
            receipt.changed_axes,
            ("policy_generation", "cache_generation", "host_profile_generation"),
        )

    def test_empty_abstention_plan_still_requires_revalidation(self) -> None:
        plan = self.plan(admitted_experts=())
        receipt = revalidate_g3_plan(
            plan=plan,
            current=self.current(plan, source_binding_generation="source::changed"),
        )
        self.assertEqual(receipt.disposition, HOLD_RECOMPUTE_G3)
        self.assertEqual(receipt.changed_axes, ("source_binding_generation",))

    def test_cache_generation_change_cannot_be_laundered_by_same_policy(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan(
            plan=plan,
            current=self.current(plan, cache_generation="cache::evicted-and-rebuilt"),
        )
        self.assertEqual(receipt.disposition, HOLD_RECOMPUTE_G3)

    def test_runtime_change_cannot_be_laundered_by_same_host_profile(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan(
            plan=plan,
            current=self.current(plan, runtime_generation="runtime::new-kernel"),
        )
        self.assertEqual(receipt.changed_axes, ("runtime_generation",))

    def test_storage_geometry_change_reopens_cost_admission(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan(
            plan=plan,
            current=self.current(plan, storage_geometry_generation="storage::new-bandwidth-window"),
        )
        self.assertEqual(receipt.disposition, HOLD_RECOMPUTE_G3)

    def test_source_binding_change_reopens_even_if_prediction_is_same(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan(
            plan=plan,
            current=self.current(plan, source_binding_generation="source::different-revision-index"),
        )
        self.assertEqual(receipt.changed_axes, ("source_binding_generation",))

    def test_different_j_classifiers_commute(self) -> None:
        plan = self.plan()
        current = self.current(
            plan,
            prediction_generation="pred::new",
            calibration_generation="cal::new",
            runtime_generation="runtime::new",
        )
        self.assertEqual(changed_axes_tree(plan, current), changed_axes_table(plan, current))

    def test_finite_drift_lattice_exhausts_256_states(self) -> None:
        proof = prove_finite_drift_lattice(self.plan())
        self.assertEqual(proof, {"states": 256, "unchanged": 1, "held": 255})

    def test_plan_identity_is_generation_sensitive(self) -> None:
        plan = self.plan()
        changed = replace(plan, cache_generation="cache::new")
        self.assertNotEqual(plan.plan_identity_digest, changed.plan_identity_digest)

    def test_plan_identity_is_not_k27_identity(self) -> None:
        plan = self.plan()
        self.assertNotIn("k27", plan.plan_identity_digest.lower())
        self.assertEqual(len(plan.plan_identity_digest), 64)

    def test_receipt_is_deterministic(self) -> None:
        plan = self.plan()
        a = revalidate_g3_plan(plan=plan, current=self.current(plan))
        b = revalidate_g3_plan(plan=plan, current=self.current(plan))
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_noncanonical_expert_set_rejected(self) -> None:
        for bad in ((4, 1), (1, 1), (-1,)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.plan(admitted_experts=bad).validate()

    def test_bad_digest_rejected(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.plan(), g3_receipt_digest="not-a-digest").validate()

    def test_blank_generation_rejected(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.plan(), policy_generation=" ").validate()

    def test_projection_cannot_self_mint_authority(self) -> None:
        for field in (
            "transfer_effect_authorized",
            "native_route_mutated",
            "physical_io_attested",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(self.plan(), **{field: True}).validate()

    def test_revalidation_receipt_cannot_self_mint_authority(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current())
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

    def test_changed_receipt_cannot_claim_reusable(self) -> None:
        receipt = revalidate_g3_plan(
            plan=self.plan(),
            current=self.current(policy_generation="policy::new"),
        )
        with self.assertRaises(ValueError):
            replace(receipt, reusable_without_recompute=True).validate_claim_ceiling()

    def test_unchanged_receipt_cannot_claim_recompute(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current())
        with self.assertRaises(ValueError):
            replace(receipt, recompute_g3_required=True).validate_claim_ceiling()


if __name__ == "__main__":
    unittest.main()
