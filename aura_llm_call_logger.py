"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fb-[Q-SYS:LLM_CALL_LOGGER]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Universal Savings Accounting)
DEPENDENCIES: json, os, re, typing, aura_pricing, aura_savings_db
FUNCTIONS: estimate_tokens, infer_provider_from_url, prompt_from_openai_payload, log_llm_call, log_openai_compatible_call, log_gemini_call
SYNOPSIS: Universal best-effort accounting shim for every external LLM call Aura makes. Unknown baselines are recorded as actual-call baselines so savings stay honest instead of inflated.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
import re
from typing import Any


def estimate_tokens(text: Any) -> int:
    """Small dependency-free token estimate for logging paths."""
    if text is None:
        return 0
    if not isinstance(text, str):
        text = json.dumps(text, default=str)
    if not text:
        return 0
    # Mirrors Aura's rough estimator without importing the heavier substrate.
    return max(1, int(len(text) / 4))


def infer_provider_from_url(url: str | None, *, default: str = "unknown") -> str:
    low = (url or "").lower()
    if "generativelanguage.googleapis.com" in low:
        return "gemini"
    if "anthropic.com" in low:
        return "anthropic"
    if "mistral.ai" in low:
        return "mistral"
    if "sambanova.ai" in low:
        return "sambanova"
    if "groq.com" in low:
        return "groq"
    if "cerebras.ai" in low:
        return "cerebras"
    if "openrouter.ai" in low:
        return "openrouter"
    if "models.inference.ai.azure.com" in low:
        return "github"
    if "api.openai.com" in low:
        return "openai"
    return default


def prompt_from_openai_payload(payload: dict[str, Any]) -> str:
    messages = payload.get("messages") or []
    if isinstance(messages, list):
        parts: list[str] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            else:
                parts.append(json.dumps(content, default=str))
        return "\n".join(parts)
    return json.dumps(payload, default=str)


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    clean = dict(metadata or {})
    for key in list(clean):
        if re.search(r"(api|secret|token|key)", key, re.IGNORECASE):
            clean[key] = "***"
    return clean


def _cost(provider: str, in_tokens: int, out_tokens: int) -> float:
    try:
        from aura_pricing import get_pricebook
        return get_pricebook().cost(provider, in_tokens, out_tokens)
    except Exception:  # noqa: BLE001
        return 0.0


def log_llm_call(
    *,
    provider: str,
    model: str,
    call_type: str,
    prompt_text: str,
    output_text: str | None,
    latency_sec: float,
    error: str | None = None,
    task: str | None = None,
    aspect: str | None = None,
    baseline_prompt_tokens: int | None = None,
    baseline_output_tokens: int | None = None,
    baseline_cost_usd: float | None = None,
    metadata: dict[str, Any] | None = None,
    db_path: str | None = None,
) -> int | None:
    """Append one logical LLM call to the rolling savings DB.

    When Aura does not know a raw/no-Aura baseline, baseline=actual is recorded
    so the dashboard counts the call/spend while savings stay exactly zero.
    """
    prompt_tokens = estimate_tokens(prompt_text)
    output_tokens = estimate_tokens(output_text) if output_text else 0
    cost_usd = 0.0 if error else _cost(provider, prompt_tokens, output_tokens)
    baseline_source = "provided"

    if baseline_prompt_tokens is None:
        baseline_prompt_tokens = prompt_tokens
        baseline_source = "actual_call_zero_savings"
    if baseline_output_tokens is None:
        baseline_output_tokens = output_tokens
    if baseline_cost_usd is None:
        baseline_cost_usd = 0.0 if error else _cost(
            provider,
            baseline_prompt_tokens,
            baseline_output_tokens,
        )

    meta = _safe_metadata(metadata)
    meta.setdefault("baseline_source", baseline_source)
    meta.setdefault("logical_call_logged", True)

    try:
        from aura_savings_db import SavingsDB, log_call
        kwargs = {
            "provider": provider or "unknown",
            "model": model or "unknown",
            "call_type": call_type,
            "task": task,
            "aspect": aspect,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "latency_sec": latency_sec,
            "baseline_prompt_tokens": baseline_prompt_tokens,
            "baseline_output_tokens": baseline_output_tokens,
            "baseline_cost_usd": baseline_cost_usd,
            "error": error,
            "metadata": meta,
        }
        if db_path:
            return SavingsDB(db_path).log_call(**kwargs)
        return log_call(**kwargs)
    except Exception:
        return None


def log_openai_compatible_call(
    *,
    url: str,
    payload: dict[str, Any],
    output_text: str | None,
    error: str | None,
    latency_sec: float,
    provider: str | None = None,
    call_type: str = "generate",
    task: str | None = None,
    aspect: str | None = None,
    baseline_prompt_tokens: int | None = None,
    baseline_output_tokens: int | None = None,
    baseline_cost_usd: float | None = None,
    metadata: dict[str, Any] | None = None,
    db_path: str | None = None,
) -> int | None:
    return log_llm_call(
        provider=provider or infer_provider_from_url(url),
        model=str(payload.get("model") or "unknown"),
        call_type=call_type,
        prompt_text=prompt_from_openai_payload(payload),
        output_text=output_text,
        latency_sec=latency_sec,
        error=error,
        task=task,
        aspect=aspect,
        baseline_prompt_tokens=baseline_prompt_tokens,
        baseline_output_tokens=baseline_output_tokens,
        baseline_cost_usd=baseline_cost_usd,
        metadata={"url_provider": infer_provider_from_url(url), **(metadata or {})},
        db_path=db_path,
    )


def log_gemini_call(
    *,
    prompt_text: str,
    output_text: str | None,
    error: str | None,
    latency_sec: float,
    model: str,
    call_type: str = "generate",
    task: str | None = None,
    aspect: str | None = None,
    baseline_prompt_tokens: int | None = None,
    baseline_output_tokens: int | None = None,
    baseline_cost_usd: float | None = None,
    metadata: dict[str, Any] | None = None,
    db_path: str | None = None,
) -> int | None:
    return log_llm_call(
        provider="gemini",
        model=model,
        call_type=call_type,
        prompt_text=prompt_text,
        output_text=output_text,
        latency_sec=latency_sec,
        error=error,
        task=task,
        aspect=aspect,
        baseline_prompt_tokens=baseline_prompt_tokens,
        baseline_output_tokens=baseline_output_tokens,
        baseline_cost_usd=baseline_cost_usd,
        metadata=metadata,
        db_path=db_path,
    )
