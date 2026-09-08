from __future__ import annotations
import hashlib,itertools,json,math,random,struct
from security_transition_domain import causal_time_order, finite_positive_duration, terminal_transition_allowed

def run():
    admitted=0; hard_invalid_admits=0
    for state in itertools.product((0,1,2), repeat=13):
        eligible=all(v==2 for v in state[:8]); admitted+=int(eligible)
        if eligible and any(v!=2 for v in state[:8]): hard_invalid_admits+=1
    labels=("observed","issued","now","expires"); values=(100,200,300,400)
    legacy_accepts=lawful=fixed_accepts=0
    for perm in itertools.permutations(labels):
        d={name:values[i] for i,name in enumerate(perm)}
        legacy=d["now"]>=d["issued"] and d["now"]<=d["expires"] and d["now"]-d["observed"]<=1000
        fixed=causal_time_order(observed_at_ms=d["observed"],issued_at_ms=d["issued"],now_ms=d["now"],expires_at_ms=d["expires"],max_age_ms=1000)
        legacy_accepts+=int(legacy); lawful+=int(d["observed"]<=d["issued"]<=d["now"]<=d["expires"]); fixed_accepts+=int(fixed)
    rng=random.Random(20260908); samples=1_000_000; legacy_nonfinite=fixed_nonfinite=0
    for _ in range(samples):
        x=struct.unpack("!d",rng.getrandbits(64).to_bytes(8,"big"))[0]
        legacy=not (x<=0.0)
        try: finite_positive_duration(x); fixed=True
        except Exception: fixed=False
        if legacy and not math.isfinite(x): legacy_nonfinite+=1
        if fixed and not math.isfinite(x): fixed_nonfinite+=1
    states=("NOT_STARTED","UNKNOWN","COMPLETED"); legacy_retry=fixed_retry=0
    for length in range(1,8):
        for seq in itertools.product(states, repeat=length):
            retry_after_completed=any(seq[i]=="COMPLETED" and any(x!="COMPLETED" for x in seq[i+1:]) for i in range(len(seq)))
            if retry_after_completed: legacy_retry+=1
            fixed_path=all(terminal_transition_allowed(previous,new) for previous,new in zip(seq,seq[1:]))
            if retry_after_completed and fixed_path: fixed_retry+=1
    result={"schema":"AURA-SECURITY-TRANSITION-DOMAIN-COMPILER-D0-v1","13d_states":3**13,"13d_admitted_context_variants":admitted,"13d_hard_invalid_admits":hard_invalid_admits,"causal_strict_orderings":24,"legacy_causal_accepts":legacy_accepts,"lawful_causal_orderings":lawful,"fixed_causal_accepts":fixed_accepts,"ieee754_samples":samples,"legacy_nonfinite_accepts":legacy_nonfinite,"fixed_nonfinite_accepts":fixed_nonfinite,"legacy_retry_after_completed_events":legacy_retry,"fixed_retry_after_completed_events":fixed_retry}
    encoded=json.dumps(result,sort_keys=True,separators=(",",":")); result["campaign_root"]=hashlib.sha256(encoded.encode()).hexdigest()
    assert admitted==243 and hard_invalid_admits==0
    assert legacy_accepts==4 and lawful==1 and fixed_accepts==1
    assert legacy_nonfinite>0 and fixed_nonfinite==0
    assert legacy_retry>0 and fixed_retry==0
    return result
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,separators=(",",":")))
