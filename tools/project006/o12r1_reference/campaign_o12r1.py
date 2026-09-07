from dataclasses import replace
from hashlib import sha256
import hmac,json,random
from o12r1_recovery import *
from test_o12r1 import base,J,R,CS,SS,FS,CO,CV,SI,SV,FO,FV,owner,ev,fr

def mac(secret,p):return hmac.new(secret,json.dumps(p,sort_keys=True,separators=(',',':')).encode(),sha256).hexdigest()
def owner_ok(o,row,now):
    return isinstance(o,AtUseOwnerReceipt) and o.operation_id=='op' and o.resource_root==R('resource') and o.owner_root==CO and o.verifier_root==CV and o.owner_generation==7 and now<=o.expires_at and hmac.compare_digest(mac(CS,o.unsigned()),o.mac) and row['intent_root']==o.intent_root and row['contract_root']==o.contract_root and row['source_digest']==o.source_digest and row['idempotency_key']==o.idempotency_key and row['effect_payload_root']==o.effect_payload_root
def sink_ok(e,row,now):
    return e is not None and e.operation_id=='op' and e.effect_attempt_root==row['effect_attempt_root'] and row['provider_operation_root'] is not None and e.provider_operation_root==row['provider_operation_root'] and e.issuer_root==SI and e.verifier_root==SV and now<=e.expires_at and hmac.compare_digest(mac(SS,e.unsigned()),e.mac)
def fence_ok(f,e,row,now):
    return f is not None and f.operation_id=='op' and f.resource_root==R('resource') and f.fenced_attempt_root==row['effect_attempt_root'] and f.owner_root==FO and f.verifier_root==FV and f.owner_generation==9 and now<=f.expires_at and hmac.compare_digest(mac(FS,f.unsigned()),f.mac) and f.generation==f.installed_generation and f.generation>e.fence_generation and f.previous_generation>=e.fence_generation
def oracle(row,mode,o,e,f,now):
    p=row['phase']
    if p=='RETURN_WRITTEN':return Action.DONE
    if p in ('RESULT_OBSERVED','ERROR_TERMINAL'):return Action.RETRY_RETURN_WRITER_ONLY
    if p!='COMPLETION_AMBIGUOUS':return Action.HOLD_UNSUPPORTED
    if not owner_ok(o,row,now):return Action.HOLD_REBIND_REQUIRED
    if e is None:
        return Action.RETRY_EXACT_SAME_EFFECT if mode is RecoveryMode.IDEMPOTENT_RETRY else (Action.QUERY_PROVIDER_STATUS if mode is RecoveryMode.QUERY_RECONCILE else Action.HOLD_AMBIGUOUS)
    if not sink_ok(e,row,now):return Action.HOLD_INVALID_EVIDENCE
    if e.disposition is SinkDisposition.ACCEPTED:return Action.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY if e.result_locator_root else Action.HOLD_AMBIGUOUS
    if e.disposition is SinkDisposition.UNKNOWN:return Action.HOLD_AMBIGUOUS
    if mode is RecoveryMode.NON_RETRYABLE:return Action.HOLD_AMBIGUOUS
    if not fence_ok(f,e,row,now):return Action.HOLD_INVALID_EVIDENCE if f is not None else Action.HOLD_AMBIGUOUS
    return Action.RETRY_EXACT_SAME_EFFECT

def decide(row,mode,o,e,f,now):
    return decide_from_owner(journal=J(row),command_id='cmd',recovery_mode=mode,current_receipt=o,current_secret=CS,current_operation_id='op',current_resource_root=R('resource'),current_owner_root=CO,current_verifier_root=CV,current_owner_generation=7,sink_evidence=e,sink_secret=SS,sink_issuer_root=SI,sink_verifier_root=SV,fence_receipt=f,fence_secret=FS,fence_owner_root=FO,fence_verifier_root=FV,fence_owner_generation=9,now=now)
def run(cases=30000):
    rng=random.Random(20260907); actions={}; out={'cases':cases,'oracle_mismatches':0,'forged_current_owner_replays':0,'forged_fence_replays':0,'accepted_provider_replays':0,'finalization_bypasses':0,'authority_minted':0,'naive_ambiguous_replays':0}
    modes=list(RecoveryMode); phases=['COMPLETION_AMBIGUOUS','RESULT_OBSERVED','ERROR_TERMINAL','RETURN_WRITTEN','ACK_WRITTEN_PRE_EFFECT']
    for i in range(cases):
        row=base(rng.choice(phases)); mode=rng.choice(modes); now=20; o=owner(row); e=None; f=None; m=rng.randrange(18)
        if m==0:o=replace(o,mac=R('bad'+str(i)))
        elif m==1:o=owner(row,owner_root=R('attacker'))
        elif m==2:o=owner(row,owner_generation=8)
        elif m==3:o=owner(row,source_digest=R('moved'+str(i)))
        elif m==4:e=ev(row,SinkDisposition.ACCEPTED,R('loc'+str(i)))
        elif m==5:e=ev(row,SinkDisposition.ACCEPTED,None)
        elif m==6:e=ev(row,SinkDisposition.UNKNOWN,None)
        elif m==7:e=ev(row); f=fr(row)
        elif m==8:e=ev(row); f=fr(row,owner_root=R('attacker'))
        elif m==9:e=ev(row); f=replace(fr(row),mac=R('bad'+str(i)))
        elif m==10:e=ev(row,effect_attempt_root=R('other'+str(i))); f=fr(row)
        elif m==11:e=ev(row,provider_operation_root=R('other'+str(i)));f=fr(row)
        elif m==12:e=replace(ev(row),mac=R('bad'+str(i)))
        elif m==13:e=ev(row);f=fr(row,installed_generation=3)
        elif m==14:e=ev(row);f=fr(row,owner_generation=8)
        elif m==15:o=False
        elif m==16:o=owner(row,expires_at=15)
        d=decide(row,mode,o,e,f,now); q=oracle(row,mode,o,e,f,now)
        out['oracle_mismatches']+=int(d.action is not q); out['authority_minted']+=int(d.effect_authority or d.gate10); actions[d.action.value]=actions.get(d.action.value,0)+1
        if row['phase']=='COMPLETION_AMBIGUOUS' and q is not Action.RETRY_EXACT_SAME_EFFECT:out['naive_ambiguous_replays']+=1
        if row['phase']=='COMPLETION_AMBIGUOUS' and isinstance(o,AtUseOwnerReceipt) and o.owner_root!=CO:out['forged_current_owner_replays']+=int(d.action is Action.RETRY_EXACT_SAME_EFFECT)
        if row['phase']=='COMPLETION_AMBIGUOUS' and f is not None and f.owner_root!=FO:out['forged_fence_replays']+=int(d.action is Action.RETRY_EXACT_SAME_EFFECT)
        if e is not None and e.disposition is SinkDisposition.ACCEPTED:out['accepted_provider_replays']+=int(d.action is Action.RETRY_EXACT_SAME_EFFECT)
        if row['phase']=='COMPLETION_AMBIGUOUS' and mode is not RecoveryMode.NON_RETRYABLE:
            gd=guard_final_projection(journal=J(row),command_id='cmd',recovery_mode=mode);out['finalization_bypasses']+=int(gd.action is FinalAction.STAGE_FINAL_RETURN)
    out['actions']=dict(sorted(actions.items())); out['campaign_root']=sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if any(out[k] for k in ('oracle_mismatches','forged_current_owner_replays','forged_fence_replays','accepted_provider_replays','finalization_bypasses','authority_minted')):raise AssertionError(out)
    return out
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
