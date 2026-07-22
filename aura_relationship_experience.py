"""Governed bi-temporal experience projection for Coding Relationship Compass receipts.

Relationship experience is derived from canonical receipts. It never replaces the
Relational Index or Relationship Atlas and never carries patch, promotion, or merge
authority. Historical observations are append-only; decay affects retrieval rank only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
import math
import re
import time
from typing import Any, Mapping, Sequence

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, sanitize_payload, stable_digest

RELATIONSHIP_EXPERIENCE_VERSION = "AURA_RELATIONSHIP_EXPERIENCE_V1"
RELATIONSHIP_EXPERIENCE_MAX_SCALAR_BYTES = 4_096
RELATIONSHIP_EXPERIENCE_MAX_REASON_BYTES = 8_192
RELATIONSHIP_EXPERIENCE_MAX_REF_ITEMS = 64
RELATIONSHIP_EXPERIENCE_MAX_REF_BYTES = 1_024
RELATIONSHIP_EXPERIENCE_MAX_PAYLOAD_BYTES = 64 * 1_024


class RelationshipOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIAL = "DENIAL"
    ABANDONMENT = "ABANDONMENT"
    ROLLBACK = "ROLLBACK"


class RelationshipHumanDisposition(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    DEFERRED = "DEFERRED"
    NOT_REVIEWED = "NOT_REVIEWED"


_ALLOWED_PRIVACY = {"PUBLIC", "PROJECT", "PRIVATE_REDACTED"}
_OPAQUE_REDACTED_DIGEST = re.compile(r"redacted:[0-9a-f]{32,64}")


def _bounded_text(
    value: Any,
    name: str,
    *,
    maximum_bytes: int,
    required: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    text = value.strip() if required else value
    if required and not text:
        raise ValueError(f"{name} is required")
    if len(text.encode("utf-8")) > maximum_bytes:
        raise ValueError(f"{name} exceeds {maximum_bytes} UTF-8 bytes")
    return text


def _required(value: Any, name: str) -> str:
    text = _bounded_text(
        value,
        name,
        maximum_bytes=RELATIONSHIP_EXPERIENCE_MAX_SCALAR_BYTES,
        required=True,
    )
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _strings(values: Sequence[Any], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence")
    if not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(values) > RELATIONSHIP_EXPERIENCE_MAX_REF_ITEMS:
        raise ValueError(f"{name} exceeds {RELATIONSHIP_EXPERIENCE_MAX_REF_ITEMS} items")
    result = tuple(
        dict.fromkeys(
            _bounded_text(
                value,
                name,
                maximum_bytes=RELATIONSHIP_EXPERIENCE_MAX_REF_BYTES,
                required=True,
            )
            for value in values
        )
    )
    return result


def _require_private_redaction(
    privacy_class: str,
    verifier_evidence_refs: Sequence[str],
    receipt_refs: Sequence[str],
    source_refs: Sequence[str],
    reason: str,
) -> None:
    if privacy_class != "PRIVATE_REDACTED":
        return

    def opaque_ref(value: str, kind: str) -> bool:
        return value == f"redacted:{kind}" or _OPAQUE_REDACTED_DIGEST.fullmatch(value) is not None

    if (
        any(not opaque_ref(value, "verifier") for value in verifier_evidence_refs)
        or any(not opaque_ref(value, "receipt") for value in receipt_refs)
        or any(not opaque_ref(value, "source") for value in source_refs)
        or reason not in {"", "[REDACTED]"}
    ):
        raise ValueError("private relationship observation requires redaction")


def _require_sanitized_reason(reason: str) -> None:
    sanitized = sanitize_payload(reason)
    if not isinstance(sanitized, str) or sanitized != reason:
        raise ValueError("relationship experience reason must be pre-sanitized")


def _payload_bytes(value: Mapping[str, Any]) -> int:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("relationship experience payload must be canonical JSON data") from exc
    return len(encoded)


def _finite_timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite timestamp")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite timestamp") from exc
    if not math.isfinite(result) or abs(result) > 1_000_000_000_000_000:
        raise ValueError(f"{name} must be a finite timestamp")
    return result


@dataclass(frozen=True)
class RelationshipExperienceObservation:
    observation_id: str
    relationship_id: str
    relationship_digest: str
    repository_head: str
    working_tree_digest: str
    valid_from_head: str
    valid_to_head: str
    transaction_time: float
    outcome: RelationshipOutcome | str
    verifier_evidence_refs: tuple[str, ...]
    receipt_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    current_source_digest: str
    human_disposition: RelationshipHumanDisposition | str
    privacy_class: str
    objective_digest: str = ""
    reason: str = ""
    version: str = RELATIONSHIP_EXPERIENCE_VERSION
    proposal_only: bool = True
    canonical_truth_owner: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    learned_weight_patch_authority: bool = False
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "relationship_id",
            "relationship_digest",
            "repository_head",
            "working_tree_digest",
            "valid_from_head",
            "current_source_digest",
        ):
            _required(getattr(self, name), name)
        for name in ("valid_to_head", "objective_digest"):
            _bounded_text(
                getattr(self, name),
                name,
                maximum_bytes=RELATIONSHIP_EXPERIENCE_MAX_SCALAR_BYTES,
            )
        _bounded_text(
            self.reason,
            "reason",
            maximum_bytes=RELATIONSHIP_EXPERIENCE_MAX_REASON_BYTES,
        )
        _require_sanitized_reason(self.reason)
        _finite_timestamp(self.transaction_time, "transaction_time")
        if not isinstance(self.outcome, (RelationshipOutcome, str)) or not isinstance(
            self.human_disposition, (RelationshipHumanDisposition, str)
        ):
            raise ValueError("relationship experience enums must be strings")
        if isinstance(self.outcome, str):
            _bounded_text(self.outcome, "outcome", maximum_bytes=64, required=True)
        if isinstance(self.human_disposition, str):
            _bounded_text(
                self.human_disposition,
                "human_disposition",
                maximum_bytes=64,
                required=True,
            )
        try:
            outcome = self.outcome if isinstance(self.outcome, RelationshipOutcome) else RelationshipOutcome(str(self.outcome))
            disposition = (
                self.human_disposition
                if isinstance(self.human_disposition, RelationshipHumanDisposition)
                else RelationshipHumanDisposition(str(self.human_disposition))
            )
        except ValueError as exc:
            raise ValueError("unsupported relationship experience enum") from exc
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "human_disposition", disposition)
        object.__setattr__(self, "verifier_evidence_refs", _strings(self.verifier_evidence_refs, "verifier_evidence_refs"))
        object.__setattr__(self, "receipt_refs", _strings(self.receipt_refs, "receipt_refs"))
        object.__setattr__(self, "source_refs", _strings(self.source_refs, "source_refs"))
        if not isinstance(self.privacy_class, str):
            raise ValueError("relationship experience privacy class must be a string")
        privacy = self.privacy_class.upper()
        if privacy not in _ALLOWED_PRIVACY:
            raise ValueError("unsupported relationship experience privacy class")
        object.__setattr__(self, "privacy_class", privacy)
        _require_private_redaction(
            privacy,
            self.verifier_evidence_refs,
            self.receipt_refs,
            self.source_refs,
            self.reason,
        )
        if (
            self.proposal_only is not True
            or self.canonical_truth_owner is not False
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.learned_weight_patch_authority is not False
            or self.promotion_authority is not False
        ):
            raise ValueError("relationship experience authority boundary changed")
        if self.version != RELATIONSHIP_EXPERIENCE_VERSION:
            raise ValueError("unsupported relationship experience version")
        canonical_payload = asdict(self)
        canonical_payload["outcome"] = outcome.value
        canonical_payload["human_disposition"] = disposition.value
        if _payload_bytes(canonical_payload) + 128 > RELATIONSHIP_EXPERIENCE_MAX_PAYLOAD_BYTES:
            raise ValueError("relationship experience payload exceeds aggregate byte limit")
        expected = stable_digest(self.identity_payload())
        if self.observation_id != f"rex_{expected}":
            raise ValueError("relationship experience observation_id mismatch")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "relationship_digest": self.relationship_digest,
            "repository_head": self.repository_head,
            "working_tree_digest": self.working_tree_digest,
            "valid_from_head": self.valid_from_head,
            "valid_to_head": self.valid_to_head,
            "transaction_time": self.transaction_time,
            "outcome": self.outcome.value if isinstance(self.outcome, RelationshipOutcome) else str(self.outcome),
            "verifier_evidence_refs": list(self.verifier_evidence_refs),
            "receipt_refs": list(self.receipt_refs),
            "source_refs": list(self.source_refs),
            "current_source_digest": self.current_source_digest,
            "human_disposition": (
                self.human_disposition.value
                if isinstance(self.human_disposition, RelationshipHumanDisposition)
                else str(self.human_disposition)
            ),
            "privacy_class": self.privacy_class,
            "objective_digest": self.objective_digest,
            "reason": self.reason,
        }

    @classmethod
    def create(
        cls,
        *,
        relationship_id: str,
        relationship_digest: str,
        repository_head: str,
        working_tree_digest: str,
        valid_from_head: str,
        outcome: RelationshipOutcome | str,
        verifier_evidence_refs: Sequence[str],
        receipt_refs: Sequence[str],
        source_refs: Sequence[str],
        current_source_digest: str,
        human_disposition: RelationshipHumanDisposition | str,
        privacy_class: str,
        valid_to_head: str = "",
        transaction_time: float | None = None,
        objective_digest: str = "",
        reason: str = "",
    ) -> "RelationshipExperienceObservation":
        timestamp = time.time() if transaction_time is None else _finite_timestamp(transaction_time, "transaction_time")
        raw_reason = _bounded_text(
            reason,
            "reason",
            maximum_bytes=RELATIONSHIP_EXPERIENCE_MAX_REASON_BYTES,
        )
        safe_reason = sanitize_payload(raw_reason)
        if not isinstance(safe_reason, str):
            safe_reason = ""
        outcome_value = (
            outcome.value
            if isinstance(outcome, RelationshipOutcome)
            else _bounded_text(outcome, "outcome", maximum_bytes=64, required=True)
        )
        disposition_value = (
            human_disposition.value
            if isinstance(human_disposition, RelationshipHumanDisposition)
            else _bounded_text(
                human_disposition,
                "human_disposition",
                maximum_bytes=64,
                required=True,
            )
        )
        identity = {
            "relationship_id": _required(relationship_id, "relationship_id"),
            "relationship_digest": _required(relationship_digest, "relationship_digest"),
            "repository_head": _required(repository_head, "repository_head"),
            "working_tree_digest": _required(working_tree_digest, "working_tree_digest"),
            "valid_from_head": _required(valid_from_head, "valid_from_head"),
            "valid_to_head": _bounded_text(
                valid_to_head,
                "valid_to_head",
                maximum_bytes=RELATIONSHIP_EXPERIENCE_MAX_SCALAR_BYTES,
            ).strip(),
            "transaction_time": timestamp,
            "outcome": outcome_value,
            "verifier_evidence_refs": list(_strings(verifier_evidence_refs, "verifier_evidence_refs")),
            "receipt_refs": list(_strings(receipt_refs, "receipt_refs")),
            "source_refs": list(_strings(source_refs, "source_refs")),
            "current_source_digest": _required(current_source_digest, "current_source_digest"),
            "human_disposition": disposition_value,
            "privacy_class": _bounded_text(
                privacy_class,
                "privacy_class",
                maximum_bytes=64,
                required=True,
            ).upper(),
            "objective_digest": _bounded_text(
                objective_digest,
                "objective_digest",
                maximum_bytes=RELATIONSHIP_EXPERIENCE_MAX_SCALAR_BYTES,
            ),
            "reason": safe_reason,
        }
        _require_private_redaction(
            identity["privacy_class"],
            identity["verifier_evidence_refs"],
            identity["receipt_refs"],
            identity["source_refs"],
            identity["reason"],
        )
        if _payload_bytes(identity) + 1_024 > RELATIONSHIP_EXPERIENCE_MAX_PAYLOAD_BYTES:
            raise ValueError("relationship experience payload exceeds aggregate byte limit")
        return cls(observation_id=f"rex_{stable_digest(identity)}", **identity)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationshipExperienceObservation":
        if not isinstance(value, Mapping):
            raise ValueError("relationship experience payload must be a mapping")
        fields = set(cls.__dataclass_fields__)
        if len(value) != len(fields) + 1 or "observation_digest" not in value:
            raise ValueError("relationship experience payload fields are not canonical")
        data = dict(value)
        raw_digest = data.pop("observation_digest")
        if not isinstance(raw_digest, str) or not re.fullmatch(r"[0-9a-f]{32}", raw_digest):
            raise ValueError("relationship experience observation_digest is malformed")
        supplied_digest = raw_digest
        if set(data) != fields:
            raise ValueError("relationship experience payload fields are not canonical")
        for key in ("verifier_evidence_refs", "receipt_refs", "source_refs"):
            if type(data[key]) is not list:
                raise ValueError(f"{key} must be a canonical JSON array")
            data[key] = _strings(data[key], key)
        item = cls(**data)
        canonical = item.to_dict()
        canonical_digest = str(canonical.pop("observation_digest"))
        if supplied_digest != canonical_digest:
            raise ValueError("relationship experience observation_digest mismatch")
        return item

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        data["human_disposition"] = self.human_disposition.value
        for key in ("verifier_evidence_refs", "receipt_refs", "source_refs"):
            data[key] = list(getattr(self, key))
        data["observation_digest"] = stable_digest(data)
        return data

    def lesson_eligibility(
        self,
        *,
        current_repository_head: str,
        current_source_digest: str,
        privacy_check_passed: bool,
    ) -> dict[str, Any]:
        missing: list[str] = []
        if not self.verifier_evidence_refs:
            missing.append("verifier_evidence")
        if not self.receipt_refs:
            missing.append("canonical_receipt")
        if self.human_disposition not in {
            RelationshipHumanDisposition.APPROVED,
            RelationshipHumanDisposition.DENIED,
        }:
            missing.append("authority_disposition")
        if not privacy_check_passed or self.privacy_class == "PRIVATE_REDACTED" and not self.source_refs:
            missing.append("privacy_check")
        if self.repository_head != str(current_repository_head or ""):
            missing.append("current_repository_corroboration")
        if self.current_source_digest != str(current_source_digest or ""):
            missing.append("current_source_corroboration")
        eligible = not missing and self.outcome in {
            RelationshipOutcome.SUCCESS,
            RelationshipOutcome.FAILURE,
            RelationshipOutcome.DENIAL,
            RelationshipOutcome.ABANDONMENT,
            RelationshipOutcome.ROLLBACK,
        }
        return {
            "eligible": eligible,
            "missing": missing,
            "outcome": self.outcome.value,
            "advisory_only": True,
            "promotion_authority": False,
        }


def advisory_decay_score(transaction_time: float, *, now: float | None = None, half_life_days: float = 30.0) -> float:
    current = time.time() if now is None else _finite_timestamp(now, "now")
    age_seconds = max(0.0, current - _finite_timestamp(transaction_time, "transaction_time"))
    half_life_seconds = max(1.0, float(half_life_days) * 86400.0)
    return round(2.0 ** (-age_seconds / half_life_seconds), 6)


def project_relationship_timeline(
    observations: Sequence[RelationshipExperienceObservation | Mapping[str, Any]],
    *,
    current_repository_head: str,
    now: float | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for raw in observations:
        observation = raw if isinstance(raw, RelationshipExperienceObservation) else RelationshipExperienceObservation.from_dict(raw)
        data = observation.to_dict()
        data["stale"] = observation.repository_head != str(current_repository_head or "")
        data["advisory_decay_score"] = advisory_decay_score(observation.transaction_time, now=now)
        items.append(data)
    items.sort(key=lambda item: (float(item["transaction_time"]), item["observation_id"]))
    return {
        "version": RELATIONSHIP_EXPERIENCE_VERSION,
        "timeline": items,
        "historical_facts_overwritten": False,
        "decay_affects_validity": False,
        "proposal_only": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "timeline_digest": stable_digest(items),
    }


def crucible_replay_scenarios(
    observations: Sequence[RelationshipExperienceObservation | Mapping[str, Any]],
    *,
    current_repository_head: str,
    current_source_digests: Mapping[str, str],
    privacy_check_passed: bool,
) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in observations:
        observation = raw if isinstance(raw, RelationshipExperienceObservation) else RelationshipExperienceObservation.from_dict(raw)
        gate = observation.lesson_eligibility(
            current_repository_head=current_repository_head,
            current_source_digest=str(current_source_digests.get(observation.relationship_id) or ""),
            privacy_check_passed=privacy_check_passed,
        )
        if not gate["eligible"]:
            rejected.append({"observation_id": observation.observation_id, "missing": gate["missing"]})
            continue
        scenario = {
            "scenario_id": f"crx_{stable_digest({'observation_id': observation.observation_id, 'relationship_id': observation.relationship_id}, digest_size=12)}",
            "relationship_id": observation.relationship_id,
            "expected_outcome": observation.outcome.value,
            "verifier_evidence_refs": list(observation.verifier_evidence_refs),
            "receipt_refs": list(observation.receipt_refs),
            "proposal_only": True,
        }
        scenarios.append(scenario)
    result = {
        "scenarios": sorted(scenarios, key=lambda item: item["scenario_id"]),
        "rejected": sorted(rejected, key=lambda item: item["observation_id"]),
        "proposal_only": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    result["replay_digest"] = stable_digest(result)
    return result


def record_relationship_experience_trace(
    observation: RelationshipExperienceObservation,
    *,
    memory_root: str,
) -> dict[str, Any]:
    """Record a compact symbolic trace atom; raw/private source content is excluded."""
    from aura_symbolic_trace_memory import record_trace_event

    atom = record_trace_event(
        {
            "event_type": "relationship_experience",
            "task_id": observation.relationship_id,
            "summary": f"{observation.relationship_id}: {observation.outcome.value}",
            "route": "CODING_RELATIONSHIP_COMPASS",
            "status": observation.outcome.value.lower(),
            "relationship_id": observation.relationship_id,
            "relationship_digest": observation.relationship_digest,
            "repo_head": observation.repository_head,
            "receipt_refs": list(observation.receipt_refs),
            "source_refs": list(observation.source_refs),
        },
        memory_root,
    )
    return atom.to_dict()


__all__ = [
    "RELATIONSHIP_EXPERIENCE_VERSION",
    "RelationshipOutcome",
    "RelationshipHumanDisposition",
    "RelationshipExperienceObservation",
    "advisory_decay_score",
    "project_relationship_timeline",
    "crucible_replay_scenarios",
    "record_relationship_experience_trace",
]
