#!/usr/bin/env python3
"""Alias-stable future-read currentness preflight.

D0 / HS1 / NONPROMOTING.

Exactly two post-PR758 foreign terminal semantic parents define this relation:
- PR #759: retrieval no-progress debt survives K27 route/scheme aliases.
- PR #760: hydrated version handoff may become HANDOFF_READY_CANDIDATE while
  mandatory future read-currentness debt remains explicitly unresolved.

This module owns only the relation between those consequences. It does not read a
source, resolve currentness, authenticate an alias owner, admit evidence, persist
state, authorize execution/effects, mint K27 semantic authority, or access native
/private transformer KV.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json

from tools.aura_nav13d_eki4_hydrated_version_handoff import (
    HandoffDisposition,
    HydratedVersionHandoffReceiptV1,
)

SCHEMA = "AURA-ALIAS-STABLE-FUTURE-READ-CURRENTNESS-PREFLIGHT-v1"
BINDING_SCHEMA = "AURA-HANDOFF-SOURCE-ROUTE-ALIAS-BINDING-PROJECTION-v1"
ALIAS_PROGRESS_SCHEMA = "AURA-ALIAS-AWARE-RETRIEVAL-PROGRESS-PROJECTION-v1"

PR759_SEMANTIC_HEAD = "658b3bc651ee39454f6b94039d26ff76d48f73d8"
PR759_SOURCE_BLOB = "1abd821beb2a8a9a96b5ac2f0956195b20a321c7"
PR759_TEST_BLOB = "ddc88a73f49d6a09d67b388cf5c4958317e10ae2"
PR759_PROOF_HEAD = "cf6b07e5c498d7c429e6679a8ba5cec5e1e46ca6"
PR759_PROOF_RUN = "33436588718"
PR759_PROOF_JOB = "99634405807"

PR760_SEMANTIC_HEAD = "1a7ab9d884acc917ea28bea2b28bc747222f1aed"
PR760_SOURCE_BLOB = "edac88e89e0659cd6bbf99c7a138e2ae3f516ae8"
PR760_TEST_BLOB = "268889ff864c1fd7f80469071d6ec6738e941f36"
PR760_PROOF_RUN = "33436321891"
PR760_PROOF_JOB = "99633531552"

HEX = frozenset("0123456789abcdef")
EXPECTED_FUTURE_AXES = ("source",)
EXPECTED_EKI2_AXES = ("SOURCE_GENERATION_CURRENT", "SOURCE_BODY_CURRENT")


class AliasProgressDecision(str, Enum):
    ALLOW_INITIAL = "ALLOW_INITIAL"
    ALLOW_CHANGED_AXIS = "ALLOW_CHANGED_AXIS"
    ALLOW_STATE_TRANSITION = "ALLOW_STATE_TRANSITION"
    CHANGE_AXIS_REQUIRED = "CHANGE_AXIS_REQUIRED"
    COLLAPSE_CONE = "COLLAPSE_CONE"
    HOLD_ALIAS_RESOLUTION_REQUIRED = "HOLD_ALIAS_RESOLUTION_REQUIRED"


class FutureReadPreflightDisposition(str, Enum):
    FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE = (
        "FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE"
    )
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_HANDOFF_NOT_READY = "HOLD_HANDOFF_NOT_READY"
    HOLD_READ_DEBT_NOT_CARRIED = "HOLD_READ_DEBT_NOT_CARRIED"
    HOLD_READ_AXES_MISMATCH = "HOLD_READ_AXES_MISMATCH"
    HOLD_SOURCE_BINDING_REQUIRED = "HOLD_SOURCE_BINDING_REQUIRED"
    HOLD_SOURCE_BINDING_MISMATCH = "HOLD_SOURCE_BINDING_MISMATCH"
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


def _sha(domain: str, value: object) -> str:
    return hashlib.sha256(
        _canonical({"domain": domain, "value": value})
    ).hexdigest()


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
class AliasAwareRetrievalProgressProjectionV1:
    """Projection of PR #759 output; this contract does not re-own its classifier."""

    schema: str
    semantic_owner_head: str
    proof_head: str
    proof_run: str
    proof_job: str
    decision: AliasProgressDecision
    current_view_digest: str
    semantic_fingerprint_digest: str
    source_sid_same: bool
    route_projection_changed: bool
    alias_projection_required: bool
    alias_projection_consumed: bool
    prior_no_progress_count: int
    next_no_progress_count: int
    source_identity_authenticated_by_this_contract: bool = False
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    authority_granted: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != ALIAS_PROGRESS_SCHEMA:
            raise ValueError("ALIAS_PROGRESS_SCHEMA_MISMATCH")
        if self.semantic_owner_head != PR759_SEMANTIC_HEAD:
            raise ValueError("PR759_SEMANTIC_HEAD_MISMATCH")
        if self.proof_head != PR759_PROOF_HEAD:
            raise ValueError("PR759_PROOF_HEAD_MISMATCH")
        if self.proof_run != PR759_PROOF_RUN or self.proof_job != PR759_PROOF_JOB:
            raise ValueError("PR759_PROOF_IDENTITY_MISMATCH")
        if not isinstance(self.decision, AliasProgressDecision):
            raise ValueError("ALIAS_PROGRESS_DECISION_INVALID")
        _digest(self.current_view_digest, "CURRENT_VIEW_DIGEST_REQUIRED")
        _digest(self.semantic_fingerprint_digest, "SEMANTIC_FINGERPRINT_DIGEST_REQUIRED")
        for value, code in (
            (self.prior_no_progress_count, "PRIOR_NO_PROGRESS_COUNT_INVALID"),
            (self.next_no_progress_count, "NEXT_NO_PROGRESS_COUNT_INVALID"),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(code)
        if self.alias_projection_consumed and not self.alias_projection_required:
            raise ValueError("ALIAS_PROJECTION_CONSUMED_WITHOUT_REQUIREMENT")
        if (
            self.route_projection_changed
            and self.source_sid_same
            and self.decision
            not in {
                AliasProgressDecision.HOLD_ALIAS_RESOLUTION_REQUIRED,
                AliasProgressDecision.CHANGE_AXIS_REQUIRED,
                AliasProgressDecision.COLLAPSE_CONE,
                AliasProgressDecision.ALLOW_STATE_TRANSITION,
            }
            and not self.alias_projection_consumed
        ):
            raise ValueError("ROUTE_ALIAS_CHANGE_NOT_OWNER_BOUND")
        if any(
            (
                self.source_identity_authenticated_by_this_contract,
                self.source_currentness_proven,
                self.semantic_truth_proven,
                self.authority_granted,
                self.effect_authority_granted,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("ALIAS_PROGRESS_EXCEEDED_NONPROMOTION_CEILING")


@dataclass(frozen=True)
class HandoffSourceRouteAliasBindingProjectionV1:
    """Opaque owner projection tying the handoff source to the current route/SID.

    This contract checks internal consistency only. It does not authenticate the owner or
    prove currentness/truth. The projection can restrict/hold a read probe; it cannot grant
    source authority or satisfy the read-currentness debt itself.
    """

    schema: str
    subject_key: str
    evidence_generation_key: str
    exact_source_uri: str
    handoff_source_view_canonical_key: str
    handoff_source_view_digest: str
    current_view_digest: str
    source_sid: str
    owner_ref: str
    owner_generation: str
    owner_receipt_digest: str
    relation_type: str = "HANDOFF_SOURCE_ALIASES_CURRENT_ROUTE"
    owner_state: str = "RESOLVED_CURRENT_PROJECTION"
    owner_authenticated_by_this_contract: bool = False
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    read_currentness_proven: bool = False
    authority_granted: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != BINDING_SCHEMA:
            raise ValueError("HANDOFF_ALIAS_BINDING_SCHEMA_MISMATCH")
        for value, code in (
            (self.subject_key, "BINDING_SUBJECT_KEY_REQUIRED"),
            (self.evidence_generation_key, "BINDING_EVIDENCE_GENERATION_REQUIRED"),
            (self.exact_source_uri, "BINDING_SOURCE_URI_REQUIRED"),
            (self.handoff_source_view_canonical_key, "HANDOFF_VIEW_CANONICAL_KEY_REQUIRED"),
            (self.source_sid, "SOURCE_SID_REQUIRED"),
            (self.owner_ref, "BINDING_OWNER_REF_REQUIRED"),
            (self.owner_generation, "BINDING_OWNER_GENERATION_REQUIRED"),
        ):
            _text(value, code)
        for value, code in (
            (self.subject_key, "BINDING_SUBJECT_KEY_INVALID"),
            (self.evidence_generation_key, "BINDING_EVIDENCE_GENERATION_INVALID"),
            (self.handoff_source_view_digest, "HANDOFF_SOURCE_VIEW_DIGEST_INVALID"),
            (self.current_view_digest, "CURRENT_VIEW_DIGEST_INVALID"),
            (self.owner_receipt_digest, "BINDING_OWNER_RECEIPT_INVALID"),
        ):
            _digest(value, code)
        if self.exact_source_uri != self.handoff_source_view_canonical_key:
            raise ValueError("HANDOFF_SOURCE_URI_VIEW_KEY_MISMATCH")
        if self.relation_type != "HANDOFF_SOURCE_ALIASES_CURRENT_ROUTE":
            raise ValueError("HANDOFF_ALIAS_RELATION_UNSUPPORTED")
        if self.owner_state != "RESOLVED_CURRENT_PROJECTION":
            raise ValueError("HANDOFF_ALIAS_BINDING_NOT_CURRENT")
        if any(
            (
                self.owner_authenticated_by_this_contract,
                self.source_currentness_proven,
                self.semantic_truth_proven,
                self.read_currentness_proven,
                self.authority_granted,
                self.effect_authority_granted,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("HANDOFF_ALIAS_BINDING_EXCEEDED_NONPROMOTION_CEILING")

    @property
    def binding_digest(self) -> str:
        self.validate()
        return _sha(BINDING_SCHEMA, asdict(self))


@dataclass(frozen=True)
class FutureReadCurrentnessProbeIntentV1:
    subject_key: str
    evidence_generation_key: str
    requested_future_read_axes: tuple[str, ...]
    requested_eki2_read_axes: tuple[str, ...]
    semantic_purpose: str = "FUTURE_READ_CURRENTNESS_PROBE"

    def validate(self) -> None:
        _digest(self.subject_key, "INTENT_SUBJECT_KEY_INVALID")
        _digest(self.evidence_generation_key, "INTENT_EVIDENCE_GENERATION_INVALID")
        if not isinstance(self.requested_future_read_axes, tuple):
            raise ValueError("FUTURE_READ_AXES_MUST_BE_TUPLE")
        if not isinstance(self.requested_eki2_read_axes, tuple):
            raise ValueError("EKI2_READ_AXES_MUST_BE_TUPLE")
        if self.semantic_purpose != "FUTURE_READ_CURRENTNESS_PROBE":
            raise ValueError("SEMANTIC_PURPOSE_MISMATCH")


@dataclass(frozen=True)
class FutureReadCurrentnessPreflightReceiptV1:
    schema: str
    disposition: FutureReadPreflightDisposition
    reason: str
    handoff_digest: str
    alias_progress_semantic_fingerprint_digest: str
    current_view_digest: str
    source_binding_digest: str | None
    subject_key: str | None
    evidence_generation_key: str | None
    requested_future_read_axes: tuple[str, ...]
    requested_eki2_read_axes: tuple[str, ...]
    probe_receipt_digest: str
    probe_admissible_candidate: bool
    read_currentness_debt_carried: bool = True
    source_currentness_proven: bool = False
    read_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    evidence_admitted: bool = False
    source_owner_authenticated_by_this_contract: bool = False
    retrieval_executed: bool = False
    materialization_executed: bool = False
    persistent_use_authorized: bool = False
    authorization_issued: bool = False
    effect_authorized: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("FUTURE_READ_PREFLIGHT_SCHEMA_MISMATCH")
        _digest(self.handoff_digest, "HANDOFF_DIGEST_REQUIRED")
        _digest(
            self.alias_progress_semantic_fingerprint_digest,
            "ALIAS_PROGRESS_FINGERPRINT_REQUIRED",
        )
        _digest(self.current_view_digest, "CURRENT_VIEW_DIGEST_REQUIRED")
        if self.source_binding_digest is not None:
            _digest(self.source_binding_digest, "SOURCE_BINDING_DIGEST_INVALID")
        if self.probe_admissible_candidate != (
            self.disposition
            is FutureReadPreflightDisposition.FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE
        ):
            raise ValueError("PROBE_ADMISSION_DISPOSITION_INCONSISTENT")
        if self.read_currentness_debt_carried is not True:
            raise ValueError("READ_CURRENTNESS_DEBT_MUST_REMAIN_CARRIED")
        if any(
            (
                self.source_currentness_proven,
                self.read_currentness_proven,
                self.semantic_truth_proven,
                self.evidence_admitted,
                self.source_owner_authenticated_by_this_contract,
                self.retrieval_executed,
                self.materialization_executed,
                self.persistent_use_authorized,
                self.authorization_issued,
                self.effect_authorized,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("FUTURE_READ_PREFLIGHT_EXCEEDED_NONPROMOTION_CEILING")


def _handoff_ceiling_breached(handoff: HydratedVersionHandoffReceiptV1) -> bool:
    return any(
        (
            not handoff.candidate_only,
            handoff.persistent_write_authorized,
            handoff.evidence_admitted,
            handoff.source_truth_proven,
            handoff.read_currentness_proven,
            handoff.effect_authorized,
            handoff.semantic_k27_authority,
            handoff.native_private_transformer_kv_accessed,
        )
    )


def _binding_matches(
    handoff: HydratedVersionHandoffReceiptV1,
    progress: AliasAwareRetrievalProgressProjectionV1,
    binding: HandoffSourceRouteAliasBindingProjectionV1 | None,
    intent: FutureReadCurrentnessProbeIntentV1,
) -> bool:
    if binding is None:
        return False
    binding.validate()
    return all(
        (
            handoff.subject_key is not None,
            handoff.evidence_generation_key is not None,
            handoff.exact_source_uri is not None,
            binding.subject_key == handoff.subject_key == intent.subject_key,
            binding.evidence_generation_key
            == handoff.evidence_generation_key
            == intent.evidence_generation_key,
            binding.exact_source_uri == handoff.exact_source_uri,
            binding.current_view_digest == progress.current_view_digest,
        )
    )


def _classify_tree(
    *,
    handoff_semantic_head: str,
    handoff: HydratedVersionHandoffReceiptV1,
    progress: AliasAwareRetrievalProgressProjectionV1,
    binding: HandoffSourceRouteAliasBindingProjectionV1 | None,
    intent: FutureReadCurrentnessProbeIntentV1,
) -> FutureReadPreflightDisposition:
    if handoff_semantic_head != PR760_SEMANTIC_HEAD:
        return FutureReadPreflightDisposition.HOLD_PARENT_GENERATION
    if progress.semantic_owner_head != PR759_SEMANTIC_HEAD:
        return FutureReadPreflightDisposition.HOLD_PARENT_GENERATION
    if _handoff_ceiling_breached(handoff):
        return FutureReadPreflightDisposition.HOLD_CLAIM_CEILING
    if handoff.disposition is not HandoffDisposition.HANDOFF_READY_CANDIDATE:
        return FutureReadPreflightDisposition.HOLD_HANDOFF_NOT_READY
    if (
        handoff.future_read_axes != EXPECTED_FUTURE_AXES
        or handoff.eki2_read_axes != EXPECTED_EKI2_AXES
    ):
        return FutureReadPreflightDisposition.HOLD_READ_DEBT_NOT_CARRIED
    if (
        intent.requested_future_read_axes != handoff.future_read_axes
        or intent.requested_eki2_read_axes != handoff.eki2_read_axes
    ):
        return FutureReadPreflightDisposition.HOLD_READ_AXES_MISMATCH
    if binding is None:
        return FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_REQUIRED
    if not _binding_matches(handoff, progress, binding, intent):
        return FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_MISMATCH
    if progress.decision is AliasProgressDecision.HOLD_ALIAS_RESOLUTION_REQUIRED:
        return FutureReadPreflightDisposition.HOLD_ALIAS_RESOLUTION_REQUIRED
    if progress.decision is AliasProgressDecision.CHANGE_AXIS_REQUIRED:
        return FutureReadPreflightDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED
    if progress.decision is AliasProgressDecision.COLLAPSE_CONE:
        return FutureReadPreflightDisposition.COLLAPSE_RETRIEVAL_CONE
    return FutureReadPreflightDisposition.FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE


def _classify_rules(
    *,
    handoff_semantic_head: str,
    handoff: HydratedVersionHandoffReceiptV1,
    progress: AliasAwareRetrievalProgressProjectionV1,
    binding: HandoffSourceRouteAliasBindingProjectionV1 | None,
    intent: FutureReadCurrentnessProbeIntentV1,
) -> FutureReadPreflightDisposition:
    rules = (
        (
            handoff_semantic_head != PR760_SEMANTIC_HEAD
            or progress.semantic_owner_head != PR759_SEMANTIC_HEAD,
            FutureReadPreflightDisposition.HOLD_PARENT_GENERATION,
        ),
        (
            _handoff_ceiling_breached(handoff),
            FutureReadPreflightDisposition.HOLD_CLAIM_CEILING,
        ),
        (
            handoff.disposition is not HandoffDisposition.HANDOFF_READY_CANDIDATE,
            FutureReadPreflightDisposition.HOLD_HANDOFF_NOT_READY,
        ),
        (
            handoff.future_read_axes != EXPECTED_FUTURE_AXES
            or handoff.eki2_read_axes != EXPECTED_EKI2_AXES,
            FutureReadPreflightDisposition.HOLD_READ_DEBT_NOT_CARRIED,
        ),
        (
            intent.requested_future_read_axes != handoff.future_read_axes
            or intent.requested_eki2_read_axes != handoff.eki2_read_axes,
            FutureReadPreflightDisposition.HOLD_READ_AXES_MISMATCH,
        ),
        (
            binding is None,
            FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_REQUIRED,
        ),
        (
            binding is not None
            and not _binding_matches(handoff, progress, binding, intent),
            FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_MISMATCH,
        ),
        (
            progress.decision is AliasProgressDecision.HOLD_ALIAS_RESOLUTION_REQUIRED,
            FutureReadPreflightDisposition.HOLD_ALIAS_RESOLUTION_REQUIRED,
        ),
        (
            progress.decision is AliasProgressDecision.CHANGE_AXIS_REQUIRED,
            FutureReadPreflightDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
        ),
        (
            progress.decision is AliasProgressDecision.COLLAPSE_CONE,
            FutureReadPreflightDisposition.COLLAPSE_RETRIEVAL_CONE,
        ),
    )
    for predicate, disposition in rules:
        if predicate:
            return disposition
    return FutureReadPreflightDisposition.FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE


def admit_alias_stable_future_read_currentness_probe(
    *,
    handoff_semantic_head: str,
    handoff: HydratedVersionHandoffReceiptV1,
    progress: AliasAwareRetrievalProgressProjectionV1,
    binding: HandoffSourceRouteAliasBindingProjectionV1 | None,
    intent: FutureReadCurrentnessProbeIntentV1,
) -> FutureReadCurrentnessPreflightReceiptV1:
    """Admit only the bounded *attempt* to resolve carried future-read currentness debt."""

    progress.validate()
    intent.validate()
    if binding is not None:
        binding.validate()

    a = _classify_tree(
        handoff_semantic_head=handoff_semantic_head,
        handoff=handoff,
        progress=progress,
        binding=binding,
        intent=intent,
    )
    b = _classify_rules(
        handoff_semantic_head=handoff_semantic_head,
        handoff=handoff,
        progress=progress,
        binding=binding,
        intent=intent,
    )
    if a is not b:
        raise RuntimeError("DIFFERENT_J_FUTURE_READ_PREFLIGHT_DIVERGED")

    reason = {
        FutureReadPreflightDisposition.FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE:
            "handoff read debt, source-route binding, requested axes, and alias-aware retrieval progress commute; probe only",
        FutureReadPreflightDisposition.HOLD_PARENT_GENERATION:
            "parent semantic generation mismatch",
        FutureReadPreflightDisposition.HOLD_HANDOFF_NOT_READY:
            "hydrated version handoff is not ready candidate",
        FutureReadPreflightDisposition.HOLD_READ_DEBT_NOT_CARRIED:
            "mandatory future read-currentness debt is not carried exactly",
        FutureReadPreflightDisposition.HOLD_READ_AXES_MISMATCH:
            "requested currentness axes do not exactly match carried read debt",
        FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_REQUIRED:
            "handoff source to current route/SID binding is required",
        FutureReadPreflightDisposition.HOLD_SOURCE_BINDING_MISMATCH:
            "handoff subject/evidence/source or current route does not match binding projection",
        FutureReadPreflightDisposition.HOLD_ALIAS_RESOLUTION_REQUIRED:
            "route alias resolution remains unresolved",
        FutureReadPreflightDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED:
            "retrieval produced no independent progress and must change a true axis",
        FutureReadPreflightDisposition.COLLAPSE_RETRIEVAL_CONE:
            "repeated alias-quotiented no-progress retrieval collapses this probe cone",
        FutureReadPreflightDisposition.HOLD_CLAIM_CEILING:
            "upstream handoff exceeds nonpromotion ceiling",
    }[a]

    admissible = (
        a
        is FutureReadPreflightDisposition.FUTURE_READ_CURRENTNESS_PROBE_ADMISSIBLE_CANDIDATE
    )
    binding_digest = binding.binding_digest if binding is not None else None
    body = {
        "schema": SCHEMA,
        "parent_semantic_heads": [PR759_SEMANTIC_HEAD, PR760_SEMANTIC_HEAD],
        "parent_proofs": {
            "pr759": [PR759_PROOF_HEAD, PR759_PROOF_RUN, PR759_PROOF_JOB],
            "pr760": [PR760_PROOF_RUN, PR760_PROOF_JOB],
        },
        "disposition": a.value,
        "reason": reason,
        "handoff_digest": handoff.handoff_digest,
        "alias_progress_semantic_fingerprint_digest": progress.semantic_fingerprint_digest,
        "current_view_digest": progress.current_view_digest,
        "source_binding_digest": binding_digest,
        "subject_key": handoff.subject_key if admissible else None,
        "evidence_generation_key": handoff.evidence_generation_key if admissible else None,
        "requested_future_read_axes": intent.requested_future_read_axes,
        "requested_eki2_read_axes": intent.requested_eki2_read_axes,
        "claim_ceiling": {
            "probe_admissible_candidate": admissible,
            "read_currentness_debt_carried": True,
            "source_currentness_proven": False,
            "read_currentness_proven": False,
            "semantic_truth_proven": False,
            "evidence_admitted": False,
            "source_owner_authenticated_by_this_contract": False,
            "retrieval_executed": False,
            "materialization_executed": False,
            "persistent_use_authorized": False,
            "authorization_issued": False,
            "effect_authorized": False,
            "semantic_k27_authority_minted": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    receipt = FutureReadCurrentnessPreflightReceiptV1(
        schema=SCHEMA,
        disposition=a,
        reason=reason,
        handoff_digest=handoff.handoff_digest,
        alias_progress_semantic_fingerprint_digest=progress.semantic_fingerprint_digest,
        current_view_digest=progress.current_view_digest,
        source_binding_digest=binding_digest,
        subject_key=handoff.subject_key if admissible else None,
        evidence_generation_key=handoff.evidence_generation_key if admissible else None,
        requested_future_read_axes=intent.requested_future_read_axes,
        requested_eki2_read_axes=intent.requested_eki2_read_axes,
        probe_receipt_digest=_sha(SCHEMA, body),
        probe_admissible_candidate=admissible,
    )
    receipt.validate()
    return receipt


def prove_different_j() -> int:
    """Exhaust the minimum consequence-changing finite cross-product (192 states)."""

    d0, d1, d2, d3 = (ch * 64 for ch in "0123")
    base_handoff = HydratedVersionHandoffReceiptV1(
        disposition=HandoffDisposition.HANDOFF_READY_CANDIDATE,
        reason="ready",
        hydration_completion_digest=d0,
        transition_receipt_digest=d1,
        subject_key=d0,
        evidence_generation_key=d1,
        material_digest=d2,
        exact_source_uri="https://example.test/source",
        future_read_axes=EXPECTED_FUTURE_AXES,
        eki2_read_axes=EXPECTED_EKI2_AXES,
        handoff_digest=d3,
    )
    decisions = tuple(AliasProgressDecision)
    checked = 0
    for handoff_ready in (False, True):
        for subject_match in (False, True):
            for binding_match in (False, True):
                for axes_match in (False, True):
                    for binding_current in (False, True):
                        for decision in decisions:
                            handoff = HydratedVersionHandoffReceiptV1(
                                **{
                                    **asdict(base_handoff),
                                    "disposition": (
                                        HandoffDisposition.HANDOFF_READY_CANDIDATE
                                        if handoff_ready
                                        else HandoffDisposition.HOLD_TRANSITION_NOT_READY
                                    ),
                                }
                            )
                            progress = AliasAwareRetrievalProgressProjectionV1(
                                schema=ALIAS_PROGRESS_SCHEMA,
                                semantic_owner_head=PR759_SEMANTIC_HEAD,
                                proof_head=PR759_PROOF_HEAD,
                                proof_run=PR759_PROOF_RUN,
                                proof_job=PR759_PROOF_JOB,
                                decision=decision,
                                current_view_digest=d2,
                                semantic_fingerprint_digest=d3,
                                source_sid_same=True,
                                route_projection_changed=True,
                                alias_projection_required=True,
                                alias_projection_consumed=(
                                    decision
                                    is not AliasProgressDecision.HOLD_ALIAS_RESOLUTION_REQUIRED
                                ),
                                prior_no_progress_count=0,
                                next_no_progress_count=0,
                            )
                            binding = HandoffSourceRouteAliasBindingProjectionV1(
                                schema=BINDING_SCHEMA,
                                subject_key=d0 if binding_match and subject_match else d1,
                                evidence_generation_key=d1,
                                exact_source_uri="https://example.test/source",
                                handoff_source_view_canonical_key="https://example.test/source",
                                handoff_source_view_digest=d0,
                                current_view_digest=d2 if binding_match else d3,
                                source_sid="sid:source",
                                owner_ref="source-owner",
                                owner_generation="owner-g1",
                                owner_receipt_digest=d3,
                                owner_state=(
                                    "RESOLVED_CURRENT_PROJECTION"
                                    if binding_current
                                    else "STALE_PROJECTION"
                                ),
                            )
                            intent = FutureReadCurrentnessProbeIntentV1(
                                subject_key=d0 if subject_match else d1,
                                evidence_generation_key=d1,
                                requested_future_read_axes=(
                                    EXPECTED_FUTURE_AXES if axes_match else ("wrong",)
                                ),
                                requested_eki2_read_axes=EXPECTED_EKI2_AXES,
                            )
                            # Stale bindings fail shape validation before classification; model
                            # that state as a missing binding for the two classifier forms.
                            b_for_classifier = binding if binding_current else None
                            a = _classify_tree(
                                handoff_semantic_head=PR760_SEMANTIC_HEAD,
                                handoff=handoff,
                                progress=progress,
                                binding=b_for_classifier,
                                intent=intent,
                            )
                            b = _classify_rules(
                                handoff_semantic_head=PR760_SEMANTIC_HEAD,
                                handoff=handoff,
                                progress=progress,
                                binding=b_for_classifier,
                                intent=intent,
                            )
                            if a is not b:
                                raise AssertionError("DIFFERENT_J_FUTURE_READ_PREFLIGHT_MISMATCH")
                            checked += 1
    return checked


LAWS = (
    "HandoffReadyCandidate!=PersistentUseReady",
    "FutureReadDebtCarried!=FutureReadDebtResolved",
    "RouteAliasRotationCannotPayFutureReadCurrentnessDebt",
    "AliasAwareRetrievalProgress!=ReadCurrentnessWitness",
    "ExactRequestedReadAxesMustEqualCarriedDebtAxes",
    "HandoffSourceMustBindCurrentRouteBeforeProbeAdmission",
    "NoProgressDebtSurvivesAliasQuotientIntoFutureReadPreflight",
    "ProbeAdmission!=ReadCurrentness!=EvidenceAdmission!=UseAuthority",
    "K27Placement!=SemanticIdentity!=VersionOrder!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
