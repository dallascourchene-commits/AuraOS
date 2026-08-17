"""Stage 06 W6 D0 mutant and primitive acceptance harness."""
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from aura_os_minimal import (  # noqa: E402
    CausalFence,
    Disposition,
    EffectDecision,
    ObligationResult,
    PassReceipt,
    REQUIRED_PROOF_CHECKS,
    RequiredObligation,
    ResidualBuffer,
    TriProposalBundle,
    VerificationEvidence,
    evaluate_containment,
    idle_state,
    p_fence,
    p_ingress,
    p_residual,
    p_router,
)

GEN = "D0-G1"
CANONICAL_MUTANTS = {
    "JOINT_MARGINAL_MUTANT": (
        "joint_dependency_complete", False,
        "decision-changing joint interaction was certified from marginals only",
    ),
    "OMISSION_MUTANT": (
        "required_evidence_present", False,
        "known required evidence was omitted",
    ),
    "RECURSIVE_SAME_BLINDSPOT": (
        "independent_defeat_path", False,
        "recursive checker shares the same blind spot",
    ),
    "SELF_CERTIFIED_KNOWN_ONLY": (
        "external_wake_path", False,
        "known-only view self-certified completeness",
    ),
    "STALE_GENERATION_MUTANT": (
        "generation_current", False,
        "closure evidence is stale relative to required generation",
    ),
}


def fact_obligation(name: str, fact: str, bad: object, reason: str) -> RequiredObligation:
    def evaluator(facts):
        if fact not in facts or facts[fact] is None:
            return ObligationResult(Disposition.UNKNOWN, f"{name}: missing {fact}")
        if facts[fact] == bad:
            return ObligationResult(Disposition.FAIL, reason)
        return ObligationResult(Disposition.PASS)
    return RequiredObligation(name, evaluator, cost_tier=1, estimated_cost=1.0, estimated_fail_probability=0.99)


def sentinel(counter: dict[str, int], name: str) -> RequiredObligation:
    def evaluator(_):
        counter["calls"] += 1
        return ObligationResult(Disposition.PASS, "sentinel")
    return RequiredObligation(name, evaluator, cost_tier=4, estimated_cost=1000.0, estimated_fail_probability=0.0)


def route_fixture(**overrides):
    packet = p_ingress({"route:local", "obligation:change"})
    residual = ResidualBuffer(obligations={"obligation:change"})
    proposals = TriProposalBundle(
        {"effect_class": "CHANGE"},
        {"effect_class": "CHANGE"},
        {"effect_class": "CHANGE"},
    )
    kwargs = dict(
        direction="route:local",
        phase="STAGE06",
        subject="obligation:change",
        authority_voice="AUTHORIZED_CONTROLLER",
        authority_current=True,
    )
    kwargs.update(overrides)
    return packet, proposals, residual, p_router(packet, proposals, residual, **kwargs)


def full_verification(**overrides):
    checks = {name: True for name in REQUIRED_PROOF_CHECKS}
    checks.update(overrides)
    return VerificationEvidence("G1", checks)


def run_vectors() -> dict[str, dict[str, object]]:
    vectors = json.loads((HERE / "W4_TEST_VECTORS.json").read_text(encoding="utf-8"))["vectors"]
    out: dict[str, dict[str, object]] = {}
    for vector in vectors:
        case = vector["id"]
        ok = False
        observed = ""
        reason = ""
        if case == "INGRESS_VALID":
            p = p_ingress({"n1"}); ok = p.origin == (0, 0, 0, 0); observed = "PASS" if ok else "FAIL"
        elif case == "INGRESS_EMPTY":
            try: p_ingress(set())
            except ValueError: ok = True; observed = "REJECT"
        elif case.startswith("ROUTER_"):
            if case == "ROUTER_VALID":
                _,_,_,r = route_fixture(); ok = r.decision is EffectDecision.ADMIT and r.valid; observed=r.decision.value; reason=r.reason
            elif case == "ROUTER_MISSING_ASP":
                _,_,_,r = route_fixture(phase=None); ok=r.decision is EffectDecision.BLOCK and r.reason==vector["reason"]; observed=r.decision.value; reason=r.reason
            elif case == "ROUTER_MISSING_VOICE":
                _,_,_,r = route_fixture(authority_voice=None); ok=r.decision is EffectDecision.BLOCK and r.reason==vector["reason"]; observed=r.decision.value; reason=r.reason
            elif case == "ROUTER_SUBJECT_OUTSIDE_CONE":
                packet=p_ingress({"route:local"}); residual=ResidualBuffer(obligations={"obligation:change"}); proposals=TriProposalBundle(*({"effect_class":"CHANGE"},)*3)
                r=p_router(packet,proposals,residual,direction="route:local",phase="STAGE06",subject="obligation:change",authority_voice="AUTHORIZED_CONTROLLER",authority_current=True)
                ok=r.decision is EffectDecision.BLOCK and r.reason==vector["reason"]; observed=r.decision.value; reason=r.reason
            elif case == "ROUTER_DIVERGENT_TRIAD":
                packet=p_ingress({"route:local","obligation:change"}); residual=ResidualBuffer(obligations={"obligation:change"}); proposals=TriProposalBundle({"effect_class":"CHANGE"},{"effect_class":"VERIFY"},{"effect_class":"CHANGE"})
                r=p_router(packet,proposals,residual,direction="route:local",phase="STAGE06",subject="obligation:change",authority_voice="AUTHORIZED_CONTROLLER",authority_current=True)
                ok=r.decision is EffectDecision.BLOCK and r.reason==vector["reason"]; observed=r.decision.value; reason=r.reason
        elif case.startswith("FENCE_"):
            *_, route = route_fixture()
            fence=CausalFence(1.0,2.0,True); verification=full_verification(); authority=True
            if case == "FENCE_RD_EQ_CD": fence=CausalFence(2.0,2.0,True)
            elif case == "FENCE_PROOF_UNKNOWN": verification=full_verification(zk_verification=None)
            elif case == "FENCE_AUTHORITY_UNKNOWN": authority=None
            elif case == "FENCE_FAIL_CLOSED_DISABLED": fence=CausalFence(1.0,2.0,False)
            r=p_fence(route,fence,verification,authority_current=authority)
            ok = r.decision.value == vector["expected"]
            if "reason" in vector: ok = ok and r.reason == vector["reason"]
            observed=r.decision.value; reason=r.reason
        elif case.startswith("RESIDUAL_"):
            b=ResidualBuffer(obligations={"o1"})
            if case == "RESIDUAL_CURRENT_VERIFIED_PASS": receipt=PassReceipt("r1","o1",Disposition.PASS,"G1",True,True)
            elif case == "RESIDUAL_STALE_GENERATION": receipt=PassReceipt("r1","o1",Disposition.PASS,"G0",True,True)
            else: receipt=PassReceipt("r1","o1",Disposition.PASS,"G1",False,True)
            r=p_residual(b,[receipt],required_generation="G1")
            ok=r.disposition.value==vector["expected"] and len(r.residual)==vector["residual_count"]
            observed=r.disposition.value; reason=str(r.rejected_receipts)
        elif case == "IDLE_ZERO_TASK_STATE":
            state=idle_state(); ok=state==() and len(state)==0; observed="PASS" if ok else "FAIL"
        out[case]={"pass":ok,"expected":vector["expected"],"observed":observed,"reason":reason}
        assert ok, f"vector failed: {case}: {out[case]}"
    return out


def run_mutants() -> dict[str, dict[str, object]]:
    results = {}
    for lane,(fact,bad,reason) in CANONICAL_MUTANTS.items():
        counter={"calls":0}
        check=fact_obligation(f"D0::{lane}",fact,bad,reason)
        expensive=sentinel(counter,f"D0::{lane}::EXPENSIVE_SENTINEL")
        outcome=evaluate_containment({fact:bad},(expensive,check))
        rejected=outcome.disposition is Disposition.FAIL
        short_circuit=counter["calls"]==0 and outcome.evaluated==(f"D0::{lane}",)
        results[lane]={
            "rejected":rejected,
            "disposition":outcome.disposition.value,
            "first_fail":outcome.first_fail,
            "evaluated":list(outcome.evaluated),
            "short_circuit":short_circuit,
            "reason":outcome.reason,
        }
        assert rejected and short_circuit, f"unsafe mutant outcome: {lane}: {results[lane]}"
    return results


def main() -> int:
    vectors=run_vectors()
    mutants=run_mutants()
    rejected=sum(1 for x in mutants.values() if x["rejected"])
    result={
        "document_id":"AURA:STAGE06:W6:D0-RESULTS:V1",
        "vector_tests":{"passed":sum(1 for x in vectors.values() if x["pass"]),"total":len(vectors),"details":vectors},
        "d0_mutants":{"rejected":rejected,"total":len(mutants),"rejection_rate":rejected/len(mutants),"details":mutants},
        "gate_b_candidate": rejected==len(mutants) and all(x["pass"] for x in vectors.values()),
    }
    (HERE/'D0_RESULTS.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({"vectors":f"{result['vector_tests']['passed']}/{result['vector_tests']['total']}","d0":f"{rejected}/{len(mutants)}","gate_b_candidate":result['gate_b_candidate']},sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
