import unittest
from dataclasses import replace
from tools.arena.proof_carrying_cache_consumption import *

def base():
    proto=ImmutableCacheArtifact("op","content","AUDIO","renderer","deps","producer-semantics","producer-receipt","PROJECT_TRUTH",True,"")
    art=replace(proto,claimed_artifact_root=proto.canonical_root())
    permit=RuntimeBoundConsumerPermit("op","source","permit",frozenset({"AUDIO","VIDEO"}),frozenset({"PROJECT_TRUTH"}),7,True,True)
    proc=EffectTimeProcessWitness("permit","source","process-current",True,True)
    req=CacheConsumptionRequest("op","source","content","AUDIO","renderer","deps","PROJECT_TRUTH","actor-a","view-a","K27:1,2,3",11)
    return art,permit,proc,req

class O21RTests(unittest.TestCase):
    def test_valid_reuse(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,r).disposition,Disposition.REUSE_D0)
    def test_k27_view_actor_do_not_change_artifact_identity(self):
        a,p,x,r=base(); d1=decide(a,p,x,r); r2=replace(r,actor="actor-b",view_id="view-b",k27_coordinate="K27:9,9,9",attempt_generation=12); d2=decide(a,p,x,r2); self.assertEqual(d1.artifact_root,d2.artifact_root); self.assertNotEqual(d1.consumption_receipt_root,d2.consumption_receipt_root)
    def test_producer_auth_required(self):
        a,p,x,r=base(); self.assertEqual(decide(replace(a,authenticated_producer=False),p,x,r).reason,"PRODUCER_PROVENANCE_NOT_AUTHENTICATED")
    def test_producer_receipt_required(self):
        a,p,x,r=base(); self.assertEqual(decide(replace(a,producer_receipt_root=""),p,x,r).reason,"PRODUCER_PROVENANCE_NOT_AUTHENTICATED")
    def test_claimed_root_checked(self):
        a,p,x,r=base(); self.assertEqual(decide(replace(a,claimed_artifact_root="poison"),p,x,r).reason,"CACHE_ARTIFACT_ROOT_MISMATCH")
    def test_operation_mismatch(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,replace(r,stable_operation_root="op2")).reason,"CACHE_OPERATION_MISMATCH")
    def test_content_mismatch(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,replace(r,content_root="other")).reason,"CACHE_CONTENT_MISMATCH")
    def test_output_kind_mismatch(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,replace(r,output_kind="VIDEO")).reason,"CACHE_OUTPUT_KIND_MISMATCH")
    def test_renderer_mismatch(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,replace(r,renderer_root="renderer2")).reason,"CACHE_RENDERER_SEMANTICS_MISMATCH")
    def test_dependency_mismatch(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,replace(r,dependency_closure_root="deps2")).reason,"CACHE_DEPENDENCY_CLOSURE_MISMATCH")
    def test_namespace_mismatch(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,replace(r,namespace="W_NATIVE")).reason,"CACHE_NAMESPACE_MISMATCH")
    def test_permit_operation_mismatch(self):
        a,p,x,r=base(); self.assertEqual(decide(a,replace(p,stable_operation_root="op2"),x,r).reason,"CONSUMER_PERMIT_OPERATION_MISMATCH")
    def test_permit_stale(self):
        a,p,x,r=base(); self.assertEqual(decide(a,replace(p,current=False),x,r).reason,"CONSUMER_PERMIT_STALE")
    def test_permit_not_proof_bound(self):
        a,p,x,r=base(); self.assertEqual(decide(a,replace(p,proof_bound=False),x,r).reason,"CONSUMER_PERMIT_NOT_PROOF_BOUND")
    def test_output_outside_permit(self):
        a,p,x,r=base(); self.assertEqual(decide(a,replace(p,allowed_output_kinds=frozenset({"VIDEO"})),x,r).reason,"OUTPUT_KIND_OUTSIDE_PERMIT")
    def test_namespace_outside_permit(self):
        a,p,x,r=base(); self.assertEqual(decide(a,replace(p,allowed_namespaces=frozenset({"W_NATIVE"})),x,r).reason,"CACHE_NAMESPACE_OUTSIDE_PERMIT")
    def test_source_incarnation_move(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,x,replace(r,source_incarnation_root="source2")).reason,"SOURCE_INCARNATION_MOVED")
    def test_process_stale(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,replace(x,current=False),r).reason,"EFFECT_TIME_PROCESS_NOT_CURRENT_AUTHENTIC")
    def test_process_unauthenticated(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,replace(x,authenticated=False),r).reason,"EFFECT_TIME_PROCESS_NOT_CURRENT_AUTHENTIC")
    def test_process_root_required(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,replace(x,effect_time_process_root=""),r).reason,"EFFECT_TIME_PROCESS_NOT_CURRENT_AUTHENTIC")
    def test_process_permit_binding(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,replace(x,runtime_bound_permit_root="permit2"),r).reason,"PROCESS_PERMIT_BINDING_MISMATCH")
    def test_process_source_binding(self):
        a,p,x,r=base(); self.assertEqual(decide(a,p,replace(x,source_incarnation_root="source2"),r).reason,"PROCESS_SOURCE_INCARNATION_MISMATCH")
    def test_artifact_root_excludes_volatile_context(self):
        a,p,x,r=base(); self.assertNotIn(r.actor,a.canonical_root()); self.assertEqual(a.canonical_root(),decide(a,p,x,r).artifact_root)
    def test_w_native_separate_namespace_can_be_valid_when_explicit(self):
        a,p,x,r=base(); proto=replace(a,namespace="W_NATIVE",claimed_artifact_root=""); a2=replace(proto,claimed_artifact_root=proto.canonical_root()); p2=replace(p,allowed_namespaces=frozenset({"W_NATIVE"})); r2=replace(r,namespace="W_NATIVE"); self.assertEqual(decide(a2,p2,x,r2).disposition,Disposition.REUSE_D0)
    def test_authority_ceiling(self):
        a,p,x,r=base(); d=decide(a,p,x,r); self.assertFalse(d.cache_write_authority or d.render_authority or d.effect_authority or d.gate10)

if __name__=="__main__": unittest.main()
