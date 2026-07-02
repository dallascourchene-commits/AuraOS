"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c9-[Q-SYS:MUSIC_CODING_ARENA]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Research-Grounded Arena Resonance)
DEPENDENCIES: dataclasses, hashlib, json, pathlib, re, typing, numpy, aura_music_inversion
FUNCTIONS: ArenaResearchIdea, load_arena_research_ideas, score_music_arena_synthesis,
fuse_music_council_plan, music_builder_objective, augment_act_tasks_with_music
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
        copied["allowed_scope"] = copied.get("allowed_scope") or "single music-mitosis fused Act Capsule"
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
        combined = min(1.0, normalized_music * 0.72 + candidate_score * 0.16 + overlap * 0.09 + priority * 0.03)
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
                "selected_research": idea.to_dict(),
                "synthesis": _synthesis_line(candidate, idea),
            }
        )
    ranked.sort(key=lambda item: (item["combined_score"], item["module_overlap"], item["priority_score"]), reverse=True)

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
    fused_score = min(0.97, max(candidate_scores or [0.5]) + 0.08)
    return {
        **synthesis,
        "fusion_candidate_id": "music_mitosis_fusion",
        "supporting_candidate_ids": ranked_ids[:3],
        "fused_score": round(fused_score, 6),
        "fused_plan": fused_plan,
    }


def music_builder_objective(objective: str, synthesis: Mapping[str, Any] | None) -> str:
    if not synthesis or synthesis.get("status") != "ready":
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
    if not synthesis or synthesis.get("status") != "ready":
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
