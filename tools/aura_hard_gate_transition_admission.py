#!/usr/bin/env python3
"""Exact hard-gate transition admission for AuraOS.

D0 / HS1 / NONPROMOTING.

A favorable evidence score never pays hard-gate debt. This membrane proves a much
narrower transition: the *same* bounded evidence may become proposal-eligible only
because an already-owned hard gate moved from FAIL to PASS under a new exact gate
evidence generation. It grants no execution/effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "AURA-HARD-GATE-TRANSITION-v1"
DECISION_SCHEMA = "AURA-HARD-GATE-TRANSITION-DECISION-v1"
GATE_STATES = frozenset({"EXACT_GREEN", "HOLD", "FAILED", "ACTION_REQUIRED", "UNKNOWN"})
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")


@dataclass(frozen=True)
class GateEvidenceState:
    gate_id: str
    owner_ref: str
    gate_scope_digest: str
    evidence_generation: str
    receipt_digest: str
    verification_state: str
    blocker: str | None
    passed: bool

    def validate(self) -> None:
        _required(self.gate_id, "GATE_ID")
        _required(self.owner_ref, "GATE_OWNER_REF")
        _sha256(self.gate_scope_digest, "GATE_SCOPE_DIGEST")
        _required(self.evidence_generation, "GATE_EVIDENCE_GENERATION")
        _sha256(self.receipt_digest, "GATE_RECEIPT_DIGEST")
        if self.verification_state not in GATE_STATES:
            raise ValueError("UNKNOWN_GATE_VERIFICATION_STATE")
        if type(self.passed) is not bool:
            raise ValueError("GATE_PASSED_MUST_BE_BOOL")
        if self.passed:
            if self.verification_state != "EXACT_GREEN":
                raise ValueError("PASSED_GATE_REQUIRES_EXACT_GREEN")
            if self.blocker is not None:
                raise ValueError("PASSED_GATE_CANNOT_HAVE_BLOCKER")
        else:
            if self.verification_state == "EXACT_GREEN":
                raise ValueError("EXACT_GREEN_GATE_MUST_BE_PASSED")
            if self.blocker is None or not self.blocker.strip():
                raise ValueError("FAILED_GATE_REQUIRES_BLOCKER")


@dataclass(frozen=True)
class EvidenceDescriptorRef:
    descriptor_digest: str
    evidence_generation: str

    def validate(self) -> None:
        _sha256(self.descriptor_digest, "EVIDENCE_DESCRIPTOR_DIGEST")
        _required(self.evidence_generation, "EVIDENCE_GENERATION")


@dataclass(frozen=True)
class ProductState:
    gates: tuple[GateEvidenceState, ...]

    def validate(self) -> None:
        if not self.gates:
            raise ValueError("HARD_GATES_REQUIRED")
        if len({g.gate_id for g in self.gates}) != len(self.gates):
            raise ValueError("DUPLICATE_HARD_GATE_ID")
        for gate in self.gates:
            gate.validate()

    @property
    def feasible(self) -> bool:
        return all(g.passed for g in self.gates)

    def by_id(self) -> dict[str, GateEvidenceState]:
        return {g.gate_id: g for g in self.gates}


@dataclass(frozen=True)
class TransitionRequest:
    schema_version: str
    transition_id: str
    domain_id: str
    target_gate_id: str
    before: ProductState
    after: ProductState
    evidence_before: EvidenceDescriptorRef
    evidence_after: EvidenceDescriptorRef
    source_currentness_root: str

    def validate(self) -> None:
        if self.schema_version != SCHEMA:
            raise ValueError("TRANSITION_SCHEMA_MISMATCH")
        for value, name in (
            (self.transition_id, "TRANSITION_ID"),
            (self.domain_id, "DOMAIN_ID"),
            (self.target_gate_id, "TARGET_GATE_ID"),
            (self.source_currentness_root, "SOURCE_CURRENTNESS_ROOT"),
        ):
            _required(value, name)
        self.before.validate()
        self.after.validate()
        self.evidence_before.validate()
        self.evidence_after.validate()


@dataclass(frozen=True)
class TransitionDecision:
    schema_version: str
    disposition: str
    reason_code: str
    transition_receipt_digest: str | None
    changed_hard_gate_ids: tuple[str, ...]
    before_product_feasible: bool
    after_product_feasible: bool
    evidence_policy_evaluated_before: bool
    evidence_policy_evaluated_after: bool
    proposal_eligible: bool
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    gate10_promoted: bool = False


def _decision(
    *,
    request: TransitionRequest,
    disposition: str,
    reason_code: str,
    changed: tuple[str, ...],
    transition_receipt_digest: str | None = None,
    proposal_eligible: bool = False,
) -> TransitionDecision:
    return TransitionDecision(
        schema_version=DECISION_SCHEMA,
        disposition=disposition,
        reason_code=reason_code,
        transition_receipt_digest=transition_receipt_digest,
        changed_hard_gate_ids=changed,
        before_product_feasible=request.before.feasible,
        after_product_feasible=request.after.feasible,
        evidence_policy_evaluated_before=request.before.feasible,
        evidence_policy_evaluated_after=request.after.feasible,
        proposal_eligible=proposal_eligible,
    )


def evaluate_hard_gate_transition(request: TransitionRequest) -> TransitionDecision:
    """Admit exactly one FAIL->PASS gate transition over unchanged bounded evidence."""
    request.validate()
    before = request.before.by_id()
    after = request.after.by_id()
    if set(before) != set(after):
        return _decision(
            request=request, disposition="REVIEW", reason_code="HARD_GATE_SET_CHANGED", changed=()
        )
    if request.target_gate_id not in before:
        return _decision(
            request=request, disposition="INVALID", reason_code="TARGET_GATE_NOT_IN_PRODUCT", changed=()
        )

    changed: list[str] = []
    for gate_id in sorted(before):
        b, a = before[gate_id], after[gate_id]
        if b.owner_ref != a.owner_ref:
            return _decision(
                request=request,
                disposition="REVIEW",
                reason_code="GATE_OWNER_CHANGED_REQUIRES_REBIND",
                changed=tuple(changed + [gate_id]),
            )
        if b.gate_scope_digest != a.gate_scope_digest:
            return _decision(
                request=request,
                disposition="REVIEW",
                reason_code="GATE_SCOPE_CHANGED_REQUIRES_NEW_GATE",
                changed=tuple(changed + [gate_id]),
            )
        if asdict(b) != asdict(a):
            changed.append(gate_id)

    changed_tuple = tuple(changed)
    if changed_tuple != (request.target_gate_id,):
        return _decision(
            request=request,
            disposition="REVIEW",
            reason_code="MULTIPLE_OR_WRONG_HARD_GATE_CHANGES",
            changed=changed_tuple,
        )

    b = before[request.target_gate_id]
    a = after[request.target_gate_id]
    if b.passed or not a.passed:
        return _decision(
            request=request,
            disposition="INVALID",
            reason_code="TARGET_GATE_MUST_TRANSITION_FAIL_TO_PASS",
            changed=changed_tuple,
        )
    if a.verification_state != "EXACT_GREEN":
        return _decision(
            request=request,
            disposition="HOLD",
            reason_code="TARGET_GATE_CLOSURE_NOT_EXACT_GREEN",
            changed=changed_tuple,
        )
    if b.evidence_generation == a.evidence_generation:
        return _decision(
            request=request,
            disposition="HOLD",
            reason_code="GATE_EVIDENCE_GENERATION_DID_NOT_ADVANCE",
            changed=changed_tuple,
        )
    if b.receipt_digest == a.receipt_digest:
        return _decision(
            request=request,
            disposition="HOLD",
            reason_code="GATE_CLOSURE_RECEIPT_DID_NOT_CHANGE",
            changed=changed_tuple,
        )
    if request.evidence_before != request.evidence_after:
        return _decision(
            request=request,
            disposition="REVIEW",
            reason_code="EVIDENCE_CHANGED_WITH_GATE_CLOSURE",
            changed=changed_tuple,
        )
    if request.before.feasible:
        return _decision(
            request=request,
            disposition="INVALID",
            reason_code="BEFORE_PRODUCT_ALREADY_FEASIBLE",
            changed=changed_tuple,
        )

    receipt = _sha(
        {
            "domain": "AURA-HARD-GATE-TRANSITION-RECEIPT-v1",
            "transition_id": request.transition_id,
            "domain_id": request.domain_id,
            "target_gate_id": request.target_gate_id,
            "gate_owner_ref": a.owner_ref,
            "gate_scope_digest": a.gate_scope_digest,
            "before_gate_generation": b.evidence_generation,
            "after_gate_generation": a.evidence_generation,
            "before_gate_receipt_digest": b.receipt_digest,
            "closure_receipt_digest": a.receipt_digest,
            "evidence_descriptor_digest": request.evidence_after.descriptor_digest,
            "evidence_generation": request.evidence_after.evidence_generation,
            "before_product_feasible": request.before.feasible,
            "after_product_feasible": request.after.feasible,
            "source_currentness_root": request.source_currentness_root,
        }
    )
    if not request.after.feasible:
        return _decision(
            request=request,
            disposition="HOLD",
            reason_code="OTHER_HARD_GATE_REMAINS_BLOCKING",
            changed=changed_tuple,
            transition_receipt_digest=receipt,
            proposal_eligible=False,
        )
    return _decision(
        request=request,
        disposition="ELIGIBLE_BOUNDED_PROPOSAL",
        reason_code="EXACT_GATE_CLOSURE_CHANGED_PRODUCT_FEASIBILITY",
        changed=changed_tuple,
        transition_receipt_digest=receipt,
        proposal_eligible=True,
    )
