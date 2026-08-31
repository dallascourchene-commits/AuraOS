#!/usr/bin/env python3
"""NAV-15 alias-stable bounded hydration transaction relation.

D0 / HS1 / NONPROMOTING.

Exactly two other-Agent semantic parents:
- PR #758: scheme-serializable, loop-safe bounded hydration transaction;
- PR #759: K27 scheme-alias-aware retrieval-progress guard.

The missing relation is same-observation binding. A positive #758 transaction and a
positive #759 alias-aware receipt are not composable merely because both are valid.
NAV-15 reexecutes #759 from raw retrieval observations and requires the exact current
fingerprint, evidence digest, and source SID to be the same observation already bound
into #758's transaction receipt.

This module does not retrieve, hydrate, materialize, admit evidence, prove currentness
or truth, authorize effects, mint K27 semantics, or access native/private transformer KV.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Optional

from tools.aura_retrieval_progress_guard import RetrievalObservation
from tools.aura_retrieval_progress_k27_alias_guard import (
    AliasAwareDecision,
    ProjectionAliasOwnerProjection,
    SchemeBoundCoordinateViewProjection,
    assess_k27_alias_aware_retrieval_progress,
)

SCHEMA = "AURA-NAV15-ALIAS-STABLE-HYDRATION-TRANSACTION-v1"
TRANSACTION_SCHEMA = "AURA-SCHEME-SERIALIZABLE-HYDRATION-TRANSACTION-v1"
TRANSACTION_HEAD = "8c30df774ad55507aa57bbfd49444991c1a2b379"
TRANSACTION_BLOB = "97211589682a7ed67c8c63530dac744b9c186e57"
TRANSACTION_RUN = "33436051562"
TRANSACTION_JOB = "99632632584"
ALIAS_HEAD = "658b3bc651ee39454f6b94039d26ff76d48f73d8"
ALIAS_BLOB = "1abd821beb2a8a9a96b5ac2f0956195b20a321c7"
ALIAS_TEST_BLOB = "ddc88a73f49d6a09d67b388cf5c4958317e10ae2"
ALIAS_PROOF_HEAD = "cf6b07e5c498d7c429e6679a8ba5cec5e1e46ca6"
ALIAS_RUN = "33436588718"
ALIAS_JOB = "99634405807"
PARENT_OBJECTIVE_5_DRIVE_ID = "1cYsTW4R6Mz46A5DMpVgX86l7aJdrcFzKc7Ooy4KFAVo"
PARENT_LOOP_SAFE_PREFLIGHT_DRIVE_ID = "1uJHYkJDS9M0DvrteqJCzabjondPh-QC9NV05NNvK2PQ"
HEX = frozenset("0123456789abcdef")


class Nav15Disposition(str, Enum):
    ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE = "ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE"
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_TRANSACTION_NOT_ADMITTED = "HOLD_TRANSACTION_NOT_ADMITTED"
    HOLD_OBSERVATION_BINDING_MISMATCH = "HOLD_OBSERVATION_BINDING_MISMATCH"
    HOLD_RAW_DECISION_MISMATCH = "HOLD_RAW_DECISION_MISMATCH"
    HOLD_ALIAS_RESOLUTION_REQUIRED = "HOLD_ALIAS_RESOLUTION_REQUIRED"
    HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED = "HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
    COLLAPSE_RETRIEVAL_CONE = "COLLAPSE_RETRIEVAL_CONE"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
    ).encode("ascii")


def _domain_sha(domain: str, value: object) -> str:
    return hashlib.sha256(_canonical({"domain": domain, "value": value})).hexdigest()


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
class SchemeSerializableTransactionProjectionV1:
    """Closed projection of one PR #758 transaction receipt."""

    parent_head: str
    schema: str
    disposition: str
    reason: str
    source_identity: str
    pre_route_projection_digest: str
    post_route_projection_digest: str
    owner_epoch: str
    semantic_plan_digest: str
    evidence_generation_key: str
    target_level: int
    retrieval_fingerprint_digest: str
    retrieval_evidence_digest: str
    retrieval_disposition: str
    exact_reopen_handle_digest: Optional[str]
    transaction_digest: str
    bounded_transaction_admitted: bool
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    evidence_admitted: bool = False
    materialization_executed: bool = False
    authorization_issued: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != TRANSACTION_SCHEMA:
            raise ValueError("TRANSACTION_SCHEMA_MISMATCH")
        for value, code in (
            (self.source_identity, "SOURCE_IDENTITY_REQUIRED"),
            (self.owner_epoch, "OWNER_EPOCH_REQUIRED"),
            (self.evidence_generation_key, "EVIDENCE_GENERATION_KEY_REQUIRED"),
        ):
            _text(value, code)
        for value, code in (
            (self.pre_route_projection_digest, "PRE_ROUTE_DIGEST_REQUIRED"),
            (self.post_route_projection_digest, "POST_ROUTE_DIGEST_REQUIRED"),
            (self.semantic_plan_digest, "SEMANTIC_PLAN_DIGEST_REQUIRED"),
            (self.retrieval_fingerprint_digest, "RETRIEVAL_FINGERPRINT_DIGEST_REQUIRED"),
            (self.retrieval_evidence_digest, "RETRIEVAL_EVIDENCE_DIGEST_REQUIRED"),
            (self.transaction_digest, "TRANSACTION_DIGEST_REQUIRED"),
        ):
            _digest(value, code)
        if self.exact_reopen_handle_digest is not None:
            _digest(self.exact_reopen_handle_digest, "REOPEN_HANDLE_DIGEST_INVALID")
        if (
            not isinstance(self.target_level, int)
            or isinstance(self.target_level, bool)
            or not 0 <= self.target_level <= 4
        ):
            raise ValueError("TARGET_LEVEL_MUST_BE_0_TO_4")
        if self.bounded_transaction_admitted != (self.disposition == "ADMIT_BOUNDED_TRANSACTION"):
            raise ValueError("TRANSACTION_ADMISSION_DISPOSITION_INCONSISTENT")
        if any(
            (
                self.source_currentness_proven,
                self.semantic_truth_proven,
                self.evidence_admitted,
                self.materialization_executed,
                self.authorization_issued,
                self.effect_authorized,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("TRANSACTION_EXCEEDED_NONPROMOTION_CEILING")
        if self.transaction_digest != _transaction_digest(self):
            raise ValueError("TRANSACTION_DIGEST_MISMATCH")


def _transaction_digest(t: SchemeSerializableTransactionProjectionV1) -> str:
    payload = {
        "schema": TRANSACTION_SCHEMA,
        "parent_drive_ids": [
            PARENT_OBJECTIVE_5_DRIVE_ID,
            PARENT_LOOP_SAFE_PREFLIGHT_DRIVE_ID,
        ],
        "disposition": t.disposition,
        "reason": t.reason,
        "source_identity": t.source_identity,
        "pre_route_projection_digest": t.pre_route_projection_digest,
        "post_route_projection_digest": t.post_route_projection_digest,
        "owner_epoch": t.owner_epoch,
        "semantic_plan_digest": t.semantic_plan_digest,
        "evidence_generation_key": t.evidence_generation_key,
        "target_level": t.target_level,
        "retrieval_fingerprint_digest": t.retrieval_fingerprint_digest,
        "retrieval_evidence_digest": t.retrieval_evidence_digest,
        "retrieval_disposition": t.retrieval_disposition,
        "exact_reopen_handle_digest": t.exact_reopen_handle_digest,
        "claim_ceiling": {
            "source_currentness_proven": False,
            "semantic_truth_proven": False,
            "evidence_admitted": False,
            "materialization_executed": False,
            "authorization_issued": False,
            "effect_authorized": False,
            "semantic_k27_authority": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return _domain_sha(TRANSACTION_SCHEMA, payload)


@dataclass(frozen=True)
class AliasStableHydrationTransactionReceiptV1:
    disposition: Nav15Disposition
    reason: str
    transaction_digest: str
    alias_progress_receipt_digest: str
    raw_retrieval_decision: Optional[str]
    alias_aware_decision: str
    source_identity: Optional[str]
    retrieval_fingerprint_digest: Optional[str]
    retrieval_evidence_digest: Optional[str]
    semantic_fingerprint_digest: Optional[str]
    transaction_relation_digest: str
    candidate_only: bool = True
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    evidence_admitted: bool = False
    materialization_executed: bool = False
    authorization_issued: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def ready(self) -> bool:
        return self.disposition is Nav15Disposition.ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE


def _classify_tree(
    *,
    transaction_parent_ok: bool,
    transaction_admitted: bool,
    observation_binding_ok: bool,
    raw_decision_match: bool,
    alias_decision: AliasAwareDecision,
    ceiling_breached: bool,
) -> Nav15Disposition:
    if not transaction_parent_ok:
        return Nav15Disposition.HOLD_PARENT_GENERATION
    if ceiling_breached:
        return Nav15Disposition.HOLD_CLAIM_CEILING
    if not transaction_admitted:
        return Nav15Disposition.HOLD_TRANSACTION_NOT_ADMITTED
    if not observation_binding_ok:
        return Nav15Disposition.HOLD_OBSERVATION_BINDING_MISMATCH
    if not raw_decision_match:
        return Nav15Disposition.HOLD_RAW_DECISION_MISMATCH
    if alias_decision is AliasAwareDecision.HOLD_ALIAS_RESOLUTION_REQUIRED:
        return Nav15Disposition.HOLD_ALIAS_RESOLUTION_REQUIRED
    if alias_decision is AliasAwareDecision.CHANGE_AXIS_REQUIRED:
        return Nav15Disposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED
    if alias_decision is AliasAwareDecision.COLLAPSE_CONE:
        return Nav15Disposition.COLLAPSE_RETRIEVAL_CONE
    return Nav15Disposition.ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE


def _classify_table(
    *,
    transaction_parent_ok: bool,
    transaction_admitted: bool,
    observation_binding_ok: bool,
    raw_decision_match: bool,
    alias_decision: AliasAwareDecision,
    ceiling_breached: bool,
) -> Nav15Disposition:
    rules = (
        (not transaction_parent_ok, Nav15Disposition.HOLD_PARENT_GENERATION),
        (ceiling_breached, Nav15Disposition.HOLD_CLAIM_CEILING),
        (not transaction_admitted, Nav15Disposition.HOLD_TRANSACTION_NOT_ADMITTED),
        (not observation_binding_ok, Nav15Disposition.HOLD_OBSERVATION_BINDING_MISMATCH),
        (not raw_decision_match, Nav15Disposition.HOLD_RAW_DECISION_MISMATCH),
        (
            alias_decision is AliasAwareDecision.HOLD_ALIAS_RESOLUTION_REQUIRED,
            Nav15Disposition.HOLD_ALIAS_RESOLUTION_REQUIRED,
        ),
        (
            alias_decision is AliasAwareDecision.CHANGE_AXIS_REQUIRED,
            Nav15Disposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
        ),
        (
            alias_decision is AliasAwareDecision.COLLAPSE_CONE,
            Nav15Disposition.COLLAPSE_RETRIEVAL_CONE,
        ),
    )
    for predicate, disposition in rules:
        if predicate:
            return disposition
    return Nav15Disposition.ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE


def bind_alias_stable_hydration_transaction(
    *,
    transaction: SchemeSerializableTransactionProjectionV1,
    previous: Optional[RetrievalObservation],
    current: RetrievalObservation,
    previous_view: Optional[SchemeBoundCoordinateViewProjection],
    current_view: SchemeBoundCoordinateViewProjection,
    alias_projection: Optional[ProjectionAliasOwnerProjection] = None,
    prior_no_progress_count: int = 0,
) -> AliasStableHydrationTransactionReceiptV1:
    """Reexecute #759 and bind its exact current observation to #758's transaction."""

    transaction.validate()
    alias_receipt = assess_k27_alias_aware_retrieval_progress(
        previous=previous,
        current=current,
        previous_view=previous_view,
        current_view=current_view,
        alias_projection=alias_projection,
        prior_no_progress_count=prior_no_progress_count,
    )
    alias_receipt.validate_claim_ceiling()

    transaction_parent_ok = transaction.parent_head == TRANSACTION_HEAD
    transaction_admitted = (
        transaction.disposition == "ADMIT_BOUNDED_TRANSACTION"
        and transaction.bounded_transaction_admitted is True
    )
    observation_binding_ok = (
        transaction.retrieval_fingerprint_digest == current.fingerprint.digest
        and transaction.retrieval_evidence_digest == current.evidence_digest
        and transaction.source_identity == current_view.source_sid
    )
    raw_decision_match = alias_receipt.raw_decision == transaction.retrieval_disposition
    ceiling_breached = any(
        (
            transaction.source_currentness_proven,
            transaction.semantic_truth_proven,
            transaction.evidence_admitted,
            transaction.materialization_executed,
            transaction.authorization_issued,
            transaction.effect_authorized,
            transaction.semantic_k27_authority,
            transaction.native_private_transformer_kv_accessed,
            alias_receipt.source_identity_authenticated_by_this_contract,
            alias_receipt.alias_owner_authenticated_by_this_contract,
            alias_receipt.source_currentness_proven,
            alias_receipt.semantic_truth_proven,
            alias_receipt.authority_granted,
            alias_receipt.effect_authority_granted,
            alias_receipt.semantic_k27_authority_minted,
            alias_receipt.native_private_transformer_kv_accessed,
        )
    )

    a = _classify_tree(
        transaction_parent_ok=transaction_parent_ok,
        transaction_admitted=transaction_admitted,
        observation_binding_ok=observation_binding_ok,
        raw_decision_match=raw_decision_match,
        alias_decision=alias_receipt.decision,
        ceiling_breached=ceiling_breached,
    )
    b = _classify_table(
        transaction_parent_ok=transaction_parent_ok,
        transaction_admitted=transaction_admitted,
        observation_binding_ok=observation_binding_ok,
        raw_decision_match=raw_decision_match,
        alias_decision=alias_receipt.decision,
        ceiling_breached=ceiling_breached,
    )
    if a is not b:
        raise RuntimeError("DIFFERENT_J_NAV15_CLASSIFIERS_DIVERGED")

    ready = a is Nav15Disposition.ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE
    reason = {
        Nav15Disposition.ALIAS_STABLE_HYDRATION_TRANSACTION_CANDIDATE: "#758 transaction is bound to the exact raw retrieval observation reclassified by #759 after route-alias quotient",
        Nav15Disposition.HOLD_PARENT_GENERATION: "scheme-serializable transaction parent generation mismatch",
        Nav15Disposition.HOLD_TRANSACTION_NOT_ADMITTED: "parent hydration transaction is not admitted",
        Nav15Disposition.HOLD_OBSERVATION_BINDING_MISMATCH: "#758 transaction and #759 reexecution do not bind the same raw fingerprint/evidence/source observation",
        Nav15Disposition.HOLD_RAW_DECISION_MISMATCH: "#758 raw retrieval disposition differs from #759 reexecuted raw parent decision",
        Nav15Disposition.HOLD_ALIAS_RESOLUTION_REQUIRED: "same-source route change requires an upstream alias-owner projection",
        Nav15Disposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED: "alias-quotiented retrieval made no independent progress and must change a genuine axis",
        Nav15Disposition.COLLAPSE_RETRIEVAL_CONE: "alias-quotiented repeated no-progress retrieval cone is collapsed",
        Nav15Disposition.HOLD_CLAIM_CEILING: "upstream projection exceeds the nonpromotion ceiling",
    }[a]

    body = {
        "schema": SCHEMA,
        "disposition": a.value,
        "reason": reason,
        "transaction_digest": transaction.transaction_digest,
        "alias_progress_receipt_digest": alias_receipt.receipt_digest,
        "raw_retrieval_decision": alias_receipt.raw_decision,
        "alias_aware_decision": alias_receipt.decision.value,
        "source_identity": transaction.source_identity if ready else None,
        "retrieval_fingerprint_digest": current.fingerprint.digest if ready else None,
        "retrieval_evidence_digest": current.evidence_digest if ready else None,
        "semantic_fingerprint_digest": alias_receipt.semantic_fingerprint_digest if ready else None,
        "claim_ceiling": {
            "candidate_only": True,
            "source_currentness_proven": False,
            "semantic_truth_proven": False,
            "evidence_admitted": False,
            "materialization_executed": False,
            "authorization_issued": False,
            "effect_authorized": False,
            "semantic_k27_authority": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return AliasStableHydrationTransactionReceiptV1(
        disposition=a,
        reason=reason,
        transaction_digest=transaction.transaction_digest,
        alias_progress_receipt_digest=alias_receipt.receipt_digest,
        raw_retrieval_decision=alias_receipt.raw_decision,
        alias_aware_decision=alias_receipt.decision.value,
        source_identity=transaction.source_identity if ready else None,
        retrieval_fingerprint_digest=current.fingerprint.digest if ready else None,
        retrieval_evidence_digest=current.evidence_digest if ready else None,
        semantic_fingerprint_digest=alias_receipt.semantic_fingerprint_digest if ready else None,
        transaction_relation_digest=_sha(body),
    )


def prove_different_j() -> int:
    checked = 0
    for parent_ok in (False, True):
        for admitted in (False, True):
            for binding_ok in (False, True):
                for raw_match in (False, True):
                    for decision in AliasAwareDecision:
                        for ceiling in (False, True):
                            a = _classify_tree(
                                transaction_parent_ok=parent_ok,
                                transaction_admitted=admitted,
                                observation_binding_ok=binding_ok,
                                raw_decision_match=raw_match,
                                alias_decision=decision,
                                ceiling_breached=ceiling,
                            )
                            b = _classify_table(
                                transaction_parent_ok=parent_ok,
                                transaction_admitted=admitted,
                                observation_binding_ok=binding_ok,
                                raw_decision_match=raw_match,
                                alias_decision=decision,
                                ceiling_breached=ceiling,
                            )
                            if a is not b:
                                raise AssertionError("DIFFERENT_J_NAV15_MISMATCH")
                            checked += 1
    return checked


LAWS = (
    "ValidParentReceipts!=SameRetrievalObservation",
    "TransactionFingerprintMustEqualReexecutedRawFingerprint",
    "TransactionEvidenceDigestMustEqualReexecutedRawEvidenceDigest",
    "TransactionSourceIdentityMustEqualAliasViewSourceSID",
    "SchemeRotationCannotResetNoProgressDebt",
    "AliasAwareProgressMustOwnNoveltyForAliasStableTransaction",
    "HOLD_ALIAS_RESOLUTION_REQUIREDCannotBecomeHydrationAdmission",
    "CHANGE_AXIS_REQUIREDCannotBecomeHydrationAdmission",
    "COLLAPSE_CONECannotBecomeHydrationAdmission",
    "AliasStableHydrationTransactionCandidate!=Materialization!=EvidenceAdmission!=Authority",
    "K27Path!=SemanticIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
