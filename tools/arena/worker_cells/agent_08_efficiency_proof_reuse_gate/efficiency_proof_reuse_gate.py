from __future__ import annotations
from dataclasses import asdict, dataclass, replace
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Sequence

SCHEMA="AURA-WQ-EFFICIENCY-PROOF-REUSE-v1"; RECEIPT_SCHEMA=SCHEMA+"-RECEIPT"
class GateError(ValueError): pass
class Decision(str,Enum):
    REUSE_EXACT="REUSE_EXACT"; ELIGIBLE_BY_PROOF_NEUTRAL_REBIND="ELIGIBLE_BY_PROOF_NEUTRAL_REBIND"; REPROVE="REPROVE"

def digest(x:Any)->str:
    try: b=json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
    except (TypeError,ValueError) as e: raise GateError("NON_CANONICAL_VALUE") from e
    return sha256(b).hexdigest()
def nonempty(x): return isinstance(x,str) and bool(x)

@dataclass(frozen=True)
class ProofWitness:
    receipt_root:str; expected_receipt_root:str; evidence_root:str; decision:Decision
    receipt_valid:bool; trace_provenance_bound:bool
    def valid(self):
        return all(map(nonempty,(self.receipt_root,self.expected_receipt_root,self.evidence_root))) and isinstance(self.decision,Decision) and all(type(x) is bool for x in (self.receipt_valid,self.trace_provenance_bound))

@dataclass(frozen=True)
class CostWitness:
    receipt_root:str; expected_receipt_root:str; source_head:str; expected_source_head:str
    workload_root:str; expected_workload_root:str; transfer_root:str; expected_transfer_root:str
    envelope_id:str; expected_envelope_id:str; result_root:str; expected_result_root:str
    benchmark_generation:str; expected_benchmark_generation:str
    receipt_valid:bool; policy_ranking_eligible:bool; exact_cumulative_cost_verified:bool; source_current:bool
    def valid(self):
        vals=(self.receipt_root,self.expected_receipt_root,self.source_head,self.expected_source_head,self.workload_root,self.expected_workload_root,self.transfer_root,self.expected_transfer_root,self.envelope_id,self.expected_envelope_id,self.result_root,self.expected_result_root,self.benchmark_generation,self.expected_benchmark_generation)
        flags=(self.receipt_valid,self.policy_ranking_eligible,self.exact_cumulative_cost_verified,self.source_current)
        return all(map(nonempty,vals)) and all(type(x) is bool for x in flags)

@dataclass(frozen=True)
class Evidence:
    claim_id:str; claim_generation:str; proof:ProofWitness; cost:CostWitness; authority_requested:bool=False
    def valid(self): return nonempty(self.claim_id) and nonempty(self.claim_generation) and type(self.proof) is ProofWitness and type(self.cost) is CostWitness and self.proof.valid() and self.cost.valid() and type(self.authority_requested) is bool

@dataclass(frozen=True)
class Receipt:
    schema:str; claim_id:str; claim_generation:str; decision:Decision; reasons:tuple[str,...]; evidence_root:str
    proof_receipt_root:str; qualified_cost_receipt_root:str
    fresh_hosted_pass:bool=False; truth_authority:bool=False; effect_authority:bool=False; gate10:bool=False
    @property
    def receipt_root(self):
        d=asdict(self); d["decision"]=self.decision.value; return digest(d)

DRIFTS=(("source_head","expected_source_head","SOURCE_HEAD_DRIFT"),("workload_root","expected_workload_root","WORKLOAD_ROOT_DRIFT"),("transfer_root","expected_transfer_root","TRANSFER_ROOT_DRIFT"),("envelope_id","expected_envelope_id","ENVELOPE_ID_DRIFT"),("result_root","expected_result_root","COST_RESULT_ROOT_DRIFT"),("benchmark_generation","expected_benchmark_generation","BENCHMARK_GENERATION_DRIFT"),("receipt_root","expected_receipt_root","COST_RECEIPT_ROOT_DRIFT"))

def reasons(e:Evidence)->tuple[str,...]:
    if not e.valid(): return ("INVALID_SHAPE",)
    out=[]; p=e.proof; c=e.cost
    if e.authority_requested: out.append("AUTHORITY_REQUESTED")
    if not p.receipt_valid or not p.trace_provenance_bound: out.append("PARENT_PROOF_REUSE_INVALID")
    if p.decision not in {Decision.REUSE_EXACT,Decision.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND}: out.append("PARENT_PROOF_REUSE_NOT_ELIGIBLE")
    if p.receipt_root!=p.expected_receipt_root: out.append("PROOF_RECEIPT_ROOT_DRIFT")
    if not c.receipt_valid: out.append("QUALIFIED_COST_RECEIPT_INVALID")
    if not c.policy_ranking_eligible: out.append("WORKLOAD_NOT_RANKING_ELIGIBLE")
    if not c.exact_cumulative_cost_verified: out.append("CUMULATIVE_COST_NOT_EXACT")
    if not c.source_current: out.append("SOURCE_STALE")
    for a,b,r in DRIFTS:
        if getattr(c,a)!=getattr(c,b): out.append(r)
    return tuple(out) or ("OK",)

def evidence_root(e:Evidence)->str:
    return digest({"schema":SCHEMA,"claim_id":e.claim_id,"claim_generation":e.claim_generation,"proof":{**asdict(e.proof),"decision":e.proof.decision.value},"cost":asdict(e.cost),"authority_requested":e.authority_requested})
def decide(e:Evidence)->Decision:
    rs=reasons(e); return e.proof.decision if rs==("OK",) else Decision.REPROVE
def make_receipt(e:Evidence)->Receipt:
    rs=reasons(e); ok=e.valid()
    return Receipt(RECEIPT_SCHEMA,e.claim_id if nonempty(e.claim_id) else "INVALID",e.claim_generation if nonempty(e.claim_generation) else "INVALID",decide(e),rs,evidence_root(e) if ok else digest({"invalid_shape":True}),e.proof.receipt_root if type(e.proof) is ProofWitness and nonempty(e.proof.receipt_root) else "INVALID",e.cost.receipt_root if type(e.cost) is CostWitness and nonempty(e.cost.receipt_root) else "INVALID")
def verify_receipt(e:Evidence,r:Receipt)->bool: return r==make_receipt(e)
def crystalline_admission(o:Sequence[int])->bool:
    if len(o)!=8 or any(type(v) is not int or v not in (0,1,2) for v in o): raise GateError("INVALID_OMEGA8")
    return tuple(o)==(2,2,2,2,2,2,2,1)
def admission_13d(o:Sequence[int],tail:Sequence[int])->bool:
    if len(tail)!=5 or any(type(v) is not int or v not in (0,1,2) for v in tail): raise GateError("INVALID_ROUTING5")
    return crystalline_admission(o)
def valid_evidence(d:Decision=Decision.REUSE_EXACT)->Evidence:
    pr=digest({"proof":"p"}); cr=digest({"cost":"c"})
    p=ProofWitness(pr,pr,digest({"e":1}),d,True,True)
    c=CostWitness(cr,cr,"src","src","work","work","transfer","transfer","env","env","result","result","bench-g1","bench-g1",True,True,True,True)
    return Evidence("moe-efficiency-credit","claim-g1",p,c,False)
