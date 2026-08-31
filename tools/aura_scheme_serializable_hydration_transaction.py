#!/usr/bin/env python3
"""Scheme-serializable, loop-safe hydration transaction membrane.

D0 / HS1 / NONPROMOTING.

Semantic parent artifacts (Aura Drive 2):
- Objective 5: SchemeSerializableRouteProjectionAddendumV1.
- Serializable, Loop-Safe Minimum Hydration Preflight.

This module owns only their consequence-distinct join. It does not own K27
resolution, source currentness, retrieval execution, materialization, evidence
admission, authorization, or effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Optional

SCHEMA = "AURA-SCHEME-SERIALIZABLE-HYDRATION-TRANSACTION-v1"
ROUTE_SCHEMA = "AURA-SCHEME-BOUND-ROUTE-PROJECTION-v1"
RETRIEVAL_SCHEMA = "AURA-RETRIEVAL-PROGRESS-PROJECTION-v1"
HEX = frozenset("0123456789abcdef")

PARENT_OBJECTIVE_5_DRIVE_ID = "1cYsTW4R6Mz46A5DMpVgX86l7aJdrcFzKc7Ooy4KFAVo"
PARENT_LOOP_SAFE_PREFLIGHT_DRIVE_ID = "1uJHYkJDS9M0DvrteqJCzabjondPh-QC9NV05NNvK2PQ"


class RetrievalProgressDisposition(str, Enum):
    ALLOW_INITIAL = "ALLOW_INITIAL"
    ALLOW_CHANGED_AXIS = "ALLOW_CHANGED_AXIS"
    ALLOW_STATE_TRANSITION = "ALLOW_STATE_TRANSITION"
    CHANGE_AXIS_REQUIRED = "CHANGE_AXIS_REQUIRED"
    COLLAPSE_CONE = "COLLAPSE_CONE"


class HydrationTransactionDisposition(str, Enum):
    ADMIT_BOUNDED_TRANSACTION = "ADMIT_BOUNDED_TRANSACTION"
    HOLD_SOURCE_IDENTITY_MISMATCH = "HOLD_SOURCE_IDENTITY_MISMATCH"
    HOLD_OWNER_EPOCH_CHANGED = "HOLD_OWNER_EPOCH_CHANGED"
    HOLD_ROUTE_RECOMPUTE = "HOLD_ROUTE_RECOMPUTE"
    HOLD_REOPEN_BINDING_REQUIRED = "HOLD_REOPEN_BINDING_REQUIRED"
    HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED = "HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
    COLLAPSE_RETRIEVAL_CONE = "COLLAPSE_RETRIEVAL_CONE"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(domain: str, value: object) -> str:
    return hashlib.sha256(_canonical({"domain": domain, "value": value})).hexdigest()


def _text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _digest(value: str, code: str) -> str:
    value = _text(value, code)
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class SchemeBoundRouteProjection:
    """Routing/currentness projection. Coordinate placement is never authority."""

    schema: str
    source_identity: str
    scheme_id: str
    normalization_version: str
    canonical_key: str
    full_digest: str
    coordinate_view_digest: str
    k27_path: str
    route_generation: str
    owner_epoch: str
    route_current: bool
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    semantic_k27_authority: bool = False
    authorization_issued: bool = False
    effect_authorized: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != ROUTE_SCHEMA:
            raise ValueError("ROUTE_PROJECTION_SCHEMA_MISMATCH")
        for value, code in (
            (self.source_identity, "SOURCE_IDENTITY_REQUIRED"),
            (self.scheme_id, "SCHEME_ID_REQUIRED"),
            (self.normalization_version, "NORMALIZATION_VERSION_REQUIRED"),
            (self.canonical_key, "CANONICAL_KEY_REQUIRED"),
            (self.k27_path, "K27_PATH_REQUIRED"),
            (self.route_generation, "ROUTE_GENERATION_REQUIRED"),
            (self.owner_epoch, "OWNER_EPOCH_REQUIRED"),
        ):
            _text(value, code)
        _digest(self.full_digest, "FULL_DIGEST_REQUIRED")
        _digest(self.coordinate_view_digest, "COORDINATE_VIEW_DIGEST_REQUIRED")
        if not isinstance(self.route_current, bool):
            raise ValueError("ROUTE_CURRENT_MUST_BE_BOOL")
        if any(
            (
                self.source_currentness_proven,
                self.semantic_truth_proven,
                self.semantic_k27_authority,
                self.authorization_issued,
                self.effect_authorized,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("ROUTE_PROJECTION_EXCEEDED_NONPROMOTION_CEILING")

    @property
    def projection_digest(self) -> str:
        self.validate()
        return _sha(ROUTE_SCHEMA, asdict(self))

    @property
    def scheme_identity(self) -> tuple[str, str, str, str]:
        self.validate()
        return (
            self.scheme_id,
            self.normalization_version,
            self.canonical_key,
            self.full_digest,
        )


@dataclass(frozen=True)
class RetrievalProgressProjection:
    """Projection from an upstream retrieval-progress owner; truth is not minted."""

    schema: str
    disposition: RetrievalProgressDisposition
    fingerprint_digest: str
    provider_state_generation: str
    evidence_digest: str
    next_no_progress_count: int
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    authority_granted: bool = False
    effect_authority_granted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != RETRIEVAL_SCHEMA:
            raise ValueError("RETRIEVAL_PROGRESS_SCHEMA_MISMATCH")
        if not isinstance(self.disposition, RetrievalProgressDisposition):
            raise ValueError("RETRIEVAL_DISPOSITION_INVALID")
        _digest(self.fingerprint_digest, "RETRIEVAL_FINGERPRINT_DIGEST_REQUIRED")
        _text(self.provider_state_generation, "PROVIDER_STATE_GENERATION_REQUIRED")
        _digest(self.evidence_digest, "RETRIEVAL_EVIDENCE_DIGEST_REQUIRED")
        if (
            not isinstance(self.next_no_progress_count, int)
            or isinstance(self.next_no_progress_count, bool)
            or self.next_no_progress_count < 0
        ):
            raise ValueError("NEXT_NO_PROGRESS_COUNT_INVALID")
        if any(
            (
                self.source_currentness_proven,
                self.semantic_truth_proven,
                self.authority_granted,
                self.effect_authority_granted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("RETRIEVAL_PROJECTION_EXCEEDED_NONPROMOTION_CEILING")


@dataclass(frozen=True)
class HydrationIntentProjection:
    semantic_plan_digest: str
    evidence_generation_key: str
    target_level: int
    new_hydration_required: bool
    exact_reopen_handle: Optional[str]

    def validate(self) -> None:
        _digest(self.semantic_plan_digest, "SEMANTIC_PLAN_DIGEST_REQUIRED")
        _text(self.evidence_generation_key, "EVIDENCE_GENERATION_KEY_REQUIRED")
        if (
            not isinstance(self.target_level, int)
            or isinstance(self.target_level, bool)
            or not 0 <= self.target_level <= 4
        ):
            raise ValueError("TARGET_LEVEL_MUST_BE_0_TO_4")
        if not isinstance(self.new_hydration_required, bool):
            raise ValueError("NEW_HYDRATION_REQUIRED_MUST_BE_BOOL")
        if self.exact_reopen_handle is not None:
            _text(self.exact_reopen_handle, "EXACT_REOPEN_HANDLE_INVALID")


@dataclass(frozen=True)
class SchemeSerializableHydrationTransactionReceipt:
    schema: str
    disposition: HydrationTransactionDisposition
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
        if self.schema != SCHEMA:
            raise ValueError("HYDRATION_TRANSACTION_SCHEMA_MISMATCH")
        _text(self.source_identity, "SOURCE_IDENTITY_REQUIRED")
        _digest(self.pre_route_projection_digest, "PRE_ROUTE_DIGEST_REQUIRED")
        _digest(self.post_route_projection_digest, "POST_ROUTE_DIGEST_REQUIRED")
        _text(self.owner_epoch, "OWNER_EPOCH_REQUIRED")
        _digest(self.semantic_plan_digest, "SEMANTIC_PLAN_DIGEST_REQUIRED")
        _text(self.evidence_generation_key, "EVIDENCE_GENERATION_KEY_REQUIRED")
        _digest(self.retrieval_fingerprint_digest, "RETRIEVAL_FINGERPRINT_DIGEST_REQUIRED")
        _digest(self.retrieval_evidence_digest, "RETRIEVAL_EVIDENCE_DIGEST_REQUIRED")
        if self.exact_reopen_handle_digest is not None:
            _digest(self.exact_reopen_handle_digest, "REOPEN_HANDLE_DIGEST_INVALID")
        if self.bounded_transaction_admitted != (
            self.disposition is HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION
        ):
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
            raise ValueError("HYDRATION_TRANSACTION_EXCEEDED_NONPROMOTION_CEILING")


def _classify_tree(
    *,
    pre: SchemeBoundRouteProjection,
    post: SchemeBoundRouteProjection,
    retrieval: RetrievalProgressProjection,
    intent: HydrationIntentProjection,
) -> HydrationTransactionDisposition:
    if pre.source_identity != post.source_identity:
        return HydrationTransactionDisposition.HOLD_SOURCE_IDENTITY_MISMATCH
    if pre.owner_epoch != post.owner_epoch:
        return HydrationTransactionDisposition.HOLD_OWNER_EPOCH_CHANGED
    if (
        pre.scheme_identity != post.scheme_identity
        or pre.coordinate_view_digest != post.coordinate_view_digest
        or pre.k27_path != post.k27_path
        or pre.route_generation != post.route_generation
        or not pre.route_current
        or not post.route_current
    ):
        return HydrationTransactionDisposition.HOLD_ROUTE_RECOMPUTE
    if intent.new_hydration_required and not intent.exact_reopen_handle:
        return HydrationTransactionDisposition.HOLD_REOPEN_BINDING_REQUIRED
    if retrieval.disposition is RetrievalProgressDisposition.CHANGE_AXIS_REQUIRED:
        return HydrationTransactionDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED
    if retrieval.disposition is RetrievalProgressDisposition.COLLAPSE_CONE:
        return HydrationTransactionDisposition.COLLAPSE_RETRIEVAL_CONE
    return HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION


def _classify_table(
    *,
    pre: SchemeBoundRouteProjection,
    post: SchemeBoundRouteProjection,
    retrieval: RetrievalProgressProjection,
    intent: HydrationIntentProjection,
) -> HydrationTransactionDisposition:
    source_same = pre.source_identity == post.source_identity
    epoch_same = pre.owner_epoch == post.owner_epoch
    route_same = (
        pre.scheme_identity == post.scheme_identity
        and pre.coordinate_view_digest == post.coordinate_view_digest
        and pre.k27_path == post.k27_path
        and pre.route_generation == post.route_generation
        and pre.route_current
        and post.route_current
    )
    reopen_ok = (not intent.new_hydration_required) or bool(intent.exact_reopen_handle)
    retrieval_state = retrieval.disposition

    ordered = (
        (not source_same, HydrationTransactionDisposition.HOLD_SOURCE_IDENTITY_MISMATCH),
        (source_same and not epoch_same, HydrationTransactionDisposition.HOLD_OWNER_EPOCH_CHANGED),
        (source_same and epoch_same and not route_same, HydrationTransactionDisposition.HOLD_ROUTE_RECOMPUTE),
        (source_same and epoch_same and route_same and not reopen_ok, HydrationTransactionDisposition.HOLD_REOPEN_BINDING_REQUIRED),
        (
            source_same
            and epoch_same
            and route_same
            and reopen_ok
            and retrieval_state is RetrievalProgressDisposition.CHANGE_AXIS_REQUIRED,
            HydrationTransactionDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
        ),
        (
            source_same
            and epoch_same
            and route_same
            and reopen_ok
            and retrieval_state is RetrievalProgressDisposition.COLLAPSE_CONE,
            HydrationTransactionDisposition.COLLAPSE_RETRIEVAL_CONE,
        ),
    )
    for predicate, disposition in ordered:
        if predicate:
            return disposition
    return HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION


def admit_scheme_serializable_hydration_transaction(
    *,
    pre_route: SchemeBoundRouteProjection,
    post_route: SchemeBoundRouteProjection,
    retrieval: RetrievalProgressProjection,
    intent: HydrationIntentProjection,
) -> SchemeSerializableHydrationTransactionReceipt:
    """Admit only a stable-route, stable-epoch, novelty-capable hydration transaction."""

    pre_route.validate()
    post_route.validate()
    retrieval.validate()
    intent.validate()

    a = _classify_tree(pre=pre_route, post=post_route, retrieval=retrieval, intent=intent)
    b = _classify_table(pre=pre_route, post=post_route, retrieval=retrieval, intent=intent)
    if a is not b:
        raise RuntimeError("Different-J scheme-serializable transaction classifiers diverged")

    reason = {
        HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION: "ROUTE_EPOCH_AND_RETRIEVAL_NOVELTY_GATES_COMMUTE",
        HydrationTransactionDisposition.HOLD_SOURCE_IDENTITY_MISMATCH: "SOURCE_IDENTITY_CHANGED_DURING_TRANSACTION",
        HydrationTransactionDisposition.HOLD_OWNER_EPOCH_CHANGED: "OWNER_EPOCH_CHANGED_DURING_TRANSACTION",
        HydrationTransactionDisposition.HOLD_ROUTE_RECOMPUTE: "SCHEME_OR_ROUTE_PROJECTION_CHANGED_RECOMPUTE_REQUIRED",
        HydrationTransactionDisposition.HOLD_REOPEN_BINDING_REQUIRED: "NEW_HYDRATION_REQUIRES_EXACT_REOPEN_HANDLE",
        HydrationTransactionDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED: "IDENTICAL_NO_PROGRESS_RETRIEVAL_MUST_CHANGE_AXIS",
        HydrationTransactionDisposition.COLLAPSE_RETRIEVAL_CONE: "REPEATED_IDENTICAL_NO_PROGRESS_RETRIEVAL_COLLAPSES_CONE",
    }[a]

    reopen_digest = (
        _sha("AURA-EXACT-REOPEN-HANDLE-v1", intent.exact_reopen_handle)
        if intent.exact_reopen_handle
        else None
    )
    payload = {
        "schema": SCHEMA,
        "parent_drive_ids": [
            PARENT_OBJECTIVE_5_DRIVE_ID,
            PARENT_LOOP_SAFE_PREFLIGHT_DRIVE_ID,
        ],
        "disposition": a.value,
        "reason": reason,
        "source_identity": pre_route.source_identity,
        "pre_route_projection_digest": pre_route.projection_digest,
        "post_route_projection_digest": post_route.projection_digest,
        "owner_epoch": pre_route.owner_epoch,
        "semantic_plan_digest": intent.semantic_plan_digest,
        "evidence_generation_key": intent.evidence_generation_key,
        "target_level": intent.target_level,
        "retrieval_fingerprint_digest": retrieval.fingerprint_digest,
        "retrieval_evidence_digest": retrieval.evidence_digest,
        "retrieval_disposition": retrieval.disposition.value,
        "exact_reopen_handle_digest": reopen_digest,
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
    receipt = SchemeSerializableHydrationTransactionReceipt(
        schema=SCHEMA,
        disposition=a,
        reason=reason,
        source_identity=pre_route.source_identity,
        pre_route_projection_digest=pre_route.projection_digest,
        post_route_projection_digest=post_route.projection_digest,
        owner_epoch=pre_route.owner_epoch,
        semantic_plan_digest=intent.semantic_plan_digest,
        evidence_generation_key=intent.evidence_generation_key,
        target_level=intent.target_level,
        retrieval_fingerprint_digest=retrieval.fingerprint_digest,
        retrieval_evidence_digest=retrieval.evidence_digest,
        retrieval_disposition=retrieval.disposition.value,
        exact_reopen_handle_digest=reopen_digest,
        transaction_digest=_sha(SCHEMA, payload),
        bounded_transaction_admitted=a is HydrationTransactionDisposition.ADMIT_BOUNDED_TRANSACTION,
    )
    receipt.validate()
    return receipt


def prove_different_j() -> int:
    digest_a = "a" * 64
    digest_b = "b" * 64
    checked = 0
    retrieval_states = tuple(RetrievalProgressDisposition)
    for source_same in (False, True):
        for epoch_same in (False, True):
            for route_same in (False, True):
                for reopen_present in (False, True):
                    for retrieval_state in retrieval_states:
                        pre = SchemeBoundRouteProjection(
                            ROUTE_SCHEMA,
                            "source:A",
                            "scheme-v1",
                            "norm-v1",
                            "key:A",
                            digest_a,
                            digest_a,
                            "K27://1/2/3",
                            "route-g1",
                            "epoch-1",
                            True,
                        )
                        post = SchemeBoundRouteProjection(
                            ROUTE_SCHEMA,
                            "source:A" if source_same else "source:B",
                            "scheme-v1" if route_same else "scheme-v2",
                            "norm-v1",
                            "key:A",
                            digest_a,
                            digest_a if route_same else digest_b,
                            "K27://1/2/3" if route_same else "K27://1/2/4",
                            "route-g1" if route_same else "route-g2",
                            "epoch-1" if epoch_same else "epoch-2",
                            True,
                        )
                        retrieval = RetrievalProgressProjection(
                            RETRIEVAL_SCHEMA,
                            retrieval_state,
                            digest_a,
                            "provider-g1",
                            digest_b,
                            0,
                        )
                        intent = HydrationIntentProjection(
                            digest_a,
                            "evidence-g1",
                            2,
                            True,
                            "https://example.invalid/source" if reopen_present else None,
                        )
                        a = _classify_tree(pre=pre, post=post, retrieval=retrieval, intent=intent)
                        b = _classify_table(pre=pre, post=post, retrieval=retrieval, intent=intent)
                        if a is not b:
                            raise AssertionError("Different-J mismatch")
                        checked += 1
    return checked


LAWS = (
    "SourceIdentityStableAcrossSchemeAliases",
    "SameSource+DifferentScheme=>RouteRecomputeNotSemanticDivergence",
    "SchemeMigrationRequiresAppendOnlyProjectionSupersession",
    "OwnerEpochMustRemainStableAcrossHydrationReadSet",
    "NewHydrationRequiresExactReopenHandle",
    "RepeatedRetrievalWithoutIndependentStateDelta!=Progress",
    "RetrievalAxisChange!=SourceCurrentnessProof",
    "K27Path!=SemanticIdentity!=Authority",
    "HydrationTransactionAdmission!=Materialization!=EvidenceAdmission!=EffectAuthority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
