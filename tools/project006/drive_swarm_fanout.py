#!/usr/bin/env python3
"""Fail-closed physical swarm compiler for the Aura Drive -> provider bridge.

This module does not own Drive I/O, provider routing, authority, or durable replay state.
It compiles one already-authorized parent swarm request into role-distinct child command
envelopes that an installed host scheduler must persist and execute independently.

The key invariant is intentionally simple:

    requested target_size=N  =>  N distinct child commands/provider attempts

A single provider response that merely writes A+/B-/C0 sections is self-triangulation,
not a physical N-worker swarm.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

SWARM_SCHEMA = "AuraPhysicalSwarmEnvelopeV1"
ROLE_SCHEMA = "AuraPhysicalSwarmRoleV1"
CHILD_CONTEXT_SCHEMA = "AuraPhysicalChildContextV1"
MAX_TARGET_SIZE = 81


class SwarmFanoutError(ValueError):
    """Typed fail-closed swarm compilation failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _text(name: str, value: Any, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise SwarmFanoutError(f"INVALID_{name.upper()}")
    return value


def _target_size(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SwarmFanoutError("INVALID_TARGET_SIZE")
    if value < 1 or value > MAX_TARGET_SIZE:
        raise SwarmFanoutError("TARGET_SIZE_OUT_OF_RANGE")
    return value


def validate_parent_swarm(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise SwarmFanoutError("SWARM_NOT_OBJECT")
    if raw.get("schema") != SWARM_SCHEMA:
        raise SwarmFanoutError("UNSUPPORTED_SWARM_SCHEMA")
    parent_command_id = _text("parent_command_id", raw.get("parent_command_id"), 256)
    parent_idempotency_key = _text(
        "parent_idempotency_key", raw.get("parent_idempotency_key"), 256
    )
    target_size = _target_size(raw.get("target_size"))
    roles = raw.get("roles")
    if not isinstance(roles, Sequence) or isinstance(roles, (str, bytes)):
        raise SwarmFanoutError("INVALID_ROLES")
    if len(roles) != target_size:
        raise SwarmFanoutError("TARGET_SIZE_ROLE_COUNT_MISMATCH")

    normalized_roles: list[dict[str, str]] = []
    seen_role_ids: set[str] = set()
    seen_worker_ids: set[str] = set()
    for item in roles:
        if not isinstance(item, Mapping) or item.get("schema") != ROLE_SCHEMA:
            raise SwarmFanoutError("INVALID_ROLE")
        role_id = _text("role_id", item.get("role_id"), 128)
        worker_id = _text("worker_id", item.get("worker_id"), 256)
        objective_suffix = _text(
            "objective_suffix", item.get("objective_suffix"), 16_000
        )
        if role_id in seen_role_ids:
            raise SwarmFanoutError("DUPLICATE_ROLE_ID")
        if worker_id in seen_worker_ids:
            raise SwarmFanoutError("DUPLICATE_WORKER_ID")
        seen_role_ids.add(role_id)
        seen_worker_ids.add(worker_id)
        normalized_roles.append(
            {
                "role_id": role_id,
                "worker_id": worker_id,
                "objective_suffix": objective_suffix,
            }
        )

    base_command = raw.get("base_command")
    if not isinstance(base_command, Mapping):
        raise SwarmFanoutError("INVALID_BASE_COMMAND")
    if base_command.get("schema") != "AuraCommandEnvelopeV1-candidate":
        raise SwarmFanoutError("BASE_COMMAND_SCHEMA_MISMATCH")

    return {
        "schema": SWARM_SCHEMA,
        "parent_command_id": parent_command_id,
        "parent_idempotency_key": parent_idempotency_key,
        "target_size": target_size,
        "roles": normalized_roles,
        "base_command": dict(base_command),
    }


def compile_role_distinct_children(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Compile deterministic role-distinct child commands.

    Durable replay/dedup belongs to the host scheduler. These deterministic child IDs make
    that durable idempotency possible across restarts.
    """
    parent = validate_parent_swarm(raw)
    base = parent["base_command"]
    objective = base.get("objective")
    if not isinstance(objective, Mapping):
        raise SwarmFanoutError("BASE_OBJECTIVE_INVALID")
    base_text = _text("base_objective_text", objective.get("text"), 128_000)

    children: list[dict[str, Any]] = []
    for ordinal, role in enumerate(parent["roles"]):
        role_key = f"{ordinal}:{role['role_id']}:{role['worker_id']}"
        child_digest = hashlib.sha256(
            f"{parent['parent_idempotency_key']}|{role_key}".encode("utf-8")
        ).hexdigest()[:24]
        child_command_id = f"{parent['parent_command_id']}::{role['role_id']}::{child_digest}"
        child_idempotency_key = (
            f"{parent['parent_idempotency_key']}::{role['role_id']}::{child_digest}"
        )

        child = json.loads(json.dumps(base))
        child["command_id"] = child_command_id
        child["idempotency_key"] = child_idempotency_key
        child_objective = dict(objective)
        child_objective["text"] = (
            f"{base_text}\n\n"
            "PHYSICAL_SWARM_ROLE:\n"
            f"- role_id: {role['role_id']}\n"
            f"- worker_id: {role['worker_id']}\n"
            f"- ordinal: {ordinal}\n"
            "- independence: FIRST_PASS_NO_SIBLING_OUTPUTS\n"
            "- do not simulate or write the other swarm roles\n\n"
            f"ROLE_OBJECTIVE:\n{role['objective_suffix']}"
        )
        child["objective"] = child_objective
        child["_host_child_context"] = {
            "schema": CHILD_CONTEXT_SCHEMA,
            "parent_command_id": parent["parent_command_id"],
            "parent_idempotency_key": parent["parent_idempotency_key"],
            "target_size": parent["target_size"],
            "ordinal": ordinal,
            "role_id": role["role_id"],
            "worker_id": role["worker_id"],
            "child_command_id": child_command_id,
            "child_idempotency_key": child_idempotency_key,
        }
        children.append(child)

    if len({c["command_id"] for c in children}) != parent["target_size"]:
        raise SwarmFanoutError("CHILD_COMMAND_ID_COLLISION")
    if len({c["idempotency_key"] for c in children}) != parent["target_size"]:
        raise SwarmFanoutError("CHILD_IDEMPOTENCY_COLLISION")
    return children


def fanout_manifest(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return a receiptable compile manifest without executing provider calls."""
    parent = validate_parent_swarm(raw)
    children = compile_role_distinct_children(raw)
    return {
        "schema": "AuraPhysicalSwarmCompileReceiptV1",
        "parent_command_id": parent["parent_command_id"],
        "parent_idempotency_key": parent["parent_idempotency_key"],
        "target_size": parent["target_size"],
        "child_count": len(children),
        "child_refs": [
            {
                "command_id": child["command_id"],
                "idempotency_key": child["idempotency_key"],
                "role_id": child["_host_child_context"]["role_id"],
                "worker_id": child["_host_child_context"]["worker_id"],
                "ordinal": child["_host_child_context"]["ordinal"],
            }
            for child in children
        ],
        "manifest_digest": _digest(
            [
                (
                    child["command_id"],
                    child["idempotency_key"],
                    child["_host_child_context"]["role_id"],
                    child["_host_child_context"]["worker_id"],
                )
                for child in children
            ]
        ),
        "effect_started": False,
    }
