"""
Aura Usage Normalizer — normalize provider-specific usage responses into a common schema.

Supports OpenAI-compatible, Anthropic, Gemini, Mistral, Groq, OpenRouter, Fireworks,
and local model usage formats. Unknown values remain None, never become zero.

Measurement classes:
  MEASURED          — provider reported exact usage
  TOKENIZER_EXACT   — local tokenizer counted exact tokens
  DERIVED           — derived from known fields (e.g., total = input + output)
  ESTIMATED         — chars/4 fallback
  UNAVAILABLE       — no usage data at all

Dependencies: stdlib only.
"""
from __future__ import annotations

from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
NORMALIZER_VERSION = "AURA_USAGE_NORMALIZER_V1"

# Measurement class hierarchy
MEASURED = "MEASURED"
TOKENIZER_EXACT = "TOKENIZER_EXACT"
DERIVED = "DERIVED"
ESTIMATED = "ESTIMATED"
UNAVAILABLE = "UNAVAILABLE"


def _safe_int(value: Any) -> int | None:
    """Convert to int or None. Never returns 0 for missing data."""
    if value is None:
        return None
    try:
        n = int(value)
        return n
    except (ValueError, TypeError):
        return None


def normalize_openai_usage(usage: dict[str, Any], provider: str = "openai") -> dict[str, Any]:
    """Normalize OpenAI-compatible usage (also Fireworks, Groq, OpenRouter, Mistral)."""
    fields_present = []
    warnings = []

    input_tokens = _safe_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
    output_tokens = _safe_int(usage.get("completion_tokens") or usage.get("output_tokens"))
    total_tokens = _safe_int(usage.get("total_tokens"))
    cached_input = _safe_int(usage.get("prompt_tokens_details", {}).get("cached_tokens")) if isinstance(usage.get("prompt_tokens_details"), dict) else None
    reasoning_tokens = _safe_int(usage.get("completion_tokens_details", {}).get("reasoning_tokens")) if isinstance(usage.get("completion_tokens_details"), dict) else None

    if input_tokens is not None:
        fields_present.append("input_tokens")
    if output_tokens is not None:
        fields_present.append("output_tokens")
    if total_tokens is not None:
        fields_present.append("total_tokens")
    if cached_input is not None:
        fields_present.append("cached_input_tokens")
    if reasoning_tokens is not None:
        fields_present.append("reasoning_tokens")

    # Derive total if missing but input+output available
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
        warnings.append("total_tokens derived from input+output")

    measurement_class = MEASURED if (input_tokens is not None or output_tokens is not None) else UNAVAILABLE
    if measurement_class == UNAVAILABLE:
        warnings.append("No usage fields found in response")

    return {
        "provider": provider,
        "model": None,  # Set by caller
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_input_tokens": cached_input,
        "cache_creation_tokens": None,
        "reasoning_tokens": reasoning_tokens,
        "tool_input_tokens": None,
        "tool_output_tokens": None,
        "provider_reported_cost_usd": None,  # Set by caller if available
        "measurement_class": measurement_class,
        "raw_usage_fields_present": fields_present,
        "usage_parse_warnings": warnings,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def normalize_anthropic_usage(usage: dict[str, Any]) -> dict[str, Any]:
    """Normalize Anthropic-style usage."""
    fields_present = []
    warnings = []

    input_tokens = _safe_int(usage.get("input_tokens"))
    output_tokens = _safe_int(usage.get("output_tokens"))
    cache_creation = _safe_int(usage.get("cache_creation_input_tokens"))
    cache_read = _safe_int(usage.get("cache_read_input_tokens"))

    if input_tokens is not None:
        fields_present.append("input_tokens")
    if output_tokens is not None:
        fields_present.append("output_tokens")
    if cache_creation is not None:
        fields_present.append("cache_creation_tokens")
    if cache_read is not None:
        fields_present.append("cached_input_tokens")

    total = None
    if input_tokens is not None and output_tokens is not None:
        total = input_tokens + output_tokens
        if cache_creation is not None:
            total += cache_creation

    measurement_class = MEASURED if (input_tokens is not None or output_tokens is not None) else UNAVAILABLE

    return {
        "provider": "anthropic",
        "model": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total,
        "cached_input_tokens": cache_read,
        "cache_creation_tokens": cache_creation,
        "reasoning_tokens": None,
        "tool_input_tokens": None,
        "tool_output_tokens": None,
        "provider_reported_cost_usd": None,
        "measurement_class": measurement_class,
        "raw_usage_fields_present": fields_present,
        "usage_parse_warnings": warnings,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def normalize_gemini_usage(usage: dict[str, Any]) -> dict[str, Any]:
    """Normalize Gemini-style usage."""
    fields_present = []
    warnings = []

    md = usage.get("usageMetadata", usage)
    input_tokens = _safe_int(md.get("promptTokenCount") or md.get("prompt_token_count"))
    output_tokens = _safe_int(md.get("candidatesTokenCount") or md.get("completion_token_count") or md.get("output_token_count"))
    total_tokens = _safe_int(md.get("totalTokenCount") or md.get("total_token_count"))
    cached_input = _safe_int(md.get("cachedContentTokenCount"))

    if input_tokens is not None:
        fields_present.append("input_tokens")
    if output_tokens is not None:
        fields_present.append("output_tokens")
    if total_tokens is not None:
        fields_present.append("total_tokens")

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
        warnings.append("total_tokens derived")

    measurement_class = MEASURED if (input_tokens is not None or output_tokens is not None) else UNAVAILABLE

    return {
        "provider": "gemini",
        "model": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cached_input_tokens": cached_input,
        "cache_creation_tokens": None,
        "reasoning_tokens": None,
        "tool_input_tokens": None,
        "tool_output_tokens": None,
        "provider_reported_cost_usd": None,
        "measurement_class": measurement_class,
        "raw_usage_fields_present": fields_present,
        "usage_parse_warnings": warnings,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def normalize_local_usage(usage: dict[str, Any]) -> dict[str, Any]:
    """Normalize local model/runtime usage (may report energy and runtime)."""
    fields_present = []
    warnings = []

    input_tokens = _safe_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
    output_tokens = _safe_int(usage.get("completion_tokens") or usage.get("output_tokens"))
    energy_joules = usage.get("energy_joules")
    runtime_ms = usage.get("runtime_ms")

    if input_tokens is not None:
        fields_present.append("input_tokens")
    if output_tokens is not None:
        fields_present.append("output_tokens")
    if energy_joules is not None:
        fields_present.append("energy_joules")
    if runtime_ms is not None:
        fields_present.append("runtime_ms")

    if input_tokens is None and output_tokens is None:
        warnings.append("Local model reported no token counts")
        measurement_class = UNAVAILABLE
    else:
        measurement_class = MEASURED

    return {
        "provider": "local",
        "model": usage.get("model", "local"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": (input_tokens + output_tokens) if (input_tokens is not None and output_tokens is not None) else None,
        "cached_input_tokens": None,
        "cache_creation_tokens": None,
        "reasoning_tokens": None,
        "tool_input_tokens": None,
        "tool_output_tokens": None,
        "provider_reported_cost_usd": 0.0,  # Local models have zero API cost
        "measurement_class": measurement_class,
        "raw_usage_fields_present": fields_present,
        "usage_parse_warnings": warnings,
        "energy_joules": energy_joules,
        "runtime_ms": runtime_ms,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def normalize_usage(usage: dict[str, Any], provider: str = "openai", model: str | None = None) -> dict[str, Any]:
    """Normalize any provider usage into common schema.

    Auto-detects provider format from usage fields. Unknown values remain None.
    """
    if not usage or not isinstance(usage, dict):
        return {
            "provider": provider, "model": model,
            "input_tokens": None, "output_tokens": None, "total_tokens": None,
            "cached_input_tokens": None, "cache_creation_tokens": None,
            "reasoning_tokens": None, "tool_input_tokens": None, "tool_output_tokens": None,
            "provider_reported_cost_usd": None,
            "measurement_class": UNAVAILABLE,
            "raw_usage_fields_present": [],
            "usage_parse_warnings": ["No usage data provided"],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    # Auto-detect format
    if "input_tokens" in usage or "cache_creation_input_tokens" in usage:
        result = normalize_anthropic_usage(usage)
    elif "usageMetadata" in usage or "promptTokenCount" in usage:
        result = normalize_gemini_usage(usage)
    elif "energy_joules" in usage or provider == "local":
        result = normalize_local_usage(usage)
    else:
        result = normalize_openai_usage(usage, provider)

    # Set model from caller
    if model:
        result["model"] = model

    # Set provider from caller if it was auto-detected wrong
    if provider and provider != result.get("provider"):
        result["provider"] = provider

    return result
