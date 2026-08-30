"""PCK2: owner-resolved persistent transformer-KV reuse admission (D0 only).

Coordinate/K27 may nominate reuse but is never runtime evidence. This module
does not access cache/model/provider/storage/network resources and grants no
execution, provider, monetary, or promotion authority. HMAC is a deterministic
local trust-root model, not production key management.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum
import hashlib, hmac, json, re
from typing import Any, Mapping

_SHA = re.compile(r"^[0-9a-f]{64}$")
_TOK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")

class KVAdmissionError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code, self.detail = code, detail

class ResponsibilityClass(str, Enum):
    TRANSFORMER_KV_CACHE="TRANSFORMER_KV_CACHE"
    COORDINATE_MEMORY="COORDINATE_MEMORY"
    SEMANTIC_RESPONSE_CACHE="SEMANTIC_RESPONSE_CACHE"

class ResolverDisposition(str, Enum):
    OWNER_RESOLVED_CURRENT="OWNER_RESOLVED_CURRENT"
    OWNER_RESOLVED_HISTORICAL="OWNER_RESOLVED_HISTORICAL"
    OWNER_UNRESOLVED="OWNER_UNRESOLVED"

def _canon(v: Any)->bytes:
    try: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
    except (TypeError,ValueError) as e: raise KVAdmissionError("NONCANONICAL_KV_STATE") from e

def _dig(domain:str,v:Any)->str:
    return hashlib.sha256(domain.encode()+b"\0"+_canon(v)).hexdigest()

def _text(v:Any,code:str)->str:
    if not isinstance(v,str) or not _TOK.fullmatch(v.strip()): raise KVAdmissionError(code)
    return v.strip()

def _sha(v:Any,code:str)->str:
    if not isinstance(v,str) or not _SHA.fullmatch(v.strip().lower()): raise KVAdmissionError(code)
    return v.strip().lower()

def _nn(v:Any,code:str)->int:
    if isinstance(v,bool) or not isinstance(v,int) or v<0: raise KVAdmissionError(code)
    return v

@dataclass(frozen=True)
class PersistentKVReuseTargetV1:
    coordinate_ref:str; k27_cell:int; model_revision:str; tokenizer_digest:str
    chat_template_digest:str; system_tool_prefix_digest:str; prefix_token_digest:str
    cache_abi:str; principal_namespace_digest:str; host_epoch:str; route_epoch:str
    source_generation:str; source_currentness_ref:str
    responsibility:ResponsibilityClass=ResponsibilityClass.TRANSFORMER_KV_CACHE
    schema:str="PersistentKVReuseTargetV1"
    def __post_init__(self):
        if self.schema!="PersistentKVReuseTargetV1": raise KVAdmissionError("KV_TARGET_SCHEMA_MISMATCH")
        object.__setattr__(self,"coordinate_ref",_text(self.coordinate_ref,"COORDINATE_REF_INVALID"))
        if isinstance(self.k27_cell,bool) or not isinstance(self.k27_cell,int) or not 0<=self.k27_cell<27: raise KVAdmissionError("K27_CELL_INVALID")
        for f in ("model_revision","cache_abi","host_epoch","route_epoch","source_generation","source_currentness_ref"):
            object.__setattr__(self,f,_text(getattr(self,f),f"{f.upper()}_INVALID"))
        for f in ("tokenizer_digest","chat_template_digest","system_tool_prefix_digest","prefix_token_digest","principal_namespace_digest"):
            object.__setattr__(self,f,_sha(getattr(self,f),f"{f.upper()}_INVALID"))
        if not isinstance(self.responsibility,ResponsibilityClass): raise KVAdmissionError("RESPONSIBILITY_CLASS_INVALID")
    @property
    def target_digest(self):
        v=asdict(self); v["responsibility"]=self.responsibility.value
        return _dig("AURA_PCK2_TARGET_V1",v)

@dataclass(frozen=True)
class PersistentKVPathEvidenceV1:
    evidence_ref:str; evidence_generation:str; evidence_currentness_ref:str; target_digest:str
    responsibility:ResponsibilityClass; model_revision:str; tokenizer_digest:str
    chat_template_digest:str; system_tool_prefix_digest:str; prefix_token_digest:str
    cache_abi:str; principal_namespace_digest:str; host_epoch:str; route_epoch:str
    persistent_restore_observed:bool; cache_read_observed:bool; cache_hit_tokens:int
    prefill_saved_us:int; transfer_us:int; restore_us:int; queue_penalty_us:int
    memory_penalty_us:int; invalidation_penalty_us:int
    schema:str="PersistentKVPathEvidenceV1"
    def __post_init__(self):
        if self.schema!="PersistentKVPathEvidenceV1": raise KVAdmissionError("KV_PATH_SCHEMA_MISMATCH")
        for f in ("evidence_ref","evidence_generation","evidence_currentness_ref","model_revision","cache_abi","host_epoch","route_epoch"):
            object.__setattr__(self,f,_text(getattr(self,f),f"{f.upper()}_INVALID"))
        for f in ("target_digest","tokenizer_digest","chat_template_digest","system_tool_prefix_digest","prefix_token_digest","principal_namespace_digest"):
            object.__setattr__(self,f,_sha(getattr(self,f),f"{f.upper()}_INVALID"))
        if not isinstance(self.responsibility,ResponsibilityClass): raise KVAdmissionError("PATH_RESPONSIBILITY_INVALID")
        for f in ("persistent_restore_observed","cache_read_observed"):
            if type(getattr(self,f)) is not bool: raise KVAdmissionError(f"{f.upper()}_BOOL_REQUIRED")
        for f in ("cache_hit_tokens","prefill_saved_us","transfer_us","restore_us","queue_penalty_us","memory_penalty_us","invalidation_penalty_us"):
            object.__setattr__(self,f,_nn(getattr(self,f),f"{f.upper()}_INVALID"))
    @property
    def path_digest(self):
        v=asdict(self); v["responsibility"]=self.responsibility.value
        return _dig("AURA_PCK2_PATH_V1",v)
    @property
    def net_reuse_us(self):
        return self.prefill_saved_us-sum((self.transfer_us,self.restore_us,self.queue_penalty_us,self.memory_penalty_us,self.invalidation_penalty_us))

def resolved_projection_payload_digest(target:PersistentKVReuseTargetV1,path:PersistentKVPathEvidenceV1)->str:
    if not isinstance(target,PersistentKVReuseTargetV1) or not isinstance(path,PersistentKVPathEvidenceV1): raise KVAdmissionError("KV_TARGET_AND_PATH_REQUIRED")
    return _dig("AURA_PCK2_RESOLVED_PROJECTION_V1",{"target_digest":target.target_digest,"path_digest":path.path_digest})

@dataclass(frozen=True)
class KVReuseProjectionClaimV1:
    owner_ref:str; owner_generation:str; owner_head:str; owner_blob:str; owner_abi:str
    subject_ref:str; subject_generation:str; source_ref:str; source_generation:str
    source_currentness_ref:str; projection_schema:str; projection_payload_digest:str
    consequence_ceiling:str="TRANSFORMER_KV_REUSE_EVIDENCE_ONLY"
    schema:str="KVReuseProjectionClaimV1"
    def __post_init__(self):
        if self.schema!="KVReuseProjectionClaimV1": raise KVAdmissionError("PROJECTION_CLAIM_SCHEMA_MISMATCH")
        for f in ("owner_ref","owner_generation","owner_abi","subject_ref","subject_generation","source_ref","source_generation","source_currentness_ref","projection_schema","consequence_ceiling"):
            object.__setattr__(self,f,_text(getattr(self,f),f"{f.upper()}_INVALID"))
        object.__setattr__(self,"owner_head",_sha(self.owner_head,"OWNER_HEAD_INVALID"))
        object.__setattr__(self,"owner_blob",_sha(self.owner_blob,"OWNER_BLOB_INVALID"))
        object.__setattr__(self,"projection_payload_digest",_sha(self.projection_payload_digest,"PROJECTION_PAYLOAD_DIGEST_INVALID"))
        if self.consequence_ceiling!="TRANSFORMER_KV_REUSE_EVIDENCE_ONLY": raise KVAdmissionError("PROJECTION_CONSEQUENCE_CEILING_WIDENING")
    @property
    def claim_digest(self): return _dig("AURA_PCK2_CLAIM_V1",asdict(self))

@dataclass(frozen=True)
class OwnerResolverProofV1:
    projection_claim_digest:str; owner_ref:str; owner_generation:str; owner_head:str
    owner_blob:str; owner_abi:str; resolver_ref:str; resolver_generation:str
    resolver_currentness_ref:str; source_ref:str; source_generation:str
    source_currentness_ref:str; owner_recognized_projection_digest:str
    disposition:ResolverDisposition; revoked:bool; supersedes_proof_digest:str|None
    resolver_signature:str; schema:str="OwnerResolverProofV1"
    def __post_init__(self):
        if self.schema!="OwnerResolverProofV1": raise KVAdmissionError("RESOLVER_PROOF_SCHEMA_MISMATCH")
        for f in ("owner_ref","owner_generation","owner_abi","resolver_ref","resolver_generation","resolver_currentness_ref","source_ref","source_generation","source_currentness_ref"):
            object.__setattr__(self,f,_text(getattr(self,f),f"{f.upper()}_INVALID"))
        for f in ("projection_claim_digest","owner_head","owner_blob","owner_recognized_projection_digest","resolver_signature"):
            object.__setattr__(self,f,_sha(getattr(self,f),f"{f.upper()}_INVALID"))
        if self.supersedes_proof_digest is not None: object.__setattr__(self,"supersedes_proof_digest",_sha(self.supersedes_proof_digest,"SUPERSEDES_PROOF_DIGEST_INVALID"))
        if not isinstance(self.disposition,ResolverDisposition): raise KVAdmissionError("RESOLVER_DISPOSITION_INVALID")
        if type(self.revoked) is not bool: raise KVAdmissionError("RESOLVER_REVOKED_BOOL_REQUIRED")
    def signing_payload(self):
        v=asdict(self); v["disposition"]=self.disposition.value; v.pop("resolver_signature"); return v
    @property
    def proof_digest(self):
        v=asdict(self); v["disposition"]=self.disposition.value; return _dig("AURA_PCK2_RESOLVER_PROOF_V1",v)

def _sign(payload:Mapping[str,Any],key:bytes)->str:
    if not isinstance(key,bytes) or not key: raise KVAdmissionError("RESOLVER_KEY_REQUIRED")
    return hmac.new(key,_canon(dict(payload)),hashlib.sha256).hexdigest()

def build_resolver_proof(*,claim:KVReuseProjectionClaimV1,resolver_ref:str,resolver_generation:str,resolver_currentness_ref:str,owner_recognized_projection_digest:str,disposition:ResolverDisposition,key:bytes,revoked:bool=False,supersedes_proof_digest:str|None=None)->OwnerResolverProofV1:
    if not isinstance(claim,KVReuseProjectionClaimV1): raise KVAdmissionError("PROJECTION_CLAIM_REQUIRED")
    if not isinstance(disposition,ResolverDisposition): raise KVAdmissionError("RESOLVER_DISPOSITION_INVALID")
    if type(revoked) is not bool: raise KVAdmissionError("RESOLVER_REVOKED_BOOL_REQUIRED")
    u={"projection_claim_digest":claim.claim_digest,"owner_ref":claim.owner_ref,"owner_generation":claim.owner_generation,
       "owner_head":claim.owner_head,"owner_blob":claim.owner_blob,"owner_abi":claim.owner_abi,
       "resolver_ref":_text(resolver_ref,"RESOLVER_REF_INVALID"),"resolver_generation":_text(resolver_generation,"RESOLVER_GENERATION_INVALID"),
       "resolver_currentness_ref":_text(resolver_currentness_ref,"RESOLVER_CURRENTNESS_REF_INVALID"),"source_ref":claim.source_ref,
       "source_generation":claim.source_generation,"source_currentness_ref":claim.source_currentness_ref,
       "owner_recognized_projection_digest":_sha(owner_recognized_projection_digest,"OWNER_RECOGNIZED_PROJECTION_DIGEST_INVALID"),
       "disposition":disposition.value,"revoked":revoked,"supersedes_proof_digest":supersedes_proof_digest,"schema":"OwnerResolverProofV1"}
    sig=_sign(u,key)
    return OwnerResolverProofV1(**{**u,"disposition":disposition,"resolver_signature":sig})

def _verify_resolver(claim,proof,keys,state):
    if not isinstance(claim,KVReuseProjectionClaimV1) or not isinstance(proof,OwnerResolverProofV1): raise KVAdmissionError("RESOLVER_CLAIM_AND_PROOF_REQUIRED")
    if not isinstance(keys,Mapping) or not isinstance(state,Mapping): raise KVAdmissionError("TRUSTED_RESOLVER_STATE_REQUIRED")
    if proof.projection_claim_digest!=claim.claim_digest: raise KVAdmissionError("RESOLVER_CLAIM_DIGEST_MISMATCH")
    for f in ("owner_ref","owner_generation","owner_head","owner_blob","owner_abi"):
        if getattr(proof,f)!=getattr(claim,f): raise KVAdmissionError("RESOLVER_OWNER_BINDING_MISMATCH",f)
    for f in ("source_ref","source_generation","source_currentness_ref"):
        if getattr(proof,f)!=getattr(claim,f): raise KVAdmissionError("RESOLVER_SOURCE_BINDING_MISMATCH",f)
    if proof.owner_recognized_projection_digest!=claim.projection_payload_digest: raise KVAdmissionError("RESOLVER_RECOGNIZED_PROJECTION_MISMATCH")
    if proof.disposition is not ResolverDisposition.OWNER_RESOLVED_CURRENT: raise KVAdmissionError("RESOLVER_NOT_CURRENT")
    if proof.revoked: raise KVAdmissionError("RESOLVER_PROOF_REVOKED")
    if proof.resolver_ref not in keys or proof.resolver_ref not in state: raise KVAdmissionError("RESOLVER_UNTRUSTED")
    gen,cur=state[proof.resolver_ref]
    if proof.resolver_generation!=gen: raise KVAdmissionError("RESOLVER_GENERATION_STALE")
    if proof.resolver_currentness_ref!=cur: raise KVAdmissionError("RESOLVER_CURRENTNESS_STALE")
    if not hmac.compare_digest(proof.resolver_signature,_sign(proof.signing_payload(),keys[proof.resolver_ref])): raise KVAdmissionError("RESOLVER_SIGNATURE_INVALID")

def _blockers(t,p):
    b=[]
    if t.responsibility is not ResponsibilityClass.TRANSFORMER_KV_CACHE: b.append("TARGET_NOT_TRANSFORMER_KV_CACHE")
    if p.responsibility is not ResponsibilityClass.TRANSFORMER_KV_CACHE: b.append("PATH_NOT_TRANSFORMER_KV_CACHE")
    if p.target_digest!=t.target_digest: b.append("PATH_TARGET_DIGEST_MISMATCH")
    for f in ("model_revision","tokenizer_digest","chat_template_digest","system_tool_prefix_digest","prefix_token_digest","cache_abi","principal_namespace_digest","host_epoch","route_epoch"):
        if getattr(p,f)!=getattr(t,f): b.append(f"PATH_{f.upper()}_MISMATCH")
    if p.evidence_generation!=t.source_generation: b.append("PATH_SOURCE_GENERATION_MISMATCH")
    if p.evidence_currentness_ref!=t.source_currentness_ref: b.append("PATH_CURRENTNESS_MISMATCH")
    if not p.persistent_restore_observed: b.append("PERSISTENT_RESTORE_NOT_OBSERVED")
    if not p.cache_read_observed: b.append("CACHE_READ_NOT_OBSERVED")
    if p.cache_hit_tokens<=0: b.append("CACHE_HIT_TOKENS_NOT_POSITIVE")
    return b

def admit_persistent_kv_reuse(*,target,claim,resolver_proof,path_evidence,trusted_resolver_keys,trusted_resolver_state):
    if not isinstance(target,PersistentKVReuseTargetV1): raise KVAdmissionError("KV_TARGET_REQUIRED")
    if not isinstance(path_evidence,PersistentKVPathEvidenceV1): raise KVAdmissionError("KV_PATH_EVIDENCE_REQUIRED")
    if not isinstance(claim,KVReuseProjectionClaimV1): raise KVAdmissionError("PROJECTION_CLAIM_REQUIRED")
    if not isinstance(resolver_proof,OwnerResolverProofV1): raise KVAdmissionError("OWNER_RESOLVER_PROOF_REQUIRED")
    if not isinstance(trusted_resolver_keys,Mapping) or not isinstance(trusted_resolver_state,Mapping): raise KVAdmissionError("TRUSTED_RESOLVER_STATE_REQUIRED")
    if claim.projection_payload_digest!=resolved_projection_payload_digest(target,path_evidence): raise KVAdmissionError("PROJECTION_PAYLOAD_DIGEST_MISMATCH")
    if claim.subject_ref!=target.coordinate_ref: raise KVAdmissionError("PROJECTION_COORDINATE_SUBJECT_MISMATCH")
    if claim.subject_generation!=target.source_generation: raise KVAdmissionError("PROJECTION_SUBJECT_GENERATION_MISMATCH")
    if claim.source_generation!=target.source_generation: raise KVAdmissionError("PROJECTION_SOURCE_GENERATION_MISMATCH")
    if claim.source_currentness_ref!=target.source_currentness_ref: raise KVAdmissionError("PROJECTION_SOURCE_CURRENTNESS_MISMATCH")
    _verify_resolver(claim,resolver_proof,trusted_resolver_keys,trusted_resolver_state)
    b=_blockers(target,path_evidence); net=path_evidence.net_reuse_us
    if b: disp,ok="EVIDENCE_REQUIRED",False
    elif net<=0: disp,ok="KV_REUSE_OBSERVED_NO_POSITIVE_NET_BENEFIT",False
    else: disp,ok="TRANSFORMER_KV_REUSE_ADMISSIBLE",True
    logical={"schema":"OwnerResolvedPersistentKVReuseAdmissionV1","target_digest":target.target_digest,
      "coordinate_ref":target.coordinate_ref,"k27_cell":target.k27_cell,"responsibility":target.responsibility.value,
      "projection_claim_digest":claim.claim_digest,"owner_resolver_proof_digest":resolver_proof.proof_digest,
      "path_evidence_digest":path_evidence.path_digest,"disposition":disp,"blockers":tuple(sorted(set(b))),
      "persistent_restore_observed":path_evidence.persistent_restore_observed,"cache_read_observed":path_evidence.cache_read_observed,
      "cache_hit_tokens":path_evidence.cache_hit_tokens,"prefill_saved_us":path_evidence.prefill_saved_us,
      "overhead_us":path_evidence.prefill_saved_us-net,"net_reuse_us":net,"owner_resolver_proof_verified":True,
      "transformer_kv_reuse_admissible":ok,"coordinate_nomination_is_authority":False,
      "coordinate_memory_equated_to_transformer_kv":False,"semantic_response_cache_equated_to_transformer_kv":False,
      "monetary_credit_authorized":False,"provider_authorized":False,"execution_authorized":False,
      "performance_superiority_claimed":False}
    return {**logical,"admission_digest":_dig("AURA_PCK2_ADMISSION_V1",logical)}
