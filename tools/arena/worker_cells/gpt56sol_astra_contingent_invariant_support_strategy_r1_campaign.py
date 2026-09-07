from tools.arena.worker_cells.gpt56sol_astra_contingent_invariant_support_strategy_r1 import *
from itertools import product
import random,json,hashlib
SEED=0xA57A10;CASES=6000
AXES=('source','currentness','causal','validity','authority','owner','evidence','capability','resource','privacy','externalization','topology','coordinate');HARD=frozenset({'source','currentness','causal','validity','authority','owner','evidence','capability','externalization'});SUP=tuple('wxyz');RES=tuple('rstu')
def task(r,i):
 o=r.randrange(2);lo=r.randint(1,3);hi=lo+r.randint(0,6);supp=frozenset(r.sample(SUP,r.randint(1,2)));return Task(f't{i}',o,Interval(lo,hi),r.choice(RES),supp,r.random()>.035)
def resource_all_ready(sensor,tasks,deadline):
 if not sensor.current:return False
 for o in (0,1):
  if any(not t.current for t in tasks if t.condition==o):return False
  if resource_only_branch_finish(sensor,tasks,o)>deadline:return False
 return True
def run():
 r=random.Random(SEED);st={k:0 for k in ['cases','ready','holds','oracle_mismatches','static_false_holds','resource_false_ready','sensor_stale','task_stale','k27_attacks','bad_k27_accepts','branch0_ready','branch1_ready','avg_tasks_x1000','strategy_nodes_total']};roots=[]
 for i in range(CASES):
  sensor=Sensor('sense',Interval(r.randint(0,2),r.randint(2,5)),r.random()>.025);n=r.randint(2,7);tasks=tuple(task(r,j) for j in range(n));deadline=r.randint(4,20);k27='K27:'+str(r.randrange(27)) if r.random()<.18 else None;p=compile_strategy(sensor,tasks,deadline,k27_coordinate=k27);oracle=oracle_dynamic_ready(sensor,tasks,deadline);st['cases']+=1;st['avg_tasks_x1000']+=n*1000
  if not sensor.current:st['sensor_stale']+=1
  if any(not t.current for t in tasks):st['task_stale']+=1
  if k27:st['k27_attacks']+=1
  if p.status=='READY_D0':st['ready']+=1
  else:st['holds']+=1
  if (p.status=='READY_D0')!=oracle:st['oracle_mismatches']+=1
  if oracle and static_union_finish(sensor,tasks)>deadline:st['static_false_holds']+=1
  if resource_all_ready(sensor,tasks,deadline) and not oracle:st['resource_false_ready']+=1
  if k27 and p.status=='READY_D0' and not oracle:st['bad_k27_accepts']+=1
  if p.branches:
   st['branch0_ready']+=int(p.branches[0].worst_finish<=deadline);st['branch1_ready']+=int(p.branches[1].worst_finish<=deadline);st['strategy_nodes_total']+=1+sum(len(b.components) for b in p.branches)
  roots.append(digest({'i':i,'sensor':(sensor.duration.lo,sensor.duration.hi,sensor.current),'tasks':[(t.name,t.condition,t.duration.lo,t.duration.hi,t.resource,sorted(t.invariant_support),t.current) for t in tasks],'deadline':deadline,'status':p.status,'worst':p.worst_finish,'root':p.strategy_root,'k27':k27}))
 states=false_ready=0
 for vals in product(range(3),repeat=13):
  states+=1;s=dict(zip(AXES,vals));hard_invalid=any(s[a]==2 for a in HARD);ready=s['topology']<2 and s['resource']<2 and not hard_invalid
  if hard_invalid and s['coordinate']==0 and ready:false_ready+=1
 out={'schema':'aura.astra.o10.contingent_invariant_support_strategy.campaign.v1','seed':SEED,'stats':st,'13d_states':states,'13d_false_ready':false_ready,'case_root':hashlib.sha256(''.join(roots).encode()).hexdigest(),'keeper_laws':['StrongStaticSchedule != DynamicContingentStrategy','MutuallyExclusiveInvariantSupport != UnionSupportAtExecution','ResourceDisjoint != InvariantIndependent','HardInvariantSupport => ConditionalCouplingHyperedge','AllDurationRealizationsOnEveryObservedBranch => DynamicReady','ObservedOutcome => ActivateOnlyBranchRelevantEvidence','K27Coordinate != StrategyAuthority != TopologyTruth']};out['campaign_root']=digest(out);print(json.dumps(out,sort_keys=True,separators=(',',':')));return int(bool(st['oracle_mismatches'] or st['bad_k27_accepts'] or false_ready or st['static_false_holds']==0 or st['resource_false_ready']==0))
if __name__=='__main__':raise SystemExit(run())
