"""Determinism, coordinate, interchange, and source-shape review detectors."""
from __future__ import annotations

import ast
from collections.abc import Mapping
import re
from typing import Any

from aura_review_lessons_contracts import (
    _CANONICAL_AUTHORITY_KEYS,
    _finding,
    _is_sequence,
    _safe_repo_path,
)


def detect_order_dependent_digesting(candidate: Any) -> list[dict[str, Any]]:
    """Detect digesting of set-like/order-insensitive values before canonicalization."""

    source = str(candidate.get("source", "") if isinstance(candidate, Mapping) else candidate or "")
    collection = "records"
    if isinstance(candidate, Mapping):
        collection = str(candidate.get("collection_name") or candidate.get("collection") or "records")
        if candidate.get("canonicalized_before_digest") is False:
            return [
                _finding(
                    detector_id="detect_order_dependent_digesting",
                    code="ORDER_DEPENDENT_DIGEST",
                    message=f"{collection} reaches digesting before canonical ordering.",
                    evidence={"collection": collection, "canonicalized_before_digest": False},
                )
            ]
    if not source:
        return []
    digest_pattern = re.compile(
        rf"(?:digest|sha256|blake2b|canonical_digest)\s*\([^)]*\b{re.escape(collection)}\b",
        re.IGNORECASE | re.DOTALL,
    )
    canonical_pattern = re.compile(
        rf"(?:sorted|canonicalize|normalize)\s*\([^)]*\b{re.escape(collection)}\b",
        re.IGNORECASE | re.DOTALL,
    )
    if digest_pattern.search(source) and not canonical_pattern.search(source):
        return [
            _finding(
                detector_id="detect_order_dependent_digesting",
                code="ORDER_DEPENDENT_DIGEST",
                message=f"{collection} appears to be digested without prior canonicalization.",
                evidence={"collection": collection, "source_excerpt": source[:1200]},
                confidence=0.92,
            )
        ]
    return []


def detect_truncate_before_sort(candidate: Any) -> list[dict[str, Any]]:
    """Detect truncating set-like inputs before stable sorting."""

    if isinstance(candidate, Mapping):
        if candidate.get("truncated_before_sort") is True:
            return [
                _finding(
                    detector_id="detect_truncate_before_sort",
                    code="TRUNCATE_BEFORE_SORT",
                    message="Set-like records are truncated before stable sorting.",
                    evidence=dict(candidate),
                )
            ]
        source = str(candidate.get("source") or "")
        collection = str(candidate.get("collection_name") or "links")
    else:
        source = str(candidate or "")
        collection = "links"
    if not source:
        return []
    slice_match = re.search(
        rf"\b{re.escape(collection)}\b\s*\[\s*:\s*[A-Za-z0-9_]+\s*\]",
        source,
    )
    sort_match = re.search(
        rf"(?:sorted\s*\(\s*{re.escape(collection)}\b|{re.escape(collection)}\.sort\s*\()",
        source,
    )
    if slice_match and (not sort_match or slice_match.start() < sort_match.start()):
        return [
            _finding(
                detector_id="detect_truncate_before_sort",
                code="TRUNCATE_BEFORE_SORT",
                message=f"{collection} is sliced before a stable canonical sort.",
                evidence={"collection": collection, "source_excerpt": source[:1200]},
                confidence=0.94,
            )
        ]
    return []


def detect_implicit_coordinate_basis_change(candidate: Any) -> list[dict[str, Any]]:
    """Detect mixed frame conventions without an explicit basis conversion."""

    if not isinstance(candidate, Mapping):
        return []
    parent = dict(candidate.get("parent") or {})
    child = dict(candidate.get("child") or {})
    explicit = candidate.get("explicit_conversion") is True
    convention_changed = any(
        parent.get(key) not in {None, ""} and child.get(key) not in {None, ""}
        and parent.get(key) != child.get(key)
        for key in ("handedness", "up_axis", "forward_axis")
    )
    if convention_changed and not explicit:
        return [
            _finding(
                detector_id="detect_implicit_coordinate_basis_change",
                code="IMPLICIT_BASIS_CHANGE",
                message="Coordinate-frame convention changes require an explicit tested conversion.",
                evidence={"parent": parent, "child": child, "explicit_conversion": False},
            )
        ]
    return []


def detect_nested_unit_double_application(candidate: Any) -> list[dict[str, Any]]:
    """Detect applying absolute units to translations and accumulated scale."""

    if not isinstance(candidate, Mapping):
        return []
    translation_converted = candidate.get("translation_converted_to_meters") is True
    accumulated_contains_unit = candidate.get("accumulated_scale_includes_unit") is True
    parent_scale = float(candidate.get("parent_unit_scale", 1.0) or 1.0)
    child_scale = float(candidate.get("child_unit_scale", 1.0) or 1.0)
    nested_non_meter = parent_scale != 1.0 and child_scale != 1.0
    if translation_converted and accumulated_contains_unit and nested_non_meter:
        return [
            _finding(
                detector_id="detect_nested_unit_double_application",
                code="NESTED_UNIT_DOUBLE_APPLICATION",
                message="Nested absolute unit conversion is applied both to translation and accumulated scale.",
                evidence={
                    "parent_unit_scale": parent_scale,
                    "child_unit_scale": child_scale,
                    "translation_converted_to_meters": True,
                    "accumulated_scale_includes_unit": True,
                },
            )
        ]
    return []


def detect_noncanonical_interchange_acceptance(candidate: Any) -> list[dict[str, Any]]:
    """Detect accepted interchange that is unsorted or contains duplicate identities."""

    if not isinstance(candidate, Mapping):
        return []
    accepted = candidate.get("accepted") is not False
    records = candidate.get("records")
    if not _is_sequence(records):
        records = candidate.get("ids") or []
    values = [str(item.get("id") if isinstance(item, Mapping) else item) for item in records]
    unsorted = values != sorted(values)
    duplicates = len(values) != len(set(values))
    set_like = candidate.get("set_like_values") or []
    set_values = [str(value) for value in set_like] if _is_sequence(set_like) else []
    set_unsorted = set_values != sorted(set_values)
    set_duplicates = len(set_values) != len(set(set_values))
    if accepted and (unsorted or duplicates or set_unsorted or set_duplicates):
        return [
            _finding(
                detector_id="detect_noncanonical_interchange_acceptance",
                code="NONCANONICAL_INTERCHANGE_ACCEPTED",
                message="Interchange acceptance must reject unsorted or duplicate record/set-like identities.",
                evidence={
                    "record_ids": values,
                    "set_like_values": set_values,
                    "unsorted": unsorted or set_unsorted,
                    "duplicates": duplicates or set_duplicates,
                },
            )
        ]
    return []


def scan_source_for_review_lessons(
    *,
    file: str,
    source: str,
) -> list[dict[str, Any]]:
    """Run conservative source-shape detectors as probable review findings.

    These checks intentionally recognize only narrow shapes learned from PR #164.
    They create review evidence, not proof or repair authority. A finding must
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

__all__ = [
    "detect_implicit_coordinate_basis_change",
    "detect_nested_unit_double_application",
    "detect_noncanonical_interchange_acceptance",
    "detect_order_dependent_digesting", "detect_truncate_before_sort",
    "scan_source_for_review_lessons",
]
