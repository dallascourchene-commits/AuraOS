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
if __name__=='__main__': unittest.main()
