from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from tools.project006.tecc_effect_admission_bridge import *

def r(x): return sha256(x.encode()).hexdigest()
@dataclass(frozen=True)
class I: command_id:str='cmd'; idempotency_key:str='idem'; source_file_id:str='drive-file-1'; source_revision:str='rev-1'; source_digest:str=r('src')
@dataclass(frozen=True)
class N: identity_root:str=r('intent'); effect_payload_root:str=r('payload')
@dataclass(frozen=True)
class K: contract_root:str=r('contract')

def make():
    i,n,k=I(),N(),K()
    p=ProducerTeccEvidence('OWNER-O14-v1','semantic',r('tecc'),r('handoff'),r('refine'),r('escalate'),n.identity_root,n.effect_payload_root,r('proofgen'),'reproof-v3','producer-A',TECC_SCHEMA,r('zero'))
    p=replace(p,receipt_root=digest(p.payload()))
    c=ConsumerAdmissionEvidence(CONSUMER_SCHEMA,'BIND_TECC_CONSUMER_D0',p.receipt_root,p.tecc_input_root,7,r('current'),'tecc-1','observer-B',r('obs'),r('zero'))
    c=replace(c,admission_root=digest(c.payload()))
    reg=TeccVerifierRegistry(b'reference-test-key-32-bytes!!!!',r('registry'))
    x=AdmissionAtUseContext(p.producer_schema,p.producer_semantic_head,p.receipt_root,p.proof_generation_root,p.proof_semantics_id,p.producer_lineage,p.tecc_input_root,p.effect_escalation_root,CONSUMER_SCHEMA,7,r('current'),'tecc-1',r('scope'),3,50)
    a=issue_authorization_receipt(producer=p,consumer=c,ident=i,intent=n,contract=k,authority_scope_root=r('scope'),authority_epoch=3,expires_at=100,verifier_instance='tecc-1',key=reg.authorization_key)
    return i,n,k,p,c,a,x,reg

def mutate(mode):
    i,n,k,p,c,a,x,g=make()
    if mode==1: p=replace(p,producer_schema='LOOKALIKE'); p=replace(p,receipt_root=digest(p.payload()))
    elif mode==2: p=replace(p,receipt_root=r('bad'))
    elif mode==3: c=replace(c,disposition='HOLD_EXTERNAL_AUTH_D0'); c=replace(c,admission_root=digest(c.payload()))
    elif mode==4: c=replace(c,observer_lineage=p.producer_lineage); c=replace(c,admission_root=digest(c.payload()))
    elif mode==5: c=replace(c,consumer_generation=8); c=replace(c,admission_root=digest(c.payload()))
    elif mode==6: x=replace(x,currentness_root=r('moved'))
    elif mode==7: a=replace(a,signature=r('forged'))
    elif mode==8: a=issue_authorization_receipt(producer=p,consumer=c,ident=i,intent=n,contract=k,authority_scope_root=r('scope'),authority_epoch=3,expires_at=100,verifier_instance='tecc-1',key=g.authorization_key,authorized=False)
    elif mode==9: x=replace(x,now=100)
    elif mode==10: x=replace(x,authority_epoch=4)
    elif mode==11: i=replace(i,idempotency_key='other')
    elif mode==12: n=replace(n,identity_root=r('intent2'))
    elif mode==13: n=replace(n,effect_payload_root=r('payload2'))
    elif mode==14: k=replace(k,contract_root=r('contract2'))
    elif mode==15: x=replace(x,verifier_instance='tecc-2')
    elif mode==16: c=replace(c,tecc_input_root=r('other')); c=replace(c,admission_root=digest(c.payload()))
    elif mode==17: a=replace(a,tecc_input_root=r('other')); a=replace(a,signature=sign_authorization(a.payload(),g.authorization_key))
    elif mode==18: p=replace(p,required_verifier_schema='OTHER'); p=replace(p,receipt_root=digest(p.payload()))
    elif mode==19: i=replace(i,source_revision='rev-2')
    elif mode==20: i=replace(i,source_file_id='drive-file-2')
    elif mode==21: pass
    return i,n,k,p,c,a,x,g

def run(cases=24000):
    c={'cases':cases,'oracle_bind':0,'oracle_nonbind':0,'candidate_false_bind':0,'candidate_false_hold':0,'legacy_unproofed_false_ready':0,'legacy_same_digest_source_collision':0,'effect_ready':0}
    for z in range(cases):
        mode=z%22; args=mutate(mode); expected=mode in (0,21)
        d=validate_effect_admission(producer=args[3],consumer=args[4],authorization=args[5],ident=args[0],intent=args[1],contract=args[2],ctx=args[6],registry=args[7])
        got=d.disposition is AdmissionDisposition.BIND_EFFECT_ATTEMPT_D0
        c['oracle_bind' if expected else 'oracle_nonbind']+=1
        c['candidate_false_bind']+=int(got and not expected)
        c['candidate_false_hold']+=int(expected and not got)
        c['legacy_unproofed_false_ready']+=int(not expected)
        if mode in (19,20):
            base=make(); legacy=lambda q: digest({'schema':'AURA-PROJECT006-TECC-EFFECT-ADMISSION-BRIDGE-v1','kind':'operation_identity','command_id':q.command_id,'idempotency_key':q.idempotency_key,'source_digest':q.source_digest,'intent_root':args[1].identity_root,'effect_payload_root':args[1].effect_payload_root,'contract_root':args[2].contract_root})
            c['legacy_same_digest_source_collision']+=int(legacy(base[0])==legacy(args[0]))
        c['effect_ready']+=int(d.effect_authority)
    raw=json.dumps(c,sort_keys=True,separators=(',',':')).encode(); out={**c,'campaign_root':sha256(raw).hexdigest(),'schema':'aura.mc_o14r.tecc_effect_admission.campaign.v2','authority':D0}
    if c['candidate_false_bind'] or c['candidate_false_hold'] or c['effect_ready']: raise AssertionError(out)
    return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
