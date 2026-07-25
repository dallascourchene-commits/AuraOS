"""Topology-anchored bilateral intent refinement for Aura Arenas.

The Gate Dialogue is a bounded, multi-turn clarification service.  It compiles
proposal-only positive and negative requirements, guardrails, paired teach-back,
human confirmation, and canonical record references.  It never executes a
workflow action and grants no patch, commit, push, merge, deployment, production,
professional, physical-work, or learning-promotion authority.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, Sequence

from aura_bilateral_intent_canonical import (
    compile_bilateral_canonical_bundle,
    compile_canonical_records,
)
from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest, stable_id
from aura_human_agent_guidance import build_guidance_packet
from aura_intent_refinement import (
    AmbiguityClass,
    ClarificationQuestion,
    ConfirmationStatus,
    GuardrailProposal,
    HumanGuardrailDisposition,
    IntentConfirmationReceipt,
    IntentRefinementSession,
    PairedTeachBack,
    compile_default_guardrails,
    detect_requirement_contradictions,
    extract_negative_requirements,
)
from aura_llm_egress import ExternalLLM, available_providers
from aura_showcase_intent import compile_bulk_intent_trace
from aura_tokenizer_guard import sanitize_tokenizer_channels

GATE_DIALOGUE_VERSION = "AURA_ARENA_GATE_DIALOGUE_V2"
MAX_COMMENT_CHARS = 6000
MAX_HISTORY = 80
MAX_PENDING = 20
SESSION_TTL_SECONDS = 30 * 60
SLOT_KEYS = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")
_PRONOUN_ONLY = {"it", "that", "this", "so", "them", "those"}


def _digest(value: Any, *, size: int = 20) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _bounded_text(value: Any, limit: int = 800) -> str:
    return str(value or "").strip()[:limit]


def _bounded_list(value: Any, *, limit: int = 12) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[Any] = []
    allowed = {
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
    for item in list(value)[:limit]:
        if isinstance(item, dict):
            result.append(
                {
                    str(key)[:80]: _bounded_text(val, 300)
                    for key, val in list(item.items())[:10]
                    if key in allowed
                }
            )
        else:
            result.append(_bounded_text(item, 300))
    return result


def _json_copy(value: Any) -> Any:
    """Return a mutable JSON copy without stringifying frozen mappings."""
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _json_copy(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_copy(item) for item in value]
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def _repository_identity(repo_root: Path) -> dict[str, Any]:
    try:
        head = _git(repo_root, "rev-parse", "HEAD")
        status = _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("exact repository identity is unavailable") from exc
    status_lines = tuple(line for line in status.splitlines() if line.strip())
    working_tree_digest = stable_digest({"head": head, "status": list(status_lines)})
    clean_receipt = stable_digest(
        {
            "repository_head": head,
            "working_tree_digest": working_tree_digest,
            "clean": not status_lines,
        }
    )
    codemap_path = repo_root / ".aura" / "CODEMAP.json"
    if not codemap_path.is_file():
        raise ValueError("canonical CODEMAP is unavailable")
    codemap_digest = "sha256:" + hashlib.sha256(codemap_path.read_bytes()).hexdigest()
    return {
        "repository_head": head,
        "working_tree_digest": working_tree_digest,
        "clean": not status_lines,
        "dirty_paths": list(status_lines),
        "clean_receipt": clean_receipt,
        "codemap_digest": codemap_digest,
    }


def normalize_node_context(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Keep presenter-safe topology metadata; never transfer source contents."""
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
            int(item)
            for item in list(line_range)[:2]
            if isinstance(item, (int, float))
        ],
        "projection_truth": _bounded_text(selected.get("projection_truth"), 120),
        "patch_authority": False,
    }
    if not any(
        value
        for key, value in node.items()
        if key not in {"patch_authority", "line_range"}
    ):
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
    return _digest(
        {
            "workflow_id": state.get("workflow_id"),
            "phase": state.get("current_phase"),
            "objective": state.get("objective"),
            "evidence_keys": state.get("evidence_keys", []),
        }
    )


def _intent_summary(trace: dict[str, Any]) -> dict[str, Any]:
    packet = dict(trace.get("six_slot_packet") or {})
    slots = dict(packet.get("slots") or {})
    bilateral = dict(trace.get("bilateral_intent") or {})
    return {
        "ok": bool(trace.get("ok")),
        "model_calls_made": int(trace.get("model_calls_made") or 0),
        "compressed_objective": _bounded_text(
            trace.get("compressed_objective"), 1600
        ),
        "slots": {key: _bounded_text(slots.get(key), 200) for key in SLOT_KEYS},
        "machine_route": {
            key: _bounded_text((trace.get("machine_route") or {}).get(key), 240)
            for key in ("rule_name", "route", "model", "context", "reason")
        },
        "bilateral_status": _bounded_text(bilateral.get("status"), 80),
        "negative_requirement_refs": list(
            bilateral.get("negative_requirement_refs") or []
        )[:24],
    }


def _node_scope(node_context: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    node = dict(node_context.get("selected_node") or {})
    paths = tuple(
        dict.fromkeys(
            value
            for value in (
                str(node.get("file_path") or "").strip(),
                *(
                    str(item).strip()
                    for item in node_context.get("tests") or ()
                    if isinstance(item, str)
                ),
            )
            if value
        )
    )
    symbols = tuple(
        value
        for value in (str(node.get("symbol") or "").strip(),)
        if value
    )
    return paths, symbols


def _positive_requirements(comment: str) -> tuple[str, ...]:
    text = comment.strip()
    positive = re.sub(
        r"(?i)\b(?:do not|don't|never|must not|cannot|can't|without)\b[^.!?\n]*[.!?]?",
        "",
        text,
    ).strip(" \t,;:-")
    return (positive or text,)


def _fallback_negatives(
    *,
    node_context: Mapping[str, Any],
    stage_hint: str,
) -> tuple[str, ...]:
    node = dict(node_context.get("selected_node") or {})
    anchor = (
        node.get("file_path")
        or node.get("symbol")
        or stage_hint
        or "the current guarded gate"
    )
    return (
        f"Do not expand beyond {anchor} and its explicitly returned bounded neighbours.",
        "Do not treat topology, semantic similarity, model confidence, or visual state as patch or approval authority.",
        "Do not commit, push, open or merge a pull request, deploy, mutate production, or promote learning without separate declared authority.",
        "Do not hide missing evidence, unresolved ambiguity, verifier failure, or stale context behind a successful-looking response.",
    )


def _definition_records(
    positives: Sequence[str],
    negatives: Sequence[str],
    *,
    source_request_digest: str,
    node_context: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = [
        {
            "term": "requested outcome",
            "means": list(positives),
            "does_not_mean": list(negatives),
            "source_refs": [f"request:{source_request_digest}"],
            "freshness": "CURRENT",
        }
    ]
    node = dict(node_context.get("selected_node") or {})
    if node:
        label = (
            str(node.get("label") or node.get("symbol") or node.get("file_path") or "")
            .strip()
        )
        if label:
            records.append(
                {
                    "term": label,
                    "means": [
                        "The exact selected topology metadata returned by the current Arena projection."
                    ],
                    "does_not_mean": [
                        "Full source transfer, patch authority, approval, or permission to modify neighbouring files."
                    ],
                    "source_refs": [
                        f"topology:{_digest(node_context)}",
                        str(node.get("file_path") or "topology_selection"),
                    ],
                    "freshness": "CURRENT",
                }
            )
    return tuple(records)


def _ambiguities(
    comment: str,
    positives: Sequence[str],
    negatives: Sequence[Any],
    contradictions: Sequence[Mapping[str, Any]],
    node_context: Mapping[str, Any],
) -> tuple[ClarificationQuestion, ...]:
    result: list[ClarificationQuestion] = []
    for conflict in contradictions:
        result.append(
            ClarificationQuestion.create(
                ambiguity_class=AmbiguityClass.CONTRADICTION,
                question=(
                    "Which requirement controls: "
                    f"“{conflict['positive_requirement']}” or "
                    f"“do not {conflict['negative_requirement']}”?"
                ),
                why_it_changes_execution=(
                    "Aura cannot compile mutually inconsistent positive and negative proof obligations."
                ),
                candidate_answers=(
                    "The positive requirement controls.",
                    "The negative requirement controls.",
                    "Revise both requirements.",
                ),
                affected_requirements=(
                    str(conflict["positive_requirement"]),
                    str(conflict["negative_requirement"]),
                ),
            )
        )
    no_anchor = not dict(node_context.get("selected_node") or {})
    for item in negatives:
        target = str(getattr(item, "target", "") or "").casefold()
        if bool(getattr(item, "ambiguous", False)) and (
            no_anchor or target in _PRONOUN_ONLY
        ):
            result.append(
                ClarificationQuestion.create(
                    ambiguity_class=AmbiguityClass.PROHIBITED_OUTCOME,
                    question=f"What exactly does “{item.statement}” prohibit?",
                    why_it_changes_execution=(
                        "The negative requirement must bind an exact target before confirmation."
                    ),
                    candidate_answers=(
                        "The selected topology node.",
                        "The current workflow gate.",
                        "A different target I will name.",
                    ),
                    affected_requirements=(item.requirement_id,),
                )
            )
    if no_anchor and re.search(r"(?i)\b(this|that|it|them|those)\b", comment):
        result.append(
            ClarificationQuestion.create(
                ambiguity_class=AmbiguityClass.SCOPE,
                question="What exact file, symbol, gate, or outcome does the reference name?",
                why_it_changes_execution=(
                    "The request uses a contextual reference but no exact topology node is selected."
                ),
                candidate_answers=(
                    "The current guarded gate.",
                    "A file or symbol I will name.",
                    "The overall task objective.",
                ),
                affected_requirements=tuple(positives),
            )
        )
    unique: dict[str, ClarificationQuestion] = {}
    for item in result:
        unique[item.question_id] = item
    return tuple(unique.values())


def _teach_back(
    positives: Sequence[str],
    negatives: Sequence[str],
    guardrails: Sequence[Mapping[str, Any]],
    unresolved: Sequence[Mapping[str, Any]] = (),
) -> PairedTeachBack:
    preserved = [
        str(item.get("statement") or "")
        for item in guardrails
        if item.get("hardness")
        in {"HARD_ARCHITECTURAL", "HARD_AUTHORITY", "DOMAIN_REQUIRED"}
    ]
    stop_conditions = [
        "the selected topology, workflow phase, repository head, source-tree digest, definitions, authority, or allowed paths change",
        "a required verifier fails or evidence is missing",
        "scope, meaning, guardrails, or authority must expand",
    ]
    decisions = [
        str(item.get("question") or "")
        for item in unresolved
        if item.get("required_human_answer") is not False
    ]
    return PairedTeachBack.create(
        will_do=positives,
        will_not_do=negatives,
        will_preserve=tuple(value for value in preserved if value),
        will_stop_or_escalate_if=stop_conditions,
        positive_examples=(f"Measured proof: {positives[0]}",),
        negative_examples=(f"Fail closed if: {negatives[0]}",),
        unresolved_assumptions=tuple(decisions),
        required_human_decisions=tuple(decisions),
    )


def _fallback_response(
    *,
    stage_hint: str,
    guide: dict[str, Any],
    node_context: dict[str, Any],
    positives: Sequence[str],
    negatives: Sequence[str],
    unresolved: Sequence[Mapping[str, Any]],
) -> str:
    gate = dict(guide.get("gate") or {})
    node = dict(node_context.get("selected_node") or {})
    anchor = (
        node.get("label")
        or node.get("symbol")
        or node.get("file_path")
        or "the current gate"
    )
    if unresolved:
        next_question = str(unresolved[0].get("question") or "")
        return (
            f"Aura anchored the request to {anchor} at "
            f"{gate.get('title') or stage_hint or 'this gate'}. "
            f"Proposed outcome: {positives[0]} Proposed prohibition: {negatives[0]} "
            f"Before confirmation, Aura needs one answer: {next_question}"
        )
    return (
        f"Aura anchored the request to {anchor} at "
        f"{gate.get('title') or stage_hint or 'this gate'}. "
        f"Proposed outcome: {positives[0]} Proposed prohibition: {negatives[0]} "
        "Review the paired teach-back and guardrails, then explicitly confirm or correct "
        "the bilateral intent. Confirmation still grants no workflow execution, patch, "
        "commit, push, merge, deployment, production, professional, physical-work, or "
        "learning-promotion authority."
    )


def _model_prompt(packet: dict[str, Any]) -> str:
    return (
        "You are Aura's proposal-only voice inside the Human Agent Arena. Explain the "
        "supplied deterministic bilateral refinement without changing it. Preserve the "
        "positive requirements, negative requirements, hard guardrails, unresolved "
        "question, paired teach-back, exact topology anchor, and deterministic guarded "
        "next action. Never invent source, authority, evidence, approval, or capability. "
        "Do not imply that confirmation authorizes execution. Keep the response under "
        "220 words.\n\n[AURA_BILATERAL_GATE_PACKET]\n"
        + json.dumps(packet, indent=2, ensure_ascii=False, default=str)
        + "\n[/AURA_BILATERAL_GATE_PACKET]"
    )


def _public_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {"_session", "_confirmation", "_created_identity"}
    return {
        key: _json_copy(value)
        for key, value in proposal.items()
        if key not in excluded
    }


class ArenaGateDialogueService:
    """Runtime-local bilateral refinement and gate-approval ledger."""

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
        try:
            repo = _repository_identity(self.repo_root)
        except ValueError as exc:
            return self._denial(str(exc).replace(" ", "_"))

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

        extracted = extract_negative_requirements(clean_comment)
        positives = _positive_requirements(clean_comment)
        negatives = tuple(item.statement for item in extracted) or _fallback_negatives(
            node_context=normalized_node,
            stage_hint=stage_hint,
        )
        contradictions = detect_requirement_contradictions(positives, extracted)
        questions = _ambiguities(
            clean_comment,
            positives,
            extracted,
            contradictions,
            normalized_node,
        )
        files, symbols = _node_scope(normalized_node)
        guardrails = compile_default_guardrails(
            arena="CODING",
            affected_files=files,
            affected_symbols=symbols,
        )

        session = IntentRefinementSession.create(
            repository_head=repo["repository_head"],
            working_tree_digest=repo["working_tree_digest"],
            arena="CODING",
            source_request=clean_comment,
            created_at=time.time(),
            expires_at=time.time() + SESSION_TTL_SECONDS,
        )
        definitions = _definition_records(
            positives,
            negatives,
            source_request_digest=session.source_request_digest,
            node_context=normalized_node,
        )
        question_records = tuple(item.to_dict() for item in questions)
        session = session.transition(
            "ANALYZED",
            positive_requirements=positives,
            negative_requirements=negatives,
            definitions=definitions,
            guardrails=guardrails,
            unresolved_ambiguities=question_records,
            questions_asked=question_records,
        )
        if questions:
            session = session.transition("CLARIFICATION_REQUIRED")
            teach_back = None
            status = "PENDING_CLARIFICATION"
        else:
            teach_back = _teach_back(
                positives,
                negatives,
                tuple(item.to_dict() for item in guardrails),
            )
            session = session.transition(
                "TEACH_BACK_PENDING",
                teach_back=teach_back,
            )
            status = "PENDING_INTENT_CONFIRMATION"

        refinement = self._refinement_projection(session)
        deterministic_response = _fallback_response(
            stage_hint=stage_hint,
            guide=guide,
            node_context=normalized_node,
            positives=positives,
            negatives=negatives,
            unresolved=refinement["unresolved_ambiguities"],
        )
        response = deterministic_response
        provenance = {
            "model_used": False,
            "provider": "deterministic_local",
            "model": "none",
            "latency_sec": 0.0,
            "fallback_reason": "",
            "deterministic_route_authoritative": True,
        }
        if prefer_model:
            response, provenance = self._optional_voice(
                deterministic_response=deterministic_response,
                packet={
                    "human_comment": clean_comment,
                    "current_phase": phase,
                    "stage_hint": _bounded_text(stage_hint, 120),
                    "gate": guide.get("gate", {}),
                    "recommended_action": (guide.get("recommended_actions") or [{}])[0],
                    "selected_topology": normalized_node,
                    "intent_trace": summary,
                    "refinement": refinement,
                    "authority": self._authority_projection(),
                },
            )

        created_at = time.time()
        identity = {
            "session_id": session.session_id,
            "workflow_id": state.get("workflow_id"),
            "phase": phase,
            "phase_hash": phase_hash,
            "stage_hint": _bounded_text(stage_hint, 120),
            "node_digest": node_digest,
            "created_at": created_at,
        }
        proposal_id = stable_id("gate-refinement", identity)
        proposal = {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal_id,
            "session_id": session.session_id,
            "status": status,
            "arena_id": "human_agent",
            "workflow_id": str(state.get("workflow_id") or ""),
            "current_phase": phase,
            "stage_hint": identity["stage_hint"],
            "phase_hash": phase_hash,
            "repository_head": repo["repository_head"],
            "source_tree_digest": repo["working_tree_digest"],
            "repository_clean": repo["clean"],
            "dirty_paths": repo["dirty_paths"],
            "node_digest": node_digest,
            "node_context": normalized_node,
            "human_comment": clean_comment,
            "intent_trace": summary,
            "refinement": refinement,
            "next_clarification_question": refinement["next_clarification_question"],
            "aura_response": response,
            "response_provenance": provenance,
            "recommended_action": (guide.get("recommended_actions") or [{}])[0],
            "available_actions": list(guide.get("available_actions") or [])[:6],
            "blocked_actions": list(guide.get("blocked_actions") or [])[:6],
            "confirmation_required": True,
            "gate_approval_required_after_confirmation": True,
            "approval_scope": "advance_existing_guarded_workflow_only",
            **self._authority_projection(),
            "_session": session,
            "_confirmation": None,
            "_created_identity": repo,
        }
        self.pending[proposal_id] = proposal
        while len(self.pending) > MAX_PENDING:
            oldest = next(iter(self.pending))
            self.pending.pop(oldest, None)
        self._record(
            {
                "proposal_id": proposal_id,
                "session_id": session.session_id,
                "status": status,
                "current_phase": phase,
                "stage_hint": identity["stage_hint"],
                "node_digest": node_digest,
                "created_at": created_at,
            }
        )
        return _public_proposal(proposal)

    def clarify(
        self,
        *,
        proposal_id: str,
        answer: str,
        current_node_context: dict[str, Any] | None = None,
        stage_hint: str = "",
        reviewer: str = "human_operator",
    ) -> dict[str, Any]:
        proposal = self.pending.get(str(proposal_id or ""))
        if proposal is None:
            return self._denial("gate_dialogue_proposal_not_found")
        stale = self._validate_context(
            proposal,
            current_node_context=current_node_context,
            stage_hint=stage_hint,
        )
        if stale:
            return stale
        session = proposal["_session"]
        if session.current_stage != "CLARIFICATION_REQUIRED":
            return self._denial("clarification_not_required", proposal=proposal)
        answer_value = _bounded_text(answer, 2000)
        if not answer_value:
            return self._denial("clarification_answer_required", proposal=proposal)

        unresolved = list(session.unresolved_ambiguities)
        current = _json_copy(unresolved.pop(0))
        answers = [
            *session.answers_received,
            {
                "question_id": current.get("question_id", ""),
                "question": current.get("question", ""),
                "answer": answer_value,
                "reviewer": _bounded_text(reviewer, 180) or "human_operator",
                "answered_at": time.time(),
            },
        ]
        definitions = [
            *session.candidate_definitions,
            {
                "term": f"clarification:{current.get('question_id', 'unknown')}",
                "means": [answer_value],
                "does_not_mean": [],
                "source_refs": [
                    f"human_answer:{stable_digest(answer_value)}",
                    session.session_id,
                ],
                "freshness": "CURRENT",
            },
        ]
        session = session.transition(
            "CLARIFICATION_REQUIRED",
            definitions=definitions,
            unresolved_ambiguities=unresolved,
            answers_received=answers,
        )
        if unresolved:
            status = "PENDING_CLARIFICATION"
        else:
            teach_back = _teach_back(
                session.candidate_positive_requirements,
                session.candidate_negative_requirements,
                session.candidate_guardrails,
            )
            session = session.transition(
                "TEACH_BACK_PENDING",
                teach_back=teach_back,
            )
            status = "PENDING_INTENT_CONFIRMATION"
        proposal["_session"] = session
        proposal["status"] = status
        proposal["refinement"] = self._refinement_projection(session)
        proposal["next_clarification_question"] = proposal["refinement"][
            "next_clarification_question"
        ]
        proposal["aura_response"] = (
            f"Clarification recorded: {answer_value}. "
            + (
                f"Next question: {proposal['next_clarification_question']['question']}"
                if proposal["next_clarification_question"]
                else "The bilateral teach-back is now ready for confirmation or correction."
            )
        )
        self._record(
            {
                "proposal_id": proposal["proposal_id"],
                "status": status,
                "event": "clarification_recorded",
                "reviewer": reviewer,
            }
        )
        return _public_proposal(proposal)

    def correct_intent(
        self,
        *,
        proposal_id: str,
        positive_requirements: Sequence[str] | None = None,
        negative_requirements: Sequence[str] | None = None,
        definitions: Sequence[Mapping[str, Any]] | None = None,
        added_guardrails: Sequence[str] = (),
        rejected_soft_guardrail_ids: Sequence[str] = (),
        current_node_context: dict[str, Any] | None = None,
        stage_hint: str = "",
        reviewer: str = "human_operator",
    ) -> dict[str, Any]:
        proposal = self.pending.get(str(proposal_id or ""))
        if proposal is None:
            return self._denial("gate_dialogue_proposal_not_found")
        stale = self._validate_context(
            proposal,
            current_node_context=current_node_context,
            stage_hint=stage_hint,
        )
        if stale:
            return stale
        session = proposal["_session"]
        if session.current_stage not in {
            "CLARIFICATION_REQUIRED",
            "TEACH_BACK_PENDING",
        }:
            return self._denial("intent_correction_not_admitted", proposal=proposal)

        positives = tuple(
            str(value).strip()
            for value in (
                positive_requirements
                if positive_requirements is not None
                else session.candidate_positive_requirements
            )
            if str(value).strip()
        )
        negatives = tuple(
            str(value).strip()
            for value in (
                negative_requirements
                if negative_requirements is not None
                else session.candidate_negative_requirements
            )
            if str(value).strip()
        )
        if not positives or not negatives:
            return self._denial(
                "correction_requires_both_intent_polarities", proposal=proposal
            )
        guardrails: list[dict[str, Any]] = []
        rejected = set(str(value) for value in rejected_soft_guardrail_ids)
        for raw in session.candidate_guardrails:
            item = _json_copy(raw)
            if item.get("guardrail_id") in rejected:
                if item.get("hardness") in {
                    "HARD_ARCHITECTURAL",
                    "HARD_AUTHORITY",
                    "DOMAIN_REQUIRED",
                }:
                    return self._denial(
                        "hard_guardrail_removal_forbidden", proposal=proposal
                    )
                item["human_disposition"] = "REJECTED_SOFT"
                item["human_note"] = f"Rejected by {reviewer} during correction."
            guardrails.append(item)
        for statement in added_guardrails:
            value = str(statement).strip()
            if not value:
                continue
            guardrails.append(
                GuardrailProposal.create(
                    statement=value,
                    source_class="HUMAN_ADDED",
                    source_refs=(
                        f"human:{reviewer}",
                        f"correction:{proposal['proposal_id']}",
                    ),
                    hardness="PROPOSED_DEFAULT",
                    enforcement_class="HUMAN_REVIEW",
                    affected_arenas=("CODING",),
                    rationale="Human-added bilateral intent guardrail.",
                    human_disposition=HumanGuardrailDisposition.ADDED,
                    human_note=f"Added by {reviewer}.",
                ).to_dict()
            )
        definition_values = (
            list(definitions)
            if definitions is not None
            else [_json_copy(item) for item in session.candidate_definitions]
        )
        corrections = [
            *session.answers_received,
            {
                "kind": "INTENT_CORRECTION",
                "reviewer": _bounded_text(reviewer, 180) or "human_operator",
                "corrected_at": time.time(),
                "positive_requirements_digest": stable_digest(list(positives)),
                "negative_requirements_digest": stable_digest(list(negatives)),
            },
        ]
        if session.current_stage == "TEACH_BACK_PENDING":
            synthetic = ClarificationQuestion.create(
                ambiguity_class=AmbiguityClass.DESIRED_OUTCOME,
                question="Apply the human correction and rebuild the paired teach-back.",
                why_it_changes_execution=(
                    "A corrected requirement changes the canonical intent digest."
                ),
                affected_requirements=(*positives, *negatives),
                required_human_answer=False,
            )
            session = session.transition(
                "CLARIFICATION_REQUIRED",
                positive_requirements=positives,
                negative_requirements=negatives,
                definitions=definition_values,
                guardrails=guardrails,
                unresolved_ambiguities=(synthetic,),
                answers_received=corrections,
            )
        else:
            session = session.transition(
                "CLARIFICATION_REQUIRED",
                positive_requirements=positives,
                negative_requirements=negatives,
                definitions=definition_values,
                guardrails=guardrails,
                unresolved_ambiguities=(),
                answers_received=corrections,
            )
        session = session.transition(
            "TEACH_BACK_PENDING",
            unresolved_ambiguities=(),
            teach_back=_teach_back(positives, negatives, guardrails),
        )
        proposal["_session"] = session
        proposal["status"] = "PENDING_INTENT_CONFIRMATION"
        proposal["refinement"] = self._refinement_projection(session)
        proposal["next_clarification_question"] = {}
        proposal["aura_response"] = (
            "The correction is recorded. Aura rebuilt the positive requirements, "
            "negative requirements, guardrails, definitions, and paired teach-back. "
            "Review the revised bilateral contract before confirmation."
        )
        self._record(
            {
                "proposal_id": proposal["proposal_id"],
                "status": proposal["status"],
                "event": "intent_corrected",
                "reviewer": reviewer,
            }
        )
        return _public_proposal(proposal)

    def confirm_intent(
        self,
        *,
        proposal_id: str,
        current_node_context: dict[str, Any] | None = None,
        stage_hint: str = "",
        reviewer: str = "human_operator",
        note: str = "",
    ) -> dict[str, Any]:
        proposal = self.pending.get(str(proposal_id or ""))
        if proposal is None:
            return self._denial("gate_dialogue_proposal_not_found")
        stale = self._validate_context(
            proposal,
            current_node_context=current_node_context,
            stage_hint=stage_hint,
        )
        if stale:
            return stale
        session = proposal["_session"]
        if session.current_stage != "TEACH_BACK_PENDING":
            return self._denial(
                "intent_not_ready_for_confirmation", proposal=proposal
            )
        repo = _repository_identity(self.repo_root)
        if not repo["clean"]:
            return self._denial(
                "repository_not_clean_for_confirmation",
                proposal=proposal,
                extra={"dirty_paths": repo["dirty_paths"]},
            )

        confirmed_guardrails: list[dict[str, Any]] = []
        for raw in session.candidate_guardrails:
            item = _json_copy(raw)
            hardness = item.get("hardness")
            disposition = item.get("human_disposition")
            if disposition == "DEFERRED":
                if hardness in {"HARD_ARCHITECTURAL", "HARD_AUTHORITY"}:
                    item["human_disposition"] = "ACKNOWLEDGED_HARD"
                else:
                    item["human_disposition"] = "CONFIRMED"
                item["human_note"] = _bounded_text(
                    note, 1200
                ) or f"Confirmed by {reviewer}."
            confirmed_guardrails.append(item)

        session = session.transition(
            "HUMAN_CONFIRMED",
            guardrails=confirmed_guardrails,
            confirmation_status=ConfirmationStatus.CONFIRMED,
        )
        authority = self._canonical_authority()
        allowed_paths, _ = _node_scope(proposal["node_context"])
        if not allowed_paths:
            allowed_paths = ("aura_arena_gate_dialogue.py",)
        runtime_profile_digest = stable_digest(
            {
                "workflow_id": proposal["workflow_id"],
                "phase": proposal["current_phase"],
                "phase_hash": proposal["phase_hash"],
                "stage_hint": proposal["stage_hint"],
                "node_digest": proposal["node_digest"],
            }
        )
        record_options = {
            "purpose": session.source_request,
            "user_meaning": " | ".join(
                session.candidate_positive_requirements
            ),
            "mode": "PROPOSE",
            "authority": authority,
            "constraints": tuple(
                item.get("statement", "")
                for item in confirmed_guardrails
                if item.get("statement")
            ),
            "acceptance_criteria": (
                "Every confirmed positive requirement has measured proof.",
                "Every confirmed negative requirement has a negative or preservation proof.",
                "The selected workflow gate remains separately human-approved.",
            ),
            "required_evidence": (
                "current confirmation receipt",
                "current source-tree and topology identity",
                "independent verification before consequential action",
            ),
            "risk_class": "bounded_gate_dialogue",
            "cost_budget": "bounded",
            "context_budget": "minimum_sufficient",
            "privacy_class": "PROJECT",
            "freshness_requirement": "CURRENT_HEAD",
            "output_contract": (
                "canonical bilateral records plus proposal-only gate recommendation"
            ),
        }
        _, ledger = compile_canonical_records(
            session,
            confirmation_ref=f"session:{session.session_id}",
            **record_options,
        )
        confirmation = IntentConfirmationReceipt.create(
            session_id=session.session_id,
            repository_head=session.repository_head,
            source_tree_digest=session.working_tree_digest,
            working_tree_clean_receipt=repo["clean_receipt"],
            source_request_digest=session.source_request_digest,
            positive_requirements=session.candidate_positive_requirements,
            negative_requirements=session.candidate_negative_requirements,
            semantic_ledger_digest=ledger.ledger_digest,
            guardrails=confirmed_guardrails,
            authority=authority,
            teach_back=PairedTeachBack.create(
                **{
                    key: value
                    for key, value in _json_copy(session.teach_back).items()
                    if key
                    in {
                        "will_do",
                        "will_not_do",
                        "will_preserve",
                        "will_stop_or_escalate_if",
                        "positive_examples",
                        "negative_examples",
                        "unresolved_assumptions",
                        "required_human_decisions",
                    }
                }
            ),
            allowed_paths=allowed_paths,
            runtime_profile_digest=runtime_profile_digest,
            human_reviewer=_bounded_text(reviewer, 180) or "human_operator",
            human_disposition="CONFIRMED",
            confirmed_at=time.time(),
            expires_at=session.expires_at,
            expires_or_stales_on=(
                "repository head changes",
                "source-tree digest changes",
                "workflow phase or phase evidence changes",
                "selected topology changes",
                "positive or negative requirement changes",
                "definition, guardrail, authority, allowed path, or runtime profile changes",
            ),
        )
        session = session.transition(
            "COMPILED",
            confirmation_receipt_id=confirmation.confirmation_id,
            confirmation_receipt=confirmation,
            confirmation_evidence={
                "source_tree_digest": session.working_tree_digest,
                "semantic_ledger_digest": ledger.ledger_digest,
                "authority": authority,
                "allowed_paths": allowed_paths,
                "runtime_profile_digest": runtime_profile_digest,
            },
        )
        bundle = compile_bilateral_canonical_bundle(
            session,
            confirmation,
            codemap_digest=repo["codemap_digest"],
            required_verifiers=("pytest", "Coding Waboose"),
            **record_options,
        )
        proposal["_session"] = session
        proposal["_confirmation"] = confirmation
        proposal["status"] = "INTENT_CONFIRMED_PENDING_GATE_APPROVAL"
        proposal["confirmation_receipt"] = confirmation.to_dict()
        proposal["canonical_bundle"] = bundle.to_dict()
        proposal["refinement"] = self._refinement_projection(session)
        proposal["next_clarification_question"] = {}
        proposal["aura_response"] = (
            "The human-confirmed bilateral intent is compiled into the canonical "
            "IntentPacket, SemanticLedger, and ArenaEvidenceSlice owners. The receipt "
            "is bound to this repository head, source-tree digest, workflow phase, "
            "topology selection, definitions, guardrails, authority, and allowed paths. "
            "A separate approval is still required before the existing guarded workflow "
            "may attempt its recommended action."
        )
        self._record(
            {
                "proposal_id": proposal["proposal_id"],
                "session_id": session.session_id,
                "confirmation_id": confirmation.confirmation_id,
                "status": proposal["status"],
                "event": "bilateral_intent_confirmed",
                "reviewer": reviewer,
            }
        )
        return _public_proposal(proposal)

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
        """Confirm/clarify through the legacy endpoint or approve the guarded gate.

        The HTTP server already exposes one approval route.  Explicit note prefixes keep
        clarification and confirmation as separate actions without adding a shadow route
        owner:
        - ``CLARIFY_INTENT:<answer>``
        - ``CONFIRM_INTENT:<human note>``
        """
        note_value = str(note or "")
        if note_value.startswith("CLARIFY_INTENT:"):
            return self.clarify(
                proposal_id=proposal_id,
                answer=note_value.split(":", 1)[1],
                current_node_context=current_node_context,
                stage_hint=stage_hint,
                reviewer=reviewer,
            )
        if note_value.startswith("CONFIRM_INTENT"):
            confirmation_note = (
                note_value.split(":", 1)[1] if ":" in note_value else ""
            )
            if not approved:
                return self._reject(
                    proposal_id=proposal_id,
                    current_node_context=current_node_context,
                    stage_hint=stage_hint,
                    reviewer=reviewer,
                    note=confirmation_note or "Intent confirmation rejected.",
                )
            return self.confirm_intent(
                proposal_id=proposal_id,
                current_node_context=current_node_context,
                stage_hint=stage_hint,
                reviewer=reviewer,
                note=confirmation_note,
            )

        proposal = self.pending.get(str(proposal_id or ""))
        if proposal is None:
            return self._denial("gate_dialogue_proposal_not_found")
        stale = self._validate_context(
            proposal,
            current_node_context=current_node_context,
            stage_hint=stage_hint,
        )
        if stale:
            return stale
        if not approved:
            return self._reject(
                proposal_id=proposal_id,
                current_node_context=current_node_context,
                stage_hint=stage_hint,
                reviewer=reviewer,
                note=note_value,
            )
        session = proposal["_session"]
        confirmation = proposal.get("_confirmation")
        if (
            session.current_stage != "COMPILED"
            or not isinstance(confirmation, IntentConfirmationReceipt)
            or proposal.get("status")
            != "INTENT_CONFIRMED_PENDING_GATE_APPROVAL"
        ):
            return self._denial(
                "intent_confirmation_required", proposal=proposal
            )

        decision_status = "APPROVED_FOR_NEXT_GUARDED_GATE"
        decision = {
            "proposal_id": proposal["proposal_id"],
            "session_id": session.session_id,
            "confirmation_id": confirmation.confirmation_id,
            "canonical_bundle_id": str(
                (proposal.get("canonical_bundle") or {}).get("bundle_id") or ""
            ),
            "status": decision_status,
            "approved": True,
            "reviewer": _bounded_text(reviewer, 180) or "human_operator",
            "note": _bounded_text(note_value, 1200),
            "reviewed_at": time.time(),
            "workflow_id": proposal["workflow_id"],
            "current_phase": proposal["current_phase"],
            "stage_hint": proposal["stage_hint"],
            "phase_hash": proposal["phase_hash"],
            "repository_head": proposal["repository_head"],
            "source_tree_digest": proposal["source_tree_digest"],
            "node_digest": proposal["node_digest"],
            "human_comment_digest": _digest(proposal["human_comment"]),
            "recommended_action_id": str(
                (proposal.get("recommended_action") or {}).get("action_id") or ""
            ),
            "advance_authority": "existing_guarded_workflow_only",
            **self._authority_projection(),
        }
        proposal["status"] = decision_status
        proposal["decision"] = decision
        self.pending.pop(proposal["proposal_id"], None)
        self._record(decision)

        ledger = list(self.workflow.evidence.get("approved_gate_intents") or [])
        ledger.append(decision)
        self.workflow.evidence["approved_gate_intents"] = ledger[-40:]
        if hasattr(self.workflow, "_event"):
            self.workflow._event(
                "gate_dialogue_approval",
                (
                    f"{proposal['stage_hint']}:{proposal['proposal_id']}:"
                    f"{decision['recommended_action_id']}"
                ),
            )
        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal["proposal_id"],
            "session_id": session.session_id,
            "confirmation_id": confirmation.confirmation_id,
            "status": decision_status,
            "approved": True,
            "decision": decision,
            "next_action": proposal.get("recommended_action") or {},
            "workflow": self.workflow.get_state(),
            "note": (
                "Human gate approval recorded. The existing guarded workflow may now "
                "attempt only the recommended action."
            ),
            **self._authority_projection(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "pending": [_public_proposal(item) for item in list(self.pending.values())[-10:]],
            "history": self.history[-30:],
            "multi_turn_clarification": True,
            "separate_intent_confirmation": True,
            "canonical_intent_owner": "aura_unified_memory_continuity.IntentPacket",
            "canonical_semantic_owner": "aura_unified_memory_continuity.SemanticLedger",
            "approval_required": True,
            **self._authority_projection(),
        }

    def _validate_context(
        self,
        proposal: Mapping[str, Any],
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
        if (
            proposal.get("node_context", {}).get("selected_node")
            and not normalized_node.get("selected_node")
        ):
            return self._denial(
                "current_topology_node_required", proposal=proposal
            )
        if _digest(normalized_node) != proposal.get("node_digest"):
            return self._denial("stale_topology_selection", proposal=proposal)
        if _bounded_text(stage_hint, 120) != str(
            proposal.get("stage_hint") or ""
        ):
            return self._denial("stale_tour_gate", proposal=proposal)
        try:
            repo = _repository_identity(self.repo_root)
        except ValueError:
            return self._denial(
                "exact_repository_identity_unavailable", proposal=proposal
            )
        if repo["repository_head"] != proposal.get("repository_head"):
            return self._denial("stale_repository_head", proposal=proposal)
        if repo["working_tree_digest"] != proposal.get("source_tree_digest"):
            return self._denial("stale_source_tree_digest", proposal=proposal)
        session = proposal.get("_session")
        if isinstance(session, IntentRefinementSession) and not session.is_current(
            repository_head=repo["repository_head"],
            working_tree_digest=repo["working_tree_digest"],
        ):
            return self._denial(
                "stale_or_expired_refinement_session", proposal=proposal
            )
        return None

    def _reject(
        self,
        *,
        proposal_id: str,
        current_node_context: dict[str, Any] | None,
        stage_hint: str,
        reviewer: str,
        note: str,
    ) -> dict[str, Any]:
        proposal = self.pending.get(str(proposal_id or ""))
        if proposal is None:
            return self._denial("gate_dialogue_proposal_not_found")
        stale = self._validate_context(
            proposal,
            current_node_context=current_node_context,
            stage_hint=stage_hint,
        )
        if stale:
            return stale
        session = proposal["_session"]
        if session.current_stage not in {"REJECTED", "EXPIRED", "STALE"}:
            try:
                session = session.transition("REJECTED")
            except ValueError:
                session = replace(
                    session,
                    current_stage="REJECTED",
                    confirmation_status="REJECTED",
                )
        decision = {
            "proposal_id": proposal["proposal_id"],
            "session_id": session.session_id,
            "status": "REJECTED_BY_HUMAN",
            "approved": False,
            "reviewer": _bounded_text(reviewer, 180) or "human_operator",
            "note": _bounded_text(note, 1200),
            "reviewed_at": time.time(),
            "advance_authority": "none",
            **self._authority_projection(),
        }
        self.pending.pop(proposal["proposal_id"], None)
        self._record(decision)
        return {
            "ok": True,
            "version": GATE_DIALOGUE_VERSION,
            "proposal_id": proposal["proposal_id"],
            "session_id": session.session_id,
            "status": "REJECTED_BY_HUMAN",
            "approved": False,
            "decision": decision,
            "next_action": {},
            "workflow": self.workflow.get_state(),
            "note": "The bilateral intent proposal was rejected. No workflow action executed.",
            **self._authority_projection(),
        }

    def _optional_voice(
        self,
        *,
        deterministic_response: str,
        packet: Mapping[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        provenance = {
            "model_used": False,
            "provider": "deterministic_local",
            "model": "none",
            "latency_sec": 0.0,
            "fallback_reason": "",
            "deterministic_route_authoritative": True,
        }
        try:
            configured = available_providers()
            if not configured:
                provenance["fallback_reason"] = "no_configured_external_provider"
                return deterministic_response, provenance
            llm = ExternalLLM(
                model="cheap",
                task="human_agent_bilateral_gate_dialogue",
                aspect=str(packet.get("current_phase") or "frame").lower(),
            )
            text, error, latency_sec = llm.generate(
                _model_prompt(dict(packet)),
                max_tokens=500,
                temperature=0.0,
                resonance_egress=False,
                call_type="human_agent_bilateral_gate_dialogue",
            )
            if text and not error:
                provenance.update(
                    {
                        "model_used": True,
                        "provider": llm.provider,
                        "model": llm.model,
                        "latency_sec": round(float(latency_sec), 4),
                    }
                )
                return str(text).strip(), provenance
            provenance["fallback_reason"] = "external_voice_unavailable"
        except Exception:  # noqa: BLE001
            provenance["fallback_reason"] = "external_voice_unavailable"
        return deterministic_response, provenance

    @staticmethod
    def _canonical_authority() -> dict[str, bool]:
        return {
            "inspect": True,
            "edit": False,
            "test": False,
            "commit": False,
            "publish_pr": False,
            "merge": False,
            "production_mutation": False,
        }

    @staticmethod
    def _authority_projection() -> dict[str, Any]:
        return {
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "automatic_promotion": False,
            "professional_authority": False,
            "physical_work_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    @staticmethod
    def _refinement_projection(
        session: IntentRefinementSession,
    ) -> dict[str, Any]:
        guardrails = [_json_copy(item) for item in session.candidate_guardrails]
        hard = [
            item
            for item in guardrails
            if item.get("hardness")
            in {"HARD_ARCHITECTURAL", "HARD_AUTHORITY", "DOMAIN_REQUIRED"}
        ]
        editable = [
            item
            for item in guardrails
            if item.get("hardness") in {"PROPOSED_DEFAULT", "SOFT_PREFERENCE"}
        ]
        human_added = [
            item
            for item in guardrails
            if item.get("source_class") == "HUMAN_ADDED"
        ]
        unresolved = [
            _json_copy(item) for item in session.unresolved_ambiguities
        ]
        return {
            "session_id": session.session_id,
            "stage": session.current_stage,
            "confirmation_status": session.confirmation_status,
            "positive_requirements": list(
                session.candidate_positive_requirements
            ),
            "negative_requirements": list(
                session.candidate_negative_requirements
            ),
            "definitions": [
                _json_copy(item) for item in session.candidate_definitions
            ],
            "unresolved_ambiguities": unresolved,
            "next_clarification_question": unresolved[0] if unresolved else {},
            "hard_guardrails": hard,
            "editable_guardrails": editable,
            "human_added_guardrails": human_added,
            "paired_teach_back": _json_copy(session.teach_back)
            if session.teach_back
            else {},
            "confirmation_receipt_id": session.confirmation_receipt_id,
            "hard_guardrails_removable": False,
            "human_correction_supported": True,
        }

    def _record(self, item: dict[str, Any]) -> None:
        self.history.append(_json_copy(item))
        self.history = self.history[-MAX_HISTORY:]

    @classmethod
    def _denial(
        cls,
        reason: str,
        *,
        proposal: Mapping[str, Any] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "reason": str(reason),
            "status": "DENIED",
            "proposal_id": str((proposal or {}).get("proposal_id") or ""),
            "session_id": str((proposal or {}).get("session_id") or ""),
            "fail_closed": True,
            **cls._authority_projection(),
            **dict(extra or {}),
        }


__all__ = [
    "ArenaGateDialogueService",
    "GATE_DIALOGUE_VERSION",
    "normalize_node_context",
]
