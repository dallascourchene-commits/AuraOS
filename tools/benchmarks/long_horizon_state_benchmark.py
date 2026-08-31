from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


TURN_DISPOSITIONS = {"PASS", "STATE_DRIFT", "TIMEOUT", "ADAPTER_ERROR", "PROTOCOL_ERROR"}
CAMPAIGN_DISPOSITIONS = {
    "PASS",
    "STATE_DRIFT",
    "INCONCLUSIVE",
    "STATE_DRIFT_WITH_INCONCLUSIVE",
}


def _digest(state: dict[str, int]) -> str:
    payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_workload(rounds: int, *, seed: int = 17) -> list[dict[str, Any]]:
    if rounds < 4:
        raise ValueError("ROUNDS_MUST_BE_AT_LEAST_4")
    state: dict[str, int] = {}
    checkpoints: dict[str, dict[str, int]] = {}
    workload: list[dict[str, Any]] = []
    rollback_turn = max(2, rounds // 2)
    for turn in range(rounds):
        if turn == 1:
            checkpoints["baseline"] = dict(state)
            op = {"type": "checkpoint", "name": "baseline"}
        elif turn == rollback_turn:
            state = dict(checkpoints["baseline"])
            op = {"type": "rollback", "name": "baseline"}
        elif turn % 3 == 2:
            key = f"k{(turn * seed) % 7}"
            op = {"type": "get", "key": key, "expected": state.get(key)}
        else:
            key = f"k{(turn * seed) % 7}"
            value = turn * seed + 3
            state[key] = value
            op = {"type": "set", "key": key, "value": value}
        workload.append(
            {
                "turn": turn,
                "operation": op,
                "expected_state_digest": _digest(state),
            }
        )
    return workload


@dataclass(frozen=True)
class TurnResult:
    turn: int
    disposition: str
    returncode: int
    wall_time_ms: float
    expected_state_digest: str
    observed_state_digest: str | None
    state_match: bool
    telemetry: dict[str, Any]
    stderr: str


def _validate_telemetry(payload: dict[str, Any]) -> dict[str, Any]:
    telemetry = payload.get("telemetry", {})
    if not isinstance(telemetry, dict):
        raise ValueError("INVALID_TELEMETRY")
    provenance = telemetry.get("provenance", "UNKNOWN")
    if provenance not in {"OBSERVED", "ESTIMATED", "UNKNOWN"}:
        raise ValueError("INVALID_TELEMETRY_PROVENANCE")
    metric_keys = ("input_tokens", "output_tokens", "cost_usd", "peak_rss_mb")
    if provenance == "UNKNOWN" and any(telemetry.get(key) is not None for key in metric_keys):
        raise ValueError("UNKNOWN_TELEMETRY_CANNOT_CARRY_VALUES")
    for key in ("input_tokens", "output_tokens"):
        value = telemetry.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise ValueError(f"INVALID_{key.upper()}")
    for key in ("cost_usd", "peak_rss_mb"):
        value = telemetry.get(key)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0):
            raise ValueError(f"INVALID_{key.upper()}")
    return telemetry


def _campaign_disposition(disposition_counts: dict[str, int], *, rounds: int) -> tuple[str, bool, int]:
    state_drift_detected = disposition_counts["STATE_DRIFT"] > 0
    inconclusive_turns = sum(
        disposition_counts[name]
        for name in ("TIMEOUT", "ADAPTER_ERROR", "PROTOCOL_ERROR")
    )
    if disposition_counts["PASS"] == rounds:
        campaign_disposition = "PASS"
    elif state_drift_detected and inconclusive_turns:
        campaign_disposition = "STATE_DRIFT_WITH_INCONCLUSIVE"
    elif state_drift_detected:
        campaign_disposition = "STATE_DRIFT"
    else:
        campaign_disposition = "INCONCLUSIVE"
    if campaign_disposition not in CAMPAIGN_DISPOSITIONS:
        raise AssertionError(f"UNKNOWN_CAMPAIGN_DISPOSITION:{campaign_disposition}")
    return campaign_disposition, state_drift_detected, inconclusive_turns


def run_adapter(
    command: Sequence[str],
    *,
    rounds: int,
    seed: int = 17,
    timeout_seconds: float = 120.0,
    cwd: Path | None = None,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise ValueError("TIMEOUT_SECONDS_MUST_BE_POSITIVE")

    workload = build_workload(rounds, seed=seed)
    results: list[TurnResult] = []
    for item in workload:
        start = time.perf_counter()
        observed: str | None = None
        telemetry: dict[str, Any] = {"provenance": "UNKNOWN"}
        stderr = ""
        returncode = 0
        disposition = "ADAPTER_ERROR"

        try:
            completed = subprocess.run(
                list(command),
                input=json.dumps(item) + "\n",
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                cwd=str(cwd) if cwd else None,
                check=False,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            returncode = completed.returncode
            stderr = completed.stderr

            if completed.returncode == 0:
                try:
                    payload = json.loads(completed.stdout)
                    if not isinstance(payload, dict):
                        raise ValueError("ADAPTER_OUTPUT_NOT_OBJECT")
                    observed = payload.get("state_digest")
                    if observed is not None and not isinstance(observed, str):
                        raise ValueError("INVALID_STATE_DIGEST")
                    telemetry = _validate_telemetry(payload)
                    disposition = "PASS" if observed == item["expected_state_digest"] else "STATE_DRIFT"
                except (json.JSONDecodeError, ValueError) as exc:
                    returncode = 65
                    disposition = "PROTOCOL_ERROR"
                    stderr = f"{stderr}\nADAPTER_PROTOCOL_ERROR:{exc}"
            else:
                disposition = "ADAPTER_ERROR"
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            returncode = 124
            disposition = "TIMEOUT"
            captured_stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            stderr = f"{captured_stderr}\nADAPTER_TIMEOUT:{timeout_seconds}"

        if disposition not in TURN_DISPOSITIONS:
            raise AssertionError(f"UNKNOWN_TURN_DISPOSITION:{disposition}")
        state_match = disposition == "PASS"
        results.append(
            TurnResult(
                turn=item["turn"],
                disposition=disposition,
                returncode=returncode,
                wall_time_ms=elapsed_ms,
                expected_state_digest=item["expected_state_digest"],
                observed_state_digest=observed,
                state_match=state_match,
                telemetry=telemetry,
                stderr=stderr,
            )
        )

    passed = sum(result.state_match for result in results)
    observed_turns = sum(result.telemetry.get("provenance") == "OBSERVED" for result in results)
    estimated_turns = sum(result.telemetry.get("provenance") == "ESTIMATED" for result in results)
    disposition_counts = {
        disposition: sum(result.disposition == disposition for result in results)
        for disposition in sorted(TURN_DISPOSITIONS)
    }
    campaign_disposition, state_drift_detected, inconclusive_turns = _campaign_disposition(
        disposition_counts, rounds=rounds
    )
    return {
        "schema_id": "AURA_LONG_HORIZON_STATE_BENCHMARK_V1",
        "rounds": rounds,
        "seed": seed,
        "timeout_seconds": timeout_seconds,
        "workload_digest": hashlib.sha256(json.dumps(workload, sort_keys=True).encode("utf-8")).hexdigest(),
        "campaign_disposition": campaign_disposition,
        "passed_turns": passed,
        "state_drift_detected": state_drift_detected,
        "inconclusive_observation_present": inconclusive_turns > 0,
        "inconclusive_turns": inconclusive_turns,
        "runner_wall_time_ms": sum(result.wall_time_ms for result in results),
        "telemetry_observed_turns": observed_turns,
        "telemetry_estimated_turns": estimated_turns,
        "disposition_counts": disposition_counts,
        "turns": [result.__dict__ for result in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a neutral long-horizon state workload through an adapter command.")
    parser.add_argument("--adapter-cmd", nargs="+", required=True)
    parser.add_argument("--rounds", type=int, default=25)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_adapter(
        args.adapter_cmd,
        rounds=args.rounds,
        seed=args.seed,
        timeout_seconds=args.timeout_seconds,
        cwd=args.cwd,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["campaign_disposition"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
