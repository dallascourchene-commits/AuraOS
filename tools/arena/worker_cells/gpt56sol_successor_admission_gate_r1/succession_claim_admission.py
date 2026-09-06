from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Iterable, Mapping, Any
from rebase_use_site_admission import D0, ACCEPT, digest, hex64, ConveyorReceiptRef, ReceiptParentBinding, compile_rebase_after_parent_admission

class ClaimDisposition(str, Enum):
    PERSISTED_SUCCESSOR_CLAIM_ACCEPTED='PERSISTED_SUCCESSOR_CLAIM_ACCEPTED'
    HOLD='HOLD'

@dataclass(frozen=True)
class PersistedSuccessionClaim:
    artifact_id:str
    actor_id:str
    predecessor_artifact_id:str
    predecessor_cut:str
    declared_foreign_pair:bool
    parent_receipts:tuple[str,str]
    declared_parent_actor_ids:tuple[str,str]
    parent_pair_root:str
    binding_roots:tuple[str,str]
    objective_seed:str
    authority_ceiling:str=D0
    effect_authority:bool=False
    gate10:bool=False
    @property
    def claim_root(self)->str:
        return digest({'schema':'AURA-PERSISTED-SUCCESSION-CLAIM-R1.3',**asdict(self)})

@dataclass(frozen=True)
class SuccessionClaimAdmissionReceipt:
    admitted:bool
    disposition:ClaimDisposition
    reasons:tuple[str,...]
    claim_root:str
    canonical_pair_root:str|None
    canonical_objective_seed:str|None
    canonical_parent_actor_ids:tuple[str,...]
    k27_coordinate:tuple[int,int,int]
    authority_ceiling:str=D0
    effect_authority:bool=False
    gate10:bool=False

def _k27(root:str)->tuple[int,int,int]:
    slot=int(root[:8],16)%27
    return (slot%3,(slot//3)%3,(slot//9)%3)

def _claim_shape_reasons(c:PersistedSuccessionClaim,ctx:Any)->list[str]:
    r=[]
    if c.authority_ceiling!=D0 or c.effect_authority or c.gate10: r.append('CLAIM_AUTHORITY_WIDENING')
    if type(c.artifact_id) is not str or not c.artifact_id.strip(): r.append('CLAIM_ARTIFACT_ID_INVALID')
    if c.actor_id!=ctx.current_actor_id: r.append('CLAIM_ACTOR_NOT_CURRENT_ACTOR')
    if c.predecessor_artifact_id!=ctx.predecessor_artifact_id: r.append('CLAIM_PREDECESSOR_ARTIFACT_MISMATCH')
    if c.predecessor_cut!=ctx.predecessor_cut: r.append('CLAIM_PREDECESSOR_CUT_MISMATCH')
    if c.declared_foreign_pair is not True: r.append('CLAIM_FOREIGN_PAIR_NOT_ASSERTED')
    if len(c.parent_receipts)!=2 or any(not hex64(x) for x in c.parent_receipts): r.append('CLAIM_PARENT_RECEIPTS_INVALID')
    if len(c.declared_parent_actor_ids)!=2 or any(type(x) is not str or not x.strip() for x in c.declared_parent_actor_ids): r.append('CLAIM_PARENT_ACTORS_INVALID')
    if not hex64(c.parent_pair_root): r.append('CLAIM_PAIR_ROOT_INVALID')
    if len(c.binding_roots)!=2 or any(not hex64(x) for x in c.binding_roots): r.append('CLAIM_BINDING_ROOTS_INVALID')
    if not hex64(c.objective_seed): r.append('CLAIM_OBJECTIVE_SEED_INVALID')
    return r

def _canonical_actors(canonical,bindings:Mapping[str,ReceiptParentBinding])->tuple[str,...]:
    out=[]
    for rd in (canonical.parent_a_receipt,canonical.parent_b_receipt):
        b=bindings.get(rd)
        ir=getattr(getattr(b,'parent_evidence',None),'immediate_receipt',None)
        actor=getattr(ir,'actor_id',None)
        if type(actor) is not str or not actor.strip():
            return ()
        out.append(actor)
    return tuple(out)

def admit_persisted_succession_claim(claim:PersistedSuccessionClaim,receipts:Iterable[ConveyorReceiptRef],bindings:Mapping[str,ReceiptParentBinding],ctx:Any)->SuccessionClaimAdmissionReceipt:
    """R1.3: narrative/persistence claims cannot outrun canonical R1.2/R2 admission.

    A document may *say* it used two foreign parents, but only a fresh canonical rebase
    replay over the exact bound immediate terminals can authorize that label locally.
    """
    reasons=_claim_shape_reasons(claim,ctx)
    canonical=compile_rebase_after_parent_admission(receipts,bindings,ctx)
    actors=_canonical_actors(canonical,bindings) if canonical.admitted else ()
    if not canonical.admitted:
        reasons.append('CANONICAL_REBASE_NOT_ADMITTED')
        reasons.extend('CANONICAL_'+x for x in canonical.reasons)
    else:
        expected_receipts=(canonical.parent_a_receipt,canonical.parent_b_receipt)
        if claim.parent_receipts!=expected_receipts: reasons.append('CLAIM_PARENT_RECEIPTS_MISMATCH')
        if claim.declared_parent_actor_ids!=actors: reasons.append('CLAIM_PARENT_ACTORS_MISMATCH')
        if len(actors)!=2 or actors[0]==claim.actor_id or actors[1]==claim.actor_id: reasons.append('IMMEDIATE_PARENT_NOT_FOREIGN_TO_CLAIM_ACTOR')
        if len(actors)==2 and actors[0]==actors[1]: reasons.append('IMMEDIATE_PARENT_ACTORS_NOT_DISTINCT')
        if claim.parent_pair_root!=canonical.parent_pair_root: reasons.append('CLAIM_PAIR_ROOT_MISMATCH')
        if claim.binding_roots!=canonical.binding_roots: reasons.append('CLAIM_BINDING_ROOTS_MISMATCH')
        if claim.objective_seed!=canonical.objective_seed: reasons.append('CLAIM_OBJECTIVE_SEED_MISMATCH')
    reasons=tuple(sorted(set(reasons)))
    material={'schema':'AURA-SUCCESSION-CLAIM-ADMISSION-R1.3','claim_root':claim.claim_root,'canonical_pair_root':canonical.parent_pair_root,'canonical_seed':canonical.objective_seed,'canonical_actors':actors,'reasons':reasons,'authority_ceiling':D0}
    root=digest(material)
    admitted=not reasons and canonical.admitted and canonical.disposition==ACCEPT
    return SuccessionClaimAdmissionReceipt(admitted,ClaimDisposition.PERSISTED_SUCCESSOR_CLAIM_ACCEPTED if admitted else ClaimDisposition.HOLD,reasons,claim.claim_root,canonical.parent_pair_root,canonical.objective_seed,actors,_k27(root),D0,False,False)

def historical_label_only_accepts(claim:PersistedSuccessionClaim)->bool:
    """Failed-first differential: the narrative-only rule R9 effectively relied upon."""
    return bool(claim.declared_foreign_pair and len(claim.declared_parent_actor_ids)==2 and len(set(claim.declared_parent_actor_ids))==2)
