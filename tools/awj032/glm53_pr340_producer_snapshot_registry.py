"""Relying-party registry pin for the exact hosted PR340 producer snapshot.

The producer in PR416 serializes but cannot authenticate its own snapshot. This
module is the separate consumer-side pin created only after observing exact-head
hosted run 33339511610 / job 99332466601. It verifies both the compact snapshot
and a recomputed final source-bound report before downstream PR409 appraisal.
"""
from __future__ import annotations

from typing import Any, Mapping

from tools.awj032.glm53_pr340_producer_snapshot import (
    PR340ProducerSnapshot,
    final_source_bound_report_digest,
)

REGISTRY_SCHEMA = "PR340ProducerSnapshotRegistryV1"
PRODUCER_EXECUTION_HEAD = "a120b0be445990a95476f2286bb75036039da7bb"
PRODUCER_BASE_HEAD = "6c1d65fceb084ea3cbe8a59b7e28818155788504"
PRODUCER_RUN_ID = "33339511610"
PRODUCER_JOB_ID = "99332466601"
FINAL_REPORT_DIGEST = "d7ff1b34d091a92449d59c0cb561bc5a87724c67ab9bdb7504a5b38f5c3dfaa9"
CLASSIFICATION_STAGE_LOGICAL_ID = "d03c28d13e4c7c99f49d611c29c24bc9b509158c8a0b84883f584f0c09c43aaa"
SNAPSHOT_DIGEST = "e4f187dce49c3711d4c1a388107b190aed6ad5a99508d85c163238f4a8f1c851"
SOURCE_BUNDLE_ID = "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b"
MODEL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
BLOCKER_SET = ("GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED",)


class PR340ProducerRegistryError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def verify_registered_pr340_snapshot(
    snapshot: PR340ProducerSnapshot,
    report: Mapping[str, Any],
) -> PR340ProducerSnapshot:
    if not isinstance(snapshot, PR340ProducerSnapshot):
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_OBJECT_REQUIRED")
    if snapshot.producer_execution_head != PRODUCER_EXECUTION_HEAD:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_EXECUTION_HEAD_MISMATCH")
    if snapshot.producer_base_head != PRODUCER_BASE_HEAD:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_BASE_HEAD_MISMATCH")
    if snapshot.final_report_digest != FINAL_REPORT_DIGEST:
        raise PR340ProducerRegistryError("PR340_FINAL_REPORT_DIGEST_MISMATCH")
    if snapshot.classification_stage_logical_id != CLASSIFICATION_STAGE_LOGICAL_ID:
        raise PR340ProducerRegistryError("PR340_CLASSIFICATION_LOGICAL_ID_MISMATCH")
    if snapshot.snapshot_digest != SNAPSHOT_DIGEST:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_DIGEST_MISMATCH")
    if snapshot.source_bundle_id != SOURCE_BUNDLE_ID:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_SOURCE_BUNDLE_MISMATCH")
    if snapshot.model_revision != MODEL_REVISION or snapshot.index_sha256 != INDEX_SHA256:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_SOURCE_IDENTITY_MISMATCH")
    if snapshot.blocker_set != BLOCKER_SET:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_BLOCKER_SET_MISMATCH")
    if snapshot.source_binding_proven is not True:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_SOURCE_BINDING_REQUIRED")
    if snapshot.producer_snapshot_serialized is not True:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_SERIALIZATION_REQUIRED")
    if snapshot.producer_snapshot_verified_by_external_registry is not False:
        raise PR340ProducerRegistryError("PRODUCER_SELF_VERIFICATION_FORBIDDEN")
    if snapshot.g2_admitted or snapshot.runtime_execution_proven or snapshot.large_checkpoint_admitted or snapshot.authority:
        raise PR340ProducerRegistryError("PR340_SNAPSHOT_EFFECT_CEILING_WIDENED")

    if not isinstance(report, Mapping):
        raise PR340ProducerRegistryError("PR340_FINAL_REPORT_REQUIRED")
    recomputed = final_source_bound_report_digest(report)
    if recomputed != FINAL_REPORT_DIGEST or recomputed != snapshot.final_report_digest:
        raise PR340ProducerRegistryError("PR340_FINAL_REPORT_RECOMPUTE_MISMATCH")
    if report.get("logical_id") != CLASSIFICATION_STAGE_LOGICAL_ID:
        raise PR340ProducerRegistryError("PR340_REPORT_CLASSIFICATION_ID_MISMATCH")
    if tuple(report.get("blockers", ())) != BLOCKER_SET:
        raise PR340ProducerRegistryError("PR340_REPORT_BLOCKER_SET_MISMATCH")
    if report.get("source_bundle_id") != SOURCE_BUNDLE_ID or report.get("source_binding_proven") is not True:
        raise PR340ProducerRegistryError("PR340_REPORT_SOURCE_BINDING_MISMATCH")
    return snapshot
