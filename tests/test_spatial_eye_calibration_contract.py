import importlib.util
import math
import sys
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'spatial' / 'eye_calibration_contract.py'
spec = importlib.util.spec_from_file_location('eye_calibration_contract', MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class EyeCalibrationContractTests(unittest.TestCase):
    def test_imported_64mm_population_ipd_never_becomes_user_truth(self):
        ipd = mod.assumed_population_ipd()
        self.assertEqual(ipd.ipd_m, 0.064)
        self.assertFalse(ipd.metric_eye_origin_eligible)
        with self.assertRaises(mod.CalibrationContractError):
            ipd.eye_origins_about_midpoint()

    def test_nominal_fov_intrinsics_never_emit_metric_ray(self):
        intrinsics = mod.nominal_intrinsics_from_horizontal_fov(
            width_px=1920, height_px=1080, horizontal_fov_deg=90.0
        )
        self.assertFalse(intrinsics.metric_ray_eligible)
        with self.assertRaises(mod.CalibrationContractError):
            intrinsics.unit_ray_from_undistorted_pixel(960, 540)

    def test_calibrated_intrinsics_and_measured_ipd_admit_metric_geometry(self):
        intrinsics = mod.CameraIntrinsicsV1(
            width_px=1920,
            height_px=1080,
            fx_px=1100.0,
            fy_px=1098.0,
            cx_px=959.5,
            cy_px=539.5,
            source=mod.IntrinsicsSource.CALIBRATED,
            calibration_ref='calibration:camera:rev7',
            reprojection_rms_px=0.31,
            pixels_are_undistorted=True,
        )
        binocular = mod.BinocularCalibrationV1(
            ipd_m=0.0632,
            ipd_sigma_m=0.0004,
            midpoint_sigma_m=0.0007,
            source=mod.IpdSource.MEASURED_USER,
            calibration_ref='calibration:user-ipd:rev3',
        )
        receipt = mod.eligibility_receipt(intrinsics, binocular)
        self.assertTrue(receipt.metric_geometry_eligible)
        left, right = binocular.eye_origins_about_midpoint()
        self.assertAlmostEqual(right[0] - left[0], 0.0632)
        ray = intrinsics.unit_ray_from_undistorted_pixel(959.5, 539.5)
        self.assertAlmostEqual(ray[0], 0.0)
        self.assertAlmostEqual(ray[1], 0.0)
        self.assertAlmostEqual(ray[2], 1.0)

    def test_eye_origin_uncertainty_is_propagated_not_dropped(self):
        binocular = mod.BinocularCalibrationV1(
            ipd_m=0.064,
            ipd_sigma_m=0.002,
            midpoint_sigma_m=0.003,
            source=mod.IpdSource.MEASURED_USER,
            calibration_ref='calibration:user-ipd:test',
        )
        expected = math.sqrt(0.003**2 + 0.001**2)
        self.assertAlmostEqual(binocular.eye_origin_sigma_m, expected)

    def test_receipt_preserves_renderer_privacy_and_accuracy_ceiling(self):
        receipt = mod.eligibility_receipt(
            mod.nominal_intrinsics_from_horizontal_fov(
                width_px=1280, height_px=720, horizontal_fov_deg=78.0
            ),
            mod.assumed_population_ipd(),
        )
        self.assertFalse(receipt.metric_geometry_eligible)
        self.assertFalse(receipt.renderer_pose_part_of_calibration_identity)
        self.assertFalse(receipt.fixed_64mm_ipd_is_user_ground_truth)
        self.assertFalse(receipt.nominal_fov_is_calibrated_intrinsics)
        self.assertFalse(receipt.raw_sensor_persistence_authorized)
        self.assertFalse(receipt.physical_gaze_accuracy_proven)
        self.assertFalse(receipt.vergence_accommodation_conflict_eliminated)
        self.assertFalse(receipt.semantic_k27_authority)
        self.assertFalse(receipt.native_transformer_kv_accessed)
        self.assertEqual(len(receipt.receipt_sha256), 64)

    def test_calibrated_intrinsics_require_reprojection_error(self):
        with self.assertRaises(mod.CalibrationContractError):
            mod.CameraIntrinsicsV1(
                width_px=640,
                height_px=480,
                fx_px=500,
                fy_px=500,
                cx_px=319.5,
                cy_px=239.5,
                source=mod.IntrinsicsSource.CALIBRATED,
                calibration_ref='calibration:missing-rms',
                reprojection_rms_px=None,
                pixels_are_undistorted=True,
            )

    def test_out_of_bounds_ipd_fails_closed(self):
        for ipd in (0.01, 0.2):
            with self.assertRaises(mod.CalibrationContractError):
                mod.BinocularCalibrationV1(
                    ipd_m=ipd,
                    ipd_sigma_m=0.001,
                    midpoint_sigma_m=0.001,
                    source=mod.IpdSource.MEASURED_USER,
                    calibration_ref='calibration:test',
                )


if __name__ == '__main__':
    unittest.main()
