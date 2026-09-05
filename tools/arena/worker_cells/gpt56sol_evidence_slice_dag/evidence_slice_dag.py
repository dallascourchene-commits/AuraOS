from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable, Mapping

SCHEMA = 'AURA-EVIDENCE-SLICE-DAG-v1'

class DagError(ValueError):
    pass

def canon(v) -> bytes:
    try:
        return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise DagError('NON_CANONICAL') from exc

def digest(v) -> str:
    return sha256(canon(v)).hexdigest()

@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    kind: str
    deps: tuple[str, ...]
    consequence_keys: tuple[str, ...]
    owner: str

    def __post_init__(self):
        if not self.node_id or not self.kind or not self.owner:
            raise DagError('INVALID_NODE')
        if len(set(self.deps)) != len(self.deps):
            raise DagError('DUPLICATE_DEP')
        if self.node_id in self.deps:
            raise DagError('SELF_CYCLE')
        if len(set(self.consequence_keys)) != len(self.consequence_keys):
            raise DagError('DUPLICATE_KEY')

@dataclass(frozen=True)
class Witness:
    node_id: str
    input_root: str
    output_root: str
    generation: str
    current: bool
    verified: bool
    d0: bool
    witness_root: str

def witness_body(w: Witness):
    return {'node_id': w.node_id, 'input_root': w.input_root, 'output_root': w.output_root,
            'generation': w.generation, 'current': w.current, 'verified': w.verified, 'd0': w.d0}

def verify_witness(w: Witness) -> bool:
    if type(w.current) is not bool or type(w.verified) is not bool or type(w.d0) is not bool:
        return False
    return w.witness_root == digest(witness_body(w))

@dataclass(frozen=True)
class RecomputePlan:
    changed_roots: tuple[str, ...]
    invalidated: tuple[str, ...]
    reusable: tuple[str, ...]
    recompute_order: tuple[str, ...]
    affected_consequence_keys: tuple[str, ...]
    decision: str
    plan_root: str

class EvidenceDag:
    def __init__(self, nodes: Iterable[NodeSpec]):
        nodes = tuple(nodes)
        self.nodes = {n.node_id: n for n in nodes}
        if not self.nodes:
            raise DagError('EMPTY_DAG')
        if len(self.nodes) != len(nodes):
            raise DagError('DUPLICATE_NODE')
        for n in self.nodes.values():
            for d in n.deps:
                if d not in self.nodes:
                    raise DagError(f'MISSING_DEP:{d}')
        self.order = self._toposort()
        self.rev = {k: set() for k in self.nodes}
        for n in self.nodes.values():
            for d in n.deps:
                self.rev[d].add(n.node_id)
        self.graph_root = digest({
            'schema': SCHEMA,
            'nodes': [
                {'node_id': n.node_id, 'kind': n.kind, 'deps': list(n.deps),
                 'consequence_keys': list(n.consequence_keys), 'owner': n.owner}
                for n in sorted(self.nodes.values(), key=lambda x: x.node_id)
            ]
        })

    def _toposort(self):
        temporary, permanent, out = set(), set(), []
        def visit(k):
            if k in permanent: return
            if k in temporary: raise DagError('CYCLE')
            temporary.add(k)
            for d in self.nodes[k].deps: visit(d)
            temporary.remove(k); permanent.add(k); out.append(k)
        for k in sorted(self.nodes): visit(k)
        return tuple(out)

    def descendants(self, changed: Iterable[str]) -> set[str]:
        q = list(changed); seen = set()
        for k in q:
            if k not in self.nodes: raise DagError(f'UNKNOWN_NODE:{k}')
        while q:
            k = q.pop()
            if k in seen: continue
            seen.add(k)
            q.extend(sorted(self.rev[k]))
        return seen

    def compile_plan(self, changed: Iterable[str], witnesses: Mapping[str, Witness]) -> RecomputePlan:
        changed = tuple(sorted(set(changed)))
        if not changed:
            raise DagError('NO_CHANGE')
        if set(witnesses) != set(self.nodes):
            raise DagError('INCOMPLETE_WITNESS_SET')
        for node_id, w in witnesses.items():
            if w.node_id != node_id:
                raise DagError('WITNESS_ID_MISMATCH')
            if not verify_witness(w):
                raise DagError(f'INVALID_WITNESS_ROOT:{node_id}')
        invalid = self.descendants(changed)
        reusable = set(self.nodes) - invalid
        for node_id in reusable:
            w = witnesses[node_id]
            if not (w.current and w.verified and w.d0):
                raise DagError(f'UNCURRENT_REUSE_WITNESS:{node_id}')
            deps = self.nodes[node_id].deps
            if deps:
                expected_input_root = digest([witnesses[d].output_root for d in deps])
                if w.input_root != expected_input_root:
                    raise DagError(f'INVALID_DEPENDENCY_BINDING:{node_id}')
        # A reusable node is lawful only if none of its transitive deps are invalid.
        # Descendant closure makes this true by construction; assert for tamper detection.
        for r in reusable:
            if any(d in invalid for d in self.nodes[r].deps):
                raise DagError('INVALID_REUSE_CUT')
        order = tuple(k for k in self.order if k in invalid)
        keys = tuple(sorted({key for k in invalid for key in self.nodes[k].consequence_keys}))
        decision = 'RECOMPUTE_MINIMUM_SLICE' if reusable else 'RECOMPUTE_ALL'
        body = {
            'schema': SCHEMA,
            'graph_root': self.graph_root,
            'changed_roots': changed,
            'invalidated': sorted(invalid),
            'reusable': sorted(reusable),
            'recompute_order': order,
            'affected_consequence_keys': keys,
            'decision': decision,
            'witness_roots': {k: witnesses[k].witness_root for k in sorted(witnesses)},
            'authority': 'D0', 'gate10': False,
        }
        return RecomputePlan(changed, tuple(sorted(invalid)), tuple(sorted(reusable)), order, keys, decision, digest(body))


def witness_for(node_id: str, input_root: str, output_root: str, generation='g1', current=True, verified=True, d0=True) -> Witness:
    if type(current) is not bool or type(verified) is not bool or type(d0) is not bool:
        raise DagError('INVALID_WITNESS_BOOL')
    provisional = Witness(node_id, input_root, output_root, generation, current, verified, d0, '')
    return Witness(node_id, input_root, output_root, generation, current, verified, d0, digest(witness_body(provisional)))


def demo_dag() -> EvidenceDag:
    return EvidenceDag([
        NodeSpec('source_raw','raw',(),('source',),'SOURCE_OWNER'),
        NodeSpec('trace_raw','raw',('source_raw',),('trace',),'TRACE_OWNER'),
        NodeSpec('workload_raw','raw',('source_raw',),('workload',),'WORKLOAD_OWNER'),
        NodeSpec('transfer_raw','raw',('trace_raw',),('transfer',),'TRANSFER_OWNER'),
        NodeSpec('source_receipt','receipt',('source_raw',),('source',),'AGENT09'),
        NodeSpec('trace_receipt','receipt',('source_receipt','trace_raw'),('trace',),'AGENT09'),
        NodeSpec('workload_receipt','receipt',('source_receipt','workload_raw','trace_receipt'),('workload',),'AGENT09'),
        NodeSpec('cost_receipt','receipt',('trace_receipt','transfer_raw'),('cost',),'AGENT09'),
        NodeSpec('composite','composite',('source_receipt','trace_receipt','workload_receipt','cost_receipt'),('admission',),'COMPOSITE_OWNER'),
    ])


def demo_witnesses(dag: EvidenceDag):
    out={}
    for i,k in enumerate(dag.order):
        n=dag.nodes[k]
        inp=digest([out[d].output_root for d in n.deps]) if n.deps else digest({'raw':k,'v':1})
        output=digest({'node':k,'input':inp,'v':1})
        out[k]=witness_for(k,inp,output)
    return out
