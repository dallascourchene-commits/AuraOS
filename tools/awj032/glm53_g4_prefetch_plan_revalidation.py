"""G4: generation-bound reuse gate for GLM-5.3 speculative transfer plans.

D0 / HS1 / NONPROMOTING.

G3 / PR #749 proves a lawful transfer *plan* can commute with predictor
abstention while preserving exact native-demand continuity. That proof does not
make a plan timeless. Predictor, calibration, policy, source, runtime, cache,
storage and host geometry can change between plan construction and attempted
reuse.

This module freezes those identity-bearing axes and requires use-time
revalidation before a G3 plan can be reused. It never executes a transfer,
changes native routing, observes physical I/O, or grants execution/effect
permission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "AURA-GLM53-G4-PREFETCH-PLAN-REVALIDATION-v1"
G3_SEMANTIC_HEAD = "bdcd92c25308a70f263439c23a73d0240b511d86"
G3_PROOF_RUN = 33428379023
G3_PROOF_JOB = 99607453967
G3_DESCENDANT_SAFE_RUN = 33428378932
G3_DESCENDANT_SAFE_JOB = 99607453756

REVALIDATED_UNCHANGED = "REVALIDATED_UNCHANGED"
HOLD_RECOMPUTE_G3 = "HOLD_RECOMPUTE_G3"

AXES = (
    "prediction_generation",
    "calibration_generation",
    "policy_generation",
    "source_binding_generation",
    "runtime_generation",
    "cache_generation",
    "storage_geometry_generation",
    "host_profile_generation",
)


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


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: str, name: str) -> str:
    value = _text(value, name)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name}_MUST_BE_LOWER_HEX_SHA256")
    return value


@dataclass(frozen=True)
class G3PlanProjection:
    """Exact non-authoritative projection of one already-built G3 plan."""

    g3_receipt_digest: str
    prediction_digest: str
    layer_id: str
    binding_digest: str
    admitted_experts: tuple[int, ...]
    prediction_generation: str
    calibration_generation: str
    policy_generation: str
    source_binding_generation: str
    runtime_generation: str
    cache_generation: str
    storage_geometry_generation: str
    host_profile_generation: str
    transfer_effect_authorized: bool = False
    native_route_mutated: bool = False
    physical_io_attested: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        _sha256(self.g3_receipt_digest, "G3_RECEIPT_DIGEST")
        _sha256(self.prediction_digest, "PREDICTION_DIGEST")
        _text(self.layer_id, "LAYER_ID")
        _text(self.binding_digest, "BINDING_DIGEST")
        if not isinstance(self.admitted_experts, tuple):
            raise ValueError("ADMITTED_EXPERTS_MUST_BE_TUPLE")
        if tuple(sorted(set(self.admitted_experts))) != self.admitted_experts:
            raise ValueError("ADMITTED_EXPERTS_MUST_BE_CANONICAL_UNIQUE_SORTED")
        if any(isinstance(e, bool) or not isinstance(e, int) or e < 0 for e in self.admitted_experts):
            raise ValueError("ADMITTED_EXPERT_ID_INVALID")
        for axis in AXES:
            _text(getattr(self, axis), axis.upper())
        if any((
            self.transfer_effect_authorized,
            self.native_route_mutated,
            self.physical_io_attested,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
        )):
            raise ValueError("G3_PLAN_PROJECTION_CANNOT_WIDEN_AUTHORITY_OR_PHYSICAL_TRUTH")

    @property
    def plan_identity_digest(self) -> str:
        self.validate()
        return _sha({
            "domain": SCHEMA,
            "g3_semantic_head": G3_SEMANTIC_HEAD,
            "g3_receipt_digest": self.g3_receipt_digest,
            "prediction_digest": self.prediction_digest,
            "layer_id": self.layer_id,
            "binding_digest": self.binding_digest,
            "admitted_experts": self.admitted_experts,
            "axes": {axis: getattr(self, axis) for axis in AXES},
        })


@dataclass(frozen=True)
class CurrentReuseContext:
    """Use-time identity observations supplied by their respective owners."""

    prediction_generation: str
    calibration_generation: str
    policy_generation: str
    source_binding_generation: str
    runtime_generation: str
    cache_generation: str
    storage_geometry_generation: str
    host_profile_generation: str

    def validate(self) -> None:
        for axis in AXES:
            _text(getattr(self, axis), axis.upper())


@dataclass(frozen=True)
class G4RevalidationReceipt:
    schema: str
    g3_semantic_head: str
    g3_proof_run: int
    g3_proof_job: int
    g3_descendant_safe_run: int
    g3_descendant_safe_job: int
    g3_receipt_digest: str
    plan_identity_digest: str
    disposition: str
    changed_axes: tuple[str, ...]
    reusable_without_recompute: bool
    recompute_g3_required: bool
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
            raise ValueError("G4_SCHEMA_MISMATCH")
        if self.g3_semantic_head != G3_SEMANTIC_HEAD:
            raise ValueError("G4_G3_SEMANTIC_HEAD_MISMATCH")
        if (self.g3_proof_run, self.g3_proof_job) != (G3_PROOF_RUN, G3_PROOF_JOB):
            raise ValueError("G4_G3_PROOF_COORDINATE_MISMATCH")
        if (self.g3_descendant_safe_run, self.g3_descendant_safe_job) != (
            G3_DESCENDANT_SAFE_RUN,
            G3_DESCENDANT_SAFE_JOB,
        ):
            raise ValueError("G4_G3_DESCENDANT_SAFE_PROOF_COORDINATE_MISMATCH")
        if self.disposition == REVALIDATED_UNCHANGED:
            if self.changed_axes or not self.reusable_without_recompute or self.recompute_g3_required:
                raise ValueError("UNCHANGED_REVALIDATION_STATE_INVALID")
        elif self.disposition == HOLD_RECOMPUTE_G3:
            if not self.changed_axes or self.reusable_without_recompute or not self.recompute_g3_required:
                raise ValueError("CHANGED_REVALIDATION_STATE_INVALID")
        else:
            raise ValueError("G4_DISPOSITION_INVALID")
        if tuple(axis for axis in AXES if axis in set(self.changed_axes)) != self.changed_axes:
            raise ValueError("CHANGED_AXES_MUST_BE_CANONICAL")
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
            raise ValueError("G4_CANNOT_WIDEN_EXECUTION_OR_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def changed_axes_tree(plan: G3PlanProjection, current: CurrentReuseContext) -> tuple[str, ...]:
    """Explicit decision-tree formulation of currentness drift."""
    plan.validate()
    current.validate()
    changed: list[str] = []
    if plan.prediction_generation != current.prediction_generation:
        changed.append("prediction_generation")
    if plan.calibration_generation != current.calibration_generation:
        changed.append("calibration_generation")
    if plan.policy_generation != current.policy_generation:
        changed.append("policy_generation")
    if plan.source_binding_generation != current.source_binding_generation:
        changed.append("source_binding_generation")
    if plan.runtime_generation != current.runtime_generation:
        changed.append("runtime_generation")
    if plan.cache_generation != current.cache_generation:
        changed.append("cache_generation")
    if plan.storage_geometry_generation != current.storage_geometry_generation:
        changed.append("storage_geometry_generation")
    if plan.host_profile_generation != current.host_profile_generation:
        changed.append("host_profile_generation")
    return tuple(changed)


def changed_axes_table(plan: G3PlanProjection, current: CurrentReuseContext) -> tuple[str, ...]:
    """Ordered-table formulation, intentionally shaped differently from the tree."""
    plan.validate()
    current.validate()
    rows = tuple((axis, getattr(plan, axis), getattr(current, axis)) for axis in AXES)
    return tuple(axis for axis, frozen, observed in rows if frozen != observed)


def revalidate_g3_plan(
    *,
    plan: G3PlanProjection,
    current: CurrentReuseContext,
) -> G4RevalidationReceipt:
    """Fail closed if any identity-bearing plan-use axis changed.

    The same rule applies to an empty G3 abstention plan: zero speculative bytes do
    not make a stale policy/source/runtime/cache context reusable.
    """
    tree = changed_axes_tree(plan, current)
    table = changed_axes_table(plan, current)
    if tree != table:
        raise AssertionError("G4_DIFFERENT_J_REVALIDATION_DISAGREEMENT")
    changed = tree
    reusable = not changed
    receipt = G4RevalidationReceipt(
        schema=SCHEMA,
        g3_semantic_head=G3_SEMANTIC_HEAD,
        g3_proof_run=G3_PROOF_RUN,
        g3_proof_job=G3_PROOF_JOB,
        g3_descendant_safe_run=G3_DESCENDANT_SAFE_RUN,
        g3_descendant_safe_job=G3_DESCENDANT_SAFE_JOB,
        g3_receipt_digest=plan.g3_receipt_digest,
        plan_identity_digest=plan.plan_identity_digest,
        disposition=REVALIDATED_UNCHANGED if reusable else HOLD_RECOMPUTE_G3,
        changed_axes=changed,
        reusable_without_recompute=reusable,
        recompute_g3_required=not reusable,
    )
    receipt.validate_claim_ceiling()
    return receipt


def prove_finite_drift_lattice(plan: G3PlanProjection) -> Mapping[str, int]:
    """Exhaust all 2^8 changed/unchanged masks and require Different-J agreement."""
    plan.validate()
    total = 0
    unchanged = 0
    held = 0
    for mask in range(1 << len(AXES)):
        values = {}
        expected = []
        for bit, axis in enumerate(AXES):
            frozen = getattr(plan, axis)
            if mask & (1 << bit):
                values[axis] = f"{frozen}::drift"
                expected.append(axis)
            else:
                values[axis] = frozen
        current = CurrentReuseContext(**values)
        tree = changed_axes_tree(plan, current)
        table = changed_axes_table(plan, current)
        if tree != table or tree != tuple(expected):
            raise AssertionError("G4_FINITE_LATTICE_CLASSIFIER_MISMATCH")
        receipt = revalidate_g3_plan(plan=plan, current=current)
        if mask == 0:
            if receipt.disposition != REVALIDATED_UNCHANGED:
                raise AssertionError("G4_UNCHANGED_MASK_MUST_REVALIDATE")
            unchanged += 1
        else:
            if receipt.disposition != HOLD_RECOMPUTE_G3:
                raise AssertionError("G4_DRIFT_MASK_MUST_HOLD")
            held += 1
        total += 1
    return {"states": total, "unchanged": unchanged, "held": held}
