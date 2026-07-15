from __future__ import annotations

from dataclasses import dataclass
import json

import pytest

from aura_st3gg_contracts import (
    PATCH_AUTHORITY,
    ST3GGDecision,
    ST3GGExactRecallRecord,
    ST3GGMeasurementClass,
    ST3GGRestorationMode,
    ST3GGSavingsPolicy,
    adapt_legacy_arena_decision,
    adapt_legacy_ast_frame,
    adapt_legacy_report_result,
    canonical_pointer,
    digest_text,
    exact_ref_for,
    parse_canonical_pointer,
    prepare_st3gg_artifact,
    verify_exact_recall_record,
)


class MemoryExactStore:
    def __init__(self) -> None:
        self.records: dict[str, ST3GGExactRecallRecord] = {}
        self.calls = 0

    def persist(self, record: ST3GGExactRecallRecord) -> dict[str, str]:
        self.calls += 1
        verify_exact_recall_record(record)
        self.records[record.exact_ref] = record
        return {
            "exact_ref": record.exact_ref,
            "original_digest": record.original_digest,
        }


def test_canonical_pointer_is_versioned_visible_ascii_and_deterministic() -> None:
    digest = digest_text("exact original")
    first = canonical_pointer("arena", digest)
    second = canonical_pointer("ARENA", digest)

    assert first == second
    assert first.startswith("ST3GG2::ARENA:")
    first.encode("ascii")
    assert parse_canonical_pointer(first)[0] == "ARENA"


def test_exact_ref_is_digest_bound_and_record_verifies() -> None:
    original = "source evidence\nwith exact spacing"
    digest = digest_text(original)
    record = ST3GGExactRecallRecord(
        namespace="REPORT",
        exact_ref=exact_ref_for("REPORT", digest),
        original_digest=digest,
        original_bytes=len(original.encode("utf-8")),
        content_type="text/plain",
        source_hint="golden",
        original=original,
    )

    verify_exact_recall_record(record)
    assert record.sidecar_dict()["original"] == original


def test_tampered_exact_record_fails_closed() -> None:
    original = "exact"
    digest = digest_text(original)

    with pytest.raises(ValueError, match="exact_recall_digest_mismatch"):
        ST3GGExactRecallRecord(
            namespace="ARENA",
            exact_ref=exact_ref_for("ARENA", digest),
            original_digest=digest,
            original_bytes=len(original),
            content_type="application/json",
            source_hint="test",
            original="tampered",
        )


def test_enabled_artifact_persists_exact_original_before_return() -> None:
    original = json.dumps(
        {"rows": [{"name": f"item-{index}", "detail": "repeat " * 40} for index in range(40)]},
        sort_keys=True,
        separators=(",", ":"),
    )
    candidate = "ST3GG1|rows=40|schema=name,detail|repeated=1"
    store = MemoryExactStore()

    artifact = prepare_st3gg_artifact(
        original,
        candidate,
        namespace="ARENA",
        content_type="application/json",
        source_hint="legacy-arena",
        policy=ST3GGSavingsPolicy(
            minimum_savings_ratio=0.08,
            minimum_raw_units=100,
            measurement_class=ST3GGMeasurementClass.BYTE_EXACT,
        ),
        persist_exact=store.persist,
    )

    assert artifact.decision.enabled is True
    assert artifact.decision.restoration_mode is ST3GGRestorationMode.EXACT_RECALL
    assert artifact.decision.exact_ref in store.records
    assert store.records[artifact.decision.exact_ref].original == original
    assert artifact.payload.endswith("ST3GG_AUTH=false")
    assert artifact.decision.patch_authority == PATCH_AUTHORITY
    assert artifact.decision.st3gg_patch_authority is False


def test_protocol_overhead_is_counted_before_persistence() -> None:
    original = "A" * 250
    candidate = "short-but-not-enough"
    store = MemoryExactStore()

    artifact = prepare_st3gg_artifact(
        original,
        candidate,
        namespace="REPORT",
        content_type="text/plain",
        policy=ST3GGSavingsPolicy(
            minimum_savings_ratio=0.80,
            minimum_raw_units=1,
            measurement_class=ST3GGMeasurementClass.BYTE_EXACT,
        ),
        persist_exact=store.persist,
    )

    assert artifact.decision.enabled is False
    assert artifact.decision.reason in {
        "protocol_overhead_erased_savings",
        "below_savings_threshold",
    }
    assert artifact.decision.overhead_units > 0
    assert artifact.payload == ""
    assert store.calls == 0


def test_missing_persistence_cannot_emit_exact_recall_handle() -> None:
    artifact = prepare_st3gg_artifact(
        "A" * 3000,
        "compact",
        namespace="ARENA",
        content_type="application/json",
        persist_exact=None,
    )

    assert artifact.decision.enabled is False
    assert artifact.decision.reason == "exact_recall_persistence_required"
    assert artifact.decision.pointer is None
    assert artifact.decision.exact_ref is None
    assert artifact.payload == ""


def test_persistence_receipt_mismatch_fails_closed() -> None:
    def bad_receipt(record: ST3GGExactRecallRecord) -> dict[str, str]:
        return {"exact_ref": record.exact_ref, "original_digest": "0" * 64}

    artifact = prepare_st3gg_artifact(
        "B" * 3000,
        "compact",
        namespace="ARENA",
        content_type="application/json",
        persist_exact=bad_receipt,
    )

    assert artifact.decision.enabled is False
    assert artifact.decision.reason == "exact_recall_receipt_mismatch"
    assert artifact.payload == ""


def test_non_ascii_and_hidden_channels_are_not_emitted() -> None:
    store = MemoryExactStore()
    artifact = prepare_st3gg_artifact(
        "C" * 4000,
        "compact\u200b\U000e0041\u202eé",
        namespace="ARENA",
        content_type="text/plain",
        persist_exact=store.persist,
    )

    assert artifact.decision.enabled is True
    artifact.payload.encode("ascii")
    assert "\u200b" not in artifact.payload
    assert "\U000e0041" not in artifact.payload
    assert "\u202e" not in artifact.payload


def test_decision_rejects_exact_claim_without_exact_ref() -> None:
    with pytest.raises(ValueError, match="exact_recall_requires_exact_ref"):
        ST3GGDecision(
            enabled=False,
            reason="invalid",
            namespace="ARENA",
            measurement_class=ST3GGMeasurementClass.BYTE_EXACT,
            raw_units=10,
            candidate_units=5,
            final_units=5,
            overhead_units=0,
            savings_ratio=0.5,
            minimum_savings_ratio=0.0,
            restoration_mode=ST3GGRestorationMode.EXACT_RECALL,
            original_digest=digest_text("x"),
        )


def test_decision_rejects_pointer_not_bound_to_original_digest() -> None:
    original_digest = digest_text("original")
    wrong_pointer = canonical_pointer("ARENA", digest_text("other"))
    with pytest.raises(ValueError, match="pointer_digest_mismatch"):
        ST3GGDecision(enabled=True, reason="invalid", namespace="ARENA", measurement_class=ST3GGMeasurementClass.BYTE_EXACT, raw_units=100, candidate_units=10, final_units=20, overhead_units=10, savings_ratio=0.8, minimum_savings_ratio=0.08, restoration_mode=ST3GGRestorationMode.LOSSY_ADVISORY, original_digest=original_digest, compact_digest=digest_text("compact"), pointer=wrong_pointer)


def test_decision_rejects_exact_ref_not_bound_to_original_digest() -> None:
    original_digest = digest_text("original")
    with pytest.raises(ValueError, match="exact_ref_digest_mismatch"):
        ST3GGDecision(enabled=True, reason="invalid", namespace="ARENA", measurement_class=ST3GGMeasurementClass.BYTE_EXACT, raw_units=100, candidate_units=10, final_units=20, overhead_units=10, savings_ratio=0.8, minimum_savings_ratio=0.08, restoration_mode=ST3GGRestorationMode.EXACT_RECALL, original_digest=original_digest, compact_digest=digest_text("compact"), pointer=canonical_pointer("ARENA", original_digest), exact_ref=exact_ref_for("ARENA", digest_text("other")))


def test_decision_rejects_inconsistent_measurement_arithmetic() -> None:
    with pytest.raises(ValueError, match="final_units_do_not_match_candidate_plus_overhead"):
        ST3GGDecision(enabled=False, reason="invalid", namespace="ARENA", measurement_class=ST3GGMeasurementClass.BYTE_EXACT, raw_units=100, candidate_units=20, final_units=30, overhead_units=5, savings_ratio=0.7, minimum_savings_ratio=0.08, restoration_mode=ST3GGRestorationMode.NONE, original_digest=digest_text("original"))


def test_decision_rejects_caller_supplied_savings_ratio() -> None:
    with pytest.raises(ValueError, match="savings_ratio_not_derived_from_final_units"):
        ST3GGDecision(enabled=False, reason="invalid", namespace="ARENA", measurement_class=ST3GGMeasurementClass.BYTE_EXACT, raw_units=100, candidate_units=20, final_units=20, overhead_units=0, savings_ratio=0.9, minimum_savings_ratio=0.08, restoration_mode=ST3GGRestorationMode.NONE, original_digest=digest_text("original"))


def test_legacy_empty_compact_payload_is_not_enabled() -> None:
    decision = adapt_legacy_report_result("original" * 20, "", 1.0, "ST3GG_PTR:empty")
    assert decision.enabled is False
    assert decision.pointer is None

@dataclass(frozen=True)
class LegacyArenaDecision:
    enabled: bool = True
    reason: str = "savings_threshold_met"
    raw_tokens_est: int = 100
    compact_tokens_est: int = 50
    savings_ratio: float = 0.5
    st3gg_pointer: str = "ST3GG-L2::ARENA:ABCD:0123456789abcdef"
    original_hash: str = "a" * 64
    warnings: tuple[str, ...] = ()


def test_legacy_arena_projection_preserves_pointer_but_does_not_claim_exact_v2_recall() -> None:
    decision = adapt_legacy_arena_decision(LegacyArenaDecision())

    assert decision.enabled is False
    assert decision.legacy_pointer == LegacyArenaDecision.st3gg_pointer
    assert decision.restoration_mode is ST3GGRestorationMode.NONE
    assert decision.reason == "legacy_projection_requires_exact_recall_migration"


def test_legacy_ast_projection_is_explicitly_lossy_advisory() -> None:
    frame = {
        "profile": "SUMMARY",
        "source_hash": "b" * 64,
        "encoded": "ST3GG_AST|summary",
        "metrics": {
            "raw_token_estimate": 100,
            "encoded_token_estimate": 40,
        },
        "warnings": ["exact_source_spans_omitted:profile=SUMMARY"],
    }

    decision = adapt_legacy_ast_frame(frame)

    assert decision.enabled is True
    assert decision.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY
    assert decision.exact_ref is None
    assert decision.legacy_surface == "AURA_ST3GG_CODEC_V1"


def test_legacy_report_projection_recomputes_byte_savings_and_stays_lossy() -> None:
    original = "Emergent Properties and Future Potential " * 20
    compressed = "E|PFP " * 20
    decision = adapt_legacy_report_result(
        original,
        compressed,
        0.99,
        "ST3GG_PTR:deadbeef0000",
    )

    assert decision.enabled is True
    assert decision.measurement_class is ST3GGMeasurementClass.BYTE_EXACT
    assert decision.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY
    assert decision.legacy_pointer == "ST3GG_PTR:deadbeef0000"
    assert "legacy_savings_recomputed" in decision.warnings


def test_golden_vectors_are_stable() -> None:
    original_digest = digest_text('{"a":1,"b":2}')
    assert original_digest == "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    assert exact_ref_for("ARENA", original_digest) == (
        "aura://st3gg/v2/ARENA/"
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )
    assert canonical_pointer("ARENA", original_digest) == "ST3GG2::ARENA:d392355dde82dc78298b0c7872591e4b"
