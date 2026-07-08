"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa11-[Q-SYS:AURA_EFFICIENCY_BENCH_METRICS]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGI'IN (Honest Efficiency Accounting)
DEPENDENCIES: __future__, dataclasses, re, typing, aura_token_economics
FUNCTIONS: BenchmarkResult, estimate_text_tokens, compute_cost, score_quality, compute_savings
SYNOPSIS: Token, cost, savings, and quality metrics for Aura efficiency benchmark runs.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import re
from typing import Any

from aura_efficiency_tasks import BenchmarkTask

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|[^\sA-Za-z0-9_]", re.ASCII)


@dataclass
class BenchmarkResult:
    run_id: str
    task_id: str
    mode: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    baseline_input_tokens: int
    baseline_output_tokens: int
    tokens_saved: int
    tokens_saved_pct: float
    cost_usd: float
    baseline_cost_usd: float
    cost_saved_usd: float
    cost_saved_pct: float
    latency_sec: float
    route: str
    expected_route: str
    route_correct: bool
    verifier_pass: bool
    tests_pass: bool
    output_format_valid: bool
    unsafe_blocked: bool
    quality_score: float
    token_source: str
    metadata: dict[str, object] = field(default_factory=dict)


def estimate_text_tokens(text: str) -> int:
    """Estimate tokens using Aura estimators when importable, with regex fallback."""
    body = text or ""
    if not body:
        return 0
    try:
        from aura_substrate import estimate_tokens as aura_estimate_tokens

        estimated = int(aura_estimate_tokens(body))
        if estimated > 0:
            return estimated
    except Exception:
        pass
    tokens = _TOKEN_RE.findall(body)
    return max(1, len(tokens))


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute provider cost from Aura's economics table when available."""
    normalized = str(model or "").strip().lower()
    if normalized in {"no_model", "local_first", "local_model", "mock", "mock-local"}:
        return 0.0
    if normalized in {"baseline_standard", "cheap_first", "cheap_model"}:
        return round(input_tokens / 1_000_000 * 0.15 + output_tokens / 1_000_000 * 0.60, 8)
    if normalized in {"premium_allowed", "premium_required", "premium_model"}:
        return round(input_tokens / 1_000_000 * 3.00 + output_tokens / 1_000_000 * 15.00, 8)
    try:
        from aura_token_economics import cost_usd

        return float(cost_usd(model, int(input_tokens), int(output_tokens)))
    except Exception:
        price_in, price_out = (3.00, 15.00)
        return round(input_tokens / 1_000_000 * price_in + output_tokens / 1_000_000 * price_out, 8)


def score_quality(result_payload: dict[str, Any], task: BenchmarkTask) -> float:
    """Score benchmark output quality on a deterministic 0..1 rubric."""
    score = 0.0
    score += 0.22 if result_payload.get("output_format_valid") else 0.0
    score += 0.18 if result_payload.get("route_correct") else 0.0
    score += 0.16 if result_payload.get("target_grounding_correct", True) else 0.0
    score += 0.16 if result_payload.get("verifier_pass") else 0.0
    score += 0.12 if result_payload.get("tests_pass") else 0.0

    if task.metadata.get("unsafe_attempt"):
        score += 0.16 if result_payload.get("unsafe_blocked") else 0.0
    elif not result_payload.get("unsafe_blocked_required", False):
        score += 0.08

    if result_payload.get("has_st3gg_metrics"):
        score += 0.04
    if result_payload.get("has_grounding_metadata"):
        score += 0.04

    return round(max(0.0, min(1.0, score)), 4)


def compute_savings(result: BenchmarkResult, baseline: BenchmarkResult) -> BenchmarkResult:
    """Return a copy of result with savings computed versus raw baseline."""
    baseline_total = int(baseline.total_tokens)
    tokens_saved = baseline_total - int(result.total_tokens)
    tokens_saved_pct = round(tokens_saved / max(baseline_total, 1) * 100.0, 4)
    baseline_cost = float(baseline.cost_usd)
    cost_saved = round(baseline_cost - float(result.cost_usd), 8)
    cost_saved_pct = round(cost_saved / max(baseline_cost, 1e-12) * 100.0, 4)
    return replace(
        result,
        baseline_input_tokens=baseline.input_tokens,
        baseline_output_tokens=baseline.output_tokens,
        tokens_saved=tokens_saved,
        tokens_saved_pct=tokens_saved_pct,
        baseline_cost_usd=baseline_cost,
        cost_saved_usd=cost_saved,
        cost_saved_pct=cost_saved_pct,
    )
