"""G4 W3 addendum: owner-resolved, epoch-stable reuse currentness for GLM-5.3.

D0 / HS1 / NONPROMOTING / STACKED ADDENDUM.

PR #757 owns the G4 generation-bound plan-revalidation semantics. This module
owns only a post-authoring W3 residual: ``CurrentReuseContext`` is a plain value
object, so direct caller construction cannot itself prove that the eight
use-time generations came from their respective owners or coexisted in one
state generation.

The addendum therefore accepts no direct use-time context. It requires an
owner resolver, brackets the consequence-bearing read with one stable owner
state epoch, obtains a plan-bound owner observation, delegates the actual
changed-axis decision to G4 unchanged, and fails closed on any missing,
malformed, exceptional, mismatched, or drifting owner state.

The resolver is a trusted integration boundary supplied by the owning
runtime/control plane. This pure contract does not authenticate the resolver
producer or independently prove source/runtime truth. It records those limits
explicitly so resolver injection cannot be laundered into producer-authentication
or effect authority.

It never executes a transfer, mutates native routing, proves physical I/O, or
grants execution/effect/Gate-10/K27/native-KV authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol

from tools.awj032.glm53_g4_prefetch_plan_revalidation import (
    CurrentReuseContext,
    G3PlanProjection,
    HOLD_RECOMPUTE_G3,
    REVALIDATED_UNCHANGED,
    revalidate_g3_plan,
)

SCHEMA = "AURA-GLM53-G4-OWNER-CURRENTNESS-W3-v1"
OWNER_REVALIDATED_UNCHANGED = "OWNER_REVALIDATED_UNCHANGED"
HOLD_OWNER_CURRENTNESS_REQUIRED = "HOLD_OWNER_CURRENTNESS_REQUIRED"
HOLD_OWNER_STATE_EPOCH_CHANGED = "HOLD_OWNER_STATE_EPOCH_CHANGED"
HOLD_RECOMPUTE_G3_OWNER_RESOLVED = "HOLD_RECOMPUTE_G3_OWNER_RESOLVED"

# Exact-green serializability precedent consumed as a law anchor, not copied.
O65_HEAD = "7efca33d95f6dc39c4e159250d45373b260060ed"
O65_RUN = 33410032496
O65_JOB = 99546999922


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


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _sha256(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError(f"{name}_MUST_BE_LOWER_HEX_SHA256")


@dataclass(frozen=True)
class OwnerReuseStateObservation:
    """Resolver projection for one exact G4 plan identity and epoch.

    ``owner`` describes the integration responsibility, not producer
    authentication by this contract. The resolver implementation must be bound
    by the trusted runtime/control plane outside this pure membrane.
    """

    plan_identity_digest: str
    owner_state_epoch: str
    resolver_generation: str
    context: CurrentReuseContext

    def validate(self) -> None:
        _sha256(self.plan_identity_digest, "PLAN_IDENTITY_DIGEST")
        _required(self.owner_state_epoch, "OWNER_STATE_EPOCH")
        _required(self.resolver_generation, "RESOLVER_GENERATION")
        if not isinstance(self.context, CurrentReuseContext):
            raise ValueError("CURRENT_REUSE_CONTEXT_TYPE_INVALID")
        self.context.validate()

    @property
    def observation_digest(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": SCHEMA,
                "plan_identity_digest": self.plan_identity_digest,
                "owner_state_epoch": self.owner_state_epoch,
                "resolver_generation": self.resolver_generation,
                "context": asdict(self.context),
            }
        )


class G4OwnerReuseStateResolver(Protocol):
    """Trusted integration boundary for G4 use-time state.

    Implementations are supplied by the owning runtime/control plane. The
    membrane deliberately has no API accepting raw currentness strings from a
    caller. The same nonempty epoch must bracket the full owner observation.

    Trust in the resolver implementation is external to this contract. Merely
    satisfying this Python protocol does not cryptographically authenticate a
    producer and does not itself prove source/runtime truth.
    """

    def resolve_g4_state_epoch(self, *, plan_identity_digest: str) -> str | None: ...

    def resolve_g4_reuse_state(
        self, *, plan_identity_digest: str
    ) -> OwnerReuseStateObservation | None: ...


@dataclass(frozen=True)
class G4OwnerCurrentnessReceipt:
    schema: str
    disposition: str
    reason_code: str
    plan_identity_digest: str
    owner_state_epoch: str | None
    owner_resolver_generation: str | None
    owner_observation_digest: str | None
    base_g4_receipt_digest: str | None
    changed_axes: tuple[str, ...]
    owner_context_resolved: bool
    owner_state_epoch_stable: bool
    reusable_without_recompute: bool
    recompute_g3_required: bool
    owner_resolver_authenticated_by_this_contract: bool = False
    owner_currentness_truth_proven_by_this_contract: bool = False
    revalidation_required_at_effect_boundary: bool = True
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
        _sha256(self.plan_identity_digest, "RECEIPT_PLAN_IDENTITY_DIGEST")
        if self.owner_state_epoch is not None:
            _required(self.owner_state_epoch, "RECEIPT_OWNER_STATE_EPOCH")
        if self.owner_resolver_generation is not None:
            _required(self.owner_resolver_generation, "RECEIPT_RESOLVER_GENERATION")
        if self.owner_observation_digest is not None:
            _sha256(self.owner_observation_digest, "OWNER_OBSERVATION_DIGEST")
        if self.base_g4_receipt_digest is not None:
            _sha256(self.base_g4_receipt_digest, "BASE_G4_RECEIPT_DIGEST")

        if self.disposition == OWNER_REVALIDATED_UNCHANGED:
            if not (
                self.owner_context_resolved
                and self.owner_state_epoch_stable
                and self.owner_state_epoch is not None
                and self.owner_resolver_generation is not None
                and self.owner_observation_digest is not None
                and self.base_g4_receipt_digest is not None
                and not self.changed_axes
                and self.reusable_without_recompute
                and not self.recompute_g3_required
            ):
                raise ValueError("OWNER_REVALIDATED_STATE_INVALID")
        else:
            if self.reusable_without_recompute:
                raise ValueError("HOLD_CANNOT_CLAIM_REUSABLE")
            if self.disposition == HOLD_RECOMPUTE_G3_OWNER_RESOLVED:
                if not self.owner_context_resolved or not self.owner_state_epoch_stable:
                    raise ValueError("OWNER_RESOLVED_RECOMPUTE_REQUIRES_STABLE_OWNER_STATE")
                if not self.changed_axes or not self.recompute_g3_required:
                    raise ValueError("OWNER_RESOLVED_RECOMPUTE_STATE_INVALID")

        if self.revalidation_required_at_effect_boundary is not True:
            raise ValueError("EFFECT_BOUNDARY_REVALIDATION_REQUIRED")
        forbidden = (
            self.owner_resolver_authenticated_by_this_contract,
            self.owner_currentness_truth_proven_by_this_contract,
            self.plan_executed_by_this_contract,
            self.transfer_effect_authorized,
            self.native_route_mutated,
            self.physical_io_proven,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("G4_W3_CANNOT_SELF_AUTHENTICATE_OR_WIDEN_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def _hold(
    *,
    plan_identity_digest: str,
    disposition: str,
    reason_code: str,
    epoch: str | None = None,
    observation: OwnerReuseStateObservation | None = None,
    base_g4_receipt_digest: str | None = None,
    changed_axes: tuple[str, ...] = (),
    owner_context_resolved: bool = False,
    owner_state_epoch_stable: bool = False,
    recompute_g3_required: bool = False,
) -> G4OwnerCurrentnessReceipt:
    receipt = G4OwnerCurrentnessReceipt(
        schema=SCHEMA,
        disposition=disposition,
        reason_code=reason_code,
        plan_identity_digest=plan_identity_digest,
        owner_state_epoch=epoch,
        owner_resolver_generation=(observation.resolver_generation if observation else None),
        owner_observation_digest=(observation.observation_digest if observation else None),
        base_g4_receipt_digest=base_g4_receipt_digest,
        changed_axes=changed_axes,
        owner_context_resolved=owner_context_resolved,
        owner_state_epoch_stable=owner_state_epoch_stable,
        reusable_without_recompute=False,
        recompute_g3_required=recompute_g3_required,
    )
    receipt.validate_claim_ceiling()
    return receipt


def _resolve_epoch(
    *, resolver: G4OwnerReuseStateResolver, plan_identity_digest: str
) -> tuple[str | None, str | None]:
    try:
        epoch = resolver.resolve_g4_state_epoch(plan_identity_digest=plan_identity_digest)
    except Exception:
        return None, "OWNER_STATE_EPOCH_RESOLVER_ERROR"
    if epoch is None:
        return None, "OWNER_STATE_EPOCH_UNAVAILABLE_OR_UNKNOWN"
    if not isinstance(epoch, str) or not epoch.strip():
        return None, "OWNER_STATE_EPOCH_INVALID"
    return epoch, None


def revalidate_g3_plan_owner_resolved(
    *,
    plan: G3PlanProjection,
    owner_resolver: G4OwnerReuseStateResolver | None,
) -> G4OwnerCurrentnessReceipt:
    """Revalidate G4 through one resolver-obtained, epoch-stable observation.

    Raw ``CurrentReuseContext`` is intentionally absent from this public API.
    Matching caller-created strings therefore cannot mint current reuse state
    through this membrane directly. Resolver producer authenticity remains an
    external runtime/control-plane obligation and is explicitly *not* proven by
    the returned receipt.
    """

    plan.validate()
    plan_identity = plan.plan_identity_digest
    if owner_resolver is None:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_CURRENTNESS_REQUIRED,
            reason_code="OWNER_RESOLVER_UNAVAILABLE",
        )

    epoch_before, error = _resolve_epoch(
        resolver=owner_resolver, plan_identity_digest=plan_identity
    )
    if error is not None:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_CURRENTNESS_REQUIRED,
            reason_code=error,
        )

    try:
        observation = owner_resolver.resolve_g4_reuse_state(
            plan_identity_digest=plan_identity
        )
    except Exception:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_CURRENTNESS_REQUIRED,
            reason_code="OWNER_REUSE_STATE_RESOLVER_ERROR",
            epoch=epoch_before,
        )
    if observation is None:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_CURRENTNESS_REQUIRED,
            reason_code="OWNER_REUSE_STATE_UNAVAILABLE_OR_UNKNOWN",
            epoch=epoch_before,
        )
    try:
        observation.validate()
    except ValueError:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_CURRENTNESS_REQUIRED,
            reason_code="OWNER_REUSE_STATE_INVALID",
            epoch=epoch_before,
        )
    if observation.plan_identity_digest != plan_identity:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_CURRENTNESS_REQUIRED,
            reason_code="OWNER_REUSE_STATE_PLAN_IDENTITY_MISMATCH",
            epoch=epoch_before,
            observation=observation,
        )
    if observation.owner_state_epoch != epoch_before:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_STATE_EPOCH_CHANGED,
            reason_code="OWNER_OBSERVATION_NOT_FROM_OPEN_EPOCH",
            epoch=epoch_before,
            observation=observation,
        )

    base = revalidate_g3_plan(plan=plan, current=observation.context)

    epoch_after, final_error = _resolve_epoch(
        resolver=owner_resolver, plan_identity_digest=plan_identity
    )
    if final_error is not None:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_CURRENTNESS_REQUIRED,
            reason_code=final_error,
            epoch=epoch_before,
            observation=observation,
            base_g4_receipt_digest=base.receipt_digest,
            changed_axes=base.changed_axes,
            owner_context_resolved=True,
        )
    if epoch_after != epoch_before:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_OWNER_STATE_EPOCH_CHANGED,
            reason_code="OWNER_STATE_EPOCH_CHANGED_DURING_REVALIDATION",
            epoch=epoch_after,
            observation=observation,
            base_g4_receipt_digest=base.receipt_digest,
            changed_axes=base.changed_axes,
            owner_context_resolved=True,
        )

    if base.disposition == HOLD_RECOMPUTE_G3:
        return _hold(
            plan_identity_digest=plan_identity,
            disposition=HOLD_RECOMPUTE_G3_OWNER_RESOLVED,
            reason_code="OWNER_RESOLVED_AXIS_DRIFT_REQUIRES_G3_RECOMPUTE",
            epoch=epoch_before,
            observation=observation,
            base_g4_receipt_digest=base.receipt_digest,
            changed_axes=base.changed_axes,
            owner_context_resolved=True,
            owner_state_epoch_stable=True,
            recompute_g3_required=True,
        )
    if base.disposition != REVALIDATED_UNCHANGED:
        raise AssertionError("UNEXPECTED_BASE_G4_DISPOSITION")

    receipt = G4OwnerCurrentnessReceipt(
        schema=SCHEMA,
        disposition=OWNER_REVALIDATED_UNCHANGED,
        reason_code="RESOLVER_CONTEXT_UNCHANGED_IN_ONE_STABLE_EPOCH",
        plan_identity_digest=plan_identity,
        owner_state_epoch=epoch_before,
        owner_resolver_generation=observation.resolver_generation,
        owner_observation_digest=observation.observation_digest,
        base_g4_receipt_digest=base.receipt_digest,
        changed_axes=(),
        owner_context_resolved=True,
        owner_state_epoch_stable=True,
        reusable_without_recompute=True,
        recompute_g3_required=False,
    )
    receipt.validate_claim_ceiling()
    return receipt
