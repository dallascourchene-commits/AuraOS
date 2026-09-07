import unittest
from dataclasses import replace
from hashlib import sha256

from tools.awj032.training_o2_transition_reference.test_transition_envelope import TransitionTest
from tools.awj032.training_o2_transition_reference.effect_time_adapter_realization import (
    StableAdapterRealization, AtUseAdapterObservation, VerifiedProcessProjection,
    admit_effect_time_realization, verify_effect_time_transition,
)

R=lambda s:sha256(s.encode()).hexdigest()

class EffectTimeAdapterRealizationTest(unittest.TestCase):
    def setUp(self):
        self.t=TransitionTest(); self.t.setUp()
        self.ack,self.result=self.t.pair()
        self.realization=StableAdapterRealization(
            self.t.env.transition_root,self.t.core.identity_root,self.t.env.intent.inference_runtime_root,
            R('loader-v1'),R('cache-schema-v1'))
        self.verified=VerifiedProcessProjection(
            R('process-witness-v1'),50,2,3,R('loaded-units-v1'),self.realization.cache_root,
            R('dispatch-v1'),4,R('population-v1'),'worker-1',True)
        self.observation=AtUseAdapterObservation(
            20,self.realization.realization_root,self.realization.cache_root,self.verified.process_witness_root,
            self.verified.process_generation,self.verified.load_generation,self.verified.loaded_units_root,
            self.verified.loaded_adapter_unit_root,self.verified.dispatch_root,self.verified.mutation_generation,
            self.verified.serving_population_root,self.verified.selected_worker_id)
        self.transition_kwargs=dict(
            permit=self.t.permit,admission_resolver=self.t.resolver,trace_authority=self.t.trace,
            ack=self.ack,result=self.result,independently_recomputed_source_digest=self.t.env.source_envelope_digest,
            now=13,observed_source_root=self.t.semantic.source_root,
            observed_target_topology_root=self.t.semantic.target_topology_root)
    def resolve(self,_): return self.verified
    def verify(self,**kw):
        args=dict(core=self.t.core,env=self.t.env,realization=self.realization,observation=self.observation,
                  resolve_process_currentness=self.resolve,transition_kwargs=self.transition_kwargs)
        args.update(kw); return verify_effect_time_transition(**args)
    def test_valid_composes_real_transition_and_effect_time_currentness(self):
        d=self.verify(); self.assertTrue(d.admitted); self.assertEqual(d.reason,'ADMIT_D0_EFFECT_TIME_ADAPTER_REALIZATION')
        self.assertFalse(d.effect_authority); self.assertFalse(d.checkpoint_authority); self.assertFalse(d.gate10)
    def test_transition_hold_propagates(self):
        bad=dict(self.transition_kwargs); bad['independently_recomputed_source_digest']=R('bad')
        self.assertTrue(self.verify(transition_kwargs=bad).reason.startswith('HOLD_TRANSITION:'))
    def test_cache_identity_must_match_stable_realization(self):
        d=admit_effect_time_realization(realization=self.realization,observation=replace(self.observation,cache_root=R('stale-cache')),resolve_process_currentness=self.resolve)
        self.assertEqual(d.reason,'HOLD_CACHE_IDENTITY')
    def test_loaded_adapter_unit_must_equal_cache_truth(self):
        v=replace(self.verified,loaded_adapter_unit_root=R('old-adapter')); o=replace(self.observation,loaded_adapter_unit_root=v.loaded_adapter_unit_root)
        d=admit_effect_time_realization(realization=self.realization,observation=o,resolve_process_currentness=lambda _:v)
        self.assertEqual(d.reason,'HOLD_LOADED_ADAPTER_REALIZATION_MOVED')
    def test_process_or_load_move_requires_rebind(self):
        self.assertEqual(admit_effect_time_realization(realization=self.realization,observation=replace(self.observation,load_generation=9),resolve_process_currentness=self.resolve).reason,'HOLD_EFFECT_TIME_PROCESS_BINDING')
    def test_expired_process_projection_holds(self):
        self.assertEqual(admit_effect_time_realization(realization=self.realization,observation=replace(self.observation,now=51),resolve_process_currentness=self.resolve).reason,'HOLD_PROCESS_CURRENTNESS_EXPIRED')
    def test_unverified_process_holds(self):
        self.assertEqual(admit_effect_time_realization(realization=self.realization,observation=self.observation,resolve_process_currentness=lambda _:None).reason,'HOLD_PROCESS_CURRENTNESS_UNVERIFIED')
    def test_projection_cannot_promote_authority(self):
        v=replace(self.verified,effect_authority=True)
        self.assertEqual(admit_effect_time_realization(realization=self.realization,observation=self.observation,resolve_process_currentness=lambda _:v).reason,'HOLD_PROCESS_PROJECTION_AUTHORITY_ESCALATION')
    def test_process_worker_rotation_preserves_immutable_cache_but_rotates_effect_witness(self):
        v2=replace(self.verified,process_witness_root=R('process-witness-v2'),process_generation=3,load_generation=4,selected_worker_id='worker-2')
        o2=replace(self.observation,process_witness_root=v2.process_witness_root,process_generation=3,load_generation=4,selected_worker_id='worker-2')
        d=admit_effect_time_realization(realization=self.realization,observation=o2,resolve_process_currentness=lambda _:v2)
        self.assertTrue(d.admitted); self.assertEqual(d.cache_root,self.realization.cache_root); self.assertNotEqual(d.process_witness_root,self.verified.process_witness_root)
    def test_semantic_core_change_rotates_cache_identity(self):
        r2=replace(self.realization,adapter_core_root=R('new-core'))
        self.assertNotEqual(r2.realization_root,self.realization.realization_root); self.assertNotEqual(r2.cache_root,self.realization.cache_root)
    def test_k27_is_absent_from_cache_and_effect_identity(self):
        self.assertFalse(hasattr(self.realization,'k27')); self.assertFalse(hasattr(self.observation,'k27'))
    def test_runtime_binding_is_stable_semantic_input(self):
        r2=replace(self.realization,runtime_root=R('other-runtime'))
        self.assertEqual(self.verify(realization=r2).reason,'HOLD_REALIZATION_RUNTIME_BINDING')

if __name__=='__main__': unittest.main()
