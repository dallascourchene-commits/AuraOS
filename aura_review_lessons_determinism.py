"""Determinism, coordinate, interchange, and source-shape review detectors."""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from aura_review_lessons_contracts import (
    _finding,
    _is_sequence,
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

__all__ = [
    "detect_implicit_coordinate_basis_change",
    "detect_nested_unit_double_application",
    "detect_noncanonical_interchange_acceptance",
    "detect_order_dependent_digesting",
    "detect_truncate_before_sort",
]
