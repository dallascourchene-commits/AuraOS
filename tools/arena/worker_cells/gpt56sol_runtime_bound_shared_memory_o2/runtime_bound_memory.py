from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Iterable, Mapping, Sequence
import hashlib, json

SCHEMA = "AURA-RUNTIME-BOUND-MEMORY-ADMISSION-v1"
CLAIM_CEILING = "D0_CONTROL_PLANE_NONPROMOTING"


def hobj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return value == value.lower()
    except ValueError:
        return False


class Disposition(str, Enum):
    ELIGIBLE_FOR_OWNER_REVIEW = "ELIGIBLE_FOR_OWNER_REVIEW"
    REPROVE_SUBJECT_STATE = "REPROVE_SUBJECT_STATE"
    REPROVE_PRODUCER_RUNTIME = "REPROVE_PRODUCER_RUNTIME"
    REPROVE_SEMANTIC = "REPROVE_SEMANTIC"
    QUARANTINE_AUTHORITY = "QUARANTINE_AUTHORITY"
    QUARANTINE_INTEGRITY = "QUARANTINE_INTEGRITY"
    HOLD_CORROBORATION = "HOLD_CORROBORATION"


@dataclass(frozen=True)
class ProducerReceipt:
    parent_pid: int
    worker_pid: int
    start_method: str
    ready: bool
    process_isolated: bool
    nonce_root: str
    factory_root: str
    implementation_generation: str
    runtime_owner_generation: str
    authority_ceiling: str = CLAIM_CEILING

    @property
    def root(self) -> str:
        return hobj({"schema": SCHEMA, "producer": asdict(self)})

    def structurally_valid(self) -> bool:
        return (
            isinstance(self.parent_pid, int) and self.parent_pid > 0
            and isinstance(self.worker_pid, int) and self.worker_pid > 0
            and self.parent_pid != self.worker_pid
            and self.start_method == "spawn"
            and self.ready is True
            and self.process_isolated is True
            and is_sha256(self.nonce_root)
            and is_sha256(self.factory_root)
            and is_sha256(self.implementation_generation)
            and is_sha256(self.runtime_owner_generation)
            and self.authority_ceiling == CLAIM_CEILING
        )


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    payload_hash: str
    lineage_root: str
    source_root: str
    consequence_root: str
    semantic_domain_root: str
    semantic_projection_root: str
    subject_generation: str
    subject_state_root: str
    producer_receipt_root: str
    producer_implementation_generation: str
    producer_owner_generation: str
    dependency_keys: tuple[str, ...]
    memory_class: str = "DECLARATIVE"
    procedure_authority: bool = False
    externally_authenticated: bool = True
    currentness_attested: bool = True
    revoked: bool = False
    authority_ceiling: str = CLAIM_CEILING

    @property
    def identity_root(self) -> str:
        return hobj({"schema": SCHEMA, "memory": asdict(self)})


@dataclass(frozen=True)
class CurrentState:
    semantic_domain_root: str
    semantic_projection_root: str
    subject_generation: str
    subject_state_root: str
    producer_receipt_root: str
    producer_implementation_generation: str
    producer_owner_generation: str
    currentness_generation: str
    external_auth_generation: str


@dataclass(frozen=True)
class Corroborator:
    lineage_root: str
    source_root: str
    consequence_root: str
    authenticated: bool = True
    current: bool = True


@dataclass(frozen=True)
class Decision:
    disposition: Disposition
    reasons: tuple[str, ...]
    memory_identity_root: str
    producer_receipt_root: str
    consequence_root: str
    invalidation_seeds: tuple[str, ...]
    k27: tuple[int, int, int] | None
    claim_ceiling: str = CLAIM_CEILING
    promotion_authorized: bool = False
    gate10: bool = False

    @property
    def receipt_root(self) -> str:
        payload = asdict(self)
        payload["disposition"] = self.disposition.value
        return hobj(payload)


def _bad_memory_shape(m: MemoryRecord) -> list[str]:
    errs: list[str] = []
    roots = (
        m.payload_hash, m.lineage_root, m.source_root, m.consequence_root,
        m.semantic_domain_root, m.semantic_projection_root, m.subject_state_root,
        m.producer_receipt_root, m.producer_implementation_generation,
        m.producer_owner_generation,
    )
    if not m.memory_id or any(not is_sha256(x) for x in roots): errs.append("MALFORMED_IDENTITY")
    if not m.subject_generation: errs.append("MALFORMED_SUBJECT_GENERATION")
    if not m.dependency_keys or len(set(m.dependency_keys)) != len(m.dependency_keys): errs.append("MALFORMED_DEPENDENCY_KEYS")
    if m.memory_class not in {"DECLARATIVE", "PROCEDURAL"}: errs.append("MALFORMED_MEMORY_CLASS")
    if m.authority_ceiling != CLAIM_CEILING: errs.append("AUTHORITY_WIDENED")
    return errs


def distinct_corroboration_count(corroborators: Sequence[Corroborator]) -> int:
    # Credit is on the full independence tuple; same-lineage/source/consequence copies collapse.
    unique = {
        (c.lineage_root, c.source_root, c.consequence_root)
        for c in corroborators if c.authenticated and c.current
    }
    return len(unique)


def k27_from_identity(full_identity_root: str) -> tuple[int, int, int]:
    raw = bytes.fromhex(full_identity_root)
    return tuple(b % 27 for b in raw[:3])  # compact locality only


def admit_memory(
    memory: MemoryRecord,
    producer: ProducerReceipt,
    current: CurrentState,
    corroborators: Sequence[Corroborator] = (),
    require_independent_corroborators: int = 0,
) -> Decision:
    reasons: list[str] = []
    seeds: list[str] = []

    shape = _bad_memory_shape(memory)
    if shape:
        return Decision(Disposition.QUARANTINE_INTEGRITY, tuple(shape), memory.identity_root, producer.root,
                        memory.consequence_root, ("MEMORY_IDENTITY",), None)

    if memory.revoked or not memory.externally_authenticated or not memory.currentness_attested:
        if memory.revoked: reasons.append("MEMORY_REVOKED")
        if not memory.externally_authenticated: reasons.append("EXTERNAL_AUTH_INCOMPLETE")
        if not memory.currentness_attested: reasons.append("CURRENTNESS_UNATTESTED")
        return Decision(Disposition.QUARANTINE_AUTHORITY, tuple(reasons), memory.identity_root, producer.root,
                        memory.consequence_root, ("MEMORY_AUTHORITY",), None)

    if memory.memory_class == "PROCEDURAL" and not memory.procedure_authority:
        return Decision(Disposition.QUARANTINE_AUTHORITY, ("PROCEDURE_AUTHORITY_MISSING",), memory.identity_root,
                        producer.root, memory.consequence_root, ("PROCEDURE_AUTHORITY",), None)

    semantic_mismatch = []
    if memory.semantic_domain_root != current.semantic_domain_root: semantic_mismatch.append("SEMANTIC_DOMAIN_MOVED")
    if memory.semantic_projection_root != current.semantic_projection_root: semantic_mismatch.append("SEMANTIC_PROJECTION_MOVED")
    if semantic_mismatch:
        return Decision(Disposition.REPROVE_SEMANTIC, tuple(semantic_mismatch), memory.identity_root, producer.root,
                        memory.consequence_root, ("SEMANTIC_MEMORY",), None)

    subject_mismatch = []
    if memory.subject_generation != current.subject_generation: subject_mismatch.append("SUBJECT_GENERATION_MOVED")
    if memory.subject_state_root != current.subject_state_root: subject_mismatch.append("SUBJECT_STATE_MOVED")
    if subject_mismatch:
        return Decision(Disposition.REPROVE_SUBJECT_STATE, tuple(subject_mismatch), memory.identity_root, producer.root,
                        memory.consequence_root, ("SUBJECT_STATE",), None)

    producer_mismatch: list[str] = []
    if not producer.structurally_valid(): producer_mismatch.append("PRODUCER_ISOLATION_INVALID")
    if memory.producer_receipt_root != producer.root: producer_mismatch.append("MEMORY_PRODUCER_RECEIPT_MISMATCH")
    if current.producer_receipt_root != producer.root: producer_mismatch.append("CURRENT_PRODUCER_RECEIPT_MISMATCH")
    if memory.producer_implementation_generation != current.producer_implementation_generation: producer_mismatch.append("PRODUCER_IMPLEMENTATION_MOVED")
    if producer.implementation_generation != current.producer_implementation_generation: producer_mismatch.append("PRODUCER_RECEIPT_IMPLEMENTATION_STALE")
    if memory.producer_owner_generation != current.producer_owner_generation: producer_mismatch.append("PRODUCER_OWNER_MOVED")
    if producer.runtime_owner_generation != current.producer_owner_generation: producer_mismatch.append("PRODUCER_RECEIPT_OWNER_STALE")
    if producer_mismatch:
        return Decision(Disposition.REPROVE_PRODUCER_RUNTIME, tuple(producer_mismatch), memory.identity_root, producer.root,
                        memory.consequence_root, ("PRODUCER_RUNTIME",), None)

    if require_independent_corroborators > 0:
        n = distinct_corroboration_count(corroborators)
        if n < require_independent_corroborators:
            return Decision(Disposition.HOLD_CORROBORATION, (f"DISTINCT_CORROBORATION_{n}_LT_{require_independent_corroborators}",),
                            memory.identity_root, producer.root, memory.consequence_root, ("CORROBORATION",), None)

    # Physical locality is derived only after every semantic/currentness/runtime hard gate.
    coord = k27_from_identity(memory.identity_root)
    return Decision(Disposition.ELIGIBLE_FOR_OWNER_REVIEW, ("ALL_HARD_GATES_CURRENT",), memory.identity_root,
                    producer.root, memory.consequence_root, (), coord)


def reverse_dependency_cone(graph: Mapping[str, Iterable[str]], seeds: Iterable[str]) -> tuple[str, ...]:
    # graph maps prerequisite -> direct dependents.
    seen = set(seeds)
    stack = list(seen)
    while stack:
        node = stack.pop()
        for nxt in graph.get(node, ()):  # minimal reverse-reachable closure
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return tuple(sorted(seen))


def route_score(decision: Decision, recompute_cost: int, fanout: int, frequency: int, locality: int) -> int:
    if decision.disposition != Disposition.ELIGIBLE_FOR_OWNER_REVIEW or decision.k27 is None:
        raise ValueError("semantic/currentness/runtime admission must precede K27 route scoring")
    vals = (recompute_cost, fanout, frequency, locality)
    if any(not isinstance(v, int) or v < 0 or v > 10**9 for v in vals):
        raise ValueError("invalid routing signal")
    # Bounded integer score; economics cannot alter semantic disposition.
    return recompute_cost * 5 + fanout * 3 + frequency * 2 + locality
