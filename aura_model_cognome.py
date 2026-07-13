"""Aura Model Cognome V1 data contracts.

The Cognome stores versioned, task-conditioned evidence about model endpoints.
It does not recover hidden weights or private chain of thought from closed APIs,
and it never grants patch, merge, or policy-promotion authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import hashlib
import json
import time
from typing import Any, Mapping

COGNOME_VERSION = "AURA_MODEL_COGNOME_V1"
SCHEMA_VERSION = 1
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

BEHAVIORAL_SURROGATE = "BEHAVIORAL_SURROGATE"
MECHANISTIC_OPEN_WEIGHT = "MECHANISTIC_OPEN_WEIGHT"
INFERRED = "INFERRED"


class ModelAccessClass(str, Enum):
    OPEN_WEIGHT = "OPEN_WEIGHT"
    GRAY_BOX = "GRAY_BOX"
    BLACK_BOX = "BLACK_BOX"


class EndpointStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


class RoutePolicyMode(str, Enum):
    ZERO_MODEL = "ZERO_MODEL"
    DIRECT = "DIRECT"
    CASCADE = "CASCADE"
    PANEL = "PANEL"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _canonicalize(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_canonicalize(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def canonical_json(value: Any) -> str:
    """Return deterministic JSON for IDs, digests, and append-only evidence."""
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_digest(value: Any, *, digest_size: int = 16) -> str:
    return hashlib.blake2b(canonical_json(value).encode("utf-8"), digest_size=digest_size).hexdigest()


def stable_id(prefix: str, value: Any, *, digest_size: int = 12) -> str:
    clean_prefix = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in prefix.strip().lower())
    return f"{clean_prefix}_{stable_digest(value, digest_size=digest_size)}"


def _enum_value(value: str | Enum) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _now() -> float:
    return time.time()


@dataclass(frozen=True)
class ModelEndpointIdentity:
    profile_id: str
    provider: str
    requested_model: str
    returned_model: str
    base_url_digest: str
    access_class: str
    endpoint_fingerprint: str
    fingerprint_version: str
    provider_revision: str
    tokenizer_family: str
    price_snapshot_digest: str
    first_seen_at: float
    last_seen_at: float
    status: str = EndpointStatus.ACTIVE.value

    @classmethod
    def create(
        cls,
        *,
        provider: str,
        requested_model: str,
        returned_model: str | None = None,
        base_url_digest: str = "",
        access_class: str | ModelAccessClass = ModelAccessClass.BLACK_BOX,
        endpoint_fingerprint: str = "",
        fingerprint_version: str = "behavioral-v1",
        provider_revision: str = "",
        tokenizer_family: str = "",
        price_snapshot_digest: str = "",
        first_seen_at: float | None = None,
        last_seen_at: float | None = None,
        status: str | EndpointStatus = EndpointStatus.ACTIVE,
    ) -> "ModelEndpointIdentity":
        provider_norm = provider.strip().lower()
        requested = requested_model.strip()
        returned = (returned_model or requested_model).strip()
        access = _enum_value(access_class)
        identity_basis = {
            "provider": provider_norm,
            "requested_model": requested,
            "returned_model": returned,
            "base_url_digest": base_url_digest,
        }
        profile_id = stable_id("profile", identity_basis)
        fingerprint = endpoint_fingerprint or stable_digest({
            **identity_basis,
            "access_class": access,
            "provider_revision": provider_revision,
            "tokenizer_family": tokenizer_family,
            "fingerprint_version": fingerprint_version,
        })
        now = _now()
        return cls(
            profile_id=profile_id,
            provider=provider_norm,
            requested_model=requested,
            returned_model=returned,
            base_url_digest=base_url_digest,
            access_class=access,
            endpoint_fingerprint=fingerprint,
            fingerprint_version=fingerprint_version,
            provider_revision=provider_revision,
            tokenizer_family=tokenizer_family,
            price_snapshot_digest=price_snapshot_digest,
            first_seen_at=now if first_seen_at is None else float(first_seen_at),
            last_seen_at=now if last_seen_at is None else float(last_seen_at),
            status=_enum_value(status),
        )

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class TaskContext:
    task_context_id: str
    objective_hash: str
    purpose_digest: str
    intent_packet_digest: str = ""
    jspace_phase_hash: str = ""
    route_capsule_digest: str = ""
    dir_slot: str = ""
    asp_slot: str = ""
    class_slot: str = ""
    subj_slot: str = ""
    voice_slot: str = ""
    stem_slot: str = ""
    task_family: str = ""
    domain: str = ""
    artifact: str = ""
    action: str = ""
    scope: str = ""
    risk: str = ""
    exactness_required: str = ""
    language: str = ""
    modality: str = ""
    required_capabilities: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    verifier_id: str = ""
    context_tokens: int = 0
    source_lines_exposed: int = 0
    topology_digest: str = ""
    source_hash_digest: str = ""
    required_capability_ids: tuple[str, ...] = ()
    capability_path: tuple[str, ...] = ()
    capability_graph_digest: str = ""
    capability_truth_boundaries: tuple[str, ...] = ()
    capability_risks: tuple[str, ...] = ()
    capability_tests: tuple[str, ...] = ()
    capability_token_savings_roles: tuple[str, ...] = ()
    latency_budget_ms: float | None = None
    cost_budget_usd: float | None = None
    energy_budget_class: str = ""
    privacy_class: str = ""
    data_egress_allowed: bool = False

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        purpose_digest: str,
        intent_packet_digest: str = "",
        capability_graph_digest: str = "",
        source_hash_digest: str = "",
        **fields: Any,
    ) -> "TaskContext":
        objective_hash = stable_digest(objective)
        basis = {
            "objective_hash": objective_hash,
            "purpose_digest": purpose_digest,
            "intent_packet_digest": intent_packet_digest,
            "capability_graph_digest": capability_graph_digest,
            "source_hash_digest": source_hash_digest,
            "task_family": fields.get("task_family", ""),
            "domain": fields.get("domain", ""),
            "required_capability_ids": fields.get("required_capability_ids", ()),
            "verifier_id": fields.get("verifier_id", ""),
        }
        return cls(
            task_context_id=stable_id("task-context", basis),
            objective_hash=objective_hash,
            purpose_digest=purpose_digest,
            intent_packet_digest=intent_packet_digest,
            capability_graph_digest=capability_graph_digest,
            source_hash_digest=source_hash_digest,
            **fields,
        )

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class RouteDecision:
    route_decision_id: str
    task_context_id: str
    purpose_digest: str
    policy_mode: str
    policy_version: str
    selected_profile_ids: tuple[str, ...] = ()
    admitted_profile_ids: tuple[str, ...] = ()
    rejected_candidates: dict[str, str] = field(default_factory=dict)
    predicted_verified_success: float | None = None
    expected_cost_usd: float | None = None
    expected_time_to_verified_ms: float | None = None
    uncertainty_score: float | None = None
    capability_graph_digest: str = ""
    knowledge_snapshot_digest: str = ""
    human_override: bool = False
    proposal_only: bool = True
    created_at: float = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        *,
        task_context_id: str,
        purpose_digest: str,
        policy_mode: str | RoutePolicyMode,
        policy_version: str,
        selected_profile_ids: tuple[str, ...] = (),
        **fields: Any,
    ) -> "RouteDecision":
        mode = _enum_value(policy_mode)
        basis = {
            "task_context_id": task_context_id,
            "purpose_digest": purpose_digest,
            "policy_mode": mode,
            "policy_version": policy_version,
            "selected_profile_ids": selected_profile_ids,
            "knowledge_snapshot_digest": fields.get("knowledge_snapshot_digest", ""),
        }
        return cls(
            route_decision_id=stable_id("route-decision", basis),
            task_context_id=task_context_id,
            purpose_digest=purpose_digest,
            policy_mode=mode,
            policy_version=policy_version,
            selected_profile_ids=selected_profile_ids,
            **fields,
        )

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class ModelObservation:
    observation_id: str
    profile_id: str
    route_decision_id: str = ""
    task_context_id: str = ""
    call_id: str = ""
    cost_run_id: str = ""
    experience_id: str = ""
    policy_mode: str = ""
    attempt_index: int = 0
    fallback_index: int = 0
    shadow_only: bool = False
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: float | None = None
    cost_status: str = "COST_UNKNOWN"
    price_snapshot_digest: str = ""
    usage_measurement_class: str = "UNAVAILABLE"
    field_measurement_classes: dict[str, str] = field(default_factory=dict)
    energy_joules: float | None = None
    queue_ms: float | None = None
    connect_ms: float | None = None
    time_to_first_token_ms: float | None = None
    generation_ms: float | None = None
    tool_execution_ms: float | None = None
    verifier_ms: float | None = None
    retry_ms: float | None = None
    fallback_ms: float | None = None
    end_to_end_ms: float | None = None
    time_to_verified_outcome_ms: float | None = None
    output_tokens_per_second: float | None = None
    verifier_pass: bool | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    format_valid: bool | None = None
    scope_violation_count: int = 0
    repair_attempt_count: int = 0
    human_review_status: str = ""
    uncertainty_score: float | None = None
    endpoint_drift_score: float | None = None
    failure_class: str = ""
    measurement_class: str = "UNAVAILABLE"
    evidence_class: str = BEHAVIORAL_SURROGATE
    extra_evidence: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    @classmethod
    def create(cls, *, profile_id: str, call_id: str = "", **fields: Any) -> "ModelObservation":
        basis = {
            "profile_id": profile_id,
            "call_id": call_id,
            "route_decision_id": fields.get("route_decision_id", ""),
            "task_context_id": fields.get("task_context_id", ""),
            "attempt_index": fields.get("attempt_index", 0),
            "fallback_index": fields.get("fallback_index", 0),
            "created_at": fields.get("created_at", 0),
            "extra_evidence_digest": stable_digest(fields.get("extra_evidence", {})),
        }
        return cls(
            observation_id=stable_id("observation", basis),
            profile_id=profile_id,
            call_id=call_id,
            **fields,
        )

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class ModelCapabilityEdge:
    edge_id: str
    profile_id: str
    aura_capability_id: str
    task_bucket: str
    support_level: str
    verified_success_probability: float | None = None
    p50_time_to_verified_ms: float | None = None
    p95_time_to_verified_ms: float | None = None
    mean_cost_usd: float | None = None
    tool_reliability: float | None = None
    format_reliability: float | None = None
    evidence_count: int = 0
    evidence_digest: str = ""
    last_validated_at: float = 0.0
    status: str = "UNVALIDATED"

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        aura_capability_id: str,
        task_bucket: str,
        support_level: str,
        **fields: Any,
    ) -> "ModelCapabilityEdge":
        basis = {
            "profile_id": profile_id,
            "aura_capability_id": aura_capability_id,
            "task_bucket": task_bucket,
        }
        return cls(
            edge_id=stable_id("model-capability-edge", basis),
            profile_id=profile_id,
            aura_capability_id=aura_capability_id,
            task_bucket=task_bucket,
            support_level=support_level,
            **fields,
        )

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class CapabilityPosterior:
    profile_id: str
    task_bucket: str
    context_bucket: str
    verifier_id: str
    sample_count: int = 0
    verified_success_alpha: float = 1.0
    verified_success_beta: float = 1.0
    mean_cost_usd: float | None = None
    mean_time_to_verified_ms: float | None = None
    p50_time_to_verified_ms: float | None = None
    p95_time_to_verified_ms: float | None = None
    p99_time_to_verified_ms: float | None = None
    mean_repair_attempts: float | None = None
    scope_violation_rate: float | None = None
    abstention_quality: float | None = None
    calibration_error: float | None = None
    last_validated_at: float = 0.0
    evidence_digest: str = ""
    status: str = "UNVALIDATED"

    @property
    def verified_success_mean(self) -> float:
        denominator = self.verified_success_alpha + self.verified_success_beta
        return self.verified_success_alpha / denominator if denominator else 0.5

    def to_dict(self) -> dict[str, Any]:
        data = _canonicalize(self)
        data["verified_success_mean"] = self.verified_success_mean
        return data


def validate_evidence_claim(access_class: str | ModelAccessClass, evidence_class: str) -> None:
    """Reject mechanistic claims for endpoints without open-weight access."""
    access = _enum_value(access_class)
    if evidence_class == MECHANISTIC_OPEN_WEIGHT and access != ModelAccessClass.OPEN_WEIGHT.value:
        raise ValueError("Mechanistic J-space evidence requires OPEN_WEIGHT access")
