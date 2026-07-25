"""Topology-anchored, bilateral, approval-gated dialogue for Aura Arenas.

The service preserves the existing proposal-only Gate Dialogue API while adding
an opt-in multi-turn refinement mode used by the Showcase UI.  Deterministic
positive/negative requirements and guardrails are authoritative; an optional
model may only voice that bounded packet.  Human confirmation compiles the
existing canonical IntentPacket and SemanticLedger and grants no patch,
commit, push, merge, production, or learning-promotion authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from aura_bilateral_intent_compiler import (
    BilateralAnalysis,
    analyze_bilateral_request,
    apply_clarification,
    compile_confirmed_bilateral_intent,
    create_refinement_session,
    refresh_refinement_session,
)
from aura_event_contracts import stable_digest
from aura_human_agent_guidance import build_guidance_packet
from aura_llm_egress import ExternalLLM, available_providers
from aura_showcase_intent import compile_bulk_intent_trace
from aura_tokenizer_guard import sanitize_tokenizer_channels

GATE_DIALOGUE_VERSION = "AURA_ARENA_GATE_DIALOGUE_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MAX_COMMENT_CHARS = 6000
MAX_HISTORY = 80
MAX_PENDING = 20
SESSION_TTL_SECONDS = 3600.0
SLOT_KEYS = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")
BILATERAL_MARKER = "[AURA_BILATERAL_REFINE]"
_CLARIFICATION = re.compile(
    r"^\[AURA_CLARIFICATION_ANSWER:(GDP-[A-Za-z0-9]+)\]\s*(.+)$",
    flags=re.DOTALL,
)


def _digest(value: Any, *, size: int = 20) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _bounded_text(value: Any, limit: int = 800) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _bounded_list(value: Any, *, limit: int = 12) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[Any] = []
    for item in list(value)[:limit]:
        if isinstance(item, dict):
            result.append(
                {
                    str(key)[:80]: _bounded_text(val, 300)
                    for key, val in list(item.items())[:10]
                    if key
                    in {
                        "id",
                        "label",
                        "file_path",
                        "symbol",
                        "kind",
                        "relation",
                        "source",
                        "target",
                        "status",
                    }
                }
            )
        else:
            result.append(_bounded_text(item, 300))
    return result


def normalize_node_context(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only presenter-safe topology metadata; never transfer source contents."""
    source = dict(raw or {})
    selected = dict(source.get("selected_node") or source.get("node") or {})
    line_range = selected.get("line_range") or []
    if not isinstance(line_range, (list, tuple)):
        line_range = []
    node = {
        "id": _bounded_text(selected.get("id"), 240),
        "label": _bounded_text(selected.get("label"), 240),
        "file_path": _bounded_text(selected.get("file_path"), 500),
        "symbol": _bounded_text(selected.get("symbol"), 240),
        "node_type": _bounded_text(selected.get("node_type"), 80),
        "line_range": [
            int(item) for item in list(line_range)[:2] if isinstance(item, (int, float))
        ],
        "projection_truth": _bounded_text(selected.get("projection_truth"), 120),
        "patch_authority": False,
    }
    if not any(value for key, value in node.items() if key not in {"patch_authority", "line_range"}):
        node = {}
    return {
        "task_id": _bounded_text(source.get("task_id"), 160),
        "selected_node": node,
        "dependencies": _bounded_list(source.get("dependencies")),
        "callers": _bounded_list(source.get("callers")),
        "tests": _bounded_list(source.get("tests")),
        "relations": _bounded_list(source.get("relations"), limit=20),
        "candidate_faults": _bounded_list(source.get("candidate_faults"), limit=8),
        "full_topology_transferred": False,
        "visual_topology_patch_authority": False,
    }


def _phase_hash(state: dict[str, Any]) -> str:
    evidence = {
        str(key): value
        for key, value in dict(state.get("evidence") or {}).items()
        if key != "approved_gate_intents"
    }
    routed = dict(state.get("state_packet") or {})
    return _digest(
        {
  "workflow_id": state.get("workflow_id"),
  "phase": state.get("current_phase"),
  "objective": state.get("objective"),
  "evidence": evidence,
  "grammar_version": state.get("grammar_version"),
  "routed_state": routed.get("state") or routed.get("current_state") or "",
        }
    )


def _intent_summary(trace: dict[str, Any]) -> dict[str, Any]:
    packet = dict(trace.get("six_slot_packet") or {})
    slots = dict(packet.get("slots") or {})
    return {
        "ok": bool(trace.get("ok")),
        "model_calls_made": int(trace.get("model_calls_made") or 0),
        "compressed_objective": _bounded_text(trace.get("compressed_objective"), 1600),
        "slots": {key: _bounded_text(slots.get(key), 200) for key in SLOT_KEYS},
        "machine_route": {
            key: _bounded_text((trace.get("machine_route") or {}).get(key), 240)
            for key in ("rule_name", "route", "model", "context", "reason")
        },
    }


def _repository_identity(root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.stdout.strip()

    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    clean = not bool(status.strip())
    tree_digest = stable_digest({"head": head, "status": status.splitlines()})
    return {
        "repository_head": head,
        "source_tree_digest": tree_digest,
        "working_tree_clean": clean,
        "working_tree_clean_receipt": stable_digest(
            {"head": head, "clean": clean, "status": status.splitlines()}
        ),
    }


def _fallback_response(
    *,
    stage_hint: str,
    guide: dict[str, Any],
    node_context: dict[str, Any],
    intent_summary: dict[str, Any],
    analysis: BilateralAnalysis,
) -> str:
    gate = dict(guide.get("gate") or {})
    node = dict(node_context.get("selected_node") or {})
    anchor = node.get("label") or node.get("symbol") or node.get("file_path") or "the current gate"
    location = node.get("file_path") or "no exact file selected"
    if analysis.questions:
        question = analysis.questions[0]
        return (
            f"At {gate.get('title') or stage_hint or 'this gate'}, Aura anchored the request to "
            f"{anchor} ({location}) and preserved both positive and negative intent. "
            f"One execution-changing ambiguity remains: {question.question} "
            "No confirmation or guarded action is available until the human answers it."
        )
    recommended = list(guide.get("recommended_actions") or [])
    blocked = list(guide.get("blocked_actions") or [])
    if recommended:
        item = recommended[0]
        action = f"The safest currently admitted action is {item.get('label')}. {item.get('description')}"
    elif blocked:
        missing = ", ".join(blocked[0].get("missing_evidence") or []) or "declared gate evidence"
        action = f"No work action is admitted yet. The smallest visible gap is {missing}."
    else:
        action = "No state-local work action is currently admitted."
    slots = intent_summary.get("slots") or {}
    slot_text = " · ".join(f"{key}={slots.get(key) or '—'}" for key in SLOT_KEYS)
    return (
        f"At {gate.get('title') or stage_hint or 'this gate'}, Aura anchored the confirmed candidate "
        f"meaning to {anchor} ({location}). The local route is {slot_text}. {action} "
        "Review the paired teach-back and guardrails before confirming. Confirmation binds canonical "
        "intent references only; it grants no patch, commit, push, merge, production, or learning authority."
    )


def _model_prompt(packet: dict[str, Any]) -> str:
    return (
        "You are Aura's proposal-only voice inside the Human Agent Arena. Explain the supplied "
        "deterministic bilateral refinement packet using only its positive requirements, negative "
        "requirements, guardrails, current gate, admitted/blocked actions, selected topology metadata, "
        "and six-slot trace. Never add, remove, weaken, or reinterpret a requirement or guardrail. "
        "Never invent a file, action, test, source fact, authority, or approval. Treat the deterministic "
        "packet and recommended action as authoritative. Keep the response under 220 words.\n\n"
        "[AURA_BILATERAL_GATE_PACKET]\n"
        + json.dumps(packet, indent=2, ensure_ascii=False, default=str)
        + "\n[/AURA_BILATERAL_GATE_PACKET]"
    )


def _analysis_fields(analysis: BilateralAnalysis) -> dict[str, Any]:
    return {
        "positive_requirements": list(analysis.positive_requirements),
        "negative_requirements": [item.to_dict() for item in analysis.negative_requirements],
        "proposed_guardrails": [item.to_dict() for item in analysis.guardrails],
        "unresolved_ambiguities": [item.to_dict() for item in analysis.questions],
        "next_clarification_question": analysis.questions[0].to_dict() if analysis.questions else {},
        "paired_teach_back": analysis.teach_back.to_dict() if analysis.teach_back else {},
        "can_confirm_intent": not analysis.questions and analysis.teach_back is not None,
    }


def _allowed_paths(node_context: dict[str, Any], state: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    node_path = str((node_context.get("selected_node") or {}).get("file_path") or "").strip()
    if node_path:
        values.append(node_path)
    evidence = dict(state.get("evidence") or {})
    affected = evidence.get("affected_files") or []
    grounding = dict(evidence.get("grounding") or {})
    localized = grounding.get("localized_files") or []
    for item in [*affected, *localized]:
        text = str(item or "").strip().replace("\\", "/")
        if text and text not in values:
            values.append(text)
    return tuple(values)


class ArenaGateDialogueService:
    """Runtime-local bilateral proposal and confirmation ledger for one workflow."""

    def __init__(self, repo_root: str | Path, workflow: Any) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.workflow = workflow
        self.pending: dict[str, dict[str, Any]] = {}
        self.confirmed: dict[str, dict[str, Any]] = {}
        self.history: list[dict[str, Any]] = []
        self._runtime: dict[str, dict[str, Any]] = {}

    def address(
        self,
        *,
        comment: str,
        node_context: dict[str, Any] | None = None,
        stage_hint: str = "",
        prefer_model: bool = True,
    ) -> dict[str, Any]:
        raw_comment = str(comment or "").strip()
        if not raw_comment:
            return self._denial("comment_required")
        if len(raw_comment) > MAX_COMMENT_CHARS:
            return self._denial("comment_too_large")

        clarification = _CLARIFICATION.match(raw_comment)
        if clarification:
            return self._answer_clarification(
                proposal_id=clarification.group(1),
                answer=clarification.group(2),
                current_node_context=node_context,
                stage_hint=stage_hint,
            )

        strict_refinement = raw_comment.startswith(BILATERAL_MARKER)
        if strict_refinement:
            raw_comment = raw_comment[len(BILATERAL_MARKER):].strip()
        guard = sanitize_tokenizer_channels(raw_comment)
        clean_comment = str(guard.sanitized_text or "").strip()
        if not clean_comment:
            return self._denial("comment_removed_by_safety_filter")

        state = self.workflow.get_state()
        guide = build_guidance_packet(state)
        normalized_node = normalize_node_context(node_context)
        trace = compile_bulk_intent_trace(
            clean_comment,
            repo_root=self.repo_root,
            include_grounding=False,
        )
        summary = _intent_summary(trace)
        phase = str(state.get("current_phase") or "FRAME")
        phase_hash = _phase_hash(state)
        node_digest = _digest(normalized_node)
        recommended = (guide.get("recommended_actions") or [{}])[0]
        selected = dict(normalized_node.get("selected_node") or {})
        affected_files = (selected.get("file_path"),) if selected.get("file_path") else ()
        affected_symbols = (selected.get("symbol"),) if selected.get("symbol") else ()
        analysis = analyze_bilateral_request(
            clean_comment,
            arena="HUMAN_AGENT",
            affected_files=affected_files,
            affected_symbols=affected_symbols,
        )
        if not strict_refinement and analysis.questions:
            while analysis.questions:
                question = analysis.questions[0]
                if question.ambiguity_class == "PROHIBITED_OUTCOME":
                    answer = "Only the locked hard defaults apply."
                elif question.candidate_answers:
                    answer = question.candidate_answers[0]
                else:
                    break
                analysis = apply_clarification(analysis, question=question, answer=answer)

        now = time.time()
        try:
            repo = _repository_identity(self.repo_root)
        except (OSError, subprocess.SubprocessError, ValueError):
            return self._denial("repository_identity_unavailable")
        session = create_refinement_session(
            analysis,
            repository_head=repo["repository_head"],
            working_tree_digest=repo["source_tree_digest"],
            arena="HUMAN_AGENT",
            created_at=now,
            expires_at=now + SESSION_TTL_SECONDS,
        )
        deterministic_response = _fallback_response(
            stage_hint=stage_hint,
            guide=guide,
            node_context=normalized_node,
            intent_summary=summary,
            analysis=analysis,
        )
        response, provenance = self._voice(
            deterministic_response=deterministic_response,
            prefer_model=prefer_model and not analysis.questions,
            prompt_packet={
                "human_comment": clean_comment,
                "stage_hint": _bounded_text(stage_hint, 120),
                "current_phase": phase,
                "gate": guide.get("gate", {}),
                "recommended_action": recommended,
                "available_actions": list(guide.get("available_actions") or [])[:4],
                "blocked_actions": list(guide.get("blocked_actions") or [])[:4],
                "selected_topology": normalized_node,
                "intent_trace": summary,
                "bilateral_refinement": analysis.to_dict(),
                "authority": self._authority(),
            },
        )
        identity = {
            "workflow_id": state.get("workflow_id"),
            "phase": phase,
            "phase_hash": phase_hash,
            "stage_hint": _bounded_text(stage_hint, 120),
            "node_digest": node_digest,
            "comment": clean_comment,
            "session_id": session.session_id,
            "created_at": now,
        }
        proposal_id = "GDP-" + _digest(identity, size=12)
        status = "CLARIFICATION_REQUIRED" if analysis.questions else "PENDING_HUMAN_APPROVAL"
        packet = {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal_id,
            "status": status,
            "refinement_status": session.current_stage,
            "arena_id": "human_agent",
            "workflow_id": str(state.get("workflow_id") or ""),
            "current_phase": phase,
            "stage_hint": _bounded_text(stage_hint, 120),
            "phase_hash": phase_hash,
            "node_digest": node_digest,
            "node_context": normalized_node,
            "human_comment": clean_comment,
            "intent_trace": summary,
            "aura_response": response,
            "response_provenance": provenance,
            "recommended_action": recommended,
            "available_actions": list(guide.get("available_actions") or [])[:6],
            "blocked_actions": list(guide.get("blocked_actions") or [])[:6],
            "approval_required": True,
            "approval_scope": "advance_existing_guarded_workflow_only",
            "confirmation_scope": "confirm_canonical_bilateral_intent_for_existing_guarded_workflow_only",
            "refinement_session_id": session.session_id,
            **_analysis_fields(analysis),
            **self._authority(),
        }
        self._store_pending(proposal_id, packet, analysis, session, repo)
        self._record(
            {
                "proposal_id": proposal_id,
                "status": packet["status"],
                "refinement_status": session.current_stage,
                "current_phase": phase,
                "stage_hint": packet["stage_hint"],
                "node_digest": node_digest,
                "human_comment_digest": _digest(clean_comment),
                "created_at": now,
            }
        )
        return packet

    def _answer_clarification(
        self,
        *,
        proposal_id: str,
        answer: str,
        current_node_context: dict[str, Any] | None,
        stage_hint: str,
    ) -> dict[str, Any]:
        proposal = self.pending.get(proposal_id)
        runtime = self._runtime.get(proposal_id)
        if proposal is None or runtime is None:
            return self._denial("gate_dialogue_proposal_not_found")
        stale = self._current_context_denial(
            proposal,
            current_node_context=current_node_context,
            stage_hint=stage_hint,
        )
        if stale:
            return stale
        analysis: BilateralAnalysis = runtime["analysis"]
        session = runtime["session"]
        if not analysis.questions:
            return self._denial("clarification_not_required", proposal=proposal)
        guard = sanitize_tokenizer_channels(answer)
        clean_answer = str(guard.sanitized_text or "").strip()
        if not clean_answer:
            return self._denial("clarification_answer_required", proposal=proposal)
        question = analysis.questions[0]
        try:
            updated = apply_clarification(analysis, question=question, answer=clean_answer)
            observed = time.time()
            updated_session = refresh_refinement_session(
                session,
                updated,
                answer=clean_answer,
                observed_at=observed,
            )
        except ValueError as exc:
            return self._denial(f"clarification_rejected:{exc}", proposal=proposal)
        runtime["analysis"] = updated
        runtime["session"] = updated_session
        proposal.update(_analysis_fields(updated))
        proposal["refinement_status"] = updated_session.current_stage
        proposal["status"] = (
            "CLARIFICATION_REQUIRED" if updated.questions else "PENDING_HUMAN_APPROVAL"
        )
        proposal["aura_response"] = _fallback_response(
            stage_hint=proposal["stage_hint"],
            guide=build_guidance_packet(self.workflow.get_state()),
            node_context=proposal["node_context"],
            intent_summary=proposal["intent_trace"],
            analysis=updated,
        )
        proposal["response_provenance"] = {
            "model_used": False,
            "provider": "deterministic_local",
            "model": "none",
            "latency_sec": 0.0,
            "fallback_reason": "clarification_compiled_deterministically",
            "deterministic_route_authoritative": True,
        }
        self._record(
            {
                "proposal_id": proposal_id,
                "status": proposal["status"],
                "refinement_status": updated_session.current_stage,
                "clarification_question_id": question.question_id,
                "clarification_answer_digest": _digest(clean_answer),
                "created_at": time.time(),
            }
        )
        return dict(proposal)

    def approve(
        self,
        *,
        proposal_id: str,
        approved: bool,
        current_node_context: dict[str, Any] | None = None,
        stage_hint: str = "",
        reviewer: str = "human_operator",
        note: str = "",
    ) -> dict[str, Any]:
        proposal = self.pending.get(str(proposal_id or ""))
        runtime = self._runtime.get(str(proposal_id or ""))
        if proposal is None or runtime is None:
            return self._denial("gate_dialogue_proposal_not_found")
        stale = self._current_context_denial(
            proposal,
            current_node_context=current_node_context,
            stage_hint=stage_hint,
        )
        if stale:
            return stale
        if approved and not proposal.get("can_confirm_intent"):
            return self._denial("clarification_required", proposal=proposal)

        if not approved:
            return self._finalize_rejection(proposal, reviewer=reviewer, note=note)

        state = self.workflow.get_state()
        normalized_node = normalize_node_context(current_node_context)
        paths = _allowed_paths(normalized_node, state)
        if not paths:
            return self._denial("exact_allowed_path_required", proposal=proposal)
        try:
            repo = _repository_identity(self.repo_root)
        except (OSError, subprocess.SubprocessError, ValueError):
            return self._denial("repository_identity_unavailable", proposal=proposal)
        expected_repo = runtime["repository"]
        if (
            repo["repository_head"] != expected_repo["repository_head"]
            or repo["source_tree_digest"] != expected_repo["source_tree_digest"]
        ):
            return self._denial("stale_repository_identity", proposal=proposal)
        confirmed_at = time.time()
        runtime_profile_digest = stable_digest(
            {
                "workflow_id": proposal["workflow_id"],
                "phase": proposal["current_phase"],
                "phase_hash": proposal["phase_hash"],
                "node_digest": proposal["node_digest"],
                "stage_hint": proposal["stage_hint"],
            }
        )
        try:
            compilation = compile_confirmed_bilateral_intent(
                session=runtime["session"],
                analysis=runtime["analysis"],
                repository_head=repo["repository_head"],
                source_tree_digest=repo["source_tree_digest"],
                working_tree_clean_receipt=repo["working_tree_clean_receipt"],
                allowed_paths=paths,
                runtime_profile_digest=runtime_profile_digest,
                human_reviewer=_bounded_text(reviewer, 180) or "human_operator",
                confirmed_at=confirmed_at,
                expires_at=min(
                    confirmed_at + SESSION_TTL_SECONDS,
                    float(runtime["session"].expires_at),
                ),
            )
        except ValueError as exc:
            return self._denial(f"canonical_compilation_failed:{exc}", proposal=proposal)

        decision = self._decision(
            proposal,
            approved=True,
            reviewer=reviewer,
            note=note,
            reviewed_at=confirmed_at,
        )
        decision["confirmation_id"] = compilation["confirmation_receipt"]["confirmation_id"]
        decision["intent_digest"] = compilation["intent_packet"]["intent_digest"]
        decision["semantic_ledger_digest"] = compilation["semantic_ledger"]["ledger_digest"]
        proposal["status"] = "APPROVED_FOR_NEXT_GUARDED_GATE"
        proposal["decision"] = decision
        proposal["canonical_compilation"] = compilation
        self.confirmed[proposal["proposal_id"]] = {
            "proposal": dict(proposal),
            "repository_head": repo["repository_head"],
            "source_tree_digest": repo["source_tree_digest"],
            "phase_hash": proposal["phase_hash"],
            "node_digest": proposal["node_digest"],
            "confirmed_at": confirmed_at,
        }
        self.pending.pop(proposal["proposal_id"], None)
        self._runtime.pop(proposal["proposal_id"], None)
        self._record(decision)

        ledger = list(self.workflow.evidence.get("approved_gate_intents") or [])
        ledger.append(
            {
                **decision,
                "confirmation_ref": decision["confirmation_id"],
                "guardrail_set_digest": compilation["confirmation_receipt"][
                    "guardrail_set_digest"
                ],
                "negative_requirements_digest": compilation["confirmation_receipt"][
                    "negative_requirements_digest"
                ],
                "u7_references": compilation["u7_references"],
            }
        )
        self.workflow.evidence["approved_gate_intents"] = ledger[-40:]
        if hasattr(self.workflow, "_event"):
            self.workflow._event(
                "gate_dialogue_intent_confirmation",
                f"{proposal['stage_hint']}:{proposal['proposal_id']}:{decision['recommended_action_id']}",
            )
        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal["proposal_id"],
            "status": decision["status"],
            "approved": True,
            "decision": decision,
            "canonical_compilation": compilation,
            "next_action": proposal.get("recommended_action"),
            "workflow": self.workflow.get_state(),
            "note": (
                "Human bilateral intent confirmation recorded. The existing guarded workflow may now "
                "attempt the next gate; no patch, commit, push, merge, production, or learning authority was granted."
            ),
            **self._authority(),
        }

    def status(self) -> dict[str, Any]:
        current_state = self.workflow.get_state()
        current_phase_hash = _phase_hash(current_state)
        try:
            repo = _repository_identity(self.repo_root)
        except (OSError, subprocess.SubprocessError, ValueError):
            repo = {"repository_head": "", "source_tree_digest": ""}
        confirmed: list[dict[str, Any]] = []
        for row in list(self.confirmed.values())[-10:]:
            proposal = dict(row["proposal"])
            stale_reasons: list[str] = []
            if row["repository_head"] != repo.get("repository_head"):
                stale_reasons.append("repository_head_changed")
            if row["source_tree_digest"] != repo.get("source_tree_digest"):
                stale_reasons.append("source_tree_digest_changed")
            if row["phase_hash"] != current_phase_hash:
                stale_reasons.append("workflow_phase_or_evidence_changed")
            proposal["confirmation_currency"] = "STALE" if stale_reasons else "CURRENT"
            proposal["stale_reasons"] = stale_reasons
            confirmed.append(proposal)
        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "pending": list(self.pending.values())[-10:],
            "confirmed": confirmed,
            "history": self.history[-30:],
            "clarification_supported": True,
            "canonical_intent_compilation": True,
            "approval_required": True,
            **self._authority(),
        }

    def _voice(
        self,
        *,
        deterministic_response: str,
        prefer_model: bool,
        prompt_packet: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        response = deterministic_response
        model_used = False
        provider = "deterministic_local"
        model = "none"
        latency_sec = 0.0
        model_error = ""
        if prefer_model:
            try:
                configured = available_providers()
                if configured:
                    llm = ExternalLLM(
                        model="cheap",
                        task="human_agent_bilateral_gate_dialogue",
                        aspect=str(prompt_packet.get("current_phase") or "frame").lower(),
                    )
                    text, error, latency_sec = llm.generate(
                        _model_prompt(prompt_packet),
                        max_tokens=500,
                        temperature=0.0,
                        resonance_egress=False,
                        call_type="human_agent_bilateral_gate_dialogue",
                    )
                    if text and not error:
                        response = str(text).strip()
                        model_used = True
                        provider = llm.provider
                        model = llm.model
                    else:
                        model_error = "external_voice_unavailable"
                else:
                    model_error = "no_configured_external_provider"
            except Exception:
                model_error = "external_voice_unavailable"
        return response, {
            "model_used": model_used,
            "provider": provider,
            "model": model,
            "latency_sec": round(float(latency_sec), 4),
            "fallback_reason": model_error,
            "deterministic_route_authoritative": True,
        }

    def _store_pending(
        self,
        proposal_id: str,
        packet: dict[str, Any],
        analysis: BilateralAnalysis,
        session: Any,
        repository: dict[str, Any],
    ) -> None:
        self.pending[proposal_id] = packet
        self._runtime[proposal_id] = {
            "analysis": analysis,
            "session": session,
            "repository": repository,
        }
        while len(self.pending) > MAX_PENDING:
            oldest = next(iter(self.pending))
            self.pending.pop(oldest, None)
            self._runtime.pop(oldest, None)

    def _current_context_denial(
        self,
        proposal: dict[str, Any],
        *,
        current_node_context: dict[str, Any] | None,
        stage_hint: str,
    ) -> dict[str, Any] | None:
        state = self.workflow.get_state()
        if str(state.get("workflow_id") or "") != proposal.get("workflow_id"):
            return self._denial("stale_workflow_identity", proposal=proposal)
        if str(state.get("current_phase") or "") != proposal.get("current_phase"):
            return self._denial("stale_workflow_phase", proposal=proposal)
        if _phase_hash(state) != proposal.get("phase_hash"):
            return self._denial("stale_workflow_evidence", proposal=proposal)
        normalized_node = normalize_node_context(current_node_context)
        if proposal.get("node_context", {}).get("selected_node") and not normalized_node.get(
            "selected_node"
        ):
            return self._denial("current_topology_node_required", proposal=proposal)
        if _digest(normalized_node) != proposal.get("node_digest"):
            return self._denial("stale_topology_selection", proposal=proposal)
        if _bounded_text(stage_hint, 120) != str(proposal.get("stage_hint") or ""):
            return self._denial("stale_tour_gate", proposal=proposal)
        runtime = self._runtime.get(proposal["proposal_id"])
        if runtime and time.time() >= float(runtime["session"].expires_at):
            return self._denial("refinement_session_expired", proposal=proposal)
        return None

    def _finalize_rejection(
        self,
        proposal: dict[str, Any],
        *,
        reviewer: str,
        note: str,
    ) -> dict[str, Any]:
        decision = self._decision(
            proposal,
            approved=False,
            reviewer=reviewer,
            note=note,
            reviewed_at=time.time(),
        )
        proposal["status"] = decision["status"]
        proposal["decision"] = decision
        self.pending.pop(proposal["proposal_id"], None)
        self._runtime.pop(proposal["proposal_id"], None)
        self._record(decision)
        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal["proposal_id"],
            "status": decision["status"],
            "approved": False,
            "decision": decision,
            "next_action": {},
            "workflow": self.workflow.get_state(),
            "note": "The bilateral interpretation was rejected. No workflow action was executed.",
            **self._authority(),
        }

    @staticmethod
    def _decision(
        proposal: dict[str, Any],
        *,
        approved: bool,
        reviewer: str,
        note: str,
        reviewed_at: float,
    ) -> dict[str, Any]:
        return {
            "proposal_id": proposal["proposal_id"],
            "status": "APPROVED_FOR_NEXT_GUARDED_GATE" if approved else "REJECTED_BY_HUMAN",
            "approved": bool(approved),
            "reviewer": _bounded_text(reviewer, 180) or "human_operator",
            "note": _bounded_text(note, 1200),
            "reviewed_at": reviewed_at,
            "workflow_id": proposal["workflow_id"],
            "current_phase": proposal["current_phase"],
            "stage_hint": proposal["stage_hint"],
            "phase_hash": proposal["phase_hash"],
            "node_digest": proposal["node_digest"],
            "human_comment_digest": _digest(proposal["human_comment"]),
            "aura_response_digest": _digest(proposal["aura_response"]),
            "recommended_action_id": str(
                (proposal.get("recommended_action") or {}).get("action_id") or ""
            ),
            "advance_authority": "existing_guarded_workflow_only" if approved else "none",
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }

    @staticmethod
    def _authority() -> dict[str, Any]:
        return {
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
            "automatic_learning_promotion": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _record(self, item: dict[str, Any]) -> None:
        self.history.append(dict(item))
        self.history = self.history[-MAX_HISTORY:]

    @staticmethod
    def _denial(reason: str, *, proposal: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "reason": str(reason),
            "status": "DENIED",
            "proposal_id": str((proposal or {}).get("proposal_id") or ""),
            "fail_closed": True,
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
            "automatic_learning_promotion": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


__all__ = [
    "ArenaGateDialogueService",
    "BILATERAL_MARKER",
    "GATE_DIALOGUE_VERSION",
    "normalize_node_context",
]
