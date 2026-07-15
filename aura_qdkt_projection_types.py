"""Immutable evidence records for read-only QDKT event projection."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
from typing import Any

from aura_event_contracts import stable_digest

QDKT_PROJECTOR_VERSION = "AURA_QDKT_PROJECTOR_P6_1"


class QDKTProjectionFindingCode(str, Enum):
    EVENT_LOG_READ_FAILED = "EVENT_LOG_READ_FAILED"
    INVALID_EVENT_RECORD = "INVALID_EVENT_RECORD"
    NONCANONICAL_EVENT_RECORD = "NONCANONICAL_EVENT_RECORD"
    EVENT_ID_MISMATCH = "EVENT_ID_MISMATCH"
    ENVELOPE_MISMATCH = "ENVELOPE_MISMATCH"
    DUPLICATE_EVENT_ID = "DUPLICATE_EVENT_ID"
    CONFLICTING_DUPLICATE_EVENT = "CONFLICTING_DUPLICATE_EVENT"
    DUPLICATE_PARENT_REF = "DUPLICATE_PARENT_REF"
    DUPLICATE_EVIDENCE_REF = "DUPLICATE_EVIDENCE_REF"
    NON_PROPOSAL_EVENT = "NON_PROPOSAL_EVENT"
    WRONG_EVENT_CONTRACT = "WRONG_EVENT_CONTRACT"
    UNSAFE_PAYLOAD_REF = "UNSAFE_PAYLOAD_REF"
    MISSING_SIDECAR = "MISSING_SIDECAR"
    MALFORMED_SIDECAR = "MALFORMED_SIDECAR"
    NONCANONICAL_SIDECAR = "NONCANONICAL_SIDECAR"
    PAYLOAD_DIGEST_MISMATCH = "PAYLOAD_DIGEST_MISMATCH"
    PAYLOAD_REF_MISMATCH = "PAYLOAD_REF_MISMATCH"
    OBSERVATION_EVENT_MISMATCH = "OBSERVATION_EVENT_MISMATCH"
    MISSING_PARENT = "MISSING_PARENT"
    OUT_OF_ORDER = "OUT_OF_ORDER"


@dataclass(frozen=True)
class QDKTProjectionFinding:
    code: QDKTProjectionFindingCode | str
    message: str
    event_ids: tuple[str, ...] = ()
    blocking: bool = True

    def __post_init__(self) -> None:
        try:
            code = (
                self.code
                if isinstance(self.code, QDKTProjectionFindingCode)
                else QDKTProjectionFindingCode(str(self.code))
            )
        except ValueError as exc:
            raise ValueError("unknown QDKT projection finding code") from exc
        if type(self.message) is not str or not self.message.strip():
            raise ValueError("finding message must not be empty")
        if isinstance(self.event_ids, (str, bytes, bytearray)):
            raise ValueError("finding event_ids must be a sequence")
        event_ids = tuple(str(item).strip() for item in self.event_ids)
        if any(not item for item in event_ids):
            raise ValueError("finding event_ids must not contain empty values")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("finding event_ids must not contain duplicates")
        if type(self.blocking) is not bool:
            raise ValueError("finding blocking must be a boolean")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", self.message.strip())
        object.__setattr__(self, "event_ids", event_ids)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["code"] = self.code.value
        value["event_ids"] = list(self.event_ids)
        return value


@dataclass(frozen=True)
class ProjectedQDKTEvent:
    event_id: str
    observation_id: str
    payload_ref: str
    payload_digest: str
    trace_id: str
    parent_event_ids: tuple[str, ...]
    created_at: float

    def __post_init__(self) -> None:
        for field_name in (
            "event_id",
            "observation_id",
            "payload_ref",
            "payload_digest",
            "trace_id",
        ):
            value = getattr(self, field_name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if isinstance(self.parent_event_ids, (str, bytes, bytearray)):
            raise ValueError("parent_event_ids must be a sequence")
        parents = tuple(str(item).strip() for item in self.parent_event_ids)
        if any(not item for item in parents) or len(parents) != len(set(parents)):
            raise ValueError("parent_event_ids must be unique non-empty strings")
        if isinstance(self.created_at, bool) or not math.isfinite(float(self.created_at)):
            raise ValueError("created_at must be finite")
        object.__setattr__(self, "parent_event_ids", parents)
        object.__setattr__(self, "created_at", float(self.created_at))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["parent_event_ids"] = list(self.parent_event_ids)
        return value


@dataclass(frozen=True)
class QDKTProjectionReport:
    events: tuple[ProjectedQDKTEvent, ...]
    findings: tuple[QDKTProjectionFinding, ...]
    qdkt_event_count: int
    ignored_non_qdkt_events: int
    version: str = QDKT_PROJECTOR_VERSION

    def __post_init__(self) -> None:
        if not all(isinstance(item, ProjectedQDKTEvent) for item in self.events):
            raise ValueError("events contains an invalid projected event")
        if not all(isinstance(item, QDKTProjectionFinding) for item in self.findings):
            raise ValueError("findings contains an invalid finding")
        event_ids = [item.event_id for item in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("projected events must have unique event IDs")
        for field_name in ("qdkt_event_count", "ignored_non_qdkt_events"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.version != QDKT_PROJECTOR_VERSION:
            raise ValueError("unsupported QDKT projector version")

    @property
    def integrity_complete(self) -> bool:
        return not any(item.blocking for item in self.findings)

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [item.to_dict() for item in self.events],
            "findings": [item.to_dict() for item in self.findings],
            "qdkt_event_count": self.qdkt_event_count,
            "ignored_non_qdkt_events": self.ignored_non_qdkt_events,
            "version": self.version,
            "integrity_complete": self.integrity_complete,
        }
