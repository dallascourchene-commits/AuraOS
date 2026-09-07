import dataclasses, json, random, sys
from consumer_admitted_currentness import *
from test_consumer_admitted_currentness import make,resolver,intent,contract,r

MODES=["valid","bad_mac","gen","current","verifier","proof","source","auth","command","intent","contract","expired","owner"]

def mutate(a, mode):
    if mode=="valid": return a
    if mode=="bad_mac": return dataclasses.replace(a,mac=r("bad"))
    changes={
        "gen":dict(consumer_generation=8),"current":dict(currentness_root=r("moved")),"verifier":dict(verifier_instance="other"),
        "proof":dict(proof_semantics_id="legacy"),"source":dict(source_root=r("other")),"auth":dict(authorization_root=r("other")),
        "command":dict(command_id="other"),"intent":dict(intent_root=r("other")),"contract":dict(contract_root=r("other")),
        "expired":dict(expires_at=999),"owner":dict(source_owner_id="other"),
    }[mode]
    try: return make(**changes)
    except Exception: return None

def structural_baseline(a):
    if a is None: return False
    return a.source_root==r("source") and a.authorization_root==r("auth") and a.proof_semantics_id==EXPECTED_REPROOF_SEMANTICS

def run(n=30000,seed=1202):
    rng=random.Random(seed); counts={m:0 for m in MODES}; mismatches=0; unsafe_baseline=0; unsafe_candidate=0; roots=[]
    for i in range(n):
        mode=MODES[rng.randrange(len(MODES))]; counts[mode]+=1; a=mutate(make(),mode)
        got=False if a is None else resolver(a)(intent(),contract()) is not None
        expected=mode=="valid"
        if got!=expected: mismatches+=1
        if structural_baseline(a) and not expected: unsafe_baseline+=1
        if got and not expected: unsafe_candidate+=1
        roots.append(digest([i,mode,got,expected]))
    result={"schema":"AURA-O12R2-CAMPAIGN-v1","cases":n,"counts":counts,"oracle_mismatches":mismatches,
            "structural_currentness_false_permits":unsafe_baseline,"unsafe_candidate_provider_permits":unsafe_candidate,
            "campaign_root":digest(roots)}
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return result
if __name__=='__main__':
    x=run(); sys.exit(0 if x["oracle_mismatches"]==x["unsafe_candidate_provider_permits"]==0 else 1)
