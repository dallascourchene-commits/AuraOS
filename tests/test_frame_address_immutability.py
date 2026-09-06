import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARENA = ROOT / 'tools' / 'arena'
sys.path.insert(0, str(ARENA))

from k27_memory.world_atlas import (
    FrameAddress, FrameAtlas, FrameTransform, PrefixCoverage, WorldFrame, zoom_lineage,
)


class FrameAddressImmutabilityTests(unittest.TestCase):
    def test_list_is_canonicalized_to_tuple(self):
        a = FrameAddress('f', 'g', [1, 2, 3], 'x')
        self.assertIsInstance(a.path, tuple)
        self.assertEqual(a.path, (1, 2, 3))

    def test_caller_mutation_cannot_change_address(self):
        path = [1, 2, 3]
        a = FrameAddress('f', 'g', path, 'x')
        path[0] = 9
        self.assertEqual(a.path, (1, 2, 3))

    def test_hash_matches_equivalent_tuple_address(self):
        a = FrameAddress('f', 'g', [1, 2, 3], 'x')
        b = FrameAddress('f', 'g', (1, 2, 3), 'x')
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual({a: 'stable'}[b], 'stable')

    def test_generator_is_materialized_once(self):
        a = FrameAddress('f', 'g', (x for x in [1, 2, 3]), 'x')
        self.assertEqual(a.path, (1, 2, 3))

    def test_bool_digit_still_rejected(self):
        for value in (True, False):
            with self.assertRaises(ValueError):
                FrameAddress('f', 'g', [value], 'x')

    def test_out_of_range_still_rejected(self):
        for value in (-1, 27):
            with self.assertRaises(ValueError):
                FrameAddress('f', 'g', [value], 'x')

    def test_projection_returns_immutable_address(self):
        atlas = FrameAtlas()
        atlas.add_frame(WorldFrame('a', '1', 'e', 'CANONICAL'))
        atlas.add_frame(WorldFrame('b', '1', 'e', 'CANONICAL'))
        atlas.add_transform(FrameTransform('a', '1', 'b', '1'))
        path = [1, 2, 3]
        source = FrameAddress('a', '1', path, 'x')
        out = atlas.project(source, 'b')
        path[:] = [9, 9, 9]
        self.assertEqual(source.path, (1, 2, 3))
        self.assertEqual(out.path, (1, 2, 3))
        self.assertIsInstance(out.path, tuple)

    def test_prefix_coverage_stable_after_caller_mutation(self):
        path = [1, 2, 3]
        address = FrameAddress('f', 'g', path, 'x')
        coverage = PrefixCoverage('f', 'g', [(1, 2)])
        self.assertTrue(coverage.covers(address))
        path[:] = [9, 9, 9]
        self.assertTrue(coverage.covers(address))

    def test_zoom_lineage_stable_after_caller_mutation(self):
        path = [1, 2, 3]
        address = FrameAddress('f', 'g', path, 'x')
        before = zoom_lineage(address)
        path[:] = [8, 8, 8]
        self.assertEqual(before, zoom_lineage(address))
        self.assertEqual(before, ((), (1,), (1, 2), (1, 2, 3)))

    def test_tuple_input_preserves_value_semantics(self):
        path = (26, 0, 13)
        a = FrameAddress('f', 'g', path, 'x')
        self.assertEqual(a.path, path)
        self.assertEqual(hash(a), hash(FrameAddress('f', 'g', path, 'x')))


if __name__ == '__main__':
    unittest.main()
