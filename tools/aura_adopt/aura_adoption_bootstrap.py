"""AURA-ADOPT-001: deterministic zero-friction entry-route compiler.

D0/reference implementation. It consumes normalized, source-bound evidence and
chooses two orthogonal outputs:
  1) the lowest-friction entry surface, and
  2) the lowest-friction lawful compute profile.

It does not discover hardware, request permissions, fetch remote code, collect
credentials, install anything, authorize effects, or claim execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import FrozenSet, Mapping


SCHEMA = "AuraAdoptionBootstrapV1"
RECEIPT_SCHEMA = "AdoptionFrictionReceiptV1"


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


class CompileError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceBinding:
    """Immutable pointer to normalized upstream evidence; not the evidence owner."""

    source_ref: str
    source_digest: str
    source_generation: str

    def __post_init__(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in asdict(self).values()):
            raise CompileError("evidence binding fields must be nonempty strings")


@dataclass(frozen=True)
class HostWitness:
    host_class: str
    browser_available: bool | None
    browser_wasm: bool | None
    network_online: bool | None
    free_storage_mb: int | None
    ram_mb: int | None
    android: bool | None = None
    native_shell_installed: bool | None = None
    native_install_available: bool | None = None
    dev_cli_available: bool | None = None
    local_runtime_available: bool | None = None
    local_model_available: bool | None = None
    local_compute_class: str = "UNKNOWN"  # FULL | CONSTRAINED | NONE | UNKNOWN
    free_remote_route_available: bool | None = None
    secure_store_available: bool | None = None
    granted_permissions: FrozenSet[str] = frozenset()
    available_credentials: FrozenSet[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.host_class, str) or not self.host_class.strip():
            raise CompileError("host_class is required")
        for field_name in ("free_storage_mb", "ram_mb"):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise CompileError(f"{field_name} must be a nonnegative integer or None")
        if self.local_compute_class not in {"FULL", "CONSTRAINED", "NONE", "UNKNOWN"}:
            raise CompileError("local_compute_class invalid")


@dataclass(frozen=True)
class FirstTask:
    task_id: str
    domain: str
    browser_supported: bool | None = True
    offline_supported: bool | None = True
    native_required: bool = False
    background_required: bool = False
    model_inference_required: bool = False
    remote_model_allowed: bool = True
    required_permissions: FrozenSet[str] = frozenset()
    minimum_storage_mb: int = 0

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.domain.strip():
            raise CompileError("task_id and domain are required")
        if self.minimum_storage_mb < 0:
            raise CompileError("minimum_storage_mb must be nonnegative")


@dataclass(frozen=True)
class EntryPreference:
    developer_mode: bool = False
    prefer_offline: bool = False
    allow_install: bool = True
    allow_remote: bool = True


@dataclass(frozen=True)
class RouteDecision:
    schema: str
    entry_surface: EntrySurface
    compute_profile: ComputeProfile
    task_id: str
    domain: str
    evidence: EvidenceBinding
    required_actions: tuple[str, ...]
    avoided_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    friction_components: Mapping[str, int | None]
    authority_required: bool
    installation_performed: bool
    permission_granted: bool
    provider_call_made: bool
    credential_stored: bool
    public_deployment: bool
    binary_distributed: bool
    effect_authorized: bool
    execution_proven: bool
    decision_digest: str

    def to_dict(self) -> dict:
        out = asdict(self)
        out["entry_surface"] = self.entry_surface.value
        out["compute_profile"] = self.compute_profile.value
        return out


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _storage_sufficient(host: HostWitness, task: FirstTask) -> bool | None:
    if host.free_storage_mb is None:
        return None
    return host.free_storage_mb >= task.minimum_storage_mb


def _missing_permissions(host: HostWitness, task: FirstTask) -> tuple[str, ...]:
    return tuple(sorted(task.required_permissions - host.granted_permissions))


def _choose_surface(
    host: HostWitness,
    task: FirstTask,
    preference: EntryPreference,
    required: list[str],
    blockers: list[str],
) -> EntrySurface:
    if preference.developer_mode and host.dev_cli_available is True:
        return EntrySurface.DEV_CLI_GITHUB

    web_known_ready = (
        host.browser_available is True
        and host.browser_wasm is True
        and task.browser_supported is True
        and not task.native_required
        and not task.background_required
    )
    if web_known_ready:
        return EntrySurface.ZERO_INSTALL_WEB_PWA

    if host.android is True and (task.native_required or task.background_required):
        if host.native_shell_installed is True:
            return EntrySurface.NATIVE_ANDROID_APK
        if host.native_install_available is True and preference.allow_install:
            required.append("INSTALL_NATIVE_ANDROID_SHELL")
            return EntrySurface.NATIVE_ANDROID_APK
        blockers.append("NATIVE_REQUIRED_BUT_UNAVAILABLE_OR_INSTALL_DISALLOWED")
        return EntrySurface.NO_SUPPORTED_SURFACE

    if host.dev_cli_available is True:
        required.append("USE_DEVELOPER_CLI_SURFACE")
        return EntrySurface.DEV_CLI_GITHUB

    blockers.append("NO_SUPPORTED_OR_PROVEN_ENTRY_SURFACE")
    return EntrySurface.NO_SUPPORTED_SURFACE


def _choose_compute(
    host: HostWitness,
    task: FirstTask,
    preference: EntryPreference,
    required: list[str],
    blockers: list[str],
) -> ComputeProfile:
    storage_ok = _storage_sufficient(host, task)

    if not task.model_inference_required:
        if host.local_compute_class == "FULL":
            return ComputeProfile.FULL_LOCAL
        if host.local_compute_class == "CONSTRAINED" or storage_ok is False:
            return ComputeProfile.CONSTRAINED_LOCAL
        return ComputeProfile.CONSTRAINED_LOCAL

    if (
        host.local_runtime_available is True
        and host.local_model_available is True
        and host.local_compute_class == "FULL"
        and storage_ok is not False
    ):
        return ComputeProfile.FULL_LOCAL

    if (
        host.local_runtime_available is True
        and host.local_model_available is True
        and host.local_compute_class == "CONSTRAINED"
        and storage_ok is not False
    ):
        return ComputeProfile.CONSTRAINED_LOCAL

    if preference.prefer_offline:
        blockers.append("MODEL_TASK_LOCAL_CAPABILITY_INSUFFICIENT_FOR_OFFLINE_PREFERENCE")
        return ComputeProfile.OFFLINE_DEGRADED

    if (
        host.network_online is True
        and preference.allow_remote
        and task.remote_model_allowed
        and host.free_remote_route_available is True
    ):
        return ComputeProfile.REMOTE_FREE_FIRST

    if (
        host.network_online is True
        and preference.allow_remote
        and task.remote_model_allowed
        and host.available_credentials
    ):
        return ComputeProfile.HYBRID_LOCAL_REMOTE

    if (
        host.network_online is True
        and preference.allow_remote
        and task.remote_model_allowed
        and host.free_remote_route_available is not True
        and not host.available_credentials
    ):
        required.append("SELECT_OR_ADD_REMOTE_ROUTE_IF_REQUIRED")
        blockers.append("NO_CURRENT_REMOTE_ROUTE_EVIDENCE")
        return ComputeProfile.OFFLINE_DEGRADED

    blockers.append("MODEL_INFERENCE_CAPABILITY_UNAVAILABLE")
    return ComputeProfile.OFFLINE_DEGRADED


def compile_entry_route(
    host: HostWitness,
    task: FirstTask,
    evidence: EvidenceBinding,
    preference: EntryPreference = EntryPreference(),
) -> RouteDecision:
    """Compile minimum-action surface x compute plan from normalized evidence."""
    required: list[str] = []
    blockers: list[str] = []

    surface = _choose_surface(host, task, preference, required, blockers)
    compute = _choose_compute(host, task, preference, required, blockers)

    missing_permissions = _missing_permissions(host, task)
    if surface == EntrySurface.NATIVE_ANDROID_APK and missing_permissions:
        required.extend(f"GRANT_PERMISSION:{p}" for p in missing_permissions)
    elif missing_permissions and (task.native_required or task.background_required):
        blockers.append("REQUIRED_PERMISSION_UNAVAILABLE_ON_SELECTED_SURFACE")

    avoided: list[str] = []
    if surface == EntrySurface.ZERO_INSTALL_WEB_PWA:
        avoided += ["MANDATORY_INSTALL", "GIT", "PYTHON", "CLI"]
    elif surface == EntrySurface.DEV_CLI_GITHUB:
        avoided.append("BINARY_TRUST_REQUIREMENT")
    if compute in {ComputeProfile.FULL_LOCAL, ComputeProfile.CONSTRAINED_LOCAL}:
        avoided += ["MANDATORY_REMOTE_PROVIDER", "MANDATORY_API_KEY"]
    if compute == ComputeProfile.REMOTE_FREE_FIRST:
        avoided += ["MANDATORY_LOCAL_MODEL_DOWNLOAD", "MANDATORY_PAID_PROVIDER"]
    if not required:
        avoided.append("UPFRONT_CONFIGURATION")

    friction = {
        "discovery_steps": None,
        "install_actions": sum(1 for a in required if a.startswith("INSTALL_")),
        "credential_actions": sum(
            1 for a in required if "REMOTE_ROUTE" in a or "KEY" in a
        ),
        "permission_actions": sum(
            1 for a in required if a.startswith("GRANT_PERMISSION:")
        ),
        "manual_configuration_actions": len(required),
        "downloaded_bytes": None,
        "peak_retained_bytes": None,
        "time_to_first_accepted_value_ms": None,
        "monetary_cost_microunits": None,
    }

    payload = {
        "schema": SCHEMA,
        "entry_surface": surface.value,
        "compute_profile": compute.value,
        "task_id": task.task_id,
        "domain": task.domain,
        "evidence": asdict(evidence),
        "required_actions": required,
        "avoided_actions": sorted(set(avoided)),
        "blockers": blockers,
        "friction_components": friction,
        "authority_required": bool(missing_permissions or required),
        "installation_performed": False,
        "permission_granted": False,
        "provider_call_made": False,
        "credential_stored": False,
        "public_deployment": False,
        "binary_distributed": False,
        "effect_authorized": False,
        "execution_proven": False,
    }
    return RouteDecision(
        schema=SCHEMA,
        entry_surface=surface,
        compute_profile=compute,
        task_id=task.task_id,
        domain=task.domain,
        evidence=evidence,
        required_actions=tuple(required),
        avoided_actions=tuple(sorted(set(avoided))),
        blockers=tuple(blockers),
        friction_components=friction,
        authority_required=bool(missing_permissions or required),
        installation_performed=False,
        permission_granted=False,
        provider_call_made=False,
        credential_stored=False,
        public_deployment=False,
        binary_distributed=False,
        effect_authorized=False,
        execution_proven=False,
        decision_digest=_digest(payload),
    )


def friction_receipt(
    decision: RouteDecision,
    *,
    route_id: str,
    build_head: str,
    observed: Mapping[str, int | str | bool | None] | None = None,
) -> dict:
    """Build a privacy-minimal friction receipt; caller supplies observations only."""
    if not route_id.strip() or not build_head.strip():
        raise CompileError("route_id and build_head are required")
    observed = dict(observed or {})
    private_keys = {
        "content",
        "prompt",
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "secret",
        "token",
    }
    if any(str(k).casefold() in private_keys for k in observed):
        raise CompileError("private content/credentials are forbidden in friction receipts")
    return {
        "schema": RECEIPT_SCHEMA,
        "route_id": route_id,
        "build_head": build_head,
        "decision_digest": decision.decision_digest,
        "entry_surface": decision.entry_surface.value,
        "compute_profile": decision.compute_profile.value,
        "task_id": decision.task_id,
        "domain": decision.domain,
        "evidence": asdict(decision.evidence),
        "required_actions": list(decision.required_actions),
        "avoided_actions": list(decision.avoided_actions),
        "blockers": list(decision.blockers),
        "friction_components": dict(decision.friction_components),
        "observed": observed,
        "privacy_ceiling": "NO_PRIVATE_CONTENT_OR_SECRET_VALUES",
        "installation_performed": False,
        "permission_granted": False,
        "provider_call_made": False,
        "credential_stored": False,
        "public_deployment": False,
        "binary_distributed": False,
        "effect_authorized": False,
        "execution_proven": False,
    }
