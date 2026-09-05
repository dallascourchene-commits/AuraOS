"""Proof-bound reuse and selective reproof closure for Aura Arena.

D0/nonpromoting reference controller. Reuse requires exact identity/currentness,
dependency generation, required-step closure, and receipt integrity. It never grants
effect authority or Gate10.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Sequence


def stable(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def digest(v: Any) -> str:
    return sha256(stable(v)).hexdigest()

@dataclass(frozen=True)
class ProofIdentity:
    project_id: str
    source_head: str
    workflow_generation: str
    input_root: str
    required_steps_root: str
    dependency_root: str
    binding_generation: int

    @property
    def identity_digest(self) -> str:
        return digest([
            self.project_id, self.source_head, self.workflow_generation,
            self.input_root, self.required_steps_root, self.dependency_root,
            self.binding_generation,
        ])

@dataclass(frozen=True)
class ProofReceipt:
    identity_digest: str
    result_root: str
    completed_steps_root: str
    effect_authority: bool
    gate10: bool
    receipt_digest: str

    @classmethod
    def build(cls, identity: ProofIdentity, result: Any, completed_steps: Sequence[str]) -> "ProofReceipt":
        completed_root = digest(sorted(completed_steps)); result_root = digest(result)
        body = [identity.identity_digest, result_root, completed_root, False, False]
        return cls(identity.identity_digest, result_root, completed_root, False, False, digest(body))

    def validate(self, identity: ProofIdentity, result: Any, completed_steps: Sequence[str]) -> bool:
        completed_root = digest(sorted(completed_steps)); result_root = digest(result)
        body = [identity.identity_digest, result_root, completed_root, False, False]
        return (
            self.identity_digest == identity.identity_digest
            and self.result_root == result_root
            and self.completed_steps_root == completed_root
            and self.effect_authority is False
            and self.gate10 is False
            and self.receipt_digest == digest(body)
        )

@dataclass(frozen=True)
class ProjectBinding:
    project_id: str
    dependencies: frozenset[str]
    required_steps: tuple[str, ...]
    binding_generation: int

@dataclass(frozen=True)
class CurrentContext:
    source_head: str
    workflow_generation: str
    input_root: str

class ProofBoundReuseLedger:
    def __init__(self) -> None:
        self.bindings: dict[str, ProjectBinding] = {}
        self.reverse: dict[str, set[str]] = {}
        self.contexts: dict[str, CurrentContext] = {}
        self.expected: dict[str, ProofIdentity] = {}
        self.stale: set[str] = set()
        self.receipts: dict[str, tuple[ProofIdentity, ProofReceipt, Any, tuple[str, ...]]] = {}

    def _rebuild_expected(self, project_id: str) -> ProofIdentity | None:
        b = self.bindings.get(project_id); c = self.contexts.get(project_id)
        if b is None or c is None: return None
        i = ProofIdentity(
            project_id=project_id,
            source_head=c.source_head,
            workflow_generation=c.workflow_generation,
            input_root=c.input_root,
            required_steps_root=digest(list(b.required_steps)),
            dependency_root=digest(sorted(b.dependencies)),
            binding_generation=b.binding_generation,
        )
        self.expected[project_id] = i
        return i

    def bind(self, project_id: str, dependencies: Iterable[str], required_steps: Iterable[str]) -> ProjectBinding:
        deps = frozenset(dependencies); steps = tuple(sorted(set(required_steps)))
        if not project_id or not deps or not steps or any(not x for x in deps) or any(not x for x in steps):
            raise ValueError("project, dependencies, and required steps must be non-empty")
        old = self.bindings.get(project_id); generation = 1 if old is None else old.binding_generation + 1
        if old:
            for dep in old.dependencies - deps:
                bucket = self.reverse.get(dep)
                if bucket:
                    bucket.discard(project_id)
                    if not bucket: self.reverse.pop(dep, None)
        for dep in deps: self.reverse.setdefault(dep, set()).add(project_id)
        b = ProjectBinding(project_id, deps, steps, generation); self.bindings[project_id] = b
        if old is not None: self.stale.add(project_id)
        self._rebuild_expected(project_id)
        return b

    def set_current_context(self, project_id: str, *, source_head: str, workflow_generation: str, input_payload: Any) -> ProofIdentity:
        if project_id not in self.bindings: raise KeyError(project_id)
        if not source_head or not workflow_generation: raise ValueError("current source/workflow identities required")
        c = CurrentContext(source_head, workflow_generation, digest(input_payload)); old = self.contexts.get(project_id)
        self.contexts[project_id] = c
        if old is not None and old != c: self.stale.add(project_id)
        return self._rebuild_expected(project_id)  # type: ignore[return-value]

    def current_identity(self, project_id: str) -> ProofIdentity:
        i = self.expected.get(project_id)
        if i is None: raise KeyError(project_id)
        return i

    def invalidate(self, dependencies: Iterable[str]) -> set[str]:
        affected: set[str] = set()
        for dep in set(dependencies): affected.update(self.reverse.get(dep, set()))
        self.stale.update(affected)
        return affected

    def admit_fresh_proof(self, identity: ProofIdentity, result: Any, completed_steps: Sequence[str], receipt: ProofReceipt) -> bool:
        b = self.bindings.get(identity.project_id); expected = self.expected.get(identity.project_id)
        if b is None or expected is None or identity != expected: return False
        if tuple(sorted(set(completed_steps))) != b.required_steps: return False
        if not receipt.validate(identity, result, completed_steps): return False
        self.receipts[identity.project_id] = (identity, receipt, result, tuple(completed_steps))
        self.stale.discard(identity.project_id)
        return True

    def reusable(self, project_id: str) -> bool:
        if project_id in self.stale: return False
        expected = self.expected.get(project_id); stored = self.receipts.get(project_id)
        if expected is None or stored is None: return False
        prior_identity, receipt, result, steps = stored
        if prior_identity != expected: return False
        return receipt.validate(expected, result, steps)

    def reusable_result(self, project_id: str) -> Any:
        if not self.reusable(project_id): raise ValueError("proof not reusable")
        return self.receipts[project_id][2]

    def current_projects(self) -> tuple[str, ...]:
        return tuple(sorted(p for p in self.bindings if self.reusable(p)))


def omega8_admit(state: Sequence[int]) -> bool:
    if len(state) != 8 or any(x not in (0,1,2) for x in state): return False
    if 0 in state: return False
    return all(x == 2 for x in state[:7]) and state[7] == 1
