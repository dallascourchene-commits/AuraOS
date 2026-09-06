from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import re
from typing import Iterable, Mapping

HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXACT = "EXACT"
REBIND = "REBIND"
REPROVE = "REPROVE"
HOLD = "HOLD"


class ReproofContractError(ValueError):
    pass


def _strict_text(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise ReproofContractError(f"INVALID_TEXT:{name}")
    return value


def _root(value: object, name: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise ReproofContractError(f"INVALID_ROOT:{name}")
    return value


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return sha256(raw.encode()).hexdigest()


def _canon_pairs(
    items: Iterable[tuple[str, str]],
    name: str,
    value_is_root: bool = False,
) -> tuple[tuple[str, str], ...]:
    out = []
    seen = set()
    for key, value in items:
        key = _strict_text(key, f"{name}.key")
        value = _root(value, f"{name}.{key}") if value_is_root else _strict_text(value, f"{name}.{key}")
        if key in seen:
            raise ReproofContractError(f"DUPLICATE_KEY:{name}:{key}")
        seen.add(key)
        out.append((key, value))
    return tuple(sorted(out))


@dataclass(frozen=True)
class Node:
    node_id: str
    dependencies: tuple[str, ...] = ()
    verifier_id: str = ""
    consequence_keys: tuple[str, ...] = ()

    def canonical(self) -> "Node":
        node_id = _strict_text(self.node_id, "node_id")
        verifier_id = _strict_text(self.verifier_id, f"{node_id}.verifier_id")
        deps = tuple(_strict_text(x, f"{node_id}.dependency") for x in self.dependencies)
        keys = tuple(_strict_text(x, f"{node_id}.consequence_key") for x in self.consequence_keys)
        if len(set(deps)) != len(deps):
            raise ReproofContractError(f"DUPLICATE_DEPENDENCY:{node_id}")
        if len(set(keys)) != len(keys):
            raise ReproofContractError(f"DUPLICATE_CONSEQUENCE_KEY:{node_id}")
        return replace(
            self,
            node_id=node_id,
            verifier_id=verifier_id,
            dependencies=tuple(sorted(deps)),
            consequence_keys=tuple(sorted(keys)),
        )


@dataclass(frozen=True)
class CanonicalGraph:
    nodes: tuple[Node, ...]
    graph_root: str
    topo_order: tuple[str, ...]

    @classmethod
    def build(cls, nodes: Iterable[Node]) -> "CanonicalGraph":
        canonical = tuple(sorted((n.canonical() for n in nodes), key=lambda n: n.node_id))
        if not canonical:
            raise ReproofContractError("EMPTY_GRAPH")
        ids = [n.node_id for n in canonical]
        if len(set(ids)) != len(ids):
            raise ReproofContractError("DUPLICATE_NODE")
        by_id = {n.node_id: n for n in canonical}
        for n in canonical:
            for dep in n.dependencies:
                if dep not in by_id:
                    raise ReproofContractError(f"UNKNOWN_DEPENDENCY:{n.node_id}:{dep}")
                if dep == n.node_id:
                    raise ReproofContractError(f"SELF_CYCLE:{n.node_id}")
        indegree = {x: 0 for x in ids}
        children = {x: [] for x in ids}
        for n in canonical:
            indegree[n.node_id] = len(n.dependencies)
            for dep in n.dependencies:
                children[dep].append(n.node_id)
        ready = sorted(x for x in ids if indegree[x] == 0)
        topo = []
        while ready:
            cur = ready.pop(0)
            topo.append(cur)
            for child in sorted(children[cur]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
                    ready.sort()
        if len(topo) != len(ids):
            raise ReproofContractError("CYCLE")
        body = [
            {
                "node_id": n.node_id,
                "dependencies": n.dependencies,
                "verifier_id": n.verifier_id,
                "consequence_keys": n.consequence_keys,
            }
            for n in canonical
        ]
        return cls(canonical, _digest(body), tuple(topo))

    @property
    def by_id(self) -> Mapping[str, Node]:
        return {n.node_id: n for n in self.nodes}

    def dependency_closed_descendants(self, seeds: Iterable[str]) -> tuple[str, ...]:
        seed_set = set()
        for seed in seeds:
            seed = _strict_text(seed, "changed_root")
            if seed not in self.by_id:
                raise ReproofContractError(f"UNKNOWN_CHANGED_ROOT:{seed}")
            seed_set.add(seed)
        children = {n.node_id: [] for n in self.nodes}
        for n in self.nodes:
            for dep in n.dependencies:
                children[dep].append(n.node_id)
        closure = set(seed_set)
        stack = sorted(seed_set, reverse=True)
        while stack:
            cur = stack.pop()
            for child in sorted(children[cur]):
                if child not in closure:
                    closure.add(child)
                    stack.append(child)
        return tuple(x for x in self.topo_order if x in closure)


@dataclass(frozen=True)
class AdmissionSurface:
    graph_root: str
    verifier_generations: tuple[tuple[str, str], ...]
    accepted_witness_roots: tuple[tuple[str, str], ...]
    proof_projection_roots: tuple[tuple[str, str], ...]
    semantic_domain_roots: tuple[tuple[str, str], ...]
    observation_generation: str
    external_receipt_root: str
    surface_root: str = ""

    @classmethod
    def mint_identity_surface(
        cls,
        *,
        graph_root: str,
        verifier_generations: Iterable[tuple[str, str]],
        accepted_witness_roots: Iterable[tuple[str, str]],
        proof_projection_roots: Iterable[tuple[str, str]],
        semantic_domain_roots: Iterable[tuple[str, str]],
        observation_generation: str,
        external_receipt_root: str,
    ) -> "AdmissionSurface":
        graph_root = _root(graph_root, "graph_root")
        vg = _canon_pairs(verifier_generations, "verifier_generations")
        aw = _canon_pairs(accepted_witness_roots, "accepted_witness_roots", True)
        pp = _canon_pairs(proof_projection_roots, "proof_projection_roots", True)
        sd = _canon_pairs(semantic_domain_roots, "semantic_domain_roots", True)
        observation_generation = _strict_text(observation_generation, "observation_generation")
        external_receipt_root = _root(external_receipt_root, "external_receipt_root")
        body = {
            "graph_root": graph_root,
            "verifier_generations": vg,
            "accepted_witness_roots": aw,
            "proof_projection_roots": pp,
            "semantic_domain_roots": sd,
            "observation_generation": observation_generation,
            "external_receipt_root": external_receipt_root,
        }
        return cls(graph_root, vg, aw, pp, sd, observation_generation, external_receipt_root, _digest(body))


@dataclass(frozen=True)
class CurrentOwnerSurface:
    graph_root: str
    verifier_generations: tuple[tuple[str, str], ...]
    projection_roots: tuple[tuple[str, str], ...]
    semantic_domain_roots: tuple[tuple[str, str], ...]
    owner_replay_receipt_root: str
    surface_root: str = ""

    @classmethod
    def mint_identity_surface(
        cls,
        *,
        graph_root: str,
        verifier_generations: Iterable[tuple[str, str]],
        projection_roots: Iterable[tuple[str, str]],
        semantic_domain_roots: Iterable[tuple[str, str]],
        owner_replay_receipt_root: str,
    ) -> "CurrentOwnerSurface":
        graph_root = _root(graph_root, "owner.graph_root")
        vg = _canon_pairs(verifier_generations, "owner.verifier_generations")
        pp = _canon_pairs(projection_roots, "owner.projection_roots", True)
        sd = _canon_pairs(semantic_domain_roots, "owner.semantic_domain_roots", True)
        owner_replay_receipt_root = _root(owner_replay_receipt_root, "owner_replay_receipt_root")
        body = {
            "graph_root": graph_root,
            "verifier_generations": vg,
            "projection_roots": pp,
            "semantic_domain_roots": sd,
            "owner_replay_receipt_root": owner_replay_receipt_root,
        }
        return cls(graph_root, vg, pp, sd, owner_replay_receipt_root, _digest(body))


@dataclass(frozen=True)
class EvidenceWitness:
    node_id: str
    graph_root: str
    witness_root: str
    output_root: str
    verifier_generation: str
    dependency_input_root: str
    projection_root: str
    semantic_domain_root: str
    d0: bool = True
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def validate_shape(self) -> None:
        _strict_text(self.node_id, "witness.node_id")
        for name in (
            "graph_root",
            "witness_root",
            "output_root",
            "dependency_input_root",
            "projection_root",
            "semantic_domain_root",
        ):
            _root(getattr(self, name), f"witness.{name}")
        _strict_text(self.verifier_generation, "witness.verifier_generation")
        for name in ("d0", "truth_authority", "effect_authority", "gate10"):
            if type(getattr(self, name)) is not bool:
                raise ReproofContractError(f"INVALID_BOOL:witness.{name}")


@dataclass(frozen=True)
class ReproofPlan:
    graph_root: str
    explicit_changed_roots: tuple[str, ...]
    drift_seeds: tuple[str, ...]
    rebind_nodes: tuple[str, ...]
    recompute_order: tuple[str, ...]
    reuse_nodes: tuple[str, ...]
    transition_classes: tuple[tuple[str, str], ...]
    admission_surface_root: str
    owner_surface_root: str
    authority_ceiling: str
    plan_root: str


def _pairs_map(pairs: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return dict(pairs)


def classify_owner_transition(
    *,
    proof_generation: object,
    current_generation: object,
    proof_projection_root: object,
    current_projection_root: object,
    proof_semantic_domain_root: object,
    current_semantic_domain_root: object,
) -> str:
    """Classify current-owner movement without authenticating either owner receipt.

    EXACT: generation, projection, and semantic-domain identity are unchanged.
    REBIND: generation moved, but exact projection and semantic-domain identities did not.
    REPROVE: projection or semantic-domain identity moved.
    HOLD: any required identity is malformed/unknown.
    """
    try:
        pg = _strict_text(proof_generation, "transition.proof_generation")
        cg = _strict_text(current_generation, "transition.current_generation")
        pp = _root(proof_projection_root, "transition.proof_projection_root")
        cp = _root(current_projection_root, "transition.current_projection_root")
        pd = _root(proof_semantic_domain_root, "transition.proof_semantic_domain_root")
        cd = _root(current_semantic_domain_root, "transition.current_semantic_domain_root")
    except ReproofContractError:
        return HOLD
    if pp != cp or pd != cd:
        return REPROVE
    if pg != cg:
        return REBIND
    return EXACT


def dependency_input_root(
    graph: CanonicalGraph,
    node_id: str,
    evidence: Mapping[str, EvidenceWitness],
) -> str:
    node = graph.by_id[node_id]
    bound = []
    for dep in node.dependencies:
        if dep not in evidence:
            raise ReproofContractError(f"MISSING_DEPENDENCY_EVIDENCE:{node_id}:{dep}")
        ev = evidence[dep]
        ev.validate_shape()
        bound.append((dep, ev.output_root, ev.semantic_domain_root))
    return _digest(tuple(sorted(bound)))


def compile_reproof_plan(
    graph: CanonicalGraph,
    *,
    explicit_changed_roots: Iterable[str],
    evidence: Mapping[str, EvidenceWitness],
    admission: AdmissionSurface,
    current_owner: CurrentOwnerSurface,
) -> ReproofPlan:
    if admission.graph_root != graph.graph_root or current_owner.graph_root != graph.graph_root:
        raise ReproofContractError("CROSS_GRAPH_SURFACE")

    expected_nodes = set(graph.by_id)
    aw = _pairs_map(admission.accepted_witness_roots)
    proof_proj = _pairs_map(admission.proof_projection_roots)
    proof_domain = _pairs_map(admission.semantic_domain_roots)
    owner_proj = _pairs_map(current_owner.projection_roots)
    owner_domain = _pairs_map(current_owner.semantic_domain_roots)
    admitted_gen = _pairs_map(admission.verifier_generations)
    owner_gen = _pairs_map(current_owner.verifier_generations)

    for label, mapping in (
        ("accepted_witness", aw),
        ("proof_projection", proof_proj),
        ("proof_domain", proof_domain),
        ("owner_projection", owner_proj),
        ("owner_domain", owner_domain),
    ):
        if set(mapping) != expected_nodes:
            raise ReproofContractError(f"INCOMPLETE_NODE_SURFACE:{label}")

    verifier_ids = {n.verifier_id for n in graph.nodes}
    if set(admitted_gen) != verifier_ids or set(owner_gen) != verifier_ids:
        raise ReproofContractError("INCOMPLETE_VERIFIER_GENERATION_SURFACE")

    explicit = tuple(sorted({_strict_text(x, "explicit_changed_root") for x in explicit_changed_roots}))
    for root in explicit:
        if root not in expected_nodes:
            raise ReproofContractError(f"UNKNOWN_CHANGED_ROOT:{root}")

    classes: dict[str, str] = {}
    drift = set()
    candidate_rebind = set()
    for n in graph.nodes:
        state = classify_owner_transition(
            proof_generation=admitted_gen[n.verifier_id],
            current_generation=owner_gen[n.verifier_id],
            proof_projection_root=proof_proj[n.node_id],
            current_projection_root=owner_proj[n.node_id],
            proof_semantic_domain_root=proof_domain[n.node_id],
            current_semantic_domain_root=owner_domain[n.node_id],
        )
        if state == HOLD:
            raise ReproofContractError(f"UNKNOWN_OWNER_TRANSITION:{n.node_id}")
        classes[n.node_id] = state
        if state == REPROVE:
            drift.add(n.node_id)
        elif state == REBIND:
            candidate_rebind.add(n.node_id)

    seeds = set(explicit) | drift
    recompute = graph.dependency_closed_descendants(seeds)
    recompute_set = set(recompute)
    rebind = tuple(x for x in graph.topo_order if x in candidate_rebind and x not in recompute_set)
    reuse = tuple(
        x
        for x in graph.topo_order
        if x not in recompute_set and x not in candidate_rebind
    )

    # Surviving evidence is validated differently by transition class:
    # EXACT evidence must already bind both proof-time and current generation.
    # REBIND evidence remains proof-time evidence and is carried only as an explicit
    # nonauthorizing rebind obligation bound to current_owner.surface_root.
    survivors = tuple(x for x in graph.topo_order if x not in recompute_set)
    for node_id in survivors:
        if node_id not in evidence:
            raise ReproofContractError(f"MISSING_SURVIVOR_EVIDENCE:{node_id}")
        ev = evidence[node_id]
        ev.validate_shape()
        node = graph.by_id[node_id]
        if ev.node_id != node_id:
            raise ReproofContractError(f"WITNESS_NODE_MISMATCH:{node_id}")
        if ev.graph_root != graph.graph_root:
            raise ReproofContractError(f"WITNESS_GRAPH_MISMATCH:{node_id}")
        if ev.witness_root != aw[node_id]:
            raise ReproofContractError(f"UNADMITTED_WITNESS:{node_id}")
        if ev.projection_root != owner_proj[node_id] or ev.projection_root != proof_proj[node_id]:
            raise ReproofContractError(f"PROJECTION_DRIFT:{node_id}")
        if ev.semantic_domain_root != owner_domain[node_id] or ev.semantic_domain_root != proof_domain[node_id]:
            raise ReproofContractError(f"SEMANTIC_DOMAIN_DRIFT:{node_id}")
        if ev.dependency_input_root != dependency_input_root(graph, node_id, evidence):
            raise ReproofContractError(f"DEPENDENCY_DETACHMENT:{node_id}")
        state = classes[node_id]
        if state == EXACT:
            if (
                ev.verifier_generation != admitted_gen[node.verifier_id]
                or ev.verifier_generation != owner_gen[node.verifier_id]
            ):
                raise ReproofContractError(f"VERIFIER_GENERATION_DRIFT:{node_id}")
        elif state == REBIND:
            if ev.verifier_generation != admitted_gen[node.verifier_id]:
                raise ReproofContractError(f"REBIND_PROOF_GENERATION_MISMATCH:{node_id}")
            if admitted_gen[node.verifier_id] == owner_gen[node.verifier_id]:
                raise ReproofContractError(f"SPURIOUS_REBIND:{node_id}")
        else:
            raise ReproofContractError(f"INVALID_SURVIVOR_CLASS:{node_id}:{state}")
        if not ev.d0 or ev.truth_authority or ev.effect_authority or ev.gate10:
            raise ReproofContractError(f"AUTHORITY_WIDENING:{node_id}")

    transition_classes = tuple((x, classes[x]) for x in graph.topo_order)
    body = {
        "graph_root": graph.graph_root,
        "explicit_changed_roots": explicit,
        "drift_seeds": tuple(x for x in graph.topo_order if x in drift),
        "rebind_nodes": rebind,
        "recompute_order": recompute,
        "reuse_nodes": reuse,
        "transition_classes": transition_classes,
        "admission_surface_root": admission.surface_root,
        "owner_surface_root": current_owner.surface_root,
        "authority_ceiling": "D0_EXTERNAL_AUTH_UNPROVEN",
    }
    return ReproofPlan(
        graph_root=graph.graph_root,
        explicit_changed_roots=explicit,
        drift_seeds=body["drift_seeds"],
        rebind_nodes=rebind,
        recompute_order=recompute,
        reuse_nodes=reuse,
        transition_classes=transition_classes,
        admission_surface_root=admission.surface_root,
        owner_surface_root=current_owner.surface_root,
        authority_ceiling=body["authority_ceiling"],
        plan_root=_digest(body),
    )


def omega8_admit(state: tuple[int, ...]) -> bool:
    return len(state) == 8 and tuple(state) == (2, 2, 2, 2, 2, 2, 2, 1)


def admit13(state: tuple[int, ...]) -> bool:
    return len(state) == 13 and tuple(state) == (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2)
