from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Sequence


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


def _finite_nonnegative(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value)) and float(value) >= 0.0


@dataclass(frozen=True, order=True)
class ExpertRef:
    layer: int
    expert: int

    def validate(self, *, layers: int, experts_per_layer: int) -> None:
        if not (0 <= self.layer < layers):
            raise ValueError("expert layer outside envelope")
        if not (0 <= self.expert < experts_per_layer):
            raise ValueError("expert id outside envelope")


@dataclass(frozen=True)
class AccessEvent:
    token: int
    layer: int
    experts: tuple[int, ...]

    def validate(self, *, layers: int, experts_per_layer: int) -> None:
        if self.token < 0 or not (0 <= self.layer < layers) or not self.experts:
            raise ValueError("invalid access event")
        if len(set(self.experts)) != len(self.experts):
            raise ValueError("duplicate expert in one routing event")
        for expert in self.experts:
            ExpertRef(self.layer, expert).validate(layers=layers, experts_per_layer=experts_per_layer)


@dataclass(frozen=True)
class BenchmarkEnvelope:
    device: str
    runtime: str
    source_head: str
    quantization: str
    cache_state: str
    layers: int
    experts_per_layer: int
    cache_capacity_experts: int
    expert_size_bytes: int
    source_bandwidth_bytes_s: float
    joules_per_gb: float

    def validate(self) -> None:
        if not all(isinstance(v, str) and v for v in (self.device, self.runtime, self.source_head, self.quantization)):
            raise ValueError("identity fields must be non-empty strings")
        if self.cache_state not in {"cold", "warm"}:
            raise ValueError("cache_state must be cold or warm")
        for value in (self.layers, self.experts_per_layer, self.cache_capacity_experts, self.expert_size_bytes):
            if type(value) is not int or value <= 0:
                raise ValueError("positive integer envelope field required")
        if self.cache_capacity_experts > self.layers * self.experts_per_layer:
            raise ValueError("cache capacity exceeds expert universe")
        if not _finite_nonnegative(self.source_bandwidth_bytes_s) or self.source_bandwidth_bytes_s <= 0:
            raise ValueError("positive finite source bandwidth required")
        if not _finite_nonnegative(self.joules_per_gb):
            raise ValueError("finite non-negative energy coefficient required")

    @property
    def root(self) -> str:
        self.validate()
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "device": self.device,
            "runtime": self.runtime,
            "source_head": self.source_head,
            "quantization": self.quantization,
            "cache_state": self.cache_state,
            "layers": self.layers,
            "experts_per_layer": self.experts_per_layer,
            "cache_capacity_experts": self.cache_capacity_experts,
            "expert_size_bytes": self.expert_size_bytes,
            "source_bandwidth_bytes_s": self.source_bandwidth_bytes_s,
            "joules_per_gb": self.joules_per_gb,
        }


@dataclass(frozen=True)
class TraceBundle:
    events: tuple[AccessEvent, ...]
    envelope_root: str

    @classmethod
    def build(cls, events: Sequence[AccessEvent], envelope: BenchmarkEnvelope) -> "TraceBundle":
        envelope.validate()
        if not events:
            raise ValueError("non-empty trace required")
        last = (-1, -1)
        frozen: list[AccessEvent] = []
        for event in events:
            event.validate(layers=envelope.layers, experts_per_layer=envelope.experts_per_layer)
            coordinate = (event.token, event.layer)
            if coordinate <= last:
                raise ValueError("trace must be strictly ordered by token/layer")
            last = coordinate
            frozen.append(event)
        return cls(tuple(frozen), envelope.root)

    @property
    def root(self) -> str:
        return _digest({
            "envelope_root": self.envelope_root,
            "events": [{"token": e.token, "layer": e.layer, "experts": list(e.experts)} for e in self.events],
        })


@dataclass(frozen=True)
class PolicyMetrics:
    policy: str
    accesses: int
    hits: int
    misses: int
    evictions: int
    bytes_loaded: int
    transfer_seconds: float
    energy_j: float
    route_root: str

    @property
    def hit_rate(self) -> float:
        return self.hits / self.accesses if self.accesses else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "policy": self.policy,
            "accesses": self.accesses,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "bytes_loaded": self.bytes_loaded,
            "transfer_seconds": self.transfer_seconds,
            "energy_j": self.energy_j,
            "route_root": self.route_root,
        }


class _LRU:
    name = "LRU"

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.resident: OrderedDict[ExpertRef, None] = OrderedDict()
        self.evictions = 0

    def access(self, ref: ExpertRef, current_layer: int, layers: int) -> bool:
        del current_layer, layers
        if ref in self.resident:
            self.resident.move_to_end(ref)
            return True
        if len(self.resident) >= self.capacity:
            self.resident.popitem(last=False)
            self.evictions += 1
        self.resident[ref] = None
        return False


class _LayerCycle:
    """Online layer-order-aware eviction that never predicts or changes router output.

    This is an Aura structure-aware heuristic inspired by anti-temporal-locality
    pressure in SpecMD. It is not claimed to be SpecMD's exact Least-Stale policy.
    """

    name = "LAYER_CYCLE"

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.resident: OrderedDict[ExpertRef, int] = OrderedDict()
        self.clock = 0
        self.evictions = 0

    @staticmethod
    def _distance_until_layer(ref: ExpertRef, current_layer: int, layers: int) -> int:
        distance = (ref.layer - current_layer) % layers
        return layers if distance == 0 else distance

    def access(self, ref: ExpertRef, current_layer: int, layers: int) -> bool:
        self.clock += 1
        if ref in self.resident:
            self.resident[ref] = self.clock
            return True
        if len(self.resident) >= self.capacity:
            victim = max(
                self.resident,
                key=lambda r: (self._distance_until_layer(r, current_layer, layers), -self.resident[r], r.layer, r.expert),
            )
            del self.resident[victim]
            self.evictions += 1
        self.resident[ref] = self.clock
        return False


class _BeladyOracle:
    name = "BELADY_ORACLE"

    def __init__(self, capacity: int, future: dict[ExpertRef, list[int]]):
        self.capacity = capacity
        self.future = future
        self.positions: Counter[ExpertRef] = Counter()
        self.resident: set[ExpertRef] = set()
        self.evictions = 0

    def _next_use(self, ref: ExpertRef) -> int:
        pos = self.positions[ref]
        seq = self.future[ref]
        return seq[pos] if pos < len(seq) else 10**18

    def access(self, ref: ExpertRef, current_layer: int, layers: int) -> bool:
        del current_layer, layers
        hit = ref in self.resident
        if not hit:
            if len(self.resident) >= self.capacity:
                victim = max(self.resident, key=lambda r: (self._next_use(r), r.layer, r.expert))
                self.resident.remove(victim)
                self.evictions += 1
            self.resident.add(ref)
        self.positions[ref] += 1
        return hit


def _flatten(trace: TraceBundle) -> list[tuple[int, ExpertRef]]:
    flat: list[tuple[int, ExpertRef]] = []
    for event in trace.events:
        for expert in event.experts:
            flat.append((event.layer, ExpertRef(event.layer, expert)))
    return flat


def evaluate_policy(trace: TraceBundle, envelope: BenchmarkEnvelope, policy: str) -> PolicyMetrics:
    envelope.validate()
    if trace.envelope_root != envelope.root:
        raise ValueError("trace/envelope identity mismatch")
    flat = _flatten(trace)
    if policy == "LRU":
        impl = _LRU(envelope.cache_capacity_experts)
    elif policy == "LAYER_CYCLE":
        impl = _LayerCycle(envelope.cache_capacity_experts)
    elif policy == "BELADY_ORACLE":
        future: dict[ExpertRef, list[int]] = {}
        for idx, (_, ref) in enumerate(flat):
            future.setdefault(ref, []).append(idx + 1)
        impl = _BeladyOracle(envelope.cache_capacity_experts, future)
    else:
        raise ValueError("unknown policy")

    hits = misses = 0
    route: list[tuple[int, int]] = []
    for layer, ref in flat:
        route.append((ref.layer, ref.expert))
        if impl.access(ref, layer, envelope.layers):
            hits += 1
        else:
            misses += 1
    loaded = misses * envelope.expert_size_bytes
    return PolicyMetrics(
        policy=policy,
        accesses=len(flat),
        hits=hits,
        misses=misses,
        evictions=impl.evictions,
        bytes_loaded=loaded,
        transfer_seconds=loaded / envelope.source_bandwidth_bytes_s,
        energy_j=loaded / 1e9 * envelope.joules_per_gb,
        route_root=_digest(route),
    )


@dataclass(frozen=True)
class Adjudication:
    state: str
    winner: str | None
    lru: PolicyMetrics
    layer_cycle: PolicyMetrics
    oracle: PolicyMetrics
    transfer_time_reduction_vs_lru: float
    oracle_regret_ratio: float
    effect_authority: bool = False
    gate10: bool = False

    @property
    def root(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "winner": self.winner,
            "lru": self.lru.as_dict(),
            "layer_cycle": self.layer_cycle.as_dict(),
            "oracle": self.oracle.as_dict(),
            "transfer_time_reduction_vs_lru": self.transfer_time_reduction_vs_lru,
            "oracle_regret_ratio": self.oracle_regret_ratio,
            "effect_authority": self.effect_authority,
            "gate10": self.gate10,
        }


def adjudicate(trace: TraceBundle, envelope: BenchmarkEnvelope, *, minimum_reduction: float = 0.02, maximum_oracle_regret_ratio: float = 1.20) -> Adjudication:
    if not (_finite_nonnegative(minimum_reduction) and _finite_nonnegative(maximum_oracle_regret_ratio)):
        raise ValueError("finite non-negative thresholds required")
    lru = evaluate_policy(trace, envelope, "LRU")
    layer_cycle = evaluate_policy(trace, envelope, "LAYER_CYCLE")
    oracle = evaluate_policy(trace, envelope, "BELADY_ORACLE")
    if len({lru.route_root, layer_cycle.route_root, oracle.route_root}) != 1:
        raise AssertionError("cache policy changed native router route")
    if oracle.misses > min(lru.misses, layer_cycle.misses):
        raise AssertionError("oracle ceiling violated")

    reduction = 0.0 if lru.transfer_seconds == 0 else (lru.transfer_seconds - layer_cycle.transfer_seconds) / lru.transfer_seconds
    regret = 1.0 if oracle.misses == 0 and layer_cycle.misses == 0 else (float("inf") if oracle.misses == 0 else layer_cycle.misses / oracle.misses)
    if not math.isfinite(regret):
        state, winner = "HOLD_ORACLE_GAP", None
    elif reduction >= minimum_reduction and regret <= maximum_oracle_regret_ratio:
        state, winner = "CANDIDATE_LAYER_CYCLE", "LAYER_CYCLE"
    elif reduction <= -minimum_reduction:
        state, winner = "CANDIDATE_LRU", "LRU"
    else:
        state, winner = "NO_MATERIAL_POLICY_ADVANTAGE", None
    return Adjudication(state, winner, lru, layer_cycle, oracle, reduction, regret)


@dataclass(frozen=True)
class BenchmarkReceipt:
    trace_root: str
    envelope_root: str
    adjudication_root: str
    source_head: str
    receipt_digest: str

    @classmethod
    def build(cls, trace: TraceBundle, envelope: BenchmarkEnvelope, result: Adjudication) -> "BenchmarkReceipt":
        payload = [trace.root, envelope.root, result.root, envelope.source_head]
        return cls(*payload, _digest(payload))

    def verify(self, trace: TraceBundle, envelope: BenchmarkEnvelope, result: Adjudication) -> bool:
        try:
            payload = [trace.root, envelope.root, result.root, envelope.source_head]
            return (
                self.trace_root == payload[0]
                and self.envelope_root == payload[1]
                and self.adjudication_root == payload[2]
                and self.source_head == payload[3]
                and self.receipt_digest == _digest(payload)
            )
        except (TypeError, ValueError):
            return False


def generate_trace(*, regime: str, seed: int, tokens: int, layers: int, experts_per_layer: int, topk: int) -> tuple[AccessEvent, ...]:
    import random

    if regime not in {"layer_cyclic", "temporal_hot", "uniform"}:
        raise ValueError("unknown regime")
    if min(tokens, layers, experts_per_layer, topk) <= 0 or topk > experts_per_layer:
        raise ValueError("invalid trace dimensions")
    rng = random.Random(seed)
    events: list[AccessEvent] = []
    hot = max(topk, min(experts_per_layer, max(topk + 1, experts_per_layer // 4)))
    prior: dict[int, tuple[int, ...]] = {}
    for token in range(tokens):
        for layer in range(layers):
            if regime == "layer_cyclic":
                base = (token * topk + layer * 3) % experts_per_layer
                experts = tuple((base + offset) % experts_per_layer for offset in range(topk))
            elif regime == "temporal_hot":
                if layer in prior and rng.random() < 0.85:
                    experts = prior[layer]
                else:
                    experts = tuple(sorted(rng.sample(range(hot), topk)))
                prior[layer] = experts
            else:
                experts = tuple(sorted(rng.sample(range(experts_per_layer), topk)))
            events.append(AccessEvent(token, layer, experts))
    return tuple(events)


def hyperscale_campaign(cases: int = 1000) -> dict[str, object]:
    if cases <= 0:
        raise ValueError("positive cases required")
    states = Counter()
    winners = Counter()
    receipt_failures = oracle_violations = authority_violations = 0
    roots: list[str] = []
    regimes = ("layer_cyclic", "temporal_hot", "uniform")
    for case in range(cases):
        envelope = BenchmarkEnvelope(
            device="synthetic-device",
            runtime="arena-cache-policy-v1",
            source_head="7a2c7a16f845752ffb7c16c68636d8d542ecd72e",
            quantization="synthetic-q4",
            cache_state="warm" if case % 2 else "cold",
            layers=8,
            experts_per_layer=16,
            cache_capacity_experts=8 + (case % 9),
            expert_size_bytes=2 * 1024 * 1024,
            source_bandwidth_bytes_s=1.2e9,
            joules_per_gb=2.4,
        )
        trace = TraceBundle.build(generate_trace(regime=regimes[case % 3], seed=910000 + case, tokens=8, layers=8, experts_per_layer=16, topk=2), envelope)
        result = adjudicate(trace, envelope)
        receipt = BenchmarkReceipt.build(trace, envelope, result)
        receipt_failures += not receipt.verify(trace, envelope, result)
        oracle_violations += result.oracle.misses > min(result.lru.misses, result.layer_cycle.misses)
        authority_violations += bool(result.effect_authority or result.gate10)
        states[result.state] += 1
        winners[str(result.winner)] += 1
        roots.append(receipt.receipt_digest)
    return {
        "cases": cases,
        "states": dict(sorted(states.items())),
        "winners": dict(sorted(winners.items())),
        "receipt_failures": receipt_failures,
        "oracle_violations": oracle_violations,
        "authority_violations": authority_violations,
        "campaign_root": _digest(roots),
    }
