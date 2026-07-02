"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c6-[Q-SYS:HARNESS_EVOLVER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Observability Evolution)
DEPENDENCIES: dataclasses, json, pathlib, time, typing, aura_qdkt(optional)
FUNCTIONS: HarnessPrediction, record_harness_prediction, verify_harness_predictions, analyze_transaction_outcome
SYNOPSIS: Evolves coding-agent harnesses using deterministic local prediction ledgers and
optional QDKT observations. This is the ASI-ARCH-Lite Analyst surface.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any

try:
    from aura_qdkt import get_qdkt
except Exception:
    get_qdkt = None  # type: ignore[assignment]


@dataclass
class HarnessPrediction:
    change_id: str
    component: str
    prediction: str
    metric_target: str
    expected_value: float
    baseline_value: float | None = None
    observed_value: float | None = None
    status: str = "pending"


def _ledger_path(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve() / "Aura_Staging" / "harness_predictions.jsonl"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def record_harness_prediction(
    change_id: str,
    component: str,
    prediction: str,
    metric_target: str,
    expected_value: float,
    *,
    repo_root: str | Path,
    baseline_value: float | None = None,
    observed_value: float | None = None,
    status: str = "pending",
) -> HarnessPrediction:
    """Record a harness modification prediction to QDKT when available and always to JSONL."""
    entry = HarnessPrediction(
        change_id=change_id,
        component=component,
        prediction=prediction,
        metric_target=metric_target,
        expected_value=expected_value,
        baseline_value=baseline_value,
        observed_value=observed_value,
        status=status,
    )
    event = {
        "event_class": "harness_evolution_prediction",
        **asdict(entry),
        "recorded_at": time.time(),
    }

    if get_qdkt is not None:
        try:
            qdkt = get_qdkt()
            if qdkt:
                qdkt.observe(
                    "harness_prediction",
                    event,
                    rationale=f"Harness change {change_id} for {component}",
                    concept=f"harness_evolution:{component}",
                    confidence=0.9,
                    subsystem="aura_harness_evolver",
                )
        except Exception as e:
            event["qdkt_observation_failed"] = type(e).__name__

    _append_jsonl(_ledger_path(repo_root), event)
    return entry


def _safe_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _count_test_statuses(test_results: dict[str, Any]) -> tuple[int, int]:
    passed = 0
    failed = 0
    for result in test_results.values():
        status = str(result.get("status", "") if isinstance(result, dict) else result).lower()
        if status in {"passed", "ok", "success"}:
            passed += 1
        elif status in {"failed", "error", "timeout"}:
            failed += 1
    return passed, failed


def analyze_transaction_outcome(transaction: dict[str, Any]) -> dict[str, Any]:
    """Extract ASI-ARCH-Lite Analyst metrics from a Live Architect transaction dict."""
    stage_results = transaction.get("stage_results", []) or []
    patch_quality = transaction.get("patch_quality", {}) or {}
    workspace = transaction.get("workspace", {}) or {}
    verification = transaction.get("verification", {}) or {}
    hotswap_capsule = transaction.get("hotswap_capsule", {}) or {}

    attempts = patch_quality.get("attempts", []) or []
    preflight_rejection_count = 0
    for attempt in attempts:
        if attempt.get("status") in {"preflight_failed", "repair_failed_blocked"}:
            preflight_rejection_count += 1
        preflight = attempt.get("preflight") or {}
        preflight_rejection_count += len(preflight.get("rejections", []) or [])

    test_pass_count, test_fail_count = _count_test_statuses(workspace.get("test_results", {}) or {})
    model_route = transaction.get("model_route", {}) or {}
    cost = transaction.get("cost") or patch_quality.get("cost") or model_route.get("cost")
    tokens = transaction.get("tokens") or patch_quality.get("tokens") or model_route.get("tokens")

    return {
        "patch_staged_count": sum(1 for item in stage_results if item.get("ok") is True),
        "preflight_rejection_count": preflight_rejection_count,
        "repair_success_count": int(patch_quality.get("repair_succeeded", 0) or 0),
        "workspace_ok": _safe_bool(workspace.get("ok")),
        "hotswap_ready": _safe_bool(verification.get("hotswap_ready")) or hotswap_capsule.get("status") == "ready",
        "test_pass_count": test_pass_count,
        "test_fail_count": test_fail_count,
        "cost": cost,
        "tokens": tokens,
        "verifier_failure_count": len(verification.get("failures", []) or []),
    }


def _read_predictions(repo_root: str | Path) -> list[dict[str, Any]]:
    path = _ledger_path(repo_root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            rows.append({"event_class": "harness_evolution_prediction", "status": "inconclusive", "parse_error": True})
            continue
        if row.get("event_class") == "harness_evolution_prediction":
            rows.append(row)
    return rows


def _latest_transaction_metrics(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    candidates = [
        root / "Aura_Staging" / "architect_live_transaction.json",
        root / "Aura_Staging" / "live_architect_transaction.json",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return {}
    latest = max(existing, key=lambda path: path.stat().st_mtime)
    try:
        transaction = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return analyze_transaction_outcome(transaction) if isinstance(transaction, dict) else {}


def _metric_satisfied(metric_name: str, observed: float, expected: float) -> bool:
    lower_is_better = any(token in metric_name.lower() for token in ("fail", "rejection", "cost", "token", "latency"))
    return observed <= expected if lower_is_better else observed >= expected


def verify_harness_predictions(repo_root: str | Path) -> dict[str, Any]:
    """
    Verify pending predictions against local JSONL ledger and transaction artifacts.

    QDKT is optional; the JSONL ledger is the deterministic fallback used in tests.
    """
    predictions = _read_predictions(repo_root)
    metrics = _latest_transaction_metrics(repo_root)
    results: list[dict[str, Any]] = []
    verified = failed = inconclusive = 0

    for row in predictions:
        existing_status = row.get("status")
        if existing_status in {"verified", "failed"}:
            status = existing_status
            if status == "verified":
                verified += 1
            elif status == "failed":
                failed += 1
            results.append({**row, "status": status})
            continue

        observed = row.get("observed_value")
        metric_target = str(row.get("metric_target", ""))
        if observed is None and metric_target in metrics:
            observed = metrics.get(metric_target)

        status = "inconclusive"
        try:
            expected = float(row.get("expected_value"))
            observed_float = float(observed) if observed is not None else None
        except Exception:
            observed_float = None
            expected = 0.0

        if observed_float is not None:
            status = "verified" if _metric_satisfied(metric_target, observed_float, expected) else "failed"

        if status == "verified":
            verified += 1
        elif status == "failed":
            failed += 1
        else:
            inconclusive += 1

        result = {
            "change_id": row.get("change_id"),
            "component": row.get("component"),
            "metric_target": metric_target,
            "expected_value": row.get("expected_value"),
            "observed_value": observed,
            "status": status,
        }
        results.append(result)

    return {
        "checked_count": len(predictions),
        "verified_count": verified,
        "failed_count": failed,
        "inconclusive_count": inconclusive,
        "metrics": metrics,
        "predictions": results,
        "qdkt_available": get_qdkt is not None,
    }
