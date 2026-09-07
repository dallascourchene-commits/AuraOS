from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dataclasses import replace
from hashlib import sha256
import json
from tools.project006.transport_source_identity_bridge import *

def r(x): return sha256(x.encode()).hexdigest()

def base():
    s=DriveSourceIncarnation("file","rev","text/plain",b"source")
    d=s.export_root
    a=TransportCallback("ACK","cmd","idem",r("attempt"),d,"ACK-v1","ACK_ACCEPTED",r("ab"),r("ao"))
    z=TransportCallback("RESULT","cmd","idem",r("attempt"),d,"RESULT-v1","TERMINAL_SUCCESS",r("rb"),r("ro"),r("result"),r("response"))
    c=AdmissionContext("cmd","idem",s.file_id,s.revision_id,s.incarnation_root,r("proof"),r("training"),r("workcell"),True,True,True)
    k=DigestPreimageContract("exact-v1","UTF8_EXACT")
    return s,a,z,c,k

def mutate(mode):
    s,a,z,c,k=base()
    if mode==1: z=replace(z,kind="ACK")
    elif mode==2: z=replace(z,attempt_id=r("other"))
    elif mode==3: z=replace(z,command_id="other")
    elif mode==4: z=replace(z,idempotency_key="other")
    elif mode==5: z=replace(z,source_envelope_digest=r("other"))
    elif mode==6: c=replace(c,command_id="other")
    elif mode==7: c=replace(c,idempotency_key="other")
    elif mode==8: s=replace(s,file_id="file2")
    elif mode==9: s=replace(s,revision_id="rev2")
    elif mode==10: s=replace(s,export_bytes=b"source2")
    elif mode==11: c=replace(c,expected_source_incarnation_root=r("other"))
    elif mode==12: c=replace(c,proof_authenticated=False)
    elif mode==13: c=replace(c,training_authenticated=False)
    elif mode==14: c=replace(c,workcell_current=False)
    elif mode==15: k=None
    elif mode==16: k=DigestPreimageContract("normalized-v1","UTF8_NO_BOM_LF")
    elif mode==17: a=replace(a,source_envelope_digest=r("claimed")); z=replace(z,source_envelope_digest=r("claimed"))
    elif mode==18: a=replace(a,kind="RESULT")
    elif mode==19: c=replace(c,source_file_id="other")
    elif mode==20: c=replace(c,source_revision_id="other")
    elif mode==21: a=replace(a,command_id="other"); z=replace(z,command_id="other")
    elif mode==22: a=replace(a,idempotency_key="other"); z=replace(z,idempotency_key="other")
    elif mode==23: pass
    return s,a,z,c,k

def oracle(mode):
    return mode in (0,16,23)

def run(cases=24000):
    out={"cases":cases,"oracle_bind":0,"oracle_nonbind":0,"false_bind":0,"false_hold":0,"naive_shared_digest_unsafe":0,"naive_shape_trust_unsafe":0,"effect_ready":0}
    for i in range(cases):
        mode=i%24; s,a,z,c,k=mutate(mode); expected=oracle(mode)
        d=validate_source_admission(source=s,ack=a,result=z,ctx=c,digest_contract=k)
        got=d.disposition is Disposition.BIND_OBSERVATION_D0
        out["oracle_bind" if expected else "oracle_nonbind"]+=1
        out["false_bind"]+=int(got and not expected); out["false_hold"]+=int(expected and not got)
        shared=(a.source_envelope_digest==z.source_envelope_digest and a.command_id==z.command_id and a.idempotency_key==z.idempotency_key)
        out["naive_shared_digest_unsafe"]+=int(shared and not expected)
        shape=(a.kind=="ACK" and z.kind=="RESULT" and bool(c.proof_bound_admission_root) and bool(c.training_admission_root))
        out["naive_shape_trust_unsafe"]+=int(shape and not expected)
        out["effect_ready"]+=int(d.effect_authority or d.training_authority or d.transport_digest_authority)
    body=json.dumps(out,sort_keys=True,separators=(",",":")); out["campaign_root"]=sha256(body.encode()).hexdigest(); out["schema"]="aura.project006.o17.transport_source.campaign.v1"; out["authority"]=D0
    if out["false_bind"] or out["false_hold"] or out["effect_ready"]: raise AssertionError(out)
    return out
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,indent=2))
