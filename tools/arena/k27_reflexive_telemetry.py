from __future__ import annotations

"""Reflexive-safe telemetry admission for Memory City Dynamic Navigator.

Foreign rebase:
- ASTRA C53 CGNA O1: novelty requires consequence-distinct counterexample evidence.
- ASTRA V6 54E1: evidence acquisition is a typed state transition when a probe can
  consume or mutate consequence-relevant state.

D0 only. This module does not execute probes and does not mint authority.
"""

from dataclasses import dataclass
from typing import Iterable
from k27_dynamic_navigator import digest


@dataclass(frozen=True)
class ProbeTransition:
    probe_id: str
    pre_state_root: str
    post_state_root: str
    declared_effect: str  # PASSIVE | MAY_MUTATE | CONSUMED_ONCE
    consequence_root: str
    material_consequence: bool
    collision_checked: bool
    lawful_ancestry: bool
    counterexample_root: str = ''
    evidence_polarity: str = 'positive'

    def validate(self):
        if not all(isinstance(x,str) and x for x in (
            self.probe_id,self.pre_state_root,self.post_state_root,
            self.declared_effect,self.consequence_root,self.evidence_polarity,
        )):
            raise ValueError('probe string fields must be nonempty')
        if self.declared_effect not in {'PASSIVE','MAY_MUTATE','CONSUMED_ONCE'}:
            raise ValueError('invalid declared_effect')
        if self.evidence_polarity not in {'positive','negative'}:
            raise ValueError('invalid evidence_polarity')
        if any(type(x) is not bool for x in (
            self.material_consequence,self.collision_checked,self.lawful_ancestry,
        )):
            raise ValueError('admission flags must be bool')


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
    authority_minted: bool = False
    gate10: bool = False


class ReflexiveTelemetryGate:
    def __init__(self, inherited_consequence_roots: Iterable[str] = ()): 
        self.inherited = set(inherited_consequence_roots)
        self.consumed_once: set[str] = set()
        self.admitted: set[str] = set()

    @staticmethod
    def _transition_root(probe: ProbeTransition) -> str:
        return digest({
            'probe_id':probe.probe_id,
            'pre_state_root':probe.pre_state_root,
            'post_state_root':probe.post_state_root,
            'declared_effect':probe.declared_effect,
            'consequence_root':probe.consequence_root,
            'counterexample_root':probe.counterexample_root,
            'evidence_polarity':probe.evidence_polarity,
        })

    def admit(self, probe: ProbeTransition) -> ProbeAdmission:
        probe.validate()
        changed=probe.pre_state_root != probe.post_state_root
        root=self._transition_root(probe)
        if probe.declared_effect == 'PASSIVE' and changed:
            return ProbeAdmission('HOLD_UNDECLARED_PROBE_EFFECT',probe.probe_id,changed,probe.consequence_root,root,False,False,'passive probe changed state')
        if probe.declared_effect == 'CONSUMED_ONCE' and probe.probe_id in self.consumed_once:
            return ProbeAdmission('HOLD_CONSUMED_ONCE',probe.probe_id,changed,probe.consequence_root,root,False,False,'consumed-once probe reused')
        if probe.declared_effect == 'CONSUMED_ONCE':
            self.consumed_once.add(probe.probe_id)
        if not probe.lawful_ancestry or not probe.collision_checked or not probe.material_consequence:
            return ProbeAdmission('REJECT',probe.probe_id,changed,probe.consequence_root,root,False,False,'admission prerequisites failed')
        if probe.consequence_root in self.inherited or probe.consequence_root in self.admitted:
            return ProbeAdmission('SUPPORT_NOT_DISCOVERY',probe.probe_id,changed,probe.consequence_root,root,not changed,False,'consequence already represented')
        if not probe.counterexample_root:
            return ProbeAdmission('HOLD_NEEDS_COUNTEREXAMPLE',probe.probe_id,changed,probe.consequence_root,root,not changed,False,'no discriminating counterexample')
        self.admitted.add(probe.consequence_root)
        return ProbeAdmission('ADMISSION_READY',probe.probe_id,changed,probe.consequence_root,root,not changed,True,'consequence-distinct counterexample survived D0 admission')

    def compile_sequence(self, probes: Iterable[ProbeTransition]) -> tuple[ProbeAdmission, ...]:
        out=[]
        expected=None
        for probe in probes:
            probe.validate()
            if expected is not None and probe.pre_state_root != expected:
                root=self._transition_root(probe)
                out.append(ProbeAdmission('HOLD_STATE_CHAIN_GAP',probe.probe_id,probe.pre_state_root!=probe.post_state_root,probe.consequence_root,root,False,False,'probe pre-state does not equal prior post-state'))
                break
            admitted=self.admit(probe)
            out.append(admitted)
            expected=probe.post_state_root
            if admitted.status.startswith('HOLD_') or admitted.status == 'REJECT':
                break
        return tuple(out)


def hard13d_admission(axes: tuple[int,...]) -> str:
    """13D noncompensation oracle: first eight axes are hard, five are contextual."""
    if len(axes) != 13 or any(type(x) is not int or x not in (0,1,2) for x in axes):
        return 'HOLD_MALFORMED'
    hard=axes[:8]
    if 0 in hard: return 'HOLD_HARD_INVALID'
    if 1 in hard: return 'HOLD_UNRESOLVED'
    return 'READY_D0'
