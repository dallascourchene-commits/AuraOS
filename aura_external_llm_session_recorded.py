"""Chronicle-enabled external-LLM refactor sessions.

The base manager retains patch, staging, and verification authority. This adapter
adds immutable history, a compact state ledger, cognitive-labor routing, local
repair budgets, and an explicit Council-replan continuation point.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any

from aura_architect_council_v2 import profile_refactor_length
from aura_cognitive_labor_router import route_failure, route_initial_refactor
from aura_external_llm_session import (
    AuraExternalLLMSessionManager as _BaseManager,
    ExternalLLMSession,
    ExternalLLMTurn,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)
from aura_refactor_chronicle import RefactorChronicle
from aura_refactor_state_ledger import (
    bounded_state_ledger_text,
    build_state_ledger,
    measure_state_preservation,
)

_TERMINAL = {
    "READY_FOR_HUMAN_REVIEW",
    "BLOCKED",
    "BLOCKED_MAX_TURNS",
    "BLOCKED_REPAIR_UNAVAILABLE",
    "BLOCKED_UNKNOWN_ROLE",
}


def _tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return (len(text.encode("utf-8")) + 3) // 4


def _digest(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=12).hexdigest()


def _usage(value: dict[str, Any]) -> tuple[int | None, int | None, float | None]:
    def integer(raw: Any) -> int | None:
        try:
            return None if raw is None else max(0, int(raw))
        except (TypeError, ValueError):
            return None

    def number(raw: Any) -> float | None:
        try:
            return None if raw is None else max(0.0, float(raw))
        except (TypeError, ValueError):
            return None

    return (
        integer(value.get("input_tokens", value.get("prompt_tokens"))),
        integer(value.get("output_tokens", value.get("completion_tokens"))),
        number(value.get("cost_usd", value.get("reported_cost_usd"))),
    )


def _prompt(turn: ExternalLLMTurn) -> str:
    return json.dumps(
        {
            "instruction": turn.instruction,
            "objective": turn.objective,
            "role": turn.role,
            "gate": turn.gate,
            "output_contract": turn.output_contract,
            "act_capsule": turn.act_capsule,
            "compressed_context": turn.compressed_context,
            "source_slices": turn.source_slices,
            "test_slices": turn.test_slices,
            "failure_packet": turn.failure_packet,
            "allowed_files": turn.allowed_files,
            "do_not_touch": turn.do_not_touch,
        },
        sort_keys=True,
        default=str,
    )


class RecordedAuraExternalLLMSessionManager(_BaseManager):
    """Record each issued turn, response, repair, replan, and terminal outcome."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        bridge: Any | None = None,
        *,
        chronicle_path: str | Path | None = None,
        experience_db_path: str | Path | None = None,
        max_local_repairs: int = 2,
    ) -> None:
        super().__init__(repo_root=repo_root, bridge=bridge)
        self.chronicle = RefactorChronicle(
            self.repo_root,
            path=chronicle_path,
            experience_db_path=experience_db_path,
        )
        self.max_local_repairs = max(0, int(max_local_repairs))
        self._finalized: set[str] = set()
        self._repair_attempts: dict[str, dict[str, int]] = {}
        self._council_replans: dict[str, int] = {}
        self._state_metrics: dict[str, list[dict[str, Any]]] = {}

    def open_session(self, **kwargs: Any) -> dict[str, Any]:
        result = super().open_session(**kwargs)
        if not result.get("session_created"):
            return result
        session_id = str(dict(result.get("session") or {}).get("session_id") or "")
        session = self._sessions[session_id]
        self._repair_attempts[session_id] = {}
        self._council_replans[session_id] = 0
        self._state_metrics[session_id] = []
        profile = profile_refactor_length({"act_tasks": session.act_capsules})
        initial_route = route_initial_refactor(
            objective=session.objective,
            task_count=profile.task_count,
            distinct_file_count=profile.distinct_file_count,
            dependency_edge_count=profile.dependency_edge_count,
            sequential_depth=profile.sequential_depth_estimate,
            large_task_count=profile.large_task_count,
        )
        self.chronicle.record(
            "refactor_session_opened",
            correlation_id=self._correlation(session_id),
            session_id=session_id,
            objective=session.objective,
            plan_phase_hash=session.plan_phase_hash,
            gate="PLAN",
            status=session.status,
            provider=session.provider,
            model=session.model,
            payload={
                "task_count": len(session.act_capsules),
                "max_context_tokens": session.max_context_tokens,
                "max_output_tokens": session.max_output_tokens,
                "max_turns": session.max_turns,
                "prepared_digest": _digest(result.get("prepared") or {}),
                "length_profile": profile.to_dict(),
                "cognitive_labor_route": initial_route.to_dict(),
            },
        )
        if session.pending_turn is not None:
            session.pending_turn = self._attach_state_ledger(session, session.pending_turn)
            self._record_issued(session, session.pending_turn)
            result["turn"] = session.pending_turn.to_dict()
            result["session"] = session.public_state()
        result["chronicle"] = self._summary(session)
        result["cognitive_labor_route"] = initial_route.to_dict()
        return result

    def submit_response(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        before = self._sessions.get(str(session_id))
        turn = before.pending_turn if before is not None else None
        prompt = _prompt(turn) if turn is not None else ""
        usage = dict(provider_usage or {})
        reported_in, reported_out, reported_cost = _usage(usage)
        result = super().submit_response(
            session_id=session_id,
            turn_id=turn_id,
            response=response,
            provider_usage=usage,
        )
        session = self._sessions.get(str(session_id))
        if session is None:
            return result
        stage = dict(result.get("stage_result") or {})
        verification = dict(result.get("verification") or {})
        role = turn.role if turn is not None else ""
        self.chronicle.record(
            "refactor_repair_completed" if role == "repair" else "refactor_worker_completed",
            correlation_id=self._correlation(session.session_id),
            session_id=session.session_id,
            objective=session.objective,
            plan_phase_hash=session.plan_phase_hash,
            task_id=turn.task_id if turn is not None else "",
            gate="REPAIR" if role == "repair" else "ACT",
            status=str(result.get("status") or session.status),
            provider=session.provider,
            model=session.model,
            input_tokens_estimated=_tokens(prompt),
            output_tokens_estimated=_tokens(response),
            input_tokens_reported=reported_in,
            output_tokens_reported=reported_out,
            cost_usd_reported=reported_cost,
            prompt=prompt,
            response=response,
            payload={
                "turn_id": turn_id,
                "turn_index": turn.turn_index if turn is not None else None,
                "provider_usage": usage,
                "stage_ok": stage.get("ok"),
                "stage_digest": _digest(stage) if stage else "",
                "verification_ok": verification.get("ok"),
                "hotswap_ready": verification.get("hotswap_ready"),
                "verification_digest": _digest(verification) if verification else "",
            },
        )
        if session.pending_turn is not None:
            session.pending_turn = self._attach_state_ledger(session, session.pending_turn)
            self._record_issued(session, session.pending_turn)
            result["next_turn"] = session.pending_turn.to_dict()
            result["session"] = session.public_state()
        if session.status in _TERMINAL:
            result["experience"] = self._finalize(session)
        result["chronicle"] = self._summary(session)
        result["state_metrics"] = list(self._state_metrics.get(session.session_id, []))
        return result

    def get_session(self, session_id: str) -> dict[str, Any]:
        result = super().get_session(session_id)
        session = self._sessions.get(str(session_id))
        if session is not None:
            result["chronicle"] = self._summary(session)
            result["state_metrics"] = list(self._state_metrics.get(session.session_id, []))
            result["council_replan_count"] = self._council_replans.get(session.session_id, 0)
        return result

    def _queue_repair(
        self,
        session: ExternalLLMSession,
        *,
        failure_packet: dict[str, Any],
        stage_result: dict[str, Any] | None = None,
        verification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task = session.active_task or {}
        task_id = str(task.get("task_id") or "")
        attempts = self._repair_attempts.setdefault(session.session_id, {})
        attempts[task_id] = attempts.get(task_id, 0) + 1
        meta = dict(failure_packet.get("failure_scope") or {})
        decision = route_failure(
            failure_packet=failure_packet,
            local_repair_attempts=attempts[task_id] - 1,
            affected_task_count=int(meta.get("affected_task_count", 1)),
            affected_file_count=int(meta.get("affected_file_count", 1)),
            downstream_tasks_invalidated=int(meta.get("downstream_tasks_invalidated", 0)),
            invariant_breach=bool(meta.get("invariant_breach", False)),
            interface_contract_breach=bool(meta.get("interface_contract_breach", False)),
            dependency_graph_breach=bool(meta.get("dependency_graph_breach", False)),
            max_local_repairs=self.max_local_repairs,
        )
        self.chronicle.record(
            "refactor_failure_routed",
            correlation_id=self._correlation(session.session_id),
            session_id=session.session_id,
            objective=session.objective,
            plan_phase_hash=session.plan_phase_hash,
            task_id=task_id,
            gate="REPAIR_OR_REPLAN",
            status=decision.route,
            provider=session.provider,
            model=session.model,
            payload={
                "decision": decision.to_dict(),
                "failure_digest": _digest(failure_packet),
                "local_repair_attempt": attempts[task_id],
            },
        )
        if decision.escalation_required:
            session.status = "WAITING_FOR_COUNCIL_REPLAN"
            session.pending_turn = None
            session.updated_at = time.time()
            return {
                "ok": False,
                "status": session.status,
                "session": session.public_state(),
                "stage_result": stage_result or (session.stage_results[-1] if session.stage_results else {}),
                "verification": verification or {},
                "next_turn": None,
                "cognitive_labor_decision": decision.to_dict(),
                "council_replan_required": True,
                "failure_packet": failure_packet,
            }
        result = super()._queue_repair(
            session,
            failure_packet=failure_packet,
            stage_result=stage_result,
            verification=verification,
        )
        result["cognitive_labor_decision"] = decision.to_dict()
        result["council_replan_required"] = False
        return result

    def apply_council_replan(
        self,
        *,
        session_id: str,
        remaining_act_capsules: list[dict[str, Any]],
        rationale: str,
        prompt: str = "",
        response: str = "",
        provider_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self._sessions.get(str(session_id))
        if session is None:
            return self._error("session_not_found")
        if session.status != "WAITING_FOR_COUNCIL_REPLAN":
            return self._error("council_replan_not_requested", session=session)
        completed = list(session.act_capsules[: session.active_task_index])
        remaining = [dict(item) for item in remaining_act_capsules if isinstance(item, dict)]
        if not remaining:
            return self._error("replan_has_no_remaining_act_capsules", session=session)
        usage = dict(provider_usage or {})
        reported_in, reported_out, reported_cost = _usage(usage)
        session.act_capsules = completed + remaining
        self._council_replans[session.session_id] = self._council_replans.get(session.session_id, 0) + 1
        session.plan_phase_hash = f"{session.plan_phase_hash}-R{self._council_replans[session.session_id]}-{_digest(remaining)[:8]}"
        session.status = "WAITING_FOR_MODEL"
        session.pending_turn = super()._build_turn(session, role="worker", failure_packet={})
        if session.pending_turn is not None:
            session.pending_turn = self._attach_state_ledger(session, session.pending_turn)
        session.updated_at = time.time()
        self.chronicle.record(
            "refactor_council_replan_applied",
            correlation_id=self._correlation(session.session_id),
            session_id=session.session_id,
            objective=session.objective,
            plan_phase_hash=session.plan_phase_hash,
            task_id=str(session.active_task.get("task_id") if session.active_task else ""),
            gate="REPLAN",
            status=session.status,
            provider=session.provider,
            model=session.model,
            input_tokens_estimated=_tokens(prompt),
            output_tokens_estimated=_tokens(response),
            input_tokens_reported=reported_in,
            output_tokens_reported=reported_out,
            cost_usd_reported=reported_cost,
            prompt=prompt,
            response=response,
            payload={
                "rationale": rationale,
                "remaining_task_count": len(remaining),
                "council_replan_count": self._council_replans[session.session_id],
                "provider_usage": usage,
            },
        )
        if session.pending_turn is not None:
            self._record_issued(session, session.pending_turn)
        return {
            "ok": session.pending_turn is not None,
            "status": session.status,
            "session": session.public_state(),
            "turn": session.pending_turn.to_dict() if session.pending_turn else None,
            "council_replan_count": self._council_replans[session.session_id],
            "production_mutation": False,
        }

    def _attach_state_ledger(
        self,
        session: ExternalLLMSession,
        turn: ExternalLLMTurn,
    ) -> ExternalLLMTurn:
        ledger = build_state_ledger(
            session,
            repair_attempts_by_task=self._repair_attempts.get(session.session_id, {}),
            council_replan_count=self._council_replans.get(session.session_id, 0),
        )
        metrics = measure_state_preservation(session, ledger)
        metrics.update({"turn_id": turn.turn_id, "task_id": turn.task_id, "turn_index": turn.turn_index})
        self._state_metrics.setdefault(session.session_id, []).append(metrics)
        ledger_text = bounded_state_ledger_text(
            ledger,
            max_tokens=min(480, max(128, session.max_context_tokens // 4)),
        )
        prefix = str(turn.compressed_context or "").strip()
        turn.compressed_context = f"{prefix}\nSTATE_LEDGER:\n{ledger_text}".strip()
        payload = {
            "compressed_context": turn.compressed_context,
            "source_slices": turn.source_slices,
            "test_slices": turn.test_slices,
            "failure_packet": turn.failure_packet,
            "act_capsule": turn.act_capsule,
        }
        while _tokens(payload) > session.max_context_tokens and turn.test_slices:
            turn.test_slices.pop()
            payload["test_slices"] = turn.test_slices
        while _tokens(payload) > session.max_context_tokens and len(turn.source_slices) > 1:
            turn.source_slices.pop()
            payload["source_slices"] = turn.source_slices
        if _tokens(payload) > session.max_context_tokens:
            allowed_chars = max(128, session.max_context_tokens * 4 // 3)
            turn.compressed_context = turn.compressed_context[-allowed_chars:]
            payload["compressed_context"] = turn.compressed_context
        turn.context_token_estimate = _tokens(payload)
        return turn

    def _record_issued(self, session: ExternalLLMSession, turn: ExternalLLMTurn) -> None:
        prompt = _prompt(turn)
        metrics = self._state_metrics.get(session.session_id, [])
        latest_metrics = metrics[-1] if metrics else {}
        self.chronicle.record(
            "refactor_model_turn_issued",
            correlation_id=self._correlation(session.session_id),
            session_id=session.session_id,
            objective=session.objective,
            plan_phase_hash=session.plan_phase_hash,
            task_id=turn.task_id,
            gate=turn.gate,
            status=session.status,
            provider=session.provider,
            model=session.model,
            input_tokens_estimated=0,
            prompt=prompt,
            payload={
                "turn_id": turn.turn_id,
                "role": turn.role,
                "turn_index": turn.turn_index,
                "prompt_tokens_estimated": _tokens(prompt),
                "declared_context_tokens": turn.context_token_estimate,
                "max_output_tokens": turn.max_output_tokens,
                "source_slice_count": len(turn.source_slices),
                "test_slice_count": len(turn.test_slices),
                "state_metrics": latest_metrics,
            },
        )

    def _finalize(self, session: ExternalLLMSession) -> dict[str, Any]:
        if session.session_id in self._finalized:
            return {"ok": True, "idempotent_replay": True, "chronicle": self._summary(session)}
        status = session.status
        summary = self._summary(session)
        metrics = self._state_metrics.get(session.session_id, [])
        notes = [
            f"terminal_status={status}",
            f"task_count={len(session.act_capsules)}",
            f"turn_count={len(session.turns)}",
            f"repair_event_count={summary.get('repair_event_count', 0)}",
            f"council_replan_count={self._council_replans.get(session.session_id, 0)}",
            f"minimum_state_preservation={min((item.get('state_preservation_score', 1.0) for item in metrics), default=1.0)}",
        ]
        self.chronicle.record(
            "refactor_session_terminal",
            correlation_id=self._correlation(session.session_id),
            session_id=session.session_id,
            objective=session.objective,
            plan_phase_hash=session.plan_phase_hash,
            gate="DECIDE",
            status=status,
            provider=session.provider,
            model=session.model,
            payload={"learning_notes": notes, "state_metrics": metrics, "production_mutation": False},
        )
        result = self.chronicle.finalize_experience(
            correlation_id=self._correlation(session.session_id),
            session_id=session.session_id,
            objective=session.objective,
            plan_phase_hash=session.plan_phase_hash,
            final_outcome=status,
            state_before="OPEN",
            state_after=status,
            selected_transition="human_review" if status == "READY_FOR_HUMAN_REVIEW" else "blocked",
            provider=session.provider,
            model=session.model,
            raw_evidence_refs=[str(self.chronicle.path)],
            learning_notes=notes,
        )
        self._finalized.add(session.session_id)
        return result

    def _summary(self, session: ExternalLLMSession) -> dict[str, Any]:
        return self.chronicle.summary(
            correlation_id=self._correlation(session.session_id),
            session_id=session.session_id,
        )

    @staticmethod
    def _correlation(session_id: str) -> str:
        return f"REF-{session_id}"


__all__ = ["RecordedAuraExternalLLMSessionManager", "PATCH_AUTHORITY", "VSA_PATCH_AUTHORITY"]
