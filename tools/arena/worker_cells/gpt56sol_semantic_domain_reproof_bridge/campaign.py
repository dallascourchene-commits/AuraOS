from dataclasses import replace
from hashlib import sha256
from itertools import product
import json, random
from semantic_domain_reproof_bridge import *
from test_semantic_domain_reproof_bridge import graph_fixture, surfaces, evidence_fixture, R


def independent_closure(g, seeds):
    deps = {n.node_id: set(n.dependencies) for n in g.nodes}
    out = set(seeds)
    changed = True
    while changed:
        changed = False
        for node_id, parents in deps.items():
            if node_id not in out and parents & out:
                out.add(node_id); changed = True
    return tuple(x for x in g.topo_order if x in out)


def remint_owner(o, **updates):
    return CurrentOwnerSurface.mint_identity_surface(
        graph_root=updates.get("graph_root", o.graph_root),
        verifier_generations=updates.get("verifier_generations", o.verifier_generations),
        projection_roots=updates.get("projection_roots", o.projection_roots),
        semantic_domain_roots=updates.get("semantic_domain_roots", o.semantic_domain_roots),
        owner_replay_receipt_root=updates.get("owner_replay_receipt_root", o.owner_replay_receipt_root),
    )


def main():
    rng = random.Random(20260905_04)
    g = graph_fixture(); a, o = surfaces(g); e = evidence_fixture(g, a, o)
    ids = list(g.topo_order)
    closure_mismatch = 0
    recompute_sum = 0
    for _ in range(100000):
        k = 1 if rng.random() < .8 else 2
        seeds = tuple(sorted(rng.sample(ids, k)))
        p = compile_reproof_plan(g, explicit_changed_roots=seeds, evidence=e, admission=a, current_owner=o)
        expected = independent_closure(g, seeds)
        closure_mismatch += int(p.recompute_order != expected)
        recompute_sum += len(p.recompute_order)

    false_reuse = 0
    mutation_counts = {"domain":0, "projection":0, "generation":0, "witness":0, "authority":0}
    for i in range(1000):
        target = rng.choice(ids)
        kind = rng.choice(tuple(mutation_counts))
        mutation_counts[kind] += 1
        try:
            if kind == "domain":
                sd = dict(o.semantic_domain_roots); sd[target] = sha256(f"domain-{i}".encode()).hexdigest()
                oo = remint_owner(o, semantic_domain_roots=sd.items())
                p = compile_reproof_plan(g, explicit_changed_roots=(), evidence=e, admission=a, current_owner=oo)
                false_reuse += int(target in p.reuse_nodes)
            elif kind == "projection":
                pp = dict(o.projection_roots); pp[target] = sha256(f"projection-{i}".encode()).hexdigest()
                oo = remint_owner(o, projection_roots=pp.items())
                p = compile_reproof_plan(g, explicit_changed_roots=(), evidence=e, admission=a, current_owner=oo)
                false_reuse += int(target in p.reuse_nodes)
            elif kind == "generation":
                n = g.by_id[target]; vg = dict(o.verifier_generations); vg[n.verifier_id] = f"moved-{i}"
                oo = remint_owner(o, verifier_generations=vg.items())
                p = compile_reproof_plan(g, explicit_changed_roots=(), evidence=e, admission=a, current_owner=oo)
                false_reuse += int(target in p.reuse_nodes)
            elif kind == "witness":
                ee = dict(e); ee[target] = replace(ee[target], witness_root=sha256(f"witness-{i}".encode()).hexdigest())
                try:
                    p = compile_reproof_plan(g, explicit_changed_roots=(), evidence=ee, admission=a, current_owner=o)
                    false_reuse += int(target in p.reuse_nodes)
                except ReproofContractError:
                    pass
            else:
                ee = dict(e); ee[target] = replace(ee[target], effect_authority=True)
                try:
                    p = compile_reproof_plan(g, explicit_changed_roots=(), evidence=ee, admission=a, current_owner=o)
                    false_reuse += int(target in p.reuse_nodes)
                except ReproofContractError:
                    pass
        except ReproofContractError:
            # HOLD/fail-closed is a valid outcome; only a mutated target surviving in reuse is false admission.
            pass

    omega_admits = sum(omega8_admit(s) for s in product(range(3), repeat=8))
    # Sample 13D instead of enumerating the full 1,594,323 state space here; unit tests pin the keeper exactly.
    hard_invalid_repairs = 0
    seen_context5 = set()
    for _ in range(100000):
        state = tuple(rng.randrange(3) for _ in range(13))
        seen_context5.add(state[-5:])
        if state != (2,2,2,2,2,2,2,2,1,2,2,2,2) and admit13(state):
            hard_invalid_repairs += 1

    result = {
        "closure_cases": 100000,
        "closure_oracle_mismatches": closure_mismatch,
        "average_recompute_nodes_of_8": recompute_sum / 100000,
        "hs1000_cases": 1000,
        "hs1000_false_reuse": false_reuse,
        "hs1000_mutations": mutation_counts,
        "omega8_states": 3**8,
        "omega8_admits": omega_admits,
        "states13_sampled": 100000,
        "context5_roots_seen": len(seen_context5),
        "hard_invalid_13d_repairs": hard_invalid_repairs,
        "graph_root": g.graph_root,
        "admission_surface_root": a.surface_root,
        "owner_surface_root": o.surface_root,
        "claim_ceiling": "D0_EXTERNAL_AUTH_UNPROVEN",
    }
    result["campaign_root"] = sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__": main()
