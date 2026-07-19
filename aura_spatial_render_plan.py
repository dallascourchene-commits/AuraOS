"""Deterministic renderer negotiation for immutable Aura spatial scenes.

This module selects a presentation adapter and bounded budgets only. It never
loads a renderer, allocates GPU resources, starts XR, fetches assets, or grants
render, execution, patch, promotion, or production authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from aura_event_contracts import stable_digest
from aura_spatial_contracts import (
    SpatialDeviceProfile,
    SpatialRenderBudget,
    SpatialRendererKind,
    SpatialRenderPlan,
    SpatialSceneSnapshot,
)

SPATIAL_RENDER_PLANNER_VERSION = "AURA_SPATIAL_RENDER_PLANNER_V1"
_DEFAULT_RENDERER_PREFERENCE = (
    SpatialRendererKind.WEBGPU,
    SpatialRendererKind.WEBGL2,
    SpatialRendererKind.ACCESSIBLE_2D,
    SpatialRendererKind.HEADLESS,
)
_DEVICE_PAYLOAD_KEYS = frozenset(
    {
        "profile_id",
        "supported_renderers",
        "budget",
        "accessibility_required",
        "xr_user_activation",
        "network_allowed",
        "source_refs",
        "metadata",
        "fingerprinting_allowed",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "version",
        "schema_version",
        "device_profile_digest",
    }
)
_PLAN_PAYLOAD_KEYS = frozenset(
    {
        "plan_id",
        "scene_id",
        "scene_digest",
        "device_profile_digest",
        "selected_renderer",
        "fallback_renderers",
        "budget",
        "scene_entity_count",
        "scene_link_count",
        "scene_asset_count",
        "scene_asset_bytes",
        "reasons",
        "source_refs",
        "accessible_fallback_required",
        "xr_user_activation_observed",
        "projection_only",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "version",
        "schema_version",
        "render_plan_digest",
    }
)
_BUDGET_KEYS = frozenset(
    {
        "max_entities",
        "max_links",
        "max_assets",
        "max_asset_bytes",
        "max_cpu_ms_per_frame",
        "max_gpu_bytes",
        "max_network_bytes",
    }
)


def compile_spatial_device_profile(
    *,
    profile_id: str,
    supported_renderers: Sequence[SpatialRendererKind | str],
    budget: SpatialRenderBudget | Mapping[str, Any] | None = None,
    accessibility_required: bool = True,
    xr_user_activation: bool = False,
    network_allowed: bool = False,
    source_refs: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> SpatialDeviceProfile:
    """Compile a bounded, non-fingerprinting presentation capability profile."""

    return SpatialDeviceProfile(
        profile_id=profile_id,
        supported_renderers=tuple(supported_renderers),
        budget=_budget(budget or SpatialRenderBudget()),
        accessibility_required=accessibility_required,
        xr_user_activation=xr_user_activation,
        network_allowed=network_allowed,
        source_refs=tuple(source_refs),
        metadata=dict(metadata or {}),
        fingerprinting_allowed=False,
        renderer_authority=False,
        execution_authority=False,
        patch_authority=False,
    )


def negotiate_spatial_render_plan(
    scene: SpatialSceneSnapshot,
    device: SpatialDeviceProfile,
    *,
    preferred_renderers: Sequence[SpatialRendererKind | str] = (),
    requested_budget: SpatialRenderBudget | Mapping[str, Any] | None = None,
    allow_xr: bool = False,
) -> SpatialRenderPlan:
    """Select one deterministic renderer plus accessible, bounded fallbacks."""

    if not isinstance(scene, SpatialSceneSnapshot):
        raise ValueError("scene must be a SpatialSceneSnapshot")
    if not isinstance(device, SpatialDeviceProfile):
        raise ValueError("device must be a SpatialDeviceProfile")
    if type(allow_xr) is not bool:
        raise ValueError("allow_xr must be a boolean")

    preference = _preferred_renderers(preferred_renderers, allow_xr=allow_xr)
    supported = set(device.supported_renderers)
    reasons: list[str] = []
    eligible: list[SpatialRendererKind] = []
    for renderer in preference:
        if renderer not in supported:
            reasons.append(f"{renderer.value}:unsupported")
            continue
        if renderer is SpatialRendererKind.WEBXR:
            if not allow_xr:
                reasons.append("WEBXR:not_requested")
                continue
            if not device.xr_user_activation:
                reasons.append("WEBXR:user_activation_not_observed")
                continue
        eligible.append(renderer)

    if not eligible:
        raise ValueError("device has no eligible bounded spatial renderer")
    selected = eligible[0]
    fallbacks = [item for item in eligible[1:] if item is not selected]
    if selected is not SpatialRendererKind.ACCESSIBLE_2D and SpatialRendererKind.ACCESSIBLE_2D not in fallbacks:
        if SpatialRendererKind.ACCESSIBLE_2D not in supported:
            raise ValueError("device lost the mandatory ACCESSIBLE_2D fallback")
        fallbacks.append(SpatialRendererKind.ACCESSIBLE_2D)
    if (
        SpatialRendererKind.HEADLESS in supported
        and SpatialRendererKind.HEADLESS is not selected
        and SpatialRendererKind.HEADLESS not in fallbacks
    ):
        fallbacks.append(SpatialRendererKind.HEADLESS)

    budget = _effective_budget(
        device.budget,
        _budget(requested_budget) if requested_budget is not None else None,
        network_allowed=device.network_allowed,
    )
    entity_count = len(scene.entities)
    link_count = len(scene.links)
    asset_count = len(scene.assets)
    asset_bytes = sum(item.byte_length for item in scene.assets)
    _assert_scene_budget(
        entity_count=entity_count,
        link_count=link_count,
        asset_count=asset_count,
        asset_bytes=asset_bytes,
        budget=budget,
    )

    reasons.insert(0, f"selected:{selected.value}")
    reasons.append("accessible_2d_fallback:required")
    reasons.append("renderer_authority:false")
    reasons.append("scene_digest:bound")
    body = {
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "device_profile_digest": device.device_profile_digest,
        "selected_renderer": selected.value,
        "fallback_renderers": [item.value for item in fallbacks],
        "budget": budget.to_dict(),
        "scene_entity_count": entity_count,
        "scene_link_count": link_count,
        "scene_asset_count": asset_count,
        "scene_asset_bytes": asset_bytes,
        "reasons": reasons,
        "allow_xr": allow_xr,
        "xr_user_activation": device.xr_user_activation,
    }
    plan_id = "render-plan:" + stable_digest(body, digest_size=12)
    refs = tuple(
        sorted(
            {
                *scene.source_refs,
                *device.source_refs,
                f"scene:{scene.scene_id}#{scene.scene_digest}",
                f"device:{device.profile_id}#{device.device_profile_digest}",
                "owner:aura_spatial_render_plan.negotiate_spatial_render_plan",
            }
        )
    )
    return SpatialRenderPlan(
        plan_id=plan_id,
        scene_id=scene.scene_id,
        scene_digest=scene.scene_digest,
        device_profile_digest=device.device_profile_digest,
        selected_renderer=selected,
        fallback_renderers=tuple(fallbacks),
        budget=budget,
        scene_entity_count=entity_count,
        scene_link_count=link_count,
        scene_asset_count=asset_count,
        scene_asset_bytes=asset_bytes,
        reasons=tuple(reasons),
        source_refs=refs,
        accessible_fallback_required=True,
        xr_user_activation_observed=(selected is SpatialRendererKind.WEBXR and device.xr_user_activation),
        projection_only=True,
        renderer_authority=False,
        execution_authority=False,
        patch_authority=False,
    )


def compile_gaussian_representation_budget(
    scene: SpatialSceneSnapshot,
    plan: SpatialRenderPlan,
    *,
    maximum_visible_splats: int = 2_000_000,
) -> Mapping[str, Any]:
    """Derive an isolated Gaussian budget from an already-admitted render plan."""

    if not isinstance(scene, SpatialSceneSnapshot) or not isinstance(plan, SpatialRenderPlan):
        raise ValueError("scene and plan must be retained spatial contracts")
    if plan.scene_id != scene.scene_id or plan.scene_digest != scene.scene_digest:
        raise ValueError("Gaussian budget cannot use a stale scene or render plan")
    if type(maximum_visible_splats) is not int or not 1 <= maximum_visible_splats <= 2_000_000:
        raise ValueError("maximum_visible_splats exceeds bounds")
    gaussian_assets = [item for item in scene.assets if item.asset_type.value == "GAUSSIAN_SPLAT"]
    declared_splats = 0
    declared_decoded_bytes = 0
    declared_gpu_bytes = 0
    maximum_bytes_per_splat = 0
    for asset in gaussian_assets:
        metadata = dict(asset.metadata)
        count = metadata.get("element_count")
        decoded = metadata.get("decoded_bytes")
        sh_degree = metadata.get("gaussian_sh_degree")
        color_space = metadata.get("gaussian_color_space")
        receipt_digest = metadata.get("import_receipt_digest")
        if type(count) is not int or count < 1 or count > 2_000_000:
            raise ValueError(f"Gaussian asset {asset.asset_id} lacks a bounded element_count")
        if type(decoded) is not int or decoded < 0 or decoded > 4_294_967_296:
            raise ValueError(f"Gaussian asset {asset.asset_id} lacks bounded decoded_bytes")
        if type(sh_degree) is not int or not 0 <= sh_degree <= 4:
            raise ValueError(f"Gaussian asset {asset.asset_id} lacks a bounded gaussian_sh_degree")
        if color_space not in {"SPZ_INTERNAL_WIDE_RGB", "srgb_rec709_display", "lin_rec709_display"}:
            raise ValueError(f"Gaussian asset {asset.asset_id} lacks a supported gaussian_color_space")
        if (
            not isinstance(receipt_digest, str)
            or len(receipt_digest) != 64
            or any(character not in "0123456789abcdef" for character in receipt_digest)
        ):
            raise ValueError(f"Gaussian asset {asset.asset_id} lacks an import receipt digest")
        bytes_per_splat = 48 + ((sh_degree + 1) ** 2 * 3 * 4)
        declared_splats += count
        declared_decoded_bytes += decoded
        declared_gpu_bytes += count * bytes_per_splat
        maximum_bytes_per_splat = max(maximum_bytes_per_splat, bytes_per_splat)
    visible_by_gpu = (
        plan.budget.max_gpu_bytes // maximum_bytes_per_splat if maximum_bytes_per_splat else maximum_visible_splats
    )
    visible_by_allocation = (
        plan.budget.max_asset_bytes // (maximum_bytes_per_splat + 4)
        if maximum_bytes_per_splat
        else maximum_visible_splats
    )
    visible = min(
        maximum_visible_splats,
        visible_by_gpu,
        visible_by_allocation,
        declared_splats or maximum_visible_splats,
    )
    if gaussian_assets and visible < 1:
        raise ValueError("render plan cannot allocate one Gaussian splat")
    return {
        "scene_id": scene.scene_id,
        "scene_digest": scene.scene_digest,
        "render_plan_digest": plan.render_plan_digest,
        "asset_count": len(gaussian_assets),
        "declared_splats": declared_splats,
        "declared_decoded_bytes": declared_decoded_bytes,
        "declared_gpu_bytes": declared_gpu_bytes,
        "max_bytes_per_splat": maximum_bytes_per_splat,
        "max_visible_splats": visible,
        "max_gpu_bytes": min(plan.budget.max_gpu_bytes, visible * maximum_bytes_per_splat),
        "max_sort_items": visible,
        "max_sort_bytes": visible * 4,
        "max_allocation_bytes": min(plan.budget.max_asset_bytes, visible * (maximum_bytes_per_splat + 4)),
        "max_frame_ms": plan.budget.max_cpu_ms_per_frame,
        "accessible_fallback_required": True,
        "point_cloud_fallback_required": True,
        "headless_fallback_required": True,
        "projection_only": True,
        "renderer_authority": False,
        "execution_authority": False,
        "patch_authority": False,
    }


def validate_spatial_device_profile_payload(
    payload: Mapping[str, Any],
) -> SpatialDeviceProfile:
    if not isinstance(payload, Mapping):
        raise ValueError("device profile payload must be an object")
    _exact_keys(payload, _DEVICE_PAYLOAD_KEYS, "device profile")
    profile = SpatialDeviceProfile(
        profile_id=payload["profile_id"],
        supported_renderers=tuple(payload["supported_renderers"]),
        budget=_budget(payload["budget"]),
        accessibility_required=payload["accessibility_required"],
        xr_user_activation=payload["xr_user_activation"],
        network_allowed=payload["network_allowed"],
        source_refs=tuple(payload["source_refs"]),
        metadata=payload["metadata"],
        fingerprinting_allowed=payload["fingerprinting_allowed"],
        renderer_authority=payload["renderer_authority"],
        execution_authority=payload["execution_authority"],
        patch_authority=payload["patch_authority"],
        version=payload["version"],
        schema_version=payload["schema_version"],
    )
    if profile.to_dict() != dict(payload):
        raise ValueError("device profile payload is not canonical")
    return profile


def validate_spatial_render_plan_payload(
    payload: Mapping[str, Any],
) -> SpatialRenderPlan:
    if not isinstance(payload, Mapping):
        raise ValueError("render plan payload must be an object")
    _exact_keys(payload, _PLAN_PAYLOAD_KEYS, "render plan")
    plan = SpatialRenderPlan(
        plan_id=payload["plan_id"],
        scene_id=payload["scene_id"],
        scene_digest=payload["scene_digest"],
        device_profile_digest=payload["device_profile_digest"],
        selected_renderer=payload["selected_renderer"],
        fallback_renderers=tuple(payload["fallback_renderers"]),
        budget=_budget(payload["budget"]),
        scene_entity_count=payload["scene_entity_count"],
        scene_link_count=payload["scene_link_count"],
        scene_asset_count=payload["scene_asset_count"],
        scene_asset_bytes=payload["scene_asset_bytes"],
        reasons=tuple(payload["reasons"]),
        source_refs=tuple(payload["source_refs"]),
        accessible_fallback_required=payload["accessible_fallback_required"],
        xr_user_activation_observed=payload["xr_user_activation_observed"],
        projection_only=payload["projection_only"],
        renderer_authority=payload["renderer_authority"],
        execution_authority=payload["execution_authority"],
        patch_authority=payload["patch_authority"],
        version=payload["version"],
        schema_version=payload["schema_version"],
    )
    if plan.to_dict() != dict(payload):
        raise ValueError("render plan payload is not canonical")
    return plan


def _preferred_renderers(
    values: Sequence[SpatialRendererKind | str],
    *,
    allow_xr: bool,
) -> tuple[SpatialRendererKind, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError("preferred_renderers must be a sequence")
    source: Sequence[SpatialRendererKind | str]
    if values:
        source = values
    elif allow_xr:
        source = (SpatialRendererKind.WEBXR, *_DEFAULT_RENDERER_PREFERENCE)
    else:
        source = _DEFAULT_RENDERER_PREFERENCE
    result: list[SpatialRendererKind] = []
    for value in source:
        try:
            renderer = value if isinstance(value, SpatialRendererKind) else SpatialRendererKind(str(value))
        except ValueError as exc:
            raise ValueError(f"unsupported preferred renderer: {value}") from exc
        if renderer in result:
            raise ValueError("preferred_renderers values must be unique")
        result.append(renderer)
    if SpatialRendererKind.ACCESSIBLE_2D not in result:
        result.append(SpatialRendererKind.ACCESSIBLE_2D)
    return tuple(result)


def _budget(value: SpatialRenderBudget | Mapping[str, Any]) -> SpatialRenderBudget:
    if isinstance(value, SpatialRenderBudget):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("render budget must be an object")
    _exact_keys(value, _BUDGET_KEYS, "render budget")
    return SpatialRenderBudget(**dict(value))


def _effective_budget(
    device: SpatialRenderBudget,
    requested: SpatialRenderBudget | None,
    *,
    network_allowed: bool,
) -> SpatialRenderBudget:
    if requested is None:
        requested = device
    return SpatialRenderBudget(
        max_entities=min(device.max_entities, requested.max_entities),
        max_links=min(device.max_links, requested.max_links),
        max_assets=min(device.max_assets, requested.max_assets),
        max_asset_bytes=min(device.max_asset_bytes, requested.max_asset_bytes),
        max_cpu_ms_per_frame=min(
            device.max_cpu_ms_per_frame,
            requested.max_cpu_ms_per_frame,
        ),
        max_gpu_bytes=min(device.max_gpu_bytes, requested.max_gpu_bytes),
        max_network_bytes=(min(device.max_network_bytes, requested.max_network_bytes) if network_allowed else 0),
    )


def _assert_scene_budget(
    *,
    entity_count: int,
    link_count: int,
    asset_count: int,
    asset_bytes: int,
    budget: SpatialRenderBudget,
) -> None:
    checks = (
        (entity_count, budget.max_entities, "entities"),
        (link_count, budget.max_links, "links"),
        (asset_count, budget.max_assets, "assets"),
        (asset_bytes, budget.max_asset_bytes, "asset bytes"),
    )
    exceeded = [name for observed, limit, name in checks if observed > limit]
    if exceeded:
        raise ValueError("scene exceeds bounded render budget: " + ", ".join(exceeded))


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
    "SPATIAL_RENDER_PLANNER_VERSION",
    "compile_spatial_device_profile",
    "negotiate_spatial_render_plan",
    "validate_spatial_device_profile_payload",
    "validate_spatial_render_plan_payload",
]
