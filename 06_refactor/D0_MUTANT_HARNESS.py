#!/usr/bin/env python3
"""D0 five-lane mutant harness for the Stage 06 AuraOS minimal candidate."""

from __future__ import annotations

import json
from aura_os_minimal import (
    CausalFence,
    Disposition,
    IngressPacket,
    PassReceipt,
    ResidualBuffer,
    TriProposalBundle,
    p_fence,
    p_residual,
    p_router,
)


def base_packet():
    return IngressPacket(frozenset({"obl:1"}))


def base_bundle():
    return TriProposalBundle(
        g_r={"candidate": "minimal"},
        g_f={"candidate": "falsifier"},
        g_c={"candidate": "risk"},
    )


def base_residual():
    return ResidualBuffer(obligations={"obl:1"})


def route(**overrides):
    args = dict(
        packet=base_packet(),
        bundle=base_bundle(),
        residual=base_residual(),
        runtime_phase="ACTIVE",
        authority_voice="HUMAN_GATED",
        authority_verified=True,
        admitted_class="PATCH",
        stem="VERIFY",
        joint_dependency_complete=True,
        independent_defeat_path=True,
    )
    args.update(overrides)
    return p_router(**args)


def run():
    rows = []

    def record(name, disposition, reason):
        rejected = disposition is not Disposition.PASS
        rows.append(
            {
                "lane": name,
                "disposition": disposition.value,
                "reason": reason,
                "rejected": rejected,
                "unsafe_pass": not rejected,
            }
        )

    r = route(joint_dependency_complete=False)
    record("JOINT_MARGINAL_MUTANT", r.check.disposition, r.check.reason)

    buf = ResidualBuffer(obligations={"obl:1"}, pass_receipts={"missing"})
    rr = p_residual(buf, {}, required_generation="G7")
    record("OMISSION_MUTANT", rr.check.disposition, rr.check.reason)
    assert "obl:1" in rr.residual_obligations

    r = route(independent_defeat_path=False)
    record("RECURSIVE_SAME_BLINDSPOT", r.check.disposition, r.check.reason)

    r = route(authority_verified=False)
    record("SELF_CERTIFIED_KNOWN_ONLY", r.check.disposition, r.check.reason)

    stale = PassReceipt("r1", "obl:1", "G6", True)
    buf = ResidualBuffer(obligations={"obl:1"}, pass_receipts={"r1"})
    rr = p_residual(buf, {"r1": stale}, required_generation="G7")
    record("STALE_GENERATION_MUTANT", rr.check.disposition, rr.check.reason)
    assert "obl:1" in rr.residual_obligations

    good_route = route()
    good_fence = p_fence(CausalFence(10.0, 20.0, True), timing_evidence_verified=True)
    good_receipt = PassReceipt("r2", "obl:1", "G7", True)
    good_residual = p_residual(
        ResidualBuffer(obligations={"obl:1"}, pass_receipts={"r2"}),
        {"r2": good_receipt},
        required_generation="G7",
    )

    assert good_route.check.disposition is Disposition.PASS
    assert len(good_route.slots) == 6
    assert good_fence.disposition is Disposition.PASS
    assert good_residual.check.disposition is Disposition.PASS
    assert not good_residual.residual_obligations

    rejected = sum(row["rejected"] for row in rows)
    unsafe = sum(row["unsafe_pass"] for row in rows)
    summary = {
        "mutants": len(rows),
        "rejected": rejected,
        "rejection_rate_percent": 100.0 * rejected / len(rows),
        "unsafe_passes": unsafe,
        "positive_controls": {
            "router": good_route.check.disposition.value,
            "fence": good_fence.disposition.value,
            "residual": good_residual.check.disposition.value,
        },
        "rows": rows,
        "status": "PASS" if rejected == len(rows) and unsafe == 0 else "FAIL",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    result = run()
    raise SystemExit(0 if result["status"] == "PASS" else 1)
