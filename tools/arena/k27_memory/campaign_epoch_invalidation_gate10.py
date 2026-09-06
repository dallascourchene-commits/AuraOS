from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from itertools import product
from pathlib import Path
import json, tempfile, sys

ARENA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ARENA))

from k27_memory import FrameAddress, MemoryConflict, MemoryStore, StaleMemory
from k27_memory.gate10_campaign_oracle import (
    HOLD_STORE_ROOT_CONFLICT, HOLD_STALE_DEPENDENCY, classify_round, completion_fields, trace_entry,
)
from consequence_admission_kernel import (
    AdmissionInput, AdmissionPolicy, AxisState, ConsequenceAdmissionKernel,
    ConsequenceVector, Decision, SourceExit,
)

WORKERS=5
ROUNDS=750

def canon(x):
    return json.dumps(x, sort_keys=True, separators=(',',':'))

def run():
    trace=[]
    false_accept=0
    false_hold=0
    aba_violations=0
    stale_dependency_violations=0
    stale_dependency_holds=0
    store_root_conflict_holds=0
    round_failures=[]
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'campaign.sqlite'
        with MemoryStore(p) as s:
            s.register_frame('f','g',expected_generation=None)
            src=s.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
            s.publish('dep', {'v':1}, FrameAddress('f','g',(2,),'dep'), source_url='u', source_version='1',
                          dependencies={'src':src['revision_id']}, dependency_epochs={'src':src['epoch']})
        for r in range(ROUNDS):
            with MemoryStore(p) as s:
                src_now=s.get('src')
                root=s.state_root()
            observed_rev=src_now['revision_id']; observed_epoch=src_now['epoch']
            def attempt(worker):
                try:
                    with MemoryStore(p) as s:
                        out=s.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1',
                                      expected_revision=observed_rev, expected_epoch=observed_epoch, expected_store_root=root)
                    return ('WIN', worker, out['revision_id'], out['epoch'], tuple(out['invalidated']), out['store_state_root'])
                except MemoryConflict as e:
                    return (HOLD_STORE_ROOT_CONFLICT, worker, type(e).__name__)
                except StaleMemory as e:
                    return (HOLD_STALE_DEPENDENCY, worker, type(e).__name__)
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                results=list(ex.map(attempt, range(WORKERS)))
            classified=classify_round(results, WORKERS, expected_hold=HOLD_STORE_ROOT_CONFLICT)
            store_root_conflict_holds += classified.hold_count
            false_accept += classified.false_accept_delta
            false_hold += classified.false_hold_delta
            if not classified.valid:
                round_failures.append({
                    'round':r, 'reason':classified.reason,
                    'win_count':classified.win_count, 'hold_count':classified.hold_count,
                    'unexpected_count':classified.unexpected_count,
                })
                break
            win=classified.winner
            if win[2] != observed_rev: aba_violations += 1
            if win[3] != observed_epoch+1: aba_violations += 1
            if 'dep' not in win[4]: stale_dependency_violations += 1
            with MemoryStore(p) as s:
                try:
                    s.get('dep')
                    stale_dependency_violations += 1
                except StaleMemory:
                    pass
                dep_stale=s.get('dep', allow_stale=True)
                try:
                    s.publish('dep', {'v':1}, FrameAddress('f','g',(2,),'dep'), source_url='u', source_version='1',
                              expected_revision=dep_stale['revision_id'], expected_epoch=dep_stale['epoch'],
                              dependencies={'src':observed_rev}, dependency_epochs={'src':observed_epoch})
                    stale_dependency_violations += 1
                except StaleMemory:
                    stale_dependency_holds += 1
                except MemoryConflict:
                    stale_dependency_violations += 1
                src_fresh=s.get('src')
                dep_repaired=s.publish('dep', {'v':1}, FrameAddress('f','g',(2,),'dep'), source_url='u', source_version='1',
                                       expected_revision=dep_stale['revision_id'], expected_epoch=dep_stale['epoch'],
                                       dependencies={'src':src_fresh['revision_id']}, dependency_epochs={'src':src_fresh['epoch']})
                final_root=s.state_root()
            trace.append(trace_entry(r, win, dep_repaired['epoch'], final_root))
    # 8-crystalline noncompensatory collapse: only all verified is a keeper.
    # Factorized 13D falsification against the canonical consequence kernel.
    # Layer A covers every Omega8 state at antipodal routing tails. Layer B
    # covers every routing tail for each single-hard-invalid axis basis. This
    # makes the routing check consequence-bearing rather than tautological.
    kernel=ConsequenceAdmissionKernel()
    policy=AdmissionPolicy('gate10-epoch-campaign-v1', tuple(range(8)), ())
    source=SourceExit('campaign','arena-gate10','r1','semantic-root',True)
    keeper=0
    hard_invalid_repaired=0
    routing_decision_variations=0
    vectors_checked=0
    tails=((0,0,0,0,0),(2,2,2,2,2))
    for axes in product((0,1,2), repeat=8):
        omega=tuple(AxisState(v) for v in axes)
        decisions=[]
        for tail in tails:
            receipt=kernel.assess(AdmissionInput('GATE10_EPOCH',ConsequenceVector(omega,tail),policy,source))
            decisions.append(receipt.decision)
            vectors_checked += 1
            if 0 in axes and receipt.decision == Decision.READY_NONAUTHORIZING:
                hard_invalid_repaired += 1
        if decisions[0] != decisions[1]: routing_decision_variations += 1
        if all(v==2 for v in axes) and decisions[0] == Decision.READY_NONAUTHORIZING:
            keeper += 1
    for hard_axis in range(8):
        axes=[2]*8; axes[hard_axis]=0
        omega=tuple(AxisState(v) for v in axes)
        baseline=None
        for tail in product((0,1,2), repeat=5):
            receipt=kernel.assess(AdmissionInput('GATE10_EPOCH',ConsequenceVector(omega,tail),policy,source))
            vectors_checked += 1
            if receipt.decision == Decision.READY_NONAUTHORIZING:
                hard_invalid_repaired += 1
            if baseline is None: baseline=receipt.decision
            elif receipt.decision != baseline: routing_decision_variations += 1
    root=sha256(canon(trace).encode()).hexdigest()
    completion=completion_fields(trace, round_failures, ROUNDS)
    return {
        'workers':WORKERS,'rounds':ROUNDS,'attempts':WORKERS*ROUNDS,
        'stale_dependency_probes':ROUNDS, 'total_write_attempts':(WORKERS+1)*ROUNDS,
        'false_accept':false_accept,'false_hold':false_hold,
        'store_root_conflict_holds':store_root_conflict_holds,
        'stale_dependency_holds':stale_dependency_holds,
        'aba_violations':aba_violations,'stale_dependency_violations':stale_dependency_violations,
        'omega8_keepers':keeper,'routing13_hard_invalid_repairs':hard_invalid_repaired,
        'routing13_decision_variations':routing_decision_variations,
        'routing13_vectors_checked':vectors_checked,
        **completion, 'round_failure_details':round_failures,
        'campaign_root':root,'final':trace[-1] if trace else None,
    }

if __name__=='__main__':
    print(json.dumps(run(),sort_keys=True))
