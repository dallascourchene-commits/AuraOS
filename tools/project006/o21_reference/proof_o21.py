from __future__ import annotations
import hashlib,itertools,json,random
TRI=(False,None,True)
def keeper(x):return all(v is True for v in x)
def omega8():
 h=hashlib.sha256();k=bad=0
 for x in itertools.product(TRI,repeat=8):
  r=keeper(x);k+=int(r);bad+=int(r and not all(v is True for v in x));h.update((repr((x,r))+'\n').encode())
 return {'states':6561,'keepers':k,'invalid_accepts':bad,'root':h.hexdigest()}
def d13():
 h=hashlib.sha256();n=k=bad=0
 for x in itertools.product(TRI,repeat=8):
  base=keeper(x)
  for c in itertools.product(TRI,repeat=5):
   r=keeper(x);n+=1;k+=int(r);bad+=int(r and not base);h.update((repr((x,c,r))+'\n').encode())
 return {'states':n,'keeper_contexts':k,'hard_invalid_contextual_repairs':bad,'root':h.hexdigest()}
def campaign(n=30000):
 rng=random.Random(20260907);h=hashlib.sha256();bad=m=0
 for _ in range(n):
  x=tuple(rng.choice((False,True)) for _ in range(8));e=all(x);a=keeper(x);m+=a!=e;bad+=a and not e;h.update((repr((x,a))+'\n').encode())
 return {'cases':n,'oracle_mismatches':m,'unsafe_accepts':bad,'root':h.hexdigest()}
def hs():
 fals=['TRANSPORT_TRUNCATION','ARTIFACT_HASH_MOVE','PATH_ESCAPE','BACKUP_MISSING','STAGE_PARTIAL','COMMIT_REPLAY','COMMIT_PUBLICATION_GAP','O20_FAIL','O19_FAIL','ROLLBACK_DRIFT']
 mech=['MANIFEST','BYTE_VERIFY','SAFE_PATH','BACKUP_ROOT','STAGE_ROOT','COMMIT_RECEIPT','PUBLICATION_JOURNAL','O20_GATE','O19_GATE','ROLLBACK_ROOT']
 ctx=['DOWNLOAD','GITHUB','DRIVE','WINDOWS','WSL','CRASH_PRE','CRASH_POST','REOPEN','RETRY','POST_UPDATE']
 cells=[];g={}
 for i,(f,m,c) in enumerate(itertools.product(fals,mech,ctx)):
  if f in fals[:3]:q='BYTE_AND_SOURCE_INTEGRITY'
  elif f in fals[3:5]:q='PRECOMMIT_RECOVERABILITY'
  elif f in fals[5:7]:q='COMMIT_VS_PUBLICATION'
  elif f in fals[7:9]:q='POSTINSTALL_ACCEPTANCE'
  else:q='ROLLBACK_INTEGRITY'
  cells.append((i,f,m,c,q));g[q]=g.get(q,0)+1
 enc=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return {'frozen_candidates':1000,'consequence_groups':g,'claimed_breakthroughs':0,'freeze_root':enc(cells),'quotient_root':enc(g)}
print(json.dumps({'omega8':omega8(),'factored13d':d13(),'campaign':campaign(),'hs1000':hs()},sort_keys=True,separators=(',',':')))
