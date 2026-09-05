import copy
import os
import sys
import unittest
from dataclasses import replace

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
from contamination_bound_cost_adjudicator import *


class T(unittest.TestCase):
    def setUp(self):
        self.c, self.k = valid_pair()
        self.a = ContaminationBoundCostAdjudicator()

    def decision(self, c=None, k=None):
        return self.a.adjudicate(c or self.c, k or self.k).decision

    def test_00_valid_pair_ready_non_authorizing(self):
        receipt = self.a.adjudicate(self.c, self.k)
        self.assertEqual(receipt.decision, Decision.READY_NONAUTHORIZING)
        self.assertTrue(receipt.comparative_cost_ranking_eligible)
        self.assertFalse(receipt.effect_authority)
        self.assertFalse(receipt.gate10)

    def test_01_composite_receipt_deterministic(self):
        self.assertEqual(self.a.adjudicate(self.c, self.k), self.a.adjudicate(self.c, self.k))

    def test_02_receipt_verifier_recomputes(self):
        r = self.a.adjudicate(self.c, self.k)
        self.assertTrue(verify_composite_receipt(self.c, self.k, r))
        self.assertFalse(verify_composite_receipt(self.c, self.k, replace(r, result_root="0" * 64)))

    def test_03_wrong_contamination_schema_holds(self):
        c = replace(self.c, schema="FORGED")
        self.assertEqual(self.decision(c=c), Decision.HOLD_PARENT_SCHEMA)

    def test_04_wrong_cost_schema_holds(self):
        k = replace(self.k, schema="FORGED")
        self.assertEqual(self.decision(k=k), Decision.HOLD_PARENT_SCHEMA)

    def test_05_wrong_parent_generation_holds(self):
        c = make_attestation(**{**self.c.canonical_without_root(), "semantic_commit": "1" * 40})
        self.assertEqual(self.decision(c=c), Decision.HOLD_PARENT_GENERATION)

    def test_06_tampered_attestation_root_holds(self):
        c = replace(self.c, attestation_root="0" * 64)
        self.assertEqual(self.decision(c=c), Decision.HOLD_PARENT_ATTESTATION)

    def test_07_unverified_parent_holds(self):
        c = make_attestation(**{**self.c.canonical_without_root(), "verified": False})
        self.assertEqual(self.decision(c=c), Decision.HOLD_PARENT_UNVERIFIED)

    def test_08_stale_parent_holds(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "current": False})
        self.assertEqual(self.decision(k=k), Decision.HOLD_PARENT_STALE)

    def test_09_contamination_parent_not_ready_holds(self):
        c = make_attestation(**{**self.c.canonical_without_root(), "ready_non_authorizing": False})
        self.assertEqual(self.decision(c=c), Decision.HOLD_PARENT_NOT_READY)

    def test_10_cost_parent_not_ready_holds(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "ready_non_authorizing": False})
        self.assertEqual(self.decision(k=k), Decision.HOLD_PARENT_NOT_READY)

    def test_11_truth_authority_holds(self):
        c = make_attestation(**{**self.c.canonical_without_root(), "truth_authority": True})
        self.assertEqual(self.decision(c=c), Decision.HOLD_AUTHORITY_CEILING)

    def test_12_effect_authority_holds(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "effect_authority": True})
        self.assertEqual(self.decision(k=k), Decision.HOLD_AUTHORITY_CEILING)

    def test_13_gate10_holds(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "gate10": True})
        self.assertEqual(self.decision(k=k), Decision.HOLD_AUTHORITY_CEILING)

    def test_14_source_mismatch_holds(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "source_identity": "b" * 40})
        self.assertEqual(self.decision(k=k), Decision.HOLD_SOURCE_IDENTITY_MISMATCH)

    def test_15_benchmark_generation_mismatch_holds(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "benchmark_generation": "bench-g2"})
        self.assertEqual(self.decision(k=k), Decision.HOLD_BENCHMARK_GENERATION_MISMATCH)

    def test_16_envelope_binding_mismatch_holds(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "envelope_identity": "f" * 64})
        self.assertEqual(self.decision(k=k), Decision.HOLD_ENVELOPE_BINDING_MISMATCH)

    def test_17_unintegrated_agent06_source_generation_cannot_be_promoted(self):
        # Agent 06 standalone fixtures use a symbolic source_generation such as
        # "src-g1". O4 requires an integrated reproof bound to the exact Git head.
        c = make_attestation(**{**self.c.canonical_without_root(), "source_identity": "src-g1"})
        self.assertFalse(c.internally_valid())
        self.assertEqual(self.decision(c=c), Decision.HOLD_PARENT_ATTESTATION)

    def test_18_bool_is_not_valid_flag_type(self):
        c = replace(self.c, verified=1, attestation_root="0" * 64)
        self.assertFalse(c.internally_valid())

    def test_19_result_root_shape_required(self):
        c = replace(self.c, result_root="x", attestation_root="0" * 64)
        self.assertFalse(c.internally_valid())

    def test_20_binding_root_changes_with_source(self):
        r1 = self.a.adjudicate(self.c, self.k)
        k2 = make_attestation(**{**self.k.canonical_without_root(), "source_identity": "b" * 40})
        r2 = self.a.adjudicate(self.c, k2)
        self.assertNotEqual(r1.parent_binding_root, r2.parent_binding_root)

    def test_21_cross_parent_mismatch_never_inherits_one_side_identity(self):
        k = make_attestation(**{**self.k.canonical_without_root(), "benchmark_generation": "other"})
        r = self.a.adjudicate(self.c, k)
        self.assertEqual(r.benchmark_generation, "")
        self.assertFalse(r.comparative_cost_ranking_eligible)

    def test_22_omega8_exact_keeper(self):
        self.assertTrue(crystalline_admission((2,2,2,2,2,2,2,1)))
        self.assertFalse(crystalline_admission((2,2,2,2,2,2,1,1)))
        self.assertFalse(crystalline_admission((2,2,2,2,2,2,2,0)))

    def test_23_13d_context_cannot_repair_hard_invalid(self):
        for routing in ((0,0,0,0,0), (2,2,2,2,2), (1,2,0,2,1)):
            self.assertFalse(admission_13d((2,2,2,2,2,2,1,1), routing))

    def test_24_noncanonical_values_rejected(self):
        with self.assertRaises(AdjudicationError):
            digest({"x": float("nan")})

    def test_25_parent_roles_are_not_swappable(self):
        c = replace(self.c, role="FUSED_ROUTE_COST")
        self.assertEqual(self.decision(c=c), Decision.HOLD_PARENT_SCHEMA)

    def test_26_parent_attestation_root_binds_currentness(self):
        c2 = make_attestation(**{**self.c.canonical_without_root(), "current": False})
        self.assertNotEqual(self.c.attestation_root, c2.attestation_root)

    def test_27_parent_attestation_root_binds_readiness(self):
        k2 = make_attestation(**{**self.k.canonical_without_root(), "ready_non_authorizing": False})
        self.assertNotEqual(self.k.attestation_root, k2.attestation_root)

    def test_28_no_policy_winner_field_exists(self):
        r = self.a.adjudicate(self.c, self.k)
        self.assertFalse(hasattr(r, "winner"))
        self.assertFalse(hasattr(r, "best_policy"))

    def test_29_exact_parent_commits_are_bound(self):
        r = self.a.adjudicate(self.c, self.k)
        self.assertEqual(r.contamination_parent_commit, CONTAMINATION_PARENT_COMMIT)
        self.assertEqual(r.cost_parent_commit, COST_PARENT_COMMIT)


if __name__ == "__main__":
    unittest.main()
