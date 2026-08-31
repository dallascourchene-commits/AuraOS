"""Structurally bind a calibrated GLM-5.3 C2 plan to an operation-witness claim.

D0 / HS1 / NONPROMOTING.

This relation consumes two independently proven lineages:
* PR #729: calibrated G2 planning -> immutable C2 request attachment.
* PR #727: operation/observer/backend provenance *pattern* for physical observations.

A caller-authored witness can prove deterministic relation consistency only. It cannot
authenticate its own producer, observer registry, source-revalidation producer, or
physical counters. Therefore this module never promotes a matching candidate witness
to physical-observation truth or observational attribution. Those require a later
external producer/observer-registry authentication receipt.

Even after authenticated observation exists, causal plan benefit still requires an
independently bound counterfactual or matched baseline.
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

SCHEMA = "AURA-GLM53-G2-C2-PLAN-OPERATION-WITNESS-STRUCTURAL-JOIN-v2"
WITNESS_SCHEMA = "AURA-GLM53-C2-OPERATION-OBSERVATION-WITNESS-CANDIDATE-v2"

PLAN_PARENT_HEAD = "5d7180f9a899b07526fd36cb290c85c8ebab4969"
PLAN_PARENT_BLOB = "c7be999691ef1a8c3e58c918c12574eab192c9e3"
OBSERVATION_PARENT_HEAD = "293c59d7260372ccd3b9e8130b12979b052c3ed9"
OBSERVATION_PARENT_BLOB = "98db548b6e8f7443b79d979eb0e177ac6aa68534"

STRUCTURAL = "PLAN_ATTEMPT_OBSERVATION_WITNESS_STRUCTURALLY_BOUND_AUTHENTICATION_REQUIRED"
HOLD = "HOLD_OPERATION_OBSERVATION_WITNESS_REQUIRED"
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
    """Caller-supplied candidate witness: structural claims, never provenance truth.

    Names ending in ``_claimed`` are deliberate. The caller may assert that an observer
    is current or that source binding was revalidated, but this module has no registry
    capable of authenticating those claims. The candidate can therefore participate in
    a deterministic structural join only.
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
    claimed_physical_read_bytes: int
    observer_current_claimed: bool = True
    exact_operation_bound_claimed: bool = True
    source_binding_revalidated_claimed: bool = True
    glm53_workload_claimed: bool = True
    tiny_fixture_crosscast: bool = False
    producer_authenticated: bool = False
    observer_registry_authenticated: bool = False
    physical_observation_proven: bool = False
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
        _nonnegative_int(self.claimed_physical_read_bytes, "WITNESS_CLAIMED_PHYSICAL_READ_BYTES_INVALID")
        if type(self.observer_current_claimed) is not bool or type(self.exact_operation_bound_claimed) is not bool:
            raise ValueError("WITNESS_BOOLEAN_CLAIMS_MUST_BE_BOOL")
        if type(self.source_binding_revalidated_claimed) is not bool or type(self.glm53_workload_claimed) is not bool:
            raise ValueError("WITNESS_BOOLEAN_CLAIMS_MUST_BE_BOOL")
        if self.tiny_fixture_crosscast is not False:
            raise ValueError("WITNESS_TINY_FIXTURE_CROSSCAST_FORBIDDEN")
        if any((
            self.producer_authenticated,
            self.observer_registry_authenticated,
            self.physical_observation_proven,
            self.execution_authority_granted,
            self.effect_authority_granted,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
        )):
            raise ValueError("CALLER_WITNESS_CANNOT_SELF_AUTHENTICATE_OR_WIDEN_AUTHORITY")

    @property
    def witness_digest(self) -> str:
        self.validate()
        return _digest({"domain": WITNESS_SCHEMA, "candidate_witness": asdict(self)})


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
    candidate_witness_digest: str | None
    operation_id_claim: str | None
    owner_host_observation_id_claim: str | None
    claimed_physical_read_bytes: int | None
    plan_to_request_bound: bool
    request_to_attempt_bound: bool
    attempt_to_candidate_witness_structurally_bound: bool
    source_binding_revalidation_claim_carried: bool
    producer_authentication_required: bool
    observer_registry_authentication_required: bool
    physical_observation_proven: bool = False
    observational_attribution_bound: bool = False
    source_binding_revalidation_proven: bool = False
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
        if self.producer_authentication_required is not True or self.observer_registry_authentication_required is not True:
            raise ValueError("EXTERNAL_PRODUCER_AND_OBSERVER_AUTHENTICATION_REMAIN_REQUIRED")
        if self.counterfactual_baseline_required is not True:
            raise ValueError("COUNTERFACTUAL_BASELINE_REQUIREMENT_CANNOT_BE_REMOVED")
        forbidden = (
            self.physical_observation_proven,
            self.observational_attribution_bound,
            self.source_binding_revalidation_proven,
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
            raise ValueError("STRUCTURAL_JOIN_CANNOT_MINT_OBSERVATION_CAUSALITY_OR_AUTHORITY")
        if self.disposition == STRUCTURAL:
            if not all((
                self.plan_to_request_bound,
                self.request_to_attempt_bound,
                self.attempt_to_candidate_witness_structurally_bound,
                self.source_binding_revalidation_claim_carried,
            )):
                raise ValueError("STRUCTURAL_JOIN_REQUIRES_COMPLETE_IDENTITY_RELATION")
            if self.candidate_witness_digest is None or self.operation_id_claim is None or self.owner_host_observation_id_claim is None:
                raise ValueError("STRUCTURAL_JOIN_REQUIRES_CANDIDATE_WITNESS_IDENTITY")
            _sha256(self.candidate_witness_digest, "STRUCTURAL_JOIN_WITNESS_DIGEST_INVALID")
            if self.claimed_physical_read_bytes is None:
                raise ValueError("STRUCTURAL_JOIN_REQUIRES_CLAIMED_BYTE_FIELD")
            _nonnegative_int(self.claimed_physical_read_bytes, "STRUCTURAL_JOIN_CLAIMED_BYTES_INVALID")
        elif self.disposition == HOLD:
            if self.attempt_to_candidate_witness_structurally_bound or self.source_binding_revalidation_claim_carried:
                raise ValueError("HELD_JOIN_CANNOT_CLAIM_WITNESS_BINDING")
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
    """Join exact identities structurally; never authenticate caller-supplied evidence."""
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
        producer_authentication_required=True,
        observer_registry_authentication_required=True,
    )
    if witness is None:
        out = PlanOperationObservationJoin(
            disposition=HOLD,
            reason_code="OPERATION_OBSERVATION_WITNESS_CANDIDATE_REQUIRED",
            candidate_witness_digest=None,
            operation_id_claim=None,
            owner_host_observation_id_claim=None,
            claimed_physical_read_bytes=None,
            attempt_to_candidate_witness_structurally_bound=False,
            source_binding_revalidation_claim_carried=False,
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
        and witness.claimed_physical_read_bytes == attempt.physical_read_bytes
    )
    if not exact:
        raise ValueError("PLAN_ATTEMPT_WITNESS_IDENTITY_MISMATCH")

    out = PlanOperationObservationJoin(
        disposition=STRUCTURAL,
        reason_code="EXACT_STRUCTURAL_WITNESS_RELATION_BOUND_EXTERNAL_AUTHENTICATION_REQUIRED",
        candidate_witness_digest=witness.witness_digest,
        operation_id_claim=witness.operation_id,
        owner_host_observation_id_claim=witness.owner_host_observation_id,
        claimed_physical_read_bytes=witness.claimed_physical_read_bytes,
        attempt_to_candidate_witness_structurally_bound=True,
        source_binding_revalidation_claim_carried=True,
        **common,
    )
    out.validate_claim_ceiling()
    return out


LAWS = (
    "PlanAttachment+ExactC2Attempt+CallerWitness=>StructuralRelationOnly",
    "StructuralWitnessRelation!=AuthenticatedObservationalAttribution",
    "CallerWitness!=BackendObservationProvenance",
    "UnauthenticatedC2Receipt+MatchingWitness!=PhysicalObservationTruth",
    "ProducerRegistryAuthenticationRequiredBeforeObservationalAttribution",
    "SourceRevalidationClaim!=AuthenticatedSourceRevalidation",
    "AuthenticatedObservationalAttribution!=CausalPlanBenefit",
    "ClaimedPhysicalReadBytes!=ObservedPhysicalReadBytes!=BytesSaved",
    "SameAttempt!=CounterfactualBaseline",
    "PlanBenefitRequiresIndependentCounterfactualOrMatchedBaseline",
    "TinyFixtureObservationPattern!=GLM53PerformanceEvidence",
    "K27Coordinate!=PlanIdentity!=ObservationAuthority!=CausalAuthority",
)
