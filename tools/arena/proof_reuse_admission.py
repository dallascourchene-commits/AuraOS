"""Independent, non-authorizing proof-reuse admission verifier.

The verifier separates proof identity from provider movement and binds reuse to the
claim's consequence-bearing envelope. Resource-sensitive claims bind trace,
environment, cumulative budget and oracle ceilings. Trace-replay claims additionally
bind canonical trace schema, executed-source provenance, fused-event structure, and
original/reconstructed event identity. The module never mints hosted PASS, effect
or Gate10 authority.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import PurePosixPath
from typing import Any, Iterable

DEFAULT_GENERATED_ALLOWLIST = frozenset({".aura/CODEMAP.json", ".aura/CODEMAP.md"})
GENERAL_PROOF = "GENERAL"
RESOURCE_SENSITIVE_BENCHMARK = "RESOURCE_SENSITIVE_BENCHMARK"
TRACE_REPLAY_PROOF = "TRACE_REPLAY_PROOF"
RESOURCE_TRACE_REPLAY_BENCHMARK = "RESOURCE_TRACE_REPLAY_BENCHMARK"
_VALID_CLAIM_SCOPES = frozenset({
    GENERAL_PROOF,
    RESOURCE_SENSITIVE_BENCHMARK,
    TRACE_REPLAY_PROOF,
    RESOURCE_TRACE_REPLAY_BENCHMARK,
})
_RESOURCE_SCOPES = frozenset({RESOURCE_SENSITIVE_BENCHMARK, RESOURCE_TRACE_REPLAY_BENCHMARK})
_TRACE_SCOPES = frozenset({TRACE_REPLAY_PROOF, RESOURCE_TRACE_REPLAY_BENCHMARK})


class Admission(str, Enum):
    REUSE_EXACT = "REUSE_EXACT"
    ELIGIBLE_BY_PROOF_NEUTRAL_REBIND = "ELIGIBLE_BY_PROOF_NEUTRAL_REBIND"
    REPROVE = "REPROVE"


def _stable(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _digest(value: Any) -> str:
    return sha256(_stable(value)).hexdigest()


def _canonical_paths(paths: Iterable[str]) -> tuple[str, ...]:
    out: set[str] = set()
    for raw in paths:
        if not isinstance(raw, str) or not raw or "\\" in raw:
            raise ValueError("changed paths must be non-empty POSIX strings")
        p = PurePosixPath(raw)
        if p.is_absolute() or ".." in p.parts or str(p) in {"", "."}:
            raise ValueError("changed paths must be repository-relative and traversal-free")
        out.add(str(p))
    return tuple(sorted(out))


@dataclass(frozen=True)
class ProofReuseEvidence:
    proved_source_head: str
    current_source_head: str
    proved_result_root: str
    expected_result_root: str
    proved_workflow_generation: str
    expected_workflow_generation: str
    proved_input_root: str
    expected_input_root: str
    proved_dependency_root: str
    expected_dependency_root: str
    proved_required_step_root: str
    expected_required_step_root: str
    proved_binding_generation: int
    expected_binding_generation: int
    internal_receipt_valid: bool
    source_truth_bound: bool
    required_steps_complete: bool
    direct_child_verified: bool = False
    trusted_generator_verified: bool = False
    changed_paths: tuple[str, ...] = ()
    authority_requested: bool = False
    claim_scope: str = GENERAL_PROOF
    # Resource-envelope identity.
    proved_trace_root: str = "NA"
    expected_trace_root: str = "NA"
    proved_environment_root: str = "NA"
    expected_environment_root: str = "NA"
    proved_resource_budget_root: str = "NA"
    expected_resource_budget_root: str = "NA"
    cumulative_resource_budget_verified: bool = True
    benchmark_oracle_ceiling_verified: bool = True
    # Trace-replay identity. These are mandatory only for trace scopes.
    proved_trace_schema_root: str = "NA"
    expected_trace_schema_root: str = "NA"
    proved_event_root: str = "NA"
    expected_event_root: str = "NA"
    reconstructed_event_root: str = "NA"
    canonical_trace_schema_verified: bool = False
    execution_source_provenance_verified: bool = False
    fused_event_structure_verified: bool = False

    def validate_shape(self) -> bool:
        strings = (
            self.proved_source_head,
            self.current_source_head,
            self.proved_result_root,
            self.expected_result_root,
            self.proved_workflow_generation,
            self.expected_workflow_generation,
            self.proved_input_root,
            self.expected_input_root,
            self.proved_dependency_root,
            self.expected_dependency_root,
            self.proved_required_step_root,
            self.expected_required_step_root,
            self.claim_scope,
            self.proved_trace_root,
            self.expected_trace_root,
            self.proved_environment_root,
            self.expected_environment_root,
            self.proved_resource_budget_root,
            self.expected_resource_budget_root,
            self.proved_trace_schema_root,
            self.expected_trace_schema_root,
            self.proved_event_root,
            self.expected_event_root,
            self.reconstructed_event_root,
         )
        bools = (
            self.internal_receipt_valid,
            self.source_truth_bound,
            self.required_steps_complete,
            self.direct_child_verified,
            self.trusted_generator_verified,
            self.authority_requested,
            self.cumulative_resource_budget_verified,
            self.benchmark_oracle_ceiling_verified,
            self.canonical_trace_schema_verified,
            self.execution_source_provenance_verified,
            self.fused_event_structure_verified,
        )
        if not (
            all(isinstance(x, str) and x for x in strings)
            and isinstance(self.proved_binding_generation, int)
            and isinstance(self.expected_binding_generation, int)
            and self.proved_binding_generation >= 0
            and self.expected_binding_generation >= 0
            and all(type(x) is bool for x in bools)
            and self.claim_scope in _VALID_CLAIM_SCOPES
        ):
            return False
        if self.claim_scope in _RESOURCE_SCOPES and not all(
            x != "NA"
            for x in (
                self.proved_trace_root,
                self.expected_trace_root,
                self.proved_environment_root,
                self.expected_environment_root,
                self.proved_resource_budget_root,
                self.expected_resource_budget_root,
            )
        ):
            return False
        if self.claim_scope in _TRACE_SCOPES and not all(
            x != "NA"
            for x in (
                self.proved_trace_schema_root,
                self.expected_trace_schema_root,
                self.proved_event_root,
                self.expected_event_root,
                self.reconstructed_event_root,
            )
        ):
            return False
        return True


@dataclass(frozen=True)
class ProofReuseReceipt:
    decision: Admission
    evidence_root: str
    changed_path_root: str
    fresh_hosted_pass: bool = False
    authority: bool = False

    def verify(
        self,
        evidence: ProofReuseEvidence,
        allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST,
    ) -> bool:
        paths = _canonical_paths(evidence.changed_paths)
        return (
            self.decision == decide(evidence, allowlist=allowlist)
            and self.evidence_root == evidence_digest(evidence)
            and self.changed_path_root == _digest(paths)
            and self.fresh_hosted_pass is False
            and self.authority is False
         )


def evidence_digest(evidence: ProofReuseEvidence) -> str:
    paths = _canonical_paths(evidence.changed_paths)
    return _digest({
        "proved_source_head": evidence.proved_source_head,
        "current_source_head": evidence.current_source_head,
        "proved_result_root": evidence.proved_result_root,
        "expected_result_root": evidence.expected_result_root,
        "proved_workflow_generation": evidence.proved_workflow_generation,
        "expected_workflow_generation": evidence.expected_workflow_generation,
        "proved_input_root": evidence.proved_input_root,
        "expected_input_root": evidence.expected_input_root,
        "proved_dependency_root": evidence.proved_dependency_root,
        "expected_dependency_root": evidence.expected_dependency_root,
        "proved_required_step_root": evidence.proved_required_step_root,
        "expected_required_step_root": evidence.expected_required_step_root,
        "proved_binding_generation": evidence.proved_binding_generation,
        "expected_binding_generation": evidence.expected_binding_generation,
        "internal_receipt_valid": evidence.internal_receipt_valid,
        "source_truth_bound": evidence.source_truth_bound,
        "required_steps_complete": evidence.required_steps_complete,
        "direct_child_verified": evidence.direct_child_verified,
        "trusted_generator_verified": evidence.trusted_generator_verified,
        "changed_paths": paths,
        "authority_requested": evidence.authority_requested,
        "claim_scope": evidence.claim_scope,
        "proved_trace_root": evidence.proved_trace_root,
        "expected_trace_root": evidence.expected_trace_root,
        "proved_environment_root": evidence.proved_environment_root,
        "expected_environment_root": evidence.expected_environment_root,
        "proved_resource_budget_root": evidence.proved_resource_budget_root,
        "expected_resource_budget_root": evidence.expected_resource_budget_root,
        "cumulative_resource_budget_verified": evidence.cumulative_resource_budget_verified,
        "benchmark_oracle_ceiling_verified": evidence.benchmark_oracle_ceiling_verified,
        "proved_trace_schema_root": evidence.proved_trace_schema_root,
        "expected_trace_schema_root": evidence.expected_trace_schema_root,
        "proved_event_root": evidence.proved_event_root,
        "expected_event_root": evidence.expected_event_root,
        "reconstructed_event_root": evidence.reconstructed_event_root,
        "canonical_trace_schema_verified": evidence.canonical_trace_schema_verified,
        "execution_source_provenance_verified": evidence.execution_source_provenance_verified,
        "fused_event_structure_verified": evidence.fused_event_structure_verified,
    })


def _resource_envelope_exact(e: ProofReuseEvidence) -> bool:
    if e.claim_scope not in _RESOURCE_SCOPES:
        return True
    return (
        e.proved_trace_root == e.expected_trace_root
        and e.proved_environment_root == e.expected_environment_root
        and e.proved_resource_budget_root == e.expected_resource_budget_root
        and e.cumulative_resource_budget_verified
        and e.benchmark_oracle_ceiling_verified
    )


def _trace_replay_exact(e: ProofReuseEvidence) -> bool:
    if e.claim_scope not in _TRACE_SCOPES:
        return True
    return (
        e.proved_trace_schema_root == e.expected_trace_schema_root
        and e.proved_event_root == e.expected_event_root
        and e.expected_event_root == e.reconstructed_event_root
        and e.canonical_trace_schema_verified
        and e.execution_source_provenance_verified
        and e.fused_event_structure_verified
    )


def _proof_truth_exact(e: ProofReuseEvidence) -> bool:
    return (
        e.internal_receipt_valid
        and e.source_truth_bound
        and e.required_steps_complete
        and e.proved_result_root == e.expected_result_root
        and e.proved_workflow_generation == e.expected_workflow_generation
        and e.proved_input_root == e.expected_input_root
        and e.proved_dependency_root == e.expected_dependency_root
        and e.proved_required_step_root == e.expected_required_step_root
        and e.proved_binding_generation == e.expected_binding_generation
        and _resource_envelope_exact(e)
        and _trace_replay_exact(e)
        and not e.authority_requested
    )


def decide(
    evidence: ProofReuseEvidence, *, allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST
) -> Admission:
    if not evidence.validate_shape():
        return Admission.REPROVE
    try:
        changed = _canonical_paths(evidence.changed_paths)
        allowed = frozenset(_canonical_paths(allowlist))
    except (TypeError, ValueError):
        return Admission.REPROVE
    if not _proof_truth_exact(evidence):
        return Admission.REPROVE
    if evidence.proved_source_head == evidence.current_source_head:
        return Admission.REUSE_EXACT if not changed else Admission.REPROVE
    if (
        evidence.direct_child_verified
        and evidence.trusted_generator_verified
        and bool(changed)
        and set(changed) <= allowed
     ):
        return Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND
    return Admission.REPROVE


def make_receipt(
    evidence: ProofReuseEvidence, *, allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST
) -> ProofReuseReceipt:
    paths = _canonical_paths(evidence.changed_paths)
    return ProofReuseReceipt(
        decision=decide(evidence, allowlist=allowlist),
        evidence_root=evidence_digest(evidence),
        changed_path_root=_digest(paths),
        fresh_hosted_pass=False,
        authority=False,
    )
