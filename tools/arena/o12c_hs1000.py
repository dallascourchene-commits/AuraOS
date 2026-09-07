from hashlib import sha256
import json, random
AXES=('read_binding','component_reproof','coverage_admission','effect_mode','mutation_identity','fence_lease','owner_verifier','authority_separation')
def run(seed=12012026):
    rng=random.Random(seed); cells=[]
    for i in range(1000): cells.append({'i':i,'axes':tuple(rng.randrange(3) for _ in AXES)})
    freeze_root=sha256(json.dumps(cells,sort_keys=True,separators=(',',':')).encode()).hexdigest(); groups={}
    for c in cells:
        a=c['axes']; candidate='TECC_ROUTE' if all(x==2 for x in a) else ('HOLD_INVALID' if 0 in a else 'HOLD_UNRESOLVED'); legacy=all(a[i]==2 for i in (0,4,5,6)); key=(candidate,legacy,tuple(i for i,x in enumerate(a) if x!=2)); groups.setdefault(str(key),[]).append(c['i'])
    q=[{'signature':k,'count':len(v),'first_index':min(v)} for k,v in groups.items()]; q.sort(key=lambda x:(-x['count'],x['signature'])); quotient_root=sha256(json.dumps(q,sort_keys=True,separators=(',',':')).encode()).hexdigest(); top=q[:27]; top27_root=sha256(json.dumps(top,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'schema':'aura.o12c.hs1000.v1','raw_challenge_cells':1000,'freeze_root':freeze_root,'consequence_groups':len(q),'quotient_root':quotient_root,'top27_root':top27_root,'top27':top,'authority':'D0_NONPROMOTING_GATE10_FALSE','note':'1000 challenge/search cells; not 1000 breakthroughs'}
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
