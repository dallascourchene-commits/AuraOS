from __future__ import annotations

from aura_event_contracts import AppendOnlyEventStore
from aura_qdkt_compatibility import (
    compare_qdkt_dual_read,
    qdkt_ownership_recommendation,
)
from aura_qdkt_compatibility_types import (
    QDKTCompatibilityFindingCode,
    QDKTDualReadStatus,
)
from aura_qdkt_observations import QDKTObservation, record_qdkt_observation

LEGACY_RESULT = {"root": "A1B2C3D4E5F60718", "belief": 6900}
OTHER_RESULT = {"root": "B1B2C3D4E5F60718", "belief": 6900}
SOURCE_SNAPSHOT = (
    {"path": "alpha.py", "digest": "a" * 64},
    {"path": "beta.py", "digest": "b" * 64},
)
OTHER_SNAPSHOT = ({"path": "gamma.py", "digest": "c" * 64},)


def record(
    store: AppendOnlyEventStore,
    result=LEGACY_RESULT,
    snapshot=SOURCE_SNAPSHOT,
    *,
    trace="trace-1",
    created_at=100.0,
):
    observation = QDKTObservation.from_legacy_result(
        result,
        source_snapshot=snapshot,
    )
    return record_qdkt_observation(
        store,
        observation,
        trace_id=trace,
        actor_id="aura",
        purpose_digest="purpose-1",
        created_at=created_at,
    )


def test_exact_existing_result_and_snapshot_are_verified(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    receipt = record(store)
    result = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.VERIFIED
    assert result.legacy_result == LEGACY_RESULT
    assert result.matching_event_ids == (receipt.event.event_id,)
    assert result.observation_id == receipt.observation.observation_id
    assert result.payload_ref == receipt.payload_ref.ref_id
    assert result.payload_digest == receipt.payload_ref.payload_digest
    assert result.findings == ()
    assert result.generator_replayed is False
    assert result.proposal_only is True
    assert result.qdkt_patch_authority is False


def test_root_and_belief_match_without_snapshot_is_advisory(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    result = compare_qdkt_dual_read(store, LEGACY_RESULT)
    assert result.status is QDKTDualReadStatus.ADVISORY_ONLY
    assert result.legacy_result == LEGACY_RESULT
    assert [item.code for item in result.findings] == [
        QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_NOT_SUPPLIED
    ]
    assert result.findings[0].blocking is False


def test_missing_canonical_evidence_is_unavailable(tmp_path) -> None:
    result = compare_qdkt_dual_read(
        AppendOnlyEventStore(tmp_path / "events"),
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.UNAVAILABLE
    assert result.legacy_result == LEGACY_RESULT
    assert result.findings[0].code is QDKTCompatibilityFindingCode.CANONICAL_EVIDENCE_UNAVAILABLE


def test_root_belief_and_snapshot_mismatches_fail_closed(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)

    root = compare_qdkt_dual_read(
        store,
        OTHER_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert root.status is QDKTDualReadStatus.MISMATCHED
    assert root.legacy_result == OTHER_RESULT
    assert root.findings[0].code is QDKTCompatibilityFindingCode.LEGACY_ROOT_MISMATCH

    belief_result = {"root": LEGACY_RESULT["root"], "belief": 1}
    belief = compare_qdkt_dual_read(
        store,
        belief_result,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert belief.status is QDKTDualReadStatus.MISMATCHED
    assert belief.legacy_result == belief_result
    assert belief.findings[0].code is QDKTCompatibilityFindingCode.LEGACY_BELIEF_MISMATCH

    snapshot = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=OTHER_SNAPSHOT,
    )
    assert snapshot.status is QDKTDualReadStatus.MISMATCHED
    assert snapshot.legacy_result == LEGACY_RESULT
    assert snapshot.findings[0].code is QDKTCompatibilityFindingCode.SOURCE_SNAPSHOT_MISMATCH


def test_unrelated_historical_observations_do_not_invalidate_exact_match(tmp_path) -> None:
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store, OTHER_RESULT, OTHER_SNAPSHOT, trace="trace-old", created_at=50.0)
    record(store, LEGACY_RESULT, SOURCE_SNAPSHOT, trace="trace-current", created_at=100.0)
    result = compare_qdkt_dual_read(
        store,
        LEGACY_RESULT,
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.VERIFIED


def test_comparison_does_not_accept_or_replay_a_generator(tmp_path) -> None:
    class GeneratorThatMustNotRun:
        calls = 0

        async def generate_epistemic_system_root(self):
            self.calls += 1
            raise AssertionError("generator replay is prohibited")

    generator = GeneratorThatMustNotRun()
    store = AppendOnlyEventStore(tmp_path / "events")
    record(store)
    result = compare_qdkt_dual_read(
        store,
        dict(LEGACY_RESULT),
        source_snapshot=SOURCE_SNAPSHOT,
    )
    assert result.status is QDKTDualReadStatus.VERIFIED
    assert generator.calls == 0


def test_ownership_recommendation_retains_legacy_and_denies_authority() -> None:
    recommendation = qdkt_ownership_recommendation()
    assert recommendation.recommendation == "RETAIN_LEGACY_DUAL_READ"
    assert recommendation.redirect_ready is False
    assert recommendation.delete_legacy_ready is False
    assert recommendation.storage_transfer_ready is False
    assert recommendation.historical_backfill_ready is False
    assert recommendation.proposal_only is True
    assert recommendation.qdkt_patch_authority is False
