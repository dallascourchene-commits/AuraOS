from __future__ import annotations

"""D0 hard-support quotient + typed reproof + ECF-bound obtainability.

Hard support, dependency/reproof, evidence currentness/obtainability, and K27
locality remain distinct semantics. Availability predicates are interpreted only
after exact current ECF leaf admission. No fetch, mutation, signature verification,
truth/effect authority, Gate10, or PKI ownership is implemented here.
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Mapping, Sequence
import json
from memory_city_ecf_adapter import ECFAdmissionIndex

AVAILABILITY_EVIDENCE_SCOPE = "MEMORY_CITY_COMPONENT_AVAILABILITY"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def _hex64(value, field):
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


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

    def component_for(self, item_id):
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
        if not isinstance(self.component_id, str) or not self.component_id:
            raise ValueError("component identity required")
        if type(self.current) is not bool or type(self.obtainable) is not bool:
            raise ValueError("current/obtainable must be exact bool")
        if type(self.available_by_tick) is not int or self.available_by_tick < 0:
            raise ValueError("available_by_tick must be nonnegative exact int")
        _hex64(self.evidence_root, "evidence_root")


@dataclass(frozen=True)
class ControllabilityDecision:
    status: str
    required_components: tuple[str, ...]
    unobtainable_components: tuple[str, ...]
    stale_components: tuple[str, ...]
    late_components: tuple[str, ...]
    reproof_components: tuple[str, ...]
    receipt_root: str
    evidence_witness_roots: tuple[str, ...] = ()
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def _component_id(members: Sequence[str]) -> str:
    return "Q-" + sha256(canonical(tuple(sorted(members))).encode()).hexdigest()[:16]


def compile_hard_support_quotient(
    universe: Iterable[str], hard_support: Iterable[HardSupportEdge],
    dependencies: Iterable[DependencyEdge], *, support_generation: int,
    support_current: bool = True, support_complete: bool = True,
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
            if ra > rb:
                ra, rb = rb, ra
            parent[rb] = ra

    support_rows = tuple(hard_support)
    normalized_support = []
    for edge in support_rows:
        edge.validate()
        normalized_support.append(tuple(sorted(edge.members)))
    if len(set(normalized_support)) != len(normalized_support):
        raise ValueError("duplicate hard support hyperedge")
    support_world_root = digest({
        "schema": "AURA-MEMORY-CITY-INVARIANT-SUPPORT-v1",
        "generation": support_generation,
        "hyperedges": [list(edge) for edge in sorted(normalized_support)],
    })
    for edge in support_rows:
        if set(edge.members) - set(items):
            raise ValueError("support references unknown item")
        for member in edge.members[1:]:
            union(edge.members[0], member)

    groups = {}
    for item in items:
        groups.setdefault(find(item), []).append(item)
    member_groups = tuple(sorted(tuple(sorted(v)) for v in groups.values()))
    item_to_cid = {}
    for members in member_groups:
        cid = _component_id(members)
        for item in members:
            item_to_cid[item] = cid

    lifted_relations = {}
    for edge in tuple(dependencies):
        edge.validate()
        if edge.source_item not in item_to_cid or edge.dependent_item not in item_to_cid:
            raise ValueError("dependency references unknown item")
        source, dependent = item_to_cid[edge.source_item], item_to_cid[edge.dependent_item]
        if source != dependent:
            lifted_relations.setdefault((source, dependent), set()).add(edge.relation)

    nodes = sorted(set(item_to_cid.values()))
    outgoing = {node: set() for node in nodes}
    indeg = {node: 0 for node in nodes}
    for source, dependent in lifted_relations:
        if dependent not in outgoing[source]:
            outgoing[source].add(dependent)
            indeg[dependent] += 1
    queue = sorted(node for node in nodes if indeg[node] == 0)
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for dependent in sorted(outgoing[node]):
            indeg[dependent] -= 1
            if indeg[dependent] == 0:
                queue.append(dependent)
                queue.sort()
    if len(order) != len(nodes):
        return _hold("HOLD_DEPENDENCY_CYCLE", support_generation, items, item_to_cid=item_to_cid)

    rank = {node: i for i, node in enumerate(order)}
    components = tuple(sorted(
        (QuotientComponent(_component_id(members), members, rank[_component_id(members)]) for members in member_groups),
        key=lambda component: component.component_id,
    ))
    lifted = tuple(
        LiftedDependency(source, dependent, tuple(sorted(relations)))
        for (source, dependent), relations in sorted(lifted_relations.items())
    )
    item_map = tuple(sorted(item_to_cid.items()))
    payload = {
        "disposition": "READY_HARD_SUPPORT_QUOTIENT_D0",
        "support_generation": support_generation,
        "support_world_root": support_world_root,
        "components": [
            {"id": component.component_id, "members": component.members, "rank": component.topo_rank}
            for component in components
        ],
        "dependencies": [
            {"source": edge.source_component, "dependent": edge.dependent_component, "relations": edge.relations}
            for edge in lifted
        ],
        "item_to_component": item_map,
    }
    return HardSupportQuotient(
        "READY_HARD_SUPPORT_QUOTIENT_D0", support_generation, support_world_root,
        components, lifted, item_map, digest(payload),
    )


def _hold(status, generation, items, *, item_to_cid=None):
    item_map = tuple(sorted((item_to_cid or {x: x for x in items}).items()))
    support_world_root = digest({
        "schema": "AURA-MEMORY-CITY-INVARIANT-SUPPORT-v1",
        "generation": generation,
        "hyperedges": [],
    })
    payload = {
        "disposition": status,
        "support_generation": generation,
        "support_world_root": support_world_root,
        "items": items,
        "item_to_component": item_map,
    }
    return HardSupportQuotient(status, generation, support_world_root, (), (), item_map, digest(payload))


def support_components_for_items(q, item_ids):
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        raise ValueError("quotient not ready")
    return tuple(sorted({q.component_for(item) for item in item_ids}))


def reproof_cone(q, changed_items):
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        raise ValueError("quotient not ready")
    seeds = set(support_components_for_items(q, changed_items))
    outgoing = {component.component_id: set() for component in q.components}
    for edge in q.dependencies:
        outgoing[edge.source_component].add(edge.dependent_component)
    seen = set(seeds)
    pending = list(sorted(seeds))
    while pending:
        node = pending.pop(0)
        for dependent in sorted(outgoing.get(node, ())):
            if dependent not in seen:
                seen.add(dependent)
                pending.append(dependent)
    return tuple(sorted(seen))


def component_availability_evidence_root(
    q: HardSupportQuotient, component_id: str, current: bool,
    obtainable: bool, available_by_tick: int,
) -> str:
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        raise ValueError("quotient not ready")
    if component_id not in {component.component_id for component in q.components}:
        raise ValueError("unknown component")
    if type(current) is not bool or type(obtainable) is not bool:
        raise ValueError("current/obtainable must be exact bool")
    if type(available_by_tick) is not int or available_by_tick < 0:
        raise ValueError("available_by_tick must be nonnegative exact int")
    return digest({
        "schema": "AURA-MEMORY-CITY-COMPONENT-AVAILABILITY-EVIDENCE-v1",
        "quotient_root": q.quotient_root,
        "support_world_root": q.support_world_root,
        "support_generation": q.support_generation,
        "component_id": component_id,
        "current": current,
        "obtainable": obtainable,
        "available_by_tick": available_by_tick,
    })


def make_component_availability(q, component_id, *, current, obtainable, available_by_tick):
    return ComponentAvailability(
        component_id, current, obtainable, available_by_tick,
        component_availability_evidence_root(
            q, component_id, current, obtainable, available_by_tick
        ),
    )


def _decision(status, required, unavailable, stale, late, reproof, qroot, evidence_witness_roots=()):
    witness_roots = tuple(sorted(evidence_witness_roots))
    payload = {
        "status": status,
        "required": required,
        "unavailable": unavailable,
        "stale": stale,
        "late": late,
        "reproof": reproof,
        "quotient_root": qroot,
        "evidence_witness_roots": witness_roots,
    }
    return ControllabilityDecision(
        status, tuple(required), tuple(unavailable), tuple(stale), tuple(late),
        tuple(reproof), digest(payload), witness_roots,
    )


def compile_controllability_cut(
    q: HardSupportQuotient, required_items: Iterable[str],
    availability: Mapping[str, ComponentAvailability], *, decision_tick: int,
    changed_items_for_reproof: Iterable[str] = (),
    ecf_index: ECFAdmissionIndex | None = None,
) -> ControllabilityDecision:
    if type(decision_tick) is not int or decision_tick < 0:
        raise ValueError("decision_tick must be nonnegative")
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        return _decision("HOLD_QUOTIENT_NOT_READY", (), (), (), (), (), q.quotient_root)

    required = support_components_for_items(q, required_items)
    stale, unavailable, late, witness_roots = [], [], [], []
    for cid in required:
        component = availability.get(cid)
        if component is None:
            unavailable.append(cid)
            continue
        component.validate()
        if component.component_id != cid:
            unavailable.append(cid)
            continue

        expected_evidence_root = component_availability_evidence_root(
            q, cid, component.current, component.obtainable,
            component.available_by_tick,
        )
        if component.evidence_root != expected_evidence_root:
            return _decision(
                "HOLD_AVAILABILITY_EVIDENCE_BINDING_MISMATCH", required,
                (), (), (), (), q.quotient_root, witness_roots,
            )
        if ecf_index is None:
            return _decision(
                "HOLD_ECF_EVIDENCE_INGRESS_REQUIRED", required,
                (), (), (), (), q.quotient_root, witness_roots,
            )
        admission = ecf_index.resolve(
            component.evidence_root, scope=AVAILABILITY_EVIDENCE_SCOPE
        )
        if admission.status != "ADMITTED_EVIDENCE_D0":
            return _decision(
                admission.status, required, (), (), (), (),
                q.quotient_root, witness_roots,
            )
        witness_roots.append(admission.witness_root)

        # Only ECF-admitted predicates are interpreted semantically.
        if not component.current:
            stale.append(cid)
        elif not component.obtainable:
            unavailable.append(cid)
        elif component.available_by_tick > decision_tick:
            late.append(cid)

    reproof = reproof_cone(q, changed_items_for_reproof) if tuple(changed_items_for_reproof) else ()
    if stale:
        status = "HOLD_STALE_REQUIRED_SUPPORT"
    elif unavailable:
        status = "HOLD_UNCONTROLLABLE_SUPPORT"
    elif late:
        status = "HOLD_LATE_REQUIRED_SUPPORT"
    else:
        status = "READY_CONTROLLABLE_SUPPORT_D0"
    return _decision(
        status, required, tuple(sorted(unavailable)), tuple(sorted(stale)),
        tuple(sorted(late)), reproof, q.quotient_root, witness_roots,
    )


def hard13d_quotient(axes):
    if len(axes) != 13 or any(type(x) is not int or x not in (0, 1, 2) for x in axes):
        return "HOLD_MALFORMED"
    hard = axes[:8]
    if 0 in hard:
        return "HOLD_HARD_INVALID"
    if 1 in hard:
        return "HOLD_UNRESOLVED"
    return "READY_D0"


def validate_contingent_strategy_branch(
    q: HardSupportQuotient, strategy, *, branch_id: str,
    availability: Mapping[str, ComponentAvailability], decision_tick: int,
    changed_items_for_reproof: Iterable[str] = (),
    ecf_index: ECFAdmissionIndex | None = None,
) -> ControllabilityDecision:
    if q.disposition != "READY_HARD_SUPPORT_QUOTIENT_D0":
        return _decision("HOLD_QUOTIENT_NOT_READY", (), (), (), (), (), q.quotient_root)
    raw_disposition = getattr(strategy, "disposition", None)
    disposition = getattr(raw_disposition, "value", raw_disposition)
    if disposition != "READY_D0":
        return _decision("HOLD_PARENT_POLICY_NOT_READY", (), (), (), (), (), q.quotient_root)
    if getattr(strategy, "support_generation", None) != q.support_generation:
        return _decision("HOLD_SUPPORT_GENERATION", (), (), (), (), (), q.quotient_root)
    if getattr(strategy, "support_root", None) != q.support_world_root:
        return _decision("HOLD_SUPPORT_WORLD_IDENTITY_MISMATCH", (), (), (), (), (), q.quotient_root)
    plan = next(
        (candidate for candidate in getattr(strategy, "branch_plans", ()) if getattr(candidate, "branch_id", None) == branch_id),
        None,
    )
    if plan is None:
        return _decision("HOLD_BRANCH_UNKNOWN", (), (), (), (), (), q.quotient_root)
    required_items = tuple(getattr(plan, "required_item_ids", ()))
    if not required_items:
        return _decision("HOLD_PARENT_POLICY_MALFORMED", (), (), (), (), (), q.quotient_root)
    required_cids = set(support_components_for_items(q, required_items))
    expected = {
        tuple(sorted(component.members))
        for component in q.components if component.component_id in required_cids
    }
    actual = {tuple(sorted(component)) for component in getattr(plan, "required_components", ())}
    if expected != actual:
        return _decision(
            "HOLD_SUPPORT_PARTITION_MISMATCH", tuple(sorted(required_cids)),
            (), (), (), (), q.quotient_root,
        )
    return compile_controllability_cut(
        q, required_items, availability, decision_tick=decision_tick,
        changed_items_for_reproof=changed_items_for_reproof,
        ecf_index=ecf_index,
    )
