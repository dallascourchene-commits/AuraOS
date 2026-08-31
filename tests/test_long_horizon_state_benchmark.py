from __future__ import annotations

import sys
from pathlib import Path

from tools.benchmarks.long_horizon_preregistration import build_preregistration, command_digest
from tools.benchmarks.long_horizon_state_benchmark import build_workload, run_adapter


PERSISTENT_ADAPTER = r'''
import hashlib
import json
import sys

GEN = "compat-persistent-v1"
state = {}
checkpoints = {}
print(json.dumps({
    "type": "adapter_handshake",
    "protocol_id": "AURA_BENCHMARK_PERSISTENT_ADAPTER_V1",
    "adapter_generation": GEN,
    "capabilities": {
        "persistent_process": True,
        "state_digest": True,
        "per_turn_timeout_control": False,
        "provider_usage_receipts": False,
        "telemetry_provenance": ["UNKNOWN"],
    },
}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    assert "expected_state_digest" not in request
    op = request["operation"]
    if op["type"] == "set":
        state[op["key"]] = op["value"]
    elif op["type"] == "checkpoint":
        checkpoints[op["name"]] = dict(state)
    elif op["type"] == "rollback":
        state = dict(checkpoints[op["name"]])
    elif op["type"] == "get":
        assert state.get(op["key"]) == op["expected"]
    digest = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps({
        "type": "turn_result",
        "turn": request["turn"],
        "adapter_generation": GEN,
        "state_digest": digest,
        "telemetry": {"provenance": "UNKNOWN"},
    }), flush=True)
'''


def test_workload_is_deterministic_contains_rollback_and_keeps_answers_runner_side():
    first = build_workload(10, seed=17)
    second = build_workload(10, seed=17)
    assert first == second
    assert any(item["operation"]["type"] == "rollback" for item in first)
    assert all("expected_state_digest" in item for item in first)
    assert all("expected_state_digest" not in item["operation"] for item in first)


def test_compatibility_entrypoint_uses_preregistered_persistent_protocol(tmp_path: Path):
    adapter = tmp_path / "adapter.py"
    adapter.write_text(PERSISTENT_ADAPTER, encoding="utf-8")
    command = [sys.executable, str(adapter)]
    preregistration = build_preregistration(
        campaign_id="compat-test",
        rounds=6,
        seed=17,
        timeout_seconds=120.0,
        arms=[
            {
                "blinded_label": "arm-01",
                "adapter_generation": "compat-persistent-v1",
                "adapter_command_digest": command_digest(command),
                "condition_commitment": "c" * 64,
            }
        ],
    )
    report = run_adapter(
        command,
        preregistration=preregistration,
        blinded_label="arm-01",
        cwd=tmp_path,
    )
    assert report["campaign_disposition"] == "PASS"
    assert report["startup_disposition"] == "PASS"
    assert report["disposition_counts"]["PASS"] == 6
    assert report["preregistration_digest"] == preregistration["preregistration_digest"]
