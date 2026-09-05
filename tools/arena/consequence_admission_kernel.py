from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
from itertools import product
import json
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

SCHEMA = "AURA-CONSEQUENCE-ADMISSION-KERNEL-v1"
GENESIS = "0" * 64
OMEGA8_AXES = (
    "identity_provenance", "temporal_currentness", "jurisdiction_privacy",
    "evidence_plane", "noncompensatory_slice", "composition_interaction",
    "recovery_reentry", "effect_human",
)
ROUTING13_AXES = ("route_a", "route_b", "route_c", "route_d", "route_e")

class AdmissionError(ValueError):
    pass

class AxisState(int, Enum):
    HARD_INVALID = 0
    UNKNOWN = 1
    VERIFIED = 2

class Decision(str, Enum):
    READY_NONAUTHORIZING = "READY_NONAUTHORIZING"
    HOLD_HARD_INVALID = "HOLD_HARD_INVALID"
    HOLD_REQUIRED_UNKNOWN = "HOLD_REQUIRED_UNKNOWN"
    HOLD_STALE_SOURCE = "HOLD_STALE_SOURCE"
    HOLD_MISSING_SOURCE_EXIT = "HOLD_MISSING_SOURCE_EXIT"
    HOLD_AUTHORITY_CEILING = "HOLD_AUTHORITY_CEILING"
    HOLD_DEPENDENCY_DEBT = "HOLD_DEPENDENCY_DEBT"

def _canonical(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_canonical(x) for x in value]
    if isinstance(value, set):
        return sorted(_canonical(x) for x in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise AdmissionError(f"unsupported canonical value: {type(value).__name__}")

def digest(value: Any) -> str:
    raw = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return sha256(raw.encode("ascii")).hexdigest()

@dataclass(frozen=True)
class ConsequenceVector:
    omega8: Tuple[AxisState, ...]
    routing5: Tuple[int, ...] = (0, 0, 0, 0, 0)
    def __post_init__(self) -> None:
        if len(self.omega8) != 8:
            raise AdmissionError("omega8 must have exactly 8 axes")
        if len(self.routing5) != 5 or any(v not in (0, 1, 2) for v in self.routing5):
            raise AdmissionError("routing5 must be five ternary coordinates")
    @property
    def y13(self) -> Tuple[int, ...]:
        return tuple(int(x) for x in self.omega8) + tuple(self.routing5)

@dataclass(frozen=True)
class SourceExit:
    source_id: str
    owner_ref: str
    generation: str
    semantic_root: str
    current: bool = True
    def valid(self) -> bool:
        return all((self.source_id, self.owner_ref, self.generation, self.semantic_root))

@dataclass(frozen=True)
class AdmissionPolicy:
    policy_id: str
    required_verified_axes: Tuple[int, ...]
    dependency_keys: Tuple[str, ...]
    effect_authority_allowed: bool = False
    def __post_init__(self) -> None:
        if not self.policy_id:
            raise AdmissionError("policy_id required")
        if len(set(self.required_verified_axes)) != len(self.required_verified_axes):
            raise AdmissionError("duplicate required axis")
        if any(i < 0 or i >= 8 for i in self.required_verified_axes):
            raise AdmissionError("required axis out of range")

@dataclass(frozen=True)
class AdmissionInput:
    project_id: str
    vector: ConsequenceVector
    policy: AdmissionPolicy
    source_exit: SourceExit | None
    unresolved_dependencies: Tuple[str, ...] = ()
    asks_effect_authority: bool = False
    evidence_refs: Tuple[str, ...] = ()

@dataclass(frozen=True)
class AdmissionReceipt:
    project_id: str
    decision: Decision
    hard_invalid_axes: Tuple[int, ...]
    required_unknown_axes: Tuple[int, ...]
    unpaid_dependencies: Tuple[str, ...]
    source_exit_digest: str | None
    vector_digest: str
    policy_digest: str
    input_digest: str
    scope_bridge_eligible: bool
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False
    @property
    def receipt_digest(self) -> str:
        return digest(asdict(self))

class ConsequenceAdmissionKernel:
    """Fail-closed consequence admission with hard-invalid dominance.

    The first eight axes carry consequence semantics. The trailing five routing
    coordinates never repair a failing first-eight state. READY is nonauthorizing.
    """
    def assess(self, inp: AdmissionInput) -> AdmissionReceipt:
        hard = tuple(i for i, s in enumerate(inp.vector.omega8) if s == AxisState.HARD_INVALID)
        req_unknown = tuple(i for i in inp.policy.required_verified_axes if inp.vector.omega8[i] != AxisState.VERIFIED)
        unpaid = tuple(sorted(set(inp.unresolved_dependencies).intersection(inp.policy.dependency_keys)))
        source_digest = None if inp.source_exit is None else digest(asdict(inp.source_exit))
        if hard:
            decision = Decision.HOLD_HARD_INVALID
        elif req_unknown:
            decision = Decision.HOLD_REQUIRED_UNKNOWN
        elif inp.source_exit is None or not inp.source_exit.valid():
            decision = Decision.HOLD_MISSING_SOURCE_EXIT
        elif not inp.source_exit.current:
            decision = Decision.HOLD_STALE_SOURCE
        elif unpaid:
            decision = Decision.HOLD_DEPENDENCY_DEBT
        elif inp.asks_effect_authority and not inp.policy.effect_authority_allowed:
            decision = Decision.HOLD_AUTHORITY_CEILING
        else:
            decision = Decision.READY_NONAUTHORIZING
        eligible = decision == Decision.READY_NONAUTHORIZING
        body = {
            "project_id": inp.project_id,
            "vector": inp.vector.y13,
            "policy": asdict(inp.policy),
            "source_exit": None if inp.source_exit is None else asdict(inp.source_exit),
            "unresolved_dependencies": inp.unresolved_dependencies,
            "asks_effect_authority": inp.asks_effect_authority,
            "evidence_refs": inp.evidence_refs,
        }
        return AdmissionReceipt(
            project_id=inp.project_id, decision=decision, hard_invalid_axes=hard,
            required_unknown_axes=req_unknown, unpaid_dependencies=unpaid,
            source_exit_digest=source_digest, vector_digest=digest(inp.vector.y13),
            policy_digest=digest(asdict(inp.policy)), input_digest=digest(body),
            scope_bridge_eligible=eligible,
        )

@dataclass(frozen=True)
class AdmissionEvent:
    event_id: str
    sequence: int
    project_id: str
    event_type: str
    receipt_digest: str
    dependency_keys: Tuple[str, ...]
    causal_parent_ids: Tuple[str, ...] = ()
    prev_hash: str = GENESIS
    event_hash: str = ""
    def body(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA, "event_id": self.event_id, "sequence": self.sequence,
            "project_id": self.project_id, "event_type": self.event_type,
            "receipt_digest": self.receipt_digest, "dependency_keys": list(self.dependency_keys),
            "causal_parent_ids": list(self.causal_parent_ids), "prev_hash": self.prev_hash,
        }
    def computed_hash(self) -> str:
        return digest(self.body())
    def sealed(self) -> "AdmissionEvent":
        return AdmissionEvent(**{**self.__dict__, "event_hash": self.computed_hash()})

class ConsequenceEventLedger:
    """Append-only admission/invalidation plane; never an authority owner."""
    def __init__(self) -> None:
        self._events: list[AdmissionEvent] = []
        self._by_id: dict[str, AdmissionEvent] = {}
        self._dep_index: dict[str, set[str]] = {}
        self._latest_receipt: dict[str, AdmissionReceipt] = {}
    @property
    def events(self) -> Tuple[AdmissionEvent, ...]:
        return tuple(self._events)
    def append_receipt(self, receipt: AdmissionReceipt, dependency_keys: Sequence[str], *, event_id: str) -> AdmissionEvent:
        if event_id in self._by_id:
            raise AdmissionError("duplicate event id")
        prev = GENESIS if not self._events else self._events[-1].event_hash
        e = AdmissionEvent(
            event_id=event_id, sequence=len(self._events), project_id=receipt.project_id,
            event_type="ADMIT" if receipt.scope_bridge_eligible else "HOLD",
            receipt_digest=receipt.receipt_digest,
            dependency_keys=tuple(sorted(set(dependency_keys))), prev_hash=prev,
        ).sealed()
        self._events.append(e); self._by_id[e.event_id] = e; self._latest_receipt[receipt.project_id] = receipt
        for key in e.dependency_keys:
            self._dep_index.setdefault(key, set()).add(receipt.project_id)
        return e
    def invalidate(self, dependency_keys: Iterable[str], *, event_id: str) -> Dict[str, Any]:
        if event_id in self._by_id:
            raise AdmissionError("duplicate event id")
        keys = tuple(sorted(set(dependency_keys)))
        affected = sorted({p for k in keys for p in self._dep_index.get(k, set())})
        prev = GENESIS if not self._events else self._events[-1].event_hash
        e = AdmissionEvent(
            event_id=event_id, sequence=len(self._events), project_id="__PORTFOLIO__",
            event_type="INVALIDATE", receipt_digest=digest({"keys": keys, "affected": affected}),
            dependency_keys=keys, prev_hash=prev,
        ).sealed()
        self._events.append(e); self._by_id[e.event_id] = e
        return {"keys": keys, "affected_projects": affected, "count": len(affected), "event_hash": e.event_hash}
    def verify(self) -> Dict[str, Any]:
        errors = []; prev = GENESIS
        for i, e in enumerate(self._events):
            if e.sequence != i: errors.append(f"sequence:{i}")
            if e.prev_hash != prev: errors.append(f"prev:{i}")
            if e.event_hash != e.computed_hash(): errors.append(f"hash:{i}")
            prev = e.event_hash
        return {"ok": not errors, "errors": errors, "count": len(self._events), "root": digest([e.event_hash for e in self._events])}

@dataclass(frozen=True)
class ReadjudicationEnvelope:
    project_id: str
    consequence_id: str
    policy_id: str
    source_exit: SourceExit
    dependency_keys: Tuple[str, ...]
    invalidators: Tuple[str, ...]
    unresolved_scars: Tuple[str, ...]
    predecessor_receipt_digest: str
    inherited_truth: bool = False
    inherited_authority: bool = False
    def validate(self) -> None:
        if self.inherited_truth or self.inherited_authority:
            raise AdmissionError("succession transfers reproof duties, not truth/authority")
        if not self.source_exit.valid():
            raise AdmissionError("current-source exit required")
        if not self.consequence_id or not self.policy_id:
            raise AdmissionError("consequence/policy identity required")
    @property
    def envelope_digest(self) -> str:
        self.validate(); return digest(asdict(self))

PROJECT_POLICIES: Dict[str, AdmissionPolicy] = {
    "BUGHOUND_O12": AdmissionPolicy("bughound-hardness-v1", (0, 1, 3, 4, 7), ("benchmark_root", "historical_cut", "hardness_policy")),
    "AWJ032_R2": AdmissionPolicy("awj032-owner-host-p0-r2", (0, 1, 3, 4, 7), ("pr311_head", "owner_host_runtime", "mtp_source", "qwen_q14")),
    "AURAOS_796": AdmissionPolicy("auraos796-reference-kernel", (0, 1, 3, 4, 7), ("semantic_root", "provider_head", "canonical_owner")),
    "COUNCIL_V3": AdmissionPolicy("council-v3-disposition", (0, 1, 3, 4, 7), ("seat_evidence", "dissent", "owner_disposition")),
    "O4_FRONTIER": AdmissionPolicy("o4-noncompensatory-frontier", (0, 1, 3, 4, 7), ("semantic_cut", "proof_generation", "scope_lift_gate")),
}

def exhaustive_omega8(policy: AdmissionPolicy) -> Dict[str, int]:
    kernel = ConsequenceAdmissionKernel(); src = SourceExit("src", "owner", "g", "s", True)
    counts = {d.value: 0 for d in Decision}
    for raw in product((0, 1, 2), repeat=8):
        r = kernel.assess(AdmissionInput("X", ConsequenceVector(tuple(AxisState(v) for v in raw)), policy, src))
        counts[r.decision.value] += 1
    return counts
