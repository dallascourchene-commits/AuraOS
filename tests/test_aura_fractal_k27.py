import random
import unittest

from tools.aura_fractal_k27 import (
    AdaptiveZoomReceipt,
    K27Candidate,
    K27Error,
    K27Path,
    K27Segment,
    ZoomDisposition,
    adaptive_zoom_pairwise,
    adaptive_zoom_trie,
    legacy_segment_micro_equivalence,
    prove_different_j,
)


class FractalK27Tests(unittest.TestCase):
    def test_all_legacy_segments_round_trip_through_three_micro_levels(self):
        for x in range(27):
            for y in range(27):
                for z in range(27):
                    seg = K27Segment(x, y, z)
                    levels = seg.to_micro_levels()
                    self.assertEqual(len(levels), 3)
                    self.assertTrue(all(all(0 <= v <= 2 for v in level) for level in levels))
                    self.assertEqual(K27Segment.from_micro_levels(levels), seg)

    def test_living_primer_handle_decomposes_as_expected(self):
        self.assertEqual(
            legacy_segment_micro_equivalence(K27Segment(11, 17, 15)),
            ((1, 1, 1), (0, 2, 2), (2, 2, 0)),
        )

    def test_path_string_micro_round_trip(self):
        path = K27Path.parse("K27:/11.17.15/2.8.21/0.4.6")
        self.assertEqual(str(path), "K27:/11.17.15/2.8.21/0.4.6")
        self.assertEqual(K27Path.from_micro_levels(path.micro_levels()), path)

    def test_parent_address_is_stable_when_child_added(self):
        parent = K27Path.parse("K27:/11.17.15")
        child = parent.child(K27Segment(2, 8, 21))
        self.assertTrue(parent.is_ancestor_of(child))
        self.assertEqual(child.parent, parent)
        self.assertEqual(str(parent), "K27:/11.17.15")

    def test_adaptive_zoom_stops_at_first_distinguishing_micro_level(self):
        a = K27Candidate("owner-a", K27Path.parse("K27:/11.17.15"))
        b = K27Candidate("owner-b", K27Path.parse("K27:/11.17.16"))
        receipt = prove_different_j((a, b))
        self.assertEqual(receipt.disposition, ZoomDisposition.DISTINGUISHED)
        self.assertEqual(receipt.distinguishing_micro_depth, 3)
        self.assertEqual(len(receipt.common_prefix), 2)

    def test_identical_locality_cannot_distinguish_owners(self):
        path = K27Path.parse("K27:/11.17.15")
        receipt = prove_different_j(
            (K27Candidate("owner-a", path), K27Candidate("owner-b", path))
        )
        self.assertEqual(receipt.disposition, ZoomDisposition.LOCALITY_COLLISION)
        self.assertIsNone(receipt.distinguishing_micro_depth)

    def test_ancestor_descendant_needs_nonlocal_identity_resolution(self):
        parent = K27Path.parse("K27:/11.17.15")
        child = K27Path.parse("K27:/11.17.15/2.8.21")
        receipt = prove_different_j(
            (K27Candidate("owner-a", parent), K27Candidate("owner-b", child))
        )
        self.assertEqual(
            receipt.disposition, ZoomDisposition.ANCESTOR_DESCENDANT_COLLISION
        )

    def test_two_independent_resolvers_agree_on_deterministic_fuzz_matrix(self):
        rng = random.Random(270327)
        for _ in range(1000):
            count = rng.randint(2, 8)
            candidates = []
            for i in range(count):
                depth = rng.randint(1, 4)
                segments = tuple(
                    K27Segment(rng.randrange(27), rng.randrange(27), rng.randrange(27))
                    for _ in range(depth)
                )
                candidates.append(K27Candidate(f"owner-{i}", K27Path(segments)))
            left = adaptive_zoom_pairwise(candidates)
            right = adaptive_zoom_trie(candidates)
            self.assertEqual(left.disposition, right.disposition)
            self.assertEqual(
                left.distinguishing_micro_depth, right.distinguishing_micro_depth
            )
            self.assertEqual(left.common_prefix, right.common_prefix)

    def test_random_paths_round_trip(self):
        rng = random.Random(27)
        for _ in range(1000):
            path = K27Path(
                tuple(
                    K27Segment(rng.randrange(27), rng.randrange(27), rng.randrange(27))
                    for _ in range(rng.randint(1, 5))
                )
            )
            self.assertEqual(K27Path.parse(str(path)), path)
            self.assertEqual(K27Path.from_micro_levels(path.micro_levels()), path)

    def test_invalid_axis_and_micro_depth_fail_closed(self):
        with self.assertRaises(K27Error):
            K27Segment(27, 0, 0).validate()
        with self.assertRaises(K27Error):
            K27Segment.from_micro_levels(((0, 0, 0),))
        with self.assertRaises(K27Error):
            K27Path.from_micro_levels(((0, 0, 0), (1, 1, 1)))

    def test_display_wildcards_are_not_accepted_as_exact_identity(self):
        with self.assertRaises(K27Error):
            K27Path.parse("K27:/11.*")

    def test_claim_ceiling_cannot_be_widened(self):
        with self.assertRaises(K27Error):
            AdaptiveZoomReceipt(
                disposition=ZoomDisposition.DISTINGUISHED,
                distinguishing_micro_depth=1,
                common_prefix=(),
                candidate_count=2,
                algorithm="PAIRWISE_LCP",
                authority=True,
            ).validate()


if __name__ == "__main__":
    unittest.main()
