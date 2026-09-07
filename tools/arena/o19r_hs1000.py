import hashlib,json
B=("delegated_attempt","exact_prestate","key_precondition","patch_identity","conflict_detection","deduplication","commit_receipt","publication_boundary","resume_state","authority_ceiling")
F=("admission_equals_commit","stale_prestate","missing_resume_state","lost_update","same_target_conflict","duplicate_replay","publication_before_commit","receipt_forgery","context_override","last_write_wins")
M=("attempt_crossbind","full_state_compare","key_precondition_check","canonical_patch_root","conflict_hold","commit_dedup","durable_receipt","separate_publication","exact_resume_root","d0_nonpromotion")
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    raw=[];i=0
    for b in B:
        for f in F:
            for m in M:
                i+=1;raw.append({"id":f"O19R-HS-{i:04d}","boundary":b,"failure":f,"mechanism":m,"status":"UNSCORED_AT_FREEZE","semantics":"CANDIDATE_NOT_BREAKTHROUGH"})
    freeze=h(raw);groups={}
    for x in raw:groups.setdefault((x["boundary"],x["failure"]),[]).append(x["id"])
    q=[{"boundary":k[0],"failure":k[1],"members":v,"root":h(v)} for k,v in sorted(groups.items())]
    top=sorted(q,key=lambda x:h({"freeze":freeze,"q":x["root"]}))[:27]
    return {"schema":"aura.o19r.hs1000.v1","raw":1000,"freeze_root":freeze,"quotients":100,"quotient_root":h(q),"top27_count":27,"top27_root":h(top),"candidate_semantics":"frozen advancement candidates, not promoted breakthroughs"}
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
