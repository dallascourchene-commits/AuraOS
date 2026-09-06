"""D0 adapter: research TestSpec proof reuse over existing AuraOS admission/currentness owners.

This module does not own truth, currentness, lifecycle, effects, or physical KV memory.
It composes the canonical ConsequenceAdmissionKernel, CurrentnessInvalidator and
CollisionBucket to classify exact reuse, currentness rebind, dependency-cone reproof,
or fail-closed hold for claim-scoped research TestSpecs.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import hmac, json
from typing import FrozenSet, Mapping, Tuple

from tools.arena.frontier27_runtime import CollisionBucket, CurrentnessInvalidator
from tools.arena.consequence_admission_kernel import (
    AdmissionInput, AdmissionPolicy, AxisState, ConsequenceAdmissionKernel,
    ConsequenceVector, Decision, SourceExit,
)


def _stable(v: object) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _digest(v: object) -> str:
    return sha256(_stable(v)).hexdigest()


@dataclass(frozen=True)
class ProofUnit:
    unit_id: str
    dependencies: FrozenSet[str]
    proof_root: str


@dataclass(frozen=True)
class ResearchProofContract:
    principal: str
    claim_id: str
    claim_digest: str
    k27: Tuple[int, int, int]
    semantic_key: str
    testspec_root: str
    semantic_admission_root: str
    source_id: str
    source_owner_ref: str
    source_generation: str
    currentness_root: str
    currentness_verified: bool
    evidence_roots: FrozenSet[str]
    min_independent_roots: int
    evidence_ancestry_admitted: bool
    proof_units: Tuple[ProofUnit, ...]
    proof_surface: Mapping[str, str]
    resolution: int
    authority_ceiling: str = "D0"
    asks_effect_authority: bool = False

    def validate(self, *, stored: bool) -> None:
        if not all((self.principal, self.claim_id, self.claim_digest, self.semantic_key, self.testspec_root,
                    self.semantic_admission_root, self.source_id, self.source_owner_ref,
                    self.source_generation, self.currentness_root)):
            raise ValueError("RESEARCH_PROOF_BINDING_REQUIRED")
        if type(self.currentness_verified) is not bool or type(self.evidence_ancestry_admitted) is not bool:
            raise ValueError("ADMISSION_WITNESSES_MUST_BE_BOOL")
        if len(self.k27) != 3 or any(type(x) is not int or not 0 <= x <= 26 for x in self.k27):
            raise ValueError("K27_INVALID")
        if type(self.resolution) is not int or not 0 <= self.resolution <= 4:
            raise ValueError("RESOLUTION_INVALID")
        if type(self.min_independent_roots) is not int or self.min_independent_roots < 1:
            raise ValueError("INDEPENDENT_EVIDENCE_POLICY_INVALID")
        if self.authority_ceiling != "D0" or self.asks_effect_authority:
            raise ValueError("D0_EFFECT_CEILING")
        if stored and not self.currentness_verified:
            raise ValueError("CURRENTNESS_MUST_BE_VERIFIED_TO_STORE")
        if stored and not self.evidence_ancestry_admitted:
            raise ValueError("EVIDENCE_ANCESTRY_MUST_BE_ADMITTED_TO_STORE")
        if stored and len(self.evidence_roots) < self.min_independent_roots:
            raise ValueError("INSUFFICIENT_INDEPENDENT_EVIDENCE_ROOTS")
        seen=set()
        for unit in self.proof_units:
            if not unit.unit_id or not unit.proof_root or not unit.dependencies or unit.unit_id in seen:
                raise ValueError("PROOF_UNIT_INVALID")
            seen.add(unit.unit_id)
            if stored and not unit.dependencies.issubset(self.proof_surface):
                raise ValueError("PROOF_UNIT_DEPENDENCY_UNBOUND")


@dataclass(frozen=True)
class StoredResearchProof:
    contract: ResearchProofContract
    physical_identity: str
    semantic_root: str


@dataclass(frozen=True)
class ReuseDecision:
    disposition: str
    reasons: Tuple[str, ...]
    invalid_units: Tuple[str, ...]
    kernel_decision: str
    cache_identity: str
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False


class ResearchTestSpecProofReuseAdapter:
    """Non-owning proof-reuse adapter around canonical Arena primitives."""
    def __init__(self, *, secret: bytes, bucket: CollisionBucket, currentness: CurrentnessInvalidator,
                 kernel: ConsequenceAdmissionKernel):
        if not secret:
            raise ValueError("PRINCIPAL_SALT_SECRET_REQUIRED")
        self.secret=secret; self.bucket=bucket; self.currentness=currentness; self.kernel=kernel

    def identity(self, c: ResearchProofContract) -> str:
        payload=[c.principal, list(c.k27), c.semantic_key, c.claim_id, c.testspec_root]
        return hmac.new(self.secret, _stable(payload), sha256).hexdigest()

    def _node(self, identity: str, unit_id: str) -> str:
        return f"research-proof:{identity}:{unit_id}"

    def store(self, c: ResearchProofContract) -> StoredResearchProof:
        c.validate(stored=True)
        identity=self.identity(c)
        # Currentness is deliberately NOT part of local semantic proof identity.
        # It has its own at-use admission witness and can be rebound without minting
        # a new semantic generation when all semantic/provenance axes remain exact.
        semantic_root=_digest({
            "claim":c.claim_digest,"testspec":c.testspec_root,"semantic_admission":c.semantic_admission_root,
            "source":[c.source_id,c.source_owner_ref,c.source_generation],
            "evidence":sorted(c.evidence_roots),"min_independent_roots":c.min_independent_roots,
            "resolution":c.resolution,"surface":dict(sorted(c.proof_surface.items())),
            "units":[(u.unit_id,sorted(u.dependencies),u.proof_root) for u in c.proof_units],
            "authority":c.authority_ceiling,
        })
        stored=StoredResearchProof(c,identity,semantic_root)
        self.bucket.put(c.k27, identity, stored)
        for u in c.proof_units:
            self.currentness.bind(self._node(identity,u.unit_id), u.dependencies)
        return stored

    def assess(self, probe: ResearchProofContract) -> ReuseDecision:
        probe.validate(stored=False)
        identity=self.identity(probe)
        try:
            stored=self.bucket.get(probe.k27, identity)
        except KeyError:
            return ReuseDecision("MISS",("CACHE_MISS",),(),Decision.HOLD_REQUIRED_UNKNOWN.value,identity)
        base=stored.contract
        reasons=[]
        if base.claim_digest != probe.claim_digest: reasons.append("CLAIM_DIGEST_DRIFT")
        if base.semantic_admission_root != probe.semantic_admission_root: reasons.append("SEMANTIC_ADMISSION_DRIFT")
        if base.source_id != probe.source_id or base.source_owner_ref != probe.source_owner_ref: reasons.append("SOURCE_IDENTITY_DRIFT")
        if base.source_generation != probe.source_generation: reasons.append("SOURCE_GENERATION_DRIFT")
        if probe.evidence_roots != base.evidence_roots: reasons.append("EVIDENCE_ANCESTRY_DRIFT")
        if probe.min_independent_roots != base.min_independent_roots: reasons.append("EVIDENCE_POLICY_DRIFT")
        if len(probe.evidence_roots) < probe.min_independent_roots: reasons.append("INSUFFICIENT_INDEPENDENT_EVIDENCE_ROOTS")
        if not probe.evidence_ancestry_admitted: reasons.append("EVIDENCE_ANCESTRY_UNADMITTED")
        if probe.resolution < base.resolution: reasons.append("RESOLUTION_TOO_SHALLOW")

        changed=tuple(sorted(p for p,v in base.proof_surface.items() if probe.proof_surface.get(p) != v))
        missing=tuple(sorted(p for p in base.proof_surface if p not in probe.proof_surface))
        expanded=tuple(sorted(p for p in probe.proof_surface if p not in base.proof_surface))
        if changed: reasons.append("PROOF_SURFACE_DRIFT")
        if missing: reasons.append("PROOF_SURFACE_MISSING")
        if expanded: reasons.append("PROOF_SURFACE_EXPANDED")
        currentness_changed=base.currentness_root != probe.currentness_root
        if currentness_changed: reasons.append("CURRENTNESS_DRIFT")
        if not probe.currentness_verified: reasons.append("CURRENTNESS_UNVERIFIED")

        impact=set(changed)|set(missing)
        invalid=set()
        if expanded:
            # Unknown owned scope is not safely classifiable: invalidate all declared units.
            for u in base.proof_units: impact.update(u.dependencies)
        if impact:
            stale_nodes=self.currentness.invalidate(impact)
            for u in base.proof_units:
                if self._node(identity,u.unit_id) in stale_nodes: invalid.add(u.unit_id)
        if expanded:
            invalid.update(u.unit_id for u in base.proof_units)

        hard_identity=any(r in reasons for r in (
            "CLAIM_DIGEST_DRIFT","SEMANTIC_ADMISSION_DRIFT","SOURCE_IDENTITY_DRIFT",
            "SOURCE_GENERATION_DRIFT","EVIDENCE_ANCESTRY_DRIFT","EVIDENCE_POLICY_DRIFT",
            "INSUFFICIENT_INDEPENDENT_EVIDENCE_ROOTS","RESOLUTION_TOO_SHALLOW",
        ))
        admission_unknown=(not probe.currentness_verified) or (not probe.evidence_ancestry_admitted)
        scope_unknown=bool(expanded)
        proof_drift=bool(changed or missing)
        omega=[AxisState.VERIFIED]*8
        if hard_identity: omega[0]=AxisState.HARD_INVALID
        if not probe.evidence_ancestry_admitted: omega[3]=AxisState.UNKNOWN
        if scope_unknown: omega[5]=AxisState.UNKNOWN
        if invalid: omega[6]=AxisState.UNKNOWN
        source=SourceExit(probe.source_id,probe.source_owner_ref,probe.source_generation,
                          probe.semantic_admission_root,current=probe.currentness_verified)
        all_deps=set().union(*(u.dependencies for u in base.proof_units)) if base.proof_units else set()
        policy=AdmissionPolicy("RESEARCH_TESTSPEC_REUSE",tuple(range(8)),tuple(sorted(all_deps)))
        receipt=self.kernel.assess(AdmissionInput(
            project_id=probe.claim_id, vector=ConsequenceVector(tuple(omega)), policy=policy,
            source_exit=source, unresolved_dependencies=tuple(sorted(impact)), asks_effect_authority=False,
            evidence_refs=tuple(sorted(probe.evidence_roots)),
        ))

        if admission_unknown or scope_unknown:
            disposition="HOLD_UNKNOWN"
        elif hard_identity or proof_drift:
            disposition="REPROVE_CONE"
        elif currentness_changed:
            disposition="REBIND_CURRENTNESS"
        elif receipt.decision == Decision.READY_NONAUTHORIZING:
            disposition="REUSE_EXACT"
        else:
            disposition="HOLD_UNKNOWN"
        return ReuseDecision(disposition,tuple(reasons),tuple(sorted(invalid)),receipt.decision.value,identity)

    def rebind_currentness(self, probe: ResearchProofContract) -> StoredResearchProof:
        decision=self.assess(probe)
        if decision.disposition != "REBIND_CURRENTNESS":
            raise ValueError(f"CURRENTNESS_REBIND_NOT_ELIGIBLE:{decision.disposition}")
        identity=decision.cache_identity
        stored=self.bucket.get(probe.k27, identity)
        # Preserve the local semantic root: only the separately admitted currentness
        # witness is changing.
        rebound=StoredResearchProof(probe, identity, stored.semantic_root)
        self.bucket.put(probe.k27, identity, rebound)
        return rebound
