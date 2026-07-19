"""Shared contracts and bounded helpers for Coding Waboose review lessons."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

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

__all__ = [
    "CRUCIBLE_REPLAY_VERSION",
    "DEFAULT_LEARNING_ROOT",
    "DEFAULT_REGISTRY_PATH",
    "PATCH_AUTHORITY",
    "REGISTRY_VERSION",
    "REVIEW_FINDING_VERSION",
    "REVIEW_LESSON_VERSION",
    "VSA_PATCH_AUTHORITY",
    "_CANONICAL_AUTHORITY_KEYS",
    "_MAX_COMMENT_BYTES",
    "_MAX_PATH_BYTES",
    "_MAX_REVIEW_PAYLOAD_BYTES",
    "_MAX_SCENARIO_BYTES",
    "_MAX_STORED_FINDINGS",
    "_PROTECTED_AUTHORITY_NORMALIZED",
    "NormalizedReviewFinding",
    "ReviewLessonError",
    "_authority_key",
    "_bounded_json",
    "_canonical_bytes",
    "_canonical_json",
    "_detector_from_text",
    "_digest",
    "_disposition",
    "_finding",
    "_git_head",
    "_is_sequence",
    "_reviewer_name",
    "_safe_repo_path",
    "_safe_text",
    "_strip_markdown",
    "_title_from_body",
    "_walk_metadata",
]
