import itertools, random, unittest
from dataclasses import replace
import os, sys
ROOT=os.path.dirname(__file__)
sys.path.insert(0,ROOT)
from evidence_slice_dag import *

class EvidenceSliceDagTests(unittest.TestCase):
    def test_source_change_recomputes_all_descendants(self):
        d=demo_dag(); w=demo_witnesses(d); p=d.compile_plan(['source_raw'],w)
        self.assertEqual(set(p.invalidated),set(d.nodes)); self.assertEqual(p.decision,'RECOMPUTE_ALL')
    def test_transfer_change_preserves_unrelated_slices(self):
        d=demo_dag(); w=demo_witnesses(d); p=d.compile_plan(['transfer_raw'],w)
        self.assertEqual(set(p.invalidated),{'transfer_raw','cost_receipt','composite'})
        self.assertIn('workload_receipt',p.reusable); self.assertIn('trace_receipt',p.reusable)
    def test_workload_change_is_scoped(self):
        d=demo_dag(); w=demo_witnesses(d); p=d.compile_plan(['workload_raw'],w)
        self.assertEqual(set(p.invalidated),{'workload_raw','workload_receipt','composite'})
        self.assertEqual(p.affected_consequence_keys,('admission','workload'))
    def test_trace_change_hits_trace_workload_cost_composite(self):
        d=demo_dag(); w=demo_witnesses(d); p=d.compile_plan(['trace_raw'],w)
        self.assertEqual({'trace_raw','transfer_raw','trace_receipt','workload_receipt','cost_receipt','composite'},set(p.invalidated))
        self.assertIn('source_receipt',p.reusable)
    def test_uncurrent_reusable_witness_fails_closed(self):
        d=demo_dag(); w=demo_witnesses(d); old=w['source_receipt']; w['source_receipt']=witness_for(old.node_id,old.input_root,old.output_root,old.generation,current=False)
        with self.assertRaisesRegex(DagError,'UNCURRENT_REUSE_WITNESS'): d.compile_plan(['transfer_raw'],w)

    def test_stale_changed_witness_is_allowed_because_it_is_recomputed(self):
        d=demo_dag(); w=demo_witnesses(d); old=w['transfer_raw']; w['transfer_raw']=witness_for(old.node_id,old.input_root,old.output_root,old.generation,current=False,verified=False)
        p=d.compile_plan(['transfer_raw'],w)
        self.assertIn('transfer_raw',p.invalidated)
        self.assertIn('source_receipt',p.reusable)
    def test_duplicate_node_generator_fails_closed(self):
        nodes=(n for n in [NodeSpec('a','raw',(),(),'x'),NodeSpec('a','raw',(),(),'x')])
        with self.assertRaisesRegex(DagError,'DUPLICATE_NODE'): EvidenceDag(nodes)

    def test_tampered_witness_fields_with_old_root_fail_closed(self):
        d=demo_dag(); w=demo_witnesses(d); w['source_receipt']=replace(w['source_receipt'], output_root='tampered')
        with self.assertRaisesRegex(DagError,'INVALID_WITNESS_ROOT'): d.compile_plan(['transfer_raw'],w)
    def test_truthy_nonbool_witness_state_fails_closed(self):
        d=demo_dag(); w=demo_witnesses(d); old=w['transfer_raw']
        w['transfer_raw']=Witness(old.node_id,old.input_root,old.output_root,old.generation,1,True,True,old.witness_root)
        with self.assertRaisesRegex(DagError,'INVALID_WITNESS_ROOT'): d.compile_plan(['transfer_raw'],w)
    def test_cycle_fails_closed(self):
        with self.assertRaisesRegex(DagError,'CYCLE'):
            EvidenceDag([NodeSpec('a','raw',('b',),(), 'x'),NodeSpec('b','raw',('a',),(), 'y')])
    def test_unknown_change_fails_closed(self):
        d=demo_dag(); w=demo_witnesses(d)
        with self.assertRaisesRegex(DagError,'UNKNOWN_NODE'): d.compile_plan(['bogus'],w)
    def test_plan_root_deterministic(self):
        d=demo_dag(); w=demo_witnesses(d)
        self.assertEqual(d.compile_plan(['transfer_raw','workload_raw'],w).plan_root,d.compile_plan(['workload_raw','transfer_raw'],w).plan_root)
    def test_hs1000_matches_graph_oracle(self):
        d=demo_dag(); w=demo_witnesses(d); rng=random.Random(20260905); nodes=list(d.nodes); false=0
        for _ in range(1000):
            changed=set(rng.sample(nodes,rng.randint(1,3))); p=d.compile_plan(changed,w)
            want=set(changed)
            while True:
                old=len(want)
                for n in d.nodes.values():
                    if any(dep in want for dep in n.deps): want.add(n.node_id)
                if len(want)==old: break
            false += set(p.invalidated)!=want
        self.assertEqual(false,0)
    def test_omega8_and_13d_noncompensation(self):
        admissible=sum(int(all(x==2 for x in s[:-1]) and s[-1]==1) for s in itertools.product(range(3), repeat=8))
        self.assertEqual(admissible,1)
        bad=(0,2,2,2,2,2,2,1)
        repairs=sum(int(all(x==2 for x in bad[:-1]) and bad[-1]==1) for _ in itertools.product(range(3), repeat=5))
        self.assertEqual(repairs,0)

if __name__=='__main__': unittest.main()
