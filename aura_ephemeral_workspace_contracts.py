"""Deterministic, non-operational contracts for intent-compiled spatial workspaces.

The records in this module reference Aura's existing canonical owners. They do
not activate an organ, invoke a renderer/model, persist project truth, or grant
source/domain/publication authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import hashlib
import json
import math
import re
from typing import Any

WORKSPACE_CONTRACTS_VERSION = "AURA_INTENT_SPATIAL_WORKSPACE_CONTRACTS_V1"
AUTHORITY_ENVELOPE_VERSION = "AURA_WORKSPACE_AUTHORITY_ENVELOPE_V1"
CANONICAL_REFERENCE_VERSION = "AURA_CANONICAL_REFERENCE_V1"
REPOSITORY_IDENTITY_VERSION = "AURA_REPOSITORY_IDENTITY_V1"
PROJECT_CONTEXT_PROJECTION_VERSION = "AURA_PROJECT_CONTEXT_PROJECTION_V1"
EPHEMERAL_WORKSPACE_RECIPE_VERSION = "AURA_EPHEMERAL_WORKSPACE_RECIPE_V1"
SPATIAL_REFERENT_BINDING_VERSION = "AURA_SPATIAL_REFERENT_BINDING_V1"
MULTIMODAL_SPATIAL_OBSERVATION_VERSION = "AURA_MULTIMODAL_SPATIAL_OBSERVATION_V1"
CODING_SPATIAL_WORKSPACE_V1 = "CODING_SPATIAL_WORKSPACE_V1"
MAX_ITEMS = 512
MAX_TEXT_BYTES = 4096
MAX_METADATA_BYTES = 65_536
MAX_TTL_SECONDS = 86_400
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DIGEST = re.compile(r"^[0-9a-f]{32,64}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TRUTH = frozenset({"EXACT", "DERIVED", "PRESENTATION", "HYPOTHESIS"})
_FRESHNESS = frozenset({"CURRENT", "BOUNDED", "STALE", "UNKNOWN"})
_INPUTS = frozenset({"VOICE", "HAND", "GAZE", "RAY", "TOUCH", "KEYBOARD", "CONTROLLER"})
_EVIDENCE = frozenset({"MEASURED", "DERIVED", "ESTIMATED", "UNAVAILABLE"})
_AUTHORITY_TOKENS = frozenset(re.sub(r"[^a-z0-9]+", "", x) for x in (
    "approval authorization authority authority_decision automatic_commit automatic_execution automatic_fix "
    "automatic_merge automatic_persistence automatic_promotion automatic_pull_request automatic_push automatic_resume "
    "capability_lease deployment_authority domain_mutation execution_authority merge_authority model_authority "
    "patch_authority payment_authority persistence_authority physical_work_authority production_mutation "
    "professional_authority promotion_authority renderer_authority sensor_authority source_mutation vsa_patch_authority"
).split())
_RAW_SENSOR_TOKENS = frozenset(re.sub(r"[^a-z0-9]+", "", x) for x in (
    "audio_buffer camera_frame depth_frame eye_frame gaze_vector_stream hand_joint_stream hand_landmarks "
    "microphone_buffer point_cloud_stream raw_audio raw_camera raw_frame raw_sensor_payload room_scan video_frame"
).split())


def _canonical(value: Any) -> Any:
    if isinstance(value, Enum): return value.value
    if is_dataclass(value): return _canonical(value.to_dict())
    if isinstance(value, Mapping): return {str(k): _canonical(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)): return [_canonical(x) for x in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_canonical(x) for x in value), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, float) and not math.isfinite(value): raise ValueError("non-finite floats are prohibited")
    if value is None or isinstance(value, (bool, int, float, str)): return value
    raise ValueError(f"non-JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def stable_digest(value: Any) -> str:
    return hashlib.blake2b(canonical_json(value).encode(), digest_size=32).hexdigest()


def _text(value: Any, name: str, *, optional: bool = False, maximum: int = MAX_TEXT_BYTES) -> str:
    result = str(value or "").strip()
    if not result and not optional: raise ValueError(f"{name} is required")
    if len(result.encode()) > maximum or any(ord(ch) < 32 for ch in result):
        raise ValueError(f"{name} exceeds its bounded text contract")
    return result


def _id(value: Any, name: str) -> str:
    result = _text(value, name, maximum=192)
    if not _ID.fullmatch(result): raise ValueError(f"{name} contains unsupported characters")
    return result


def _digest(value: Any, name: str, *, optional: bool = False) -> str:
    result = _text(value, name, optional=optional, maximum=64).lower()
    if result and not _DIGEST.fullmatch(result): raise ValueError(f"{name} must be 32-64 lowercase hex characters")
    return result


def _bool(value: Any, name: str, required: bool) -> bool:
    if type(value) is not bool or value is not required: raise ValueError(f"{name} must be {str(required).lower()}")
    return value


def _int(value: Any, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high: raise ValueError(f"{name} must be an integer in {low}..{high}")
    return value


def _prob(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1: raise ValueError(f"{name} must be between 0 and 1")
    return number


def _seq(value: Any, name: str, *, ids: bool = False, max_items: int = MAX_ITEMS, sort: bool = False) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence): raise ValueError(f"{name} must be a sequence")
    if len(value) > max_items: raise ValueError(f"{name} exceeds its item ceiling")
    result = tuple((_id(x, f"{name}[]") if ids else _text(x, f"{name}[]")) for x in value)
    if len(set(result)) != len(result): raise ValueError(f"{name} values must be unique")
    return tuple(sorted(result)) if sort else result


def _find_token(value: Any, tokens: frozenset[str], path: str) -> str | None:
    stack = [(value, path, 0)]; seen = 0
    while stack:
        current, current_path, depth = stack.pop(); seen += 1
        if depth > 24 or seen > 8192: raise ValueError(f"{path} exceeds its structural ceiling")
        if isinstance(current, Mapping):
            for key, item in current.items():
                token = re.sub(r"[^a-z0-9]+", "", str(key).lower()); child = f"{current_path}.{key}"
                if token in tokens: return child
                stack.append((item, child, depth + 1))
        elif isinstance(current, (list, tuple, set, frozenset)):
            stack.extend((item, f"{current_path}[{i}]", depth + 1) for i, item in enumerate(current))
    return None


def _metadata(value: Any, name: str) -> tuple[tuple[str, Any], ...]:
    if value in (None, ()): return ()
    candidate = dict(value) if isinstance(value, (Mapping, tuple)) else None
    if candidate is None: raise ValueError(f"{name} must be an object")
    authority = _find_token(candidate, _AUTHORITY_TOKENS, name)
    if authority: raise ValueError(f"{name} cannot contain an authority alias: {authority}")
    raw = _find_token(candidate, _RAW_SENSOR_TOKENS, name)
    if raw: raise ValueError(f"{name} cannot contain raw sensor data: {raw}")
    normalized = _canonical(candidate)
    if len(canonical_json(normalized).encode()) > MAX_METADATA_BYTES: raise ValueError(f"{name} exceeds its byte ceiling")
    return tuple(normalized.items())


def _strict(payload: Mapping[str, Any], expected: set[str], name: str) -> None:
    supplied = set(payload)
    if supplied != expected: raise ValueError(f"{name} keys mismatch: missing={sorted(expected-supplied)}, extra={sorted(supplied-expected)}")


def _set_record_digest(record: Any, field_name: str) -> None:
    body = record.to_dict(); supplied = str(body.pop(field_name, "") or "").lower(); expected = stable_digest(body)
    if supplied and supplied != expected: raise ValueError(f"{field_name} does not match canonical bytes")
    object.__setattr__(record, field_name, expected)


@dataclass(frozen=True)
class AuthorityEnvelope:
    version: str = AUTHORITY_ENVELOPE_VERSION
    projection_only: bool = True; review_only: bool = True; human_review_required: bool = True
    source_mutation: bool = False; domain_mutation: bool = False; production_mutation: bool = False
    renderer_authority: bool = False; sensor_authority: bool = False; model_authority: bool = False
    execution_authority: bool = False; persistence_authority: bool = False; deployment_authority: bool = False
    physical_work_authority: bool = False; payment_authority: bool = False; professional_authority: bool = False
    patch_authority: bool = False; vsa_patch_authority: bool = False
    automatic_persistence: bool = False; automatic_resume: bool = False; automatic_promotion: bool = False
    automatic_commit: bool = False; automatic_push: bool = False; automatic_pull_request: bool = False; automatic_merge: bool = False

    def __post_init__(self) -> None:
        if self.version != AUTHORITY_ENVELOPE_VERSION: raise ValueError("unsupported authority version")
        for f in fields(self):
            if f.name != "version": _bool(getattr(self, f.name), f"authority.{f.name}", f.name in {"projection_only", "review_only", "human_review_required"})

    def to_dict(self) -> dict[str, Any]: return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorityEnvelope":
        _strict(payload, {f.name for f in fields(cls)}, "authority"); return cls(**dict(payload))


@dataclass(frozen=True)
class CanonicalReference:
    reference_id: str; owner: str; canonical_ref: str; digest: str
    truth_class: str = "EXACT"; freshness_class: str = "CURRENT"; metadata: tuple[tuple[str, Any], ...] = ()
    version: str = CANONICAL_REFERENCE_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_id", _id(self.reference_id, "reference.reference_id"))
        object.__setattr__(self, "owner", _id(self.owner, "reference.owner"))
        object.__setattr__(self, "canonical_ref", _text(self.canonical_ref, "reference.canonical_ref"))
        object.__setattr__(self, "digest", _digest(self.digest, "reference.digest"))
        if self.truth_class not in _TRUTH or self.freshness_class not in _FRESHNESS: raise ValueError("unsupported reference class")
        object.__setattr__(self, "metadata", _metadata(self.metadata, "reference.metadata"))
        if self.version != CANONICAL_REFERENCE_VERSION: raise ValueError("unsupported reference version")

    def to_dict(self) -> dict[str, Any]:
        return {"version":self.version,"reference_id":self.reference_id,"owner":self.owner,"canonical_ref":self.canonical_ref,
                "digest":self.digest,"truth_class":self.truth_class,"freshness_class":self.freshness_class,"metadata":dict(self.metadata)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalReference":
        _strict(payload, {"version","reference_id","owner","canonical_ref","digest","truth_class","freshness_class","metadata"}, "reference")
        return cls(**dict(payload))


@dataclass(frozen=True)
class RepositoryIdentity:
    repository: str; ref: str; commit_sha: str; source_tree_digest: str; identity_digest: str = ""
    version: str = REPOSITORY_IDENTITY_VERSION

    def __post_init__(self) -> None:
        repo = _text(self.repository, "repository.repository", maximum=256)
        if not _REPO.fullmatch(repo): raise ValueError("repository must be owner/name")
        object.__setattr__(self, "repository", repo); object.__setattr__(self, "ref", _text(self.ref, "repository.ref", maximum=256))
        object.__setattr__(self, "commit_sha", _digest(self.commit_sha, "repository.commit_sha"))
        object.__setattr__(self, "source_tree_digest", _digest(self.source_tree_digest, "repository.source_tree_digest"))
        if self.version != REPOSITORY_IDENTITY_VERSION: raise ValueError("unsupported repository identity version")
        _set_record_digest(self, "identity_digest")

    def to_dict(self) -> dict[str, Any]: return {"version":self.version,"repository":self.repository,"ref":self.ref,"commit_sha":self.commit_sha,"source_tree_digest":self.source_tree_digest,"identity_digest":self.identity_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RepositoryIdentity":
        _strict(payload, {"version","repository","ref","commit_sha","source_tree_digest","identity_digest"}, "repository"); return cls(**dict(payload))


_REFERENCE_FIELDS = ("artifact_evidence_refs","decision_refs","rejected_alternative_refs","unresolved_question_refs","assumption_refs","capability_refs","relationship_refs","blocker_refs","next_action_refs")


@dataclass(frozen=True)
class ProjectContextProjection:
    projection_id: str; project_ref: str; canonical_owner: str; objective_digest: str; purpose_digest: str
    repository_identity: RepositoryIdentity; artifact_evidence_refs: tuple[CanonicalReference, ...]
    decision_refs: tuple[CanonicalReference, ...] = (); rejected_alternative_refs: tuple[CanonicalReference, ...] = ()
    unresolved_question_refs: tuple[CanonicalReference, ...] = (); assumption_refs: tuple[CanonicalReference, ...] = ()
    capability_refs: tuple[CanonicalReference, ...] = (); relationship_refs: tuple[CanonicalReference, ...] = ()
    blocker_refs: tuple[CanonicalReference, ...] = (); next_action_refs: tuple[CanonicalReference, ...] = ()
    freshness_timestamp_ms: int = 0; freshness_class: str = "CURRENT"; completeness_warnings: tuple[str, ...] = ()
    privacy_class: str = "MINIMUM_SUFFICIENT"; egress_class: str = "LOCAL_ONLY"; projection_only: bool = True
    authority: AuthorityEnvelope = AuthorityEnvelope(); projection_digest: str = ""; version: str = PROJECT_CONTEXT_PROJECTION_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self,"projection_id",_id(self.projection_id,"project.projection_id")); object.__setattr__(self,"project_ref",_text(self.project_ref,"project.project_ref"))
        object.__setattr__(self,"canonical_owner",_id(self.canonical_owner,"project.canonical_owner")); object.__setattr__(self,"objective_digest",_digest(self.objective_digest,"project.objective_digest")); object.__setattr__(self,"purpose_digest",_digest(self.purpose_digest,"project.purpose_digest"))
        if not isinstance(self.repository_identity, RepositoryIdentity): object.__setattr__(self,"repository_identity",RepositoryIdentity.from_dict(self.repository_identity))
        seen: set[str] = set()
        for name in _REFERENCE_FIELDS:
            raw = getattr(self,name)
            if isinstance(raw,(str,bytes,bytearray)) or not isinstance(raw,Sequence) or len(raw)>MAX_ITEMS: raise ValueError(f"project.{name} must be a bounded sequence")
            refs=tuple(x if isinstance(x,CanonicalReference) else CanonicalReference.from_dict(x) for x in raw)
            for ref in refs:
                if ref.reference_id in seen: raise ValueError(f"duplicate project reference: {ref.reference_id}")
                seen.add(ref.reference_id)
            object.__setattr__(self,name,refs)
        if not self.artifact_evidence_refs: raise ValueError("artifact_evidence_refs must not be empty")
        object.__setattr__(self,"freshness_timestamp_ms",_int(self.freshness_timestamp_ms,"project.freshness_timestamp_ms",0,2**63-1))
        if self.freshness_class not in _FRESHNESS: raise ValueError("unsupported project freshness")
        object.__setattr__(self,"completeness_warnings",_seq(self.completeness_warnings,"project.completeness_warnings",max_items=128,sort=True))
        object.__setattr__(self,"privacy_class",_id(self.privacy_class,"project.privacy_class")); object.__setattr__(self,"egress_class",_id(self.egress_class,"project.egress_class")); _bool(self.projection_only,"project.projection_only",True)
        if not isinstance(self.authority,AuthorityEnvelope): object.__setattr__(self,"authority",AuthorityEnvelope.from_dict(self.authority))
        if self.version != PROJECT_CONTEXT_PROJECTION_VERSION: raise ValueError("unsupported project version")
        _set_record_digest(self,"projection_digest")

    def all_references(self) -> tuple[CanonicalReference,...]: return tuple(x for name in _REFERENCE_FIELDS for x in getattr(self,name))

    def to_dict(self) -> dict[str,Any]:
        result={"version":self.version,"projection_id":self.projection_id,"project_ref":self.project_ref,"canonical_owner":self.canonical_owner,"objective_digest":self.objective_digest,"purpose_digest":self.purpose_digest,"repository_identity":self.repository_identity.to_dict(),"freshness_timestamp_ms":self.freshness_timestamp_ms,"freshness_class":self.freshness_class,"completeness_warnings":list(self.completeness_warnings),"privacy_class":self.privacy_class,"egress_class":self.egress_class,"projection_only":self.projection_only,"authority":self.authority.to_dict(),"projection_digest":self.projection_digest}
        result.update({name:[x.to_dict() for x in getattr(self,name)] for name in _REFERENCE_FIELDS}); return result

    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"ProjectContextProjection":
        _strict(payload,{"version","projection_id","project_ref","canonical_owner","objective_digest","purpose_digest","repository_identity","freshness_timestamp_ms","freshness_class","completeness_warnings","privacy_class","egress_class","projection_only","authority","projection_digest",*_REFERENCE_FIELDS},"project"); return cls(**dict(payload))

    def validate_bindings(self,*,expected_repository_identity_digest:str,expected_project_ref:str|None=None,expected_reference_digests:Mapping[str,str]|None=None,reject_stale:bool=True)->None:
        if self.repository_identity.identity_digest != _digest(expected_repository_identity_digest,"expected repository digest"): raise ValueError("stale repository identity digest")
        if expected_project_ref is not None and self.project_ref != _text(expected_project_ref,"expected project ref"): raise ValueError("stale project reference")
        refs={x.reference_id:x for x in self.all_references()}
        for key,value in (expected_reference_digests or {}).items():
            if key not in refs or refs[key].digest != _digest(value,f"expected reference {key}"): raise ValueError(f"stale evidence digest: {key}")
        if reject_stale and any(x.freshness_class in {"STALE","UNKNOWN"} for x in refs.values()): raise ValueError("stale or unknown project references")


@dataclass(frozen=True)
class WorkspaceBudget:
    wall_time_ms:int=300_000; memory_mb:int=512; context_tokens:int=64_000; output_bytes:int=4_000_000
    tool_calls:int=64; model_calls:int=8; cost_microusd:int=0; network_calls:int=0; device_events:int=100_000
    def __post_init__(self)->None:
        for f in fields(self): object.__setattr__(self,f.name,_int(getattr(self,f.name),f"budget.{f.name}",0,10_000_000_000))
    def to_dict(self)->dict[str,int]: return {f.name:getattr(self,f.name) for f in fields(self)}
    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"WorkspaceBudget": _strict(payload,{f.name for f in fields(cls)},"budget"); return cls(**dict(payload))


@dataclass(frozen=True)
class DependencyEdge:
    source_capability_id:str; target_capability_id:str
    def __post_init__(self)->None:
        object.__setattr__(self,"source_capability_id",_id(self.source_capability_id,"dependency.source")); object.__setattr__(self,"target_capability_id",_id(self.target_capability_id,"dependency.target"))
        if self.source_capability_id==self.target_capability_id: raise ValueError("self dependency is prohibited")
    def to_dict(self)->dict[str,str]: return {"source_capability_id":self.source_capability_id,"target_capability_id":self.target_capability_id}
    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"DependencyEdge": _strict(payload,{"source_capability_id","target_capability_id"},"dependency"); return cls(**dict(payload))


def _acyclic(nodes:Sequence[str],edges:Sequence[DependencyEdge])->None:
    graph={x:[] for x in nodes}; degree={x:0 for x in nodes}
    for edge in edges: graph[edge.source_capability_id].append(edge.target_capability_id); degree[edge.target_capability_id]+=1
    queue=sorted(x for x in nodes if degree[x]==0); count=0
    while queue:
        current=queue.pop(0); count+=1
        for target in graph[current]:
            degree[target]-=1
            if degree[target]==0: queue.append(target); queue.sort()
    if count != len(nodes): raise ValueError("recipe dependency graph contains a cycle")


def _refs(value:Any,name:str)->tuple[CanonicalReference,...]:
    if isinstance(value,(str,bytes,bytearray)) or not isinstance(value,Sequence) or not value or len(value)>MAX_ITEMS: raise ValueError(f"{name} must be a non-empty bounded sequence")
    result=tuple(x if isinstance(x,CanonicalReference) else CanonicalReference.from_dict(x) for x in value)
    if len({x.reference_id for x in result})!=len(result): raise ValueError(f"duplicate {name} IDs")
    return result


def _owner_map(value:Any)->tuple[tuple[str,str],...]:
    items=value.items() if isinstance(value,Mapping) else value
    result=tuple(sorted((_id(k,"handoff key"),_id(v,"handoff owner")) for k,v in items))
    if not result or len({k for k,_ in result})!=len(result): raise ValueError("handoff map must be non-empty and unique")
    return result


@dataclass(frozen=True)
class EphemeralWorkspaceRecipe:
    recipe_id:str; demonstration_id:str; base_manifest_ref:CanonicalReference; canonical_intent_digest:str
    project_projection_id:str; project_projection_digest:str; capability_ids:tuple[str,...]; dependency_edges:tuple[DependencyEdge,...]
    adapter_refs:tuple[CanonicalReference,...]; evidence_refs:tuple[CanonicalReference,...]; domain_owner_handoff_map:tuple[tuple[str,str],...]
    budgets:WorkspaceBudget; renderer_requirements:tuple[str,...]; device_requirements:tuple[str,...]
    allowed_interaction_actions:tuple[str,...]; required_verification_gates:tuple[str,...]; ttl_seconds:int=300
    lifecycle_policy:str="EXPLICIT_COMPLETE_CANCEL_FAILURE_OR_TTL"; dissolution_policy:str="MANDATORY_REVOKE_AND_REMOVE_TEMP_STATE"
    automatic_persistence:bool=False; automatic_resume:bool=False; automatic_promotion:bool=False
    authority:AuthorityEnvelope=AuthorityEnvelope(); recipe_digest:str=""; version:str=EPHEMERAL_WORKSPACE_RECIPE_VERSION

    def __post_init__(self)->None:
        object.__setattr__(self,"recipe_id",_id(self.recipe_id,"recipe.recipe_id")); object.__setattr__(self,"demonstration_id",_id(self.demonstration_id,"recipe.demonstration_id"))
        if not isinstance(self.base_manifest_ref,CanonicalReference): object.__setattr__(self,"base_manifest_ref",CanonicalReference.from_dict(self.base_manifest_ref))
        object.__setattr__(self,"canonical_intent_digest",_digest(self.canonical_intent_digest,"recipe.intent")); object.__setattr__(self,"project_projection_id",_id(self.project_projection_id,"recipe.project_id")); object.__setattr__(self,"project_projection_digest",_digest(self.project_projection_digest,"recipe.project_digest"))
        object.__setattr__(self,"capability_ids",_seq(self.capability_ids,"recipe.capabilities",ids=True,max_items=128)); allowed=set(self.capability_ids)
        edges=tuple(x if isinstance(x,DependencyEdge) else DependencyEdge.from_dict(x) for x in self.dependency_edges)
        if len({(x.source_capability_id,x.target_capability_id) for x in edges})!=len(edges) or any(x.source_capability_id not in allowed or x.target_capability_id not in allowed for x in edges): raise ValueError("invalid recipe dependency")
        _acyclic(self.capability_ids,edges); object.__setattr__(self,"dependency_edges",tuple(sorted(edges,key=lambda x:(x.source_capability_id,x.target_capability_id))))
        object.__setattr__(self,"adapter_refs",_refs(self.adapter_refs,"adapter_refs")); object.__setattr__(self,"evidence_refs",_refs(self.evidence_refs,"evidence_refs")); object.__setattr__(self,"domain_owner_handoff_map",_owner_map(self.domain_owner_handoff_map))
        if not isinstance(self.budgets,WorkspaceBudget): object.__setattr__(self,"budgets",WorkspaceBudget.from_dict(self.budgets))
        for name,ids,limit in (("renderer_requirements",False,32),("device_requirements",False,32),("allowed_interaction_actions",True,64),("required_verification_gates",True,64)):
            object.__setattr__(self,name,_seq(getattr(self,name),f"recipe.{name}",ids=ids,max_items=limit,sort=not ids))
        object.__setattr__(self,"ttl_seconds",_int(self.ttl_seconds,"recipe.ttl",1,MAX_TTL_SECONDS)); object.__setattr__(self,"lifecycle_policy",_id(self.lifecycle_policy,"recipe.lifecycle")); object.__setattr__(self,"dissolution_policy",_id(self.dissolution_policy,"recipe.dissolution"))
        for name in ("automatic_persistence","automatic_resume","automatic_promotion"): _bool(getattr(self,name),f"recipe.{name}",False)
        if not isinstance(self.authority,AuthorityEnvelope): object.__setattr__(self,"authority",AuthorityEnvelope.from_dict(self.authority))
        if self.version!=EPHEMERAL_WORKSPACE_RECIPE_VERSION: raise ValueError("unsupported recipe version")
        _set_record_digest(self,"recipe_digest")

    def to_dict(self)->dict[str,Any]:
        return {"version":self.version,"recipe_id":self.recipe_id,"demonstration_id":self.demonstration_id,"base_manifest_ref":self.base_manifest_ref.to_dict(),"canonical_intent_digest":self.canonical_intent_digest,"project_projection_id":self.project_projection_id,"project_projection_digest":self.project_projection_digest,"capability_ids":list(self.capability_ids),"dependency_edges":[x.to_dict() for x in self.dependency_edges],"adapter_refs":[x.to_dict() for x in self.adapter_refs],"evidence_refs":[x.to_dict() for x in self.evidence_refs],"domain_owner_handoff_map":dict(self.domain_owner_handoff_map),"budgets":self.budgets.to_dict(),"renderer_requirements":list(self.renderer_requirements),"device_requirements":list(self.device_requirements),"allowed_interaction_actions":list(self.allowed_interaction_actions),"required_verification_gates":list(self.required_verification_gates),"ttl_seconds":self.ttl_seconds,"lifecycle_policy":self.lifecycle_policy,"dissolution_policy":self.dissolution_policy,"automatic_persistence":self.automatic_persistence,"automatic_resume":self.automatic_resume,"automatic_promotion":self.automatic_promotion,"authority":self.authority.to_dict(),"recipe_digest":self.recipe_digest}

    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"EphemeralWorkspaceRecipe":
        expected={"version","recipe_id","demonstration_id","base_manifest_ref","canonical_intent_digest","project_projection_id","project_projection_digest","capability_ids","dependency_edges","adapter_refs","evidence_refs","domain_owner_handoff_map","budgets","renderer_requirements","device_requirements","allowed_interaction_actions","required_verification_gates","ttl_seconds","lifecycle_policy","dissolution_policy","automatic_persistence","automatic_resume","automatic_promotion","authority","recipe_digest"}; _strict(payload,expected,"recipe"); return cls(**dict(payload))

    def validate_bindings(self,*,expected_intent_digest:str,expected_project_projection_digest:str,expected_base_manifest_digest:str,expected_adapter_digests:Mapping[str,str],expected_evidence_digests:Mapping[str,str])->None:
        for actual,expected,message in ((self.canonical_intent_digest,expected_intent_digest,"stale canonical intent digest"),(self.project_projection_digest,expected_project_projection_digest,"stale project projection digest"),(self.base_manifest_ref.digest,expected_base_manifest_digest,"stale base manifest digest")):
            if actual!=_digest(expected,message): raise ValueError(message)
        for refs,expected,kind in ((self.adapter_refs,expected_adapter_digests,"adapter"),(self.evidence_refs,expected_evidence_digests,"evidence")):
            current={x.reference_id:x for x in refs}
            if set(current)!=set(expected): raise ValueError(f"{kind} reference set mismatch")
            if any(current[k].digest!=_digest(v,f"expected {kind} {k}") or current[k].freshness_class in {"STALE","UNKNOWN"} for k,v in expected.items()): raise ValueError(f"stale {kind} digest")


@dataclass(frozen=True)
class SpatialReferentBinding:
    binding_id:str; scene_id:str; scene_digest:str; session_id:str; session_digest:str; entity_id:str; entity_digest:str
    confidence:float; evidence_ref:CanonicalReference; input_sources:tuple[str,...]; binding_digest:str=""; version:str=SPATIAL_REFERENT_BINDING_VERSION
    def __post_init__(self)->None:
        for name in ("binding_id","scene_id","session_id","entity_id"): object.__setattr__(self,name,_id(getattr(self,name),f"referent.{name}"))
        for name in ("scene_digest","session_digest","entity_digest"): object.__setattr__(self,name,_digest(getattr(self,name),f"referent.{name}"))
        object.__setattr__(self,"confidence",_prob(self.confidence,"referent.confidence"))
        if not isinstance(self.evidence_ref,CanonicalReference): object.__setattr__(self,"evidence_ref",CanonicalReference.from_dict(self.evidence_ref))
        sources=tuple(sorted(x.upper() for x in _seq(self.input_sources,"referent.input_sources",max_items=7)))
        if not sources or not set(sources)<=_INPUTS: raise ValueError("unsupported referent input source")
        object.__setattr__(self,"input_sources",sources)
        if self.version!=SPATIAL_REFERENT_BINDING_VERSION: raise ValueError("unsupported referent version")
        _set_record_digest(self,"binding_digest")
    def to_dict(self)->dict[str,Any]: return {"version":self.version,"binding_id":self.binding_id,"scene_id":self.scene_id,"scene_digest":self.scene_digest,"session_id":self.session_id,"session_digest":self.session_digest,"entity_id":self.entity_id,"entity_digest":self.entity_digest,"confidence":self.confidence,"evidence_ref":self.evidence_ref.to_dict(),"input_sources":list(self.input_sources),"binding_digest":self.binding_digest}
    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"SpatialReferentBinding": _strict(payload,{"version","binding_id","scene_id","scene_digest","session_id","session_digest","entity_id","entity_digest","confidence","evidence_ref","input_sources","binding_digest"},"referent"); return cls(**dict(payload))


@dataclass(frozen=True)
class MultimodalSpatialObservation:
    observation_id:str; scene_id:str; scene_digest:str; session_id:str; session_digest:str; input_sources:tuple[str,...]
    normalized_event:str; normalized_action:str; target_candidates:tuple[SpatialReferentBinding,...]; speech_text:str=""; transcript_digest:str=""
    temporal_window_start_ms:int=0; temporal_window_end_ms:int=0; provider_class:str="LOCAL_NORMALIZED_PROVIDER"
    evidence_class:str="DERIVED"; tracking_quality:float=0.0; raw_sensor_retained:bool=False; authority:AuthorityEnvelope=AuthorityEnvelope()
    observation_digest:str=""; version:str=MULTIMODAL_SPATIAL_OBSERVATION_VERSION
    def __post_init__(self)->None:
        for name in ("observation_id","scene_id","session_id"): object.__setattr__(self,name,_id(getattr(self,name),f"observation.{name}"))
        for name in ("scene_digest","session_digest"): object.__setattr__(self,name,_digest(getattr(self,name),f"observation.{name}"))
        sources=tuple(sorted(x.upper() for x in _seq(self.input_sources,"observation.input_sources",max_items=7)))
        if not sources or not set(sources)<=_INPUTS: raise ValueError("unsupported observation input source")
        object.__setattr__(self,"input_sources",sources); object.__setattr__(self,"normalized_event",_id(self.normalized_event,"observation.event")); object.__setattr__(self,"normalized_action",_id(self.normalized_action,"observation.action"))
        targets=tuple(x if isinstance(x,SpatialReferentBinding) else SpatialReferentBinding.from_dict(x) for x in self.target_candidates)
        if not 1<=len(targets)<=32 or len({x.binding_id for x in targets})!=len(targets): raise ValueError("observation requires unique bounded target bindings")
        for target in targets:
            if (target.scene_id,target.scene_digest,target.session_id,target.session_digest)!=(self.scene_id,self.scene_digest,self.session_id,self.session_digest): raise ValueError("stale referent scene/session")
        object.__setattr__(self,"target_candidates",tuple(sorted(targets,key=lambda x:(-x.confidence,x.binding_id))))
        speech=_text(self.speech_text,"observation.speech",optional=True,maximum=512); transcript=_digest(self.transcript_digest,"observation.transcript",optional=True)
        if speech and not transcript: raise ValueError("speech requires transcript digest")
        object.__setattr__(self,"speech_text",speech); object.__setattr__(self,"transcript_digest",transcript)
        start=_int(self.temporal_window_start_ms,"observation.start",0,2**63-1); end=_int(self.temporal_window_end_ms,"observation.end",0,2**63-1)
        if end<start or end-start>60_000: raise ValueError("invalid temporal binding window")
        object.__setattr__(self,"provider_class",_id(self.provider_class,"observation.provider"))
        if self.evidence_class not in _EVIDENCE: raise ValueError("unsupported observation evidence class")
        object.__setattr__(self,"tracking_quality",_prob(self.tracking_quality,"observation.tracking_quality")); _bool(self.raw_sensor_retained,"observation.raw_sensor_retained",False)
        if not isinstance(self.authority,AuthorityEnvelope): object.__setattr__(self,"authority",AuthorityEnvelope.from_dict(self.authority))
        if self.version!=MULTIMODAL_SPATIAL_OBSERVATION_VERSION: raise ValueError("unsupported observation version")
        _set_record_digest(self,"observation_digest")
    def to_dict(self)->dict[str,Any]: return {"version":self.version,"observation_id":self.observation_id,"scene_id":self.scene_id,"scene_digest":self.scene_digest,"session_id":self.session_id,"session_digest":self.session_digest,"input_sources":list(self.input_sources),"normalized_event":self.normalized_event,"normalized_action":self.normalized_action,"target_candidates":[x.to_dict() for x in self.target_candidates],"speech_text":self.speech_text,"transcript_digest":self.transcript_digest,"temporal_window_start_ms":self.temporal_window_start_ms,"temporal_window_end_ms":self.temporal_window_end_ms,"provider_class":self.provider_class,"evidence_class":self.evidence_class,"tracking_quality":self.tracking_quality,"raw_sensor_retained":self.raw_sensor_retained,"authority":self.authority.to_dict(),"observation_digest":self.observation_digest}
    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"MultimodalSpatialObservation":
        raw=_find_token(payload,_RAW_SENSOR_TOKENS,"observation")
        if raw: raise ValueError(f"raw sensor payload is prohibited: {raw}")
        _strict(payload,{"version","observation_id","scene_id","scene_digest","session_id","session_digest","input_sources","normalized_event","normalized_action","target_candidates","speech_text","transcript_digest","temporal_window_start_ms","temporal_window_end_ms","provider_class","evidence_class","tracking_quality","raw_sensor_retained","authority","observation_digest"},"observation"); return cls(**dict(payload))
    def validate_bindings(self,*,expected_scene_digest:str,expected_session_digest:str,expected_entity_digests:Mapping[str,str])->None:
        if self.scene_digest!=_digest(expected_scene_digest,"expected scene"): raise ValueError("stale scene digest")
        if self.session_digest!=_digest(expected_session_digest,"expected session"): raise ValueError("stale session digest")
        for target in self.target_candidates:
            if target.entity_id not in expected_entity_digests or target.entity_digest!=_digest(expected_entity_digests[target.entity_id],"expected entity"): raise ValueError(f"stale or unknown scene entity: {target.entity_id}")


CODING_SPATIAL_WORKSPACE_V1_DEFINITION={
    "demonstration_id":CODING_SPATIAL_WORKSPACE_V1,
    "capability_ids":["compile_compass_packet","fetch_bounded_neighborhood","open_exact_source_slice","display_tests_and_schemas","compile_candidate_change_graph","prepare_forge_handoff","read_verification_status","display_attempt_archive_evidence","dissolve_workspace"],
    "dependency_edges":[["compile_compass_packet","fetch_bounded_neighborhood"],["fetch_bounded_neighborhood","open_exact_source_slice"],["fetch_bounded_neighborhood","display_tests_and_schemas"],["fetch_bounded_neighborhood","compile_candidate_change_graph"],["compile_candidate_change_graph","prepare_forge_handoff"],["prepare_forge_handoff","read_verification_status"],["read_verification_status","display_attempt_archive_evidence"],["display_attempt_archive_evidence","dissolve_workspace"]],
    "domain_owner_handoff_map":{"architecture":"aura_coding_relationship_compass","code_candidate":"aura_forge","continuity":"aura_unified_memory_continuity","dissolution":"aura_ephemeral_runtime","runtime_proof":"aura_runtime_refactor_harness","semantic_review":"aura_coding_waboose"},
    "renderer_requirements":["ACCESSIBLE_2D_REQUIRED","WEBGL2_OPTIONAL","WEBXR_OPTIONAL"],"device_requirements":["KEYBOARD_REQUIRED","POINTER_OPTIONAL","XR_OPTIONAL"],
    "allowed_interaction_actions":["SELECT","DESELECT","EXPAND","CONTRACT","FOCUS","OPEN_SOURCE","ISOLATE","COMPARE","REQUEST_RELATIONAL_SYNTHESIS","REQUEST_SIMULATION","DISMISS_CANDIDATE","PREPARE_REPAIR_REQUEST","PREPARE_DOMAIN_HANDOFF","CONFIRM_HANDOFF"],
    "required_verification_gates":["EXACT_REPOSITORY_IDENTITY","EXACT_PROJECT_PROJECTION","ADAPTER_IDENTITY","EVIDENCE_FRESHNESS","AUTHORITY_NON_ESCALATION","NO_PRODUCTION_MUTATION","MANDATORY_DISSOLUTION"]}


def _manifest_snapshot(manifest:Any)->tuple[dict[str,Any],str]:
    body=_canonical(manifest.to_dict() if hasattr(manifest,"to_dict") else manifest)
    if not isinstance(body,dict): raise ValueError("base manifest must be an object")
    _text(body.get("manifest_version"),"base manifest version"); _id(body.get("organ_id"),"base organ id")
    supplied=str(manifest.compute_digest() if hasattr(manifest,"compute_digest") else body.get("phase_hash") or "").lower()
    return body,(_digest(supplied,"base manifest digest") if supplied else stable_digest(body))


def compile_coding_spatial_workspace_recipe(*,base_manifest:Any,project_projection:ProjectContextProjection|Mapping[str,Any],canonical_intent_digest:str,adapter_refs:Sequence[CanonicalReference|Mapping[str,Any]],evidence_refs:Sequence[CanonicalReference|Mapping[str,Any]],budgets:WorkspaceBudget|Mapping[str,Any]|None=None,ttl_seconds:int=300)->EphemeralWorkspaceRecipe:
    """Compile the first recipe without invoking any canonical owner."""
    before=canonical_json(base_manifest.to_dict() if hasattr(base_manifest,"to_dict") else base_manifest); body,digest=_manifest_snapshot(base_manifest)
    if before!=canonical_json(base_manifest.to_dict() if hasattr(base_manifest,"to_dict") else base_manifest): raise ValueError("base V1 manifest changed while wrapping")
    project=project_projection if isinstance(project_projection,ProjectContextProjection) else ProjectContextProjection.from_dict(project_projection)
    manifest_ref=CanonicalReference(f"organ-manifest:{body['organ_id']}","aura_ephemeral_manifest",f"ephemeral-organ:{body['organ_id']}@{body['manifest_version']}",digest,metadata={"manifest_version":body["manifest_version"],"wrapped_not_replaced":True})
    definition=CODING_SPATIAL_WORKSPACE_V1_DEFINITION; intent=_digest(canonical_intent_digest,"canonical intent")
    identity={"demonstration_id":CODING_SPATIAL_WORKSPACE_V1,"base_manifest_digest":digest,"intent_digest":intent,"project_projection_digest":project.projection_digest}
    return EphemeralWorkspaceRecipe(f"workspace-recipe:{stable_digest(identity)[:24]}",CODING_SPATIAL_WORKSPACE_V1,manifest_ref,intent,project.projection_id,project.projection_digest,tuple(definition["capability_ids"]),tuple(DependencyEdge(*x) for x in definition["dependency_edges"]),tuple(adapter_refs),tuple(evidence_refs),definition["domain_owner_handoff_map"],budgets or WorkspaceBudget(),tuple(definition["renderer_requirements"]),tuple(definition["device_requirements"]),tuple(definition["allowed_interaction_actions"]),tuple(definition["required_verification_gates"]),ttl_seconds)


__all__=["AUTHORITY_ENVELOPE_VERSION","CANONICAL_REFERENCE_VERSION","CODING_SPATIAL_WORKSPACE_V1","CODING_SPATIAL_WORKSPACE_V1_DEFINITION","EPHEMERAL_WORKSPACE_RECIPE_VERSION","MULTIMODAL_SPATIAL_OBSERVATION_VERSION","PROJECT_CONTEXT_PROJECTION_VERSION","REPOSITORY_IDENTITY_VERSION","SPATIAL_REFERENT_BINDING_VERSION","WORKSPACE_CONTRACTS_VERSION","AuthorityEnvelope","CanonicalReference","DependencyEdge","EphemeralWorkspaceRecipe","MultimodalSpatialObservation","ProjectContextProjection","RepositoryIdentity","SpatialReferentBinding","WorkspaceBudget","canonical_json","compile_coding_spatial_workspace_recipe","stable_digest"]
