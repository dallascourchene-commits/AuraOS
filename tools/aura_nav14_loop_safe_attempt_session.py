#!/usr/bin/env python3
"""Bind a NAV-14 progress candidate to one fail-closed loop-guard session.

D0 / HS1 / NONPROMOTING.

Exactly two semantic parents:
- NAV-14 progress-bound hydrated version handoff.
- Universal execution loop-safety guard.

This module creates no network/tool execution, currentness witness, persistence,
authorization, semantic K27 authority, or native/private transformer KV access.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json

SCHEMA = "AURA-NAV14-LOOP-SAFE-ATTEMPT-SESSION-v1"
NAV14_HEAD = "6cdd1be40428250bffba20e924f664c7be585469"
NAV14_BLOB = "b1bdfb4c65281c314e658a6fb6fc8727a4b54245"
NAV14_RUN = 33437542974
NAV14_JOB = 99637538062
LOOP_HEAD = "6406e2f302335f940a7e780d818966a539c88845"
LOOP_BLOB = "ba5800c20b09fd736054ef69615fd2e8f872b664"
LOOP_RUN = 33437846633
LOOP_JOB = 99638534069
LOOP_VERSION = "AURA_EXECUTION_LOOP_GUARD_V1"
HEX = frozenset("0123456789abcdef")


class AttemptDisposition(str, Enum):
    ATTEMPT_SESSION_CANDIDATE = "ATTEMPT_SESSION_CANDIDATE"
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_HANDOFF_NOT_READY = "HOLD_HANDOFF_NOT_READY"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"
    HOLD_CANDIDATE_BINDING_MISMATCH = "HOLD_CANDIDATE_BINDING_MISMATCH"
    HOLD_SESSION_BINDING_MISMATCH = "HOLD_SESSION_BINDING_MISMATCH"
    HOLD_ATTEMPT_LEDGER_REOPEN_REQUIRED = "HOLD_ATTEMPT_LEDGER_REOPEN_REQUIRED"
    HOLD_LOOP_GUARD_TAINTED = "HOLD_LOOP_GUARD_TAINTED"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
                      default=lambda o: o.value if isinstance(o, Enum) else str(o)).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _digest(value: str, code: str) -> str:
    value = _text(value, code).lower()
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class ProgressBoundHandoffProjectionV1:
    parent_head: str
    candidate_digest: str
    disposition: str
    subject_key: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str
    candidate_only: bool = True
    persistent_write_authorized: bool = False
    evidence_admitted: bool = False
    source_truth_proven: bool = False
    read_currentness_proven: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        _digest(self.candidate_digest, "CANDIDATE_DIGEST_REQUIRED")
        _digest(self.subject_key, "SUBJECT_KEY_REQUIRED")
        _digest(self.evidence_generation_key, "EVIDENCE_GENERATION_REQUIRED")
        _digest(self.material_digest, "MATERIAL_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "EXACT_SOURCE_URI_REQUIRED")


@dataclass(frozen=True)
class AttemptLedgerProjectionV1:
    """Opaque durable-state projection; this contract does not authenticate its producer."""
    candidate_digest: str
    session_id: str
    ledger_generation: str
    attempt_ordinal: int
    prior_terminalized: bool
    prior_no_progress_debt: int
    durable_identity_bound: bool
    producer_authenticated_by_this_contract: bool = False

    def validate(self) -> None:
        _digest(self.candidate_digest, "LEDGER_CANDIDATE_DIGEST_REQUIRED")
        _text(self.session_id, "SESSION_ID_REQUIRED")
        _text(self.ledger_generation, "LEDGER_GENERATION_REQUIRED")
        if not isinstance(self.attempt_ordinal, int) or isinstance(self.attempt_ordinal, bool) or self.attempt_ordinal < 0:
            raise ValueError("ATTEMPT_ORDINAL_INVALID")
        if not isinstance(self.prior_no_progress_debt, int) or isinstance(self.prior_no_progress_debt, bool) or self.prior_no_progress_debt < 0:
            raise ValueError("PRIOR_NO_PROGRESS_DEBT_INVALID")
        if self.producer_authenticated_by_this_contract:
            raise ValueError("LEDGER_AUTHENTICATION_CANNOT_BE_SELF_MINTED")


@dataclass(frozen=True)
class LoopGuardSnapshotProjectionV1:
    parent_head: str
    version: str
    objective_id: str
    incident_count: int
    mutation_stop: bool
    frozen_primitives: tuple[str, ...]
    blocked_write_keys: tuple[tuple[str, str], ...]
    effect_authority: bool = False
    semantic_authority: bool = False
    provider_authority: bool = False
    native_private_transformer_kv: bool = False

    def validate(self) -> None:
        _text(self.objective_id, "GUARD_OBJECTIVE_ID_REQUIRED")
        if self.version != LOOP_VERSION:
            raise ValueError("LOOP_GUARD_VERSION_MISMATCH")
        if not isinstance(self.incident_count, int) or isinstance(self.incident_count, bool) or self.incident_count < 0:
            raise ValueError("INCIDENT_COUNT_INVALID")
        if any((self.effect_authority, self.semantic_authority, self.provider_authority,
                self.native_private_transformer_kv)):
            raise ValueError("LOOP_GUARD_PROJECTION_EXCEEDED_CEILING")

    @property
    def snapshot_digest(self) -> str:
        self.validate()
        return _sha(asdict(self))


@dataclass(frozen=True)
class AttemptIntentV1:
    candidate_digest: str
    session_id: str
    operation_class: str
    target_resource: str
    semantic_purpose: str

    def validate(self) -> None:
        _digest(self.candidate_digest, "INTENT_CANDIDATE_DIGEST_REQUIRED")
        _text(self.session_id, "INTENT_SESSION_ID_REQUIRED")
        _text(self.operation_class, "OPERATION_CLASS_REQUIRED")
        _text(self.target_resource, "TARGET_RESOURCE_REQUIRED")
        _text(self.semantic_purpose, "SEMANTIC_PURPOSE_REQUIRED")

    @property
    def fingerprint_digest(self) -> str:
        self.validate()
        return _sha(asdict(self))


@dataclass(frozen=True)
class LoopSafeAttemptReceiptV1:
    schema: str
    disposition: AttemptDisposition
    reason: str
    candidate_digest: str | None
    session_id: str | None
    ledger_generation: str | None
    attempt_ordinal: int | None
    operation_fingerprint_digest: str | None
    guard_snapshot_digest: str
    attempt_receipt_digest: str
    attempt_session_candidate: bool
    candidate_only: bool = True
    ledger_producer_authenticated: bool = False
    currentness_resolved: bool = False
    evidence_admitted: bool = False
    tool_execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False


def _ceiling_breached(h: ProgressBoundHandoffProjectionV1, g: LoopGuardSnapshotProjectionV1) -> bool:
    return any((not h.candidate_only, h.persistent_write_authorized, h.evidence_admitted,
                h.source_truth_proven, h.read_currentness_proven, h.effect_authorized,
                h.semantic_k27_authority, h.native_private_transformer_kv_accessed,
                g.effect_authority, g.semantic_authority, g.provider_authority,
                g.native_private_transformer_kv))


def _guard_clean(g: LoopGuardSnapshotProjectionV1) -> bool:
    return (g.incident_count == 0 and not g.mutation_stop and not g.frozen_primitives and not g.blocked_write_keys)


def _classify_tree(h: ProgressBoundHandoffProjectionV1, l: AttemptLedgerProjectionV1,
                   g: LoopGuardSnapshotProjectionV1, i: AttemptIntentV1) -> AttemptDisposition:
    if h.parent_head != NAV14_HEAD or g.parent_head != LOOP_HEAD:
        return AttemptDisposition.HOLD_PARENT_GENERATION
    if _ceiling_breached(h, g):
        return AttemptDisposition.HOLD_CLAIM_CEILING
    if h.disposition != "PROGRESS_BOUND_HANDOFF_CANDIDATE":
        return AttemptDisposition.HOLD_HANDOFF_NOT_READY
    if h.candidate_digest != l.candidate_digest or h.candidate_digest != i.candidate_digest:
        return AttemptDisposition.HOLD_CANDIDATE_BINDING_MISMATCH
    if l.session_id != i.session_id or g.objective_id != i.session_id:
        return AttemptDisposition.HOLD_SESSION_BINDING_MISMATCH
    if l.prior_terminalized or l.prior_no_progress_debt > 0 or not l.durable_identity_bound:
        return AttemptDisposition.HOLD_ATTEMPT_LEDGER_REOPEN_REQUIRED
    if not _guard_clean(g):
        return AttemptDisposition.HOLD_LOOP_GUARD_TAINTED
    return AttemptDisposition.ATTEMPT_SESSION_CANDIDATE


def _classify_rules(h: ProgressBoundHandoffProjectionV1, l: AttemptLedgerProjectionV1,
                    g: LoopGuardSnapshotProjectionV1, i: AttemptIntentV1) -> AttemptDisposition:
    rules = (
        (h.parent_head != NAV14_HEAD or g.parent_head != LOOP_HEAD, AttemptDisposition.HOLD_PARENT_GENERATION),
        (_ceiling_breached(h, g), AttemptDisposition.HOLD_CLAIM_CEILING),
        (h.disposition != "PROGRESS_BOUND_HANDOFF_CANDIDATE", AttemptDisposition.HOLD_HANDOFF_NOT_READY),
        (h.candidate_digest != l.candidate_digest or h.candidate_digest != i.candidate_digest,
         AttemptDisposition.HOLD_CANDIDATE_BINDING_MISMATCH),
        (l.session_id != i.session_id or g.objective_id != i.session_id,
         AttemptDisposition.HOLD_SESSION_BINDING_MISMATCH),
        (l.prior_terminalized or l.prior_no_progress_debt > 0 or not l.durable_identity_bound,
         AttemptDisposition.HOLD_ATTEMPT_LEDGER_REOPEN_REQUIRED),
        (not _guard_clean(g), AttemptDisposition.HOLD_LOOP_GUARD_TAINTED),
    )
    for predicate, disposition in rules:
        if predicate:
            return disposition
    return AttemptDisposition.ATTEMPT_SESSION_CANDIDATE


def bind_loop_safe_attempt_session(*, handoff: ProgressBoundHandoffProjectionV1,
                                   ledger: AttemptLedgerProjectionV1,
                                   guard: LoopGuardSnapshotProjectionV1,
                                   intent: AttemptIntentV1) -> LoopSafeAttemptReceiptV1:
    handoff.validate(); ledger.validate(); guard.validate(); intent.validate()
    a = _classify_tree(handoff, ledger, guard, intent)
    b = _classify_rules(handoff, ledger, guard, intent)
    if a is not b:
        raise RuntimeError("DIFFERENT_J_ATTEMPT_SESSION_CLASSIFIERS_DIVERGED")
    ready = a is AttemptDisposition.ATTEMPT_SESSION_CANDIDATE
    reasons = {
        AttemptDisposition.ATTEMPT_SESSION_CANDIDATE: "exact NAV-14 candidate is bound to one clean durable attempt-session projection",
        AttemptDisposition.HOLD_PARENT_GENERATION: "parent semantic generation mismatch",
        AttemptDisposition.HOLD_HANDOFF_NOT_READY: "NAV-14 projection is not candidate-ready",
        AttemptDisposition.HOLD_CLAIM_CEILING: "upstream projection exceeds nonpromotion ceiling",
        AttemptDisposition.HOLD_CANDIDATE_BINDING_MISMATCH: "candidate identity does not commute across handoff, ledger, and intent",
        AttemptDisposition.HOLD_SESSION_BINDING_MISMATCH: "session identity does not commute across durable ledger, guard, and intent",
        AttemptDisposition.HOLD_ATTEMPT_LEDGER_REOPEN_REQUIRED: "durable attempt history carries terminal/no-progress debt or lacks durable binding",
        AttemptDisposition.HOLD_LOOP_GUARD_TAINTED: "loop guard carries incident, mutation-stop, frozen-primitive, or no-op write debt",
    }
    body = {
        "schema": SCHEMA, "disposition": a.value, "reason": reasons[a],
        "candidate_digest": handoff.candidate_digest if ready else None,
        "session_id": ledger.session_id if ready else None,
        "ledger_generation": ledger.ledger_generation if ready else None,
        "attempt_ordinal": ledger.attempt_ordinal if ready else None,
        "operation_fingerprint_digest": intent.fingerprint_digest if ready else None,
        "guard_snapshot_digest": guard.snapshot_digest,
        "attempt_session_candidate": ready,
        "candidate_only": True,
        "ledger_producer_authenticated": False,
        "currentness_resolved": False, "evidence_admitted": False,
        "tool_execution_authorized": False, "effect_authorized": False,
        "semantic_k27_authority": False, "native_private_transformer_kv_accessed": False,
    }
    body["attempt_receipt_digest"] = _sha(body)
    return LoopSafeAttemptReceiptV1(**body)


def _fixture(candidate_ready: bool = True, candidate_match: bool = True, session_match: bool = True,
             ledger_open: bool = True, guard_clean: bool = True, ceiling_ok: bool = True):
    candidate = "1" * 64
    h = ProgressBoundHandoffProjectionV1(
        NAV14_HEAD, candidate, "PROGRESS_BOUND_HANDOFF_CANDIDATE" if candidate_ready else "HOLD",
        "2"*64, "3"*64, "4"*64, "https://example.test/source",
        candidate_only=ceiling_ok,
    )
    l = AttemptLedgerProjectionV1(
        candidate if candidate_match else "5"*64, "session-1", "ledger-gen-1", 0,
        not ledger_open, 0 if ledger_open else 1, True,
    )
    i = AttemptIntentV1(candidate, "session-1" if session_match else "session-x",
                        "probe", "source:1", "advance-progress-bound-handoff")
    g = LoopGuardSnapshotProjectionV1(
        LOOP_HEAD, LOOP_VERSION, "session-1", 0 if guard_clean else 1,
        False, (), (),
    )
    return h, l, g, i


def prove_different_j() -> int:
    checked = 0
    for ready in (False, True):
        for candidate_match in (False, True):
            for session_match in (False, True):
                for ledger_open in (False, True):
                    for guard_clean in (False, True):
                        for ceiling_ok in (False, True):
                            h,l,g,i = _fixture(ready, candidate_match, session_match, ledger_open, guard_clean, ceiling_ok)
                            a = _classify_tree(h,l,g,i); b = _classify_rules(h,l,g,i)
                            if a is not b:
                                raise AssertionError((ready,candidate_match,session_match,ledger_open,guard_clean,ceiling_ok,a,b))
                            checked += 1
    return checked


LAWS = (
    "ProgressBoundHandoffCandidate!=ToolExecutionAuthority",
    "CandidateIdentityMustBindAttemptSession",
    "DurableAttemptHistoryCannotBeResetByNewInMemoryWrapper",
    "LoopGuardIncidentDebtInvalidatesAttemptSession",
    "NoOpHistoryDrift!=ProofProgress",
    "AttemptSessionCandidate!=CurrentnessResolved",
    "AttemptLedgerProjection!=LedgerProducerAuthentication",
    "K27Placement!=SemanticIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
