from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json

try:
    from .memory_city_horizon_fenced_handoff import *
except ImportError:
    from memory_city_horizon_fenced_handoff import *


def r(x):
    return sha256(x.encode()).hexdigest()


@dataclass(frozen=True)
class H:
    status: str = 'READY_SUPPORT_CLOSED_HYDRATION_D0'
    receipt_root: str = r('hydr')
    support_root: str = r('support')
    support_cut: tuple[str, ...] = ('a', 'b')


@dataclass(frozen=True)
class C:
    disposition: str = 'READY_D0'
    receipt_root: str = r('typed')
    influence_root: str = r('infl')
    reproof_item_ids: tuple[str, ...] = ('a', 'b', 'c')
    transition_model_root: str = r('trans')
    horizon: int = 2
    future_congruence_root: str = r('future')
    reproof_semantics: str | None = EXPECTED_REPROOF_SEMANTICS


@dataclass(frozen=True)
class RC:
    status: str = 'READY_D0'
    receipt_root: str = r('readcert')
    coverage_receipt_root: str = r('cov')
    binding_roots: tuple[str, ...] = ()
    member_support_roots: tuple[str, ...] = (r('support'),)
    member_hydration_receipt_roots: tuple[str, ...] = (r('hydr'),)
    hydration_cut: tuple[str, ...] = ('a', 'b')
    reproof_item_ids: tuple[str, ...] = ('a', 'b', 'c')
    transition_model_root: str = r('trans')
    horizon: int = 2
    future_congruence_root: str = r('future')
    consequence_root: str = r('cons')


@dataclass(frozen=True)
class RU:
    status: str = 'READY_D0'
    certificate_root: str = r('readcert')


def admission(h, c, mode='EFFECT_BOUND'):
    p = {
        'schema': 'AURA-MEMORY-CITY-PROOF-CARRYING-TYPED-ADMISSION-v2',
        'disposition': 'HOLD_TECC_REQUIRED_D0' if mode == 'EFFECT_BOUND' else 'READY_D0',
        'reason': 'effect_bound_use_requires_independent_tecc_verification' if mode == 'EFFECT_BOUND' else 'read_only_coverage_and_horizon_ready',
        'admission_mode': mode,
        'typed_closure_receipt_root': c.receipt_root,
        'coverage_receipt_root': r('cov'),
        'support_root': h.support_root,
        'influence_root': c.influence_root,
        'transition_model_root': c.transition_model_root,
        'future_congruence_root': c.future_congruence_root,
        'horizon': c.horizon,
        'required_verifier_schema': 'AURA-TECC-v1' if mode == 'EFFECT_BOUND' else None,
        'authority_minted': False,
        'mutation_authority': False,
        'effect_authority': False,
        'gate10': False,
    }
    p['receipt_root'] = digest(p)
    return p


def legacy_binding_root(h, c):
    """Pre-M3 PR888 binding identity: same outer schema, no algorithm identity."""
    return digest({
        'schema': READ_BINDING_SCHEMA,
        'hydration_receipt_root': h.receipt_root,
        'hydration_support_root': h.support_root,
        'typed_closure_receipt_root': c.receipt_root,
    })


def base():
    h = H()
    c = C()
    cert = RC(binding_roots=(canonical_read_binding_root(h, c),))
    return (
        h, c, cert, RU(), admission(h, c),
        EffectHandoffEvidence(r('owner'), r('verifier')),
        MutationBoundaryProjection('cell', 4, r('cfg'), 8, 17, 17, 'worker', 100, r('ta'), r('rf')),
        HandoffVerificationContext('cell', 4, r('cfg'), 8, 17, 17, r('owner'), r('verifier'), r('ta'), r('rf'), 50),
    )


def legacy_ready(read_use, mutation, verification):
    return (
        getattr(read_use, 'status', None) == 'READY_D0'
        and mutation.revision == verification.revision
        and mutation.configuration_root == verification.configuration_root
        and mutation.support_epoch == verification.support_epoch
        and mutation.fence_generation == verification.fence_generation == mutation.installed_fence_generation == verification.installed_fence_generation
        and verification.now < mutation.expires_at
    )


def run(cases=18000):
    counts = {
        'cases': cases,
        'oracle_tecc_route': 0,
        'oracle_hold': 0,
        'candidate_false_route': 0,
        'candidate_false_hold': 0,
        'legacy_semantics_false_route': 0,
        'pre_m3_binding_false_hold_current': 0,
        'pre_m3_binding_false_route_legacy': 0,
        'legacy_false_effect_upgrade': 0,
        'effect_ready': 0,
    }
    for i in range(cases):
        h, c, cert, use, a, ev, m, v = base()
        mode = i % 18
        if mode == 1:
            a = admission(h, c, 'READ_ONLY')
        elif mode == 2:
            c = replace(c, reproof_item_ids=('a', 'c')); a = admission(h, c)
        elif mode == 3:
            c = replace(c, transition_model_root=r('moved')); a = admission(h, c)
        elif mode == 4:
            c = replace(c, future_congruence_root=r('movedfuture')); a = admission(h, c)
        elif mode == 5:
            use = replace(use, certificate_root=r('other'))
        elif mode == 6:
            a = dict(a); a['required_verifier_schema'] = 'WRONG'; a['receipt_root'] = digest({k: v for k, v in a.items() if k != 'receipt_root'})
        elif mode == 7:
            a = dict(a); a['effect_authority'] = True; a['receipt_root'] = digest({k: v for k, v in a.items() if k != 'receipt_root'})
        elif mode == 8:
            v = replace(v, now=100)
        elif mode == 9:
            m = replace(m, installed_fence_generation=16); v = replace(v, installed_fence_generation=16)
        elif mode == 10:
            m = replace(m, revision=5)
        elif mode == 11:
            ev = replace(ev, owner_evidence_root=r('old'))
        elif mode == 12:
            a = dict(a); a['coverage_receipt_root'] = r('other'); a['receipt_root'] = digest({k: v for k, v in a.items() if k != 'receipt_root'})
        elif mode == 13:
            h = replace(h, support_cut=('a',)); a = admission(h, c)
        elif mode == 14:
            cert = replace(cert, status='HOLD_D0')
        elif mode == 15:
            use = replace(use, status='HOLD_D0')
        elif mode == 16:
            c = replace(c, reproof_semantics=None)
            cert = replace(cert, binding_roots=(legacy_binding_root(h, c),))
            a = admission(h, c)
        elif mode == 17:
            c = replace(c, reproof_semantics='ITEM_ONLY_DIRECTED_REPROOF-v0')
            cert = replace(cert, binding_roots=(canonical_read_binding_root(h, c),))
            a = admission(h, c)

        expected = mode == 0
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, v)
        routed = d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0
        counts['oracle_tecc_route' if expected else 'oracle_hold'] += 1
        counts['candidate_false_route'] += int(routed and not expected)
        counts['candidate_false_hold'] += int(expected and not routed)
        counts['legacy_semantics_false_route'] += int(mode in (16, 17) and routed)
        counts['legacy_false_effect_upgrade'] += int(legacy_ready(use, m, v) and not expected)
        counts['effect_ready'] += int(getattr(d, 'effect_authority', False))

        # Counterfactual pre-M3 PR888 binding behavior.
        if mode == 0:
            counts['pre_m3_binding_false_hold_current'] += int(legacy_binding_root(h, c) not in cert.binding_roots)
        if mode == 16:
            counts['pre_m3_binding_false_route_legacy'] += int(legacy_binding_root(h, c) in cert.binding_roots)

    raw = json.dumps(counts, sort_keys=True, separators=(',', ':')).encode()
    out = {
        **counts,
        'campaign_root': sha256(raw).hexdigest(),
        'schema': 'aura.o12c.m3_reproof_semantics_migration.campaign.v1',
        'authority': 'D0_NONPROMOTING_GATE10_FALSE',
        'expected_reproof_semantics': EXPECTED_REPROOF_SEMANTICS,
    }
    if counts['candidate_false_route'] or counts['candidate_false_hold'] or counts['legacy_semantics_false_route'] or counts['effect_ready']:
        raise AssertionError(out)
    return out


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True, indent=2))
