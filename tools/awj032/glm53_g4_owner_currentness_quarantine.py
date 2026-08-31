"""G4 W3: quarantine caller-shaped currentness in GLM-5.3 plan revalidation.

D0 / HS1 / NONPROMOTING / STACKED ADDENDUM TO PR #757.

PR #757 correctly detects drift among eight identity-bearing plan-use axes, but its
CurrentReuseContext is caller-constructible. Equality between frozen plan labels
and caller-supplied labels proves only structural equality, not that the labels
were independently observed as current at use time.

This addendum does not create a second G4 owner. It wraps the existing G4
classifier and refuses to turn the all-equal structural state into reusable-plan
currentness until a future owner-authenticated observation adapter supplies that
separate proof plane.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from tools.awj032.glm53_g4_prefetch_plan_revalidation import (
    AXES,
    CurrentReuseContext,
    G3PlanProjection,
    HOLD_RECOMPUTE_G3,
    REVALIDATED_UNCHANGED,
    revalidate_g3_plan,
)

SCHEMA = "AURA-GLM53-G4-W3-OWNER-CURRENTNESS-QUARANTINE-v1"
G4_OWNER_PR = 757
G4_OWNER_SEMANTIC_HEAD = "68d76cb7d08366d085be13ad68871ab3c9cf00e1"
G4_OWNER_PARENT_HEAD_AT_REPAIR = "f8408d480f9209923932447e3f731bb2f2d30b86"
CURRENTNESS_LAW_PR = 395
CURRENTNESS_LAW_HEAD = "2a483a4232ce8745ee25e81246c39004ff28537e"
CURRENTNESS_LAW_RUN = 33336734334

HOLD_OWNER_OBSERVATION_AUTH_REQUIRED = "HOLD_OWNER_OBSERVATION_AUTH_REQUIRED"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class G4OwnerCurrentnessQuarantineReceipt:
    """Non-authoritative result of applying the W3 quarantine to G4."""

    schema: str
    g4_owner_pr: int
    g4_owner_semantic_head: str
    currentness_law_pr: int
    currentness_law_head: str
    currentness_law_run: int
    g3_receipt_digest: str
    plan_identity_digest: str
    base_g4_disposition: str
    disposition: str
    changed_axes: tuple[str, ...]
    structural_generation_match: bool
    independent_owner_observation_required: bool
    independently_resolved_currentness_proven: bool = False
    reusable_without_recompute: bool = False
    plan_executed_by_this_contract: bool = False
    transfer_effect_authorized: bool = False
    native_route_mutated: bool = False
    physical_io_proven: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("G4_W3_SCHEMA_MISMATCH")
        if self.g4_owner_pr != G4_OWNER_PR:
            raise ValueError("G4_W3_OWNER_PR_MISMATCH")
        if self.g4_owner_semantic_head != G4_OWNER_SEMANTIC_HEAD:
            raise ValueError("G4_W3_OWNER_SEMANTIC_HEAD_MISMATCH")
        if (self.currentness_law_pr, self.currentness_law_head, self.currentness_law_run) != (
            CURRENTNESS_LAW_PR,
            CURRENTNESS_LAW_HEAD,
            CURRENTNESS_LAW_RUN,
        ):
            raise ValueError("G4_W3_CURRENTNESS_LAW_PROVENANCE_MISMATCH")

        canonical_changed = tuple(axis for axis in AXES if axis in set(self.changed_axes))
        if canonical_changed != self.changed_axes:
            raise ValueError("G4_W3_CHANGED_AXES_NOT_CANONICAL")

        if self.changed_axes:
            if self.base_g4_disposition != HOLD_RECOMPUTE_G3:
                raise ValueError("G4_W3_DRIFT_MUST_PRESERVE_BASE_HOLD")
            if self.disposition != HOLD_RECOMPUTE_G3:
                raise ValueError("G4_W3_DRIFT_CANNOT_BE_DOWNGRADED")
            if self.structural_generation_match:
                raise ValueError("G4_W3_DRIFT_CANNOT_CLAIM_STRUCTURAL_MATCH")
        else:
            if self.base_g4_disposition != REVALIDATED_UNCHANGED:
                raise ValueError("G4_W3_EQUAL_STATE_BASE_DISPOSITION_MISMATCH")
            if self.disposition != HOLD_OWNER_OBSERVATION_AUTH_REQUIRED:
                raise ValueError("G4_W3_EQUAL_STATE_MUST_HOLD_FOR_OWNER_OBSERVATION")
            if not self.structural_generation_match:
                raise ValueError("G4_W3_EQUAL_STATE_MUST_RECORD_STRUCTURAL_MATCH")

        if not self.independent_owner_observation_required:
            raise ValueError("G4_W3_OWNER_OBSERVATION_REQUIREMENT_MUST_REMAIN_TRUE")
        if self.independently_resolved_currentness_proven:
            raise ValueError("G4_W3_CANNOT_SELF_PROVE_CURRENTNESS")
        if self.reusable_without_recompute:
            raise ValueError("G4_W3_CANNOT_GRANT_PLAN_REUSE")
        if any((
            self.plan_executed_by_this_contract,
            self.transfer_effect_authorized,
            self.native_route_mutated,
            self.physical_io_proven,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )):
            raise ValueError("G4_W3_CANNOT_WIDEN_EXECUTION_OR_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def quarantine_caller_shaped_currentness(
    *,
    plan: G3PlanProjection,
    current: CurrentReuseContext,
) -> G4OwnerCurrentnessQuarantineReceipt:
    """Preserve drift HOLDs and quarantine all-equal caller-shaped observations.

    If any G4 axis differs, the existing owner already has sufficient reason to
    recompute G3 and that HOLD is preserved exactly.

    If all eight labels are equal, the base G4 result is only a structural
    equality fact. Because this addendum has no owner registry/resolver capable
    of authenticating use-time observations, it returns
    HOLD_OWNER_OBSERVATION_AUTH_REQUIRED rather than granting reuse.
    """
    base = revalidate_g3_plan(plan=plan, current=current)
    changed = base.changed_axes
    structural_match = not changed
    disposition = (
        HOLD_OWNER_OBSERVATION_AUTH_REQUIRED
        if structural_match
        else HOLD_RECOMPUTE_G3
    )
    receipt = G4OwnerCurrentnessQuarantineReceipt(
        schema=SCHEMA,
        g4_owner_pr=G4_OWNER_PR,
        g4_owner_semantic_head=G4_OWNER_SEMANTIC_HEAD,
        currentness_law_pr=CURRENTNESS_LAW_PR,
        currentness_law_head=CURRENTNESS_LAW_HEAD,
        currentness_law_run=CURRENTNESS_LAW_RUN,
        g3_receipt_digest=base.g3_receipt_digest,
        plan_identity_digest=base.plan_identity_digest,
        base_g4_disposition=base.disposition,
        disposition=disposition,
        changed_axes=changed,
        structural_generation_match=structural_match,
        independent_owner_observation_required=True,
    )
    receipt.validate_claim_ceiling()
    return receipt


def prove_quarantine_lattice(plan: G3PlanProjection) -> Mapping[str, int]:
    """Exhaust the inherited 2^8 label lattice under the stricter W3 boundary."""
    plan.validate()
    total = 0
    owner_observation_holds = 0
    recompute_holds = 0
    reusable = 0
    for mask in range(1 << len(AXES)):
        values: dict[str, str] = {}
        for bit, axis in enumerate(AXES):
            frozen = getattr(plan, axis)
            values[axis] = f"{frozen}::drift" if mask & (1 << bit) else frozen
        receipt = quarantine_caller_shaped_currentness(
            plan=plan,
            current=CurrentReuseContext(**values),
        )
        if receipt.disposition == HOLD_OWNER_OBSERVATION_AUTH_REQUIRED:
            owner_observation_holds += 1
        elif receipt.disposition == HOLD_RECOMPUTE_G3:
            recompute_holds += 1
        else:
            raise AssertionError("G4_W3_UNEXPECTED_DISPOSITION")
        reusable += int(receipt.reusable_without_recompute)
        total += 1
    return {
        "states": total,
        "owner_observation_holds": owner_observation_holds,
        "recompute_holds": recompute_holds,
        "reusable": reusable,
    }
