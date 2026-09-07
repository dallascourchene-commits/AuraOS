from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from k27_dynamic_navigator import digest
@dataclass(frozen=True)
class ProbeTransition:
    probe_id:str; pre_state_root:str; post_state_root:str; declared_effect:str; consequence_root:str; material_consequence:bool; collision_checked:bool; lawful_ancestry:bool; counterexample_root:str=''; evidence_polarity:str='positive'
    def validate(self):
        if not all(isinstance(x,str) and x for x in (self.probe_id,self.pre_state_root,self.post_state_root,self.declared_effect,self.consequence_root,self.evidence_polarity)): raise ValueError('probe string fields must be nonempty')
        if self.declared_effect not in {'PASSIVE','MAY_MUTATE','CONSUMED_ONCE'}: raise ValueError('invalid declared_effect')
        if self.evidence_polarity not in {'positive','negative'}: raise ValueError('invalid evidence_polarity')
        if any(type(x) is not bool for x in (self.material_consequence,self.collision_checked,self.lawful_ancestry)): raise ValueError('admission flags must be bool')
@dataclass(frozen=True)
class ProbeAdmission:
    status:str; probe_id:str; state_changed:bool; consequence_root:str; transition_root:str; telemetry_reusable:bool; novelty_admitted:bool; reason:str; authority_minted:bool=False; gate10:bool=False
class ReflexiveTelemetryGate:
    def __init__(self,inherited_consequence_roots:Iterable[str]=()): self.inherited=set(inherited_consequence_roots); self.consumed_once=set(); self.admitted=set()
    @staticmethod
    def _transition_root(p): return digest({'probe_id':p.probe_id,'pre_state_root':p.pre_state_root,'post_state_root':p.post_state_root,'declared_effect':p.declared_effect,'consequence_root':p.consequence_root,'counterexample_root':p.counterexample_root,'evidence_polarity':p.evidence_polarity})
    def admit(self,p):
        p.validate(); changed=p.pre_state_root!=p.post_state_root; root=self._transition_root(p)
        if p.declared_effect=='PASSIVE' and changed:return ProbeAdmission('HOLD_UNDECLARED_PROBE_EFFECT',p.probe_id,changed,p.consequence_root,root,False,False,'passive probe changed state')
        if p.declared_effect=='CONSUMED_ONCE' and p.probe_id in self.consumed_once:return ProbeAdmission('HOLD_CONSUMED_ONCE',p.probe_id,changed,p.consequence_root,root,False,False,'consumed-once probe reused')
        if p.declared_effect=='CONSUMED_ONCE': self.consumed_once.add(p.probe_id)
        if not p.lawful_ancestry or not p.collision_checked or not p.material_consequence:return ProbeAdmission('REJECT',p.probe_id,changed,p.consequence_root,root,False,False,'admission prerequisites failed')
        if p.consequence_root in self.inherited or p.consequence_root in self.admitted:return ProbeAdmission('SUPPORT_NOT_DISCOVERY',p.probe_id,changed,p.consequence_root,root,not changed,False,'consequence already represented')
        if not p.counterexample_root:return ProbeAdmission('HOLD_NEEDS_COUNTEREXAMPLE',p.probe_id,changed,p.consequence_root,root,not changed,False,'no discriminating counterexample')
        self.admitted.add(p.consequence_root); return ProbeAdmission('ADMISSION_READY',p.probe_id,changed,p.consequence_root,root,not changed,True,'consequence-distinct counterexample survived D0 admission')
    def compile_sequence(self,probes):
        out=[]; expected=None
        for p in probes:
            p.validate()
            if expected is not None and p.pre_state_root!=expected:
                out.append(ProbeAdmission('HOLD_STATE_CHAIN_GAP',p.probe_id,p.pre_state_root!=p.post_state_root,p.consequence_root,self._transition_root(p),False,False,'probe pre-state does not equal prior post-state')); break
            a=self.admit(p); out.append(a); expected=p.post_state_root
            if a.status.startswith('HOLD_') or a.status=='REJECT': break
        return tuple(out)
def hard13d_admission(axes):
    if len(axes)!=13 or any(type(x) is not int or x not in (0,1,2) for x in axes):return 'HOLD_MALFORMED'
    hard=axes[:8]
    if 0 in hard:return 'HOLD_HARD_INVALID'
    if 1 in hard:return 'HOLD_UNRESOLVED'
    return 'READY_D0'
