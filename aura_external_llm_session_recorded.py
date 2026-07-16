"""Chronicle-enabled external-LLM refactor sessions.

The orchestration and authority model remain in ``aura_external_llm_session``.
This adapter only adds append-only events and an ArenaExperience projection.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from aura_external_llm_session import (
    AuraExternalLLMSessionManager as _BaseManager,
    ExternalLLMSession,
    ExternalLLMTurn,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)
from aura_refactor_chronicle import RefactorChronicle

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
    def as_int(raw: Any) -> int | None:
        try:
            return None if raw is None else max(0, int(raw))
        except (TypeError, ValueError):
            return None

    def as_float(raw: Any) -> float | None:
        try:
            return None if raw is None else max(0.0, float(raw))
        except (TypeError, ValueError):
            return None

    return (
        as_int(value.get("input_tokens", value.get("prompt_tokens"))),
        as_int(value.get("output_tokens", value.get("completion_tokens"))),
        as_float(value.get("cost_usd", value.get("reported_cost_usd"))),
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
    """Record every issued turn, response, repair, and terminal outcome."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        bridge: Any | None = None,
        *,
        chronicle_path: str | Path | None = None,
        experience_db_path: str | Path | None = None,
    ) -> None:
        super().__init__(repo_root=repo_root, bridge=bridge)
        self.chronicle = RefactorChronicle(
            self.repo_root,
            path=chronicle_path,
            experience_db_path=experience_db_path,
        )
        self._finalized: set[str] = set()

    def open_session(self, **kwargs: Any) -> dict[str, Any]:
        result = super().open_session(**kwargs)
        if not result.get("session_created"):
            return result
        state = dict(result.get("session") or {})
        session_id = str(state.get("session_id") or "")
        session = self._sessions[session_id]
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
            },
        )
        if session.pending_turn is not None:
            self._record_issued(session, session.pending_turn)
        result["chronicle"] = self._summary(session)
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
            self._record_issued(session, session.pending_turn)
        if session.status in _TERMINAL:
            result["experience"] = self._finalize(session)
        result["chronicle"] = self._summary(session)
        return result

    def get_session(self, session_id: str) -> dict[str, Any]:
        result = super().get_session(session_id)
        session = self._sessions.get(str(session_id))
        if session is not None:
            result["chronicle"] = self._summary(session)
        return result

    def _record_issued(self, session: ExternalLLMSession, turn: ExternalLLMTurn) -> None:
        prompt = _prompt(turn)
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
            input_tokens_estimated=_tokens(prompt),
            prompt=prompt,
            payload={
                "turn_id": turn.turn_id,
                "role": turn.role,
                "turn_index": turn.turn_index,
                "declared_context_tokens": turn.context_token_estimate,
                "max_output_tokens": turn.max_output_tokens,
                "source_slice_count": len(turn.source_slices),
                "test_slice_count": len(turn.test_slices),
            },
        )

    def _finalize(self, session: ExternalLLMSession) -> dict[str, Any]:
        if session.session_id in self._finalized:
            return {"ok": True, "idempotent_replay": True, "chronicle": self._summary(session)}
        status = session.status
        notes = [
            f"terminal_status={status}",
            f"task_count={len(session.act_capsules)}",
            f"turn_count={len(session.turns)}",
            f"repair_event_count={self._summary(session).get('repair_event_count', 0)}",
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
            payload={"learning_notes": notes, "production_mutation": False},
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


__all__ = [
    "RecordedAuraExternalLLMSessionManager",
    "PATCH_AUTHORITY",
    "VSA_PATCH_AUTHORITY",
]
