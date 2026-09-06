from __future__ import annotations
import itertools
import json
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
    ClockGuardReceipt,
    context13_clock_admission_preserves_invalid,
    guarded_resource_commit,
    make_admission,
    make_witness,
    omega8_clock_admission_keeper,
)

H = '1' * 64
T = '2' * 64
PLAN = 100000
EXP = 101000


def fixture(i):
    owner = OwnerSnapshot(H, T)
    key = f'db:{i % 31}'
    lease = Lease(digest(('lease', i)), key, 'A', 'LA', LeaseMode.EXCLUSIVE, PLAN - 1000, EXP + (i % 101), 1)
    registry = LeaseRegistrySnapshot(1, (lease,))
    p = Proposal(f'P{i}', 'A', 'LA', H, digest(('c', i)), digest(('r', i)), {f'f{i % 17}.py': digest(('b', i))}, False)
    rp = ResourceProposal(p, (ResourceRequirement(key, RequirementMode.WRITE, lease.lease_id),))
    submitted = plan_resource_absorption(owner, registry, (rp,), now_s=PLAN)
    return owner, registry, (rp,), submitted, lease.expires_s


def current_pair(t, i, generation='g-current', nonce='current'):
    w = make_witness('clock-owner', generation, t, f'{nonce}-{i}')
    a = make_admission(w, f'adm-{generation}')
    return w, a


def decide(i, family):
    owner, registry, proposals, submitted, expiry = fixture(i)
    expected = False
    if family == 0:
        w, a = current_pair(PLAN, i); expected = True; expected_root = a.currentness_root
    elif family == 1:
        w, a = current_pair(min(expiry - 1, PLAN + 1), i); expected = True; expected_root = a.currentness_root
    elif family == 2:
        w, a = current_pair(expiry, i); expected_root = a.currentness_root
    elif family == 3:
        w, a = current_pair(PLAN - 1, i); expected_root = a.currentness_root
    elif family == 4:
        stale_w, stale_a = current_pair(PLAN + 25, i, generation='g-old', nonce='old')
        current_w, current_a = current_pair(expiry + 50, i, generation='g-new', nonce='new')
        w, a, expected_root = stale_w, stale_a, current_a.currentness_root
    elif family == 5:
        w, a = current_pair(PLAN + 25, i); w = replace(w, witness_root='0' * 64); expected_root = a.currentness_root
    elif family == 6:
        w, a = current_pair(PLAN + 25, i); a = replace(a, producer_id='other'); expected_root = a.currentness_root
    elif family == 7:
        w, a = current_pair(PLAN + 25, i); a = replace(a, clock_generation='other-generation'); expected_root = a.currentness_root
    elif family == 8:
        w = make_witness('clock-owner', 'g-current', PLAN + 25, f'scope-{i}', scope='wrong-scope'); a = make_admission(w, 'adm-g-current'); expected_root = a.currentness_root
    elif family == 9:
        w, a = current_pair(PLAN + 25, i); a = replace(a, currentness_root='0' * 64); expected_root = '0' * 64
    elif family == 10:
        w, _ = current_pair(PLAN + 25, i); a = make_admission(w, 'adm-g-current', authority_ceiling='D1'); expected_root = a.currentness_root
    elif family == 11:
        w, a, expected_root = None, None, None
    else:
        raise ValueError(family)
    r = guarded_resource_commit(
        submitted,
        observed_owner_head=H,
        observed_lease_root=registry.root,
        clock_witness=w,
        clock_admission=a,
        expected_clock_admission_root=expected_root,
        owner=owner,
        registry=registry,
        proposals=proposals,
    )
    return r, expected, expiry


def run(n=100000):
    mismatches = 0
    false_admit = 0
    false_reject = 0
    historical_free_scalar_escape = 0
    family_counts = {k: 0 for k in range(12)}
    family_escapes = {k: 0 for k in range(12)}
    sample = []
    for i in range(n):
        family = i % 12
        family_counts[family] += 1
        r, expected, expiry = decide(i, family)
        if r.admitted != expected:
            mismatches += 1
            family_escapes[family] += 1
        if r.admitted and not expected:
            false_admit += 1
        if expected and not r.admitted:
            false_reject += 1
        if family == 4:
            # Historical raw-scalar API could choose PLAN+25, which is >= plan and < expiry.
            # The current owner admission root instead names an expired-time witness, so R4.2 rejects the stale scalar/witness pair.
            stale_scalar = PLAN + 25
            if stale_scalar >= PLAN and stale_scalar < expiry and not r.admitted:
                historical_free_scalar_escape += 1
        if i < 1000:
            sample.append((family, r.admitted, r.reasons, r.witness_root, r.admission_root, r.observed_s))

    hs_escapes = 0
    for family in range(12):
        for j in range(1000):
            r, expected, _ = decide(family * 1000 + j, family)
            if r.admitted != expected:
                hs_escapes += 1

    omega = sum(omega8_clock_admission_keeper(x) for x in itertools.product(range(3), repeat=8))
    repairs = sum(context13_clock_admission_preserves_invalid((2, 2, 2, 2, 2, 2, 2, 1), tail) for tail in itertools.product(range(3), repeat=5))
    out = {
        'cases': n,
        'mismatches': mismatches,
        'false_admit': false_admit,
        'false_reject': false_reject,
        'historical_free_scalar_escape': historical_free_scalar_escape,
        'family_counts': family_counts,
        'family_escapes': family_escapes,
        'hs1000_families': 12,
        'hs1000_cases': 12000,
        'hs1000_escapes': hs_escapes,
        'omega8_states': 6561,
        'omega8_keepers': omega,
        '13d_tails': 243,
        '13d_repairs': repairs,
        'sample_root': digest(sample),
    }
    out['campaign_root'] = digest(out)
    assert mismatches == false_admit == false_reject == hs_escapes == repairs == 0
    assert historical_free_scalar_escape > 0
    assert omega == 1
    print(json.dumps(out, sort_keys=True))
    return out


if __name__ == '__main__':
    run()
