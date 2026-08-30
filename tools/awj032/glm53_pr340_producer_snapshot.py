"""Canonical final source-bound producer snapshot for AWJ032 PR340.

D0 metadata-only. This module executes the real PR340 source-bound checkpoint probe
with a deterministic role-intent classification derived from the same immutable
config/index bytes, then hashes the *complete final source-bound report*. The
classification-stage ``logical_id`` is retained as lineage but is not treated as
identity for fields appended later by ``source_bound_probe``.

This module emits a candidate producer snapshot. It does not authenticate itself:
no canonical expected report digest lives here. A downstream relying party must pin
an independently observed exact-run snapshot before granting producer provenance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from tools.awj032.glm53_checkpoint_extra_layer_classification import (
    CheckpointExtraLayerClassification,
    CheckpointExtraLayerEvidenceObservation,
    RESOLVER_PROVENANCE_BLOCKER,
)
from tools.awj032.glm53_checkpoint_source_binding import (
    GLM53CheckpointSourceBundle,
    source_bound_probe,
)

SCHEMA = "PR340ProducerSnapshotV1"
REPORT_DIGEST_DOMAIN = "AURA/AWJ032/GLM53/PR340/FINAL_SOURCE_BOUND_REPORT/V1"
OFFICIAL_REPO = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_CONFIG_SHA256 = "3ac72612095574542f7fff847ada8e59d9199dd8af44bdf625d7e02615572e69"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_SOURCE_BUNDLE_ID = "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b"
CURRENT_AIRLLM_SECURITY_GENERATION = "e26f5228b2a7ad97aa8325593cf5550febce61ed"
PR340_PRODUCER_BASE_HEAD = "6c1d65fceb084ea3cbe8a59b7e28818155788504"
ROLE_INDEX = 78
ROLE = "MTP_NON_DECODER"
ROLE_EVIDENCE_REF = "awj032:pr340:official-source-role-intent-v1"
ROLE_RESOLVER_REF = "awj032:pr340:source-role-intent-builder-v1"
ROLE_RESOLUTION_RECEIPT_REF = "awj032:pr340:source-role-intent-receipt-v1"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class PR340ProducerSnapshotError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
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


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha40(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise PR340ProducerSnapshotError(code)
    out = value.strip().lower()
    if not _SHA40.fullmatch(out):
        raise PR340ProducerSnapshotError(code)
    return out


def _weight_map(sources: GLM53CheckpointSourceBundle) -> Mapping[str, str]:
    index = sources.index.mapping()
    value = index.get("weight_map")
    if not isinstance(value, Mapping) or not value:
        raise PR340ProducerSnapshotError("INDEX_WEIGHT_MAP_REQUIRED")
    return value


def _role_intent_digest(sources: GLM53CheckpointSourceBundle) -> str:
    return _sha(
        {
            "schema": "PR340OfficialSourceRoleIntentV1",
            "repo": OFFICIAL_REPO,
            "model_revision": sources.model_revision,
            "index_sha256": sources.index.raw_sha256,
            "source_bundle_id": sources.source_bundle_id,
            "num_hidden_layers": 78,
            "num_nextn_predict_layers": 1,
            "role_index": ROLE_INDEX,
            "role": ROLE,
            "marker_prefix": f"model.layers.{ROLE_INDEX}.eh_proj",
        }
    )


def build_canonical_role_intent(
    sources: GLM53CheckpointSourceBundle,
) -> tuple[CheckpointExtraLayerClassification, CheckpointExtraLayerEvidenceObservation]:
    if not isinstance(sources, GLM53CheckpointSourceBundle):
        raise PR340ProducerSnapshotError("SOURCE_BUNDLE_REQUIRED")
    if sources.model_revision != OFFICIAL_REVISION:
        raise PR340ProducerSnapshotError("MODEL_REVISION_MISMATCH")
    if sources.config.raw_sha256 != OFFICIAL_CONFIG_SHA256:
        raise PR340ProducerSnapshotError("CONFIG_SHA256_MISMATCH")
    if sources.index.raw_sha256 != OFFICIAL_INDEX_SHA256:
        raise PR340ProducerSnapshotError("INDEX_SHA256_MISMATCH")
    if sources.source_bundle_id != OFFICIAL_SOURCE_BUNDLE_ID:
        raise PR340ProducerSnapshotError("SOURCE_BUNDLE_ID_MISMATCH")

    config = sources.config.mapping()
    if config.get("num_hidden_layers") != 78 or config.get("num_nextn_predict_layers") != 1:
        raise PR340ProducerSnapshotError("OFFICIAL_MTP_CONFIG_MISMATCH")
    marker_prefix = f"model.layers.{ROLE_INDEX}.eh_proj"
    if not any(str(key).startswith(marker_prefix) for key in _weight_map(sources)):
        raise PR340ProducerSnapshotError("OFFICIAL_MTP_MARKER_REQUIRED")

    roles = ((ROLE_INDEX, ROLE),)
    evidence_digest = _role_intent_digest(sources)
    classification = CheckpointExtraLayerClassification(
        model_revision=sources.model_revision,
        index_sha256=sources.index.raw_sha256,
        num_hidden_layers=78,
        roles=roles,
        evidence_ref=ROLE_EVIDENCE_REF,
        evidence_digest=evidence_digest,
        evidence_generation=OFFICIAL_REVISION,
        resolver_ref=ROLE_RESOLVER_REF,
        resolver_generation=PR340_PRODUCER_BASE_HEAD,
    )
    observation = CheckpointExtraLayerEvidenceObservation(
        evidence_ref=classification.evidence_ref,
        evidence_digest=classification.evidence_digest,
        evidence_generation=classification.evidence_generation,
        resolver_ref=classification.resolver_ref,
        resolver_generation=classification.resolver_generation,
        resolution_receipt_ref=ROLE_RESOLUTION_RECEIPT_REF,
        model_revision=sources.model_revision,
        index_sha256=sources.index.raw_sha256,
        num_hidden_layers=78,
        roles=roles,
        evidence_current=True,
    )
    return classification, observation


def build_final_source_bound_report(
    sources: GLM53CheckpointSourceBundle,
    *,
    observation_time: str | None = None,
) -> dict[str, Any]:
    classification, observation = build_canonical_role_intent(sources)
    report = source_bound_probe(
        sources=sources,
        airllm_revision=CURRENT_AIRLLM_SECURITY_GENERATION,
        security_hard_false_remote_code=True,
        representative_sparse_layer=3,
        extra_layer_classification=classification,
        extra_layer_evidence_observation=observation,
        observation_time=observation_time,
    )
    if report.get("schema") != "GLM53CheckpointLayoutProbeV1":
        raise PR340ProducerSnapshotError("FINAL_REPORT_SCHEMA_MISMATCH")
    if report.get("source_binding_proven") is not True:
        raise PR340ProducerSnapshotError("FINAL_REPORT_SOURCE_BINDING_REQUIRED")
    if report.get("blockers") != [RESOLVER_PROVENANCE_BLOCKER]:
        raise PR340ProducerSnapshotError(
            "FINAL_REPORT_BLOCKER_SET_MISMATCH", repr(report.get("blockers"))
        )
    if report.get("extra_layer_resolver_provenance_proven") is not False:
        raise PR340ProducerSnapshotError("FINAL_REPORT_PROVENANCE_PRESTATE_INVALID")
    if report.get("classified_extra_checkpoint_layers") != [
        {"index": ROLE_INDEX, "role": ROLE, "decoder_pager_membership": False}
    ]:
        raise PR340ProducerSnapshotError("FINAL_REPORT_ROLE_MISMATCH")
    if report.get("unclassified_extra_checkpoint_layer_indices") not in ([], tuple()):
        raise PR340ProducerSnapshotError("FINAL_REPORT_UNCLASSIFIED_LAYER_REMAINS")
    if (
        report.get("g2_admitted") is not False
        or report.get("large_checkpoint_admitted") is not False
        or report.get("runtime_execution_proven") is not False
        or report.get("provider_calls") != 0
        or report.get("claim_ceiling") != "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT"
    ):
        raise PR340ProducerSnapshotError("FINAL_REPORT_EFFECT_CEILING_WIDENED")
    return report


def final_source_bound_report_digest(report: Mapping[str, Any]) -> str:
    if not isinstance(report, Mapping):
        raise PR340ProducerSnapshotError("FINAL_REPORT_REQUIRED")
    # These are receipt/legacy metadata. Every other final field is consequence state.
    payload = {key: value for key, value in report.items() if key not in {"observation_time", "logical_id"}}
    return _sha({"domain": REPORT_DIGEST_DOMAIN, "report": payload})


@dataclass(frozen=True)
class PR340ProducerSnapshot:
    final_report_digest: str
    classification_stage_logical_id: str
    source_bundle_id: str
    config_parsed_sha256: str
    index_parsed_sha256: str
    weight_map_digest: str
    blocker_set: tuple[str, ...]
    producer_base_head: str
    producer_execution_head: str
    airllm_security_generation: str
    model_revision: str
    index_sha256: str
    source_binding_proven: bool = True
    producer_snapshot_serialized: bool = True
    producer_snapshot_verified_by_external_registry: bool = False
    g2_admitted: bool = False
    runtime_execution_proven: bool = False
    large_checkpoint_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA

    @property
    def snapshot_digest(self) -> str:
        return _sha(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def emit_pr340_producer_snapshot(
    sources: GLM53CheckpointSourceBundle,
    *,
    producer_execution_head: str,
    observation_time: str | None = None,
) -> tuple[PR340ProducerSnapshot, dict[str, Any]]:
    execution_head = _sha40(producer_execution_head, "PRODUCER_EXECUTION_HEAD_REQUIRED")
    report = build_final_source_bound_report(sources, observation_time=observation_time)
    snapshot = PR340ProducerSnapshot(
        final_report_digest=final_source_bound_report_digest(report),
        classification_stage_logical_id=str(report["logical_id"]),
        source_bundle_id=str(report["source_bundle_id"]),
        config_parsed_sha256=str(report["config_parsed_sha256"]),
        index_parsed_sha256=str(report["index_parsed_sha256"]),
        weight_map_digest=str(report["weight_map_digest"]),
        blocker_set=tuple(report["blockers"]),
        producer_base_head=PR340_PRODUCER_BASE_HEAD,
        producer_execution_head=execution_head,
        airllm_security_generation=CURRENT_AIRLLM_SECURITY_GENERATION,
        model_revision=str(report["model_revision"]),
        index_sha256=str(report["index_sha256"]),
    )
    return snapshot, report
