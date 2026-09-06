import unittest
from world_atlas import *


class T(unittest.TestCase):
    def setUp(self):
        self.a=WorldFrame('CITY_A','g1','e1','CANONICAL')
        self.b=WorldFrame('WORLD','g7','e1','GENERATED')
        self.at=FrameAtlas(); self.at.add_frame(self.a); self.at.add_frame(self.b)
        self.t=FrameTransform('CITY_A','g1','WORLD','g7',axis_perm=(2,0,1),invert=(False,True,False))
        self.at.add_transform(self.t)
        self.x=FrameAddress('CITY_A','g1',(1,5,26,3),'drive:abc')
    def test_path_is_frame_qualified(self):
        y=FrameAddress('WORLD','g7',self.x.path,'drive:abc')
        self.assertNotEqual((self.x.frame_id,self.x.path),(y.frame_id,y.path))
    def test_transform_required(self):
        self.at.transforms.clear()
        with self.assertRaises(ValueError): self.at.project(self.x,'WORLD')
    def test_transform_preserves_identity(self):
        y=self.at.project(self.x,'WORLD')
        self.assertEqual(y.canonical_ref,self.x.canonical_ref)
        self.assertEqual(y.frame_id,'WORLD')
        self.assertNotEqual(y.path,self.x.path)
    def test_generation_drift_holds(self):
        self.at.frames['CITY_A']=WorldFrame('CITY_A','g2','e1','CANONICAL')
        with self.assertRaises(ValueError): self.at.project(self.x,'WORLD')
    def test_stale_transform_holds(self):
        self.at.transforms[('CITY_A','WORLD')]=FrameTransform('CITY_A','g1','WORLD','g7',current=False)
        with self.assertRaises(ValueError): self.at.project(self.x,'WORLD')
    def test_27_children_collapse(self):
        c=PrefixCoverage('WORLD','g7',[(4,d) for d in range(27)])
        self.assertEqual(c.prefixes,frozenset({(4,)}))
    def test_incomplete_does_not_collapse(self):
        c=PrefixCoverage('WORLD','g7',[(4,d) for d in range(26)])
        self.assertEqual(c.records(),26)
    def test_coverage_is_frame_isolated(self):
        c=PrefixCoverage('CITY_A','g1',[(1,5)])
        self.assertTrue(c.covers(self.x))
        y=self.at.project(self.x,'WORLD')
        self.assertFalse(c.covers(y))
    def test_portal_no_authority(self):
        p=WorldPortal('P','CITY_A','WORLD',('CITY_A','WORLD'))
        self.assertIsNone(p.authority)
    def test_zoom_prefixes(self):
        z=zoom_lineage(self.x)
        self.assertEqual(z[0],())
        self.assertEqual(z[-1],self.x.path)
        self.assertEqual(len(z),len(self.x.path)+1)


if __name__=='__main__': unittest.main()
