from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "AURA-AIRLLM-SECURITY-REPROOF-DAG-v1"
PLAN_SCHEMA = SCHEMA + "-PLAN"
AIRLLM_SECURITY_PARENT = "48fa74c2955f3574c4f8cf11514ff402d8b66434"
EVIDENCE_DAG_PARENT = "d6b41a8efd1001cfe60dd67811b3fc77cafde3f3"
BASE_SOURCE = "7a2c7a16f845752ffb7c16c68636d8d542ecd72e"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_GEN = re.compile(r"^[0-9a-f]{40}$")

class SecurityPlanError(ValueError):
    pass

class Decision(str, Enum):
    RECOMPUTE = "RECOMPUTE"
    REUSE_ALL = "REUSE_ALL"
    HOLD = "HOLD"


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise SecurityPlanError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canonical_json(value)).hexdigest()


def _sid(v: Any, label: str = "identity") -> str:
    if not isinstance(v, str) or _ID.fullmatch(v) is None:
        raise SecurityPlanError(f"MALFORMED_{label.upper()}")
    return v


def _sha(v: Any, label: str = "root") -> str:
    if not isinstance(v, str) or _SHA256.fullmatch(v) is None:
        raise SecurityPlanError(f"MALFORMED_{label.upper()}")
    return v


def _gen(v: Any, label: str = "generation") -> str:
    if not isinstance(v, str) or _GEN.fullmatch(v) is None:
        raise SecurityPlanError(f"MALFORMED_{label.upper()}")
    return v


@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    deps: tuple[str, ...]
    consequence_keys: tuple[str, ...]
    raw: bool = False

    def normalized(self) -> "NodeSpec":
        node_id = _sid(self.node_id, "node_id")
        if type(self.raw) is not bool:
            raise SecurityPlanError("MALFORMED_RAW_FLAG")
        deps = tuple(sorted({_sid(x, "dependency") for x in self.deps}))
        keys = tuple(sorted({_sid(x, "consequence_key") for x in self.consequence_keys}))
        if len(deps) != len(self.deps) or len(keys) != len(self.consequence_keys):
            raise SecurityPlanError("DUPLICATE_DEP_OR_KEY")
        if node_id in deps:
            raise SecurityPlanError("SELF_DEPENDENCY")
        return NodeSpec(node_id, deps, keys, self.raw)


@dataclass(frozen=True)
class Witness:
    node_id: str
    security_generation: str
    dag_generation: str
    graph_root: str
    output_root: str
    input_root: str
    verifier_root: str
    witness_root: str

    def canonical_without_root(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "-WITNESS",
            "node_id": self.node_id,
            "security_generation": self.security_generation,
            "dag_generation": self.dag_generation,
            "graph_root": self.graph_root,
            "output_root": self.output_root,
            "input_root": self.input_root,
            "verifier_root": self.verifier_root,
        }


@dataclass(frozen=True)
class ReproofPlan:
    schema: str
    decision: Decision
    graph_root: str
    changed: tuple[str, ...]
    recompute_order: tuple[str, ...]
    reusable: tuple[str, ...]
    consequence_keys: tuple[str, ...]
    parent_security_generation: str
    parent_dag_generation: str
    base_source: str
    d0: bool = True
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False
    plan_root: str = ""

    def payload_without_root(self) -> dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        d.pop("plan_root")
        return d

    def verify(self) -> bool:
        if self.schema != PLAN_SCHEMA or type(self.d0) is not bool or self.d0 is not True:
            return False
        if any(type(x) is not bool or x for x in (self.truth_authority, self.effect_authority, self.gate10)):
            return False
        try:
            _sha(self.graph_root, "graph_root")
            _gen(self.parent_security_generation, "security_generation")
            _gen(self.parent_dag_generation, "dag_generation")
            _gen(self.base_source, "base_source")
            _sha(self.plan_root, "plan_root")
            for x in self.changed + self.recompute_order + self.reusable + self.consequence_keys:
                _sid(x)
        except SecurityPlanError:
            return False
        return self.plan_root == digest(self.payload_without_root())


def airllm_security_nodes() -> tuple[NodeSpec, ...]:
    return (
        NodeSpec("MODEL_BYTES", (), ("MODEL_INTEGRITY",), True),
        NodeSpec("LOADER_SOURCE", (), ("LOADER_INTEGRITY",), True),
        NodeSpec("PACKAGE_MANIFEST", (), ("PACKAGE_INTEGRITY",), True),
        NodeSpec("TRACE_PROVENANCE", (), ("REUSE_PROVENANCE",), True),
        NodeSpec("WORKLOAD_ENV", (), ("REUSE_ENVIRONMENT",), True),
        NodeSpec("SAFETENSORS_STRUCTURE", ("MODEL_BYTES",), ("SERIALIZATION_SAFETY",)),
        NodeSpec("MODEL_ALLOWLIST", ("MODEL_BYTES",), ("MODEL_ALLOWLIST",)),
        NodeSpec("REMOTE_CODE_POLICY", ("LOADER_SOURCE", "PACKAGE_MANIFEST"), ("REMOTE_CODE_DENY",)),
        NodeSpec("NONDESTRUCTIVE_LOAD", ("LOADER_SOURCE",), ("LOAD_SIDE_EFFECT",)),
        NodeSpec(
            "SECURE_ENTRYPOINT",
            ("SAFETENSORS_STRUCTURE", "MODEL_ALLOWLIST", "LOADER_SOURCE", "PACKAGE_MANIFEST", "REMOTE_CODE_POLICY", "NONDESTRUCTIVE_LOAD"),
            ("AIRLLM_SECURITY_ADMISSION",),
        ),
        NodeSpec("SECURITY_RECEIPT", ("SECURE_ENTRYPOINT",), ("SECURITY_RECEIPT",)),
        NodeSpec("TRACE_WORKLOAD_REUSE", ("SECURITY_RECEIPT", "TRACE_PROVENANCE", "WORKLOAD_ENV"), ("SECURITY_PROOF_REUSE",)),
        NodeSpec("FINAL_REUSE_RECEIPT", ("TRACE_WORKLOAD_REUSE",), ("FINAL_REUSE_RECEIPT",)),
    )


def _normalize_nodes(nodes: Iterable[NodeSpec]) -> tuple[NodeSpec, ...]:
    materialized = tuple(n.normalized() for n in nodes)
    ids = [n.node_id for n in materialized]
    if len(ids) != len(set(ids)):
        raise SecurityPlanError("DUPLICATE_NODE")
    by = {n.node_id: n for n in materialized}
    for n in materialized:
        for dep in n.deps:
            if dep not in by:
                raise SecurityPlanError("MISSING_DEPENDENCY")
    temp: set[str] = set(); perm: set[str] = set()
    def visit(x: str) -> None:
        if x in perm: return
        if x in temp: raise SecurityPlanError("CYCLE")
        temp.add(x)
        for d in by[x].deps: visit(d)
        temp.remove(x); perm.add(x)
    for x in sorted(by): visit(x)
    return tuple(sorted(materialized, key=lambda n: n.node_id))


def graph_root(nodes: Iterable[NodeSpec]) -> str:
    ns = _normalize_nodes(nodes)
    return digest({"schema": SCHEMA + "-GRAPH", "nodes": [asdict(n) for n in ns]})

CANONICAL_GRAPH_ROOT = graph_root(airllm_security_nodes())


def dependency_input_root(node: NodeSpec, current_outputs: Mapping[str, str]) -> str:
    pairs = []
    for dep in node.deps:
        if dep not in current_outputs:
            raise SecurityPlanError("MISSING_CURRENT_DEPENDENCY_OUTPUT")
        pairs.append((dep, _sha(current_outputs[dep], "dependency_output_root")))
    return digest({"node": node.node_id, "dependencies": sorted(pairs)})


def make_witness(node: NodeSpec, output_root: str, current_outputs: Mapping[str, str], verifier_root: str,
                 *, security_generation: str = AIRLLM_SECURITY_PARENT, dag_generation: str = EVIDENCE_DAG_PARENT,
                 g_root: str = CANONICAL_GRAPH_ROOT) -> Witness:
    node = node.normalized()
    w = Witness(
        node.node_id,
        _gen(security_generation, "security_generation"),
        _gen(dag_generation, "dag_generation"),
        _sha(g_root, "graph_root"),
        _sha(output_root, "output_root"),
        dependency_input_root(node, current_outputs),
        _sha(verifier_root, "verifier_root"),
        "",
    )
    return Witness(**{**w.__dict__, "witness_root": digest(w.canonical_without_root())})


def verify_witness(w: Witness, node: NodeSpec, current_outputs: Mapping[str, str], expected_verifier_roots: Mapping[str, str]) -> bool:
    if type(w) is not Witness:
        return False
    try:
        node = node.normalized()
        if w.node_id != node.node_id:
            return False
        if w.security_generation != AIRLLM_SECURITY_PARENT or w.dag_generation != EVIDENCE_DAG_PARENT:
            return False
        if w.graph_root != CANONICAL_GRAPH_ROOT:
            return False
        if w.node_id not in current_outputs or w.node_id not in expected_verifier_roots:
            return False
        if _sha(current_outputs[w.node_id], "current_output_root") != w.output_root:
            return False
        if _sha(expected_verifier_roots[w.node_id], "expected_verifier_root") != w.verifier_root:
            return False
        if dependency_input_root(node, current_outputs) != w.input_root:
            return False
        _sha(w.witness_root, "witness_root")
    except SecurityPlanError:
        return False
    return w.witness_root == digest(w.canonical_without_root())


def _descendant_closure(by: Mapping[str, NodeSpec], changed: Sequence[str]) -> set[str]:
    rev: dict[str, set[str]] = {x: set() for x in by}
    for n in by.values():
        for d in n.deps: rev[d].add(n.node_id)
    out = set(changed); q = list(changed)
    while q:
        x = q.pop()
        for child in sorted(rev[x]):
            if child not in out:
                out.add(child); q.append(child)
    return out


def _topo_subset(by: Mapping[str, NodeSpec], subset: set[str]) -> tuple[str, ...]:
    seen: set[str] = set(); out: list[str] = []
    def visit(x: str) -> None:
        if x in seen: return
        for d in by[x].deps:
            if d in subset: visit(d)
        seen.add(x); out.append(x)
    for x in sorted(subset): visit(x)
    return tuple(out)


def compile_reproof_plan(changed: Iterable[str], witnesses: Mapping[str, Witness], current_outputs: Mapping[str, str],
                         expected_verifier_roots: Mapping[str, str], nodes: Iterable[NodeSpec] | None = None) -> ReproofPlan:
    ns = _normalize_nodes(airllm_security_nodes() if nodes is None else nodes)
    g = graph_root(ns)
    if g != CANONICAL_GRAPH_ROOT:
        raise SecurityPlanError("NONCANONICAL_SECURITY_GRAPH")
    by = {n.node_id: n for n in ns}
    changed_tuple = tuple(sorted({_sid(x, "changed_node") for x in changed}))
    if any(x not in by for x in changed_tuple):
        raise SecurityPlanError("UNKNOWN_CHANGED_NODE")
    if set(current_outputs) != set(by) or set(expected_verifier_roots) != set(by) or set(witnesses) != set(by):
        raise SecurityPlanError("INCOMPLETE_SECURITY_STATE")
    for k, v in current_outputs.items(): _sid(k); _sha(v, "current_output_root")
    for k, v in expected_verifier_roots.items(): _sid(k); _sha(v, "verifier_root")

    cone = _descendant_closure(by, changed_tuple)
    reusable = tuple(sorted(set(by) - cone))
    for node_id in reusable:
        if not verify_witness(witnesses[node_id], by[node_id], current_outputs, expected_verifier_roots):
            raise SecurityPlanError("INVALID_REUSABLE_WITNESS")

    order = _topo_subset(by, cone)
    keys = tuple(sorted({k for n in cone for k in by[n].consequence_keys}))
    decision = Decision.REUSE_ALL if not cone else Decision.RECOMPUTE
    p = ReproofPlan(PLAN_SCHEMA, decision, g, changed_tuple, order, reusable, keys,
                    AIRLLM_SECURITY_PARENT, EVIDENCE_DAG_PARENT, BASE_SOURCE)
    return ReproofPlan(**{**p.__dict__, "plan_root": digest(p.payload_without_root())})


def crystalline_admission(state8: Sequence[int]) -> bool:
    return len(state8) == 8 and all(type(x) is int and x == 2 for x in state8)


def admission_13d(state13: Sequence[int]) -> bool:
    if len(state13) != 13 or any(type(x) is not int or x not in (0, 1, 2) for x in state13):
        return False
    return crystalline_admission(state13[:8])

__all__ = [
    "SCHEMA", "PLAN_SCHEMA", "AIRLLM_SECURITY_PARENT", "EVIDENCE_DAG_PARENT", "BASE_SOURCE",
    "CANONICAL_GRAPH_ROOT", "SecurityPlanError", "Decision", "NodeSpec", "Witness", "ReproofPlan",
    "airllm_security_nodes", "graph_root", "dependency_input_root", "make_witness", "verify_witness",
    "compile_reproof_plan", "crystalline_admission", "admission_13d", "digest",
]
