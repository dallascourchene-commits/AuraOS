"""Guarded-WFST adapter for the existing HumanAgentWorkflow public API.

The adapter composes the current workflow rather than replacing it. Existing action
methods remain the execution authority; the WFST selects only declared, state-local,
admissible actions and records observable experience.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import time
from typing import Any

from aura_arena_experience import build_arena_experience
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_compiler import ARENA_WFST_COMPILER_VERSION
from aura_arena_wfst_runtime import ARENA_WFST_RUNTIME_VERSION, ArenaWFSTRuntime

HUMAN_AGENT_WFST_ADAPTER_VERSION = "AURA_HUMAN_AGENT_WFST_ADAPTER_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class HumanAgentWFSTController:
    def __init__(self, workflow: Any, *, repo_root: str | Path = ".") -> None:
        self.workflow = workflow
        self.repo_root = Path(repo_root).resolve()
        self.runtime = ArenaWFSTRuntime(repo_root=self.repo_root)
        base = self.repo_root / ".aura" / "arena_routes"
        human = self.runtime.register_manifest(base / "human_agent.v1.json")
        meta = self.runtime.register_manifest(base / "meta.v1.json")
        self.initialization = {"human": human, "meta": meta}
        self._ledger: ArenaExperienceLedger | None = None
        self._ledger_error = ""

    def project_state(self, *, telemetry: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self._workflow_state()
        if not self._ready():
            return self._initialization_denial(state)
        return self.runtime.project_state(
            arena_id="human_agent",
            current_state=state,
            evidence=dict(getattr(self.workflow, "evidence", {}) or {}),
            context=self._context(),
            policy=self._policy(),
            telemetry=telemetry,
        )

    def route_action(
        self,
        action_id: str,
        *,
        payload: dict[str, Any] | None = None,
        telemetry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.route_command(action_id, payload=payload, telemetry=telemetry)

    def route_command(
        self,
        command: str,
        *,
        payload: dict[str, Any] | None = None,
        telemetry: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = str(command or "").strip()
        payload = dict(payload or {})
        state_before = self._workflow_state()
        if not text:
            return {
                "ok": False,
                "status": "DENIED",
                "reason": "command_required",
                "message": "Command is required.",
                "state": state_before,
                "workflow": self._workflow_snapshot(),
            }
        if not self._ready():
            return self._initialization_denial(state_before)

        evidence_view = dict(getattr(self.workflow, "evidence", {}) or {})
        for key, value in payload.items():
            if value not in (None, "", [], {}, ()):
                evidence_view[key] = value

        started = time.time()
        route_input = text
        execution_payload = payload
        route = self.runtime.route(
            arena_id="human_agent",
            current_state=state_before,
            input_text=route_input,
            evidence=evidence_view,
            context=self._context(),
            policy=self._policy(),
            telemetry=telemetry,
        )

        # A free-form request at FRAME is an objective only when it did not resolve
        # to a declared state-local or Meta transition. This preserves "help" and
        # "status" as Meta self-loops instead of accidentally making them objectives.
        if state_before == "FRAME" and not route.get("selected"):
            route_input = "HUMAN.SET_OBJECTIVE"
            execution_payload = {**payload, "objective": text}
            route = self.runtime.route(
                arena_id="human_agent",
                current_state=state_before,
                input_text=route_input,
                evidence=evidence_view,
                context=self._context(),
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
                "workflow": self._workflow_snapshot(),
            }
            result["experience_recording"] = self._record_experience(
                started_at=started,
                state_before=state_before,
                state_after=state_before,
                selected_transition="",
                final_outcome=outcome,
                payload={"command": text, "route": route},
            )
            return result

        if selected.get("meta_transition"):
            response = self._meta_response(selected, route)
            result = {
                **route,
                "ok": True,
                "status": "META_COMPLETED",
                "action_id": str(selected.get("transition_id") or ""),
                "message": "Meta guidance returned without changing workflow state.",
                "meta_response": response,
                "workflow": self._workflow_snapshot(),
            }
            result["experience_recording"] = self._record_experience(
                started_at=started,
                state_before=state_before,
                state_after=state_before,
                selected_transition=str(selected.get("transition_id") or ""),
                final_outcome="META_COMPLETED",
                payload={"command": text, "route": route, "meta_response": response},
            )
            return result

        action_id = str((selected.get("provenance") or {}).get("action_id") or "")
        if not action_id:
            result = {
                **route,
                "ok": False,
                "status": "DENIED",
                "reason": "selected_transition_has_no_action_binding",
                "message": "The selected transition has no grounded action binding.",
                "fail_closed": True,
                "workflow": self._workflow_snapshot(),
            }
            result["experience_recording"] = self._record_experience(
                started_at=started,
                state_before=state_before,
                state_after=state_before,
                selected_transition=str(selected.get("transition_id") or ""),
                final_outcome="DENIED",
                payload={"command": text, "route": route, "failure": "selected_transition_has_no_action_binding"},
            )
            return result

        result = self.workflow.execute(action_id, execution_payload)
        state_after = self._workflow_state()
        final_outcome = "COMPLETED" if result.get("ok") else "DENIED"
        recording = self._record_experience(
            started_at=started,
            state_before=state_before,
            state_after=state_after,
            selected_transition=str(selected.get("transition_id") or ""),
            final_outcome=final_outcome,
            payload={
                "command": text,
                "normalized_route_input": route_input,
                "route": route,
                "action_id": action_id,
                "action_result": _bounded_result(result),
            },
        )
        return {
            **result,
            "route_decision": route,
            "experience_recording": recording,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def close(self) -> None:
        if self._ledger is not None:
            self._ledger.close()
            self._ledger = None

    def _ready(self) -> bool:
        return bool(self.initialization.get("human", {}).get("ok") and self.initialization.get("meta", {}).get("ok"))

    def _workflow_state(self) -> str:
        current_phase = getattr(self.workflow, "current_phase", None)
        if callable(current_phase):
            return str(current_phase() or "FRAME")
        state = self.workflow.get_state()
        return str(state.get("current_phase") or "FRAME")

    def _workflow_snapshot(self) -> dict[str, Any]:
        snapshot = getattr(self.workflow, "get_state_without_routing", None)
        if callable(snapshot):
            return dict(snapshot())
        return dict(self.workflow.get_state())

    def _context(self) -> dict[str, Any]:
        return {
            "objective": str(getattr(self.workflow, "objective", "") or ""),
            "lifecycle_allowed": True,
            "lease_capabilities": [],
            "repository_commit": _git_value(self.repo_root, ["rev-parse", "HEAD"]),
            "working_tree_digest": _working_tree_digest(self.repo_root),
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

    def _record_experience(
        self,
        *,
        started_at: float,
        state_before: str,
        state_after: str,
        selected_transition: str,
        final_outcome: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        ledger = self._ledger_instance()
        if ledger is None:
            return {"ok": False, "reason": self._ledger_error or "experience_ledger_unavailable", "persistent": False}
        evidence = dict(getattr(self.workflow, "evidence", {}) or {})
        try:
            experience = build_arena_experience(
                arena_id="human_agent",
                arena_version="AURA_HUMAN_AGENT_WORKFLOW_V1",
                grammar_version="human-agent-wfst-v1",
                runtime_version=ARENA_WFST_RUNTIME_VERSION,
                compiler_version=ARENA_WFST_COMPILER_VERSION,
                state_before=state_before,
                state_after=state_after,
                selected_transition=selected_transition,
                final_outcome=final_outcome,
                payload={"evidence_keys": sorted(evidence), **payload},
                task_id=str(getattr(self.workflow, "workflow_id", "") or ""),
                workflow_id=str(getattr(self.workflow, "workflow_id", "") or ""),
                started_at=started_at,
                completed_at=time.time(),
                repository_commit_sha=_git_value(self.repo_root, ["rev-parse", "HEAD"]),
                working_tree_digest=_working_tree_digest(self.repo_root),
                objective=str(getattr(self.workflow, "objective", "") or ""),
                source_hashes=_source_hashes_from_evidence(evidence),
            )
            result = ledger.record(experience)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": f"experience_record_failed:{type(exc).__name__}", "persistent": False}
        return {**result, "persistent": bool(result.get("ok"))}

    @staticmethod
    def _meta_response(selected: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
        transition_id = str(selected.get("transition_id") or "")
        if transition_id == "META.WHY_BLOCKED":
            return {"kind": "why_blocked", "blocked": route.get("blocked", [])}
        if transition_id == "META.SHOW_EVIDENCE":
            return {"kind": "show_evidence", "state_packet": route.get("state_packet", {})}
        if transition_id == "META.WHAT_NEXT":
            return {"kind": "what_next", "recommended": [item for item in route.get("recommended", []) if not item.get("meta_transition")]}
        return {
            "kind": transition_id.casefold().replace(".", "_"),
            "state": route.get("state"),
            "recommended": route.get("recommended", []),
            "blocked": route.get("blocked", []),
        }

    def _initialization_denial(self, state: str) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "DENIED",
            "reason": "human_agent_wfst_initialization_failed",
            "message": "The Human Agent grammar did not initialize; routing failed closed.",
            "state": state,
            "initialization": self.initialization,
            "fail_closed": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def _blocked_message(route: dict[str, Any]) -> str:
    blocked = list(route.get("blocked") or [])
    if not blocked:
        return "No safe state-local transition matched. Clarification is required."
    missing = sorted({item for row in blocked for item in row.get("missing_evidence", [])})
    return "Transition blocked by hard guards." + (f" Missing: {', '.join(missing)}." if missing else "")


def _bounded_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "status": result.get("status"),
        "action_id": result.get("action_id"),
        "message": str(result.get("message") or "")[:1000],
        "missing_evidence": list(result.get("missing_evidence") or []),
        "produced_evidence_keys": sorted((result.get("produced_evidence") or {}).keys()),
    }


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
