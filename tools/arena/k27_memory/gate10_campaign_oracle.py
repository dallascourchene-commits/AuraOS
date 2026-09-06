from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence
from hashlib import sha256
import json
import re

SCHEMA = "AURA-K27-GATE10-CAMPAIGN-ORACLE-v1"
WIN = "WIN"
HOLD_STORE_ROOT_CONFLICT = "HOLD_STORE_ROOT_CONFLICT"
HOLD_STALE_DEPENDENCY = "HOLD_STALE_DEPENDENCY"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_EXCEPTION = {
    HOLD_STORE_ROOT_CONFLICT: "MemoryConflict",
    HOLD_STALE_DEPENDENCY: "StaleMemory",
}


class CampaignOracleError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def campaign_root_from_trace(trace: Sequence[dict[str, Any]]) -> str:
    rows = list(trace)
    for expected_round, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CampaignOracleError("trace rows must be dictionaries")
        if set(row) != {"round", "src_epoch", "dep_epoch", "root", "root_scope"}:
            raise CampaignOracleError("trace row has noncanonical fields")
        if row.get("round") != expected_round:
            raise CampaignOracleError("trace round identity must be contiguous from zero")
        if type(row.get("src_epoch")) is not int or row["src_epoch"] <= 0:
            raise CampaignOracleError("trace src_epoch must be a positive exact int")
        if type(row.get("dep_epoch")) is not int or row["dep_epoch"] <= 0:
            raise CampaignOracleError("trace dep_epoch must be a positive exact int")
        if not _is_sha256(row.get("root")):
            raise CampaignOracleError("trace root must be a lowercase SHA-256 digest")
        if row.get("root_scope") != "POST_DEPENDENCY_REPAIR":
            raise CampaignOracleError("trace root scope must be POST_DEPENDENCY_REPAIR")
    return sha256(canonical_json(rows).encode()).hexdigest()


@dataclass(frozen=True)
class RoundClassification:
    valid: bool
    reason: str
    winner: tuple[Any, ...] | None
    win_count: int
    hold_count: int
    unexpected_count: int
    malformed_count: int
    false_accept_delta: int
    false_hold_delta: int


def _worker_ok(value: Any, workers: int) -> bool:
    return type(value) is int and 0 <= value < workers


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _valid_win(row: tuple[Any, ...], workers: int) -> bool:
    return (
        len(row) == 6
        and row[0] == WIN
        and _worker_ok(row[1], workers)
        and _is_sha256(row[2])
        and type(row[3]) is int and row[3] > 0
        and isinstance(row[4], tuple)
        and all(isinstance(x, str) and x for x in row[4])
        and _is_sha256(row[5])
    )


def _valid_hold(row: tuple[Any, ...], workers: int, expected_hold: str) -> bool:
    return (
        len(row) == 3
        and row[0] == expected_hold
        and _worker_ok(row[1], workers)
        and row[2] == _EXPECTED_EXCEPTION[expected_hold]
    )


def classify_round(
    results: Iterable[Sequence[Any]],
    workers: int,
    *,
    expected_hold: str = HOLD_STORE_ROOT_CONFLICT,
) -> RoundClassification:
    if type(workers) is not int or workers < 2:
        raise CampaignOracleError("workers must be an exact int >= 2")
    if expected_hold not in _EXPECTED_EXCEPTION:
        raise CampaignOracleError("expected_hold must be a canonical campaign HOLD")

    rows: list[tuple[Any, ...]] = []
    malformed = 0
    for raw in results:
        try:
            row = tuple(raw)
        except TypeError:
            malformed += 1
            continue
        rows.append(row)
        status = row[0] if row else None
        if status == WIN:
            malformed += 0 if _valid_win(row, workers) else 1
        elif status == expected_hold:
            malformed += 0 if _valid_hold(row, workers, expected_hold) else 1
        elif not row:
            malformed += 1

    wins = tuple(row for row in rows if _valid_win(row, workers))
    holds = tuple(row for row in rows if _valid_hold(row, workers, expected_hold))
    unexpected = tuple(
        row for row in rows
        if row and row[0] not in (WIN, expected_hold)
    )
    exact_attempts = len(rows) == workers
    worker_ids = tuple(row[1] for row in wins + holds)
    exact_worker_set = (
        len(worker_ids) == workers
        and len(set(worker_ids)) == workers
        and set(worker_ids) == set(range(workers))
    )
    valid = (
        exact_attempts
        and malformed == 0
        and not unexpected
        and exact_worker_set
        and len(wins) == 1
        and len(holds) == workers - 1
    )
    if malformed:
        reason = "MALFORMED_ROW"
    elif not exact_attempts:
        reason = "ATTEMPT_COUNT_MISMATCH"
    elif unexpected:
        reason = "UNEXPECTED_STATUS"
    elif not exact_worker_set:
        reason = "WORKER_IDENTITY_MISMATCH"
    elif len(wins) != 1:
        reason = "NON_SINGLE_WINNER"
    elif len(holds) != workers - 1:
        reason = "HOLD_COUNT_MISMATCH"
    else:
        reason = "OK"
    return RoundClassification(
        valid=valid,
        reason=reason,
        winner=wins[0] if valid else None,
        win_count=len(wins),
        hold_count=len(holds),
        unexpected_count=len(unexpected),
        malformed_count=malformed,
        false_accept_delta=0 if len(wins) == 1 else max(1, abs(len(wins) - 1)),
        false_hold_delta=0 if len(holds) == workers - 1 and not unexpected and not malformed and exact_worker_set
            else max(1, abs(len(holds) - (workers - 1)) + len(unexpected) + malformed + (0 if exact_worker_set else 1)),
    )


def trace_entry(round_index: int, winner: Sequence[Any], dep_epoch: int, final_root: str) -> dict[str, Any]:
    if type(round_index) is not int or round_index < 0:
        raise CampaignOracleError("round_index must be a nonnegative exact int")
    winner = tuple(winner)
    if len(winner) != 6 or winner[0] != WIN or type(winner[3]) is not int or winner[3] <= 0:
        raise CampaignOracleError("winner must be a canonical WIN row with a positive source epoch")
    if not _is_sha256(winner[2]) or not _is_sha256(winner[5]):
        raise CampaignOracleError("winner must bind exact revision and store roots")
    if type(dep_epoch) is not int or dep_epoch <= 0:
        raise CampaignOracleError("dep_epoch must be a positive exact int")
    if not _is_sha256(final_root):
        raise CampaignOracleError("final_root must be a lowercase SHA-256 digest")
    return {
        "round": round_index,
        "src_epoch": winner[3],
        "dep_epoch": dep_epoch,
        "root": final_root,
        "root_scope": "POST_DEPENDENCY_REPAIR",
    }


def completion_fields(trace: Sequence[dict[str, Any]], failures: Sequence[dict[str, Any]], rounds: int) -> dict[str, Any]:
    if type(rounds) is not int or rounds <= 0:
        raise CampaignOracleError("rounds must be a positive exact int")
    completed = len(trace)
    failure_count = len(failures)
    round_ids = tuple(row.get("round") if isinstance(row, dict) else None for row in trace)
    round_identity_complete = round_ids == tuple(range(rounds))
    return {
        "campaign_complete": completed == rounds and failure_count == 0 and round_identity_complete,
        "completed_rounds": completed,
        "round_failures": failure_count,
        "round_identity_complete": round_identity_complete,
    }


def execution_fields(
    *, rounds: int, workers: int, concurrent_attempts: int,
    stale_dependency_probes: int, dependency_repairs: int,
) -> dict[str, int]:
    if type(rounds) is not int or rounds <= 0 or type(workers) is not int or workers < 2:
        raise CampaignOracleError("rounds/workers must be positive exact ints")
    values=(concurrent_attempts, stale_dependency_probes, dependency_repairs)
    if any(type(v) is not int or v < 0 for v in values):
        raise CampaignOracleError("executed work counters must be nonnegative exact ints")
    targets=(workers*rounds, rounds, rounds)
    if any(v > t for v,t in zip(values,targets)):
        raise CampaignOracleError("executed work cannot exceed configured target")
    return {
        "target_concurrent_attempts": targets[0],
        "attempts": concurrent_attempts,
        "target_stale_dependency_probes": targets[1],
        "stale_dependency_probes": stale_dependency_probes,
        "target_dependency_repairs": targets[2],
        "dependency_repairs": dependency_repairs,
        "target_campaign_round_write_attempts": sum(targets),
        "total_write_attempts": sum(values),
    }
