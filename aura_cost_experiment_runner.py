"""
Aura Cost Experiment Runner — controlled paired comparisons.

Supports RAW_AGENT, AURA_CODEMAP_ONLY, AURA_BOUNDED_CONTEXT, AURA_FULL_PIPELINE,
AURA_HERMES, and ablation modes (AURA_WITHOUT_DREAM, etc.).

Modes:
  REPLAY  — use stored provider responses for deterministic tests
  SHADOW  — measure raw baseline without sending a second paid call (COUNTERFACTUAL_ESTIMATE)
  PAIRED_LIVE — run both paths through the same provider (PAIRED_MEASURED, requires approval)

Dependencies: stdlib only.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
RUNNER_VERSION = "AURA_COST_EXPERIMENT_RUNNER_V1"

# Experiment modes
EXPERIMENT_MODES = [
    "RAW_AGENT", "AURA_CODEMAP_ONLY", "AURA_BOUNDED_CONTEXT",
    "AURA_FULL_PIPELINE", "AURA_HERMES",
    "AURA_WITHOUT_DREAM", "AURA_WITHOUT_ST3GG", "AURA_WITHOUT_CONTEXT_CRUSHER",
]

# Measurement modes
REPLAY = "REPLAY"
SHADOW = "SHADOW"
PAIRED_LIVE = "PAIRED_LIVE"

# Savings status
SAVINGS_PROVISIONAL = "SAVINGS_PROVISIONAL"
SAVINGS_VERIFIED = "SAVINGS_VERIFIED"
SAVINGS_INCONCLUSIVE = "SAVINGS_INCONCLUSIVE"
SAVINGS_INVALIDATED_BY_QUALITY = "SAVINGS_INVALIDATED_BY_QUALITY"
NO_COMPARABLE_BASELINE = "NO_COMPARABLE_BASELINE"


def create_comparison_id(objective: str, model: str, commit_sha: str = "") -> str:
    """Create a stable comparison ID for paired runs."""
    return hashlib.blake2b(
        f"{objective}:{model}:{commit_sha}".encode(), digest_size=12
    ).hexdigest()


def validate_comparability(run_a: dict, run_b: dict) -> dict[str, Any]:
    """Validate that two runs are comparable."""
    mismatches = []
    if run_a.get("model") != run_b.get("model"):
        mismatches.append("model_mismatch")
    if run_a.get("repository_commit_sha") and run_b.get("repository_commit_sha"):
        if run_a["repository_commit_sha"] != run_b["repository_commit_sha"]:
            mismatches.append("commit_sha_mismatch")
    if run_a.get("objective_hash") and run_b.get("objective_hash"):
        if run_a["objective_hash"] != run_b["objective_hash"]:
            mismatches.append("objective_mismatch")
    return {
        "ok": len(mismatches) == 0,
        "mismatches": mismatches,
        "comparable": len(mismatches) == 0,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def compute_savings_status(
    aura_cost: float | None,
    raw_cost: float | None,
    aura_verified: bool,
    quality_not_worse: bool = True,
    has_baseline: bool = True,
) -> str:
    """Determine savings status based on cost and quality."""
    if not has_baseline or raw_cost is None or aura_cost is None:
        return NO_COMPARABLE_BASELINE
    if aura_cost < raw_cost and aura_verified and quality_not_worse:
        return SAVINGS_VERIFIED
    if aura_cost < raw_cost and not aura_verified:
        return SAVINGS_INVALIDATED_BY_QUALITY
    if aura_cost < raw_cost and not quality_not_worse:
        return SAVINGS_INVALIDATED_BY_QUALITY
    if aura_cost >= raw_cost:
        return SAVINGS_INCONCLUSIVE
    return SAVINGS_PROVISIONAL


def compute_quality_normalized_metrics(
    aura_run: dict[str, Any],
    raw_run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute quality-normalized economics metrics."""
    aura_cost = aura_run.get("calculated_cost_usd") or aura_run.get("provider_cost_usd") or 0.0
    aura_verified = aura_run.get("verification_status") == "VERIFIED"
    aura_tokens = (aura_run.get("input_tokens") or 0) + (aura_run.get("output_tokens") or 0)

    metrics = {
        "cost_per_verified_success": None,
        "tokens_per_verified_success": None,
        "latency_per_verified_success": None,
        "cost_per_accepted_patch": None,
        "tokens_per_accepted_patch": None,
        "repair_cost": None,
        "human_minutes_per_success": None,
        "context_lines_per_success": None,
        "scope_violations_per_run": aura_run.get("scope_violation_count", 0),
        "savings_status": SAVINGS_PROVISIONAL,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

    if aura_verified:
        metrics["cost_per_verified_success"] = aura_cost
        metrics["tokens_per_verified_success"] = aura_tokens
        metrics["latency_per_verified_success"] = aura_run.get("latency_ms")
        if aura_run.get("patch_id"):
            metrics["cost_per_accepted_patch"] = aura_cost
            metrics["tokens_per_accepted_patch"] = aura_tokens

    repair_count = aura_run.get("repair_attempt_count", 0)
    if repair_count > 0:
        metrics["repair_cost"] = aura_cost * 0.1 * repair_count  # Estimate

    metrics["context_lines_per_success"] = aura_run.get("source_lines_exposed")

    # Compare with raw baseline if available
    if raw_run:
        raw_cost = raw_run.get("calculated_cost_usd") or raw_run.get("provider_cost_usd") or 0.0
        raw_tokens = (raw_run.get("input_tokens") or 0) + (raw_run.get("output_tokens") or 0)

        metrics["raw_cost"] = raw_cost
        metrics["aura_cost"] = aura_cost
        metrics["gross_saving"] = round(max(0, raw_cost - aura_cost), 6)
        metrics["net_saving"] = round(max(0, raw_cost - aura_cost - (metrics["repair_cost"] or 0)), 6)
        metrics["raw_input_tokens"] = raw_run.get("input_tokens")
        metrics["aura_input_tokens"] = aura_run.get("input_tokens")
        metrics["raw_output_tokens"] = raw_run.get("output_tokens")
        metrics["aura_output_tokens"] = aura_run.get("output_tokens")
        metrics["latency_delta"] = (aura_run.get("latency_ms") or 0) - (raw_run.get("latency_ms") or 0)
        metrics["context_exposure_delta"] = (aura_run.get("source_lines_exposed") or 0) - (raw_run.get("source_lines_exposed") or 0)

        metrics["savings_status"] = compute_savings_status(
            aura_cost=aura_cost,
            raw_cost=raw_cost,
            aura_verified=aura_verified,
            quality_not_worse=aura_run.get("quality_score", 1.0) >= (raw_run.get("quality_score", 0.0)),
        )

    return metrics


def run_replay_experiment(
    objective: str,
    model: str,
    fixtures: dict[str, Any],
    mode: str = "AURA_FULL_PIPELINE",
) -> dict[str, Any]:
    """Run a replay experiment using stored provider fixtures."""
    comparison_id = create_comparison_id(objective, model)
    fixture = fixtures.get(mode, fixtures.get("default", {}))

    run = {
        "run_id": hashlib.blake2b(f"{comparison_id}:{mode}:{time.time()}".encode(), digest_size=12).hexdigest(),
        "comparison_id": comparison_id,
        "mode": mode,
        "provider": fixture.get("provider", "replay"),
        "model": model,
        "measurement_class": fixture.get("measurement_class", "MEASURED"),
        "input_tokens": fixture.get("input_tokens"),
        "output_tokens": fixture.get("output_tokens"),
        "calculated_cost_usd": fixture.get("cost_usd"),
        "latency_ms": fixture.get("latency_ms", 100.0),
        "verification_status": fixture.get("verification_status", "VERIFIED"),
        "source_lines_exposed": fixture.get("source_lines_exposed", 120),
        "quality_score": fixture.get("quality_score", 0.9),
        "repair_attempt_count": fixture.get("repair_attempt_count", 0),
        "confidence_class": "REPLAY_FIXTURE",
        "started_at": time.time(),
        "completed_at": time.time() + fixture.get("latency_ms", 100) / 1000,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

    return {
        "ok": True,
        "version": RUNNER_VERSION,
        "run": run,
        "measurement_mode": REPLAY,
        "comparison_id": comparison_id,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def run_shadow_baseline(
    objective: str,
    model: str,
    raw_context_chars: int,
    pricing_result: dict[str, Any],
) -> dict[str, Any]:
    """Run a shadow baseline (counterfactual estimate, no paid call)."""
    comparison_id = create_comparison_id(objective, model)
    estimated_input_tokens = raw_context_chars // 4
    estimated_cost = None
    if pricing_result.get("cost_usd") is not None and pricing_result.get("cost_status") != "COST_UNKNOWN":
        price = pricing_result.get("price_snapshot", {})
        in_price = price.get("input_per_million_usd", 0) if price else 0
        estimated_cost = round(estimated_input_tokens / 1_000_000 * in_price, 6)

    run = {
        "run_id": hashlib.blake2b(f"{comparison_id}:shadow:{time.time()}".encode(), digest_size=12).hexdigest(),
        "comparison_id": comparison_id,
        "mode": "RAW_AGENT",
        "provider": "shadow",
        "model": model,
        "measurement_class": "ESTIMATED",
        "estimated_input_tokens": estimated_input_tokens,
        "input_tokens": None,  # Not measured
        "output_tokens": None,
        "calculated_cost_usd": estimated_cost,
        "latency_ms": None,
        "verification_status": "NOT_RUN",
        "source_lines_exposed": None,
        "confidence_class": "COUNTERFACTUAL_ESTIMATE",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

    return {
        "ok": True,
        "version": RUNNER_VERSION,
        "run": run,
        "measurement_mode": SHADOW,
        "comparison_id": comparison_id,
        "note": "Shadow baseline is a counterfactual estimate. No paid provider call was made.",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def comparison_report(aura_run: dict, raw_run: dict) -> dict[str, Any]:
    """Generate a paired comparison report."""
    comparability = validate_comparability(aura_run, raw_run)
    if not comparability["comparable"]:
        return {
            "ok": False,
            "error": "Runs are not comparable",
            "mismatches": comparability["mismatches"],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    metrics = compute_quality_normalized_metrics(aura_run, raw_run)
    return {
        "ok": True,
        "version": RUNNER_VERSION,
        "comparison_id": aura_run.get("comparison_id"),
        "metrics": metrics,
        "raw_run": {k: v for k, v in raw_run.items() if k in (
            "run_id", "mode", "provider", "model", "input_tokens", "output_tokens",
            "calculated_cost_usd", "latency_ms", "verification_status", "measurement_class"
        )},
        "aura_run": {k: v for k, v in aura_run.items() if k in (
            "run_id", "mode", "provider", "model", "input_tokens", "output_tokens",
            "calculated_cost_usd", "latency_ms", "verification_status", "measurement_class",
            "repair_attempt_count", "quality_score"
        )},
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
