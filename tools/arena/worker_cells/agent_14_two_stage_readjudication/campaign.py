import itertools,json,os,random,sys
from dataclasses import replace
from hashlib import sha256
HERE=os.path.dirname(__file__);sys.path.insert(0,HERE)
from two_stage_readjudication import *
def R(x):return dig(x)
def local():return LocalSurface('1'*40,'1'*40,R('p'),R('p'),R('d'),R('d'),R('g'),R('g'),R('a'),R('a'),R('r'),R('r'))
def subjects():return [AuthSubject(s,'2'*40,ProviderState.ATTESTED,R(s)) for s in SUBJECTS]
def randomized(n=50000,seed=1414):
 rng=random.Random(seed);false=0;counts={d.value:0 for d in Decision}
 for i in range(n):
  l=local();xs=subjects();mode=rng.randrange(8)
  if mode==0:l=replace(l,current_projection_root=R(('p',i)))
  elif mode==1:l=replace(l,current_domain_root=R(('d',i)))
  elif mode==2:l=replace(l,current_generation='3'*40)
  elif mode==3:l=replace(l,current_graph_root=R(('g',i)))
  elif mode==4:
   j=rng.randrange(4);xs[j]=AuthSubject(xs[j].subject,xs[j].generation,ProviderState.OBSERVED,None)
  elif mode==5:
   j=rng.randrange(4);xs[j]=AuthSubject(xs[j].subject,xs[j].generation,ProviderState.EXPIRED,None)
  elif mode==6:l=replace(l,gate10=True)
  r=adjudicate(l,xs);counts[r.decision.value]+=1
  if mode in (0,1,2,3,6) and r.decision!=Decision.REPROVE_LOCAL_FIRST:false+=1
  if mode in (4,5) and r.decision!=Decision.HOLD_AUTHENTICATION_CUTSET:false+=1
  if mode==7 and r.decision!=Decision.ELIGIBLE_FOR_FRESH_READJUDICATION:false+=1
 return {'cases':n,'false_decisions':false,'counts':counts}
def oracle_bundles():
 mis=0
 for mask in range(16):
  missing={SUBJECTS[i] for i in range(4) if mask>>i&1};got=minimum_bundles(missing)
  if not missing:
   mis+=int(got!=());continue
  cover=set().union(*(BUNDLES[x] for x in got));mis+=int(not missing<=cover)
  for r in range(1,len(got)):
   if any(missing<=set().union(*(BUNDLES[x] for x in c)) for c in itertools.combinations(BUNDLES,r)):mis+=1;break
 return {'sets':16,'mismatches':mis}
def hs1000():
 false=0
 for i in range(1000):
  l=local();xs=subjects();m=i%4
  if m==0:l=replace(l,current_admission_root=R(i))
  elif m==1:l=replace(l,effect_authority=True)
  else:
   j=i%4;xs[j]=AuthSubject(xs[j].subject,xs[j].generation,ProviderState.CONTESTED if m==2 else ProviderState.INDETERMINATE,None)
  r=adjudicate(l,xs)
  if m<2 and r.decision!=Decision.REPROVE_LOCAL_FIRST:false+=1
  if m>=2 and r.decision!=Decision.HOLD_AUTHENTICATION_CUTSET:false+=1
 return {'cases':1000,'false_decisions':false}
def d13(n=100000):
 rng=random.Random(14);seen=set();repair=0
 while len(seen)<n:
  s=tuple(rng.randrange(3) for _ in range(13))
  if s in seen:continue
  seen.add(s);repair+=int(any(x!=2 for x in s[:8]) and admission13(s))
 return {'unique':n,'hard_invalid_repairs':repair}
def main():
 sem={'schema':SCHEMA+'-CAMPAIGN','parents':[SEMANTIC_DOMAIN_PARENT,AUTH_CUTSET_PARENT],'randomized':randomized(),'bundle_oracle':oracle_bundles(),'hs1000':hs1000(),'omega8':{'states':3**8,'keepers':sum(crystalline(s) for s in itertools.product(range(3),repeat=8))},'13d':d13()};root=sha256(json.dumps(sem,sort_keys=True,separators=(',',':')).encode()).hexdigest();print(json.dumps({'semantic':sem,'campaign_root':root},sort_keys=True));assert sem['randomized']['false_decisions']==0 and sem['bundle_oracle']['mismatches']==0 and sem['hs1000']['false_decisions']==0 and sem['omega8']['keepers']==1 and sem['13d']['hard_invalid_repairs']==0
if __name__=='__main__':main()
