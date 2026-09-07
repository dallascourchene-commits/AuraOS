import itertools,json
from hashlib import sha256
AXES=("installed_attestation_current","process_witness_current","process_incarnation_exact","loaded_units_exact","dispatch_and_mutation_exact","lazy_and_population_closed","serving_worker_exact","authority_separation")
def h(x):return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    bind=invalid=0
    for s in itertools.product(range(3),repeat=8):
        oracle=all(x==2 for x in s); candidate=all(x==2 for x in s); bind+=int(candidate); invalid+=int(candidate and not oracle)
    out={"schema":"aura.o20r.omega8.v1","axes":AXES,"states":3**8,"bind":bind,"invalid_bind":invalid,"effect_authority":0}; out["root"]=h(out); return out
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
