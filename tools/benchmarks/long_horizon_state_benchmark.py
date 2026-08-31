from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence


BENCHMARK_SCHEMA_ID = "AURA_LONG_HORIZON_STATE_BENCHMARK_V1"


def _digest(state: dict[str, int]) -> str:
    payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_workload(rounds: int, *, seed: int = 17) -> list[dict[str, Any]]:
    if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds < 4:
        raise ValueError("ROUNDS_MUST_BE_AT_LEAST_4")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED_MUST_BE_INTEGER")
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


def run_adapter(
    command: Sequence[str],
    *,
    preregistration: dict[str, Any],
    blinded_label: str,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Compatibility entrypoint for the canonical preregistered persistent runner.

    Comparator execution is intentionally not implemented here. Keeping a second
    subprocess path would let callers bypass the persistent handshake, frozen
    preregistration, and answer-leak protections. The import is local to avoid a
    module cycle because the persistent runner reuses build_workload().
    """
    from tools.benchmarks.persistent_adapter_runner import run_persistent_adapter

    return run_persistent_adapter(
        command,
        preregistration=preregistration,
        blinded_label=blinded_label,
        cwd=cwd,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a preregistered persistent long-horizon state benchmark adapter."
    )
    parser.add_argument("--adapter-cmd", nargs="+", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--blinded-label", required=True)
    parser.add_argument("--cwd", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preregistration = json.loads(args.preregistration.read_text(encoding="utf-8"))
    report = run_adapter(
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
