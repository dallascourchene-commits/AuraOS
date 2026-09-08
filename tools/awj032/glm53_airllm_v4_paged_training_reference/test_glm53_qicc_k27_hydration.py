import unittest
from dataclasses import replace
from glm53_paged_training import default_source
from glm53_qicc_k27_hydration import *
class T(unittest.TestCase):
    def test_same_pages_different_route_reuses_hydration_not_replay(self):
        a=[(0,1),(2,3)]; b=[(0,2),(1,3)]
        kw=dict(layer=5,adapter_generation='ag',optimizer_generation='og',qicc_runtime_fingerprint='qicc-r1')
        x=mint_k27_hydration_lease(default_source(),a,**kw); y=mint_k27_hydration_lease(default_source(),b,**kw)
        self.assertEqual(x.page_set,(0,1,2,3)); self.assertTrue(can_reuse_hydration(x,y))
        self.assertTrue(replay_identity_differs(a,b,layer=5,pager_binding=default_source().pager_binding))
    def test_different_pages_do_not_reuse(self):
        kw=dict(layer=5,adapter_generation='ag',optimizer_generation='og',qicc_runtime_fingerprint='qicc-r1')
        a=mint_k27_hydration_lease(default_source(),[(0,1),(2,3)],**kw)
        b=mint_k27_hydration_lease(default_source(),[(0,1),(2,4)],**kw)
        self.assertFalse(can_reuse_hydration(a,b))
    def test_source_or_optimizer_drift_blocks_reuse(self):
        r=[(0,1),(2,3)]; kw=dict(layer=5,adapter_generation='ag',optimizer_generation='og',qicc_runtime_fingerprint='qicc-r1')
        a=mint_k27_hydration_lease(default_source(),r,**kw)
        b=mint_k27_hydration_lease(replace(default_source(),index_digest='other'),r,**kw)
        c=mint_k27_hydration_lease(default_source(),r,**{**kw,'optimizer_generation':'og2'})
        self.assertFalse(can_reuse_hydration(a,b)); self.assertFalse(can_reuse_hydration(a,c))
if __name__=='__main__':unittest.main()
