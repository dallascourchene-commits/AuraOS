"""W3 guard binding G2 calibration policy to the predictor that emitted a prediction.

D0 / HS1 / NONPROMOTING.

G2's first exact-green generation binds each forecast to a calibration generation and
binds prediction/policy by layer and source, but it does not prove that the calibration
generation belongs to the predictor generation that produced the prediction. A stale
or different predictor can therefore reuse another predictor's calibration identity.

This guard owns only that missing identity relation and delegates cost admission to G2
unchanged after the relation is proven.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from tools.awj032 import glm53_prefetch_transfer_admission as g2
from tools.awj032.glm53_router_separated_prefetch import PrefetchPrediction

SCHEMA = "AURA-GLM53-G2-PREDICTOR-CALIBRATION-BINDING-v1"


@dataclass(frozen=True)
class PredictorCalibrationBinding:
    schema: str
    predictor_generation: str
    calibration_generation: str
    policy_generation: str
    layer_id: str
    source_binding_digest: str
    current: bool
    execution_authorized: bool = False
    transfer_effect_authorized: bool = False
    semantic_k27_authority: bool = False

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("G2_CALIBRATION_BINDING_SCHEMA_MISMATCH")
        for value, name in (
            (self.predictor_generation, "PREDICTOR_GENERATION"),
            (self.calibration_generation, "CALIBRATION_GENERATION"),
            (self.policy_generation, "POLICY_GENERATION"),
            (self.layer_id, "LAYER_ID"),
            (self.source_binding_digest, "SOURCE_BINDING_DIGEST"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"G2_CALIBRATION_BINDING_{name}_REQUIRED")
        if self.current is not True:
            raise ValueError("G2_CALIBRATION_BINDING_MUST_BE_CURRENT")
        if self.execution_authorized or self.transfer_effect_authorized or self.semantic_k27_authority:
            raise ValueError("G2_CALIBRATION_BINDING_CANNOT_AUTHORIZE_EFFECTS")


def admit_prefetch_transfers_predictor_bound(
    *,
    prediction: PrefetchPrediction,
    forecasts: Sequence[g2.CalibratedExpertForecast],
    policy: g2.PrefetchTransferPolicy,
    binding: PredictorCalibrationBinding,
    num_experts: int,
) -> g2.PrefetchTransferAdmissionReceipt:
    """Admit a G2 transfer plan only after exact predictor↔calibration binding."""
    binding.validate()
    if prediction.predictor_generation != binding.predictor_generation:
        raise ValueError("G2_PREDICTION_PREDICTOR_GENERATION_NOT_CALIBRATION_BOUND")
    if policy.predictor_calibration_generation != binding.calibration_generation:
        raise ValueError("G2_POLICY_CALIBRATION_GENERATION_NOT_BINDING")
    if policy.policy_generation != binding.policy_generation:
        raise ValueError("G2_POLICY_GENERATION_NOT_CALIBRATION_BOUND")
    if prediction.layer_id != binding.layer_id or policy.layer_id != binding.layer_id:
        raise ValueError("G2_CALIBRATION_BINDING_LAYER_MISMATCH")
    if prediction.binding_digest != binding.source_binding_digest or policy.binding_digest != binding.source_binding_digest:
        raise ValueError("G2_CALIBRATION_BINDING_SOURCE_MISMATCH")
    for forecast in forecasts:
        if forecast.calibration_generation != binding.calibration_generation:
            raise ValueError("G2_FORECAST_CALIBRATION_NOT_EXACT_BINDING")

    receipt = g2.admit_prefetch_transfers(
        prediction=prediction,
        forecasts=forecasts,
        policy=policy,
        num_experts=num_experts,
    )
    receipt.validate_claim_ceiling()
    return receipt


LAWS = (
    "CalibrationGeneration!=PredictorGeneration",
    "SameLayerAndSource!=CalibrationApplicability",
    "PredictionGeneration+CalibrationGeneration+PolicyGenerationMustCommute",
    "PredictorCalibrationBinding!=TransferAuthority",
    "K27Coordinate!=CalibrationCurrentness!=ExecutionAuthority",
)
