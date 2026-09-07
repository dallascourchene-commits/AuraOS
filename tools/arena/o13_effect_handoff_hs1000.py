from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "arena"))

from campaign_memory_city_effect_handoff_o13 import oracle_matches, scenario
from memory_city_effect_handoff_o13 import compile_effect_handoff, digest

BOUNDARIES = (
    "read_semantics", "read_at_t1", "coverage", "admission", "lease_identity",
    "fence_install", "owner_evidence", "verifier_evidence", "authority", "tecc_route",
)
CLASSES = (
    "valid", "stale", "substituted", "malformed", "legacy",
    "aba", "missing", "contradictory", "expired", "context_only",
)
MECHANISMS = (
    "identity", "receipt", "root", "generation", "epoch",
    "holder", "expiry", "mode", "semantic_version", "authority_flag",
)


def frozen_cells():
    cells = []
    for boundary in BOUNDARIES:
        for consequence_class in CLASSES:
            for mechanism in MECHANISMS:
                cells.append({
                    "boundary": boundary,
                    "consequence_class": consequence_class,
                    "mechanism": mechanism,
                    "expected_gain": "UNSCORED_AT_FREEZE",
                })
    return cells


def run():
    cells = frozen_cells()
    freeze_root = digest(cells)
    results = []
    groups = {}
    oracle_mismatches = 0
    by_mode = {str(i): {"cells": 0, "oracle_mismatches": 0} for i in range(8)}
    for index, cell in enumerate(cells):
        # Exercise the implementation-backed eight-scenario falsifier while the
        # 10x10x10 grid remains a search geometry, not a breakthrough count.
        cert, kwargs, expected_disposition, expected_reason, mode = scenario(index)
        decision = compile_effect_handoff(cert, **kwargs)
        consequence = (decision.disposition.value, decision.reason)
        exact = oracle_matches(decision, expected_disposition, expected_reason)
        if not exact:
            oracle_mismatches += 1
            by_mode[str(mode)]["oracle_mismatches"] += 1
        by_mode[str(mode)]["cells"] += 1
        results.append({
            "cell": cell,
            "mode": mode,
            "expected_disposition": expected_disposition.value,
            "expected_reason": expected_reason,
            "consequence": consequence,
            "oracle_match": exact,
        })
        groups.setdefault(consequence, 0)
        groups[consequence] += 1
    quotient_rows = sorted((list(key), count) for key, count in groups.items())
    payload = {
        "schema": "AURA-MEMORY-CITY-O13-HS1000-v2-EXACT-ORACLE",
        "raw_challenge_cells": len(cells),
        "claim_breakthroughs": 0,
        "freeze_root": freeze_root,
        "observed_consequence_groups": len(groups),
        "oracle_mismatches": oracle_mismatches,
        "by_mode": by_mode,
        "quotient_rows": quotient_rows,
        "result_root": digest(results),
    }
    payload["quotient_root"] = digest(quotient_rows)
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
