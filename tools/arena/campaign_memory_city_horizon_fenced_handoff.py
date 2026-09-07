import sys,json,hashlib
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_horizon_fenced_handoff import *
R=lambda x:digest(x)
@dataclass(frozen=True)
class ReadCert:
    status:str; coverage_receipt_root:str; program_root:str; sealed_domain_root:str; coverage_generation:int; binding_roots:tuple; member_support_roots:tuple; transition_model_root:str; horizon:int; future_congruence_root:str|None; consequence_root:str; receipt_root:str
@dataclass(frozen=True)
class Use:
    status:str='READY_D0'; reason:str='ok'; certificate_root:str=''
def main():
    keys=['cases','oracle_ready','bridge_ready','uncrossbound_false_ready','bridge_false_ready','bridge_false_hold','full_config_false_hold','consequence_swap','coverage_move','member_move','horizon_move','fence_attack','receipt_attack','valid_irrelevant_context']
    m={k:0 for k in keys}
    for n in range(12000):
        cls=n%8; tag=f'x{n%101}'
        c=ReadCert('READY_D0',R(['coverage',tag]),R(['program',tag]),R(['domain',tag]),4,(R(['b1',tag]),R(['b2',tag])),(R(['s1',tag]),R(['s2',tag])),R(['t',tag]),2,R(['f',tag]),R(['c',tag]),R(['receipt',tag]))
        u=Use(certificate_root=c.receipt_root); sem=semantic_handoff_root(c)
        ev=SemanticHandoffEvidence(read_use_root(c,u),sem,R(['owner',tag]),R(['verify',tag]))
        mut=MutationBoundaryProjection('cell',7,R(['cfg',tag]),11,19,19,'agent',100,sem,R(['trans',tag]),R(['resource',tag]))
        v=HandoffVerificationContext('cell',7,R(['cfg',tag]),11,19,19,R(['owner',tag]),R(['verify',tag]),R(['trans',tag]),R(['resource',tag]),10)
        hidden_equal=True
        if cls==0:
            hidden_equal=False; m['valid_irrelevant_context']+=1
        elif cls==1:
            old=ReadCert(**{**c.__dict__,'consequence_root':R(['old-c',tag]),'receipt_root':R(['old-r',tag])})
            mut=MutationBoundaryProjection(mut.cell_id,mut.revision,mut.configuration_root,mut.support_epoch,mut.fence_generation,mut.installed_fence_generation,mut.holder,mut.expires_at,semantic_handoff_root(old),mut.transition_authority_receipt_root,mut.resource_fence_receipt_root); m['consequence_swap']+=1
        elif cls==2:
            old=ReadCert(**{**c.__dict__,'coverage_generation':3,'receipt_root':R(['old-r2',tag])})
            mut=MutationBoundaryProjection(mut.cell_id,mut.revision,mut.configuration_root,mut.support_epoch,mut.fence_generation,mut.installed_fence_generation,mut.holder,mut.expires_at,semantic_handoff_root(old),mut.transition_authority_receipt_root,mut.resource_fence_receipt_root); m['coverage_move']+=1
        elif cls==3:
            old=ReadCert(**{**c.__dict__,'member_support_roots':(R(['s1',tag]),R(['s3',tag])),'receipt_root':R(['old-r3',tag])})
            mut=MutationBoundaryProjection(mut.cell_id,mut.revision,mut.configuration_root,mut.support_epoch,mut.fence_generation,mut.installed_fence_generation,mut.holder,mut.expires_at,semantic_handoff_root(old),mut.transition_authority_receipt_root,mut.resource_fence_receipt_root); m['member_move']+=1
        elif cls==4:
            c=ReadCert(**{**c.__dict__,'transition_model_root':R(['new-t',tag]),'future_congruence_root':R(['new-f',tag]),'receipt_root':R(['new-r',tag])}); m['horizon_move']+=1
        elif cls==5:
            mut=MutationBoundaryProjection(mut.cell_id,mut.revision,mut.configuration_root,mut.support_epoch,19,18,mut.holder,mut.expires_at,mut.semantic_handoff_root,mut.transition_authority_receipt_root,mut.resource_fence_receipt_root); m['fence_attack']+=1
        elif cls==6:
            ev=SemanticHandoffEvidence(ev.read_use_root,ev.semantic_handoff_root,R(['forged',tag]),ev.verifier_receipt_root); m['receipt_attack']+=1
        expected=semantic_handoff_root(c)
        oracle=(ev.read_use_root==read_use_root(c,u) and ev.semantic_handoff_root==expected and ev.owner_evidence_root==v.owner_evidence_root and ev.verifier_receipt_root==v.verifier_receipt_root and mut.semantic_handoff_root==expected and mut.cell_id==v.cell_id and mut.revision==v.revision and mut.configuration_root==v.configuration_root and mut.support_epoch==v.support_epoch and mut.transition_authority_receipt_root==v.transition_authority_receipt_root and mut.resource_fence_receipt_root==v.resource_fence_receipt_root and mut.fence_generation==v.fence_generation==mut.installed_fence_generation==v.installed_fence_generation and v.now<mut.expires_at)
        uncross=(mut.cell_id==v.cell_id and mut.revision==v.revision and mut.configuration_root==v.configuration_root and mut.support_epoch==v.support_epoch and mut.fence_generation==mut.installed_fence_generation==v.fence_generation==v.installed_fence_generation and v.now<mut.expires_at and ev.owner_evidence_root==v.owner_evidence_root and ev.verifier_receipt_root==v.verifier_receipt_root)
        got=compile_horizon_fenced_handoff(c,u,ev,mut,v).disposition is HandoffDisposition.READY_D0
        full=oracle and hidden_equal
        m['cases']+=1;m['oracle_ready']+=oracle;m['bridge_ready']+=got;m['uncrossbound_false_ready']+=(uncross and not oracle);m['bridge_false_ready']+=(got and not oracle);m['bridge_false_hold']+=((not got) and oracle);m['full_config_false_hold']+=((not full) and oracle)
    assert m['bridge_false_ready']==0 and m['bridge_false_hold']==0
    out={'schema':'AURA-MEMORY-CITY-HFSC-R2-CAMPAIGN-v1','metrics':m};out['campaign_root']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest();print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
