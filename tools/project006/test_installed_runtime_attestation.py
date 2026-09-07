from __future__ import annotations
import unittest
from installed_runtime_attestation import *

M=RuntimeReleaseManifest('O20','dallascourchene-commits/AuraOS','head-20',25,'a'*64,{'consumer':'1'*64,'outbox':'2'*64,'wrapper':'3'*64,'guardian':'4'*64})
def measurement(**kw):
    d=dict(host_id='laptop',observed_head='head-20',observed_components=dict(M.components),host_incarnation='boot-7',source_incarnation_root='b'*64,observed_at_ms=1000,k27_coordinate=(1,2,3)); d.update(kw); return HostMeasurement(**d)
def evidence(m=None,**kw):
    m=m or measurement(); d=dict(measurement_root=m.technical_root,release_root=M.release_root,verifier_id='verifier',observer_id='observer',authenticated=True,independent=True,source_incarnation_reproducible=True,host_incarnation_bound=True,issued_at_ms=900,expires_at_ms=2000); d.update(kw); return MeasurementEvidence(**d)
class Tests(unittest.TestCase):
    def test_owner_stale_report_is_not_exact_head_or_design_failure(self):
        r=attest_runtime(M,owner_reported_updated=False,measurement=None,evidence=None,now_ms=1100); self.assertEqual(r.disposition,RuntimeDisposition.OWNER_REPORTED_STALE_UNMEASURED); self.assertIsNone(r.exact_installed_head); self.assertFalse(r.design_falsified)
    def test_no_measurement_unknown(self):
        r=attest_runtime(M,owner_reported_updated=None,measurement=None,evidence=None,now_ms=1100); self.assertEqual(r.disposition,RuntimeDisposition.UNKNOWN_UNMEASURED)
    def test_current_requires_exact_measured_manifest(self):
        m=measurement(); r=attest_runtime(M,owner_reported_updated=False,measurement=m,evidence=evidence(m),now_ms=1100); self.assertTrue(r.current); self.assertEqual(r.disposition,RuntimeDisposition.CURRENT_EXACT_HOST_OBSERVED)
    def test_owner_report_does_not_override_exact_measurement(self):
        m=measurement(); r=attest_runtime(M,owner_reported_updated=False,measurement=m,evidence=evidence(m),now_ms=1100); self.assertTrue(r.current)
    def test_stale_measured_head(self):
        m=measurement(observed_head='old-head'); r=attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=evidence(m),now_ms=1100); self.assertEqual(r.disposition,RuntimeDisposition.STALE_MEASURED_HEAD)
    def test_mixed_generation_same_head(self):
        c=dict(M.components); c['guardian']='9'*64; m=measurement(observed_components=c); r=attest_runtime(M,owner_reported_updated=True,measurement=m,evidence=evidence(m),now_ms=1100); self.assertEqual(r.disposition,RuntimeDisposition.MIXED_GENERATION)
    def test_missing_component_is_mixed(self):
        c=dict(M.components); c.pop('guardian'); m=measurement(observed_components=c); r=attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=evidence(m),now_ms=1100); self.assertEqual(r.disposition,RuntimeDisposition.MIXED_GENERATION)
    def test_forged_evidence_holds(self):
        m=measurement(); e=evidence(m,authenticated=False); self.assertEqual(attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=e,now_ms=1100).disposition,RuntimeDisposition.HOLD_UNAUTHENTICATED_MEASUREMENT)
    def test_wrong_measurement_binding_holds(self):
        m=measurement(); e=evidence(m,measurement_root='f'*64); self.assertEqual(attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=e,now_ms=1100).disposition,RuntimeDisposition.HOLD_UNAUTHENTICATED_MEASUREMENT)
    def test_source_incarnation_unresolved_holds(self):
        m=measurement(source_incarnation_root=None); e=evidence(m,source_incarnation_reproducible=False); self.assertEqual(attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=e,now_ms=1100).disposition,RuntimeDisposition.HOLD_SOURCE_INCARNATION_UNRESOLVED)
    def test_host_incarnation_unbound_holds(self):
        m=measurement(); e=evidence(m,host_incarnation_bound=False); self.assertEqual(attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=e,now_ms=1100).disposition,RuntimeDisposition.HOLD_HOST_INCARNATION_UNBOUND)
    def test_expired_holds(self):
        m=measurement(); e=evidence(m,expires_at_ms=1050); self.assertEqual(attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=e,now_ms=1100).disposition,RuntimeDisposition.HOLD_STALE_MEASUREMENT)
    def test_future_issued_holds(self):
        m=measurement(); e=evidence(m,issued_at_ms=1200,expires_at_ms=2000); self.assertEqual(attest_runtime(M,owner_reported_updated=None,measurement=m,evidence=e,now_ms=1100).disposition,RuntimeDisposition.HOLD_STALE_MEASUREMENT)
    def test_k27_move_does_not_change_technical_identity(self):
        a=measurement(k27_coordinate=(1,2,3)); b=measurement(k27_coordinate=(26,0,7)); self.assertEqual(a.technical_root,b.technical_root)
    def test_release_root_excludes_host_volatility(self):
        a=measurement(host_incarnation='boot-a'); b=measurement(host_incarnation='boot-b'); self.assertEqual(M.release_root,M.release_root); self.assertNotEqual(a.technical_root,b.technical_root)
if __name__=='__main__': unittest.main()
