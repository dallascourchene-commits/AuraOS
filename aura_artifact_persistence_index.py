"""AS-06 durable artifact persistence/index rebased to repaired AS-02 C0.

This module remains a pure coordination/evidence plane.  It consumes canonical
ArtifactMutationEventV1/ArtifactIdentityV1 plus independently verified landed
artifact evidence, emits replay-stable persistence receipts, and projects a
CAS-bound live artifact index.  It never grants semantic, coordinate, effect,
provider, wake, or execution authority.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

PERSISTENCE_RECEIPT_SCHEMA = "ArtifactPersistenceReceiptV1"
LIVE_INDEX_SCHEMA = "LiveArtifactIndexV1"
ARTIFACT_AVAILABLE_SCHEMA = "ArtifactAvailableEventV1"
ARTIFACT_EVENT_SCHEMA = "ArtifactMutationEventV1"
ARTIFACT_IDENTITY_SCHEMA = "ArtifactIdentityV1"
UNKNOWN = "UNKNOWN"

_OWNER_STATUSES = frozenset({"BOUND", "PENDING_EXTERNAL_OWNER", UNKNOWN})
_COORDINATE_STATUSES = frozenset({"BOUND", "PENDING_EXTERNAL_OWNER", UNKNOWN})
_OPERATIONS = frozenset({"UPSERT", "TOMBSTONE"})
_LINEAGE_REQUIRED_EVENT_TYPES = frozenset({"RENAME", "DELETE", "TOMBSTONE", "SUPERSEDE"})


class ArtifactPersistenceError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(value: Any, code: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ArtifactPersistenceError(code)
    out = value.strip()
    if not out and not allow_empty:
        raise ArtifactPersistenceError(code)
    return out


def _optional_text(value: Any, code: str) -> str | None:
    if value is None:
        return None
    out = _text(value, code, allow_empty=True)
    return out or None


def _known_currentness(value: Any, code: str = "CURRENTNESS_REF_REQUIRED") -> str:
    out = _text(value, code)
    if out == UNKNOWN:
        raise ArtifactPersistenceError("STALE_CURRENTNESS_REBASE_REQUIRED")
    return out


def _nonnegative_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ArtifactPersistenceError(code)
    return value


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
        raise ArtifactPersistenceError("NONCANONICAL_VALUE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _sha256_text(value: Any, code: str) -> str:
    out = _text(value, code).lower()
    if len(out) != 64 or any(ch not in "0123456789abcdef" for ch in out):
        raise ArtifactPersistenceError(code)
    return out


def _strict_bool(value: Any, code: str) -> bool:
    if type(value) is not bool:
        raise ArtifactPersistenceError(code)
    return value


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactPersistenceError(code)
    return value


def _event_common(
    event: Mapping[str, Any],
    *,
    currentness_ref: str,
    mirror_fence: str,
) -> dict[str, Any]:
    if event.get("schema") != ARTIFACT_EVENT_SCHEMA:
        raise ArtifactPersistenceError("ARTIFACT_EVENT_SCHEMA_INVALID")
    event_type = _text(event.get("event_type"), "EVENT_TYPE_REQUIRED").upper()
    currentness = _known_currentness(currentness_ref)
    event_currentness = _known_currentness(
        event.get("source_currentness_ref"), "EVENT_CURRENTNESS_REQUIRED"
    )
    if event_currentness != currentness:
        raise ArtifactPersistenceError("STALE_CURRENTNESS_REBASE_REQUIRED")

    supplied_fence = _text(mirror_fence, "MIRROR_FENCE_REQUIRED")
    event_fence = _text(event.get("mirror_fence"), "EVENT_MIRROR_FENCE_REQUIRED")
    if supplied_fence != event_fence:
        raise ArtifactPersistenceError("MIRROR_FENCE_BINDING_MISMATCH")

    generation = _nonnegative_int(event.get("generation"), "EVENT_GENERATION_REQUIRED")
    prior_artifact_id = _optional_text(
        event.get("prior_artifact_id"), "PRIOR_ARTIFACT_ID_INVALID"
    )
    prior_resource_ref = _optional_text(
        event.get("prior_resource_ref"), "PRIOR_RESOURCE_REF_INVALID"
    )
    if event_type in _LINEAGE_REQUIRED_EVENT_TYPES and not (
        prior_artifact_id or prior_resource_ref
    ):
        raise ArtifactPersistenceError("PRIOR_LINEAGE_REQUIRED")

    return {
        "event_type": event_type,
        "currentness_ref": currentness,
        "mirror_fence": event_fence,
        "event_generation": generation,
        "source_prior_artifact_id": prior_artifact_id,
        "prior_resource_ref": prior_resource_ref,
    }


@dataclass(frozen=True)
class ArtifactPersistenceReceipt:
    event_id: str
    artifact_sid: str
    project_id: str
    source_surface: str
    persisted_surface: str
    resource_ref: str
    currentness_ref: str
    mirror_fence: str
    persistence_verification_ref: str
    owner_binding_status: str
    coordinate_binding_status: str
    operation: str = "UPSERT"
    sha256: str | None = None
    byte_size: int | None = None
    provider_version: str | None = None
    owner_ref: str | None = None
    coordinate_ref: str | None = None
    producer_worker_id: str = ""
    claim_id: str = ""
    claim_fence: int | None = None
    work_order_id: str = ""
    event_generation: int = 0
    source_prior_artifact_id: str | None = None
    prior_resource_ref: str | None = None
    prior_artifact_sid: str | None = None
    observed_at: str = ""
    receipt_id: str = ""
    schema: str = PERSISTENCE_RECEIPT_SCHEMA
    semantic_authority: bool = False
    coordinate_authority: bool = False
    effect_authorized: bool = False
    runtime_execution_proven: bool = False
    background_execution_claimed: bool = False

    def __post_init__(self) -> None:
        if self.schema != PERSISTENCE_RECEIPT_SCHEMA:
            raise ArtifactPersistenceError("PERSISTENCE_RECEIPT_SCHEMA_INVALID")
        for field_name, code in (
            ("event_id", "EVENT_ID_REQUIRED"),
            ("artifact_sid", "ARTIFACT_SID_REQUIRED"),
            ("project_id", "PROJECT_ID_REQUIRED"),
            ("source_surface", "SOURCE_SURFACE_REQUIRED"),
            ("persisted_surface", "PERSISTED_SURFACE_REQUIRED"),
            ("resource_ref", "RESOURCE_REF_REQUIRED"),
            ("mirror_fence", "MIRROR_FENCE_REQUIRED"),
            ("persistence_verification_ref", "PERSISTENCE_VERIFICATION_REF_REQUIRED"),
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), code))
        object.__setattr__(self, "currentness_ref", _known_currentness(self.currentness_ref))
        object.__setattr__(
            self, "event_generation", _nonnegative_int(self.event_generation, "EVENT_GENERATION_INVALID")
        )

        operation = _text(self.operation, "OPERATION_REQUIRED").upper()
        if operation not in _OPERATIONS:
            raise ArtifactPersistenceError("PERSISTENCE_OPERATION_INVALID")
        object.__setattr__(self, "operation", operation)

        owner_status = _text(
            self.owner_binding_status, "OWNER_BINDING_STATUS_REQUIRED"
        ).upper()
        if owner_status not in _OWNER_STATUSES:
            raise ArtifactPersistenceError("OWNER_BINDING_STATUS_INVALID")
        object.__setattr__(self, "owner_binding_status", owner_status)
        coordinate_status = _text(
            self.coordinate_binding_status, "COORDINATE_BINDING_STATUS_REQUIRED"
        ).upper()
        if coordinate_status not in _COORDINATE_STATUSES:
            raise ArtifactPersistenceError("COORDINATE_BINDING_STATUS_INVALID")
        object.__setattr__(self, "coordinate_binding_status", coordinate_status)

        object.__setattr__(self, "owner_ref", _optional_text(self.owner_ref, "OWNER_REF_INVALID"))
        object.__setattr__(
            self, "coordinate_ref", _optional_text(self.coordinate_ref, "COORDINATE_REF_INVALID")
        )
        object.__setattr__(
            self,
            "source_prior_artifact_id",
            _optional_text(self.source_prior_artifact_id, "SOURCE_PRIOR_ARTIFACT_ID_INVALID"),
        )
        object.__setattr__(
            self,
            "prior_resource_ref",
            _optional_text(self.prior_resource_ref, "PRIOR_RESOURCE_REF_INVALID"),
        )
        object.__setattr__(
            self,
            "prior_artifact_sid",
            _optional_text(self.prior_artifact_sid, "PRIOR_ARTIFACT_SID_INVALID"),
        )
        object.__setattr__(
            self, "provider_version", _optional_text(self.provider_version, "PROVIDER_VERSION_INVALID")
        )

        if owner_status == "BOUND" and self.owner_ref is None:
            raise ArtifactPersistenceError("BOUND_OWNER_REF_REQUIRED")
        if coordinate_status == "BOUND" and self.coordinate_ref is None:
            raise ArtifactPersistenceError("BOUND_COORDINATE_REF_REQUIRED")

        for field_name in ("producer_worker_id", "claim_id", "work_order_id", "observed_at"):
            object.__setattr__(
                self,
                field_name,
                _text(
                    getattr(self, field_name),
                    f"{field_name.upper()}_INVALID",
                    allow_empty=True,
                ),
            )

        claim_known = self.claim_id not in {"", UNKNOWN}
        if claim_known:
            if (
                isinstance(self.claim_fence, bool)
                or not isinstance(self.claim_fence, int)
                or self.claim_fence < 1
            ):
                raise ArtifactPersistenceError("CLAIM_FENCE_REQUIRED")
        elif self.claim_fence is not None:
            if self.claim_id == UNKNOWN:
                raise ArtifactPersistenceError("CLAIM_FENCE_FOR_UNKNOWN_CLAIM")
            raise ArtifactPersistenceError("CLAIM_FENCE_WITHOUT_CLAIM")

        if operation == "UPSERT":
            if self.sha256 is None or self.byte_size is None:
                raise ArtifactPersistenceError("UPSERT_IDENTITY_EVIDENCE_REQUIRED")
            digest = _sha256_text(self.sha256, "SHA256_INVALID")
            object.__setattr__(self, "sha256", digest)
            _nonnegative_int(self.byte_size, "BYTE_SIZE_INVALID")
            expected_sid = f"artifact-sha256-{digest}"
            if self.artifact_sid != expected_sid:
                raise ArtifactPersistenceError("ARTIFACT_SID_HASH_BINDING_MISMATCH")
            if self.provider_version is None:
                raise ArtifactPersistenceError("PROVIDER_VERSION_REQUIRED")
        else:
            if self.prior_artifact_sid is None:
                raise ArtifactPersistenceError("TOMBSTONE_PRIOR_ARTIFACT_REQUIRED")
            if self.artifact_sid != self.prior_artifact_sid:
                raise ArtifactPersistenceError("TOMBSTONE_ARTIFACT_BINDING_MISMATCH")
            if self.sha256 is not None or self.byte_size is not None:
                raise ArtifactPersistenceError("TOMBSTONE_MUST_NOT_CLAIM_BYTES")

        for field_name in (
            "semantic_authority",
            "coordinate_authority",
            "effect_authorized",
            "runtime_execution_proven",
            "background_execution_claimed",
        ):
            if (
                _strict_bool(
                    getattr(self, field_name), f"{field_name.upper()}_BOOLEAN_REQUIRED"
                )
                is not False
            ):
                raise ArtifactPersistenceError("PERSISTENCE_RECEIPT_AUTHORITY_WIDENING")

        expected = self.compute_receipt_id()
        supplied = _text(self.receipt_id, "RECEIPT_ID_INVALID", allow_empty=True)
        if supplied and supplied != expected:
            raise ArtifactPersistenceError("RECEIPT_ID_BINDING_MISMATCH")
        object.__setattr__(self, "receipt_id", expected)

    def logical_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "event_id": self.event_id,
            "artifact_sid": self.artifact_sid,
            "project_id": self.project_id,
            "source_surface": self.source_surface,
            "persisted_surface": self.persisted_surface,
            "resource_ref": self.resource_ref,
            "currentness_ref": self.currentness_ref,
            "mirror_fence": self.mirror_fence,
            "persistence_verification_ref": self.persistence_verification_ref,
            "owner_binding_status": self.owner_binding_status,
            "coordinate_binding_status": self.coordinate_binding_status,
            "operation": self.operation,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "provider_version": self.provider_version,
            "owner_ref": self.owner_ref,
            "coordinate_ref": self.coordinate_ref,
            "producer_worker_id": self.producer_worker_id,
            "claim_id": self.claim_id,
            "claim_fence": self.claim_fence,
            "work_order_id": self.work_order_id,
            "event_generation": self.event_generation,
            "source_prior_artifact_id": self.source_prior_artifact_id,
            "prior_resource_ref": self.prior_resource_ref,
            "prior_artifact_sid": self.prior_artifact_sid,
            "semantic_authority": False,
            "coordinate_authority": False,
            "effect_authorized": False,
            "runtime_execution_proven": False,
            "background_execution_claimed": False,
        }

    def compute_receipt_id(self) -> str:
        return f"apr-{_digest('AURA_ARTIFACT_PERSISTENCE_RECEIPT_V1', self.logical_payload())[:32]}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_persistence_receipt_from_landed_verification(
    *,
    event: Mapping[str, Any],
    identity: Mapping[str, Any],
    landed_verification: Mapping[str, Any],
    persisted_surface: str,
    currentness_ref: str,
    mirror_fence: str,
    persistence_verification_ref: str,
    owner_binding_status: str = "PENDING_EXTERNAL_OWNER",
    owner_ref: str | None = None,
    coordinate_binding_status: str = "PENDING_EXTERNAL_OWNER",
    coordinate_ref: str | None = None,
    claim_fence: int | None = None,
    observed_at: str = "",
) -> ArtifactPersistenceReceipt:
    event = _mapping(event, "EVENT_MAPPING_REQUIRED")
    identity = _mapping(identity, "IDENTITY_MAPPING_REQUIRED")
    verification = _mapping(landed_verification, "LANDED_VERIFICATION_MAPPING_REQUIRED")
    common = _event_common(
        event, currentness_ref=currentness_ref, mirror_fence=mirror_fence
    )
    if identity.get("schema") != ARTIFACT_IDENTITY_SCHEMA:
        raise ArtifactPersistenceError("ARTIFACT_IDENTITY_SCHEMA_INVALID")
    if common["event_type"] in {"DELETE", "TOMBSTONE"}:
        raise ArtifactPersistenceError("TOMBSTONE_REQUIRES_TOMBSTONE_RECEIPT")

    if verification.get("status") != "LANDED_BYTES_VERIFIED":
        raise ArtifactPersistenceError("LANDED_BYTES_VERIFICATION_REQUIRED")
    if verification.get("artifact_write_observed") is not True:
        raise ArtifactPersistenceError("ARTIFACT_WRITE_OBSERVED_REQUIRED")

    digest = _sha256_text(identity.get("sha256"), "IDENTITY_SHA256_INVALID")
    if verification.get("persisted_sha256") != digest:
        raise ArtifactPersistenceError("LANDED_HASH_IDENTITY_MISMATCH")
    byte_size = _nonnegative_int(identity.get("byte_size"), "IDENTITY_BYTE_SIZE_INVALID")
    if verification.get("byte_size") != byte_size:
        raise ArtifactPersistenceError("LANDED_SIZE_IDENTITY_MISMATCH")

    artifact_sid = _text(identity.get("artifact_sid"), "IDENTITY_ARTIFACT_SID_REQUIRED")
    if artifact_sid != f"artifact-sha256-{digest}":
        raise ArtifactPersistenceError("IDENTITY_ARTIFACT_SID_HASH_MISMATCH")

    return ArtifactPersistenceReceipt(
        event_id=_text(event.get("event_id"), "EVENT_ID_REQUIRED"),
        artifact_sid=artifact_sid,
        project_id=_text(event.get("project_id"), "PROJECT_ID_REQUIRED"),
        source_surface=_text(event.get("source_surface"), "SOURCE_SURFACE_REQUIRED"),
        persisted_surface=persisted_surface,
        resource_ref=_text(
            verification.get("destination_resource_id"), "DESTINATION_RESOURCE_REQUIRED"
        ),
        currentness_ref=common["currentness_ref"],
        mirror_fence=common["mirror_fence"],
        persistence_verification_ref=persistence_verification_ref,
        owner_binding_status=owner_binding_status,
        coordinate_binding_status=coordinate_binding_status,
        operation="UPSERT",
        sha256=digest,
        byte_size=byte_size,
        provider_version=_text(
            verification.get("destination_version_token"), "DESTINATION_VERSION_REQUIRED"
        ),
        owner_ref=owner_ref,
        coordinate_ref=coordinate_ref,
        producer_worker_id=_text(
            event.get("producer_worker_id", UNKNOWN),
            "PRODUCER_WORKER_ID_INVALID",
            allow_empty=True,
        ),
        claim_id=_text(event.get("claim_id", UNKNOWN), "CLAIM_ID_INVALID", allow_empty=True),
        claim_fence=claim_fence,
        work_order_id=_text(
            event.get("work_order_id", UNKNOWN), "WORK_ORDER_ID_INVALID", allow_empty=True
        ),
        event_generation=common["event_generation"],
        source_prior_artifact_id=common["source_prior_artifact_id"],
        prior_resource_ref=common["prior_resource_ref"],
        observed_at=observed_at,
    )


def build_tombstone_receipt(
    *,
    event: Mapping[str, Any],
    artifact_sid: str,
    persisted_surface: str,
    resource_ref: str,
    currentness_ref: str,
    mirror_fence: str,
    persistence_verification_ref: str,
    owner_binding_status: str = "PENDING_EXTERNAL_OWNER",
    owner_ref: str | None = None,
    coordinate_binding_status: str = "PENDING_EXTERNAL_OWNER",
    coordinate_ref: str | None = None,
    claim_fence: int | None = None,
    observed_at: str = "",
) -> ArtifactPersistenceReceipt:
    event = _mapping(event, "EVENT_MAPPING_REQUIRED")
    common = _event_common(
        event, currentness_ref=currentness_ref, mirror_fence=mirror_fence
    )
    if common["event_type"] not in {"DELETE", "TOMBSTONE"}:
        raise ArtifactPersistenceError("TOMBSTONE_EVENT_REQUIRED")

    sid = _text(artifact_sid, "ARTIFACT_SID_REQUIRED")
    source_prior = common["source_prior_artifact_id"]
    if source_prior and source_prior.startswith("artifact-sha256-") and source_prior != sid:
        raise ArtifactPersistenceError("TOMBSTONE_SOURCE_ARTIFACT_MISMATCH")

    return ArtifactPersistenceReceipt(
        event_id=_text(event.get("event_id"), "EVENT_ID_REQUIRED"),
        artifact_sid=sid,
        project_id=_text(event.get("project_id"), "PROJECT_ID_REQUIRED"),
        source_surface=_text(event.get("source_surface"), "SOURCE_SURFACE_REQUIRED"),
        persisted_surface=persisted_surface,
        resource_ref=resource_ref,
        currentness_ref=common["currentness_ref"],
        mirror_fence=common["mirror_fence"],
        persistence_verification_ref=persistence_verification_ref,
        owner_binding_status=owner_binding_status,
        coordinate_binding_status=coordinate_binding_status,
        operation="TOMBSTONE",
        prior_artifact_sid=sid,
        source_prior_artifact_id=source_prior,
        prior_resource_ref=common["prior_resource_ref"],
        event_generation=common["event_generation"],
        owner_ref=owner_ref,
        coordinate_ref=coordinate_ref,
        producer_worker_id=_text(
            event.get("producer_worker_id", UNKNOWN),
            "PRODUCER_WORKER_ID_INVALID",
            allow_empty=True,
        ),
        claim_id=_text(event.get("claim_id", UNKNOWN), "CLAIM_ID_INVALID", allow_empty=True),
        claim_fence=claim_fence,
        work_order_id=_text(
            event.get("work_order_id", UNKNOWN), "WORK_ORDER_ID_INVALID", allow_empty=True
        ),
        observed_at=observed_at,
    )


def new_live_artifact_index(*, project_id: str, currentness_ref: str) -> dict[str, Any]:
    return {
        "schema": LIVE_INDEX_SCHEMA,
        "project_id": _text(project_id, "PROJECT_ID_REQUIRED"),
        "currentness_ref": _known_currentness(currentness_ref),
        "generation": 0,
        "receipts": {},
        "artifacts": {},
        "resource_heads": {},
        "semantic_authority": False,
        "coordinate_authority": False,
        "effect_authorized": False,
        "runtime_execution_proven": False,
    }


def _normalize_index(state: Mapping[str, Any]) -> dict[str, Any]:
    state = _mapping(state, "LIVE_INDEX_MAPPING_REQUIRED")
    if state.get("schema") != LIVE_INDEX_SCHEMA:
        raise ArtifactPersistenceError("LIVE_INDEX_SCHEMA_INVALID")
    out = deepcopy(dict(state))
    _text(out.get("project_id"), "PROJECT_ID_REQUIRED")
    _known_currentness(out.get("currentness_ref"))
    _nonnegative_int(out.get("generation"), "LIVE_INDEX_GENERATION_INVALID")
    for key in ("receipts", "artifacts", "resource_heads"):
        if not isinstance(out.get(key), Mapping):
            raise ArtifactPersistenceError("LIVE_INDEX_STRUCTURE_INVALID", key)
        out[key] = deepcopy(dict(out[key]))
    for field_name in (
        "semantic_authority",
        "coordinate_authority",
        "effect_authorized",
        "runtime_execution_proven",
    ):
        if out.get(field_name) is not False:
            raise ArtifactPersistenceError("LIVE_INDEX_AUTHORITY_WIDENING")
    return out


def index_revision(state: Mapping[str, Any]) -> str:
    normalized = _normalize_index(state)
    logical = {
        "schema": normalized["schema"],
        "project_id": normalized["project_id"],
        "currentness_ref": normalized["currentness_ref"],
        "generation": normalized["generation"],
        "receipt_ids": sorted(normalized["receipts"]),
        "artifacts": normalized["artifacts"],
        "resource_heads": normalized["resource_heads"],
        "semantic_authority": False,
        "coordinate_authority": False,
        "effect_authorized": False,
        "runtime_execution_proven": False,
    }
    return _digest("AURA_LIVE_ARTIFACT_INDEX_V1", logical)


def _receipt_logical_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"observed_at", "receipt_id"}
    }


def _refresh_artifact_state(entry: dict[str, Any]) -> None:
    locations = entry.get("locations", {})
    entry["state"] = (
        "LIVE"
        if any(loc.get("state") == "LIVE" for loc in locations.values())
        else "TOMBSTONED"
    )


def apply_persistence_receipt(
    state: Mapping[str, Any],
    receipt: ArtifactPersistenceReceipt,
    *,
    expected_revision: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(receipt, ArtifactPersistenceReceipt):
        raise ArtifactPersistenceError("PERSISTENCE_RECEIPT_OBJECT_REQUIRED")
    current = _normalize_index(state)
    observed_revision = index_revision(current)
    if _text(expected_revision, "EXPECTED_REVISION_REQUIRED") != observed_revision:
        raise ArtifactPersistenceError("LIVE_INDEX_STALE_CAS")
    if receipt.project_id != current["project_id"]:
        raise ArtifactPersistenceError("LIVE_INDEX_PROJECT_MISMATCH")
    if receipt.currentness_ref != current["currentness_ref"]:
        raise ArtifactPersistenceError("STALE_CURRENTNESS_REBASE_REQUIRED")

    existing = current["receipts"].get(receipt.receipt_id)
    if existing is not None:
        if _receipt_logical_from_row(existing) == receipt.logical_payload():
            return current, {
                "decision": "IDEMPOTENT_REPLAY",
                "receipt_id": receipt.receipt_id,
                "before_revision": observed_revision,
                "after_revision": observed_revision,
                "state_changed": False,
                "effect_authorized": False,
                "runtime_execution_proven": False,
            }
        raise ArtifactPersistenceError("PERSISTENCE_RECEIPT_ID_COLLISION")

    next_state = deepcopy(current)
    next_state["receipts"][receipt.receipt_id] = receipt.to_dict()
    location_key = f"{receipt.persisted_surface}::{receipt.resource_ref}"

    if receipt.operation == "UPSERT":
        previous_sid = next_state["resource_heads"].get(location_key)
        if previous_sid and previous_sid != receipt.artifact_sid:
            old = next_state["artifacts"].get(previous_sid)
            if old and location_key in old.get("locations", {}):
                old["locations"][location_key]["state"] = "SUPERSEDED"
                old["locations"][location_key]["superseded_by_receipt_id"] = receipt.receipt_id
                _refresh_artifact_state(old)

        entry = next_state["artifacts"].setdefault(
            receipt.artifact_sid,
            {
                "artifact_sid": receipt.artifact_sid,
                "sha256": receipt.sha256,
                "byte_size": receipt.byte_size,
                "locations": {},
                "history_receipt_ids": [],
                "state": "LIVE",
            },
        )
        if entry.get("sha256") != receipt.sha256 or entry.get("byte_size") != receipt.byte_size:
            raise ArtifactPersistenceError("ARTIFACT_IDENTITY_MUTATION_REFUSED")
        entry["locations"][location_key] = {
            "persisted_surface": receipt.persisted_surface,
            "resource_ref": receipt.resource_ref,
            "provider_version": receipt.provider_version,
            "state": "LIVE",
            "last_receipt_id": receipt.receipt_id,
            "owner_binding_status": receipt.owner_binding_status,
            "owner_ref": receipt.owner_ref,
            "coordinate_binding_status": receipt.coordinate_binding_status,
            "coordinate_ref": receipt.coordinate_ref,
            "mirror_fence": receipt.mirror_fence,
            "event_generation": receipt.event_generation,
        }
        entry["history_receipt_ids"].append(receipt.receipt_id)
        _refresh_artifact_state(entry)
        next_state["resource_heads"][location_key] = receipt.artifact_sid
    else:
        entry = next_state["artifacts"].setdefault(
            receipt.artifact_sid,
            {
                "artifact_sid": receipt.artifact_sid,
                "sha256": None,
                "byte_size": None,
                "locations": {},
                "history_receipt_ids": [],
                "state": "TOMBSTONED",
            },
        )
        location = entry["locations"].setdefault(
            location_key,
            {
                "persisted_surface": receipt.persisted_surface,
                "resource_ref": receipt.resource_ref,
                "provider_version": None,
                "owner_binding_status": receipt.owner_binding_status,
                "owner_ref": receipt.owner_ref,
                "coordinate_binding_status": receipt.coordinate_binding_status,
                "coordinate_ref": receipt.coordinate_ref,
                "mirror_fence": receipt.mirror_fence,
                "event_generation": receipt.event_generation,
            },
        )
        location["state"] = "TOMBSTONED"
        location["last_receipt_id"] = receipt.receipt_id
        entry["history_receipt_ids"].append(receipt.receipt_id)
        if next_state["resource_heads"].get(location_key) == receipt.artifact_sid:
            next_state["resource_heads"].pop(location_key, None)
        _refresh_artifact_state(entry)

    next_state["generation"] += 1
    after_revision = index_revision(next_state)
    return next_state, {
        "decision": "PERSISTENCE_APPLIED",
        "receipt_id": receipt.receipt_id,
        "before_revision": observed_revision,
        "after_revision": after_revision,
        "state_changed": True,
        "effect_authorized": False,
        "runtime_execution_proven": False,
    }


def artifact_available_event(
    receipt: ArtifactPersistenceReceipt,
    *,
    live_index_revision: str,
) -> dict[str, Any]:
    revision = _text(live_index_revision, "LIVE_INDEX_REVISION_REQUIRED")
    event_type = (
        "ARTIFACT_AVAILABLE" if receipt.operation == "UPSERT" else "ARTIFACT_TOMBSTONED"
    )
    body = {
        "schema": ARTIFACT_AVAILABLE_SCHEMA,
        "event_type": event_type,
        "project_id": receipt.project_id,
        "artifact_sid": receipt.artifact_sid,
        "persistence_receipt_id": receipt.receipt_id,
        "live_index_revision": revision,
        "currentness_ref": receipt.currentness_ref,
        "persisted_surface": receipt.persisted_surface,
        "resource_ref": receipt.resource_ref,
        "source_event_id": receipt.event_id,
        "source_event_generation": receipt.event_generation,
        "mirror_fence": receipt.mirror_fence,
        "owner_binding_status": receipt.owner_binding_status,
        "owner_ref": receipt.owner_ref,
        "coordinate_binding_status": receipt.coordinate_binding_status,
        "coordinate_ref": receipt.coordinate_ref,
        "delivery_intent_only": True,
        "execution_authorized": False,
        "effect_authorized": False,
        "provider_calls_authorized": False,
        "runtime_execution_proven": False,
        "background_execution_claimed": False,
    }
    body["event_id"] = f"aae-{_digest('AURA_ARTIFACT_AVAILABLE_EVENT_V1', body)[:32]}"
    return body
