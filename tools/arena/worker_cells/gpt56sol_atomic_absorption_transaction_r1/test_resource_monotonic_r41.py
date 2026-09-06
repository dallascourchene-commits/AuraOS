import itertools
import unittest

from atomic_absorption import Proposal, OwnerSnapshot, digest
from resource_absorption import (
    Lease,
    LeaseMode,
    LeaseRegistrySnapshot,
    RequirementMode,
    ResourceProposal,
    ResourceRequirement,
    commit_resource_absorption,
    context13_resource_preserves_invalid,
    omega8_resource_keeper,
    plan_resource_absorption,
)

H = '1' * 64
T = '2' * 64
PLAN = 1000


def fixture(*, issued=900, expires=1100):
    owner = OwnerSnapshot(H, T)
    lease = Lease('L', 'db:x', 'A', 'LA', LeaseMode.EXCLUSIVE, issued, expires, 1)
    registry = LeaseRegistrySnapshot(1, (lease,))
    proposal = Proposal('P', 'A', 'LA', H, digest('c'), digest('r'), {'x.py': digest('b')}, False)
    rp = ResourceProposal(proposal, (ResourceRequirement('db:x', RequirementMode.WRITE, 'L'),))
    submitted = plan_resource_absorption(owner, registry, (rp,), now_s=PLAN)
    return owner, registry, (rp,), submitted


class ResourceMonotonicR41Tests(unittest.TestCase):
    def commit(self, now_s, *, owner_head=H, registry_root=None, with_sources=True):
        owner, registry, proposals, submitted = fixture()
        kwargs = dict(observed_owner_head=owner_head, observed_lease_root=registry.root if registry_root is None else registry_root, now_s=now_s)
        if with_sources:
            kwargs.update(owner=owner, registry=registry, proposals=proposals)
        return commit_resource_absorption(submitted, **kwargs)

    def test_01_exact_plan_time_commits(self):
        self.assertTrue(self.commit(PLAN).committed)

    def test_02_forward_before_expiry_commits(self):
        self.assertTrue(self.commit(1099).committed)

    def test_03_expiry_boundary_fails(self):
        self.assertFalse(self.commit(1100).committed)

    def test_04_forward_after_expiry_fails(self):
        self.assertFalse(self.commit(1200).committed)

    def test_05_clock_rollback_after_issue_fails(self):
        self.assertFalse(self.commit(950).committed)

    def test_06_clock_rollback_to_issue_fails(self):
        self.assertFalse(self.commit(900).committed)

    def test_07_clock_rollback_before_issue_fails_closed(self):
        self.assertFalse(self.commit(850).committed)

    def test_08_owner_move_fails(self):
        self.assertFalse(self.commit(1001, owner_head='9' * 64).committed)

    def test_09_registry_move_fails(self):
        owner, registry, proposals, submitted = fixture()
        moved = LeaseRegistrySnapshot(2, registry.leases)
        r = commit_resource_absorption(submitted, observed_owner_head=H, observed_lease_root=moved.root, owner=owner, registry=registry, proposals=proposals, now_s=1001)
        self.assertFalse(r.committed)

    def test_10_missing_sources_fails(self):
        self.assertFalse(self.commit(1001, with_sources=False).committed)

    def test_11_omega8_exactly_one_keeper(self):
        self.assertEqual(sum(omega8_resource_keeper(x) for x in itertools.product(range(3), repeat=8)), 1)

    def test_12_13d_tail_cannot_repair_rollback_axis(self):
        core = (2, 2, 2, 2, 2, 2, 2, 1)
        self.assertFalse(any(context13_resource_preserves_invalid(core, tail) for tail in itertools.product(range(3), repeat=5)))


if __name__ == '__main__':
    unittest.main()
