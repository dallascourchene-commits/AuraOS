"""
Aura Agent Arena Bridge — Fireworks worker integration.

Lets Aura call a cheap/fast Fireworks model only after Aura has compressed the
exact context.  Uses the user's Fireworks credits and stable prompt caching.

The Fireworks worker may generate candidate diffs only.  It cannot apply
patches directly.  Every returned diff must go through ``aura_stage_patch``
and ``aura_verify_arena``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from aura_agent_arena_errors import make_error_packet

_LOG = logging.getLogger(__name__)

FIREWORKS_BRIDGE_VERSION = "AURA_AGENT_ARENA_FIREWORKS_V1"
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

# Model tier defaults — can be overridden by environment variables.
_DEFAULT_MODELS = {
    "fast": "accounts/fireworks/models/llama-v3-1-8b-instruct",
    "code": "accounts/fireworks/models/llama-v3-1-70b-instruct",
    "judge": "accounts/fireworks/models/llama-v3-1-70b-instruct",
}

# Static system prompt — kept stable for prompt caching.
# Do NOT include timestamps, branch names, or dynamic test logs here.
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


def _get_model(tier: str) -> str:
    env_key = f"AURA_FIREWORKS_MODEL_{tier.upper()}"
    return os.environ.get(env_key, _DEFAULT_MODELS.get(tier, _DEFAULT_MODELS["fast"]))


def _get_session_id() -> str:
    """Build a stable session affinity key for prompt caching."""
    session_id = os.environ.get("AURA_FIREWORKS_SESSION_ID", "")
    if session_id:
        return session_id
    # Build from repo hash + branch if available.
    repo_hash = hashlib.blake2b(os.getcwd().encode(), digest_size=8).hexdigest()
    branch = "default"
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode == 0:
            branch = proc.stdout.strip() or "default"
    except Exception:  # noqa: BLE001
        pass
    return f"aura-arena-{repo_hash}-{branch}"


def _has_api_key() -> bool:
    return bool(os.environ.get("FIREWORKS_API_KEY"))


def fireworks_patch_worker(
    *,
    task_id: str,
    compressed_context: str,
    instruction: str,
    model_tier: str = "fast",
    max_output_tokens: int = 2048,
) -> dict[str, Any]:
    """Call a Fireworks model for a compressed micro-patch.

    Returns a candidate diff only — never applies the patch.
    The caller must stage the diff via ``aura_stage_patch`` and verify
    via ``aura_verify_arena``.
    """
    if not _has_api_key():
        return make_error_packet(
            "fireworks_call_failed",
            "FIREWORKS_API_KEY is not set. Fireworks worker skipped safely.",
            repair_hint="Set FIREWORKS_API_KEY environment variable to use delegated Fireworks mode.",
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

    # Lazy import openai — it may not be installed.
    try:
        from openai import OpenAI
    except ImportError:
        return make_error_packet(
            "fireworks_call_failed",
            "openai package is not installed. Install with: pip install openai",
            repair_hint="The openai package is required for Fireworks integration.",
        )

    model = _get_model(model_tier)
    session_id = _get_session_id()

    # Build messages: static system prompt first (for cache), dynamic content last.
    user_content = (
        f"Task ID: {task_id}\n\n"
        f"Compressed Context:\n{compressed_context}\n\n"
        f"Instruction:\n{instruction}\n\n"
        f"Return a unified diff only. Do not include explanations."
    )

    messages = [
        {"role": "system", "content": STATIC_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        client = OpenAI(
            api_key=os.environ["FIREWORKS_API_KEY"],
            base_url=FIREWORKS_BASE_URL,
        )

        # Set session affinity header for prompt caching.
        extra_headers = {
            "x-session-affinity": session_id,
        }

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_output_tokens,
            temperature=0.2,
            extra_headers=extra_headers,
        )

        diff_text = ""
        if response.choices:
            diff_text = response.choices[0].message.content or ""

        # Extract usage info.
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        # Extract cache headers if available.
        cache_headers: dict[str, Any] = {}
        if hasattr(response, "headers") and response.headers:
            for key in ("x-session-affinity", "x-cache-hit", "x-cached-tokens"):
                val = response.headers.get(key)
                if val:
                    cache_headers[key] = val

        # Validate the diff looks like a unified diff.
        warnings: list[str] = []
        if diff_text and not any(
            line.startswith(("diff --git", "--- ", "+++ ", "@@"))
            for line in diff_text.splitlines()
        ):
            warnings.append("Response does not appear to be a unified diff. Verify before staging.")

        return {
            "ok": True,
            "model": model,
            "diff": diff_text,
            "usage": usage,
            "cache_headers": cache_headers,
            "session_id": session_id,
            "warnings": warnings,
            "patch_authority": "exact_source_spans_and_hashes_only",
            "vsa_patch_authority": False,
            "must_stage_before_apply": True,
        }

    except Exception as exc:  # noqa: BLE001
        return make_error_packet(
            "fireworks_call_failed",
            f"Fireworks API call failed: {exc}",
            repair_hint="Check FIREWORKS_API_KEY, model availability, and network connectivity.",
            next_allowed_tools=["aura_stage_patch"],
        )


def is_fireworks_available() -> bool:
    """Return True if Fireworks can be used (API key present and openai installed)."""
    if not _has_api_key():
        return False
    try:
        import openai  # noqa: F401

        return True
    except ImportError:
        return False