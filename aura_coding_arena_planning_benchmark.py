"""Deterministic P7 fixture benchmark for the Coding Arena Planning Board adapter."""
from __future__ import annotations

import argparse
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from aura_coding_arena_planning import inspect_coding_arena_planning_compatibility
from aura_coding_arena_planning_types import (
    CODING_ARENA_BENCHMARK_VERSION,
    CodingArenaBenchmarkCase,
    CodingArenaBenchmarkCaseResult,
    CodingArenaBenchmarkReport,
    CodingArenaCompatibilityStatus,
)
from aura_event_contracts import canonical_json, stable_digest

_PATCH_OUTPUT_MODES = frozenset({"PATCH", "UNIFIED_DIFF", "JSON_EDIT_PLAN", "PYTHON"})
_CODE_DOMAIN_OBJECTS = [
    "files",
    "symbols",
    "diffs",
    "tests",
    "topology_deltas",
    "dream_usefulness_scores",
]
_ARENA_INVARIANT = (
    "models propose, Arena stages, Shadow critiques, Judge decides, "
    "verifier proves, human approves, ledger remembers"
)
_ALLOWED_ACTIONS = [
    "read leased files and CODEMAP context",
    "emit one bounded unified diff",
    "declare affected files, symbols, and tests",
    "emit BoundaryContract placeholders for external assumptions",
]
_FORBIDDEN_ACTIONS = [
    "mutate production files directly",
    "touch files outside leased regions",
    "write aura_incubator.py in live Architect mode",
    "invent behavior across a boundary without a BoundaryContract",
]


def _legacy_hash(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _phase_hash(case_id: str, task_ids: list[str]) -> str:
    return _legacy_hash({"case_id": case_id, "task_ids": task_ids})


def _task(
    *,
    task_id: str,
    objective: str,
    target_file: str | None,
    target_symbol: str | None = None,
    related_files: tuple[str, ...] = (),
    expected_output: str = "UNIFIED_DIFF",
    role: str = "cheap_builder",
    constraints: tuple[str, ...] = ("NO_FAKE_FILES", "PRESERVE_SIGNATURES"),
) -> dict[str, Any]:
    return {
        "capsule_version": "AURA_ACT_CAPSULE_V1",
        "task_id": task_id,
        "role": role,
        "objective": objective,
        "target_file": target_file,
        "target_symbol": target_symbol,
        "related_files": list(related_files),
        "allowed_scope": "single bounded edit",
        "context_ref": f"ACT-{stable_digest({'task_id': task_id}, digest_size=8)}",
        "topological_grounding": {},
        "acceptance": "Return a bounded candidate or a refusal reason.",
        "escalate_if": [
            "missing target file",
            "requires public API change",
            "touches files outside allowed scope",
        ],
        "constraints": list(constraints),
        "expected_output": expected_output,
        "size": "S",
    }


def _grounding(
    task: dict[str, Any],
    *,
    file_exists: bool = True,
    codemap_file_hit: bool = True,
    symbol_exists: bool = True,
    test_files: tuple[str, ...] = (),
    neighbor_files: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "target_file": task["target_file"],
        "target_symbol": task["target_symbol"],
        "file_exists": file_exists,
        "codemap_file_hit": codemap_file_hit,
        "symbol_exists": symbol_exists,
        "codemap_symbol_hits": [
            {
                "name": task["target_symbol"],
                "file": task["target_file"],
                "kind": "function",
                "line": 1,
                "end_line": 5,
            }
        ]
        if task["target_symbol"] and symbol_exists
        else [],
        "test_files": list(test_files),
        "neighbor_files": list(neighbor_files),
        "dream_scores": [],
    }


def _artifact_for_target(task: dict[str, Any]) -> str:
    target = task["target_file"]
    if target and PurePosixPath(target).name.startswith("test_"):
        return "test_file"
    if target and target.endswith(".py"):
        return "python_module"
    if target and target.endswith((".md", ".txt", ".rst")):
        return "documentation"
    if str(task["expected_output"]).upper() in _PATCH_OUTPUT_MODES:
        return "patch"
    return "documentation"


def _scope_for_task(task: dict[str, Any]) -> str:
    scope_text = " ".join(
        [task["allowed_scope"], task["objective"], task["acceptance"]]
    ).lower()
    if "repo" in scope_text or "repository" in scope_text:
        return "repo"
    if "subsystem" in scope_text or "multi-file" in scope_text or task["size"] in {"L", "XL"}:
        return "subsystem"
    if task["target_symbol"]:
        return "symbol"
    return "file"


def _risk_for_task(plan: dict[str, Any], task: dict[str, Any]) -> str:
    task_text = " ".join(
        [plan["objective"], task["objective"], task["allowed_scope"]]
    ).lower()
    explicit_risk = " ".join(plan["risk_map"]).lower()
    if any(term in task_text for term in ("live", "hot-swap", "hotswap", "promote")):
        return "live"
    if any(
        term in explicit_risk
        for term in ("live traffic", "production", "customer-facing", "promote immediately")
    ):
        return "live"
    if task["size"] in {"L", "XL"} or any(
        term in f"{task_text} {explicit_risk}"
        for term in ("high risk", "public api", "dependency", "schema", "rewrite")
    ):
        return "high"
    if any(term in task_text for term in ("read-only", "explain", "inspect")):
        return "low"
    return "medium"


def _route(
    plan: dict[str, Any],
    task: dict[str, Any],
    ground: dict[str, Any],
    route: str,
    reason: str,
) -> dict[str, Any]:
    grounding: list[str] = []
    if ground["file_exists"]:
        grounding.append("file_exists")
    if ground["symbol_exists"]:
        grounding.append("symbol_exists")
    if ground["test_files"]:
        grounding.append("tests_exist")
    if ground["codemap_file_hit"] and (
        not task["target_symbol"] or ground["symbol_exists"]
    ):
        grounding.append("codemap_grounded")
    if (
        ground["file_exists"]
        and ground["codemap_file_hit"]
        and ground["symbol_exists"]
        and ground["test_files"]
    ):
        grounding.append("full")
    expected_output = str(task["expected_output"]).upper()
    action = "modify" if expected_output in _PATCH_OUTPUT_MODES else "inspect"
    return {
        "route": route,
        "reason": reason,
        "symbol_output": route,
        "task_id": task["task_id"],
        "target_file": task["target_file"],
        "target_symbol": task["target_symbol"],
        "frame": {
            "intent": "code_refactor",
            "artifact": _artifact_for_target(task),
            "action": action,
            "scope": _scope_for_task(task),
            "risk": _risk_for_task(plan, task),
            "grounding": grounding,
            "tests": "existing" if ground["test_files"] else "none",
            "quality": "balanced",
            "cost": "local_first",
            "target_file": task["target_file"],
            "target_symbol": task["target_symbol"],
        },
    }


def _declared_files(task: dict[str, Any]) -> list[str]:
    result: list[str] = []
    if task["target_file"]:
        result.append(task["target_file"])
    for path in task["related_files"]:
        if path not in result:
            result.append(path)
    return result


def _regions(task: dict[str, Any], ground: dict[str, Any]) -> list[dict[str, Any]]:
    declared = _declared_files(task)
    result = [
        {"region_type": "file", "id": path, "mode": "write"}
        for path in declared
    ]
    result.extend(
        {"region_type": "file", "id": path, "mode": "read"}
        for path in ground["neighbor_files"]
        if path not in declared
    )
    if task["target_symbol"]:
        result.append(
            {
                "region_type": "symbol",
                "id": task["target_symbol"],
                "file": task["target_file"],
                "mode": "write",
            }
        )
    return result


def _boundary_core(task: dict[str, Any], ground: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "contract_version": "AURA_BOUNDARY_CONTRACT_V1",
        "domain": "code",
        "capsule_id": task["task_id"],
        "boundary_type": "code_boundary",
        "external_system": "CODEMAP/topology/test-neighbor surface",
        "source_region": {
            "file": task["target_file"],
            "symbol": task["target_symbol"],
        },
        "owned_scope": _declared_files(task),
        "assumptions": [
            "Only declared files and symbols may be changed.",
            "Neighbor files are read context unless explicitly leased.",
        ],
        "required_inputs": [
            "CODEMAP file card",
            "nearby tests",
            "patch diff headers",
        ],
        "promised_outputs": [
            "unified diff or refusal",
            "affected_files metadata",
            "tests metadata",
        ],
        "constraints": list(task["constraints"]),
        "escalation_triggers": list(task["escalate_if"]),
        "invariant": (
            "preserve phase_hash, codemap_epoch, target_file, target_symbol, "
            "and test boundary"
        ),
        "status": "placeholder",
        "metadata": {
            "task_id": task["task_id"],
            "target_file": task["target_file"],
            "target_symbol": task["target_symbol"],
            "neighbor_files": list(ground["neighbor_files"]),
            "upstream": "aura_fusion.build_task_capsule",
            "downstream": "aura_phase_capsule.capture_phase_capsule",
        },
    }
    contract_id = f"BC-{_legacy_hash(payload)[:12]}"
    return {
        **payload,
        "contract_id": contract_id,
        "phase_hash": _legacy_hash({**payload, "contract_id": contract_id}),
    }


def _enriched_boundary(
    task: dict[str, Any],
    core: dict[str, Any],
) -> dict[str, Any]:
    metadata = core["metadata"]
    return {
        **core,
        "task_id": metadata["task_id"],
        "target_file": metadata["target_file"],
        "target_symbol": metadata["target_symbol"],
        "upstream": metadata["upstream"],
        "downstream": metadata["downstream"],
        "agent_scope": task["allowed_scope"],
        "neighbor_files": list(metadata["neighbor_files"]),
    }


def _liquid_action(
    task: dict[str, Any],
    ground: dict[str, Any],
    boundary: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "capsule_version": "AURA_ACTION_CAPSULE_V1",
        "capsule_id": task["task_id"],
        "domain": "code",
        "role": task["role"],
        "objective": task["objective"],
        "target": {
            "file": task["target_file"],
            "symbol": task["target_symbol"],
        },
        "scope": {
            "regions": _regions(task, ground),
            "allowed_scope": task["allowed_scope"],
        },
        "allowed_actions": list(_ALLOWED_ACTIONS),
        "forbidden_actions": list(_FORBIDDEN_ACTIONS),
        "acceptance_checks": [
            task["acceptance"],
            *(f"nearby test: {name}" for name in ground["test_files"]),
        ],
        "expected_output": task["expected_output"],
        "escalation_triggers": list(task["escalate_if"]),
        "boundary_contract_ids": [boundary["contract_id"]],
        "metadata": {
            "source_capsule_version": task["capsule_version"],
            "size": task["size"],
            "dream_context_scores": list(ground["dream_scores"])[:8],
        },
    }
    return {**payload, "phase_hash": _legacy_hash(payload)}


def _lease(action: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "lease_version": "AURA_ARENA_LEASE_V1",
        "domain": "code",
        "capsule_id": action["capsule_id"],
        "holder": action["role"],
        "regions": list(action["scope"]["regions"]),
        "allowed_actions": list(action["allowed_actions"]),
        "forbidden_actions": list(action["forbidden_actions"]),
        "mode": "exclusive_write",
        "conflict_policy": "judge_then_reground",
        "status": "active",
        "metadata": {"action_phase_hash": action["phase_hash"]},
    }
    lease_id = f"LEASE-{_legacy_hash(payload)[:12]}"
    return {
        **payload,
        "lease_id": lease_id,
        "phase_hash": _legacy_hash({**payload, "lease_id": lease_id}),
    }


def _liquid_arena(
    plan: dict[str, Any],
    actions: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    leases: list[dict[str, Any]],
    shadow_report: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "arena_version": "AURA_LIQUID_PLANNING_ARENA_V1",
        "domain": "code",
        "intent": plan["objective"],
        "plan_ref": plan["phase_hash"],
        "domain_objects": list(_CODE_DOMAIN_OBJECTS),
        "action_capsules": actions,
        "boundary_contracts": boundaries,
        "agent_leases": leases,
        "shared_action_queue": [],
        "verification_ledger": [
            {"stage": "lease", "status": "active", "lease_count": len(leases)},
            {
                "stage": "shadow",
                "status": "passed" if shadow_report["ok"] else "blocked",
            },
        ],
        "adapter": {
            "domain": "code",
            "domain_objects": list(_CODE_DOMAIN_OBJECTS),
            "invariant": _ARENA_INVARIANT,
        },
    }
    arena_id = f"LPA-{_legacy_hash(payload)[:12]}"
    return {
        **payload,
        "arena_id": arena_id,
        "phase_hash": _legacy_hash({**payload, "arena_id": arena_id}),
    }


def _case(
    *,
    case_id: str,
    tasks: tuple[dict[str, Any], ...],
    grounding: tuple[dict[str, Any], ...],
    routes: tuple[tuple[str, str], ...],
    findings: tuple[dict[str, Any], ...] = (),
    shadow_ok: bool = True,
    shadow_gate: str = "ALLOW_BUILDER",
    ready_for_incubator: bool | None = None,
    expected_status: CodingArenaCompatibilityStatus = CodingArenaCompatibilityStatus.VERIFIED_SHADOW,
) -> CodingArenaBenchmarkCase:
    if not tasks:
        raise ValueError("fixture tasks must not be empty")
    if len(tasks) != len(grounding) or len(tasks) != len(routes):
        raise ValueError("fixture tasks, grounding, and routes must have equal lengths")
    task_ids = [str(task["task_id"]) for task in tasks]
    plan_phase_hash = _phase_hash(case_id, task_ids)
    plan = {
        "capsule_version": "AURA_FRACTAL_PLAN_CAPSULE_V1",
        "objective": f"P7 fixture objective: {case_id}",
        "architecture_decision": (
            "Preserve the legacy Coding Arena and add a shadow projection."
        ),
        "constraints": ["NO_NEW_DEPS", "PRESERVE_SIGNATURES"],
        "acceptance_criteria": ["Exact task mapping is preserved."],
        "rollback_conditions": ["Discard the shadow projection."],
        "risk_map": [],
        "act_capsules": list(tasks),
        "escalation_rules": [],
        "fusion_capsule": {"phase_hash": f"fusion-{plan_phase_hash}"},
        "context_ref": f"PLAN-{plan_phase_hash}",
        "st3gg_capsule": None,
        "continuity_capsule": None,
        "phase_hash": plan_phase_hash,
    }
    shadow_payload = {
        "plan_phase_hash": plan_phase_hash,
        "findings": list(findings),
    }
    shadow_report = {
        "report_version": "AURA_SHADOW_REPORT_V1",
        "ok": shadow_ok,
        "phase_hash": _legacy_hash(shadow_payload),
        "findings": list(findings),
        "gate": shadow_gate,
    }
    boundary_cores = [
        _boundary_core(task, ground)
        for task, ground in zip(tasks, grounding)
    ]
    liquid_actions = [
        _liquid_action(task, ground, boundary)
        for task, ground, boundary in zip(tasks, grounding, boundary_cores)
    ]
    leases = [_lease(action) for action in liquid_actions]
    enriched_boundaries = [
        _enriched_boundary(task, boundary)
        for task, boundary in zip(tasks, boundary_cores)
    ]
    route_records = [
        _route(plan, task, ground, route_name, reason)
        for task, ground, (route_name, reason) in zip(tasks, grounding, routes)
    ]
    affected_files = sorted(
        {
            str(item["target_file"])
            for item in grounding
            if item["target_file"] and item["file_exists"]
        }
    )
    computed_ready = (
        shadow_ok
        and all(
            ground["file_exists"]
            for task, ground in zip(tasks, grounding)
            if task["target_file"]
        )
        and bool(route_records)
        and all(item["route"] == "BUILDER_PATCH" for item in route_records)
    )
    ready = computed_ready if ready_for_incubator is None else ready_for_incubator
    arena = {
        "arena_version": "AURA_REFACTOR_ARENA_V1",
        "plan_phase_hash": plan_phase_hash,
        "affected_files": affected_files,
        "boundary_contracts": enriched_boundaries,
        "agent_capsules": list(tasks),
        "shared_patch_queue": [],
        "conflict_resolver": {
            "mode": "liquid_region_lease",
            "cross_boundary_edit": "escalate_to_shadow",
            "same_file_conflict": "judge_then_reground",
            "lease_violation": "block_transaction",
        },
        "shadow_report": shadow_report,
        "verification_ledger": [],
        "ready_for_incubator": ready,
        "rollback_hint": "Discard by plan phase hash.",
        "agent_leases": leases,
        "liquid_arena": _liquid_arena(
            plan,
            liquid_actions,
            boundary_cores,
            leases,
            shadow_report,
        ),
        "routing_decisions": route_records,
    }
    return CodingArenaBenchmarkCase(
        case_id=case_id,
        plan=plan,
        grounding=grounding,
        shadow_report=shadow_report,
        arena=arena,
        expected_status=expected_status,
    )


def default_benchmark_cases() -> tuple[CodingArenaBenchmarkCase, ...]:
    single = _task(
        task_id="SINGLE-1",
        objective="Patch the declared parser function.",
        target_file="aura_parser.py",
        target_symbol="parse",
    )
    single_ground = _grounding(
        single,
        test_files=("tests/test_aura_parser.py",),
        neighbor_files=("aura_tokens.py",),
    )
    multi_a = _task(
        task_id="MULTI-1",
        objective="Patch the board adapter.",
        target_file="aura_adapter.py",
        related_files=("aura_adapter_types.py",),
    )
    multi_b = _task(
        task_id="MULTI-2",
        objective="Add focused adapter tests.",
        target_file="tests/test_aura_adapter.py",
    )
    multi_a_ground = _grounding(
        multi_a,
        test_files=("tests/test_aura_adapter.py",),
        neighbor_files=("aura_planning_board.py",),
    )
    multi_b_ground = _grounding(
        multi_b,
        test_files=("tests/test_aura_adapter.py",),
        neighbor_files=("aura_adapter.py",),
    )
    inspect_task = _task(
        task_id="INSPECT-1",
        objective="Inspect the exact source boundary without a patch.",
        target_file="aura_architect_loop.py",
        expected_output="TEXT",
        role="researcher",
    )
    inspect_ground = _grounding(
        inspect_task,
        test_files=("test_aura_architect_loop.py",),
        neighbor_files=("aura_liquid_planning_arena.py",),
    )
    warning_task = _task(
        task_id="WARN-1",
        objective="Prepare a bounded patch while reporting the missing nearby test.",
        target_file="aura_warning_fixture.py",
    )
    warning_ground = _grounding(warning_task, test_files=())
    warning_finding = {
        "shadow_type": "missing_test",
        "severity": "warn",
        "message": "No nearby test file was found for the target file.",
        "task_id": warning_task["task_id"],
        "target_file": warning_task["target_file"],
        "target_symbol": warning_task["target_symbol"],
    }
    blocked_task = _task(
        task_id="BLOCKED-1",
        objective="Refuse a patch against a missing file.",
        target_file="missing_fixture.py",
    )
    blocked_ground = _grounding(
        blocked_task,
        file_exists=False,
        codemap_file_hit=False,
        symbol_exists=True,
        test_files=(),
    )
    blocked_finding = {
        "shadow_type": "fake_file",
        "severity": "blocker",
        "message": "Target file is absent from the working tree.",
        "task_id": blocked_task["task_id"],
        "target_file": blocked_task["target_file"],
        "target_symbol": blocked_task["target_symbol"],
    }
    return (
        _case(
            case_id="grounded_single_file_patch",
            tasks=(single,),
            grounding=(single_ground,),
            routes=(("BUILDER_PATCH", "grounded_patch"),),
        ),
        _case(
            case_id="grounded_multi_act_patch",
            tasks=(multi_a, multi_b),
            grounding=(multi_a_ground, multi_b_ground),
            routes=(
                ("BUILDER_PATCH", "grounded_patch"),
                ("BUILDER_PATCH", "grounded_patch"),
            ),
        ),
        _case(
            case_id="inspect_only_route",
            tasks=(inspect_task,),
            grounding=(inspect_ground,),
            routes=(("RESEARCH_DECOMPOSE", "inspect_only"),),
            ready_for_incubator=False,
        ),
        _case(
            case_id="warning_missing_test",
            tasks=(warning_task,),
            grounding=(warning_ground,),
            routes=(("BUILDER_PATCH", "grounded_patch"),),
            findings=(warning_finding,),
            shadow_gate="ALLOW_BUILDER_WITH_WARNINGS",
        ),
        _case(
            case_id="blocked_missing_file",
            tasks=(blocked_task,),
            grounding=(blocked_ground,),
            routes=(("BLOCKED_WITH_REASON", "missing_grounding"),),
            findings=(blocked_finding,),
            shadow_ok=False,
            shadow_gate="BLOCK_BUILDER",
            ready_for_incubator=False,
            expected_status=CodingArenaCompatibilityStatus.BLOCKED_LEGACY,
        ),
    )


def _token_proxy(byte_count: int) -> int:
    return (int(byte_count) + 3) // 4


def run_coding_arena_planning_benchmark(
    *,
    cases: Sequence[CodingArenaBenchmarkCase] | None = None,
    repeats: int = 3,
) -> CodingArenaBenchmarkReport:
    if type(repeats) is not int or repeats < 2 or repeats > 20:
        raise ValueError("repeats must be an integer between 2 and 20")
    selected = tuple(default_benchmark_cases() if cases is None else cases)
    if not selected:
        raise ValueError("benchmark cases must not be empty")
    if not all(isinstance(case, CodingArenaBenchmarkCase) for case in selected):
        raise ValueError("cases must contain CodingArenaBenchmarkCase records")
    case_ids = [case.case_id for case in selected]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark case_id values must be unique")

    results: list[CodingArenaBenchmarkCaseResult] = []
    all_board_digests: list[str] = []
    all_action_ids: list[str] = []
    for case in selected:
        baseline_payload = {
            "plan": case.plan,
            "grounding": list(case.grounding),
            "shadow_report": case.shadow_report,
            "arena": case.arena,
        }
        before = canonical_json(baseline_payload)
        inspections = tuple(
            inspect_coding_arena_planning_compatibility(
                case.plan,
                case.grounding,
                case.shadow_report,
                case.arena,
            )
            for _ in range(repeats)
        )
        after = canonical_json(baseline_payload)
        first = inspections[0]
        inspection_digests = tuple(item.digest for item in inspections)
        deterministic = len(set(inspection_digests)) == 1
        board_digest = first.board.digest if first.board is not None else None
        action_ids = (
            tuple(action.action_id for action in first.board.actions)
            if first.board is not None
            else ()
        )
        verifier_count = (
            sum(1 for action in first.board.actions if action.verifier_ids)
            if first.board is not None
            else 0
        )
        task_count = first.report.task_count
        verifier_rate = verifier_count / task_count if task_count else 0.0
        baseline_bytes = len(before.encode("utf-8"))
        candidate_json = canonical_json(first.to_dict())
        candidate_bytes = len(candidate_json.encode("utf-8"))
        overhead_ratio = candidate_bytes / baseline_bytes if baseline_bytes else 0.0
        mutation = before != after or first.report.legacy_mutated
        passed = (
            first.report.status is case.expected_status
            and deterministic
            and first.report.mapped_action_count == task_count
            and first.report.task_order_preserved
            and first.report.exact_legacy_preserved
            and not mutation
            and not first.report.authority_changed
            and first.report.proposal_only
            and verifier_rate == 1.0
            and first.board is not None
            and all(action.proposal_only for action in first.board.actions)
            and all(
                action.authority_requirement.value == "HUMAN"
                for action in first.board.actions
            )
        )
        result = CodingArenaBenchmarkCaseResult(
            case_id=case.case_id,
            expected_status=case.expected_status,
            observed_status=first.report.status,
            passed=passed,
            task_count=task_count,
            mapped_action_count=first.report.mapped_action_count,
            deterministic=deterministic,
            task_order_preserved=first.report.task_order_preserved,
            exact_legacy_preserved=first.report.exact_legacy_preserved,
            legacy_mutated=mutation,
            authority_changed=first.report.authority_changed,
            proposal_only=first.report.proposal_only,
            verifier_declaration_rate=verifier_rate,
            baseline_bytes=baseline_bytes,
            candidate_bytes=candidate_bytes,
            baseline_token_proxy=_token_proxy(baseline_bytes),
            candidate_token_proxy=_token_proxy(candidate_bytes),
            overhead_ratio=overhead_ratio,
            board_digest=board_digest,
            inspection_digest=first.digest,
            finding_codes=tuple(finding.code for finding in first.report.findings),
        )
        results.append(result)
        if board_digest is not None:
            all_board_digests.append(board_digest)
        all_action_ids.extend(action_ids)

    total_cases = len(results)
    total_tasks = sum(item.task_count for item in results)
    mapped_actions = sum(item.mapped_action_count for item in results)
    baseline_bytes = sum(item.baseline_bytes for item in results)
    candidate_bytes = sum(item.candidate_bytes for item in results)
    baseline_tokens = sum(item.baseline_token_proxy for item in results)
    candidate_tokens = sum(item.candidate_token_proxy for item in results)
    board_collisions = len(all_board_digests) - len(set(all_board_digests))
    action_collisions = len(all_action_ids) - len(set(all_action_ids))
    identifier_collisions = board_collisions + action_collisions
    action_coverage = mapped_actions / total_tasks if total_tasks else 0.0
    deterministic_rate = sum(item.deterministic for item in results) / total_cases
    order_rate = sum(item.task_order_preserved for item in results) / total_cases
    verifier_rate = (
        sum(item.verifier_declaration_rate * item.task_count for item in results)
        / total_tasks
        if total_tasks
        else 0.0
    )
    mutation_drift_count = sum(item.legacy_mutated for item in results)
    authority_drift_count = sum(item.authority_changed for item in results)
    passed_cases = sum(item.passed for item in results)
    gate_passed = (
        passed_cases == total_cases
        and action_coverage == 1.0
        and deterministic_rate == 1.0
        and order_rate == 1.0
        and verifier_rate == 1.0
        and mutation_drift_count == 0
        and authority_drift_count == 0
        and identifier_collisions == 0
    )
    return CodingArenaBenchmarkReport(
        version=CODING_ARENA_BENCHMARK_VERSION,
        measurement_class="EMPIRICAL_FIXTURE_WITH_HEURISTIC_TOKEN_PROXY",
        repeats=repeats,
        total_cases=total_cases,
        passed_cases=passed_cases,
        total_tasks=total_tasks,
        mapped_actions=mapped_actions,
        action_coverage=action_coverage,
        deterministic_case_rate=deterministic_rate,
        order_preservation_rate=order_rate,
        verifier_declaration_rate=verifier_rate,
        mutation_drift_count=mutation_drift_count,
        authority_drift_count=authority_drift_count,
        identifier_collision_count=identifier_collisions,
        baseline_bytes=baseline_bytes,
        candidate_bytes=candidate_bytes,
        baseline_token_proxy=baseline_tokens,
        candidate_token_proxy=candidate_tokens,
        overhead_ratio=candidate_bytes / baseline_bytes if baseline_bytes else 0.0,
        gate_passed=gate_passed,
        cases=tuple(results),
        limitations=(
            "Fixture measurements prove adapter parity only for the committed cases.",
            "Byte counts are exact canonical UTF-8 sizes; token counts are a deterministic four-bytes-per-token proxy.",
            "No latency, provider quality, model quality, execution success, or general efficiency improvement is claimed.",
            "The benchmark never stages patches, runs tests, grants authority, hotswaps, or merges.",
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic P7 Coding Arena Planning Board benchmark."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args(argv)
    report = run_coding_arena_planning_benchmark(repeats=args.repeats)
    text = report.to_json() + "\n"
    if args.output is not None:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report.gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
