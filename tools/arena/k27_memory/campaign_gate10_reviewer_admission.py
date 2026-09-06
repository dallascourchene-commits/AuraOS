from __future__ import annotations

import json, random
from hashlib import sha256
try:
    from tools.arena.k27_memory import gate10_reviewer_admission as g
except ModuleNotFoundError:
    import gate10_reviewer_admission as g

HEAD = "67e1062cfab90ce647c7e3450cc613424746e285"
OWNER = "SESSION-WORKER:GPT56SOL:20260906T0846-0500-E4B9-STACK"
REVIEWER = "DIFFERENT-J:PR863:GATE10:REVIEWER:EXAMPLE"


def state_root(i):
    return sha256(f"post-repair:{i}".encode()).hexdigest()


def valid_evidence():
    trace=[{
        "round":i,"concurrent_attempts":5,"winner_count":1,"store_root_conflict_holds":4,
        "stale_dependency_probe":"HOLD_STALE_DEPENDENCY","aba_violations":0,
        "false_accepts":0,"false_holds":0,"post_repair_state_root":state_root(i),
    } for i in range(g.EXPECTED_ROUNDS)]
    return {
        "reviewer_identity":{"authority_status":"EXTERNALLY_AUTHENTICATED","actor_id":"worker:different-j",
            "lineage_root":REVIEWER,"generation":"github-app-review:20260906","attestation_root":"b"*64},
        "replay":{"campaign_complete":True,"completed_rounds":750,"round_failures":0,
            "concurrent_attempts":3750,"stale_dependency_probes":750,"aba_violations":0,
            "false_accepts":0,"false_holds":0,"trace":trace,"campaign_root":g.replay_trace_root(trace)},
        "registry":{"dataSound":True,"uniqueKeys":1115,"ambiguousDigests":0,
            "registry_sha256":g.REGISTRY_SHA256,"semantic_registry_root":g.SEMANTIC_REGISTRY_ROOT},
        "provenance":{"archive_sha256":g.PROVENANCE_ARCHIVE_SHA256,"manifest_sha256":g.PROVENANCE_MANIFEST_SHA256,
            "scene_source_sha256":g.SCENE_SOURCE_SHA256,"manifest_payloads_verified":69,"provider_bytes_bound":True},
        "invalidation":{"bounded":True,"deterministic":True,"ambiguous_edges":0},
        "authority":{"k27_coordinate_authority":False,"truth_authority":False,"currentness_authority":False,
            "authority_minted":False,"gate10":False,"canonical_promotion":False,"merge_authority":False,"effect_authority":False},
    }


def terminal_for(evidence, lineage=REVIEWER, head=HEAD):
    return g.build_terminal(terminal_id="terminal:review:1",actor_id="worker:different-j",lineage_root=lineage,
        derivation_root="sha256:"+"a"*64,reviewed_head_sha=head,evidence=evidence)


SEED = 27086313
SINGLE_PER_AXIS = 50
RANDOM_MULTI = 650
AXIS_KEYS = [
    "01_exact_current_head", "02_terminal_class", "03_reviewer_identity_authenticated_projection", "04_different_j",
    "05_terminal_receipt_root", "06_complete_evidence_root", "07_replay_complete",
    "08_full_trace_recomputable", "09_registry_shape", "10_provider_bytes",
    "11_invalidation_bounded_deterministic", "12_authority_decoupled_from_coordinate",
    "13_nonpromoting_reviewer_claim",
]


def canonical(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False)


def reseal(t, e):
    return g.build_terminal(terminal_id=t["terminal_id"], actor_id=t["actor_id"], lineage_root=t["lineage_root"],
                            derivation_root=t["derivation_root"], reviewed_head_sha=t["reviewed_head_sha"], evidence=e)


def mutate(e, t, axis):
    if axis == 1:
        t["reviewed_head_sha"] = "0" * 40; t["receipt_root"] = g.terminal_receipt_root(t)
    elif axis == 2:
        t["terminal_class"] = "NARRATIVE_ONLY"; t["receipt_root"] = g.terminal_receipt_root(t)
    elif axis == 3:
        e["reviewer_identity"]["authority_status"] = "OBSERVED"
        old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 4:
        t["lineage_root"] = OWNER
        e["reviewer_identity"]["lineage_root"] = OWNER
        old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 5:
        t["receipt_root"] = "f" * 64
    elif axis == 6:
        e["registry"]["dataSound"] = False
    elif axis == 7:
        e["replay"]["campaign_complete"] = False; old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 8:
        e["replay"]["trace"] = e["replay"]["trace"][:-1]
        e["replay"]["campaign_root"] = g.replay_trace_root(e["replay"]["trace"])
        old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 9:
        e["registry"]["uniqueKeys"] = 1114; old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 10:
        e["provenance"]["manifest_payloads_verified"] = 68; old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 11:
        e["invalidation"]["deterministic"] = False; old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 12:
        e["authority"]["truth_authority"] = True; old = dict(t); t.clear(); t.update(reseal(old, e))
    elif axis == 13:
        e["authority"]["authority_minted"] = True; old = dict(t); t.clear(); t.update(reseal(old, e))


def one(axis):
    e = valid_evidence(); t = terminal_for(e); mutate(e, t, axis); return e, t


def main():
    rng = random.Random(SEED)
    false_ready = 0
    isolated_detection = {key: 0 for key in AXIS_KEYS}
    roots = []
    for axis, key in enumerate(AXIS_KEYS, start=1):
        for _ in range(SINGLE_PER_AXIS):
            e, t = one(axis)
            r = g.evaluate_gate10_reviewer_admission(owner_lineage_root=OWNER, current_head_sha=HEAD, terminal=t, evidence=e)
            if r.decision is not g.Decision.HOLD: false_ready += 1
            if not r.axes[key]: isolated_detection[key] += 1
            roots.append(r.receipt_root)
    for _ in range(RANDOM_MULTI):
        e = valid_evidence(); t = terminal_for(e)
        for axis in sorted(rng.sample(range(1, 14), rng.randint(2, 5))): mutate(e, t, axis)
        r = g.evaluate_gate10_reviewer_admission(owner_lineage_root=OWNER, current_head_sha=HEAD, terminal=t, evidence=e)
        if r.decision is not g.Decision.HOLD: false_ready += 1
        roots.append(r.receipt_root)
    e = valid_evidence(); t = terminal_for(e)
    ready = g.evaluate_gate10_reviewer_admission(owner_lineage_root=OWNER, current_head_sha=HEAD, terminal=t, evidence=e)
    print(canonical({
        "seed": SEED, "mutants": 13 * SINGLE_PER_AXIS + RANDOM_MULTI,
        "isolated_per_axis": SINGLE_PER_AXIS, "random_multi": RANDOM_MULTI,
        "false_ready": false_ready, "valid_decision": ready.decision.value,
        "valid_axes": sum(ready.axes.values()), "isolated_axis_detection": isolated_detection,
        "campaign_root": sha256(canonical(roots).encode()).hexdigest(),
        "authority_minted": ready.authority_minted, "gate10": ready.gate10,
    }))


if __name__ == "__main__": main()
