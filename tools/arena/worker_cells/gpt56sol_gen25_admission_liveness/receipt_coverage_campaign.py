from dataclasses import dataclass
from hashlib import sha256
import itertools, json, random
from receipt_coverage_witness import *

ROOT="a"*64

@dataclass(frozen=True)
class R: sequence_no:int
@dataclass(frozen=True)
class P:
    command_id:str="CMD"; attempt_id:str|None="ATT"; receipts:tuple[R,...]=(); hold_reason:str|None=None; ledger_root:str="b"*64

def run():
    rng=random.Random(85301)
    mismatches=0; roots=[]
    for i in range(100_000):
        universe=sorted(rng.sample(range(0,200), rng.randrange(0,20)))
        expected=tuple(universe)
        mode=rng.randrange(4)
        if mode==0: observed=expected
        elif mode==1 and expected:
            drop=rng.choice(expected); observed=tuple(x for x in expected if x!=drop)
        elif mode==2:
            extra=201+i; observed=tuple(sorted(expected+(extra,)))
        else:
            observed=expected
            if expected:
                drop=rng.choice(expected); observed=tuple(x for x in expected if x!=drop)
            extra=500+i; observed=tuple(sorted(observed+(extra,)))
        c=compile_coverage_contract(command_id="CMD",attempt_id="ATT",expected_sequence_ids=expected,witness_root=ROOT)
        r=verify_projection_coverage(c,P(receipts=tuple(R(x) for x in reversed(observed))))
        missing=tuple(sorted(set(expected)-set(observed))); unexpected=tuple(sorted(set(observed)-set(expected)))
        if not missing and not unexpected: exp=CoverageState.COMPLETE
        elif missing and not unexpected: exp=CoverageState.MISSING_EXPECTED
        elif unexpected and not missing: exp=CoverageState.UNEXPECTED_OBSERVED
        else: exp=CoverageState.COVERAGE_MISMATCH
        mismatches += (r.state is not exp or r.coverage_complete != (exp is CoverageState.COMPLETE))
        roots.append(r.receipt_root)

    missing_escapes=extra_escapes=hold_repairs=origin_assumptions=0
    for i in range(1000):
        expected=(0,2,7,50+i)
        c=compile_coverage_contract(command_id="CMD",attempt_id="ATT",expected_sequence_ids=expected,witness_root=ROOT)
        m=verify_projection_coverage(c,P(receipts=tuple(R(x) for x in expected if x!=2)))
        missing_escapes += m.coverage_complete
        e=verify_projection_coverage(c,P(receipts=tuple(R(x) for x in expected+(10000+i,))))
        extra_escapes += e.coverage_complete
        h=verify_projection_coverage(c,P(receipts=tuple(R(x) for x in expected),hold_reason="SEQUENCE_EQUIVOCATION"))
        hold_repairs += h.coverage_complete
        s=verify_projection_coverage(c,P(receipts=tuple(R(x) for x in reversed(expected))))
        origin_assumptions += not s.coverage_complete

    omega=sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8))
    repairs=sum(context13_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5))
    out={
      "oracle_decisions":100000,"oracle_mismatches":mismatches,
      "hs1000_missing_coverage_escapes":missing_escapes,
      "hs1000_unexpected_coverage_escapes":extra_escapes,
      "hs1000_integrity_hold_repairs":hold_repairs,
      "hs1000_origin_or_contiguity_assumptions":origin_assumptions,
      "omega8_keepers":omega,"13d_repairs":repairs,
      "oracle_root":sha256("".join(roots).encode()).hexdigest(),
    }
    out["campaign_root"]=sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    print(json.dumps(out,sort_keys=True))
    if any((mismatches,missing_escapes,extra_escapes,hold_repairs,origin_assumptions,repairs)) or omega != 1:
        raise SystemExit(1)

if __name__=="__main__": run()
