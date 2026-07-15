from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from aura_arena_st3gg_egress import compress_report_st3gg, decompress_report_st3gg
from aura_st3gg_codec import ST3GGCodec, ST3GGProfile
from aura_st3gg_compatibility import (
    REPORT_SOURCE_HINT,
    ST3GGLegacyDisposition,
    compress_report_with_v2_facade,
    dual_read_st3gg_recall,
    encode_source_with_v2_facade,
    p5_3_legacy_disposition,
    project_ast_frame_to_v2,
    project_report_egress_to_v2,
)
from aura_st3gg_contracts import PATCH_AUTHORITY, ST3GGRestorationMode
from aura_st3gg_recall import ST3GG_RECALL_VERSION, index_path_for_ledger


AST_SOURCE = (
    """
from pathlib import Path


def hydrate_records(records, default_name):
    hydrated = []
    for record in records:
        name = record.get("name", default_name)
        tags = sorted(record.get("tags", []))
        if name:
            hydrated.append({"name": name, "tags": tags})
    return hydrated
""".strip()
    + "\n"
) * 12

REPORT_TEXT = (
    "Emergent Properties and Future Potential\n"
    "Verified High-Leverage Clusters\n"
    "Evidence Status Score source_hash source_span required_tests verifier_notes\n"
    "NO_PATCHES NO_CODE_WRITES NO_UNIFIED_DIFF REPORT_ONLY\n"
) * 80


def _exact_report(tmp_path: Path):
    ledger_path = tmp_path / "p5_3_recall.jsonl"
    result = compress_report_with_v2_facade(
        REPORT_TEXT,
        persist_exact=True,
        ledger_path=ledger_path,
        minimum_savings_ratio=0.08,
    )
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.EXACT_RECALL
    assert result.binding is not None
    assert result.recall_evidence is not None
    assert result.recall_evidence.verified is True
    return ledger_path, result


def test_ast_facade_preserves_golden_v1_frame_and_classifies_lossy() -> None:
    direct = ST3GGCodec().encode_source(
        AST_SOURCE,
        source_file="sample.py",
        target_symbol="hydrate_records",
        profile=ST3GGProfile.SUMMARY,
    )
    wrapped = encode_source_with_v2_facade(
        AST_SOURCE,
        source_file="sample.py",
        target_symbol="hydrate_records",
        profile=ST3GGProfile.SUMMARY,
    )

    assert wrapped.legacy_frame == direct
    assert wrapped.v2_decision.restoration_mode in {
        ST3GGRestorationMode.LOSSY_ADVISORY,
        ST3GGRestorationMode.NONE,
    }
    assert wrapped.v2_decision.exact_ref is None
    if wrapped.v2_decision.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY:
        assert wrapped.v2_decision.enabled is True
    assert wrapped.v2_decision.raw_units == ST3GGCodec().estimate_token_cost(AST_SOURCE)
    assert wrapped.v2_decision.candidate_units == ST3GGCodec().estimate_token_cost(direct.encoded)
    assert wrapped.v2_decision.patch_authority == PATCH_AUTHORITY
    assert wrapped.v2_decision.st3gg_patch_authority is False


def test_ast_exact_spans_remain_sidecar_and_never_claim_exact_recall() -> None:
    result = encode_source_with_v2_facade(
        AST_SOURCE,
        source_file="sample.py",
        target_symbol="hydrate_records",
        profile=ST3GGProfile.PATCH,
    )

    assert result.legacy_frame.spans
    assert result.exact_span_count == len(result.legacy_frame.spans)
    assert result.v2_decision.restoration_mode in {
        ST3GGRestorationMode.LOSSY_ADVISORY,
        ST3GGRestorationMode.NONE,
    }
    assert result.v2_decision.exact_ref is None


def test_ast_forged_measurement_fails_closed_to_none() -> None:
    frame = ST3GGCodec().encode_source(AST_SOURCE, profile=ST3GGProfile.SUMMARY)
    forged_metrics = replace(
        frame.metrics,
        raw_token_estimate=frame.metrics.raw_token_estimate + 1,
    )
    forged = replace(frame, metrics=forged_metrics)

    result = project_ast_frame_to_v2(AST_SOURCE, forged, profile=ST3GGProfile.SUMMARY)

    assert result.legacy_frame == forged
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.mismatch_reasons == ("legacy_ast_raw_measurement_disagreement",)


def test_ast_noncanonical_fidelity_metadata_fails_closed() -> None:
    frame = ST3GGCodec().encode_source(AST_SOURCE, profile=ST3GGProfile.SUMMARY)
    changed_fidelity = 0.0 if frame.metrics.fidelity_score != 0.0 else 1.0
    forged = replace(frame, metrics=replace(frame.metrics, fidelity_score=changed_fidelity))

    result = project_ast_frame_to_v2(AST_SOURCE, forged, profile=ST3GGProfile.SUMMARY)

    assert result.legacy_frame == forged
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.mismatch_reasons == ("legacy_ast_frame_replay_disagreement",)


def test_ast_projection_crash_cannot_suppress_v1_frame() -> None:
    direct = ST3GGCodec().encode_source(AST_SOURCE, profile=ST3GGProfile.SUMMARY)

    def boom(_text: str) -> int:
        raise RuntimeError("counter unavailable")

    result = encode_source_with_v2_facade(
        AST_SOURCE,
        profile=ST3GGProfile.SUMMARY,
        count_units=boom,
    )

    assert result.legacy_frame == direct
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.mismatch_reasons == ("legacy_ast_projection_failed:RuntimeError",)


def test_report_facade_preserves_exact_legacy_tuple_without_persistence() -> None:
    direct = compress_report_st3gg(REPORT_TEXT)
    result = compress_report_with_v2_facade(REPORT_TEXT)

    assert result.legacy_result == direct
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY
    assert result.binding is None
    assert result.recall_evidence is None
    assert result.v2_payload == ""
    assert result.legacy_restored_preview == decompress_report_st3gg(direct[0])


def test_report_invalid_unicode_still_preserves_legacy_result() -> None:
    original = "Emergent Properties and Future Potential " * 20 + chr(0xD800)
    direct = compress_report_st3gg(original)

    result = compress_report_with_v2_facade(original)

    assert result.legacy_result == direct
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.mismatch_reasons == ("legacy_report_projection_failed:UnicodeEncodeError",)


def test_report_exact_recall_binds_v2_to_verified_v1_dual_reads(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    binding = result.binding
    evidence = result.recall_evidence
    assert binding is not None
    assert evidence is not None

    assert result.legacy_result == compress_report_st3gg(REPORT_TEXT)
    assert result.v2_payload.endswith("ST3GG_AUTH=false")
    assert binding.pointer == result.v2_decision.pointer
    assert binding.exact_ref == result.v2_decision.exact_ref
    assert binding.storage_owner == ST3GG_RECALL_VERSION
    assert binding.source_hint == REPORT_SOURCE_HINT
    assert evidence.restoration_mode is ST3GGRestorationMode.EXACT_RECALL
    assert {name for name, _digest in evidence.alias_record_digests} == {"pointer", "digest", "dash_key"}
    assert len({digest for _name, digest in evidence.alias_record_digests}) == 1
    assert index_path_for_ledger(ledger_path).exists()


def test_report_canonical_overhead_can_block_exact_without_changing_v1(tmp_path: Path) -> None:
    original = "Emergent Properties and Future Potential " * 4
    direct = compress_report_st3gg(original)
    result = compress_report_with_v2_facade(
        original,
        persist_exact=True,
        ledger_path=tmp_path / "overhead.jsonl",
        minimum_savings_ratio=0.0,
    )

    assert result.legacy_result == direct
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY
    assert result.v2_payload == ""
    assert result.binding is None
    assert "exact_recall_not_admitted:protocol_overhead_erased_savings" in result.mismatch_reasons


def test_report_persistence_failure_preserves_v1_and_downgrades_to_lossy(tmp_path: Path) -> None:
    direct = compress_report_st3gg(REPORT_TEXT)

    def boom(**_kwargs):
        raise RuntimeError("disk unavailable")

    result = compress_report_with_v2_facade(
        REPORT_TEXT,
        persist_exact=True,
        ledger_path=tmp_path / "boom.jsonl",
        upsert_record=boom,
    )

    assert result.legacy_result == direct
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.LOSSY_ADVISORY
    assert result.binding is None
    assert result.recall_evidence is None
    assert any(
        item.startswith("exact_recall_not_admitted:exact_recall_persistence_failed")
        for item in result.mismatch_reasons
    )


def test_malformed_report_pointer_fails_closed_to_none() -> None:
    compact, savings, _pointer = compress_report_st3gg(REPORT_TEXT)
    result = project_report_egress_to_v2(
        REPORT_TEXT,
        compact,
        savings,
        "ST3GG_PTR:not-hex",
    )

    assert result.legacy_compressed == compact
    assert result.legacy_pointer == "ST3GG_PTR:not-hex"
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.mismatch_reasons == ("legacy_report_pointer_malformed",)


def test_empty_report_is_explicit_none() -> None:
    result = compress_report_with_v2_facade("")

    assert result.legacy_result == ("", 0.0, "")
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.v2_decision.reason == "empty_report"


def test_dual_read_rejects_pointer_substitution(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    assert result.binding is not None
    substituted = replace(
        result.binding,
        legacy_recall_pointer="ST3GG-L2::TEXT_PLAIN:ABCD:0000000000000000",
    )

    evidence = dual_read_st3gg_recall(
        substituted,
        ledger_path=ledger_path,
        expected_original=REPORT_TEXT,
        expected_compact=result.legacy_compressed,
    )

    assert evidence.verified is False
    assert evidence.restoration_mode is ST3GGRestorationMode.NONE
    assert evidence.mismatch_reasons == ("legacy_json_digest_alias_disagreement",)


def test_dual_read_rejects_json_alias_disagreement(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    assert result.binding is not None
    index_path = index_path_for_ledger(ledger_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["aliases"][result.binding.original_digest] = "ST3GG-L2::TEXT_PLAIN:ABCD:0000000000000000"
    index_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    evidence = dual_read_st3gg_recall(result.binding, ledger_path=ledger_path)

    assert evidence.verified is False
    assert evidence.mismatch_reasons == ("legacy_json_digest_alias_disagreement",)


def test_dual_read_rejects_duplicate_conflicting_record(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    assert result.binding is not None
    index_path = index_path_for_ledger(ledger_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    original_record = dict(payload["records"][result.binding.legacy_recall_pointer])
    duplicate_pointer = "ST3GG-L2::TEXT_PLAIN:ABCD:0000000000000000"
    original_record["pointer"] = duplicate_pointer
    payload["records"][duplicate_pointer] = original_record
    index_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    evidence = dual_read_st3gg_recall(result.binding, ledger_path=ledger_path)

    assert evidence.verified is False
    assert evidence.mismatch_reasons == ("legacy_duplicate_or_conflicting_records",)


def test_dual_read_rejects_noncanonical_record_metadata(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    assert result.binding is not None
    index_path = index_path_for_ledger(ledger_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["records"][result.binding.legacy_recall_pointer]["glyph"] = "ZZZZ"
    index_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    evidence = dual_read_st3gg_recall(result.binding, ledger_path=ledger_path)

    assert evidence.verified is False
    assert evidence.mismatch_reasons == ("legacy_record_glyph_malformed",)


def test_dual_read_rejects_digest_bound_length_disagreement(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    assert result.binding is not None
    forged = replace(result.binding, original_bytes=result.binding.original_bytes + 1)

    evidence = dual_read_st3gg_recall(
        forged,
        ledger_path=ledger_path,
        expected_original=REPORT_TEXT,
        expected_compact=result.legacy_compressed,
    )

    assert evidence.verified is False
    assert evidence.mismatch_reasons == ("legacy_record_original_length_mismatch",)


def test_dual_read_evidence_digest_is_deterministic(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    assert result.binding is not None
    first = dual_read_st3gg_recall(result.binding, ledger_path=ledger_path)
    second = dual_read_st3gg_recall(result.binding, ledger_path=ledger_path)

    assert first.verified is True
    assert first.evidence_digest == second.evidence_digest


def test_p5_3_explicitly_retains_v1() -> None:
    decision = p5_3_legacy_disposition()

    assert decision.disposition is ST3GGLegacyDisposition.RETAIN_V1
    assert "v1_storage_is_still_the_only_persisted_exact_original_owner" in decision.blockers
    assert decision.proposal_only is True
    assert decision.st3gg_patch_authority is False
    assert len(decision.decision_digest) == 32
