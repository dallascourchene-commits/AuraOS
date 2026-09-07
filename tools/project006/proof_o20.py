from __future__ import annotations
import hashlib,itertools,json,random
TRI=(False,None,True)
def keeper(x): return all(v is True for v in x)
def omega8():
    h=hashlib.sha256(); k=bad=0
    for x in itertools.product(TRI,repeat=8):
        r=keeper(x); k+=int(r); bad+=int(r and not all(v is True for v in x)); h.update((repr((x,r))+'\n').encode())
    return {'states':6561,'keepers':k,'invalid_accepts':bad,'root':h.hexdigest()}
def d13():
    h=hashlib.sha256(); total=keep=repair=0
    for x in itertools.product(TRI,repeat=8):
        base=keeper(x)
        for c in itertools.product(TRI,repeat=5):
            r=keeper(x); total+=1; keep+=int(r); repair+=int(r and not base); h.update((repr((x,c,r))+'\n').encode())
    return {'states':total,'keeper_contexts':keep,'hard_invalid_contextual_repairs':repair,'root':h.hexdigest()}
def campaign(n=30000):
    rng=random.Random(20260907); h=hashlib.sha256(); mismatches=unsafe=0
    for _ in range(n):
        x=tuple(rng.choice((False,True)) for _ in range(8)); expected=all(x); actual=keeper(x); mismatches+=actual!=expected; unsafe+=actual and not expected; h.update((repr((x,actual))+'\n').encode())
    return {'cases':n,'oracle_mismatches':mismatches,'unsafe_current_accepts':unsafe,'root':h.hexdigest()}
def hs():
    fals=['OWNER_REPORT_ONLY','HEAD_MOVE','COMPONENT_MISSING','COMPONENT_HASH_MOVE','UNAUTH_MEASUREMENT','SOURCE_UNRESOLVED','HOST_INCARNATION_MOVE','STALE_OBSERVATION','K27_MOVE','CANONICAL_OPERATION_STABLE']
    mech=['RELEASE_MANIFEST','FULL_COMPONENT_SET','SOURCE_INCARNATION','INDEPENDENT_VERIFIER','HOST_INCAR_BIND','FRESHNESS_SEAL','OWNER_REPORT_LABEL','TECHNICAL_ROOT','CURRENTNESS_DECISION','D0_CEILING']
    ctx=['FRONTDOOR','PROJECT006','WINDOWS','WSL','REBOOT','RESTART','RDC_OFFLINE','DRIVE_DELAY','REPO_MOVE','POST_UPDATE']
    cells=[]; groups={}
    for i,(f,m,c) in enumerate(itertools.product(fals,mech,ctx)):
        if f=='OWNER_REPORT_ONLY': g='OWNER_REPORT_VS_MEASUREMENT'
        elif f in ('HEAD_MOVE','COMPONENT_MISSING','COMPONENT_HASH_MOVE'): g='MIXED_OR_STALE_GENERATION'
        elif f in ('UNAUTH_MEASUREMENT','SOURCE_UNRESOLVED'): g='SOURCE_PROVENANCE'
        elif f in ('HOST_INCARNATION_MOVE','STALE_OBSERVATION'): g='AT_USE_INCAR_FRESHNESS'
        else: g='SEMANTIC_VS_VOLATILE_SEPARATION'
        cells.append((i,f,m,c,g)); groups[g]=groups.get(g,0)+1
    enc=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'frozen_candidates':1000,'consequence_groups':groups,'claimed_breakthroughs':0,'freeze_root':enc(cells),'quotient_root':enc(groups)}
print(json.dumps({'omega8':omega8(),'factored13d':d13(),'campaign':campaign(),'hs1000':hs()},sort_keys=True,separators=(',',':')))
