import itertools, os, random, sys, unittest
from dataclasses import replace
ROOT=os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0,os.path.join(ROOT,'tools','arena'))
from proof_reuse_admission import *

def base():
    return ProofReuseEvidence('h','h','r','r','w','w','i','i','d','d','s','s',1,1,True,True,True)
def resource():
    return replace(base(),claim_scope=RESOURCE_SENSITIVE_BENCHMARK,proved_trace_root='t',expected_trace_root='t',
        proved_environment_root='e',expected_environment_root='e',proved_resource_budget_root='b',expected_resource_budget_root='b',
        cumulative_resource_budget_verified=True,benchmark_oracle_ceiling_verified=True)
def trace():
    return replace(base(),claim_scope=TRACE_REPLAY_PROOF,proved_trace_schema_root='schema',expected_trace_schema_root='schema',
        proved_event_root='event',expected_event_root='event',reconstructed_event_root='event',canonical_trace_schema_verified=True,
        execution_source_provenance_verified=True,fused_event_structure_verified=True)
def both():
    return replace(resource(),claim_scope=RESOURCE_TRACE_REPLAY_BENCHMARK,proved_trace_schema_root='schema',expected_trace_schema_root='schema',
        proved_event_root='event',expected_event_root='event',reconstructed_event_root='event',canonical_trace_schema_verified=True,
        execution_source_provenance_verified=True,fused_event_structure_verified=True)
def rebound(e=base(), child='h2', paths=('.aura/CODEMAP.md',), generator='AURAOS_CODEMAP_BOT'):
    root=rebind_observation_root(e.proved_source_head,child,generator,paths)
    return replace(e,current_source_head=child,direct_child_verified=True,trusted_generator_verified=True,provider_observation_verified=True,
        changed_paths=paths,rebind_parent_head=e.proved_source_head,rebind_child_head=child,observed_generator_identity=generator,
        expected_generator_identity=generator,provider_observation_root=root,expected_provider_observation_root=root)

def oracle(e, allowlist=DEFAULT_GENERATED_ALLOWLIST):
    resource_ok=e.claim_scope not in {RESOURCE_SENSITIVE_BENCHMARK,RESOURCE_TRACE_REPLAY_BENCHMARK} or (
        e.proved_trace_root==e.expected_trace_root and e.proved_environment_root==e.expected_environment_root and
        e.proved_resource_budget_root==e.expected_resource_budget_root and e.cumulative_resource_budget_verified and e.benchmark_oracle_ceiling_verified)
    trace_ok=e.claim_scope not in {TRACE_REPLAY_PROOF,RESOURCE_TRACE_REPLAY_BENCHMARK} or (
        e.proved_trace_schema_root==e.expected_trace_schema_root and e.proved_event_root==e.expected_event_root==e.reconstructed_event_root and
        e.canonical_trace_schema_verified and e.execution_source_provenance_verified and e.fused_event_structure_verified)
    core=e.internal_receipt_valid and e.source_truth_bound and e.required_steps_complete and e.proved_result_root==e.expected_result_root and \
        e.proved_workflow_generation==e.expected_workflow_generation and e.proved_input_root==e.expected_input_root and \
        e.proved_dependency_root==e.expected_dependency_root and e.proved_required_step_root==e.expected_required_step_root and \
        e.proved_binding_generation==e.expected_binding_generation and resource_ok and trace_ok and not e.authority_requested
    if not core:return Admission.REPROVE
    try: changed=tuple(sorted(set(e.changed_paths))); allowed=set(allowlist)
    except Exception:return Admission.REPROVE
    if e.proved_source_head==e.current_source_head:return Admission.REUSE_EXACT if not changed else Admission.REPROVE
    if not set(changed)<=allowed:return Admission.REPROVE
    try: computed=rebind_observation_root(e.rebind_parent_head,e.rebind_child_head,e.observed_generator_identity,changed)
    except Exception:return Admission.REPROVE
    bound=(e.direct_child_verified and e.trusted_generator_verified and e.provider_observation_verified and
           e.rebind_parent_head==e.proved_source_head and e.rebind_child_head==e.current_source_head and
           e.observed_generator_identity==e.expected_generator_identity and
           e.provider_observation_root==e.expected_provider_observation_root==computed)
    return Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND if bound else Admission.REPROVE

class T(unittest.TestCase):
    def test_01_general_exact_and_hard_gates(self):
        self.assertEqual(decide(base()),Admission.REUSE_EXACT)
        for e in [replace(base(),source_truth_bound=False),replace(base(),internal_receipt_valid=False),replace(base(),required_steps_complete=False),replace(base(),expected_result_root='x'),replace(base(),authority_requested=True)]:self.assertEqual(decide(e),Admission.REPROVE)
    def test_02_bare_rebind_booleans_no_longer_suffice(self):
        old=replace(base(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=('.aura/CODEMAP.md',));self.assertEqual(decide(old),Admission.REPROVE)
    def test_03_bound_rebind_succeeds(self):self.assertEqual(decide(rebound()),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
    def test_04_rebind_parent_child_generator_and_observation_are_noncompensatory(self):
        e=rebound();bad=[replace(e,rebind_parent_head='other'),replace(e,rebind_child_head='other'),replace(e,expected_generator_identity='OTHER'),replace(e,provider_observation_root='0'*64),replace(e,expected_provider_observation_root='f'*64),replace(e,provider_observation_verified=False),replace(e,direct_child_verified=False),replace(e,trusted_generator_verified=False)]
        for x in bad:self.assertEqual(decide(x),Admission.REPROVE)
    def test_05_live_codemap_transition(self):
        parent='0e1aba9dd0ba4fd57c25c90764959f618ff8c990';child='fe19118995a5619ce8bdd32efcf037574705ea17';paths=('.aura/CODEMAP.json','.aura/CODEMAP.md');e=replace(base(),proved_source_head=parent,current_source_head=child);e=rebound(e,child=child,paths=paths,generator='AuraOS CODEMAP Bot');self.assertEqual(e.rebind_parent_head,parent);self.assertEqual(decide(e),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND);r=make_receipt(e);self.assertTrue(r.verify(e));self.assertFalse(r.fresh_hosted_pass);self.assertFalse(r.authority)
    def test_06_receipt_binds_allowlist_policy(self):
        e=rebound(base(),child='h2',paths=('generated/x',),generator='GEN');custom=('generated/x',);r=make_receipt(e,allowlist=custom);self.assertTrue(r.verify(e,allowlist=custom));self.assertFalse(r.verify(e));self.assertNotEqual(r.allowlist_root,allowlist_root())
    def test_07_receipt_tamper_and_canonical_paths(self):
        e=rebound();r=make_receipt(e);self.assertTrue(r.verify(e));self.assertFalse(replace(r,evidence_root='0'*64).verify(e));self.assertFalse(replace(r,allowlist_root='0'*64).verify(e));a=rebound(base(),paths=('.aura/CODEMAP.md','.aura/CODEMAP.json','.aura/CODEMAP.md'));b=rebound(base(),paths=('.aura/CODEMAP.json','.aura/CODEMAP.md'));self.assertEqual(evidence_digest(a),evidence_digest(b))
    def test_08_bad_paths_and_shape_fail_closed(self):
        for p in ('../x','/x','a\\b',''):x=replace(base(),current_source_head='h2',direct_child_verified=True,trusted_generator_verified=True,changed_paths=(p,));self.assertEqual(decide(x),Admission.REPROVE)
        for e in [replace(base(),proved_source_head=''),replace(base(),proved_binding_generation=-1),replace(base(),internal_receipt_valid=1),replace(base(),claim_scope='X'),replace(base(),claim_scope=TRACE_REPLAY_PROOF)]:self.assertEqual(decide(e),Admission.REPROVE)
    def test_09_resource_surface(self):
        self.assertEqual(decide(resource()),Admission.REUSE_EXACT)
        for e in [replace(resource(),expected_trace_root='x'),replace(resource(),expected_environment_root='x'),replace(resource(),expected_resource_budget_root='x'),replace(resource(),cumulative_resource_budget_verified=False),replace(resource(),benchmark_oracle_ceiling_verified=False)]:self.assertEqual(decide(e),Admission.REPROVE)
        self.assertEqual(decide(rebound(resource())),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
    def test_10_trace_surface(self):
        self.assertEqual(decide(trace()),Admission.REUSE_EXACT)
        for e in [replace(trace(),expected_trace_schema_root='x'),replace(trace(),expected_event_root='x'),replace(trace(),reconstructed_event_root='x'),replace(trace(),canonical_trace_schema_verified=False),replace(trace(),execution_source_provenance_verified=False),replace(trace(),fused_event_structure_verified=False)]:self.assertEqual(decide(e),Admission.REPROVE)
        self.assertEqual(decide(rebound(trace())),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND)
    def test_11_combined_scope(self):self.assertEqual(decide(both()),Admission.REUSE_EXACT);self.assertEqual(decide(rebound(both())),Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND);self.assertEqual(decide(replace(both(),expected_resource_budget_root='x')),Admission.REPROVE);self.assertEqual(decide(replace(both(),reconstructed_event_root='x')),Admission.REPROVE)
    def test_12_general_omega8_and_13d(self):
        admits=0
        for s in itertools.product((0,1,2),repeat=8):
            e=replace(base(),internal_receipt_valid=s[0]==1,source_truth_bound=s[1]==1,required_steps_complete=s[2]==1,expected_result_root='r' if s[3]==1 else 'x',expected_workflow_generation='w' if s[4]==1 else 'x',expected_input_root='i' if s[5]==1 else 'x',expected_dependency_root='d' if s[6]==1 else 'x',expected_required_step_root='s' if s[7]==1 else 'x');d=decide(e);admits+=d==Admission.REUSE_EXACT
            if 0 in s:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1);bad=replace(base(),source_truth_bound=False)
        for _ in itertools.product((0,1,2),repeat=5):self.assertEqual(decide(bad),Admission.REPROVE)
    def test_13_rebind_omega8(self):
        good=rebound();admits=0
        for s in itertools.product((0,1,2),repeat=8):
            e=replace(good,direct_child_verified=s[0]==1,trusted_generator_verified=s[1]==1,provider_observation_verified=s[2]==1,rebind_parent_head='h' if s[3]==1 else 'x',rebind_child_head='h2' if s[4]==1 else 'x',expected_generator_identity='AURAOS_CODEMAP_BOT' if s[5]==1 else 'x',provider_observation_root=good.provider_observation_root if s[6]==1 else 'x',expected_provider_observation_root=good.provider_observation_root if s[7]==1 else 'x');d=decide(e);admits+=d==Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND
            if 0 in s:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1)
    def test_14_rebind_13d_context_cannot_repair_forged_provider_observation(self):
        bad=replace(rebound(),provider_observation_verified=False)
        for _ in itertools.product((0,1,2),repeat=5):self.assertEqual(decide(bad),Admission.REPROVE)
    def test_15_randomized_general_oracle(self):
        rng=random.Random(27100)
        for _ in range(50000):
            exact,rec,truth,steps,root=[bool(rng.getrandbits(1)) for _ in range(5)];e=replace(base(),current_source_head='h' if exact else 'h2',internal_receipt_valid=rec,source_truth_bound=truth,required_steps_complete=steps,expected_result_root='r' if root else 'x');e=rebound(e) if not exact and rng.getrandbits(1) else e;self.assertEqual(decide(e),oracle(e))
    def test_16_randomized_resource_oracle(self):
        rng=random.Random(27101)
        for _ in range(50000):
            e=resource();exact=bool(rng.getrandbits(1));e=replace(e,current_source_head='h' if exact else 'h2',expected_trace_root='t' if rng.getrandbits(1) else 'x',expected_environment_root='e' if rng.getrandbits(1) else 'x',expected_resource_budget_root='b' if rng.getrandbits(1) else 'x',cumulative_resource_budget_verified=bool(rng.getrandbits(1)),benchmark_oracle_ceiling_verified=bool(rng.getrandbits(1)));e=rebound(e) if not exact and rng.getrandbits(1) else e;self.assertEqual(decide(e),oracle(e))
    def test_17_randomized_trace_oracle(self):
        rng=random.Random(27102)
        for _ in range(50000):
            e=trace();exact=bool(rng.getrandbits(1));e=replace(e,current_source_head='h' if exact else 'h2',expected_trace_schema_root='schema' if rng.getrandbits(1) else 'x',reconstructed_event_root='event' if rng.getrandbits(1) else 'x',canonical_trace_schema_verified=bool(rng.getrandbits(1)),execution_source_provenance_verified=bool(rng.getrandbits(1)),fused_event_structure_verified=bool(rng.getrandbits(1)));e=rebound(e) if not exact and rng.getrandbits(1) else e;self.assertEqual(decide(e),oracle(e))
    def test_18_hs1000_provider_binding_surface(self):
        good=rebound();admits=0
        for parent_i,gen_i,root_i in itertools.product(range(10),repeat=3):
            e=replace(good,rebind_parent_head='h' if parent_i==0 else f'p{parent_i}',expected_generator_identity='AURAOS_CODEMAP_BOT' if gen_i==0 else f'g{gen_i}',provider_observation_root=good.provider_observation_root if root_i==0 else f'r{root_i}');d=decide(e);admits+=d==Admission.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND
            if parent_i or gen_i or root_i:self.assertEqual(d,Admission.REPROVE)
        self.assertEqual(admits,1)
    def test_19_provider_observation_root_is_canonical(self):
        a=rebind_observation_root('p','c','g',('.aura/CODEMAP.md','.aura/CODEMAP.json','.aura/CODEMAP.md'));b=rebind_observation_root('p','c','g',('.aura/CODEMAP.json','.aura/CODEMAP.md'));self.assertEqual(a,b);self.assertNotEqual(a,rebind_observation_root('p','c2','g',('.aura/CODEMAP.json','.aura/CODEMAP.md')))
    def test_20_bound_attestation_remains_nonauthorizing(self):e=rebound();r=make_receipt(e);self.assertFalse(r.authority);self.assertFalse(r.fresh_hosted_pass);self.assertEqual(decide(replace(e,authority_requested=True)),Admission.REPROVE)

class O4EvidenceAncestry(unittest.TestCase):
    @staticmethod
    def _raw(tag='a',note='n'):return (('source',f'src-{tag}'),('trace',f'trace-{tag}'),('cost',f'cost-{tag}'),('note',note))
    def _transition(self,prior=None,current=None,prior_gen='g1',current_gen='g2',changed=('generated/meta.json',),bind=True):
        prior=prior or self._raw('a','old');current=current or self._raw('a','new');keys=('source','trace','cost');p=project_raw_evidence('evidence-v1',prior,keys);c=project_raw_evidence('evidence-v1',current,keys);root=generation_observation_root('owner-A',prior_gen,current_gen,c.full_projection_root,changed) if bind and prior_gen!=current_gen else 'NA'
        return ParentGenerationTransition('owner-A','owner-A',prior_gen,current_gen,'evidence-v1',tuple(prior),tuple(current),keys,p.full_projection_root,p.consequence_projection_root,c.full_projection_root,c.consequence_projection_root,tuple(changed),root,root,bool(bind and prior_gen!=current_gen))
    def test_21_raw_projection_recomputes_and_rejects_duplicate_or_missing_keys(self):
        p=project_raw_evidence('evidence-v1',self._raw(),('source','trace','cost'));self.assertNotEqual(p.full_projection_root,p.consequence_projection_root)
        with self.assertRaises(ValueError):project_raw_evidence('evidence-v1',(('x',1),('x',2)),('x',))
        with self.assertRaises(ValueError):project_raw_evidence('evidence-v1',(('x',1),),('missing',))
        with self.assertRaises(ValueError):project_raw_evidence('evidence-v1',(('x',float('nan')),),('x',))
    def test_22_exact_unchanged_requires_same_generation_projection_and_no_paths(self):
        raw=self._raw('a','same');t=self._transition(raw,raw,'g1','g1',(),False);r=classify_parent_generation(t);self.assertEqual(r.disposition,GenerationDisposition.EXACT_UNCHANGED);self.assertFalse(r.readjudication_required);self.assertFalse(r.auto_admit);self.assertEqual(classify_parent_generation(replace(t,changed_paths=('generated/meta.json',))).disposition,GenerationDisposition.UNKNOWN)
    def test_23_generation_change_same_consequence_is_proof_neutral_rebind(self):
        t=self._transition();r=classify_parent_generation(t);self.assertEqual(r.disposition,GenerationDisposition.PROOF_NEUTRAL_REBIND);self.assertEqual(r.obligations,('CROSS_BINDINGS:READJUDICATE_CURRENTNESS',));self.assertTrue(r.readjudication_required);self.assertFalse(r.auto_admit);self.assertFalse(r.authority);self.assertTrue(r.verify(t))
    def test_24_consequence_change_reproves_only_parent_plus_cross_bindings(self):
        r=classify_parent_generation(self._transition(current=self._raw('b','new')));self.assertEqual(r.disposition,GenerationDisposition.CONSEQUENCE_CHANGED);self.assertEqual(r.obligations,('owner-A:REPROVE_PARENT','CROSS_BINDINGS:READJUDICATE_AFTER_PARENT_PROOF'))
    def test_25_unbound_provider_observation_is_unknown(self):self.assertEqual(classify_parent_generation(self._transition(bind=False)).disposition,GenerationDisposition.UNKNOWN)
    def test_26_projection_root_or_owner_substitution_is_unknown(self):
        t=self._transition()
        for bad in (replace(t,expected_owner_id='other'),replace(t,expected_current_full_projection_root='x'),replace(t,proof_time_consequence_projection_root='x'),replace(t,provider_observation_root='x')):self.assertEqual(classify_parent_generation(bad).disposition,GenerationDisposition.UNKNOWN)
    def test_27_same_generation_raw_evidence_drift_is_unknown_not_rebind(self):
        t=self._transition(self._raw('a','old'),self._raw('a','new'),'g1','g1',(),False);self.assertEqual(classify_parent_generation(t).disposition,GenerationDisposition.UNKNOWN)
    def test_28_o4_omega8_noncompensatory(self):
        good=self._transition();admits=0
        for s in itertools.product((0,1,2),repeat=8):
            t=good
            if s[0]!=1:t=replace(t,expected_owner_id='x')
            if s[1]!=1:t=replace(t,proof_time_full_projection_root='x')
            if s[2]!=1:t=replace(t,expected_current_full_projection_root='x')
            if s[3]!=1:t=replace(t,provider_observation_verified=False)
            if s[4]!=1:t=replace(t,provider_observation_root='x')
            if s[5]!=1:t=replace(t,current_generation='gX')
            if s[6]!=1:t=replace(t,expected_current_consequence_projection_root='x')
            if s[7]!=1:t=replace(t,authority_requested=True)
            d=classify_parent_generation(t).disposition;admits+=d==GenerationDisposition.PROOF_NEUTRAL_REBIND
            if 0 in s:self.assertEqual(d,GenerationDisposition.UNKNOWN)
        self.assertEqual(admits,1)
    def test_29_o4_13d_context_cannot_repair_unknown(self):
        bad=replace(self._transition(),provider_observation_verified=False)
        for _ in itertools.product((0,1,2),repeat=5):self.assertEqual(classify_parent_generation(bad).disposition,GenerationDisposition.UNKNOWN)
    def test_30_o4_hs1000_and_randomized_oracle(self):
        good=self._transition();admit=0
        for owner_i,root_i,provider_i in itertools.product(range(10),repeat=3):
            t=good
            if owner_i:t=replace(t,expected_owner_id=f'o{owner_i}')
            if root_i:t=replace(t,expected_current_full_projection_root=f'r{root_i}')
            if provider_i:t=replace(t,provider_observation_root=f'p{provider_i}')
            d=classify_parent_generation(t).disposition;admit+=d==GenerationDisposition.PROOF_NEUTRAL_REBIND
            if owner_i or root_i or provider_i:self.assertEqual(d,GenerationDisposition.UNKNOWN)
        self.assertEqual(admit,1);rng=random.Random(27103)
        for _ in range(100000):
            consequence_changed=bool(rng.getrandbits(1));bound=bool(rng.getrandbits(1));same_gen=bool(rng.getrandbits(1));unversioned_drift=bool(rng.getrandbits(1));prior=self._raw('a','same' if not unversioned_drift else 'old');current=self._raw('b' if consequence_changed else 'a','same' if not unversioned_drift else 'new')
            if same_gen:t=self._transition(prior,current,'g1','g1',(),False);expected=GenerationDisposition.EXACT_UNCHANGED if prior==current else GenerationDisposition.UNKNOWN
            else:t=self._transition(prior,current,bind=bound);expected=GenerationDisposition.UNKNOWN if not bound else GenerationDisposition.CONSEQUENCE_CHANGED if consequence_changed else GenerationDisposition.PROOF_NEUTRAL_REBIND
            self.assertEqual(classify_parent_generation(t).disposition,expected)

if __name__=='__main__':unittest.main()
