import unittest,itertools
from tools.arena.worker_cells.gpt56sol_astra_probe_induced_coupling_closure_r1 import *
class TestCoupling(unittest.TestCase):
 def cert(self,current=True,complete=True):
  l=frozenset({'a','b'});r=frozenset({'c','d'});pairs=frozenset(edge(x,y) for x in l for y in r);return CutCertificate(l,r,pairs if complete else frozenset({edge('a','c')}),current)
 def test_read_only(self):self.assertEqual(compile_independence(self.cert(),[edge('a','b'),edge('c','d')],[EvidenceProbe('read',frozenset(),True,False)]).status,'READY_D0')
 def test_cross_probe_holds(self):self.assertEqual(compile_independence(self.cert(),[],[EvidenceProbe('p',frozenset({edge('b','c')}))]).status,'HOLD_PROBE_INDUCED_COUPLING')
 def test_naive_false_ready(self):
  c=self.cert();ps=[EvidenceProbe('p',frozenset({edge('a','d')}))];self.assertTrue(naive_preprobe_independence(c,[],ps));self.assertFalse(oracle_independence_after_probes(c,[],ps))
 def test_incomplete_cut(self):self.assertEqual(compile_independence(self.cert(complete=False),[],[]).status,'HOLD_INCOMPLETE_CUT')
 def test_stale_cert(self):self.assertEqual(compile_independence(self.cert(current=False),[],[]).status,'HOLD_CERT_CURRENTNESS')
 def test_stale_probe(self):self.assertEqual(compile_independence(self.cert(),[],[EvidenceProbe('p',frozenset(),False)]).status,'HOLD_PROBE_CURRENTNESS')
 def test_initial_cross(self):self.assertEqual(compile_independence(self.cert(),[edge('a','c')],[]).status,'HOLD_ALREADY_COUPLED')
 def test_changed_cone_local(self):
  c=CutCertificate(frozenset({'a','b'}),frozenset({'c','d','e'}),frozenset(edge(x,y) for x in {'a','b'} for y in {'c','d','e'}));d=compile_independence(c,[edge('a','b'),edge('c','d')],[EvidenceProbe('local',frozenset({edge('d','e')}))]);self.assertEqual(d.status,'READY_D0');self.assertEqual(d.changed_cone,frozenset({'c','d','e'}))
 def test_join_order_final_graph(self):
  ps=[EvidenceProbe('p1',frozenset({edge('a','b')})),EvidenceProbe('p2',frozenset({edge('b','c')})),EvidenceProbe('p3',frozenset({edge('c','d')}))];self.assertEqual(len({compile_independence(self.cert(),[],x).final_edges for x in itertools.permutations(ps)}),1)
 def test_k27_nonauthority(self):
  d=compile_independence(self.cert(),[],[EvidenceProbe('p',frozenset({edge('a','c')}))],k27_coordinate='K27:HOT');self.assertNotEqual(d.status,'READY_D0');self.assertFalse(d.effect_authority);self.assertFalse(d.gate10)
 def test_empty_change_cone(self):self.assertEqual(compile_independence(self.cert(),[],[]).changed_cone,frozenset())
 def test_trusted_partition_actual_cross_still_holds(self):
  c=CutCertificate(frozenset({'a'}),frozenset({'b'}),frozenset(),True,True);self.assertEqual(compile_independence(c,[],[EvidenceProbe('p',frozenset({edge('a','b')}))]).status,'HOLD_PROBE_INDUCED_COUPLING')
if __name__=='__main__':unittest.main()
