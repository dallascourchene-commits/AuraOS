"""Bind one calibrated GLM-5.3 speculative transfer plan to an exact C2 request.

D0 / HS1 / NONPROMOTING.

This module is a stacked attachment to PR #582's owner-host C2 handoff. It does not
create or mutate a C2 request, execute a transfer, observe physical I/O, select native
execution experts, authenticate an owner-host producer, or admit G2.

Exactly two newer foreign semantic artifacts define the attachment boundary:
- PR #725 quarantines G1 physical I/O: caller-authored structure cannot mint physical
  byte truth; measurement remains delegated to backend/W4/owner-host evidence.
- PR #726 binds G2 calibration to the exact predictor and policy generations that
  emitted and evaluated the prediction.

A proof-plumbing scar on PR #726 established a further provenance distinction:
semantic source generation and verification generation are separate identities. The
sidecar therefore carries both without granting the verifier semantic sibling credit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest

SCHEMA = "AURA-GLM53-G2-C2-TRANSFER-PLAN-ATTACHMENT-v1"
PLAN_REF_SCHEMA = "AURA-GLM53-CALIBRATED-TRANSFER-PLAN-REF-v1"

G1_PHYSICAL_QUARANTINE_HEAD = "de33bd7d5d1bdc3e8374e42dd5ec533c6536b3de"
G1_PHYSICAL_QUARANTINE_BLOB = "dcf54745dc4e938ad55a9874df7b289ef5fab92d"
G2_PREDICTOR_CALIBRATION_HEAD = "0aa762e11d9de31378658b6a40cdf0205209d3ac"
G2_PREDICTOR_CALIBRATION_BLOB = "9ecba5cd71a2fe6096e9fde08a139a5feace3f53"
G2_PREDICTOR_CALIBRATION_TEST_BLOB = "c084d71182519d49463072fd3d3a1da155e3ce05"
G2_PREDICTOR_CALIBRATION_VERIFICATION_HEAD = "543391fd79d150a33fda972817a179ae6ce4f1f5"
C2_OWNER_HEAD = "aed91d3dc1d6bafdf51bd977fcb5b42d196e2d07"
C2_OWNER_BLOB = "91da9f6f5c9c8175fbe123634e53e14bc9ba3cbe"

PHYSICAL_IO_UNKNOWN = "UNKNOWN_UNTIL_OWNER_HOST_ATTEMPT"
ATTACHED = "CALIBRATED_TRANSFER_PLAN_ATTACHED"
ATTACHED_NOOP = "CALIBRATED_TRANSFER_PLAN_ATTACHED_NOOP"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _sha256(value: Any, code: str) -> str:
    value = _text(value, code)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(code)
    return value


def _canonical_experts(values: tuple[int, ...]) -> tuple[int, ...]:
    if not isinstance(values, tuple):
        raise ValueError("ATTACHED_EXPERTS_MUST_BE_TUPLE")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values):
        raise ValueError("ATTACHED_EXPERT_ID_INVALID")
    canonical = tuple(sorted(set(values)))
    if canonical != values:
        raise ValueError("ATTACHED_EXPERTS_MUST_BE_SORTED_UNIQUE")
    return canonical


@dataclass(frozen=True)
class CalibratedTransferPlanRef:
    """Portable reference to an already-derived calibrated G2 planning receipt.

    The reference carries identities and the permanent non-effect ceiling. Semantic
    source identity and proof/reverification identity are deliberately separate.
    """

    g2_receipt_digest: str
    prediction_digest: str
    predictor_generation: str
    calibration_generation: str
    policy_generation: str
    layer_id: str
    source_binding_digest: str
    admitted_experts: tuple[int, ...]
    admitted_logical_bytes: int
    physical_io_attested: bool = False
    physical_prefetch_bytes: int | None = None
    transfer_effect_authorized: bool = False
    g2_admitted: bool = False
    semantic_k27_authority_minted: bool = False
    g1_physical_quarantine_head: str = G1_PHYSICAL_QUARANTINE_HEAD
    g1_physical_quarantine_blob: str = G1_PHYSICAL_QUARANTINE_BLOB
    g2_predictor_calibration_head: str = G2_PREDICTOR_CALIBRATION_HEAD
    g2_predictor_calibration_blob: str = G2_PREDICTOR_CALIBRATION_BLOB
    g2_predictor_calibration_test_blob: str = G2_PREDICTOR_CALIBRATION_TEST_BLOB
    g2_predictor_calibration_verification_head: str = G2_PREDICTOR_CALIBRATION_VERIFICATION_HEAD
    schema: str = PLAN_REF_SCHEMA

    def validate(self) -> None:
        if self.schema != PLAN_REF_SCHEMA:
            raise ValueError("TRANSFER_PLAN_REF_SCHEMA_MISMATCH")
        for value, code in (
            (self.g2_receipt_digest, "G2_RECEIPT_DIGEST_INVALID"),
            (self.prediction_digest, "PREDICTION_DIGEST_INVALID"),
        ):
            _sha256(value, code)
        for value, code in (
            (self.predictor_generation, "PREDICTOR_GENERATION_REQUIRED"),
            (self.calibration_generation, "CALIBRATION_GENERATION_REQUIRED"),
            (self.policy_generation, "POLICY_GENERATION_REQUIRED"),
            (self.layer_id, "LAYER_ID_REQUIRED"),
            (self.source_binding_digest, "SOURCE_BINDING_DIGEST_REQUIRED"),
        ):
            _text(value, code)
        if self.g1_physical_quarantine_head != G1_PHYSICAL_QUARANTINE_HEAD:
            raise ValueError("G1_PHYSICAL_QUARANTINE_HEAD_MISMATCH")
        if self.g1_physical_quarantine_blob != G1_PHYSICAL_QUARANTINE_BLOB:
            raise ValueError("G1_PHYSICAL_QUARANTINE_BLOB_MISMATCH")
        if self.g2_predictor_calibration_head != G2_PREDICTOR_CALIBRATION_HEAD:
            raise ValueError("G2_PREDICTOR_CALIBRATION_HEAD_MISMATCH")
        if self.g2_predictor_calibration_blob != G2_PREDICTOR_CALIBRATION_BLOB:
            raise ValueError("G2_PREDICTOR_CALIBRATION_BLOB_MISMATCH")
        if self.g2_predictor_calibration_test_blob != G2_PREDICTOR_CALIBRATION_TEST_BLOB:
            raise ValueError("G2_PREDICTOR_CALIBRATION_TEST_BLOB_MISMATCH")
        if self.g2_predictor_calibration_verification_head != G2_PREDICTOR_CALIBRATION_VERIFICATION_HEAD:
            raise ValueError("G2_PREDICTOR_CALIBRATION_VERIFICATION_HEAD_MISMATCH")
        _canonical_experts(self.admitted_experts)
        if isinstance(self.admitted_logical_bytes, bool) or not isinstance(self.admitted_logical_bytes, int):
            raise ValueError("ADMITTED_LOGICAL_BYTES_MUST_BE_INT")
        if self.admitted_logical_bytes < 0:
            raise ValueError("ADMITTED_LOGICAL_BYTES_MUST_BE_NONNEGATIVE")
        if self.admitted_experts and self.admitted_logical_bytes <= 0:
            raise ValueError("NONEMPTY_TRANSFER_PLAN_REQUIRES_POSITIVE_LOGICAL_BYTES")
        if not self.admitted_experts and self.admitted_logical_bytes != 0:
            raise ValueError("EMPTY_TRANSFER_PLAN_REQUIRES_ZERO_LOGICAL_BYTES")
        if self.physical_io_attested is not False or self.physical_prefetch_bytes is not None:
            raise ValueError("TRANSFER_PLAN_REF_CANNOT_CARRY_PHYSICAL_IO_TRUTH")
        if self.transfer_effect_authorized or self.g2_admitted or self.semantic_k27_authority_minted:
            raise ValueError("TRANSFER_PLAN_REF_CANNOT_WIDEN_AUTHORITY")

    @property
    def ref_digest(self) -> str:
        self.validate()
        return _digest({"domain": PLAN_REF_SCHEMA, "plan_ref": asdict(self)})


@dataclass(frozen=True)
class G2C2TransferPlanAttachment:
    schema: str
    c2_owner_head: str
    c2_owner_blob: str
    c2_request_digest: str
    c2_storage_plan_digest: str
    c2_model_revision: str
    transfer_plan_ref_digest: str
    source_binding_digest: str
    admitted_experts: tuple[int, ...]
    admitted_logical_bytes: int
    disposition: str
    physical_io_state: str
    source_binding_revalidation_required: bool
    c2_source_binding_equivalence_proven: bool
    owner_host_measurement_required: bool
    native_route_remains_authoritative: bool
    c2_request_mutated: bool
    physical_io_proven: bool
    execution_authorized: bool
    transfer_effect_authorized: bool
    g2_admitted: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_deploy_spend_public_financial_human_effect: bool

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("G2_C2_ATTACHMENT_SCHEMA_MISMATCH")
        if self.c2_owner_head != C2_OWNER_HEAD or self.c2_owner_blob != C2_OWNER_BLOB:
            raise ValueError("G2_C2_ATTACHMENT_C2_OWNER_MISMATCH")
        _sha256(self.c2_request_digest, "G2_C2_ATTACHMENT_REQUEST_DIGEST_INVALID")
        _sha256(self.c2_storage_plan_digest, "G2_C2_ATTACHMENT_STORAGE_PLAN_DIGEST_INVALID")
        _sha256(self.transfer_plan_ref_digest, "G2_C2_ATTACHMENT_PLAN_REF_DIGEST_INVALID")
        _text(self.c2_model_revision, "G2_C2_ATTACHMENT_MODEL_REVISION_REQUIRED")
        _text(self.source_binding_digest, "G2_C2_ATTACHMENT_SOURCE_BINDING_REQUIRED")
        _canonical_experts(self.admitted_experts)
        if self.disposition not in {ATTACHED, ATTACHED_NOOP}:
            raise ValueError("G2_C2_ATTACHMENT_DISPOSITION_INVALID")
        if self.physical_io_state != PHYSICAL_IO_UNKNOWN:
            raise ValueError("G2_C2_ATTACHMENT_PHYSICAL_IO_MUST_REMAIN_UNKNOWN")
        required_true = (
            self.source_binding_revalidation_required,
            self.owner_host_measurement_required,
            self.native_route_remains_authoritative,
        )
        if any(value is not True for value in required_true):
            raise ValueError("G2_C2_ATTACHMENT_REQUIRED_BOUNDARY_MISSING")
        forbidden = (
            self.c2_source_binding_equivalence_proven,
            self.c2_request_mutated,
            self.physical_io_proven,
            self.execution_authorized,
            self.transfer_effect_authorized,
            self.g2_admitted,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("G2_C2_ATTACHMENT_CANNOT_WIDEN_AUTHORITY_OR_EVIDENCE")
        if self.admitted_experts and self.admitted_logical_bytes <= 0:
            raise ValueError("G2_C2_ATTACHMENT_NONEMPTY_PLAN_REQUIRES_BYTES")
        if not self.admitted_experts and self.admitted_logical_bytes != 0:
            raise ValueError("G2_C2_ATTACHMENT_NOOP_REQUIRES_ZERO_BYTES")

    @property
    def attachment_digest(self) -> str:
        self.validate_claim_ceiling()
        return _digest({"domain": SCHEMA, "attachment": asdict(self)})


def attach_calibrated_g2_plan_to_c2_request(
    *,
    request: OwnerHostC2CanaryRequest,
    plan_ref: CalibratedTransferPlanRef,
) -> G2C2TransferPlanAttachment:
    """Attach a non-effect calibrated plan to one exact immutable C2 request.

    The relation intentionally does *not* infer that the G1 pager source-binding digest
    is equivalent to the C2 model/source snapshot. That remains a pre-effect owner-host
    revalidation obligation because PR #582 does not carry the G1 binding identity.
    """
    if not isinstance(request, OwnerHostC2CanaryRequest):
        raise ValueError("OWNER_HOST_C2_REQUEST_REQUIRED")
    if not isinstance(plan_ref, CalibratedTransferPlanRef):
        raise ValueError("CALIBRATED_TRANSFER_PLAN_REF_REQUIRED")
    plan_ref.validate()

    request_digest_before = request.request_digest
    if request.execution_authorized_by_this_contract is not False or request.g2_admitted is not False:
        raise ValueError("C2_REQUEST_AUTHORITY_CEILING_REQUIRED")

    attachment = G2C2TransferPlanAttachment(
        schema=SCHEMA,
        c2_owner_head=C2_OWNER_HEAD,
        c2_owner_blob=C2_OWNER_BLOB,
        c2_request_digest=request_digest_before,
        c2_storage_plan_digest=request.storage_plan_digest,
        c2_model_revision=request.model_revision,
        transfer_plan_ref_digest=plan_ref.ref_digest,
        source_binding_digest=plan_ref.source_binding_digest,
        admitted_experts=plan_ref.admitted_experts,
        admitted_logical_bytes=plan_ref.admitted_logical_bytes,
        disposition=ATTACHED if plan_ref.admitted_experts else ATTACHED_NOOP,
        physical_io_state=PHYSICAL_IO_UNKNOWN,
        source_binding_revalidation_required=True,
        c2_source_binding_equivalence_proven=False,
        owner_host_measurement_required=True,
        native_route_remains_authoritative=True,
        c2_request_mutated=False,
        physical_io_proven=False,
        execution_authorized=False,
        transfer_effect_authorized=False,
        g2_admitted=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_deploy_spend_public_financial_human_effect=False,
    )
    if request.request_digest != request_digest_before:
        raise ValueError("C2_REQUEST_MUTATED_DURING_ATTACHMENT")
    attachment.validate_claim_ceiling()
    return attachment


LAWS = (
    "G2PlanEligibility!=C2TransferAuthority",
    "C2TransferPlanAttachment!=C2RequestMutation",
    "PredictorCalibrationBindingMustCommuteBeforeAttachment",
    "SemanticGeneration!=VerificationGeneration",
    "ReproofSuccess!=NewSemanticConsequence",
    "PhysicalIOMustRemainUnknownBeforeOwnerHostAttempt",
    "G1PhysicalIOQuarantine+C2OwnerHostReceipt=>MeasurementPlaneRemainsDownstream",
    "AttachedExpertSet!=NativeExecutionRoute",
    "LogicalPlanBytes!=PhysicalReadBytes",
    "C2StoragePlanDigest!=G2PlanReceiptDigest",
    "SourceBindingCarried!=C2SourceEquivalenceProof",
    "K27Coordinate!=PlanIdentity!=MeasurementAuthority!=ExecutionAuthority",
)
