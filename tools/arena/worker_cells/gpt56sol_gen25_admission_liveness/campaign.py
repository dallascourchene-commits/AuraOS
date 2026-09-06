from hashlib import sha256
import itertools, json, random
from liveness_witness import *

NOW=2_000_000
HEAD=Head("GEN25","d91e0a39358901c5")

def oracle(command, receipts):
    if command.generation != HEAD.generation or command.head_digest != HEAD.digest:
        return CommandState.STALE_HEAD
    bound=[r for r in receipts if r.command_id==command.command_id and r.observed_s>=command.created_s]
    if not bound: return CommandState.ADMISSION_STARVED
    if any(r.kind in {"RESULT","ERROR"} or r.state.startswith("TERMINAL_") for r in bound): return CommandState.TERMINAL
    if any("REJECT" in r.state or "BLOCK" in r.state for r in bound): return CommandState.TYPED_REJECTED
    if any(r.kind=="ACK" and r.state in {"ACK_ACCEPTED","ACK_ACCEPTED_PRE_EFFECT"} for r in bound): return CommandState.ADMITTED_NOT_TERMINAL
    return CommandState.UNKNOWN

def run():
    rng=random.Random(59025)
    mismatches=0
    roots=[]
    for i in range(100_000):
        cid=f"C{i}"
        created=1_000_000+rng.randrange(900_000)
        generation="GEN25" if rng.randrange(7) else "GEN24"
        c=Command(cid,created,generation,"d91e0a39358901c5" if rng.randrange(11) else "wrong","AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND",False)
        rs=[]
        mode=rng.randrange(7)
        if mode==1: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"ACK","ACK_ACCEPTED")]
        elif mode==2: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"RESULT","TERMINAL_SUCCESS")]
        elif mode==3: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"ACK","CURRENTNESS_REJECTED")]
        elif mode==4: rs=[Receipt("OTHER",NOW-1,"RESULT","TERMINAL_SUCCESS")]
        elif mode==5: rs=[Receipt(cid,max(0,created-1),"ACK","ACK_ACCEPTED")]
        elif mode==6: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"ACK","WEIRD")]
        got=classify_command(NOW,HEAD,c,rs).state
        exp=oracle(c,rs)
        mismatches += got!=exp
        roots.append(sha256(json.dumps([cid,got.value],separators=(",",":")).encode()).hexdigest())
    # HS1000: every cell has active ingress but no command-bound current receipt; unrelated historical bus success may exist.
    false_healthy=0
    hs=[]
    for i in range(1000):
        c=Command(f"AWJ-{i}",NOW-7200-i,"GEN25","d91e0a39358901c5","READY",False)
        unrelated=[Receipt("HISTORICAL",NOW-10,"RESULT","TERMINAL_SUCCESS")]
        p=compile_recovery(now_s=NOW,head=HEAD,commands=[c],receipts=unrelated,consumer=ConsumerObservation(False),starvation_after_s=3600,reducer_stall_after_s=3600)
        if p.system_state==SystemState.HEALTHY_PROGRESS or p.provider_fanout_allowed: false_healthy+=1
        hs.append(p.receipt_root)
    omega=sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8))
    repairs=sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
    out={
      "oracle_decisions":100_000,"oracle_mismatches":mismatches,
      "hs1000_false_healthy":false_healthy,"omega8_keepers":omega,"13d_repairs":repairs,
      "oracle_root":sha256("".join(roots).encode()).hexdigest(),
      "hs1000_root":sha256("".join(hs).encode()).hexdigest(),
    }
    out["campaign_root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    print(json.dumps(out,sort_keys=True))
    if mismatches or false_healthy or omega!=1 or repairs!=0: raise SystemExit(1)

if __name__=='__main__': run()
