from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json


class TopologyDisposition(str, Enum):
    READY_POST_PROGRAM = "READY_POST_PROGRAM"
    HOLD_INVALID_PROGRAM = "HOLD_INVALID_PROGRAM"


Edge = tuple[str, str]


def norm_edge(edge: Edge) -> Edge:
    a, b = edge
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b or a == b:
        raise ValueError("invalid edge")
    return (a, b) if a < b else (b, a)


def edge_set(edges):
    return frozenset(norm_edge(edge) for edge in edges)


def graph_root(nodes, edges):
    raw = json.dumps(
        {"nodes": sorted(nodes), "edges": [list(edge) for edge in sorted(edge_set(edges))]},
        sort_keys=True, separators=(",", ":"),
    ).encode()
    return sha256(raw).hexdigest()


def components(nodes, edges):
    adjacency = {node: set() for node in nodes}
    for a, b in edge_set(edges):
        if a not in adjacency or b not in adjacency:
            raise ValueError("edge references unknown node")
        adjacency[a].add(b)
        adjacency[b].add(a)
    out = []
    seen = set()
    for root in sorted(nodes):
        if root in seen:
            continue
        stack = [root]
        seen.add(root)
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in sorted(adjacency[node]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        out.append(tuple(sorted(component)))
    return tuple(sorted(out))


@dataclass(frozen=True)
class ProbeStep:
    observed_edge: Edge
    add_edges: tuple[Edge, ...] = ()
    remove_edges: tuple[Edge, ...] = ()
    consume_observed_edge: bool = False


@dataclass(frozen=True)
class TopologyCertificate:
    disposition: TopologyDisposition
    pre_root: str
    program_root: str
    post_root: str
    post_partition: tuple[tuple[str, ...], ...]
    probes_executed: int
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def program_root(program):
    rows = []
    for step in program:
        rows.append({
            "observed": list(norm_edge(step.observed_edge)),
            "add": [list(norm_edge(edge)) for edge in step.add_edges],
            "remove": [list(norm_edge(edge)) for edge in step.remove_edges],
            "consume": step.consume_observed_edge,
        })
    return sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def execute_probe_program(nodes, edges, program):
    nodes = frozenset(nodes)
    current = set(edge_set(edges))
    pre_root = graph_root(nodes, current)
    for step in program:
        observed = norm_edge(step.observed_edge)
        for edge in step.remove_edges:
            current.discard(norm_edge(edge))
        if step.consume_observed_edge:
            current.discard(observed)
        for edge in step.add_edges:
            normalized = norm_edge(edge)
            if normalized[0] not in nodes or normalized[1] not in nodes:
                raise ValueError("program adds edge with unknown node")
            current.add(normalized)
    return TopologyCertificate(
        TopologyDisposition.READY_POST_PROGRAM,
        pre_root,
        program_root(program),
        graph_root(nodes, current),
        components(nodes, current),
        len(program),
    )
