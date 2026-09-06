from hashlib import sha256
import itertools, json, random
from host_observation_bridge import *
from liveness_witness import Command, compile_recovery, omega8_keeper, context13_preserves_invalid

NOW=2_000_000
A="a"*64; B="b"*64; C="c"*64; D="d"*64

def s(t, *, active="active", pid=7, state=B, receipts=C, command_receipt=None, cursor=None, scan=None):
    if cursor is None: cursor=max(0,t-1000)
    if scan is None: scan=max(0,t-500)
    return HostSnapshot(t,active,"running" if active=="active" else "dead",pid,A,state,receipts,command_receipt,cursor,scan,None)

def oracle_move(a,b):
    return any((a.state_sha256!=b.state_sha256,a.command_bound_receipt_root!=b.command_bound_receipt_root,a.cursor_s!=b.cursor_s,a.last_scan_s!=b.last_scan_s))

def run():
    rng=random.Random(852003)
    mismatches=0
    roots=[]
    for i in range(100_000):
        bt=1_000_000+rng.randrange(400_000)
        at=bt+rng.randrange(500_000)
        before=s(bt,state=B,receipts=C,cursor=bt-1000-rng.randrange(1000),scan=bt-100-rng.randrange(100))
        mode=rng.randrange(6)
        after=s(at,state=(D if mode==1 else before.state_sha256),receipts=(D if mode==2 else before.receipts_inventory_root),command_receipt=(D if mode==3 else before.command_bound_receipt_root),cursor=(before.cursor_s+1 if mode==4 else before.cursor_s),scan=(before.last_scan_s+1 if mode==5 else before.last_scan_s))
        pair=compare_snapshots(before,after,observation_cut_s=NOW)
        mismatches += pair.progress_moved != oracle_move(before,after)
        roots.append(pair.observation.evidence_root)
    # HS1000: active process, no observed progress after canary iteration => exactly one bounded restart, never fanout.
    false_decisions=0
    hs=[]
    for i in range(1000):
        before=s(1_700_000+i,cursor=1_600_000,scan=1_600_100)
        after=s(1_800_000+i,cursor=1_600_000,scan=1_600_100)
        pair=compare_snapshots(before,after,observation_cut_s=NOW)
        cmd=Command(f"AWJ{i}",1_000_000,EXPECTED_HEAD.generation,EXPECTED_HEAD.digest,"READY",False)
        p=compile_recovery(now_s=NOW,head=EXPECTED_HEAD,commands=[cmd],receipts=[],consumer=pair.observation,starvation_after_s=3600,reducer_stall_after_s=3600)
        false_decisions += not (p.restart_budget==1 and not p.provider_fanout_allowed and p.recovery_steps.count("RESTART_AURA_PROJECT006_ONCE")==1)
        hs.append(p.receipt_root)
    probe=compile_read_only_probe(); assert_probe_read_only(probe)
    forbidden_hits=sum(any(tok.lower() in {"restart","start","stop","kill","allow","once","python","python3","curl","wget"} for tok in st.argv) for st in probe.steps)
    omega=sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8))
    repairs=sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
    out={
        "movement_oracle_decisions":100_000,
        "movement_mismatches":mismatches,
        "hs1000_false_recovery_decisions":false_decisions,
        "probe_forbidden_effect_hits":forbidden_hits,
        "omega8_keepers":omega,
        "13d_repairs":repairs,
        "movement_root":sha256("".join(roots).encode()).hexdigest(),
        "hs1000_root":sha256("".join(hs).encode()).hexdigest(),
        "probe_plan_root":probe.plan_root,
    }
    out["campaign_root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    print(json.dumps(out,sort_keys=True))
    if mismatches or false_decisions or forbidden_hits or omega!=1 or repairs!=0:
        raise SystemExit(1)

if __name__ == "__main__": run()
