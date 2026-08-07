"""Verified Ephemeral Workspace V2 execution lifecycle.

This module is an additive companion to the one-shot Ephemeral Organ V1
runtime.  It compiles a verified PR1 ``EphemeralWorkspaceRecipe`` into a closed
execution graph, separates parse/bind/admit, executes only exact operational
adapter artifacts under a revocable lease, prepares proof-carrying domain
handoffs, and deterministically dissolves temporary state.

It grants no source mutation, domain, payment, deployment, publication, model,
professional, physical-work, or merge authority. Arbitrary native execution is
always denied; Wasmtime/WASI remains fail-closed until separately admitted.
"""
from __future__ import annotations

import copy
import math
import re
import time
from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aura_ephemeral_adapter_registry import OperationalAdapterRegistry
from aura_ephemeral_registry_store import EphemeralRegistryStore
from aura_ephemeral_sandbox import destroy_sandbox, prepare_sandbox, verify_dissolution
from aura_ephemeral_workspace_contracts import (
    MAX_CANONICAL_DEPTH,
    MAX_ITEMS,
    AuthorityEnvelope,
    EphemeralWorkspaceRecipe,
    canonical_json,
    stable_digest,
)

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
WORKSPACE_EXECUTION_GRAPH_V2 = "AURA_WORKSPACE_EXECUTION_GRAPH_V2"
SPATIAL_ACTION_CERTIFICATE_V2 = "AURA_SPATIAL_ACTION_CERTIFICATE_V2"
WORKSPACE_RUNTIME_V2 = "AURA_VERIFIED_EPHEMERAL_WORKSPACE_RUNTIME_V2"
MAX_GRAPH_NODES = 256
MAX_GRAPH_EDGES = 512
MAX_OUTPUT_BYTES = 4_000_000
MAX_CERTIFICATE_RECEIPTS = 4
MAX_JSON_ITEMS = 4096
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")

_SAFE_EFFECTS = frozenset({"read_only", "compute", "write_temp", "domain_handoff"})
_DENIED_EFFECTS = frozenset({
    "native", "arbitrary_native", "shell", "subprocess", "network", "device",
    "secret", "secret_access", "production_mutation", "deployment", "payment",
})
_CONSEQUENTIAL_EFFECTS = frozenset({"domain_handoff"})
_FAILURE_CLASSES = frozenset({
    "local", "upstream", "structural", "stale", "policy", "budget",
    "cancellation", "environment",
})
_STATES = frozenset({
    "ADMITTED", "ACTIVATING", "ACTIVE", "COMPLETING", "CANCELLING",
    "INVALIDATING", "FAILING", "EXPIRING", "DISSOLVING", "DISSOLVED",
})
_TERMINAL_PREP = frozenset({
    "COMPLETING", "CANCELLING", "INVALIDATING", "FAILING", "EXPIRING",
})
_CERT_TRANSITIONS = {
    "PREPARED": "OPEN",
    "OPEN": "APPROVED",
    "APPROVED": "EXECUTED",
    "EXECUTED": "CLOSED",
}


class _BudgetExceeded(ValueError):
    """Internal marker for runtime-owned resource budget exhaustion."""


# ---------------------------------------------------------------------------
# Bounded public-boundary helpers
# ---------------------------------------------------------------------------


def _exact_string(value: Any, name: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty exact string")
    if len(value.encode("utf-8")) > 4096:
        raise ValueError(f"{name} exceeds its byte ceiling")
    if pattern is not None and pattern.fullmatch(value) is None:
        raise ValueError(f"{name} has an invalid canonical spelling")
    return value


def _digest(value: Any, name: str) -> str:
    return _exact_string(value, name, pattern=_DIGEST)


def _integer(value: Any, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    return value


def _finite(value: Any, name: str, *, low: float = 0.0) -> float:
    if type(value) not in {int, float} or type(value) is bool:
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or result < low:
        raise ValueError(f"{name} must be a finite number >= {low}")
    return result


def _exact_mapping(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{name} must be an exact object")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{name} keys must be exact strings")
    return value


def _exact_sequence(value: Any, name: str, *, maximum: int = MAX_ITEMS) -> list[Any]:
    if type(value) not in {list, tuple}:
        raise ValueError(f"{name} must be an exact sequence")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds its item ceiling")
    return list(value)


def _detach_json(
    value: Any,
    *,
    name: str = "value",
    depth: int = 0,
    active: set[int] | None = None,
    counter: list[int] | None = None,
) -> Any:
    """Deep-detach hostile output with explicit depth/item/scalar ceilings."""
    if depth > MAX_CANONICAL_DEPTH:
        raise ValueError(f"{name} exceeds its nesting ceiling")
    if active is None:
        active = set()
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_JSON_ITEMS:
        raise ValueError(f"{name} exceeds its total item ceiling")
    if value is None or type(value) is bool or type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{name} contains a non-finite number")
        return value
    if type(value) is str:
        if len(value.encode("utf-8")) > 65_536:
            raise ValueError(f"{name} contains an oversized string")
        return value
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in active:
            raise ValueError(f"{name} contains a recursive object")
        active.add(marker)
        try:
            try:
                pairs = list(value.items())
            except Exception as exc:
                raise ValueError(f"{name} has an invalid mapping protocol") from exc
            if len(pairs) > MAX_ITEMS:
                raise ValueError(f"{name} exceeds its object item ceiling")
            result: dict[str, Any] = {}
            for item in pairs:
                try:
                    key, child = item
                except Exception as exc:
                    raise ValueError(f"{name} contains a malformed mapping entry") from exc
                if type(key) is not str or key in result:
                    raise ValueError(f"{name} keys must be unique exact strings")
                result[key] = _detach_json(
                    child, name=f"{name}.{key}", depth=depth + 1,
                    active=active, counter=counter,
                )
            return {key: result[key] for key in sorted(result)}
        finally:
            active.remove(marker)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        marker = id(value)
        if marker in active:
            raise ValueError(f"{name} contains a recursive sequence")
        active.add(marker)
        try:
            try:
                items = list(value)
            except Exception as exc:
                raise ValueError(f"{name} has an invalid sequence protocol") from exc
            if len(items) > MAX_ITEMS:
                raise ValueError(f"{name} exceeds its sequence item ceiling")
            return [
                _detach_json(item, name=f"{name}[{index}]", depth=depth + 1,
                             active=active, counter=counter)
                for index, item in enumerate(items)
            ]
        finally:
            active.remove(marker)
    raise ValueError(f"{name} contains a non-JSON value")


def _record_digest(record: Mapping[str, Any], field: str) -> str:
    body = copy.deepcopy(dict(record))
    body.pop(field, None)
    return stable_digest(body)


def _require_record_digest(record: Mapping[str, Any], field: str, name: str) -> None:
    expected = _record_digest(record, field)
    if record.get(field) != expected:
        raise ValueError(f"{name} digest does not match complete content")


def _recipe(value: Any) -> EphemeralWorkspaceRecipe:
    if type(value) is EphemeralWorkspaceRecipe:
        return value
    return EphemeralWorkspaceRecipe.from_dict(_exact_mapping(value, "recipe"))


def _authority() -> dict[str, Any]:
    return AuthorityEnvelope().to_dict()


def _require_closed_authority(value: Any, name: str) -> dict[str, Any]:
    detached = _detach_json(value, name=name)
    if detached != _authority():
        raise ValueError(f"{name} must equal the closed PR1 authority envelope")
    return detached


def _require_current_recipe(recipe: EphemeralWorkspaceRecipe, now: float | None = None) -> float:
    current = time.time() if now is None else _finite(now, "now")
    if current >= recipe.expires_at_epoch_seconds:
        raise ValueError("workspace recipe is expired")
    return current


# ---------------------------------------------------------------------------
# WorkspaceExecutionGraph compilation, parse, bind, admit
# ---------------------------------------------------------------------------


def _node_identity_body(node: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(node)
    body.pop("node_digest", None)
    return body


def _graph_identity_body(graph: Mapping[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(dict(graph))
    body.pop("graph_digest", None)
    body.pop("graph_id", None)
    return body


def compile_workspace_execution_graph_v2(
    recipe: EphemeralWorkspaceRecipe | Mapping[str, Any],
    *,
    adapter_bindings: Mapping[str, str],
    adapter_registry: OperationalAdapterRegistry,
    now: float | None = None,
) -> dict[str, Any]:
    """Compile a closed graph from an exact, current PR1 recipe."""
    value = _recipe(recipe)
    _require_current_recipe(value, now)
    if value.budgets.wall_time_ms < 1:
        raise ValueError("wall_time_ms must be at least 1 for executable workspaces")
    bindings = _exact_mapping(adapter_bindings, "adapter_bindings")
    if set(bindings) != set(value.capability_ids):
        raise ValueError("adapter_bindings must cover the complete recipe capability set")
    nodes: list[dict[str, Any]] = []
    for capability_id in value.capability_ids:
        adapter_id = _exact_string(bindings[capability_id], "adapter id", pattern=_ID)
        result = adapter_registry.get_binding(adapter_id)
        if not result.get("ok"):
            raise ValueError(result.get("error", "unknown adapter"))
        binding = _detach_json(result["binding"], name=f"binding.{adapter_id}")
        if binding["revocation_state"] != "ACTIVE":
            raise ValueError(f"adapter is revoked: {adapter_id}")
        if not adapter_registry.is_operational(adapter_id):
            raise ValueError(f"adapter is not operational: {adapter_id}")
        effect = _exact_string(binding["side_effect_class"], "side effect")
        if effect in _DENIED_EFFECTS or effect not in _SAFE_EFFECTS:
            raise ValueError(f"adapter effect is denied: {effect}")
        human_gate = binding["human_approval_policy"] == "required"
        if effect in _CONSEQUENTIAL_EFFECTS and not human_gate:
            raise ValueError(f"consequential adapter lacks a human gate: {adapter_id}")
        node = {
            "node_id": capability_id,
            "capability_id": capability_id,
            "adapter_id": adapter_id,
            "adapter_version": binding["version"],
            "adapter_digest": binding["adapter_digest"],
            "implementation_digest": binding["implementation_digest"],
            "input_schema_digest": binding["input_schema_digest"],
            "output_schema_digest": binding["output_schema_digest"],
            "effect_class": effect,
            "human_gate": human_gate,
            "terminal": False,
            "retry_limit": 0,
            "timeout_ms": min(value.budgets.wall_time_ms, 30_000),
            "assumptions_digest": stable_digest({"capability_id": capability_id, "recipe": value.recipe_digest}),
            "source_identity_digest": binding["implementation_digest"],
            "node_digest": "",
        }
        node["node_digest"] = stable_digest(_node_identity_body(node))
        nodes.append(node)
    edges = [
        {"source_node_id": edge.source_capability_id,
         "target_node_id": edge.target_capability_id}
        for edge in value.dependency_edges
    ]
    outgoing = {item["node_id"]: 0 for item in nodes}
    incoming = {item["node_id"]: 0 for item in nodes}
    for edge in edges:
        outgoing[edge["source_node_id"]] += 1
        incoming[edge["target_node_id"]] += 1
    terminals = sorted(node_id for node_id, count in outgoing.items() if count == 0)
    entries = sorted(node_id for node_id, count in incoming.items() if count == 0)
    for node in nodes:
        if node["node_id"] in terminals:
            node["terminal"] = True
            node["node_digest"] = stable_digest(_node_identity_body(node))
    graph: dict[str, Any] = {
        "version": WORKSPACE_EXECUTION_GRAPH_V2,
        "graph_id": "",
        "recipe_id": value.recipe_id,
        "recipe_digest": value.recipe_digest,
        "nodes": sorted(nodes, key=lambda item: item["node_id"]),
        "edges": sorted(edges, key=lambda item: (item["source_node_id"], item["target_node_id"])),
        "entry_node_ids": entries,
        "terminal_node_ids": terminals,
        "budgets": value.budgets.to_dict(),
        "issued_at_epoch_seconds": value.issued_at_epoch_seconds,
        "expires_at_epoch_seconds": value.expires_at_epoch_seconds,
        "max_parallelism": 1,
        "authority": _authority(),
        "arbitrary_native_execution": False,
        "graph_digest": "",
    }
    graph["graph_digest"] = stable_digest(_graph_identity_body(graph))
    graph["graph_id"] = f"workspace-graph:{graph['graph_digest'][:24]}"
    validate_workspace_execution_graph_v2(graph)
    return graph


def parse_workspace_execution_graph_v2(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Parse only exact bounded structure, spelling, and self-integrity."""
    graph = _detach_json(_exact_mapping(payload, "graph"), name="graph")
    expected = {
        "version", "graph_id", "recipe_id", "recipe_digest", "nodes", "edges",
        "entry_node_ids", "terminal_node_ids", "budgets", "issued_at_epoch_seconds",
        "expires_at_epoch_seconds", "max_parallelism", "authority",
        "arbitrary_native_execution", "graph_digest",
    }
    if set(graph) != expected:
        raise ValueError("graph fields are incomplete or unknown")
    if graph["version"] != WORKSPACE_EXECUTION_GRAPH_V2:
        raise ValueError("unsupported graph version")
    _exact_string(graph["graph_id"], "graph_id", pattern=_ID)
    _exact_string(graph["recipe_id"], "recipe_id", pattern=_ID)
    _digest(graph["recipe_digest"], "recipe_digest")
    _digest(graph["graph_digest"], "graph_digest")
    _require_closed_authority(graph["authority"], "graph.authority")
    if graph["arbitrary_native_execution"] is not False:
        raise ValueError("arbitrary native execution must remain denied")
    _integer(graph["max_parallelism"], "max_parallelism", 1, 16)
    _integer(graph["issued_at_epoch_seconds"], "issued_at", 1, 2**63 - 1)
    _integer(graph["expires_at_epoch_seconds"], "expires_at", 1, 2**63 - 1)
    if stable_digest(_graph_identity_body(graph)) != graph["graph_digest"]:
        raise ValueError("graph digest does not match complete behavior-defining content")
    expected_id = f"workspace-graph:{graph['graph_digest'][:24]}"
    if graph["graph_id"] != expected_id:
        raise ValueError("graph_id does not match graph digest")
    return graph


def validate_workspace_execution_graph_v2(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate graph, temporal, identity, effect, budget, and gate invariants."""
    graph = parse_workspace_execution_graph_v2(payload)
    nodes = _exact_sequence(graph["nodes"], "nodes", maximum=MAX_GRAPH_NODES)
    edges = _exact_sequence(graph["edges"], "edges", maximum=MAX_GRAPH_EDGES)
    if not nodes:
        raise ValueError("graph must contain nodes")
    node_map: dict[str, dict[str, Any]] = {}
    node_fields = {
        "node_id", "capability_id", "adapter_id", "adapter_version", "adapter_digest",
        "implementation_digest", "input_schema_digest", "output_schema_digest",
        "effect_class", "human_gate", "terminal", "retry_limit", "timeout_ms",
        "assumptions_digest", "source_identity_digest", "node_digest",
    }
    for raw in nodes:
        node = _exact_mapping(raw, "node")
        if set(node) != node_fields:
            raise ValueError("node fields are incomplete or unknown")
        node_id = _exact_string(node["node_id"], "node_id", pattern=_ID)
        if node_id in node_map:
            raise ValueError("duplicate graph node")
        if node["capability_id"] != node_id:
            raise ValueError("node and capability identity must match")
        for name in ("adapter_digest", "implementation_digest", "input_schema_digest",
                     "output_schema_digest", "assumptions_digest", "source_identity_digest",
                     "node_digest"):
            _digest(node[name], f"node.{name}")
        _exact_string(node["adapter_id"], "adapter_id", pattern=_ID)
        _exact_string(node["adapter_version"], "adapter_version")
        effect = _exact_string(node["effect_class"], "effect_class")
        if effect not in _SAFE_EFFECTS or effect in _DENIED_EFFECTS:
            raise ValueError("node effect is not admitted")
        if type(node["human_gate"]) is not bool or type(node["terminal"]) is not bool:
            raise ValueError("node gate/terminal fields must be booleans")
        if effect in _CONSEQUENTIAL_EFFECTS and node["human_gate"] is not True:
            raise ValueError("consequential node lacks human gate")
        _integer(node["retry_limit"], "retry_limit", 0, 8)
        _integer(node["timeout_ms"], "timeout_ms", 1, 300_000)
        if stable_digest(_node_identity_body(node)) != node["node_digest"]:
            raise ValueError("node digest does not match complete identity")
        node_map[node_id] = node
    adjacency = {node_id: [] for node_id in node_map}
    reverse = {node_id: [] for node_id in node_map}
    edge_seen: set[tuple[str, str]] = set()
    for raw in edges:
        edge = _exact_mapping(raw, "edge")
        if set(edge) != {"source_node_id", "target_node_id"}:
            raise ValueError("edge fields are incomplete or unknown")
        source = _exact_string(edge["source_node_id"], "edge source", pattern=_ID)
        target = _exact_string(edge["target_node_id"], "edge target", pattern=_ID)
        if source == target or source not in node_map or target not in node_map:
            raise ValueError("edge has invalid endpoints")
        if (source, target) in edge_seen:
            raise ValueError("duplicate graph edge")
        edge_seen.add((source, target))
        adjacency[source].append(target)
        reverse[target].append(source)
    queue = deque(sorted(node for node, parents in reverse.items() if not parents))
    visited: list[str] = []
    degree = {node: len(parents) for node, parents in reverse.items()}
    while queue:
        current = queue.popleft()
        visited.append(current)
        for target in sorted(adjacency[current]):
            degree[target] -= 1
            if degree[target] == 0:
                queue.append(target)
    if len(visited) != len(node_map):
        raise ValueError("graph contains a cycle")
    entries = sorted(node for node, parents in reverse.items() if not parents)
    terminals = sorted(node for node, children in adjacency.items() if not children)
    if graph["entry_node_ids"] != entries or graph["terminal_node_ids"] != terminals:
        raise ValueError("entry or terminal identity is incomplete")
    if any(node_map[node]["terminal"] != (node in terminals) for node in node_map):
        raise ValueError("node terminal flag is inconsistent")
    reachable: set[str] = set()
    todo = list(entries)
    while todo:
        current = todo.pop()
        if current in reachable:
            continue
        reachable.add(current)
        todo.extend(adjacency[current])
    if reachable != set(node_map):
        raise ValueError("graph contains an unreachable node")
    can_reach_terminal: set[str] = set(terminals)
    todo = list(terminals)
    while todo:
        current = todo.pop()
        for parent in reverse[current]:
            if parent not in can_reach_terminal:
                can_reach_terminal.add(parent)
                todo.append(parent)
    if can_reach_terminal != set(node_map):
        raise ValueError("graph contains a dead-end node")
    budgets = _exact_mapping(graph["budgets"], "budgets")
    expected_budget_fields = {
        "wall_time_ms", "memory_mb", "context_tokens", "output_bytes", "tool_calls",
        "model_calls", "cost_microusd", "network_calls", "device_events",
    }
    if set(budgets) != expected_budget_fields:
        raise ValueError("graph budgets are incomplete")
    for name, value in budgets.items():
        minimum = 1 if name == "wall_time_ms" else 0
        _integer(value, f"budget.{name}", minimum, 10_000_000_000)
    if budgets["model_calls"] != 0 or budgets["network_calls"] != 0:
        raise ValueError("PR2 graph cannot admit model or network calls")
    if graph["expires_at_epoch_seconds"] <= graph["issued_at_epoch_seconds"]:
        raise ValueError("graph lifetime is invalid")
    return graph


def bind_workspace_execution_graph_v2(
    graph: Mapping[str, Any],
    *,
    expected_recipe: EphemeralWorkspaceRecipe | Mapping[str, Any],
    expected_adapter_bindings: Mapping[str, str],
    adapter_registry: OperationalAdapterRegistry,
    now: float | None = None,
) -> dict[str, Any]:
    """Bind the complete graph to independently supplied current expectations."""
    parsed = validate_workspace_execution_graph_v2(graph)
    recipe = _recipe(expected_recipe)
    expected = compile_workspace_execution_graph_v2(
        recipe,
        adapter_bindings=expected_adapter_bindings,
        adapter_registry=adapter_registry,
        now=now,
    )
    if parsed != expected:
        raise ValueError("stale complete execution graph identity")
    if parsed["recipe_id"] != recipe.recipe_id or parsed["recipe_digest"] != recipe.recipe_digest:
        raise ValueError("graph is not bound to the expected recipe")
    return parsed


def _workspace_id(graph_digest: str, activation_nonce: str) -> str:
    return f"workspace:v2:{stable_digest({'graph_digest': graph_digest, 'nonce': activation_nonce})[:24]}"


def admit_workspace_v2(
    graph: Mapping[str, Any],
    *,
    expected_recipe: EphemeralWorkspaceRecipe | Mapping[str, Any],
    expected_adapter_bindings: Mapping[str, str],
    adapter_registry: OperationalAdapterRegistry,
    store: EphemeralRegistryStore,
    activation_nonce: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Admit a bound, current graph into the separate V2 registry."""
    current = time.time() if now is None else _finite(now, "now")
    nonce = _exact_string(activation_nonce, "activation_nonce", pattern=_ID)
    bound = bind_workspace_execution_graph_v2(
        graph,
        expected_recipe=expected_recipe,
        expected_adapter_bindings=expected_adapter_bindings,
        adapter_registry=adapter_registry,
        now=current,
    )
    if current >= bound["expires_at_epoch_seconds"]:
        raise ValueError("execution graph is expired")
    workspace_id = _workspace_id(bound["graph_digest"], nonce)
    result = store.register_workspace_v2({
        "workspace_id": workspace_id,
        "recipe_json": _recipe(expected_recipe).to_dict(),
        "recipe_digest": bound["recipe_digest"],
        "graph_json": bound,
        "graph_digest": bound["graph_digest"],
        "state": "ADMITTED",
        "created_at": current,
        "expires_at": bound["expires_at_epoch_seconds"],
        "activation_nonce": nonce,
        "usage_json": {"tool_calls": 0, "output_bytes": 0, "started_at": current},
    })
    if not result.get("ok"):
        return result
    return {"ok": True, "workspace_id": workspace_id, "state": "ADMITTED",
            "graph_digest": bound["graph_digest"],
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


# ---------------------------------------------------------------------------
# Lifecycle, execution, failure attribution, partial re-execution
# ---------------------------------------------------------------------------


def _workspace(store: EphemeralRegistryStore, workspace_id: str) -> dict[str, Any]:
    _exact_string(workspace_id, "workspace_id", pattern=_ID)
    result = store.get_workspace_v2(workspace_id)
    if not result.get("ok"):
        raise ValueError(result.get("error", "workspace not found"))
    record = result["workspace"]
    if record["state"] not in _STATES:
        raise ValueError("workspace has an invalid stored state")
    return record


def _node_maps(graph: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    nodes = {node["node_id"]: node for node in graph["nodes"]}
    parents = {node_id: [] for node_id in nodes}
    children = {node_id: [] for node_id in nodes}
    for edge in graph["edges"]:
        parents[edge["target_node_id"]].append(edge["source_node_id"])
        children[edge["source_node_id"]].append(edge["target_node_id"])
    return nodes, parents, children


def _failure_record(
    *,
    workspace_id: str,
    failure_class: str,
    reason: str,
    node_id: str = "",
    timestamp: float | None = None,
) -> dict[str, Any]:
    if failure_class not in _FAILURE_CLASSES:
        raise ValueError("unknown failure class")
    record = {
        "workspace_id": workspace_id,
        "node_id": node_id,
        "failure_class": failure_class,
        "reason": _exact_string(reason, "failure reason"),
        "timestamp": time.time() if timestamp is None else _finite(timestamp, "failure timestamp"),
        "failure_digest": "",
    }
    record["failure_digest"] = stable_digest({k: v for k, v in record.items() if k != "failure_digest"})
    return record


def _validate_temp_paths(value: Any, temp_dir: str, *, key: str = "") -> None:
    if isinstance(value, dict):
        for child_key, child in value.items():
            _validate_temp_paths(child, temp_dir, key=child_key)
        return
    if isinstance(value, list):
        for child in value:
            _validate_temp_paths(child, temp_dir, key=key)
        return
    if type(value) is not str:
        return
    path_keys = {"path", "temp_dir", "output_path", "artifact_path"}
    parts = [part for part in re.split(r"[\/]+", value) if part]
    windows_absolute = re.match(r"^(?:[A-Za-z]:[\/]|\\)", value) is not None
    candidate = Path(value)
    path_sensitive = key in path_keys or candidate.is_absolute() or windows_absolute or ".." in parts
    if not path_sensitive:
        return
    if windows_absolute and not candidate.is_absolute():
        raise ValueError("adapter output path escapes the workspace sandbox")
    root = Path(temp_dir).resolve()
    candidate = candidate if candidate.is_absolute() else root / candidate
    if candidate.is_symlink():
        raise ValueError("adapter output contains a symlink path")
    try:
        candidate.resolve().relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("adapter output path escapes the workspace sandbox") from exc

def _approval_valid(approval: Any, *, workspace_id: str, graph_digest: str, node_id: str) -> bool:
    if type(approval) is not dict:
        return False
    expected = {"workspace_id", "graph_digest", "node_id", "approved", "approval_digest"}
    if set(approval) != expected or approval.get("approved") is not True:
        return False
    body = dict(approval)
    supplied = body.pop("approval_digest", None)
    return bool(
        approval.get("workspace_id") == workspace_id
        and approval.get("graph_digest") == graph_digest
        and approval.get("node_id") == node_id
        and supplied == stable_digest(body)
    )


def build_human_gate_receipt_v2(*, workspace_id: str, graph_digest: str, node_id: str) -> dict[str, Any]:
    receipt = {
        "workspace_id": _exact_string(workspace_id, "workspace_id", pattern=_ID),
        "graph_digest": _digest(graph_digest, "graph_digest"),
        "node_id": _exact_string(node_id, "node_id", pattern=_ID),
        "approved": True,
        "approval_digest": "",
    }
    receipt["approval_digest"] = stable_digest({k: v for k, v in receipt.items() if k != "approval_digest"})
    return receipt


def _adapter_bindings_current(
    graph: Mapping[str, Any], adapter_registry: OperationalAdapterRegistry
) -> None:
    for node in graph["nodes"]:
        result = adapter_registry.get_binding(node["adapter_id"])
        if not result.get("ok") or result["binding"] != {
            "identity_version": result.get("binding", {}).get("identity_version"),
            "adapter_id": node["adapter_id"],
            "version": node["adapter_version"],
            "adapter_digest": node["adapter_digest"],
            "implementation_digest": node["implementation_digest"],
            "input_schema_digest": node["input_schema_digest"],
            "output_schema_digest": node["output_schema_digest"],
            "side_effect_class": node["effect_class"],
            "human_approval_policy": "required" if node["human_gate"] else "not_required",
            "host_compatibility": result.get("binding", {}).get("host_compatibility"),
            "rollback_ref": result.get("binding", {}).get("rollback_ref"),
            "revocation_state": "ACTIVE",
        }:
            raise ValueError(f"stale or revoked adapter binding: {node['adapter_id']}")
        if not adapter_registry.is_operational(node["adapter_id"]):
            raise ValueError(f"adapter is no longer operational: {node['adapter_id']}")


def _cleanup_workspace_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    reason: str,
) -> dict[str, Any]:
    record = _workspace(store, workspace_id)
    if record["state"] == "DISSOLVED":
        receipt = dict(record.get("cleanup_receipt", {}))
        return {"ok": bool(receipt.get("cleanup_verified", True)), **receipt, "state": "DISSOLVED"}
    if record["state"] != "DISSOLVING":
        moved = store.transition_workspace_v2(workspace_id, record["state"], "DISSOLVING",
                                              terminal_reason=reason)
        if not moved.get("ok"):
            record = _workspace(store, workspace_id)
            if record["state"] == "DISSOLVED":
                receipt = dict(record.get("cleanup_receipt", {}))
                return {"ok": bool(receipt.get("cleanup_verified", True)), **receipt,
                        "state": "DISSOLVED"}
            if record["state"] != "DISSOLVING":
                raise ValueError("workspace cleanup lost its state race")
        else:
            record = _workspace(store, workspace_id)
    lease = store.revoke_workspace_v2_lease(workspace_id, reason=reason)
    temp_dir = record.get("sandbox_path", "")
    if temp_dir:
        destroy_sandbox(temp_dir)
    verified = verify_dissolution(temp_dir, lease.get("ok", False))
    receipt = {
        "workspace_id": workspace_id,
        "reason": reason,
        "lease_revoked": bool(lease.get("ok")),
        "temp_dir_removed": bool(verified.get("temp_dir_removed")),
        "cleanup_verified": bool(verified.get("ok")),
        "cleaned_at": time.time(),
        "cleanup_digest": "",
    }
    receipt["cleanup_digest"] = stable_digest({k: v for k, v in receipt.items() if k != "cleanup_digest"})
    store.update_workspace_v2(workspace_id, cleanup_receipt=receipt)
    if not receipt["cleanup_verified"]:
        return {"ok": False, **receipt, "state": "DISSOLVING"}
    moved = store.transition_workspace_v2(workspace_id, "DISSOLVING", "DISSOLVED",
                                          terminal_reason=reason)
    if not moved.get("ok"):
        current = _workspace(store, workspace_id)
        if current["state"] == "DISSOLVED":
            final_receipt = dict(current.get("cleanup_receipt", receipt))
            return {"ok": bool(final_receipt.get("cleanup_verified", True)), **final_receipt,
                    "state": "DISSOLVED"}
        raise ValueError("workspace cleanup could not finalize dissolution")
    return {"ok": True, **receipt, "state": "DISSOLVED"}

def _expire_if_needed(workspace_id: str, *, store: EphemeralRegistryStore, now: float | None = None) -> None:
    record = _workspace(store, workspace_id)
    current = time.time() if now is None else _finite(now, "now")
    if current < record["expires_at"] or record["state"] == "DISSOLVED":
        return
    failures = list(record["failure_records"])
    failures.append(_failure_record(
        workspace_id=workspace_id, failure_class="stale", reason="workspace TTL expired",
        timestamp=current,
    ))
    store.update_workspace_v2(workspace_id, failure_records=failures)
    if record["state"] != "EXPIRING":
        moved = store.transition_workspace_v2(workspace_id, record["state"], "EXPIRING",
                                              terminal_reason="ttl_expired")
        if not moved.get("ok"):
            raise ValueError("workspace expiry lost its state race")
    _cleanup_workspace_v2(workspace_id, store=store, reason="ttl_expired")
    raise ValueError("workspace is expired and dissolved")


def activate_workspace_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    adapter_registry: OperationalAdapterRegistry,
    repo_root: str = ".",
    now: float | None = None,
) -> dict[str, Any]:
    """Activate one admitted graph; every failure path attempts cleanup."""
    _expire_if_needed(workspace_id, store=store, now=now)
    record = _workspace(store, workspace_id)
    if record["state"] != "ADMITTED":
        return {"ok": False, "error": "duplicate_or_invalid_activation", "state": record["state"]}
    moved = store.transition_workspace_v2(workspace_id, "ADMITTED", "ACTIVATING")
    if not moved.get("ok"):
        return moved
    try:
        graph = validate_workspace_execution_graph_v2(record["graph_json"])
        _adapter_bindings_current(graph, adapter_registry)
        sandbox = prepare_sandbox(
            {"organ_id": workspace_id.replace(":", "-"), "resource_budget": graph["budgets"]},
            repo_root=repo_root,
        )
        if not sandbox.get("ok"):
            raise ValueError(sandbox.get("error", "sandbox preparation failed"))
        store.update_workspace_v2(workspace_id, sandbox_path=sandbox["temp_dir"])
        moved = store.transition_workspace_v2(workspace_id, "ACTIVATING", "ACTIVE")
        if not moved.get("ok"):
            raise ValueError("activation lost its lifecycle state race")
        return {"ok": True, "workspace_id": workspace_id, "state": "ACTIVE",
                "sandbox_mode": sandbox.get("receipt", {}).get("sandbox_mode", "builtin_only"),
                "arbitrary_native_execution": False,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except BaseException as original:
        try:
            current = _workspace(store, workspace_id)
            failures = list(current["failure_records"])
            failures.append(_failure_record(
                workspace_id=workspace_id,
                failure_class="environment" if not isinstance(original, ValueError) else "structural",
                reason=f"activation failed: {type(original).__name__}: {original}",
            ))
            store.update_workspace_v2(workspace_id, failure_records=failures)
            if current["state"] != "FAILING":
                store.transition_workspace_v2(workspace_id, current["state"], "FAILING",
                                              terminal_reason="activation_failed")
            _cleanup_workspace_v2(workspace_id, store=store, reason="activation_failed")
        except BaseException as cleanup_error:
            raise cleanup_error from original
        if isinstance(original, Exception):
            return {"ok": False, "error": f"activation_failed: {type(original).__name__}: {original}",
                    "workspace_id": workspace_id, "state": "DISSOLVED"}
        raise


def workspace_status_v2(workspace_id: str, *, store: EphemeralRegistryStore) -> dict[str, Any]:
    record = _workspace(store, workspace_id)
    return {"ok": True, "workspace": record,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def _ready_node_ids(record: Mapping[str, Any]) -> list[str]:
    graph = record["graph_json"]
    nodes, parents, _ = _node_maps(graph)
    receipts = record["node_receipts"]
    ready = []
    for node_id in sorted(nodes):
        if node_id in receipts:
            continue
        if all(receipts.get(parent, {}).get("status") == "VERIFIED" for parent in parents[node_id]):
            ready.append(node_id)
    return ready


def execute_workspace_node_v2(
    workspace_id: str,
    node_id: str,
    *,
    params: Mapping[str, Any],
    store: EphemeralRegistryStore,
    adapter_registry: OperationalAdapterRegistry,
    human_gate_receipt: Mapping[str, Any] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Execute one dependency-ready node and persist an exact receipt."""
    _expire_if_needed(workspace_id, store=store, now=now)
    record = _workspace(store, workspace_id)
    if record["state"] != "ACTIVE":
        return {"ok": False, "error": f"workspace_not_active: {record['state']}"}
    if not store.is_workspace_v2_lease_active(workspace_id, now=now):
        return {"ok": False, "error": "workspace_lease_revoked"}
    graph = validate_workspace_execution_graph_v2(record["graph_json"])
    try:
        _adapter_bindings_current(graph, adapter_registry)
    except Exception as exc:
        return _fail_workspace_v2(
            workspace_id, store=store, failure_class="stale",
            reason=f"adapter binding invalidated: {type(exc).__name__}: {exc}",
        )
    nodes, parents, _ = _node_maps(graph)
    node_key = _exact_string(node_id, "node_id", pattern=_ID)
    if node_key not in nodes:
        raise ValueError("unknown graph node")
    node = nodes[node_key]
    expected_receipts = dict(record["node_receipts"])
    receipts = dict(expected_receipts)
    if node_key in receipts:
        return {"ok": False, "error": "node_already_executed", "receipt": receipts[node_key]}
    missing = [parent for parent in parents[node_key]
               if receipts.get(parent, {}).get("status") != "VERIFIED"]
    if missing:
        return {"ok": False, "error": "upstream_receipts_missing", "missing": sorted(missing)}
    if node["human_gate"] and not _approval_valid(
        human_gate_receipt, workspace_id=workspace_id,
        graph_digest=graph["graph_digest"], node_id=node_key,
    ):
        return {"ok": False, "error": "human_gate_required", "node_id": node_key}
    clean_params = _detach_json(_exact_mapping(params, "params"), name="params")
    expected_usage = dict(record["usage_json"])
    usage = dict(expected_usage)
    if usage.get("tool_calls", 0) >= graph["budgets"]["tool_calls"]:
        return _fail_workspace_v2(
            workspace_id, store=store, failure_class="budget",
            reason="tool call budget exhausted", node_id=node_key,
        )
    started = time.time() if now is None else _finite(now, "now")
    upstream_digests = [receipts[parent]["receipt_digest"] for parent in sorted(parents[node_key])]
    try:
        raw = adapter_registry.execute(
            node["adapter_id"], params=clean_params,
            lease_active=store.is_workspace_v2_lease_active(workspace_id, now=started),
        )
        output = _detach_json(raw, name="adapter_result")
        encoded_size = len(canonical_json(output).encode("utf-8"))
        if encoded_size > min(graph["budgets"]["output_bytes"], MAX_OUTPUT_BYTES):
            raise _BudgetExceeded("adapter result exceeds output budget")
        _validate_temp_paths(output, record["sandbox_path"])
        if output.get("adapter_digest") != node["adapter_digest"] \
                or output.get("implementation_digest") != node["implementation_digest"]:
            raise ValueError("adapter result identity does not match admitted node")
        if output.get("ok") is False:
            reason = _exact_string(str(output.get("error", "adapter failed")), "adapter failure")
            category = output.get("failure_class", "local")
            category = category if category in _FAILURE_CLASSES else "local"
            return _fail_workspace_v2(
                workspace_id, store=store, failure_class=category,
                reason=reason, node_id=node_key,
            )
        completed = time.time()
        receipt = {
            "workspace_id": workspace_id,
            "graph_digest": graph["graph_digest"],
            "node_id": node_key,
            "node_digest": node["node_digest"],
            "adapter_digest": node["adapter_digest"],
            "implementation_digest": node["implementation_digest"],
            "input_digest": stable_digest(clean_params),
            "upstream_receipt_digests": upstream_digests,
            "assumptions_digest": node["assumptions_digest"],
            "source_identity_digest": node["source_identity_digest"],
            "output": output,
            "output_digest": stable_digest(output),
            "started_at": started,
            "completed_at": completed,
            "status": "VERIFIED",
            "receipt_digest": "",
        }
        receipt["receipt_digest"] = stable_digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
        receipts[node_key] = receipt
        usage["tool_calls"] = usage.get("tool_calls", 0) + 1
        usage["output_bytes"] = usage.get("output_bytes", 0) + encoded_size
        if usage["output_bytes"] > graph["budgets"]["output_bytes"]:
            return _fail_workspace_v2(
                workspace_id, store=store, failure_class="budget",
                reason="cumulative output budget exhausted", node_id=node_key,
            )
        committed = store.commit_workspace_v2_node_execution(
            workspace_id,
            expected_node_receipts=expected_receipts,
            expected_usage=expected_usage,
            node_receipts=receipts,
            usage_json=usage,
            now=completed,
        )
        if not committed.get("ok"):
            return {
                **committed,
                "ok": False,
                "node_id": node_key,
                "receipt_committed": False,
            }
        return {"ok": True, "workspace_id": workspace_id, "node_id": node_key,
                "receipt": receipt,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except BaseException as original:
        if isinstance(original, Exception):
            failure_class = "budget" if isinstance(original, _BudgetExceeded) else "structural"
            return _fail_workspace_v2(
                workspace_id, store=store, failure_class=failure_class,
                reason=f"node execution failed: {type(original).__name__}: {original}",
                node_id=node_key,
            )
        try:
            _fail_workspace_v2(
                workspace_id, store=store, failure_class="cancellation",
                reason=f"process interruption: {type(original).__name__}", node_id=node_key,
            )
        except BaseException as cleanup_error:
            raise cleanup_error from original
        raise


def execute_ready_wave_v2(
    workspace_id: str,
    *,
    params_by_node: Mapping[str, Mapping[str, Any]],
    store: EphemeralRegistryStore,
    adapter_registry: OperationalAdapterRegistry,
    human_gate_receipts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute one proven-independent topological wave in deterministic order."""
    record = _workspace(store, workspace_id)
    ready = _ready_node_ids(record)
    params_map = _exact_mapping(params_by_node, "params_by_node")
    gates = {} if human_gate_receipts is None else _exact_mapping(
        human_gate_receipts, "human_gate_receipts"
    )
    results = []
    for node_id in ready:
        result = execute_workspace_node_v2(
            workspace_id, node_id,
            params=params_map.get(node_id, {}), store=store,
            adapter_registry=adapter_registry,
            human_gate_receipt=gates.get(node_id),
        )
        results.append(result)
        if not result.get("ok"):
            break
    return {"ok": all(item.get("ok") for item in results),
            "workspace_id": workspace_id, "ready_node_ids": ready,
            "parallelism_proven": len(ready), "parallelism_used": 1,
            "results": results,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def _fail_workspace_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    failure_class: str,
    reason: str,
    node_id: str = "",
) -> dict[str, Any]:
    record = _workspace(store, workspace_id)
    failures = list(record["failure_records"])
    failure = _failure_record(
        workspace_id=workspace_id, failure_class=failure_class,
        reason=reason, node_id=node_id,
    )
    failures.append(failure)
    store.update_workspace_v2(workspace_id, failure_records=failures)
    current = _workspace(store, workspace_id)
    if current["state"] not in {"FAILING", "DISSOLVING", "DISSOLVED"}:
        store.transition_workspace_v2(workspace_id, current["state"], "FAILING",
                                      terminal_reason=reason)
    cleanup = _cleanup_workspace_v2(workspace_id, store=store, reason="failure")
    return {"ok": False, "error": reason, "failure": failure,
            "cleanup": cleanup, "state": cleanup.get("state", "DISSOLVING")}


def complete_workspace_v2(workspace_id: str, *, store: EphemeralRegistryStore) -> dict[str, Any]:
    _expire_if_needed(workspace_id, store=store)
    record = _workspace(store, workspace_id)
    if record["state"] != "ACTIVE":
        return {"ok": False, "error": f"workspace_not_active: {record['state']}"}
    graph = record["graph_json"]
    receipts = record["node_receipts"]
    missing = sorted(node["node_id"] for node in graph["nodes"]
                     if receipts.get(node["node_id"], {}).get("status") != "VERIFIED")
    if missing:
        return {"ok": False, "error": "workspace_graph_incomplete", "missing": missing}
    moved = store.transition_workspace_v2(workspace_id, "ACTIVE", "COMPLETING",
                                          terminal_reason="completed")
    if not moved.get("ok"):
        return moved
    cleanup = _cleanup_workspace_v2(workspace_id, store=store, reason="completed")
    return {"ok": bool(cleanup.get("ok")), "workspace_id": workspace_id,
            "state": cleanup.get("state"), "cleanup": cleanup,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def cancel_workspace_v2(workspace_id: str, *, store: EphemeralRegistryStore,
                        reason: str = "human_cancelled") -> dict[str, Any]:
    record = _workspace(store, workspace_id)
    if record["state"] == "DISSOLVED":
        return {"ok": False, "error": "workspace_already_dissolved"}
    if record["state"] in _TERMINAL_PREP or record["state"] == "DISSOLVING":
        terminal_reason = record.get("terminal_reason") or reason
        return _cleanup_workspace_v2(workspace_id, store=store, reason=terminal_reason)
    moved = store.transition_workspace_v2(workspace_id, record["state"], "CANCELLING",
                                          terminal_reason=reason)
    if not moved.get("ok"):
        return moved
    return _cleanup_workspace_v2(workspace_id, store=store, reason="cancelled")

def invalidate_workspace_v2(workspace_id: str, *, store: EphemeralRegistryStore,
                            reason: str) -> dict[str, Any]:
    _exact_string(reason, "invalidation reason")
    record = _workspace(store, workspace_id)
    if record["state"] == "DISSOLVED":
        return {"ok": False, "error": "workspace_already_dissolved"}
    failures = list(record["failure_records"])
    failures.append(_failure_record(
        workspace_id=workspace_id, failure_class="stale", reason=reason,
    ))
    store.update_workspace_v2(workspace_id, failure_records=failures)
    moved = store.transition_workspace_v2(workspace_id, record["state"], "INVALIDATING",
                                          terminal_reason=reason)
    if not moved.get("ok"):
        return moved
    return _cleanup_workspace_v2(workspace_id, store=store, reason="invalidated")


def dissolve_workspace_v2(workspace_id: str, *, store: EphemeralRegistryStore,
                          reason: str = "explicit_dissolution") -> dict[str, Any]:
    return _cleanup_workspace_v2(workspace_id, store=store, reason=reason)


def partial_reexecution_plan_v2(
    graph: Mapping[str, Any],
    *,
    prior_receipts: Mapping[str, Mapping[str, Any]],
    changed_node_ids: Sequence[str],
) -> dict[str, Any]:
    """Reuse only receipts whose full upstream identity closure is unchanged."""
    parsed = validate_workspace_execution_graph_v2(graph)
    receipts = _exact_mapping(prior_receipts, "prior_receipts")
    changed = set(_exact_sequence(changed_node_ids, "changed_node_ids"))
    nodes, parents, children = _node_maps(parsed)
    if not changed <= set(nodes):
        raise ValueError("changed_node_ids contains an unknown node")
    reexecute = set(changed)
    todo = list(changed)
    while todo:
        current = todo.pop()
        for child in children[current]:
            if child not in reexecute:
                reexecute.add(child)
                todo.append(child)
    reusable: list[str] = []
    for node_id in sorted(set(nodes) - reexecute):
        receipt = receipts.get(node_id)
        node = nodes[node_id]
        if type(receipt) is not dict:
            reexecute.add(node_id)
            continue
        expected_upstream = [
            receipts[parent].get("receipt_digest", "")
            for parent in sorted(parents[node_id])
            if type(receipts.get(parent)) is dict
        ]
        if (
            receipt.get("status") == "VERIFIED"
            and receipt.get("node_digest") == node["node_digest"]
            and receipt.get("adapter_digest") == node["adapter_digest"]
            and receipt.get("implementation_digest") == node["implementation_digest"]
            and receipt.get("assumptions_digest") == node["assumptions_digest"]
            and receipt.get("source_identity_digest") == node["source_identity_digest"]
            and receipt.get("upstream_receipt_digests") == expected_upstream
        ):
            reusable.append(node_id)
        else:
            reexecute.add(node_id)
    # If a newly invalid node has descendants, invalidate them too.
    todo = list(reexecute)
    while todo:
        current = todo.pop()
        for child in children[current]:
            if child not in reexecute:
                reexecute.add(child)
                todo.append(child)
    reusable = sorted(set(reusable) - reexecute)
    return {"ok": True, "graph_digest": parsed["graph_digest"],
            "reusable_node_ids": reusable, "reexecute_node_ids": sorted(reexecute),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


# ---------------------------------------------------------------------------
# SpatialActionCertificate preparation and owner-evidence closure
# ---------------------------------------------------------------------------


def _certificate_body(certificate: Mapping[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(dict(certificate))
    body.pop("certificate_digest", None)
    return body


def _certificate_identity_body(certificate: Mapping[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(dict(certificate))
    for name in ("certificate_id", "certificate_digest", "status", "receipts"):
        body.pop(name, None)
    return body


def _receipt(
    *,
    receipt_type: str,
    certificate_id: str,
    timestamp: float,
    evidence_digest: str,
    owner: str,
) -> dict[str, Any]:
    value = {
        "receipt_type": receipt_type,
        "certificate_id": certificate_id,
        "timestamp": timestamp,
        "evidence_digest": _digest(evidence_digest, "receipt evidence digest"),
        "owner": _exact_string(owner, "receipt owner", pattern=_ID),
        "receipt_digest": "",
    }
    value["receipt_digest"] = stable_digest({k: v for k, v in value.items() if k != "receipt_digest"})
    return value


def prepare_spatial_action_certificate_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    principal_id: str,
    requested_operation: str,
    subject_refs: Sequence[str],
    target_refs: Sequence[str],
    policy_digest: str,
    approval_class: str,
    runtime_environment_digest: str,
    effect_boundary: str,
    assumptions_digest: str,
    cost_microusd: int,
    reversible: bool,
    proof_obligations: Sequence[str],
    nonce: str,
    expires_at: float,
    now: float | None = None,
) -> dict[str, Any]:
    """Prepare a proposal-only certificate; no domain operation is authorized."""
    record = _workspace(store, workspace_id)
    if record["state"] != "ACTIVE":
        raise ValueError("action certificate requires an active workspace")
    if record["certificate_json"]:
        raise ValueError("workspace already has an action certificate")
    current = time.time() if now is None else _finite(now, "now")
    expiry = _finite(expires_at, "expires_at")
    if not current < expiry <= record["expires_at"]:
        raise ValueError("certificate expiry must be current and workspace-bounded")
    if type(reversible) is not bool:
        raise ValueError("reversible must be an exact boolean")
    subjects = sorted({_exact_string(v, "subject ref", pattern=_ID)
                       for v in _exact_sequence(subject_refs, "subject_refs")})
    targets = sorted({_exact_string(v, "target ref", pattern=_ID)
                      for v in _exact_sequence(target_refs, "target_refs")})
    obligations = sorted({_exact_string(v, "proof obligation", pattern=_ID)
                          for v in _exact_sequence(proof_obligations, "proof_obligations")})
    if not subjects or not targets or not obligations:
        raise ValueError("certificate subjects, targets, and proof obligations are required")
    certificate: dict[str, Any] = {
        "version": SPATIAL_ACTION_CERTIFICATE_V2,
        "certificate_id": "",
        "workspace_id": workspace_id,
        "graph_digest": record["graph_digest"],
        "principal_id": _exact_string(principal_id, "principal_id", pattern=_ID),
        "requested_operation": _exact_string(requested_operation, "requested_operation", pattern=_ID),
        "subject_refs": subjects,
        "target_refs": targets,
        "policy_digest": _digest(policy_digest, "policy_digest"),
        "approval_class": _exact_string(approval_class, "approval_class", pattern=_ID),
        "runtime_environment_digest": _digest(runtime_environment_digest, "runtime_environment_digest"),
        "effect_boundary": _exact_string(effect_boundary, "effect_boundary", pattern=_ID),
        "assumptions_digest": _digest(assumptions_digest, "assumptions_digest"),
        "cost_microusd": _integer(cost_microusd, "cost_microusd", 0, 10_000_000_000),
        "reversible": reversible,
        "proof_obligations": obligations,
        "nonce": _exact_string(nonce, "certificate nonce", pattern=_ID),
        "issued_at": current,
        "expires_at": expiry,
        "status": "PREPARED",
        "receipts": [],
        "authority": _authority(),
        "certificate_digest": "",
    }
    certificate["certificate_id"] = (
        f"spatial-action:{stable_digest(_certificate_identity_body(certificate))[:24]}"
    )
    certificate["certificate_digest"] = stable_digest(_certificate_body(certificate))
    validate_spatial_action_certificate_v2(certificate)
    committed = store.commit_workspace_v2_certificate(
        workspace_id,
        expected_certificate={},
        certificate=certificate,
        now=current,
    )
    if not committed.get("ok"):
        raise ValueError(committed.get("error", "action certificate state changed"))
    return {"ok": True, "certificate": certificate, "authorized": False,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def validate_spatial_action_certificate_v2(
    certificate: Mapping[str, Any],
    *,
    expected_certificate: Mapping[str, Any] | None = None,
    workspace_record: Mapping[str, Any] | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    value = _detach_json(_exact_mapping(certificate, "certificate"), name="certificate")
    expected_fields = {
        "version", "certificate_id", "workspace_id", "graph_digest", "principal_id",
        "requested_operation", "subject_refs", "target_refs", "policy_digest",
        "approval_class", "runtime_environment_digest", "effect_boundary",
        "assumptions_digest", "cost_microusd", "reversible", "proof_obligations",
        "nonce", "issued_at", "expires_at", "status", "receipts", "authority",
        "certificate_digest",
    }
    if set(value) != expected_fields or value["version"] != SPATIAL_ACTION_CERTIFICATE_V2:
        raise ValueError("certificate fields or version are invalid")
    _exact_string(value["certificate_id"], "certificate_id", pattern=_ID)
    _exact_string(value["workspace_id"], "workspace_id", pattern=_ID)
    for name in ("graph_digest", "policy_digest", "runtime_environment_digest",
                 "assumptions_digest", "certificate_digest"):
        _digest(value[name], name)
    _require_closed_authority(value["authority"], "certificate.authority")
    if value["status"] not in {"PREPARED", "OPEN", "APPROVED", "EXECUTED", "CLOSED"}:
        raise ValueError("unknown certificate status")
    receipts = _exact_sequence(value["receipts"], "certificate receipts",
                               maximum=MAX_CERTIFICATE_RECEIPTS)
    expected_types = ["OPEN", "APPROVAL", "EXECUTION", "OUTCOME"]
    required_count = {"PREPARED": 0, "OPEN": 1, "APPROVED": 2, "EXECUTED": 3, "CLOSED": 4}[value["status"]]
    if len(receipts) != required_count:
        raise ValueError("certificate receipt chain is incomplete or excessive")
    prior_time = value["issued_at"]
    for index, receipt in enumerate(receipts):
        raw = _exact_mapping(receipt, "certificate receipt")
        if set(raw) != {"receipt_type", "certificate_id", "timestamp", "evidence_digest", "owner", "receipt_digest"}:
            raise ValueError("certificate receipt fields are invalid")
        if raw["receipt_type"] != expected_types[index] or raw["certificate_id"] != value["certificate_id"]:
            raise ValueError("certificate receipt sequence or identity is invalid")
        timestamp = _finite(raw["timestamp"], "receipt timestamp")
        if timestamp < prior_time:
            raise ValueError("certificate receipt timestamps are not monotonic")
        prior_time = timestamp
        _digest(raw["evidence_digest"], "receipt evidence")
        _digest(raw["receipt_digest"], "receipt digest")
        _exact_string(raw["owner"], "receipt owner", pattern=_ID)
        _require_record_digest(raw, "receipt_digest", "certificate receipt")
    _finite(value["issued_at"], "issued_at")
    _finite(value["expires_at"], "expires_at")
    if value["expires_at"] <= value["issued_at"]:
        raise ValueError("certificate lifetime is invalid")
    if expected_certificate is not None:
        expected = _detach_json(_exact_mapping(expected_certificate, "expected_certificate"),
                                name="expected_certificate")
        if value != expected:
            raise ValueError("stale complete action certificate identity")
    if workspace_record is not None:
        record = _exact_mapping(workspace_record, "workspace_record")
        if value["workspace_id"] != record.get("workspace_id") \
                or value["graph_digest"] != record.get("graph_digest"):
            raise ValueError("certificate is not bound to the current workspace")
        if record.get("state") == "DISSOLVED" and value["status"] != "CLOSED":
            raise ValueError("open certificate cannot survive workspace dissolution")
    current = time.time() if now is None else _finite(now, "now")
    if current >= value["expires_at"] and value["status"] != "CLOSED":
        raise ValueError("action certificate is expired")
    if stable_digest(_certificate_body(value)) != value["certificate_digest"]:
        raise ValueError("certificate digest does not match the complete record")
    expected_id = f"spatial-action:{stable_digest(_certificate_identity_body(value))[:24]}"
    if value["certificate_id"] != expected_id:
        raise ValueError("certificate_id does not match immutable request identity")
    return value


def advance_spatial_action_certificate_v2(
    workspace_id: str,
    *,
    store: EphemeralRegistryStore,
    expected_status: str,
    evidence_digest: str,
    owner: str,
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Advance one exact receipt step under ACTIVE-state certificate CAS."""
    record = _workspace(store, workspace_id)
    if record["state"] != "ACTIVE":
        raise ValueError("action certificate advancement requires an active workspace")
    current = record["certificate_json"]
    if not current:
        raise ValueError("workspace has no action certificate")
    certificate = validate_spatial_action_certificate_v2(
        current, expected_certificate=current, workspace_record=record,
    )
    status = _exact_string(expected_status, "expected_status")
    owner_id = _exact_string(owner, "receipt owner", pattern=_ID)
    if certificate["status"] != status or status not in _CERT_TRANSITIONS:
        raise ValueError("stale or illegal certificate transition")
    next_status = _CERT_TRANSITIONS[status]
    receipt_type = {
        "PREPARED": "OPEN", "OPEN": "APPROVAL", "APPROVED": "EXECUTION",
        "EXECUTED": "OUTCOME",
    }[status]
    moment = time.time() if timestamp is None else _finite(timestamp, "timestamp")
    if moment >= certificate["expires_at"]:
        raise ValueError("certificate transition is expired")
    if certificate["receipts"] and moment < certificate["receipts"][-1]["timestamp"]:
        raise ValueError("certificate transition timestamp regressed")
    runtime_owners = {"spatial_runtime", "workspace_runtime"}
    if status in {"OPEN", "APPROVED"} and owner_id in runtime_owners:
        raise ValueError("spatial/runtime layer cannot self-authorize execution")
    if status == "EXECUTED" and owner_id in runtime_owners:
        raise ValueError("spatial/runtime layer cannot self-prove outcome")
    updated = copy.deepcopy(certificate)
    updated["status"] = next_status
    updated["receipts"].append(_receipt(
        receipt_type=receipt_type,
        certificate_id=certificate["certificate_id"],
        timestamp=moment,
        evidence_digest=evidence_digest,
        owner=owner_id,
    ))
    updated["certificate_digest"] = stable_digest(_certificate_body(updated))
    validate_spatial_action_certificate_v2(updated, workspace_record=record)
    committed = store.commit_workspace_v2_certificate(
        workspace_id,
        expected_certificate=certificate,
        certificate=updated,
        now=moment,
    )
    if not committed.get("ok"):
        raise ValueError(committed.get("error", "stale action certificate state"))
    return {"ok": True, "certificate": updated,
            "authorized": False,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

class WorkspaceSessionV2:
    """Context manager that guarantees cancellation cleanup on interruption."""

    def __init__(self, workspace_id: str, *, store: EphemeralRegistryStore) -> None:
        self.workspace_id = workspace_id
        self.store = store

    def __enter__(self) -> WorkspaceSessionV2:
        return self

    def __exit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> bool:
        if exc is not None:
            try:
                record = _workspace(self.store, self.workspace_id)
                if record["state"] != "DISSOLVED":
                    cancel_workspace_v2(
                        self.workspace_id, store=self.store,
                        reason=f"session_interrupted:{type(exc).__name__}",
                    )
            except BaseException as cleanup_error:
                raise cleanup_error from exc
        return False
