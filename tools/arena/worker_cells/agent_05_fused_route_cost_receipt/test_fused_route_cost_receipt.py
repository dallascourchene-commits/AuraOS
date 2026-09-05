import itertools
import math
from dataclasses import replace
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from fused_route_cost_receipt import *

HEAD = "a" * 40
ENV = CostEnvelope(HEAD, "rt-1", "hw-1", "bench-1", "bytes-1.2GBps-energy-2.4JperGB", 0.10)
EVENTS = (
    RouteEvent(1, 0, 0, (1, 2)),
    RouteEvent(2, 0, 1, (2, 3)),
    RouteEvent(3, 1, 0, (3, 4)),
)
TRANSFERS = (
    TransferCharge("p1", 1, "SPECULATIVE", 1, 2, 3, 10, 0.1, 0.04),
    TransferCharge("d1", 2, "DEMAND", 2, 2, 2, 20, 0.2, 0.20),
    TransferCharge("p2", 3, "SPECULATIVE", 2, 3, 4, 10, 0.1, 0.06),
)

class CostReceiptTests(unittest.TestCase):
    def test_round_trip(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertTrue(verify_receipt(EVENTS, TRANSFERS, ENV, r))
        self.assertAlmostEqual(r.speculative_modeled_energy_j, 0.10)
        self.assertAlmostEqual(r.speculative_energy_remaining_j, 0.0)
        self.assertAlmostEqual(r.total_modeled_energy_j, 0.30)

    def test_demand_energy_not_spend_spec_budget(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertEqual(r.demand_modeled_energy_j, 0.20)
        self.assertEqual(r.speculative_modeled_energy_j, 0.10)

    def test_duplicate_physical_id_rejected(self):
        bad = (TRANSFERS[0], replace(TRANSFERS[1], transfer_id="p1"), TRANSFERS[2])
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, bad, ENV)

    def test_cumulative_budget_rejected(self):
        bad = (TRANSFERS[0], TRANSFERS[1], replace(TRANSFERS[2], modeled_energy_j=0.061))
        with self.assertRaisesRegex(CostReceiptError, "CUMULATIVE"): compile_receipt(EVENTS, bad, ENV)

    def test_exact_boundary_allowed(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertAlmostEqual(r.speculative_modeled_energy_j, ENV.speculative_energy_budget_j)

    def test_bool_energy_rejected(self):
        bad = (replace(TRANSFERS[0], modeled_energy_j=True),) + TRANSFERS[1:]
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, bad, ENV)

    def test_bool_bytes_rejected(self):
        bad = (replace(TRANSFERS[0], bytes_moved=True),) + TRANSFERS[1:]
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, bad, ENV)

    def test_nonfinite_rejected(self):
        bad = (replace(TRANSFERS[0], modeled_time_s=math.inf),) + TRANSFERS[1:]
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, bad, ENV)

    def test_bad_schema_rejected(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(EVENTS, TRANSFERS, ENV, replace(r, schema="evil")))

    def test_result_root_tamper_rejected(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(EVENTS, TRANSFERS, ENV, replace(r, result_root="0" * 64)))

    def test_total_tamper_rejected(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(EVENTS, TRANSFERS, ENV, replace(r, total_bytes=r.total_bytes + 1)))

    def test_source_head_tamper_rejected(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(EVENTS, TRANSFERS, replace(ENV, source_head="b" * 40), r))

    def test_envelope_tamper_rejected(self):
        r = compile_receipt(EVENTS, TRANSFERS, ENV)
        self.assertFalse(verify_receipt(EVENTS, TRANSFERS, replace(ENV, hardware_fingerprint="different"), r))

    def test_target_expert_must_be_in_fused_event(self):
        bad = (replace(TRANSFERS[0], expert_id=99),) + TRANSFERS[1:]
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, bad, ENV)

    def test_speculative_must_target_future(self):
        bad = (replace(TRANSFERS[0], target_event_sequence=1, expert_id=1),) + TRANSFERS[1:]
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, bad, ENV)

    def test_demand_must_target_current(self):
        bad = (TRANSFERS[0], replace(TRANSFERS[1], trigger_event_sequence=1), TRANSFERS[2])
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, bad, ENV)

    def test_event_duplicate_expert_rejected(self):
        with self.assertRaises(CostReceiptError): event_root((replace(EVENTS[0], experts=(1, 1)),) + EVENTS[1:])

    def test_event_sequence_rejected(self):
        with self.assertRaises(CostReceiptError): event_root((EVENTS[0], replace(EVENTS[1], sequence=3), EVENTS[2]))

    def test_authority_escalation_rejected(self):
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, TRANSFERS, replace(ENV, effect_authority=True))
        with self.assertRaises(CostReceiptError): compile_receipt(EVENTS, TRANSFERS, replace(ENV, gate10=True))

    def test_clean_git_identity_and_dirty_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "arena@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Arena Test"], cwd=root, check=True)
            p = root / "worker.py"; p.write_text("x=1\n")
            subprocess.run(["git", "add", "worker.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            self.assertRegex(resolve_clean_git_head(root, ["worker.py"]), r"^[0-9a-f]{40}$")
            p.write_text("x=2\n")
            with self.assertRaisesRegex(CostReceiptError, "DIRTY"): resolve_clean_git_head(root, ["worker.py"])

    def test_untracked_file_does_not_forge_tracked_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "arena@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Arena Test"], cwd=root, check=True)
            (root / "tracked.py").write_text("x=1\n")
            subprocess.run(["git", "add", "tracked.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            (root / "untracked.tmp").write_text("not executed source\n")
            self.assertRegex(resolve_clean_git_head(root, ["tracked.py"]), r"^[0-9a-f]{40}$")

    def test_omega8_hard_invalid_dominates(self):
        for i in range(8):
            x = [1] * 8; x[i] = 0
            self.assertFalse(crystalline_admission(x))

    def test_omega8_effect_authority_rejected(self):
        self.assertFalse(crystalline_admission([1] * 7 + [2]))

    def test_omega8_exhaustive_has_128_d0_states(self):
        states = list(itertools.product((0, 1, 2), repeat=8))
        self.assertEqual(sum(crystalline_admission(s) for s in states), 128)

    def test_13d_routing_cannot_repair_head(self):
        rng = random.Random(13); repairs = 0
        for _ in range(10_000):
            omega = [rng.randrange(3) for _ in range(8)]; routing = [rng.randrange(3) for _ in range(5)]
            if 0 in omega and admission_13d(omega, routing): repairs += 1
        self.assertEqual(repairs, 0)

if __name__ == "__main__": unittest.main()
