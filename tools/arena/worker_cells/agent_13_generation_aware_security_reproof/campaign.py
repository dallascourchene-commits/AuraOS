import itertools,json,os,random,sys,time
from dataclasses import replace
from hashlib import sha256
HERE=os.path.dirname(__file__);sys.path.insert(0,HERE)
from generation_aware_security_reproof import *
def roots(v=1):return tuple((k,digest({'k':k,'v':v})) for k in SEMANTIC_FIELDS)
def surface(gen='1'*40,**kw):
 d=dict(generation=gen,schema_root=digest({'schema':1}),admission_surface_root=digest({'surface':1}),verifier_generation='2'*40,semantic_roots=roots(),provider_attested=True,current=True,complete=True);d.update(kw);return GenerationSurface(**d)
def oracle_changed(old,current):
 o=old.roots();c=current.roots();return tuple(sorted(k for k in SEMANTIC_FIELDS if o[k]!=c[k]))
def randomized(n=100000,seed=1313):
 rng=random.Random(seed);base=surface();mismatch=false_reuse=0;fra=0;changed_cases=0
 for i in range(n):
  cur=surface('3'*40);rr=dict(cur.roots());mode=rng.randrange(6)
  if mode==0: pass
  elif mode==1: rr[rng.choice(SEMANTIC_FIELDS)]=digest({'i':i})
  elif mode==2:
   for k in rng.sample(SEMANTIC_FIELDS,2):rr[k]=digest({'i':i,'k':k})
  elif mode==3: cur=replace(cur,provider_attested=False)
  elif mode==4: cur=replace(cur,admission_surface_root=digest({'i':i}))
  else: cur=replace(cur,current=False)
  cur=replace(cur,semantic_roots=tuple(rr.items()));r=classify(base,cur)
  changed=oracle_changed(base,cur)
  if changed and r.decision==Decision.REUSE_EXACT:false_reuse+=1
  if r.decision==Decision.REPROVE_CONE:
   want=descendants(DIM_TO_NODE[k] for k in changed);mismatch+=int(set(r.recompute_order)!=want);fra+=len(want)/len(DEPS);changed_cases+=1
 return {'cases':n,'closure_mismatches':mismatch,'false_reuses':false_reuse,'mean_changed_cone_fraction':fra/max(1,changed_cases)}
def hs1000():
 base=surface();false=0
 for i in range(1000):
  cur=surface('3'*40);rr=dict(cur.roots());mode=i%5
  if mode==0:cur=replace(cur,provider_attested=False)
  elif mode==1:cur=replace(cur,current=False)
  elif mode==2:cur=replace(cur,admission_surface_root=digest({'x':i}))
  elif mode==3:rr['model_root']=digest({'x':i})
  else:rr['trace_root']=digest({'x':i})
  r=classify(base,replace(cur,semantic_roots=tuple(rr.items())))
  if mode<3 and r.decision!=Decision.HOLD_UNKNOWN:false+=1
  if mode>=3 and r.decision!=Decision.REPROVE_CONE:false+=1
 return {'cases':1000,'false_decisions':false}
def omega():
 keep=sum(crystalline_admission(s) for s in itertools.product(range(3),repeat=8));return {'states':3**8,'keepers':keep}
def d13(n=100000):
 rng=random.Random(13);seen=set();repair=0
 while len(seen)<n:
  s=tuple(rng.randrange(3) for _ in range(13))
  if s in seen:continue
  seen.add(s);repair+=int(any(x!=2 for x in s[:8]) and admission_13d(s))
 return {'unique':n,'hard_invalid_repairs':repair}
def main():
 sem={'schema':SCHEMA+'-CAMPAIGN','parents':[GEN_COMPAT_PARENT,EFFICIENCY_REPLAY_PARENT],'security_graph_parent':SECURITY_GRAPH_PARENT,'randomized':randomized(),'hs1000':hs1000(),'omega8':omega(),'13d':d13()}
 root=sha256(json.dumps(sem,sort_keys=True,separators=(',',':')).encode()).hexdigest();print(json.dumps({'semantic':sem,'campaign_root':root},sort_keys=True));assert sem['randomized']['closure_mismatches']==0 and sem['randomized']['false_reuses']==0 and sem['hs1000']['false_decisions']==0 and sem['omega8']['keepers']==1 and sem['13d']['hard_invalid_repairs']==0
if __name__=='__main__':main()
