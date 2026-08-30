from __future__ import annotations

import hashlib

import pytest

from aura_arena_artifact_event_core import ArtifactEventRefusal, MirrorLineage
from aura_cloud_artifact_drive_adapter import DriveResourceRead
from aura_cloud_artifact_event_bridge import (
    CanonicalCloudArtifact,
    CanonicalCloudTombstone,
    CloudArtifactBridgeError,
    bind_custodian_record,
    bridge_contract,
    hydrate_canonical_event,
    validate_mirror_binding,
)


class FakeReader:
    def __init__(self):
        self.calls = []

    def read_resource(self, resource_id):
        self.calls.append(resource_id)
        return DriveResourceRead(
            resource_id,
            "v1",
            b"cloud-bytes",
            "application/octet-stream",
        )


def record(**overrides):
    value = {
        "event_key": "google:change:p1:0:file-1",
        "provider": "google",
        "source": "drive_changes",
        "event_type": "drive.change.file",
        "resource_id": "file-1",
        "observed_at": "2026-08-30T15:00:00Z",
        "status": "processing",
    }
    value.update(overrides)
    return value


def bind(rec=None, **kwargs):
    return bind_custodian_record(
        rec or record(),
        canonical_event_type=kwargs.pop("canonical_event_type", "MODIFY"),
        project_id="CS-PROJ-001",
        source_surface=kwargs.pop("source_surface", "AURA_DRIVE_CLOUD"),
        source_currentness_ref=kwargs.pop("source_currentness_ref", "head-1"),
        **kwargs,
    )


def test_provider_event_is_not_auto_promoted_to_canonical_semantics():
    event = bind()
    assert record()["event_type"] == "drive.change.file"
    assert event.event_type == "MODIFY"


def test_invalid_canonical_semantic_type_fails_closed():
    with pytest.raises(ArtifactEventRefusal, match="UNSUPPORTED_EVENT_TYPE"):
        bind(canonical_event_type="drive.change.file")


def test_event_id_is_stable_across_observation_time_redelivery():
    first = bind(record(observed_at="2026-08-30T15:00:00Z"))
    second = bind(record(observed_at="2026-08-30T16:00:00Z"))
    assert first.event_id == second.event_id


def test_unclaimed_custodian_record_refused_before_binding():
    with pytest.raises(
        CloudArtifactBridgeError,
        match="CUSTODIAN_EVENT_NOT_CLAIMED",
    ):
        bind(record(status="pending"))


def test_hydration_produces_as02_content_addressed_identity():
    reader = FakeReader()
    event = bind()
    result = hydrate_canonical_event(
        record(),
        event,
        currentness_ref="head-1",
        reader=reader,
    )
    assert isinstance(result, CanonicalCloudArtifact)
    expected = hashlib.sha256(b"cloud-bytes").hexdigest()
    assert result.identity.sha256 == expected
    assert result.identity.artifact_sid == f"artifact-sha256-{expected}"
    assert result.hydrated.sha256 == expected
    assert result.event.event_id in result.identity.parent_refs
    assert reader.calls == ["file-1"]


def test_stale_currentness_refuses_before_drive_read():
    reader = FakeReader()
    event = bind(source_currentness_ref="head-1")
    with pytest.raises(
        CloudArtifactBridgeError,
        match="STALE_CURRENTNESS_REBASE_REQUIRED",
    ):
        hydrate_canonical_event(
            record(),
            event,
            currentness_ref="head-2",
            reader=reader,
        )
    assert reader.calls == []


def test_resource_mismatch_refuses_before_drive_read():
    reader = FakeReader()
    event = bind(record(resource_id="file-1"))
    with pytest.raises(
        CloudArtifactBridgeError,
        match="EVENT_CUSTODIAN_RESOURCE_MISMATCH",
    ):
        hydrate_canonical_event(
            record(resource_id="file-2"),
            event,
            currentness_ref="head-1",
            reader=reader,
        )
    assert reader.calls == []


def test_tombstone_uses_as02_no_bytes_contract_and_never_reads_drive():
    reader = FakeReader()
    event = bind(canonical_event_type="TOMBSTONE")
    result = hydrate_canonical_event(
        record(),
        event,
        currentness_ref="head-1",
        reader=reader,
    )
    assert isinstance(result, CanonicalCloudTombstone)
    assert result.bytes_hydrated is False
    assert reader.calls == []


def test_mirror_lineage_exact_binding_passes():
    origin = "custodian:google:change:p1:0:file-1"
    lineage = MirrorLineage.start(
        origin,
        "AURA_DRIVE_CLOUD",
    ).next_hop("AURA_DRIVE_2")
    event = bind(
        source_surface="AURA_DRIVE_2",
        mirror_lineage=lineage,
    )
    validate_mirror_binding(event, lineage)
    assert event.generation == 1
    assert event.mirror_fence == lineage.fence


def test_mirror_lineage_mismatch_fails_closed():
    origin = "custodian:google:change:p1:0:file-1"
    lineage = MirrorLineage.start(
        origin,
        "AURA_DRIVE_CLOUD",
    ).next_hop("AURA_DRIVE_2")
    event = bind(
        source_surface="AURA_DRIVE_2",
        mirror_lineage=lineage,
    )
    other = MirrorLineage.start(
        origin,
        "AURA_DRIVE_CLOUD",
    ).next_hop("OTHER")
    with pytest.raises(
        CloudArtifactBridgeError,
        match="MIRROR_SOURCE_SURFACE_MISMATCH",
    ):
        validate_mirror_binding(event, other)


def test_bridge_never_claims_coordinate_receipt_wake_or_execution():
    reader = FakeReader()
    result = hydrate_canonical_event(
        record(),
        bind(),
        currentness_ref="head-1",
        reader=reader,
    )
    assert result.coordinate_bound is False
    assert result.persistence_receipt_emitted is False
    assert result.workgraph_wake_emitted is False
    assert result.execution_proven is False
    contract = bridge_contract()
    assert contract["raw_provider_event_autopromotion"] is False
    assert contract["execution_proven"] is False
