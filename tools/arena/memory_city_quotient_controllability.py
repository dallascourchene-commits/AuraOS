from __future__ import annotations

"""D0 hard-support quotient + typed dependency/reproof + epistemic obtainability.

This layer keeps three semantics separate:
  * hard support => indivisible hydration components;
  * directed READ/INFLUENCE edges => recomputation/reproof reachability;
  * availability/currentness => whether required support can actually be obtained.

It does not fetch bytes, mutate K27, merge dependency cycles into support components,
or mint truth/effect/Gate10 authority.
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping, Sequence
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class HardSupportEdge:
    invariant_id: str
    members: tuple[str, ...]

    def validate(self):
        if not isinstance(self.invariant_id, str) or not self.invariant_id:
            raise ValueError("invariant_id required")
        if len(self.members) < 2 or len(set(self.members)) != len(self.members):
            raise ValueError("hard support edge requires >=2 distinct members")
        if any(not isinstance(x, str) or not x for x in self.members):
            raise ValueError("support members must be nonempty strings")


@dataclass(frozen=True)
class DependencyEdge:
    source_item: str
    dependent_item: str
    relation: str

    def validate(self):
        if not self.source_item or not self.dependent_item:
            raise ValueError("dependency endpoints required")
        if self.relation not in {"READ", "INFLUENCE"}:
            raise ValueError("relation must be READ or INFLUENCE")


@dataclass(frozen=True)
class QuotientComponent:
    component_id: str
    members: tuple[str, ...]
    topo_rank: int


@dataclass(frozen=True)
class LiftedDependency:
    source_component: str
    dependent_component: str
    relations: tuple[str, ...]


@dataclass(frozen=True)
class HardSupportQuotient:
    disposition: str
    support_generation: int
    support_world_root: str
    components: tuple[QuotientComponent, ...]
    dependencies: tuple[LiftedDependency, ...]
    item_to_component: tuple[tuple[str, str], ...]
    quotient_root: str
    authority_minted: bool = False
    gate10: bool = False

    def component_for(self, item_id: str) -> str:
        table = dict(self.item_to_component)
        if item_id not in table:
            raise KeyError(item_id)
        return table[item_id]


@dataclass(frozen=True)
class ComponentAvailability:
    component_id: str
    current: bool
    obtainable: bool
    available_by_tick: int
    evidence_root: str

    def validate(self):
        if not self.component_id or not self.evidence_root:
            raise ValueError("component/evidence identity required")
        if type(self.current) is not bool or type(self.obtainable) is not bool:
            raise ValueError("current/obtainable must be bool")
        if type(self.available_by_tick) is not int or self.available_by_tick < 0:
            raise ValueError("available_by_tick must be nonnegative")


@dataclass(frozen=True)
class ControllabilityDecision:
    status: str
    required_components: tuple[str, ...]
    unobtainable_components: tuple[str, ...]
    stale_components: tuple[str, ...]
    late_components: tuple[str, ...]
    reproof_components: tuple[str, ...]
    receipt_root: str
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def _component_id(members: Sequence[str]) -> str:
    ms = tuple(sorted(members))
    return "Q-" + sha256(canonical(ms).encode()).hexdigest()[:16]


def compile_hard_support_quotient(
    universe: Iterable[str],
    hard_support: Iterable[HardSupportEdge],
    dependencies: Iterable[DependencyEdge],
    *,
    support_generation: int,
    support_current: bool = True,
    support_complete: bool = True,
) -> HardSupportQuotient:
    items = tuple(sorted(set(universe)))
    if not items or any(not isinstance(x, str) or not x for x in items):
        raise ValueError("nonempty universe required")
    if type(support_generation) is not int or support_generation < 0:
        raise ValueError("support_generation must be nonnegative")
    if type(support_current) is not bool or type(support_complete) is not bool:
        raise ValueError("support flags must be bool")
    if not support_current:
        return _hold("HOLD_SUPPORT_STALE", support_generation, items)
    if not support_complete:
        return _hold("HOLD_SUPPORT_INCOMPLETE", support_generation, items)

    parent = {x: x for x in items}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            if ra > rb: ra, rb = rb, ra
            parent[rb] = ra

    support_rows = tuple(hard_support)
    normalized_support = []
    for edge in support_rows:
        edge.validate()
        normalized_support.append(tuple(sorted(edge.members)))
    if len(set(normalized_support)) != len(normalized_support):
        raise ValueError("duplicate hard support hyperedge")
    support_world_root = digest({
        "schema":"AURA-MEMORY-CITY-INVARIANT-SUPPORT-v1",
        "generation":support_generation,
        "hyperedges":[list(edge) for edge in sorted(normalized_support)],
    })
    for edge in support_rows:
        missing = set(edge.members) - set(items)
        if missing:
            raise ValueError("support references unknown item")
        h = edge.members[0]
        for m in edge.members[1:]: union(h, m)

    groups = {}
    for item in items:
        groups.setdefault(find(item), []).append(item)
    member_groups = tuple(sorted((tuple(sorted(v)) for v in groups.values())))
    item_to_cid = {}
    for members in member_groups:
        cid = _component_id(members)
        for x in members: item_to_cid[x] = cid

    lifted_relations = {}
    for edge in tuple(dependencies):
        edge.validate()
        if edge.source_item not in item_to_cid or edge.dependent_item not in item_to_cid:
            raise ValueError("dependency references unknown item")
        s, d = item_to_cid[edge.source_item], item_to_cid[edge.dependent_item]
        if s == d:
            continue
        lifted_relations.setdefault((s, d), set()).add(edge.relation)

    nodes = sorted(set(item_to_cid.values()))
    outgoing = {n: set() for n in nodes}
    indeg = {n: 0 for n in nodes}
    for s, d in lifted_relations:
        if d not in outgoing[s]:
            outgoing[s].add(d); indeg[d] += 1
    queue = sorted([n for n in nodes if indeg[n] == 0])
    order = []
    while queue:
        n = queue.pop(0); order.append(n)
        for d in sorted(outgoing[n]):
            indeg[d] -= 1
            if indeg[d] == 0:
                queue.append(d); queue.sort()
    if len(order) != len(nodes):
        return _hold("HOLD_DEPENDENCY_CYCLE", support_generation, items, item_to_cid=item_to_cid)
    rank = {n: i for i, n in enumerate(order)}
    components = tuple(sorted((QuotientComponent(_component_id(m), m, rank[_component_id(m)]) for m in member_groups), key=lambda x: x.component_id))
    lifted = tuple(LiftedDependency(s, d, tuple(sorted(rs))) for (s, d), rs in sorted(lifted_relations.items()))
    item_map = tuple(sorted(item_to_cid.items()))
    payload = {
        "disposition":"READY_HARD_SUPPORT_QUOTIENT_D0",
        "support_generation":support_generation,
        "support_world_root":support_world_root,
        "components":[{"id":c.component_id,"members":c.members,"rank":c.topo_rank} for c in components],
        "dependencies":[{"source":e.source_component,"dependent":e.dependent_component,"relations":e.relations} for e in lifted],
        "item_to_component":item_map,
    }
    return HardSupportQuotient("READY_HARD_SUPPORT_QUOTIENT_D0", support_generation, support_world_root, components, lifted, item_map, digest(payload))


def _hold(status, generation, items, *, item_to_cid=None):
    item_map = tuple(sorted((item_to_cid or {x: x for x in items}).items()))
    support_world_root = digest({
        "schema":"AURA-MEMORY-CITY-INVARIANT-SUPPORT-v1",
        "generation":generation,
        "hyperedges":[],
    })
    payload={"disposition":status,"support_generation":generation,"support_world_root":support_world_root,"items":items,"item_to_component":item_map}
    return HardSupportQuotient(status,generation,support_world_root,(),(),item_map,digest(payload))


def support_components_for_items(q: HardSupportQuotient, item_ids: Iterable[str]) -> tuple[str, ...]:
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        raise ValueError("quotient not ready")
    return tuple(sorted({q.component_for(x) for x in item_ids}))


def reproof_cone(q: HardSupportQuotient, changed_items: Iterable[str]) -> tuple[str, ...]:
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        raise ValueError("quotient not ready")
    seeds=set(support_components_for_items(q, changed_items))
    out={e.source_component:set() for e in q.dependencies}
    for c in q.components: out.setdefault(c.component_id,set())
    for e in q.dependencies: out[e.source_component].add(e.dependent_component)
    seen=set(seeds); pending=list(sorted(seeds))
    while pending:
        n=pending.pop(0)
        for d in sorted(out.get(n,())):
            if d not in seen:
                seen.add(d); pending.append(d)
    return tuple(sorted(seen))


def compile_controllability_cut(
    q: HardSupportQuotient,
    required_items: Iterable[str],
    availability: Mapping[str, ComponentAvailability],
    *,
    decision_tick: int,
    changed_items_for_reproof: Iterable[str] = (),
) -> ControllabilityDecision:
    if type(decision_tick) is not int or decision_tick < 0:
        raise ValueError("decision_tick must be nonnegative")
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        return _decision("HOLD_QUOTIENT_NOT_READY",(),(),(),(),(),q.quotient_root)
    required=support_components_for_items(q, required_items)
    stale=[]; unavailable=[]; late=[]
    for cid in required:
        a=availability.get(cid)
        if a is None:
            unavailable.append(cid); continue
        a.validate()
        if a.component_id != cid:
            unavailable.append(cid); continue
        if not a.current: stale.append(cid)
        elif not a.obtainable: unavailable.append(cid)
        elif a.available_by_tick > decision_tick: late.append(cid)
    rep = reproof_cone(q, changed_items_for_reproof) if tuple(changed_items_for_reproof) else ()
    if stale:
        status="HOLD_STALE_REQUIRED_SUPPORT"
    elif unavailable:
        status="HOLD_UNCONTROLLABLE_SUPPORT"
    elif late:
        status="HOLD_LATE_REQUIRED_SUPPORT"
    else:
        status="READY_CONTROLLABLE_SUPPORT_D0"
    return _decision(status,required,tuple(sorted(unavailable)),tuple(sorted(stale)),tuple(sorted(late)),rep,q.quotient_root)


def _decision(status,required,unavailable,stale,late,reproof,qroot):
    payload={"status":status,"required":required,"unavailable":unavailable,"stale":stale,"late":late,"reproof":reproof,"quotient_root":qroot}
    return ControllabilityDecision(status,tuple(required),tuple(unavailable),tuple(stale),tuple(late),tuple(reproof),digest(payload))


def hard13d_quotient(axes: tuple[int, ...]) -> str:
    if len(axes)!=13 or any(type(x) is not int or x not in (0,1,2) for x in axes):
        return "HOLD_MALFORMED"
    hard=axes[:8]
    if 0 in hard: return "HOLD_HARD_INVALID"
    if 1 in hard: return "HOLD_UNRESOLVED"
    return "READY_D0"


def validate_contingent_strategy_branch(
    q: HardSupportQuotient,
    strategy,
    *,
    branch_id: str,
    availability: Mapping[str, ComponentAvailability],
    decision_tick: int,
    changed_items_for_reproof: Iterable[str] = (),
) -> ControllabilityDecision:
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        return _decision("HOLD_QUOTIENT_NOT_READY",(),(),(),(),(),q.quotient_root)
    raw_disp = getattr(strategy, "disposition", None)
    disp = getattr(raw_disp, "value", raw_disp)
    if disp != "READY_D0":
        return _decision("HOLD_PARENT_POLICY_NOT_READY",(),(),(),(),(),q.quotient_root)
    if getattr(strategy, "support_generation", None) != q.support_generation:
        return _decision("HOLD_SUPPORT_GENERATION",(),(),(),(),(),q.quotient_root)
    if getattr(strategy, "support_root", None) != q.support_world_root:
        return _decision("HOLD_SUPPORT_WORLD_IDENTITY_MISMATCH",(),(),(),(),(),q.quotient_root)
    plan = next((p for p in getattr(strategy, "branch_plans", ()) if getattr(p, "branch_id", None) == branch_id), None)
    if plan is None:
        return _decision("HOLD_BRANCH_UNKNOWN",(),(),(),(),(),q.quotient_root)
    required_items = tuple(getattr(plan, "required_item_ids", ()))
    if not required_items:
        return _decision("HOLD_PARENT_POLICY_MALFORMED",(),(),(),(),(),q.quotient_root)
    required_cids = set(support_components_for_items(q, required_items))
    expected = {tuple(sorted(c.members)) for c in q.components if c.component_id in required_cids}
    actual = {tuple(sorted(c)) for c in getattr(plan, "required_components", ())}
    if expected != actual:
        return _decision("HOLD_SUPPORT_PARTITION_MISMATCH",tuple(sorted(required_cids)),(),(),(),(),q.quotient_root)
    return compile_controllability_cut(q, required_items, availability, decision_tick=decision_tick, changed_items_for_reproof=changed_items_for_reproof)
