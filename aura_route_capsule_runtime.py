"""Live, bounded materialization for already-admissible Aura route capsules.

This layer never admits transitions. The guarded Arena runtime calls it only after
hard guards and existing capability binding have passed.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from aura_polysynthetic_intent import PolysyntheticIntentPacket, bind_intent_packet
from aura_route_capsule_binding import rank_admissible_capsules
from aura_route_capsule_compiler import compile_route_capsule
from aura_route_capsule_registry import load_registry_component
from aura_route_capsule_types import CompiledRouteCapsule

ROUTE_CAPSULE_RUNTIME_VERSION = "AURA_ROUTE_CAPSULE_RUNTIME_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class CapsuleMaterialization:
    capsule_id: str
    transition_id: str
    capsule_digest: str
    capsule_manifest_digest: str
    intent_packet_digest: str
    vsa_profile_digest: str
    resonance: float
    component_digests: dict[str, str]
    data_aperture: dict[str, Any]
    memory_aperture: dict[str, Any]
    tool_bundle: dict[str, Any]
    model_policy: dict[str, Any]
    execution_budget: dict[str, Any]
    verifier_contract: dict[str, Any]
    output_schema: dict[str, Any]
    capability_bindings: tuple[dict[str, Any], ...]
    intent_source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ROUTE_CAPSULE_RUNTIME_VERSION,
            "capsule_id": self.capsule_id,
            "transition_id": self.transition_id,
            "capsule_digest": self.capsule_digest,
            "capsule_manifest_digest": self.capsule_manifest_digest,
            "intent_packet_digest": self.intent_packet_digest,
            "vsa_profile_digest": self.vsa_profile_digest,
            "resonance": self.resonance,
            "component_digests": dict(sorted(self.component_digests.items())),
            "data_aperture": dict(self.data_aperture),
            "memory_aperture": dict(self.memory_aperture),
            "tool_bundle": dict(self.tool_bundle),
            "model_policy": dict(self.model_policy),
            "execution_budget": dict(self.execution_budget),
            "verifier_contract": dict(self.verifier_contract),
            "output_schema": dict(self.output_schema),
            "capability_bindings": [dict(item) for item in self.capability_bindings],
            "intent_source": self.intent_source,
            "runtime_authority": "bounded_after_hard_guards",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_activation": False,
            "automatic_grammar_promotion": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }


def compile_transition_capsule(transition: Any, *, repo_root: str | Path) -> CompiledRouteCapsule:
    reference = str(getattr(transition, "route_capsule_ref", "") or "").strip()
    if not reference:
        raise ValueError("transition has no route_capsule_ref")
    result = compile_route_capsule(reference, repo_root=repo_root)
    if not result.ok or result.compiled is None:
        detail = [item.to_dict() for item in result.diagnostics]
        raise ValueError(f"route capsule compilation failed: {json.dumps(detail, sort_keys=True)}")
    compiled = result.compiled
    if compiled.capsule.transition_id != transition.transition_id:
        raise ValueError("route capsule transition_id does not match Arena transition")
    profile_ref = str(getattr(transition, "morphology_profile_ref", "") or "").strip()
    if profile_ref and compiled.capsule.morphology_profile_ref != profile_ref:
        raise ValueError("route capsule morphology_profile_ref does not match Arena transition")
    return compiled


def materialize_route_capsule(
    compiled: CompiledRouteCapsule,
    *,
    repo_root: str | Path,
    input_text: str,
    context: Mapping[str, Any] | None = None,
) -> CapsuleMaterialization:
    context = dict(context or {})
    packet, intent_source = _intent_packet(compiled, input_text=input_text, context=context)
    bound = _bind_with_pinned_profile(compiled, packet, repo_root=repo_root)
    ranked = rank_admissible_capsules(
        bound,
        [compiled],
        admissible_capsule_ids={compiled.capsule.capsule_id},
        repo_root=repo_root,
    )
    if len(ranked) != 1:
        raise ValueError("admissible capsule did not produce exactly one resonance score")

    components = {}
    for field_name in (
        "data_aperture_ref", "memory_aperture_ref", "tool_bundle_ref",
        "model_policy_ref", "execution_budget_ref", "verifier_contract_ref",
        "output_schema_ref",
    ):
        component = load_registry_component(
            repo_root, getattr(compiled.capsule, field_name), field_name=field_name
        )
        expected = compiled.component_digests.get(field_name)
        if component.digest != expected:
            raise ValueError(f"stale compiled component digest: {field_name}")
        components[field_name] = component.payload

    data_aperture = _bounded_data_aperture(components["data_aperture_ref"])
    memory_aperture = _bounded_memory_aperture(components["memory_aperture_ref"])
    tool_bundle = _bounded_tool_bundle(components["tool_bundle_ref"], compiled)
    execution_budget = _bounded_execution_budget(components["execution_budget_ref"])
    model_policy = _plain_component(components["model_policy_ref"])
    verifier_contract = _plain_component(components["verifier_contract_ref"])
    output_schema = _plain_component(components["output_schema_ref"])

    return CapsuleMaterialization(
        capsule_id=compiled.capsule.capsule_id,
        transition_id=compiled.capsule.transition_id,
        capsule_digest=compiled.capsule.digest(),
        capsule_manifest_digest=compiled.capsule_manifest_digest,
        intent_packet_digest=packet.digest(),
        vsa_profile_digest=bound.vsa_profile_digest,
        resonance=ranked[0].resonance,
        component_digests=dict(compiled.component_digests),
        data_aperture=data_aperture,
        memory_aperture=memory_aperture,
        tool_bundle=tool_bundle,
        model_policy=model_policy,
        execution_budget=execution_budget,
        verifier_contract=verifier_contract,
        output_schema=output_schema,
        capability_bindings=compiled.capability_bindings,
        intent_source=intent_source,
    )


def capsule_observation(route: Mapping[str, Any] | None) -> dict[str, Any]:
    selected = dict((route or {}).get("selected") or {})
    capsule = selected.get("route_capsule")
    if not isinstance(capsule, dict):
        return {}
    usage = dict(selected.get("route_capsule_usage") or {})
    return {
        "capsule_id": str(capsule.get("capsule_id") or ""),
        "transition_id": str(capsule.get("transition_id") or ""),
        "capsule_digest": str(capsule.get("capsule_digest") or ""),
        "capsule_manifest_digest": str(capsule.get("capsule_manifest_digest") or ""),
        "intent_packet_digest": str(capsule.get("intent_packet_digest") or ""),
        "vsa_profile_digest": str(capsule.get("vsa_profile_digest") or ""),
        "component_digests": dict(capsule.get("component_digests") or {}),
        "resonance": capsule.get("resonance"),
        "actual_context_items": list(usage.get("actual_context_items") or []),
        "actual_tool_calls": list(usage.get("actual_tool_calls") or []),
        "actual_model": str(usage.get("actual_model") or ""),
        "budget_requested": dict(capsule.get("execution_budget") or {}),
        "budget_consumed": dict(usage.get("budget_consumed") or {}),
        "runtime_authority": "bounded_after_hard_guards",
    }


def _intent_packet(compiled: CompiledRouteCapsule, *, input_text: str, context: dict[str, Any]):
    explicit = context.get("polysynthetic_intent")
    if isinstance(explicit, Mapping):
        slots = explicit.get("slots") if isinstance(explicit.get("slots"), Mapping) else explicit
        adjuncts = explicit.get("adjuncts") if isinstance(explicit.get("adjuncts"), Mapping) else {}
        return PolysyntheticIntentPacket.from_slots(
            slots,
            adjuncts=adjuncts,
            objective=str(context.get("objective") or input_text or ""),
        ), "context.polysynthetic_intent"
    return PolysyntheticIntentPacket.from_slots(
        compiled.capsule.morphology_signature,
        adjuncts=compiled.capsule.routing_adjuncts,
        objective=str(context.get("objective") or input_text or ""),
    ), "capsule_signature_fallback"


def _bind_with_pinned_profile(compiled, packet, *, repo_root):
    from aura_vsa_encoding_profile import VSAEncodingProfile
    component = load_registry_component(
        repo_root, compiled.capsule.vsa_profile_ref, field_name="vsa_profile_ref"
    )
    if component.digest != compiled.component_digests.get("vsa_profile_ref"):
        raise ValueError("stale compiled VSA profile digest")
    return bind_intent_packet(packet, VSAEncodingProfile.from_dict(component.payload))


def _bounded_data_aperture(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _plain_component(payload)
    for key in ("maximum_files", "maximum_symbols", "maximum_lines"):
        result[key] = _positive_int(payload.get(key), key)
    if result.get("allow_unbounded_repository_context") is True:
        raise ValueError("data aperture may not allow unbounded repository context")
    return result


def _bounded_memory_aperture(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _plain_component(payload)
    result["maximum_experiences"] = _positive_int(payload.get("maximum_experiences"), "maximum_experiences")
    result["states"] = [str(item) for item in payload.get("states", []) if str(item)]
    result["transition_ids"] = [str(item) for item in payload.get("transition_ids", []) if str(item)]
    result["exclude"] = [str(item) for item in payload.get("exclude", []) if str(item)]
    return result


def _bounded_tool_bundle(payload: Mapping[str, Any], compiled: CompiledRouteCapsule) -> dict[str, Any]:
    result = _plain_component(payload)
    requested = [str(item) for item in payload.get("requested_capabilities", []) if str(item)]
    forbidden = {str(item) for item in payload.get("forbidden_capabilities", []) if str(item)}
    if tuple(requested) != compiled.capsule.requested_capabilities:
        raise ValueError("tool bundle no longer matches compiled capsule capabilities")
    if forbidden.intersection(requested):
        raise ValueError("tool bundle requests a forbidden capability")
    result["requested_capabilities"] = requested
    result["forbidden_capabilities"] = sorted(forbidden)
    return result


def _bounded_execution_budget(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = _plain_component(payload)
    for key in ("input_tokens", "output_tokens", "tool_calls", "model_calls", "wall_seconds"):
        result[key] = _positive_int(payload.get(key), key)
    return result


def _plain_component(payload: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(dict(payload), sort_keys=True, default=str))


def _positive_int(value: Any, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if number <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return number


def observation_digest(value: Mapping[str, Any]) -> str:
    body = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()
