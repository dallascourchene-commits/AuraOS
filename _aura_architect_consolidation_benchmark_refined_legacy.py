"""Refined context-ranking adapter for the Architect consolidation benchmark.

The first empirical preparation run showed that generic LOCALIZE_FIRST fallback
candidates could consume the slice budget before the Architect/Human-Agent spine.
This adapter intentionally preserves that finding while fixing the benchmark path:
exact source spans, selected capability lanes, grounded affordances, and known
Architect/Human-Agent core modules rank above fallback localization candidates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import aura_architect_consolidation_benchmark as benchmark

_REFINED_CORE_FILES = tuple(dict.fromkeys([
    *benchmark._CORE_FILES,
    "aura_human_agent_concepts.py",
    "aura_coding_arena_workflow_memory.py",
    "aura_skillweaver.py",
    "aura_arena_attempt_archive.py",
]))
benchmark._CORE_FILES = _REFINED_CORE_FILES


def _build_raw_context(
    root: Path,
    *,
    max_files: int = 30,
    max_chars: int = 520_000,
) -> tuple[str, dict[str, Any]]:
    excluded = {
        "aura_architect_consolidation_benchmark.py",
        "aura_architect_consolidation_benchmark_refined.py",
    }
    candidates: list[tuple[float, str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".md"}:
            continue
        rel_obj = path.relative_to(root)
        rel = rel_obj.as_posix()
        if any(part in {".git", ".venv", "venv", "node_modules", "__pycache__"} for part in rel_obj.parts):
            continue
        if ".save" in path.name or rel in excluded:
            continue
        text = benchmark._safe_read(path)
        score = benchmark._path_relevance(rel, text)
        if score > 0:
            candidates.append((score, rel, text))
    candidates.sort(key=lambda item: (-item[0], item[1]))

    sections: list[str] = []
    selected: list[dict[str, Any]] = []
    remaining = max_chars
    for score, rel, text in candidates:
        if len(selected) >= max_files or remaining <= 0:
            break
        body = text[:remaining]
        truncated = len(body) < len(text)
        sections.append(f"\n\n===== FILE: {rel} =====\n{body}")
        selected.append({
            "path": rel,
            "score": round(score, 3),
            "source_bytes": len(text.encode("utf-8")),
            "included_bytes": len(body.encode("utf-8")),
            "source_lines": len(text.splitlines()),
            "included_lines": len(body.splitlines()),
            "truncated": truncated,
        })
        remaining -= len(body)
    context = "".join(sections).lstrip()
    return context, {
        "selection_method": "RELEVANCE_RANKED_COMPLETE_FILES_WITH_GLOBAL_CHAR_CAP",
        "selected_files": selected,
        "file_count": len(selected),
        "bytes": len(context.encode("utf-8")),
        "lines": len(context.splitlines()),
        "token_proxy": benchmark._token_proxy(context),
        "max_files": max_files,
        "max_chars": max_chars,
        "benchmark_sources_excluded": sorted(excluded),
    }


def _build_aura_slice_packet(root: Path, objective: str, *, token_budget: int = 9000) -> dict[str, Any]:
    routing: dict[str, Any] = {}
    affordances: dict[str, Any] = {}
    grounding: dict[str, Any] = {}
    lanes: list[Any] = []
    try:
        from aura_cockpit_capability_router import route_capability_lanes
        routing = route_capability_lanes(objective)
    except Exception as exc:
        routing = {"ok": False, "error": type(exc).__name__}
    try:
        from aura_affordance_directory import find_affordances
        affordances = find_affordances(objective, repo_root=root, top_k=7)
    except Exception as exc:
        affordances = {"objective": objective, "error": type(exc).__name__, "recommended_affordances": []}
    try:
        from aura_coding_arena_grounding import ground_coding_arena_intent
        grounding = ground_coding_arena_intent(objective, root)
    except Exception as exc:
        grounding = {"route": "BLOCKED_WITH_REASON", "error": type(exc).__name__}
    try:
        from aura_capability_lane_registry import load_capability_lanes
        lanes = list(load_capability_lanes())
    except Exception:
        lanes = []

    path_scores: dict[str, float] = {}
    path_reasons: dict[str, list[str]] = {}

    def add_path(raw: Any, score: float, reason: str) -> None:
        value = benchmark._normalize_candidate_path(raw)
        if not value or not (root / value).is_file():
            return
        path_scores[value] = max(path_scores.get(value, float("-inf")), float(score))
        reasons = path_reasons.setdefault(value, [])
        if reason not in reasons:
            reasons.append(reason)

    route = str(grounding.get("route") or "")
    fallback_score = 5.0 if route == "LOCALIZE_FIRST" else 24.0
    add_path(grounding.get("target_file"), fallback_score + 2.0, f"grounding_target:{route or 'unknown'}")
    for item in grounding.get("candidate_files", []) or []:
        add_path(item, fallback_score, f"grounding_candidate:{route or 'unknown'}")
    for item in grounding.get("exact_hits", []) or []:
        add_path(item, 42.0, "grounding_exact_hit")
    for item in grounding.get("source_spans", []) or []:
        add_path(item, 44.0, "grounding_exact_source_span")

    recommended = list(affordances.get("recommended_affordances", []) or [])
    for item in recommended:
        if not isinstance(item, dict):
            continue
        aff_score = float(item.get("score") or 0.0)
        for path in item.get("implemented_by", []) or []:
            add_path(path, 34.0 + min(10.0, max(0.0, aff_score)), f"affordance:{item.get('id', '')}")
        for path in item.get("tests", []) or []:
            add_path(path, 26.0 + min(6.0, max(0.0, aff_score)), f"affordance_test:{item.get('id', '')}")

    selected_lane_ids = {
        str(item.get("lane_id") or "")
        for item in list(routing.get("selected_lanes", []) or [])
        if isinstance(item, dict)
    }
    for lane in lanes:
        lane_id = str(getattr(lane, "lane_id", ""))
        if lane_id not in selected_lane_ids:
            continue
        for path in list(getattr(lane, "source_modules", []) or []):
            add_path(path, 38.0, f"selected_lane:{lane_id}")
        for path in list(getattr(lane, "tests", []) or []):
            add_path(path, 28.0, f"selected_lane_test:{lane_id}")

    for rel in _REFINED_CORE_FILES:
        path = root / rel
        if path.is_file():
            relevance = benchmark._path_relevance(rel, benchmark._safe_read(path))
            add_path(rel, 50.0 + min(25.0, relevance / 3.0), "objective_core_architecture")

    ranked_paths = sorted(
        path_scores,
        key=lambda value: (
            -path_scores[value],
            -benchmark._path_relevance(value, benchmark._safe_read(root / value)),
            value,
        ),
    )
    source_paths = [path for path in ranked_paths if not (path.startswith("test") or "/test" in path)]
    test_paths = [path for path in ranked_paths if path.startswith("test") or "/test" in path]
    source_slices: list[dict[str, Any]] = []
    test_slices: list[dict[str, Any]] = []
    source_budget = max(512, int(token_budget * 0.82))
    test_budget = max(256, token_budget - source_budget)
    terms = tuple(term.replace("_", "") for term in benchmark._CORE_TERMS) + benchmark._CORE_TERMS

    def build_slice(rel: str, budget: int, *, max_lines: int) -> dict[str, Any] | None:
        path = root / rel
        definitions = benchmark._find_relevant_definitions(path, terms, limit=1) if path.suffix == ".py" else []
        if not definitions:
            definitions = [("", 1, min(80, len(benchmark._safe_read(path).splitlines()) or 1))]
        symbol, start, end = definitions[0]
        item = benchmark._slice_text(path, start, end, max_lines=max_lines)
        item["file"] = rel
        item["symbol"] = symbol
        item["selection_score"] = round(path_scores[rel], 3)
        item["selection_reasons"] = path_reasons.get(rel, [])
        return item if int(item["token_proxy"]) <= budget else None

    for rel in source_paths:
        if source_budget <= 120 or len(source_slices) >= 14:
            break
        item = build_slice(rel, source_budget, max_lines=min(120, max(20, source_budget // 5)))
        if item is not None:
            source_slices.append(item)
            source_budget -= int(item["token_proxy"])

    for rel in test_paths:
        if test_budget <= 96 or len(test_slices) >= 4:
            break
        item = build_slice(rel, test_budget, max_lines=min(100, max(16, test_budget // 5)))
        if item is not None:
            test_slices.append(item)
            test_budget -= int(item["token_proxy"])

    compact_affordances = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "implemented_by": list(item.get("implemented_by", []) or [])[:5],
            "symbols": list(item.get("symbols", []) or [])[:8],
            "tests": list(item.get("tests", []) or [])[:5],
            "grounding": item.get("grounding"),
            "score": item.get("score"),
        }
        for item in recommended[:7]
        if isinstance(item, dict)
    ]
    packet = {
        "packet_version": "AURA_ARCHITECT_CONSOLIDATION_SLICE_PACKET_V1_REFINED",
        "objective": objective,
        "capability_route": {
            "selected_lanes": list(routing.get("selected_lanes", []) or []),
            "lane_order": list(routing.get("lane_order", []) or []),
            "required_evidence": list(routing.get("required_evidence", []) or []),
            "next_workflow_gate": routing.get("next_workflow_gate"),
        },
        "affordances": compact_affordances,
        "grounding": {
            "route": grounding.get("route"),
            "target_file": grounding.get("target_file"),
            "target_symbol": grounding.get("target_symbol"),
            "candidate_files": [
                benchmark._normalize_candidate_path(item)
                for item in list(grounding.get("candidate_files", []) or [])[:12]
            ],
            "tests": list(grounding.get("tests", []) or [])[:10],
            "route_reasons": list(grounding.get("route_reasons", []) or [])[:10],
            "source_spans": list(grounding.get("source_spans", []) or [])[:8],
            "fallback_candidates_downranked": route == "LOCALIZE_FIRST",
        },
        "ranked_files": [
            {"path": path, "score": round(path_scores[path], 3), "reasons": path_reasons.get(path, [])}
            for path in ranked_paths[:24]
        ],
        "source_slices": source_slices,
        "test_slices": test_slices,
        "invariants": {
            "patch_authority": benchmark.PATCH_AUTHORITY,
            "vsa_patch_authority": benchmark.VSA_PATCH_AUTHORITY,
            "production_mutation": False,
            "plans_persist": True,
            "human_review_required": True,
            "reuse_before_reinvent": True,
        },
        "empirical_finding": {
            "finding": "Generic LOCALIZE_FIRST fallback candidates can outrank the intended subsystem on broad cross-cutting objectives.",
            "correction": "Rank exact spans, selected lanes, grounded affordances, and objective-core files before fallback candidates.",
        },
    }
    packet["measurement"] = {
        "bytes": len(benchmark._canonical(packet).encode("utf-8")),
        "token_proxy": benchmark._token_proxy(packet),
        "source_slice_count": len(source_slices),
        "test_slice_count": len(test_slices),
        "requested_token_budget": token_budget,
        "unused_source_budget": source_budget,
        "unused_test_budget": test_budget,
    }
    return packet


benchmark._build_raw_context = _build_raw_context
benchmark._build_aura_slice_packet = _build_aura_slice_packet


def main(argv: list[str] | None = None) -> int:
    return benchmark.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
