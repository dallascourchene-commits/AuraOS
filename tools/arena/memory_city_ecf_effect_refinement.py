from __future__ import annotations

"""O10R1: ECF-gate Memory City effect-obligation refinement evidence.

This is a D0/nonpromoting adapter. It removes caller self-attestation from the
O8 refinement seam by requiring each semantic effect-obligation observation to
resolve against the current ECF admission cut before it may become an O8
projection. The adapter does *not* authenticate the upstream ECF owner or mint
an admitted-witness set; ``ECFAdmissionIndex.admitted_witness_roots`` remains an
explicit trust input owned by the upstream ECF plane.

Keeper:
    CallerBoolean != ECFAdmissionResult != UpstreamECFOwnerAuthentication
"""

from dataclasses import dataclass
from hashlib import sha256
import json

from memory_city_consequence_refinement import (
    D0,
    EffectIntent,
    EffectObligationProjection,
    EffectRefinementPlan,
    compile_effect_refinement,
)
from memory_city_ecf_adapter import ECFAdmissionIndex

SCHEMA = "AURA-MEMORY-CITY-ECF-EFFECT-REFINEMENT-v1"
EVIDENCE_SCHEMA = "AURA-MEMORY-CITY-EFFECT-OBLIGATION-EVIDENCE-v1"
OWNER_TRUST_BOUNDARY = "UPSTREAM_ECF_OWNER_ADMITTED_WITNESS_ROOTS_REQUIRED"


def digest(value) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _root(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value.lower() != value
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError(f"{field} must be lowercase sha256")
    return value


@dataclass(frozen=True)
class EffectObligationObservation:
    read_binding_root: str
    effect_obligation_root: str
    source_observation_root: str
    nuisance_configuration_root: str

    def __post_init__(self) -> None:
        for field in (
            "read_binding_root",
            "effect_obligation_root",
            "source_observation_root",
            "nuisance_configuration_root",
        ):
            _root(getattr(self, field), field)

    def evidence_digest(self, intent: EffectIntent) -> str:
        if not isinstance(intent, EffectIntent):
            raise ValueError("intent must be EffectIntent")
        return digest(
            {
                "schema": EVIDENCE_SCHEMA,
                "read_binding_root": self.read_binding_root,
                "effect_obligation_root": self.effect_obligation_root,
                "intent_binding_root": intent.binding_root,
                "source_observation_root": self.source_observation_root,
            }
        )


@dataclass(frozen=True)
class ECFEffectRefinement:
    plan: EffectRefinementPlan
    evidence_set_root: str
    admitted_witness_roots: tuple[str, ...]
    per_binding_status: tuple[tuple[str, str], ...]
    ecf_coherent_cut_root: str
    owner_trust_boundary: str = OWNER_TRUST_BOUNDARY
    upstream_owner_authentication_claimed: bool = False
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.plan, EffectRefinementPlan):
            raise ValueError("plan must be EffectRefinementPlan")
        _root(self.evidence_set_root, "evidence_set_root")
        _root(self.ecf_coherent_cut_root, "ecf_coherent_cut_root")
        for root in self.admitted_witness_roots:
            _root(root, "admitted_witness_root")
        if self.owner_trust_boundary != OWNER_TRUST_BOUNDARY:
            raise ValueError("owner trust boundary must remain explicit")
        if self.upstream_owner_authentication_claimed:
            raise ValueError("D0 adapter cannot claim upstream ECF authentication")
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("ECF refinement cannot mint authority")


def compile_ecf_effect_refinement(
    observations: tuple[EffectObligationObservation, ...],
    cert,
    intent: EffectIntent,
    ecf_index: ECFAdmissionIndex,
) -> ECFEffectRefinement:
    """Compile O8 refinement only from current ECF-admitted semantic evidence.

    The caller may supply observations, but may not supply the old O8
    ``obligation_authenticated`` / ``observation_current`` booleans. Those two
    facts are derived solely from ``ECFAdmissionIndex.resolve``.
    """
    if not isinstance(intent, EffectIntent):
        raise ValueError("intent must be EffectIntent")
    if not isinstance(ecf_index, ECFAdmissionIndex):
        raise ValueError("ecf_index must be ECFAdmissionIndex")
    if any(not isinstance(obs, EffectObligationObservation) for obs in observations):
        raise ValueError("observations must be EffectObligationObservation")

    scope = ecf_index.current_cut.evidence_scope
    projections: list[EffectObligationProjection] = []
    statuses: list[tuple[str, str]] = []
    admitted: list[str] = []

    for obs in observations:
        evidence_digest = obs.evidence_digest(intent)
        admission = ecf_index.resolve(evidence_digest, scope=scope)
        statuses.append((obs.read_binding_root, admission.status))
        admitted_here = admission.status == "ADMITTED_EVIDENCE_D0"
        if admitted_here:
            admitted.append(admission.witness_root)
        projections.append(
            EffectObligationProjection(
                obs.read_binding_root,
                obs.effect_obligation_root,
                admission.witness_root if admitted_here else None,
                admitted_here,
                admitted_here,
                obs.nuisance_configuration_root,
            )
        )

    plan = compile_effect_refinement(tuple(projections), cert, intent)
    cut = ecf_index.current_cut
    canonical_statuses = tuple(sorted(statuses))
    canonical_admitted = tuple(sorted(admitted))
    evidence_set_root = digest(
        {
            "schema": SCHEMA,
            "kind": "ecf_effect_refinement",
            "read_certificate_root": plan.read_certificate_root,
            "parent_read_root": plan.parent_read_root,
            "intent_binding_root": intent.binding_root,
            "plan_root": plan.plan_root,
            "ecf_jurisdiction_id": cut.jurisdiction_id,
            "ecf_jurisdiction_generation": cut.jurisdiction_generation,
            "ecf_producer_registry_root": cut.producer_registry_root,
            "ecf_producer_id": cut.producer_id,
            "ecf_producer_incarnation": cut.producer_incarnation,
            "ecf_scope": cut.evidence_scope,
            "ecf_coherent_cut_root": cut.coherent_cut_root,
            "admitted_witness_roots": canonical_admitted,
            "per_binding_status": canonical_statuses,
            "owner_trust_boundary": OWNER_TRUST_BOUNDARY,
            "upstream_owner_authentication_claimed": False,
            "authority": D0,
            "effect_authority": False,
            "gate10": False,
        }
    )
    return ECFEffectRefinement(
        plan,
        evidence_set_root,
        canonical_admitted,
        canonical_statuses,
        cut.coherent_cut_root,
    )
