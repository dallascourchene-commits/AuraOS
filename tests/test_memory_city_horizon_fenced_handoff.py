from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools' / 'arena'))
from memory_city_horizon_fenced_handoff import *


def r(x):
    return sha256(x.encode()).hexdigest()


@dataclass(frozen=True)
class Hydration:
    status: str = 'READY_SUPPORT_CLOSED_HYDRATION_D0'
    receipt_root: str = r('hydr')
    support_root: str = r('support')
    support_cut: tuple[str, ...] = ('a', 'b')


@dataclass(frozen=True)
class Closure:
    disposition: str = 'READY_D0'
    receipt_root: str = r('typed')
    influence_root: str = r('infl')
    reproof_item_ids: tuple[str, ...] = ('a', 'b', 'c')
    transition_model_root: str = r('trans')
    horizon: int = 2
    future_congruence_root: str = r('future')
    reproof_semantics: str | None = EXPECTED_REPROOF_SEMANTICS


@dataclass(frozen=True)
class ReadCert:
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
    mutation_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False


@dataclass(frozen=True)
class ReadUse:
    status: str = 'READY_D0'
    certificate_root: str = r('readcert')


def admission(h=Hydration(), c=Closure(), mode='EFFECT_BOUND'):
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


def fixtures():
    h = Hydration()
    c = Closure()
    cert = ReadCert(binding_roots=(canonical_read_binding_root(h, c),))
    use = ReadUse()
    a = admission(h, c)
    ev = EffectHandoffEvidence(r('owner'), r('verifier'))
    m = MutationBoundaryProjection('cell', 4, r('cfg'), 8, 17, 17, 'worker', 100, r('ta'), r('rf'))
    v = HandoffVerificationContext('cell', 4, r('cfg'), 8, 17, 17, r('owner'), r('verifier'), r('ta'), r('rf'), 50)
    return h, c, cert, use, a, ev, m, v


class T(unittest.TestCase):
    def test_valid_cross_binding_routes_to_tecc_not_ready(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, v)
        self.assertIs(d.disposition, HandoffDisposition.HOLD_TECC_REQUIRED_D0)
        self.assertEqual(d.required_verifier_schema, 'AURA-TECC-v1')
        self.assertFalse(d.effect_authority)

    def test_current_binding_matches_m3_owner_formula(self):
        h, c, *_ = fixtures()
        expected = digest({
            'schema': READ_BINDING_SCHEMA,
            'hydration_receipt_root': h.receipt_root,
            'hydration_support_root': h.support_root,
            'typed_closure_receipt_root': c.receipt_root,
            'typed_reproof_semantics': EXPECTED_REPROOF_SEMANTICS,
        })
        self.assertEqual(canonical_read_binding_root(h, c), expected)

    def test_legacy_same_schema_missing_semantics_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        legacy = replace(c, reproof_semantics=None)
        legacy_root = digest({
            'schema': READ_BINDING_SCHEMA,
            'hydration_receipt_root': h.receipt_root,
            'hydration_support_root': h.support_root,
            'typed_closure_receipt_root': legacy.receipt_root,
        })
        legacy_cert = replace(cert, binding_roots=(legacy_root,))
        d = compile_effect_handoff(legacy_cert, use, h, legacy, admission(h, legacy), ev, m, v)
        self.assertEqual(d.reason, 'ACTIVE_REPROOF_SEMANTICS_NOT_CURRENT')

    def test_wrong_reproof_semantics_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        moved = replace(c, reproof_semantics='ITEM_ONLY_DIRECTED_REPROOF-v0')
        moved_cert = replace(cert, binding_roots=(canonical_read_binding_root(h, moved),))
        d = compile_effect_handoff(moved_cert, use, h, moved, admission(h, moved), ev, m, v)
        self.assertEqual(d.reason, 'ACTIVE_REPROOF_SEMANTICS_NOT_CURRENT')

    def test_semantics_move_changes_binding_identity(self):
        h, c, *_ = fixtures()
        legacy = replace(c, reproof_semantics=None)
        self.assertNotEqual(canonical_read_binding_root(h, c), canonical_read_binding_root(h, legacy))

    def test_read_only_cannot_enter_effect_handoff(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, use, h, c, admission(h, c, 'READ_ONLY'), ev, m, v)
        self.assertEqual(d.reason, 'READ_ONLY_CANNOT_ENTER_EFFECT_HANDOFF')

    def test_stale_component_reproof_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        c2 = replace(c, reproof_item_ids=('a', 'c'))
        d = compile_effect_handoff(cert, use, h, c2, admission(h, c2), ev, m, v)
        self.assertEqual(d.reason, 'ACTIVE_READ_WORLD_NOT_CERTIFIED')

    def test_same_receipt_semantic_swap_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        c2 = replace(c, reproof_item_ids=('a', 'b', 'd'))
        d = compile_effect_handoff(cert, use, h, c2, admission(h, c2), ev, m, v)
        self.assertIn(d.reason, ('ACTIVE_READ_WORLD_NOT_CERTIFIED', 'ACTIVE_COMPONENT_REPROOF_MOVED'))

    def test_transition_move_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        c2 = replace(c, transition_model_root=r('moved'))
        d = compile_effect_handoff(cert, use, h, c2, admission(h, c2), ev, m, v)
        self.assertIn(d.reason, ('ACTIVE_READ_WORLD_NOT_CERTIFIED', 'ACTIVE_TRANSITION_CONSEQUENCE_MOVED'))

    def test_read_use_certificate_move_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, replace(use, certificate_root=r('other')), h, c, a, ev, m, v)
        self.assertEqual(d.reason, 'READ_USE_CERTIFICATE_MOVED')

    def test_forged_admission_receipt_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        a = dict(a)
        a['support_root'] = r('other')
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, v)
        self.assertEqual(d.reason, 'ADMISSION_SUPPORT_MOVED')

    def test_authority_escalation_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        a = dict(a)
        a['effect_authority'] = True
        a['receipt_root'] = digest({k: v for k, v in a.items() if k != 'receipt_root'})
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, v)
        self.assertEqual(d.reason, 'ADMISSION_AUTHORITY_ESCALATION')

    def test_expired_lease_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, replace(v, now=100))
        self.assertEqual(d.reason, 'LEASE_EXPIRED')

    def test_uninstalled_fence_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        m = replace(m, installed_fence_generation=16)
        v = replace(v, installed_fence_generation=16)
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, v)
        self.assertEqual(d.reason, 'FENCE_NOT_INSTALLED_CURRENT')

    def test_revision_move_rebinds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, use, h, c, a, ev, replace(m, revision=5), v)
        self.assertIs(d.disposition, HandoffDisposition.REBIND_REQUIRED)

    def test_owner_evidence_stale_holds(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, use, h, c, a, replace(ev, owner_evidence_root=r('old')), m, v)
        self.assertEqual(d.reason, 'OWNER_EVIDENCE_ROOT_STALE')

    def test_tecc_input_binds_reproof_semantics(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, v)
        self.assertIsNotNone(d.tecc_input_root)
        moved = replace(c, reproof_semantics='OTHER')
        moved_cert = replace(cert, binding_roots=(canonical_read_binding_root(h, moved),))
        held = compile_effect_handoff(moved_cert, use, h, moved, admission(h, moved), ev, m, v)
        self.assertIsNone(held.tecc_input_root)

    def test_decision_never_mints_authority(self):
        h, c, cert, use, a, ev, m, v = fixtures()
        d = compile_effect_handoff(cert, use, h, c, a, ev, m, v)
        self.assertFalse(d.authority_minted)
        self.assertFalse(d.mutation_authority)
        self.assertFalse(d.effect_authority)
        self.assertFalse(d.gate10)

    def test_campaign_direct_script_entrypoint_runs(self):
        repo = Path(__file__).resolve().parents[1]
        script = repo / 'tools' / 'arena' / 'campaign_memory_city_horizon_fenced_handoff.py'
        completed = subprocess.run([sys.executable, str(script)], cwd=repo, capture_output=True, text=True, check=True)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload['candidate_false_route'], 0)
        self.assertEqual(payload['candidate_false_hold'], 0)
        self.assertEqual(payload['legacy_semantics_false_route'], 0)
        self.assertEqual(payload['effect_ready'], 0)


if __name__ == '__main__':
    unittest.main()
