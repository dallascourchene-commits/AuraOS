from __future__ import annotations
from dataclasses import dataclass,asdict
from typing import List,Tuple
import hashlib,json
PRIMITIVES=('K27_RECURSION','MULTIPLEX_OVERLAY','SPATIAL_WFST','PHYSICAL_JURISDICTION','XR_ANCHOR','LOD_CULLING','VISUAL_SKIN','BREADBOARD','XR_INTERACTION','TENANCY_MULTIUSER')
CONCERNS=('COHERENCE','RETRIEVAL','CURRENTNESS','AUTHORITY','PRIVACY','PERFORMANCE','ACCESSIBILITY','RECOVERY','INTEROPERABILITY','COGNITION_USABILITY')
OPERATORS=('BLIND_ABLATION','MUTATION','FUZZ','USER_STUDY','HEADSET_BENCH','MOBILE_BENCH','CROSS_DEVICE_REPLAY','FAILURE_INJECTION','OWNER_CHALLENGE','INTEGRATION_TEST')
@dataclass(frozen=True)
class Ticket:
 id:str; primitive:str; concern:str; operator:str; k27:Tuple[int,int,int]; question:str


def k27_for(i,j,k): return (i*2%27,j*2%27,k*2%27)
def generate()->List[Ticket]:
 out=[]
 for i,p in enumerate(PRIMITIVES):
  for j,c in enumerate(CONCERNS):
   for k,o in enumerate(OPERATORS):
    key=f'{p}|{c}|{o}'; tid='MCXR-'+hashlib.sha256(key.encode()).hexdigest()[:10]
    out.append(Ticket(tid,p,c,o,k27_for(i,j,k),f'Can {p} survive {o} pressure on {c} without city labels becoming truth/authority?'))
 return out


def hot_frontier(tickets:List[Ticket],n=50)->List[Ticket]:
 # deterministic portfolio: round-robin across all three axes, one per primitive/operator pair before repeats
 scored=sorted(tickets,key=lambda t:hashlib.sha256((t.id+'|hot').encode()).hexdigest())
 out=[]; pc={}; cc={}; oc={}
 while scored and len(out)<n:
  best=min(scored,key=lambda t:(pc.get(t.primitive,0)+cc.get(t.concern,0)+oc.get(t.operator,0),pc.get(t.primitive,0),cc.get(t.concern,0),oc.get(t.operator,0),t.id))
  scored.remove(best);out.append(best);pc[best.primitive]=pc.get(best.primitive,0)+1;cc[best.concern]=cc.get(best.concern,0)+1;oc[best.operator]=oc.get(best.operator,0)+1
 return out


def receipt(tickets,hot):
 return {'schema':'MCXR-RESEARCH-v1','candidate_count':len(tickets),'hot_count':len(hot),'candidate_is_finding':False,'k27_is_authority':False,'hot_ids':[t.id for t in hot]}
if __name__=='__main__':
 t=generate();h=hot_frontier(t);print(json.dumps({'receipt':receipt(t,h),'hot':[asdict(x) for x in h]},indent=2))
