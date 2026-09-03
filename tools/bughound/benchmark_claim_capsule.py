"""BugHound O11 benchmark claim capsule and conservative comparison gate.

The gate binds benchmark claims to exact evidence. It never grants target-testing,
submission, payment, deployment, or generalized real-world superiority authority.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json
from typing import Iterable

QUALITY_AXES = ("precision", "recall", "localization_f1", "trace_coverage", "reproduction_rate", "patched_specificity", "repeatability")
COST_AXES = ("tool_calls", "tokens", "elapsed_ms")

class ClaimCapsuleError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail

def _canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()

def _dig(domain, v):
    return hashlib.sha256(domain.encode()+b"\0"+_canon(v)).hexdigest()

def _need(s, code):
    if not isinstance(s, str) or not s.strip(): raise ClaimCapsuleError(code)
    return s.strip()

@dataclass(frozen=True)
class IntervalV1:
    low: float
    point: float
    high: float
    def validate(self, *, unit=False):
        vals=(self.low,self.point,self.high)
        if any(not isinstance(v,(int,float)) for v in vals): raise ClaimCapsuleError("INTERVAL_NUMERIC_REQUIRED")
        if not self.low <= self.point <= self.high: raise ClaimCapsuleError("INTERVAL_ORDER_INVALID")
        if unit and not (0 <= self.low <= self.high <= 1): raise ClaimCapsuleError("UNIT_INTERVAL_INVALID")

@dataclass(frozen=True)
class BenchmarkRunReceiptV1:
    system_id: str
    system_generation: str
    corpus_id: str
    corpus_generation: str
    benchmark_semantic_root: str
    historical_cut_digest: str
    split_digest: str
    case_set_digest: str
    evaluator_generation: str
    tool_policy_digest: str
    resource_budget_digest: str
    provider_head: str
    provider_run_id: str
    provider_job_id: str
    exact_head_verified: bool
    historical_blind: bool
    repo_group_disjoint: bool
    contamination_free: bool
    completed: bool
    quality: tuple[tuple[str, IntervalV1], ...]
    costs: tuple[tuple[str, IntervalV1], ...]
    independent_observer_ref: str
    authority: bool=False
    external_effect: bool=False
    @property
    def run_digest(self): return _dig("AURA_BUGHOUND_BENCHMARK_RUN_V1", asdict(self))

@dataclass(frozen=True)
class ComparisonReceiptV1:
    challenger: str
    baselines: tuple[str,...]
    basis_digest: str
    run_digests: tuple[str,...]
    status: str
    supported_quality_axes: tuple[str,...]
    nonworse_cost_axes: tuple[str,...]
    claim_scope: str
    authority: bool=False
    external_effect: bool=False
    generalized_real_world_superiority: bool=False
    @property
    def receipt_digest(self): return _dig("AURA_BUGHOUND_COMPARISON_RECEIPT_V1", asdict(self))

def _maps(run):
    q=dict(run.quality); c=dict(run.costs)
    if set(q)!=set(QUALITY_AXES): raise ClaimCapsuleError("QUALITY_AXES_INCOMPLETE")
    if set(c)!=set(COST_AXES): raise ClaimCapsuleError("COST_AXES_INCOMPLETE")
    for x in QUALITY_AXES: q[x].validate(unit=True)
    for x in COST_AXES:
        c[x].validate(unit=False)
        if c[x].low < 0: raise ClaimCapsuleError("COST_NEGATIVE")
    return q,c

def validate_run(run: BenchmarkRunReceiptV1):
    if not isinstance(run,BenchmarkRunReceiptV1): raise ClaimCapsuleError("RUN_RECEIPT_REQUIRED")
    for attr,code in (("system_id","SYSTEM_ID_REQUIRED"),("system_generation","SYSTEM_GENERATION_REQUIRED"),("corpus_id","CORPUS_ID_REQUIRED"),("corpus_generation","CORPUS_GENERATION_REQUIRED"),("benchmark_semantic_root","BENCHMARK_ROOT_REQUIRED"),("historical_cut_digest","HISTORICAL_CUT_REQUIRED"),("split_digest","SPLIT_DIGEST_REQUIRED"),("case_set_digest","CASE_SET_REQUIRED"),("evaluator_generation","EVALUATOR_GENERATION_REQUIRED"),("tool_policy_digest","TOOL_POLICY_REQUIRED"),("resource_budget_digest","RESOURCE_BUDGET_REQUIRED"),("provider_head","PROVIDER_HEAD_REQUIRED"),("provider_run_id","PROVIDER_RUN_REQUIRED"),("provider_job_id","PROVIDER_JOB_REQUIRED"),("independent_observer_ref","INDEPENDENT_OBSERVER_REQUIRED")):
        _need(getattr(run,attr),code)
    if run.authority or run.external_effect: raise ClaimCapsuleError("RUN_EFFECT_FORBIDDEN")
    if not run.completed: raise ClaimCapsuleError("RUN_INCOMPLETE")
    if not run.exact_head_verified: raise ClaimCapsuleError("EXACT_HEAD_UNVERIFIED")
    if not run.historical_blind: raise ClaimCapsuleError("HISTORICAL_BLIND_REQUIRED")
    if not run.repo_group_disjoint: raise ClaimCapsuleError("REPO_GROUP_DISJOINT_REQUIRED")
    if not run.contamination_free: raise ClaimCapsuleError("CONTAMINATION_FREE_REQUIRED")
    _maps(run)

def _basis_tuple(r):
    return (r.corpus_id,r.corpus_generation,r.benchmark_semantic_root,r.historical_cut_digest,r.split_digest,r.case_set_digest,r.evaluator_generation,r.tool_policy_digest,r.resource_budget_digest)

def compare(challenger: BenchmarkRunReceiptV1, baselines: Iterable[BenchmarkRunReceiptV1], *, claim_scope: str) -> ComparisonReceiptV1:
    validate_run(challenger)
    bs=tuple(baselines)
    if not bs: raise ClaimCapsuleError("BASELINE_REQUIRED")
    _need(claim_scope,"CLAIM_SCOPE_REQUIRED")
    for b in bs: validate_run(b)
    if any(b.system_id==challenger.system_id and b.system_generation==challenger.system_generation for b in bs): raise ClaimCapsuleError("SELF_COMPARISON_FORBIDDEN")
    basis=_basis_tuple(challenger)
    if any(_basis_tuple(b)!=basis for b in bs): raise ClaimCapsuleError("UNMATCHED_BENCHMARK_BASIS")
    observers={challenger.independent_observer_ref,*(b.independent_observer_ref for b in bs)}
    if len(observers)<2: raise ClaimCapsuleError("OBSERVER_DIVERSITY_REQUIRED")
    cq,cc=_maps(challenger)
    baseline_maps=tuple(_maps(b) for b in bs)
    supported=[]
    for axis in QUALITY_AXES:
        # Conservative separation: challenger lower bound must exceed every baseline upper bound.
        if all(cq[axis].low > bq[axis].high for bq,_ in baseline_maps): supported.append(axis)
    nonworse=[]
    for axis in COST_AXES:
        # Cost is lower-is-better; challenger upper bound must be <= every baseline upper bound.
        if all(cc[axis].high <= bc[axis].high for _,bc in baseline_maps): nonworse.append(axis)
    all_quality=len(supported)==len(QUALITY_AXES)
    all_cost=len(nonworse)==len(COST_AXES)
    status="SCOPED_SUPERIORITY_SUPPORTED" if all_quality and all_cost else "CLAIM_HOLD_INSUFFICIENT_DOMINANCE"
    run_digests=(challenger.run_digest,)+tuple(b.run_digest for b in bs)
    return ComparisonReceiptV1(
        challenger=challenger.system_id,
        baselines=tuple(b.system_id for b in bs),
        basis_digest=_dig("AURA_BUGHOUND_COMPARISON_BASIS_V1",basis),
        run_digests=run_digests,
        status=status,
        supported_quality_axes=tuple(supported),
        nonworse_cost_axes=tuple(nonworse),
        claim_scope=claim_scope,
    )

def hyper1000():
    return tuple((a,b,c) for a in range(10) for b in range(10) for c in range(10))
