#!/usr/bin/env python3
"""AuraOS collision-safe rebase/addendum contract.

This module preserves useful cognition when a live owner already occupies a
consequence seam.  It deliberately separates provenance retention from semantic
credit and authority.  A collision may require rebasing or an addendum; it must
never silently erase a valid contribution or double-count duplicate semantics.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable, Tuple

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CollisionDisposition(str, Enum):
    HOLD_OWNER_CURRENTNESS_REQUIRED = "HOLD_OWNER_CURRENTNESS_REQUIRED"
    DUPLICATE_RETAINED_AS_LINEAGE = "DUPLICATE_RETAINED_AS_LINEAGE"
    ADDENDUM_CANDIDATE = "ADDENDUM_CANDIDATE"
    ORTHOGONAL_OWNER_CANDIDATE = "ORTHOGONAL_OWNER_CANDIDATE"


@dataclass(frozen=True)
class OwnerState:
    owner_ref: str
    semantic_generation: str
    semantic_digest: str
    current: bool


@dataclass(frozen=True)
class CandidateContribution:
    contribution_ref: str
    semantic_digest: str
    claims: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    invalidators: Tuple[str, ...]


@dataclass(frozen=True)
class CollisionAssessment:
    owner: OwnerState
    candidate: CandidateContribution
    overlapping_claims: Tuple[str, ...]
    unique_residual_claims: Tuple[str, ...]
    disposition: CollisionDisposition
    preserve_as_reusable_cognition: bool
    requires_rebase: bool
    requires_revalidation: bool
    duplicate_semantic_mass: bool
    sibling_credit_earned: bool
    effect_authority_granted: bool
    semantic_authority_granted: bool
    assessment_digest: str


def _canonical_tuple(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted({value.strip() for value in values if value and value.strip()}))


def _require_digest(value: str, field_name: str) -> None:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase 64-hex SHA-256 digest")


def _digest(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def assess_collision(
    owner: OwnerState,
    candidate: CandidateContribution,
    *,
    overlapping_claims: Iterable[str],
    unique_residual_claims: Iterable[str],
) -> CollisionAssessment:
    """Classify a contribution against a current semantic owner.

    Laws enforced by construction:
      Collision != ContributionLoss
      OwnerSupersession != CognitionInvalidation
      DuplicateSemanticMass => ZeroSiblingCredit
      RebaseAddendum != Authority
      CurrentOwnerGenerationMustBeBoundBeforeRebase

    This function never grants semantic/effect authority and never grants
    successor sibling credit.  An ADDENDUM_CANDIDATE still requires the owner's
    current generation to be revalidated and the residual to be independently
    proven before any downstream system may treat it as an earned consequence.
    """

    _require_digest(owner.semantic_digest, "owner.semantic_digest")
    _require_digest(candidate.semantic_digest, "candidate.semantic_digest")
    if not owner.owner_ref.strip() or not owner.semantic_generation.strip():
        raise ValueError("owner_ref and semantic_generation are required")
    if not candidate.contribution_ref.strip():
        raise ValueError("contribution_ref is required")

    claims = _canonical_tuple(candidate.claims)
    evidence_refs = _canonical_tuple(candidate.evidence_refs)
    invalidators = _canonical_tuple(candidate.invalidators)
    overlap = _canonical_tuple(overlapping_claims)
    residual = _canonical_tuple(unique_residual_claims)

    if not set(overlap).issubset(set(claims)):
        raise ValueError("overlapping_claims must be a subset of candidate.claims")
    if not set(residual).issubset(set(claims)):
        raise ValueError("unique_residual_claims must be a subset of candidate.claims")
    if set(overlap) & set(residual):
        raise ValueError("overlapping and unique residual claims must be disjoint")

    if not owner.current:
        disposition = CollisionDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED
        preserve = True
        requires_rebase = False
        requires_revalidation = True
        duplicate_mass = False
    elif owner.semantic_digest == candidate.semantic_digest or (
        claims and set(claims).issubset(set(overlap)) and not residual
    ):
        disposition = CollisionDisposition.DUPLICATE_RETAINED_AS_LINEAGE
        preserve = True
        requires_rebase = False
        requires_revalidation = False
        duplicate_mass = True
    elif overlap:
        disposition = CollisionDisposition.ADDENDUM_CANDIDATE
        preserve = True
        requires_rebase = True
        requires_revalidation = True
        duplicate_mass = False
    else:
        disposition = CollisionDisposition.ORTHOGONAL_OWNER_CANDIDATE
        preserve = True
        requires_rebase = False
        requires_revalidation = True
        duplicate_mass = False

    core = {
        "schema": "AuraCollisionSafeRebaseAssessmentV1",
        "owner": asdict(owner),
        "candidate": {
            "contribution_ref": candidate.contribution_ref,
            "semantic_digest": candidate.semantic_digest,
            "claims": claims,
            "evidence_refs": evidence_refs,
            "invalidators": invalidators,
        },
        "overlapping_claims": overlap,
        "unique_residual_claims": residual,
        "disposition": disposition.value,
        "preserve_as_reusable_cognition": preserve,
        "requires_rebase": requires_rebase,
        "requires_revalidation": requires_revalidation,
        "duplicate_semantic_mass": duplicate_mass,
        "sibling_credit_earned": False,
        "effect_authority_granted": False,
        "semantic_authority_granted": False,
    }

    return CollisionAssessment(
        owner=owner,
        candidate=CandidateContribution(
            contribution_ref=candidate.contribution_ref,
            semantic_digest=candidate.semantic_digest,
            claims=claims,
            evidence_refs=evidence_refs,
            invalidators=invalidators,
        ),
        overlapping_claims=overlap,
        unique_residual_claims=residual,
        disposition=disposition,
        preserve_as_reusable_cognition=preserve,
        requires_rebase=requires_rebase,
        requires_revalidation=requires_revalidation,
        duplicate_semantic_mass=duplicate_mass,
        sibling_credit_earned=False,
        effect_authority_granted=False,
        semantic_authority_granted=False,
        assessment_digest=_digest(core),
    )
