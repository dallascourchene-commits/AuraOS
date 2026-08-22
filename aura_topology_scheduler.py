from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

SCHEDULER_STATE_SCHEMA = "AURAOS_V9_SCHEDULER_STATE_V1"
PHASE_DECISION_SCHEMA = "AURAOS_V9_SCHEDULER_PHASE_DECISION_V1"
SCHEDULER_CANONICAL_PROFILE = "AURAOS_V9_SCHEDULER_CANONICAL_JSON_V1"

SCHEDULER_STATE_DOMAIN = "AURA::V9::SCHEDULER::STATE::V1"
PHASE_DECISION_DOMAIN = "AURA::V9::SCHEDULER::PHASE-DECISION::V1"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_JCS_SAFE_INTEGER = (1 << 53) - 1
_MAX_BASIS_POINTS = 10_000


class ContractViolation(ValueError):
    """Fail-closed structural validation error for the V9 scheduler state."""


def _nfc(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ContractViolation(f"{field} must be a string")
    normalized = unicodedata.normalize("NFC", value)
    if not normalized:
        raise ContractViolation(f"{field} must be non-empty")
    return normalized


def _digest(value: str, field: str) -> str:
    normalized = _nfc(value, field)
    if not _HEX64.fullmatch(normalized):
        raise ContractViolation(f"{field} must be lowercase 64-hex SHA-256 syntax")
    return normalized


def _count(value: int, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > _MAX_JCS_SAFE_INTEGER
    ):
        raise ContractViolation(
            f"{field} must be a non-negative JCS-safe integer <= {_MAX_JCS_SAFE_INTEGER}"
        )
    return value


def _positive_count(value: int, field: str) -> int:
    result = _count(value, field)
    if result == 0:
        raise ContractViolation(f"{field} must be greater than zero")
    return result


def _basis_points(value: int, field: str) -> int:
    result = _count(value, field)
    if result > _MAX_BASIS_POINTS:
        raise ContractViolation(f"{field} must be <= {_MAX_BASIS_POINTS}")
    return result


def _normalize_json(value: Any, field: str = "value") -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, float):
        raise ContractViolation(f"{field} contains unsupported JSON value")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return _count(value, field)
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item, f"{field}[]") for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = _nfc(key, f"{field}.key")
            if normalized_key in normalized:
                raise ContractViolation(f"{field} has duplicate canonical key")
            normalized[normalized_key] = _normalize_json(
                item, f"{field}.{normalized_key}"
            )
        return normalized
    raise ContractViolation(
        f"{field} contains unsupported type {type(value).__name__}"
    )


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    normalized = _normalize_json(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _hash_domain(domain: str, body: Mapping[str, Any]) -> str:
    if "domain_separator" in body:
        raise ContractViolation("body may not supply domain_separator")
    return hashlib.sha256(
        canonical_json_bytes({"domain_separator": domain, **dict(body)})
    ).hexdigest()


def _canonical_string_set(values: Iterable[str], field: str) -> tuple[str, ...]:
    normalized = [_nfc(value, field) for value in values]
    if len(set(normalized)) != len(normalized):
        raise ContractViolation(f"{field} contains duplicate canonical members")
    return tuple(sorted(normalized, key=lambda item: item.encode("utf-8")))


def _canonical_edge_set(
    values: Iterable[tuple[str, str]], field: str
) -> tuple[tuple[str, str], ...]:
    normalized: list[tuple[str, str]] = []
    for index, edge in enumerate(values):
        if not isinstance(edge, tuple) or len(edge) != 2:
            raise ContractViolation(f"{field}[{index}] must be a 2-tuple")
        source = _nfc(edge[0], f"{field}[{index}].source")
        target = _nfc(edge[1], f"{field}[{index}].target")
        if source == target:
            raise ContractViolation(f"{field}[{index}] may not be a self-edge")
        normalized.append((source, target))
    if len(set(normalized)) != len(normalized):
        raise ContractViolation(f"{field} contains duplicate canonical members")
    return tuple(
        sorted(
            normalized,
            key=lambda edge: (
                edge[0].encode("utf-8"),
                edge[1].encode("utf-8"),
            ),
        )
    )


class SchedulerPhase(str, Enum):
    DISCOVER = "DISCOVER"
    DIVERGE = "DIVERGE"
    SYNTHESIZE = "SYNTHESIZE"
    CONVERGE = "CONVERGE"
    VERIFY = "VERIFY"
    REDUCE = "REDUCE"
    EXECUTE = "EXECUTE"
    RECOVER = "RECOVER"
    REBASE = "REBASE"


class PhaseReason(str, Enum):
    HARD_GUARD_REBASE = "HARD_GUARD_REBASE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    DISCOVERY_GAP = "DISCOVERY_GAP"
    CANDIDATE_DEFICIT = "CANDIDATE_DEFICIT"
    CONTRADICTION_OR_DISSENT = "CONTRADICTION_OR_DISSENT"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
    VERIFICATION_DEBT = "VERIFICATION_DEBT"
    REDUCTION_READY = "REDUCTION_READY"
    READY_WORK = "READY_WORK"
    ASSURANCE_FALLBACK = "ASSURANCE_FALLBACK"


@dataclass(frozen=True)
class WorkloadStateV1:
    ready_task_count: int
    blocked_task_count: int
    dependency_edges: Sequence[tuple[str, str]]
    upstream_prerequisite_refs: Sequence[str]
    downstream_dependent_refs: Sequence[str]
    critical_path_refs: Sequence[str]

    def protected_body(self) -> dict[str, Any]:
        return {
            "ready_task_count": _count(self.ready_task_count, "ready_task_count"),
            "blocked_task_count": _count(
                self.blocked_task_count, "blocked_task_count"
            ),
            "dependency_edges": [
                list(edge)
                for edge in _canonical_edge_set(
                    self.dependency_edges, "dependency_edges"
                )
            ],
            "upstream_prerequisite_refs": list(
                _canonical_string_set(
                    self.upstream_prerequisite_refs, "upstream_prerequisite_refs"
                )
            ),
            "downstream_dependent_refs": list(
                _canonical_string_set(
                    self.downstream_dependent_refs, "downstream_dependent_refs"
                )
            ),
            "critical_path_refs": list(
                _canonical_string_set(self.critical_path_refs, "critical_path_refs")
            ),
        }


@dataclass(frozen=True)
class EvidenceStateV1:
    unresolved_uncertainty_count: int
    contradiction_refs: Sequence[str]
    dissent_refs: Sequence[str]
    candidate_count: int
    target_candidate_count: int
    verification_debt_count: int
    discovery_gap_count: int
    reduction_ready_count: int

    def protected_body(self) -> dict[str, Any]:
        return {
            "unresolved_uncertainty_count": _count(
                self.unresolved_uncertainty_count, "unresolved_uncertainty_count"
            ),
            "contradiction_refs": list(
                _canonical_string_set(self.contradiction_refs, "contradiction_refs")
            ),
            "dissent_refs": list(
                _canonical_string_set(self.dissent_refs, "dissent_refs")
            ),
            "candidate_count": _count(self.candidate_count, "candidate_count"),
            "target_candidate_count": _count(
                self.target_candidate_count, "target_candidate_count"
            ),
            "verification_debt_count": _count(
                self.verification_debt_count, "verification_debt_count"
            ),
            "discovery_gap_count": _count(
                self.discovery_gap_count, "discovery_gap_count"
            ),
            "reduction_ready_count": _count(
                self.reduction_ready_count, "reduction_ready_count"
            ),
        }


@dataclass(frozen=True)
class WorkerStateV1:
    active_worker_count: int
    logical_position_refs: Sequence[str]
    capability_profile_refs: Sequence[str]
    evidence_independence_groups: Sequence[str]
    queue_depth: int
    expected_service_time_ms: int

    def protected_body(self) -> dict[str, Any]:
        return {
            "active_worker_count": _count(
                self.active_worker_count, "active_worker_count"
            ),
            "logical_position_refs": list(
                _canonical_string_set(
                    self.logical_position_refs, "logical_position_refs"
                )
            ),
            "capability_profile_refs": list(
                _canonical_string_set(
                    self.capability_profile_refs, "capability_profile_refs"
                )
            ),
            "evidence_independence_groups": list(
                _canonical_string_set(
                    self.evidence_independence_groups,
                    "evidence_independence_groups",
                )
            ),
            "queue_depth": _count(self.queue_depth, "queue_depth"),
            "expected_service_time_ms": _count(
                self.expected_service_time_ms, "expected_service_time_ms"
            ),
        }


@dataclass(frozen=True)
class ResourceStateV1:
    available_device_refs: Sequence[str]
    cpu_millicores_available: int
    gpu_memory_bytes_available: int
    npu_unit_count: int
    ram_bytes_available: int
    storage_bytes_available: int
    battery_basis_points: int
    thermal_state: str

    def protected_body(self) -> dict[str, Any]:
        return {
            "available_device_refs": list(
                _canonical_string_set(
                    self.available_device_refs, "available_device_refs"
                )
            ),
            "cpu_millicores_available": _count(
                self.cpu_millicores_available, "cpu_millicores_available"
            ),
            "gpu_memory_bytes_available": _count(
                self.gpu_memory_bytes_available, "gpu_memory_bytes_available"
            ),
            "npu_unit_count": _count(self.npu_unit_count, "npu_unit_count"),
            "ram_bytes_available": _count(
                self.ram_bytes_available, "ram_bytes_available"
            ),
            "storage_bytes_available": _count(
                self.storage_bytes_available, "storage_bytes_available"
            ),
            "battery_basis_points": _basis_points(
                self.battery_basis_points, "battery_basis_points"
            ),
            "thermal_state": _nfc(self.thermal_state, "thermal_state"),
        }


@dataclass(frozen=True)
class NetworkStateV1:
    latency_ms: int
    jitter_ms: int
    loss_basis_points: int
    bandwidth_kbps: int
    network_cost_microunits: int

    def protected_body(self) -> dict[str, Any]:
        return {
            "latency_ms": _count(self.latency_ms, "latency_ms"),
            "jitter_ms": _count(self.jitter_ms, "jitter_ms"),
            "loss_basis_points": _basis_points(
                self.loss_basis_points, "loss_basis_points"
            ),
            "bandwidth_kbps": _count(self.bandwidth_kbps, "bandwidth_kbps"),
            "network_cost_microunits": _count(
                self.network_cost_microunits, "network_cost_microunits"
            ),
        }


@dataclass(frozen=True)
class FailureStateV1:
    failed_worker_count: int
    timeout_count: int
    cancellation_pending: bool
    recovery_pending: bool

    def protected_body(self) -> dict[str, Any]:
        if not isinstance(self.cancellation_pending, bool):
            raise ContractViolation("cancellation_pending must be boolean")
        if not isinstance(self.recovery_pending, bool):
            raise ContractViolation("recovery_pending must be boolean")
        return {
            "failed_worker_count": _count(
                self.failed_worker_count, "failed_worker_count"
            ),
            "timeout_count": _count(self.timeout_count, "timeout_count"),
            "cancellation_pending": self.cancellation_pending,
            "recovery_pending": self.recovery_pending,
        }


@dataclass(frozen=True)
class SchedulerStateV1:
    objective_id: str
    objective_class: str
    objective_digest: str
    acceptance_criteria_digest: str
    consequence_class: str

    current_phase: SchedulerPhase
    current_topology_profile: str
    recursion_depth: int

    workload: WorkloadStateV1
    evidence: EvidenceStateV1
    workers: WorkerStateV1
    resources: ResourceStateV1

    token_budget_remaining: int
    model_budget_microunits: int
    provider_budget_microunits: int
    provider_availability_refs: Sequence[str]

    source_locality_refs: Sequence[str]
    source_generation: int
    source_current: bool
    currentness_digest: str
    semantic_environment: str

    authority_current: bool
    authority_ceiling_digest: str
    privacy_class: str
    privacy_admissible: bool

    network: NetworkStateV1
    failure: FailureStateV1

    prior_topology_outcome_receipt_refs: Sequence[str]
    prior_handoff_outcome_receipt_refs: Sequence[str]
    prior_outcome_confidence_basis_points: int

    creation_stage: int
    creation_stage_ready: bool
    step_basis_current: bool

    def protected_body(self) -> dict[str, Any]:
        if not isinstance(self.current_phase, SchedulerPhase):
            raise ContractViolation("current_phase must be a SchedulerPhase")
        for field, value in (
            ("source_current", self.source_current),
            ("authority_current", self.authority_current),
            ("privacy_admissible", self.privacy_admissible),
            ("creation_stage_ready", self.creation_stage_ready),
            ("step_basis_current", self.step_basis_current),
        ):
            if not isinstance(value, bool):
                raise ContractViolation(f"{field} must be boolean")

        return {
            "schema": SCHEDULER_STATE_SCHEMA,
            "canonical_profile_id": SCHEDULER_CANONICAL_PROFILE,
            "objective": {
                "objective_id": _nfc(self.objective_id, "objective_id"),
                "objective_class": _nfc(self.objective_class, "objective_class"),
                "objective_digest": _digest(
                    self.objective_digest, "objective_digest"
                ),
                "acceptance_criteria_digest": _digest(
                    self.acceptance_criteria_digest, "acceptance_criteria_digest"
                ),
                "consequence_class": _nfc(
                    self.consequence_class, "consequence_class"
                ),
            },
            "topology_context": {
                "current_phase": self.current_phase.value,
                "current_topology_profile": _nfc(
                    self.current_topology_profile, "current_topology_profile"
                ),
                "recursion_depth": _count(
                    self.recursion_depth, "recursion_depth"
                ),
            },
            "workload": self.workload.protected_body(),
            "evidence": self.evidence.protected_body(),
            "workers": self.workers.protected_body(),
            "resources": self.resources.protected_body(),
            "budgets": {
                "token_budget_remaining": _count(
                    self.token_budget_remaining, "token_budget_remaining"
                ),
                "model_budget_microunits": _count(
                    self.model_budget_microunits, "model_budget_microunits"
                ),
                "provider_budget_microunits": _count(
                    self.provider_budget_microunits,
                    "provider_budget_microunits",
                ),
                "provider_availability_refs": list(
                    _canonical_string_set(
                        self.provider_availability_refs,
                        "provider_availability_refs",
                    )
                ),
            },
            "source_currentness": {
                "source_locality_refs": list(
                    _canonical_string_set(
                        self.source_locality_refs, "source_locality_refs"
                    )
                ),
                "source_generation": _count(
                    self.source_generation, "source_generation"
                ),
                "source_current": self.source_current,
                "currentness_digest": _digest(
                    self.currentness_digest, "currentness_digest"
                ),
                "semantic_environment": _nfc(
                    self.semantic_environment, "semantic_environment"
                ),
            },
            "authority_privacy": {
                "authority_current": self.authority_current,
                "authority_ceiling_digest": _digest(
                    self.authority_ceiling_digest,
                    "authority_ceiling_digest",
                ),
                "privacy_class": _nfc(self.privacy_class, "privacy_class"),
                "privacy_admissible": self.privacy_admissible,
            },
            "network": self.network.protected_body(),
            "failure": self.failure.protected_body(),
            "prior_outcomes": {
                "prior_topology_outcome_receipt_refs": list(
                    _canonical_string_set(
                        self.prior_topology_outcome_receipt_refs,
                        "prior_topology_outcome_receipt_refs",
                    )
                ),
                "prior_handoff_outcome_receipt_refs": list(
                    _canonical_string_set(
                        self.prior_handoff_outcome_receipt_refs,
                        "prior_handoff_outcome_receipt_refs",
                    )
                ),
                "confidence_basis_points": _basis_points(
                    self.prior_outcome_confidence_basis_points,
                    "prior_outcome_confidence_basis_points",
                ),
            },
            "creation_process": {
                "creation_stage": _positive_count(
                    self.creation_stage, "creation_stage"
                ),
                "creation_stage_ready": self.creation_stage_ready,
                "step_basis_current": self.step_basis_current,
            },
        }

    def state_digest(self) -> str:
        body = self.protected_body()
        stage = body["creation_process"]["creation_stage"]
        if stage > 10:
            raise ContractViolation("creation_stage must be <= 10")
        return _hash_domain(SCHEDULER_STATE_DOMAIN, body)


@dataclass(frozen=True)
class PhaseDecisionV1:
    phase: SchedulerPhase
    reason: PhaseReason
    state_digest: str

    def protected_body(self) -> dict[str, Any]:
        if not isinstance(self.phase, SchedulerPhase):
            raise ContractViolation("phase must be a SchedulerPhase")
        if not isinstance(self.reason, PhaseReason):
            raise ContractViolation("reason must be a PhaseReason")
        return {
            "schema": PHASE_DECISION_SCHEMA,
            "phase": self.phase.value,
            "reason": self.reason.value,
            "state_digest": _digest(self.state_digest, "state_digest"),
        }

    def decision_digest(self) -> str:
        return _hash_domain(PHASE_DECISION_DOMAIN, self.protected_body())


def classify_phase(state: SchedulerStateV1) -> PhaseDecisionV1:
    """Classify one bounded scheduler phase without selecting topology or workers.

    Hard source/currentness/authority/privacy/step-basis guards dominate workflow
    progression. Recovery conditions dominate ordinary discovery/synthesis work.
    The remaining rules are explicit and ordered so the decision can be replayed
    from the protected SchedulerStateV1 alone.
    """

    if not isinstance(state, SchedulerStateV1):
        raise ContractViolation("state must be a SchedulerStateV1")

    state_digest = state.state_digest()

    if (
        not state.source_current
        or not state.authority_current
        or not state.privacy_admissible
        or not state.creation_stage_ready
        or not state.step_basis_current
    ):
        phase = SchedulerPhase.REBASE
        reason = PhaseReason.HARD_GUARD_REBASE
    elif (
        state.failure.recovery_pending
        or state.failure.cancellation_pending
        or state.failure.failed_worker_count > 0
        or state.failure.timeout_count > 0
    ):
        phase = SchedulerPhase.RECOVER
        reason = PhaseReason.RECOVERY_REQUIRED
    elif state.evidence.discovery_gap_count > 0:
        phase = SchedulerPhase.DISCOVER
        reason = PhaseReason.DISCOVERY_GAP
    elif state.evidence.candidate_count < state.evidence.target_candidate_count:
        phase = SchedulerPhase.DIVERGE
        reason = PhaseReason.CANDIDATE_DEFICIT
    elif state.evidence.contradiction_refs or state.evidence.dissent_refs:
        phase = SchedulerPhase.SYNTHESIZE
        reason = PhaseReason.CONTRADICTION_OR_DISSENT
    elif state.evidence.candidate_count > 1:
        phase = SchedulerPhase.CONVERGE
        reason = PhaseReason.MULTIPLE_CANDIDATES
    elif state.evidence.verification_debt_count > 0:
        phase = SchedulerPhase.VERIFY
        reason = PhaseReason.VERIFICATION_DEBT
    elif state.evidence.reduction_ready_count > 0:
        phase = SchedulerPhase.REDUCE
        reason = PhaseReason.REDUCTION_READY
    elif state.workload.ready_task_count > 0:
        phase = SchedulerPhase.EXECUTE
        reason = PhaseReason.READY_WORK
    else:
        phase = SchedulerPhase.VERIFY
        reason = PhaseReason.ASSURANCE_FALLBACK

    return PhaseDecisionV1(phase=phase, reason=reason, state_digest=state_digest)
