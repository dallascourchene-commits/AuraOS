import importlib.util
import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "spatial" / "eye_calibration_contract.py"
spec = importlib.util.spec_from_file_location("eye_calibration_contract", MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def policy():
    return mod.CalibrationQualityPolicyV1(
        policy_generation="test-policy-7",
        min_camera_samples=6,
        max_camera_reprojection_rms_px=0.5,
        min_ipd_samples=3,
        max_ipd_sample_sigma_m=0.002,
    )


def camera_dataset(*, noise=0.0, space=None):
    fx, fy, cx, cy = 900.0, 1200.0, 500.0, 400.0
    pts = ((-0.4,-0.3),(-0.2,0.2),(0.0,-0.1),(0.1,0.3),(0.3,-0.25),(0.45,0.1))
    samples = []
    for i,(x,y) in enumerate(pts):
        n = noise if i % 2 == 0 else -noise
        samples.append(mod.CameraCalibrationSampleV1(x,y,fx*x+cx+n,fy*y+cy-n))
    return mod.CameraCalibrationDatasetV1(
        sensor_id="cam-7",
        sensor_generation="runtime-11",
        calibration_generation="cal-19",
        width_px=1280,
        height_px=720,
        coordinate_space=space or mod.CoordinateSpace.UNDISTORTED_PINHOLE_PIXELS_V1,
        samples=tuple(samples),
    )


def ipd_dataset(samples=(0.0630,0.0632,0.0631)):
    return mod.IpdMeasurementDatasetV1(
        sensor_id="ipd-device-2",
        sensor_generation="runtime-4",
        calibration_generation="ipd-cal-5",
        coordinate_space="HEAD_LOCAL_METERS_V1",
        ipd_samples_m=tuple(samples),
        midpoint_sigma_m=0.0007,
    )


class EyeCalibrationProducerTraversalTests(unittest.TestCase):
    def test_arbitrary_refs_or_enums_no_longer_exist_as_metric_admission_surface(self):
        self.assertNotIn("calibration_ref", mod.CameraIntrinsicsV2.__dataclass_fields__)
        self.assertNotIn("source", mod.CameraIntrinsicsV2.__dataclass_fields__)
        self.assertNotIn("calibration_ref", mod.BinocularCalibrationV2.__dataclass_fields__)
        self.assertNotIn("source", mod.BinocularCalibrationV2.__dataclass_fields__)

    def test_camera_producer_recomputes_anisotropic_intrinsics(self):
        e = mod.produce_camera_calibration_evidence(camera_dataset(), policy())
        self.assertTrue(e.quality_admitted)
        self.assertAlmostEqual(e.fx_px, 900.0)
        self.assertAlmostEqual(e.fy_px, 1200.0)
        self.assertAlmostEqual(e.cx_px, 500.0)
        self.assertAlmostEqual(e.cy_px, 400.0)
        self.assertTrue(mod.verify_camera_calibration_evidence(e))
        ray = mod.CameraIntrinsicsV2(e).unit_ray_from_undistorted_pixel(500.0, 400.0)
        self.assertAlmostEqual(ray[0], 0.0)
        self.assertAlmostEqual(ray[1], 0.0)
        self.assertAlmostEqual(ray[2], 1.0)

    def test_camera_result_field_forgery_fails_recompute(self):
        e = mod.produce_camera_calibration_evidence(camera_dataset(), policy())
        forged = replace(e, fx_px=e.fx_px + 50.0)
        self.assertFalse(mod.verify_camera_calibration_evidence(forged))
        with self.assertRaises(mod.CalibrationContractError):
            mod.CameraIntrinsicsV2(forged).unit_ray_from_undistorted_pixel(500, 400)

    def test_raw_distorted_coordinate_space_is_rejected_by_pinhole_producer(self):
        d = camera_dataset(space=mod.CoordinateSpace.RAW_DISTORTED_PIXELS_V1)
        with self.assertRaises(mod.CalibrationContractError):
            mod.produce_camera_calibration_evidence(d, policy())

    def test_quality_policy_is_separate_from_observed_rms(self):
        d = camera_dataset(noise=0.4)
        strict = replace(policy(), max_camera_reprojection_rms_px=0.1)
        loose = replace(policy(), max_camera_reprojection_rms_px=1.0)
        es = mod.produce_camera_calibration_evidence(d, strict)
        el = mod.produce_camera_calibration_evidence(d, loose)
        self.assertAlmostEqual(es.reprojection_rms_px, el.reprojection_rms_px)
        self.assertFalse(es.quality_admitted)
        self.assertTrue(el.quality_admitted)
        self.assertNotEqual(es.evidence_sha256, el.evidence_sha256)

    def test_ipd_producer_recomputes_measurement_and_uncertainty(self):
        e = mod.produce_ipd_calibration_evidence(ipd_dataset(), policy())
        self.assertTrue(mod.verify_ipd_calibration_evidence(e))
        b = mod.BinocularCalibrationV2(e)
        self.assertTrue(b.metric_eye_origin_eligible)
        left, right = b.eye_origins_about_midpoint()
        self.assertAlmostEqual(right[0] - left[0], e.ipd_m)
        expected = math.sqrt(e.midpoint_sigma_m**2 + (0.5*e.ipd_mean_sigma_m)**2)
        self.assertAlmostEqual(b.eye_origin_sigma_m, expected)

    def test_ipd_result_field_forgery_fails_recompute(self):
        e = mod.produce_ipd_calibration_evidence(ipd_dataset(), policy())
        forged = replace(e, ipd_m=0.08)
        self.assertFalse(mod.verify_ipd_calibration_evidence(forged))
        self.assertFalse(mod.BinocularCalibrationV2(forged).metric_eye_origin_eligible)

    def test_population_ipd_and_nominal_fov_remain_nonmetric(self):
        self.assertFalse(mod.assumed_population_ipd()["metric_eye_origin_eligible"])
        self.assertFalse(mod.nominal_intrinsics_from_horizontal_fov(
            width_px=1280, height_px=720, horizontal_fov_deg=80.0
        )["metric_ray_eligible"])

    def test_bool_int_substitutions_fail_closed(self):
        with self.assertRaises(mod.CalibrationContractError):
            mod.nominal_intrinsics_from_horizontal_fov(width_px=True, height_px=720, horizontal_fov_deg=80.0)
        with self.assertRaises(mod.CalibrationContractError):
            mod.CameraCalibrationSampleV1(True, 0.1, 1.0, 2.0)

    def test_receipt_preserves_physical_and_authority_ceiling(self):
        p = policy()
        r = mod.eligibility_receipt(
            mod.CameraIntrinsicsV2(mod.produce_camera_calibration_evidence(camera_dataset(), p)),
            mod.BinocularCalibrationV2(mod.produce_ipd_calibration_evidence(ipd_dataset(), p)),
        )
        self.assertTrue(r["metric_geometry_eligible"])
        self.assertTrue(r["camera_producer_traversed"])
        self.assertTrue(r["ipd_producer_traversed"])
        self.assertTrue(r["quality_policy_separate_from_measurement"])
        for field in (
            "physical_calibration_producer_authenticated",
            "physical_gaze_accuracy_proven",
            "physical_3d_accuracy_proven",
            "raw_sensor_persistence_authorized",
            "semantic_k27_authority",
            "native_transformer_kv_accessed",
        ):
            self.assertFalse(r[field])


if __name__ == "__main__":
    unittest.main()
