"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Honest Communication)
DEPENDENCIES: json, os, time, aura_api_rotator, aura_llm_call_logger
FUNCTIONS: ExternalLLM, interpret, generate, generate_openai_compatible_payload
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura External LLM Egress.
=========================

This is the only place Aura is permitted to touch a language model, and it is
always an external one. Aura's deterministic substrate stays LLM-free.

Default egress priority:

    Fireworks -> direct DeepSeek -> Anthropic -> Mistral -> SambaNova ->
    Groq -> Cerebras -> OpenRouter -> GitHub Models -> OpenAI -> Gemini

Fireworks defaults to GLM 5.2. The budget/cheap role uses DeepSeek-V4-Flash on
Fireworks. A separately configured DEEPSEEK_API_KEY may use DeepSeek directly as
the next provider fallback.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any
import urllib.request

from aura_api_rotator import (
    gemini_generate,
    gemini_key_pool,
    load_secrets,
    openai_compatible_generate,
)
from aura_context_crusher import apply_context_crush_to_messages, apply_context_crush_to_prompt
from aura_llm_call_logger import log_llm_call
from aura_paper_memory import (
    AuraResonanceEgressGate,
    load_research_profiles_from_jsonl,
    track_egress_savings,
    verify_egress_contract,
)
from aura_pre_egress_interceptor import apply_pre_egress_profile
from aura_provider_registry import ProviderRegistry
from aura_tokenizer_guard import sanitize_message_payloads, sanitize_tokenizer_channels

_REGISTRY = ProviderRegistry()
PROVIDERS: dict[str, dict[str, Any]] = _REGISTRY.providers
DEFAULT_PROVIDER_ORDER = list(_REGISTRY.provider_priority)
KNOWN_WORKING = tuple(DEFAULT_PROVIDER_ORDER)

_FORBIDDEN = {
    "local", "llama_local", "internal", "in_process", "llamacpp", "llama_cpp", "node",
}
_PLACEHOLDER_MARKERS = (
    "your_", "paste_", "changeme", "_here", "xxxx", "example", "replace_me",
)
_MODEL_ROLE_ALIASES = {
    "default": "primary",
    "primary": "primary",
    "best": "primary",
    "premium": "premium",
    "reasoner": "reasoner",
    "coding": "coding",
    "glm": "primary",
    "glm-5.2": "primary",
    "glm 5.2": "primary",
    "cheap": "cheap_builder",
    "budget": "cheap_builder",
    "fast": "cheap_builder",
    "flash": "cheap_builder",
    "deepseek": "cheap_builder",
    "deepseek-v4-flash": "cheap_builder",
    "shadow": "shadow",
    "summarizer": "summarizer",
}


def provider_priority() -> list[str]:
    """Return the deterministic external-provider priority order."""
    return list(DEFAULT_PROVIDER_ORDER)


def _secret_value(cfg: dict[str, Any], secrets: dict[str, Any]) -> str:
    key_name = str(cfg.get("key") or cfg.get("api_key_env") or "")
    value = secrets.get(key_name) if key_name else None
    if not value and key_name:
        value = os.environ.get(key_name)
    return str(value or "").strip()


def _has_key(name: str, cfg: dict[str, Any], sec: dict[str, Any]) -> bool:
    if cfg.get("api") == "gemini":
        return bool(gemini_key_pool(sec))
    key_val = _secret_value(cfg, sec)
    if not key_val:
        return False
    lowered = key_val.lower()
    return not any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _resolve_model(cfg: dict[str, Any], requested: str | None) -> str:
    roles = dict(cfg.get("default_roles") or {})
    if requested is None or not str(requested).strip():
        return str(cfg.get("model") or roles.get("primary") or "")
    raw = str(requested).strip()
    role = _MODEL_ROLE_ALIASES.get(raw.lower())
    if role and roles.get(role):
        return str(roles[role])
    if raw in roles:
        return str(roles[raw])
    return raw


def _anthropic_generate(
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
) -> tuple[str | None, str | None]:
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
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["content"][0]["text"]).strip(), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _forbidden_external_url(url: str) -> bool:
    low = (url or "").strip().lower()
    return any(
        low.startswith(prefix)
        for prefix in (
            "http://127.", "https://127.", "http://localhost", "https://localhost",
            "http://0.0.0.0", "https://0.0.0.0",
        )
    )


def generate_openai_compatible_payload(
    *,
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 900,
    temperature: float = 0.0,
    response_format: dict[str, Any] | None = None,
    timeout: float = 60,
    task: str | None = "aura_fusion",
    aspect: str | None = "fusion",
    baseline_prompt_tokens: int | None = None,
    baseline_output_tokens: int | None = None,
    baseline_cost_usd: float | None = None,
    context_crush: bool = True,
    context_crush_ledger: str | None = None,
) -> tuple[str | None, str | None, float, bool]:
    """Call an external OpenAI-compatible provider with Aura's egress guards."""
    if _forbidden_external_url(base_url):
        return None, "forbidden local/internal model endpoint", 0.0, False
    if not api_key or not str(api_key).strip():
        return None, f"missing API key for provider '{provider}'", 0.0, False

    crush_batch = None
    tokenizer_guard = None
    if context_crush:
        crush_batch = apply_context_crush_to_messages(messages, ledger_path=context_crush_ledger)
        outbound_messages = crush_batch.messages
    else:
        tokenizer_guard = sanitize_message_payloads(messages)
        outbound_messages = tokenizer_guard.messages

    payload: dict[str, Any] = {
        "model": model,
        "messages": outbound_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format

    def _metadata(schema: bool, *, retry: bool = False) -> dict[str, Any]:
        return {
            "provider": provider,
            "response_format": schema,
            "schema_retry": retry,
            "context_crush": crush_batch.to_jsonable() if crush_batch is not None else None,
            "tokenizer_guard": tokenizer_guard.to_jsonable() if tokenizer_guard is not None else None,
        }

    started = time.time()
    text, error = openai_compatible_generate(
        base_url,
        api_key,
        payload,
        timeout=timeout,
        task=task,
        aspect=aspect,
        baseline_prompt_tokens=baseline_prompt_tokens,
        baseline_output_tokens=baseline_output_tokens,
        baseline_cost_usd=baseline_cost_usd,
        savings_metadata=_metadata(bool(response_format)),
    )
    used_schema = bool(response_format and not error)
    if error and response_format and any(
        marker in str(error).lower()
        for marker in ("response_format", "json_schema", "schema", "400", "unsupported")
    ):
        payload.pop("response_format", None)
        text, error = openai_compatible_generate(
            base_url,
            api_key,
            payload,
            timeout=timeout,
            task=task,
            aspect=aspect,
            baseline_prompt_tokens=baseline_prompt_tokens,
            baseline_output_tokens=baseline_output_tokens,
            baseline_cost_usd=baseline_cost_usd,
            savings_metadata=_metadata(False, retry=True),
        )
        used_schema = False
    return text, error, time.time() - started, used_schema


def available_providers(secrets: dict[str, Any] | None = None) -> list[str]:
    """Return configured external providers in deterministic priority order."""
    sec = secrets if secrets is not None else load_secrets()
    return [
        name for name in DEFAULT_PROVIDER_ORDER
        if name in PROVIDERS and name not in _FORBIDDEN and _has_key(name, PROVIDERS[name], sec)
    ]


def classify_providers(secrets: dict[str, Any] | None = None) -> dict[str, list[str]]:
    sec = secrets if secrets is not None else load_secrets()
    working: list[str] = []
    configured: list[str] = []
    placeholder: list[str] = []
    ordered_names = list(dict.fromkeys([*DEFAULT_PROVIDER_ORDER, *PROVIDERS]))
    for name in ordered_names:
        if name in _FORBIDDEN or name not in PROVIDERS:
            continue
        if _has_key(name, PROVIDERS[name], sec):
            (working if name in KNOWN_WORKING else configured).append(name)
        else:
            placeholder.append(name)
    return {"working": working, "configured": configured, "placeholder": placeholder}


def usable_providers(
    secrets: dict[str, Any] | None = None,
    prefer_working: bool = True,
) -> list[str]:
    buckets = classify_providers(secrets)
    if prefer_working and buckets["working"]:
        return list(buckets["working"])
    return buckets["working"] + buckets["configured"]


class ExternalLLM:
    """Aura's single external-language-model egress."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        secrets: dict[str, Any] | None = None,
        task: str | None = None,
        aspect: str | None = None,
        baseline_prompt_tokens: int | None = None,
        baseline_output_tokens: int | None = None,
        baseline_cost_usd: float | None = None,
    ) -> None:
        self.secrets = secrets if secrets is not None else load_secrets()
        candidates = [provider] if provider else DEFAULT_PROVIDER_ORDER
        chosen = None
        last_error = None
        for candidate in candidates:
            if candidate is None:
                continue
            name = str(candidate).lower()
            if name in _FORBIDDEN:
                raise ValueError(
                    f"Provider '{candidate}' is forbidden in egress. Aura must use an external provider "
                    f"from {DEFAULT_PROVIDER_ORDER}."
                )
            if name not in PROVIDERS:
                last_error = f"unknown provider '{candidate}'"
                continue
            if not _has_key(name, PROVIDERS[name], self.secrets):
                last_error = f"no API key for '{candidate}'"
                continue
            chosen = name
            break
        if chosen is None:
            raise RuntimeError(f"No usable external provider. Last error: {last_error}")

        self.provider = chosen
        self.cfg = PROVIDERS[chosen]
        if chosen == "anthropic":
            default_model = str(self.secrets.get("CLAUDE_DEFAULT_MODEL") or os.environ.get("CLAUDE_DEFAULT_MODEL") or "claude-sonnet-4-6")
            premium_model = str(self.secrets.get("CLAUDE_PREMIUM_MODEL") or os.environ.get("CLAUDE_PREMIUM_MODEL") or "claude-opus-4-8")
            query = str(model or "").strip().lower()
            if query in {"premium", "opus", "claude-opus-4-8", premium_model.lower()}:
                self.model = premium_model
            elif not query or query in {"default", "sonnet", "claude-sonnet-4-6", default_model.lower()}:
                self.model = default_model
            else:
                self.model = str(model)
        else:
            self.model = _resolve_model(self.cfg, model)

        self.api = str(self.cfg.get("api") or "openai")
        self.is_gemini = self.api == "gemini"
        self.api_key = _secret_value(self.cfg, self.secrets)
        self._task = task
        self._aspect = aspect
        self._baseline_prompt = baseline_prompt_tokens
        self._baseline_output = baseline_output_tokens
        self._baseline_cost = baseline_cost_usd

    def _log_to_savings(
        self,
        call_type: str,
        prompt: str,
        output_text: str | None,
        latency_sec: float,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        log_llm_call(
            provider=self.provider,
            model=self.model,
            call_type=call_type,
            prompt_text=prompt,
            output_text=output_text,
            latency_sec=latency_sec,
            error=error,
            task=self._task,
            aspect=self._aspect,
            baseline_prompt_tokens=self._baseline_prompt,
            baseline_output_tokens=self._baseline_output,
            baseline_cost_usd=self._baseline_cost,
            metadata={"source": "ExternalLLM._log_to_savings", **(metadata or {})},
        )

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1300,
        temperature: float = 0.1,
        router_context: str | None = None,
        slot_matrix: Any | None = None,
        pre_egress: bool = True,
        call_type: str = "generate",
        paper_ledger: str | None = None,
        resonance_egress: bool = True,
        grammar_stencil: str = "root ::=",
        context_crush: bool = True,
        context_crush_ledger: str | None = None,
    ) -> tuple[str | None, str | None, float]:
        full_prompt = (
            f"{prompt}\n\nCODE CONTEXT (from AI Router – read this section only, not the whole file):\n"
            f"```python\n{router_context}\n```"
            if router_context else prompt
        )
        resonance_intent = full_prompt
        crush_result = None
        if context_crush:
            crush_result = apply_context_crush_to_prompt(
                full_prompt,
                source_hint="external_llm.generate",
                ledger_path=context_crush_ledger,
            )
            full_prompt = crush_result.compressed_payload

        raec_payload = None
        raec_metrics: dict[str, Any] | None = None
        if resonance_egress:
            raec_start = time.time()
            ledger_path = paper_ledger or os.environ.get("AURA_PAPER_MEMORY_LEDGER") or "Aura_Memory/paper_memory_ledger.jsonl"
            try:
                profiles = load_research_profiles_from_jsonl(ledger_path)
                if profiles:
                    gate = AuraResonanceEgressGate()
                    raec_payload = gate.inject_latent_context(resonance_intent, profiles, self.provider)
                    if verify_egress_contract(raec_payload, grammar_stencil):
                        full_prompt = f"{full_prompt}\n\n[AURA_RAEC]\n{raec_payload.slot_matrix_string}\n[/AURA_RAEC]"
                raec_metrics = track_egress_savings(len(full_prompt), 0, time.time() - raec_start)
            except Exception:  # noqa: BLE001
                raec_payload = None
                raec_metrics = None

        profile_decision = None
        if pre_egress:
            full_prompt, profile_decision = apply_pre_egress_profile(full_prompt, slot_matrix=slot_matrix)
            if profile_decision.throttled:
                max_tokens = min(max_tokens, 512)
        tokenizer_guard = sanitize_tokenizer_channels(full_prompt)
        full_prompt = tokenizer_guard.sanitized_text

        savings_meta = {
            "source": "ExternalLLM.generate",
            "provider_priority": provider_priority(),
            "selected_provider": self.provider,
            "selected_model": self.model,
            "pre_egress": pre_egress,
            "pre_egress_profile": getattr(profile_decision, "profile_id", None),
            "resonance_egress": bool(raec_payload and raec_payload.slot_matrix_string),
            "raec_slot_chars": len(raec_payload.slot_matrix_string if raec_payload is not None else ""),
            "raec_lift_dispatch_count": len(raec_payload.lift_dispatch if raec_payload is not None else ()),
            "raec_efficiency": raec_metrics,
            "context_crush": crush_result.to_jsonable() if crush_result is not None else None,
            "tokenizer_guard": tokenizer_guard.to_jsonable(),
        }

        started = time.time()
        logged_by_helper = False
        if self.is_gemini:
            text, error = gemini_generate(
                full_prompt,
                secrets=self.secrets,
                call_type=call_type,
                task=self._task,
                aspect=self._aspect,
                baseline_prompt_tokens=self._baseline_prompt,
                baseline_output_tokens=self._baseline_output,
                baseline_cost_usd=self._baseline_cost,
                savings_metadata=savings_meta,
            )
            logged_by_helper = True
        elif self.api == "anthropic":
            text, error = _anthropic_generate(
                self.cfg["url"], self.api_key, self.model, full_prompt, max_tokens, timeout=60,
            )
        else:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            text, error = openai_compatible_generate(
                self.cfg["url"],
                self.api_key,
                payload,
                timeout=60,
                call_type=call_type,
                task=self._task,
                aspect=self._aspect,
                baseline_prompt_tokens=self._baseline_prompt,
                baseline_output_tokens=self._baseline_output,
                baseline_cost_usd=self._baseline_cost,
                savings_metadata=savings_meta,
            )
            logged_by_helper = True
        latency = time.time() - started
        if not logged_by_helper:
            self._log_to_savings(call_type, full_prompt, text, latency, error=error, metadata=savings_meta)
        return text, error, latency

    def interpret(
        self,
        data: Any,
        instruction: str,
        *,
        max_tokens: int = 400,
        slot_matrix: Any | None = None,
        pre_egress: bool = True,
    ) -> tuple[str | None, str | None, float]:
        if not isinstance(data, str):
            data = json.dumps(data, indent=2, default=str)
        prompt = (
            "You are the external voice for the Aura substrate. Aura is a fast, deterministic "
            "orchestration layer that does not run its own language model. Below is structured "
            f"data Aura produced. {instruction}\n\n[AURA DATA]\n{data}\n"
        )
        return self.generate(
            prompt,
            max_tokens=max_tokens,
            slot_matrix=slot_matrix,
            pre_egress=pre_egress,
            call_type="interpret",
        )

    def cost(self, in_tokens: int, out_tokens: int) -> float:
        try:
            from aura_pricing import get_pricebook
            return get_pricebook().cost(self.provider, in_tokens, out_tokens)
        except Exception:  # noqa: BLE001
            in_price = float(self.cfg.get("price_in_per_1k") or 0.0)
            out_price = float(self.cfg.get("price_out_per_1k") or 0.0)
            return round(in_tokens / 1000 * in_price + out_tokens / 1000 * out_price, 6)
