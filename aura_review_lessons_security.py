"""Security, boundedness, schema, workflow, and evidence review detectors."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
import re
from typing import Any
from urllib.parse import unquote, urlsplit

from aura_review_lessons_contracts import (
    _CANONICAL_AUTHORITY_KEYS,
    _PROTECTED_AUTHORITY_EXPECTED,
    _PROTECTED_AUTHORITY_NORMALIZED,
    ReviewLessonError,
    _authority_key,
    _finding,
    _is_sequence,
    _safe_repo_path,
    _walk_metadata,
)


def detect_authority_aliases(candidate: Any) -> list[dict[str, Any]]:
    """Detect separator/case/camel aliases for protected authority keys."""

    findings: list[dict[str, Any]] = []
    for path, key, value in _walk_metadata(candidate):
        normalized = _authority_key(key)
        canonical = _PROTECTED_AUTHORITY_NORMALIZED.get(normalized)
        if canonical is None or key == canonical:
            continue
        findings.append(
            _finding(
                detector_id="detect_authority_aliases",
                code="AUTHORITY_ALIAS",
                message=(
                    f"Metadata key {key!r} aliases protected authority key "
                    f"{canonical!r}; aliases must fail closed."
                ),
                evidence={"metadata_path": path, "key": key, "canonical_key": canonical, "value": value},
                confidence=1.0,
            )
        )
    return findings


def _is_spatial_no_authority_envelope(candidate: Any) -> bool:
    return bool(
        isinstance(candidate, Mapping)
        and candidate.get("projection_only") is True
        and candidate.get("renderer_authority") is False
        and candidate.get("execution_authority") is False
        and candidate.get("patch_authority") is False
        and candidate.get("production_mutation") is False
    )


def detect_protected_metadata_overrides(candidate: Any) -> list[dict[str, Any]]:
    """Detect affirmative or contradictory canonical authority metadata."""

    findings: list[dict[str, Any]] = []
    spatial_no_authority = _is_spatial_no_authority_envelope(candidate)
    for path, key, value in _walk_metadata(candidate):
        if key not in _CANONICAL_AUTHORITY_KEYS:
            continue
        expected = _PROTECTED_AUTHORITY_EXPECTED[key]
        if key == "patch_authority" and path == "$.patch_authority" and spatial_no_authority:
            continue
        if value == "<dynamic>":
            # The source scanner resolves known authority constants before this
            # detector. Unknown dynamic values are not promoted to a confirmed
            # override merely because static literal evaluation was impossible.
            continue
        if type(value) is type(expected) and value == expected:
            continue
        findings.append(
            _finding(
                detector_id="detect_protected_metadata_overrides",
                code="PROTECTED_AUTHORITY_OVERRIDE",
                message=(
                    f"Protected authority field {key!r} must remain exactly "
                    f"{expected!r}."
                ),
                evidence={
                    "metadata_path": path,
                    "key": key,
                    "value": value,
                    "expected": expected,
                },
                confidence=1.0,
            )
        )
    return findings


def detect_count_without_byte_budget(candidate: Any) -> list[dict[str, Any]]:
    """Detect attacker-controlled evidence that has count caps but no byte caps."""

    if not isinstance(candidate, Mapping):
        return []
    count_keys = {
        key
        for key in candidate
        if any(term in str(key).casefold() for term in ("count", "items", "records", "nodes", "edges"))
        and "max" in str(key).casefold()
    }
    byte_keys = {
        key
        for key in candidate
        if any(term in str(key).casefold() for term in ("byte", "bytes", "size"))
        and "max" in str(key).casefold()
    }
    attacker_controlled = candidate.get("attacker_controlled", True) is not False
    if count_keys and not byte_keys and attacker_controlled:
        return [
            _finding(
                detector_id="detect_count_without_byte_budget",
                code="COUNT_ONLY_BOUND",
                message="Retained attacker-controlled evidence has a count cap but no byte cap.",
                evidence={"count_keys": sorted(map(str, count_keys)), "byte_keys": []},
            )
        ]
    return []


def detect_noncanonical_source_path(candidate: Any) -> list[dict[str, Any]]:
    """Detect traversal, absolute, dot-segment, slash-alias, and control paths."""

    values: list[Any]
    if isinstance(candidate, Mapping):
        raw = (
            candidate.get("paths")
            or candidate.get("source_refs")
            or candidate.get("path")
            or candidate.get("file")
            or []
        )
        values = list(raw) if _is_sequence(raw) else [raw]
    elif _is_sequence(candidate):
        values = list(candidate)
    else:
        values = [candidate]
    findings: list[dict[str, Any]] = []
    for value in values:
        text = str(value or "")
        if text.startswith("source:"):
            text = text[len("source:") :].split("#", 1)[0]
        try:
            _safe_repo_path(text)
        except ReviewLessonError as exc:
            findings.append(
                _finding(
                    detector_id="detect_noncanonical_source_path",
                    code="NONCANONICAL_SOURCE_PATH",
                    message=str(exc),
                    path=text,
                    evidence={"supplied_path": text},
                )
            )
    return findings


def detect_uri_alias_encoding(candidate: Any) -> list[dict[str, Any]]:
    """Detect encoded separators, repeated separators, credentials, query/fragment."""

    values: list[Any]
    if isinstance(candidate, Mapping):
        raw = candidate.get("uris") or candidate.get("uri") or []
        values = list(raw) if _is_sequence(raw) else [raw]
    elif _is_sequence(candidate):
        values = list(candidate)
    else:
        values = [candidate]
    findings: list[dict[str, Any]] = []
    for value in values:
        uri = str(value or "").strip()
        scheme, separator, remainder = uri.partition(":")
        if separator == ":" and remainder == "//" and re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*", scheme):
            continue
        lowered = uri.casefold()
        decoded = unquote(uri)
        unsafe = False
        reasons: list[str] = []
        if re.search(r"%(?:2f|5c)", lowered):
            unsafe = True
            reasons.append("encoded_separator")
        if decoded != uri:
            # Reject only decode operations that introduce or change path
            # separators. Benign encodings such as ``%20`` remain permitted.
            if decoded.count("/") != uri.count("/") or decoded.count("\\") != uri.count("\\"):
                unsafe = True
                reasons.append("decoded_separator_change")
        parsed = urlsplit(uri)
        if parsed.username is not None or parsed.password is not None:
            unsafe = True
            reasons.append("credentials")
        if parsed.query:
            unsafe = True
            reasons.append("query")
        if parsed.fragment:
            unsafe = True
            reasons.append("fragment")
        path = parsed.path or uri
        if "\\" in path:
            unsafe = True
            reasons.append("backslash")
        if "//" in path:
            unsafe = True
            reasons.append("repeated_separator")
        if any(part in {".", ".."} for part in PurePosixPath(path).parts):
            unsafe = True
            reasons.append("dot_segment")
        if unsafe:
            findings.append(
                _finding(
                    detector_id="detect_uri_alias_encoding",
                    code="NONCANONICAL_URI",
                    message="Asset/source URI contains a noncanonical alias.",
                    evidence={"uri": uri, "reasons": sorted(set(reasons))},
                )
            )
    return findings


def detect_schema_runtime_drift(candidate: Any) -> list[dict[str, Any]]:
    """Detect mismatch between schema acceptance and runtime semantic acceptance."""

    if not isinstance(candidate, Mapping):
        return []
    schema_accepts = candidate.get("schema_accepts")
    runtime_accepts = candidate.get("runtime_accepts")
    if isinstance(schema_accepts, bool) and isinstance(runtime_accepts, bool):
        if schema_accepts != runtime_accepts:
            return [
                _finding(
                    detector_id="detect_schema_runtime_drift",
                    code="SCHEMA_RUNTIME_DRIFT",
                    message="Schema and runtime accept different payload sets.",
                    evidence={
                        "schema_accepts": schema_accepts,
                        "runtime_accepts": runtime_accepts,
                        "invariant": candidate.get("invariant", ""),
                    },
                )
            ]
    return []


def detect_unwired_regression(candidate: Any) -> list[dict[str, Any]]:
    """Detect regression tests omitted from compile, lint, or pytest workflow gates."""

    if not isinstance(candidate, Mapping):
        return []
    test_path = str(candidate.get("test_path") or "").strip()
    workflow = str(candidate.get("workflow") or "")
    required_stages = tuple(candidate.get("required_stages") or ("py_compile", "ruff", "pytest"))
    missing = [
        stage
        for stage in required_stages
        if stage not in workflow or (test_path and test_path not in _workflow_stage_text(workflow, stage))
    ]
    if test_path and missing:
        return [
            _finding(
                detector_id="detect_unwired_regression",
                code="UNWIRED_REGRESSION",
                message=f"Regression {test_path} is missing from workflow stages: {', '.join(missing)}.",
                path=test_path,
                evidence={"missing_stages": missing},
            )
        ]
    return []


def _workflow_stage_text(workflow: str, stage: str) -> str:
    match = re.search(
        rf"(?ms)^\s*[-#]?\s*.*{re.escape(stage)}.*?(?=^\s*[-#]?\s*(?:python|ruff|pytest|name:)|\Z)",
        workflow,
    )
    return match.group(0) if match else ""


def detect_stale_evidence_claim(candidate: Any) -> list[dict[str, Any]]:
    """Detect claims that upgrade configured/historical evidence into current passes."""

    if not isinstance(candidate, Mapping):
        return []
    claim = str(candidate.get("claim") or candidate.get("claim_status") or "").casefold()
    evidence_status = str(candidate.get("evidence_status") or "").casefold()
    evidence_head = str(candidate.get("evidence_head") or "")
    current_head = str(candidate.get("current_head") or "")
    bad_upgrade = (
        any(term in claim for term in ("passed", "verified", "green"))
        and evidence_status in {"configured", "not_executed", "queued", "in_progress", "historical"}
    )
    head_mismatch = bool(
        evidence_head
        and current_head
        and evidence_head != current_head
        and any(term in claim for term in ("current", "passed", "verified", "green"))
    )
    if bad_upgrade or head_mismatch:
        return [
            _finding(
                detector_id="detect_stale_evidence_claim",
                code="STALE_EVIDENCE_CLAIM",
                message="Evidence claim is stronger or fresher than its bound execution evidence.",
                evidence={
                    "claim": claim,
                    "evidence_status": evidence_status,
                    "evidence_head": evidence_head,
                    "current_head": current_head,
                },
            )
        ]
    return []


__all__ = [
    "detect_authority_aliases",
    "detect_count_without_byte_budget",
    "detect_noncanonical_source_path",
    "detect_protected_metadata_overrides",
    "detect_schema_runtime_drift",
    "detect_stale_evidence_claim",
    "detect_unwired_regression",
    "detect_uri_alias_encoding",
]
