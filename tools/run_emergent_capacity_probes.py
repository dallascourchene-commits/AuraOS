#!/usr/bin/env python3
"""Run a reproducible, read-only emergent-capacity probe suite against AuraOS.

This is an analysis harness only. It imports Aura's merged emergent-potential
implementation, builds one topology anchor from the repository, and executes
multiple independent discovery and new-capacity projection probes.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aura_emergent_potential_repl import (  # noqa: E402
    _repo_python_sources,
    audit_emergent_potential,
)
from aura_topological_context_anchor import CodeTopoAnchor  # noqa: E402


PROBES: list[dict[str, Any]] = [
    {
        "id": "P01_HIGH_LEVERAGE_UNWIRED",
        "mode": "discover",
        "focus": "Find unwired abilities which can be high leverage if united. Prioritize exact local evidence, verifier readiness, token reduction, and low-risk missing wires.",
    },
    {
        "id": "P02_CODING_HUMAN_AGENT_ARENA",
        "mode": "discover",
        "focus": "Find ways to enhance the Coding Arena and Human Agent Arena so humans and coding agents can coordinate, inspect topology, challenge plans, compare candidates, verify outcomes, and safely hand off work.",
    },
    {
        "id": "P03_CIVIC_ARENA_RELIABILITY",
        "mode": "discover",
        "focus": "Optimize the Civic Arena and make it more effective, evidence-grounded, auditable, reliable, community-controlled, and able to measure whether interventions actually improve outcomes.",
    },
    {
        "id": "P04_ARXIV_FORAGER_EXACT_TRUTH",
        "mode": "discover",
        "focus": "Make the arXiv forager more efficient: maximize useful scientific data without noise overload, use sidecars and the arXiv API for exact metadata truth, deduplicate papers, preserve provenance, and route only high-value findings into engineering.",
    },
    {
        "id": "P05_TOKEN_ENERGY_EXACTNESS",
        "mode": "discover",
        "focus": "Reduce token, memory, communication, and energy cost while preserving exact source grounding, deterministic verification, and high-quality reasoning across model routing and agent workflows.",
    },
    {
        "id": "P06_RESEARCH_TO_EMPIRICAL_ENGINEERING",
        "mode": "discover",
        "focus": "Find missing wires that turn research manifests, papers, hypotheses, acceptance tests, empirical software lab tasks, benchmarks, and local test runners into a closed evidence-to-engineering loop.",
    },
    {
        "id": "P07_CONTINUAL_LEARNING_WITHOUT_DRIFT",
        "mode": "discover",
        "focus": "Find a safe way for Aura to learn from arena outcomes, verifier traces, failed attempts, operator corrections, and benchmark deltas without silent behavioral drift or unbounded memory growth.",
    },
    {
        "id": "P08_EXTERNAL_CODING_AGENT_SAFETY",
        "mode": "discover",
        "focus": "Improve external coding-agent sessions with exact context leasing, capability boundaries, budget enforcement, disagreement handling, rollback, reproducibility, and proof that the final result matches the requested task.",
    },
    {
        "id": "P09_INDIGENOUS_CIVIC_GOVERNANCE",
        "mode": "discover",
        "focus": "Strengthen the Civic Arena for Indigenous-led governance: community authority, consent, local knowledge, transparent evidence, restorative pathways, measurable outcomes, and protection against extractive or externally imposed optimization.",
    },
    {
        "id": "P10_FEDERATED_ARENAS",
        "mode": "discover",
        "focus": "Find unwired capacities created by federating Coding, Human Agent, Civic, Research, Planning, and Empirical Arenas while keeping authority, evidence, and costs explicit at every handoff.",
    },
    {
        "id": "P11_CAPABILITY_FOUNDRY",
        "mode": "project",
        "focus": "Design a capacity-creation workflow that begins with a desired task and ends with a tested, documented, bounded Aura capability.",
        "new": "An Evidence-Backed Capability Foundry that decomposes a requested outcome into capability atoms, retrieves relevant research, maps research claims to local architecture, proposes missing wires, compiles deterministic action capsules, runs empirical benchmarks, verifies safety and cost, and only then presents a human-approved implementation plan.",
        "with": ["research_manifest", "empirical_lab", "coding_arena", "capsule_compiler", "test_runner", "topology", "memory"],
    },
    {
        "id": "P12_ARXIV_ENGINEERING_SYNTHESIZER",
        "mode": "project",
        "focus": "Create a research system that can discover engineering ideas beyond current implementations without confusing novelty with truth.",
        "new": "An arXiv Engineering Synthesizer that uses the arXiv API as canonical metadata, sidecars for full-text extraction and claim indexing, citation and version provenance, novelty clustering, contradiction detection, implementation-lesson manifests, and empirical local benchmarks before any paper-derived idea is trusted.",
        "with": ["research_manifest", "external_api", "memory", "model_router", "empirical_lab", "test_runner"],
    },
    {
        "id": "P13_HUMAN_AGENT_CO_DEVELOPMENT",
        "mode": "project",
        "focus": "Create a new human-agent co-development capacity where the operator can steer architecture at high leverage without micromanaging code.",
        "new": "A Human-Agent Co-Development Conductor that turns human goals into topology-grounded work packets, lets multiple agents propose competing plans, exposes assumptions and disagreements in the Human Agent Arena, asks the operator only high-leverage decisions, and converts the selected plan into bounded verified coding sessions.",
        "with": ["coding_arena", "model_router", "capsule_compiler", "test_runner", "memory", "topology", "localizer"],
    },
    {
        "id": "P14_CIVIC_INTERVENTION_ENGINE",
        "mode": "project",
        "focus": "Create a trustworthy capacity for designing and evaluating civic interventions before real-world deployment.",
        "new": "A Community-Governed Civic Intervention Engine that represents stakeholder authority, needs, resources, causal assumptions, risks, and consent; compares intervention pathways; records dissent; simulates uncertainty; defines measurable community-approved outcomes; and updates plans only from auditable evidence.",
        "with": ["memory", "empirical_lab", "test_runner", "model_router", "external_api"],
    },
    {
        "id": "P15_SELF_HEALING_ENGINEERING",
        "mode": "project",
        "focus": "Create a bounded self-healing engineering capacity without granting uncontrolled patch authority.",
        "new": "A Verified Self-Healing Engineering Loop that detects regressions, localizes likely faults, retrieves exact topology spans, generates several constrained repair candidates, runs deterministic tests and benchmarks, compares cost and behavior deltas, supports hot-swap rollback, and requires explicit human approval for repository changes.",
        "with": ["localizer", "topology", "coding_arena", "capsule_compiler", "test_runner", "hotswap", "memory", "model_router"],
    },
]


def connection_key(connection: dict[str, Any]) -> str:
    source = connection.get("source", {}) or {}
    target = connection.get("target", {}) or {}
    return (
        f"{source.get('file', '')}:{source.get('symbol', '')}"
        f" -> {target.get('file', '')}:{target.get('symbol', '')}"
    )


def render_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# AuraOS Emergent Capacity Probe Report")
    lines.append("")
    lines.append(f"- Generated: {payload['generated_at']}")
    lines.append(f"- Repository head: {payload['repository_head']}")
    lines.append(f"- Python files scanned: {payload['python_file_count']}")
    lines.append(f"- Topology nodes: {payload['topology_node_count']}")
    lines.append(f"- Topology edges: {payload['topology_edge_count']}")
    lines.append(f"- Probes executed: {payload['probe_count']}")
    lines.append(f"- Probe failures: {payload['failure_count']}")
    lines.append("")
    lines.append("## Cross-Probe Recurrence")
    lines.append("")
    lines.append("Candidates that recur across independent prompts are the strongest evidence that the opportunity is architectural rather than prompt-specific.")
    lines.append("")
    lines.append("| Rank | Occurrences | Best score | Statuses | Missing connection | Emergent ability |")
    lines.append("|---:|---:|---:|---|---|---|")
    for index, item in enumerate(payload["recurring_candidates"][:25], start=1):
        statuses = ", ".join(item["statuses"])
        ability = str(item["emergent_ability"]).replace("|", "\\|")
        key = str(item["connection"]).replace("|", "\\|")
        lines.append(
            f"| {index} | {item['occurrences']} | {item['best_score']:.4f} | {statuses} | {key} | {ability} |"
        )
    lines.append("")
    lines.append("## Probe Results")
    for result in payload["results"]:
        lines.append("")
        lines.append(f"### {result['id']}")
        lines.append("")
        lines.append(f"- Mode: {result['mode']}")
        lines.append(f"- Focus: {result['focus']}")
        if result.get("new"):
            lines.append(f"- Proposed capacity: {result['new']}")
            lines.append(f"- Requested components: {', '.join(result.get('with', []))}")
        if result.get("error"):
            lines.append(f"- ERROR: `{result['error']}`")
            continue
        summary = result["report"]["summary"]
        lines.append(
            "- Summary: "
            f"abilities={summary.get('total_abilities_scanned', 0)}, "
            f"candidates={summary.get('candidate_unwired_connections', 0)}, "
            f"future_patchable={summary.get('future_patchable', 0)}, "
            f"needs_grounding={summary.get('needs_grounding', 0)}, "
            f"too_risky={summary.get('too_risky', 0)}"
        )
        verifier_summary = result["report"].get("verifier_summary")
        if verifier_summary:
            lines.append(f"- Verifier: {verifier_summary}")
        lines.append("")
        lines.append("| Rank | Score | Status | Missing wire | Emergent ability |")
        lines.append("|---:|---:|---|---|---|")
        for rank, candidate in enumerate(result["report"].get("connections", [])[:12], start=1):
            key = connection_key(candidate).replace("|", "\\|")
            ability = str(candidate.get("emergent_ability", "")).replace("|", "\\|")
            lines.append(
                f"| {rank} | {float(candidate.get('emergence_score', 0.0)):.4f} | "
                f"{candidate.get('status', '')} | {key} | {ability} |"
            )
    lines.append("")
    lines.append("## Interpretation Guardrails")
    lines.append("")
    lines.append("- This suite uses Aura's read-only emergent-potential path. It does not patch or auto-wire any candidate.")
    lines.append("- A high score means the local topology suggests a useful combination; it is not proof that the resulting system will outperform existing work.")
    lines.append("- Research-derived capacities still require claim-level provenance, adversarial review, benchmarks, ablations, and human approval.")
    return "\n".join(lines) + "\n"


def main() -> int:
    output_dir = REPO_ROOT / "artifacts" / "emergent_capacity_probes"
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = _repo_python_sources(REPO_ROOT)
    anchor = CodeTopoAnchor.build_from_files(sources)

    results: list[dict[str, Any]] = []
    candidate_occurrences: Counter[str] = Counter()
    candidate_best_score: dict[str, float] = defaultdict(float)
    candidate_statuses: dict[str, set[str]] = defaultdict(set)
    candidate_ability: dict[str, str] = {}
    failures = 0

    for probe in PROBES:
        result: dict[str, Any] = dict(probe)
        try:
            report = audit_emergent_potential(
                anchor,
                top=12,
                focus=probe.get("focus", ""),
                new_function_description=probe.get("new", ""),
                combine_with=probe.get("with", ()),
            )
            report_payload = report.to_dict()
            result["report"] = report_payload
            for candidate in report_payload.get("connections", []):
                key = connection_key(candidate)
                candidate_occurrences[key] += 1
                candidate_best_score[key] = max(
                    candidate_best_score[key],
                    float(candidate.get("emergence_score", 0.0)),
                )
                candidate_statuses[key].add(str(candidate.get("status", "")))
                candidate_ability.setdefault(key, str(candidate.get("emergent_ability", "")))
        except Exception as exc:  # preserve the remaining probes and report exact failure
            failures += 1
            result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(result)

    recurring_candidates = [
        {
            "connection": key,
            "occurrences": count,
            "best_score": candidate_best_score[key],
            "statuses": sorted(candidate_statuses[key]),
            "emergent_ability": candidate_ability.get(key, ""),
        }
        for key, count in candidate_occurrences.items()
    ]
    recurring_candidates.sort(
        key=lambda item: (-item["occurrences"], -item["best_score"], item["connection"])
    )

    payload = {
        "suite_version": "AURA_EMERGENT_CAPACITY_PROBES_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository_head": "624a8afefe1824ef070f4684bcc7dc4195542162",
        "python_file_count": len(sources),
        "topology_node_count": len(anchor.nodes),
        "topology_edge_count": len(anchor.edges),
        "probe_count": len(PROBES),
        "failure_count": failures,
        "recurring_candidates": recurring_candidates,
        "results": results,
    }

    json_path = output_dir / "emergent_capacity_probes.json"
    md_path = output_dir / "emergent_capacity_report.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_report(payload), encoding="utf-8")

    print(md_path.read_text(encoding="utf-8"))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
