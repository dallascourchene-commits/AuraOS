from __future__ import annotations

import json

import pytest

import aura_qdkt_compatibility as compatibility
from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DIKWPStage,
    canonical_json,
)
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
EVENT_ID = "event_" + "a" * 24
OBSERVATION_ID = "qdkt-observation_" + "b" * 24
PAYLOAD_REF = "payload_" + "c" * 24


def record(
    store: AppendOnlyEventStore,
    *,
    trace="trace-1",
    created_at=100.0,
    result=LEGACY_RESULT,
    snapshot=SOURCE_SNAPSHOT,
    parent_event_ids=(),
):
    return record_qdkt_observation(
        store,
        QDKTObservation.from_legacy_result(result, source_snapshot=snapshot),
        trace_id=trace,
        actor_id="aura",
        purpose_digest="purpose-1",
        parent_event_ids=parent_event_ids,
        created_at=created_at,
    )


def generic_parent(created_at=50.0) -> AuraEventEnvelope:
    return AuraEventEnvelope.create(
        trace_id="trace-parent",
        event_type="test.parent.recorded",
        actor_id="aura",
        actor_type=ActorType.AURA,
        node_id="parent-node",
        purpose_digest="purpose-parent",
        dikwp_stage=DIKWPStage.DATA,
        payload_ref="parent-payload",
        payload_digest="parent-digest",
        policy_scope="test.parent",
        proposal_only=True,
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


def test_parent_removed_between_projection_and_reread_fails_closed(
    tmp_path,
    monkeypatch,
) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    parent = generic_parent()
    store.append(parent)
    record(store, parent_event_ids=(parent.event_id,))
    original = compatibility.project_qdkt_events
    changed = False

    def project_then_remove_parent(target):
        nonlocal changed
        report = original(target)
        if not changed:
            lines = target.events_path.read_text(encoding="utf-8").splitlines()
            target.events_path.write_text(lines[-1] + "\n", encoding="utf-8")
            changed = True
        return report

    monkeypatch.setattr(compatibility, "project_qdkt_events", project_then_remove_parent)
    result = compatibility.compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.MISMATCHED
    assert result.legacy_result == LEGACY_RESULT
    assert QDKTCompatibilityFindingCode.CANONICAL_INTEGRITY_FAILED in codes(result)


def test_parent_duplicated_between_projection_and_reread_fails_closed(
    tmp_path,
    monkeypatch,
) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    parent = generic_parent()
    store.append(parent)
    record(store, parent_event_ids=(parent.event_id,))
    original = compatibility.project_qdkt_events
    changed = False

    def project_then_duplicate_parent(target):
        nonlocal changed
        report = original(target)
        if not changed:
            lines = target.events_path.read_text(encoding="utf-8").splitlines()
            target.events_path.write_text(
                "\n".join((lines[0], lines[0], lines[1])) + "\n",
                encoding="utf-8",
            )
            changed = True
        return report

    monkeypatch.setattr(compatibility, "project_qdkt_events", project_then_duplicate_parent)
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
        (EVENT_ID,),
        blocking=False,
    )
    evidence = QDKTDualReadEvidence(
        legacy_root=LEGACY_RESULT["root"],
        legacy_belief=LEGACY_RESULT["belief"],
        status=QDKTDualReadStatus.ADVISORY_ONLY,
        findings=(item for item in (warning, warning)),
        matching_event_ids=(item for item in (EVENT_ID,)),
        observation_id=OBSERVATION_ID,
        payload_ref=PAYLOAD_REF,
        payload_digest="d" * 32,
        canonical_source_snapshot_digest="e" * 32,
        canonical_source_count=2,
        canonical_created_at=100.0,
    )
    assert evidence.findings == (warning,)
    assert evidence.matching_event_ids == (EVENT_ID,)


def test_evidence_rejects_incoherent_status_and_metadata() -> None:
    warning = QDKTCompatibilityFinding(
        QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_NOT_SUPPLIED,
        "snapshot omitted",
        (EVENT_ID,),
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


def test_evidence_rejects_noncanonical_selected_ids_and_negative_time() -> None:
    blocking = QDKTCompatibilityFinding(
        QDKTCompatibilityFindingCode.STALE_CANONICAL_EVIDENCE,
        "stale",
        (EVENT_ID,),
    )
    common = {
        "legacy_root": LEGACY_RESULT["root"],
        "legacy_belief": LEGACY_RESULT["belief"],
        "status": QDKTDualReadStatus.MISMATCHED,
        "findings": (blocking,),
        "matching_event_ids": (EVENT_ID,),
        "observation_id": OBSERVATION_ID,
        "payload_ref": PAYLOAD_REF,
        "payload_digest": "d" * 32,
        "canonical_source_snapshot_digest": "e" * 32,
        "canonical_source_count": 2,
        "canonical_created_at": 100.0,
    }
    for field, value in (
        ("matching_event_ids", ("event-bad",)),
        ("observation_id", "observation-bad"),
        ("payload_ref", "payload-bad"),
        ("canonical_created_at", -1.0),
    ):
        payload = dict(common)
        payload[field] = value
        with pytest.raises(ValueError):
            QDKTDualReadEvidence(**payload)


def test_ownership_contract_rejects_owner_substitution() -> None:
    with pytest.raises(ValueError, match="ownership changed"):
        QDKTOwnershipRecommendation(current_result_owner="replacement.generator")
    with pytest.raises(ValueError, match="evidence ownership changed"):
        QDKTOwnershipRecommendation(canonical_evidence_owner="replacement.store")
