from __future__ import annotations

from dataclasses import asdict
import unittest

from tools.aura_hyperscale_work_admission import (
    MODE_DUPLICATE,
    MODE_EXPLORATION,
    MODE_REJECTED,
    MODE_VERIFICATION,
    PROCESS_DUPLICATE,
    SEMANTIC_SIBLING,
    SUPPORT_MERGE,
    EvidenceObservation,
    admit_work,
    glm53_remaining_payload_verification_fixture,
    minimum_evidence_cover,
    public_api_has_effect_boolean,
)


class AuraHyperScaleWorkAdmissionTests(unittest.TestCase):
    def _observations(self) -> tuple[EvidenceObservation, ...]:
        return (
            EvidenceObservation(
                observation_id="left",
                covers=("A",),
                cost_score=1,
                byte_cost=10,
            ),
            EvidenceObservation(
                observation_id="right",
                covers=("B",),
                cost_score=1,
                byte_cost=20,
            ),
            EvidenceObservation(
                observation_id="wide",
                covers=("A", "B"),
                cost_score=7,
                byte_cost=1_000,
            ),
        )

    def test_minimum_cover_prefers_small_exact_cone(self) -> None:
        cover = minimum_evidence_cover(("A", "B"), self._observations())
        self.assertTrue(cover.complete)
        self.assertEqual(cover.selected_observation_ids, ("left", "right"))
        self.assertEqual(cover.selected_cost_score, 2)
        self.assertEqual(cover.selected_byte_cost, 30)

    def test_minimum_cover_is_order_independent(self) -> None:
        a = minimum_evidence_cover(("B", "A"), self._observations())
        b = minimum_evidence_cover(("A", "B"), tuple(reversed(self._observations())))
        self.assertEqual(a, b)
        self.assertEqual(a.digest, b.digest)

    def test_uncoverable_verification_fails_closed(self) -> None:
        r = admit_work(
            semantic_disposition=SUPPORT_MERGE,
            hard_gates_pass=True,
            unresolved_leaves=("A", "B"),
            observations=(self._observations()[0],),
            verification_benefit_score=100,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.mode, MODE_REJECTED)
        self.assertEqual(r.reason, "VERIFICATION_EVIDENCE_CONE_NOT_COVERABLE")

    def test_support_merge_admits_verification_when_value_beats_minimum_cover(self) -> None:
        r = admit_work(
            semantic_disposition=SUPPORT_MERGE,
            hard_gates_pass=True,
            unresolved_leaves=("A", "B"),
            observations=self._observations(),
            verification_benefit_score=3,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.mode, MODE_VERIFICATION)
        self.assertEqual(r.selected_observation_ids, ("left", "right"))
        self.assertTrue(r.eligible_to_add_new_egk)
        self.assertFalse(r.eligible_to_seek_new_sck)
        self.assertFalse(r.counts_as_terminal_semantic_sibling_now)
        self.assertFalse(r.verification_inflates_semantic_mass)

    def test_support_merge_rejected_when_value_does_not_beat_cover_cost(self) -> None:
        r = admit_work(
            semantic_disposition=SUPPORT_MERGE,
            hard_gates_pass=True,
            unresolved_leaves=("A", "B"),
            observations=self._observations(),
            verification_benefit_score=2,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.reason, "VERIFICATION_VALUE_NOT_GREATER_THAN_MINIMUM_COVER_COST")

    def test_support_merge_without_unresolved_evidence_does_not_create_work(self) -> None:
        r = admit_work(
            semantic_disposition=SUPPORT_MERGE,
            hard_gates_pass=True,
            verification_benefit_score=10,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.reason, "VERIFICATION_HAS_NO_UNRESOLVED_EVIDENCE")

    def test_new_sck_exploration_has_separate_value_channel(self) -> None:
        r = admit_work(
            semantic_disposition=SEMANTIC_SIBLING,
            hard_gates_pass=True,
            exploration_benefit_score=8,
            exploration_cost_score=3,
            verification_benefit_score=999,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.mode, MODE_EXPLORATION)
        self.assertTrue(r.eligible_to_seek_new_sck)
        self.assertFalse(r.eligible_to_add_new_egk)
        self.assertEqual(r.selected_observation_ids, ())
        self.assertFalse(r.counts_as_terminal_semantic_sibling_now)

    def test_exploration_value_must_strictly_exceed_cost(self) -> None:
        r = admit_work(
            semantic_disposition=SEMANTIC_SIBLING,
            hard_gates_pass=True,
            exploration_benefit_score=3,
            exploration_cost_score=3,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.reason, "EXPLORATION_VALUE_NOT_GREATER_THAN_COST")

    def test_process_duplicate_never_schedules_more_work(self) -> None:
        r = admit_work(
            semantic_disposition=PROCESS_DUPLICATE,
            hard_gates_pass=True,
            unresolved_leaves=("A",),
            observations=(self._observations()[0],),
            exploration_benefit_score=100,
            verification_benefit_score=100,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.mode, MODE_DUPLICATE)
        self.assertFalse(r.process_retry_inflates_evidence_mass)

    def test_failed_hard_gate_blocks_both_value_channels(self) -> None:
        exploration = admit_work(
            semantic_disposition=SEMANTIC_SIBLING,
            hard_gates_pass=False,
            exploration_benefit_score=100,
            exploration_cost_score=1,
        )
        verification = admit_work(
            semantic_disposition=SUPPORT_MERGE,
            hard_gates_pass=False,
            unresolved_leaves=("A",),
            observations=(self._observations()[0],),
            verification_benefit_score=100,
        )
        self.assertFalse(exploration.admitted)
        self.assertFalse(verification.admitted)

    def test_unknown_semantic_disposition_fails_closed(self) -> None:
        r = admit_work(semantic_disposition="TERMINAL_GREEN", hard_gates_pass=True)
        self.assertFalse(r.admitted)
        self.assertEqual(r.mode, MODE_REJECTED)
        self.assertEqual(r.reason, "SEMANTIC_DISPOSITION_NOT_WORK_ADMISSIBLE")

    def test_glm_fixture_selects_only_remaining_up_and_down_pairs(self) -> None:
        r = glm53_remaining_payload_verification_fixture()
        self.assertTrue(r.admitted)
        self.assertEqual(r.mode, MODE_VERIFICATION)
        self.assertEqual(r.selected_observation_ids, ("down-pair", "up-pair"))
        self.assertEqual(r.selected_cost_score, 2)
        self.assertEqual(r.selected_byte_cost, 25_171_968)
        self.assertEqual(len(r.unresolved_leaves), 4)
        self.assertTrue(r.minimum_cover_complete)

    def test_complete_nonpromotion_ceiling(self) -> None:
        r = asdict(glm53_remaining_payload_verification_fixture())
        for key in (
            "counts_as_terminal_semantic_sibling_now",
            "verification_inflates_semantic_mass",
            "process_retry_inflates_evidence_mass",
            "k27_coordinate_growth_grants_semantic_authority",
            "automatic_effect_execution",
            "semantic_truth_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(r[key], key)
        self.assertFalse(public_api_has_effect_boolean())

    def test_receipt_is_deterministic(self) -> None:
        a = glm53_remaining_payload_verification_fixture()
        b = glm53_remaining_payload_verification_fixture()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(len(a.receipt_digest), 64)


if __name__ == "__main__":
    unittest.main()
