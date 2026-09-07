from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from k27_dynamic_navigator import digest
from memory_city_ecf_adapter import ECFAdmissionIndex


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f'{field} must be nonempty')
    return value


def _hex64(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(f'{field} must be lowercase sha256 hex')
    return value


@dataclass(frozen=True)
class ProbeTransition:
    probe_id: str
    pre_state_root: str
    post_state_root: str
    declared_effect: str
    consequence_root: str
    material_consequence: bool
    collision_checked: bool
    lawful_ancestry: bool
    counterexample_root: str = ''
    evidence_polarity: str = 'positive'
    evidence_root: str = ''

    def validate(self):
        if not all(isinstance(x, str) and x for x in (
            self.probe_id, self.pre_state_root, self.post_state_root,
            self.declared_effect, self.consequence_root, self.evidence_polarity,
        )):
            raise ValueError('probe string fields must be nonempty')
        if self.declared_effect not in {'PASSIVE', 'MAY_MUTATE', 'CONSUMED_ONCE'}:
            raise ValueError('invalid declared_effect')
        if self.evidence_polarity not in {'positive', 'negative'}:
            raise ValueError('invalid evidence_polarity')
        if any(type(x) is not bool for x in (
            self.material_consequence, self.collision_checked, self.lawful_ancestry,
        )):
            raise ValueError('admission flags must be bool')
        if self.evidence_root:
            _hex64(self.evidence_root, 'evidence_root')


@dataclass(frozen=True)
class VerifiedProbeEvidence:
    evidence_id: str
    probe_id: str
    pre_state_root: str
    post_state_root: str
    declared_effect: str
    consequence_root: str
    material_consequence: bool
    collision_checked: bool
    lawful_ancestry: bool
    counterexample_root: str
    evidence_polarity: str
    producer_id: str
    producer_incarnation: str
    observation_root: str
    schema_root: str
    batch_root: str

    def validate(self):
        for field in (
            'evidence_id', 'probe_id', 'pre_state_root', 'post_state_root',
            'declared_effect', 'consequence_root', 'evidence_polarity',
            'producer_id', 'producer_incarnation',
        ):
            _nonempty(getattr(self, field), field)
        if self.declared_effect not in {'PASSIVE', 'MAY_MUTATE', 'CONSUMED_ONCE'}:
            raise ValueError('invalid declared_effect')
        if self.evidence_polarity not in {'positive', 'negative'}:
            raise ValueError('invalid evidence_polarity')
        if any(type(getattr(self, field)) is not bool for field in (
            'material_consequence', 'collision_checked', 'lawful_ancestry',
        )):
            raise ValueError('verified admission flags must be exact bool')
        for field in ('observation_root', 'schema_root', 'batch_root'):
            _hex64(getattr(self, field), field)

    @property
    def evidence_root(self):
        self.validate()
        return digest({
            'schema': 'AURA-VERIFIED-PROBE-EVIDENCE-v1',
            'evidence_id': self.evidence_id,
            'probe_id': self.probe_id,
            'pre_state_root': self.pre_state_root,
            'post_state_root': self.post_state_root,
            'declared_effect': self.declared_effect,
            'consequence_root': self.consequence_root,
            'material_consequence': self.material_consequence,
            'collision_checked': self.collision_checked,
            'lawful_ancestry': self.lawful_ancestry,
            'counterexample_root': self.counterexample_root,
            'evidence_polarity': self.evidence_polarity,
            'producer_id': self.producer_id,
            'producer_incarnation': self.producer_incarnation,
            'observation_root': self.observation_root,
            'schema_root': self.schema_root,
            'batch_root': self.batch_root,
        })


@dataclass(frozen=True)
class ProbeAdmission:
    status: str
    probe_id: str
    state_changed: bool
    consequence_root: str
    transition_root: str
    telemetry_reusable: bool
    novelty_admitted: bool
    reason: str
    evidence_root: str = ''
    authority_minted: bool = False
    gate10: bool = False


class ReflexiveTelemetryGate:
    """D0 novelty admission over structural evidence plus current ECF ingress.

    Probe fields are candidate assertions, never provenance. The rightful ECF
    owner must already have admitted an exact witness for the content-addressed
    evidence root and current use cut. This gate does not authenticate signatures,
    register producers, mint evidence/effect authority, or infer trust from K27.
    """

    def __init__(
        self,
        inherited_consequence_roots: Iterable[str] = (),
        *,
        evidence_records: Iterable[VerifiedProbeEvidence] = (),
        ecf_index: ECFAdmissionIndex | None = None,
    ):
        self.inherited = set(inherited_consequence_roots)
        self.consumed_once = set()
        self.admitted = set()
        self.ecf_index = ecf_index
        self._evidence = {}
        self._evidence_ids = set()
        for evidence in evidence_records:
            if not isinstance(evidence, VerifiedProbeEvidence):
                raise ValueError('evidence records must be VerifiedProbeEvidence')
            root = evidence.evidence_root
            if root in self._evidence or evidence.evidence_id in self._evidence_ids:
                raise ValueError('duplicate evidence identity')
            self._evidence[root] = evidence
            self._evidence_ids.add(evidence.evidence_id)

    @staticmethod
    def _transition_root(p):
        return digest({
            'probe_id': p.probe_id,
            'pre_state_root': p.pre_state_root,
            'post_state_root': p.post_state_root,
            'declared_effect': p.declared_effect,
            'consequence_root': p.consequence_root,
            'counterexample_root': p.counterexample_root,
            'evidence_polarity': p.evidence_polarity,
            'evidence_root': p.evidence_root,
        })

    @staticmethod
    def _candidate_binding(p):
        return (
            p.probe_id, p.pre_state_root, p.post_state_root, p.declared_effect,
            p.consequence_root, p.material_consequence, p.collision_checked,
            p.lawful_ancestry, p.counterexample_root, p.evidence_polarity,
        )

    @staticmethod
    def _evidence_binding(e):
        return (
            e.probe_id, e.pre_state_root, e.post_state_root, e.declared_effect,
            e.consequence_root, e.material_consequence, e.collision_checked,
            e.lawful_ancestry, e.counterexample_root, e.evidence_polarity,
        )

    def _hold(self, status, p, changed, reason):
        return ProbeAdmission(
            status, p.probe_id, changed, p.consequence_root,
            self._transition_root(p), False, False, reason, p.evidence_root,
        )

    def _verified_evidence(self, p, changed):
        if not p.evidence_root:
            return None, self._hold(
                'HOLD_NEEDS_VERIFIED_EVIDENCE', p, changed,
                'novelty/support telemetry requires evidence identity',
            )
        evidence = self._evidence.get(p.evidence_root)
        if evidence is None:
            return None, self._hold(
                'HOLD_EVIDENCE_NOT_FOUND', p, changed,
                'evidence root not present in structural evidence index',
            )
        if self._candidate_binding(p) != self._evidence_binding(evidence):
            return None, self._hold(
                'HOLD_EVIDENCE_BINDING_MISMATCH', p, changed,
                'caller assertions do not match structural evidence',
            )
        if self.ecf_index is None:
            return None, self._hold(
                'HOLD_ECF_EVIDENCE_INGRESS_REQUIRED', p, changed,
                'no current ECF evidence ingress bound',
            )
        admission = self.ecf_index.resolve(
            p.evidence_root, scope='MEMORY_CITY_REFLEXIVE_TELEMETRY'
        )
        if admission.status != 'ADMITTED_EVIDENCE_D0':
            return None, self._hold(admission.status, p, changed, admission.reason)
        return evidence, None

    def admit(self, p):
        p.validate()
        changed = p.pre_state_root != p.post_state_root
        root = self._transition_root(p)
        if p.declared_effect == 'PASSIVE' and changed:
            return ProbeAdmission(
                'HOLD_UNDECLARED_PROBE_EFFECT', p.probe_id, changed,
                p.consequence_root, root, False, False,
                'passive probe changed state', p.evidence_root,
            )

        evidence, hold = self._verified_evidence(p, changed)
        if hold is not None:
            return hold
        assert evidence is not None

        if p.declared_effect == 'CONSUMED_ONCE' and p.probe_id in self.consumed_once:
            return ProbeAdmission(
                'HOLD_CONSUMED_ONCE', p.probe_id, changed,
                evidence.consequence_root, root, False, False,
                'consumed-once probe reused', p.evidence_root,
            )
        if not evidence.lawful_ancestry or not evidence.collision_checked or not evidence.material_consequence:
            return ProbeAdmission(
                'REJECT', p.probe_id, changed, evidence.consequence_root, root,
                False, False, 'verified admission prerequisites failed', p.evidence_root,
            )
        # Only owner-admitted evidence can consume a one-use slot.
        if p.declared_effect == 'CONSUMED_ONCE':
            self.consumed_once.add(p.probe_id)
        if evidence.consequence_root in self.inherited or evidence.consequence_root in self.admitted:
            return ProbeAdmission(
                'SUPPORT_NOT_DISCOVERY', p.probe_id, changed,
                evidence.consequence_root, root, not changed, False,
                'consequence already represented', p.evidence_root,
            )
        if not evidence.counterexample_root:
            return ProbeAdmission(
                'HOLD_NEEDS_COUNTEREXAMPLE', p.probe_id, changed,
                evidence.consequence_root, root, not changed, False,
                'no ECF-admitted discriminating counterexample', p.evidence_root,
            )
        self.admitted.add(evidence.consequence_root)
        return ProbeAdmission(
            'ADMISSION_READY', p.probe_id, changed, evidence.consequence_root,
            root, not changed, True,
            'ECF-admitted consequence-distinct counterexample survived D0 admission',
            p.evidence_root,
        )

    def compile_sequence(self, probes):
        out = []
        expected = None
        for p in probes:
            p.validate()
            if expected is not None and p.pre_state_root != expected:
                out.append(ProbeAdmission(
                    'HOLD_STATE_CHAIN_GAP', p.probe_id,
                    p.pre_state_root != p.post_state_root, p.consequence_root,
                    self._transition_root(p), False, False,
                    'probe pre-state does not equal prior post-state', p.evidence_root,
                ))
                break
            admission = self.admit(p)
            out.append(admission)
            expected = p.post_state_root
            if admission.status.startswith('HOLD_') or admission.status == 'REJECT':
                break
        return tuple(out)


def hard13d_admission(axes):
    if len(axes) != 13 or any(type(x) is not int or x not in (0, 1, 2) for x in axes):
        return 'HOLD_MALFORMED'
    hard = axes[:8]
    if 0 in hard:
        return 'HOLD_HARD_INVALID'
    if 1 in hard:
        return 'HOLD_UNRESOLVED'
    return 'READY_D0'
