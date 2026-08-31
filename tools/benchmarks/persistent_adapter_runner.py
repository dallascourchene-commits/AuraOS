from __future__ import annotations

import argparse
import hashlib
import json
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Sequence

from tools.benchmarks.long_horizon_preregistration import (
    command_digest,
    get_preregistered_arm,
    validate_preregistration,
)
from tools.benchmarks.long_horizon_state_benchmark import build_workload
from tools.benchmarks.persistent_adapter_protocol import make_turn_request, validate_handshake, validate_turn_response


RUNNER_SCHEMA_ID = "AURA_PERSISTENT_ADAPTER_RUNNER_V1"
TURN_DISPOSITIONS = {
    "PASS",
    "STATE_DRIFT",
    "TIMEOUT",
    "ADAPTER_EXIT",
    "PROTOCOL_ERROR",
    "NOT_RUN_AFTER_ADAPTER_FAILURE",
}


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _reader(stream: Any, output: queue.Queue[str | None]) -> None:
    try:
        for line in iter(stream.readline, ""):
            output.put(line.rstrip("\r\n"))
    finally:
        output.put(None)


def _stderr_reader(stream: Any, sink: list[str]) -> None:
    for line in iter(stream.readline, ""):
        sink.append(line.rstrip("\r\n"))


def _receive_line(output: queue.Queue[str | None], *, timeout_seconds: float) -> str:
    try:
        line = output.get(timeout=timeout_seconds)
    except queue.Empty as exc:
        raise TimeoutError("ADAPTER_RESPONSE_TIMEOUT") from exc
    if line is None:
        raise EOFError("ADAPTER_STDOUT_CLOSED")
    return line


def _terminate(process: subprocess.Popen[str], *, grace_seconds: float = 1.0) -> dict[str, Any]:
    if process.stdin and not process.stdin.closed:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
    try:
        returncode = process.wait(timeout=grace_seconds)
        return {"disposition": "CLEAN_EXIT", "returncode": returncode}
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            returncode = process.wait(timeout=grace_seconds)
            return {"disposition": "TERMINATED", "returncode": returncode}
        except subprocess.TimeoutExpired:
            process.kill()
            returncode = process.wait(timeout=grace_seconds)
            return {"disposition": "KILLED", "returncode": returncode}


def _startup_failure_report(
    *,
    startup_disposition: str,
    startup_error: str,
    preregistration: dict[str, Any],
    blinded_label: str,
    arm: dict[str, str],
    adapter_command_digest: str,
    adapter_generation: str | None,
    teardown: dict[str, Any],
    stderr_lines: list[str],
) -> dict[str, Any]:
    report = {
        "schema_id": RUNNER_SCHEMA_ID,
        "campaign_disposition": "INCONCLUSIVE",
        "startup_disposition": startup_disposition,
        "startup_error": startup_error,
        "preregistration_digest": preregistration["preregistration_digest"],
        "blinded_label": blinded_label,
        "condition_commitment": arm["condition_commitment"],
        "handshake": None,
        "adapter_generation": adapter_generation,
        "adapter_command_digest": adapter_command_digest,
        "rounds": preregistration["rounds"],
        "seed": preregistration["seed"],
        "startup_timeout_seconds": preregistration["startup_timeout_seconds"],
        "turn_timeout_seconds": preregistration["timeout_seconds"],
        "workload_digest": preregistration["workload_digest"],
        "state_drift_detected": False,
        "inconclusive_turns": preregistration["rounds"],
        "disposition_counts": {name: 0 for name in sorted(TURN_DISPOSITIONS)},
        "turns": [],
        "teardown": teardown,
        "stderr": stderr_lines,
    }
    report["evidence_digest"] = _canonical_digest(report)
    return report


def run_persistent_adapter(
    command: Sequence[str],
    *,
    preregistration: dict[str, Any],
    blinded_label: str,
    cwd: Path | None = None,
) -> dict[str, Any]:
    preregistration = validate_preregistration(preregistration)
    arm = get_preregistered_arm(preregistration, blinded_label)
    adapter_command_digest = command_digest(command)
    if adapter_command_digest != arm["adapter_command_digest"]:
        raise ValueError("ADAPTER_COMMAND_DIGEST_MISMATCH")

    rounds = preregistration["rounds"]
    seed = preregistration["seed"]
    startup_timeout_seconds = preregistration["startup_timeout_seconds"]
    turn_timeout_seconds = preregistration["timeout_seconds"]
    workload = build_workload(rounds, seed=seed)
    workload_digest = _canonical_digest(workload)
    if workload_digest != preregistration["workload_digest"]:
        raise ValueError("WORKLOAD_DIGEST_MISMATCH")

    process = subprocess.Popen(
        list(command),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=str(cwd) if cwd else None,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        raise RuntimeError("ADAPTER_PIPES_REQUIRED")

    stdout_queue: queue.Queue[str | None] = queue.Queue()
    stderr_lines: list[str] = []
    stdout_thread = threading.Thread(target=_reader, args=(process.stdout, stdout_queue), daemon=True)
    stderr_thread = threading.Thread(target=_stderr_reader, args=(process.stderr, stderr_lines), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    handshake: dict[str, Any]
    started_at = time.perf_counter()
    try:
        raw_handshake = _receive_line(stdout_queue, timeout_seconds=startup_timeout_seconds)
        handshake_payload = json.loads(raw_handshake)
        handshake = validate_handshake(handshake_payload)
    except TimeoutError as exc:
        teardown = _terminate(process)
        return _startup_failure_report(
            startup_disposition="TIMEOUT",
            startup_error=str(exc),
            preregistration=preregistration,
            blinded_label=blinded_label,
            arm=arm,
            adapter_command_digest=adapter_command_digest,
            adapter_generation=None,
            teardown=teardown,
            stderr_lines=stderr_lines,
        )
    except (EOFError, json.JSONDecodeError, ValueError) as exc:
        teardown = _terminate(process)
        return _startup_failure_report(
            startup_disposition="PROTOCOL_ERROR",
            startup_error=str(exc),
            preregistration=preregistration,
            blinded_label=blinded_label,
            arm=arm,
            adapter_command_digest=adapter_command_digest,
            adapter_generation=None,
            teardown=teardown,
            stderr_lines=stderr_lines,
        )

    generation = handshake["adapter_generation"]
    if generation != arm["adapter_generation"]:
        teardown = _terminate(process)
        return _startup_failure_report(
            startup_disposition="PROTOCOL_ERROR",
            startup_error="ADAPTER_GENERATION_MISMATCH",
            preregistration=preregistration,
            blinded_label=blinded_label,
            arm=arm,
            adapter_command_digest=adapter_command_digest,
            adapter_generation=generation,
            teardown=teardown,
            stderr_lines=stderr_lines,
        )

    turns: list[dict[str, Any]] = []
    adapter_failed = False
    for item in workload:
        if adapter_failed:
            turns.append(
                {
                    "turn": item["turn"],
                    "disposition": "NOT_RUN_AFTER_ADAPTER_FAILURE",
                    "expected_state_digest": item["expected_state_digest"],
                    "observed_state_digest": None,
                    "telemetry": {"provenance": "UNKNOWN"},
                    "wall_time_ms": 0.0,
                }
            )
            continue

        request = make_turn_request(item)
        turn_started_at = time.perf_counter()
        try:
            process.stdin.write(json.dumps(request, sort_keys=True) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            turns.append(
                {
                    "turn": item["turn"],
                    "disposition": "ADAPTER_EXIT",
                    "expected_state_digest": item["expected_state_digest"],
                    "observed_state_digest": None,
                    "telemetry": {"provenance": "UNKNOWN"},
                    "wall_time_ms": (time.perf_counter() - turn_started_at) * 1000.0,
                    "error": str(exc),
                }
            )
            adapter_failed = True
            continue

        try:
            raw_response = _receive_line(stdout_queue, timeout_seconds=turn_timeout_seconds)
            payload = json.loads(raw_response)
            response = validate_turn_response(
                payload,
                expected_turn=item["turn"],
                adapter_generation=generation,
            )
            state_match = response["state_digest"] == item["expected_state_digest"]
            turns.append(
                {
                    "turn": item["turn"],
                    "disposition": "PASS" if state_match else "STATE_DRIFT",
                    "expected_state_digest": item["expected_state_digest"],
                    "observed_state_digest": response["state_digest"],
                    "telemetry": response["telemetry"],
                    "wall_time_ms": (time.perf_counter() - turn_started_at) * 1000.0,
                }
            )
        except TimeoutError as exc:
            turns.append(
                {
                    "turn": item["turn"],
                    "disposition": "TIMEOUT",
                    "expected_state_digest": item["expected_state_digest"],
                    "observed_state_digest": None,
                    "telemetry": {"provenance": "UNKNOWN"},
                    "wall_time_ms": (time.perf_counter() - turn_started_at) * 1000.0,
                    "error": str(exc),
                }
            )
            adapter_failed = True
        except EOFError as exc:
            turns.append(
                {
                    "turn": item["turn"],
                    "disposition": "ADAPTER_EXIT",
                    "expected_state_digest": item["expected_state_digest"],
                    "observed_state_digest": None,
                    "telemetry": {"provenance": "UNKNOWN"},
                    "wall_time_ms": (time.perf_counter() - turn_started_at) * 1000.0,
                    "error": str(exc),
                }
            )
            adapter_failed = True
        except (json.JSONDecodeError, ValueError) as exc:
            turns.append(
                {
                    "turn": item["turn"],
                    "disposition": "PROTOCOL_ERROR",
                    "expected_state_digest": item["expected_state_digest"],
                    "observed_state_digest": None,
                    "telemetry": {"provenance": "UNKNOWN"},
                    "wall_time_ms": (time.perf_counter() - turn_started_at) * 1000.0,
                    "error": str(exc),
                }
            )
            adapter_failed = True

    teardown = _terminate(process)
    stdout_thread.join(timeout=1.0)
    stderr_thread.join(timeout=1.0)

    disposition_counts = {
        name: sum(turn["disposition"] == name for turn in turns)
        for name in sorted(TURN_DISPOSITIONS)
    }
    state_drift_detected = disposition_counts["STATE_DRIFT"] > 0
    inconclusive_turns = sum(
        disposition_counts[name]
        for name in ("TIMEOUT", "ADAPTER_EXIT", "PROTOCOL_ERROR", "NOT_RUN_AFTER_ADAPTER_FAILURE")
    )
    if disposition_counts["PASS"] == rounds:
        campaign_disposition = "PASS"
    elif state_drift_detected and inconclusive_turns:
        campaign_disposition = "STATE_DRIFT_WITH_INCONCLUSIVE"
    elif state_drift_detected:
        campaign_disposition = "STATE_DRIFT"
    else:
        campaign_disposition = "INCONCLUSIVE"

    report = {
        "schema_id": RUNNER_SCHEMA_ID,
        "campaign_disposition": campaign_disposition,
        "startup_disposition": "PASS",
        "preregistration_digest": preregistration["preregistration_digest"],
        "blinded_label": blinded_label,
        "condition_commitment": arm["condition_commitment"],
        "handshake": handshake,
        "adapter_generation": generation,
        "rounds": rounds,
        "seed": seed,
        "startup_timeout_seconds": startup_timeout_seconds,
        "turn_timeout_seconds": turn_timeout_seconds,
        "workload_digest": workload_digest,
        "adapter_command_digest": adapter_command_digest,
        "state_drift_detected": state_drift_detected,
        "inconclusive_turns": inconclusive_turns,
        "disposition_counts": disposition_counts,
        "runner_wall_time_ms": (time.perf_counter() - started_at) * 1000.0,
        "turns": turns,
        "teardown": teardown,
        "stderr": stderr_lines,
    }
    report["evidence_digest"] = _canonical_digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one preregistered persistent benchmark adapter.")
    parser.add_argument("--adapter-cmd", nargs="+", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--blinded-label", required=True)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preregistration = json.loads(args.preregistration.read_text(encoding="utf-8"))
    report = run_persistent_adapter(
        args.adapter_cmd,
        preregistration=preregistration,
        blinded_label=args.blinded_label,
        cwd=args.cwd,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["campaign_disposition"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
