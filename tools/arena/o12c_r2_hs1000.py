from __future__ import annotations
import hashlib,json,sys
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_effect_handoff_o12c_r2 import *
from campaign_memory_city_effect_handoff_o12c_r2 import state,R

def main():
    cells=[]; groups={}
    mechanisms=['valid','schema','authority','consequence','holder','read_owner','intent','escalation','ref_owner','expiry']
    for boundary in range(10):
      for mech in mechanisms:
       for cls in range(10):
        tag=f'{boundary}:{mech}:{cls}';h,t,c,u,ro,a,r,e,m,v=state(tag)
        if mech=='schema':a=dict(a);a['schema']='OTHER';a.pop('receipt_root');a['receipt_root']=digest(a)
        elif mech=='authority':c=replace(c,effect_authority=True)
        elif mech=='consequence':c=replace(c,consequence_root=R(['forged',tag]))
        elif mech=='holder':v=replace(v,holder='other')
        elif mech=='read_owner':v=replace(v,read_owner_receipt_root=R(['moved',tag]))
        elif mech=='intent':v=replace(v,intent_binding_root=R(['moved-intent',tag]))
        elif mech=='escalation':v=replace(v,effect_escalation_root=R(['moved-esc',tag]))
        elif mech=='ref_owner':v=replace(v,refinement_owner_receipt_root=R(['moved-ref-owner',tag]))
        elif mech=='expiry':v=replace(v,now=100)
        d=compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v)
        rec={'boundary':boundary,'mechanism':mech,'class':cls,'disposition':d.disposition.value,'reason':d.reason}
        cells.append(rec); groups.setdefault((d.disposition.value,d.reason),0);groups[(d.disposition.value,d.reason)]+=1
    freeze=hashlib.sha256(json.dumps(cells,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    grouped=[{'disposition':k[0],'reason':k[1],'count':v} for k,v in sorted(groups.items())]
    quotient=hashlib.sha256(json.dumps(grouped,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    top27=hashlib.sha256(json.dumps(grouped[:27],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    out={'schema':'AURA-MEMORY-CITY-O12C-R2-HS1000-v1','cells':len(cells),'consequence_groups':len(grouped),'freeze_root':freeze,'quotient_root':quotient,'top27_root':top27,'groups':grouped}
    print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
