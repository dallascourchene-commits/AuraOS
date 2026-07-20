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

_RESOURCE_KEYS = {
    "cpu_limit",
    "memory_limit",
    "disk_limit",
    "network_limit",
    "timeout",
    "timeout_seconds",
    "max_bytes",
    "max_files",
    "max_depth",
    "max_workers",
    "max_items",
    "max_events",
}
_SECRET_KEY_RE = re.compile(r"(?:token|secret|password|passwd|api[_-]?key|credential|private[_-]?key)", re.I)
_REDACTION_TOKEN_RE = re.compile(r"\[REDACTED:[A-Z0-9_.-]+\]")
_WORKFLOW_PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
_ACTION_REF_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@(.+)$")


def detect_authority_aliases(candidate: Any) -> list[dict[str, Any]]:
    """Detect normalized aliases of canonical authority keys."""

    findings: list[dict[str, Any]] = []
    for path, key, _value in _walk_metadata(candidate):
        normalized = _authority_key(key)
        if normalized not in _PROTECTED_AUTHORITY_NORMALIZED:
            continue
        canonical = _PROTECTED_AUTHORITY_NORMALIZED[normalized]
        if key != canonical:
            findings.append(
                _finding(
                    detector="detect_authority_aliases",
                    severity="high",
                    title="Authority metadata uses a non-canonical alias",
                    evidence={"path": path, "key": key, "canonical": canonical},
                    repair="Reject normalized authority aliases and admit only exact canonical authority keys.",
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
            continue
        if isinstance(expected, bool):
            mismatch = type(value) is not bool or value is not expected
        else:
            mismatch = value != expected
        if mismatch:
            findings.append(
                _finding(
                    detector="detect_protected_metadata_overrides",
                    severity="critical",
                    title="Protected authority metadata is contradictory",
                    evidence={"path": path, "key": key, "value": value, "expected": expected},
                    repair="Remove contradictory authority metadata and preserve the immutable no-authority envelope.",
                )
            )
    return findings


def detect_uri_alias_encoding(value: Any) -> list[dict[str, Any]]:
    """Detect encoded separators, repeated separators, and ambiguous URI aliases."""

    values = value if _is_sequence(value) else [value]
    findings: list[dict[str, Any]] = []
    for index, item in enumerate(values):
        if not isinstance(item, str):
            continue
        uri = str(item or "").strip()
        scheme, separator, remainder = uri.partition(":")
        if separator == ":" and remainder == "//" and re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*", scheme):
            continue
        lowered = uri.casefold()
        encoded_separator = "%2f" in lowered or "%5c" in lowered
        repeated_separator = "//" in urlsplit(uri).path or "\\" in uri
        decoded = unquote(uri)
        decoded_changes_separator = decoded.count("/") != uri.count("/") or decoded.count("\\") != uri.count("\\")
        if encoded_separator or repeated_separator or decoded_changes_separator:
            findings.append(
                _finding(
                    detector="detect_uri_alias_encoding",
                    severity="high",
                    title="Ambiguous encoded or repeated URI separator",
                    evidence={
                        "index": index,
                        "uri": uri,
                        "encoded_separator": encoded_separator,
                        "repeated_separator": repeated_separator,
                        "decoded_changes_separator": decoded_changes_separator,
                    },
                    repair="Decode once, reject separator changes, and fail closed on ambiguous URI aliases.",
                )
            )
    return findings


def detect_missing_scheme_checks(value: Any, *, allowed_schemes: set[str] | None = None) -> list[dict[str, Any]]:
    """Detect URI values without an explicit admitted scheme."""

    schemes = allowed_schemes or {"https"}
    values = value if _is_sequence(value) else [value]
    findings: list[dict[str, Any]] = []
    for index, item in enumerate(values):
        if not isinstance(item, str):
            continue
        parsed = urlsplit(item)
        if parsed.scheme.casefold() not in {scheme.casefold() for scheme in schemes}:
            findings.append(
                _finding(
                    detector="detect_missing_scheme_checks",
                    severity="high",
                    title="URI scheme is not explicitly admitted",
                    evidence={"index": index, "uri": item, "scheme": parsed.scheme, "allowed_schemes": sorted(schemes)},
                    repair="Parse the URI and admit only the exact expected scheme set before any transport action.",
                )
            )
    return findings


def detect_missing_resource_bounds(candidate: Any) -> list[dict[str, Any]]:
    """Detect declared unbounded resource controls and missing bounds on resource-marked packets."""

    findings: list[dict[str, Any]] = []
    for path, key, value in _walk_metadata(candidate):
        if key not in _RESOURCE_KEYS:
            continue
        if value in (None, "", 0, -1, False, "unbounded", "unlimited"):
            findings.append(
                _finding(
                    detector="detect_missing_resource_bounds",
                    severity="high",
                    title="Resource control is absent or unbounded",
                    evidence={"path": path, "key": key, "value": value},
                    repair="Provide a finite positive bound and fail closed when it is absent.",
                )
            )
    if isinstance(candidate, Mapping) and candidate.get("resource_sensitive") is True:
        present = {str(key) for key in candidate if str(key) in _RESOURCE_KEYS}
        if not present:
            findings.append(
                _finding(
                    detector="detect_missing_resource_bounds",
                    severity="high",
                    title="Resource-sensitive packet declares no finite bound",
                    evidence={"keys": sorted(str(key) for key in candidate)},
                    repair="Add finite CPU, memory, count, size, or timeout bounds before execution.",
                )
            )
    return findings


def detect_schema_drift(candidate: Any) -> list[dict[str, Any]]:
    """Detect unsupported schema versions, missing versions, and unknown-field drift."""

    findings: list[dict[str, Any]] = []
    if not isinstance(candidate, Mapping):
        return findings
    supported = candidate.get("supported_schema_versions")
    version = candidate.get("schema_version")
    schema_marked = bool(supported is not None or version is not None or candidate.get("schema_required") is True)
    if not schema_marked:
        return findings
    if version in (None, ""):
        findings.append(
            _finding(
                detector="detect_schema_drift",
                severity="high",
                title="Schema-marked packet omits schema_version",
                evidence={"keys": sorted(str(key) for key in candidate)},
                repair="Require an exact schema_version and reject unsupported or missing versions.",
            )
        )
    elif _is_sequence(supported) and version not in supported:
        findings.append(
            _finding(
                detector="detect_schema_drift",
                severity="critical",
                title="Packet uses an unsupported schema version",
                evidence={"schema_version": version, "supported": list(supported)},
                repair="Fail closed on unsupported schema versions before deserialization or dispatch.",
            )
        )
    allowed = candidate.get("allowed_fields")
    payload = candidate.get("payload")
    if _is_sequence(allowed) and isinstance(payload, Mapping):
        unknown = sorted(str(key) for key in payload if str(key) not in {str(item) for item in allowed})
        if unknown:
            findings.append(
                _finding(
                    detector="detect_schema_drift",
                    severity="high",
                    title="Payload contains unknown fields outside the declared schema",
                    evidence={"unknown_fields": unknown},
                    repair="Reject unknown fields or update the declared schema deliberately with compatibility tests.",
                )
            )
    return findings


def detect_unpinned_workflow_dependencies(candidate: Any) -> list[dict[str, Any]]:
    """Detect mutable GitHub Actions refs and unbounded package install commands."""

    findings: list[dict[str, Any]] = []
    uses_values: list[str] = []
    run_values: list[str] = []
    if isinstance(candidate, str):
        text = candidate
        uses_values.extend(re.findall(r"(?m)^\s*-?\s*uses:\s*([^\s#]+)", text))
        run_values.extend(re.findall(r"(?m)^\s*run:\s*(.+)$", text))
    elif isinstance(candidate, Mapping):
        for path, key, value in _walk_metadata(candidate):
            if key == "uses" and isinstance(value, str):
                uses_values.append(value)
            if key == "run" and isinstance(value, str):
                run_values.append(value)
    for value in uses_values:
        if value.startswith("./") or value.startswith("docker://"):
            continue
        if not _WORKFLOW_PIN_RE.fullmatch(value):
            ref_match = _ACTION_REF_RE.fullmatch(value)
            findings.append(
                _finding(
                    detector="detect_unpinned_workflow_dependencies",
                    severity="high",
                    title="Workflow action dependency is not pinned to a full commit SHA",
                    evidence={"uses": value, "ref": ref_match.group(1) if ref_match else ""},
                    repair="Pin third-party workflow actions to an exact 40-character commit SHA.",
                )
            )
    for value in run_values:
        lowered = value.casefold()
        if ("pip install" in lowered or "npm install" in lowered or "npm i " in lowered) and "--require-hashes" not in lowered:
            findings.append(
                _finding(
                    detector="detect_unpinned_workflow_dependencies",
                    severity="high",
                    title="Workflow installs dependencies without a lock or hash requirement",
                    evidence={"run": value[:500]},
                    repair="Use a locked dependency file with integrity hashes or an equivalent immutable package pin.",
                )
            )
    return findings


def detect_secret_persistence(candidate: Any) -> list[dict[str, Any]]:
    """Detect secret-like fields or token-shaped values entering durable payloads."""

    findings: list[dict[str, Any]] = []
    if not isinstance(candidate, Mapping):
        return findings
    durable = candidate.get("persist") is True or candidate.get("durable") is True or candidate.get("archive") is True
    payload = candidate.get("payload", candidate)
    if not durable:
        return findings
    for path, key, value in _walk_metadata(payload):
        key_secret = bool(_SECRET_KEY_RE.search(key))
        value_text = str(value or "")
        token_secret = bool(
            re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", value_text)
            or re.search(r"(?:Bearer|Basic)\s+[A-Za-z0-9+/_.=-]{12,}", value_text, re.I)
        )
        if key_secret or token_secret:
            findings.append(
                _finding(
                    detector="detect_secret_persistence",
                    severity="critical",
                    title="Secret-like content enters a durable payload",
                    evidence={"path": path, "key": key, "redaction_marker_present": bool(_REDACTION_TOKEN_RE.search(value_text))},
                    repair="Redact or omit the secret before persistence and retain only a stable non-secret reference.",
                )
            )
    return findings


def detect_path_alias_collisions(value: Any) -> list[dict[str, Any]]:
    """Detect multiple raw paths that normalize to the same repository-relative target."""

    values = value if _is_sequence(value) else [value]
    normalized: dict[str, list[str]] = {}
    findings: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, str):
            continue
        try:
            safe = _safe_repo_path(item)
        except ReviewLessonError as exc:
            findings.append(
                _finding(
                    detector="detect_path_alias_collisions",
                    severity="high",
                    title="Path is not a safe repository-relative path",
                    evidence={"path": item, "error": str(exc)},
                    repair="Reject absolute, traversal, or malformed repository paths before any filesystem access.",
                )
            )
            continue
        canonical = PurePosixPath(safe).as_posix().casefold()
        normalized.setdefault(canonical, []).append(item)
    for canonical, raw_values in sorted(normalized.items()):
        if len(set(raw_values)) > 1:
            findings.append(
                _finding(
                    detector="detect_path_alias_collisions",
                    severity="high",
                    title="Distinct raw paths collapse to the same canonical target",
                    evidence={"canonical": canonical, "paths": sorted(set(raw_values))},
                    repair="Canonicalize once and reject duplicate aliases before reading, writing, or patching files.",
                )
            )
    return findings


__all__ = [
    "detect_authority_aliases",
    "detect_missing_resource_bounds",
    "detect_missing_scheme_checks",
    "detect_path_alias_collisions",
    "detect_protected_metadata_overrides",
    "detect_schema_drift",
    "detect_secret_persistence",
    "detect_unpinned_workflow_dependencies",
    "detect_uri_alias_encoding",
]
