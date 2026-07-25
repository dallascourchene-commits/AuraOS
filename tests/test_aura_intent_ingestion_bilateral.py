"""Bilateral intent ingestion, compression, and routing proofs."""
from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import aura_intent_ingestion as ingestion  # noqa: E402
from aura_intent_ingestion import (  # noqa: E402
    compile_intent_packet,
    compress_intent_for_agent,
    intent_to_agent_handoff,
    parse_intent_document,
)


def test_structured_bilateral_sections_preserve_exact_negative_spans():
    text = """[AURA_INTENT]
OBJECTIVE: Preserve overlays. Do not merge automatically.

[AURA_REQUIRED_BEHAVIOR]
- Preserve overlays across representation changes.

[AURA_PROHIBITED_BEHAVIOR]
- Do not mutate canonical geometry.
- Do not infer professional approval.
"""
    parsed = parse_intent_document(text)
    assert "AURA_PROHIBITED_BEHAVIOR" in parsed["sections"]
    assert parsed["positive_requirements"] == [
        "Preserve overlays across representation changes."
    ]
    assert len(parsed["negative_requirements"]) == 3
    assert all(
        text[item["source_start"]:item["source_end"]] == item["source_span"]
        for item in parsed["negative_requirements"]
    )
    assert "not" in ingestion._extract_keywords("do not merge")


def test_negative_requirements_survive_compression_and_handoff_verbatim():
    packet = compile_intent_packet(
        "Build the renderer. Do not merge automatically.",
        repo_root=REPO_ROOT,
        skip_grounding=True,
    )
    digest = packet["negative_requirements_digest"]
    assert digest
    assert (
        packet["routing_frame"]["bilateral_intent_refs"]
        ["negative_requirements_digest"]
        == digest
    )

    compressed = compress_intent_for_agent(packet, repo_root=REPO_ROOT)
    assert compressed["negation_preserved"] is True
    assert "NEGATIVE REQUIREMENTS — FULL TEXT, NOT COMPRESSED" in compressed[
        "compressed_payload"
    ]
    assert "Do not merge automatically." in compressed["compressed_payload"]

    handoff = intent_to_agent_handoff(packet, repo_root=REPO_ROOT)
    assert handoff["negation_preserved"] is True
    assert handoff["negative_requirements"] == packet["negative_requirements"]
    assert handoff["negative_requirements_digest"] == digest
    assert "Do not merge automatically." in handoff["compressed_context"]


def test_contradiction_routes_with_clarification_evidence_not_authority():
    text = """[AURA_INTENT]
OBJECTIVE: Automatically merge the pull request.

[AURA_REQUIRED_BEHAVIOR]
Automatically merge the pull request.

[AURA_PROHIBITED_BEHAVIOR]
Do not merge the pull request automatically.
"""
    packet = compile_intent_packet(text, repo_root=REPO_ROOT, skip_grounding=True)
    assert packet["requires_clarification"] is True
    assert packet["requirement_contradictions"]
    assert packet["route_decision"]["bilateral_intent_status"] == (
        "CLARIFICATION_REQUIRED"
    )
    refs = packet["routing_frame"]["bilateral_intent_refs"]
    assert refs["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert refs["vsa_patch_authority"] is False


def test_positive_leave_command_is_not_false_negative():
    parsed = parse_intent_document("Leave a review comment for the author.")
    assert parsed["negative_requirements"] == []
