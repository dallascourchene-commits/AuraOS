"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f4-[Q-SYS:HUMAN_AGENT_ARENA_SERVER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Local Human Agent Arena HTTP Surface)
DEPENDENCIES: __future__, argparse, http.server, json, mimetypes, pathlib, urllib.parse, typing,
              aura_human_agent_arena, aura_human_agent_workflow,
              aura_coding_workbench_wfst_adapter, aura_emergent_refactor_workspace,
              aura_arena_research_bridge
FUNCTIONS: HumanAgentArenaServerState, dispatch_api_request, make_handler, serve, main
SYNOPSIS: Local Human Agent Arena HTTP surface with guarded-WFST Human and Coding
workflow projections, bounded ephemeral tools, persistent emergent-property evidence,
bounded arXiv/GitHub research, and jurisdiction-aware Civic map projection. No direct
production mutation. External evidence never grants patch authority.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from aura_arena_research_bridge import ArenaResearchBridge
from aura_coding_workbench_wfst_adapter import CodingWorkbenchWFSTSession
from aura_emergent_refactor_workspace import EmergentResultsStore
from aura_human_agent_arena import HumanAgentArena
from aura_human_agent_workflow import HumanAgentWorkflow

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090
FRONTEND_DIR = Path(__file__).resolve().parent / "aura_human_agent_arena"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SERVER_VERSION = "AURA_HUMAN_AGENT_ARENA_SERVER_V0_4"


class AuraThreadingHTTPServer(ThreadingHTTPServer):
    """Serve slow research requests without freezing the Arena control surface."""

    daemon_threads = True
    allow_reuse_address = True


class HumanAgentArenaServerState:
    """Holds spatial, guarded-workflow, emergent-evidence, and research surfaces."""

    def __init__(self, repo_root: str | Path = ".", *, demo: bool = False):
        self.repo_root = Path(repo_root).resolve()
        self.demo = bool(demo)
        self.arena = HumanAgentArena(self.repo_root, demo=self.demo)
        self.workflow = HumanAgentWorkflow(self.repo_root)
        self.coding_workbench = CodingWorkbenchWFSTSession(self.repo_root)
        self.emergent_store = EmergentResultsStore(self.repo_root)
        self.seed_import = self.emergent_store.import_seed_reports()
        self.research_bridge = ArenaResearchBridge(str(self.repo_root))

    def close(self) -> None:
        self.workflow.close()
        self.coding_workbench.close()


def _error(message: str, code: int = 400) -> tuple[int, dict[str, Any]]:
    return code, {
        "ok": False,
        "error": str(message),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _handle_civic_api(method: str, route: str, parsed: Any, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Handle Civic Commons Arena API requests."""
    path_parts = parsed.path.strip("/").split("/")
    query = parse_qs(parsed.query)

    try:
        from aura_civic_runtime import (
            create_civic_session,
            get_session,
            add_contribution,
            match_resources,
            run_mitosis,
            run_scenarios,
            get_consent,
            record_consent_response,
            run_what_if,
            create_pilot,
            get_issue_pulse,
            export_packet,
            close_session,
            select_profiles,
        )
    except Exception as exc:  # noqa: BLE001
        return _error(f"civic_runtime_unavailable: {exc}", 503)

    if method == "GET" and route == "/api/civic/status":
        try:
            from aura_civic_snapshots import list_snapshots
            snapshots = list_snapshots().get("snapshots", [])
        except Exception:  # noqa: BLE001
            snapshots = []
        return 200, {
            "ok": True,
            "civic_available": True,
            "snapshots": snapshots,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    if method == "POST" and route == "/api/civic/sessions":
        objective = str(body.get("objective") or "")
        story = str(body.get("story") or "hairstylist")
        result = create_civic_session(objective)
        if result.get("ok") and story:
            try:
                from aura_civic_runtime import _update_session
                _update_session(result["session"]["session_id"], {"story": story})
            except Exception:  # noqa: BLE001
                pass
        return 200, result

    if method == "GET" and len(path_parts) == 4 and path_parts[2] == "sessions":
        return 200, get_session(path_parts[3])

    if method == "POST" and len(path_parts) == 5 and path_parts[2] == "sessions":
        session_id = path_parts[3]
        action = path_parts[4]
        handlers = {
            "profiles": lambda: select_profiles(session_id, body.get("profile_refs", [])),
            "contributions": lambda: add_contribution(session_id, body),
            "consent": lambda: get_consent(session_id),
            "resource-match": lambda: match_resources(session_id),
            "mitosis": lambda: run_mitosis(session_id),
            "scenarios": lambda: run_scenarios(session_id),
            "responses": lambda: record_consent_response(session_id, body),
            "what-if": lambda: run_what_if(session_id, body),
            "pilot": lambda: create_pilot(session_id, str(body.get("scenario_id") or "")),
            "export": lambda: export_packet(session_id),
            "close": lambda: close_session(session_id),
        }
        if action == "tensor-analyze":
            session = get_session(session_id)
            if session.get("ok"):
                from aura_civic_tensor_adapter import analyze_civic_session
                return 200, analyze_civic_session(session["session"])
            return 200, session
        handler = handlers.get(action)
        if handler is not None:
            return 200, handler()

    if method == "GET" and len(path_parts) == 5 and path_parts[2] == "sessions":
        session_id = path_parts[3]
        action = path_parts[4]
        if action == "consent":
            return 200, get_consent(session_id)
        if action == "issue-pulse":
            return 200, get_issue_pulse(session_id)
        session = get_session(session_id)
        if not session.get("ok"):
            return 200, session
        manifest = session["session"].get("map_manifest", {})
        if not manifest:
            try:
                from aura_civic_organs import civic_map_organ
                manifest = civic_map_organ(session["session"]).get("map_manifest", {})
            except Exception:  # noqa: BLE001
                manifest = {}
        if action == "map-manifest":
            return 200, {
                "ok": True,
                "map_manifest": manifest,
                "accessible_table_parity": True,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        if action == "map-projection":
            from aura_civic_map import project_map_manifest
            projection = project_map_manifest(
                manifest,
                bbox=query.get("bbox", [None])[0],
                zoom=_query_float(query.get("zoom", [None])[0], default=10.0),
                jurisdiction_id=str(query.get("jurisdiction", [""])[0] or ""),
                viewer_scope=str(query.get("viewer_scope", ["community"])[0] or "community"),
            )
            return (200 if projection.get("ok") else 400), projection

    if method == "GET" and len(path_parts) == 6 and path_parts[2] == "sessions":
        session = get_session(path_parts[3])
        if not session.get("ok"):
            return 200, session
        object_id = path_parts[5]
        if path_parts[4] == "evidence":
            for item in session["session"].get("legal_instruments", []):
                if item.get("id", item.get("source_id", "")) == object_id:
                    return 200, {
                        "ok": True,
                        "evidence": item,
                        "patch_authority": PATCH_AUTHORITY,
                        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                    }
            return _error("evidence not found", 404)
        if path_parts[4] == "legal":
            instruments = session["session"].get("legal_instruments", [])
            filtered = [item for item in instruments if item.get("scenario_id") == object_id]
            return 200, {
                "ok": True,
                "legal_instruments": filtered or instruments,
                "no_legal_approval": True,
                "disclaimer": "Aura is not providing legal advice.",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

    return _error("civic route not found", 404)


def _attach_emergent_refactor_context(
    state: HumanAgentArenaServerState,
    objective: str,
    *,
    finding_ids: Iterable[str] = (),
    research_evidence_ids: Iterable[str] = (),
) -> dict[str, Any]:
    objective_text = str(objective or "").strip()
    if not objective_text:
        return {"ok": False, "error": "objective_required_for_emergent_context"}
    emergent_store = getattr(state, "emergent_store", None)
    if emergent_store is None:
        return {
            "ok": False,
            "status": "UNAVAILABLE",
            "error": "emergent_workspace_unavailable",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    packet_result = emergent_store.build_refactor_packet(
        objective_text,
        finding_ids=list(finding_ids),
        research_evidence_ids=list(research_evidence_ids),
        max_findings=8,
        persist=True,
    )
    packet = dict(packet_result.get("packet") or {})
    if not packet:
        return packet_result
    workflow_evidence = state.workflow.evidence
    workflow_evidence["emergent_refactor_packet"] = packet
    workflow_evidence["emergent_findings"] = list(packet.get("selected_findings") or [])
    workflow_evidence["research_gaps"] = list(packet.get("research_gaps") or [])
    workflow_evidence["external_research_evidence"] = list(packet.get("research_evidence") or [])
    existing_tests = list(workflow_evidence.get("test_targets") or [])
    workflow_evidence["test_targets"] = _unique([*existing_tests, *list(packet.get("required_tests") or [])])[:16]
    return packet_result


def _prepare_payload_with_emergent_context(
    state: HumanAgentArenaServerState,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    objective = str(state.workflow.state.objective or payload.get("objective") or "").strip()
    result = _attach_emergent_refactor_context(
        state,
        objective,
        finding_ids=list(payload.get("finding_ids") or []),
        research_evidence_ids=list(payload.get("research_evidence_ids") or []),
    ) if objective else {"ok": False, "error": "objective_not_set"}
    packet = dict(result.get("packet") or {})
    merged = dict(payload)
    merged["acceptance_criteria"] = _unique(
        [
            *list(payload.get("acceptance_criteria") or []),
            *list(packet.get("acceptance_criteria") or []),
            *[f"Close or explicitly defer research gap: {item.get('gap')}" for item in packet.get("research_gaps", []) if item.get("gap")],
        ]
    )
    merged["emergent_refactor_packet_id"] = packet.get("packet_id", "")
    return merged, result


def _handle_emergent_and_research_api(
    state: HumanAgentArenaServerState,
    method: str,
    route: str,
    query: dict[str, list[str]],
    body: dict[str, Any],
) -> tuple[int, dict[str, Any]] | None:
    if method == "GET" and route == "/api/human-agent/emergent/runs":
        return 200, state.emergent_store.list_runs(limit=_query_int(query.get("limit", [None])[0], default=50))

    if method == "GET" and route == "/api/human-agent/emergent/search":
        text = str(query.get("q", [""])[0] or "")
        statuses = [item for item in str(query.get("status", [""])[0] or "").split(",") if item]
        return 200, state.emergent_store.search_findings(
            text,
            limit=_query_int(query.get("limit", [None])[0], default=20),
            statuses=statuses,
        )

    if method == "GET" and route.startswith("/api/human-agent/emergent/findings/"):
        finding_id = route.rsplit("/", 1)[-1]
        result = state.emergent_store.get_finding(finding_id)
        return (200 if result.get("ok") else 404), result

    if method == "GET" and route.startswith("/api/human-agent/emergent/runs/"):
        run_id = route.rsplit("/", 1)[-1]
        result = state.emergent_store.get_run(run_id)
        return (200 if result.get("ok") else 404), result

    if method == "POST" and route == "/api/human-agent/emergent/import":
        report = body.get("report")
        if not isinstance(report, dict) or not report:
            return _error("report is required")
        try:
            result = state.emergent_store.store_report(
                report,
                source=str(body.get("source") or "human_agent_arena_import"),
                label=str(body.get("label") or ""),
                metadata=dict(body.get("metadata") or {}),
            )
        except Exception as exc:  # noqa: BLE001
            return _error(f"emergent_import_failed:{exc}")
        return 200, result

    if method == "POST" and route == "/api/human-agent/emergent/refactor-packet":
        objective = str(body.get("objective") or state.workflow.state.objective or "").strip()
        try:
            result = _attach_emergent_refactor_context(
                state,
                objective,
                finding_ids=list(body.get("finding_ids") or []),
                research_evidence_ids=list(body.get("research_evidence_ids") or []),
            )
        except Exception as exc:  # noqa: BLE001
            return _error(f"refactor_packet_failed:{exc}")
        return (200 if result.get("ok") else 409), result

    if method == "POST" and route == "/api/human-agent/research/search":
        provider = str(body.get("provider") or "").lower()
        search_query = str(body.get("query") or "")
        try:
            result = state.research_bridge.search(
                provider,
                search_query,
                limit=int(body.get("limit") or 8),
                include_sidecars=bool(body.get("include_sidecars", False)),
                sidecar_limit=int(body.get("sidecar_limit") or 2),
            )
        except Exception as exc:  # noqa: BLE001
            return _error(f"research_search_failed:{exc}")
        if not result.get("ok"):
            return 502, result
        stored = state.emergent_store.store_research_evidence(
            provider=provider,
            query=search_query,
            results=list(result.get("results") or []),
            linked_finding_ids=list(body.get("finding_ids") or []),
            metadata={
                "metadata_truth": result.get("metadata_truth"),
                "sidecar_truth": result.get("sidecar_truth"),
                "count": result.get("count", 0),
            },
        )
        result["stored_evidence"] = stored
        return 200, result

    if method == "GET" and route == "/api/human-agent/research/evidence":
        return 200, state.emergent_store.list_research_evidence(
            limit=_query_int(query.get("limit", [None])[0], default=50)
        )

    if method == "GET" and route.startswith("/api/human-agent/research/evidence/"):
        evidence_id = route.rsplit("/", 1)[-1]
        result = state.emergent_store.get_research_evidence(evidence_id)
        return (200 if result.get("ok") else 404), result

    return None


def dispatch_api_request(
    state: HumanAgentArenaServerState,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Pure dispatcher used by the server and deterministic tests."""
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    route = parsed.path.rstrip("/") or "/"
    body = dict(payload or {})

    if route.startswith("/api/civic"):
        return _handle_civic_api(method, route, parsed, body)

    enhanced = _handle_emergent_and_research_api(state, method, route, query, body)
    if enhanced is not None:
        return enhanced

    if method == "GET" and route == "/api/human-agent/state":
        workflow = state.workflow.get_state()
        return 200, {
            "ok": True,
            "version": SERVER_VERSION,
            "state": state.arena.get_state(),
            "topology": state.arena.topology,
            "workflow": workflow,
            "routing": workflow.get("routing", {}),
            "coding_workbench": state.coding_workbench.get_state(),
            "emergent_workspace": state.emergent_store.list_runs(limit=20),
            "seed_import": state.seed_import,
            "research_evidence": state.emergent_store.list_research_evidence(limit=20),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    if method == "GET" and route == "/api/human-agent/events":
        since = _query_int(query.get("since", [None])[0], default=0)
        return 200, state.arena.get_events(since=since)

    if method == "GET" and route == "/api/human-agent/topology":
        return 200, state.arena.topology

    if method == "GET" and route == "/api/human-agent/workflow":
        return 200, state.workflow.get_state()

    if method == "GET" and route == "/api/human-agent/routes":
        workflow = state.workflow.get_state()
        return 200, {
            "ok": bool(workflow.get("routing", {}).get("ok")),
            "workflow_id": workflow.get("workflow_id"),
            "current_phase": workflow.get("current_phase"),
            "routing": workflow.get("routing", {}),
            "recommended": workflow.get("recommended", []),
            "available": workflow.get("available", []),
            "blocked": workflow.get("blocked", []),
            "meta": workflow.get("meta", []),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    if method == "POST" and route == "/api/human-agent/workflow/action":
        action_id = str(body.get("action_id") or "")
        if not action_id:
            return _error("action_id is required")
        action_payload = dict(body.get("payload") or {})
        emergent_context: dict[str, Any] = {}
        if action_id == "prepare_capsule":
            action_payload, emergent_context = _prepare_payload_with_emergent_context(state, action_payload)
        elif action_id == "ground_context" and state.workflow.state.objective:
            emergent_context = _attach_emergent_refactor_context(state, state.workflow.state.objective)
        result = state.workflow.execute_guarded(action_id, action_payload)
        if result.get("ok") and action_id in {"set_objective", "ground_context"}:
            objective = str(state.workflow.state.objective or action_payload.get("objective") or "")
            if objective:
                emergent_context = _attach_emergent_refactor_context(state, objective)
        if emergent_context:
            result["emergent_context"] = emergent_context
            result["workflow"] = state.workflow.get_state()
        return (200 if result.get("ok") else 409), result

    if method == "POST" and route == "/api/human-agent/workflow/command":
        command = str(body.get("command") or "")
        if not command.strip():
            return _error("command is required")
        command_payload = dict(body.get("payload") or {})
        emergent_context: dict[str, Any] = {}
        if state.workflow.state.objective:
            command_payload, emergent_context = _prepare_payload_with_emergent_context(state, command_payload)
        result = state.workflow.ingest_command(command, command_payload)
        objective = str(state.workflow.state.objective or "")
        if result.get("ok") and objective:
            emergent_context = _attach_emergent_refactor_context(state, objective)
            result["emergent_context"] = emergent_context
            result["workflow"] = state.workflow.get_state()
        return (200 if result.get("ok") else 409), result

    if method == "GET" and route == "/api/coding-workbench/state":
        return 200, state.coding_workbench.get_state()

    if method == "GET" and route == "/api/coding-workbench/routes":
        return 200, state.coding_workbench.project_state()

    if method == "POST" and route == "/api/coding-workbench/action":
        action_id = str(body.get("action_id") or "")
        if not action_id:
            return _error("action_id is required")
        result = state.coding_workbench.route_action(action_id, payload=dict(body.get("payload") or {}))
        return (200 if result.get("ok") else 409), result

    if method == "POST" and route == "/api/coding-workbench/command":
        command = str(body.get("command") or "")
        if not command.strip():
            return _error("command is required")
        result = state.coding_workbench.route_command(command, payload=dict(body.get("payload") or {}))
        return (200 if result.get("ok") else 409), result

    if method == "GET" and route == "/api/human-agent/tools":
        tools = state.workflow.tools.get_tools()
        tools.setdefault("tools", [])
        tools["tools"].extend(
            [
                {
                    "tool_id": "emergent_refactor_workspace",
                    "title": "Emergent Refactor Workspace",
                    "purpose": "Search stored emergent properties and compile them into refactor evidence.",
                    "capability": "search_emergent_evidence",
                    "stage": "GROUND",
                    "risk": "low",
                    "runtime": "trusted_server_adapter",
                    "requires": ["objective"],
                    "produces": ["emergent_refactor_packet", "research_gaps"],
                },
                {
                    "tool_id": "research_forager",
                    "title": "arXiv / GitHub Research Forager",
                    "purpose": "Search official public APIs and preserve bounded external evidence for missing pieces.",
                    "capability": "external_research",
                    "stage": "GROUND",
                    "risk": "medium",
                    "runtime": "bounded_network_adapter",
                    "requires": ["provider", "query"],
                    "produces": ["research_evidence"],
                },
            ]
        )
        return 200, tools

    if method == "POST" and route == "/api/human-agent/tools/run":
        tool_id = str(body.get("tool_id") or "")
        if not tool_id:
            return _error("tool_id is required")
        inputs = dict(body.get("inputs") or {})
        objective = str(body.get("objective") or state.workflow.state.objective)
        if tool_id == "emergent_refactor_workspace":
            result = _attach_emergent_refactor_context(
                state,
                objective,
                finding_ids=list(inputs.get("finding_ids") or []),
                research_evidence_ids=list(inputs.get("research_evidence_ids") or []),
            )
            return (200 if result.get("ok") else 409), {
                "run_id": str((result.get("packet") or {}).get("packet_id") or ""),
                "tool_id": tool_id,
                "status": "COMPLETED" if result.get("ok") else "FAILED",
                "outputs": result,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        if tool_id == "research_forager":
            return dispatch_api_request(
                state,
                "POST",
                "/api/human-agent/research/search",
                {
                    "provider": inputs.get("provider"),
                    "query": inputs.get("query") or objective,
                    "limit": inputs.get("limit", 8),
                    "include_sidecars": inputs.get("include_sidecars", False),
                    "sidecar_limit": inputs.get("sidecar_limit", 2),
                    "finding_ids": inputs.get("finding_ids", []),
                },
            )
        result = state.workflow.tools.execute(
            tool_id,
            objective=objective,
            inputs=inputs,
        )
        return (200 if result.get("status") != "DENIED" else 409), result

    if method == "GET" and route.startswith("/api/human-agent/tool-runs/"):
        run_id = route.rsplit("/", 1)[-1]
        result = state.workflow.tools.get_run(run_id)
        return (200 if result.get("ok") else 404), result

    if method == "GET" and route == "/api/human-agent/cost-telemetry":
        try:
            from aura_cost_telemetry_events import get_telemetry_stream
            from aura_empirical_cost_ledger import EmpiricalCostLedger
            stream = get_telemetry_stream()
            ledger = EmpiricalCostLedger(repo_root=state.repo_root)
            history = ledger.get_history(limit=10)
            ledger.close()
            return 200, {
                "ok": True,
                "event_count": stream.event_count(),
                "recent_events": stream.get_events(limit=20),
                "recent_runs": history,
                "visual_states": {
                    "measured": "green",
                    "estimated": "yellow",
                    "unavailable": "grey",
                    "verified": "green",
                    "invalidated": "red",
                    "counterfactual": "purple",
                },
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:  # noqa: BLE001
            return 200, {
                "ok": True,
                "event_count": 0,
                "recent_events": [],
                "recent_runs": [],
                "note": f"Cost telemetry unavailable: {exc}",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

    if method == "GET" and route == "/api/human-agent/cost-events":
        try:
            from aura_cost_telemetry_events import get_telemetry_stream
            since = _query_float(query.get("since", [None])[0], default=0.0)
            events = get_telemetry_stream().get_events(since=since, limit=100)
            return 200, {
                "ok": True,
                "events": events,
                "count": len(events),
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        except Exception as exc:  # noqa: BLE001
            return 200, {
                "ok": True,
                "events": [],
                "count": 0,
                "note": f"Cost events unavailable: {exc}",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

    if method == "POST" and route == "/api/human-agent/command":
        command = str(body.get("command") or "")
        if not command.strip():
            return _error("command is required")
        mode = str(body.get("mode") or "explore").strip()
        if mode not in {"explore", "diagnose", "hypothesize", "prepare"}:
            mode = "explore"
        result = state.arena.route_command(
            command,
            selected_node_ids=_node_ids(body),
            mode=mode,
        )
        return 200, result

    return _error(f"Unknown route: {method} {route}", 404)


def make_handler(state: HumanAgentArenaServerState):
    class HumanAgentArenaHandler(BaseHTTPRequestHandler):
        server_version = "AuraHumanAgentArena/0.4"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._send_json(*dispatch_api_request(state, "GET", self.path))
                return
            self._serve_static(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    payload = {}
            except json.JSONDecodeError:
                self._send_json(400, {"ok": False, "error": "invalid JSON"})
                return
            self._send_json(*dispatch_api_request(state, "POST", parsed.path, payload))

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_static(self, request_path: str) -> None:
            rel = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
            candidate = (FRONTEND_DIR / rel).resolve()
            try:
                candidate.relative_to(FRONTEND_DIR.resolve())
            except ValueError:
                self.send_error(403)
                return
            if not candidate.exists() or not candidate.is_file():
                self.send_error(404)
                return
            body = candidate.read_bytes()
            if rel == "index.html":
                text = body.decode("utf-8", errors="replace")
                if "wfst.css" not in text:
                    text = text.replace("</head>", '  <link rel="stylesheet" href="wfst.css">\n</head>')
                if "wfst.js" not in text:
                    text = text.replace("</body>", '  <script src="wfst.js"></script>\n</body>')
                body = text.encode("utf-8")
            mime = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("content-type", mime)
            self.send_header("cache-control", "no-store")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return HumanAgentArenaHandler


def serve(
    repo_root: str | Path = ".",
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    demo: bool = False,
) -> AuraThreadingHTTPServer:
    state = HumanAgentArenaServerState(repo_root, demo=demo)
    server = AuraThreadingHTTPServer((host, int(port)), make_handler(state))
    print(f"Aura Human Agent Arena listening on http://{host}:{port}")
    print("Guarded Human and Coding WFST workflows are active.")
    print("Stored emergent evidence and bounded arXiv/GitHub research are active.")
    print("External evidence is advisory; exact source spans, tests, and human review remain authoritative.")
    try:
        server.serve_forever()
    finally:
        state.close()
        server.server_close()
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aura's local Human Agent Arena.")
    parser.add_argument("--repo-root", default=".", help="AuraOS repository root")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--demo", action="store_true", help="Use the built-in offline demo topology")
    args = parser.parse_args(argv)
    serve(args.repo_root, host=args.host, port=args.port, demo=args.demo)
    return 0


def _node_ids(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("selected_node_ids", payload.get("node_ids", []))
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if item]
    return []


def _query_int(value: str | None, *, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        return default


def _query_float(value: str | None, *, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return max(0.0, float(value))
    except (ValueError, TypeError):
        return default


def _unique(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list)) else str(value)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
