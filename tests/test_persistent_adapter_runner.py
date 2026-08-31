from __future__ import annotations

import sys
from pathlib import Path

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


def test_persistent_adapter_keeps_state_in_one_process(tmp_path):
    adapter = write_adapter(tmp_path, PERSISTENT_ADAPTER)
    report = run_persistent_adapter([sys.executable, str(adapter)], rounds=8, cwd=tmp_path)
    assert report["campaign_disposition"] == "PASS"
    assert report["startup_disposition"] == "PASS"
    assert report["adapter_generation"] == "fake-persistent-v1"
    assert report["disposition_counts"]["PASS"] == 8
    assert report["state_drift_detected"] is False
    assert report["inconclusive_turns"] == 0
    assert len(report["evidence_digest"]) == 64


def test_generation_mismatch_fails_protocol_and_stops_later_effects(tmp_path):
    body = PERSISTENT_ADAPTER.replace(
        '"adapter_generation": GEN,\n        "state_digest": digest,',
        '"adapter_generation": "stale-generation",\n        "state_digest": digest,',
    )
    adapter = write_adapter(tmp_path, body)
    report = run_persistent_adapter([sys.executable, str(adapter)], rounds=4, cwd=tmp_path)
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
    report = run_persistent_adapter([sys.executable, str(adapter)], rounds=6, cwd=tmp_path)
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
    report = run_persistent_adapter(
        [sys.executable, str(adapter)],
        rounds=4,
        turn_timeout_seconds=0.02,
        cwd=tmp_path,
    )
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
    report = run_persistent_adapter([sys.executable, str(adapter)], rounds=4, cwd=tmp_path)
    assert report["campaign_disposition"] == "INCONCLUSIVE"
    assert report["startup_disposition"] == "PROTOCOL_ERROR"
    assert report["turns"] == []
