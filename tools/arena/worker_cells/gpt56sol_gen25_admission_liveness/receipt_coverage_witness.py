from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Sequence

SCHEMA = "AURA-GEN25-RECEIPT-COVERAGE-WITNESS-v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class E(ValueError):
    pass


class CoverageState(str, Enum):
    COMPLETE = "COMPLETE"
    MISSING_EXPECTED = "MISSING_EXPECTED"
    UNEXPECTED_OBSERVED = "UNEXPECTED_OBSERVED"
    COVERAGE_MISMATCH = "COVERAGE_MISMATCH"
    LEDGER_INTEGRITY_HOLD = "LEDGER_INTEGRITY_HOLD"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    UNPROVEN = "UNPROVEN"


@dataclass(frozen=True)
class CoverageContract:
    command_id: str
    attempt_id: str
    expected_sequence_ids: tuple[int, ...]
    witness_root: str
    contract_root: str


@dataclass(frozen=True)
class CoverageReceipt:
    command_id: str
    attempt_id: str
    state: CoverageState
    expected_sequence_ids: tuple[int, ...]
    observed_sequence_ids: tuple[int, ...]
    missing_sequence_ids: tuple[int, ...]
    unexpected_sequence_ids: tuple[int, ...]
    ledger_root: str | None
    coverage_complete: bool
    provider_fanout_allowed: bool
    effect_authority: bool
    gate10: bool
    receipt_root: str


def _cj(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _dig(value: Any) -> str:
    return sha256(_cj(value)).hexdigest()


def _text(value: str, name: str, max_len: int = 256) -> str:
    if type(value) is not str or not value or len(value) > max_len or any(ord(ch) < 32 for ch in value):
        raise E(name)
    return value


def _root(value: str, name: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise E(name)
    return value


def _seq(value: int) -> int:
    # Aura GEN25 v5 intentionally permits zero and does not declare a 1-based origin.
    if type(value) is not int or value < 0:
        raise E("BAD_SEQUENCE_ID")
    return value


def _canonical_ids(values: Iterable[int], *, name: str) -> tuple[int, ...]:
    vals = tuple(_seq(v) for v in values)
    if len(set(vals)) != len(vals):
        raise E(name)
    return tuple(sorted(vals))


def compile_coverage_contract(
    *,
    command_id: str,
    attempt_id: str,
    expected_sequence_ids: Iterable[int],
    witness_root: str,
) -> CoverageContract:
    command_id = _text(command_id, "BAD_COMMAND_ID")
    attempt_id = _text(attempt_id, "BAD_ATTEMPT_ID")
    expected = _canonical_ids(expected_sequence_ids, name="DUPLICATE_EXPECTED_SEQUENCE_ID")
    witness_root = _root(witness_root, "BAD_WITNESS_ROOT")
    payload = {
        "schema": SCHEMA,
        "command_id": command_id,
        "attempt_id": attempt_id,
        "expected_sequence_ids": list(expected),
        "witness_root": witness_root,
        "authority_ceiling": "D0_COVERAGE_ONLY",
    }
    return CoverageContract(command_id, attempt_id, expected, witness_root, _dig(payload))


def verify_projection_coverage(contract: CoverageContract, projection: Any) -> CoverageReceipt:
    """Verify exact expected-set coverage over a typed-ledger projection.

    `projection` is intentionally structural rather than importing the live v5 module.
    It must expose command_id, attempt_id, receipts, hold_reason, and ledger_root;
    each receipt must expose sequence_no. This keeps the witness stackable while the
    owner module evolves.
    """
    if not isinstance(contract, CoverageContract):
        raise E("BAD_COVERAGE_CONTRACT")
    _root(contract.contract_root, "BAD_CONTRACT_ROOT")

    try:
        command_id = projection.command_id
        attempt_id = projection.attempt_id
        receipts: Sequence[Any] = tuple(projection.receipts)
        hold_reason = projection.hold_reason
        ledger_root = projection.ledger_root
    except Exception as exc:  # structural boundary; fail closed
        raise E("BAD_LEDGER_PROJECTION") from exc

    _text(command_id, "BAD_PROJECTION_COMMAND_ID")
    if attempt_id is not None:
        _text(attempt_id, "BAD_PROJECTION_ATTEMPT_ID")
    _root(ledger_root, "BAD_LEDGER_ROOT")

    observed_raw = []
    for receipt in receipts:
        try:
            observed_raw.append(receipt.sequence_no)
        except Exception as exc:
            raise E("BAD_PROJECTED_RECEIPT") from exc
    observed = _canonical_ids(observed_raw, name="DUPLICATE_PROJECTED_SEQUENCE_ID")

    expected = contract.expected_sequence_ids
    missing = tuple(sorted(set(expected) - set(observed)))
    unexpected = tuple(sorted(set(observed) - set(expected)))

    if hold_reason is not None:
        _text(hold_reason, "BAD_LEDGER_HOLD_REASON", max_len=512)
        state = CoverageState.LEDGER_INTEGRITY_HOLD
    elif command_id != contract.command_id or attempt_id != contract.attempt_id:
        state = CoverageState.SCOPE_MISMATCH
    elif not missing and not unexpected:
        state = CoverageState.COMPLETE
    elif missing and not unexpected:
        state = CoverageState.MISSING_EXPECTED
    elif unexpected and not missing:
        state = CoverageState.UNEXPECTED_OBSERVED
    else:
        state = CoverageState.COVERAGE_MISMATCH

    complete = state is CoverageState.COMPLETE
    payload = {
        "schema": SCHEMA,
        "contract_root": contract.contract_root,
        "command_id": contract.command_id,
        "attempt_id": contract.attempt_id,
        "state": state.value,
        "expected_sequence_ids": list(expected),
        "observed_sequence_ids": list(observed),
        "missing_sequence_ids": list(missing),
        "unexpected_sequence_ids": list(unexpected),
        "ledger_root": ledger_root,
        "ledger_hold_reason": hold_reason,
        "coverage_complete": complete,
        "provider_fanout_allowed": False,
        "effect_authority": False,
        "gate10": False,
    }
    return CoverageReceipt(
        command_id=contract.command_id,
        attempt_id=contract.attempt_id,
        state=state,
        expected_sequence_ids=expected,
        observed_sequence_ids=observed,
        missing_sequence_ids=missing,
        unexpected_sequence_ids=unexpected,
        ledger_root=ledger_root,
        coverage_complete=complete,
        provider_fanout_allowed=False,
        effect_authority=False,
        gate10=False,
        receipt_root=_dig(payload),
    )


def k27_coverage_coordinate(receipt: CoverageReceipt) -> tuple[int, int, int, int]:
    """Logical K27 coordinate only; never truth/authentication/effect/native KV."""
    if not isinstance(receipt, CoverageReceipt):
        raise E("BAD_COVERAGE_RECEIPT")
    identity = 2 if receipt.state is not CoverageState.SCOPE_MISMATCH else 0
    coverage = 2 if receipt.coverage_complete else (1 if receipt.state in {CoverageState.MISSING_EXPECTED, CoverageState.UNEXPECTED_OBSERVED, CoverageState.COVERAGE_MISMATCH} else 0)
    reuse = 2 if receipt.coverage_complete else 0
    return identity, coverage, reuse, 9 * identity + 3 * coverage + reuse


def omega8_keeper(axes: Sequence[int]) -> bool:
    return len(axes) == 8 and all(type(x) is int and x == 2 for x in axes)


def context13_preserves_invalid(core8: Sequence[int], tail5: Sequence[int]) -> bool:
    if len(tail5) != 5 or any(type(x) is not int or x not in (0, 1, 2) for x in tail5):
        raise E("BAD_13D_TAIL")
    return omega8_keeper(core8)
