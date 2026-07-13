"""Aura Model Cognome V1 data contracts.

The Cognome stores versioned, task-conditioned evidence about model endpoints.
It never treats closed-model behavior as recovered weights or private reasoning,
and it grants no patch, merge, or policy-promotion authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields as dataclass_fields, is_dataclass, replace
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Mapping

COGNOME_VERSION = "AURA_MODEL_COGNOME_V1"
SCHEMA_VERSION = 1
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

BEHAVIORAL_SURROGATE = "BEHAVIORAL_SURROGATE"
MECHANISTIC_OPEN_WEIGHT = "MECHANISTIC_OPEN_WEIGHT"
INFERRED = "INFERRED"
_ALLOWED_EVIDENCE_CLASSES = {BEHAVIORAL_SURROGATE, MECHANISTIC_OPEN_WEIGHT, INFERRED}


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
        normalized = [_canonicalize(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite floats are not permitted in Cognome records")
    return value


def canonical_json(value: Any) -> str:
    """Return deterministic JSON for IDs, digests, and append-only evidence."""
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_digest(value: Any, *, digest_size: int = 16) -> str:
    if not 1 <= int(digest_size) <= 64:
        raise ValueError("digest_size must be between 1 and 64 bytes")
    return hashlib.blake2b(canonical_json(value).encode("utf-8"), digest_size=int(digest_size)).hexdigest()


def stable_id(prefix: str, value: Any, *, digest_size: int = 12) -> str:
    clean_prefix = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in prefix.strip().lower())
    if not clean_prefix:
        raise ValueError("stable_id prefix must not be empty")
    return f"{clean_prefix}_{stable_digest(value, digest_size=digest_size)}"


def _enum_value(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value)
    allowed = {item.value for item in enum_type}
    if raw not in allowed:
        raise ValueError(f"Unknown {field_name}: {raw}")
    return raw


def _now() -> float:
    return time.time()


def _require_nonempty(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _validate_probability(value: float | None, field_name: str) -> None:
    if value is not None and not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")


def _validate_nonnegative(value: float | int | None, field_name: str) -> None:
    if value is not None and float(value) < 0:
        raise ValueError(f"{field_name} must be non-negative")


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
        fingerprint_version: str = "identity-v1",
        provider_revision: str = "",
        tokenizer_family: str = "",
        price_snapshot_digest: str = "",
        first_seen_at: float | None = None,
        last_seen_at: float | None = None,
        status: str | EndpointStatus = EndpointStatus.ACTIVE,
    ) -> "ModelEndpointIdentity":
        provider_norm = _require_nonempty(provider, "provider").lower()
        requested = _require_nonempty(requested_model, "requested_model")
        returned = _require_nonempty(returned_model or requested_model, "returned_model")
        access = _enum_value(access_class, ModelAccessClass, "access_class")
        status_value = _enum_value(status, EndpointStatus, "endpoint status")
        identity_basis = {
            "provider": provider_norm,
            "requested_model": requested,
            "base_url_digest": str(base_url_digest),
            "access_class": access,
        }
        profile_id = stable_id("profile", identity_basis)
        fingerprint_version_value = _require_nonempty(fingerprint_version, "fingerprint_version")
        fingerprint = endpoint_fingerprint or stable_digest({
            "identity_basis": identity_basis,
            "returned_model": returned,
            "provider_revision": provider_revision,
            "tokenizer_family": tokenizer_family,
            "fingerprint_version": fingerprint_version_value,
        })
        first = _now() if first_seen_at is None else float(first_seen_at)
        last = first if last_seen_at is None else float(last_seen_at)
        if last < first:
            raise ValueError("last_seen_at must be greater than or equal to first_seen_at")
        return cls(
            profile_id=profile_id,
            provider=provider_norm,
            requested_model=requested,
            returned_model=returned,
            base_url_digest=str(base_url_digest),
            access_class=access,
            endpoint_fingerprint=str(fingerprint),
            fingerprint_version=fingerprint_version_value,
            provider_revision=str(provider_revision),
            tokenizer_family=str(tokenizer_family),
            price_snapshot_digest=str(price_snapshot_digest),
            first_seen_at=first,
            last_seen_at=last,
            status=status_value,
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
        objective_hash = stable_digest(_require_nonempty(objective, "objective"))
        purpose = _require_nonempty(purpose_digest, "purpose_digest")
        tuple_fields = {
            "required_capabilities",
            "required_tools",
            "required_capability_ids",
            "capability_path",
            "capability_truth_boundaries",
            "capability_risks",
            "capability_tests",
            "capability_token_savings_roles",
        }
        normalized_fields = dict(fields)
        for name in tuple_fields:
            if name in normalized_fields:
                normalized_fields[name] = tuple(str(item) for item in normalized_fields[name])
        _validate_nonnegative(normalized_fields.get("context_tokens", 0), "context_tokens")
        _validate_nonnegative(normalized_fields.get("source_lines_exposed", 0), "source_lines_exposed")
        _validate_nonnegative(normalized_fields.get("latency_budget_ms"), "latency_budget_ms")
        _validate_nonnegative(normalized_fields.get("cost_budget_usd"), "cost_budget_usd")
        allowed = {item.name for item in dataclass_fields(cls)} - {
            "task_context_id", "objective_hash", "purpose_digest", "intent_packet_digest",
            "capability_graph_digest", "source_hash_digest",
        }
        unknown = sorted(set(normalized_fields) - allowed)
        if unknown:
            raise TypeError(f"Unknown TaskContext fields: {', '.join(unknown)}")
        payload = {
            "objective_hash": objective_hash,
            "purpose_digest": purpose,
            "intent_packet_digest": str(intent_packet_digest),
            "capability_graph_digest": str(capability_graph_digest),
            "source_hash_digest": str(source_hash_digest),
            **normalized_fields,
        }
        task_context_id = stable_id("task-context", payload)
        return cls(task_context_id=task_context_id, **payload)

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
        created_at: float | None = None,
        **fields: Any,
    ) -> "RouteDecision":
        task_id = _require_nonempty(task_context_id, "task_context_id")
        purpose = _require_nonempty(purpose_digest, "purpose_digest")
        mode = _enum_value(policy_mode, RoutePolicyMode, "policy_mode")
        version = _require_nonempty(policy_version, "policy_version")
        timestamp = _now() if created_at is None else float(created_at)
        selected = tuple(str(item) for item in selected_profile_ids)
        if mode == RoutePolicyMode.ZERO_MODEL.value and selected:
            raise ValueError("ZERO_MODEL decisions cannot select model profiles")
        if "admitted_profile_ids" in fields:
            fields["admitted_profile_ids"] = tuple(str(item) for item in fields["admitted_profile_ids"])
        for name in ("predicted_verified_success", "uncertainty_score"):
            _validate_probability(fields.get(name), name)
        _validate_nonnegative(fields.get("expected_cost_usd"), "expected_cost_usd")
        _validate_nonnegative(fields.get("expected_time_to_verified_ms"), "expected_time_to_verified_ms")
        basis = {
            "task_context_id": task_id,
            "purpose_digest": purpose,
            "policy_mode": mode,
            "policy_version": version,
            "selected_profile_ids": selected,
            "knowledge_snapshot_digest": fields.get("knowledge_snapshot_digest", ""),
            "created_at": timestamp,
        }
        return cls(
            route_decision_id=stable_id("route-decision", basis),
            task_context_id=task_id,
            purpose_digest=purpose,
            policy_mode=mode,
            policy_version=version,
            selected_profile_ids=selected,
            created_at=timestamp,
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
    def create(
        cls,
        *,
        profile_id: str,
        call_id: str = "",
        created_at: float | None = None,
        **fields: Any,
    ) -> "ModelObservation":
        profile = _require_nonempty(profile_id, "profile_id")
        timestamp = _now() if created_at is None else float(created_at)
        nonnegative_fields = (
            "attempt_index", "fallback_index", "input_tokens", "cached_input_tokens",
            "output_tokens", "reasoning_tokens", "cost_usd", "energy_joules", "queue_ms",
            "connect_ms", "time_to_first_token_ms", "generation_ms", "tool_execution_ms",
            "verifier_ms", "retry_ms", "fallback_ms", "end_to_end_ms",
            "time_to_verified_outcome_ms", "output_tokens_per_second", "tests_passed",
            "tests_failed", "scope_violation_count", "repair_attempt_count",
        )
        for name in nonnegative_fields:
            _validate_nonnegative(fields.get(name), name)
        _validate_probability(fields.get("uncertainty_score"), "uncertainty_score")
        _validate_probability(fields.get("endpoint_drift_score"), "endpoint_drift_score")
        evidence_class = str(fields.get("evidence_class", BEHAVIORAL_SURROGATE))
        if evidence_class not in _ALLOWED_EVIDENCE_CLASSES:
            raise ValueError(f"Unknown evidence_class: {evidence_class}")
        fields["evidence_class"] = evidence_class
        basis = {
            "profile_id": profile,
            "call_id": str(call_id),
            "route_decision_id": fields.get("route_decision_id", ""),
            "task_context_id": fields.get("task_context_id", ""),
            "attempt_index": fields.get("attempt_index", 0),
            "fallback_index": fields.get("fallback_index", 0),
            "created_at": timestamp,
            "extra_evidence_digest": stable_digest(fields.get("extra_evidence", {})),
        }
        return cls(
            observation_id=stable_id("observation", basis),
            profile_id=profile,
            call_id=str(call_id),
            created_at=timestamp,
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
    capability_graph_digest: str = ""
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
        profile = _require_nonempty(profile_id, "profile_id")
        capability = _require_nonempty(aura_capability_id, "aura_capability_id")
        bucket = _require_nonempty(task_bucket, "task_bucket")
        support = _require_nonempty(support_level, "support_level")
        for name in ("verified_success_probability", "tool_reliability", "format_reliability"):
            _validate_probability(fields.get(name), name)
        for name in ("p50_time_to_verified_ms", "p95_time_to_verified_ms", "mean_cost_usd", "evidence_count", "last_validated_at"):
            _validate_nonnegative(fields.get(name), name)
        p50 = fields.get("p50_time_to_verified_ms")
        p95 = fields.get("p95_time_to_verified_ms")
        if p50 is not None and p95 is not None and float(p95) < float(p50):
            raise ValueError("p95_time_to_verified_ms must be >= p50_time_to_verified_ms")
        basis = {
            "profile_id": profile,
            "aura_capability_id": capability,
            "task_bucket": bucket,
        }
        return cls(
            edge_id=stable_id("model-capability-edge", basis),
            profile_id=profile,
            aura_capability_id=capability,
            task_bucket=bucket,
            support_level=support,
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
    validation_split: str = "TRAIN"
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

    def __post_init__(self) -> None:
        _require_nonempty(self.profile_id, "profile_id")
        _require_nonempty(self.task_bucket, "task_bucket")
        _require_nonempty(self.context_bucket, "context_bucket")
        _require_nonempty(self.verifier_id, "verifier_id")
        if self.validation_split not in {"TRAIN", "VALIDATION", "SHADOW"}:
            raise ValueError(f"Unknown validation_split: {self.validation_split}")
        for name in ("sample_count", "verified_success_alpha", "verified_success_beta", "mean_cost_usd", "mean_time_to_verified_ms", "p50_time_to_verified_ms", "p95_time_to_verified_ms", "p99_time_to_verified_ms", "mean_repair_attempts", "last_validated_at"):
            _validate_nonnegative(getattr(self, name), name)
        if self.verified_success_alpha <= 0 or self.verified_success_beta <= 0:
            raise ValueError("Beta posterior parameters must be greater than zero")
        for name in ("scope_violation_rate", "abstention_quality", "calibration_error"):
            _validate_probability(getattr(self, name), name)
        quantiles = [self.p50_time_to_verified_ms, self.p95_time_to_verified_ms, self.p99_time_to_verified_ms]
        present = [float(value) for value in quantiles if value is not None]
        if present != sorted(present):
            raise ValueError("Latency quantiles must be monotonic")

    @property
    def verified_success_mean(self) -> float:
        denominator = self.verified_success_alpha + self.verified_success_beta
        return self.verified_success_alpha / denominator if denominator else 0.5

    def update_verified_outcome(self, passed: bool, *, evidence_digest: str, validated_at: float | None = None) -> "CapabilityPosterior":
        return replace(
            self,
            sample_count=self.sample_count + 1,
            verified_success_alpha=self.verified_success_alpha + (1.0 if passed else 0.0),
            verified_success_beta=self.verified_success_beta + (0.0 if passed else 1.0),
            evidence_digest=_require_nonempty(evidence_digest, "evidence_digest"),
            last_validated_at=_now() if validated_at is None else float(validated_at),
            status="VALIDATED",
        )

    def to_dict(self) -> dict[str, Any]:
        data = _canonicalize(self)
        data["verified_success_mean"] = self.verified_success_mean
        return data


def validate_evidence_claim(access_class: str | ModelAccessClass, evidence_class: str) -> None:
    """Reject mechanistic claims for endpoints without open-weight access."""
    access = _enum_value(access_class, ModelAccessClass, "access_class")
    if evidence_class not in _ALLOWED_EVIDENCE_CLASSES:
        raise ValueError(f"Unknown evidence_class: {evidence_class}")
    if evidence_class == MECHANISTIC_OPEN_WEIGHT and access != ModelAccessClass.OPEN_WEIGHT.value:
        raise ValueError("Mechanistic J-space evidence requires OPEN_WEIGHT access")
