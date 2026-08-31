import unittest

from tools.aura_nav_epistemic_route import (
    CurrentnessStatus,
    EpistemicError,
    EpistemicRouteReceipt,
    EpistemicState,
    ExternalRouteEvidence,
    LocalityStatus,
    NextTransition,
    VersionStatus,
    exhaustive_projection_space,
    prove_classifier_different_j,
)


def ev(**changes):
    data = dict(
        owner_ref="owner",
        map_present=True,
        locality=LocalityStatus.DISTINGUISHED,
        version=VersionStatus.SELECTED_VERSION_CANDIDATE,
        currentness=CurrentnessStatus.RESOLVED_CURRENT,
        available_hydration_level=4,
        required_hydration_level=0,
    )
    data.update(changes)
    return ExternalRouteEvidence(**data)


class NavEpistemicRouteTests(unittest.TestCase):
    def test_known_current_requires_independent_currentness_and_sufficient_hydration(self):
        receipt = prove_classifier_different_j(ev())
        self.assertEqual(receipt.state, EpistemicState.KNOWN_CURRENT)
        self.assertEqual(receipt.next_transition, NextTransition.NONE)

    def test_current_but_underhydrated_is_external_unhydrated(self):
        receipt = prove_classifier_different_j(
            ev(available_hydration_level=1, required_hydration_level=3)
        )
        self.assertEqual(receipt.state, EpistemicState.EXTERNAL_UNHYDRATED)
        self.assertEqual(receipt.next_transition, NextTransition.HYDRATE_MINIMUM)

    def test_stale_beats_hydration(self):
        receipt = prove_classifier_different_j(
            ev(
                currentness=CurrentnessStatus.STALE,
                available_hydration_level=0,
                required_hydration_level=4,
            )
        )
        self.assertEqual(receipt.state, EpistemicState.STALE)
        self.assertEqual(receipt.next_transition, NextTransition.REOPEN_CURRENTNESS)

    def test_persisted_not_required_cannot_be_current_for_external_route(self):
        receipt = prove_classifier_different_j(
            ev(currentness=CurrentnessStatus.NOT_REQUIRED)
        )
        self.assertEqual(receipt.state, EpistemicState.UNRESOLVED)
        self.assertEqual(receipt.next_transition, NextTransition.RESOLVE_CURRENTNESS)

    def test_unknown_currentness_remains_unknown(self):
        receipt = prove_classifier_different_j(
            ev(currentness=CurrentnessStatus.UNKNOWN)
        )
        self.assertEqual(receipt.state, EpistemicState.UNKNOWN)

    def test_historical_wins_over_stale_or_hydration_debt(self):
        receipt = prove_classifier_different_j(
            ev(
                version=VersionStatus.HISTORICAL_ONLY,
                currentness=CurrentnessStatus.STALE,
                available_hydration_level=0,
                required_hydration_level=4,
            )
        )
        self.assertEqual(receipt.state, EpistemicState.HISTORICAL)

    def test_collision_wins_over_persisted_history_labels(self):
        receipt = prove_classifier_different_j(
            ev(
                locality=LocalityStatus.LOCALITY_COLLISION,
                version=VersionStatus.HISTORICAL_ONLY,
            )
        )
        self.assertEqual(receipt.state, EpistemicState.COLLISION)

    def test_ambiguous_version_head_is_collision(self):
        receipt = prove_classifier_different_j(
            ev(version=VersionStatus.AMBIGUOUS_HEAD)
        )
        self.assertEqual(receipt.state, EpistemicState.COLLISION)

    def test_owner_missing_and_map_gap_are_distinct(self):
        self.assertEqual(
            prove_classifier_different_j(ev(owner_ref=None)).state,
            EpistemicState.OWNER_MISSING,
        )
        self.assertEqual(
            prove_classifier_different_j(ev(map_present=False)).state,
            EpistemicState.MAP_GAP,
        )

    def test_unresolved_version_precedes_currentness(self):
        receipt = prove_classifier_different_j(
            ev(
                version=VersionStatus.NOT_RESOLVED,
                currentness=CurrentnessStatus.RESOLVED_CURRENT,
            )
        )
        self.assertEqual(receipt.state, EpistemicState.UNRESOLVED)
        self.assertEqual(receipt.next_transition, NextTransition.RESOLVE_VERSION)

    def test_not_evaluated_locality_is_unresolved(self):
        receipt = prove_classifier_different_j(
            ev(locality=LocalityStatus.NOT_EVALUATED)
        )
        self.assertEqual(receipt.state, EpistemicState.UNRESOLVED)

    def test_exhaustive_cross_product_two_formulations_agree(self):
        count = 0
        for evidence in exhaustive_projection_space():
            prove_classifier_different_j(evidence)
            count += 1
        self.assertEqual(count, 8000)

    def test_claim_ceiling_cannot_be_widened(self):
        with self.assertRaises(EpistemicError):
            EpistemicRouteReceipt(
                state=EpistemicState.KNOWN_CURRENT,
                next_transition=NextTransition.NONE,
                available_hydration_level=4,
                required_hydration_level=0,
                semantic_truth=True,
            ).validate()


if __name__ == "__main__":
    unittest.main()
