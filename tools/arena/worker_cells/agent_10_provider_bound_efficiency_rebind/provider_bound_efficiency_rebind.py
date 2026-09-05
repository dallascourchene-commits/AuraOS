from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from hashlib import sha256
from itertools import product
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "AURA-PROVIDER-BOUND-EFFICIENCY-REBIND-v1"
RECEIPT_SCHEMA = SCHEMA + "-RECEIPT"
AGENT27_PARENT_COMMIT = "b07199c48f9b6c26642108c9ff61bf3ca0dc6082"
AGENT08_PARENT_COMMIT = "7f68a02632de769475efdcf1dfb94acefcff7cf1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

class RebindError(ValueError): pass
class Decision(str, Enum):
    REUSE_AFTER_PROVIDER_BOUND_REBIND = "REUSE_AFTER_PROVIDER_BOUND_REBIND"
    REPROVE = "REPROVE"

def _canon(value: Any) -> bytes:
    try: return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc: raise RebindError("NON_CANONICAL_VALUE") from exc

def digest(value: Any) -> str: return sha256(_canon(value)).hexdigest()
def _hex40(v: str, name: str) -> str:
    if not isinstance(v, str) or not HEX40.fullmatch(v): raise RebindError(f"INVALID_HEX40:{name}")
    return v
def _hex64(v: str, name: str) -> str:
    if not isinstance(v, str) or not HEX64.fullmatch(v): raise RebindError(f"INVALID_HEX64:{name}")
    return v
def _nonempty(v: str, name: str) -> str:
    if not isinstance(v, str) or not v: raise RebindError(f"INVALID_STRING:{name}")
    return v
def _strict_bool(v: bool, name: str) -> bool:
    if type(v) is not bool: raise RebindError(f"INVALID_BOOL:{name}")
    return v

def canonical_paths(paths: Sequence[str]) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes)) or not paths: raise RebindError("INVALID_CHANGED_PATHS")
    out=tuple(sorted(paths))
    if len(set(out)) != len(out): raise RebindError("DUPLICATE_CHANGED_PATH")
    for p in out:
        if not isinstance(p, str) or not p or p.startswith("/") or ".." in p.split("/"): raise RebindError("INVALID_CHANGED_PATH")
    return out

def observation_root(parent: str, child: str, generator: str, changed_paths: Sequence[str]) -> str:
    return digest({"schema":"AURA-PROVIDER-MOVEMENT-OBSERVATION-v1","parent":_hex40(parent,"parent"),"child":_hex40(child,"child"),"generator":_nonempty(generator,"generator"),"changed_paths":canonical_paths(changed_paths)})

@dataclass(frozen=True)
class ProviderMovement:
    proved_parent_head:str; current_child_head:str; observed_parent_head:str; observed_child_head:str
    observed_generator_identity:str; expected_generator_identity:str
    changed_paths:tuple[str,...]; allowed_proof_neutral_paths:tuple[str,...]
    expected_provider_observation_root:str; provider_observation_verified:bool
    agent27_semantic_commit:str=AGENT27_PARENT_COMMIT

@dataclass(frozen=True)
class EfficiencyProjection:
    semantic_source_head:str; runtime_sha256:str; trace_projection:Mapping[str,Any]; cost_projection:Mapping[str,Any]
    benchmark_generation:str; hardware_fingerprint:str; agent08_semantic_commit:str=AGENT08_PARENT_COMMIT
    @property
    def trace_root(self)->str: return digest(self.trace_projection)
    @property
    def cost_root(self)->str: return digest(self.cost_projection)
    @property
    def projection_root(self)->str:
        return digest({"semantic_source_head":self.semantic_source_head,"runtime_sha256":self.runtime_sha256,"trace_root":self.trace_root,"cost_root":self.cost_root,"benchmark_generation":self.benchmark_generation,"hardware_fingerprint":self.hardware_fingerprint,"agent08_semantic_commit":self.agent08_semantic_commit})

@dataclass(frozen=True)
class RebindEvidence:
    movement:ProviderMovement; proof_time_projection:EfficiencyProjection; current_projection:EfficiencyProjection
    expected_proof_time_projection_root:str; expected_current_projection_root:str; authority_requested:bool=False

@dataclass(frozen=True)
class Receipt:
    schema:str; decision:Decision; reasons:tuple[str,...]; parent_head:str; child_head:str; provider_observation_root:str; allowlist_root:str
    proof_time_projection_root:str; current_projection_root:str; trace_projection_root:str; cost_projection_root:str
    agent27_semantic_commit:str; agent08_semantic_commit:str; evidence_root:str
    fresh_hosted_pass:bool=False; effect_authority:bool=False; gate10:bool=False; receipt_root:str=""
    def without_root(self)->dict[str,Any]:
        d=asdict(self); d["decision"]=self.decision.value; d.pop("receipt_root"); return d

def _validate_projection(p: EfficiencyProjection)->None:
    if type(p) is not EfficiencyProjection: raise RebindError("EFFICIENCY_PROJECTION_REQUIRED")
    _hex40(p.semantic_source_head,"semantic_source_head"); _hex64(p.runtime_sha256,"runtime_sha256")
    _nonempty(p.benchmark_generation,"benchmark_generation"); _nonempty(p.hardware_fingerprint,"hardware_fingerprint")
    if p.agent08_semantic_commit != AGENT08_PARENT_COMMIT: raise RebindError("WRONG_AGENT08_PARENT_GENERATION")
    if not isinstance(p.trace_projection,Mapping) or not p.trace_projection: raise RebindError("TRACE_PROJECTION_REQUIRED")
    if not isinstance(p.cost_projection,Mapping) or not p.cost_projection: raise RebindError("COST_PROJECTION_REQUIRED")
    digest(p.trace_projection); digest(p.cost_projection); _hex64(p.projection_root,"projection_root")

def movement_facts(m: ProviderMovement)->tuple[str,str]:
    if type(m) is not ProviderMovement: raise RebindError("PROVIDER_MOVEMENT_REQUIRED")
    for name in ("proved_parent_head","current_child_head","observed_parent_head","observed_child_head"): _hex40(getattr(m,name),name)
    if m.agent27_semantic_commit != AGENT27_PARENT_COMMIT: raise RebindError("WRONG_AGENT27_PARENT_GENERATION")
    observed_gen=_nonempty(m.observed_generator_identity,"observed_generator_identity"); expected_gen=_nonempty(m.expected_generator_identity,"expected_generator_identity")
    changed=canonical_paths(m.changed_paths); allowed=canonical_paths(m.allowed_proof_neutral_paths)
    _hex64(m.expected_provider_observation_root,"expected_provider_observation_root"); _strict_bool(m.provider_observation_verified,"provider_observation_verified")
    if m.observed_parent_head != m.proved_parent_head: raise RebindError("PROVIDER_PARENT_MISMATCH")
    if m.observed_child_head != m.current_child_head: raise RebindError("PROVIDER_CHILD_MISMATCH")
    if observed_gen != expected_gen: raise RebindError("GENERATOR_IDENTITY_MISMATCH")
    if not set(changed).issubset(set(allowed)): raise RebindError("NON_NEUTRAL_CHANGED_PATH")
    root=observation_root(m.observed_parent_head,m.observed_child_head,observed_gen,changed)
    if root != m.expected_provider_observation_root: raise RebindError("PROVIDER_OBSERVATION_ROOT_MISMATCH")
    if m.provider_observation_verified is not True: raise RebindError("PROVIDER_OBSERVATION_NOT_EXTERNALLY_VERIFIED")
    return root,digest({"allowed_proof_neutral_paths":allowed})

def reasons(e: RebindEvidence)->tuple[str,...]:
    if type(e) is not RebindEvidence: return ("INVALID_EVIDENCE_TYPE",)
    try:
        _strict_bool(e.authority_requested,"authority_requested"); obs_root,allowlist_root=movement_facts(e.movement)
        _validate_projection(e.proof_time_projection); _validate_projection(e.current_projection)
        _hex64(e.expected_proof_time_projection_root,"expected_proof_time_projection_root"); _hex64(e.expected_current_projection_root,"expected_current_projection_root")
    except RebindError as exc: return (str(exc),)
    out=[]; m=e.movement; old=e.proof_time_projection; cur=e.current_projection
    if e.authority_requested: out.append("AUTHORITY_REQUESTED")
    if old.semantic_source_head != m.proved_parent_head: out.append("PROOF_PROJECTION_PARENT_MISMATCH")
    if cur.semantic_source_head != m.proved_parent_head: out.append("CURRENT_SEMANTIC_SOURCE_DRIFT")
    if old.projection_root != e.expected_proof_time_projection_root: out.append("PROOF_TIME_PROJECTION_ROOT_MISMATCH")
    if cur.projection_root != e.expected_current_projection_root: out.append("CURRENT_PROJECTION_ROOT_MISMATCH")
    if old.projection_root != cur.projection_root: out.append("EFFICIENCY_PROJECTION_DRIFT")
    if old.runtime_sha256 != cur.runtime_sha256: out.append("RUNTIME_DRIFT")
    if old.trace_root != cur.trace_root: out.append("TRACE_PROJECTION_DRIFT")
    if old.cost_root != cur.cost_root: out.append("COST_PROJECTION_DRIFT")
    if old.benchmark_generation != cur.benchmark_generation: out.append("BENCHMARK_GENERATION_DRIFT")
    if old.hardware_fingerprint != cur.hardware_fingerprint: out.append("HARDWARE_ENVELOPE_DRIFT")
    if obs_root != e.movement.expected_provider_observation_root or not allowlist_root: out.append("MOVEMENT_BINDING_INVALID")
    return tuple(out) or ("OK",)

def evidence_root(e:RebindEvidence)->str:
    return digest({"schema":SCHEMA,"movement":asdict(e.movement),"proof_time_projection":{"semantic_source_head":e.proof_time_projection.semantic_source_head,"runtime_sha256":e.proof_time_projection.runtime_sha256,"trace_projection":e.proof_time_projection.trace_projection,"cost_projection":e.proof_time_projection.cost_projection,"benchmark_generation":e.proof_time_projection.benchmark_generation,"hardware_fingerprint":e.proof_time_projection.hardware_fingerprint,"agent08_semantic_commit":e.proof_time_projection.agent08_semantic_commit},"current_projection":{"semantic_source_head":e.current_projection.semantic_source_head,"runtime_sha256":e.current_projection.runtime_sha256,"trace_projection":e.current_projection.trace_projection,"cost_projection":e.current_projection.cost_projection,"benchmark_generation":e.current_projection.benchmark_generation,"hardware_fingerprint":e.current_projection.hardware_fingerprint,"agent08_semantic_commit":e.current_projection.agent08_semantic_commit},"expected_proof_time_projection_root":e.expected_proof_time_projection_root,"expected_current_projection_root":e.expected_current_projection_root,"authority_requested":e.authority_requested})

def decide(e:RebindEvidence)->Decision: return Decision.REUSE_AFTER_PROVIDER_BOUND_REBIND if reasons(e)==("OK",) else Decision.REPROVE

def make_receipt(e:RebindEvidence)->Receipt:
    rs=reasons(e); ok=rs==("OK",)
    try:
        obs_root,allowlist_root=movement_facts(e.movement); old_root=e.proof_time_projection.projection_root; cur_root=e.current_projection.projection_root
        trace_root=e.current_projection.trace_root; cost_root=e.current_projection.cost_root; parent=e.movement.proved_parent_head; child=e.movement.current_child_head
    except Exception:
        obs_root=allowlist_root=old_root=cur_root=trace_root=cost_root="0"*64; parent=child="0"*40
    base=Receipt(RECEIPT_SCHEMA,Decision.REUSE_AFTER_PROVIDER_BOUND_REBIND if ok else Decision.REPROVE,rs,parent,child,obs_root,allowlist_root,old_root,cur_root,trace_root,cost_root,AGENT27_PARENT_COMMIT,AGENT08_PARENT_COMMIT,evidence_root(e) if type(e) is RebindEvidence else "0"*64,False,False,False,"")
    return replace(base,receipt_root=digest(base.without_root()))

def verify_receipt(e:RebindEvidence,receipt:Receipt)->bool:
    if type(receipt) is not Receipt or receipt.schema != RECEIPT_SCHEMA: return False
    try: expected=make_receipt(e)
    except Exception: return False
    return receipt==expected and receipt.receipt_root==digest(receipt.without_root()) and not receipt.fresh_hosted_pass and not receipt.effect_authority and not receipt.gate10

AXES8=("parent_child_binding","provider_observation","generator_allowlist","proof_projection","current_projection","trace_cost_exactness","succession_composition","effect_ceiling")
def classify8(state:Sequence[int])->str:
    if len(state)!=8 or any(type(v) is not int or v not in (0,1,2) for v in state): raise RebindError("INVALID_OMEGA8")
    if any(v==0 for v in state[:7]) or state[7]==0: return "REPROVE_HARD_INVALID"
    if any(v==1 for v in state[:7]): return "REPROVE_UNRESOLVED"
    if state[7]==2: return "REPROVE_AUTHORITY_WIDENING"
    return "REUSE_AFTER_PROVIDER_BOUND_REBIND"
def classify13(state:Sequence[int])->str:
    if len(state)!=13 or any(type(v) is not int or v not in (0,1,2) for v in state): raise RebindError("INVALID_13D")
    core=classify8(state[:8])
    if core!="REUSE_AFTER_PROVIDER_BOUND_REBIND": return core
    tail=state[8:]
    if 0 in tail: return "REPROVE_TRAILING_HARD_INVALID"
    if 1 in tail: return "REPROVE_TRAILING_UNRESOLVED"
    return core
def exhaustive8()->dict[str,int]:
    counts={}
    for state in product(range(3),repeat=8):
        d=classify8(state); counts[d]=counts.get(d,0)+1
    return counts
