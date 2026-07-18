from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path

from aura_external_llm_session import ExternalLLMTurn
from aura_gate import GateAuthorityEnvelope, GatePolicyManifest, gate_purpose_digest

ROOT = Path(__file__).resolve().parents[1]


def _json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_authority_schema_tracks_exact_runtime_envelope_fields() -> None:
    schema = _json("schemas/aura_gate_authority_envelope.schema.json")
    runtime_fields = set(GateAuthorityEnvelope.__dataclass_fields__)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == runtime_fields
    assert set(schema["properties"]) == runtime_fields
    assert schema["properties"]["human_review_required"] == {"const": True}
    assert schema["properties"]["production_mutation"] == {"const": False}
    assert schema["properties"]["automatic_promotion"] == {"const": False}


def test_example_policy_is_content_addressed_and_deny_by_default() -> None:
    raw = _json("examples/aura_gate_policy.json")
    policy = GatePolicyManifest.from_mapping(raw)
    objective = (
        "Review aura_forge.py and propose a bounded patch for AuraForgeRuntime without committing or promoting it."
    )

    assert policy.to_dict() == raw
    assert policy.allowed_purpose_digests == (gate_purpose_digest(objective),)
    assert policy.private_only is True
    assert policy.human_review_required is True
    assert policy.production_mutation is False
    assert policy.automatic_promotion is False
    assert set(policy.allowed_egress_fields) == {field.name for field in fields(ExternalLLMTurn)} | {"version"}
    assert "BOUNDED_SOURCE_CONTEXT" in policy.allowed_data_classes


def test_token_benchmark_is_arithmetically_consistent_and_truthful() -> None:
    record = _json("docs/evidence/AURA_GATE_PHASE2_AGENT_BRIDGE_COUNCIL_V3_BENCHMARK_2026-07-18.json")
    bridge = record["agent_bridge"]
    council = record["selective_council_v3"]
    combined = record["combined_non_overlapping_proxy"]
    provider = record["full_codex_session_provider_telemetry"]
    current = record["current_tree_reference_after_adversarial_closure"]

    assert provider["availability"] == "NOT_AVAILABLE"
    assert provider["input_tokens"] is None
    assert provider["output_tokens"] is None
    assert bridge["historical_planning_snapshot"]["reproducible_from_current_tree"] is False
    assert sum(item["char_count"] for item in current["files"]) == current["raw_char_count"]
    assert (current["raw_char_count"] + 3) // 4 == current["raw_context_token_estimate"]
    assert (
        bridge["raw_context_token_estimate"] - bridge["aura_context_token_estimate"]
        == bridge["estimated_input_tokens_saved"]
    )
    assert (
        council["actual_input_token_estimate"] + council["actual_output_token_estimate"]
        == council["actual_total_token_estimate"]
    )
    assert (
        combined["counterfactual_total_token_estimate"] - combined["recorded_total_token_estimate"]
        == combined["estimated_tokens_saved"]
    )
