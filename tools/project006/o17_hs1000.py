import hashlib,json
B=("drive_file_identity","drive_revision_identity","export_preimage","transport_pair","reported_transport_digest","proof_bound_admission","training_admission","workcell_currentness","k27_context","authority_ceiling")
F=("same_digest_new_file","same_digest_new_revision","export_normalization_move","ack_result_split","undeclared_preimage_contract","forged_proof_shape","forged_training_shape","stale_workcell","context_compensation","authority_smuggling")
M=("file_revision_root","independent_export_hash","explicit_preimage_contract","pair_cross_binding","preimage_recompute","authenticated_proof_root","authenticated_training_root","at_use_workcell_check","structural_context_exclusion","d0_only")
def h(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def build():
    raw=[]; n=0
    for b in B:
      for f in F:
       for m in M:
        n+=1; raw.append({"id":f"O17-HS-{n:04d}","boundary":b,"failure":f,"mechanism":m,"status":"UNSCORED_AT_FREEZE","semantic_class":"CANDIDATE_NOT_BREAKTHROUGH"})
    freeze=h(raw); groups={}
    for x in raw: groups.setdefault((x["boundary"],x["failure"]),[]).append(x["id"])
    q=[{"boundary":k[0],"failure":k[1],"members":tuple(v),"root":h(v)} for k,v in sorted(groups.items())]
    top=sorted(q,key=lambda x:h({"freeze":freeze,"q":x["root"]}))[:27]
    return {"schema":"aura.project006.o17.hs1000.v1","raw":len(raw),"freeze_root":freeze,"quotients":len(q),"quotient_root":h(q),"top27_count":len(top),"top27_root":h(top),"candidate_semantics":"frozen advancement candidates, not promoted breakthroughs"}
if __name__=="__main__": print(json.dumps(build(),sort_keys=True,separators=(",",":")))
