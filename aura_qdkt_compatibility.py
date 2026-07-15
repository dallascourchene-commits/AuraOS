"""Opt-in P6.2 dual-read evidence for an already-produced legacy QDKT result."""
from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from aura_event_contracts import AppendOnlyEventStore
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
    validate_qdkt_envelope,
)


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


def _projector_findings(report: Any) -> tuple[QDKTCompatibilityFinding, ...]:
    return tuple(
        _finding(
            QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED,
            f"{item.code.value}:{item.message}",
            tuple(item.event_ids),
        )
        for item in report.findings
        if item.blocking
    )


def _valid_observations(
    store: AppendOnlyEventStore,
) -> tuple[tuple[Any, QDKTObservation], ...]:
    collector = FindingCollector()
    rows = read_event_rows(store, collector)
    valid: list[tuple[Any, QDKTObservation]] = []
    seen: set[str] = set()
    for _index, raw in rows:
        if raw.get("event_type") != QDKT_EVENT_TYPE:
            continue
        envelope = validate_qdkt_envelope(raw, collector)
        if envelope is None or envelope.event_id in seen:
            continue
        observation = load_observation(store, envelope, collector)
        if observation is None:
            continue
        seen.add(envelope.event_id)
        valid.append((envelope, observation))
    return tuple(sorted(valid, key=lambda item: (item[0].created_at, item[0].event_id)))


def _result(
    *,
    root: str,
    belief: int,
    status: QDKTDualReadStatus,
    findings: tuple[QDKTCompatibilityFinding, ...],
    matches: tuple[tuple[Any, QDKTObservation], ...] = (),
    inventory: QDKTInventoryReport | None = None,
    expected_snapshot_digest: str = "",
    expected_source_count: int | None = None,
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
        source_snapshot_digest=(
            observation.source_snapshot_digest
            if observation
            else expected_snapshot_digest
        ),
        source_count=(observation.source_count if observation else expected_source_count),
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

    expected_digest = ""
    expected_count: int | None = None
    if source_snapshot is not None:
        try:
            expected = QDKTObservation.from_legacy_result(
                legacy_result,
                source_snapshot=source_snapshot,
            )
        except ValueError as exc:
            raise ValueError("source_snapshot is invalid for canonical comparison") from exc
        expected_digest = expected.source_snapshot_digest
        expected_count = expected.source_count

    report = project_qdkt_events(store)
    integrity_findings = _projector_findings(report)
    valid = _valid_observations(store)

    if integrity_findings:
        return _result(
            root=root,
            belief=belief,
            status=QDKTDualReadStatus.MISMATCHED,
            findings=integrity_findings,
            inventory=inventory,
            expected_snapshot_digest=expected_digest,
            expected_source_count=expected_count,
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
            expected_snapshot_digest=expected_digest,
            expected_source_count=expected_count,
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
            if item[1].source_snapshot_digest == expected_digest
            and item[1].source_count == expected_count
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

    if source_snapshot is not None and matches:
        conflicts = tuple(
            item
            for item in valid
            if item[1].source_snapshot_digest == expected_digest
            and item[1].source_count == expected_count
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
            expected_snapshot_digest=expected_digest,
            expected_source_count=expected_count,
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
        expected_snapshot_digest=expected_digest,
        expected_source_count=expected_count,
    )


__all__ = ["compare_qdkt_dual_read", "qdkt_ownership_recommendation"]
