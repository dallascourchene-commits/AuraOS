import itertools
from dataclasses import replace
from decimal import Decimal
import random
import unittest

from workload_qualified_cost_receipt import *

HEAD = "b" * 40
ENV = CostEnvelope(HEAD, "rt-v1", "hw-v1", "bench-v1", "2.4", "0.02")
SAMPLES = (
    WorkloadSample("a1", "code", "rendered-code-1", True),
    WorkloadSample("a2", "code", "rendered-code-2", True),
    WorkloadSample("b1", "reasoning", "rendered-reason-1", True),
    WorkloadSample("b2", "reasoning", "rendered-reason-2", True),
    WorkloadSample("c1", "control", "rendered-code-1", False, "shared-prefix-control"),
)
TRANSFERS = (
    TransferCharge("d1", 1, "a1", "DEMAND", 2_000_000),
    TransferCharge("s1", 2, "a2", "SPECULATIVE", 3_000_000),
    TransferCharge("d2", 3, "b1", "DEMAND", 1_000_000),
)

class T(unittest.TestCase):
    def test_round_trip(self):
        r = compile_receipt(SAMPLES, TRANSFERS, ENV)
        self.assertTrue(verify_receipt(SAMPLES, TRANSFERS, ENV, r))
        self.assertEqual(r.ranking_categories, ("code", "reasoning"))
        self.assertEqual(r.ranking_sample_count, 4)
        self.assertEqual(r.control_sample_count, 1)

    def test_exact_energy_from_integer_bytes(self):
        r = compile_receipt(SAMPLES, TRANSFERS, ENV)
        self.assertEqual(r.total_modeled_energy_j, "0.0144")
        self.assertEqual(r.speculative_modeled_energy_j, "0.0072")
        self.assertEqual(r.speculative_energy_remaining_j, "0.0128")
        self.assertEqual(energy_from_bytes(r.total_bytes, ENV), Decimal("0.0144"))

    def test_cross_category_ranking_collision_rejected(self):
        bad = list(SAMPLES); bad[2] = replace(bad[2], rendered_prefix=SAMPLES[0].rendered_prefix)
        with self.assertRaisesRegex(QualifiedCostError, "CROSS_CATEGORY"): compile_receipt(tuple(bad), TRANSFERS, ENV)

    def test_same_category_prefix_reuse_allowed(self):
        good = list(SAMPLES); good[1] = replace(good[1], rendered_prefix=SAMPLES[0].rendered_prefix)
        self.assertTrue(compile_receipt(tuple(good), TRANSFERS, ENV).policy_ranking_eligible)

    def test_control_can_share_prefix(self):
        self.assertEqual(SAMPLES[-1].rendered_prefix, SAMPLES[0].rendered_prefix)
        self.assertTrue(compile_receipt(SAMPLES, TRANSFERS, ENV).policy_ranking_eligible)

    def test_control_requires_explicit_group(self):
        bad = SAMPLES[:-1] + (replace(SAMPLES[-1], control_group=None),)
        with self.assertRaises(QualifiedCostError): compile_receipt(bad, TRANSFERS, ENV)

    def test_ranking_sample_cannot_be_control(self):
        bad = (replace(SAMPLES[0], control_group="x"),) + SAMPLES[1:]
        with self.assertRaises(QualifiedCostError): compile_receipt(bad, TRANSFERS, ENV)

    def test_need_two_ranking_categories(self):
        onecat = tuple(replace(s, category="code") if s.ranking_eligible else s for s in SAMPLES)
        with self.assertRaisesRegex(QualifiedCostError, "TWO_RANKING"): compile_receipt(onecat, TRANSFERS, ENV)

    def test_bool_ranking_flag_rejected(self):
        bad = (replace(SAMPLES[0], ranking_eligible=1),) + SAMPLES[1:]
        with self.assertRaises(QualifiedCostError): compile_receipt(bad, TRANSFERS, ENV)

    def test_duplicate_sample_id_rejected(self):
        bad = SAMPLES + (replace(SAMPLES[-1], sample_id="a1", control_group="x"),)
        with self.assertRaises(QualifiedCostError): compile_receipt(bad, TRANSFERS, ENV)

    def test_unknown_transfer_sample_rejected(self):
        bad = (replace(TRANSFERS[0], sample_id="missing"),) + TRANSFERS[1:]
        with self.assertRaises(QualifiedCostError): compile_receipt(SAMPLES, bad, ENV)

    def test_duplicate_physical_transfer_rejected(self):
        bad = (TRANSFERS[0], replace(TRANSFERS[1], transfer_id="d1"), TRANSFERS[2])
        with self.assertRaises(QualifiedCostError): compile_receipt(SAMPLES, bad, ENV)

    def test_transfer_sequence_rejected(self):
        bad = (TRANSFERS[0], replace(TRANSFERS[1], sequence=3), TRANSFERS[2])
        with self.assertRaises(QualifiedCostError): compile_receipt(SAMPLES, bad, ENV)

    def test_bool_bytes_rejected(self):
        bad = (replace(TRANSFERS[0], bytes_moved=True),) + TRANSFERS[1:]
        with self.assertRaises(QualifiedCostError): compile_receipt(SAMPLES, bad, ENV)

    def test_cumulative_budget_exact_boundary(self):
        spec_bytes = TRANSFERS[1].bytes_moved
        exact = _budget_for_bytes(spec_bytes)
        env = replace(ENV, speculative_energy_budget_j=exact)
        r = compile_receipt(SAMPLES, TRANSFERS, env)
        self.assertEqual(r.speculative_energy_remaining_j, "0")

    def test_cumulative_budget_one_byte_over_rejected(self):
        one_less = _budget_for_bytes(TRANSFERS[1].bytes_moved - 1)
        with self.assertRaisesRegex(QualifiedCostError, "CUMULATIVE"): compile_receipt(SAMPLES, TRANSFERS, replace(ENV, speculative_energy_budget_j=one_less))

    def test_float_roundtrip_cannot_change_exact_byte_energy(self):
        total = 0
        for _ in range(1000): total += 1001
        direct = energy_from_bytes(total, ENV)
        pieces = sum((energy_from_bytes(1001, ENV) for _ in range(1000)), Decimal("0"))
        self.assertEqual(direct, pieces)

    def test_result_root_tamper_rejected(self):
        r = compile_receipt(SAMPLES, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(SAMPLES, TRANSFERS, ENV, replace(r, result_root="0" * 64)))

    def test_workload_root_tamper_rejected(self):
        r = compile_receipt(SAMPLES, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(SAMPLES, TRANSFERS, ENV, replace(r, workload_root="0" * 64)))

    def test_envelope_tamper_rejected(self):
        r = compile_receipt(SAMPLES, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(SAMPLES, TRANSFERS, replace(ENV, hardware_fingerprint="other"), r))

    def test_authority_escalation_rejected(self):
        with self.assertRaises(QualifiedCostError): compile_receipt(SAMPLES, TRANSFERS, replace(ENV, effect_authority=True))
        with self.assertRaises(QualifiedCostError): compile_receipt(SAMPLES, TRANSFERS, replace(ENV, gate10=True))

    def test_decimal_nonfinite_rejected(self):
        with self.assertRaises(QualifiedCostError): compile_receipt(SAMPLES, TRANSFERS, replace(ENV, joules_per_gb="NaN"))

    def test_omega8_hard_invalid(self):
        for i in range(8):
            x=[1]*8; x[i]=0; self.assertFalse(crystalline_admission(x))

    def test_omega8_exact_count(self):
        states=list(itertools.product((0,1,2), repeat=8))
        self.assertEqual(sum(crystalline_admission(x) for x in states), 128)

    def test_13d_no_repair(self):
        rng=random.Random(7); repairs=0
        for _ in range(10_000):
            o=[rng.randrange(3) for _ in range(8)]; r=[rng.randrange(3) for _ in range(5)]
            if 0 in o and admission_13d(o,r): repairs+=1
        self.assertEqual(repairs,0)


def _budget_for_bytes(byte_count: int) -> str:
    return format((Decimal(byte_count) * Decimal(ENV.joules_per_gb) / Decimal(ENV.bytes_per_gb)).normalize(), "f")

if __name__ == "__main__": unittest.main()
