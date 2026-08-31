"""G4: structural generation revalidation for GLM-5.3 speculative transfer plans.

D0 / HS1 / NONPROMOTING.

G3 / PR #749 proves a lawful transfer *plan* can commute with predictor
abstention while preserving exact native-demand continuity. That proof does not
make a plan timeless. Predictor, calibration, policy, source, runtime, cache,
storage and host geometry can change between plan construction and attempted
reuse.

This module freezes those identity-bearing axes and compares them with use-time
projections. It deliberately does NOT authenticate the producers of those
projections. Therefore exact label equality establishes only a structural
currentness candidate; it never grants plan reuse, transfer execution, physical
I/O truth, routing authority, or effect authority.

Law:
    MatchingGenerationLabels != AuthenticatedOwnerCurrentness != ReuseAuthority
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "AURA-GLM53-G4-PREFETCH-PLAN-REVALIDATION-v2"
G3_SEMANTIC_HEAD = "bdcd92c25308a70f263439c23a73d0240b511d86"
G3_PROOF_RUN = 33428379023
G3_PROOF_JOB = 99607453967
G3_DESCENDANT_SAFE_RUN = 33428378932
G3_DESCENDANT_SAFE_JOB = 99607453756

STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED = "STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED"
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
        if any(
            isinstance(expert, bool) or not isinstance(expert, int) or expert < 0
            for expert in self.admitted_experts
        ):
            raise ValueError("ADMITTED_EXPERT_ID_INVALID")
        for axis in AXES:
            _text(getattr(self, axis), axis.upper())
        if any(
            (
                self.transfer_effect_authorized,
                self.native_route_mutated,
                self.physical_io_attested,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError(
                "G3_PLAN_PROJECTION_CANNOT_WIDEN_AUTHORITY_OR_PHYSICAL_TRUTH"
            )

    @property
    def plan_identity_digest(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": SCHEMA,
                "g3_semantic_head": G3_SEMANTIC_HEAD,
                "g3_receipt_digest": self.g3_receipt_digest,
                "prediction_digest": self.prediction_digest,
                "layer_id": self.layer_id,
                "binding_digest": self.binding_digest,
                "admitted_experts": self.admitted_experts,
                "axes": {axis: getattr(self, axis) for axis in AXES},
            }
        )


@dataclass(frozen=True)
class CurrentReuseContext:
    """Caller-supplied use-time generation projection.

    The labels can be compared structurally, but this object cannot authenticate
    their producers or prove that an owner/registry supplied them.
    """

    prediction_generation: str
    calibration_generation: str
    policy_generation: str
    source_binding_generation: str
    runtime_generation: str
    cache_generation: str
    storage_geometry_generation: str
    host_profile_generation: str
    owner_currentness_authenticated: bool = False

    def validate(self) -> None:
        for axis in AXES:
            _text(getattr(self, axis), axis.upper())
        if self.owner_currentness_authenticated:
            raise ValueError(
                "CALLER_CONTEXT_CANNOT_SELF_MINT_OWNER_CURRENTNESS_AUTHENTICATION"
            )


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
    structural_generation_match: bool
    recompute_g3_required: bool
    owner_currentness_authentication_required: bool = True
    owner_currentness_authenticated_by_this_contract: bool = False
    reuse_authorized_by_this_contract: bool = False
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
        _sha256(self.g3_receipt_digest, "G4_G3_RECEIPT_DIGEST")
        _sha256(self.plan_identity_digest, "G4_PLAN_IDENTITY_DIGEST")

        if self.disposition == STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED:
            if (
                self.changed_axes
                or not self.structural_generation_match
                or self.recompute_g3_required
            ):
                raise ValueError("STRUCTURAL_MATCH_REVALIDATION_STATE_INVALID")
        elif self.disposition == HOLD_RECOMPUTE_G3:
            if (
                not self.changed_axes
                or self.structural_generation_match
                or not self.recompute_g3_required
            ):
                raise ValueError("CHANGED_REVALIDATION_STATE_INVALID")
        else:
            raise ValueError("G4_DISPOSITION_INVALID")

        changed_set = set(self.changed_axes)
        if len(changed_set) != len(self.changed_axes):
            raise ValueError("CHANGED_AXES_MUST_BE_UNIQUE")
        if any(axis not in AXES for axis in self.changed_axes):
            raise ValueError("CHANGED_AXES_UNKNOWN")
        if tuple(axis for axis in AXES if axis in changed_set) != self.changed_axes:
            raise ValueError("CHANGED_AXES_MUST_BE_CANONICAL")

        if not self.owner_currentness_authentication_required:
            raise ValueError("G4_OWNER_CURRENTNESS_AUTHENTICATION_MUST_REMAIN_REQUIRED")
        if any(
            (
                self.owner_currentness_authenticated_by_this_contract,
                self.reuse_authorized_by_this_contract,
                self.plan_executed_by_this_contract,
                self.transfer_effect_authorized,
                self.native_route_mutated,
                self.physical_io_proven,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
                self.gate10_promoted,
                self.merge_deploy_spend_public_financial_human_effect,
            )
        ):
            raise ValueError("G4_CANNOT_WIDEN_CURRENTNESS_EXECUTION_OR_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def changed_axes_tree(
    plan: G3PlanProjection, current: CurrentReuseContext
) -> tuple[str, ...]:
    """Explicit decision-tree formulation of structural generation drift."""
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


def changed_axes_table(
    plan: G3PlanProjection, current: CurrentReuseContext
) -> tuple[str, ...]:
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
    """Compare structural generations without authenticating owner currentness.

    Any drift fail-closes to G3 recomputation. Exact label equality produces only
    a structural-match receipt that still requires owner/registry currentness
    authentication before any downstream consumer can treat the plan as reusable.
    """
    tree = changed_axes_tree(plan, current)
    table = changed_axes_table(plan, current)
    if tree != table:
        raise AssertionError("G4_DIFFERENT_J_REVALIDATION_DISAGREEMENT")

    changed = tree
    structural_match = not changed
    receipt = G4RevalidationReceipt(
        schema=SCHEMA,
        g3_semantic_head=G3_SEMANTIC_HEAD,
        g3_proof_run=G3_PROOF_RUN,
        g3_proof_job=G3_PROOF_JOB,
        g3_descendant_safe_run=G3_DESCENDANT_SAFE_RUN,
        g3_descendant_safe_job=G3_DESCENDANT_SAFE_JOB,
        g3_receipt_digest=plan.g3_receipt_digest,
        plan_identity_digest=plan.plan_identity_digest,
        disposition=(
            STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED
            if structural_match
            else HOLD_RECOMPUTE_G3
        ),
        changed_axes=changed,
        structural_generation_match=structural_match,
        recompute_g3_required=not structural_match,
    )
    receipt.validate_claim_ceiling()
    return receipt


def prove_finite_drift_lattice(plan: G3PlanProjection) -> Mapping[str, int]:
    """Exhaust all 2^8 changed/unchanged masks and require Different-J agreement."""
    plan.validate()
    total = 0
    structural_matches = 0
    held = 0
    for mask in range(1 << len(AXES)):
        values: dict[str, str] = {}
        expected: list[str] = []
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
            if receipt.disposition != STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED:
                raise AssertionError("G4_UNCHANGED_MASK_MUST_BE_STRUCTURAL_MATCH")
            if receipt.reuse_authorized_by_this_contract:
                raise AssertionError("G4_STRUCTURAL_MATCH_CANNOT_AUTHORIZE_REUSE")
            structural_matches += 1
        else:
            if receipt.disposition != HOLD_RECOMPUTE_G3:
                raise AssertionError("G4_DRIFT_MASK_MUST_HOLD")
            held += 1
        total += 1
    return {
        "states": total,
        "structural_matches": structural_matches,
        "held": held,
        "authenticated_reuse_authorizations": 0,
    }
