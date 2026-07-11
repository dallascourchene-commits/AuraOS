"""Deterministic capability binding over Aura's existing registries.

This module is an adapter, not another registry. It resolves a terminal grammar symbol
to already-installed tools, affordances, lanes, or plugins and fails closed when the
binding cannot be grounded.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CAPABILITY_BINDING_VERSION = "AURA_CAPABILITY_BINDING_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class CapabilityBinding:
    capability_id: str
    binding_type: str
    implementation_id: str
    runtime: str
    risk: str
    lease_capabilities: tuple[str, ...]
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()
    grounded: bool = True
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["lease_capabilities"] = list(self.lease_capabilities)
        data["requires"] = list(self.requires)
        data["produces"] = list(self.produces)
        data["version"] = CAPABILITY_BINDING_VERSION
        data["patch_authority"] = PATCH_AUTHORITY
        data["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return data


def capability_exists(capability_id: str, *, repo_root: str | Path = ".") -> bool:
    return bool(resolve_capability_binding(capability_id, repo_root=repo_root).get("ok"))


def resolve_capability_binding(capability_id: str, *, repo_root: str | Path = ".") -> dict[str, Any]:
    requested = str(capability_id or "").strip()
    if not requested:
        return _denied(requested, "capability_id_required")
    namespace, separator, local_id = requested.partition(":")
    if not separator:
        namespace, local_id = "tool", requested
    namespace = namespace.casefold()
    local_id = local_id.strip()
    if namespace == "tool":
        return _resolve_tool(requested, local_id)
    if namespace == "affordance":
        return _resolve_affordance(requested, local_id, repo_root)
    if namespace == "lane":
        return _resolve_lane(requested, local_id)
    if namespace == "plugin":
        return _resolve_plugin(requested, local_id, repo_root)
    return _denied(requested, f"unsupported_capability_namespace:{namespace}")


def resolve_capability_bindings(capability_ids, *, repo_root: str | Path = ".") -> dict[str, Any]:
    bindings: list[dict[str, Any]] = []
    denials: list[dict[str, Any]] = []
    for capability_id in capability_ids:
        result = resolve_capability_binding(capability_id, repo_root=repo_root)
        if result.get("ok"):
            bindings.append(dict(result["binding"]))
        else:
            denials.append(result)
    return {
        "ok": not denials,
        "bindings": bindings,
        "denials": denials,
        "requested": [str(item) for item in capability_ids],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _resolve_tool(requested: str, tool_id: str) -> dict[str, Any]:
    try:
        from aura_arena_tool_runtime import TOOLS
    except Exception as exc:
        return _denied(requested, f"tool_registry_unavailable:{type(exc).__name__}")
    tool = TOOLS.get(tool_id)
    if tool is None:
        return _denied(requested, "tool_not_registered")
    return _allowed(CapabilityBinding(
        capability_id=requested,
        binding_type="arena_tool",
        implementation_id=tool.tool_id,
        runtime=tool.runtime,
        risk=tool.risk,
        lease_capabilities=(tool.capability,),
        requires=tuple(tool.requires),
        produces=tuple(tool.produces),
        source="aura_arena_tool_runtime.TOOLS",
        metadata={"stage": tool.stage, "title": tool.title},
    ))


def _resolve_affordance(requested: str, affordance_id: str, repo_root: str | Path) -> dict[str, Any]:
    try:
        from aura_affordance_directory import load_affordance_directory
        directory = load_affordance_directory(Path(repo_root).resolve())
    except Exception as exc:
        return _denied(requested, f"affordance_directory_unavailable:{type(exc).__name__}")
    for item in directory:
        item_id = str(getattr(item, "id", getattr(item, "affordance_id", "")))
        if item_id != affordance_id:
            continue
        implemented_by = tuple(str(value) for value in getattr(item, "implemented_by", ()) or ())
        return _allowed(CapabilityBinding(
            capability_id=requested,
            binding_type="affordance",
            implementation_id=affordance_id,
            runtime="registered_affordance",
            risk=str(getattr(item, "risk", "unknown")),
            lease_capabilities=(affordance_id,),
            source="aura_affordance_directory",
            metadata={"implemented_by": list(implemented_by), "grounding": str(getattr(item, "grounding", ""))},
        ))
    return _denied(requested, "affordance_not_registered")


def _resolve_lane(requested: str, lane_id: str) -> dict[str, Any]:
    try:
        from aura_capability_lane_registry import load_capability_lanes
        lanes = load_capability_lanes()
    except Exception as exc:
        return _denied(requested, f"capability_lane_registry_unavailable:{type(exc).__name__}")
    for lane in lanes:
        if str(getattr(lane, "lane_id", "")) != lane_id:
            continue
        return _allowed(CapabilityBinding(
            capability_id=requested,
            binding_type="capability_lane",
            implementation_id=lane_id,
            runtime="advisory_lane",
            risk="advisory",
            lease_capabilities=(lane_id,),
            source="aura_capability_lane_registry",
            metadata={"advisory_only": bool(getattr(lane, "advisory_only", True))},
        ))
    return _denied(requested, "capability_lane_not_registered")


def _resolve_plugin(requested: str, plugin_id: str, repo_root: str | Path) -> dict[str, Any]:
    try:
        from aura_cockpit_plugin_registration import list_registered_plugins
        payload = list_registered_plugins(repo_root=Path(repo_root).resolve())
        plugins = payload.get("plugins", []) if isinstance(payload, dict) else []
    except Exception as exc:
        return _denied(requested, f"plugin_registry_unavailable:{type(exc).__name__}")
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        candidate = str(plugin.get("plugin_id") or plugin.get("id") or "")
        if candidate != plugin_id:
            continue
        return _allowed(CapabilityBinding(
            capability_id=requested,
            binding_type="plugin",
            implementation_id=plugin_id,
            runtime=str(plugin.get("runtime") or "registered_plugin"),
            risk=str(plugin.get("risk") or "unknown"),
            lease_capabilities=tuple(str(item) for item in plugin.get("capabilities", []) or [plugin_id]),
            source="aura_cockpit_plugin_registration",
            metadata={"manifest_digest": plugin.get("manifest_digest", "")},
        ))
    return _denied(requested, "plugin_not_registered")


def _allowed(binding: CapabilityBinding) -> dict[str, Any]:
    return {
        "ok": True,
        "binding": binding.to_dict(),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _denied(capability_id: str, reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "capability_id": capability_id,
        "reason": reason,
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
