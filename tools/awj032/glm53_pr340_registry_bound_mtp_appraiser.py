"""Registry-bound successor membrane for AWJ032 PR409 MTP-role admission.

D0 metadata/provenance only. This module removes caller control from the producer
expectation on the current W3 path by binding the exact independently observed
PR340ProducerSnapshotV1 generation recorded by the Arena registry receipt.

It deliberately reuses PR409's already-hosted immutable-source role appraiser.
The new responsibility here is narrower: prove that the incoming complete
source-bound PR340 report is the exact report pinned by an independent relying
party before PR409 may discharge its one provenance blocker.

No tensor payload, model import/inference, runtime-MTP support, G2, provider,
merge, deployment, or effect authority is granted by this membrane.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
import json
from typing import Any, Callable, Mapping

from tools.awj032 import glm53_official_mtp_role_source_appraiser as appraiser

SCHEMA = "PR340RegistryBoundMTPAdmissionV1"
REPORT_DIGEST_DOMAIN = "AURA/AWJ032/GLM53/PR340/FINAL_SOURCE_BOUND_REPORT/V1"
REGISTRY_RECEIPT_REF = "drive:1Tb7F-vu_Rb8bImIQXscword8tRRpt_DawtJV9dMnKEw"
PINNED_FINAL_REPORT_DIGEST = "d7ff1b34d091a92449d59c0cb561bc5a87724c67ab9bdb7504a5b38f5c3dfaa9"
PINNED_SNAPSHOT_DIGEST = "e4f187dce49c3711d4c1a388107b190aed6ad5a99508d85c163238f4a8f1c851"
PINNED_CLASSIFICATION_STAGE_LOGICAL_ID = "d03c28d13e4c7c99f49d611c29c24bc9b509158c8a0b84883f584f0c09c43aaa"
PINNED_PRODUCER_BASE_HEAD = "6c1d65fceb084ea3cbe8a59b7e28818155788504"
PINNED_PRODUCER_EXECUTION_HEAD = "a120b0be445990a95476f2286bb75036039da7bb"
PINNED_SOURCE_BUNDLE_ID = "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b"
PINNED_MODEL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
PINNED_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
PINNED_BLOCKER_SET = (appraiser.PROVENANCE_BLOCKER,)


class RegistryBoundMTPAdmissionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RegistryBoundMTPAdmissionError("NONCANONICAL_REPORT") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def final_source_bound_report_digest(report: Mapping[str, Any]) -> str:
    """Mirror PR416's exact final-report identity grammar.

    `observation_time` is volatile receipt metadata and the older classification
    `logical_id` is lineage. Every other final report field remains inside the
    independently pinned consequence identity.
    """
    if not isinstance(report, Mapping):
        raise RegistryBoundMTPAdmissionError("FINAL_REPORT_REQUIRED")
    payload = {
        key: value
        for key, value in report.items()
        if key not in {"observation_time", "logical_id"}
    }
    return _sha({"domain": REPORT_DIGEST_DOMAIN, "report": payload})


@dataclass(frozen=True)
class PR340RegistryVerificationReceipt:
    final_report_digest: str
    classification_stage_logical_id: str
    registry_receipt_ref: str = REGISTRY_RECEIPT_REF
    snapshot_digest: str = PINNED_SNAPSHOT_DIGEST
    producer_base_head: str = PINNED_PRODUCER_BASE_HEAD
    producer_execution_head: str = PINNED_PRODUCER_EXECUTION_HEAD
    source_bundle_id: str = PINNED_SOURCE_BUNDLE_ID
    model_revision: str = PINNED_MODEL_REVISION
    index_sha256: str = PINNED_INDEX_SHA256
    blocker_set: tuple[str, ...] = PINNED_BLOCKER_SET
    producer_registry_verified: bool = True
    runtime_execution_proven: bool = False
    g2_admitted: bool = False
    authority: bool = False
    schema: str = "PR340RegistryVerificationReceiptV1"


def verify_pr340_against_registry(report: Mapping[str, Any]) -> PR340RegistryVerificationReceipt:
    """Fail closed unless `report` is the exact independently pinned PR340 final report."""
    if not isinstance(report, Mapping):
        raise RegistryBoundMTPAdmissionError("FINAL_REPORT_REQUIRED")
    if report.get("schema") != "GLM53CheckpointLayoutProbeV1":
        raise RegistryBoundMTPAdmissionError("GLM53_LAYOUT_PROBE_REPORT_REQUIRED")

    reported_logical = report.get("logical_id")
    if reported_logical != PINNED_CLASSIFICATION_STAGE_LOGICAL_ID:
        raise RegistryBoundMTPAdmissionError(
            "PR340_REGISTRY_CLASSIFICATION_ID_MISMATCH",
            f"expected={PINNED_CLASSIFICATION_STAGE_LOGICAL_ID},observed={reported_logical}",
        )
    recomputed_logical = appraiser._pr340_classification_stage_logical_id(report)
    if recomputed_logical != reported_logical:
        raise RegistryBoundMTPAdmissionError(
            "PR340_CLASSIFICATION_ID_RECOMPUTE_MISMATCH",
            f"reported={reported_logical},recomputed={recomputed_logical}",
        )

    observed_final_digest = final_source_bound_report_digest(report)
    if observed_final_digest != PINNED_FINAL_REPORT_DIGEST:
        raise RegistryBoundMTPAdmissionError(
            "PR340_REGISTRY_FINAL_REPORT_DIGEST_MISMATCH",
            f"expected={PINNED_FINAL_REPORT_DIGEST},observed={observed_final_digest}",
        )

    if report.get("source_bundle_id") != PINNED_SOURCE_BUNDLE_ID:
        raise RegistryBoundMTPAdmissionError("PR340_REGISTRY_SOURCE_BUNDLE_MISMATCH")
    if report.get("model_revision") != PINNED_MODEL_REVISION:
        raise RegistryBoundMTPAdmissionError("PR340_REGISTRY_MODEL_REVISION_MISMATCH")
    if report.get("index_sha256") != PINNED_INDEX_SHA256:
        raise RegistryBoundMTPAdmissionError("PR340_REGISTRY_INDEX_SHA256_MISMATCH")
    blockers = report.get("blockers")
    if not isinstance(blockers, list) or tuple(blockers) != PINNED_BLOCKER_SET:
        raise RegistryBoundMTPAdmissionError("PR340_REGISTRY_BLOCKER_SET_MISMATCH")

    return PR340RegistryVerificationReceipt(
        final_report_digest=observed_final_digest,
        classification_stage_logical_id=recomputed_logical,
    )


def _with_registry_receipt(
    admitted: Mapping[str, Any],
    registry: PR340RegistryVerificationReceipt,
) -> dict[str, Any]:
    if not isinstance(admitted, Mapping):
        raise RegistryBoundMTPAdmissionError("ADMITTED_REPORT_REQUIRED")
    logical = {
        key: value
        for key, value in admitted.items()
        if key not in {"logical_id", "observation_time", "claim_ceiling"}
    }
    logical.update(
        {
            "pr340_producer_registry_verified": True,
            "pr340_producer_registry_receipt_ref": registry.registry_receipt_ref,
            "pr340_producer_final_report_digest": registry.final_report_digest,
            "pr340_producer_snapshot_digest": registry.snapshot_digest,
            "pr340_producer_execution_head": registry.producer_execution_head,
        }
    )
    return {
        **logical,
        "logical_id": appraiser._sha256_json(logical),
        "observation_time": admitted.get("observation_time"),
        "claim_ceiling": admitted.get(
            "claim_ceiling", "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT"
        ),
    }


def verify_and_admit_registry_bound_official_mtp_role(
    report: Mapping[str, Any],
    *,
    read_full: Callable[[str, int], bytes] = appraiser.urllib_read_full,
) -> dict[str, Any]:
    """Registry-bound current path with no caller-controlled producer expectation.

    The exact registry pin is checked first. PR409's hosted source-role appraiser is
    then reused with code-owned producer lineage solely as a compatibility input;
    callers cannot replace either expected value through this API.
    """
    registry = verify_pr340_against_registry(report)
    evidence = appraiser.observe_official_mtp_role(read_full=read_full)
    admitted = appraiser._apply_verified_source_role(
        report,
        evidence,
        expected_pr340_logical_id=PINNED_CLASSIFICATION_STAGE_LOGICAL_ID,
        expected_pr340_semantic_generation=PINNED_PRODUCER_BASE_HEAD,
    )
    out = _with_registry_receipt(admitted, registry)
    if (
        out.get("g2_admitted") is not False
        or out.get("large_checkpoint_admitted") is not False
        or out.get("runtime_execution_proven") is not False
    ):
        raise RegistryBoundMTPAdmissionError("EFFECT_CEILING_WIDENED")
    return out


def public_interface_has_caller_expected_identity() -> bool:
    """Machine-check the successor API does not accept caller expected-ID fields."""
    params = inspect.signature(verify_and_admit_registry_bound_official_mtp_role).parameters
    return any(name.startswith("expected_pr340") for name in params)
