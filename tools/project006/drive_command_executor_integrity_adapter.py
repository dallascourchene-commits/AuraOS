#!/usr/bin/env python3
"""Integrity wrapper for the minimal Aura Drive -> DeepSeek D0 executor.

AWJ-033 repair target:
- a parent swarm request must never reach the one-call hook directly;
- only a role-distinct child produced by the fanout coordinator may carry physical
  swarm context into the single-call executor;
- child context must match a host-owned expected-child record, not merely self-assert
  a syntactically valid digest/identity;
- transport success is never promoted directly to objective success;
- refusal/provider/model identity contradictions are quarantined fail-closed.

This module deliberately does not own durable replay, Drive I/O, provider routing,
heartbeats, leases, or objective-specific verification. Those remain host/scheduler
responsibilities. The host MUST reject caller-supplied reserved `_host_*` fields before
fanout compilation and pass the persisted expected child separately at execution time.
Deterministic digests are integrity evidence, not an authentication substitute.
"""
from __future__ import annotations

import string
from collections.abc import Callable, Mapping
from typing import Any

from drive_command_executor_hook import (
    CommandHookError,
    execute_admitted_command,
)
from drive_swarm_fanout import CHILD_CONTEXT_SCHEMA, SWARM_SCHEMA
from drive_swarm_integrity import classify_model_output

_BAD_TERMINAL = {
    "RESULT_INVALID",
    "MODEL_REFUSAL",
    "PROVIDER_IDENTITY_MISMATCH",
    "MODEL_IDENTITY_MISMATCH",
    "ROLE_FANOUT_VIOLATION",
}


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256_hex(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in string.hexdigits for ch in value)
    )


def _normalize_child_context(ctx: Any) -> dict[str, Any]:
    if not isinstance(ctx, Mapping) or ctx.get("schema") != CHILD_CONTEXT_SCHEMA:
        raise CommandHookError("PHYSICAL_CHILD_CONTEXT_INVALID")

    required_text = (
        "parent_command_id",
        "parent_idempotency_key",
        "role_id",
        "worker_id",
        "child_command_id",
        "child_idempotency_key",
    )
    for key in required_text:
        if not _nonempty_text(ctx.get(key)):
            raise CommandHookError("PHYSICAL_CHILD_CONTEXT_INVALID")
    if not _sha256_hex(ctx.get("parent_payload_digest")):
        raise CommandHookError("PHYSICAL_CHILD_PAYLOAD_DIGEST_INVALID")

    target_size = ctx.get("target_size")
    ordinal = ctx.get("ordinal")
    if (
        isinstance(target_size, bool)
        or not isinstance(target_size, int)
        or target_size < 1
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 0
        or ordinal >= target_size
    ):
        raise CommandHookError("PHYSICAL_CHILD_CONTEXT_INVALID")

    return {
        "schema": CHILD_CONTEXT_SCHEMA,
        "parent_command_id": str(ctx["parent_command_id"]),
        "parent_idempotency_key": str(ctx["parent_idempotency_key"]),
        "parent_payload_digest": str(ctx["parent_payload_digest"]).lower(),
        "target_size": target_size,
        "ordinal": ordinal,
        "role_id": str(ctx["role_id"]),
        "worker_id": str(ctx["worker_id"]),
        "child_command_id": str(ctx["child_command_id"]),
        "child_idempotency_key": str(ctx["child_idempotency_key"]),
    }


def validate_single_call_route(
    raw: Mapping[str, Any],
    *,
    expected_child_context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Fail closed on parent-swarm misuse and authenticate compiled child context.

    ``expected_child_context`` must come from the host-persisted fanout transaction.
    Supplying a second copy taken from ``raw`` does not create authority; the installed
    scheduler owns this trust boundary and must keep caller-authored reserved fields out.
    """
    if not isinstance(raw, Mapping):
        raise CommandHookError("COMMAND_NOT_OBJECT")

    if raw.get("schema") == SWARM_SCHEMA:
        raise CommandHookError("PHYSICAL_SWARM_PARENT_REQUIRES_FANOUT_COORDINATOR")

    top_target = raw.get("target_size")
    if top_target is not None:
        if isinstance(top_target, bool) or not isinstance(top_target, int) or top_target < 1:
            raise CommandHookError("INVALID_TARGET_SIZE")
        if top_target > 1 and "_host_child_context" not in raw:
            raise CommandHookError("PHYSICAL_SWARM_PARENT_REQUIRES_FANOUT_COORDINATOR")

    ctx = raw.get("_host_child_context")
    if ctx is None:
        if expected_child_context is not None:
            raise CommandHookError("PHYSICAL_CHILD_CONTEXT_MISSING")
        return None

    if expected_child_context is None:
        raise CommandHookError("PHYSICAL_CHILD_EXPECTATION_REQUIRED")

    normalized = _normalize_child_context(ctx)
    expected = _normalize_child_context(expected_child_context)
    if normalized != expected:
        raise CommandHookError("PHYSICAL_CHILD_EXPECTATION_MISMATCH")

    if top_target is not None and top_target != normalized["target_size"]:
        raise CommandHookError("PHYSICAL_CHILD_TARGET_SIZE_BINDING_MISMATCH")
    if normalized["child_command_id"] != raw.get("command_id"):
        raise CommandHookError("PHYSICAL_CHILD_COMMAND_BINDING_MISMATCH")
    if normalized["child_idempotency_key"] != raw.get("idempotency_key"):
        raise CommandHookError("PHYSICAL_CHILD_IDEMPOTENCY_BINDING_MISMATCH")

    return normalized


def integrity_gate_result(
    result: Mapping[str, Any],
    *,
    expected_provider: str = "deepseek",
    expected_model: str | None = None,
) -> dict[str, Any]:
    """Convert raw transport RESULT into a fail-closed adequacy state."""
    if not isinstance(result, Mapping):
        raise CommandHookError("EXECUTOR_RESULT_NOT_OBJECT")

    out = dict(result)
    if out.get("record_type") != "RESULT":
        return out

    check = classify_model_output(
        out,
        expected_provider=expected_provider,
        expected_model=expected_model,
        physical_swarm_expected=False,
    )
    out["integrity_classification"] = check["classification"]
    out["integrity_reasons"] = list(check["reasons"])
    out["provider_observed"] = check["provider_observed"]
    out["model_observed"] = check["model_observed"]

    if check["classification"] in _BAD_TERMINAL:
        out["record_type"] = "ERROR"
        out["status"] = check["classification"]
        out["error_code"] = check["classification"]
        out["quarantine"] = True
        out["objective_adequacy"] = "FAILED"
        out["reduction_allowed"] = False
        return out

    # Transport succeeded, but objective completion/effect claims still need an
    # independent source/effect-aware validator.
    out["status"] = "RESULT_PARTIAL"
    out["objective_adequacy"] = "EVIDENCE_REQUIRED"
    out["reduction_allowed"] = False
    out["quarantine"] = False
    return out


def execute_integrity_checked_command(
    raw: Mapping[str, Any],
    *,
    executor: Callable[..., Mapping[str, Any]] = execute_admitted_command,
    expected_child_context: Mapping[str, Any] | None = None,
    expected_provider: str = "deepseek",
    expected_model: str | None = None,
    **executor_kwargs: Any,
) -> dict[str, Any]:
    """Guard route shape, execute one admitted child/single command, gate result."""
    child_context = validate_single_call_route(
        raw,
        expected_child_context=expected_child_context,
    )
    result = dict(executor(raw, **executor_kwargs))
    gated = integrity_gate_result(
        result,
        expected_provider=expected_provider,
        expected_model=expected_model,
    )

    if child_context is not None:
        gated["physical_child_context"] = child_context
        gated["parent_command_id"] = child_context["parent_command_id"]
        gated["parent_idempotency_key"] = child_context["parent_idempotency_key"]
        gated["parent_payload_digest"] = child_context["parent_payload_digest"]
        gated["ordinal"] = child_context["ordinal"]
        gated["role_id"] = child_context["role_id"]
        gated["worker_id"] = child_context["worker_id"]
        gated["child_command_id"] = child_context["child_command_id"]
        gated["child_idempotency_key"] = child_context["child_idempotency_key"]
        # One child attempt is not a physical-swarm proof. The reducer must gather
        # the exact host-persisted expected child set before claiming fanout.
        gated["physical_swarm_proven"] = False

    return gated
