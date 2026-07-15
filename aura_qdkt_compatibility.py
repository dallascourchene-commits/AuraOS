"""Opt-in P6.2 dual-read facade for existing legacy QDKT results."""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from aura_event_contracts import AppendOnlyEventStore
from aura_qdkt_compatibility_types import (
    QDKTDualReadEvidence,
    QDKTDualReadStatus,
)
from aura_qdkt_observations import QDKTObservation
from aura_qdkt_projection import project_qdkt_events
from aura_qdkt_projection_types import ProjectedQDKTEvent


def _codes(*values: str) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value}))


def _result(
    legacy_result: Mapping[str, Any],
    *,
    status: QDKTDualReadStatus,
    reason: str,
    expected_observation: QDKTObservation | None = None,
    matched_event: ProjectedQDKTEvent | None = None,
    projection_digest: str | None = None,
    finding_codes: tuple[str, ...] = (),
    expected_event_id: str = "",
    freshness_floor: float | None = None,
) -> QDKTDualReadEvidence:
    return QDKTDualReadEvidence(
        status=status,
        reason=reason,
        legacy_result=legacy_result,
        expected_observation=expected_observation,
        matched_event=matched_event,
        projection_digest=projection_digest,
        finding_codes=finding_codes,
        expected_event_id=expected_event_id,
        freshness_floor=freshness_floor,
    )


def verify_qdkt_dual_read(
    legacy_result: Mapping[str, Any],
    *,
    source_snapshot: Any,
    store: AppendOnlyEventStore,
    expected_event_id: str = "",
    freshness_floor: float | None = None,
    planning_board_ref: str = "",
    planning_history_ref: str = "",
    continuity_ref: str = "",
) -> QDKTDualReadEvidence:
    """Compare an existing legacy value with canonical evidence without replay.

    The exact caller-supplied mapping remains available through ``legacy_value``
    for every status. This function never invokes ``QuantumMerkleDAG``.
    """
    if not isinstance(legacy_result, Mapping):
        raise ValueError("legacy_result must be a mapping")
    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    if type(expected_event_id) is not str:
        raise ValueError("expected_event_id must be a string")
    expected_event_id = expected_event_id.strip()
    if freshness_floor is not None and (
        isinstance(freshness_floor, bool)
        or not isinstance(freshness_floor, (int, float))
        or not math.isfinite(float(freshness_floor))
    ):
        raise ValueError("freshness_floor must be finite")
    if freshness_floor is not None:
        freshness_floor = float(freshness_floor)

    try:
        expected = QDKTObservation.from_legacy_result(
            legacy_result,
            source_snapshot=source_snapshot,
            planning_board_ref=planning_board_ref,
            planning_history_ref=planning_history_ref,
            continuity_ref=continuity_ref,
        )
    except Exception as exc:
        code = (
            "LEGACY_RESULT_INVALID"
            if set(legacy_result) != {"root", "belief"}
            or type(legacy_result.get("root")) is not str
            or type(legacy_result.get("belief")) is not int
            else "SOURCE_OR_REFERENCE_INVALID"
        )
        status = (
            QDKTDualReadStatus.MISMATCHED
            if code == "LEGACY_RESULT_INVALID"
            else QDKTDualReadStatus.UNAVAILABLE
        )
        return _result(
            legacy_result,
            status=status,
            reason=f"expected observation unavailable:{type(exc).__name__}",
            finding_codes=(code,),
            expected_event_id=expected_event_id,
            freshness_floor=freshness_floor,
        )

    try:
        report = project_qdkt_events(store)
    except Exception as exc:
        return _result(
            legacy_result,
            status=QDKTDualReadStatus.UNAVAILABLE,
            reason=f"canonical projection unavailable:{type(exc).__name__}",
            expected_observation=expected,
            finding_codes=("PROJECTOR_FAILED",),
            expected_event_id=expected_event_id,
            freshness_floor=freshness_floor,
        )

    projection_digest = report.digest
    report_codes = _codes(*(finding.code.value for finding in report.findings))
    if report_codes:
        return _result(
            legacy_result,
            status=QDKTDualReadStatus.MISMATCHED,
            reason="canonical event store integrity is incomplete",
            expected_observation=expected,
            projection_digest=projection_digest,
            finding_codes=report_codes,
            expected_event_id=expected_event_id,
            freshness_floor=freshness_floor,
        )

    if expected_event_id:
        event_matches = tuple(
            event for event in report.events if event.event_id == expected_event_id
        )
        if not event_matches:
            return _result(
                legacy_result,
                status=QDKTDualReadStatus.UNAVAILABLE,
                reason="expected canonical event was not found",
                expected_observation=expected,
                projection_digest=projection_digest,
                finding_codes=("EXPECTED_EVENT_NOT_FOUND",),
                expected_event_id=expected_event_id,
                freshness_floor=freshness_floor,
            )
        candidate = event_matches[0]
        if candidate.observation_id != expected.observation_id:
            return _result(
                legacy_result,
                status=QDKTDualReadStatus.MISMATCHED,
                reason="expected event identifies a different observation",
                expected_observation=expected,
                projection_digest=projection_digest,
                finding_codes=("EXPECTED_EVENT_OBSERVATION_MISMATCH",),
                expected_event_id=expected_event_id,
                freshness_floor=freshness_floor,
            )
        candidates = (candidate,)
    else:
        candidates = tuple(
            event
            for event in report.events
            if event.observation_id == expected.observation_id
        )
        if not candidates:
            return _result(
                legacy_result,
                status=QDKTDualReadStatus.ADVISORY_ONLY,
                reason="legacy result is valid but no matching canonical event exists",
                expected_observation=expected,
                projection_digest=projection_digest,
                expected_event_id="",
                freshness_floor=freshness_floor,
            )

    if len(candidates) != 1:
        return _result(
            legacy_result,
            status=QDKTDualReadStatus.MISMATCHED,
            reason="canonical evidence is not unique",
            expected_observation=expected,
            projection_digest=projection_digest,
            finding_codes=("MATCHING_EVENT_NOT_UNIQUE",),
            expected_event_id=expected_event_id,
            freshness_floor=freshness_floor,
        )

    candidate = candidates[0]
    if candidate.payload_digest != expected.digest:
        return _result(
            legacy_result,
            status=QDKTDualReadStatus.MISMATCHED,
            reason="canonical payload digest differs from the expected observation",
            expected_observation=expected,
            projection_digest=projection_digest,
            finding_codes=("EXPECTED_PAYLOAD_DIGEST_MISMATCH",),
            expected_event_id=expected_event_id,
            freshness_floor=freshness_floor,
        )
    if freshness_floor is not None and candidate.created_at < freshness_floor:
        return _result(
            legacy_result,
            status=QDKTDualReadStatus.MISMATCHED,
            reason="canonical evidence is older than the declared freshness floor",
            expected_observation=expected,
            projection_digest=projection_digest,
            finding_codes=("CANONICAL_EVIDENCE_STALE",),
            expected_event_id=expected_event_id,
            freshness_floor=freshness_floor,
        )

    return _result(
        legacy_result,
        status=QDKTDualReadStatus.VERIFIED_DUAL_READ,
        reason="verified",
        expected_observation=expected,
        matched_event=candidate,
        projection_digest=projection_digest,
        expected_event_id=expected_event_id,
        freshness_floor=freshness_floor,
    )


__all__ = ["verify_qdkt_dual_read"]
