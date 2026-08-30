from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class PreferenceSource(str, Enum):
    USER_SELECTED = "USER_SELECTED"
    PLATFORM_EXPOSED = "PLATFORM_EXPOSED"


class PlanStatus(str, Enum):
    READY_BOUNDED = "READY_BOUNDED"
    PARTIAL = "PARTIAL"
    ASSISTED_FALLBACK_REQUIRED = "ASSISTED_FALLBACK_REQUIRED"
    REBASE_REQUIRED = "REBASE_REQUIRED"


class AcceptanceMode(str, Enum):
    NONE = "NONE"
    SYNTHETIC_TECHNICAL = "SYNTHETIC_TECHNICAL"
    USER_EXPLICIT = "USER_EXPLICIT"


class SaveEvidenceMode(str, Enum):
    NONE = "NONE"
    SIMULATED = "SIMULATED"
    DOWNLOAD_INITIATED = "DOWNLOAD_INITIATED"
    SAVE_OBSERVED = "SAVE_OBSERVED"
    REOPEN_OBSERVED = "REOPEN_OBSERVED"


@dataclass(frozen=True)
class AccessNeedsV1:
    source_ref: str
    source_currentness_ref: str
    preference_source: PreferenceSource
    keyboard_required: bool = False
    screen_reader_required: bool = False
    high_contrast_required: bool = False
    reduced_motion_required: bool = False
    captions_required: bool = False
    voice_input_requested: bool = False
    touch_input_requested: bool = True
    simplified_guidance_requested: bool = True

    def __post_init__(self) -> None:
        for name in ("source_ref", "source_currentness_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_{name.upper()}")
        if not isinstance(self.preference_source, PreferenceSource):
            raise ValueError("INVALID_PREFERENCE_SOURCE")
        for name in (
            "keyboard_required",
            "screen_reader_required",
            "high_contrast_required",
            "reduced_motion_required",
            "captions_required",
            "voice_input_requested",
            "touch_input_requested",
            "simplified_guidance_requested",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"INVALID_{name.upper()}")


@dataclass(frozen=True)
class OnboardingSurfaceCapabilitiesV1:
    source_ref: str
    source_currentness_ref: str
    keyboard_operable: Optional[bool]
    screen_reader_semantics: Optional[bool]
    high_contrast_mode: Optional[bool]
    reduced_motion_mode: Optional[bool]
    captions_available: Optional[bool]
    voice_input_available: Optional[bool]
    touch_operable: Optional[bool]
    local_file_picker_available: Optional[bool]
    canvas_render_available: Optional[bool]
    local_download_available: Optional[bool]

    def __post_init__(self) -> None:
        for name in ("source_ref", "source_currentness_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_{name.upper()}")
        for name in (
            "keyboard_operable",
            "screen_reader_semantics",
            "high_contrast_mode",
            "reduced_motion_mode",
            "captions_available",
            "voice_input_available",
            "touch_operable",
            "local_file_picker_available",
            "canvas_render_available",
            "local_download_available",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"INVALID_{name.upper()}")


@dataclass(frozen=True)
class FirstValueEvidenceV1:
    acceptance_mode: AcceptanceMode = AcceptanceMode.NONE
    acceptance_ref: str = ""
    save_evidence_mode: SaveEvidenceMode = SaveEvidenceMode.NONE
    save_evidence_ref: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.acceptance_mode, AcceptanceMode):
            raise ValueError("INVALID_ACCEPTANCE_MODE")
        if not isinstance(self.save_evidence_mode, SaveEvidenceMode):
            raise ValueError("INVALID_SAVE_EVIDENCE_MODE")
        if not isinstance(self.acceptance_ref, str) or not isinstance(self.save_evidence_ref, str):
            raise ValueError("INVALID_EVIDENCE_REF")
        if self.acceptance_mode is AcceptanceMode.USER_EXPLICIT and not self.acceptance_ref.strip():
            raise ValueError("USER_ACCEPTANCE_REF_REQUIRED")
        if self.save_evidence_mode in (SaveEvidenceMode.SAVE_OBSERVED, SaveEvidenceMode.REOPEN_OBSERVED) and not self.save_evidence_ref.strip():
            raise ValueError("SAVE_EVIDENCE_REF_REQUIRED")


@dataclass(frozen=True)
class AccessibleOnboardingPlanV1:
    status: PlanStatus
    steps: Tuple[str, ...]
    blockers: Tuple[str, ...]
    unknowns: Tuple[str, ...]
    assisted_fallback_reasons: Tuple[str, ...]
    advanced_surfaces_hidden: Tuple[str, ...]
    user_explicit_acceptance_proven: bool
    save_observed: bool
    reopen_observed: bool
    telemetry_authorized: bool = False
    telemetry_performed: bool = False
    install_authorized: bool = False
    credential_request_authorized: bool = False
    provider_effect_authorized: bool = False
    execution_proven: bool = False


def compile_accessible_onboarding_plan(
    needs: AccessNeedsV1,
    capabilities: OnboardingSurfaceCapabilitiesV1,
    evidence: FirstValueEvidenceV1,
    *,
    expected_needs_currentness_ref: str,
    expected_capabilities_currentness_ref: str,
) -> AccessibleOnboardingPlanV1:
    if not isinstance(needs, AccessNeedsV1):
        raise ValueError("INVALID_ACCESS_NEEDS")
    if not isinstance(capabilities, OnboardingSurfaceCapabilitiesV1):
        raise ValueError("INVALID_SURFACE_CAPABILITIES")
    if not isinstance(evidence, FirstValueEvidenceV1):
        raise ValueError("INVALID_FIRST_VALUE_EVIDENCE")

    if (
        needs.source_currentness_ref != expected_needs_currentness_ref
        or capabilities.source_currentness_ref != expected_capabilities_currentness_ref
    ):
        return AccessibleOnboardingPlanV1(
            PlanStatus.REBASE_REQUIRED,
            (),
            ("CURRENTNESS_MISMATCH",),
            (),
            (),
            (),
            False,
            False,
            False,
        )

    unknowns: list[str] = []
    fallback: list[str] = []

    checks = (
        (needs.keyboard_required, "KEYBOARD", capabilities.keyboard_operable),
        (needs.screen_reader_required, "SCREEN_READER", capabilities.screen_reader_semantics),
        (needs.high_contrast_required, "HIGH_CONTRAST", capabilities.high_contrast_mode),
        (needs.reduced_motion_required, "REDUCED_MOTION", capabilities.reduced_motion_mode),
        (needs.captions_required, "CAPTIONS", capabilities.captions_available),
        (needs.voice_input_requested, "VOICE_INPUT", capabilities.voice_input_available),
        (needs.touch_input_requested, "TOUCH", capabilities.touch_operable),
        (True, "LOCAL_FILE_PICKER", capabilities.local_file_picker_available),
        (True, "CANVAS_RENDER", capabilities.canvas_render_available),
        (True, "LOCAL_DOWNLOAD", capabilities.local_download_available),
    )
    for required, label, available in checks:
        if not required:
            continue
        if available is None:
            unknowns.append(f"{label}_CAPABILITY_UNKNOWN")
        elif available is False:
            fallback.append(f"{label}_UNAVAILABLE")

    steps: list[str] = ["OPEN"]
    if needs.simplified_guidance_requested:
        steps.append("GUIDED_PICK_INPUT")
    else:
        steps.append("PICK_INPUT")
    steps.extend(("APPLY_RECIPE", "PREVIEW", "USER_EXPLICIT_ACCEPT", "SAVE_LOCAL"))

    if fallback:
        status = PlanStatus.ASSISTED_FALLBACK_REQUIRED
        steps.append("OFFER_ASSISTED_PATH")
    elif unknowns:
        status = PlanStatus.PARTIAL
    else:
        status = PlanStatus.READY_BOUNDED

    explicit_acceptance = evidence.acceptance_mode is AcceptanceMode.USER_EXPLICIT
    save_observed = evidence.save_evidence_mode in (
        SaveEvidenceMode.SAVE_OBSERVED,
        SaveEvidenceMode.REOPEN_OBSERVED,
    )
    reopen_observed = evidence.save_evidence_mode is SaveEvidenceMode.REOPEN_OBSERVED

    # Technical/synthetic output and simulated/download-initiation evidence are
    # useful diagnostics, but they never satisfy human value or save/reopen proof.
    return AccessibleOnboardingPlanV1(
        status=status,
        steps=tuple(steps),
        blockers=(),
        unknowns=tuple(sorted(set(unknowns))),
        assisted_fallback_reasons=tuple(sorted(set(fallback))),
        advanced_surfaces_hidden=(
            "API_KEYS",
            "MODEL_DOWNLOADS",
            "PROVIDER_SETTINGS",
            "DEVELOPER_CLI",
            "CLOUD_ACCOUNT_LINK",
            "BACKGROUND_AUTOMATION",
        ),
        user_explicit_acceptance_proven=explicit_acceptance,
        save_observed=save_observed,
        reopen_observed=reopen_observed,
    )
