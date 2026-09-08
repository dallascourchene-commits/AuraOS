import hashlib,unittest
from dataclasses import replace
from tools.project006.effect_time_loaded_execution import *
def H(x):return hashlib.sha256(x.encode()).hexdigest()
def fx(pop=1):
    m=ExecutionTopologyManifest(H('rel'),H('src'),H('topo'),H('unit'),H('dispatch'))
    p=LoadedProcessMeasurement(m.release_root,m.source_root,m.target_topology_root,H('proc'),7,8,9,m.answer_unit_root,m.dispatch_root,(),H('pop'),pop,H('worker') if pop>1 else None,1000)
    e=ProcessEvidence(p.measurement_root,m.manifest_root,'verifier','observer',True,True,1050,2000)
    x=AtUseExpectation(p.process_identity_root,7,8,9,H('worker') if pop>1 else None,1100,500)
    return m,p,e,x
class T(unittest.TestCase):
    def test_current(self): m,p,e,x=fx(); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.CURRENT_EFFECT_EXECUTABLE)
    def test_release(self): m,p,e,x=fx(); p=replace(p,installed_release_root=H('old')); e=replace(e,measurement_root=p.measurement_root); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_INSTALLED_RELEASE)
    def test_source(self): m,p,e,x=fx(); p=replace(p,source_root=H('other')); e=replace(e,measurement_root=p.measurement_root); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_SOURCE_TOPOLOGY)
    def test_topology(self): m,p,e,x=fx(); p=replace(p,target_topology_root=H('other')); e=replace(e,measurement_root=p.measurement_root); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_SOURCE_TOPOLOGY)
    def test_auth(self): m,p,e,x=fx(); e=replace(e,authenticated=False); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_UNAUTHENTICATED_PROCESS)
    def test_process(self): m,p,e,x=fx(); x=replace(x,process_identity_root=H('new')); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_PROCESS_IDENTITY)
    def test_process_gen(self): m,p,e,x=fx(); x=replace(x,process_generation=8); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_PROCESS_GENERATION)
    def test_load_gen(self): m,p,e,x=fx(); x=replace(x,load_generation=9); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_LOAD_GENERATION)
    def test_mutation_gen(self): m,p,e,x=fx(); x=replace(x,mutation_generation=10); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_MUTATION_GENERATION)
    def test_answer_unit(self): m,p,e,x=fx(); p=replace(p,loaded_answer_unit_root=H('stale')); e=replace(e,measurement_root=p.measurement_root); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_ANSWER_UNIT)
    def test_dispatch(self): m,p,e,x=fx(); p=replace(p,dispatch_root=H('stale')); e=replace(e,measurement_root=p.measurement_root); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_DISPATCH)
    def test_unresolved(self): m,p,e,x=fx(); p=replace(p,unresolved_units=('lazy.plugin',)); e=replace(e,measurement_root=p.measurement_root); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_UNRESOLVED_UNIT)
    def test_population_requires_selection(self): m,p,e,x=fx(2); x=replace(x,selected_worker_root=None); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_WORKER_SELECTION)
    def test_worker_mismatch(self): m,p,e,x=fx(2); x=replace(x,selected_worker_root=H('other')); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_WORKER_SELECTION)
    def test_stale(self): m,p,e,x=fx(); x=replace(x,now_ms=3000); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_STALE_EFFECT_TIME)
    def test_evidence_cannot_predate_measurement(self): m,p,e,x=fx(); e=replace(e,issued_at_ms=900); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_STALE_EFFECT_TIME)
    def test_future_measurement_cannot_be_current(self): m,p,e,x=fx(); p=replace(p,observed_at_ms=1200); e=replace(e,measurement_root=p.measurement_root,issued_at_ms=1000); self.assertEqual(attest_loaded_execution(m,p,e,x).disposition,Disposition.HOLD_STALE_EFFECT_TIME)
    def test_k27_absent_from_identity(self): m,p,e,x=fx(); self.assertTrue(attest_loaded_execution(m,p,e,x).current)
if __name__=='__main__':unittest.main()
