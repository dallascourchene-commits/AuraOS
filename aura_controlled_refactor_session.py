"""Controlled Surgeon session using a preselected Aura Architect plan.

This adapter lets native Aura and third-party Arena clients execute the same
prepared plan through the existing persistent slice-session machinery.  The
human-selected control profile bounds Council replans, Surgeon turns, repair
attempts, context, output, and local evidence recording.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from aura_architect_control import ArchitectControlProfile, normalize_control_profile
from aura_external_llm_session_safe import AuraExternalLLMSessionManager
from aura_refactor_output_vault import RefactorOutputVault

CONTROLLED_SESSION_VERSION = "AURA_CONTROLLED_REFACTOR_SESSION_V1"


class _PreparedBridgeProxy:
    """Delegate every bridge call except the already-frozen preparation result."""

    def __init__(self, bridge: Any, prepared: Mapping[str, Any]) -> None:
        self._bridge = bridge
        self._prepared = dict(prepared)
        self.repo_root = getattr(bridge, "repo_root", ".")

    def aura_prepare_arena(self, **_kwargs: Any) -> dict[str, Any]:
        return dict(self._prepared)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bridge, name)


class ControlledRefactorSessionManager(AuraExternalLLMSessionManager):
    """Persistent slice-leased Surgeon controlled by one immutable profile."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        bridge: Any | None = None,
        *,
        control: Mapping[str, Any] | ArchitectControlProfile | None = None,
        surface: str = "native",
        output_vault: RefactorOutputVault | None = None,
    ) -> None:
        self.control = normalize_control_profile(control, surface=surface)
        super().__init__(
            repo_root=repo_root,
            bridge=bridge,
            max_local_repairs=self.control.surgeon_max_local_repairs,
        )
        self.output_vault = output_vault or RefactorOutputVault(
            self.repo_root, root=self.control.output_root
        )
        self._vault_runs: dict[str, str] = {}

    def open_prepared_session(
        self,
        *,
        prepared_arena: Mapping[str, Any],
        objective: str,
        provider: str = "external",
        model: str = "",
        run_id: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.control.surgeon_mode == "PLAN_ONLY":
            return {
                "ok": False,
                "error": "surgeon_disabled_by_control_profile",
                "control_profile": self.control.to_dict(),
                "production_mutation": False,
            }
        prepared = dict(prepared_arena)
        if not prepared.get("ok", True):
            return {**prepared, "session_created": False}
        if not list(prepared.get("act_capsules") or []):
            return {
                "ok": False,
                "error": "prepared_arena_has_no_act_capsules",
                "session_created": False,
                "control_profile": self.control.to_dict(),
            }

        original_bridge = self.bridge
        self.bridge = _PreparedBridgeProxy(original_bridge, prepared)
        try:
            result = super().open_session(
                objective=str(objective),
                target_file=None,
                target_symbol=None,
                acceptance_criteria=[],
                risk_map=[],
                constraints=[
                    "architect_plan_is_frozen_before_surgeon_execution",
                    f"council_mode={self.control.council_mode}",
                    f"council_call_budget={self.control.council_call_budget}",
                    f"surgeon_mode={self.control.surgeon_mode}",
                    "full_generated_outputs_recorded_locally",
                ],
                provider=str(provider or "external"),
                model=str(model or ""),
                max_context_tokens=self.control.surgeon_context_tokens,
                max_output_tokens=self.control.surgeon_output_tokens,
                max_turns=self.control.surgeon_max_turns,
            )
        finally:
            self.bridge = original_bridge

        if not result.get("session_created"):
            return result
        session = dict(result.get("session") or {})
        session_id = str(session.get("session_id") or "")
        parent_run = str(run_id or "").strip()
        vault_run = f"{parent_run}-surgeon" if parent_run else session_id
        self._vault_runs[session_id] = vault_run
        if self.control.record_outputs:
            self.output_vault.start_run(
                run_id=vault_run,
                objective=str(objective),
                surface=self.control.surface,
                control_profile=self.control.to_dict(),
                metadata={
                    "parent_architect_run_id": parent_run,
                    "session_id": session_id,
                    "provider": str(provider or "external"),
                    "model": str(model or ""),
                    "prepared_plan_phase_hash": prepared.get("plan_phase_hash", ""),
                    "controlled_session_version": CONTROLLED_SESSION_VERSION,
                    **dict(metadata or {}),
                },
            )
        result["control_profile"] = self.control.to_dict()
        result["output_vault"] = {
            "enabled": self.control.record_outputs,
            "run_id": vault_run,
            "parent_run_id": parent_run,
            "root": self.control.output_root,
            "visibility": "LOCAL_PRIVATE_FULL_OUTPUT",
        }
        return result

    def submit_response(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self._sessions.get(str(session_id))
        turn = session.pending_turn if session is not None else None
        prompt = json.dumps(turn.to_dict(), sort_keys=True, default=str) if turn is not None else ""
        task_id = turn.task_id if turn is not None else ""
        role = turn.role if turn is not None else ""
        result = super().submit_response(
            session_id=session_id,
            turn_id=turn_id,
            response=response,
            provider_usage=provider_usage,
        )
        if self.control.record_outputs and turn is not None:
            run_id = self._vault_runs.get(str(session_id), str(session_id))
            vault_record = self.output_vault.record_generated_output(
                run_id=run_id,
                turn_id=turn_id,
                task_id=task_id,
                role=role,
                prompt=prompt,
                response=str(response),
                result=result,
                provider_usage=provider_usage,
            )
            result["local_output_record"] = {
                "run_id": run_id,
                "turn_id": turn_id,
                "response_digest": vault_record.get("response_digest"),
                "evidence_digest": vault_record.get("evidence_digest"),
                "artifacts": vault_record.get("artifacts", {}),
                "visibility": "LOCAL_PRIVATE_FULL_OUTPUT",
            }
        result["control_profile"] = self.control.to_dict()
        return result

    def apply_council_replan(self, **kwargs: Any) -> dict[str, Any]:
        if self.control.council_mode == "OFF" or not self.control.council_replan_allowed:
            return {
                "ok": False,
                "error": "council_replan_disabled_by_control_profile",
                "control_profile": self.control.to_dict(),
                "production_mutation": False,
            }
        session_id = str(kwargs.get("session_id") or "")
        used = int(self._council_replans.get(session_id, 0))
        if used >= self.control.council_call_budget:
            return {
                "ok": False,
                "error": "council_call_budget_exhausted",
                "used": used,
                "budget": self.control.council_call_budget,
                "control_profile": self.control.to_dict(),
                "production_mutation": False,
            }
        result = super().apply_council_replan(**kwargs)
        result["control_profile"] = self.control.to_dict()
        result["council_budget"] = {
            "used_replans": int(self._council_replans.get(session_id, 0)),
            "maximum_replans": self.control.council_call_budget,
        }
        return result


__all__ = ["CONTROLLED_SESSION_VERSION", "ControlledRefactorSessionManager"]
