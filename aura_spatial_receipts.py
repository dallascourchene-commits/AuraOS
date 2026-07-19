"""Bounded empirical and dissolution receipts for Aura spatial projection.

Receipts describe observed presentation and cleanup only. They are never proof
of domain truth, approval, execution, patch validity, promotion, or production
mutation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import re
from typing import Any

from aura_event_contracts import stable_digest
from aura_spatial_contracts import (
    SpatialDeviceProfile,
    SpatialDissolutionReceipt,
    SpatialProjectionSessionSummary,
    SpatialRendererKind,
    SpatialRenderEvidenceClass,
    SpatialRenderOutcome,
    SpatialRenderPlan,
    SpatialRenderReceipt,
    SpatialSessionState,
)

SPATIAL_RECEIPTS_VERSION = "AURA_SPATIAL_RECEIPTS_V1"
_RENDER_RECEIPT_KEYS = frozenset(
    {
        "receipt_id",
        "scene_id",
        "scene_digest",
        "plan_id",
        "render_plan_digest",
        "device_profile_digest",
        "renderer",
        "outcome",
        "evidence_class",
        "sequence",
        "metrics",
        "source_refs",
        "renderer_disposed",
        "projection_only",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "version",
        "schema_version",
        "render_receipt_digest",
    }
)
_DISSOLUTION_KEYS = frozenset(
    {
        "receipt_id",
        "session_id",
        "scene_digest",
        "render_plan_digest",
        "terminal_state",
        "reason_code",
        "sequence",
        "render_receipt_ids",
        "released_asset_ids",
        "source_refs",
        "renderer_disposed",
        "leases_released",
        "raw_sensor_data_retained",
        "production_mutation",
        "automatic_merge",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "version",
        "schema_version",
        "dissolution_digest",
    }
)

_TELEMETRY_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_MAX_TELEMETRY_TEXT = 256


def compile_spatial_render_receipt(
    plan: SpatialRenderPlan,
    device: SpatialDeviceProfile,
    *,
    renderer: SpatialRendererKind | str | None = None,
    outcome: SpatialRenderOutcome | str,
    evidence_class: SpatialRenderEvidenceClass | str,
    sequence: int,
    metrics: Mapping[str, Any] | None = None,
    renderer_disposed: bool = False,
    source_refs: Sequence[str] = (),
) -> SpatialRenderReceipt:
    if not isinstance(plan, SpatialRenderPlan):
        raise ValueError("plan must be a SpatialRenderPlan")
    if not isinstance(device, SpatialDeviceProfile):
        raise ValueError("device must be a SpatialDeviceProfile")
    if metrics is not None and not isinstance(metrics, Mapping):
        raise ValueError("metrics must be an object")
    if plan.device_profile_digest != device.device_profile_digest:
        raise ValueError("render plan is not bound to the supplied device profile")
    renderer_value = (
        plan.selected_renderer
        if renderer is None
        else (renderer if isinstance(renderer, SpatialRendererKind) else SpatialRendererKind(str(renderer)))
    )
    admitted = {plan.selected_renderer, *plan.fallback_renderers}
    if renderer_value not in admitted:
        raise ValueError("renderer was not admitted by the render plan")
    refs = tuple(
        sorted(
            {
                *plan.source_refs,
                *device.source_refs,
                *source_refs,
                f"render-plan:{plan.plan_id}#{plan.render_plan_digest}",
                "owner:aura_spatial_receipts.compile_spatial_render_receipt",
            }
        )
    )
    provisional = SpatialRenderReceipt(
        receipt_id="render-receipt:canonical",
        scene_id=plan.scene_id,
        scene_digest=plan.scene_digest,
        plan_id=plan.plan_id,
        render_plan_digest=plan.render_plan_digest,
        device_profile_digest=device.device_profile_digest,
        renderer=renderer_value,
        outcome=outcome,
        evidence_class=evidence_class,
        sequence=sequence,
        metrics=dict(metrics or {}),
        source_refs=refs,
        renderer_disposed=renderer_disposed,
        projection_only=True,
        renderer_authority=False,
        execution_authority=False,
        patch_authority=False,
    )
    canonical_metrics = provisional.to_dict()["metrics"]
    body = {
        "scene_digest": provisional.scene_digest,
        "render_plan_digest": provisional.render_plan_digest,
        "device_profile_digest": provisional.device_profile_digest,
        "renderer": provisional.renderer.value,
        "outcome": provisional.outcome.value,
        "evidence_class": provisional.evidence_class.value,
        "sequence": provisional.sequence,
        "metrics": canonical_metrics,
        "renderer_disposed": provisional.renderer_disposed,
    }
    receipt_id = "render-receipt:" + stable_digest(body, digest_size=12)
    return SpatialRenderReceipt(
        receipt_id=receipt_id,
        scene_id=provisional.scene_id,
        scene_digest=provisional.scene_digest,
        plan_id=provisional.plan_id,
        render_plan_digest=provisional.render_plan_digest,
        device_profile_digest=provisional.device_profile_digest,
        renderer=provisional.renderer,
        outcome=provisional.outcome,
        evidence_class=provisional.evidence_class,
        sequence=provisional.sequence,
        metrics=canonical_metrics,
        source_refs=provisional.source_refs,
        renderer_disposed=provisional.renderer_disposed,
        projection_only=True,
        renderer_authority=False,
        execution_authority=False,
        patch_authority=False,
    )


def compile_spatial_dissolution_receipt(
    summary: SpatialProjectionSessionSummary,
    *,
    reason_code: str,
    sequence: int,
    terminal_state: SpatialSessionState | str = SpatialSessionState.DISSOLVED,
    released_asset_ids: Sequence[str] = (),
    source_refs: Sequence[str] = (),
) -> SpatialDissolutionReceipt:
    if not isinstance(summary, SpatialProjectionSessionSummary):
        raise ValueError("summary must be a SpatialProjectionSessionSummary")
    state = (
        terminal_state if isinstance(terminal_state, SpatialSessionState) else SpatialSessionState(str(terminal_state))
    )
    if summary.state is SpatialSessionState.ACTIVE and state is not SpatialSessionState.DISSOLVED:
        raise ValueError("an active session may only transition directly to DISSOLVED")
    refs = tuple(
        sorted(
            {
                *summary.source_refs,
                *source_refs,
                f"session:{summary.session_id}#{summary.session_digest}",
                "owner:aura_spatial_receipts.compile_spatial_dissolution_receipt",
            }
        )
    )
    provisional = SpatialDissolutionReceipt(
        receipt_id="dissolution:canonical",
        session_id=summary.session_id,
        scene_digest=summary.scene_digest,
        render_plan_digest=summary.render_plan_digest,
        terminal_state=state,
        reason_code=reason_code,
        sequence=sequence,
        render_receipt_ids=summary.render_receipt_ids,
        released_asset_ids=tuple(released_asset_ids),
        source_refs=refs,
        renderer_disposed=True,
        leases_released=True,
        raw_sensor_data_retained=False,
        production_mutation=False,
        automatic_merge=False,
        renderer_authority=False,
        execution_authority=False,
        patch_authority=False,
    )
    body = {
        "session_id": provisional.session_id,
        "scene_digest": provisional.scene_digest,
        "render_plan_digest": provisional.render_plan_digest,
        "terminal_state": provisional.terminal_state.value,
        "reason_code": provisional.reason_code,
        "sequence": provisional.sequence,
        "render_receipt_ids": list(provisional.render_receipt_ids),
        "released_asset_ids": list(provisional.released_asset_ids),
    }
    receipt_id = "dissolution:" + stable_digest(body, digest_size=12)
    return SpatialDissolutionReceipt(
        receipt_id=receipt_id,
        session_id=provisional.session_id,
        scene_digest=provisional.scene_digest,
        render_plan_digest=provisional.render_plan_digest,
        terminal_state=provisional.terminal_state,
        reason_code=provisional.reason_code,
        sequence=provisional.sequence,
        render_receipt_ids=provisional.render_receipt_ids,
        released_asset_ids=provisional.released_asset_ids,
        source_refs=provisional.source_refs,
        renderer_disposed=True,
        leases_released=True,
        raw_sensor_data_retained=False,
        production_mutation=False,
        automatic_merge=False,
        renderer_authority=False,
        execution_authority=False,
        patch_authority=False,
    )


_BROWSER_TELEMETRY_CLASSES = frozenset({"MEASURED", "CALCULATED", "ESTIMATED", "UNAVAILABLE"})


def compile_spatial_browser_telemetry_receipt(
    plan: SpatialRenderPlan,
    device: SpatialDeviceProfile,
    packet: Mapping[str, Any],
    *,
    sequence: int,
) -> SpatialRenderReceipt:
    """Compile a bounded browser telemetry packet into an empirical render receipt."""

    if not isinstance(packet, Mapping):
        raise ValueError("browser telemetry packet must be an object")
    expected = {
        "version",
        "scene_digest",
        "render_plan_digest",
        "device_profile_digest",
        "fixture_digest",
        "renderer",
        "metrics",
        "projection_only",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "production_mutation",
        "automatic_merge",
        "human_review_required",
    }
    if set(packet) != expected:
        raise ValueError("browser telemetry keys mismatch")
    if packet["version"] != "AURA_SPATIAL_BROWSER_TELEMETRY_V1":
        raise ValueError("unsupported browser telemetry version")
    if packet["scene_digest"] != plan.scene_digest:
        raise ValueError("browser telemetry scene digest is stale")
    if packet["render_plan_digest"] != plan.render_plan_digest:
        raise ValueError("browser telemetry render plan digest is stale")
    if packet["device_profile_digest"] != device.device_profile_digest:
        raise ValueError("browser telemetry device digest is stale")
    fixture_digest = str(packet["fixture_digest"])
    if len(fixture_digest) != 64 or any(ch not in "0123456789abcdef" for ch in fixture_digest):
        raise ValueError("fixture_digest must be lowercase sha256")
    for key, required in (
        ("projection_only", True),
        ("human_review_required", True),
        ("renderer_authority", False),
        ("execution_authority", False),
        ("patch_authority", False),
        ("production_mutation", False),
        ("automatic_merge", False),
    ):
        if packet[key] is not required:
            raise ValueError(f"browser telemetry {key} boundary is invalid")
    metrics = packet["metrics"]
    if not isinstance(metrics, Mapping) or len(metrics) > 64:
        raise ValueError("browser telemetry metrics must be a bounded object")
    normalized: dict[str, Any] = {}
    observed_classes: set[str] = set()
    for name in sorted(metrics):
        if not isinstance(name, str) or not _TELEMETRY_NAME.fullmatch(name):
            raise ValueError(f"invalid telemetry metric name: {name}")
        metric = metrics[name]
        if not isinstance(metric, Mapping) or set(metric) != {"value", "unit", "evidence_class", "method"}:
            raise ValueError(f"invalid telemetry metric: {name}")
        evidence = str(metric["evidence_class"])
        if evidence not in _BROWSER_TELEMETRY_CLASSES:
            raise ValueError(f"invalid telemetry evidence class: {evidence}")
        value = metric["value"]
        if evidence == "UNAVAILABLE":
            if value is not None:
                raise ValueError("UNAVAILABLE telemetry values must be null")
        elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError("telemetry values must be finite numeric values or unavailable")
        unit = str(metric["unit"])
        method = str(metric["method"])
        if len(unit.encode("utf-8")) > 64 or len(method.encode("utf-8")) > _MAX_TELEMETRY_TEXT:
            raise ValueError("telemetry unit or method exceeds its byte ceiling")
        normalized[name] = {
            "value": value,
            "unit": unit,
            "evidence_class": evidence,
            "method": method,
        }
        observed_classes.add(evidence)
    overall = (
        SpatialRenderEvidenceClass.MEASURED
        if "MEASURED" in observed_classes
        else SpatialRenderEvidenceClass.DERIVED
        if "CALCULATED" in observed_classes
        else SpatialRenderEvidenceClass.ESTIMATED
        if "ESTIMATED" in observed_classes
        else SpatialRenderEvidenceClass.UNAVAILABLE
    )
    return compile_spatial_render_receipt(
        plan,
        device,
        renderer=packet["renderer"],
        outcome=SpatialRenderOutcome.PRESENTED,
        evidence_class=overall,
        sequence=sequence,
        metrics={
            "fixture_digest": fixture_digest,
            "browser_metrics": normalized,
        },
        renderer_disposed=False,
        source_refs=(f"browser-fixture:{fixture_digest}",),
    )


def validate_spatial_render_receipt_payload(
    payload: Mapping[str, Any],
) -> SpatialRenderReceipt:
    if not isinstance(payload, Mapping):
        raise ValueError("render receipt payload must be an object")
    _exact_keys(payload, _RENDER_RECEIPT_KEYS, "render receipt")
    receipt = SpatialRenderReceipt(
        receipt_id=payload["receipt_id"],
        scene_id=payload["scene_id"],
        scene_digest=payload["scene_digest"],
        plan_id=payload["plan_id"],
        render_plan_digest=payload["render_plan_digest"],
        device_profile_digest=payload["device_profile_digest"],
        renderer=payload["renderer"],
        outcome=payload["outcome"],
        evidence_class=payload["evidence_class"],
        sequence=payload["sequence"],
        metrics=payload["metrics"],
        source_refs=tuple(payload["source_refs"]),
        renderer_disposed=payload["renderer_disposed"],
        projection_only=payload["projection_only"],
        renderer_authority=payload["renderer_authority"],
        execution_authority=payload["execution_authority"],
        patch_authority=payload["patch_authority"],
        version=payload["version"],
        schema_version=payload["schema_version"],
    )
    if receipt.to_dict() != dict(payload):
        raise ValueError("render receipt payload is not canonical")
    return receipt


def validate_spatial_dissolution_receipt_payload(
    payload: Mapping[str, Any],
) -> SpatialDissolutionReceipt:
    if not isinstance(payload, Mapping):
        raise ValueError("dissolution receipt payload must be an object")
    _exact_keys(payload, _DISSOLUTION_KEYS, "dissolution receipt")
    receipt = SpatialDissolutionReceipt(
        receipt_id=payload["receipt_id"],
        session_id=payload["session_id"],
        scene_digest=payload["scene_digest"],
        render_plan_digest=payload["render_plan_digest"],
        terminal_state=payload["terminal_state"],
        reason_code=payload["reason_code"],
        sequence=payload["sequence"],
        render_receipt_ids=tuple(payload["render_receipt_ids"]),
        released_asset_ids=tuple(payload["released_asset_ids"]),
        source_refs=tuple(payload["source_refs"]),
        renderer_disposed=payload["renderer_disposed"],
        leases_released=payload["leases_released"],
        raw_sensor_data_retained=payload["raw_sensor_data_retained"],
        production_mutation=payload["production_mutation"],
        automatic_merge=payload["automatic_merge"],
        renderer_authority=payload["renderer_authority"],
        execution_authority=payload["execution_authority"],
        patch_authority=payload["patch_authority"],
        version=payload["version"],
        schema_version=payload["schema_version"],
    )
    if receipt.to_dict() != dict(payload):
        raise ValueError("dissolution receipt payload is not canonical")
    return receipt


def _exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    label: str,
) -> None:
    supplied = set(value)
    if supplied != expected:
        raise ValueError(
            f"{label} keys mismatch: missing={sorted(expected - supplied)}, extra={sorted(supplied - expected)}"
        )


__all__ = [
    "SPATIAL_RECEIPTS_VERSION",
    "compile_spatial_browser_telemetry_receipt",
    "compile_spatial_dissolution_receipt",
    "compile_spatial_render_receipt",
    "validate_spatial_dissolution_receipt_payload",
    "validate_spatial_render_receipt_payload",
]
