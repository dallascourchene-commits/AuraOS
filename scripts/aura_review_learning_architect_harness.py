#!/usr/bin/env python3
"""Execute Aura's native planning/review surfaces for the PR164 lesson refactor.

The harness is read-only with respect to tracked source.  It uses the retained
Agent Bridge, Architect preparation path, Selective Council V3 lane router,
Surgeon control contract, Capability Connectome/Affordance Directory, Emergent
Evidence Spine, and Coding Waboose.  It writes one bounded JSON receipt only to
an explicitly supplied artifact path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from aura_agent_arena_review_learning_bridge import ReviewLearningAgentArenaBridge
from aura_architect_control import normalize_control_profile
from aura_architect_council_v2 import profile_refactor_length
from aura_architect_council_v3 import ARCHITECT_COUNCIL_V3, select_critic_lanes
from aura_coding_waboose_review_lessons import PATCH_AUTHORITY

HARNESS_VERSION = "AURA_PR164_REVIEW_LEARNING_ARCHITECT_HARNESS_V1"
_MAX_RECEIPT_BYTES = 1_048_576


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.blake2b(_canonical(value), digest_size=20).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return "UNAVAILABLE"
    return result.stdout.strip() or "UNAVAILABLE"


def _summary(packet: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {"ok": False, "status": "invalid_packet"}
    return {key: packet.get(key) for key in keys if key in packet}


def _plan() -> dict[str, Any]:
    tasks = [
        {
            "task_id": "RL1",
            "title": "Typed lesson registry and runtime contract",
            "target_file": "aura_coding_waboose_review_lessons.py",
            "related_files": [
                "schemas/aura_review_lesson.schema.json",
                ".aura/review_lessons/pr164_spatial_review_lessons.json",
            ],
            "size": "L",
            "depends_on": [],
        },
        {
            "task_id": "RL2",
            "title": "Deterministic PR164 detector pack",
            "target_file": "aura_coding_waboose_review_lessons.py",
            "related_files": ["tests/test_aura_coding_waboose_review_lessons.py"],
            "size": "L",
            "depends_on": ["RL1"],
        },
        {
            "task_id": "RL3",
            "title": "Crucible adversarial replay receipts",
            "target_file": "aura_coding_waboose_review_lessons.py",
            "related_files": ["tests/test_aura_coding_waboose_review_lessons.py"],
            "size": "M",
            "depends_on": ["RL2"],
        },
        {
            "task_id": "RL4",
            "title": "Coding Waboose source-scan integration",
            "target_file": "aura_coding_waboose_review_learning.py",
            "related_files": ["aura_coding_waboose.py"],
            "size": "M",
            "depends_on": ["RL1", "RL2"],
        },
        {
            "task_id": "RL5",
            "title": "Agent Bridge and MCP projections",
            "target_file": "aura_agent_arena_review_learning_bridge.py",
            "related_files": ["aura_agent_arena_review_learning_mcp.py"],
            "size": "M",
            "depends_on": ["RL4"],
        },
        {
            "task_id": "RL6",
            "title": "Connectome and affordance registration",
            "target_file": ".aura/AFFORDANCE_MAP.json",
            "related_files": ["aura_capability_connectome.py"],
            "size": "S",
            "depends_on": ["RL5"],
        },
        {
            "task_id": "RL7",
            "title": "Focused workflow and real Waboose harness",
            "target_file": ".github/workflows/aura-review-learning.yml",
            "related_files": ["scripts/aura_review_learning_architect_harness.py"],
            "size": "M",
            "depends_on": ["RL3", "RL4", "RL5", "RL6"],
        },
        {
            "task_id": "RL8",
            "title": "Documentation, review ingestion, and generated-map boundary",
            "target_file": "docs/AURA_CODING_WABOOSE_REVIEW_LEARNING.md",
            "related_files": [".aura/CODEMAP.md", ".aura/CODEMAP.json", "topology_map.json"],
            "size": "S",
            "depends_on": ["RL7"],
        },
    ]
    return {
        "architecture_decision": (
            "Extend retained Coding Waboose and Agent Bridge through narrow typed "
            "review-learning adapters; do not create a parallel review authority."
        ),
        "target_file": "aura_coding_waboose_review_lessons.py",
        "target_symbol": "ReviewLessonEngine",
        "act_tasks": tasks,
        "acceptance_criteria": [
            "All 13 PR164 lessons have deterministic replay fixtures.",
            "CodeRabbit, Codex, and manual findings normalize into typed dispositions.",
            "Coding Waboose invokes precision-first lesson detectors on changed source.",
            "Agent Bridge exposes review-only lesson tools through a narrow adapter.",
            "Focused Python 3.10/3.12 workflow executes schema, compile, Ruff, pytest, Waboose, and harness gates.",
            "No patch, commit, push, pull-request, merge, or production authority expands.",
        ],
        "rollback_conditions": [
            "Any detector produces unbounded evidence or bypasses exact-source corroboration.",
            "Any adapter weakens existing Coding Waboose or Agent Bridge authority fields.",
            "Schema/runtime outcomes diverge.",
            "Focused workflow or Crucible replay fails.",
        ],
        "risk_map": [
            "false-positive detector noise",
            "reviewer payload ambiguity",
            "stale or historical evidence mislabeling",
            "unbounded comment or scenario payload",
            "private-core integration drift",
            "generated CODEMAP/topology reviewed before source stabilizes",
        ],
        "constraints": [
            "external reviewer output is teacher signal only",
            "exact source and regressions corroborate findings",
            "generated maps are excluded from targeted reviewer scope",
            "human review remains mandatory",
        ],
        "escalation_rules": [
            "Council handles interface, dependency, sequence, continuity, rollback, or cost defects.",
            "Surgeon receives one exact bounded file/symbol slice at a time.",
            "Failed local verification returns a repair packet; it never promotes automatically.",
        ],
    }


def run(repo_root: Path, *, base_ref: str, head_ref: str) -> dict[str, Any]:
    objective = (
        "Integrate PR164 CodeRabbit, Codex, and manual review lessons into Coding "
        "Waboose through typed detectors, Crucible replay, Connectome registration, "
        "and review-only Agent Bridge tools."
    )
    head = _git(repo_root, "rev-parse", "HEAD")
    bridge = ReviewLearningAgentArenaBridge(
        repo_root=str(repo_root),
        review_learning_root=repo_root / "Aura_Staging" / "review_learning_harness",
    )

    repo_digest = bridge.aura_repo_digest(include_hubs=True, max_lines=80)
    affordances = bridge.aura_find_affordances(
        objective=objective,
        target_files=[
            "aura_coding_waboose.py",
            "aura_waboose_learning.py",
            "aura_coding_waboose_review_lessons.py",
            "aura_coding_waboose_review_learning.py",
            "aura_agent_arena_review_learning_bridge.py",
        ],
        target_symbols=["CodingWaboose", "ReviewLessonEngine"],
        include_affordances=True,
        top_k=7,
    )
    atomic = bridge.aura_atomic_function_inventory(
        query="review lesson detector Coding Waboose Agent Bridge",
        target_files=[
            "aura_coding_waboose.py",
            "aura_waboose_learning.py",
            "aura_coding_waboose_review_lessons.py",
            "aura_coding_waboose_review_learning.py",
            "aura_agent_arena_review_learning_bridge.py",
        ],
        target_symbols=["CodingWaboose", "ReviewLessonEngine"],
        limit=120,
        include_source=False,
    )
    emergent = bridge.aura_emergent_evidence(
        {
            "objective": objective,
            "target_files": [
                "aura_coding_waboose.py",
                "aura_waboose_learning.py",
                "aura_coding_waboose_review_lessons.py",
                "aura_coding_waboose_review_learning.py",
                "aura_agent_arena_review_learning_bridge.py",
            ],
            "target_symbols": ["CodingWaboose", "ReviewLessonEngine"],
            "target_arena": "coding_waboose",
            "radius": 2,
            "max_atomic_nodes": 120,
            "max_source_lines": 80,
            "include_source": False,
            "include_future": True,
            "include_research_plan": False,
            "include_offline_research": False,
        }
    )

    prepare_arguments = {
        "objective": objective,
        "target_file": "aura_coding_waboose.py",
        "target_symbol": "CodingWaboose",
        "acceptance_criteria": _plan()["acceptance_criteria"],
        "risk_map": _plan()["risk_map"],
        "constraints": _plan()["constraints"],
        "refresh_codemap": False,
        "use_emergent_evidence": True,
        "emergent_radius": 2,
        "emergent_max_atomic_nodes": 120,
        "emergent_include_source": False,
        "emergent_include_research_plan": False,
    }
    prepared = bridge.aura_prepare_arena(**prepare_arguments)
    prepare_fallback = False
    if not prepared.get("ok"):
        prepare_fallback = True
        prepare_arguments["use_emergent_evidence"] = False
        prepared = bridge.aura_prepare_arena(**prepare_arguments)

    plan = _plan()
    candidate = {"candidate_id": "PR164-REVIEW-LEARNING", "plan": plan, "score": 1.0}
    council_lanes = select_critic_lanes(candidate)
    profile = profile_refactor_length(plan).to_dict()
    surgeon_control = normalize_control_profile(
        {
            "surface": "coding_arena",
            "council_mode": "SELECTIVE_V3",
            "council_call_budget": len(council_lanes),
            "critic_lanes": council_lanes,
            "surgeon_mode": "PROPOSE",
            "surgeon_max_turns": max(8, len(plan["act_tasks"])),
            "surgeon_max_local_repairs": 2,
            "surgeon_context_tokens": 2400,
            "surgeon_output_tokens": 2400,
            "council_replan_allowed": True,
            "record_outputs": False,
            "output_root": "Aura_Staging/review_learning_harness",
            "human_review_required": True,
            "production_mutation": False,
            "vsa_patch_authority": False,
        },
        surface="coding_arena",
    ).to_dict()

    waboose_prepared = bridge.aura_waboose_prepare(
        {
            "objective": objective,
            "mode": "range",
            "base_ref": base_ref,
            "head_ref": head_ref,
            "profile": "precision",
            "focus_directives": [
                {
                    "name": "standard_correctness",
                    "question": "Are all PR164 defect classes executable, bounded, and source-corroborated?",
                    "risk": "correctness",
                    "direction": "both",
                    "target_patterns": ["review_lessons", "waboose", "agent_arena"],
                    "required_evidence": ["exact_source", "crucible_replay", "focused_tests"],
                    "suggested_tools": ["pytest", "ruff", "jsonschema"],
                },
                {
                    "name": "dependency_impact",
                    "question": "Can any reviewer payload or detector grant mutation or promotion authority?",
                    "risk": "authority",
                    "direction": "both",
                    "target_patterns": ["automatic_", "patch_authority", "human_review"],
                    "required_evidence": ["tamper_test", "contract_invariant"],
                    "suggested_tools": ["pytest"],
                },
            ],
            "invariants": plan["acceptance_criteria"],
            "risk_map": plan["risk_map"],
            "agent_name": "none",
            "graph_depth": 2,
            "graph_node_budget": 160,
            "run_tests": False,
            "run_optional_tools": False,
            "metadata": {
                "harness_version": HARNESS_VERSION,
                "council_version": ARCHITECT_COUNCIL_V3,
                "surgeon_mode": "PROPOSE",
            },
        }
    )
    if waboose_prepared.get("ok"):
        waboose_scanned = bridge.aura_waboose_scan(waboose_prepared["review_id"])
        waboose_final = bridge.aura_waboose_finalize(waboose_prepared["review_id"])
    else:
        waboose_scanned = {"ok": False, "status": "prepare_failed"}
        waboose_final = {"ok": False, "status": "prepare_failed"}

    crucible = bridge.aura_waboose_crucible_replay()
    act_capsules = list(prepared.get("act_capsules") or [])
    surgeon_slices = [
        {
            "task_id": str(item.get("task_id") or ""),
            "target_file": str(item.get("target_file") or item.get("file") or ""),
            "target_symbol": str(item.get("target_symbol") or item.get("symbol") or ""),
            "slice_hash": str(item.get("slice_hash") or item.get("capsule_hash") or ""),
            "authority": "proposal_only",
        }
        for item in act_capsules[:40]
        if isinstance(item, dict)
    ]
    if not surgeon_slices:
        surgeon_slices = [
            {
                "task_id": task["task_id"],
                "target_file": task["target_file"],
                "target_symbol": "",
                "slice_hash": "TO_BE_BOUND_BY_AGENT_BRIDGE",
                "authority": "proposal_only",
            }
            for task in plan["act_tasks"]
        ]

    expected_lanes = {"scope", "tests", "sequence", "continuity", "rollback", "cost"}
    checks = {
        "repo_head_available": head != "UNAVAILABLE",
        "agent_bridge_repo_digest_ok": bool(repo_digest.get("ok", True)),
        "agent_bridge_prepare_ok": bool(prepared.get("ok")),
        "atomic_inventory_returned": isinstance(atomic, dict),
        "emergent_evidence_invoked": isinstance(emergent, dict),
        "council_v3_all_justified_lanes_selected": set(council_lanes) == expected_lanes,
        "surgeon_control_is_proposal_only": surgeon_control["surgeon_mode"] == "PROPOSE",
        "surgeon_production_mutation_false": surgeon_control["production_mutation"] is False,
        "waboose_prepare_ok": bool(waboose_prepared.get("ok")),
        "waboose_scan_ok": bool(waboose_scanned.get("ok")),
        "waboose_finalize_ok": bool(waboose_final.get("ok")),
        "crucible_passed": crucible.get("status") == "PASSED" and crucible.get("failed_count") == 0,
        "human_review_required": True,
    }

    receipt: dict[str, Any] = {
        "version": HARNESS_VERSION,
        "objective": objective,
        "repository": {
            "root": str(repo_root),
            "head": head,
            "base_ref": base_ref,
            "head_ref": head_ref,
            "working_tree_status": _git(repo_root, "status", "--short"),
        },
        "coding_arena_and_agent_bridge": {
            "repo_digest": _summary(
                repo_digest,
                ("ok", "version", "repo_head", "file_count", "symbol_count", "hubs"),
            ),
            "architect_prepare": _summary(
                prepared,
                (
                    "ok",
                    "version",
                    "plan_phase_hash",
                    "status",
                    "routing_decisions",
                    "shadow_findings",
                    "patch_authority",
                    "production_mutation",
                ),
            ),
            "emergent_prepare_fallback": prepare_fallback,
            "act_capsule_count": len(act_capsules),
        },
        "connectome_and_atomic_inventory": {
            "affordances": _summary(
                affordances,
                ("grounding", "route_frame", "recommended_affordances", "patch_authority"),
            ),
            "atomic_inventory": _summary(
                atomic,
                (
                    "ok",
                    "version",
                    "inventory_digest",
                    "total_count",
                    "selected_count",
                    "patch_authority",
                ),
            ),
        },
        "emergent_properties": _summary(
            emergent,
            (
                "ok",
                "version",
                "packet_id",
                "packet_digest",
                "status",
                "grounding_ok",
                "waboose_focus_directives",
                "emergent_compositions",
                "tests",
                "patch_authority",
            ),
        ),
        "council_v3": {
            "version": ARCHITECT_COUNCIL_V3,
            "selected_lanes": council_lanes,
            "length_profile": profile,
            "supplemental_rubrics": [
                "security_and_authority",
                "protocol_and_interchange",
                "evidence_and_boundedness",
            ],
        },
        "surgeon": {
            "control_profile": surgeon_control,
            "slices": surgeon_slices,
            "execution_performed": False,
            "reason": "The harness prepares proposal-only exact slices; implementation remains the current coding agent's reviewed branch work.",
        },
        "coding_waboose": {
            "prepare": _summary(
                waboose_prepared,
                ("ok", "review_id", "status", "review_lesson_context", "automatic_merge"),
            ),
            "scan": _summary(
                waboose_scanned,
                (
                    "ok",
                    "status",
                    "review_lesson_findings_added",
                    "review_lesson_crucible",
                    "automatic_merge",
                ),
            ),
            "finalize": _summary(
                waboose_final,
                ("ok", "status", "finding_count", "repair_request_count", "automatic_merge"),
            ),
        },
        "crucible": _summary(
            crucible,
            (
                "version",
                "status",
                "registry_digest",
                "scenario_count",
                "passed_count",
                "failed_count",
                "packet_digest",
            ),
        ),
        "checks": checks,
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "evidence_semantics": {
            "harness_execution": "current_head_execution",
            "workflow_configuration": "not_a_pass_without_observed_run",
            "generated_maps": "not_reviewed_or_regenerated_by_this_harness",
            "external_reviews": "teacher_signals_requiring_exact_source_corroboration",
        },
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    receipt["receipt_digest"] = _digest(receipt)
    body = _canonical(receipt)
    if len(body) > _MAX_RECEIPT_BYTES:
        raise RuntimeError("architect harness receipt exceeds canonical byte ceiling")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base-ref", default=os.environ.get("AURA_BASE_REF", "HEAD~1"))
    parser.add_argument("--head-ref", default=os.environ.get("AURA_HEAD_REF", "HEAD"))
    parser.add_argument(
        "--output",
        default="Aura_Staging/review_learning_harness/architect_receipt.json",
    )
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    receipt = run(root, base_ref=str(args.base_ref), head_ref=str(args.head_ref))
    output = root / str(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
