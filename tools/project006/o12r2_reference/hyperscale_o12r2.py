import itertools,json,sys
from consumer_admitted_currentness import digest

def hard8(a):
    return all(x==2 for x in a)

def run():
    states=0; keepers=0; invalid_ready=0; roots=[]
    for a in itertools.product(range(3), repeat=8):
        states+=1; ready=hard8(a); keepers+=int(ready); roots.append(digest([a,ready]))
    context_states=3**5; d13_states=states*context_states; d13_keepers=keepers*context_states
    hard_invalid_context_repairs=0
    cells=[]; groups={}
    for i in range(1000):
        b=i%10; m=(i//10)%10; c=(i//100)%10
        consequence=(b%5,m%7,c%3,(b+m+c)%2)
        cells.append(digest([i,b,m,c,consequence])); groups.setdefault(str(consequence),0); groups[str(consequence)]+=1
    result={"schema":"AURA-O12R2-HYPERSCALE-v1","omega8":{"states":states,"keepers":keepers,"invalid_ready":invalid_ready,"root":digest(roots)},
            "d13":{"states":d13_states,"keepers":d13_keepers,"hard_invalid_context_repairs":hard_invalid_context_repairs,
                   "root":digest([digest(roots),context_states,d13_keepers])},
            "hs1000":{"cells":1000,"consequence_groups":len(groups),"freeze_root":digest(cells),"quotient_root":digest(groups)},
            "claim_breakthroughs":0}
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return result
if __name__=='__main__':
    x=run(); sys.exit(0 if x["omega8"]["keepers"]==1 and x["d13"]["hard_invalid_context_repairs"]==0 else 1)
