import itertools, random, unittest
from dataclasses import replace
import os, sys
ROOT=os.path.dirname(__file__)
sys.path.insert(0,ROOT)
from evidence_slice_dag import *


def admission_for(d,w, accepted=None, verifier_generation='agent09-e68b9188'):
    if accepted is None:
        accepted=tuple((k,v.witness_root) for k,v in w.items())
    return AdmissionSet(
        graph_root=d.graph_root,
        verifier_generations=(('AGENT09',verifier_generation),),
        accepted_witness_roots=tuple(accepted),
        observation_generation='obs-20260905',
        external_receipt_root=digest({'external':'agent09-admission-fixture'}),
    )


class EvidenceSliceDagTests(unittest.TestCase):
    def test_source_change_recomputes_all_descendants(self):
        d=demo_dag(); w=demo_witnesses(d); a=admission_for(d,w); p=d.compile_plan(['source_raw'],w,a)
        self.assertEqual(set(p.invalidated),set(d.nodes)); self.assertEqual(p.decision,'RECOMPUTE_ALL')

    def test_transfer_change_preserves_unrelated_slices(self):
        d=demo_dag(); w=demo_witnesses(d); p=d.compile_plan(['transfer_raw'],w,admission_for(d,w))
        self.assertEqual(set(p.invalidated),{'transfer_raw','cost_receipt','composite'})
        self.assertIn('workload_receipt',p.reusable); self.assertIn('trace_receipt',p.reusable)

    def test_workload_change_is_scoped(self):
        d=demo_dag(); w=demo_witnesses(d); p=d.compile_plan(['workload_raw'],w,admission_for(d,w))
        self.assertEqual(set(p.invalidated),{'workload_raw','workload_receipt','composite'})
        self.assertEqual(p.affected_consequence_keys,('admission','workload'))

    def test_trace_change_hits_trace_workload_cost_composite(self):
        d=demo_dag(); w=demo_witnesses(d); p=d.compile_plan(['trace_raw'],w,admission_for(d,w))
        self.assertEqual({'trace_raw','transfer_raw','trace_receipt','workload_receipt','cost_receipt','composite'},set(p.invalidated))
        self.assertIn('source_receipt',p.reusable)

    def test_self_valid_witness_without_external_admission_fails(self):
        d=demo_dag(); w=demo_witnesses(d); accepted=tuple((k,v.witness_root) for k,v in w.items() if k!='source_receipt')
        with self.assertRaisesRegex(DagError,'UNADMITTED_REUSE_WITNESS'):
            d.compile_plan(['transfer_raw'],w,admission_for(d,w,accepted))

    def test_verifier_generation_must_match_external_surface(self):
        d=demo_dag(); w=demo_witnesses(d)
        with self.assertRaisesRegex(DagError,'VERIFIER_GENERATION_MISMATCH'):
            d.compile_plan(['transfer_raw'],w,admission_for(d,w,verifier_generation='agent09-other'))

    def test_changed_witness_does_not_need_admission(self):
        d=demo_dag(); w=demo_witnesses(d); accepted=tuple((k,v.witness_root) for k,v in w.items() if k not in {'transfer_raw','cost_receipt','composite'})
        p=d.compile_plan(['transfer_raw'],w,admission_for(d,w,accepted))
        self.assertIn('transfer_raw',p.invalidated); self.assertIn('source_receipt',p.reusable)

    def test_duplicate_node_generator_fails_closed(self):
        nodes=(n for n in [NodeSpec('a','raw',(),(),'x','v'),NodeSpec('a','raw',(),(),'x','v')])
        with self.assertRaisesRegex(DagError,'DUPLICATE_NODE'): EvidenceDag(nodes)

    def test_tampered_witness_fields_with_old_root_fail_closed(self):
        d=demo_dag(); w=demo_witnesses(d); w['source_receipt']=replace(w['source_receipt'],output_root=digest({'tampered':1}))
        with self.assertRaisesRegex(DagError,'INVALID_WITNESS_ROOT'):
            d.compile_plan(['transfer_raw'],w,admission_for(d,w))

    def test_self_valid_but_detached_reusable_witness_fails_closed(self):
        d=demo_dag(); w=demo_witnesses(d); old=w['source_receipt']
        detached=make_witness(node_id=old.node_id,graph_root=old.graph_root,input_root=digest({'detached':'input'}),output_root=old.output_root,generation=old.generation,verifier_id=old.verifier_id,verifier_generation=old.verifier_generation,upstream_receipt_root=old.upstream_receipt_root)
        w['source_receipt']=detached
        a=admission_for(d,w)
        with self.assertRaisesRegex(DagError,'INVALID_DEPENDENCY_BINDING'):
            d.compile_plan(['transfer_raw'],w,a)

    def test_cross_graph_replay_fails_closed(self):
        d1=demo_dag(); w=demo_witnesses(d1); a=admission_for(d1,w)
        d2=EvidenceDag(list(d1.nodes.values())+[NodeSpec('extra','raw',(),('extra',),'X','AGENT09')])
        w2=dict(w); w2['extra']=make_witness(node_id='extra',graph_root=d2.graph_root,input_root=digest({'raw':'extra'}),output_root=digest({'out':'extra'}),generation='g1',verifier_id='AGENT09',verifier_generation='agent09-e68b9188',upstream_receipt_root=digest({'r':'x'}))
        with self.assertRaisesRegex(DagError,'ADMISSION_GRAPH_MISMATCH'):
            d2.compile_plan(['extra'],w2,a)

    def test_malformed_identity_types_fail_closed(self):
        with self.assertRaisesRegex(DagError,'INVALID_STRING:node_id'):
            NodeSpec(True,'raw',(),(),'x','v')
        with self.assertRaisesRegex(DagError,'INVALID_STRING:deps'):
            NodeSpec('a','raw',('',),(),'x','v')
        d=demo_dag(); w=demo_witnesses(d); old=w['source_raw']
        with self.assertRaisesRegex(DagError,'INVALID_HEX64:witness.output_root'):
            Witness(old.node_id,old.graph_root,old.input_root,'',old.generation,old.verifier_id,old.verifier_generation,old.upstream_receipt_root,old.witness_root)

    def test_permuted_dependency_and_key_declarations_are_canonical(self):
        nodes1=[
            NodeSpec('a','raw',(),('z','a'),'o','v'),
            NodeSpec('b','raw',(),('b',),'o','v'),
            NodeSpec('c','derived',('a','b'),('y','x'),'o','v'),
        ]
        nodes2=[
            NodeSpec('c','derived',('b','a'),('x','y'),'o','v'),
            NodeSpec('b','raw',(),('b',),'o','v'),
            NodeSpec('a','raw',(),('a','z'),'o','v'),
        ]
        d1=EvidenceDag(nodes1); d2=EvidenceDag(nodes2)
        self.assertEqual(d1.graph_root,d2.graph_root); self.assertEqual(d1.order,d2.order)

    def test_unknown_change_and_nonstring_change_fail_closed(self):
        d=demo_dag(); w=demo_witnesses(d); a=admission_for(d,w)
        with self.assertRaisesRegex(DagError,'UNKNOWN_NODE'): d.compile_plan(['bogus'],w,a)
        with self.assertRaisesRegex(DagError,'INVALID_STRING:changed_root'): d.compile_plan([True],w,a)

    def test_plan_root_deterministic(self):
        d=demo_dag(); w=demo_witnesses(d); a=admission_for(d,w)
        self.assertEqual(d.compile_plan(['transfer_raw','workload_raw'],w,a).plan_root,d.compile_plan(['workload_raw','transfer_raw'],w,a).plan_root)

    def test_hs1000_matches_graph_oracle(self):
        d=demo_dag(); w=demo_witnesses(d); a=admission_for(d,w); rng=random.Random(20260905); nodes=list(d.nodes); false=0
        for _ in range(1000):
            changed=set(rng.sample(nodes,rng.randint(1,3))); p=d.compile_plan(changed,w,a)
            want=set(changed)
            while True:
                old=len(want)
                for n in d.nodes.values():
                    if any(dep in want for dep in n.deps): want.add(n.node_id)
                if len(want)==old: break
            false += set(p.invalidated)!=want
        self.assertEqual(false,0)

    def test_omega8_and_13d_noncompensation(self):
        admissible=sum(int(all(x==2 for x in s[:-1]) and s[-1]==1) for s in itertools.product(range(3),repeat=8))
        self.assertEqual(admissible,1)
        bad=(0,2,2,2,2,2,2,1)
        repairs=sum(int(all(x==2 for x in bad[:-1]) and bad[-1]==1) for _ in itertools.product(range(3),repeat=5))
        self.assertEqual(repairs,0)


if __name__=='__main__': unittest.main()
