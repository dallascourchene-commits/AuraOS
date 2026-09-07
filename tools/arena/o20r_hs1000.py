import hashlib,json
B=("installed_runtime","process_incarnation","loaded_units","dispatch_identity","mutation_model","lazy_units","worker_population","effect_time_revalidation","process_aba","authority_ceiling")
F=("installed_equals_loaded","load_time_equals_effect_time","process_restart","hot_reload","monkeypatch_or_registry_swap","jit_or_plugin_load","lazy_fallback","mixed_worker_generation","unobservable_mutation","context_override")
M=("installed_attestation_bind","process_start_nonce","loaded_units_root","dispatch_root","mutation_generation_or_cut","unresolved_unit_hold","population_selection_bind","at_use_observation","generation_lineage","d0_nonpromotion")
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    raw=[];i=0
    for b in B:
        for f in F:
            for m in M:
                i+=1;raw.append({"id":f"O20R-HS-{i:04d}","boundary":b,"failure":f,"mechanism":m,"status":"UNSCORED_AT_FREEZE","semantics":"CANDIDATE_NOT_BREAKTHROUGH"})
    freeze=h(raw);groups={}
    for x in raw:groups.setdefault((x["boundary"],x["failure"]),[]).append(x["id"])
    q=[{"boundary":k[0],"failure":k[1],"members":v,"root":h(v)} for k,v in sorted(groups.items())]
    top=sorted(q,key=lambda x:h({"freeze":freeze,"q":x["root"]}))[:27]
    return {"schema":"aura.o20r.hs1000.v1","raw":1000,"freeze_root":freeze,"quotients":100,"quotient_root":h(q),"top27_count":27,"top27_root":h(top),"candidate_semantics":"frozen advancement candidates, not promoted breakthroughs"}
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
