"""Canonical bilateral-intent compilation for AuraOS.

This companion compiles a current, human-confirmed refinement session into Aura's
existing IntentPacket, SemanticLedger, and ArenaEvidenceSlice owners.  It carries
reference-only Act-envelope, unified-execution, and U7 bindings without creating
another intent, memory, truth, policy, verifier, learning, or authority plane.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, canonical_json, stable_digest
from aura_intent_refinement import (
    IntentConfirmationReceipt,
    IntentRefinementSession,
)
from aura_unified_memory_continuity import (
    ActCapsuleEnvelope,
    ArenaEvidenceItem,
    ArenaEvidenceSlice,
    AuthorityEnvelope,
    EvidenceTruthClass,
    IntentPacket,
    SemanticDefinition,
    SemanticLedger,
    compile_act_capsule_envelope,
    compile_arena_evidence_slice,
)

VERSION = "AURA_BILATERAL_CANONICAL_BINDING_V1"
OWNER_REFS = MappingProxyType({
    "intent_packet": "aura_unified_memory_continuity.IntentPacket",
    "semantic_ledger": "aura_unified_memory_continuity.SemanticLedger",
    "arena_evidence_slice": "aura_unified_memory_continuity.ArenaEvidenceSlice",
    "act_capsule_envelope": "aura_unified_memory_continuity.ActCapsuleEnvelope",
    "unified_execution_binding": (
        "aura_unified_memory_continuity_toolchain.UnifiedExecutionBinding"
    ),
    "u7_learning_to_reproof": (
        "aura_unified_memory_continuity_learning.GovernedLearningToReproof"
    ),
})
FORBIDDEN_AUTHORITY = MappingProxyType({
    "memory_owner": False,
    "truth_owner": False,
    "policy_owner": False,
    "routing_owner": False,
    "verification_owner": False,
    "patch_authority": PATCH_AUTHORITY,
    "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    "automatic_commit": False,
    "automatic_push": False,
    "automatic_pull_request": False,
    "automatic_merge": False,
    "automatic_promotion": False,
    "production_mutation": False,
})


def _required(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _strings(values: Sequence[Any], name: str, *, required: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    result = tuple(dict.fromkeys(_required(value, name) for value in values))
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _record(value: Any, name: str) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object or to_dict record")
    normalized = json.loads(canonical_json(dict(value)))
    if not isinstance(normalized, dict):
        raise ValueError(f"{name} must normalize to an object")
    return normalized


def _authority(value: AuthorityEnvelope | Mapping[str, Any] | None) -> AuthorityEnvelope:
    if value is None:
        return AuthorityEnvelope(inspect=True)
    if isinstance(value, AuthorityEnvelope):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("authority must use AuthorityEnvelope or an object")
    allowed = set(AuthorityEnvelope.__dataclass_fields__)
    if set(value) - allowed:
        raise ValueError("authority contains unknown fields")
    normalized: dict[str, bool] = {}
    for name in allowed:
        item = value.get(name, False)
        if type(item) is not bool:
            raise ValueError(f"authority.{name} must be a boolean")
        normalized[name] = item
    return AuthorityEnvelope(**normalized)


def _active_guardrails(session: IntentRefinementSession) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for raw in session.candidate_guardrails:
        item = _record(raw, "guardrail")
        if item.get("human_disposition") == "REJECTED_SOFT":
            continue
        result.append(item)
    return tuple(result)


def _definitions(
    session: IntentRefinementSession,
    *,
    confirmation_ref: str,
) -> tuple[SemanticDefinition, ...]:
    definitions: list[SemanticDefinition] = []
    for raw in session.candidate_definitions:
        item = _record(raw, "definition")
        definitions.append(
            SemanticDefinition(
                term=_required(item.get("term"), "definition.term"),
                means=_strings(item.get("means") or (), "definition.means", required=True),
                does_not_mean=_strings(
                    item.get("does_not_mean") or (), "definition.does_not_mean"
                ),
                source_refs=_strings(
                    item.get("source_refs") or (confirmation_ref,),
                    "definition.source_refs",
                    required=True,
                ),
                freshness=str(item.get("freshness") or "CURRENT"),
            )
        )
    required_defaults = (
        SemanticDefinition(
            term="confirmed intent",
            means=session.candidate_positive_requirements,
            does_not_mean=session.candidate_negative_requirements,
            source_refs=(confirmation_ref, f"request:{session.source_request_digest}"),
        ),
        SemanticDefinition(
            term="authority",
            means=("Only the canonical AuthorityEnvelope grants an allowed capability.",),
            does_not_mean=(
                "Human confirmation grants no undeclared patch, commit, push, merge, "
                "deployment, production, professional, or learning-promotion authority.",
            ),
            source_refs=(confirmation_ref, "aura_unified_memory_continuity.AuthorityEnvelope"),
        ),
        SemanticDefinition(
            term="guardrail",
            means=("A confirmed constraint or prohibition bound to this exact intent.",),
            does_not_mean=("A parallel policy, truth, verification, or promotion owner.",),
            source_refs=(confirmation_ref, "aura_intent_refinement.GuardrailProposal"),
        ),
        SemanticDefinition(
            term="verification",
            means=("Independent measured evidence required by the canonical execution owners.",),
            does_not_mean=("Model confidence, visual appearance, or self-verification.",),
            source_refs=(confirmation_ref, "aura_unified_memory_continuity.ArenaEvidenceSlice"),
        ),
    )
    existing = {item.term.casefold() for item in definitions}
    definitions.extend(item for item in required_defaults if item.term.casefold() not in existing)
    return tuple(definitions)


def compile_canonical_records(
    session: IntentRefinementSession,
    *,
    confirmation_ref: str,
    purpose: str = "",
    user_meaning: str = "",
    mode: str = "PROPOSE",
    authority: AuthorityEnvelope | Mapping[str, Any] | None = None,
    constraints: Sequence[str] = (),
    acceptance_criteria: Sequence[str] = (),
    required_evidence: Sequence[str] = (),
    risk_class: str = "bounded_intent_refinement",
    cost_budget: str = "bounded",
    context_budget: str = "minimum_sufficient",
    privacy_class: str = "PROJECT",
    freshness_requirement: str = "CURRENT_HEAD",
    output_contract: str = "canonical bilateral intent records plus immutable references",
) -> tuple[IntentPacket, SemanticLedger]:
    """Compile canonical records without granting execution authority."""
    if not isinstance(session, IntentRefinementSession):
        raise ValueError("session must use IntentRefinementSession")
    if session.current_stage not in {"HUMAN_CONFIRMED", "COMPILED"}:
        raise ValueError("canonical compilation requires a human-confirmed session")
    if session.confirmation_status != "CONFIRMED":
        raise ValueError("canonical compilation requires confirmed human disposition")
    if session.unresolved_ambiguities:
        raise ValueError("canonical compilation cannot contain unresolved ambiguities")
    if not session.candidate_positive_requirements or not session.candidate_negative_requirements:
        raise ValueError("canonical compilation requires both intent polarities")
    guardrails = _active_guardrails(session)
    deferred = [item["guardrail_id"] for item in guardrails if item.get("human_disposition") == "DEFERRED"]
    if deferred:
        raise ValueError(f"canonical compilation cannot contain deferred guardrails: {deferred}")
    guardrail_statements = tuple(
        _required(item.get("statement"), "guardrail.statement") for item in guardrails
    )
    prohibitions = tuple(
        dict.fromkeys([*session.candidate_negative_requirements, *guardrail_statements])
    )
    objective = session.candidate_positive_requirements[0]
    packet = IntentPacket.create(
        objective=objective,
        purpose=purpose.strip() or session.source_request,
        user_meaning=user_meaning.strip()
        or " | ".join(session.candidate_positive_requirements),
        mode=mode,
        arena=session.arena,
        constraints=tuple(dict.fromkeys([*_strings(constraints, "constraints"), *guardrail_statements])),
        prohibitions=prohibitions,
        authority=_authority(authority),
        acceptance_criteria=_strings(
            acceptance_criteria
            or (
                "Every confirmed positive requirement has measured proof.",
                "Every confirmed negative requirement has a negative or preservation proof.",
                "No authority boundary changes without human reconfirmation.",
            ),
            "acceptance_criteria",
            required=True,
        ),
        required_evidence=_strings(
            required_evidence
            or (
                "current confirmation receipt",
                "current source-tree identity",
                "positive and negative proof coverage",
                "independent verifier evidence before consequential execution",
            ),
            "required_evidence",
            required=True,
        ),
        risk_class=_required(risk_class, "risk_class"),
        cost_budget=_required(cost_budget, "cost_budget"),
        context_budget=_required(context_budget, "context_budget"),
        privacy_class=_required(privacy_class, "privacy_class"),
        freshness_requirement=_required(freshness_requirement, "freshness_requirement"),
        output_contract=_required(output_contract, "output_contract"),
    )
    ledger = SemanticLedger.create(
        intent_digest=packet.intent_digest,
        definitions=_definitions(session, confirmation_ref=confirmation_ref),
    )
    return packet, ledger


@dataclass(frozen=True)
class BilateralCanonicalBundle:
    bundle_id: str
    repository_head: str
    source_tree_digest: str
    confirmation_id: str
    intent_packet: Mapping[str, Any]
    semantic_ledger: Mapping[str, Any]
    arena_evidence_slice: Mapping[str, Any]
    act_capsule_envelope: Mapping[str, Any]
    unified_execution_binding_ref: str
    u7_references: Mapping[str, Any]
    owner_refs: Mapping[str, str]
    authority: Mapping[str, Any]
    bundle_digest: str
    version: str = VERSION

    def __post_init__(self) -> None:
        for name in (
            "bundle_id",
            "repository_head",
            "source_tree_digest",
            "confirmation_id",
            "bundle_digest",
        ):
            _required(getattr(self, name), name)
        if self.version != VERSION:
            raise ValueError("unsupported bilateral canonical bundle version")
        for name in (
            "intent_packet",
            "semantic_ledger",
            "arena_evidence_slice",
            "act_capsule_envelope",
            "u7_references",
            "owner_refs",
            "authority",
        ):
            object.__setattr__(self, name, MappingProxyType(_record(getattr(self, name), name)))
        if dict(self.authority) != dict(FORBIDDEN_AUTHORITY):
            raise ValueError("bilateral canonical bundle authority changed")
        expected = stable_digest(self.identity_payload())
        if self.bundle_digest != expected or self.bundle_id != f"bilateral_{expected}":
            raise ValueError("bilateral canonical bundle identity mismatch")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "repository_head": self.repository_head,
            "source_tree_digest": self.source_tree_digest,
            "confirmation_id": self.confirmation_id,
            "intent_packet": _record(self.intent_packet, "intent_packet"),
            "semantic_ledger": _record(self.semantic_ledger, "semantic_ledger"),
            "arena_evidence_slice": _record(
                self.arena_evidence_slice, "arena_evidence_slice"
            ),
            "act_capsule_envelope": _record(
                self.act_capsule_envelope, "act_capsule_envelope"
            ),
            "unified_execution_binding_ref": self.unified_execution_binding_ref,
            "u7_references": _record(self.u7_references, "u7_references"),
            "owner_refs": _record(self.owner_refs, "owner_refs"),
            "authority": _record(self.authority, "authority"),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            **self.identity_payload(),
            "bundle_digest": self.bundle_digest,
            "version": self.version,
        }


def compile_bilateral_canonical_bundle(
    session: IntentRefinementSession,
    confirmation: IntentConfirmationReceipt,
    *,
    codemap_digest: str,
    evidence_items: Sequence[ArenaEvidenceItem] = (),
    required_verifiers: Sequence[str] = ("pytest", "Coding Waboose"),
    unified_execution_binding_ref: str = "",
    intent_revision_id: str = "",
    legacy_act_capsule: Any | None = None,
    allowed_files: Sequence[str] = (),
    allowed_symbols: Sequence[str] = (),
    allowed_tools: Sequence[str] = (),
    repair_budget: int = 0,
    legal_outcomes: Sequence[str] = ("VERIFY", "ESCALATE", "REFUSE", "READY_FOR_HUMAN_REVIEW"),
    continuity_requirements: Sequence[str] = (
        "preserve the confirmed positive and negative intent digests",
        "stale confirmation when exact context changes",
        "require current reproof before consequential learning",
    ),
    **record_options: Any,
) -> BilateralCanonicalBundle:
    """Compile a receipt-bound, reference-only bilateral canonical bundle."""
    if not isinstance(session, IntentRefinementSession) or session.current_stage != "COMPILED":
        raise ValueError("bundle compilation requires a COMPILED IntentRefinementSession")
    if not isinstance(confirmation, IntentConfirmationReceipt):
        raise ValueError("confirmation must use IntentConfirmationReceipt")
    if session.confirmation_receipt_id != confirmation.confirmation_id:
        raise ValueError("session and confirmation receipt disagree")
    if not confirmation.has_valid_identity():
        raise ValueError("confirmation receipt identity is invalid")
    if time.time() >= confirmation.expires_at:
        raise ValueError("confirmation receipt is expired")
    if (
        confirmation.repository_head != session.repository_head
        or confirmation.source_tree_digest != session.working_tree_digest
        or confirmation.source_request_digest != session.source_request_digest
    ):
        raise ValueError("confirmation receipt is stale for the compiled session")
    intent, ledger = compile_canonical_records(
        session,
        confirmation_ref=f"session:{session.session_id}",
        **record_options,
    )
    if ledger.ledger_digest != confirmation.semantic_ledger_digest:
        raise ValueError("canonical SemanticLedger differs from the confirmed receipt")
    if intent.intent_digest == "":
        raise ValueError("canonical IntentPacket identity is empty")

    active_guardrails = _active_guardrails(session)
    if stable_digest(active_guardrails) != confirmation.guardrail_set_digest:
        raise ValueError("confirmed guardrail set changed before canonical binding")

    confirmation_item = ArenaEvidenceItem(
        evidence_ref=f"exact_receipt:intent_confirmation:{confirmation.confirmation_id}",
        causal_reason="Human confirmation binds the exact bilateral intent and guardrail set.",
        truth_class=EvidenceTruthClass.EXACT_RECEIPT,
        canonical_owner="aura_intent_refinement.IntentConfirmationReceipt",
        source_digest=confirmation.confirmation_id,
        freshness="CURRENT",
        required=True,
    )
    request_item = ArenaEvidenceItem(
        evidence_ref=f"exact_source:intent_request:{session.source_request_digest}",
        causal_reason="The original human request remains exact and recoverable.",
        truth_class=EvidenceTruthClass.EXACT_SOURCE,
        canonical_owner="aura_intent_refinement.IntentRefinementSession",
        source_digest=session.source_request_digest,
        freshness="CURRENT",
        required=True,
    )
    ledger_item = ArenaEvidenceItem(
        evidence_ref=f"exact_schema:semantic_ledger:{ledger.ledger_digest}",
        causal_reason="Canonical meanings and does-not-mean definitions govern interpretation.",
        truth_class=EvidenceTruthClass.EXACT_SCHEMA,
        canonical_owner="aura_unified_memory_continuity.SemanticLedger",
        source_digest=ledger.ledger_digest,
        freshness="CURRENT",
        required=True,
    )
    candidates = (confirmation_item, request_item, ledger_item, *tuple(evidence_items))
    required_refs = tuple(item.evidence_ref for item in candidates if item.required)
    arena_slice = compile_arena_evidence_slice(
        repository_head=session.repository_head,
        working_tree_digest=session.working_tree_digest,
        codemap_digest=_required(codemap_digest, "codemap_digest"),
        objective_digest=intent.intent_digest,
        candidate_items=candidates,
        required_refs=required_refs,
        prohibitions=intent.prohibitions,
        required_verifiers=_strings(
            required_verifiers, "required_verifiers", required=True
        ),
    )

    envelope: ActCapsuleEnvelope | None = None
    if legacy_act_capsule is not None:
        files_value = _strings(allowed_files, "allowed_files", required=True)
        envelope = compile_act_capsule_envelope(
            legacy_act_capsule=legacy_act_capsule,
            intent=intent,
            semantic_ledger=ledger,
            arena_slice=arena_slice,
            allowed_files=files_value,
            allowed_symbols=_strings(allowed_symbols, "allowed_symbols"),
            prohibited_effects=intent.prohibitions,
            invariants=(
                "confirmed intent is model-independent",
                "negative requirements remain executable proof obligations",
                "human confirmation grants no undeclared authority",
            ),
            allowed_tools=_strings(allowed_tools, "allowed_tools"),
            acceptance_bundle=intent.acceptance_criteria,
            repair_budget=repair_budget,
            legal_outcomes=legal_outcomes,
            continuity_requirements=_strings(
                continuity_requirements,
                "continuity_requirements",
                required=True,
            ),
            required_semantic_terms=("confirmed intent", "authority", "guardrail", "verification"),
        )

    u7_refs = {
        "confirmation_digest": confirmation.confirmation_id,
        "negative_requirements_digest": confirmation.negative_requirements_digest,
        "guardrail_set_digest": confirmation.guardrail_set_digest,
        "intent_revision_id": str(intent_revision_id or ""),
        "p0_prediction_ref": "",
        "p1_observation_ref": "",
        "current_reproof_ref": "",
        "observed_guardrail_violation": False,
        "prediction_error_classes_enabled": ["ORIGINAL_ASSUMPTION", "CONTEXT_GAP"],
        "proposal_only": True,
        "learning_promotion_authority": False,
    }
    identity = {
        "repository_head": session.repository_head,
        "source_tree_digest": session.working_tree_digest,
        "confirmation_id": confirmation.confirmation_id,
        "intent_packet": intent.to_dict(),
        "semantic_ledger": ledger.to_dict(),
        "arena_evidence_slice": arena_slice.to_dict(),
        "act_capsule_envelope": envelope.to_dict() if envelope else {},
        "unified_execution_binding_ref": str(
            unified_execution_binding_ref
            or confirmation.unified_execution_binding_ref
            or ""
        ),
        "u7_references": u7_refs,
        "owner_refs": dict(OWNER_REFS),
        "authority": dict(FORBIDDEN_AUTHORITY),
    }
    digest = stable_digest(identity)
    return BilateralCanonicalBundle(
        bundle_id=f"bilateral_{digest}",
        bundle_digest=digest,
        **identity,
    )


def canonical_binding_capabilities() -> dict[str, Any]:
    return {
        "version": VERSION,
        "canonical_owners": dict(OWNER_REFS),
        "authority": dict(FORBIDDEN_AUTHORITY),
        "compiles_intent_packet": True,
        "compiles_semantic_ledger": True,
        "compiles_arena_evidence_slice": True,
        "act_capsule_envelope_optional_until_plan_exists": True,
        "unified_execution_binding_reference_only": True,
        "u7_reference_only": True,
    }


__all__ = [
    "BilateralCanonicalBundle",
    "VERSION",
    "canonical_binding_capabilities",
    "compile_bilateral_canonical_bundle",
    "compile_canonical_records",
]
