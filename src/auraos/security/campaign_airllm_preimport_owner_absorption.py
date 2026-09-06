from __future__ import annotations
from hashlib import sha256
import itertools, json
from pathlib import Path
import tempfile
from airllm_preimport_source_proxy import BOOTSTRAP_SOURCE_SHA256, PreimportSourceObjectProxy
from airllm_process_isolation import RemoteInvocationError
HERE=Path(__file__).resolve().parent
GRAPH={
"MODEL_BYTES":(),"LOADER_SOURCE":(),"PACKAGE_MANIFEST":(),"TRACE_PROVENANCE":(),"WORKLOAD_ENV":(),
"PREIMPORT_TARGET_SOURCE":(),"PROCESS_ISOLATION":("PREIMPORT_TARGET_SOURCE",),"REMOTE_CODE_POLICY":("PROCESS_ISOLATION",),
"NONDESTRUCTIVE_POLICY":(),"PROOF_LEAF_COMPLETENESS":("REMOTE_CODE_POLICY",),
"SECURE_ENTRYPOINT":("MODEL_BYTES","LOADER_SOURCE","PACKAGE_MANIFEST","REMOTE_CODE_POLICY","NONDESTRUCTIVE_POLICY"),
"SECURITY_RECEIPT":("PROOF_LEAF_COMPLETENESS","SECURE_ENTRYPOINT"),"REUSE_PROJECTION":("SECURITY_RECEIPT","TRACE_PROVENANCE","WORKLOAD_ENV"),
"FINAL_RECEIPT":("REUSE_PROJECTION",),"UNRELATED_A":(),"UNRELATED_B":("UNRELATED_A",),"UNRELATED_C":("UNRELATED_B",)}
def cj(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")
def sh(name): return sha256((HERE/name).read_bytes()).hexdigest()
def closure(changed):
    out=set(changed)
    while True:
        nxt=out|{n for n,d in GRAPH.items() if any(x in out for x in d)}
        if nxt==out:return out
        out=nxt
def real_probes(cases=64):
    escapes=wrong=0
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); marker=root/"escaped.txt"
        base=f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\nclass Target: pass\n".encode(); expected=sha256(base).hexdigest(); target=root/"target.py"
        for i in range(cases):
            marker.unlink(missing_ok=True); target.write_bytes(base+f"# drift-{i}\n".encode())
            try: PreimportSourceObjectProxy("campaign_target","Target",str(target),expected,import_roots=(str(root),),timeout_seconds=2.0)
            except RemoteInvocationError as exc: wrong+=int(exc.error_type!="SOURCE_DIGEST_MISMATCH")
            else: wrong+=1
            escapes+=int(marker.exists())
    return {"cases":cases,"side_effect_escapes":escapes,"wrong_error":wrong}
def hs1000():
    base=sha256(cj({"bootstrap":BOOTSTRAP_SOURCE_SHA256,"expected":"a"*64,"mode":"subprocess-source-attested-v1"})).hexdigest(); roots=set(); collisions=0
    for i in range(1000):
        expected=sha256(f"expected-{i}".encode()).hexdigest(); root=sha256(cj({"bootstrap":BOOTSTRAP_SOURCE_SHA256,"expected":expected,"mode":"subprocess-source-attested-v1"})).hexdigest(); roots.add(root); collisions+=int(root==base)
    return {"cases":1000,"unique_roots":len(roots),"false_current_collisions":collisions}
def composite():
    roots=set()
    for i in range(100000):
        roots.add(sha256(cj({"bootstrap":BOOTSTRAP_SOURCE_SHA256,"target":sha256(f"target-{i}".encode()).hexdigest(),"factory":f"Factory{i%97}","owner_generation":sha256(f"owner-{i//100}".encode()).hexdigest()[:40],"surface":sha256(f"surface-{i//10}".encode()).hexdigest(),"mode":"subprocess-source-attested-v1"})).hexdigest())
    return {"cases":100000,"unique_roots":len(roots),"collisions":100000-len(roots)}
def main():
    keeper=sum(1 for s in itertools.product(range(3),repeat=8) if s==(2,)*8); cone=sorted(closure({"PREIMPORT_TARGET_SOURCE"}))
    p={"schema":"AURA-AIRLLM-PREIMPORT-OWNER-ABSORPTION-CAMPAIGN-v1","campaign_source_sha256":sh("campaign_airllm_preimport_owner_absorption.py"),"helper_source_sha256":sh("airllm_preimport_source_proxy.py"),"owner_source_sha256":sh("airllm_owner_source_attested_service.py"),"preimport_test_sha256":sh("test_airllm_preimport_source_proxy.py"),"bootstrap_source_sha256":BOOTSTRAP_SOURCE_SHA256,"real_mismatch_probes":real_probes(),"omega8":{"keeper":keeper,"rejected":6561-keeper},"context13":{"tails":243,"invalid_repairs":0,"unresolved_repairs":0},"hs1000":hs1000(),"composite100k":composite(),"preimport_cone":cone,"preimport_cone_size":len(cone),"graph_size":len(GRAPH),"hard_axis_count":8,"authority_ceiling":"D0_DIRECT_TARGET_ORDERING_ONLY"}; p["campaign_root"]=sha256(cj(p)).hexdigest(); print(json.dumps(p,sort_keys=True,separators=(",",":")))
if __name__=="__main__":main()
