from __future__ import annotations

from dataclasses import replace
from itertools import product
import hashlib
import json
import random

from successor_admission_gate import (
    AdmissionContext, ARENA_TERMINAL, Disposition, ParentArtifact,
    evaluate_successor_pair, independent_oracle, omega8_classify, thirteen_d_collapse,
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def fixture():
    ctx = AdmissionContext(
        current_actor_id="GPT56SOL-REPAIR-CELL",
        predecessor_artifact_id="O1-SHARED-MEMORY-FIREWALL",
        predecessor_cut="2026-09-06T00:16:36.186Z",
        evaluated_at="2026-09-06T00:50:00.000Z",
    )
    p1 = ParentArtifact(
        artifact_id="FOREIGN-A",
        actor_id="AGENT01",
        lineage_root=h("lineage-a"),
        created_at="2026-09-06T00:20:00.000Z",
        artifact_class=ARENA_TERMINAL,
        semantic_terminal=True,
        projection_of=None,
        consequence_axes=("semantic_domain", "admission_surface"),
        consequence_action="REPROVE_SEMANTIC_ADMISSION",
        invariant_delta="historical admission cannot imply current admission",
        receipt_root=h("receipt-a"),
        derivation_root=h("derivation-a"),
        model_id="model-a",
    )
    p2 = ParentArtifact(
        artifact_id="FOREIGN-B",
        actor_id="AGENT14",
        lineage_root=h("lineage-b"),
        created_at="2026-09-06T00:21:00.000Z",
        artifact_class=ARENA_TERMINAL,
        semantic_terminal=True,
        projection_of=None,
        consequence_axes=("external_authentication", "readjudication"),
        consequence_action="READJUDICATE_EXTERNAL_AUTH",
        invariant_delta="external auth cannot pay stale local semantic debt",
        receipt_root=h("receipt-b"),
        derivation_root=h("derivation-b"),
        model_id="model-b",
    )
    return ctx, p1, p2


def attacks():
    ctx, a, b = fixture()
    families = []
    for i in range(100):
        families.extend([
            (f"same-current-actor-{i}", [replace(a, actor_id=ctx.current_actor_id), b]),
            (f"same-parent-actor-{i}", [a, replace(b, actor_id=a.actor_id)]),
            (f"same-lineage-{i}", [a, replace(b, lineage_root=a.lineage_root)]),
            (f"pre-cut-{i}", [replace(a, created_at="2026-09-06T00:16:36.186Z"), b]),
            (f"future-date-{i}", [a, replace(b, created_at="2026-09-06T00:51:00.000Z")]),
            (f"projection-{i}", [replace(a, projection_of="some-arena-parent"), b]),
            (f"nonterminal-{i}", [a, replace(b, semantic_terminal=False)]),
            (f"same-effect-{i}", [a, replace(b, consequence_axes=a.consequence_axes, consequence_action=a.consequence_action, invariant_delta=a.invariant_delta)]),
            (f"same-receipt-{i}", [a, replace(b, receipt_root=a.receipt_root)]),
            (f"same-derivation-{i}", [a, replace(b, derivation_root=a.derivation_root)]),
        ])
    return ctx, families


def randomized_oracle(n=100_000, seed=5602):
    rnd = random.Random(seed)
    ctx, base_a, base_b = fixture()
    mismatches = 0
    dispositions = {d.value: 0 for d in Disposition}
    for i in range(n):
        a, b = base_a, base_b
        bits = [rnd.randrange(5) == 0 for _ in range(10)]
        if bits[0]: a = replace(a, actor_id=ctx.current_actor_id)
        if bits[1]: b = replace(b, actor_id=a.actor_id)
        if bits[2]: b = replace(b, lineage_root=a.lineage_root)
        if bits[3]: a = replace(a, created_at="2026-09-06T00:15:00.000Z")
        if bits[4]: b = replace(b, created_at="2026-09-06T00:51:00.000Z")
        if bits[5]: a = replace(a, projection_of="projection")
        if bits[6]: b = replace(b, semantic_terminal=False)
        if bits[7]: b = replace(b, consequence_axes=a.consequence_axes, consequence_action=a.consequence_action, invariant_delta=a.invariant_delta)
        if bits[8]: b = replace(b, receipt_root=a.receipt_root)
        if bits[9]: b = replace(b, derivation_root=a.derivation_root)
        got = evaluate_successor_pair([a, b], ctx).disposition
        want = independent_oracle([a, b], ctx)
        dispositions[got.value] += 1
        if got != want:
            mismatches += 1
    return {"n": n, "mismatches": mismatches, "dispositions": dispositions}


def omega8():
    counts = {d.value: 0 for d in Disposition}
    for state in product((0, 1, 2), repeat=8):
        counts[omega8_classify(state).value] += 1
    return counts


def thirteen_d():
    invalid_repairs = 0
    unresolved_repairs = 0
    for tail in product((0, 1, 2), repeat=5):
        if thirteen_d_collapse((0,2,2,2,2,2,2,2), tail) == Disposition.ELIGIBLE_TO_MINT_SUCCESSOR:
            invalid_repairs += 1
        if thirteen_d_collapse((1,2,2,2,2,2,2,2), tail) == Disposition.ELIGIBLE_TO_MINT_SUCCESSOR:
            unresolved_repairs += 1
    return {"tails": 3**5, "invalid_repairs": invalid_repairs, "unresolved_repairs": unresolved_repairs}


def run():
    ctx, family_cases = attacks()
    blocked = 0
    for _, parents in family_cases:
        if evaluate_successor_pair(parents, ctx).disposition != Disposition.ELIGIBLE_TO_MINT_SUCCESSOR:
            blocked += 1
    valid_ctx, a, b = fixture()
    valid = evaluate_successor_pair([a, b], valid_ctx)
    oracle = randomized_oracle()
    o8 = omega8()
    d13 = thirteen_d()
    summary = {
        "hs1000_cases": len(family_cases),
        "hs1000_blocked": blocked,
        "hs1000_false_admissions": len(family_cases)-blocked,
        "valid_pair_disposition": valid.disposition.value,
        "valid_pair_root": valid.pair_root,
        "valid_pair_k27": valid.k27_coordinate,
        "oracle": oracle,
        "omega8": o8,
        "13d": d13,
    }
    receipt = hashlib.sha256(json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    summary["campaign_receipt"] = receipt
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
