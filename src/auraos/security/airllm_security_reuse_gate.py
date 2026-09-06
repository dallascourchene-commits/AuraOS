from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json, re
from typing import Mapping

S = "AURA-AIRLLM-SECURITY-RECEIPT-v1"
RS = "AURA-AIRLLM-SECURITY-REUSE-ADMISSION-v1"
H = re.compile(r"^[0-9a-f]{64}$")
SC = {"GENERAL_LOCAL_SECURITY", "TRACE_SENSITIVE_LOCAL_SECURITY", "WORKLOAD_SENSITIVE_LOCAL_SECURITY", "TRACE_WORKLOAD_LOCAL_SECURITY"}
TS = {"TRACE_SENSITIVE_LOCAL_SECURITY", "TRACE_WORKLOAD_LOCAL_SECURITY"}
WS = {"WORKLOAD_SENSITIVE_LOCAL_SECURITY", "TRACE_WORKLOAD_LOCAL_SECURITY"}
P = ("1fqAvyxo24Agxup7H6ijOD15iWWt9eLR6AvOb0bynSDs", "1R4mqYlVPW2BKq21tFXOsz0uAAwS9BjiO2TntAdbOd0s")
_REQUIRED_LEAVES = {
    "model_artifact_integrity": (("source", "security", "evidence"), "LOCAL_ARTIFACT_STATIC"),
    "loader_source_integrity": (("source", "security", "evidence"), "LOCAL_SOURCE_STATIC"),
    "runtime_hard_false_membrane": (("semantic", "source", "runtime", "security", "evidence"), "LOCAL_RUNTIME"),
    "pinned_source_compatibility": (("source", "dependency", "security", "evidence"), "LOCAL_COMPATIBILITY"),
}

class SecurityReuseError(ValueError):
    pass

def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
def dig(x):
    return sha256(canon(x)).hexdigest()
def reqh(x, n):
    if not isinstance(x, str) or H.fullmatch(x) is None:
        raise SecurityReuseError(f"{n} must be exact lowercase SHA-256")
    return x

def _exact_string(x):
    return isinstance(x, str) and bool(x) and x.strip() == x

def _valid_complete_leaves(r: Mapping[str, object]) -> bool:
    leaves = r.get("leaves")
    bound = r.get("bound_generation")
    current = r.get("current_generation")
    if not isinstance(leaves, list) or len(leaves) != len(_REQUIRED_LEAVES):
        return False
    if not isinstance(bound, Mapping) or not isinstance(current, Mapping):
        return False
    if any(not _exact_string(k) or not _exact_string(v) for k, v in bound.items()):
        return False
    if dict(bound) != dict(current):
        return False
    seen = set()
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            return False
        leaf_id = leaf.get("leaf_id")
        if leaf_id not in _REQUIRED_LEAVES or leaf_id in seen:
            return False
        seen.add(leaf_id)
        axes, evidence_class = _REQUIRED_LEAVES[leaf_id]
        if leaf.get("axes") != list(axes) or leaf.get("evidence_class") != evidence_class:
            return False
        if leaf.get("status") != "PASS":
            return False
        proof = leaf.get("proof")
        if not isinstance(proof, Mapping):
            return False
        if proof.get("status") != "PASS" or not _exact_string(proof.get("proof_id")):
            return False
        if not isinstance(proof.get("proof_digest"), str) or H.fullmatch(proof["proof_digest"]) is None:
            return False
        proof_generation = proof.get("bound_generation")
        if not isinstance(proof_generation, Mapping):
            return False
        expected_generation = {axis: bound.get(axis) for axis in axes}
        if any(value is None for value in expected_generation.values()):
            return False
        if dict(proof_generation) != expected_generation:
            return False
        if not isinstance(proof.get("note", ""), str):
            return False
    return seen == set(_REQUIRED_LEAVES)

def valid_receipt(r):
    if not isinstance(r, Mapping) or r.get("schema") != S:
        return False
    h = r.get("receipt_sha256")
    if not isinstance(h, str) or H.fullmatch(h) is None:
        return False
    if any(r.get(k) is not False for k in ("effect_authority", "promotion_authorized", "owner_host_proven", "hosted_ci_proven", "gate10")):
        return False
    if r.get("disposition") != "LOCAL_VERIFIED_NONPROMOTING" or r.get("stale_or_missing") != []:
        return False
    if not _valid_complete_leaves(r):
        return False
    b = dict(r); b.pop("receipt_sha256", None); b.pop("k27", None); e = dig(b)
    if e != h:
        return False
    raw = bytes.fromhex(e)
    return r.get("k27") == [raw[0] % 27, raw[1] % 27, raw[2] % 27]

def subject_root(r):
    x = r.get("subject")
    if not isinstance(x, Mapping):
        raise SecurityReuseError("receipt subject must be a mapping")
    return dig(dict(x))
def generation_root(r):
    x = r.get("current_generation")
    if not isinstance(x, Mapping):
        raise SecurityReuseError("receipt current_generation must be a mapping")
    return dig(dict(x))

@dataclass(frozen=True)
class TraceReuseContract:
    expected_trace_schema_root: str
    proved_trace_schema_root: str
    expected_event_root: str
    proved_event_root: str
    reconstructed_event_root: str
    canonical_trace_schema_verified: bool
    execution_source_provenance_verified: bool
    fused_event_structure_verified: bool
    def __post_init__(self):
        for f in ("expected_trace_schema_root", "proved_trace_schema_root", "expected_event_root", "proved_event_root", "reconstructed_event_root"):
            reqh(getattr(self, f), f)
        for f in ("canonical_trace_schema_verified", "execution_source_provenance_verified", "fused_event_structure_verified"):
            if type(getattr(self, f)) is not bool:
                raise SecurityReuseError(f"{f} must be bool")
    def reasons(self):
        q = []
        if self.proved_trace_schema_root != self.expected_trace_schema_root: q.append("TRACE_SCHEMA_ROOT_MISMATCH")
        if not self.proved_event_root == self.expected_event_root == self.reconstructed_event_root: q.append("EVENT_IDENTITY_MISMATCH")
        if not self.canonical_trace_schema_verified: q.append("CANONICAL_TRACE_SCHEMA_UNVERIFIED")
        if not self.execution_source_provenance_verified: q.append("EXECUTION_SOURCE_PROVENANCE_UNVERIFIED")
        if not self.fused_event_structure_verified: q.append("FUSED_EVENT_STRUCTURE_UNVERIFIED")
        return q

@dataclass(frozen=True)
class WorkloadReuseContract:
    expected_workload_root: str
    observed_workload_root: str
    expected_environment_root: str
    observed_environment_root: str
    source_current: bool
    cross_category_rendered_prefix_collision: bool
    ranking_category_count: int
    def __post_init__(self):
        for f in ("expected_workload_root", "observed_workload_root", "expected_environment_root", "observed_environment_root"):
            reqh(getattr(self, f), f)
        if type(self.source_current) is not bool or type(self.cross_category_rendered_prefix_collision) is not bool:
            raise SecurityReuseError("workload booleans must be bool")
        if type(self.ranking_category_count) is not int or self.ranking_category_count < 0:
            raise SecurityReuseError("ranking_category_count must be non-negative int")
    def reasons(self):
        q = []
        if self.observed_workload_root != self.expected_workload_root: q.append("WORKLOAD_ROOT_MISMATCH")
        if self.observed_environment_root != self.expected_environment_root: q.append("ENVIRONMENT_ROOT_MISMATCH")
        if not self.source_current: q.append("WORKLOAD_SOURCE_STALE")
        if self.cross_category_rendered_prefix_collision: q.append("RENDERED_PREFIX_CONTAMINATION")
        if self.ranking_category_count < 2: q.append("INSUFFICIENT_RANKING_CATEGORIES")
        return q

@dataclass(frozen=True)
class SecurityReuseRequest:
    scope: str
    expected_receipt_sha256: str
    expected_subject_root: str
    expected_current_generation_root: str
    authority_requested: bool = False
    trace: TraceReuseContract | None = None
    workload: WorkloadReuseContract | None = None
    def __post_init__(self):
        if self.scope not in SC: raise SecurityReuseError("unsupported scope")
        for f in ("expected_receipt_sha256", "expected_subject_root", "expected_current_generation_root"): reqh(getattr(self, f), f)
        if type(self.authority_requested) is not bool: raise SecurityReuseError("authority_requested must be bool")
        if (self.scope in TS) != (self.trace is not None): raise SecurityReuseError("trace contract shape mismatch")
        if (self.scope in WS) != (self.workload is not None): raise SecurityReuseError("workload contract shape mismatch")

def admit(r: Mapping[str, object], x: SecurityReuseRequest):
    q = []; v = valid_receipt(r)
    if not v: q.append("SECURITY_RECEIPT_INVALID_OR_STALE")
    h = r.get("receipt_sha256") if isinstance(r, Mapping) else None
    if h != x.expected_receipt_sha256: q.append("RECEIPT_IDENTITY_MISMATCH")
    if v:
        try:
            if subject_root(r) != x.expected_subject_root: q.append("SECURITY_SUBJECT_MISMATCH")
            if generation_root(r) != x.expected_current_generation_root: q.append("SECURITY_GENERATION_MISMATCH")
        except SecurityReuseError:
            q.append("SECURITY_RECEIPT_MALFORMED_CONTEXT")
    if x.trace: q += x.trace.reasons()
    if x.workload: q += x.workload.reasons()
    if x.authority_requested: q.append("AUTHORITY_REQUEST_REQUIRES_REPROOF")
    q = sorted(set(q)); ok = not q
    b = {"schema": RS, "scope": x.scope, "exact_foreign_parents": list(P), "source_receipt_sha256": h, "expected_receipt_sha256": x.expected_receipt_sha256, "expected_subject_root": x.expected_subject_root, "expected_current_generation_root": x.expected_current_generation_root, "trace_contract": None if x.trace is None else asdict(x.trace), "workload_contract": None if x.workload is None else asdict(x.workload), "disposition": "REUSE_LOCAL_D0" if ok else "REPROVE", "reusable": ok, "reasons": q, "truth_authority": False, "effect_authority": False, "promotion_authorized": False, "owner_host_proven": False, "hosted_ci_proven": False, "gate10": False, "laws": ["MatchingResultRootDoesNotImplyReusableTraceProof", "TraceReuseRequiresCanonicalSchemaExecutionProvenanceAndExactEventIdentity", "WorkloadReuseRequiresExactEnvelopeCurrentSourceAndNoPrefixContamination", "TraceAndWorkloadObligationsAreNoncompensatory", "CompleteCanonicalSecurityLeavesRequiredForReuse", "LocalReuseEligibilityDoesNotMintAuthority", "TrailingContextCannotRepairFailedHardAxis"]}
    d = dig(b); b["decision_sha256"] = d; z = bytes.fromhex(d); b["k27"] = [z[0] % 27, z[1] % 27, z[2] % 27]; return b

def verify(d):
    if not isinstance(d, Mapping) or d.get("schema") != RS: return False
    h = d.get("decision_sha256")
    if not isinstance(h, str) or H.fullmatch(h) is None: return False
    if any(d.get(k) is not False for k in ("truth_authority", "effect_authority", "promotion_authorized", "owner_host_proven", "hosted_ci_proven", "gate10")): return False
    b = dict(d); b.pop("decision_sha256", None); b.pop("k27", None); e = dig(b); z = bytes.fromhex(e)
    return e == h and d.get("k27") == [z[0] % 27, z[1] % 27, z[2] % 27]

__all__ = ["SecurityReuseError", "SecurityReuseRequest", "TraceReuseContract", "WorkloadReuseContract", "admit", "subject_root", "generation_root", "valid_receipt", "verify"]
