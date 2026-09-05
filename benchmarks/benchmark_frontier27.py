import json,os,random,sys,time
ROOT=os.path.dirname(os.path.dirname(__file__));sys.path.insert(0,os.path.join(ROOT,'tools','arena'))
from frontier27_runtime import *
SEED=2701000

def routes(steps=3000,experts=96,k=4):
 r=random.Random(SEED);out=[];pred=[];hot=list(range(16))
 for _ in range(steps):
  x=r.sample(hot,k) if r.random()<.82 else r.sample(range(experts),k);out.append(x);pred.append([e if r.random()<.70 else r.randrange(experts) for e in x])
 return out,pred

def retrieval(n=10000,q=500):
 records={f'R{i:05d}':f'family_{i%100} mechanism_{i%27} currentness cache expert route evidence record_{i}' for i in range(n)};rng=random.Random(SEED+1);qs=[f'family_{rng.randrange(100)} mechanism_{rng.randrange(27)}' for _ in range(q)]
 t=time.perf_counter();before_exam=0
 for term in qs:
  w=set(tokens(term))
  for text in records.values():before_exam+=1;bool(w&set(tokens(text)))
 before_s=time.perf_counter()-t
 t=time.perf_counter();idx=HybridIndexBridge(10);cache=HotColdCache(records)
 for identity,text in records.items():
  h=sha256(identity.encode()).digest();idx.add(identity,text,(h[0]%27,h[1]%27,h[2]%27))
 build=time.perf_counter()-t;t=time.perf_counter();after_exam=0
 for term in qs:
  c=idx.candidates(term,24);after_exam+=len(c)
  ids=[x[0] for x in c]
  for i in ids:cache.get(i)
  RetrievalReceipt.build(term,ids,'g1')
 after_s=time.perf_counter()-t
 return {'before':{'wall_s':before_s,'examined':before_exam},'after':{'query_wall_s':after_s,'index_build_s':build,'amortized_wall_s':after_s+build,'examined':after_exam,'hot_hits':cache.hits,'hot_misses':cache.misses}}

def main():
 rs,ps=routes();size=8*1024*1024;tier=StorageTier('ssd',10_000*size,1.2e9,2.4)
 b=LegacyOffload(size,1.2e9,2.4).run(rs,ps);a=FrontierOffload(size,24,tier,.0025,.1).run(rs,ps)
 inv=CurrentnessInvalidator();nodes=20000
 for i in range(nodes):inv.bind(f'N{i}',[f'D{i%200}',f'D{(i*7)%200}'])
 affected=inv.invalidate(['D17']);ring=SnapshotRing(128)
 for i in range(10000):ring.append(i,{'i':i})
 ret=retrieval();audit=security_campaign(1000)
 red=lambda x,y:(x-y)/x
 out={'seed':SEED,'manifest':FRONTIER_27,'offload':{'before':b,'after':a},'retrieval':ret,'currentness':{'before':nodes,'after':len(affected)},'snapshots':{'before':10000,'after':len(ring)},'audit':audit}
 out['gains']={'offload_transfer_bytes_reduction':red(b['bytes'],a['bytes']),'offload_estimated_transfer_time_reduction':red(b['seconds'],a['seconds']),'offload_estimated_energy_reduction':red(b['energy_j'],a['energy_j']),'retrieval_candidate_reduction':red(ret['before']['examined'],ret['after']['examined']),'retrieval_query_wall_time_reduction':red(ret['before']['wall_s'],ret['after']['query_wall_s']),'retrieval_amortized_wall_time_reduction':red(ret['before']['wall_s'],ret['after']['amortized_wall_s']),'selective_reproof_reduction':red(nodes,len(affected)),'snapshot_retention_reduction':red(10000,len(ring)),'security_false_admission_reduction':audit['false_admission_reduction']}
 print(json.dumps(out,indent=2,sort_keys=True))
if __name__=='__main__':main()
