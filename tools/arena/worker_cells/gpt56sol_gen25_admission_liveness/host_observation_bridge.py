from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Sequence

from liveness_witness import ConsumerObservation, E, Head

SCHEMA = "AURA-PROJECT006-OBSERVATION-BRIDGE-v1"
EXPECTED_HEAD = Head("GEN25", "d91e0a39358901c5")
SERVICE = "aura-project006.service"
CONSUMER_PATH = "/home/john_of_wick/.config/aura-drive/bin/aura_drive_swarm_consumer_v1.py"
STATE_PATH = "/home/john_of_wick/.config/aura-drive/state/swarm_consumer_v1/consumer_state.json"
RECEIPTS_PATH = "/home/john_of_wick/.config/aura-drive/state/swarm_consumer_v1/receipts"
CANARY_COMMAND_ID = "AWJ033-CURRENT-CONSUMER-WAKE-ADMISSION-DIAGNOSTIC-20260902T234505Z-R1"
CANARY_DRIVE_ID = "1HUDT8fQM1eD3ifrR3TnUQutybplTjQ3X"
OWNER_HOST_SOURCE_ID = "1642dU_3XEGZp3C25q4wqNFz4cVReq9YJ-515QGWqdf0"
COMMAND_SOURCE_ID = "1utcDMI3aIicEQGdrwJjR-k7cptPYHzTHiv_p8rQyHso"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

@dataclass(frozen=True)
class ProbeStep:
    name: str
    argv: tuple[str, ...]
    effect: str

@dataclass(frozen=True)
class ProbePlan:
    head: Head
    service: str
    consumer_path: str
    state_path: str
    receipts_path: str
    canary_command_id: str
    canary_drive_id: str
    steps: tuple[ProbeStep, ...]
    plan_root: str

@dataclass(frozen=True)
class HostSnapshot:
    observed_s: int
    active_state: str
    sub_state: str
    main_pid: int
    consumer_sha256: str
    state_sha256: str | None
    receipts_inventory_root: str | None
    command_bound_receipt_root: str | None = None
    cursor_s: int | None = None
    last_scan_s: int | None = None
    lease_current: bool | None = None

@dataclass(frozen=True)
class SnapshotPair:
    before_root: str
    after_root: str
    progress_moved: bool
    observation: ConsumerObservation


def _cj(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def _root(v) -> str:
    return sha256(_cj(v)).hexdigest()

def _text(v, name, max_len=1024):
    if not isinstance(v, str) or not v or len(v) > max_len or any(ord(c) < 32 for c in v):
        raise E(name)
    return v

def _nonneg(v, name):
    if type(v) is not int or v < 0:
        raise E(name)
    return v

def _sha(v, name, *, optional=False):
    if optional and v is None:
        return None
    if not isinstance(v, str) or _HEX64.fullmatch(v) is None:
        raise E(name)
    return v

def _opt_time(v, name, observed_s):
    if v is None:
        return None
    _nonneg(v, name)
    if v > observed_s:
        raise E(f"FUTURE_{name}")
    return v

def _opt_bool(v, name):
    if v is not None and type(v) is not bool:
        raise E(name)
    return v


def compile_read_only_probe(head: Head = EXPECTED_HEAD) -> ProbePlan:
    if head != EXPECTED_HEAD:
        raise E("HEAD_NOT_AUTHORITATIVE_GEN25")
    steps = (
        ProbeStep("SERVICE_STATE", ("systemctl", "--user", "show", SERVICE, "-p", "ActiveState", "-p", "SubState", "-p", "MainPID"), "READ_ONLY"),
        ProbeStep("CONSUMER_SHA256", ("sha256sum", CONSUMER_PATH), "READ_ONLY"),
        ProbeStep("CONSUMER_STATE", ("cat", STATE_PATH), "READ_ONLY"),
        ProbeStep("RECEIPT_INVENTORY", ("ls", "-lt", RECEIPTS_PATH), "READ_ONLY"),
        ProbeStep("CANARY_RECEIPT_MATCH", ("grep", "-R", "-l", "--fixed-strings", CANARY_COMMAND_ID, RECEIPTS_PATH), "READ_ONLY"),
    )
    payload = {
        "schema": SCHEMA,
        "head": {"generation": head.generation, "digest": head.digest},
        "service": SERVICE,
        "consumer_path": CONSUMER_PATH,
        "state_path": STATE_PATH,
        "receipts_path": RECEIPTS_PATH,
        "canary": {"command_id": CANARY_COMMAND_ID, "drive_id": CANARY_DRIVE_ID},
        "sources": [OWNER_HOST_SOURCE_ID, COMMAND_SOURCE_ID],
        "steps": [{"name": s.name, "argv": list(s.argv), "effect": s.effect} for s in steps],
        "restart_authorized": False,
        "consumer_iteration_authorized": False,
        "provider_fanout_authorized": False,
    }
    return ProbePlan(head, SERVICE, CONSUMER_PATH, STATE_PATH, RECEIPTS_PATH, CANARY_COMMAND_ID, CANARY_DRIVE_ID, steps, _root(payload))


def validate_snapshot(snapshot: HostSnapshot, *, observation_cut_s: int, head: Head = EXPECTED_HEAD) -> str:
    if head != EXPECTED_HEAD:
        raise E("HEAD_NOT_AUTHORITATIVE_GEN25")
    _nonneg(observation_cut_s, "BAD_OBSERVATION_CUT")
    _nonneg(snapshot.observed_s, "BAD_OBSERVED_TIME")
    if snapshot.observed_s > observation_cut_s:
        raise E("FUTURE_HOST_SNAPSHOT")
    _text(snapshot.active_state, "BAD_ACTIVE_STATE", 64)
    _text(snapshot.sub_state, "BAD_SUB_STATE", 64)
    _nonneg(snapshot.main_pid, "BAD_MAIN_PID")
    _sha(snapshot.consumer_sha256, "BAD_CONSUMER_SHA256")
    _sha(snapshot.state_sha256, "BAD_STATE_SHA256", optional=True)
    _sha(snapshot.receipts_inventory_root, "BAD_RECEIPTS_ROOT", optional=True)
    _sha(snapshot.command_bound_receipt_root, "BAD_COMMAND_RECEIPT_ROOT", optional=True)
    _opt_time(snapshot.cursor_s, "CURSOR_TIME", snapshot.observed_s)
    _opt_time(snapshot.last_scan_s, "LAST_SCAN_TIME", snapshot.observed_s)
    _opt_bool(snapshot.lease_current, "BAD_LEASE_CURRENT")
    payload = {
        "schema": SCHEMA,
        "head": {"generation": head.generation, "digest": head.digest},
        "service": SERVICE,
        "consumer_path": CONSUMER_PATH,
        "state_path": STATE_PATH,
        "receipts_path": RECEIPTS_PATH,
        "snapshot": {
            "observed_s": snapshot.observed_s,
            "active_state": snapshot.active_state,
            "sub_state": snapshot.sub_state,
            "main_pid": snapshot.main_pid,
            "consumer_sha256": snapshot.consumer_sha256,
            "state_sha256": snapshot.state_sha256,
            "receipts_inventory_root": snapshot.receipts_inventory_root,
            "command_bound_receipt_root": snapshot.command_bound_receipt_root,
            "cursor_s": snapshot.cursor_s,
            "last_scan_s": snapshot.last_scan_s,
            "lease_current_advisory": snapshot.lease_current,
        },
        "authority_ceiling": "D0_OBSERVATION_ONLY",
    }
    return _root(payload)


def service_active(snapshot: HostSnapshot) -> bool:
    return snapshot.active_state == "active" and snapshot.main_pid > 0


def compare_snapshots(before: HostSnapshot, after: HostSnapshot, *, observation_cut_s: int, head: Head = EXPECTED_HEAD) -> SnapshotPair:
    before_root = validate_snapshot(before, observation_cut_s=observation_cut_s, head=head)
    after_root = validate_snapshot(after, observation_cut_s=observation_cut_s, head=head)
    if after.observed_s < before.observed_s:
        raise E("SNAPSHOT_TIME_REVERSED")
    moved = any((
        before.state_sha256 != after.state_sha256,
        before.command_bound_receipt_root != after.command_bound_receipt_root,
        before.cursor_s != after.cursor_s,
        before.last_scan_s != after.last_scan_s,
    ))
    evidence_root = _root({"before": before_root, "after": after_root, "progress_moved": moved})
    observation = ConsumerObservation(
        observed=True,
        service_active=service_active(after),
        cursor_s=after.cursor_s,
        last_scan_s=after.last_scan_s,
        progress_moved=moved,
        lease_current=after.lease_current,
        evidence_root=evidence_root,
    )
    return SnapshotPair(before_root, after_root, moved, observation)


def single_snapshot_observation(snapshot: HostSnapshot, *, observation_cut_s: int, head: Head = EXPECTED_HEAD) -> ConsumerObservation:
    evidence_root = validate_snapshot(snapshot, observation_cut_s=observation_cut_s, head=head)
    return ConsumerObservation(
        observed=True,
        service_active=service_active(snapshot),
        cursor_s=snapshot.cursor_s,
        last_scan_s=snapshot.last_scan_s,
        progress_moved=None,
        lease_current=snapshot.lease_current,
        evidence_root=evidence_root,
    )


def assert_probe_read_only(plan: ProbePlan) -> None:
    forbidden = {"restart", "start", "stop", "kill", "allow", "once", "python", "python3", "curl", "wget"}
    for step in plan.steps:
        if step.effect != "READ_ONLY":
            raise E("NON_READ_ONLY_PROBE_STEP")
        lowered = {part.lower() for part in step.argv}
        if lowered & forbidden:
            raise E("PROBE_CONTAINS_EFFECT_TOKEN")
