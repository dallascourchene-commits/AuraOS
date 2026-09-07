from __future__ import annotations
import hashlib,itertools,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_effect_handoff_o12c_r2 import *
from o12c_r2_lattice_state import mutate

def main():
    M={'states':0,'oracle_tecc':0,'candidate_tecc':0,'false_tecc':0,'false_hold':0,'effect_ready':0}
    for hard in itertools.product(range(3), repeat=8):
        h,t,c,u,ro,a,r,e,m,v=mutate(hard,'l8')
        d=compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v)
        expected=all(x==2 for x in hard); got=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0
        M['states']+=1;M['oracle_tecc']+=expected;M['candidate_tecc']+=got;M['false_tecc']+=(got and not expected);M['false_hold']+=((not got) and expected);M['effect_ready']+=int(getattr(d.disposition,'value',d.disposition)=='READY_D0')
    assert M['states']==3**8 and M['false_tecc']==0 and M['false_hold']==0 and M['effect_ready']==0
    out={'schema':'AURA-MEMORY-CITY-O12C-R2-LATTICE8-v1','metrics':M};out['root']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest();print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
