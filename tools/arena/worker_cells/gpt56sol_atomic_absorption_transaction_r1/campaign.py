from atomic_absorption import *
import random,itertools,json
H='1'*64; T='2'*64
rng=random.Random(85227)
def mk(i,mode):
    files={f'tools/w{i}.py':digest(('b',i))}; base=H; auth=False
    if mode==1: base='3'*64
    if mode==2: files={'.v5-stage-marker-'+str(i):digest(i)}
    if mode==3: auth=True
    return Proposal(f'P{i}',f'agent{i}',f'lin{i}',base,digest(('c',i)),digest(('r',i)),files,auth)

def run():
    counts={'cases':0,'bad_ready':0,'cas_lost':0,'conflict_escape':0,'debris_escape':0,'authority_escape':0,'consequence_divergence_escape':0}
    snap=OwnerSnapshot(H,T)
    for i in range(100000):
        mode=rng.randrange(6); a=mk(i,0)
        if mode==0: props=[a]
        elif mode==1: props=[a,mk(i+1,1)]
        elif mode==2: props=[a,mk(i+1,2)]
        elif mode==3: props=[a,mk(i+1,3)]
        elif mode==4:
            p='same'; props=[Proposal('A'+str(i),'aa','la',H,digest(('a',i)),digest(('ra',i)),{p:digest('x')}),Proposal('B'+str(i),'bb','lb',H,digest(('b',i)),digest(('rb',i)),{p:digest('y')})]
        else:
            c=digest(('same',i)); props=[Proposal('A'+str(i),'aa','la',H,c,digest(('ra',i)),{'a':digest('x')}),Proposal('B'+str(i),'bb','lb',H,c,digest(('rb',i)),{'b':digest('y')})]
        q=plan(snap,props); counts['cases']+=1
        if mode==0 and q.disposition!=Disposition.READY: counts['bad_ready']+=1
        if mode==1 and q.disposition!=Disposition.REBASE_REQUIRED: counts['cas_lost']+=1
        if mode==2 and q.disposition!=Disposition.DEBRIS_HOLD: counts['debris_escape']+=1
        if mode==3 and q.disposition!=Disposition.AUTHORITY_HOLD: counts['authority_escape']+=1
        if mode==4 and q.disposition!=Disposition.CONFLICT_HOLD: counts['conflict_escape']+=1
        if mode==5 and q.disposition!=Disposition.CONFLICT_HOLD: counts['consequence_divergence_escape']+=1
    hs_false=0
    for i in range(1000):
        q=plan(snap,[mk(i,0)]); r=commit(q,('4'*64 if i%2==0 else H))
        if i%2==0 and (r.committed or r.write_count): hs_false+=1
        if i%2==1 and not r.committed: hs_false+=1
    omega=sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8))
    repairs=sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
    out={**counts,'hs1000_false':hs_false,'omega8_keepers':omega,'13d_repairs':repairs}
    out['campaign_root']=digest(out)
    print(json.dumps(out,sort_keys=True))
    assert not any(out[k] for k in ('bad_ready','cas_lost','conflict_escape','debris_escape','authority_escape','consequence_divergence_escape','hs1000_false'))
    assert omega==1 and repairs==0
if __name__=='__main__': run()
