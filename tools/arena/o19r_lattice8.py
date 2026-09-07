import itertools,json
from hashlib import sha256
AXES=("delegated_attempt_exact","attempt_current","commit_mode_valid","prestate_or_key_preconditions_exact","patch_identity_exact","conflict_free","durable_commit_receipt","authority_separation")
def h(x):return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    bind=invalid=0
    for s in itertools.product(range(3),repeat=8):
        oracle=all(x==2 for x in s); candidate=all(x==2 for x in s); bind+=int(candidate); invalid+=int(candidate and not oracle)
    out={"schema":"aura.o19r.omega8.v1","axes":AXES,"states":3**8,"bind":bind,"invalid_bind":invalid,"effect_ready":0}; out["root"]=h(out); return out
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
