import json
from dataclasses import replace
from hashlib import sha256
from tools.arena.transactional_shared_truth_commit import *

def r(x): return sha256(x.encode()).hexdigest()

def fixture():
    current={"a":"0","b":"0","w":"1","opt":"adam","rng":"7"}; op="op"; att="att"
    a=AttemptAdmission("CREATIVE",op,att,r("src"),r("wc"),r("lease"),True,True)
    pre=state_root(current.items())
    p=CommitProposal(CommitMode.KEY_PRECONDITION,op,att,pre,(("a","1"),),(("a","0"),))
    return current,a,p

def oracle(a,p,current):
    if not a.current or not a.proof_bound:return False
    if a.operation_root!=p.operation_root or a.attempt_root!=p.attempt_root:return False
    if not p.writes or len({k for k,_ in p.writes})!=len(p.writes):return False
    root=state_root(current.items())
    if p.mode==CommitMode.EXACT_PRESTATE:return p.pre_state_root==root and p.resume_root==p.pre_state_root
    if p.mode==CommitMode.KEY_PRECONDITION:
        e=dict(p.preconditions); return set(e)=={k for k,_ in p.writes} and all(current.get(k)==e[k] for k,_ in p.writes)
    return False

def scenario(mode):
    current,a,p=fixture()
    if mode<6:
        if mode in (1,3,5):
            pre=state_root(current.items()); p=CommitProposal(CommitMode.EXACT_PRESTATE,"op","att",pre,(("w",str(2+mode)),),resume_root=pre)
        elif mode in (2,4):
            p=replace(p,writes=(("b",str(mode)),),preconditions=(("b","0"),))
        return current,a,p,True
    if mode==6:a=replace(a,current=False)
    elif mode==7:a=replace(a,proof_bound=False)
    elif mode==8:a=replace(a,operation_root="other")
    elif mode==9:a=replace(a,attempt_root="other")
    elif mode in (10,14,18,22):
        pre=r(f"stale-{mode}"); p=CommitProposal(CommitMode.EXACT_PRESTATE,"op","att",pre,(("w",str(mode)),),resume_root=pre)
    elif mode in (11,15,19,23):
        pre=state_root(current.items()); p=CommitProposal(CommitMode.EXACT_PRESTATE,"op","att",pre,(("w",str(mode)),),resume_root=r("wrong"))
    elif mode in (12,16,20): p=replace(p,preconditions=())
    elif mode in (13,17,21): p=replace(p,preconditions=(("a","old"),))
    return current,a,p,False

def run(n=24000):
    out={"cases":n,"false_commit":0,"false_hold":0,"naive_admission_means_commit_unsafe":0,"naive_last_write_wins_unsafe":0,"authority_promotions":0}; reasons={}
    for i in range(n):
        current,a,p,_=scenario(i%24); ok,reason=evaluate_snapshot(a,p,current); expected=oracle(a,p,current)
        out["false_commit"]+=int(ok and not expected); out["false_hold"]+=int((not ok) and expected)
        naive_admission=a.current and a.proof_bound and a.operation_root==p.operation_root and a.attempt_root==p.attempt_root
        naive_lww=a.operation_root==p.operation_root and a.attempt_root==p.attempt_root
        out["naive_admission_means_commit_unsafe"]+=int(naive_admission and not expected)
        out["naive_last_write_wins_unsafe"]+=int(naive_lww and not expected)
        reasons[reason]=reasons.get(reason,0)+1
    out["reasons"]=dict(sorted(reasons.items())); out["root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return out
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,indent=2))
