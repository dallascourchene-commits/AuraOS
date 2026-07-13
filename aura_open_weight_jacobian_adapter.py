"""Optional adapter for externally computed open-weight Jacobian Lens summaries.

The adapter never computes or stores raw activations, hidden states, private
reasoning, or prompts. It accepts content-addressed aggregate metrics only and
refuses mechanistic claims for gray-box or black-box endpoints.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
from typing import Any, Mapping

from aura_model_cognome import (
    MECHANISTIC_OPEN_WEIGHT,
    ModelAccessClass,
    ModelEndpointIdentity,
    ModelObservation,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    stable_digest,
    stable_id,
    validate_evidence_claim,
)

JACOBIAN_ADAPTER_VERSION = "AURA_OPEN_WEIGHT_JACOBIAN_ADAPTER_V1"
_ALLOWED_METRICS = frozenset(
    {
        "workspace_rank",
        "global_workspace_score",
        "verbalizability_score",
        "cross_layer_consistency",
        "causal_effect_size",
        "probe_accuracy",
        "representation_sparsity",
    }
)


def _finite(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class JacobianLensSummary:
    summary_id: str
    model_artifact_digest: str
    analysis_artifact_digest: str
    method_version: str
    layer_start: int
    layer_end: int
    sample_count: int
    metrics: dict[str, float]
    task_bucket: str = ""
    dataset_digest: str = ""
    code_digest: str = ""
    created_at: float = field(default_factory=time.time)
    raw_activations_stored: bool = False
    raw_prompts_stored: bool = False
    private_reasoning_stored: bool = False
    version: str = JACOBIAN_ADAPTER_VERSION

    def __post_init__(self) -> None:
        for name in ("summary_id", "model_artifact_digest", "analysis_artifact_digest", "method_version"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.layer_start < 0 or self.layer_end < self.layer_start:
            raise ValueError("Jacobian layer range is invalid")
        if self.sample_count <= 0:
            raise ValueError("sample_count must be positive")
        unknown = sorted(set(self.metrics) - _ALLOWED_METRICS)
        if unknown:
            raise ValueError("unsupported Jacobian summary metrics: " + ", ".join(unknown))
        if not self.metrics:
            raise ValueError("Jacobian summary requires at least one aggregate metric")
        for name, value in self.metrics.items():
            number = _finite(value, name)
            if name not in {"workspace_rank"} and not 0.0 <= number <= 1.0:
                raise ValueError(f"{name} must be between zero and one")
            if name == "workspace_rank" and number < 0:
                raise ValueError("workspace_rank must be non-negative")
        if self.raw_activations_stored or self.raw_prompts_stored or self.private_reasoning_stored:
            raise ValueError("Jacobian adapter accepts aggregate summaries only")
        expected = stable_digest(
            {
                "model_artifact_digest": self.model_artifact_digest,
                "method_version": self.method_version,
                "layer_start": self.layer_start,
                "layer_end": self.layer_end,
                "sample_count": self.sample_count,
                "metrics": self.metrics,
                "task_bucket": self.task_bucket,
                "dataset_digest": self.dataset_digest,
                "code_digest": self.code_digest,
            }
        )
        if expected != self.analysis_artifact_digest:
            raise ValueError("analysis_artifact_digest does not match the canonical summary")

    @classmethod
    def create(
        cls,
        *,
        model_artifact_digest: str,
        method_version: str,
        layer_start: int,
        layer_end: int,
        sample_count: int,
        metrics: Mapping[str, float],
        task_bucket: str = "",
        dataset_digest: str = "",
        code_digest: str = "",
        created_at: float | None = None,
    ) -> "JacobianLensSummary":
        clean_metrics = {str(key): float(value) for key, value in metrics.items()}
        basis = {
            "model_artifact_digest": model_artifact_digest,
            "method_version": method_version,
            "layer_start": int(layer_start),
            "layer_end": int(layer_end),
            "sample_count": int(sample_count),
            "metrics": clean_metrics,
            "task_bucket": task_bucket,
            "dataset_digest": dataset_digest,
            "code_digest": code_digest,
        }
        analysis_digest = stable_digest(basis)
        return cls(
            summary_id=stable_id("jacobian-summary", basis),
            model_artifact_digest=model_artifact_digest,
            analysis_artifact_digest=analysis_digest,
            method_version=method_version,
            layer_start=int(layer_start),
            layer_end=int(layer_end),
            sample_count=int(sample_count),
            metrics=clean_metrics,
            task_bucket=task_bucket,
            dataset_digest=dataset_digest,
            code_digest=code_digest,
            created_at=time.time() if created_at is None else float(created_at),
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "JacobianLensSummary":
        return cls(
            summary_id=str(value.get("summary_id") or ""),
            model_artifact_digest=str(value.get("model_artifact_digest") or ""),
            analysis_artifact_digest=str(value.get("analysis_artifact_digest") or ""),
            method_version=str(value.get("method_version") or ""),
            layer_start=int(value.get("layer_start") or 0),
            layer_end=int(value.get("layer_end") or 0),
            sample_count=int(value.get("sample_count") or 0),
            metrics={str(key): float(metric) for key, metric in dict(value.get("metrics") or {}).items()},
            task_bucket=str(value.get("task_bucket") or ""),
            dataset_digest=str(value.get("dataset_digest") or ""),
            code_digest=str(value.get("code_digest") or ""),
            created_at=float(value.get("created_at") or time.time()),
            raw_activations_stored=bool(value.get("raw_activations_stored", False)),
            raw_prompts_stored=bool(value.get("raw_prompts_stored", False)),
            private_reasoning_stored=bool(value.get("private_reasoning_stored", False)),
            version=str(value.get("version") or JACOBIAN_ADAPTER_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_open_weight_observation(
    endpoint: ModelEndpointIdentity,
    summary: JacobianLensSummary | Mapping[str, Any],
    *,
    call_id: str = "",
    task_context_id: str = "",
    route_decision_id: str = "",
    created_at: float | None = None,
) -> ModelObservation:
    if endpoint.access_class != ModelAccessClass.OPEN_WEIGHT.value:
        raise ValueError("Jacobian mechanistic evidence requires an OPEN_WEIGHT endpoint")
    validate_evidence_claim(endpoint.access_class, MECHANISTIC_OPEN_WEIGHT)
    packet = summary if isinstance(summary, JacobianLensSummary) else JacobianLensSummary.from_mapping(summary)
    if endpoint.endpoint_fingerprint and packet.model_artifact_digest != endpoint.endpoint_fingerprint:
        raise ValueError("Jacobian model artifact digest does not match endpoint fingerprint")
    evidence = {
        "adapter_version": JACOBIAN_ADAPTER_VERSION,
        "summary_id": packet.summary_id,
        "analysis_artifact_digest": packet.analysis_artifact_digest,
        "model_artifact_digest": packet.model_artifact_digest,
        "method_version": packet.method_version,
        "layer_range": [packet.layer_start, packet.layer_end],
        "sample_count": packet.sample_count,
        "metrics": dict(packet.metrics),
        "task_bucket": packet.task_bucket,
        "dataset_digest": packet.dataset_digest,
        "code_digest": packet.code_digest,
        "aggregate_summary_only": True,
        "raw_activations_stored": False,
        "raw_prompts_stored": False,
        "private_reasoning_stored": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    return ModelObservation.create(
        profile_id=endpoint.profile_id,
        call_id=call_id,
        task_context_id=task_context_id,
        route_decision_id=route_decision_id,
        measurement_class="MEASURED",
        evidence_class=MECHANISTIC_OPEN_WEIGHT,
        field_measurement_classes={name: "MEASURED" for name in packet.metrics},
        extra_evidence=evidence,
        created_at=packet.created_at if created_at is None else float(created_at),
    )


def persist_open_weight_observation(store: Any, endpoint: ModelEndpointIdentity, observation: ModelObservation) -> str:
    if endpoint.access_class != ModelAccessClass.OPEN_WEIGHT.value:
        raise ValueError("only OPEN_WEIGHT endpoints may persist Jacobian observations")
    if observation.profile_id != endpoint.profile_id:
        raise ValueError("observation profile does not match endpoint")
    if observation.evidence_class != MECHANISTIC_OPEN_WEIGHT:
        raise ValueError("observation is not mechanistic open-weight evidence")
    return str(store.record_observation(observation))
