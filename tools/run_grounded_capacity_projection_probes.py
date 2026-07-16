#!/usr/bin/env python3
"""Run new-capacity projections against exact AuraOS file targets.

The first probe suite intentionally exercised role-like `combine_with` values and
confirmed that the API fails closed when no exact file is resolved. This suite
uses the documented exact-file contract so the proposed capacities are ranked
against grounded local symbols.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aura_emergent_potential_repl import _repo_python_sources, audit_emergent_potential  # noqa: E402
from aura_topological_context_anchor import CodeTopoAnchor  # noqa: E402


PROBES: list[dict[str, Any]] = [
    {
        "id": "G01_EVIDENCE_BACKED_CAPABILITY_FOUNDRY",
        "focus": "Create a repeatable capacity-development pipeline from desired outcome to grounded design, research evidence, executable tests, empirical benchmarks, and human approval.",
        "new": "Evidence-Backed Capability Foundry: convert a desired task into capability atoms, research requirements, exact architecture targets, missing wires, failing tests, bounded implementation capsules, empirical trials, safety and cost gates, and a human-approved release decision.",
        "with": [
            "aura_emergent_potential_repl.py",
            "aura_emergent_result_verifier.py",
            "aura_research_manifest.py",
            "aura_empirical_software_lab.py",
            "aura_coding_arena_grounding.py",
            "aura_architect_loop.py",
            "aura_capsule_trial_runner.py",
            "aura_topological_context_anchor.py",
        ],
    },
    {
        "id": "G02_ARXIV_ENGINEERING_SYNTHESIZER",
        "focus": "Create an exact, low-noise research-to-engineering capability using canonical arXiv metadata, sidecar extraction, claim provenance, novelty clustering, contradiction checks, and local benchmarks.",
        "new": "arXiv Engineering Synthesizer: use official arXiv metadata as identity truth, sidecars for full-text and claim extraction, version-aware provenance, semantic novelty and contradiction clustering, implementation-lesson manifests, and empirical local verification before recommending engineering changes.",
        "with": [
            "arxiv_forager.py",
            "aura_paper_memory.py",
            "aura_scientific_memory.py",
            "aura_research_manifest.py",
            "aura_research_cockpit_adapter.py",
            "aura_coding_research_lane.py",
            "aura_empirical_software_lab.py",
        ],
    },
    {
        "id": "G03_HUMAN_AGENT_CO_DEVELOPMENT_CONDUCTOR",
        "focus": "Create a human-agent architecture conductor that exposes assumptions and disagreements, asks only high-leverage human decisions, and executes bounded verified coding sessions.",
        "new": "Human-Agent Co-Development Conductor: translate operator goals into topology-grounded work packets, solicit competing agent plans, surface assumptions and disagreements, route high-leverage decisions to the human, compile the selected plan into bounded coding sessions, and verify the result against the original goal.",
        "with": [
            "aura_human_agent_arena_server.py",
            "aura_coding_arena_grounding.py",
            "aura_agent_arena_cli.py",
            "aura_architect_loop.py",
            "aura_capsule_trial_runner.py",
            "aura_route_capsule_compiler.py",
            "aura_repo_localizer.py",
        ],
    },
    {
        "id": "G04_COMMUNITY_GOVERNED_CIVIC_INTERVENTION_ENGINE",
        "focus": "Create a reliable community-governed system for comparing, consenting to, deploying, and evaluating civic interventions under uncertainty.",
        "new": "Community-Governed Civic Intervention Engine: represent authority, consent, needs, assets, causal assumptions, dissent, risk and uncertainty; compare pathways; define community-approved outcome measures; stage reversible pilots; and update plans only from auditable evidence.",
        "with": [
            "aura_civic_runtime.py",
            "aura_civic_planning.py",
            "aura_civic_map.py",
            "aura_civic_planning_inventory.py",
            "aura_civic_cost_integration.py",
            "aura_civic_guided_steps.py",
            "aura_empirical_software_lab.py",
        ],
    },
    {
        "id": "G05_VERIFIED_SELF_HEALING_ENGINEERING_LOOP",
        "focus": "Create bounded self-healing engineering without autonomous merge authority.",
        "new": "Verified Self-Healing Engineering Loop: detect regressions, localize likely faults, retrieve exact source spans, generate diverse constrained repairs, run deterministic tests and benchmarks, compare behavioral and cost deltas, support rollback, and require explicit human approval before repository writes or merge.",
        "with": [
            "aura_repo_localizer.py",
            "aura_topological_context_anchor.py",
            "aura_coding_arena_grounding.py",
            "aura_capsule_variant_generator.py",
            "aura_capsule_trial_runner.py",
            "aura_live_architect.py",
            "aura_emergent_result_verifier.py",
        ],
    },
    {
        "id": "G06_ARXIV_SIGNAL_BUDGET_CONTROLLER",
        "focus": "Maximize useful paper coverage while bounding duplicate, low-relevance, unsupported, and context-expensive research noise.",
        "new": "arXiv Signal-Budget Controller: separate canonical metadata harvesting from expensive full-text processing; deduplicate by arXiv identity and version; rank papers by task relevance, novelty, evidence quality and implementation value; allocate sidecar and model budgets adaptively; and stop retrieval when marginal information gain falls below cost.",
        "with": [
            "arxiv_forager.py",
            "aura_paper_memory.py",
            "aura_scientific_memory.py",
            "aura_research_manifest.py",
            "aura_research_cockpit_adapter.py",
            "aura_model_router_scorecard.py",
        ],
    },
    {
        "id": "G07_CAPABILITY_RESEARCH_BENCHMARK_LOOP",
        "focus": "Use scientific literature to create genuinely better Aura capacities without treating paper claims as implementation truth.",
        "new": "Capability Research Benchmark Loop: formulate a capability hypothesis, retrieve and triangulate primary research, translate each claim into falsifiable engineering requirements, generate multiple architectural candidates, benchmark against Aura's current baseline and external baselines, run ablations, reject unsupported novelty, and retain only reproducible improvements.",
        "with": [
            "aura_emergent_potential_repl.py",
            "arxiv_forager.py",
            "aura_research_manifest.py",
            "aura_empirical_software_lab.py",
            "aura_coding_research_lane.py",
            "aura_capsule_trial_runner.py",
            "aura_emergent_result_verifier.py",
        ],
    },
]


def connection_target(candidate: dict[str, Any]) -> str:
    target = candidate.get("target", {}) or {}
    return f"{target.get('file', '')}:{target.get('symbol', '')}"


def main() -> int:
    output_dir = REPO_ROOT / "artifacts" / "grounded_capacity_projection_probes"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = _repo_python_sources(REPO_ROOT)
    anchor = CodeTopoAnchor.build_from_files(sources)
    results: list[dict[str, Any]] = []
    failures = 0

    for probe in PROBES:
        item = dict(probe)
        try:
            report = audit_emergent_potential(
                anchor,
                top=12,
                focus=probe["focus"],
                new_function_description=probe["new"],
                combine_with=probe["with"],
            )
            item["report"] = report.to_dict()
        except Exception as exc:
            failures += 1
            item["error"] = f"{type(exc).__name__}: {exc}"
        results.append(item)

    payload = {
        "suite_version": "AURA_GROUNDED_CAPACITY_PROJECTIONS_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_head": "624a8afefe1824ef070f4684bcc7dc4195542162",
        "python_file_count": len(sources),
        "topology_node_count": len(anchor.nodes),
        "topology_edge_count": len(anchor.edges),
        "probe_count": len(PROBES),
        "failure_count": failures,
        "results": results,
    }

    lines = [
        "# AuraOS Grounded New-Capacity Projection Report",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Repository head: {payload['repository_head']}",
        f"- Probes: {payload['probe_count']}",
        f"- Failures: {payload['failure_count']}",
        "",
    ]
    for item in results:
        lines.extend([f"## {item['id']}", "", f"- Proposed capacity: {item['new']}"])
        if item.get("error"):
            lines.extend([f"- ERROR: `{item['error']}`", ""])
            continue
        report = item["report"]
        summary = report["summary"]
        lines.append(
            f"- Candidates: {summary.get('candidate_unwired_connections', 0)}; "
            f"future-patchable: {summary.get('future_patchable', 0)}; "
            f"needs-grounding: {summary.get('needs_grounding', 0)}; "
            f"too-risky: {summary.get('too_risky', 0)}"
        )
        lines.append(f"- Verifier: {report.get('verifier_summary', '')}")
        lines.extend(["", "| Rank | Score | Status | Grounded target |", "|---:|---:|---|---|"])
        for rank, candidate in enumerate(report.get("connections", []), start=1):
            lines.append(
                f"| {rank} | {float(candidate.get('emergence_score', 0.0)):.4f} | "
                f"{candidate.get('status', '')} | {connection_target(candidate).replace('|', chr(92) + '|')} |"
            )
        lines.append("")

    json_path = output_dir / "grounded_capacity_projections.json"
    md_path = output_dir / "grounded_capacity_projection_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md_path.read_text(encoding="utf-8"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
