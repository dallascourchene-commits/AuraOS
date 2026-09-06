from hashlib import sha256
import itertools, json, random
from liveness_witness import *
import liveness_witness as lw

NOW=2_000_000
HEAD=Head("GEN25","d91e0a39358901c5")

def oracle(command, receipts):
    q=lw._queue_class(command.queue_state)
    if q=="INACTIVE": return CommandState.INACTIVE_QUEUE
    if q=="UNKNOWN": return CommandState.UNKNOWN
    if command.generation != HEAD.generation or command.head_digest != HEAD.digest:
        return CommandState.STALE_HEAD
    matching=[r for r in receipts if r.command_id==command.command_id]
    for r in matching:
        if type(r.observed_s) is not int or r.observed_s < 0: raise E("BAD_RECEIPT_TIME")
        if r.observed_s > NOW: raise E("FUTURE_RECEIPT")
        if not isinstance(r.kind,str) or not r.kind: raise E("BAD_RECEIPT_KIND")
        if not isinstance(r.state,str) or not r.state: raise E("BAD_RECEIPT_STATE")
    bound=[r for r in matching if r.observed_s>=command.created_s]
    if not bound: return CommandState.ADMISSION_STARVED
    if any(r.kind in {"RESULT","ERROR"} or r.state.startswith("TERMINAL_") for r in bound): return CommandState.TERMINAL
    if any("REJECT" in r.state or "BLOCK" in r.state for r in bound): return CommandState.TYPED_REJECTED
    if any(r.kind=="ACK" and r.state in {"ACK_ACCEPTED","ACK_ACCEPTED_PRE_EFFECT"} for r in bound): return CommandState.ADMITTED_NOT_TERMINAL
    return CommandState.UNKNOWN

def run():
    rng=random.Random(59025)
    mismatches=0
    future_receipts_rejected=0
    roots=[]
    for i in range(100_000):
        cid=f"C{i}"
        created=1_000_000+rng.randrange(900_000)
        generation="GEN25" if rng.randrange(7) else "GEN24"
        q=("READY","CANCELLED","MYSTERY")[rng.randrange(3)] if rng.randrange(10)==0 else "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND"
        c=Command(cid,created,generation,"d91e0a39358901c5" if rng.randrange(11) else "wrong",q,False)
        rs=[]
        mode=rng.randrange(8)
        if mode==1: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"ACK","ACK_ACCEPTED")]
        elif mode==2: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"RESULT","TERMINAL_SUCCESS")]
        elif mode==3: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"ACK","CURRENTNESS_REJECTED")]
        elif mode==4: rs=[Receipt("OTHER",NOW-1,"RESULT","TERMINAL_SUCCESS")]
        elif mode==5: rs=[Receipt(cid,max(0,created-1),"ACK","ACK_ACCEPTED")]
        elif mode==6: rs=[Receipt(cid,created+rng.randrange(max(1,NOW-created)),"ACK","WEIRD")]
        elif mode==7 and q in ACTIVE_QUEUE_STATES and generation=="GEN25" and c.head_digest==HEAD.digest: rs=[Receipt(cid,NOW+1+rng.randrange(1000),"ACK","ACK_ACCEPTED")]
        try: got=classify_command(NOW,HEAD,c,rs).state
        except E as exc: got=f"E:{exc}"
        try: exp=oracle(c,rs)
        except E as exc: exp=f"E:{exc}"
        if exp=="E:FUTURE_RECEIPT" and got=="E:FUTURE_RECEIPT": future_receipts_rejected+=1
        mismatches += got!=exp
        roots.append(sha256(json.dumps([cid,str(got)],separators=(",",":")).encode()).hexdigest())
    false_healthy=0
    boundary_failures=0
    hs=[]
    inactive=tuple(sorted(INACTIVE_QUEUE_STATES))
    for i in range(1000):
        c=Command(f"AWJ-{i}",NOW-7200-i,"GEN25","d91e0a39358901c5","READY",False)
        unrelated=[Receipt("HISTORICAL",NOW-10,"RESULT","TERMINAL_SUCCESS")]
        p=compile_recovery(now_s=NOW,head=HEAD,commands=[c],receipts=unrelated,consumer=ConsumerObservation(False),starvation_after_s=3600,reducer_stall_after_s=3600)
        if p.system_state==SystemState.HEALTHY_PROGRESS or p.provider_fanout_allowed: false_healthy+=1
        mode=i%3
        if mode==0:
            try:
                compile_recovery(now_s=NOW,head=HEAD,commands=[c],receipts=[Receipt(c.command_id,NOW+1,"RESULT","TERMINAL_SUCCESS")],consumer=ConsumerObservation(False),starvation_after_s=3600,reducer_stall_after_s=3600)
                boundary_failures+=1
            except E as exc:
                if str(exc)!="FUTURE_RECEIPT": boundary_failures+=1
        elif mode==1:
            ic=Command(c.command_id,c.created_s,c.generation,c.head_digest,inactive[i%len(inactive)],False)
            ip=compile_recovery(now_s=NOW,head=HEAD,commands=[ic],receipts=(),consumer=ConsumerObservation(False),starvation_after_s=3600,reducer_stall_after_s=3600)
            if ip.system_state!=SystemState.NO_ACTIVE_INGRESS: boundary_failures+=1
        else:
            try:
                compile_recovery(now_s=NOW,head=HEAD,commands=[c],receipts=(),consumer=ConsumerObservation(True),starvation_after_s=3600,reducer_stall_after_s=3600)
                boundary_failures+=1
            except E as exc:
                if str(exc)!="INCOMPLETE_CONSUMER_OBSERVATION": boundary_failures+=1
        hs.append(p.receipt_root)
    consumer_fuzz_rejected=0
    for i in range(1000):
        # 2/3 malformed: missing required observed service state every third, or non-bool service every odd cell.
        bad = ConsumerObservation(True, service_active=(None if i%3==0 else (i if i%2 else True)), lease_current=None)
        try:
            compile_recovery(now_s=NOW,head=HEAD,commands=[Command(f"X{i}",NOW-7200,"GEN25","d91e0a39358901c5","READY",False)],receipts=[],consumer=bad,starvation_after_s=3600,reducer_stall_after_s=3600)
        except E:
            consumer_fuzz_rejected += 1
    omega=sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8))
    repairs=sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
    out={
      "oracle_decisions":100_000,"oracle_mismatches":mismatches,
      "future_receipts_rejected":future_receipts_rejected,
      "hs1000_false_healthy":false_healthy,"hs1000_boundary_failures":boundary_failures,
      "consumer_fuzz_rejected":consumer_fuzz_rejected,
      "omega8_keepers":omega,"13d_repairs":repairs,
      "oracle_root":sha256("".join(roots).encode()).hexdigest(),
      "hs1000_root":sha256("".join(hs).encode()).hexdigest(),
    }
    out["campaign_root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    print(json.dumps(out,sort_keys=True))
    if mismatches or false_healthy or boundary_failures or omega!=1 or repairs!=0 or consumer_fuzz_rejected != 667: raise SystemExit(1)

if __name__=='__main__': run()
