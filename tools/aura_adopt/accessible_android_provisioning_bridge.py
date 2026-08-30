"""ZF-09 -> ZF-02 accessibility-preserving Android provisioning membrane.

D0 coordination only. This bridge consumes the canonical AccessibleOnboardingPlanV1
from ZF-09 plus a read-only projection of sibling ZF-02 AdaptiveProvisioningPlanV1.
It does not probe a device, install an APK, download a model, grant permissions,
request credentials, call a provider, infer access needs, or execute a route.

The key law is progressive disclosure under host feasibility: a feasible Android
substrate may describe future actions, but MODEL_DOWNLOAD / REMOTE_ROUTE_ADMISSION /
BACKGROUND_PERMISSION_REVIEW remain deferred from the first-value path. Technical
capacity never widens accessibility or effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping

try:
    from .accessible_onboarding import AccessibleOnboardingPlanV1
except ImportError:
    from accessible_onboarding import AccessibleOnboardingPlanV1

SCHEMA = "AccessibleAndroidProvisioningBridgeV1"


class AccessibleProvisioningError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (tuple, list)):
        return [_normalize(v) for v in value]
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            _normalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AccessibleProvisioningError("NONCANONICAL_PLAN") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    row = _normalize(value)
    if not isinstance(row, Mapping):
        raise AccessibleProvisioningError(code)
    return row


def _sequence(value: Any, code: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise AccessibleProvisioningError(code)
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AccessibleProvisioningError(code)
        out.append(item.strip())
    return tuple(out)


def _nonnegative_int_or_none(value: Any, code: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AccessibleProvisioningError(code)
    return value


ADVANCED_ACTION_TO_SURFACE = {
    "MODEL_DOWNLOAD": "MODEL_DOWNLOADS",
    "REMOTE_ROUTE_ADMISSION": "PROVIDER_SETTINGS",
    "BACKGROUND_PERMISSION_REVIEW": "BACKGROUND_AUTOMATION",
}

PROVISIONING_AUTHORITY_FIELDS = (
    "install_authorized",
    "install_performed",
    "download_authorized",
    "download_performed",
    "permission_grant_authorized",
    "permission_granted",
    "credential_requested",
    "provider_effect_authorized",
    "provider_effect_performed",
    "execution_proven",
)

ONBOARDING_AUTHORITY_FIELDS = (
    "telemetry_authorized",
    "telemetry_performed",
    "install_authorized",
    "credential_request_authorized",
    "provider_effect_authorized",
    "execution_proven",
)


@dataclass(frozen=True)
class AccessibleAndroidProvisioningDecisionV1:
    status: str
    onboarding_plan_digest: str
    provisioning_plan_digest: str
    selected_entry_surface: str
    provisioning_profile: str
    first_value_steps: tuple[str, ...]
    deferred_actions: tuple[str, ...]
    ordinary_future_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    unknowns: tuple[str, ...]
    assisted_fallback_reasons: tuple[str, ...]
    estimated_download_bytes: int | None
    estimated_peak_storage_bytes: int | None
    user_explicit_acceptance_proven: bool
    save_observed: bool
    reopen_observed: bool
    schema: str = SCHEMA
    telemetry_authorized: bool = False
    install_authorized: bool = False
    download_authorized: bool = False
    permission_grant_authorized: bool = False
    credential_request_authorized: bool = False
    provider_effect_authorized: bool = False
    execution_proven: bool = False
    decision_digest: str = ""

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise AccessibleProvisioningError("DECISION_SCHEMA_MISMATCH")
        expected = self.compute_digest()
        supplied = str(self.decision_digest or "").strip()
        if supplied and supplied != expected:
            raise AccessibleProvisioningError("DECISION_DIGEST_MISMATCH")
        object.__setattr__(self, "decision_digest", expected)

    def logical_payload(self) -> dict[str, Any]:
        row = asdict(self)
        row.pop("decision_digest", None)
        return row

    def compute_digest(self) -> str:
        return _digest(self.logical_payload())


def compile_accessible_android_provisioning_decision(
    *,
    onboarding_plan: AccessibleOnboardingPlanV1,
    provisioning_plan: Mapping[str, Any] | Any,
) -> AccessibleAndroidProvisioningDecisionV1:
    if not isinstance(onboarding_plan, AccessibleOnboardingPlanV1):
        raise AccessibleProvisioningError("ACCESSIBLE_ONBOARDING_PLAN_REQUIRED")
    onboarding = _mapping(onboarding_plan, "ACCESSIBLE_ONBOARDING_PLAN_MAPPING_REQUIRED")
    provisioning = _mapping(provisioning_plan, "ADAPTIVE_PROVISIONING_PLAN_MAPPING_REQUIRED")

    for field in ONBOARDING_AUTHORITY_FIELDS:
        if onboarding.get(field) is not False:
            raise AccessibleProvisioningError("ONBOARDING_AUTHORITY_WIDENING", field)
    for field in PROVISIONING_AUTHORITY_FIELDS:
        if provisioning.get(field) is not False:
            raise AccessibleProvisioningError("PROVISIONING_AUTHORITY_WIDENING", field)

    selected_surface = _enum_value(provisioning.get("selected_entry_surface"))
    if selected_surface != "NATIVE_ANDROID_APK":
        raise AccessibleProvisioningError("ANDROID_NATIVE_SURFACE_REQUIRED", str(selected_surface))

    onboarding_status = _enum_value(onboarding.get("status"))
    provisioning_status = _enum_value(provisioning.get("status"))
    profile = _enum_value(provisioning.get("profile"))
    if onboarding_status not in {
        "READY_BOUNDED", "PARTIAL", "ASSISTED_FALLBACK_REQUIRED", "REBASE_REQUIRED"
    }:
        raise AccessibleProvisioningError("ONBOARDING_STATUS_INVALID", str(onboarding_status))
    if provisioning_status not in {
        "READY_BOUNDED", "PARTIAL", "BLOCKED", "REBASE_REQUIRED", "NOT_APPLICABLE"
    }:
        raise AccessibleProvisioningError("PROVISIONING_STATUS_INVALID", str(provisioning_status))

    steps = _sequence(onboarding.get("steps"), "ONBOARDING_STEPS_INVALID")
    hidden = set(_sequence(onboarding.get("advanced_surfaces_hidden"), "ADVANCED_SURFACES_HIDDEN_INVALID"))
    onboarding_unknowns = _sequence(onboarding.get("unknowns"), "ONBOARDING_UNKNOWNS_INVALID")
    fallback = _sequence(
        onboarding.get("assisted_fallback_reasons"), "ASSISTED_FALLBACK_REASONS_INVALID"
    )
    provisioning_blockers = _sequence(provisioning.get("blockers"), "PROVISIONING_BLOCKERS_INVALID")
    provisioning_unknowns = _sequence(provisioning.get("unknowns"), "PROVISIONING_UNKNOWNS_INVALID")
    required_actions = _sequence(provisioning.get("required_actions"), "PROVISIONING_REQUIRED_ACTIONS_INVALID")

    deferred: list[str] = []
    ordinary_future: list[str] = []
    for action in required_actions:
        hidden_surface = ADVANCED_ACTION_TO_SURFACE.get(action)
        if hidden_surface is None:
            ordinary_future.append(action)
            continue
        if hidden_surface not in hidden:
            raise AccessibleProvisioningError(
                "PROGRESSIVE_DISCLOSURE_CONTRACT_MISMATCH",
                f"{action}:{hidden_surface}",
            )
        deferred.append(action)

    download_bytes = _nonnegative_int_or_none(
        provisioning.get("estimated_download_bytes"), "ESTIMATED_DOWNLOAD_BYTES_INVALID"
    )
    peak_storage = _nonnegative_int_or_none(
        provisioning.get("estimated_peak_storage_bytes"), "ESTIMATED_PEAK_STORAGE_BYTES_INVALID"
    )
    if "MODEL_DOWNLOAD" in required_actions and (download_bytes is None or download_bytes <= 0):
        raise AccessibleProvisioningError("MODEL_DOWNLOAD_BYTES_REQUIRED")

    # Status composition is deliberately conservative. Accessibility fallback and
    # currentness outrank technical host readiness; unknowns remain partial.
    blockers = tuple(sorted(set(provisioning_blockers)))
    unknowns = tuple(sorted(set((*onboarding_unknowns, *provisioning_unknowns))))
    if onboarding_status == "REBASE_REQUIRED" or provisioning_status == "REBASE_REQUIRED":
        status = "REBASE_REQUIRED"
    elif onboarding_status == "ASSISTED_FALLBACK_REQUIRED":
        status = "ASSISTED_FALLBACK_REQUIRED"
    elif provisioning_status == "BLOCKED":
        status = "BLOCKED_RESOURCE"
    elif onboarding_status == "PARTIAL" or provisioning_status == "PARTIAL" or unknowns:
        status = "PARTIAL"
    elif provisioning_status == "NOT_APPLICABLE":
        status = "NOT_APPLICABLE"
    else:
        status = "READY_FOR_USER_REVIEW"

    return AccessibleAndroidProvisioningDecisionV1(
        status=status,
        onboarding_plan_digest=_digest(onboarding),
        provisioning_plan_digest=_digest(provisioning),
        selected_entry_surface="NATIVE_ANDROID_APK",
        provisioning_profile=str(profile),
        first_value_steps=steps,
        deferred_actions=tuple(dict.fromkeys(deferred)),
        ordinary_future_actions=tuple(dict.fromkeys(ordinary_future)),
        blockers=blockers,
        unknowns=unknowns,
        assisted_fallback_reasons=tuple(sorted(set(fallback))),
        estimated_download_bytes=download_bytes,
        estimated_peak_storage_bytes=peak_storage,
        user_explicit_acceptance_proven=bool(onboarding.get("user_explicit_acceptance_proven")),
        save_observed=bool(onboarding.get("save_observed")),
        reopen_observed=bool(onboarding.get("reopen_observed")),
    )
