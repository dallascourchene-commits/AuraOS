"""Controlled Surgeon session using a preselected Aura Architect plan.

This adapter lets native Aura and third-party Arena clients execute the same
prepared plan through the existing persistent slice-session machinery. The
human-selected control profile bounds Council replans, Surgeon turns, repair
attempts, context, output, and local evidence recording.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Mapping

from aura_architect_control import ArchitectControlProfile, normalize_control_profile
from aura_external_llm_session_safe import AuraExternalLLMSessionManager
from aura_refactor_output_vault import RefactorOutputVault
from aura_event_contracts import stable_digest

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
        self._bilateral_bindings: dict[str, dict[str, Any]] = {}

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
        bilateral = dict(prepared.get("bilateral_contract") or {})
        bilateral_gate = dict(prepared.get("bilateral_plan_gate") or {})
        temporary_agent_identity = (
            f"external_llm:{str(provider or 'external')}:{str(model or '')}"
        ).rstrip(":")
        if bilateral:
            if bilateral_gate.get("passed") is not True:
                return {
                    "ok": False,
                    "error": "bilateral_plan_gate_not_passed",
                    "session_created": False,
                    "failure_classes": list(
                        bilateral_gate.get("failure_classes") or ()
                    ),
                    "production_mutation": False,
                }
            if time.time() >= float(bilateral.get("expires_at") or 0.0):
                return {
                    "ok": False,
                    "error": "bilateral_confirmation_expired",
                    "session_created": False,
                    "production_mutation": False,
                }
            phase_hash = str(prepared.get("plan_phase_hash") or "")
            retained = getattr(self.bridge, "_sessions", {}).get(phase_hash)
            retained_arena = retained.get("arena") if isinstance(retained, dict) else None
            if retained_arena is not None:
                retained_arena.bilateral_proof_plan[
                    "temporary_agent_identity"
                ] = temporary_agent_identity

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
        if bilateral:
            binding = {
                "temporary_agent_identity": temporary_agent_identity,
                "session_id": session_id,
                "confirmation_digest": bilateral.get("confirmation_digest"),
                "contract_digest": bilateral.get("contract_digest"),
                "guardrail_set_digest": bilateral.get("guardrail_set_digest"),
                "hard_guardrail_ids": list(
                    bilateral.get("hard_guardrail_ids") or ()
                ),
                "human_guardrail_ids": list(
                    bilateral.get("human_guardrail_ids") or ()
                ),
                "allowed_effects": list(bilateral.get("allowed_effects") or ()),
                "prohibited_effects": list(
                    bilateral.get("prohibited_effects") or ()
                ),
                "allowed_path_set_digest": bilateral.get(
                    "allowed_path_set_digest"
                ),
                "repair_budget": self.control.surgeon_max_local_repairs,
                "plan_revision": dict(
                    prepared.get("bilateral_proof_plan") or {}
                ).get("plan_revision"),
                "intent_revision_id": bilateral.get("intent_revision_id"),
                "expires_at": bilateral.get("expires_at"),
                "lease_status": "ACTIVE",
            }
            binding["binding_digest"] = stable_digest(binding)
            self._bilateral_bindings[session_id] = binding
            result["bilateral_session_binding"] = dict(binding)
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
            "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
        }
        return result

    def next_turn(self, session_id: str) -> dict[str, Any]:
        bilateral = self._bilateral_bindings.get(str(session_id))
        if bilateral and time.time() >= float(bilateral.get("expires_at") or 0.0):
            bilateral["lease_status"] = "EXPIRED"
            session = self._sessions.get(str(session_id))
            if session is not None:
                return self._block_replan(
                    session,
                    status="BLOCKED_CONFIRMATION_EXPIRED",
                    error="bilateral_confirmation_expired",
                )
            return {
                "ok": False,
                "status": "BLOCKED_CONFIRMATION_EXPIRED",
                "error": "bilateral_confirmation_expired",
                "session": None,
                "turn": None,
                "production_mutation": False,
                "control_profile": self.control.to_dict(),
            }
        return super().next_turn(session_id)

    def submit_response(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        bilateral = self._bilateral_bindings.get(str(session_id))
        if bilateral and time.time() >= float(bilateral.get("expires_at") or 0.0):
            bilateral["lease_status"] = "EXPIRED"
            session = self._sessions.get(str(session_id))
            if session is not None:
                return self._block_replan(
                    session,
                    status="BLOCKED_CONFIRMATION_EXPIRED",
                    error="bilateral_confirmation_expired",
                )
            return {
                "ok": False,
                "status": "BLOCKED_CONFIRMATION_EXPIRED",
                "error": "bilateral_confirmation_expired",
                "session": None,
                "turn": None,
                "production_mutation": False,
                "control_profile": self.control.to_dict(),
            }
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
                "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
            }
        result["control_profile"] = self.control.to_dict()
        return result

    def _block_replan(
        self,
        session: Any,
        *,
        status: str,
        error: str,
    ) -> dict[str, Any]:
        session.status = status
        session.pending_turn = None
        result = {
            "ok": False,
            "status": status,
            "error": error,
            "session": session.public_state(),
            "turn": None,
            "production_mutation": False,
            "control_profile": self.control.to_dict(),
        }
        if hasattr(self, "_finalize"):
            result["experience"] = self._finalize(session)
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
        session = self._sessions.get(session_id)
        if session is None:
            return {
                "ok": False,
                "error": "session_not_found",
                "control_profile": self.control.to_dict(),
                "production_mutation": False,
            }
        bilateral = self._bilateral_bindings.get(session_id)
        if bilateral:
            delta = kwargs.get("plan_revision")
            if not isinstance(delta, Mapping):
                return self._block_replan(
                    session,
                    status="BLOCKED_HUMAN_RECONFIRMATION_REQUIRED",
                    error="bilateral_replan_requires_explicit_revision_delta",
                )
            changed_fields = [
                field
                for field in (
                    "meaning_changed",
                    "scope_changed",
                    "authority_changed",
                    "guardrails_changed",
                    "new_owner_or_dependency",
                )
                if bool(delta.get(field))
            ]
            proposed_remaining = [
                dict(item)
                for item in list(kwargs.get("remaining_act_capsules") or ())
                if isinstance(item, Mapping)
            ]
            frozen_remaining = [
                dict(item)
                for item in session.act_capsules[session.active_task_index :]
            ]
            actual_plan_changed = stable_digest(proposed_remaining) != stable_digest(
                frozen_remaining
            )
            identity_changed = any(
                str(delta.get(field) or "") != str(expected or "")
                for field, expected in (
                    ("confirmation_digest", bilateral.get("confirmation_digest")),
                    ("intent_revision_id", bilateral.get("intent_revision_id")),
                    (
                        "allowed_path_set_digest",
                        bilateral.get("allowed_path_set_digest"),
                    ),
                    ("guardrail_set_digest", bilateral.get("guardrail_set_digest")),
                )
            )
            if changed_fields or identity_changed or actual_plan_changed:
                bilateral["lease_status"] = "RECONFIRMATION_REQUIRED"
                return self._block_replan(
                    session,
                    status="BLOCKED_HUMAN_RECONFIRMATION_REQUIRED",
                    error=(
                        "council_replan_changes_confirmed_bilateral_contract:"
                        + ",".join(
                            changed_fields
                            or (["identity"] if identity_changed else ["frozen_plan"])
                        )
                    ),
                )
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
        if len(session.turns) >= session.max_turns:
            return self._block_replan(
                session,
                status="BLOCKED_MAX_TURNS",
                error="max_turns_exceeded_before_council_replan",
            )

        task_id = str((session.active_task or {}).get("task_id") or "")
        prompt = str(kwargs.get("prompt") or "")
        response = str(kwargs.get("response") or "")
        provider_usage = dict(kwargs.get("provider_usage") or {})
        forwarded_kwargs = dict(kwargs)
        forwarded_kwargs.pop("plan_revision", None)
        result = super().apply_council_replan(**forwarded_kwargs)
        if result.get("status") == "WAITING_FOR_MODEL" and not result.get("turn"):
            result = self._block_replan(
                session,
                status="BLOCKED_REPLAN_TURN_UNAVAILABLE",
                error="unable_to_build_replanned_turn",
            )

        result["control_profile"] = self.control.to_dict()
        result["council_budget"] = {
            "used_replans": int(self._council_replans.get(session_id, 0)),
            "maximum_replans": self.control.council_call_budget,
        }
        if self.control.record_outputs:
            run_id = self._vault_runs.get(session_id, session_id)
            replan_number = int(self._council_replans.get(session_id, used))
            vault_record = self.output_vault.record_generated_output(
                run_id=run_id,
                turn_id=f"COUNCIL-REPLAN-{max(1, replan_number)}",
                task_id=task_id,
                role="council_replan",
                prompt=prompt,
                response=response,
                result=result,
                provider_usage=provider_usage,
            )
            result["local_output_record"] = {
                "run_id": run_id,
                "response_digest": vault_record.get("response_digest"),
                "evidence_digest": vault_record.get("evidence_digest"),
                "artifacts": vault_record.get("artifacts", {}),
                "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
            }
        return result


__all__ = ["CONTROLLED_SESSION_VERSION", "ControlledRefactorSessionManager"]
