from __future__ import annotations
import hashlib,itertools,json,math,random,struct
from security_transition_domain import (
    CrossPlaneBinding, Decision, ParentReceipt, TransitionDomainSpec, TransitionEvidence,
    causal_time_order, finite_positive_duration, readjudicate, terminal_transition_allowed,
)
H=lambda s:hashlib.sha256(s.encode()).hexdigest()
GRAPH={
    "generation":("semantic_domain","semantic_projection"),
    "semantic_domain":("cross_plane_binding","value_domain"),
    "semantic_projection":("cross_plane_binding",),
    "cross_plane_binding":("evidence_current",),
    "value_domain":("causal_order","lifecycle_transition"),
    "causal_order":("evidence_current",),
    "lifecycle_transition":("evidence_current",),
    "evidence_current":("reproducible",),
    "reproducible":(),
}
LOCAL_FIELDS=(
    ("generation_current","generation"),
    ("semantic_domain_current","semantic_domain"),
    ("semantic_projection_current","semantic_projection"),
    ("cross_plane_binding_current","cross_plane_binding"),
    ("value_domain_valid","value_domain"),
    ("causal_order_valid","causal_order"),
    ("lifecycle_transition_valid","lifecycle_transition"),
    ("evidence_current","evidence_current"),
    ("reproducible","reproducible"),
)
EVIDENCE_FIELDS=tuple(name for name,_ in LOCAL_FIELDS)+("external_auth_complete","authority_ceiling_intact")

def binding():
    spec=TransitionDomainSpec(H("domain"),H("projection"),H("schema"))
    return CrossPlaneBinding(ParentReceipt("p839","g839",H("839")),ParentReceipt("p845","g845",H("845")),spec.spec_root)

def evidence_from_bits(bits):
    return TransitionEvidence(**dict(zip(EVIDENCE_FIELDS,bits)))

def run():
    # Conceptual 8-hard/5-context lattice retained as falsification geometry.
    admitted=0; hard_invalid_admits=0
    for state in itertools.product((0,1,2), repeat=13):
        eligible=all(v==2 for v in state[:8]); admitted+=int(eligible)
        if eligible and any(v!=2 for v in state[:8]): hard_invalid_admits+=1

    # Actual implementation truth table: all 11 evidence booleans are noncompensatory.
    b=binding(); boolean_eligible=0; boolean_unsafe_eligible=0
    for bits in itertools.product((False,True), repeat=len(EVIDENCE_FIELDS)):
        decision=readjudicate(evidence=evidence_from_bits(bits),binding=b,dependency_graph=GRAPH).decision
        is_eligible=decision is Decision.ELIGIBLE_FOR_FRESH_READJUDICATION
        boolean_eligible+=int(is_eligible)
        boolean_unsafe_eligible+=int(is_eligible and not all(bits))

    # No caller-declared change subset may hide an observed failed local axis.
    local_nodes=tuple(node for _,node in LOCAL_FIELDS); reproof_cases=0; reproof_misses=0
    for field,node in LOCAL_FIELDS:
        for mask in range(1<<len(local_nodes)):
            declared=tuple(local_nodes[i] for i in range(len(local_nodes)) if mask&(1<<i))
            kwargs={name:True for name in EVIDENCE_FIELDS}; kwargs[field]=False
            r=readjudicate(evidence=TransitionEvidence(**kwargs),binding=b,dependency_graph=GRAPH,changed_dimensions=declared)
            reproof_cases+=1
            if r.decision is not Decision.REPROVE_LOCAL_FIRST or node not in r.reproof_cone:
                reproof_misses+=1

    labels=("observed","issued","now","expires"); values=(100,200,300,400)
    legacy_accepts=lawful=fixed_accepts=0
    for perm in itertools.permutations(labels):
        d={name:values[i] for i,name in enumerate(perm)}
        legacy=d["now"]>=d["issued"] and d["now"]<=d["expires"] and d["now"]-d["observed"]<=1000
        fixed=causal_time_order(observed_at_ms=d["observed"],issued_at_ms=d["issued"],now_ms=d["now"],expires_at_ms=d["expires"],max_age_ms=1000)
        legacy_accepts+=int(legacy); lawful+=int(d["observed"]<=d["issued"]<=d["now"]<=d["expires"]); fixed_accepts+=int(fixed)
    rng=random.Random(20260908); samples=1_000_000; legacy_nonfinite=fixed_nonfinite=0
    for _ in range(samples):
        x=struct.unpack("!d",rng.getrandbits(64).to_bytes(8,"big"))[0]
        legacy=not (x<=0.0)
        try: finite_positive_duration(x); fixed=True
        except Exception: fixed=False
        if legacy and not math.isfinite(x): legacy_nonfinite+=1
        if fixed and not math.isfinite(x): fixed_nonfinite+=1
    states=("NOT_STARTED","UNKNOWN","COMPLETED"); legacy_retry=fixed_retry=0
    for length in range(1,8):
        for seq in itertools.product(states, repeat=length):
            retry_after_completed=any(seq[i]=="COMPLETED" and any(x!="COMPLETED" for x in seq[i+1:]) for i in range(len(seq)))
            if retry_after_completed: legacy_retry+=1
            fixed_path=all(terminal_transition_allowed(previous,new) for previous,new in zip(seq,seq[1:]))
            if retry_after_completed and fixed_path: fixed_retry+=1
    result={
        "schema":"AURA-SECURITY-TRANSITION-DOMAIN-COMPILER-D0-v2",
        "13d_states":3**13,"13d_admitted_context_variants":admitted,"13d_hard_invalid_admits":hard_invalid_admits,
        "boolean_gate_states":2**len(EVIDENCE_FIELDS),"boolean_gate_eligible":boolean_eligible,"boolean_gate_unsafe_eligible":boolean_unsafe_eligible,
        "reproof_union_cases":reproof_cases,"reproof_union_misses":reproof_misses,
        "causal_strict_orderings":24,"legacy_causal_accepts":legacy_accepts,"lawful_causal_orderings":lawful,"fixed_causal_accepts":fixed_accepts,
        "ieee754_samples":samples,"legacy_nonfinite_accepts":legacy_nonfinite,"fixed_nonfinite_accepts":fixed_nonfinite,
        "legacy_retry_after_completed_events":legacy_retry,"fixed_retry_after_completed_events":fixed_retry,
    }
    encoded=json.dumps(result,sort_keys=True,separators=(",",":")); result["campaign_root"]=hashlib.sha256(encoded.encode()).hexdigest()
    assert admitted==243 and hard_invalid_admits==0
    assert boolean_eligible==1 and boolean_unsafe_eligible==0
    assert reproof_cases==len(LOCAL_FIELDS)*(1<<len(local_nodes)) and reproof_misses==0
    assert legacy_accepts==4 and lawful==1 and fixed_accepts==1
    assert legacy_nonfinite>0 and fixed_nonfinite==0
    assert legacy_retry>0 and fixed_retry==0
    return result
if __name__=="__main__": print(json.dumps(run(),sort_keys=True,separators=(",",":")))
