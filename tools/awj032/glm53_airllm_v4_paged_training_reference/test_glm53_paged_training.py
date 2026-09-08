import itertools,random,unittest
from dataclasses import replace
from glm53_paged_training import *

def routes(n,seed=0,hot=False):
    rng=random.Random(seed); out=[]
    for _ in range(n):
        pool=list(range(32)) if hot and rng.random()<.95 else list(range(256)); out.append(tuple(rng.sample(pool,8)))
    return out
class T(unittest.TestCase):
    def test_v4_rank16_residency_is_blocked(self):
        r=assess(default_source(),default_abi(),default_policy()); self.assertEqual(r.decision,Decision.BLOCK_ADAPTER_RESIDENCY); self.assertEqual(r.full_sparse_lora_params,5662310400)
    def test_adapter_paging_closes_only_to_empirical(self):
        p=replace(default_policy(),adapter_paging_or_layer_locality=True); self.assertEqual(assess(default_source(),default_abi(),p).decision,Decision.HOLD_EMPIRICAL)
    def test_previous_airllm_pin_is_stale_for_v4_training(self):
        s=replace(default_source(),semantic_commit=AIRLLM_PREVIOUS_AURA_PIN); self.assertEqual(assess(s,default_abi(),replace(default_policy(),adapter_paging_or_layer_locality=True)).decision,Decision.BLOCK_SOURCE)
    def test_qwen_type_identity_is_not_glm_abi(self):
        a=replace(default_abi(),expert_class=UPSTREAM_PACKED_LORA_CLASS); self.assertEqual(assess(default_source(),a,replace(default_policy(),adapter_paging_or_layer_locality=True)).decision,Decision.BLOCK_EXPERT_ABI)
    def test_geometry(self):
        g=Geometry(); self.assertEqual(g.expert_bytes(256),9663676416); self.assertEqual(g.expert_bytes(8),301989888); self.assertEqual(1-g.expert_bytes(8)/g.expert_bytes(256),.96875)
    def test_forward_backward_lease(self):
        x=routes(1,1); l=mint_forward_lease(default_source(),x,attempt='a',layer=9,adapter_generation='ag',optimizer_generation='og'); self.assertTrue(backward_ready(l,default_source(),x,attempt='a',adapter_generation='ag',optimizer_generation='og',pages=l.pages))
        self.assertFalse(backward_ready(l,default_source(),routes(1,2),attempt='a',adapter_generation='ag',optimizer_generation='og',pages=l.pages))
    def test_eight_corner_noncompensation(self):
        ready=0
        for sec,pager,replay in itertools.product([False,True],repeat=3):
            s=default_source() if sec else replace(default_source(),hard_false_digest='')
            a=default_abi() if pager else replace(default_abi(),selected_pager=False)
            p=replace(default_policy(),adapter_paging_or_layer_locality=True,route_replay_identity=replay)
            ready += assess(s,a,p).decision==Decision.HOLD_EMPIRICAL
        self.assertEqual(ready,1)
    def test_hs1000_route_union_exact(self):
        seen=set()
        for seed in range(1000):
            x=routes(random.Random(seed).randint(1,8),seed); ids=route_union(x); seen.update(ids); self.assertEqual(ids,tuple(sorted({q for row in x for q in row})))
        self.assertEqual(seen,set(range(256)))
    def test_chunk_lease_uniform_512_six_gib(self):
        l=choose_chunk(routes(512,8),device_budget=6*1024**3,reserved_nonexpert=1*1024**3); self.assertEqual(l.chunk_tokens,16); self.assertIsNone(l.physical_io_bytes)
    def test_hot_routes_admit_no_smaller_chunk(self):
        u=choose_chunk(routes(512,7),device_budget=6*1024**3,reserved_nonexpert=1*1024**3); h=choose_chunk(routes(512,7,True),device_budget=6*1024**3,reserved_nonexpert=1*1024**3); self.assertGreaterEqual(h.chunk_tokens,u.chunk_tokens)
    def test_same_union_different_route_rejected(self):
        a=[(0,1),(2,3)]; b=[(0,2),(1,3)]; self.assertEqual(route_union(a),route_union(b))
        l=mint_forward_lease(default_source(),a,attempt='x',layer=2,adapter_generation='ag',optimizer_generation='og')
        self.assertFalse(backward_ready(l,default_source(),b,attempt='x',adapter_generation='ag',optimizer_generation='og',pages=l.pages))
    def test_topk_order_is_route_identity(self):
        a=[(0,1,2,3)]; b=[(3,2,1,0)]; self.assertEqual(route_union(a),route_union(b)); self.assertNotEqual(route_root(a,layer=1,pager_binding='p'),route_root(b,layer=1,pager_binding='p'))
    def test_bitset_profile_hs1000_matches_sets(self):
        rng=random.Random(991); C=(1,2,4,8,16,32,64)
        for _ in range(1000):
            n=rng.randint(1,64); rs=[tuple(rng.sample(range(256),8)) for _ in range(n)]
            for c,peak,total,counts in chunk_profile(rs,C):
                ref=[len({x for row in rs[s:s+c] for x in row}) for s in range(0,n,c)]
                self.assertEqual((peak,total,counts),(max(ref),sum(ref),tuple(ref)))
    def test_conditioned_plan_vs_hydration_vs_invocation(self):
        a=[(0,1),(2,3),(0,2),(1,3)]; b=[(10,11),(12,13),(10,12),(11,13)]
        kw=dict(layer=5,adapter_generation='ag',optimizer_generation='og',device_budget=6<<30,reserved_nonexpert=1<<30,candidates=(1,2,4),qicc_runtime_fingerprint='qicc-r1')
        x=mint_conditioned_plan_lease(default_source(),a,invocation_id='i1',**kw); y=mint_conditioned_plan_lease(default_source(),b,invocation_id='i2',**kw)
        self.assertEqual(x.profile_root,y.profile_root); self.assertTrue(can_reuse_plan(x,y)); self.assertFalse(can_reuse_hydration(x,y)); self.assertFalse(same_invocation(x,y))
    def test_condition_change_blocks_plan_reuse(self):
        r=routes(16,5); kw=dict(invocation_id='i',layer=2,adapter_generation='ag',optimizer_generation='og',device_budget=6<<30,reserved_nonexpert=1<<30,qicc_runtime_fingerprint='qicc-r1')
        a=mint_conditioned_plan_lease(default_source(),r,**kw); b=mint_conditioned_plan_lease(replace(default_source(),model_revision='new'),r,**kw); self.assertFalse(can_reuse_plan(a,b))
    def test_separator_no_mimic(self):
        d=[tuple(range(8)),tuple(range(8)),tuple(range(16,24)),tuple(range(16,24))]; s=separator_receipt(d,chunk_tokens=1); self.assertTrue(s.factorized); self.assertEqual(s.component_count,2)
        c=[(0,1),(1,2),(2,3),(3,4)]; s=separator_receipt(c,chunk_tokens=1); self.assertFalse(s.factorized); self.assertEqual(s.component_count,1)
if __name__=='__main__': unittest.main()
