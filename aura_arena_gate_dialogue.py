"""Topology-anchored, approval-gated dialogue for Aura Arenas.

A gate dialogue lets a human select an exact topology node, add ordinary-language
intent, and ask Aura to address that intent from the current guarded workflow state.
Aura's response is a proposal only. It cannot advance a gate until the human approves
it, and approval becomes stale if the workflow phase or selected topology evidence
changes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any

from aura_human_agent_guidance import build_guidance_packet
from aura_llm_egress import ExternalLLM, available_providers
from aura_showcase_intent import compile_bulk_intent_trace
from aura_tokenizer_guard import sanitize_tokenizer_channels

GATE_DIALOGUE_VERSION = "AURA_ARENA_GATE_DIALOGUE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MAX_COMMENT_CHARS = 6000
MAX_HISTORY = 80
SLOT_KEYS = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")


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
            result.append({
                str(key)[:80]: _bounded_text(val, 300)
                for key, val in list(item.items())[:10]
                if key in {"id", "label", "file_path", "symbol", "kind", "relation", "source", "target", "status"}
            })
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
        "line_range": [int(item) for item in list(line_range)[:2] if isinstance(item, (int, float))],
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
    routed = dict(state.get("state_packet") or {})
    existing = str(routed.get("phase_hash") or "").strip()
    if existing:
        return existing
    return _digest({
        "workflow_id": state.get("workflow_id"),
        "phase": state.get("current_phase"),
        "objective": state.get("objective"),
        "evidence_keys": state.get("evidence_keys", []),
    })


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


def _fallback_response(
    *,
    comment: str,
    stage_hint: str,
    guide: dict[str, Any],
    node_context: dict[str, Any],
    intent_summary: dict[str, Any],
) -> str:
    gate = dict(guide.get("gate") or {})
    node = dict(node_context.get("selected_node") or {})
    anchor = node.get("label") or node.get("symbol") or node.get("file_path") or "the current gate"
    location = node.get("file_path") or "no exact file selected"
    recommended = list(guide.get("recommended_actions") or [])
    blocked = list(guide.get("blocked_actions") or [])
    if recommended:
        item = recommended[0]
        action = (
            f"The safest currently admitted action is {item.get('label')}. "
            f"{item.get('description')}"
        )
    elif blocked:
        missing = ", ".join(blocked[0].get("missing_evidence") or []) or "declared gate evidence"
        action = f"No work action is admitted yet. The smallest visible gap is {missing}."
    else:
        action = "No state-local work action is currently admitted."
    slots = intent_summary.get("slots") or {}
    slot_text = " · ".join(f"{key}={slots.get(key) or '—'}" for key in SLOT_KEYS)
    return (
        f"At {gate.get('title') or stage_hint or 'this gate'}, Aura anchored your intent to {anchor} "
        f"({location}). Your comment was parsed locally as {slot_text}. {action} "
        "Approval records this interpretation for the selected evidence and permits only the existing "
        "guarded workflow to attempt the next step. It does not grant patch, commit, push, or merge authority."
    )


def _model_prompt(packet: dict[str, Any]) -> str:
    return (
        "You are Aura's external voice inside the Human Agent Arena. Address the human's new intent "
        "using only the supplied current gate, admitted/blocked actions, selected topology metadata, "
        "and deterministic intent trace. Explain how the selected file or symbol, its dependencies, "
        "callers, tests, and current evidence affect the request. Never invent a file, action, test, "
        "capability, source fact, or approval. Treat the deterministic recommended_action as authoritative. "
        "Keep the response under 220 words and end by clearly asking for human approval before the existing "
        "guarded workflow attempts the next gate.\n\n[AURA_GATE_DIALOGUE_PACKET]\n"
        + json.dumps(packet, indent=2, ensure_ascii=False, default=str)
        + "\n[/AURA_GATE_DIALOGUE_PACKET]"
    )


class ArenaGateDialogueService:
    """Runtime-local proposal and approval ledger for one Human Agent workflow."""

    def __init__(self, repo_root: str | Path, workflow: Any) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.workflow = workflow
        self.pending: dict[str, dict[str, Any]] = {}
        self.history: list[dict[str, Any]] = []

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
        deterministic_response = _fallback_response(
            comment=clean_comment,
            stage_hint=stage_hint,
            guide=guide,
            node_context=normalized_node,
            intent_summary=summary,
        )

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
                        task="human_agent_gate_dialogue",
                        aspect=phase.lower(),
                    )
                    prompt_packet = {
                        "human_comment": clean_comment,
                        "stage_hint": _bounded_text(stage_hint, 120),
                        "current_phase": phase,
                        "gate": guide.get("gate", {}),
                        "recommended_action": recommended,
                        "available_actions": list(guide.get("available_actions") or [])[:4],
                        "blocked_actions": list(guide.get("blocked_actions") or [])[:4],
                        "selected_topology": normalized_node,
                        "intent_trace": summary,
                        "authority": {
                            "human_approval_required": True,
                            "production_mutation": False,
                            "automatic_commit": False,
                            "automatic_push": False,
                            "automatic_merge": False,
                        },
                    }
                    text, error, latency_sec = llm.generate(
                        _model_prompt(prompt_packet),
                        max_tokens=500,
                        temperature=0.0,
                        resonance_egress=False,
                        call_type="human_agent_gate_dialogue",
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
            except Exception:  # noqa: BLE001
                model_error = "external_voice_unavailable"

        identity = {
            "workflow_id": state.get("workflow_id"),
            "phase": phase,
            "phase_hash": phase_hash,
            "stage_hint": _bounded_text(stage_hint, 120),
            "node_digest": node_digest,
            "comment": clean_comment,
            "created_at": time.time(),
        }
        proposal_id = "GDP-" + _digest(identity, size=12)
        packet = {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal_id,
            "status": "PENDING_HUMAN_APPROVAL",
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
            "response_provenance": {
                "model_used": model_used,
                "provider": provider,
                "model": model,
                "latency_sec": round(float(latency_sec), 4),
                "fallback_reason": model_error,
                "deterministic_route_authoritative": True,
            },
            "recommended_action": recommended,
            "available_actions": list(guide.get("available_actions") or [])[:6],
            "blocked_actions": list(guide.get("blocked_actions") or [])[:6],
            "approval_required": True,
            "approval_scope": "advance_existing_guarded_workflow_only",
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        self.pending[proposal_id] = packet
        self._record({
            "proposal_id": proposal_id,
            "status": packet["status"],
            "current_phase": phase,
            "stage_hint": packet["stage_hint"],
            "node_digest": node_digest,
            "human_comment": clean_comment,
            "created_at": identity["created_at"],
        })
        return packet

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
        if proposal is None:
            return self._denial("gate_dialogue_proposal_not_found")

        state = self.workflow.get_state()
        if str(state.get("workflow_id") or "") != proposal.get("workflow_id"):
            return self._denial("stale_workflow_identity", proposal=proposal)
        if str(state.get("current_phase") or "") != proposal.get("current_phase"):
            return self._denial("stale_workflow_phase", proposal=proposal)
        if _phase_hash(state) != proposal.get("phase_hash"):
            return self._denial("stale_workflow_evidence", proposal=proposal)
        normalized_node = normalize_node_context(current_node_context)
        if proposal.get("node_context", {}).get("selected_node") and not normalized_node.get("selected_node"):
            return self._denial("current_topology_node_required", proposal=proposal)
        if _digest(normalized_node) != proposal.get("node_digest"):
            return self._denial("stale_topology_selection", proposal=proposal)
        if _bounded_text(stage_hint, 120) != str(proposal.get("stage_hint") or ""):
            return self._denial("stale_tour_gate", proposal=proposal)

        decision_status = "APPROVED_FOR_NEXT_GUARDED_GATE" if approved else "REJECTED_BY_HUMAN"
        decision = {
            "proposal_id": proposal["proposal_id"],
            "status": decision_status,
            "approved": bool(approved),
            "reviewer": _bounded_text(reviewer, 180) or "human_operator",
            "note": _bounded_text(note, 1200),
            "reviewed_at": time.time(),
            "workflow_id": proposal["workflow_id"],
            "current_phase": proposal["current_phase"],
            "stage_hint": proposal["stage_hint"],
            "phase_hash": proposal["phase_hash"],
            "node_digest": proposal["node_digest"],
            "human_comment_digest": _digest(proposal["human_comment"]),
            "aura_response_digest": _digest(proposal["aura_response"]),
            "recommended_action_id": str((proposal.get("recommended_action") or {}).get("action_id") or ""),
            "advance_authority": "existing_guarded_workflow_only" if approved else "none",
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }
        proposal["status"] = decision_status
        proposal["decision"] = decision
        self.pending.pop(proposal["proposal_id"], None)
        self._record(decision)

        if approved:
            ledger = list(self.workflow.evidence.get("approved_gate_intents") or [])
            ledger.append(decision)
            self.workflow.evidence["approved_gate_intents"] = ledger[-40:]
            if hasattr(self.workflow, "_event"):
                self.workflow._event(
                    "gate_dialogue_approval",
                    f"{proposal['stage_hint']}:{proposal['proposal_id']}:{decision['recommended_action_id']}",
                )

        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal["proposal_id"],
            "status": decision_status,
            "approved": bool(approved),
            "decision": decision,
            "next_action": proposal.get("recommended_action") if approved else {},
            "workflow": self.workflow.get_state(),
            "note": (
                "Human approval recorded. The existing guarded workflow may now attempt the next gate."
                if approved
                else "The proposal was rejected. No workflow action was executed."
            ),
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "pending": list(self.pending.values())[-10:],
            "history": self.history[-30:],
            "approval_required": True,
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
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
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


__all__ = [
    "ArenaGateDialogueService",
    "GATE_DIALOGUE_VERSION",
    "normalize_node_context",
]
