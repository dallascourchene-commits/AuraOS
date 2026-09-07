from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "arena"))

from memory_city_coverage_membrane import AdmissionMode, PositiveTrace, compile_coverage_certificate, compile_proof_carrying_typed_admission
from memory_city_read_consequence import ReadWorldBinding, compile_read_consequence_certificate
from memory_city_support_hydration import SupportClosedHydration
from memory_city_typed_closure import REPROOF_SEMANTICS, TypedClosureCertificate, TypedClosureDisposition
from memory_city_effect_handoff_o13 import EffectHandoffEvidence, HandoffDecision, HandoffDisposition, HandoffVerificationContext, MutationBoundaryProjection, compile_effect_handoff, digest


def hx(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def fixtures():
    hydration = SupportClosedHydration(
        status="READY_SUPPORT_CLOSED_HYDRATION_D0", support_cut=("a", "b"), missing_objects=(),
        selected_bytes=20, universe_bytes=100, hydration_fraction=0.2,
        plan_root=hx("plan"), receipt_root=hx("hydr"), support_root=hx("support"),
    )
    closure = TypedClosureCertificate(
        disposition=TypedClosureDisposition.READY, hydration=None, support_root=hydration.support_root,
        influence_root=hx("influence"), reproof_item_ids=("a", "b", "c"), horizon=2,
        transition_model_root=hx("transition"), future_congruence_root=hx("future"),
        receipt_root=hx("typed"), reproof_semantics=REPROOF_SEMANTICS,
    )
    binding = ReadWorldBinding(hydration, closure).binding_root
    program, domain = hx("program"), hx("domain")
    coverage = compile_coverage_certificate(
        program_root=program, sealed_domain_root=domain, generation=7, obligations=(binding,),
        positive=(PositiveTrace(binding, program, domain, 7, hx("trace"), True, True),),
    )
    cert = compile_read_consequence_certificate((ReadWorldBinding(hydration, closure),), coverage)
    admission = compile_proof_carrying_typed_admission(
        typed_closure_receipt_root=closure.receipt_root, coverage=coverage,
        support_root=hydration.support_root, influence_root=closure.influence_root,
        transition_model_root=closure.transition_model_root,
        future_congruence_root=closure.future_congruence_root, horizon=closure.horizon,
        mode=AdmissionMode.EFFECT_BOUND,
    )
    evidence = EffectHandoffEvidence(hx("owner"), hx("verifier"))
    mutation = MutationBoundaryProjection("cell", 4, hx("cfg"), 8, 17, 17, "worker", 100, hx("ta"), hx("rf"))
    verification = HandoffVerificationContext("cell", 4, hx("cfg"), 8, 17, 17, "worker", 100, hx("owner"), hx("verifier"), hx("ta"), hx("rf"), 50)
    kwargs = dict(
        hydration=hydration, typed_closure=closure, fixed_support_root=hydration.support_root,
        coverage=coverage, current_program_root=program, current_sealed_domain_root=domain,
        current_coverage_generation=7, admission=admission, evidence=evidence,
        mutation=mutation, verification=verification,
    )
    return cert, kwargs


def scenario(index: int):
    cert, kwargs = fixtures()
    mode = index % 8
    expected_disposition = HandoffDisposition.HOLD_TECC_REQUIRED_D0
    expected_reason = "EXACT_CURRENT_OWNER_CROSS_BINDING_REQUIRES_INDEPENDENT_TECC"
    if mode == 1:
        kwargs["typed_closure"] = replace(kwargs["typed_closure"], reproof_semantics="")
        expected_disposition = HandoffDisposition.HOLD
        expected_reason = "READ_OWNER_AT_T1_HOLD_REPROOF_SEMANTICS"
    elif mode == 2:
        kwargs["typed_closure"] = replace(kwargs["typed_closure"], receipt_root=hx(f"moved-{index}"))
        expected_disposition = HandoffDisposition.HOLD
        expected_reason = "READ_OWNER_AT_T1_HOLD_ACTIVE_WORLD_MEMBERSHIP"
    elif mode == 3:
        kwargs["mutation"] = replace(kwargs["mutation"], holder=f"other-{index}")
        expected_disposition = HandoffDisposition.REBIND_REQUIRED
        expected_reason = "LEASE_IDENTITY_MOVED"
    elif mode == 4:
        kwargs["mutation"] = replace(kwargs["mutation"], expires_at=101 + (index % 17))
        expected_disposition = HandoffDisposition.REBIND_REQUIRED
        expected_reason = "LEASE_IDENTITY_MOVED"
    elif mode == 5:
        altered = dict(kwargs["admission"])
        altered["schema"] = "UNKNOWN-ADMISSION"
        kwargs["admission"] = altered
        expected_disposition = HandoffDisposition.HOLD
        expected_reason = "ADMISSION_NOT_EXACT_CURRENT_OWNER_OUTPUT"
    elif mode == 6:
        cert = replace(cert, effect_authority=True)
        expected_disposition = HandoffDisposition.HOLD
        expected_reason = "READ_CERTIFICATE_AUTHORITY_ESCALATION"
    elif mode == 7:
        cert = replace(cert, consequence_root=hx(f"forged-{index}"))
        expected_disposition = HandoffDisposition.HOLD
        expected_reason = "READ_CERTIFICATE_CONSEQUENCE_ROOT_FORGED"
    return cert, kwargs, expected_disposition, expected_reason, mode


def oracle_matches(decision, expected_disposition: HandoffDisposition, expected_reason: str) -> bool:
    """Require the exact recovery/hold class and exact semantic reason, not merely non-effect."""
    return decision.disposition is expected_disposition and decision.reason == expected_reason


def oracle_self_test() -> bool:
    """Prove the campaign oracle detects the historical blind spot: HOLD substituted for REBIND."""
    wrong = HandoffDecision(HandoffDisposition.HOLD, "LEASE_IDENTITY_MOVED")
    return not oracle_matches(wrong, HandoffDisposition.REBIND_REQUIRED, "LEASE_IDENTITY_MOVED")


def run(cases: int = 24000) -> dict:
    false_tecc_route = 0
    false_hold = 0
    disposition_mismatches = 0
    reason_mismatches = 0
    oracle_mismatches = 0
    tecc_routes = 0
    effect_ready = 0
    by_mode = {
        str(i): {
            "cases": 0,
            "tecc": 0,
            "hold": 0,
            "rebind": 0,
            "disposition_mismatches": 0,
            "reason_mismatches": 0,
            "oracle_mismatches": 0,
        }
        for i in range(8)
    }
    samples = []
    for index in range(cases):
        cert, kwargs, expected_disposition, expected_reason, mode = scenario(index)
        decision = compile_effect_handoff(cert, **kwargs)
        row = by_mode[str(mode)]
        row["cases"] += 1
        if decision.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0:
            row["tecc"] += 1
            tecc_routes += 1
        elif decision.disposition is HandoffDisposition.REBIND_REQUIRED:
            row["rebind"] += 1
        else:
            row["hold"] += 1

        disposition_ok = decision.disposition is expected_disposition
        reason_ok = decision.reason == expected_reason
        if not disposition_ok:
            disposition_mismatches += 1
            row["disposition_mismatches"] += 1
        if not reason_ok:
            reason_mismatches += 1
            row["reason_mismatches"] += 1
        if not (disposition_ok and reason_ok):
            oracle_mismatches += 1
            row["oracle_mismatches"] += 1

        # Preserve the original coarse safety counters for historical comparability.
        if decision.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0 and expected_disposition is not HandoffDisposition.HOLD_TECC_REQUIRED_D0:
            false_tecc_route += 1
        if decision.disposition is not HandoffDisposition.HOLD_TECC_REQUIRED_D0 and expected_disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0:
            false_hold += 1
        if decision.effect_authority:
            effect_ready += 1
        if len(samples) < 16:
            samples.append({
                "mode": mode,
                "expected_disposition": expected_disposition.value,
                "expected_reason": expected_reason,
                "observed_disposition": decision.disposition.value,
                "observed_reason": decision.reason,
            })
    payload = {
        "schema": "AURA-MEMORY-CITY-O13-EFFECT-HANDOFF-CAMPAIGN-v2-EXACT-ORACLE",
        "cases": cases,
        "tecc_routes": tecc_routes,
        "false_tecc_route": false_tecc_route,
        "false_hold": false_hold,
        "disposition_mismatches": disposition_mismatches,
        "reason_mismatches": reason_mismatches,
        "oracle_mismatches": oracle_mismatches,
        "oracle_self_test_pass": oracle_self_test(),
        "effect_ready": effect_ready,
        "by_mode": by_mode,
        "samples": samples,
    }
    payload["campaign_root"] = digest(payload)
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
