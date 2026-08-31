#!/usr/bin/env python3
"""Software-only junction from metric binocular geometry to phase steering.

This adapter deliberately consumes exact external owners at runtime instead of
reimplementing their calibration or optics semantics. It turns a measured-user
binocular baseline plus an explicit *declared software* rigid-frame binding into
one viewpoint-dependent phase-steering witness.

It is not a gaze estimator, physical extrinsics calibration, holographic display,
perceptual-parallax proof, or effect authorization surface.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
from types import ModuleType
from typing import Sequence

SCHEMA = "AURA_SPATIAL_VIEWPOINT_PHASE_STEERING_V1"
PR621_EXACT_HEAD = "944c4e52be670d251ebf43b05558f7fab275bed2"
PR621_BLOB = "eba22a2fe052be27731d808a5c0b9f31ea9dc7bb"
PR621_RUN = 33365864866
PR620_EXACT_HEAD = "1a4c3f6705964428b1d80f2bbd3f5ada8c000f8b"
PR620_BLOB = "5aacc34ef9fba08ebedefd77efc964f92e6e3bbb"
PR620_DEP_BLOB = "076080018f586bb10a0d9e18561d17db79c71f5a"
PR620_RUN = 33365731815


class ViewpointSteeringError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ViewpointSteeringError(f"{name}:FINITE_NUMBER_REQUIRED")
    out = float(value)
    if not math.isfinite(out):
        raise ViewpointSteeringError(f"{name}:FINITE_NUMBER_REQUIRED")
    return out


def _load_module(name: str, path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_exact_parents(
    *, eye_module_path: pathlib.Path, optics_module_path: pathlib.Path
) -> tuple[ModuleType, ModuleType]:
    # PR620 imports its exact candidate-falsifier dependency by module name.
    optics_parent_dir = str(optics_module_path.parent)
    if optics_parent_dir not in sys.path:
        sys.path.insert(0, optics_parent_dir)
    eye = _load_module("aura_pr621_eye_calibration", eye_module_path)
    optics = _load_module("aura_pr620_optics_conformance", optics_module_path)
    return eye, optics


@dataclass(frozen=True)
class DeclaredRigidTransformV1:
    """A declared software coordinate transform, never physical calibration proof."""

    rotation_row_major: tuple[float, ...]
    translation_m: tuple[float, float, float]
    frame_binding_id: str

    def __post_init__(self) -> None:
        if len(self.rotation_row_major) != 9:
            raise ViewpointSteeringError("rotation:EXACTLY_9_VALUES_REQUIRED")
        rotation = tuple(_finite(v, "rotation") for v in self.rotation_row_major)
        translation = tuple(_finite(v, "translation_m") for v in self.translation_m)
        if len(translation) != 3:
            raise ViewpointSteeringError("translation_m:EXACTLY_3_VALUES_REQUIRED")
        if not isinstance(self.frame_binding_id, str) or not self.frame_binding_id.strip():
            raise ViewpointSteeringError("frame_binding_id:NONEMPTY_STRING_REQUIRED")
        if len(self.frame_binding_id) > 256:
            raise ViewpointSteeringError("frame_binding_id:TOO_LONG")

        rows = (rotation[0:3], rotation[3:6], rotation[6:9])
        for row in rows:
            norm = math.sqrt(sum(v * v for v in row))
            if abs(norm - 1.0) > 1e-9:
                raise ViewpointSteeringError("rotation:ROW_NOT_UNIT")
        for a, b in ((rows[0], rows[1]), (rows[0], rows[2]), (rows[1], rows[2])):
            if abs(sum(x * y for x, y in zip(a, b))) > 1e-9:
                raise ViewpointSteeringError("rotation:ROWS_NOT_ORTHOGONAL")
        det = (
            rotation[0] * (rotation[4] * rotation[8] - rotation[5] * rotation[7])
            - rotation[1] * (rotation[3] * rotation[8] - rotation[5] * rotation[6])
            + rotation[2] * (rotation[3] * rotation[7] - rotation[4] * rotation[6])
        )
        if abs(det - 1.0) > 1e-9:
            raise ViewpointSteeringError("rotation:PROPER_RIGID_TRANSFORM_REQUIRED")

        object.__setattr__(self, "rotation_row_major", rotation)
        object.__setattr__(self, "translation_m", translation)
        object.__setattr__(self, "frame_binding_id", " ".join(self.frame_binding_id.split()))

    @property
    def digest(self) -> str:
        return _sha(asdict(self))

    def transform_point(self, point: Sequence[float]) -> tuple[float, float, float]:
        if len(point) != 3:
            raise ViewpointSteeringError("point:EXACTLY_3_VALUES_REQUIRED")
        x, y, z = (_finite(v, "point") for v in point)
        r = self.rotation_row_major
        t = self.translation_m
        return (
            r[0] * x + r[1] * y + r[2] * z + t[0],
            r[3] * x + r[4] * y + r[5] * z + t[1],
            r[6] * x + r[7] * y + r[8] * z + t[2],
        )


@dataclass(frozen=True)
class SteeringQueryV1:
    selected_eye: str
    sample_x_m: float
    sample_y_m: float
    wavelength_m: float
    base_phase_radians: float = 0.0

    def __post_init__(self) -> None:
        eye = self.selected_eye.upper()
        if eye not in {"LEFT", "RIGHT"}:
            raise ViewpointSteeringError("selected_eye:LEFT_OR_RIGHT_REQUIRED")
        object.__setattr__(self, "selected_eye", eye)
        for name in ("sample_x_m", "sample_y_m", "base_phase_radians"):
            object.__setattr__(self, name, _finite(getattr(self, name), name))
        wavelength = _finite(self.wavelength_m, "wavelength_m")
        if wavelength <= 0.0:
            raise ViewpointSteeringError("wavelength_m:POSITIVE_REQUIRED")
        object.__setattr__(self, "wavelength_m", wavelength)


@dataclass(frozen=True)
class ViewpointPhaseSteeringReceiptV1:
    schema: str
    pr621_exact_head: str
    pr620_exact_head: str
    binocular_source: str
    metric_eye_origin_eligible: bool
    selected_eye: str
    frame_binding_id: str
    frame_binding_digest: str
    selected_eye_display_m: tuple[float, float, float]
    sample_x_m: float
    sample_y_m: float
    wavelength_m: float
    reference_phase_radians: float
    independent_phase_radians: float
    circular_phase_error_radians: float
    software_phase_conformance: bool
    declared_software_transform_only: bool
    physical_extrinsics_calibrated: bool
    gaze_direction_observed: bool
    physical_gaze_accuracy_proven: bool
    raw_sensor_persistence_authorized: bool
    physical_display_observed: bool
    holographic_parallax_perception_proven: bool
    vergence_accommodation_conflict_eliminated: bool
    speckle_suppression_proven: bool
    optical_safety_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    effect_authority: bool
    gate10_promoted: bool
    receipt_sha256: str = ""


def build_viewpoint_phase_steering_witness(
    *,
    eye_module: ModuleType,
    optics_module: ModuleType,
    binocular_calibration: object,
    transform: DeclaredRigidTransformV1,
    query: SteeringQueryV1,
    phase_tolerance_radians: float = 1e-9,
) -> ViewpointPhaseSteeringReceiptV1:
    tolerance = _finite(phase_tolerance_radians, "phase_tolerance_radians")
    if tolerance <= 0.0:
        raise ViewpointSteeringError("phase_tolerance_radians:POSITIVE_REQUIRED")

    measured_source = eye_module.IpdSource.MEASURED_USER
    if getattr(binocular_calibration, "source", None) is not measured_source:
        raise ViewpointSteeringError("binocular:MEASURED_USER_REQUIRED")
    if not getattr(binocular_calibration, "metric_eye_origin_eligible", False):
        raise ViewpointSteeringError("binocular:METRIC_EYE_ORIGIN_NOT_ELIGIBLE")

    left, right = binocular_calibration.eye_origins_about_midpoint()
    selected_local = left if query.selected_eye == "LEFT" else right
    selected_display = transform.transform_point(selected_local)
    if selected_display[2] <= 0.0:
        raise ViewpointSteeringError("selected_eye_display_z:POSITIVE_REQUIRED")

    case = optics_module.SteeringConformanceCase(
        base_phase_radians=query.base_phase_radians,
        sample_x_m=query.sample_x_m,
        sample_y_m=query.sample_y_m,
        eye_x_m=selected_display[0],
        eye_y_m=selected_display[1],
        eye_z_m=selected_display[2],
        wavelength_m=query.wavelength_m,
    )
    independent_phase = optics_module.independent_phase_steering(case)
    reference = optics_module.imported.phase_steering_sample(
        base_phase_radians=case.base_phase_radians,
        sample_x_m=case.sample_x_m,
        sample_y_m=case.sample_y_m,
        eye_x_m=case.eye_x_m,
        eye_y_m=case.eye_y_m,
        eye_z_m=case.eye_z_m,
        wavelength_m=case.wavelength_m,
    ).phase_radians
    phase_error = optics_module.circular_phase_error(reference, independent_phase)
    conformance = phase_error <= tolerance
    if not conformance:
        raise ViewpointSteeringError("phase_steering:PARENT_FORMULATIONS_DISAGREE")

    unsigned = ViewpointPhaseSteeringReceiptV1(
        schema=SCHEMA,
        pr621_exact_head=PR621_EXACT_HEAD,
        pr620_exact_head=PR620_EXACT_HEAD,
        binocular_source=binocular_calibration.source.value,
        metric_eye_origin_eligible=True,
        selected_eye=query.selected_eye,
        frame_binding_id=transform.frame_binding_id,
        frame_binding_digest=transform.digest,
        selected_eye_display_m=selected_display,
        sample_x_m=query.sample_x_m,
        sample_y_m=query.sample_y_m,
        wavelength_m=query.wavelength_m,
        reference_phase_radians=reference,
        independent_phase_radians=independent_phase,
        circular_phase_error_radians=phase_error,
        software_phase_conformance=True,
        declared_software_transform_only=True,
        physical_extrinsics_calibrated=False,
        gaze_direction_observed=False,
        physical_gaze_accuracy_proven=False,
        raw_sensor_persistence_authorized=False,
        physical_display_observed=False,
        holographic_parallax_perception_proven=False,
        vergence_accommodation_conflict_eliminated=False,
        speckle_suppression_proven=False,
        optical_safety_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        effect_authority=False,
        gate10_promoted=False,
    )
    raw = asdict(unsigned)
    raw.pop("receipt_sha256")
    return ViewpointPhaseSteeringReceiptV1(
        **raw,
        receipt_sha256=_sha(raw),
    )


def verify_receipt(receipt: ViewpointPhaseSteeringReceiptV1) -> bool:
    body = asdict(receipt)
    digest = body.pop("receipt_sha256")
    if digest != _sha(body):
        return False
    hard_false = (
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
    )
    return (
        receipt.schema == SCHEMA
        and receipt.pr621_exact_head == PR621_EXACT_HEAD
        and receipt.pr620_exact_head == PR620_EXACT_HEAD
        and receipt.metric_eye_origin_eligible is True
        and receipt.software_phase_conformance is True
        and receipt.declared_software_transform_only is True
        and all(getattr(receipt, key) is False for key in hard_false)
    )
