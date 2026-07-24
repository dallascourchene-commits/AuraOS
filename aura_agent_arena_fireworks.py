"""Aura Agent Arena external patch-worker compatibility bridge.

The historical MCP/tool name remains ``fireworks_patch_worker`` so existing
clients do not break. Its implementation is provider-neutral: compressed patch
work is routed through Aura's canonical DeepSeek-first egress, rotates every
configured key, and falls back across providers. The worker may return candidate
diffs only; it never applies, commits, pushes, or merges them.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

from aura_agent_arena_errors import make_error_packet
from aura_api_rotator import load_secrets, provider_key_pool
from aura_llm_egress import (
    available_providers,
    generate_routed_openai_compatible_payload,
)
from aura_provider_registry import ProviderRegistry

FIREWORKS_BRIDGE_VERSION = "AURA_AGENT_ARENA_EXTERNAL_WORKER_V2"
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

_DEFAULT_MODELS = {
    "fast": "accounts/fireworks/models/llama-v3-1-8b-instruct",
    "code": "accounts/fireworks/models/llama-v3-1-70b-instruct",
    "judge": "accounts/fireworks/models/llama-v3-1-70b-instruct",
}

STATIC_SYSTEM_PROMPT = """\
You are an external coding agent using Aura Agent Arena Bridge.

Never read full repo files unless Aura explicitly grants a slice.
Use aura_repo_digest first.
Use aura_prepare_arena before patching.
Use aura_get_micro_context for exact task context.
Return unified diffs only.
Never patch from VSA, ST3GG, JSpace, screenshots, or summaries alone.
Patch authority is exact source spans, hashes, tests, and verifier gates.
If blocked, call aura_repair_packet.
If tests fail twice, escalate instead of broadening scope.
"""


def _get_model(tier: str) -> str | None:
    generic = os.environ.get(f"AURA_AGENT_ARENA_MODEL_{tier.upper()}")
    if generic:
        return generic
    if os.environ.get("AURA_AGENT_ARENA_PROVIDER", "").strip().lower() == "fireworks":
        return os.environ.get(f"AURA_FIREWORKS_MODEL_{tier.upper()}", _DEFAULT_MODELS.get(tier, _DEFAULT_MODELS["fast"]))
    return None


def _get_session_id() -> str:
    session_id = os.environ.get("AURA_FIREWORKS_SESSION_ID") or os.environ.get("AURA_AGENT_ARENA_SESSION_ID")
    if session_id:
        return session_id
    repo_hash = hashlib.blake2b(os.getcwd().encode(), digest_size=8).hexdigest()
    return f"aura-arena-{repo_hash}"


def _model_role(tier: str) -> str:
    return {
        "fast": "cheap_builder",
        "code": "coding",
        "judge": "premium",
    }.get(str(tier or "fast").lower(), "cheap_builder")


def _openai_worker_providers(secrets: dict[str, Any], role: str) -> list[str]:
    registry = ProviderRegistry()
    return [
        provider
        for provider in available_providers(secrets, role=role)
        if str((registry.get_provider_config(provider) or {}).get("api") or "openai") == "openai"
    ]


def _has_api_key() -> bool:
    return bool(_openai_worker_providers(load_secrets(), "cheap_builder"))


def fireworks_patch_worker(
    *,
    task_id: str,
    compressed_context: str,
    instruction: str,
    model_tier: str = "fast",
    max_output_tokens: int = 2048,
) -> dict[str, Any]:
    """Route a compressed micro-patch through replaceable external providers.

    The compatibility name is intentionally retained. The returned diff must be
    staged with ``aura_stage_patch`` and verified with ``aura_verify_arena``.
    """
    secrets = load_secrets()
    if not _openai_worker_providers(secrets, _model_role(model_tier)):
        return make_error_packet(
            "fireworks_call_failed",
            "No external provider key is configured. Add DEEPSEEK_API_KEY, MISTRAL_API_KEY, "
            "XAI_API_KEY/GROK_API_KEY, FIREWORKS_API_KEY, or another registered provider key.",
            repair_hint="Add one or more provider keys to aura_secrets.json; plural and numbered backup keys are rotated automatically.",
            next_allowed_tools=["aura_stage_patch"],
        )
    if not compressed_context or not compressed_context.strip():
        return make_error_packet(
            "fireworks_call_failed",
            "compressed_context is required and must be non-empty.",
            repair_hint="Call aura_get_micro_context first to get compressed context.",
        )
    if not instruction or not instruction.strip():
        return make_error_packet(
            "fireworks_call_failed",
            "instruction is required and must be non-empty.",
        )

    user_content = (
        f"Task ID: {task_id}\n\n"
        f"Compressed Context:\n{compressed_context}\n\n"
        f"Instruction:\n{instruction}\n\n"
        "Return a unified diff only. Do not include explanations."
    )
    preferred_provider = os.environ.get("AURA_AGENT_ARENA_PROVIDER", "").strip().lower() or None
    preferred_model = _get_model(model_tier)
    text, error, latency, _used_schema, route = generate_routed_openai_compatible_payload(
        messages=[
            {"role": "system", "content": STATIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        model_role=_model_role(model_tier),
        preferred_provider=preferred_provider,
        preferred_model=preferred_model,
        secrets=secrets,
        allow_provider_fallback=True,
        max_tokens=max_output_tokens,
        temperature=0.2,
        task="agent_arena_patch_worker",
        aspect="candidate_diff",
        context_crush=False,
    )
    if error or not text:
        return make_error_packet(
            "fireworks_call_failed",
            f"External patch worker failed: {error or 'empty response'}",
            repair_hint="Check configured provider keys, quotas, model availability, and network connectivity.",
            next_allowed_tools=["aura_stage_patch"],
        )

    warnings: list[str] = []
    if not any(
        line.startswith(("diff --git", "--- ", "+++ ", "@@"))
        for line in text.splitlines()
    ):
        warnings.append("Response does not appear to be a unified diff. Verify before staging.")

    return {
        "ok": True,
        "provider": route.get("provider"),
        "model": route.get("model"),
        "diff": text,
        "usage": {},
        "cache_headers": {},
        "session_id": _get_session_id(),
        "latency_sec": round(latency, 3),
        "fallback_index": route.get("fallback_index", 0),
        "key_count": route.get("key_count", 0),
        "warnings": warnings,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
        "must_stage_before_apply": True,
    }


def is_fireworks_available() -> bool:
    """Return whether the legacy Fireworks provider itself has a usable key."""
    secrets = load_secrets()
    config = ProviderRegistry().get_provider_config("fireworks") or {}
    names = [config.get("api_key_env", "FIREWORKS_API_KEY"), *config.get("api_key_aliases", [])]
    return bool(provider_key_pool("fireworks", secrets, key_names=names))


def is_external_worker_available() -> bool:
    """Return whether any registered OpenAI-compatible patch worker is usable."""
    return _has_api_key()
