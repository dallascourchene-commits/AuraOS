"""Immutable P6.2 QDKT dual-read compatibility evidence."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import Enum
import math
from typing import Any

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
from aura_qdkt_observations import QDKTObservation
from aura_qdkt_projection_types import ProjectedQDKTEvent

QDKT_COMPATIBILITY_VERSION = "AURA_QDKT_COMPATIBILITY_P6_2"
QDKT_EXECUTION_MODE = "OPT_IN_DUAL_READ"
QDKT_COMPATIBILITY_AUTHORITY = False


class QDKTDualReadStatus(str, Enum):
    VERIFIED_DUAL_READ = "VERIFIED_DUAL_READ"
    ADVISORY_ONLY = "ADVISORY_ONLY"
    UNAVAILABLE = "UNAVAILABLE"
    MISMATCHED = "MISMATCHED"


@dataclass(frozen=True)
class QDKTDualReadEvidence:
    status: QDKTDualReadStatus | str
    reason: str
    legacy_result: Mapping[str, Any]
    expected_observation: QDKTObservation | None
    matched_event: ProjectedQDKTEvent | None
    projection_digest: str | None
    finding_codes: tuple[str, ...]
    expected_event_id: str = ""
    freshness_floor: float | None = None
    proposal_only: bool = True
    reproducible: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    qdkt_compatibility_authority: bool = QDKT_COMPATIBILITY_AUTHORITY
    execution_mode: str = QDKT_EXECUTION_MODE
    version: str = QDKT_COMPATIBILITY_VERSION

    def __post_init__(self) -> None:
        try:
            status = (
                self.status
                if isinstance(self.status, QDKTDualReadStatus)
                else QDKTDualReadStatus(str(self.status))
            )
        except ValueError as exc:
            raise ValueError("dual-read status is invalid") from exc
        if type(self.reason) is not str or not self.reason.strip():
            raise ValueError("reason must not be empty")
        if not isinstance(self.legacy_result, Mapping):
            raise ValueError("legacy_result must be a mapping")
        if self.expected_observation is not None and not isinstance(
            self.expected_observation, QDKTObservation
        ):
            raise ValueError("expected_observation is invalid")
        if self.matched_event is not None and not isinstance(
            self.matched_event, ProjectedQDKTEvent
        ):
            raise ValueError("matched_event is invalid")
        if self.projection_digest is not None and (
            type(self.projection_digest) is not str
            or len(self.projection_digest) != 32
        ):
            raise ValueError("projection_digest must be a stable BLAKE2 digest")
        if type(self.finding_codes) is not tuple or any(
            type(item) is not str or not item for item in self.finding_codes
        ):
            raise ValueError("finding_codes must be a tuple of non-empty strings")
        if len(self.finding_codes) != len(set(self.finding_codes)):
            raise ValueError("finding_codes must not contain duplicates")
        if type(self.expected_event_id) is not str:
            raise ValueError("expected_event_id must be a string")
        if self.freshness_floor is not None and (
            isinstance(self.freshness_floor, bool)
            or not isinstance(self.freshness_floor, (int, float))
            or not math.isfinite(float(self.freshness_floor))
        ):
            raise ValueError("freshness_floor must be finite")
        if (
            self.proposal_only is not True
            or self.reproducible is not False
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.qdkt_compatibility_authority is not False
            or self.execution_mode != QDKT_EXECUTION_MODE
            or self.version != QDKT_COMPATIBILITY_VERSION
        ):
            raise ValueError("QDKT compatibility authority boundary changed")

        verified = status is QDKTDualReadStatus.VERIFIED_DUAL_READ
        if verified:
            if self.expected_observation is None or self.matched_event is None:
                raise ValueError("verified dual-read evidence is incomplete")
            if self.finding_codes:
                raise ValueError("verified dual-read evidence has findings")
            if self.matched_event.observation_id != self.expected_observation.observation_id:
                raise ValueError("verified event observation identity disagrees")
            if self.matched_event.payload_digest != self.expected_observation.digest:
                raise ValueError("verified event payload digest disagrees")
            if self.expected_event_id and self.matched_event.event_id != self.expected_event_id:
                raise ValueError("verified event ID disagrees")
            if (
                self.freshness_floor is not None
                and self.matched_event.created_at < float(self.freshness_floor)
            ):
                raise ValueError("verified event is stale")
        else:
            if self.matched_event is not None:
                raise ValueError("non-verified evidence must not carry a matched event")
        if status is QDKTDualReadStatus.MISMATCHED and not self.finding_codes:
            raise ValueError("mismatched evidence requires a finding code")
        if status is QDKTDualReadStatus.ADVISORY_ONLY and self.expected_observation is None:
            raise ValueError("advisory evidence requires a valid observation")
        if status is QDKTDualReadStatus.UNAVAILABLE and self.reason == "verified":
            raise ValueError("unavailable evidence reason is invalid")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason", self.reason.strip())
        if self.freshness_floor is not None:
            object.__setattr__(self, "freshness_floor", float(self.freshness_floor))

    @property
    def legacy_value(self) -> Mapping[str, Any]:
        """Return the exact caller-supplied legacy mapping unchanged."""
        return self.legacy_result

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        value["legacy_result"] = dict(self.legacy_result)
        value["expected_observation"] = (
            self.expected_observation.to_dict()
            if self.expected_observation is not None
            else None
        )
        value["matched_event"] = (
            self.matched_event.to_dict() if self.matched_event is not None else None
        )
        value["finding_codes"] = list(self.finding_codes)
        return value
