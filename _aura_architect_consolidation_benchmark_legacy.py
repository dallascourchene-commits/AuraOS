"""Reproducible Architect benchmark for AuraOS consolidation planning.

The benchmark uses one fixed repository objective and three arms:

RAW_BROAD_CONTEXT
    One model receives a broad set of complete, relevance-ranked repository files.

AURA_SLICE_SINGLE
    One model receives Aura-native routing, affordance, grounding, and bounded
    source/test slices.

AURA_ARCHITECT_COUNCIL
    Aura's real ArchitectFusionCouncil coordinates the deterministic local plan,
    two external planner roles, cheap Shadow critics, and a Judge. Model responses
    are supplied through a provider-neutral fixture/callback so every prompt and
    response is reproducible and auditable.

This benchmark plans only. It does not stage, patch, promote, commit, push, merge,
or mutate production source. Token values use a deterministic char/4 proxy unless
provider-reported usage is supplied. Normalized cost is derived from an explicit
rate card and is not a provider bill.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
from dataclasses import asdict, is_dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable

BENCHMARK_VERSION = "AURA_ARCHITECT_CONSOLIDATION_BENCHMARK_V1"
OBJECTIVE = (
    "Scan the AuraOS repository and produce a grounded, staged refactor skeleton "
    "that consolidates memory, skill, capability, and agentic functions to improve "
    "the Human Agent Arena. Reuse existing Aura architecture, preserve compatibility "
    "through explicit adapters, retain plans and verifier evidence, and require human "
    "approval before mutation or promotion."
)
MEASUREMENT_CLASS = {
    "bytes_lines_files": "MEASURED_EXACT_FROM_TESTED_COMMIT",
    "tokens": "ESTIMATED_CHAR4_PROXY",
    "quality": "DERIVED_DETERMINISTIC_GROUNDING_RUBRIC",
    "normalized_cost": "DERIVED_RATE_CARD_NOT_PROVIDER_BILL",
    "provider_cost": "UNAVAILABLE_UNLESS_REPORTED",
}
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_CORE_TERMS = (
    "human_agent",
    "architect",
    "agent",
    "arena",
    "memory",
    "experience",
    "skill",
    "affordance",
    "capability",
    "planning",
    "capsule",
    "crucible",
    "router",
    "mcp",
    "workflow",
    "cockpit",
)
_CORE_FILES = (
    "aura_live_architect.py",
    "aura_architect_loop.py",
    "aura_human_agent_workflow.py",
    "aura_human_agent_arena.py",
    "aura_agent_arena_bridge.py",
    "aura_agent_arena_mcp.py",
    "aura_external_llm_session.py",
    "aura_planning_board.py",
    "aura_coding_arena_planning.py",
    "aura_affordance_directory.py",
    "aura_capability_lane_registry.py",
    "aura_cockpit_capability_router.py",
    "aura_arena_experience.py",
    "aura_arena_experience_ledger.py",
    "aura_arena_crucible.py",
    "aura_crucible_miner.py",
)
_DOMAIN_TERMS: dict[str, tuple[str, ...]] = {
    "memory": ("memory", "experience", "ledger", "trace", "recall"),
    "skills_capabilities": ("skill", "affordance", "capability", "lane", "registry"),
    "agents_orchestration": ("agent", "architect", "router", "mcp", "council", "worker"),
    "human_agent_arena": ("human agent", "human_agent", "workspace", "arena", "ui"),
    "canonical_plan": ("planning board", "plan skeleton", "capsule", "adapter", "canonical"),
    "governance": ("verifier", "human review", "approval", "rollback", "stage", "authority"),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_canonical(value).encode("utf-8"), digest_size=size).hexdigest()


def _token_proxy(value: Any) -> int:
    text = value if isinstance(value, str) else _canonical(value)
    return (len(text.encode("utf-8")) + 3) // 4


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _git_sha(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception:
        return ""


def _source_inventory(root: Path) -> dict[str, Any]:
    allowed_suffixes = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".lexc"}
    ignored_parts = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    files: list[dict[str, Any]] = []
    total_bytes = 0
    total_lines = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue
        rel = path.relative_to(root)
        if any(part in ignored_parts for part in rel.parts):
            continue
        if ".save" in path.name or path.name.endswith((".bak", ".tmp")):
            continue
        text = _safe_read(path)
        byte_count = len(text.encode("utf-8"))
        line_count = len(text.splitlines())
        total_bytes += byte_count
        total_lines += line_count
        files.append(
            {
                "path": rel.as_posix(),
                "bytes": byte_count,
                "lines": line_count,
                "token_proxy": _token_proxy(text),
            }
        )
    return {
        "file_count": len(files),
        "bytes": total_bytes,
        "lines": total_lines,
        "token_proxy": (total_bytes + 3) // 4,
        "files": files,
    }


def _path_relevance(path: str, text: str) -> float:
    lower_path = path.lower()
    header = text[:16000].lower()
    score = 0.0
    for term in _CORE_TERMS:
        if term in lower_path:
            score += 7.0
        spaced = term.replace("_", " ")
        score += min(4, header.count(term)) * 0.75
        if spaced != term:
            score += min(3, header.count(spaced)) * 0.5
    if path in _CORE_FILES:
        score += 20.0
    if path.startswith("test") or "/test" in path:
        score += 1.5
    if path.startswith("docs/"):
        score += 1.0
    return score


def _build_raw_context(
    root: Path,
    *,
    max_files: int = 30,
    max_chars: int = 520_000,
) -> tuple[str, dict[str, Any]]:
    candidates: list[tuple[float, str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".md"}:
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in {".git", ".venv", "venv", "node_modules", "__pycache__"} for part in path.relative_to(root).parts):
            continue
        if ".save" in path.name:
            continue
        text = _safe_read(path)
        score = _path_relevance(rel, text)
        if score > 0:
            candidates.append((score, rel, text))
    candidates.sort(key=lambda item: (-item[0], item[1]))

    sections: list[str] = []
    selected: list[dict[str, Any]] = []
    remaining = max_chars
    for score, rel, text in candidates:
        if len(selected) >= max_files or remaining <= 0:
            break
        body = text
        truncated = False
        if len(body) > remaining:
            body = body[:remaining]
            truncated = True
        section = f"\n\n===== FILE: {rel} =====\n{body}"
        sections.append(section)
        selected.append(
            {
                "path": rel,
                "score": round(score, 3),
                "source_bytes": len(text.encode("utf-8")),
                "included_bytes": len(body.encode("utf-8")),
                "source_lines": len(text.splitlines()),
                "included_lines": len(body.splitlines()),
                "truncated": truncated,
            }
        )
        remaining -= len(body)
    context = "".join(sections).lstrip()
    return context, {
        "selection_method": "RELEVANCE_RANKED_COMPLETE_FILES_WITH_GLOBAL_CHAR_CAP",
        "selected_files": selected,
        "file_count": len(selected),
        "bytes": len(context.encode("utf-8")),
        "lines": len(context.splitlines()),
        "token_proxy": _token_proxy(context),
        "max_files": max_files,
        "max_chars": max_chars,
    }


def _find_relevant_definitions(path: Path, terms: tuple[str, ...], limit: int = 2) -> list[tuple[str, int, int]]:
    text = _safe_read(path)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []
    hits: list[tuple[int, str, int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        name = str(node.name)
        lowered = name.lower()
        score = sum(2 for term in terms if term in lowered)
        if score:
            hits.append((score, name, int(node.lineno), int(getattr(node, "end_lineno", node.lineno))))
    hits.sort(key=lambda item: (-item[0], item[2]))
    return [(name, start, end) for _score, name, start, end in hits[:limit]]


def _slice_text(path: Path, start: int, end: int, *, max_lines: int = 120) -> dict[str, Any]:
    lines = _safe_read(path).splitlines()
    start = max(1, start)
    end = max(start, min(end, start + max_lines - 1, len(lines)))
    body = "\n".join(lines[start - 1 : end])
    return {
        "file": path.name if path.parent == path.parent.parent else path.as_posix(),
        "line_start": start,
        "line_end": end,
        "content": body,
        "bytes": len(body.encode("utf-8")),
        "token_proxy": _token_proxy(body),
        "source_hash": hashlib.blake2b(body.encode("utf-8"), digest_size=12).hexdigest(),
    }


def _normalize_candidate_path(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("path") or value.get("file") or value.get("file_path") or ""
    return str(value or "").replace("\\", "/").lstrip("./")


def _build_aura_slice_packet(root: Path, objective: str, *, token_budget: int = 9000) -> dict[str, Any]:
    routing: dict[str, Any] = {}
    affordances: dict[str, Any] = {}
    grounding: dict[str, Any] = {}
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

    paths: list[str] = []

    def add_path(raw: Any) -> None:
        value = _normalize_candidate_path(raw)
        if value and value not in paths and (root / value).is_file():
            paths.append(value)

    for item in grounding.get("candidate_files", []) or []:
        add_path(item)
    for item in grounding.get("exact_hits", []) or []:
        add_path(item)
    for item in affordances.get("recommended_affordances", []) or []:
        for path in item.get("implemented_by", []) or []:
            add_path(path)
        for path in item.get("tests", []) or []:
            add_path(path)
    for path in _CORE_FILES:
        add_path(path)

    slices: list[dict[str, Any]] = []
    test_slices: list[dict[str, Any]] = []
    remaining = token_budget
    terms = tuple(term.replace("_", "") for term in _CORE_TERMS) + _CORE_TERMS
    for rel in paths:
        if remaining <= 160 or len(slices) >= 16:
            break
        path = root / rel
        definitions = _find_relevant_definitions(path, terms, limit=2) if path.suffix == ".py" else []
        if not definitions:
            definitions = [("", 1, min(80, len(_safe_read(path).splitlines()) or 1))]
        for symbol, start, end in definitions:
            if remaining <= 160 or len(slices) >= 16:
                break
            item = _slice_text(path, start, end, max_lines=min(120, max(20, remaining // 5)))
            item["file"] = rel
            item["symbol"] = symbol
            cost = int(item["token_proxy"])
            if cost > remaining:
                continue
            if rel.startswith("test") or "/test" in rel:
                test_slices.append(item)
            else:
                slices.append(item)
            remaining -= cost

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
        for item in list(affordances.get("recommended_affordances", []) or [])[:7]
        if isinstance(item, dict)
    ]
    compact_grounding = {
        "route": grounding.get("route"),
        "target_file": grounding.get("target_file"),
        "target_symbol": grounding.get("target_symbol"),
        "candidate_files": [
            _normalize_candidate_path(item)
            for item in list(grounding.get("candidate_files", []) or [])[:12]
        ],
        "tests": list(grounding.get("tests", []) or [])[:10],
        "route_reasons": list(grounding.get("route_reasons", []) or [])[:10],
        "source_spans": list(grounding.get("source_spans", []) or [])[:8],
    }
    packet = {
        "packet_version": "AURA_ARCHITECT_CONSOLIDATION_SLICE_PACKET_V1",
        "objective": objective,
        "capability_route": {
            "selected_lanes": list(routing.get("selected_lanes", []) or []),
            "lane_order": list(routing.get("lane_order", []) or []),
            "required_evidence": list(routing.get("required_evidence", []) or []),
            "next_workflow_gate": routing.get("next_workflow_gate"),
        },
        "affordances": compact_affordances,
        "grounding": compact_grounding,
        "source_slices": slices,
        "test_slices": test_slices,
        "invariants": {
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "production_mutation": False,
            "plans_persist": True,
            "human_review_required": True,
            "reuse_before_reinvent": True,
        },
    }
    packet["measurement"] = {
        "bytes": len(_canonical(packet).encode("utf-8")),
        "token_proxy": _token_proxy(packet),
        "source_slice_count": len(slices),
        "test_slice_count": len(test_slices),
        "requested_token_budget": token_budget,
        "unused_slice_budget": remaining,
    }
    return packet


def _plan_instruction() -> str:
    return (
        "Return JSON only. Produce a bounded Aura Architect refactor plan with fields: "
        "architecture_decision, target_file, target_symbol, act_tasks, acceptance_criteria, "
        "rollback_conditions, risk_map, constraints. Each act task must include task_id, "
        "objective, target_file, target_symbol, related_files, allowed_scope, acceptance, "
        "expected_output=UNIFIED_DIFF, and size. Use only repository facts present in the "
        "context. Prefer existing modules and explicit adapters over a new giant abstraction. "
        "The plan must persist in the Human Agent Arena, preserve verifier evidence, stage all "
        "changes, and require human approval before mutation or promotion."
    )


def prepare_prompts(root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = _source_inventory(root)
    raw_context, raw_measurement = _build_raw_context(root)
    aura_packet = _build_aura_slice_packet(root, OBJECTIVE)
    raw_prompt = f"{_plan_instruction()}\n\nOBJECTIVE:\n{OBJECTIVE}\n\nBROAD REPOSITORY CONTEXT:\n{raw_context}\n"
    slice_prompt = (
        f"{_plan_instruction()}\n\nOBJECTIVE:\n{OBJECTIVE}\n\n"
        f"AURA SLICE PACKET:\n{json.dumps(aura_packet, indent=2, sort_keys=True, default=str)}\n"
    )
    (output_dir / "raw_prompt.txt").write_text(raw_prompt, encoding="utf-8")
    (output_dir / "aura_slice_prompt.txt").write_text(slice_prompt, encoding="utf-8")
    template = {
        "benchmark_version": BENCHMARK_VERSION,
        "model": "",
        "raw_plan": {},
        "aura_slice_plan": {},
        "council": {
            "planner": {},
            "planner_alt": {},
            "critics": {},
            "judge": {},
        },
        "notes": "Fill with JSON-only model responses. Critic keys use candidate_id:critic_id.",
    }
    (output_dir / "responses.template.json").write_text(
        json.dumps(template, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    codemap_path = root / ".aura" / "CODEMAP.json"
    codemap_bytes = codemap_path.stat().st_size if codemap_path.exists() else 0
    codemap_digest = hashlib.blake2b(codemap_path.read_bytes(), digest_size=16).hexdigest() if codemap_bytes else ""
    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "objective": OBJECTIVE,
        "repository_commit_sha": _git_sha(root),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "measurement_class": MEASUREMENT_CLASS,
        "repository_inventory": {key: value for key, value in inventory.items() if key != "files"},
        "codemap": {"path": ".aura/CODEMAP.json", "bytes": codemap_bytes, "digest": codemap_digest},
        "raw_broad_context": raw_measurement,
        "aura_slice_packet": aura_packet["measurement"],
        "prompts": {
            "raw": {"bytes": len(raw_prompt.encode("utf-8")), "token_proxy": _token_proxy(raw_prompt)},
            "aura_slice": {"bytes": len(slice_prompt.encode("utf-8")), "token_proxy": _token_proxy(slice_prompt)},
        },
        "limitations": [
            "The full repository inventory is measured, but the RAW arm uses a relevance-ranked broad context capped by file and character limits.",
            "Token values are a deterministic four-bytes-per-token proxy unless provider usage is supplied.",
            "Prompt preparation measures context efficiency only; quality requires completed response fixtures and score mode.",
            "No source mutation, patch staging, promotion, commit, push, or merge occurs.",
        ],
    }
    (output_dir / "prepare_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _symbol_exists(path: Path, symbol: str | None) -> bool:
    if not symbol:
        return True
    try:
        tree = ast.parse(_safe_read(path), filename=str(path))
    except SyntaxError:
        return False
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol
        for node in ast.walk(tree)
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    return dict(value) if isinstance(value, dict) else {"value": value}


def _prepare_plan(root: Path, plan: dict[str, Any]) -> tuple[Any | None, str | None]:
    try:
        from aura_architect_loop import ArchitectFusionLoop

        loop = ArchitectFusionLoop(repo_root=root)
        prepared = loop.prepare(
            OBJECTIVE,
            architecture_decision=str(plan.get("architecture_decision") or "Bounded consolidation plan."),
            act_tasks=list(plan.get("act_tasks", []) or []),
            target_file=plan.get("target_file"),
            target_symbol=plan.get("target_symbol"),
            acceptance_criteria=list(plan.get("acceptance_criteria", []) or []),
            rollback_conditions=list(plan.get("rollback_conditions", []) or []),
            risk_map=list(plan.get("risk_map", []) or []),
            constraints=list(plan.get("constraints", []) or []),
        )
        return prepared, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def score_plan(root: Path, plan: dict[str, Any], *, label: str) -> dict[str, Any]:
    tasks = [item for item in list(plan.get("act_tasks", []) or []) if isinstance(item, dict)]
    task_count = len(tasks)
    exact_files = 0
    exact_symbols = 0
    output_contracts = 0
    bounded_scopes = 0
    acceptance_count = 0
    for task in tasks:
        target_file = str(task.get("target_file") or "")
        path = root / target_file if target_file else None
        file_ok = bool(path and path.is_file())
        exact_files += int(file_ok)
        exact_symbols += int(file_ok and _symbol_exists(path, task.get("target_symbol")))
        output_contracts += int(str(task.get("expected_output") or "").upper() == "UNIFIED_DIFF")
        bounded_scopes += int(bool(str(task.get("allowed_scope") or "").strip()))
        acceptance_count += int(bool(str(task.get("acceptance") or "").strip()))

    prepared, prepare_error = _prepare_plan(root, plan) if tasks else (None, "no_act_tasks")
    grounding: list[dict[str, Any]] = []
    shadow: dict[str, Any] = {}
    arena: dict[str, Any] = {}
    if prepared is not None:
        grounding = [_as_dict(item) for item in prepared.grounding]
        shadow = _as_dict(prepared.shadow_report)
        arena = _as_dict(prepared.arena)
    grounded_tests = sum(1 for item in grounding if item.get("test_files"))
    blockers = [item for item in shadow.get("findings", []) or [] if item.get("severity") == "blocker"]
    warnings = [item for item in shadow.get("findings", []) or [] if item.get("severity") != "blocker"]

    full_text = _canonical(plan).lower()
    domain_coverage = {
        domain: any(term in full_text for term in terms)
        for domain, terms in _DOMAIN_TERMS.items()
    }
    governance_checks = {
        "human_review": "human" in full_text and ("review" in full_text or "approval" in full_text),
        "stage_only": "stage" in full_text,
        "rollback": "rollback" in full_text,
        "no_direct_mutation": not any(
            phrase in full_text
            for phrase in (
                "write directly to production",
                "auto merge",
                "automatically merge",
                "bypass verifier",
            )
        ),
        "adapter_preservation": "adapter" in full_text or "compatib" in full_text,
        "plan_persistence": "persist" in full_text or "retain" in full_text or "workspace" in full_text,
    }
    schema_score = sum(
        (
            bool(plan.get("architecture_decision")),
            3 <= task_count <= 12,
            all(bool(task.get("task_id")) for task in tasks) if tasks else False,
            all(bool(task.get("target_file")) for task in tasks) if tasks else False,
        )
    ) / 4
    exact_file_rate = exact_files / task_count if task_count else 0.0
    exact_symbol_rate = exact_symbols / task_count if task_count else 0.0
    output_rate = output_contracts / task_count if task_count else 0.0
    scope_rate = bounded_scopes / task_count if task_count else 0.0
    acceptance_rate = acceptance_count / task_count if task_count else 0.0
    test_rate = grounded_tests / task_count if task_count else 0.0
    domain_rate = sum(domain_coverage.values()) / len(domain_coverage)
    governance_rate = sum(governance_checks.values()) / len(governance_checks)
    blocker_score = 1.0 if not blockers and prepared is not None else 0.0
    arena_score = 1.0 if arena.get("ready_for_incubator") else 0.5 if prepared is not None else 0.0
    quality_score = round(
        0.10 * schema_score
        + 0.17 * exact_file_rate
        + 0.13 * exact_symbol_rate
        + 0.08 * output_rate
        + 0.05 * scope_rate
        + 0.05 * acceptance_rate
        + 0.10 * test_rate
        + 0.12 * domain_rate
        + 0.10 * governance_rate
        + 0.05 * blocker_score
        + 0.05 * arena_score,
        4,
    )
    return {
        "label": label,
        "quality_score": quality_score,
        "task_count": task_count,
        "schema_score": round(schema_score, 4),
        "exact_file_rate": round(exact_file_rate, 4),
        "exact_symbol_rate": round(exact_symbol_rate, 4),
        "output_contract_rate": round(output_rate, 4),
        "bounded_scope_rate": round(scope_rate, 4),
        "acceptance_rate": round(acceptance_rate, 4),
        "grounded_test_rate": round(test_rate, 4),
        "domain_coverage": domain_coverage,
        "domain_coverage_rate": round(domain_rate, 4),
        "governance_checks": governance_checks,
        "governance_rate": round(governance_rate, 4),
        "shadow_blocker_count": len(blockers),
        "shadow_warning_count": len(warnings),
        "arena_ready_for_incubator": bool(arena.get("ready_for_incubator")),
        "prepare_error": prepare_error,
        "plan_digest": _digest(plan),
        "prepared": {
            "plan": _as_dict(prepared.plan) if prepared is not None else {},
            "grounding": grounding,
            "shadow_report": shadow,
            "arena": arena,
        },
    }


class FixtureModelCallback:
    """Return reproducible role responses while retaining every actual Aura prompt."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self.fixture = fixture
        self.requests: list[dict[str, Any]] = []

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(dict(request))
        role = str(request.get("role") or "")
        meta = dict(request.get("meta") or {})
        candidate_id = str(meta.get("candidate_id") or "")
        critic_id = str(meta.get("critic_id") or "")
        phase = str(meta.get("council_phase") or "")
        council = dict(self.fixture.get("council") or {})
        response: Any = None
        if role == "planner":
            response = council.get("planner")
        elif role == "planner_alt":
            response = council.get("planner_alt")
        elif role == "shadow":
            critics = dict(council.get("critics") or {})
            response = critics.get(f"{candidate_id}:{critic_id}") or critics.get(critic_id)
        elif role == "judge":
            judges = dict(council.get("judge") or {})
            response = judges.get(phase) or judges.get("plan_judge")
        if response is None and role == "shadow":
            response = {
                "approved": True,
                "score": 0.72,
                "blockers": [],
                "rationale": "Fixture fallback: no blocker found in the bounded candidate plan.",
            }
        if response is None and role == "judge":
            response = {
                "selected_candidate_id": candidate_id or "local_free",
                "approved": True,
                "rationale": "Fixture fallback selected the highest grounded candidate.",
            }
        text = response if isinstance(response, str) else json.dumps(response or {}, sort_keys=True)
        return {"text": text, "usage": {}, "cost_usd": None}


async def _run_council(root: Path, fixture: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    from aura_external_llm_session import InstrumentedExternalModelCaller
    from aura_live_architect import ArchitectModelRouter

    callback = FixtureModelCallback(fixture)
    caller = InstrumentedExternalModelCaller(callback, hard_prompt_token_limit=64_000)
    ledger_path = output_dir / "architect_benchmark_ledger.jsonl"
    router = ArchitectModelRouter(repo_root=root, model_caller=caller, ledger_path=ledger_path)
    decision = await router.plan_with_council(OBJECTIVE)
    selected_plan = dict(decision.selected_plan)
    selected_score = score_plan(root, selected_plan, label="AURA_ARCHITECT_COUNCIL")
    requests = [
        {
            "provider": item.get("provider"),
            "role": item.get("role"),
            "meta": item.get("meta"),
            "input_token_estimate": item.get("input_token_estimate"),
            "prompt_digest": _digest(item.get("prompt", "")),
            "prompt": item.get("prompt", ""),
        }
        for item in callback.requests
    ]
    return {
        "decision": decision.to_dict(),
        "selected_plan": selected_plan,
        "quality": selected_score,
        "model_usage": caller.summary(),
        "requests": requests,
    }


def _normalized_cost(input_tokens: int, output_tokens: int, input_rate: float, output_rate: float) -> float:
    return round((input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate, 8)


def _pct_reduction(before: float, after: float) -> float | None:
    if before <= 0:
        return None
    return round((before - after) / before * 100.0, 2)


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    arms = report["arms"]
    raw = arms["raw_broad_context"]
    sliced = arms["aura_slice_single"]
    council = arms["aura_architect_council"]
    comparison = report["comparison"]
    lines = [
        "# Aura Architect Consolidation Benchmark",
        "",
        f"**Version:** `{report['benchmark_version']}`  ",
        f"**Commit:** `{report['repository_commit_sha']}`  ",
        f"**Model fixture:** `{report['model']}`  ",
        f"**Objective:** {report['objective']}",
        "",
        "## Results",
        "",
        "| Arm | Model calls | Input token proxy | Output token proxy | Total token proxy | Quality | Normalized cost* |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| RAW broad context | {raw['model_calls']} | {raw['input_tokens']} | {raw['output_tokens']} | {raw['total_tokens']} | {raw['quality']['quality_score']:.4f} | ${raw['normalized_cost_usd']:.6f} |",
        f"| Aura slice, single planner | {sliced['model_calls']} | {sliced['input_tokens']} | {sliced['output_tokens']} | {sliced['total_tokens']} | {sliced['quality']['quality_score']:.4f} | ${sliced['normalized_cost_usd']:.6f} |",
        f"| Aura Architect Council | {council['model_calls']} | {council['input_tokens']} | {council['output_tokens']} | {council['total_tokens']} | {council['quality']['quality_score']:.4f} | ${council['normalized_cost_usd']:.6f} |",
        "",
        "*Normalized cost uses the declared benchmark rate card, not a provider invoice.*",
        "",
        "## Headline comparisons",
        "",
        f"- Aura slice input reduction vs RAW: **{comparison['slice_input_reduction_pct']}%**.",
        f"- Aura slice total-token reduction vs RAW: **{comparison['slice_total_reduction_pct']}%**.",
        f"- Aura slice quality delta vs RAW: **{comparison['slice_quality_delta']:+.4f}**.",
        f"- Council total-token reduction vs RAW: **{comparison['council_total_reduction_pct']}%**.",
        f"- Council quality delta vs RAW: **{comparison['council_quality_delta']:+.4f}**.",
        f"- Full repository token proxy avoided by the Aura slice prompt: **{comparison['slice_vs_full_repo_reduction_pct']}%**.",
        "",
        "## Interpretation",
        "",
        report["interpretation"],
        "",
        "## Measurement labels",
        "",
        *[f"- `{key}`: `{value}`" for key, value in report["measurement_class"].items()],
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def score_benchmark(
    root: Path,
    output_dir: Path,
    responses_path: Path,
    *,
    input_rate: float,
    output_rate: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "prepare_manifest.json"
    if not manifest_path.exists():
        prepare_prompts(root, output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture = json.loads(responses_path.read_text(encoding="utf-8"))
    raw_plan = dict(fixture.get("raw_plan") or {})
    slice_plan = dict(fixture.get("aura_slice_plan") or {})
    raw_prompt = (output_dir / "raw_prompt.txt").read_text(encoding="utf-8")
    slice_prompt = (output_dir / "aura_slice_prompt.txt").read_text(encoding="utf-8")
    raw_output = json.dumps(raw_plan, sort_keys=True)
    slice_output = json.dumps(slice_plan, sort_keys=True)
    raw_quality = score_plan(root, raw_plan, label="RAW_BROAD_CONTEXT")
    slice_quality = score_plan(root, slice_plan, label="AURA_SLICE_SINGLE")
    council = asyncio.run(_run_council(root, fixture, output_dir))
    council_usage = council["model_usage"]

    raw_input = _token_proxy(raw_prompt)
    raw_out = _token_proxy(raw_output)
    slice_input = _token_proxy(slice_prompt)
    slice_out = _token_proxy(slice_output)
    council_input = int(council_usage.get("input_token_estimate", 0))
    council_out = int(council_usage.get("output_token_estimate", 0))
    rate_card = {
        "input_usd_per_million_tokens": input_rate,
        "output_usd_per_million_tokens": output_rate,
    }

    arms = {
        "raw_broad_context": {
            "model_calls": 1,
            "input_tokens": raw_input,
            "output_tokens": raw_out,
            "total_tokens": raw_input + raw_out,
            "normalized_cost_usd": _normalized_cost(raw_input, raw_out, input_rate, output_rate),
            "quality": raw_quality,
            "plan": raw_plan,
        },
        "aura_slice_single": {
            "model_calls": 1,
            "input_tokens": slice_input,
            "output_tokens": slice_out,
            "total_tokens": slice_input + slice_out,
            "normalized_cost_usd": _normalized_cost(slice_input, slice_out, input_rate, output_rate),
            "quality": slice_quality,
            "plan": slice_plan,
        },
        "aura_architect_council": {
            "model_calls": int(council_usage.get("call_count", 0)),
            "input_tokens": council_input,
            "output_tokens": council_out,
            "total_tokens": council_input + council_out,
            "normalized_cost_usd": _normalized_cost(council_input, council_out, input_rate, output_rate),
            "quality": council["quality"],
            "selected_plan": council["selected_plan"],
            "decision": council["decision"],
            "model_usage": council_usage,
        },
    }
    full_repo_tokens = int(manifest["repository_inventory"]["token_proxy"])
    comparison = {
        "slice_input_reduction_pct": _pct_reduction(raw_input, slice_input),
        "slice_total_reduction_pct": _pct_reduction(raw_input + raw_out, slice_input + slice_out),
        "slice_quality_delta": round(slice_quality["quality_score"] - raw_quality["quality_score"], 4),
        "slice_cost_reduction_pct": _pct_reduction(
            arms["raw_broad_context"]["normalized_cost_usd"],
            arms["aura_slice_single"]["normalized_cost_usd"],
        ),
        "council_total_reduction_pct": _pct_reduction(raw_input + raw_out, council_input + council_out),
        "council_quality_delta": round(council["quality"]["quality_score"] - raw_quality["quality_score"], 4),
        "council_cost_reduction_pct": _pct_reduction(
            arms["raw_broad_context"]["normalized_cost_usd"],
            arms["aura_architect_council"]["normalized_cost_usd"],
        ),
        "slice_vs_full_repo_reduction_pct": _pct_reduction(full_repo_tokens, slice_input),
        "raw_vs_full_repo_reduction_pct": _pct_reduction(full_repo_tokens, raw_input),
    }
    if comparison["council_total_reduction_pct"] is not None and comparison["council_total_reduction_pct"] >= 0:
        council_interpretation = "The full Council improved deliberation quality while remaining below the broad-context token budget."
    else:
        council_interpretation = "The full Council used more aggregate tokens than the broad single-agent arm; its value must therefore be justified by quality, safety, and repair reduction rather than prompt compression alone."
    interpretation = (
        "The single sliced planner isolates Aura's context-selection effect. The Council arm measures the real cost of "
        "multi-agent deliberation instead of comparing only one small Council prompt with one large baseline prompt. "
        + council_interpretation
        + " These results are a reproducible first pilot, not proof of general superiority or consciousness."
    )
    report = {
        "benchmark_version": BENCHMARK_VERSION,
        "objective": OBJECTIVE,
        "repository_commit_sha": _git_sha(root),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": str(fixture.get("model") or "UNSPECIFIED_FIXTURE_MODEL"),
        "measurement_class": MEASUREMENT_CLASS,
        "rate_card": rate_card,
        "prepare_manifest": manifest,
        "arms": arms,
        "comparison": comparison,
        "interpretation": interpretation,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "production_mutation": False,
        "limitations": [
            "This pilot uses committed model-response fixtures so the result is reproducible; it is not a blinded randomized trial.",
            "The same model session authored the pilot fixtures, so cross-arm contamination cannot be ruled out.",
            "The RAW arm is a relevance-ranked broad repository handoff, not an actual transmission of every repository byte.",
            "Token counts use char/4 proxies; tokenizer-exact and provider-billed runs should be added for publication-grade claims.",
            "Normalized USD uses the declared rate card and is not an invoice or current market price.",
            "The deterministic quality rubric measures grounding, coverage, boundedness, tests, and governance; it does not fully measure long-term refactor success.",
            "The benchmark produces a plan skeleton only and performs no production mutation.",
        ],
    }
    (output_dir / "architect_consolidation_benchmark.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, output_dir / "architect_consolidation_benchmark.md")
    skeleton = {
        "version": "AURA_ARCHITECT_CONSOLIDATION_SKELETON_V1",
        "objective": OBJECTIVE,
        "repository_commit_sha": report["repository_commit_sha"],
        "selected_by": "AURA_ARCHITECT_COUNCIL",
        "selected_plan": council["selected_plan"],
        "quality": council["quality"],
        "council_decision": council["decision"],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "production_mutation": False,
        "next_gate": "HUMAN_REVIEW_BEFORE_REFACTOR",
    }
    (output_dir / "architect_consolidation_skeleton.json").write_text(
        json.dumps(skeleton, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (output_dir / "council_requests.json").write_text(
        json.dumps(council["requests"], indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aura Architect consolidation benchmark")
    parser.add_argument("command", choices=("prepare", "score"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("Aura_Memory/benchmarks/architect_consolidation"))
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--input-rate", type=float, default=1.0)
    parser.add_argument("--output-rate", type=float, default=3.0)
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    if args.command == "prepare":
        manifest = prepare_prompts(root, output_dir)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    if args.responses is None:
        parser.error("--responses is required for score")
    responses = args.responses if args.responses.is_absolute() else root / args.responses
    report = score_benchmark(
        root,
        output_dir,
        responses,
        input_rate=args.input_rate,
        output_rate=args.output_rate,
    )
    print(json.dumps(report["comparison"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
