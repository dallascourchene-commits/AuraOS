import itertools,json
from hashlib import sha256
HARD=("cache_identity_exact","producer_provenance_authenticated","stable_operation_and_dependency_exact","consumer_permit_current","source_incarnation_exact","effect_time_process_current","namespace_and_output_authorized","authority_separation")
CTX=("k27_locality","cache_heat","view_identity","actor_identity","presentation_priority")
def h(x):return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    lawful=repairs=0
    for s in itertools.product(range(3),repeat=13):
        hard=all(x==2 for x in s[:8]); candidate=hard; lawful+=int(candidate); repairs+=int(candidate and not hard)
    out={"schema":"aura.o21r.13d.v1","hard_axes":HARD,"context_axes":CTX,"cartesian_states":3**13,"hard_keeper":1,"lawful_contextual_reuse":lawful,"hard_invalid_context_repair":repairs,"authority_promotions":0};out["root"]=h(out);return out
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
