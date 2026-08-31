#!/usr/bin/env python3
"""NAV-13A/B/C: recursive K27 LawField inheritance and boundary membrane.

D0 / HS1 / NONPROMOTING.

This module owns only navigation-law projection:
Recursive K27 path + inherited/local policy projections -> EffectiveLawField,
plus a deterministic detector for state changes that require recomputation.

It does not own storage, AST/source materialization, semantic identity,
evidence truth, currentness truth, authorization issuance, tool execution,
or effects. Supersession inputs are upstream authority projections whose
identity is bound here but whose trust is not minted here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable, Mapping, Sequence

from tools.aura_fractal_k27 import K27Path

SCHEMA = "AURA-NAV13-LAWFIELD-v1"
BOUNDARY_SCHEMA = "AURA-NAV13-LAWFIELD-BOUNDARY-v1"
SUPERSESSION_STATE = "VERIFIED_BOUNDED"


def _sha256_json(domain: str, payload: Mapping[str, object]) -> str:
    raw = json.dumps(
        {"domain": domain, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _require_digest(value: str, code: str) -> str:
    value = _require_text(value, code)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(code)
    return value


def _normalize_unique(values: Iterable[str], code: str) -> tuple[str, ...]:
    items = tuple(_require_text(v, code) for v in values)
    if len(set(items)) != len(items):
        raise ValueError(code)
    return tuple(sorted(items))


def _normalize_optional_unique(
    values: Sequence[str] | None, code: str
) -> tuple[str, ...] | None:
    if values is None:
        return None
    return _normalize_unique(values, code)


@dataclass(frozen=True)
class LawFieldOverlay:
    path: K27Path
    owner_ref: str
    rule_generation: str
    hard_constraints_add: tuple[str, ...] = ()
    allowed_actions_limit: tuple[str, ...] | None = None
    denied_actions_add: tuple[str, ...] = ()
    required_evidence_add: tuple[str, ...] = ()
    authority_scopes_limit: tuple[str, ...] | None = None
    effect_scopes_limit: tuple[str, ...] | None = None
    domain_roles: tuple[str, ...] = ()
    evidence_state_digest: str = "0" * 64
    authority_state_digest: str = "0" * 64
    temporal_state_digest: str = "0" * 64
    provider_policy_digest: str = "0" * 64

    def normalized(self) -> "LawFieldOverlay":
        if not isinstance(self.path, K27Path):
            raise ValueError("K27_PATH_REQUIRED")
        return LawFieldOverlay(
            path=self.path,
            owner_ref=_require_text(self.owner_ref, "OWNER_REF_REQUIRED"),
            rule_generation=_require_text(
                self.rule_generation, "RULE_GENERATION_REQUIRED"
            ),
            hard_constraints_add=_normalize_unique(
                self.hard_constraints_add, "DUPLICATE_HARD_CONSTRAINT"
            ),
            allowed_actions_limit=_normalize_optional_unique(
                self.allowed_actions_limit, "DUPLICATE_ALLOWED_ACTION"
            ),
            denied_actions_add=_normalize_unique(
                self.denied_actions_add, "DUPLICATE_DENIED_ACTION"
            ),
            required_evidence_add=_normalize_unique(
                self.required_evidence_add, "DUPLICATE_REQUIRED_EVIDENCE"
            ),
            authority_scopes_limit=_normalize_optional_unique(
                self.authority_scopes_limit, "DUPLICATE_AUTHORITY_SCOPE"
            ),
            effect_scopes_limit=_normalize_optional_unique(
                self.effect_scopes_limit, "DUPLICATE_EFFECT_SCOPE"
            ),
            domain_roles=_normalize_unique(self.domain_roles, "DUPLICATE_DOMAIN_ROLE"),
            evidence_state_digest=_require_digest(
                self.evidence_state_digest, "EVIDENCE_STATE_DIGEST_REQUIRED"
            ),
            authority_state_digest=_require_digest(
                self.authority_state_digest, "AUTHORITY_STATE_DIGEST_REQUIRED"
            ),
            temporal_state_digest=_require_digest(
                self.temporal_state_digest, "TEMPORAL_STATE_DIGEST_REQUIRED"
            ),
            provider_policy_digest=_require_digest(
                self.provider_policy_digest, "PROVIDER_POLICY_DIGEST_REQUIRED"
            ),
        )


@dataclass(frozen=True)
class SupersessionProjection:
    target_constraint: str
    parent_law_digest: str
    child_path: str
    authority_owner_ref: str
    authority_generation: str
    authority_receipt_digest: str
    authority_state: str = SUPERSESSION_STATE

    def validate(self) -> None:
        _require_text(self.target_constraint, "SUPERSESSION_TARGET_REQUIRED")
        _require_digest(self.parent_law_digest, "SUPERSESSION_PARENT_DIGEST_REQUIRED")
        _require_text(self.child_path, "SUPERSESSION_CHILD_PATH_REQUIRED")
        _require_text(self.authority_owner_ref, "SUPERSESSION_OWNER_REQUIRED")
        _require_text(self.authority_generation, "SUPERSESSION_GENERATION_REQUIRED")
        _require_digest(
            self.authority_receipt_digest, "SUPERSESSION_RECEIPT_DIGEST_REQUIRED"
        )
        if self.authority_state != SUPERSESSION_STATE:
            raise ValueError("SUPERSESSION_AUTHORITY_NOT_VERIFIED_BOUNDED")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return _sha256_json(
            "AURA-NAV13-SUPERSESSION-PROJECTION-v1",
            asdict(self),
        )


@dataclass(frozen=True)
class EffectiveLawField:
    schema: str
    path: str
    parent_law_digest: str
    owner_ref: str
    rule_generation: str
    hard_constraints: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    denied_actions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    authority_scopes: tuple[str, ...]
    effect_scopes: tuple[str, ...]
    domain_roles: tuple[str, ...]
    evidence_state_digest: str
    authority_state_digest: str
    temporal_state_digest: str
    provider_policy_digest: str
    supersession_fingerprints: tuple[str, ...]
    semantic_truth_proven: bool = False
    evidence_admitted: bool = False
    authorization_issued: bool = False
    transition_authorized: bool = False
    effect_authorized: bool = False
    effect_executed: bool = False
    k27_semantic_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def digest(self) -> str:
        body = asdict(self)
        return _sha256_json(SCHEMA, body)

    def validate_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("LAW_FIELD_SCHEMA_MISMATCH")
        if any(
            (
                self.semantic_truth_proven,
                self.evidence_admitted,
                self.authorization_issued,
                self.transition_authorized,
                self.effect_authorized,
                self.effect_executed,
                self.k27_semantic_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("LAW_FIELD_EXCEEDED_NONPROMOTION_CEILING")


def _root_tuple(values: tuple[str, ...] | None, code: str) -> tuple[str, ...]:
    if values is None:
        raise ValueError(code)
    return values


def root_law_field(overlay: LawFieldOverlay) -> EffectiveLawField:
    o = overlay.normalized()
    allowed = _root_tuple(o.allowed_actions_limit, "ROOT_ALLOWED_ACTIONS_REQUIRED")
    authority = _root_tuple(
        o.authority_scopes_limit, "ROOT_AUTHORITY_SCOPES_REQUIRED"
    )
    effects = _root_tuple(o.effect_scopes_limit, "ROOT_EFFECT_SCOPES_REQUIRED")
    denied = o.denied_actions_add
    if set(denied) - set(allowed):
        raise ValueError("ROOT_DENIED_ACTION_OUTSIDE_ALLOWED_UNIVERSE")
    field = EffectiveLawField(
        schema=SCHEMA,
        path=str(o.path),
        parent_law_digest="ROOT",
        owner_ref=o.owner_ref,
        rule_generation=o.rule_generation,
        hard_constraints=o.hard_constraints_add,
        allowed_actions=tuple(sorted(set(allowed) - set(denied))),
        denied_actions=denied,
        required_evidence=o.required_evidence_add,
        authority_scopes=authority,
        effect_scopes=effects,
        domain_roles=o.domain_roles,
        evidence_state_digest=o.evidence_state_digest,
        authority_state_digest=o.authority_state_digest,
        temporal_state_digest=o.temporal_state_digest,
        provider_policy_digest=o.provider_policy_digest,
        supersession_fingerprints=(),
    )
    field.validate_ceiling()
    return field


def inherit_law_field(
    parent: EffectiveLawField,
    child_overlay: LawFieldOverlay,
    *,
    supersessions: Iterable[SupersessionProjection] = (),
) -> EffectiveLawField:
    parent.validate_ceiling()
    child = child_overlay.normalized()
    parent_path = K27Path.parse(parent.path)
    if child.path.parent != parent_path:
        raise ValueError("CHILD_LAWFIELD_MUST_BE_DIRECT_K27_CHILD")

    child_allowed = child.allowed_actions_limit
    if child_allowed is not None and not set(child_allowed).issubset(parent.allowed_actions):
        raise ValueError("CHILD_PERMISSION_WIDENING_REJECTED")
    child_authority = child.authority_scopes_limit
    if child_authority is not None and not set(child_authority).issubset(
        parent.authority_scopes
    ):
        raise ValueError("CHILD_AUTHORITY_WIDENING_REJECTED")
    child_effects = child.effect_scopes_limit
    if child_effects is not None and not set(child_effects).issubset(parent.effect_scopes):
        raise ValueError("CHILD_EFFECT_WIDENING_REJECTED")

    supersession_items = tuple(supersessions)
    targets: set[str] = set()
    fingerprints: list[str] = []
    for projection in supersession_items:
        projection.validate()
        if projection.target_constraint in targets:
            raise ValueError("DUPLICATE_SUPERSESSION_TARGET")
        if projection.target_constraint not in parent.hard_constraints:
            raise ValueError("SUPERSESSION_TARGET_NOT_IN_PARENT")
        if projection.parent_law_digest != parent.digest:
            raise ValueError("SUPERSESSION_PARENT_DIGEST_MISMATCH")
        if projection.child_path != str(child.path):
            raise ValueError("SUPERSESSION_CHILD_PATH_MISMATCH")
        targets.add(projection.target_constraint)
        fingerprints.append(projection.fingerprint)

    hard = tuple(
        sorted((set(parent.hard_constraints) - targets) | set(child.hard_constraints_add))
    )
    allowed_base = (
        set(parent.allowed_actions) if child_allowed is None else set(child_allowed)
    )
    denied = tuple(sorted(set(parent.denied_actions) | set(child.denied_actions_add)))
    allowed = tuple(sorted(allowed_base - set(denied)))
    authority = tuple(
        sorted(
            set(parent.authority_scopes)
            if child_authority is None
            else set(child_authority)
        )
    )
    effects = tuple(
        sorted(set(parent.effect_scopes) if child_effects is None else set(child_effects))
    )

    field = EffectiveLawField(
        schema=SCHEMA,
        path=str(child.path),
        parent_law_digest=parent.digest,
        owner_ref=child.owner_ref,
        rule_generation=child.rule_generation,
        hard_constraints=hard,
        allowed_actions=allowed,
        denied_actions=denied,
        required_evidence=tuple(
            sorted(set(parent.required_evidence) | set(child.required_evidence_add))
        ),
        authority_scopes=authority,
        effect_scopes=effects,
        domain_roles=tuple(sorted(set(parent.domain_roles) | set(child.domain_roles))),
        evidence_state_digest=child.evidence_state_digest,
        authority_state_digest=child.authority_state_digest,
        temporal_state_digest=child.temporal_state_digest,
        provider_policy_digest=child.provider_policy_digest,
        supersession_fingerprints=tuple(sorted(fingerprints)),
    )
    field.validate_ceiling()
    return field


class BoundaryReason(str, Enum):
    K27_PATH_CHANGED = "K27_PATH_CHANGED"
    EFFECTIVE_LAW_CHANGED = "EFFECTIVE_LAW_CHANGED"
    SEMANTIC_OWNER_CHANGED = "SEMANTIC_OWNER_CHANGED"
    DOMAIN_ROLE_CHANGED = "DOMAIN_ROLE_CHANGED"
    EVIDENCE_STATE_CHANGED = "EVIDENCE_STATE_CHANGED"
    AUTHORITY_STATE_CHANGED = "AUTHORITY_STATE_CHANGED"
    TEMPORAL_STATE_CHANGED = "TEMPORAL_STATE_CHANGED"
    EXECUTION_ENVIRONMENT_CHANGED = "EXECUTION_ENVIRONMENT_CHANGED"
    PROVIDER_POLICY_CHANGED = "PROVIDER_POLICY_CHANGED"
    WORK_ORDER_STATE_CHANGED = "WORK_ORDER_STATE_CHANGED"


@dataclass(frozen=True)
class BoundarySnapshot:
    path: str
    effective_law_digest: str
    semantic_owner_ref: str
    domain_role_digest: str
    evidence_state_digest: str
    authority_state_digest: str
    temporal_state_digest: str
    execution_environment_digest: str
    provider_policy_digest: str
    work_order_state_digest: str

    def validate(self) -> None:
        K27Path.parse(self.path)
        _require_digest(self.effective_law_digest, "EFFECTIVE_LAW_DIGEST_REQUIRED")
        _require_text(self.semantic_owner_ref, "SEMANTIC_OWNER_REF_REQUIRED")
        for value, code in (
            (self.domain_role_digest, "DOMAIN_ROLE_DIGEST_REQUIRED"),
            (self.evidence_state_digest, "EVIDENCE_STATE_DIGEST_REQUIRED"),
            (self.authority_state_digest, "AUTHORITY_STATE_DIGEST_REQUIRED"),
            (self.temporal_state_digest, "TEMPORAL_STATE_DIGEST_REQUIRED"),
            (self.execution_environment_digest, "EXECUTION_ENVIRONMENT_DIGEST_REQUIRED"),
            (self.provider_policy_digest, "PROVIDER_POLICY_DIGEST_REQUIRED"),
            (self.work_order_state_digest, "WORK_ORDER_STATE_DIGEST_REQUIRED"),
        ):
            _require_digest(value, code)


@dataclass(frozen=True)
class BoundaryDecision:
    schema: str
    requires_recomputation: bool
    reasons: tuple[BoundaryReason, ...]
    before_digest: str
    after_digest: str
    transition_authorized: bool = False
    effect_authorized: bool = False
    effect_executed: bool = False

    def validate(self) -> None:
        if self.schema != BOUNDARY_SCHEMA:
            raise ValueError("BOUNDARY_SCHEMA_MISMATCH")
        if self.requires_recomputation != bool(self.reasons):
            raise ValueError("BOUNDARY_DECISION_INCONSISTENT")
        if any((self.transition_authorized, self.effect_authorized, self.effect_executed)):
            raise ValueError("BOUNDARY_DECISION_EXCEEDED_NONPROMOTION_CEILING")


def _snapshot_digest(snapshot: BoundarySnapshot) -> str:
    snapshot.validate()
    return _sha256_json("AURA-NAV13-BOUNDARY-SNAPSHOT-v1", asdict(snapshot))


_BOUNDARY_TABLE = (
    ("path", BoundaryReason.K27_PATH_CHANGED),
    ("effective_law_digest", BoundaryReason.EFFECTIVE_LAW_CHANGED),
    ("semantic_owner_ref", BoundaryReason.SEMANTIC_OWNER_CHANGED),
    ("domain_role_digest", BoundaryReason.DOMAIN_ROLE_CHANGED),
    ("evidence_state_digest", BoundaryReason.EVIDENCE_STATE_CHANGED),
    ("authority_state_digest", BoundaryReason.AUTHORITY_STATE_CHANGED),
    ("temporal_state_digest", BoundaryReason.TEMPORAL_STATE_CHANGED),
    ("execution_environment_digest", BoundaryReason.EXECUTION_ENVIRONMENT_CHANGED),
    ("provider_policy_digest", BoundaryReason.PROVIDER_POLICY_CHANGED),
    ("work_order_state_digest", BoundaryReason.WORK_ORDER_STATE_CHANGED),
)


def boundary_reasons_table(
    before: BoundarySnapshot, after: BoundarySnapshot
) -> tuple[BoundaryReason, ...]:
    before.validate()
    after.validate()
    return tuple(
        reason
        for field_name, reason in _BOUNDARY_TABLE
        if getattr(before, field_name) != getattr(after, field_name)
    )


def boundary_reasons_explicit(
    before: BoundarySnapshot, after: BoundarySnapshot
) -> tuple[BoundaryReason, ...]:
    before.validate()
    after.validate()
    reasons: list[BoundaryReason] = []
    if before.path != after.path:
        reasons.append(BoundaryReason.K27_PATH_CHANGED)
    if before.effective_law_digest != after.effective_law_digest:
        reasons.append(BoundaryReason.EFFECTIVE_LAW_CHANGED)
    if before.semantic_owner_ref != after.semantic_owner_ref:
        reasons.append(BoundaryReason.SEMANTIC_OWNER_CHANGED)
    if before.domain_role_digest != after.domain_role_digest:
        reasons.append(BoundaryReason.DOMAIN_ROLE_CHANGED)
    if before.evidence_state_digest != after.evidence_state_digest:
        reasons.append(BoundaryReason.EVIDENCE_STATE_CHANGED)
    if before.authority_state_digest != after.authority_state_digest:
        reasons.append(BoundaryReason.AUTHORITY_STATE_CHANGED)
    if before.temporal_state_digest != after.temporal_state_digest:
        reasons.append(BoundaryReason.TEMPORAL_STATE_CHANGED)
    if before.execution_environment_digest != after.execution_environment_digest:
        reasons.append(BoundaryReason.EXECUTION_ENVIRONMENT_CHANGED)
    if before.provider_policy_digest != after.provider_policy_digest:
        reasons.append(BoundaryReason.PROVIDER_POLICY_CHANGED)
    if before.work_order_state_digest != after.work_order_state_digest:
        reasons.append(BoundaryReason.WORK_ORDER_STATE_CHANGED)
    return tuple(reasons)


def detect_lawfield_boundary(
    before: BoundarySnapshot, after: BoundarySnapshot
) -> BoundaryDecision:
    left = boundary_reasons_explicit(before, after)
    right = boundary_reasons_table(before, after)
    if left != right:
        raise AssertionError("DIFFERENT_J_BOUNDARY_DETECTORS_DISAGREE")
    decision = BoundaryDecision(
        schema=BOUNDARY_SCHEMA,
        requires_recomputation=bool(left),
        reasons=left,
        before_digest=_snapshot_digest(before),
        after_digest=_snapshot_digest(after),
    )
    decision.validate()
    return decision


def snapshot_from_field(
    field: EffectiveLawField,
    *,
    semantic_owner_ref: str,
    execution_environment_digest: str,
    work_order_state_digest: str,
) -> BoundarySnapshot:
    field.validate_ceiling()
    domain_role_digest = _sha256_json(
        "AURA-NAV13-DOMAIN-ROLES-v1", {"roles": list(field.domain_roles)}
    )
    return BoundarySnapshot(
        path=field.path,
        effective_law_digest=field.digest,
        semantic_owner_ref=_require_text(
            semantic_owner_ref, "SEMANTIC_OWNER_REF_REQUIRED"
        ),
        domain_role_digest=domain_role_digest,
        evidence_state_digest=field.evidence_state_digest,
        authority_state_digest=field.authority_state_digest,
        temporal_state_digest=field.temporal_state_digest,
        execution_environment_digest=_require_digest(
            execution_environment_digest, "EXECUTION_ENVIRONMENT_DIGEST_REQUIRED"
        ),
        provider_policy_digest=field.provider_policy_digest,
        work_order_state_digest=_require_digest(
            work_order_state_digest, "WORK_ORDER_STATE_DIGEST_REQUIRED"
        ),
    )


__all__ = [
    "SCHEMA",
    "BOUNDARY_SCHEMA",
    "SUPERSESSION_STATE",
    "LawFieldOverlay",
    "SupersessionProjection",
    "EffectiveLawField",
    "root_law_field",
    "inherit_law_field",
    "BoundaryReason",
    "BoundarySnapshot",
    "BoundaryDecision",
    "boundary_reasons_table",
    "boundary_reasons_explicit",
    "detect_lawfield_boundary",
    "snapshot_from_field",
]
