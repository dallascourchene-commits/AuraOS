"""G2: cost-aware transfer admission for router-separated GLM-5.3 prefetch.

D0 / HS1 / NONPROMOTING.

Two other-Agent artifacts are composed without taking over their ownership:
- G1 / PR #716 owns router-separated prediction/route semantics and exact-demand
  recovery. Prediction may plan transfers but never selects executed experts.
- W4 / PR #394 owns the storage-only reuse/bandwidth feasibility algebra and the
  rule that unattested physical I/O remains UNKNOWN.

This membrane answers a narrower question: which predicted expert transfers are
worth *planning* inside a bounded prefetch window?

Latency terms are compared in seconds. Energy and physical-I/O evidence remain
separate typed planes; they are never silently converted into latency or authority.
No transfer is executed here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from math import isfinite
from typing import Any, Mapping, Sequence

from tools.awj032.glm53_io_feasibility import required_reuse
from tools.awj032.glm53_router_separated_prefetch import PrefetchPrediction

SCHEMA = "AURA-GLM53-PREFETCH-TRANSFER-ADMISSION-v1"
G1_HEAD = "0696fb43e44fdec421b0bd74abd5f7d21914df3a"
W4_HEAD = "9a1ddd1ccf0376ce8a944fde72241314b9ee7e13"

ELIGIBLE = "PREFETCH_TRANSFER_PLAN_ELIGIBLE"
SKIP_CONFIDENCE = "SKIP_CONFIDENCE_BELOW_POLICY"
SKIP_MARGIN = "SKIP_NONPOSITIVE_EXPECTED_LATENCY_MARGIN"
SKIP_WINDOW = "SKIP_PREFETCH_WINDOW_CAPACITY"
SKIP_BATCH_BYTES = "SKIP_BATCH_LOGICAL_BYTE_CAP"
SKIP_ENERGY = "SKIP_ENERGY_BUDGET"
HOLD_ENERGY = "HOLD_ENERGY_ESTIMATE_REQUIRED"
REUSE_APPLICABLE = "APPLICABLE_POSITIVE_LOGICAL_BYTES"
REUSE_NOT_APPLICABLE = "NOT_APPLICABLE_ZERO_LOGICAL_BYTES"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _positive(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name}_MUST_BE_FINITE_POSITIVE")
    return value


def _nonnegative(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name}_MUST_BE_FINITE_NONNEGATIVE")
    return value


def _probability(numerator: int, denominator: int, name: str) -> float:
    if isinstance(numerator, bool) or isinstance(denominator, bool):
        raise ValueError(f"{name}_MUST_BE_INTEGER_RATIONAL")
    if not isinstance(numerator, int) or not isinstance(denominator, int):
        raise ValueError(f"{name}_MUST_BE_INTEGER_RATIONAL")
    if denominator <= 0 or numerator < 0 or numerator > denominator:
        raise ValueError(f"{name}_MUST_BE_IN_[0,1]")
    return numerator / denominator


@dataclass(frozen=True)
class CalibratedExpertForecast:
    expert_id: int
    calibration_generation: str
    hit_probability_numerator: int
    hit_probability_denominator: int
    expected_miss_stall_seconds: float
    logical_expert_bytes: int
    estimated_transfer_energy_joules: float | None = None

    @property
    def hit_probability(self) -> float:
        return _probability(
            self.hit_probability_numerator,
            self.hit_probability_denominator,
            "FORECAST_HIT_PROBABILITY",
        )

    def validate(self) -> None:
        if isinstance(self.expert_id, bool) or not isinstance(self.expert_id, int) or self.expert_id < 0:
            raise ValueError("FORECAST_EXPERT_ID_INVALID")
        if not isinstance(self.calibration_generation, str) or not self.calibration_generation.strip():
            raise ValueError("FORECAST_CALIBRATION_GENERATION_REQUIRED")
        _ = self.hit_probability
        _positive(self.expected_miss_stall_seconds, "EXPECTED_MISS_STALL_SECONDS")
        if isinstance(self.logical_expert_bytes, bool) or not isinstance(self.logical_expert_bytes, int) or self.logical_expert_bytes <= 0:
            raise ValueError("LOGICAL_EXPERT_BYTES_MUST_BE_POSITIVE_INT")
        if self.estimated_transfer_energy_joules is not None:
            _nonnegative(self.estimated_transfer_energy_joules, "ESTIMATED_TRANSFER_ENERGY_JOULES")


@dataclass(frozen=True)
class PrefetchTransferPolicy:
    policy_generation: str
    predictor_calibration_generation: str
    layer_id: str
    binding_digest: str
    effective_storage_bandwidth_bytes_per_second: float
    prefetch_window_seconds: float
    minimum_hit_probability_numerator: int
    minimum_hit_probability_denominator: int
    eviction_penalty_seconds: float = 0.0
    rework_penalty_seconds: float = 0.0
    max_logical_prefetch_bytes: int | None = None
    max_estimated_transfer_energy_joules: float | None = None

    @property
    def minimum_hit_probability(self) -> float:
        return _probability(
            self.minimum_hit_probability_numerator,
            self.minimum_hit_probability_denominator,
            "MINIMUM_HIT_PROBABILITY",
        )

    def validate(self) -> None:
        for value, name in (
            (self.policy_generation, "POLICY_GENERATION"),
            (self.predictor_calibration_generation, "PREDICTOR_CALIBRATION_GENERATION"),
            (self.layer_id, "LAYER_ID"),
            (self.binding_digest, "BINDING_DIGEST"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name}_REQUIRED")
        _positive(
            self.effective_storage_bandwidth_bytes_per_second,
            "EFFECTIVE_STORAGE_BANDWIDTH_BYTES_PER_SECOND",
        )
        _positive(self.prefetch_window_seconds, "PREFETCH_WINDOW_SECONDS")
        _ = self.minimum_hit_probability
        _nonnegative(self.eviction_penalty_seconds, "EVICTION_PENALTY_SECONDS")
        _nonnegative(self.rework_penalty_seconds, "REWORK_PENALTY_SECONDS")
        if self.max_logical_prefetch_bytes is not None:
            if (
                isinstance(self.max_logical_prefetch_bytes, bool)
                or not isinstance(self.max_logical_prefetch_bytes, int)
                or self.max_logical_prefetch_bytes <= 0
            ):
                raise ValueError("MAX_LOGICAL_PREFETCH_BYTES_MUST_BE_POSITIVE_INT")
        if self.max_estimated_transfer_energy_joules is not None:
            _positive(
                self.max_estimated_transfer_energy_joules,
                "MAX_ESTIMATED_TRANSFER_ENERGY_JOULES",
            )


@dataclass(frozen=True)
class ExpertTransferDecision:
    expert_id: int
    disposition: str
    hit_probability: float
    logical_expert_bytes: int
    logical_transfer_seconds: float
    expected_stall_avoidance_seconds: float
    planning_latency_cost_seconds: float
    expected_latency_margin_seconds: float
    estimated_transfer_energy_joules: float | None


@dataclass(frozen=True)
class PrefetchTransferAdmissionReceipt:
    schema: str
    g1_head: str
    w4_head: str
    prediction_digest: str
    policy_generation: str
    predictor_calibration_generation: str
    layer_id: str
    binding_digest: str
    predicted_experts: tuple[int, ...]
    admitted_experts: tuple[int, ...]
    candidate_decisions: tuple[ExpertTransferDecision, ...]
    cold_predicted_logical_bytes: int
    cold_required_reuse_for_window: float | None
    cold_required_reuse_disposition: str
    admitted_logical_bytes: int
    admitted_logical_transfer_seconds: float
    admitted_expected_latency_margin_seconds: float
    admitted_estimated_energy_joules: float | None
    physical_io_attested: bool = False
    physical_prefetch_bytes: int | None = None
    physical_storage_budget_proven: bool = False
    native_route_mutated: bool = False
    model_output_semantics_changed: bool = False
    transfer_effect_authorized: bool = False
    g2_admitted: bool = False
    native_private_transformer_kv_accessed: bool = False
    semantic_k27_authority_minted: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("TRANSFER_ADMISSION_SCHEMA_MISMATCH")
        if self.cold_predicted_logical_bytes == 0:
            if self.cold_required_reuse_for_window is not None:
                raise ValueError("ZERO_BYTE_REUSE_MUST_BE_NOT_APPLICABLE")
            if self.cold_required_reuse_disposition != REUSE_NOT_APPLICABLE:
                raise ValueError("ZERO_BYTE_REUSE_DISPOSITION_MISMATCH")
        elif self.cold_predicted_logical_bytes > 0:
            if self.cold_required_reuse_for_window is None:
                raise ValueError("POSITIVE_BYTE_REUSE_VALUE_REQUIRED")
            if self.cold_required_reuse_disposition != REUSE_APPLICABLE:
                raise ValueError("POSITIVE_BYTE_REUSE_DISPOSITION_MISMATCH")
        else:
            raise ValueError("COLD_PREDICTED_LOGICAL_BYTES_MUST_BE_NONNEGATIVE")
        if self.physical_io_attested is not False or self.physical_prefetch_bytes is not None:
            raise ValueError("TRANSFER_ADMISSION_CANNOT_SELF_ATTEST_PHYSICAL_IO")
        if self.physical_storage_budget_proven is not False:
            raise ValueError("TRANSFER_ADMISSION_CANNOT_PROVE_PHYSICAL_STORAGE_BUDGET")
        if any((
            self.native_route_mutated,
            self.model_output_semantics_changed,
            self.transfer_effect_authorized,
            self.g2_admitted,
            self.native_private_transformer_kv_accessed,
            self.semantic_k27_authority_minted,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )):
            raise ValueError("TRANSFER_ADMISSION_CANNOT_WIDEN_EXECUTION_OR_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def admit_prefetch_transfers(
    *,
    prediction: PrefetchPrediction,
    forecasts: Sequence[CalibratedExpertForecast],
    policy: PrefetchTransferPolicy,
    num_experts: int,
) -> PrefetchTransferAdmissionReceipt:
    """Choose a deterministic planning subset without executing any transfer.

    Ranking is by expected latency margin descending, then expert id. This is a
    deterministic bounded heuristic, not a claim of global knapsack optimality.

    A lawful predictor abstention is represented as an empty predicted set. With
    no speculative bytes, W4's positive-byte reuse equation has no input in its
    mathematical domain. Reuse feasibility is therefore explicitly NOT_APPLICABLE,
    not numerical zero. Zero transfer bytes/time remain ordinary additive zeros.
    """
    prediction.validate(num_experts=num_experts)
    policy.validate()
    if prediction.layer_id != policy.layer_id:
        raise ValueError("PREDICTION_POLICY_LAYER_MISMATCH")
    if prediction.binding_digest != policy.binding_digest:
        raise ValueError("PREDICTION_POLICY_BINDING_MISMATCH")

    by_expert: dict[int, CalibratedExpertForecast] = {}
    for forecast in forecasts:
        forecast.validate()
        if forecast.expert_id in by_expert:
            raise ValueError("DUPLICATE_FORECAST_EXPERT")
        if forecast.calibration_generation != policy.predictor_calibration_generation:
            raise ValueError("FORECAST_CALIBRATION_GENERATION_MISMATCH")
        by_expert[forecast.expert_id] = forecast
    if set(by_expert) != set(prediction.predicted_experts):
        raise ValueError("FORECAST_SET_MUST_EQUAL_PREDICTED_EXPERT_SET")

    bandwidth = policy.effective_storage_bandwidth_bytes_per_second
    cold_bytes = sum(by_expert[e].logical_expert_bytes for e in prediction.predicted_experts)
    if cold_bytes == 0:
        cold_reuse_needed = None
        cold_reuse_disposition = REUSE_NOT_APPLICABLE
    else:
        cold_reuse_needed = required_reuse(
            logical_expert_bytes_required=cold_bytes,
            effective_storage_bandwidth_bytes_per_second=bandwidth,
            target_expert_io_seconds=policy.prefetch_window_seconds,
        )
        cold_reuse_disposition = REUSE_APPLICABLE

    evaluated: list[tuple[CalibratedExpertForecast, ExpertTransferDecision]] = []
    for expert_id in prediction.predicted_experts:
        forecast = by_expert[expert_id]
        transfer_seconds = forecast.logical_expert_bytes / bandwidth
        expected_avoidance = forecast.hit_probability * forecast.expected_miss_stall_seconds
        planning_cost = transfer_seconds + policy.eviction_penalty_seconds + policy.rework_penalty_seconds
        margin = expected_avoidance - planning_cost
        if forecast.hit_probability < policy.minimum_hit_probability:
            disposition = SKIP_CONFIDENCE
        elif margin <= 0:
            disposition = SKIP_MARGIN
        elif policy.max_estimated_transfer_energy_joules is not None and forecast.estimated_transfer_energy_joules is None:
            disposition = HOLD_ENERGY
        elif (
            policy.max_estimated_transfer_energy_joules is not None
            and forecast.estimated_transfer_energy_joules is not None
            and forecast.estimated_transfer_energy_joules > policy.max_estimated_transfer_energy_joules
        ):
            disposition = SKIP_ENERGY
        else:
            disposition = ELIGIBLE
        evaluated.append((
            forecast,
            ExpertTransferDecision(
                expert_id=expert_id,
                disposition=disposition,
                hit_probability=forecast.hit_probability,
                logical_expert_bytes=forecast.logical_expert_bytes,
                logical_transfer_seconds=transfer_seconds,
                expected_stall_avoidance_seconds=expected_avoidance,
                planning_latency_cost_seconds=planning_cost,
                expected_latency_margin_seconds=margin,
                estimated_transfer_energy_joules=forecast.estimated_transfer_energy_joules,
            ),
        ))

    candidates = [item for item in evaluated if item[1].disposition == ELIGIBLE]
    candidates.sort(key=lambda item: (-item[1].expected_latency_margin_seconds, item[0].expert_id))

    admitted: set[int] = set()
    used_seconds = 0.0
    used_bytes = 0
    used_energy = 0.0
    energy_known = True
    final_by_expert = {decision.expert_id: decision for _, decision in evaluated}

    for forecast, decision in candidates:
        next_seconds = used_seconds + decision.logical_transfer_seconds
        if next_seconds > policy.prefetch_window_seconds + 1e-12:
            final_by_expert[forecast.expert_id] = ExpertTransferDecision(
                **{**asdict(decision), "disposition": SKIP_WINDOW}
            )
            continue
        next_bytes = used_bytes + forecast.logical_expert_bytes
        if policy.max_logical_prefetch_bytes is not None and next_bytes > policy.max_logical_prefetch_bytes:
            final_by_expert[forecast.expert_id] = ExpertTransferDecision(
                **{**asdict(decision), "disposition": SKIP_BATCH_BYTES}
            )
            continue
        if policy.max_estimated_transfer_energy_joules is not None:
            assert forecast.estimated_transfer_energy_joules is not None
            if used_energy + forecast.estimated_transfer_energy_joules > policy.max_estimated_transfer_energy_joules:
                final_by_expert[forecast.expert_id] = ExpertTransferDecision(
                    **{**asdict(decision), "disposition": SKIP_ENERGY}
                )
                continue
        admitted.add(forecast.expert_id)
        used_seconds = next_seconds
        used_bytes = next_bytes
        if forecast.estimated_transfer_energy_joules is None:
            energy_known = False
        else:
            used_energy += forecast.estimated_transfer_energy_joules

    ordered_decisions = tuple(final_by_expert[e] for e in prediction.predicted_experts)
    admitted_experts = tuple(e for e in prediction.predicted_experts if e in admitted)
    margin_total = sum(final_by_expert[e].expected_latency_margin_seconds for e in admitted_experts)
    receipt = PrefetchTransferAdmissionReceipt(
        schema=SCHEMA,
        g1_head=G1_HEAD,
        w4_head=W4_HEAD,
        prediction_digest=prediction.digest,
        policy_generation=policy.policy_generation,
        predictor_calibration_generation=policy.predictor_calibration_generation,
        layer_id=prediction.layer_id,
        binding_digest=prediction.binding_digest,
        predicted_experts=prediction.predicted_experts,
        admitted_experts=admitted_experts,
        candidate_decisions=ordered_decisions,
        cold_predicted_logical_bytes=cold_bytes,
        cold_required_reuse_for_window=cold_reuse_needed,
        cold_required_reuse_disposition=cold_reuse_disposition,
        admitted_logical_bytes=used_bytes,
        admitted_logical_transfer_seconds=used_seconds,
        admitted_expected_latency_margin_seconds=margin_total,
        admitted_estimated_energy_joules=used_energy if energy_known else None,
    )
    receipt.validate_claim_ceiling()
    return receipt
