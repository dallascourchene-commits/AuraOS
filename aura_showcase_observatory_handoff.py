"""Review-only handoffs from the Aura Observatory into governed Arenas.

The Observatory explains and packages an already compiled intent trace. It does not
execute a worker, create an ArenaExperience, or grant patch authority. A Human Agent
handoff imports only bounded objective and grounding evidence. A Learning Arena intake
remains ineligible until a governed Arena execution produces verified experience.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
OBSERVATORY_HANDOFF_VERSION = "AURA_OBSERVATORY_HANDOFF_V1"


def _digest(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def build_observatory_handoff(trace: dict[str, Any]) -> dict[str, Any]:
    """Build a bounded, review-only Human Agent packet from one compiled trace."""
    raw = dict(trace or {})
    objective = str(raw.get("objective") or "").strip()
    if raw.get("ok") is not True or not objective:
        return _denial("valid_compiled_trace_required")

    grounding = dict(raw.get("grounding") or {})
    likely_files = [
        str(item) for item in raw.get("likely_files", []) if str(item)
    ][:8]
    likely_symbols = [
        str(item) for item in raw.get("likely_symbols", []) if str(item)
    ][:8]
    source_spans = [
        dict(item)
        for item in grounding.get("source_spans", [])
        if isinstance(item, dict)
    ][:8]
    tests = [
        str(item) for item in grounding.get("tests", []) if str(item)
    ][:8]
    topology = dict(raw.get("topology_packet") or {})
    workspace = dict(topology.get("workspace") or {})
    route = dict(raw.get("machine_route") or raw.get("route_decision") or {})
    slots = dict((raw.get("six_slot_packet") or {}).get("slots") or {})

    localized_files = list(
        dict.fromkeys(
            [
                *likely_files,
                str(grounding.get("target_file") or ""),
                *[
                    str(item.get("file_path") or "")
                    for item in source_spans
                ],
            ]
        )
    )
    localized_files = [item for item in localized_files if item][:8]
    localized_symbols = list(
        dict.fromkeys(
            [
                *likely_symbols,
                str(grounding.get("target_symbol") or ""),
                *[
                    str(item.get("symbol") or "")
                    for item in source_spans
                ],
            ]
        )
    )
    localized_symbols = [item for item in localized_symbols if item][:8]

    trace_identity = {
        "objective": objective,
        "compressed_objective": raw.get("compressed_objective", ""),
        "routing_frame": raw.get("routing_frame", {}),
        "machine_route": route,
        "six_slot_packet": slots,
        "likely_files": localized_files,
        "likely_symbols": localized_symbols,
    }
    trace_digest = _digest(trace_identity)
    return {
        "ok": True,
        "version": OBSERVATORY_HANDOFF_VERSION,
        "handoff_kind": "OBSERVATORY_TO_HUMAN_AGENT",
        "observatory_trace_digest": trace_digest,
        "objective": objective,
        "issue": {
            "title": "Observatory-compiled intention",
            "question": objective,
            "truth_class": "COMPILED_AND_GROUNDED_TRACE",
        },
        "grounding": {
            "localized_files": localized_files,
            "localized_symbols": localized_symbols,
            "line_ranges": source_spans,
            "source_hashes": dict(grounding.get("hashes") or {}),
            "truth_class": "EXACT_REPOSITORY_FACTS_WHERE_PRESENT",
            "grounding": (
                "grounded"
                if localized_files or localized_symbols
                else "NEEDS_GROUNDING"
            ),
        },
        "test_targets": tests,
        "intent_slots": slots,
        "routing_frame": dict(raw.get("routing_frame") or {}),
        "route_decision": route,
        "agent_handoff": dict(raw.get("agent_handoff") or {}),
        "topology_summary": {
            "returned_node_count": int(
                workspace.get("returned_node_count") or 0
            ),
            "returned_link_count": int(
                workspace.get("returned_link_count") or 0
            ),
            "selected_node_ids": list(
                workspace.get("selected_node_ids") or []
            )[:4],
            "full_topology_transferred": False,
        },
        "production_mutation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def import_observatory_trace_into_workflow(
    workflow: Any,
    trace: dict[str, Any],
) -> dict[str, Any]:
    """Open a clean Human Agent workflow from one Observatory trace."""
    packet = build_observatory_handoff(trace)
    if not packet.get("ok"):
        return packet

    snapshot = _snapshot_workflow(workflow)
    try:
        workflow.objective = ""
        workflow.evidence.clear()
        workflow.last_result = {}
        framed = workflow.execute_guarded(
            "set_objective",
            {"objective": packet["objective"]},
        )
    except Exception as exc:  # noqa: BLE001
        _restore_workflow(workflow, snapshot)
        return {
            "ok": False,
            "error": f"workflow_objective_error:{type(exc).__name__}",
            "handoff": packet,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    if not framed.get("ok"):
        _restore_workflow(workflow, snapshot)
        return {
            "ok": False,
            "error": "workflow_objective_denied",
            "workflow_result": framed,
            "handoff": packet,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    grounding = dict(packet["grounding"])
    workflow.evidence.update(
        {
            "grounding": grounding,
            "affected_files": list(
                grounding.get("localized_files") or []
            ),
            "observatory_trace_digest": packet[
                "observatory_trace_digest"
            ],
            "observatory_intent_slots": dict(
                packet.get("intent_slots") or {}
            ),
            "observatory_route_decision": dict(
                packet.get("route_decision") or {}
            ),
            "observatory_agent_handoff": dict(
                packet.get("agent_handoff") or {}
            ),
            "observatory_topology_summary": dict(
                packet.get("topology_summary") or {}
            ),
        }
    )
    if packet.get("test_targets"):
        workflow.evidence["test_targets"] = list(packet["test_targets"])

    phase_compilation = _safe_compile_observatory_phase_capsules(
        workflow,
        packet,
    )
    cost_record: dict[str, Any] | None = None
    if phase_compilation.get("ok"):
        workflow.evidence.update(
            {
                "grounded_phase_capsules": list(
                    phase_compilation.get("phase_capsules") or []
                ),
                "grounding_evidence_id": phase_compilation.get(
                    "grounding_evidence_id", ""
                ),
                "grounding_evidence": dict(
                    phase_compilation.get("grounding_evidence") or {}
                ),
                "phase_capsule_context_cost": dict(
                    phase_compilation.get("context_cost_accounting") or {}
                ),
            }
        )
        cost_record = _record_observatory_cost_projection(
            workflow,
            packet,
            phase_compilation,
        )
        workflow.evidence["phase_capsule_cost_observatory"] = cost_record
        if cost_record.get("actual_run_id"):
            workflow.evidence["cost_run_id"] = cost_record["actual_run_id"]

    learning_intake = build_learning_intake(trace)
    workflow.evidence["learning_arena_intake"] = learning_intake
    if hasattr(workflow, "_event"):
        workflow._event(
            "observatory_handoff",
            (
                "Imported bounded trace "
                f"{packet['observatory_trace_digest'][:12]}"
            ),
        )
        if phase_compilation.get("ok"):
            workflow._event(
                "phase_capsule_compiled",
                (
                    "Compiled shared evidence "
                    f"{phase_compilation['grounding_evidence_id'][:16]}"
                ),
            )

    next_actions = ["export_handoff"]
    if phase_compilation.get("ok"):
        next_actions.insert(0, "prepare_capsule")
    else:
        next_actions.insert(0, "ground_context")

    return {
        "ok": True,
        "handoff": packet,
        "phase_capsule_compilation": phase_compilation,
        "phase_capsule_cost_observatory": cost_record,
        "learning_intake": learning_intake,
        "workflow": workflow.get_state(),
        "next_actions": next_actions,
        "note": (
            "A clean Human Agent workflow was opened from the compiled intent. "
            "Grounded phase capsules are evidence references only; "
            "no patch was staged or applied."
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _snapshot_workflow(workflow: Any) -> dict[str, Any]:
    events = getattr(workflow, "events", None)
    return {
        "objective": getattr(workflow, "objective", ""),
        "evidence": dict(getattr(workflow, "evidence", {}) or {}),
        "last_result": dict(getattr(workflow, "last_result", {}) or {}),
        "events": list(events) if isinstance(events, list) else None,
    }


def _restore_workflow(
    workflow: Any,
    snapshot: dict[str, Any],
) -> None:
    workflow.objective = snapshot["objective"]
    workflow.evidence.clear()
    workflow.evidence.update(snapshot["evidence"])
    workflow.last_result = dict(snapshot["last_result"])
    if snapshot["events"] is not None and isinstance(
        getattr(workflow, "events", None),
        list,
    ):
        workflow.events[:] = snapshot["events"]


def _safe_compile_observatory_phase_capsules(
    workflow: Any,
    packet: dict[str, Any],
) -> dict[str, Any]:
    try:
        return _compile_observatory_phase_capsules(workflow, packet)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": (
                "phase_capsule_compilation_unavailable:"
                f"{type(exc).__name__}"
            ),
            "phase_capsules": [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def _compile_observatory_phase_capsules(
    workflow: Any,
    packet: dict[str, Any],
) -> dict[str, Any]:
    from aura_cockpit_planner import objective_to_phase_capsules

    grounding = dict(packet.get("grounding") or {})
    spans = [
        dict(item)
        for item in grounding.get("line_ranges", [])
        if isinstance(item, dict)
    ]
    hashes = dict(grounding.get("source_hashes") or {})
    exact_files = [
        str(item.get("file_path") or "")
        for item in spans
        if item.get("file_path")
    ]
    target_file = exact_files[0] if exact_files else ""
    target_symbol = str(
        (spans[0] if spans else {}).get("symbol") or ""
    )
    grounding_packet = {
        "version": "AURA_OBSERVATORY_GROUNDING_HANDOFF_V1",
        "anchor_version": "OBSERVATORY_TRACE",
        "grounding_ok": bool(spans and hashes and target_file),
        "route": str(
            (packet.get("route_decision") or {}).get("route")
            or "HUMAN_AGENT_ARENA"
        ),
        "target_file": target_file,
        "target_symbol": target_symbol or None,
        "source_spans": spans,
        "tests": list(packet.get("test_targets") or []),
        "hashes": hashes,
        "route_reasons": [
            "observatory_compiled_trace",
            "exact_evidence_reused_before_regrounding",
        ],
        "safety_policy": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    return objective_to_phase_capsules(
        packet["objective"],
        repo_root=str(getattr(workflow, "repo_root", ".")),
        grounding_packet=grounding_packet,
    )


def _record_observatory_cost_projection(
    workflow: Any,
    packet: dict[str, Any],
    phase_compilation: dict[str, Any],
) -> dict[str, Any]:
    from aura_cost_experiment_runner import (
        record_structural_context_projection,
    )

    repo_root = getattr(workflow, "repo_root", None)
    if repo_root is None:
        return {
            "ok": False,
            "reason": "workflow_repo_root_unavailable",
            "persistent": False,
            "measurement_class": "ESTIMATED",
            "eligible_for_crucible": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    return record_structural_context_projection(
        dict(phase_compilation.get("context_cost_accounting") or {}),
        repo_root=str(repo_root),
        objective=packet["objective"],
        task_id=str(getattr(workflow, "workflow_id", "") or ""),
        arena_id="human_agent",
        correlation_id=packet["observatory_trace_digest"],
    )


def build_learning_intake(trace: dict[str, Any]) -> dict[str, Any]:
    """Build a transparent pre-experience intake for the real Crucible."""
    packet = build_observatory_handoff(trace)
    if not packet.get("ok"):
        return packet
    return {
        "ok": True,
        "version": OBSERVATORY_HANDOFF_VERSION,
        "handoff_kind": "OBSERVATORY_TO_LEARNING_ARENA_INTAKE",
        "status": "AWAITING_VERIFIED_EXPERIENCE",
        "eligible_for_crucible": False,
        "objective": packet["objective"],
        "observatory_trace_digest": packet[
            "observatory_trace_digest"
        ],
        "intent_slots": packet["intent_slots"],
        "route_decision": packet["route_decision"],
        "localized_files": packet["grounding"]["localized_files"],
        "localized_symbols": packet["grounding"][
            "localized_symbols"
        ],
        "required_sequence": [
            "HUMAN_AGENT_OR_OTHER_GOVERNED_ARENA_EXECUTION",
            "VERIFIER_EVIDENCE",
            "OUTCOME_VECTOR",
            "ARENA_EXPERIENCE_V3_RECORD",
            "TRAIN_VALIDATION_SHADOW",
            "CRYSTALLIZATION_PROPOSED",
            "VERIFIER_AND_HUMAN_REVIEW",
        ],
        "reason": (
            "The Crucible learns from verified ArenaExperience records, "
            "not directly from a raw intention. This intake preserves "
            "the question and lineage until governed execution produces "
            "observable evidence."
        ),
        "production_mutation": False,
        "automatic_grammar_promotion": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _denial(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "build_learning_intake",
    "build_observatory_handoff",
    "import_observatory_trace_into_workflow",
]
