"""D0 process-isolation canary for a non-returning caller iterator.

This is deliberately a canary, not a production sandbox. It proves that one
direct worker process can be allowed to finish startup, signal READY, and then
be bounded by a parent-owned execution deadline while reusing R10.2's materializer.
It does not prove descendant-process-tree containment or external-effect rollback.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import multiprocessing as mp
import time
from typing import Final

from tools.arena.worker_cells.gpt56sol_frontier27_numeric_preflight.transactional_preflight import _freeze_records

SCENARIOS: Final = frozenset({"finite", "ordinary_reject", "non_returning_next"})
FINAL_KINDS: Final = frozenset({"COMPLETED", "GOVERNED_REJECT", "UNCONTROLLED_CHILD_EXCEPTION"})


class _RaisesOnNext:
    def __init__(self) -> None:
        self.used = False
    def __iter__(self): return self
    def __next__(self):
        if not self.used:
            self.used = True
            return (1,)
        raise RuntimeError("caller-controlled next failure")


class _NeverReturnsNext:
    def __iter__(self): return self
    def __next__(self):
        while True:
            time.sleep(60.0)


def _stable(v: object) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(v: object) -> str:
    return sha256(_stable(v)).hexdigest()


def _child_entry(send_conn, scenario: str) -> None:
    """Initialize, signal READY, then run one fixed side-effect-free scenario."""
    try:
        send_conn.send({"kind": "READY"})
        if scenario == "finite":
            routes, preds = _freeze_records([(1, 2), (3,)], [(1,), (3, 4)], max_records=8, max_items_per_record=8)
            send_conn.send({"kind": "COMPLETED", "payload_root": _digest([routes, preds]), "records": len(routes)})
            return
        if scenario == "ordinary_reject":
            try:
                _freeze_records(_RaisesOnNext(), [(1,)], max_records=8, max_items_per_record=8)
            except ValueError as exc:
                send_conn.send({"kind": "GOVERNED_REJECT", "error_type": type(exc).__name__})
                return
            send_conn.send({"kind": "UNCONTROLLED_CHILD_EXCEPTION", "error_type": "false_accept"})
            return
        if scenario == "non_returning_next":
            _freeze_records(_NeverReturnsNext(), [], max_records=8, max_items_per_record=8)
            send_conn.send({"kind": "UNCONTROLLED_CHILD_EXCEPTION", "error_type": "unexpected_return"})
            return
        send_conn.send({"kind": "UNCONTROLLED_CHILD_EXCEPTION", "error_type": "unknown_scenario"})
    except Exception as exc:
        try:
            send_conn.send({"kind": "UNCONTROLLED_CHILD_EXCEPTION", "error_type": type(exc).__name__})
        except Exception:
            pass
    finally:
        send_conn.close()


@dataclass(frozen=True)
class WatchdogReceipt:
    scenario: str
    disposition: str
    ready_observed: bool
    worker_exitcode: int | None
    payload_root: str | None = None
    records: int | None = None
    error_type: str | None = None

    def stable_evidence(self) -> dict[str, object]:
        return {
            "scenario": self.scenario,
            "disposition": self.disposition,
            "ready_observed": self.ready_observed,
            "payload_root": self.payload_root,
            "records": self.records,
            "error_type": self.error_type,
        }


def _terminate_and_reap(worker, cleanup_grace_s: float, *, prefix: str) -> str:
    worker.terminate()
    worker.join(cleanup_grace_s)
    disposition = f"{prefix}_TERMINATED"
    if worker.is_alive():
        kill = getattr(worker, "kill", None)
        if kill is None:
            raise RuntimeError("worker survived terminate and kill is unavailable")
        kill()
        worker.join(cleanup_grace_s)
        disposition = f"{prefix}_KILLED"
    if worker.is_alive() or worker.exitcode is None:
        raise RuntimeError("watchdog failed to reap worker")
    return disposition


def run_watchdog_canary(
    scenario: str,
    *,
    startup_deadline_s: float = 1.0,
    execution_deadline_s: float = 0.75,
    cleanup_grace_s: float = 0.25,
    start_method: str = "spawn",
) -> WatchdogReceipt:
    """Run one direct child with distinct startup and post-READY deadlines."""
    if scenario not in SCENARIOS:
        raise ValueError("unknown watchdog scenario")
    for name, value in (
        ("startup_deadline_s", startup_deadline_s),
        ("execution_deadline_s", execution_deadline_s),
        ("cleanup_grace_s", cleanup_grace_s),
    ):
        if type(value) is not float or not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be a finite positive float")
    if start_method not in mp.get_all_start_methods():
        raise ValueError("unsupported multiprocessing start method")

    ctx = mp.get_context(start_method)
    recv_conn, send_conn = ctx.Pipe(duplex=False)
    worker = ctx.Process(target=_child_entry, args=(send_conn, scenario), daemon=False)
    worker.start()
    send_conn.close()
    ready_observed = False
    try:
        if not recv_conn.poll(startup_deadline_s):
            if worker.is_alive():
                disposition = _terminate_and_reap(worker, cleanup_grace_s, prefix="STARTUP_TIMEOUT")
                return WatchdogReceipt(scenario, disposition, False, worker.exitcode)
            worker.join(cleanup_grace_s)
            return WatchdogReceipt(scenario, "WORKER_EXITED_BEFORE_READY", False, worker.exitcode)

        ready = recv_conn.recv()
        if not isinstance(ready, dict) or ready.get("kind") != "READY":
            if worker.is_alive():
                disposition = _terminate_and_reap(worker, cleanup_grace_s, prefix="INVALID_READY")
                return WatchdogReceipt(scenario, disposition, False, worker.exitcode, error_type="invalid_ready")
            return WatchdogReceipt(scenario, "INVALID_READY_RECEIPT", False, worker.exitcode, error_type="invalid_ready")
        ready_observed = True

        worker.join(execution_deadline_s)
        if worker.is_alive():
            disposition = _terminate_and_reap(worker, cleanup_grace_s, prefix="EXECUTION_TIMEOUT")
            return WatchdogReceipt(scenario, disposition, True, worker.exitcode)

        message = recv_conn.recv() if recv_conn.poll() else None
        if message is None:
            return WatchdogReceipt(scenario, "WORKER_EXITED_NO_FINAL_RECEIPT", True, worker.exitcode)
        if not isinstance(message, dict) or message.get("kind") not in FINAL_KINDS:
            return WatchdogReceipt(scenario, "UNCONTROLLED_CHILD_EXCEPTION", True, worker.exitcode, error_type="invalid_final_receipt")
        return WatchdogReceipt(
            scenario=scenario,
            disposition=message["kind"],
            ready_observed=True,
            worker_exitcode=worker.exitcode,
            payload_root=message.get("payload_root"),
            records=message.get("records"),
            error_type=message.get("error_type"),
        )
    finally:
        recv_conn.close()
        if worker.is_alive():
            _terminate_and_reap(worker, cleanup_grace_s, prefix="FINALIZER")
