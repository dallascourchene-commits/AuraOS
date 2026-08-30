"""AURA-ADOPT-001 ZF-08A: cross-device Aura Drive bootstrap planner."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "CrossDeviceAuraDriveBootstrapV1"
PLAN_SCHEMA = "AuraDriveLocationPlanV1"
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,191}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
CURRENTNESS = frozenset({"CURRENT", "STALE", "UNKNOWN"})
CAPABILITY = frozenset({"AVAILABLE", "UNAVAILABLE", "UNKNOWN"})
INTENTS = frozenset({"DEFAULT_LOCAL_FIRST", "LOCAL_ONLY", "PORTABLE_FILE", "CLOUD_BACKED", "HYBRID"})
ACCOUNT_LINK = frozenset({"NOT_LINKED", "LINKED", "UNKNOWN"})
FORBIDDEN_KEYS = frozenset({
    "api_key", "apikey", "credential", "credentials", "secret", "token",
    "access_token", "refresh_token", "password", "private_key", "endpoint",
    "provider_url", "provider_endpoint", "oauth_token", "authorization_code",
    "email", "phone", "device_id", "account_id", "session_id", "ip_address",
})


class BootstrapError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _ident(name: str, value: Any) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise BootstrapError("INVALID_IDENTIFIER", name)
    if value.startswith(("http://", "https://")):
        raise BootstrapError("REMOTE_URL_FORBIDDEN", name)
    return value


def _sha(name: str, value: Any) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise BootstrapError("INVALID_SHA256", name)
    return value


def _safe(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise BootstrapError("NONSTRING_KEY_FORBIDDEN", path)
            if key.casefold() in FORBIDDEN_KEYS:
                raise BootstrapError("FORBIDDEN_BOOTSTRAP_FIELD", f"{path}.{key}")
            _safe(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _safe(child, f"{path}[{index}]")
    elif value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and (
            value != value or value in (float("inf"), float("-inf"))
        ):
            raise BootstrapError("NONFINITE_NUMBER_FORBIDDEN", path)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            raise BootstrapError("REMOTE_URL_FORBIDDEN", path)
    else:
        raise BootstrapError("UNSUPPORTED_VALUE", path)


@dataclass(frozen=True)
class SourceBinding:
    ref: str
    digest: str
    source_generation: str
    currentness: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _ident("ref", self.ref)
        _sha("digest", self.digest)
        _ident("source_generation", self.source_generation)
        if self.currentness not in CURRENTNESS:
            raise BootstrapError("INVALID_CURRENTNESS", self.currentness)


@dataclass(frozen=True)
class BindingEvidence:
    ref: str
    digest: str
    source_generation: str
    currentness: str

    def __post_init__(self) -> None:
        _ident("binding.ref", self.ref)
        _sha("binding.digest", self.digest)
        _ident("binding.source_generation", self.source_generation)
        if self.currentness not in CURRENTNESS:
            raise BootstrapError("INVALID_CURRENTNESS", self.currentness)


@dataclass(frozen=True)
class StorageCapabilities:
    source: SourceBinding
    local_persistence: str
    portable_file: str
    cloud_connector: str
    network: str

    def __post_init__(self) -> None:
        for name in ("local_persistence", "portable_file", "cloud_connector", "network"):
            value = getattr(self, name)
            if value not in CAPABILITY:
                raise BootstrapError("INVALID_CAPABILITY_STATE", f"{name}:{value}")


@dataclass(frozen=True)
class StorageIntent:
    mode: str = "DEFAULT_LOCAL_FIRST"
    explicitly_selected: bool = False

    def __post_init__(self) -> None:
        if self.mode not in INTENTS:
            raise BootstrapError("INVALID_STORAGE_INTENT", self.mode)
        if self.mode != "DEFAULT_LOCAL_FIRST" and not self.explicitly_selected:
            raise BootstrapError("EXPLICIT_STORAGE_SELECTION_REQUIRED", self.mode)


@dataclass(frozen=True)
class CloudAdmissionEvidence:
    connector_ref: str
    source: SourceBinding
    account_link_state: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _ident("connector_ref", self.connector_ref)
        if self.account_link_state not in ACCOUNT_LINK:
            raise BootstrapError("INVALID_ACCOUNT_LINK_STATE", self.account_link_state)


@dataclass(frozen=True)
class BootstrapRequest:
    request_id: str
    source: SourceBinding
    capabilities: StorageCapabilities
    intent: StorageIntent = StorageIntent()
    cloud: CloudAdmissionEvidence | None = None
    policy: Mapping[str, Any] | None = None
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise BootstrapError("SCHEMA_MISMATCH")
        _ident("request_id", self.request_id)
        object.__setattr__(self, "policy", dict(self.policy or {}))
        _safe(self.policy, "$.policy")


def _binding_blockers(
    name: str, claimed: SourceBinding, observed: BindingEvidence | None
) -> list[str]:
    if observed is None:
        return [f"{name}_BINDING_EVIDENCE_REQUIRED"]
    blockers: list[str] = []
    if observed.ref != claimed.ref:
        blockers.append(f"{name}_REF_MISMATCH")
    if observed.digest != claimed.digest:
        blockers.append(f"{name}_DIGEST_MISMATCH")
    if observed.source_generation != claimed.source_generation:
        blockers.append(f"{name}_GENERATION_MISMATCH")
    if observed.currentness != "CURRENT":
        blockers.append(f"{name}_CURRENTNESS_{observed.currentness}")
    if claimed.currentness in {"STALE", "UNKNOWN"}:
        blockers.append(f"{name}_CLAIM_CURRENTNESS_{claimed.currentness}")
    return blockers


def compile_bootstrap_plan(
    request: BootstrapRequest,
    *,
    current_bindings: Mapping[str, BindingEvidence],
) -> dict[str, Any]:
    if not isinstance(current_bindings, Mapping):
        raise BootstrapError("CURRENT_BINDINGS_REQUIRED")
    blockers: list[str] = []
    warnings: list[str] = []
    required_actions: list[str] = []

    blockers.extend(
        _binding_blockers(
            "REQUEST_SOURCE", request.source, current_bindings.get(request.source.ref)
        )
    )
    blockers.extend(
        _binding_blockers(
            "CAPABILITY_SOURCE",
            request.capabilities.source,
            current_bindings.get(request.capabilities.source.ref),
        )
    )

    mode = request.intent.mode
    local = request.capabilities.local_persistence
    portable = request.capabilities.portable_file
    cloud_cap = request.capabilities.cloud_connector
    network = request.capabilities.network
    primary = "UNRESOLVED"
    secondary = "NONE"
    cloud_requested = mode in {"CLOUD_BACKED", "HYBRID"}

    if mode == "DEFAULT_LOCAL_FIRST":
        if local == "AVAILABLE":
            primary = "LOCAL_PERSISTENT"
            if portable == "AVAILABLE":
                secondary = "PORTABLE_EXPORT_REOPEN"
        elif local == "UNAVAILABLE" and portable == "AVAILABLE":
            primary = "PORTABLE_FILE_ONLY"
            warnings.append("LOCAL_PERSISTENCE_UNAVAILABLE")
        elif local == "UNKNOWN":
            blockers.append("LOCAL_PERSISTENCE_UNKNOWN")
        else:
            blockers.append("NO_LOCAL_OR_PORTABLE_STORAGE_PATH")
    elif mode == "LOCAL_ONLY":
        if local == "AVAILABLE":
            primary = "LOCAL_PERSISTENT"
        elif local == "UNKNOWN":
            blockers.append("LOCAL_PERSISTENCE_UNKNOWN")
        else:
            blockers.append("LOCAL_PERSISTENCE_UNAVAILABLE")
        if portable == "AVAILABLE":
            secondary = "PORTABLE_EXPORT_REOPEN"
    elif mode == "PORTABLE_FILE":
        if portable == "AVAILABLE":
            primary = "PORTABLE_FILE_ONLY"
        elif portable == "UNKNOWN":
            blockers.append("PORTABLE_FILE_CAPABILITY_UNKNOWN")
        else:
            blockers.append("PORTABLE_FILE_CAPABILITY_UNAVAILABLE")
    elif cloud_requested:
        if request.cloud is None:
            blockers.append("CLOUD_ADMISSION_EVIDENCE_REQUIRED")
        else:
            blockers.extend(
                _binding_blockers(
                    "CLOUD_SOURCE",
                    request.cloud.source,
                    current_bindings.get(request.cloud.source.ref),
                )
            )
            if request.cloud.connector_ref != request.cloud.source.ref:
                blockers.append("CLOUD_CONNECTOR_REF_MISMATCH")
        if cloud_cap == "UNKNOWN":
            blockers.append("CLOUD_CONNECTOR_CAPABILITY_UNKNOWN")
        elif cloud_cap == "UNAVAILABLE":
            blockers.append("CLOUD_CONNECTOR_CAPABILITY_UNAVAILABLE")
        if network == "UNKNOWN":
            blockers.append("NETWORK_CAPABILITY_UNKNOWN")
        elif network == "UNAVAILABLE":
            blockers.append("NETWORK_CAPABILITY_UNAVAILABLE")
        if mode == "HYBRID":
            if local == "AVAILABLE":
                primary = "LOCAL_PERSISTENT"
                secondary = "CLOUD_SELECTED_PENDING_AUTHORITY"
            elif local == "UNKNOWN":
                blockers.append("LOCAL_PERSISTENCE_UNKNOWN")
            else:
                blockers.append("HYBRID_REQUIRES_LOCAL_PERSISTENCE")
        else:
            primary = "CLOUD_SELECTED_PENDING_AUTHORITY"
            if portable == "AVAILABLE":
                secondary = "PORTABLE_EXPORT_REOPEN"
        if request.cloud is not None:
            if request.cloud.account_link_state == "NOT_LINKED":
                required_actions.append("USER_LINK_CLOUD_ACCOUNT")
            elif request.cloud.account_link_state == "UNKNOWN":
                blockers.append("CLOUD_ACCOUNT_LINK_STATE_UNKNOWN")
            else:
                required_actions.append("USER_CONFIRM_CLOUD_STORAGE_SCOPE")

    if blockers:
        status = "STORAGE_EVIDENCE_OR_ASSISTANCE_REQUIRED"
    elif cloud_requested:
        status = "READY_FOR_STORAGE_AUTHORITY_GATE"
    else:
        status = "READY_FOR_LOCAL_USER_ACTION"

    payload = {
        "schema": PLAN_SCHEMA,
        "request_id": request.request_id,
        "request_source_digest": request.source.digest,
        "capability_source_digest": request.capabilities.source.digest,
        "intent_mode": mode,
        "intent_explicit": request.intent.explicitly_selected,
        "primary_location": primary,
        "secondary_location": secondary,
        "portable_export_reopen_available": portable == "AVAILABLE",
        "cloud_selected": cloud_requested,
        "cloud_controls_visible": cloud_requested,
        "account_link_prompt_visible": (
            cloud_requested
            and request.cloud is not None
            and request.cloud.account_link_state == "NOT_LINKED"
        ),
        "advanced_storage_controls_visible": cloud_requested,
        "required_user_actions": required_actions,
        "warnings": warnings,
        "blockers": blockers,
        "status": status,
        "local_write_authorized": False,
        "local_read_authorized": False,
        "portable_export_authorized": False,
        "portable_reopen_proven": False,
        "cloud_read_authorized": False,
        "cloud_write_authorized": False,
        "cloud_sync_authorized": False,
        "account_link_authorized": False,
        "network_fetch_authorized": False,
        "effect_authorized": False,
        "execution_proven": False,
    }
    payload["plan_digest"] = _digest(payload)
    return payload
