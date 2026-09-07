import json
from effect_refinement_seal import digest
cells=[]
for a in range(10):
  for b in range(10):
    for c in range(10): cells.append({'a':a,'b':b,'c':c})
freeze=digest(cells); groups={}
for x in cells:
    cls=('valid' if x['a']==9 and x['b']==9 and x['c']==9 else ('intent' if x['a']<3 else 'obligation' if x['b']<3 else 'plan' if x['c']<3 else 'owner'))
    groups[cls]=groups.get(cls,0)+1
out={'raw_challenge_cells':1000,'claim_breakthroughs':0,'freeze_root':freeze,'consequence_groups':groups,'group_count':len(groups),'quotient_root':digest(groups)}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
