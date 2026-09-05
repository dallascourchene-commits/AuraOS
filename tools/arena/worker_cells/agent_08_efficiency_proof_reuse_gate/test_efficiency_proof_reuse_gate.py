import unittest
from dataclasses import replace, asdict
from decimal import Decimal
from efficiency_proof_reuse_gate import *

H=CURRENT_BASE_HEAD
R='a'*64

def valid_proof():
    return ProofParentEvidence(
        PROOF_PARENT_SEMANTIC_COMMIT,PROOF_PARENT_SOURCE_BLOB,H,H,
        '1'*64,'1'*64,'wf1','wf1','2'*64,'2'*64,'3'*64,'3'*64,'4'*64,'4'*64,1,1,
        True,True,True,False,False,(),False,RESOURCE_TRACE_REPLAY_BENCHMARK,
        '5'*64,'5'*64,'6'*64,'6'*64,'7'*64,'7'*64,True,True,
        '8'*64,'8'*64,'9'*64,'9'*64,'9'*64,True,True,True,
        'NA','NA','NA','NA','NA','NA',False)

def valid_cost():
    samples=(WorkloadSample('s1','code','p1',True),WorkloadSample('s2','reason','p2',True),WorkloadSample('c1','control','p1',False,'shared'))
    transfers=(TransferCharge('t1',1,'s1','DEMAND',1000),TransferCharge('t2',2,'s2','SPECULATIVE',100))
    env=CostEnvelope(H,'rt1','hw1','bench1','2.4','1.0',1_000_000_000,False,False)
    return CostParentEvidence(COST_PARENT_SEMANTIC_COMMIT,COST_PARENT_SOURCE_BLOB,samples,transfers,env)

def valid_evidence():
    p=valid_proof(); c=valid_cost()
    return EfficiencyReuseEvidence('claim','g1',p.projection_root,c.projection_root,p,c)

def oracle_proof_root(p):
    d=asdict(p);d.pop('semantic_commit');d.pop('verifier_blob')
    d['changed_paths']=tuple(sorted(set(d['changed_paths'])))
    return digest(d)

def oracle_parent_decision(p):
    # Independent spelling of the pinned AGENT_27 RESOURCE_TRACE_REPLAY_BENCHMARK exact-reuse path.
    bools=(p.internal_receipt_valid,p.source_truth_bound,p.required_steps_complete,p.direct_child_verified,p.trusted_generator_verified,p.authority_requested,p.cumulative_resource_budget_verified,p.benchmark_oracle_ceiling_verified,p.canonical_trace_schema_verified,p.execution_source_provenance_verified,p.fused_event_structure_verified,p.provider_observation_verified)
    if not all(type(x) is bool for x in bools): return 'REPROVE'
    if p.claim_scope!=RESOURCE_TRACE_REPLAY_BENCHMARK:return 'REPROVE'
    if not (p.internal_receipt_valid and p.source_truth_bound and p.required_steps_complete):return 'REPROVE'
    if not (p.proved_result_root==p.expected_result_root and p.proved_workflow_generation==p.expected_workflow_generation and p.proved_input_root==p.expected_input_root and p.proved_dependency_root==p.expected_dependency_root and p.proved_required_step_root==p.expected_required_step_root and p.proved_binding_generation==p.expected_binding_generation):return 'REPROVE'
    if not (p.proved_trace_root==p.expected_trace_root and p.proved_environment_root==p.expected_environment_root and p.proved_resource_budget_root==p.expected_resource_budget_root and p.cumulative_resource_budget_verified and p.benchmark_oracle_ceiling_verified):return 'REPROVE'
    if not (p.proved_trace_schema_root==p.expected_trace_schema_root and p.proved_event_root==p.expected_event_root==p.reconstructed_event_root and p.canonical_trace_schema_verified and p.execution_source_provenance_verified and p.fused_event_structure_verified):return 'REPROVE'
    if p.authority_requested:return 'REPROVE'
    if p.proved_source_head==p.current_source_head:return 'REUSE_EXACT' if not p.changed_paths else 'REPROVE'
    return 'REPROVE'

def oracle_cost(c):
    e=c.envelope
    cats=tuple(sorted({s.category for s in c.samples if s.ranking_eligible}))
    demand=[t for t in c.transfers if t.kind=='DEMAND']; spec=[t for t in c.transfers if t.kind=='SPECULATIVE']
    db=sum(t.bytes_moved for t in demand);sb=sum(t.bytes_moved for t in spec);rate=Decimal(e.joules_per_gb);budget=Decimal(e.speculative_energy_budget_j)
    ds=lambda x:'0' if x==0 else format(x.normalize(),'f')
    base={'schema':'AURA-WORKLOAD-QUALIFIED-COST-RECEIPT-v1','source_head':e.source_head,'envelope_id':digest(asdict(e)),'workload_root':digest([asdict(s) for s in c.samples]),'transfer_root':digest([asdict(t) for t in c.transfers]),'ranking_categories':cats,'ranking_sample_count':sum(1 for s in c.samples if s.ranking_eligible),'control_sample_count':sum(1 for s in c.samples if not s.ranking_eligible),'transfer_count':len(c.transfers),'demand_transfer_count':len(demand),'speculative_transfer_count':len(spec),'total_bytes':db+sb,'demand_bytes':db,'speculative_bytes':sb,'total_modeled_energy_j':ds(Decimal(db+sb)*rate/Decimal(e.bytes_per_gb)),'demand_modeled_energy_j':ds(Decimal(db)*rate/Decimal(e.bytes_per_gb)),'speculative_modeled_energy_j':ds(Decimal(sb)*rate/Decimal(e.bytes_per_gb)),'speculative_energy_budget_j':ds(budget),'speculative_energy_remaining_j':ds(budget-Decimal(sb)*rate/Decimal(e.bytes_per_gb)),'policy_ranking_eligible':True,'effect_authority':False,'gate10':False}
    return {**base,'result_root':digest(base)}

class T(unittest.TestCase):
    def test_valid_reuse(self): self.assertEqual(assess(valid_evidence()).decision,Decision.REUSE_EXACT)
    def test_receipt_roundtrip(self):
        e=valid_evidence();r=assess(e);self.assertTrue(verify_receipt(e,r));self.assertFalse(verify_receipt(e,replace(r,claim_generation='x')))
    def test_context_bound(self):
        e=valid_evidence();a=assess(e,(1,1,1,1,1));b=assess(e,(1,1,1,1,2));self.assertNotEqual(a.receipt_root,b.receipt_root);self.assertEqual(a.decision,b.decision)
    def test_parent_decision_parity(self):
        p=valid_proof();self.assertEqual(p.parent_decision().value,oracle_parent_decision(p));self.assertEqual(p.parent_evidence_root(),oracle_proof_root(p))
    def test_parent_receipt_exact_shape(self):
        p=valid_proof();r=p.parent_receipt();self.assertEqual(r['decision'],'REUSE_EXACT');self.assertEqual(r['evidence_root'],oracle_proof_root(p));self.assertFalse(r['fresh_hosted_pass']);self.assertFalse(r['authority'])
    def test_parent_false_truth_reproves(self): self.assertEqual(replace(valid_proof(),source_truth_bound=False).parent_decision(),ParentAdmission.REPROVE)
    def test_parent_resource_drift_reproves(self): self.assertEqual(replace(valid_proof(),expected_resource_budget_root='f'*64).parent_decision(),ParentAdmission.REPROVE)
    def test_parent_trace_drift_reproves(self): self.assertEqual(replace(valid_proof(),reconstructed_event_root='f'*64).parent_decision(),ParentAdmission.REPROVE)
    def test_parent_changed_path_reproves(self): self.assertEqual(replace(valid_proof(),changed_paths=('.aura/CODEMAP.md',)).parent_decision(),ParentAdmission.REPROVE)
    def test_parent_generation_pin(self):
        with self.assertRaises(GateError): _=replace(valid_proof(),semantic_commit='0'*40).projection_root
    def test_current_source_pin(self):
        with self.assertRaises(GateError): _=replace(valid_proof(),current_source_head='1'*40).projection_root
    def test_cost_exact_oracle_parity(self): self.assertEqual(valid_cost().independently_compile(),oracle_cost(valid_cost()))
    def test_cost_envelope_includes_authority_fields(self):
        c=valid_cost();got=c.independently_compile();self.assertEqual(got['envelope_id'],digest(asdict(c.envelope)))
    def test_cost_effect_authority_rejected(self):
        c=valid_cost();c=replace(c,envelope=replace(c.envelope,effect_authority=True));
        with self.assertRaises(GateError):c.independently_compile()
    def test_cost_gate10_rejected(self):
        c=valid_cost();c=replace(c,envelope=replace(c.envelope,gate10=True));
        with self.assertRaises(GateError):c.independently_compile()
    def test_cost_prefix_collision_rejected(self):
        c=valid_cost();ss=list(c.samples);ss[1]=replace(ss[1],rendered_prefix='p1');c=replace(c,samples=tuple(ss));
        with self.assertRaises(GateError):c.independently_compile()
    def test_cost_budget_rejected(self):
        c=valid_cost();c=replace(c,envelope=replace(c.envelope,speculative_energy_budget_j='0'));
        with self.assertRaises(GateError):c.independently_compile()
    def test_proof_time_root_drift_reproves(self):
        e=valid_evidence();self.assertEqual(assess(replace(e,proved_proof_projection_root='f'*64)).decision,Decision.REPROVE)
    def test_cost_time_root_drift_reproves(self):
        e=valid_evidence();self.assertEqual(assess(replace(e,proved_cost_projection_root='f'*64)).decision,Decision.REPROVE)
    def test_authority_reproves(self): self.assertEqual(assess(replace(valid_evidence(),authority_requested=True)).decision,Decision.REPROVE)
    def test_malformed_context(self):
        with self.assertRaises(GateError):assess(valid_evidence(),(1,1,1,1,3))
    def test_omega8_exact_keeper(self): self.assertTrue(crystalline_admission((2,2,2,2,2,2,2,1)));self.assertFalse(crystalline_admission((2,2,2,2,2,2,2,2)))
    def test_13d_tail_cannot_repair(self):
        for tail in ((0,0,0,0,0),(2,2,2,2,2)):self.assertFalse(admission_13d((0,2,2,2,2,2,2,1),tail))

if __name__=='__main__':unittest.main()
