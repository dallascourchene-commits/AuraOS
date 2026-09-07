from dataclasses import replace
from hashlib import sha256
import hmac,json,random
from project006_sink_evidence_recovery import *
R=lambda s:sha256(s.encode()).hexdigest(); SECRET=b'test-only-sink-verifier-secret'; ISSUER=R('sink-issuer'); VERIFIER=R('sink-verifier')
def base(i):
 op=OperationIdentity(f'c{i}',f'o{i}',f'k{i}',R(f'p{i}'),f'f{i}',f'r{i%5}',R(f's{i}'),R(f'a{i}'),R(f'ps{i%3}'),R(f'fr{i%7}')); return op,CurrentOwnerContext(op,op.authorization_root,op.proof_semantics_root,op.fence_root)
def evidence(op,disp,result,gen=3,valid=True):
 e=sign_sink_evidence(secret=SECRET,operation_id=op.operation_id,disposition=disp,sink_result_digest=R('result'+op.operation_id),result_locator_root=R('loc'+op.operation_id) if result else None,issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100,sink_fence_generation=gen)
 return e if valid else replace(e,mac=R('bad'+op.operation_id))
def sf(gen=4,installed=4): return SinkFenceContext(gen,installed,R(f'sf{gen}-{installed}'))
def oracle(state,op,cur,cap,e,f,now):
 if state is NativeState.RETURN_WRITTEN:return RecoveryAction.DONE
 if state in (NativeState.RESULT_OBSERVED,NativeState.ERROR_TERMINAL):return RecoveryAction.RETRY_RETURN_WRITER_ONLY
 same=(cur.operation==op and cur.authorization_root==op.authorization_root and cur.proof_semantics_root==op.proof_semantics_root and cur.fence_root==op.fence_root)
 if state is NativeState.ACK_WRITTEN_PRE_EFFECT:return RecoveryAction.START_PROVIDER_ONCE if same else RecoveryAction.HOLD_CURRENTNESS_MOVED
 if state is not NativeState.COMPLETION_AMBIGUOUS:return RecoveryAction.HOLD_UNSUPPORTED_STATE
 if e is not None:
  x=hmac.new(SECRET,json.dumps(e.unsigned_payload(),sort_keys=True,separators=(',',':')).encode(),sha256).hexdigest(); valid=e.operation_id==op.operation_id and e.issuer_root==ISSUER and e.verifier_root==VERIFIER and now<=e.expires_at and hmac.compare_digest(x,e.mac)
  if not valid:return RecoveryAction.HOLD_INVALID_SINK_EVIDENCE
  if e.disposition is SinkDisposition.ACCEPTED:return RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY if e.result_locator_root else RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY
  if e.disposition is SinkDisposition.UNKNOWN:return RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY
  if not same:return RecoveryAction.HOLD_CURRENTNESS_MOVED
  fenced=f is not None and f.generation==f.installed_generation and f.installed_generation>e.sink_fence_generation
  if not fenced:return RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY
  return RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID if cap is RecoveryCapability.IDEMPOTENT_RETRY else RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY
 if not same:return RecoveryAction.HOLD_CURRENTNESS_MOVED
 if cap is RecoveryCapability.IDEMPOTENT_RETRY:return RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID
 if cap is RecoveryCapability.QUERY_RECONCILE:return RecoveryAction.QUERY_RECONCILE
 return RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY
def run(cases=24000):
 rng=random.Random(20260907); c={'cases':cases,'oracle_mismatches':0,'accepted_without_result_replays':0,'notaccepted_without_new_fence_replays':0,'authority_minted':0,'unsafe_naive_replays':0}; actions={}
 for i in range(cases):
  op,cur=base(i); state=rng.choice(list(NativeState)); cap=rng.choice(list(RecoveryCapability)); e=None; f=None; mode=rng.randrange(16)
  if mode==0:e=evidence(op,SinkDisposition.ACCEPTED,True)
  elif mode==1:e=evidence(op,SinkDisposition.ACCEPTED,False)
  elif mode in (2,3,4):e=evidence(op,SinkDisposition.NOT_ACCEPTED,False); f=[None,sf(3,3),sf(4,4)][mode-2]
  elif mode==5:e=evidence(op,SinkDisposition.UNKNOWN,False)
  elif mode==6:e=evidence(op,SinkDisposition.ACCEPTED,True,valid=False)
  elif mode==7:e=replace(evidence(op,SinkDisposition.NOT_ACCEPTED,False),operation_id='wrong')
  if mode==8:cur=replace(cur,authorization_root=R('m'+str(i)))
  elif mode==9:cur=replace(cur,proof_semantics_root=R('mps'+str(i)))
  elif mode==10:cur=replace(cur,fence_root=R('mf'+str(i)))
  elif mode==11:cur=replace(cur,operation=replace(cur.operation,payload_digest=R('mp'+str(i))))
  d=decide_recovery(state=state,operation=op,current=cur,capability=cap,sink_evidence=e,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=50,sink_fence=f); o=oracle(state,op,cur,cap,e,f,50)
  c['oracle_mismatches']+=int(d.action is not o); c['authority_minted']+=int(d.authority_minted or d.effect_authority or d.gate10); actions[d.action.value]=actions.get(d.action.value,0)+1
  if state is NativeState.COMPLETION_AMBIGUOUS and e is not None and e.disposition is SinkDisposition.ACCEPTED and not e.result_locator_root:c['accepted_without_result_replays']+=int(d.action in (RecoveryAction.START_PROVIDER_ONCE,RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID))
  if state is NativeState.COMPLETION_AMBIGUOUS and e is not None and e.disposition is SinkDisposition.NOT_ACCEPTED and not (f and f.generation==f.installed_generation and f.installed_generation>e.sink_fence_generation):c['notaccepted_without_new_fence_replays']+=int(d.action is RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID)
  if state is NativeState.COMPLETION_AMBIGUOUS and o is not RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID:c['unsafe_naive_replays']+=1
 c['actions']=dict(sorted(actions.items())); raw=json.dumps(c,sort_keys=True,separators=(',',':')).encode(); c['campaign_root']=sha256(raw).hexdigest()
 if any(c[k] for k in ('oracle_mismatches','accepted_without_result_replays','notaccepted_without_new_fence_replays','authority_minted')): raise AssertionError(c)
 return c
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
