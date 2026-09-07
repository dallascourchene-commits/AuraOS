import unittest
from dataclasses import replace
from hashlib import sha256

from tools.arena.attenuated_stable_operation_delegation import StableOperation, DelegationHop, DomainAdmission, AttemptContext
from tools.project006.installed_runtime_attestation import RuntimeReleaseManifest, HostMeasurement, MeasurementEvidence, AttestationError
from tools.arena.installed_runtime_bound_delegation import RuntimeTarget, PermitDisposition, bind_at_use

def h(s): return sha256(s.encode()).hexdigest()

class O21Tests(unittest.TestCase):
    def setUp(self):
        self.now=1_000_000
        self.op=StableOperation('training',h('semantic'),'step',h('source-v1'),h('policy'))
        self.hops=(DelegationHop('root',frozenset({'step','read'}),100,1),DelegationHop('worker',frozenset({'step'}),50,2))
        self.adm=DomainAdmission('training',self.op.root(),h('admission'),frozenset({'step'}),60,7,True,True)
        self.ctx=AttemptContext('worker',h('workcell'),3,True,h('lease'),True,self.op.source_incarnation_root,frozenset({'step'}),20)
        self.man=RuntimeReleaseManifest('r1','AuraOS','head-1',9,self.op.root(),{'runtime':h('runtime'),'bridge':h('bridge')})
        self.meas=HostMeasurement('host-A','head-1',dict(self.man.components),'inc-A',self.op.source_incarnation_root,self.now-1000,(1,2,3))
        self.ev=MeasurementEvidence(self.meas.technical_root,self.man.release_root,'verifier','observer',True,True,True,True,self.now-2000,self.now+100000)
        self.target=RuntimeTarget('host-A','inc-A',self.man.release_root)
    def call(self,**kw):
        d=dict(operation=self.op,hops=self.hops,admission=self.adm,ctx=self.ctx,manifest=self.man,target=self.target,owner_reported_updated=True,measurement=self.meas,evidence=self.ev,now_ms=self.now)
        d.update(kw); return bind_at_use(**d)
    def test_01_happy(self): self.assertEqual(self.call().disposition,PermitDisposition.ADMIT_D0)
    def test_02_no_effect_authority(self): self.assertFalse(self.call().effect_authority)
    def test_03_no_training_authority(self): self.assertFalse(self.call().training_authority)
    def test_04_no_checkpoint_authority(self): self.assertFalse(self.call().checkpoint_authority)
    def test_05_gate10_false(self): self.assertFalse(self.call().gate10)
    def test_06_nonattenuating_scope(self):
        hops=(self.hops[0],replace(self.hops[1],scope=frozenset({'step','admin'}))); self.assertEqual(self.call(hops=hops).disposition,PermitDisposition.HOLD_DELEGATION)
    def test_07_nonattenuating_budget(self):
        hops=(self.hops[0],replace(self.hops[1],budget=101)); self.assertEqual(self.call(hops=hops).disposition,PermitDisposition.HOLD_DELEGATION)
    def test_08_stale_hop(self):
        hops=(replace(self.hops[0],current=False),self.hops[1]); self.assertEqual(self.call(hops=hops).disposition,PermitDisposition.HOLD_DELEGATION)
    def test_09_stale_workcell(self): self.assertEqual(self.call(ctx=replace(self.ctx,workcell_current=False)).disposition,PermitDisposition.HOLD_DELEGATION)
    def test_10_stale_lease(self): self.assertEqual(self.call(ctx=replace(self.ctx,lease_current=False)).disposition,PermitDisposition.HOLD_DELEGATION)
    def test_11_scope_excess(self): self.assertEqual(self.call(ctx=replace(self.ctx,requested_scope=frozenset({'admin'}))).disposition,PermitDisposition.HOLD_DELEGATION)
    def test_12_budget_excess(self): self.assertEqual(self.call(ctx=replace(self.ctx,requested_budget=99)).disposition,PermitDisposition.HOLD_DELEGATION)
    def test_13_unmeasured_owner_true(self): self.assertEqual(self.call(measurement=None,evidence=None).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_14_owner_stale_no_measurement(self): self.assertEqual(self.call(owner_reported_updated=False,measurement=None,evidence=None).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_15_stale_head(self):
        m=replace(self.meas,observed_head='old'); e=replace(self.ev,measurement_root=m.technical_root); self.assertEqual(self.call(measurement=m,evidence=e).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_16_mixed_generation(self):
        m=replace(self.meas,observed_components={'runtime':h('WRONG'),'bridge':h('bridge')}); e=replace(self.ev,measurement_root=m.technical_root); self.assertEqual(self.call(measurement=m,evidence=e).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_17_unauthenticated(self): self.assertEqual(self.call(evidence=replace(self.ev,authenticated=False)).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_18_nonindependent(self): self.assertEqual(self.call(evidence=replace(self.ev,independent=False)).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_19_source_unreproducible(self): self.assertEqual(self.call(evidence=replace(self.ev,source_incarnation_reproducible=False)).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_20_host_unbound(self): self.assertEqual(self.call(evidence=replace(self.ev,host_incarnation_bound=False)).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_21_expired(self): self.assertEqual(self.call(now_ms=self.ev.expires_at_ms+1).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_22_measurement_too_old(self): self.assertEqual(self.call(now_ms=self.now+400000).disposition,PermitDisposition.HOLD_RUNTIME)
    def test_23_release_operation_swap(self):
        man=replace(self.man,canonical_operation_root=h('other-op')); ev=replace(self.ev,release_root=man.release_root); self.assertEqual(self.call(manifest=man,evidence=ev,target=replace(self.target,release_root=man.release_root)).disposition,PermitDisposition.HOLD_RELEASE_OPERATION_MISMATCH)
    def test_24_source_cross_binding(self):
        m=replace(self.meas,source_incarnation_root=h('other-source')); e=replace(self.ev,measurement_root=m.technical_root); self.assertEqual(self.call(measurement=m,evidence=e).disposition,PermitDisposition.HOLD_SOURCE_CROSS_BINDING)
    def test_25_target_release(self): self.assertEqual(self.call(target=replace(self.target,release_root=h('other-release'))).disposition,PermitDisposition.HOLD_TARGET_RELEASE_MISMATCH)
    def test_26_target_host(self): self.assertEqual(self.call(target=replace(self.target,host_id='host-B')).disposition,PermitDisposition.HOLD_TARGET_HOST_MISMATCH)
    def test_27_target_incarnation(self): self.assertEqual(self.call(target=replace(self.target,host_incarnation='inc-B')).disposition,PermitDisposition.HOLD_TARGET_INCARNATION_MISMATCH)
    def test_28_k27_rebind_is_identity_invariant(self):
        a=self.call(); m=replace(self.meas,k27_coordinate=(26,0,26)); e=replace(self.ev,measurement_root=m.technical_root); b=self.call(measurement=m,evidence=e); self.assertEqual(a.permit_root,b.permit_root)
    def test_29_host_incarnation_rotates_permit(self):
        m=replace(self.meas,host_incarnation='inc-B'); e=replace(self.ev,measurement_root=m.technical_root); t=replace(self.target,host_incarnation='inc-B'); b=self.call(measurement=m,evidence=e,target=t); self.assertNotEqual(self.call().permit_root,b.permit_root)
    def test_30_workcell_attempt_rotates_permit(self):
        c=replace(self.ctx,workcell_root=h('other-workcell')); b=self.call(ctx=c); self.assertNotEqual(self.call().permit_root,b.permit_root)
    def test_31_owner_report_does_not_override_exact_measurement(self): self.assertEqual(self.call(owner_reported_updated=False).disposition,PermitDisposition.ADMIT_D0)
    def test_32_observer_same_as_verifier_rejected(self):
        with self.assertRaises(AttestationError): self.call(evidence=replace(self.ev,observer_id='verifier'))
    def test_33_k27_not_in_permit_root_directly(self): self.assertEqual(self.call().permit_root,self.call(measurement=replace(self.meas,k27_coordinate=None),evidence=replace(self.ev,measurement_root=replace(self.meas,k27_coordinate=None).technical_root)).permit_root)

if __name__=='__main__': unittest.main()
