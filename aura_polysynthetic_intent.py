"""Canonical six-slot polysynthetic intent packets and deterministic VSA binding.

The six slots are an Aura engineering contract inspired by morphotactic ordering.
They are not asserted as a universal linguistic model of polysynthetic languages.
Adjunct routing features remain orthogonal so risk, cost, and model policy do not
pollute the core slot sequence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from aura_vsa_encoding_profile import (
    DEFAULT_COMPLEX_PHASOR_V1,
    VSAEncodingProfile,
    bind,
    bundle,
    permute,
    seeded_hv,
    vector_digest,
)

POLYSYNTHETIC_INTENT_VERSION = "AURA_POLYSYNTHETIC_INTENT_V1"
BOUND_INTENT_VERSION = "AURA_BOUND_INTENT_REPRESENTATION_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

SLOT_ORDER = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")
SLOT_ALIASES = {
    "SPATIAL": "DIR",
    "DIRECTION": "DIR",
    "ASPECT": "ASP",
    "CLASSIFIER": "CLASS",
    "SUBJECT": "SUBJ",
}
ALLOWED_ADJUNCTS = frozenset({
    "risk", "grounding", "tests", "quality", "cost", "context_class",
    "model_class", "resource_budget", "thermal_class", "jurisdiction",
})


def canonicalize_slot_name(name: str) -> str:
    upper = str(name or "").strip().upper()
    return SLOT_ALIASES.get(upper, upper)


def _canonical_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


@dataclass(frozen=True)
class PolysyntheticIntentPacket:
    dir: str
    asp: str
    class_: str
    subj: str
    voice: str
    stem: str
    adjuncts: dict[str, str] = field(default_factory=dict)
    objective_digest: str = ""

    @classmethod
    def from_slots(
        cls,
        slots: Mapping[str, Any],
        *,
        adjuncts: Mapping[str, Any] | None = None,
        objective: str = "",
    ) -> "PolysyntheticIntentPacket":
        if not isinstance(slots, Mapping):
            raise TypeError("slots must be a mapping")
        normalized: dict[str, str] = {}
        for raw_name, raw_value in slots.items():
            name = canonicalize_slot_name(raw_name)
            if name not in SLOT_ORDER:
                raise ValueError(f"unknown core slot: {raw_name}")
            if name in normalized:
                raise ValueError(f"duplicate core slot after alias resolution: {name}")
            value = _canonical_text(raw_value)
            if not value:
                raise ValueError(f"slot {name} requires a nonempty filler")
            normalized[name] = value
        missing = [name for name in SLOT_ORDER if name not in normalized]
        if missing:
            raise ValueError(f"missing core slots: {', '.join(missing)}")

        canonical_adjuncts: dict[str, str] = {}
        for raw_name, raw_value in (adjuncts or {}).items():
            name = str(raw_name or "").strip().casefold()
            if name not in ALLOWED_ADJUNCTS:
                raise ValueError(f"unsupported adjunct feature: {raw_name}")
            value = _canonical_text(raw_value)
            if value:
                canonical_adjuncts[name] = value
        objective_digest = hashlib.blake2b(_canonical_text(objective).encode("utf-8"), digest_size=20).hexdigest() if objective else ""
        return cls(
            dir=normalized["DIR"], asp=normalized["ASP"], class_=normalized["CLASS"],
            subj=normalized["SUBJ"], voice=normalized["VOICE"], stem=normalized["STEM"],
            adjuncts=dict(sorted(canonical_adjuncts.items())), objective_digest=objective_digest,
        )

    @classmethod
    def from_symbol_sequence(
        cls,
        symbols: Sequence[Any],
        *,
        adjuncts: Mapping[str, Any] | None = None,
        objective: str = "",
    ) -> "PolysyntheticIntentPacket":
        if len(symbols) != len(SLOT_ORDER):
            raise ValueError("symbol sequence must contain exactly six fillers")
        return cls.from_slots(dict(zip(SLOT_ORDER, symbols)), adjuncts=adjuncts, objective=objective)

    def slot_items(self) -> tuple[tuple[str, str], ...]:
        return (
            ("DIR", self.dir), ("ASP", self.asp), ("CLASS", self.class_),
            ("SUBJ", self.subj), ("VOICE", self.voice), ("STEM", self.stem),
        )

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "schema_version": POLYSYNTHETIC_INTENT_VERSION,
            "slots": {name: value for name, value in self.slot_items()},
            "adjuncts": dict(sorted(self.adjuncts.items())),
            "objective_digest": self.objective_digest,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def digest(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


@dataclass(frozen=True)
class BoundIntentRepresentation:
    packet_digest: str
    vsa_profile_digest: str
    vector_digest: str
    slot_vector_digests: tuple[str, ...]
    adjunct_vector_digests: tuple[str, ...]
    vector: np.ndarray = field(repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": BOUND_INTENT_VERSION,
            "packet_digest": self.packet_digest,
            "vsa_profile_digest": self.vsa_profile_digest,
            "vector_digest": self.vector_digest,
            "slot_vector_digests": list(self.slot_vector_digests),
            "adjunct_vector_digests": list(self.adjunct_vector_digests),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "routing_authority": "advisory_after_hard_guards",
        }


def bind_intent_packet(
    packet: PolysyntheticIntentPacket,
    profile: VSAEncodingProfile = DEFAULT_COMPLEX_PHASOR_V1,
) -> BoundIntentRepresentation:
    profile.validate()
    slot_vectors: list[np.ndarray] = []
    for index, (slot_name, filler) in enumerate(packet.slot_items()):
        role = seeded_hv(f"SLOT::{slot_name}", profile)
        value = seeded_hv(f"FILLER::{slot_name}::{filler}", profile)
        if slot_name in {"ASP", "STEM"}:
            value = permute(value, steps=profile.permutation_shift * (index + 1), profile=profile)
        slot_vectors.append(bind(role, value))

    adjunct_vectors: list[np.ndarray] = []
    for name, filler in sorted(packet.adjuncts.items()):
        role = seeded_hv(f"ADJUNCT::{name}", profile)
        value = seeded_hv(f"ADJUNCT_FILLER::{name}::{filler}", profile)
        adjunct_vectors.append(bind(role, value))

    combined = bundle([*slot_vectors, *adjunct_vectors] if adjunct_vectors else slot_vectors)
    return BoundIntentRepresentation(
        packet_digest=packet.digest(),
        vsa_profile_digest=profile.digest(),
        vector_digest=vector_digest(combined),
        slot_vector_digests=tuple(vector_digest(item) for item in slot_vectors),
        adjunct_vector_digests=tuple(vector_digest(item) for item in adjunct_vectors),
        vector=combined,
    )
