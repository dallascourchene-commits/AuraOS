from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from enum import Enum
import json
from typing import Any, Callable, Iterable, Mapping, Sequence

D0='D0'
KEEP='KEEP_CANDIDATE'
ACCEPT='FOREIGN_PARENT_PAIR_ACCEPTED'

def canonical(v:Any)->Any:
    if isinstance(v,Enum): return v.value
    if hasattr(v,'__dataclass_fields__'): return canonical(asdict(v))
    if isinstance(v,dict): return {str(k):canonical(v[k]) for k in sorted(v)}
    if isinstance(v,(list,tuple)): return [canonical(x) for x in v]
    if isinstance(v,set): return sorted(canonical(x) for x in v)
    if v is None or isinstance(v,(bool,int,float,str)): return v
    raise TypeError(type(v).__name__)
def digest(v:Any)->str:
    return sha256(json.dumps(canonical(v),sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')).hexdigest()

def hex64(v:object)->bool:
    return type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v)

@dataclass(frozen=True)
class ConveyorReceiptRef:
    capsule_id:str
    lineage_id:str
    consequence_fingerprint:str
    receipt_digest:str
    disposition:str
    effect_authority:bool=False
    gate10:bool=False

@dataclass(frozen=True)
class ReceiptParentBinding:
    conveyor_receipt_digest:str
    parent_evidence:Any
    terminal_receipt_root:str
    source_owner_ref:str
    source_revision_root:str
    authority_ceiling:str=D0
    @property
    def binding_root(self)->str:
        return digest({'schema':'AURA-REBASE-RECEIPT-PARENT-BINDING-v1',
            'conveyor_receipt_digest':self.conveyor_receipt_digest,
            'terminal_receipt_root':self.terminal_receipt_root,
            'source_owner_ref':self.source_owner_ref,
            'source_revision_root':self.source_revision_root,
            'authority_ceiling':self.authority_ceiling})

@dataclass(frozen=True)
class RebaseAdmissionReceipt:
    admitted:bool
    disposition:str
    parent_a_receipt:str|None
    parent_b_receipt:str|None
    parent_pair_root:str|None
    binding_roots:tuple[str,...]
    objective_seed:str|None
    reasons:tuple[str,...]
    authority_ceiling:str=D0
    effect_authority:bool=False
    gate10:bool=False


def _binding_reasons(r:ConveyorReceiptRef,b:ReceiptParentBinding,label:str)->list[str]:
    out=[]
    if b.authority_ceiling!=D0: out.append(label+'_BINDING_AUTHORITY_WIDENING')
    if b.conveyor_receipt_digest!=r.receipt_digest: out.append(label+'_CONVEYOR_RECEIPT_MISMATCH')
    if not hex64(b.terminal_receipt_root): out.append(label+'_TERMINAL_RECEIPT_ROOT_INVALID')
    if type(b.source_owner_ref) is not str or not b.source_owner_ref.strip(): out.append(label+'_SOURCE_OWNER_UNRESOLVED')
    if not hex64(b.source_revision_root): out.append(label+'_SOURCE_REVISION_UNRESOLVED')
    pe=b.parent_evidence
    immediate=getattr(pe,'immediate_receipt',None)
    if immediate is None: out.append(label+'_IMMEDIATE_RECEIPT_REQUIRED')
    else:
        actual=getattr(immediate,'receipt_root',None)
        if actual!=b.terminal_receipt_root: out.append(label+'_TERMINAL_RECEIPT_BINDING_MISMATCH')
    return out


def compile_rebase_after_parent_admission(
    receipts:Iterable[ConveyorReceiptRef],
    bindings:Mapping[str,ReceiptParentBinding],
    ctx:Any,
    admit_pair:Callable[[Sequence[Any],Any],Any],
)->RebaseAdmissionReceipt:
    """Non-owning use-site fence around the conveyor's historical compile_rebase predicate."""
    keep=sorted((r for r in receipts if r.disposition==KEEP and not r.effect_authority and not r.gate10), key=lambda r:(r.capsule_id,r.receipt_digest))
    holds=[]
    for i,a in enumerate(keep):
        for b in keep[i+1:]:
            # Preserve the old cheap prefilter, but never let it mint by itself.
            if a.lineage_id==b.lineage_id or a.consequence_fingerprint==b.consequence_fingerprint:
                continue
            ba=bindings.get(a.receipt_digest); bb=bindings.get(b.receipt_digest)
            if ba is None or bb is None:
                holds.append('PARENT_BINDING_REQUIRED')
                continue
            rs=_binding_reasons(a,ba,'A')+_binding_reasons(b,bb,'B')
            if rs:
                holds.extend(rs); continue
            gate=admit_pair([ba.parent_evidence,bb.parent_evidence],ctx)
            disp=getattr(getattr(gate,'disposition',None),'value',getattr(gate,'disposition',None))
            pair_root=getattr(gate,'pair_root',None)
            auth=getattr(gate,'authority_ceiling',D0)
            if disp!=ACCEPT or auth!=D0 or not hex64(pair_root):
                holds.append('SUCCESSOR_PARENT_GATE_'+str(disp)); continue
            binding_roots=(ba.binding_root,bb.binding_root)
            seed=digest((a.receipt_digest,b.receipt_digest,pair_root,binding_roots,'NEXT_MINIMUM_CONSEQUENCE_CONE'))
            return RebaseAdmissionReceipt(True,ACCEPT,a.receipt_digest,b.receipt_digest,pair_root,binding_roots,seed,(),D0,False,False)
    return RebaseAdmissionReceipt(False,'HOLD',None,None,None,(),None,tuple(sorted(set(holds))) or ('NO_ADMISSIBLE_PARENT_PAIR',),D0,False,False)
