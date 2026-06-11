"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c1-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: MINWAAJIMO (Respectful Transmission)
DEPENDENCIES: __future__, json, os, time, urllib.request, urllib.error, aura_api_rotator
FUNCTIONS: AnthropicRouter, _anthropic_call, _sambanova_call, _openai_compat_call
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Anthropic-first cloud router with dynamic failover matrix.
===========================================================

Priority matrix (boot-time default):
    1. Mistral       — codestral 25.08
    2. Anthropic     — claude-sonnet-4-6 (default) / claude-opus-4-8 (premium)
    3. SambaNova     — quota-limit (429) intercepted, context preserve
    4. Groq
    5. Gemini

Models and pricing are read dynamically from ~/aura_secrets.json at call time.
No API strings are hardcoded in this file.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from aura_api_rotator import (
    gemini_generate,
    gemini_key_pool,
    get_gemini_rotator,
    load_secrets,
)

# ---------------------------------------------------------------------------
# Model constants (keys, not strings exposed to users)
# ---------------------------------------------------------------------------
CLAUDE_DEFAULT_MODEL_KEY = "CLAUDE_DEFAULT_MODEL"
CLAUDE_PREMIUM_MODEL_KEY = "CLAUDE_PREMIUM_MODEL"

_CLAUDE_DEFAULT_FALLBACK = "claude-sonnet-4-6"
_CLAUDE_PREMIUM_FALLBACK = "claude-opus-4-8"

ANTHROPIC_API_VERSION = "2023-06-01"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"

# SambaNova quota limit HTTP codes that should trigger immediate failover
_SAMBANOVA_QUOTA_CODES = {429, 503}

# Pricing per million tokens (input / output)
_PRICING: dict[str, tuple[float, float]] = {
    _CLAUDE_DEFAULT_FALLBACK: (3.00, 15.00),
    _CLAUDE_PREMIUM_FALLBACK: (5.00, 25.00),
    "Meta-Llama-3.3-70B-Instruct": (0.60, 1.20),
    "llama-3.3-70b-versatile": (0.59, 0.79),
}


# ---------------------------------------------------------------------------
# Low-level call helpers (no API strings stored here — all from secrets)
# ---------------------------------------------------------------------------

def _anthropic_call(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int = 1300,
    timeout: float = 60.0,
) -> tuple[str | None, str | None, float]:
    """Direct Anthropic Messages API call. Returns (text, error, latency_sec)."""
    t0 = time.time()
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
    }
    req = urllib.request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("content", [{}])[0].get("text", "").strip()
        return text or None, None, time.time() - t0
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}: {exc.reason}", time.time() - t0
    except Exception as exc:  # noqa: BLE001
        return None, str(exc), time.time() - t0


def _sambanova_call(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int = 1300,
    timeout: float = 60.0,
) -> tuple[str | None, str | None, float, bool]:
    """SambaNova call. Returns (text, error, latency_sec, quota_hit)."""
    t0 = time.time()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.15,
    }
    headers = {
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    url = "https://api.sambanova.ai/v1/chat/completions"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        return text or None, None, time.time() - t0, False
    except urllib.error.HTTPError as exc:
        quota_hit = exc.code in _SAMBANOVA_QUOTA_CODES
        return None, f"HTTP {exc.code}: {exc.reason}", time.time() - t0, quota_hit
    except Exception as exc:  # noqa: BLE001
        return None, str(exc), time.time() - t0, False


def _openai_compat_call(
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int = 1300,
    timeout: float = 60.0,
) -> tuple[str | None, str | None, float]:
    """Generic OpenAI-compatible call. Returns (text, error, latency_sec)."""
    t0 = time.time()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.15,
    }
    headers = {
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        return text or None, None, time.time() - t0
    except Exception as exc:  # noqa: BLE001
        return None, str(exc), time.time() - t0


# ---------------------------------------------------------------------------
# AnthropicRouter
# ---------------------------------------------------------------------------

class AnthropicRouter:
    """
    Anthropic-first cloud routing layer with dynamic failover.

    The router reads ALL credentials and model overrides from ~/aura_secrets.json
    at call time — nothing is cached beyond one call boundary to ensure key
    rotation takes effect immediately.

    Failover order:
        Anthropic → SambaNova → Mistral → Groq → Gemini

    SambaNova quota limits (HTTP 429 / 503) are intercepted and trigger instant
    transfer to Mistral without surfacing the error to the user.
    """

FAILOVER_ORDER = ["mistral", "anthropic", "sambanova", "groq", "cerebras", "openrouter", "gemini"]

    # OpenAI-compat endpoints and key names (populated at call time from secrets)
    _PROVIDER_META: dict[str, dict] = {
        "mistral": {
            "url": "https://api.mistral.ai/v1/chat/completions",
            "key_name": "MISTRAL_API_KEY",
            "model_name": "mistral-small-latest",
        },
        "groq": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "key_name": "GROQ_API_KEY",
            "model_name": "llama-3.3-70b-versatile",
        },
        "cerebras": {
            "url": "https://api.cerebras.ai/v1/chat/completions",
            "key_name": "CEREBRAS_API_KEY",
            "model_name": "llama3.1-8b",
        },
        "openrouter": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "key_name": "OPEN_ROUTER_API_KEY",
            "model_name": "meta-llama/llama-3.3-70b-instruct",
        },
    }

    def __init__(self, use_premium: bool = False) -> None:
        self.use_premium = use_premium

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        *,
        context: str | None = None,
        use_premium: bool | None = None,
        max_tokens: int = 1300,
        timeout: float = 60.0,
    ) -> tuple[str | None, str | None, float, str]:
        """
        Route the prompt through the failover matrix.

        Parameters
        ----------
        prompt      : The user / system prompt.
        context     : Optional compact conversational context to prepend (for
                      continuity after a failover). Injected at the start of
                      the prompt if provided.
        use_premium : Override instance-level premium flag for this call.
        max_tokens  : Maximum output tokens.
        timeout     : Per-provider timeout in seconds.

        Returns
        -------
        (text, error, latency_sec, provider_used)
        """
        secrets = load_secrets()
        premium = use_premium if use_premium is not None else self.use_premium
        full_prompt = f"[CONTEXT]\n{context}\n\n{prompt}" if context else prompt

        tried: list[str] = []
        for provider in self.FAILOVER_ORDER:
            result = self._try_provider(
                provider, full_prompt, secrets, premium, max_tokens, timeout
            )
            if result is None:
                tried.append(f"{provider}:no_key")
                continue
            text, err, lat, quota_hit = result

            if text:
                if tried:
                    print(f"[~] AnthropicRouter: fell back past {tried} → {provider}")
                return text, None, lat, provider

            reason = "quota_limit" if quota_hit else (err or "empty")
            tried.append(f"{provider}:{reason}")
            print(f"[!] AnthropicRouter: {provider} failed ({reason}), trying next…")

        total_lat = sum(
            float(t.split(":")[1]) if ":" in t else 0.0 for t in tried
        )
        return (
            None,
            f"All providers exhausted: {tried}",
            total_lat,
            "none",
        )

    def cost_usd(self, model: str, in_tokens: int, out_tokens: int) -> float:
        """Return the estimated USD cost for a call given the active model."""
        price_in, price_out = _PRICING.get(model, (0.003, 0.015))
        return round(in_tokens / 1_000_000 * price_in + out_tokens / 1_000_000 * price_out, 8)

    def active_model(self, secrets: dict | None = None, premium: bool | None = None) -> str:
        """Resolve the active Anthropic model from secrets or env."""
        sec = secrets or load_secrets()
        prem = premium if premium is not None else self.use_premium
        if prem:
            return sec.get(CLAUDE_PREMIUM_MODEL_KEY, _CLAUDE_PREMIUM_FALLBACK)
        return sec.get(CLAUDE_DEFAULT_MODEL_KEY, _CLAUDE_DEFAULT_FALLBACK)

    # ------------------------------------------------------------------
    # Per-provider dispatch
    # ------------------------------------------------------------------

    def _try_provider(
        self,
        provider: str,
        prompt: str,
        secrets: dict,
        premium: bool,
        max_tokens: int,
        timeout: float,
    ) -> tuple[str | None, str | None, float, bool] | None:
        """
        Try one provider. Returns (text, error, latency, quota_hit) or None if
        the provider has no usable key.
        """
        if provider == "anthropic":
            key = secrets.get("ANTHROPIC_API_KEY", "")
            if not key or any(m in key.lower() for m in ("your_", "paste_", "xxxx")):
                return None
            model = self.active_model(secrets, premium)
            text, err, lat = _anthropic_call(key, model, prompt, max_tokens, timeout)
            return text, err, lat, False

        if provider == "sambanova":
            key = secrets.get("SAMBANOVA_API_KEY", "")
            if not key or any(m in key.lower() for m in ("your_", "paste_", "xxxx")):
                return None
            model = secrets.get("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")
            text, err, lat, quota_hit = _sambanova_call(key, model, prompt, max_tokens, timeout)
            return text, err, lat, quota_hit

        if provider == "gemini":
            if not gemini_key_pool(secrets):
                return None
            rotator = get_gemini_rotator(secrets)
            text, err = gemini_generate(prompt, secrets=secrets, rotator=rotator)
            return text, err, 0.0, False

        meta = self._PROVIDER_META.get(provider)
        if meta is None:
            return None
        key = secrets.get(meta["key_name"], "")
        if not key or any(m in key.lower() for m in ("your_", "paste_", "xxxx")):
            return None
        model = secrets.get(f"{provider.upper()}_MODEL", meta["model_name"])
        text, err, lat = _openai_compat_call(
            meta["url"], key, model, prompt, max_tokens, timeout
        )
        return text, err, lat, False
