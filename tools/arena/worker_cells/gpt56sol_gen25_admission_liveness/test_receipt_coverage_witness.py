import itertools
import unittest
from dataclasses import dataclass
from receipt_coverage_witness import *

ROOT = "a" * 64
LEDGER = "b" * 64

@dataclass(frozen=True)
class R:
    sequence_no: int

@dataclass(frozen=True)
class P:
    command_id: str = "CMD"
    attempt_id: str | None = "ATT"
    receipts: tuple[R, ...] = ()
    hold_reason: str | None = None
    ledger_root: str = LEDGER


def C(ids=(0, 2, 7)):
    return compile_coverage_contract(command_id="CMD", attempt_id="ATT", expected_sequence_ids=ids, witness_root=ROOT)

class T(unittest.TestCase):
    def test_sparse_zero_based_exact_set_is_complete(self):
        r = verify_projection_coverage(C(), P(receipts=(R(7), R(0), R(2))))
        self.assertEqual(r.state, CoverageState.COMPLETE)
        self.assertTrue(r.coverage_complete)
    def test_expected_order_is_canonical_not_semantic(self):
        self.assertEqual(C((7,0,2)).contract_root, C((0,2,7)).contract_root)
    def test_missing_expected_holds_coverage(self):
        r = verify_projection_coverage(C(), P(receipts=(R(0), R(7))))
        self.assertEqual(r.state, CoverageState.MISSING_EXPECTED)
        self.assertEqual(r.missing_sequence_ids, (2,))
        self.assertFalse(r.coverage_complete)
    def test_unexpected_observed_is_not_complete(self):
        r = verify_projection_coverage(C(), P(receipts=(R(0), R(2), R(7), R(9))))
        self.assertEqual(r.state, CoverageState.UNEXPECTED_OBSERVED)
        self.assertEqual(r.unexpected_sequence_ids, (9,))
    def test_both_missing_and_extra_is_mismatch(self):
        r = verify_projection_coverage(C(), P(receipts=(R(0), R(9))))
        self.assertEqual(r.state, CoverageState.COVERAGE_MISMATCH)
    def test_scope_mismatch(self):
        r = verify_projection_coverage(C(), P(command_id="OTHER", receipts=(R(0),R(2),R(7))))
        self.assertEqual(r.state, CoverageState.SCOPE_MISMATCH)
    def test_attempt_mismatch(self):
        r = verify_projection_coverage(C(), P(attempt_id="OTHER", receipts=(R(0),R(2),R(7))))
        self.assertEqual(r.state, CoverageState.SCOPE_MISMATCH)
    def test_ledger_integrity_hold_is_noncompensatory(self):
        r = verify_projection_coverage(C(), P(receipts=(R(0),R(2),R(7)), hold_reason="SEQUENCE_EQUIVOCATION"))
        self.assertEqual(r.state, CoverageState.LEDGER_INTEGRITY_HOLD)
        self.assertFalse(r.coverage_complete)
    def test_duplicate_projected_sequence_fails_closed(self):
        with self.assertRaisesRegex(E,"DUPLICATE_PROJECTED_SEQUENCE_ID"):
            verify_projection_coverage(C(), P(receipts=(R(0),R(2),R(2),R(7))))
    def test_duplicate_expected_sequence_fails_closed(self):
        with self.assertRaisesRegex(E,"DUPLICATE_EXPECTED_SEQUENCE_ID"):
            C((0,2,2,7))
    def test_negative_sequence_fails_closed(self):
        with self.assertRaisesRegex(E,"BAD_SEQUENCE_ID"):
            C((-1,))
    def test_zero_sequence_is_valid(self):
        self.assertEqual(C((0,)).expected_sequence_ids,(0,))
    def test_bad_witness_root_fails(self):
        with self.assertRaisesRegex(E,"BAD_WITNESS_ROOT"):
            compile_coverage_contract(command_id="CMD",attempt_id="ATT",expected_sequence_ids=(0,),witness_root="x")
    def test_bad_ledger_root_fails(self):
        with self.assertRaisesRegex(E,"BAD_LEDGER_ROOT"):
            verify_projection_coverage(C(), P(ledger_root="x"))
    def test_receipt_binds_ledger_root(self):
        a=verify_projection_coverage(C(),P(receipts=(R(0),R(2),R(7)),ledger_root="b"*64))
        b=verify_projection_coverage(C(),P(receipts=(R(0),R(2),R(7)),ledger_root="c"*64))
        self.assertNotEqual(a.receipt_root,b.receipt_root)
    def test_receipt_binds_contract_witness(self):
        a=C(); b=compile_coverage_contract(command_id="CMD",attempt_id="ATT",expected_sequence_ids=(0,2,7),witness_root="c"*64)
        pa=verify_projection_coverage(a,P(receipts=(R(0),R(2),R(7))))
        pb=verify_projection_coverage(b,P(receipts=(R(0),R(2),R(7))))
        self.assertNotEqual(pa.receipt_root,pb.receipt_root)
    def test_no_authority_minted(self):
        r=verify_projection_coverage(C(),P(receipts=(R(0),R(2),R(7))))
        self.assertFalse(r.provider_fanout_allowed); self.assertFalse(r.effect_authority); self.assertFalse(r.gate10)
    def test_k27_complete_coordinate(self):
        r=verify_projection_coverage(C(),P(receipts=(R(0),R(2),R(7))))
        self.assertEqual(k27_coverage_coordinate(r),(2,2,2,26))
    def test_k27_incomplete_not_reusable(self):
        r=verify_projection_coverage(C(),P(receipts=(R(0),R(7))))
        x,y,z,slot=k27_coverage_coordinate(r); self.assertEqual((x,y,z),(2,1,0)); self.assertEqual(slot,21)
    def test_omega8_exactly_one_keeper(self):
        self.assertEqual(sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8)),1)
    def test_13d_cannot_repair_hard_invalid(self):
        core=(2,2,2,2,2,2,2,1)
        self.assertEqual(sum(context13_preserves_invalid(core,t) for t in itertools.product(range(3),repeat=5)),0)

if __name__ == "__main__": unittest.main()
