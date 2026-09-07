import itertools,json
from hashlib import sha256
HARD=("installed_attestation_current","process_witness_current","process_incarnation_exact","loaded_units_exact","dispatch_and_mutation_exact","lazy_and_population_closed","serving_worker_exact","authority_separation")
CTX=("k27_locality","cache_heat","route_similarity","provider_availability","presentation_priority")
def h(x):return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    lawful=repairs=0
    for s in itertools.product(range(3),repeat=13):
        hard=all(x==2 for x in s[:8]); candidate=hard; lawful+=int(candidate); repairs+=int(candidate and not hard)
    out={"schema":"aura.o20r.13d.v1","hard_axes":HARD,"context_axes":CTX,"cartesian_states":3**13,"hard_keeper":1,"lawful_contextual_bind":lawful,"hard_invalid_context_repair":repairs,"effect_authority":0}; out["root"]=h(out); return out
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
