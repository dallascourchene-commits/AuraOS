from dataclasses import replace
from pathlib import Path
import json, subprocess, sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from campaign_memory_city_horizon_fenced_handoff import *

class T(unittest.TestCase):
    def test_valid_routes_to_tecc_not_effect_ready(self):
        d=invoke(base()); self.assertIs(d.disposition,HandoffDisposition.HOLD_TECC_REQUIRED_D0); self.assertFalse(d.effect_authority); self.assertIsNotNone(d.effect_escalation_root)
    def test_foreign_admission_schema_holds(self):
        d=invoke(apply_mode(1,base())); self.assertEqual(d.reason,'ADMISSION_SCHEMA_NOT_CANONICAL')
    def test_missing_authority_declaration_holds(self):
        d=invoke(apply_mode(2,base())); self.assertEqual(d.reason,'ADMISSION_SHAPE_NOT_CANONICAL')
    def test_read_certificate_authority_holds(self):
        d=invoke(apply_mode(3,base())); self.assertEqual(d.reason,'READ_CERTIFICATE_AUTHORITY_ESCALATION')
    def test_substituted_consequence_holds_even_if_self_rehashed(self):
        d=invoke(apply_mode(4,base())); self.assertEqual(d.reason,'READ_CONSEQUENCE_ROOT_UNAUTHENTICATED')
    def test_holder_mismatch_holds(self):
        d=invoke(apply_mode(5,base())); self.assertEqual(d.reason,'LEASE_HOLDER_MOVED')
    def test_read_only_admission_holds(self):
        d=invoke(apply_mode(6,base())); self.assertEqual(d.reason,'READ_ONLY_CANNOT_ENTER_EFFECT_HANDOFF')
    def test_effect_obligation_move_holds(self):
        d=invoke(apply_mode(7,base())); self.assertEqual(d.reason,'HOLD_EFFECT_OBLIGATION_MOVED')
    def test_unresolved_refinement_holds(self):
        d=invoke(apply_mode(8,base())); self.assertEqual(d.reason,'EFFECT_REFINEMENT_NOT_COMPLETE')
    def test_component_reproof_move_holds(self):
        d=invoke(apply_mode(9,base())); self.assertEqual(d.reason,'ACTIVE_COMPONENT_REPROOF_MOVED')
    def test_reproof_semantics_move_holds(self):
        d=invoke(apply_mode(10,base())); self.assertEqual(d.reason,'ACTIVE_REPROOF_SEMANTICS_MOVED')
    def test_transition_move_holds(self):
        d=invoke(apply_mode(11,base())); self.assertEqual(d.reason,'ACTIVE_TRANSITION_CONSEQUENCE_MOVED')
    def test_read_use_move_holds(self):
        d=invoke(apply_mode(12,base())); self.assertEqual(d.reason,'READ_USE_CERTIFICATE_MOVED')
    def test_owner_and_verifier_stale_hold(self):
        self.assertEqual(invoke(apply_mode(13,base())).reason,'OWNER_EVIDENCE_ROOT_STALE'); self.assertEqual(invoke(apply_mode(14,base())).reason,'VERIFIER_RECEIPT_ROOT_STALE')
    def test_revision_rebinds(self):
        self.assertIs(invoke(apply_mode(15,base())).disposition,HandoffDisposition.REBIND_REQUIRED)
    def test_uninstalled_fence_holds(self):
        self.assertEqual(invoke(apply_mode(16,base())).reason,'FENCE_NOT_INSTALLED_CURRENT')
    def test_expired_lease_holds(self):
        self.assertEqual(invoke(apply_mode(17,base())).reason,'LEASE_EXPIRED')
    def test_negative_times_rejected(self):
        with self.assertRaises(ValueError): MutationBoundaryProjection('cell',4,r('cfg'),8,17,17,'worker',-1,r('ta'),r('rf'))
        with self.assertRaises(ValueError): HandoffVerificationContext('cell',4,r('cfg'),8,17,17,'worker',r('owner'),r('verifier'),r('ta'),r('rf'),-1)
    def test_pr878_binding_semantics_field_required(self):
        d=invoke(apply_mode(23,base())); self.assertEqual(d.reason,'ACTIVE_READ_WORLD_NOT_CERTIFIED')
    def test_context_axes_do_not_repair_hard_invalid(self):
        a,_=evaluate_hard_state((2,2,2,2,2,2,2,2),(0,0,0,0,0)); b,_=evaluate_hard_state((2,2,2,2,2,2,2,2),(2,2,2,2,2)); self.assertEqual(a.disposition,b.disposition)
        bad,_=evaluate_hard_state((2,2,2,2,2,0,2,2),(2,2,2,2,2)); self.assertIsNot(bad.disposition,HandoffDisposition.HOLD_TECC_REQUIRED_D0)
    def test_campaign_direct_entrypoint(self):
        repo=ROOT; script=repo/'tools'/'arena'/'campaign_memory_city_horizon_fenced_handoff.py'; cp=subprocess.run([sys.executable,str(script)],cwd=repo,capture_output=True,text=True,check=True); p=json.loads(cp.stdout); self.assertEqual(p['candidate_false_route'],0); self.assertEqual(p['review_attack_canaries'],5000)

if __name__=='__main__': unittest.main()
