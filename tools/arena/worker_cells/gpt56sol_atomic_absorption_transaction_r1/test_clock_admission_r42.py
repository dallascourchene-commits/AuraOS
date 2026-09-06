import itertools
import unittest
from dataclasses import replace

from atomic_absorption import Proposal, OwnerSnapshot, digest
from resource_absorption import (
    Lease,
    LeaseMode,
    LeaseRegistrySnapshot,
    RequirementMode,
    ResourceProposal,
    ResourceRequirement,
    plan_resource_absorption,
)
from clock_admission_r42 import (
    CLOCK_SCOPE,
    ClockAdmission,
    context13_clock_admission_preserves_invalid,
    guarded_resource_commit,
    make_admission,
    make_witness,
    omega8_clock_admission_keeper,
)

H = '1' * 64
T = '2' * 64
PLAN = 1000
EXP = 1100


def fixture():
    owner = OwnerSnapshot(H, T)
    lease = Lease('L', 'db:x', 'A', 'LA', LeaseMode.EXCLUSIVE, 900, EXP, 1)
    registry = LeaseRegistrySnapshot(1, (lease,))
    p = Proposal('P', 'A', 'LA', H, digest('c'), digest('r'), {'x.py': digest('b')}, False)
    rp = ResourceProposal(p, (ResourceRequirement('db:x', RequirementMode.WRITE, 'L'),))
    submitted = plan_resource_absorption(owner, registry, (rp,), now_s=PLAN)
    return owner, registry, (rp,), submitted


def call(witness, admission, expected_root=None):
    owner, registry, proposals, submitted = fixture()
    return guarded_resource_commit(
        submitted,
        observed_owner_head=H,
        observed_lease_root=registry.root,
        clock_witness=witness,
        clock_admission=admission,
        expected_clock_admission_root=admission.currentness_root if expected_root is None and admission is not None else expected_root,
        owner=owner,
        registry=registry,
        proposals=proposals,
    )


class ClockAdmissionR42Tests(unittest.TestCase):
    def admitted(self, t=1050, producer='clock-owner', generation='g1', nonce='n1'):
        w = make_witness(producer, generation, t, nonce)
        a = make_admission(w, 'adm-g1')
        return w, a

    def test_01_current_admitted_forward_time_commits(self):
        w, a = self.admitted(1050)
        self.assertTrue(call(w, a).admitted)

    def test_02_exact_plan_time_commits(self):
        w, a = self.admitted(PLAN)
        self.assertTrue(call(w, a).admitted)

    def test_03_current_admitted_expired_time_holds_downstream(self):
        w, a = self.admitted(EXP)
        r = call(w, a)
        self.assertFalse(r.admitted)
        self.assertIn('DOWNSTREAM_RESOURCE_COMMIT_HOLD', r.reasons)

    def test_04_stale_backdated_witness_rejected_by_new_expected_admission(self):
        stale_w = make_witness('clock-owner', 'g1', 1050, 'old')
        stale_a = make_admission(stale_w, 'adm-g1')
        current_w = make_witness('clock-owner', 'g2', 1200, 'new')
        current_a = make_admission(current_w, 'adm-g2')
        r = call(stale_w, stale_a, expected_root=current_a.currentness_root)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_ADMISSION_CURRENTNESS_MISMATCH', r.reasons)

    def test_05_missing_witness_holds(self):
        _, a = self.admitted()
        r = call(None, a)
        self.assertFalse(r.admitted)
        self.assertIn('COMMIT_TIME_WITNESS_REQUIRED', r.reasons)

    def test_06_missing_admission_holds(self):
        w, _ = self.admitted()
        r = call(w, None, expected_root='a' * 64)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_ADMISSION_REQUIRED', r.reasons)

    def test_07_missing_expected_root_holds(self):
        w, a = self.admitted()
        r = call(w, a, expected_root=None)
        # helper defaults when admission exists; call guarded function directly for actual missing-root case.
        owner, registry, proposals, submitted = fixture()
        r = guarded_resource_commit(submitted, observed_owner_head=H, observed_lease_root=registry.root,
            clock_witness=w, clock_admission=a, expected_clock_admission_root=None,
            owner=owner, registry=registry, proposals=proposals)
        self.assertFalse(r.admitted)
        self.assertIn('EXPECTED_CLOCK_ADMISSION_ROOT_REQUIRED', r.reasons)

    def test_08_witness_digest_mismatch_holds(self):
        w, a = self.admitted()
        bad = replace(w, witness_root='0' * 64)
        r = call(bad, a)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_WITNESS_DIGEST_MISMATCH', r.reasons)

    def test_09_producer_mismatch_holds(self):
        w, a = self.admitted()
        bad = replace(a, producer_id='other')
        r = call(w, bad, expected_root=a.currentness_root)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_PRODUCER_MISMATCH', r.reasons)

    def test_10_generation_mismatch_holds(self):
        w, a = self.admitted()
        bad = replace(a, clock_generation='g2')
        r = call(w, bad, expected_root=a.currentness_root)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_GENERATION_MISMATCH', r.reasons)

    def test_11_scope_mismatch_holds(self):
        w = make_witness('clock-owner', 'g1', 1050, 'n', scope='wrong')
        a = make_admission(w, 'adm-g1')
        r = call(w, a)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_SCOPE_MISMATCH', r.reasons)

    def test_12_witness_admission_binding_mismatch_holds(self):
        w1, _ = self.admitted(1050, nonce='a')
        w2, a2 = self.admitted(1050, nonce='b')
        r = call(w1, a2)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_WITNESS_ADMISSION_MISMATCH', r.reasons)

    def test_13_admission_root_tamper_holds(self):
        w, a = self.admitted()
        bad = replace(a, currentness_root='0' * 64)
        r = call(w, bad, expected_root='0' * 64)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_ADMISSION_ROOT_MISMATCH', r.reasons)

    def test_14_authority_widening_holds(self):
        w, _ = self.admitted()
        a = make_admission(w, 'adm-g1', authority_ceiling='D1')
        r = call(w, a)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_ADMISSION_AUTHORITY_WIDENING', r.reasons)

    def test_15_gate10_holds(self):
        w, _ = self.admitted()
        a = make_admission(w, 'adm-g1', gate10=True)
        r = call(w, a)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_ADMISSION_AUTHORITY_WIDENING', r.reasons)

    def test_16_before_plan_holds(self):
        w, a = self.admitted(950)
        r = call(w, a)
        self.assertFalse(r.admitted)
        self.assertIn('CLOCK_BEFORE_PLAN', r.reasons)

    def test_17_observed_time_changes_witness_and_admission_roots(self):
        w1, a1 = self.admitted(1050, nonce='same')
        w2, a2 = self.admitted(1051, nonce='same')
        self.assertNotEqual(w1.witness_root, w2.witness_root)
        self.assertNotEqual(a1.currentness_root, a2.currentness_root)

    def test_18_omega8_one_keeper(self):
        self.assertEqual(sum(omega8_clock_admission_keeper(x) for x in itertools.product(range(3), repeat=8)), 1)

    def test_19_13d_cannot_repair_bad_clock_admission_axis(self):
        core = (2, 2, 2, 2, 2, 2, 2, 1)
        self.assertFalse(any(context13_clock_admission_preserves_invalid(core, tail) for tail in itertools.product(range(3), repeat=5)))


if __name__ == '__main__':
    unittest.main()
