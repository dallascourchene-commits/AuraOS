from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import multiprocessing as mp
from pathlib import Path
import sys
import threading
import types
from typing import Any, Iterable, Mapping, Sequence


def _stable(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _digest(value: Any) -> str:
    return sha256(_stable(value)).hexdigest()


def _source_digest(source: bytes) -> str:
    return sha256(source).hexdigest()


def _load_owner_module(source: bytes, expected_digest: str, module_name: str):
    observed = _source_digest(source)
    if observed != expected_digest:
        raise RuntimeError("canonical owner source identity mismatch")
    module = types.ModuleType(module_name)
    module.__file__ = f"<{module_name}>"
    module.__package__ = ""
    sys.modules[module_name] = module
    try:
        code = compile(source, module.__file__, "exec")
        exec(code, module.__dict__)
        return module
    except Exception:
        sys.modules.pop(module_name, None)
        raise


def _initial_state(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "size": spec["size"],
        "capacity": spec["capacity"],
        "tier": {
            "name": spec["tier"]["name"],
            "capacity_bytes": spec["tier"]["capacity_bytes"],
            "bandwidth": spec["tier"]["bandwidth"],
            "joules_per_gb": spec["tier"]["joules_per_gb"],
        },
        "window_s": spec["window_s"],
        "budget_j": spec["budget_j"],
        "residency": [],
        "hits": 0,
        "misses": 0,
    }


def _build_owner(module, state: Mapping[str, Any]):
    t = state["tier"]
    tier = module.StorageTier(t["name"], t["capacity_bytes"], t["bandwidth"], t["joules_per_gb"])
    owner = module.FrontierOffload(state["size"], state["capacity"], tier, state["window_s"], state["budget_j"])
    _apply_state(owner, module, state)
    return owner


def _capture_state(owner) -> dict[str, Any]:
    return {
        "size": owner.size,
        "capacity": owner.r.capacity,
        "tier": {
            "name": owner.t.name,
            "capacity_bytes": owner.t.capacity_bytes,
            "bandwidth": owner.t.bandwidth,
            "joules_per_gb": owner.t.joules_per_gb,
        },
        "window_s": owner.w,
        "budget_j": owner.e,
        "residency": list(owner.r.r.keys()),
        "hits": owner.r.hits,
        "misses": owner.r.misses,
    }


def _apply_state(owner, module, state: Mapping[str, Any]) -> None:
    t = state["tier"]
    owner.size = state["size"]
    owner.r.capacity = state["capacity"]
    owner.t = module.StorageTier(t["name"], t["capacity_bytes"], t["bandwidth"], t["joules_per_gb"])
    owner.w = state["window_s"]
    owner.e = state["budget_j"]
    owner.r.r = OrderedDict((int(x), None) for x in state["residency"])
    owner.r.hits = state["hits"]
    owner.r.misses = state["misses"]


@dataclass(frozen=True)
class FrontierSnapshot:
    commit_generation: int
    mutation_epoch: int
    full_state: dict[str, Any]
    full_state_root: str
    owner_source_root: str


@dataclass(frozen=True)
class FrontierCommitReceipt:
    admitted: bool
    reason: str
    commit_generation: int
    mutation_epoch: int
    full_state_root: str
    owner_source_root: str
    result: Any = None


def _snapshot_payload(owner, generation: int, epoch: int, source_root: str) -> dict[str, Any]:
    state = _capture_state(owner)
    return {
        "commit_generation": generation,
        "mutation_epoch": epoch,
        "full_state": state,
        "full_state_root": _digest(state),
        "owner_source_root": source_root,
    }


def _owner_process_main(conn, source: bytes, source_root: str, initial_spec: dict[str, Any]):
    module = _load_owner_module(source, source_root, f"_aura_frontier_owner_{id(conn)}")
    owner = _build_owner(module, _initial_state(initial_spec))
    generation = 0
    epoch = 0
    try:
        while True:
            request = conn.recv()
            op = request.get("op")
            if op == "close":
                conn.send({"ok": True})
                return
            if op == "snapshot":
                conn.send({"ok": True, "snapshot": _snapshot_payload(owner, generation, epoch, source_root)})
                continue
            if op == "run":
                before = _capture_state(owner)
                result = module.FrontierOffload.run(owner, request["routes"], request["preds"])
                after = _capture_state(owner)
                if after != before:
                    epoch += 1
                conn.send({"ok": True, "result": result, "snapshot": _snapshot_payload(owner, generation, epoch, source_root)})
                continue
            if op == "governed_write":
                # Every admitted governed persistent write advances the epoch, even if
                # the final bytes equal the starting bytes.
                _apply_state(owner, module, request["state"])
                epoch += 1
                conn.send({"ok": True, "snapshot": _snapshot_payload(owner, generation, epoch, source_root)})
                continue
            if op == "commit":
                current = _snapshot_payload(owner, generation, epoch, source_root)
                expected = request["expected"]
                if current["owner_source_root"] != expected["owner_source_root"]:
                    conn.send({"ok": True, "receipt": {**current, "admitted": False, "reason": "HOLD_SOURCE_ROOT", "result": None}})
                    continue
                if current["commit_generation"] != expected["commit_generation"]:
                    conn.send({"ok": True, "receipt": {**current, "admitted": False, "reason": "HOLD_COMMIT_GENERATION", "result": None}})
                    continue
                if current["mutation_epoch"] != expected["mutation_epoch"]:
                    conn.send({"ok": True, "receipt": {**current, "admitted": False, "reason": "HOLD_MUTATION_EPOCH", "result": None}})
                    continue
                if current["full_state_root"] != expected["full_state_root"] or current["full_state"] != expected["full_state"]:
                    conn.send({"ok": True, "receipt": {**current, "admitted": False, "reason": "HOLD_FULL_STATE", "result": None}})
                    continue
                _apply_state(owner, module, request["post_state"])
                generation += 1
                epoch += 1
                after = _snapshot_payload(owner, generation, epoch, source_root)
                conn.send({"ok": True, "receipt": {**after, "admitted": True, "reason": "COMMIT", "result": request.get("result")}})
                continue
            conn.send({"ok": False, "error": f"unknown operation: {op}"})
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _transition_worker(conn, source: bytes, source_root: str, snapshot: dict[str, Any], routes, preds):
    try:
        module = _load_owner_module(source, source_root, f"_aura_frontier_transition_{id(conn)}")
        owner = _build_owner(module, snapshot["full_state"])
        result = module.FrontierOffload.run(owner, routes, preds)
        post_state = _capture_state(owner)
        conn.send({
            "ok": True,
            "result": result,
            "post_state": post_state,
            "post_state_root": _digest(post_state),
            "owner_source_root": source_root,
        })
    except Exception as exc:
        conn.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        conn.close()


class FrontierEpochOwnerProcess:
    """Process-owned Frontier state with a monotone lifecycle epoch.

    The raw FrontierOffload object exists only in the child process. Parent callers
    receive snapshots/receipts, never a mutable owner reference.
    """

    __slots__ = ("__source", "__source_root", "__conn", "__process", "__rpc_lock")

    def __init__(self, source: bytes, expected_source_root: str, initial_spec: Mapping[str, Any]):
        observed = _source_digest(source)
        if observed != expected_source_root:
            raise ValueError("owner source root mismatch")
        self.__source = bytes(source)
        self.__source_root = expected_source_root
        ctx = mp.get_context("spawn")
        parent_conn, child_conn = ctx.Pipe()
        process = ctx.Process(
            target=_owner_process_main,
            args=(child_conn, self.__source, self.__source_root, dict(initial_spec)),
            daemon=True,
        )
        process.start()
        child_conn.close()
        self.__conn = parent_conn
        self.__process = process
        self.__rpc_lock = threading.Lock()
        self.snapshot()  # fail-fast boot check

    @classmethod
    def from_canonical_file(cls, path: str | Path, expected_source_root: str, initial_spec: Mapping[str, Any]):
        source = Path(path).read_bytes()
        return cls(source, expected_source_root, initial_spec)

    @property
    def owner_source_root(self) -> str:
        return self.__source_root

    def _rpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.__rpc_lock:
            if not self.__process.is_alive():
                raise RuntimeError("owner process is not alive")
            self.__conn.send(payload)
            reply = self.__conn.recv()
        if not reply.get("ok"):
            raise RuntimeError(reply.get("error", "owner process request failed"))
        return reply

    def snapshot(self) -> FrontierSnapshot:
        s = self._rpc({"op": "snapshot"})["snapshot"]
        return FrontierSnapshot(**s)

    def run(self, routes: Sequence[Sequence[int]], preds: Sequence[Sequence[int]]):
        reply = self._rpc({"op": "run", "routes": [list(x) for x in routes], "preds": [list(x) for x in preds]})
        return reply["result"], FrontierSnapshot(**reply["snapshot"])

    def governed_write(self, state: Mapping[str, Any]) -> FrontierSnapshot:
        reply = self._rpc({"op": "governed_write", "state": json.loads(_stable(state).decode("ascii"))})
        return FrontierSnapshot(**reply["snapshot"])

    def commit(self, expected: FrontierSnapshot, post_state: Mapping[str, Any], result: Any) -> FrontierCommitReceipt:
        reply = self._rpc({
            "op": "commit",
            "expected": asdict(expected),
            "post_state": json.loads(_stable(post_state).decode("ascii")),
            "result": result,
        })["receipt"]
        return FrontierCommitReceipt(
            admitted=reply["admitted"],
            reason=reply["reason"],
            commit_generation=reply["commit_generation"],
            mutation_epoch=reply["mutation_epoch"],
            full_state_root=reply["full_state_root"],
            owner_source_root=reply["owner_source_root"],
            result=reply.get("result"),
        )

    def project_pinned(self, snapshot: FrontierSnapshot, routes, preds) -> tuple[Any, dict[str, Any], str]:
        if snapshot.owner_source_root != self.__source_root:
            raise ValueError("snapshot source root mismatch")
        ctx = mp.get_context("spawn")
        parent_conn, child_conn = ctx.Pipe(False)
        process = ctx.Process(
            target=_transition_worker,
            args=(child_conn, self.__source, self.__source_root, asdict(snapshot), [list(x) for x in routes], [list(x) for x in preds]),
        )
        process.start()
        child_conn.close()
        reply = parent_conn.recv()
        process.join(timeout=30)
        if process.is_alive():
            process.terminate(); process.join(timeout=5)
            raise TimeoutError("pinned transition worker timed out")
        if process.exitcode != 0 or not reply.get("ok"):
            raise RuntimeError(reply.get("error", f"transition worker exit {process.exitcode}"))
        return reply["result"], reply["post_state"], reply["owner_source_root"]

    def transact(self, routes, preds) -> FrontierCommitReceipt:
        snap = self.snapshot()
        result, post_state, source_root = self.project_pinned(snap, routes, preds)
        if source_root != snap.owner_source_root:
            return FrontierCommitReceipt(False, "HOLD_SOURCE_ROOT", snap.commit_generation, snap.mutation_epoch, snap.full_state_root, snap.owner_source_root)
        return self.commit(snap, post_state, result)

    def close(self) -> None:
        process = getattr(self, "_FrontierEpochOwnerProcess__process", None)
        conn = getattr(self, "_FrontierEpochOwnerProcess__conn", None)
        if process is None:
            return
        if process.is_alive():
            try:
                self._rpc({"op": "close"})
            except Exception:
                pass
            process.join(timeout=5)
        if process.is_alive():
            process.terminate(); process.join(timeout=5)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


__all__ = [
    "FrontierSnapshot",
    "FrontierCommitReceipt",
    "FrontierEpochOwnerProcess",
]
