from __future__ import annotations

from dataclasses import replace
import unittest

import tools.bughound.registered_reproduction_gate as gate
from test_bughound_registered_reproduction_gate import RegisteredIndependentReproductionGateTests


class ReproductionRegistryConvergenceV2Tests(unittest.TestCase):
    def f(self):
        return RegisteredIndependentReproductionGateTests()

    def public_with_records(self, records):
        prior = gate._CANONICAL_REPRODUCTION_RECORDS
        gate._CANONICAL_REPRODUCTION_RECORDS = tuple(records)
        try:
            return gate.admit_with_registered_independent_reproduction(**self.f().public_kwargs())
        finally:
            gate._CANONICAL_REPRODUCTION_RECORDS = prior

    def test_two_valid_distinct_observer_matches_remain_ambiguous(self):
        a = self.f().record()
        b = replace(
            a,
            registry_receipt_ref="registry://receipt/second",
            registry_observer_ref="registry://observer/second-independent",
        )
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_AMBIGUOUS"):
            self.public_with_records((a, b))

    def test_one_valid_match_plus_malformed_neighbor_poison_full_registry_binding(self):
        good = self.f().record()
        malformed = replace(
            good,
            target_ref="target://unrelated",
            registry_receipt_ref="registry://receipt/unrelated",
            registry_observer_ref=good.reproducer_ref,
        )
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_OBSERVER_PRODUCER_SEPARATION_REQUIRED"):
            self.public_with_records((good, malformed))

    def test_structurally_valid_stale_neighbor_is_bound_but_not_ambiguous(self):
        good = self.f().record()
        stale = replace(
            good,
            target_ref="target://unrelated",
            registry_receipt_ref="registry://receipt/historical",
            registry_observer_ref="registry://observer/historical",
            registry_current=False,
        )
        out = self.public_with_records((good, stale))
        self.assertTrue(out.independent_reproduction_registry_proven)
        self.assertEqual(gate.REGISTRY_GENERATION, out.registry_generation)
        self.assertTrue(out.registry_digest)
        self.assertFalse(out.external_effect)


if __name__ == "__main__":
    unittest.main()
