import unittest
from dataclasses import replace
import random
from provider_bound_efficiency_rebind import *

PARENT="a"*40; CHILD="b"*40; GEN="AuraOS CODEMAP Bot"; ALLOWED=(".aura/CODEMAP.json",".aura/CODEMAP.md"); CHANGED=ALLOWED; RUNTIME="1"*64

def projection(**changes):
    d=dict(semantic_source_head=PARENT,runtime_sha256=RUNTIME,trace_projection={"event_root":"trace","events":8192,"schema":"fused-v1"},cost_projection={"transfer_root":"cost","bytes":1000,"spec_bytes":10,"schema":"cost-v1"},benchmark_generation="bench-1",hardware_fingerprint="host-1"); d.update(changes); return EfficiencyProjection(**d)
def movement(**changes):
    d=dict(proved_parent_head=PARENT,current_child_head=CHILD,observed_parent_head=PARENT,observed_child_head=CHILD,observed_generator_identity=GEN,expected_generator_identity=GEN,changed_paths=CHANGED,allowed_proof_neutral_paths=ALLOWED,expected_provider_observation_root=observation_root(PARENT,CHILD,GEN,CHANGED),provider_observation_verified=True); d.update(changes); return ProviderMovement(**d)
def evidence(m=None,old=None,cur=None,**changes):
    old=old or projection(); cur=cur or projection(); d=dict(movement=m or movement(),proof_time_projection=old,current_projection=cur,expected_proof_time_projection_root=old.projection_root,expected_current_projection_root=cur.projection_root,authority_requested=False); d.update(changes); return RebindEvidence(**d)

class Tests(unittest.TestCase):
    def test_valid_provider_bound_reuse(self):
        e=evidence(); r=make_receipt(e); self.assertEqual(r.decision,Decision.REUSE_AFTER_PROVIDER_BOUND_REBIND); self.assertTrue(verify_receipt(e,r))
    def test_imaginary_child_cannot_pass_root(self): self.assertEqual(decide(evidence(m=movement(current_child_head="c"*40,observed_child_head="c"*40))),Decision.REPROVE)
    def test_parent_binding_required(self): self.assertIn("PROVIDER_PARENT_MISMATCH",reasons(evidence(m=movement(observed_parent_head="c"*40)))[0])
    def test_child_binding_required(self): self.assertIn("PROVIDER_CHILD_MISMATCH",reasons(evidence(m=movement(observed_child_head="c"*40)))[0])
    def test_generator_identity_exact(self): self.assertEqual(decide(evidence(m=movement(observed_generator_identity="Other Bot"))),Decision.REPROVE)
    def test_non_neutral_path_rejected(self): self.assertEqual(decide(evidence(m=movement(changed_paths=ALLOWED+("tools/arena/frontier27_runtime.py",)))),Decision.REPROVE)
    def test_observation_root_must_be_external_expected(self): self.assertEqual(decide(evidence(m=movement(expected_provider_observation_root="f"*64))),Decision.REPROVE)
    def test_provider_external_verification_required(self): self.assertEqual(decide(evidence(m=movement(provider_observation_verified=False))),Decision.REPROVE)
    def test_bool_type_strict(self): self.assertEqual(decide(evidence(m=movement(provider_observation_verified=1))),Decision.REPROVE)
    def test_wrong_agent27_generation(self): self.assertEqual(decide(evidence(m=movement(agent27_semantic_commit="c"*40))),Decision.REPROVE)
    def test_wrong_agent08_generation(self): self.assertEqual(decide(evidence(cur=projection(agent08_semantic_commit="c"*40))),Decision.REPROVE)
    def test_runtime_drift(self): self.assertIn("RUNTIME_DRIFT",reasons(evidence(cur=projection(runtime_sha256="2"*64))))
    def test_trace_projection_drift(self): self.assertIn("TRACE_PROJECTION_DRIFT",reasons(evidence(cur=projection(trace_projection={"event_root":"different","events":8192,"schema":"fused-v1"}))))
    def test_cost_projection_drift(self): self.assertIn("COST_PROJECTION_DRIFT",reasons(evidence(cur=projection(cost_projection={"transfer_root":"different","bytes":1000,"spec_bytes":10,"schema":"cost-v1"}))))
    def test_benchmark_drift(self): self.assertIn("BENCHMARK_GENERATION_DRIFT",reasons(evidence(cur=projection(benchmark_generation="bench-2"))))
    def test_hardware_drift(self): self.assertIn("HARDWARE_ENVELOPE_DRIFT",reasons(evidence(cur=projection(hardware_fingerprint="host-2"))))
    def test_current_projection_must_keep_semantic_parent(self): self.assertIn("CURRENT_SEMANTIC_SOURCE_DRIFT",reasons(evidence(cur=projection(semantic_source_head=CHILD))))
    def test_expected_proof_root_pinned(self): self.assertIn("PROOF_TIME_PROJECTION_ROOT_MISMATCH",reasons(evidence(expected_proof_time_projection_root="f"*64)))
    def test_expected_current_root_pinned(self): self.assertIn("CURRENT_PROJECTION_ROOT_MISMATCH",reasons(evidence(expected_current_projection_root="f"*64)))
    def test_authority_request_reproves(self): self.assertEqual(decide(evidence(authority_requested=True)),Decision.REPROVE)
    def test_receipt_tamper(self):
        e=evidence(); r=make_receipt(e); self.assertFalse(verify_receipt(e,replace(r,child_head="c"*40)))
    def test_receipt_hard_false_authority(self):
        r=make_receipt(evidence()); self.assertFalse(r.fresh_hosted_pass); self.assertFalse(r.effect_authority); self.assertFalse(r.gate10)
    def test_path_order_canonical(self): self.assertEqual(observation_root(PARENT,CHILD,GEN,ALLOWED),observation_root(PARENT,CHILD,GEN,tuple(reversed(ALLOWED))))
    def test_duplicate_path_rejected(self):
        with self.assertRaisesRegex(RebindError,"DUPLICATE_CHANGED_PATH"): observation_root(PARENT,CHILD,GEN,(ALLOWED[0],ALLOWED[0]))
    def test_omega8_single_keeper(self):
        c=exhaustive8(); self.assertEqual(sum(c.values()),3**8); self.assertEqual(c.get("REUSE_AFTER_PROVIDER_BOUND_REBIND"),1)
    def test_13d_tail_actually_matters(self):
        core=(2,2,2,2,2,2,2,1); self.assertEqual(classify13(core+(2,2,2,2,2)),"REUSE_AFTER_PROVIDER_BOUND_REBIND"); self.assertNotEqual(classify13(core+(0,2,2,2,2)),"REUSE_AFTER_PROVIDER_BOUND_REBIND")
    def test_13d_cannot_repair_invalid_core(self):
        rng=random.Random(10)
        for _ in range(10000):
            core=[2,2,2,2,2,2,2,1]; core[rng.randrange(7)]=0; tail=tuple(rng.randrange(3) for _ in range(5)); self.assertNotEqual(classify13(tuple(core)+tail),"REUSE_AFTER_PROVIDER_BOUND_REBIND")

if __name__=="__main__": unittest.main()
