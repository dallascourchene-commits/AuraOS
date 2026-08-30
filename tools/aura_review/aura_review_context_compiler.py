from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

SCHEMA = "AffectedConeContextV2"
PRODUCTION = "PRODUCTION"
NONAUTHORITATIVE_FIXTURE = "NONAUTHORITATIVE_FIXTURE"
COORDINATE_BINDING_SCHEMA = "CoordinateLocatorBindingV2"
EDGE_TYPES = {
    "IMPORTS", "CALLS", "IMPLEMENTS", "READS", "WRITES", "DEPENDS_ON",
    "DEPENDED_BY", "MUST_NOT_AFFECT", "NEGATIVE_SPACE", "TEST_COVERS",
}
NEGATIVE_EDGE_TYPES = {"MUST_NOT_AFFECT", "NEGATIVE_SPACE"}


class ContextCompileRefusal(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextCompileRefusal(f"INVALID_{name.upper()}")
    return value.strip()


def _canonical(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(payload: object) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _norm_path(path: object) -> str:
    value = _text("path", path).replace("\\", "/")
    if value.startswith("/") or value.startswith("../") or "/../" in value or value == "..":
        raise ContextCompileRefusal("PATH_OUTSIDE_REPOSITORY", value)
    while "//" in value:
        value = value.replace("//", "/")
    return value


@dataclass(frozen=True)
class GraphEdgeV1:
    source: str
    target: str
    relation: str
    generation_ref: str
    source_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _norm_path(self.source))
        object.__setattr__(self, "target", _norm_path(self.target))
        relation = _text("relation", self.relation).upper()
        if relation not in EDGE_TYPES:
            raise ContextCompileRefusal("UNKNOWN_EDGE_RELATION", relation)
        object.__setattr__(self, "relation", relation)
        object.__setattr__(self, "generation_ref", _text("generation_ref", self.generation_ref))
        object.__setattr__(self, "source_ref", _text("source_ref", self.source_ref))


@dataclass(frozen=True)
class CoordinateLocatorV1:
    path: str
    coordinate: str
    coordinate_generation: str
    authority: bool = False
    currentness: bool = False
    source_truth: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _norm_path(self.path))
        object.__setattr__(self, "coordinate", _text("coordinate", self.coordinate))
        object.__setattr__(self, "coordinate_generation", _text("coordinate_generation", self.coordinate_generation))
        for field in ("authority", "currentness", "source_truth"):
            if not isinstance(getattr(self, field), bool):
                raise ContextCompileRefusal(f"INVALID_COORDINATE_{field.upper()}")
            if getattr(self, field):
                raise ContextCompileRefusal("COORDINATE_AUTHORITY_WIDENING", field)


@dataclass(frozen=True)
class ContextNodeV1:
    path: str
    required: bool
    distance: int
    reasons: tuple[str, ...]
    coordinates: tuple[str, ...] = ()
    coordinate_bindings: tuple[tuple[str, str], ...] = ()


def _direct_edge_reason(edge: GraphEdgeV1, changed: set[str]) -> tuple[str, str] | None:
    """Return the direct consequence of an edge touching the changed frontier."""
    if edge.relation in NEGATIVE_EDGE_TYPES:
        if edge.source in changed:
            return edge.target, edge.relation
        return None
    if edge.source in changed:
        return edge.target, f"OUTBOUND:{edge.relation}"
    if edge.target in changed:
        return edge.source, f"INBOUND:{edge.relation}"
    return None


def _coordinate_provenance_rows(nodes: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: dict[tuple[str, str], str] = {}
    for node in nodes:
        if not isinstance(node, Mapping):
            raise ContextCompileRefusal("INVALID_CONTEXT_NODE")
        path = _norm_path(node.get("path"))
        coordinates_raw = node.get("coordinates") or ()
        bindings_raw = node.get("coordinate_bindings") or ()
        if isinstance(coordinates_raw, str) or not isinstance(coordinates_raw, Sequence):
            raise ContextCompileRefusal("INVALID_COORDINATE_BINDINGS")
        if isinstance(bindings_raw, str) or not isinstance(bindings_raw, Sequence):
            raise ContextCompileRefusal("INVALID_COORDINATE_BINDINGS")
        coordinates = {_text("coordinate", value) for value in coordinates_raw}
        bound_coordinates: set[str] = set()
        for binding in bindings_raw:
            if (
                isinstance(binding, str)
                or not isinstance(binding, Sequence)
                or len(binding) != 2
            ):
                raise ContextCompileRefusal("INVALID_COORDINATE_BINDINGS")
            coordinate = _text("coordinate", binding[0])
            generation = _text("coordinate_generation", binding[1])
            key = (path, coordinate)
            if key in seen:
                if seen[key] != generation:
                    raise ContextCompileRefusal("COORDINATE_GENERATION_CONFLICT", f"{path}:{coordinate}")
                raise ContextCompileRefusal("COORDINATE_BINDING_DUPLICATE", f"{path}:{coordinate}")
            seen[key] = generation
            bound_coordinates.add(coordinate)
            rows.append(
                {
                    "path": path,
                    "coordinate": coordinate,
                    "coordinate_generation": generation,
                }
            )
        if coordinates != bound_coordinates:
            raise ContextCompileRefusal("COORDINATE_BINDING_COVERAGE_MISMATCH", path)
    return sorted(rows, key=lambda row: (row["path"], row["coordinate"], row["coordinate_generation"]))


def _validate_coordinate_provenance(context: Mapping[str, object]) -> None:
    if context.get("coordinate_locator_binding_schema") != COORDINATE_BINDING_SCHEMA:
        raise ContextCompileRefusal("COORDINATE_BINDING_SCHEMA_MISMATCH")
    nodes = context.get("nodes") or ()
    if isinstance(nodes, str) or not isinstance(nodes, Sequence):
        raise ContextCompileRefusal("INVALID_CONTEXT_NODES")
    rows = _coordinate_provenance_rows(nodes)
    count = context.get("coordinate_locator_count")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(rows):
        raise ContextCompileRefusal("COORDINATE_LOCATOR_COUNT_MISMATCH")
    claimed = _text(
        "coordinate_locator_generation_digest",
        context.get("coordinate_locator_generation_digest"),
    )
    if claimed != _digest(rows):
        raise ContextCompileRefusal("COORDINATE_GENERATION_DIGEST_MISMATCH")


def compile_affected_cone(
    *,
    repository: str,
    base_sha: str,
    head_sha: str,
    diff_digest: str,
    currentness_ref: str,
    source_generation_ref: str,
    codemap_generation_ref: str,
    workgraph_generation_ref: str,
    route_policy_ref: str,
    changed_paths: Sequence[str],
    code_graph_edges: Sequence[GraphEdgeV1],
    workgraph_edges: Sequence[GraphEdgeV1],
    coordinate_locators: Sequence[CoordinateLocatorV1] = (),
    expected_codemap_generation_ref: str | None = None,
    expected_workgraph_generation_ref: str | None = None,
    fixture_mode: bool = False,
    max_nodes: int = 64,
    optional_depth: int = 1,
) -> dict:
    bindings = {
        "repository": repository,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "diff_digest": diff_digest,
        "currentness_ref": currentness_ref,
        "source_generation_ref": source_generation_ref,
        "codemap_generation_ref": codemap_generation_ref,
        "workgraph_generation_ref": workgraph_generation_ref,
        "route_policy_ref": route_policy_ref,
    }
    bindings = {k: _text(k, v) for k, v in bindings.items()}
    if type(fixture_mode) is not bool:
        raise ContextCompileRefusal("INVALID_FIXTURE_MODE")
    mode = NONAUTHORITATIVE_FIXTURE if fixture_mode else PRODUCTION
    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes < 1:
        raise ContextCompileRefusal("INVALID_MAX_NODES")
    if isinstance(optional_depth, bool) or not isinstance(optional_depth, int) or optional_depth < 0:
        raise ContextCompileRefusal("INVALID_OPTIONAL_DEPTH")

    if not fixture_mode and (
        expected_codemap_generation_ref is None or expected_workgraph_generation_ref is None
    ):
        raise ContextCompileRefusal("CURRENTNESS_EVIDENCE_REQUIRED")
    if expected_codemap_generation_ref is not None:
        expected_codemap_generation_ref = _text(
            "expected_codemap_generation_ref", expected_codemap_generation_ref
        )
        if codemap_generation_ref != expected_codemap_generation_ref:
            raise ContextCompileRefusal("CODEMAP_GENERATION_STALE")
    if expected_workgraph_generation_ref is not None:
        expected_workgraph_generation_ref = _text(
            "expected_workgraph_generation_ref", expected_workgraph_generation_ref
        )
        if workgraph_generation_ref != expected_workgraph_generation_ref:
            raise ContextCompileRefusal("WORKGRAPH_GENERATION_STALE")

    changed = {_norm_path(p) for p in changed_paths}
    if not changed:
        raise ContextCompileRefusal("CHANGED_PATHS_REQUIRED")

    all_edges = tuple(code_graph_edges) + tuple(workgraph_edges)
    for edge in all_edges:
        if not isinstance(edge, GraphEdgeV1):
            raise ContextCompileRefusal("INVALID_GRAPH_EDGE")
    for edge in code_graph_edges:
        if edge.generation_ref != codemap_generation_ref:
            raise ContextCompileRefusal("CODEMAP_EDGE_GENERATION_MISMATCH", edge.source_ref)
    for edge in workgraph_edges:
        if edge.generation_ref != workgraph_generation_ref:
            raise ContextCompileRefusal("WORKGRAPH_EDGE_GENERATION_MISMATCH", edge.source_ref)

    locators: dict[str, dict[str, str]] = defaultdict(dict)
    for locator in coordinate_locators:
        if not isinstance(locator, CoordinateLocatorV1):
            raise ContextCompileRefusal("INVALID_COORDINATE_LOCATOR")
        existing = locators[locator.path].get(locator.coordinate)
        if existing is not None and existing != locator.coordinate_generation:
            raise ContextCompileRefusal(
                "COORDINATE_GENERATION_CONFLICT",
                f"{locator.path}:{locator.coordinate}",
            )
        locators[locator.path][locator.coordinate] = locator.coordinate_generation

    reasons: dict[str, set[str]] = {p: {"CHANGED_PATH"} for p in changed}
    distance: dict[str, int] = {p: 0 for p in changed}
    required: set[str] = set(changed)
    adjacency: dict[str, list[tuple[str, GraphEdgeV1]]] = defaultdict(list)

    for edge in all_edges:
        adjacency[edge.source].append((edge.target, edge))
        adjacency[edge.target].append((edge.source, edge))
        direct = _direct_edge_reason(edge, changed)
        if direct is None:
            continue
        node, why = direct
        reasons.setdefault(node, set()).add(why)
        distance[node] = min(distance.get(node, 999), 1)
        required.add(node)

    if len(required) > max_nodes:
        raise ContextCompileRefusal(
            "CONTEXT_BUDGET_INSUFFICIENT", f"required={len(required)} max_nodes={max_nodes}"
        )

    if optional_depth:
        queue = deque((p, 0) for p in sorted(required))
        seen_depth = {p: 0 for p in required}
        while queue:
            node, depth_now = queue.popleft()
            if depth_now >= optional_depth:
                continue
            for other, edge in sorted(
                adjacency.get(node, ()), key=lambda item: (item[0], item[1].relation)
            ):
                next_depth = depth_now + 1
                if other in required:
                    continue
                old = seen_depth.get(other)
                if old is not None and old <= next_depth:
                    continue
                seen_depth[other] = next_depth
                reasons.setdefault(other, set()).add(f"OPTIONAL:{edge.relation}:VIA:{node}")
                distance[other] = min(distance.get(other, 999), next_depth + 1)
                queue.append((other, next_depth))

    required_sorted = sorted(required)
    optional_sorted = sorted(
        (p for p in reasons if p not in required), key=lambda p: (distance.get(p, 999), p)
    )
    room = max_nodes - len(required_sorted)
    selected = required_sorted + optional_sorted[:room]
    omitted_optional = optional_sorted[room:]
    nodes = [
        ContextNodeV1(
            path=p,
            required=p in required,
            distance=distance.get(p, 0),
            reasons=tuple(sorted(reasons[p])),
            coordinates=tuple(sorted(locators.get(p, {}))),
            coordinate_bindings=tuple(
                sorted((coordinate, generation) for coordinate, generation in locators.get(p, {}).items())
            ),
        )
        for p in selected
    ]

    graph_refs = sorted(
        {
            edge.source_ref
            for edge in all_edges
            if edge.source in selected or edge.target in selected
        }
    )
    node_dicts = [asdict(node) for node in nodes]
    coordinate_rows = _coordinate_provenance_rows(node_dicts)
    body = {
        "schema": SCHEMA,
        "mode": mode,
        **bindings,
        "changed_paths": sorted(changed),
        "nodes": node_dicts,
        "required_node_count": len(required_sorted),
        "selected_node_count": len(nodes),
        "omitted_optional_paths": omitted_optional,
        "code_graph_refs": graph_refs,
        "coordinate_locator_binding_schema": COORDINATE_BINDING_SCHEMA,
        "coordinate_locator_count": len(coordinate_rows),
        "coordinate_locator_generation_digest": _digest(coordinate_rows),
        "coordinate_is_authority": False,
        "coordinate_is_currentness": False,
        "coordinate_is_source_truth": False,
        "context_budget_exhausted": bool(omitted_optional),
        "context_strategy": "MINIMUM_CONSEQUENCE_COMPLETE_REACHED_FRONTIER_V2_COORDGEN",
    }
    body["context_digest"] = _digest(body)
    return body


def project_review_capsule_inputs(context: Mapping[str, object]) -> dict:
    if not isinstance(context, Mapping) or context.get("schema") != SCHEMA:
        raise ContextCompileRefusal("INVALID_AFFECTED_CONE_CONTEXT")
    if context.get("mode") != PRODUCTION:
        raise ContextCompileRefusal("NONAUTHORITATIVE_FIXTURE_CONTEXT")
    _validate_coordinate_provenance(context)
    claimed_digest = _text("context_digest", context.get("context_digest"))
    body = dict(context)
    body.pop("context_digest", None)
    if claimed_digest != _digest(body):
        raise ContextCompileRefusal("AFFECTED_CONE_DIGEST_MISMATCH")
    return {
        "changed_paths": list(context.get("changed_paths") or ()),
        "code_graph_refs": list(context.get("code_graph_refs") or ()),
        "deterministic_receipt_refs": [f"affected-cone:{claimed_digest}"],
    }
