from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from itertools import product
import json, random, sys
from provider_observation_slice_bridge import *

PARENT="a"*40; CHILD="b"*40; PROVIDER="github"; REPO="dallascourchene-commits/AuraOS"; CR="PR-999"
GEN="AuraOS CODEMAP Bot"; VERIFIER="auraos-provider-proof-bridge"; PATHS=(".aura/CODEMAP.json",".aura/CODEMAP.md")
GRAPH="1"*64; PAYLOAD="3"*64; SEMANTIC_RECEIPT="4"*64
BINDINGS=(PathBinding(PATHS[0],("provider_binding",)),PathBinding(PATHS[1],("provider_binding",)))

def obs(status=EvidenceStatus.ATTESTED, **kw):
    d=dict(provider=PROVIDER,repository=REPO,change_request_id=CR,parent_head=PARENT,child_head=CHILD,actor_identity="provider-bot",generator_identity=GEN,changed_paths=PATHS,evidence_uri="https://api.github.com/repos/dallascourchene-commits/AuraOS/pulls/999",captured_at="2026-09-05T23:40:00Z",verifier_id=VERIFIER,verifier_generation="v1",status=status,payload_sha256=PAYLOAD); d.update(kw); return observation_for(**d)
def ex(**kw):
    d=dict(provider=PROVIDER,repository=REPO,change_request_id=CR,proved_parent_head=PARENT,current_child_head=CHILD,expected_generator_identity=GEN,allowed_proof_neutral_paths=PATHS,accepted_verifier_ids=(VERIFIER,)); d.update(kw); return MovementExpectation(**d)
def adm(**kw):
    d=dict(graph_root=GRAPH,verifier_generations=(("AGENT09","agent09-e68b9188"),),accepted_witness_roots=(("cost_receipt","5"*64),("trace_receipt","6"*64)),observation_generation="obs-g1",external_receipt_root=SEMANTIC_RECEIPT); d.update(kw); return semantic_admission_for(**d)
def plan(a=None,**kw):
    a=a or adm(); d=dict(graph_root=GRAPH,changed_roots=("provider_binding",),invalidated=("combined_reuse","provider_binding"),reusable=("cost_receipt","trace_receipt"),recompute_order=("provider_binding","combined_reuse"),affected_consequence_keys=("provider_binding","proof_reuse"),admission_surface_root=a.surface_root,decision="RECOMPUTE_MINIMUM_SLICE",plan_root="2"*64); d.update(kw); return SlicePlanAttestation(**d)
def ev(o=None,x=None,b=None,a=None,p=None,**kw):
    a=a or adm(); d=dict(observation=o or obs(),expectation=x or ex(),bindings=b or BINDINGS,semantic_admission=a,slice_plan=p or plan(a),expected_graph_root=GRAPH,authority_requested=False); d.update(kw); return BridgeEvidence(**d)

# Independent oracle intentionally does not call reasons() or decide().
def oracle(e: BridgeEvidence) -> str:
    try:
        o,x,a,p=e.observation,e.expectation,e.semantic_admission,e.slice_plan
        if type(o) is not ProviderObservation or type(x) is not MovementExpectation or type(a) is not SemanticAdmissionSurface or type(p) is not SlicePlanAttestation: return Decision.HOLD_DAG_PLAN.value
        if not isinstance(o.status,EvidenceStatus) or o.observation_root != digest(observation_body(o)): return Decision.HOLD_MOVEMENT_BINDING.value
        if x.agent10_semantic_commit != AGENT10_PARENT_COMMIT: return Decision.HOLD_MOVEMENT_BINDING.value
        if (o.provider,o.repository,o.change_request_id)!=(x.provider,x.repository,x.change_request_id): return Decision.HOLD_MOVEMENT_BINDING.value
        if o.parent_head!=x.proved_parent_head or o.child_head!=x.current_child_head or o.generator_identity!=x.expected_generator_identity: return Decision.HOLD_MOVEMENT_BINDING.value
        if o.verifier_id not in x.accepted_verifier_ids or not set(o.changed_paths).issubset(set(x.allowed_proof_neutral_paths)): return Decision.HOLD_MOVEMENT_BINDING.value
        bm={binding.path:tuple(sorted(binding.evidence_nodes)) for binding in e.bindings}
        if len(bm)!=len(e.bindings) or any(path not in bm for path in o.changed_paths) or e.authority_requested is not False: return Decision.HOLD_MOVEMENT_BINDING.value
        if o.status is not EvidenceStatus.ATTESTED: return Decision.HOLD_PROVIDER_EVIDENCE.value
        if a.surface_root != digest(semantic_admission_body(a)) or a.graph_root != e.expected_graph_root: return Decision.HOLD_SEMANTIC_ADMISSION.value
        nodes=tuple(sorted({node for path in o.changed_paths for node in bm[path]}))
        if p.dag_semantic_commit!=EVIDENCE_DAG_PARENT_COMMIT or p.dag_schema!=EVIDENCE_DAG_SCHEMA: return Decision.HOLD_DAG_PLAN.value
        if p.graph_root!=e.expected_graph_root or p.graph_root!=a.graph_root or p.changed_roots!=nodes or p.admission_surface_root!=a.surface_root: return Decision.HOLD_DAG_PLAN.value
        if p.decision not in {"RECOMPUTE_MINIMUM_SLICE","RECOMPUTE_ALL"}: return Decision.HOLD_DAG_PLAN.value
        if not set(p.changed_roots).issubset(set(p.invalidated)) or set(p.invalidated)&set(p.reusable) or set(p.recompute_order)!=set(p.invalidated): return Decision.HOLD_DAG_PLAN.value
        return Decision.REPROVE_MINIMUM_SLICE.value
    except Exception:
        return Decision.HOLD_DAG_PLAN.value


def mutate(rng: random.Random, e: BridgeEvidence):
    family=rng.randrange(18)
    if family==0: return replace(e,observation=replace(e.observation,status=EvidenceStatus.OBSERVED))
    if family==1: return replace(e,observation=replace(e.observation,status=EvidenceStatus.CONTESTED))
    if family==2: return replace(e,observation=replace(e.observation,observation_root="f"*64))
    if family==3: return replace(e,observation=obs(parent_head="c"*40))
    if family==4: return replace(e,observation=obs(generator_identity="Other Bot"))
    if family==5: return replace(e,observation=obs(verifier_id="other"))
    if family==6: return replace(e,observation=obs(changed_paths=PATHS+("tools/arena/frontier27_runtime.py",)))
    if family==7:
        a=replace(e.semantic_admission,surface_root="f"*64); return replace(e,semantic_admission=a,slice_plan=replace(e.slice_plan,admission_surface_root="f"*64))
    if family==8:
        a=adm(graph_root="f"*64); return replace(e,semantic_admission=a,slice_plan=plan(a,graph_root="f"*64))
    if family==9: return replace(e,slice_plan=replace(e.slice_plan,admission_surface_root="f"*64))
    if family==10: return replace(e,slice_plan=replace(e.slice_plan,graph_root="f"*64))
    if family==11: return replace(e,slice_plan=replace(e.slice_plan,changed_roots=("other",),invalidated=("other","combined_reuse"),recompute_order=("other","combined_reuse")))
    if family==12: return replace(e,slice_plan=replace(e.slice_plan,dag_semantic_commit="88aa998ae80677375ebc8fcda3ea08c7cb894a6e"))
    if family==13: return replace(e,slice_plan=replace(e.slice_plan,dag_schema="AURA-EVIDENCE-SLICE-DAG-v1"))
    if family==14: return replace(e,expectation=ex(agent10_semantic_commit="c"*40))
    if family==15: return replace(e,authority_requested=True)
    if family==16: return replace(e,slice_plan=replace(e.slice_plan,reusable=("combined_reuse",)))
    return e


def main(seed=18807,trials=100000):
    rng=random.Random(seed); base=ev(); mismatches=0; false_reuse=0; h=sha256(); counts={}
    for i in range(trials):
        e=base if i%29==0 else mutate(rng,base)
        got=decide(e).value; want=oracle(e); counts[got]=counts.get(got,0)+1
        mismatches += got!=want
        false_reuse += got==Decision.REPROVE_MINIMUM_SLICE.value and want!=got
        h.update(json.dumps([i,got,want,make_receipt(e).receipt_root],separators=(",",":"),sort_keys=True).encode())
    omega=exhaustive8(); tail_repairs=0; tail_roots=set(); core=[2,2,2,2,2,2,2,1]; core[4]=0
    for tail in product(range(3),repeat=5):
        tail_roots.add(digest({"tail":tail}))
        tail_repairs += classify13(tuple(core)+tail)==Decision.REPROVE_MINIMUM_SLICE.value
    hs_false=0; families=[]
    for family in range(10):
        for i in range(100):
            e=mutate(random.Random(910000+family*100+i),base); got=decide(e).value; want=oracle(e)
            hs_false += got==Decision.REPROVE_MINIMUM_SLICE.value and want!=got; families.append((family,i,got))
    parent_surface_reference=digest({"schema":ADMISSION_SCHEMA,"graph_root":GRAPH,"verifier_generations":(("AGENT09","agent09-e68b9188"),),"accepted_witness_roots":(("cost_receipt","5"*64),("trace_receipt","6"*64)),"observation_generation":"obs-g1","external_receipt_root":SEMANTIC_RECEIPT})
    result={"schema":SCHEMA,"seed":seed,"trials":trials,"oracle_mismatches":mismatches,"false_reuse":false_reuse,"decision_counts":counts,"oracle_root":h.hexdigest(),"omega8":omega,"tail_contexts":len(tail_roots),"hard_invalid_tail_repairs":tail_repairs,"hs1000_cases":len(families),"hs1000_false_reuse":hs_false,"parent_admission_surface_match":parent_surface_reference==base.semantic_admission.surface_root,"valid_receipt_root":make_receipt(base).receipt_root}
    result["campaign_root"]=digest(result); print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0 if mismatches==0 and false_reuse==0 and tail_repairs==0 and hs_false==0 and result["parent_admission_surface_match"] else 1

if __name__=="__main__":
    seed=int(sys.argv[1]) if len(sys.argv)>1 else 18807; trials=int(sys.argv[2]) if len(sys.argv)>2 else 100000; raise SystemExit(main(seed,trials))
