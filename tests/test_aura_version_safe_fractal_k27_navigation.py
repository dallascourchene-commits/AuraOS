from dataclasses import replace
import unittest

from tools.aura_external_cognition_subject_version_resolver import (
    RESOLVER_SCHEMA,
    SubjectVersionDisposition,
    SubjectVersionResolutionReceiptV1,
)
from tools.aura_fractal_k27 import K27Path
from tools.aura_version_safe_fractal_k27_navigation import (
    VersionK27Disposition,
    VersionK27PlacementV1,
    bind_version_candidate_to_k27,
)

SUBJECT = "a" * 64
G1 = "1" * 64
G2 = "2" * 64
G3 = "3" * 64
K1 = f"external-cognition://{SUBJECT}/record/{G1}"
K2 = f"external-cognition://{SUBJECT}/record/{G2}"
K3 = f"external-cognition://{SUBJECT}/record/{G3}"


def selected_receipt():
    return SubjectVersionResolutionReceiptV1(
        schema=RESOLVER_SCHEMA,
        disposition=SubjectVersionDisposition.SELECTED_VERSION_CANDIDATE,
        semantic_subject_id=SUBJECT,
        store_generation="EKI2::STORE::" + "b" * 32,
        store_sha256="b" * 64,
        subject_record_count=2,
        candidate_record_key=K2,
        candidate_record_generation=G2,
        historical_record_keys=(K1,),
        head_record_keys=(K2,),
        reason="TEST_SELECTED_WITH_CURRENTNESS_DEBT",
    )


def p(key, generation, path):
    return VersionK27PlacementV1(key, generation, K27Path.parse(path))


class VersionSafeFractalK27NavigationTests(unittest.TestCase):
    def test_distinguished_versions_bind_without_reselecting(self):
        r = bind_version_candidate_to_k27(
            resolution=selected_receipt(),
            placements=(p(K1, G1, "K27:/11.17.15"), p(K2, G2, "K27:/20.17.15")),
        )
        self.assertEqual(r.disposition, VersionK27Disposition.NAVIGATION_BOUND_DISTINGUISHED)
        self.assertEqual(r.version_record_key, K2)
        self.assertIsNotNone(r.distinguishing_micro_depth)
        self.assertFalse(r.version_selected_by_k27)
        self.assertTrue(r.read_time_currentness_required)
        self.assertFalse(r.source_currentness_proven)
        self.assertFalse(r.read_authority)
        self.assertFalse(r.effect_authority)

    def test_placement_order_cannot_change_selected_version(self):
        a = p(K1, G1, "K27:/1.2.3")
        b = p(K2, G2, "K27:/24.25.26")
        left = bind_version_candidate_to_k27(resolution=selected_receipt(), placements=(a, b))
        right = bind_version_candidate_to_k27(resolution=selected_receipt(), placements=(b, a))
        self.assertEqual(left.version_record_key, right.version_record_key)
        self.assertEqual(left.version_record_generation, right.version_record_generation)
        self.assertEqual(left.disposition, right.disposition)

    def test_selected_relocation_changes_navigation_not_version_identity(self):
        before = bind_version_candidate_to_k27(
            resolution=selected_receipt(), placements=(p(K2, G2, "K27:/1.2.3"),)
        )
        after = bind_version_candidate_to_k27(
            resolution=selected_receipt(), placements=(p(K2, G2, "K27:/4.5.6"),)
        )
        self.assertEqual(before.version_record_key, after.version_record_key)
        self.assertEqual(before.version_record_generation, after.version_record_generation)
        self.assertNotEqual(before.selected_k27_path, after.selected_k27_path)
        self.assertNotEqual(before.receipt_digest, after.receipt_digest)

    def test_exact_locality_collision_holds_distinct_versions(self):
        r = bind_version_candidate_to_k27(
            resolution=selected_receipt(),
            placements=(p(K1, G1, "K27:/11.17.15"), p(K2, G2, "K27:/11.17.15")),
        )
        self.assertEqual(r.disposition, VersionK27Disposition.HOLD_LOCALITY_COLLISION)
        self.assertEqual(r.collision_record_keys, (K1,))
        self.assertFalse(r.semantic_identity_from_k27)
        self.assertFalse(r.version_order_from_k27)

    def test_ancestor_descendant_collision_holds_without_supersession_inference(self):
        r = bind_version_candidate_to_k27(
            resolution=selected_receipt(),
            placements=(p(K1, G1, "K27:/11.17.15"), p(K2, G2, "K27:/11.17.15/2.3.4")),
        )
        self.assertEqual(r.disposition, VersionK27Disposition.HOLD_ANCESTOR_DESCENDANT_COLLISION)
        self.assertFalse(r.version_order_from_k27)

    def test_single_selected_version_binds_but_keeps_currentness_debt(self):
        r = bind_version_candidate_to_k27(
            resolution=selected_receipt(), placements=(p(K2, G2, "K27:/11.17.15"),)
        )
        self.assertEqual(r.disposition, VersionK27Disposition.NAVIGATION_BOUND_SINGLE)
        self.assertIsNone(r.distinguishing_micro_depth)
        self.assertTrue(r.read_time_currentness_required)

    def test_selected_generation_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "SELECTED_VERSION_GENERATION_MISMATCH"):
            bind_version_candidate_to_k27(
                resolution=selected_receipt(), placements=(p(K2, G3, "K27:/1.2.3"),)
            )

    def test_foreign_version_placement_fails(self):
        with self.assertRaisesRegex(ValueError, "PLACEMENT_NOT_SELECTED_OR_HISTORICAL_VERSION"):
            bind_version_candidate_to_k27(
                resolution=selected_receipt(),
                placements=(p(K2, G2, "K27:/1.2.3"), p(K3, G3, "K27:/4.5.6")),
            )

    def test_nonselected_resolution_cannot_be_navigated(self):
        hold = replace(
            selected_receipt(),
            disposition=SubjectVersionDisposition.HOLD_AMBIGUOUS_HEAD,
            candidate_record_key=None,
            candidate_record_generation=None,
        )
        with self.assertRaisesRegex(ValueError, "SELECTED_VERSION_CANDIDATE_REQUIRED"):
            bind_version_candidate_to_k27(resolution=hold, placements=(p(K2, G2, "K27:/1.2.3"),))

    def test_currentness_or_k27_selection_laundering_fails(self):
        with self.assertRaisesRegex(ValueError, "RESOLUTION_CURRENTNESS_CEILING_WIDENED"):
            bind_version_candidate_to_k27(
                resolution=replace(selected_receipt(), source_currentness_proven=True),
                placements=(p(K2, G2, "K27:/1.2.3"),),
            )
        with self.assertRaisesRegex(ValueError, "K27_MUST_NOT_HAVE_SELECTED_VERSION"):
            bind_version_candidate_to_k27(
                resolution=replace(selected_receipt(), k27_used_for_version_selection=True),
                placements=(p(K2, G2, "K27:/1.2.3"),),
            )


if __name__ == "__main__":
    unittest.main()
