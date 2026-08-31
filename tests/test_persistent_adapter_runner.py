from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tools.benchmarks.long_horizon_preregistration import build_preregistration, command_digest
from tools.benchmarks.persistent_adapter_runner import run_persistent_adapter


PERSISTENT_ADAPTER = r'''
import hashlib
import json
import sys

GEN = "fake-persistent-v1"
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


def write_adapter(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "persistent_adapter.py"
    path.write_text(body, encoding="utf-8")
    return path


def make_prereg(command, *, rounds=4, generation="fake-persistent-v1", timeout=120.0, startup_timeout=10.0):
    return build_preregistration(
        campaign_id="persistent-runner-test",
        rounds=rounds,
        seed=17,
        startup_timeout_seconds=startup_timeout,
        timeout_seconds=timeout,
        arms=[
            {
                "blinded_label": "arm-01",
                "adapter_generation": generation,
                "adapter_command_digest": command_digest(command),
                "condition_commitment": "c" * 64,
            }
        ],
    )


def run(command, *, rounds=4, generation="fake-persistent-v1", timeout=120.0, startup_timeout=10.0, cwd=None):
    pre = make_prereg(
        command,
        rounds=rounds,
        generation=generation,
        timeout=timeout,
        startup_timeout=startup_timeout,
    )
    return run_persistent_adapter(command, preregistration=pre, blinded_label="arm-01", cwd=cwd)


def test_persistent_adapter_keeps_state_in_one_process(tmp_path):
    adapter = write_adapter(tmp_path, PERSISTENT_ADAPTER)
    command = [sys.executable, str(adapter)]
    report = run(command, rounds=8, cwd=tmp_path)
    assert report["campaign_disposition"] == "PASS"
    assert report["startup_disposition"] == "PASS"
    assert report["adapter_generation"] == "fake-persistent-v1"
    assert report["blinded_label"] == "arm-01"
    assert len(report["preregistration_digest"]) == 64
    assert report["disposition_counts"]["PASS"] == 8
    assert report["state_drift_detected"] is False
    assert report["inconclusive_turns"] == 0
    assert len(report["evidence_digest"]) == 64


def test_changed_command_is_rejected_before_process_launch(tmp_path):
    adapter = write_adapter(tmp_path, PERSISTENT_ADAPTER)
    command = [sys.executable, str(adapter)]
    pre = make_prereg(command)
    with pytest.raises(ValueError, match="ADAPTER_COMMAND_DIGEST_MISMATCH"):
        run_persistent_adapter(
            [sys.executable, "different_adapter.py"],
            preregistration=pre,
            blinded_label="arm-01",
            cwd=tmp_path,
        )


def test_handshake_generation_mismatch_stops_before_turn_effects(tmp_path):
    body = PERSISTENT_ADAPTER.replace('GEN = "fake-persistent-v1"', 'GEN = "stale-generation"')
    adapter = write_adapter(tmp_path, body)
    command = [sys.executable, str(adapter)]
    report = run(command, generation="fake-persistent-v1", cwd=tmp_path)
    assert report["campaign_disposition"] == "INCONCLUSIVE"
    assert report["startup_disposition"] == "PROTOCOL_ERROR"
    assert report["startup_error"] == "ADAPTER_GENERATION_MISMATCH"
    assert report["adapter_generation"] == "stale-generation"
    assert report["turns"] == []


def test_turn_generation_mismatch_fails_protocol_and_stops_later_effects(tmp_path):
    body = PERSISTENT_ADAPTER.replace(
        '"adapter_generation": GEN,\n        "state_digest": digest,',
        '"adapter_generation": "stale-generation",\n        "state_digest": digest,',
    )
    adapter = write_adapter(tmp_path, body)
    command = [sys.executable, str(adapter)]
    report = run(command, cwd=tmp_path)
    assert report["campaign_disposition"] == "INCONCLUSIVE"
    assert report["disposition_counts"]["PROTOCOL_ERROR"] == 1
    assert report["disposition_counts"]["NOT_RUN_AFTER_ADAPTER_FAILURE"] == 3
    assert report["state_drift_detected"] is False


def test_real_digest_mismatch_does_not_desynchronize_persistent_process(tmp_path):
    body = PERSISTENT_ADAPTER.replace(
        '"state_digest": digest,',
        '"state_digest": ("0" * 64 if request["turn"] == 2 else digest),',
    )
    adapter = write_adapter(tmp_path, body)
    command = [sys.executable, str(adapter)]
    report = run(command, rounds=6, cwd=tmp_path)
    assert report["campaign_disposition"] == "STATE_DRIFT"
    assert report["disposition_counts"]["STATE_DRIFT"] == 1
    assert report["disposition_counts"]["PASS"] == 5
    assert report["inconclusive_turns"] == 0


def test_timeout_is_retained_and_future_turns_are_not_replayed(tmp_path):
    body = PERSISTENT_ADAPTER.replace(
        'op = request["operation"]',
        'import time\n    if request["turn"] == 1: time.sleep(1.0)\n    op = request["operation"]',
    )
    adapter = write_adapter(tmp_path, body)
    command = [sys.executable, str(adapter)]
    report = run(command, timeout=0.02, cwd=tmp_path)
    assert report["campaign_disposition"] == "INCONCLUSIVE"
    assert report["disposition_counts"]["PASS"] == 1
    assert report["disposition_counts"]["TIMEOUT"] == 1
    assert report["disposition_counts"]["NOT_RUN_AFTER_ADAPTER_FAILURE"] == 2
    assert report["state_drift_detected"] is False


def test_invalid_handshake_is_inconclusive_without_turn_execution(tmp_path):
    adapter = write_adapter(
        tmp_path,
        'import json,sys\nprint(json.dumps({"type":"adapter_handshake","protocol_id":"wrong"}), flush=True)\nfor line in sys.stdin: pass\n',
    )
    command = [sys.executable, str(adapter)]
    report = run(command, cwd=tmp_path)
    assert report["campaign_disposition"] == "INCONCLUSIVE"
    assert report["startup_disposition"] == "PROTOCOL_ERROR"
    assert report["turns"] == []
