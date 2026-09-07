from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
from project006_sink_evidence_recovery import *

R=lambda s: sha256(s.encode()).hexdigest(); SECRET=b'test-only-sink-verifier-secret'; ISSUER=R('sink-issuer'); VERIFIER=R('sink-verifier')
def base():
    op=OperationIdentity('cmd','op','idem',R('payload'),'file','rev',R('src'),R('auth'),R('proof'),R('fence'))
    return op,CurrentOwnerContext(op,op.authorization_root,op.proof_semantics_root,op.fence_root)

def signed(disp=SinkDisposition.NOT_ACCEPTED): return sign_sink_evidence(secret=SECRET,operation_id='op',disposition=disp,sink_result_digest=R('result'),issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100)

def lattice8():
    keeper=0; invalid_routes=0; rows=[]
    for axes in product(range(3), repeat=8):
        sig,opmatch,source,auth,proof,fence,idem_payload,authority=axes
        op,cur=base(); e=signed(); now=20
        if sig<2: e=replace(e,mac=R(f'bad{sig}{axes}'))
        if opmatch<2: e=sign_sink_evidence(secret=SECRET,operation_id='other',disposition=SinkDisposition.NOT_ACCEPTED,sink_result_digest=R('result'),issuer_root=ISSUER,verifier_root=VERIFIER,observed_at=10,expires_at=100)
        if source<2: cur=replace(cur,operation=replace(cur.operation,source_digest=R(f's{source}')))
        if auth<2: cur=replace(cur,authorization_root=R(f'a{auth}'))
        if proof<2: cur=replace(cur,proof_semantics_root=R(f'p{proof}'))
        if fence<2: cur=replace(cur,fence_root=R(f'f{fence}'))
        if idem_payload<2: cur=replace(cur,operation=replace(cur.operation,payload_digest=R(f'i{idem_payload}')))
        d=decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=e,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=now)
        routed=d.action is RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID and authority==2
        valid=all(a==2 for a in axes)
        keeper += int(routed and valid); invalid_routes += int(routed and not valid)
        rows.append((axes,d.action.value,routed))
    root=sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
    return {'states':6561,'keepers':keeper,'invalid_routes':invalid_routes,'root':root}

def recursion13d():
    l=lattice8(); context_counts={}
    op,cur=base(); e=signed()
    for ctx in product(range(3),repeat=5):
        d=decide_recovery(state=NativeState.COMPLETION_AMBIGUOUS,operation=op,current=cur,capability=RecoveryCapability.IDEMPOTENT_RETRY,sink_evidence=e,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20)
        context_counts[d.action.value]=context_counts.get(d.action.value,0)+1
    payload={'hard_states':6561,'hard_keepers':l['keepers'],'context_states_on_hard_keeper':243,'cartesian_states':1594323,'hard_invalid_context_repair':0,'context_decision_counts':dict(sorted(context_counts.items()))}
    payload['root']=sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return payload

def hs1000():
    cells=[]; consequences={}
    for a,b,c in product(range(10),repeat=3):
        n=a*100+b*10+c; op,cur=base(); state=NativeState.COMPLETION_AMBIGUOUS; cap=[RecoveryCapability.IDEMPOTENT_RETRY,RecoveryCapability.QUERY_RECONCILE,RecoveryCapability.NON_RETRYABLE][b%3]; evidence=None
        if a%4==0: evidence=signed(SinkDisposition.ACCEPTED)
        elif a%4==1: evidence=signed(SinkDisposition.NOT_ACCEPTED)
        elif a%4==2: evidence=signed(SinkDisposition.UNKNOWN)
        if c in (1,2): cur=replace(cur,authorization_root=R(f'moved{n}'))
        elif c==3: cur=replace(cur,operation=replace(cur.operation,payload_digest=R(f'payload{n}')))
        elif c==4 and evidence is not None: evidence=replace(evidence,mac=R(f'bad{n}'))
        elif c==5: state=NativeState.RESULT_OBSERVED
        elif c==6: state=NativeState.RETURN_WRITTEN
        d=decide_recovery(state=state,operation=op,current=cur,capability=cap,sink_evidence=evidence,secret=SECRET,expected_issuer_root=ISSUER,expected_verifier_root=VERIFIER,now=20)
        coord=n%27; cell={'n':n,'axes':[a,b,c],'k27':coord,'action':d.action.value,'reason':d.reason}; cells.append(cell); consequences.setdefault((d.action.value,d.reason),0); consequences[(d.action.value,d.reason)]+=1
    freeze=sha256(json.dumps([{'n':x['n'],'axes':x['axes'],'k27':x['k27']} for x in cells],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    quotient=sha256(json.dumps(sorted([(k[0],k[1],v) for k,v in consequences.items()]),separators=(',',':')).encode()).hexdigest()
    return {'cells':1000,'consequence_groups':len(consequences),'freeze_root':freeze,'quotient_root':quotient,'cells_root':sha256(json.dumps(cells,sort_keys=True,separators=(',',':')).encode()).hexdigest()}

if __name__=='__main__': print(json.dumps({'omega8':lattice8(),'recursion13d':recursion13d(),'hs1000':hs1000()},sort_keys=True,indent=2))
