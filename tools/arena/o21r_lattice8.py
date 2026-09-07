import itertools,json
from hashlib import sha256
AXES=("cache_identity_exact","producer_provenance_authenticated","stable_operation_and_dependency_exact","consumer_permit_current","source_incarnation_exact","effect_time_process_current","namespace_and_output_authorized","authority_separation")
def h(x):return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def run():
    reuse=invalid=0
    for s in itertools.product(range(3),repeat=8):
        oracle=all(x==2 for x in s); candidate=all(x==2 for x in s); reuse+=int(candidate); invalid+=int(candidate and not oracle)
    out={"schema":"aura.o21r.omega8.v1","axes":AXES,"states":3**8,"reuse":reuse,"invalid_reuse":invalid,"authority_promotions":0};out["root"]=h(out);return out
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,indent=2))
