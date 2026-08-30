"""AURA-ADOPT-001: deterministic zero-friction entry-route compiler.

D0/reference implementation. It chooses the lowest-friction lawful entry route
from already-observed host/task evidence. It does not discover hardware, request
permissions, fetch remote code, collect credentials, or authorize execution.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
from typing import FrozenSet, Mapping


SCHEMA = "AuraAdoptionBootstrapV1"
RECEIPT_SCHEMA = "AdoptionFrictionReceiptV1"


class AdoptionRoute(str, Enum):
    ZERO_INSTALL_WEB_PWA = "ZERO_INSTALL_WEB_PWA"
    NATIVE_ANDROID_APK = "NATIVE_ANDROID_APK"
    DEV_CLI_GITHUB = "DEV_CLI_GITHUB"
    FULL_LOCAL = "FULL_LOCAL"
    CONSTRAINED_LOCAL = "CONSTRAINED_LOCAL"
    HYBRID_LOCAL_REMOTE = "HYBRID_LOCAL_REMOTE"
    REMOTE_FREE_FIRST = "REMOTE_FREE_FIRST"
    OFFLINE_DEGRADED = "OFFLINE_DEGRADED"


class CompileError(ValueError):
    pass


@dataclass(frozen=True)
class HostWitness:
    host_class: str
    browser_available: bool
    browser_wasm: bool
    network_online: bool
    free_storage_mb: int | None
    ram_mb: int | None
    android: bool = False
    native_shell_installed: bool = False
    dev_cli_available: bool = False
    local_runtime_available: bool = False
    local_model_available: bool = False
    secure_store_available: bool | None = None
    granted_permissions: FrozenSet[str] = frozenset()
    available_credentials: FrozenSet[str] = frozenset()

    def __post_init__(self) -> None:
        for field_name in ("free_storage_mb", "ram_mb"):
            value = getattr(self, field_name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise CompileError(f"{field_name} must be a nonnegative integer or None")


@dataclass(frozen=True)
class FirstTask:
    task_id: str
    domain: str
    browser_supported: bool = True
    offline_supported: bool = True
    native_required: bool = False
    local_model_required: bool = False
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
    route: AdoptionRoute
    task_id: str
    required_actions: tuple[str, ...]
    avoided_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    friction_components: Mapping[str, int | None]
    authority_required: bool
    effect_authorized: bool
    execution_proven: bool
    decision_digest: str

    def to_dict(self) -> dict:
        out = asdict(self)
        out["route"] = self.route.value
        return out


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _storage_sufficient(host: HostWitness, task: FirstTask) -> bool | None:
    if host.free_storage_mb is None:
        return None
    return host.free_storage_mb >= task.minimum_storage_mb


def _missing_permissions(host: HostWitness, task: FirstTask) -> tuple[str, ...]:
    return tuple(sorted(task.required_permissions - host.granted_permissions))


def compile_entry_route(
    host: HostWitness,
    task: FirstTask,
    preference: EntryPreference = EntryPreference(),
) -> RouteDecision:
    """Choose the minimum-action lawful route.

    Ordering is adoption-specific, not a general execution scheduler: reuse/browser
    first when sufficient; native/install only when the task requires it; developer
    CLI only when explicitly requested; model/key requests are deferred until a
    selected route actually requires them.
    """
    missing_permissions = _missing_permissions(host, task)
    storage_ok = _storage_sufficient(host, task)
    blockers: list[str] = []
    required: list[str] = []

    if preference.developer_mode and host.dev_cli_available:
        route = AdoptionRoute.DEV_CLI_GITHUB
    elif (
        host.browser_available
        and host.browser_wasm
        and task.browser_supported
        and not task.native_required
        and not task.local_model_required
        and (host.network_online or task.offline_supported)
    ):
        route = AdoptionRoute.ZERO_INSTALL_WEB_PWA
    elif host.android and task.native_required:
        route = AdoptionRoute.NATIVE_ANDROID_APK
        if not host.native_shell_installed:
            if preference.allow_install:
                required.append("INSTALL_NATIVE_ANDROID_SHELL")
            else:
                blockers.append("NATIVE_REQUIRED_INSTALL_NOT_ALLOWED")
        if missing_permissions:
            required.extend(f"GRANT_PERMISSION:{p}" for p in missing_permissions)
    elif host.local_runtime_available and (not task.local_model_required or host.local_model_available):
        route = AdoptionRoute.FULL_LOCAL
        if storage_ok is False:
            route = AdoptionRoute.CONSTRAINED_LOCAL
            blockers.append("LOCAL_STORAGE_BELOW_TASK_MINIMUM")
    elif host.network_online and preference.allow_remote and task.remote_model_allowed:
        route = AdoptionRoute.REMOTE_FREE_FIRST
        if not host.available_credentials:
            required.append("SELECT_OR_ADD_REMOTE_ROUTE_IF_REQUIRED")
    elif task.offline_supported:
        route = AdoptionRoute.OFFLINE_DEGRADED
        if task.local_model_required and not host.local_model_available:
            blockers.append("LOCAL_MODEL_UNAVAILABLE_OFFLINE")
        if task.native_required and not host.native_shell_installed:
            blockers.append("NATIVE_CAPABILITY_UNAVAILABLE_OFFLINE")
    else:
        route = AdoptionRoute.OFFLINE_DEGRADED
        blockers.append("NO_LAWFUL_ROUTE_FOR_TASK")

    if route != AdoptionRoute.NATIVE_ANDROID_APK and missing_permissions and task.native_required:
        blockers.append("REQUIRED_PERMISSION_UNAVAILABLE_ON_SELECTED_ROUTE")

    avoided: list[str] = []
    if route == AdoptionRoute.ZERO_INSTALL_WEB_PWA:
        avoided += ["MANDATORY_INSTALL", "GIT", "PYTHON", "CLI", "MANDATORY_API_KEY"]
    elif route in {AdoptionRoute.FULL_LOCAL, AdoptionRoute.CONSTRAINED_LOCAL}:
        avoided += ["MANDATORY_REMOTE_PROVIDER", "MANDATORY_API_KEY"]
    elif route == AdoptionRoute.DEV_CLI_GITHUB:
        avoided += ["BINARY_TRUST_REQUIREMENT"]
    if not required:
        avoided.append("UPFRONT_CONFIGURATION")

    friction = {
        "discovery_steps": None,
        "install_actions": sum(1 for a in required if a.startswith("INSTALL_")),
        "credential_actions": sum(1 for a in required if "REMOTE_ROUTE" in a or "KEY" in a),
        "permission_actions": sum(1 for a in required if a.startswith("GRANT_PERMISSION:")),
        "manual_configuration_actions": len(required),
        "downloaded_bytes": None,
        "time_to_first_accepted_value_ms": None,
        "monetary_cost_microunits": None,
    }

    payload = {
        "schema": SCHEMA,
        "route": route.value,
        "task_id": task.task_id,
        "required_actions": required,
        "avoided_actions": sorted(set(avoided)),
        "blockers": blockers,
        "friction_components": friction,
        "authority_required": bool(missing_permissions or required),
        "effect_authorized": False,
        "execution_proven": False,
    }
    return RouteDecision(
        schema=SCHEMA,
        route=route,
        task_id=task.task_id,
        required_actions=tuple(required),
        avoided_actions=tuple(sorted(set(avoided))),
        blockers=tuple(blockers),
        friction_components=friction,
        authority_required=bool(missing_permissions or required),
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
    private_keys = {"content", "prompt", "api_key", "credential", "secret", "token"}
    if any(str(k).casefold() in private_keys for k in observed):
        raise CompileError("private content/credentials are forbidden in friction receipts")
    return {
        "schema": RECEIPT_SCHEMA,
        "route_id": route_id,
        "build_head": build_head,
        "decision_digest": decision.decision_digest,
        "route": decision.route.value,
        "task_id": decision.task_id,
        "required_actions": list(decision.required_actions),
        "avoided_actions": list(decision.avoided_actions),
        "blockers": list(decision.blockers),
        "friction_components": dict(decision.friction_components),
        "observed": observed,
        "privacy_ceiling": "NO_PRIVATE_CONTENT_OR_SECRET_VALUES",
        "effect_authorized": False,
        "execution_proven": False,
    }
