from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from host_receipt_registry import (
    HostExecutionPlan,
    HostReceiptError,
    HostReceiptRegistry,
    RECEIPT_SCHEMA,
    normalize_child_identity,
)


class HostExecutionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _hex64(name: str, value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text):
        raise HostExecutionError(f"{name.upper()}_INVALID")
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _plan_child(registry: HostReceiptRegistry, plan: HostExecutionPlan, child_identity: Mapping[str, Any]) -> dict[str, Any]:
    registry.assert_owned_plan(plan)
    child = normalize_child_identity(child_identity)
    expected = {str(c["command_id"]): normalize_child_identity(c) for c in plan.children}.get(child["command_id"])
    if expected != child:
        raise HostExecutionError("CHILD_NOT_IN_HOST_PLAN")
    return child


def execute_observed_child(
    *,
    registry: HostReceiptRegistry,
    plan: HostExecutionPlan,
    child_identity: Mapping[str, Any],
    parent_command_id: str,
    cohort_id: str,
    work_order_id: str,
    route_admission_digest: str,
    expected_provider: str,
    expected_model: str,
    executor: Any,
    prompt: str,
    generate_kwargs: Mapping[str, Any] | None = None,
    observed_at: Callable[[], str] = _now,
) -> dict[str, Any]:
    """Record STARTED before generate and COMMITTED/FAILED after the observed call."""
    child = _plan_child(registry, plan, child_identity)
    route_digest = _hex64("route_admission_digest", route_admission_digest)
    provider = str(expected_provider or "").strip().casefold()
    model = str(expected_model or "").strip().casefold()
    if not provider:
        raise HostExecutionError("EXPECTED_PROVIDER_REQUIRED")
    if not model:
        raise HostExecutionError("EXPECTED_MODEL_REQUIRED")
    observed_provider = str(getattr(executor, "provider", "") or "").strip().casefold()
    observed_model = str(getattr(executor, "model", "") or "").strip().casefold()
    if observed_provider != provider:
        raise HostExecutionError("EXECUTOR_PROVIDER_ROUTE_MISMATCH")
    if observed_model != model:
        raise HostExecutionError("EXECUTOR_MODEL_ROUTE_MISMATCH")

    request_id = "PRQ-" + _sha(f"{plan.plan_digest}|{child['attempt_id']}|{route_digest}")[:32]
    receipt_stem = _sha(f"{plan.plan_digest}|{child['attempt_id']}|{request_id}")[:32]
    common = {
        "receipt_schema": RECEIPT_SCHEMA,
        "command_id": child["command_id"],
        "idempotency_key": child["idempotency_key"],
        "parent_command_id": str(parent_command_id),
        "fanout_id": child["fanout_id"],
        "cohort_id": str(cohort_id),
        "attempt_id": child["attempt_id"],
        "worker_id": child["worker_id"],
        "worker_instance_id": f"{child['worker_id']}@{registry.host_instance_id}",
        "role_id": child["role_id"],
        "role_instance_id": child["role_instance_id"],
        "objective_id": child["objective_id"],
        "work_order_id": str(work_order_id),
        "provider": provider,
        "model": model,
        "source_generation": child["source_generation"],
        "command_digest": child["command_digest"],
        "parent_payload_digest": child["parent_payload_digest"],
        "plan_digest": child["plan_digest"],
        "manifest_digest": child["manifest_digest"],
        "route_admission_digest": route_digest,
        "ordinal": child["ordinal"],
        "effect_kind": "MODEL_OUTPUT_ONLY",
        "provider_request_id": request_id,
        "reconcile_key": f"{child['attempt_id']}::{request_id}",
        "host_instance_id": registry.host_instance_id,
        "executor_id": registry.executor_id,
    }
    registry.record({
        **common,
        "receipt_id": f"START-{receipt_stem}",
        "artifact_identity": "PENDING",
        "result_digest": "NONE",
        "observed_at": observed_at(),
        "execution_state": "STARTED",
    })

    try:
        text, error, latency = executor.generate(prompt, **dict(generate_kwargs or {}))
    except Exception as exc:
        registry.record({
            **common,
            "receipt_id": f"FAIL-{receipt_stem}",
            "artifact_identity": f"ERROR:{type(exc).__name__}",
            "result_digest": _sha(type(exc).__name__),
            "observed_at": observed_at(),
            "execution_state": "FAILED",
        })
        raise HostExecutionError("PROVIDER_CALL_FAILED") from exc

    if error or not text:
        detail = str(error or "EMPTY_RESULT")
        registry.record({
            **common,
            "receipt_id": f"FAIL-{receipt_stem}",
            "artifact_identity": "ERROR:PROVIDER_OR_EMPTY_RESULT",
            "result_digest": _sha(detail),
            "observed_at": observed_at(),
            "execution_state": "FAILED",
        })
        raise HostExecutionError("PROVIDER_OR_EMPTY_RESULT")

    safe_text = str(text)
    result_digest = _sha(safe_text)
    committed = registry.record({
        **common,
        "receipt_id": f"COMMIT-{receipt_stem}",
        "artifact_identity": f"RESULT:{result_digest}",
        "result_digest": result_digest,
        "observed_at": observed_at(),
        "execution_state": "COMMITTED",
    })
    return {
        "record_type": "RESULT",
        "status": "RESULT_PARTIAL",
        "command_id": child["command_id"],
        "idempotency_key": child["idempotency_key"],
        "parent_command_id": parent_command_id,
        "parent_payload_digest": child["parent_payload_digest"],
        "ordinal": child["ordinal"],
        "role_id": child["role_id"],
        "worker_id": child["worker_id"],
        "attempt_id": child["attempt_id"],
        "provider_request_id": request_id,
        "provider": provider,
        "model": model,
        "route_provider": provider,
        "route_model": model,
        "route_admission_digest": route_digest,
        "result_digest": result_digest,
        "result": safe_text,
        "latency_ms": max(0, int(float(latency) * 1000)),
        "host_receipt_id": committed["receipt_id"],
    }
