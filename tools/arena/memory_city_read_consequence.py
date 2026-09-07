from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from memory_city_coverage_membrane import CoverageCertificate, CoverageDisposition

D0 = "D0_NONPROMOTING"
SCHEMA = "AURA-MEMORY-CITY-TRUST-EXACT-READ-CONSEQUENCE-v2"

def digest(v):
    return sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def valid_root(x: str) -> bool:
    return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x)

class ReadConsequenceDisposition(str, Enum):
    READY = "READY_D0"
    HOLD_COVERAGE = "HOLD_COVERAGE"
    HOLD_ENVELOPE = "HOLD_WORLD_ENVELOPE"
    HOLD_STALE_WORLD = "HOLD_STALE_WORLD"
    HOLD_CONSEQUENCE_DIVERGENCE = "HOLD_CONSEQUENCE_DIVERGENCE"
    HOLD_TRUST_DIVERGENCE = "HOLD_READ_TRUST_DIVERGENCE"
    HOLD_MEMBER = "HOLD_WORLD_MEMBERSHIP"
    HOLD_COVERAGE_IDENTITY = "HOLD_COVERAGE_IDENTITY"
    HOLD_TRUST_IDENTITY = "HOLD_READ_TRUST_IDENTITY"
    HOLD_PROJECTION_IDENTITY = "HOLD_PROJECTION_IDENTITY"
    HOLD_MUTATION = "HOLD_MUTATION_AUTHORITY"

@dataclass(frozen=True)
class ReadWorldProjection:
    world_id: str
    world_root: str
    hydration_item_ids: tuple[str, ...]
    reproof_item_ids: tuple[str, ...]
    read_obligation_root: str
    projection_root: str
    current: bool = True
    k27_hint: tuple[int, ...] = ()
    def __post_init__(self):
        if not isinstance(self.world_id, str) or not self.world_id:
            raise ValueError("world_id required")
        for name, root in (("world_root", self.world_root), ("read_obligation_root", self.read_obligation_root), ("projection_root", self.projection_root)):
            if not valid_root(root):
                raise ValueError(f"{name} must be lowercase sha256")
        if len(set(self.hydration_item_ids)) != len(self.hydration_item_ids):
            raise ValueError("duplicate hydration item")
        if len(set(self.reproof_item_ids)) != len(self.reproof_item_ids):
            raise ValueError("duplicate reproof item")
        if type(self.current) is not bool:
            raise ValueError("current must be bool")
        if any(type(x) is not int or x < 0 or x > 26 for x in self.k27_hint):
            raise ValueError("k27 hint values must be 0..26")
    @property
    def hydration_cut(self): return tuple(sorted(self.hydration_item_ids))
    @property
    def reproof_cut(self): return tuple(sorted(self.reproof_item_ids))

@dataclass(frozen=True)
class ReadConsequenceCertificate:
    disposition: ReadConsequenceDisposition
    coverage_receipt_root: str
    program_root: str
    sealed_domain_root: str
    generation: int
    member_world_ids: tuple[str, ...]
    member_world_roots: tuple[str, ...]
    member_projection_roots: tuple[str, ...]
    hydration_cut: tuple[str, ...]
    reproof_cut: tuple[str, ...]
    read_obligation_root: str | None
    consequence_root: str | None
    receipt_root: str
    reason: str = ""
    authority: str = D0
    mutation_authority: bool = False
    gate10: bool = False

@dataclass(frozen=True)
class ReadConsequenceUseDecision:
    disposition: ReadConsequenceDisposition
    reason: str
    consequence_root: str | None
    authority: str = D0
    mutation_authority: bool = False
    gate10: bool = False


def compile_read_consequence_certificate(*, coverage: CoverageCertificate,
                                         projections: tuple[ReadWorldProjection, ...]) -> ReadConsequenceCertificate:
    if coverage.disposition is not CoverageDisposition.READY:
        payload = {"schema": SCHEMA, "disposition": ReadConsequenceDisposition.HOLD_COVERAGE.value,
                   "coverage": coverage.receipt_root, "reason": "coverage_not_ready"}
        return ReadConsequenceCertificate(ReadConsequenceDisposition.HOLD_COVERAGE, coverage.receipt_root,
            coverage.program_root, coverage.sealed_domain_root, coverage.generation, (), (), (), (), (), None, None,
            digest(payload), "coverage_not_ready")
    positive = tuple(sorted(coverage.discharged_positive))
    if not positive:
        payload = {"schema": SCHEMA, "disposition": ReadConsequenceDisposition.HOLD_ENVELOPE.value,
                   "coverage": coverage.receipt_root, "reason": "no_admitted_positive_world"}
        return ReadConsequenceCertificate(ReadConsequenceDisposition.HOLD_ENVELOPE, coverage.receipt_root,
            coverage.program_root, coverage.sealed_domain_root, coverage.generation, (), (), (), (), (), None, None,
            digest(payload), "no_admitted_positive_world")
    ids = tuple(sorted(p.world_id for p in projections))
    if len(set(ids)) != len(ids) or ids != positive:
        payload = {"schema": SCHEMA, "disposition": ReadConsequenceDisposition.HOLD_ENVELOPE.value,
                   "coverage": coverage.receipt_root, "positive": list(positive), "projection_ids": list(ids),
                   "reason": "positive_world_projection_mismatch"}
        return ReadConsequenceCertificate(ReadConsequenceDisposition.HOLD_ENVELOPE, coverage.receipt_root,
            coverage.program_root, coverage.sealed_domain_root, coverage.generation, (), (), (), (), (), None, None,
            digest(payload), "positive_world_projection_mismatch")
    ordered = tuple(sorted(projections, key=lambda p: p.world_id))
    if any(not p.current for p in ordered):
        payload = {"schema": SCHEMA, "disposition": ReadConsequenceDisposition.HOLD_STALE_WORLD.value,
                   "coverage": coverage.receipt_root, "reason": "stale_member_world"}
        return ReadConsequenceCertificate(ReadConsequenceDisposition.HOLD_STALE_WORLD, coverage.receipt_root,
            coverage.program_root, coverage.sealed_domain_root, coverage.generation, ids,
            tuple(p.world_root for p in ordered), tuple(p.projection_root for p in ordered), (), (), None, None, digest(payload), "stale_member_world")
    hyd = {p.hydration_cut for p in ordered}; rep = {p.reproof_cut for p in ordered}
    trust = {p.read_obligation_root for p in ordered}
    if len(hyd) != 1 or len(rep) != 1:
        disp = ReadConsequenceDisposition.HOLD_CONSEQUENCE_DIVERGENCE; reason = "hydration_or_reproof_diverged"
        hcut = (); rcut = (); tro = None; croot = None
    elif len(trust) != 1:
        disp = ReadConsequenceDisposition.HOLD_TRUST_DIVERGENCE; reason = "read_use_trust_obligation_diverged"
        hcut = next(iter(hyd)); rcut = next(iter(rep)); tro = None; croot = None
    else:
        disp = ReadConsequenceDisposition.READY; reason = "complete_world_envelope_uniform_read_consequence_and_trust"
        hcut = next(iter(hyd)); rcut = next(iter(rep)); tro = next(iter(trust))
        croot = digest({"schema": SCHEMA, "coverage": coverage.receipt_root, "program": coverage.program_root,
                        "domain": coverage.sealed_domain_root, "generation": coverage.generation,
                        "hydration": list(hcut), "reproof": list(rcut), "read_obligation_root": tro})
    payload = {"schema": SCHEMA, "disposition": disp.value, "coverage": coverage.receipt_root,
               "program": coverage.program_root, "domain": coverage.sealed_domain_root, "generation": coverage.generation,
               "member_world_ids": list(ids), "member_world_roots": [p.world_root for p in ordered],
               "member_projection_roots": [p.projection_root for p in ordered],
               "hydration": list(hcut), "reproof": list(rcut), "read_obligation_root": tro,
               "consequence_root": croot, "reason": reason, "mutation_authority": False}
    return ReadConsequenceCertificate(disp, coverage.receipt_root, coverage.program_root, coverage.sealed_domain_root,
        coverage.generation, ids, tuple(p.world_root for p in ordered), tuple(p.projection_root for p in ordered), hcut, rcut, tro, croot, digest(payload), reason)


def validate_read_consequence_at_use(cert: ReadConsequenceCertificate, *, coverage: CoverageCertificate,
                                     active_world_id: str, active_world_root: str, active_projection_root: str,
                                     read_obligation_root: str, mutation_requested: bool = False) -> ReadConsequenceUseDecision:
    if mutation_requested:
        return ReadConsequenceUseDecision(ReadConsequenceDisposition.HOLD_MUTATION,
            "read_consequence_certificate_never_mints_mutation_authority", None)
    if coverage.receipt_root != cert.coverage_receipt_root or coverage.disposition is not CoverageDisposition.READY:
        return ReadConsequenceUseDecision(ReadConsequenceDisposition.HOLD_COVERAGE_IDENTITY,
            "coverage_receipt_or_readiness_moved", None)
    pairs = set(zip(cert.member_world_ids, cert.member_world_roots))
    if (active_world_id, active_world_root) not in pairs:
        return ReadConsequenceUseDecision(ReadConsequenceDisposition.HOLD_MEMBER,
            "active_world_not_certified_member", None)
    projection_pairs = set(zip(cert.member_world_ids, cert.member_world_roots, cert.member_projection_roots))
    if (active_world_id, active_world_root, active_projection_root) not in projection_pairs:
        return ReadConsequenceUseDecision(ReadConsequenceDisposition.HOLD_PROJECTION_IDENTITY,
            "active_world_projection_receipt_moved", None)
    if cert.disposition is not ReadConsequenceDisposition.READY:
        return ReadConsequenceUseDecision(cert.disposition, cert.reason, None)
    if read_obligation_root != cert.read_obligation_root:
        return ReadConsequenceUseDecision(ReadConsequenceDisposition.HOLD_TRUST_IDENTITY,
            "read_use_trust_obligation_moved", None)
    return ReadConsequenceUseDecision(ReadConsequenceDisposition.READY,
        "active_world_is_current_member_of_trust_exact_read_consequence_class", cert.consequence_root)
