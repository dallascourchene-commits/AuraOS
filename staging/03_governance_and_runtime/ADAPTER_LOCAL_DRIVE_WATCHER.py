"""WO-STAGE-003 — local Aura Drive watcher and fail-closed causal fence.

Watches a locally mounted/synced ``Aura Drive/05_JOURNAL`` tree. For every
observed file/state delta δ, computes a stable delta hash and the consequence
cone W(δ)=Forward(δ)∩Backward(C_o). Affected material consequences stay blocked
until recovery/reproof is explicitly VERIFIED, enforcing R_d ≺ C_d (or a
non-bypassable fence until R_d closes).

This module is local-only. It does not use Google credentials, call remote APIs,
deploy, merge, or promote symbolic/canonical state. Freshness is claimed only
for this observation channel/cursor; provider-wide freshness and failure-domain
independence are not inferred.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import fnmatch, hashlib, json, os
from pathlib import Path
import threading, time
from typing import Any, Callable, Iterable, Mapping, Sequence


def _json(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash(v: Any) -> str:
    return hashlib.sha256(_json(v).encode()).hexdigest()


def _file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


class RecoveryStatus(str, Enum):
    PENDING = "PENDING"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True)
class FileState:
    path: str
    size: int
    mtime_ns: int
    sha256: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "mtime_ns": self.mtime_ns, "sha256": self.sha256}


@dataclass(frozen=True)
class FileDelta:
    kind: str
    path: str
    before: FileState | None
    after: FileState | None
    observed_ns: int
    delta_hash: str

    @classmethod
    def make(cls, kind: str, path: str, before: FileState | None, after: FileState | None) -> "FileDelta":
        observed = time.time_ns()
        basis = {
            "kind": kind,
            "path": path,
            "before": before.as_dict() if before else None,
            "after": after.as_dict() if after else None,
            "observed_ns": observed,
        }
        return cls(kind, path, before, after, observed, _hash(basis))

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "before": self.before.as_dict() if self.before else None,
            "after": self.after.as_dict() if self.after else None,
            "observed_ns": self.observed_ns,
            "delta_hash": self.delta_hash,
        }


class AppendOnlyJSONLedger:
    """Process-local O_APPEND JSONL evidence ledger with a hash chain."""
    ZERO = "0" * 64

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def append(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            index, prev = self._tail()
            base = {"index": index + 1, "kind": kind, "timestamp_ns": time.time_ns(), "prev_hash": prev, "payload": payload}
            row = {**base, "entry_hash": _hash(base)}
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(fd, (_json(row) + "\n").encode())
                os.fsync(fd)
            finally:
                os.close(fd)
            return row

    def _tail(self) -> tuple[int, str]:
        if not self.path.exists() or not self.path.stat().st_size:
            return 0, self.ZERO
        rows = [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]
        return (int(rows[-1]["index"]), str(rows[-1]["entry_hash"])) if rows else (0, self.ZERO)

    def verify(self) -> tuple[bool, str]:
        prev, expected = self.ZERO, 1
        if not self.path.exists():
            return True, "empty"
        for raw in self.path.read_text().splitlines():
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row.get("index") != expected or row.get("prev_hash") != prev:
                return False, f"chain mismatch at {expected}"
            supplied = row.get("entry_hash")
            if supplied != _hash({k: v for k, v in row.items() if k != "entry_hash"}):
                return False, f"hash mismatch at {expected}"
            prev, expected = str(supplied), expected + 1
        return True, f"verified {expected - 1} entries"


class DependencyGraph:
    """Directed dependency graph; edge A->B means a change in A can affect B."""
    def __init__(self, edges: Iterable[tuple[str, str]] = ()):
        self.fwd: dict[str, set[str]] = {}
        self.rev: dict[str, set[str]] = {}
        for a, b in edges:
            self.add(a, b)

    def add(self, a: str, b: str) -> None:
        self.fwd.setdefault(a, set()).add(b); self.fwd.setdefault(b, set())
        self.rev.setdefault(b, set()).add(a); self.rev.setdefault(a, set())

    @staticmethod
    def _reach(seeds: Iterable[str], graph: Mapping[str, set[str]]) -> set[str]:
        todo, seen = list(seeds), set()
        while todo:
            n = todo.pop()
            if n in seen: continue
            seen.add(n); todo.extend(graph.get(n, ()))
        return seen

    def consequence_cone(self, delta_nodes: Iterable[str], consequence_targets: Iterable[str]) -> frozenset[str]:
        """W(δ) = Forward(δ) ∩ Backward(C_o)."""
        return frozenset(self._reach(delta_nodes, self.fwd) & self._reach(consequence_targets, self.rev))


@dataclass(frozen=True)
class PathRule:
    glob: str
    nodes: tuple[str, ...]


class PathNodeResolver:
    def __init__(self, rules: Sequence[PathRule]):
        self.rules = tuple(rules)

    def resolve(self, relative_path: str) -> frozenset[str]:
        out: set[str] = set()
        for rule in self.rules:
            if fnmatch.fnmatch(relative_path, rule.glob):
                out.update(rule.nodes)
        return frozenset(out)


@dataclass
class RecoveryTicket:
    delta_hash: str
    cone: frozenset[str]
    block_all: bool
    status: RecoveryStatus = RecoveryStatus.PENDING
    evidence: Mapping[str, Any] | None = None


class CausalPrecedenceGate:
    """Fail-closed fence: PENDING/FAILED block; only VERIFIED releases."""
    def __init__(self):
        self._tickets: dict[str, RecoveryTicket] = {}
        self._cv = threading.Condition(threading.RLock())

    def register(self, delta_hash: str, cone: Iterable[str], *, block_all: bool = False) -> RecoveryTicket:
        with self._cv:
            t = self._tickets.get(delta_hash)
            if t is None:
                t = RecoveryTicket(delta_hash, frozenset(cone), bool(block_all))
                self._tickets[delta_hash] = t
            return t

    def verify(self, delta_hash: str, evidence: Mapping[str, Any] | None = None) -> None:
        with self._cv:
            t = self._tickets[delta_hash]
            t.status, t.evidence = RecoveryStatus.VERIFIED, evidence
            self._cv.notify_all()

    def fail(self, delta_hash: str, evidence: Mapping[str, Any] | None = None) -> None:
        with self._cv:
            t = self._tickets[delta_hash]
            t.status, t.evidence = RecoveryStatus.FAILED, evidence
            self._cv.notify_all()

    def blockers(self, consequence: str) -> tuple[RecoveryTicket, ...]:
        with self._cv:
            return tuple(t for t in self._tickets.values() if t.status is not RecoveryStatus.VERIFIED and (t.block_all or consequence in t.cone))

    def wait_until_safe(self, consequence: str, timeout: float | None = None) -> None:
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._cv:
            while self.blockers(consequence):
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0: raise TimeoutError(f"consequence fenced: {consequence}")
                    self._cv.wait(remaining)
                else:
                    self._cv.wait()

    @contextmanager
    def consequence_guard(self, consequence: str, timeout: float | None = None):
        self.wait_until_safe(consequence, timeout)
        yield


@dataclass(frozen=True)
class AdapterEvent:
    delta: FileDelta
    mapped_nodes: frozenset[str]
    consequence_cone: frozenset[str]
    recovery_required: bool
    block_all: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "delta": self.delta.as_dict(), "mapped_nodes": sorted(self.mapped_nodes),
            "consequence_cone": sorted(self.consequence_cone), "recovery_required": self.recovery_required,
            "block_all": self.block_all,
        }


class LocalDriveWatcher:
    """Polling adapter for one local journal folder."""
    def __init__(self, journal: str | os.PathLike[str], *, graph: DependencyGraph, resolver: PathNodeResolver,
                 consequence_targets: Iterable[str], ledger: AppendOnlyJSONLedger | None = None,
                 poll_interval: float = 1.0, fail_closed_unknown: bool = True):
        self.journal = Path(journal).expanduser().resolve()
        if not self.journal.is_dir(): raise ValueError(f"missing journal folder: {self.journal}")
        self.graph, self.resolver = graph, resolver
        self.targets = frozenset(consequence_targets)
        if not self.targets: raise ValueError("consequence_targets required")
        self.ledger, self.poll_interval = ledger, float(poll_interval)
        self.fail_closed_unknown = bool(fail_closed_unknown)
        self.gate = CausalPrecedenceGate()
        self._snapshot: dict[str, FileState] | None = None
        self.callbacks: list[Callable[[AdapterEvent], None]] = []

    def _scan(self) -> dict[str, FileState]:
        out: dict[str, FileState] = {}
        for p in sorted(self.journal.rglob("*")):
            if not p.is_file(): continue
            try:
                st = p.stat(); rel = p.relative_to(self.journal).as_posix()
                out[rel] = FileState(rel, st.st_size, st.st_mtime_ns, _file_hash(p))
            except (FileNotFoundError, PermissionError, OSError):
                continue
        return out

    def prime(self) -> None:
        self._snapshot = self._scan()

    def scan_once(self) -> tuple[AdapterEvent, ...]:
        current = self._scan()
        if self._snapshot is None:
            self._snapshot = current; return ()
        previous, self._snapshot = self._snapshot, current
        events: list[AdapterEvent] = []
        for path in sorted(set(previous) | set(current)):
            before, after = previous.get(path), current.get(path)
            if before is None: kind = "CREATED"
            elif after is None: kind = "DELETED"
            elif before.as_dict() != after.as_dict(): kind = "MODIFIED"
            else: continue
            delta = FileDelta.make(kind, path, before, after)
            mapped = self.resolver.resolve(path)
            cone = self.graph.consequence_cone(mapped, self.targets) if mapped else frozenset()
            block_all = not mapped and self.fail_closed_unknown
            required = bool(cone) or block_all
            if required: self.gate.register(delta.delta_hash, cone, block_all=block_all)  # fence first
            event = AdapterEvent(delta, mapped, cone, required, block_all)
            events.append(event)
            if self.ledger: self.ledger.append("drive_delta", event.as_dict())
        for event in events:
            for callback in tuple(self.callbacks): callback(event)
        return tuple(events)

    def verify_recovery(self, delta_hash: str, evidence: Mapping[str, Any] | None = None) -> None:
        self.gate.verify(delta_hash, evidence)
        if self.ledger: self.ledger.append("recovery_verified", {"delta_hash": delta_hash, "evidence": evidence})

    def fail_recovery(self, delta_hash: str, evidence: Mapping[str, Any] | None = None) -> None:
        self.gate.fail(delta_hash, evidence)
        if self.ledger: self.ledger.append("recovery_failed", {"delta_hash": delta_hash, "evidence": evidence})

    def run(self, stop: threading.Event) -> None:
        if self._snapshot is None: self.prime()
        while not stop.wait(self.poll_interval): self.scan_once()


def build_aura_journal_watcher(aura_drive: str | os.PathLike[str], *, graph: DependencyGraph,
                               resolver: PathNodeResolver, consequence_targets: Iterable[str],
                               ledger_path: str | os.PathLike[str] | None = None,
                               poll_interval: float = 1.0) -> LocalDriveWatcher:
    root = Path(aura_drive).expanduser().resolve()
    journal = root / "05_JOURNAL" if root.name == "Aura Drive" else root / "Aura Drive" / "05_JOURNAL"
    ledger = AppendOnlyJSONLedger(ledger_path) if ledger_path else None
    return LocalDriveWatcher(journal, graph=graph, resolver=resolver, consequence_targets=consequence_targets,
                             ledger=ledger, poll_interval=poll_interval, fail_closed_unknown=True)


__all__ = ["AppendOnlyJSONLedger", "DependencyGraph", "PathRule", "PathNodeResolver", "RecoveryStatus",
           "RecoveryTicket", "CausalPrecedenceGate", "FileState", "FileDelta", "AdapterEvent",
           "LocalDriveWatcher", "build_aura_journal_watcher"]
