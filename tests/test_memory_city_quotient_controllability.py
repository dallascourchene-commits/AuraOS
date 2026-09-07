import itertools, sys, unittest
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_ecf_adapter import ECFCurrentCut, ECFLeafAdmissionWitness, ECFAdmissionIndex
from memory_city_quotient_controllability import *

REG=digest({'registry':'r1'}); CUT=digest({'cut':'c1'}); AUTH=digest({'auth':'a1'}); GRANT=digest({'grant':'g1'})
def se(i,*m): return HardSupportEdge(i,tuple(m))
def de(a,b,r='READ'): return DependencyEdge(a,b,r)
def ecf(root,*,generation=1):
    cut=ECFCurrentCut('JUR-MEM',generation,REG,'availability-owner','boot-1',AVAILABILITY_EVIDENCE_SCOPE,CUT)
    w=ECFLeafAdmissionWitness('w-'+root[:8],root,'JUR-MEM',1,REG,'availability-owner','boot-1',AVAILABILITY_EVIDENCE_SCOPE,CUT,AUTH,GRANT)
    return ECFAdmissionIndex(cut,(w,),admitted_witness_roots=(w.witness_root,))
def av(q,cid,cur=True,obt=True,t=0):
    a=make_component_availability(q,cid,current=cur,obtainable=obt,available_by_tick=t)
    return a,ecf(a.evidence_root)

class QTests(unittest.TestCase):
    def test_support_and_dependency_are_distinct_algebras(self):
        q=compile_hard_support_quotient(['A','B','C'],[se('h','A','B')],[de('B','C')],support_generation=1)
        self.assertEqual(len(q.components),2); self.assertEqual(len(q.dependencies),1)
        self.assertEqual(len(support_components_for_items(q,['A'])),1); self.assertEqual(len(reproof_cone(q,['A'])),2)
    def test_dependency_does_not_expand_hydration_support(self):
        q=compile_hard_support_quotient(['A','B'],[],[de('A','B')],support_generation=1)
        self.assertEqual(len(support_components_for_items(q,['A'])),1); self.assertEqual(len(reproof_cone(q,['A'])),2)
    def test_support_does_not_imply_downstream_reproof(self):
        q=compile_hard_support_quotient(['A','B'],[se('h','A','B')],[],support_generation=1)
        self.assertEqual(len(reproof_cone(q,['A'])),1)
    def test_internal_dependency_is_quotiented_away(self):
        q=compile_hard_support_quotient(['A','B'],[se('h','A','B')],[de('A','B')],support_generation=1)
        self.assertEqual(q.dependencies,())
    def test_cycle_holds_without_merging_support_components(self):
        q=compile_hard_support_quotient(['A','B'],[],[de('A','B'),de('B','A')],support_generation=1)
        self.assertEqual(q.disposition,'HOLD_DEPENDENCY_CYCLE')
    def test_stale_and_incomplete_support_hold(self):
        self.assertEqual(compile_hard_support_quotient(['A'],[],[],support_generation=1,support_current=False).disposition,'HOLD_SUPPORT_STALE')
        self.assertEqual(compile_hard_support_quotient(['A'],[],[],support_generation=1,support_complete=False).disposition,'HOLD_SUPPORT_INCOMPLETE')
    def test_no_ecf_cannot_ready(self):
        q=compile_hard_support_quotient(['A'],[],[],support_generation=1); cid=q.component_for('A'); a=make_component_availability(q,cid,current=True,obtainable=True,available_by_tick=0)
        self.assertEqual(compile_controllability_cut(q,['A'],{cid:a},decision_tick=1).status,'HOLD_ECF_EVIDENCE_INGRESS_REQUIRED')
    def test_authenticated_unobtainable_holds(self):
        q=compile_hard_support_quotient(['A'],[],[],support_generation=1); cid=q.component_for('A'); a,e=av(q,cid,obt=False)
        self.assertEqual(compile_controllability_cut(q,['A'],{cid:a},decision_tick=1,ecf_index=e).status,'HOLD_UNCONTROLLABLE_SUPPORT')
    def test_authenticated_late_holds(self):
        q=compile_hard_support_quotient(['A'],[],[],support_generation=1); cid=q.component_for('A'); a,e=av(q,cid,t=5)
        self.assertEqual(compile_controllability_cut(q,['A'],{cid:a},decision_tick=4,ecf_index=e).status,'HOLD_LATE_REQUIRED_SUPPORT')
    def test_authenticated_stale_holds(self):
        q=compile_hard_support_quotient(['A'],[],[],support_generation=1); cid=q.component_for('A'); a,e=av(q,cid,cur=False)
        self.assertEqual(compile_controllability_cut(q,['A'],{cid:a},decision_tick=4,ecf_index=e).status,'HOLD_STALE_REQUIRED_SUPPORT')
    def test_forged_current_under_old_evidence_root_holds(self):
        q=compile_hard_support_quotient(['A'],[],[],support_generation=1); cid=q.component_for('A'); a,e=av(q,cid)
        forged=ComponentAvailability(cid,False,True,0,a.evidence_root)
        self.assertEqual(compile_controllability_cut(q,['A'],{cid:forged},decision_tick=4,ecf_index=e).status,'HOLD_AVAILABILITY_EVIDENCE_BINDING_MISMATCH')
    def test_ecf_currentness_move_holds(self):
        q=compile_hard_support_quotient(['A'],[],[],support_generation=1); cid=q.component_for('A'); a=make_component_availability(q,cid,current=True,obtainable=True,available_by_tick=0)
        self.assertEqual(compile_controllability_cut(q,['A'],{cid:a},decision_tick=1,ecf_index=ecf(a.evidence_root,generation=2)).status,'HOLD_ECF_JURISDICTION_CURRENTNESS')
    def test_ready_preserves_separate_reproof_cone(self):
        q=compile_hard_support_quotient(['A','B','C'],[se('h','A','B')],[de('B','C')],support_generation=1); cid=q.component_for('A'); a,e=av(q,cid)
        d=compile_controllability_cut(q,['A'],{cid:a},decision_tick=1,changed_items_for_reproof=['A'],ecf_index=e)
        self.assertEqual(d.status,'READY_CONTROLLABLE_SUPPORT_D0'); self.assertEqual(len(d.required_components),1); self.assertEqual(len(d.reproof_components),2); self.assertEqual(len(d.evidence_witness_roots),1); self.assertFalse(d.authority_minted); self.assertFalse(d.gate10)
    def test_parent_contingent_branch_binds_exact_support_partition(self):
        @dataclass(frozen=True)
        class Plan: branch_id:str; required_item_ids:tuple[str,...]; required_components:tuple[tuple[str,...],...]
        @dataclass(frozen=True)
        class Strat: disposition:str; support_generation:int; support_root:str; branch_plans:tuple[Plan,...]
        q=compile_hard_support_quotient(['A','B'],[se('h','A','B')],[],support_generation=7); cid=q.component_for('A'); a,e=av(q,cid)
        st=Strat('READY_D0',7,q.support_world_root,(Plan('x',('A',),(('A','B'),)),))
        self.assertEqual(validate_contingent_strategy_branch(q,st,branch_id='x',availability={cid:a},decision_tick=1,ecf_index=e).status,'READY_CONTROLLABLE_SUPPORT_D0')
    def test_parent_partition_mismatch_holds_before_availability(self):
        @dataclass(frozen=True)
        class Plan: branch_id:str; required_item_ids:tuple[str,...]; required_components:tuple[tuple[str,...],...]
        @dataclass(frozen=True)
        class Strat: disposition:str; support_generation:int; support_root:str; branch_plans:tuple[Plan,...]
        q=compile_hard_support_quotient(['A','B'],[se('h','A','B')],[],support_generation=7); cid=q.component_for('A'); a,e=av(q,cid)
        st=Strat('READY_D0',7,q.support_world_root,(Plan('x',('A',),(('A',),)),))
        self.assertEqual(validate_contingent_strategy_branch(q,st,branch_id='x',availability={cid:a},decision_tick=1,ecf_index=e).status,'HOLD_SUPPORT_PARTITION_MISMATCH')
    def test_same_generation_different_support_world_holds_before_partition(self):
        @dataclass(frozen=True)
        class Plan: branch_id:str; required_item_ids:tuple[str,...]; required_components:tuple[tuple[str,...],...]
        @dataclass(frozen=True)
        class Strat: disposition:str; support_generation:int; support_root:str; branch_plans:tuple[Plan,...]
        q=compile_hard_support_quotient(['A','B','C'],[se('h','A','B')],[],support_generation=7); cid=q.component_for('C'); a,e=av(q,cid)
        stale_root=compile_hard_support_quotient(['A','B','C'],[se('h2','A','C')],[],support_generation=7).support_world_root
        st=Strat('READY_D0',7,stale_root,(Plan('x',('C',),(('C',),)),))
        self.assertEqual(validate_contingent_strategy_branch(q,st,branch_id='x',availability={cid:a},decision_tick=1,ecf_index=e).status,'HOLD_SUPPORT_WORLD_IDENTITY_MISMATCH')
    def test_support_world_root_matches_parent_normalized_semantics(self):
        q1=compile_hard_support_quotient(['A','B','C'],[se('x','B','A'),se('y','C','B')],[],support_generation=4)
        q2=compile_hard_support_quotient(['A','B','C'],[se('other','A','B'),se('another','B','C')],[],support_generation=4)
        self.assertEqual(q1.support_world_root,q2.support_world_root)
    def test_13d_noncompensation(self):
        for tail in itertools.product(range(3),repeat=5): self.assertEqual(hard13d_quotient((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')

if __name__=='__main__': unittest.main()
