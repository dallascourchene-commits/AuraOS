import unittest
from dataclasses import replace
from tools.arena.effect_time_loaded_process_currentness import *

def base(model=MutationModel.MUTATION_OBSERVED_AND_VERSIONED):
    a=InstalledRuntimeAttestation("host","runtime",7,100,200,True,True)
    p=LoadedProcessWitness("host","runtime","pid","start",3,9,(("core","c1"),("plugin","p1")),"dispatch",model,4,(),"pop","worker-1",True,110,180,True,"cut" if model==MutationModel.IMMUTABLE_FOR_CUT else None)
    u=AtUseObservation(120,"host","runtime","pid","start",3,9,p.loaded_units_root(),"dispatch",4,"pop","worker-1","cut" if model==MutationModel.IMMUTABLE_FOR_CUT else None,True)
    return a,p,u

class O20RTests(unittest.TestCase):
    def test_versioned_valid(self):
        a,p,u=base(); self.assertEqual(decide(a,p,u).disposition,Disposition.ADMIT_D0)
    def test_immutable_valid(self):
        a,p,u=base(MutationModel.IMMUTABLE_FOR_CUT); self.assertEqual(decide(a,p,u).disposition,Disposition.ADMIT_D0)
    def test_installed_not_current(self):
        a,p,u=base(); self.assertEqual(decide(replace(a,current=False),p,u).reason,"INSTALLED_ATTESTATION_NOT_CURRENT_AUTHENTIC")
    def test_installed_unauthenticated(self):
        a,p,u=base(); self.assertEqual(decide(replace(a,authenticated=False),p,u).reason,"INSTALLED_ATTESTATION_NOT_CURRENT_AUTHENTIC")
    def test_installed_expired(self):
        a,p,u=base(); self.assertEqual(decide(replace(a,valid_until=119),p,u).reason,"INSTALLED_ATTESTATION_EXPIRED")
    def test_process_unauthenticated(self):
        a,p,u=base(); self.assertEqual(decide(a,replace(p,authenticated=False),u).reason,"PROCESS_WITNESS_NOT_AUTHENTICATED")
    def test_process_expired(self):
        a,p,u=base(); self.assertEqual(decide(a,replace(p,valid_until=119),u).reason,"PROCESS_WITNESS_EXPIRED")
    def test_host_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,host_id="other")).reason,"HOST_IDENTITY_MISMATCH")
    def test_installed_root_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,installed_runtime_root="other")).reason,"INSTALLED_RUNTIME_ROOT_MISMATCH")
    def test_unresolved_lazy_unit(self):
        a,p,u=base(); self.assertEqual(decide(a,replace(p,unresolved_answer_bearing_units=("lazy",)),u).reason,"UNRESOLVED_ANSWER_BEARING_UNIT")
    def test_population_incomplete(self):
        a,p,u=base(); self.assertEqual(decide(a,replace(p,population_complete=False),u).reason,"SERVING_POPULATION_INCOMPLETE")
    def test_worker_selection_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,selected_worker_id="worker-2")).reason,"SERVING_WORKER_SELECTION_MOVED")
    def test_population_root_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,serving_population_root="other")).reason,"SERVING_WORKER_SELECTION_MOVED")
    def test_process_id_restart(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,process_id="pid2")).reason,"PROCESS_INCARCATION_MOVED")
    def test_process_start_aba(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,process_start_nonce="new-start")).reason,"PROCESS_INCARCATION_MOVED")
    def test_process_generation_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,process_generation=4)).reason,"PROCESS_INCARCATION_MOVED")
    def test_load_generation_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,load_generation=10)).reason,"LOAD_GENERATION_MOVED")
    def test_loaded_units_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,loaded_units_root="monkeypatch")).reason,"LOADED_ANSWER_BEARING_UNITS_MOVED")
    def test_dispatch_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,dispatch_root="new-dispatch")).reason,"DISPATCH_IDENTITY_MOVED")
    def test_mutation_generation_move(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,mutation_generation=5)).reason,"MUTATION_GENERATION_MOVED")
    def test_unobservable_mutation_holds(self):
        a,p,u=base(); p=replace(p,mutation_model=MutationModel.MUTATION_UNOBSERVABLE); self.assertEqual(decide(a,p,u).reason,"UNOBSERVABLE_RUNTIME_MUTATION")
    def test_immutable_cut_move(self):
        a,p,u=base(MutationModel.IMMUTABLE_FOR_CUT); self.assertEqual(decide(a,p,replace(u,immutable_cut_root="other")).reason,"IMMUTABILITY_CUT_NOT_CURRENT")
    def test_immutable_cut_stale(self):
        a,p,u=base(MutationModel.IMMUTABLE_FOR_CUT); self.assertEqual(decide(a,p,replace(u,immutable_cut_current=False)).reason,"IMMUTABILITY_CUT_NOT_CURRENT")
    def test_malformed_time(self):
        a,p,u=base(); self.assertEqual(decide(a,p,replace(u,now=-1)).reason,"MALFORMED_TIME")
    def test_authority_ceiling(self):
        a,p,u=base(); d=decide(a,p,u); self.assertFalse(d.effect_authority or d.checkpoint_authority or d.project_write_authority or d.gate10)

if __name__=="__main__": unittest.main()
