from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

ROUTE_ADMISSION_SCHEMA = "AuraProviderRouteAdmissionV1"
DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-v4-flash"
PRO_MODEL = "deepseek-v4-pro"
RETIRED_MODELS = frozenset({"deepseek-chat", "deepseek-reasoner"})


class RouteAdmissionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RouteAdmissionError(f"{name.upper()}_REQUIRED")
    return value.strip()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def validate_route_admission(
    raw: Mapping[str, Any] | None,
    *,
    command_digest: str,
    executor_id: str,
    effect_class: str,
    expected_provider: str,
    expected_model: str,
) -> dict[str, str]:
    provider = _text("expected_provider", expected_provider).casefold()
    model = _text("expected_model", expected_model)
    if model.casefold() in RETIRED_MODELS:
        raise RouteAdmissionError("EXPECTED_MODEL_RETIRED")
    if not isinstance(raw, Mapping):
        raise RouteAdmissionError("ROUTE_ADMISSION_REQUIRED")

    required = {
        "schema",
        "command_digest",
        "executor_id",
        "effect_class",
        "currentness",
        "provider",
        "model",
        "route_class",
        "route_generation",
        "escalation_decision",
        "escalation_ref",
        "policy_ref",
        "authority_admission_ref",
        "provider_cost_admission_ref",
    }
    if set(raw) != required:
        raise RouteAdmissionError("ROUTE_ADMISSION_SHAPE_INVALID")
    out = {key: _text(key, raw.get(key)) for key in required}
    if out["schema"] != ROUTE_ADMISSION_SCHEMA:
        raise RouteAdmissionError("ROUTE_ADMISSION_SCHEMA_MISMATCH")
    if out["command_digest"] != command_digest:
        raise RouteAdmissionError("ROUTE_ADMISSION_COMMAND_MISMATCH")
    if out["executor_id"] != executor_id or out["effect_class"] != effect_class:
        raise RouteAdmissionError("ROUTE_ADMISSION_EFFECT_BINDING_MISMATCH")
    if out["currentness"] != "CURRENT":
        raise RouteAdmissionError("ROUTE_ADMISSION_NOT_CURRENT")
    if out["provider"].casefold() != provider:
        raise RouteAdmissionError("ROUTE_PROVIDER_MISMATCH")
    if out["model"].casefold() != model.casefold():
        raise RouteAdmissionError("ROUTE_MODEL_MISMATCH")
    if out["model"].casefold() in RETIRED_MODELS:
        raise RouteAdmissionError("ROUTE_MODEL_RETIRED")

    if out["model"].casefold() == PRO_MODEL:
        if out["route_class"].casefold() != "pro":
            raise RouteAdmissionError("PRO_ROUTE_CLASS_REQUIRED")
        if out["escalation_decision"] != "ALLOW":
            raise RouteAdmissionError("PRO_ESCALATION_REQUIRED")
        if out["escalation_ref"].casefold() in {"none", "not_required", "n/a"}:
            raise RouteAdmissionError("PRO_ESCALATION_REF_REQUIRED")
    else:
        if out["model"].casefold() != DEFAULT_MODEL:
            raise RouteAdmissionError("ORDINARY_ROUTE_MUST_USE_FLASH")
        if out["route_class"].casefold() not in {"standard", "flash"}:
            raise RouteAdmissionError("STANDARD_ROUTE_CLASS_REQUIRED")
        if out["escalation_decision"] != "NOT_REQUIRED":
            raise RouteAdmissionError("UNEXPECTED_ESCALATION_DECISION")
        if out["escalation_ref"].casefold() != "none":
            raise RouteAdmissionError("UNEXPECTED_ESCALATION_REF")
    return out


def validate_effect_route_binding(
    route: Mapping[str, str], admission: Mapping[str, Any]
) -> None:
    if not isinstance(admission, Mapping):
        raise RouteAdmissionError("EFFECT_ADMISSION_INVALID")
    for key in (
        "command_digest",
        "policy_ref",
        "authority_admission_ref",
        "provider_cost_admission_ref",
    ):
        if str(admission.get(key) or "") != route[key]:
            raise RouteAdmissionError("ROUTE_EFFECT_ADMISSION_BINDING_MISMATCH")


def build_exact_executor(provider: str, model: str):
    from aura_llm_egress import ExternalLLM

    return ExternalLLM(
        provider=provider,
        model=model,
        task="drive_command_bridge",
        aspect="awj033_pre_effect_exact_route",
        allow_provider_fallback=False,
    )


def attest_executor(executor: Any, route: Mapping[str, str]) -> Any:
    provider = str(getattr(executor, "provider", "") or "").strip().casefold()
    model = str(getattr(executor, "model", "") or "").strip().casefold()
    if not provider:
        raise RouteAdmissionError("EXECUTOR_PROVIDER_ATTESTATION_MISSING")
    if not model:
        raise RouteAdmissionError("EXECUTOR_MODEL_ATTESTATION_MISSING")
    if provider != route["provider"].casefold():
        raise RouteAdmissionError("EXECUTOR_PROVIDER_ROUTE_MISMATCH")
    if model != route["model"].casefold():
        raise RouteAdmissionError("EXECUTOR_MODEL_ROUTE_MISMATCH")
    return executor


def prepare_exact_executor(
    route: Mapping[str, str],
    *,
    factory: Callable[[str, str], Any] = build_exact_executor,
):
    executor = factory(route["provider"], route["model"])
    return attest_executor(executor, route)
