import itertools, os, random, sys, unittest
from dataclasses import replace
ROOT=os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0,os.path.join(ROOT,'tools','arena'))
from proof_reuse_admission import *

def base():
    return ProofReuseEvidence('h','h','r','r','w','w','i','i','d','d','s','s',1,1,True,True,True)
def resource():
    return replace(base(),claim_scope=RESOURCE_SENSITIVE_BENCHMARK,
        proved_trace_root='t',expected_trace_root='t',proved_environment_root='e',expected_environment_root='e',
        proved_resource_budget_root='b',expected_resource_budget_root='b',cumulative_resource_budget_verified=True,
        benchmark_oracle_ceiling_verified=True)
def trace():
    return replace(base(),claim_scope=TRACE_REPLAY_PROOF,proved_trace_schema_root='schema',expected_trace_schema_root='schema',
        proved_event_root='event',expected_event_root='event',reconstructed_event_root='event',
        canonical_trace_schema_verified=True,execution_source_provenance_verified=True,fused_event_structure_verified=True)
def both():
    return replace(resource(),claim_scope=RESOURCE_TRACE_REPLAY_BENCHMARK,proved_trace_schema_root='schema',
        expected_trace_schema_root='schema',proved_event_root='event',expected_event_root='event',reconstructed_event_root='event',
        canonical_trace_schema_verified=True,execution_source_provenance_verified=True,fused_event_structure_verified=True)

def oracle(e,generated=True):
    resource_ok=e.claim_scope not in {RESOURCE_SENSITIVE_BENCHMARK,RESOURCE_TRACE_REPLAY_BENCHMARK} or (
        e.proved_trace_root==e.expected_trace_root and e.proved_environment_root==e.expected_environment_root and
        e.proved_resource_budget_root==e.expected_resource_budget_root and e.cumulative_resource_budget_verified and
        e.benchmark_oracle_ceiling_verified)
    trace_ok=e.claim_scope not in {TRACE_REPLAY_PROOF,RESOURCE_TRACE_REPLAY_BENCHMARK} or (
        e.proved_trace_schema_root==e.expected_trace_schema_root and e.proved_event_root==e.expected_event_root==e.reconstructed_event_root and
        e.canonical_trace_schema_verified and e.execution_source_provenance_verified and e.fused_event_structure_verified)
    core=e.internal_receipt_valid and e.source_truth_bound and e.required_steps_complete and e.proved_result_root==e.expected_result_root and \
        e.proved_workflow_generation==e.expected_workflow_generation and e.proved_input_root==e.expected_input_root and \
        e.proved_dependency_root==e.expected_dependency_root and e.proved_required_step_root==e.expected_required_step_root and \
        e.proved_binding_generation==e.expected_binding_generation and resource_ok and trace_ok and not e.authority_requested
    if not core:return Admission.REPROVE
    if e.proved_source_head==e.current_source_head:return Admission.REUSE_EXACT if not e.changed_paths else Admission.REPROVE
    return Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND if e.direct_child_verified and e.trusted_generator_verified and generated else Admission.REPROVE

class T(unittest.TestCase):
    def test_01_general_admission_surface(self):
        self.assertEqual(decide(base()),Admission.REUSE_EXACT)
        g=replace(base(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=('.aura/CODEMAP.md',))
        self.assertEqual(decide(g),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
        for e in [replace(base(),source_truth_bound=False),replace(base(),internal_receipt_valid=False),replace(base(),required_steps_complete=False),
                  replace(base(),expected_result_root='x'),replace(base(),authority_requested=True),replace(g,changed_paths=('src/x.py',))]:
            self.assertEqual(decide(e),Admission.REPROVE)
    def test_02_receipt_and_canonical_paths(self):
        e=base();r=make_receipt(e);self.assertTrue(r.verify(e));self.assertFalse(r.authority);self.assertFalse(r.fresh_hosted_pass)
        self.assertFalse(replace(r,evidence_root='0'*64).verify(e));self.assertFalse(r.verify(replace(e,expected_result_root='x')))
        a=replace(base(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=('.aura/CODEMAP.md','.aura/CODEMAP.json','.aura/CODEMAP.md'))
        b=replace(a,changed_paths=('.aura/CODEMAP.json','.aura/CODEMAP.md'));self.assertEqual(evidence_digest(a),evidence_digest(b))
    def test_03_bad_paths_and_allowlist(self):
        for p in ('../x','/x','a\\b',''):
            self.assertEqual(decide(replace(base(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=(p,))),Admission.REPROVE)
        e=replace(base(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=('generated/x',))
        self.assertEqual(decide(e),Admission.REPROVE);self.assertEqual(decide(e,allowlist=('generated/x',)),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
    def test_04_shape_fails_closed(self):
        for e in [replace(base(),proved_source_head=''),replace(base(),proved_binding_generation=-1),replace(base(),internal_receipt_valid=1),replace(base(),claim_scope='X'),replace(base(),claim_scope=TRACE_REPLAY_PROOF)]:
            self.assertEqual(decide(e),Admission.REPROVE)
    def test_05_general_omega8(self):
        admits=0
        for s in itertools.product((0,1,2),repeat=8):
            e=replace(base(),internal_receipt_valid=s[0]==1,source_truth_bound=s[1]==1,required_steps_complete=s[2]==1,
                expected_result_root='r' if s[3]==1 else 'x',expected_workflow_generation='w' if s[4]==1 else 'x',
                expected_input_root='i' if s[5]==1 else 'x',expected_dependency_root='d' if s[6]==1 else 'x',expected_required_step_root='s' if s[7]==1 else 'x')
            d=decide(e);admits+=d==Admission.REUSE_EXACT
            if 0 in s:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1)
    def test_06_general_13d(self):
        bad=replace(base(),source_truth_bound=False)
        for _ in itertools.product((0,1,2),repeat=5):self.assertEqual(decide(bad),Admission.REPROVE)
    def test_07_general_random_oracle(self):
        rng=random.Random(27027)
        for _ in range(50000):
            exact,rec,truth,steps,root,direct,trusted,gen=[rng.choice((0,1)) for _ in range(8)];changed=() if exact else (('.aura/CODEMAP.md',) if gen else ('src/x.py',))
            e=replace(base(),current_source_head='h' if exact else 'h2',internal_receipt_valid=bool(rec),source_truth_bound=bool(truth),required_steps_complete=bool(steps),expected_result_root='r' if root else 'x',direct_child_verified=bool(direct),trusted_generator_verified=bool(trusted),changed_paths=changed)
            self.assertEqual(decide(e),oracle(e,bool(gen)))
    def test_08_resource_surface(self):
        self.assertEqual(decide(resource()),Admission.REUSE_EXACT)
        for e in [replace(resource(),expected_trace_root='x'),replace(resource(),expected_environment_root='x'),replace(resource(),expected_resource_budget_root='x'),replace(resource(),cumulative_resource_budget_verified=False),replace(resource(),benchmark_oracle_ceiling_verified=False)]:
            self.assertEqual(decide(e),Admission.REPROVE)
    def test_09_resource_rebind_receipt(self):
        e=replace(resource(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=('.aura/CODEMAP.md',));self.assertEqual(decide(e),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
        self.assertEqual(decide(replace(e,expected_resource_budget_root='x')),Admission.REPROVE);r=make_receipt(resource());self.assertFalse(r.verify(replace(resource(),expected_environment_root='x')))
    def test_10_resource_omega8_and_13d(self):
        admits=0
        for s in itertools.product((0,1,2),repeat=8):
            e=replace(resource(),internal_receipt_valid=s[0]==1,source_truth_bound=s[1]==1,required_steps_complete=s[2]==1,expected_trace_root='t' if s[3]==1 else 'x',expected_environment_root='e' if s[4]==1 else 'x',expected_resource_budget_root='b' if s[5]==1 else 'x',cumulative_resource_budget_verified=s[6]==1,benchmark_oracle_ceiling_verified=s[7]==1)
            d=decide(e);admits+=d==Admission.REUSE_EXACT
            if 0 in s:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1);bad=replace(resource(),cumulative_resource_budget_verified=False)
        for _ in itertools.product((0,1,2),repeat=5):self.assertEqual(decide(bad),Admission.REPROVE)
    def test_11_resource_random_oracle(self):
        rng=random.Random(27028)
        for _ in range(50000):
            vals=[bool(rng.getrandbits(1)) for _ in range(12)];exact,rec,truth,steps,tr,env,bud,cum,ceil,direct,trusted,gen=vals;changed=() if exact else (('.aura/CODEMAP.md',) if gen else ('src/x.py',))
            e=replace(resource(),current_source_head='h' if exact else 'h2',internal_receipt_valid=rec,source_truth_bound=truth,required_steps_complete=steps,expected_trace_root='t' if tr else 'x',expected_environment_root='e' if env else 'x',expected_resource_budget_root='b' if bud else 'x',cumulative_resource_budget_verified=cum,benchmark_oracle_ceiling_verified=ceil,direct_child_verified=direct,trusted_generator_verified=trusted,changed_paths=changed)
            self.assertEqual(decide(e),oracle(e,gen))
    def test_12_resource_hs1000(self):
        admits=0
        for a,b,c in itertools.product(range(10),repeat=3):
            e=replace(resource(),current_source_head='h' if a==0 else f'h{a}',expected_resource_budget_root='b' if b==0 else f'b{b}',expected_environment_root='e' if c==0 else f'e{c}',direct_child_verified=a!=0,trusted_generator_verified=a!=0,changed_paths=() if a==0 else ('.aura/CODEMAP.md',));d=decide(e);admits+=d!=Admission.REPROVE
            if b or c:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,10)
    def test_13_trace_surface(self):
        self.assertEqual(decide(trace()),Admission.REUSE_EXACT)
        for e in [replace(trace(),expected_trace_schema_root='x'),replace(trace(),expected_event_root='x'),replace(trace(),reconstructed_event_root='x'),replace(trace(),canonical_trace_schema_verified=False),replace(trace(),execution_source_provenance_verified=False),replace(trace(),fused_event_structure_verified=False)]:self.assertEqual(decide(e),Admission.REPROVE)
    def test_14_trace_rebind_receipt(self):
        e=replace(trace(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=('.aura/CODEMAP.md',));self.assertEqual(decide(e),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND);self.assertEqual(decide(replace(e,reconstructed_event_root='x')),Admission.REPROVE)
        r=make_receipt(trace());self.assertFalse(r.verify(replace(trace(),expected_event_root='x')));self.assertFalse(r.verify(replace(trace(),execution_source_provenance_verified=False)))
    def test_15_trace_omega8_and_13d(self):
        admits=0
        for s in itertools.product((0,1,2),repeat=8):
            e=replace(trace(),internal_receipt_valid=s[0]==1,source_truth_bound=s[1]==1,required_steps_complete=s[2]==1,expected_trace_schema_root='schema' if s[3]==1 else 'x',reconstructed_event_root='event' if s[4]==1 else 'x',canonical_trace_schema_verified=s[5]==1,execution_source_provenance_verified=s[6]==1,fused_event_structure_verified=s[7]==1);d=decide(e);admits+=d==Admission.REUSE_EXACT
            if 0 in s:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1);bad=replace(trace(),reconstructed_event_root='x')
        for _ in itertools.product((0,1,2),repeat=5):self.assertEqual(decide(bad),Admission.REPROVE)
    def test_16_trace_random_oracle(self):
        rng=random.Random(27029)
        for _ in range(50000):
            vals=[bool(rng.getrandbits(1)) for _ in range(12)];exact,rec,truth,steps,sch,ev,canon,prov,fused,direct,trusted,gen=vals;changed=() if exact else (('.aura/CODEMAP.md',) if gen else ('src/x.py',))
            e=replace(trace(),current_source_head='h' if exact else 'h2',internal_receipt_valid=rec,source_truth_bound=truth,required_steps_complete=steps,expected_trace_schema_root='schema' if sch else 'x',reconstructed_event_root='event' if ev else 'x',canonical_trace_schema_verified=canon,execution_source_provenance_verified=prov,fused_event_structure_verified=fused,direct_child_verified=direct,trusted_generator_verified=trusted,changed_paths=changed)
            self.assertEqual(decide(e),oracle(e,gen))
    def test_17_trace_hs1000(self):
        admits=0
        for a,b,c in itertools.product(range(10),repeat=3):
            e=replace(trace(),expected_trace_schema_root='schema' if a==0 else f's{a}',expected_event_root='event' if b==0 else f'e{b}',reconstructed_event_root='event' if c==0 else f'r{c}');d=decide(e);admits+=d!=Admission.REPROVE
            if a or b or c:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1)
    def test_18_combined_scope(self):
        self.assertEqual(decide(both()),Admission.REUSE_EXACT);self.assertEqual(decide(replace(both(),expected_resource_budget_root='x')),Admission.REPROVE);self.assertEqual(decide(replace(both(),reconstructed_event_root='x')),Admission.REPROVE)
        self.assertEqual(decide(replace(resource(),claim_scope=RESOURCE_TRACE_REPLAY_BENCHMARK)),Admission.REPROVE)
    def test_19_combined_rebind(self):
        e=replace(both(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=('.aura/CODEMAP.json',));self.assertEqual(decide(e),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
        self.assertEqual(decide(replace(e,expected_trace_schema_root='x')),Admission.REPROVE);self.assertEqual(decide(replace(e,cumulative_resource_budget_verified=False)),Admission.REPROVE)
    def test_20_authority_ceiling(self):
        for e in (base(),resource(),trace(),both()):
            r=make_receipt(e);self.assertFalse(r.authority);self.assertFalse(r.fresh_hosted_pass);self.assertEqual(decide(replace(e,authority_requested=True)),Admission.REPROVE)
if __name__=='__main__':unittest.main()
