import json
from dataclasses import replace
from hashlib import sha256
from tools.arena.effect_time_loaded_process_currentness import *

def base():
    a=InstalledRuntimeAttestation("host","runtime",7,100,200,True,True)
    p=LoadedProcessWitness("host","runtime","pid","start",3,9,(("core","c1"),("plugin","p1")),"dispatch",MutationModel.MUTATION_OBSERVED_AND_VERSIONED,4,(),"pop","worker-1",True,110,180,True,None)
    u=AtUseObservation(120,"host","runtime","pid","start",3,9,p.loaded_units_root(),"dispatch",4,"pop","worker-1",None,True)
    return a,p,u

def oracle(a,p,u):
    if min(u.now,a.observed_at,a.valid_until,p.observed_at,p.valid_until)<0:return False
    if not a.authenticated or not a.current or u.now>a.valid_until:return False
    if not p.authenticated or u.now>p.valid_until:return False
    if p.host_id!=a.host_id or u.host_id!=a.host_id:return False
    if p.installed_runtime_root!=a.installed_runtime_root or u.installed_runtime_root!=a.installed_runtime_root:return False
    if p.unresolved_answer_bearing_units or not p.population_complete:return False
    if u.serving_population_root!=p.serving_population_root or u.selected_worker_id!=p.worker_id:return False
    if (u.process_id,u.process_start_nonce,u.process_generation)!=(p.process_id,p.process_start_nonce,p.process_generation):return False
    if u.load_generation!=p.load_generation or u.loaded_units_root!=p.loaded_units_root() or u.dispatch_root!=p.dispatch_root:return False
    if p.mutation_model==MutationModel.MUTATION_UNOBSERVABLE:return False
    if p.mutation_model==MutationModel.MUTATION_OBSERVED_AND_VERSIONED:return u.mutation_generation==p.mutation_generation
    if p.mutation_model==MutationModel.IMMUTABLE_FOR_CUT:return bool(p.immutable_cut_root and u.immutable_cut_root==p.immutable_cut_root and u.immutable_cut_current)
    return False

def scenario(mode):
    a,p,u=base()
    if mode==0:pass
    elif mode==1:u=replace(u,process_id="pid-restart")
    elif mode==2:u=replace(u,load_generation=10)
    elif mode==3:u=replace(u,loaded_units_root="monkeypatched-root")
    elif mode==4:u=replace(u,dispatch_root="hot-swapped-dispatch")
    elif mode==5:u=replace(u,mutation_generation=5)
    elif mode==6:p=replace(p,unresolved_answer_bearing_units=("lazy-fallback",))
    elif mode==7:p=replace(p,valid_until=119)
    elif mode==8:a=replace(a,current=False)
    elif mode==9:p=replace(p,mutation_model=MutationModel.MUTATION_UNOBSERVABLE)
    elif mode==10:u=replace(u,selected_worker_id="worker-2")
    elif mode==11:u=replace(u,installed_runtime_root="runtime-other")
    return a,p,u

def installed_only(a,p,u):
    return a.authenticated and a.current and u.now<=a.valid_until and u.host_id==a.host_id and u.installed_runtime_root==a.installed_runtime_root

def load_time_only(a,p,u):
    return (installed_only(a,p,u) and p.authenticated and u.now<=p.valid_until and p.host_id==a.host_id and
            p.installed_runtime_root==a.installed_runtime_root and not p.unresolved_answer_bearing_units and p.population_complete and
            p.mutation_model!=MutationModel.MUTATION_UNOBSERVABLE)

def run(n=24000):
    out={"cases":n,"false_admit":0,"false_hold":0,"naive_installed_only_unsafe":0,"naive_load_time_only_unsafe":0,"authority_promotions":0}; reasons={}
    for i in range(n):
        a,p,u=scenario(i%12); expected=oracle(a,p,u); d=decide(a,p,u); admitted=d.disposition is Disposition.ADMIT_D0
        out["false_admit"]+=int(admitted and not expected); out["false_hold"]+=int((not admitted) and expected)
        out["naive_installed_only_unsafe"]+=int(installed_only(a,p,u) and not expected)
        out["naive_load_time_only_unsafe"]+=int(load_time_only(a,p,u) and not expected)
        out["authority_promotions"]+=int(d.effect_authority or d.checkpoint_authority or d.project_write_authority or d.gate10)
        reasons[d.reason]=reasons.get(d.reason,0)+1
    out["reasons"]=dict(sorted(reasons.items())); out["root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return out
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,indent=2))
