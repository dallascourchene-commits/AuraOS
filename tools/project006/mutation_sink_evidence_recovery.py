from dataclasses import replace
from hashlib import sha256
from project006_sink_evidence_recovery import *
R=lambda s:sha256(s.encode()).hexdigest();S=b'test-only-sink-verifier-secret';I=R('sink-issuer');V=R('sink-verifier')
op=OperationIdentity('c','o','k',R('p'),'f','r',R('s'),R('a'),R('ps'),R('fr'));cur=CurrentOwnerContext(op,R('a'),R('ps'),R('fr'))
def e(d,result=False):return sign_sink_evidence(secret=S,operation_id='o',disposition=d,sink_result_digest=R('res'),result_locator_root=R('loc') if result else None,issuer_root=I,verifier_root=V,observed_at=10,expires_at=100,sink_fence_generation=3)
def f(g=4,i=4):return SinkFenceContext(g,i,R(f'sf{g}{i}'))
def d(ev,fc=None,current=cur):return decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=current,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=ev,secret=S,expected_issuer_root=I,expected_verifier_root=V,now=20,sink_fence=fc)
def run():
 k={};k['accepted_without_result_replay']=d(e(SinkDisposition.ACCEPTED,False)).reason=='ACCEPTED_RESULT_UNAVAILABLE';k['notaccepted_without_fence_replay']=d(e(SinkDisposition.NOT_ACCEPTED)).reason=='OLD_INFLIGHT_REQUEST_NOT_FENCED';k['equal_fence_replay']=d(e(SinkDisposition.NOT_ACCEPTED),f(3,3)).reason=='OLD_INFLIGHT_REQUEST_NOT_FENCED';k['uninstalled_fence_replay']=d(e(SinkDisposition.NOT_ACCEPTED),f(4,3)).reason=='OLD_INFLIGHT_REQUEST_NOT_FENCED';k['unknown_requery_loop']=d(e(SinkDisposition.UNKNOWN),f()).reason=='SINK_STATUS_UNKNOWN';k['forged_accepted']=d(replace(e(SinkDisposition.ACCEPTED,True),mac=R('bad'))).action is RecoveryAction.HOLD_INVALID_SINK_EVIDENCE;return {'mutants':len(k),'killed':sum(k.values()),'details':k}
if __name__=='__main__':import json;print(json.dumps(run(),sort_keys=True,indent=2))
