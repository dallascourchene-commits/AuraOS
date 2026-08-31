"""Canonical-owner W3 composition for AWJ032 GLM-5.3.

D0/nonpromoting. The canonical public boundary accepts the lower pager plan plus
current security/metadata evidence and invokes PR410's producer-consuming W3
admission itself. A caller-supplied serialized PR410 receipt is not accepted as
consequence authority. The MTP provenance owner remains a code-owned receipt pinned
from the independently observed PR421 exact hosted generation.

Success grants only eligibility for the deterministic native synthetic W3 fixture.
It does not grant official tensor compatibility, numerical W3 proof, model/runtime
execution, provider effect, quality, G2, deployment, or authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

from tools.awj032.glm53_official_w2_observation import OFFICIAL_W2_OBSERVATION
from tools.awj032.glm53_w3_official_producer_admission import (
    CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD,
    CURRENT_GLM53_METADATA_SEMANTIC_HEAD,
    evaluate_w3_official_producer_admission,
)

SCHEMA = "AWJ032GLM53W3CanonicalOwnerCompositeV1"
W3_SCHEMA = "AWJ032GLM53W3OfficialProducerAdmissionV1"
PROVENANCE_BLOCKER = "GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"

PR410_CURRENT_HEAD = "6ee14323a83d53a446dfc5c567d05534bf671010"
PR410_VERIFIED_SEMANTIC_HEAD = "837fbafa9c8343eb5d23904a4edeb71b38f576d3"
PR410_VERIFIED_RUN_ID = 33338915148
PR410_VERIFIED_JOB_ID = 99330806528

PR421_SEMANTIC_HEAD = "11afbd64db600e8839c8d18d72dd0320d074a0ac"
PR421_OBSERVATION_HEAD = "85813c6a9218e77d1a5e92ba2b82d27f08a65ea4"
PR421_RUN_ID = 33340370095
PR421_JOB_ID = 99334783653
PR421_OUTPUT_PIN_REF = "drive:14Q8kBD76D_OvmdxT1CVx52kbIrMlec-Xk1iPImOF5Ks"
PR421_REPORT_LOGICAL_ID = "bdcda54659157ed8249d258e3db20e1141b25ffb51d1e6d593e3c8a788b1eb23"

PR340_REGISTRY_PIN_DIGEST = "2b162e1598d3fa2d086f207318d338178e9645e55891f4f5de6bf211a8dd93da"
PR340_REGISTRY_RECEIPT_REF = "drive:1Tb7F-vu_Rb8bImIQXscword8tRRpt_DawtJV9dMnKEw"
PR340_FINAL_REPORT_DIGEST = "d7ff1b34d091a92449d59c0cb561bc5a87724c67ab9bdb7504a5b38f5c3dfaa9"
PR340_SNAPSHOT_DIGEST = "e4f187dce49c3711d4c1a388107b190aed6ad5a99508d85c163238f4a8f1c851"
PR340_CLASSIFICATION_LOGICAL_ID = "d03c28d13e4c7c99f49d611c29c24bc9b509158c8a0b84883f584f0c09c43aaa"
PR340_PRODUCER_BASE_HEAD = "6c1d65fceb084ea3cbe8a59b7e28818155788504"
PR340_PRODUCER_EXECUTION_HEAD = "a120b0be445990a95476f2286bb75036039da7bb"

OFFICIAL_MODEL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_SOURCE_BUNDLE_ID = "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b"
OFFICIAL_CONFIG_PARSED_SHA256 = "d497aba98135da3586209ba863e8e42eccf77a014811d0d3df812db9909c5d40"
OFFICIAL_INDEX_PARSED_SHA256 = "08f826679200e2dc91d5e9c5514bab239369122a8d0ef81df9c8accd55d4797c"
OFFICIAL_WEIGHT_MAP_DIGEST = "f201f9a19849fab7d0cb4ce928294aa4536b03fed527ce3bf4b3be2962fbc6a7"
OFFICIAL_MTP_SOURCE_EVIDENCE_ID = "b0803af6fdb7afd0dcdbf7c5b718605658a02534c960d965cfc1729eb4d9d3a2"


class CanonicalOwnerCompositeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _as_mapping(value: Any, code: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, Mapping):
            return dict(raw)
    raise CanonicalOwnerCompositeError(code)


def _exact_false(value: Any, code: str) -> None:
    if type(value) is not bool or value is not False:
        raise CanonicalOwnerCompositeError(code)


@dataclass(frozen=True)
class PR421CanonicalOwnerReceipt:
    semantic_head: str = PR421_SEMANTIC_HEAD
    observation_head: str = PR421_OBSERVATION_HEAD
    run_id: int = PR421_RUN_ID
    job_id: int = PR421_JOB_ID
    report_logical_id: str = PR421_REPORT_LOGICAL_ID
    output_pin_ref: str = PR421_OUTPUT_PIN_REF
    status: str = "READY_FOR_HEADER_AND_TINY_FIXTURE"
    blockers: tuple[str, ...] = ()
    pr340_registry_pin_digest: str = PR340_REGISTRY_PIN_DIGEST
    pr340_registry_receipt_ref: str = PR340_REGISTRY_RECEIPT_REF
    pr340_final_report_digest: str = PR340_FINAL_REPORT_DIGEST
    pr340_snapshot_digest: str = PR340_SNAPSHOT_DIGEST
    pr340_classification_logical_id: str = PR340_CLASSIFICATION_LOGICAL_ID
    pr340_producer_base_head: str = PR340_PRODUCER_BASE_HEAD
    pr340_producer_execution_head: str = PR340_PRODUCER_EXECUTION_HEAD
    official_model_revision: str = OFFICIAL_MODEL_REVISION
    official_index_sha256: str = OFFICIAL_INDEX_SHA256
    official_source_bundle_id: str = OFFICIAL_SOURCE_BUNDLE_ID
    official_config_parsed_sha256: str = OFFICIAL_CONFIG_PARSED_SHA256
    official_index_parsed_sha256: str = OFFICIAL_INDEX_PARSED_SHA256
    official_weight_map_digest: str = OFFICIAL_WEIGHT_MAP_DIGEST
    official_mtp_source_evidence_id: str = OFFICIAL_MTP_SOURCE_EVIDENCE_ID
    source_binding_proven: bool = True
    mtp_resolver_provenance_proven: bool = True
    pr340_producer_logical_id_verified: bool = True
    pr340_final_report_registry_proven: bool = True
    g2_admitted: bool = False
    large_checkpoint_admitted: bool = False
    runtime_execution_proven: bool = False
    authority: bool = False

    @property
    def receipt_digest(self) -> str:
        return _digest(asdict(self))


CANONICAL_PR421_OWNER_RECEIPT = PR421CanonicalOwnerReceipt()


def _validate_owner_receipt() -> PR421CanonicalOwnerReceipt:
    owner = CANONICAL_PR421_OWNER_RECEIPT
    if not isinstance(owner, PR421CanonicalOwnerReceipt):
        raise CanonicalOwnerCompositeError("PR421_CANONICAL_OWNER_RECEIPT_REQUIRED")
    expected = PR421CanonicalOwnerReceipt()
    if owner != expected:
        raise CanonicalOwnerCompositeError("PR421_CANONICAL_OWNER_RECEIPT_MISMATCH")
    if owner.status != "READY_FOR_HEADER_AND_TINY_FIXTURE" or owner.blockers != ():
        raise CanonicalOwnerCompositeError("PR421_OWNER_NOT_READY")
    for value, code in (
        (owner.source_binding_proven, "PR421_SOURCE_BINDING_REQUIRED"),
        (owner.mtp_resolver_provenance_proven, "PR421_MTP_PROVENANCE_REQUIRED"),
        (owner.pr340_producer_logical_id_verified, "PR421_PR340_PRODUCER_VERIFICATION_REQUIRED"),
        (owner.pr340_final_report_registry_proven, "PR421_PR340_REGISTRY_PROOF_REQUIRED"),
    ):
        if type(value) is not bool or value is not True:
            raise CanonicalOwnerCompositeError(code)
    for value, code in (
        (owner.g2_admitted, "PR421_G2_WIDENING_FORBIDDEN"),
        (owner.large_checkpoint_admitted, "PR421_CHECKPOINT_WIDENING_FORBIDDEN"),
        (owner.runtime_execution_proven, "PR421_RUNTIME_WIDENING_FORBIDDEN"),
        (owner.authority, "PR421_AUTHORITY_WIDENING_FORBIDDEN"),
    ):
        _exact_false(value, code)
    return owner


def _validate_w3_receipt(value: Any) -> dict[str, Any]:
    """Validate the receipt emitted by the immediately preceding live PR410 call.

    This helper is deliberately private. It exists for adversarial tests and for
    the canonical public wrapper below; callers cannot use a serialized receipt
    as the public consequence-bearing input.
    """
    receipt = _as_mapping(value, "PR410_W3_RECEIPT_REQUIRED")
    if receipt.get("schema") != W3_SCHEMA:
        raise CanonicalOwnerCompositeError("PR410_W3_RECEIPT_SCHEMA_MISMATCH")
    if receipt.get("status") != "BLOCKED":
        raise CanonicalOwnerCompositeError("PR410_PRECOMPOSITION_BLOCKED_REQUIRED")
    blockers = receipt.get("blockers")
    if blockers not in ([PROVENANCE_BLOCKER], (PROVENANCE_BLOCKER,)):
        raise CanonicalOwnerCompositeError("PR410_W3_BLOCKER_SET_NOT_COMPOSABLE")
    if receipt.get("official_w2_producer_proof_consumed") is not True:
        raise CanonicalOwnerCompositeError("PR410_W2_PRODUCER_PROOF_REQUIRED")
    for field in (
        "synthetic_tiny_fixture_admitted",
        "g2_admitted",
        "runtime_execution_admitted",
        "checkpoint_payload_admitted",
        "provider_effect_admitted",
        "authority",
    ):
        _exact_false(receipt.get(field), f"PR410_EFFECT_CEILING_WIDENED:{field}")

    o = OFFICIAL_W2_OBSERVATION
    expected = {
        "official_w2_observation_digest": o.observation_digest,
        "official_w2_receipt_digest": o.receipt_digest,
        "official_w2_producer_semantic_head": o.producer_semantic_head,
        "official_w2_producer_run_ref": o.producer_run_ref,
        "official_w2_drive_observation_ref": o.drive_observation_ref,
        "representative_layer": o.layer,
        "representative_expert": o.expert,
        "airllm_security_semantic_head": CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD,
        "glm53_metadata_semantic_head": CURRENT_GLM53_METADATA_SEMANTIC_HEAD,
    }
    for key, expected_value in expected.items():
        if receipt.get(key) != expected_value:
            raise CanonicalOwnerCompositeError("PR410_RECEIPT_GENERATION_MISMATCH", key)
    for field in ("official_w2_bound_plan_digest", "inner_source_plan_digest"):
        value = receipt.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise CanonicalOwnerCompositeError("PR410_RECEIPT_DIGEST_REQUIRED", field)
    return receipt


@dataclass(frozen=True)
class W3CanonicalOwnerCompositeReceipt:
    status: str
    blockers: tuple[str, ...]
    pr410_input_receipt_digest: str
    pr421_owner_receipt_digest: str
    pr410_current_head: str = PR410_CURRENT_HEAD
    pr410_verified_semantic_head: str = PR410_VERIFIED_SEMANTIC_HEAD
    pr410_verified_run_id: int = PR410_VERIFIED_RUN_ID
    pr410_verified_job_id: int = PR410_VERIFIED_JOB_ID
    pr421_semantic_head: str = PR421_SEMANTIC_HEAD
    pr421_observation_head: str = PR421_OBSERVATION_HEAD
    pr421_run_id: int = PR421_RUN_ID
    pr421_job_id: int = PR421_JOB_ID
    pr421_report_logical_id: str = PR421_REPORT_LOGICAL_ID
    official_w2_producer_proof_consumed: bool = True
    registry_bound_mtp_owner_consumed: bool = True
    native_synthetic_w3_eligible: bool = True
    native_synthetic_w3_numerical_proven: bool = False
    official_tensor_payload_admitted: bool = False
    runtime_execution_admitted: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    provider_effect_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "blockers": list(self.blockers)}

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def _compose_verified_pr410_receipt(w3_receipt: Any) -> W3CanonicalOwnerCompositeReceipt:
    """Private reduction after the canonical wrapper has executed PR410."""
    w3 = _validate_w3_receipt(w3_receipt)
    owner = _validate_owner_receipt()
    return W3CanonicalOwnerCompositeReceipt(
        status="ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE",
        blockers=(),
        pr410_input_receipt_digest=_digest(w3),
        pr421_owner_receipt_digest=owner.receipt_digest,
    )


def compose_canonical_w3_admission(
    *,
    pager_plan: Any,
    airllm_security_evidence: Mapping[str, Any],
    glm53_metadata_evidence: Mapping[str, Any],
) -> W3CanonicalOwnerCompositeReceipt:
    """Traverse PR410 live, then join its result with the pinned PR421 owner.

    The caller cannot supply a PR410 receipt. PR410 itself must consume the lower
    pager plan through its official-W2 producer binder at this consequence
    boundary before the canonical-owner reduction may run.
    """
    w3_receipt = evaluate_w3_official_producer_admission(
        pager_plan=pager_plan,
        airllm_security_evidence=airllm_security_evidence,
        glm53_metadata_evidence=glm53_metadata_evidence,
    )
    return _compose_verified_pr410_receipt(w3_receipt)
