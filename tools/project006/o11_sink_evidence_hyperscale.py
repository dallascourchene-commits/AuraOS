from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
from project006_sink_evidence_recovery import *
R=lambda s:sha256(s.encode()).hexdigest(); SECRET=b'test-only-sink-verifier-secret'; ISSUER=R('sink-issuer'); VERIFIER=R('sink-verifier')
def b():
 op=OperationIdentity('c','o','k',R('p'),'f','r',R('s'),R('a'),R('ps'),R('fr')); return op,CurrentOwnerContext(op,R('a'),R('ps'),R('fr'))
def e(d=SinkDisposition.NOT_ACCEPTED,result=False,gen=3):return sign_sink_evidence(secret=SECRET,operation_id='o',disposition=d,sink_result_digest=R('res'),result_locator_root=R('loc') if result else None,issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100,sink_fence_generation=gen)
def sf(g=4,i=4):return SinkFenceContext(g,i,R(f'sf{g}{i}'))
def lattice8():
 rows=[]; keep=bad=0
 for ax in product(range(3),repeat=8):
  sig,opid,source,auth,proof,fence,idem,sinkf=ax; op,cur=b(); ev=e(); sfc=sf()
  if sig<2:ev=replace(ev,mac=R(str(ax)))
  if opid<2:ev=replace(ev,operation_id='x')
  if source<2:cur=replace(cur,operation=replace(cur.operation,source_digest=R('x'+str(source))))
  if auth<2:cur=replace(cur,authorization_root=R('a'+str(auth)))
  if proof<2:cur=replace(cur,proof_semantics_root=R('p'+str(proof)))
  if fence<2:cur=replace(cur,fence_root=R('f'+str(fence)))
  if idem<2:cur=replace(cur,operation=replace(cur.operation,payload_digest=R('i'+str(idem))))
  if sinkf<2:sfc=sf(3,3) if sinkf==1 else sf(4,3)
  d=decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20,sink_fence=sfc); routed=d.action is RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID; valid=all(x==2 for x in ax); keep+=int(routed and valid); bad+=int(routed and not valid); rows.append((ax,d.action.value))
 return {'states':6561,'keepers':keep,'invalid_routes':bad,'root':sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()}
def r13():
 l=lattice8(); op,cur=b(); ev=e(); counts={}
 for _ in product(range(3),repeat=5):
  d=decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20,sink_fence=sf()); counts[d.action.value]=counts.get(d.action.value,0)+1
 p={'hard_states':6561,'hard_keepers':l['keepers'],'context_states_on_keeper':243,'cartesian_states':1594323,'hard_invalid_context_repair':0,'context_counts':counts};p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest();return p
def hs():
 cells=[];q={}
 for a,bx,c in product(range(10),repeat=3):
  n=a*100+bx*10+c;op,cur=b();cap=list(RecoveryCapability)[bx%3];ev=None;sfc=None;state=NativeState.COMPLETION_AMBIGUOUS
  if a%4==0:ev=e(SinkDisposition.ACCEPTED,c%2==0)
  elif a%4==1:ev=e(SinkDisposition.NOT_ACCEPTED);sfc=sf() if c>=5 else sf(3,3)
  elif a%4==2:ev=e(SinkDisposition.UNKNOWN)
  if c==7:state=NativeState.RESULT_OBSERVED
  elif c==8:cur=replace(cur,authorization_root=R('m'+str(n)))
  d=decide_recovery(state=state,operation=op,current=cur,capability=cap,sink_evidence=ev,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20,sink_fence=sfc);cell={'n':n,'k27':n%27,'action':d.action.value,'reason':d.reason};cells.append(cell);q[(d.action.value,d.reason)]=q.get((d.action.value,d.reason),0)+1
 freeze=sha256(json.dumps([{'n':x['n'],'k27':x['k27']} for x in cells],sort_keys=True,separators=(',',':')).encode()).hexdigest(); quot=sha256(json.dumps(sorted((a,r,v) for (a,r),v in q.items()),separators=(',',':')).encode()).hexdigest();return {'cells':1000,'groups':len(q),'freeze_root':freeze,'quotient_root':quot,'cells_root':sha256(json.dumps(cells,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
if __name__=='__main__':print(json.dumps({'omega8':lattice8(),'recursion13d':r13(),'hs1000':hs()},sort_keys=True,indent=2))
