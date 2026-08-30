"""Mission-agnostic TriadicArtifactRebaseV1 coordination contract.

Validates artifact-level Triadic Process lineage used to derive a new Arena
objective from exactly two sibling-agent artifacts plus the synthesizing worker.
Coordination-only: it never claims cognition ran, grants effect authority, or
starts runtime/provider work.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterable, Sequence

SCHEMA = "TriadicArtifactRebaseV1"
_EFFECT_RANK = {"D0": 0, "D1": 1, "D2": 2, "D3": 3}
_EVIDENCE_RANK = {
    "RUNTIME_RECEIPT": 0,
    "TEST_RECEIPT": 1,
    "SOURCE_EVIDENCE": 2,
    "ADVERSARIAL_ORACLE": 3,
    "PROTOCOL": 4,
    "DERIVED": 5,
    "HYPOTHESIS": 6,
    "UNKNOWN": 7,
}


class TriadicRebaseError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TriadicRebaseError(code)
    return value.strip()


def _texts(values: Sequence[str], code: str, *, require_nonempty: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise TriadicRebaseError(code)
    out = tuple(_text(v, code) for v in values)
    if require_nonempty and not out:
        raise TriadicRebaseError(code)
    return out


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class ArtifactAnchor:
    artifact_ref: str
    agent_id: str
    role: str
    evidence_class: str
    currentness: str
    content_digest: str
    evidence_ref: str
    dependency_relevance: int = 0
    superseded: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_ref", _text(self.artifact_ref, "ANCHOR_REF_REQUIRED"))
        object.__setattr__(self, "agent_id", _text(self.agent_id, "ANCHOR_AGENT_REQUIRED"))
        object.__setattr__(self, "role", _text(self.role, "ANCHOR_ROLE_REQUIRED"))
        object.__setattr__(
            self,
            "evidence_class",
            _text(self.evidence_class, "ANCHOR_EVIDENCE_CLASS_REQUIRED").upper(),
        )
        object.__setattr__(
            self,
            "currentness",
            _text(self.currentness, "ANCHOR_CURRENTNESS_REQUIRED").upper(),
        )
        digest = _text(self.content_digest, "ANCHOR_CONTENT_DIGEST_REQUIRED").lower()
        if len(digest) < 16 or any(ch not in "0123456789abcdef" for ch in digest):
            raise TriadicRebaseError("ANCHOR_CONTENT_DIGEST_INVALID", self.artifact_ref)
        object.__setattr__(self, "content_digest", digest)
        object.__setattr__(
            self,
            "evidence_ref",
            _text(self.evidence_ref, "ANCHOR_EVIDENCE_REF_REQUIRED"),
        )
        if (
            isinstance(self.dependency_relevance, bool)
            or not isinstance(self.dependency_relevance, int)
            or self.dependency_relevance < 0
        ):
            raise TriadicRebaseError("ANCHOR_RELEVANCE_INVALID")


@dataclass(frozen=True)
class TriadicRebasePacket:
    schema: str
    triad_id: str
    packet_digest: str
    mission_ref: str
    purpose_ref: str
    currentness_basis: str
    synthesizing_agent_id: str
    anchors: tuple[ArtifactAnchor, ArtifactAnchor]
    agreements: tuple[str, ...]
    tensions: tuple[str, ...]
    unknowns: tuple[str, ...]
    derived_objective: str
    why_material: str
    dependencies: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    inherited_effect_ceiling: str
    required_effect_ceiling: str
    cost_ceiling: float | None
    expected_output: str
    acceptance: tuple[str, ...]
    reopen_conditions: tuple[str, ...]
    disposition: str
    provisional_reasons: tuple[str, ...]
    observed_at: str | None
    produced_artifact_ref: str | None
    synthesis_execution_proven: bool = False
    runtime_execution_proven: bool = False
    effect_authorized: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def select_two_sibling_anchors(
    candidates: Iterable[ArtifactAnchor],
    *,
    synthesizing_agent_id: str,
) -> tuple[ArtifactAnchor, ArtifactAnchor]:
    """Deterministically nominate two current non-self sibling anchors.

    Nomination is coordination only; it does not claim a cognitive worker
    inspected or synthesized the artifacts.
    """
    synth = _text(synthesizing_agent_id, "SYNTHESIZER_REQUIRED")
    eligible = [
        a
        for a in candidates
        if a.agent_id != synth and a.currentness == "CURRENT" and not a.superseded
    ]
    if len(eligible) < 2:
        raise TriadicRebaseError("TRIAD_ANCHOR_INSUFFICIENT")

    eligible.sort(
        key=lambda a: (
            -a.dependency_relevance,
            _EVIDENCE_RANK.get(a.evidence_class, 99),
            a.agent_id,
            a.role,
            a.artifact_ref,
        )
    )
    first = eligible[0]
    rest = sorted(
        eligible[1:],
        key=lambda a: (
            a.agent_id == first.agent_id,
            a.role == first.role,
            -a.dependency_relevance,
            _EVIDENCE_RANK.get(a.evidence_class, 99),
            a.agent_id,
            a.artifact_ref,
        ),
    )
    return first, rest[0]


def compile_triadic_rebase(
    *,
    mission_ref: str,
    purpose_ref: str,
    currentness_basis: str,
    synthesizing_agent_id: str,
    anchors: Sequence[ArtifactAnchor],
    agreements: Sequence[str],
    tensions: Sequence[str],
    unknowns: Sequence[str],
    derived_objective: str,
    why_material: str,
    dependencies: Sequence[str],
    required_capabilities: Sequence[str],
    inherited_effect_ceiling: str,
    required_effect_ceiling: str,
    cost_ceiling: float | None,
    expected_output: str,
    acceptance: Sequence[str],
    reopen_conditions: Sequence[str],
    observed_at: str | None = None,
    produced_artifact_ref: str | None = None,
    allow_provisional: bool = False,
    same_agent_exception_ref: str | None = None,
) -> TriadicRebasePacket:
    mission = _text(mission_ref, "MISSION_REF_REQUIRED")
    purpose = _text(purpose_ref, "PURPOSE_REF_REQUIRED")
    currentness = _text(currentness_basis, "CURRENTNESS_BASIS_REQUIRED")
    synth = _text(synthesizing_agent_id, "SYNTHESIZER_REQUIRED")
    if len(anchors) != 2:
        raise TriadicRebaseError("TRIAD_REQUIRES_EXACTLY_TWO_SIBLING_ANCHORS")
    a, b = anchors
    if a.artifact_ref == b.artifact_ref:
        raise TriadicRebaseError("TRIAD_ANCHOR_DUPLICATE_ARTIFACT")
    if a.agent_id == synth or b.agent_id == synth:
        raise TriadicRebaseError("TRIAD_SELF_AUTHORED_ANCHOR_REJECTED")
    if a.agent_id == b.agent_id and not (
        same_agent_exception_ref and same_agent_exception_ref.strip()
    ):
        raise TriadicRebaseError("TRIAD_DISTINCT_AGENT_ANCHOR_REQUIRED")

    provisional: list[str] = []
    for anchor in (a, b):
        if anchor.currentness != "CURRENT" or anchor.superseded:
            provisional.append(f"ANCHOR_NOT_CURRENT:{anchor.artifact_ref}")
    if provisional and not allow_provisional:
        raise TriadicRebaseError(
            "TRIAD_ANCHOR_REBASE_REQUIRED",
            ",".join(provisional),
        )

    agreements_t = _texts(agreements, "AGREEMENT_REQUIRED", require_nonempty=True)
    tensions_t = _texts(tensions, "TENSION_REQUIRED", require_nonempty=True)
    unknowns_t = _texts(unknowns, "UNKNOWN_INVALID")
    objective = _text(derived_objective, "DERIVED_OBJECTIVE_REQUIRED")
    why = _text(why_material, "WHY_MATERIAL_REQUIRED")
    deps = _texts(dependencies, "DEPENDENCY_INVALID")
    caps = _texts(required_capabilities, "CAPABILITY_INVALID")
    expected = _text(expected_output, "EXPECTED_OUTPUT_REQUIRED")
    acceptance_t = _texts(acceptance, "ACCEPTANCE_REQUIRED", require_nonempty=True)
    reopen_t = _texts(reopen_conditions, "REOPEN_REQUIRED", require_nonempty=True)

    parent_effect = _text(
        inherited_effect_ceiling,
        "INHERITED_EFFECT_CEILING_REQUIRED",
    ).upper()
    requested_effect = _text(
        required_effect_ceiling,
        "REQUIRED_EFFECT_CEILING_REQUIRED",
    ).upper()
    if parent_effect not in _EFFECT_RANK or requested_effect not in _EFFECT_RANK:
        raise TriadicRebaseError("EFFECT_CEILING_INVALID")
    if _EFFECT_RANK[requested_effect] > _EFFECT_RANK[parent_effect]:
        raise TriadicRebaseError("TRIADIC_REBASE_CANNOT_WIDEN_EFFECT_AUTHORITY")

    if cost_ceiling is not None:
        if isinstance(cost_ceiling, bool) or not isinstance(cost_ceiling, (int, float)):
            raise TriadicRebaseError("COST_CEILING_INVALID")
        if not math.isfinite(float(cost_ceiling)) or float(cost_ceiling) < 0:
            raise TriadicRebaseError("COST_CEILING_INVALID")
        cost_value: float | None = float(cost_ceiling)
    else:
        cost_value = None

    basis = {
        "schema": SCHEMA,
        "mission_ref": mission,
        "purpose_ref": purpose,
        "currentness_basis": currentness,
        "synthesizing_agent_id": synth,
        "anchors": [
            {
                "artifact_ref": x.artifact_ref,
                "agent_id": x.agent_id,
                "role": x.role,
                "content_digest": x.content_digest,
                "evidence_ref": x.evidence_ref,
            }
            for x in (a, b)
        ],
    }
    triad_id = hashlib.sha256(
        b"TRIADIC_ARTIFACT_REBASE_BASIS_V1\0" + _canonical(basis)
    ).hexdigest()[:32]

    disposition = (
        "PROVISIONAL_REBASE_REQUIRED"
        if provisional
        else "READY_FOR_OBJECTIVE_CLAIM"
    )
    packet_body = {
        **basis,
        "triad_id": triad_id,
        "agreements": agreements_t,
        "tensions": tensions_t,
        "unknowns": unknowns_t,
        "derived_objective": objective,
        "why_material": why,
        "dependencies": deps,
        "required_capabilities": caps,
        "inherited_effect_ceiling": parent_effect,
        "required_effect_ceiling": requested_effect,
        "cost_ceiling": cost_value,
        "expected_output": expected,
        "acceptance": acceptance_t,
        "reopen_conditions": reopen_t,
        "disposition": disposition,
        "provisional_reasons": tuple(provisional),
        "produced_artifact_ref": produced_artifact_ref,
        "synthesis_execution_proven": False,
        "runtime_execution_proven": False,
        "effect_authorized": False,
    }
    # Observation time is deliberately excluded from logical identity/digest.
    packet_digest = hashlib.sha256(
        b"TRIADIC_ARTIFACT_REBASE_PACKET_V1\0" + _canonical(packet_body)
    ).hexdigest()

    return TriadicRebasePacket(
        schema=SCHEMA,
        triad_id=triad_id,
        packet_digest=packet_digest,
        mission_ref=mission,
        purpose_ref=purpose,
        currentness_basis=currentness,
        synthesizing_agent_id=synth,
        anchors=(a, b),
        agreements=agreements_t,
        tensions=tensions_t,
        unknowns=unknowns_t,
        derived_objective=objective,
        why_material=why,
        dependencies=deps,
        required_capabilities=caps,
        inherited_effect_ceiling=parent_effect,
        required_effect_ceiling=requested_effect,
        cost_ceiling=cost_value,
        expected_output=expected,
        acceptance=acceptance_t,
        reopen_conditions=reopen_t,
        disposition=disposition,
        provisional_reasons=tuple(provisional),
        observed_at=observed_at,
        produced_artifact_ref=produced_artifact_ref,
    )
