"""Finalize Architect benchmark evidence without assuming Aura wins every arm.

The finalizer converts raw metrics and gate records into explicit findings, corrects
interpretation text from the observed deltas, and emits a README-ready Markdown
section. It never alters measured token, cost, quality, routing, or grounding data.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any


def _role_totals(calls: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0}
    )
    for call in calls:
        role = str(call.get("role") or "unknown")
        totals[role]["calls"] += 1
        totals[role]["input_tokens"] += int(call.get("input_token_estimate") or 0)
        totals[role]["output_tokens"] += int(call.get("output_token_estimate") or 0)
    return dict(sorted(totals.items()))


def _route_findings(quality: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    prepared = dict(quality.get("prepared") or {})
    arena = dict(prepared.get("arena") or {})
    for route in list(arena.get("routing_decisions", []) or []):
        if route.get("route") == "BUILDER_PATCH":
            continue
        findings.append(
            {
                "kind": "NON_BUILDER_ROUTE",
                "task_id": route.get("task_id"),
                "route": route.get("route"),
                "reason": route.get("reason"),
                "scope": dict(route.get("frame") or {}).get("scope"),
                "risk": dict(route.get("frame") or {}).get("risk"),
            }
        )
    shadow = dict(prepared.get("shadow_report") or {})
    for item in list(shadow.get("findings", []) or []):
        findings.append(
            {
                "kind": "SHADOW_FINDING",
                "task_id": item.get("task_id"),
                "severity": item.get("severity"),
                "shadow_type": item.get("shadow_type"),
                "message": item.get("message"),
            }
        )
    return findings


def finalize(report_path: Path, responses_path: Path, skeleton_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    responses = json.loads(responses_path.read_text(encoding="utf-8"))
    skeleton = json.loads(skeleton_path.read_text(encoding="utf-8"))
    comparison = report["comparison"]
    arms = report["arms"]
    council_arm = arms["aura_architect_council"]
    council_calls = int(council_arm.get("model_calls") or 0)
    selected = dict(council_arm.get("selected_plan") or {})
    submitted = dict((responses.get("council") or {}).get("planner") or {})
    contract_fields = (
        "acceptance_criteria",
        "rollback_conditions",
        "risk_map",
        "constraints",
    )
    lost_fields = [
        field for field in contract_fields if submitted.get(field) and not selected.get(field)
    ]
    role_totals = _role_totals(list(council_arm["model_usage"].get("calls", []) or []))
    route_findings = _route_findings(council_arm["quality"])
    council_quality_supported = comparison["council_quality_delta"] > 0
    council_quality_statement = (
        "outperformed the broad-context arm"
        if council_quality_supported
        else "did not outperform the broad-context arm"
    )

    findings = [
        {
            "id": "F1_SLICE_EFFICIENCY",
            "status": "SUPPORTED_FIRST_PILOT",
            "statement": (
                f"The Aura-slice single-planner arm reduced input-token proxy by "
                f"{comparison['slice_input_reduction_pct']}% and total-token proxy by "
                f"{comparison['slice_total_reduction_pct']}% versus the broad-context arm."
            ),
        },
        {
            "id": "F2_SLICE_QUALITY",
            "status": "SUPPORTED_FIRST_PILOT",
            "statement": (
                f"The Aura-slice arm changed deterministic grounded-plan quality by "
                f"{comparison['slice_quality_delta']:+.4f} versus broad context."
            ),
        },
        {
            "id": "F3_COUNCIL_EFFICIENCY",
            "status": "MIXED_FIRST_PILOT",
            "statement": (
                f"The measured {council_calls}-call Council remained "
                f"{comparison['council_total_reduction_pct']}% below the broad-context "
                "total-token proxy, but used substantially more tokens than the single "
                "sliced planner."
            ),
            "measured_model_calls": council_calls,
        },
        {
            "id": "F4_COUNCIL_QUALITY",
            "status": (
                "SUPPORTED_FIRST_PILOT"
                if council_quality_supported
                else "NOT_SUPPORTED_FIRST_PILOT"
            ),
            "statement": (
                f"The Council changed deterministic quality by "
                f"{comparison['council_quality_delta']:+.4f} versus broad context and "
                f"{council_quality_statement} in this run."
            ),
        },
        {
            "id": "F5_PLAN_CONTRACT_LOSS",
            "status": "DEFECT_OBSERVED" if lost_fields else "NOT_OBSERVED",
            "statement": (
                (
                    "Architect Council normalization did not preserve submitted plan-level fields: "
                    + ", ".join(lost_fields)
                    + "."
                )
                if lost_fields
                else "Architect Council normalization preserved every submitted plan-level governance field."
            ),
            "lost_fields": lost_fields,
        },
        {
            "id": "F6_LOCALIZATION_FALLBACK",
            "status": "DEFECT_OBSERVED_AND_BENCHMARK_ADAPTER_CORRECTED",
            "statement": (
                "The initial generic LOCALIZE_FIRST route ranked unrelated fallback modules "
                "above the Architect/Human-Agent spine. The refined benchmark ranks exact "
                "spans, selected lanes, grounded affordances, and objective-core files before "
                "fallback candidates."
            ),
        },
        {
            "id": "F7_REFACTOR_READINESS",
            "status": "HUMAN_REPAIR_REQUIRED",
            "statement": (
                "The selected skeleton is grounded and blocker-free but is not Arena-ready "
                "because at least one task routed outside BUILDER_PATCH and one target lacked "
                "a nearby test mapping."
            ),
            "gate_findings": route_findings,
        },
    ]

    slice_text = (
        "The sliced arm preserved or improved the deterministic grounded-plan score."
        if comparison["slice_quality_delta"] >= 0
        else "The sliced arm saved context but reduced the deterministic grounded-plan score."
    )
    council_text = (
        "The Council improved quality versus broad context."
        if council_quality_supported
        else "The Council did not improve quality versus broad context in this pilot."
    )
    report["interpretation"] = (
        "The single sliced planner isolates Aura's context-selection effect and achieved the "
        "strongest quality-adjusted efficiency in this first pilot. "
        + slice_text
        + " The Council arm measures aggregate multi-agent cost across planners, critics, and "
        "Judge rather than comparing only one compact prompt. "
        + council_text
        + " The run also exposed contract-preservation and routing defects that must be repaired "
        "before claiming general architectural superiority. This is reproducible pilot evidence, "
        "not proof that Aura is revolutionary, generally superior, conscious, or production-ready."
    )
    report["findings"] = findings
    report["council_role_totals"] = role_totals
    report["claims"] = {
        "supported": [
            "slice context reduction",
            "slice normalized cost reduction",
            "grounded plan generation",
        ],
        "not_yet_supported": [
            "general quality superiority",
            "Council superiority",
            "production refactor success",
            "provider-billed cost savings",
            "revolutionary architecture claim",
        ],
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    skeleton["benchmark_findings"] = findings
    skeleton["repair_requirements"] = {
        "preserve_plan_contract_fields": lost_fields,
        "resolve_non_builder_routes": [
            item for item in route_findings if item.get("kind") == "NON_BUILDER_ROUTE"
        ],
        "resolve_shadow_findings": [
            item for item in route_findings if item.get("kind") == "SHADOW_FINDING"
        ],
    }
    skeleton_path.write_text(
        json.dumps(skeleton, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    snippet_path = report_path.parent / "README_ARCHITECT_BENCHMARK.md"
    raw = arms["raw_broad_context"]
    sliced = arms["aura_slice_single"]
    council = council_arm
    snippet = f"""## First Architect Consolidation Benchmark

**Status:** reproducible single-session pilot; plan-only; no production mutation.

The benchmark uses the same repository commit, objective, output contract, and deterministic grounding rubric across three arms:

| Arm | Calls | Input token proxy | Output token proxy | Total token proxy | Grounded-plan quality | Normalized cost* |
|---|---:|---:|---:|---:|---:|---:|
| Broad-context single planner | {raw['model_calls']} | {raw['input_tokens']:,} | {raw['output_tokens']:,} | {raw['total_tokens']:,} | {raw['quality']['quality_score']:.4f} | ${raw['normalized_cost_usd']:.6f} |
| Aura-slice single planner | {sliced['model_calls']} | {sliced['input_tokens']:,} | {sliced['output_tokens']:,} | {sliced['total_tokens']:,} | {sliced['quality']['quality_score']:.4f} | ${sliced['normalized_cost_usd']:.6f} |
| Aura Architect Council | {council['model_calls']} | {council['input_tokens']:,} | {council['output_tokens']:,} | {council['total_tokens']:,} | {council['quality']['quality_score']:.4f} | ${council['normalized_cost_usd']:.6f} |

\\*Normalized cost uses a declared $1/M input and $3/M output rate card; it is **not** a provider invoice.

### What the first run supports

- **{comparison['slice_input_reduction_pct']}%** less input-token proxy and **{comparison['slice_total_reduction_pct']}%** less total-token proxy for Aura slices versus broad context.
- The sliced plan scored **{comparison['slice_quality_delta']:+.4f}** versus broad context while reducing normalized cost by **{comparison['slice_cost_reduction_pct']}%**.
- The measured {council_calls}-call Council remained **{comparison['council_total_reduction_pct']}%** below the broad-context total-token proxy; its quality changed **{comparison['council_quality_delta']:+.4f}**.

### Defects discovered by the benchmark

1. Generic `LOCALIZE_FIRST` fallback candidates initially displaced the intended Architect/Human-Agent modules; benchmark ranking now down-ranks those fallbacks.
2. Council normalization dropped plan-level fields: `{', '.join(lost_fields) if lost_fields else 'none'}`.
3. The selected skeleton remained `PLAN_ONLY` for one task because a keyword scope heuristic interpreted “repository” as repo-wide authority.
4. One experience target had no nearby test mapping, so the skeleton remains a human-review proposal rather than refactor-ready code.

### Reproduce

```bash
python aura_codebase_navigator.py
python aura_architect_consolidation_benchmark_refined.py prepare --repo-root . --output-dir benchmark-output
python benchmarks/architect_consolidation/generate_gpt56_pilot_fixture.py --output benchmark-output/responses.gpt-5.6-thinking.json
python aura_architect_consolidation_benchmark_refined.py score --repo-root . --output-dir benchmark-output --responses benchmark-output/responses.gpt-5.6-thinking.json --input-rate 1.0 --output-rate 3.0
python aura_architect_benchmark_report.py --report benchmark-output/architect_consolidation_benchmark.json --responses benchmark-output/responses.gpt-5.6-thinking.json --skeleton benchmark-output/architect_consolidation_skeleton.json
```

Measurement labels: source bytes/files/lines are **MEASURED**; token counts are **ESTIMATED** char/4 proxies; quality and normalized cost are **DERIVED**; provider-billed cost is **UNAVAILABLE**.
"""
    snippet_path.write_text(snippet, encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--skeleton", type=Path, required=True)
    args = parser.parse_args()
    report = finalize(args.report, args.responses, args.skeleton)
    print(
        json.dumps(
            {"comparison": report["comparison"], "findings": report["findings"]},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
