from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Sequence

SCHEMA = "AURA-WQ-EFFICIENCY-PROOF-REUSE-v2"
RECEIPT_SCHEMA = SCHEMA + "-RECEIPT"
PROOF_PARENT_SEMANTIC_COMMIT = "b07199c48f9b6c26642108c9ff61bf3ca0dc6082"
PROOF_PARENT_SOURCE_BLOB = "9ff46da6e89dffa095eebfb1f453cb7e7ded9ec8"
COST_PARENT_SEMANTIC_COMMIT = "09302691da7292ac2e2b75a0e9c5d6409848f609"
COST_PARENT_SOURCE_BLOB = "dbfc655897e3402517ba978b0856ea8a96595b0f"
CURRENT_BASE_HEAD = "7a2c7a16f845752ffb7c16c68636d8d542ecd72e"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class GateError(ValueError):
    pass


class Decision(str, Enum):
    REUSE_EXACT = "REUSE_EXACT"
    REPROVE = "REPROVE"


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GateError("NON_CANONICAL_VALUE") from exc


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _hex40(value: Any) -> bool:
    return isinstance(value, str) and _HEX40.fullmatch(value) is not None


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def _dec(value: Any, name: str) -> Decimal:
    if not isinstance(value, str) or not value:
        raise GateError(f"INVALID_DECIMAL:{name}")
    try:
        out = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise GateError(f"INVALID_DECIMAL:{name}") from exc
    if not out.is_finite() or out < 0:
        raise GateError(f"INVALID_DECIMAL:{name}")
    return out


def _dstr(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


@dataclass(frozen=True)
class ProofParentEvidence:
    semantic_commit: str
    verifier_blob: str
    source_head: str
    current_source_head: str
    result_root: str
    expected_result_root: str
    workflow_generation: str
    expected_workflow_generation: str
    input_root: str
    expected_input_root: str
    dependency_root: str
    expected_dependency_root: str
    required_step_root: str
    expected_required_step_root: str
    binding_generation: int
    expected_binding_generation: int
    trace_root: str
    expected_trace_root: str
    environment_root: str
    expected_environment_root: str
    resource_budget_root: str
    expected_resource_budget_root: str
    trace_schema_root: str
    expected_trace_schema_root: str
    event_root: str
    expected_event_root: str
    reconstructed_event_root: str
    cumulative_budget_proof_root: str
    expected_cumulative_budget_proof_root: str
    oracle_ceiling_proof_root: str
    expected_oracle_ceiling_proof_root: str
    execution_provenance_root: str
    expected_execution_provenance_root: str
    fused_event_structure_root: str
    expected_fused_event_structure_root: str

    def validate_shape(self) -> bool:
        strings = (
            self.semantic_commit, self.verifier_blob, self.source_head, self.current_source_head,
            self.result_root, self.expected_result_root, self.workflow_generation,
            self.expected_workflow_generation, self.input_root, self.expected_input_root,
            self.dependency_root, self.expected_dependency_root, self.required_step_root,
            self.expected_required_step_root, self.trace_root, self.expected_trace_root,
            self.environment_root, self.expected_environment_root, self.resource_budget_root,
            self.expected_resource_budget_root, self.trace_schema_root, self.expected_trace_schema_root,
            self.event_root, self.expected_event_root, self.reconstructed_event_root,
            self.cumulative_budget_proof_root, self.expected_cumulative_budget_proof_root,
            self.oracle_ceiling_proof_root, self.expected_oracle_ceiling_proof_root,
            self.execution_provenance_root, self.expected_execution_provenance_root,
            self.fused_event_structure_root, self.expected_fused_event_structure_root,
        )
        return (
            all(_nonempty(x) for x in strings)
            and _hex40(self.semantic_commit)
            and _hex40(self.verifier_blob)
            and _hex40(self.source_head)
            and _hex40(self.current_source_head)
            and all(type(x) is int and x >= 0 for x in (self.binding_generation, self.expected_binding_generation))
        )

    def independently_valid(self) -> bool:
        if not self.validate_shape():
            return False
        if self.semantic_commit != PROOF_PARENT_SEMANTIC_COMMIT or self.verifier_blob != PROOF_PARENT_SOURCE_BLOB:
            return False
        if self.source_head != CURRENT_BASE_HEAD or self.current_source_head != CURRENT_BASE_HEAD:
            return False
        equal_pairs = (
            (self.result_root, self.expected_result_root),
            (self.workflow_generation, self.expected_workflow_generation),
            (self.input_root, self.expected_input_root),
            (self.dependency_root, self.expected_dependency_root),
            (self.required_step_root, self.expected_required_step_root),
            (self.trace_root, self.expected_trace_root),
            (self.environment_root, self.expected_environment_root),
            (self.resource_budget_root, self.expected_resource_budget_root),
            (self.trace_schema_root, self.expected_trace_schema_root),
            (self.event_root, self.expected_event_root),
            (self.expected_event_root, self.reconstructed_event_root),
            (self.cumulative_budget_proof_root, self.expected_cumulative_budget_proof_root),
            (self.oracle_ceiling_proof_root, self.expected_oracle_ceiling_proof_root),
            (self.execution_provenance_root, self.expected_execution_provenance_root),
            (self.fused_event_structure_root, self.expected_fused_event_structure_root),
        )
        return all(a == b for a, b in equal_pairs) and self.binding_generation == self.expected_binding_generation

    @property
    def projection_root(self) -> str:
        if not self.independently_valid():
            raise GateError("INVALID_PROOF_PARENT")
        return digest({"parent":"AGENT_27","evidence":asdict(self)})


@dataclass(frozen=True)
class WorkloadSample:
    sample_id: str
    category: str
    rendered_prefix: str
    ranking_eligible: bool
    control_group: str | None = None

    def canonical(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TransferCharge:
    transfer_id: str
    sequence: int
    sample_id: str
    kind: str
    bytes_moved: int

    def canonical(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CostEnvelope:
    source_head: str
    runtime_generation: str
    hardware_fingerprint: str
    benchmark_generation: str
    joules_per_gb: str
    speculative_energy_budget_j: str
    bytes_per_gb: int = 1_000_000_000

    def canonical(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CostParentEvidence:
    semantic_commit: str
    verifier_blob: str
    samples: tuple[WorkloadSample, ...]
    transfers: tuple[TransferCharge, ...]
    envelope: CostEnvelope

    def independently_compile(self) -> dict[str, Any]:
        if self.semantic_commit != COST_PARENT_SEMANTIC_COMMIT or self.verifier_blob != COST_PARENT_SOURCE_BLOB:
            raise GateError("COST_PARENT_GENERATION_DRIFT")
        if type(self.samples) is not tuple or not self.samples:
            raise GateError("EMPTY_WORKLOAD")
        if type(self.transfers) is not tuple:
            raise GateError("INVALID_TRANSFERS")
        if type(self.envelope) is not CostEnvelope:
            raise GateError("INVALID_ENVELOPE")
        env = self.envelope
        if env.source_head != CURRENT_BASE_HEAD or not _hex40(env.source_head):
            raise GateError("SOURCE_HEAD_DRIFT")
        for v in (env.runtime_generation, env.hardware_fingerprint, env.benchmark_generation):
            if not _nonempty(v): raise GateError("INVALID_ENVELOPE_IDENTITY")
        if type(env.bytes_per_gb) is not int or env.bytes_per_gb <= 0:
            raise GateError("INVALID_BYTES_PER_GB")
        rate = _dec(env.joules_per_gb, "joules_per_gb")
        budget = _dec(env.speculative_energy_budget_j, "speculative_energy_budget_j")

        ids: set[str] = set(); ranking_by_prefix: dict[str, set[str]] = {}; cats: set[str] = set()
        for s in self.samples:
            if type(s) is not WorkloadSample or not all(_nonempty(x) for x in (s.sample_id,s.category,s.rendered_prefix)) or type(s.ranking_eligible) is not bool:
                raise GateError("INVALID_SAMPLE")
            if s.sample_id in ids: raise GateError("DUPLICATE_SAMPLE_ID")
            ids.add(s.sample_id)
            if s.ranking_eligible:
                if s.control_group is not None: raise GateError("RANKING_SAMPLE_CANNOT_BE_CONTROL")
                cats.add(s.category); ranking_by_prefix.setdefault(s.rendered_prefix,set()).add(s.category)
            elif not _nonempty(s.control_group):
                raise GateError("CONTROL_GROUP_REQUIRED")
        if len(cats) < 2: raise GateError("NEED_TWO_RANKING_CATEGORIES")
        if any(len(v)>1 for v in ranking_by_prefix.values()): raise GateError("CROSS_CATEGORY_EXACT_PREFIX_COLLISION")

        seen: set[str] = set(); demand_b=spec_b=0; demand_n=spec_n=0
        for expected,t in enumerate(self.transfers,1):
            if type(t) is not TransferCharge or not _nonempty(t.transfer_id) or t.transfer_id in seen:
                raise GateError("INVALID_TRANSFER_ID")
            seen.add(t.transfer_id)
            if type(t.sequence) is not int or t.sequence != expected: raise GateError("NONCONTIGUOUS_TRANSFER_SEQUENCE")
            if t.sample_id not in ids: raise GateError("TRANSFER_UNKNOWN_SAMPLE")
            if t.kind not in {"DEMAND","SPECULATIVE"}: raise GateError("INVALID_TRANSFER_KIND")
            if type(t.bytes_moved) is not int or t.bytes_moved <= 0: raise GateError("INVALID_TRANSFER_BYTES")
            if t.kind=="DEMAND": demand_b += t.bytes_moved; demand_n += 1
            else: spec_b += t.bytes_moved; spec_n += 1
        total_b=demand_b+spec_b
        spec_e=Decimal(spec_b)*rate/Decimal(env.bytes_per_gb)
        if spec_e>budget: raise GateError("CUMULATIVE_SPECULATIVE_ENERGY_BUDGET_EXCEEDED")
        total_e=Decimal(total_b)*rate/Decimal(env.bytes_per_gb); demand_e=Decimal(demand_b)*rate/Decimal(env.bytes_per_gb)
        workload_root=digest([s.canonical() for s in self.samples]); transfer_root=digest([t.canonical() for t in self.transfers]); envelope_id=digest(env.canonical())
        body={"schema":"AURA-WORKLOAD-QUALIFIED-COST-RECEIPT-v1","source_head":env.source_head,"envelope_id":envelope_id,"workload_root":workload_root,"transfer_root":transfer_root,"ranking_categories":sorted(cats),"ranking_sample_count":sum(s.ranking_eligible for s in self.samples),"control_sample_count":sum(not s.ranking_eligible for s in self.samples),"transfer_count":len(self.transfers),"demand_transfer_count":demand_n,"speculative_transfer_count":spec_n,"total_bytes":total_b,"demand_bytes":demand_b,"speculative_bytes":spec_b,"total_modeled_energy_j":_dstr(total_e),"demand_modeled_energy_j":_dstr(demand_e),"speculative_modeled_energy_j":_dstr(spec_e),"speculative_energy_budget_j":_dstr(budget),"speculative_energy_remaining_j":_dstr(budget-spec_e),"policy_ranking_eligible":True,"effect_authority":False,"gate10":False}
        body["result_root"]=digest(body)
        return body

    @property
    def projection_root(self) -> str:
        return digest({"parent":"AGENT_07","semantic_commit":self.semantic_commit,"verifier_blob":self.verifier_blob,"receipt":self.independently_compile()})


@dataclass(frozen=True)
class EfficiencyReuseEvidence:
    claim_id: str
    claim_generation: str
    proved_proof_projection_root: str
    proved_cost_projection_root: str
    proof: ProofParentEvidence
    cost: CostParentEvidence
    authority_requested: bool = False


@dataclass(frozen=True)
class Receipt:
    schema: str
    claim_id: str
    claim_generation: str
    decision: Decision
    reasons: tuple[str, ...]
    proof_projection_root: str
    cost_projection_root: str
    context_root: str
    fresh_hosted_pass: bool = False
    truth_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    @property
    def receipt_root(self) -> str:
        d=asdict(self); d["decision"]=self.decision.value; return digest(d)


def assess(e: EfficiencyReuseEvidence, context5: Sequence[int] = (1,1,1,1,1)) -> Receipt:
    if len(context5)!=5 or any(type(v) is not int or v not in (0,1,2) for v in context5):
        raise GateError("INVALID_CONTEXT5")
    ctx=digest({"context5":list(context5)})
    reasons=[]
    if not _nonempty(e.claim_id) or not _nonempty(e.claim_generation) or not _hex64(e.proved_proof_projection_root) or not _hex64(e.proved_cost_projection_root) or type(e.authority_requested) is not bool:
        reasons.append("INVALID_SHAPE")
    if e.authority_requested: reasons.append("AUTHORITY_REQUESTED")
    try: proof_root=e.proof.projection_root
    except (AttributeError,GateError,TypeError,ValueError): proof_root=digest({"invalid":"proof"}); reasons.append("PROOF_PARENT_INVALID")
    try: cost_root=e.cost.projection_root
    except (AttributeError,GateError,TypeError,ValueError): cost_root=digest({"invalid":"cost"}); reasons.append("COST_PARENT_INVALID")
    if proof_root != e.proved_proof_projection_root: reasons.append("PROOF_PARENT_DRIFT")
    if cost_root != e.proved_cost_projection_root: reasons.append("COST_PARENT_DRIFT")
    decision=Decision.REUSE_EXACT if not reasons else Decision.REPROVE
    return Receipt(RECEIPT_SCHEMA,e.claim_id if _nonempty(e.claim_id) else "INVALID",e.claim_generation if _nonempty(e.claim_generation) else "INVALID",decision,tuple(reasons) or ("OK",),proof_root,cost_root,ctx)


def verify_receipt(e: EfficiencyReuseEvidence, r: Receipt, context5: Sequence[int]=(1,1,1,1,1)) -> bool:
    return r == assess(e, context5)


def recontextualize(receipt: Receipt, context5: Sequence[int]) -> Receipt:
    """Bind a previously adjudicated receipt to a new routing/context tail without reopening hard axes."""
    if len(context5)!=5 or any(type(v) is not int or v not in (0,1,2) for v in context5):
        raise GateError("INVALID_CONTEXT5")
    return replace(receipt, context_root=digest({"context5":list(context5)}))


def crystalline_admission(omega8: Sequence[int]) -> bool:
    if len(omega8)!=8 or any(type(v) is not int or v not in (0,1,2) for v in omega8): raise GateError("INVALID_OMEGA8")
    return tuple(omega8)==(2,2,2,2,2,2,2,1)


def admission_13d(omega8: Sequence[int], context5: Sequence[int]) -> bool:
    if len(context5)!=5 or any(type(v) is not int or v not in (0,1,2) for v in context5): raise GateError("INVALID_CONTEXT5")
    _ = digest({"context5":list(context5)})
    return crystalline_admission(omega8)


def valid_evidence() -> EfficiencyReuseEvidence:
    h=lambda x:digest({"w":x})
    p=ProofParentEvidence(PROOF_PARENT_SEMANTIC_COMMIT,PROOF_PARENT_SOURCE_BLOB,CURRENT_BASE_HEAD,CURRENT_BASE_HEAD,h("result"),h("result"),"wf-g1","wf-g1",h("input"),h("input"),h("dep"),h("dep"),h("steps"),h("steps"),1,1,h("trace"),h("trace"),h("env"),h("env"),h("budget"),h("budget"),h("schema"),h("schema"),h("event"),h("event"),h("event"),h("budget-proof"),h("budget-proof"),h("oracle"),h("oracle"),h("exec"),h("exec"),h("fused"),h("fused"))
    samples=(WorkloadSample("s1","code","code-prefix",True),WorkloadSample("s2","reasoning","reason-prefix",True),WorkloadSample("c1","control","code-prefix",False,"shared-control"))
    transfers=(TransferCharge("t1",1,"s1","DEMAND",1000),TransferCharge("t2",2,"s2","SPECULATIVE",200))
    env=CostEnvelope(CURRENT_BASE_HEAD,"rt-g1","hw-g1","bench-g1","2.4","0.05")
    c=CostParentEvidence(COST_PARENT_SEMANTIC_COMMIT,COST_PARENT_SOURCE_BLOB,samples,transfers,env)
    return EfficiencyReuseEvidence("moe-efficiency-credit","claim-g2",p.projection_root,c.projection_root,p,c,False)
