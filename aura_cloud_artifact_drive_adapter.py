"""Governed Google Drive hydrate/publish sidecar for CS-ARENA-SYNC-001 AS-05.

This module deliberately does not own Drive observation intake, semantic coordinates,
artifact persistence receipts/indexing, WorkGraph wake, or execution authority.
It consumes a record already claimed from the Custodian durable inbox, hydrates the
changed Drive resource only after currentness checks, prepares a hash/version-bound
publish proposal, and can invoke an injected Drive writer only with a separately
bound admission record. A successful write is independently read back before the
adapter reports verified landed bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Protocol

CLOUD_ADAPTER_VERSION = "AURA_CLOUD_ARTIFACT_DRIVE_ADAPTER_V1"
HYDRATION_SCHEMA = "CloudArtifactHydrationV1"
PUBLISH_PROPOSAL_SCHEMA = "CloudArtifactPublishProposalV1"
PUBLISH_ADMISSION_SCHEMA = "CloudArtifactPublishAdmissionV1"
PUBLISH_VERIFICATION_SCHEMA = "CloudArtifactPublishVerificationV1"
_ALLOWED_OPERATIONS = frozenset({"CREATE", "UPDATE", "MIRROR"})


class CloudDriveAdapterError(RuntimeError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message


class DriveResourceReader(Protocol):
    def read_resource(self, resource_id: str) -> "DriveResourceRead":
        """Return current resource bytes + version metadata without mutating Drive."""


class DriveResourceWriter(Protocol):
    def write_resource(
        self,
        *,
        destination_resource_id: str | None,
        content: bytes,
        expected_destination_version: str | None,
        operation: str,
        idempotency_key: str,
    ) -> "DriveWriteResult":
        """Perform an admitted CAS write and return provider identity/version."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CloudDriveAdapterError(f"{field.upper()}_REQUIRED")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CloudDriveAdapterError(f"{field.upper()}_INVALID")
    return value.strip() or None


def _bytes(value: Any, field: str) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise CloudDriveAdapterError(f"{field.upper()}_BYTES_REQUIRED")
    return bytes(value)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CloudDriveAdapterError("NONCANONICAL_VALUE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise CloudDriveAdapterError(f"{field.upper()}_BOOLEAN_REQUIRED")
    return value


@dataclass(frozen=True)
class DriveResourceRead:
    resource_id: str
    version_token: str
    content: bytes
    mime_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        object.__setattr__(self, "resource_id", _text(self.resource_id, "resource_id"))
        object.__setattr__(self, "version_token", _text(self.version_token, "version_token"))
        object.__setattr__(self, "content", _bytes(self.content, "content"))
        object.__setattr__(self, "mime_type", _text(self.mime_type, "mime_type"))

    @property
    def sha256(self) -> str:
        return _sha256(self.content)


@dataclass(frozen=True)
class HydratedCloudArtifact:
    event_key: str
    resource_id: str
    source_currentness_ref: str
    provider_version_token: str
    sha256: str
    byte_size: int
    mime_type: str
    content: bytes
    schema: str = HYDRATION_SCHEMA
    execution_proven: bool = False

    def __post_init__(self) -> None:
        for field in (
            "event_key",
            "resource_id",
            "source_currentness_ref",
            "provider_version_token",
            "sha256",
            "mime_type",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "content", _bytes(self.content, "content"))
        if self.byte_size != len(self.content):
            raise CloudDriveAdapterError("HYDRATION_SIZE_MISMATCH")
        if self.sha256 != _sha256(self.content):
            raise CloudDriveAdapterError("HYDRATION_HASH_MISMATCH")
        if self.schema != HYDRATION_SCHEMA or self.execution_proven is not False:
            raise CloudDriveAdapterError("HYDRATION_BOUNDARY_INVALID")


@dataclass(frozen=True)
class CloudPublishProposal:
    source_event_key: str
    source_resource_id: str
    source_version_token: str
    source_sha256: str
    source_content: bytes
    currentness_ref: str
    operation: str
    destination_resource_id: str | None
    expected_destination_version: str | None
    destination_surface: str
    authority_ref: str
    schema: str = PUBLISH_PROPOSAL_SCHEMA
    effect_authorized: bool = False
    provider_call_authorized: bool = False
    runtime_execution_proven: bool = False

    def __post_init__(self) -> None:
        for field in (
            "source_event_key",
            "source_resource_id",
            "source_version_token",
            "source_sha256",
            "currentness_ref",
            "destination_surface",
            "authority_ref",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "source_content", _bytes(self.source_content, "source_content"))
        operation = _text(self.operation, "operation").upper()
        if operation not in _ALLOWED_OPERATIONS:
            raise CloudDriveAdapterError("OPERATION_INVALID")
        object.__setattr__(self, "operation", operation)
        object.__setattr__(
            self,
            "destination_resource_id",
            _optional_text(self.destination_resource_id, "destination_resource_id"),
        )
        object.__setattr__(
            self,
            "expected_destination_version",
            _optional_text(self.expected_destination_version, "expected_destination_version"),
        )
        if operation in {"UPDATE", "MIRROR"} and self.destination_resource_id is None:
            raise CloudDriveAdapterError("DESTINATION_RESOURCE_REQUIRED")
        if operation == "UPDATE" and self.expected_destination_version is None:
            raise CloudDriveAdapterError("EXPECTED_DESTINATION_VERSION_REQUIRED")
        if self.source_sha256 != _sha256(self.source_content):
            raise CloudDriveAdapterError("SOURCE_HASH_MISMATCH")
        if (
            self.schema != PUBLISH_PROPOSAL_SCHEMA
            or self.effect_authorized is not False
            or self.provider_call_authorized is not False
            or self.runtime_execution_proven is not False
        ):
            raise CloudDriveAdapterError("PROPOSAL_AUTHORITY_BOUNDARY_INVALID")

    @property
    def digest(self) -> str:
        return _digest(
            "AURA_CLOUD_ARTIFACT_PUBLISH_PROPOSAL_V1",
            {
                "source_event_key": self.source_event_key,
                "source_resource_id": self.source_resource_id,
                "source_version_token": self.source_version_token,
                "source_sha256": self.source_sha256,
                "currentness_ref": self.currentness_ref,
                "operation": self.operation,
                "destination_resource_id": self.destination_resource_id,
                "expected_destination_version": self.expected_destination_version,
                "destination_surface": self.destination_surface,
                "authority_ref": self.authority_ref,
            },
        )

    @property
    def idempotency_key(self) -> str:
        return _digest("AURA_CLOUD_ARTIFACT_WRITE_IDEMPOTENCY_V1", self.digest)


@dataclass(frozen=True)
class CloudPublishAdmission:
    proposal_digest: str
    currentness_ref: str
    authority_receipt_ref: str
    write_authorized: bool = False
    provider_call_authorized: bool = False
    schema: str = PUBLISH_ADMISSION_SCHEMA

    def __post_init__(self) -> None:
        for field in ("proposal_digest", "currentness_ref", "authority_receipt_ref"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(
            self, "write_authorized", _strict_bool(self.write_authorized, "write_authorized")
        )
        object.__setattr__(
            self,
            "provider_call_authorized",
            _strict_bool(self.provider_call_authorized, "provider_call_authorized"),
        )
        if self.schema != PUBLISH_ADMISSION_SCHEMA:
            raise CloudDriveAdapterError("ADMISSION_SCHEMA_INVALID")


@dataclass(frozen=True)
class DriveWriteResult:
    resource_id: str
    version_token: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "resource_id", _text(self.resource_id, "resource_id"))
        object.__setattr__(self, "version_token", _text(self.version_token, "version_token"))


@dataclass(frozen=True)
class CloudPublishVerification:
    proposal_digest: str
    destination_resource_id: str
    destination_version_token: str
    persisted_sha256: str
    byte_size: int
    status: str
    authority_receipt_ref: str
    artifact_write_observed: bool
    schema: str = PUBLISH_VERIFICATION_SCHEMA
    runtime_execution_proven: bool = False
    background_execution_claimed: bool = False

    def __post_init__(self) -> None:
        for field in (
            "proposal_digest",
            "destination_resource_id",
            "destination_version_token",
            "persisted_sha256",
            "status",
            "authority_receipt_ref",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(
            self,
            "artifact_write_observed",
            _strict_bool(self.artifact_write_observed, "artifact_write_observed"),
        )
        if self.byte_size < 0:
            raise CloudDriveAdapterError("BYTE_SIZE_INVALID")
        if (
            self.schema != PUBLISH_VERIFICATION_SCHEMA
            or self.runtime_execution_proven is not False
            or self.background_execution_claimed is not False
        ):
            raise CloudDriveAdapterError("VERIFICATION_EXECUTION_BOUNDARY_INVALID")


def hydrate_claimed_event(
    record: Mapping[str, Any],
    *,
    currentness_ref: str,
    event_currentness_ref: str,
    reader: DriveResourceReader,
) -> HydratedCloudArtifact:
    """Hydrate a durable Custodian event only after claim/currentness checks.

    Removal/tombstone events intentionally do not hydrate bytes; those belong to the
    tombstone path owned by the event/identity core and persistence layer.
    """
    if not isinstance(record, Mapping):
        raise CloudDriveAdapterError("EVENT_RECORD_INVALID")
    if str(record.get("status") or "") != "processing":
        raise CloudDriveAdapterError("EVENT_NOT_DURABLY_CLAIMED")
    source = str(record.get("source") or "")
    if source not in {"drive_changes", "workspace_events"}:
        raise CloudDriveAdapterError("EVENT_SOURCE_UNSUPPORTED")
    event_type = str(record.get("event_type") or "")
    if event_type.endswith(".removed") or "delete" in event_type.lower():
        raise CloudDriveAdapterError("TOMBSTONE_EVENT_REQUIRES_NO_HYDRATION")
    currentness = _text(currentness_ref, "currentness_ref")
    event_currentness = _text(event_currentness_ref, "event_currentness_ref")
    if currentness != event_currentness:
        raise CloudDriveAdapterError("STALE_CURRENTNESS_REBASE_REQUIRED")
    event_key = _text(record.get("event_key"), "event_key")
    resource_id = _text(record.get("resource_id"), "resource_id")
    read = reader.read_resource(resource_id)
    if not isinstance(read, DriveResourceRead):
        raise CloudDriveAdapterError("DRIVE_READ_RESULT_INVALID")
    if read.resource_id != resource_id:
        raise CloudDriveAdapterError("DRIVE_READ_RESOURCE_MISMATCH")
    return HydratedCloudArtifact(
        event_key=event_key,
        resource_id=resource_id,
        source_currentness_ref=currentness,
        provider_version_token=read.version_token,
        sha256=read.sha256,
        byte_size=len(read.content),
        mime_type=read.mime_type,
        content=read.content,
    )


def prepare_publish_proposal(
    hydrated: HydratedCloudArtifact,
    *,
    currentness_ref: str,
    operation: str,
    destination_surface: str,
    authority_ref: str,
    destination_resource_id: str | None = None,
    expected_destination_version: str | None = None,
) -> CloudPublishProposal:
    currentness = _text(currentness_ref, "currentness_ref")
    if currentness != hydrated.source_currentness_ref:
        raise CloudDriveAdapterError("STALE_CURRENTNESS_REBASE_REQUIRED")
    return CloudPublishProposal(
        source_event_key=hydrated.event_key,
        source_resource_id=hydrated.resource_id,
        source_version_token=hydrated.provider_version_token,
        source_sha256=hydrated.sha256,
        source_content=hydrated.content,
        currentness_ref=currentness,
        operation=operation,
        destination_resource_id=destination_resource_id,
        expected_destination_version=expected_destination_version,
        destination_surface=destination_surface,
        authority_ref=authority_ref,
    )


def execute_admitted_publish(
    proposal: CloudPublishProposal,
    admission: CloudPublishAdmission,
    *,
    currentness_ref: str,
    writer: DriveResourceWriter,
    reader: DriveResourceReader,
) -> CloudPublishVerification:
    """Execute exactly one admitted Drive write and verify landed bytes by readback.

    The injected writer MUST enforce provider-side CAS using the supplied expected
    destination version. This function refuses before calling the writer if the
    admission/currentness/proposal binding is stale or incomplete.
    """
    currentness = _text(currentness_ref, "currentness_ref")
    if currentness != proposal.currentness_ref or currentness != admission.currentness_ref:
        raise CloudDriveAdapterError("STALE_CURRENTNESS_REBASE_REQUIRED")
    if admission.proposal_digest != proposal.digest:
        raise CloudDriveAdapterError("ADMISSION_PROPOSAL_MISMATCH")
    if admission.authority_receipt_ref != proposal.authority_ref:
        raise CloudDriveAdapterError("ADMISSION_AUTHORITY_MISMATCH")
    if not admission.write_authorized:
        raise CloudDriveAdapterError("DRIVE_WRITE_NOT_AUTHORIZED")
    if not admission.provider_call_authorized:
        raise CloudDriveAdapterError("DRIVE_PROVIDER_CALL_NOT_AUTHORIZED")

    result = writer.write_resource(
        destination_resource_id=proposal.destination_resource_id,
        content=proposal.source_content,
        expected_destination_version=proposal.expected_destination_version,
        operation=proposal.operation,
        idempotency_key=proposal.idempotency_key,
    )
    if not isinstance(result, DriveWriteResult):
        raise CloudDriveAdapterError("DRIVE_WRITE_RESULT_INVALID")
    if proposal.destination_resource_id and result.resource_id != proposal.destination_resource_id:
        raise CloudDriveAdapterError("DRIVE_WRITE_RESOURCE_MISMATCH")

    landed = reader.read_resource(result.resource_id)
    if not isinstance(landed, DriveResourceRead):
        raise CloudDriveAdapterError("DRIVE_READBACK_RESULT_INVALID")
    if landed.resource_id != result.resource_id:
        raise CloudDriveAdapterError("DRIVE_READBACK_RESOURCE_MISMATCH")
    if landed.version_token != result.version_token:
        raise CloudDriveAdapterError("DRIVE_READBACK_VERSION_MISMATCH")
    if landed.sha256 != proposal.source_sha256:
        raise CloudDriveAdapterError("DRIVE_LANDED_HASH_MISMATCH")
    if landed.content != proposal.source_content:
        raise CloudDriveAdapterError("DRIVE_LANDED_BYTES_MISMATCH")

    return CloudPublishVerification(
        proposal_digest=proposal.digest,
        destination_resource_id=landed.resource_id,
        destination_version_token=landed.version_token,
        persisted_sha256=landed.sha256,
        byte_size=len(landed.content),
        status="LANDED_BYTES_VERIFIED",
        authority_receipt_ref=admission.authority_receipt_ref,
        artifact_write_observed=True,
    )


def adapter_contract() -> dict[str, Any]:
    """Machine-readable boundary declaration for sibling AS-02/06/07 integration."""
    return {
        "version": CLOUD_ADAPTER_VERSION,
        "observation_owner": "aura_custodian_drive_event_adapter.py",
        "observation_boundary": "READ_ONLY_DURABLE_INBOX",
        "coordinate_owner": "EXTERNAL_AURA_UNIFY_REQUIRED",
        "persistence_receipt_owner": "AS_06_EXTERNAL",
        "workgraph_wake_owner": "AS_07_H_I_EXTERNAL",
        "drive_writer": "INJECTED_HOST_EFFECT_ADAPTER",
        "requires": [
            "durably_claimed_event",
            "matching_currentness",
            "exact_source_hash_and_provider_version",
            "proposal_digest_bound_admission",
            "provider_side_version_CAS",
            "landed_byte_readback",
        ],
        "execution_proven": False,
        "provider_calls_during_observation": 0,
    }
