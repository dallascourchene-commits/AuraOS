"""Opt-in P6.2 dual-read evidence for an already-produced legacy QDKT result."""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from aura_event_contracts import AppendOnlyEventStore, stable_digest
from aura_qdkt_compatibility_types import (
    QDKTCompatibilityFinding,
    QDKTCompatibilityFindingCode,
    QDKTDualReadEvidence,
    QDKTDualReadStatus,
    QDKTInventoryReport,
    QDKTOwnershipRecommendation,
    validate_legacy_result,
)
from aura_qdkt_observations import QDKT_EVENT_TYPE, QDKTObservation
from aura_qdkt_projection import project_qdkt_events
from aura_qdkt_projection_io import (
    FindingCollector,
    load_observation,
    read_event_rows,
    rebuild_envelope,
    validate_qdkt_envelope,
)
from aura_qdkt_projection_types import QDKTProjectionFindingCode


def qdkt_ownership_recommendation() -> QDKTOwnershipRecommendation:
    """Return the separate proposal-only ownership disposition for P6.2."""
    return QDKTOwnershipRecommendation()


def _finite_nonnegative(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0.0
    ):
        raise ValueError(f"{name} must be a finite non-negative number")
    return float(value)


def _finding(
    code: QDKTCompatibilityFindingCode,
    detail: str,
    event_ids: tuple[str, ...] = (),
    *,
    blocking: bool = True,
) -> QDKTCompatibilityFinding:
    return QDKTCompatibilityFinding(code, detail, event_ids, blocking)


def _projection_findings(findings: Any) -> tuple[QDKTCompatibilityFinding, ...]:
    return tuple(
        _finding(
            QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED,
            f"{item.code.value}:{item.message}",
            tuple(item.event_ids),
        )
        for item in findings
        if item.blocking
    )


def _valid_observations(
    store: AppendOnlyEventStore,
) -> tuple[
    tuple[tuple[Any, QDKTObservation], ...],
    tuple[QDKTCompatibilityFinding, ...],
]:
    collector = FindingCollector()
    rows = read_event_rows(store, collector)
    valid: list[tuple[Any, QDKTObservation]] = []
    all_events: dict[str, tuple[int, float]] = {}
    row_digests: dict[str, str] = {}
    for index, raw in rows:
        event_id = str(raw.get("event_id") or "")
        try:
            row_digest = stable_digest(raw)
        except (TypeError, ValueError):
            collector.add(
                QDKTProjectionFindingCode.INVALID_EVENT_RECORD,
                "event cannot be canonically digested during compatibility read",
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
                "duplicate event ID during compatibility read",
                (event_id,),
            )
            continue
        row_digests[event_id] = row_digest

        generic = rebuild_envelope(raw)
        if generic is not None:
            all_events[generic.event_id] = (index, generic.created_at)
        if raw.get("event_type") != QDKT_EVENT_TYPE:
            continue
        envelope = validate_qdkt_envelope(raw, collector)
        if envelope is None:
            continue
        observation = load_observation(store, envelope, collector)
        if observation is None:
            continue
        valid.append((envelope, observation))

    ordered = tuple(sorted(valid, key=lambda item: (item[0].created_at, item[0].event_id)))
    for envelope, _observation in ordered:
        child = all_events.get(envelope.event_id)
        for parent_id in envelope.parent_event_ids:
            parent = all_events.get(parent_id)
            if parent is None:
                collector.add(
                    QDKTProjectionFindingCode.MISSING_PARENT,
                    "QDKT parent event is missing or invalid during compatibility read",
                    (envelope.event_id, parent_id),
                )
            elif child is not None and (
                parent[0] >= child[0] or parent[1] > envelope.created_at
            ):
                collector.add(
                    QDKTProjectionFindingCode.OUT_OF_ORDER,
                    "QDKT parent occurs after its child during compatibility read",
                    (envelope.event_id, parent_id),
                )

    findings = tuple(
        sorted(
            _projection_findings(collector.findings),
            key=lambda item: (item.code.value, item.event_ids, item.detail),
        )
    )
    return ordered, findings


def _projected_signature(report: Any) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            item.event_id,
            item.observation_id,
            item.payload_ref,
            item.payload_digest,
            item.trace_id,
            tuple(item.parent_event_ids),
            float(item.created_at),
        )
        for item in report.events
    )


def _observation_signature(
    observations: tuple[tuple[Any, QDKTObservation], ...],
) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            envelope.event_id,
            observation.observation_id,
            envelope.payload_ref,
            envelope.payload_digest,
            envelope.trace_id,
            tuple(envelope.parent_event_ids),
            float(envelope.created_at),
        )
        for envelope, observation in observations
    )


def _result(
    *,
    root: str,
    belief: int,
    status: QDKTDualReadStatus,
    findings: tuple[QDKTCompatibilityFinding, ...],
    matches: tuple[tuple[Any, QDKTObservation], ...] = (),
    inventory: QDKTInventoryReport | None = None,
    requested_snapshot_digest: str = "",
    requested_source_count: int | None = None,
) -> QDKTDualReadEvidence:
    ownership = qdkt_ownership_recommendation()
    selected = matches[0] if len(matches) == 1 else None
    envelope = selected[0] if selected else None
    observation = selected[1] if selected else None
    return QDKTDualReadEvidence(
        legacy_root=root,
        legacy_belief=belief,
        status=status,
        findings=findings,
        matching_event_ids=tuple(item[0].event_id for item in matches),
        observation_id=observation.observation_id if observation else "",
        payload_ref=envelope.payload_ref if envelope else "",
        payload_digest=envelope.payload_digest if envelope else "",
        canonical_source_snapshot_digest=(
            observation.source_snapshot_digest if observation else ""
        ),
        canonical_source_count=(observation.source_count if observation else None),
        requested_source_snapshot_digest=requested_snapshot_digest,
        requested_source_count=requested_source_count,
        canonical_created_at=(envelope.created_at if envelope else None),
        inventory_digest=inventory.digest if inventory is not None else "",
        ownership_digest=ownership.digest,
    )


def compare_qdkt_dual_read(
    store: AppendOnlyEventStore,
    legacy_result: Mapping[str, Any],
    *,
    source_snapshot: Any | None = None,
    inventory: QDKTInventoryReport | None = None,
    max_age_seconds: float | None = None,
    now: float | None = None,
) -> QDKTDualReadEvidence:
    """Compare stored canonical evidence without invoking the legacy generator.

    The caller supplies the exact result already returned by
    ``QuantumMerkleDAG.generate_epistemic_system_root``. This function only
    reads the canonical append-only event store and exact sidecars.
    """
    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    root, belief = validate_legacy_result(legacy_result)
    if inventory is not None and not isinstance(inventory, QDKTInventoryReport):
        raise ValueError("inventory must be a QDKTInventoryReport")
    maximum_age = None
    current_time = None
    if max_age_seconds is not None:
        maximum_age = _finite_nonnegative(max_age_seconds, "max_age_seconds")
        if now is None:
            raise ValueError("now is required when max_age_seconds is supplied")
        current_time = _finite_nonnegative(now, "now")

    requested_digest = ""
    requested_count: int | None = None
    if source_snapshot is not None:
        try:
            expected = QDKTObservation.from_legacy_result(
                legacy_result,
                source_snapshot=source_snapshot,
            )
        except ValueError as exc:
            raise ValueError("source_snapshot is invalid for canonical comparison") from exc
        requested_digest = expected.source_snapshot_digest
        requested_count = expected.source_count

    report = project_qdkt_events(store)
    integrity_findings = _projection_findings(report.findings)
    valid, reread_findings = _valid_observations(store)
    integrity_findings = tuple((*integrity_findings, *reread_findings))
    if not integrity_findings and _projected_signature(report) != _observation_signature(valid):
        event_ids = tuple(
            sorted(
                {
                    *(item.event_id for item in report.events),
                    *(item[0].event_id for item in valid),
                }
            )
        )
        integrity_findings = (
            _finding(
                QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED,
                "QDKT event evidence changed between projection and compatibility read",
                event_ids,
            ),
        )

    if integrity_findings:
        return _result(
            root=root,
            belief=belief,
            status=QDKTDualReadStatus.MISMATCHED,
            findings=integrity_findings,
            inventory=inventory,
            requested_snapshot_digest=requested_digest,
            requested_source_count=requested_count,
        )

    if report.qdkt_event_count == 0:
        return _result(
            root=root,
            belief=belief,
            status=QDKTDualReadStatus.UNAVAILABLE,
            findings=(
                _finding(
                    QDKTCompatibilityFindingCode.CANONICAL_EVIDENCE_UNAVAILABLE,
                    "no canonical QDKT observation event is available",
                ),
            ),
            inventory=inventory,
            requested_snapshot_digest=requested_digest,
            requested_source_count=requested_count,
        )

    root_matches = tuple(item for item in valid if item[1].legacy_root == root)
    value_matches = tuple(
        item
        for item in root_matches
        if item[1].legacy_belief == belief
    )
    findings: list[QDKTCompatibilityFinding] = []
    all_event_ids = tuple(item[0].event_id for item in valid)

    if not root_matches:
        findings.append(
            _finding(
                QDKTCompatibilityFindingCode.LEGACY_ROOT_MISMATCH,
                "canonical observations do not match the supplied legacy root",
                all_event_ids,
            )
        )
    elif not value_matches:
        findings.append(
            _finding(
                QDKTCompatibilityFindingCode.LEGACY_BELIEF_MISMATCH,
                "canonical observations match the root but not the supplied belief",
                tuple(item[0].event_id for item in root_matches),
            )
        )

    matches = value_matches
    if source_snapshot is not None:
        source_matches = tuple(
            item
            for item in value_matches
            if item[1].source_snapshot_digest == requested_digest
            and item[1].source_count == requested_count
        )
        if value_matches and not source_matches:
            findings.append(
                _finding(
                    QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_MISMATCH,
                    "canonical root and belief match but source snapshot identity differs",
                    tuple(item[0].event_id for item in value_matches),
                )
            )
        matches = source_matches

    if len(matches) > 1:
        findings.append(
            _finding(
                QDKTCompatibilityFindingCode.DUPLICATE_MATCHING_EVIDENCE,
                "more than one canonical event claims the same legacy observation",
                tuple(item[0].event_id for item in matches),
            )
        )

    conflict_identities: set[tuple[str, int]] = set()
    if source_snapshot is not None and requested_count is not None:
        conflict_identities.add((requested_digest, requested_count))
    else:
        conflict_identities.update(
            (item[1].source_snapshot_digest, item[1].source_count)
            for item in matches
        )
    if matches and conflict_identities:
        conflicts = tuple(
            item
            for item in valid
            if (
                item[1].source_snapshot_digest,
                item[1].source_count,
            )
            in conflict_identities
            and (
                item[1].legacy_root != root
                or item[1].legacy_belief != belief
            )
        )
        if conflicts:
            findings.append(
                _finding(
                    QDKTCompatibilityFindingCode.CONFLICTING_CANONICAL_EVIDENCE,
                    "the same source snapshot is bound to a conflicting root or belief",
                    tuple(item[0].event_id for item in conflicts),
                )
            )

    if len(matches) == 1 and maximum_age is not None and current_time is not None:
        age = current_time - float(matches[0][0].created_at)
        if age < 0.0 or age > maximum_age:
            findings.append(
                _finding(
                    QDKTCompatibilityFindingCode.STALE_CANONICAL_EVIDENCE,
                    "canonical QDKT evidence is outside the permitted age window",
                    (matches[0][0].event_id,),
                )
            )

    if findings or len(matches) != 1:
        if not findings:
            findings.append(
                _finding(
                    QDKTCompatibilityFindingCode.CANONICAL_EVIDENCE_UNAVAILABLE,
                    "no single canonical QDKT observation satisfies the comparison",
                    all_event_ids,
                )
            )
        return _result(
            root=root,
            belief=belief,
            status=QDKTDualReadStatus.MISMATCHED,
            findings=tuple(findings),
            matches=matches,
            inventory=inventory,
            requested_snapshot_digest=requested_digest,
            requested_source_count=requested_count,
        )

    if source_snapshot is None:
        return _result(
            root=root,
            belief=belief,
            status=QDKTDualReadStatus.ADVISORY_ONLY,
            findings=(
                _finding(
                    QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_NOT_SUPPLIED,
                    "root and belief match, but source-snapshot identity was not supplied",
                    (matches[0][0].event_id,),
                    blocking=False,
                ),
            ),
            matches=matches,
            inventory=inventory,
        )

    return _result(
        root=root,
        belief=belief,
        status=QDKTDualReadStatus.VERIFIED,
        findings=(),
        matches=matches,
        inventory=inventory,
        requested_snapshot_digest=requested_digest,
        requested_source_count=requested_count,
    )


__all__ = ["compare_qdkt_dual_read", "qdkt_ownership_recommendation"]
