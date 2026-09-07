import hashlib,json
B=("cache_identity","producer_provenance","stable_operation","dependency_closure","consumer_permit","source_incarnation","effect_time_process","namespace_output","volatile_view_context","authority_ceiling")
F=("cache_hit_equals_permission","producer_shape_trust","operation_move","dependency_move","permit_stale","source_move","process_stale","namespace_alias","k27_view_in_identity","context_override")
M=("canonical_artifact_root","producer_receipt_auth","operation_bind","dependency_bind","runtime_bound_permit","source_incarnation_bind","effect_time_process_bind","namespace_output_policy","separate_consumption_receipt","d0_nonpromotion")
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    raw=[];i=0
    for b in B:
        for f in F:
            for m in M:
                i+=1;raw.append({"id":f"O21R-HS-{i:04d}","boundary":b,"failure":f,"mechanism":m,"status":"UNSCORED_AT_FREEZE","semantics":"CANDIDATE_NOT_BREAKTHROUGH"})
    freeze=h(raw);groups={}
    for x in raw:groups.setdefault((x["boundary"],x["failure"]),[]).append(x["id"])
    q=[{"boundary":k[0],"failure":k[1],"members":v,"root":h(v)} for k,v in sorted(groups.items())]
    top=sorted(q,key=lambda x:h({"freeze":freeze,"q":x["root"]}))[:27]
    return {"schema":"aura.o21r.hs1000.v1","raw":1000,"freeze_root":freeze,"quotients":100,"quotient_root":h(q),"top27_count":27,"top27_root":h(top),"candidate_semantics":"frozen advancement candidates, not promoted breakthroughs"}
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
