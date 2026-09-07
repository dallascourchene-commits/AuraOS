from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

D0 = "D0_NONPROMOTING"
TECC_SCHEMA = "AURA-TECC-v1"

def digest(v):
    return sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class CoverageDisposition(str, Enum):
    READY = "READY_D0"
    HOLD_PENDING = "HOLD_PENDING_OBLIGATION"
    HOLD_STALE = "HOLD_STALE_COVERAGE"
    HOLD_CONFLICT = "HOLD_EVIDENCE_CONFLICT"
    HOLD_IDENTITY = "HOLD_COVERAGE_IDENTITY"
    HOLD_MUTATION = "HOLD_MUTATION_AUTHORITY"

class AdmissionMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    EFFECT_BOUND = "EFFECT_BOUND"

@dataclass(frozen=True)
class PositiveTrace:
    branch_id: str
    program_root: str
    sealed_domain_root: str
    generation: int
    trace_root: str
    current: bool = True
    complete: bool = True

@dataclass(frozen=True)
class NegativeProof:
    branch_id: str
    program_root: str
    sealed_domain_root: str
    generation: int
    proof_root: str
    current: bool = True
    sound: bool = True

@dataclass(frozen=True)
class CoverageCertificate:
    disposition: CoverageDisposition
    program_root: str
    sealed_domain_root: str
    generation: int
    obligations: tuple[str, ...]
    discharged_positive: tuple[str, ...]
    discharged_negative: tuple[str, ...]
    pending: tuple[str, ...]
    receipt_root: str
    authority: str = D0
    mutation_authority: bool = False
    gate10: bool = False

@dataclass(frozen=True)
class CoverageUseDecision:
    disposition: CoverageDisposition
    reason: str
    authority: str = D0
    mutation_authority: bool = False
    gate10: bool = False


def _valid_root(x: str) -> bool:
    return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x)


def compile_coverage_certificate(*, program_root: str, sealed_domain_root: str, generation: int,
                                 obligations: tuple[str, ...], positive: tuple[PositiveTrace, ...] = (),
                                 negative: tuple[NegativeProof, ...] = ()) -> CoverageCertificate:
    if not _valid_root(program_root) or not _valid_root(sealed_domain_root):
        raise ValueError("program/domain roots must be lowercase sha256")
    if type(generation) is not int or generation < 0:
        raise ValueError("generation must be nonnegative")
    if not obligations or any(not isinstance(x, str) or not x for x in obligations):
        raise ValueError("nonempty obligations required")
    if len(set(obligations)) != len(obligations):
        raise ValueError("duplicate obligation")
    allowed = set(obligations)
    pos, neg, stale = set(), set(), set()
    for ev in positive:
        if ev.branch_id not in allowed:
            raise ValueError("positive trace for unknown obligation")
        identity_ok = (ev.program_root, ev.sealed_domain_root, ev.generation) == (program_root, sealed_domain_root, generation)
        if identity_ok and ev.current and ev.complete:
            pos.add(ev.branch_id)
        else:
            stale.add(ev.branch_id)
    for ev in negative:
        if ev.branch_id not in allowed:
            raise ValueError("negative proof for unknown obligation")
        identity_ok = (ev.program_root, ev.sealed_domain_root, ev.generation) == (program_root, sealed_domain_root, generation)
        if identity_ok and ev.current and ev.sound:
            neg.add(ev.branch_id)
        else:
            stale.add(ev.branch_id)
    conflict = pos & neg
    pending = allowed - pos - neg
    if conflict:
        disp = CoverageDisposition.HOLD_CONFLICT
    elif stale:
        disp = CoverageDisposition.HOLD_STALE
    elif pending:
        disp = CoverageDisposition.HOLD_PENDING
    else:
        disp = CoverageDisposition.READY
    payload = {
        "schema": "AURA-MEMORY-CITY-COVERAGE-MEMBRANE-v1",
        "disposition": disp.value,
        "program_root": program_root,
        "sealed_domain_root": sealed_domain_root,
        "generation": generation,
        "obligations": sorted(obligations),
        "positive": sorted(pos),
        "negative": sorted(neg),
        "pending": sorted(pending),
        "stale": sorted(stale),
        "conflict": sorted(conflict),
        "mutation_authority": False,
    }
    return CoverageCertificate(disp, program_root, sealed_domain_root, generation,
        tuple(sorted(obligations)), tuple(sorted(pos)), tuple(sorted(neg)), tuple(sorted(pending)), digest(payload))


def validate_coverage_at_use(cert: CoverageCertificate, *, program_root: str, sealed_domain_root: str,
                             generation: int, mutation_requested: bool = False) -> CoverageUseDecision:
    if mutation_requested:
        return CoverageUseDecision(CoverageDisposition.HOLD_MUTATION, "read_only_membrane_never_mints_mutation_authority")
    if (program_root, sealed_domain_root, generation) != (cert.program_root, cert.sealed_domain_root, cert.generation):
        return CoverageUseDecision(CoverageDisposition.HOLD_IDENTITY, "program_domain_or_generation_moved")
    if cert.disposition is not CoverageDisposition.READY:
        return CoverageUseDecision(cert.disposition, "compiled_coverage_not_ready")
    return CoverageUseDecision(CoverageDisposition.READY, "all_branch_obligations_currently_discharged")


def compile_proof_carrying_typed_admission(*, typed_closure_receipt_root: str, coverage: CoverageCertificate,
                                            support_root: str, influence_root: str, transition_model_root: str,
                                            future_congruence_root: str | None, horizon: int,
                                            mode: AdmissionMode = AdmissionMode.READ_ONLY) -> dict:
    for name, root in (("typed", typed_closure_receipt_root), ("support", support_root), ("influence", influence_root), ("transition", transition_model_root)):
        if not isinstance(root, str) or not root:
            raise ValueError(f"{name} root required")
    if type(horizon) is not int or horizon < 0:
        raise ValueError("horizon must be nonnegative")
    if not isinstance(mode, AdmissionMode):
        raise ValueError("mode must be AdmissionMode")

    read_ready = coverage.disposition is CoverageDisposition.READY and (horizon == 0 or bool(future_congruence_root))
    if mode is AdmissionMode.EFFECT_BOUND:
        disposition = "HOLD_TECC_REQUIRED_D0"
        reason = "effect_bound_use_requires_independent_tecc_verification"
        required_verifier_schema = TECC_SCHEMA
    else:
        disposition = "READY_D0" if read_ready else "HOLD_D0"
        reason = "read_only_coverage_and_horizon_ready" if read_ready else "read_only_coverage_or_horizon_not_ready"
        required_verifier_schema = None

    payload = {
        "schema": "AURA-MEMORY-CITY-PROOF-CARRYING-TYPED-ADMISSION-v2",
        "disposition": disposition,
        "reason": reason,
        "admission_mode": mode.value,
        "typed_closure_receipt_root": typed_closure_receipt_root,
        "coverage_receipt_root": coverage.receipt_root,
        "support_root": support_root,
        "influence_root": influence_root,
        "transition_model_root": transition_model_root,
        "future_congruence_root": future_congruence_root,
        "horizon": horizon,
        "required_verifier_schema": required_verifier_schema,
        "authority_minted": False,
        "mutation_authority": False,
        "effect_authority": False,
        "gate10": False,
    }
    payload["receipt_root"] = digest(payload)
    return payload
