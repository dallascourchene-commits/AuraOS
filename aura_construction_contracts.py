"""Minimal immutable SCO Construction domain contracts for AuraOS.

These contracts represent digital claims and evidence only. They never authorize
physical work, certify safety or engineering, release payment, control access,
or replace owner, professional, contractual, legal, regulatory, or community
authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
import re
from typing import Any, Iterable

from aura_event_contracts import (
    ActorType,
    AuraEventEnvelope,
    DIKWPStage,
    MeasurementClass,
    stable_digest,
    stable_id,
)

CONSTRUCTION_CONTRACTS_VERSION = "AURA_CONSTRUCTION_CONTRACTS_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
PROPOSAL_ONLY = True
GENESIS_CHAIN_DIGEST = "GENESIS"
_HEX = re.compile(r"^[0-9a-f]+$")


class ConstructionRecordKind(str, Enum):
    CLAIM = "CLAIM"
    EVIDENCE = "EVIDENCE"


class ConstructionEvidenceClass(str, Enum):
    OWNER_RECORD = "OWNER_RECORD"
    CONTRACTOR_RECORD = "CONTRACTOR_RECORD"
    PROFESSIONAL_RECORD = "PROFESSIONAL_RECORD"
    INSPECTION = "INSPECTION"
    TEST_RESULT = "TEST_RESULT"
    DOCUMENT = "DOCUMENT"
    PHOTO = "PHOTO"
    SENSOR = "SENSOR"
    LOCATION = "LOCATION"
    OTHER = "OTHER"


class ConstructionAuthorityClass(str, Enum):
    NONE = "NONE"
    INFORMATIVE = "INFORMATIVE"
    OWNER = "OWNER"
    CONTRACTOR = "CONTRACTOR"
    PROFESSIONAL = "PROFESSIONAL"
    REGULATORY = "REGULATORY"
    LEGAL = "LEGAL"
    COMMUNITY = "COMMUNITY"


class ConstructionPrivacyClass(str, Enum):
    PUBLIC = "PUBLIC"
    PROJECT = "PROJECT"
    RESTRICTED = "RESTRICTED"
    SENSITIVE = "SENSITIVE"


def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    normalized = " ".join(value.split())
    if normalized != value:
        raise ValueError(f"{name} must be normalized")
    return value


def _normalized_text_input(value: Any, name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _scope_component(value: Any, name: str) -> str:
    normalized = _text(value, name)
    if any(token in normalized for token in ("/", "\\", "*", "|")):
        raise ValueError(f"{name} contains a reserved scope delimiter")
    return normalized


def _chain_reference(value: Any, name: str, *, genesis_allowed: bool) -> str:
    if genesis_allowed and value == GENESIS_CHAIN_DIGEST:
        return GENESIS_CHAIN_DIGEST
    return _digest(value, name)


def _tuple_strings(value: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    normalized = tuple(_text(item, f"{name}[]") for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    if normalized != tuple(sorted(normalized)):
        raise ValueError(f"{name} must use canonical sorted order")
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _sequence_input(value: Any, name: str) -> tuple[Any, ...]:
    if type(value) not in {list, tuple}:
        raise ValueError(f"{name} must be a list or tuple")
    return tuple(value)


def _normalized_unique(values: Iterable[Any], name: str) -> tuple[str, ...]:
    items = _sequence_input(values, name)
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if type(raw) is not str:
            raise ValueError(f"{name} contains a non-string value")
        normalized = " ".join(raw.split())
        if not normalized:
            raise ValueError(f"{name} contains an empty value")
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate or normalization-colliding values")
        seen.add(normalized)
        result.append(normalized)
    return tuple(sorted(result))


def _enum_value(value: Any, enum_type: type[Enum], name: str) -> str:
    if isinstance(value, enum_type):
        raw = value.value
    elif type(value) is str:
        raw = value
    else:
        raise ValueError(f"{name} must be a string or {enum_type.__name__}")
    permitted = {item.value for item in enum_type}
    if raw not in permitted:
        raise ValueError(f"unknown {name}: {raw}")
    return raw


def _digest(value: Any, name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a hexadecimal digest")
    normalized = value.lower()
    if len(normalized) not in {32, 64} or _HEX.fullmatch(normalized) is None:
        raise ValueError(f"{name} must be a 32- or 64-character hexadecimal digest")
    if value != normalized:
        raise ValueError(f"{name} must use canonical lowercase hexadecimal")
    return normalized


def _probability(value: Any, name: str) -> float | None:
    if value is None:
        return None
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between zero and one")
    return number


def _timestamp(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _require_canonical_float(value: Any, name: str, *, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(f"{name} must be a canonical finite float")


def _require_canonical_enum(value: Any, enum_type: type[Enum], name: str) -> str:
    normalized = _enum_value(value, enum_type, name)
    if type(value) is not str or value != normalized:
        raise ValueError(f"{name} must be stored as its canonical string value")
    return normalized


def _validate_boundaries(*, proposal_only: bool, patch_authority: str, vsa_patch_authority: bool) -> None:
    if proposal_only is not True:
        raise ValueError("construction records must remain proposal-only")
    if patch_authority != PATCH_AUTHORITY or vsa_patch_authority is not False:
        raise ValueError("construction patch-authority boundary was modified")


@dataclass(frozen=True)
class ConstructionScope:
    project_id: str
    zone_id: str = ""
    work_package_id: str = ""

    def __post_init__(self) -> None:
        _scope_component(self.project_id, "scope.project_id")
        if type(self.zone_id) is not str:
            raise ValueError("scope.zone_id must be a string")
        if type(self.work_package_id) is not str:
            raise ValueError("scope.work_package_id must be a string")
        if self.zone_id:
            _scope_component(self.zone_id, "scope.zone_id")
        if self.work_package_id:
            _scope_component(self.work_package_id, "scope.work_package_id")
            if not self.zone_id:
                raise ValueError("scope.work_package_id requires scope.zone_id")

    @property
    def scope_key(self) -> str:
        return "/".join((self.project_id, self.zone_id or "*", self.work_package_id or "*"))

    @property
    def policy_scope(self) -> str:
        return "/".join(
            component
            for component in (
                "construction",
                self.project_id,
                self.zone_id,
                self.work_package_id,
            )
            if component
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionScope":
        data = dict(value)
        return cls(
            project_id=data.get("project_id"),
            zone_id=data.get("zone_id", ""),
            work_package_id=data.get("work_package_id", ""),
        )


@dataclass(frozen=True)
class ConstructionEvidence:
    evidence_id: str
    evidence_digest: str
    scope: ConstructionScope
    subject_id: str
    evidence_class: str
    source_ref: str
    payload_digest: str
    measurement_class: str
    confidence: float | None
    authority_class: str
    privacy_class: str
    consent_refs: tuple[str, ...]
    observed_at: float
    expires_at: float | None
    version: str = CONSTRUCTION_CONTRACTS_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_CONTRACTS_VERSION:
            raise ValueError("unsupported construction evidence version")
        if type(self.scope) is not ConstructionScope:
            raise ValueError("evidence scope must be a ConstructionScope")
        _text(self.subject_id, "evidence.subject_id")
        evidence_class = _require_canonical_enum(
            self.evidence_class, ConstructionEvidenceClass, "evidence_class"
        )
        _text(self.source_ref, "evidence.source_ref")
        _digest(self.payload_digest, "evidence.payload_digest")
        _require_canonical_enum(
            self.measurement_class, MeasurementClass, "measurement_class"
        )
        _require_canonical_float(
            self.confidence, "evidence.confidence", allow_none=True
        )
        _probability(self.confidence, "evidence.confidence")
        authority = _require_canonical_enum(
            self.authority_class, ConstructionAuthorityClass, "authority_class"
        )
        privacy = _require_canonical_enum(
            self.privacy_class, ConstructionPrivacyClass, "privacy_class"
        )
        _tuple_strings(self.consent_refs, "evidence.consent_refs")
        _require_canonical_float(self.observed_at, "evidence.observed_at")
        _require_canonical_float(
            self.expires_at, "evidence.expires_at", allow_none=True
        )
        observed = _timestamp(self.observed_at, "evidence.observed_at")
        if self.expires_at is not None and _timestamp(self.expires_at, "evidence.expires_at") <= observed:
            raise ValueError("evidence expires_at must be later than observed_at")
        if privacy == ConstructionPrivacyClass.SENSITIVE.value and not self.consent_refs:
            raise ValueError("sensitive evidence requires consent references")
        if (
            evidence_class
            in {
                ConstructionEvidenceClass.SENSOR.value,
                ConstructionEvidenceClass.LOCATION.value,
            }
            and authority not in {
            ConstructionAuthorityClass.NONE.value,
                ConstructionAuthorityClass.INFORMATIVE.value,
            }
        ):
            raise ValueError(
                "sensor and location evidence cannot carry dispositive authority"
            )
        _validate_boundaries(
            proposal_only=self.proposal_only,
            patch_authority=self.patch_authority,
            vsa_patch_authority=self.vsa_patch_authority,
        )
        payload = self._identity_payload()
        if self.evidence_digest != stable_digest(payload):
            raise ValueError("evidence digest does not match its content")
        if self.evidence_id != stable_id("construction-evidence", payload):
            raise ValueError("evidence ID does not match its content")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionEvidence":
        data = dict(value)
        return cls(
            evidence_id=data.get("evidence_id"),
            evidence_digest=data.get("evidence_digest"),
            scope=ConstructionScope.from_dict(dict(data.get("scope") or {})),
            subject_id=data.get("subject_id"),
            evidence_class=data.get("evidence_class"),
            source_ref=data.get("source_ref"),
            payload_digest=data.get("payload_digest"),
            measurement_class=data.get("measurement_class"),
            confidence=(
                data.get("confidence")
            ),
            authority_class=data.get("authority_class"),
            privacy_class=data.get("privacy_class"),
            consent_refs=_sequence_input(
                data.get("consent_refs", ()), "evidence.consent_refs"
            ),
            observed_at=data.get("observed_at"),
            expires_at=(
                data.get("expires_at")
            ),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    @classmethod
    def create(
        cls,
        *,
        scope: ConstructionScope,
        subject_id: str,
        evidence_class: str | ConstructionEvidenceClass,
        source_ref: str,
        payload_digest: str,
        measurement_class: str | MeasurementClass,
        confidence: float | None,
        authority_class: str | ConstructionAuthorityClass,
        privacy_class: str | ConstructionPrivacyClass,
        consent_refs: Iterable[str] = (),
        observed_at: float,
        expires_at: float | None = None,
    ) -> "ConstructionEvidence":
        if type(scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        values = {
            "scope": scope,
            "subject_id": _normalized_text_input(subject_id, "subject_id"),
            "evidence_class": _enum_value(evidence_class, ConstructionEvidenceClass, "evidence_class"),
            "source_ref": _normalized_text_input(source_ref, "source_ref"),
            "payload_digest": _digest(payload_digest, "payload_digest"),
            "measurement_class": _enum_value(measurement_class, MeasurementClass, "measurement_class"),
            "confidence": _probability(confidence, "confidence"),
            "authority_class": _enum_value(authority_class, ConstructionAuthorityClass, "authority_class"),
            "privacy_class": _enum_value(privacy_class, ConstructionPrivacyClass, "privacy_class"),
            "consent_refs": _normalized_unique(consent_refs, "consent_refs"),
            "observed_at": _timestamp(observed_at, "observed_at"),
            "expires_at": None if expires_at is None else _timestamp(expires_at, "expires_at"),
            "version": CONSTRUCTION_CONTRACTS_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = cls._payload_from_values(values)
        return cls(
            evidence_id=stable_id("construction-evidence", payload),
            evidence_digest=stable_digest(payload),
            **values,
        )

    @staticmethod
    def _payload_from_values(values: dict[str, Any]) -> dict[str, Any]:
        return {
            **values,
            "scope": values["scope"].to_dict(),
            "consent_refs": list(values["consent_refs"]),
        }

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("evidence_id")
        data.pop("evidence_digest")
        return data

    @property
    def state_key(self) -> str:
        return stable_id(
            "construction-evidence-state",
            {
                "scope": self.scope.to_dict(),
                "subject_id": self.subject_id,
                "evidence_class": self.evidence_class,
                "source_ref": self.source_ref,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConstructionClaim:
    claim_id: str
    claim_digest: str
    scope: ConstructionScope
    subject_id: str
    predicate: str
    value_digest: str
    claimant_id: str
    evidence_refs: tuple[str, ...]
    measurement_class: str
    confidence: float | None
    authority_class: str
    privacy_class: str
    consent_refs: tuple[str, ...]
    created_at: float
    expires_at: float | None
    version: str = CONSTRUCTION_CONTRACTS_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_CONTRACTS_VERSION:
            raise ValueError("unsupported construction claim version")
        if type(self.scope) is not ConstructionScope:
            raise ValueError("claim scope must be a ConstructionScope")
        _text(self.subject_id, "claim.subject_id")
        _text(self.predicate, "claim.predicate")
        _digest(self.value_digest, "claim.value_digest")
        _text(self.claimant_id, "claim.claimant_id")
        _tuple_strings(self.evidence_refs, "claim.evidence_refs")
        _require_canonical_enum(
            self.measurement_class, MeasurementClass, "measurement_class"
        )
        _require_canonical_float(self.confidence, "claim.confidence", allow_none=True)
        _probability(self.confidence, "claim.confidence")
        authority = _require_canonical_enum(
            self.authority_class, ConstructionAuthorityClass, "authority_class"
        )
        privacy = _require_canonical_enum(
            self.privacy_class, ConstructionPrivacyClass, "privacy_class"
        )
        _tuple_strings(self.consent_refs, "claim.consent_refs")
        _require_canonical_float(self.created_at, "claim.created_at")
        _require_canonical_float(self.expires_at, "claim.expires_at", allow_none=True)
        created = _timestamp(self.created_at, "claim.created_at")
        if self.expires_at is not None and _timestamp(self.expires_at, "claim.expires_at") <= created:
            raise ValueError("claim expires_at must be later than created_at")
        if privacy == ConstructionPrivacyClass.SENSITIVE.value and not self.consent_refs:
            raise ValueError("sensitive claims require consent references")
        if authority in {
            ConstructionAuthorityClass.PROFESSIONAL.value,
            ConstructionAuthorityClass.REGULATORY.value,
            ConstructionAuthorityClass.LEGAL.value,
        } and not self.evidence_refs:
            raise ValueError("high-authority claims require exact evidence references")
        _validate_boundaries(
            proposal_only=self.proposal_only,
            patch_authority=self.patch_authority,
            vsa_patch_authority=self.vsa_patch_authority,
        )
        payload = self._identity_payload()
        if self.claim_digest != stable_digest(payload):
            raise ValueError("claim digest does not match its content")
        if self.claim_id != stable_id("construction-claim", payload):
            raise ValueError("claim ID does not match its content")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionClaim":
        data = dict(value)
        return cls(
            claim_id=data.get("claim_id"),
            claim_digest=data.get("claim_digest"),
            scope=ConstructionScope.from_dict(dict(data.get("scope") or {})),
            subject_id=data.get("subject_id"),
            predicate=data.get("predicate"),
            value_digest=data.get("value_digest"),
            claimant_id=data.get("claimant_id"),
            evidence_refs=_sequence_input(
                data.get("evidence_refs", ()), "claim.evidence_refs"
            ),
            measurement_class=data.get("measurement_class"),
            confidence=(
                data.get("confidence")
            ),
            authority_class=data.get("authority_class"),
            privacy_class=data.get("privacy_class"),
            consent_refs=_sequence_input(
                data.get("consent_refs", ()), "claim.consent_refs"
            ),
            created_at=data.get("created_at"),
            expires_at=(
                data.get("expires_at")
            ),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    @classmethod
    def create(
        cls,
        *,
        scope: ConstructionScope,
        subject_id: str,
        predicate: str,
        value_digest: str,
        claimant_id: str,
        evidence_refs: Iterable[str],
        measurement_class: str | MeasurementClass,
        confidence: float | None,
        authority_class: str | ConstructionAuthorityClass,
        privacy_class: str | ConstructionPrivacyClass,
        consent_refs: Iterable[str] = (),
        created_at: float,
        expires_at: float | None = None,
    ) -> "ConstructionClaim":
        if type(scope) is not ConstructionScope:
            raise ValueError("scope must be an exact ConstructionScope")
        values = {
            "scope": scope,
            "subject_id": _normalized_text_input(subject_id, "subject_id"),
            "predicate": _normalized_text_input(predicate, "predicate"),
            "value_digest": _digest(value_digest, "value_digest"),
            "claimant_id": _normalized_text_input(claimant_id, "claimant_id"),
            "evidence_refs": _normalized_unique(evidence_refs, "evidence_refs"),
            "measurement_class": _enum_value(measurement_class, MeasurementClass, "measurement_class"),
            "confidence": _probability(confidence, "confidence"),
            "authority_class": _enum_value(authority_class, ConstructionAuthorityClass, "authority_class"),
            "privacy_class": _enum_value(privacy_class, ConstructionPrivacyClass, "privacy_class"),
            "consent_refs": _normalized_unique(consent_refs, "consent_refs"),
            "created_at": _timestamp(created_at, "created_at"),
            "expires_at": None if expires_at is None else _timestamp(expires_at, "expires_at"),
            "version": CONSTRUCTION_CONTRACTS_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = cls._payload_from_values(values)
        return cls(
            claim_id=stable_id("construction-claim", payload),
            claim_digest=stable_digest(payload),
            **values,
        )

    @staticmethod
    def _payload_from_values(values: dict[str, Any]) -> dict[str, Any]:
        return {
            **values,
            "scope": values["scope"].to_dict(),
            "evidence_refs": list(values["evidence_refs"]),
            "consent_refs": list(values["consent_refs"]),
        }

    def _identity_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("claim_id")
        data.pop("claim_digest")
        return data

    @property
    def state_key(self) -> str:
        return stable_id(
            "construction-claim-state",
            {
                "scope": self.scope.to_dict(),
                "subject_id": self.subject_id,
                "predicate": self.predicate,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ConstructionRecord = ConstructionClaim | ConstructionEvidence


@dataclass(frozen=True)
class ConstructionEvent:
    event_id: str
    event_digest: str
    chain_digest: str
    ledger_id: str
    sequence_number: int
    previous_chain_digest: str
    trace_id: str
    record_kind: str
    record: ConstructionRecord
    actor_id: str
    actor_type: str
    parent_event_ids: tuple[str, ...]
    supersedes_event_ids: tuple[str, ...]
    created_at: float
    version: str = CONSTRUCTION_CONTRACTS_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_CONTRACTS_VERSION:
            raise ValueError("unsupported construction event version")
        if type(self.record) not in {ConstructionClaim, ConstructionEvidence}:
            raise ValueError(
                "event record must be an exact ConstructionClaim or ConstructionEvidence"
            )
        _text(self.ledger_id, "event.ledger_id")
        expected_ledger = f"construction/{self.record.scope.project_id}"
        if self.ledger_id != expected_ledger:
            raise ValueError(f"construction event ledger must be {expected_ledger}")
        if type(self.sequence_number) is not int or self.sequence_number < 1:
            raise ValueError("event sequence_number must be a positive integer")
        expected_previous = _chain_reference(
            self.previous_chain_digest,
            "event.previous_chain_digest",
            genesis_allowed=self.sequence_number == 1,
        )
        if self.previous_chain_digest != expected_previous:
            raise ValueError("event.previous_chain_digest is not canonical")
        if (
            self.sequence_number == 1
            and self.previous_chain_digest != GENESIS_CHAIN_DIGEST
        ):
            raise ValueError("first construction event must use the genesis digest")
        if (
            self.sequence_number > 1
            and self.previous_chain_digest == GENESIS_CHAIN_DIGEST
        ):
            raise ValueError("non-genesis construction event cannot use genesis digest")
        _text(self.trace_id, "event.trace_id")
        kind = _require_canonical_enum(
            self.record_kind, ConstructionRecordKind, "record_kind"
        )
        if kind == ConstructionRecordKind.CLAIM.value and type(self.record) is not ConstructionClaim:
            raise ValueError("CLAIM event requires a ConstructionClaim")
        if kind == ConstructionRecordKind.EVIDENCE.value and type(self.record) is not ConstructionEvidence:
            raise ValueError("EVIDENCE event requires ConstructionEvidence")
        _text(self.actor_id, "event.actor_id")
        _require_canonical_enum(self.actor_type, ActorType, "actor_type")
        _tuple_strings(self.parent_event_ids, "event.parent_event_ids")
        _tuple_strings(self.supersedes_event_ids, "event.supersedes_event_ids")
        if set(self.parent_event_ids) & set(self.supersedes_event_ids):
            raise ValueError("parent and supersession references must be disjoint")
        _require_canonical_float(self.created_at, "event.created_at")
        event_time = _timestamp(self.created_at, "event.created_at")
        record_time = (
            self.record.created_at
            if type(self.record) is ConstructionClaim
            else self.record.observed_at
        )
        if event_time < record_time:
            raise ValueError("construction event cannot predate its record")
        _validate_boundaries(
            proposal_only=self.proposal_only,
            patch_authority=self.patch_authority,
            vsa_patch_authority=self.vsa_patch_authority,
        )
        payload = self._event_payload()
        if self.event_digest != stable_digest(payload):
            raise ValueError("event digest does not match its content")
        chain_payload = {
            "ledger_id": self.ledger_id,
            "sequence_number": self.sequence_number,
            "previous_chain_digest": self.previous_chain_digest,
            "event_digest": self.event_digest,
        }
        if self.chain_digest != stable_digest(chain_payload):
            raise ValueError("event chain digest does not match")
        identity = {**chain_payload, "chain_digest": self.chain_digest}
        if self.event_id != stable_id("construction-event", identity):
            raise ValueError("event ID does not match its content")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionEvent":
        data = dict(value)
        kind = data.get("record_kind")
        raw_record = dict(data.get("record") or {})
        if kind == ConstructionRecordKind.CLAIM.value:
            record: ConstructionRecord = ConstructionClaim.from_dict(raw_record)
        elif kind == ConstructionRecordKind.EVIDENCE.value:
            record = ConstructionEvidence.from_dict(raw_record)
        else:
            raise ValueError(f"unknown construction event record kind: {kind}")
        return cls(
            event_id=data.get("event_id"),
            event_digest=data.get("event_digest"),
            chain_digest=data.get("chain_digest"),
            ledger_id=data.get("ledger_id"),
            sequence_number=data.get("sequence_number"),
            previous_chain_digest=data.get("previous_chain_digest"),
            trace_id=data.get("trace_id"),
            record_kind=kind,
            record=record,
            actor_id=data.get("actor_id"),
            actor_type=data.get("actor_type"),
            parent_event_ids=_sequence_input(data.get("parent_event_ids", ()), "event.parent_event_ids"),
            supersedes_event_ids=_sequence_input(data.get("supersedes_event_ids", ()), "event.supersedes_event_ids"),
            created_at=data.get("created_at"),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    @classmethod
    def create(
        cls,
        *,
        ledger_id: str,
        sequence_number: int,
        previous_chain_digest: str,
        trace_id: str,
        record: ConstructionRecord,
        actor_id: str,
        actor_type: str | ActorType,
        parent_event_ids: Iterable[str] = (),
        supersedes_event_ids: Iterable[str] = (),
        created_at: float,
    ) -> "ConstructionEvent":
        if type(record) is ConstructionClaim:
            kind = ConstructionRecordKind.CLAIM.value
        elif type(record) is ConstructionEvidence:
            kind = ConstructionRecordKind.EVIDENCE.value
        else:
            raise ValueError("record must be an exact ConstructionClaim or ConstructionEvidence")
        if type(sequence_number) is not int:
            raise ValueError("sequence_number must be an integer")
        values = {
            "ledger_id": _normalized_text_input(ledger_id, "ledger_id"),
            "sequence_number": sequence_number,
            "previous_chain_digest": previous_chain_digest,
            "trace_id": _normalized_text_input(trace_id, "trace_id"),
            "record_kind": kind,
            "record": record,
            "actor_id": _normalized_text_input(actor_id, "actor_id"),
            "actor_type": _enum_value(actor_type, ActorType, "actor_type"),
            "parent_event_ids": _normalized_unique(parent_event_ids, "parent_event_ids"),
            "supersedes_event_ids": _normalized_unique(supersedes_event_ids, "supersedes_event_ids"),
            "created_at": _timestamp(created_at, "created_at"),
            "version": CONSTRUCTION_CONTRACTS_VERSION,
            "proposal_only": PROPOSAL_ONLY,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload = cls._payload_from_values(values)
        event_digest = stable_digest(payload)
        chain_payload = {
            "ledger_id": values["ledger_id"],
            "sequence_number": values["sequence_number"],
            "previous_chain_digest": values["previous_chain_digest"],
            "event_digest": event_digest,
        }
        chain_digest = stable_digest(chain_payload)
        identity = {**chain_payload, "chain_digest": chain_digest}
        return cls(
            event_id=stable_id("construction-event", identity),
            event_digest=event_digest,
            chain_digest=chain_digest,
            **values,
        )

    @staticmethod
    def _payload_from_values(values: dict[str, Any]) -> dict[str, Any]:
        return {
            **values,
            "record": values["record"].to_dict(),
            "parent_event_ids": list(values["parent_event_ids"]),
            "supersedes_event_ids": list(values["supersedes_event_ids"]),
        }

    def _event_payload(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("event_id", "event_digest", "chain_digest"):
            data.pop(key)
        return data

    @property
    def project_id(self) -> str:
        return self.record.scope.project_id

    @property
    def state_key(self) -> str:
        return self.record.state_key

    @property
    def record_id(self) -> str:
        return self.record.claim_id if isinstance(self.record, ConstructionClaim) else self.record.evidence_id

    @property
    def record_digest(self) -> str:
        return self.record.claim_digest if isinstance(self.record, ConstructionClaim) else self.record.evidence_digest

    def to_aura_event_envelope(self) -> AuraEventEnvelope:
        measurement = self.record.measurement_class
        confidence = self.record.confidence
        evidence_refs = self.record.evidence_refs if isinstance(self.record, ConstructionClaim) else ()
        return AuraEventEnvelope.create(
            trace_id=self.trace_id,
            parent_event_ids=self.parent_event_ids,
            event_type=f"construction.{self.record_kind.lower()}.recorded",
            actor_id=self.actor_id,
            actor_type=self.actor_type,
            arena_id="sco_construction",
            node_id=self.state_key,
            objective_id=self.record_id,
            purpose_digest=stable_digest({"record_id": self.record_id, "project_id": self.project_id}),
            dikwp_stage=DIKWPStage.INFORMATION,
            payload_ref=self.record_id,
            payload_digest=self.record_digest,
            evidence_refs=evidence_refs,
            policy_scope=self.record.scope.policy_scope,
            proposal_only=True,
            measurement_classes={"record": measurement},
            confidence=confidence,
            uncertainty=None if confidence is None else 1.0 - confidence,
            created_at=self.created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "CONSTRUCTION_CONTRACTS_VERSION",
    "PATCH_AUTHORITY",
    "VSA_PATCH_AUTHORITY",
    "PROPOSAL_ONLY",
    "GENESIS_CHAIN_DIGEST",
    "ConstructionRecordKind",
    "ConstructionEvidenceClass",
    "ConstructionAuthorityClass",
    "ConstructionPrivacyClass",
    "ConstructionScope",
    "ConstructionEvidence",
    "ConstructionClaim",
    "ConstructionEvent",
]
