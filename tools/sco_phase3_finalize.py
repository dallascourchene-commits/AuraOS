from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIED_HEAD = "15b3c26a3228a95174a845c75a178cf772cf5e81"
BASELINE = "7edd80484629378af0658bfca0d7d4e351361831"


def insert_before(path: str, marker: str, sentinel: str, block: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if sentinel not in text:
        if marker not in text:
            raise RuntimeError(f"missing marker {marker!r} in {path}")
        text = text.replace(marker, block.rstrip() + "\n\n" + marker, 1)
    target.write_text(text, encoding="utf-8")


def replace_optional(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old in text:
        target.write_text(text.replace(old, new, 1), encoding="utf-8")


COMMON = f"""Verified on source head `{VERIFIED_HEAD}`:

- exact Python 3.11 compile, fatal Ruff selection, and diff checks passed;
- `81/81` focused Phase 3 tests passed in `22.45s`;
- focused adapter/fixture/benchmark coverage was `88%`, with learning coverage at `82%`;
- `241/241` Construction and canonical-owner regressions passed in `10.53s`;
- the zero-model benchmark completed `250` candidate-order permutations;
- native Selective Council V3 selected the bounded Surgeon plan at score `0.99`;
- Architect verification recorded `16` checks, `0` failures, four exact-file leases, and Judge `promote_hotswap`;
- the Experience Ledger stored `15` unique seeded episodes from one fictional scenario and one objective;
- Crucible produced one `CRYSTALLIZATION_PROPOSED` candidate and did not mutate active grammar."""

README_BLOCK = f"""## SCO Construction advisory runtime

PR #148 adds the bounded Phase 3 E7–E11 Construction Arena vertical slice:

```text
ConstructionProjectState
  → exact evidence readiness
  → hard blockers before ranking
  → advisory probabilistic signal
  → cheapest / fastest / recommended / safest options
  → ActionCapsule + BoundaryContract + ArenaLease
  → verifier-backed proposal
  → human review
  → ArenaExperience V3
  → proposal-only Crucible
```

{COMMON}

This is synthetic/shadow software evidence, not a real-project or production-readiness claim. Provider tokens, provider cost, and real-project savings remain `NOT_MEASURED`. The runtime cannot authorize physical work, release payment, control access, certify safety or engineering, mutate authoritative records, or automatically promote grammar. See [`docs/evidence/AURA_SCO_PHASE3_E7_E11_VERIFICATION.json`](docs/evidence/AURA_SCO_PHASE3_E7_E11_VERIFICATION.json)."""

ARCHITECTURE_BLOCK = f"""## SCO Construction advisory runtime

The Construction Arena is a narrow adapter over canonical Construction, Liquid Planning, WFST, Experience, Crucible, and Architect owners. It does not create a second project truth store.

```text
immutable Construction events and claims
  → ConstructionProjectState replay
  → exact readiness and conflict checks
  → hard candidate filtering
  → advisory probabilistic signal
  → deterministic role-preserving option surface
  → Liquid Planning capsule, boundary, and lease
  → WFST evidence and verifier guards
  → proposal-only human decision packet
```

Architectural invariants:

- exact readiness, expiry, conflict, sensor-only, project-scope, and authority blockers run before probabilistic ranking;
- a high probabilistic score cannot rescue a blocked route;
- cheapest, fastest, recommended, and safest roles retain semantic ordering while exposing distinct admissible alternatives;
- runtime packets are read-only proposals and cannot mutate the Construction event chain;
- every route transition requires benchmark evidence and a passing verifier packet;
- Experience identity excludes wall-clock timing and replay is idempotent;
- the 15 episodes are one synthetic scenario and one objective, so no field generalization is claimed;
- Crucible may propose only `soft_weight_profile.empirical_uncertainty` and cannot promote active grammar;
- physical work, payment, access, professional certification, source mutation, commit, push, and merge remain outside runtime authority.

Primary files: `.aura/arena_routes/construction.v1.json`, `aura_construction_adapter.py`, `aura_construction_fixtures.py`, `aura_construction_benchmark.py`, `aura_construction_learning.py`, and `aura_construction_architect_refactor.py`.

{COMMON}"""

USER_GUIDE_BLOCK = f"""## SCO Construction advisory runtime

Run the deterministic fixture benchmark:

```bash
python3 aura_construction_benchmark.py --iterations 250 --seed 1337 --json
```

Run the governed synthetic learning projection:

```bash
python3 aura_construction_learning.py \\
  --repo-root . \\
  --output-dir Aura_Staging/sco_construction_phase3_learning \\
  --experience-count 15 \\
  --iterations-per-experience 25 \\
  --seed-base 1337
```

Run the native Council–Surgeon verification harness:

```bash
python3 aura_construction_architect_refactor.py \\
  --base-sha {BASELINE} \\
  --output-dir Aura_Staging/sco_construction_phase3_architect
```

{COMMON}

Interpret these as fictional deterministic and synthetic pipeline gates only. A `CRYSTALLIZATION_PROPOSED` result requires verifier and human review and does not change active grammar. All real physical-work, payment, access, safety, engineering, legal, and regulatory decisions remain with authorized humans and institutions."""

PLAN = f"""# SCO Construction Arena — Phase 3 E7–E11 Verification Record

```yaml
document_status: VERIFIED_PENDING_PINNED_FINAL_CI
document_version: 2.0.0
date: 2026-07-17
baseline_main: {BASELINE}
verified_source_head: {VERIFIED_HEAD}
branch: refactor/sco-construction-e7-e8
pull_request: 148
phase_scope:
  - E7_ADVISORY_LANES
  - E8_SYNTHETIC_SHADOW_ADAPTER
  - E10_EXPERIENCE_CRUCIBLE_PROJECTION
  - E11_ZERO_MODEL_BENCHMARK_ARM
coderabbit_invocations: 1
coderabbit_result: REVIEW_FINISHED_WITH_NO_SUBMITTED_REVIEW_OR_INLINE_THREADS
production_connectors: FORBIDDEN_IN_THIS_PHASE
private_project_data: FORBIDDEN_IN_THIS_PHASE
physical_work_authority: false
payment_release_authority: false
access_control_authority: false
professional_certification_authority: false
```

## Final architecture

```text
ConstructionProjectState
  → deterministic readiness
  → hard filtering
  → advisory ranking
  → role-preserving options
  → capsules, boundaries, and leases
  → WFST evidence/verifier guards
  → human proposal decision
  → ArenaExperience V3
  → TRAIN / VALIDATION / SHADOW
  → CRYSTALLIZATION_PROPOSED
  → verifier and human review
```

{COMMON}

## Incorporated hardening

The final sweep repaired scalar collection and unknown-field deserialization attacks, malformed runtime values, option-role ordering loss, cross-project scope mismatch, probabilistic override attempts, missing WFST evidence and verifier guards, benchmark tampering, wall-clock identity drift, unsafe Architect base/path/test boundaries, and the Python 3.11 `RefactorSkeleton` identity expression. Focused and owner regression tests cover these changes.

## Claim boundaries

The benchmark is zero-model and synthetic. Provider usage, provider cost, real-project savings, and production readiness are not measured. The 15 episodes are independent seeded executions of one fictional scenario, not 15 field projects. The Crucible distinct-objective threshold remains unmet and is preserved as a warning. Active grammar, hard guards, capabilities, source code, and authority are unchanged.

## Deferred by design

Human Agent API/UI wiring, Observatory projection, real owner/contractor/payment/access/sensor/safety integrations, external-model comparisons, and commercial field claims remain deferred.

## Final sequence

```text
verified source gates
  → synchronized README / ARCHITECTURE / USER_GUIDE / evidence
  → regenerated CODEMAP and topology
  → pinned-head final CI
  → mark PR ready
  → merge
  → post-merge verification
```
"""

EVIDENCE = {
    "version": "AURA_SCO_PHASE3_E7_E11_VERIFICATION_V1",
    "date": "2026-07-17",
    "repository": "dallascourchene-commits/AuraOS",
    "pull_request": 148,
    "baseline_main": BASELINE,
    "verified_source_head": VERIFIED_HEAD,
    "audit_run_id": 29594790717,
    "audit_artifact_id": 8412607621,
    "coderabbit": {
        "invocations": 1,
        "finished": True,
        "submitted_review": False,
        "inline_threads": 0,
        "invoke_again": False,
    },
    "tests": {
        "focused_collected": 81,
        "focused_passed": 81,
        "focused_elapsed_seconds": 22.45,
        "owner_regressions_passed": 241,
        "owner_regression_elapsed_seconds": 10.53,
    },
    "coverage_percent": {
        "focused_domain_total": 88,
        "adapter": 87,
        "benchmark": 90,
        "fixtures": 90,
        "learning": 82,
    },
    "benchmark": {
        "iterations": 250,
        "status": "PASS",
        "model_calls": 0,
        "provider_tokens": "NOT_MEASURED",
        "provider_cost": "NOT_MEASURED",
        "real_project_savings": "NOT_MEASURED",
        "production_readiness": "NOT_CLAIMED",
    },
    "architect": {
        "selected_plan_id": "SELECTIVE_COUNCIL_V3_SURGEON",
        "selected_plan_score": 0.99,
        "actual_model_calls": 0,
        "critic_lanes": ["scope", "tests", "sequence", "rollback", "cost"],
        "leases": 4,
        "staged_patches": 4,
        "verification_checks": 16,
        "verification_failures": 0,
        "judge_decision": "promote_hotswap",
        "human_review_required": True,
        "canonical_owner_modules_reused": 12,
        "parallel_truth_stores_added": 0,
        "production_connectors_added": 0,
    },
    "learning": {
        "episodes": 15,
        "iterations_per_episode": 25,
        "scenarios": 1,
        "objectives": 1,
        "unique_episode_digests": 15,
        "unique_evaluation_digests": 1,
        "unique_recommendations": 1,
        "ledger_records": 15,
        "crucible_candidates": 1,
        "crucible_proposals": 1,
        "terminal_status": "CRYSTALLIZATION_PROPOSED",
        "active_grammar_mutated": False,
        "all_proposal_thresholds_met": False,
        "distinct_objective_threshold_met": False,
        "generalization_claimed": False,
    },
    "dependency_repair": {
        "pull_request": 149,
        "merged": True,
        "identity_arguments_changed": False,
        "public_api_changed": False,
        "authority_boundary_changed": False,
    },
    "claim_boundaries": {
        "synthetic_only": True,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_control_authorized": False,
        "professional_certification_authorized": False,
        "active_grammar_mutated": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    },
}


def main() -> None:
    insert_before("README.md", "## Truth and authority", "## SCO Construction advisory runtime", README_BLOCK)
    replace_optional(
        ".aura/ARCHITECTURE.md",
        "**Architecture audit:** through merged PR #133 and the canonical Human Agent, Observatory, and Crucible documentation sync.  ",
        "**Architecture audit:** through SCO Construction Phase 3 E7–E11 verification in PR #148 and the canonical Human Agent, Observatory, Experience, Crucible, Council, and Surgeon boundaries.  ",
    )
    insert_before(
        ".aura/ARCHITECTURE.md",
        "## 7. Benchmark evidence hierarchy",
        "## SCO Construction advisory runtime",
        ARCHITECTURE_BLOCK,
    )
    replace_optional(
        "USER_GUIDE.md",
        "**Documentation audit:** through merged PR #133 and the canonical Human Agent, Observatory, and Crucible documentation sync.  ",
        "**Documentation audit:** through SCO Construction Phase 3 E7–E11 verification in PR #148 and the canonical Human Agent, Observatory, Experience, Crucible, Council, and Surgeon documentation sync.  ",
    )
    insert_before(
        "USER_GUIDE.md",
        "## 10. Cost and benchmark interpretation",
        "## SCO Construction advisory runtime",
        USER_GUIDE_BLOCK,
    )
    (ROOT / "docs/AURA_SCO_PHASE3_E7_E8_EXECUTION_PLAN.md").write_text(PLAN, encoding="utf-8")
    evidence_path = ROOT / "docs/evidence/AURA_SCO_PHASE3_E7_E11_VERIFICATION.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(EVIDENCE, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
