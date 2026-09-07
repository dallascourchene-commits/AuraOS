import sys,unittest
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'/'arena'))

from memory_city_consequence_refinement import (
    EffectIntent,EffectObligationProjection,compile_effect_refinement,
)
from memory_city_handoff_current_read_seal import CurrentReadUseBinding
from memory_city_horizon_fenced_handoff import (
    HandoffVerificationContext,MutationBoundaryProjection,SemanticHandoffEvidence,
    read_use_root,semantic_handoff_root,
)
from memory_city_current_effect_handoff import (
    compile_current_effect_subclass_handoff,hard13d_current_effect,
)

def hx(s):return sha256(s.encode()).hexdigest()

def cert():
    return SimpleNamespace(
        status='READY_D0',receipt_root=hx('read-cert'),coverage_receipt_root=hx('coverage'),
        program_root=hx('program'),sealed_domain_root=hx('domain'),coverage_generation=7,
        binding_roots=(hx('b1'),hx('b2')),member_support_roots=(hx('s1'),hx('s2')),
        consequence_root=hx('consequence'),transition_model_root=hx('transition'),
        horizon=0,future_congruence_root=None,
    )

def use(c):
    return SimpleNamespace(status='READY_D0',certificate_root=c.receipt_root,branch_id=None,
                           hydrate_item_ids=(),reproof_item_ids=())

def intent(program=None,tag='intent'):
    return EffectIntent(hx(tag),hx('effect-domain'),program or hx('program'))

def projections(*,evidence_tag='evidence',obligation_b1='ob-a',current=True,authenticated=True):
    return (
        EffectObligationProjection(hx('b1'),hx(obligation_b1),hx(evidence_tag+'-1'),authenticated,current,hx('nuisance-1')),
        EffectObligationProjection(hx('b2'),hx('ob-b'),hx(evidence_tag+'-2'),True,True,hx('nuisance-2')),
    )

def fixture(*,current_read_tag='read-owner',owner_tag='owner',verifier_tag='verifier',
            expires_at=100,now=10,fence=2,installed=2,mutation_semantic=None,
            intent_obj=None,projection_rows=None):
    c=cert();u=use(c);i=intent_obj or intent(c.program_root)
    rows=projection_rows or projections();plan=compile_effect_refinement(rows,c,i)
    sr=semantic_handoff_root(c);ur=read_use_root(c,u)
    cr=CurrentReadUseBinding(ur,hx(current_read_tag))
    ev=SemanticHandoffEvidence(ur,sr,hx(owner_tag),hx(verifier_tag))
    mutation=MutationBoundaryProjection('cell',1,hx('config'),1,fence,installed,'holder',expires_at,
        mutation_semantic or sr,hx('transition-auth'),hx('resource-fence'))
    verification=HandoffVerificationContext('cell',1,hx('config'),1,fence,installed,
        hx(owner_tag),hx(verifier_tag),hx('transition-auth'),hx('resource-fence'),now)
    return c,u,i,plan,cr,ev,mutation,verification

def decide(fx,*,read_binding=hx('b1'),obligation=hx('ob-a'),intent_override=None,current_read_override=None):
    c,u,i,plan,cr,ev,m,v=fx
    return compile_current_effect_subclass_handoff(c,u,current_read_override or cr,plan,intent_override or i,
        read_binding_root=read_binding,obligation_root=obligation,evidence=ev,mutation=m,verification=v)

class CurrentEffectHandoffTests(unittest.TestCase):
    def test_ready_cross_binding_is_d0_only(self):
        d=decide(fixture());self.assertEqual(d.status,'READY_CURRENT_EFFECT_SUBCLASS_D0')
        self.assertFalse(d.authority_minted);self.assertFalse(d.mutation_authority);self.assertFalse(d.effect_authority);self.assertFalse(d.gate10)

    def test_stale_read_use_rebinds(self):
        fx=fixture();bad=CurrentReadUseBinding(hx('moved-read-use'),hx('read-owner'))
        d=decide(fx,current_read_override=bad);self.assertEqual(d.status,'REBIND_REQUIRED');self.assertEqual(d.reason,'CURRENT_READ_USE_MOVED')

    def test_moved_effect_obligation_holds(self):
        d=decide(fixture(),obligation=hx('ob-moved'));self.assertEqual(d.status,'HOLD_EFFECT_REFINEMENT_D0');self.assertEqual(d.reason,'HOLD_EFFECT_OBLIGATION_MOVED')

    def test_detached_binding_holds(self):
        d=decide(fixture(),read_binding=hx('detached'));self.assertEqual(d.status,'HOLD_EFFECT_REFINEMENT_D0');self.assertEqual(d.reason,'HOLD_BINDING_UNRESOLVED')

    def test_moved_intent_holds(self):
        fx=fixture();d=decide(fx,intent_override=intent(hx('program'),tag='moved-intent'))
        self.assertEqual(d.status,'HOLD_EFFECT_REFINEMENT_D0');self.assertEqual(d.reason,'HOLD_EFFECT_INTENT_MOVED')

    def test_lease_expiry_holds(self):
        d=decide(fixture(expires_at=10,now=10));self.assertEqual(d.status,'HOLD_HANDOFF_D0');self.assertEqual(d.reason,'LEASE_EXPIRED')

    def test_semantic_handoff_move_rebinds(self):
        d=decide(fixture(mutation_semantic=hx('moved-semantic')));self.assertEqual(d.status,'REBIND_REQUIRED');self.assertEqual(d.reason,'SEMANTIC_HANDOFF_MOVED')

    def test_uninstalled_fence_holds(self):
        d=decide(fixture(fence=3,installed=2));self.assertEqual(d.status,'HOLD_HANDOFF_D0');self.assertIn(d.reason,{'FENCE_NOT_INSTALLED_CURRENT','INSTALLED_FENCE_RECEIPT_MISMATCH','RESOURCE_FENCE_NOT_CURRENT'})

    def test_read_owner_receipt_changes_final_identity(self):
        a=decide(fixture(current_read_tag='owner-a'));b=decide(fixture(current_read_tag='owner-b'))
        self.assertEqual(a.status,b.status);self.assertNotEqual(a.current_effect_handoff_root,b.current_effect_handoff_root)

    def test_verifier_receipt_changes_final_identity(self):
        a=decide(fixture(verifier_tag='verifier-a'));b=decide(fixture(verifier_tag='verifier-b'))
        self.assertEqual(a.status,b.status);self.assertNotEqual(a.current_effect_handoff_root,b.current_effect_handoff_root)

    def test_effect_evidence_changes_final_identity(self):
        a=decide(fixture(projection_rows=projections(evidence_tag='ev-a')))
        b=decide(fixture(projection_rows=projections(evidence_tag='ev-b')))
        self.assertEqual(a.status,b.status);self.assertNotEqual(a.effect_escalation_root,b.effect_escalation_root);self.assertNotEqual(a.current_effect_handoff_root,b.current_effect_handoff_root)

    def test_mutation_snapshot_changes_final_identity(self):
        a=decide(fixture(now=10,expires_at=100));b=decide(fixture(now=11,expires_at=100))
        self.assertEqual(a.status,b.status);self.assertNotEqual(a.mutation_snapshot_root,b.mutation_snapshot_root);self.assertNotEqual(a.current_effect_handoff_root,b.current_effect_handoff_root)

    def test_unresolved_effect_evidence_cannot_escalate(self):
        rows=projections(current=False);d=decide(fixture(projection_rows=rows))
        self.assertEqual(d.status,'HOLD_EFFECT_REFINEMENT_D0')

    def test_13d_noncompensation(self):
        self.assertEqual(hard13d_current_effect((2,)*8+(0,)*5),'READY_D0')
        self.assertEqual(hard13d_current_effect((0,)+(2,)*12),'HOLD_HARD_INVALID')
        self.assertEqual(hard13d_current_effect((1,)+(2,)*12),'HOLD_UNRESOLVED')

if __name__=='__main__':unittest.main()
