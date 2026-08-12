from __future__ import annotations

import json
import sqlite3

import pytest

import aura_qdkt as qdkt


def _fresh(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(qdkt, "_MEMPALACE_DB", tmp_path / "mempalace.db")
    monkeypatch.setattr(qdkt, "_WORKSPACE_DB", tmp_path / "workspace.db")
    monkeypatch.setattr(qdkt, "_CRYSTAL_JSON", tmp_path / "qdkt_crystal_cache.json")
    monkeypatch.setattr(qdkt, "_ACCUMULATOR_JSON", tmp_path / "qdkt_pattern_accumulator.json")
    qdkt._CRYSTAL_CACHE.clear()
    qdkt._PATTERN_ACCUMULATOR.clear()
    qdkt._INSTANCE = None
    return qdkt.UnifiedQDKT()


def _observe(engine, concept, confidence=0.9, action="act", **extra):
    payload = dict(extra)
    if action is not None:
        payload["action"] = action
    return engine.observe("test", payload, concept=concept, confidence=confidence)


def test_r0_r6_repetition_only_creates_candidates(monkeypatch, tmp_path):
    engine = _fresh(monkeypatch, tmp_path)

    assert engine.fast_path("fresh") is None  # R0

    _observe(engine, "corr", 0.9, "bad")
    assert engine.fast_path("corr") is None  # R1
    _observe(engine, "corr", 0.9, "bad")
    assert engine.fast_path("corr") is None  # R2
    _observe(engine, "corr", 0.9, "bad")
    candidate = engine.crystallization_candidate("corr")
    assert candidate["state"] == "candidate"  # R3
    assert candidate["independent_source_count"] == 1
    assert engine.fast_path("corr") is None

    for source in ("s1", "s2", "s3"):
        _observe(engine, "independent", 0.9, "good", source_id=source)
    candidate = engine.crystallization_candidate("independent")
    assert candidate["state"] == "candidate"  # R4
    assert candidate["independent_source_count"] == 3
    assert engine.fast_path("independent") is None

    for source in ("n1", "n2", "n3"):
        _observe(engine, "no-action", 0.9, None, source_id=source)
    assert engine.fast_path("no-action") is None  # R5
    assert engine.crystallization_candidate("no-action")["state"] == "accumulating"

    for source in ("l1", "l2", "l3"):
        _observe(engine, "low-confidence", 0.6, "act", source_id=source)
    assert engine.fast_path("low-confidence") is None  # R6
    assert engine.crystallization_candidate("low-confidence")["state"] == "accumulating"


def test_r7_r8_explicit_crystal_and_contradiction_revalidation(monkeypatch, tmp_path):
    engine = _fresh(monkeypatch, tmp_path)

    engine.crystallize(
        "reviewed", "use-this", confidence=0.95, source="reviewed",
        evidence_refs=["ev1"], reviewed_by="J99", policy_ref="POLICY-1",
    )
    assert engine.fast_path("reviewed")["action"] == "use-this"  # R7

    with pytest.raises(ValueError):
        engine.crystallize("bad-promotion", "x", source="auto_threshold")

    engine.crystallize("contradict", "old", source="reviewed", reviewed_by="J99")
    assert engine.fast_path("contradict") is not None
    _observe(engine, "contradict", 0.99, "new", source_id="fresh", contradiction=True)
    assert engine.fast_path("contradict") is None  # R8
    state = engine.query("contradict")["crystal_state"]
    assert state["revalidation_required"] is True
    assert state["revalidation_reason"] == "contradictory_fresh_evidence"


def test_r9_restart_separates_accumulator_and_crystal(monkeypatch, tmp_path):
    engine = _fresh(monkeypatch, tmp_path)
    _observe(engine, "restart-candidate", 0.9, "a", source_id="rc1")
    engine.crystallize("restart-crystal", "b", source="reviewed", reviewed_by="J99")

    qdkt._CRYSTAL_CACHE.clear()
    qdkt._PATTERN_ACCUMULATOR.clear()
    restarted = qdkt.UnifiedQDKT()

    assert restarted.fast_path("restart-candidate") is None
    assert restarted.crystallization_candidate("restart-candidate") is not None
    assert restarted.fast_path("restart-crystal")["action"] == "b"


def test_r10_duplicate_source_is_not_independent(monkeypatch, tmp_path):
    engine = _fresh(monkeypatch, tmp_path)
    for _ in range(3):
        _observe(engine, "duplicate", 0.95, "x", source_id="same-source")

    candidate = engine.crystallization_candidate("duplicate")
    assert candidate["count"] == 3
    assert candidate["independent_source_count"] == 1
    assert engine.fast_path("duplicate") is None


def test_r11_stale_source_generation_disables_fast_path(monkeypatch, tmp_path):
    engine = _fresh(monkeypatch, tmp_path)
    engine.crystallize(
        "stale", "old", source="reviewed", reviewed_by="J99", source_generation="g1"
    )
    assert engine.fast_path("stale") is not None

    _observe(
        engine, "stale", 0.9, "old", source_id="source",
        source_generation="g2", source_stale=True,
    )
    assert engine.fast_path("stale") is None
    state = engine.query("stale")["crystal_state"]
    assert state["revalidation_reason"] == "stale_source_generation"


def test_legacy_conflated_cache_migrates_fail_closed(monkeypatch, tmp_path):
    engine = _fresh(monkeypatch, tmp_path)
    del engine

    legacy_unknown = qdkt._concept_key("legacy-unknown")
    legacy_auto = qdkt._concept_key("legacy-auto")
    explicit = qdkt._concept_key("legacy-explicit")
    qdkt._CRYSTAL_JSON.write_text(json.dumps({
        legacy_unknown: {"action": "u", "confidence": 0.9, "count": 2},
        legacy_auto: {
            "action": "a", "confidence": 0.9, "count": 3, "source": "auto_threshold"
        },
        explicit: {"action": "e", "confidence": 0.9, "count": 1, "source": "reviewed"},
    }), encoding="utf-8")
    with sqlite3.connect(qdkt._WORKSPACE_DB) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO qdkt_crystals VALUES (?,?,?,?,?)",
            (legacy_unknown, "u", 0.9, 2, 1.0),
        )
        conn.execute(
            "INSERT OR REPLACE INTO qdkt_crystals VALUES (?,?,?,?,?)",
            (legacy_auto, "a", 0.9, 3, 1.0),
        )
        conn.commit()

    qdkt._CRYSTAL_CACHE.clear()
    qdkt._PATTERN_ACCUMULATOR.clear()
    migrated = qdkt.UnifiedQDKT()

    assert migrated.fast_path("legacy-unknown") is None
    assert migrated.fast_path("legacy-auto") is None
    assert migrated.fast_path("legacy-explicit")["action"] == "e"
    assert migrated.crystallization_candidate("legacy-auto")["migration_reason"] == (
        "legacy_auto_threshold_requires_revalidation"
    )
    sanitized = json.loads(qdkt._CRYSTAL_JSON.read_text(encoding="utf-8"))
    assert set(sanitized) == {explicit}
