from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Sequence


SCHEMA = "AURA-GEN25-ADMISSION-LIVENESS-WITNESS-v5"
ACTIVE_QUEUE_STATES = frozenset({"AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND", "READY"})
INACTIVE_QUEUE_STATES = frozenset({"CANCELLED", "HOLD", "SUPERSEDED", "DONE", "TERMINAL"})


class E(ValueError): pass


class EventClass(str, Enum):
    ACK_ACCEPTED = "ACK_ACCEPTED"
    ACK_ACCEPTED_PRE_EFFECT = "ACK_ACCEPTED_PRE_EFFECT"
    REJECTED = "REJECTED"
    TERMINAL_RESULT = "TERMINAL_RESULT"
    TERMINAL_ERROR = "TERMINAL_ERROR"


class CommandState(str, Enum):
    TERMINAL = "TERMINAL"
    ADMITTED_NOT_TERMINAL = "ADMITTED_NOT_TERMINAL"
    TYPED_REJECTED = "TYPED_REJECTED"
    ADMISSION_STARVED = "ADMISSION_STARVED"
    STALE_HEAD = "STALE_HEAD"
    INACTIVE_QUEUE = "INACTIVE_QUEUE"
    RECEIPT_INTEGRITY_HOLD = "RECEIPT_INTEGRITY_HOLD"
    UNKNOWN = "UNKNOWN"


class SystemState(str, Enum):
    HEALTHY_PROGRESS = "HEALTHY_PROGRESS"
    ACTIVE_INGRESS_EGRESS_STARVATION = "ACTIVE_INGRESS_EGRESS_STARVATION"
    POST_ACK_REDUCER_STALL = "POST_ACK_REDUCER_STALL"
    CURRENTNESS_BLOCK = "CURRENTNESS_BLOCK"
    RECEIPT_INTEGRITY_HOLD = "RECEIPT_INTEGRITY_HOLD"
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
class TypedReceipt:
    command_id: str
    attempt_id: str
    sequence_no: int
    observed_s: int
    event_class: EventClass
    detail_code: str


@dataclass(frozen=True)
class ConsumerObservation:
    observed: bool
    service_active: bool | None = None
    cursor_s: int | None = None
    last_scan_s: int | None = None
    progress_moved: bool | None = None
    lease_current: bool | None = None
    evidence_root: str | None = None


@dataclass(frozen=True)
class LedgerProjection:
    command_id: str
    attempt_id: str | None
    receipts: tuple[TypedReceipt, ...]
    hold_reason: str | None
    ledger_root: str


@dataclass(frozen=True)
class CommandDisposition:
    command_id: str
    state: CommandState
    reason: str
    age_s: int
    progress_age_s: int | None
    attempt_id: str | None = None
    ledger_root: str | None = None


@dataclass(frozen=True)
class RecoveryPlan:
    system_state: SystemState
    commands: tuple[CommandDisposition, ...]
    recovery_steps: tuple[str, ...]
    local_progress_proven: bool
    provider_fanout_allowed: bool
    restart_budget: int
    receipt_root: str




def _cj(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _dig(v): return sha256(_cj(v)).hexdigest()


def _text(x, name, max_len=512):
    if type(x) is not str or not x or len(x) > max_len or any(ord(c) < 32 for c in x): raise E(name)
    return x


def _nn(x, name):
    if type(x) is not int or x < 0: raise E(name)
    return x


def _bool(x, name):
    if type(x) is not bool: raise E(name)
    return x


def _opt_bool(x, name):
    if x is not None and type(x) is not bool: raise E(name)
    return x


def _opt_time(x, name, now_s):
    if x is None: return None
    _nn(x, name)
    if x > now_s: raise E("FUTURE_" + name)
    return x


def _queue_class(q):
    if q in ACTIVE_QUEUE_STATES: return "ACTIVE"
    if q in INACTIVE_QUEUE_STATES: return "INACTIVE"
    return "UNKNOWN"


def _validate_head(h): _text(h.generation,"BAD_HEAD_GENERATION",128); _text(h.digest,"BAD_HEAD_DIGEST",256)
def _validate_command(c):
    _text(c.command_id,"BAD_COMMAND_ID",256); _nn(c.created_s,"BAD_CREATED"); _text(c.generation,"BAD_COMMAND_GENERATION",128); _text(c.head_digest,"BAD_COMMAND_HEAD_DIGEST",256); _text(c.queue_state,"BAD_QUEUE_STATE",256); _bool(c.execution_authorized,"BAD_EXEC_AUTH")
def _validate_consumer(c, now_s):
    _bool(c.observed,"BAD_CONSUMER_OBSERVED"); _opt_bool(c.service_active,"BAD_SERVICE_ACTIVE"); _opt_bool(c.progress_moved,"BAD_PROGRESS_MOVED"); _opt_bool(c.lease_current,"BAD_LEASE_CURRENT"); _opt_time(c.cursor_s,"CURSOR_TIME",now_s); _opt_time(c.last_scan_s,"LAST_SCAN_TIME",now_s)
    if c.evidence_root is not None: _text(c.evidence_root,"BAD_EVIDENCE_ROOT",256)
    if not c.observed and any(v is not None for v in (c.service_active,c.cursor_s,c.last_scan_s,c.progress_moved,c.lease_current,c.evidence_root)): raise E("UNOBSERVED_CONSUMER_HAS_STATE")
    if c.observed and c.service_active is None: raise E("INCOMPLETE_CONSUMER_OBSERVATION")


def _validate_receipt(r: TypedReceipt, now_s: int):
    _text(r.command_id,"BAD_COMMAND_ID",256); _text(r.attempt_id,"BAD_ATTEMPT_ID",256); _nn(r.sequence_no,"BAD_SEQUENCE"); _nn(r.observed_s,"BAD_RECEIPT_TIME")
    if r.observed_s > now_s: raise E("FUTURE_RECEIPT")
    if not isinstance(r.event_class, EventClass): raise E("BAD_EVENT_CLASS")
    _text(r.detail_code,"BAD_DETAIL_CODE",256)


def _semantic_key(r: TypedReceipt):
    return (r.command_id,r.attempt_id,r.sequence_no,r.event_class.value,r.detail_code)


def project_receipt_ledger(command_id: str, command_created_s: int, receipts: Sequence[TypedReceipt], now_s: int) -> LedgerProjection:
    _text(command_id,"BAD_COMMAND_ID",256); _nn(command_created_s,"BAD_CREATED"); _nn(now_s,"BAD_NOW")
    matching = [r for r in receipts if r.command_id == command_id]
    for r in matching: _validate_receipt(r, now_s)
    matching = [r for r in matching if r.observed_s >= command_created_s]
    if not matching:
        root = _dig({"schema":"AURA-GEN25-TYPED-LEDGER-v1","command_id":command_id,"attempt_id":None,"events":[],"hold":None})
        return LedgerProjection(command_id,None,(),None,root)
    attempts = {r.attempt_id for r in matching}
    if len(attempts) != 1:
        root = _dig({"schema":"AURA-GEN25-TYPED-LEDGER-v1","command_id":command_id,"attempts":sorted(attempts),"hold":"AMBIGUOUS_ATTEMPT_LINEAGE"})
        return LedgerProjection(command_id,None,(),"AMBIGUOUS_ATTEMPT_LINEAGE",root)
    attempt = next(iter(attempts))
    by_seq: dict[int, TypedReceipt] = {}
    for r in sorted(matching, key=lambda x: (x.sequence_no,x.observed_s,x.event_class.value,x.detail_code)):
        prev = by_seq.get(r.sequence_no)
        if prev is None:
            by_seq[r.sequence_no] = r
        elif _semantic_key(prev) != _semantic_key(r):
            root = _dig({"schema":"AURA-GEN25-TYPED-LEDGER-v1","command_id":command_id,"attempt_id":attempt,"sequence":r.sequence_no,"hold":"SEQUENCE_EQUIVOCATION"})
            return LedgerProjection(command_id,attempt,(),"SEQUENCE_EQUIVOCATION",root)
        elif r.observed_s < prev.observed_s:
            by_seq[r.sequence_no] = r
    ordered = tuple(by_seq[k] for k in sorted(by_seq))
    terminal_seen = False
    rejection_seen = False
    for r in ordered:
        if terminal_seen or rejection_seen:
            root = _dig({"schema":"AURA-GEN25-TYPED-LEDGER-v1","command_id":command_id,"attempt_id":attempt,"hold":"EVENT_AFTER_TERMINAL_OR_REJECTION","sequence":r.sequence_no})
            return LedgerProjection(command_id,attempt,ordered,"EVENT_AFTER_TERMINAL_OR_REJECTION",root)
        if r.event_class in {EventClass.TERMINAL_RESULT,EventClass.TERMINAL_ERROR}: terminal_seen = True
        elif r.event_class == EventClass.REJECTED: rejection_seen = True
    events = [{"sequence_no":r.sequence_no,"observed_s":r.observed_s,"event_class":r.event_class.value,"detail_code":r.detail_code} for r in ordered]
    root = _dig({"schema":"AURA-GEN25-TYPED-LEDGER-v1","command_id":command_id,"attempt_id":attempt,"events":events,"hold":None})
    return LedgerProjection(command_id,attempt,ordered,None,root)


def classify_command(now_s: int, head: Head, command: Command, receipts: Sequence[TypedReceipt]) -> CommandDisposition:
    _nn(now_s,"BAD_NOW"); _validate_head(head); _validate_command(command)
    if command.created_s > now_s: raise E("FUTURE_COMMAND")
    age = now_s-command.created_s
    q = _queue_class(command.queue_state)
    if q == "INACTIVE": return CommandDisposition(command.command_id,CommandState.INACTIVE_QUEUE,f"QUEUE:{command.queue_state}",age,None)
    if q == "UNKNOWN": return CommandDisposition(command.command_id,CommandState.UNKNOWN,"QUEUE_STATE_NOT_CLASSIFIED",age,None)
    if command.generation != head.generation or command.head_digest != head.digest: return CommandDisposition(command.command_id,CommandState.STALE_HEAD,"COMMAND_HEAD_DIFFERS_FROM_CURRENT_HEAD",age,None)
    ledger = project_receipt_ledger(command.command_id,command.created_s,receipts,now_s)
    if ledger.hold_reason:
        return CommandDisposition(command.command_id,CommandState.RECEIPT_INTEGRITY_HOLD,ledger.hold_reason,age,None,ledger.attempt_id,ledger.ledger_root)
    if not ledger.receipts:
        return CommandDisposition(command.command_id,CommandState.ADMISSION_STARVED,"NO_COMMAND_BOUND_TYPED_RECEIPT",age,None,None,ledger.ledger_root)
    terminals=[r for r in ledger.receipts if r.event_class in {EventClass.TERMINAL_RESULT,EventClass.TERMINAL_ERROR}]
    if terminals:
        t=terminals[-1]; return CommandDisposition(command.command_id,CommandState.TERMINAL,f"{t.event_class.value}:{t.detail_code}",age,now_s-t.observed_s,ledger.attempt_id,ledger.ledger_root)
    rejects=[r for r in ledger.receipts if r.event_class==EventClass.REJECTED]
    if rejects:
        r=rejects[-1]; return CommandDisposition(command.command_id,CommandState.TYPED_REJECTED,f"REJECTED:{r.detail_code}",age,now_s-r.observed_s,ledger.attempt_id,ledger.ledger_root)
    acks=[r for r in ledger.receipts if r.event_class in {EventClass.ACK_ACCEPTED,EventClass.ACK_ACCEPTED_PRE_EFFECT}]
    if acks:
        a=min(acks,key=lambda r:(r.sequence_no,r.observed_s)); return CommandDisposition(command.command_id,CommandState.ADMITTED_NOT_TERMINAL,f"ACK:{a.event_class.value}",age,now_s-a.observed_s,ledger.attempt_id,ledger.ledger_root)
    return CommandDisposition(command.command_id,CommandState.UNKNOWN,"COMMAND_BOUND_RECEIPT_NOT_CLASSIFIABLE",age,None,ledger.attempt_id,ledger.ledger_root)


def compile_recovery(*,now_s:int,head:Head,commands:Iterable[Command],receipts:Sequence[TypedReceipt],consumer:ConsumerObservation,starvation_after_s:int,reducer_stall_after_s:int)->RecoveryPlan:
    _nn(now_s,"BAD_NOW"); _validate_head(head); _nn(starvation_after_s,"BAD_STARVATION_THRESHOLD"); _nn(reducer_stall_after_s,"BAD_REDUCER_THRESHOLD"); _validate_consumer(consumer,now_s)
    cmds=tuple(commands); ids=[_text(c.command_id,"BAD_COMMAND_ID",256) for c in cmds]
    if len(set(ids))!=len(ids): raise E("DUPLICATE_COMMAND_ID")
    qs=tuple(_queue_class(c.queue_state) for c in cmds); ds=tuple(classify_command(now_s,head,c,receipts) for c in cmds); active=tuple(d for d,q in zip(ds,qs) if q=="ACTIVE")
    if not cmds: system=SystemState.NO_ACTIVE_INGRESS
    elif not active: system=SystemState.HOST_VISIBILITY_REQUIRED if "UNKNOWN" in qs else SystemState.NO_ACTIVE_INGRESS
    elif any(d.state==CommandState.RECEIPT_INTEGRITY_HOLD for d in active): system=SystemState.RECEIPT_INTEGRITY_HOLD
    elif any(d.state==CommandState.STALE_HEAD for d in active): system=SystemState.CURRENTNESS_BLOCK
    elif any(d.state==CommandState.ADMITTED_NOT_TERMINAL and (d.progress_age_s or 0)>=reducer_stall_after_s for d in active): system=SystemState.POST_ACK_REDUCER_STALL
    elif any(d.state==CommandState.ADMISSION_STARVED and d.age_s>=starvation_after_s for d in active): system=SystemState.ACTIVE_INGRESS_EGRESS_STARVATION
    elif all(d.state==CommandState.TERMINAL for d in active): system=SystemState.HEALTHY_PROGRESS
    else: system=SystemState.HOST_VISIBILITY_REQUIRED
    if system==SystemState.RECEIPT_INTEGRITY_HOLD:
        steps=("FREEZE_COMMAND_REPLAY_AND_RESTART","RECONCILE_TYPED_RECEIPT_LEDGER","ESTABLISH_ATTEMPT_LINEAGE_AND_SEQUENCE_INTEGRITY","RECLASSIFY_COMMAND_PROGRESS") ; rb=0
    elif system==SystemState.ACTIVE_INGRESS_EGRESS_STARVATION:
        if not consumer.observed:
            steps=("OBSERVE_PROJECT006_SERVICE_STATE","HASH_INSTALLED_CONSUMER","READ_CONSUMER_CURSOR_STATE_AND_LOCAL_RECEIPTS","REUSE_EXISTING_EXECUTION_FALSE_CANARY","RUN_EXACTLY_ONE_CONSUMER_ITERATION","EMIT_COMMAND_BOUND_TYPED_ADMISSION_OR_FIRST_FAILING_GATE"); rb=0
        elif consumer.service_active is False:
            steps=("CAPTURE_PRE_STATE","RESTART_AURA_PROJECT006_ONCE","REUSE_EXISTING_EXECUTION_FALSE_CANARY","RUN_EXACTLY_ONE_CONSUMER_ITERATION","CAPTURE_POST_STATE_AND_LOCAL_RECEIPTS","EMIT_COMMAND_BOUND_TYPED_ADMISSION_OR_FIRST_FAILING_GATE"); rb=1
        elif consumer.progress_moved is False:
            steps=("CAPTURE_STUCK_ACTIVE_STATE","RESTART_AURA_PROJECT006_ONCE","REUSE_EXISTING_EXECUTION_FALSE_CANARY","RUN_EXACTLY_ONE_CONSUMER_ITERATION","CAPTURE_POST_STATE_AND_LOCAL_RECEIPTS","EMIT_COMMAND_BOUND_TYPED_ADMISSION_OR_FIRST_FAILING_GATE"); rb=1
        elif consumer.progress_moved is None:
            steps=("CAPTURE_PRE_STATE","REUSE_EXISTING_EXECUTION_FALSE_CANARY","RUN_EXACTLY_ONE_CONSUMER_ITERATION","CAPTURE_POST_STATE_AND_LOCAL_RECEIPTS","COMPARE_CURSOR_STATE_RECEIPT_MOVEMENT","EMIT_COMMAND_BOUND_TYPED_ADMISSION_OR_FIRST_FAILING_GATE"); rb=0
        else:
            steps=("INSPECT_COMMAND_BOUND_RECEIPT_OR_CALLBACK_BOUNDARY","EMIT_COMMAND_BOUND_TYPED_ADMISSION_OR_FIRST_FAILING_GATE"); rb=0
    elif system==SystemState.POST_ACK_REDUCER_STALL:
        steps=("DO_NOT_REPLAY_EFFECT","CORRELATE_TYPED_ATTEMPT_TO_TERMINAL_CALLBACK","INSPECT_CALLBACK_REDUCER_AND_EGRESS_WRITER","EMIT_TYPED_TERMINAL_OR_FIRST_FAILING_GATE"); rb=0
    elif system==SystemState.CURRENTNESS_BLOCK: steps=("REBIND_EXACT_CURRENT_HEAD","REVALIDATE_COMMAND_AUTHORITY_AND_ADMISSION_SURFACE"); rb=0
    elif system==SystemState.HOST_VISIBILITY_REQUIRED: steps=("OBSERVE_CONSUMER_CURSOR_LEASE_LAST_SCAN","EMIT_TYPED_COMMAND_STATE"); rb=0
    else: steps=(); rb=0
    progress=any(d.state in {CommandState.TERMINAL,CommandState.ADMITTED_NOT_TERMINAL,CommandState.TYPED_REJECTED} for d in active)
    payload={"schema":SCHEMA,"head":{"generation":head.generation,"digest":head.digest},"system_state":system.value,"commands":[{"command_id":d.command_id,"state":d.state.value,"reason":d.reason,"age_s":d.age_s,"progress_age_s":d.progress_age_s,"attempt_id":d.attempt_id,"ledger_root":d.ledger_root} for d in ds],"queue_classes":list(qs),"consumer":{"observed":consumer.observed,"service_active":consumer.service_active,"cursor_s":consumer.cursor_s,"last_scan_s":consumer.last_scan_s,"progress_moved":consumer.progress_moved,"lease_current_advisory":consumer.lease_current,"evidence_root":consumer.evidence_root},"recovery_steps":list(steps),"local_progress_proven":progress,"provider_fanout_allowed":False,"restart_budget":rb,"authority_ceiling":"D0","gate10":False}
    return RecoveryPlan(system,ds,steps,progress,False,rb,_dig(payload))


def omega8_keeper(axes): return len(axes)==8 and all(type(x) is int and x==2 for x in axes)
def context13_preserves_invalid(core8,tail5):
    if len(tail5)!=5 or any(type(x) is not int or x not in (0,1,2) for x in tail5): raise E("BAD_13D_TAIL")
    return omega8_keeper(core8)
