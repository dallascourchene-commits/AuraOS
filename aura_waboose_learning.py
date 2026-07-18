"""Grounded CodeRabbit-to-Coding-Waboose learning loop.

A successful external review is a teacher signal, never patch authority.  Each
finding must bind to the exact reviewed repository head and source span before it
is stored.  Aura's Capability Connectome records the affected capability path,
DREAM-lite ranks the episode against prior lessons, and QDKT records repeated
confirmation.  Only deterministic rule packs or separately corroborated agent
findings can authorize a Forge repair request.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import time
import tokenize
from typing import Any

from aura_capability_connectome import build_capability_connectome
from aura_capability_connectome_v2 import enrich_connectome
from aura_capability_resolver_v2 import resolve_capabilities
from aura_dream_retrieval import DreamCandidate, rerank_for_arena
from aura_qdkt import UnifiedQDKT

WABOOSE_LEARNING_VERSION = "AURA_WABOOSE_CODERABBIT_LEARNING_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
DEFAULT_LEARNING_ROOT = Path.home() / ".aura" / "coding_waboose_learning"
_CRYSTAL_CONFIRMATIONS = 3
_CRYSTAL_CONFIDENCE = 0.75
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")

_KNOWN_RULE_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "strict_input_types",
        ("bool(\"false\")", "truthy", "boolean option", "strict boolean"),
    ),
    (
        "symbol_identity",
        ("qualified symbol", "same-named method", "bare symbol", "worker.run"),
    ),
    (
        "source_integrity",
        ("tokenize.open", "encoding cookie", "errors=\"replace\"", "partial source", "unreadable file"),
    ),
    (
        "bounded_graph_integrity",
        ("edge endpoint", "bounded closure", "outside the selected closure", "queued ids"),
    ),
    (
        "test_evidence_preservation",
        ("test callable", "test edge", "drops test", "test evidence"),
    ),
)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_json(value).encode("utf-8"), digest_size=size).hexdigest()


def _tokens(value: Any) -> set[str]:
    return {item.lower() for item in _TOKEN_RE.findall(str(value or ""))}


def _safe_repo_path(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts:
        raise ValueError("finding file must be a repository-relative path")
    return path.as_posix()


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return "UNAVAILABLE"
    return result.stdout.strip() or "UNAVAILABLE"


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{_digest(time.time(), size=6)}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _smallest_covering_node(tree: ast.AST, line_start: int, line_end: int) -> ast.AST:
    candidates = [
        node
        for node in ast.walk(tree)
        if hasattr(node, "lineno")
        and int(getattr(node, "lineno", 0) or 0) <= line_start
        and int(getattr(node, "end_lineno", getattr(node, "lineno", 0)) or 0) >= line_end
    ]
    if not candidates:
        return tree
    return min(
        candidates,
        key=lambda node: (
            int(getattr(node, "end_lineno", line_end) or line_end)
            - int(getattr(node, "lineno", line_start) or line_start),
            len(list(ast.walk(node))),
        ),
    )


def _ast_signature(node: ast.AST) -> dict[str, Any]:
    node_types: set[str] = set()
    calls: set[str] = set()
    strings: set[str] = set()
    operators: set[str] = set()
    names: set[str] = set()
    for item in ast.walk(node):
        node_types.add(type(item).__name__)
        if isinstance(item, ast.Call):
            name = _call_name(item.func)
            if name:
                calls.add(name)
        elif isinstance(item, ast.Constant) and isinstance(item.value, str):
            strings.update(_tokens(item.value))
        elif isinstance(item, ast.Name):
            names.add(item.id)
        elif isinstance(item, (ast.operator, ast.unaryop, ast.boolop, ast.cmpop)):
            operators.add(type(item).__name__)
    return {
        "node_types": sorted(node_types),
        "calls": sorted(calls),
        "strings": sorted(strings)[:80],
        "operators": sorted(operators),
        "names": sorted(names)[:120],
    }


def _known_rule_pack(text: str) -> str:
    lowered = text.lower()
    for pack, terms in _KNOWN_RULE_TERMS:
        if any(term in lowered for term in terms):
            return pack
    return ""


def _clean_markdown(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<details>.*?</details>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"!\[[^]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_>#]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_from_comment(body: str) -> str:
    cleaned = _clean_markdown(body)
    if not cleaned:
        return "CodeRabbit review finding"
    match = re.search(r"(?:Minor|Major|Critical|Quick win)\s+(.{12,180}?)(?:\.|$)", cleaned)
    if match:
        return match.group(1).strip()
    return cleaned[:180]


@dataclass(frozen=True)
class CodeRabbitLesson:
    lesson_id: str
    run_id: str
    repository_head: str
    pr_number: int
    file: str
    line_start: int
    line_end: int
    title: str
    message: str
    severity: str
    category: str
    suggested_fix: str
    source_digest: str
    source_excerpt_digest: str
    source_excerpt: str
    source_grounded: bool
    semantic_rule_pack: str
    ast_signature: dict[str, Any]
    capability_path: dict[str, Any]
    dream_match: dict[str, Any]
    learned_at: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CodeRabbitLearningStore:
    """Append-only CodeRabbit episodes plus compact learned pattern registry."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        learning_root: str | Path = DEFAULT_LEARNING_ROOT,
        qdkt: UnifiedQDKT | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.learning_root = Path(learning_root).expanduser().resolve()
        self.episodes_path = self.learning_root / "coderabbit_episodes.jsonl"
        self.patterns_path = self.learning_root / "coderabbit_patterns.json"
        self.dream_ledger_path = self.learning_root / "dream_coderabbit_ledger.jsonl"
        self.qdkt = qdkt or UnifiedQDKT()

    def _load_patterns(self) -> dict[str, dict[str, Any]]:
        if not self.patterns_path.exists():
            return {}
        value = json.loads(self.patterns_path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("Coding Waboose pattern registry must be an object")
        return {
            str(key): dict(item)
            for key, item in value.items()
            if isinstance(item, Mapping)
        }

    def _append_episode(self, lesson: CodeRabbitLesson) -> None:
        self.episodes_path.parent.mkdir(parents=True, exist_ok=True)
        with self.episodes_path.open("a", encoding="utf-8") as handle:
            handle.write(_json({"version": WABOOSE_LEARNING_VERSION, **lesson.to_dict()}) + "\n")

    def _connectome_path(
        self,
        *,
        title: str,
        message: str,
        file: str,
        symbol: str,
    ) -> dict[str, Any]:
        objective = f"Learn code review pattern: {title}. {message[:800]}"
        try:
            resolution = resolve_capabilities(
                objective,
                target_files=[file],
                target_symbols=[symbol] if symbol else [],
                repo_root=self.repo_root,
                top_k=16,
                token_budget=1800,
            )
            graph = enrich_connectome(build_capability_connectome(self.repo_root))
        except Exception as exc:
            return {
                "ok": False,
                "error": type(exc).__name__,
                "path": [],
                "path_digest": "",
                "truth_boundary": "advisory",
                "patch_authority": False,
            }
        path = dict(resolution.get("capability_connectome_path") or {})
        return {
            "ok": bool(path.get("ok", True)),
            "graph_digest": str(graph.get("graph_digest") or graph.get("digest") or ""),
            "path": list(path.get("path") or []),
            "path_details": list(path.get("path_details") or []),
            "path_digest": str(
                resolution.get("capability_path_digest")
                or path.get("path_digest")
                or ""
            ),
            "truth_boundary": "advisory",
            "patch_authority": False,
        }

    def _dream_match(
        self,
        *,
        query: str,
        patterns: Mapping[str, Mapping[str, Any]],
        verifier_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        candidates = [
            DreamCandidate(
                candidate_id=pattern_id,
                candidate_type="code_review_pattern",
                source="coding_waboose_memory",
                content=" ".join(
                    [
                        str(pattern.get("title") or ""),
                        str(pattern.get("message") or ""),
                        str(pattern.get("recommended_action") or ""),
                        str(pattern.get("semantic_rule_pack") or ""),
                    ]
                ),
                metadata={
                    "confirmation_count": int(pattern.get("confirmation_count") or 0),
                    "capability_path": list(pattern.get("capability_path") or []),
                },
                semantic_score=float(pattern.get("confidence") or 0.0),
                truth_boundary="advisory_teacher_signal",
                exact_lookup_required=True,
                verifier_result=dict(verifier_result),
            )
            for pattern_id, pattern in patterns.items()
        ]
        if not candidates:
            return {"matched_pattern_id": "", "score": 0.0, "phase_hash": ""}
        ranked = rerank_for_arena(
            query,
            candidates,
            "code_review_pattern",
            arena_domain="coding_waboose",
            verifier_result=dict(verifier_result),
            ledger_path=self.dream_ledger_path,
            qdkt=self.qdkt,
            top_k=1,
            record=True,
            metadata={"teacher": "coderabbit", "patch_authority": False},
        )
        top = list(ranked.get("ranked_candidates") or [])
        if not top:
            return {"matched_pattern_id": "", "score": 0.0, "phase_hash": ranked.get("phase_hash", "")}
        score = float(dict(top[0].get("dream_usefulness") or {}).get("usefulness_score") or 0.0)
        return {
            "matched_pattern_id": str(top[0].get("candidate_id") or "") if score >= 0.72 else "",
            "score": round(score, 6),
            "phase_hash": str(ranked.get("phase_hash") or ""),
        }

    def ingest_review(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Learn only from a completed successful CodeRabbit review at this head."""

        if not isinstance(payload, Mapping):
            raise ValueError("CodeRabbit review payload must be an object")
        status = str(
            payload.get("conclusion")
            or payload.get("status")
            or payload.get("review_status")
            or ""
        ).lower()
        success = payload.get("success") is True or status in {
            "completed",
            "success",
            "successful",
            "reviewed",
            "changes_requested",
            "commented",
            "approved",
        }
        if not success:
            return self._result(False, "coderabbit_review_not_successful")
        current_head = _git_head(self.repo_root)
        reviewed_head = str(payload.get("head_sha") or payload.get("commit_sha") or current_head)
        if current_head == "UNAVAILABLE" or reviewed_head != current_head:
            return self._result(False, "coderabbit_review_head_mismatch")
        run_id = str(payload.get("run_id") or payload.get("review_id") or _digest(payload, size=10))
        pr_number = int(payload.get("pr_number") or payload.get("pull_request_number") or 0)
        findings = self._normalized_findings(payload)
        patterns = self._load_patterns()
        learned: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for index, finding in enumerate(findings):
            try:
                lesson = self._ground_lesson(
                    finding,
                    run_id=run_id,
                    pr_number=pr_number,
                    repository_head=current_head,
                    patterns=patterns,
                )
            except (OSError, SyntaxError, UnicodeError, ValueError, LookupError) as exc:
                rejected.append({"index": index, "reason": str(exc)[:500]})
                continue
            self._append_episode(lesson)
            pattern = self._update_pattern(patterns, lesson)
            learned.append(
                {
                    "lesson_id": lesson.lesson_id,
                    "pattern_id": pattern["pattern_id"],
                    "semantic_rule_pack": lesson.semantic_rule_pack,
                    "confirmation_count": pattern["confirmation_count"],
                    "confidence": pattern["confidence"],
                    "connectome_path": lesson.capability_path.get("path", []),
                }
            )
        _atomic_write_json(self.patterns_path, patterns)
        return {
            **self._result(bool(learned), "learned" if learned else "no_grounded_findings"),
            "run_id": run_id,
            "repository_head": current_head,
            "learned_count": len(learned),
            "rejected_count": len(rejected),
            "learned": learned,
            "rejected": rejected,
            "pattern_count": len(patterns),
        }

    def _normalized_findings(self, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        raw = payload.get("findings")
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            return [dict(item) for item in raw if isinstance(item, Mapping)]
        threads = payload.get("review_threads") or payload.get("threads") or []
        result: list[dict[str, Any]] = []
        if not isinstance(threads, Sequence) or isinstance(threads, (str, bytes)):
            return result
        for thread in threads:
            if not isinstance(thread, Mapping):
                continue
            file = thread.get("path") or thread.get("file")
            line = thread.get("line") or thread.get("original_line") or 1
            for comment in thread.get("comments") or []:
                if not isinstance(comment, Mapping):
                    continue
                author = dict(comment.get("author") or {}).get("login") or comment.get("user") or ""
                if "coderabbit" not in str(author).lower():
                    continue
                body = str(comment.get("body") or "")
                result.append(
                    {
                        "file": file,
                        "line_start": line,
                        "line_end": line,
                        "title": _title_from_comment(body),
                        "message": _clean_markdown(body),
                        "severity": "high" if "major" in body.lower() else "medium",
                        "category": "correctness",
                        "suggested_fix": "Apply the grounded CodeRabbit recommendation and add a regression test.",
                        "author": author,
                    }
                )
        return result

    def _ground_lesson(
        self,
        finding: Mapping[str, Any],
        *,
        run_id: str,
        pr_number: int,
        repository_head: str,
        patterns: Mapping[str, Mapping[str, Any]],
    ) -> CodeRabbitLesson:
        author = str(finding.get("author") or finding.get("source") or "coderabbit")
        if "coderabbit" not in author.lower():
            raise ValueError("finding is not attributed to CodeRabbit")
        file = _safe_repo_path(finding.get("file") or finding.get("path"))
        path = (self.repo_root / file).resolve()
        path.relative_to(self.repo_root)
        if not path.is_file():
            raise ValueError("finding source file does not exist at the reviewed head")
        with tokenize.open(path) as handle:
            source = handle.read()
        lines = source.splitlines()
        line_start = int(finding.get("line_start") or finding.get("line") or 1)
        line_end = int(finding.get("line_end") or line_start)
        if line_start < 1 or line_end < line_start or line_end > len(lines):
            raise ValueError("finding line range is outside the reviewed source")
        excerpt_start = max(1, line_start - 3)
        excerpt_end = min(len(lines), line_end + 3)
        excerpt = "\n".join(lines[excerpt_start - 1 : excerpt_end])
        supplied_excerpt = str(finding.get("evidence_excerpt") or "").strip()
        if supplied_excerpt and supplied_excerpt not in excerpt:
            raise ValueError("finding evidence excerpt does not match the reviewed source")
        tree = ast.parse(source, filename=file)
        node = _smallest_covering_node(tree, line_start, line_end)
        signature = _ast_signature(node)
        symbol = str(getattr(node, "name", "") or finding.get("symbol") or "")
        title = str(finding.get("title") or "CodeRabbit review finding").strip()[:300]
        message = str(finding.get("message") or finding.get("body") or title).strip()[:5000]
        suggested_fix = str(finding.get("suggested_fix") or "Add a grounded regression repair.").strip()[:2000]
        semantic_rule_pack = _known_rule_pack(f"{title} {message} {suggested_fix}")
        capability_path = self._connectome_path(
            title=title,
            message=message,
            file=file,
            symbol=symbol,
        )
        verifier_result = {
            "ok": True,
            "approved": True,
            "source_grounded": True,
            "repository_head": repository_head,
        }
        dream_match = self._dream_match(
            query=f"{title} {message}",
            patterns=patterns,
            verifier_result=verifier_result,
        )
        identity = {
            "run_id": run_id,
            "head": repository_head,
            "file": file,
            "line": [line_start, line_end],
            "title": title,
            "source": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }
        return CodeRabbitLesson(
            lesson_id=f"CRLESSON-{_digest(identity, size=12)}",
            run_id=run_id,
            repository_head=repository_head,
            pr_number=pr_number,
            file=file,
            line_start=line_start,
            line_end=line_end,
            title=title,
            message=message,
            severity=str(finding.get("severity") or "medium").lower(),
            category=str(finding.get("category") or "correctness").lower(),
            suggested_fix=suggested_fix,
            source_digest=hashlib.sha256(source.encode("utf-8")).hexdigest(),
            source_excerpt_digest=hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
            source_excerpt=excerpt,
            source_grounded=True,
            semantic_rule_pack=semantic_rule_pack,
            ast_signature=signature,
            capability_path=capability_path,
            dream_match=dream_match,
            learned_at=time.time(),
        )

    def _update_pattern(
        self,
        patterns: dict[str, dict[str, Any]],
        lesson: CodeRabbitLesson,
    ) -> dict[str, Any]:
        matched = str(lesson.dream_match.get("matched_pattern_id") or "")
        pattern_id = matched if matched in patterns else ""
        if not pattern_id:
            pattern_id = "CRPATTERN-" + _digest(
                {
                    "pack": lesson.semantic_rule_pack,
                    "title_tokens": sorted(_tokens(lesson.title)),
                    "calls": lesson.ast_signature.get("calls", []),
                    "node_types": lesson.ast_signature.get("node_types", []),
                },
                size=12,
            )
        existing = dict(patterns.get(pattern_id) or {})
        count = int(existing.get("confirmation_count") or 0) + 1
        confidence = min(0.98, 0.58 + 0.10 * count + (0.08 if lesson.semantic_rule_pack else 0.0))
        capability_nodes = list(
            dict.fromkeys(
                [
                    *list(existing.get("capability_path") or []),
                    *list(lesson.capability_path.get("path") or []),
                ]
            )
        )
        pattern = {
            "pattern_id": pattern_id,
            "title": lesson.title,
            "message": lesson.message,
            "recommended_action": lesson.suggested_fix,
            "severity": lesson.severity,
            "category": lesson.category,
            "semantic_rule_pack": lesson.semantic_rule_pack,
            "confirmation_count": count,
            "confidence": round(confidence, 6),
            "source_grounded_confirmations": int(existing.get("source_grounded_confirmations") or 0) + 1,
            "files": sorted(set(existing.get("files") or []) | {lesson.file}),
            "capability_path": capability_nodes,
            "ast_signature": lesson.ast_signature,
            "title_tokens": sorted(_tokens(f"{lesson.title} {lesson.message}"))[:160],
            "last_repository_head": lesson.repository_head,
            "first_seen": float(existing.get("first_seen") or lesson.learned_at),
            "last_confirmed": lesson.learned_at,
            "teacher": "CodeRabbit",
            "truth_boundary": "advisory_teacher_signal",
            "patch_authority": False,
        }
        patterns[pattern_id] = pattern
        event_payload = {
            "pattern_id": pattern_id,
            "file_path": lesson.file,
            "semantic_rule_pack": lesson.semantic_rule_pack,
            "confirmation_count": count,
            "connectome_path": capability_nodes,
            "source_grounded": True,
            "success": True,
            "patch_authority": False,
        }
        self.qdkt.observe(
            "coderabbit_review_learning",
            event_payload,
            rationale=f"Grounded CodeRabbit finding: {lesson.title}",
            concept=f"coding_waboose:{pattern_id}",
            confidence=confidence,
            subsystem="coding_waboose",
        )
        if count >= _CRYSTAL_CONFIRMATIONS and confidence >= _CRYSTAL_CONFIDENCE:
            self.qdkt.crystallize(
                f"coding_waboose:{pattern_id}",
                lesson.suggested_fix,
                confidence=confidence,
                source="coderabbit_grounded_repetition",
            )
            pattern["qdkt_crystallized"] = True
        else:
            pattern["qdkt_crystallized"] = False
        return pattern

    def learning_context(
        self,
        objective: str,
        *,
        changed_files: Sequence[str] = (),
        top_k: int = 8,
    ) -> dict[str, Any]:
        patterns = self._load_patterns()
        candidates = [
            DreamCandidate(
                candidate_id=pattern_id,
                candidate_type="code_review_pattern",
                source="coding_waboose_memory",
                content=" ".join(
                    [
                        str(pattern.get("title") or ""),
                        str(pattern.get("message") or ""),
                        str(pattern.get("recommended_action") or ""),
                    ]
                ),
                metadata={
                    "semantic_rule_pack": pattern.get("semantic_rule_pack", ""),
                    "confirmation_count": pattern.get("confirmation_count", 0),
                    "capability_path": pattern.get("capability_path", []),
                    "files": pattern.get("files", []),
                },
                semantic_score=float(pattern.get("confidence") or 0.0),
                truth_boundary="advisory_teacher_signal",
                exact_lookup_required=True,
                verifier_result={"ok": True, "approved": True},
            )
            for pattern_id, pattern in patterns.items()
        ]
        if not candidates:
            return {
                "ok": True,
                "version": WABOOSE_LEARNING_VERSION,
                "patterns": [],
                "pattern_count": 0,
                "patch_authority": False,
            }
        query = " ".join([objective, *changed_files])
        ranked = rerank_for_arena(
            query,
            candidates,
            "code_review_pattern",
            arena_domain="coding_waboose",
            ledger_path=self.dream_ledger_path,
            qdkt=self.qdkt,
            top_k=max(1, min(24, int(top_k))),
            record=False,
            metadata={"phase": "waboose_prepare", "patch_authority": False},
        )
        return {
            "ok": True,
            "version": WABOOSE_LEARNING_VERSION,
            "patterns": list(ranked.get("ranked_candidates") or []),
            "pattern_count": len(patterns),
            "phase_hash": ranked.get("phase_hash", ""),
            "connectome_routed": True,
            "dream_lite_ranked": True,
            "qdkt_backed": True,
            "truth_boundary": "advisory_teacher_signal",
            "patch_authority": False,
        }

    def scan_learned_patterns(self, *, file: str, source: str, tree: ast.AST) -> list[dict[str, Any]]:
        """Surface non-promoted learned patterns as probable, never repair proof."""

        patterns = self._load_patterns()
        findings: list[dict[str, Any]] = []
        source_tokens = _tokens(source)
        source_signature = _ast_signature(tree)
        source_nodes = set(source_signature["node_types"])
        source_calls = set(source_signature["calls"])
        for pattern_id, pattern in patterns.items():
            if pattern.get("semantic_rule_pack"):
                continue
            pattern_tokens = set(pattern.get("title_tokens") or [])
            pattern_signature = dict(pattern.get("ast_signature") or {})
            pattern_nodes = set(pattern_signature.get("node_types") or [])
            pattern_calls = set(pattern_signature.get("calls") or [])
            token_overlap = len(source_tokens & pattern_tokens) / max(1, len(pattern_tokens))
            node_overlap = len(source_nodes & pattern_nodes) / max(1, len(pattern_nodes))
            call_overlap = len(source_calls & pattern_calls) / max(1, len(pattern_calls)) if pattern_calls else 1.0
            similarity = token_overlap * 0.35 + node_overlap * 0.35 + call_overlap * 0.30
            if similarity < 0.78:
                continue
            confidence = min(0.88, 0.62 + 0.06 * int(pattern.get("confirmation_count") or 1))
            findings.append(
                {
                    "origin": "waboose_learned_pattern",
                    "rule": f"learned:{pattern_id}",
                    "category": str(pattern.get("category") or "correctness"),
                    "severity": str(pattern.get("severity") or "medium"),
                    "confidence": round(confidence, 4),
                    "title": f"Learned CodeRabbit pattern may recur: {pattern.get('title', pattern_id)}",
                    "message": str(pattern.get("message") or "A previously grounded CodeRabbit pattern resembles this file."),
                    "file": file,
                    "line_start": 1,
                    "line_end": max(1, len(source.splitlines())),
                    "suggested_fix": str(pattern.get("recommended_action") or "Run a focused semantic review."),
                    "evidence": [
                        {
                            "kind": "dream_lite_pattern_similarity",
                            "pattern_id": pattern_id,
                            "similarity": round(similarity, 6),
                            "confirmation_count": pattern.get("confirmation_count", 0),
                            "capability_path": pattern.get("capability_path", []),
                            "truth_boundary": "advisory_teacher_signal",
                        }
                    ],
                    "status": "probable",
                    "repair_authority": False,
                }
            )
        return findings

    def summary(self) -> dict[str, Any]:
        patterns = self._load_patterns()
        episodes = 0
        if self.episodes_path.exists():
            with self.episodes_path.open("r", encoding="utf-8") as handle:
                episodes = sum(1 for line in handle if line.strip())
        return {
            "ok": True,
            "version": WABOOSE_LEARNING_VERSION,
            "episode_count": episodes,
            "pattern_count": len(patterns),
            "crystallized_count": sum(bool(item.get("qdkt_crystallized")) for item in patterns.values()),
            "known_rule_pack_count": sum(bool(item.get("semantic_rule_pack")) for item in patterns.values()),
            "connectome_routed": True,
            "dream_lite_ranked": True,
            "qdkt_backed": True,
            "patch_authority": False,
            "production_mutation": False,
        }

    @staticmethod
    def _result(ok: bool, status: str) -> dict[str, Any]:
        return {
            "ok": ok,
            "version": WABOOSE_LEARNING_VERSION,
            "status": status,
            "teacher": "CodeRabbit",
            "teacher_is_patch_authority": False,
            "connectome_is_advisory": True,
            "dream_lite_is_ranking_only": True,
            "qdkt_crystals_are_patch_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
        }


__all__ = [
    "CodeRabbitLearningStore",
    "CodeRabbitLesson",
    "DEFAULT_LEARNING_ROOT",
    "WABOOSE_LEARNING_VERSION",
]
