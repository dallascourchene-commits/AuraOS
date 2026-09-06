import unittest, random
from k27_city import *


class T(unittest.TestCase):
    def test_digit_bijection(self):
        for d in range(27): self.assertEqual(digit_from_xyz(*xyz_from_digit(d)),d)
    def test_recursive_27(self):
        p=K27Path((4,9))
        self.assertEqual(len({p.child(i) for i in range(27)}),27)
        self.assertTrue(all(p.is_prefix_of(p.child(i)) for i in range(27)))
    def test_xyz_trits(self):
        p=K27Path((0,13,26))
        xs,ys,zs=p.xyz_trits(); self.assertEqual(len(xs),3); self.assertEqual(digit_from_xyz(xs[1],ys[1],zs[1]),13)
    def test_morton_prefix(self):
        p=K27Path((2,3)); q=p.child(4)
        self.assertEqual(q.morton27(),p.morton27()*27+4)
    def test_lineage_inheritance(self):
        c=K27City(); root=K27Path(); city=K27Path((1,)); room=K27Path((1,5))
        c.add(Cell(root,'ROOT',rules={'safety':OverlayRule('safety','strict',True,False,1)}))
        c.add(Cell(city,'CITY',rules={'culture':OverlayRule('culture','research',False,True,2)}))
        c.add(Cell(room,'ROOM'))
        r=c.effective_rules(room); self.assertEqual(r['safety'].value,'strict'); self.assertEqual(r['culture'].value,'research')
    def test_hard_override_blocked(self):
        c=K27City(); c.add(Cell(K27Path(),'R',rules={'x':OverlayRule('x','A',True,False)})); c.add(Cell(K27Path((0,)),'C',rules={'x':OverlayRule('x','B')}))
        with self.assertRaises(ValueError): c.effective_rules(K27Path((0,)))
    def test_delegated_override(self):
        c=K27City(); c.add(Cell(K27Path(),'R',rules={'x':OverlayRule('x','A',True,True)})); c.add(Cell(K27Path((0,)),'C',rules={'x':OverlayRule('x','B')}))
        self.assertEqual(c.effective_rules(K27Path((0,)))['x'].value,'B')
    def test_rename_not_identity(self):
        c=K27City(); p=K27Path((1,2)); c.add(Cell(p,'drive:abc',display_name='Evidence Ave')); a=c.stable_identity(p); c.rename(p,'Proof Street'); self.assertEqual(a,c.stable_identity(p))
    def test_geography_profile_not_coordinate(self):
        p=K27Path((1,2,3,4,5)); self.assertEqual(scale_role(len(p.digits)),'neighborhood')
        self.assertEqual(p.digits,(1,2,3,4,5))
    def test_random_roundtrip(self):
        rnd=random.Random(7)
        for _ in range(10000):
            d=rnd.randrange(27); self.assertEqual(digit_from_xyz(*xyz_from_digit(d)),d)


if __name__=='__main__': unittest.main()
