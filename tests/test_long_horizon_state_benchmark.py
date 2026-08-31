from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.benchmarks.long_horizon_state_benchmark import build_workload, run_adapter


ADAPTER = r'''
import hashlib
import json
import pathlib
import sys

item = json.loads(sys.stdin.read())
state_path = pathlib.Path("adapter-state.json")
checkpoint_path = pathlib.Path("adapter-baseline.json")
state = json.loads(state_path.read_text()) if state_path.exists() else {}
op = item["operation"]
if op["type"] == "set":
    state[op["key"]] = op["value"]
elif op["type"] == "checkpoint":
    checkpoint_path.write_text(json.dumps(state, sort_keys=True))
elif op["type"] == "rollback":
    state = json.loads(checkpoint_path.read_text())
elif op["type"] == "get":
    assert state.get(op["key"]) == op["expected"]
state_path.write_text(json.dumps(state, sort_keys=True))
payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
digest = hashlib.sha256(payload).hexdigest()
print(json.dumps({"state_digest": digest, "telemetry": {"provenance": "UNKNOWN"}}))
'''


def write_adapter(tmp_path: Path, body: str = ADAPTER) -> Path:
    path = tmp_path / "adapter.py"
    path.write_text(body, encoding="utf-8")
    return path


def test_workload_is_deterministic_and_contains_rollback():
    first = build_workload(10, seed=17)
    second = build_workload(10, seed=17)
    assert first == second
    assert any(item["operation"]["type"] == "rollback" for item in first)


def test_neutral_adapter_can_pass_same_state_workload(tmp_path):
    adapter = write_adapter(tmp_path)
    report = run_adapter([sys.executable, str(adapter)], rounds=8, seed=17, cwd=tmp_path)
    assert report["passed_turns"] == 8
    assert report["state_drift_detected"] is False
    assert report["telemetry_observed_turns"] == 0
    assert all(turn["telemetry"]["provenance"] == "UNKNOWN" for turn in report["turns"])


def test_wrong_digest_is_state_drift_not_success(tmp_path):
    adapter = write_adapter(
        tmp_path,
        'import json,sys\njson.loads(sys.stdin.read())\nprint(json.dumps({"state_digest":"wrong","telemetry":{"provenance":"UNKNOWN"}}))\n',
    )
    report = run_adapter([sys.executable, str(adapter)], rounds=4, cwd=tmp_path)
    assert report["passed_turns"] == 0
    assert report["state_drift_detected"] is True


def test_unknown_telemetry_cannot_carry_fake_zero(tmp_path):
    adapter = write_adapter(
        tmp_path,
        'import json,sys\nitem=json.loads(sys.stdin.read())\nprint(json.dumps({"state_digest":item["expected_state_digest"],"telemetry":{"provenance":"UNKNOWN","input_tokens":0}}))\n',
    )
    report = run_adapter([sys.executable, str(adapter)], rounds=4, cwd=tmp_path)
    assert report["passed_turns"] == 0
    assert all(turn["returncode"] == 65 for turn in report["turns"])
