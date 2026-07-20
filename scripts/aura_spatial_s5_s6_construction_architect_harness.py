#!/usr/bin/env python3
# ruff: noqa: E402
"""Aura-native architecture and proof harness for Spatial S5 + S6 Construction.

The harness exercises Connectome/affordance discovery, Emergent Properties,
Council/Surgeon planning, Coding Waboose, Crucible, the governed Spatial Arena
lifecycle, and the privacy-minimized Construction spatial projection. It never
mutates production source or grants domain/renderer/patch authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Any
import uuid

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_agent_arena_review_learning_bridge import ReviewLearningAgentArenaBridge
from aura_architect_control import normalize_control_profile
from aura_architect_council_v3 import ARCHITECT_COUNCIL_V3
from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_coding_waboose_review_lessons import PATCH_AUTHORITY
from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
)
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_spatial_agent_bridge import AuraSpatialAgentBridge
from aura_spatial_arena import SpatialArena

HARNESS_VERSION = "AURA_SPATIAL_S5_S6_CONSTRUCTION_ARCHITECT_HARNESS_V1"
_MAX_RECEIPT_BYTES = 1_048_576
_TARGET_FILES = [
    ".aura/arena_routes/spatial.v1.json",
    "aura_spatial_arena.py",
    "aura_spatial_construction.py",
    "aura_spatial_agent_bridge.py",
    "aura_spatial_mcp.py",
    "aura_spatial_cli.py",
    "aura_arena_persistence_adapters.py",
    "aura_agent_arena_persistence_bridge.py",
    "aura_agent_arena_mcp.py",
    "tests/test_aura_spatial_s5_arena.py",
    "tests/test_aura_spatial_s6_construction.py",
    "tests/test_aura_spatial_agent_bridge_mcp.py",
    "tests/test_aura_spatial_cli.py",
    "tests/test_aura_spatial_s5_s6_harness.py",
    "scripts/aura_spatial_s5_s6_construction_architect_harness.py",
]
_FORBIDDEN_CONSTRUCTION_FIELDS = {
    "actor_id",
    "claimant_id",
    "consent_refs",
    "payload_digest",
    "observed_at",
    "expires_at",
    "source_coordinates",
    "exact_coordinates",
}


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
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _summary(packet: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {"ok": False, "status": "invalid_packet"}
    return {key: packet.get(key) for key in keys if key in packet}


def _safe_architecture_call(label: str, callback: Any) -> dict[str, Any]:
    timeout_seconds = int(os.environ.get("AURA_S5_S6_ARCHITECT_TIMEOUT_SECONDS", "120"))
    if timeout_seconds < 1 or timeout_seconds > 1800:
        timeout_seconds = 120

    def _timeout_handler(_signum: int, _frame: Any) -> None:
        raise TimeoutError(f"{label} exceeded {timeout_seconds} seconds")

    prior_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        result = callback()
    except Exception as exc:  # fail closed with bounded diagnostic evidence
        return {
            "ok": False,
            "status": "FAILED_CLOSED",
            "component": label,
            "error_type": type(exc).__name__,
            "error": str(exc)[:1024],
            "patch_authority": PATCH_AUTHORITY,
            "automatic_merge": False,
        }
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior_handler)
    return (
        result
        if isinstance(result, dict)
        else {
            "ok": False,
            "status": "INVALID_PACKET",
            "component": label,
            "patch_authority": PATCH_AUTHORITY,
            "automatic_merge": False,
        }
    )


def _call_preserving_generated_maps(repo_root: Path, callback: Any) -> tuple[Any, bool]:
    paths = (
        repo_root / ".aura" / "CODEMAP.json",
        repo_root / ".aura" / "CODEMAP.md",
    )
    snapshots = {path: (path.exists(), path.read_bytes() if path.exists() else b"") for path in paths}
    try:
        result = callback()
    finally:
        for path, (existed, content) in snapshots.items():
            if existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            elif path.exists():
                path.unlink()
    restored = all(
        path.exists() == existed and (not existed or path.read_bytes() == content)
        for path, (existed, content) in snapshots.items()
    )
    return result, restored


def _temporary_arena_root(repo_root: Path) -> tempfile.TemporaryDirectory[str]:
    staging = repo_root / "Aura_Staging"
    staging.mkdir(parents=True, exist_ok=True)
    holder = tempfile.TemporaryDirectory(prefix="spatial-s5-s6-harness-", dir=staging)
    root = Path(holder.name)
    route_dir = root / ".aura" / "arena_routes"
    route_dir.mkdir(parents=True)
    shutil.copy2(repo_root / ".aura/arena_routes/spatial.v1.json", route_dir / "spatial.v1.json")
    return holder


def _prove_lifecycle(repo_root: Path, observed_head: str) -> dict[str, Any]:
    fixture = build_sco_construction_demo_fixture()
    construction_packet = ConstructionArenaAdapter().build_runtime_packet(
        objective="review synthetic Construction alternatives spatially",
        state=fixture.state,
        scope=fixture.focus_scope,
        candidates=fixture.candidates,
        now=10.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=fixture.probabilistic_signals,
    )
    with _temporary_arena_root(repo_root) as root_name:
        arena_root = Path(root_name)
        arena = SpatialArena(arena_root, now=lambda: 100.0)
        bridge = AuraSpatialAgentBridge(arena_root, arena=arena)
        prepared = bridge.prepare_construction_projection(
            objective="review synthetic Construction alternatives spatially",
            state=fixture.state,
            construction_runtime_packet=construction_packet,
        )
        run_id = prepared["run_id"]
        candidate_entity = next(item for item in prepared["scene"]["entities"] if item["entity_type"] == "DOMAIN_NODE")
        interaction = bridge.interact(
            run_id,
            action="SELECT",
            target_entity_ids=(candidate_entity["entity_id"],),
        )
        proof = bridge.prove(
            run_id,
            repo_head=observed_head if observed_head != "UNAVAILABLE" else "0" * 40,
            metrics={"source": "architect_harness", "renderer_allocated": False, "frame_ms": 0.0},
        )
        observatory = bridge.observatory(run_id)
        restore = bridge.restore_assessment(
            run_id,
            current_repo_head=observed_head if observed_head != "UNAVAILABLE" else "0" * 40,
        )
        decision = bridge.decide(run_id, decision="await authorized human Construction review")
        status = bridge.status(run_id)
        dissolution = bridge.dissolve(
            run_id,
            renderer_cleanup_receipt={
                "state": "NOT_ALLOCATED",
                "renderer_allocated": False,
                "evidence_class": "CLIENT_REPORTED",
                "session_id": status["session_id"],
                "scene_digest": status["scene_digest"],
                "render_plan_digest": status["render_plan_digest"],
                "renderer_authority": False,
                "execution_authority": False,
            },
            reason_code="HARNESS_COMPLETE",
        )
        encoded_scene = json.dumps(prepared["scene"], sort_keys=True)
        forbidden = sorted(field for field in _FORBIDDEN_CONSTRUCTION_FIELDS if f'"{field}"' in encoded_scene)
        route = load_and_compile_arena_grammar(arena_root / ".aura/arena_routes/spatial.v1.json")
        return {
            "route_ok": route.ok,
            "route_manifest_digest": route.manifest_digest,
            "run_id": run_id,
            "construction_state_digest": fixture.state.state_digest,
            "scene_digest": prepared["scene"]["scene_digest"],
            "render_plan_digest": prepared["render_plan"]["render_plan_digest"],
            "interaction_id": interaction["intent"]["interaction_id"],
            "interaction_review_only": interaction["intent"]["review_only"],
            "proof_receipt_id": proof["render_receipt"]["receipt_id"],
            "checkpoint_id": proof["checkpoint"]["checkpoint"]["checkpoint_id"],
            "attempt_archive_ok": proof["attempt_archive"]["ok"],
            "observatory_read_only": observatory["read_only"],
            "cost_receipt_digest": observatory["cost_receipt"]["cost_receipt_digest"],
            "restore_status": restore["assessment"]["status"],
            "automatic_resume": restore["automatic_resume"],
            "decision_digest": decision["decision_packet"]["decision_digest"],
            "decision_applied": decision["decision_packet"]["decision_applied"],
            "dissolution_digest": dissolution["dissolution_receipt"]["dissolution_digest"],
            "renderer_allocated": dissolution["renderer_allocated"],
            "renderer_resources_released": dissolution["renderer_resources_released"],
            "renderer_resources_released_verified": dissolution["renderer_resources_released_verified"],
            "renderer_resource_boundary_satisfied": dissolution["renderer_resource_boundary_satisfied"],
            "lease_released": dissolution["lease_released"],
            "active_sessions_after_dissolution": arena.session_manager.active_session_count,
            "forbidden_construction_fields": forbidden,
            "event_payloads_included": False,
            "person_level_data_included": False,
            "source_coordinates_included": False,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_controlled": False,
            "production_mutation": False,
            "automatic_merge": False,
        }


def _architecture_inner(
    repo_root: Path, *, base_ref: str, head_ref: str, observed_head: str, structural_only: bool
) -> dict[str, Any]:
    if structural_only:
        return {
            "mode": "structural_only",
            "agent_bridge": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "connectome": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "emergent": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "waboose": {"ok": True, "status": "not_invoked_in_structural_mode"},
            "crucible": {"status": "not_invoked_in_structural_mode"},
        }

    objective = (
        "Implement governed Spatial S5 lifecycle and Construction-only S6 projection "
        "without duplicating domain ownership or introducing authority"
    )
    bridge = ReviewLearningAgentArenaBridge(
        repo_root=str(repo_root),
        review_learning_root=repo_root / "Aura_Staging" / "spatial_s5_s6_construction_harness",
    )
    repo_digest = _safe_architecture_call(
        "repo_digest", lambda: bridge.aura_repo_digest(include_hubs=False, max_lines=20)
    )
    affordances = _safe_architecture_call(
        "affordances",
        lambda: bridge.aura_find_affordances(
            objective=objective,
            target_files=_TARGET_FILES,
            target_symbols=[
                "SpatialArena",
                "project_construction_state_to_scene",
                "checkpoint_spatial",
                "AuraSpatialAgentBridge",
            ],
            include_affordances=True,
            top_k=4,
        ),
    )
    atomic = _safe_architecture_call(
        "atomic_inventory",
        lambda: bridge.aura_atomic_function_inventory(
            query="spatial arena lifecycle lease privacy egress construction projection checkpoint observatory dissolution",
            target_files=_TARGET_FILES,
            target_symbols=[
                "SpatialArena",
                "project_construction_state_to_scene",
                "checkpoint_spatial",
            ],
            limit=48,
            include_source=False,
        ),
    )
    emergent = _safe_architecture_call(
        "emergent",
        lambda: bridge.aura_emergent_evidence(
            {
                "objective": objective,
                "target_files": _TARGET_FILES,
                "target_symbols": [
                    "SpatialArena",
                    "project_construction_state_to_scene",
                    "AuraSpatialAgentBridge",
                ],
                "target_arena": "coding_arena",
                "radius": 1,
                "max_atomic_nodes": 48,
                "max_source_lines": 20,
                "include_source": False,
                "include_future": False,
                "include_research_plan": False,
                "include_offline_research": False,
            }
        ),
    )
    prepared, maps_restored = _call_preserving_generated_maps(
        repo_root,
        lambda: _safe_architecture_call(
            "agent_bridge_prepare",
            lambda: bridge.aura_prepare_arena(
                objective=objective,
                target_file="aura_spatial_arena.py",
                target_symbol="SpatialArena",
                acceptance_criteria=[
                    "S5 lifecycle and Construction-only S6 projection remain bounded, assessment-only, externally owned, privacy-minimized, and cleanup-bound",
                ],
                risk_map=[
                    "duplicate Construction state, privacy leakage, unobserved cleanup, automatic resume, or authority escalation",
                ],
                constraints={
                    "production_mutation": False,
                    "automatic_merge": False,
                    "coderabbit_autofix": False,
                    "human_review_required": True,
                },
                use_emergent_evidence=False,
            ),
        ),
    )
    waboose_prepared = _safe_architecture_call(
        "waboose_prepare",
        lambda: bridge.aura_waboose_prepare(
            {
                "objective": objective,
                "mode": "files",
                "base_ref": base_ref,
                "head_ref": head_ref,
                "changed_files": _TARGET_FILES,
                "profile": "precision",
                "focus_directives": [
                    "authority boundary",
                    "privacy minimization",
                    "exact-head lifecycle cleanup",
                    "restore assessment only",
                ],
                "invariants": [
                    "no domain mutation",
                    "no renderer authority",
                    "no automatic resume",
                    "no person-level Construction projection",
                    "dissolution releases resources and leases",
                ],
                "risk_map": [
                    "stale state/scene/plan digest",
                    "unadmitted egress",
                    "private geometry leakage",
                    "duplicate canonical owner",
                ],
                "agent_name": "none",
                "graph_depth": 0,
                "graph_node_budget": 40,
                "run_tests": False,
                "run_optional_tools": False,
                "metadata": {
                    "harness_version": HARNESS_VERSION,
                    "observed_head": observed_head,
                    "council_version": ARCHITECT_COUNCIL_V3,
                    "surgeon_mode": "PROPOSE",
                },
            }
        ),
    )
    if waboose_prepared.get("ok"):
        waboose_scan = _safe_architecture_call(
            "waboose_scan", lambda: bridge.aura_waboose_scan(waboose_prepared["review_id"])
        )
        waboose_final = (
            _safe_architecture_call(
                "waboose_finalize", lambda: bridge.aura_waboose_finalize(waboose_prepared["review_id"])
            )
            if waboose_scan.get("ok")
            else {"ok": False, "status": "SCAN_FAILED", "patch_authority": PATCH_AUTHORITY}
        )
    else:
        waboose_scan = {"ok": False, "status": "prepare_failed"}
        waboose_final = {"ok": False, "status": "prepare_failed"}
    crucible = _safe_architecture_call("crucible", bridge.aura_waboose_crucible_replay)
    control = normalize_control_profile(
        {
            "surface": "coding_arena",
            "council_mode": "SELECTIVE_V3",
            "council_call_budget": 6,
            "critic_lanes": ["scope", "tests", "sequence", "continuity", "rollback", "cost"],
            "surgeon_mode": "PROPOSE",
            "surgeon_max_turns": 10,
            "surgeon_max_local_repairs": 2,
            "surgeon_context_tokens": 2400,
            "surgeon_output_tokens": 2400,
            "council_replan_allowed": True,
            "record_outputs": False,
            "output_root": "Aura_Staging/spatial_s5_s6_construction_harness",
            "human_review_required": True,
            "production_mutation": False,
            "vsa_patch_authority": False,
        },
        surface="coding_arena",
    ).to_dict()
    return {
        "mode": "full",
        "agent_bridge": {
            "repo_digest": _summary(repo_digest, ("ok", "version", "repo_head", "file_count", "symbol_count")),
            "prepare": _summary(
                prepared, ("ok", "version", "status", "plan_phase_hash", "production_mutation", "patch_authority")
            ),
            "generated_maps_restored": maps_restored,
        },
        "connectome": {
            "affordances": _summary(
                affordances, ("grounding", "route_frame", "recommended_affordances", "patch_authority")
            ),
            "atomic_inventory": _summary(
                atomic, ("ok", "version", "inventory_digest", "total_count", "selected_count", "patch_authority")
            ),
        },
        "emergent": _summary(
            emergent,
            ("ok", "version", "packet_digest", "status", "grounding_ok", "selected_count", "patch_authority", "error"),
        ),
        "council_surgeon_control": control,
        "waboose": {
            "prepare": _summary(waboose_prepared, ("ok", "review_id", "status", "patch_authority")),
            "scan": _summary(
                waboose_scan,
                ("ok", "status", "review_lesson_findings_added", "finding_count", "patch_authority", "error"),
            ),
            "finalize": _summary(
                waboose_final,
                ("ok", "status", "summary", "finding_count", "repair_request_count", "patch_authority", "error"),
            ),
        },
        "crucible": _summary(
            crucible,
            (
                "ok",
                "status",
                "scenario_count",
                "passed_count",
                "failed_count",
                "packet_digest",
                "patch_authority",
                "error",
            ),
        ),
    }


def _marked_analysis_process_ids(run_token: str, proc_root: Path = Path("/proc")) -> tuple[int, ...]:
    """Return Linux process ids carrying this harness's unique child token."""

    if not run_token or not proc_root.is_dir():
        return ()
    marker = f"AURA_S5_S6_ARCHITECT_RUN_TOKEN={run_token}".encode()
    matches: list[int] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            environment = (entry / "environ").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        if marker in environment:
            matches.append(int(entry.name))
    return tuple(sorted(matches))


def _terminate_process_group(process: subprocess.Popen[Any], *, run_token: str = "") -> None:
    """Kill the isolated child session and any token-marked detached helpers."""

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    for pid in _marked_analysis_process_ids(run_token):
        if pid == os.getpid():
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _failed_architecture_packet(error_type: str, error: str) -> dict[str, Any]:
    return {
        "mode": "failed_closed",
        "error_type": error_type,
        "error": error[:1024],
        "agent_bridge": {"prepare": {"ok": False}, "generated_maps_restored": False},
        "connectome": {"atomic_inventory": {"ok": False}},
        "emergent": {"ok": False, "grounding_ok": False},
        "waboose": {
            "prepare": {"ok": False},
            "scan": {"ok": False},
            "finalize": {"ok": False},
        },
        "crucible": {"status": "FAILED_CLOSED", "failed_count": 1},
        "council_surgeon_control": {},
    }


def _architecture(
    repo_root: Path, *, base_ref: str, head_ref: str, observed_head: str, structural_only: bool
) -> dict[str, Any]:
    if structural_only:
        return _architecture_inner(
            repo_root,
            base_ref=base_ref,
            head_ref=head_ref,
            observed_head=observed_head,
            structural_only=True,
        )
    timeout_seconds = int(os.environ.get("AURA_S5_S6_ARCHITECT_TOTAL_TIMEOUT_SECONDS", "600"))
    if timeout_seconds < 1 or timeout_seconds > 3600:
        timeout_seconds = 600
    map_paths = (
        repo_root / ".aura" / "CODEMAP.json",
        repo_root / ".aura" / "CODEMAP.md",
    )
    snapshots = {path: (path.exists(), path.read_bytes() if path.exists() else b"") for path in map_paths}
    # Keep child scratch outside the repository. Waboose and the Connectome scan
    # repository evidence; placing an in-progress receipt under Aura_Staging can
    # make the proof observe its own changing output and stall recursively.
    scratch_dir = Path(tempfile.mkdtemp(prefix="aura-s5-s6-architecture-"))
    output_path = scratch_dir / "packet.json"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--repo-root",
        str(repo_root),
        "--base-ref",
        base_ref,
        "--head-ref",
        head_ref,
        "--observed-head",
        observed_head,
        "--architecture-only-output",
        str(output_path),
    ]
    stdout_path = output_path.with_suffix(".stdout.log")
    stderr_path = output_path.with_suffix(".stderr.log")
    run_token = uuid.uuid4().hex
    try:
        # Use ordinary files instead of PIPEs. Aura architecture calls may spawn
        # descendants that inherit standard streams; waiting on pipe EOF would
        # otherwise hang even after the bounded child has written its receipt.
        with (
            stdout_path.open("w", encoding="utf-8") as stdout_handle,
            stderr_path.open("w", encoding="utf-8") as stderr_handle,
        ):
            process = subprocess.Popen(
                command,
                cwd=repo_root,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                start_new_session=True,
                env={
                    **os.environ,
                    "AURA_S5_S6_ARCHITECT_CHILD": "1",
                    "AURA_S5_S6_ARCHITECT_RUN_TOKEN": run_token,
                },
            )
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _terminate_process_group(process, run_token=run_token)
                process.wait(timeout=10)
                packet = _failed_architecture_packet(
                    "TimeoutError",
                    f"full architecture harness exceeded {timeout_seconds} seconds",
                )
            else:
                if process.returncode == 0 and output_path.is_file() and output_path.stat().st_size:
                    packet = json.loads(output_path.read_text(encoding="utf-8"))
                else:
                    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
                    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
                    packet = _failed_architecture_packet(
                        "ArchitectureChildError",
                        (stderr or stdout or f"child exited {process.returncode}")[-1024:],
                    )
            finally:
                # Aura analysis calls may leave helper descendants alive after the
                # bounded child has written its receipt. Reap the entire isolated
                # session so inherited workflow streams cannot keep the job open.
                _terminate_process_group(process, run_token=run_token)
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
        for path, (existed, content) in snapshots.items():
            if existed:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            elif path.exists():
                path.unlink()
    return packet


def run(
    repo_root: Path, *, base_ref: str, head_ref: str, observed_head: str, structural_only: bool = False
) -> dict[str, Any]:
    actual_head = _git(repo_root, "rev-parse", "HEAD")
    observed = observed_head.strip() or actual_head
    before = _git(repo_root, "status", "--short")
    lifecycle = _prove_lifecycle(repo_root, observed)
    architecture = _architecture(
        repo_root,
        base_ref=base_ref,
        head_ref=head_ref,
        observed_head=observed,
        structural_only=structural_only,
    )
    after = _git(repo_root, "status", "--short")
    checks = {
        "route_compiles": lifecycle["route_ok"] is True,
        "exact_head_observed": actual_head == "UNAVAILABLE" or observed == actual_head,
        "construction_owner_external": lifecycle["construction_state_digest"] != "",
        "forbidden_construction_fields_absent": not lifecycle["forbidden_construction_fields"],
        "event_payloads_absent": lifecycle["event_payloads_included"] is False,
        "person_level_data_absent": lifecycle["person_level_data_included"] is False,
        "source_coordinates_absent": lifecycle["source_coordinates_included"] is False,
        "interaction_review_only": lifecycle["interaction_review_only"] is True,
        "checkpoint_assessment_only": lifecycle["automatic_resume"] is False,
        "observatory_read_only": lifecycle["observatory_read_only"] is True,
        "decision_not_applied": lifecycle["decision_applied"] is False,
        "renderer_resource_boundary_satisfied": lifecycle["renderer_resource_boundary_satisfied"] is True,
        "synthetic_renderer_not_allocated": lifecycle["renderer_allocated"] is False,
        "no_unverified_release_claim": lifecycle["renderer_resources_released"] is False
        and lifecycle["renderer_resources_released_verified"] is False,
        "lease_released": lifecycle["lease_released"] is True,
        "no_active_sessions": lifecycle["active_sessions_after_dissolution"] == 0,
        "no_physical_authority": lifecycle["physical_work_authorized"] is False,
        "no_payment_release": lifecycle["payment_released"] is False,
        "no_access_control": lifecycle["access_controlled"] is False,
        "no_production_mutation": lifecycle["production_mutation"] is False,
        "no_automatic_merge": lifecycle["automatic_merge"] is False,
        "tracked_state_unchanged": before == after,
    }
    if not structural_only:
        checks.update(
            {
                "agent_bridge_prepare_ok": architecture["agent_bridge"]["prepare"].get("ok") is True,
                "generated_maps_restored": architecture["agent_bridge"]["generated_maps_restored"] is True,
                "atomic_inventory_ok": architecture["connectome"]["atomic_inventory"].get("ok") is True,
                "emergent_grounded": architecture["emergent"].get("ok") is True
                and architecture["emergent"].get("grounding_ok") is True,
                "waboose_prepare_ok": architecture["waboose"]["prepare"].get("ok") is True,
                "waboose_scan_ok": architecture["waboose"]["scan"].get("ok") is True,
                "waboose_finalize_ok": architecture["waboose"]["finalize"].get("ok") is True,
                "waboose_no_visible_findings": int(
                    (architecture["waboose"]["finalize"].get("summary") or {}).get("visible_findings", 0)
                )
                == 0,
                "crucible_passed": architecture["crucible"].get("status") == "PASSED"
                and int(architecture["crucible"].get("failed_count", 0)) == 0,
                "council_surgeon_proposal_only": architecture["council_surgeon_control"].get("surgeon_mode")
                == "PROPOSE"
                and architecture["council_surgeon_control"].get("production_mutation") is False
                and architecture["council_surgeon_control"].get("human_review_required") is True,
            }
        )
    status = "PASSED" if all(checks.values()) else "FAILED"
    packet = {
        "ok": status == "PASSED",
        "status": status,
        "version": HARNESS_VERSION,
        "base_ref": base_ref,
        "head_ref": head_ref,
        "observed_head": observed,
        "actual_head": actual_head,
        "structural_only": structural_only,
        "target_files": _TARGET_FILES,
        "lifecycle": lifecycle,
        "architecture": architecture,
        "checks": checks,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "production_mutation": False,
        "automatic_merge": False,
        "human_review_required": True,
    }
    packet["receipt_digest"] = _digest(packet)
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(_REPO_ROOT))
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--observed-head", default="")
    parser.add_argument("--receipt")
    parser.add_argument("--structural-only", action="store_true")
    parser.add_argument("--architecture-only-output")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    if args.architecture_only_output:
        packet = _architecture_inner(
            root,
            base_ref=args.base_ref,
            head_ref=args.head_ref,
            observed_head=args.observed_head.strip() or _git(root, "rev-parse", "HEAD"),
            structural_only=False,
        )
        output = Path(args.architecture_only_output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(_canonical(packet) + b"\n")
        os._exit(0)
    if not args.receipt:
        parser.error("--receipt is required unless --architecture-only-output is used")
    packet = run(
        root,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        observed_head=args.observed_head,
        structural_only=args.structural_only,
    )
    encoded = _canonical(packet) + b"\n"
    if len(encoded) > _MAX_RECEIPT_BYTES:
        raise ValueError("Spatial S5/S6 harness receipt exceeds its byte cap")
    output = Path(args.receipt).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    print(
        json.dumps(
            {"ok": packet["ok"], "receipt": str(output), "receipt_digest": packet["receipt_digest"]}, sort_keys=True
        )
    )
    return 0 if packet["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
