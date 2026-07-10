"""Tests for Aura Empirical Cost Observatory modules.

All tests run offline with deterministic fixtures. No network, no provider calls.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_usage_normalizer import (
    normalize_openai_usage, normalize_anthropic_usage, normalize_gemini_usage,
    normalize_local_usage, normalize_usage, MEASURED, UNAVAILABLE, ESTIMATED,
    PATCH_AUTHORITY,
)
from aura_pricing_registry import PricingRegistry, COST_MEASURED, COST_CALCULATED, COST_UNKNOWN
from aura_empirical_cost_ledger import EmpiricalCostLedger
from aura_cost_attribution import AttributionLedger, StageMeasurement
from aura_cost_experiment_runner import (
    create_comparison_id, validate_comparability, compute_savings_status,
    compute_quality_normalized_metrics, run_replay_experiment, run_shadow_baseline,
    comparison_report, SAVINGS_VERIFIED, SAVINGS_INVALIDATED_BY_QUALITY,
    NO_COMPARABLE_BASELINE, REPLAY, SHADOW,
)
from aura_cost_telemetry_events import (
    TelemetryEventStream, emit_cost_run_started, emit_cost_stage_completed,
    emit_quality_gate, emit_savings_status, get_telemetry_stream,
    visual_state_for_measurement_class, visual_state_for_savings,
)


# ---------------------------------------------------------------------------
# Usage Normalizer tests
# ---------------------------------------------------------------------------

class TestUsageNormalizer:
    def test_openai_usage(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        result = normalize_openai_usage(usage)
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["measurement_class"] == MEASURED

    def test_anthropic_usage(self):
        usage = {"input_tokens": 200, "output_tokens": 80, "cache_read_input_tokens": 50}
        result = normalize_anthropic_usage(usage)
        assert result["input_tokens"] == 200
        assert result["cached_input_tokens"] == 50
        assert result["measurement_class"] == MEASURED

    def test_gemini_usage(self):
        usage = {"usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 100}}
        result = normalize_gemini_usage(usage)
        assert result["input_tokens"] == 300
        assert result["output_tokens"] == 100

    def test_missing_usage_fields(self):
        result = normalize_openai_usage({})
        assert result["input_tokens"] is None
        assert result["output_tokens"] is None
        assert result["measurement_class"] == UNAVAILABLE

    def test_cached_token_handling(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50,
                 "prompt_tokens_details": {"cached_tokens": 30}}
        result = normalize_openai_usage(usage)
        assert result["cached_input_tokens"] == 30

    def test_reasoning_token_handling(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50,
                 "completion_tokens_details": {"reasoning_tokens": 20}}
        result = normalize_openai_usage(usage)
        assert result["reasoning_tokens"] == 20

    def test_unknown_values_remain_none(self):
        result = normalize_openai_usage({"prompt_tokens": 100})
        assert result["output_tokens"] is None  # Not zero!
        assert result["cached_input_tokens"] is None

    def test_auto_detect_anthropic(self):
        usage = {"input_tokens": 100, "output_tokens": 50, "cache_creation_input_tokens": 10}
        result = normalize_usage(usage, provider="anthropic", model="claude-sonnet-4-6")
        assert result["provider"] == "anthropic"
        assert result["cache_creation_tokens"] == 10

    def test_auto_detect_gemini(self):
        usage = {"usageMetadata": {"promptTokenCount": 100}}
        result = normalize_usage(usage, provider="gemini", model="gemini-1.5-flash")
        assert result["input_tokens"] == 100

    def test_local_usage(self):
        usage = {"prompt_tokens": 50, "completion_tokens": 25, "energy_joules": 1.2}
        result = normalize_local_usage(usage)
        assert result["provider"] == "local"
        assert result["provider_reported_cost_usd"] == 0.0
        assert result.get("energy_joules") == 1.2

    def test_no_usage_data(self):
        result = normalize_usage(None, provider="openai", model="gpt-4o-mini")
        assert result["measurement_class"] == UNAVAILABLE

    def test_invariants(self):
        result = normalize_openai_usage({"prompt_tokens": 10})
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False

# ---------------------------------------------------------------------------
# Pricing Registry tests
# ---------------------------------------------------------------------------

class TestPricingRegistry:
    def test_known_model(self):
        registry = PricingRegistry(repo_root=REPO_ROOT)
        price = registry.get_price("claude-sonnet-4-6")
        assert price is not None
        assert price.input_per_million_usd == 3.00

    def test_unknown_model(self):
        registry = PricingRegistry(repo_root=REPO_ROOT)
        price = registry.get_price("unknown-model-xyz")
        assert price is None

    def test_calculate_cost_known(self):
        registry = PricingRegistry(repo_root=REPO_ROOT)
        result = registry.calculate_cost("claude-sonnet-4-6", 1000, 500)
        assert result["cost_status"] == COST_CALCULATED
        assert result["cost_usd"] is not None
        assert result["cost_usd"] > 0

    def test_calculate_cost_unknown(self):
        registry = PricingRegistry(repo_root=REPO_ROOT)
        result = registry.calculate_cost("unknown-model", 1000, 500)
        assert result["cost_status"] == COST_UNKNOWN
        assert result["cost_usd"] is None

    def test_provider_billed_overrides(self):
        registry = PricingRegistry(repo_root=REPO_ROOT)
        result = registry.calculate_cost("claude-sonnet-4-6", 1000, 500,
                                          provider_billed_cost=0.123)
        assert result["cost_status"] == COST_MEASURED
        assert result["cost_usd"] == 0.123

    def test_price_snapshot(self):
        registry = PricingRegistry(repo_root=REPO_ROOT)
        snap = registry.snapshot()
        assert "registry_version" in snap
        assert len(snap["prices"]) > 0

    def test_cached_token_pricing(self):
        registry = PricingRegistry(repo_root=REPO_ROOT)
        result = registry.calculate_cost("claude-sonnet-4-6", 1000, 500,
                                          cached_input_tokens=200)
        assert result["cost_status"] == COST_CALCULATED

# ---------------------------------------------------------------------------
# Empirical Cost Ledger tests
# ---------------------------------------------------------------------------

class TestEmpiricalCostLedger:
    def test_record_and_retrieve(self, tmp_path):
        ledger = EmpiricalCostLedger(repo_root=tmp_path)
        run = {
            "comparison_id": "test_cmp_1",
            "mode": "AURA_FULL_PIPELINE",
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "measurement_class": "MEASURED",
            "input_tokens": 1000,
            "output_tokens": 500,
            "calculated_cost_usd": 0.0105,
            "verification_status": "VERIFIED",
        }
        result = ledger.record_run(run)
        assert result["ok"] is True
        run_id = result["run_id"]
        retrieved = ledger.get_run(run_id)
        assert retrieved is not None
        assert retrieved["input_tokens"] == 1000
        assert retrieved["verification_status"] == "VERIFIED"
        ledger.close()

    def test_comparison_retrieval(self, tmp_path):
        import time
        ledger = EmpiricalCostLedger(repo_root=tmp_path)
        for mode in ["RAW_AGENT", "AURA_FULL_PIPELINE"]:
            ledger.record_run({
                "comparison_id": "test_cmp_2",
                "mode": mode,
                "provider": "test",
                "model": "test-model",
                "measurement_class": "MEASURED",
            })
            time.sleep(0.01)
        runs = ledger.get_comparison("test_cmp_2")
        assert len(runs) == 2
        ledger.close()

    def test_history(self, tmp_path):
        ledger = EmpiricalCostLedger(repo_root=tmp_path)
        ledger.record_run({"comparison_id": "h1", "mode": "test", "provider": "p", "model": "m"})
        history = ledger.get_history(limit=10)
        assert len(history) >= 1
        ledger.close()

    def test_persists_across_connections(self, tmp_path):
        ledger1 = EmpiricalCostLedger(repo_root=tmp_path)
        ledger1.record_run({"comparison_id": "persist_test", "mode": "test", "provider": "p", "model": "m"})
        ledger1.close()
        ledger2 = EmpiricalCostLedger(repo_root=tmp_path)
        history = ledger2.get_history(limit=10)
        assert any(h["comparison_id"] == "persist_test" for h in history)
        ledger2.close()

# ---------------------------------------------------------------------------
# Cost Attribution tests
# ---------------------------------------------------------------------------

class TestCostAttribution:
    def test_stage_measurement(self):
        sm = StageMeasurement("CODEMAP_LOCALIZED", input_chars=8000, output_chars=2000)
        assert sm.exclusive_tokens_saved > 0
        assert sm.measurement_class == "ESTIMATED"

    def test_attribution_report(self):
        ledger = AttributionLedger()
        ledger.record_stage("RAW_OBJECTIVE", input_chars=0, output_chars=20000)
        ledger.record_stage("CODEMAP_LOCALIZED", input_chars=20000, output_chars=4000)
        ledger.record_stage("READ_SLICE", input_chars=4000, output_chars=1200)
        report = ledger.attribution_report()
        assert report["ok"] is True
        assert report["total_exclusive_saved"] > 0
        assert len(report["stages"]) == 3

    def test_no_double_counting(self):
        ledger = AttributionLedger()
        ledger.record_stage("CODEMAP_LOCALIZED", input_chars=10000, output_chars=3000)
        ledger.record_stage("CONTEXT_CRUSHED", input_chars=3000, output_chars=1500)
        report = ledger.attribution_report()
        # Each stage's saving is exclusive (input - output)
        stage0_saved = report["stages"][0]["exclusive_tokens_saved"]
        stage1_saved = report["stages"][1]["exclusive_tokens_saved"]
        total = report["total_exclusive_saved"]

        # CODEMAP_LOCALIZED: 10000 input - 3000 output = 7000 saved
        # (10000 chars / 4 = 2500 tokens input, 3000 chars / 4 = 750 tokens output, 2500-750=1750 tokens saved)
        expected_stage0 = 10000 // 4 - 3000 // 4  # 2500 - 750 = 1750
        # CONTEXT_CRUSHED: 3000 input - 1500 output = 1500 saved
        # (3000 chars / 4 = 750 tokens input, 1500 chars / 4 = 375 tokens output, 750-375=375 tokens saved)
        expected_stage1 = 3000 // 4 - 1500 // 4  # 750 - 375 = 375
        expected_total = expected_stage0 + expected_stage1  # 1750 + 375 = 2125

        assert stage0_saved == expected_stage0
        assert stage1_saved == expected_stage1
        assert total == expected_total
        assert total == stage0_saved + stage1_saved  # No double counting

    def test_waterfall_markdown(self):
        ledger = AttributionLedger()
        ledger.record_stage("RAW_OBJECTIVE", input_chars=0, output_chars=20000)
        ledger.record_stage("CODEMAP_LOCALIZED", input_chars=20000, output_chars=4000)
        md = ledger.waterfall_markdown()
        assert "Waterfall" in md

# ---------------------------------------------------------------------------
# Experiment Runner tests
# ---------------------------------------------------------------------------

class TestExperimentRunner:
    def test_replay_experiment(self):
        fixtures = {"AURA_FULL_PIPELINE": {"input_tokens": 500, "output_tokens": 200, "cost_usd": 0.005}}
        result = run_replay_experiment("test objective", "claude-sonnet-4-6", fixtures)
        assert result["ok"] is True
        assert result["measurement_mode"] == REPLAY
        assert result["run"]["input_tokens"] == 500

    def test_shadow_baseline(self):
        pricing = {"cost_usd": 0.01, "cost_status": COST_CALCULATED,
                   "price_snapshot": {"input_per_million_usd": 3.0}}
        result = run_shadow_baseline("test", "claude-sonnet-4-6", 80000, pricing)
        assert result["ok"] is True
        assert result["measurement_mode"] == SHADOW
        assert "counterfactual" in result["note"].lower()

    def test_savings_verified(self):
        status = compute_savings_status(aura_cost=0.005, raw_cost=0.02,
                                         aura_verified=True, quality_not_worse=True)
        assert status == SAVINGS_VERIFIED

    def test_savings_invalidated_by_quality(self):
        status = compute_savings_status(aura_cost=0.005, raw_cost=0.02,
                                         aura_verified=False)
        assert status == SAVINGS_INVALIDATED_BY_QUALITY

    def test_savings_invalidated_by_quality_worse(self):
        """Test SAVINGS_INVALIDATED when quality is worse despite verification."""
        status = compute_savings_status(aura_cost=0.005, raw_cost=0.02,
                                         aura_verified=True, quality_not_worse=False)
        assert status == SAVINGS_INVALIDATED_BY_QUALITY

    def test_no_baseline(self):
        status = compute_savings_status(aura_cost=0.005, raw_cost=None,
                                         aura_verified=True, has_baseline=False)
        assert status == NO_COMPARABLE_BASELINE

    def test_quality_normalized_metrics(self):
        aura_run = {"calculated_cost_usd": 0.005, "input_tokens": 500, "output_tokens": 200,
                    "verification_status": "VERIFIED", "latency_ms": 100,
                    "source_lines_exposed": 120, "repair_attempt_count": 0}
        metrics = compute_quality_normalized_metrics(aura_run)
        assert metrics["cost_per_verified_success"] == 0.005
        assert metrics["tokens_per_verified_success"] == 700

    def test_comparison_report(self):
        aura_run = {"comparison_id": "cmp1", "model": "test", "repository_commit_sha": "abc",
                    "objective_hash": "h1", "calculated_cost_usd": 0.005,
                    "input_tokens": 500, "output_tokens": 200,
                    "verification_status": "VERIFIED", "latency_ms": 100,
                    "quality_score": 0.9, "repair_attempt_count": 0,
                    "source_lines_exposed": 120}
        raw_run = {"comparison_id": "cmp1", "model": "test", "repository_commit_sha": "abc",
                   "objective_hash": "h1", "calculated_cost_usd": 0.02,
                   "input_tokens": 5000, "output_tokens": 2000,
                   "verification_status": "NOT_RUN", "latency_ms": 200,
                   "quality_score": 0.0, "source_lines_exposed": 2000}
        report = comparison_report(aura_run, raw_run)
        assert report["ok"] is True
        assert "metrics" in report

    def test_comparability_mismatch(self):
        a = {"model": "m1", "repository_commit_sha": "abc", "objective_hash": "h1"}
        b = {"model": "m2", "repository_commit_sha": "abc", "objective_hash": "h1"}
        result = validate_comparability(a, b)
        assert result["comparable"] is False
        assert "model_mismatch" in result["mismatches"]

# ---------------------------------------------------------------------------
# Telemetry Events tests
# ---------------------------------------------------------------------------

class TestTelemetryEvents:
    def test_emit_and_retrieve(self):
        stream = TelemetryEventStream()
        stream.emit("cost_run_started", {"run_id": "r1", "comparison_id": "c1"})
        events = stream.get_events()
        assert len(events) == 1
        assert events[0]["event"] == "cost_run_started"

    def test_quality_gate_events(self):
        stream = TelemetryEventStream()
        stream.emit("quality_gate_passed", {"run_id": "r1", "passed": True})
        stream.emit("quality_gate_failed", {"run_id": "r2", "passed": False})
        events = stream.get_events()
        assert len(events) == 2

    def test_savings_events(self):
        stream = TelemetryEventStream()
        stream.emit("savings_verified", {"run_id": "r1", "savings_usd": 0.01})
        events = stream.get_events()
        assert events[0]["event"] == "savings_verified"

    def test_visual_states(self):
        assert visual_state_for_measurement_class("MEASURED") == "green"
        assert visual_state_for_measurement_class("ESTIMATED") == "yellow"
        assert visual_state_for_measurement_class("UNAVAILABLE") == "grey"
        assert visual_state_for_savings("SAVINGS_VERIFIED") == "green"
        assert visual_state_for_savings("SAVINGS_INVALIDATED_BY_QUALITY") == "red"

    def test_unknown_event_type_rejected(self):
        stream = TelemetryEventStream()
        result = stream.emit("unknown_event", {})
        assert result["ok"] is False

    def test_global_stream(self):
        get_telemetry_stream().clear()
        emit_cost_run_started("r1", "c1", "AURA_FULL_PIPELINE", "anthropic", "claude-sonnet-4-6")
        stream = get_telemetry_stream()
        assert stream.event_count() >= 1

    def test_no_secrets_in_events(self):
        import json
        stream = TelemetryEventStream()
        secret_api_key = "sk-test-secret-key-12345"
        secret_value = "should_not_appear"
        stream.emit("cost_run_started", {"run_id": "r1", "comparison_id": "c1",
                                          "api_key": secret_api_key,
                                          "secret_field": secret_value})
        events = stream.get_events()
        # Serialize and verify secrets are not present
        serialized = json.dumps(events)
        assert secret_api_key not in serialized
        assert secret_value not in serialized
        # Verify event structure is correct
        assert "patch_authority" in events[0]

    def test_invariants(self):
        stream = TelemetryEventStream()
        stream.emit("cost_run_started", {"run_id": "r1"})
        events = stream.get_events()
        assert events[0]["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert events[0]["vsa_patch_authority"] is False


# ---------------------------------------------------------------------------
# End-to-end fixture test
# ---------------------------------------------------------------------------

class TestEndToEndFixture:
    """End-to-end fixture: raw baseline → Aura pipeline → provider usage →
    candidate verification → quality-normalized comparison → telemetry → report."""

    def test_full_pipeline_e2e(self):
        # 1. Create comparison ID
        comparison_id = create_comparison_id("refactor egress", "claude-sonnet-4-6", "abc123")

        # 2. Run raw baseline (replay fixture)
        raw_fixtures = {"RAW_AGENT": {"input_tokens": 5000, "output_tokens": 2000, "cost_usd": 0.02,
                                       "latency_ms": 300, "verification_status": "NOT_RUN",
                                       "source_lines_exposed": 2000}}
        raw_result = run_replay_experiment("refactor egress", "claude-sonnet-4-6", raw_fixtures, mode="RAW_AGENT")
        raw_run = raw_result["run"]
        raw_run["repository_commit_sha"] = "abc123"
        raw_run["objective_hash"] = "h1"
        raw_run["quality_score"] = 0.0

        # 3. Run Aura pipeline (replay fixture)
        aura_fixtures = {"AURA_FULL_PIPELINE": {"input_tokens": 500, "output_tokens": 200, "cost_usd": 0.005,
                                                  "latency_ms": 100, "verification_status": "VERIFIED",
                                                  "source_lines_exposed": 120, "quality_score": 0.9,
                                                  "repair_attempt_count": 0}}
        aura_result = run_replay_experiment("refactor egress", "claude-sonnet-4-6", aura_fixtures, mode="AURA_FULL_PIPELINE")
        aura_run = aura_result["run"]
        aura_run["repository_commit_sha"] = "abc123"
        aura_run["objective_hash"] = "h1"

        # 4. Emit telemetry events
        stream = TelemetryEventStream()
        stream.clear()
        stream.emit("cost_run_started", {"run_id": raw_run["run_id"], "comparison_id": comparison_id})
        stream.emit("cost_run_started", {"run_id": aura_run["run_id"], "comparison_id": comparison_id})
        stream.emit("provider_usage_received", {"run_id": aura_run["run_id"], "usage": {"input_tokens": 500}})
        stream.emit("cost_stage_completed", {"run_id": aura_run["run_id"], "stage": "CODEMAP_LOCALIZED",
                                              "measurement_class": "ESTIMATED", "exclusive_tokens_saved": 4500})
        stream.emit("quality_gate_passed", {"run_id": aura_run["run_id"], "passed": True})
        stream.emit("savings_verified", {"run_id": aura_run["run_id"], "savings_usd": 0.015})
        stream.emit("cost_run_completed", {"run_id": aura_run["run_id"], "comparison_id": comparison_id,
                                            "total_cost_usd": 0.005, "verification_status": "VERIFIED",
                                            "savings_status": "SAVINGS_VERIFIED"})

        # 5. Generate comparison report
        report = comparison_report(aura_run, raw_run)
        assert report["ok"] is True
        metrics = report["metrics"]
        assert metrics["savings_status"] == SAVINGS_VERIFIED
        assert metrics["gross_saving"] > 0
        assert metrics["net_saving"] > 0

        # 6. Verify telemetry events
        events = stream.get_events()
        assert len(events) == 7
        assert events[0]["event"] == "cost_run_started"
        assert events[-1]["event"] == "cost_run_completed"

        # 7. Visual states
        assert visual_state_for_savings(metrics["savings_status"]) == "green"

    def test_e2e_failed_cheap_run(self):
        """A cheaper run that failed cannot claim verified savings."""
        aura_run = {"comparison_id": "c1", "model": "m", "repository_commit_sha": "a",
                    "objective_hash": "h", "calculated_cost_usd": 0.005,
                    "input_tokens": 500, "output_tokens": 200,
                    "verification_status": "FAILED", "quality_score": 0.3}
        raw_run = {"comparison_id": "c1", "model": "m", "repository_commit_sha": "a",
                   "objective_hash": "h", "calculated_cost_usd": 0.02,
                   "input_tokens": 5000, "output_tokens": 2000,
                   "verification_status": "NOT_RUN", "quality_score": 0.0}
        report = comparison_report(aura_run, raw_run)
        assert report["ok"] is True
        assert report["metrics"]["savings_status"] == SAVINGS_INVALIDATED_BY_QUALITY

    def test_e2e_no_secrets_in_ledger(self, tmp_path):
        """Ledger must not store secrets."""
        import json
        ledger = EmpiricalCostLedger(repo_root=tmp_path)
        secret_key = "sk-test-secret-12345"
        secret_value = "should_not_be_stored"
        ledger.record_run({
            "comparison_id": "secret_test",
            "mode": "test",
            "provider": "p",
            "model": "m",
            "telemetry_warnings": [f"api_key={secret_key} {secret_value}"],
        })
        run = ledger.get_run(ledger.get_history(limit=1)[0]["run_id"])
        # Serialize and verify secrets are not present
        serialized = json.dumps(run)
        assert secret_key not in serialized
        assert secret_value not in serialized
        # Verify ledger structure is correct
        assert run["patch_authority"] == "exact_source_spans_and_hashes_only"
        ledger.close()


# ---------------------------------------------------------------------------
# Arena telemetry integration tests
# ---------------------------------------------------------------------------

class TestArenaTelemetryIntegration:
    def test_cost_telemetry_endpoint(self):
        """Test the cost telemetry API endpoint returns valid data."""
        from aura_human_agent_arena_server import dispatch_api_request, HumanAgentArenaServerState
        state = HumanAgentArenaServerState(repo_root=REPO_ROOT)
        status, result = dispatch_api_request(state, "GET", "/api/human-agent/cost-telemetry")
        assert status == 200
        assert result["ok"] is True
        assert "event_count" in result
        assert "patch_authority" in result

    def test_cost_events_endpoint(self):
        """Test the cost events API endpoint."""
        from aura_human_agent_arena_server import dispatch_api_request, HumanAgentArenaServerState
        state = HumanAgentArenaServerState(repo_root=REPO_ROOT)
        status, result = dispatch_api_request(state, "GET", "/api/human-agent/cost-events")
        assert status == 200
        assert result["ok"] is True
        assert "events" in result

    def test_cost_events_since_filter(self):
        """Test the cost events endpoint with since parameter for timestamp filtering."""
        import time
        from aura_human_agent_arena_server import dispatch_api_request, HumanAgentArenaServerState
        from aura_cost_telemetry_events import get_telemetry_stream

        # Get stream reference and clear it first to ensure test isolation
        stream = get_telemetry_stream()
        stream.clear()

        # Create state after clearing to avoid any initialization events
        state = HumanAgentArenaServerState(repo_root=REPO_ROOT)

        # Seed events with specific timestamps
        timestamp_before = time.time() - 100
        timestamp_cutoff = time.time() - 50
        timestamp_after = time.time()

        # Manually create events with controlled timestamps
        stream.emit("cost_run_started", {"run_id": "before", "comparison_id": "c1",
                                          "mode": "test", "provider": "test", "model": "test"})
        stream._events[-1]["timestamp"] = timestamp_before

        stream.emit("cost_run_started", {"run_id": "after1", "comparison_id": "c2",
                                          "mode": "test", "provider": "test", "model": "test"})
        stream._events[-1]["timestamp"] = timestamp_after

        stream.emit("cost_run_completed", {"run_id": "after2", "comparison_id": "c3"})
        stream._events[-1]["timestamp"] = timestamp_after + 1

        # Request events since cutoff
        status, result = dispatch_api_request(state, "GET", f"/api/human-agent/cost-events?since={timestamp_cutoff}")
        assert status == 200
        assert result["ok"] is True
        assert "events" in result

        # Should only contain events after cutoff
        events = result["events"]
        assert len(events) == 2  # exactly after1 and after2, not "before"
        for event in events:
            assert event["timestamp"] >= timestamp_cutoff
            assert event["run_id"] in ["after1", "after2"]

        stream.clear()


# ---------------------------------------------------------------------------
# MCP tools tests
# ---------------------------------------------------------------------------

class TestCostMCPTools:
    def test_tool_list(self):
        from aura_cost_observatory_mcp import cost_mcp_tool_list
        tools = cost_mcp_tool_list()
        assert len(tools) == 4
        names = [t["name"] for t in tools]
        assert "aura_cost_run_status" in names
        assert "aura_get_cost_comparison" in names

    def test_execute_status_tool(self):
        from aura_cost_observatory_mcp import execute_cost_mcp_tool
        result = execute_cost_mcp_tool("aura_cost_run_status", {}, repo_root=str(REPO_ROOT))
        assert result["ok"] is True
        assert "event_count" in result

    def test_execute_unknown_tool(self):
        from aura_cost_observatory_mcp import execute_cost_mcp_tool
        result = execute_cost_mcp_tool("unknown_tool", {})
        assert result["ok"] is False

    def test_invariants(self):
        from aura_cost_observatory_mcp import execute_cost_mcp_tool
        result = execute_cost_mcp_tool("aura_cost_run_status", {}, repo_root=str(REPO_ROOT))
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False
