from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Iterable, Mapping

SCHEMA = 'AURA-EVIDENCE-SLICE-DAG-v2'
_HEX64 = re.compile(r'^[0-9a-f]{64}$')


class DagError(ValueError):
    pass


def canon(value) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise DagError('NON_CANONICAL') from exc


def digest(value) -> str:
    return sha256(canon(value)).hexdigest()


def _string(value, name: str) -> str:
    if type(value) is not str or not value:
        raise DagError(f'INVALID_STRING:{name}')
    return value


def _hex64(value, name: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise DagError(f'INVALID_HEX64:{name}')
    return value


def _string_tuple(values, name: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise DagError(f'INVALID_TUPLE:{name}')
    out=[]
    for value in values:
        out.append(_string(value, name))
    if len(set(out)) != len(out):
        raise DagError(f'DUPLICATE_VALUE:{name}')
    return tuple(sorted(out))


@dataclass(frozen=True)
class NodeSpec:
    node_id: str
    kind: str
    deps: tuple[str, ...]
    consequence_keys: tuple[str, ...]
    owner: str
    verifier_id: str

    def __post_init__(self):
        object.__setattr__(self, 'node_id', _string(self.node_id, 'node_id'))
        object.__setattr__(self, 'kind', _string(self.kind, 'kind'))
        object.__setattr__(self, 'owner', _string(self.owner, 'owner'))
        object.__setattr__(self, 'verifier_id', _string(self.verifier_id, 'verifier_id'))
        object.__setattr__(self, 'deps', _string_tuple(self.deps, 'deps'))
        object.__setattr__(self, 'consequence_keys', _string_tuple(self.consequence_keys, 'consequence_keys'))
        if self.node_id in self.deps:
            raise DagError('SELF_CYCLE')


@dataclass(frozen=True)
class Witness:
    node_id: str
    graph_root: str
    input_root: str
    output_root: str
    generation: str
    verifier_id: str
    verifier_generation: str
    upstream_receipt_root: str
    witness_root: str

    def __post_init__(self):
        _string(self.node_id, 'witness.node_id')
        _hex64(self.graph_root, 'witness.graph_root')
        _hex64(self.input_root, 'witness.input_root')
        _hex64(self.output_root, 'witness.output_root')
        _string(self.generation, 'witness.generation')
        _string(self.verifier_id, 'witness.verifier_id')
        _string(self.verifier_generation, 'witness.verifier_generation')
        _hex64(self.upstream_receipt_root, 'witness.upstream_receipt_root')
        _hex64(self.witness_root, 'witness.witness_root')


@dataclass(frozen=True)
class AdmissionSet:
    graph_root: str
    verifier_generations: tuple[tuple[str, str], ...]
    accepted_witness_roots: tuple[tuple[str, str], ...]
    observation_generation: str
    external_receipt_root: str

    def __post_init__(self):
        _hex64(self.graph_root, 'admission.graph_root')
        _string(self.observation_generation, 'admission.observation_generation')
        _hex64(self.external_receipt_root, 'admission.external_receipt_root')
        vg=[]
        seen=set()
        if type(self.verifier_generations) is not tuple:
            raise DagError('INVALID_TUPLE:verifier_generations')
        for item in self.verifier_generations:
            if type(item) is not tuple or len(item) != 2:
                raise DagError('INVALID_PAIR:verifier_generations')
            verifier_id=_string(item[0], 'verifier_id')
            generation=_string(item[1], 'verifier_generation')
            if verifier_id in seen:
                raise DagError('DUPLICATE_VERIFIER')
            seen.add(verifier_id); vg.append((verifier_id,generation))
        accepted=[]; seen_nodes=set()
        if type(self.accepted_witness_roots) is not tuple:
            raise DagError('INVALID_TUPLE:accepted_witness_roots')
        for item in self.accepted_witness_roots:
            if type(item) is not tuple or len(item) != 2:
                raise DagError('INVALID_PAIR:accepted_witness_roots')
            node_id=_string(item[0], 'accepted.node_id')
            root=_hex64(item[1], 'accepted.witness_root')
            if node_id in seen_nodes:
                raise DagError('DUPLICATE_ADMISSION_NODE')
            seen_nodes.add(node_id); accepted.append((node_id,root))
        object.__setattr__(self, 'verifier_generations', tuple(sorted(vg)))
        object.__setattr__(self, 'accepted_witness_roots', tuple(sorted(accepted)))

    @property
    def surface_root(self) -> str:
        return digest({
            'schema':'AURA-EXTERNAL-WITNESS-ADMISSION-v1',
            'graph_root':self.graph_root,
            'verifier_generations':self.verifier_generations,
            'accepted_witness_roots':self.accepted_witness_roots,
            'observation_generation':self.observation_generation,
            'external_receipt_root':self.external_receipt_root,
        })


@dataclass(frozen=True)
class RecomputePlan:
    changed_roots: tuple[str, ...]
    invalidated: tuple[str, ...]
    reusable: tuple[str, ...]
    recompute_order: tuple[str, ...]
    affected_consequence_keys: tuple[str, ...]
    admission_surface_root: str
    decision: str
    plan_root: str


def witness_body(w: Witness):
    return {
        'node_id':w.node_id,
        'graph_root':w.graph_root,
        'input_root':w.input_root,
        'output_root':w.output_root,
        'generation':w.generation,
        'verifier_id':w.verifier_id,
        'verifier_generation':w.verifier_generation,
        'upstream_receipt_root':w.upstream_receipt_root,
    }


def verify_witness_integrity(w: Witness) -> bool:
    return w.witness_root == digest(witness_body(w))


def dependency_input_root(deps: tuple[str, ...], witnesses: Mapping[str, Witness]) -> str:
    return digest([(node_id, witnesses[node_id].output_root) for node_id in sorted(deps)])


class EvidenceDag:
    def __init__(self, nodes: Iterable[NodeSpec]):
        nodes=tuple(nodes)
        if not nodes:
            raise DagError('EMPTY_DAG')
        self.nodes={}
        for node in nodes:
            if not isinstance(node, NodeSpec):
                raise DagError('INVALID_NODE_SPEC')
            if node.node_id in self.nodes:
                raise DagError('DUPLICATE_NODE')
            self.nodes[node.node_id]=node
        for node in self.nodes.values():
            for dep in node.deps:
                if dep not in self.nodes:
                    raise DagError(f'MISSING_DEP:{dep}')
        self.order=self._toposort()
        self.rev={key:set() for key in self.nodes}
        for node in self.nodes.values():
            for dep in node.deps:
                self.rev[dep].add(node.node_id)
        self.graph_root=digest({
            'schema':SCHEMA,
            'nodes':[
                {
                    'node_id':node.node_id,
                    'kind':node.kind,
                    'deps':node.deps,
                    'consequence_keys':node.consequence_keys,
                    'owner':node.owner,
                    'verifier_id':node.verifier_id,
                }
                for node in sorted(self.nodes.values(), key=lambda item:item.node_id)
            ],
        })

    def _toposort(self) -> tuple[str, ...]:
        temporary=set(); permanent=set(); out=[]
        def visit(node_id):
            if node_id in permanent:
                return
            if node_id in temporary:
                raise DagError('CYCLE')
            temporary.add(node_id)
            for dep in sorted(self.nodes[node_id].deps):
                visit(dep)
            temporary.remove(node_id); permanent.add(node_id); out.append(node_id)
        for node_id in sorted(self.nodes):
            visit(node_id)
        return tuple(out)

    def descendants(self, changed: Iterable[str]) -> set[str]:
        changed_items=tuple(changed)
        for node_id in changed_items:
            _string(node_id, 'changed_root')
            if node_id not in self.nodes:
                raise DagError(f'UNKNOWN_NODE:{node_id}')
        queue=list(sorted(set(changed_items))); seen=set()
        while queue:
            node_id=queue.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            queue.extend(sorted(self.rev[node_id]))
        return seen

    def compile_plan(self, changed: Iterable[str], witnesses: Mapping[str, Witness], admission: AdmissionSet) -> RecomputePlan:
        changed_items=tuple(changed)
        for node_id in changed_items:
            _string(node_id, 'changed_root')
        changed_roots=tuple(sorted(set(changed_items)))
        if not changed_roots:
            raise DagError('NO_CHANGE')
        if not isinstance(admission, AdmissionSet):
            raise DagError('MISSING_EXTERNAL_ADMISSION')
        if admission.graph_root != self.graph_root:
            raise DagError('ADMISSION_GRAPH_MISMATCH')
        for key in witnesses:
            _string(key, 'witness_map_key')
        if set(witnesses) != set(self.nodes):
            raise DagError('INCOMPLETE_WITNESS_SET')
        for node_id,witness in witnesses.items():
            if not isinstance(witness, Witness):
                raise DagError('INVALID_WITNESS')
            if witness.node_id != node_id:
                raise DagError('WITNESS_ID_MISMATCH')
            if witness.graph_root != self.graph_root:
                raise DagError(f'WITNESS_GRAPH_MISMATCH:{node_id}')
            if not verify_witness_integrity(witness):
                raise DagError(f'INVALID_WITNESS_ROOT:{node_id}')
        invalid=self.descendants(changed_roots)
        reusable=set(self.nodes)-invalid
        admitted=dict(admission.accepted_witness_roots)
        verifier_generations=dict(admission.verifier_generations)
        for node_id in sorted(reusable):
            witness=witnesses[node_id]
            spec=self.nodes[node_id]
            if admitted.get(node_id) != witness.witness_root:
                raise DagError(f'UNADMITTED_REUSE_WITNESS:{node_id}')
            if witness.verifier_id != spec.verifier_id:
                raise DagError(f'VERIFIER_ID_MISMATCH:{node_id}')
            if verifier_generations.get(witness.verifier_id) != witness.verifier_generation:
                raise DagError(f'VERIFIER_GENERATION_MISMATCH:{node_id}')
            if spec.deps:
                expected=dependency_input_root(spec.deps,witnesses)
                if witness.input_root != expected:
                    raise DagError(f'INVALID_DEPENDENCY_BINDING:{node_id}')
        for node_id in reusable:
            if any(dep in invalid for dep in self.nodes[node_id].deps):
                raise DagError('INVALID_REUSE_CUT')
        order=tuple(node_id for node_id in self.order if node_id in invalid)
        keys=tuple(sorted({key for node_id in invalid for key in self.nodes[node_id].consequence_keys}))
        decision='RECOMPUTE_MINIMUM_SLICE' if reusable else 'RECOMPUTE_ALL'
        body={
            'schema':SCHEMA,
            'graph_root':self.graph_root,
            'changed_roots':changed_roots,
            'invalidated':sorted(invalid),
            'reusable':sorted(reusable),
            'recompute_order':order,
            'affected_consequence_keys':keys,
            'admission_surface_root':admission.surface_root,
            'external_admission_receipt_root':admission.external_receipt_root,
            'admitted_reuse_roots':[(node_id,witnesses[node_id].witness_root) for node_id in sorted(reusable)],
            'authority':'D0',
            'gate10':False,
        }
        return RecomputePlan(changed_roots,tuple(sorted(invalid)),tuple(sorted(reusable)),order,keys,admission.surface_root,decision,digest(body))


def make_witness(*, node_id: str, graph_root: str, input_root: str, output_root: str, generation: str,
                 verifier_id: str, verifier_generation: str, upstream_receipt_root: str) -> Witness:
    provisional=Witness(
        node_id=node_id,
        graph_root=graph_root,
        input_root=input_root,
        output_root=output_root,
        generation=generation,
        verifier_id=verifier_id,
        verifier_generation=verifier_generation,
        upstream_receipt_root=upstream_receipt_root,
        witness_root='0'*64,
    )
    root=digest(witness_body(provisional))
    return Witness(**{**witness_body(provisional),'witness_root':root})


def demo_dag() -> EvidenceDag:
    return EvidenceDag([
        NodeSpec('source_raw','raw',(),('source',),'SOURCE_OWNER','AGENT09'),
        NodeSpec('trace_raw','raw',('source_raw',),('trace',),'TRACE_OWNER','AGENT09'),
        NodeSpec('workload_raw','raw',('source_raw',),('workload',),'WORKLOAD_OWNER','AGENT09'),
        NodeSpec('transfer_raw','raw',('trace_raw',),('transfer',),'TRANSFER_OWNER','AGENT09'),
        NodeSpec('source_receipt','receipt',('source_raw',),('source',),'AGENT09','AGENT09'),
        NodeSpec('trace_receipt','receipt',('source_receipt','trace_raw'),('trace',),'AGENT09','AGENT09'),
        NodeSpec('workload_receipt','receipt',('trace_receipt','source_receipt','workload_raw'),('workload',),'AGENT09','AGENT09'),
        NodeSpec('cost_receipt','receipt',('transfer_raw','trace_receipt'),('cost',),'AGENT09','AGENT09'),
        NodeSpec('composite','composite',('cost_receipt','workload_receipt','source_receipt','trace_receipt'),('admission',),'COMPOSITE_OWNER','AGENT09'),
    ])


def demo_witnesses(dag: EvidenceDag, verifier_generation='agent09-e68b9188') -> dict[str,Witness]:
    out={}
    upstream=digest({'fixture':'upstream-agent09-receipt'})
    for node_id in dag.order:
        spec=dag.nodes[node_id]
        inp=dependency_input_root(spec.deps,out) if spec.deps else digest({'raw':node_id,'v':1})
        output=digest({'node':node_id,'input':inp,'v':1})
        out[node_id]=make_witness(
            node_id=node_id,
            graph_root=dag.graph_root,
            input_root=inp,
            output_root=output,
            generation='g1',
            verifier_id=spec.verifier_id,
            verifier_generation=verifier_generation,
            upstream_receipt_root=upstream,
        )
    return out
