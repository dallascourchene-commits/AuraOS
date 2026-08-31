from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_g5_recompute_admission import (
    ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT,
    ALLOW_STATE_TRANSITION,
    G4_HOLD_RECOMPUTE,
    G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED,
    G4V2RevalidationProjection,
    AliasStableProgressProjection,
    assess_g3_recompute_admission,
)
from tools.awj032.glm53_g5_owner_resolved_recompute_premise import (
    BASE_G5_HOLD,
    HOLD_G4_OWNER_EPOCH_CHANGED,
    HOLD_G4_OWNER_OBSERVATION_MISMATCH,
    HOLD_G4_OWNER_RESOLVED_DRIFT_REQUIRED,
    OWNER_RESOLVED_G4_HOLD,
    OWNER_RESOLVED_RECOMPUTE_CANDIDATE,
    OwnerResolvedG4DriftObservation,
    assess_owner_resolved_recompute_premise,
)


def d(ch: str) -> str:
    return ch * 64


def g4_runtime_drift() -> G4V2RevalidationProjection:
    return G4V2RevalidationProjection(
        receipt_digest=d("a"),
        disposition=G4_HOLD_RECOMPUTE,
        changed_axes=("runtime_generation",),
        frozen_source_binding_generation="source::17",
        current_source_binding_generation="source::17",
    )


def g4_structural_match() -> G4V2RevalidationProjection:
    return G4V2RevalidationProjection(
        receipt_digest=d("b"),
        disposition=G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED,
        changed_axes=(),
        frozen_source_binding_generation="source::17",
        current_source_binding_generation="source::17",
    )


def progress() -> AliasStableProgressProjection:
    return AliasStableProgressProjection(
        receipt_digest=d("c"),
        decision=ALLOW_STATE_TRANSITION,
        semantic_fingerprint_digest=d("d"),
        source_sid="sid::glm53",
        provider_state_generation="provider::18",
        evidence_digest=d("e"),
        route_projection_changed=False,
        source_sid_same=True,
        alias_projection_required=False,
        alias_projection_consumed=False,
        raw_decision=ALLOW_STATE_TRANSITION,
        semantic_decision=ALLOW_STATE_TRANSITION,
    )


def observation(g4: G4V2RevalidationProjection, *, epoch: str = "epoch::17") -> OwnerResolvedG4DriftObservation:
    return OwnerResolvedG4DriftObservation(
        observation_digest=d("f"),
        g4_receipt_digest=g4.receipt_digest,
        disposition=OWNER_RESOLVED_G4_HOLD,
        changed_axes=g4.changed_axes,
        frozen_source_binding_generation=g4.frozen_source_binding_generation,
        current_source_binding_generation=g4.current_source_binding_generation,
        owner_state_epoch=epoch,
        owner_resolver_generation="resolver::17",
    )


class StableResolver:
    def __init__(self, obs: OwnerResolvedG4DriftObservation) -> None:
        self.obs = obs

    def resolve_state_epoch(self, *, g4_receipt_digest: str) -> str:
        assert g4_receipt_digest == self.obs.g4_receipt_digest
        return self.obs.owner_state_epoch

    def resolve_g4_drift(self, *, g4_receipt_digest: str) -> OwnerResolvedG4DriftObservation:
        assert g4_receipt_digest == self.obs.g4_receipt_digest
        return self.obs


class DriftingResolver(StableResolver):
    def __init__(self, obs: OwnerResolvedG4DriftObservation) -> None:
        super().__init__(obs)
        self.calls = 0

    def resolve_state_epoch(self, *, g4_receipt_digest: str) -> str:
        self.calls += 1
        return "epoch::17" if self.calls == 1 else "epoch::18"


class G5OwnerResolvedRecomputePremiseTests(unittest.TestCase):
    def test_reproduces_raw_projection_admission_seam(self) -> None:
        raw = assess_g3_recompute_admission(g4=g4_runtime_drift(), progress=progress())
        self.assertEqual(raw.disposition, ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT)
        self.assertTrue(raw.bounded_g3_recompute_attempt_admitted)

    def test_raw_structural_drift_alone_is_quarantined(self) -> None:
        gated = assess_owner_resolved_recompute_premise(g4=g4_runtime_drift(), progress=progress())
        self.assertEqual(gated.disposition, HOLD_G4_OWNER_RESOLVED_DRIFT_REQUIRED)
        self.assertFalse(gated.raw_structural_projection_sufficient)
        self.assertFalse(gated.owner_resolved_recompute_candidate)
        self.assertFalse(gated.bounded_g3_recompute_attempt_admitted_by_this_contract)

    def test_exact_stable_owner_resolution_yields_candidate_only(self) -> None:
        g4 = g4_runtime_drift()
        gated = assess_owner_resolved_recompute_premise(
            g4=g4,
            progress=progress(),
            resolver=StableResolver(observation(g4)),
        )
        self.assertEqual(gated.disposition, OWNER_RESOLVED_RECOMPUTE_CANDIDATE)
        self.assertTrue(gated.owner_resolved_recompute_candidate)
        self.assertFalse(gated.raw_structural_projection_sufficient)
        self.assertFalse(gated.resolver_authenticated_by_this_contract)
        self.assertFalse(gated.owner_currentness_truth_proven_by_this_contract)
        self.assertFalse(gated.epoch_change_complete_proven_by_this_contract)
        self.assertFalse(gated.bounded_g3_recompute_attempt_admitted_by_this_contract)
        self.assertFalse(gated.recompute_executed_by_this_contract)
        self.assertFalse(gated.gate10_promoted)

    def test_epoch_change_fails_closed(self) -> None:
        g4 = g4_runtime_drift()
        gated = assess_owner_resolved_recompute_premise(
            g4=g4,
            progress=progress(),
            resolver=DriftingResolver(observation(g4)),
        )
        self.assertEqual(gated.disposition, HOLD_G4_OWNER_EPOCH_CHANGED)
        self.assertFalse(gated.owner_resolved_recompute_candidate)

    def test_owner_observation_must_bind_exact_raw_projection(self) -> None:
        g4 = g4_runtime_drift()
        wrong = replace(observation(g4), current_source_binding_generation="source::999")
        gated = assess_owner_resolved_recompute_premise(
            g4=g4,
            progress=progress(),
            resolver=StableResolver(wrong),
        )
        self.assertEqual(gated.disposition, HOLD_G4_OWNER_OBSERVATION_MISMATCH)

    def test_existing_structural_match_hold_is_not_widened(self) -> None:
        gated = assess_owner_resolved_recompute_premise(g4=g4_structural_match(), progress=progress())
        self.assertEqual(gated.disposition, BASE_G5_HOLD)
        self.assertFalse(gated.owner_resolved_recompute_candidate)
        self.assertFalse(gated.bounded_g3_recompute_attempt_admitted_by_this_contract)

    def test_receipt_is_deterministic(self) -> None:
        g4 = g4_runtime_drift()
        resolver = StableResolver(observation(g4))
        a = assess_owner_resolved_recompute_premise(g4=g4, progress=progress(), resolver=resolver)
        b = assess_owner_resolved_recompute_premise(g4=g4, progress=progress(), resolver=resolver)
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_claim_ceiling_rejects_all_authority_widening(self) -> None:
        gated = assess_owner_resolved_recompute_premise(g4=g4_runtime_drift(), progress=progress())
        for field in (
            "raw_structural_projection_sufficient",
            "resolver_authenticated_by_this_contract",
            "owner_currentness_truth_proven_by_this_contract",
            "epoch_change_complete_proven_by_this_contract",
            "bounded_g3_recompute_attempt_admitted_by_this_contract",
            "recompute_executed_by_this_contract",
            "retrieval_or_provider_effect_authorized",
            "transfer_effect_authorized",
            "native_route_mutated",
            "physical_io_proven",
            "source_currentness_minted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(gated, **{field: True}).validate_claim_ceiling()


if __name__ == "__main__":
    unittest.main()
