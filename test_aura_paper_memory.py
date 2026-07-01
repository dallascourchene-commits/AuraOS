import base64
import json

import numpy as np

from aura_paper_memory import (
    DIMENSIONS,
    HEADER_BYTES,
    AuraResonanceEgressGate,
    EgressResonancePayload,
    ResearchProfileVector,
    compile_paper_memory_record,
    encode_text_as_phasor,
    load_research_profiles_from_jsonl,
    record_to_trace_content,
    track_egress_savings,
    upsert_paper_memory_record,
    verify_egress_contract,
)


def test_compile_paper_memory_record_builds_header_points_and_vectors():
    record = compile_paper_memory_record(
        doc_id="ARXIV_2501.00001",
        title="Resonance Augmented Egress Core",
        abstract=(
            "We propose a deterministic middleware gate for low-token egress. "
            "The method demonstrates resonance lookup over stored paper vectors. "
            "Results show compact context injection before provider calls."
        ),
        full_text=(
            "The system stores chunk-level phasor vectors and a holographic header. "
            "It preserves metadata for recall and routes only dense brackets at egress."
        ),
        authors=("Aura Lab",),
        categories=("cs.AI",),
        published="2026-06-23T00:00:00",
        source_url="https://arxiv.org/abs/2501.00001",
        pdf_url="https://arxiv.org/pdf/2501.00001",
    )

    assert record.structural_vector.shape == (DIMENSIONS,)
    assert record.structural_vector.dtype == np.complex64
    assert len(base64.b64decode(record.holographic_header)) == HEADER_BYTES
    assert len([point for point in record.three_main_points if point]) == 3
    assert record.metadata["chunk_count"] >= 1
    assert record.single_seed_lift is not None
    assert record.single_seed_lift.seed_id.startswith("ARXIV_2501.00001")
    assert record.metadata["single_seed_lift_version"] == record.single_seed_lift.version


def test_paper_memory_ledger_round_trips_research_profiles(tmp_path):
    ledger = tmp_path / "paper_memory_ledger.jsonl"
    record = compile_paper_memory_record(
        doc_id="ARXIV_LEDGER",
        title="Ledger Test",
        abstract="We show that a paper-memory record can round trip through JSONL.",
    )

    upsert_paper_memory_record(record, ledger)
    profiles = load_research_profiles_from_jsonl(ledger)

    assert len(profiles) == 1
    assert profiles[0].doc_id == "ARXIV_LEDGER"
    assert profiles[0].structural_vector.shape == (DIMENSIONS,)
    assert profiles[0].single_seed_lift is not None
    assert profiles[0].single_seed_lift.vector_count >= 1


def test_legacy_paper_memory_rows_still_load_without_lift_profile(tmp_path):
    ledger = tmp_path / "legacy_paper_memory_ledger.jsonl"
    record = compile_paper_memory_record(
        doc_id="ARXIV_LEGACY",
        title="Legacy Test",
        abstract="Legacy paper rows may not have single seed lift fields.",
    )
    payload = record.to_jsonable()
    payload.pop("single_seed_lift", None)
    ledger.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    profiles = load_research_profiles_from_jsonl(ledger)

    assert len(profiles) == 1
    assert profiles[0].doc_id == "ARXIV_LEGACY"
    assert profiles[0].single_seed_lift is None


def test_raec_gate_selects_highest_resonance_profile():
    intent = "resonance augmented egress core"
    match = ResearchProfileVector(
        doc_id="MATCH",
        summary_capsule="P1=matching context",
        structural_vector=encode_text_as_phasor(intent),
    )
    miss = ResearchProfileVector(
        doc_id="MISS",
        summary_capsule="P1=distant context",
        structural_vector=encode_text_as_phasor("unrelated cache eviction"),
    )

    payload = AuraResonanceEgressGate().inject_latent_context(
        intent,
        [miss, match],
        "test-provider",
    )

    assert payload.slot_matrix_string.startswith("[ANCHOR_ID:MATCH]")
    assert "[CONSTRAINTS:P1=matching context]" in payload.slot_matrix_string
    assert payload.target_provider == "test-provider"


def test_raec_gate_includes_single_seed_lift_capsule_from_ledger(tmp_path):
    ledger = tmp_path / "paper_memory_ledger.jsonl"
    record = compile_paper_memory_record(
        doc_id="ARXIV_LIFT",
        title="Cofactor-Free Single Seed Context Lift",
        abstract="We demonstrate cached inverse dispatch for compact context recall.",
        full_text="The lifted seed profile avoids global recomputation for every egress call.",
    )
    upsert_paper_memory_record(record, ledger)
    profiles = load_research_profiles_from_jsonl(ledger)

    payload = AuraResonanceEgressGate().inject_latent_context(
        "cached inverse dispatch",
        profiles,
        "test-provider",
    )

    assert "LIFT=SEED=" in payload.slot_matrix_string
    assert len(payload.lift_dispatch) == 1
    assert payload.lift_dispatch[0]["version"] == record.single_seed_lift.version


def test_verify_egress_contract_rejects_incomplete_payloads():
    valid = EgressResonancePayload("prompt", "[ANCHOR_ID:X][CONSTRAINTS:Y]", "p")

    assert verify_egress_contract(valid, "root ::= command")
    assert not verify_egress_contract(
        EgressResonancePayload("", "[ANCHOR_ID:X]", "p"),
        "root ::= command",
    )
    assert not verify_egress_contract(
        EgressResonancePayload("prompt", "", "p"),
        "root ::= command",
    )
    assert not verify_egress_contract(valid, "missing root rule")


def test_trace_content_and_savings_report_are_compact():
    record = compile_paper_memory_record(
        doc_id="ARXIV_TRACE",
        title="Trace Test",
        abstract="We propose compact trace storage for paper memory.",
    )
    trace = record_to_trace_content(record)
    report = track_egress_savings(400, 20, 0.5)

    assert "TITLE: Trace Test" in trace
    assert "POINTS:" in trace
    assert report["input_tokens_est"] == 100
    assert report["output_tokens"] == 20
    assert report["efficiency_score"] > 0
