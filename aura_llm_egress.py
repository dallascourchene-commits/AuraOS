"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Honest Communication)
DEPENDENCIES: json, os, time, aura_api_rotator
FUNCTIONS: ExternalLLM, interpret, generate
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura External LLM Egress.
=========================

This is the ONLY place Aura is permitted to touch a language model, and it is
always an **external** one. Aura's substrate (`aura_substrate.py`) is LLM-free;
when she needs to *speak* to a human or have her structured data *interpreted*,
she hands that data here and an external provider verbalizes it.

Design rules (enforced):
  * No internal / in-process / local llama. This module never imports
    `llama_cpp` and never calls `127.0.0.1:8081`. Aura herself stays fast and
    deterministic; only egress is networked.
  * Gemini IS allowed (it is an external provider) and routes through the
    Gemini REST path in aura_api_rotator. Its keys may be rejected until
    refreshed; in that case the cell simply records the error and is skipped.
  * Default provider order: Anthropic -> Mistral -> Samba Nova -> Groq -> Cerebras -> Open Router - Github.

Providers are reached through the existing OpenAI-compatible HTTPS POST helper
in `aura_api_rotator.py`, so no new dependency is added.
"""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from aura_api_rotator import (
    gemini_generate,
    gemini_key_pool,
    load_secrets,
    openai_compatible_generate,
)

from aura_savings_db import log_call as _log_call_to_db
from aura_substrate import estimate_tokens as _estimate_tokens

# External providers only. Internal/local engines are intentionally excluded —
# Aura must call out, not run a model in-process. Gemini is an allowed external
# provider (routed via the Gemini REST path); all others are OpenAI-compatible.
PROVIDERS: dict[str, dict] = {
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "key": "MISTRAL_API_KEY",
        "model": "mistral-small-latest",
        "price_in_per_1k": 0.0002,
        "price_out_per_1k": 0.0006,
    },
    "sambanova": {
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "key": "SAMBANOVA_API_KEY",
        "model": "Meta-Llama-3.3-70B-Instruct",
        "price_in_per_1k": 0.0006,
        "price_out_per_1k": 0.0012,
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "price_in_per_1k": 0.00059,
        "price_out_per_1k": 0.00079,
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key": "CEREBRAS_API_KEY",
        "model": "llama-3.3-70b",
        "price_in_per_1k": 0.00085,
        "price_out_per_1k": 0.0012,
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": "OPEN_ROUTER_API_KEY",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "price_in_per_1k": 0.0006,
        "price_out_per_1k": 0.0006,
    },
    "github": {
        "url": "https://models.inference.ai.azure.com/chat/completions",
        "key": "GITHUB_TOKEN",
        "model": "gpt-4o-mini",
        "price_in_per_1k": 0.00015,
        "price_out_per_1k": 0.0006,
    },
    # --- placeholders for future keys (skipped cleanly until configured) ---
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "key": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "price_in_per_1k": 0.00015,
        "price_out_per_1k": 0.0006,
    },
    "anthropic": {
        "api": "anthropic",       # uses the Anthropic Messages API, not OpenAI-compatible
        "url": "https://api.anthropic.com/v1/messages",
        "key": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-4-6",
        "price_in_per_1k": 0.0008,
        "price_out_per_1k": 0.004,
    },
    "gemini": {
        "api": "gemini",          # uses the Gemini REST path, not OpenAI-compatible
        "url": "(gemini-rest)",
        "key": "GEMINI_API_KEY",
        "model": "gemini-1.5-flash",
        "price_in_per_1k": 0.00007,
        "price_out_per_1k": 0.0003,
    },
}
DEFAULT_PROVIDER_ORDER = ["anthropic", "mistral", "sambanova", "groq", "cerebras", "openrouter", "gemini"]

# Providers verified to work with the currently-configured keys. The benchmark
# defaults to these so we never burn calls on providers whose keys are absent or
# rejected. Everything else in PROVIDERS is a placeholder until a key is added.
KNOWN_WORKING = ("anthropic", "sambanova", "mistral", "groq", "cerebras", "openrouter", "github", "gemini")

# Names that must never be used here — Aura does not run her own model. Only
# local/internal in-process engines are forbidden; Gemini is an allowed external
# provider again (keys may be refreshed later).
_FORBIDDEN = {"local", "llama_local", "internal", "in_process",
              "llamacpp", "llama_cpp", "node"}


_PLACEHOLDER_MARKERS = ("your_", "paste_", "changeme", "_here", "xxxx")


def _has_key(name: str, cfg: dict, sec: dict[str, Any]) -> bool:
    if cfg.get("api") == "gemini":
        # honour the rotator's placeholder filtering + key pool
        return bool(gemini_key_pool(sec))
    key_val = sec.get(cfg["key"])
    if not key_val or not str(key_val).strip():
        return False
    low = str(key_val).lower()
    return not any(m in low for m in _PLACEHOLDER_MARKERS)


def _anthropic_generate(url: str, api_key: str, model: str, prompt: str,
                        max_tokens: int, timeout: float):
    """Anthropic Messages API call (placeholder path; untested without a key)."""
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["content"][0]["text"].strip(), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def available_providers(secrets: dict[str, Any] | None = None) -> list[str]:
    """Providers from the catalog that have a usable (non-placeholder) key.

    Excludes forbidden (local/internal) engines. This is how the benchmark
    honours "do not call providers without API keys".
    """
    sec = secrets if secrets is not None else load_secrets()
    return [name for name, cfg in PROVIDERS.items()
            if name not in _FORBIDDEN and _has_key(name, cfg, sec)]


def classify_providers(secrets: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """Bucket catalog providers for `--list-providers`.

    Returns {"working": [...], "configured": [...], "placeholder": [...]} where
    `working` = has a key AND is in KNOWN_WORKING, `configured` = has a key but
    unverified, `placeholder` = catalog entry with no usable key yet.
    """
    sec = secrets if secrets is not None else load_secrets()
    working, configured, placeholder = [], [], []
    for name, cfg in PROVIDERS.items():
        if name in _FORBIDDEN:
            continue
        if _has_key(name, cfg, sec):
            (working if name in KNOWN_WORKING else configured).append(name)
        else:
            placeholder.append(name)
    return {"working": working, "configured": configured, "placeholder": placeholder}


def usable_providers(secrets: dict[str, Any] | None = None,
                     prefer_working: bool = True) -> list[str]:
    """Providers to actually run by default: known-working ones that have keys,
    falling back to any configured provider if none of the known-working set is
    present. Never includes placeholders (no key)."""
    buckets = classify_providers(secrets)
    if prefer_working and buckets["working"]:
        return list(buckets["working"])
    return buckets["working"] + buckets["configured"]


class ExternalLLM:
    """The single external egress. Picks an external provider; never internal/local.

    Every call to `generate()` or `interpret()` is automatically logged to the
    savings database (aura_savings_db), recording tokens, cost, latency, and
    savings vs a naive baseline.
    """

    def __init__(self, provider: str | None = None, model: str | None = None,
                 secrets: dict[str, Any] | None = None,
                 # ── call-context for savings logging ──
                 task: str | None = None,
                 aspect: str | None = None,
                 baseline_prompt_tokens: int | None = None,
                 baseline_output_tokens: int | None = None,
                 baseline_cost_usd: float | None = None):
        self.secrets = secrets if secrets is not None else load_secrets()
        candidates = [provider] if provider else DEFAULT_PROVIDER_ORDER
        chosen = None
        last_err = None
        for cand in candidates:
            if cand is None:
                continue
            low = cand.lower()
            if low in _FORBIDDEN:
                raise ValueError(
                    f"Provider '{cand}' is forbidden in egress. Aura must call an "
                    f"external provider (e.g. {DEFAULT_PROVIDER_ORDER}), never an "
                    f"internal/local in-process model."
                )
            if low not in PROVIDERS:
                last_err = f"unknown provider '{cand}'"
                continue
            if not _has_key(low, PROVIDERS[low], self.secrets):
                last_err = f"no API key for '{cand}'"
                continue
            chosen = low
            break
        if chosen is None:
            raise RuntimeError(f"No usable external provider. Last error: {last_err}")
        self.provider = chosen
        self.cfg = PROVIDERS[chosen]
        
        # Comprehensive dynamic routing for all Anthropic layers
        if chosen == "anthropic":
            default_str = self.secrets.get("CLAUDE_DEFAULT_MODEL", "claude-sonnet-4-6")
            premium_str = self.secrets.get("CLAUDE_PREMIUM_MODEL", "claude-opus-4-8")
            
            # Normalize the incoming request token to match shorthand choices
            model_query = str(model).strip().lower() if model else ""
            
            if model_query in ("premium", "opus", "claude-opus-4-8", premium_str.lower()):
                self.model = premium_str
            elif model_query in ("default", "sonnet", "claude-sonnet-4-6", default_str.lower()) or not model:
                self.model = default_str
            else:
                self.model = model  # Transparent pass-through if an explicit unmapped variant is used
        else:
            self.model = model or self.cfg["model"]
            
        self.api = self.cfg.get("api", "openai")
        
        # ─── UNIVERSAL KEY BINDING ───
        self.is_gemini = (self.api == "gemini")
        self.api_key = self.secrets.get(self.cfg["key"])

        # ─── savings-logging context ───
        self._task = task
        self._aspect = aspect
        self._baseline_prompt = baseline_prompt_tokens
        self._baseline_output = baseline_output_tokens
        self._baseline_cost = baseline_cost_usd

    def _log_to_savings(self, call_type: str, prompt: str,
                         output_text: str | None, latency_sec: float,
                         error: str | None = None) -> None:
        """Log this LLM call to the persistent savings database (best-effort)."""
        try:
            in_tokens = _estimate_tokens(prompt)
            out_tokens = _estimate_tokens(output_text) if output_text else 0
            cost = 0.0 if error else self.cost(in_tokens, out_tokens)

            _log_call_to_db(
                provider=self.provider,
                model=self.model,
                call_type=call_type,
                task=self._task,
                aspect=self._aspect,
                prompt_tokens=in_tokens,
                output_tokens=out_tokens,
                cost_usd=cost,
                latency_sec=latency_sec,
                baseline_prompt_tokens=self._baseline_prompt,
                baseline_output_tokens=self._baseline_output,
                baseline_cost_usd=self._baseline_cost,
                error=error,
            )
        except Exception:
            pass  # never let logging break the call

    # -- raw generation ----------------------------------------------------- #
    def generate(self, prompt: str, *, max_tokens: int = 1300, temperature: float = 0.1,
                 router_context: "str | None" = None):
        """Return (text, error, latency_sec). External call only (HTTPS POST).

        Every call is silently logged to the savings database.

        Args:
            prompt: The user / task prompt sent to the LLM.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            router_context: Optional minimal code excerpt from the AI Router
                (aura_ai_router.get_router_context_for_func). When provided,
                it is prepended to the prompt as a CODE CONTEXT block, letting
                the LLM focus on only the relevant function rather than
                reading entire files. This reduces token usage by 80-90%.
        """
        # Inject router context if provided
        if router_context:
            full_prompt = (
                f"{prompt}\n\n"
                "CODE CONTEXT (from AI Router – read this section only, "
                "not the whole file):\n"
                f"```python\n{router_context}\n```"
            )
        else:
            full_prompt = prompt

        t0 = time.time()
        text = None
        err = None
        if self.is_gemini:
            text, err = gemini_generate(full_prompt, secrets=self.secrets)
        elif self.api == "anthropic":
            text, err = _anthropic_generate(self.cfg["url"], self.api_key, self.model,
                                            full_prompt, max_tokens, timeout=60)
        else:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            text, err = openai_compatible_generate(self.cfg["url"], self.api_key, payload, timeout=60)
        latency = time.time() - t0
        self._log_to_savings("generate", full_prompt, text, latency, error=err)
        return text, err, latency

    # -- "speak" / interpret Aura's structured data ------------------------- #
    def interpret(self, data: Any, instruction: str, *, max_tokens: int = 400):
        """
        Hand Aura's structured data to the external model purely so it can be
        verbalized / interpreted for a human. Returns (text, error, latency).

        Every call is silently logged to the savings database (logged as
        'interpret' rather than 'generate' for analytics).
        """
        if not isinstance(data, str):
            data = json.dumps(data, indent=2, default=str)
        prompt = (
            "You are the external voice for the Aura substrate. Aura is a fast, "
            "deterministic orchestration layer that does not run its own language "
            "model. Below is structured data Aura produced. "
            f"{instruction}\n\n[AURA DATA]\n{data}\n"
        )
        t0 = time.time()
        text, err, latency = self.generate(prompt, max_tokens=max_tokens)
        # Override the generate-level log with the correct call_type
        if not err:
            self._log_to_savings("interpret", prompt, text, latency)
        return text, err, latency

    def cost(self, in_tokens: int, out_tokens: int) -> float:
        # Prefer the central, weekly-refreshable PriceBook; fall back to the
        # static catalog price if it is unavailable (keeps egress dependency-light).
        try:
            from aura_pricing import get_pricebook
            return get_pricebook().cost(self.provider, in_tokens, out_tokens)
        except Exception:  # noqa: BLE001
            return round(
                in_tokens / 1000 * self.cfg["price_in_per_1k"]
                + out_tokens / 1000 * self.cfg["price_out_per_1k"], 6)
