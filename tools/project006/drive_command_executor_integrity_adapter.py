#!/usr/bin/env python3
"""Fail-closed AWJ-033 integrity wrapper with pre-effect exact route admission."""
from __future__ import annotations

import string
from collections.abc import Callable, Mapping
from typing import Any

from drive_command_executor_hook import (
    CommandHookError,
    EFFECT_CLASS,
    EXECUTOR_ID,
    _canonical_digest,
    execute_admitted_command,
    validate_admitted_command,
)
from drive_route_admission import (
    RouteAdmissionError,
    build_exact_executor,
    prepare_exact_executor,
    validate_effect_route_binding,
    validate_route_admission,
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


def _as_hook_error(exc: RouteAdmissionError) -> CommandHookError:
    return CommandHookError(exc.code)


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
    """Reject parent swarm routing and bind child context to host expectations."""
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
    expected_provider: str,
    expected_model: str,
) -> dict[str, Any]:
    """Convert transport output into a fail-closed adequacy state."""
    if not _nonempty_text(expected_provider):
        raise CommandHookError("EXPECTED_PROVIDER_REQUIRED")
    if not _nonempty_text(expected_model):
        raise CommandHookError("EXPECTED_MODEL_REQUIRED")
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
    route_admission: Mapping[str, Any] | None = None,
    route_executor_factory: Callable[[str, str], Any] = build_exact_executor,
    expected_provider: str | None = None,
    expected_model: str | None = None,
    test_only_allow_executor_override: bool = False,
    **executor_kwargs: Any,
) -> dict[str, Any]:
    """Validate route/effect admission, ACK, then attest executor before generate()."""
    child_context = validate_single_call_route(
        raw,
        expected_child_context=expected_child_context,
    )
    command = validate_admitted_command(raw)
    command_digest = _canonical_digest(command)

    route_provider = str((route_admission or {}).get("provider") or "")
    route_model = str((route_admission or {}).get("model") or "")
    if (
        expected_provider is not None
        and route_provider.casefold() != str(expected_provider).strip().casefold()
    ):
        raise CommandHookError("EXPECTED_PROVIDER_ROUTE_MISMATCH")
    if (
        expected_model is not None
        and route_model.casefold() != str(expected_model).strip().casefold()
    ):
        raise CommandHookError("EXPECTED_MODEL_ROUTE_MISMATCH")

    try:
        route = validate_route_admission(
            route_admission,
            command_digest=command_digest,
            executor_id=EXECUTOR_ID,
            effect_class=EFFECT_CLASS,
            expected_provider=route_provider,
            expected_model=route_model,
        )
    except RouteAdmissionError as exc:
        raise _as_hook_error(exc) from exc

    if executor is not execute_admitted_command and not test_only_allow_executor_override:
        raise CommandHookError("UNVERIFIED_EXECUTOR_OVERRIDE_FORBIDDEN")
    if "executor_factory" in executor_kwargs:
        raise CommandHookError("ROUTE_EXECUTOR_FACTORY_OVERRIDE_FORBIDDEN")

    effect_admission = executor_kwargs.pop("effect_admission", None)
    if effect_admission is None:
        raise CommandHookError("EFFECT_ADMISSION_REQUIRED")

    def bound_effect_admission(command_arg, digest, executor_id, effect_class):
        admission = effect_admission(
            command_arg,
            digest,
            executor_id,
            effect_class,
        )
        try:
            validate_effect_route_binding(route, admission)
        except RouteAdmissionError as exc:
            raise _as_hook_error(exc) from exc
        return admission

    route_factory_error: list[str] = []

    # The one-call hook performs effect admission -> ACK -> executor_factory -> generate.
    # This closure attests the exact resolved provider/model during executor_factory,
    # so a mismatch fails after ACK but strictly before generate/provider effect.
    def attested_executor_factory():
        try:
            return prepare_exact_executor(route, factory=route_executor_factory)
        except RouteAdmissionError as exc:
            route_factory_error.append(exc.code)
            raise _as_hook_error(exc) from exc

    result = dict(
        executor(
            raw,
            executor_factory=attested_executor_factory,
            effect_admission=bound_effect_admission,
            **executor_kwargs,
        )
    )
    if route_factory_error:
        # The lower hook conservatively converts factory exceptions to
        # EXECUTOR_UNAVAILABLE. Preserve the exact pre-effect route failure here;
        # generate() was never reached.
        code = route_factory_error[0]
        result["record_type"] = "ERROR"
        result["status"] = code
        result["error_code"] = code
        result["pre_effect_route_failure"] = True
        result["reduction_allowed"] = False

    gated = integrity_gate_result(
        result,
        expected_provider=route["provider"],
        expected_model=route["model"],
    )

    gated["route_admission_digest"] = _canonical_digest(route)
    gated["route_provider"] = route["provider"]
    gated["route_model"] = route["model"]
    gated["route_class"] = route["route_class"]
    gated["route_generation"] = route["route_generation"]
    gated["route_escalation_decision"] = route["escalation_decision"]
    gated["route_escalation_ref"] = route["escalation_ref"]

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
        gated["physical_swarm_proven"] = False

    return gated
