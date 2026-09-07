import unittest
from dataclasses import replace
from hashlib import sha256
import json

from tools.awj032.speculative_realization_reconciliation_reference.speculative_realization_reconciliation import *


def r(x): return sha256(str(x).encode()).hexdigest()


class O5Tests(unittest.TestCase):
    def setUp(self):
        self.q = SpeculativeMaterializationCapsule(
            MaterializationKind.QWEN_ADAPTER,r('base'),r('candidate'),r('bytes'),r('source'),r('runtime'),r('proof'),r('consumer'),O_AVX14_CAMPAIGN_ROOT,
            adapter_realization_root=r('realization'),adapter_cache_root=r('cache'))
        self.g = SpeculativeMaterializationCapsule(
            MaterializationKind.GLM_EXPERT_SLICE_SET,r('base'),r('candidate'),r('bytes'),r('source'),r('runtime'),r('proof'),r('consumer'),O_AVX14_CAMPAIGN_ROOT,
            native_route_root=r('route'),selected_slice_plan_root=r('slices'),fp8_scale_plan_root=r('scales'))
        self.cur = CanonicalSelectionV1(r('base'),r('candidate'),r('bytes'),r('source'),r('runtime'),r('proof'),r('consumer'))
        self.o20 = O20PortBindingV1(r('port'),True,O20_HOLD_EMPIRICAL,True,r('route'),r('slices'),r('scales'))
        self.o4 = O4EffectTimeBindingV1(True,O4_EFFECT_TIME_ADMIT,r('realization'),r('cache'),r('process'),r('effect'))

    def d(self,s=None,c=None,t=AdoptionTarget.CACHE_REUSE,o20=None,o4=None):
        return reconcile_speculative_materialization(speculative=s or self.q,current=c or self.cur,target=t,o20=o20,o4=o4)

    def test_qwen_exact_cache_reuse(self):
        self.assertEqual(Disposition.REUSE_EXACT_SPECULATIVE_BYTES_D0,self.d().disposition)
    def test_qwen_serving_requires_o4(self):
        self.assertEqual(Disposition.HOLD_O4_EFFECT_TIME_REBIND,self.d(t=AdoptionTarget.SERVING_ACTIVATION).disposition)
    def test_qwen_serving_exact_o4_rebind(self):
        self.assertEqual(Disposition.ADMIT_D0_EFFECT_TIME_REBOUND,self.d(t=AdoptionTarget.SERVING_ACTIVATION,o4=self.o4).disposition)
    def test_qwen_stale_o4_cache_holds(self):
        bad=replace(self.o4,cache_root=r('other-cache'))
        self.assertEqual(Disposition.HOLD_O4_EFFECT_TIME_REBIND,self.d(t=AdoptionTarget.SERVING_ACTIVATION,o4=bad).disposition)
    def test_same_bytes_losing_candidate_dissolves(self):
        c=replace(self.cur,winning_candidate_operation_root=r('winner-2'))
        self.assertEqual(Disposition.DISSOLVE_NONWINNING_CANDIDATE,self.d(c=c).disposition)
    def test_base_move_holds(self): self.assertEqual(Disposition.HOLD_PROJECT_BASE_CURRENTNESS,self.d(c=replace(self.cur,project_base_root=r('b2'))).disposition)
    def test_source_move_holds(self): self.assertEqual(Disposition.HOLD_SOURCE_CURRENTNESS,self.d(c=replace(self.cur,source_generation_root=r('s2'))).disposition)
    def test_runtime_move_holds(self): self.assertEqual(Disposition.HOLD_RUNTIME_CURRENTNESS,self.d(c=replace(self.cur,runtime_root=r('r2'))).disposition)
    def test_proof_move_holds(self): self.assertEqual(Disposition.HOLD_PROOF_CURRENTNESS,self.d(c=replace(self.cur,proof_root=r('p2'))).disposition)
    def test_consumer_move_holds(self): self.assertEqual(Disposition.HOLD_CONSUMER_CURRENTNESS,self.d(c=replace(self.cur,consumer_root=r('c2'))).disposition)
    def test_materialization_move_holds(self): self.assertEqual(Disposition.HOLD_MATERIALIZATION_IDENTITY,self.d(c=replace(self.cur,materialization_root=r('m2'))).disposition)
    def test_glm_exact_bytes_reuse_for_empirical_proof(self):
        d=self.d(s=self.g,t=AdoptionTarget.CACHE_REUSE,o20=self.o20)
        self.assertEqual(Disposition.REUSE_EXACT_SPECULATIVE_BYTES_D0,d.disposition)
        self.assertFalse(d.training_authority)
    def test_glm_training_never_promoted_by_reuse(self):
        self.assertEqual(Disposition.HOLD_EMPIRICAL_PORT_RUN,self.d(s=self.g,t=AdoptionTarget.TRAINING_ACTIVATION,o20=self.o20).disposition)
    def test_glm_serving_is_different_owner(self):
        self.assertEqual(Disposition.HOLD_UNSUPPORTED_ACTIVATION,self.d(s=self.g,t=AdoptionTarget.SERVING_ACTIVATION,o20=self.o20).disposition)
    def test_glm_o20_not_ready_holds(self):
        bad=replace(self.o20,static_abi_ready=False)
        self.assertEqual(Disposition.HOLD_O20_STATIC_ABI,self.d(s=self.g,o20=bad).disposition)
    def test_glm_native_route_move_holds(self):
        bad=replace(self.o20,native_route_root=r('r2'))
        self.assertEqual(Disposition.HOLD_NATIVE_ROUTE_BINDING,self.d(s=self.g,o20=bad).disposition)
    def test_glm_slice_move_holds(self):
        bad=replace(self.o20,selected_slice_plan_root=r('s2'))
        self.assertEqual(Disposition.HOLD_SELECTED_SLICE_BINDING,self.d(s=self.g,o20=bad).disposition)
    def test_glm_scale_move_holds(self):
        bad=replace(self.o20,fp8_scale_plan_root=r('f2'))
        self.assertEqual(Disposition.HOLD_FP8_SCALE_BINDING,self.d(s=self.g,o20=bad).disposition)
    def test_qwen_training_activation_unsupported(self):
        self.assertEqual(Disposition.HOLD_UNSUPPORTED_ACTIVATION,self.d(t=AdoptionTarget.TRAINING_ACTIVATION).disposition)
    def test_parent_campaign_identity_is_exact(self):
        with self.assertRaisesRegex(ValueError,'O_AVX14_PARENT_ROOT_MISMATCH'):
            replace(self.q,reconciliation_parent_root=r('wrong-parent'))
    def test_speculative_capsule_cannot_mint_authority(self):
        with self.assertRaisesRegex(ValueError,'CANNOT_MINT'):
            replace(self.q,effect_authority=True)
    def test_o4_binding_cannot_mint_authority(self):
        with self.assertRaisesRegex(ValueError,'AUTHORITY_ESCALATION'):
            replace(self.o4,gate10=True)
    def test_o20_binding_cannot_mint_authority(self):
        with self.assertRaisesRegex(ValueError,'CANNOT_MINT'):
            replace(self.o20,effect_authority=True)
    def test_decision_never_mints_authority(self):
        for d in (self.d(),self.d(t=AdoptionTarget.SERVING_ACTIVATION,o4=self.o4),self.d(s=self.g,o20=self.o20),self.d(s=self.g,t=AdoptionTarget.TRAINING_ACTIVATION,o20=self.o20)):
            self.assertFalse(d.effect_authority or d.training_authority or d.checkpoint_authority or d.gate10)
    def test_consumer_matrix_dependency_closed_minimum(self):
        required={'focused_tests','random_campaign'}
        self.assertTrue(PROOF_CONSUMER_MATRIX)
        for field,consumers in PROOF_CONSUMER_MATRIX.items():
            self.assertTrue(required <= set(consumers),(field,consumers))
    def test_roots_are_deterministic(self):
        self.assertEqual(self.q.capsule_root,replace(self.q).capsule_root)
        self.assertEqual(self.cur.selection_root,replace(self.cur).selection_root)

if __name__=='__main__': unittest.main()
