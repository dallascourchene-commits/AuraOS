"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa90d-[Q-SYS:DREAM_RETRIEVAL]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Usefulness-Grounded Retrieval)
DEPENDENCIES: dataclasses, hashlib, json, pathlib, time, typing
FUNCTIONS: DreamRetrievalExample, DreamCandidate, DreamUsefulnessScore, DreamRetrievalLedger, DreamReranker, rerank_for_arena, record_arena_retrieval_feedback
SYNOPSIS: DREAM-lite retrieval substrate. Scores ST3GG, CODEMAP, paper-memory, travel VSA pointer, and Arena candidates by downstream usefulness while preserving sidecar/file/provenance truth boundaries.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

DREAM_RETRIEVAL_VERSION = "AURA_DREAM_RETRIEVAL_V1"
DREAM_LEDGER_PATH = Path("Aura_Memory") / "dream_retrieval_ledger.jsonl"
LocalLossFn = Callable[["DreamRetrievalExample", "DreamCandidate"], float | dict[str, Any]]
JudgeFn = Callable[["DreamRetrievalExample", "DreamCandidate"], float | dict[str, Any]]


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_json_dumps(payload).encode("utf-8"), digest_size=size).hexdigest()


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _tokens(text: str) -> set[str]:
    return {item for item in re.findall(r"[a-zA-Z0-9_./:-]+", str(text).lower()) if len(item) > 2}


def _verifier_approved(verifier_result: Any) -> bool | None:
    if verifier_result is None:
        return None
    if isinstance(verifier_result, bool):
        return verifier_result
    if isinstance(verifier_result, dict):
        for key in ("approved", "ok", "hotswap_ready", "success"):
            if key in verifier_result:
                return bool(verifier_result.get(key))
        status = str(verifier_result.get("status", "")).lower()
        if status:
            return status in {"approved", "passed", "verified", "ready", "ok"}
    return None


def _failure_reason(verifier_result: Any) -> str:
    if isinstance(verifier_result, dict):
        blockers = verifier_result.get("blockers") or verifier_result.get("failures") or []
        if isinstance(blockers, list) and blockers:
            return ",".join(str(item) for item in blockers[:3])
        for key in ("failure_reason", "reason", "message", "status"):
            value = verifier_result.get(key)
            if value:
                return str(value)
    return ""


@dataclass(frozen=True)
class DreamCandidate:
    candidate_id: str
    candidate_type: str
    source: str
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    semantic_score: float = 0.0
    truth_boundary: str = ""
    exact_lookup_required: bool = False
    verifier_result: dict[str, Any] | None = None
    failure_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_any(cls, value: DreamCandidate | dict[str, Any] | str, *, default_type: str = "context") -> DreamCandidate:
        if isinstance(value, DreamCandidate):
            return value
        if isinstance(value, str):
            return cls(candidate_id=value, candidate_type=default_type, source="literal", content=value)
        data = dict(value)
        candidate_id = str(data.get("candidate_id") or data.get("id") or data.get("vsa_id") or _hash_payload(data, size=8))
        candidate_type = str(data.get("candidate_type") or data.get("type") or default_type)
        source = str(data.get("source") or data.get("sidecar_table") or data.get("origin") or "unknown")
        content = str(data.get("content") or data.get("text") or data.get("path") or data.get("name") or "")
        metadata = dict(data.get("metadata") or {})
        for key in ("path", "file", "symbol", "semantic_tags", "sidecar_table", "sidecar_key", "domain"):
            if key in data and key not in metadata:
                metadata[key] = data[key]
        semantic_score_value = data.get("semantic_score")
        final_semantic_score = semantic_score_value if semantic_score_value is not None else data.get("score")
        return cls(
            candidate_id=candidate_id,
            candidate_type=candidate_type,
            source=source,
            content=content,
            metadata=metadata,
            semantic_score=_clamp01(final_semantic_score, 0.0),
            truth_boundary=str(data.get("truth_boundary") or ""),
            exact_lookup_required=bool(data.get("exact_lookup_required", False)),
            verifier_result=data.get("verifier_result"),
            failure_reason=str(data.get("failure_reason") or ""),
        )


@dataclass(frozen=True)
class DreamRetrievalExample:
    query: str
    target_type: str
    candidates: list[DreamCandidate]
    arena_domain: str = ""
    expected_output: str = ""
    mode: str = "judge_heuristic"
    verifier_result: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    phase_hash: str = ""

    def __post_init__(self) -> None:
        if not self.phase_hash:
            object.__setattr__(
                self,
                "phase_hash",
                _hash_payload(
                    {
                        "query": self.query,
                        "target_type": self.target_type,
                        "arena_domain": self.arena_domain,
                        "candidate_ids": [item.candidate_id for item in self.candidates],
                    }
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["candidates"] = [item.to_dict() for item in self.candidates]
        return payload


@dataclass(frozen=True)
class DreamUsefulnessScore:
    candidate_id: str
    candidate_type: str
    source: str
    usefulness_score: float
    semantic_score: float
    target_type: str
    mode: str
    query: str
    verifier_result: dict[str, Any] | None = None
    failure_reason: str = ""
    rationale: str = ""
    features: dict[str, Any] = field(default_factory=dict)
    phase_hash: str = ""
    ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.phase_hash:
            object.__setattr__(
                self,
                "phase_hash",
                _hash_payload(
                    {
                        "candidate_id": self.candidate_id,
                        "target_type": self.target_type,
                        "usefulness_score": round(self.usefulness_score, 6),
                        "mode": self.mode,
                        "query": self.query,
                    }
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_ledger_row(self) -> dict[str, Any]:
        return {
            "version": DREAM_RETRIEVAL_VERSION,
            "query": self.query,
            "candidate_id": self.candidate_id,
            "candidate_type": self.candidate_type,
            "source": self.source,
            "usefulness_score": self.usefulness_score,
            "semantic_score": self.semantic_score,
            "target_type": self.target_type,
            "mode": self.mode,
            "verifier_result": self.verifier_result,
            "phase_hash": self.phase_hash,
            "failure_reason": self.failure_reason,
            "rationale": self.rationale,
            "features": self.features,
            "ts": self.ts,
        }


class DreamRetrievalLedger:
    def __init__(self, path: str | Path = DREAM_LEDGER_PATH, *, qdkt: Any = None):
        self.path = Path(path)
        self.qdkt = qdkt

    def append_score(self, score: DreamUsefulnessScore) -> dict[str, Any]:
        row = score.to_ledger_row()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(_json_dumps(row) + "\n")
        if self.qdkt is not None and hasattr(self.qdkt, "observe_retrieval_usefulness"):
            self.qdkt.observe_retrieval_usefulness(row)
        return row

    def recent(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows[-limit:]


class DreamReranker:
    def __init__(
        self,
        *,
        ledger: DreamRetrievalLedger | None = None,
        local_loss_fn: LocalLossFn | None = None,
        judge_fn: JudgeFn | None = None,
    ):
        self.ledger = ledger
        self.local_loss_fn = local_loss_fn
        self.judge_fn = judge_fn

    def _heuristic_score(self, example: DreamRetrievalExample, candidate: DreamCandidate) -> tuple[float, dict[str, Any], str]:
        query_tokens = _tokens(example.query)
        candidate_material = " ".join(
            [
                candidate.content,
                candidate.candidate_id,
                candidate.candidate_type,
                candidate.source,
                _json_dumps(candidate.metadata),
            ]
        )
        candidate_tokens = _tokens(candidate_material)
        overlap = len(query_tokens & candidate_tokens) / max(1, len(query_tokens))
        semantic = _clamp01(candidate.semantic_score)
        source_bonus = 0.0
        source_text = f"{candidate.source} {candidate.candidate_type}".lower()
        target = example.target_type.lower()
        if "code" in target and any(word in source_text for word in ("codemap", "file", "test", "symbol")):
            source_bonus += 0.14
        if "travel" in target and any(word in source_text for word in ("vsa", "sidecar", "travel")):
            source_bonus += 0.14
        if "shadow" in target and any(word in source_text for word in ("failure", "test", "verifier")):
            source_bonus += 0.12
        if "st3gg" in source_text or "memory" in source_text:
            source_bonus += 0.08
        approved = _verifier_approved(candidate.verifier_result or example.verifier_result)
        verifier_bonus = 0.0
        if approved is True:
            verifier_bonus = 0.16
        elif approved is False:
            verifier_bonus = -0.28
        boundary_penalty = 0.0
        if candidate.exact_lookup_required and approved is not True:
            boundary_penalty -= 0.18
        if candidate.failure_reason or _failure_reason(candidate.verifier_result):
            boundary_penalty -= 0.16
        score = _clamp01(0.20 + semantic * 0.18 + overlap * 0.48 + source_bonus + verifier_bonus + boundary_penalty)
        features = {
            "lexical_overlap": round(overlap, 6),
            "semantic_component": semantic,
            "source_bonus": round(source_bonus, 6),
            "verifier_bonus": verifier_bonus,
            "boundary_penalty": round(boundary_penalty, 6),
            "exact_lookup_required": candidate.exact_lookup_required,
        }
        rationale = "heuristic downstream-usefulness score from overlap, source fit, verifier signal, and truth boundary"
        return score, features, rationale

    def _loss_score(self, example: DreamRetrievalExample, candidate: DreamCandidate) -> tuple[float, dict[str, Any], str] | None:
        if self.local_loss_fn is None:
            return None
        result = self.local_loss_fn(example, candidate)
        if isinstance(result, dict):
            candidate_loss = float(result.get("candidate_loss", result.get("loss", 0.0)))
            baseline_loss = result.get("baseline_loss")
            if baseline_loss is not None:
                delta = max(0.0, float(baseline_loss) - candidate_loss)
                score = _clamp01(delta / max(abs(float(baseline_loss)), 1.0))
            else:
                score = _clamp01(1.0 / (1.0 + max(0.0, candidate_loss)))
            features = dict(result)
        else:
            candidate_loss = float(result)
            score = _clamp01(1.0 / (1.0 + max(0.0, candidate_loss)))
            features = {"candidate_loss": candidate_loss}
        return score, features, "local next-token loss proxy"

    def _judge_score(self, example: DreamRetrievalExample, candidate: DreamCandidate) -> tuple[float, dict[str, Any], str] | None:
        if self.judge_fn is None:
            return None
        result = self.judge_fn(example, candidate)
        if isinstance(result, dict):
            return (
                _clamp01(result.get("usefulness_score", result.get("score", 0.0))),
                dict(result.get("features") or {}),
                str(result.get("rationale") or "judge usefulness score"),
            )
        return _clamp01(result), {}, "judge usefulness score"

    def score_candidate(self, example: DreamRetrievalExample, candidate: DreamCandidate) -> DreamUsefulnessScore:
        mode = example.mode
        scored = None
        if mode == "local_loss":
            scored = self._loss_score(example, candidate)
        if scored is None and mode in {"judge", "judge_heuristic"}:
            scored = self._judge_score(example, candidate)
        if scored is None:
            scored = self._heuristic_score(example, candidate)
            mode = "judge_heuristic"
        usefulness, features, rationale = scored
        return DreamUsefulnessScore(
            candidate_id=candidate.candidate_id,
            candidate_type=candidate.candidate_type,
            source=candidate.source,
            usefulness_score=round(_clamp01(usefulness), 6),
            semantic_score=_clamp01(candidate.semantic_score),
            target_type=example.target_type,
            mode=mode,
            query=example.query,
            verifier_result=candidate.verifier_result or example.verifier_result,
            failure_reason=candidate.failure_reason or _failure_reason(candidate.verifier_result or example.verifier_result),
            rationale=rationale,
            features=features,
        )

    def rerank(
        self,
        example: DreamRetrievalExample,
        *,
        top_k: int | None = None,
        record: bool = True,
    ) -> dict[str, Any]:
        scores = [self.score_candidate(example, candidate) for candidate in example.candidates]
        by_id = {candidate.candidate_id: candidate for candidate in example.candidates}
        ranked_scores = sorted(scores, key=lambda item: (item.usefulness_score, item.semantic_score), reverse=True)
        if top_k is not None:
            ranked_scores = ranked_scores[: max(0, top_k)]
        if record and self.ledger is not None:
            for score in ranked_scores:
                self.ledger.append_score(score)
        ranked_candidates = [by_id[score.candidate_id].to_dict() | {"dream_usefulness": score.to_ledger_row()} for score in ranked_scores]
        payload = {
            "version": DREAM_RETRIEVAL_VERSION,
            "query": example.query,
            "target_type": example.target_type,
            "arena_domain": example.arena_domain,
            "ranked_candidates": ranked_candidates,
            "scores": [score.to_ledger_row() for score in ranked_scores],
        }
        return {**payload, "phase_hash": _hash_payload(payload)}


def rerank_for_arena(
    intent: str,
    candidates: list[DreamCandidate | dict[str, Any] | str],
    target_type: str,
    *,
    arena_domain: str = "",
    expected_output: str = "",
    mode: str = "judge_heuristic",
    verifier_result: dict[str, Any] | None = None,
    ledger_path: str | Path = DREAM_LEDGER_PATH,
    qdkt: Any = None,
    top_k: int | None = None,
    record: bool = True,
    local_loss_fn: LocalLossFn | None = None,
    judge_fn: JudgeFn | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = [DreamCandidate.from_any(item) for item in candidates]
    example = DreamRetrievalExample(
        query=intent,
        target_type=target_type,
        candidates=normalized,
        arena_domain=arena_domain,
        expected_output=expected_output,
        mode=mode,
        verifier_result=verifier_result,
        metadata=dict(metadata or {}),
    )
    ledger = DreamRetrievalLedger(ledger_path, qdkt=qdkt) if record else None
    return DreamReranker(ledger=ledger, local_loss_fn=local_loss_fn, judge_fn=judge_fn).rerank(
        example,
        top_k=top_k,
        record=record,
    )


def record_arena_retrieval_feedback(
    intent: str,
    candidates: list[DreamCandidate | dict[str, Any] | str],
    *,
    target_type: str,
    verifier_result: dict[str, Any] | None = None,
    arena_domain: str = "",
    ledger_path: str | Path = DREAM_LEDGER_PATH,
    qdkt: Any = None,
) -> dict[str, Any]:
    prepared = []
    for item in candidates:
        candidate = DreamCandidate.from_any(item)
        prepared.append(
            DreamCandidate(
                **{
                    **candidate.to_dict(),
                    "verifier_result": verifier_result or candidate.verifier_result,
                    "failure_reason": candidate.failure_reason or _failure_reason(verifier_result),
                }
            )
        )
    return rerank_for_arena(
        intent,
        prepared,
        target_type,
        arena_domain=arena_domain,
        verifier_result=verifier_result,
        ledger_path=ledger_path,
        qdkt=qdkt,
    )
