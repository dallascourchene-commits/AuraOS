from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from drive_swarm_route_integrity import validate_route_bound_physical_swarm_receipts
from host_receipt_registry import HostExecutionPlan, HostReceiptError, HostReceiptRegistry, normalize_child_identity


class HostSwarmReductionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_registry_backed_physical_swarm(
    *,
    registry: HostReceiptRegistry,
    plan: HostExecutionPlan,
    model_outputs: Mapping[str, Mapping[str, Any]],
    expected_provider: str,
    expected_model: str,
    route_bound_validator: Callable[..., Mapping[str, Any]] = validate_route_bound_physical_swarm_receipts,
) -> dict[str, Any]:
    """Resolve exact host evidence internally; no caller receipt-list parameter exists."""
    registry.assert_owned_plan(plan)
    provider = str(expected_provider or "").strip().casefold()
    model = str(expected_model or "").strip().casefold()
    if not provider:
        raise HostSwarmReductionError("EXPECTED_PROVIDER_REQUIRED")
    if not model:
        raise HostSwarmReductionError("EXPECTED_MODEL_REQUIRED")
    if len(model_outputs) != plan.target_size:
        raise HostSwarmReductionError("MODEL_OUTPUT_COUNT_MISMATCH")

    leaves: list[dict[str, Any]] = []
    projection_digests: list[str] = []
    for child_raw in plan.children:
        child = normalize_child_identity(child_raw)
        try:
            projection = registry.resolve(
                plan,
                child,
                required_evidence=("provider_request_id", "result_digest", "route_admission_digest"),
            )
            registry.assert_owned_projection(projection)
        except HostReceiptError as exc:
            raise HostSwarmReductionError(exc.code) from exc
        host = dict(projection.records[-1])
        if host["provider"].casefold() != provider:
            raise HostSwarmReductionError("HOST_PROVIDER_MISMATCH")
        if host["model"].casefold() != model:
            raise HostSwarmReductionError("HOST_MODEL_MISMATCH")
        output = model_outputs.get(child["command_id"])
        if not isinstance(output, Mapping):
            raise HostSwarmReductionError("MODEL_OUTPUT_MISSING")
        text = str(output.get("result") or "")
        if not text:
            raise HostSwarmReductionError("MODEL_OUTPUT_EMPTY")
        if _sha(text) != host["result_digest"]:
            raise HostSwarmReductionError("MODEL_OUTPUT_RESULT_DIGEST_MISMATCH")
        leaves.append({
            "record_type": "RESULT",
            "status": "RESULT_PARTIAL",
            "parent_command_id": plan.parent_command_id,
            "parent_payload_digest": child["parent_payload_digest"],
            "command_id": child["command_id"],
            "child_command_id": child["command_id"],
            "idempotency_key": child["idempotency_key"],
            "child_idempotency_key": child["idempotency_key"],
            "ordinal": child["ordinal"],
            "role_id": child["role_id"],
            "worker_id": child["worker_id"],
            "attempt_id": child["attempt_id"],
            "provider_request_id": host["provider_request_id"],
            "provider": host["provider"],
            "model": host["model"],
            "route_provider": host["provider"],
            "route_model": host["model"],
            "route_admission_digest": host["route_admission_digest"],
            "result": text,
        })
        projection_digests.append(projection.projection_digest)

    out = dict(route_bound_validator(
        parent_command_id=plan.parent_command_id,
        target_size=plan.target_size,
        fanout_manifest=plan.manifest,
        child_receipts=leaves,
        expected_provider=provider,
        expected_model=model,
    ))
    out["registry_authority_proven"] = True
    out["host_execution_plan_digest"] = plan.plan_digest
    out["host_receipt_projection_digests"] = projection_digests
    return out
