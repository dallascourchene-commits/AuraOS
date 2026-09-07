from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
import random

from memory_city_coverage_membrane import AdmissionMode, PositiveTrace, compile_coverage_certificate, compile_proof_carrying_typed_admission
from memory_city_read_consequence import ReadWorldBinding, compile_read_consequence_certificate
from memory_city_support_hydration import SupportClosedHydration
from memory_city_typed_closure import REPROOF_SEMANTICS, TypedClosureCertificate, TypedClosureDisposition
from memory_city_effect_handoff_o13 import EffectHandoffEvidence,HandoffDisposition,HandoffVerificationContext,MutationBoundaryProjection,compile_effect_handoff
from memory_city_consequence_refinement import EffectIntent,EffectObligationProjection,compile_effect_refinement,effect_escalation_root
from memory_city_effect_refinement_handoff_o14 import EffectRefinementEvidence,EffectRefinementVerificationContext,compile_effect_refined_handoff


def hx(value: str) -> str: return sha256(value.encode()).hexdigest()


def fixture(tag: str):
    hydration=SupportClosedHydration("READY_SUPPORT_CLOSED_HYDRATION_D0",("a","b"),(),20,100,0.2,hx(f"plan:{tag}"),hx(f"hydr:{tag}"),support_root=hx(f"support:{tag}"))
    closure=TypedClosureCertificate(TypedClosureDisposition.READY,None,hydration.support_root,hx(f"influence:{tag}"),("a","b","c"),2,hx(f"transition:{tag}"),hx(f"future:{tag}"),hx(f"typed:{tag}"),reproof_semantics=REPROOF_SEMANTICS)
    binding=ReadWorldBinding(hydration,closure).binding_root
    program=hx(f"program:{tag}"); domain=hx(f"domain:{tag}")
    coverage=compile_coverage_certificate(program_root=program,sealed_domain_root=domain,generation=7,obligations=(binding,),positive=(PositiveTrace(binding,program,domain,7,hx(f"trace:{tag}"),True,True),))
    cert=compile_read_consequence_certificate((ReadWorldBinding(hydration,closure),),coverage)
    admission=compile_proof_carrying_typed_admission(typed_closure_receipt_root=closure.receipt_root,coverage=coverage,support_root=hydration.support_root,influence_root=closure.influence_root,transition_model_root=closure.transition_model_root,future_congruence_root=closure.future_congruence_root,horizon=closure.horizon,mode=AdmissionMode.EFFECT_BOUND)
    base_kwargs=dict(hydration=hydration,typed_closure=closure,fixed_support_root=hydration.support_root,coverage=coverage,current_program_root=program,current_sealed_domain_root=domain,current_coverage_generation=7,admission=admission,evidence=EffectHandoffEvidence(hx(f"owner:{tag}"),hx(f"verifier:{tag}")),mutation=MutationBoundaryProjection("cell",4,hx(f"cfg:{tag}"),8,17,17,"worker",100,hx(f"ta:{tag}"),hx(f"rf:{tag}")),verification=HandoffVerificationContext("cell",4,hx(f"cfg:{tag}"),8,17,17,"worker",100,hx(f"owner:{tag}"),hx(f"verifier:{tag}"),hx(f"ta:{tag}"),hx(f"rf:{tag}"),50))
    intent=EffectIntent(hx(f"intent:{tag}"),hx(f"effect-domain:{tag}"),hx(f"effect-program:{tag}"))
    plan=compile_effect_refinement((EffectObligationProjection(binding,hx(f"obligation:{tag}"),hx(f"obligation-evidence:{tag}"),True,True,hx(f"nuisance:{tag}")),),cert,intent)
    child=plan.subclasses[0]
    refinement=EffectRefinementEvidence(plan,intent,child,hx(f"ref-owner:{tag}"),hx(f"ref-verifier:{tag}"))
    current=EffectRefinementVerificationContext(binding,plan.plan_root,intent.binding_root,child.obligation_root,effect_escalation_root(plan,child),refinement.owner_receipt_root,refinement.verifier_receipt_root)
    return cert,base_kwargs,refinement,current


def run(n:int=16000, seed:int=14014):
    rng=random.Random(seed)
    modes=("valid","plan","intent","obligation","escalation","owner","verifier","binding")
    counts={"cases":n,"candidate_tecc":0,"oracle_tecc":0,"false_tecc":0,"false_hold":0,"base_collision_pairs":0,"refined_collision_pairs":0,"nuisance_false_splits":0,"effect_ready":0}
    samples=[]
    for i in range(n):
        cert,kw,ref,current=fixture(str(i+1)); mode=modes[i%len(modes)]; cur=current
        if mode=="plan":cur=replace(cur,plan_root=hx(f"moved-plan:{i}"))
        elif mode=="intent":cur=replace(cur,intent_binding_root=hx(f"moved-intent:{i}"))
        elif mode=="obligation":cur=replace(cur,obligation_root=hx(f"moved-obligation:{i}"))
        elif mode=="escalation":cur=replace(cur,escalation_root=hx(f"moved-escalation:{i}"))
        elif mode=="owner":cur=replace(cur,owner_receipt_root=hx(f"moved-owner:{i}"))
        elif mode=="verifier":cur=replace(cur,verifier_receipt_root=hx(f"moved-verifier:{i}"))
        elif mode=="binding":cur=replace(cur,read_binding_root=hx(f"moved-binding:{i}"))
        d=compile_effect_refined_handoff(cert,**kw,refinement=ref,refinement_verification=cur)
        got=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0; expected=mode=="valid"
        counts["candidate_tecc"]+=got; counts["oracle_tecc"]+=expected; counts["false_tecc"]+=got and not expected; counts["false_hold"]+=(not got) and expected; counts["effect_ready"]+=d.effect_authority
        if i<32:samples.append((i,mode,d.disposition.value,d.reason,d.tecc_input_root))
    for j in range(4000):
        cert,kw,ref1,current1=fixture(f"pair:{j}")
        o13a=compile_effect_handoff(cert,**kw); o13b=compile_effect_handoff(cert,**kw)
        intent2=EffectIntent(hx(f"alt-intent:{j}"),ref1.intent.effect_domain_root,ref1.intent.program_root); binding=current1.read_binding_root
        plan2=compile_effect_refinement((EffectObligationProjection(binding,hx(f"alt-obligation:{j}"),hx(f"alt-evidence:{j}"),True,True,hx(f"alt-nuisance:{j}")),),cert,intent2); child2=plan2.subclasses[0]
        ref2=EffectRefinementEvidence(plan2,intent2,child2,hx(f"alt-owner:{j}"),hx(f"alt-verifier:{j}")); current2=EffectRefinementVerificationContext(binding,plan2.plan_root,intent2.binding_root,child2.obligation_root,effect_escalation_root(plan2,child2),ref2.owner_receipt_root,ref2.verifier_receipt_root)
        d1=compile_effect_refined_handoff(cert,**kw,refinement=ref1,refinement_verification=current1); d2=compile_effect_refined_handoff(cert,**kw,refinement=ref2,refinement_verification=current2)
        counts["base_collision_pairs"] += o13a.tecc_input_root==o13b.tecc_input_root
        counts["refined_collision_pairs"] += d1.tecc_input_root==d2.tecc_input_root
        plan3=compile_effect_refinement((EffectObligationProjection(binding,ref1.child.obligation_root,ref1.child.evidence_roots[0],True,True,hx(f"different-nuisance:{j}")),),cert,ref1.intent); child3=plan3.subclasses[0]
        ref3=EffectRefinementEvidence(plan3,ref1.intent,child3,ref1.owner_receipt_root,ref1.verifier_receipt_root); current3=EffectRefinementVerificationContext(binding,plan3.plan_root,ref1.intent.binding_root,child3.obligation_root,effect_escalation_root(plan3,child3),ref3.owner_receipt_root,ref3.verifier_receipt_root)
        d3=compile_effect_refined_handoff(cert,**kw,refinement=ref3,refinement_verification=current3)
        counts["nuisance_false_splits"] += d1.tecc_input_root!=d3.tecc_input_root
    payload={"schema":"AURA-O14-CAMPAIGN-v2-INTEGRATED","counts":counts,"sample":samples}
    payload["campaign_root"]=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return payload

if __name__=="__main__":print(json.dumps(run(),sort_keys=True,separators=(",",":")))
