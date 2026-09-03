from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from typing import Iterable


def dg(x: object) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class NegativeKnowledge:
    experiment_id: str
    evidence_generation: str
    failure_class: str
    falsifier_ref: str
    invalidators: tuple[str, ...]
    def validate(self):
        if not all((self.experiment_id,self.evidence_generation,self.failure_class,self.falsifier_ref)):
            raise ValueError("NEGATIVE_KNOWLEDGE_BINDING_REQUIRED")


class NegativeKnowledgeCache:
    def __init__(self): self._rows: dict[tuple[str,str],NegativeKnowledge] = {}
    def record(self, row: NegativeKnowledge) -> str:
        row.validate(); key=(row.experiment_id,row.evidence_generation); prior=self._rows.get(key)
        if prior is not None:
            if prior==row: return "DUPLICATE_COLLAPSED"
            raise ValueError("NEGATIVE_KNOWLEDGE_CONFLICT")
        self._rows[key]=row; return "RECORDED"
    def reusable(self, experiment_id: str, generation: str, observed_invalidators: Iterable[str]=()) -> bool:
        row=self._rows.get((experiment_id,generation))
        if row is None: return False
        return not bool(set(row.invalidators)&set(observed_invalidators))


@dataclass(frozen=True)
class ExperimentCandidate:
    experiment_id: str
    project: str
    evidence_generation: str
    operation_class: str
    prerequisites: tuple[str, ...]
    satisfied_prerequisites: tuple[str, ...]
    cost_units: float
    discrimination_units: float
    emits_domains: tuple[str, ...]
    owner_authorized: bool
    material_delta: bool
    physical: bool
    source_ref: str
    exact_target_ref: str
    reversible: bool = True
    effect_authority: bool = False
    def validate(self):
        if not all((self.experiment_id,self.project,self.evidence_generation,self.operation_class,self.source_ref,self.exact_target_ref)):
            raise ValueError("EXPERIMENT_BINDING_REQUIRED")
        if self.cost_units <= 0 or self.discrimination_units < 0: raise ValueError("INVALID_EXPERIMENT_ECONOMICS")
        if self.effect_authority: raise ValueError("SCHEDULER_CANNOT_MINT_EFFECT")


@dataclass(frozen=True)
class CandidateDecision:
    experiment_id: str
    disposition: str
    missing_prerequisites: tuple[str, ...]
    contribution_domains: tuple[str, ...]
    score: float
    reason: str
    effect_authority: bool = False


class PhysicalEvidenceScheduler:
    """Deterministic cost/discrimination priority only after hard semantic and authority gates."""
    def __init__(self, negative_cache: NegativeKnowledgeCache | None = None): self.negative_cache=negative_cache or NegativeKnowledgeCache()
    def assess(self, c: ExperimentCandidate, *, unresolved_domains: set[str], observed_invalidators: Iterable[str]=()) -> CandidateDecision:
        c.validate(); missing=tuple(sorted(set(c.prerequisites)-set(c.satisfied_prerequisites))); contribution=tuple(sorted(set(c.emits_domains)&set(unresolved_domains)))
        if missing: return CandidateDecision(c.experiment_id,"HOLD_PREDECESSOR",missing,contribution,0.0,"HARD_PREDECESSOR_UNSATISFIED")
        if c.physical and not c.owner_authorized: return CandidateDecision(c.experiment_id,"HOLD_OWNER_AUTHORITY",(),contribution,0.0,"PHYSICAL_OPERATION_NOT_AUTHORIZED")
        if not c.material_delta: return CandidateDecision(c.experiment_id,"NOOP_NO_MATERIAL_DELTA",(),contribution,0.0,"SAME_PROGRESS_FINGERPRINT")
        if self.negative_cache.reusable(c.experiment_id,c.evidence_generation,observed_invalidators): return CandidateDecision(c.experiment_id,"DEPRIORITIZE_NEGATIVE_KNOWLEDGE_REUSE",(),contribution,0.0,"EXACT_GENERATION_FAILURE_ALREADY_KNOWN")
        if not contribution: return CandidateDecision(c.experiment_id,"NOOP_NO_UNRESOLVED_DOMAIN",(),(),0.0,"OPERATION_CANNOT_CHANGE_ACTIVE_EVIDENCE_DEBT")
        score=(c.discrimination_units*len(contribution))/c.cost_units
        return CandidateDecision(c.experiment_id,"ADMISSIBLE_PRIORITY_CANDIDATE",(),contribution,score,"HARD_GATES_SATISFIED_INFORMATION_PER_COST_PROXY")
    def rank(self, candidates: Iterable[ExperimentCandidate], *, unresolved_domains: set[str], observed_invalidators: dict[str,tuple[str,...]]|None=None) -> tuple[CandidateDecision,...]:
        observed_invalidators=observed_invalidators or {}; rows=[self.assess(c,unresolved_domains=unresolved_domains,observed_invalidators=observed_invalidators.get(c.experiment_id,())) for c in candidates]
        rows.sort(key=lambda x:(x.disposition!="ADMISSIBLE_PRIORITY_CANDIDATE",-x.score,x.experiment_id)); return tuple(rows)
    def select(self, candidates: Iterable[ExperimentCandidate], *, unresolved_domains: set[str], observed_invalidators: dict[str,tuple[str,...]]|None=None) -> CandidateDecision | None:
        return next((x for x in self.rank(candidates,unresolved_domains=unresolved_domains,observed_invalidators=observed_invalidators) if x.disposition=="ADMISSIBLE_PRIORITY_CANDIDATE"),None)


GLM_G1="GLM_G1_SECURITY_CURRENT"; GLM_P0A="GLM_P0A_CAPABILITY_CURRENT"; AWJ032_ACK="AWJ032_COMMAND_BOUND_ACK"; BUG_CORPUS="BUGHOUND_AUTHORIZED_REAL_CORPUS"; BUG_EVM="BUGHOUND_OWNED_LOCAL_EVM_ORACLE"


def portfolio_fixture() -> tuple[ExperimentCandidate,...]:
    return (
        ExperimentCandidate("GLM-P1-TRACE","AWJ032-GLM53","PR311:d951404","P1_PHYSICAL_TRACE",(GLM_G1,GLM_P0A,AWJ032_ACK),(GLM_G1,),8.0,9.0,("PHYSICAL_OBSERVATION","CORRECTNESS","RUNTIME_CAPABILITY"),True,True,True,"github:PR311","d951404e0ba15a04682f47610f4643ce55d9ff7e"),
        ExperimentCandidate("GLM-DRAFTEXPERT-TRAIN","AWJ032-GLM53","PR311:d951404","DRAFTEXPERT_TRAIN",(GLM_G1,GLM_P0A,AWJ032_ACK,"GLM_P1_TRACE_PROVEN"),(GLM_G1,),40.0,5.0,("CAUSAL_BENEFIT",),True,True,True,"arxiv:2607.24434","d951404e0ba15a04682f47610f4643ce55d9ff7e"),
        ExperimentCandidate("BUGHOUND-REAL-CORPUS","BugHound","BUGHOUND:20260903","REAL_CORPUS_REPLAY",(BUG_CORPUS,),(),12.0,8.0,("CORRECTNESS","CAUSAL_BENEFIT"),False,True,True,"drive:bughound","BUGHOUND"),
        ExperimentCandidate("BUGHOUND-EVM-ORACLE","BugHound","BUGHOUND:20260903","LOCAL_EVM_ORACLE",(BUG_EVM,),(),15.0,7.0,("CORRECTNESS","PHYSICAL_OBSERVATION"),False,True,True,"drive:bughound","BUGHOUND"),
        ExperimentCandidate("MEMORYCITY-DELTA-REBUILD","MemoryCity","WORLD:20260903","DERIVED_REBUILD",(),(),1.0,3.0,("CORRECTNESS",),True,False,False,"drive:memorycity","MEMORY_CITY"),
        ExperimentCandidate("PR798-PROVIDER-REPLAY","AuraOS796","PR798:a35c8e7","PROVIDER_REPLAY",(),(),1.0,2.0,("CORRECTNESS","SOURCE_SECURITY"),True,False,False,"github:PR798","a35c8e717fcb502d80d236931b911f1029fe08c1"),
    )


def evidence_commitments(c: ExperimentCandidate, decision: CandidateDecision) -> tuple[dict,...]:
    if decision.disposition!="ADMISSIBLE_PRIORITY_CANDIDATE": return ()
    return tuple({"operation_id":c.experiment_id,"domain":domain,"target_ref":c.exact_target_ref,"evidence_generation":c.evidence_generation,"effect_authority":False} for domain in decision.contribution_domains)
