import hashlib, itertools, json, os, random, sys
from dataclasses import replace
ROOT=os.path.dirname(__file__); sys.path.insert(0,os.path.join(ROOT,"src"))
from generation_reproof_certificate import *

def oracle(prior, ta, tb):
    # Independent spelling of the decision law; no call to compile_reproof.
    obligations=[]; states=[]; new=[]
    for old,t in ((prior.parent_a,ta),(prior.parent_b,tb)):
        if t.old_snapshot_root!=old.snapshot_root or not t.owner_verified or t.owner_transition_root!=t.expected_owner_transition_root:
            states.append("UNKNOWN"); obligations.append(f"{old.role}:VERIFY_OR_REPROVE_PARENT" if t.old_snapshot_root==old.snapshot_root else f"{old.role}:OLD_BINDING_MISMATCH")
        elif not t.new_snapshot.verified or not t.new_snapshot.current or not t.new_snapshot.d0 or t.transition_class is TransitionClass.UNKNOWN:
            states.append("UNKNOWN"); obligations.append(f"{old.role}:VERIFY_OR_REPROVE_PARENT")
        elif t.transition_class is TransitionClass.EXACT_UNCHANGED:
            if t.new_snapshot.snapshot_root==old.snapshot_root and not t.changed_fields: states.append("EXACT")
            else: states.append("UNKNOWN"); obligations.append(f"{old.role}:INVALID_EXACT_TRANSITION")
        elif t.transition_class is TransitionClass.PROOF_NEUTRAL_REBIND:
            if old.consequence_root==t.new_snapshot.consequence_root and set(t.changed_fields)<=NEUTRAL_FIELDS and all(getattr(old,f)==getattr(t.new_snapshot,f) for f in CONSEQUENCE_BINDINGS): states.append("NEUTRAL")
            else: states.append("REPROVE"); obligations.append(f"{old.role}:REPROVE_PARENT")
        else:
            states.append("REPROVE"); obligations.append(f"{old.role}:REPROVE_PARENT")
        new.append(t.new_snapshot)
    aa,bb=sorted(new,key=lambda s:s.role); drift=[f for f in CONSEQUENCE_BINDINGS if getattr(aa,f)!=getattr(bb,f)]
    if drift: obligations.append("CROSS_BINDINGS:READJUDICATE:"+",".join(drift))
    if "UNKNOWN" in states:
        decision=Decision.HOLD_UNKNOWN
    elif "REPROVE" in states or drift:
        decision=Decision.REPROVE_MINIMUM_CONE
    elif "NEUTRAL" in states:
        decision=Decision.REBIND_AND_READJUDICATE
    else:
        decision=Decision.REUSE_EXACT
    return decision

def random_transition(rng, old):
    mode=rng.randrange(8); new=old; cls=TransitionClass.EXACT_UNCHANGED; fields=(); owner=True
    if mode==1:
        new=replace(old,generation=old.generation+"n",receipt_root=digest({"r":rng.randrange(10**9),"role":old.role})); cls=TransitionClass.PROOF_NEUTRAL_REBIND; fields=("generation","receipt_root")
    elif mode==2:
        new=replace(old,generation=old.generation+"c",receipt_root=digest({"r":rng.randrange(10**9)}),consequence_root=digest({"c":rng.randrange(10**9)})); cls=TransitionClass.CONSEQUENCE_CHANGED; fields=("generation","receipt_root")
    elif mode==3:
        new=replace(old,generation=old.generation+"s",receipt_root=digest({"r":rng.randrange(10**9)}),consequence_root=digest({"c":rng.randrange(10**9)}),source_identity=old.source_identity+"x"); cls=TransitionClass.CONSEQUENCE_CHANGED; fields=("source_identity",)
    elif mode==4:
        new=replace(old,generation=old.generation+"u",verified=False); cls=TransitionClass.UNKNOWN; owner=False
    elif mode==5:
        new=replace(old,generation=old.generation+"b",receipt_root=digest({"r":rng.randrange(10**9)}),benchmark_generation=old.benchmark_generation+"2",consequence_root=digest({"c":rng.randrange(10**9)})); cls=TransitionClass.CONSEQUENCE_CHANGED; fields=("benchmark_generation",)
    elif mode==6:
        new=replace(old,generation=old.generation+"e",receipt_root=digest({"r":rng.randrange(10**9)}),envelope_id=old.envelope_id+"2",consequence_root=digest({"c":rng.randrange(10**9)})); cls=TransitionClass.CONSEQUENCE_CHANGED; fields=("envelope_id",)
    elif mode==7:
        new=replace(old,generation=old.generation+"x",receipt_root=digest({"r":rng.randrange(10**9)})); cls=TransitionClass.PROOF_NEUTRAL_REBIND; fields=("semantic_policy",)
    root=digest({"owner":old.producer,"mode":mode,"nonce":rng.randrange(10**9)})
    return TransitionAttestation(old.role,old.snapshot_root,new,cls,tuple(fields),root,root if owner else digest({"bad":root}),owner)

def main():
    rng=random.Random(20260905); prior=demo_prior(); mismatches=0; cases=100000; h=hashlib.sha256()
    for i in range(cases):
        ta=random_transition(rng,prior.parent_a); tb=random_transition(rng,prior.parent_b)
        got=compile_reproof(prior,[ta,tb]).decision; want=oracle(prior,ta,tb)
        mismatches += got!=want
        h.update(f"{i}|{got.value}|{want.value}|{ta.attestation_root}|{tb.attestation_root}\n".encode())
    omega=list(itertools.product(range(3),repeat=8)); admitted=sum(crystalline_admission(x) for x in omega)
    bad=(0,2,2,2,2,2,2,1); tails=list(itertools.product(range(3),repeat=5)); repairs=sum(admission_13d(bad,t) for t in tails)
    # HS1000: 10 mutation families against a valid exact handoff; every mutated case must lose exact reuse.
    false=0
    for i in range(1000):
        old=prior.parent_a; mode=i%10; t=exact_transition(old)
        if mode==0: t=replace(t,old_snapshot_root=digest({"wrong":i}))
        elif mode==1: t=replace(t,owner_verified=False)
        elif mode==2: t=replace(t,expected_owner_transition_root=digest({"wrong":i}))
        elif mode==3: t=replace(t,transition_class=TransitionClass.UNKNOWN)
        elif mode==4: t=replace(t,new_snapshot=replace(old,verified=False),transition_class=TransitionClass.UNKNOWN)
        elif mode==5: t=replace(t,new_snapshot=replace(old,current=False),transition_class=TransitionClass.UNKNOWN)
        elif mode==6: t=replace(t,new_snapshot=replace(old,d0=False),transition_class=TransitionClass.UNKNOWN)
        elif mode==7: t=replace(t,new_snapshot=replace(old,generation="drift"),transition_class=TransitionClass.EXACT_UNCHANGED)
        elif mode==8: t=replace(t,new_snapshot=replace(old,generation="drift",receipt_root=digest({"r":i})),transition_class=TransitionClass.PROOF_NEUTRAL_REBIND,changed_fields=("semantic_policy",))
        else: t=replace(t,new_snapshot=replace(old,source_identity="other",consequence_root=digest({"c":i})),transition_class=TransitionClass.CONSEQUENCE_CHANGED,changed_fields=("source_identity",))
        try: decision=compile_reproof(prior,[t,exact_transition(prior.parent_b)]).decision
        except ReproofError: decision=Decision.HOLD_UNKNOWN
        false += decision is Decision.REUSE_EXACT
    live_a=replace(prior.parent_a,generation=O4_PARENT_A_NEW,receipt_root=digest({"live":"a"}),consequence_root=digest({"review":"invalid"}),verified=False)
    live_b=replace(prior.parent_b,generation=O4_PARENT_B_NEW,receipt_root=digest({"live":"b"}),consequence_root=digest({"arith":"exact-rational"}))
    ra=digest({"owner":"AGENT_06","live":1}); rb=digest({"owner":"AGENT_05","live":1})
    ta=TransitionAttestation(live_a.role,prior.parent_a.snapshot_root,live_a,TransitionClass.UNKNOWN,("generation","receipt_root"),ra,digest({"unverified":ra}),False)
    tb=TransitionAttestation(live_b.role,prior.parent_b.snapshot_root,live_b,TransitionClass.CONSEQUENCE_CHANGED,("generation","receipt_root"),rb,rb,True)
    live=compile_reproof(prior,[ta,tb])
    out={"schema":SCHEMA,"oracle_cases":cases,"oracle_mismatches":mismatches,"oracle_root":h.hexdigest(),"omega8_states":len(omega),"omega8_admit":admitted,"tail13d":len(tails),"hard_invalid_repairs":repairs,"hs1000":1000,"hs1000_false_exact_reuse":false,"live_o4_decision":live.decision.value,"live_o4_obligations":live.obligations,"live_o4_receipt_root":live.receipt_root}
    stable=json.dumps(out,sort_keys=True,separators=(",",":")); out["campaign_root"]=hashlib.sha256(stable.encode()).hexdigest(); print(json.dumps(out,sort_keys=True))
    if mismatches or admitted!=1 or repairs or false: raise SystemExit(1)
if __name__=="__main__": main()
