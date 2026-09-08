"""D0 GLM-5.3 × AirLLM v4 paged streamed-training reference.

Nonpromoting control plane only. It does not execute GLM-5.3 or authorize G2/Gate10.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib, json

AIRLLM_V4_TAG="v4.0.0"
AIRLLM_V4_SEMANTIC_COMMIT="ff35db207a0c559af9aa95d686057c3fe84f1d40"
AIRLLM_OBSERVED_HEAD="430adb15ee32b570063835176c10b3a8ac974d90"
AIRLLM_PREVIOUS_AURA_PIN="55e435087d951da8c25ab3672e969025241a398e"
GLM_EXPERT_CLASS="GlmMoeDsaExperts"
UPSTREAM_PACKED_LORA_CLASS="Qwen4ExpTextExperts"

class Decision(str,Enum):
    BLOCK_SOURCE="BLOCK_SOURCE"; BLOCK_SECURITY="BLOCK_SECURITY"; BLOCK_EXPERT_ABI="BLOCK_EXPERT_ABI"
    BLOCK_ROUTER="BLOCK_ROUTER"; BLOCK_PAGER="BLOCK_PAGER"; BLOCK_REPLAY="BLOCK_REPLAY"
    BLOCK_ADAPTER_RESIDENCY="BLOCK_ADAPTER_RESIDENCY"; HOLD_EMPIRICAL="HOLD_EMPIRICAL"

@dataclass(frozen=True)
class Geometry:
    layers:int=78; first_dense_layers:int=3; experts:int=256; top_k:int=8; hidden:int=6144; intermediate:int=2048
    @property
    def sparse_layers(self): return self.layers-self.first_dense_layers
    def expert_bytes(self,n=1): return n*((2*self.intermediate)*self.hidden+self.hidden*self.intermediate)
    def lora_params(self,rank,layers=None): return (self.sparse_layers if layers is None else layers)*self.experts*rank*(2*self.hidden+3*self.intermediate)

@dataclass(frozen=True)
class Source:
    semantic_tag:str; semantic_commit:str; training_surface_digest:str; hard_false_digest:str; model_revision:str; index_digest:str; pager_binding:str
    upstream_remote_fallback:bool=True

@dataclass(frozen=True)
class ABI:
    expert_class:str; experts_interface:bool; experts:int; hidden:int; intermediate:int; native_router:bool; selected_pager:bool; fp8_scales_with_pages:bool

@dataclass(frozen=True)
class Policy:
    backward_recompute:bool; use_cache:bool; gradient_checkpointing:bool; dropout:float; route_replay_identity:bool
    rank:int; resident_adapter_budget:int; adapter_paging_or_layer_locality:bool

@dataclass(frozen=True)
class PortReceipt:
    decision:Decision; reason:str; logical_full_bank_bytes:int; logical_top8_bytes:int; logical_top8_reduction:float
    full_sparse_lora_params:int; full_sparse_lora_bf16_bytes:int; source_root:str; claim_ceiling:str="D0_NONPROMOTING"

@dataclass(frozen=True)
class ForwardLease:
    attempt:str; layer:int; route:tuple[int,...]; route_root:str; source_root:str; adapter_generation:str; optimizer_generation:str; pages:tuple[int,...]; root:str

@dataclass(frozen=True)
class ChunkLease:
    chunk_tokens:int|None; peak_declared_bytes:int|None; total_logical_expert_bytes:int|None; physical_io_bytes:int|None; physical_time_seconds:float|None; reason:str
    claim_ceiling:str="D0_LOGICAL_PLAN_ONLY"

def _h(x):
    if hasattr(x,"__dataclass_fields__"): x=asdict(x)
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def route_union(rows,experts=256):
    ids=tuple(sorted({int(x) for row in rows for x in row}))
    if not ids: raise ValueError("empty_native_route")
    if ids[0]<0 or ids[-1]>=experts: raise ValueError("expert_out_of_range")
    return ids

def route_root(rows,*,layer,pager_binding): return _h({"layer":int(layer),"pager":pager_binding,"native":route_union(rows)})

def assess(source:Source,abi:ABI,policy:Policy,g=Geometry()):
    full=g.expert_bytes(g.experts); top=g.expert_bytes(g.top_k); lora=g.lora_params(policy.rank); lora_bytes=2*lora
    if source.semantic_tag!=AIRLLM_V4_TAG or source.semantic_commit!=AIRLLM_V4_SEMANTIC_COMMIT:
        d,r=Decision.BLOCK_SOURCE,"AirLLM v4 streamed-training semantic generation not bound"
    elif source.upstream_remote_fallback and not source.hard_false_digest:
        d,r=Decision.BLOCK_SECURITY,"Aura hard-false source membrane required"
    elif not (abi.expert_class==GLM_EXPERT_CLASS and abi.experts_interface and abi.experts==g.experts and abi.hidden==g.hidden and abi.intermediate==g.intermediate):
        d,r=Decision.BLOCK_EXPERT_ABI,"Qwen packed-LoRA class identity cannot stand in for GLM ExpertsInterface ABI"
    elif not abi.native_router: d,r=Decision.BLOCK_ROUTER,"native GLM router must own top-k"
    elif not (abi.selected_pager and abi.fp8_scales_with_pages): d,r=Decision.BLOCK_PAGER,"selected base expert + FP8 scale pages must be source-bound"
    elif not (policy.backward_recompute and not policy.use_cache and not policy.gradient_checkpointing and policy.dropout==0 and policy.route_replay_identity):
        d,r=Decision.BLOCK_REPLAY,"backward recompute must replay exact forward native route"
    elif lora_bytes>policy.resident_adapter_budget and not policy.adapter_paging_or_layer_locality:
        d,r=Decision.BLOCK_ADAPTER_RESIDENCY,"all-expert/all-layer packed LoRA residency exceeds declared budget"
    else: d,r=Decision.HOLD_EMPIRICAL,"static adapter/pager contract closes only to tiny FP8 + owner-host empirical validation"
    return PortReceipt(d,r,full,top,1-top/full,lora,lora_bytes,_h(source))

def mint_forward_lease(source:Source,rows,*,attempt,layer,adapter_generation,optimizer_generation):
    ids=route_union(rows); sr=_h(source); rr=route_root([ids],layer=layer,pager_binding=source.pager_binding)
    root=_h({"attempt":attempt,"layer":layer,"route":ids,"rr":rr,"sr":sr,"adapter":adapter_generation,"optim":optimizer_generation,"pages":ids})
    return ForwardLease(attempt,layer,ids,rr,sr,adapter_generation,optimizer_generation,ids,root)

def backward_ready(lease:ForwardLease,source:Source,rows,*,attempt,adapter_generation,optimizer_generation,pages):
    ids=route_union(rows); pp=tuple(sorted({int(x) for x in pages}))
    return (_h(source)==lease.source_root and attempt==lease.attempt and adapter_generation==lease.adapter_generation
            and optimizer_generation==lease.optimizer_generation and ids==lease.route and pp==lease.pages
            and route_root([ids],layer=lease.layer,pager_binding=source.pager_binding)==lease.route_root)

def _chunk_counts(rows,c): return [len(route_union(rows[s:s+c])) for s in range(0,len(rows),c)]
def choose_chunk(rows,*,device_budget,reserved_nonexpert,rank=16,candidates=(1,2,4,8,16,32,64,128,256,512),g=Geometry()):
    rows=[tuple(int(x) for x in r) for r in rows]
    if not rows: raise ValueError("empty_route_matrix")
    available=int(device_budget)-int(reserved_nonexpert); expert_bytes=g.expert_bytes(1)
    adapter_working_per_expert=rank*(2*g.hidden+3*g.intermediate)*2*4 # params+grad+2 declared Adam tensors
    feasible=[]
    for c in sorted(set(int(x) for x in candidates if 0<int(x)<=len(rows))):
        counts=_chunk_counts(rows,c); peak=max(counts); total=sum(counts)*expert_bytes; working=peak*(expert_bytes+adapter_working_per_expert)
        if working<=available: feasible.append((total,-c,c,working))
    if not feasible: return ChunkLease(None,None,None,None,None,"no exact chunk candidate fits declared logical working-set budget")
    total,_,c,working=min(feasible)
    return ChunkLease(c,working,total,None,None,"logical exact plan only; physical I/O requires independent attestation")

def default_source(): return Source(AIRLLM_V4_TAG,AIRLLM_V4_SEMANTIC_COMMIT,"airllm-v4-training-files","aura-hard-false","glm53-rev","glm53-index","pager-binding")
def default_abi(): return ABI(GLM_EXPERT_CLASS,True,256,6144,2048,True,True,True)
def default_policy(): return Policy(True,False,False,0.0,True,16,6*1024**3,False)
