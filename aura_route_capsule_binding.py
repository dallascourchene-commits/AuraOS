"""Advisory VSA ranking for already-admissible Aura route capsules.

This module cannot admit a capsule. Callers must provide the exact set of capsule
IDs that survived hard guards, policy, evidence, lifecycle, and lease checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aura_polysynthetic_intent import BoundIntentRepresentation, PolysyntheticIntentPacket, bind_intent_packet
from aura_route_capsule_types import CompiledRouteCapsule
from aura_vsa_encoding_profile import VSAEncodingProfile, cosine
from aura_route_capsule_registry import load_registry_component

ROUTE_CAPSULE_BINDING_VERSION = "AURA_ROUTE_CAPSULE_BINDING_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class CapsuleResonance:
    capsule_id: str
    transition_id: str
    resonance: float
    admissible: bool = True
    routing_authority: str = "advisory_after_hard_guards"

    def to_dict(self) -> dict:
        return {
            "capsule_id": self.capsule_id,
            "transition_id": self.transition_id,
            "resonance": self.resonance,
            "admissible": self.admissible,
            "routing_authority": self.routing_authority,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def rank_admissible_capsules(
    intent: BoundIntentRepresentation,
    capsules: Iterable[CompiledRouteCapsule],
    *,
    admissible_capsule_ids: set[str] | frozenset[str],
    repo_root: str | Path = ".",
) -> list[CapsuleResonance]:
    """Score only caller-provided admissible capsules; never expand that set."""
    allowed = frozenset(str(item) for item in admissible_capsule_ids)
    if not allowed:
        return []
    scored: list[CapsuleResonance] = []
    for compiled in capsules:
        capsule_id = compiled.capsule.capsule_id
        if capsule_id not in allowed:
            continue
        profile_component = load_registry_component(
            repo_root,
            compiled.capsule.vsa_profile_ref,
            field_name="vsa_profile_ref",
        )
        if profile_component.digest != compiled.component_digests.get("vsa_profile_ref"):
            raise ValueError(f"stale compiled capsule profile digest: {capsule_id}")
        profile = VSAEncodingProfile.from_dict(profile_component.payload)
        if intent.vsa_profile_digest != profile.digest():
            raise ValueError("intent and capsule use different VSA profiles")
        capsule_packet = PolysyntheticIntentPacket.from_slots(
            compiled.capsule.morphology_signature,
            adjuncts=compiled.capsule.routing_adjuncts,
        )
        capsule_bound = bind_intent_packet(capsule_packet, profile)
        if capsule_bound.vector_digest != compiled.morphology_vector_digest:
            raise ValueError(f"stale compiled morphology signature: {capsule_id}")
        scored.append(CapsuleResonance(
            capsule_id=capsule_id,
            transition_id=compiled.capsule.transition_id,
            resonance=round(cosine(intent.vector, capsule_bound.vector), 9),
        ))
    return sorted(scored, key=lambda item: (-item.resonance, item.capsule_id))
