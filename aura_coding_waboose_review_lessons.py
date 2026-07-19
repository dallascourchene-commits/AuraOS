"""Typed PR-review lessons, detectors, and Crucible replay for Coding Waboose.

External reviewers are teacher signals, never patch authority.  This module
normalizes CodeRabbit, Codex, and manual review evidence into bounded typed
findings; binds durable lessons to explicit invariants, repair patterns, and
required regressions; and exposes deterministic detectors that Coding Waboose,
the Capability Connectome, Agent Bridge adapters, and Crucible replays can use.

The module is intentionally stdlib-only.  It never edits source, commits,
pushes, opens pull requests, merges, or mutates production state.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any
from urllib.parse import unquote, urlsplit

REVIEW_LESSON_VERSION = "AURA_CODING_WABOOSE_REVIEW_LESSONS_V1"
REVIEW_FINDING_VERSION = "AURA_EXTERNAL_REVIEW_FINDING_V1"
CRUCIBLE_REPLAY_VERSION = "AURA_REVIEW_LESSON_CRUCIBLE_REPLAY_V1"
REGISTRY_VERSION = "AURA_REVIEW_LESSON_REGISTRY_V1"

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parent
    / ".aura"
    / "review_lessons"
    / "pr164_spatial_review_lessons.json"
)
DEFAULT_LEARNING_ROOT = Path.home() / ".aura" / "coding_waboose_review_lessons"

_MAX_REVIEW_PAYLOAD_BYTES = 1_048_576
_MAX_COMMENT_BYTES = 16_384
_MAX_STORED_FINDINGS = 500
_MAX_PATH_BYTES = 1024
_MAX_SCENARIO_BYTES = 262_144

_PROTECTED_AUTHORITY_KEYS = (
    "approval",
    "authorization",
    "automatic_commit",
    "automatic_fix",
    "automatic_merge",
    "automatic_pull_request",
    "automatic_push",
    "execution_authority",
    "merge",
    "patch_authority",
    "production_mutation",
    "promotion",
    "renderer_authority",
    "spatial_patch_authority",
    "vsa_patch_authority",
)
_PROTECTED_AUTHORITY_NORMALIZED = {
    re.sub(r"[^a-z0-9]+", "", key.lower()): key for key in _PROTECTED_AUTHORITY_KEYS
}
_CANONICAL_AUTHORITY_KEYS = set(_PROTECTED_AUTHORITY_KEYS)

_REVIEWER_ALIASES = {
    "coderabbit": "CodeRabbit",
    "coderabbitai": "CodeRabbit",
    "chatgpt-codex-connector": "Codex",
    "codex": "Codex",
    "github-copilot": "GitHub Copilot",
}

_DETECTOR_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "detect_authority_aliases",
        (
            "authority alias",
            "automaticmerge",
            "automatic merge",
            "patchauthority",
            "patch authority",
            "camel-case authority",
            "mixed-case authority",
            "separator aliases",
        ),
    ),
    (
        "detect_protected_metadata_overrides",
        ("metadata from overriding", "overriding authority", "protected false", "authority claim"),
    ),
    (
        "detect_order_dependent_digesting",
        ("input ordering", "order-dependent", "link identities", "digest solely from input order"),
    ),
    (
        "detect_truncate_before_sort",
        ("before applying the projection cap", "before truncation", "truncate before sort"),
    ),
    (
        "detect_count_without_byte_budget",
        ("byte cap", "byte limit", "arbitrarily large", "count-only cap", "unbounded scene payload"),
    ),
    (
        "detect_noncanonical_source_path",
        ("source path", "source anchor", "traversal", "absolute source", "non-canonical path"),
    ),
    (
        "detect_uri_alias_encoding",
        ("encoded separator", "repeated path separator", "asset uri", "uri path separator"),
    ),
    (
        "detect_schema_runtime_drift",
        ("schema/code drift", "schema/runtime", "published schema", "schema accepts"),
    ),
    (
        "detect_unwired_regression",
        ("workflow omits", "never executed by this workflow", "absent from the preceding compile"),
    ),
    (
        "detect_stale_evidence_claim",
        ("stale evidence", "historical pass", "configured", "not executed"),
    ),
    (
        "detect_implicit_coordinate_basis_change",
        ("handedness", "up axis", "frame convention changes", "basis change"),
    ),
    (
        "detect_nested_unit_double_application",
        ("nested non-meter", "applied a second time", "double application", "relative to the parent"),
    ),
    (
        "detect_noncanonical_interchange_acceptance",
        (
            "canonical ordering",
            "noncanonical serialized",
            "reorder otherwise identical",
            "duplicate identities",
            "distinct accepted scene_digest",
        ),
    ),
)


class ReviewLessonError(ValueError):
    """Raised when a review lesson or reviewer payload violates the contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    )


def _canonical_bytes(value: Any) -> bytes:
    return _canonical_json(value).encode("utf-8")


def _digest(value: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_canonical_bytes(value), digest_size=size).hexdigest()


def _bounded_json(value: Any, *, maximum: int, label: str) -> bytes:
    payload = _canonical_bytes(value)
    if len(payload) > maximum:
        raise ReviewLessonError(f"{label} exceeds {maximum} canonical bytes")
    return payload


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


def _authority_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _safe_text(value: Any, *, maximum_bytes: int = _MAX_COMMENT_BYTES) -> str:
    text = str(value or "").strip()
    encoded = text.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return text
    clipped = encoded[:maximum_bytes]
    while clipped:
        try:
            return clipped.decode("utf-8")
        except UnicodeDecodeError as exc:
            clipped = clipped[: exc.start]
    return ""


def _safe_repo_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text.encode("utf-8")) > _MAX_PATH_BYTES:
        raise ReviewLessonError("repository path exceeds byte limit")
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise ReviewLessonError("repository path contains control characters")
    if "\\" in text or "//" in text:
        raise ReviewLessonError("repository path must be canonical POSIX form")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReviewLessonError("repository path must be canonical and relative")
    if path.as_posix() != text:
        raise ReviewLessonError("repository path is not canonical")
    return text


def _reviewer_name(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("login") or value.get("name") or ""
    text = str(value or "").strip()
    lowered = text.casefold()
    for alias, canonical in _REVIEWER_ALIASES.items():
        if alias in lowered:
            return canonical
    return text or "Unknown"


def _strip_markdown(value: Any) -> str:
    text = _safe_text(value)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<details>.*?</details>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"!\[[^]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_>#]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_from_body(body: str) -> str:
    cleaned = _strip_markdown(body)
    cleaned = re.sub(r"!\s*P[0-9]\s*Badge", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Useful\?.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "External review finding"
    sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0]
    return sentence[:240].strip()


def _detector_from_text(value: str) -> str:
    lowered = value.casefold()
    for detector_id, terms in _DETECTOR_KEYWORDS:
        if any(term in lowered for term in terms):
            return detector_id
    return "detect_unclassified_review_pattern"


def _disposition(
    *,
    reviewed_head: str,
    current_head: str,
    resolved: bool,
    outdated: bool,
) -> str:
    if outdated:
        return "outdated"
    if resolved:
        return "resolved"
    if current_head not in {"", "UNAVAILABLE"} and reviewed_head and reviewed_head != current_head:
        return "historical"
    return "current_head"


def _finding(
    *,
    detector_id: str,
    code: str,
    message: str,
    path: str = "",
    line_start: int = 0,
    line_end: int = 0,
    evidence: Any = None,
    confidence: float = 1.0,
) -> dict[str, Any]:
    payload = {
        "version": REVIEW_FINDING_VERSION,
        "detector_id": detector_id,
        "code": code,
        "message": message,
        "path": path,
        "line_start": int(line_start),
        "line_end": int(line_end),
        "evidence": evidence,
        "confidence": round(max(0.0, min(1.0, float(confidence))), 6),
        "source_grounded": False,
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
    payload["finding_id"] = "RVF-" + _digest(payload, size=12)
    return payload


def _walk_metadata(
    value: Any,
    *,
    prefix: str = "$",
    seen: set[int] | None = None,
) -> list[tuple[str, str, Any]]:
    if seen is None:
        seen = set()
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in seen:
            return []
        seen.add(identity)
        result: list[tuple[str, str, Any]] = []
        for key, item in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}"
            result.append((path, key_text, item))
            result.extend(_walk_metadata(item, prefix=path, seen=seen))
        return result
    if _is_sequence(value):
        identity = id(value)
        if identity in seen:
            return []
        seen.add(identity)
        result = []
        for index, item in enumerate(value):
            result.extend(_walk_metadata(item, prefix=f"{prefix}[{index}]", seen=seen))
        return result
    return []


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


def detect_protected_metadata_overrides(candidate: Any) -> list[dict[str, Any]]:
    """Detect affirmative or contradictory canonical authority metadata."""

    findings: list[dict[str, Any]] = []
    for path, key, value in _walk_metadata(candidate):
        if key not in _CANONICAL_AUTHORITY_KEYS:
            continue
        if value is False:
            continue
        findings.append(
            _finding(
                detector_id="detect_protected_metadata_overrides",
                code="PROTECTED_AUTHORITY_OVERRIDE",
                message=f"Protected authority field {key!r} must remain exactly false.",
                evidence={"metadata_path": path, "key": key, "value": value},
                confidence=1.0,
            )
        )
    return findings


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


DETECTORS = {
    function.__name__: function
    for function in (
        detect_authority_aliases,
        detect_protected_metadata_overrides,
        detect_order_dependent_digesting,
        detect_truncate_before_sort,
        detect_count_without_byte_budget,
        detect_noncanonical_source_path,
        detect_uri_alias_encoding,
        detect_schema_runtime_drift,
        detect_unwired_regression,
        detect_stale_evidence_claim,
        detect_implicit_coordinate_basis_change,
        detect_nested_unit_double_application,
        detect_noncanonical_interchange_acceptance,
    )
}


@dataclass(frozen=True)
class NormalizedReviewFinding:
    finding_id: str
    reviewer: str
    review_kind: str
    repository_head: str
    current_head: str
    pr_number: int
    comment_id: str
    path: str
    line_start: int
    line_end: int
    title: str
    message: str
    severity: str
    category: str
    disposition: str
    resolved: bool
    outdated: bool
    duplicate_of: str
    detector_id: str
    invariant: str
    source_grounded: bool
    confidence: float
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.update(
            {
                "version": REVIEW_FINDING_VERSION,
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
        )
        return result


def normalize_external_review(
    payload: Mapping[str, Any],
    *,
    current_head: str = "",
) -> dict[str, Any]:
    """Normalize top-level comments, inline threads, and review submissions.

    Normalization does not claim that source was verified.  It records whether
    evidence is current, historical, resolved, outdated, or duplicate.
    """

    if not isinstance(payload, Mapping):
        raise ReviewLessonError("review payload must be an object")
    _bounded_json(payload, maximum=_MAX_REVIEW_PAYLOAD_BYTES, label="review payload")
    reviewed_head = str(payload.get("head_sha") or payload.get("commit_sha") or "")
    current = current_head or str(payload.get("current_head") or "") or reviewed_head
    pr_number = int(payload.get("pr_number") or payload.get("pull_request_number") or 0)
    raw: list[dict[str, Any]] = []

    comments = payload.get("comments") or payload.get("issue_comments") or []
    if _is_sequence(comments):
        for comment in comments[:_MAX_STORED_FINDINGS]:
            if isinstance(comment, Mapping):
                try:
                    raw.append(
                        _raw_review_row(
                            comment,
                            review_kind="top_level_pr_comment",
                            reviewed_head=reviewed_head,
                            current_head=current,
                            pr_number=pr_number,
                        )
                    )
                except (ReviewLessonError, ValueError):
                    continue

    threads = payload.get("review_threads") or payload.get("threads") or []
    if _is_sequence(threads):
        for thread in threads[:_MAX_STORED_FINDINGS]:
            if not isinstance(thread, Mapping):
                continue
            thread_comments = thread.get("comments") or []
            if not _is_sequence(thread_comments):
                continue
            for comment in thread_comments:
                if not isinstance(comment, Mapping):
                    continue
                merged = dict(comment)
                merged.setdefault("path", thread.get("path"))
                merged.setdefault("line", thread.get("line") or thread.get("original_line"))
                merged.setdefault("start_line", thread.get("start_line") or thread.get("original_start_line"))
                merged["is_resolved"] = bool(thread.get("is_resolved"))
                merged["is_outdated"] = bool(thread.get("is_outdated"))
                try:
                    raw.append(
                        _raw_review_row(
                            merged,
                            review_kind="inline_review_thread",
                            reviewed_head=reviewed_head,
                            current_head=current,
                            pr_number=pr_number,
                        )
                    )
                except (ReviewLessonError, ValueError):
                    continue

    reviews = payload.get("reviews") or payload.get("review_submissions") or []
    if _is_sequence(reviews):
        for review in reviews[:_MAX_STORED_FINDINGS]:
            if isinstance(review, Mapping):
                try:
                    raw.append(
                        _raw_review_row(
                            review,
                            review_kind="review_submission",
                            reviewed_head=reviewed_head,
                            current_head=current,
                            pr_number=pr_number,
                        )
                    )
                except (ReviewLessonError, ValueError):
                    continue

    if not raw and _is_sequence(payload.get("findings")):
        for finding in payload.get("findings") or []:
            if isinstance(finding, Mapping):
                try:
                    raw.append(
                        _raw_review_row(
                            finding,
                            review_kind=str(finding.get("review_kind") or "normalized_finding"),
                            reviewed_head=reviewed_head,
                            current_head=current,
                            pr_number=pr_number,
                        )
                    )
                except (ReviewLessonError, ValueError):
                    continue

    dedupe: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    for row in raw[:_MAX_STORED_FINDINGS]:
        identity = _digest(
            {
                "reviewer": row["reviewer"],
                "path": row["path"],
                "line": [row["line_start"], row["line_end"]],
                "message": row["message"].casefold(),
            },
            size=12,
        )
        duplicate_of = dedupe.get(identity, "")
        if not duplicate_of:
            dedupe[identity] = row["finding_id"]
        row["duplicate_of"] = duplicate_of
        if duplicate_of:
            row["disposition"] = "duplicate"
        normalized.append(row)

    packet = {
        "version": REVIEW_LESSON_VERSION,
        "status": "normalized",
        "repository_head": reviewed_head,
        "current_head": current,
        "pr_number": pr_number,
        "finding_count": len(normalized),
        "findings": normalized,
        "truth_boundary": "typed_external_review_evidence",
        "source_grounding_required_before_learning": True,
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
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


def _raw_review_row(
    value: Mapping[str, Any],
    *,
    review_kind: str,
    reviewed_head: str,
    current_head: str,
    pr_number: int,
) -> dict[str, Any]:
    body = _safe_text(value.get("body") or value.get("message") or value.get("title") or "")
    reviewer = _reviewer_name(value.get("author") or value.get("user") or value.get("source"))
    path = _safe_repo_path(value.get("path") or value.get("file") or "")
    line_start = int(value.get("start_line") or value.get("line_start") or value.get("line") or 0)
    line_end = int(value.get("line_end") or value.get("line") or line_start)
    if line_start < 0 or line_end < line_start:
        raise ReviewLessonError("review line range is invalid")
    resolved = bool(value.get("is_resolved") or value.get("resolved"))
    outdated = bool(value.get("is_outdated") or value.get("outdated"))
    message = _strip_markdown(body)
    title = _safe_text(value.get("title") or _title_from_body(body), maximum_bytes=1024)
    detector_id = str(value.get("detector_id") or _detector_from_text(f"{title} {message}"))
    invariant = str(value.get("invariant") or "")
    confidence = float(value.get("confidence") or (0.98 if reviewer in {"CodeRabbit", "Codex"} else 0.75))
    provenance = {
        "comment_id": str(value.get("id") or value.get("comment_id") or ""),
        "url": str(value.get("url") or ""),
        "created_at": str(value.get("created_at") or ""),
        "updated_at": str(value.get("updated_at") or ""),
    }
    identity = {
        "reviewer": reviewer,
        "kind": review_kind,
        "head": reviewed_head,
        "path": path,
        "line": [line_start, line_end],
        "message": message,
        "comment_id": provenance["comment_id"],
    }
    finding = NormalizedReviewFinding(
        finding_id="XRF-" + _digest(identity, size=12),
        reviewer=reviewer,
        review_kind=review_kind,
        repository_head=reviewed_head,
        current_head=current_head,
        pr_number=pr_number,
        comment_id=provenance["comment_id"],
        path=path,
        line_start=line_start,
        line_end=line_end,
        title=title,
        message=message,
        severity=str(value.get("severity") or _severity_from_body(body)).lower(),
        category=str(value.get("category") or "correctness").lower(),
        disposition=_disposition(
            reviewed_head=reviewed_head,
            current_head=current_head,
            resolved=resolved,
            outdated=outdated,
        ),
        resolved=resolved,
        outdated=outdated,
        duplicate_of="",
        detector_id=detector_id,
        invariant=invariant,
        source_grounded=bool(value.get("source_grounded")),
        confidence=max(0.0, min(1.0, confidence)),
        provenance=provenance,
    )
    return finding.to_dict()


def _severity_from_body(body: str) -> str:
    lowered = body.casefold()
    if "p0" in lowered or "critical" in lowered:
        return "critical"
    if "p1" in lowered or "major" in lowered:
        return "high"
    if "p2" in lowered:
        return "medium"
    return "low"


def validate_review_lesson_registry(value: Mapping[str, Any]) -> dict[str, Any]:
    """Runtime semantic validation for the strict lesson registry."""

    if not isinstance(value, Mapping):
        raise ReviewLessonError("review lesson registry must be an object")
    _bounded_json(value, maximum=_MAX_REVIEW_PAYLOAD_BYTES, label="review lesson registry")
    if value.get("version") != REGISTRY_VERSION:
        raise ReviewLessonError("unsupported review lesson registry version")
    lessons = value.get("lessons")
    scenarios = value.get("scenarios")
    if not _is_sequence(lessons) or not _is_sequence(scenarios):
        raise ReviewLessonError("registry lessons and scenarios must be arrays")
    lesson_ids: set[str] = set()
    detector_ids: set[str] = set()
    canonical_lessons: list[dict[str, Any]] = []
    for raw in lessons:
        if not isinstance(raw, Mapping):
            raise ReviewLessonError("each lesson must be an object")
        lesson = dict(raw)
        lesson_id = str(lesson.get("lesson_id") or "")
        detector_id = str(lesson.get("detector_id") or "")
        if not lesson_id or lesson_id in lesson_ids:
            raise ReviewLessonError("lesson IDs must be non-empty and unique")
        if detector_id not in DETECTORS:
            raise ReviewLessonError(f"unknown detector_id: {detector_id}")
        lesson_ids.add(lesson_id)
        detector_ids.add(detector_id)
        for key in (
            "trigger",
            "invariant",
            "repair_pattern",
            "required_regression",
            "generalization_scope",
            "false_positive_guard",
            "provenance",
        ):
            if key not in lesson:
                raise ReviewLessonError(f"lesson {lesson_id} missing {key}")
        confidence = float(lesson.get("confidence") or 0.0)
        if not 0.0 <= confidence <= 1.0:
            raise ReviewLessonError(f"lesson {lesson_id} confidence is outside [0,1]")
        canonical_lessons.append(lesson)
    canonical_scenarios: list[dict[str, Any]] = []
    scenario_ids: set[str] = set()
    for raw in scenarios:
        if not isinstance(raw, Mapping):
            raise ReviewLessonError("each scenario must be an object")
        scenario = dict(raw)
        scenario_id = str(scenario.get("scenario_id") or "")
        detector_id = str(scenario.get("detector_id") or "")
        if not scenario_id or scenario_id in scenario_ids:
            raise ReviewLessonError("scenario IDs must be non-empty and unique")
        if detector_id not in detector_ids:
            raise ReviewLessonError(f"scenario detector has no lesson: {detector_id}")
        _bounded_json(scenario, maximum=_MAX_SCENARIO_BYTES, label=f"scenario {scenario_id}")
        scenario_ids.add(scenario_id)
        canonical_scenarios.append(scenario)
    result = dict(value)
    result["lessons"] = sorted(canonical_lessons, key=lambda item: str(item["lesson_id"]))
    result["scenarios"] = sorted(canonical_scenarios, key=lambda item: str(item["scenario_id"]))
    supplied_digest = str(result.pop("registry_digest", "") or "")
    canonical_digest = _digest(result, size=20)
    if supplied_digest and supplied_digest != canonical_digest:
        raise ReviewLessonError("review lesson registry digest mismatch")
    result["registry_digest"] = canonical_digest
    return result


def load_review_lesson_registry(path: str | Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_review_lesson_registry(value)


def run_review_detector(detector_id: str, candidate: Any) -> dict[str, Any]:
    detector = DETECTORS.get(detector_id)
    if detector is None:
        raise ReviewLessonError(f"unknown review detector: {detector_id}")
    _bounded_json(candidate, maximum=_MAX_SCENARIO_BYTES, label="review detector candidate")
    findings = detector(candidate)
    packet = {
        "version": REVIEW_LESSON_VERSION,
        "detector_id": detector_id,
        "finding_count": len(findings),
        "findings": findings,
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
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


def run_crucible_replay(
    registry: Mapping[str, Any] | str | Path = DEFAULT_REGISTRY_PATH,
    *,
    detector_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Replay typed adversarial lessons and emit proof-oriented receipts."""

    if isinstance(registry, (str, Path)):
        loaded = load_review_lesson_registry(registry)
    else:
        loaded = validate_review_lesson_registry(registry)
    selected = {str(value) for value in detector_ids if str(value)}
    lessons = {str(item["detector_id"]): dict(item) for item in loaded["lessons"]}
    receipts: list[dict[str, Any]] = []
    for scenario in loaded["scenarios"]:
        detector_id = str(scenario["detector_id"])
        if selected and detector_id not in selected:
            continue
        lesson = lessons[detector_id]
        result = run_review_detector(detector_id, scenario.get("candidate"))
        expected_code = str(scenario.get("expected_finding_code") or "")
        matching = [
            finding
            for finding in result["findings"]
            if not expected_code or finding.get("code") == expected_code
        ]
        receipt = {
            "version": CRUCIBLE_REPLAY_VERSION,
            "scenario_id": scenario["scenario_id"],
            "lesson_invoked": lesson["lesson_id"],
            "detector_id": detector_id,
            "finding_produced": bool(matching),
            "finding_ids": [str(item.get("finding_id") or "") for item in matching],
            "code_slice": scenario.get("code_slice") or scenario.get("candidate"),
            "invariant_violated": lesson["invariant"],
            "suggested_repair": lesson["repair_pattern"],
            "required_regression": lesson["required_regression"],
            "confidence": float(lesson["confidence"]),
            "provenance": lesson["provenance"],
            "expected_finding_code": expected_code,
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
        receipt["receipt_digest"] = _digest(receipt, size=16)
        receipts.append(receipt)
    packet = {
        "version": CRUCIBLE_REPLAY_VERSION,
        "registry_digest": loaded["registry_digest"],
        "scenario_count": len(receipts),
        "passed_count": sum(1 for item in receipts if item["finding_produced"]),
        "failed_count": sum(1 for item in receipts if not item["finding_produced"]),
        "receipts": receipts,
        "status": "PASSED" if receipts and all(item["finding_produced"] for item in receipts) else "FAILED",
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
    packet["packet_digest"] = _digest(packet, size=16)
    return packet


class ReviewLessonEngine:
    """Repository-bound typed lesson and external-review adapter."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        registry_path: str | Path = DEFAULT_REGISTRY_PATH,
        learning_root: str | Path = DEFAULT_LEARNING_ROOT,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_path = Path(registry_path)
        if not self.registry_path.is_absolute():
            self.registry_path = self.repo_root / self.registry_path
        self.learning_root = Path(learning_root).expanduser().resolve()
        self.findings_path = self.learning_root / "external_review_findings.jsonl"

    def summary(self) -> dict[str, Any]:
        registry = load_review_lesson_registry(self.registry_path)
        stored = 0
        if self.findings_path.exists():
            with self.findings_path.open("r", encoding="utf-8") as handle:
                stored = sum(1 for line in handle if line.strip())
        return {
            "version": REVIEW_LESSON_VERSION,
            "registry_path": str(self.registry_path),
            "registry_digest": registry["registry_digest"],
            "lesson_count": len(registry["lessons"]),
            "scenario_count": len(registry["scenarios"]),
            "detectors": sorted(DETECTORS),
            "stored_external_finding_count": stored,
            "truth_boundary": "review_learning_only",
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

    def normalize_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        head = current_head or _git_head(self.repo_root)
        return normalize_external_review(payload, current_head=head)

    def ingest_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        packet = self.normalize_review(payload, current_head=current_head)
        known: set[str] = set()
        if self.findings_path.exists():
            with self.findings_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    finding_id = str(row.get("finding_id") or "")
                    if finding_id:
                        known.add(finding_id)
        stored: list[str] = []
        rejected: list[dict[str, str]] = []
        self.findings_path.parent.mkdir(parents=True, exist_ok=True)
        with self.findings_path.open("a", encoding="utf-8") as handle:
            for finding in packet["findings"]:
                finding_id = str(finding.get("finding_id") or "")
                if finding_id in known or finding.get("disposition") == "duplicate":
                    rejected.append({"finding_id": finding_id, "reason": "duplicate"})
                    continue
                handle.write(_canonical_json(finding) + "\n")
                known.add(finding_id)
                stored.append(finding_id)
        return {
            **packet,
            "status": "stored" if stored else "no_new_findings",
            "stored_count": len(stored),
            "stored_finding_ids": stored,
            "rejected": rejected,
        }

    def detector(self, detector_id: str, candidate: Any) -> dict[str, Any]:
        return run_review_detector(detector_id, candidate)

    def crucible(self, *, detector_ids: Sequence[str] = ()) -> dict[str, Any]:
        return run_crucible_replay(self.registry_path, detector_ids=detector_ids)


__all__ = [
    "CRUCIBLE_REPLAY_VERSION",
    "DEFAULT_LEARNING_ROOT",
    "DEFAULT_REGISTRY_PATH",
    "DETECTORS",
    "PATCH_AUTHORITY",
    "REGISTRY_VERSION",
    "REVIEW_FINDING_VERSION",
    "REVIEW_LESSON_VERSION",
    "VSA_PATCH_AUTHORITY",
    "ReviewLessonEngine",
    "ReviewLessonError",
    "detect_authority_aliases",
    "detect_count_without_byte_budget",
    "detect_implicit_coordinate_basis_change",
    "detect_nested_unit_double_application",
    "detect_noncanonical_interchange_acceptance",
    "detect_noncanonical_source_path",
    "detect_order_dependent_digesting",
    "detect_protected_metadata_overrides",
    "detect_schema_runtime_drift",
    "detect_stale_evidence_claim",
    "detect_truncate_before_sort",
    "detect_unwired_regression",
    "detect_uri_alias_encoding",
    "load_review_lesson_registry",
    "normalize_external_review",
    "run_crucible_replay",
    "run_review_detector",
    "validate_review_lesson_registry",
]
