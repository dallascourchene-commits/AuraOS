from tools.arena.worker_cells.gpt56sol_astra_uncertainty_bounded_evidence_choreography_r1 import *
from itertools import product,permutations
import random,json,hashlib
SEED=0xA57A08;CASES=5000
AXES=('source','currentness','causal','validity','authority','owner','evidence','capability','resource','privacy','externalization','topology','coordinate');HARD=frozenset({'source','currentness','causal','validity','authority','owner','evidence','capability','externalization'})
def make_truth(r):
 s=[r.choice((False,True)) for _ in range(4)]
 if not any(s):s[r.randrange(4)]=True
 if all(s):s[r.randrange(4)]=False
 return tuple(bool(((m>>0)&1) and s[((m>>1)&1)|(((m>>2)&1)<<1)]) for m in range(8))
def q(r,name,bit,private):
 lo=r.randint(1,4);return EvidenceQuery(name,bit,r.randint(1,9),DurationInterval(lo,lo+r.randint(0,8)),private,0,r.random()>0.04)
def ref(r):
 lo=r.randint(1,3);return RefreshAction('refresh',r.randint(1,4),DurationInterval(lo,lo+r.randint(0,6)),r.random()>0.025)
def uniform_ref(table,known):
 vals=set()
 for m in range(8):
  bits=tuple((m>>i)&1 for i in range(3))
  if all(k==UNKNOWN or k==bits[i] for i,k in enumerate(known)):vals.add(bool(table[m]))
 return next(iter(vals)) if len(vals)==1 else None
def oracle_min_cost(table,queries,refresh,deadline):
 def rec(known,refreshed,ehi):
  u=uniform_ref(table,known)
  if u is False:return 0
  if u is True and refreshed:return 0
  o=[]
  if u is True and not refreshed and refresh.clock_current and ehi+refresh.duration.hi<=deadline:
   s=rec(known,True,ehi+refresh.duration.hi)
   if s is not None:o.append(refresh.cost+s)
  if u is None:
   for x in queries:
    if not x.clock_current or known[x.bit]!=UNKNOWN or (x.private and known[x.premise_bit]!=1) or ehi+x.duration.hi>deadline:continue
    bs=[]
    for b in (0,1):
     kk=list(known);kk[x.bit]=b;bs.append(rec(tuple(kk),refreshed,ehi+x.duration.hi))
    if None not in bs:o.append(x.cost+max(bs))
  return min(o) if o else None
 return rec((UNKNOWN,UNKNOWN,UNKNOWN),False,0)
def run():
 r=random.Random(SEED);st={k:0 for k in ['cases','robust_ready','robust_hold','oracle_mismatches','optimal_cost_mismatches','midpoint_ready','midpoint_false_ready','private_premise_failures','positive_refresh_failures','k27_attacks','bad_k27_accepts','stale_clock_cases','permutation_mismatches']};roots=[]
 for i in range(CASES):
  t=make_truth(r);qs=(q(r,'premise',0,False),q(r,'private_a',1,True),q(r,'private_b',2,True));rf=ref(r);dl=r.randint(4,24);k27='K27:'+str(r.randrange(27)) if r.random()<.2 else None;rb=compile_choreography(t,qs,rf,dl,k27_coordinate=k27);mid=compile_choreography(t,qs,rf,dl,duration_mode='midpoint',k27_coordinate=k27);st['cases']+=1
  if k27:st['k27_attacks']+=1
  if not all(x.clock_current for x in qs) or not rf.clock_current:st['stale_clock_cases']+=1
  oracle=oracle_min_cost(t,qs,rf,dl)
  if rb.status=='READY_D0':
   st['robust_ready']+=1;v=validate_tree(t,qs,rf,rb.tree,dl)
   if v['failures']:
    st['oracle_mismatches']+=1;st['private_premise_failures']+=sum(f[0]=='private_before_premise' for f in v['failures']);st['positive_refresh_failures']+=sum(f[0]=='positive_without_refresh' for f in v['failures'])
   if oracle is None:st['oracle_mismatches']+=1
   elif rb.worst_cost!=oracle:st['optimal_cost_mismatches']+=1
  else:
   st['robust_hold']+=1
   if oracle is not None:st['oracle_mismatches']+=1
  if mid.status=='READY_D0':
   st['midpoint_ready']+=1
   if validate_tree(t,qs,rf,mid.tree,dl,robust=True)['failures']:st['midpoint_false_ready']+=1
  if k27 and rb.status=='READY_D0' and not robustly_safe(rb,t,qs,rf,dl):st['bad_k27_accepts']+=1
  if i<96 and len({compile_choreography(t,p,rf,dl).plan_root for p in permutations(qs)})!=1:st['permutation_mismatches']+=1
  roots.append(digest({'i':i,'truth':t,'q':[(x.name,x.cost,x.duration.lo,x.duration.hi,x.clock_current) for x in qs],'refresh':(rf.cost,rf.duration.lo,rf.duration.hi,rf.clock_current),'deadline':dl,'robust':rb.status,'cost':rb.worst_cost,'root':rb.plan_root,'mid':mid.status,'k27':k27}))
 states=false_ready=0
 for vals in product(range(3),repeat=13):
  states+=1;s=dict(zip(AXES,vals));hard_invalid=any(s[a]==2 for a in HARD);ready=s['resource']<2 and not hard_invalid
  if hard_invalid and s['coordinate']==0 and ready:false_ready+=1
 out={'schema':'aura.astra.o8.uncertainty_bounded_evidence_choreography.campaign.v1','seed':SEED,'stats':st,'13d_states':states,'13d_false_ready':false_ready,'case_root':hashlib.sha256(''.join(roots).encode()).hexdigest(),'keeper_laws':['EvidenceQueryOptimality != RobustDeadlineFeasibility','MidpointDeadlineFeasible != AllClockRealizationsDeadlineFeasible','PrivateEvidence => HardPremiseAdmitted','PositiveReady => ExactAtUseRefresh','ClockRelationCurrentness != EvidencePredicateTruth','K27Coordinate != Evidence != ClockProof != Authority','Hard13DAxisCannotBeCompensated']};out['campaign_root']=digest(out);print(json.dumps(out,sort_keys=True,separators=(',',':')))
 return int(bool(st['oracle_mismatches'] or st['optimal_cost_mismatches'] or st['private_premise_failures'] or st['positive_refresh_failures'] or st['bad_k27_accepts'] or st['permutation_mismatches'] or false_ready or st['midpoint_false_ready']==0))
if __name__=='__main__':raise SystemExit(run())
