"""Deep legacy-integrity checks for the P7 Coding Arena shadow adapter.

The checks in this module reconstruct immutable records produced by
``CodeArenaAdapter`` and ``build_refactor_arena``. They do not execute the
legacy workflow or mutate any input.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any

from aura_event_contracts import canonical_json

LIQUID_ARENA_VERSION = "AURA_LIQUID_PLANNING_ARENA_V1"
ACTION_CAPSULE_VERSION = "AURA_ACTION_CAPSULE_V1"
BOUNDARY_CONTRACT_VERSION = "AURA_BOUNDARY_CONTRACT_V1"
ARENA_LEASE_VERSION = "AURA_ARENA_LEASE_V1"

_CODE_DOMAIN_OBJECTS = (
    "files",
    "symbols",
    "diffs",
    "tests",
    "topology_deltas",
    "dream_usefulness_scores",
)
_ARENA_INVARIANT = (
    "models propose, Arena stages, Shadow critiques, Judge decides, "
    "verifier proves, human approves, ledger remembers"
)
_ALLOWED_ACTIONS = (
    "read leased files and CODEMAP context",
    "emit one bounded unified diff",
    "declare affected files, symbols, and tests",
    "emit BoundaryContract placeholders for external assumptions",
)
_FORBIDDEN_ACTIONS = (
    "mutate production files directly",
    "touch files outside leased regions",
    "write aura_incubator.py in live Architect mode",
    "invent behavior across a boundary without a BoundaryContract",
)
_BOUNDARY_ASSUMPTIONS = (
    "Only declared files and symbols may be changed.",
    "Neighbor files are read context unless explicitly leased.",
)
_BOUNDARY_REQUIRED_INPUTS = (
    "CODEMAP file card",
    "nearby tests",
    "patch diff headers",
)
_BOUNDARY_PROMISED_OUTPUTS = (
    "unified diff or refusal",
    "affected_files metadata",
    "tests metadata",
)
_BOUNDARY_INVARIANT = (
    "preserve phase_hash, codemap_epoch, target_file, target_symbol, and test boundary"
)
_BOUNDARY_CORE_KEYS = (
    "contract_version",
    "contract_id",
    "domain",
    "capsule_id",
    "boundary_type",
    "external_system",
    "source_region",
    "owned_scope",
    "assumptions",
    "required_inputs",
    "promised_outputs",
    "constraints",
    "escalation_triggers",
    "invariant",
    "status",
    "metadata",
    "phase_hash",
)
_BOUNDARY_ENRICHED_KEYS = (
    "task_id",
    "target_file",
    "target_symbol",
    "upstream",
    "downstream",
    "agent_scope",
    "neighbor_files",
)
_ACTION_KEYS = (
    "capsule_version",
    "capsule_id",
    "domain",
    "role",
    "objective",
    "target",
    "scope",
    "allowed_actions",
    "forbidden_actions",
    "acceptance_checks",
    "expected_output",
    "escalation_triggers",
    "boundary_contract_ids",
    "metadata",
    "phase_hash",
)
_LEASE_KEYS = (
    "lease_version",
    "lease_id",
    "domain",
    "capsule_id",
    "holder",
    "regions",
    "allowed_actions",
    "forbidden_actions",
    "mode",
    "conflict_policy",
    "status",
    "metadata",
    "phase_hash",
)
_LIQUID_KEYS = (
    "arena_version",
    "arena_id",
    "domain",
    "intent",
    "plan_ref",
    "domain_objects",
    "action_capsules",
    "boundary_contracts",
    "agent_leases",
    "shared_action_queue",
    "verification_ledger",
    "adapter",
    "phase_hash",
)
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


class LegacyCodingArenaIntegrityError(ValueError):
    """A stable fail-closed integrity finding."""

    def __init__(self, code: str, message: str, *, task_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.task_id = task_id


def _fail(code: str, message: str, *, task_id: str | None = None) -> None:
    raise LegacyCodingArenaIntegrityError(code, message, task_id=task_id)


def _text(value: Any, field_name: str, *, task_id: str | None = None) -> str:
    if not isinstance(value, str):
        _fail("INVALID_STRING", f"{field_name} must be a string", task_id=task_id)
    result = value.strip()
    if not result:
        _fail("MISSING_REQUIRED_FIELD", f"{field_name} must not be empty", task_id=task_id)
    return result


def _optional_text(value: Any, field_name: str, *, task_id: str | None = None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _fail("INVALID_STRING", f"{field_name} must be a string or null", task_id=task_id)
    result = value.strip()
    return result or None


def _strict_bool(value: Any, field_name: str, *, task_id: str | None = None) -> bool:
    if type(value) is not bool:
        _fail("INVALID_BOOLEAN", f"{field_name} must be a boolean", task_id=task_id)
    return value


def _path(value: Any, field_name: str, *, task_id: str | None = None) -> str:
    result = _text(value, field_name, task_id=task_id)
    if "\\" in result:
        _fail("NONCANONICAL_PATH", f"{field_name} must use forward slashes", task_id=task_id)
    if result.startswith("/") or _DRIVE_PREFIX.match(result):
        _fail("UNSAFE_PATH", f"{field_name} must be repository-relative", task_id=task_id)
    pure = PurePosixPath(result)
    if any(part in {"", ".", ".."} for part in pure.parts):
        _fail(
            "UNSAFE_PATH",
            f"{field_name} must be normalized without traversal",
            task_id=task_id,
        )
    if pure.as_posix() != result:
        _fail("NONCANONICAL_PATH", f"{field_name} must be normalized", task_id=task_id)
    return result


def _optional_path(value: Any, field_name: str, *, task_id: str | None = None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return _path(value, field_name, task_id=task_id)


def _records(value: Any, field_name: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        _fail("INVALID_SEQUENCE", f"{field_name} must be a JSON array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            _fail("INVALID_RECORD", f"{field_name}[{index}] must be an object")
        result.append(item)
    return tuple(result)


def _strings(
    value: Any,
    field_name: str,
    *,
    task_id: str | None = None,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        _fail("INVALID_SEQUENCE", f"{field_name} must be a JSON array", task_id=task_id)
    result = tuple(
        _text(item, f"{field_name}[{index}]", task_id=task_id)
        for index, item in enumerate(value)
    )
    if len(result) != len(set(result)):
        _fail("DUPLICATE_VALUE", f"{field_name} must not contain duplicates", task_id=task_id)
    return result


def _exact_keys(
    record: Mapping[str, Any],
    expected: Sequence[str],
    field_name: str,
    *,
    task_id: str | None = None,
) -> None:
    actual = set(record)
    required = set(expected)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        _fail(
            "LEGACY_SCHEMA_MISMATCH",
            f"{field_name} keys differ; missing={missing}, extra={extra}",
            task_id=task_id,
        )


def _legacy_hash(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _hashed_record(
    payload: dict[str, Any],
    *,
    id_field: str,
    id_prefix: str,
    task_id: str,
    field_name: str,
) -> dict[str, Any]:
    record_id = f"{id_prefix}{_legacy_hash(payload)[:12]}"
    return {
        **payload,
        id_field: record_id,
        "phase_hash": _legacy_hash({**payload, id_field: record_id}),
    }


def _declared_files(act: Mapping[str, Any], task_id: str) -> tuple[str, ...]:
    result: list[str] = []
    target = _optional_path(act.get("target_file"), "act.target_file", task_id=task_id)
    if target:
        result.append(target)
    for index, item in enumerate(_strings(act.get("related_files"), "act.related_files", task_id=task_id)):
        path = _path(item, f"act.related_files[{index}]", task_id=task_id)
        if path not in result:
            result.append(path)
    return tuple(result)


def _expected_regions(
    act: Mapping[str, Any],
    ground: Mapping[str, Any],
    task_id: str,
) -> list[dict[str, Any]]:
    declared = _declared_files(act, task_id)
    neighbors = tuple(
        _path(item, f"grounding.neighbor_files[{index}]", task_id=task_id)
        for index, item in enumerate(
            _strings(ground.get("neighbor_files"), "grounding.neighbor_files", task_id=task_id)
        )
    )
    regions: list[dict[str, Any]] = [
        {"region_type": "file", "id": path, "mode": "write"}
        for path in declared
    ]
    regions.extend(
        {"region_type": "file", "id": path, "mode": "read"}
        for path in neighbors
        if path not in declared
    )
    symbol = _optional_text(act.get("target_symbol"), "act.target_symbol", task_id=task_id)
    target = _optional_path(act.get("target_file"), "act.target_file", task_id=task_id)
    if symbol:
        if target is None:
            _fail(
                "SYMBOL_WITHOUT_TARGET_FILE",
                "a symbol lease requires a target file",
                task_id=task_id,
            )
        regions.append(
            {
                "region_type": "symbol",
                "id": symbol,
                "file": target,
                "mode": "write",
            }
        )
    return regions


def _expected_boundary(
    act: Mapping[str, Any],
    ground: Mapping[str, Any],
    task_id: str,
) -> dict[str, Any]:
    target_file = _optional_path(act.get("target_file"), "act.target_file", task_id=task_id)
    target_symbol = _optional_text(act.get("target_symbol"), "act.target_symbol", task_id=task_id)
    neighbors = list(
        _path(item, f"grounding.neighbor_files[{index}]", task_id=task_id)
        for index, item in enumerate(
            _strings(ground.get("neighbor_files"), "grounding.neighbor_files", task_id=task_id)
        )
    )
    payload = {
        "contract_version": BOUNDARY_CONTRACT_VERSION,
        "domain": "code",
        "capsule_id": task_id,
        "boundary_type": "code_boundary",
        "external_system": "CODEMAP/topology/test-neighbor surface",
        "source_region": {"file": target_file, "symbol": target_symbol},
        "owned_scope": list(_declared_files(act, task_id)),
        "assumptions": list(_BOUNDARY_ASSUMPTIONS),
        "required_inputs": list(_BOUNDARY_REQUIRED_INPUTS),
        "promised_outputs": list(_BOUNDARY_PROMISED_OUTPUTS),
        "constraints": list(_strings(act.get("constraints"), "act.constraints", task_id=task_id)),
        "escalation_triggers": list(
            _strings(act.get("escalate_if"), "act.escalate_if", task_id=task_id)
        ),
        "invariant": _BOUNDARY_INVARIANT,
        "status": "placeholder",
        "metadata": {
            "task_id": task_id,
            "target_file": target_file,
            "target_symbol": target_symbol,
            "neighbor_files": neighbors,
            "upstream": "aura_fusion.build_task_capsule",
            "downstream": "aura_phase_capsule.capture_phase_capsule",
        },
    }
    return _hashed_record(
        payload,
        id_field="contract_id",
        id_prefix="BC-",
        task_id=task_id,
        field_name="boundary",
    )


def _expected_action(
    act: Mapping[str, Any],
    ground: Mapping[str, Any],
    boundary: Mapping[str, Any],
    task_id: str,
) -> dict[str, Any]:
    tests = tuple(
        _path(item, f"grounding.test_files[{index}]", task_id=task_id)
        for index, item in enumerate(
            _strings(ground.get("test_files"), "grounding.test_files", task_id=task_id)
        )
    )
    acceptance = _text(act.get("acceptance"), "act.acceptance", task_id=task_id)
    target_file = _optional_path(act.get("target_file"), "act.target_file", task_id=task_id)
    target_symbol = _optional_text(act.get("target_symbol"), "act.target_symbol", task_id=task_id)
    payload = {
        "capsule_version": ACTION_CAPSULE_VERSION,
        "capsule_id": task_id,
        "domain": "code",
        "role": _text(act.get("role"), "act.role", task_id=task_id),
        "objective": _text(act.get("objective"), "act.objective", task_id=task_id),
        "target": {"file": target_file, "symbol": target_symbol},
        "scope": {
            "regions": _expected_regions(act, ground, task_id),
            "allowed_scope": _text(
                act.get("allowed_scope"),
                "act.allowed_scope",
                task_id=task_id,
            ),
        },
        "allowed_actions": list(_ALLOWED_ACTIONS),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "acceptance_checks": [acceptance, *(f"nearby test: {path}" for path in tests)],
        "expected_output": _text(
            act.get("expected_output"),
            "act.expected_output",
            task_id=task_id,
        ),
        "escalation_triggers": list(
            _strings(act.get("escalate_if"), "act.escalate_if", task_id=task_id)
        ),
        "boundary_contract_ids": [
            _text(boundary.get("contract_id"), "boundary.contract_id", task_id=task_id)
        ],
        "metadata": {
            "source_capsule_version": _text(
                act.get("capsule_version"),
                "act.capsule_version",
                task_id=task_id,
            ),
            "size": _text(act.get("size"), "act.size", task_id=task_id),
            "dream_context_scores": list(ground.get("dream_scores") or [])[:8],
        },
    }
    return {**payload, "phase_hash": _legacy_hash(payload)}


def _expected_lease(action: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    scope = action.get("scope")
    if not isinstance(scope, dict):
        _fail("INVALID_ACTION_SCOPE", "liquid action scope must be an object", task_id=task_id)
    payload = {
        "lease_version": ARENA_LEASE_VERSION,
        "domain": "code",
        "capsule_id": task_id,
        "holder": _text(action.get("role"), "liquid_action.role", task_id=task_id),
        "regions": list(scope.get("regions") or []),
        "allowed_actions": list(action.get("allowed_actions") or []),
        "forbidden_actions": list(action.get("forbidden_actions") or []),
        "mode": "exclusive_write",
        "conflict_policy": "judge_then_reground",
        "status": "active",
        "metadata": {
            "action_phase_hash": _text(
                action.get("phase_hash"),
                "liquid_action.phase_hash",
                task_id=task_id,
            )
        },
    }
    return _hashed_record(
        payload,
        id_field="lease_id",
        id_prefix="LEASE-",
        task_id=task_id,
        field_name="lease",
    )


def _canonical_equal(left: Any, right: Any) -> bool:
    return canonical_json(left) == canonical_json(right)


def validate_legacy_coding_arena_integrity(
    plan: Mapping[str, Any],
    grounding: Sequence[Mapping[str, Any]],
    shadow_report: Mapping[str, Any],
    arena: Mapping[str, Any],
) -> None:
    """Reconstruct and verify immutable legacy Coding Arena records."""
    acts = _records(plan.get("act_capsules"), "plan.act_capsules")
    ground_records = tuple(grounding)
    if len(acts) != len(ground_records):
        _fail("TASK_SET_MISMATCH", "grounding count differs from the legacy plan")

    task_ids = tuple(
        _text(act.get("task_id"), f"plan.act_capsules[{index}].task_id")
        for index, act in enumerate(acts)
    )
    if len(task_ids) != len(set(task_ids)):
        _fail("DUPLICATE_TASK_ID", "plan task IDs must be unique")

    ground_by_task: dict[str, Mapping[str, Any]] = {}
    ground_order: list[str] = []
    for index, ground in enumerate(ground_records):
        if not isinstance(ground, Mapping):
            _fail("INVALID_RECORD", f"grounding[{index}] must be an object")
        task_id = _text(ground.get("task_id"), f"grounding[{index}].task_id")
        if task_id in ground_by_task:
            _fail("DUPLICATE_TASK_EVIDENCE", "grounding task IDs must be unique", task_id=task_id)
        ground_by_task[task_id] = ground
        ground_order.append(task_id)
    if tuple(ground_order) != task_ids:
        _fail("TASK_ORDER_MISMATCH", "grounding order differs from the legacy plan")

    liquid = arena.get("liquid_arena")
    if not isinstance(liquid, dict) or not liquid:
        _fail("LIQUID_ARENA_UNAVAILABLE", "arena.liquid_arena must be a non-empty object")
    _exact_keys(liquid, _LIQUID_KEYS, "arena.liquid_arena")

    if _text(liquid.get("arena_version"), "liquid_arena.arena_version") != LIQUID_ARENA_VERSION:
        _fail("LIQUID_VERSION_MISMATCH", "liquid_arena version is not the canonical V1 contract")
    if _text(liquid.get("domain"), "liquid_arena.domain") != "code":
        _fail("LIQUID_DOMAIN_MISMATCH", "liquid_arena.domain must remain 'code'")
    if _text(liquid.get("intent"), "liquid_arena.intent") != _text(plan.get("objective"), "plan.objective"):
        _fail("LIQUID_INTENT_MISMATCH", "liquid_arena.intent differs from plan.objective")
    if _text(liquid.get("plan_ref"), "liquid_arena.plan_ref") != _text(plan.get("phase_hash"), "plan.phase_hash"):
        _fail("LIQUID_PLAN_REF_MISMATCH", "liquid_arena.plan_ref differs from plan.phase_hash")
    if tuple(_strings(liquid.get("domain_objects"), "liquid_arena.domain_objects")) != _CODE_DOMAIN_OBJECTS:
        _fail("LIQUID_DOMAIN_OBJECTS_MISMATCH", "liquid_arena.domain_objects changed")

    actions = _records(liquid.get("action_capsules"), "liquid_arena.action_capsules")
    boundaries = _records(liquid.get("boundary_contracts"), "liquid_arena.boundary_contracts")
    leases = _records(liquid.get("agent_leases"), "liquid_arena.agent_leases")
    top_boundaries = _records(arena.get("boundary_contracts"), "arena.boundary_contracts")
    top_leases = _records(arena.get("agent_leases"), "arena.agent_leases")
    if not (
        len(actions)
        == len(boundaries)
        == len(leases)
        == len(top_boundaries)
        == len(top_leases)
        == len(acts)
    ):
        _fail("LIQUID_RECORD_COUNT_MISMATCH", "legacy action, boundary, and lease counts differ")

    expected_actions: list[dict[str, Any]] = []
    expected_boundaries: list[dict[str, Any]] = []
    expected_leases: list[dict[str, Any]] = []
    for index, (task_id, act) in enumerate(zip(task_ids, acts)):
        ground = ground_by_task[task_id]
        expected_boundary = _expected_boundary(act, ground, task_id)
        expected_action = _expected_action(act, ground, expected_boundary, task_id)
        expected_lease = _expected_lease(expected_action, task_id)

        actual_action = actions[index]
        actual_boundary = boundaries[index]
        actual_lease = leases[index]
        top_boundary = top_boundaries[index]
        top_lease = top_leases[index]

        _exact_keys(actual_action, _ACTION_KEYS, f"liquid action {task_id}", task_id=task_id)
        _exact_keys(actual_boundary, _BOUNDARY_CORE_KEYS, f"liquid boundary {task_id}", task_id=task_id)
        _exact_keys(actual_lease, _LEASE_KEYS, f"liquid lease {task_id}", task_id=task_id)
        _exact_keys(
            top_boundary,
            (*_BOUNDARY_CORE_KEYS, *_BOUNDARY_ENRICHED_KEYS),
            f"top boundary {task_id}",
            task_id=task_id,
        )
        _exact_keys(top_lease, _LEASE_KEYS, f"top lease {task_id}", task_id=task_id)

        if not _canonical_equal(actual_boundary, expected_boundary):
            _fail(
                "BOUNDARY_DERIVATION_MISMATCH",
                "liquid boundary is not the canonical CodeArenaAdapter boundary",
                task_id=task_id,
            )
        if not _canonical_equal(actual_action, expected_action):
            _fail(
                "LIQUID_ACTION_DERIVATION_MISMATCH",
                "liquid action is not the canonical CodeArenaAdapter action",
                task_id=task_id,
            )
        if not _canonical_equal(actual_lease, expected_lease):
            _fail(
                "LEASE_DERIVATION_MISMATCH",
                "liquid lease is not the canonical CodeArenaAdapter lease",
                task_id=task_id,
            )

        top_boundary_core = {key: top_boundary[key] for key in _BOUNDARY_CORE_KEYS}
        if not _canonical_equal(top_boundary_core, expected_boundary):
            _fail(
                "TOP_LEVEL_BOUNDARY_SUBSTITUTION",
                "top-level boundary differs from the Liquid Arena source",
                task_id=task_id,
            )
        expected_enrichment = {
            "task_id": task_id,
            "target_file": expected_boundary["metadata"]["target_file"],
            "target_symbol": expected_boundary["metadata"]["target_symbol"],
            "upstream": expected_boundary["metadata"]["upstream"],
            "downstream": expected_boundary["metadata"]["downstream"],
            "agent_scope": _text(
                act.get("allowed_scope"),
                "act.allowed_scope",
                task_id=task_id,
            ),
            "neighbor_files": expected_boundary["metadata"]["neighbor_files"],
        }
        actual_enrichment = {key: top_boundary[key] for key in _BOUNDARY_ENRICHED_KEYS}
        if not _canonical_equal(actual_enrichment, expected_enrichment):
            _fail(
                "BOUNDARY_ENRICHMENT_MISMATCH",
                "top-level boundary enrichment differs from its source metadata",
                task_id=task_id,
            )
        if not _canonical_equal(top_lease, expected_lease):
            _fail(
                "TOP_LEVEL_LEASE_SUBSTITUTION",
                "top-level lease differs from the Liquid Arena source",
                task_id=task_id,
            )

        expected_actions.append(expected_action)
        expected_boundaries.append(expected_boundary)
        expected_leases.append(expected_lease)

    adapter = {
        "domain": "code",
        "domain_objects": list(_CODE_DOMAIN_OBJECTS),
        "invariant": _ARENA_INVARIANT,
    }
    initial_ledger = [
        {"stage": "lease", "status": "active", "lease_count": len(expected_leases)},
        {
            "stage": "shadow",
            "status": "passed"
            if _strict_bool(shadow_report.get("ok"), "shadow_report.ok")
            else "blocked",
        },
    ]
    initial_payload = {
        "arena_version": LIQUID_ARENA_VERSION,
        "domain": "code",
        "intent": _text(plan.get("objective"), "plan.objective"),
        "plan_ref": _text(plan.get("phase_hash"), "plan.phase_hash"),
        "domain_objects": list(_CODE_DOMAIN_OBJECTS),
        "action_capsules": expected_actions,
        "boundary_contracts": expected_boundaries,
        "agent_leases": expected_leases,
        "shared_action_queue": [],
        "verification_ledger": initial_ledger,
        "adapter": adapter,
    }
    expected_arena_id = f"LPA-{_legacy_hash(initial_payload)[:12]}"
    expected_phase_hash = _legacy_hash({**initial_payload, "arena_id": expected_arena_id})
    if _text(liquid.get("arena_id"), "liquid_arena.arena_id") != expected_arena_id:
        _fail("LIQUID_ARENA_ID_MISMATCH", "liquid_arena.arena_id does not verify")
    if _text(liquid.get("phase_hash"), "liquid_arena.phase_hash") != expected_phase_hash:
        _fail("LIQUID_ARENA_PHASE_HASH_MISMATCH", "liquid_arena.phase_hash does not verify")
    if not _canonical_equal(liquid.get("adapter"), adapter):
        _fail("LIQUID_ADAPTER_MISMATCH", "liquid_arena.adapter changed")
    if not _canonical_equal(liquid.get("verification_ledger"), initial_ledger):
        _fail("LIQUID_LEDGER_MISMATCH", "liquid_arena verification ledger changed")
    if not isinstance(liquid.get("shared_action_queue"), list):
        _fail("INVALID_SEQUENCE", "liquid_arena.shared_action_queue must be a JSON array")

    routes = _records(arena.get("routing_decisions"), "arena.routing_decisions")
    route_order: list[str] = []
    route_names: list[str] = []
    for index, route in enumerate(routes):
        task_id = _text(route.get("task_id"), f"arena.routing_decisions[{index}].task_id")
        route_order.append(task_id)
        route_names.append(
            _text(route.get("route"), f"arena.routing_decisions[{index}].route", task_id=task_id)
        )
        _text(route.get("reason"), f"arena.routing_decisions[{index}].reason", task_id=task_id)
        _text(
            route.get("symbol_output"),
            f"arena.routing_decisions[{index}].symbol_output",
            task_id=task_id,
        )
    if tuple(route_order) != task_ids:
        _fail("TASK_ORDER_MISMATCH", "routing decision order differs from the legacy plan")

    ground_ready = all(
        _strict_bool(ground_by_task[task_id].get("file_exists"), "grounding.file_exists", task_id=task_id)
        for task_id, act in zip(task_ids, acts)
        if act.get("target_file")
    )
    builder_authorized = bool(route_names) and all(name == "BUILDER_PATCH" for name in route_names)
    expected_ready = (
        _strict_bool(shadow_report.get("ok"), "shadow_report.ok")
        and ground_ready
        and builder_authorized
    )
    actual_ready = _strict_bool(arena.get("ready_for_incubator"), "arena.ready_for_incubator")
    if actual_ready != expected_ready:
        _fail(
            "READY_FOR_INCUBATOR_MISMATCH",
            "arena.ready_for_incubator contradicts the legacy shadow, grounding, or routes",
        )
