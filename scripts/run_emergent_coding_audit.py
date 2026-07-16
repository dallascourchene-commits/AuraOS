"""Run deterministic, read-only emergent capability audits for Aura coding.

This script is intentionally analysis-only. It builds one exact CodeTopoAnchor from
local Python sources, reuses that anchor across focused queries, and writes reports
under analysis-output/. It does not patch, stage, commit, call providers, or mutate
Aura runtime state.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import traceback

from aura_emergent_potential_repl import (
    READ_ONLY_CONSTRAINTS,
    _repo_python_sources,
    audit_emergent_potential,
    render_emergent_potential_report,
)
from aura_topological_context_anchor import CodeTopoAnchor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis-output"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:80] or "audit"


def _top_candidates(payload: dict, limit: int = 8) -> list[dict]:
    clusters = list(payload.get("verified_clusters", []) or [])
    candidates: list[dict] = []
    for cluster in clusters[:limit]:
        representative = dict(cluster.get("representative", {}) or {})
        candidates.append(
            {
                "cluster_id": cluster.get("cluster_id"),
                "classification": cluster.get("classification"),
                "score": cluster.get("cluster_score", cluster.get("score")),
                "emergent_ability": representative.get(
                    "emergent_ability", cluster.get("emergent_ability")
                ),
                "source": representative.get("source"),
                "target": representative.get("target"),
                "missing_wire": representative.get(
                    "missing_wire", cluster.get("missing_wire")
                ),
            }
        )
    if candidates:
        return candidates
    for connection in list(payload.get("connections", []) or [])[:limit]:
        candidates.append(
            {
                "classification": connection.get("status"),
                "score": connection.get("emergence_score"),
                "emergent_ability": connection.get("emergent_ability"),
                "source": connection.get("source"),
                "target": connection.get("target"),
                "missing_wire": connection.get("missing_wire"),
            }
        )
    return candidates


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    source_files = _repo_python_sources(ROOT)
    anchor = CodeTopoAnchor.build_from_files(source_files)

    audits = [
        {
            "id": "coding-consolidation-broad",
            "focus": (
                "coding architecture consolidation architect REPL Human Agent Arena "
                "Coding Arena Fusion capability reuse verification hotswap learning"
            ),
        },
        {
            "id": "architect-plan-to-live-skeleton",
            "focus": (
                "architect multi-LLM plan skeleton Human Agent Arena gate repair "
                "patch staging verifier hot swap rollback"
            ),
            "new": (
                "Convert multi-LLM Architect plans into persistent UI-editable coding "
                "skeletons that advance through deterministic gates, retain every plan "
                "revision, and become hot-swappable only after verifier approval."
            ),
            "with": [
                "architect",
                "human agent arena",
                "coding workbench",
                "patch staging",
                "verification",
                "hotswap",
            ],
        },
        {
            "id": "fusion-architect-cognome",
            "focus": (
                "Aura Fusion architect planning model cognome adaptive router panel judge "
                "verifier cost telemetry context grounding"
            ),
        },
        {
            "id": "learn-from-llm-plans",
            "focus": (
                "experience crucible C1 C2 C3 architect plans LLM responses failed attempts "
                "procedure candidates replay shadow drift human promotion"
            ),
            "new": (
                "Mine successful and failed Architect plans, model responses, gate repairs, "
                "and verifier receipts into governed reusable procedure candidates without "
                "allowing experience records to activate code or policy automatically."
            ),
            "with": [
                "experience",
                "crucible",
                "route capsules",
                "replay",
                "shadow",
                "verification",
            ],
        },
        {
            "id": "reuse-before-invention",
            "focus": (
                "capability connectome capability genome resolver affordance directory "
                "codemap topology node inspector reuse before invention architect planning"
            ),
        },
        {
            "id": "planning-board-coding-loop",
            "focus": (
                "planning board coding arena workbench regression replay action capsules "
                "patch staging tests verification human review PR ready"
            ),
        },
        {
            "id": "emergent-to-action-capsule",
            "focus": (
                "emergent capability audit future patch capsule hint architect skeleton "
                "human review exact source spans tests safe handoff"
            ),
            "new": (
                "Promote a verified emergent-capability report into a human-editable Architect "
                "skeleton and proposed ActionCapsule while preserving exact evidence, explicit "
                "missing wires, required tests, and report-only authority until approval."
            ),
            "with": [
                "emergent capability audit",
                "architect",
                "action capsule",
                "human agent arena",
                "topological context",
                "test runner",
            ],
        },
        {
            "id": "self-improving-coding-control-plane",
            "focus": (
                "architect REPL fusion model learning capability consolidation topology "
                "experience verifier continuity institutional memory self improvement"
            ),
        },
    ]

    index: dict = {
        "read_only_constraints": list(READ_ONLY_CONSTRAINTS),
        "source_file_count": len(source_files),
        "anchor_node_count": len(anchor.nodes),
        "anchor_edge_count": len(anchor.edges),
        "warnings": list(anchor.warnings),
        "audits": [],
    }

    successful = 0
    markdown_index = [
        "# Aura Coding Emergent Capability Audit",
        "",
        "This artifact was generated from one read-only CodeTopoAnchor over the checked-out repository.",
        "It performs no patches, code writes, provider calls, staging, commits, merges, or hot-swaps.",
        "",
        f"- Python source files scanned: {len(source_files)}",
        f"- Topology nodes: {len(anchor.nodes)}",
        f"- Topology edges: {len(anchor.edges)}",
        f"- Constraints: {', '.join(READ_ONLY_CONSTRAINTS)}",
        "",
        "## Audits",
    ]

    for audit in audits:
        audit_id = _slug(str(audit["id"]))
        try:
            report = audit_emergent_potential(
                anchor,
                top=30,
                focus=str(audit.get("focus", "")),
                new_function_description=str(audit.get("new", "")),
                combine_with=tuple(audit.get("with", []) or []),
            )
            payload = report.to_dict()
            json_path = OUTPUT / f"{audit_id}.json"
            markdown_path = OUTPUT / f"{audit_id}.md"
            json_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
            )
            markdown_path.write_text(
                render_emergent_potential_report(report), encoding="utf-8"
            )
            summary = dict(payload.get("summary", {}) or {})
            entry = {
                "id": audit_id,
                "focus": audit.get("focus", ""),
                "new_function_description": audit.get("new", ""),
                "combine_with": audit.get("with", []),
                "summary": summary,
                "raw_candidate_count": payload.get("raw_candidate_count", 0),
                "suppressed_duplicate_count": payload.get(
                    "suppressed_duplicate_count", 0
                ),
                "rejected_candidate_count": payload.get("rejected_candidate_count", 0),
                "verifier_summary": payload.get("verifier_summary", ""),
                "top_candidates": _top_candidates(payload),
                "json": json_path.name,
                "markdown": markdown_path.name,
                "error": None,
            }
            index["audits"].append(entry)
            markdown_index.extend(
                [
                    "",
                    f"### {audit_id}",
                    f"- Focus: {audit.get('focus', '')}",
                    f"- Candidate connections: {summary.get('candidate_unwired_connections', 0)}",
                    f"- Future-patchable: {summary.get('future_patchable', 0)}",
                    f"- Needs grounding: {summary.get('needs_grounding', 0)}",
                    f"- Raw candidates: {payload.get('raw_candidate_count', 0)}",
                    f"- Suppressed duplicates: {payload.get('suppressed_duplicate_count', 0)}",
                    f"- Rejected candidates: {payload.get('rejected_candidate_count', 0)}",
                    f"- Reports: `{json_path.name}`, `{markdown_path.name}`",
                ]
            )
            successful += 1
        except Exception as exc:  # preserve diagnostics in the artifact
            error = {
                "id": audit_id,
                "focus": audit.get("focus", ""),
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
            index["audits"].append(error)
            (OUTPUT / f"{audit_id}.error.json").write_text(
                json.dumps(error, indent=2, sort_keys=True), encoding="utf-8"
            )
            markdown_index.extend(
                ["", f"### {audit_id}", f"- Error: `{error['error']}`"]
            )

    index["successful_audits"] = successful
    index["failed_audits"] = len(audits) - successful
    (OUTPUT / "summary.json").write_text(
        json.dumps(index, indent=2, sort_keys=True), encoding="utf-8"
    )
    (OUTPUT / "INDEX.md").write_text("\n".join(markdown_index) + "\n", encoding="utf-8")

    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
