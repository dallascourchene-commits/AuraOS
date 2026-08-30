"""Pure deterministic Aura global-adoption entry route compiler.

This module is intentionally a projection/decision layer. It does not probe hardware,
request permissions, collect credentials, install binaries, call providers, or deploy
anything. Upstream evidence owners (for example HostDiscoveryV1 and later
DeviceCapabilityEnvelopeV1) remain the device/source truth planes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any


SCHEMA = "AuraAdoptionBootstrapV1"
RECEIPT_SCHEMA = "AuraAdoptionBootstrapReceiptV1"
CLAIM_CEILING = "D0_ROUTE_DECISION_ONLY_NO_INSTALL_PERMISSION_PROVIDER_DEPLOYMENT_EFFECT"


class BootstrapError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


class UserMode(str, Enum):
    ORDINARY = "ORDINARY"
    DEVELOPER = "DEVELOPER"


class PlatformClass(str, Enum):
    ANDROID = "ANDROID"
    DESKTOP = "DESKTOP"
    WEB_ONLY = "WEB_ONLY"
    UNKNOWN = "UNKNOWN"


class LocalComputeClass(str, Enum):
    NONE = "NONE"
    CONSTRAINED = "CONSTRAINED"
    CAPABLE = "CAPABLE"
    UNKNOWN = "UNKNOWN"


class StorageClass(str, Enum):
    CRITICAL = "CRITICAL"
    LOW = "LOW"
    NORMAL = "NORMAL"
    UNKNOWN = "UNKNOWN"


class NetworkState(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class EntrySurface(str, Enum):
    ZERO_INSTALL_WEB_PWA = "ZERO_INSTALL_WEB_PWA"
    NATIVE_ANDROID_APK = "NATIVE_ANDROID_APK"
    DEV_CLI_GITHUB = "DEV_CLI_GITHUB"
    NO_SUPPORTED_SURFACE = "NO_SUPPORTED_SURFACE"


class ComputeProfile(str, Enum):
    FULL_LOCAL = "FULL_LOCAL"
    CONSTRAINED_LOCAL = "CONSTRAINED_LOCAL"
    HYBRID_LOCAL_REMOTE = "HYBRID_LOCAL_REMOTE"
    REMOTE_FREE_FIRST = "REMOTE_FREE_FIRST"
    OFFLINE_DEGRADED = "OFFLINE_DEGRADED"


def _nonempty_text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BootstrapError(code)
    return value.strip()


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BootstrapError("NONCANONICAL_BOOTSTRAP_STATE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical_json(value)).hexdigest()


@dataclass(frozen=True)
class SourceBindingV1:
    """Opaque binding to upstream normalized evidence.

    The compiler never treats this digest as authentication. It only prevents a route
    receipt from being silently transplanted onto a different caller-declared evidence
    snapshot. Verification/attestation of the upstream artifact remains outside this
    module.
    """

    source_generation: str
    currentness_ref: str
    host_evidence_ref: str
    host_evidence_digest: str
    capability_evidence_ref: str | None = None
    capability_evidence_digest: str | None = None

    def __post_init__(self) -> None:
        for value, code in (
            (self.source_generation, "SOURCE_GENERATION_REQUIRED"),
            (self.currentness_ref, "CURRENTNESS_REF_REQUIRED"),
            (self.host_evidence_ref, "HOST_EVIDENCE_REF_REQUIRED"),
            (self.host_evidence_digest, "HOST_EVIDENCE_DIGEST_REQUIRED"),
        ):
            _nonempty_text(value, code)
        optional = (
            (self.capability_evidence_ref, "CAPABILITY_EVIDENCE_REF_INVALID"),
            (self.capability_evidence_digest, "CAPABILITY_EVIDENCE_DIGEST_INVALID"),
        )
        for value, code in optional:
            if value is not None:
                _nonempty_text(value, code)
        if (self.capability_evidence_ref is None) != (self.capability_evidence_digest is None):
            raise BootstrapError("CAPABILITY_EVIDENCE_BINDING_INCOMPLETE")

    def logical(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        return _digest("AURA_ADOPTION_SOURCE_BINDING_V1", self.logical())


@dataclass(frozen=True)
class BootstrapProjectionV1:
    """Route-relevant facts projected from upstream evidence.

    Boolean fields are capability/availability observations only. They grant no
    permission, authority, network reachability guarantee, provider entitlement, or
    deployment right.
    """

    source: SourceBindingV1
    user_mode: UserMode
    platform_class: PlatformClass
    browser_available: bool
    native_install_available: bool
    cli_available: bool
    offline_required: bool
    background_required: bool
    local_compute_class: LocalComputeClass
    storage_class: StorageClass
    network_state: NetworkState
    free_remote_route_available: bool
    provider_credential_present: bool
    desired_first_capability: str
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise BootstrapError("BOOTSTRAP_SCHEMA_MISMATCH")
        for name in (
            "browser_available",
            "native_install_available",
            "cli_available",
            "offline_required",
            "background_required",
            "free_remote_route_available",
            "provider_credential_present",
        ):
            if type(getattr(self, name)) is not bool:
                raise BootstrapError("BOOL_REQUIRED", name)
        _nonempty_text(self.desired_first_capability, "FIRST_CAPABILITY_REQUIRED")

    def logical(self) -> dict[str, Any]:
        value = asdict(self)
        value["user_mode"] = self.user_mode.value
        value["platform_class"] = self.platform_class.value
        value["local_compute_class"] = self.local_compute_class.value
        value["storage_class"] = self.storage_class.value
        value["network_state"] = self.network_state.value
        return value

    @property
    def digest(self) -> str:
        return _digest("AURA_ADOPTION_BOOTSTRAP_PROJECTION_V1", self.logical())


@dataclass(frozen=True)
class FrictionReceiptV1:
    """Observable/decision-level friction accounting, not a behavioral guarantee."""

    install_actions_required: int
    permission_actions_required: int
    credential_actions_required: int
    model_download_actions_required: int
    unsupported_unknown_count: int

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BootstrapError("FRICTION_COUNT_INVALID", name)

    @property
    def total_required_actions(self) -> int:
        return (
            self.install_actions_required
            + self.permission_actions_required
            + self.credential_actions_required
            + self.model_download_actions_required
        )


@dataclass(frozen=True)
class BootstrapReceiptV1:
    schema: str
    projection_digest: str
    source_binding_digest: str
    surface: EntrySurface
    compute_profile: ComputeProfile
    first_use_capability: str
    required_actions: tuple[str, ...]
    avoided_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    friction: FrictionReceiptV1
    installation_performed: bool = False
    permission_granted: bool = False
    provider_call_made: bool = False
    credential_stored: bool = False
    public_deployment_performed: bool = False
    binary_distributed: bool = False
    claim_ceiling: str = CLAIM_CEILING

    def __post_init__(self) -> None:
        if self.schema != RECEIPT_SCHEMA:
            raise BootstrapError("RECEIPT_SCHEMA_MISMATCH")
        for value, code in (
            (self.projection_digest, "PROJECTION_DIGEST_REQUIRED"),
            (self.source_binding_digest, "SOURCE_BINDING_DIGEST_REQUIRED"),
            (self.first_use_capability, "FIRST_CAPABILITY_REQUIRED"),
            (self.claim_ceiling, "CLAIM_CEILING_REQUIRED"),
        ):
            _nonempty_text(value, code)
        for name in (
            "installation_performed",
            "permission_granted",
            "provider_call_made",
            "credential_stored",
            "public_deployment_performed",
            "binary_distributed",
        ):
            if getattr(self, name) is not False:
                raise BootstrapError("EFFECT_FLAG_MUST_REMAIN_FALSE", name)

    def logical(self) -> dict[str, Any]:
        value = asdict(self)
        value["surface"] = self.surface.value
        value["compute_profile"] = self.compute_profile.value
        return value

    @property
    def digest(self) -> str:
        return _digest("AURA_ADOPTION_BOOTSTRAP_RECEIPT_V1", self.logical())


def _select_surface(p: BootstrapProjectionV1) -> tuple[EntrySurface, list[str], list[str], list[str]]:
    required: list[str] = []
    avoided: list[str] = []
    blockers: list[str] = []

    if p.user_mode is UserMode.DEVELOPER and p.cli_available:
        surface = EntrySurface.DEV_CLI_GITHUB
        required.append("OPEN_GITHUB_OR_AURA_CLI")
        avoided.append("INSTALL_ANDROID_APK")
        return surface, required, avoided, blockers

    ordinary_web_fit = p.browser_available and not p.offline_required and not p.background_required
    if ordinary_web_fit:
        surface = EntrySurface.ZERO_INSTALL_WEB_PWA
        required.append("OPEN_AURA_WEB_ENTRY")
        avoided.extend(("INSTALL_ANDROID_APK", "INSTALL_PYTHON_OR_GIT"))
        return surface, required, avoided, blockers

    native_fit = (
        p.platform_class is PlatformClass.ANDROID
        and p.native_install_available
        and (p.offline_required or p.background_required or not p.browser_available)
    )
    if native_fit:
        surface = EntrySurface.NATIVE_ANDROID_APK
        required.append("INSTALL_AURA_ANDROID_APP")
        avoided.append("INSTALL_DEVELOPER_CLI")
        if p.background_required:
            required.append("REQUEST_BACKGROUND_CAPABILITY_IF_PLATFORM_REQUIRES")
        return surface, required, avoided, blockers

    if p.browser_available:
        surface = EntrySurface.ZERO_INSTALL_WEB_PWA
        required.append("OPEN_AURA_WEB_ENTRY")
        avoided.extend(("INSTALL_ANDROID_APK", "INSTALL_PYTHON_OR_GIT"))
        blockers.append("WEB_SURFACE_MAY_NOT_SATISFY_OFFLINE_OR_BACKGROUND_REQUIREMENT")
        return surface, required, avoided, blockers

    if p.cli_available:
        surface = EntrySurface.DEV_CLI_GITHUB
        required.append("OPEN_GITHUB_OR_AURA_CLI")
        avoided.append("INSTALL_ANDROID_APK")
        return surface, required, avoided, blockers

    if p.platform_class is PlatformClass.ANDROID and p.native_install_available:
        surface = EntrySurface.NATIVE_ANDROID_APK
        required.append("INSTALL_AURA_ANDROID_APP")
        avoided.append("INSTALL_DEVELOPER_CLI")
        return surface, required, avoided, blockers

    blockers.append("NO_SUPPORTED_ENTRY_SURFACE_PROVEN")
    return EntrySurface.NO_SUPPORTED_SURFACE, required, avoided, blockers


def _select_compute(
    p: BootstrapProjectionV1,
) -> tuple[ComputeProfile, list[str], list[str], list[str], int]:
    required: list[str] = []
    avoided: list[str] = []
    blockers: list[str] = []
    unknowns = 0

    if p.offline_required or p.network_state is NetworkState.OFFLINE:
        avoided.extend(("ENTER_PROVIDER_KEY", "CALL_REMOTE_PROVIDER"))
        if p.local_compute_class is LocalComputeClass.CAPABLE and p.storage_class is StorageClass.NORMAL:
            required.append("USE_EXISTING_OR_RESOLVE_LOCAL_RUNTIME")
            return ComputeProfile.FULL_LOCAL, required, avoided, blockers, unknowns
        if p.local_compute_class in (LocalComputeClass.CAPABLE, LocalComputeClass.CONSTRAINED):
            if p.storage_class is StorageClass.UNKNOWN:
                unknowns += 1
                blockers.append("LOCAL_STORAGE_CAPACITY_UNKNOWN")
            required.append("USE_CONSTRAINED_LOCAL_RUNTIME")
            return ComputeProfile.CONSTRAINED_LOCAL, required, avoided, blockers, unknowns
        if p.local_compute_class is LocalComputeClass.UNKNOWN:
            unknowns += 1
            blockers.append("LOCAL_COMPUTE_CAPABILITY_UNKNOWN")
        else:
            blockers.append("LOCAL_COMPUTE_UNAVAILABLE_FOR_OFFLINE_REQUIREMENT")
        return ComputeProfile.OFFLINE_DEGRADED, required, avoided, blockers, unknowns

    if p.network_state is NetworkState.UNKNOWN:
        unknowns += 1

    if p.local_compute_class is LocalComputeClass.CAPABLE and p.storage_class is StorageClass.NORMAL:
        required.append("USE_EXISTING_OR_RESOLVE_LOCAL_RUNTIME")
        avoided.extend(("ENTER_PROVIDER_KEY", "CALL_PAID_PROVIDER"))
        return ComputeProfile.FULL_LOCAL, required, avoided, blockers, unknowns

    if (
        p.network_state is NetworkState.ONLINE
        and p.free_remote_route_available
        and p.storage_class in (StorageClass.CRITICAL, StorageClass.LOW)
    ):
        required.append("USE_CURRENT_FREE_REMOTE_ROUTE")
        avoided.extend(("DOWNLOAD_LOCAL_MODEL", "ENTER_PROVIDER_KEY", "CALL_PAID_PROVIDER"))
        return ComputeProfile.REMOTE_FREE_FIRST, required, avoided, blockers, unknowns

    if p.local_compute_class is LocalComputeClass.CONSTRAINED:
        if p.network_state is NetworkState.ONLINE and p.provider_credential_present:
            required.append("USE_EXISTING_PROVIDER_CREDENTIAL_WITHOUT_RESTORING_IT")
            avoided.append("DOWNLOAD_LARGE_LOCAL_MODEL")
            return ComputeProfile.HYBRID_LOCAL_REMOTE, required, avoided, blockers, unknowns
        required.append("USE_CONSTRAINED_LOCAL_RUNTIME")
        avoided.extend(("ENTER_PROVIDER_KEY", "DOWNLOAD_LARGE_LOCAL_MODEL"))
        return ComputeProfile.CONSTRAINED_LOCAL, required, avoided, blockers, unknowns

    if p.network_state is NetworkState.ONLINE and p.free_remote_route_available:
        required.append("USE_CURRENT_FREE_REMOTE_ROUTE")
        avoided.extend(("DOWNLOAD_LOCAL_MODEL", "ENTER_PROVIDER_KEY", "CALL_PAID_PROVIDER"))
        return ComputeProfile.REMOTE_FREE_FIRST, required, avoided, blockers, unknowns

    if p.network_state is NetworkState.ONLINE and p.provider_credential_present:
        required.append("USE_EXISTING_PROVIDER_CREDENTIAL_WITHOUT_RESTORING_IT")
        avoided.append("DOWNLOAD_LOCAL_MODEL")
        return ComputeProfile.HYBRID_LOCAL_REMOTE, required, avoided, blockers, unknowns

    if p.local_compute_class is LocalComputeClass.UNKNOWN:
        unknowns += 1
        blockers.append("LOCAL_COMPUTE_CAPABILITY_UNKNOWN")
    if p.storage_class is StorageClass.UNKNOWN:
        unknowns += 1
        blockers.append("LOCAL_STORAGE_CAPACITY_UNKNOWN")
    if p.network_state is NetworkState.UNKNOWN:
        blockers.append("NETWORK_STATE_UNKNOWN")
    elif p.network_state is NetworkState.ONLINE:
        blockers.append("NO_REMOTE_ROUTE_PROVEN")
    return ComputeProfile.OFFLINE_DEGRADED, required, avoided, blockers, unknowns


def compile_entry_route(p: BootstrapProjectionV1) -> BootstrapReceiptV1:
    """Compile a lowest-friction lawful route without performing any effect."""

    surface, s_required, s_avoided, s_blockers = _select_surface(p)
    compute, c_required, c_avoided, c_blockers, unknowns = _select_compute(p)

    required = tuple(dict.fromkeys(s_required + c_required))
    avoided = tuple(dict.fromkeys(s_avoided + c_avoided))
    blockers = tuple(sorted(set(s_blockers + c_blockers)))

    install_count = sum(
        action in {"INSTALL_AURA_ANDROID_APP", "INSTALL_DEVELOPER_CLI"}
        for action in required
    )
    permission_count = sum(action.startswith("REQUEST_") for action in required)
    credential_count = sum("ENTER_PROVIDER_KEY" in action for action in required)
    model_download_count = sum("DOWNLOAD_" in action for action in required)

    friction = FrictionReceiptV1(
        install_actions_required=install_count,
        permission_actions_required=permission_count,
        credential_actions_required=credential_count,
        model_download_actions_required=model_download_count,
        unsupported_unknown_count=unknowns,
    )

    return BootstrapReceiptV1(
        schema=RECEIPT_SCHEMA,
        projection_digest=p.digest,
        source_binding_digest=p.source.digest,
        surface=surface,
        compute_profile=compute,
        first_use_capability=p.desired_first_capability.strip(),
        required_actions=required,
        avoided_actions=avoided,
        blockers=blockers,
        friction=friction,
    )


__all__ = [
    "BootstrapError",
    "BootstrapProjectionV1",
    "BootstrapReceiptV1",
    "ComputeProfile",
    "EntrySurface",
    "FrictionReceiptV1",
    "LocalComputeClass",
    "NetworkState",
    "PlatformClass",
    "SourceBindingV1",
    "StorageClass",
    "UserMode",
    "compile_entry_route",
]
