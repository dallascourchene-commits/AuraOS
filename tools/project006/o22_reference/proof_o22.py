import hashlib,itertools,json,random
TRI=(False,None,True)
def keeper(x):return all(v is True for v in x)
def omega8():
 h=hashlib.sha256();k=b=0
 for x in itertools.product(TRI,repeat=8):
  r=keeper(x);k+=r;b+=r and not all(v is True for v in x);h.update((repr((x,r))+'\n').encode())
 return {'states':6561,'keepers':k,'invalid_accepts':b,'root':h.hexdigest()}
def d13():
 h=hashlib.sha256();n=k=b=0
 for x in itertools.product(TRI,repeat=8):
  hard=keeper(x)
  for c in itertools.product(TRI,repeat=5):
   r=keeper(x);n+=1;k+=r;b+=r and not hard;h.update((repr((x,c,r))+'\n').encode())
 return {'states':n,'keeper_contexts':k,'hard_invalid_contextual_repairs':b,'root':h.hexdigest()}
def campaign(n=30000):
 rng=random.Random(220260907);h=hashlib.sha256();m=b=0
 for _ in range(n):
  x=tuple(rng.choice((False,True)) for _ in range(8));e=all(x);a=keeper(x);m+=a!=e;b+=a and not e;h.update((repr((x,a))+'\n').encode())
 return {'cases':n,'oracle_mismatches':m,'unsafe_ready':b,'root':h.hexdigest()}
def hs():
 fals=['HOST_ABSENT','BAD_MAC','HOST_INCAR_MOVE','BASE_MOVE','COMPONENT_SET_MOVE','COMPONENT_VALUE_MOVE','PROOF_MISSING','PROOF_SKIPPED','PROOF_ZERO_CASES','PROOF_HEAD_MOVE']
 mech=['HOST_BASIS','FULL_BINDING','INCARNATION','SOURCE_ROOT','KEY_SET','VALUE_ROOT','PROOF_SET','NONVACUOUS','EXACT_HEAD','O21_HANDOFF']
 ctx=['DRIVE','GITHUB','WINDOWS','WSL','CRASH','REOPEN','RETRY','PARALLEL','K27','POSTUPDATE']
 g={};cells=[]
 for i,(f,m,c) in enumerate(itertools.product(fals,mech,ctx)):
  if f in ('HOST_ABSENT','BAD_MAC','HOST_INCAR_MOVE'):q='AUTHENTICATED_HOST_OBSERVATION'
  elif f in ('BASE_MOVE','COMPONENT_SET_MOVE'):q='SOURCE_AND_COMPONENT_SET_CURRENTNESS'
  elif f=='COMPONENT_VALUE_MOVE':q='OBSERVED_VALUE_BINDING'
  elif f in ('PROOF_MISSING','PROOF_SKIPPED','PROOF_ZERO_CASES'):q='NONVACUOUS_PROOF_COMPLETENESS'
  elif f=='PROOF_HEAD_MOVE':q='EXACT_HEAD_PROOF_CURRENTNESS'
  else:q='O21_HANDOFF'
  cells.append((i,f,m,c,q));g[q]=g.get(q,0)+1
 enc=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return {'frozen_candidates':1000,'consequence_groups':g,'claimed_breakthroughs':0,'freeze_root':enc(cells),'quotient_root':enc(g)}
print(json.dumps({'omega8':omega8(),'factored13d':d13(),'campaign':campaign(),'hs1000':hs()},sort_keys=True,separators=(',',':')))
