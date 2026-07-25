"""Canonical compiler for confirmed bilateral Gate Dialogue intent.

This module is a bounded companion over Aura's existing refinement and unified
memory/continuity owners.  It creates no parallel memory, truth, policy,
routing, verification, patch, publication, production, or learning authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest
from aura_intent_refinement import (
    AmbiguityClass,
    ClarificationQuestion,
    GuardrailProposal,
    HumanGuardrailDisposition,
    IntentConfirmationReceipt,
    IntentRefinementSession,
    NegativeRequirement,
    PairedTeachBack,
    compile_default_guardrails,
    detect_requirement_contradictions,
    extract_negative_requirements,
)
from aura_unified_memory_continuity import (
    AuthorityEnvelope,
    IntentPacket,
    SemanticDefinition,
    SemanticLedger,
)

VERSION = "AURA_BILATERAL_CANONICAL_COMPILER_V1"
MEMORY_OWNER = TRUTH_OWNER = POLICY_OWNER = ROUTING_OWNER = False
VERIFICATION_OWNER = PATCH_AUTHORITY_GRANTED = PRODUCTION_MUTATION = False
HUMAN_CONFIRMATION_REQUIRED = True


@dataclass(frozen=True)
class BilateralAnalysis:
    source_request: str
    positive_requirements: tuple[str, ...]
    negative_requirements: tuple[NegativeRequirement, ...]
    guardrails: tuple[GuardrailProposal, ...]
    questions: tuple[ClarificationQuestion, ...]
    teach_back: PairedTeachBack | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "source_request": self.source_request,
            "positive_requirements": list(self.positive_requirements),
            "negative_requirements": [item.to_dict() for item in self.negative_requirements],
            "guardrails": [item.to_dict() for item in self.guardrails],
            "questions": [item.to_dict() for item in self.questions],
            "teach_back": self.teach_back.to_dict() if self.teach_back else {},
            "authority": _authority_projection(),
        }


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must not be empty")
    return text


def _strings(values: Sequence[Any], name: str, *, required: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    result = tuple(dict.fromkeys(_required(item, name) for item in values))
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _sentences(text: str) -> tuple[str, ...]:
    source = _required(text, "source_request")
    result: list[str] = []
    start = 0
    for index, char in enumerate(source):
        if char in ".!?\n":
            value = source[start:index + 1].strip()
            if value:
                result.append(value)
            start = index + 1
    tail = source[start:].strip()
    if tail:
        result.append(tail)
    return tuple(result)


def _positive_requirements(source_request: str, negatives: Sequence[NegativeRequirement]) -> tuple[str, ...]:
    negative_spans = {item.source_span for item in negatives}
    positives = tuple(
        sentence
        for sentence in _sentences(source_request)
        if sentence not in negative_spans and not extract_negative_requirements(sentence)
    )
    return positives or (_required(source_request, "source_request"),)


def _resolved_guardrails(guardrails: Sequence[GuardrailProposal]) -> tuple[GuardrailProposal, ...]:
    resolved: list[GuardrailProposal] = []
    for item in guardrails:
        if item.hardness in {"HARD_ARCHITECTURAL", "HARD_AUTHORITY"}:
            disposition = HumanGuardrailDisposition.ACKNOWLEDGED_HARD
        else:
            disposition = HumanGuardrailDisposition.CONFIRMED
        resolved.append(item.with_human_disposition(disposition))
    return tuple(resolved)


def _teach_back(
    positive_requirements: Sequence[str],
    negative_requirements: Sequence[NegativeRequirement],
    guardrails: Sequence[GuardrailProposal],
) -> PairedTeachBack:
    negative = tuple(item.statement for item in negative_requirements)
    hard = tuple(item.statement for item in guardrails if item.is_hard)
    editable = tuple(item.statement for item in guardrails if not item.is_hard)
    return PairedTeachBack.create(
        will_do=_strings(positive_requirements, "positive_requirements", required=True),
        will_not_do=negative or ("Do not exceed the confirmed authority or bounded repository scope.",),
        will_preserve=(
            "Exact-source and human-review authority remain canonical.",
            "The selected topology evidence remains navigation evidence, not patch authority.",
        ),
        will_stop_or_escalate_if=(
            "Repository head, selected topology, workflow phase, meaning, authority, or scope changes.",
            "A required verifier, definition, or exact source reference is missing.",
        ),
        positive_examples=(positive_requirements[0],),
        negative_examples=((negative or hard or editable)[0],),
    )


def analyze_bilateral_request(
    source_request: str,
    *,
    arena: str = "HUMAN_AGENT",
    affected_files: Sequence[str] = (),
    affected_symbols: Sequence[str] = (),
    supplied_positive_requirements: Sequence[str] = (),
    supplied_negative_requirements: Sequence[str] = (),
) -> BilateralAnalysis:
    source = _required(source_request, "source_request")
    parsed_negatives = list(extract_negative_requirements(source))
    for statement in _strings(supplied_negative_requirements, "supplied_negative_requirements"):
        if statement not in {item.statement for item in parsed_negatives}:
            parsed_negatives.extend(extract_negative_requirements(statement))
    positives = tuple(
        dict.fromkeys(
            [
                *_strings(supplied_positive_requirements, "supplied_positive_requirements"),
                *_positive_requirements(source, parsed_negatives),
            ]
        )
    )
    guardrails = compile_default_guardrails(
        arena=arena,
        affected_files=affected_files,
        affected_symbols=affected_symbols,
    )
    questions: list[ClarificationQuestion] = []
    ambiguous = [item for item in parsed_negatives if item.ambiguous]
    if ambiguous:
        item = ambiguous[0]
        questions.append(
            ClarificationQuestion.create(
                ambiguity_class=AmbiguityClass.PROHIBITED_OUTCOME,
                question="What exact outcome must Aura not produce?",
                why_it_changes_execution="The current negative phrase has no exact operational target.",
                affected_requirements=(item.requirement_id,),
            )
        )
    contradictions = detect_requirement_contradictions(positives, parsed_negatives)
    if contradictions:
        conflict = contradictions[0]
        questions.append(
            ClarificationQuestion.create(
                ambiguity_class=AmbiguityClass.CONTRADICTION,
                question="Which requirement controls this conflict?",
                why_it_changes_execution=(
                    "The same bounded behavior appears in both required and prohibited intent."
                ),
                candidate_answers=(
                    conflict["positive_requirement"],
                    conflict["negative_requirement"],
                ),
            )
        )
    if not parsed_negatives:
        questions.append(
            ClarificationQuestion.create(
                ambiguity_class=AmbiguityClass.PROHIBITED_OUTCOME,
                question="What must Aura explicitly not do?",
                why_it_changes_execution=(
                    "A bilateral confirmation requires explicit prohibited behavior or a human statement that only hard defaults apply."
                ),
                candidate_answers=(
                    "Only the locked hard defaults apply.",
                    "Do not expand beyond the selected topology scope.",
                ),
            )
        )
    teach_back = None if questions else _teach_back(positives, parsed_negatives, guardrails)
    return BilateralAnalysis(
        source_request=source,
        positive_requirements=positives,
        negative_requirements=tuple(parsed_negatives),
        guardrails=tuple(guardrails),
        questions=tuple(questions),
        teach_back=teach_back,
    )


def apply_clarification(
    analysis: BilateralAnalysis,
    *,
    question: ClarificationQuestion,
    answer: str,
) -> BilateralAnalysis:
    value = _required(answer, "clarification answer")
    positives = list(analysis.positive_requirements)
    negatives = list(analysis.negative_requirements)
    if question.ambiguity_class == AmbiguityClass.PROHIBITED_OUTCOME.value:
        if value.casefold() == "only the locked hard defaults apply.":
            value = "Do not exceed the locked hard architectural and authority guardrails."
        extracted = extract_negative_requirements(value)
        if extracted:
            negatives.extend(item for item in extracted if item.statement not in {row.statement for row in negatives})
        else:
            normalized = f"Do not {value[0].lower() + value[1:] if len(value) > 1 else value.lower()}"
            negatives.extend(extract_negative_requirements(normalized))
    elif question.ambiguity_class == AmbiguityClass.DESIRED_OUTCOME.value:
        positives.append(value)
    elif question.ambiguity_class == AmbiguityClass.CONTRADICTION.value:
        candidates = tuple(question.candidate_answers)
        if len(candidates) != 2 or value not in candidates:
            raise ValueError(
                "contradiction clarification must select one declared requirement"
            )
        positive_candidate, negative_candidate = candidates
        if value == positive_candidate:
            negatives = [
                item
                for item in negatives
                if item.statement != negative_candidate
                and item.target != negative_candidate
            ]
        else:
            positives = [
                item for item in positives if item != positive_candidate
            ]
            if not positives:
                positives = [
                    "Preserve the confirmed prohibition and locked guardrails."
                ]
    remaining = tuple(item for item in analysis.questions if item.question_id != question.question_id)
    teach_back = None if remaining else _teach_back(positives, negatives, analysis.guardrails)
    return BilateralAnalysis(
        source_request=analysis.source_request,
        positive_requirements=tuple(dict.fromkeys(positives)),
        negative_requirements=tuple(negatives),
        guardrails=analysis.guardrails,
        questions=remaining,
        teach_back=teach_back,
    )


def create_refinement_session(
    analysis: BilateralAnalysis,
    *,
    repository_head: str,
    working_tree_digest: str,
    arena: str,
    created_at: float,
    expires_at: float,
) -> IntentRefinementSession:
    session = IntentRefinementSession.create(
        repository_head=repository_head,
        working_tree_digest=working_tree_digest,
        arena=arena,
        source_request=analysis.source_request,
        created_at=created_at,
        expires_at=expires_at,
    )
    questions = tuple(item.to_dict() for item in analysis.questions)
    session = session.transition(
        "ANALYZED",
        positive_requirements=analysis.positive_requirements,
        negative_requirements=tuple(item.statement for item in analysis.negative_requirements),
        guardrails=tuple(item.to_dict() for item in analysis.guardrails),
        unresolved_ambiguities=questions,
        questions_asked=questions,
        now=created_at,
    )
    if analysis.questions:
        return session.transition("CLARIFICATION_REQUIRED", now=created_at)
    if analysis.teach_back is None:
        raise ValueError("teach-back is required when clarification is complete")
    return session.transition("TEACH_BACK_PENDING", teach_back=analysis.teach_back, now=created_at)


def refresh_refinement_session(
    session: IntentRefinementSession,
    analysis: BilateralAnalysis,
    *,
    answer: str,
    observed_at: float,
) -> IntentRefinementSession:
    if session.current_stage != "CLARIFICATION_REQUIRED":
        raise ValueError("clarification answer requires a clarification-pending session")
    answers = [*session.answers_received, {"answer": _required(answer, "answer"), "received_at": observed_at}]
    questions = tuple(item.to_dict() for item in analysis.questions)
    target = "CLARIFICATION_REQUIRED" if questions else "TEACH_BACK_PENDING"
    return session.transition(
        target,
        positive_requirements=analysis.positive_requirements,
        negative_requirements=tuple(item.statement for item in analysis.negative_requirements),
        guardrails=tuple(item.to_dict() for item in analysis.guardrails),
        unresolved_ambiguities=questions,
        questions_asked=questions,
        answers_received=answers,
        teach_back=analysis.teach_back,
        now=observed_at,
    )


def compile_confirmed_bilateral_intent(
    *,
    session: IntentRefinementSession,
    analysis: BilateralAnalysis,
    repository_head: str,
    source_tree_digest: str,
    working_tree_clean_receipt: str,
    allowed_paths: Sequence[str],
    runtime_profile_digest: str,
    human_reviewer: str,
    confirmed_at: float,
    expires_at: float,
    arena: str = "Human Agent",
) -> dict[str, Any]:
    if session.current_stage != "TEACH_BACK_PENDING" or analysis.teach_back is None:
        raise ValueError("intent must complete clarification and teach-back before confirmation")
    paths = _strings(allowed_paths, "allowed_paths", required=True)
    resolved_guardrails = _resolved_guardrails(analysis.guardrails)
    prohibitions = tuple(
        dict.fromkeys(
            [
                *(item.statement for item in analysis.negative_requirements),
                *(item.statement for item in resolved_guardrails if item.is_hard),
            ]
        )
    )
    authority = AuthorityEnvelope(inspect=True)
    intent = IntentPacket.create(
        objective=analysis.positive_requirements[0],
        purpose="Preserve the human-confirmed bilateral meaning at the selected guarded workflow gate.",
        user_meaning=analysis.source_request,
        mode="PROPOSE",
        arena=arena,
        constraints=tuple(item.statement for item in resolved_guardrails if not item.is_hard),
        prohibitions=prohibitions,
        authority=authority,
        acceptance_criteria=analysis.positive_requirements,
        required_evidence=(
            "current human confirmation receipt",
            "current selected topology identity",
            "independent verification before consequential execution",
        ),
        risk_class="BOUNDED_GATE_DIALOGUE",
        cost_budget="BOUNDED",
        context_budget="MINIMUM_SUFFICIENT",
        privacy_class="PROJECT",
        freshness_requirement="CURRENT_HEAD",
        output_contract="proposal-only canonical bilateral intent references",
    )
    source_ref = f"intent-refinement:{session.session_id}"
    definitions = (
        SemanticDefinition(
            term="confirmed gate intent",
            means=("the positive and negative requirements in the current confirmation receipt",),
            does_not_mean=("patch, commit, push, merge, deployment, or production authority",),
            source_refs=(source_ref,),
        ),
        SemanticDefinition(
            term="topology evidence",
            means=("bounded navigation evidence tied to the selected node and current repository identity",),
            does_not_mean=("visual patch authority or permission to widen scope",),
            source_refs=(source_ref,),
        ),
        SemanticDefinition(
            term="human approval",
            means=("confirmation of the interpreted intent for the existing guarded workflow only",),
            does_not_mean=("automatic execution or durable learning promotion",),
            source_refs=(source_ref,),
        ),
    )
    ledger = SemanticLedger.create(intent_digest=intent.intent_digest, definitions=definitions)
    confirmed_session = session.transition(
        "HUMAN_CONFIRMED",
        positive_requirements=analysis.positive_requirements,
        negative_requirements=tuple(item.statement for item in analysis.negative_requirements),
        guardrails=tuple(item.to_dict() for item in resolved_guardrails),
        unresolved_ambiguities=(),
        teach_back=analysis.teach_back,
        confirmation_status="CONFIRMED",
        now=confirmed_at,
    )
    receipt = IntentConfirmationReceipt.create(
        session_id=confirmed_session.session_id,
        repository_head=repository_head,
        source_tree_digest=source_tree_digest,
        working_tree_clean_receipt=working_tree_clean_receipt,
        source_request_digest=confirmed_session.source_request_digest,
        positive_requirements=analysis.positive_requirements,
        negative_requirements=tuple(item.statement for item in analysis.negative_requirements),
        semantic_ledger_digest=ledger.ledger_digest,
        guardrails=resolved_guardrails,
        authority=authority.to_dict(),
        teach_back=analysis.teach_back,
        allowed_paths=paths,
        runtime_profile_digest=runtime_profile_digest,
        human_reviewer=human_reviewer,
        human_disposition="CONFIRMED",
        confirmed_at=confirmed_at,
        expires_at=expires_at,
        expires_or_stales_on=(
            "repository head changes",
            "source tree digest changes",
            "selected topology identity changes",
            "workflow phase changes",
            "semantic definitions change",
            "positive or negative requirements change",
            "guardrail set or authority changes",
        ),
    )
    compiled_session = confirmed_session.transition(
        "COMPILED",
        confirmation_receipt_id=receipt.confirmation_id,
        confirmation_receipt=receipt,
        confirmation_evidence={
            "source_tree_digest": source_tree_digest,
            "semantic_ledger_digest": ledger.ledger_digest,
            "authority": authority.to_dict(),
            "allowed_paths": list(paths),
            "runtime_profile_digest": runtime_profile_digest,
        },
        now=confirmed_at,
    )
    u7_refs = {
        "confirmation_digest": receipt.confirmation_id,
        "negative_requirements_digest": receipt.negative_requirements_digest,
        "guardrail_set_digest": receipt.guardrail_set_digest,
        "intent_revision_id": "",
        "incident_replay_digest": "",
        "observed_guardrail_violation_refs": [],
        "proposal_only": True,
        "current_reproof_required_before_learning": True,
    }
    execution_refs = {
        "intent_packet_owner": "aura_unified_memory_continuity.IntentPacket",
        "semantic_ledger_owner": "aura_unified_memory_continuity.SemanticLedger",
        "arena_evidence_slice_owner": "aura_unified_memory_continuity.ArenaEvidenceSlice",
        "act_capsule_envelope_owner": "aura_unified_memory_continuity.ActCapsuleEnvelope",
        "unified_execution_binding_owner": (
            "aura_unified_memory_continuity_toolchain.UnifiedExecutionBinding"
        ),
        "binding_status": "PENDING_PLAN_CAPSULE_AND_EXACT_EVIDENCE",
        "confirmation_ref": receipt.confirmation_id,
        "intent_digest": intent.intent_digest,
        "semantic_ledger_digest": ledger.ledger_digest,
    }
    return {
        "version": VERSION,
        "intent_packet": intent.to_dict(),
        "semantic_ledger": ledger.to_dict(),
        "confirmation_receipt": receipt.to_dict(),
        "refinement_session": compiled_session.to_dict(),
        "guardrails": [item.to_dict() for item in resolved_guardrails],
        "execution_references": execution_refs,
        "u7_references": u7_refs,
        "authority": _authority_projection(),
    }


def _authority_projection() -> dict[str, Any]:
    return {
        "memory_owner": MEMORY_OWNER,
        "truth_owner": TRUTH_OWNER,
        "policy_owner": POLICY_OWNER,
        "routing_owner": ROUTING_OWNER,
        "verification_owner": VERIFICATION_OWNER,
        "patch_authority": PATCH_AUTHORITY_GRANTED,
        "production_mutation": PRODUCTION_MUTATION,
        "human_confirmation_required": HUMAN_CONFIRMATION_REQUIRED,
        "exact_patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
        "automatic_learning_promotion": False,
    }


def bilateral_compiler_capabilities() -> dict[str, Any]:
    return {"version": VERSION, **_authority_projection()}


__all__ = [
    "BilateralAnalysis",
    "VERSION",
    "analyze_bilateral_request",
    "apply_clarification",
    "bilateral_compiler_capabilities",
    "compile_confirmed_bilateral_intent",
    "create_refinement_session",
    "refresh_refinement_session",
]
