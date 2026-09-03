from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

SCHEMA = "AuraConstitutionalInvariantCheckerV1"

EVIDENCE_DOMAINS = frozenset({
    "SOURCE_SECURITY", "RUNTIME_CAPABILITY", "PHYSICAL_OBSERVATION",
    "CORRECTNESS", "CAUSAL_BENEFIT", "PROVENANCE", "TIMING", "MEMORY",
    "ENERGY", "OWNER_AUTHORITY", "LEGAL_COMMUNITY_DISPOSITION", "HUMAN_GATE",
})
COLD_STATES = frozenset({
    "HOLD_EXTERNAL", "COLD_ARCHIVE", "SUPERSEDED_BUT_PROVENANCE_RETAINED",
    "RETIRED_NO_REOPEN_WITHOUT_INVALIDATOR",
})


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class EvidencePayment:
    debt_domain: str
    leaf_domain: str
    leaf_digest: str


@dataclass(frozen=True)
class ProjectionClaim:
    source_owner_authority: bool
    source_effect_authority: bool
    projected_owner_authority: bool
    projected_effect_authority: bool


@dataclass(frozen=True)
class SourceTransition:
    old_provider_generation: str
    new_provider_generation: str
    old_semantic_root: str
    new_semantic_root: str
    semantic_movement_claimed: bool


@dataclass(frozen=True)
class SupersessionEdge:
    older: str
    newer: str


@dataclass(frozen=True)
class WakeClaim:
    lifecycle_state: str
    requested_wake: bool
    declared_invalidators: tuple[str, ...]
    observed_invalidators: tuple[str, ...]


@dataclass(frozen=True)
class CrossJurisdictionClaim:
    source_owner_authority: bool
    source_effect_authority: bool
    destination_owner_authority: bool
    destination_effect_authority: bool
    destination_local_revalidation: bool


@dataclass(frozen=True)
class Gate10Claim:
    crossed: bool
    actor_kind: str | None


@dataclass(frozen=True)
class DependencyClaim:
    completeness: str
    selective_revalidation: bool
    owner_or_physical_effect: bool
    owner_authority_available: bool
    disposition: str


@dataclass(frozen=True)
class ConstitutionalSnapshot:
    evidence_payments: tuple[EvidencePayment, ...] = ()
    projections: tuple[ProjectionClaim, ...] = ()
    source_transitions: tuple[SourceTransition, ...] = ()
    supersession_edges: tuple[SupersessionEdge, ...] = ()
    wake_claims: tuple[WakeClaim, ...] = ()
    cross_jurisdiction_claims: tuple[CrossJurisdictionClaim, ...] = ()
    gate10_claims: tuple[Gate10Claim, ...] = ()
    dependency_claims: tuple[DependencyClaim, ...] = ()


@dataclass(frozen=True)
class Violation:
    law_id: str
    detail: str
    witness_digest: str


@dataclass(frozen=True)
class VerificationReceipt:
    schema: str
    lawful: bool
    checked_laws: tuple[str, ...]
    violations: tuple[Violation, ...]
    snapshot_digest: str
    effect_authority: bool = False
    gate10: bool = False


LAWS = (
    "CI-01-EVIDENCE-DOMAIN-NONCOMPENSATION",
    "CI-02-PROJECTION-NO-AUTHORITY-WIDENING",
    "CI-03-PROVIDER-MOVEMENT-NO-SEMANTIC-MINTING",
    "CI-04-SUPERSESSION-DAG-ACYCLIC",
    "CI-05-COLD-WAKE-REQUIRES-MATCHING-INVALIDATOR",
    "CI-06-CROSS-JURISDICTION-NO-AUTHORITY-WIDENING",
    "CI-07-GATE10-ACTOR-HUMAN",
    "CI-08-UNKNOWN-DEPENDENCY-COMPLETENESS-WIDENS-REVALIDATION",
)


class ConstitutionalInvariantChecker:
    """T2 structural/symbolic checker over normalized observations.

    It never mints truth, currentness, owner/effect authority, or Gate10.
    """

    def check(self, snapshot: ConstitutionalSnapshot) -> VerificationReceipt:
        violations: list[Violation] = []
        violations.extend(self._evidence_domain(snapshot.evidence_payments))
        violations.extend(self._projection(snapshot.projections))
        violations.extend(self._source_transition(snapshot.source_transitions))
        violations.extend(self._supersession(snapshot.supersession_edges))
        violations.extend(self._wake(snapshot.wake_claims))
        violations.extend(self._cross_jurisdiction(snapshot.cross_jurisdiction_claims))
        violations.extend(self._gate10(snapshot.gate10_claims))
        violations.extend(self._dependency(snapshot.dependency_claims))
        return VerificationReceipt(
            SCHEMA, not violations, LAWS, tuple(violations), digest(asdict(snapshot))
        )

    def assert_lawful(self, snapshot: ConstitutionalSnapshot) -> VerificationReceipt:
        receipt = self.check(snapshot)
        if not receipt.lawful:
            raise ValueError("CONSTITUTIONAL_VIOLATION:" + ",".join(v.law_id for v in receipt.violations))
        return receipt

    @staticmethod
    def _v(law_id: str, detail: str, witness: object) -> Violation:
        return Violation(law_id, detail, digest(witness))

    def _evidence_domain(self, rows: Sequence[EvidencePayment]) -> list[Violation]:
        out: list[Violation] = []
        for row in rows:
            if row.debt_domain not in EVIDENCE_DOMAINS or row.leaf_domain not in EVIDENCE_DOMAINS:
                out.append(self._v(LAWS[0], "UNKNOWN_EVIDENCE_DOMAIN", asdict(row)))
            elif row.debt_domain != row.leaf_domain:
                out.append(self._v(LAWS[0], "CROSS_DOMAIN_EVIDENCE_PAYMENT", asdict(row)))
        return out

    def _projection(self, rows: Sequence[ProjectionClaim]) -> list[Violation]:
        out: list[Violation] = []
        for row in rows:
            if row.projected_owner_authority and not row.source_owner_authority:
                out.append(self._v(LAWS[1], "PROJECTION_MINTED_OWNER_AUTHORITY", asdict(row)))
            if row.projected_effect_authority and not row.source_effect_authority:
                out.append(self._v(LAWS[1], "PROJECTION_MINTED_EFFECT_AUTHORITY", asdict(row)))
        return out

    def _source_transition(self, rows: Sequence[SourceTransition]) -> list[Violation]:
        out: list[Violation] = []
        for row in rows:
            semantic_changed = row.old_semantic_root != row.new_semantic_root
            provider_changed = row.old_provider_generation != row.new_provider_generation
            if row.semantic_movement_claimed and not semantic_changed:
                detail = "PROVIDER_ONLY_MOVEMENT_MINTED_SEMANTIC_MOVEMENT" if provider_changed else "NO_DELTA_MINTED_SEMANTIC_MOVEMENT"
                out.append(self._v(LAWS[2], detail, asdict(row)))
        return out

    def _supersession(self, edges: Sequence[SupersessionEdge]) -> list[Violation]:
        adjacency: dict[str, set[str]] = {}
        nodes: set[str] = set()
        for edge in edges:
            if not edge.older or not edge.newer:
                return [self._v(LAWS[3], "EMPTY_SUPERSESSION_NODE", asdict(edge))]
            adjacency.setdefault(edge.older, set()).add(edge.newer)
            nodes.update((edge.older, edge.newer))
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for child in adjacency.get(node, ()):
                if dfs(child):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        for node in sorted(nodes):
            if dfs(node):
                return [self._v(LAWS[3], "SUPERSESSION_CYCLE", sorted((e.older, e.newer) for e in edges))]
        return []

    def _wake(self, rows: Sequence[WakeClaim]) -> list[Violation]:
        out: list[Violation] = []
        for row in rows:
            if row.lifecycle_state in COLD_STATES and row.requested_wake:
                if not (set(row.declared_invalidators) & set(row.observed_invalidators)):
                    out.append(self._v(LAWS[4], "COLD_WORK_SELF_WAKE_OR_UNMATCHED_INVALIDATOR", asdict(row)))
        return out

    def _cross_jurisdiction(self, rows: Sequence[CrossJurisdictionClaim]) -> list[Violation]:
        out: list[Violation] = []
        for row in rows:
            if row.destination_owner_authority and not row.source_owner_authority:
                out.append(self._v(LAWS[5], "CROSS_CITY_MINTED_OWNER_AUTHORITY", asdict(row)))
            if row.destination_effect_authority and not row.source_effect_authority:
                out.append(self._v(LAWS[5], "CROSS_CITY_MINTED_EFFECT_AUTHORITY", asdict(row)))
            if (row.destination_owner_authority or row.destination_effect_authority) and not row.destination_local_revalidation:
                out.append(self._v(LAWS[5], "DESTINATION_AUTHORITY_WITHOUT_LOCAL_REVALIDATION", asdict(row)))
        return out

    def _gate10(self, rows: Sequence[Gate10Claim]) -> list[Violation]:
        return [
            self._v(LAWS[6], "GATE10_NONHUMAN_ACTOR", asdict(row))
            for row in rows if row.crossed and row.actor_kind != "HUMAN"
        ]

    def _dependency(self, rows: Sequence[DependencyClaim]) -> list[Violation]:
        out: list[Violation] = []
        for row in rows:
            if row.completeness not in {"COMPLETE", "UNKNOWN", "PARTIAL"}:
                out.append(self._v(LAWS[7], "UNKNOWN_COMPLETENESS_ENUM", asdict(row)))
                continue
            incomplete = row.completeness != "COMPLETE"
            if incomplete and row.selective_revalidation:
                out.append(self._v(LAWS[7], "INCOMPLETE_DEPENDENCIES_USED_SELECTIVE_REVALIDATION", asdict(row)))
            if incomplete and row.owner_or_physical_effect and not row.owner_authority_available and row.disposition != "HOLD_AUTHORITY":
                out.append(self._v(LAWS[7], "OWNER_OR_PHYSICAL_REVALIDATION_WITHOUT_AUTHORITY_OR_HOLD", asdict(row)))
            if incomplete and not row.owner_or_physical_effect and row.disposition not in {"WIDEN_LOCAL_REVALIDATION", "FULL_LOCAL_REVALIDATION"}:
                out.append(self._v(LAWS[7], "LOCAL_INCOMPLETE_DEPENDENCY_REQUIRES_WIDER_LOCAL_REVALIDATION", asdict(row)))
        return out


def normalize_mapping(data: Mapping[str, object]) -> ConstitutionalSnapshot:
    def rows(name: str, cls):
        value = data.get(name, ())
        if isinstance(value, (str, bytes, Mapping)):
            raise ValueError(f"{name.upper()}_MUST_BE_SEQUENCE")
        return tuple(cls(**dict(item)) for item in value)
    return ConstitutionalSnapshot(
        evidence_payments=rows("evidence_payments", EvidencePayment),
        projections=rows("projections", ProjectionClaim),
        source_transitions=rows("source_transitions", SourceTransition),
        supersession_edges=rows("supersession_edges", SupersessionEdge),
        wake_claims=rows("wake_claims", WakeClaim),
        cross_jurisdiction_claims=rows("cross_jurisdiction_claims", CrossJurisdictionClaim),
        gate10_claims=rows("gate10_claims", Gate10Claim),
        dependency_claims=rows("dependency_claims", DependencyClaim),
    )
