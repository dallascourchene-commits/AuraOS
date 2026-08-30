import unittest
import zf05b_zf07c_share_escalation_firewall as m
E='e'*64; C='c'*64; D='d'*64

def share():
    x={'schema':m.SHARE_PLAN_SCHEMA,'capsule_digest':C,'capsule_id':'cap:1','preferred_entry_surface':'web','next_surface':None,'creator_ref':'creator:1','claimed_attribution_refs':['attr:1'],'attribution_evidence_current':True,'attribution_identity_proven':False,'referral_depth':0,'required_user_actions':list(m.SHARE_FIXED_ACTIONS),'blockers':[],'status':'READY_FOR_USER_ACTION','network_fetch_authorized':False,'install_authorized':False,'execution_authorized':False,'execution_proven':False,'publication_authorized':False,'payment_authorized':False,'telemetry_authorized':False,'recipient_tracking_authorized':False,'provider_call_authorized':False,'adoption_success_proven':False}
    x['plan_digest']=m._plain_digest(x); return x

def recipe():
    x={'schema':m.RECIPE_PLAN_SCHEMA,'recipe_digest':D,'recipe_id':'recipe:1','recipe_version':'v1','purpose':'p','capability_refs':['capability:model'],'asset_refs':[],'parameters':{},'constraints':{},'effect_ceiling':'NONE','rights':{},'blockers':[],'status':'READY_FOR_ADMISSION','authority_owner_resolved':False,'effect_authorized':False,'execution_proven':False,'publication_authorized':False,'payment_authorized':False,'marketplace_listed':False}
    x['plan_digest']=m._plain_digest(x); return x

def currentness(): return {'source_currentness_ref':'cur:source','model_catalog_currentness_ref':'cur:model','provider_catalog_currentness_ref':'cur:provider','rate_catalog_currentness_ref':'cur:rate'}
def residual(r=None):
    r=r or recipe(); return {'residual_id':'res:1','recipe_plan_digest':r['plan_digest'],'capability_ref':'capability:model','residual_kind':'MODEL_INFERENCE_REQUIRED','unresolved':True,'source_generation':'gen:1','source_currentness_ref':'cur:source','minimum_context_tokens':1}

def option(remote=False):
    actions=['EXPLICIT_REMOTE_EXECUTION_CONSENT'] if remote else []
    return {'route_id':'route:remote' if remote else 'route:local','model_ref':'model:1','provider_ref':'provider:1' if remote else '','execution_location':'REMOTE' if remote else 'LOCAL','cost_class':'FREE_BOUNDED' if remote else 'INCLUDED','required_actions':actions,'zero_effect_ready':not actions,'download_bytes':None,'candidate_evidence_ref':'evidence:candidate','candidate_evidence_digest':E,'evidence_summary':['ok']}
def decision(r=None, remote=False, disposition=None):
    r=r or residual(); cur,dig=m.verify_router_currentness(currentness()); o=option(remote)
    disp=disposition or ('USER_CHOICE_REQUIRED' if remote else 'LOCAL_ROUTE_READY')
    logical={'schema':m.ROUTER_DECISION_SCHEMA,'router_schema':m.ROUTER_SCHEMA,'residual_id':r['residual_id'],'capability_ref':r['capability_ref'],'recipe_plan_digest':r['recipe_plan_digest'],'residual_source_generation':r['source_generation'],'residual_source_currentness_ref':r['source_currentness_ref'],'router_currentness_digest':dig,'disposition':disp,'selected_route_id':o['route_id'],'options':[m._option_logical(o)],'blockers':(),'earned_action_classes':tuple(sorted(o['required_actions'])),'credential_prompt_performed':False,'credential_collected':False,'model_download_started':False,'provider_call_made':False,'payment_performed':False,'effect_authorized':False,'execution_proven':False,'catalog_evidence_authenticated':False}
    out=dict(logical); out['blockers']=[]; out['earned_action_classes']=list(logical['earned_action_classes']); out['decision_digest']=m._domain_digest('AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1',logical); return out

class Resolver:
    def __init__(self, owner_mode='ok', target_mode='ok'): self.owner_mode=owner_mode; self.target_mode=target_mode
    def resolve_owner_projection(self,q):
        if self.owner_mode=='missing': return None
        kw=dict(query_digest=q.digest,resolver_ref='resolver:aura',resolver_generation='r1',issuer_ref='issuer:aura',owner_ref=q.owner_ref,owner_head=q.owner_head,owner_blob=q.owner_blob,owner_currentness_ref=q.owner_currentness_ref,subject_ref=q.subject_ref,subject_generation=q.subject_generation,projection_payload_digest=q.projection_payload_digest,currentness_state='CURRENT',revoked=False,lineage_ref='lineage:'+q.evidence_domain.lower(),consequence_ceiling=q.consequence_ceiling)
        if self.owner_mode=='stale': kw['currentness_state']='STALE'
        if self.owner_mode=='revoked': kw['revoked']=True
        if self.owner_mode=='wrong_owner': kw['owner_head']='0'*40
        if self.owner_mode=='wrong_digest': kw['projection_payload_digest']='0'*64
        return m.OwnerProjectionResolutionV1(**kw)
    def resolve_provider_target(self,q):
        if self.target_mode=='missing': return None
        kw=dict(query_digest=q.digest,resolver_ref='resolver:aura',resolver_generation='r1',issuer_ref='issuer:aura',evidence_ref='provider:evidence',evidence_digest=E,source_generation='provider:gen1',currentness_ref='cur:provider-target',currentness_state='CURRENT',revoked=False,principal_ref=q.principal_ref,route_id=q.route_id,provider_ref=q.provider_ref,model_ref=q.model_ref,candidate_evidence_ref=q.candidate_evidence_ref,candidate_evidence_digest=q.candidate_evidence_digest,cost_class=q.cost_class,provider_currentness_ref=q.provider_currentness_ref,rate_currentness_ref=q.rate_currentness_ref)
        if self.target_mode=='wrong_principal': kw['principal_ref']='user:other'
        if self.target_mode=='wrong_provider': kw['provider_ref']='provider:other'
        if self.target_mode=='stale': kw['currentness_state']='STALE'
        if self.target_mode=='revoked': kw['revoked']=True
        return m.ProviderTargetResolutionV1(**kw)

def compile_case(remote=False,resolver_obj=None):
    s=share(); rp=recipe(); res=residual(rp); dec=decision(res,remote)
    return m.compile_share_escalation_firewall(s,rp,res,dec,router_currentness=currentness(),principal_ref='user:1',resolver=resolver_obj)

class T(unittest.TestCase):
    def test_no_resolver_fail_closed(self):
        x=compile_case(False,None); self.assertEqual(x['disposition'],'EVIDENCE_REQUIRED'); self.assertFalse(x['owner_resolution_proven'])
    def test_local_happy(self):
        x=compile_case(False,Resolver()); self.assertEqual(x['disposition'],'RECIPIENT_ESCALATION_READY'); self.assertTrue(x['owner_resolution_proven']); self.assertTrue(x['provider_targets_resolved'])
    def test_remote_happy(self):
        x=compile_case(True,Resolver()); self.assertEqual(x['disposition'],'RECIPIENT_ESCALATION_READY'); self.assertEqual(len(x['presentable_options']),1)
    def test_owner_missing(self): self.assertEqual(compile_case(False,Resolver('missing'))['disposition'],'EVIDENCE_REQUIRED')
    def test_owner_stale(self): self.assertEqual(compile_case(False,Resolver('stale'))['disposition'],'EVIDENCE_REQUIRED')
    def test_owner_revoked(self): self.assertEqual(compile_case(False,Resolver('revoked'))['disposition'],'EVIDENCE_REQUIRED')
    def test_owner_wrong_owner(self): self.assertEqual(compile_case(False,Resolver('wrong_owner'))['disposition'],'EVIDENCE_REQUIRED')
    def test_owner_wrong_projection(self): self.assertEqual(compile_case(False,Resolver('wrong_digest'))['disposition'],'EVIDENCE_REQUIRED')
    def test_target_missing(self): self.assertEqual(compile_case(True,Resolver(target_mode='missing'))['disposition'],'EVIDENCE_REQUIRED')
    def test_target_wrong_principal(self): self.assertEqual(compile_case(True,Resolver(target_mode='wrong_principal'))['disposition'],'EVIDENCE_REQUIRED')
    def test_target_wrong_provider(self): self.assertEqual(compile_case(True,Resolver(target_mode='wrong_provider'))['disposition'],'EVIDENCE_REQUIRED')
    def test_target_stale(self): self.assertEqual(compile_case(True,Resolver(target_mode='stale'))['disposition'],'EVIDENCE_REQUIRED')
    def test_target_revoked(self): self.assertEqual(compile_case(True,Resolver(target_mode='revoked'))['disposition'],'EVIDENCE_REQUIRED')
    def test_share_tamper(self):
        s=share(); s['capsule_id']='cap:2'; rp=recipe(); res=residual(rp); dec=decision(res)
        with self.assertRaises(m.FirewallError): m.compile_share_escalation_firewall(s,rp,res,dec,router_currentness=currentness(),principal_ref='user:1',resolver=Resolver())
    def test_recipe_tamper(self):
        s=share(); rp=recipe(); rp['purpose']='tamper'; res=residual(recipe()); dec=decision(res)
        with self.assertRaises(m.FirewallError): m.compile_share_escalation_firewall(s,rp,res,dec,router_currentness=currentness(),principal_ref='user:1',resolver=Resolver())
    def test_decision_tamper(self):
        s=share(); rp=recipe(); res=residual(rp); dec=decision(res); dec['selected_route_id']='route:other'
        with self.assertRaises(m.FirewallError): m.compile_share_escalation_firewall(s,rp,res,dec,router_currentness=currentness(),principal_ref='user:1',resolver=Resolver())
    def test_no_authority(self):
        x=compile_case(True,Resolver())
        for k in ('credential_authorized','model_download_authorized','provider_call_authorized','payment_authorized','network_authorized','effect_authorized','execution_proven'): self.assertFalse(x[k])
    def test_digest_binds_residual_unresolved(self):
        a=compile_case(False,Resolver()); rp=recipe(); res=residual(rp); res['unresolved']=False; dec=decision(res,False,'NO_ESCALATION_REQUIRED'); dec['selected_route_id']=None; dec['options']=[]; dec['earned_action_classes']=[]
        cur,dig=m.verify_router_currentness(currentness()); logical={'schema':m.ROUTER_DECISION_SCHEMA,'router_schema':m.ROUTER_SCHEMA,'residual_id':res['residual_id'],'capability_ref':res['capability_ref'],'recipe_plan_digest':res['recipe_plan_digest'],'residual_source_generation':res['source_generation'],'residual_source_currentness_ref':res['source_currentness_ref'],'router_currentness_digest':dig,'disposition':'NO_ESCALATION_REQUIRED','selected_route_id':None,'options':[],'blockers':(),'earned_action_classes':(),'credential_prompt_performed':False,'credential_collected':False,'model_download_started':False,'provider_call_made':False,'payment_performed':False,'effect_authorized':False,'execution_proven':False,'catalog_evidence_authenticated':False}; dec['decision_digest']=m._domain_digest('AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1',logical)
        b=m.compile_share_escalation_firewall(share(),rp,res,dec,router_currentness=currentness(),principal_ref='user:1',resolver=Resolver()); self.assertNotEqual(a['firewall_digest'],b['firewall_digest'])
    def test_query_digest_tamper_rejected(self):
        class R(Resolver):
            def resolve_owner_projection(self,q):
                r=super().resolve_owner_projection(q); return m.OwnerProjectionResolutionV1(**{**r.__dict__,'query_digest':'0'*64})
        self.assertEqual(compile_case(False,R())['disposition'],'EVIDENCE_REQUIRED')
    def test_provider_query_digest_tamper_rejected(self):
        class R(Resolver):
            def resolve_provider_target(self,q):
                r=super().resolve_provider_target(q); return m.ProviderTargetResolutionV1(**{**r.__dict__,'query_digest':'0'*64})
        self.assertEqual(compile_case(True,R())['disposition'],'EVIDENCE_REQUIRED')

if __name__=='__main__': unittest.main()
