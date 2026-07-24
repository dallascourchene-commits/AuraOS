"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Honest Communication)
DEPENDENCIES: json, os, time, aura_api_rotator, aura_llm_call_logger
FUNCTIONS: ExternalLLM, interpret, generate, generate_openai_compatible_payload, generate_routed_openai_compatible_payload, generate_architect_model
SYNOPSIS: DeepSeek-first role-aware external egress with provider and per-provider key fallback.
[/AURA_MASTER_KEY]

Aura External LLM Egress.
=========================

This is the canonical place Aura is permitted to touch a language model, and it
is always an external one. Aura's deterministic substrate stays LLM-free.

Premium/default work starts with direct DeepSeek. Cheap, Shadow, and summary
work use the registry's lower-cost order. Every provider consumes all valid keys
from ``aura_secrets.json`` through deterministic round-robin rotation, and an
unpinned call falls through to the next configured provider on quota, timeout,
or provider failure.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any
import urllib.request

from aura_api_rotator import (
    gemini_generate,
    get_provider_rotator,
    load_secrets,
    openai_compatible_generate,
    provider_key_pool,
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
DEFAULT_PROVIDER_ORDER = _REGISTRY.provider_order("primary")
KNOWN_WORKING = tuple(dict.fromkeys(name for role in _REGISTRY.provider_priority_by_role.values() for name in role))

_FORBIDDEN = {
    "local", "llama_local", "internal", "in_process", "llamacpp", "llama_cpp", "node",
}
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
    "deepseek": "primary",
    "deepseek-v4-flash": "cheap_builder",
    "shadow": "shadow",
    "summarizer": "summarizer",
}


def _requested_role(requested: str | None) -> str:
    raw = str(requested or "primary").strip().lower()
    return _MODEL_ROLE_ALIASES.get(raw, raw if raw in _REGISTRY.provider_priority_by_role else "primary")


def provider_priority(role: str | None = None) -> list[str]:
    """Return deterministic external-provider priority for a model role."""
    return _REGISTRY.provider_order(_requested_role(role))


def _key_names(cfg: dict[str, Any]) -> list[str]:
    return [
        str(name)
        for name in [cfg.get("api_key_env") or cfg.get("key"), *cfg.get("api_key_aliases", [])]
        if name
    ]


def _provider_keys(name: str, cfg: dict[str, Any], secrets: dict[str, Any]) -> list[str]:
    return provider_key_pool(name, secrets, key_names=_key_names(cfg))


def _secret_value(cfg: dict[str, Any], secrets: dict[str, Any]) -> str:
    provider = str(cfg.get("provider") or "")
    keys = _provider_keys(provider, cfg, secrets)
    return keys[0] if keys else ""


def _has_key(name: str, cfg: dict[str, Any], sec: dict[str, Any]) -> bool:
    return bool(_provider_keys(name, cfg, sec))


def _resolve_model(cfg: dict[str, Any], requested: str | None) -> str:
    roles = dict(cfg.get("default_roles") or {})
    if requested is None or not str(requested).strip():
        return str(roles.get("primary") or cfg.get("model") or "")
    raw = str(requested).strip()
    role = _MODEL_ROLE_ALIASES.get(raw.lower())
    if role:
        return str(roles.get(role) or cfg.get("model") or raw)
    if roles.get(raw.lower()):
        return str(roles[raw.lower()])
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


def _unique_keys(api_key: str | None, api_keys: list[str] | tuple[str, ...] | None) -> list[str]:
    ordered: list[str] = []
    for key in [api_key, *(api_keys or ())]:
        value = str(key or "").strip()
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def generate_openai_compatible_payload(
    *,
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    api_keys: list[str] | tuple[str, ...] | None = None,
    max_tokens: int = 900,
    temperature: float = 0.0,
    response_format: dict[str, Any] | None = None,
    timeout: float = 60,
    call_type: str = "generate",
    allow_provider_fallback: bool = True,
    model_role: str | None = None,
    task: str | None = "aura_fusion",
    aspect: str | None = "fusion",
    baseline_prompt_tokens: int | None = None,
    baseline_output_tokens: int | None = None,
    baseline_cost_usd: float | None = None,
    context_crush: bool = True,
    context_crush_ledger: str | None = None,
) -> tuple[str | None, str | None, float, bool]:
    """Call one OpenAI-compatible provider, rotating every configured key."""
    if _forbidden_external_url(base_url):
        return None, "forbidden local/internal model endpoint", 0.0, False
    cfg = PROVIDERS.get(str(provider or "").lower()) or {}
    configured_keys = _provider_keys(str(provider or "").lower(), cfg, load_secrets()) if cfg else []
    keys = _unique_keys(api_key, [*(api_keys or ()), *configured_keys])
    if not keys:
        return None, f"missing API key for provider '{provider}'", 0.0, False

    crush_batch = None
    tokenizer_guard = None
    if context_crush:
        crush_batch = apply_context_crush_to_messages(messages, ledger_path=context_crush_ledger)
        outbound_messages = crush_batch.messages
    else:
        tokenizer_guard = sanitize_message_payloads(messages)
        outbound_messages = tokenizer_guard.messages

    base_payload: dict[str, Any] = {
        "model": model,
        "messages": outbound_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_format:
        base_payload["response_format"] = response_format

    def _metadata(schema: bool, *, retry: bool = False, key_index: int = 0) -> dict[str, Any]:
        return {
            "provider": provider,
            "response_format": schema,
            "schema_retry": retry,
            "key_index": key_index,
            "key_count": len(keys),
            "context_crush": crush_batch.to_jsonable() if crush_batch is not None else None,
            "tokenizer_guard": tokenizer_guard.to_jsonable() if tokenizer_guard is not None else None,
        }

    started = time.time()
    rotator = get_provider_rotator(provider, keys=keys)
    errors: list[str] = []
    rotated_keys = rotator.iter_keys()
    if not rotated_keys:
        return None, f"all keys cooling down for provider '{provider}'", time.time() - started, False
    for key_index, key in enumerate(rotated_keys):
        payload = dict(base_payload)
        text, error = openai_compatible_generate(
            base_url,
            key,
            payload,
            timeout=timeout,
            call_type=call_type,
            task=task,
            aspect=aspect,
            baseline_prompt_tokens=baseline_prompt_tokens,
            baseline_output_tokens=baseline_output_tokens,
            baseline_cost_usd=baseline_cost_usd,
            savings_metadata=_metadata(bool(response_format), key_index=key_index),
        )
        used_schema = bool(response_format and not error)
        if error and response_format and any(
            marker in str(error).lower()
            for marker in ("response_format", "json_schema", "schema", "400", "unsupported")
        ):
            payload.pop("response_format", None)
            text, error = openai_compatible_generate(
                base_url,
                key,
                payload,
                timeout=timeout,
                call_type=call_type,
                task=task,
                aspect=aspect,
                baseline_prompt_tokens=baseline_prompt_tokens,
                baseline_output_tokens=baseline_output_tokens,
                baseline_cost_usd=baseline_cost_usd,
                savings_metadata=_metadata(False, retry=True, key_index=key_index),
            )
            used_schema = False
        if text and not error:
            rotator.record_success(key)
            return text, None, time.time() - started, used_schema
        rotator.record_failure(key, str(error or "empty response"))
        errors.append(f"key[{key_index}]: {error or 'empty response'}")
    if allow_provider_fallback:
        inferred_role = _requested_role(model_role or ("cheap_builder" if any(token in str(model).lower() for token in ("small", "flash", "mini", "8b")) else "premium"))
        for fallback_provider in provider_priority(inferred_role):
            if fallback_provider == str(provider or "").lower():
                continue
            fallback_cfg = PROVIDERS.get(fallback_provider)
            if not fallback_cfg or str(fallback_cfg.get("api") or "openai") != "openai":
                continue
            fallback_keys = _provider_keys(fallback_provider, fallback_cfg, load_secrets())
            if not fallback_keys:
                continue
            fallback_model = _resolve_model(fallback_cfg, inferred_role)
            text, error, _latency, used_schema = generate_openai_compatible_payload(
                provider=fallback_provider,
                base_url=str(fallback_cfg["url"]),
                api_key=fallback_keys[0],
                api_keys=fallback_keys[1:],
                model=fallback_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
                timeout=timeout,
                call_type=call_type,
                allow_provider_fallback=False,
                model_role=inferred_role,
                task=task,
                aspect=aspect,
                baseline_prompt_tokens=baseline_prompt_tokens,
                baseline_output_tokens=baseline_output_tokens,
                baseline_cost_usd=baseline_cost_usd,
                context_crush=context_crush,
                context_crush_ledger=context_crush_ledger,
            )
            if text and not error:
                return text, None, time.time() - started, used_schema
            errors.append(f"{fallback_provider}: {error or 'empty response'}")
    return None, "; ".join(errors), time.time() - started, False


def generate_routed_openai_compatible_payload(
    *,
    messages: list[dict[str, str]],
    model_role: str = "premium",
    preferred_provider: str | None = None,
    preferred_model: str | None = None,
    secrets: dict[str, Any] | None = None,
    allow_provider_fallback: bool = True,
    **kwargs: Any,
) -> tuple[str | None, str | None, float, bool, dict[str, Any]]:
    """Route structured messages across configured OpenAI-compatible providers."""
    sec = secrets if secrets is not None else load_secrets()
    role = _requested_role(model_role)
    order = _REGISTRY.provider_order(role)
    preferred = str(preferred_provider or "").lower()
    if preferred:
        order = [preferred, *(name for name in order if name != preferred)]
        if not allow_provider_fallback:
            order = order[:1]
    errors: list[str] = []
    started = time.time()
    for index, provider in enumerate(order):
        cfg = PROVIDERS.get(provider)
        if not cfg or provider in _FORBIDDEN or str(cfg.get("api") or "openai") != "openai":
            continue
        keys = _provider_keys(provider, cfg, sec)
        if not keys:
            continue
        model = preferred_model if index == 0 and preferred_model else _resolve_model(cfg, role)
        text, error, _latency, used_schema = generate_openai_compatible_payload(
            provider=provider,
            base_url=str(cfg["url"]),
            api_key=keys[0],
            api_keys=keys[1:],
            model=str(model),
            messages=messages,
            allow_provider_fallback=False,
            model_role=role,
            **kwargs,
        )
        if text and not error:
            return text, None, time.time() - started, used_schema, {
                "provider": provider,
                "model": model,
                "fallback_index": index,
                "key_count": len(keys),
            }
        errors.append(f"{provider}: {error or 'empty response'}")
    return None, "; ".join(errors) or "no configured OpenAI-compatible provider", time.time() - started, False, {}


def available_providers(secrets: dict[str, Any] | None = None, *, role: str | None = None) -> list[str]:
    """Return configured external providers in deterministic role priority order."""
    sec = secrets if secrets is not None else load_secrets()
    return [
        name for name in provider_priority(role)
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
    *,
    role: str | None = None,
) -> list[str]:
    available = available_providers(secrets, role=role)
    if prefer_working:
        return [name for name in available if name in KNOWN_WORKING]
    return available


class ExternalLLM:
    """Aura's single external-language-model egress with automatic failover."""

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
        allow_provider_fallback: bool | None = None,
    ) -> None:
        self.secrets = secrets if secrets is not None else load_secrets()
        self.requested_model = model
        self.model_role = _requested_role(model)
        fallback_allowed = bool(allow_provider_fallback) if allow_provider_fallback is not None else provider is None
        self._provider_pinned = provider is not None and not fallback_allowed
        base_order = provider_priority(self.model_role)
        preferred = str(provider or "").lower()
        candidates = ([preferred] + [name for name in base_order if name != preferred]) if preferred else base_order
        if self._provider_pinned:
            candidates = candidates[:1]
        for candidate in candidates:
            if candidate in _FORBIDDEN:
                raise ValueError(
                    f"Provider '{candidate}' is forbidden in egress. Aura must use an external provider "
                    f"from {provider_priority(self.model_role)}."
                )
        self._routes = [
            name for name in candidates
            if name in PROVIDERS and _has_key(name, PROVIDERS[name], self.secrets)
        ]
        if not self._routes:
            raise RuntimeError(f"No usable external provider for role '{self.model_role}'.")
        self._task = task
        self._aspect = aspect
        self._baseline_prompt = baseline_prompt_tokens
        self._baseline_output = baseline_output_tokens
        self._baseline_cost = baseline_cost_usd
        self._activate(self._routes[0])

    def _activate(self, provider: str) -> None:
        self.provider = provider
        self.cfg = PROVIDERS[provider]
        request = self.requested_model if self._provider_pinned else self.model_role
        self.model = _resolve_model(self.cfg, request)
        if provider == "anthropic":
            default_model = str(
                self.secrets.get("CLAUDE_DEFAULT_MODEL")
                or os.environ.get("CLAUDE_DEFAULT_MODEL")
                or "claude-sonnet-4-6"
            )
            premium_model = str(
                self.secrets.get("CLAUDE_PREMIUM_MODEL")
                or os.environ.get("CLAUDE_PREMIUM_MODEL")
                or "claude-opus-4-8"
            )
            self.model = premium_model if self.model_role in {"premium", "reasoner"} else default_model
        self.api = str(self.cfg.get("api") or "openai")
        self.is_gemini = self.api == "gemini"
        self.api_keys = _provider_keys(provider, self.cfg, self.secrets)
        self.api_key = self.api_keys[0] if self.api_keys else ""

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

    def _call_current(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
        call_type: str,
        savings_meta: dict[str, Any],
    ) -> tuple[str | None, str | None, bool]:
        if self.is_gemini:
            text, error = gemini_generate(
                prompt,
                secrets=self.secrets,
                call_type=call_type,
                task=self._task,
                aspect=self._aspect,
                baseline_prompt_tokens=self._baseline_prompt,
                baseline_output_tokens=self._baseline_output,
                baseline_cost_usd=self._baseline_cost,
                savings_metadata=savings_meta,
            )
            return text, error, True
        if self.api == "anthropic":
            errors: list[str] = []
            rotator = get_provider_rotator(self.provider, keys=self.api_keys)
            rotated_keys = rotator.iter_keys()
            if not rotated_keys:
                return None, f"all keys cooling down for provider '{self.provider}'", False
            for key in rotated_keys:
                text, error = _anthropic_generate(
                    self.cfg["url"], key, self.model, prompt, max_tokens, timeout=60,
                )
                if text and not error:
                    rotator.record_success(key)
                    return text, None, False
                rotator.record_failure(key, str(error or "empty response"))
                errors.append(str(error or "empty response"))
            return None, "; ".join(errors), False
        text, error, _latency, _schema = generate_openai_compatible_payload(
            provider=self.provider,
            base_url=self.cfg["url"],
            api_key=self.api_keys[0],
            api_keys=self.api_keys[1:],
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=60,
            call_type=call_type,
            allow_provider_fallback=False,
            model_role=self.model_role,
            task=self._task,
            aspect=self._aspect,
            baseline_prompt_tokens=self._baseline_prompt,
            baseline_output_tokens=self._baseline_output,
            baseline_cost_usd=self._baseline_cost,
            context_crush=False,
        )
        return text, error, True

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

        started = time.time()
        errors: list[str] = []
        for fallback_index, provider in enumerate(self._routes):
            self._activate(provider)
            savings_meta = {
                "source": "ExternalLLM.generate",
                "provider_priority": provider_priority(self.model_role),
                "selected_provider": self.provider,
                "selected_model": self.model,
                "fallback_index": fallback_index,
                "key_count": len(self.api_keys),
                "pre_egress": pre_egress,
                "pre_egress_profile": getattr(profile_decision, "profile_id", None),
                "resonance_egress": bool(raec_payload and raec_payload.slot_matrix_string),
                "raec_slot_chars": len(raec_payload.slot_matrix_string if raec_payload is not None else ""),
                "raec_lift_dispatch_count": len(raec_payload.lift_dispatch if raec_payload is not None else ()),
                "raec_efficiency": raec_metrics,
                "context_crush": crush_result.to_jsonable() if crush_result is not None else None,
                "tokenizer_guard": tokenizer_guard.to_jsonable(),
            }
            text, error, logged_by_helper = self._call_current(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                call_type=call_type,
                savings_meta=savings_meta,
            )
            latency = time.time() - started
            if not logged_by_helper:
                self._log_to_savings(call_type, full_prompt, text, latency, error=error, metadata=savings_meta)
            if text and not error:
                return text, None, latency
            errors.append(f"{provider}: {error or 'empty response'}")
            if self._provider_pinned:
                break
        return None, "; ".join(errors), time.time() - started

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


def generate_architect_model(
    provider_tag: str,
    prompt: str,
    meta: dict[str, Any] | None = None,
    *,
    secrets: dict[str, Any] | None = None,
) -> str | None:
    """Council/Architect callback routed through the canonical egress."""
    payload = dict(meta or {})
    profile = dict(payload.get("profile") or {})
    role = str(payload.get("role") or profile.get("role") or "planner").lower()
    cost_tier = str(profile.get("cost_tier") or "premium").lower()
    model_role = "cheap_builder" if cost_tier == "cheap" or role in {"worker", "shadow"} else "premium"
    preferred = str(provider_tag or "").lower()
    if preferred not in PROVIDERS:
        preferred = ""
    try:
        egress = ExternalLLM(
            provider=preferred or None,
            model=model_role,
            secrets=secrets,
            task="architect_council",
            aspect=role,
            allow_provider_fallback=True,
        )
    except (RuntimeError, ValueError):
        return None
    text, _error, _latency = egress.generate(
        prompt,
        max_tokens=1300,
        temperature=0.0,
        pre_egress=True,
        call_type="architect_council",
    )
    return text
