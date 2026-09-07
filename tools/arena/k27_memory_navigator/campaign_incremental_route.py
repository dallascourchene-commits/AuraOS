from __future__ import annotations

import hashlib
import json
import random

from .minimal_evidence import EvidenceMode, EvidenceWorld, compile_minimal_evidence
from .route_card_admission import (
    CapacityEnvelope, Polarity, ProofReceipt, RouteIdentity,
    TemporalRequirement, UseContext,
)
from .route_delta_planner import RouteChange, RouteSegment, plan_route_delta

H = "0" * 64
A = "1" * 64
B = "2" * 64


def identity(i=0, currentness=1, epoch=1):
    return RouteIdentity(H, f"target-{i}", A, B, "g", epoch, "boot", currentness, (i % 3,))


def envelope():
    return CapacityEnvelope(5, 5, 1, 2)


def temporal():
    return TemporalRequirement(1)


def receipt(i, negative=False):
    t = temporal()
    return ProofReceipt(
        Polarity.NEGATIVE if negative else Polarity.POSITIVE,
        identity(i), envelope(), t.mode, t.event_time,
        state_independent_negative=negative,
    )


def run(seed=8088, cases=20000):
    rng = random.Random(seed)
    oracle_mismatches = 0
    full_units = 0
    selected_units = 0
    evidence_adaptive = 0
    evidence_zero_disclosure = 0
    semantic_rows = []

    for _ in range(cases):
        count = rng.randint(3, 20)
        segments = []
        contexts = {}
        changed = {f"n{rng.randrange(count + 1)}"}
        if rng.random() < .25:
            changed.add(f"n{rng.randrange(count + 1)}")
        geometry_changed = rng.random() < .7
        for i in range(count):
            negative = rng.random() < .35
            segment = RouteSegment(
                f"s{i}", frozenset({f"n{i}", f"n{i+1}"}), receipt(i, negative))
            segments.append(segment)
            contexts[segment.segment_id] = UseContext(
                identity(i, 1 + int(rng.random() < .08), 1 + int(rng.random() < .03)),
                envelope(), temporal(),
            )
        change = RouteChange(frozenset(changed if geometry_changed else ()), geometry_changed)
        plan = plan_route_delta(segments, contexts, change, eager_threshold=.5)

        affected = [s.segment_id for s in segments
                    if geometry_changed and s.corridor_nodes & changed]
        expected = count if geometry_changed and len(affected) / count >= .5 else len(affected)
        if plan.geometry_recomputations != expected:
            oracle_mismatches += 1
        full_units += count
        selected_units += plan.geometry_recomputations

        if rng.random() < .1:
            worlds = [EvidenceWorld("a", "HOLD", (0, 0, 0)),
                      EvidenceWorld("b", "HOLD", (1, 1, 1))]
        else:
            worlds = [EvidenceWorld("a", "A", (0, 0, 0)),
                      EvidenceWorld("b", "B", (1, 0, 1)),
                      EvidenceWorld("c", "C", (1, 1, 0))]
        evidence = compile_minimal_evidence(
            worlds, [rng.randint(1, 5) for _ in range(3)],
            hard_premises_valid=(rng.random() > .02),
        )
        evidence_adaptive += evidence.mode is EvidenceMode.ADAPTIVE
        evidence_zero_disclosure += evidence.mode is EvidenceMode.ZERO_DISCLOSURE
        semantic_rows.append((
            plan.strategy.value, plan.geometry_recomputations,
            evidence.mode.value, evidence.worst_case_cost,
        ))

    root = hashlib.sha256(json.dumps(semantic_rows, separators=(",", ":")).encode()).hexdigest()
    result = {
        "cases": cases,
        "oracle_mismatches": oracle_mismatches,
        "full_geometry_units": full_units,
        "selected_geometry_units": selected_units,
        "modeled_reduction": 1 - selected_units / full_units,
        "evidence_adaptive": evidence_adaptive,
        "evidence_zero_disclosure": evidence_zero_disclosure,
        "campaign_root": root,
        "authority_minted": False,
        "effect_authority": False,
        "gate10": False,
    }
    if oracle_mismatches:
        raise AssertionError(result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
