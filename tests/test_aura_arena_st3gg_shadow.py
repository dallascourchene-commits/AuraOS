from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from aura_arena_st3gg_codec import (
    PATCH_AUTHORITY,
    ArenaST3GGCapsule,
    encode_arena_capsule_for_egress,
)
from aura_arena_st3gg_shadow import (
    ARENA_ST3GG_SHADOW_VERSION,
    V1_STORAGE_OWNER,
    V2_EXECUTION_MODE,
    encode_arena_capsule_with_v2_shadow,
    project_arena_st3gg_v2_shadow,
)
from aura_st3gg_contracts import ST3GGRestorationMode, canonical_pointer, exact_ref_for
from aura_st3gg_recall import lookup_st3gg_recall


def _golden_capsule() -> dict:
    return {"a": "x" * 500}


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


def _record_for(view: ArenaST3GGCapsule, root: Path):
    record = lookup_st3gg_recall(
        view.decision.st3gg_pointer or "",
        ledger_path=root / "Aura_Memory" / "st3gg_arena_recall.jsonl",
    )
    assert record is not None
    return record


def test_shadow_wrapper_preserves_exact_v1_golden_bytes(tmp_path: Path) -> None:
    direct = encode_arena_capsule_for_egress(
        _golden_capsule(),
        min_raw_chars=0,
        min_savings_ratio=0.0,
        recall_root=tmp_path / "direct",
    )
    shadow = encode_arena_capsule_with_v2_shadow(
        _golden_capsule(),
        min_raw_chars=0,
        min_savings_ratio=0.0,
        recall_root=tmp_path / "shadow",
    )
    expected = (
        "ST3GG1|S=A901|M=dict|K=K033:a|D=K033="
        + ("x" * 180)
        + "|PTR=ST3GG-L2::ARENA:B142:432fd7d62a33716c"
        "|HASH=164585c8407d8fc047404c23926659d0f04d92de81b0e171301478c7cee0edc8"
        "|MARK=<<aura_arena_st3gg:164585c8407d8fc047404c23926659d0f04d92de81b0e171301478c7cee0edc8>>"
        "|AUTH=exact_source_spans_and_hashes_only|VSA_AUTH=false"
    )

    assert direct.payload.encode("ascii") == expected.encode("ascii")
    assert shadow.legacy_capsule == direct
    assert shadow.legacy_capsule.payload.encode("ascii") == expected.encode("ascii")
    assert shadow.comparison.exact_recall_verified is True


def test_large_v1_record_projects_to_enabled_canonical_v2_exact_recall(tmp_path: Path) -> None:
    result = encode_arena_capsule_with_v2_shadow(_large_capsule(), recall_root=tmp_path)
    comparison = result.comparison
    decision = comparison.v2_decision

    assert result.legacy_capsule.decision.enabled is True
    assert comparison.eligible is True
    assert comparison.exact_recall_verified is True
    assert comparison.version == ARENA_ST3GG_SHADOW_VERSION
    assert comparison.execution_mode == V2_EXECUTION_MODE
    assert comparison.v1_storage_owner == V1_STORAGE_OWNER
    assert decision.enabled is True
    assert decision.restoration_mode is ST3GGRestorationMode.EXACT_RECALL
    assert decision.pointer == canonical_pointer("ARENA", decision.original_digest)
    assert decision.exact_ref == exact_ref_for("ARENA", decision.original_digest)
    assert decision.final_units == decision.candidate_units + decision.overhead_units
    assert decision.legacy_pointer == result.legacy_capsule.decision.st3gg_pointer
    assert comparison.legacy_record_pointer == result.legacy_capsule.decision.st3gg_pointer
    assert comparison.mismatch_reasons == ()
    assert comparison.patch_authority == PATCH_AUTHORITY
    assert comparison.st3gg_patch_authority is False


def test_missing_v1_record_fails_closed_without_changing_v1_output(tmp_path: Path) -> None:
    result = encode_arena_capsule_with_v2_shadow(
        _large_capsule(),
        recall_root=tmp_path,
        lookup_record=lambda *args, **kwargs: None,
    )

    assert result.legacy_capsule.decision.enabled is True
    assert result.legacy_capsule.payload.startswith("ST3GG1|")
    assert result.comparison.eligible is False
    assert result.comparison.exact_recall_verified is False
    assert result.comparison.v2_decision.enabled is False
    assert result.comparison.mismatch_reasons == ("legacy_exact_record_missing",)


def test_stale_v1_record_is_rejected(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    record = _record_for(legacy, tmp_path)
    stale = replace(record, original=record.original + " ")

    comparison = project_arena_st3gg_v2_shadow(
        capsule,
        legacy,
        recall_root=tmp_path,
        lookup_record=lambda *args, **kwargs: stale,
    )

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_exact_record_stale",)


def test_v1_pointer_substitution_is_rejected(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    record = _record_for(legacy, tmp_path)
    substituted = replace(record, pointer=record.pointer + "-other")

    comparison = project_arena_st3gg_v2_shadow(
        capsule,
        legacy,
        recall_root=tmp_path,
        lookup_record=lambda *args, **kwargs: substituted,
    )

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_record_pointer_substitution",)


def test_v1_digest_disagreement_is_rejected(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    record = _record_for(legacy, tmp_path)
    disagreed = replace(record, original_hash="0" * 64)

    comparison = project_arena_st3gg_v2_shadow(
        capsule,
        legacy,
        recall_root=tmp_path,
        lookup_record=lambda *args, **kwargs: disagreed,
    )

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_record_digest_disagreement",)


def test_noncanonical_v1_record_metadata_is_rejected(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    record = _record_for(legacy, tmp_path)
    noncanonical = replace(record, content_type="arena")

    comparison = project_arena_st3gg_v2_shadow(
        capsule,
        legacy,
        recall_root=tmp_path,
        lookup_record=lambda *args, **kwargs: noncanonical,
    )

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_record_content_type_noncanonical",)


def test_empty_legacy_compact_candidate_is_rejected_before_exact_claim(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    pointer = legacy.decision.st3gg_pointer or ""
    digest = legacy.original_hash or ""
    suffix_only = (
        f"|PTR={pointer}|HASH={digest}|MARK=<<aura_arena_st3gg:{digest}>>|"
        f"AUTH={PATCH_AUTHORITY}|VSA_AUTH=false"
    )
    forged = replace(legacy, payload=suffix_only)

    comparison = project_arena_st3gg_v2_shadow(capsule, forged, recall_root=tmp_path)

    assert comparison.v2_decision.enabled is False
    assert comparison.mismatch_reasons == ("legacy_compact_candidate_empty",)


def test_canonical_overhead_can_disable_v2_while_v1_remains_live(tmp_path: Path) -> None:
    result = encode_arena_capsule_with_v2_shadow(
        _golden_capsule(),
        min_raw_chars=0,
        min_savings_ratio=0.0,
        recall_root=tmp_path,
    )

    assert result.legacy_capsule.decision.enabled is True
    assert result.comparison.eligible is True
    assert result.comparison.exact_recall_verified is True
    assert result.comparison.v2_decision.enabled is False
    assert result.comparison.v2_decision.reason == "protocol_overhead_erased_savings"
    assert result.comparison.mismatch_reasons == (
        "v2_not_enabled:protocol_overhead_erased_savings",
    )


def test_shadow_comparison_is_deterministic_and_read_only(tmp_path: Path) -> None:
    capsule = _large_capsule()
    legacy = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)
    first = project_arena_st3gg_v2_shadow(capsule, legacy, recall_root=tmp_path)
    second = project_arena_st3gg_v2_shadow(capsule, legacy, recall_root=tmp_path)

    assert first == second
    assert first.comparison_digest == second.comparison_digest
    assert first.v2_decision.proposal_only is True
    assert first.v2_decision.st3gg_patch_authority is False
