from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from aura_arena_st3gg_egress import compress_report_st3gg
from aura_st3gg_compatibility import (
    compress_report_with_v2_facade,
    dual_read_st3gg_recall,
    encode_source_with_v2_facade,
    project_report_egress_to_v2,
)
from aura_st3gg_contracts import ST3GGRestorationMode
from aura_st3gg_recall import index_path_for_ledger, lookup_st3gg_recall

REPORT_TEXT = (
    "Emergent Properties and Future Potential\n"
    "Verified High-Leverage Clusters\n"
    "Evidence Status Score source_hash source_span required_tests verifier_notes\n"
    "NO_PATCHES NO_CODE_WRITES NO_UNIFIED_DIFF REPORT_ONLY\n"
) * 80

AST_SOURCE = "def hydrate(value):\n    return value + 1\n" * 80


def _exact_report(tmp_path: Path):
    ledger_path = tmp_path / "constructor_hardening.jsonl"
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


def test_verified_evidence_rejects_missing_alias_proof(tmp_path: Path) -> None:
    _ledger_path, result = _exact_report(tmp_path)

    with pytest.raises(ValueError, match="verified_alias_evidence_incomplete"):
        replace(result.recall_evidence, alias_record_digests=())


def test_verified_evidence_rejects_json_digest_disagreement(tmp_path: Path) -> None:
    _ledger_path, result = _exact_report(tmp_path)

    with pytest.raises(ValueError, match="verified_json_evidence_disagreement"):
        replace(result.recall_evidence, json_index_record_digest="0" * 64)


def test_exact_binding_rejects_compact_pointer_disagreement(tmp_path: Path) -> None:
    _ledger_path, result = _exact_report(tmp_path)

    with pytest.raises(ValueError, match="binding_surface_pointer_digest_mismatch"):
        replace(result.binding, legacy_compact_digest="0" * 64)


def test_ast_result_rejects_forged_frame_digest() -> None:
    result = encode_source_with_v2_facade(AST_SOURCE)

    with pytest.raises(ValueError, match="ast_frame_digest_disagreement"):
        replace(result, legacy_frame_digest="0" * 64)


def test_invalid_legacy_savings_fails_closed_without_second_exception() -> None:
    compressed, _savings, pointer = compress_report_st3gg(REPORT_TEXT)

    result = project_report_egress_to_v2(REPORT_TEXT, compressed, 2.0, pointer)

    assert result.legacy_result == (compressed, 0.0, pointer)
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.mismatch_reasons == ("legacy_savings_ratio_invalid",)


def test_forged_in_range_legacy_savings_fails_closed() -> None:
    compressed, savings, pointer = compress_report_st3gg(REPORT_TEXT)
    forged = 0.0 if savings != 0.0 else 0.5

    result = project_report_egress_to_v2(REPORT_TEXT, compressed, forged, pointer)

    assert result.legacy_result == (compressed, forged, pointer)
    assert result.v2_decision.restoration_mode is ST3GGRestorationMode.NONE
    assert result.mismatch_reasons == ("legacy_report_savings_disagreement",)


def test_dual_read_rejects_created_timestamp_substitution(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    original_record = lookup_st3gg_recall(
        result.binding.legacy_recall_pointer,
        ledger_path=ledger_path,
    )
    assert original_record is not None
    index_path = index_path_for_ledger(ledger_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    record = payload["records"][result.binding.legacy_recall_pointer]
    record["created_unix"] = float(record["created_unix"]) + 1.0
    index_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    evidence = dual_read_st3gg_recall(
        result.binding,
        ledger_path=ledger_path,
        lookup_record=lambda *_args, **_kwargs: original_record,
    )

    assert evidence.verified is False
    assert evidence.mismatch_reasons == ("legacy_pointer_record_substitution",)


def test_failed_evidence_cannot_carry_resolved_exact_state(tmp_path: Path) -> None:
    ledger_path, result = _exact_report(tmp_path)
    substituted = replace(
        result.binding,
        legacy_recall_pointer="ST3GG-L2::TEXT_PLAIN:ABCD:0000000000000000",
    )
    failed = dual_read_st3gg_recall(substituted, ledger_path=ledger_path)
    assert failed.verified is False

    with pytest.raises(ValueError, match="failed_evidence_carries_verified_state"):
        replace(failed, resolved_pointer=substituted.legacy_recall_pointer)
