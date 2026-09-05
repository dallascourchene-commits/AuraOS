"""Independent, non-authorizing proof-reuse admission verifier.

Proof reuse is fail-closed. Exact reuse binds proof/result/workflow/input/dependency
identity. Resource and trace scopes add noncompensatory envelope and replay gates.
Generated-only source movement is eligible for a proof-neutral rebind only when a
provider observation is explicitly bound to parent, child, generator identity and
changed paths. This module verifies bounded attestation consistency; it does not
establish provider truth, mint hosted PASS, effect authority, or Gate10.
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
_VALID_CLAIM_SCOPES = frozenset({GENERAL_PROOF, RESOURCE_SENSITIVE_BENCHMARK, TRACE_REPLAY_PROOF, RESOURCE_TRACE_REPLAY_BENCHMARK})
_RESOURCE_SCOPES = frozenset({RESOURCE_SENSITIVE_BENCHMARK, RESOURCE_TRACE_REPLAY_BENCHMARK})
_TRACE_SCOPES = frozenset({TRACE_REPLAY_PROOF, RESOURCE_TRACE_REPLAY_BENCHMARK})

class Admission(str, Enum):
    REUSE_EXACT = "REUSE_EXACT"
    ELIGIBLE_BY_PROOF_NEUTRAL_REBIND = "ELIGIBLE_BY_PROOF_NEUTRAL_REBIND"
    REPROVE = "REPROVE"

def _stable(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

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

def allowlist_root(allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST) -> str:
    return _digest(_canonical_paths(allowlist))

def rebind_observation_root(parent_head: str, child_head: str, generator_identity: str, changed_paths: Iterable[str]) -> str:
    if not all(isinstance(x, str) and x and x != "NA" for x in (parent_head, child_head, generator_identity)):
        raise ValueError("rebind observation requires concrete parent, child, and generator identity")
    paths = _canonical_paths(changed_paths)
    if not paths:
        raise ValueError("rebind observation requires at least one changed path")
    return _digest({"parent_head": parent_head, "child_head": child_head, "generator_identity": generator_identity, "changed_paths": paths})

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
    proved_trace_root: str = "NA"
    expected_trace_root: str = "NA"
    proved_environment_root: str = "NA"
    expected_environment_root: str = "NA"
    proved_resource_budget_root: str = "NA"
    expected_resource_budget_root: str = "NA"
    cumulative_resource_budget_verified: bool = True
    benchmark_oracle_ceiling_verified: bool = True
    proved_trace_schema_root: str = "NA"
    expected_trace_schema_root: str = "NA"
    proved_event_root: str = "NA"
    expected_event_root: str = "NA"
    reconstructed_event_root: str = "NA"
    canonical_trace_schema_verified: bool = False
    execution_source_provenance_verified: bool = False
    fused_event_structure_verified: bool = False
    rebind_parent_head: str = "NA"
    rebind_child_head: str = "NA"
    observed_generator_identity: str = "NA"
    expected_generator_identity: str = "NA"
    provider_observation_root: str = "NA"
    expected_provider_observation_root: str = "NA"
    provider_observation_verified: bool = False

    def validate_shape(self) -> bool:
        strings = (
            self.proved_source_head, self.current_source_head, self.proved_result_root, self.expected_result_root,
            self.proved_workflow_generation, self.expected_workflow_generation, self.proved_input_root, self.expected_input_root,
            self.proved_dependency_root, self.expected_dependency_root, self.proved_required_step_root, self.expected_required_step_root,
            self.claim_scope, self.proved_trace_root, self.expected_trace_root, self.proved_environment_root, self.expected_environment_root,
            self.proved_resource_budget_root, self.expected_resource_budget_root, self.proved_trace_schema_root, self.expected_trace_schema_root,
            self.proved_event_root, self.expected_event_root, self.reconstructed_event_root, self.rebind_parent_head, self.rebind_child_head,
            self.observed_generator_identity, self.expected_generator_identity, self.provider_observation_root, self.expected_provider_observation_root,
        )
        bools = (
            self.internal_receipt_valid, self.source_truth_bound, self.required_steps_complete, self.direct_child_verified,
            self.trusted_generator_verified, self.authority_requested, self.cumulative_resource_budget_verified,
            self.benchmark_oracle_ceiling_verified, self.canonical_trace_schema_verified, self.execution_source_provenance_verified,
            self.fused_event_structure_verified, self.provider_observation_verified,
        )
        if not (all(isinstance(x, str) and x for x in strings)
                and type(self.proved_binding_generation) is int and type(self.expected_binding_generation) is int
                and self.proved_binding_generation >= 0 and self.expected_binding_generation >= 0
                and all(type(x) is bool for x in bools) and self.claim_scope in _VALID_CLAIM_SCOPES):
            return False
        if self.claim_scope in _RESOURCE_SCOPES and not all(x != "NA" for x in (
            self.proved_trace_root, self.expected_trace_root, self.proved_environment_root,
            self.expected_environment_root, self.proved_resource_budget_root, self.expected_resource_budget_root)):
            return False
        if self.claim_scope in _TRACE_SCOPES and not all(x != "NA" for x in (
            self.proved_trace_schema_root, self.expected_trace_schema_root, self.proved_event_root,
            self.expected_event_root, self.reconstructed_event_root)):
            return False
        return True

@dataclass(frozen=True)
class ProofReuseReceipt:
    decision: Admission
    evidence_root: str
    changed_path_root: str
    allowlist_root: str
    fresh_hosted_pass: bool = False
    authority: bool = False

    def verify(self, evidence: ProofReuseEvidence, allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST) -> bool:
        try:
            paths = _canonical_paths(evidence.changed_paths)
            policy_root = allowlist_root_fn(allowlist)
        except (TypeError, ValueError):
            return False
        return (self.decision == decide(evidence, allowlist=allowlist)
                and self.evidence_root == evidence_digest(evidence)
                and self.changed_path_root == _digest(paths)
                and self.allowlist_root == policy_root
                and self.fresh_hosted_pass is False and self.authority is False)

def allowlist_root_fn(allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST) -> str:
    return allowlist_root(allowlist)

def evidence_digest(e: ProofReuseEvidence) -> str:
    paths = _canonical_paths(e.changed_paths)
    return _digest({
        "proved_source_head": e.proved_source_head, "current_source_head": e.current_source_head,
        "proved_result_root": e.proved_result_root, "expected_result_root": e.expected_result_root,
        "proved_workflow_generation": e.proved_workflow_generation, "expected_workflow_generation": e.expected_workflow_generation,
        "proved_input_root": e.proved_input_root, "expected_input_root": e.expected_input_root,
        "proved_dependency_root": e.proved_dependency_root, "expected_dependency_root": e.expected_dependency_root,
        "proved_required_step_root": e.proved_required_step_root, "expected_required_step_root": e.expected_required_step_root,
        "proved_binding_generation": e.proved_binding_generation, "expected_binding_generation": e.expected_binding_generation,
        "internal_receipt_valid": e.internal_receipt_valid, "source_truth_bound": e.source_truth_bound,
        "required_steps_complete": e.required_steps_complete, "direct_child_verified": e.direct_child_verified,
        "trusted_generator_verified": e.trusted_generator_verified, "changed_paths": paths,
        "authority_requested": e.authority_requested, "claim_scope": e.claim_scope,
        "proved_trace_root": e.proved_trace_root, "expected_trace_root": e.expected_trace_root,
        "proved_environment_root": e.proved_environment_root, "expected_environment_root": e.expected_environment_root,
        "proved_resource_budget_root": e.proved_resource_budget_root, "expected_resource_budget_root": e.expected_resource_budget_root,
        "cumulative_resource_budget_verified": e.cumulative_resource_budget_verified,
        "benchmark_oracle_ceiling_verified": e.benchmark_oracle_ceiling_verified,
        "proved_trace_schema_root": e.proved_trace_schema_root, "expected_trace_schema_root": e.expected_trace_schema_root,
        "proved_event_root": e.proved_event_root, "expected_event_root": e.expected_event_root,
        "reconstructed_event_root": e.reconstructed_event_root,
        "canonical_trace_schema_verified": e.canonical_trace_schema_verified,
        "execution_source_provenance_verified": e.execution_source_provenance_verified,
        "fused_event_structure_verified": e.fused_event_structure_verified,
        "rebind_parent_head": e.rebind_parent_head, "rebind_child_head": e.rebind_child_head,
        "observed_generator_identity": e.observed_generator_identity, "expected_generator_identity": e.expected_generator_identity,
        "provider_observation_root": e.provider_observation_root,
        "expected_provider_observation_root": e.expected_provider_observation_root,
        "provider_observation_verified": e.provider_observation_verified,
    })

def _resource_envelope_exact(e: ProofReuseEvidence) -> bool:
    if e.claim_scope not in _RESOURCE_SCOPES:
        return True
    return (e.proved_trace_root == e.expected_trace_root and e.proved_environment_root == e.expected_environment_root
            and e.proved_resource_budget_root == e.expected_resource_budget_root
            and e.cumulative_resource_budget_verified and e.benchmark_oracle_ceiling_verified)

def _trace_replay_exact(e: ProofReuseEvidence) -> bool:
    if e.claim_scope not in _TRACE_SCOPES:
        return True
    return (e.proved_trace_schema_root == e.expected_trace_schema_root
            and e.proved_event_root == e.expected_event_root == e.reconstructed_event_root
            and e.canonical_trace_schema_verified and e.execution_source_provenance_verified and e.fused_event_structure_verified)

def _proof_truth_exact(e: ProofReuseEvidence) -> bool:
    return (e.internal_receipt_valid and e.source_truth_bound and e.required_steps_complete
            and e.proved_result_root == e.expected_result_root
            and e.proved_workflow_generation == e.expected_workflow_generation
            and e.proved_input_root == e.expected_input_root
            and e.proved_dependency_root == e.expected_dependency_root
            and e.proved_required_step_root == e.expected_required_step_root
            and e.proved_binding_generation == e.expected_binding_generation
            and _resource_envelope_exact(e) and _trace_replay_exact(e) and not e.authority_requested)

def _rebind_attestation_exact(e: ProofReuseEvidence, changed: tuple[str, ...]) -> bool:
    if not (e.direct_child_verified and e.trusted_generator_verified and e.provider_observation_verified and changed):
        return False
    if not all(x != "NA" for x in (e.rebind_parent_head, e.rebind_child_head, e.observed_generator_identity,
                                     e.expected_generator_identity, e.provider_observation_root,
                                     e.expected_provider_observation_root)):
        return False
    if (e.rebind_parent_head != e.proved_source_head or e.rebind_child_head != e.current_source_head
            or e.observed_generator_identity != e.expected_generator_identity):
        return False
    try:
        computed = rebind_observation_root(e.rebind_parent_head, e.rebind_child_head, e.observed_generator_identity, changed)
    except (TypeError, ValueError):
        return False
    return e.provider_observation_root == e.expected_provider_observation_root == computed

def decide(evidence: ProofReuseEvidence, *, allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST) -> Admission:
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
    if set(changed) <= allowed and _rebind_attestation_exact(evidence, changed):
        return Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND
    return Admission.REPROVE

def make_receipt(evidence: ProofReuseEvidence, *, allowlist: Iterable[str] = DEFAULT_GENERATED_ALLOWLIST) -> ProofReuseReceipt:
    paths = _canonical_paths(evidence.changed_paths)
    return ProofReuseReceipt(decision=decide(evidence, allowlist=allowlist), evidence_root=evidence_digest(evidence),
                             changed_path_root=_digest(paths), allowlist_root=allowlist_root(allowlist),
                             fresh_hosted_pass=False, authority=False)

class GenerationDisposition(str, Enum):
    EXACT_UNCHANGED = "EXACT_UNCHANGED"
    PROOF_NEUTRAL_REBIND = "PROOF_NEUTRAL_REBIND"
    CONSEQUENCE_CHANGED = "CONSEQUENCE_CHANGED"
    UNKNOWN = "UNKNOWN"

def _canonical_named_fields(fields: Iterable[tuple[str, Any]]) -> tuple[tuple[str, Any], ...]:
    if isinstance(fields, (str, bytes)):
        raise ValueError("raw evidence fields must be named pairs")
    out: dict[str, Any] = {}
    for item in fields:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("raw evidence fields must be (name, value) pairs")
        name, value = item
        if not isinstance(name, str) or not name or name in out:
            raise ValueError("raw evidence field names must be unique non-empty strings")
        _stable(value)
        out[name] = value
    if not out:
        raise ValueError("raw evidence cannot be empty")
    return tuple((name, out[name]) for name in sorted(out))

@dataclass(frozen=True)
class EvidenceProjectionReceipt:
    schema: str
    full_projection_root: str
    consequence_projection_root: str
    consequence_keys_root: str

def project_raw_evidence(schema: str, fields: Iterable[tuple[str, Any]], consequence_keys: Iterable[str]) -> EvidenceProjectionReceipt:
    """Recompute full and consequence-only roots from explicit raw evidence."""
    if not isinstance(schema, str) or not schema or schema == "NA":
        raise ValueError("evidence schema must be concrete")
    canonical = _canonical_named_fields(fields)
    by_name = dict(canonical)
    keys = tuple(sorted(set(consequence_keys)))
    if not keys or any(not isinstance(k, str) or not k for k in keys) or any(k not in by_name for k in keys):
        raise ValueError("consequence keys must be present non-empty strings")
    consequence = tuple((k, by_name[k]) for k in keys)
    return EvidenceProjectionReceipt(schema, _digest({"schema": schema, "fields": canonical}),
                                     _digest({"schema": schema, "consequence": consequence}), _digest(keys))

def generation_observation_root(owner_id: str, prior_generation: str, current_generation: str,
                                current_projection_root: str, changed_paths: Iterable[str]) -> str:
    if not all(isinstance(x, str) and x and x != "NA" for x in (owner_id, prior_generation, current_generation, current_projection_root)):
        raise ValueError("generation observation requires concrete owner/generation/projection identity")
    return _digest({"owner_id": owner_id, "prior_generation": prior_generation, "current_generation": current_generation,
                    "current_projection_root": current_projection_root, "changed_paths": _canonical_paths(changed_paths)})

@dataclass(frozen=True)
class ParentGenerationTransition:
    owner_id: str
    expected_owner_id: str
    prior_generation: str
    current_generation: str
    evidence_schema: str
    prior_raw_evidence: tuple[tuple[str, Any], ...]
    current_raw_evidence: tuple[tuple[str, Any], ...]
    consequence_keys: tuple[str, ...]
    proof_time_full_projection_root: str
    proof_time_consequence_projection_root: str
    expected_current_full_projection_root: str
    expected_current_consequence_projection_root: str
    changed_paths: tuple[str, ...] = ()
    provider_observation_root: str = "NA"
    expected_provider_observation_root: str = "NA"
    provider_observation_verified: bool = False
    authority_requested: bool = False

    def validate_shape(self) -> bool:
        strings=(self.owner_id,self.expected_owner_id,self.prior_generation,self.current_generation,self.evidence_schema,
                 self.proof_time_full_projection_root,self.proof_time_consequence_projection_root,
                 self.expected_current_full_projection_root,self.expected_current_consequence_projection_root,
                 self.provider_observation_root,self.expected_provider_observation_root)
        return (all(isinstance(x,str) and x for x in strings) and type(self.provider_observation_verified) is bool
                and type(self.authority_requested) is bool and isinstance(self.prior_raw_evidence,tuple)
                and isinstance(self.current_raw_evidence,tuple) and isinstance(self.consequence_keys,tuple)
                and isinstance(self.changed_paths,tuple))

@dataclass(frozen=True)
class GenerationReproofReceipt:
    disposition: GenerationDisposition
    owner_id: str
    prior_generation: str
    current_generation: str
    prior_projection_root: str
    current_projection_root: str
    prior_consequence_root: str
    current_consequence_root: str
    changed_path_root: str
    obligations: tuple[str, ...]
    readjudication_required: bool
    auto_admit: bool = False
    authority: bool = False

    def verify(self, transition: ParentGenerationTransition) -> bool:
        return self == classify_parent_generation(transition)

def _unknown_generation_receipt(t: ParentGenerationTransition, prior: EvidenceProjectionReceipt | None = None,
                                current: EvidenceProjectionReceipt | None = None) -> GenerationReproofReceipt:
    owner=t.owner_id if isinstance(t.owner_id,str) and t.owner_id else "UNKNOWN_OWNER"
    try:path_root=_digest(_canonical_paths(t.changed_paths))
    except (TypeError,ValueError):path_root="UNRESOLVED"
    return GenerationReproofReceipt(GenerationDisposition.UNKNOWN,owner,
        t.prior_generation if isinstance(t.prior_generation,str) else "UNRESOLVED",
        t.current_generation if isinstance(t.current_generation,str) else "UNRESOLVED",
        prior.full_projection_root if prior else "UNRESOLVED",current.full_projection_root if current else "UNRESOLVED",
        prior.consequence_projection_root if prior else "UNRESOLVED",current.consequence_projection_root if current else "UNRESOLVED",
        path_root,(f"{owner}:VERIFY_OR_REPROVE_PARENT","CROSS_BINDINGS:READJUDICATE_AFTER_PARENT_PROOF"),True,False,False)

def classify_parent_generation(t: ParentGenerationTransition) -> GenerationReproofReceipt:
    """Recompute evidence ancestry and return the smallest nonauthorizing reproof cone."""
    if not t.validate_shape() or t.authority_requested:return _unknown_generation_receipt(t)
    try:
        prior=project_raw_evidence(t.evidence_schema,t.prior_raw_evidence,t.consequence_keys)
        current=project_raw_evidence(t.evidence_schema,t.current_raw_evidence,t.consequence_keys)
        changed=_canonical_paths(t.changed_paths)
    except (TypeError,ValueError,OverflowError):return _unknown_generation_receipt(t)
    if (t.owner_id!=t.expected_owner_id or prior.full_projection_root!=t.proof_time_full_projection_root
            or prior.consequence_projection_root!=t.proof_time_consequence_projection_root
            or current.full_projection_root!=t.expected_current_full_projection_root
            or current.consequence_projection_root!=t.expected_current_consequence_projection_root):
        return _unknown_generation_receipt(t,prior,current)
    common=dict(owner_id=t.owner_id,prior_generation=t.prior_generation,current_generation=t.current_generation,
        prior_projection_root=prior.full_projection_root,current_projection_root=current.full_projection_root,
        prior_consequence_root=prior.consequence_projection_root,current_consequence_root=current.consequence_projection_root,
        changed_path_root=_digest(changed),auto_admit=False,authority=False)
    if t.prior_generation==t.current_generation:
        if prior.full_projection_root==current.full_projection_root and not changed:
            return GenerationReproofReceipt(disposition=GenerationDisposition.EXACT_UNCHANGED,obligations=(),readjudication_required=False,**common)
        return GenerationReproofReceipt(disposition=GenerationDisposition.UNKNOWN,
            obligations=(f"{t.owner_id}:VERIFY_OR_REPROVE_PARENT","CROSS_BINDINGS:READJUDICATE_AFTER_PARENT_PROOF"),readjudication_required=True,**common)
    try:observed=generation_observation_root(t.owner_id,t.prior_generation,t.current_generation,current.full_projection_root,changed)
    except (TypeError,ValueError):return _unknown_generation_receipt(t,prior,current)
    bound=(t.provider_observation_verified and t.provider_observation_root!="NA" and t.expected_provider_observation_root!="NA"
           and t.provider_observation_root==t.expected_provider_observation_root==observed)
    if not bound:
        return GenerationReproofReceipt(disposition=GenerationDisposition.UNKNOWN,
            obligations=(f"{t.owner_id}:VERIFY_OR_REPROVE_PARENT","CROSS_BINDINGS:READJUDICATE_AFTER_PARENT_PROOF"),readjudication_required=True,**common)
    if prior.consequence_projection_root!=current.consequence_projection_root:
        return GenerationReproofReceipt(disposition=GenerationDisposition.CONSEQUENCE_CHANGED,
            obligations=(f"{t.owner_id}:REPROVE_PARENT","CROSS_BINDINGS:READJUDICATE_AFTER_PARENT_PROOF"),readjudication_required=True,**common)
    return GenerationReproofReceipt(disposition=GenerationDisposition.PROOF_NEUTRAL_REBIND,
        obligations=("CROSS_BINDINGS:READJUDICATE_CURRENTNESS",),readjudication_required=True,**common)
