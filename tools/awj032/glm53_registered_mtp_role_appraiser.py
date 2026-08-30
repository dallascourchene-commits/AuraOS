"""Registry-bound relying-party admission for the GLM-5.3 PR340 -> PR409 seam.

The legacy PR409 source appraiser can verify an independently supplied expected
classification-stage producer ID. That helper remains useful as a pure validator,
but a caller-supplied expectation is not a trust root. This module is the canonical
relying-party surface: its PR340 producer coordinate is code-owned and was pinned
from an independently observed exact PR416 hosted producer run.

D0 metadata/source provenance only. No tensor payload, model import, inference,
provider effect, G2, deployment, or authority widening is admitted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

from tools.awj032 import glm53_official_mtp_role_source_appraiser as appraiser
from tools.awj032.glm53_pr340_producer_snapshot import final_source_bound_report_digest

REGISTRY_SCHEMA = "PR340ProducerRegistryPinV1"
REGISTRY_RECEIPT_REF = "drive:1Tb7F-vu_Rb8bImIQXscword8tRRpt_DawtJV9dMnKEw"
PINNED_FINAL_REPORT_DIGEST = "d7ff1b34d091a92449d59c0cb561bc5a87724c67ab9bdb7504a5b38f5c3dfaa9"
PINNED_SNAPSHOT_DIGEST = "e4f187dce49c3711d4c1a388107b190aed6ad5a99508d85c163238f4a8f1c851"
PINNED_CLASSIFICATION_STAGE_LOGICAL_ID = "d03c28d13e4c7c99f49d611c29c24bc9b509158c8a0b84883f584f0c09c43aaa"
PINNED_PRODUCER_BASE_HEAD = "6c1d65fceb084ea3cbe8a59b7e28818155788504"
PINNED_PRODUCER_EXECUTION_HEAD = "a120b0be445990a95476f2286bb75036039da7bb"
PINNED_RUN_ID = 33339511610
PINNED_JOB_ID = 99332466601
PINNED_MODEL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
PINNED_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
PINNED_SOURCE_BUNDLE_ID = "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b"
PINNED_CONFIG_PARSED_SHA256 = "d497aba98135da3586209ba863e8e42eccf77a014811d0d3df812db9909c5d40"
PINNED_INDEX_PARSED_SHA256 = "08f826679200e2dc91d5e9c5514bab239369122a8d0ef81df9c8accd55d4797c"
PINNED_WEIGHT_MAP_DIGEST = "f201f9a19849fab7d0cb4ce928294aa4536b03fed527ce3bf4b3be2962fbc6a7"
PINNED_BLOCKER_SET = (appraiser.PROVENANCE_BLOCKER,)
CLAIM_CEILING = "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT"


class RegistryBoundMTPRoleError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class PR340ProducerRegistryPin:
    final_report_digest: str = PINNED_FINAL_REPORT_DIGEST
    snapshot_digest: str = PINNED_SNAPSHOT_DIGEST
    classification_stage_logical_id: str = PINNED_CLASSIFICATION_STAGE_LOGICAL_ID
    producer_base_head: str = PINNED_PRODUCER_BASE_HEAD
    producer_execution_head: str = PINNED_PRODUCER_EXECUTION_HEAD
    run_id: int = PINNED_RUN_ID
    job_id: int = PINNED_JOB_ID
    model_revision: str = PINNED_MODEL_REVISION
    index_sha256: str = PINNED_INDEX_SHA256
    source_bundle_id: str = PINNED_SOURCE_BUNDLE_ID
    config_parsed_sha256: str = PINNED_CONFIG_PARSED_SHA256
    index_parsed_sha256: str = PINNED_INDEX_PARSED_SHA256
    weight_map_digest: str = PINNED_WEIGHT_MAP_DIGEST
    blocker_set: tuple[str, ...] = PINNED_BLOCKER_SET
    registry_receipt_ref: str = REGISTRY_RECEIPT_REF
    registry_current: bool = True
    authority: bool = False
    g2_admitted: bool = False
    runtime_execution_proven: bool = False
    schema: str = REGISTRY_SCHEMA

    @property
    def pin_digest(self) -> str:
        return _digest(asdict(self))


CANONICAL_PR340_PRODUCER_PIN = PR340ProducerRegistryPin()


def _pin() -> PR340ProducerRegistryPin:
    pin = CANONICAL_PR340_PRODUCER_PIN
    if not isinstance(pin, PR340ProducerRegistryPin) or pin.schema != REGISTRY_SCHEMA:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_PIN_REQUIRED")
    if pin.registry_current is not True:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_PIN_STALE")
    if pin.authority or pin.g2_admitted or pin.runtime_execution_proven:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_AUTHORITY_WIDENING_FORBIDDEN")
    if pin.producer_base_head != appraiser.PR340_PRODUCER_SEMANTIC_GENERATION:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_SEMANTIC_GENERATION_MISMATCH")
    return pin


def verify_registered_pr340_report(report: Mapping[str, Any]) -> str:
    """Verify one final PR340 report against the non-caller registry coordinate."""
    if not isinstance(report, Mapping):
        raise RegistryBoundMTPRoleError("PR340_REPORT_REQUIRED")
    pin = _pin()
    observed_final = final_source_bound_report_digest(report)
    if observed_final != pin.final_report_digest:
        raise RegistryBoundMTPRoleError(
            "PR340_REGISTRY_FINAL_REPORT_DIGEST_MISMATCH",
            f"expected={pin.final_report_digest},observed={observed_final}",
        )

    expected_fields = {
        "logical_id": pin.classification_stage_logical_id,
        "model_revision": pin.model_revision,
        "index_sha256": pin.index_sha256,
        "source_bundle_id": pin.source_bundle_id,
        "config_parsed_sha256": pin.config_parsed_sha256,
        "index_parsed_sha256": pin.index_parsed_sha256,
        "weight_map_digest": pin.weight_map_digest,
    }
    mismatches = [field for field, expected in expected_fields.items() if report.get(field) != expected]
    if mismatches:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_REPORT_FIELD_MISMATCH", ",".join(mismatches))
    if tuple(report.get("blockers", ())) != pin.blocker_set:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_BLOCKER_SET_MISMATCH")
    if report.get("source_binding_proven") is not True:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_SOURCE_BINDING_REQUIRED")
    if report.get("extra_layer_resolver_provenance_proven") is not False:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_PROVENANCE_PRESTATE_INVALID")
    if report.get("claim_ceiling") != CLAIM_CEILING:
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_CLAIM_CEILING_MISMATCH")
    if (
        report.get("g2_admitted") is not False
        or report.get("large_checkpoint_admitted") is not False
        or report.get("runtime_execution_proven") is not False
        or report.get("provider_calls") != 0
    ):
        raise RegistryBoundMTPRoleError("PR340_REGISTRY_EFFECT_CEILING_WIDENED")
    return observed_final


def _apply_registered_official_mtp_role(
    report: Mapping[str, Any],
    evidence: appraiser.OfficialSourceMTPRoleEvidence,
) -> dict[str, Any]:
    """Apply PR409 source-role proof only after the code-owned registry pin passes."""
    pin = _pin()
    observed_final = verify_registered_pr340_report(report)
    admitted = appraiser._apply_verified_source_role(
        report,
        evidence,
        expected_pr340_logical_id=pin.classification_stage_logical_id,
        expected_pr340_semantic_generation=pin.producer_base_head,
    )
    logical = {
        key: value
        for key, value in admitted.items()
        if key not in {"logical_id", "observation_time", "claim_ceiling"}
    }
    logical.update(
        {
            "pr340_final_report_registry_proven": True,
            "pr340_final_report_digest": observed_final,
            "pr340_registry_pin_digest": pin.pin_digest,
            "pr340_registry_receipt_ref": pin.registry_receipt_ref,
            "pr340_registry_producer_execution_head": pin.producer_execution_head,
            "pr340_registry_producer_snapshot_digest": pin.snapshot_digest,
            "pr340_registry_run_id": pin.run_id,
            "pr340_registry_job_id": pin.job_id,
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
        }
    )
    return {
        **logical,
        "logical_id": _digest(logical),
        "observation_time": admitted.get("observation_time"),
        "claim_ceiling": admitted.get("claim_ceiling", CLAIM_CEILING),
    }


def verify_and_admit_registered_official_mtp_role(
    report: Mapping[str, Any],
    *,
    read_full: Callable[[str, int], bytes] = appraiser.urllib_read_full,
) -> dict[str, Any]:
    """Canonical public relying-party entry point; callers supply no expected producer ID."""
    evidence = appraiser.observe_official_mtp_role(read_full=read_full)
    return _apply_registered_official_mtp_role(report, evidence)
