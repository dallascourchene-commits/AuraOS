"""Bind a calibrated GLM-5.3 C2 plan to its exact observed host operation.

D0 / HS1 / NONPROMOTING.

This relation consumes two independently proven lineages:
* PR #729: calibrated G2 planning -> immutable C2 request attachment.
* PR #727: operation/observer/backend provenance pattern for physical observations.

It may establish that an observation belongs to the exact C2 attempt descended from an
exact calibrated plan. It deliberately cannot infer that the plan *caused* byte or
latency savings. Causal benefit requires an independently bound counterfactual/baseline.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.awj032.glm53_g2_c2_transfer_plan_attachment import G2C2TransferPlanAttachment
from tools.awj032.glm53_owner_host_c2_handoff import (
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    OwnerHostC2JoinReceipt,
)

SCHEMA = "AURA-GLM53-G2-C2-PLAN-OPERATION-OBSERVATION-JOIN-v1"
WITNESS_SCHEMA = "AURA-GLM53-C2-OPERATION-OBSERVATION-WITNESS-v1"

PLAN_PARENT_HEAD = "5d7180f9a899b07526fd36cb290c85c8ebab4969"
PLAN_PARENT_BLOB = "c7be999691ef1a8c3e58c918c12574eab192c9e3"
OBSERVATION_PARENT_HEAD = "293c59d7260372ccd3b9e8130b12979b052c3ed9"
OBSERVATION_PARENT_BLOB = "98db548b6e8f7443b79d979eb0e177ac6aa68534"

BOUND = "PLAN_ATTEMPT_OPERATION_OBSERVATION_BOUND"
HOLD = "HOLD_OPERATION_OBSERVATION_REQUIRED"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _sha256(value: Any, code: str) -> str:
    value = _text(value, code)
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(code)
    return value


def _nonnegative_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class GLM53OperationObservationWitness:
    """Exact operation-scoped witness projected from an external owner/observer plane.

    This module validates relation consistency but does not itself authenticate the
    external producer registry. The provenance references therefore remain explicit in
    the final relation and no execution/effect authority is granted.
    """

    schema: str
    request_digest: str
    attempt_receipt_digest: str
    c2_join_logical_id: str
    plan_attachment_digest: str
    plan_source_binding_digest: str
    owner_host_observation_id: str
    operation_id: str
    runner_identity: str
    runner_generation: str
    source_snapshot_digest: str
    backend_owner_ref: str
    observer_generation: str
    host_measurement_ref: str
    lifecycle_measurement_ref: str
    physical_io_attestation_ref: str
    source_binding_revalidation_ref: str
    physical_read_bytes: int
    observer_current: bool = True
    exact_operation_bound: bool = True
    source_binding_revalidated: bool = True
    glm53_workload: bool = True
    tiny_fixture_crosscast: bool = False
    execution_authority_granted: bool = False
    effect_authority_granted: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != WITNESS_SCHEMA:
            raise ValueError("GLM53_OPERATION_WITNESS_SCHEMA_MISMATCH")
        for value, code in (
            (self.request_digest, "WITNESS_REQUEST_DIGEST_INVALID"),
            (self.attempt_receipt_digest, "WITNESS_ATTEMPT_DIGEST_INVALID"),
            (self.c2_join_logical_id, "WITNESS_C2_JOIN_ID_INVALID"),
            (self.plan_attachment_digest, "WITNESS_PLAN_ATTACHMENT_DIGEST_INVALID"),
            (self.source_snapshot_digest, "WITNESS_SOURCE_SNAPSHOT_DIGEST_INVALID"),
        ):
            _sha256(value, code)
        for value, code in (
            (self.plan_source_binding_digest, "WITNESS_PLAN_SOURCE_BINDING_REQUIRED"),
            (self.owner_host_observation_id, "WITNESS_OBSERVATION_ID_REQUIRED"),
            (self.operation_id, "WITNESS_OPERATION_ID_REQUIRED"),
            (self.runner_identity, "WITNESS_RUNNER_IDENTITY_REQUIRED"),
            (self.runner_generation, "WITNESS_RUNNER_GENERATION_REQUIRED"),
            (self.backend_owner_ref, "WITNESS_BACKEND_OWNER_REQUIRED"),
            (self.observer_generation, "WITNESS_OBSERVER_GENERATION_REQUIRED"),
            (self.host_measurement_ref, "WITNESS_HOST_MEASUREMENT_REF_REQUIRED"),
            (self.lifecycle_measurement_ref, "WITNESS_LIFECYCLE_MEASUREMENT_REF_REQUIRED"),
            (self.physical_io_attestation_ref, "WITNESS_PHYSICAL_ATTESTATION_REF_REQUIRED"),
            (self.source_binding_revalidation_ref, "WITNESS_SOURCE_REVALIDATION_REF_REQUIRED"),
        ):
            _text(value, code)
        _nonnegative_int(self.physical_read_bytes, "WITNESS_PHYSICAL_READ_BYTES_INVALID")
        if self.observer_current is not True:
            raise ValueError("WITNESS_OBSERVER_CURRENTNESS_REQUIRED")
        if self.exact_operation_bound is not True:
            raise ValueError("WITNESS_EXACT_OPERATION_BINDING_REQUIRED")
        if self.source_binding_revalidated is not True:
            raise ValueError("WITNESS_SOURCE_BINDING_REVALIDATION_REQUIRED")
        if self.glm53_workload is not True or self.tiny_fixture_crosscast is not False:
            raise ValueError("WITNESS_MUST_BE_GLM53_NOT_TINY_FIXTURE_CROSSCAST")
        if any((
            self.execution_authority_granted,
            self.effect_authority_granted,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
        )):
            raise ValueError("WITNESS_CANNOT_WIDEN_AUTHORITY")

    @property
    def witness_digest(self) -> str:
        self.validate()
        return _digest({"domain": WITNESS_SCHEMA, "witness": asdict(self)})


@dataclass(frozen=True)
class PlanOperationObservationJoin:
    schema: str
    disposition: str
    reason_code: str
    plan_parent_head: str
    observation_parent_head: str
    plan_attachment_digest: str
    request_digest: str
    attempt_receipt_digest: str
    c2_join_logical_id: str
    operation_observation_digest: str | None
    operation_id: str | None
    owner_host_observation_id: str | None
    physical_read_bytes: int | None
    plan_to_request_bound: bool
    request_to_attempt_bound: bool
    attempt_to_observation_bound: bool
    source_binding_revalidation_bound: bool
    observational_attribution_bound: bool
    counterfactual_baseline_required: bool = True
    causal_plan_benefit_proven: bool = False
    bytes_saved_proven: bool = False
    latency_saved_proven: bool = False
    physical_io_avoided_proven: bool = False
    native_route_mutated: bool = False
    execution_authorized: bool = False
    effect_authority_proven: bool = False
    g2_admitted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("PLAN_OPERATION_JOIN_SCHEMA_MISMATCH")
        if self.plan_parent_head != PLAN_PARENT_HEAD or self.observation_parent_head != OBSERVATION_PARENT_HEAD:
            raise ValueError("PLAN_OPERATION_JOIN_PARENT_GENERATION_MISMATCH")
        for value, code in (
            (self.plan_attachment_digest, "PLAN_OPERATION_JOIN_ATTACHMENT_DIGEST_INVALID"),
            (self.request_digest, "PLAN_OPERATION_JOIN_REQUEST_DIGEST_INVALID"),
            (self.attempt_receipt_digest, "PLAN_OPERATION_JOIN_ATTEMPT_DIGEST_INVALID"),
            (self.c2_join_logical_id, "PLAN_OPERATION_JOIN_C2_JOIN_ID_INVALID"),
        ):
            _sha256(value, code)
        if self.counterfactual_baseline_required is not True:
            raise ValueError("COUNTERFACTUAL_BASELINE_REQUIREMENT_CANNOT_BE_REMOVED")
        forbidden = (
            self.causal_plan_benefit_proven,
            self.bytes_saved_proven,
            self.latency_saved_proven,
            self.physical_io_avoided_proven,
            self.native_route_mutated,
            self.execution_authorized,
            self.effect_authority_proven,
            self.g2_admitted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(v is not False for v in forbidden):
            raise ValueError("PLAN_OPERATION_JOIN_CANNOT_MINT_CAUSAL_BENEFIT_OR_AUTHORITY")
        if self.disposition == BOUND:
            if not all((
                self.plan_to_request_bound,
                self.request_to_attempt_bound,
                self.attempt_to_observation_bound,
                self.source_binding_revalidation_bound,
                self.observational_attribution_bound,
            )):
                raise ValueError("BOUND_PLAN_OPERATION_JOIN_REQUIRES_COMPLETE_RELATION")
            if self.operation_observation_digest is None or self.operation_id is None or self.owner_host_observation_id is None:
                raise ValueError("BOUND_PLAN_OPERATION_JOIN_REQUIRES_OBSERVATION_IDENTITY")
            _sha256(self.operation_observation_digest, "PLAN_OPERATION_JOIN_OBSERVATION_DIGEST_INVALID")
            if self.physical_read_bytes is None:
                raise ValueError("BOUND_PLAN_OPERATION_JOIN_REQUIRES_OBSERVED_PHYSICAL_BYTES")
            _nonnegative_int(self.physical_read_bytes, "PLAN_OPERATION_JOIN_PHYSICAL_BYTES_INVALID")
        elif self.disposition == HOLD:
            if self.attempt_to_observation_bound or self.observational_attribution_bound:
                raise ValueError("HELD_PLAN_OPERATION_JOIN_CANNOT_CLAIM_OBSERVATION_BINDING")
        else:
            raise ValueError("PLAN_OPERATION_JOIN_DISPOSITION_INVALID")

    @property
    def relation_digest(self) -> str:
        self.validate_claim_ceiling()
        return _digest({"domain": SCHEMA, "relation": asdict(self)})


def bind_plan_attempt_operation_observation(
    *,
    attachment: G2C2TransferPlanAttachment,
    request: OwnerHostC2CanaryRequest,
    attempt: OwnerHostC2CanaryReceipt,
    c2_join: OwnerHostC2JoinReceipt,
    witness: GLM53OperationObservationWitness | None,
) -> PlanOperationObservationJoin:
    """Join exact planning and observation identities without claiming causality."""
    attachment.validate_claim_ceiling()
    request_digest = request.request_digest
    attempt_digest = attempt.receipt_digest
    join_id = c2_join.logical_id
    attachment_digest = attachment.attachment_digest

    if attachment.c2_request_digest != request_digest:
        raise ValueError("PLAN_ATTACHMENT_NOT_FOR_C2_REQUEST")
    if attachment.c2_storage_plan_digest != request.storage_plan_digest:
        raise ValueError("PLAN_ATTACHMENT_STORAGE_PLAN_DRIFT")
    if attempt.request_digest != request_digest:
        raise ValueError("C2_ATTEMPT_NOT_FOR_REQUEST")
    if c2_join.request_digest != request_digest or c2_join.attempt_receipt_digest != attempt_digest:
        raise ValueError("C2_JOIN_NOT_FOR_EXACT_ATTEMPT")

    common = dict(
        schema=SCHEMA,
        plan_parent_head=PLAN_PARENT_HEAD,
        observation_parent_head=OBSERVATION_PARENT_HEAD,
        plan_attachment_digest=attachment_digest,
        request_digest=request_digest,
        attempt_receipt_digest=attempt_digest,
        c2_join_logical_id=join_id,
        plan_to_request_bound=True,
        request_to_attempt_bound=True,
    )
    if witness is None:
        out = PlanOperationObservationJoin(
            disposition=HOLD,
            reason_code="EXACT_OPERATION_OBSERVATION_WITNESS_REQUIRED",
            operation_observation_digest=None,
            operation_id=None,
            owner_host_observation_id=None,
            physical_read_bytes=None,
            attempt_to_observation_bound=False,
            source_binding_revalidation_bound=False,
            observational_attribution_bound=False,
            **common,
        )
        out.validate_claim_ceiling()
        return out

    witness.validate()
    exact = (
        witness.request_digest == request_digest
        and witness.attempt_receipt_digest == attempt_digest
        and witness.c2_join_logical_id == join_id
        and witness.plan_attachment_digest == attachment_digest
        and witness.plan_source_binding_digest == attachment.source_binding_digest
        and witness.owner_host_observation_id == attempt.owner_host_observation_id
        and witness.runner_identity == attempt.runner_identity
        and witness.runner_generation == attempt.runner_generation
        and witness.source_snapshot_digest == attempt.source_snapshot_digest
        and witness.host_measurement_ref == attempt.host_measurement_ref
        and witness.lifecycle_measurement_ref == attempt.lifecycle_measurement_ref
        and witness.physical_read_bytes == attempt.physical_read_bytes
    )
    if not exact:
        raise ValueError("PLAN_ATTEMPT_OBSERVATION_IDENTITY_MISMATCH")

    out = PlanOperationObservationJoin(
        disposition=BOUND,
        reason_code="EXACT_PLAN_ATTEMPT_OPERATION_OBSERVATION_RELATION_BOUND",
        operation_observation_digest=witness.witness_digest,
        operation_id=witness.operation_id,
        owner_host_observation_id=witness.owner_host_observation_id,
        physical_read_bytes=witness.physical_read_bytes,
        attempt_to_observation_bound=True,
        source_binding_revalidation_bound=True,
        observational_attribution_bound=True,
        **common,
    )
    out.validate_claim_ceiling()
    return out


LAWS = (
    "PlanAttachment+ExactC2Attempt+OperationWitness=>ObservationalAttribution",
    "ObservationalAttribution!=CausalPlanBenefit",
    "ObservedPhysicalReadBytes!=BytesSaved",
    "SameAttempt!=CounterfactualBaseline",
    "PlanBenefitRequiresIndependentCounterfactualOrMatchedBaseline",
    "SourceBindingRevalidation!=ExecutionAuthority",
    "TinyFixtureObservationPattern!=GLM53PerformanceEvidence",
    "K27Coordinate!=PlanIdentity!=ObservationAuthority!=CausalAuthority",
)
