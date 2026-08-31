#!/usr/bin/env python3
"""Aura Navigator: K27 locality × semantic-collision routing membrane.

D0 / HS1 / NONPROMOTING.

Objective H converges two independently owned and hosted-proven surfaces:
- NAV03A recursive K27 adaptive zoom (locality/retrieval geometry only), and
- collision-safe rebase assessment (semantic overlap/owner-currentness only).

The two axes are deliberately evaluated independently.  A different K27 path
cannot prove a different semantic owner, and a shared K27 path cannot prove
semantic duplication.  This module returns only a bounded Navigator route and
hydration plan; it grants no semantic, evidence, currentness, write, tool, or
effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping, Tuple

from tools.aura_fractal_k27 import (
    AdaptiveZoomReceipt,
    K27Candidate,
    K27Path,
    ZoomDisposition,
    prove_different_j,
)
from tools.aura_collision_safe_rebase import (
    CandidateContribution,
    CollisionAssessment,
    CollisionDisposition,
    OwnerState,
    assess_collision,
)


SCHEMA = "AURA-NAVIGATOR-K27-COLLISION-ROUTER-v1"
NAV03A_HEAD = "d97012ce7d3dd221adac0f750db4b77ddf6a7ab9"
NAV03A_PROOF_HEAD = "91028c63155bbff891d780f123e4477f037f8096"
NAV03A_PROOF_RUN = 33423871812
NAV03A_PROOF_JOB = 99592589458
COLLISION_HEAD = "88042284f44cce3bcad40097b069ca31348d133d"
COLLISION_PROOF_HEAD = "ba5301429ae4ee00b44424397033568a00a956b6"
COLLISION_PROOF_RUN = 33424128729
COLLISION_PROOF_JOB = 99593429609
TRUE_DIAMOND = "620bd0c02190d4efcb41978cf95a3268dfbe02a5"


class NavigatorRouteDisposition(str, Enum):
    HOLD_OWNER_CURRENTNESS_REQUIRED = "HOLD_OWNER_CURRENTNESS_REQUIRED"
    RETAIN_DUPLICATE_LINEAGE = "RETAIN_DUPLICATE_LINEAGE"
    ROUTE_ADDENDUM_REBASE = "ROUTE_ADDENDUM_REBASE"
    ROUTE_ORTHOGONAL_CANDIDATE = "ROUTE_ORTHOGONAL_CANDIDATE"


@dataclass(frozen=True)
class NavigatorK27CollisionReceiptV1:
    schema: str
    owner_ref: str
    candidate_ref: str
    owner_k27_path: str
    candidate_k27_path: str
    locality_disposition: ZoomDisposition
    distinguishing_micro_depth: int | None
    common_prefix: Tuple[Tuple[int, int, int], ...]
    semantic_collision_disposition: CollisionDisposition
    route_disposition: NavigatorRouteDisposition
    hydration_plan: Tuple[str, ...]
    overlapping_claims: Tuple[str, ...]
    unique_residual_claims: Tuple[str, ...]
    preserve_as_reusable_cognition: bool
    requires_rebase: bool
    requires_owner_revalidation: bool
    requires_semantic_revalidation: bool
    duplicate_semantic_mass: bool
    sibling_credit_earned: bool
    nav03a_head: str = NAV03A_HEAD
    nav03a_proof_head: str = NAV03A_PROOF_HEAD
    nav03a_proof_run: int = NAV03A_PROOF_RUN
    nav03a_proof_job: int = NAV03A_PROOF_JOB
    collision_head: str = COLLISION_HEAD
    collision_proof_head: str = COLLISION_PROOF_HEAD
    collision_proof_run: int = COLLISION_PROOF_RUN
    collision_proof_job: int = COLLISION_PROOF_JOB
    true_diamond: str = TRUE_DIAMOND
    k27_semantic_identity: bool = False
    k27_evidence_rank: bool = False
    k27_currentness_witness: bool = False
    semantic_authority_granted: bool = False
    read_authority_granted: bool = False
    write_authority_granted: bool = False
    tool_execution_authority_granted: bool = False
    effect_authority_granted: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def receipt_digest(self) -> str:
        body = asdict(self)
        body["locality_disposition"] = self.locality_disposition.value
        body["semantic_collision_disposition"] = self.semantic_collision_disposition.value
        body["route_disposition"] = self.route_disposition.value
        raw = json.dumps(
            {"domain": SCHEMA, "receipt": body},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> Mapping[str, Any]:
        body = asdict(self)
        body["locality_disposition"] = self.locality_disposition.value
        body["semantic_collision_disposition"] = self.semantic_collision_disposition.value
        body["route_disposition"] = self.route_disposition.value
        body["receipt_digest"] = self.receipt_digest
        return body


def _path_text(path: K27Path) -> str:
    return path.to_string()


def _hydration_plan(
    locality: AdaptiveZoomReceipt,
    semantic: CollisionAssessment,
) -> Tuple[str, ...]:
    plan: list[str] = []

    if locality.disposition is ZoomDisposition.DISTINGUISHED:
        plan.append("KEEP_K27_NEIGHBORHOODS_DISTINCT")
        plan.append("HYDRATE_ONLY_MINIMUM_DISTINGUISHING_LOCALITY")
    elif locality.disposition is ZoomDisposition.LOCALITY_COLLISION:
        plan.append("K27_LOCALITY_COLLISION_DOES_NOT_DECIDE_SEMANTICS")
        plan.append("DESCEND_K27_OR_EXPAND_ATLAS_ONLY_IF_ROUTING_PRECISION_REQUIRES")
    else:
        plan.append("K27_ANCESTOR_DESCENDANT_DOES_NOT_DECIDE_SEMANTICS")
        plan.append("HYDRATE_CHILD_PATH_ONLY_IF_ROUTE_REQUIRES")

    if semantic.disposition is CollisionDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED:
        plan.append("REVALIDATE_CURRENT_OWNER_GENERATION_BEFORE_REBASE_OR_ADMISSION")
    elif semantic.disposition is CollisionDisposition.DUPLICATE_RETAINED_AS_LINEAGE:
        plan.append("PRESERVE_CANDIDATE_AS_LINEAGE_WITH_ZERO_SIBLING_CREDIT")
        plan.append("DO_NOT_DUPLICATE_CANONICAL_OWNER")
    elif semantic.disposition is CollisionDisposition.ADDENDUM_CANDIDATE:
        plan.append("HYDRATE_ONLY_UNIQUE_RESIDUAL_AND_OWNER_INVALIDATORS")
        plan.append("ROUTE_TO_TYPED_ADDENDUM_REBASE")
    else:
        plan.append("HYDRATE_ONLY_ORTHOGONAL_RESIDUAL_AND_INVALIDATORS")
        plan.append("ROUTE_TO_NEW_OBJECTIVE_CANDIDATE_WITHOUT_AUTHORITY")

    return tuple(plan)


def route_k27_collision(
    *,
    owner: OwnerState,
    candidate: CandidateContribution,
    owner_path: K27Path,
    candidate_path: K27Path,
    overlapping_claims: Iterable[str],
    unique_residual_claims: Iterable[str],
) -> NavigatorK27CollisionReceiptV1:
    """Join independent locality and semantic-collision evidence.

    K27 is used strictly to shape hydration/locality.  Semantic collision is
    assessed strictly by the collision-safe rebase owner.  Neither surface can
    borrow authority from the other.
    """
    if not isinstance(owner_path, K27Path) or not isinstance(candidate_path, K27Path):
        raise ValueError("NAVIGATOR_K27_PATHS_REQUIRED")
    if owner.owner_ref.strip() == candidate.contribution_ref.strip():
        raise ValueError("OWNER_AND_CANDIDATE_REFS_MUST_BE_DISTINCT")

    locality = prove_different_j(
        (
            K27Candidate(owner_ref=owner.owner_ref, path=owner_path),
            K27Candidate(owner_ref=candidate.contribution_ref, path=candidate_path),
        )
    )
    semantic = assess_collision(
        owner,
        candidate,
        overlapping_claims=overlapping_claims,
        unique_residual_claims=unique_residual_claims,
    )

    if any(
        (
            locality.semantic_identity,
            locality.evidence_rank,
            locality.currentness_witness,
            locality.authority,
            locality.effect_authority,
        )
    ):
        raise ValueError("K27_LOCALITY_RECEIPT_EXCEEDED_AUTHORITY_CEILING")
    if semantic.sibling_credit_earned or semantic.semantic_authority_granted or semantic.effect_authority_granted:
        raise ValueError("COLLISION_ASSESSMENT_EXCEEDED_AUTHORITY_CEILING")

    if semantic.disposition is CollisionDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED:
        route = NavigatorRouteDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED
    elif semantic.disposition is CollisionDisposition.DUPLICATE_RETAINED_AS_LINEAGE:
        route = NavigatorRouteDisposition.RETAIN_DUPLICATE_LINEAGE
    elif semantic.disposition is CollisionDisposition.ADDENDUM_CANDIDATE:
        route = NavigatorRouteDisposition.ROUTE_ADDENDUM_REBASE
    else:
        route = NavigatorRouteDisposition.ROUTE_ORTHOGONAL_CANDIDATE

    return NavigatorK27CollisionReceiptV1(
        schema=SCHEMA,
        owner_ref=owner.owner_ref,
        candidate_ref=candidate.contribution_ref,
        owner_k27_path=_path_text(owner_path),
        candidate_k27_path=_path_text(candidate_path),
        locality_disposition=locality.disposition,
        distinguishing_micro_depth=locality.distinguishing_micro_depth,
        common_prefix=locality.common_prefix,
        semantic_collision_disposition=semantic.disposition,
        route_disposition=route,
        hydration_plan=_hydration_plan(locality, semantic),
        overlapping_claims=semantic.overlapping_claims,
        unique_residual_claims=semantic.unique_residual_claims,
        preserve_as_reusable_cognition=semantic.preserve_as_reusable_cognition,
        requires_rebase=semantic.requires_rebase,
        requires_owner_revalidation=(
            semantic.disposition is CollisionDisposition.HOLD_OWNER_CURRENTNESS_REQUIRED
        ),
        requires_semantic_revalidation=semantic.requires_revalidation,
        duplicate_semantic_mass=semantic.duplicate_semantic_mass,
        sibling_credit_earned=False,
    )


__all__ = [
    "SCHEMA",
    "NAV03A_HEAD",
    "NAV03A_PROOF_HEAD",
    "NAV03A_PROOF_RUN",
    "NAV03A_PROOF_JOB",
    "COLLISION_HEAD",
    "COLLISION_PROOF_HEAD",
    "COLLISION_PROOF_RUN",
    "COLLISION_PROOF_JOB",
    "TRUE_DIAMOND",
    "NavigatorRouteDisposition",
    "NavigatorK27CollisionReceiptV1",
    "route_k27_collision",
]
