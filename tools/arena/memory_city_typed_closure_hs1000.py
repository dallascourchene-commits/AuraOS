from __future__ import annotations

"""Deterministic MC-O9 HS1000 frontier generator.

The 1,000 raw entries are frozen candidate coordinates, not 1,000 proven
breakthroughs. Ranking/quotienting happens only after the raw set is frozen.
D0/non-promoting; no truth, execution, effect, merge, or Gate-10 authority.
"""
import hashlib
import json

BOUNDARIES = (
    "hard_support", "directed_influence", "support_currentness", "influence_currentness",
    "transition_model", "future_congruence", "hydration_budget", "reproof_scope",
    "k27_locality", "authority_cut",
)
FAILURES = (
    "support_only_underinvalidate", "symmetrized_union_overexpand", "stale_support_root",
    "stale_influence_root", "current_only_persistent_reuse", "incomplete_support",
    "incomplete_influence", "transition_drift", "k27_crosscast", "authority_crosscast",
)
MECHANISMS = (
    "typed_product", "exact_support_component", "directed_descendant_reproof",
    "support_identity_rebind", "influence_identity_rebind", "h0_exact_rebind",
    "horizon_congruence_certificate", "noncompensatory_hold", "counterexample_receipt",
    "separate_locality_accounting",
)


def h(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build() -> dict[str, object]:
    raw = []
    n = 0
    for boundary in BOUNDARIES:
        for failure in FAILURES:
            for mechanism in MECHANISMS:
                n += 1
                raw.append({
                    "id": f"MC-O9-HS-{n:04d}",
                    "boundary": boundary,
                    "failure": failure,
                    "mechanism": mechanism,
                    "status": "UNSCORED_AT_FREEZE",
                    "semantic_class": "CANDIDATE_NOT_BREAKTHROUGH",
                })
    freeze_root = h(raw)
    # Consequence quotient is deliberately defined only after raw freeze.
    groups = {}
    for row in raw:
        key = (row["boundary"], row["failure"])
        groups.setdefault(key, []).append(row["id"])
    quotients = [
        {"boundary": k[0], "failure": k[1], "members": tuple(v), "root": h(v)}
        for k, v in sorted(groups.items())
    ]
    # Ranking is stable but explicitly post-freeze; 27 is an experimental K27 lens.
    ranked = sorted(quotients, key=lambda q: h({"freeze_root": freeze_root, "q": q["root"]}))
    top27 = ranked[:27]
    return {
        "schema": "AURA-MEMORY-CITY-TYPED-CLOSURE-HS1000-v1",
        "raw_count": len(raw),
        "freeze_root": freeze_root,
        "quotient_count": len(quotients),
        "quotient_root": h(quotients),
        "top27_count": len(top27),
        "top27_root": h(top27),
        "candidate_semantics": "raw entries are frozen advancement candidates; none is promoted merely by enumeration",
        "authority": "D0_NONPROMOTING",
    }


if __name__ == "__main__":
    print(json.dumps(build(), sort_keys=True, separators=(",", ":")))
