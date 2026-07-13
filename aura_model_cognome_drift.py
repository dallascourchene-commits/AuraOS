"""Governed endpoint probe contracts and deterministic drift assessment.

This module evaluates explicit probe results. It has no network or provider-call
surface. Lifecycle changes require explicit approval at persistence time.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
from typing import Any, Iterable, Mapping

from aura_model_cognome import EndpointStatus, PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest, stable_id

DRIFT_VERSION = "AURA_MODEL_COGNOME_DRIFT_V1"
STABLE = "STABLE"
WARNING = "WARNING"
STALE_PROPOSED = "STALE_PROPOSED"
QUARANTINE_PROPOSED = "QUARANTINE_PROPOSED"
_ALLOWED_ASSESSMENTS = frozenset({STABLE, WARNING, STALE_PROPOSED, QUARANTINE_PROPOSED})


def _probability(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and between zero and one")
    return number


def _nonnegative(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


@dataclass(frozen=True)
class ProbeDefinition:
    probe_id: str
    name: str
    prompt_digest: str
    verifier_id: str
    expected_format_digest: str = ""
    required_capability_ids: tuple[str, ...] = ()
    max_tokens: int = 0
    timeout_ms: float = 0.0
    version: str = DRIFT_VERSION

    def __post_init__(self) -> None:
        for name in ("probe_id", "name", "prompt_digest", "verifier_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.max_tokens < 0:
            raise ValueError("max_tokens must be non-negative")
        _nonnegative(self.timeout_ms, "timeout_ms")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        prompt_digest: str,
        verifier_id: str,
        expected_format_digest: str = "",
        required_capability_ids: Iterable[str] = (),
        max_tokens: int = 0,
        timeout_ms: float = 0.0,
    ) -> "ProbeDefinition":
        capabilities = tuple(sorted({str(item) for item in required_capability_ids if str(item)}))
        basis = {
            "name": name,
            "prompt_digest": prompt_digest,
            "verifier_id": verifier_id,
            "expected_format_digest": expected_format_digest,
            "required_capability_ids": capabilities,
            "max_tokens": int(max_tokens),
            "timeout_ms": float(timeout_ms),
        }
        return cls(
            probe_id=stable_id("cognome-probe", basis),
            name=name,
            prompt_digest=prompt_digest,
            verifier_id=verifier_id,
            expected_format_digest=expected_format_digest,
            required_capability_ids=capabilities,
            max_tokens=int(max_tokens),
            timeout_ms=float(timeout_ms),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_capability_ids"] = list(self.required_capability_ids)
        return data


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    profile_id: str
    endpoint_fingerprint: str
    verifier_pass: bool
    format_valid: bool
    latency_ms: float
    error_class: str = ""
    output_digest: str = ""
    evidence_digest: str = ""
    observed_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        for name in ("probe_id", "profile_id", "endpoint_fingerprint"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        _nonnegative(self.latency_ms, "latency_ms")
        if not self.evidence_digest:
            object.__setattr__(
                self,
                "evidence_digest",
                stable_digest(
                    {
                        "probe_id": self.probe_id,
                        "profile_id": self.profile_id,
                        "endpoint_fingerprint": self.endpoint_fingerprint,
                        "verifier_pass": self.verifier_pass,
                        "format_valid": self.format_valid,
                        "latency_ms": self.latency_ms,
                        "error_class": self.error_class,
                        "output_digest": self.output_digest,
                        "observed_at": self.observed_at,
                    }
                ),
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProbeResult":
        return cls(
            probe_id=str(value.get("probe_id") or ""),
            profile_id=str(value.get("profile_id") or ""),
            endpoint_fingerprint=str(value.get("endpoint_fingerprint") or value.get("fingerprint") or ""),
            verifier_pass=bool(value.get("verifier_pass")),
            format_valid=bool(value.get("format_valid")),
            latency_ms=float(value.get("latency_ms") or 0.0),
            error_class=str(value.get("error_class") or ""),
            output_digest=str(value.get("output_digest") or ""),
            evidence_digest=str(value.get("evidence_digest") or ""),
            observed_at=float(value.get("observed_at") or time.time()),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DriftPolicy:
    warning_score: float = 0.15
    stale_score: float = 0.35
    quarantine_score: float = 0.65
    fingerprint_weight: float = 0.35
    verifier_drop_weight: float = 0.30
    format_drop_weight: float = 0.15
    error_increase_weight: float = 0.10
    latency_inflation_weight: float = 0.10
    minimum_probe_count: int = 3
    policy_version: str = DRIFT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "warning_score",
            "stale_score",
            "quarantine_score",
            "fingerprint_weight",
            "verifier_drop_weight",
            "format_drop_weight",
            "error_increase_weight",
            "latency_inflation_weight",
        ):
            _probability(getattr(self, name), name)
        if not self.warning_score <= self.stale_score <= self.quarantine_score:
            raise ValueError("drift thresholds must be monotonic")
        weight_total = sum(
            getattr(self, name)
            for name in (
                "fingerprint_weight",
                "verifier_drop_weight",
                "format_drop_weight",
                "error_increase_weight",
                "latency_inflation_weight",
            )
        )
        if not math.isclose(weight_total, 1.0, abs_tol=1e-9):
            raise ValueError("drift weights must sum to one")
        if self.minimum_probe_count <= 0:
            raise ValueError("minimum_probe_count must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DriftAssessment:
    assessment_id: str
    profile_id: str
    reference_fingerprint: str
    current_fingerprint: str
    reference_count: int
    current_count: int
    drift_score: float
    status: str
    metric_deltas: dict[str, float]
    evidence_digest: str
    policy_version: str
    reasons: tuple[str, ...] = ()
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_ASSESSMENTS:
            raise ValueError(f"unknown drift status: {self.status}")
        _probability(self.drift_score, "drift_score")
        if not self.evidence_digest:
            raise ValueError("evidence_digest must not be empty")
        if not self.proposal_only or self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority:
            raise ValueError("drift assessments cannot carry mutation authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        return data


def _aggregate(results: tuple[ProbeResult, ...]) -> dict[str, float]:
    return {
        "pass_rate": sum(1 for item in results if item.verifier_pass) / len(results),
        "format_rate": sum(1 for item in results if item.format_valid) / len(results),
        "error_rate": sum(1 for item in results if item.error_class) / len(results),
        "mean_latency_ms": sum(item.latency_ms for item in results) / len(results),
    }


def assess_drift(
    reference_results: Iterable[ProbeResult | Mapping[str, Any]],
    current_results: Iterable[ProbeResult | Mapping[str, Any]],
    *,
    policy: DriftPolicy | None = None,
    created_at: float | None = None,
) -> DriftAssessment:
    policy = policy or DriftPolicy()
    reference = tuple(item if isinstance(item, ProbeResult) else ProbeResult.from_mapping(item) for item in reference_results)
    current = tuple(item if isinstance(item, ProbeResult) else ProbeResult.from_mapping(item) for item in current_results)
    if len(reference) < policy.minimum_probe_count or len(current) < policy.minimum_probe_count:
        raise ValueError("drift assessment has insufficient probe evidence")
    profile_ids = {item.profile_id for item in (*reference, *current)}
    if len(profile_ids) != 1:
        raise ValueError("all probe results must belong to one profile")
    reference_ids = {item.probe_id for item in reference}
    current_ids = {item.probe_id for item in current}
    if reference_ids != current_ids:
        raise ValueError("reference and current probe suites must contain the same probe IDs")
    reference_fingerprints = {item.endpoint_fingerprint for item in reference}
    current_fingerprints = {item.endpoint_fingerprint for item in current}
    if len(reference_fingerprints) != 1 or len(current_fingerprints) != 1:
        raise ValueError("each probe batch must use one endpoint fingerprint")

    reference_metrics = _aggregate(reference)
    current_metrics = _aggregate(current)
    fingerprint_delta = 0.0 if reference_fingerprints == current_fingerprints else 1.0
    verifier_drop = max(0.0, reference_metrics["pass_rate"] - current_metrics["pass_rate"])
    format_drop = max(0.0, reference_metrics["format_rate"] - current_metrics["format_rate"])
    error_increase = max(0.0, current_metrics["error_rate"] - reference_metrics["error_rate"])
    reference_latency = reference_metrics["mean_latency_ms"]
    if reference_latency <= 0:
        latency_inflation = 0.0 if current_metrics["mean_latency_ms"] <= 0 else 1.0
    else:
        latency_inflation = min(1.0, max(0.0, current_metrics["mean_latency_ms"] / reference_latency - 1.0))
    metric_deltas = {
        "fingerprint_changed": fingerprint_delta,
        "verifier_pass_rate_drop": verifier_drop,
        "format_valid_rate_drop": format_drop,
        "error_rate_increase": error_increase,
        "latency_inflation": latency_inflation,
    }
    score = min(
        1.0,
        fingerprint_delta * policy.fingerprint_weight
        + verifier_drop * policy.verifier_drop_weight
        + format_drop * policy.format_drop_weight
        + error_increase * policy.error_increase_weight
        + latency_inflation * policy.latency_inflation_weight,
    )
    if score >= policy.quarantine_score:
        status = QUARANTINE_PROPOSED
    elif score >= policy.stale_score:
        status = STALE_PROPOSED
    elif score >= policy.warning_score:
        status = WARNING
    else:
        status = STABLE
    reasons = tuple(key for key, value in metric_deltas.items() if value > 0)
    evidence_basis = {
        "profile_id": next(iter(profile_ids)),
        "reference": sorted((item.probe_id, item.evidence_digest) for item in reference),
        "current": sorted((item.probe_id, item.evidence_digest) for item in current),
        "metric_deltas": metric_deltas,
        "policy": policy.to_dict(),
    }
    evidence_digest = stable_digest(evidence_basis)
    assessment_id = stable_id("drift-assessment", {"evidence_digest": evidence_digest, "status": status})
    return DriftAssessment(
        assessment_id=assessment_id,
        profile_id=next(iter(profile_ids)),
        reference_fingerprint=next(iter(reference_fingerprints)),
        current_fingerprint=next(iter(current_fingerprints)),
        reference_count=len(reference),
        current_count=len(current),
        drift_score=score,
        status=status,
        metric_deltas=metric_deltas,
        evidence_digest=evidence_digest,
        policy_version=policy.policy_version,
        reasons=reasons,
        created_at=time.time() if created_at is None else float(created_at),
    )


def persist_drift_assessment(
    store: Any,
    assessment: DriftAssessment,
    *,
    approve_lifecycle_change: bool = False,
    approved_by: str = "",
) -> str:
    """Record assessment; lifecycle mutation requires explicit named approval."""
    status = WARNING
    if assessment.status == STABLE:
        status = "STABLE"
    elif approve_lifecycle_change:
        if not str(approved_by).strip():
            raise ValueError("approved_by is required for lifecycle changes")
        if assessment.status == STALE_PROPOSED:
            status = EndpointStatus.STALE.value
        elif assessment.status == QUARANTINE_PROPOSED:
            status = EndpointStatus.QUARANTINED.value
    payload = assessment.to_dict()
    payload.update(
        {
            "status": status,
            "recommended_status": assessment.status,
            "lifecycle_change_approved": bool(approve_lifecycle_change),
            "approved_by": str(approved_by),
            "reference_fingerprint": assessment.reference_fingerprint,
            "current_fingerprint": assessment.current_fingerprint,
            "created_at": assessment.created_at,
        }
    )
    return str(store.record_drift_event(payload))
