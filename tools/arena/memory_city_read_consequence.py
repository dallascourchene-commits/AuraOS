from __future__ import annotations
from dataclasses import dataclass
from k27_dynamic_navigator import digest
from memory_city_support_hydration import SupportClosedHydration
from memory_city_typed_closure import TypedClosureCertificate,TypedClosureDisposition
from memory_city_coverage_membrane import CoverageCertificate,CoverageDisposition,validate_coverage_at_use
D0='D0_NONPROMOTING'
@dataclass(frozen=True)
class ReadWorldBinding:
    hydration: SupportClosedHydration
    typed_closure: TypedClosureCertificate
    def __post_init__(self):
        if not isinstance(self.hydration,SupportClosedHydration):raise ValueError('hydration must be SupportClosedHydration')
        if not isinstance(self.typed_closure,TypedClosureCertificate):raise ValueError('typed_closure must be TypedClosureCertificate')
    @property
    def binding_root(self):
        return digest({'schema':'AURA-MEMORY-CITY-READ-WORLD-BINDING-v1','hydration_receipt_root':self.hydration.receipt_root,'hydration_support_root':self.hydration.support_root,'typed_closure_receipt_root':self.typed_closure.receipt_root})
@dataclass(frozen=True)
class ReadConsequenceCertificate:
    status:str; coverage_receipt_root:str; program_root:str; sealed_domain_root:str; coverage_generation:int
    binding_roots:tuple[str,...]; member_support_roots:tuple[str,...]; member_hydration_receipt_roots:tuple[str,...]
    hydration_cut:tuple[str,...]; reproof_item_ids:tuple[str,...]; transition_model_root:str; horizon:int; future_congruence_root:str|None
    consequence_root:str; receipt_root:str; reason:str=''; authority:str=D0; mutation_authority:bool=False; effect_authority:bool=False; gate10:bool=False
@dataclass(frozen=True)
class ReadConsequenceUseDecision:
    status:str; reason:str; certificate_root:str; mutation_authority:bool=False; effect_authority:bool=False; gate10:bool=False

def _hold(reason,coverage,bindings=()):
    payload={'schema':'AURA-MEMORY-CITY-READ-CONSEQUENCE-CERT-v1','status':'HOLD_D0','coverage_receipt_root':coverage.receipt_root,'reason':reason,'bindings':list(bindings)}
    r=digest(payload)
    return ReadConsequenceCertificate('HOLD_D0',coverage.receipt_root,coverage.program_root,coverage.sealed_domain_root,coverage.generation,tuple(bindings),(),(),(),(),'',0,None,'',r,reason)
def compile_read_consequence_certificate(worlds:tuple[ReadWorldBinding,...],coverage:CoverageCertificate)->ReadConsequenceCertificate:
    if not isinstance(coverage,CoverageCertificate):raise ValueError('coverage must be CoverageCertificate')
    if any(not isinstance(w,ReadWorldBinding) for w in worlds):raise ValueError('worlds must be ReadWorldBinding')
    if not worlds:return _hold('world_envelope_empty',coverage)
    bindings=tuple(w.binding_root for w in worlds)
    if len(set(bindings))!=len(bindings):return _hold('duplicate_world_binding',coverage,bindings)
    if coverage.disposition is not CoverageDisposition.READY:return _hold('coverage_not_ready',coverage,bindings)
    if set(coverage.obligations)!=set(bindings) or coverage.pending:return _hold('coverage_does_not_exactly_cover_world_bindings',coverage,bindings)
    for w in worlds:
        if w.hydration.status!='READY_SUPPORT_CLOSED_HYDRATION_D0' or not w.hydration.support_root:return _hold('hydration_world_not_ready_or_unidentified',coverage,bindings)
        if w.typed_closure.disposition is not TypedClosureDisposition.READY:return _hold('typed_closure_not_ready',coverage,bindings)
    hydration_cuts={tuple(w.hydration.support_cut) for w in worlds}
    reproof_cuts={tuple(w.typed_closure.reproof_item_ids) for w in worlds}
    transitions={(w.typed_closure.transition_model_root,w.typed_closure.horizon,w.typed_closure.future_congruence_root) for w in worlds}
    if len(hydration_cuts)!=1:return _hold('hydration_consequence_diverged',coverage,bindings)
    if len(reproof_cuts)!=1:return _hold('reproof_consequence_diverged',coverage,bindings)
    if len(transitions)!=1:return _hold('transition_consequence_diverged',coverage,bindings)
    hydration_cut=next(iter(hydration_cuts)); reproof=next(iter(reproof_cuts)); transition,horizon,future=next(iter(transitions))
    support_roots=tuple(sorted({w.hydration.support_root for w in worlds})); hydration_receipts=tuple(sorted({w.hydration.receipt_root for w in worlds}))
    consequence_root=digest({'schema':'AURA-MEMORY-CITY-READ-CONSEQUENCE-v1','hydration_cut':hydration_cut,'reproof':reproof,'transition_model_root':transition,'horizon':horizon,'future_congruence_root':future})
    payload={'schema':'AURA-MEMORY-CITY-READ-CONSEQUENCE-CERT-v1','status':'READY_D0','coverage_receipt_root':coverage.receipt_root,'program_root':coverage.program_root,'sealed_domain_root':coverage.sealed_domain_root,'coverage_generation':coverage.generation,'bindings':sorted(bindings),'member_support_roots':support_roots,'member_hydration_receipts':hydration_receipts,'consequence_root':consequence_root,'mutation_authority':False,'effect_authority':False,'gate10':False}
    return ReadConsequenceCertificate('READY_D0',coverage.receipt_root,coverage.program_root,coverage.sealed_domain_root,coverage.generation,tuple(sorted(bindings)),support_roots,hydration_receipts,hydration_cut,reproof,transition,horizon,future,consequence_root,digest(payload))
def validate_read_consequence_at_use(cert:ReadConsequenceCertificate,*,hydration:SupportClosedHydration,fixed_support_root:str,coverage:CoverageCertificate,current_program_root:str,current_sealed_domain_root:str,current_coverage_generation:int,mutation_requested:bool=False)->ReadConsequenceUseDecision:
    if mutation_requested:return ReadConsequenceUseDecision('HOLD_MUTATION_AUTHORITY','read_consequence_certificate_never_authorizes_mutation',cert.receipt_root)
    if cert.status!='READY_D0':return ReadConsequenceUseDecision('HOLD_CERTIFICATE','compiled_read_consequence_not_ready',cert.receipt_root)
    if coverage.receipt_root!=cert.coverage_receipt_root:return ReadConsequenceUseDecision('HOLD_COVERAGE_IDENTITY','coverage_receipt_moved',cert.receipt_root)
    cu=validate_coverage_at_use(coverage,program_root=current_program_root,sealed_domain_root=current_sealed_domain_root,generation=current_coverage_generation,mutation_requested=False)
    if cu.disposition is not CoverageDisposition.READY:return ReadConsequenceUseDecision(cu.disposition.value,cu.reason,cert.receipt_root)
    if hydration.status!='READY_SUPPORT_CLOSED_HYDRATION_D0':return ReadConsequenceUseDecision('HOLD_HYDRATION','active_hydration_not_ready',cert.receipt_root)
    if hydration.receipt_root not in cert.member_hydration_receipt_roots or hydration.support_root not in cert.member_support_roots:return ReadConsequenceUseDecision('HOLD_ACTIVE_WORLD_MEMBERSHIP','active_hydration_world_not_certified',cert.receipt_root)
    if fixed_support_root not in cert.member_support_roots:return ReadConsequenceUseDecision('HOLD_FIXED_WORLD_MEMBERSHIP','fixed_point_world_not_certified',cert.receipt_root)
    if tuple(hydration.support_cut)!=cert.hydration_cut:return ReadConsequenceUseDecision('HOLD_ACTIVE_CONSEQUENCE','active_hydration_consequence_moved',cert.receipt_root)
    return ReadConsequenceUseDecision('READY_D0','complete_current_read_consequence_equivalence',cert.receipt_root)
