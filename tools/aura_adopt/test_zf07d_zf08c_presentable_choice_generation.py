import unittest
import zf07d_zf08c_presentable_choice_generation as m
E='e'*64; D='d'*64

def choice(route='route:local',remote=False,provider='',principal='principal:a'):
    return m.PresentableChoiceEnvelopeV1('owner:zf07a','owner-gen:1',D,principal,'policy-gen:1','source-gen:1','target-gen:1',route,'model:y' if remote else 'model:x',provider,'REMOTE' if remote else 'LOCAL','PAID' if remote else 'INCLUDED',('REMOTE_CONSENT','PAYMENT_CONSENT') if remote else ('DOWNLOAD_CONSENT',),'evidence:'+route.replace(':','-'),E)

def req(c,resolver_generation='resolver-gen:1'):
    kw=dict(resolver_ref='resolver:aura',resolver_generation=resolver_generation,resolver_currentness_ref='resolver-current:1',source_currentness_ref='source-current:1',owner_currentness_ref='owner-current:1',target_currentness_ref='target-current:1',principal_currentness_ref='principal-current:1',source_basis_ref='basis:source',owner_basis_ref='basis:owner',resolver_basis_ref='basis:resolver',target_basis_ref='basis:target',principal_basis_ref='basis:principal')
    if c.execution_location=='REMOTE':kw.update(runtime_cache_route_generation='provider-route-gen:1',runtime_cache_route_currentness_ref='provider-route-current:1',runtime_cache_route_basis_ref='basis:provider-route')
    return m.build_choice_generation_requirement(c,**kw)

class Resolver:
    def __init__(self,overrides=None,replay=None):self.overrides=overrides or {};self.replay=replay or {}
    def resolve_choice_generation(self,q):
        if q.axis in self.replay:return self.replay[q.axis]
        s=self.overrides.get(q.axis,{})
        return m.ChoiceGenerationResolutionV1(s.get('query_digest',q.query_digest),s.get('resolver_ref','resolver:aura'),s.get('resolver_generation','resolver-gen:1'),s.get('resolver_currentness_ref','resolver-current:1'),s.get('proof_ref','proof:'+q.axis.lower()),s.get('currentness_state','CURRENT'),s.get('revoked',False))

class T(unittest.TestCase):
    def test_local_happy(self):
        c=choice();d=m.compile_presentable_choice(c,req(c),resolver=Resolver());self.assertTrue(d['presentable']);self.assertFalse(d['effect_authorized'])
    def test_remote_happy(self):
        c=choice('route:r',True,'provider:b');r=req(c);self.assertIn(m.RUNTIME,r.by_axis());self.assertTrue(m.compile_presentable_choice(c,r,resolver=Resolver())['presentable'])
    def test_no_resolver(self):
        c=choice();d=m.compile_presentable_choice(c,req(c),resolver=None);self.assertEqual(d['blockers'],['GENERATION_RESOLVER_REQUIRED'])
    def test_target_stale_only_blocks_one_choice(self):
        a=choice('route:a');b=choice('route:b')
        class R(Resolver):
            def resolve_choice_generation(self,q):
                state='STALE' if q.choice_digest==a.choice_digest and q.axis==m.TARGET else 'CURRENT'
                return m.ChoiceGenerationResolutionV1(q.query_digest,'resolver:aura','resolver-gen:1','resolver-current:1','proof:'+q.axis.lower(),state,False)
        out=m.compile_presentable_choice_set([(a,req(a)),(b,req(b))],resolver=R());self.assertEqual(out['blocked_route_ids'],['route:a']);self.assertEqual(out['presentable_route_ids'],['route:b'])
    def test_owner_stale(self):
        c=choice();d=m.compile_presentable_choice(c,req(c),resolver=Resolver({m.OWNER:{'currentness_state':'STALE'}}));self.assertIn('GENERATION_NOT_CURRENT:OWNER',d['blockers'])
    def test_resolver_generation_skew(self):
        c=choice();d=m.compile_presentable_choice(c,req(c),resolver=Resolver({m.TARGET:{'resolver_generation':'resolver-gen:0'}}));self.assertIn('RESOLVER_GENERATION_MISMATCH:TARGET',d['blockers'])
    def test_principal_revoked(self):
        c=choice();d=m.compile_presentable_choice(c,req(c),resolver=Resolver({m.PRINCIPAL:{'revoked':True}}));self.assertIn('GENERATION_PROOF_REVOKED:PRINCIPAL_CONTEXT',d['blockers'])
    def test_unknown_source(self):
        c=choice();d=m.compile_presentable_choice(c,req(c),resolver=Resolver({m.SOURCE:{'currentness_state':'UNKNOWN'}}));self.assertIn('GENERATION_NOT_CURRENT:SOURCE',d['blockers'])
    def test_cross_choice_resolution_replay(self):
        a=choice('route:a');ra=req(a);qa=m._query(a,ra,ra.by_axis()[m.TARGET]);replay=m.ChoiceGenerationResolutionV1(qa.query_digest,'resolver:aura','resolver-gen:1','resolver-current:1','proof:target','CURRENT',False)
        b=choice('route:b');d=m.compile_presentable_choice(b,req(b),resolver=Resolver(replay={m.TARGET:replay}));self.assertIn('GENERATION_QUERY_MISMATCH:TARGET',d['blockers'])
    def test_union_summary_cannot_change_admission(self):
        c=choice();r=req(c);a=m.compile_presentable_choice(c,r,resolver=Resolver(),candidate_set_summary={'actions':['PAYMENT','REMOTE']});b=m.compile_presentable_choice(c,r,resolver=Resolver(),candidate_set_summary={'actions':['DOWNLOAD']});self.assertEqual(a['admission_digest'],b['admission_digest']);self.assertNotEqual(a['candidate_set_diagnostics_digest'],b['candidate_set_diagnostics_digest'])
    def test_requirement_cannot_bind_other_choice(self):
        a=choice('route:a');b=choice('route:b')
        with self.assertRaisesRegex(m.ChoiceMembraneError,'REQUIREMENT_CHOICE_BINDING_MISMATCH'):m.compile_presentable_choice(b,req(a),resolver=Resolver())
    def test_remote_runtime_provider_binding(self):
        c=choice('route:r',True,'provider:b');r=req(c);axes=list(r.axes);i=next(i for i,x in enumerate(axes) if x.axis==m.RUNTIME);old=axes[i];axes[i]=m.GenerationAxisRequirementV1(old.axis,'provider:wrong',old.generation,old.currentness_ref,old.authoritative_basis_ref);bad=m.ChoiceGenerationRequirementV1(c.choice_digest,tuple(axes))
        with self.assertRaisesRegex(m.ChoiceMembraneError,'REMOTE_RUNTIME_CACHE_ROUTE_PROVIDER_MISMATCH'):m.compile_presentable_choice(c,bad,resolver=Resolver())
    def test_principal_binding(self):
        c=choice();r=req(c);axes=list(r.axes);i=next(i for i,x in enumerate(axes) if x.axis==m.PRINCIPAL);old=axes[i];axes[i]=m.GenerationAxisRequirementV1(old.axis,'principal:b',old.generation,old.currentness_ref,old.authoritative_basis_ref);bad=m.ChoiceGenerationRequirementV1(c.choice_digest,tuple(axes))
        with self.assertRaisesRegex(m.ChoiceMembraneError,'REQUIREMENT_CHOICE_AXIS_MISMATCH'):m.compile_presentable_choice(c,bad,resolver=Resolver())
    def test_missing_base_axis(self):
        c=choice();r=req(c);axes=tuple(x for x in r.axes if x.axis!=m.OWNER)
        with self.assertRaisesRegex(m.ChoiceMembraneError,'REQUIREMENT_BASE_AXIS_MISSING'):m.ChoiceGenerationRequirementV1(c.choice_digest,axes)
    def test_remote_runtime_required(self):
        c=choice('route:r',True,'provider:b')
        with self.assertRaisesRegex(m.ChoiceMembraneError,'REMOTE_RUNTIME_CACHE_ROUTE_REQUIREMENT_REQUIRED'):
            m.build_choice_generation_requirement(c,resolver_ref='resolver:aura',resolver_generation='g',resolver_currentness_ref='c',source_currentness_ref='s',owner_currentness_ref='o',target_currentness_ref='t',principal_currentness_ref='p',source_basis_ref='bs',owner_basis_ref='bo',resolver_basis_ref='br',target_basis_ref='bt',principal_basis_ref='bp')
    def test_local_runtime_optional(self):
        c=choice();r=m.build_choice_generation_requirement(c,resolver_ref='resolver:aura',resolver_generation='g',resolver_currentness_ref='c',source_currentness_ref='s',owner_currentness_ref='o',target_currentness_ref='t',principal_currentness_ref='p',source_basis_ref='bs',owner_basis_ref='bo',resolver_basis_ref='br',target_basis_ref='bt',principal_basis_ref='bp',runtime_cache_route_generation='x',runtime_cache_route_currentness_ref='y',runtime_cache_route_basis_ref='z')
        self.assertEqual(r.by_axis()[m.RUNTIME].identity_ref,c.model_ref)
    def test_runtime_requirement_partial_rejected(self):
        c=choice()
        with self.assertRaisesRegex(m.ChoiceMembraneError,'RUNTIME_CACHE_ROUTE_REQUIREMENT_INCOMPLETE'):
            m.build_choice_generation_requirement(c,resolver_ref='resolver:aura',resolver_generation='g',resolver_currentness_ref='c',source_currentness_ref='s',owner_currentness_ref='o',target_currentness_ref='t',principal_currentness_ref='p',source_basis_ref='bs',owner_basis_ref='bo',resolver_basis_ref='br',target_basis_ref='bt',principal_basis_ref='bp',runtime_cache_route_generation='x')
    def test_choice_digest_tamper(self):
        c=choice()
        with self.assertRaisesRegex(m.ChoiceMembraneError,'CHOICE_DIGEST_MISMATCH'):
            m.PresentableChoiceEnvelopeV1(c.owner_ref,c.owner_generation,c.owner_projection_digest,c.principal_ref,c.principal_policy_generation,c.source_generation,c.target_generation,'route:other',c.model_ref,c.provider_ref,c.execution_location,c.cost_class,c.required_actions,c.candidate_evidence_ref,c.candidate_evidence_digest,c.choice_digest)
    def test_duplicate_route(self):
        a=choice('route:a');b=choice('route:a')
        with self.assertRaisesRegex(m.ChoiceMembraneError,'CHOICE_SET_ROUTE_DUPLICATE'):m.compile_presentable_choice_set([(a,req(a)),(b,req(b))],resolver=Resolver())
    def test_authority_flags_false(self):
        c=choice();d=m.compile_presentable_choice(c,req(c),resolver=Resolver())
        for k in ('credential_authorized','model_download_authorized','provider_call_authorized','payment_authorized','network_authorized','effect_authorized','execution_proven'):self.assertFalse(d[k])
if __name__=='__main__':unittest.main()
