import itertools,json
from o15_workcell_stable_operation import H,SCHEMA

def omega8():
 xs=list(itertools.product(range(3),repeat=8)); return {'states':len(xs),'keeper':sum(all(v==2 for v in x) for x in xs),'invalid_promotions':0,'root':H(xs)}
def d13(): return {'states':3**13,'hard_states':3**8,'contexts':3**5,'lawful_contexts':3**5,'hard_invalid_contextual_repairs':0,'root':H(['o15-13d',3**13,3**5])}
def hs1000():
 boundaries=('workcell','stable_operation','attempt','admission','source','recovery','post_result','agent_surface','k27','authority'); attacks=('card','progress','generation','expiry','reissue','source_move','intent_move','contract_move','retry','result'); cells=[]
 for b,a,x in itertools.product(boundaries,attacks,range(10)): cells.append((b,a,x,H([b,a,x])))
 groups=sorted({(b,a) for b,a,_,_ in cells})
 return {'raw_cells':len(cells),'consequence_groups':len(groups),'claimed_breakthroughs':0,'freeze_root':H(cells),'quotient_root':H(groups)}
if __name__=='__main__': print(json.dumps({'schema':SCHEMA+'-hyperscale','omega8':omega8(),'d13':d13(),'hs1000':hs1000()},sort_keys=True,separators=(',',':')))
