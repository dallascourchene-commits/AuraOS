from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g4_prefetch_plan_revalidation import (
    AXES,
    CurrentReuseContext,
    G3PlanProjection,
    HOLD_RECOMPUTE_G3,
    STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED,
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

    def current(self, plan: G3PlanProjection | None = None, **changes: object) -> CurrentReuseContext:
        p = plan or self.plan()
        values: dict[str, object] = {axis: getattr(p, axis) for axis in AXES}
        values.update(changes)
        return CurrentReuseContext(**values)

    def test_unchanged_labels_are_structural_match_not_reuse_authority(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan(plan=plan, current=self.current(plan))
        self.assertEqual(receipt.disposition, STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED)
        self.assertEqual(receipt.changed_axes, ())
        self.assertTrue(receipt.structural_generation_match)
        self.assertFalse(receipt.recompute_g3_required)
        self.assertTrue(receipt.owner_currentness_authentication_required)
        self.assertFalse(receipt.owner_currentness_authenticated_by_this_contract)
        self.assertFalse(receipt.reuse_authorized_by_this_contract)
        self.assertFalse(receipt.plan_executed_by_this_contract)

    def test_caller_context_cannot_self_mint_owner_authentication(self) -> None:
        with self.assertRaisesRegex(ValueError, "CALLER_CONTEXT_CANNOT_SELF_MINT_OWNER_CURRENTNESS_AUTHENTICATION"):
            self.current(owner_currentness_authenticated=True).validate()

    def test_matching_arbitrary_labels_do_not_authenticate_currentness(self) -> None:
        plan = replace(
            self.plan(),
            prediction_generation="caller::same",
            calibration_generation="caller::same",
            policy_generation="caller::same",
            source_binding_generation="caller::same",
            runtime_generation="caller::same",
            cache_generation="caller::same",
            storage_geometry_generation="caller::same",
            host_profile_generation="caller::same",
        )
        current = CurrentReuseContext(
            prediction_generation="caller::same",
            calibration_generation="caller::same",
            policy_generation="caller::same",
            source_binding_generation="caller::same",
            runtime_generation="caller::same",
            cache_generation="caller::same",
            storage_geometry_generation="caller::same",
            host_profile_generation="caller::same",
        )
        receipt = revalidate_g3_plan(plan=plan, current=current)
        self.assertEqual(receipt.disposition, STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED)
        self.assertFalse(receipt.owner_currentness_authenticated_by_this_contract)
        self.assertFalse(receipt.reuse_authorized_by_this_contract)

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
                self.assertFalse(receipt.structural_generation_match)
                self.assertFalse(receipt.reuse_authorized_by_this_contract)

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

    def test_empty_abstention_plan_still_requires_structural_revalidation(self) -> None:
        plan = self.plan(admitted_experts=())
        unchanged = revalidate_g3_plan(plan=plan, current=self.current(plan))
        self.assertEqual(unchanged.disposition, STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED)
        self.assertFalse(unchanged.reuse_authorized_by_this_contract)
        drifted = revalidate_g3_plan(
            plan=plan,
            current=self.current(plan, source_binding_generation="source::changed"),
        )
        self.assertEqual(drifted.disposition, HOLD_RECOMPUTE_G3)

    def test_finite_drift_lattice_exhausts_256_states_without_authorizing_reuse(self) -> None:
        proof = prove_finite_drift_lattice(self.plan())
        self.assertEqual(
            proof,
            {"states": 256, "structural_matches": 1, "held": 255, "authenticated_reuse_authorizations": 0},
        )

    def test_plan_identity_is_generation_sensitive(self) -> None:
        plan = self.plan()
        self.assertNotEqual(plan.plan_identity_digest, replace(plan, cache_generation="cache::new").plan_identity_digest)

    def test_receipt_is_deterministic(self) -> None:
        plan = self.plan()
        a = revalidate_g3_plan(plan=plan, current=self.current(plan))
        b = revalidate_g3_plan(plan=plan, current=self.current(plan))
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_noncanonical_expert_set_rejected(self) -> None:
        for bad in ((4, 1), (1, 1), (-1,)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.plan(admitted_experts=bad).validate()

    def test_bad_plan_digest_rejected(self) -> None:
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

    def test_receipt_cannot_self_mint_currentness_reuse_or_effect_authority(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current())
        for field in (
            "owner_currentness_authenticated_by_this_contract",
            "reuse_authorized_by_this_contract",
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

    def test_receipt_requires_owner_authentication_gate(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current())
        with self.assertRaises(ValueError):
            replace(receipt, owner_currentness_authentication_required=False).validate_claim_ceiling()

    def test_manual_receipt_cannot_launder_bad_identity_digest(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current())
        with self.assertRaises(ValueError):
            replace(receipt, plan_identity_digest="forged").validate_claim_ceiling()
        with self.assertRaises(ValueError):
            replace(receipt, g3_receipt_digest="forged").validate_claim_ceiling()

    def test_changed_receipt_cannot_claim_structural_match(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current(policy_generation="policy::new"))
        with self.assertRaises(ValueError):
            replace(receipt, structural_generation_match=True).validate_claim_ceiling()

    def test_unchanged_receipt_cannot_claim_recompute(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current())
        with self.assertRaises(ValueError):
            replace(receipt, recompute_g3_required=True).validate_claim_ceiling()

    def test_changed_axes_reject_unknown_and_duplicate_entries(self) -> None:
        receipt = revalidate_g3_plan(plan=self.plan(), current=self.current(policy_generation="policy::new"))
        with self.assertRaises(ValueError):
            replace(receipt, changed_axes=("policy_generation", "policy_generation")).validate_claim_ceiling()
        with self.assertRaises(ValueError):
            replace(receipt, changed_axes=("unknown_generation",)).validate_claim_ceiling()


if __name__ == "__main__":
    unittest.main()
