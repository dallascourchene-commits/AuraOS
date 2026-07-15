from __future__ import annotations

import json

import pytest

import aura_qdkt_compatibility as compatibility
from aura_event_contracts import AppendOnlyEventStore, canonical_json
from aura_qdkt_compatibility import compare_qdkt_dual_read
from aura_qdkt_compatibility_types import (
    QDKTCompatibilityFinding,
    QDKTCompatibilityFindingCode,
    QDKTDualReadEvidence,
    QDKTDualReadStatus,
    QDKTOwnershipRecommendation,
)
from aura_qdkt_observations import QDKTObservation, record_qdkt_observation

LEGACY_RESULT = {"root": "A1B2C3D4E5F60718", "belief": 6900}
SOURCE_SNAPSHOT = (
    {"path": "alpha.py", "digest": "a" * 64},
    {"path": "beta.py", "digest": "b" * 64},
)


def record(
    store: AppendOnlyEventStore,
    *,
    trace="trace-1",
    created_at=100.0,
    result=LEGACY_RESULT,
    snapshot=SOURCE_SNAPSHOT,
):
    return record_qdkt_observation(
        store,
        QDKTObservation.from_legacy_result(result, source_snapshot=snapshot),
        trace_id=trace,
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=created_at,
    )


def codes(result) -> set[QDKTCompatibilityFindingCode]:
    return {item.code for item in result.findings}


def test_missing_malformed_and_substituted_sidecars_are_mismatched(tmp_path) -> None:
    for name, mutation in (
        ("missing", lambda path: path.unlink()),
        ("malformed", lambda path: path.write_text("{bad", encoding="utf-8")),
        (
            "substituted",
            lambda path: path.write_text(
                canonical_json(
                    QDKTObservation.from_legacy_result(
                        {"root": "B1B2C3D4E5F60718", "belief": 6900},
                        source_snapshot=SOURCE_SNAPSHOT,
                    ).to_dict()
                ),
                encoding="utf-8",
            ),
        ),
    ):
        store = AppendOnlyEventStore(tmp_path / name)
        receipt = record(store)
        path = store.sidecars_dir / f"{receipt.payload_ref.ref_id}.json"
        mutation(path)
        result = compare_qdkt_dual_read(
            store,
            LEGACY_RESULT,
            source_snapshot=SOURCE_SNAPSHOT,
        )
        assert result.status is QDKTDualReadStatus.MISMATCHED
        assert result.legacy_result == LEGACY_RESULT
        assert QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED in codes(result)


def test_duplicate_event_rows_are_mismatched(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    row = store.events_path.read_text(encoding="utf-8")
    store.events_path.write_text(row + row, encoding="utf-8")
    result = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.MISMATCHED
    assert QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED in codes(result)


def test_store_change_between_projection_and_reread_fails_closed(
    tmp_path,
    monkeypatch,
) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    original = compatibility.project_qdkt_events
    changed = False

    def project_then_duplicate(target):
        nonlocal changed
        report = original(target)
        if not changed:
            row = target.events_path.read_text(encoding="utf-8")
            target.events_path.write_text(row + row, encoding="utf-8")
            changed = True
        return report

    monkeypatch.setattr(compatibility, "project_qdkt_events", project_then_duplicate)
    result = compatibility.compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.MISMATCHED
    assert result.legacy_result == LEGACY_RESULT
    assert QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED in codes(result)


def test_multiple_exact_events_are_mismatched_without_rewriting_legacy(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store, trace="trace-1", created_at=100.0)
    record(store, trace="trace-2", created_at=101.0)
    result = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.MISMATCHED
    assert result.legacy_result == LEGACY_RESULT
    assert QDKTCompatibilityFindingCode.DUPLICATE_MATCHING_EVIDENCE in codes(result)


def test_same_snapshot_with_conflicting_result_is_mismatched(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store, trace="trace-good", result=LEGACY_RESULT)
    record(
        store,
        trace="trace-conflict",
        result={"root": "B1B2C3D4E5F60718", "belief": 6900},
    )
    result = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.MISMATCHED
    assert QDKTCompatibilityFindingCode.CONFLICTING_CANONICAL_EVIDENCE in codes(result)


def test_same_snapshot_conflict_without_caller_snapshot_fails_closed(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store, trace="trace-good", result=LEGACY_RESULT)
    record(
        store,
        trace="trace-conflict",
        result={"root": "B1B2C3D4E5F60718", "belief": 6900},
    )
    result = compare_qdkt_dual_read(store, LEGACY_RESULT)
    assert result.status is QDKTDualReadStatus.MISMATCHED
    assert result.legacy_result == LEGACY_RESULT
    assert QDKTCompatibilityFindingCode.CONFLICTING_CANONICAL_EVIDENCE in codes(result)
    assert QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_NOT_SUPPLIED not in codes(result)


def test_stale_or_future_dated_evidence_is_mismatched(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store, created_at=100.0)
    stale = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
        max_age_seconds=10.0,
        now=111.0,
    )
    assert stale.status is QDKTDualReadStatus.MISMATCHED
    assert QDKTCompatibilityFindingCode.STALE_CANONICAL_EVIDENCE in codes(stale)

    future = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
        max_age_seconds=10.0,
        now=99.0,
    )
    assert future.status is QDKTDualReadStatus.MISMATCHED
    assert QDKTCompatibilityFindingCode.STALE_CANONICAL_EVIDENCE in codes(future)


def test_invalid_inputs_raise_before_any_store_write(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    for invalid in (
        {"root": "bad", "belief": 1},
        {"root": LEGACY_RESULT["root"], "belief": True},
        {"root": LEGACY_RESULT["root"], "belief": 1, "extra": 2},
    ):
        with pytest.raises(ValueError):
            compare_qdkt_dual_read(store, invalid, source_snapshot=SOURCE_SNAPSHOT)
    with pytest.raises(ValueError, match="source_snapshot"):
        compare_qdkt_dual_read(store, LEGACY_RESULT, source_snapshot="unsafe")
    with pytest.raises(ValueError, match="now is required"):
        compare_qdkt_dual_read(
            store,
            LEGACY_RESULT,
            source_snapshot=SOURCE_SNAPSHOT,
            max_age_seconds=10.0,
        )
    assert not store.events_path.exists()
    assert list(store.sidecars_dir.iterdir()) == []


def test_noncanonical_event_bytes_fail_closed(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    row = json.loads(store.events_path.read_text(encoding="utf-8"))
    store.events_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    result = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.MISMATCHED
    assert QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED in codes(result)


def test_evidence_normalizes_one_shot_finding_iterables() -> None:
    warning = QDKTCompatibilityFinding(
        QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_NOT_SUPPLIED,
        "snapshot omitted",
        ("event-1",),
        blocking=False,
    )
    evidence = QDKTDualReadEvidence(
        legacy_root=LEGACY_RESULT["root"],
        legacy_belief=LEGACY_RESULT["belief"],
        status=QDKTDualReadStatus.ADVISORY_ONLY,
        findings=(item for item in (warning,)),
        matching_event_ids=(item for item in ("event-1",)),
        observation_id="observation-1",
        payload_ref="payload_" + "a" * 24,
        payload_digest="b" * 32,
        canonical_source_snapshot_digest="c" * 32,
        canonical_source_count=2,
        canonical_created_at=100.0,
    )
    assert evidence.findings == (warning,)
    assert evidence.matching_event_ids == ("event-1",)


def test_evidence_rejects_incoherent_status_and_metadata() -> None:
    warning = QDKTCompatibilityFinding(
        QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_NOT_SUPPLIED,
        "snapshot omitted",
        ("event-1",),
        blocking=False,
    )
    with pytest.raises(ValueError, match="mismatched evidence"):
        QDKTDualReadEvidence(
            legacy_root=LEGACY_RESULT["root"],
            legacy_belief=LEGACY_RESULT["belief"],
            status=QDKTDualReadStatus.MISMATCHED,
            findings=(warning,),
        )
    with pytest.raises(ValueError, match="digest and count"):
        QDKTDualReadEvidence(
            legacy_root=LEGACY_RESULT["root"],
            legacy_belief=LEGACY_RESULT["belief"],
            status=QDKTDualReadStatus.MISMATCHED,
            findings=(
                QDKTCompatibilityFinding(
                    QDKTCompatibilityFindingCode.LEGACY_ROOT_MISMATCH,
                    "root mismatch",
                ),
            ),
            requested_source_snapshot_digest="d" * 32,
        )


def test_ownership_contract_rejects_owner_substitution() -> None:
    with pytest.raises(ValueError, match="ownership changed"):
        QDKTOwnershipRecommendation(current_result_owner="replacement.generator")
    with pytest.raises(ValueError, match="evidence ownership changed"):
        QDKTOwnershipRecommendation(canonical_evidence_owner="replacement.store")
