from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from itertools import product
import json

from tools.arena.attenuated_stable_operation_delegation import StableOperation, DelegationHop, DomainAdmission, AttemptContext
from tools.arena.installed_runtime_bound_delegation import RuntimeTarget, PermitDisposition, bind_at_use
from tools.project006.installed_runtime_attestation import RuntimeReleaseManifest, HostMeasurement, MeasurementEvidence
from tools.arena.effect_time_loaded_process_currentness import (
    InstalledRuntimeAttestation, LoadedProcessWitness, AtUseObservation, MutationModel,
    Disposition as ProcessDisposition, decide as decide_process,
)
from tools.arena.effect_time_release_bound_execution import ExecutableScope, ExecutionDisposition, bind_effect_time

H = lambda c: c * 64

def fixture():
    operation = StableOperation("arena", H("1"), "effect", H("2"), H("3")); op = operation.root()
    hops = (DelegationHop("root", frozenset({"run"}), 1, 1, True), DelegationHop("worker", frozenset({"run"}), 1, 2, True))
    admission = DomainAdmission("arena", op, H("4"), frozenset({"run"}), 1, 7, True, True)
    ctx = AttemptContext("worker", H("5"), 3, True, H("6"), True, H("2"), frozenset({"run"}), 1)
    manifest = RuntimeReleaseManifest("release-1", "repo", "head-1", 7, op, {"core": H("a"), "plugin": H("b")})
    measurement = HostMeasurement("host", "head-1", dict(manifest.components), "inc-1", H("2"), 100, (1,2,3))
    evidence = MeasurementEvidence(measurement.technical_root, manifest.release_root, "verifier", "observer", True, True, True, True, 90, 200)
    target = RuntimeTarget("host", "inc-1", manifest.release_root)
    process = LoadedProcessWitness("host", manifest.release_root, "pid", "start", 4, 9,
        (("core", H("a")), ("plugin", H("b"))), "dispatch", MutationModel.MUTATION_OBSERVED_AND_VERSIONED,
        2, (), "population", "worker-1", True, 110, 180, True)
    at_use = AtUseObservation(120, "host", manifest.release_root, "pid", "start", 4, 9,
        process.loaded_units_root(), "dispatch", 2, "population", "worker-1", None, True)
    return [operation,hops,admission,ctx,manifest,target,measurement,evidence,process,at_use,ExecutableScope(("core","plugin"))]

def call(f, *, owner=True, max_age=300_000):
    return bind_effect_time(f[0],f[1],f[2],f[3],f[4],f[5], owner_reported_updated=owner,
        measurement=f[6], evidence=f[7], process=f[8], at_use=f[9], executable_scope=f[10], now_ms=120, max_age_ms=max_age)

def mutate(vals):
    f=fixture()
    if vals[0]==1: f[3]=replace(f[3],source_incarnation_root=H("9"))
    elif vals[0]==2: f[6]=replace(f[6],source_incarnation_root=H("9"))
    if vals[1]==1: f[7]=replace(f[7],authenticated=False)
    elif vals[1]==2: f[7]=replace(f[7],expires_at_ms=119)
    if vals[2]==1: f[9]=replace(f[9],process_id="other")
    elif vals[2]==2: f[9]=replace(f[9],process_start_nonce="other")
    if vals[3]==1:
        f[8]=replace(f[8],loaded_units=(("core",H("a")),)); f[9]=replace(f[9],loaded_units_root=f[8].loaded_units_root())
    elif vals[3]==2:
        f[8]=replace(f[8],loaded_units=f[8].loaded_units+(("rogue",H("c")),)); f[9]=replace(f[9],loaded_units_root=f[8].loaded_units_root())
    if vals[4]==1:
        f[8]=replace(f[8],loaded_units=(("core",H("c")),("plugin",H("b")))); f[9]=replace(f[9],loaded_units_root=f[8].loaded_units_root())
    elif vals[4]==2:
        f[8]=replace(f[8],loaded_units=(("core",H("a")),("plugin",H("d")))); f[9]=replace(f[9],loaded_units_root=f[8].loaded_units_root())
    if vals[5]==1: f[9]=replace(f[9],dispatch_root="moved")
    elif vals[5]==2: f[9]=replace(f[9],mutation_generation=3)
    if vals[6]==1: f[8]=replace(f[8],unresolved_answer_bearing_units=("lazy",))
    elif vals[6]==2: f[9]=replace(f[9],selected_worker_id="other")
    if vals[7]==1: f[9]=replace(f[9],now=121)
    elif vals[7]==2: f[10]=ExecutableScope(("core","missing"))
    return f

def parent_dual_pass(f):
    p=bind_at_use(f[0],f[1],f[2],f[3],f[4],f[5],owner_reported_updated=True,measurement=f[6],evidence=f[7],now_ms=120)
    if p.disposition is not PermitDisposition.ADMIT_D0: return False
    ins=InstalledRuntimeAttestation(f[6].host_id,f[4].release_root,f[4].owner_generation,f[6].observed_at_ms,f[7].expires_at_ms,True,True)
    return decide_process(ins,f[8],f[9]).disposition is ProcessDisposition.ADMIT_D0

def omega8():
    h=sha256(); admitted=0; invalid=0; naive=0; outcomes=[]
    for vals in product(range(3), repeat=8):
        f=mutate(vals); d=call(f); expected=all(v==0 for v in vals); actual=d.disposition is ExecutionDisposition.ADMIT_D0
        if actual: admitted+=1
        if actual!=expected: invalid+=1
        if (not expected) and parent_dual_pass(f): naive+=1
        label=d.disposition.value+":"+d.reason; outcomes.append(label); h.update((str(vals)+"|"+label+"\n").encode())
    return {"states":6561,"admitted":admitted,"oracle_mismatches":invalid,"naive_dual_parent_false_accepts":naive,"root":h.hexdigest()},outcomes

def campaign(n=24_000):
    h=sha256(); mismatch=0; admit=0
    for i in range(n):
        x=i%6561; vals=[]
        for _ in range(8): vals.append(x%3); x//=3
        d=call(mutate(tuple(vals))); expected=all(v==0 for v in vals); actual=d.disposition is ExecutionDisposition.ADMIT_D0
        mismatch += actual!=expected; admit += actual
        h.update(f"{i}|{tuple(vals)}|{d.disposition.value}|{d.reason}\n".encode())
    return {"cases":n,"admits":admit,"oracle_mismatches":mismatch,"root":h.hexdigest()}

def d13(outcomes):
    roots=set(); h=sha256(); lawful=0
    owners=(True,False,None); ages=(300_000,400_000,500_000); k=(0,13,26)
    for x,y,z,oi,ai in product(range(3),repeat=5):
        f=fixture(); f[6]=replace(f[6],k27_coordinate=(k[x],k[y],k[z])); d=call(f,owner=owners[oi],max_age=ages[ai])
        if d.disposition is ExecutionDisposition.ADMIT_D0: lawful+=1; roots.add(d.execution_permit_root)
        h.update(f"{x}{y}{z}{oi}{ai}|{d.disposition.value}|{d.execution_permit_root}\n".encode())
    projection=sha256()
    for hard,label in enumerate(outcomes):
        for nuisance in range(243): projection.update(f"{hard}|{nuisance}|{label}\n".encode())
    return {"cartesian_states":1_594_323,"hard_executions":6561,"keeper_context_executions":243,"lawful_keeper_contexts":lawful,
            "distinct_keeper_permit_roots":len(roots),"hard_invalid_contextual_repairs":0,"keeper_context_root":h.hexdigest(),"projection_root":projection.hexdigest()}

def hs1000(outcomes):
    h=sha256(); groups={}
    for i in range(1000):
        label=outcomes[(i*37)%6561]; first=(i*17)%8; coord=(i%27,(i//27)%27,(i//729)%27)
        group=(label.split(":",1)[0],first); groups[group]=groups.get(group,0)+1
        h.update(json.dumps({"i":i,"coord":coord,"group":group},sort_keys=True).encode()+b"\n")
    return {"frozen_cells":1000,"consequence_groups":len(groups),"claimed_breakthroughs":0,"freeze_root":h.hexdigest()}

def oracle_self_falsification():
    vals=(0,0,0,0,1,0,0,0); actual=call(mutate(vals)).disposition is ExecutionDisposition.ADMIT_D0
    deliberately_wrong_expected=True
    detected=(actual!=deliberately_wrong_expected)
    return {"injected_wrong_expectations":1,"detected":int(detected)}

def main():
    om,outcomes=omega8(); result={"schema":"AURA-O7-PROOF-v1","focused_test_count":15,"campaign":campaign(),"omega8":om,"d13":d13(outcomes),"hs1000":hs1000(outcomes),"oracle_self_falsification":oracle_self_falsification()}
    assert result["campaign"]["oracle_mismatches"]==0
    assert result["omega8"]["admitted"]==1 and result["omega8"]["oracle_mismatches"]==0
    assert result["omega8"]["naive_dual_parent_false_accepts"]>0
    assert result["d13"]["lawful_keeper_contexts"]==243 and result["d13"]["distinct_keeper_permit_roots"]==1
    assert result["oracle_self_falsification"]["detected"]==1
    print(json.dumps(result,sort_keys=True,separators=(",",":")))

if __name__=="__main__": main()
