"""Governed bi-temporal experience projection for Coding Relationship Compass receipts.

Relationship experience is derived from canonical receipts. It never replaces the
Relational Index or Relationship Atlas and never carries patch, promotion, or merge
authority. Historical observations are append-only; decay affects retrieval rank only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import math
import time
from typing import Any, Mapping, Sequence

from aura_event_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, sanitize_payload, stable_digest

RELATIONSHIP_EXPERIENCE_VERSION = "AURA_RELATIONSHIP_EXPERIENCE_V1"


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


def _required(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _strings(values: Sequence[Any], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence")
    result = tuple(dict.fromkeys(_required(value, name) for value in values))
    return result


def _finite_timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite timestamp")
    return float(value)


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
        _finite_timestamp(self.transaction_time, "transaction_time")
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
        privacy = str(self.privacy_class or "").upper()
        if privacy not in _ALLOWED_PRIVACY:
            raise ValueError("unsupported relationship experience privacy class")
        object.__setattr__(self, "privacy_class", privacy)
        if (
            not self.proposal_only
            or self.canonical_truth_owner
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority
            or self.learned_weight_patch_authority
            or self.promotion_authority
        ):
            raise ValueError("relationship experience authority boundary changed")
        if self.version != RELATIONSHIP_EXPERIENCE_VERSION:
            raise ValueError("unsupported relationship experience version")
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
        safe_reason = sanitize_payload(str(reason or ""))
        if not isinstance(safe_reason, str):
            safe_reason = ""
        identity = {
            "relationship_id": _required(relationship_id, "relationship_id"),
            "relationship_digest": _required(relationship_digest, "relationship_digest"),
            "repository_head": _required(repository_head, "repository_head"),
            "working_tree_digest": _required(working_tree_digest, "working_tree_digest"),
            "valid_from_head": _required(valid_from_head, "valid_from_head"),
            "valid_to_head": str(valid_to_head or "").strip(),
            "transaction_time": timestamp,
            "outcome": outcome.value if isinstance(outcome, RelationshipOutcome) else str(outcome),
            "verifier_evidence_refs": list(_strings(verifier_evidence_refs, "verifier_evidence_refs")),
            "receipt_refs": list(_strings(receipt_refs, "receipt_refs")),
            "source_refs": list(_strings(source_refs, "source_refs")),
            "current_source_digest": _required(current_source_digest, "current_source_digest"),
            "human_disposition": (
                human_disposition.value
                if isinstance(human_disposition, RelationshipHumanDisposition)
                else str(human_disposition)
            ),
            "privacy_class": str(privacy_class or "").upper(),
            "objective_digest": str(objective_digest or ""),
            "reason": safe_reason,
        }
        return cls(observation_id=f"rex_{stable_digest(identity)}", **identity)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationshipExperienceObservation":
        if not isinstance(value, Mapping):
            raise ValueError("relationship experience payload must be a mapping")
        data = dict(value)
        supplied_digest = str(data.pop("observation_digest", "") or "")
        fields = set(cls.__dataclass_fields__)
        if set(data) != fields:
            raise ValueError("relationship experience payload fields are not canonical")
        canonical_json = dict(data)
        if supplied_digest and supplied_digest != stable_digest(canonical_json):
            raise ValueError("relationship experience observation_digest mismatch")
        for key in ("verifier_evidence_refs", "receipt_refs", "source_refs"):
            if type(data[key]) is not list:
                raise ValueError(f"{key} must be a canonical JSON array")
            data[key] = tuple(data[key])
        return cls(**data)

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
