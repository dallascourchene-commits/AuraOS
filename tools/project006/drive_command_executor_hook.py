"""Minimal admitted Aura Drive command -> existing DeepSeek egress hook.

This is deliberately not a Drive client, scheduler, durable execution ledger, policy
engine, or provider registry. The installed inbox owns ingestion/replay state, a
host-owned policy/cost gate owns effect admission, and the installed bus writer owns
Drive output. This module validates one already-admitted D0 command and adapts an
exactly admitted internal DeepSeek effect to Aura's existing canonical egress.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Callable, Mapping
from typing import Any, Protocol

HOOK_VERSION = "AURA_DRIVE_DEEPSEEK_D0_HOOK_V1"
COMMAND_SCHEMA = "AuraCommandEnvelopeV1-candidate"
AUTHORIZED_QUEUE_STATE = "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND"
EXECUTOR_ID = "AURA_CANONICAL_EGRESS_DEEPSEEK_D0_V1"
EFFECT_CLASS = "INTERNAL_DEEPSEEK_PROVIDER_INFERENCE_EGRESS"
EFFECT_ADMISSION_VERSION = "P0_D_EFFECT_ADMISSION_V1"
REQUIRED_CAPABILITY = "EXISTING_AURA_DEEPSEEK_EXECUTOR"

_MAX_ID_CHARS = 256
_MAX_REF_CHARS = 1024
_MAX_OBJECTIVE_CHARS = 128_000
_MAX_INTENT_ITEMS = 128
_MAX_INTENT_ITEM_CHARS = 4096

_FORBIDDEN_CONTROL_KEYS = frozenset(
    {
        "api_key",
        "api_keys",
        "authorization",
        "bearer",
        "access_token",
        "refresh_token",
        "password",
        "secret",
        "credential",
        "credentials",
        "provider_url",
        "base_url",
        "endpoint",
        "host",
        "hostname",
        "route_ref",
        "route",
        "lease",
        "fence",
        "currentness",
        "provider",
        "provider_name",
        "model",
        "model_id",
        "fencing_token",
        "lease_generation",
        "currentness_ref",
        "validation_receipt_ref",
        # Effect admission is a host-owned input to execute_admitted_command().
        # The Drive command cannot self-authorize by supplying these fields.
        "effect_admission",
        "effect_admission_ref",
        "authority_admission",
        "authority_admission_ref",
        "provider_cost_admission",
        "provider_cost_admission_ref",
    }
)

_EFFECT_ADMISSION_KEYS = frozenset(
    {
        "admission_version",
        "command_digest",
        "authority_ref",
        "workspace_scope",
        "executor_id",
        "effect_class",
        "currentness",
        "authority_decision",
        "cost_decision",
        "policy_ref",
        "authority_admission_ref",
        "provider_cost_admission_ref",
    }
)

_BROAD_EXTERNAL_DENIALS = (
    "no external communication",
    "no external communications",
    "no network communication",
    "no network communications",
    "no network access",
    "no external calls",
    "no provider calls",
    "no api calls",
)


class CommandHookError(ValueError):
    """Typed fail-closed command/hook admission failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _Executor(Protocol):
    """Narrow structural type matching the existing ExternalLLM.generate API."""

    provider: str
    model: str

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
    ) -> tuple[str | None, str | None, float]: ...


EffectAdmissionProvider = Callable[
    [Mapping[str, Any], str, str, str], Mapping[str, Any]
]


def _canonical_digest(value: Any) -> str:
    """Return deterministic SHA-256 over canonical JSON."""
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _require_text(name: str, value: Any, *, maximum: int) -> str:
    """Require bounded nonempty text without hidden C0 controls."""
    if not isinstance(value, str):
        raise CommandHookError(f"INVALID_{name.upper()}")
    if not value or len(value) > maximum:
        raise CommandHookError(f"INVALID_{name.upper()}")
    if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in value):
        raise CommandHookError(f"INVALID_{name.upper()}")
    return value


def _intent_list(name: str, value: Any) -> tuple[str, ...]:
    """Normalize a bounded intent list while preserving order and text."""
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or len(value) > _MAX_INTENT_ITEMS:
        raise CommandHookError(f"INVALID_{name.upper()}")
    return tuple(
        _require_text(name, item, maximum=_MAX_INTENT_ITEM_CHARS)
        for item in value
    )


def _reject_structured_provider_control(value: Any) -> None:
    """Reject caller-controlled provider, execution, or admission authority keys."""
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).strip().lower()
            if key in _FORBIDDEN_CONTROL_KEYS:
                raise CommandHookError("DRIVE_PROVIDER_CONTROL_FORBIDDEN")
            _reject_structured_provider_control(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_structured_provider_control(child)


def _has_explicit_deepseek_exception(text: str) -> bool:
    """Recognize a narrow explicit exception to a broad external-effect denial."""
    low = " ".join(text.casefold().split())
    return (
        "deepseek" in low
        and ("except" in low or "beyond" in low or "other than" in low)
        and ("authorized" in low or "required" in low)
    )


def _validate_intent_consistency(negative_intent: tuple[str, ...]) -> None:
    """Fail closed when command prohibitions contradict required DeepSeek egress."""
    for item in negative_intent:
        low = " ".join(item.casefold().split())
        if any(low.startswith(prefix) for prefix in _BROAD_EXTERNAL_DENIALS):
            if not _has_explicit_deepseek_exception(low):
                raise CommandHookError(
                    "INTENT_CONTRADICTION_EXTERNAL_EGRESS_FORBIDDEN"
                )


def _requested_capability(value: Any) -> str:
    """Extract the command capability ceiling from the supported candidate shape."""
    if isinstance(value, Mapping):
        value = value.get("semantic_id_or_alias")
    capability = _require_text(
        "requested_capability", value, maximum=_MAX_REF_CHARS
    )
    if capability != REQUIRED_CAPABILITY:
        raise CommandHookError("REQUESTED_CAPABILITY_MISMATCH")
    return capability


def validate_admitted_command(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one already-admitted owner-bound ChatGPT/D0 command.

    Upstream remains responsible for proving current owner authority and durable
    idempotency state. This adapter preserves policy operands and fails closed on
    contradictory intent, capability widening, or caller-supplied effect authority.
    """
    if not isinstance(raw, Mapping):
        raise CommandHookError("COMMAND_NOT_OBJECT")
    _reject_structured_provider_control(raw)

    if raw.get("schema") != COMMAND_SCHEMA:
        raise CommandHookError("UNSUPPORTED_COMMAND_SCHEMA")
    if raw.get("queue_state") != AUTHORIZED_QUEUE_STATE:
        raise CommandHookError("COMMAND_NOT_DISPATCH_READY")
    if raw.get("message_authorized") is not True:
        raise CommandHookError("MESSAGE_NOT_AUTHORIZED")
    if raw.get("execution_authorized") is not True:
        raise CommandHookError("EXECUTION_NOT_AUTHORIZED")

    command_id = _require_text(
        "command_id", raw.get("command_id"), maximum=_MAX_ID_CHARS
    )
    idempotency_key = _require_text(
        "idempotency_key", raw.get("idempotency_key"), maximum=_MAX_ID_CHARS
    )
    authority_ref = _require_text(
        "authority_ref", raw.get("authority_ref"), maximum=_MAX_REF_CHARS
    )

    transport = raw.get("transport")
    if not isinstance(transport, Mapping) or transport.get("type") != "CHATGPT":
        raise CommandHookError("UNSUPPORTED_TRANSPORT_FOR_MINIMAL_BRIDGE")

    objective = raw.get("objective")
    if not isinstance(objective, Mapping):
        raise CommandHookError("INVALID_OBJECTIVE")
    objective_text = _require_text(
        "objective_text", objective.get("text"), maximum=_MAX_OBJECTIVE_CHARS
    )
    if objective.get("requested_effect") != "D0":
        raise CommandHookError("MINIMAL_BRIDGE_D0_ONLY")

    positive_intent = _intent_list(
        "positive_intent", objective.get("positive_intent")
    )
    negative_intent = _intent_list(
        "negative_intent", objective.get("negative_intent")
    )
    success_criteria = _intent_list(
        "success_criteria", objective.get("success_criteria")
    )
    _validate_intent_consistency(negative_intent)

    constraints = raw.get("constraints")
    if not isinstance(constraints, Mapping):
        raise CommandHookError("INVALID_CONSTRAINTS")
    workspace_scope = _require_text(
        "workspace_scope", constraints.get("workspace_scope"), maximum=_MAX_REF_CHARS
    )
    if workspace_scope != "AURA_DRIVE_ONLY":
        raise CommandHookError("MINIMAL_BRIDGE_WORKSPACE_SCOPE_MISMATCH")

    capability = _requested_capability(raw.get("requested_capability"))

    human_disposition = raw.get("human_disposition")
    if human_disposition is not None:
        if not isinstance(human_disposition, Mapping):
            raise CommandHookError("INVALID_HUMAN_DISPOSITION")
        if human_disposition.get("required") is True:
            raise CommandHookError("HUMAN_DISPOSITION_REQUIRED")

    target_ref = objective.get("target_ref")
    if target_ref is not None:
        target_ref = _require_text(
            "target_ref", target_ref, maximum=_MAX_REF_CHARS
        )

    return {
        "schema": COMMAND_SCHEMA,
        "queue_state": AUTHORIZED_QUEUE_STATE,
        "command_id": command_id,
        "idempotency_key": idempotency_key,
        "authority_ref": authority_ref,
        "transport_type": "CHATGPT",
        "objective_text": objective_text,
        "target_ref": target_ref,
        "requested_effect": "D0",
        "positive_intent": positive_intent,
        "negative_intent": negative_intent,
        "success_criteria": success_criteria,
        "workspace_scope": workspace_scope,
        "requested_capability": capability,
    }


def _validate_effect_admission(
    raw: Mapping[str, Any],
    *,
    command: Mapping[str, Any],
    request_digest: str,
) -> dict[str, str]:
    """Validate a host-owned authority+cost admission receipt for this exact effect."""
    if not isinstance(raw, Mapping):
        raise CommandHookError("EFFECT_ADMISSION_INVALID")
    if set(raw) != _EFFECT_ADMISSION_KEYS:
        raise CommandHookError("EFFECT_ADMISSION_SHAPE_INVALID")

    normalized = {
        key: _require_text(
            key,
            raw.get(key),
            maximum=_MAX_REF_CHARS,
        )
        for key in _EFFECT_ADMISSION_KEYS
    }
    expected = {
        "admission_version": EFFECT_ADMISSION_VERSION,
        "command_digest": request_digest,
        "authority_ref": str(command["authority_ref"]),
        "workspace_scope": str(command["workspace_scope"]),
        "executor_id": EXECUTOR_ID,
        "effect_class": EFFECT_CLASS,
        "currentness": "CURRENT",
        "authority_decision": "ALLOW",
        "cost_decision": "ALLOW",
    }
    for key, expected_value in expected.items():
        if normalized[key] != expected_value:
            if key == "currentness":
                raise CommandHookError("EFFECT_ADMISSION_NOT_CURRENT")
            if key == "authority_decision":
                raise CommandHookError("AUTHORITY_ADMISSION_NOT_ALLOW")
            if key == "cost_decision":
                raise CommandHookError("PROVIDER_COST_ADMISSION_NOT_ALLOW")
            raise CommandHookError("EFFECT_ADMISSION_BINDING_MISMATCH")
    return normalized


def _build_prompt(command: Mapping[str, Any]) -> str:
    """Compile the bounded objective while retaining accepted negative intent."""
    target = command.get("target_ref")
    target_line = f"\nTARGET_REF: {target}" if target else ""
    negative = command.get("negative_intent") or ()
    negative_block = ""
    if negative:
        negative_block = "\nNEGATIVE_INTENT:\n" + "\n".join(
            f"- {item}" for item in negative
        )
    return (
        "You are Aura's external DeepSeek development worker. Complete only the "
        "bounded D0 task below. Do not claim file, host, provider, deployment, or "
        "other effects you did not actually perform. Do not request or expose "
        "credentials. Return a concise development result suitable for the caller.\n\n"
        f"OBJECTIVE:\n{command['objective_text']}"
        f"{target_line}{negative_block}"
    )


def _default_executor_factory() -> _Executor:
    """Construct the existing canonical egress pinned to DeepSeek without fallback."""
    from aura_llm_egress import ExternalLLM

    return ExternalLLM(
        provider="deepseek",
        model="coding",
        task="drive_command_bridge",
        aspect="minimal_d0_executor",
        allow_provider_fallback=False,
    )


def _record_base(
    command: Mapping[str, Any],
    request_digest: str,
    admission: Mapping[str, str],
) -> dict[str, Any]:
    """Build safe lineage fields shared by ACK/RESULT/ERROR records."""
    return {
        "hook_version": HOOK_VERSION,
        "command_id": command["command_id"],
        "idempotency_key": command["idempotency_key"],
        "authority_ref": command["authority_ref"],
        "requested_effect": "D0",
        "requested_capability": command["requested_capability"],
        "executor_id": EXECUTOR_ID,
        "effect_class": EFFECT_CLASS,
        "execution_request_digest": request_digest,
        "effect_admission_digest": _canonical_digest(admission),
        "authority_admission_ref": admission["authority_admission_ref"],
        "provider_cost_admission_ref": admission[
            "provider_cost_admission_ref"
        ],
        # Existing ExternalLLM exposes no owner-issued attempt identity.
        "execution_identity": "UNKNOWN",
    }


def execute_admitted_command(
    raw: Mapping[str, Any],
    *,
    executor_factory: Callable[[], _Executor] = _default_executor_factory,
    emit_ack: Callable[[Mapping[str, Any]], None] | None = None,
    effect_admission: EffectAdmissionProvider | None = None,
) -> dict[str, Any]:
    """Execute one admitted D0 command after host-owned policy and cost admission.

    The host must reconcile durable execution state outside this module. A caller
    cannot self-authorize through Drive fields: the separate ``effect_admission``
    callback must return a current receipt bound to this exact command digest,
    workspace, executor, effect class, owner authority, and provider-cost decision.
    Only then may ACK be emitted and the existing DeepSeek egress be constructed.
    """
    command = validate_admitted_command(raw)
    if emit_ack is None:
        raise CommandHookError("ACK_SINK_REQUIRED")
    if effect_admission is None:
        raise CommandHookError("EFFECT_ADMISSION_REQUIRED")

    request_digest = _canonical_digest(command)
    try:
        raw_admission = effect_admission(
            command,
            request_digest,
            EXECUTOR_ID,
            EFFECT_CLASS,
        )
    except CommandHookError:
        raise
    except Exception as exc:
        raise CommandHookError("EFFECT_ADMISSION_FAILED") from exc
    admission = _validate_effect_admission(
        raw_admission,
        command=command,
        request_digest=request_digest,
    )

    base = _record_base(command, request_digest, admission)
    ack = {
        **base,
        "record_type": "ACK",
        "status": "EXECUTOR_CALLBACK_ACCEPTED",
    }
    try:
        emit_ack(ack)
    except Exception as exc:
        raise CommandHookError("ACK_EMIT_FAILED") from exc

    try:
        executor = executor_factory()
    except Exception as exc:
        return {
            **base,
            "record_type": "ERROR",
            "status": "EXECUTOR_UNAVAILABLE",
            "error_code": "DEEPSEEK_EXECUTOR_UNAVAILABLE",
            "error_type": type(exc).__name__,
        }

    try:
        text, error, latency = executor.generate(
            _build_prompt(command),
            max_tokens=900,
            temperature=0.0,
            pre_egress=False,
            resonance_egress=False,
            context_crush=False,
            call_type="drive_command_d0",
        )
    except Exception as exc:
        return {
            **base,
            "record_type": "ERROR",
            "status": "EXECUTOR_FAILED",
            "error_code": "DEEPSEEK_EXECUTOR_FAILURE",
            "error_type": type(exc).__name__,
        }

    if error or not text:
        return {
            **base,
            "record_type": "ERROR",
            "status": "EXECUTOR_FAILED",
            "error_code": "DEEPSEEK_EXECUTOR_FAILURE",
            "error_type": "PROVIDER_OR_EMPTY_RESULT",
        }

    safe_text = str(text)
    return {
        **base,
        "record_type": "RESULT",
        "status": "OK",
        "provider": str(getattr(executor, "provider", "deepseek")),
        "model": str(getattr(executor, "model", "UNKNOWN")),
        "result_digest": hashlib.sha256(
            safe_text.encode("utf-8")
        ).hexdigest(),
        "latency_ms": max(0, int(float(latency) * 1000)),
        "result": safe_text,
    }


def _emit_stdout(record: Mapping[str, Any]) -> None:
    """Emit one deterministic JSONL record."""
    print(
        json.dumps(dict(record), sort_keys=True, ensure_ascii=False),
        flush=True,
    )


def _safe_command_id(raw: Any) -> str | None:
    """Return a bounded command ID for top-level error lineage when available."""
    if isinstance(raw, Mapping):
        value = raw.get("command_id")
        if isinstance(value, str) and value and len(value) <= _MAX_ID_CHARS:
            return value
    return None


def main() -> int:
    """Run one JSON-stdin command and emit ACK plus one terminal JSONL record."""
    raw: Any = None
    try:
        raw = json.load(sys.stdin)
        terminal = execute_admitted_command(raw, emit_ack=_emit_stdout)
    except CommandHookError as exc:
        _emit_stdout(
            {
                "hook_version": HOOK_VERSION,
                "record_type": "ERROR",
                "status": "ADMISSION_REJECTED",
                "command_id": _safe_command_id(raw),
                "execution_identity": "UNKNOWN",
                "error_code": exc.code,
            }
        )
        return 2
    except Exception as exc:
        _emit_stdout(
            {
                "hook_version": HOOK_VERSION,
                "record_type": "ERROR",
                "status": "HOOK_INTERNAL_FAILURE",
                "command_id": _safe_command_id(raw),
                "execution_identity": "UNKNOWN",
                "error_code": "HOOK_INTERNAL_FAILURE",
                "error_type": type(exc).__name__,
            }
        )
        return 3

    _emit_stdout(terminal)
    return 0 if terminal.get("record_type") == "RESULT" else 4


if __name__ == "__main__":
    raise SystemExit(main())
