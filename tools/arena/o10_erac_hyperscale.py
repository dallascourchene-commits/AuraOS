from itertools import product
import json
from effect_return_atomicity import digest,hard13d_erac

def run():
    cells=[]; groups={}
    for a in range(10):
        for b in range(10):
            for c in range(10):
                hard_invalid=(a in (6,7,8,9) or b in (7,8,9))
                unresolved=(not hard_invalid and (a in (4,5) and b in (4,5)))
                consequence='HOLD_HARD_INVALID' if hard_invalid else ('HOLD_UNRESOLVED' if unresolved else ('RETURN_ONLY' if c<3 else ('RECONCILE_OR_RETRY' if c<7 else 'TERMINAL_NOOP')))
                cell={'a':a,'b':b,'c':c,'consequence':consequence}
                cells.append(cell); groups[consequence]=groups.get(consequence,0)+1
    freeze_root=digest(cells); quotient_root=digest(dict(sorted(groups.items())))

    omega_counts={'keeper':0,'invalid':0,'unresolved':0}
    for axes in product((0,1,2),repeat=8):
        if 0 in axes: omega_counts['invalid']+=1
        elif 1 in axes: omega_counts['unresolved']+=1
        else: omega_counts['keeper']+=1
    omega_root=digest(omega_counts)

    d13={'states':0,'ready':0,'hard_invalid':0,'unresolved':0,'hard_invalid_repaired':0,'unresolved_repaired':0}
    for axes in product((0,1,2),repeat=13):
        d13['states']+=1
        r=hard13d_erac(axes)
        if r=='READY_RECOVERY_ACTION_D0': d13['ready']+=1
        elif r=='HOLD_HARD_INVALID': d13['hard_invalid']+=1
        elif r=='HOLD_UNRESOLVED': d13['unresolved']+=1
        if 0 in axes[:8] and r=='READY_RECOVERY_ACTION_D0': d13['hard_invalid_repaired']+=1
        if 0 not in axes[:8] and 1 in axes[:8] and r=='READY_RECOVERY_ACTION_D0': d13['unresolved_repaired']+=1
    d13_root=digest(d13)
    out={'hs1000_cells':len(cells),'hs1000_groups':len(groups),'freeze_root':freeze_root,'quotient_root':quotient_root,
         'omega8':omega_counts,'omega8_root':omega_root,'d13':d13,'d13_root':d13_root}
    out['root']=digest(out)
    return out

if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(',',':')))
