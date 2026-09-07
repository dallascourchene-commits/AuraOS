import unittest
from dataclasses import replace
from tools.arena.attenuated_stable_operation_delegation import Disposition
from tools.arena.o19_authenticated_attenuated_delegation import AuthenticationError, D0, sign_grant, sign_currentness, sign_admission, sign_attempt_use
from tools.arena.o19_authenticated_attenuated_delegation_proof import fixture, run, altered, PK, CK, AOK, AVK, UVK, NOW, parent_shape_baseline, oracle, candidate, AXES, forged_parent_attack

class O19Tests(unittest.TestCase):
    def test_valid(self): self.assertEqual(run(*fixture()).parent_decision.disposition,Disposition.ADMIT_D0)
    def test_exact_parent_forgery_is_real(self): self.assertEqual(forged_parent_attack(),'ADMIT_DELEGATED_ATTEMPT_D0')
    def test_grant_auth(self): self._holds('grant_auth')
    def test_parent_link(self): self._holds('parent_link')
    def test_attenuation(self): self._holds('attenuation')
    def test_grant_currentness(self): self._holds('grant_currentness')
    def test_admission_auth(self): self._holds('admission_auth')
    def test_attempt_auth(self): self._holds('attempt_auth')
    def test_source_binding(self): self._holds('source_binding')
    def test_authority_ceiling(self): self._holds('authority_ceiling')
    def _holds(self,axis):
        with self.assertRaises(AuthenticationError): run(*altered(axis))
    def test_no_chain(self):
        op,_,_,a,u=fixture()
        with self.assertRaises(AuthenticationError): run(op,[],[],a,u)
    def test_currentness_cardinality(self):
        op,gs,cs,a,u=fixture()
        with self.assertRaises(AuthenticationError): run(op,gs,cs[:1],a,u)
    def test_root_parent_forbidden(self):
        op,gs,cs,a,u=fixture(); x=gs[0].unsigned; x['parent_grant_root']='f'*64; gs[0]=sign_grant(x,PK['root-owner'])
        cu=cs[0].unsigned; cu['grant_root']=gs[0].grant_root; cs[0]=sign_currentness(cu,CK['observer-1'])
        with self.assertRaises(AuthenticationError): run(op,gs,cs,a,u)
    def test_wrong_child_issuer(self):
        op,gs,cs,a,u=fixture(); x=gs[1].unsigned; x['issuer']='worker-b'; gs[1]=sign_grant(x,PK['worker-b'])
        cu=cs[1].unsigned; cu['grant_root']=gs[1].grant_root; cs[1]=sign_currentness(cu,CK['observer-2'])
        with self.assertRaises(AuthenticationError): run(op,gs,cs,a,u)
    def test_generation_not_monotone(self):
        op,gs,cs,a,u=fixture(); x=gs[1].unsigned; x['generation']=1; gs[1]=sign_grant(x,PK['worker-a'])
        cu=cs[1].unsigned; cu['grant_root']=gs[1].grant_root; cu['generation']=1; cs[1]=sign_currentness(cu,CK['observer-2'])
        with self.assertRaises(AuthenticationError): run(op,gs,cs,a,u)
    def test_self_observer_rejected(self):
        op,gs,cs,a,u=fixture(); cs[1]=replace(cs[1],observer='worker-b',signature='0'*64)
        with self.assertRaises(AuthenticationError): run(op,gs,cs,a,u)
    def test_owner_verifier_same_rejected(self):
        op,gs,cs,a,u=fixture(); x=a.unsigned; x['verifier']='domain-owner'; a=sign_admission(x,AOK['domain-owner'],AOK['domain-owner'])
        av=dict(AVK); av['domain-owner']=AOK['domain-owner']
        from tools.arena.o19_authenticated_attenuated_delegation import authenticate_and_decide
        with self.assertRaises(AuthenticationError): authenticate_and_decide(op,gs,cs,a,u,frozenset({'edit'}),30,principal_keys=PK,currentness_verifier_keys=CK,admission_owner_keys=AOK,admission_verifier_keys=av,attempt_verifier_keys=UVK,now=NOW)
    def test_request_scope_exceeds(self):
        op,gs,cs,a,u=fixture(); from tools.arena.o19_authenticated_attenuated_delegation import authenticate_and_decide
        d=authenticate_and_decide(op,gs,cs,a,u,frozenset({'read'}),30,principal_keys=PK,currentness_verifier_keys=CK,admission_owner_keys=AOK,admission_verifier_keys=AVK,attempt_verifier_keys=UVK,now=NOW)
        self.assertEqual(d.parent_decision.disposition,Disposition.HOLD)
    def test_request_budget_exceeds(self):
        op,gs,cs,a,u=fixture(); from tools.arena.o19_authenticated_attenuated_delegation import authenticate_and_decide
        d=authenticate_and_decide(op,gs,cs,a,u,frozenset({'edit'}),41,principal_keys=PK,currentness_verifier_keys=CK,admission_owner_keys=AOK,admission_verifier_keys=AVK,attempt_verifier_keys=UVK,now=NOW)
        self.assertEqual(d.parent_decision.disposition,Disposition.HOLD)
    def test_result_has_no_authority(self):
        d=run(*fixture()); self.assertFalse(d.effect_authority or d.training_authority or d.checkpoint_authority or d.gate10)
    def test_parent_shape_false_admits_forged(self): self.assertTrue(parent_shape_baseline((False,True,True,False,False,False,True,False)))
    def test_candidate_independent_oracle_valid(self): self.assertEqual(candidate((True,)*8),oracle((True,)*8))
    def test_candidate_independent_oracle_each_invalid(self):
        for i in range(8):
            bits=[True]*8; bits[i]=False; self.assertFalse(candidate(tuple(bits)),AXES[i])

if __name__=='__main__': unittest.main()
