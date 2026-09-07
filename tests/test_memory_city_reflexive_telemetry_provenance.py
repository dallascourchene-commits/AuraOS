import itertools
import random
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'/'arena'))
from k27_dynamic_navigator import digest
from memory_city_ecf_adapter import ECFCurrentCut, ECFLeafAdmissionWitness, ECFAdmissionIndex
from k27_reflexive_telemetry import (
    ProbeTransition, ReflexiveTelemetryGate, VerifiedProbeEvidence, hard13d_admission,
)

BATCH = digest({'batch':'b1'})
SCHEMA = digest({'schema':'telemetry-v1'})
OBS = digest({'obs':'o1'})
REG = digest({'registry':'r1'})
CUT = digest({'cut':'c1'})
AUTH = digest({'auth':'a1'})
GRANT = digest({'grant':'g1'})
SCOPE = 'MEMORY_CITY_REFLEXIVE_TELEMETRY'


def evidence(**kw):
    base = dict(
        evidence_id='ev1', probe_id='p', pre_state_root='a', post_state_root='a',
        declared_effect='MAY_MUTATE', consequence_root='c', material_consequence=True,
        collision_checked=True, lawful_ancestry=True, counterexample_root='cx',
        evidence_polarity='positive', producer_id='telemetry-owner',
        producer_incarnation='boot-1', observation_root=OBS, schema_root=SCHEMA,
        batch_root=BATCH,
    )
    base.update(kw)
    return VerifiedProbeEvidence(**base)


def transition(e=None, **kw):
    e = e or evidence()
    base = dict(
        probe_id=e.probe_id, pre_state_root=e.pre_state_root,
        post_state_root=e.post_state_root, declared_effect=e.declared_effect,
        consequence_root=e.consequence_root, material_consequence=e.material_consequence,
        collision_checked=e.collision_checked, lawful_ancestry=e.lawful_ancestry,
        counterexample_root=e.counterexample_root, evidence_polarity=e.evidence_polarity,
        evidence_root=e.evidence_root,
    )
    base.update(kw)
    return ProbeTransition(**base)


def ecf(e, *, current_incarnation='boot-1', admitted=True):
    cut = ECFCurrentCut('JUR-MEM', 3, REG, 'telemetry-owner', current_incarnation, SCOPE, CUT)
    witness = ECFLeafAdmissionWitness(
        'w-' + e.evidence_id, e.evidence_root, 'JUR-MEM', 3, REG,
        'telemetry-owner', 'boot-1', SCOPE, CUT, AUTH, GRANT,
    )
    index = ECFAdmissionIndex(
        cut, (witness,),
        admitted_witness_roots=(witness.witness_root,) if admitted else (),
    )
    return index


def gate(e=None, inherited=(), *, index=True):
    e = e or evidence()
    return ReflexiveTelemetryGate(
        inherited, evidence_records=(e,), ecf_index=ecf(e) if index else None,
    )


class ProvenanceTelemetryTests(unittest.TestCase):
    def test_ecf_admitted_positive_admits(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e)).status,'ADMISSION_READY')
    def test_structural_evidence_without_ecf_holds(self):
        e=evidence(); self.assertEqual(gate(e,index=False).admit(transition(e)).status,'HOLD_ECF_EVIDENCE_INGRESS_REQUIRED')
    def test_missing_evidence_holds(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e,evidence_root='')).status,'HOLD_NEEDS_VERIFIED_EVIDENCE')
    def test_unknown_evidence_root_holds(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e,evidence_root=digest({'other':1}))).status,'HOLD_EVIDENCE_NOT_FOUND')
    def test_unadmitted_ecf_witness_holds(self):
        e=evidence(); g=ReflexiveTelemetryGate(evidence_records=(e,),ecf_index=ecf(e,admitted=False))
        self.assertEqual(g.admit(transition(e)).status,'HOLD_ECF_WITNESS_NOT_ADMITTED')
    def test_producer_incarnation_move_holds(self):
        e=evidence(); g=ReflexiveTelemetryGate(evidence_records=(e,),ecf_index=ecf(e,current_incarnation='boot-2'))
        self.assertEqual(g.admit(transition(e)).status,'HOLD_ECF_PRODUCER_CURRENTNESS')
    def test_forged_material_flag_holds(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e,material_consequence=False)).status,'HOLD_EVIDENCE_BINDING_MISMATCH')
    def test_forged_collision_flag_holds(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e,collision_checked=False)).status,'HOLD_EVIDENCE_BINDING_MISMATCH')
    def test_forged_ancestry_flag_holds(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e,lawful_ancestry=False)).status,'HOLD_EVIDENCE_BINDING_MISMATCH')
    def test_forged_consequence_root_holds(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e,consequence_root='forged')).status,'HOLD_EVIDENCE_BINDING_MISMATCH')
    def test_forged_counterexample_root_holds(self):
        e=evidence(); self.assertEqual(gate(e).admit(transition(e,counterexample_root='forged')).status,'HOLD_EVIDENCE_BINDING_MISMATCH')
    def test_verified_failed_prereq_rejects(self):
        e=evidence(lawful_ancestry=False); self.assertEqual(gate(e).admit(transition(e)).status,'REJECT')
    def test_no_counterexample_holds(self):
        e=evidence(counterexample_root=''); self.assertEqual(gate(e).admit(transition(e)).status,'HOLD_NEEDS_COUNTEREXAMPLE')
    def test_existing_consequence_is_support_only(self):
        e=evidence(); self.assertEqual(gate(e,inherited=('c',)).admit(transition(e)).status,'SUPPORT_NOT_DISCOVERY')
    def test_passive_state_change_holds_before_evidence(self):
        p=ProbeTransition('p','a','b','PASSIVE','c',True,True,True,'cx')
        self.assertEqual(ReflexiveTelemetryGate().admit(p).status,'HOLD_UNDECLARED_PROBE_EFFECT')
    def test_unverified_consumed_once_cannot_burn_slot(self):
        e=evidence(declared_effect='CONSUMED_ONCE'); g=gate(e)
        self.assertEqual(g.admit(transition(e,evidence_root='')).status,'HOLD_NEEDS_VERIFIED_EVIDENCE')
        self.assertEqual(g.admit(transition(e)).status,'ADMISSION_READY')
    def test_verified_consumed_once_reuse_holds(self):
        e=evidence(declared_effect='CONSUMED_ONCE'); g=gate(e)
        self.assertEqual(g.admit(transition(e)).status,'ADMISSION_READY')
        self.assertEqual(g.admit(transition(e)).status,'HOLD_CONSUMED_ONCE')
    def test_duplicate_evidence_id_rejected(self):
        e=evidence(); e2=evidence(consequence_root='d')
        with self.assertRaises(ValueError): ReflexiveTelemetryGate(evidence_records=(e,e2))
    def test_evidence_root_changes_with_producer_incarnation(self):
        self.assertNotEqual(evidence().evidence_root,evidence(producer_incarnation='boot-2').evidence_root)
    def test_sequence_gap_holds(self):
        e1=evidence(evidence_id='e1',probe_id='p1',post_state_root='b',observation_root=digest({'o':1}))
        e2=evidence(evidence_id='e2',probe_id='p2',pre_state_root='x',post_state_root='x',consequence_root='d',counterexample_root='dx',observation_root=digest({'o':2}))
        w1=ECFLeafAdmissionWitness('w1',e1.evidence_root,'JUR-MEM',3,REG,'telemetry-owner','boot-1',SCOPE,CUT,AUTH,GRANT)
        w2=ECFLeafAdmissionWitness('w2',e2.evidence_root,'JUR-MEM',3,REG,'telemetry-owner','boot-1',SCOPE,CUT,AUTH,GRANT)
        idx=ECFAdmissionIndex(ECFCurrentCut('JUR-MEM',3,REG,'telemetry-owner','boot-1',SCOPE,CUT),(w1,w2),admitted_witness_roots=(w1.witness_root,w2.witness_root))
        out=ReflexiveTelemetryGate(evidence_records=(e1,e2),ecf_index=idx).compile_sequence((transition(e1),transition(e2)))
        self.assertEqual(out[-1].status,'HOLD_STATE_CHAIN_GAP')
    def test_hard13d_noncompensation(self):
        for tail in itertools.product(range(3),repeat=5):
            self.assertEqual(hard13d_admission((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')
    def test_randomized_forgery_never_admits(self):
        rng=random.Random(14001)
        fields=('material_consequence','collision_checked','lawful_ancestry','consequence_root','counterexample_root','post_state_root','evidence_root')
        for i in range(10000):
            e=evidence(evidence_id=f'e{i}',probe_id=f'p{i}',consequence_root=f'c{i}',counterexample_root=f'x{i}',observation_root=digest({'o':i}))
            g=gate(e); field=rng.choice(fields)
            if field in {'material_consequence','collision_checked','lawful_ancestry'}: value=not getattr(e,field)
            elif field=='evidence_root': value=digest({'forged':i})
            else: value=f'forged-{i}'
            self.assertNotEqual(g.admit(transition(e,**{field:value})).status,'ADMISSION_READY')

if __name__=='__main__': unittest.main()
