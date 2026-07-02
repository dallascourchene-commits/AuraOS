"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c7-[Q-SYS:EMPIRICAL_SOFTWARE_LAB]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Scorable Tasks / Sandboxed Empirical Search)
DEPENDENCIES: dataclasses, hashlib, json, math, pathlib, time, typing
FUNCTIONS: EmpiricalTask, EmpiricalCandidate, EmpiricalScoreCard, EmpiricalRunResult,
define_empirical_task, generate_candidate, score_candidate, select_next_candidate_ucb,
record_empirical_result, recommend_promotion
SYNOPSIS: Adapts Empirical Research Assistance-style scorable software search to AuraOS.
Aura subsystems become bounded empirical tasks. Candidate changes are scored from
local verifier artifacts and recorded for human-visible promotion review only.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import blake2b
import json
import math
from pathlib import Path
import time
from typing import Any

from aura_harness_evolver import analyze_transaction_outcome, record_harness_prediction
from aura_module_manifest import generate_module_manifest, module_exists, summarize_module_manifest

try:
    from aura_repair_kg import build_repair_kg
except Exception:
    build_repair_kg = None  # type: ignore[assignment]


EMPIRICAL_LEDGER = Path("Aura_Staging") / "empirical_candidate_tree.jsonl"

TASK_DEFINITIONS: dict[str, dict[str, Any]] = {
    "patch_repair": {
        "metric_name": "patch_repair_score",
        "target_modules": [
            "aura_patch_quality_gate.py",
            "aura_patch_repair.py",
            "aura_live_architect.py",
            "aura_harness_evolver.py",
        ],
        "proposal": "Tune patch preflight, one-shot repair, or early diagnostic policy without touching production code.",
    },
    "repo_localization": {
        "metric_name": "localizer_score",
        "target_modules": [
            "aura_repo_localizer.py",
            "aura_repair_kg.py",
            ".aura/CODEMAP.json",
            ".aura/CODEMAP.md",
        ],
        "proposal": "Improve CODEMAP/AST/test evidence ranking while avoiding monolith overread.",
    },
    "context_compression": {
        "metric_name": "context_score",
        "target_modules": [
            "aura_builder_context.py",
            "aura_context_crusher.py",
            "aura_st3gg_recall.py",
        ],
        "proposal": "Improve surgical context packets by preserving required symbols, tests, and neighbor evidence per token.",
    },
    "hotswap_safety": {
        "metric_name": "hotswap_score",
        "target_modules": [
            "aura_hotswap_refactor.py",
            "aura_live_architect.py",
            "aura_architect_loop.py",
        ],
        "proposal": "Refine reload safety classification and sandbox reload evidence without bypassing verifier gates.",
    },
    "research_retrieval_utility": {
        "metric_name": "research_utility_score",
        "target_modules": [
            "arxiv_forager.py",
            "aura_research_manifest.py",
            "aura_research_ingest_bridge.py",
            "aura_paper_memory.py",
            "aura_repair_kg.py",
        ],
        "proposal": "Score whether research entries produce target-module lessons, acceptance tests, and later repair lift.",
    },
}


@dataclass
class EmpiricalTask:
    task_type: str
    metric_name: str
    target_modules: list[str]
    scoring_directives: list[str]
    evidence: dict[str, Any]
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmpiricalCandidate:
    candidate_id: str
    parent_id: str | None
    task_type: str
    target_module: str
    proposal: str
    expected_metric: str
    evidence: dict[str, Any]
    status: str = "proposed"
    score: float = 0.0
    visits: int = 0
    fitness_history: list[float] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    promoted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmpiricalScoreCard:
    candidate_id: str
    task_type: str
    metric_name: str
    score: float
    metrics: dict[str, Any]
    passed: bool
    reasons: list[str]
    penalties: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmpiricalRunResult:
    ok: bool
    candidate_id: str
    task_type: str
    score_card: EmpiricalScoreCard
    recommended_promotion: bool
    analyst_summary: str
    failures: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score_card"] = self.score_card.to_dict()
        return data


def _load_codemap(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root / ".aura" / "CODEMAP.json"
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aura" / "MODULE_MANIFEST.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return generate_module_manifest(repo_root)


def _codemap_file_evidence(codemap: dict[str, Any] | None, modules: list[str]) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "codemap_available": bool(codemap),
        "file_hits": [],
        "symbol_hits": [],
        "repo_scale": {},
    }
    if not codemap:
        return evidence

    coverage = codemap.get("coverage", {}) if isinstance(codemap.get("coverage"), dict) else {}
    summary = codemap.get("summary", {}) if isinstance(codemap.get("summary"), dict) else {}
    evidence["repo_scale"] = {
        "included_file_count": coverage.get("included_file_count") or summary.get("file_count"),
        "tokens_est": summary.get("tokens_est"),
        "bytes": summary.get("bytes"),
    }

    entries: list[dict[str, Any]] = []
    for key in ("files", "file_cards"):
        raw = codemap.get(key)
        if isinstance(raw, list):
            entries.extend(item for item in raw if isinstance(item, dict))
    by_path = {str(entry.get("path", "")).replace("\\", "/"): entry for entry in entries}
    module_set = {module.replace("\\", "/") for module in modules}
    for module in sorted(module_set):
        hit = by_path.get(module)
        if hit:
            evidence["file_hits"].append(
                {
                    "path": module,
                    "role": hit.get("role"),
                    "lines": hit.get("lines"),
                    "tokens_est": hit.get("tokens_est"),
                    "topology": hit.get("topology", {}),
                }
            )

    symbol_index = codemap.get("symbol_index", {})
    if isinstance(symbol_index, dict):
        for symbol, occurrences in symbol_index.items():
            if not isinstance(occurrences, list):
                continue
            for occurrence in occurrences:
                file_path = str(occurrence.get("file") or occurrence.get("path") or "").replace("\\", "/")
                if file_path in module_set:
                    evidence["symbol_hits"].append(
                        {
                            "symbol": symbol,
                            "file": file_path,
                            "kind": occurrence.get("kind"),
                            "line": occurrence.get("line"),
                        }
                    )
    evidence["symbol_hits"] = evidence["symbol_hits"][:30]
    return evidence


def _task_constraints() -> list[str]:
    return [
        "No production writes.",
        "No autonomous promotion.",
        "No model call unless MODULE_MANIFEST, CODEMAP evidence, and declared scope are present.",
        "Every candidate must have a measurable local score.",
        "Every score must be reproducible from local verifier artifacts.",
    ]


def define_empirical_task(task_type: str, repo_root: str | Path) -> EmpiricalTask:
    """Define a CODEMAP-grounded scorable Aura subsystem task."""
    normalized = task_type.strip().lower()
    if normalized not in TASK_DEFINITIONS:
        raise ValueError(f"Unknown empirical task type: {task_type}")

    root = Path(repo_root).resolve()
    definition = TASK_DEFINITIONS[normalized]
    codemap = _load_codemap(root)
    manifest = _load_manifest(root)
    target_modules = list(definition["target_modules"])
    manifest_summary = summarize_module_manifest(manifest)
    present_modules = [
        module for module in target_modules if module.startswith(".aura/") or module_exists(manifest, module) or (root / module).exists()
    ]

    kg_packet: dict[str, Any] = {}
    if build_repair_kg is not None and present_modules:
        try:
            kg = build_repair_kg(root)
            kg_packet = kg.evidence_packet_for_file(present_modules[0], depth=1)
        except Exception:
            kg_packet = {}

    evidence = {
        "manifest": manifest_summary,
        "target_modules_present": present_modules,
        "target_modules_missing": [module for module in target_modules if module not in present_modules],
        "codemap": _codemap_file_evidence(codemap, target_modules),
        "repair_kg": kg_packet,
    }
    directives = [
        f"Optimize {definition['metric_name']} from local verifier artifacts.",
        str(definition["proposal"]),
        "Sandbox first; recommend only after score improves and verifier evidence is green.",
    ]
    return EmpiricalTask(
        task_type=normalized,
        metric_name=str(definition["metric_name"]),
        target_modules=target_modules,
        scoring_directives=directives,
        evidence=evidence,
        constraints=_task_constraints(),
    )


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = blake2b(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"), digest_size=6).hexdigest()
    return f"{prefix}-{digest}"


def generate_candidate(task: EmpiricalTask, parent_candidate: EmpiricalCandidate | None = None) -> EmpiricalCandidate:
    """Generate one deterministic bounded candidate description. No model call is required."""
    present = task.evidence.get("target_modules_present", []) or task.target_modules
    target_module = str(present[0])
    parent_id = parent_candidate.candidate_id if parent_candidate else None
    payload = {
        "task_type": task.task_type,
        "metric_name": task.metric_name,
        "target_module": target_module,
        "parent_id": parent_id,
        "directives": task.scoring_directives,
    }
    return EmpiricalCandidate(
        candidate_id=_stable_id(task.task_type.upper(), payload),
        parent_id=parent_id,
        task_type=task.task_type,
        target_module=target_module,
        proposal=task.scoring_directives[1],
        expected_metric=task.metric_name,
        evidence={
            "manifest_hash": task.evidence.get("manifest", {}).get("manifest_hash"),
            "codemap_available": task.evidence.get("codemap", {}).get("codemap_available", False),
            "kg_root": task.evidence.get("repair_kg", {}).get("root"),
        },
    )


def _as_metrics(transaction_or_metrics: dict[str, Any]) -> dict[str, Any]:
    if {"workspace", "verification", "stage_results"} & set(transaction_or_metrics):
        return analyze_transaction_outcome(transaction_or_metrics)
    return dict(transaction_or_metrics)


def _bool_metric(metrics: dict[str, Any], key: str) -> bool | None:
    """Return True if metric is present and truthy, False if present and falsy, None if absent."""
    if key not in metrics:
        return None
    return bool(metrics.get(key))


def _score_from_terms(positive: list[tuple[bool, str]], negative: list[tuple[bool, str]], metrics: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    reasons = [reason for ok, reason in positive if ok]
    penalties = [reason for active, reason in negative if active]
    raw = sum(1.0 for ok, _ in positive if ok) - sum(1.0 for active, _ in negative if active)
    possible = max(1, len(positive))
    score = max(0.0, min(1.0, raw / possible))
    if metrics.get("cost") is not None:
        try:
            score = max(0.0, score - min(float(metrics["cost"]) / 100.0, 0.2))
        except Exception:
            pass
    if metrics.get("tokens") is not None:
        try:
            score = max(0.0, score - min(float(metrics["tokens"]) / 100000.0, 0.2))
        except Exception:
            pass
    return round(score, 4), reasons, penalties


def score_candidate(
    task: EmpiricalTask,
    transaction_or_metrics: dict[str, Any],
    *,
    candidate_id: str = "manual",
) -> EmpiricalScoreCard:
    """Compute a deterministic score card for a task from local transaction metrics."""
    metrics = _as_metrics(transaction_or_metrics)
    task_type = task.task_type

    if task_type == "patch_repair":
        positive = [
            (int(metrics.get("patch_staged_count", 0) or 0) > 0, "patch_staged"),
            (_bool_metric(metrics, "workspace_ok"), "workspace_ok"),
            (int(metrics.get("repair_success_count", 0) or 0) >= 0, "repair_path_measured"),
            (int(metrics.get("test_pass_count", 0) or 0) > 0, "selected_tests_pass"),
            (int(metrics.get("verifier_failure_count", 0) or 0) == 0, "no_verifier_failures"),
        ]
        negative = [
            (int(metrics.get("preflight_rejection_count", 0) or 0) > 0, "preflight_rejections"),
            (int(metrics.get("test_fail_count", 0) or 0) > 0, "test_failures"),
            (bool(metrics.get("hallucinated_file_reference")), "hallucinated_file_reference"),
            (bool(metrics.get("scope_violation")), "scope_violation"),
        ]
    elif task_type == "repo_localization":
        positive = [
            (_bool_metric(metrics, "target_file_in_top_5"), "target_file_in_top_5"),
            (_bool_metric(metrics, "symbol_found"), "symbol_found"),
            (_bool_metric(metrics, "test_file_found"), "test_file_found"),
            (_bool_metric(metrics, "neighbor_graph_relevance"), "neighbor_graph_relevance"),
        ]
        negative = [
            (_bool_metric(metrics, "irrelevant_hub_bias"), "irrelevant_hub_bias"),
            (_bool_metric(metrics, "monolith_overread_penalty"), "monolith_overread_penalty"),
        ]
    elif task_type == "context_compression":
        positive = [
            (_bool_metric(metrics, "required_symbol_present"), "required_symbol_present"),
            (_bool_metric(metrics, "required_neighbor_present"), "required_neighbor_present"),
            (_bool_metric(metrics, "test_context_present"), "test_context_present"),
            (_bool_metric(metrics, "source_excerpt_exact"), "source_excerpt_exact"),
        ]
        negative = [
            (float(metrics.get("token_count", 0) or 0) > float(metrics.get("token_budget", 8000) or 8000), "token_count_over_budget"),
            (_bool_metric(metrics, "missing_dependency"), "missing_dependency"),
            (_bool_metric(metrics, "stale_line_range"), "stale_line_range"),
        ]
    elif task_type == "hotswap_safety":
        importlib_reload = _bool_metric(metrics, "importlib_reload_pass")
        global_state = _bool_metric(metrics, "global_state_delta")
        thread_side_effect = _bool_metric(metrics, "running_thread_side_effect")
        sig_stable = _bool_metric(metrics, "public_signature_stable")
        hotswap_ready_val = _bool_metric(metrics, "hotswap_ready")
        restart_req = _bool_metric(metrics, "restart_required")
        hierarchy_change = _bool_metric(metrics, "class_hierarchy_change")

        positive = [
            (importlib_reload is True, "importlib_reload_pass"),
            (global_state is False, "no_global_state_delta"),
            (thread_side_effect is False, "no_running_thread_side_effect"),
            (sig_stable is True, "public_signature_stable"),
            (hotswap_ready_val is True, "hotswap_ready"),
        ]
        negative = [
            (restart_req is True, "restart_required"),
            (hierarchy_change is True, "class_hierarchy_change"),
            (int(metrics.get("test_fail_count", 0) or 0) > 0, "test_failures"),
        ]
    elif task_type == "research_retrieval_utility":
        positive = [
            (_bool_metric(metrics, "paper_supports_target_module"), "paper_supports_target_module"),
            (_bool_metric(metrics, "implementation_lesson_extracted"), "implementation_lesson_extracted"),
            (_bool_metric(metrics, "acceptance_test_created"), "acceptance_test_created"),
            (_bool_metric(metrics, "later_patch_success_linked"), "later_patch_success_linked"),
        ]
        negative = [
            (_bool_metric(metrics, "irrelevant_ingest"), "irrelevant_ingest"),
            (_bool_metric(metrics, "no_target_module"), "no_target_module"),
            (_bool_metric(metrics, "no_measurable_acceptance_test"), "no_measurable_acceptance_test"),
        ]
    else:
        raise ValueError(f"Unknown empirical task type: {task_type}")

    score, reasons, penalties = _score_from_terms(positive, negative, metrics)
    return EmpiricalScoreCard(
        candidate_id=candidate_id,
        task_type=task_type,
        metric_name=task.metric_name,
        score=score,
        metrics=metrics,
        passed=score >= 0.7 and not penalties,
        reasons=reasons,
        penalties=penalties,
    )


def select_next_candidate_ucb(
    candidate_tree: list[EmpiricalCandidate] | list[dict[str, Any]],
    *,
    exploration_c: float = 1.2,
) -> EmpiricalCandidate | dict[str, Any] | None:
    """Select the next candidate using a small upper-confidence-bound score."""
    if not candidate_tree:
        return None

    def visits(item: EmpiricalCandidate | dict[str, Any]) -> int:
        return int(item.visits if isinstance(item, EmpiricalCandidate) else item.get("visits", 0) or 0)

    parent_visits = max(1, sum(visits(item) for item in candidate_tree))

    def value(item: EmpiricalCandidate | dict[str, Any]) -> float:
        if isinstance(item, EmpiricalCandidate):
            history = item.fitness_history
            base_score = item.score
            safety_penalty = 0.3 if item.failure_modes else 0.0
            cost_penalty = float(item.evidence.get("cost_penalty", 0.0) or 0.0)
            item_visits = item.visits
        else:
            history = list(item.get("fitness_history", []) or [])
            base_score = float(item.get("score", 0.0) or 0.0)
            safety_penalty = float(item.get("safety_penalty", 0.0) or (0.3 if item.get("failure_modes") else 0.0))
            cost_penalty = float(item.get("cost_penalty", 0.0) or 0.0)
            item_visits = int(item.get("visits", 0) or 0)
        mean_score = sum(history) / len(history) if history else base_score
        exploration = exploration_c * math.sqrt(math.log(parent_visits + 1) / (item_visits + 1))
        return mean_score + exploration - safety_penalty - cost_penalty

    return max(candidate_tree, key=value)


def _ledger_path(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve() / EMPIRICAL_LEDGER


def _append_ledger(repo_root: str | Path, payload: dict[str, Any]) -> None:
    path = _ledger_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def record_empirical_result(result: EmpiricalRunResult, repo_root: str | Path) -> None:
    """Persist a candidate-tree row and a harness prediction fallback row."""
    payload = {
        "event_class": "empirical_run_result",
        "recorded_at": time.time(),
        **result.to_dict(),
    }
    _append_ledger(repo_root, payload)
    try:
        record_harness_prediction(
            result.candidate_id,
            result.task_type,
            result.analyst_summary,
            result.score_card.metric_name,
            result.score_card.score,
            repo_root=repo_root,
            observed_value=result.score_card.score,
            status="verified" if result.ok else "failed",
        )
    except Exception:
        pass


def _read_empirical_rows(repo_root: str | Path) -> list[dict[str, Any]]:
    path = _ledger_path(repo_root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("event_class") == "empirical_run_result":
            rows.append(row)
    return rows


def recommend_promotion(candidate_id: str, repo_root: str | Path) -> dict[str, Any]:
    """
    Return a human-visible promotion recommendation only.

    This never mutates production and never bypasses Refactor Arena or hotswap review.
    """
    rows = [row for row in _read_empirical_rows(repo_root) if row.get("candidate_id") == candidate_id]
    if not rows:
        return {
            "candidate_id": candidate_id,
            "recommended": False,
            "reason": "No empirical result recorded for candidate.",
            "required_gate": "Refactor Arena verifier + human approval",
        }
    row = rows[-1]
    score_card = row.get("score_card", {}) or {}
    metrics = score_card.get("metrics", {}) or {}
    failures = row.get("failures", []) or []
    verifier_green = metrics.get("workspace_ok") is True and not failures
    has_hotswap_metrics = "hotswap_ready" in metrics or "public_signature_stable" in metrics
    hotswap_green = (
        (metrics.get("hotswap_ready") is True or metrics.get("public_signature_stable") is True)
        if has_hotswap_metrics
        else True
    )
    recommended = bool(row.get("ok")) and bool(score_card.get("passed")) and verifier_green and hotswap_green
    return {
        "candidate_id": candidate_id,
        "recommended": recommended,
        "score": score_card.get("score", 0.0),
        "reason": "Score improved and verifier evidence is green." if recommended else "Verifier, hotswap, score, or failure evidence is insufficient.",
        "required_gate": "Refactor Arena verifier + human approval",
        "no_autopromote": True,
    }


def analyze_empirical_candidate(
    *,
    task: EmpiricalTask,
    candidate: EmpiricalCandidate,
    transaction_or_metrics: dict[str, Any],
) -> EmpiricalRunResult:
    """Score a candidate and build a compact analyst result."""
    score_card = score_candidate(task, transaction_or_metrics, candidate_id=candidate.candidate_id)
    failures = list(score_card.penalties)
    ok = score_card.passed
    summary = (
        f"{task.task_type} candidate {candidate.candidate_id} scored {score_card.score:.2f} "
        f"on {task.metric_name}; reasons={len(score_card.reasons)} penalties={len(score_card.penalties)}."
    )
    return EmpiricalRunResult(
        ok=ok,
        candidate_id=candidate.candidate_id,
        task_type=task.task_type,
        score_card=score_card,
        recommended_promotion=ok,
        analyst_summary=summary,
        failures=failures,
    )
