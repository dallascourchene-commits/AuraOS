"""
Aura Agent Arena Bridge — CLI wrapper.

Exposes all bridge tools as shell commands so any CLI-based agent can use
Aura's Coding Arena without MCP support.

Usage:
    python -m aura_agent_arena_cli digest
    python -m aura_agent_arena_cli prepare --objective "..." --target-file ... --target-symbol ...
    python -m aura_agent_arena_cli search --query "..." --kind symbol
    python -m aura_agent_arena_cli context --task-id A1 --format both
    python -m aura_agent_arena_cli read-slice --file aura_fst_routing.py --symbol AuraCodingArenaRouter
    python -m aura_agent_arena_cli fireworks-patch --task-id A1 --instruction "..."
    python -m aura_agent_arena_cli stage-patch --task-id A1 --diff-file patch.diff
    python -m aura_agent_arena_cli verify --scope declared
    python -m aura_agent_arena_cli repair-packet --task-id A1
    python -m aura_agent_arena_cli status
    python -m aura_agent_arena_cli export-icm
    python -m aura_agent_arena_cli find-affordances --objective "refactor coding arena"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_fireworks import fireworks_patch_worker

# Hermes Arena Mode — optional import (additive, does not break existing CLI)
try:
    from aura_hermes_arena_mode import (
        generate_hermes_contract,
        generate_pr_runbook,
        generate_token_savings_report,
        run_preflight,
        write_hermes_aura_rules,
    )
    _HERMES_MODE_AVAILABLE = True
except Exception:  # noqa: BLE001
    _HERMES_MODE_AVAILABLE = False

# Native Cockpit — optional import (additive, does not break existing CLI)
try:
    from aura_native_cockpit import AuraNativeCockpit
    from aura_intent_ingestion import (
        parse_intent_document,
        compile_intent_packet,
        route_intent_to_lexc,
    )
    from aura_capability_connectome import (
        build_capability_connectome,
        find_capability_path,
    )
    from aura_token_economy_orchestrator import compute_token_economy
    from aura_workflow_gates import workflow_state_machine
    _NATIVE_COCKPIT_AVAILABLE = True
except Exception:  # noqa: BLE001
    _NATIVE_COCKPIT_AVAILABLE = False

# Capability Orchestration — optional import (additive)
try:
    from aura_capability_lane_registry import lane_registry_packet, explain_lane, list_lane_ids
    from aura_cockpit_capability_router import route_capability_lanes
    _CAPABILITY_LANES_AVAILABLE = True
except Exception:  # noqa: BLE001
    _CAPABILITY_LANES_AVAILABLE = False

# Coding Workbench — optional import (additive)
try:
    from aura_topology_health import topology_health_packet
    from aura_coding_workbench_actions import (
        open_workspace, scope_task, filter_context, localize_code,
        rank_code_regions as _rank_regions, slice_context as _slice_ctx,
        build_change_graph as _build_cg, detect_refactor_candidates as _detect_rc,
        split_work as _split_work, prepare_agent_handoff as _prep_handoff,
    )
    from aura_change_graph import build_change_graph
    from aura_refactor_candidate import detect_refactor_candidates
    from aura_work_splitter import split_large_objective
    from aura_command_risk_gate import classify_command_risk, command_risk_packet
    from aura_agent_workbench_interface import agent_workbench_contract
    _WORKBENCH_AVAILABLE = True
except Exception:  # noqa: BLE001
    _WORKBENCH_AVAILABLE = False

# Cost Observatory — optional import (additive)
try:
    from aura_usage_normalizer import normalize_usage
    from aura_pricing_registry import PricingRegistry
    from aura_empirical_cost_ledger import EmpiricalCostLedger
    from aura_cost_attribution import AttributionLedger
    from aura_cost_experiment_runner import (
        run_replay_experiment, run_shadow_baseline, comparison_report,
        compute_quality_normalized_metrics, create_comparison_id,
    )
    from aura_cost_telemetry_events import get_telemetry_stream
    _COST_OBSERVATORY_AVAILABLE = True
except Exception:  # noqa: BLE001
    _COST_OBSERVATORY_AVAILABLE = False

# Capability Resolver + Stabilization — optional import (additive)
try:
    from aura_capability_resolver import resolve_capabilities
    from aura_system_stabilization import stabilization_status
    _CAPABILITY_RESOLVER_AVAILABLE = True
except Exception:  # noqa: BLE001
    _CAPABILITY_RESOLVER_AVAILABLE = False

# Ephemeral Organ Runtime — optional import (additive)
try:
    from aura_ephemeral_runtime import (
        plan_ephemeral_organ, validate_ephemeral_organ, run_ephemeral_organ,
        ephemeral_status, dissolve_ephemeral_organ, ephemeral_receipt,
    )
    _EPHEMERAL_AVAILABLE = True
except Exception:  # noqa: BLE001
    _EPHEMERAL_AVAILABLE = False

# Civic Commons Arena — optional import (additive)
try:
    from aura_civic_runtime import (
        create_civic_session, get_session, run_full_demo, add_contribution,
        match_resources, run_mitosis, run_scenarios, get_consent, record_consent_response,
        run_what_if, create_pilot, get_issue_pulse, export_packet,
        close_session, civic_status,
    )
    _CIVIC_AVAILABLE = True
except Exception:  # noqa: BLE001
    _CIVIC_AVAILABLE = False

# Tensor Evidence Engine — optional import (additive)
try:
    from aura_coding_tensor_adapter import analyze_coding_region
    from aura_civic_tensor_adapter import analyze_civic_session
    from aura_tensor_evidence import TensorBeliefEngine, compress_factor
    _TENSOR_AVAILABLE = True
except Exception:  # noqa: BLE001
    _TENSOR_AVAILABLE = False

# Module-level bridge instance — persists across CLI calls within one process.
_bridge: AuraAgentArenaBridge | None = None
# Module-level plan_phase_hash — set by prepare, used by subsequent commands.
_plan_phase_hash: str | None = None


def _get_bridge() -> AuraAgentArenaBridge:
    global _bridge
    if _bridge is None:
        _bridge = AuraAgentArenaBridge()
    return _bridge


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def _load_plan_phase_hash() -> str | None:
    """Load plan_phase_hash from env or a temp file."""
    global _plan_phase_hash
    if _plan_phase_hash:
        return _plan_phase_hash
    env_hash = os.environ.get("AURA_ARENA_PLAN_PHASE_HASH", "")
    if env_hash:
        return env_hash
    # Try loading from temp file.
    try:
        from pathlib import Path

        p = Path("/tmp/aura_arena_plan_phase_hash")
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _save_plan_phase_hash(phase_hash: str) -> None:
    global _plan_phase_hash
    _plan_phase_hash = phase_hash
    try:
        from pathlib import Path

        Path("/tmp/aura_arena_plan_phase_hash").write_text(phase_hash, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _require_plan_phase_hash() -> str:
    phase_hash = _load_plan_phase_hash()
    if not phase_hash:
        print(json.dumps({
            "ok": False,
            "error": "No plan_phase_hash found. Run 'prepare' first or set AURA_ARENA_PLAN_PHASE_HASH env.",
        }, indent=2))
        raise SystemExit(1)
    return phase_hash


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_digest(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_repo_digest(
        include_hubs=not args.no_hubs,
        max_lines=args.max_lines,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_prepare(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_prepare_arena(
        objective=args.objective,
        target_file=args.target_file,
        target_symbol=args.target_symbol,
        acceptance_criteria=args.acceptance_criteria.split(",") if args.acceptance_criteria else None,
        risk_map=args.risk_map.split(",") if args.risk_map else None,
        constraints=args.constraints.split(",") if args.constraints else None,
    )
    if result.get("ok") and result.get("plan_phase_hash"):
        _save_plan_phase_hash(result["plan_phase_hash"])
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_search(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_search_code(
        query=args.query,
        search_kind=args.kind,
        max_results=args.max_results,
        include_neighbors=not args.no_neighbors,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_context(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_get_micro_context(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
        depth=args.depth,
        format=args.format,
        max_tokens_est=args.max_tokens,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_read_slice(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_read_slice(
        file=args.file,
        symbol=args.symbol,
        line_start=args.line_start,
        line_end=args.line_end,
        max_lines=args.max_lines,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_fireworks_patch(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()

    # Get compressed context for the task.
    context_result = bridge.aura_get_micro_context(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
    )
    compressed_context = context_result.get("compressed_context", "")

    result = fireworks_patch_worker(
        task_id=args.task_id,
        compressed_context=compressed_context,
        instruction=args.instruction,
        model_tier=args.model_tier,
        max_output_tokens=args.max_output_tokens,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_stage_patch(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()

    # Read diff from file or stdin.
    diff_content = ""
    if args.diff_file:
        try:
            with open(args.diff_file, "r", encoding="utf-8") as f:
                diff_content = f.read()
        except OSError as exc:
            print(json.dumps({"ok": False, "error": f"Cannot read diff file: {exc}"}, indent=2))
            return 1
    elif args.diff:
        diff_content = args.diff
    else:
        # Read from stdin.
        diff_content = sys.stdin.read()

    result = bridge.aura_stage_patch(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
        owner=args.owner,
        diff=diff_content,
        affected_files=args.affected_files.split(",") if args.affected_files else [],
        affected_symbols=args.affected_symbols.split(",") if args.affected_symbols else None,
        tests=args.tests.split(",") if args.tests else None,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_verify(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_verify_arena(
        plan_phase_hash=phase_hash,
        test_scope=args.scope,
        runner=args.runner,
        max_log_lines=args.max_log_lines,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_repair_packet(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_repair_packet(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
        failure_id=args.failure_id,
        max_tokens_est=args.max_tokens,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_status(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_hotswap_status(
        plan_phase_hash=phase_hash,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_export_icm(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_export_icm(
        plan_phase_hash=phase_hash,
        workspace_root=args.workspace_root,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_find_affordances(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_find_affordances(
        objective=args.objective,
        target_files=[item.strip() for item in args.target_files.split(",") if item.strip()] if args.target_files else None,
        target_symbols=[item.strip() for item in args.target_symbols.split(",") if item.strip()] if args.target_symbols else None,
        include_affordances=not args.no_affordances,
        top_k=args.top_k,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Hermes Arena Mode command handlers
# ---------------------------------------------------------------------------


def _require_hermes_mode() -> None:
    """Raise SystemExit if Hermes Arena Mode is not available."""
    if not _HERMES_MODE_AVAILABLE:
        print(json.dumps({
            "ok": False,
            "error": "Hermes Arena Mode is not available. Ensure aura_hermes_arena_mode.py is importable.",
        }, indent=2))
        raise SystemExit(1)


def cmd_hermes_contract(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    result = generate_hermes_contract(
        objective=args.objective,
        mode=args.mode,
        repo_root=".",
    )
    if args.json:
        _print_json(result)
    else:
        if result.get("ok"):
            print(result.get("contract", ""))
        else:
            _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_preflight(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    target_files = None
    if args.target_files:
        target_files = [f.strip() for f in args.target_files.split(",") if f.strip()]
    target_symbols = None
    if args.target_symbols:
        target_symbols = [s.strip() for s in args.target_symbols.split(",") if s.strip()]
    result = run_preflight(
        objective=args.objective,
        repo_root=".",
        target_files=target_files,
        target_symbols=target_symbols,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_token_report(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    result = generate_token_savings_report(
        objective=args.objective,
        files=files,
        repo_root=".",
        include_preflight=args.include_preflight,
        output_format=args.format,
    )
    if args.format == "markdown" and result.get("ok"):
        print(result.get("markdown", ""))
    else:
        _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_pr_runbook(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    files = None
    if args.files:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
    result = generate_pr_runbook(
        objective=args.objective,
        branch=args.branch,
        repo_root=".",
        files=files,
    )
    if args.json:
        _print_json(result)
    else:
        if result.get("ok"):
            print(result.get("runbook", ""))
        else:
            _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_write_rules(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    result = write_hermes_aura_rules(repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Native Cockpit command handlers
# ---------------------------------------------------------------------------


def _require_native_cockpit() -> None:
    """Raise SystemExit if Native Cockpit is not available."""
    if not _NATIVE_COCKPIT_AVAILABLE:
        print(json.dumps({
            "ok": False,
            "error": "Native Cockpit is not available. Ensure aura_native_cockpit.py and related modules are importable.",
        }, indent=2))
        raise SystemExit(1)


def cmd_ingest_intent(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    cockpit = AuraNativeCockpit(repo_root=".")
    result = cockpit.ingest_intent(args.file)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_validate_lexc_route(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    cockpit = AuraNativeCockpit(repo_root=".")
    result = cockpit.validate_lexc_route(args.file)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_capability_connectome(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    result = build_capability_connectome(repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_capability_path(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    result = find_capability_path(args.objective, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_token_economy_cli(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    result = compute_token_economy(args.objective, files, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_workflow_gates(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    result = workflow_state_machine()
    _print_json(result)
    return 0 if result.get("ok", True) else 1


def cmd_native_cockpit_contract(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    cockpit = AuraNativeCockpit(repo_root=".")
    result = cockpit.cockpit_contract(args.objective)
    if args.json:
        _print_json(result)
    else:
        if result.get("ok"):
            print(result.get("contract", ""))
        else:
            _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_prepare_native_handoff(args: argparse.Namespace) -> int:
    _require_native_cockpit()
    cockpit = AuraNativeCockpit(repo_root=".")
    # First ingest the intent
    packet = cockpit.ingest_intent(args.intent_file)
    if not packet.get("ok"):
        _print_json(packet)
        return 1
    # Then prepare handoff
    result = cockpit.prepare_handoff(packet, agent=args.agent)
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Capability Orchestration command handlers
# ---------------------------------------------------------------------------


def _require_capability_lanes() -> None:
    if not _CAPABILITY_LANES_AVAILABLE:
        print(json.dumps({"ok": False, "error": "Capability lanes not available."}, indent=2))
        raise SystemExit(1)


def cmd_capability_lanes(args: argparse.Namespace) -> int:
    _require_capability_lanes()
    result = lane_registry_packet()
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_route_lanes(args: argparse.Namespace) -> int:
    _require_capability_lanes()
    result = route_capability_lanes(args.objective)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_music_rank(args: argparse.Namespace) -> int:
    try:
        from aura_music_mitosis_adapter import music_rank_cockpit_candidates
        candidates = []
        if args.candidates:
            candidates = [c.strip() for c in args.candidates.split(",") if c.strip()]
        result = music_rank_cockpit_candidates(args.objective, candidates, repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_mitosis_split(args: argparse.Namespace) -> int:
    try:
        from aura_music_mitosis_adapter import mitosis_split_objective
        result = mitosis_split_objective(args.objective, repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_research_evidence(args: argparse.Namespace) -> int:
    try:
        from aura_research_cockpit_adapter import research_manifest_search, research_to_cockpit_evidence_packet
        search = research_manifest_search(args.objective, repo_root=".", offline=args.offline)
        evidence = research_to_cockpit_evidence_packet(search, repo_root=".")
        result = {"ok": True, "search": search, "evidence": evidence,
                  "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_skillweave(args: argparse.Namespace) -> int:
    try:
        from aura_skill_cockpit_adapter import discover_skills_for_objective
        result = discover_skills_for_objective(args.objective, repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_goap_plan(args: argparse.Namespace) -> int:
    try:
        from aura_cockpit_planner import plan_objective_with_goap
        result = plan_objective_with_goap(args.objective, repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_swarm_plan(args: argparse.Namespace) -> int:
    try:
        from aura_cockpit_swarm import build_swarm_plan
        agents = [a.strip() for a in args.agents.split(",") if a.strip()]
        result = build_swarm_plan(args.objective, agents=agents, repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_phase_capsules(args: argparse.Namespace) -> int:
    try:
        from aura_cockpit_planner import objective_to_phase_capsules
        result = objective_to_phase_capsules(args.objective, repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_live_stage_plan(args: argparse.Namespace) -> int:
    try:
        from aura_live_architect_cockpit_adapter import live_stage_review_packet
        result = live_stage_review_packet(args.objective, repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_cockpit_audit(args: argparse.Namespace) -> int:
    try:
        from aura_cockpit_audit_trail import export_cockpit_audit_packet
        result = export_cockpit_audit_packet(repo_root=".")
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False}
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Coding Workbench command handlers
# ---------------------------------------------------------------------------


def _require_workbench() -> None:
    if not _WORKBENCH_AVAILABLE:
        print(json.dumps({"ok": False, "error": "Coding Workbench not available."}, indent=2))
        raise SystemExit(1)


def cmd_topology_health(args: argparse.Namespace) -> int:
    _require_workbench()
    result = topology_health_packet(repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_open_workspace(args: argparse.Namespace) -> int:
    _require_workbench()
    result = open_workspace(repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_scope_task(args: argparse.Namespace) -> int:
    _require_workbench()
    result = scope_task(args.objective, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_filter_context(args: argparse.Namespace) -> int:
    _require_workbench()
    result = filter_context(args.objective, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_localize_code(args: argparse.Namespace) -> int:
    _require_workbench()
    result = localize_code(args.objective, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_rank_code_regions_cli(args: argparse.Namespace) -> int:
    _require_workbench()
    result = _rank_regions(args.objective, repo_root=".", max_lines=args.max_lines)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_slice_context_cli(args: argparse.Namespace) -> int:
    _require_workbench()
    # Load ranking from file or use empty
    loc = {}
    if args.ranking_file:
        try:
            with open(args.ranking_file, "r", encoding="utf-8") as f:
                loc = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(json.dumps({
                "ok": False,
                "error": f"Could not load ranking file '{args.ranking_file}': {exc}",
            }, indent=2))
            return 1
    result = _slice_ctx(loc, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_change_graph_cli(args: argparse.Namespace) -> int:
    _require_workbench()
    result = _build_cg(args.objective, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_refactor_candidates_cli(args: argparse.Namespace) -> int:
    _require_workbench()
    graph = _build_cg(args.objective, repo_root=".")
    if not graph.get("ok"):
        _print_json(graph)
        return 1
    result = _detect_rc(graph, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_split_work_cli(args: argparse.Namespace) -> int:
    _require_workbench()
    result = _split_work(args.objective, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_command_risk_cli(args: argparse.Namespace) -> int:
    _require_workbench()
    result = classify_command_risk(args.command, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_agent_workbench_contract(args: argparse.Namespace) -> int:
    _require_workbench()
    result = agent_workbench_contract(args.agent)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_prepare_agent_work(args: argparse.Namespace) -> int:
    _require_workbench()
    result = _prep_handoff(args.candidate_id, agent=args.agent, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Cost Observatory command handlers
# ---------------------------------------------------------------------------


def _require_cost_observatory() -> None:
    if not _COST_OBSERVATORY_AVAILABLE:
        print(json.dumps({"ok": False, "error": "Cost Observatory not available."}, indent=2))
        raise SystemExit(1)


def cmd_cost_status(args: argparse.Namespace) -> int:
    _require_cost_observatory()
    stream = get_telemetry_stream()
    ledger = EmpiricalCostLedger(repo_root=".")
    history = ledger.get_history(limit=5)
    ledger.close()
    result = {
        "ok": True,
        "event_count": stream.event_count(),
        "recent_runs": history,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }
    _print_json(result)
    return 0


def cmd_cost_run(args: argparse.Namespace) -> int:
    _require_cost_observatory()
    mode = "AURA_FULL_PIPELINE" if args.mode == "aura" else "RAW_AGENT"
    fixtures = {"AURA_FULL_PIPELINE": {"input_tokens": 500, "output_tokens": 200, "cost_usd": 0.005},
                "RAW_AGENT": {"input_tokens": 5000, "output_tokens": 2000, "cost_usd": 0.02}}
    result = run_replay_experiment(args.objective, "claude-sonnet-4-6", fixtures, mode=mode)
    # Persist to ledger
    ledger = EmpiricalCostLedger(repo_root=".")
    ledger.record_run(result["run"])
    ledger.close()
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_cost_baseline(args: argparse.Namespace) -> int:
    _require_cost_observatory()
    registry = PricingRegistry(repo_root=".")
    pricing = registry.calculate_cost("claude-sonnet-4-6", 20000, None)
    result = run_shadow_baseline(args.objective, "claude-sonnet-4-6", 80000, pricing)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_cost_compare(args: argparse.Namespace) -> int:
    _require_cost_observatory()
    ledger = EmpiricalCostLedger(repo_root=".")
    runs = ledger.get_comparison(args.comparison_id)
    ledger.close()
    if len(runs) < 2:
        print(json.dumps({"ok": False, "error": "Need at least 2 runs for comparison"}))
        return 1
    report = comparison_report(runs[-1], runs[0])  # Aura = last, Raw = first
    _print_json(report)
    return 0 if report.get("ok") else 1


def cmd_cost_report(args: argparse.Namespace) -> int:
    _require_cost_observatory()
    ledger = EmpiricalCostLedger(repo_root=".")
    runs = ledger.get_comparison(args.comparison_id)
    ledger.close()
    if not runs:
        print(json.dumps({"ok": False, "error": "No runs found"}))
        return 1
    if args.format == "markdown" and len(runs) >= 2:
        report = comparison_report(runs[-1], runs[0])
        # Simple markdown output
        lines = [f"# Cost Comparison Report ({args.comparison_id})", ""]
        metrics = report.get("metrics", {})
        for k, v in metrics.items():
            if v is not None:
                lines.append(f"- {k}: {v}")
        print("\n".join(lines))
    else:
        _print_json({"ok": True, "runs": runs, "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False})
    return 0


def cmd_cost_attribution(args: argparse.Namespace) -> int:
    _require_cost_observatory()
    ledger = EmpiricalCostLedger(repo_root=".")
    run = ledger.get_run(args.run_id)
    ledger.close()
    if not run:
        print(json.dumps({"ok": False, "error": "Run not found"}))
        return 1
    # Build attribution from run data
    attr = AttributionLedger()
    context_before = run.get("context_bytes_before", 0)
    context_after = run.get("context_bytes_after", 0)
    source_chars = run.get("source_chars_exposed", 0)

    # RAW_OBJECTIVE: initial context size
    if context_before > 0:
        attr.record_stage("RAW_OBJECTIVE", output_chars=context_before)

    # CODEMAP_LOCALIZED: context reduction from localization
    if context_before > 0 and source_chars > 0:
        attr.record_stage("CODEMAP_LOCALIZED", input_chars=context_before, output_chars=source_chars)

    # READ_SLICE: final context after all transformations
    if source_chars > 0 and context_after > 0:
        attr.record_stage("READ_SLICE", input_chars=source_chars, output_chars=context_after)

    report = attr.attribution_report()
    _print_json(report)
    return 0


def cmd_cost_history(args: argparse.Namespace) -> int:
    _require_cost_observatory()
    ledger = EmpiricalCostLedger(repo_root=".")
    history = ledger.get_history(limit=args.limit)
    ledger.close()
    _print_json({"ok": True, "runs": history, "count": len(history),
                 "patch_authority": "exact_source_spans_and_hashes_only", "vsa_patch_authority": False})
    return 0


# ---------------------------------------------------------------------------
# Capability Resolver + Stabilization command handlers
# ---------------------------------------------------------------------------


def _require_capability_resolver() -> None:
    if not _CAPABILITY_RESOLVER_AVAILABLE:
        print(json.dumps({"ok": False, "error": "Capability Resolver not available."}, indent=2))
        raise SystemExit(1)


def cmd_resolve_capabilities(args: argparse.Namespace) -> int:
    _require_capability_resolver()
    result = resolve_capabilities(
        args.objective, repo_root=".",
        target_files=args.target_files.split(",") if args.target_files else None,
        target_symbols=args.target_symbols.split(",") if args.target_symbols else None,
    )
    _print_json(result)
    return 0 if result.get("version") else 1


def cmd_stabilization_status(args: argparse.Namespace) -> int:
    _require_capability_resolver()
    result = stabilization_status(repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Ephemeral Organ Runtime command handlers
# ---------------------------------------------------------------------------


def _require_ephemeral() -> None:
    if not _EPHEMERAL_AVAILABLE:
        print(json.dumps({"ok": False, "error": "Ephemeral Runtime not available."}, indent=2))
        raise SystemExit(1)


def cmd_ephemeral_plan(args: argparse.Namespace) -> int:
    _require_ephemeral()
    result = plan_ephemeral_organ(args.objective, ttl_seconds=args.ttl, repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_ephemeral_validate(args: argparse.Namespace) -> int:
    _require_ephemeral()
    result = validate_ephemeral_organ(args.organ_id, repo_root=".", human_approval=args.human_approval)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_ephemeral_run(args: argparse.Namespace) -> int:
    _require_ephemeral()
    result = run_ephemeral_organ(args.organ_id, repo_root=".", human_approval=True)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_ephemeral_status(args: argparse.Namespace) -> int:
    _require_ephemeral()
    result = ephemeral_status(args.organ_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_ephemeral_dissolve(args: argparse.Namespace) -> int:
    _require_ephemeral()
    result = dissolve_ephemeral_organ(args.organ_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_ephemeral_receipt(args: argparse.Namespace) -> int:
    _require_ephemeral()
    result = ephemeral_receipt(args.organ_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Civic Commons Arena command handlers
# ---------------------------------------------------------------------------


def _require_civic() -> None:
    if not _CIVIC_AVAILABLE:
        print(json.dumps({"ok": False, "error": "Civic Commons Arena not available."}, indent=2))
        raise SystemExit(1)


def cmd_civic_demo(args: argparse.Namespace) -> int:
    _require_civic()
    result = run_full_demo(story=args.story)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_create(args: argparse.Namespace) -> int:
    _require_civic()
    result = create_civic_session(args.objective, fixture=True)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_status(args: argparse.Namespace) -> int:
    _require_civic()
    result = civic_status(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_profiles(args: argparse.Namespace) -> int:
    _require_civic()
    result = civic_status(args.session_id)
    if result.get("ok"):
        profiles = result["session"].get("profile_set", {})
        _print_json({"ok": True, "profiles": profiles})
        return 0
    _print_json(result)
    return 1


def cmd_civic_add_contribution(args: argparse.Namespace) -> int:
    _require_civic()
    import json as _json
    contrib = {}
    if args.file:
        with open(args.file) as f:
            contrib = _json.load(f)
    result = add_contribution(args.session_id, contrib)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_match_resources(args: argparse.Namespace) -> int:
    _require_civic()
    result = match_resources(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_mitosis(args: argparse.Namespace) -> int:
    _require_civic()
    result = run_mitosis(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_scenarios(args: argparse.Namespace) -> int:
    _require_civic()
    result = run_scenarios(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_respond(args: argparse.Namespace) -> int:
    _require_civic()
    import json as _json
    response = {}
    if args.file:
        with open(args.file) as f:
            response = _json.load(f)
    result = record_consent_response(args.session_id, response)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_consent(args: argparse.Namespace) -> int:
    _require_civic()
    result = get_consent(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_what_if(args: argparse.Namespace) -> int:
    _require_civic()
    import json as _json
    changes = {}
    if args.file:
        with open(args.file) as f:
            changes = _json.load(f)
    result = run_what_if(args.session_id, changes)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_pilot(args: argparse.Namespace) -> int:
    _require_civic()
    result = create_pilot(args.session_id, getattr(args, "scenario_id", ""))
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_issue_pulse(args: argparse.Namespace) -> int:
    _require_civic()
    result = get_issue_pulse(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_export(args: argparse.Namespace) -> int:
    _require_civic()
    result = export_packet(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_civic_close(args: argparse.Namespace) -> int:
    _require_civic()
    result = close_session(args.session_id)
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Tensor Evidence commands
# ---------------------------------------------------------------------------

def _require_tensor():
    if not _TENSOR_AVAILABLE:
        print(json.dumps({"ok": False, "error": "tensor evidence engine not available"}))
        raise SystemExit(1)


def cmd_tensor_analyze_coding(args: argparse.Namespace) -> int:
    _require_tensor()
    result = analyze_coding_region(
        node_ids=args.node_ids.split(",") if args.node_ids else [],
        source_grounded=args.grounded,
        tests_present=args.tests,
        dependency_depth=args.deps or 0,
        public_api_touched=args.public_api,
        external_effects=args.external.split(",") if args.external else [],
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_tensor_analyze_civic(args: argparse.Namespace) -> int:
    _require_tensor()
    from aura_civic_runtime import get_session
    s = get_session(args.session_id)
    if not s["ok"]:
        _print_json(s)
        return 1
    result = analyze_civic_session(s["session"])
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_tensor_compress(args: argparse.Namespace) -> int:
    _require_tensor()
    import numpy as np
    # Demo: compress a random low-rank matrix
    u = np.random.rand(8, 2); v = np.random.rand(2, 8)
    tensor = u @ v
    r = compress_factor(tensor, max_rank=args.max_rank, reconstruction_tolerance=args.tolerance)
    _print_json(r)
    return 0 if r.get("ok") else 1


def cmd_tensor_show_contradictions(args: argparse.Namespace) -> int:
    _require_tensor()
    if args.session_id:
        from aura_civic_runtime import get_session
        s = get_session(args.session_id)
        if s["ok"]:
            r = analyze_civic_session(s["session"])
            contradicted = r["tensor_evidence_analysis"]["contradicted_variables"]
            _print_json({"ok": True, "contradictions": contradicted,
                         "advisory": "Contradictions are advisory only.",
                         "patch_authority": "exact_source_spans_and_hashes_only"})
            return 0
    _print_json({"ok": False, "error": "no session selected"})
    return 1


def cmd_tensor_show_confinement(args: argparse.Namespace) -> int:
    _require_tensor()
    if args.session_id:
        from aura_civic_runtime import get_session
        s = get_session(args.session_id)
        if s["ok"]:
            r = analyze_civic_session(s["session"])
            conf = r["tensor_evidence_analysis"]["confinement"]
            _print_json({"ok": True, "confinement": conf, "advisory": True})
            return 0
    _print_json({"ok": False, "error": "no session selected"})
    return 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aura-agent-arena",
        description="Aura Agent Arena Bridge — CLI for external coding agents.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # digest
    p_digest = subparsers.add_parser("digest", help="Return repo orientation packet")
    p_digest.add_argument("--no-hubs", action="store_true", help="Exclude hub list")
    p_digest.add_argument("--max-lines", type=int, default=120, help="Max lines in output")
    p_digest.set_defaults(func=cmd_digest)

    # prepare
    p_prepare = subparsers.add_parser("prepare", help="Run Aura's prepare pipeline")
    p_prepare.add_argument("--objective", required=True, help="Task objective")
    p_prepare.add_argument("--target-file", default=None, help="Target file path")
    p_prepare.add_argument("--target-symbol", default=None, help="Target symbol name")
    p_prepare.add_argument("--acceptance-criteria", default=None, help="Comma-separated criteria")
    p_prepare.add_argument("--risk-map", default=None, help="Comma-separated risks")
    p_prepare.add_argument("--constraints", default=None, help="Comma-separated constraints")
    p_prepare.set_defaults(func=cmd_prepare)

    # search
    p_search = subparsers.add_parser("search", help="Search CODEMAP")
    p_search.add_argument("--query", required=True, help="Search query")
    p_search.add_argument("--kind", default="symbol", choices=["symbol", "file", "text", "command"])
    p_search.add_argument("--max-results", type=int, default=10)
    p_search.add_argument("--no-neighbors", action="store_true")
    p_search.set_defaults(func=cmd_search)

    # context
    p_context = subparsers.add_parser("context", help="Get micro-context for a task")
    p_context.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_context.add_argument("--format", default="both", choices=["capsule", "st3gg", "both"])
    p_context.add_argument("--depth", type=int, default=1)
    p_context.add_argument("--max-tokens", type=int, default=2000)
    p_context.set_defaults(func=cmd_context)

    # read-slice
    p_read = subparsers.add_parser("read-slice", help="Read a bounded file slice")
    p_read.add_argument("--file", required=True, help="File path (repo-relative)")
    p_read.add_argument("--symbol", default=None, help="Symbol to read")
    p_read.add_argument("--line-start", type=int, default=None)
    p_read.add_argument("--line-end", type=int, default=None)
    p_read.add_argument("--max-lines", type=int, default=120)
    p_read.set_defaults(func=cmd_read_slice)

    # fireworks-patch
    p_fw = subparsers.add_parser("fireworks-patch", help="Call Fireworks for a candidate diff")
    p_fw.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_fw.add_argument("--instruction", required=True, help="Instruction for the model")
    p_fw.add_argument("--model-tier", default="fast", choices=["fast", "code", "judge"])
    p_fw.add_argument("--max-output-tokens", type=int, default=2048)
    p_fw.set_defaults(func=cmd_fireworks_patch)

    # stage-patch
    p_stage = subparsers.add_parser("stage-patch", help="Stage a patch through the arena")
    p_stage.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_stage.add_argument("--diff-file", default=None, help="File containing the unified diff")
    p_stage.add_argument("--diff", default=None, help="Inline diff content")
    p_stage.add_argument("--affected-files", default=None, help="Comma-separated affected files")
    p_stage.add_argument("--affected-symbols", default=None, help="Comma-separated affected symbols")
    p_stage.add_argument("--tests", default=None, help="Comma-separated test files")
    p_stage.add_argument("--owner", default="external_agent")
    p_stage.set_defaults(func=cmd_stage_patch)

    # verify
    p_verify = subparsers.add_parser("verify", help="Run verifier/tests")
    p_verify.add_argument("--scope", default="focused", choices=["focused", "all", "declared"])
    p_verify.add_argument("--runner", default="pytest")
    p_verify.add_argument("--max-log-lines", type=int, default=80)
    p_verify.set_defaults(func=cmd_verify)

    # repair-packet
    p_repair = subparsers.add_parser("repair-packet", help="Get repair context for a failed patch")
    p_repair.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_repair.add_argument("--failure-id", default=None, help="Specific failure stage ID")
    p_repair.add_argument("--max-tokens", type=int, default=1500)
    p_repair.set_defaults(func=cmd_repair_packet)

    # status
    p_status = subparsers.add_parser("status", help="Check hotswap/promotion status")
    p_status.set_defaults(func=cmd_status)

    # export-icm
    p_export = subparsers.add_parser("export-icm", help="Export arena to ICM workspace")
    p_export.add_argument("--workspace-root", default=None)
    p_export.set_defaults(func=cmd_export_icm)

    # find-affordances
    p_aff = subparsers.add_parser("find-affordances", help="Find internal Aura tools for an objective")
    p_aff.add_argument("--objective", required=True, help="Task objective or question")
    p_aff.add_argument("--target-files", default=None, help="Comma-separated target file paths")
    p_aff.add_argument("--target-symbols", default=None, help="Comma-separated target symbol names")
    p_aff.add_argument("--no-affordances", action="store_true", help="Skip affordance cards")
    p_aff.add_argument("--top-k", type=int, default=7, help="Max affordances to return (3-7)")
    p_aff.set_defaults(func=cmd_find_affordances)

    # ---- Hermes Arena Mode subcommands (additive) ----

    # hermes-contract
    p_contract = subparsers.add_parser(
        "hermes-contract",
        help="Generate a ready-to-paste Hermes operating contract / system prompt",
    )
    p_contract.add_argument("--objective", required=True, help="Coding objective")
    p_contract.add_argument("--mode", default="pr", choices=["pr", "direct"], help="Operating mode (default: pr)")
    p_contract.add_argument("--json", action="store_true", help="Output full JSON instead of markdown contract text")
    p_contract.set_defaults(func=cmd_hermes_contract)

    # preflight
    p_preflight = subparsers.add_parser(
        "preflight",
        help="Generate a compact JSON preflight packet for a coding objective",
    )
    p_preflight.add_argument("--objective", required=True, help="Coding objective")
    p_preflight.add_argument("--target-files", default=None, help="Comma-separated target file paths")
    p_preflight.add_argument("--target-symbols", default=None, help="Comma-separated target symbol names")
    p_preflight.set_defaults(func=cmd_preflight)

    # token-report
    p_token = subparsers.add_parser(
        "token-report",
        help="Generate a token savings report comparing raw vs Aura context usage",
    )
    p_token.add_argument("--objective", required=True, help="Coding objective")
    p_token.add_argument("--files", required=True, help="Comma-separated repo-relative file paths")
    p_token.add_argument("--include-preflight", action="store_true", help="Include full preflight packet in report")
    p_token.add_argument("--format", default="json", choices=["json", "markdown"], help="Output format (default: json)")
    p_token.set_defaults(func=cmd_token_report)

    # pr-runbook
    p_runbook = subparsers.add_parser(
        "pr-runbook",
        help="Generate a PR-safe Git/Hermes workflow runbook for a task",
    )
    p_runbook.add_argument("--objective", required=True, help="Coding objective")
    p_runbook.add_argument("--branch", required=True, help="Feature branch name (e.g. feature/my-task)")
    p_runbook.add_argument("--files", default=None, help="Comma-separated files that will be modified")
    p_runbook.add_argument("--json", action="store_true", help="Output full JSON instead of markdown runbook text")
    p_runbook.set_defaults(func=cmd_pr_runbook)

    # write-rules
    p_rules = subparsers.add_parser(
        "write-rules",
        help="Write .aura/HERMES_AURA_RULES.md guard file",
    )
    p_rules.set_defaults(func=cmd_write_rules)

    # ---- Native Cockpit subcommands (additive) ----

    # ingest-intent
    p_ingest = subparsers.add_parser(
        "ingest-intent",
        help="Ingest an Aura-native intent document and compile an IntentPacket",
    )
    p_ingest.add_argument("--file", required=True, help="Path to .aura.md intent document")
    p_ingest.set_defaults(func=cmd_ingest_intent)

    # validate-lexc-route
    p_vlexc = subparsers.add_parser(
        "validate-lexc-route",
        help="Validate the LEXC route from an intent document",
    )
    p_vlexc.add_argument("--file", required=True, help="Path to .aura.md intent document")
    p_vlexc.set_defaults(func=cmd_validate_lexc_route)

    # capability-connectome
    p_conn = subparsers.add_parser(
        "capability-connectome",
        help="Build the full capability connectome graph",
    )
    p_conn.set_defaults(func=cmd_capability_connectome)

    # capability-path
    p_cpath = subparsers.add_parser(
        "capability-path",
        help="Find the capability path for an objective",
    )
    p_cpath.add_argument("--objective", required=True, help="Coding objective")
    p_cpath.set_defaults(func=cmd_capability_path)

    # token-economy
    p_tecon = subparsers.add_parser(
        "token-economy",
        help="Compute a token economy report with savings sources",
    )
    p_tecon.add_argument("--objective", required=True, help="Coding objective")
    p_tecon.add_argument("--files", required=True, help="Comma-separated file paths")
    p_tecon.set_defaults(func=cmd_token_economy_cli)

    # workflow-gates
    p_wgates = subparsers.add_parser(
        "workflow-gates",
        help="Show the workflow state machine (18 checkpoint states)",
    )
    p_wgates.set_defaults(func=cmd_workflow_gates)

    # native-cockpit-contract
    p_ncc = subparsers.add_parser(
        "native-cockpit-contract",
        help="Generate a native cockpit contract for an objective",
    )
    p_ncc.add_argument("--objective", required=True, help="Coding objective")
    p_ncc.add_argument("--json", action="store_true", help="Output full JSON")
    p_ncc.set_defaults(func=cmd_native_cockpit_contract)

    # prepare-native-handoff
    p_pnh = subparsers.add_parser(
        "prepare-native-handoff",
        help="Prepare an agent handoff packet from an intent document",
    )
    p_pnh.add_argument("--intent-file", required=True, help="Path to .aura.md intent document")
    p_pnh.add_argument("--agent", default="hermes", help="Agent name (hermes, codex)")
    p_pnh.set_defaults(func=cmd_prepare_native_handoff)

    # ---- Capability Orchestration subcommands (additive) ----

    # capability-lanes
    p_clanes = subparsers.add_parser("capability-lanes", help="List all cockpit capability lanes")
    p_clanes.set_defaults(func=cmd_capability_lanes)

    # route-lanes
    p_route = subparsers.add_parser("route-lanes", help="Route an objective to capability lanes")
    p_route.add_argument("--objective", required=True, help="Coding objective")
    p_route.set_defaults(func=cmd_route_lanes)

    # music-rank
    p_music = subparsers.add_parser("music-rank", help="Run MUSIC advisory ranking on candidates")
    p_music.add_argument("--objective", required=True, help="Coding objective")
    p_music.add_argument("--candidates", default=None, help="Comma-separated list of candidate files or symbols to rank")
    p_music.set_defaults(func=cmd_music_rank)

    # mitosis-split
    p_mitosis = subparsers.add_parser("mitosis-split", help="Split objective into child capsules")
    p_mitosis.add_argument("--objective", required=True, help="Coding objective")
    p_mitosis.set_defaults(func=cmd_mitosis_split)

    # research-evidence
    p_research = subparsers.add_parser("research-evidence", help="Search research manifest for evidence")
    p_research.add_argument("--objective", required=True, help="Coding objective")
    p_research.add_argument("--offline", action="store_true", default=False, help="Offline mode")
    p_research.set_defaults(func=cmd_research_evidence)

    # skillweave
    p_skill = subparsers.add_parser("skillweave", help="Discover skills for an objective")
    p_skill.add_argument("--objective", required=True, help="Coding objective")
    p_skill.set_defaults(func=cmd_skillweave)

    # goap-plan
    p_goap = subparsers.add_parser("goap-plan", help="Plan objective with GOAP planner")
    p_goap.add_argument("--objective", required=True, help="Coding objective")
    p_goap.set_defaults(func=cmd_goap_plan)

    # swarm-plan
    p_swarm = subparsers.add_parser("swarm-plan", help="Build multi-agent swarm plan")
    p_swarm.add_argument("--objective", required=True, help="Coding objective")
    p_swarm.add_argument("--agents", default="hermes", help="Comma-separated agent names")
    p_swarm.set_defaults(func=cmd_swarm_plan)

    # phase-capsules
    p_phase = subparsers.add_parser("phase-capsules", help="Create phase capsules for an objective")
    p_phase.add_argument("--objective", required=True, help="Coding objective")
    p_phase.set_defaults(func=cmd_phase_capsules)

    # live-stage-plan
    p_stage = subparsers.add_parser("live-stage-plan", help="Create live architect stage plan")
    p_stage.add_argument("--objective", required=True, help="Coding objective")
    p_stage.set_defaults(func=cmd_live_stage_plan)

    # cockpit-audit
    p_audit = subparsers.add_parser("cockpit-audit", help="Export cockpit audit packet")
    p_audit.add_argument("--objective", default="", help="Optional objective filter")
    p_audit.set_defaults(func=cmd_cockpit_audit)

    # ---- Coding Workbench subcommands (additive) ----

    # topology-health
    p_th = subparsers.add_parser("topology-health", help="Check CODEMAP topology health")
    p_th.set_defaults(func=cmd_topology_health)

    # open-workspace
    p_ow = subparsers.add_parser("open-workspace", help="Open a coding workspace")
    p_ow.add_argument("--objective", default="", help="Initial objective")
    p_ow.set_defaults(func=cmd_open_workspace)

    # scope-task
    p_st = subparsers.add_parser("scope-task", help="Scope a coding task")
    p_st.add_argument("--objective", required=True, help="Coding objective")
    p_st.set_defaults(func=cmd_scope_task)

    # filter-context
    p_fc = subparsers.add_parser("filter-context", help="Filter context for an objective")
    p_fc.add_argument("--objective", required=True, help="Coding objective")
    p_fc.set_defaults(func=cmd_filter_context)

    # localize-code
    p_lc = subparsers.add_parser("localize-code", help="Localize code through CODEMAP")
    p_lc.add_argument("--objective", required=True, help="Coding objective")
    p_lc.set_defaults(func=cmd_localize_code)

    # rank-code-regions
    p_rcr = subparsers.add_parser("rank-code-regions", help="Rank code regions under token/line budget")
    p_rcr.add_argument("--objective", required=True, help="Coding objective")
    p_rcr.add_argument("--max-lines", type=int, default=400, help="Max lines budget")
    p_rcr.set_defaults(func=cmd_rank_code_regions_cli)

    # slice-context
    p_sc = subparsers.add_parser("slice-context", help="Slice context from ranking")
    p_sc.add_argument("--ranking-file", default=None, help="Path to ranking JSON file")
    p_sc.set_defaults(func=cmd_slice_context_cli)

    # change-graph
    p_cg = subparsers.add_parser("change-graph", help="Build a change graph")
    p_cg.add_argument("--objective", required=True, help="Coding objective")
    p_cg.set_defaults(func=cmd_change_graph_cli)

    # refactor-candidates
    p_rfc = subparsers.add_parser("refactor-candidates", help="Detect refactor candidates")
    p_rfc.add_argument("--objective", required=True, help="Coding objective")
    p_rfc.set_defaults(func=cmd_refactor_candidates_cli)

    # split-work (already exists from capability orchestration, override with workbench version)
    # Use a different name to avoid conflict
    p_sw = subparsers.add_parser("split-work", help="Split work into child tasks")
    p_sw.add_argument("--objective", required=True, help="Coding objective")
    p_sw.set_defaults(func=cmd_split_work_cli)

    # command-risk
    p_cr = subparsers.add_parser("command-risk", help="Classify command risk")
    p_cr.add_argument("--command", required=True, help="Command to classify")
    p_cr.set_defaults(func=cmd_command_risk_cli)

    # agent-workbench-contract
    p_awc = subparsers.add_parser("agent-workbench-contract", help="Generate agent workbench contract")
    p_awc.add_argument("--agent", default="hermes", help="Agent name")
    p_awc.set_defaults(func=cmd_agent_workbench_contract)

    # prepare-agent-work
    p_paw = subparsers.add_parser("prepare-agent-work", help="Prepare agent handoff for a candidate")
    p_paw.add_argument("--candidate-id", required=True, help="Candidate ID")
    p_paw.add_argument("--agent", default="hermes", help="Agent name")
    p_paw.set_defaults(func=cmd_prepare_agent_work)

    # ---- Cost Observatory subcommands (additive) ----

    # cost-status
    p_cs = subparsers.add_parser("cost-status", help="Show cost observatory status")
    p_cs.set_defaults(func=cmd_cost_status)

    # cost-run
    p_cr = subparsers.add_parser("cost-run", help="Run a cost experiment")
    p_cr.add_argument("--objective", required=True, help="Coding objective")
    p_cr.add_argument("--mode", default="aura", choices=["aura", "raw"], help="Experiment mode")
    p_cr.set_defaults(func=cmd_cost_run)

    # cost-baseline
    p_cb = subparsers.add_parser("cost-baseline", help="Run a shadow baseline")
    p_cb.add_argument("--objective", required=True, help="Coding objective")
    p_cb.add_argument("--mode", default="shadow", choices=["shadow"], help="Baseline mode")
    p_cb.set_defaults(func=cmd_cost_baseline)

    # cost-compare
    p_cc = subparsers.add_parser("cost-compare", help="Compare runs by comparison ID")
    p_cc.add_argument("--comparison-id", required=True, help="Comparison ID")
    p_cc.set_defaults(func=cmd_cost_compare)

    # cost-report
    p_crep = subparsers.add_parser("cost-report", help="Generate cost report")
    p_crep.add_argument("--comparison-id", required=True, help="Comparison ID")
    p_crep.add_argument("--format", default="json", choices=["json", "markdown"])
    p_crep.set_defaults(func=cmd_cost_report)

    # cost-attribution
    p_ca = subparsers.add_parser("cost-attribution", help="Show cost attribution for a run")
    p_ca.add_argument("--run-id", required=True, help="Run ID")
    p_ca.set_defaults(func=cmd_cost_attribution)

    # cost-history
    p_ch = subparsers.add_parser("cost-history", help="Show cost run history")
    p_ch.add_argument("--limit", type=int, default=20)
    p_ch.set_defaults(func=cmd_cost_history)

    # ---- Capability Resolver + Stabilization subcommands (additive) ----

    # resolve-capabilities
    p_rc = subparsers.add_parser("resolve-capabilities", help="Resolve grounded capabilities for an objective")
    p_rc.add_argument("--objective", required=True, help="Coding objective")
    p_rc.add_argument("--target-files", default=None, help="Comma-separated target files")
    p_rc.add_argument("--target-symbols", default=None, help="Comma-separated target symbols")
    p_rc.set_defaults(func=cmd_resolve_capabilities)

    # stabilization-status
    p_ss = subparsers.add_parser("stabilization-status", help="Show system stabilization report")
    p_ss.set_defaults(func=cmd_stabilization_status)

    # ---- Ephemeral Organ Runtime subcommands (additive) ----

    # ephemeral-plan
    p_ep = subparsers.add_parser("ephemeral-plan", help="Plan an ephemeral organ for an objective")
    p_ep.add_argument("--objective", required=True, help="Objective for the ephemeral organ")
    p_ep.add_argument("--ttl", type=int, default=300, help="TTL in seconds")
    p_ep.set_defaults(func=cmd_ephemeral_plan)

    # ephemeral-validate
    p_ev = subparsers.add_parser("ephemeral-validate", help="Validate an ephemeral organ through the product automaton")
    p_ev.add_argument("--organ-id", required=True, help="Organ ID")
    p_ev.add_argument("--human-approval", action="store_true", help="Indicate human approval is present")
    p_ev.set_defaults(func=cmd_ephemeral_validate)

    # ephemeral-run
    p_er = subparsers.add_parser("ephemeral-run", help="Run an ephemeral organ (read-only MVP)")
    p_er.add_argument("--organ-id", required=True, help="Organ ID")
    p_er.set_defaults(func=cmd_ephemeral_run)

    # ephemeral-status
    p_es = subparsers.add_parser("ephemeral-status", help="Get ephemeral organ status")
    p_es.add_argument("--organ-id", required=True, help="Organ ID")
    p_es.set_defaults(func=cmd_ephemeral_status)

    # ephemeral-dissolve
    p_ed = subparsers.add_parser("ephemeral-dissolve", help="Dissolve an ephemeral organ")
    p_ed.add_argument("--organ-id", required=True, help="Organ ID")
    p_ed.set_defaults(func=cmd_ephemeral_dissolve)

    # ephemeral-receipt
    p_ert = subparsers.add_parser("ephemeral-receipt", help="Get dissolution receipt for an ephemeral organ")
    p_ert.add_argument("--organ-id", required=True, help="Organ ID")
    p_ert.set_defaults(func=cmd_ephemeral_receipt)

    # ---- Civic Commons Arena subcommands (additive) ----

    # civic-demo
    p_cd = subparsers.add_parser("civic-demo", help="Run full Civic Commons demo")
    p_cd.add_argument("--fixture", action="store_true", default=True)
    p_cd.add_argument("--story", default="hairstylist", choices=["hairstylist","youth_centre","council_pulse"])
    p_cd.set_defaults(func=cmd_civic_demo)

    # civic-create
    p_cc = subparsers.add_parser("civic-create", help="Create a Civic Commons session")
    p_cc.add_argument("--objective", required=True)
    p_cc.set_defaults(func=cmd_civic_create)

    # civic-status
    p_cst = subparsers.add_parser("civic-status", help="Get Civic session status")
    p_cst.add_argument("--session-id", required=True)
    p_cst.set_defaults(func=cmd_civic_status)

    # civic-profiles
    p_cp = subparsers.add_parser("civic-profiles", help="Show active profiles")
    p_cp.add_argument("--session-id", required=True)
    p_cp.set_defaults(func=cmd_civic_profiles)

    # civic-add-contribution
    p_cac = subparsers.add_parser("civic-add-contribution", help="Add a contribution")
    p_cac.add_argument("--session-id", required=True)
    p_cac.add_argument("--file", default="")
    p_cac.set_defaults(func=cmd_civic_add_contribution)

    # civic-match-resources
    p_cmr = subparsers.add_parser("civic-match-resources", help="Match resources")
    p_cmr.add_argument("--session-id", required=True)
    p_cmr.set_defaults(func=cmd_civic_match_resources)

    # civic-mitosis
    p_cm = subparsers.add_parser("civic-mitosis", help="Run MITOSIS decomposition")
    p_cm.add_argument("--session-id", required=True)
    p_cm.set_defaults(func=cmd_civic_mitosis)

    # civic-scenarios
    p_csc = subparsers.add_parser("civic-scenarios", help="Run MUSIC scenario comparison")
    p_csc.add_argument("--session-id", required=True)
    p_csc.set_defaults(func=cmd_civic_scenarios)

    # civic-respond
    p_cr = subparsers.add_parser("civic-respond", help="Collect responses")
    p_cr.add_argument("--session-id", required=True)
    p_cr.add_argument("--file", default="")
    p_cr.set_defaults(func=cmd_civic_respond)

    # civic-consent
    p_cco = subparsers.add_parser("civic-consent", help="Get Consent Arc")
    p_cco.add_argument("--session-id", required=True)
    p_cco.set_defaults(func=cmd_civic_consent)

    # civic-what-if
    p_cwi = subparsers.add_parser("civic-what-if", help="Run What-If simulation")
    p_cwi.add_argument("--session-id", required=True)
    p_cwi.add_argument("--file", default="")
    p_cwi.set_defaults(func=cmd_civic_what_if)

    # civic-pilot
    p_cpi = subparsers.add_parser("civic-pilot", help="Create pilot packet")
    p_cpi.add_argument("--session-id", required=True)
    p_cpi.add_argument("--scenario-id", default="")
    p_cpi.set_defaults(func=cmd_civic_pilot)

    # civic-issue-pulse
    p_cip = subparsers.add_parser("civic-issue-pulse", help="Show council issue pulse")
    p_cip.add_argument("--session-id", required=True)
    p_cip.set_defaults(func=cmd_civic_issue_pulse)

    # civic-export
    p_ce = subparsers.add_parser("civic-export", help="Export decision packet")
    p_ce.add_argument("--session-id", required=True)
    p_ce.set_defaults(func=cmd_civic_export)

    # civic-close
    p_ccl = subparsers.add_parser("civic-close", help="Close Civic session")
    p_ccl.add_argument("--session-id", required=True)
    p_ccl.set_defaults(func=cmd_civic_close)

    # ---- Tensor Evidence commands ----
    p_tac = subparsers.add_parser("tensor-analyze-coding", help="Analyze coding region with tensor BP")
    p_tac.add_argument("--node-ids", default="")
    p_tac.add_argument("--grounded", action="store_true")
    p_tac.add_argument("--tests", action="store_true")
    p_tac.add_argument("--deps", type=int, default=0)
    p_tac.add_argument("--public-api", action="store_true")
    p_tac.add_argument("--external", default="")
    p_tac.set_defaults(func=cmd_tensor_analyze_coding)

    p_tav = subparsers.add_parser("tensor-analyze-civic", help="Analyze civic session with tensor BP")
    p_tav.add_argument("--session-id", required=True)
    p_tav.set_defaults(func=cmd_tensor_analyze_civic)

    p_tcp = subparsers.add_parser("tensor-compress", help="Demo tensor compression")
    p_tcp.add_argument("--max-rank", type=int, default=None)
    p_tcp.add_argument("--tolerance", type=float, default=1e-3)
    p_tcp.set_defaults(func=cmd_tensor_compress)

    p_tct = subparsers.add_parser("tensor-contradictions", help="Show contradictions")
    p_tct.add_argument("--session-id", default="")
    p_tct.set_defaults(func=cmd_tensor_show_contradictions)

    p_tcf = subparsers.add_parser("tensor-confinement", help="Show confinement analysis")
    p_tcf.add_argument("--session-id", default="")
    p_tcf.set_defaults(func=cmd_tensor_show_confinement)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
