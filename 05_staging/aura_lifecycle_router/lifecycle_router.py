from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from enum import Enum
import hashlib, json
from typing import Iterable


def dg(x: object) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class Lifecycle(str, Enum):
    CURRENT_HOT = "CURRENT_HOT"
    HOLD_EXTERNAL = "HOLD_EXTERNAL"
    COLD_ARCHIVE = "COLD_ARCHIVE"
    SUPERSEDED_BUT_PROVENANCE_RETAINED = "SUPERSEDED_BUT_PROVENANCE_RETAINED"
    RETIRED_NO_REOPEN_WITHOUT_INVALIDATOR = "RETIRED_NO_REOPEN_WITHOUT_INVALIDATOR"
    ABSORBED_CANONICAL = "ABSORBED_CANONICAL"
    INVALIDATED = "INVALIDATED"


EVIDENCE_DOMAINS = {
    "SOURCE_SECURITY", "RUNTIME_CAPABILITY", "PHYSICAL_OBSERVATION", "CORRECTNESS",
    "CAUSAL_BENEFIT", "OWNER_AUTHORITY", "LEGAL_COMMUNITY_DISPOSITION", "HUMAN_GATE",
}


@dataclass(frozen=True)
class WakeCondition:
    kind: str
    ref: str
    def validate(self):
        if not self.kind or not self.ref: raise ValueError("WAKE_CONDITION_BINDING_REQUIRED")


@dataclass(frozen=True)
class ArtifactState:
    artifact_id: str
    project: str
    semantic_root: str
    source_ref: str
    owner_ref: str
    lifecycle: Lifecycle
    frame_cut: str
    jurisdiction: str
    wake_conditions: tuple[WakeCondition, ...]
    evidence_domains: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    k27: tuple[int, int, int] | None = None
    effect_authority: bool = False

    def validate(self):
        if not all((self.artifact_id,self.project,self.semantic_root,self.source_ref,self.owner_ref,self.frame_cut,self.jurisdiction)):
            raise ValueError("ARTIFACT_BINDING_REQUIRED")
        if self.effect_authority: raise ValueError("LIFECYCLE_CANNOT_MINT_EFFECT")
        for w in self.wake_conditions: w.validate()
        if any(d not in EVIDENCE_DOMAINS for d in self.evidence_domains): raise ValueError("UNKNOWN_EVIDENCE_DOMAIN")
        if self.k27 is not None and (len(self.k27)!=3 or any((x<0 or x>26) for x in self.k27)):
            raise ValueError("INVALID_K27_ROUTING_COORDINATE")


@dataclass(frozen=True)
class EvidenceLeaf:
    operation_id: str
    domain: str
    source_ref: str
    provider_generation: str
    semantic_root: str
    current: bool
    producer: str
    effect_authority: bool = False
    def validate(self):
        if self.domain not in EVIDENCE_DOMAINS: raise ValueError("UNKNOWN_EVIDENCE_DOMAIN")
        if not all((self.operation_id,self.source_ref,self.provider_generation,self.semantic_root,self.producer)):
            raise ValueError("EVIDENCE_BINDING_REQUIRED")
        if self.effect_authority: raise ValueError("EVIDENCE_LEAF_CANNOT_MINT_EFFECT")


@dataclass(frozen=True)
class ClaimContract:
    claim_id: str
    required_domains: tuple[str, ...]
    target_ref: str
    target_generation: str
    def validate(self):
        if not self.claim_id or not self.target_ref or not self.target_generation: raise ValueError("CLAIM_BINDING_REQUIRED")
        if not self.required_domains or any(d not in EVIDENCE_DOMAINS for d in self.required_domains): raise ValueError("CLAIM_DOMAIN_REQUIRED")


class EvidenceDomainFirewall:
    def admit(self, claim: ClaimContract, leaves: Iterable[EvidenceLeaf]) -> dict:
        claim.validate(); valid=[]
        for leaf in leaves:
            leaf.validate()
            if leaf.current: valid.append(leaf)
        by_domain={}
        for leaf in valid: by_domain.setdefault(leaf.domain,[]).append(leaf)
        missing=tuple(sorted(d for d in set(claim.required_domains) if d not in by_domain))
        return {"status":"CLAIM_EVIDENCE_COMPLETE" if not missing else "HOLD_EVIDENCE_DOMAIN","claim_id":claim.claim_id,"missing_domains":missing,"satisfied_domains":tuple(sorted(set(claim.required_domains)-set(missing))),"operation_ids":tuple(sorted({x.operation_id for x in valid if x.domain in claim.required_domains})),"cross_domain_substitution":False,"effect_authority":False}


class LifecycleAtlas:
    def __init__(self): self._items: dict[str,ArtifactState] = {}
    def register(self, item: ArtifactState) -> str:
        item.validate(); prior=self._items.get(item.artifact_id)
        if prior is not None:
            if prior==item: return "DUPLICATE_COLLAPSED"
            raise ValueError("ARTIFACT_ID_CONFLICT")
        self._items[item.artifact_id]=item; return "REGISTERED"
    def get(self, artifact_id: str) -> ArtifactState: return self._items[artifact_id]
    def transition(self, artifact_id: str, lifecycle: Lifecycle, *, invalidator_ref: str | None = None) -> ArtifactState:
        prior=self._items[artifact_id]
        if prior.lifecycle in {Lifecycle.RETIRED_NO_REOPEN_WITHOUT_INVALIDATOR, Lifecycle.INVALIDATED} and lifecycle==Lifecycle.CURRENT_HOT and not invalidator_ref:
            raise ValueError("REOPEN_INVALIDATOR_REQUIRED")
        if prior.lifecycle==Lifecycle.ABSORBED_CANONICAL and lifecycle==Lifecycle.CURRENT_HOT: raise ValueError("CANONICAL_ALREADY_CURRENT")
        updated=replace(prior,lifecycle=lifecycle); self._items[artifact_id]=updated; return updated
    def supersede(self, old_id: str, new_item: ArtifactState) -> tuple[ArtifactState,ArtifactState]:
        old=self._items[old_id]
        if old.project!=new_item.project: raise ValueError("CROSS_PROJECT_SUPERSESSION_REQUIRES_BRIDGE")
        if old_id not in new_item.supersedes: raise ValueError("SUPERSESSION_EDGE_REQUIRED")
        self.register(new_item); old2=replace(old,lifecycle=Lifecycle.SUPERSEDED_BUT_PROVENANCE_RETAINED); self._items[old_id]=old2
        return old2,new_item
    def active(self, project: str | None = None) -> tuple[ArtifactState,...]:
        rows=[x for x in self._items.values() if x.lifecycle in {Lifecycle.CURRENT_HOT,Lifecycle.ABSORBED_CANONICAL}]
        if project is not None: rows=[x for x in rows if x.project==project]
        return tuple(sorted(rows,key=lambda x:(x.project,x.artifact_id)))
    def provenance(self, project: str | None = None) -> tuple[ArtifactState,...]:
        rows=list(self._items.values())
        if project is not None: rows=[x for x in rows if x.project==project]
        return tuple(sorted(rows,key=lambda x:(x.project,x.artifact_id)))
    def wake(self, artifact_id: str, *, kind: str, ref: str) -> dict:
        item=self._items[artifact_id]; matched=any(w.kind==kind and w.ref==ref for w in item.wake_conditions)
        sleeping=item.lifecycle in {Lifecycle.HOLD_EXTERNAL,Lifecycle.COLD_ARCHIVE,Lifecycle.SUPERSEDED_BUT_PROVENANCE_RETAINED,Lifecycle.RETIRED_NO_REOPEN_WITHOUT_INVALIDATOR}
        return {"status":"WAKE_CANDIDATE" if matched and sleeping else "NO_WAKE","artifact_id":artifact_id,"matched":matched,"effect_authority":False}
    def manifest(self) -> dict:
        rows=[asdict(x) for x in self.provenance()]
        for row in rows: row["lifecycle"]=row["lifecycle"].value
        return {"artifacts":rows,"manifest_root":dg(rows),"effect_authority":False,"k27_authority":False}


@dataclass(frozen=True)
class CurrentnessWitness:
    source_ref: str
    provider_generation: str
    semantic_root: str
    current: bool
    observed_at_ref: str
    producer: str
    effect_authority: bool = False
    def validate(self):
        if not all((self.source_ref,self.provider_generation,self.semantic_root,self.observed_at_ref,self.producer)):
            raise ValueError("CURRENTNESS_WITNESS_BINDING_REQUIRED")
        if self.effect_authority: raise ValueError("CURRENTNESS_WITNESS_CANNOT_MINT_EFFECT")
    @property
    def identity(self) -> str:
        self.validate(); return dg(asdict(self))


@dataclass(frozen=True)
class TransitionIntent:
    objective: str
    source_artifact: str
    destination_project: str
    frame_cut: str
    jurisdiction: str
    currentness: str
    destination_consequence: str
    bridge_ref: str | None = None
    currentness_witness: CurrentnessWitness | None = None
    effect_claim: str = "NONE"


class TransitionRouter:
    """Derived cross-project routing only; never owns truth/currentness/authority/effect."""
    def __init__(self, atlas: LifecycleAtlas): self.atlas=atlas
    def compile(self, t: TransitionIntent) -> dict:
        if not all((t.objective,t.source_artifact,t.destination_project,t.frame_cut,t.jurisdiction,t.currentness,t.destination_consequence)):
            raise ValueError("TRANSITION_BINDING_REQUIRED")
        source=self.atlas.get(t.source_artifact)
        if source.lifecycle not in {Lifecycle.CURRENT_HOT,Lifecycle.ABSORBED_CANONICAL}: return {"status":"HOLD_SOURCE_NOT_HOT","effect_authority":False}
        if t.currentness!="CURRENT": return {"status":"HOLD_CURRENTNESS","effect_authority":False}
        witness=t.currentness_witness
        if witness is None: return {"status":"HOLD_CURRENTNESS_WITNESS_REQUIRED","effect_authority":False}
        witness.validate()
        if not witness.current: return {"status":"HOLD_CURRENTNESS","effect_authority":False}
        if witness.source_ref!=source.source_ref: return {"status":"HOLD_CURRENTNESS_SOURCE_MISMATCH","effect_authority":False}
        if witness.semantic_root!=source.semantic_root: return {"status":"HOLD_CURRENTNESS_SEMANTIC_MISMATCH","effect_authority":False}
        if source.frame_cut!=t.frame_cut: return {"status":"HOLD_INCOHERENT_CUT","effect_authority":False}
        if source.jurisdiction!=t.jurisdiction and not t.bridge_ref: return {"status":"HOLD_JURISDICTION_BRIDGE_REQUIRED","effect_authority":False}
        if t.effect_claim!="NONE": return {"status":"HOLD_EFFECT_OWNER_REQUIRED","effect_authority":False}
        body={"objective":t.objective,"source_artifact":t.source_artifact,"destination_project":t.destination_project,"destination_consequence":t.destination_consequence,"frame_cut":t.frame_cut,"jurisdiction":t.jurisdiction,"bridge_ref":t.bridge_ref,"currentness_witness":witness.identity}
        return {"status":"ROUTED_DERIVED_NO_AUTHORITY_PROMOTION","transition_digest":dg(body),"source_owner_ref":source.owner_ref,"currentness_witness_digest":witness.identity,"effect_authority":False,"new_owner_count":0}


def portfolio_fixture() -> LifecycleAtlas:
    a=LifecycleAtlas()
    a.register(ArtifactState("PR798-SOURCECURSOR3D","AuraOS796","a35c8e717fcb502d80d236931b911f1029fe08c1","github:PR798","github://dallascourchene-commits/AuraOS/pull/798",Lifecycle.CURRENT_HOT,"MAIN:5576537","AURAOS",(WakeCondition("PR_HEAD","798"),WakeCondition("OWNER_DISPOSITION","796")),("SOURCE_SECURITY",),(18,24,10)))
    a.register(ArtifactState("PR799-P0-ADMISSION","ResearchOwnerP0","2487e7eff2f3c6af1330b5352557ccf7af08ce7a","github:PR799","github://dallascourchene-commits/AuraOS/pull/799",Lifecycle.CURRENT_HOT,"MAIN:5576537","AURAOS",(WakeCondition("COMMAND_ACK","AWJ032"),WakeCondition("COMMAND_RESULT","AWJ032")),("OWNER_AUTHORITY","SOURCE_SECURITY")))
    a.register(ArtifactState("PR311-G1","AWJ032-GLM53","d951404e0ba15a04682f47610f4643ce55d9ff7e","github:PR311","github://dallascourchene-commits/AuraOS/pull/311",Lifecycle.CURRENT_HOT,"PR311:d951404","AURAOS",(WakeCondition("PR_HEAD","311"),WakeCondition("P0A_RECEIPT","AWJ032")),("SOURCE_SECURITY",)))
    a.register(ArtifactState("BUGHOUND-CASH-FIDELITY","BugHound","90e9e1fea0135d6ffc83cf3ca3dca79a6e6ed59a93770fa149b006ea347a75c1","drive:bughound","drive:1otDRAyLSgTFiYN5nK6w7twHpBy3uIf9dKF99s0Nx7p0",Lifecycle.HOLD_EXTERNAL,"BUGHOUND:20260903","BUGHOUND",(WakeCondition("AUTHORIZED_REAL_CORPUS","BUGHOUND"),WakeCondition("OWNED_LOCAL_EVM_ORACLE","BUGHOUND")),("CORRECTNESS",)))
    a.register(ArtifactState("MEMORY-CITY-PROJECTION","MemoryCity","projection-v1","drive:memorycity","drive:1XH7kAFtSf5YoZK56gqef25pA9Ki_MoxGjnOGfnWW65c",Lifecycle.CURRENT_HOT,"WORLD:20260903","MEMORY_CITY",(WakeCondition("SOURCE_DELTA","MEMORY_CITY"),),("SOURCE_SECURITY",)))
    a.register(ArtifactState("AURA-WORLD-CIVIC","AuraWorld","civic-derived-v1","drive:auraworld","drive:1jaIHDjyDD6jlzzzaJqFC7GPqKlcimmVC33uVkF9HZIU",Lifecycle.CURRENT_HOT,"WORLD:20260903","AURA_WORLD",(WakeCondition("SOURCE_DELTA","AURA_WORLD"),),("LEGAL_COMMUNITY_DISPOSITION",)))
    return a
