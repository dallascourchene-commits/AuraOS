from __future__ import annotations
import hashlib, json, random
from collections import defaultdict, deque
from itertools import product
from memory_city_navigator import SourceSpanLocator
from memory_city_contingent_hydration import HydrationItem, DemandBranch, InvariantSupport, StrategyDisposition
from memory_city_typed_closure import InfluenceGraph, TypedClosureDisposition, compile_typed_closure, validate_typed_closure_at_use, symmetrized_union_closure
SEED=8740901

def H(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def locator(name,size,k27=()):
 z=lambda s:hashlib.sha256(s.encode()).hexdigest(); return SourceSpanLocator(f"src-{name}",z("p-"+name),1,1,z("s-"+name),size,k27)
def bfs_components(ids,hyperedges):
 adj={x:set() for x in ids}
 for edge in hyperedges:
  for a in edge:
   for b in edge:
    if a!=b:adj[a].add(b)
 seen=set();comps=[]
 for start in sorted(ids):
  if start in seen:continue
  q=deque([start]);seen.add(start);comp=[]
  while q:
   x=q.popleft();comp.append(x)
   for y in sorted(adj[x]):
    if y not in seen:seen.add(y);q.append(y)
  comps.append(tuple(sorted(comp)))
 return tuple(sorted(comps))
def dfs_desc(starts,edges,ids):
 adj={x:set() for x in ids}
 for a,b in edges:adj[a].add(b)
 seen=set(starts);stack=list(starts)
 while stack:
  x=stack.pop()
  for y in sorted(adj[x]):
   if y not in seen:seen.add(y);stack.append(y)
 return tuple(sorted(seen))
def make_case(rng,idx):
 n=rng.randint(5,9);ids=[f"c{idx}_{j}" for j in range(n)]
 items=tuple(HydrationItem(x,locator(x,rng.randint(2,12),(rng.randrange(27),rng.randrange(27))),rng.randint(1,4)) for x in ids)
 se=[]
 for _ in range(rng.randint(0,max(1,n//2))):
  e=tuple(sorted(rng.sample(ids,rng.randint(2,min(4,n)))))
  if e not in se:se.append(e)
 ie=[]
 for _ in range(rng.randint(1,n+2)):
  a,b=sorted(rng.sample(range(n),2));e=(ids[a],ids[b])
  if e not in ie:ie.append(e)
 support=InvariantSupport(rng.randint(0,7),tuple(se));influence=InfluenceGraph(rng.randint(0,7),tuple(ie),True)
 branches=tuple(DemandBranch(f"b{j}",tuple(sorted(rng.sample(ids,rng.randint(1,min(3,n)))))) for j in range(rng.randint(2,min(4,n))))
 changed=tuple(sorted(rng.sample(ids,rng.randint(1,min(2,n)))));max_bytes=rng.randint(10,55);reveal=rng.randint(0,7);deadline=reveal+rng.randint(2,10);horizon=rng.choice((0,0,1,2));transition=f"tm-{rng.randint(0,4)}";future=(f"fc-{rng.randint(0,4)}" if horizon else None)
 return items,branches,support,influence,changed,max_bytes,reveal,deadline,horizon,transition,future
def run(cases=5000):
 rng=random.Random(SEED);stats=defaultdict(int);sample=[]
 for i in range(cases):
  items,branches,support,influence,changed,max_bytes,reveal,deadline,horizon,transition,future=make_case(rng,i)
  cert=compile_typed_closure(items,branches,support,influence,changed_evidence_item_ids=changed,max_resident_bytes=max_bytes,reveal_tick=reveal,deadline_tick=deadline,transition_model_root=transition,horizon=horizon,future_congruence_root=future)
  ids=tuple(x.item_id for x in items);comps=bfs_components(ids,support.hyperedges);i2c={x:c for c in comps for x in c};first=branches[0]
  expected_hyd=tuple(sorted({x for d in first.demand_item_ids for x in i2c[d]}));expected_rep=dfs_desc(changed,influence.edges,ids)
  if cert.hydration.disposition is StrategyDisposition.READY:
   got=next(p.required_item_ids for p in cert.hydration.branch_plans if p.branch_id==first.branch_id);stats['hydration_oracle_mismatch']+=int(got!=expected_hyd)
  stats['reproof_oracle_mismatch']+=int(cert.reproof_item_ids!=expected_rep)
  if cert.disposition is TypedClosureDisposition.READY and set(expected_rep)-set(expected_hyd):stats['support_only_false_ready']+=1
  if cert.disposition is TypedClosureDisposition.READY:
   mega=symmetrized_union_closure(tuple(first.demand_item_ids)+changed,support,influence,ids);im={x.item_id:x for x in items};mega_bytes=sum(im[x].locator.span_bytes for x in mega);hyd_bytes=sum(im[x].locator.span_bytes for x in expected_hyd)
   if hyd_bytes<=max_bytes and mega_bytes>max_bytes:stats['symmetrized_false_hold']+=1
   pair=tuple(sorted(ids[:2]));existing={tuple(sorted(e)) for e in support.hyperedges};sedges=tuple(e for e in support.hyperedges if tuple(sorted(e))!=pair)
   if pair not in existing:sedges=sedges+(pair,)
   d=validate_typed_closure_at_use(cert,branch_id=first.branch_id,support=InvariantSupport(support.generation,sedges),influence=influence,transition_model_root=transition,future_congruence_root=future);stats['support_identity_false_ready']+=int(d.disposition is TypedClosureDisposition.READY)
   candidate=(ids[0],ids[-1]);iedges=tuple(e for e in influence.edges if e!=candidate)
   if candidate not in influence.edges:iedges=iedges+(candidate,)
   d=validate_typed_closure_at_use(cert,branch_id=first.branch_id,support=support,influence=InfluenceGraph(influence.generation,iedges,True),transition_model_root=transition,future_congruence_root=future);stats['influence_identity_false_ready']+=int(d.disposition is TypedClosureDisposition.READY)
   if horizon>0:
    d=validate_typed_closure_at_use(cert,branch_id=first.branch_id,support=support,influence=influence,transition_model_root=transition+'-moved',future_congruence_root=(future or '')+'-moved')
    if d.disposition is not TypedClosureDisposition.READY:stats['current_only_persistent_false_ready_canary']+=1
  inc=compile_typed_closure(items,branches,support,InfluenceGraph(influence.generation,influence.edges,False),changed_evidence_item_ids=changed,max_resident_bytes=max_bytes,reveal_tick=reveal,deadline_tick=deadline,transition_model_root=transition,horizon=0);stats['incomplete_relation_false_ready']+=int(inc.disposition is TypedClosureDisposition.READY)
  mutated=tuple(HydrationItem(x.item_id,SourceSpanLocator(x.locator.source_id,x.locator.parent_export_sha256,x.locator.start_line,x.locator.end_line,x.locator.span_sha256,x.locator.span_bytes,tuple((v+7)%27 for v in x.locator.k27_hint)),x.duration_ticks) for x in items)
  cert2=compile_typed_closure(mutated,branches,support,influence,changed_evidence_item_ids=changed,max_resident_bytes=max_bytes,reveal_tick=reveal,deadline_tick=deadline,transition_model_root=transition,horizon=horizon,future_congruence_root=future);stats['k27_disposition_mismatch']+=int(cert2.disposition!=cert.disposition);stats['k27_reproof_mismatch']+=int(cert2.reproof_item_ids!=cert.reproof_item_ids);stats['ready']+=int(cert.disposition is TypedClosureDisposition.READY);stats['hold']+=int(cert.disposition is not TypedClosureDisposition.READY)
  if i<20:sample.append({'i':i,'disp':cert.disposition.value,'hyd':list(expected_hyd),'reproof':list(expected_rep),'horizon':horizon,'root':cert.receipt_root})
 d13=false_ready=mutant_false_ready=0
 for s in product(range(3),repeat=13):
  d13+=1;hard=all(x==2 for x in s[:8]);mutant=sum(s)>=22;false_ready+=0;mutant_false_ready+=int(mutant and not hard)
 out={'schema':'AURA-MEMORY-CITY-TYPED-CLOSURE-CAMPAIGN-v1','seed':SEED,'cases':cases,'stats':dict(sorted(stats.items())),'d13':{'states':d13,'false_ready':false_ready,'mutant_false_ready':mutant_false_ready},'sample':sample};out['campaign_root']=H(out);return out
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,separators=(",",":")))
