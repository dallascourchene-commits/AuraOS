"""Read-only coordinator for canonical QDKT observation events."""
from __future__ import annotations

from aura_event_contracts import AppendOnlyEventStore, stable_digest
from aura_qdkt_observations import QDKT_EVENT_TYPE
from aura_qdkt_projection_io import (
    FindingCollector,
    load_observation,
    read_event_rows,
    rebuild_envelope,
    validate_qdkt_envelope,
)
from aura_qdkt_projection_types import (
    ProjectedQDKTEvent,
    QDKTProjectionFindingCode,
    QDKTProjectionReport,
)


def project_qdkt_events(store: AppendOnlyEventStore) -> QDKTProjectionReport:
    """Verify QDKT events and sidecars without writing or repairing the store."""
    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    collector = FindingCollector()
    records = read_event_rows(store, collector)
    all_events: dict[str, tuple[int, float]] = {}
    row_digests: dict[str, str] = {}
    projected: list[ProjectedQDKTEvent] = []
    qdkt_count = 0
    ignored = 0

    for index, raw in records:
        generic = rebuild_envelope(raw)
        if generic is not None:
            all_events.setdefault(generic.event_id, (index, generic.created_at))
        if raw.get("event_type") != QDKT_EVENT_TYPE:
            ignored += 1
            continue
        qdkt_count += 1
        event_id = str(raw.get("event_id") or "")
        try:
            row_digest = stable_digest(raw)
        except (TypeError, ValueError):
            collector.add(
                QDKTProjectionFindingCode.INVALID_EVENT_RECORD,
                "QDKT event cannot be canonically digested",
                (event_id,),
            )
            continue
        previous = row_digests.get(event_id)
        if previous is not None:
            code = (
                QDKTProjectionFindingCode.DUPLICATE_EVENT_ID
                if previous == row_digest
                else QDKTProjectionFindingCode.CONFLICTING_DUPLICATE_EVENT
            )
            collector.add(
                code,
                "duplicate QDKT event ID in the event log",
                (event_id,),
            )
            continue
        row_digests[event_id] = row_digest
        envelope = validate_qdkt_envelope(raw, collector)
        if envelope is None:
            continue
        observation = load_observation(store, envelope, collector)
        if observation is None:
            continue
        projected.append(
            ProjectedQDKTEvent(
                event_id=envelope.event_id,
                observation_id=observation.observation_id,
                payload_ref=envelope.payload_ref,
                payload_digest=envelope.payload_digest,
                trace_id=envelope.trace_id,
                parent_event_ids=envelope.parent_event_ids,
                created_at=envelope.created_at,
            )
        )

    for event in projected:
        child = all_events.get(event.event_id)
        for parent_id in event.parent_event_ids:
            parent = all_events.get(parent_id)
            if parent is None:
                collector.add(
                    QDKTProjectionFindingCode.MISSING_PARENT,
                    "QDKT parent event is missing or invalid",
                    (event.event_id, parent_id),
                )
            elif child is not None and (
                parent[0] >= child[0] or parent[1] > event.created_at
            ):
                collector.add(
                    QDKTProjectionFindingCode.OUT_OF_ORDER,
                    "QDKT parent occurs after its child",
                    (event.event_id, parent_id),
                )

    findings = tuple(
        sorted(
            collector.findings,
            key=lambda item: (item.code.value, item.event_ids, item.message),
        )
    )
    events = tuple(
        sorted(projected, key=lambda item: (item.created_at, item.event_id))
    )
    return QDKTProjectionReport(events, findings, qdkt_count, ignored)


__all__ = ["project_qdkt_events"]
