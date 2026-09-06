from auth_cutset import *
import hashlib,itertools,json,random
SEED=20260905

def oracle_cover(need,bundles):
    need=set(need)
    if not need:return ()
    norm=[b.normalized() for b in bundles]
    wins=[]
    for mask in range(1,1<<len(norm)):
        ids=[]; cov=set()
        for i,b in enumerate(norm):
            if mask>>i&1: ids.append(b.bundle_id); cov.update(b.covers)
        if need<=cov: wins.append((len(ids),tuple(sorted(ids))))
    if not wins: raise RuntimeError
    return min(wins)[1]

def run(n=20000):
    rng=random.Random(SEED); bundles=bundle_catalog(); h=hashlib.sha256(); mismatch=0; false=0
    counts={}; allstates=list(ProviderState)
    oracle_map={}
    for r in range(5):
        for combo in itertools.combinations(SUBJECTS,r): oracle_map[tuple(sorted(combo))]=oracle_cover(combo,bundles)
    for i in range(n):
        states={s:rng.choice(allstates) for s in SUBJECTS}
        auth=make_auth(states); p=compile_plan(default_parents(),auth,bundles)
        missing=tuple(sorted(s for s in SUBJECTS if states[s] is not ProviderState.ATTESTED))
        want=Decision.ELIGIBLE_FOR_FRESH_READJUDICATION if not missing else Decision.HOLD_AUTHENTICATION_CUTSET
        mismatch += p.decision is not want
        if missing: mismatch += p.minimum_bundle_ids != oracle_map[missing]
        false += bool(missing) and p.decision is Decision.ELIGIBLE_FOR_FRESH_READJUDICATION
        counts[p.decision.value]=counts.get(p.decision.value,0)+1
        h.update(f'{i}|{p.receipt_root}|{p.decision.value}|{",".join(p.minimum_bundle_ids)}\n'.encode())
    # HS1000: break one of five hard surfaces from a fully attested control.
    hsfalse=0
    full={s:ProviderState.ATTESTED for s in SUBJECTS}
    for i in range(1000):
        k=i%5; parents=list(default_parents()); states=dict(full); auth=make_auth(states)
        if k==0: parents[0]=ParentReplay(parents[0].owner,'0'*40,parents[0].expected_generation,parents[0].projection_root,parents[0].expected_projection_root)
        elif k==1: parents[1]=ParentReplay(parents[1].owner,parents[1].generation,parents[1].expected_generation,'0'*64,parents[1].expected_projection_root,parents[1].graph_root,parents[1].expected_graph_root)
        elif k==2: auth['AIRLLM_SECURITY_PARENT']=SubjectAuth('AIRLLM_SECURITY_PARENT',ProviderState.OBSERVED,auth['AIRLLM_SECURITY_PARENT'].evidence_root,'OBS_GEN_2')
        elif k==3: parents[1]=ParentReplay(parents[1].owner,parents[1].generation,parents[1].expected_generation,parents[1].projection_root,parents[1].expected_projection_root,parents[1].graph_root,'0'*64)
        else: parents[0]=ParentReplay(parents[0].owner,parents[0].generation,parents[0].expected_generation,parents[0].projection_root,parents[0].expected_projection_root,source_bound=False)
        p=compile_plan(tuple(parents),auth,bundles)
        hsfalse += p.decision is Decision.ELIGIBLE_FOR_FRESH_READJUDICATION
    # Omega8 ternary geometry: exactly the all-2 hard core can be eligible.
    omega_keep=0
    for axes in itertools.product(range(3),repeat=8):
        omega_keep += all(x==2 for x in axes)
    # 13D trailing five axes cannot repair a hard-invalid core.
    tail_repairs=0
    bad=list(default_parents()); bad[0]=ParentReplay(bad[0].owner,bad[0].generation,bad[0].expected_generation,bad[0].projection_root,bad[0].expected_projection_root,source_bound=False)
    auth=make_auth({s:ProviderState.ATTESTED for s in SUBJECTS})
    base=compile_plan(tuple(bad),auth,bundles)
    for tail in itertools.product(range(3),repeat=5):
        # Tail is receipt/routing context only; core decision must remain local reproof.
        tail_repairs += base.decision is Decision.ELIGIBLE_FOR_FRESH_READJUDICATION
        h.update(('T|'+''.join(map(str,tail))+'|'+base.receipt_root+'\n').encode())
    out={'schema':SCHEMA+'-CAMPAIGN','oracle_cases':n,'oracle_mismatches':mismatch,'false_auth_admissions':false,
         'hs1000_false_admissions':hsfalse,'omega8_states':3**8,'omega8_keepers':omega_keep,
         'tail13d_states':3**5,'tail13d_hard_invalid_repairs':tail_repairs,'decision_counts':counts,
         'campaign_root':h.hexdigest(),'authority':AUTHORITY}
    return out

if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
