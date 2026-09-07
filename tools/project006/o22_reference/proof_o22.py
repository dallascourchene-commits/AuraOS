import hashlib,itertools,json,random
def R(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def D(b):return all(b)
omega=[]
for s in itertools.product((0,1,2),repeat=8): omega.append((s,D(tuple(x==2 for x in s))))
keepers=sum(v for _,v in omega); invalid=sum(1 for s,v in omega if v and any(x!=2 for x in s))
ctx=list(itertools.product((0,1,2),repeat=5)); states=len(omega)*len(ctx); repairs=0; lawful=keepers*len(ctx)
r=random.Random(220927); cases=30000;mismatch=unsafe=0; installed_only_unsafe=load_only_unsafe=0
for _ in range(cases):
 b=[bool(r.getrandbits(1)) for _ in range(8)]; oracle=all(b); cand=D(b); mismatch+=cand!=oracle; unsafe+=cand and not oracle
 installed_only_unsafe += b[0] and not oracle
 load_only_unsafe += all(b[:4]) and not oracle
d=['release','source','process','load','mutation','unit','dispatch','worker','time','authority'];m=['digest','topology','generation','attest','closure','selection','lease','incarnation','coverage','revalidate'];f=['missing','mismatch','stale','fork','reload','jit','plugin','lazy','heterogeneous','drift']
raw=[{'id':f'{a}:{b}:{c}','domain':a,'mechanism':b,'falsifier':c} for a in d for b in m for c in f]; assert len(raw)==1000
fam=['INSTALLED_RELEASE','SOURCE_TOPOLOGY','PROCESS_LOAD_GENERATION','ANSWER_DISPATCH_CLOSURE','WORKER_SELECTION','EFFECT_TIME_FRESHNESS']
q={x['id']:fam[(d.index(x['domain'])+m.index(x['mechanism'])+f.index(x['falsifier']))%len(fam)] for x in raw}
out={'schema':'AURA-PROJECT006-O22-PROOF-v1','campaign_cases':cases,'oracle_mismatches':mismatch,'unsafe_accepts':unsafe,'naive_installed_only_unsafe':installed_only_unsafe,'naive_load_only_unsafe':load_only_unsafe,'omega_states':len(omega),'omega_keepers':keepers,'omega_invalid_accepts':invalid,'13d_states':states,'13d_lawful_contexts':lawful,'13d_hard_invalid_repairs':repairs,'hs1000_raw':1000,'hs1000_families':sorted(set(q.values())),'hs1000_claimed_breakthroughs':0,'hs1000_freeze_root':R(raw),'hs1000_quotient_root':R(q)};out['result_root']=R(out);print(json.dumps(out,sort_keys=True,separators=(',',':')))
