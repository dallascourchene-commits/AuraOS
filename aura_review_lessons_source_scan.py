"""Precision-first static source-shape scanner for review lessons."""
from __future__ import annotations

import ast
import re
from typing import Any

from aura_review_lessons_contracts import (
    _CANONICAL_AUTHORITY_KEYS,
    _finding,
    _safe_repo_path,
)


def scan_source_for_review_lessons(
    *,
    file: str,
    source: str,
) -> list[dict[str, Any]]:
    """Run conservative source-shape detectors as probable review findings.

    These checks intentionally recognize only narrow shapes learned from PR #164.
    They create review evidence, not proof or repair authority.  A finding must
    still be corroborated by exact tests, runtime behavior, or human review.
    """

    canonical_file = _safe_repo_path(file)
    findings: list[dict[str, Any]] = []
    lines = source.splitlines()

    try:
        tree = compile(source, canonical_file, "exec", flags=0, dont_inherit=True, optimize=0)
        del tree
    except SyntaxError:
        return findings

    # Caller metadata expanded after protected false fields.
    try:
        parsed = ast.parse(source, filename=canonical_file)
    except SyntaxError:
        parsed = None
    if parsed is not None:
        for node in ast.walk(parsed):
            if not isinstance(node, ast.Dict):
                continue
            protected_indexes: list[int] = []
            for index, (key_node, value_node) in enumerate(zip(node.keys, node.values)):
                if (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                    and key_node.value in _CANONICAL_AUTHORITY_KEYS
                    and isinstance(value_node, ast.Constant)
                    and value_node.value is False
                ):
                    protected_indexes.append(index)
            if not protected_indexes:
                continue
            for index, (key_node, value_node) in enumerate(zip(node.keys, node.values)):
                if key_node is not None or index <= min(protected_indexes):
                    continue
                mapping_name = ""
                if isinstance(value_node, ast.Name):
                    mapping_name = value_node.id
                elif isinstance(value_node, ast.Attribute):
                    mapping_name = value_node.attr
                if "metadata" not in mapping_name.casefold():
                    continue
                line = int(getattr(node, "lineno", 1) or 1)
                end_line = int(getattr(node, "end_lineno", line) or line)
                finding = _finding(
                    detector_id="detect_protected_metadata_overrides",
                    code="PROTECTED_AUTHORITY_OVERRIDE_SHAPE",
                    message=(
                        "A metadata mapping is expanded after protected false authority fields; "
                        "verify that untrusted keys cannot override the authority envelope."
                    ),
                    path=canonical_file,
                    line_start=line,
                    line_end=end_line,
                    evidence={
                        "mapping": mapping_name,
                        "source_shape": "protected_false_then_mapping_unpack",
                    },
                    confidence=0.86,
                )
                finding["source_grounded"] = True
                findings.append(finding)

    # Truncation before a later stable sort of the same collection.
    slice_pattern = re.compile(
        r"(?m)(?P<target>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<collection>[A-Za-z_][A-Za-z0-9_]*)"
        r"\s*\[\s*:\s*(?P<cap>[A-Za-z_][A-Za-z0-9_]*|\d+)\s*\]"
    )
    for match in slice_pattern.finditer(source):
        collection = match.group("collection")
        tail = source[match.end() :]
        later_sort = re.search(
            rf"(?:sorted\s*\(\s*{re.escape(match.group('target'))}\b|"
            rf"{re.escape(match.group('target'))}\.sort\s*\()",
            tail,
        )
        if not later_sort:
            continue
        line = source.count("\n", 0, match.start()) + 1
        finding = _finding(
            detector_id="detect_truncate_before_sort",
            code="TRUNCATE_BEFORE_SORT_SHAPE",
            message=f"{collection} is truncated before the retained subset is sorted.",
            path=canonical_file,
            line_start=line,
            line_end=line,
            evidence={"collection": collection, "cap": match.group("cap")},
            confidence=0.9,
        )
        finding["source_grounded"] = True
        findings.append(finding)

    # Digesting a likely set-like collection without an explicit canonicalizer.
    digest_calls = re.compile(
        r"(?m)(?:sha256|blake2b|digest|canonical_digest)\s*\(\s*(?P<collection>links|edges|"
        r"entities|records|source_refs|findings)\b"
    )
    for match in digest_calls.finditer(source):
        collection = match.group("collection")
        prefix = source[max(0, match.start() - 5000) : match.start()]
        canonicalized = re.search(
            rf"(?:sorted|canonicalize|normalize|deduplicate)\s*\([^\n)]*\b{re.escape(collection)}\b",
            prefix,
        )
        if canonicalized:
            continue
        line = source.count("\n", 0, match.start()) + 1
        finding = _finding(
            detector_id="detect_order_dependent_digesting",
            code="ORDER_DEPENDENT_DIGEST_SHAPE",
            message=f"{collection} reaches a digest call without a nearby explicit canonicalizer.",
            path=canonical_file,
            line_start=line,
            line_end=line,
            evidence={"collection": collection},
            confidence=0.72,
        )
        finding["source_grounded"] = True
        findings.append(finding)

    # URI decode followed by slash stripping reproduces the reviewed alias class.
    uri_alias = re.compile(
        r"(?s)(?:unquote|url_decode)\s*\([^)]*\).{0,500}?\.lstrip\s*\(\s*['\"]/[\\/]*['\"]\s*\)"
    )
    for match in uri_alias.finditer(source):
        line = source.count("\n", 0, match.start()) + 1
        finding = _finding(
            detector_id="detect_uri_alias_encoding",
            code="URI_DECODE_THEN_STRIP_SHAPE",
            message="URI decoding is followed by leading-separator stripping; reject aliases instead of repairing them.",
            path=canonical_file,
            line_start=line,
            line_end=min(len(lines), line + match.group(0).count("\n")),
            evidence={"source_shape": "decode_then_lstrip_separator"},
            confidence=0.9,
        )
        finding["source_grounded"] = True
        findings.append(finding)

    # Count ceilings without any byte ceilings in the same module are advisory.
    count_constants = sorted(set(re.findall(r"\bMAX_[A-Z0-9_]*(?:COUNT|ITEMS|NODES|EDGES)\b", source)))
    byte_constants = sorted(set(re.findall(r"\bMAX_[A-Z0-9_]*(?:BYTE|BYTES|SIZE)\b", source)))
    if count_constants and not byte_constants:
        finding = _finding(
            detector_id="detect_count_without_byte_budget",
            code="COUNT_ONLY_BOUND_SHAPE",
            message="The module declares count ceilings but no explicit byte ceiling; verify all retained untrusted evidence is byte-bounded.",
            path=canonical_file,
            line_start=1,
            line_end=min(len(lines), 1),
            evidence={"count_constants": count_constants, "byte_constants": byte_constants},
            confidence=0.58,
        )
        finding["source_grounded"] = True
        findings.append(finding)

    # Deterministic de-duplication by detector/path/range/code.
    unique: dict[tuple[str, str, int, int, str], dict[str, Any]] = {}
    for finding in findings:
        key = (
            str(finding.get("detector_id") or ""),
            str(finding.get("path") or ""),
            int(finding.get("line_start") or 0),
            int(finding.get("line_end") or 0),
            str(finding.get("code") or ""),
        )
        unique[key] = finding
    return [unique[key] for key in sorted(unique)]

__all__ = ["scan_source_for_review_lessons"]
