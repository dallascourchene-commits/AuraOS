from __future__ import annotations

"""D0 contingent invariant-closed hydration strategy for Memory City Navigator.

This module is a finite exact policy compiler over already-bound SourceSpanLocator
objects. It does not fetch source bytes, mutate K27, mint truth/currentness/effect
authority, or claim native/private Transformer KV access.

The compiler treats exact hard-invariant connected components as indivisible
hydration blocks. Before a branch/demand observation arrives, it may prefetch a
branch-independent hedge set. After the observation, it hydrates only the
remaining invariant-closed blocks for that branch. A READY strategy exists only
when one nonanticipatory prefetch choice keeps every admissible branch within the
declared capacity and deadline.
"""
from dataclasses import asdict, dataclass
from enum import Enum
from itertools import combinations
from typing import Any, Mapping

from memory_city_navigator import NavigatorError, SourceSpanLocator, digest

SCHEMA = "AURA-MEMORY-CITY-CONTINGENT-HYDRATION-v1"
D0 = "D0_NONPROMOTING"


class StrategyDisposition(str, Enum):
    READY = "READY_D0"
    HOLD_NO_CONTROLLABLE_POLICY = "HOLD_NO_CONTROLLABLE_POLICY"
    HOLD_SUPPORT_GENERATION = "HOLD_SUPPORT_GENERATION"
    HOLD_BRANCH = "HOLD_BRANCH"


@dataclass(frozen=True)
class HydrationItem:
    item_id: str
    locator: SourceSpanLocator
    duration_ticks: int

    def __post_init__(self) -> None:
        if not isinstance(self.item_id, str) or not self.item_id:
            raise NavigatorError("item_id is required")
        if type(self.duration_ticks) is not int or self.duration_ticks < 0:
            raise NavigatorError("duration_ticks must be nonnegative")


@dataclass(frozen=True)
class DemandBranch:
    branch_id: str
    demand_item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id:
            raise NavigatorError("branch_id is required")
        if not self.demand_item_ids:
            raise NavigatorError("branch demand cannot be empty")
        if len(set(self.demand_item_ids)) != len(self.demand_item_ids):
            raise NavigatorError("duplicate demand item")


@dataclass(frozen=True)
class InvariantSupport:
    generation: int
    hyperedges: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        if type(self.generation) is not int or self.generation < 0:
            raise NavigatorError("support generation must be nonnegative")
        normalized=[]
        for edge in self.hyperedges:
            if len(edge) < 2 or len(set(edge)) != len(edge):
                raise NavigatorError("hard-invariant hyperedge must contain >=2 distinct items")
            normalized.append(tuple(sorted(edge)))
        if len(set(normalized)) != len(normalized):
            raise NavigatorError("duplicate hard-invariant hyperedge")

    @property
    def normalized_hyperedges(self) -> tuple[tuple[str, ...], ...]:
        return tuple(sorted(tuple(sorted(edge)) for edge in self.hyperedges))

    @property
    def support_root(self) -> str:
        return digest({
            "schema":"AURA-MEMORY-CITY-INVARIANT-SUPPORT-v1",
            "generation":self.generation,
            "hyperedges":[list(edge) for edge in self.normalized_hyperedges],
        })


@dataclass(frozen=True)
class BranchPlan:
    branch_id: str
    required_components: tuple[tuple[str, ...], ...]
    remaining_components: tuple[tuple[str, ...], ...]
    required_item_ids: tuple[str, ...]
    remaining_item_ids: tuple[str, ...]
    resident_bytes: int
    post_reveal_ticks: int


@dataclass(frozen=True)
class ContingentHydrationStrategy:
    disposition: StrategyDisposition
    support_generation: int
    support_root: str
    prefetch_components: tuple[tuple[str, ...], ...]
    prefetch_item_ids: tuple[str, ...]
    prefetch_bytes: int
    prefetch_ticks: int
    max_resident_bytes: int
    reveal_tick: int
    deadline_tick: int
    branch_plans: tuple[BranchPlan, ...]
    reasons: tuple[str, ...]
    receipt_root: str
    authority: str = D0
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


@dataclass(frozen=True)
class StrategyUseDecision:
    disposition: StrategyDisposition
    branch_id: str
    hydrate_item_ids: tuple[str, ...]
    reason: str
    authority: str = D0
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def _canonical_items(items: tuple[HydrationItem, ...]) -> dict[str, HydrationItem]:
    out: dict[str, HydrationItem] = {}
    for item in items:
        if item.item_id in out:
            raise NavigatorError("duplicate item_id")
        out[item.item_id] = item
    if not out:
        raise NavigatorError("at least one hydration item is required")
    return out


def invariant_components(item_ids: tuple[str, ...], support: InvariantSupport) -> tuple[tuple[str, ...], ...]:
    """Return exact connected components induced only by hard-invariant hyperedges."""
    ids = tuple(sorted(set(item_ids)))
    if len(ids) != len(item_ids):
        raise NavigatorError("duplicate item id in universe")
    universe = set(ids)
    parent = {x: x for x in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra > rb:
                ra, rb = rb, ra
            parent[rb] = ra

    for edge in support.hyperedges:
        missing = set(edge) - universe
        if missing:
            raise NavigatorError("support references unknown item")
        head = edge[0]
        for x in edge[1:]:
            union(head, x)

    groups: dict[str, list[str]] = {}
    for x in ids:
        groups.setdefault(find(x), []).append(x)
    return tuple(sorted((tuple(sorted(v)) for v in groups.values()), key=lambda c: c))


def _component_maps(items: Mapping[str, HydrationItem], components: tuple[tuple[str, ...], ...]):
    item_to_component: dict[str, tuple[str, ...]] = {}
    component_bytes: dict[tuple[str, ...], int] = {}
    component_ticks: dict[tuple[str, ...], int] = {}
    for comp in components:
        component_bytes[comp] = sum(items[x].locator.span_bytes for x in comp)
        component_ticks[comp] = sum(items[x].duration_ticks for x in comp)
        for x in comp:
            item_to_component[x] = comp
    return item_to_component, component_bytes, component_ticks


def _powerset(values: tuple[tuple[str, ...], ...]):
    for r in range(len(values) + 1):
        for subset in combinations(values, r):
            yield subset


def compile_contingent_hydration(
    items: tuple[HydrationItem, ...],
    branches: tuple[DemandBranch, ...],
    support: InvariantSupport,
    *,
    max_resident_bytes: int,
    reveal_tick: int,
    deadline_tick: int,
    max_exact_components: int = 16,
) -> ContingentHydrationStrategy:
    if type(max_resident_bytes) is not int or max_resident_bytes < 0:
        raise NavigatorError("max_resident_bytes must be nonnegative")
    if type(reveal_tick) is not int or reveal_tick < 0:
        raise NavigatorError("reveal_tick must be nonnegative")
    if type(deadline_tick) is not int or deadline_tick < reveal_tick:
        raise NavigatorError("deadline_tick must be >= reveal_tick")
    if type(max_exact_components) is not int or max_exact_components <= 0:
        raise NavigatorError("max_exact_components must be positive")
    if not branches:
        raise NavigatorError("at least one demand branch is required")

    item_map = _canonical_items(items)
    branch_map: dict[str, DemandBranch] = {}
    for branch in branches:
        if branch.branch_id in branch_map:
            raise NavigatorError("duplicate branch_id")
        missing = set(branch.demand_item_ids) - set(item_map)
        if missing:
            raise NavigatorError("branch references unknown item")
        branch_map[branch.branch_id] = branch

    comps = invariant_components(tuple(item_map), support)
    if len(comps) > max_exact_components:
        raise NavigatorError("exact contingent compiler component limit exceeded")
    item_to_comp, comp_bytes, comp_ticks = _component_maps(item_map, comps)

    required_by_branch: dict[str, frozenset[tuple[str, ...]]] = {}
    for bid, branch in sorted(branch_map.items()):
        required_by_branch[bid] = frozenset(item_to_comp[x] for x in branch.demand_item_ids)

    feasible: list[tuple[Any, ...]] = []
    post_budget = deadline_tick - reveal_tick
    for prefetched in _powerset(comps):
        pset = frozenset(prefetched)
        pbytes = sum(comp_bytes[c] for c in pset)
        pticks = sum(comp_ticks[c] for c in pset)
        if pbytes > max_resident_bytes or pticks > reveal_tick:
            continue
        branch_rows = []
        ok = True
        worst_post = 0
        worst_resident = 0
        total_branch_bytes = 0
        for bid, required in sorted(required_by_branch.items()):
            remaining = required - pset
            resident = required | pset
            resident_bytes = sum(comp_bytes[c] for c in resident)
            post_ticks = sum(comp_ticks[c] for c in remaining)
            if resident_bytes > max_resident_bytes or post_ticks > post_budget:
                ok = False
                break
            worst_post = max(worst_post, post_ticks)
            worst_resident = max(worst_resident, resident_bytes)
            total_branch_bytes += sum(comp_bytes[c] for c in remaining)
            branch_rows.append((bid, required, remaining, resident_bytes, post_ticks))
        if ok:
            feasible.append((pbytes, worst_post, total_branch_bytes, tuple(prefetched),
                             worst_resident, branch_rows, pticks))

    if not feasible:
        payload = {
            "schema": SCHEMA,
            "disposition": StrategyDisposition.HOLD_NO_CONTROLLABLE_POLICY.value,
            "support_generation": support.generation,
            "support_root": support.support_root,
            "max_resident_bytes": max_resident_bytes,
            "reveal_tick": reveal_tick,
            "deadline_tick": deadline_tick,
            "components": [list(c) for c in comps],
            "branch_requirements": {
                bid: [list(c) for c in sorted(req)]
                for bid, req in sorted(required_by_branch.items())
            },
            "authority_minted": False,
        }
        return ContingentHydrationStrategy(
            StrategyDisposition.HOLD_NO_CONTROLLABLE_POLICY, support.generation, support.support_root,
            (), (), 0, 0, max_resident_bytes, reveal_tick, deadline_tick, (),
            ("NO_NONANTICIPATORY_POLICY_FOR_ALL_BRANCHES",), digest(payload)
        )

    _, _, _, prefetched, _, branch_rows, pticks = sorted(feasible, key=lambda x: x[:4])[0]
    pset = frozenset(prefetched)
    prefetch_items = tuple(sorted(x for c in pset for x in c))
    plans: list[BranchPlan] = []
    for bid, required, remaining, resident_bytes, post_ticks in branch_rows:
        required_items = tuple(sorted(x for c in required for x in c))
        remaining_items = tuple(sorted(x for c in remaining for x in c))
        plans.append(BranchPlan(
            bid, tuple(sorted(required)), tuple(sorted(remaining)),
            required_items, remaining_items, resident_bytes, post_ticks
        ))

    payload = {
        "schema": SCHEMA,
        "disposition": StrategyDisposition.READY.value,
        "support_generation": support.generation,
        "support_root": support.support_root,
        "prefetch_components": [list(c) for c in sorted(pset)],
        "prefetch_items": list(prefetch_items),
        "prefetch_bytes": sum(comp_bytes[c] for c in pset),
        "prefetch_ticks": pticks,
        "max_resident_bytes": max_resident_bytes,
        "reveal_tick": reveal_tick,
        "deadline_tick": deadline_tick,
        "branch_plans": [asdict(x) for x in plans],
        "locator_roots": {
            k: {
                "source_id": v.locator.source_id,
                "parent_export_sha256": v.locator.parent_export_sha256,
                "span_sha256": v.locator.span_sha256,
                "span_bytes": v.locator.span_bytes,
            } for k, v in sorted(item_map.items())
        },
        "authority_minted": False,
    }
    return ContingentHydrationStrategy(
        StrategyDisposition.READY, support.generation, support.support_root, tuple(sorted(pset)),
        prefetch_items, sum(comp_bytes[c] for c in pset), pticks,
        max_resident_bytes, reveal_tick, deadline_tick, tuple(plans), (),
        digest(payload)
    )


def validate_strategy_at_use(
    strategy: ContingentHydrationStrategy,
    *,
    branch_id: str,
    support: InvariantSupport,
) -> StrategyUseDecision:
    if support.generation != strategy.support_generation:
        return StrategyUseDecision(
            StrategyDisposition.HOLD_SUPPORT_GENERATION, branch_id, (),
            "support_generation_changed"
        )
    if support.support_root != strategy.support_root:
        return StrategyUseDecision(
            StrategyDisposition.HOLD_SUPPORT_GENERATION, branch_id, (),
            "support_identity_changed_same_generation"
        )
    if strategy.disposition is not StrategyDisposition.READY:
        return StrategyUseDecision(
            StrategyDisposition.HOLD_NO_CONTROLLABLE_POLICY, branch_id, (),
            "compiled_strategy_not_ready"
        )
    for plan in strategy.branch_plans:
        if plan.branch_id == branch_id:
            return StrategyUseDecision(
                StrategyDisposition.READY, branch_id, plan.remaining_item_ids,
                "branch_observed_hydrate_remaining_invariant_closure"
            )
    return StrategyUseDecision(
        StrategyDisposition.HOLD_BRANCH, branch_id, (), "unknown_branch"
    )


def clairvoyant_branch_feasible(
    items: tuple[HydrationItem, ...],
    branch: DemandBranch,
    support: InvariantSupport,
    *,
    max_resident_bytes: int,
    reveal_tick: int,
    deadline_tick: int,
) -> bool:
    """Unsafe baseline: permits the pre-reveal choice to depend on future branch."""
    item_map = _canonical_items(items)
    comps = invariant_components(tuple(item_map), support)
    item_to_comp, comp_bytes, comp_ticks = _component_maps(item_map, comps)
    required = frozenset(item_to_comp[x] for x in branch.demand_item_ids)
    post_budget = deadline_tick - reveal_tick
    for prefetched in _powerset(tuple(sorted(required))):
        pset = frozenset(prefetched)
        if sum(comp_bytes[c] for c in pset) > max_resident_bytes:
            continue
        if sum(comp_ticks[c] for c in pset) > reveal_tick:
            continue
        if sum(comp_ticks[c] for c in required - pset) > post_budget:
            continue
        if sum(comp_bytes[c] for c in required) <= max_resident_bytes:
            return True
    return False


def fixed_union_feasible(
    items: tuple[HydrationItem, ...],
    branches: tuple[DemandBranch, ...],
    support: InvariantSupport,
    *,
    max_resident_bytes: int,
    deadline_tick: int,
) -> bool:
    """Over-conservative baseline: hydrate the union of every possible branch."""
    item_map = _canonical_items(items)
    comps = invariant_components(tuple(item_map), support)
    item_to_comp, comp_bytes, comp_ticks = _component_maps(item_map, comps)
    union = frozenset(item_to_comp[x] for b in branches for x in b.demand_item_ids)
    return (
        sum(comp_bytes[c] for c in union) <= max_resident_bytes
        and sum(comp_ticks[c] for c in union) <= deadline_tick
    )
