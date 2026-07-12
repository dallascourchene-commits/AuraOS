"""Deterministic manifest compiler for Aura Arena guarded-WFST grammars."""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib, json, re
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from aura_arena_wfst_types import ArenaTransition, CompiledArenaGrammar, PATCH_AUTHORITY, VSA_PATCH_AUTHORITY

ARENA_WFST_COMPILER_VERSION="AURA_ARENA_WFST_COMPILER_V2"
MANIFEST_SCHEMA_VERSION="AURA_ARENA_GRAMMAR_MANIFEST_V1"
DEFAULT_GUARD_IDS=frozenset({"GUARD.ALWAYS","GUARD.EVIDENCE_PRESENT","GUARD.EVIDENCE_ALL","GUARD.EXACT_TARGET","GUARD.SOURCE_HASH_MATCH","GUARD.TEST_EVIDENCE","GUARD.VERIFIER_PASS","GUARD.LEASE_CONTAINS_CAPABILITY","GUARD.HUMAN_APPROVAL","GUARD.LIFECYCLE_ALLOWED","GUARD.POLICY_FLAG","GUARD.REPOSITORY_CLEAN_OR_SNAPSHOTTED"})
_ID_RE=re.compile(r"^[A-Za-z0-9_.:\-*/]+$")

@dataclass(frozen=True)
class CompileDiagnostic:
    severity:str; code:str; message:str; transition_id:str=""; state:str=""
    def to_dict(self): return {"severity":self.severity,"code":self.code,"message":self.message,"transition_id":self.transition_id,"state":self.state}
@dataclass
class ArenaGrammarCompileResult:
    ok:bool; grammar:CompiledArenaGrammar|None; diagnostics:list[CompileDiagnostic]=field(default_factory=list); manifest_digest:str=""
    def to_dict(self): return {"ok":self.ok,"version":ARENA_WFST_COMPILER_VERSION,"manifest_digest":self.manifest_digest,"grammar":self.grammar.to_dict() if self.grammar else None,"diagnostics":[x.to_dict() for x in self.diagnostics],"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":VSA_PATCH_AUTHORITY,"automatic_grammar_promotion":False}

def load_and_compile_arena_grammar(path:str|Path,*,guard_ids=None,capability_exists:Callable[[str],bool]|None=None):
    p=Path(path)
    try: payload=json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:return _failed("manifest_not_found",f"manifest not found: {p}")
    except json.JSONDecodeError as exc:return _failed("manifest_invalid_json",f"invalid JSON: {exc}")
    except OSError as exc:return _failed("manifest_read_failed",str(exc))
    return compile_arena_grammar(payload,guard_ids=guard_ids,capability_exists=capability_exists,source_path=str(p))

def compile_arena_grammar(manifest:dict[str,Any],*,guard_ids=None,capability_exists=None,source_path:str=""):
    d=[]
    if not isinstance(manifest,dict): return _failed("manifest_not_object","grammar manifest must be an object")
    schema=str(manifest.get("schema_version") or "")
    if schema!=MANIFEST_SCHEMA_VERSION:d.append(CompileDiagnostic("error","unsupported_schema_version",f"expected {MANIFEST_SCHEMA_VERSION}, received {schema or '<missing>'}"))
    arena_id=_manifest_text(manifest,"arena_id",d); arena_version=_manifest_text(manifest,"arena_version",d); grammar_version=_manifest_text(manifest,"grammar_version",d); start_state=_manifest_text(manifest,"start_state",d); meta=bool(manifest.get("meta_grammar",False))
    raw_states=manifest.get("states") or []
    if not isinstance(raw_states,list): d.append(CompileDiagnostic("error","states_not_list","states must be a list")); raw_states=[]
    states=_deduplicated_ids(raw_states,"state",d); state_set=set(states)
    if meta and "*" not in state_set:d.append(CompileDiagnostic("error","meta_missing_wildcard","meta grammar must declare '*' state"))
    elif not meta and start_state and start_state not in state_set:d.append(CompileDiagnostic("error","unknown_start_state",f"start state {start_state} is not declared"))
    terminals=set(_text_list(manifest.get("terminal_states") or []))
    for s in sorted(terminals-state_set):d.append(CompileDiagnostic("error","unknown_terminal_state",f"terminal state {s} is not declared",state=s))
    allowed=frozenset(guard_ids or DEFAULT_GUARD_IDS); transitions=[]; tids=set(); aliases={}
    raw_transitions=manifest.get("transitions") or []
    if not isinstance(raw_transitions,list):d.append(CompileDiagnostic("error","transitions_not_list","transitions must be a list")); raw_transitions=[]
    for i,raw in enumerate(raw_transitions):
        try:t=ArenaTransition.from_dict(raw,arena_id=arena_id,grammar_version=grammar_version)
        except (TypeError,ValueError) as exc:d.append(CompileDiagnostic("error","invalid_transition",f"transition[{i}]: {exc}"));continue
        if t.transition_id in tids:d.append(CompileDiagnostic("error","duplicate_transition_id",f"duplicate transition id {t.transition_id}",t.transition_id));continue
        tids.add(t.transition_id);transitions.append(t)
        if t.from_state not in state_set and not(meta and t.from_state=="*"):d.append(CompileDiagnostic("error","unknown_from_state",f"unknown from_state {t.from_state}",t.transition_id,t.from_state))
        if t.next_state not in state_set and not(meta and t.next_state=="*"):d.append(CompileDiagnostic("error","unknown_next_state",f"unknown next_state {t.next_state}",t.transition_id,t.next_state))
        for g in t.hard_guards:
            if g.guard_id not in allowed:d.append(CompileDiagnostic("error","unknown_guard",f"unknown guard id {g.guard_id}",t.transition_id,t.from_state))
        for c in t.requested_capabilities:
            if not _valid_id(c):d.append(CompileDiagnostic("error","invalid_capability_id",f"invalid capability id {c!r}",t.transition_id))
            elif capability_exists is not None:
                try:exists=bool(capability_exists(c))
                except Exception as exc:exists=False;d.append(CompileDiagnostic("error","capability_validation_failed",f"capability validation failed for {c}: {type(exc).__name__}",t.transition_id))
                if not exists:d.append(CompileDiagnostic("error","unbound_capability",f"capability is not grounded: {c}",t.transition_id))
        _validate_capsule_refs(t,d)
        for phrase in t.input_phrases():
            n=normalize_input_phrase(phrase)
            if not n:d.append(CompileDiagnostic("error","empty_input_phrase","transition contains an empty normalized input phrase",t.transition_id));continue
            key=(t.from_state,n); prior=aliases.get(key)
            if prior and prior!=t.transition_id:d.append(CompileDiagnostic("error","ambiguous_state_local_alias",f"input phrase {phrase!r} resolves to both {prior} and {t.transition_id} in {t.from_state}",t.transition_id,t.from_state))
            else:aliases[key]=t.transition_id
    for t in transitions:
        if t.rollback_transition and t.rollback_transition not in tids:d.append(CompileDiagnostic("error","unknown_rollback_transition",f"rollback transition {t.rollback_transition} is not declared",t.transition_id))
    if not meta and start_state in state_set:
        reachable=_reachable_states(start_state,transitions)
        for s in sorted(state_set-reachable):d.append(CompileDiagnostic("warning","unreachable_state",f"state {s} is unreachable from {start_state}",state=s))
        outgoing={x.from_state for x in transitions}
        for s in sorted(state_set-terminals):
            if s not in outgoing:d.append(CompileDiagnostic("warning","dead_end_nonterminal",f"nonterminal state {s} has no outgoing transition",state=s))
    digest=_manifest_digest(manifest); errors=any(x.severity=="error" for x in d); grammar=None
    if not errors:grammar=CompiledArenaGrammar(arena_id,arena_version,grammar_version,start_state,tuple(states),tuple(sorted(transitions,key=lambda x:(x.from_state,x.transition_id))),digest,source_path,meta)
    return ArenaGrammarCompileResult(not errors,grammar,d,digest)

def normalize_input_phrase(value):
    text=str(value or "").strip().casefold(); text=re.sub(r"[^a-z0-9_.:\-/*]+"," ",text); return " ".join(text.split())
def _validate_capsule_refs(t,d):
    refs=(t.morphology_profile_ref,t.route_capsule_ref)
    if bool(refs[0])!=bool(refs[1]):d.append(CompileDiagnostic("error","incomplete_route_capsule_reference","morphology_profile_ref and route_capsule_ref must be declared together",t.transition_id));return
    if not refs[0]:return
    for value,root,code in ((refs[0],".aura/morphology_profiles","invalid_morphology_profile_ref"),(refs[1],".aura/route_capsules","invalid_route_capsule_ref")):
        raw=value.replace("\\","/"); pure=PurePosixPath(raw)
        if pure.is_absolute() or any(p in {"",".",".."} for p in pure.parts) or pure.suffix.casefold()!=".json":d.append(CompileDiagnostic("error",code,f"unsafe repository-relative reference: {value}",t.transition_id));continue
        try:pure.relative_to(PurePosixPath(root))
        except ValueError:d.append(CompileDiagnostic("error",code,f"reference must remain under {root}",t.transition_id))
def _reachable_states(start,transitions):
    adj={}
    for t in transitions:adj.setdefault(t.from_state,set()).add(t.next_state)
    seen={start};stack=[start]
    while stack:
        cur=stack.pop()
        for target in sorted(adj.get(cur,())):
            if target not in seen:seen.add(target);stack.append(target)
    return seen
def _manifest_digest(m):return hashlib.blake2b(json.dumps(m,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode(),digest_size=20).hexdigest()
def _manifest_text(m,key,d):
    v=str(m.get(key) or "").strip()
    if not v:d.append(CompileDiagnostic("error",f"missing_{key}",f"{key} is required"))
    elif not _valid_id(v):d.append(CompileDiagnostic("error",f"invalid_{key}",f"{key} contains unsupported characters: {v!r}"))
    return v
def _deduplicated_ids(values,kind,d):
    out=[];seen=set()
    for raw in values:
        v=str(raw or "").strip()
        if not v or not _valid_id(v):d.append(CompileDiagnostic("error",f"invalid_{kind}_id",f"invalid {kind} id: {v!r}"));continue
        if v in seen:d.append(CompileDiagnostic("error",f"duplicate_{kind}_id",f"duplicate {kind} id: {v}"));continue
        seen.add(v);out.append(v)
    return out
def _text_list(v):return [v] if isinstance(v,str) else ([str(x).strip() for x in v if str(x).strip()] if isinstance(v,list) else [])
def _valid_id(v):return bool(v and _ID_RE.fullmatch(v))
def _failed(code,message):return ArenaGrammarCompileResult(False,None,[CompileDiagnostic("error",code,message)],"")
