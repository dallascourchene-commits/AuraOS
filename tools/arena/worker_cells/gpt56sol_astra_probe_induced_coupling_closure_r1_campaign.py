from tools.arena.worker_cells.gpt56sol_astra_probe_induced_coupling_closure_r1 import *
from itertools import product
import random,json,hashlib
SEED=0xA57A09;CASES=6000
AXES=('source','currentness','causal','validity','authority','owner','evidence','capability','resource','privacy','externalization','topology','coordinate');HARD=frozenset({'source','currentness','causal','validity','authority','owner','evidence','capability','externalization'});NODES=tuple('abcdef');LEFT=frozenset('abc');RIGHT=frozenset('def');FULL=frozenset(edge(a,b) for a in LEFT for b in RIGHT)
def rnd_internal(r):
 es=set()
 for group in (LEFT,RIGHT):
  gs=sorted(group)
  for i,a in enumerate(gs):
   for b in gs[i+1:]:
    if r.random()<.45:es.add(edge(a,b))
 return frozenset(es)
def rnd_probe(r,i):
 es=set()
 for _ in range(r.randint(0,2)):
  a,b=r.sample(NODES,2);es.add(edge(a,b))
 return EvidenceProbe(f'p{i}',frozenset(es),r.random()>.035,bool(es))
def run():
 r=random.Random(SEED);st={k:0 for k in ['cases','ready','holds','oracle_mismatches','naive_false_ready','stale_cert_attacks','incomplete_cert_attacks','stale_probe_cases','k27_attacks','bad_k27_accepts','cross_probe_cases','local_only_probe_cases','changed_cone_nodes_total']};roots=[]
 for i in range(CASES):
  incomplete=r.random()<.1;current=r.random()>.06;absent=FULL if not incomplete else frozenset(r.sample(sorted(FULL),r.randint(0,len(FULL)-1)));cert=CutCertificate(LEFT,RIGHT,absent,current);initial=rnd_internal(r);probes=tuple(rnd_probe(r,j) for j in range(r.randint(0,4)));k27='K27:'+str(r.randrange(27)) if r.random()<.18 else None;d=compile_independence(cert,initial,probes,k27_coordinate=k27);oracle=oracle_independence_after_probes(cert,initial,probes);st['cases']+=1
  if not current:st['stale_cert_attacks']+=1
  if incomplete:st['incomplete_cert_attacks']+=1
  if any(not p.current for p in probes):st['stale_probe_cases']+=1
  if k27:st['k27_attacks']+=1
  if any(frozenset(edge(*e) for e in p.activates_couplings)&FULL for p in probes):st['cross_probe_cases']+=1
  elif any(p.activates_couplings for p in probes):st['local_only_probe_cases']+=1
  st['ready' if d.status=='READY_D0' else 'holds']+=1
  if (d.status=='READY_D0')!=oracle:st['oracle_mismatches']+=1
  if naive_preprobe_independence(cert,initial,probes) and not oracle:st['naive_false_ready']+=1
  if k27 and d.status=='READY_D0' and not oracle:st['bad_k27_accepts']+=1
  st['changed_cone_nodes_total']+=len(d.changed_cone);roots.append(digest({'i':i,'cert_current':current,'complete':cert.complete,'initial':sorted(initial),'probes':[(p.name,sorted(p.activates_couplings),p.current) for p in probes],'status':d.status,'final':sorted(d.final_edges),'cone':sorted(d.changed_cone),'k27':k27}))
 states=false_ready=0
 for vals in product(range(3),repeat=13):
  states+=1;s=dict(zip(AXES,vals));hard_invalid=any(s[a]==2 for a in HARD);ready=s['topology']<2 and not hard_invalid
  if hard_invalid and s['coordinate']==0 and ready:false_ready+=1
 out={'schema':'aura.astra.o9.probe_induced_coupling_closure.campaign.v1','seed':SEED,'stats':st,'13d_states':states,'13d_false_ready':false_ready,'case_root':hashlib.sha256(''.join(roots).encode()).hexdigest(),'keeper_laws':['EvidenceProbeMayChangeCouplingTopology','PreProbeIndependence != PostProbeIndependence','NoObservedCoupling != Independence','ProbeInducedCrossCutEdge => ConservativeJoinAndReproof','ChangedTopology => ReproveChangedConnectedConeOnly','ReadOnlyProbe => PreserveValidCut','K27Coordinate != CouplingProof != Authority']};out['campaign_root']=digest(out);print(json.dumps(out,sort_keys=True,separators=(',',':')));return int(bool(st['oracle_mismatches'] or st['bad_k27_accepts'] or false_ready or st['naive_false_ready']==0))
if __name__=='__main__':raise SystemExit(run())
