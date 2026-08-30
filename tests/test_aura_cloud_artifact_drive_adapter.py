from __future__ import annotations

import pytest

from aura_cloud_artifact_drive_adapter import (
    CloudDriveAdapterError,
    CloudPublishAdmission,
    DriveResourceRead,
    DriveWriteResult,
    adapter_contract,
    execute_admitted_publish,
    hydrate_claimed_event,
    prepare_publish_proposal,
)


class FakeDrive:
    def __init__(self):
        self.resources = {
            "src": ("v1", b"source-bytes", "application/octet-stream"),
            "dest": ("d1", b"old", "application/octet-stream"),
        }
        self.read_calls = []
        self.write_calls = []
        self.corrupt_readback = False
        self.force_result_version = None

    def read_resource(self, resource_id):
        self.read_calls.append(resource_id)
        version, content, mime = self.resources[resource_id]
        if self.corrupt_readback and resource_id == "dest":
            content = b"corrupt"
        return DriveResourceRead(resource_id, version, content, mime)

    def write_resource(
        self,
        *,
        destination_resource_id,
        content,
        expected_destination_version,
        operation,
        idempotency_key,
    ):
        self.write_calls.append(
            (destination_resource_id, expected_destination_version, operation, idempotency_key)
        )
        if operation == "CREATE":
            resource_id = destination_resource_id or "created"
            if resource_id in self.resources:
                raise CloudDriveAdapterError("PROVIDER_ALREADY_EXISTS")
            version = "n1"
        else:
            resource_id = destination_resource_id
            if resource_id not in self.resources:
                raise CloudDriveAdapterError("PROVIDER_NOT_FOUND")
            current_version = self.resources[resource_id][0]
            if expected_destination_version is not None and current_version != expected_destination_version:
                raise CloudDriveAdapterError("PROVIDER_CAS_CONFLICT")
            version = "d2"
        self.resources[resource_id] = (version, bytes(content), "application/octet-stream")
        return DriveWriteResult(resource_id, self.force_result_version or version)


def record(**overrides):
    value = {
        "event_key": "google:evt-1",
        "provider": "google",
        "source": "drive_changes",
        "event_type": "drive.change.file",
        "resource_id": "src",
        "status": "processing",
    }
    value.update(overrides)
    return value


def hydrate(drive=None):
    drive = drive or FakeDrive()
    return hydrate_claimed_event(
        record(),
        currentness_ref="head-1",
        event_currentness_ref="head-1",
        reader=drive,
    )


def proposal(drive=None):
    drive = drive or FakeDrive()
    h = hydrate(drive)
    return prepare_publish_proposal(
        h,
        currentness_ref="head-1",
        operation="UPDATE",
        destination_resource_id="dest",
        expected_destination_version="d1",
        destination_surface="google_drive",
        authority_ref="authority:1",
    )


def admitted(p):
    return CloudPublishAdmission(
        proposal_digest=p.digest,
        currentness_ref="head-1",
        authority_receipt_ref="authority:1",
        write_authorized=True,
        provider_call_authorized=True,
    )


def test_hydrates_only_processing_record_after_currentness_gate():
    drive = FakeDrive()
    h = hydrate(drive)
    assert drive.read_calls == ["src"]
    assert h.provider_version_token == "v1"
    assert h.byte_size == len(b"source-bytes")
    assert h.execution_proven is False


def test_unclaimed_event_never_calls_reader():
    drive = FakeDrive()
    with pytest.raises(CloudDriveAdapterError, match="EVENT_NOT_DURABLY_CLAIMED"):
        hydrate_claimed_event(
            record(status="pending"),
            currentness_ref="head-1",
            event_currentness_ref="head-1",
            reader=drive,
        )
    assert drive.read_calls == []


def test_stale_event_never_calls_reader():
    drive = FakeDrive()
    with pytest.raises(CloudDriveAdapterError, match="STALE_CURRENTNESS_REBASE_REQUIRED"):
        hydrate_claimed_event(
            record(),
            currentness_ref="head-2",
            event_currentness_ref="head-1",
            reader=drive,
        )
    assert drive.read_calls == []


def test_tombstone_event_does_not_hydrate_bytes():
    drive = FakeDrive()
    with pytest.raises(CloudDriveAdapterError, match="TOMBSTONE_EVENT_REQUIRES_NO_HYDRATION"):
        hydrate_claimed_event(
            record(event_type="drive.change.file.removed"),
            currentness_ref="head-1",
            event_currentness_ref="head-1",
            reader=drive,
        )
    assert drive.read_calls == []


def test_publish_proposal_is_non_authoritative_and_hash_bound():
    p = proposal()
    assert p.effect_authorized is False
    assert p.provider_call_authorized is False
    assert p.runtime_execution_proven is False
    assert len(p.digest) == 64
    assert len(p.idempotency_key) == 64


def test_update_requires_expected_destination_version():
    h = hydrate()
    with pytest.raises(CloudDriveAdapterError, match="EXPECTED_DESTINATION_VERSION_REQUIRED"):
        prepare_publish_proposal(
            h,
            currentness_ref="head-1",
            operation="UPDATE",
            destination_resource_id="dest",
            destination_surface="google_drive",
            authority_ref="authority:1",
        )


def test_unadmitted_write_never_calls_writer():
    drive = FakeDrive()
    p = proposal(drive)
    admission = CloudPublishAdmission(
        proposal_digest=p.digest,
        currentness_ref="head-1",
        authority_receipt_ref="authority:1",
        write_authorized=False,
        provider_call_authorized=True,
    )
    with pytest.raises(CloudDriveAdapterError, match="DRIVE_WRITE_NOT_AUTHORIZED"):
        execute_admitted_publish(
            p, admission, currentness_ref="head-1", writer=drive, reader=drive
        )
    assert drive.write_calls == []


def test_provider_call_requires_explicit_admission():
    drive = FakeDrive()
    p = proposal(drive)
    admission = CloudPublishAdmission(
        proposal_digest=p.digest,
        currentness_ref="head-1",
        authority_receipt_ref="authority:1",
        write_authorized=True,
        provider_call_authorized=False,
    )
    with pytest.raises(CloudDriveAdapterError, match="DRIVE_PROVIDER_CALL_NOT_AUTHORIZED"):
        execute_admitted_publish(
            p, admission, currentness_ref="head-1", writer=drive, reader=drive
        )
    assert drive.write_calls == []


def test_stale_currentness_refuses_before_write():
    drive = FakeDrive()
    p = proposal(drive)
    with pytest.raises(CloudDriveAdapterError, match="STALE_CURRENTNESS_REBASE_REQUIRED"):
        execute_admitted_publish(
            p, admitted(p), currentness_ref="head-2", writer=drive, reader=drive
        )
    assert drive.write_calls == []


def test_admission_must_bind_exact_proposal_digest():
    drive = FakeDrive()
    p = proposal(drive)
    admission = CloudPublishAdmission(
        proposal_digest="x" * 64,
        currentness_ref="head-1",
        authority_receipt_ref="authority:1",
        write_authorized=True,
        provider_call_authorized=True,
    )
    with pytest.raises(CloudDriveAdapterError, match="ADMISSION_PROPOSAL_MISMATCH"):
        execute_admitted_publish(
            p, admission, currentness_ref="head-1", writer=drive, reader=drive
        )
    assert drive.write_calls == []


def test_provider_side_cas_conflict_fails_without_overwrite():
    drive = FakeDrive()
    p = proposal(drive)
    drive.resources["dest"] = ("d9", b"changed-by-sibling", "application/octet-stream")
    with pytest.raises(CloudDriveAdapterError, match="PROVIDER_CAS_CONFLICT"):
        execute_admitted_publish(
            p, admitted(p), currentness_ref="head-1", writer=drive, reader=drive
        )
    assert drive.resources["dest"][1] == b"changed-by-sibling"


def test_successful_write_requires_landed_byte_readback():
    drive = FakeDrive()
    p = proposal(drive)
    receipt = execute_admitted_publish(
        p, admitted(p), currentness_ref="head-1", writer=drive, reader=drive
    )
    assert receipt.status == "LANDED_BYTES_VERIFIED"
    assert receipt.persisted_sha256 == p.source_sha256
    assert receipt.destination_version_token == "d2"
    assert receipt.artifact_write_observed is True
    assert receipt.runtime_execution_proven is False
    assert receipt.background_execution_claimed is False


def test_corrupt_readback_fails_closed():
    drive = FakeDrive()
    p = proposal(drive)
    drive.corrupt_readback = True
    with pytest.raises(CloudDriveAdapterError, match="DRIVE_LANDED_HASH_MISMATCH"):
        execute_admitted_publish(
            p, admitted(p), currentness_ref="head-1", writer=drive, reader=drive
        )


def test_readback_version_must_match_writer_result():
    drive = FakeDrive()
    p = proposal(drive)
    drive.force_result_version = "provider-said-different"
    with pytest.raises(CloudDriveAdapterError, match="DRIVE_READBACK_VERSION_MISMATCH"):
        execute_admitted_publish(
            p, admitted(p), currentness_ref="head-1", writer=drive, reader=drive
        )


def test_contract_preserves_external_owners():
    contract = adapter_contract()
    assert contract["observation_boundary"] == "READ_ONLY_DURABLE_INBOX"
    assert contract["coordinate_owner"] == "EXTERNAL_AURA_UNIFY_REQUIRED"
    assert contract["persistence_receipt_owner"] == "AS_06_EXTERNAL"
    assert contract["workgraph_wake_owner"] == "AS_07_H_I_EXTERNAL"
    assert contract["execution_proven"] is False
