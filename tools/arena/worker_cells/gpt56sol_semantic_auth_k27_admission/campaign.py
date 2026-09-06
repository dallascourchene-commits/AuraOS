from dataclasses import replace
import itertools,json,random
import semantic_auth_k27_admission as m
H=lambda s:m.digest({'h':s});G='1'*40

def fixture():
 d,p,dep,sem,prov,local,auth=map(H,['domain','proj','dep','sem','prov','local','auth'])
 s=m.make_semantic_transition(decision=m.SemanticDecision.EXACT_CURRENT,semantic_domain_root=d,semantic_projection_root=p,dependency_root=dep)
 r=m.make_readjudication(decision=m.ReadjudicationDecision.ELIGIBLE_FOR_FRESH_READJUDICATION,local_surface_root=local,auth_surface_root=auth)
 b=m.make_cross_plane_binding(s,r);a=m.make_admission_set(binding_roots=[b.binding_root],external_receipt_root=H('external'))
 e=m.make_entry(subject_id='kv://demo',semantic_root=sem,semantic_domain_root=d,semantic_projection_root=p,provider_anchor_root=prov,dependency_root=dep,runtime_owner='runtime',runtime_generation=G,compatibility_profile='cp1',benchmark_generation=G,payload_hash=H('payload'),cache_handle='opaque://1')
 c=m.CurrentContext(e.subject_id,sem,d,p,prov,dep,'runtime',G,'cp1',G,H('payload'),local,auth)
 return [s,r,b,a,e,c,m.RoutingSignals(5,2,3,1,0)]

def oracle(f):
 s,r,b,a,e,c,_=f
 if not (m.verify_semantic(s) and m.verify_readjudication(r) and m.verify_cross_plane_binding(b) and m.verify_admission_set(a) and m.verify_entry(e)):return m.Decision.HOLD
 if s.owner_proof_root!=a.semantic_owner_proof_root or s.semantic_domain_root!=c.semantic_domain_root or e.semantic_domain_root!=c.semantic_domain_root or s.semantic_projection_root!=c.semantic_projection_root or e.semantic_projection_root!=c.semantic_projection_root or s.dependency_root!=c.dependency_root or e.dependency_root!=c.dependency_root:return m.Decision.REPROVE_SEMANTIC
 if r.owner_generation!=a.readjudication_owner_generation:return m.Decision.HOLD
 if b.binding_root not in a.accepted_binding_roots:return m.Decision.HOLD
 if (b.semantic_owner_proof_root,b.readjudication_owner_generation,b.semantic_receipt_root,b.readjudication_receipt_root,b.semantic_domain_root,b.semantic_projection_root,b.local_surface_root,b.auth_surface_root)!=(s.owner_proof_root,r.owner_generation,s.receipt_root,r.receipt_root,s.semantic_domain_root,s.semantic_projection_root,r.local_surface_root,r.auth_surface_root):return m.Decision.HOLD
 if r.local_surface_root!=c.expected_local_surface_root or r.auth_surface_root!=c.expected_auth_surface_root:return m.Decision.HOLD
 if (e.subject_id,e.semantic_root,e.provider_anchor_root,e.runtime_owner,e.runtime_generation,e.compatibility_profile,e.benchmark_generation,e.payload_hash)!=(c.subject_id,c.semantic_root,c.provider_anchor_root,c.runtime_owner,c.runtime_generation,c.compatibility_profile,c.benchmark_generation,c.payload_hash):return m.Decision.HOLD
 if s.decision is m.SemanticDecision.REPROVE_SECURITY or r.decision is m.ReadjudicationDecision.REPROVE_LOCAL_FIRST:return m.Decision.REPROVE_SEMANTIC
 if r.decision is m.ReadjudicationDecision.HOLD_AUTHENTICATION_CUTSET:return m.Decision.READJUDICATE_EXTERNAL_AUTH
 return m.Decision.ADMIT_RUNTIME_REUSE

def mutate(f,fam,i):
 if fam=='domain':f[5]=replace(f[5],semantic_domain_root=H('d'+str(i)))
 elif fam=='projection':f[5]=replace(f[5],semantic_projection_root=H('p'+str(i)))
 elif fam=='semantic_generation':f[3]=m.make_admission_set(binding_roots=[f[2].binding_root],external_receipt_root=H('x'),semantic_owner_proof_root=H('g'+str(i)))
 elif fam=='binding_admission':f[3]=m.make_admission_set(binding_roots=[H('b'+str(i))],external_receipt_root=H('x'))
 elif fam=='readj_generation':f[3]=m.make_admission_set(binding_roots=[f[2].binding_root],external_receipt_root=H('x'),readjudication_owner_generation='2'*40)
 elif fam=='mixmatch':f[1]=m.make_readjudication(decision=m.ReadjudicationDecision.ELIGIBLE_FOR_FRESH_READJUDICATION,local_surface_root=H('l'+str(i)),auth_surface_root=H('a'+str(i)))
 elif fam=='auth_decision':
  f[1]=m.make_readjudication(decision=m.ReadjudicationDecision.HOLD_AUTHENTICATION_CUTSET,local_surface_root=f[1].local_surface_root,auth_surface_root=f[1].auth_surface_root);f[2]=m.make_cross_plane_binding(f[0],f[1]);f[3]=m.make_admission_set(binding_roots=[f[2].binding_root],external_receipt_root=H('x'))
 elif fam=='runtime_generation':f[5]=replace(f[5],runtime_generation='2'*40)
 elif fam=='benchmark':f[5]=replace(f[5],benchmark_generation='2'*40)
 elif fam=='payload':f[5]=replace(f[5],payload_hash=H('pay'+str(i)))
 return f

def run(n=100000,seed=20260905):
 rng=random.Random(seed);base=fixture();fams=['domain','projection','semantic_generation','binding_admission','readj_generation','mixmatch','auth_decision','runtime_generation','benchmark','payload','green'];mism=0;leaves=[]
 for i in range(n):
  f=mutate(list(base),rng.choice(fams),i);want=oracle(f);got=m.decide(*f).decision;mism+=want!=got;leaves.append(m.digest({'i':i,'w':want.value,'g':got.value}))
 false=0
 for fam in fams[:-1]:
  for j in range(100):false+=m.decide(*mutate(list(base),fam,j)).decision is m.Decision.ADMIT_RUNTIME_REUSE
 out={'oracle_cases':n,'oracle_mismatches':mism,'hs1000_false_admits':false,'omega8_keepers':sum(m.crystalline(x) for x in itertools.product(range(3),repeat=8)),'tails13d_repairs':sum(m.admission13((0,2,2,2,2,2,2,2)+t) for t in itertools.product(range(3),repeat=5)),'campaign_root':m.digest(leaves),'green_receipt_root':m.decide(*base).receipt_root,'cross_plane_binding_root':base[2].binding_root,'admission_surface_root':base[3].surface_root,'entry_root':base[4].entry_root}
 print(json.dumps(out,sort_keys=True));return out
if __name__=='__main__':run()
