from __future__ import annotations

"""Duck-typed bridge from PR863 K27MemoryRuntime into Navigator RouteIdentity."""
from dataclasses import dataclass
from typing import Any

from .route_card_admission import RouteIdentity


class RuntimeBridgeError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeBridgeReceipt:
    object_id: str
    runtime_state_root: str
    registry_semantic_root: str
    revision_id: str
    lifecycle_epoch: int
    k27: tuple[int, ...]
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def _hex64(value: Any, field: str) -> str:
    if (not isinstance(value, str) or len(value) != 64 or value.lower() != value
            or any(c not in "0123456789abcdef" for c in value)):
        raise RuntimeBridgeError(f"{field} must be lowercase SHA-256 hex")
    return value


def route_identity_from_runtime(runtime: Any, object_id: str, *, objective_root: str,
                                dependency_root: str, owner_incarnation: str,
                                currentness_generation: int) -> tuple[RouteIdentity, RuntimeBridgeReceipt]:
    """Project one exact PR863 runtime read into Navigator identity.

    The bridge consumes runtime-observed local identity only. owner_incarnation,
    dependency_root and currentness_generation remain explicit caller/upstream
    evidence and are never inferred from K27 locality. The observed runtime state
    root and revision are bound into RouteIdentity so admission cannot discard the
    bridge receipt and silently replay a proof across a runtime incarnation change.
    """
    if not isinstance(object_id, str) or not object_id:
        raise RuntimeBridgeError("object_id required")
    if not isinstance(owner_incarnation, str) or not owner_incarnation:
        raise RuntimeBridgeError("owner_incarnation required")
    if type(currentness_generation) is not int or currentness_generation < 0:
        raise RuntimeBridgeError("currentness_generation must be non-negative exact int")
    _hex64(objective_root, "objective_root")
    _hex64(dependency_root, "dependency_root")

    seal = runtime.seal
    state_root = _hex64(getattr(runtime, "_state_root", None), "runtime_state_root")
    semantic = _hex64(getattr(seal, "semantic_registry_root", None), "semantic_registry_root")
    binding, _record = runtime.read(object_id)

    if any(bool(getattr(binding, name, False)) for name in (
        "truth_authority", "planning_authority", "effect_authority", "gate10"
    )):
        raise RuntimeBridgeError("runtime binding widened authority")
    revision_id = getattr(binding, "revision_id", None)
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise RuntimeBridgeError("revision_id required")
    path = tuple(binding.path)
    route = RouteIdentity(
        objective_root=objective_root,
        target_id=object_id,
        source_root=semantic,
        dependency_root=dependency_root,
        map_generation=binding.frame_generation,
        lifecycle_epoch=binding.epoch,
        owner_incarnation=owner_incarnation,
        currentness_generation=currentness_generation,
        k27=path,
        runtime_state_root=state_root,
        revision_id=revision_id,
    )
    receipt = RuntimeBridgeReceipt(
        object_id=object_id,
        runtime_state_root=state_root,
        registry_semantic_root=semantic,
        revision_id=revision_id,
        lifecycle_epoch=binding.epoch,
        k27=path,
    )
    return route, receipt
