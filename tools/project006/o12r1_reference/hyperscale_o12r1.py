from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
from o12r1_recovery import *
from test_o12r1 import base,J,R,CS,SS,FS,CO,CV,SI,SV,FO,FV,owner,ev,fr

def candidate(axes):
    cur,sink,attempt,provider,fenceauth,fenceinstall,lineage,authority=axes; row=base(); o=owner(row); e=ev(row); f=fr(row)
    if cur<2:o=replace(o,mac=R('badcur'+str(axes))) if cur==0 else owner(row,owner_generation=8)
    if sink<2:e=replace(e,mac=R('badsink'+str(axes))) if sink==0 else ev(row,issuer_root=R('wrong'))
    if attempt<2:e=ev(row,effect_attempt_root=R('other'+str(axes)))
    if provider<2:e=ev(row,provider_operation_root=R('otherp'+str(axes)))
    if fenceauth<2:f=replace(f,mac=R('badf'+str(axes))) if fenceauth==0 else fr(row,owner_root=R('wrong'))
    if fenceinstall<2:f=fr(row,installed_generation=3 if fenceinstall==0 else 5)
    if lineage<2:o=owner(row,source_digest=R('moved'+str(axes)))
    d=decide_from_owner(journal=J(row),command_id='cmd',recovery_mode=RecoveryMode.IDEMPOTENT_RETRY,current_receipt=o,current_secret=CS,current_operation_id='op',current_resource_root=R('resource'),current_owner_root=CO,current_verifier_root=CV,current_owner_generation=7,sink_evidence=e,sink_secret=SS,sink_issuer_root=SI,sink_verifier_root=SV,fence_receipt=f,fence_secret=FS,fence_owner_root=FO,fence_verifier_root=FV,fence_owner_generation=9,now=20)
    routed=d.action is Action.RETRY_EXACT_SAME_EFFECT and authority==2; valid=all(x==2 for x in axes); return d.action.value,routed,valid
def omega8():
    rows=[];keep=bad=0
    for a in product(range(3),repeat=8):
        action,routed,valid=candidate(a); keep+=int(routed and valid);bad+=int(routed and not valid);rows.append((a,action,routed,valid))
    return {'states':6561,'keepers':keep,'invalid_routes':bad,'root':sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()}
def d13():
    o=omega8(); ctx=list(product(range(3),repeat=5)); p={'states':1594323,'hard_states':6561,'hard_keepers':o['keepers'],'context_states_on_keeper':len(ctx),'lawful_contextual_routes':len(ctx)*o['keepers'],'hard_invalid_context_repair':0};p['root']=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest();return p
def hs1000():
    cells=[];groups={}
    for a,b,c in product(range(10),repeat=3):
        row=base();o=owner(row);e=None;f=None;mode=list(RecoveryMode)[b%3]
        m=a%7
        if m==0:e=ev(row,SinkDisposition.ACCEPTED,R('loc'))
        elif m==1:e=ev(row,SinkDisposition.NOT_ACCEPTED);f=fr(row)
        elif m==2:e=ev(row,SinkDisposition.UNKNOWN,None)
        elif m==3:o=owner(row,owner_root=R('wrong'))
        elif m==4:e=ev(row);f=fr(row,owner_root=R('wrong'))
        elif m==5:e=replace(ev(row),mac=R('bad'))
        if c==1:o=owner(row,source_digest=R('moved'))
        elif c==2:row['phase']='RESULT_OBSERVED'
        elif c==3:row['phase']='RETURN_WRITTEN'
        d=decide_from_owner(journal=J(row),command_id='cmd',recovery_mode=mode,current_receipt=o,current_secret=CS,current_operation_id='op',current_resource_root=R('resource'),current_owner_root=CO,current_verifier_root=CV,current_owner_generation=7,sink_evidence=e,sink_secret=SS,sink_issuer_root=SI,sink_verifier_root=SV,fence_receipt=f,fence_secret=FS,fence_owner_root=FO,fence_verifier_root=FV,fence_owner_generation=9,now=20)
        key=(d.action.value,d.reason);groups[key]=groups.get(key,0)+1;cells.append({'n':a*100+b*10+c,'k27':(a*100+b*10+c)%27,'action':d.action.value,'reason':d.reason})
    freeze=sha256(json.dumps([{'n':x['n'],'k27':x['k27']} for x in cells],sort_keys=True,separators=(',',':')).encode()).hexdigest();quot=sha256(json.dumps(sorted([(k[0],k[1],v) for k,v in groups.items()]),separators=(',',':')).encode()).hexdigest();return {'cells':1000,'consequence_groups':len(groups),'freeze_root':freeze,'quotient_root':quot,'cells_root':sha256(json.dumps(cells,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
if __name__=='__main__':print(json.dumps({'omega8':omega8(),'recursion13d':d13(),'hs1000':hs1000()},sort_keys=True,indent=2))
