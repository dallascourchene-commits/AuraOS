from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Iterable, Mapping, Optional, Sequence

HEX = frozenset("0123456789abcdef")

class TransitionDomainError(ValueError):
    pass

class Decision(str, Enum):
    REPROVE_LOCAL_FIRST = "REPROVE_LOCAL_FIRST"
    READJUDICATE_EXTERNAL_AUTH = "READJUDICATE_EXTERNAL_AUTH"
    HOLD_AUTHORITY = "HOLD_AUTHORITY"
    ELIGIBLE_FOR_FRESH_READJUDICATION = "ELIGIBLE_FOR_FRESH_READJUDICATION"

def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX

def canonical_root(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=lambda x: x.value if isinstance(x, Enum) else x.__dict__).encode()).hexdigest()

def exact_nonnegative_int(value: object, name: str = "value") -> int:
    if type(value) is not int or value < 0:
        raise TransitionDomainError(f"{name}: exact nonnegative integer required")
    return value

def finite_positive_duration(value: object, name: str = "duration") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0.0:
        raise TransitionDomainError(f"{name}: finite positive duration required")
    return float(value)

def causal_time_order(*, observed_at_ms: object, issued_at_ms: object, now_ms: object, expires_at_ms: object, max_age_ms: Optional[object] = None) -> bool:
    observed = exact_nonnegative_int(observed_at_ms, "observed_at_ms")
    issued = exact_nonnegative_int(issued_at_ms, "issued_at_ms")
    now = exact_nonnegative_int(now_ms, "now_ms")
    expires = exact_nonnegative_int(expires_at_ms, "expires_at_ms")
    if not (observed <= issued <= now <= expires):
        return False
    if max_age_ms is not None:
        max_age = exact_nonnegative_int(max_age_ms, "max_age_ms")
        if now - observed > max_age:
            return False
    return True

def terminal_transition_allowed(previous: str, new: str, *, terminal_states: Iterable[str] = ("COMPLETED",)) -> bool:
    terminals = frozenset(terminal_states)
    return not (previous in terminals and new != previous)

def compile_reproof_cone(graph: Mapping[str, Sequence[str]], changed: Iterable[str]) -> tuple[str, ...]:
    known = set(graph)
    seeds = set(changed)
    unknown = seeds - known
    if unknown:
        raise TransitionDomainError(f"unknown reproof seed(s): {sorted(unknown)!r}")
    closure = set(seeds)
    frontier = list(sorted(seeds))
    while frontier:
        node = frontier.pop(0)
        for child in graph[node]:
            if child not in known:
                raise TransitionDomainError(f"unknown graph child: {child!r}")
            if child not in closure:
                closure.add(child)
                frontier.append(child)
    return tuple(sorted(closure))

@dataclass(frozen=True)
class ParentReceipt:
    label: str
    generation: str
    receipt_root: str
    def validate(self) -> None:
        if not self.label or not self.generation or not _hex64(self.receipt_root):
            raise TransitionDomainError("PARENT_RECEIPT_INVALID")

@dataclass(frozen=True)
class TransitionDomainSpec:
    semantic_domain_root: str
    semantic_projection_root: str
    transition_schema_root: str
    terminal_states: tuple[str, ...] = ("COMPLETED",)
    def validate(self) -> None:
        for value in (self.semantic_domain_root, self.semantic_projection_root, self.transition_schema_root):
            if not _hex64(value):
                raise TransitionDomainError("TRANSITION_SPEC_ROOT_INVALID")
        if not self.terminal_states or any(not isinstance(x, str) or not x for x in self.terminal_states):
            raise TransitionDomainError("TERMINAL_STATE_SET_INVALID")
    @property
    def spec_root(self) -> str:
        self.validate()
        return canonical_root(self)

@dataclass(frozen=True)
class CrossPlaneBinding:
    generation_parent: ParentReceipt
    semantic_auth_parent: ParentReceipt
    transition_spec_root: str
    def validate(self) -> None:
        self.generation_parent.validate()
        self.semantic_auth_parent.validate()
        if not _hex64(self.transition_spec_root):
            raise TransitionDomainError("CROSS_PLANE_TRANSITION_ROOT_INVALID")
        if self.generation_parent.label == self.semantic_auth_parent.label:
            raise TransitionDomainError("CROSS_PLANE_PARENTS_NOT_DISTINCT")
    @property
    def binding_root(self) -> str:
        self.validate()
        return canonical_root(self)

@dataclass(frozen=True)
class TransitionEvidence:
    generation_current: bool
    semantic_domain_current: bool
    semantic_projection_current: bool
    cross_plane_binding_current: bool
    value_domain_valid: bool
    causal_order_valid: bool
    lifecycle_transition_valid: bool
    external_auth_complete: bool
    evidence_current: bool
    reproducible: bool
    authority_ceiling_intact: bool
    def validate(self) -> None:
        for name, value in self.__dict__.items():
            if type(value) is not bool:
                raise TransitionDomainError(f"{name}: exact bool required")
    @property
    def local_exact(self) -> bool:
        self.validate()
        return all((self.generation_current, self.semantic_domain_current, self.semantic_projection_current, self.cross_plane_binding_current, self.value_domain_valid, self.causal_order_valid, self.lifecycle_transition_valid, self.evidence_current, self.reproducible))

@dataclass(frozen=True)
class Readjudication:
    decision: Decision
    reasons: tuple[str, ...]
    reproof_cone: tuple[str, ...]
    cross_plane_binding_root: str

def readjudicate(*, evidence: TransitionEvidence, binding: CrossPlaneBinding, dependency_graph: Mapping[str, Sequence[str]], changed_dimensions: Iterable[str] = ()) -> Readjudication:
    evidence.validate()
    root = binding.binding_root
    changed = tuple(sorted(set(changed_dimensions)))
    axes = (
        ("generation", evidence.generation_current),
        ("semantic_domain", evidence.semantic_domain_current),
        ("semantic_projection", evidence.semantic_projection_current),
        ("cross_plane_binding", evidence.cross_plane_binding_current),
        ("value_domain", evidence.value_domain_valid),
        ("causal_order", evidence.causal_order_valid),
        ("lifecycle_transition", evidence.lifecycle_transition_valid),
        ("evidence_current", evidence.evidence_current),
        ("reproducible", evidence.reproducible),
    )
    local_failures = tuple(name for name, ok in axes if not ok)
    if local_failures:
        failure_seeds = tuple(x for x in local_failures if x in dependency_graph)
        seeds = tuple(sorted(set(changed).union(failure_seeds)))
        cone = compile_reproof_cone(dependency_graph, seeds) if seeds else ()
        return Readjudication(Decision.REPROVE_LOCAL_FIRST, local_failures, cone, root)
    if not evidence.external_auth_complete:
        return Readjudication(Decision.READJUDICATE_EXTERNAL_AUTH, ("external_auth_incomplete",), (), root)
    if not evidence.authority_ceiling_intact:
        return Readjudication(Decision.HOLD_AUTHORITY, ("authority_ceiling_widened",), (), root)
    return Readjudication(Decision.ELIGIBLE_FOR_FRESH_READJUDICATION, (), (), root)
