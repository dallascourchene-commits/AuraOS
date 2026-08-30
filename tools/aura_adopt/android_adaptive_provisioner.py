from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class HostKind(str, Enum):
    ANDROID = "ANDROID"
    NON_ANDROID = "NON_ANDROID"
    UNKNOWN = "UNKNOWN"


class EntrySurface(str, Enum):
    ZERO_INSTALL_WEB_PWA = "ZERO_INSTALL_WEB_PWA"
    NATIVE_ANDROID_APK = "NATIVE_ANDROID_APK"
    DEV_CLI_GITHUB = "DEV_CLI_GITHUB"
    NO_SUPPORTED_SURFACE = "NO_SUPPORTED_SURFACE"


class ProvisioningProfile(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    DETERMINISTIC_NATIVE = "DETERMINISTIC_NATIVE"
    HYBRID_REMOTE_ADMISSION_REQUIRED = "HYBRID_REMOTE_ADMISSION_REQUIRED"
    MICRO_LOCAL_MODEL_ELIGIBLE = "MICRO_LOCAL_MODEL_ELIGIBLE"
    FULL_LOCAL_MODEL_ELIGIBLE = "FULL_LOCAL_MODEL_ELIGIBLE"
    BLOCKED = "BLOCKED"


class PlanStatus(str, Enum):
    READY_BOUNDED = "READY_BOUNDED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    REBASE_REQUIRED = "REBASE_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class HostSubstrateWitnessV1:
    source_ref: str
    source_generation: str
    source_currentness_ref: str
    host_kind: HostKind
    android_api_level: Optional[int] = None
    free_storage_bytes: Optional[int] = None
    ram_bytes: Optional[int] = None
    saf_available: Optional[bool] = None
    webview_available: Optional[bool] = None
    network_available: Optional[bool] = None
    native_tts_available: Optional[bool] = None
    background_execution_available: Optional[bool] = None
    local_model_runtime_available: Optional[bool] = None

    def __post_init__(self) -> None:
        for name in ("source_ref", "source_generation", "source_currentness_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_{name.upper()}")
        if not isinstance(self.host_kind, HostKind):
            raise ValueError("INVALID_HOST_KIND")
        for name in ("android_api_level", "free_storage_bytes", "ram_bytes"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError(f"INVALID_{name.upper()}")
        for name in (
            "saf_available",
            "webview_available",
            "network_available",
            "native_tts_available",
            "background_execution_available",
            "local_model_runtime_available",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"INVALID_{name.upper()}")


@dataclass(frozen=True)
class CapabilityRequirementsV1:
    capability_ids: Tuple[str, ...]
    working_storage_bytes: int = 0
    working_ram_bytes: int = 0
    requires_offline: bool = False
    requires_background: bool = False
    requires_local_inference: bool = False
    remote_inference_acceptable: bool = False
    requires_native_tts: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.capability_ids, tuple) or not self.capability_ids:
            raise ValueError("CAPABILITY_IDS_REQUIRED")
        if any(not isinstance(v, str) or not v.strip() for v in self.capability_ids):
            raise ValueError("INVALID_CAPABILITY_ID")
        if len(self.capability_ids) != len(set(self.capability_ids)):
            raise ValueError("DUPLICATE_CAPABILITY_ID")
        for name in ("working_storage_bytes", "working_ram_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"INVALID_{name.upper()}")
        for name in (
            "requires_offline",
            "requires_background",
            "requires_local_inference",
            "remote_inference_acceptable",
            "requires_native_tts",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"INVALID_{name.upper()}")


@dataclass(frozen=True)
class ProvisioningPolicyV1:
    policy_ref: str
    policy_currentness_ref: str
    minimum_android_api_level: int
    native_shell_bytes: int
    storage_reserve_bytes: int
    micro_model_bytes: Optional[int] = None
    micro_model_min_ram_bytes: Optional[int] = None
    full_model_bytes: Optional[int] = None
    full_model_min_ram_bytes: Optional[int] = None

    def __post_init__(self) -> None:
        for name in ("policy_ref", "policy_currentness_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"INVALID_{name.upper()}")
        for name in (
            "minimum_android_api_level",
            "native_shell_bytes",
            "storage_reserve_bytes",
            "micro_model_bytes",
            "micro_model_min_ram_bytes",
            "full_model_bytes",
            "full_model_min_ram_bytes",
        ):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError(f"INVALID_{name.upper()}")


@dataclass(frozen=True)
class AdaptiveProvisioningPlanV1:
    selected_entry_surface: EntrySurface
    status: PlanStatus
    profile: ProvisioningProfile
    blockers: Tuple[str, ...]
    unknowns: Tuple[str, ...]
    required_actions: Tuple[str, ...]
    avoided_actions: Tuple[str, ...]
    estimated_download_bytes: Optional[int]
    estimated_peak_storage_bytes: Optional[int]
    install_authorized: bool = False
    install_performed: bool = False
    download_authorized: bool = False
    download_performed: bool = False
    permission_grant_authorized: bool = False
    permission_granted: bool = False
    credential_requested: bool = False
    provider_effect_authorized: bool = False
    provider_effect_performed: bool = False
    execution_proven: bool = False


def _sum_or_none(*values: Optional[int]) -> Optional[int]:
    if any(v is None for v in values):
        return None
    return sum(v for v in values if v is not None)


def compile_adaptive_provisioning_plan(
    witness: HostSubstrateWitnessV1,
    requirements: CapabilityRequirementsV1,
    policy: ProvisioningPolicyV1,
    *,
    selected_entry_surface: EntrySurface,
    expected_witness_currentness_ref: str,
    expected_policy_currentness_ref: str,
) -> AdaptiveProvisioningPlanV1:
    """Compile the minimum adequate Android provisioning plan without effects.

    Discovery is evidence, never permission. A returned READY_BOUNDED plan may
    name required future actions but never authorizes or performs them.
    """
    if not isinstance(witness, HostSubstrateWitnessV1):
        raise ValueError("INVALID_HOST_WITNESS")
    if not isinstance(requirements, CapabilityRequirementsV1):
        raise ValueError("INVALID_REQUIREMENTS")
    if not isinstance(policy, ProvisioningPolicyV1):
        raise ValueError("INVALID_POLICY")
    if not isinstance(selected_entry_surface, EntrySurface):
        raise ValueError("INVALID_ENTRY_SURFACE")

    if (
        witness.source_currentness_ref != expected_witness_currentness_ref
        or policy.policy_currentness_ref != expected_policy_currentness_ref
    ):
        return AdaptiveProvisioningPlanV1(
            selected_entry_surface,
            PlanStatus.REBASE_REQUIRED,
            ProvisioningProfile.BLOCKED,
            ("CURRENTNESS_MISMATCH",),
            (),
            (),
            (),
            None,
            None,
        )

    if selected_entry_surface is not EntrySurface.NATIVE_ANDROID_APK:
        return AdaptiveProvisioningPlanV1(
            selected_entry_surface,
            PlanStatus.NOT_APPLICABLE,
            ProvisioningProfile.NOT_APPLICABLE,
            (),
            (),
            (),
            ("APK_INSTALL", "MODEL_DOWNLOAD", "PROVIDER_KEY"),
            0,
            0,
        )

    blockers: list[str] = []
    unknowns: list[str] = []
    required: list[str] = ["APK_INSTALL"]
    avoided: list[str] = ["DEVELOPER_CLI"]

    if witness.host_kind is HostKind.UNKNOWN:
        unknowns.append("HOST_KIND_UNKNOWN")
    elif witness.host_kind is not HostKind.ANDROID:
        blockers.append("ANDROID_HOST_REQUIRED")

    if witness.android_api_level is None:
        unknowns.append("ANDROID_API_LEVEL_UNKNOWN")
    elif witness.android_api_level < policy.minimum_android_api_level:
        blockers.append("ANDROID_API_LEVEL_UNSUPPORTED")

    if witness.saf_available is None:
        unknowns.append("SAF_AVAILABILITY_UNKNOWN")
    elif witness.saf_available is False:
        blockers.append("SAF_REQUIRED")

    if requirements.requires_background:
        if witness.background_execution_available is None:
            unknowns.append("BACKGROUND_EXECUTION_UNKNOWN")
        elif witness.background_execution_available is False:
            blockers.append("BACKGROUND_EXECUTION_UNAVAILABLE")
        else:
            required.append("BACKGROUND_PERMISSION_REVIEW")
    else:
        avoided.append("BACKGROUND_PERMISSION")

    if requirements.requires_native_tts:
        if witness.native_tts_available is None:
            unknowns.append("NATIVE_TTS_UNKNOWN")
        elif witness.native_tts_available is False:
            blockers.append("NATIVE_TTS_UNAVAILABLE")

    base_peak = policy.native_shell_bytes + policy.storage_reserve_bytes + requirements.working_storage_bytes
    if witness.free_storage_bytes is None:
        unknowns.append("FREE_STORAGE_UNKNOWN")
    elif witness.free_storage_bytes < base_peak:
        blockers.append("INSUFFICIENT_STORAGE_FOR_NATIVE_SHELL")

    if witness.ram_bytes is None and requirements.working_ram_bytes > 0:
        unknowns.append("RAM_UNKNOWN")
    elif witness.ram_bytes is not None and witness.ram_bytes < requirements.working_ram_bytes:
        blockers.append("INSUFFICIENT_RAM_FOR_CAPABILITY")

    profile = ProvisioningProfile.DETERMINISTIC_NATIVE
    download_bytes: Optional[int] = policy.native_shell_bytes
    peak_storage: Optional[int] = base_peak

    if requirements.requires_local_inference:
        if witness.local_model_runtime_available is None:
            unknowns.append("LOCAL_MODEL_RUNTIME_UNKNOWN")
        elif witness.local_model_runtime_available is False:
            if requirements.remote_inference_acceptable:
                if requirements.requires_offline:
                    blockers.append("OFFLINE_LOCAL_INFERENCE_UNAVAILABLE")
                elif witness.network_available is False:
                    blockers.append("NETWORK_UNAVAILABLE_FOR_REMOTE_RESIDUAL")
                elif witness.network_available is None:
                    unknowns.append("NETWORK_AVAILABILITY_UNKNOWN")
                else:
                    profile = ProvisioningProfile.HYBRID_REMOTE_ADMISSION_REQUIRED
                    required.append("REMOTE_ROUTE_ADMISSION")
                    avoided.append("MODEL_DOWNLOAD")
            else:
                blockers.append("LOCAL_MODEL_RUNTIME_REQUIRED")
        else:
            # Choose the smallest adequate local model tier. Missing model-size
            # policy remains UNKNOWN rather than being treated as zero bytes.
            if policy.micro_model_bytes is None or policy.micro_model_min_ram_bytes is None:
                unknowns.append("MICRO_MODEL_POLICY_UNKNOWN")
            else:
                micro_peak = base_peak + policy.micro_model_bytes
                micro_ram_ok = witness.ram_bytes is not None and witness.ram_bytes >= policy.micro_model_min_ram_bytes
                micro_storage_ok = witness.free_storage_bytes is not None and witness.free_storage_bytes >= micro_peak
                if micro_ram_ok and micro_storage_ok:
                    profile = ProvisioningProfile.MICRO_LOCAL_MODEL_ELIGIBLE
                    required.append("MODEL_DOWNLOAD")
                    download_bytes = policy.native_shell_bytes + policy.micro_model_bytes
                    peak_storage = micro_peak
                else:
                    if witness.ram_bytes is None:
                        unknowns.append("RAM_UNKNOWN_FOR_MICRO_MODEL")
                    if witness.free_storage_bytes is None:
                        unknowns.append("FREE_STORAGE_UNKNOWN_FOR_MICRO_MODEL")
                    if policy.full_model_bytes is not None and policy.full_model_min_ram_bytes is not None:
                        full_peak = base_peak + policy.full_model_bytes
                        full_ram_ok = witness.ram_bytes is not None and witness.ram_bytes >= policy.full_model_min_ram_bytes
                        full_storage_ok = witness.free_storage_bytes is not None and witness.free_storage_bytes >= full_peak
                        if full_ram_ok and full_storage_ok:
                            profile = ProvisioningProfile.FULL_LOCAL_MODEL_ELIGIBLE
                            required.append("MODEL_DOWNLOAD")
                            download_bytes = policy.native_shell_bytes + policy.full_model_bytes
                            peak_storage = full_peak
                        elif requirements.remote_inference_acceptable and not requirements.requires_offline and witness.network_available is True:
                            profile = ProvisioningProfile.HYBRID_REMOTE_ADMISSION_REQUIRED
                            required.append("REMOTE_ROUTE_ADMISSION")
                            avoided.append("MODEL_DOWNLOAD")
                        elif not unknowns:
                            blockers.append("NO_ADEQUATE_LOCAL_MODEL_TIER")
                    elif not unknowns:
                        blockers.append("NO_ADEQUATE_LOCAL_MODEL_TIER")
    else:
        avoided.extend(("MODEL_DOWNLOAD", "PROVIDER_KEY"))

    if blockers:
        status = PlanStatus.BLOCKED
        profile = ProvisioningProfile.BLOCKED
    elif unknowns:
        status = PlanStatus.PARTIAL
    else:
        status = PlanStatus.READY_BOUNDED

    return AdaptiveProvisioningPlanV1(
        selected_entry_surface=selected_entry_surface,
        status=status,
        profile=profile,
        blockers=tuple(sorted(set(blockers))),
        unknowns=tuple(sorted(set(unknowns))),
        required_actions=tuple(dict.fromkeys(required)),
        avoided_actions=tuple(dict.fromkeys(avoided)),
        estimated_download_bytes=download_bytes,
        estimated_peak_storage_bytes=peak_storage,
    )
