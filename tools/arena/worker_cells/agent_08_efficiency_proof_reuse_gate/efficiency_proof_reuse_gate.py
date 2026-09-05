from __future__ import annotations
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
import json, re
from pathlib import PurePosixPath
from typing import Any, Iterable, Sequence

SCHEMA='AURA-WQ-EFFICIENCY-PROOF-REUSE-v3'
RECEIPT_SCHEMA=SCHEMA+'-RECEIPT'
PROOF_PARENT_SEMANTIC_COMMIT='955267f7884a1cc4c4a91ccf95dd084afa329798'
PROOF_PARENT_SOURCE_BLOB='0e886c41e21254445dfa68ce3813698c48bb1fad'
COST_PARENT_SEMANTIC_COMMIT='09302691da7292ac2e2b75a0e9c5d6409848f609'
COST_PARENT_SOURCE_BLOB='dbfc655897e3402517ba978b0856ea8a96595b0f'
CURRENT_BASE_HEAD='7a2c7a16f845752ffb7c16c68636d8d542ecd72e'
RESOURCE_TRACE_REPLAY_BENCHMARK='RESOURCE_TRACE_REPLAY_BENCHMARK'
DEFAULT_GENERATED_ALLOWLIST=frozenset({'.aura/CODEMAP.json','.aura/CODEMAP.md'})
_HEX40=re.compile(r'^[0-9a-f]{40}$'); _HEX64=re.compile(r'^[0-9a-f]{64}$')

class GateError(ValueError): pass
class Decision(str,Enum): REUSE_EXACT='REUSE_EXACT'; REPROVE='REPROVE'
class ParentAdmission(str,Enum): REUSE_EXACT='REUSE_EXACT'; ELIGIBLE_BY_PROOF_NEUTRAL_REBIND='ELIGIBLE_BY_PROOF_NEUTRAL_REBIND'; REPROVE='REPROVE'

def canonical_bytes(v:Any)->bytes:
    try:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    except (TypeError,ValueError) as e: raise GateError('NON_CANONICAL_VALUE') from e

def digest(v:Any)->str:return sha256(canonical_bytes(v)).hexdigest()
def _nonempty(v): return isinstance(v,str) and bool(v)
def _hex40(v): return isinstance(v,str) and _HEX40.fullmatch(v) is not None
def _hex64(v): return isinstance(v,str) and _HEX64.fullmatch(v) is not None

def _canonical_paths(paths:Iterable[str])->tuple[str,...]:
    out=set()
    for raw in paths:
        if not isinstance(raw,str) or not raw or '\\' in raw: raise GateError('INVALID_PATH')
        p=PurePosixPath(raw)
        if p.is_absolute() or '..' in p.parts or str(p) in {'','.'}: raise GateError('INVALID_PATH')
        out.add(str(p))
    return tuple(sorted(out))

def allowlist_root(allowlist:Iterable[str]=DEFAULT_GENERATED_ALLOWLIST)->str:return digest(_canonical_paths(allowlist))

def _dec(v:Any,name:str)->Decimal:
    if not isinstance(v,str) or not v: raise GateError(f'INVALID_DECIMAL:{name}')
    try:o=Decimal(v)
    except (InvalidOperation,ValueError) as e: raise GateError(f'INVALID_DECIMAL:{name}') from e
    if not o.is_finite() or o<0: raise GateError(f'INVALID_DECIMAL:{name}')
    return o

def _dstr(v:Decimal)->str:return '0' if v==0 else format(v.normalize(),'f')

@dataclass(frozen=True)
class ProofParentEvidence:
    semantic_commit:str; verifier_blob:str
    proved_source_head:str; current_source_head:str
    proved_result_root:str; expected_result_root:str
    proved_workflow_generation:str; expected_workflow_generation:str
    proved_input_root:str; expected_input_root:str
    proved_dependency_root:str; expected_dependency_root:str
    proved_required_step_root:str; expected_required_step_root:str
    proved_binding_generation:int; expected_binding_generation:int
    internal_receipt_valid:bool; source_truth_bound:bool; required_steps_complete:bool
    direct_child_verified:bool=False; trusted_generator_verified:bool=False
    changed_paths:tuple[str,...]=(); authority_requested:bool=False
    claim_scope:str=RESOURCE_TRACE_REPLAY_BENCHMARK
    proved_trace_root:str='NA'; expected_trace_root:str='NA'
    proved_environment_root:str='NA'; expected_environment_root:str='NA'
    proved_resource_budget_root:str='NA'; expected_resource_budget_root:str='NA'
    cumulative_resource_budget_verified:bool=True; benchmark_oracle_ceiling_verified:bool=True
    proved_trace_schema_root:str='NA'; expected_trace_schema_root:str='NA'
    proved_event_root:str='NA'; expected_event_root:str='NA'; reconstructed_event_root:str='NA'
    canonical_trace_schema_verified:bool=False; execution_source_provenance_verified:bool=False; fused_event_structure_verified:bool=False
    rebind_parent_head:str='NA'; rebind_child_head:str='NA'; observed_generator_identity:str='NA'; expected_generator_identity:str='NA'
    provider_observation_root:str='NA'; expected_provider_observation_root:str='NA'; provider_observation_verified:bool=False

    def parent_payload(self)->dict[str,Any]:
        d=asdict(self); d.pop('semantic_commit'); d.pop('verifier_blob'); return d

    def validate_shape(self)->bool:
        # Exact pinned verifier requires every identity-bearing string field to be a concrete string.
        strings=(self.proved_source_head,self.current_source_head,self.proved_result_root,self.expected_result_root,
            self.proved_workflow_generation,self.expected_workflow_generation,self.proved_input_root,self.expected_input_root,
            self.proved_dependency_root,self.expected_dependency_root,self.proved_required_step_root,self.expected_required_step_root,
            self.claim_scope,self.proved_trace_root,self.expected_trace_root,self.proved_environment_root,self.expected_environment_root,
            self.proved_resource_budget_root,self.expected_resource_budget_root,self.proved_trace_schema_root,self.expected_trace_schema_root,
            self.proved_event_root,self.expected_event_root,self.reconstructed_event_root,self.rebind_parent_head,self.rebind_child_head,
            self.observed_generator_identity,self.expected_generator_identity,self.provider_observation_root,self.expected_provider_observation_root)
        if not all(_nonempty(x) for x in strings): return False
        if type(self.proved_binding_generation) is not int or type(self.expected_binding_generation) is not int or min(self.proved_binding_generation,self.expected_binding_generation)<0:return False
        bool_fields=(self.internal_receipt_valid,self.source_truth_bound,self.required_steps_complete,self.direct_child_verified,self.trusted_generator_verified,self.authority_requested,self.cumulative_resource_budget_verified,self.benchmark_oracle_ceiling_verified,self.canonical_trace_schema_verified,self.execution_source_provenance_verified,self.fused_event_structure_verified,self.provider_observation_verified)
        if not all(type(x) is bool for x in bool_fields): return False
        if self.claim_scope != RESOURCE_TRACE_REPLAY_BENCHMARK:return False
        required=(self.proved_trace_root,self.expected_trace_root,self.proved_environment_root,self.expected_environment_root,self.proved_resource_budget_root,self.expected_resource_budget_root,self.proved_trace_schema_root,self.expected_trace_schema_root,self.proved_event_root,self.expected_event_root,self.reconstructed_event_root)
        return all(x!='NA' for x in required)

    def proof_truth_exact(self)->bool:
        if not self.validate_shape(): return False
        return (self.internal_receipt_valid and self.source_truth_bound and self.required_steps_complete
            and self.proved_result_root==self.expected_result_root
            and self.proved_workflow_generation==self.expected_workflow_generation
            and self.proved_input_root==self.expected_input_root
            and self.proved_dependency_root==self.expected_dependency_root
            and self.proved_required_step_root==self.expected_required_step_root
            and self.proved_binding_generation==self.expected_binding_generation
            and self.proved_trace_root==self.expected_trace_root
            and self.proved_environment_root==self.expected_environment_root
            and self.proved_resource_budget_root==self.expected_resource_budget_root
            and self.cumulative_resource_budget_verified and self.benchmark_oracle_ceiling_verified
            and self.proved_trace_schema_root==self.expected_trace_schema_root
            and self.proved_event_root==self.expected_event_root==self.reconstructed_event_root
            and self.canonical_trace_schema_verified and self.execution_source_provenance_verified and self.fused_event_structure_verified
            and not self.authority_requested)

    def parent_decision(self)->ParentAdmission:
        # AGENT_08 intentionally supports only the parent's exact-reuse branch; generated-child rebind remains upstream debt.
        if not self.proof_truth_exact(): return ParentAdmission.REPROVE
        try: changed=_canonical_paths(self.changed_paths)
        except GateError:return ParentAdmission.REPROVE
        if self.proved_source_head==self.current_source_head:
            return ParentAdmission.REUSE_EXACT if not changed else ParentAdmission.REPROVE
        return ParentAdmission.REPROVE

    def parent_evidence_root(self)->str:
        # Exact key set and values used by the pinned AGENT_27 evidence_digest.
        p=self.parent_payload(); p['changed_paths']=_canonical_paths(self.changed_paths)
        return digest(p)

    def parent_receipt(self)->dict[str,Any]:
        paths=_canonical_paths(self.changed_paths)
        return {'decision':self.parent_decision().value,'evidence_root':self.parent_evidence_root(),'changed_path_root':digest(paths),'allowlist_root':allowlist_root(),'fresh_hosted_pass':False,'authority':False}

    @property
    def projection_root(self)->str:
        if self.semantic_commit!=PROOF_PARENT_SEMANTIC_COMMIT or self.verifier_blob!=PROOF_PARENT_SOURCE_BLOB: raise GateError('PROOF_PARENT_GENERATION_DRIFT')
        if self.proved_source_head!=CURRENT_BASE_HEAD or self.current_source_head!=CURRENT_BASE_HEAD: raise GateError('SOURCE_HEAD_DRIFT')
        if self.parent_decision()!=ParentAdmission.REUSE_EXACT: raise GateError('PROOF_PARENT_REPROVE')
        return digest({'parent':'AGENT_27','semantic_commit':self.semantic_commit,'verifier_blob':self.verifier_blob,'receipt':self.parent_receipt()})

@dataclass(frozen=True)
class WorkloadSample:
    sample_id:str; category:str; rendered_prefix:str; ranking_eligible:bool; control_group:str|None=None
    def canonical(self):return asdict(self)
@dataclass(frozen=True)
class TransferCharge:
    transfer_id:str; sequence:int; sample_id:str; kind:str; bytes_moved:int
    def canonical(self):return asdict(self)
@dataclass(frozen=True)
class CostEnvelope:
    source_head:str; runtime_generation:str; hardware_fingerprint:str; benchmark_generation:str
    joules_per_gb:str; speculative_energy_budget_j:str; bytes_per_gb:int=1_000_000_000
    effect_authority:bool=False; gate10:bool=False
    def canonical(self):return asdict(self)

@dataclass(frozen=True)
class CostParentEvidence:
    semantic_commit:str; verifier_blob:str; samples:tuple[WorkloadSample,...]; transfers:tuple[TransferCharge,...]; envelope:CostEnvelope
    def independently_compile(self)->dict[str,Any]:
        if self.semantic_commit!=COST_PARENT_SEMANTIC_COMMIT or self.verifier_blob!=COST_PARENT_SOURCE_BLOB:raise GateError('COST_PARENT_GENERATION_DRIFT')
        if type(self.samples) is not tuple or not self.samples:raise GateError('EMPTY_WORKLOAD')
        if type(self.transfers) is not tuple:raise GateError('INVALID_TRANSFERS')
        if type(self.envelope) is not CostEnvelope:raise GateError('INVALID_ENVELOPE')
        e=self.envelope
        if not _hex40(e.source_head) or e.source_head!=CURRENT_BASE_HEAD:raise GateError('SOURCE_HEAD_DRIFT')
        for v in (e.runtime_generation,e.hardware_fingerprint,e.benchmark_generation):
            if not _nonempty(v):raise GateError('INVALID_ENVELOPE_IDENTITY')
        if type(e.bytes_per_gb) is not int or e.bytes_per_gb<1:raise GateError('INVALID_BYTES_PER_GB')
        if e.effect_authority is not False or e.gate10 is not False:raise GateError('D0_AUTHORITY_ESCALATION')
        rate=_dec(e.joules_per_gb,'joules_per_gb'); budget=_dec(e.speculative_energy_budget_j,'speculative_energy_budget_j')
        ids=set(); ranking_by_prefix={}; cats=set()
        for s in self.samples:
            if type(s) is not WorkloadSample or not all(_nonempty(x) for x in (s.sample_id,s.category,s.rendered_prefix)) or type(s.ranking_eligible) is not bool:raise GateError('INVALID_SAMPLE')
            if s.sample_id in ids:raise GateError('DUPLICATE_SAMPLE_ID')
            ids.add(s.sample_id)
            if s.ranking_eligible:
                if s.control_group is not None:raise GateError('RANKING_SAMPLE_CANNOT_BE_CONTROL')
                cats.add(s.category);ranking_by_prefix.setdefault(s.rendered_prefix,set()).add(s.category)
            elif not _nonempty(s.control_group):raise GateError('CONTROL_GROUP_REQUIRED')
        if len(cats)<2:raise GateError('NEED_AT_LEAST_TWO_RANKING_CATEGORIES')
        if any(len(v)>1 for v in ranking_by_prefix.values()):raise GateError('CROSS_CATEGORY_EXACT_PREFIX_COLLISION')
        seen=set();db=sb=dn=sn=0
        for expected,t in enumerate(self.transfers,1):
            if type(t) is not TransferCharge or not _nonempty(t.transfer_id) or t.transfer_id in seen:raise GateError('DUPLICATE_PHYSICAL_TRANSFER_ID')
            seen.add(t.transfer_id)
            if type(t.sequence) is not int or t.sequence!=expected:raise GateError('NONCONTIGUOUS_TRANSFER_SEQUENCE')
            if t.sample_id not in ids:raise GateError('TRANSFER_UNKNOWN_SAMPLE')
            if t.kind not in {'DEMAND','SPECULATIVE'}:raise GateError('INVALID_TRANSFER_KIND')
            if type(t.bytes_moved) is not int or t.bytes_moved<1:raise GateError('INVALID_TRANSFER_BYTES')
            if t.kind=='DEMAND':db+=t.bytes_moved;dn+=1
            else:sb+=t.bytes_moved;sn+=1
        total=db+sb; te=Decimal(total)*rate/Decimal(e.bytes_per_gb); de=Decimal(db)*rate/Decimal(e.bytes_per_gb); se=Decimal(sb)*rate/Decimal(e.bytes_per_gb)
        if se>budget:raise GateError('CUMULATIVE_SPECULATIVE_ENERGY_BUDGET_EXCEEDED')
        base={'schema':'AURA-WORKLOAD-QUALIFIED-COST-RECEIPT-v1','source_head':e.source_head,'envelope_id':digest(e.canonical()),'workload_root':digest([s.canonical() for s in self.samples]),'transfer_root':digest([t.canonical() for t in self.transfers]),'ranking_categories':tuple(sorted(cats)),'ranking_sample_count':sum(1 for s in self.samples if s.ranking_eligible),'control_sample_count':sum(1 for s in self.samples if not s.ranking_eligible),'transfer_count':len(self.transfers),'demand_transfer_count':dn,'speculative_transfer_count':sn,'total_bytes':total,'demand_bytes':db,'speculative_bytes':sb,'total_modeled_energy_j':_dstr(te),'demand_modeled_energy_j':_dstr(de),'speculative_modeled_energy_j':_dstr(se),'speculative_energy_budget_j':_dstr(budget),'speculative_energy_remaining_j':_dstr(budget-se),'policy_ranking_eligible':True,'effect_authority':False,'gate10':False}
        return {**base,'result_root':digest(base)}
    @property
    def projection_root(self)->str:return digest({'parent':'AGENT_07','semantic_commit':self.semantic_commit,'verifier_blob':self.verifier_blob,'receipt':self.independently_compile()})

@dataclass(frozen=True)
class EfficiencyReuseEvidence:
    claim_id:str; claim_generation:str; proved_proof_projection_root:str; proved_cost_projection_root:str; proof:ProofParentEvidence; cost:CostParentEvidence; authority_requested:bool=False
@dataclass(frozen=True)
class Receipt:
    schema:str; claim_id:str; claim_generation:str; decision:Decision; reasons:tuple[str,...]; proof_projection_root:str; cost_projection_root:str; context_root:str
    fresh_hosted_pass:bool=False; truth_authority:bool=False; effect_authority:bool=False; gate10:bool=False
    @property
    def receipt_root(self):
        d=asdict(self);d['decision']=self.decision.value;return digest(d)

def assess(e:EfficiencyReuseEvidence,context5:Sequence[int]=(1,1,1,1,1))->Receipt:
    if len(context5)!=5 or any(type(v) is not int or v not in (0,1,2) for v in context5):raise GateError('INVALID_CONTEXT5')
    reasons=[];ctx=digest({'context5':list(context5)})
    if not _nonempty(e.claim_id) or not _nonempty(e.claim_generation) or not _hex64(e.proved_proof_projection_root) or not _hex64(e.proved_cost_projection_root) or type(e.authority_requested) is not bool:reasons.append('INVALID_SHAPE')
    if e.authority_requested:reasons.append('AUTHORITY_REQUESTED')
    try:pr=e.proof.projection_root
    except Exception:pr=digest({'invalid':'proof'});reasons.append('PROOF_PARENT_INVALID')
    try:cr=e.cost.projection_root
    except Exception:cr=digest({'invalid':'cost'});reasons.append('COST_PARENT_INVALID')
    if pr!=e.proved_proof_projection_root:reasons.append('PROOF_PARENT_DRIFT')
    if cr!=e.proved_cost_projection_root:reasons.append('COST_PARENT_DRIFT')
    dec=Decision.REUSE_EXACT if not reasons else Decision.REPROVE
    return Receipt(RECEIPT_SCHEMA,e.claim_id if _nonempty(e.claim_id) else 'INVALID',e.claim_generation if _nonempty(e.claim_generation) else 'INVALID',dec,tuple(reasons) or ('OK',),pr,cr,ctx)
def verify_receipt(e,r,context5=(1,1,1,1,1)):return r==assess(e,context5)
def recontextualize(r:Receipt,context5:Sequence[int])->Receipt:
    if len(context5)!=5 or any(type(v) is not int or v not in (0,1,2) for v in context5):raise GateError('INVALID_CONTEXT5')
    return replace(r,context_root=digest({'context5':list(context5)}))
def crystalline_admission(omega8:Sequence[int])->bool:
    if len(omega8)!=8 or any(type(v) is not int or v not in (0,1,2) for v in omega8):raise GateError('INVALID_OMEGA8')
    return tuple(omega8)==(2,2,2,2,2,2,2,1)
def admission_13d(omega8,routing5):
    if len(routing5)!=5 or any(type(v) is not int or v not in (0,1,2) for v in routing5):raise GateError('INVALID_ROUTING5')
    return crystalline_admission(omega8)
