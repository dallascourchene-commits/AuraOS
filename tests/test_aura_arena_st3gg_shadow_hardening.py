from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import aura_arena_st3gg_shadow as shadow_module
from aura_arena_st3gg_codec import PATCH_AUTHORITY, encode_arena_capsule_for_egress
from aura_arena_st3gg_shadow import (
    encode_arena_capsule_with_v2_shadow,
    project_arena_st3gg_v2_shadow,
)
from aura_st3gg_recall import lookup_st3gg_recall


def _large_capsule() -> dict:
    neighbors = [
        {
            "id": f"module.py::symbol_{index}",
            "file_path": "module.py",
            "symbol": f"symbol_{index}",
            "node_type": "function",
            "summary": "deterministic repeated topology evidence " * 8,
        }
        for index in range(80)
    ]
    return {
        "capsule_version": "AURA_CODING_ARENA_CAPSULE_V1",
        "op": "patch",
        "selected": {"node_ids": ["module.py::symbol_1"]},
        "context": {
            "target_files": ["module.py"],
            "target_symbols": ["symbol_1"],
            "line_ranges": [
                {
                    "node_id": "module.py::symbol_1",
                    "file_path": "module.py",
                    "line_range": [1, 20],
                }
            ],
            "tests": ["test_module.py"],
            "neighbors": neighbors,
        },
        "route_decision": {"route": "LOCAL_DETERMINISTIC", "network_calls_made": False},
        "jspace_packet": "J0/S=code>A=patch#READY_PATCH",
        "jspace_state": {
            "next_state": "READY_PATCH",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        },
        "phase_hash": "large",
    }


def _ledger(root: Path) -> Path:
    return root / "Aura_Memory" / "st3gg_arena_recall.jsonl"


def _live_record(legacy, root: Path):
    record = lookup_st3gg_recall(
        legacy.decision.st3gg_pointer or "",
        ledger_path=_ledger(root),
    )
    assert record is not None
    return record


def test_wrapper_returns_unchanged_v1_when_projection_itself_crashes(monkeypatch, tmp_path: Path) -> None:
    def crash_projection(*args, **kwargs):
        raise RuntimeError("forced shadow failure")

    monkeypatch.setattr(shadow_module, "project_arena_st3gg_v2_shadow", crash_projection)
    result = encode_arena_capsule_with_v2_shadow(_large_capsule(), recall_root=tmp_path)

    assert result.legacy_capsule.decision.enabled is True
    assert result.legacy_capsule.payload.startswith("ST3GG1|")
    assert result.comparison.v2_decision.enabled is False
    assert result.comparison.mismatch_reasons == ("shadow_projection_failed:RuntimeError",)


def test_digest_alias_must_recover_the_same_v1_record(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    record = _live_record(legacy, tmp_path)

    def pointer_only_lookup(key: str, *, ledger_path: Path):
        return record if key == record.pointer else None

    comparison = project_arena_st3gg_v2_shadow(
        capsule,
        legacy,
        recall_root=tmp_path,
        lookup_record=pointer_only_lookup,
    )

    assert comparison.exact_recall_verified is False
    assert comparison.v2_decision.enabled is False
    assert comparison.legacy_record_pointer == record.pointer
    assert comparison.mismatch_reasons == ("legacy_digest_alias_missing",)


def test_digest_alias_record_substitution_is_rejected(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    record = _live_record(legacy, tmp_path)
    substituted = replace(record, created_unix=record.created_unix + 1.0)

    def substituted_alias_lookup(key: str, *, ledger_path: Path):
        if key == record.pointer:
            return record
        if key == record.original_hash:
            return substituted
        return None

    comparison = project_arena_st3gg_v2_shadow(
        capsule,
        legacy,
        recall_root=tmp_path,
        lookup_record=substituted_alias_lookup,
    )

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_digest_alias_record_substitution",)


def test_forged_v1_phase_hash_is_rejected(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    forged = replace(legacy, phase_hash="0" * 32)

    comparison = project_arena_st3gg_v2_shadow(capsule, forged, recall_root=tmp_path)

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_phase_hash_disagreement",)


def test_forged_v1_measurement_is_rejected_before_exact_claim(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    forged_decision = replace(
        legacy.decision,
        raw_tokens_est=legacy.decision.raw_tokens_est + 1,
    )
    forged = replace(legacy, decision=forged_decision)

    comparison = project_arena_st3gg_v2_shadow(capsule, forged, recall_root=tmp_path)

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_raw_measurement_disagreement",)


def test_noncanonical_live_v1_mode_is_rejected(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    forged = replace(legacy, mode="not-the-v1-mode")

    comparison = project_arena_st3gg_v2_shadow(capsule, forged, recall_root=tmp_path)

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_capsule_mode_noncanonical",)


def test_comparison_carries_the_complete_live_v1_decision(tmp_path: Path) -> None:
    result = encode_arena_capsule_with_v2_shadow(_large_capsule(), recall_root=tmp_path)

    assert result.comparison.legacy_decision == result.legacy_capsule.decision
    assert result.comparison.to_dict()["legacy_decision"]["reason"] == "savings_threshold_met"
    assert result.comparison.to_dict()["legacy_decision"]["warnings"] == list(
        result.legacy_capsule.decision.warnings
    )
