"""Coding Waboose integration for typed external-review lessons and Crucible replay.

This is a narrow extension of the retained :mod:`aura_coding_waboose` owner.  It
adds deterministic review-lesson scans, typed CodeRabbit/Codex/manual review
normalization, and adversarial Crucible replay without changing Coding Waboose's
review-only authority boundary.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path
import re
import tokenize
from typing import Any

from aura_coding_waboose import CodingWaboose
from aura_coding_waboose_review_lessons import (
    DEFAULT_LEARNING_ROOT,
    DEFAULT_REGISTRY_PATH,
    PATCH_AUTHORITY,
    REVIEW_LESSON_VERSION,
    ReviewLessonEngine,
    VSA_PATCH_AUTHORITY,
    detect_authority_aliases,
    detect_count_without_byte_budget,
    detect_noncanonical_source_path,
    detect_order_dependent_digesting,
    detect_protected_metadata_overrides,
    detect_stale_evidence_claim,
    detect_truncate_before_sort,
    detect_uri_alias_encoding,
)

WABOOSE_REVIEW_LEARNING_VERSION = "AURA_CODING_WABOOSE_REVIEW_LEARNING_V1"

_COUNT_BUDGET_RE = re.compile(
    r"(?m)^\s*(MAX_[A-Z0-9_]*(?:COUNT|ITEMS|NODES|EDGES|RECORDS|REFS))\s*="
)
_BYTE_BUDGET_RE = re.compile(
    r"(?m)^\s*MAX_[A-Z0-9_]*(?:BYTE|BYTES|SIZE|PAYLOAD)\w*\s*="
)
_DIGEST_CALL_RE = re.compile(
    r"\b(?:digest|sha256|blake2b|canonical_digest)\s*\((?P<body>[^)]{1,600})\)",
    re.IGNORECASE | re.DOTALL,
)
_SET_LIKE_NAME_RE = re.compile(
    r"(?:^|_)(?:assets|edges|entities|findings|frames|ids|links|nodes|paths|records|refs|relations|source_refs)(?:$|_)",
    re.IGNORECASE,
)


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


def _literal_value(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return "<dynamic>"


def _line(node: ast.AST) -> tuple[int, int]:
    start = int(getattr(node, "lineno", 1) or 1)
    end = int(getattr(node, "end_lineno", start) or start)
    return start, end


def _review_finding(
    *,
    detector: Mapping[str, Any],
    file: str,
    title: str,
    suggested_fix: str,
    line_start: int = 1,
    line_end: int = 1,
    category: str = "correctness",
    severity: str = "medium",
    confidence: float | None = None,
) -> dict[str, Any]:
    return {
        "origin": "waboose_review_lesson",
        "rule": str(detector.get("detector_id") or detector.get("code") or "review_lesson"),
        "category": category,
        "severity": severity,
        "confidence": float(confidence if confidence is not None else detector.get("confidence", 0.9)),
        "title": title,
        "message": str(detector.get("message") or title),
        "file": file,
        "line_start": max(1, int(line_start)),
        "line_end": max(max(1, int(line_start)), int(line_end)),
        "suggested_fix": suggested_fix,
        "evidence": [
            {
                "kind": "review_lesson_detector",
                "detector_id": detector.get("detector_id", ""),
                "finding_id": detector.get("finding_id", ""),
                "evidence": detector.get("evidence"),
                "source": REVIEW_LESSON_VERSION,
            }
        ],
        "status": "confirmed" if float(detector.get("confidence", 0.0)) >= 0.98 else "probable",
        "repair_authority": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def scan_python_review_lessons(*, file: str, source: str, tree: ast.AST) -> list[dict[str, Any]]:
    """Run precision-first static lesson detectors over one Python source file."""

    findings: list[dict[str, Any]] = []
    sorted_assignments: dict[str, int] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets: list[ast.AST]
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            else:
                targets = [node.target]
            if isinstance(value, ast.Call) and _call_name(value.func).endswith("sorted"):
                for target in targets:
                    if isinstance(target, ast.Name):
                        sorted_assignments[target.id] = int(getattr(node, "lineno", 0) or 0)

        if isinstance(node, ast.Dict):
            payload: dict[str, Any] = {}
            key_nodes: dict[str, ast.AST] = {}
            for key_node, value_node in zip(node.keys, node.values):
                if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                    continue
                payload[key_node.value] = _literal_value(value_node)
                key_nodes[key_node.value] = key_node
            if payload:
                for detector in detect_authority_aliases(payload):
                    evidence = dict(detector.get("evidence") or {})
                    key = str(evidence.get("key") or "")
                    start, end = _line(key_nodes.get(key, node))
                    findings.append(
                        _review_finding(
                            detector=detector,
                            file=file,
                            title="Authority metadata alias bypass",
                            suggested_fix=(
                                "Normalize security-sensitive metadata keys by case-folding and "
                                "removing separators, then reject protected aliases recursively."
                            ),
                            line_start=start,
                            line_end=end,
                            category="authority",
                            severity="high",
                        )
                    )
                for detector in detect_protected_metadata_overrides(payload):
                    evidence = dict(detector.get("evidence") or {})
                    key = str(evidence.get("key") or "")
                    start, end = _line(key_nodes.get(key, node))
                    findings.append(
                        _review_finding(
                            detector=detector,
                            file=file,
                            title="Protected authority metadata can be contradicted",
                            suggested_fix=(
                                "Reject protected authority fields before metadata merge and "
                                "reassert the immutable false authority envelope afterward."
                            ),
                            line_start=start,
                            line_end=end,
                            category="authority",
                            severity="high",
                        )
                    )

        if isinstance(node, ast.Call):
            name = _call_name(node.func).casefold()
            if any(token in name for token in ("digest", "sha256", "blake2b")):
                for argument in node.args:
                    if not isinstance(argument, ast.Name):
                        continue
                    if not _SET_LIKE_NAME_RE.search(argument.id):
                        continue
                    prior_sort = sorted_assignments.get(argument.id, 0)
                    line_start, line_end = _line(node)
                    if prior_sort and prior_sort < line_start:
                        continue
                    detector_packet = detect_order_dependent_digesting(
                        {
                            "collection_name": argument.id,
                            "canonicalized_before_digest": False,
                        }
                    )
                    for detector in detector_packet:
                        findings.append(
                            _review_finding(
                                detector=detector,
                                file=file,
                                title="Potential order-dependent digest identity",
                                suggested_fix=(
                                    "Canonicalize and deduplicate set-like values before assigning "
                                    "IDs, hashing, caching, or interchange."
                                ),
                                line_start=line_start,
                                line_end=line_end,
                                category="correctness",
                                severity="medium",
                                confidence=0.88,
                            )
                        )

        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            slice_node = node.slice
            if not isinstance(slice_node, ast.Slice) or slice_node.lower is not None:
                continue
            if slice_node.upper is None:
                continue
            line_start, line_end = _line(node)
            source_before = "\n".join(source.splitlines()[: max(0, line_start - 1)])
            name = node.value.id
            if not _SET_LIKE_NAME_RE.search(name):
                continue
            sorted_before = bool(
                re.search(rf"(?:sorted\s*\(\s*{re.escape(name)}\b|{re.escape(name)}\.sort\s*\()", source_before)
            )
            if sorted_before:
                continue
            for detector in detect_truncate_before_sort(
                {"truncated_before_sort": True, "collection": name}
            ):
                findings.append(
                    _review_finding(
                        detector=detector,
                        file=file,
                        title="Collection may be truncated before canonical sorting",
                        suggested_fix="Normalize, stably sort, and deduplicate before applying the cap.",
                        line_start=line_start,
                        line_end=line_end,
                        category="correctness",
                        severity="medium",
                        confidence=0.86,
                    )
                )

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
            path_candidates: list[str] = []
            if text.startswith("source:"):
                path_candidates.append(text)
            elif text.startswith(("./", "../", "/")) or "\\" in text:
                if any(token in text.casefold() for token in (".py", ".json", ".md", "source")):
                    path_candidates.append(text)
            for candidate in path_candidates:
                for detector in detect_noncanonical_source_path(candidate):
                    start, end = _line(node)
                    findings.append(
                        _review_finding(
                            detector=detector,
                            file=file,
                            title="Noncanonical source path is retained as evidence",
                            suggested_fix="Require canonical repository-relative POSIX paths before constructing source anchors.",
                            line_start=start,
                            line_end=end,
                            category="security",
                            severity="high",
                        )
                    )
            if "%2f" in text.casefold() or "%5c" in text.casefold() or "://" in text:
                for detector in detect_uri_alias_encoding(text):
                    start, end = _line(node)
                    findings.append(
                        _review_finding(
                            detector=detector,
                            file=file,
                            title="Ambiguous encoded or repeated URI separator",
                            suggested_fix="Reject decoded separator changes and ambiguous URI aliases fail closed.",
                            line_start=start,
                            line_end=end,
                            category="security",
                            severity="high",
                        )
                    )

    count_constants = sorted(set(_COUNT_BUDGET_RE.findall(source)))
    if count_constants and not _BYTE_BUDGET_RE.search(source):
        variable_evidence_modules = (
            "interaction",
            "metadata",
            "packet",
            "review",
            "scene",
            "source",
            "transport",
            "websocket",
            "ws_",
        )
        if any(token in file.casefold() for token in variable_evidence_modules):
            for detector in detect_count_without_byte_budget(
                {count_constants[0]: 1, "attacker_controlled": True}
            ):
                line_start = next(
                    (
                        index
                        for index, line in enumerate(source.splitlines(), start=1)
                        if count_constants[0] in line
                    ),
                    1,
                )
                findings.append(
                    _review_finding(
                        detector=detector,
                        file=file,
                        title="Count-bounded evidence has no module byte budget",
                        suggested_fix="Add per-item and aggregate canonical byte ceilings and regression cases.",
                        line_start=line_start,
                        line_end=line_start,
                        category="security",
                        severity="medium",
                        confidence=0.86,
                    )
                )

    # A lexical fallback catches direct digest calls that AST cannot relate to a
    # preceding canonicalization assignment.  It remains probable, not confirmed.
    for match in _DIGEST_CALL_RE.finditer(source):
        body = match.group("body")
        names = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", body)
        for name in names[:4]:
            if not _SET_LIKE_NAME_RE.search(name):
                continue
            if name in sorted_assignments or name in {"self", "str", "bytes", "value"}:
                continue
            prefix = source[: match.start()]
            if re.search(rf"sorted\s*\(\s*{re.escape(name)}\b", prefix):
                continue
            line_start = source.count("\n", 0, match.start()) + 1
            detector = detect_order_dependent_digesting(
                {"collection_name": name, "canonicalized_before_digest": False}
            )[0]
            findings.append(
                _review_finding(
                    detector=detector,
                    file=file,
                    title="Digest input lacks visible canonicalization",
                    suggested_fix="Prove and test canonical ordering before digest construction.",
                    line_start=line_start,
                    line_end=line_start,
                    category="correctness",
                    severity="medium",
                    confidence=0.86,
                )
            )
            break

    # Deduplicate by rule/file/line/message before the parent arena normalization.
    unique: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for finding in findings:
        key = (
            str(finding.get("rule") or ""),
            str(finding.get("file") or ""),
            int(finding.get("line_start") or 0),
            str(finding.get("message") or ""),
        )
        unique.setdefault(key, finding)
    return list(unique.values())


def scan_text_review_lessons(*, file: str, source: str) -> list[dict[str, Any]]:
    """Scan docs/workflows for stale-evidence claims and static path/URI aliases."""

    findings: list[dict[str, Any]] = []
    lowered = source.casefold()
    if any(term in lowered for term in ("workflow configured", "test file exists", "manual inspection")) and any(
        term in lowered for term in ("workflow passed", "test executed", "ci verification")
    ):
        detector = detect_stale_evidence_claim(
            {
                "claim": "current workflow passed",
                "evidence_status": "configured",
                "evidence_head": "historical",
                "current_head": "current",
            }
        )[0]
        findings.append(
            _review_finding(
                detector=detector,
                file=file,
                title="Evidence prose may upgrade configured or historical proof",
                suggested_fix="Bind each verification statement to an exact SHA, run, and observed status.",
                line_start=1,
                line_end=1,
                category="contract",
                severity="medium",
                confidence=0.9,
            )
        )
    return findings


class ReviewLessonAwareCodingWaboose(CodingWaboose):
    """Coding Waboose with typed PR-review lessons and replayable detectors."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        command_runner: Any = None,
        learning_root: str | Path | None = None,
        review_registry_path: str | Path = DEFAULT_REGISTRY_PATH,
        review_learning_root: str | Path = DEFAULT_LEARNING_ROOT,
    ) -> None:
        super().__init__(
            repo_root,
            command_runner=command_runner,
            learning_root=learning_root,
        )
        registry_path = Path(review_registry_path)
        if review_registry_path == DEFAULT_REGISTRY_PATH:
            registry_path = Path(".aura/review_lessons/pr164_spatial_review_lessons.json")
        self.review_lesson_engine = ReviewLessonEngine(
            self.repo_root,
            registry_path=registry_path,
            learning_root=review_learning_root,
        )

    @staticmethod
    def _brand_review_learning(packet: dict[str, Any]) -> dict[str, Any]:
        packet["review_learning_version"] = WABOOSE_REVIEW_LEARNING_VERSION
        packet["production_mutation"] = False
        packet["automatic_fix"] = False
        packet["automatic_commit"] = False
        packet["automatic_push"] = False
        packet["automatic_pull_request"] = False
        packet["automatic_merge"] = False
        packet["human_review_required"] = True
        packet["patch_authority"] = PATCH_AUTHORITY
        packet["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return packet

    def prepare(self, value: Any) -> dict[str, Any]:
        result = super().prepare(value)
        if result.get("ok"):
            summary = self.review_lesson_engine.summary()
            result["review_lesson_context"] = {
                "registry_digest": summary["registry_digest"],
                "lesson_count": summary["lesson_count"],
                "scenario_count": summary["scenario_count"],
                "detectors": summary["detectors"],
                "truth_boundary": summary["truth_boundary"],
            }
            state = self._reviews.get(str(result.get("review_id") or ""))
            if state is not None:
                state["review_lesson_context"] = result["review_lesson_context"]
        return self._brand_review_learning(result)

    def scan(self, review_id: str) -> dict[str, Any]:
        result = super().scan(review_id)
        if not result.get("ok"):
            return self._brand_review_learning(result)
        state = self._reviews[review_id]
        added: list[dict[str, Any]] = []
        changed_files = list(state["contract"].changed_files)
        deleted_files = set(state.get("deleted_files", ()))
        source_by_file: dict[str, str] = {}
        for file in changed_files:
            if file in deleted_files:
                continue
            path = self._resolve_file(file)
            if path is None or not path.is_file():
                continue
            try:
                if file.endswith(".py"):
                    with tokenize.open(path) as handle:
                        source = handle.read()
                    source_by_file[file] = source
                    added.extend(
                        scan_python_review_lessons(
                            file=file,
                            source=source,
                            tree=ast.parse(source, filename=file),
                        )
                    )
                elif file.endswith((".md", ".json", ".yml", ".yaml")):
                    source = path.read_text(encoding="utf-8")
                    source_by_file[file] = source
                    added.extend(scan_text_review_lessons(file=file, source=source))
            except (OSError, SyntaxError, UnicodeError, LookupError):
                continue

        workflows = {
            file: source
            for file, source in source_by_file.items()
            if file.startswith(".github/workflows/") and file.endswith((".yml", ".yaml"))
        }
        changed_tests = [file for file in changed_files if file.startswith("tests/test_")]
        if workflows and changed_tests:
            from aura_coding_waboose_review_lessons import detect_unwired_regression

            for workflow_file, workflow_source in workflows.items():
                for test_file in changed_tests:
                    for detector in detect_unwired_regression(
                        {
                            "test_path": test_file,
                            "workflow": workflow_source,
                            "required_stages": ("py_compile", "ruff", "pytest"),
                        }
                    ):
                        added.append(
                            _review_finding(
                                detector=detector,
                                file=workflow_file,
                                title="Changed regression is not wired into every focused workflow gate",
                                suggested_fix=(
                                    "Add the regression to compile, fatal Ruff, and focused pytest stages, "
                                    "or prove deterministic repository-wide discovery."
                                ),
                                line_start=1,
                                line_end=1,
                                category="test_gap",
                                severity="high",
                            )
                        )

        if added:
            state["deterministic_findings"] = self._normalize_findings(
                [*state.get("deterministic_findings", []), *added],
                origin_default="waboose_review_lesson",
            )
            result["deterministic_findings"] = state["deterministic_findings"]
        replay = self.review_lesson_engine.crucible()
        result["review_lesson_findings_added"] = len(added)
        result["review_lesson_crucible"] = {
            "status": replay["status"],
            "scenario_count": replay["scenario_count"],
            "passed_count": replay["passed_count"],
            "failed_count": replay["failed_count"],
            "registry_digest": replay["registry_digest"],
        }
        result["agent_packet"] = self._agent_packet_from_state(review_id, include_source=False)
        return self._brand_review_learning(result)

    def _agent_packet_from_state(
        self,
        review_id: str,
        *,
        include_source: bool,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        packet = super()._agent_packet_from_state(
            review_id,
            include_source=include_source,
            max_files=max_files,
            max_lines_per_file=max_lines_per_file,
        )
        packet["review_lesson_context"] = self._reviews[review_id].get(
            "review_lesson_context",
            self.review_lesson_engine.summary(),
        )
        packet["agent_instructions"] = [
            "Apply PR-review lesson detectors as hypotheses until exact source and regression evidence corroborate them.",
            "Distinguish current-head, historical, resolved, outdated, and duplicate external findings.",
            "Never convert reviewer output or Crucible replay into patch, commit, push, pull-request, merge, or production authority.",
            *list(packet.get("agent_instructions") or []),
        ]
        return self._brand_review_learning(packet)

    def ingest_external_review(
        self,
        review_payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        return self._brand_review_learning(
            self.review_lesson_engine.ingest_review(
                review_payload,
                current_head=current_head,
            )
        )

    def review_lesson_summary(self) -> dict[str, Any]:
        return self._brand_review_learning(self.review_lesson_engine.summary())

    def run_review_lesson_detector(self, detector_id: str, candidate: Any) -> dict[str, Any]:
        return self._brand_review_learning(
            self.review_lesson_engine.detector(detector_id, candidate)
        )

    def replay_review_lessons(self, detector_ids: Sequence[str] = ()) -> dict[str, Any]:
        return self._brand_review_learning(
            self.review_lesson_engine.crucible(detector_ids=detector_ids)
        )


__all__ = [
    "ReviewLessonAwareCodingWaboose",
    "WABOOSE_REVIEW_LEARNING_VERSION",
    "scan_python_review_lessons",
    "scan_text_review_lessons",
]
