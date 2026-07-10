"""
Aura Civic Cost Integration — connects civic stages to the Empirical Cost Observatory.

Records civic stage costs: intent/profile, source retrieval, contribution normalization,
MITOSIS, resource matching, MUSIC, legal evidence, map preparation, deliberation,
What-If, pilot, decision packet, verification.

Reports: measured or labelled usage, latency, cost, verification status, quality status,
and cost_per_verified_success.

Fixture mode reports zero provider cost without fake provider usage.
"""
from __future__ import annotations
import time, json
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

CIVIC_STAGES = (
    "intent_profile", "source_retrieval", "contribution_normalization",
    "mitosis", "resource_matching", "music", "legal_evidence",
    "map_preparation", "deliberation", "what_if", "pilot",
    "decision_packet", "verification",
)


def record_civic_stage(
    stage: str,
    *,
    session_id: str = "",
    organ_type: str = "",
    latency_ms: float = 0.0,
    usage: dict[str, int] | None = None,
    cost_usd: float = 0.0,
    verification_status: str = "verified",
    quality_status: str = "pass",
    fixture_mode: bool = True,
) -> dict[str, Any]:
    """Record a civic stage cost through the Empirical Cost Observatory."""
    if stage not in CIVIC_STAGES:
        return {"ok": False, "error": f"unknown_civic_stage: {stage}",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

    # In fixture mode, usage is zero and cost is zero — don't fake provider usage
    if fixture_mode:
        usage = usage or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        cost_usd = 0.0
    else:
        usage = usage or {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    # Calculate cost_per_verified_success
    if verification_status == "verified":
        cost_per_verified = cost_usd if cost_usd > 0 else 0.0
    else:
        cost_per_verified = float('inf') if cost_usd > 0 else 0.0

    record = {
        "stage": stage,
        "session_id": session_id,
        "organ_type": organ_type,
        "latency_ms": latency_ms,
        "usage": usage,
        "cost_usd": cost_usd,
        "measurement_class": "MEASURED" if not fixture_mode else "FIXTURE_ZERO",
        "verification_status": verification_status,
        "quality_status": quality_status,
        "cost_per_verified_success": cost_per_verified,
        "timestamp": time.time(),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

    # Try to record through the Empirical Cost Observatory
    try:
        from aura_empirical_cost_ledger import EmpiricalCostLedger
        ledger = EmpiricalCostLedger(repo_root=".")
        ledger.record_run(
            run_id=f"civic_{stage}_{session_id}_{int(time.time())}",
            provider="fixture" if fixture_mode else "unknown",
            model="fixture" if fixture_mode else "unknown",
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cached_input_tokens=0,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            measurement_class=record["measurement_class"],
            stage=f"civic_{stage}",
            verification_status=verification_status,
        )
    except Exception:
        pass  # Cost ledger is optional — record is still returned

    return {"ok": True, "record": record,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def get_civic_cost_summary(session_id: str) -> dict[str, Any]:
    """Get cost summary for all civic stages in a session."""
    # This would query the cost ledger in production
    return {
        "ok": True,
        "session_id": session_id,
        "stages": list(CIVIC_STAGES),
        "total_cost_usd": 0.0,  # fixture mode
        "total_verified_successes": 0,
        "cost_per_verified_success": 0.0,
        "measurement_class": "FIXTURE_ZERO",
        "note": "Fixture mode: zero provider cost. No fake provider usage reported.",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
