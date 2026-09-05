from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Iterable, Sequence

SCHEMA = "AURA-FUSED-ROUTE-EVENT-CONTRACT-v1"
RECEIPT_SCHEMA = "AURA-FUSED-ROUTE-EVENT-REPLAY-RECEIPT-v1"


class FusedRouteError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FusedRouteError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class FusedRouteEvent:
    sequence: int
    token: int
    layer: int
    native_experts: tuple[int, ...]

    def validate(self, *, experts_per_layer: int, top_k: int) -> None:
        if type(self.sequence) is not int or self.sequence <= 0:
            raise FusedRouteError("INVALID_EVENT_SEQUENCE")
        if type(self.token) is not int or self.token < 0:
            raise FusedRouteError("INVALID_TOKEN")
        if type(self.layer) is not int or self.layer < 0:
            raise FusedRouteError("INVALID_LAYER")
        if not isinstance(self.native_experts, tuple) or len(self.native_experts) != top_k:
            raise FusedRouteError("INVALID_TOPK_MEMBERSHIP")
        if len(set(self.native_experts)) != len(self.native_experts):
            raise FusedRouteError("DUPLICATE_NATIVE_EXPERT")
        if any(type(x) is not int or x < 0 or x >= experts_per_layer for x in self.native_experts):
            raise FusedRouteError("NATIVE_EXPERT_OUT_OF_RANGE")

    def canonical(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "token": self.token,
            "layer": self.layer,
            "native_experts": list(self.native_experts),
        }


@dataclass(frozen=True)
class FlatExpertAccess:
    event_sequence: int
    member_index: int
    group_size: int
    token: int
    layer: int
    expert: int

    def canonical(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class AtomicTrace:
    events: tuple[FusedRouteEvent, ...]
    tokens: int
    layers: int
    experts_per_layer: int
    top_k: int

    def validate(self) -> None:
        for name, value in (
            ("tokens", self.tokens),
            ("layers", self.layers),
            ("experts_per_layer", self.experts_per_layer),
            ("top_k", self.top_k),
        ):
            if type(value) is not int or value <= 0:
                raise FusedRouteError(f"INVALID_{name.upper()}")
        if self.top_k > self.experts_per_layer:
            raise FusedRouteError("TOPK_EXCEEDS_EXPERTS")
        expected = self.tokens * self.layers
        if len(self.events) != expected:
            raise FusedRouteError("INCOMPLETE_EVENT_GRID")
        for idx, event in enumerate(self.events, start=1):
            event.validate(experts_per_layer=self.experts_per_layer, top_k=self.top_k)
            if event.sequence != idx:
                raise FusedRouteError("NON_CONTIGUOUS_EVENT_SEQUENCE")
            expected_token = (idx - 1) // self.layers
            expected_layer = (idx - 1) % self.layers
            if (event.token, event.layer) != (expected_token, expected_layer):
                raise FusedRouteError("NON_CANONICAL_TOKEN_LAYER_GRID")

    @property
    def root(self) -> str:
        self.validate()
        return digest({
            "schema": SCHEMA,
            "tokens": self.tokens,
            "layers": self.layers,
            "experts_per_layer": self.experts_per_layer,
            "top_k": self.top_k,
            "events": [e.canonical() for e in self.events],
        })


@dataclass(frozen=True)
class ReplayReceipt:
    schema: str
    state: str
    original_event_root: str
    flat_access_root: str
    reconstructed_event_root: str
    fused_event_count: int
    flat_access_count: int
    atomic_semantics_preserved: bool
    effect_authority: bool = False
    gate10: bool = False

    @property
    def root(self) -> str:
        return digest(asdict(self))


def flatten_atomic_trace(trace: AtomicTrace) -> tuple[FlatExpertAccess, ...]:
    trace.validate()
    out: list[FlatExpertAccess] = []
    for event in trace.events:
        for member_index, expert in enumerate(event.native_experts):
            out.append(FlatExpertAccess(
                event_sequence=event.sequence,
                member_index=member_index,
                group_size=trace.top_k,
                token=event.token,
                layer=event.layer,
                expert=expert,
            ))
    return tuple(out)


def flat_access_root(accesses: Sequence[FlatExpertAccess]) -> str:
    if not accesses:
        raise FusedRouteError("EMPTY_FLAT_ACCESS_STREAM")
    return digest([a.canonical() for a in accesses])


def reconstruct_atomic_trace(
    accesses: Sequence[FlatExpertAccess],
    *,
    tokens: int,
    layers: int,
    experts_per_layer: int,
    top_k: int,
) -> AtomicTrace:
    if not accesses:
        raise FusedRouteError("EMPTY_FLAT_ACCESS_STREAM")
    expected_accesses = tokens * layers * top_k
    if len(accesses) != expected_accesses:
        raise FusedRouteError("INCOMPLETE_FLAT_ACCESS_STREAM")

    events: list[FusedRouteEvent] = []
    cursor = 0
    for event_sequence in range(1, tokens * layers + 1):
        group = accesses[cursor: cursor + top_k]
        if len(group) != top_k:
            raise FusedRouteError("TRUNCATED_EVENT_GROUP")
        expected_token = (event_sequence - 1) // layers
        expected_layer = (event_sequence - 1) % layers
        experts: list[int] = []
        for member_index, access in enumerate(group):
            if type(access) is not FlatExpertAccess:
                raise FusedRouteError("INVALID_ACCESS_TYPE")
            if access.event_sequence != event_sequence:
                raise FusedRouteError("EVENT_GROUP_BOUNDARY_LOST")
            if access.member_index != member_index:
                raise FusedRouteError("MEMBER_ORDER_LOST")
            if access.group_size != top_k:
                raise FusedRouteError("GROUP_SIZE_MISMATCH")
            if (access.token, access.layer) != (expected_token, expected_layer):
                raise FusedRouteError("TOKEN_LAYER_GROUP_MISMATCH")
            experts.append(access.expert)
        event = FusedRouteEvent(event_sequence, expected_token, expected_layer, tuple(experts))
        event.validate(experts_per_layer=experts_per_layer, top_k=top_k)
        events.append(event)
        cursor += top_k

    trace = AtomicTrace(tuple(events), tokens, layers, experts_per_layer, top_k)
    trace.validate()
    return trace


def verify_atomic_roundtrip(trace: AtomicTrace, accesses: Sequence[FlatExpertAccess]) -> ReplayReceipt:
    trace.validate()
    original_root = trace.root
    flat_root = flat_access_root(accesses)
    reconstructed = reconstruct_atomic_trace(
        accesses,
        tokens=trace.tokens,
        layers=trace.layers,
        experts_per_layer=trace.experts_per_layer,
        top_k=trace.top_k,
    )
    reconstructed_root = reconstructed.root
    if reconstructed_root != original_root:
        raise FusedRouteError("ATOMIC_REPLAY_ROOT_MISMATCH")
    return ReplayReceipt(
        schema=RECEIPT_SCHEMA,
        state="ATOMIC_ROUTE_REPLAY_VERIFIED_D0",
        original_event_root=original_root,
        flat_access_root=flat_root,
        reconstructed_event_root=reconstructed_root,
        fused_event_count=len(trace.events),
        flat_access_count=len(accesses),
        atomic_semantics_preserved=True,
        effect_authority=False,
        gate10=False,
    )


def naive_expert_only_flatten(trace: AtomicTrace) -> tuple[int, ...]:
    """Deliberately lossy representation used only as a falsifier/control."""
    trace.validate()
    return tuple(expert for event in trace.events for expert in event.native_experts)


def lossy_stream_is_admissible(experts: Sequence[int]) -> bool:
    # An expert-only stream lacks event membership/token/layer/cardinality and can never
    # pay the fused-route replay contract, regardless of length or apparent plausibility.
    _ = experts
    return False


def crystalline_admission(omega8: Sequence[int]) -> bool:
    if len(omega8) != 8 or any(type(v) is not int or v not in (0, 1, 2) for v in omega8):
        raise FusedRouteError("INVALID_OMEGA8")
    if any(v == 0 for v in omega8):
        return False
    return omega8[7] == 1


def generate_trace(*, tokens: int, layers: int, experts_per_layer: int, top_k: int, seed: int = 0) -> AtomicTrace:
    import random
    rng = random.Random(seed)
    events: list[FusedRouteEvent] = []
    sequence = 1
    for token in range(tokens):
        for layer in range(layers):
            experts = tuple(rng.sample(range(experts_per_layer), top_k))
            events.append(FusedRouteEvent(sequence, token, layer, experts))
            sequence += 1
    trace = AtomicTrace(tuple(events), tokens, layers, experts_per_layer, top_k)
    trace.validate()
    return trace
