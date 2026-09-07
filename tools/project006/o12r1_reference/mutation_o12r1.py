from dataclasses import replace
from o12r1_recovery import *
from test_o12r1 import base,J,R,CO,CV,SI,SV,FO,FV,CS,SS,FS,owner,ev,fr,dec

def run():
    row=base(); checks={}
    checks['caller_boolean_currentness']=dec(o=False).action is Action.HOLD_REBIND_REQUIRED
    checks['forged_current_owner']=dec(o=owner(owner_root=R('attacker'))).action is not Action.RETRY_EXACT_SAME_EFFECT
    checks['forged_current_mac']=dec(o=replace(owner(),mac=R('bad'))).action is not Action.RETRY_EXACT_SAME_EFFECT
    checks['forged_fence_owner']=dec(e=ev(),f=fr(owner_root=R('attacker'))).action is not Action.RETRY_EXACT_SAME_EFFECT
    checks['forged_fence_mac']=dec(e=ev(),f=replace(fr(),mac=R('bad'))).action is not Action.RETRY_EXACT_SAME_EFFECT
    checks['wrong_attempt']=dec(e=ev(effect_attempt_root=R('other')),f=fr()).action is not Action.RETRY_EXACT_SAME_EFFECT
    checks['accepted_no_result']=dec(e=ev(d=SinkDisposition.ACCEPTED,result=None)).action is not Action.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY
    checks['unknown_no_retry']=dec(e=ev(d=SinkDisposition.UNKNOWN,result=None),f=fr()).action is not Action.RETRY_EXACT_SAME_EFFECT
    checks['retryable_ambiguity_not_final']=guard_final_projection(journal=J(row),command_id='cmd',recovery_mode=RecoveryMode.IDEMPOTENT_RETRY).action is FinalAction.HOLD_RECOVERY_REQUIRED
    checks['terminal_no_reexec']=dec(row=base('RESULT_OBSERVED')).action is Action.RETRY_RETURN_WRITER_ONLY
    return {'mutants':len(checks),'killed':sum(checks.values()),'details':checks}
if __name__=='__main__':import json;print(json.dumps(run(),sort_keys=True,indent=2))
