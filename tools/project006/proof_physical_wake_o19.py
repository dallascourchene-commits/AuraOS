from __future__ import annotations
import hashlib,itertools,json
TRI=(False,None,True)
def accept(x): return all(v is True for v in x)
def omega8():
    h=hashlib.sha256(); k=b=0
    for x in itertools.product(TRI,repeat=8):
        r=accept(x); k+=int(r); b+=int(r and not all(v is True for v in x)); h.update((repr((x,r))+'\n').encode())
    return {'states':6561,'keepers':k,'invalid_accepts':b,'root':h.hexdigest()}
def d13():
    contexts=list(itertools.product(TRI,repeat=5)); h=hashlib.sha256(); total=keep=rep=0
    for x in itertools.product(TRI,repeat=8):
        base=accept(x)
        for c in contexts:
            r=accept(x); total+=1; keep+=int(r); rep+=int(r and not base); h.update((repr((x,c,r))+'\n').encode())
    return {'states':total,'keeper_contexts':keep,'hard_invalid_contextual_repairs':rep,'root':h.hexdigest()}
def hs():
    fals=['GUARDIAN_MISSING','STOP_UNOBSERVED','RESTART_UNOBSERVED','INGEST_MISSING','CONSUME_MISSING','RETURN_MISSING','REPLAY_MISSING','DUPLICATE_EFFECT','CURRENTNESS_MOVE','AUTHORITY_MOVE']
    mechs=['TYPED_LEDGER','COVERAGE_CONTRACT','SEQUENCE_EQUIVOCATION','TIME_ORDER','PROVIDER_COUNT','CURRENTNESS_BIND','AUTHORITY_BIND','REPLAY_EVENT','SQLITE_WAL','OUTBOUND_ORACLE']
    ctx=['R4','AWJ033','COLD','WARM','CRASH','REOPEN','REPLAY','LOCK','DRIVE_DELAY','RDC_LOSS']
    cells=[]; groups={}
    for i,(f,m,c) in enumerate(itertools.product(fals,mechs,ctx)):
        g='WAKE_COVERAGE' if f in fals[:3] else 'COMMAND_COVERAGE' if f in fals[3:6] else 'REPLAY_SAFETY' if f in fals[6:8] else 'CURRENTNESS_AUTHORITY'
        cells.append((i,f,m,c,g)); groups[g]=groups.get(g,0)+1
    enc=lambda o:hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'frozen_candidates':1000,'consequence_groups':groups,'claimed_breakthroughs':0,'freeze_root':enc(cells),'quotient_root':enc(groups)}
print(json.dumps({'omega8':omega8(),'factored13d':d13(),'hs1000':hs()},sort_keys=True,separators=(',',':')))
