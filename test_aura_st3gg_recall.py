from pathlib import Path

from aura_st3gg_recall import (
    FROZEN_COMPACTION_ALIAS_THRESHOLD,
    ST3GGRecallRecord,
    ST3GG_RECALL_VERSION,
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


def test_st3gg_record_round_trip_jsonable():
    original_record = ST3GGRecallRecord(
        pointer="ST3GG-L2::CCR:ABCD:0123456789abcdef0123456789abcdef",
        dash_key="0123456789abcdef",
        glyph="ABCD",
        holographic_header="dGVzdGhlYWRlcg",
        original_hash="aura_ccr_test_hash",
        content_type="json",
        original='{"answer":42}',
        compressed="[AURA_CCR]",
        source_hint="unit_test",
        created_unix=1782313426.0,
    )

    payload = original_record.to_jsonable()
    restored = ST3GGRecallRecord.from_jsonable(payload)

    assert payload["version"] == ST3GG_RECALL_VERSION
    assert restored == original_record


def test_compile_visible_capsule_with_dict_input():
    capsule = compile_visible_st3gg_capsule({"alpha": "first", "beta": "second", "gamma": "third"})

    assert capsule is not None
    assert capsule.startswith("ST3GG1|S=A901|M=dict|")
    capsule.encode("ascii")
    assert "|D=" in capsule


def test_compile_visible_capsule_returns_none_for_empty_or_non_structured_input():
    assert compile_visible_st3gg_capsule({}) is None
    assert compile_visible_st3gg_capsule([]) is None
    assert compile_visible_st3gg_capsule("string") is None
    assert compile_visible_st3gg_capsule(42) is None
    assert compile_visible_st3gg_capsule(None) is None
    assert compile_visible_st3gg_capsule(["a", "b", "c"]) is None


def test_lookup_st3gg_recall_returns_none_for_missing_key(tmp_path: Path):
    assert lookup_st3gg_recall(
        "nonexistent_key",
        ledger_path=tmp_path / "empty.jsonl",
    ) is None


def test_lookup_st3gg_recall_returns_none_for_wrong_key_in_existing_ledger(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"
    upsert_st3gg_recall(
        ledger_path=ledger,
        original_hash="real_hash",
        content_type="text",
        original="hello world",
    )

    assert lookup_st3gg_recall("completely_wrong_key", ledger_path=ledger) is None


def test_compute_compaction_efficiency_single_key():
    stats = compute_compaction_efficiency(
        raw_keys_count=1,
        file_size_bytes=64,
        lookup_latency_sec=0.0,
    )

    assert stats["allocated_bits_per_key"] == 512.0
    assert stats["metric_profile"] == "AURA_ST3GG_HASH_COMPACTION_ANALYTICS"
    assert stats["recall_complexity_profile"] == "BOUNDED_O_1_ACTIVE_HASH"
    assert stats["space_optimization_ratio"] < 1.0


def test_compute_compaction_efficiency_zero_keys_does_not_crash():
    stats = compute_compaction_efficiency(
        raw_keys_count=0,
        file_size_bytes=0,
        lookup_latency_sec=0.0,
    )

    assert isinstance(stats["allocated_bits_per_key"], float)
    assert stats["metric_profile"] == "AURA_ST3GG_HASH_COMPACTION_ANALYTICS"


def test_frozen_compaction_recommended_threshold_is_documented(tmp_path: Path):
    stats = st3gg_recall_index_stats(tmp_path / "context_crush.jsonl")

    assert stats["frozen_compaction_recommended"] is False
    assert FROZEN_COMPACTION_ALIAS_THRESHOLD == 4096


def test_sidecar_path_naming_conventions(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"

    index = index_path_for_ledger(ledger)
    store = store_path_for_ledger(ledger)
    hash_table = hash_table_path_for_ledger(ledger)

    assert str(index).endswith(".jsonl.st3gg_index.json")
    assert str(store).endswith(".jsonl.st3gg_store.jsonl")
    assert str(hash_table).endswith(".jsonl.st3gg_hash.bin")
    assert index.parent == ledger.parent
    assert store.parent == ledger.parent
    assert hash_table.parent == ledger.parent


def test_upsert_creates_all_sidecar_files(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"

    upsert_st3gg_recall(
        ledger_path=ledger,
        original_hash="upsert_test_hash",
        content_type="text",
        original="some original content",
        compressed="[CRUSH]",
        source_hint="unit",
    )

    assert index_path_for_ledger(ledger).exists()
    assert store_path_for_ledger(ledger).exists()
    assert hash_table_path_for_ledger(ledger).exists()


def test_upsert_record_pointer_format():
    pointer, dash_key, glyph, header = compile_st3gg_pointer("test content", namespace="JSON")

    assert pointer.startswith("ST3GG-L2::JSON:")
    assert glyph in pointer
    assert dash_key in pointer
    pointer.encode("ascii")
    header.encode("ascii")
    int(dash_key, 16)


def test_upsert_and_lookup_returns_correct_record_fields(tmp_path: Path):
    ledger = tmp_path / "context_crush.jsonl"

    record = upsert_st3gg_recall(
        ledger_path=ledger,
        original_hash="field_check_hash",
        content_type="log",
        original="important log content",
        compressed="[LOG_CRUSH]",
        source_hint="integration",
    )

    assert record.original_hash == "field_check_hash"
    assert record.content_type == "log"
    assert record.original == "important log content"
    assert record.compressed == "[LOG_CRUSH]"
    assert record.source_hint == "integration"
    assert record.pointer.startswith("ST3GG-L2::")
    assert record.dash_key
    assert record.glyph
    assert record.holographic_header
    assert record.created_unix > 0


def test_st3gg_recall_index_stats_empty_ledger(tmp_path: Path):
    stats = st3gg_recall_index_stats(tmp_path / "empty_ledger.jsonl")

    assert stats["index_profile"] == "AURA_ST3GG_OPEN_ADDRESS_HASH"
    assert stats["hash_capacity"] == 0
    assert stats["indexed_alias_count"] == 0
    assert stats["estimated_record_count"] == 0
    assert stats["frozen_compaction_recommended"] is False
    assert stats["future_frozen_profile"] == "PTRHASH_OR_TPH_MPHF_SEGMENT"


def test_visible_capsule_max_rows_truncates_list():
    capsule = compile_visible_st3gg_capsule([{"k": str(i)} for i in range(50)], max_rows=10)

    assert capsule is not None
    assert "O=40" in capsule


def test_compile_visible_capsule_seed_is_reflected_in_output():
    data = {"x": 1}
    capsule_default = compile_visible_st3gg_capsule(data, seed=0xA901)
    capsule_alt = compile_visible_st3gg_capsule(data, seed=0xBEEF)

    assert capsule_default != capsule_alt
    assert "S=A901" in capsule_default
    assert "S=BEEF" in capsule_alt
