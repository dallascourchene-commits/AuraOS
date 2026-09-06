from __future__ import annotations
import itertools
import json
import random

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
PLAN = 100000
RNG = random.Random(85741)


def make(i):
    owner = OwnerSnapshot(H, T)
    issued = PLAN - 1000 - (i % 97)
    expires = PLAN + 1000 + (i % 193)
    key = f'db:{i % 31}'
    lease = Lease(digest(('lease', i)), key, 'A', 'LA', LeaseMode.EXCLUSIVE, issued, expires, 1)
    registry = LeaseRegistrySnapshot(1, (lease,))
    p = Proposal(f'P{i}', 'A', 'LA', H, digest(('c', i)), digest(('r', i)), {f'f{i % 17}.py': digest(('b', i))}, False)
    rp = ResourceProposal(p, (ResourceRequirement(key, RequirementMode.WRITE, lease.lease_id),))
    submitted = plan_resource_absorption(owner, registry, (rp,), now_s=PLAN)
    return owner, registry, (rp,), submitted, issued, expires


def run(n=100000):
    mismatches = 0
    false_commit = 0
    false_reject = 0
    roots = []
    family_counts = {k: 0 for k in range(10)}
    family_escapes = {k: 0 for k in range(10)}
    for i in range(n):
        owner, registry, proposals, submitted, issued, expires = make(i)
        k = i % 10
        family_counts[k] += 1
        observed_head = H
        observed_root = registry.root
        sources = True
        if k == 0:
            now = PLAN
            expect = True
        elif k == 1:
            now = PLAN + 1 + (i % max(1, expires - PLAN - 1))
            expect = now < expires
        elif k == 2:
            now = PLAN - 1
            expect = False
        elif k == 3:
            now = issued
            expect = False
        elif k == 4:
            now = max(0, issued - 1)
            expect = False
        elif k == 5:
            now = expires
            expect = False
        elif k == 6:
            now = expires + 1 + (i % 11)
            expect = False
        elif k == 7:
            now = PLAN + 1
            observed_head = '9' * 64
            expect = False
        elif k == 8:
            now = PLAN + 1
            observed_root = LeaseRegistrySnapshot(2, registry.leases).root
            expect = False
        else:
            now = PLAN + 1
            sources = False
            expect = False
        kwargs = dict(observed_owner_head=observed_head, observed_lease_root=observed_root, now_s=now)
        if sources:
            kwargs.update(owner=owner, registry=registry, proposals=proposals)
        r = commit_resource_absorption(submitted, **kwargs)
        got = r.committed
        if got != expect:
            mismatches += 1
            family_escapes[k] += 1
        if got and not expect:
            false_commit += 1
        if expect and not got:
            false_reject += 1
        if i < 1000:
            roots.append((k, now, got, r.manifest_root, r.new_head))

    hs_escapes = 0
    for family in range(10):
        for j in range(1000):
            i = family * 1000 + j
            owner, registry, proposals, submitted, issued, expires = make(i)
            if family == 0:
                now, expect, oh, rr, src = PLAN, True, H, registry.root, True
            elif family == 1:
                now, expect, oh, rr, src = min(expires - 1, PLAN + 1), True, H, registry.root, True
            elif family == 2:
                now, expect, oh, rr, src = PLAN - 1, False, H, registry.root, True
            elif family == 3:
                now, expect, oh, rr, src = issued, False, H, registry.root, True
            elif family == 4:
                now, expect, oh, rr, src = max(0, issued - 1), False, H, registry.root, True
            elif family == 5:
                now, expect, oh, rr, src = expires, False, H, registry.root, True
            elif family == 6:
                now, expect, oh, rr, src = expires + 1, False, H, registry.root, True
            elif family == 7:
                now, expect, oh, rr, src = PLAN + 1, False, '9' * 64, registry.root, True
            elif family == 8:
                now, expect, oh, rr, src = PLAN + 1, False, H, LeaseRegistrySnapshot(2, registry.leases).root, True
            else:
                now, expect, oh, rr, src = PLAN + 1, False, H, registry.root, False
            kwargs = dict(observed_owner_head=oh, observed_lease_root=rr, now_s=now)
            if src:
                kwargs.update(owner=owner, registry=registry, proposals=proposals)
            if commit_resource_absorption(submitted, **kwargs).committed != expect:
                hs_escapes += 1

    omega = sum(omega8_resource_keeper(x) for x in itertools.product(range(3), repeat=8))
    repairs = sum(context13_resource_preserves_invalid((2, 2, 2, 2, 2, 2, 2, 1), t) for t in itertools.product(range(3), repeat=5))
    out = {
        'cases': n,
        'mismatches': mismatches,
        'false_commit': false_commit,
        'false_reject': false_reject,
        'family_counts': family_counts,
        'family_escapes': family_escapes,
        'hs1000_families': 10,
        'hs1000_cases': 10000,
        'hs1000_escapes': hs_escapes,
        'omega8_states': 6561,
        'omega8_keepers': omega,
        '13d_tails': 243,
        '13d_repairs': repairs,
        'sample_root': digest(roots),
    }
    out['campaign_root'] = digest(out)
    assert mismatches == false_commit == false_reject == hs_escapes == repairs == 0
    assert omega == 1
    print(json.dumps(out, sort_keys=True))
    return out


if __name__ == '__main__':
    run()
