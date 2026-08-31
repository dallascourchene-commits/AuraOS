#!/usr/bin/env python3
"""Bind retrieval progress to semantic source identity, not K27 route aliases.

D0 / HS1 / NONPROMOTING.

Exactly two post-cut other-Agent artifacts define this residual:
- PR #754: repeated retrieval without a true axis/state/evidence transition accrues
  no-progress debt and eventually collapses the cone.
- NAV09 scheme-bound external-coordinate envelope (Aura Drive 2): one source SID may
  lawfully have multiple scheme/version-bound routing projections; coordinate changes
  are not semantic source changes.

This additive guard does not own source identity, alias verification, K27 placement,
retrieval execution, currentness, truth, or effects. Route aliases may only make retry
admission stricter. A caller-supplied SID change is never sufficient to mint progress:
without an independently changed non-resource axis or provider/evidence state it HOLDS.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
from typing import Optional

from tools.aura_retrieval_progress_guard import (
    RetrievalDecision,
    RetrievalFingerprint,
    RetrievalObservation,
    RetrievalProgressReceipt,
    assess_retrieval_progress,
)

SCHEMA = "AURA-RETRIEVAL-PROGRESS-K27-ALIAS-GUARD-v1"
VIEW_SCHEMA = "AURA-K27-SCHEME-BOUND-COORDINATE-VIEW-PROJECTION-v1"
ALIAS_SCHEMA = "AURA-K27-PROJECTION-ALIAS-OWNER-PROJECTION-v1"
NAV09_DRIVE_ARTIFACT_ID = "1eP6rlOLkJgkPs4ZXZa-OUQsdYrubXOiPhjgavx-nWy8"
HEX = frozenset("0123456789abcdef")


class AliasAwareDecision(str, Enum):
    ALLOW_INITIAL = RetrievalDecision.ALLOW_INITIAL.value
    ALLOW_CHANGED_AXIS = RetrievalDecision.ALLOW_CHANGED_AXIS.value
    ALLOW_STATE_TRANSITION = RetrievalDecision.ALLOW_STATE_TRANSITION.value
    CHANGE_AXIS_REQUIRED = RetrievalDecision.CHANGE_AXIS_REQUIRED.value
    COLLAPSE_CONE = RetrievalDecision.COLLAPSE_CONE.value
    HOLD_ALIAS_RESOLUTION_REQUIRED = "HOLD_ALIAS_RESOLUTION_REQUIRED"
    HOLD_SOURCE_IDENTITY_TRANSITION_REQUIRED = "HOLD_SOURCE_IDENTITY_TRANSITION_REQUIRED"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _hash(domain: str, value: object) -> str:
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


def _xyz(value: tuple[int, int, int]) -> tuple[int, int, int]:
    if not isinstance(value, tuple) or len(value) != 3:
        raise ValueError("K27_XYZ_MUST_BE_THREE_TUPLE")
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < 27 for v in value):
        raise ValueError("K27_XYZ_COMPONENT_OUT_OF_RANGE")
    return value


@dataclass(frozen=True)
class SchemeBoundCoordinateViewProjection:
    """Scheme/version-bound route projection supplied by an upstream K27 owner.

    Full digest is verified against the declared canonical key. The xyz mapping itself
    is not rederived because NAV09 leaves canonical MOD27 mapping ownership outside this
    addendum. Source identity is also not authenticated by this contract.
    """

    schema: str
    scheme_id: str
    normalization_version: str
    canonical_key: str
    full_digest: str
    xyz: tuple[int, int, int]
    source_sid: str
    source_binding_generation: str
    source_binding_receipt_digest: str
    relation_type: str = "RESOLVES_TO"
    source_identity_authenticated_by_this_contract: bool = False
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    routing_authority_granted: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != VIEW_SCHEMA:
            raise ValueError("K27_VIEW_SCHEMA_MISMATCH")
        for value, code in (
            (self.scheme_id, "K27_SCHEME_ID_REQUIRED"),
            (self.normalization_version, "K27_NORMALIZATION_VERSION_REQUIRED"),
            (self.canonical_key, "K27_CANONICAL_KEY_REQUIRED"),
            (self.source_sid, "K27_SOURCE_SID_REQUIRED"),
            (self.source_binding_generation, "K27_SOURCE_BINDING_GENERATION_REQUIRED"),
        ):
            _text(value, code)
        _digest(self.full_digest, "K27_FULL_DIGEST_INVALID")
        _digest(self.source_binding_receipt_digest, "K27_SOURCE_BINDING_RECEIPT_INVALID")
        _xyz(self.xyz)
        expected = hashlib.sha256(self.canonical_key.encode("utf-8")).hexdigest()
        if self.full_digest != expected:
            raise ValueError("K27_CANONICAL_KEY_FULL_DIGEST_MISMATCH")
        if self.relation_type not in {"RESOLVES_TO", "SUPERSEDED_FOR_ROUTING_BY"}:
            raise ValueError("K27_VIEW_RELATION_TYPE_UNSUPPORTED")
        if any(
            (
                self.source_identity_authenticated_by_this_contract,
                self.source_currentness_proven,
                self.semantic_truth_proven,
                self.routing_authority_granted,
                self.effect_authority_granted,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("K27_VIEW_EXCEEDED_NONPROMOTION_CEILING")

    @property
    def view_digest(self) -> str:
        self.validate()
        return _hash(VIEW_SCHEMA, asdict(self))

    @property
    def resource_token(self) -> str:
        return f"k27view:{self.view_digest}"


@dataclass(frozen=True)
class ProjectionAliasOwnerProjection:
    """Opaque upstream projection relating two route views to one source SID.

    Internal identity/currentness shape is checked, but source-owner authentication is not
    performed here. The projection is therefore permitted only to *remove* artificial route
    progress (or cause a HOLD), never to create a new allow.
    """

    schema: str
    view_digests: tuple[str, str]
    source_sid: str
    owner_ref: str
    owner_generation: str
    owner_receipt_digest: str
    relation_type: str
    owner_state: str = "RESOLVED_CURRENT_PROJECTION"
    owner_authenticated_by_this_contract: bool = False
    source_truth_proven: bool = False
    source_currentness_proven_by_this_contract: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != ALIAS_SCHEMA:
            raise ValueError("K27_ALIAS_SCHEMA_MISMATCH")
        if not isinstance(self.view_digests, tuple) or len(self.view_digests) != 2:
            raise ValueError("K27_ALIAS_REQUIRES_TWO_VIEW_DIGESTS")
        for value in self.view_digests:
            _digest(value, "K27_ALIAS_VIEW_DIGEST_INVALID")
        if tuple(sorted(set(self.view_digests))) != self.view_digests:
            raise ValueError("K27_ALIAS_VIEW_DIGESTS_MUST_BE_SORTED_UNIQUE")
        for value, code in (
            (self.source_sid, "K27_ALIAS_SOURCE_SID_REQUIRED"),
            (self.owner_ref, "K27_ALIAS_OWNER_REF_REQUIRED"),
            (self.owner_generation, "K27_ALIAS_OWNER_GENERATION_REQUIRED"),
        ):
            _text(value, code)
        _digest(self.owner_receipt_digest, "K27_ALIAS_OWNER_RECEIPT_INVALID")
        if self.relation_type not in {"ALIASABLE_PROJECTIONS", "SUPERSEDED_FOR_ROUTING_BY"}:
            raise ValueError("K27_ALIAS_RELATION_UNSUPPORTED")
        if self.owner_state != "RESOLVED_CURRENT_PROJECTION":
            raise ValueError("K27_ALIAS_OWNER_PROJECTION_NOT_CURRENT")
        if any(
            (
                self.owner_authenticated_by_this_contract,
                self.source_truth_proven,
                self.source_currentness_proven_by_this_contract,
                self.effect_authority_granted,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("K27_ALIAS_EXCEEDED_NONPROMOTION_CEILING")

    @property
    def projection_digest(self) -> str:
        self.validate()
        return _hash(ALIAS_SCHEMA, asdict(self))


@dataclass(frozen=True)
class AliasAwareRetrievalProgressReceipt:
    schema: str
    decision: AliasAwareDecision
    reason: str
    raw_decision: Optional[str]
    semantic_decision: Optional[str]
    raw_fingerprint_digest: Optional[str]
    previous_view_digest: Optional[str]
    current_view_digest: str
    source_sid_same: bool
    route_projection_changed: bool
    alias_projection_required: bool
    alias_projection_consumed: bool
    alias_projection_digest: Optional[str]
    semantic_fingerprint_digest: str
    prior_no_progress_count: int
    next_no_progress_count: int
    receipt_digest: str
    source_identity_authenticated_by_this_contract: bool = False
    alias_owner_authenticated_by_this_contract: bool = False
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    authority_granted: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_claim_ceiling(self) -> None:
        _digest(self.current_view_digest, "CURRENT_VIEW_DIGEST_INVALID")
        if self.previous_view_digest is not None:
            _digest(self.previous_view_digest, "PREVIOUS_VIEW_DIGEST_INVALID")
        if self.raw_fingerprint_digest is not None:
            _digest(self.raw_fingerprint_digest, "RAW_FINGERPRINT_DIGEST_INVALID")
        _digest(self.semantic_fingerprint_digest, "SEMANTIC_FINGERPRINT_DIGEST_INVALID")
        _digest(self.receipt_digest, "ALIAS_AWARE_RECEIPT_DIGEST_INVALID")
        if self.alias_projection_digest is not None:
            _digest(self.alias_projection_digest, "ALIAS_PROJECTION_DIGEST_INVALID")
        if self.alias_projection_consumed and not self.alias_projection_required:
            raise ValueError("ALIAS_PROJECTION_CONSUMED_WHEN_NOT_REQUIRED")
        if self.decision is AliasAwareDecision.HOLD_ALIAS_RESOLUTION_REQUIRED:
            if not self.alias_projection_required or self.alias_projection_consumed:
                raise ValueError("ALIAS_HOLD_STATE_INCONSISTENT")
        if self.decision is AliasAwareDecision.HOLD_SOURCE_IDENTITY_TRANSITION_REQUIRED:
            if self.source_sid_same:
                raise ValueError("SOURCE_IDENTITY_HOLD_REQUIRES_DIFFERENT_SID")
        if any(
            (
                self.source_identity_authenticated_by_this_contract,
                self.alias_owner_authenticated_by_this_contract,
                self.source_currentness_proven,
                self.semantic_truth_proven,
                self.authority_granted,
                self.effect_authority_granted,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("ALIAS_AWARE_RETRIEVAL_EXCEEDED_NONPROMOTION_CEILING")


def _semantic_fingerprint(fingerprint: RetrievalFingerprint, resource: str) -> RetrievalFingerprint:
    return replace(fingerprint, resource=resource)


def _decision(value: RetrievalDecision) -> AliasAwareDecision:
    return AliasAwareDecision(value.value)


def _validate_route_binding(
    observation: RetrievalObservation,
    view: SchemeBoundCoordinateViewProjection,
    label: str,
) -> None:
    view.validate()
    if observation.fingerprint.resource != view.resource_token:
        raise ValueError(f"{label}_RETRIEVAL_RESOURCE_NOT_BOUND_TO_K27_VIEW")


def _alias_matches(
    alias: ProjectionAliasOwnerProjection,
    previous_view: SchemeBoundCoordinateViewProjection,
    current_view: SchemeBoundCoordinateViewProjection,
) -> None:
    alias.validate()
    expected = tuple(sorted((previous_view.view_digest, current_view.view_digest)))
    if alias.view_digests != expected:
        raise ValueError("K27_ALIAS_VIEW_SET_MISMATCH")
    if previous_view.source_sid != current_view.source_sid or alias.source_sid != current_view.source_sid:
        raise ValueError("K27_ALIAS_SOURCE_SID_MISMATCH")


def _receipt(
    *,
    decision: AliasAwareDecision,
    reason: str,
    raw: Optional[RetrievalProgressReceipt],
    semantic: Optional[RetrievalProgressReceipt],
    semantic_current_fingerprint_digest: str,
    previous_view: Optional[SchemeBoundCoordinateViewProjection],
    current_view: SchemeBoundCoordinateViewProjection,
    alias_required: bool,
    alias: Optional[ProjectionAliasOwnerProjection],
    prior_no_progress_count: int,
) -> AliasAwareRetrievalProgressReceipt:
    current_digest = current_view.view_digest
    previous_digest = previous_view.view_digest if previous_view is not None else None
    same_sid = bool(previous_view is not None and previous_view.source_sid == current_view.source_sid)
    route_changed = bool(previous_view is not None and previous_digest != current_digest)
    alias_digest = alias.projection_digest if alias is not None else None
    raw_fp_digest = raw.fingerprint_digest if raw is not None else None
    next_count = semantic.next_no_progress_count if semantic is not None else prior_no_progress_count
    body = {
        "decision": decision.value,
        "reason": reason,
        "raw_decision": raw.decision.value if raw is not None else None,
        "semantic_decision": semantic.decision.value if semantic is not None else None,
        "raw_fingerprint_digest": raw_fp_digest,
        "previous_view_digest": previous_digest,
        "current_view_digest": current_digest,
        "source_sid_same": same_sid,
        "route_projection_changed": route_changed,
        "alias_projection_required": alias_required,
        "alias_projection_consumed": alias is not None,
        "alias_projection_digest": alias_digest,
        "semantic_fingerprint_digest": semantic_current_fingerprint_digest,
        "prior_no_progress_count": prior_no_progress_count,
        "next_no_progress_count": next_count,
    }
    receipt = AliasAwareRetrievalProgressReceipt(
        schema=SCHEMA,
        decision=decision,
        reason=reason,
        raw_decision=raw.decision.value if raw is not None else None,
        semantic_decision=semantic.decision.value if semantic is not None else None,
        raw_fingerprint_digest=raw_fp_digest,
        previous_view_digest=previous_digest,
        current_view_digest=current_digest,
        source_sid_same=same_sid,
        route_projection_changed=route_changed,
        alias_projection_required=alias_required,
        alias_projection_consumed=alias is not None,
        alias_projection_digest=alias_digest,
        semantic_fingerprint_digest=semantic_current_fingerprint_digest,
        prior_no_progress_count=prior_no_progress_count,
        next_no_progress_count=next_count,
        receipt_digest=_hash(SCHEMA, body),
    )
    receipt.validate_claim_ceiling()
    return receipt


def assess_k27_alias_aware_retrieval_progress(
    *,
    previous: Optional[RetrievalObservation],
    current: RetrievalObservation,
    previous_view: Optional[SchemeBoundCoordinateViewProjection],
    current_view: SchemeBoundCoordinateViewProjection,
    alias_projection: Optional[ProjectionAliasOwnerProjection] = None,
    prior_no_progress_count: int = 0,
) -> AliasAwareRetrievalProgressReceipt:
    """Preserve #754 debt across aliases without trusting caller-minted SID changes.

    For same-SID route changes, an upstream alias projection is mandatory and the raw route
    resource is replaced by stable SID before delegating to #754. For different SIDs this
    contract deliberately removes *both* SID values from semantic resource comparison; a SID
    change alone therefore cannot create progress. Only an independent non-resource axis or
    provider/evidence state change may proceed; otherwise the transition HOLDS for a separate
    source-identity owner.
    """

    _validate_route_binding(current, current_view, "CURRENT")
    if previous is None:
        if previous_view is not None:
            raise ValueError("INITIAL_RETRIEVAL_CANNOT_HAVE_PREVIOUS_VIEW")
        if alias_projection is not None:
            raise ValueError("INITIAL_RETRIEVAL_CANNOT_CONSUME_ALIAS_PROJECTION")
        semantic_current_fp = _semantic_fingerprint(
            current.fingerprint, f"source-sid:{current_view.source_sid}"
        )
        semantic_current = replace(current, fingerprint=semantic_current_fp)
        semantic = assess_retrieval_progress(
            previous=None,
            current=semantic_current,
            prior_no_progress_count=prior_no_progress_count,
        )
        return _receipt(
            decision=_decision(semantic.decision),
            reason="INITIAL_SEMANTIC_SOURCE_RETRIEVAL",
            raw=semantic,
            semantic=semantic,
            semantic_current_fingerprint_digest=semantic_current_fp.digest,
            previous_view=None,
            current_view=current_view,
            alias_required=False,
            alias=None,
            prior_no_progress_count=prior_no_progress_count,
        )

    if previous_view is None:
        raise ValueError("PREVIOUS_VIEW_REQUIRED_FOR_NONINITIAL_RETRIEVAL")
    _validate_route_binding(previous, previous_view, "PREVIOUS")
    raw = assess_retrieval_progress(
        previous=previous,
        current=current,
        prior_no_progress_count=prior_no_progress_count,
    )
    same_sid = previous_view.source_sid == current_view.source_sid
    route_changed = previous_view.view_digest != current_view.view_digest
    alias_required = same_sid and route_changed

    if same_sid:
        semantic_resource = f"source-sid:{current_view.source_sid}"
        semantic_previous_fp = _semantic_fingerprint(previous.fingerprint, semantic_resource)
        semantic_current_fp = _semantic_fingerprint(current.fingerprint, semantic_resource)
    else:
        # SID values are explicitly untrusted here. Quotient them out so caller SID rotation
        # cannot become ALLOW_CHANGED_AXIS. Other fingerprint axes and provider/evidence state
        # remain visible to #754 and may independently establish progress.
        unresolved = "source-identity-transition:UNVERIFIED"
        semantic_previous_fp = _semantic_fingerprint(previous.fingerprint, unresolved)
        semantic_current_fp = _semantic_fingerprint(current.fingerprint, unresolved)

    semantic = assess_retrieval_progress(
        previous=replace(previous, fingerprint=semantic_previous_fp),
        current=replace(current, fingerprint=semantic_current_fp),
        prior_no_progress_count=prior_no_progress_count,
    )

    if alias_required and alias_projection is None:
        return _receipt(
            decision=AliasAwareDecision.HOLD_ALIAS_RESOLUTION_REQUIRED,
            reason="SAME_SID_ROUTE_CHANGED_WITHOUT_OWNER_ALIAS_PROJECTION",
            raw=raw,
            semantic=semantic,
            semantic_current_fingerprint_digest=semantic_current_fp.digest,
            previous_view=previous_view,
            current_view=current_view,
            alias_required=True,
            alias=None,
            prior_no_progress_count=prior_no_progress_count,
        )
    if alias_required:
        assert alias_projection is not None
        _alias_matches(alias_projection, previous_view, current_view)
    elif alias_projection is not None:
        raise ValueError("ALIAS_PROJECTION_NOT_REQUIRED_FOR_THIS_ROUTE_TRANSITION")

    if not same_sid and semantic.decision in {
        RetrievalDecision.CHANGE_AXIS_REQUIRED,
        RetrievalDecision.COLLAPSE_CONE,
    }:
        return _receipt(
            decision=AliasAwareDecision.HOLD_SOURCE_IDENTITY_TRANSITION_REQUIRED,
            reason="CALLER_SID_CHANGE_HAS_NO_INDEPENDENT_PROGRESS_WITNESS",
            raw=raw,
            semantic=semantic,
            semantic_current_fingerprint_digest=semantic_current_fp.digest,
            previous_view=previous_view,
            current_view=current_view,
            alias_required=False,
            alias=None,
            prior_no_progress_count=prior_no_progress_count,
        )

    return _receipt(
        decision=_decision(semantic.decision),
        reason=(
            "ROUTE_ALIAS_QUOTIENTED_TO_STABLE_SOURCE_SID"
            if alias_required
            else "SEMANTIC_SOURCE_IDENTITY_APPLIED"
            if same_sid
            else "SID_CHANGE_IGNORED;INDEPENDENT_PROGRESS_AXIS_USED"
        ),
        raw=raw,
        semantic=semantic,
        semantic_current_fingerprint_digest=semantic_current_fp.digest,
        previous_view=previous_view,
        current_view=current_view,
        alias_required=alias_required,
        alias=alias_projection,
        prior_no_progress_count=prior_no_progress_count,
    )


LAWS = (
    "RouteProjectionChanged!=SemanticRetrievalAxisChanged",
    "SameSID+DifferentScheme=>AliasableRoutingProjectionsNotNewSource",
    "SameSID+SamePurpose+SameProviderState+SameEvidence=>NoProgressDebtContinuesAcrossSchemes",
    "SchemeRotationCannotResetNoProgressDebt",
    "CallerSIDRotationCannotMintProgress",
    "DifferentSIDWithoutIndependentProgress=>HoldForSourceIdentityOwner",
    "SameXYZ+DifferentFullDigest=>CoordinateCollisionNeverSourceMerge",
    "AliasProjectionMissing=>HoldNotProgress",
    "AliasProjectionCanOnlyRestrictRetry;CannotGrantProgressOrAuthority",
    "ProviderOrEvidenceGenerationChangeMayStillCountAsStateTransition",
    "CoordinateView!=SourceIdentity!=SemanticTruth!=Authority",
    "NormalizationVersionChange=>RouteRecomputeNotSemanticRegeneration",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
