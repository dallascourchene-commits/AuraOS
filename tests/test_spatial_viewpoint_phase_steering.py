from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import unittest


def load_child():
    path = pathlib.Path("tools/spatial/viewpoint_phase_steering_witness.py")
    spec = importlib.util.spec_from_file_location("viewpoint_phase_steering_witness", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ViewpointPhaseSteeringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.child = load_child()
        eye_path = pathlib.Path(os.environ["PR621_EYE_MODULE"])
        optics_path = pathlib.Path(os.environ["PR620_OPTICS_MODULE"])
        cls.eye, cls.optics = cls.child.load_exact_parents(
            eye_module_path=eye_path,
            optics_module_path=optics_path,
        )

    def measured_binocular(self):
        return self.eye.BinocularCalibrationV1(
            ipd_m=0.064,
            ipd_sigma_m=0.0005,
            midpoint_sigma_m=0.001,
            source=self.eye.IpdSource.MEASURED_USER,
            calibration_ref="fixture:measured-user-ipd:v1",
        )

    def identity_transform(self, z=0.35):
        return self.child.DeclaredRigidTransformV1(
            rotation_row_major=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            translation_m=(0.0, 0.0, z),
            frame_binding_id="fixture:binocular-midpoint-to-display:v1",
        )

    def query(self, eye="LEFT"):
        return self.child.SteeringQueryV1(
            selected_eye=eye,
            sample_x_m=0.0002,
            sample_y_m=-0.0001,
            wavelength_m=532e-9,
            base_phase_radians=0.15,
        )

    def witness(self, *, eye="LEFT", transform=None, binocular=None):
        return self.child.build_viewpoint_phase_steering_witness(
            eye_module=self.eye,
            optics_module=self.optics,
            binocular_calibration=binocular or self.measured_binocular(),
            transform=transform or self.identity_transform(),
            query=self.query(eye),
        )

    def test_measured_user_viewpoint_builds_valid_receipt(self):
        receipt = self.witness()
        self.assertTrue(self.child.verify_receipt(receipt))
        self.assertEqual(receipt.binocular_source, "MEASURED_USER")
        self.assertTrue(receipt.software_phase_conformance)
        self.assertLessEqual(receipt.circular_phase_error_radians, 1e-9)

    def test_population_ipd_assumption_cannot_drive_viewpoint(self):
        assumed = self.eye.assumed_population_ipd()
        with self.assertRaisesRegex(self.child.ViewpointSteeringError, "MEASURED_USER_REQUIRED"):
            self.witness(binocular=assumed)

    def test_left_and_right_eye_yield_distinct_phase_on_asymmetric_sample(self):
        left = self.witness(eye="LEFT")
        right = self.witness(eye="RIGHT")
        self.assertNotEqual(left.selected_eye_display_m, right.selected_eye_display_m)
        self.assertNotAlmostEqual(
            left.independent_phase_radians,
            right.independent_phase_radians,
            places=10,
        )

    def test_frame_binding_changes_receipt_and_phase(self):
        a = self.witness()
        moved = self.child.DeclaredRigidTransformV1(
            rotation_row_major=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
            translation_m=(0.01, 0.0, 0.35),
            frame_binding_id="fixture:shifted-binding:v2",
        )
        b = self.witness(transform=moved)
        self.assertNotEqual(a.frame_binding_digest, b.frame_binding_digest)
        self.assertNotEqual(a.receipt_sha256, b.receipt_sha256)
        self.assertNotAlmostEqual(a.independent_phase_radians, b.independent_phase_radians, places=10)

    def test_reflection_is_not_a_proper_rigid_transform(self):
        with self.assertRaisesRegex(self.child.ViewpointSteeringError, "PROPER_RIGID_TRANSFORM_REQUIRED"):
            self.child.DeclaredRigidTransformV1(
                rotation_row_major=(-1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
                translation_m=(0.0, 0.0, 0.35),
                frame_binding_id="fixture:reflection",
            )

    def test_nonorthogonal_rotation_fails_closed(self):
        with self.assertRaises(self.child.ViewpointSteeringError):
            self.child.DeclaredRigidTransformV1(
                rotation_row_major=(1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0),
                translation_m=(0.0, 0.0, 0.35),
                frame_binding_id="fixture:bad-rotation",
            )

    def test_eye_behind_display_frame_fails_closed(self):
        behind = self.identity_transform(z=-0.01)
        with self.assertRaisesRegex(self.child.ViewpointSteeringError, "POSITIVE_REQUIRED"):
            self.witness(transform=behind)

    def test_tampered_receipt_fails(self):
        receipt = self.witness()
        tampered = self.child.ViewpointPhaseSteeringReceiptV1(
            **{**receipt.__dict__, "physical_display_observed": True}
        )
        self.assertFalse(self.child.verify_receipt(tampered))

    def test_negative_ceiling_is_complete(self):
        receipt = self.witness()
        for key in (
            "physical_extrinsics_calibrated",
            "gaze_direction_observed",
            "physical_gaze_accuracy_proven",
            "raw_sensor_persistence_authorized",
            "physical_display_observed",
            "holographic_parallax_perception_proven",
            "vergence_accommodation_conflict_eliminated",
            "speckle_suppression_proven",
            "optical_safety_proven",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "effect_authority",
            "gate10_promoted",
        ):
            self.assertIs(getattr(receipt, key), False, key)


if __name__ == "__main__":
    unittest.main()
