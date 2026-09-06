from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
import random

from semantic_domain_reproof_bridge import *
from test_semantic_domain_reproof_bridge import graph_fixture, surfaces, evidence_fixture


def independent_closure(g, seeds):
    deps = {n.node_id: set(n.dependencies) for n in g.nodes}
    out = set(seeds)
    changed = True
    while changed:
        changed = False
        for node_id, parents in deps.items():
            if node_id not in out and parents & out:
                out.add(node_id)
                changed = True
    return tuple(x for x in g.topo_order if x in out)


def remint_owner(o, **updates):
    return CurrentOwnerSurface.mint_identity_surface(
        graph_root=updates.get("graph_root", o.graph_root),
        verifier_generations=updates.get("verifier_generations", o.verifier_generations),
        projection_roots=updates.get("projection_roots", o.projection_roots),
        semantic_domain_roots=updates.get("semantic_domain_roots", o.semantic_domain_roots),
        owner_replay_receipt_root=updates.get(
            "owner_replay_receipt_root", o.owner_replay_receipt_root
        ),
    )


def H(tag):
    return sha256(tag.encode()).hexdigest()


def main():
    rng = random.Random(20260905_041)
    g = graph_fixture()
    a, o = surfaces(g)
    e = evidence_fixture(g, a, o)
    ids = list(g.topo_order)

    closure_mismatch = 0
    recompute_sum = 0
    for _ in range(100000):
        k = 1 if rng.random() < 0.8 else 2
        seeds = tuple(sorted(rng.sample(ids, k)))
        p = compile_reproof_plan(
            g,
            explicit_changed_roots=seeds,
            evidence=e,
            admission=a,
            current_owner=o,
        )
        expected = independent_closure(g, seeds)
        closure_mismatch += int(p.recompute_order != expected)
        recompute_sum += len(p.recompute_order)

    transition_mismatch = 0
    for i in range(100000):
        target = rng.choice(ids)
        node = g.by_id[target]
        mode = rng.randrange(4)
        vg = dict(o.verifier_generations)
        pp = dict(o.projection_roots)
        sd = dict(o.semantic_domain_roots)
        expected = EXACT
        if mode == 1:
            vg[node.verifier_id] = f"generation-{i}"
            expected = REBIND
        elif mode == 2:
            pp[target] = H(f"projection-{i}")
            expected = REPROVE
        elif mode == 3:
            vg[node.verifier_id] = f"generation-{i}"
            sd[target] = H(f"domain-{i}")
            expected = REPROVE
        oo = remint_owner(
            o,
            verifier_generations=vg.items(),
            projection_roots=pp.items(),
            semantic_domain_roots=sd.items(),
        )
        p = compile_reproof_plan(
            g,
            explicit_changed_roots=(),
            evidence=e,
            admission=a,
            current_owner=oo,
        )
        got = dict(p.transition_classes)[target]
        transition_mismatch += int(got != expected)
        if expected == REBIND:
            transition_mismatch += int(target not in p.rebind_nodes or target in p.recompute_order)
        elif expected == REPROVE:
            transition_mismatch += int(target not in p.recompute_order)

    false_admission = 0
    mutation_counts = {
        "domain": 0,
        "projection": 0,
        "generation_rebind": 0,
        "witness": 0,
        "authority": 0,
    }
    for i in range(1000):
        target = ids[i % len(ids)]
        kind = tuple(mutation_counts)[i % len(mutation_counts)]
        mutation_counts[kind] += 1
        try:
            if kind == "domain":
                sd = dict(o.semantic_domain_roots)
                sd[target] = H(f"hs-domain-{i}")
                p = compile_reproof_plan(
                    g,
                    explicit_changed_roots=(),
                    evidence=e,
                    admission=a,
                    current_owner=remint_owner(o, semantic_domain_roots=sd.items()),
                )
                false_admission += int(target not in p.recompute_order)
            elif kind == "projection":
                pp = dict(o.projection_roots)
                pp[target] = H(f"hs-projection-{i}")
                p = compile_reproof_plan(
                    g,
                    explicit_changed_roots=(),
                    evidence=e,
                    admission=a,
                    current_owner=remint_owner(o, projection_roots=pp.items()),
                )
                false_admission += int(target not in p.recompute_order)
            elif kind == "generation_rebind":
                n = g.by_id[target]
                vg = dict(o.verifier_generations)
                vg[n.verifier_id] = f"hs-generation-{i}"
                p = compile_reproof_plan(
                    g,
                    explicit_changed_roots=(),
                    evidence=e,
                    admission=a,
                    current_owner=remint_owner(o, verifier_generations=vg.items()),
                )
                false_admission += int(target not in p.rebind_nodes or target in p.recompute_order)
            elif kind == "witness":
                ee = dict(e)
                ee[target] = replace(ee[target], witness_root=H(f"hs-witness-{i}"))
                try:
                    p = compile_reproof_plan(
                        g,
                        explicit_changed_roots=(),
                        evidence=ee,
                        admission=a,
                        current_owner=o,
                    )
                    false_admission += int(target in p.reuse_nodes or target in p.rebind_nodes)
                except ReproofContractError:
                    pass
            else:
                ee = dict(e)
                ee[target] = replace(ee[target], effect_authority=True)
                try:
                    p = compile_reproof_plan(
                        g,
                        explicit_changed_roots=(),
                        evidence=ee,
                        admission=a,
                        current_owner=o,
                    )
                    false_admission += int(target in p.reuse_nodes or target in p.rebind_nodes)
                except ReproofContractError:
                    pass
        except ReproofContractError:
            if kind in ("domain", "projection", "generation_rebind"):
                false_admission += 1

    generation_only_false_reproof = 0
    generation_only_false_reuse = 0
    for i in range(1000):
        target = ids[i % len(ids)]
        node = g.by_id[target]
        vg = dict(o.verifier_generations)
        vg[node.verifier_id] = f"neutral-{i}"
        p = compile_reproof_plan(
            g,
            explicit_changed_roots=(),
            evidence=e,
            admission=a,
            current_owner=remint_owner(o, verifier_generations=vg.items()),
        )
        generation_only_false_reproof += int(target in p.recompute_order)
        generation_only_false_reuse += int(target in p.reuse_nodes)
        generation_only_false_reuse += int(target not in p.rebind_nodes)

    omega_admits = sum(omega8_admit(s) for s in product(range(3), repeat=8))
    hard_invalid_repairs = 0
    seen_context5 = set()
    keeper13 = (2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2)
    for _ in range(100000):
        state = tuple(rng.randrange(3) for _ in range(13))
        seen_context5.add(state[-5:])
        if state != keeper13 and admit13(state):
            hard_invalid_repairs += 1

    base_plan = compile_reproof_plan(
        g,
        explicit_changed_roots=(),
        evidence=e,
        admission=a,
        current_owner=o,
    )
    result = {
        "closure_cases": 100000,
        "closure_oracle_mismatches": closure_mismatch,
        "average_explicit_change_recompute_nodes_of_8": recompute_sum / 100000,
        "transition_cases": 100000,
        "transition_oracle_mismatches": transition_mismatch,
        "hs1000_cases": 1000,
        "hs1000_false_admissions": false_admission,
        "hs1000_mutations": mutation_counts,
        "generation_only_hs1000_cases": 1000,
        "generation_only_false_reproof": generation_only_false_reproof,
        "generation_only_false_direct_reuse": generation_only_false_reuse,
        "omega8_states": 3**8,
        "omega8_admits": omega_admits,
        "states13_sampled": 100000,
        "context5_roots_seen": len(seen_context5),
        "hard_invalid_13d_repairs": hard_invalid_repairs,
        "graph_root": g.graph_root,
        "admission_surface_root": a.surface_root,
        "owner_surface_root": o.surface_root,
        "base_plan_root": base_plan.plan_root,
        "claim_ceiling": "D0_EXTERNAL_AUTH_UNPROVEN",
    }
    result["campaign_root"] = sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
