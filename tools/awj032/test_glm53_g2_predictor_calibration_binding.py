from __future__ import annotations

from dataclasses import replace
import unittest

from tools.awj032.glm53_router_separated_prefetch import PREFETCH_SCHEMA, PrefetchPrediction
from tools.awj032 import glm53_prefetch_transfer_admission as g2
from tools.awj032.glm53_g2_predictor_calibration_binding import (
    SCHEMA,
    PredictorCalibrationBinding,
    admit_prefetch_transfers_predictor_bound,
)


def prediction(*, predictor="predictor:g2:v1", layer="layer:07", source="binding:g2:source"):
    return PrefetchPrediction(
        schema=PREFETCH_SCHEMA,
        predictor_generation=predictor,
        layer_id=layer,
        binding_digest=source,
        predicted_experts=(0, 1),
    )


def forecast(expert: int, *, calibration="calibration:g2:v1"):
    return g2.CalibratedExpertForecast(
        expert_id=expert,
        calibration_generation=calibration,
        hit_probability_numerator=9,
        hit_probability_denominator=10,
        expected_miss_stall_seconds=0.02,
        logical_expert_bytes=1_000_000,
    )


def policy(**updates):
    base = dict(
        policy_generation="policy:g2:v1",
        predictor_calibration_generation="calibration:g2:v1",
        layer_id="layer:07",
        binding_digest="binding:g2:source",
        effective_storage_bandwidth_bytes_per_second=1_000_000_000.0,
        prefetch_window_seconds=0.01,
        minimum_hit_probability_numerator=1,
        minimum_hit_probability_denominator=2,
    )
    base.update(updates)
    return g2.PrefetchTransferPolicy(**base)


def binding(**updates):
    base = dict(
        schema=SCHEMA,
        predictor_generation="predictor:g2:v1",
        calibration_generation="calibration:g2:v1",
        policy_generation="policy:g2:v1",
        layer_id="layer:07",
        source_binding_digest="binding:g2:source",
        current=True,
    )
    base.update(updates)
    return PredictorCalibrationBinding(**base)


class G2PredictorCalibrationBindingTests(unittest.TestCase):
    def run(self, *, p=None, fs=None, pol=None, b=None):
        return admit_prefetch_transfers_predictor_bound(
            prediction=p or prediction(),
            forecasts=fs or [forecast(0), forecast(1)],
            policy=pol or policy(),
            binding=b or binding(),
            num_experts=8,
        )

    def test_exact_binding_preserves_g2_nonpromoting_admission(self):
        receipt = self.run()
        self.assertEqual((0, 1), receipt.admitted_experts)
        self.assertFalse(receipt.transfer_effect_authorized)
        self.assertFalse(receipt.g2_admitted)
        self.assertFalse(receipt.semantic_k27_authority_minted)

    def test_different_predictor_cannot_reuse_calibration(self):
        with self.assertRaisesRegex(ValueError, "G2_PREDICTION_PREDICTOR_GENERATION_NOT_CALIBRATION_BOUND"):
            self.run(p=prediction(predictor="predictor:g2:v2"))

    def test_policy_calibration_or_policy_generation_cross_cast_rejected(self):
        with self.assertRaisesRegex(ValueError, "G2_POLICY_CALIBRATION_GENERATION_NOT_BINDING"):
            self.run(pol=policy(predictor_calibration_generation="calibration:other"))
        with self.assertRaisesRegex(ValueError, "G2_POLICY_GENERATION_NOT_CALIBRATION_BOUND"):
            self.run(pol=policy(policy_generation="policy:g2:v2"))

    def test_layer_and_source_relation_must_commute(self):
        with self.assertRaisesRegex(ValueError, "G2_CALIBRATION_BINDING_LAYER_MISMATCH"):
            self.run(b=binding(layer_id="layer:08"))
        with self.assertRaisesRegex(ValueError, "G2_CALIBRATION_BINDING_SOURCE_MISMATCH"):
            self.run(b=binding(source_binding_digest="binding:other"))

    def test_forecast_calibration_must_equal_binding(self):
        with self.assertRaisesRegex(ValueError, "G2_FORECAST_CALIBRATION_NOT_EXACT_BINDING"):
            self.run(fs=[forecast(0), forecast(1, calibration="calibration:other")])

    def test_stale_or_authority_widened_binding_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "G2_CALIBRATION_BINDING_MUST_BE_CURRENT"):
            self.run(b=binding(current=False))
        for field in ("execution_authorized", "transfer_effect_authorized", "semantic_k27_authority"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "G2_CALIBRATION_BINDING_CANNOT_AUTHORIZE_EFFECTS"):
                    self.run(b=binding(**{field: True}))


if __name__ == "__main__":
    unittest.main()
