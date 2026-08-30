"""AS-02 <-> AS-05 bridge for cloud artifact intake.

Pure integration only. It translates a *durably claimed* Custodian inbox record
into the canonical AS-02 ArtifactMutationEvent, then binds AS-05 hydrated bytes to
AS-02 ArtifactIdentity. Coordinate assignment, persistence receipts/indexing,
WorkGraph wake, and execution authority remain external owners.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from aura_arena_artifact_event_core import (
    ArtifactIdentity,
    ArtifactMutationEvent,
    MirrorLineage,
    validate_event_identity_binding,
)
from aura_cloud_artifact_drive_adapter import (
    DriveResourceReader,
    HydratedCloudArtifact,
    hydrate_claimed_event,
)

BRIDGE_SCHEMA = "CloudArtifactCanonicalBindingV1"
TOMBSTONE_SCHEMA = "CloudArtifactTombstoneBindingV1"


class CloudArtifactBridgeError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _required(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CloudArtifactBridgeError(f"{field.upper()}_REQUIRED")
    return value.strip()


def _record_text(record: Mapping[str, Any], field: str) -> str:
    return _required(record.get(field), field)


def bind_custodian_record(
    record: Mapping[str, Any],
    *,
    canonical_event_type: str,
    project_id: str,
    source_surface: str,
    source_currentness_ref: str,
    producer_worker_id: str = "",
    claim_id: str = "",
    work_order_id: str = "",
    prior_artifact_id: str = "",
    mirror_lineage: MirrorLineage | None = None,
) -> ArtifactMutationEvent:
    """Bind provider-neutral durable intake to AS-02 canonical event semantics.

    `canonical_event_type` and `source_surface` are explicit caller-owned semantic
    inputs. Raw provider event names and file/folder heuristics are never promoted
    into canonical mutation or coordinate truth by this bridge.
    """
    if not isinstance(record, Mapping):
        raise CloudArtifactBridgeError("CUSTODIAN_RECORD_INVALID")
    if str(record.get("status") or "") != "processing":
        raise CloudArtifactBridgeError("CUSTODIAN_EVENT_NOT_CLAIMED")
    event_key = _record_text(record, "event_key")
    provider = _record_text(record, "provider")
    resource_id = _record_text(record, "resource_id")
    origin_id = f"custodian:{event_key}"

    generation = 0
    mirror_fence = ""
    if mirror_lineage is not None:
        if mirror_lineage.origin_id != origin_id:
            raise CloudArtifactBridgeError("MIRROR_ORIGIN_MISMATCH")
        if mirror_lineage.surfaces[-1] != _required(source_surface, "source_surface"):
            raise CloudArtifactBridgeError("MIRROR_SOURCE_SURFACE_MISMATCH")
        generation = mirror_lineage.generation
        mirror_fence = mirror_lineage.fence

    return ArtifactMutationEvent(
        origin_id=origin_id,
        provider=provider,
        source_surface=source_surface,
        event_type=canonical_event_type,
        resource_ref=resource_id,
        project_id=project_id,
        producer_worker_id=producer_worker_id,
        claim_id=claim_id,
        work_order_id=work_order_id,
        source_currentness_ref=source_currentness_ref,
        observed_at=str(record.get("observed_at") or ""),
        generation=generation,
        mirror_fence=mirror_fence,
        prior_artifact_id=prior_artifact_id,
    )


def validate_mirror_binding(
    event: ArtifactMutationEvent, lineage: MirrorLineage
) -> None:
    if event.origin_id != lineage.origin_id:
        raise CloudArtifactBridgeError("MIRROR_ORIGIN_MISMATCH")
    if event.source_surface != lineage.surfaces[-1]:
        raise CloudArtifactBridgeError("MIRROR_SOURCE_SURFACE_MISMATCH")
    if event.generation != lineage.generation:
        raise CloudArtifactBridgeError("MIRROR_GENERATION_MISMATCH")
    if event.mirror_fence != lineage.fence:
        raise CloudArtifactBridgeError("MIRROR_FENCE_MISMATCH")


@dataclass(frozen=True)
class CanonicalCloudArtifact:
    event: ArtifactMutationEvent
    identity: ArtifactIdentity
    hydrated: HydratedCloudArtifact
    schema: str = BRIDGE_SCHEMA
    coordinate_bound: bool = False
    persistence_receipt_emitted: bool = False
    workgraph_wake_emitted: bool = False
    execution_proven: bool = False

    def __post_init__(self) -> None:
        if self.schema != BRIDGE_SCHEMA:
            raise CloudArtifactBridgeError("BRIDGE_SCHEMA_INVALID")
        if self.identity.sha256 != self.hydrated.sha256:
            raise CloudArtifactBridgeError("IDENTITY_HYDRATION_HASH_MISMATCH")
        if self.identity.byte_size != self.hydrated.byte_size:
            raise CloudArtifactBridgeError("IDENTITY_HYDRATION_SIZE_MISMATCH")
        if self.event.resource_ref != self.hydrated.resource_id:
            raise CloudArtifactBridgeError("EVENT_HYDRATION_RESOURCE_MISMATCH")
        if any(
            (
                self.coordinate_bound,
                self.persistence_receipt_emitted,
                self.workgraph_wake_emitted,
                self.execution_proven,
            )
        ):
            raise CloudArtifactBridgeError("BRIDGE_AUTHORITY_BOUNDARY_WIDENED")


@dataclass(frozen=True)
class CanonicalCloudTombstone:
    event: ArtifactMutationEvent
    schema: str = TOMBSTONE_SCHEMA
    bytes_hydrated: bool = False
    coordinate_bound: bool = False
    persistence_receipt_emitted: bool = False
    workgraph_wake_emitted: bool = False
    execution_proven: bool = False

    def __post_init__(self) -> None:
        if self.schema != TOMBSTONE_SCHEMA or any(
            (
                self.bytes_hydrated,
                self.coordinate_bound,
                self.persistence_receipt_emitted,
                self.workgraph_wake_emitted,
                self.execution_proven,
            )
        ):
            raise CloudArtifactBridgeError("TOMBSTONE_BOUNDARY_INVALID")


def hydrate_canonical_event(
    record: Mapping[str, Any],
    event: ArtifactMutationEvent,
    *,
    currentness_ref: str,
    reader: DriveResourceReader,
    extension: str = "",
) -> CanonicalCloudArtifact | CanonicalCloudTombstone:
    """Hydrate/bind exact bytes for non-tombstone canonical cloud mutations."""
    expected_origin = f"custodian:{_record_text(record, 'event_key')}"
    if event.origin_id != expected_origin:
        raise CloudArtifactBridgeError("EVENT_CUSTODIAN_ORIGIN_MISMATCH")
    if event.resource_ref != _record_text(record, "resource_id"):
        raise CloudArtifactBridgeError("EVENT_CUSTODIAN_RESOURCE_MISMATCH")
    currentness = _required(currentness_ref, "currentness_ref")
    if event.source_currentness_ref != currentness:
        raise CloudArtifactBridgeError("STALE_CURRENTNESS_REBASE_REQUIRED")

    if event.event_type in {"DELETE", "TOMBSTONE"}:
        validate_event_identity_binding(event, None)
        return CanonicalCloudTombstone(event=event)

    hydrated = hydrate_claimed_event(
        record,
        currentness_ref=currentness,
        event_currentness_ref=event.source_currentness_ref,
        reader=reader,
    )
    identity = ArtifactIdentity.from_bytes(
        hydrated.content,
        mime_type=hydrated.mime_type,
        extension=extension,
        parent_refs=(event.event_id,),
    )
    validate_event_identity_binding(event, identity)
    return CanonicalCloudArtifact(event=event, identity=identity, hydrated=hydrated)


def bridge_contract() -> dict[str, Any]:
    return {
        "schema": "CloudArtifactEventBridgeContractV1",
        "upstream_intake": "Custodian EventEnvelope / durable processing claim",
        "canonical_event_owner": "AS_02 ArtifactMutationEventV1",
        "canonical_identity_owner": "AS_02 ArtifactIdentityV1",
        "cloud_hydration_publish_owner": "AS_05 Cloud Drive adapter",
        "coordinate_owner": "AS_03 / AURA_UNIFY external",
        "persistence_receipt_index_owner": "AS_06 external",
        "workgraph_wake_owner": "AS_07 / H_I external",
        "raw_provider_event_autopromotion": False,
        "execution_proven": False,
    }
