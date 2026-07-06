"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c9-[Q-SYS:MUSIC_CODING_ARENA]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Research-Grounded Arena Resonance)
DEPENDENCIES: dataclasses, hashlib, json, pathlib, re, typing, numpy, aura_music_inversion
FUNCTIONS: ArenaResearchIdea, load_arena_research_ideas, classify_music_result,
score_music_arena_synthesis, fuse_music_council_plan, music_builder_objective,
augment_act_tasks_with_music
SYNOPSIS: Uses bounded MUSIC component search to pair Coding Arena plan
candidates with related local arXiv/research-memory ideas, then proposes a
bounded council-fusion candidate. This never bypasses Arena verification.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import blake2b
import json
from pathlib import Path
import re
from typing import Any, Mapping

import numpy as np

from aura_music_inversion import music_component_search


DEFAULT_FEATURE_DIMENSIONS = 256
DEFAULT_PROJECTION_DIM = 64
RESEARCH_POLICY_VERSION = "AURA_MUSIC_RESEARCH_POLICY_V2"
PATCH_ELIGIBLE = "PATCH_ELIGIBLE"
RESEARCH_ANALOGY_ONLY = "RESEARCH_ANALOGY_ONLY"
BLOCKED = "BLOCKED"
_CLASSIFICATION_WEIGHT = {
    PATCH_ELIGIBLE: 2,
    RESEARCH_ANALOGY_ONLY: 1,
    BLOCKED: 0,
}

_GENERIC_ACCEPTANCE_FRAGMENTS = (
    "extract a concrete verifier-facing acceptance check",
    "translate the retrieved arxiv idea",
    "add or preserve a local verifier check",
    "local regression or verifier metric before promotion",
)
_CONCRETE_ACCEPTANCE_TERMS = (
    "test_",
    "pytest",
    "assert",
    "regression",
    "verifier",
    "workspace verification",
    "preflight",
    "passes",
)
_BROAD_SCOPE_TERMS = (
    "rewrite",
    "entire",
    "whole",
    "all modules",
    "multi-file",
    "new subsystem",
    "architecture-wide",
    "public api",
    "schema",
)
_VAGUE_PLAN_TERMS = ("improve", "enhance", "optimize", "refactor", "upgrade")
_VERIFIER_ALIGNMENT_TERMS = (
    "pytest",
    "assert",
    "regression",
    "verifier",
    "workspace verification",
    "preflight",
)


@dataclass(frozen=True)
class ArenaResearchIdea:
    idea_id: str
    label: str
    source: str
    arxiv_id: str = ""
    target_modules: tuple[str, ...] = ()
    implementation_lesson: str = ""
    acceptance_test: str = ""
    priority: int = 5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hash_id(prefix: str, payload: str) -> str:
    return f"{prefix}-{blake2b(payload.encode('utf-8', errors='ignore'), digest_size=6).hexdigest()}"


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_./:-]{2,}", str(text or "").lower())


def _text_vector(text: str, *, dimensions: int = DEFAULT_FEATURE_DIMENSIONS) -> np.ndarray:
    """Encode text into a small deterministic complex feature vector."""
    dims = int(max(8, dimensions))
    vector = np.zeros(dims, dtype=np.complex64)
    tokens = _tokens(text) or [str(text or "empty")]
    for position, token in enumerate(tokens):
        digest = blake2b(f"{position}:{token}".encode("utf-8", errors="ignore"), digest_size=16).digest()
        bucket = int.from_bytes(digest[:4], "little") % dims
        phase_bucket = int.from_bytes(digest[4:8], "little") % 4096
        phase = np.float32((phase_bucket / 4096.0) * 2.0 * np.pi)
        sign = 1.0 if digest[8] & 1 else -1.0
        weight = np.float32(1.0 + min(3, len(token) // 8) * 0.15)
        vector[bucket] += np.complex64(sign * weight * np.exp(1j * phase))
    return _unit_vector(vector)


def _unit_vector(vector: np.ndarray) -> np.ndarray:
    arr = np.asarray(vector, dtype=np.complex64).reshape(-1)
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-12:
        return arr
    return (arr / np.float32(norm)).astype(np.complex64)


def _idea_text(idea: ArenaResearchIdea) -> str:
    return " ".join(
        item
        for item in (
            idea.label,
            idea.arxiv_id,
            " ".join(idea.target_modules),
            idea.implementation_lesson,
            idea.acceptance_test,
        )
        if item
    )


def _plan_text(candidate: Mapping[str, Any]) -> str:
    plan = candidate.get("plan", {}) if isinstance(candidate, Mapping) else {}
    if not isinstance(plan, Mapping):
        plan = {}
    fields: list[str] = [
        str(candidate.get("candidate_id", "")),
        str(candidate.get("source", "")),
        str(candidate.get("cost_tier", "")),
        str(plan.get("architecture_decision", "")),
        str(plan.get("target_file", "")),
        str(plan.get("target_symbol", "")),
        str(plan.get("objective", "")),
    ]
    for task in plan.get("act_tasks", []) or []:
        if isinstance(task, Mapping):
            fields.extend(
                [
                    str(task.get("task_id", "")),
                    str(task.get("objective", "")),
                    str(task.get("target_file", "")),
                    str(task.get("target_symbol", "")),
                    str(task.get("acceptance", "")),
                ]
            )
        else:
            fields.append(str(task))
    return " ".join(item for item in fields if item)


def _candidate_targets(candidate: Mapping[str, Any], target_file: str | None = None) -> set[str]:
    plan = candidate.get("plan", {}) if isinstance(candidate, Mapping) else {}
    targets: set[str] = set()
    for value in (target_file, plan.get("target_file") if isinstance(plan, Mapping) else None):
        if value:
            targets.add(str(value).replace("\\", "/"))
            targets.add(Path(str(value)).name)
    if isinstance(plan, Mapping):
        for task in plan.get("act_tasks", []) or []:
            if not isinstance(task, Mapping):
                continue
            task_file = task.get("target_file")
            if task_file:
                targets.add(str(task_file).replace("\\", "/"))
                targets.add(Path(str(task_file)).name)
    return {item for item in targets if item}


def _module_overlap(candidate: Mapping[str, Any], idea: ArenaResearchIdea, target_file: str | None) -> float:
    targets = _candidate_targets(candidate, target_file=target_file)
    if not targets or not idea.target_modules:
        return 0.0
    modules = {module.replace("\\", "/") for module in idea.target_modules}
    basenames = {Path(module).name for module in modules}
    if targets & modules:
        return 1.0
    if targets & basenames:
        return 0.85
    if any(target in module or module in target for target in targets for module in modules):
        return 0.55
    return 0.0


def _priority_score(priority: int) -> float:
    return 1.0 / (1.0 + max(0, int(priority)))


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _normalize_path(path: Any) -> str:
    normalized = str(path or "").replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _codemap_paths(codemap: Mapping[str, Any] | None) -> set[str]:
    if not codemap:
        return set()
    paths: set[str] = set()
    coverage = codemap.get("coverage", {}) if isinstance(codemap.get("coverage"), Mapping) else {}
    for item in coverage.get("all_included_paths_sorted", []) or []:
        normalized = _normalize_path(item)
        if normalized:
            paths.add(normalized)
    for key in ("file_cards", "files"):
        for card in codemap.get(key, []) or []:
            if isinstance(card, Mapping):
                normalized = _normalize_path(card.get("path"))
                if normalized:
                    paths.add(normalized)
    return paths


def _module_manifest_paths(manifest: Mapping[str, Any] | None) -> set[str]:
    if not manifest:
        return set()
    paths: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key in ("path", "file", "module", "target_file"):
                normalized = _normalize_path(value.get(key))
                if normalized.endswith(".py") or "/" in normalized:
                    paths.add(normalized)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str):
            normalized = _normalize_path(value)
            if normalized.endswith(".py"):
                paths.add(normalized)

    visit(manifest)
    return paths


def _file_card(codemap: Mapping[str, Any] | None, target_file: str) -> Mapping[str, Any]:
    if not codemap:
        return {}
    for key in ("file_cards", "files"):
        for card in codemap.get(key, []) or []:
            if isinstance(card, Mapping) and _normalize_path(card.get("path")) == target_file:
                return card
    return {}


def _symbol_exists(codemap: Mapping[str, Any] | None, target_file: str, target_symbol: str | None) -> bool:
    if not target_symbol:
        return True
    if not codemap:
        return False
    symbol_index = codemap.get("symbol_index", {}) if isinstance(codemap.get("symbol_index"), Mapping) else {}
    for hit in symbol_index.get(str(target_symbol), []) or []:
        if isinstance(hit, Mapping) and _normalize_path(hit.get("file")) == target_file:
            return True
    card = _file_card(codemap, target_file)
    for symbol in card.get("symbols", []) or []:
        if isinstance(symbol, Mapping) and str(symbol.get("name", "")) == str(target_symbol):
            return True
    return False


def _test_files_for_target(root: Path, codemap: Mapping[str, Any] | None, target_file: str) -> list[str]:
    stem = Path(target_file).stem
    candidates = [f"test_{stem}.py", f"tests/test_{stem}.py"]
    card = _file_card(codemap, target_file)
    topology = card.get("topology", {}) if isinstance(card, Mapping) else {}
    for item in topology.get("neighbor_files", []) or []:
        normalized = _normalize_path(item)
        if normalized and ("test" in Path(normalized).name.lower() or normalized.startswith("tests/")):
            candidates.append(normalized)
    seen: set[str] = set()
    tests: list[str] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (root / candidate).exists():
            tests.append(candidate)
    return tests


def _generic_acceptance(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if not lowered:
        return True
    return any(fragment in lowered for fragment in _GENERIC_ACCEPTANCE_FRAGMENTS)


def _concrete_acceptance(text: str) -> bool:
    lowered = str(text or "").strip().lower()
    if _generic_acceptance(lowered):
        return False
    return len(lowered) >= 16 and any(term in lowered for term in _CONCRETE_ACCEPTANCE_TERMS)


def _candidate_plan(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    plan = candidate.get("plan", {}) if isinstance(candidate, Mapping) else {}
    return plan if isinstance(plan, Mapping) else {}


def _candidate_target(candidate: Mapping[str, Any], target_file: str | None, target_symbol: str | None) -> tuple[str, str | None]:
    plan = _candidate_plan(candidate)
    file_value = _normalize_path(plan.get("target_file") or target_file)
    symbol_value = plan.get("target_symbol") or target_symbol
    for task in plan.get("act_tasks", []) or []:
        if not isinstance(task, Mapping):
            continue
        if not file_value:
            file_value = _normalize_path(task.get("target_file"))
        if symbol_value is None and task.get("target_symbol"):
            symbol_value = str(task.get("target_symbol"))
    return file_value, str(symbol_value) if symbol_value else None


def _plan_acceptance(candidate: Mapping[str, Any], idea: ArenaResearchIdea) -> str:
    plan = _candidate_plan(candidate)
    parts = [idea.acceptance_test]
    for task in plan.get("act_tasks", []) or []:
        if isinstance(task, Mapping):
            parts.append(str(task.get("acceptance", "")))
    return " ".join(part for part in parts if part)


def _generated_test_plan(acceptance: str) -> bool:
    lowered = acceptance.lower()
    return any(term in lowered for term in ("generated test", "add regression test", "create test", "test plan"))


def _acceptance_alignment(
    acceptance: str,
    *,
    target_file: str,
    target_symbol: str | None,
    test_files: list[str],
) -> dict[str, Any]:
    lowered = str(acceptance or "").lower()
    hits: list[str] = []
    known_tests = {_normalize_path(item).lower() for item in test_files}
    known_test_names = {Path(item).name.lower() for item in known_tests}
    mentioned_tests = {
        _normalize_path(match).lower()
        for match in re.findall(r"(?:[\w./-]+/)?test_[\w.-]+\.py", lowered)
    }
    matched_tests = sorted(
        test
        for test in mentioned_tests
        if test in known_tests or Path(test).name.lower() in known_test_names
    )
    if matched_tests:
        hits.extend(f"test_file:{item}" for item in matched_tests)
    if mentioned_tests and not matched_tests:
        return {
            "ok": False,
            "hits": hits,
            "mentioned_test_files": sorted(mentioned_tests),
            "missing_test_files": sorted(mentioned_tests),
        }

    target_file_lower = target_file.lower()
    target_stem = Path(target_file).stem.lower() if target_file else ""
    if target_file_lower and (target_file_lower in lowered or (target_stem and target_stem in lowered)):
        hits.append("target_file")
    if target_symbol and target_symbol.lower() in lowered:
        hits.append("target_symbol")
    for term in _VERIFIER_ALIGNMENT_TERMS:
        if term in lowered:
            hits.append(f"verifier:{term}")
    return {
        "ok": bool(hits),
        "hits": sorted(set(hits)),
        "mentioned_test_files": sorted(mentioned_tests),
        "missing_test_files": [],
    }


def _critic_report_policy(candidate: Mapping[str, Any]) -> dict[str, Any]:
    reports = candidate.get("critic_reports", []) if isinstance(candidate, Mapping) else []
    rejected_domains: list[str] = []
    blocking_domains: list[str] = []
    penalties: list[str] = []
    for report in reports or []:
        if not isinstance(report, Mapping):
            continue
        approved = report.get("approved")
        approved_bool = approved is True or str(approved).strip().lower() == "true"
        if approved_bool:
            continue
        critic_id = str(report.get("critic_id") or "critic").strip().lower()
        rejected_domains.append(critic_id)
        blockers = " ".join(str(item) for item in report.get("blockers", []) or []).lower()
        if critic_id in {"scope", "tests"} or "scope" in blockers or "test" in blockers or "verifier" in blockers:
            blocking_domains.append(critic_id)
        if critic_id:
            penalties.append(f"critic_rejected_{critic_id}")
    return {
        "rejected_domains": sorted(set(rejected_domains)),
        "blocking_domains": sorted(set(blocking_domains)),
        "penalties": sorted(set(penalties)),
        "hard_block": bool(blocking_domains),
    }


def _scope_stats(candidate: Mapping[str, Any]) -> dict[str, Any]:
    plan = _candidate_plan(candidate)
    tasks = [task for task in plan.get("act_tasks", []) or [] if isinstance(task, Mapping)]
    files = {
        _normalize_path(plan.get("target_file")),
        *(_normalize_path(task.get("target_file")) for task in tasks),
    }
    files.discard("")
    text = " ".join(
        [
            str(plan.get("architecture_decision", "")),
            str(plan.get("objective", "")),
            *(str(task.get(key, "")) for task in tasks for key in ("objective", "acceptance", "allowed_scope", "size")),
        ]
    ).lower()
    broad_hits = [term for term in _BROAD_SCOPE_TERMS if term in text]
    vague_hits = [term for term in _VAGUE_PLAN_TERMS if term in text]
    large_topology_terms = re.findall(r"\b\d{4,}\s+(?:edges|nodes|files|modules|symbols|functions)\b", text)
    task_sizes = [str(task.get("size", "")).upper() for task in tasks]
    too_broad = (
        len(tasks) > 2
        or len(files) > 2
        or len(broad_hits) >= 2
        or bool(large_topology_terms)
        or any(size in {"L", "XL"} for size in task_sizes)
    )
    vague = bool(vague_hits) and not any(str(task.get("target_symbol", "")).strip() for task in tasks)
    return {
        "task_count": len(tasks),
        "target_file_count": len(files),
        "broad_terms": broad_hits,
        "vague_terms": vague_hits,
        "large_topology_terms": large_topology_terms,
        "too_broad": too_broad,
        "vague": vague,
    }


def classify_music_result(
    candidate: Mapping[str, Any],
    idea: ArenaResearchIdea | Mapping[str, Any],
    *,
    repo_root: str | Path,
    target_file: str | None = None,
    target_symbol: str | None = None,
    module_overlap: float = 0.0,
    normalized_music_score: float = 0.0,
) -> dict[str, Any]:
    """Classify MUSIC-ranked candidate::research pairings before Act creation."""
    root = Path(repo_root).resolve()
    codemap = _load_json(root / ".aura" / "CODEMAP.json")
    manifest = _load_json(root / ".aura" / "MODULE_MANIFEST.json")
    if isinstance(idea, ArenaResearchIdea):
        research = idea
    else:
        research = ArenaResearchIdea(
            idea_id=str(idea.get("idea_id") or idea.get("research_id") or "research"),
            label=str(idea.get("label") or idea.get("arxiv_id") or "research"),
            source=str(idea.get("source") or "research"),
            arxiv_id=str(idea.get("arxiv_id") or ""),
            target_modules=tuple(str(item) for item in idea.get("target_modules", []) or []),
            implementation_lesson=str(idea.get("implementation_lesson") or ""),
            acceptance_test=str(idea.get("acceptance_test") or ""),
            priority=int(idea.get("priority", 5) or 5),
        )

    resolved_file, resolved_symbol = _candidate_target(candidate, target_file, target_symbol)
    codemap_paths = _codemap_paths(codemap)
    manifest_paths = _module_manifest_paths(manifest)
    acceptance = _plan_acceptance(candidate, research)
    concrete_acceptance = _concrete_acceptance(acceptance)
    test_files = _test_files_for_target(root, codemap, resolved_file) if resolved_file else []
    has_generated_test_plan = _generated_test_plan(acceptance)
    acceptance_alignment = _acceptance_alignment(
        acceptance,
        target_file=resolved_file,
        target_symbol=resolved_symbol,
        test_files=test_files,
    )
    scope = _scope_stats(candidate)
    critic_policy = _critic_report_policy(candidate)
    target_exists = bool(resolved_file and (root / resolved_file).exists())
    codemap_file_hit = bool(resolved_file and resolved_file in codemap_paths)
    manifest_file_hit = True if manifest is None else bool(resolved_file and resolved_file in manifest_paths)
    symbol_exists = _symbol_exists(codemap, resolved_file, resolved_symbol)
    target_modules = {_normalize_path(item) for item in research.target_modules if _normalize_path(item)}
    target_basenames = {Path(item).name for item in target_modules}
    repo_grounded_path = bool(
        target_modules
        and module_overlap > 0.0
        and resolved_file
        and (resolved_file in target_modules or Path(resolved_file).name in target_basenames)
    )

    reasons: list[str] = []
    penalties: list[str] = []
    blockers: list[str] = []
    analogies: list[str] = []

    if codemap is None:
        blockers.append("codemap_unavailable")
    if not resolved_file or not target_exists or not codemap_file_hit or not manifest_file_hit:
        blockers.append("target_file_unresolved")
    if resolved_symbol and not symbol_exists:
        blockers.append("target_symbol_unresolved")
    if not test_files and not has_generated_test_plan:
        blockers.append("missing_tests_or_verifier_evidence")
    if scope["too_broad"]:
        blockers.append("act_capsule_too_broad")
    if critic_policy["hard_block"]:
        blockers.append("critic_reports_rejected_scope_or_tests")

    if not research.target_modules:
        analogies.append("research_has_no_target_modules")
    if module_overlap <= 0.0:
        analogies.append("missing_module_overlap")
    if not concrete_acceptance:
        analogies.append("missing_concrete_acceptance_test")
    if concrete_acceptance and not acceptance_alignment["ok"]:
        analogies.append("acceptance_not_aligned_to_target_or_verifier")
    if _generic_acceptance(research.acceptance_test):
        analogies.append("generic_research_acceptance")
    if not repo_grounded_path:
        analogies.append("no_repo_grounded_implementation_path")

    if scope["vague"]:
        penalties.append("vague_plan")
    if resolved_file == "aura_node.py" and "aura_node.py" not in target_modules:
        penalties.append("defaulting_new_subsystem_to_aura_node")
    if normalized_music_score >= 0.75 and module_overlap <= 0.0:
        penalties.append("high_music_score_without_module_overlap")
    if analogies:
        penalties.append("research_analogy_not_implementation_evidence")
    penalties.extend(str(item) for item in critic_policy["penalties"])

    if blockers:
        classification = BLOCKED
        reasons.extend(blockers)
        reasons.extend(item for item in analogies if item not in reasons)
    elif analogies:
        classification = RESEARCH_ANALOGY_ONLY
        reasons.extend(analogies)
    else:
        classification = PATCH_ELIGIBLE
        reasons.append("grounded_patch_candidate")

    return {
        "policy_version": RESEARCH_POLICY_VERSION,
        "classification": classification,
        "reasons": reasons,
        "blockers": blockers,
        "analogy_reasons": analogies,
        "penalties": penalties,
        "research_source": research.source,
        "target_file": resolved_file,
        "target_symbol": resolved_symbol,
        "module_overlap": round(float(module_overlap), 6),
        "concrete_acceptance": concrete_acceptance,
        "acceptance_alignment": acceptance_alignment,
        "acceptance_test": research.acceptance_test,
        "test_files": test_files,
        "generated_test_plan": has_generated_test_plan,
        "codemap_file_hit": codemap_file_hit,
        "module_manifest_checked": manifest is not None,
        "module_manifest_file_hit": manifest_file_hit,
        "symbol_exists": symbol_exists,
        "repo_grounded_path": repo_grounded_path,
        "critic_evidence": critic_policy,
        "scope": scope,
    }


def _manifest_ideas(root: Path) -> list[ArenaResearchIdea]:
    path = root / ".aura" / "RESEARCH_MANIFEST.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    ideas: list[ArenaResearchIdea] = []
    for row in data.get("papers", []) if isinstance(data, dict) else []:
        if not isinstance(row, dict):
            continue
        arxiv_id = str(row.get("arxiv_id", "")).strip()
        label = str(row.get("label") or arxiv_id or "research_manifest_entry").strip()
        payload = json.dumps(row, sort_keys=True, default=str)
        ideas.append(
            ArenaResearchIdea(
                idea_id=_hash_id("manifest", payload),
                label=label,
                source="research_manifest",
                arxiv_id=arxiv_id,
                target_modules=tuple(str(item) for item in row.get("target_modules", []) or []),
                implementation_lesson=str(row.get("implementation_lesson", "")),
                acceptance_test=str(row.get("acceptance_test", "")),
                priority=int(row.get("priority", 5) or 5),
            )
        )
    return ideas


def _paper_memory_ideas(root: Path, *, limit: int) -> list[ArenaResearchIdea]:
    path = root / "Aura_Memory" / "paper_memory_ledger.jsonl"
    if not path.exists():
        return []
    ideas: list[ArenaResearchIdea] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if len(ideas) >= limit:
                    break
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or row.get("doc_id") or "paper_memory_record").strip()
                points = row.get("three_main_points", []) or []
                if isinstance(points, list):
                    lesson = " ".join(str(item) for item in points[:3])
                else:
                    lesson = str(points)
                if not lesson:
                    lesson = str(row.get("summary_capsule", ""))
                payload = json.dumps({"title": title, "lesson": lesson}, sort_keys=True)
                ideas.append(
                    ArenaResearchIdea(
                        idea_id=_hash_id("paper", payload),
                        label=title[:96],
                        source="paper_memory_ledger",
                        implementation_lesson=lesson[:600],
                        acceptance_test="Extract a concrete verifier-facing acceptance check from the paper memory before promotion.",
                        priority=4,
                    )
                )
    except OSError:
        return []
    return ideas


def _arxiv_cache_ideas(root: Path, *, limit: int) -> list[ArenaResearchIdea]:
    cache_root = root / "Aura_Memory" / "arxiv_cache"
    if not cache_root.exists():
        return []
    ideas: list[ArenaResearchIdea] = []
    for path in sorted(cache_root.glob("*.json"))[:limit]:
        try:
            row = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        paper_id = str(row.get("paper_id") or row.get("id") or path.stem)
        title = str(row.get("title") or paper_id).strip()
        abstract = str(row.get("abstract") or "").strip()
        categories = row.get("categories", []) or []
        if isinstance(categories, str):
            categories_text = categories
        else:
            categories_text = " ".join(str(item) for item in categories)
        payload = json.dumps({"paper_id": paper_id, "title": title, "abstract": abstract}, sort_keys=True)
        ideas.append(
            ArenaResearchIdea(
                idea_id=_hash_id("arxiv", payload),
                label=title[:96],
                source="arxiv_cache",
                arxiv_id=paper_id,
                implementation_lesson=(abstract or categories_text)[:700],
                acceptance_test="Translate the retrieved arXiv idea into a local regression or verifier metric before promotion.",
                priority=6,
            )
        )
    return ideas


def load_arena_research_ideas(repo_root: str | Path, *, limit: int = 32) -> list[ArenaResearchIdea]:
    """Load local manifest, paper-memory, and arXiv-cache ideas for arena synthesis."""
    root = Path(repo_root).resolve()
    ideas: list[ArenaResearchIdea] = []
    ideas.extend(_manifest_ideas(root))
    remaining = max(0, limit - len(ideas))
    if remaining:
        ideas.extend(_paper_memory_ideas(root, limit=remaining))
    remaining = max(0, limit - len(ideas))
    if remaining:
        ideas.extend(_arxiv_cache_ideas(root, limit=remaining))

    deduped: dict[str, ArenaResearchIdea] = {}
    for idea in ideas:
        key = idea.arxiv_id or idea.idea_id
        deduped.setdefault(key, idea)
    return sorted(deduped.values(), key=lambda item: (item.priority, item.label))[:limit]


def _pair_key(candidate_id: str, idea_id: str) -> str:
    return f"{candidate_id}::{idea_id}"


def _split_pair_key(pair_key: str) -> tuple[str, str]:
    left, sep, right = pair_key.partition("::")
    return left, right if sep else ""


def _synthesis_line(candidate: Mapping[str, Any], idea: ArenaResearchIdea) -> str:
    lesson = idea.implementation_lesson.strip() or "Use this research entry as a bounded implementation prior."
    acceptance = idea.acceptance_test.strip() or "Add or preserve a local verifier check for the research-derived change."
    label = f"{idea.label} ({idea.arxiv_id})" if idea.arxiv_id else idea.label
    source = str(candidate.get("source") or candidate.get("candidate_id") or "selected plan")
    return (
        f"Mitosis synthesis: combine {source} with {label}: {lesson} "
        f"Verifier-facing acceptance: {acceptance}"
    )


def _short_text(value: Any, *, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip()


def _candidate_by_id(candidates: list[dict[str, Any]], candidate_id: str) -> dict[str, Any] | None:
    for candidate in candidates:
        if str(candidate.get("candidate_id", "")) == candidate_id:
            return candidate
    return None


def _ranked_candidate_ids(candidates: list[dict[str, Any]], anchor_id: str) -> list[str]:
    def score(candidate: dict[str, Any]) -> float:
        try:
            return float(candidate.get("score", 0.0) or 0.0)
        except Exception:
            return 0.0

    ordered = sorted(candidates, key=score, reverse=True)
    ids: list[str] = []
    if anchor_id:
        ids.append(anchor_id)
    for candidate in ordered:
        candidate_id = str(candidate.get("candidate_id", ""))
        if candidate_id and candidate_id not in ids:
            ids.append(candidate_id)
    return ids


def _copy_task(task: Any, *, index: int, fallback_target: str | None, fallback_symbol: str | None) -> dict[str, Any]:
    if isinstance(task, Mapping):
        copied = dict(task)
    else:
        copied = {"objective": str(task)}
    copied.setdefault("task_id", f"MUSIC-FUSED-{index + 1}")
    if copied.get("target_file") is None:
        copied["target_file"] = fallback_target
    if copied.get("target_symbol") is None:
        copied["target_symbol"] = fallback_symbol
    copied.setdefault("allowed_scope", "single music-mitosis fused Act Capsule")
    copied.setdefault("expected_output", "UNIFIED_DIFF")
    return copied


def _merge_plan_text(candidates: list[dict[str, Any]], candidate_ids: list[str], field: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for candidate_id in candidate_ids:
        candidate = _candidate_by_id(candidates, candidate_id)
        plan = candidate.get("plan", {}) if candidate else {}
        value = _short_text(plan.get(field, "") if isinstance(plan, Mapping) else "")
        if value and value not in seen:
            values.append(value)
            seen.add(value)
    return values


def _supporting_task_summaries(candidates: list[dict[str, Any]], candidate_ids: list[str], *, limit: int = 3) -> list[str]:
    summaries: list[str] = []
    seen: set[str] = set()
    for candidate_id in candidate_ids:
        candidate = _candidate_by_id(candidates, candidate_id)
        plan = candidate.get("plan", {}) if candidate else {}
        if not isinstance(plan, Mapping):
            continue
        for task in plan.get("act_tasks", []) or []:
            if not isinstance(task, Mapping):
                objective = _short_text(task)
            else:
                objective = _short_text(task.get("objective", "") or task.get("acceptance", ""))
            if objective and objective not in seen:
                summaries.append(objective)
                seen.add(objective)
            if len(summaries) >= limit:
                return summaries
    return summaries


def _build_fused_plan(
    *,
    intent: str,
    candidates: list[dict[str, Any]],
    synthesis: dict[str, Any],
    target_file: str | None,
    target_symbol: str | None,
) -> dict[str, Any]:
    selected_id = str(synthesis.get("selected_candidate_id", ""))
    supporting_ids = _ranked_candidate_ids(candidates, selected_id)[:3]
    anchor = _candidate_by_id(candidates, supporting_ids[0]) if supporting_ids else None
    anchor_plan = dict(anchor.get("plan", {}) if anchor else {})
    research = synthesis.get("selected_research", {}) or {}

    target = anchor_plan.get("target_file") or target_file
    symbol = anchor_plan.get("target_symbol") or target_symbol
    for candidate_id in supporting_ids:
        candidate = _candidate_by_id(candidates, candidate_id)
        if not candidate:
            continue
        candidate_target, candidate_symbol = _candidate_target(candidate, target, symbol)
        if not target and candidate_target:
            target = candidate_target
        if not symbol and candidate_symbol:
            symbol = candidate_symbol
        if target and symbol:
            break
    plan_decisions = _merge_plan_text(candidates, supporting_ids, "architecture_decision")
    supporting_tasks = _supporting_task_summaries(candidates, supporting_ids[1:] or supporting_ids)
    research_label = str(research.get("label") or research.get("arxiv_id") or "local research")
    research_lesson = _short_text(research.get("implementation_lesson", ""), limit=360)
    research_acceptance = _short_text(research.get("acceptance_test", ""), limit=260)

    decision_parts = [
        "MUSIC mitosis-fused council plan.",
        f"Anchor candidate: {supporting_ids[0] if supporting_ids else 'local_free'}.",
    ]
    if len(supporting_ids) > 1:
        decision_parts.append(f"Complementary candidates: {', '.join(supporting_ids[1:])}.")
    if plan_decisions:
        decision_parts.append("Council synthesis: " + " | ".join(plan_decisions[:3]))
    if research_lesson:
        decision_parts.append(f"Research stabilizer {research_label}: {research_lesson}")

    anchor_tasks = list(anchor_plan.get("act_tasks", []) or [])
    if not anchor_tasks:
        anchor_tasks = [
            {
                "task_id": "MUSIC-FUSED-1",
                "objective": intent,
                "target_file": target,
                "target_symbol": symbol,
                "acceptance": "Return a unified diff that applies cleanly in the temporary workspace and passes local verification.",
                "expected_output": "UNIFIED_DIFF",
            }
        ]

    fused_tasks: list[dict[str, Any]] = []
    hint = str(synthesis.get("builder_hint") or synthesis.get("synthesis") or "").strip()
    complement = " ".join(supporting_tasks[:2])
    for index, task in enumerate(anchor_tasks[:3]):
        copied = _copy_task(task, index=index, fallback_target=target, fallback_symbol=symbol)
        objective_parts = [_short_text(copied.get("objective", ""), limit=500)]
        if complement:
            objective_parts.append(f"Council complement: {complement}")
        if hint:
            objective_parts.append(hint)
        copied["objective"] = "\n\n".join(item for item in objective_parts if item)

        acceptance_parts = [_short_text(copied.get("acceptance", ""), limit=420)]
        if research_acceptance:
            acceptance_parts.append(f"Research acceptance: {research_acceptance}")
        if complement:
            acceptance_parts.append("Preserve the complementary council constraints while staying within the declared target scope.")
        copied["acceptance"] = " ".join(item for item in acceptance_parts if item)
        copied["role"] = copied.get("role", "music_mitosis_builder")
        copied_scope = str(copied.get("allowed_scope") or "").strip()
        if not copied_scope or copied_scope == "single live Architect Act Capsule":
            copied["allowed_scope"] = (
                "single music-mitosis fused symbol Act Capsule"
                if copied.get("target_symbol")
                else "single music-mitosis fused file Act Capsule"
            )
        fused_tasks.append(copied)

    return {
        "architecture_decision": " ".join(decision_parts),
        "target_file": str(target) if target else None,
        "target_symbol": str(symbol) if symbol else None,
        "act_tasks": fused_tasks,
        "source": "music_mitosis_fusion",
        "objective": intent,
        "music_mitosis": {
            "status": synthesis.get("status"),
            "supporting_candidate_ids": supporting_ids,
            "selected_research": research,
            "synthesis": synthesis.get("synthesis"),
            "builder_hint": synthesis.get("builder_hint"),
            "acceptance_test": synthesis.get("acceptance_test"),
        },
    }


def score_music_arena_synthesis(
    intent: str,
    candidates: list[dict[str, Any]],
    *,
    repo_root: str | Path,
    target_file: str | None = None,
    target_symbol: str | None = None,
    top_k: int = 5,
    dimensions: int = DEFAULT_FEATURE_DIMENSIONS,
    projection_dim: int = DEFAULT_PROJECTION_DIM,
) -> dict[str, Any]:
    """
    Rank plan-candidate/research-idea pairs with bounded MUSIC component search.

    The eigendecomposition path only sees the projected covariance reported in
    diagnostics. This function is deterministic and advisory.
    """
    bounded_candidates = list(candidates or [])[:8]
    ideas = load_arena_research_ideas(repo_root, limit=24)
    if not bounded_candidates:
        return {"status": "disabled", "reason": "no_plan_candidates"}
    if not ideas:
        return {"status": "disabled", "reason": "no_local_research_ideas"}

    intent_vec = _text_vector(f"intent {intent}", dimensions=dimensions)
    target_vec = _text_vector(f"target {target_file or ''} {target_symbol or ''}", dimensions=dimensions)
    plan_vectors = {
        str(candidate.get("candidate_id") or f"candidate_{index}"): _text_vector(_plan_text(candidate), dimensions=dimensions)
        for index, candidate in enumerate(bounded_candidates)
    }
    snapshot_columns = [intent_vec, target_vec, *plan_vectors.values()]
    snapshots = np.stack(snapshot_columns, axis=1).astype(np.complex64)

    component_library: dict[str, np.ndarray] = {}
    pair_meta: dict[str, dict[str, Any]] = {}
    for candidate in bounded_candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id:
            continue
        plan_vec = plan_vectors[candidate_id]
        for idea in ideas:
            overlap = _module_overlap(candidate, idea, target_file)
            idea_vec = _text_vector(_idea_text(idea), dimensions=dimensions)
            pair_vector = _unit_vector(
                np.float32(0.55) * plan_vec
                + np.float32(0.35) * idea_vec
                + np.float32(0.20 + overlap * 0.25) * target_vec
                + np.float32(0.15) * intent_vec
            )
            key = _pair_key(candidate_id, idea.idea_id)
            component_library[key] = pair_vector
            pair_meta[key] = {
                "candidate": candidate,
                "idea": idea,
                "module_overlap": overlap,
            }

    if not component_library:
        return {"status": "disabled", "reason": "no_pair_components"}

    signal_count = max(1, min(3, snapshots.shape[1] - 1, projection_dim - 1))
    music_result = music_component_search(
        snapshots,
        component_library,
        signal_count=signal_count,
        top_k=min(max(1, top_k), len(component_library)),
        projection_dim=projection_dim,
        max_snapshots=64,
    )
    max_music = max((float(score) for score in music_result.scores.values()), default=1.0)
    if max_music <= 0:
        max_music = 1.0

    ranked: list[dict[str, Any]] = []
    for key, music_score in music_result.scores.items():
        candidate_id, idea_id = _split_pair_key(key)
        meta = pair_meta[key]
        candidate = meta["candidate"]
        idea: ArenaResearchIdea = meta["idea"]
        normalized_music = float(music_score) / max_music
        try:
            candidate_score = float(candidate.get("score", 0.0) or 0.0)
        except Exception:
            candidate_score = 0.0
        priority = _priority_score(idea.priority)
        overlap = float(meta["module_overlap"])
        policy = classify_music_result(
            candidate,
            idea,
            repo_root=repo_root,
            target_file=target_file,
            target_symbol=target_symbol,
            module_overlap=overlap,
            normalized_music_score=normalized_music,
        )
        combined = min(1.0, normalized_music * 0.72 + candidate_score * 0.16 + overlap * 0.09 + priority * 0.03)
        combined = max(0.0, combined - len(policy["penalties"]) * 0.07)
        if policy["classification"] == RESEARCH_ANALOGY_ONLY:
            combined = min(combined, 0.49)
        elif policy["classification"] == BLOCKED:
            combined = min(combined, 0.05)
        ranked.append(
            {
                "pair_id": key,
                "candidate_id": candidate_id,
                "research_id": idea_id,
                "music_score": round(float(music_score), 6),
                "normalized_music_score": round(normalized_music, 6),
                "candidate_score": round(candidate_score, 6),
                "module_overlap": round(overlap, 6),
                "priority_score": round(priority, 6),
                "combined_score": round(combined, 6),
                "classification": policy["classification"],
                "grounding": policy,
                "selected_research": idea.to_dict(),
                "synthesis": _synthesis_line(candidate, idea),
            }
        )
    ranked.sort(
        key=lambda item: (
            _CLASSIFICATION_WEIGHT.get(str(item.get("classification")), 0),
            item["combined_score"],
            item["module_overlap"],
            item["priority_score"],
        ),
        reverse=True,
    )

    best_by_candidate: dict[str, dict[str, Any]] = {}
    for item in ranked:
        best_by_candidate.setdefault(item["candidate_id"], item)

    selected = ranked[0]
    diagnostics = music_result.to_dict()
    diagnostics["singular_values"] = diagnostics.get("singular_values", [])[:8]
    diagnostics["feature_dimensions"] = dimensions
    diagnostics["projection_dim"] = projection_dim
    diagnostics["ideas_considered"] = len(ideas)
    diagnostics["pairs_considered"] = len(component_library)
    return {
        "status": "ready",
        "version": "AURA_MUSIC_CODING_ARENA_V1",
        "selected_candidate_id": selected["candidate_id"],
        "selected_research_id": selected["research_id"],
        "classification": selected["classification"],
        "grounding": selected["grounding"],
        "selected_research": selected["selected_research"],
        "synthesis": selected["synthesis"],
        "builder_hint": (
            "MUSIC_MITOSIS: "
            f"{selected['synthesis']} Keep the patch scoped to the selected Act Capsule and preserve verifier gates."
        ),
        "acceptance_test": selected["selected_research"].get("acceptance_test", ""),
        "ranked_pairs": ranked[:top_k],
        "best_by_candidate": best_by_candidate,
        "diagnostics": diagnostics,
    }


def fuse_music_council_plan(
    intent: str,
    candidates: list[dict[str, Any]],
    *,
    repo_root: str | Path,
    target_file: str | None = None,
    target_symbol: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Create a bounded council-fusion candidate from plan candidates plus research."""
    synthesis = score_music_arena_synthesis(
        intent,
        candidates,
        repo_root=repo_root,
        target_file=target_file,
        target_symbol=target_symbol,
        top_k=top_k,
    )
    if synthesis.get("status") != "ready":
        return synthesis
    if synthesis.get("classification") != PATCH_ELIGIBLE:
        return {
            **synthesis,
            "fusion_candidate_id": "music_mitosis_fusion",
            "fusion_blocked": True,
            "fused_score": 0.0,
        }

    selected_id = str(synthesis.get("selected_candidate_id", ""))
    ranked_ids = _ranked_candidate_ids(candidates, selected_id)
    candidate_scores = []
    for candidate_id in ranked_ids[:3]:
        candidate = _candidate_by_id(candidates, candidate_id)
        if not candidate:
            continue
        try:
            candidate_scores.append(float(candidate.get("score", 0.0) or 0.0))
        except Exception:
            candidate_scores.append(0.0)
    fused_plan = _build_fused_plan(
        intent=intent,
        candidates=candidates,
        synthesis=synthesis,
        target_file=target_file,
        target_symbol=target_symbol,
    )
    selected_score = float((synthesis.get("ranked_pairs") or [{"combined_score": 0.0}])[0].get("combined_score", 0.0))
    fused_score = min(0.97, max(candidate_scores or [0.5]) + 0.08, selected_score)
    return {
        **synthesis,
        "fusion_candidate_id": "music_mitosis_fusion",
        "supporting_candidate_ids": ranked_ids[:3],
        "fused_score": round(fused_score, 6),
        "fused_plan": fused_plan,
    }


def music_builder_objective(objective: str, synthesis: Mapping[str, Any] | None) -> str:
    if not synthesis or synthesis.get("status") != "ready" or synthesis.get("classification") != PATCH_ELIGIBLE:
        return objective
    hint = str(synthesis.get("builder_hint") or "").strip()
    if not hint or hint in objective:
        return objective
    return f"{objective}\n\n{hint}"


def augment_act_tasks_with_music(
    act_tasks: list[str | dict[str, Any]],
    synthesis: Mapping[str, Any] | None,
) -> list[str | dict[str, Any]]:
    """Return Act tasks with the selected MUSIC research hint folded into objectives."""
    if not synthesis or synthesis.get("status") != "ready" or synthesis.get("classification") != PATCH_ELIGIBLE:
        return list(act_tasks)
    hint = str(synthesis.get("builder_hint") or synthesis.get("synthesis") or "").strip()
    acceptance_test = str(synthesis.get("acceptance_test") or "").strip()
    if not hint and not acceptance_test:
        return list(act_tasks)

    augmented: list[str | dict[str, Any]] = []
    for task in act_tasks:
        if isinstance(task, Mapping):
            updated = dict(task)
            objective = str(updated.get("objective", "")).strip()
            if hint and hint not in objective:
                updated["objective"] = f"{objective}\n\n{hint}" if objective else hint
            if acceptance_test:
                acceptance = str(updated.get("acceptance", "")).strip()
                if acceptance_test not in acceptance:
                    updated["acceptance"] = (
                        f"{acceptance} Research acceptance: {acceptance_test}"
                        if acceptance
                        else f"Research acceptance: {acceptance_test}"
                    )
            augmented.append(updated)
        else:
            text = str(task)
            augmented.append(f"{text}\n\n{hint}" if hint and hint not in text else task)
    return augmented
