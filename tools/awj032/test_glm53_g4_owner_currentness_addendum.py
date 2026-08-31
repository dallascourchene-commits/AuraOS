from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.awj032.glm53_g4_prefetch_plan_revalidation import (
    AXES,
    CurrentReuseContext,
    G3PlanProjection,
)
from tools.awj032.glm53_g4_owner_currentness_addendum import (
    HOLD_OWNER_CURRENTNESS_REQUIRED,
    HOLD_OWNER_STATE_EPOCH_CHANGED,
    HOLD_RECOMPUTE_G3_OWNER_RESOLVED,
    RESOLVER_MATCHED_EXTERNAL_TRUST_REQUIRED,
    OwnerReuseStateObservation,
    revalidate_g3_plan_owner_resolved,
)


def d(ch: str) -> str:
    return ch * 64


class FakeResolver:
    """Test double only; Protocol shape proves neither authentication nor epoch truth."""

    def __init__(
        self,
        *,
        plan: G3PlanProjection,
        context: CurrentReuseContext | None = None,
        epochs: tuple[str | None, ...] = ("epoch::1", "epoch::1"),
        observation_plan_identity: str | None = None,
        observation_epoch: str = "epoch::1",
        resolver_generation: str = "resolver::1",
        raise_epoch: bool = False,
        raise_state: bool = False,
    ) -> None:
        self.plan = plan
        self.context = context or CurrentReuseContext(
            **{axis: getattr(plan, axis) for axis in AXES}
        )
        self.epochs = list(epochs)
        self.observation_plan_identity = observation_plan_identity
        self.observation_epoch = observation_epoch
        self.resolver_generation = resolver_generation
        self.raise_epoch = raise_epoch
        self.raise_state = raise_state

    def resolve_g4_state_epoch(self, *, plan_identity_digest: str) -> str | None:
        if self.raise_epoch:
            raise RuntimeError("epoch unavailable")
        if not self.epochs:
            return None
        return self.epochs.pop(0)

    def resolve_g4_reuse_state(
        self, *, plan_identity_digest: str
    ) -> OwnerReuseStateObservation | None:
        if self.raise_state:
            raise RuntimeError("state unavailable")
        return OwnerReuseStateObservation(
            plan_identity_digest=(
                self.observation_plan_identity or self.plan.plan_identity_digest
            ),
            owner_state_epoch=self.observation_epoch,
            resolver_generation=self.resolver_generation,
            context=self.context,
        )


class G4OwnerCurrentnessAddendumTests(unittest.TestCase):
    def plan(self) -> G3PlanProjection:
        return G3PlanProjection(
            g3_receipt_digest=d("a"),
            prediction_digest=d("b"),
            layer_id="moe.17",
            binding_digest="binding::glm53::rev::idx",
            admitted_experts=(1, 4),
            prediction_generation="pred::17",
            calibration_generation="cal::17",
            policy_generation="policy::17",
            source_binding_generation="source::17",
            runtime_generation="runtime::17",
            cache_generation="cache::17",
            storage_geometry_generation="storage::17",
            host_profile_generation="host::17",
        )

    def current(self, plan: G3PlanProjection, **changes: str) -> CurrentReuseContext:
        values = {axis: getattr(plan, axis) for axis in AXES}
        values.update(changes)
        return CurrentReuseContext(**values)

    def test_public_api_accepts_owner_resolver_not_raw_context(self) -> None:
        sig = inspect.signature(revalidate_g3_plan_owner_resolved)
        self.assertEqual(tuple(sig.parameters), ("plan", "owner_resolver"))
        self.assertNotIn("current", sig.parameters)

    def test_missing_owner_resolver_fails_closed(self) -> None:
        receipt = revalidate_g3_plan_owner_resolved(
            plan=self.plan(), owner_resolver=None
        )
        self.assertEqual(receipt.disposition, HOLD_OWNER_CURRENTNESS_REQUIRED)
        self.assertFalse(receipt.reusable_without_recompute)

    def test_matching_fake_resolver_is_candidate_not_reuse_authority(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan)
        )
        self.assertEqual(receipt.disposition, RESOLVER_MATCHED_EXTERNAL_TRUST_REQUIRED)
        self.assertTrue(receipt.owner_context_resolved)
        self.assertTrue(receipt.owner_state_epoch_stable)
        self.assertFalse(receipt.reusable_without_recompute)
        self.assertFalse(receipt.recompute_g3_required)
        self.assertTrue(receipt.external_resolver_trust_required)
        self.assertFalse(receipt.owner_resolver_authenticated_by_this_contract)
        self.assertFalse(receipt.owner_currentness_truth_proven_by_this_contract)
        self.assertTrue(receipt.owner_epoch_change_complete_required)
        self.assertFalse(receipt.owner_epoch_change_complete_proven_by_this_contract)
        self.assertFalse(receipt.plan_executed_by_this_contract)

    def test_arbitrary_matching_fake_resolver_cannot_authorize_reuse(self) -> None:
        plan = replace(
            self.plan(),
            prediction_generation="fake::same",
            calibration_generation="fake::same",
            policy_generation="fake::same",
            source_binding_generation="fake::same",
            runtime_generation="fake::same",
            cache_generation="fake::same",
            storage_geometry_generation="fake::same",
            host_profile_generation="fake::same",
        )
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan)
        )
        self.assertEqual(receipt.disposition, RESOLVER_MATCHED_EXTERNAL_TRUST_REQUIRED)
        self.assertFalse(receipt.reusable_without_recompute)
        self.assertFalse(receipt.owner_resolver_authenticated_by_this_contract)

    def test_owner_resolved_axis_drift_requires_g3_recompute(self) -> None:
        plan = self.plan()
        resolver = FakeResolver(
            plan=plan,
            context=self.current(plan, cache_generation="cache::18"),
        )
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=resolver
        )
        self.assertEqual(receipt.disposition, HOLD_RECOMPUTE_G3_OWNER_RESOLVED)
        self.assertEqual(receipt.changed_axes, ("cache_generation",))
        self.assertTrue(receipt.recompute_g3_required)
        self.assertFalse(receipt.reusable_without_recompute)

    def test_epoch_drift_after_owner_read_fails_closed(self) -> None:
        plan = self.plan()
        resolver = FakeResolver(plan=plan, epochs=("epoch::1", "epoch::2"))
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=resolver
        )
        self.assertEqual(receipt.disposition, HOLD_OWNER_STATE_EPOCH_CHANGED)
        self.assertFalse(receipt.reusable_without_recompute)

    def test_observation_must_belong_to_open_epoch(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan,
            owner_resolver=FakeResolver(plan=plan, observation_epoch="epoch::other"),
        )
        self.assertEqual(receipt.disposition, HOLD_OWNER_STATE_EPOCH_CHANGED)

    def test_observation_must_bind_exact_plan_identity(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan,
            owner_resolver=FakeResolver(plan=plan, observation_plan_identity=d("c")),
        )
        self.assertEqual(receipt.disposition, HOLD_OWNER_CURRENTNESS_REQUIRED)
        self.assertEqual(
            receipt.reason_code, "OWNER_REUSE_STATE_PLAN_IDENTITY_MISMATCH"
        )

    def test_epoch_resolver_error_is_not_converted_to_currentness(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan, raise_epoch=True)
        )
        self.assertEqual(receipt.disposition, HOLD_OWNER_CURRENTNESS_REQUIRED)

    def test_state_resolver_error_is_not_converted_to_currentness(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan, raise_state=True)
        )
        self.assertEqual(receipt.disposition, HOLD_OWNER_CURRENTNESS_REQUIRED)

    def test_owner_observation_identity_is_generation_sensitive(self) -> None:
        plan = self.plan()
        a = OwnerReuseStateObservation(
            plan_identity_digest=plan.plan_identity_digest,
            owner_state_epoch="epoch::1",
            resolver_generation="resolver::1",
            context=self.current(plan),
        )
        b = replace(a, resolver_generation="resolver::2")
        self.assertNotEqual(a.observation_digest, b.observation_digest)

    def test_receipt_cannot_disable_external_trust_requirement(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan)
        )
        with self.assertRaises(ValueError):
            replace(receipt, external_resolver_trust_required=False).validate_claim_ceiling()

    def test_receipt_cannot_self_authenticate_or_mint_effect_authority(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan)
        )
        for field in (
            "owner_resolver_authenticated_by_this_contract",
            "owner_currentness_truth_proven_by_this_contract",
            "owner_epoch_change_complete_proven_by_this_contract",
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

    def test_epoch_change_complete_requirement_cannot_be_disabled(self) -> None:
        plan = self.plan()
        receipt = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan)
        )
        with self.assertRaises(ValueError):
            replace(
                receipt, owner_epoch_change_complete_required=False
            ).validate_claim_ceiling()

    def test_no_disposition_from_this_contract_can_claim_reusable(self) -> None:
        plan = self.plan()
        candidate = revalidate_g3_plan_owner_resolved(
            plan=plan, owner_resolver=FakeResolver(plan=plan)
        )
        with self.assertRaises(ValueError):
            replace(candidate, reusable_without_recompute=True).validate_claim_ceiling()
        hold = revalidate_g3_plan_owner_resolved(plan=plan, owner_resolver=None)
        with self.assertRaises(ValueError):
            replace(hold, reusable_without_recompute=True).validate_claim_ceiling()


if __name__ == "__main__":
    unittest.main()
