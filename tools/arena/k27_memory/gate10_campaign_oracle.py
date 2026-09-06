from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence
import re

SCHEMA = "AURA-K27-GATE10-CAMPAIGN-ORACLE-v1"
WIN = "WIN"
HOLD_STORE_ROOT_CONFLICT = "HOLD_STORE_ROOT_CONFLICT"
HOLD_STALE_DEPENDENCY = "HOLD_STALE_DEPENDENCY"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CampaignOracleError(ValueError):
    pass


@dataclass(frozen=True)
class RoundClassification:
    valid: bool
    reason: str
    winner: tuple[Any, ...] | None
    win_count: int
    hold_count: int
    unexpected_count: int
    false_accept_delta: int
    false_hold_delta: int


def classify_round(
    results: Iterable[Sequence[Any]],
    workers: int,
    *,
    expected_hold: str = HOLD_STORE_ROOT_CONFLICT,
) -> RoundClassification:
    if type(workers) is not int or workers < 2:
        raise CampaignOracleError("workers must be an exact int >= 2")
    if expected_hold not in (HOLD_STORE_ROOT_CONFLICT, HOLD_STALE_DEPENDENCY):
        raise CampaignOracleError("expected_hold must be a canonical campaign HOLD")
    rows = tuple(tuple(row) for row in results)
    if any(not row for row in rows):
        raise CampaignOracleError("round result rows must be nonempty")
    wins = tuple(row for row in rows if row[0] == WIN)
    holds = tuple(row for row in rows if row[0] == expected_hold)
    unexpected = tuple(row for row in rows if row[0] not in (WIN, expected_hold))
    exact_attempts = len(rows) == workers
    valid = exact_attempts and len(wins) == 1 and len(holds) == workers - 1 and not unexpected
    if not exact_attempts:
        reason = "ATTEMPT_COUNT_MISMATCH"
    elif unexpected:
        reason = "UNEXPECTED_STATUS"
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
        false_accept_delta=0 if len(wins) == 1 else max(1, abs(len(wins) - 1)),
        false_hold_delta=0 if len(holds) == workers - 1 and not unexpected else max(1, abs(len(holds) - (workers - 1)) + len(unexpected)),
    )


def trace_entry(round_index: int, winner: Sequence[Any], dep_epoch: int, final_root: str) -> dict[str, Any]:
    if type(round_index) is not int or round_index < 0:
        raise CampaignOracleError("round_index must be a nonnegative exact int")
    winner = tuple(winner)
    if len(winner) < 4 or winner[0] != WIN or type(winner[3]) is not int or winner[3] <= 0:
        raise CampaignOracleError("winner must be a valid WIN row with a positive source epoch")
    if type(dep_epoch) is not int or dep_epoch <= 0:
        raise CampaignOracleError("dep_epoch must be a positive exact int")
    if not isinstance(final_root, str) or not _SHA256.fullmatch(final_root):
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
    return {
        "campaign_complete": completed == rounds and failure_count == 0,
        "completed_rounds": completed,
        "round_failures": failure_count,
    }
