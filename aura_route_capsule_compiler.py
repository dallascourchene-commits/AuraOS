"""Deterministic compiler for Aura Executable Route Capsule manifests.

Compilation resolves repository-relative component references and existing capability
bindings. It never executes component content and never activates a capsule.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Callable

from aura_polysynthetic_intent import PolysyntheticIntentPacket, bind_intent_packet
from aura_route_capsule_registry import (
    LoadedRegistryComponent,
    canonical_json_digest,
    load_registry_component,
    resolve_repository_reference,
)
from aura_route_capsule_types import (
    CompiledRouteCapsule,
    ExecutableRouteCapsule,
    REFERENCE_FIELDS,
)
from aura_vsa_encoding_profile import VSAEncodingProfile, bundle, seeded_hv, vector_digest

ROUTE_CAPSULE_COMPILER_VERSION = "AURA_ROUTE_CAPSULE_COMPILER_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class CapsuleCompileDiagnostic:
    severity: str
    code: str
    message: str
    field_name: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "field_name": self.field_name,
        }


@dataclass
class RouteCapsuleCompileResult:
    ok: bool
    compiled: CompiledRouteCapsule | None
    diagnostics: list[CapsuleCompileDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "version": ROUTE_CAPSULE_COMPILER_VERSION,
            "compiled": self.compiled.to_dict() if self.compiled else None,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_activation": False,
            "automatic_grammar_promotion": False,
        }


def compile_route_capsule(
    path: str | Path,
    *,
    repo_root: str | Path = ".",
    capability_resolver: Callable[[tuple[str, ...]], dict[str, Any]] | None = None,
) -> RouteCapsuleCompileResult:
    diagnostics: list[CapsuleCompileDiagnostic] = []
    try:
        manifest_path, relative_path = resolve_repository_reference(repo_root, str(path), field_name="route_capsule")
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        capsule = ExecutableRouteCapsule.from_dict(payload)
    except Exception as exc:  # noqa: BLE001 - converted to a fail-closed diagnostic
        return _failed("invalid_capsule_manifest", str(exc))

    components: dict[str, LoadedRegistryComponent] = {}
    for field_name in REFERENCE_FIELDS:
        try:
            components[field_name] = load_registry_component(
                repo_root,
                getattr(capsule, field_name),
                field_name=field_name,
            )
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(CapsuleCompileDiagnostic("error", "component_resolution_failed", str(exc), field_name))

    if diagnostics:
        return RouteCapsuleCompileResult(False, None, diagnostics)

    try:
        profile = VSAEncodingProfile.from_dict(components["vsa_profile_ref"].payload)
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(CapsuleCompileDiagnostic("error", "invalid_vsa_profile", str(exc), "vsa_profile_ref"))
        return RouteCapsuleCompileResult(False, None, diagnostics)

    morphology_payload = components["morphology_profile_ref"].payload
    slot_order = tuple(str(item) for item in morphology_payload.get("slot_order", []))
    if slot_order != ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"):
        diagnostics.append(CapsuleCompileDiagnostic(
            "error", "invalid_morphology_slot_order",
            "morphology profile must preserve DIR, ASP, CLASS, SUBJ, VOICE, STEM",
            "morphology_profile_ref",
        ))
        return RouteCapsuleCompileResult(False, None, diagnostics)

    try:
        capsule_intent = PolysyntheticIntentPacket.from_slots(
            capsule.morphology_signature, adjuncts=capsule.routing_adjuncts
        )
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(CapsuleCompileDiagnostic(
            "error", "invalid_capsule_morphology_signature", str(exc), "morphology_signature"
        ))
        return RouteCapsuleCompileResult(False, None, diagnostics)

    tool_payload = components["tool_bundle_ref"].payload
    declared = tuple(str(item) for item in tool_payload.get("requested_capabilities", []) or [])
    if tuple(capsule.requested_capabilities) != declared:
        diagnostics.append(CapsuleCompileDiagnostic(
            "error", "capability_bundle_mismatch",
            "capsule requested_capabilities must exactly match the tool bundle",
            "tool_bundle_ref",
        ))
        return RouteCapsuleCompileResult(False, None, diagnostics)

    resolver = capability_resolver or _default_capability_resolver(repo_root)
    resolution = resolver(tuple(capsule.requested_capabilities))
    if not resolution.get("ok"):
        diagnostics.append(CapsuleCompileDiagnostic(
            "error", "unbound_capability_bundle",
            json.dumps(resolution.get("denials") or resolution, sort_keys=True, default=str),
            "tool_bundle_ref",
        ))
        return RouteCapsuleCompileResult(False, None, diagnostics)
    bindings = tuple(dict(item) for item in resolution.get("bindings", []))

    morphology_bound = bind_intent_packet(capsule_intent, profile)
    route_signature = bundle([
        morphology_bound.vector,
        seeded_hv(f"CAPSULE::{capsule.capsule_id}", profile),
        seeded_hv(f"TRANSITION::{capsule.transition_id}", profile),
        *(
            seeded_hv(f"COMPONENT::{field_name}::{component.component_id}::{component.digest}", profile)
            for field_name, component in sorted(components.items())
        ),
    ])
    compiled = CompiledRouteCapsule(
        capsule=capsule,
        capsule_manifest_digest=canonical_json_digest(payload),
        component_digests={field_name: item.digest for field_name, item in components.items()},
        component_ids={field_name: item.component_id for field_name, item in components.items()},
        capability_bindings=bindings,
        morphology_vector_digest=morphology_bound.vector_digest,
        route_signature_digest=vector_digest(route_signature),
        vsa_profile_digest=profile.digest(),
        source_path=relative_path,
    )
    return RouteCapsuleCompileResult(True, compiled, diagnostics)


def compile_intent_for_capsule(
    packet: PolysyntheticIntentPacket,
    compiled: CompiledRouteCapsule,
    *,
    repo_root: str | Path = ".",
):
    """Bind an intent with the capsule's pinned profile; still advisory only."""
    component = load_registry_component(
        repo_root,
        compiled.capsule.vsa_profile_ref,
        field_name="vsa_profile_ref",
    )
    if component.digest != compiled.component_digests["vsa_profile_ref"]:
        raise ValueError("compiled capsule VSA profile digest no longer matches repository content")
    profile = VSAEncodingProfile.from_dict(component.payload)
    return bind_intent_packet(packet, profile)


def _default_capability_resolver(repo_root: str | Path):
    def resolve(capabilities: tuple[str, ...]) -> dict[str, Any]:
        from aura_capability_binding import resolve_capability_bindings
        return resolve_capability_bindings(capabilities, repo_root=repo_root)
    return resolve


def _failed(code: str, message: str) -> RouteCapsuleCompileResult:
    return RouteCapsuleCompileResult(False, None, [CapsuleCompileDiagnostic("error", code, message)])
