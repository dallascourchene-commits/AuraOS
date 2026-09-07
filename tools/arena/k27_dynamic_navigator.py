from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence
import copy, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
def digest(value: Any) -> str:
    return sha256(canonical(value).encode()).hexdigest()
@dataclass(frozen=True)
class TrafficEvent:
    event_id:str; surface:str; operation:str; locator:str; hydration_level:str; currentness_cut:str; bytes_observed:int=0; objective_signature:str=""; owner_ref:str=""
    def validate(self):
        if not all(isinstance(v,str) and v for v in (self.event_id,self.surface,self.operation,self.locator,self.hydration_level,self.currentness_cut)): raise ValueError("traffic event string fields must be nonempty")
        if self.hydration_level not in {"metadata","snippet","exact"}: raise ValueError("unsupported hydration level")
        if type(self.bytes_observed) is not int or self.bytes_observed<0: raise ValueError("bytes_observed must be a nonnegative int")
@dataclass(frozen=True)
class RouteRegistration:
    route_id:str; route_object_id:str; dependencies:tuple[str,...]; revision_id:str; epoch:int; projection_root:str; execution_authority:bool=False; gate10:bool=False
@dataclass(frozen=True)
class InvalidationPlan:
    changed_object_id:str; cone:tuple[str,...]; affected_routes:tuple[str,...]; reusable_routes:tuple[str,...]; mutation_performed:bool=False; authority_minted:bool=False; gate10:bool=False
@dataclass(frozen=True)
class LawField:
    name:str; allowed_capabilities:frozenset[str]; required_information:frozenset[str]=frozenset(); irreversible_allowed:bool=True; max_effect_cost:int=10**9
@dataclass(frozen=True)
class EffectIntent:
    effect_id:str; required_capability:str; irreversible:bool; effect_cost:int
@dataclass(frozen=True)
class EffectDisposition:
    status:str; checked_nodes:tuple[str,...]; blocking_node:str|None; missing_information:tuple[str,...]=(); effect_authority:bool=False; gate10:bool=False
@dataclass(frozen=True)
class AtUseCapsule:
    object_id:str; revision_id:str; epoch:int; payload_sha256:str; source_url:str; source_version:str; exact_payload:Any; capture_root:str; currentness_scope:str="local registry consistency only"; effect_authority:bool=False; gate10:bool=False
@dataclass(frozen=True)
class NegativeRouteScar:
    scar_id:str; reason:str; max_envelope:Mapping[str,int]; hard_semantic_root:str; evidence_root:str; polarity:str="negative"
@dataclass(frozen=True)
class TrafficSummary:
    events:int; unique_locators:int; repeated_locator_hits:int; metadata_events:int; snippet_events:int; exact_events:int; bytes_observed:int; surfaces:tuple[tuple[str,int],...]; summary_root:str
class K27DynamicNavigator:
    def __init__(self,runtime:Any): self.runtime=runtime; self._routes={}; self._traffic=[]
    @property
    def traffic(self): return tuple(self._traffic)
    def record(self,event:TrafficEvent):
        event.validate()
        if any(old.event_id==event.event_id for old in self._traffic): raise ValueError("duplicate traffic event_id")
        self._traffic.append(event)
    def register_route(self,route_id:str,route_object_id:str)->RouteRegistration:
        if not route_id or not route_object_id: raise ValueError("route_id and route_object_id are required")
        projection=self.runtime.route_projection(route_object_id); binding=projection["binding"]
        dependencies=tuple(sorted(set(projection.get("dependencies",{}))|{route_object_id}))
        reg=RouteRegistration(route_id,route_object_id,dependencies,binding["revision_id"],binding["epoch"],digest(projection)); self._routes[route_id]=reg; return reg
    def plan_invalidation(self,changed_object_id:str)->InvalidationPlan:
        if not changed_object_id: raise ValueError("changed_object_id required")
        raw=self.runtime.invalidation_cone(changed_object_id)
        if raw.get("mutation_performed") is not False: raise ValueError("invalidation planning must be read-only")
        cone={changed_object_id}
        for row in raw.get("affected",()):
            if isinstance(row,Mapping) and row.get("object_id"): cone.add(str(row["object_id"]))
        affected=[]; reusable=[]
        for route_id,reg in sorted(self._routes.items()): (affected if cone.intersection(reg.dependencies) else reusable).append(route_id)
        return InvalidationPlan(changed_object_id,tuple(sorted(cone)),tuple(affected),tuple(reusable))
    @staticmethod
    def compile_effect(route_nodes:Sequence[str],node_laws:Mapping[str,LawField],actor_information:Mapping[str,Iterable[str]],intent:EffectIntent)->EffectDisposition:
        if not route_nodes:return EffectDisposition("HOLD_ROUTE_EMPTY",(),None)
        checked=[]
        for node in route_nodes:
            law=node_laws.get(node)
            if law is None:return EffectDisposition("HOLD_LAWFIELD_UNKNOWN",tuple(checked),node)
            checked.append(node)
            if intent.required_capability not in law.allowed_capabilities:return EffectDisposition("HOLD_CAPABILITY_FORBIDDEN",tuple(checked),node)
            if intent.irreversible and not law.irreversible_allowed:return EffectDisposition("HOLD_IRREVERSIBLE_FRONTIER",tuple(checked),node)
            if type(intent.effect_cost) is not int or intent.effect_cost<0 or intent.effect_cost>law.max_effect_cost:return EffectDisposition("HOLD_EFFECT_BUDGET",tuple(checked),node)
            missing=tuple(sorted(set(law.required_information)-set(actor_information.get(node,()))))
            if missing:return EffectDisposition("HOLD_INFORMATION_EDGE",tuple(checked),node,missing)
        return EffectDisposition("READY_DISTRIBUTED_REALISABILITY_D0",tuple(checked),None)
    def capture_at_use(self,object_id:str)->AtUseCapsule:
        binding,record=self.runtime.read(object_id); exact_payload=copy.deepcopy(record["payload"])
        material={"object_id":binding.object_id,"revision_id":binding.revision_id,"epoch":binding.epoch,"payload_sha256":binding.payload_sha256,"source_url":record["source_url"],"source_version":record["source_version"],"payload":exact_payload}
        return AtUseCapsule(binding.object_id,binding.revision_id,binding.epoch,binding.payload_sha256,record["source_url"],record["source_version"],exact_payload,digest(material))
    @staticmethod
    def classify_negative_scar(scar:NegativeRouteScar,current_envelope:Mapping[str,int],current_hard_semantic_root:str,*,currentness_only_movement:bool=False)->str:
        if scar.polarity!="negative": return "RECHECK_POSITIVE_AT_USE"
        if not scar.hard_semantic_root or scar.hard_semantic_root!=current_hard_semantic_root:return "REPROVE_NEGATIVE"
        if set(current_envelope)!=set(scar.max_envelope):return "REPROVE_NEGATIVE"
        for key,maximum in scar.max_envelope.items():
            current=current_envelope[key]
            if type(maximum) is not int or type(current) is not int or current>maximum:return "REPROVE_NEGATIVE"
        return "REBIND_NEGATIVE_CURRENTNESS" if currentness_only_movement else "REUSE_NEGATIVE"
def summarize_traffic(events:Iterable[TrafficEvent])->TrafficSummary:
    rows=list(events); seen=set(); surface_counts={}; locators=[]; levels={"metadata":0,"snippet":0,"exact":0}; bytes_observed=0
    for row in rows:
        row.validate()
        if row.event_id in seen:raise ValueError("duplicate traffic event_id")
        seen.add(row.event_id); locators.append(row.locator); surface_counts[row.surface]=surface_counts.get(row.surface,0)+1; levels[row.hydration_level]+=1; bytes_observed+=row.bytes_observed
    unique=len(set(locators)); payload={"events":[asdict(e) for e in rows],"surface_counts":sorted(surface_counts.items())}
    return TrafficSummary(len(rows),unique,len(rows)-unique,levels["metadata"],levels["snippet"],levels["exact"],bytes_observed,tuple(sorted(surface_counts.items())),digest(payload))
