import unittest,itertools
from atomic_absorption import *
H='1'*64; T='2'*64
def P(i='A',base=H,cons=None,files=None,auth=False,actor=None,lineage=None):
    cons=cons or (str((int(i.encode().hex(),16)%10))*64)
    if not HEX64.fullmatch(cons): cons=digest(cons)
    return Proposal(i,actor or 'agent-'+i,lineage or 'lin-'+i,base,cons,digest('r'+i),files or {f'tools/{i}.py':digest('b'+i)},auth)
class Tst(unittest.TestCase):
    def s(self): return OwnerSnapshot(H,T)
    def test_disjoint_two_proposals_atomic(self):
        q=plan(self.s(),[P('A'),P('B')]); self.assertEqual(q.disposition,Disposition.READY); r=commit(q,H); self.assertTrue(r.committed); self.assertEqual(r.write_count,2); self.assertEqual(r.lost_consequence_count,0)
    def test_stale_any_rebases_all(self): self.assertEqual(plan(self.s(),[P('A'),P('B',base='3'*64)]).disposition,Disposition.REBASE_REQUIRED)
    def test_cas_movement_zero_write(self):
        q=plan(self.s(),[P('A')]); r=commit(q,'4'*64); self.assertFalse(r.committed); self.assertEqual(r.write_count,0); self.assertEqual(r.lost_consequence_count,1)
    def test_conflicting_path_holds(self):
        a=P('A',files={'x':digest('a')}); b=P('B',files={'x':digest('b')}); self.assertEqual(plan(self.s(),[a,b]).disposition,Disposition.CONFLICT_HOLD)
    def test_identical_path_blob_safe(self):
        d=digest('x'); q=plan(self.s(),[P('A',files={'x':d}),P('B',files={'x':d})]); self.assertEqual(q.disposition,Disposition.READY); self.assertEqual(len(q.writes),1)
    def test_duplicate_consequence_exact_redelivery_collapses(self):
        c=digest('same'); a=P('A',cons=c); b=Proposal('B','agent-B','lin-B',H,c,a.receipt_root,dict(a.files)); q=plan(self.s(),[a,b]); self.assertEqual(len(q.accepted_proposals),1); self.assertEqual(q.collapsed_proposals,('B',))
    def test_staging_marker_holds(self): self.assertEqual(plan(self.s(),[P('A',files={'x/.v5-stage-marker':digest('x')})]).disposition,Disposition.DEBRIS_HOLD)
    def test_effect_authority_holds(self): self.assertEqual(plan(self.s(),[P('A',auth=True)]).disposition,Disposition.AUTHORITY_HOLD)
    def test_bad_blob_fails(self):
        with self.assertRaises(E): plan(self.s(),[P('A',files={'x':'no'})])
    def test_bad_path_fails(self):
        with self.assertRaises(E): plan(self.s(),[P('A',files={'../x':digest('x')})])
    def test_manifest_deterministic_order(self): self.assertEqual(plan(self.s(),[P('B'),P('A')]).manifest_root,plan(self.s(),[P('A'),P('B')]).manifest_root)
    def test_no_proposals(self):
        with self.assertRaises(E): plan(self.s(),[])
    def test_hold_commit_no_write(self):
        q=plan(self.s(),[P('A',base='3'*64)]); r=commit(q,H); self.assertFalse(r.committed); self.assertEqual(r.write_count,0)
    def test_omega8_one_keeper(self): self.assertEqual(sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8)),1)
    def test_13d_no_repair(self): self.assertEqual(sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5)),0)
if __name__=='__main__': unittest.main()
