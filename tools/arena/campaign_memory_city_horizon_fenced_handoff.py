import sys,json,hashlib
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_horizon_fenced_handoff import *
R=lambda x:digest(x)
@dataclass(frozen=True)
class Cert:
    disposition:str; support_root:str; influence_root:str; transition_model_root:str; horizon:int; future_congruence_root:str|None; receipt_root:str
@dataclass(frozen=True)
class Use:
    disposition:str='READY_D0'; branch_id:str='b'; hydrate_item_ids:tuple=('A',); reproof_item_ids:tuple=('A','B')
def main():
    m={k:0 for k in ['cases','oracle_ready','bridge_ready','uncrossbound_false_ready','bridge_false_ready','bridge_false_hold','full_config_false_hold','semantic_swap','horizon_move','fence_attack','receipt_attack','revision_move','valid_irrelevant_context']}
    for n in range(12000):
        cls=n%8; tag=f'x{n%101}'; c=Cert('READY_D0',R(['s',tag]),R(['i',tag]),R(['t',tag]),2,R(['f',tag]),R(['receipt',tag])); u=Use(); sem=semantic_handoff_root(c)
        ev=SemanticHandoffEvidence(read_use_root(c,u),sem,R(['owner',tag]),R(['verify',tag]))
        mut=MutationBoundaryProjection('cell',7,R(['cfg',tag]),11,19,19,'agent',100,sem,R(['trans',tag]),R(['resource',tag]))
        v=HandoffVerificationContext('cell',7,R(['cfg',tag]),11,19,19,R(['owner',tag]),R(['verify',tag]),R(['trans',tag]),R(['resource',tag]),10)
        hidden_equal=True
        if cls==0: hidden_equal=False; m['valid_irrelevant_context']+=1
        elif cls==1:
            old=Cert('READY_D0',R(['old-s',tag]),c.influence_root,c.transition_model_root,2,c.future_congruence_root,R(['old-receipt',tag])); oldsem=semantic_handoff_root(old)
            mut=MutationBoundaryProjection(mut.cell_id,mut.revision,mut.configuration_root,mut.support_epoch,mut.fence_generation,mut.installed_fence_generation,mut.holder,mut.expires_at,oldsem,mut.transition_authority_receipt_root,mut.resource_fence_receipt_root); m['semantic_swap']+=1
        elif cls==2:
            c=Cert(c.disposition,c.support_root,c.influence_root,R(['new-t',tag]),2,R(['new-f',tag]),R(['new-receipt',tag])); m['horizon_move']+=1
        elif cls==3:
            mut=MutationBoundaryProjection(mut.cell_id,mut.revision,mut.configuration_root,mut.support_epoch,19,18,mut.holder,mut.expires_at,mut.semantic_handoff_root,mut.transition_authority_receipt_root,mut.resource_fence_receipt_root); m['fence_attack']+=1
        elif cls==4:
            ev=SemanticHandoffEvidence(ev.read_use_root,ev.semantic_handoff_root,R(['forged-owner',tag]),ev.verifier_receipt_root); m['receipt_attack']+=1
        elif cls==5:
            v=HandoffVerificationContext(v.cell_id,8,v.configuration_root,v.support_epoch,v.fence_generation,v.installed_fence_generation,v.owner_evidence_root,v.verifier_receipt_root,v.transition_authority_receipt_root,v.resource_fence_receipt_root,v.now); m['revision_move']+=1
        elif cls==6:
            mut=MutationBoundaryProjection(mut.cell_id,mut.revision,mut.configuration_root,mut.support_epoch,mut.fence_generation,mut.installed_fence_generation,mut.holder,10,mut.semantic_handoff_root,mut.transition_authority_receipt_root,mut.resource_fence_receipt_root)
        try: expected_sem=semantic_handoff_root(c); expected_use=read_use_root(c,u)
        except ValueError: expected_sem=None; expected_use=None
        oracle=(expected_sem is not None and ev.read_use_root==expected_use and ev.semantic_handoff_root==expected_sem and ev.owner_evidence_root==v.owner_evidence_root and ev.verifier_receipt_root==v.verifier_receipt_root and mut.semantic_handoff_root==expected_sem and mut.cell_id==v.cell_id and mut.revision==v.revision and mut.configuration_root==v.configuration_root and mut.support_epoch==v.support_epoch and mut.transition_authority_receipt_root==v.transition_authority_receipt_root and mut.resource_fence_receipt_root==v.resource_fence_receipt_root and mut.fence_generation==v.fence_generation==mut.installed_fence_generation==v.installed_fence_generation and v.now<mut.expires_at)
        uncross=(mut.cell_id==v.cell_id and mut.revision==v.revision and mut.configuration_root==v.configuration_root and mut.support_epoch==v.support_epoch and mut.fence_generation==mut.installed_fence_generation==v.fence_generation==v.installed_fence_generation and v.now<mut.expires_at and ev.owner_evidence_root==v.owner_evidence_root and ev.verifier_receipt_root==v.verifier_receipt_root)
        try: got=compile_horizon_fenced_handoff(c,u,ev,mut,v).disposition is HandoffDisposition.READY_D0
        except ValueError: got=False
        full=oracle and hidden_equal
        m['cases']+=1; m['oracle_ready']+=oracle; m['bridge_ready']+=got; m['uncrossbound_false_ready']+=(uncross and not oracle); m['bridge_false_ready']+=(got and not oracle); m['bridge_false_hold']+=((not got) and oracle); m['full_config_false_hold']+=((not full) and oracle)
    assert m['bridge_false_ready']==0 and m['bridge_false_hold']==0
    out={'schema':'AURA-MEMORY-CITY-HFSC-CAMPAIGN-v1','metrics':m}; out['campaign_root']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest(); print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__': main()
