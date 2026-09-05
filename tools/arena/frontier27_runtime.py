"""Executable D0 reference implementation of the SOL-AURA1000 top-27 frontier.

This module is deliberately stdlib-only and fail-closed at governed boundaries.
It is a reference runtime, not an effect-authority or physical-performance owner.
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
import json
import re
import time
from typing import Any, Iterable, Mapping, Sequence


def stable(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(v: Any) -> str:
    return sha256(stable(v)).hexdigest()


def tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", s.lower())


def _sha256_text(v: object) -> bool:
    return isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) is not None


class HardFalseSecurityGate:
    @staticmethod
    def admit(*, source_audited: bool, runtime_hard_false: bool, remote_code_widening: bool) -> bool:
        return source_audited and runtime_hard_false and not remote_code_widening


@dataclass(frozen=True)
class IdentityEnvelope:
    model: str
    runtime: str
    source: str
    host: str
    generation: str


class P0IdentityGate:
    @staticmethod
    def admit(expected: IdentityEnvelope, observed: IdentityEnvelope | None) -> bool:
        return observed == expected


@dataclass(frozen=True)
class PerformanceEnvelope:
    device: str
    cache_state: str
    thermal_c: float
    clock_mhz: int


class MatchedEnvelopeGate:
    @staticmethod
    def comparable(a: PerformanceEnvelope, b: PerformanceEnvelope) -> bool:
        return (
            a.device == b.device
            and a.cache_state == b.cache_state
            and abs(a.thermal_c - b.thermal_c) <= 3
            and abs(a.clock_mhz - b.clock_mhz) / max(a.clock_mhz, b.clock_mhz, 1) <= 0.05
        )


class VersionRangeGate:
    @staticmethod
    def _v(s: str) -> tuple[int, int, int]:
        if not isinstance(s, str):
            raise ValueError("version must be text")
        m = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", s)
        if not m:
            raise ValueError(s)
        return tuple(int(x or 0) for x in m.groups())

    @classmethod
    def admit(cls, v: str | None, minimum: str, maximum_exclusive: str) -> bool:
        try:
            return v is not None and cls._v(minimum) <= cls._v(v) < cls._v(maximum_exclusive)
        except (TypeError, ValueError):
            return False


@dataclass(frozen=True)
class CapabilityManifest:
    host_powers: frozenset[str] = frozenset()

    def allows(self, requested: Iterable[str]) -> bool:
        return set(requested) <= self.host_powers


@dataclass(frozen=True)
class ComponentContract:
    name: str
    generation: str
    exports: frozenset[str]
    imports: frozenset[str]
    authority: frozenset[str]


class CompositionMembrane:
    @staticmethod
    def compose(a: ComponentContract, b: ComponentContract, interface: Iterable[str]) -> dict[str, Any]:
        return {
            "interface": tuple(sorted(a.exports & b.imports & set(interface))),
            "authority": tuple(sorted(a.authority & b.authority)),
            "generation_root": digest([a.generation, b.generation]),
        }


@dataclass
class StateHandleLease:
    resource: str
    owner: str
    generation: int
    expires_at: float
    closed: bool = False

    def valid(self, owner: str, generation: int, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return not self.closed and owner == self.owner and generation == self.generation and now <= self.expires_at

    def close(self) -> None:
        self.closed = True


class HardGatePin:
    DEFAULT_REQUIRED = frozenset({"hard", "identity"})

    @staticmethod
    def admit(
        gates: Mapping[str, bool],
        soft_score: float = 0,
        *,
        required: Iterable[str] = DEFAULT_REQUIRED,
    ) -> bool:
        del soft_score
        req = frozenset(required)
        if not req or set(gates) != set(req):
            return False
        return all(type(gates[k]) is bool and gates[k] for k in req)


@dataclass(frozen=True)
class ExportReceipt:
    output_digest: str
    dependency_root: str
    generation: str
    receipt_digest: str

    @classmethod
    def build(cls, payload: Any, deps: Sequence[str], generation: str) -> "ExportReceipt":
        o, d = digest(payload), digest(sorted(deps))
        return cls(o, d, generation, digest([o, d, generation]))

    def verify(self) -> bool:
        return (
            _sha256_text(self.output_digest)
            and _sha256_text(self.dependency_root)
            and bool(self.generation)
            and _sha256_text(self.receipt_digest)
            and self.receipt_digest == digest([self.output_digest, self.dependency_root, self.generation])
        )

    def reusable(self, deps: Sequence[str], generation: str, *, output_digest: str | None = None) -> bool:
        if not self.verify():
            return False
        if output_digest is not None and self.output_digest != output_digest:
            return False
        return self.dependency_root == digest(sorted(deps)) and self.generation == generation


class SnapshotRing:
    def __init__(self, capacity: int = 128):
        self.r = deque(maxlen=capacity)

    def append(self, tick: int, state: Any) -> None:
        self.r.append((tick, digest(state)))

    def __len__(self) -> int:
        return len(self.r)


class CurrentnessInvalidator:
    def __init__(self):
        self.rev: dict[str, set[str]] = defaultdict(set)
        self.node_deps: dict[str, frozenset[str]] = {}
        self.stale: set[str] = set()

    def bind(self, node: str, deps: Iterable[str]) -> None:
        new = frozenset(deps)
        if not node or not new or any(not isinstance(d, str) or not d for d in new):
            raise ValueError("node and non-empty dependency identities required")
        old = self.node_deps.get(node, frozenset())
        for d in old - new:
            self.rev[d].discard(node)
            if not self.rev[d]:
                self.rev.pop(d, None)
        for d in new:
            self.rev[d].add(node)
        self.node_deps[node] = new

    def invalidate(self, deps: Iterable[str]) -> set[str]:
        out: set[str] = set()
        for d in set(deps):
            out.update(self.rev.get(d, set()))
        self.stale.update(out)
        return out

    def complete_reproof(self, node: str, deps: Iterable[str]) -> bool:
        observed = frozenset(deps)
        if self.node_deps.get(node) != observed:
            return False
        self.stale.discard(node)
        return True

    def current(self, node: str) -> bool:
        return node in self.node_deps and node not in self.stale


@dataclass(frozen=True)
class TypedEdge:
    source: str
    relation: str
    target: str
    provenance: str
    generation: int
    current: bool = True


class TypedGraphEdges:
    def __init__(self):
        self.idx = defaultdict(list)

    def add(self, e: TypedEdge) -> None:
        self.idx[(e.source, e.relation)].append(e)

    def lookup(self, s: str, r: str) -> tuple[TypedEdge, ...]:
        return tuple(e for e in self.idx[(s, r)] if e.current)


class CollisionBucket:
    def __init__(self):
        self.b = defaultdict(dict)

    def put(self, k: tuple[int, int, int], identity: str, v: Any) -> None:
        self.b[k][identity] = v

    def get(self, k: tuple[int, int, int], identity: str) -> Any:
        return self.b[k][identity]

    def identities(self, k: tuple[int, int, int]) -> tuple[str, ...]:
        return tuple(sorted(self.b[k]))


class HDCSemanticKey:
    def encode(self, text: str) -> int:
        acc = [0] * 64
        for t in tokens(text):
            h = int.from_bytes(sha256(t.encode()).digest()[:8], "big")
            for i in range(64):
                acc[i] += 1 if h >> i & 1 else -1
        return sum((1 << i) for i, x in enumerate(acc) if x >= 0)

    @staticmethod
    def distance(a: int, b: int) -> int:
        return (a ^ b).bit_count()


class HybridIndexBridge:
    """HDC-prefix candidate routing plus exact lexical backstop."""

    def __init__(self, prefix_bits: int = 10):
        if not 1 <= prefix_bits <= 63:
            raise ValueError("prefix_bits must be in [1, 63]")
        self.p = prefix_bits
        self.h = HDCSemanticKey()
        self.b: dict[int, list[str]] = defaultdict(list)
        self.lex: dict[str, set[str]] = defaultdict(set)
        self.meta: dict[str, tuple[int, tuple[int, int, int]]] = {}

    def add(self, identity: str, text: str, k27: tuple[int, int, int]) -> None:
        if identity in self.meta:
            raise ValueError("duplicate identity")
        k = self.h.encode(text)
        self.meta[identity] = (k, k27)
        self.b[k >> (64 - self.p)].append(identity)
        for term in set(tokens(text)):
            self.lex[term].add(identity)

    def candidates(self, q: str, max_hamming: int = 24):
        k = self.h.encode(q)
        qterms = set(tokens(q))
        if qterms:
            lexical_sets = [self.lex.get(term, set()) for term in qterms]
            lexical = set.intersection(*map(set, lexical_sets)) if lexical_sets else set()
        else:
            lexical = set()
        semantic = set(self.b.get(k >> (64 - self.p), ()))
        pool = lexical | semantic
        out = []
        for identity in pool:
            h, coord = self.meta[identity]
            distance = self.h.distance(k, h)
            if identity in lexical or distance <= max_hamming:
                out.append((identity, coord, distance))
        return tuple(sorted(out, key=lambda x: (x[2], x[0])))


class HotColdCache:
    def __init__(self, cold: Mapping[str, Any], capacity: int = 512):
        self.cold = cold
        self.capacity = capacity
        self.hot = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, k: str) -> Any:
        if k in self.hot:
            self.hits += 1
            v = self.hot.pop(k)
        else:
            self.misses += 1
            v = self.cold[k]
        self.hot[k] = v
        if len(self.hot) > self.capacity:
            self.hot.popitem(last=False)
        return v


@dataclass(frozen=True)
class RetrievalReceipt:
    query_digest: str
    candidates: tuple[str, ...]
    generation: str
    receipt_digest: str

    @classmethod
    def build(cls, q: str, c: Sequence[str], generation: str) -> "RetrievalReceipt":
        qd = digest(q)
        candidates = tuple(c)
        return cls(qd, candidates, generation, digest([qd, list(candidates), generation]))

    def verify(self) -> bool:
        return (
            _sha256_text(self.query_digest)
            and bool(self.generation)
            and _sha256_text(self.receipt_digest)
            and self.receipt_digest == digest([self.query_digest, list(self.candidates), self.generation])
        )

    def valid_for(self, q: str, candidates: Sequence[str], generation: str) -> bool:
        return (
            self.verify()
            and self.query_digest == digest(q)
            and self.candidates == tuple(candidates)
            and self.generation == generation
        )


class PageCacheStateGate:
    @staticmethod
    def classify(s: str | None) -> str:
        return s if s in {"cold", "warm"} else "CALIBRATION_REQUIRED"


class RouterPreservingPrefetch:
    @staticmethod
    def plan(native: Sequence[int], pred: Sequence[int], allowed: Iterable[int]) -> tuple[int, ...]:
        del native
        allowed_set = set(allowed)
        return tuple(dict.fromkeys(x for x in pred if x in allowed_set))


class NativeRouterAuthority:
    @staticmethod
    def execute(native: Sequence[int], prefetched: Iterable[int]) -> tuple[int, ...]:
        del prefetched
        return tuple(native)


class WindowAwareBudget:
    @staticmethod
    def bytes(bandwidth: float, window_s: float, cap: int) -> int:
        return min(cap, max(0, int(bandwidth * window_s)))


class PrefetchWasteGuard:
    @staticmethod
    def admit(useful: int, wasted: int) -> bool:
        return useful > wasted


@dataclass(frozen=True)
class StorageTier:
    name: str
    capacity_bytes: int
    bandwidth: float
    joules_per_gb: float


class TierEnergyAdmission:
    @staticmethod
    def admit(t: StorageTier, n: int, budget_j: float) -> bool:
        return n <= t.capacity_bytes and n / 1e9 * t.joules_per_gb <= budget_j


class StorageTierPlacement:
    @staticmethod
    def choose(tiers: Sequence[StorageTier], n: int, budget_j: float) -> StorageTier | None:
        ok = [t for t in tiers if TierEnergyAdmission.admit(t, n, budget_j)]
        return max(ok, key=lambda t: t.bandwidth) if ok else None


@dataclass
class UsefulByteAccounting:
    useful: int = 0
    wasted: int = 0
    missed: int = 0

    @property
    def total(self) -> int:
        return self.useful + self.wasted + self.missed


class ExpertResidencyLRU:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.r = OrderedDict()
        self.hits = 0
        self.misses = 0

    def access(self, x: int) -> bool:
        hit = x in self.r
        self.hits += hit
        self.misses += not hit
        if hit:
            self.r.move_to_end(x)
        else:
            self.r[x] = None
            if len(self.r) > self.capacity:
                self.r.popitem(last=False)
        return hit

    def resident(self, x: int) -> bool:
        return x in self.r

    def prefetch(self, x: int) -> None:
        if x in self.r:
            self.r.move_to_end(x)
        else:
            self.r[x] = None
            if len(self.r) > self.capacity:
                self.r.popitem(last=False)


class PLEExpertSeparation:
    def __init__(self, expert_capacity: int, ple_capacity: int):
        self.experts = ExpertResidencyLRU(expert_capacity)
        self.ple = OrderedDict()
        self.pc = ple_capacity

    def access(self, kind: str, x: int) -> bool:
        if kind == "expert":
            return self.experts.access(x)
        if kind != "ple":
            raise ValueError(kind)
        hit = x in self.ple
        self.ple[x] = None
        self.ple.move_to_end(x)
        if len(self.ple) > self.pc:
            self.ple.popitem(last=False)
        return hit


FRONTIER_27 = (
    "HardFalseSecurityGate", "HybridIndexBridge", "ExportReceipt", "TypedGraphEdges",
    "NativeRouterAuthority", "RouterPreservingPrefetch", "PageCacheStateGate", "VersionRangeGate",
    "SnapshotRing", "HotColdCache", "StorageTierPlacement", "StateHandleLease", "WindowAwareBudget",
    "PrefetchWasteGuard", "TierEnergyAdmission", "UsefulByteAccounting", "ExpertResidencyLRU",
    "PLEExpertSeparation", "P0IdentityGate", "MatchedEnvelopeGate", "CompositionMembrane", "CollisionBucket",
    "HardGatePin", "CapabilityManifest", "RetrievalReceipt", "CurrentnessInvalidator", "HDCSemanticKey",
)


class LegacyOffload:
    def __init__(self, size: int, bandwidth: float, jpgb: float):
        self.size = size
        self.bw = bandwidth
        self.jpgb = jpgb

    def run(self, routes, preds):
        a = UsefulByteAccounting(); secs = energy = 0.0
        for route, pred in zip(routes, preds):
            n = len(route) * self.size
            a.missed += n; secs += n / self.bw; energy += n / 1e9 * self.jpgb; rs = set(route)
            for x in pred:
                if x in rs: a.useful += self.size
                else: a.wasted += self.size
                secs += self.size / self.bw; energy += self.size / 1e9 * self.jpgb
        return {"bytes": a.total, "seconds": secs, "energy_j": energy, "hit_rate": 0.0}


class FrontierOffload:
    """Conservative serialized model: every actual prefetch/miss transfer counts time."""
    def __init__(self, size: int, capacity: int, tier: StorageTier, window_s: float, budget_j: float):
        self.size = size; self.r = ExpertResidencyLRU(capacity); self.t = tier; self.w = window_s; self.e = budget_j

    def run(self, routes, preds):
        a = UsefulByteAccounting(); secs = energy = 0.0
        for route, pred in zip(routes, preds):
            native = NativeRouterAuthority.execute(route, ())
            budget = WindowAwareBudget.bytes(self.t.bandwidth, self.w, self.size * len(pred))
            plan = RouterPreservingPrefetch.plan(native, pred[: budget // self.size], range(10000))
            rs = set(native); useful = sum(x in rs for x in plan) * self.size; wasted = sum(x not in rs for x in plan) * self.size
            if PrefetchWasteGuard.admit(useful, wasted):
                for x in plan:
                    if not self.r.resident(x):
                        self.r.prefetch(x)
                        a.useful += self.size if x in rs else 0; a.wasted += self.size if x not in rs else 0
                        secs += self.size / self.t.bandwidth; energy += self.size / 1e9 * self.t.joules_per_gb
            for x in native:
                if not self.r.access(x):
                    a.missed += self.size; secs += self.size / self.t.bandwidth; energy += self.size / 1e9 * self.t.joules_per_gb
        total = self.r.hits + self.r.misses
        return {"bytes": a.total, "seconds": secs, "energy_j": energy, "hit_rate": self.r.hits / total}


def security_campaign(n: int = 1000) -> dict[str, Any]:
    e = IdentityEnvelope("glm53", "r", "s", "h", "g"); invalid = blocked = 0
    for i in range(n):
        observed = e if i % 7 else IdentityEnvelope("glm53", "r2", "s", "h", "g")
        hard = HardFalseSecurityGate.admit(source_audited=i % 11 != 0, runtime_hard_false=i % 13 != 0, remote_code_widening=i % 17 == 0)
        ident = P0IdentityGate.admit(e, observed)
        invalid += not (hard and ident); blocked += not HardGatePin.admit({"hard": hard, "identity": ident})
    return {"cases": n, "invalid": invalid, "before_false_admits": invalid, "after_blocked": blocked, "false_admission_reduction": blocked / invalid if invalid else 1.0}
