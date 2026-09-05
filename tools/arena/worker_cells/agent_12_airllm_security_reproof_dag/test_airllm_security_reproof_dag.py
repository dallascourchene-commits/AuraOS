import itertools
import os
import sys
import unittest
from dataclasses import replace

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
from airllm_security_reproof_dag import *


def fixture():
    nodes = airllm_security_nodes(); by = {n.node_id:n for n in nodes}
    outputs = {n.node_id: digest({"output":n.node_id,"v":1}) for n in nodes}
    verifiers = {n.node_id: digest({"verifier":n.node_id,"security":AIRLLM_SECURITY_PARENT}) for n in nodes}
    witnesses = {n.node_id: make_witness(n, outputs[n.node_id], outputs, verifiers[n.node_id]) for n in nodes}
    return nodes, by, outputs, verifiers, witnesses

class SecurityDAGTests(unittest.TestCase):
    def test_01_graph_deterministic(self):
        nodes,*_ = fixture(); self.assertEqual(graph_root(nodes), graph_root(reversed(nodes))); self.assertEqual(graph_root(nodes), CANONICAL_GRAPH_ROOT)
    def test_02_model_change_recomputes_security_chain(self):
        _,_,o,v,w=fixture(); p=compile_reproof_plan(["MODEL_BYTES"],w,o,v)
        expected={"MODEL_BYTES","SAFETENSORS_STRUCTURE","MODEL_ALLOWLIST","SECURE_ENTRYPOINT","SECURITY_RECEIPT","TRACE_WORKLOAD_REUSE","FINAL_REUSE_RECEIPT"}
        self.assertEqual(set(p.recompute_order),expected); self.assertTrue(p.verify())
    def test_03_package_change_recomputes_remote_code_and_entrypoint(self):
        _,_,o,v,w=fixture(); p=compile_reproof_plan(["PACKAGE_MANIFEST"],w,o,v)
        self.assertEqual(set(p.recompute_order),{"PACKAGE_MANIFEST","REMOTE_CODE_POLICY","SECURE_ENTRYPOINT","SECURITY_RECEIPT","TRACE_WORKLOAD_REUSE","FINAL_REUSE_RECEIPT"})
    def test_04_trace_change_is_narrow(self):
        _,_,o,v,w=fixture(); p=compile_reproof_plan(["TRACE_PROVENANCE"],w,o,v)
        self.assertEqual(set(p.recompute_order),{"TRACE_PROVENANCE","TRACE_WORKLOAD_REUSE","FINAL_REUSE_RECEIPT"}); self.assertIn("SECURITY_RECEIPT",p.reusable)
    def test_05_workload_change_is_narrow(self):
        _,_,o,v,w=fixture(); p=compile_reproof_plan(["WORKLOAD_ENV"],w,o,v)
        self.assertEqual(set(p.recompute_order),{"WORKLOAD_ENV","TRACE_WORKLOAD_REUSE","FINAL_REUSE_RECEIPT"})
    def test_06_no_change_reuses_all(self):
        nodes,_,o,v,w=fixture(); p=compile_reproof_plan([],w,o,v); self.assertEqual(p.decision,Decision.REUSE_ALL); self.assertEqual(len(p.reusable),len(nodes))
    def test_07_unknown_change_fails(self):
        _,_,o,v,w=fixture(); self.assertRaises(SecurityPlanError,compile_reproof_plan,["UNKNOWN"],w,o,v)
    def test_08_weaker_graph_fails(self):
        nodes,_,o,v,w=fixture(); self.assertRaises(SecurityPlanError,compile_reproof_plan,["MODEL_BYTES"],w,o,v,nodes[:-1])
    def test_09_witness_tamper_fails(self):
        _,_,o,v,w=fixture(); w=dict(w); w["PACKAGE_MANIFEST"]=replace(w["PACKAGE_MANIFEST"],output_root="0"*64); self.assertRaises(SecurityPlanError,compile_reproof_plan,["TRACE_PROVENANCE"],w,o,v)
    def test_10_dependency_detach_fails(self):
        _,_,o,v,w=fixture(); o=dict(o); o["LOADER_SOURCE"]=digest({"changed":1}); self.assertRaises(SecurityPlanError,compile_reproof_plan,["TRACE_PROVENANCE"],w,o,v)
    def test_11_verifier_drift_fails(self):
        _,_,o,v,w=fixture(); v=dict(v); v["MODEL_ALLOWLIST"]=digest({"other":1}); self.assertRaises(SecurityPlanError,compile_reproof_plan,["TRACE_PROVENANCE"],w,o,v)
    def test_12_parent_generation_replay_fails(self):
        _,_,o,v,w=fixture(); w=dict(w); x=w["MODEL_ALLOWLIST"]; w["MODEL_ALLOWLIST"]=replace(x,security_generation="1"*40,witness_root=x.witness_root); self.assertRaises(SecurityPlanError,compile_reproof_plan,["TRACE_PROVENANCE"],w,o,v)
    def test_13_incomplete_outputs_fail(self):
        _,_,o,v,w=fixture(); o=dict(o); o.pop("MODEL_BYTES"); self.assertRaises(SecurityPlanError,compile_reproof_plan,[],w,o,v)
    def test_14_incomplete_witnesses_fail(self):
        _,_,o,v,w=fixture(); w=dict(w); w.pop("MODEL_BYTES"); self.assertRaises(SecurityPlanError,compile_reproof_plan,[],w,o,v)
    def test_15_malformed_identity_fails(self):
        nodes,_,o,v,w=fixture(); bad=list(nodes); bad[0]=NodeSpec(True,(),("X",),True); self.assertRaises(SecurityPlanError,graph_root,bad)
    def test_16_duplicate_dependency_fails(self):
        nodes,_,o,v,w=fixture(); bad=list(nodes); bad[5]=NodeSpec("SAFETENSORS_STRUCTURE",("MODEL_BYTES","MODEL_BYTES"),("SERIALIZATION_SAFETY",)); self.assertRaises(SecurityPlanError,graph_root,bad)
    def test_17_dependency_order_canonical(self):
        nodes,_,o,v,w=fixture(); altered=[]
        for n in nodes:
            altered.append(NodeSpec(n.node_id,tuple(reversed(n.deps)),tuple(reversed(n.consequence_keys)),n.raw))
        self.assertEqual(graph_root(nodes),graph_root(altered))
    def test_18_authority_ceiling(self):
        _,_,o,v,w=fixture(); p=compile_reproof_plan(["MODEL_BYTES"],w,o,v); self.assertTrue(p.d0); self.assertFalse(p.truth_authority); self.assertFalse(p.effect_authority); self.assertFalse(p.gate10)
    def test_19_plan_tamper_rejected(self):
        _,_,o,v,w=fixture(); p=compile_reproof_plan(["MODEL_BYTES"],w,o,v); self.assertFalse(replace(p,plan_root="0"*64).verify())
    def test_20_omega8_exact_keeper(self):
        keep=sum(crystalline_admission(s) for s in itertools.product(range(3),repeat=8)); self.assertEqual(keep,1)
    def test_21_13d_nonrepair(self):
        for tail in itertools.product(range(3),repeat=5): self.assertFalse(admission_13d((0,2,2,2,2,2,2,2)+tail))
    def test_22_bool_axis_fails(self): self.assertFalse(admission_13d((True,2,2,2,2,2,2,2,0,0,0,0,0)))
    def test_23_multiple_changes_union_closure(self):
        _,_,o,v,w=fixture(); p=compile_reproof_plan(["TRACE_PROVENANCE","PACKAGE_MANIFEST"],w,o,v); self.assertIn("REMOTE_CODE_POLICY",p.recompute_order); self.assertIn("TRACE_PROVENANCE",p.recompute_order); self.assertEqual(len(p.recompute_order),7)
    def test_24_changed_node_witness_may_be_stale(self):
        _,_,o,v,w=fixture(); w=dict(w); w["MODEL_BYTES"]=replace(w["MODEL_BYTES"],witness_root="0"*64); p=compile_reproof_plan(["MODEL_BYTES"],w,o,v); self.assertIn("MODEL_BYTES",p.recompute_order)
    def test_25_reusable_raw_witness_still_verified(self):
        _,_,o,v,w=fixture(); w=dict(w); w["WORKLOAD_ENV"]=replace(w["WORKLOAD_ENV"],verifier_root="0"*64); self.assertRaises(SecurityPlanError,compile_reproof_plan,["MODEL_BYTES"],w,o,v)
    def test_26_cross_graph_reuse_fails(self):
        _,_,o,v,w=fixture(); w=dict(w); x=w["MODEL_ALLOWLIST"]; w["MODEL_ALLOWLIST"]=replace(x,graph_root="0"*64); self.assertRaises(SecurityPlanError,compile_reproof_plan,["TRACE_PROVENANCE"],w,o,v)

if __name__ == "__main__": unittest.main()
