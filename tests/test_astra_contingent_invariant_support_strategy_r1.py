import unittest
from tools.arena.worker_cells.gpt56sol_astra_contingent_invariant_support_strategy_r1 import *
class T(unittest.TestCase):
 def sensor(self,hi=2,current=True):return Sensor('sense',Interval(1,hi),current)
 def task(self,n,o,hi,res,supp,current=True):return Task(n,o,Interval(1,hi),res,frozenset(supp),current)
 def test_dynamic_branch_beats_static_union(self):
  ts=(self.task('a',0,4,'r1',{'x'}),self.task('b',1,4,'r2',{'x'}));s=self.sensor(2);p=compile_strategy(s,ts,6);self.assertEqual(p.status,'READY_D0');self.assertGreater(static_union_finish(s,ts),6)
 def test_resource_only_false_ready_hidden_invariant(self):
  ts=(self.task('a',0,4,'r1',{'x'}),self.task('b',0,4,'r2',{'x'}),self.task('c',1,1,'r3',{'z'}));s=self.sensor(1);p=compile_strategy(s,ts,7);self.assertEqual(p.status,'HOLD_NOT_DYNAMICALLY_CONTROLLABLE');self.assertLessEqual(resource_only_branch_finish(s,ts,0),7)
 def test_disjoint_support_parallel(self):
  ts=(self.task('a',0,4,'r1',{'x'}),self.task('b',0,5,'r2',{'y'}));p=compile_strategy(self.sensor(1),ts+(self.task('c',1,1,'r3',{'z'}),),6);self.assertEqual(p.status,'READY_D0');self.assertEqual(p.branches[0].worst_finish,6)
 def test_transitive_support_serializes_component(self):
  ts=(self.task('a',0,2,'r1',{'x'}),self.task('b',0,2,'r2',{'x','y'}),self.task('c',0,2,'r3',{'y'}),self.task('d',1,1,'r4',{'z'}));p=compile_strategy(self.sensor(1),ts,6);self.assertEqual(p.status,'HOLD_NOT_DYNAMICALLY_CONTROLLABLE');self.assertEqual(p.branches[0].worst_finish,7)
 def test_stale_sensor(self):self.assertEqual(compile_strategy(self.sensor(current=False),(),1).status,'HOLD_SENSOR_CURRENTNESS')
 def test_stale_active_task(self):self.assertEqual(compile_strategy(self.sensor(),(self.task('a',0,1,'r',{'x'},False),self.task('b',1,1,'r',{'x'})),10).status,'HOLD_TASK_CURRENTNESS')
 def test_stale_inactive_task_only_blocks_its_branch(self):self.assertEqual(compile_strategy(self.sensor(),(self.task('a',0,1,'r',{'x'}),self.task('b',1,1,'r',{'x'},False)),10).status,'HOLD_TASK_CURRENTNESS')
 def test_oracle_matches(self):
  ts=(self.task('a',0,2,'r1',{'x'}),self.task('b',1,4,'r2',{'y'}));s=self.sensor(2);self.assertEqual(compile_strategy(s,ts,6).status=='READY_D0',oracle_dynamic_ready(s,ts,6))
 def test_k27_nonauthority(self):
  p=compile_strategy(self.sensor(),(self.task('a',0,1,'r',{'x'}),self.task('b',1,1,'r',{'x'})),10,k27_coordinate='K27:0');self.assertFalse(p.gate10);self.assertFalse(p.effect_authority);self.assertEqual(p.authority,D0)
 def test_branch_roots_distinct(self):
  ts=(self.task('a',0,1,'r',{'x'}),self.task('b',1,1,'r',{'y'}));p=compile_strategy(self.sensor(),ts,10);self.assertNotEqual(p.branches[0].root,p.branches[1].root)
 def test_task_declaration_order_invariant(self):
  import itertools
  ts=(self.task('a',0,2,'r',{'x'}),self.task('b',0,1,'s',{'y'}),self.task('c',1,1,'t',{'z'}));roots={compile_strategy(self.sensor(),perm,10).strategy_root for perm in itertools.permutations(ts)};self.assertEqual(len(roots),1)
 def test_invalid_condition(self):
  with self.assertRaises(ValueError):Task('x',2,Interval(1,1),'r',frozenset({'x'}))
if __name__=='__main__':unittest.main()
