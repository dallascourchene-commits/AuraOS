from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Sequence

SCHEMA = "AURA-GEN25-ADMISSION-LIVENESS-WITNESS-v2"

class E(ValueError):
    pass

class CommandState(str, Enum):
    TERMINAL = "TERMINAL"
    ADMITTED_NOT_TERMINAL = "ADMITTED_NOT_TERMINAL"
    TYPED_REJECTED = "TYPED_REJECTED"
    ADMISSION_STARVED = "ADMISSION_STARVED"
    STALE_HEAD = "STALE_HEAD"
    UNKNOWN = "UNKNOWN"

class SystemState(str, Enum):
    HEALTHY_PROGRESS = "HEALTHY_PROGRESS"
    ACTIVE_INGRESS_EGRESS_STARVATION = "ACTIVE_INGRESS_EGRESS_STARVATION"
    POST_ACK_REDUCER_STALL = "POST_ACK_REDUCER_STALL"
    CURRENTNESS_BLOCK = "CURRENTNESS_BLOCK"
    HOST_VISIBILITY_REQUIRED = "HOST_VISIBILITY_REQUIRED"
    NO_ACTIVE_INGRESS = "NO_ACTIVE_INGRESS"

@dataclass(frozen=True)
class Head:
    generation: str
    digest: str

@dataclass(frozen=True)
class Command:
    command_id: str
    created_s: int
    generation: str
    head_digest: str
    queue_state: str
    execution_authorized: bool

@dataclass(frozen=True)
class Receipt:
    command_id: str
    observed_s: int
    kind: str
    state: str

@dataclass(frozen=True)
class ConsumerObservation:
    observed: bool
    service_active: bool | None = None
    cursor_s: int | None = None
    last_scan_s: int | None = None
    lease_current: bool | None = None

@dataclass(frozen=True)
class CommandDisposition:
    command_id: str
    state: CommandState
    reason: str
    age_s: int
    progress_age_s: int | None

@dataclass(frozen=True)
class RecoveryPlan:
    system_state: SystemState
    commands: tuple[CommandDisposition, ...]
    recovery_steps: tuple[str, ...]
    local_progress_proven: bool
    provider_fanout_allowed: bool
    restart_budget: int
    receipt_root: str


def _cj(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def _dig(v) -> str:
    return sha256(_cj(v)).hexdigest()

def _valid_text(x: str, name: str, *, max_len: int = 512) -> str:
    if not isinstance(x, str) or not x or len(x) > max_len or any(ord(c) < 32 for c in x):
        raise E(name)
    return x

def _valid_id(x: str) -> str:
    return _valid_text(x, "BAD_COMMAND_ID", max_len=256)

def _valid_nonneg(x: int, name: str) -> int:
    if type(x) is not int or x < 0:
        raise E(name)
    return x

def _bool(x, name: str) -> bool:
    if type(x) is not bool:
        raise E(name)
    return x

def _opt_bool(x, name: str) -> bool | None:
    if x is not None and type(x) is not bool:
        raise E(name)
    return x

def _opt_time(x, name: str, now_s: int) -> int | None:
    if x is None:
        return None
    _valid_nonneg(x, name)
    if x > now_s:
        raise E(f"FUTURE_{name}")
    return x

def _validate_head(head: Head) -> None:
    _valid_text(head.generation, "BAD_HEAD_GENERATION", max_len=128)
    _valid_text(head.digest, "BAD_HEAD_DIGEST", max_len=256)

def _validate_command(command: Command) -> None:
    _valid_id(command.command_id)
    _valid_nonneg(command.created_s, "BAD_CREATED")
    _valid_text(command.generation, "BAD_COMMAND_GENERATION", max_len=128)
    _valid_text(command.head_digest, "BAD_COMMAND_HEAD_DIGEST", max_len=256)
    _valid_text(command.queue_state, "BAD_QUEUE_STATE", max_len=256)
    _bool(command.execution_authorized, "BAD_EXEC_AUTH")

def _validate_bound_receipt(receipt: Receipt, now_s: int) -> None:
    _valid_id(receipt.command_id)
    _valid_nonneg(receipt.observed_s, "BAD_RECEIPT_TIME")
    if receipt.observed_s > now_s:
        raise E("FUTURE_RECEIPT")
    _valid_text(receipt.kind, "BAD_RECEIPT_KIND", max_len=64)
    _valid_text(receipt.state, "BAD_RECEIPT_STATE", max_len=256)

def _validate_consumer(consumer: ConsumerObservation, now_s: int) -> None:
    _bool(consumer.observed, "BAD_CONSUMER_OBSERVED")
    _opt_bool(consumer.service_active, "BAD_SERVICE_ACTIVE")
    _opt_bool(consumer.lease_current, "BAD_LEASE_CURRENT")
    _opt_time(consumer.cursor_s, "CURSOR_TIME", now_s)
    _opt_time(consumer.last_scan_s, "LAST_SCAN_TIME", now_s)
    if not consumer.observed:
        if any(v is not None for v in (consumer.service_active, consumer.cursor_s, consumer.last_scan_s, consumer.lease_current)):
            raise E("UNOBSERVED_CONSUMER_HAS_STATE")
    else:
        if consumer.service_active is None or consumer.lease_current is None:
            raise E("INCOMPLETE_CONSUMER_OBSERVATION")


def classify_command(now_s: int, head: Head, command: Command, receipts: Sequence[Receipt]) -> CommandDisposition:
    now_s = _valid_nonneg(now_s, "BAD_NOW")
    _validate_head(head)
    _validate_command(command)
    if command.created_s > now_s:
        raise E("FUTURE_COMMAND")
    age = now_s - command.created_s
    if command.generation != head.generation or command.head_digest != head.digest:
        return CommandDisposition(command.command_id, CommandState.STALE_HEAD, "COMMAND_HEAD_DIFFERS_FROM_CURRENT_HEAD", age, None)

    matching = [r for r in receipts if r.command_id == command.command_id]
    for r in matching:
        _validate_bound_receipt(r, now_s)
    bound = [r for r in matching if r.observed_s >= command.created_s]
    bound.sort(key=lambda r: (r.observed_s, r.kind, r.state))
    if not bound:
        return CommandDisposition(command.command_id, CommandState.ADMISSION_STARVED, "NO_COMMAND_BOUND_TYPED_RECEIPT", age, None)
    last = bound[-1]
    progress_age = now_s - last.observed_s
    terminal = [r for r in bound if r.kind in {"RESULT", "ERROR"} or r.state.startswith("TERMINAL_")]
    if terminal:
        t = terminal[-1]
        return CommandDisposition(command.command_id, CommandState.TERMINAL, f"{t.kind}:{t.state}", age, now_s - t.observed_s)
    rejected = [r for r in bound if "REJECT" in r.state or "BLOCK" in r.state]
    if rejected:
        r = rejected[-1]
        return CommandDisposition(command.command_id, CommandState.TYPED_REJECTED, f"{r.kind}:{r.state}", age, now_s - r.observed_s)
    acked = [r for r in bound if r.kind == "ACK" and r.state in {"ACK_ACCEPTED", "ACK_ACCEPTED_PRE_EFFECT"}]
    if acked:
        a = acked[-1]
        return CommandDisposition(command.command_id, CommandState.ADMITTED_NOT_TERMINAL, f"ACK:{a.state}", age, now_s - a.observed_s)
    return CommandDisposition(command.command_id, CommandState.UNKNOWN, "COMMAND_BOUND_RECEIPT_NOT_CLASSIFIABLE", age, progress_age)


def compile_recovery(
    *,
    now_s: int,
    head: Head,
    commands: Iterable[Command],
    receipts: Sequence[Receipt],
    consumer: ConsumerObservation,
    starvation_after_s: int,
    reducer_stall_after_s: int,
) -> RecoveryPlan:
    now_s = _valid_nonneg(now_s, "BAD_NOW")
    _validate_head(head)
    starvation_after_s = _valid_nonneg(starvation_after_s, "BAD_STARVATION_THRESHOLD")
    reducer_stall_after_s = _valid_nonneg(reducer_stall_after_s, "BAD_REDUCER_THRESHOLD")
    _validate_consumer(consumer, now_s)
    cmds = tuple(commands)
    ids = [_valid_id(c.command_id) for c in cmds]
    if len(set(ids)) != len(ids):
        raise E("DUPLICATE_COMMAND_ID")
    dispositions = tuple(classify_command(now_s, head, c, receipts) for c in cmds)

    if not cmds:
        system = SystemState.NO_ACTIVE_INGRESS
    elif any(d.state == CommandState.STALE_HEAD for d in dispositions):
        system = SystemState.CURRENTNESS_BLOCK
    elif any(d.state == CommandState.ADMITTED_NOT_TERMINAL and (d.progress_age_s or 0) >= reducer_stall_after_s for d in dispositions):
        system = SystemState.POST_ACK_REDUCER_STALL
    elif any(d.state == CommandState.ADMISSION_STARVED and d.age_s >= starvation_after_s for d in dispositions):
        system = SystemState.ACTIVE_INGRESS_EGRESS_STARVATION
    elif all(d.state == CommandState.TERMINAL for d in dispositions):
        system = SystemState.HEALTHY_PROGRESS
    else:
        system = SystemState.HOST_VISIBILITY_REQUIRED

    if system == SystemState.ACTIVE_INGRESS_EGRESS_STARVATION:
        if not consumer.observed:
            steps = (
                "OBSERVE_PROJECT006_SERVICE_STATE",
                "HASH_INSTALLED_CONSUMER",
                "READ_CONSUMER_CURSOR_STATE_AND_LOCAL_RECEIPTS",
                "REUSE_EXISTING_EXECUTION_FALSE_CANARY",
                "RUN_EXACTLY_ONE_CONSUMER_ITERATION",
                "EMIT_COMMAND_BOUND_TYPED_ADMISSION_OR_FIRST_FAILING_GATE",
            )
            restart_budget = 0
        else:
            restart_needed = (consumer.service_active is False) or (consumer.lease_current is False)
            steps = (
                "CAPTURE_PRE_STATE",
                *(("RESTART_AURA_PROJECT006_ONCE",) if restart_needed else ()),
                "REUSE_EXISTING_EXECUTION_FALSE_CANARY",
                "RUN_EXACTLY_ONE_CONSUMER_ITERATION",
                "CAPTURE_POST_STATE_AND_LOCAL_RECEIPTS",
                "EMIT_COMMAND_BOUND_TYPED_ADMISSION_OR_FIRST_FAILING_GATE",
            )
            restart_budget = 1 if restart_needed else 0
    elif system == SystemState.POST_ACK_REDUCER_STALL:
        steps = (
            "DO_NOT_REPLAY_EFFECT",
            "CORRELATE_ACK_ATTEMPT_ID_TO_TERMINAL_CALLBACK",
            "INSPECT_CALLBACK_REDUCER_AND_EGRESS_WRITER",
            "EMIT_TYPED_TERMINAL_OR_FIRST_FAILING_GATE",
        )
        restart_budget = 0
    elif system == SystemState.CURRENTNESS_BLOCK:
        steps = ("REBIND_EXACT_CURRENT_HEAD", "REVALIDATE_COMMAND_AUTHORITY_AND_ADMISSION_SURFACE")
        restart_budget = 0
    elif system == SystemState.HOST_VISIBILITY_REQUIRED:
        steps = ("OBSERVE_CONSUMER_CURSOR_LEASE_LAST_SCAN", "EMIT_TYPED_COMMAND_STATE")
        restart_budget = 0
    else:
        steps = ()
        restart_budget = 0

    progress = any(d.state in {CommandState.TERMINAL, CommandState.ADMITTED_NOT_TERMINAL, CommandState.TYPED_REJECTED} for d in dispositions)
    fanout = False
    payload = {
        "schema": SCHEMA,
        "system_state": system.value,
        "commands": [
            {
                "command_id": d.command_id,
                "state": d.state.value,
                "reason": d.reason,
                "age_s": d.age_s,
                "progress_age_s": d.progress_age_s,
            }
            for d in dispositions
        ],
        "recovery_steps": list(steps),
        "local_progress_proven": progress,
        "provider_fanout_allowed": fanout,
        "restart_budget": restart_budget,
        "authority_ceiling": "D0",
        "gate10": False,
    }
    return RecoveryPlan(system, dispositions, steps, progress, fanout, restart_budget, _dig(payload))


def omega8_keeper(axes: Sequence[int]) -> bool:
    return len(axes) == 8 and all(type(x) is int and x == 2 for x in axes)

def context13_preserves_invalid(core8: Sequence[int], tail5: Sequence[int]) -> bool:
    if len(tail5) != 5 or any(type(x) is not int or x not in (0, 1, 2) for x in tail5):
        raise E("BAD_13D_TAIL")
    return omega8_keeper(core8)
