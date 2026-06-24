from pathlib import Path

from aura_st3gg_recall import (
    compile_st3gg_pointer,
    compile_visible_st3gg_capsule,
    compute_compaction_efficiency,
    hash_table_path_for_ledger,
    index_path_for_ledger,
    lookup_st3gg_recall,
    st3gg_recall_index_stats,
    store_path_for_ledger,
    upsert_st3gg_recall,
)


def test_st3gg_pointer_is_deterministic_visible_ascii():
    first = compile_st3gg_pointer("paper chunk", namespace="PAPER")
    second = compile_st3gg_pointer("paper chunk", namespace="PAPER")

    assert first == second
    pointer, dash_key, glyph, header = first
    assert pointer.startswith("ST3GG-L2::PAPER:")
    assert dash_key
    assert glyph
    assert header
    pointer.encode("ascii")
    header.encode("ascii")


def test_st3gg_sidecar_lookup_by_hash_pointer_and_dash_key(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"

    record = upsert_st3gg_recall(
        ledger_path=ledger,
        original_hash="aura_ccr_test",
        content_type="json",
        original='{"answer":42}',
        compressed="[AURA_CCR]",
        source_hint="unit",
    )

    assert index_path_for_ledger(ledger).exists()
    assert lookup_st3gg_recall("aura_ccr_test", ledger_path=ledger) == record
    assert lookup_st3gg_recall(record.pointer, ledger_path=ledger) == record
    assert lookup_st3gg_recall(record.dash_key, ledger_path=ledger) == record
    assert hash_table_path_for_ledger(ledger).exists()
    assert store_path_for_ledger(ledger).exists()


def test_st3gg_hash_sidecar_survives_without_json_index(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"
    record = upsert_st3gg_recall(
        ledger_path=ledger,
        original_hash="aura_ccr_hash_only",
        content_type="log",
        original="important line",
        compressed="[AURA_LOG_CRUSH]",
    )
    index_path_for_ledger(ledger).unlink()

    assert lookup_st3gg_recall("aura_ccr_hash_only", ledger_path=ledger) == record
    assert lookup_st3gg_recall(record.pointer, ledger_path=ledger) == record


def test_visible_st3gg_capsule_is_ascii_and_structural():
    capsule = compile_visible_st3gg_capsule([
        {"path": "a.py", "line": 1, "message": "same schema"},
        {"path": "b.py", "line": 2, "message": "same schema"},
    ])

    assert capsule is not None
    assert capsule.startswith("ST3GG1|S=A901|M=rows|")
    capsule.encode("ascii")
    assert "\u200b" not in capsule


def test_compaction_efficiency_reports_bits_per_key():
    stats = compute_compaction_efficiency(
        raw_keys_count=100,
        file_size_bytes=200,
        lookup_latency_sec=0.001,
    )

    assert stats["metric_profile"] == "AURA_ST3GG_HASH_COMPACTION_ANALYTICS"
    assert stats["allocated_bits_per_key"] == 16.0
    assert stats["mphf_lower_bound_bits_per_key"] == 1.44
    assert stats["recall_complexity_profile"] == "BOUNDED_O_1_ACTIVE_HASH"


def test_st3gg_recall_index_stats_reports_active_sidecar(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"
    for idx in range(3):
        upsert_st3gg_recall(
            ledger_path=ledger,
            original_hash=f"aura_ccr_{idx}",
            content_type="json",
            original=f'{{"idx":{idx}}}',
            compressed="[AURA_CCR]",
        )

    stats = st3gg_recall_index_stats(ledger)

    assert stats["index_profile"] == "AURA_ST3GG_OPEN_ADDRESS_HASH"
    assert stats["hash_capacity"] >= 2048
    assert stats["indexed_alias_count"] == 9
    assert stats["estimated_record_count"] == 3
    assert stats["hash_table_bytes"] > 0
    assert stats["record_store_bytes"] > 0
    assert stats["json_compat_index_bytes"] > 0
    assert stats["frozen_compaction_recommended"] is False
