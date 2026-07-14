"""Shadow-only observability wrapper for exact Aura tool calls.

The wrapper never augments the invoked callable's keyword arguments. Decision,
result, and event records are produced beside the call and may optionally be
persisted to an append-only store.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Mapping

from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DIKWPStage,
    MeasurementClass,
    ToolDecisionRecord,
    ToolResultRecord,
)

SHADOW_OBSERVABILITY_VERSION = "AURA_SHADOW_TOOL_OBSERVABILITY_V1"


@dataclass(frozen=True)
class ObservedToolCall:
    value: Any
    decision: ToolDecisionRecord
    result: ToolResultRecord
    decision_event: AuraEventEnvelope
    result_event: AuraEventEnvelope
    persisted_event_ids: tuple[str, ...]


def invoke_tool_shadow(
    tool: Callable[..., Any],
    *,
    tool_kwargs: Mapping[str, Any],
    decision: ToolDecisionRecord,
    purpose_digest: str,
    actor_id: str = "aura.orchestrator",
    arena_id: str = "",
    store: AppendOnlyEventStore | None = None,
    now: Callable[[], float] = time.time,
) -> ObservedToolCall:
    """Invoke ``tool`` with exactly ``tool_kwargs`` and emit sidecar records."""
    kwargs = dict(tool_kwargs)
    started = float(now())
    value: Any = None
    status = "SUCCEEDED"
    error_class = ""
    caught: BaseException | None = None
    try:
        value = tool(**kwargs)
        if isinstance(value, Mapping) and (
            value.get("ok") is False or value.get("status") in {"FAILED", "DENIED", "ERROR"}
        ):
            status = str(value.get("status") or "FAILED").upper()
            error_class = str(value.get("error_class") or value.get("error") or "")
    except BaseException as exc:  # preserve exact caller-visible exception behavior
        caught = exc
        status = "FAILED"
        error_class = type(exc).__name__
        value = {"raised": type(exc).__name__}
    finished = float(now())

    result = ToolResultRecord.create(
        decision_id=decision.decision_id,
        tool_id=decision.tool_id,
        status=status,
        output=value,
        error_class=error_class,
        started_at=started,
        finished_at=finished,
    )

    decision_payload_ref = f"inline:{decision.decision_id}"
    result_payload_ref = f"inline:{result.result_id}"
    if store is not None:
        decision_ref = store.store_payload(decision.to_dict(), kind="tool-decision", created_at=started)
        result_ref = store.store_payload(result.to_dict(), kind="tool-result", created_at=finished)
        decision_payload_ref = decision_ref.ref_id
        result_payload_ref = result_ref.ref_id

    decision_event = AuraEventEnvelope.create(
        trace_id=decision.trace_id,
        event_type="TOOL_DECISION_RECORDED",
        actor_id=actor_id,
        actor_type=ActorType.AURA,
        arena_id=arena_id,
        board_id=decision.board_id,
        node_id=decision.node_id,
        purpose_digest=purpose_digest,
        dikwp_stage=DIKWPStage.INFORMATION,
        payload_ref=decision_payload_ref,
        payload_digest=decision.decision_id,
        proposal_only=True,
        measurement_classes={"confidence": MeasurementClass.MODEL_ESTIMATED},
        confidence=decision.confidence_estimate,
        created_at=started,
    )
    result_event = AuraEventEnvelope.create(
        trace_id=decision.trace_id,
        parent_event_ids=(decision_event.event_id,),
        event_type="TOOL_RESULT_RECORDED",
        actor_id=decision.tool_id,
        actor_type=ActorType.TOOL,
        arena_id=arena_id,
        board_id=decision.board_id,
        node_id=decision.node_id,
        purpose_digest=purpose_digest,
        dikwp_stage=DIKWPStage.DATA,
        payload_ref=result_payload_ref,
        payload_digest=result.result_id,
        proposal_only=True,
        created_at=finished,
    )

    persisted: list[str] = []
    if store is not None:
        if store.append(decision_event):
            persisted.append(decision_event.event_id)
        if store.append(result_event):
            persisted.append(result_event.event_id)

    observed = ObservedToolCall(
        value=value,
        decision=decision,
        result=result,
        decision_event=decision_event,
        result_event=result_event,
        persisted_event_ids=tuple(persisted),
    )
    if caught is not None:
        raise caught
    return observed
