"""Triadic Confluence Runtime V0.1 — D0 nonpromoting Arena donor.

Composition-first rebase for exactly two parent artifacts.
The runtime preserves compatible consequence-distinct content, collapses duplicates,
scopes dominance, and fails closed on unresolved conflict. Durable generations are
emitted only when a material delta is verified.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping, Sequence


class Relation(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    COMPLEMENTARY = "COMPLEMENTARY"
    SPECIALIZES = "SPECIALIZES"
    DOMINATES = "DOMINATES"
    CONFLICTS = "CONFLICTS"
    ORTHOGONAL = "ORTHOGONAL"
    UNKNOWN = "UNKNOWN"


class RebaseAction(str, Enum):
    COMPOSE = "COMPOSE"
    AMEND = "AMEND"
    SUPERSEDE_SCOPED = "SUPERSEDE_SCOPED"
    HOLD = "HOLD"
    COLLAPSE_SAME = "COLLAPSE_SAME"


MATERIAL_DELTA_KINDS = frozenset({
    "SEMANTIC", "FALSIFIER", "CORRECTION", "COMPRESSION", "EXECUTION",
    "EVIDENCE", "CURRENTNESS", "BLOCKER_RESOLUTION",
})


@dataclass(frozen=True)
class Clause:
    key: str
    value: str
    consequence: str
    scope: str = "GLOBAL"
    authority: int = 0
    status: str = "CURRENT_HOT"
    provenance: tuple[str, ...] = ()

    def semantic_key(self) -> tuple[str, str, str]:
        return (self.key.strip().lower(), self.scope.strip().lower(), self.consequence.strip().lower())

    def exact_key(self) -> tuple[str, str, str, str]:
        return (*self.semantic_key(), self.value.strip().lower())


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    clauses: tuple[Clause, ...]
    authority_ceiling: int = 0
    source_generation: str = "UNKNOWN"
    terminal_verified: bool = True
    claim_ceiling: str = "D0_NONPROMOTING"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterialDelta:
    kind: str
    description: str
    verified: bool
    before_cost: float | None = None
    after_cost: float | None = None

    def earns_generation(self) -> bool:
        if not self.verified or self.kind not in MATERIAL_DELTA_KINDS:
            return False
        if self.kind == "COMPRESSION":
            return (
                self.before_cost is not None and self.after_cost is not None
                and self.after_cost < self.before_cost
            )
        return True


@dataclass(frozen=True)
class ClauseDecision:
    semantic_key: tuple[str, str, str]
    relation: Relation
    selected: tuple[Clause, ...]
    reason: str


@dataclass(frozen=True)
class ConfluenceResult:
    parent_ids: tuple[str, str]
    action: RebaseAction
    decisions: tuple[ClauseDecision, ...]
    clauses: tuple[Clause, ...]
    authority_ceiling: int
    material_deltas: tuple[MaterialDelta, ...]
    durable_generation: bool
    unresolved_conflicts: tuple[tuple[str, str, str], ...]
    child_id: str | None
    normal_form_hash: str
    refinement_debt: int
    claim_ceiling: str = "D0_NONPROMOTING"

    def to_canonical_dict(self) -> dict[str, Any]:
        return canonicalize(asdict(self))


def canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): canonicalize(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        vals = [canonicalize(v) for v in value]
        return vals
    if isinstance(value, set):
        return sorted(canonicalize(v) for v in value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _with_provenance(clause: Clause, parent_id: str) -> Clause:
    prov = tuple(sorted(set(clause.provenance) | {parent_id}))
    return Clause(
        key=clause.key,
        value=clause.value,
        consequence=clause.consequence,
        scope=clause.scope,
        authority=clause.authority,
        status=clause.status,
        provenance=prov,
    )


def _relation(a: Clause, b: Clause) -> ClauseDecision:
    if a.exact_key() == b.exact_key():
        merged = Clause(
            key=a.key,
            value=a.value,
            consequence=a.consequence,
            scope=a.scope,
            authority=min(a.authority, b.authority),
            status=a.status if a.status == b.status else "CURRENT_CONDITIONAL",
            provenance=tuple(sorted(set(a.provenance) | set(b.provenance))),
        )
        return ClauseDecision(a.semantic_key(), Relation.EQUIVALENT, (merged,), "same consequence and value")

    if a.key.strip().lower() == b.key.strip().lower() and a.consequence.strip().lower() == b.consequence.strip().lower():
        if a.scope != b.scope:
            selected = tuple(sorted((a, b), key=lambda c: (c.scope, c.value, c.provenance)))
            return ClauseDecision(a.semantic_key(), Relation.SPECIALIZES, selected, "same invariant with distinct scopes")
        if a.authority != b.authority:
            winner = a if a.authority > b.authority else b
            return ClauseDecision(a.semantic_key(), Relation.DOMINATES, (winner,), "higher scoped authority resolves same consequence")
        return ClauseDecision(a.semantic_key(), Relation.CONFLICTS, (), "same scoped consequence disagrees without lawful resolver")

    if a.key.strip().lower() == b.key.strip().lower():
        selected = tuple(sorted((a, b), key=lambda c: (c.consequence, c.value, c.provenance)))
        return ClauseDecision(a.semantic_key(), Relation.COMPLEMENTARY, selected, "same topic carries consequence-distinct invariants")
    selected = tuple(sorted((a, b), key=lambda c: (c.key, c.consequence, c.value, c.provenance)))
    return ClauseDecision(a.semantic_key(), Relation.ORTHOGONAL, selected, "independent invariants coexist")


def _group(artifact: Artifact) -> dict[str, list[Clause]]:
    out: dict[str, list[Clause]] = {}
    for c in artifact.clauses:
        out.setdefault(c.key.strip().lower(), []).append(_with_provenance(c, artifact.artifact_id))
    return out


def _normal_form(clauses: Iterable[Clause]) -> tuple[Clause, ...]:
    acc: dict[tuple[str, str, str, str], Clause] = {}
    for c in clauses:
        k = c.exact_key()
        if k in acc:
            old = acc[k]
            acc[k] = Clause(
                key=min(old.key, c.key),
                value=min(old.value, c.value),
                consequence=min(old.consequence, c.consequence),
                scope=min(old.scope, c.scope),
                authority=min(old.authority, c.authority),
                status=old.status if old.status == c.status else "CURRENT_CONDITIONAL",
                provenance=tuple(sorted(set(old.provenance) | set(c.provenance))),
            )
        else:
            acc[k] = c
    return tuple(sorted(acc.values(), key=lambda c: (c.key.lower(), c.scope.lower(), c.consequence.lower(), c.value.lower(), c.provenance)))


def semantic_normal_form_hash(clauses: Sequence[Clause]) -> str:
    stripped = [
        {
            "key": c.key.strip().lower(),
            "value": c.value.strip().lower(),
            "consequence": c.consequence.strip().lower(),
            "scope": c.scope.strip().lower(),
        }
        for c in _normal_form(clauses)
    ]
    return digest(stripped)


def confluence_rebase(
    parent_a: Artifact,
    parent_b: Artifact,
    *,
    material_deltas: Sequence[MaterialDelta] = (),
    prior_normal_form_hash: str | None = None,
    refinement_debt: int = 0,
) -> ConfluenceResult:
    if parent_a.artifact_id == parent_b.artifact_id:
        raise ValueError("exactly two foreign parents are required")
    if not (parent_a.terminal_verified and parent_b.terminal_verified):
        raise ValueError("both parents must be terminal-verified")

    ga, gb = _group(parent_a), _group(parent_b)
    keys = sorted(set(ga) | set(gb))
    decisions: list[ClauseDecision] = []
    selected: list[Clause] = []
    conflicts: list[tuple[str, str, str]] = []
    any_dominance = False

    for key in keys:
        aa, bb = ga.get(key, []), gb.get(key, [])
        if not aa:
            for b in bb:
                d = ClauseDecision(b.semantic_key(), Relation.ORTHOGONAL, (b,), "present only in parent B")
                decisions.append(d); selected.extend(d.selected)
            continue
        if not bb:
            for a in aa:
                d = ClauseDecision(a.semantic_key(), Relation.ORTHOGONAL, (a,), "present only in parent A")
                decisions.append(d); selected.extend(d.selected)
            continue

        by_cons_a: dict[str, list[Clause]] = {}
        by_cons_b: dict[str, list[Clause]] = {}
        for a in aa:
            by_cons_a.setdefault(a.consequence.strip().lower(), []).append(a)
        for b in bb:
            by_cons_b.setdefault(b.consequence.strip().lower(), []).append(b)
        for cons in sorted(set(by_cons_a) | set(by_cons_b)):
            la = sorted(by_cons_a.get(cons, []), key=lambda c: (c.scope, c.value, c.provenance))
            lb = sorted(by_cons_b.get(cons, []), key=lambda c: (c.scope, c.value, c.provenance))
            pairs = min(len(la), len(lb))
            for i in range(pairs):
                d = _relation(la[i], lb[i])
                decisions.append(d)
                if d.relation == Relation.CONFLICTS:
                    conflicts.append(d.semantic_key)
                else:
                    selected.extend(d.selected)
                any_dominance |= d.relation == Relation.DOMINATES
            for a in la[pairs:]:
                d = ClauseDecision(a.semantic_key(), Relation.COMPLEMENTARY, (a,), "consequence-distinct clause present only in parent A")
                decisions.append(d); selected.extend(d.selected)
            for b in lb[pairs:]:
                d = ClauseDecision(b.semantic_key(), Relation.COMPLEMENTARY, (b,), "consequence-distinct clause present only in parent B")
                decisions.append(d); selected.extend(d.selected)

    clauses = _normal_form(selected)
    nf_hash = semantic_normal_form_hash(clauses)
    earned = tuple(d for d in material_deltas if d.earns_generation())
    has_material = bool(earned)

    same_as_prior = prior_normal_form_hash is not None and prior_normal_form_hash == nf_hash
    if conflicts:
        action = RebaseAction.HOLD
        durable = False
        child_id = None
        next_debt = refinement_debt
    elif same_as_prior and not has_material:
        action = RebaseAction.COLLAPSE_SAME
        durable = False
        child_id = None
        next_debt = refinement_debt + 1
    else:
        if any_dominance:
            action = RebaseAction.SUPERSEDE_SCOPED
        elif has_material and same_as_prior:
            action = RebaseAction.AMEND
        else:
            action = RebaseAction.COMPOSE
        durable = has_material or not same_as_prior
        child_id = f"TC-{nf_hash[:16]}" if durable else None
        next_debt = 0 if durable else refinement_debt + 1

    return ConfluenceResult(
        parent_ids=tuple(sorted((parent_a.artifact_id, parent_b.artifact_id))),
        action=action,
        decisions=tuple(sorted(decisions, key=lambda d: (d.semantic_key, d.relation.value, d.reason))),
        clauses=clauses,
        authority_ceiling=min(parent_a.authority_ceiling, parent_b.authority_ceiling),
        material_deltas=tuple(material_deltas),
        durable_generation=durable,
        unresolved_conflicts=tuple(sorted(set(conflicts))),
        child_id=child_id,
        normal_form_hash=nf_hash,
        refinement_debt=next_debt,
        claim_ceiling="D0_NONPROMOTING",
    )


def result_digest(result: ConfluenceResult) -> str:
    return digest(result.to_canonical_dict())
