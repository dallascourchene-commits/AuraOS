import hashlib,json
from dataclasses import dataclass
from memory_city_consequence_refinement import *
R=lambda x:digest(x)
I=EffectIntent(R('intent'),R('effect-domain'),R('program'))
@dataclass(frozen=True)
class ReadCert:
    status:str;coverage_receipt_root:str;program_root:str;sealed_domain_root:str;coverage_generation:int;binding_roots:tuple;transition_model_root:str;horizon:int;future_congruence_root:str|None;consequence_root:str;receipt_root:str
def proj(b,obl='o',auth=True,current=True,cfg=None):return EffectObligationProjection(b,None if obl is None else R(obl),None if obl is None else R(['ev',b,obl]),auth,current,R(cfg or ['cfg',b]))
def main():
    keys=['cases','bindings','oracle_ready_bindings','refined_ready_bindings','refinement_false_ready','refinement_false_hold','naive_read_as_effect_false_ready','detached_key_false_ready','modeled_full_identity_false_hold','effect_subclasses','multi_obligation_cases','forged_cases','stale_cases','binding_attack_cases','intent_move_cases','obligation_move_cases','valid_nuisance_cases']
    m={k:0 for k in keys}
    for n in range(12000):
        bs=tuple(R(['b',n,i]) for i in range(4));c=ReadCert('READY_D0',R(['coverage',n]),R('program'),R('domain'),7,bs,R('transition'),2,R('future'),R('consequence'),R(['receipt',n]));cls=n%8;intent=I;use_attack=None
        if cls==0: ps=tuple(proj(b,cfg=['noise',i]) for i,b in enumerate(bs));m['valid_nuisance_cases']+=1
        elif cls==1: ps=(proj(bs[0],'a'),proj(bs[1],'a'),proj(bs[2],'b'),proj(bs[3],'b'));m['multi_obligation_cases']+=1
        elif cls==2: ps=(proj(bs[0],auth=False),proj(bs[1]),proj(bs[2]),proj(bs[3]));m['forged_cases']+=1
        elif cls==3: ps=(proj(bs[0],current=False),proj(bs[1]),proj(bs[2]),proj(bs[3]));m['stale_cases']+=1
        elif cls==4: ps=(proj(R(['detached',n])),proj(bs[1]),proj(bs[2]),proj(bs[3]));m['binding_attack_cases']+=1
        elif cls==5: ps=tuple(proj(b) for b in bs);use_attack='intent';m['intent_move_cases']+=1
        elif cls==6: ps=tuple(proj(b) for b in bs);use_attack='obligation';m['obligation_move_cases']+=1
        else: ps=(proj(bs[0],'a'),proj(bs[1],'b'),proj(bs[2],'c'),proj(bs[3],'d'))
        plan=compile_effect_refinement(ps,c,intent);got={b:child for child in plan.subclasses for b in child.member_binding_roots}
        projection_by={x.read_binding_root:x for x in ps}
        envelope_exact=len(projection_by)==len(ps) and set(projection_by)==set(bs)
        oracle={}
        for b in bs:
            x=projection_by.get(b);valid=bool(envelope_exact and x and x.effect_obligation_root and x.obligation_evidence_root and x.obligation_authenticated and x.observation_current)
            oracle[b]=valid;m['oracle_ready_bindings']+=int(valid);g=b in got;m['refined_ready_bindings']+=int(g);m['refinement_false_ready']+=int(g and not valid);m['refinement_false_hold']+=int((not g) and valid)
            m['naive_read_as_effect_false_ready']+=int(not valid)
        if cls==4:m['detached_key_false_ready']+=1
        valid=[b for b,v in oracle.items() if v]
        if len(valid)>1:m['modeled_full_identity_false_hold']+=len(valid)
        if use_attack=='intent' and plan.subclasses:
            i2=EffectIntent(R(['intent2',n]),I.effect_domain_root,I.program_root);assert validate_effect_binding(plan,cert=c,intent=i2,read_binding_root=bs[0],obligation_root=projection_by[bs[0]].effect_obligation_root)=='HOLD_EFFECT_INTENT_MOVED'
        if use_attack=='obligation' and plan.subclasses:assert validate_effect_binding(plan,cert=c,intent=I,read_binding_root=bs[0],obligation_root=R(['moved',n]))=='HOLD_EFFECT_OBLIGATION_MOVED'
        assert refinement_invariants(c,plan)
        m['cases']+=1;m['bindings']+=4;m['effect_subclasses']+=len(plan.subclasses)
    assert m['refinement_false_ready']==0 and m['refinement_false_hold']==0
    out={'schema':'AURA-MEMORY-CITY-CONSEQUENCE-REFINEMENT-CAMPAIGN-v2','metrics':m};out['campaign_root']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest();print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
