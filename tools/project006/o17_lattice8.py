from itertools import product
from hashlib import sha256
import json

D0="D0_NONPROMOTING"
HARD=(
    "drive_file_identity_exact",
    "drive_revision_identity_exact",
    "independent_export_root_exact",
    "transport_ack_result_pair_exact",
    "digest_preimage_contract_resolved",
    "downstream_admissions_authenticated",
    "workcell_current",
    "authority_separation",
)

def decide(axes):
    if len(axes)!=8 or any(type(x) is not int or x not in (0,1,2) for x in axes): return "HOLD_MALFORMED"
    if 0 in axes: return "HOLD_HARD_INVALID"
    if 1 in axes: return "HOLD_UNRESOLVED"
    return "BIND_OBSERVATION_D0"

def run():
    states=bind=invalid=0
    for axes in product(range(3),repeat=8):
        d=decide(axes); lawful=all(x==2 for x in axes); states+=1; bind+=int(d=="BIND_OBSERVATION_D0"); invalid+=int(d=="BIND_OBSERVATION_D0" and not lawful)
    out={"schema":"aura.project006.o17.omega8.v1","hard_axes":HARD,"states":states,"bind":bind,"invalid_bind":invalid,"effect_ready":0,"authority":D0}
    out["root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if states!=6561 or bind!=1 or invalid: raise AssertionError(out)
    return out
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,indent=2))
