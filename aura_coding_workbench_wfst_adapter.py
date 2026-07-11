"""Guarded-WFST session adapter for Aura's 18-state Coding Workbench.

The adapter composes ``aura_coding_workbench_sequence`` and existing workbench
functions. It never commits, pushes, merges, opens a PR, or mutates the active
Arena grammar. Consequential external work is represented as a reviewable packet.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import time
from typing import Any, Callable

from aura_arena_experience import build_arena_experience, sanitize_experience_payload
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_compiler import ARENA_WFST_COMPILER_VERSION
from aura_arena_wfst_runtime import ARENA_WFST_RUNTIME_VERSION, ArenaWFSTRuntime
from aura_coding_workbench_sequence import GATE_DEFINITIONS, WorkbenchState, get_gate

CODING_WORKBENCH_WFST_ADAPTER_VERSION = "AURA_CODING_WORKBENCH_WFST_ADAPTER_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class CodingWorkbenchWFSTSession:
    """Persistent local control session over the existing Coding Workbench gates."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        session_path: str | Path | None = None,
        restore: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.session_path = (
            Path(session_path).resolve()
            if session_path is not None
            else self.repo_root / "Aura_Memory" / "coding_workbench_wfst_session.json"
        )
        self.session_id = f"CWFST-{secrets.token_hex(8)}"
        self.state = WorkbenchState.WORKSPACE_OPENED
        self.objective = ""
        self.evidence: dict[str, Any] = {}
        self.event_log: list[dict[str, Any]] = []
        self.last_result: dict[str, Any] = {}
        self.runtime = ArenaWFSTRuntime(repo_root=self.repo_root)
        route_root = self.repo_root / ".aura" / "arena_routes"
        coding = self.runtime.register_manifest(route_root / "coding.v1.json")
        meta = self.runtime.register_manifest(route_root / "meta.v1.json")
        self.initialization = {"coding": coding, "meta": meta}
        self._ledger: ArenaExperienceLedger | None = None
        self._ledger_error = ""
        if restore and self.session_path.exists():
            self._restore()
        if "topology_health" not in self.evidence:
            self._initialize_topology()
        self._event("init", f"Coding Workbench WFST opened in {self.state.value}")
        self._persist()

    def close(self) -> None:
        self._persist()
        if self._ledger is not None:
            self._ledger.close()
            self._ledger = None

    def current_state(self) -> str:
        return self.state.value

    def project_state(self, *, telemetry: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._ready():
            return self._initialization_denial()
        route = self.runtime.project_state(
            arena_id="coding_workbench",
            current_state=self.state.value,
            evidence=dict(self.evidence),
            context=self._context({}),
            policy=self._policy(),
            telemetry=telemetry,
        )
        gate = get_gate(self.state).to_dict()
        route["legacy_gate"] = gate
        route["equivalence"] = {
            "legacy_allowed_actions": list(gate.get("allowed_actions", [])),
            "legacy_blocked_actions": list(gate.get("blocked_actions", [])),
            "legacy_required_evidence": list(gate.get("required_evidence", [])),
            "legacy_next_actions": list(gate.get("next_actions", [])),
        }
        return route

    def get_state(self) -> dict[str, Any]:
        gate = get_gate(self.state).to_dict()
        routing = self.project_state()
        return {
            "ok": bool(routing.get("ok")),
            "version": CODING_WORKBENCH_WFST_ADAPTER_VERSION,
            "session_id": self.session_id,
            "state": self.state.value,
            "objective": self.objective,
            "evidence_keys": sorted(self.evidence),
            "evidence": dict(self.evidence),
            "gate": gate,
            "routing": routing,
            "recommended": routing.get("recommended", []),
            "available": routing.get("available", []),
            "blocked": routing.get("blocked", []),
            "meta": routing.get("meta", []),
            "last_result": dict(self.last_result),
            "event_log": list(self.event_log[-40:]),
            "session_path": str(self.session_path),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }

    def route_command(
        self,
        command: str,
        *,
        payload: dict[str, Any] | None = None,
        telemetry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = str(command or "").strip()
        payload = dict(payload or {})
        if not text:
            return self._denial("command_required")
        if self.state is WorkbenchState.WORKSPACE_OPENED:
            evidence_view = dict(self.evidence)
            for key, value in payload.items():
                if value not in (None, "", [], {}, ()):
                    evidence_view[key] = value
            preview = self.runtime.route(
                arena_id="coding_workbench",
                current_state=self.state.value,
                input_text=text,
                evidence=evidence_view,
                context=self._context(payload),
                policy=self._policy(),
                telemetry=telemetry,
            )
            if not preview.get("selected"):
                return self.route_action(
                    "scope_task",
                    payload={**payload, "objective": text},
                    telemetry=telemetry,
                    original_command=text,
                )
        return self.route_action(text, payload=payload, telemetry=telemetry, original_command=text)

    def route_action(
        self,
        action_or_alias: str,
        *,
        payload: dict[str, Any] | None = None,
        telemetry: dict[str, Any] | None = None,
        original_command: str = "",
    ) -> dict[str, Any]:
        text = str(action_or_alias or "").strip()
        payload = dict(payload or {})
        state_before = self.state.value
        if not text:
            return self._denial("action_required")
        if not self._ready():
            return self._initialization_denial()

        evidence_view = dict(self.evidence)
        for key, value in payload.items():
            if value not in (None, "", [], {}, ()):
                evidence_view[key] = value
        if payload.get("approved") is not None or payload.get("reviewer") or isinstance(payload.get("human_approval"), dict):
            evidence_view["human_approval"] = _approval_record(payload)
        started = time.time()
        route = self.runtime.route(
            arena_id="coding_workbench",
            current_state=state_before,
            input_text=text,
            evidence=evidence_view,
            context=self._context(payload),
            policy=self._policy(),
            telemetry=telemetry,
        )
        selected = route.get("selected") if isinstance(route, dict) else None
        if not selected:
            outcome = "BLOCKED" if route.get("blocked") else "ABSTAINED"
            result = {
                **route,
                "ok": False,
                "status": outcome,
                "message": _blocked_message(route),
                "workflow": self.get_state_without_routing(),
            }
            result["experience_recording"] = self._record_experience(
                started_at=started,
                state_before=state_before,
                state_after=state_before,
                selected_transition="",
                final_outcome=outcome,
                payload={"command": original_command or text, "route": route},
            )
            self.last_result = result
            self._event("route", f"{text}:{outcome}")
            self._persist()
            return result

        if selected.get("meta_transition"):
            result = {
                **route,
                "ok": True,
                "status": "META_COMPLETED",
                "action_id": str(selected.get("transition_id") or ""),
                "message": "Meta guidance returned without changing Coding Workbench state.",
                "meta_response": _meta_response(selected, route),
                "workflow": self.get_state_without_routing(),
            }
            result["experience_recording"] = self._record_experience(
                started_at=started,
                state_before=state_before,
                state_after=state_before,
                selected_transition=str(selected.get("transition_id") or ""),
                final_outcome="META_COMPLETED",
                payload={"command": original_command or text, "route": route},
            )
            self.last_result = result
            self._event("meta", result["action_id"])
            self._persist()
            return result

        action_id = str((selected.get("provenance") or {}).get("action_id") or "")
        if not action_id:
            result = self._denial("selected_transition_has_no_action_binding")
            result.update({"route_decision": route, "workflow": self.get_state_without_routing()})
            result["experience_recording"] = self._record_experience(
                started_at=started,
                state_before=state_before,
                state_after=state_before,
                selected_transition=str(selected.get("transition_id") or ""),
                final_outcome="DENIED",
                payload={"command": original_command or text, "route": route},
            )
            self.last_result = result
            self._persist()
            return result

        action_result = self._execute_action(action_id, payload)
        if action_result.get("ok") or action_result.get("transition_on_failure"):
            next_state = str(action_result.get("next_state") or selected.get("next_state") or state_before)
            try:
                self.state = WorkbenchState(next_state)
            except ValueError:
                action_result = {
                    "ok": False,
                    "status": "DENIED",
                    "action_id": action_id,
                    "message": f"Action returned unknown next state: {next_state}",
                    "fail_closed": True,
                }
        state_after = self.state.value
        final_outcome = "COMPLETED" if action_result.get("ok") else "DENIED"
        result = {
            **action_result,
            "route_decision": route,
            "workflow": self.get_state_without_routing(),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        result["experience_recording"] = self._record_experience(
            started_at=started,
            state_before=state_before,
            state_after=state_after,
            selected_transition=str(selected.get("transition_id") or ""),
            final_outcome=final_outcome,
            payload={
                "command": original_command or text,
                "action_id": action_id,
                "route": route,
                "action_result": _bounded_result(action_result),
            },
        )
        self.last_result = result
        self._event("action", f"{action_id}:{final_outcome}:{state_before}->{state_after}")
        self._persist()
        return result

    def get_state_without_routing(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": CODING_WORKBENCH_WFST_ADAPTER_VERSION,
            "session_id": self.session_id,
            "state": self.state.value,
            "objective": self.objective,
            "evidence_keys": sorted(self.evidence),
            "evidence": dict(self.evidence),
            "gate": get_gate(self.state).to_dict(),
            "event_log": list(self.event_log[-40:]),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _execute_action(self, action_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            handler = getattr(self, f"_do_{action_id}")
        except AttributeError:
            return self._denial(f"unimplemented_workbench_action:{action_id}", action_id=action_id)
        try:
            result = handler(payload)
        except Exception as exc:  # noqa: BLE001
            return self._denial(f"workbench_action_failed:{type(exc).__name__}", action_id=action_id)
        result = dict(result or {})
        result.setdefault("action_id", action_id)
        result.setdefault("status", "ALLOWED" if result.get("ok") else "DENIED")
        result.setdefault("message", f"{action_id} {'completed' if result.get('ok') else 'was denied'}.")
        return result

    def _do_check_topology(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_topology_health import topology_health_packet
        health = topology_health_packet(repo_root=self.repo_root)
        self.evidence["topology_health"] = health
        if int(health.get("topology_nodes", 0) or 0) <= 0:
            return {
                "ok": True,
                "next_state": WorkbenchState.NEED_TOPOLOGY_REPAIR.value,
                "produced_evidence": {"topology_health": health},
                "message": "Topology is degraded; Coding Workbench entered the repair gate.",
            }
        return {
            "ok": True,
            "next_state": self.state.value,
            "produced_evidence": {"topology_health": health},
            "message": "Topology health checked without changing workflow position.",
        }

    def _do_scope_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import scope_task
        objective = str(payload.get("objective") or self.objective or "").strip()
        if not objective:
            return self._denial("objective_required", action_id="scope_task")
        output = scope_task(objective, repo_root=self.repo_root)
        if output.get("ok"):
            self.objective = objective
            self.evidence.update({"objective": objective, "scope": output.get("scope", {})})
        return _action_packet(output, "scope_task", produced={"objective": objective, "scope": output.get("scope", {})})

    def _do_filter_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import filter_context
        output = filter_context(self.objective, repo_root=self.repo_root, filters=payload.get("filters"))
        if output.get("ok"):
            self.evidence["filtered_context"] = output
        return _action_packet(output, "filter_context", produced={"filtered_context": output})

    def _do_localize_code(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import localize_code
        output = localize_code(self.objective, repo_root=self.repo_root)
        if output.get("ok"):
            self.evidence.update({
                "localized_files": list(output.get("localized_files") or []),
                "localized_symbols": list(output.get("localized_symbols") or []),
                "line_ranges": list(output.get("line_ranges") or []),
            })
        return _action_packet(output, "localize_code", produced={
            "localized_files": self.evidence.get("localized_files", []),
            "localized_symbols": self.evidence.get("localized_symbols", []),
            "line_ranges": self.evidence.get("line_ranges", []),
        })

    def _do_rank_code_regions(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import rank_code_regions
        output = rank_code_regions(
            self.objective,
            repo_root=self.repo_root,
            max_regions=int(payload.get("max_regions", 20)),
            max_lines=int(payload.get("max_lines", 400)),
        )
        if output.get("ok", True):
            self.evidence["ranked_regions"] = output
        return _action_packet(output, "rank_code_regions", produced={"ranked_regions": output})

    def _do_slice_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import slice_context
        localization = payload.get("localization_packet") or self.evidence.get("ranked_regions") or {
            "localized_files": self.evidence.get("localized_files", []),
            "localized_symbols": self.evidence.get("localized_symbols", []),
            "line_ranges": self.evidence.get("line_ranges", []),
        }
        output = slice_context(localization, repo_root=self.repo_root)
        if output.get("ok"):
            self.evidence["context_slices"] = output
        return _action_packet(output, "slice_context", produced={"context_slices": output})

    def _do_build_change_graph(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import build_change_graph
        localization = payload.get("localization_packet") or self.evidence.get("context_slices") or self.evidence.get("ranked_regions")
        output = build_change_graph(self.objective, localization, repo_root=self.repo_root)
        if not output.get("ok") and output.get("next_gate") == WorkbenchState.NEED_TOPOLOGY_REPAIR.value:
            self.evidence["topology_repair"] = output.get("topology_health", {})
            packet = _action_packet(output, "build_change_graph", next_state=WorkbenchState.NEED_TOPOLOGY_REPAIR.value)
            packet["transition_on_failure"] = True
            return packet
        if output.get("ok"):
            self.evidence["change_graph"] = output
        return _action_packet(output, "build_change_graph", produced={"change_graph": output})

    def _do_detect_refactor_candidates(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import detect_refactor_candidates
        output = detect_refactor_candidates(self.evidence.get("change_graph", {}), repo_root=self.repo_root)
        if output.get("ok", True):
            self.evidence["refactor_candidates"] = output
        return _action_packet(output, "detect_refactor_candidates", produced={"refactor_candidates": output})

    def _do_split_work(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import split_work
        source = payload.get("candidate") or self.evidence.get("refactor_candidates") or self.objective
        output = split_work(source, repo_root=self.repo_root)
        if output.get("ok", True):
            self.evidence["work_split"] = output
        return _action_packet(output, "split_work", produced={"work_split": output})

    def _do_create_act_capsules(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import create_act_capsules
        split_packet = payload.get("split_packet") or self.evidence.get("work_split")
        if not isinstance(split_packet, dict) or not split_packet:
            candidates = self.evidence.get("refactor_candidates")
            if not isinstance(candidates, dict) or not candidates:
                return self._denial("work_split_or_refactor_candidates_required", action_id="create_act_capsules")
            from aura_coding_workbench_actions import split_work
            split_packet = split_work(candidates, repo_root=self.repo_root)
            if not split_packet.get("ok", True):
                return self._denial("implicit_work_split_failed", action_id="create_act_capsules")
            self.evidence["work_split"] = split_packet
        output = create_act_capsules(split_packet, repo_root=self.repo_root)
        if output.get("ok", True):
            self.evidence["act_capsules"] = output.get("act_capsules", output)
        return _action_packet(output, "create_act_capsules", produced={"act_capsules": self.evidence.get("act_capsules")})

    def _do_prepare_agent_handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import prepare_agent_handoff
        capsules = self.evidence.get("act_capsules")
        items = capsules if isinstance(capsules, list) else (capsules.get("act_capsules", []) if isinstance(capsules, dict) else [])
        first = items[0] if items and isinstance(items[0], dict) else {}
        capsule_id = str(
            payload.get("capsule_id")
            or first.get("capsule_id")
            or first.get("task_id")
            or first.get("child_id")
            or ""
        )
        if not capsule_id:
            return self._denial("capsule_id_required", action_id="prepare_agent_handoff")
        output = prepare_agent_handoff(capsule_id, agent=str(payload.get("agent") or "hermes"), repo_root=self.repo_root)
        if output.get("ok"):
            self.evidence["agent_handoff_packet"] = output.get("handoff_packet", output)
        return _action_packet(output, "prepare_agent_handoff", produced={"agent_handoff_packet": self.evidence.get("agent_handoff_packet")})

    def _do_send_to_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        patch = payload.get("staged_patch") or self.evidence.get("staged_patch")
        if not patch:
            return self._denial("staged_patch_required_after_agent_handoff", action_id="send_to_agent")
        self.evidence["staged_patch"] = _bounded_patch_reference(patch)
        return {
            "ok": True,
            "action_id": "send_to_agent",
            "next_state": WorkbenchState.PATCH_STAGED.value,
            "message": "External-agent handoff result recorded as a staged patch reference; no patch was applied.",
            "produced_evidence": {"staged_patch": self.evidence["staged_patch"]},
            "external_execution_performed": False,
        }

    def _do_run_targeted_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import run_targeted_tests
        test_packet = dict(payload.get("test_packet") or {"targets": payload.get("test_targets", [])})
        output = run_targeted_tests(test_packet, repo_root=self.repo_root)
        self.evidence["test_run_plan"] = output
        return _action_packet(
            output,
            "run_targeted_tests",
            produced={"test_run_plan": output},
            message="Targeted test plan recorded. Passing test evidence is still required before verification.",
        )

    def _do_wait_for_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        results = payload.get("test_results") or self.evidence.get("test_results")
        if not isinstance(results, dict):
            return self._denial("measured_test_results_required", action_id="wait_for_tests")
        passed = bool(results.get("ok") or results.get("passed")) and not results.get("failed")
        self.evidence["test_results"] = results
        if not passed:
            return {
                "ok": False,
                "action_id": "wait_for_tests",
                "status": "DENIED",
                "message": "Tests did not pass; Coding Workbench remains at TESTS_RUNNING.",
                "missing_evidence": ["passing_test_results"],
                "next_state": WorkbenchState.TESTS_RUNNING.value,
            }
        self.evidence["verification_ok"] = True
        return {
            "ok": True,
            "action_id": "wait_for_tests",
            "next_state": WorkbenchState.PATCH_VERIFIED.value,
            "message": "Measured passing test results recorded.",
            "produced_evidence": {"test_results": results, "verification_ok": True},
        }

    def _do_request_human_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        packet = {
            "staged_patch": self.evidence.get("staged_patch"),
            "test_results": self.evidence.get("test_results"),
            "verification_ok": self.evidence.get("verification_ok") is True,
            "requested_at": time.time(),
            "production_mutation": False,
        }
        self.evidence["review_packet"] = packet
        return {
            "ok": True,
            "action_id": "request_human_review",
            "next_state": WorkbenchState.HUMAN_REVIEW_REQUIRED.value,
            "message": "Human review packet prepared. No PR or production mutation occurred.",
            "produced_evidence": {"review_packet": packet},
        }

    def _do_approve_for_pr(self, payload: dict[str, Any]) -> dict[str, Any]:
        approval = _approval_record(payload)
        if not approval["approved"]:
            return self._denial("explicit_human_approval_required", action_id="approve_for_pr")
        self.evidence["human_approval"] = approval
        return {
            "ok": True,
            "action_id": "approve_for_pr",
            "next_state": WorkbenchState.PR_READY.value,
            "message": "Human approval recorded. The work is eligible for a draft PR packet only.",
            "produced_evidence": {"human_approval": approval},
            "pr_opened": False,
        }

    def _do_reject(self, payload: dict[str, Any]) -> dict[str, Any]:
        rejection = {"approved": False, "reviewer": str(payload.get("reviewer") or "human_operator"), "note": str(payload.get("note") or ""), "recorded_at": time.time()}
        self.evidence["human_rejection"] = rejection
        return {
            "ok": True,
            "action_id": "reject",
            "next_state": WorkbenchState.HUMAN_REVIEW_REQUIRED.value,
            "message": "Human rejection recorded; the patch was not promoted.",
            "produced_evidence": {"human_rejection": rejection},
        }

    def _do_open_pr(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._pr_packet("open_pr", payload)

    def _do_generate_pr_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._pr_packet("generate_pr_command", payload)

    def _pr_packet(self, action_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        branch = str(payload.get("branch") or "feature/review-required")
        title = str(payload.get("title") or self.objective or "Aura Coding Workbench change")
        command = f"gh pr create --draft --base main --head {shlex.quote(branch)} --title {shlex.quote(title)}"
        packet = {"branch": branch, "title": title, "command": command, "draft": True, "executed": False}
        self.evidence["pr_packet"] = packet
        return {
            "ok": True,
            "action_id": action_id,
            "next_state": WorkbenchState.PR_READY.value,
            "message": "Draft PR command generated but not executed.",
            "produced_evidence": {"pr_packet": packet},
            "pr_opened": False,
        }

    def _do_repair_topology(self, payload: dict[str, Any]) -> dict[str, Any]:
        repair = payload.get("topology_repair") or self.evidence.get("topology_repair")
        if not repair:
            return self._denial("topology_repair_evidence_required", action_id="repair_topology")
        self.evidence["topology_repair"] = repair
        return {"ok": True, "action_id": "repair_topology", "next_state": WorkbenchState.WORKSPACE_OPENED.value, "message": "Topology repair evidence recorded; topology must be checked again."}

    def _do_text_only_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "action_id": "text_only_search", "next_state": WorkbenchState.NEED_TOPOLOGY_REPAIR.value, "message": "Text-only fallback selected; graph-dependent actions remain blocked."}

    def _do_review_risk(self, payload: dict[str, Any]) -> dict[str, Any]:
        review = payload.get("security_review") or {"reviewed": True, "note": str(payload.get("note") or ""), "recorded_at": time.time()}
        self.evidence["security_review"] = review
        return {"ok": True, "action_id": "review_risk", "next_state": WorkbenchState.BLOCKED_SECURITY_RISK.value, "message": "Security risk review recorded; execution remains blocked."}

    def _do_human_override(self, payload: dict[str, Any]) -> dict[str, Any]:
        approval = _approval_record(payload)
        if not approval["approved"] or not self.evidence.get("security_review"):
            return self._denial("security_review_and_human_approval_required", action_id="human_override")
        self.evidence["human_approval"] = approval
        return {"ok": True, "action_id": "human_override", "next_state": WorkbenchState.WORKSPACE_OPENED.value, "message": "Human override recorded; all downstream gates still apply."}

    def _initialize_topology(self) -> None:
        try:
            from aura_topology_health import topology_health_packet
            self.evidence["topology_health"] = topology_health_packet(repo_root=self.repo_root)
        except Exception as exc:  # noqa: BLE001
            self.evidence["topology_health"] = {"ok": False, "error": f"topology_health_unavailable:{type(exc).__name__}"}

    def _context(self, payload: dict[str, Any]) -> dict[str, Any]:
        approval = payload.get("human_approval")
        if approval is None and (payload.get("approved") is not None or payload.get("reviewer")):
            approval = _approval_record(payload)
        return {
            "objective": self.objective,
            "human_approval": approval or self.evidence.get("human_approval"),
            "lifecycle_allowed": True,
            "repository_commit": _git_value(self.repo_root, ["rev-parse", "HEAD"]),
            "working_tree_digest": _working_tree_digest(self.repo_root),
            "working_tree_dirty": bool(_git_value(self.repo_root, ["status", "--porcelain=v1"])),
            "snapshot_digest": str(payload.get("snapshot_digest") or ""),
        }

    @staticmethod
    def _policy() -> dict[str, Any]:
        return {
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
            "automatic_grammar_promotion": False,
        }

    def _ready(self) -> bool:
        return bool(self.initialization.get("coding", {}).get("ok") and self.initialization.get("meta", {}).get("ok"))

    def _initialization_denial(self) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "DENIED",
            "reason": "coding_workbench_wfst_initialization_failed",
            "initialization": self.initialization,
            "fail_closed": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _denial(self, reason: str, *, action_id: str = "") -> dict[str, Any]:
        return {
            "ok": False,
            "status": "DENIED",
            "action_id": action_id,
            "reason": reason,
            "message": reason.replace("_", " "),
            "fail_closed": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _event(self, kind: str, detail: str) -> None:
        self.event_log.append({"ts": time.time(), "kind": kind, "detail": detail})
        self.event_log = self.event_log[-120:]

    def _ledger_instance(self) -> ArenaExperienceLedger | None:
        if self._ledger is not None:
            return self._ledger
        if self._ledger_error:
            return None
        try:
            self._ledger = ArenaExperienceLedger(self.repo_root)
        except Exception as exc:  # noqa: BLE001
            self._ledger_error = f"experience_ledger_unavailable:{type(exc).__name__}"
            return None
        return self._ledger

    def _record_experience(self, *, started_at: float, state_before: str, state_after: str, selected_transition: str, final_outcome: str, payload: dict[str, Any]) -> dict[str, Any]:
        ledger = self._ledger_instance()
        if ledger is None:
            return {"ok": False, "reason": self._ledger_error or "experience_ledger_unavailable", "persistent": False}
        try:
            experience = build_arena_experience(
                arena_id="coding_workbench",
                arena_version="AURA_CODING_WORKBENCH_SEQUENCE_V1",
                grammar_version="coding-workbench-wfst-v1",
                runtime_version=ARENA_WFST_RUNTIME_VERSION,
                compiler_version=ARENA_WFST_COMPILER_VERSION,
                state_before=state_before,
                state_after=state_after,
                selected_transition=selected_transition,
                final_outcome=final_outcome,
                payload={"evidence_keys": sorted(self.evidence), **payload},
                task_id=self.session_id,
                workflow_id=self.session_id,
                started_at=started_at,
                completed_at=time.time(),
                repository_commit_sha=_git_value(self.repo_root, ["rev-parse", "HEAD"]),
                working_tree_digest=_working_tree_digest(self.repo_root),
                objective=self.objective,
                source_hashes=_source_hashes_from_evidence(self.evidence),
            )
            result = ledger.record(experience)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": f"experience_record_failed:{type(exc).__name__}", "persistent": False}
        return {**result, "persistent": bool(result.get("ok"))}

    def _persist(self) -> None:
        payload = {
            "version": CODING_WORKBENCH_WFST_ADAPTER_VERSION,
            "session_id": self.session_id,
            "state": self.state.value,
            "objective": self.objective,
            "evidence": _bounded_evidence(self.evidence),
            "event_log": self.event_log[-120:],
            "saved_at": time.time(),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        sanitized, _ = sanitize_experience_payload(payload)
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.session_path.with_suffix(self.session_path.suffix + ".tmp")
        temp.write_text(json.dumps(sanitized, sort_keys=True, indent=2, default=str), encoding="utf-8")
        os.replace(temp, self.session_path)

    def _restore(self) -> None:
        try:
            payload = json.loads(self.session_path.read_text(encoding="utf-8"))
            state = WorkbenchState(str(payload.get("state") or WorkbenchState.WORKSPACE_OPENED.value))
            evidence = payload.get("evidence") or {}
            if not isinstance(evidence, dict):
                raise ValueError("evidence_not_object")
            self.session_id = str(payload.get("session_id") or self.session_id)
            self.state = state
            self.objective = str(payload.get("objective") or "")
            self.evidence = dict(evidence)
            self.event_log = list(payload.get("event_log") or [])[-120:]
        except Exception as exc:  # noqa: BLE001
            self.state = WorkbenchState.WORKSPACE_OPENED
            self.objective = ""
            self.evidence = {}
            self.event_log = [{"ts": time.time(), "kind": "restore_failed", "detail": type(exc).__name__}]


def _action_packet(output: dict[str, Any], action_id: str, *, produced: dict[str, Any] | None = None, next_state: str = "", message: str = "") -> dict[str, Any]:
    output = dict(output or {})
    ok = bool(output.get("ok", True))
    return {
        "ok": ok,
        "status": "ALLOWED" if ok else "DENIED",
        "action_id": action_id,
        "message": message or str(output.get("message") or output.get("error") or f"{action_id} {'completed' if ok else 'failed'}"),
        "next_state": next_state or str(output.get("next_gate") or ""),
        "produced_evidence": dict(produced or {}),
        "details": output,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _approval_record(payload: dict[str, Any]) -> dict[str, Any]:
    nested = payload.get("human_approval") if isinstance(payload.get("human_approval"), dict) else {}
    approved = bool(payload.get("approved", nested.get("approved", nested.get("approved_for_next_gate", False))))
    return {
        "approved": approved,
        "reviewer": str(payload.get("reviewer") or nested.get("reviewer") or "human_operator"),
        "note": str(payload.get("note") or nested.get("note") or ""),
        "recorded_at": time.time(),
        "automatic": False,
    }


def _bounded_patch_reference(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
        return {"kind": "patch_metadata", "digest": hashlib.blake2b(body.encode(), digest_size=16).hexdigest(), "keys": sorted(value), "size_bytes": len(body)}
    body = str(value)
    return {"kind": "patch_reference", "digest": hashlib.blake2b(body.encode(), digest_size=16).hexdigest(), "size_bytes": len(body)}


def _bounded_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in evidence.items():
        if any(term in key.casefold() for term in ("diff", "source_text", "full_source", "private_key")):
            output[key] = _bounded_patch_reference(value)
        else:
            output[key] = value
    return output


def _source_hashes_from_evidence(evidence: dict[str, Any]) -> list[str]:
    output: list[str] = []
    stack: list[Any] = [evidence]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if "hash" in str(key).casefold() and isinstance(item, str) and item:
                    output.append(item)
                elif isinstance(item, (dict, list, tuple)):
                    stack.append(item)
        elif isinstance(value, (list, tuple)):
            stack.extend(value)
    return sorted(set(output))


def _bounded_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "status": result.get("status"),
        "action_id": result.get("action_id"),
        "message": str(result.get("message") or "")[:1000],
        "missing_evidence": list(result.get("missing_evidence") or []),
        "produced_evidence_keys": sorted((result.get("produced_evidence") or {}).keys()),
    }


def _blocked_message(route: dict[str, Any]) -> str:
    blocked = route.get("blocked") or []
    if not blocked:
        return "No safe state-local transition matched. Clarification is required."
    missing = sorted({item for row in blocked for item in row.get("missing_evidence", [])})
    return "Transition blocked by hard guards." + (f" Missing: {', '.join(missing)}." if missing else "")


def _meta_response(selected: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    transition_id = str(selected.get("transition_id") or "")
    if transition_id == "META.WHY_BLOCKED":
        return {"kind": "why_blocked", "blocked": route.get("blocked", [])}
    if transition_id == "META.WHAT_NEXT":
        return {"kind": "what_next", "recommended": [item for item in route.get("recommended", []) if not item.get("meta_transition")]}
    return {"kind": transition_id.casefold().replace(".", "_"), "state": route.get("state"), "recommended": route.get("recommended", []), "blocked": route.get("blocked", [])}


def _git_value(repo_root: Path, args: list[str]) -> str:
    import subprocess
    try:
        result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, timeout=3, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _working_tree_digest(repo_root: Path) -> str:
    value = _git_value(repo_root, ["status", "--porcelain=v1"])
    return hashlib.blake2b(value.encode("utf-8"), digest_size=12).hexdigest()
