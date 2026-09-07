from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from math import inf
from typing import Sequence


class EvidenceMode(str, Enum):
    HOLD_BEFORE_QUERY = "HOLD_BEFORE_QUERY"
    ZERO_DISCLOSURE = "ZERO_DISCLOSURE"
    ADAPTIVE = "ADAPTIVE"
    FULL_REIFY = "FULL_REIFY"


@dataclass(frozen=True)
class EvidenceWorld:
    world_id: str
    outcome: str
    bits: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.world_id or not self.outcome:
            raise ValueError("world_id and outcome required")
        if any(type(b) is not int or b not in (0, 1) for b in self.bits):
            raise ValueError("bits must be exact binary ints")


@dataclass(frozen=True)
class DecisionNode:
    predicate_index: int | None = None
    outcome: str | None = None
    zero: "DecisionNode | None" = None
    one: "DecisionNode | None" = None


@dataclass(frozen=True)
class EvidencePlan:
    mode: EvidenceMode
    worst_case_cost: int | None
    tree: DecisionNode | None
    queried_predicates_upper_bound: int
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def compile_minimal_evidence(
    worlds: Sequence[EvidenceWorld],
    costs: Sequence[int],
    *,
    hard_premises_valid: bool,
    supported_single_bit_family: bool = True,
) -> EvidencePlan:
    """Exact minimum-worst-case weighted single-bit decision tree.

    This is intentionally finite/model-exact. It first enforces hard premise
    admission; a uniform quotient requires no disclosure. Unsupported evidence
    families fall back to full reification rather than overclaim optimality.
    """
    if not hard_premises_valid:
        return EvidencePlan(EvidenceMode.HOLD_BEFORE_QUERY, 0, None, 0)
    if not worlds:
        raise ValueError("at least one evidence world required")
    width = len(worlds[0].bits)
    if any(len(w.bits) != width for w in worlds):
        raise ValueError("all worlds must have same predicate width")
    if len(costs) != width or any(type(c) is not int or c <= 0 for c in costs):
        raise ValueError("costs must be positive exact ints matching predicate width")
    outcomes = {w.outcome for w in worlds}
    if len(outcomes) == 1:
        return EvidencePlan(EvidenceMode.ZERO_DISCLOSURE, 0, DecisionNode(outcome=next(iter(outcomes))), 0)
    if not supported_single_bit_family:
        return EvidencePlan(EvidenceMode.FULL_REIFY, None, None, width)

    by_id = {w.world_id: w for w in worlds}
    if len(by_id) != len(worlds):
        raise ValueError("duplicate world_id")

    @lru_cache(maxsize=None)
    def solve(ids: tuple[str, ...], remaining: tuple[int, ...]):
        subset = [by_id[i] for i in ids]
        labels = {w.outcome for w in subset}
        if len(labels) == 1:
            return 0, DecisionNode(outcome=next(iter(labels))), 0
        best = (inf, None, inf)
        for p in remaining:
            z = tuple(sorted(w.world_id for w in subset if w.bits[p] == 0))
            o = tuple(sorted(w.world_id for w in subset if w.bits[p] == 1))
            if not z or not o:
                continue
            rest = tuple(x for x in remaining if x != p)
            zc, zt, zd = solve(z, rest)
            oc, ot, od = solve(o, rest)
            if zc == inf or oc == inf:
                continue
            candidate = (costs[p] + max(zc, oc), DecisionNode(p, None, zt, ot), 1 + max(zd, od))
            if candidate[0] < best[0] or (candidate[0] == best[0] and p < (best[1].predicate_index if best[1] else inf)):
                best = candidate
        return best

    ids = tuple(sorted(w.world_id for w in worlds))
    cost, tree, depth = solve(ids, tuple(range(width)))
    if cost == inf or tree is None:
        return EvidencePlan(EvidenceMode.FULL_REIFY, None, None, width)
    return EvidencePlan(EvidenceMode.ADAPTIVE, int(cost), tree, int(depth))


def evaluate(tree: DecisionNode, bits: Sequence[int]) -> str:
    node = tree
    while node.outcome is None:
        if node.predicate_index is None:
            raise ValueError("malformed decision tree")
        bit = bits[node.predicate_index]
        if type(bit) is not int or bit not in (0, 1):
            raise ValueError("bits must be binary exact ints")
        node = node.one if bit else node.zero
        if node is None:
            raise ValueError("tree branch missing")
    return node.outcome
