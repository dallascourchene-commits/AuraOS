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

from collections.abc import Mapping
import hashlib
import json
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
RUNNER_VERSION = "AURA_COST_EXPERIMENT_RUNNER_V1"

EXPERIMENT_MODES = [
    "RAW_AGENT",
    "AURA_CODEMAP_ONLY",
    "AURA_BOUNDED_CONTEXT",
    "AURA_FULL_PIPELINE",
    "AURA_HERMES",
    "AURA_WITHOUT_DREAM",
    "AURA_WITHOUT_ST3GG",
    "AURA_WITHOUT_CONTEXT_CRUSHER",
]

REPLAY = "REPLAY"
SHADOW = "SHADOW"
PAIRED_LIVE = "PAIRED_LIVE"

SAVINGS_PROVISIONAL = "SAVINGS_PROVISIONAL"
SAVINGS_VERIFIED = "SAVINGS_VERIFIED"
SAVINGS_INCONCLUSIVE = "SAVINGS_INCONCLUSIVE"
SAVINGS_INVALIDATED_BY_QUALITY = "SAVINGS_INVALIDATED_BY_QUALITY"
NO_COMPARABLE_BASELINE = "NO_COMPARABLE_BASELINE"

_PROJECTION_CLASS = "PROJECTED_STRUCTURAL_TOKEN_PROXY"
_ESTIMATED = "ESTIMATED"
_PROJECTION_METHOD = "deterministic_utf8_bytes_divided_by_4_ceiling"


def create_comparison_id(objective: str, model: str, commit_sha: str = "") -> str:
    """Create a stable comparison ID for paired runs."""
    return hashlib.blake2b(
        f"{objective}:{model}:{commit_sha}".encode(), digest_size=12
    ).hexdigest()


def record_structural_context_projection(
    accounting: Mapping[str, Any],
    *,
    repo_root: str = ".",
    objective: str = "",
    task_id: str = "",
    arena_id: str = "human_agent",
    plan_phase_hash: str = "",
    correlation_id: str = "",
    model: str = "AURA_GROUNDED_PHASE_CAPSULE_COMPILER_V1",
) -> dict[str, Any]:
    """Persist a bounded shared-context estimate and repeated-context shadow."""
    from aura_empirical_cost_ledger import EmpiricalCostLedger

    validation = _validate_structural_context_accounting(accounting)
    if not validation["ok"]:
        return _projection_denial(validation["reason"])

    shared_tokens = validation["shared_tokens"]
    repeated_tokens = validation["repeated_tokens"]
    shared_bytes = validation["shared_bytes"]
    repeated_bytes = validation["repeated_bytes"]
    avoided_tokens = repeated_tokens - shared_tokens
    projected_savings_percent = round(
        (avoided_tokens / repeated_tokens) * 100.0, 4
    )
    savings_status = (
        SAVINGS_PROVISIONAL if avoided_tokens > 0 else SAVINGS_INCONCLUSIVE
    )

    objective_hash = hashlib.sha256(
        _canonical_text(objective, "objective", allow_empty=True).encode("utf-8")
    ).hexdigest()
    identity = {
        "model": _canonical_text(model, "model"),
        "objective_hash": objective_hash,
        "task_id": _canonical_text(task_id, "task_id", allow_empty=True),
        "arena_id": _canonical_text(arena_id, "arena_id"),
        "plan_phase_hash": _canonical_text(
            plan_phase_hash, "plan_phase_hash", allow_empty=True
        ),
        "correlation_id": _canonical_text(
            correlation_id, "correlation_id", allow_empty=True
        ),
        "classification": _PROJECTION_CLASS,
        "measurement_class": _ESTIMATED,
        "method": _PROJECTION_METHOD,
        "shared_tokens": shared_tokens,
        "repeated_tokens": repeated_tokens,
        "shared_bytes": shared_bytes,
        "repeated_bytes": repeated_bytes,
    }
    digest = hashlib.sha256(
        json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()[:24]
    comparison_id = f"CMP-GPE-{digest}"
    actual_run_id = f"COST-GPE-{digest}-SHARED"
    shadow_run_id = f"COST-GPE-{digest}-REPEATED"
    now = time.time()
    warnings = [
        "structural_projection_only",
        "provider_usage_unavailable",
        "tokenizer_exact_count_unavailable",
        "quality_not_yet_verified",
        "crucible_requires_verified_arena_experience",
    ]
    field_classes = {
        "estimated_input_tokens": "ESTIMATED",
        "context_bytes_before": "DERIVED",
        "context_bytes_after": "DERIVED",
    }
    common = {
        "comparison_id": comparison_id,
        "task_id": identity["task_id"],
        "arena_id": identity["arena_id"],
        "plan_phase_hash": identity["plan_phase_hash"],
        "objective_hash": objective_hash,
        "provider": "aura-local",
        "model": identity["model"],
        "measurement_class": _ESTIMATED,
        "started_at": now,
        "completed_at": now,
        "model_call_count": 0,
        "tool_call_count": 0,
        "verification_status": "STRUCTURAL_PROJECTION_ONLY",
        "scope_violation_count": 0,
        "repair_attempt_count": 0,
        "human_intervention_count": 0,
        "confidence_class": "COUNTERFACTUAL_ESTIMATE",
        "telemetry_warnings": warnings,
        "field_measurement_classes": field_classes,
        "correlation_id": identity["correlation_id"],
    }
    actual = {
        **common,
        "run_id": actual_run_id,
        "mode": "AURA_SHARED_GROUNDING_EVIDENCE",
        "estimated_input_tokens": shared_tokens,
        "estimated_output_tokens": 0,
        "context_bytes_before": repeated_bytes,
        "context_bytes_after": shared_bytes,
        "cost_status": savings_status,
    }
    shadow = {
        **common,
        "run_id": shadow_run_id,
        "mode": "SHADOW_REPEATED_GROUNDING_EVIDENCE",
        "estimated_input_tokens": repeated_tokens,
        "estimated_output_tokens": 0,
        "context_bytes_before": repeated_bytes,
        "context_bytes_after": repeated_bytes,
        "cost_status": NO_COMPARABLE_BASELINE,
    }

    try:
        ledger = EmpiricalCostLedger(repo_root=repo_root)
        try:
            pair_record = ledger.record_runs((shadow, actual))
            stored_shadow = ledger.get_run(shadow_run_id)
            stored_actual = ledger.get_run(actual_run_id)
        finally:
            ledger.close()
    except Exception as exc:  # noqa: BLE001
        return {
            **_projection_denial(
                f"cost_observatory_unavailable:{type(exc).__name__}"
            ),
            "comparison_id": comparison_id,
        }

    pair_ok = bool(
        pair_record.get("ok")
        and pair_record.get("record_count") == 2
        and stored_shadow is not None
        and stored_actual is not None
        and stored_shadow.get("comparison_id") == comparison_id
        and stored_actual.get("comparison_id") == comparison_id
    )
    return {
        "ok": pair_ok,
        "persistent": pair_ok,
        "comparison_id": comparison_id,
        "actual_run_id": actual_run_id,
        "shadow_run_id": shadow_run_id,
        "measurement_class": _ESTIMATED,
        "classification": _PROJECTION_CLASS,
        "savings_status": savings_status,
        "projected_savings_percent": projected_savings_percent,
        "eligible_for_crucible": False,
        "pair_atomic": True,
        "required_next_evidence": [
            "GOVERNED_ARENA_EXECUTION",
            "VERIFIER_EVIDENCE",
            "OUTCOME_VECTOR",
            "ARENA_EXPERIENCE_V3_RECORD",
        ],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _validate_structural_context_accounting(
    accounting: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(accounting, Mapping):
        return {"ok": False, "reason": "context_cost_accounting_must_be_a_mapping"}
    if accounting.get("classification") != _PROJECTION_CLASS:
        return {"ok": False, "reason": "structural_projection_class_required"}
    if accounting.get("measurement_class") != _ESTIMATED:
        return {"ok": False, "reason": "estimated_measurement_class_required"}
    if accounting.get("method") != _PROJECTION_METHOD:
        return {"ok": False, "reason": "canonical_projection_method_required"}
    if accounting.get("provider_reported") is not False:
        return {"ok": False, "reason": "provider_reported_must_be_false"}
    if accounting.get("tokenizer_exact") is not False:
        return {"ok": False, "reason": "tokenizer_exact_must_be_false"}

    try:
        shared_tokens = _positive_int(
            accounting.get("shared_evidence_total_token_proxy"),
            "shared_evidence_total_token_proxy",
        )
        repeated_tokens = _positive_int(
            accounting.get("repeated_evidence_counterfactual_token_proxy"),
            "repeated_evidence_counterfactual_token_proxy",
        )
        shared_bytes = _positive_int(
            accounting.get("shared_evidence_total_bytes"),
            "shared_evidence_total_bytes",
        )
        repeated_bytes = _positive_int(
            accounting.get("repeated_evidence_counterfactual_bytes"),
            "repeated_evidence_counterfactual_bytes",
        )
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}

    if shared_tokens != (shared_bytes + 3) // 4:
        return {"ok": False, "reason": "shared_token_proxy_mismatch"}
    if repeated_tokens != (repeated_bytes + 3) // 4:
        return {"ok": False, "reason": "repeated_token_proxy_mismatch"}
    if repeated_bytes < shared_bytes or repeated_tokens < shared_tokens:
        return {"ok": False, "reason": "counterfactual_must_not_be_smaller"}

    return {
        "ok": True,
        "shared_tokens": shared_tokens,
        "repeated_tokens": repeated_tokens,
        "shared_bytes": shared_bytes,
        "repeated_bytes": repeated_bytes,
    }


def _projection_denial(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "persistent": False,
        "measurement_class": _ESTIMATED,
        "classification": _PROJECTION_CLASS,
        "eligible_for_crucible": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field}_must_be_a_positive_integer")
    return value


def _canonical_text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ValueError(f"{field}_must_be_canonical_text")
    if not allow_empty and not value:
        raise ValueError(f"{field}_must_be_nonempty")
    return value


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
    return SAVINGS_INCONCLUSIVE


def compute_quality_normalized_metrics(
    aura_run: dict[str, Any],
    raw_run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute quality-normalized economics metrics."""
    aura_cost = (
        aura_run.get("calculated_cost_usd")
        or aura_run.get("provider_cost_usd")
        or 0.0
    )
    aura_verified = aura_run.get("verification_status") == "VERIFIED"
    aura_tokens = (
        (aura_run.get("input_tokens") or 0)
        + (aura_run.get("output_tokens") or 0)
    )

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
        metrics["repair_cost"] = aura_cost * 0.1 * repair_count

    metrics["context_lines_per_success"] = aura_run.get("source_lines_exposed")

    if raw_run:
        raw_cost = (
            raw_run.get("calculated_cost_usd")
            or raw_run.get("provider_cost_usd")
            or 0.0
        )
        metrics["raw_cost"] = raw_cost
        metrics["aura_cost"] = aura_cost
        metrics["gross_saving"] = round(max(0, raw_cost - aura_cost), 6)
        metrics["net_saving"] = round(
            max(0, raw_cost - aura_cost - (metrics["repair_cost"] or 0)), 6
        )
        metrics["raw_input_tokens"] = raw_run.get("input_tokens")
        metrics["aura_input_tokens"] = aura_run.get("input_tokens")
        metrics["raw_output_tokens"] = raw_run.get("output_tokens")
        metrics["aura_output_tokens"] = aura_run.get("output_tokens")
        metrics["latency_delta"] = (
            (aura_run.get("latency_ms") or 0)
            - (raw_run.get("latency_ms") or 0)
        )
        metrics["context_exposure_delta"] = (
            (aura_run.get("source_lines_exposed") or 0)
            - (raw_run.get("source_lines_exposed") or 0)
        )

        aura_quality = aura_run.get("quality_score")
        raw_quality = raw_run.get("quality_score")
        if aura_quality is None or raw_quality is None:
            metrics["savings_status"] = (
                SAVINGS_PROVISIONAL
                if aura_cost < raw_cost
                else SAVINGS_INCONCLUSIVE
            )
        else:
            metrics["savings_status"] = compute_savings_status(
                aura_cost=aura_cost,
                raw_cost=raw_cost,
                aura_verified=aura_verified,
                quality_not_worse=aura_quality >= raw_quality,
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
        "run_id": hashlib.blake2b(
            f"{comparison_id}:{mode}:{time.time()}".encode(),
            digest_size=12,
        ).hexdigest(),
        "comparison_id": comparison_id,
        "mode": mode,
        "provider": fixture.get("provider", "replay"),
        "model": model,
        "measurement_class": fixture.get("measurement_class", "MEASURED"),
        "input_tokens": fixture.get("input_tokens"),
        "output_tokens": fixture.get("output_tokens"),
        "calculated_cost_usd": fixture.get("cost_usd"),
        "latency_ms": fixture.get("latency_ms", 100.0),
        "verification_status": fixture.get(
            "verification_status", "VERIFIED"
        ),
        "source_lines_exposed": fixture.get("source_lines_exposed", 120),
        "quality_score": fixture.get("quality_score", 0.9),
        "repair_attempt_count": fixture.get("repair_attempt_count", 0),
        "confidence_class": "REPLAY_FIXTURE",
        "started_at": time.time(),
        "completed_at": (
            time.time() + fixture.get("latency_ms", 100) / 1000
        ),
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
    if (
        pricing_result.get("cost_usd") is not None
        and pricing_result.get("cost_status") != "COST_UNKNOWN"
    ):
        price = pricing_result.get("price_snapshot", {})
        in_price = price.get("input_per_million_usd", 0) if price else 0
        estimated_cost = round(
            estimated_input_tokens / 1_000_000 * in_price, 6
        )

    run = {
        "run_id": hashlib.blake2b(
            f"{comparison_id}:shadow:{time.time()}".encode(),
            digest_size=12,
        ).hexdigest(),
        "comparison_id": comparison_id,
        "mode": "RAW_AGENT",
        "provider": "shadow",
        "model": model,
        "measurement_class": "ESTIMATED",
        "estimated_input_tokens": estimated_input_tokens,
        "input_tokens": None,
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
        "note": (
            "Shadow baseline is a counterfactual estimate. "
            "No paid provider call was made."
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def comparison_report(
    aura_run: dict,
    raw_run: dict,
) -> dict[str, Any]:
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
        "raw_run": {
            key: value
            for key, value in raw_run.items()
            if key
            in (
                "run_id",
                "mode",
                "provider",
                "model",
                "input_tokens",
                "output_tokens",
                "calculated_cost_usd",
                "latency_ms",
                "verification_status",
                "measurement_class",
            )
        },
        "aura_run": {
            key: value
            for key, value in aura_run.items()
            if key
            in (
                "run_id",
                "mode",
                "provider",
                "model",
                "input_tokens",
                "output_tokens",
                "calculated_cost_usd",
                "latency_ms",
                "verification_status",
                "measurement_class",
                "repair_attempt_count",
                "quality_score",
            )
        },
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
