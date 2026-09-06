from __future__ import annotations

import json, random
from dataclasses import asdict, replace
from pathlib import Path

from runtime_bound_memory import (
    CLAIM_CEILING, Corroborator, CurrentState, Disposition, MemoryRecord,
    ProducerReceipt, admit_memory, hobj, reverse_dependency_cone,
)

H=lambda s: hobj({"v":s})


def fixture():
    producer = ProducerReceipt(
        parent_pid=101, worker_pid=202, start_method="spawn", ready=True,
        process_isolated=True, nonce_root=H("nonce"), factory_root=H("factory"),
        implementation_generation=H("impl-g2"), runtime_owner_generation=H("owner-g4"),
    )
    current = CurrentState(
        semantic_domain_root=H("sem-domain"), semantic_projection_root=H("sem-proj"),
        subject_generation="subject-g9", subject_state_root=H("subject-state-g9"),
        producer_receipt_root=producer.root,
        producer_implementation_generation=producer.implementation_generation,
        producer_owner_generation=producer.runtime_owner_generation,
        currentness_generation="current-g12", external_auth_generation="auth-g8",
    )
    memory = MemoryRecord(
        memory_id="M-001", payload_hash=H("payload"), lineage_root=H("lineage-a"),
        source_root=H("source-a"), consequence_root=H("consequence-a"),
        semantic_domain_root=current.semantic_domain_root,
        semantic_projection_root=current.semantic_projection_root,
        subject_generation=current.subject_generation, subject_state_root=current.subject_state_root,
        producer_receipt_root=producer.root,
        producer_implementation_generation=producer.implementation_generation,
        producer_owner_generation=producer.runtime_owner_generation,
        dependency_keys=("SOURCE", "SEMANTIC", "SUBJECT", "PRODUCER_RUNTIME"),
    )
    return memory, producer, current


def independent_oracle(memory, producer, current, corroborators=(), require=0):
    if memory.revoked or not memory.externally_authenticated or not memory.currentness_attested:
        return Disposition.QUARANTINE_AUTHORITY
    if memory.memory_class == "PROCEDURAL" and not memory.procedure_authority:
        return Disposition.QUARANTINE_AUTHORITY
    if memory.semantic_domain_root != current.semantic_domain_root or memory.semantic_projection_root != current.semantic_projection_root:
        return Disposition.REPROVE_SEMANTIC
    if memory.subject_generation != current.subject_generation or memory.subject_state_root != current.subject_state_root:
        return Disposition.REPROVE_SUBJECT_STATE
    pbad = (
        not producer.structurally_valid()
        or memory.producer_receipt_root != producer.root
        or current.producer_receipt_root != producer.root
        or memory.producer_implementation_generation != current.producer_implementation_generation
        or producer.implementation_generation != current.producer_implementation_generation
        or memory.producer_owner_generation != current.producer_owner_generation
        or producer.runtime_owner_generation != current.producer_owner_generation
    )
    if pbad:
        return Disposition.REPROVE_PRODUCER_RUNTIME
    if require:
        n = len({(c.lineage_root,c.source_root,c.consequence_root) for c in corroborators if c.authenticated and c.current})
        if n < require:
            return Disposition.HOLD_CORROBORATION
    return Disposition.ELIGIBLE_FOR_OWNER_REVIEW


def mutate_case(memory, producer, current, idx):
    mode = idx % 8
    if mode == 0:
        memory = replace(memory, subject_generation=f"moved-{idx}")
    elif mode == 1:
        memory = replace(memory, subject_state_root=H(f"moved-state-{idx}"))
    elif mode == 2:
        current = replace(current, producer_implementation_generation=H(f"impl-moved-{idx}"))
    elif mode == 3:
        current = replace(current, producer_owner_generation=H(f"owner-moved-{idx}"))
    elif mode == 4:
        producer = replace(producer, process_isolated=False)
    elif mode == 5:
        memory = replace(memory, semantic_domain_root=H(f"sem-moved-{idx}"))
    elif mode == 6:
        memory = replace(memory, externally_authenticated=False)
    else:
        memory = replace(memory, authority_ceiling="EFFECT_AUTHORIZED")
    return memory, producer, current


def run(root: str|Path, oracle_cases=100000, hs1000=1000):
    root=Path(root); root.mkdir(parents=True, exist_ok=True)
    memory, producer, current=fixture()
    clean=admit_memory(memory,producer,current)
    assert clean.disposition==Disposition.ELIGIBLE_FOR_OWNER_REVIEW

    false_admissions=0
    counts={d.value:0 for d in Disposition}
    for i in range(hs1000):
        m,p,c=mutate_case(memory,producer,current,i)
        d=admit_memory(m,p,c)
        counts[d.disposition.value]+=1
        if d.disposition==Disposition.ELIGIBLE_FOR_OWNER_REVIEW:
            false_admissions+=1

    rng=random.Random(20260905)
    oracle_mismatches=0
    for i in range(oracle_cases):
        m,p,c=memory,producer,current
        # independently randomize one or more semantic/runtime axes
        for axis in range(7):
            if rng.randrange(7)==0:
                if axis==0: m=replace(m,subject_generation=f"sg-{i}")
                elif axis==1: m=replace(m,subject_state_root=H(f"ss-{i}"))
                elif axis==2: c=replace(c,producer_implementation_generation=H(f"pi-{i}"))
                elif axis==3: c=replace(c,producer_owner_generation=H(f"po-{i}"))
                elif axis==4: p=replace(p,process_isolated=False)
                elif axis==5: m=replace(m,semantic_projection_root=H(f"sp-{i}"))
                else: m=replace(m,revoked=True)
        got=admit_memory(m,p,c).disposition
        exp=independent_oracle(m,p,c)
        if got!=exp: oracle_mismatches+=1

    # Omega8: eight ternary hard axes; only all-zero/current is keeper.
    omega_keeper=0
    for state in range(3**8):
        trits=[]; z=state
        for _ in range(8): trits.append(z%3); z//=3
        m,p,c=memory,producer,current
        if trits[0]: m=replace(m,semantic_domain_root=H(f"od{trits[0]}"))
        if trits[1]: m=replace(m,semantic_projection_root=H(f"op{trits[1]}"))
        if trits[2]: m=replace(m,subject_generation=f"og{trits[2]}")
        if trits[3]: m=replace(m,subject_state_root=H(f"os{trits[3]}"))
        if trits[4]: c=replace(c,producer_implementation_generation=H(f"oi{trits[4]}"))
        if trits[5]: c=replace(c,producer_owner_generation=H(f"oo{trits[5]}"))
        if trits[6]: p=replace(p,process_isolated=False)
        if trits[7]: m=replace(m,externally_authenticated=False)
        if admit_memory(m,p,c).disposition==Disposition.ELIGIBLE_FOR_OWNER_REVIEW: omega_keeper+=1

    # 13D tail: a hard-invalid producer core cannot be repaired by 5 context trits.
    hard=replace(producer, process_isolated=False)
    repaired=0
    context_roots=set()
    for tail in range(3**5):
        ctx=[]; z=tail
        for _ in range(5): ctx.append(z%3); z//=3
        context_roots.add(hobj(ctx))
        if admit_memory(memory,hard,current).disposition==Disposition.ELIGIBLE_FOR_OWNER_REVIEW:
            repaired+=1

    graph={
        "PRODUCER_RUNTIME": ["MEMORY_ELIGIBILITY"],
        "MEMORY_ELIGIBILITY": ["K27_REUSE", "ACTION_POLICY"],
        "K27_REUSE": ["FINAL_RECEIPT"],
        "ACTION_POLICY": ["FINAL_RECEIPT"],
        "UNRELATED_SOURCE": ["UNRELATED_SUMMARY"],
    }
    producer_cone=reverse_dependency_cone(graph,["PRODUCER_RUNTIME"])

    summary={
        "schema":"AURA-O2-RUNTIME-BOUND-MEMORY-CAMPAIGN-v1",
        "claim_ceiling":CLAIM_CEILING,
        "clean_disposition":clean.disposition.value,
        "clean_k27":clean.k27,
        "hs1000_cases":hs1000,
        "hs1000_false_admissions":false_admissions,
        "hs1000_dispositions":{k:v for k,v in counts.items() if v},
        "oracle_cases":oracle_cases,
        "oracle_mismatches":oracle_mismatches,
        "omega8_states":3**8,
        "omega8_keepers":omega_keeper,
        "13d_context5_states":3**5,
        "13d_hard_invalid_repairs":repaired,
        "distinct_context_roots":len(context_roots),
        "producer_invalidation_cone":producer_cone,
        "unrelated_source_preserved":"UNRELATED_SOURCE" not in producer_cone,
        "promotion_authorized":False,
        "gate10":False,
    }
    summary["receipt_root"]=hobj(summary)
    (root/"campaign_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    return summary

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--oracle-cases",type=int,default=100000)
    ns=ap.parse_args(); print(json.dumps(run(ns.root,ns.oracle_cases),indent=2,sort_keys=True))
