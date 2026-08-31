#!/usr/bin/env python3
"""Resolve one stable EKI semantic subject to one version-record candidate.

D0 / HS1 / NONPROMOTING.

This membrane consumes an exact EKI-2 coordinate-memory snapshot and identifies
one unsuperseded record for a stable semantic subject.  It does not infer
chronology, source currentness, semantic truth, or any read/write/effect
authority.  The selected record remains subject to the independently owned EKI
read-currentness membrane before use.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping


STORE_SCHEMA_NAME = "aura-coordinate-memory-kv-v1"
STORE_SCHEMA_VERSION = "1.0.0"
RESOLVER_SCHEMA = "AURA-EKI-SUBJECT-VERSION-RESOLVER-v1"
RECORD_PREFIX = "external-cognition://"
HEX = frozenset("0123456789abcdef")


class SubjectVersionDisposition(str, Enum):
    SELECTED_VERSION_CANDIDATE = "SELECTED_VERSION_CANDIDATE"
    HOLD_SUBJECT_NOT_FOUND = "HOLD_SUBJECT_NOT_FOUND"
    HOLD_AMBIGUOUS_HEAD = "HOLD_AMBIGUOUS_HEAD"
    HOLD_SUPERSESSION_TARGET_MISSING = "HOLD_SUPERSESSION_TARGET_MISSING"
    HOLD_CROSS_SUBJECT_SUCCESSOR = "HOLD_CROSS_SUBJECT_SUCCESSOR"
    HOLD_SUPERSESSION_CYCLE = "HOLD_SUPERSESSION_CYCLE"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _subject_key_prefix(semantic_subject_id: str) -> str:
    _sha256(semantic_subject_id, "SEMANTIC_SUBJECT_ID")
    return f"{RECORD_PREFIX}{semantic_subject_id}/record/"


def _parse_snapshot(snapshot_bytes: bytes) -> tuple[Mapping[str, Any], ...]:
    try:
        body = json.loads(snapshot_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("SNAPSHOT_MUST_BE_VALID_UTF8_JSON") from exc
    if not isinstance(body, Mapping):
        raise ValueError("SNAPSHOT_OBJECT_REQUIRED")
    schema = body.get("schema")
    if not isinstance(schema, Mapping) or schema.get("name") != STORE_SCHEMA_NAME or schema.get("version") != STORE_SCHEMA_VERSION:
        raise ValueError("SNAPSHOT_SCHEMA_MISMATCH")
    rows = body.get("rows")
    if not isinstance(rows, list):
        raise ValueError("SNAPSHOT_ROWS_LIST_REQUIRED")
    seen: set[str] = set()
    normalized: list[Mapping[str, Any]] = []
    required_v = {"cell", "digest", "standing", "reopen", "successor"}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("K"), str):
            raise ValueError("SNAPSHOT_ROW_SHAPE_INVALID")
        key = row["K"]
        if key in seen:
            raise ValueError("SNAPSHOT_DUPLICATE_KEY")
        seen.add(key)
        value = row.get("V")
        if not isinstance(value, Mapping) or set(value) != required_v:
            raise ValueError("SNAPSHOT_ROW_VALUE_SCHEMA_INVALID")
        if not isinstance(value.get("standing"), str):
            raise ValueError("SNAPSHOT_STANDING_STRING_REQUIRED")
        normalized.append({"K": key, "V": dict(value)})
    return tuple(normalized)


def _standing(value: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        parsed = json.loads(value["standing"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("ROW_STANDING_MUST_BE_VALID_JSON") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError("ROW_STANDING_OBJECT_REQUIRED")
    return parsed


def _record_generation_from_key(key: str, semantic_subject_id: str) -> str:
    prefix = _subject_key_prefix(semantic_subject_id)
    if not key.startswith(prefix):
        raise ValueError("VERSION_KEY_SUBJECT_PREFIX_MISMATCH")
    generation = key[len(prefix):]
    return _sha256(generation, "RECORD_GENERATION")


@dataclass(frozen=True)
class SubjectVersionResolutionReceiptV1:
    schema: str
    disposition: SubjectVersionDisposition
    semantic_subject_id: str
    store_generation: str
    store_sha256: str
    subject_record_count: int
    candidate_record_key: str | None
    candidate_record_generation: str | None
    historical_record_keys: tuple[str, ...]
    head_record_keys: tuple[str, ...]
    reason: str
    candidate_only: bool = True
    source_currentness_proven: bool = False
    selected_head_is_currentness_witness: bool = False
    chronology_inferred: bool = False
    k27_used_for_version_selection: bool = False
    semantic_truth_proven: bool = False
    read_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha({"domain": RESOLVER_SCHEMA, "receipt": asdict(self)})


def resolve_subject_version(
    *,
    snapshot_bytes: bytes,
    semantic_subject_id: str,
    expected_store_sha256: str,
    expected_store_generation: str,
) -> SubjectVersionResolutionReceiptV1:
    """Return one unsuperseded version candidate or a typed HOLD.

    The only ordering relation admitted here is an explicit persisted successor
    edge.  Timestamps, source generation labels, lexical key order, K27 locality,
    and persisted CURRENT labels cannot choose a head.
    """
    semantic_subject_id = _sha256(semantic_subject_id, "SEMANTIC_SUBJECT_ID")
    expected_store_sha256 = _sha256(expected_store_sha256, "EXPECTED_STORE_SHA256")
    observed_sha = _sha_bytes(snapshot_bytes)
    if observed_sha != expected_store_sha256:
        raise ValueError("STORE_SHA256_MISMATCH")
    derived_generation = "EKI2::STORE::" + observed_sha[:32]
    if expected_store_generation != derived_generation:
        raise ValueError("STORE_GENERATION_MISMATCH")

    rows = _parse_snapshot(snapshot_bytes)
    prefix = _subject_key_prefix(semantic_subject_id)
    subject_rows = {row["K"]: row["V"] for row in rows if row["K"].startswith(prefix)}

    def receipt(disposition: SubjectVersionDisposition, *, candidate_key: str | None = None, candidate_generation: str | None = None, heads: tuple[str, ...] = (), reason: str) -> SubjectVersionResolutionReceiptV1:
        historical = tuple(sorted(k for k, v in subject_rows.items() if v.get("successor") not in (None, "")))
        return SubjectVersionResolutionReceiptV1(
            schema=RESOLVER_SCHEMA,
            disposition=disposition,
            semantic_subject_id=semantic_subject_id,
            store_generation=derived_generation,
            store_sha256=observed_sha,
            subject_record_count=len(subject_rows),
            candidate_record_key=candidate_key,
            candidate_record_generation=candidate_generation,
            historical_record_keys=historical,
            head_record_keys=heads,
            reason=reason,
        )

    if not subject_rows:
        return receipt(SubjectVersionDisposition.HOLD_SUBJECT_NOT_FOUND, reason="SUBJECT_HAS_NO_VERSION_ROWS")

    successors: dict[str, str] = {}
    for key, value in subject_rows.items():
        generation = _record_generation_from_key(key, semantic_subject_id)
        standing = _standing(value)
        if standing.get("semantic_id") != semantic_subject_id:
            raise ValueError("ROW_STANDING_SUBJECT_MISMATCH")
        if standing.get("record_generation") != generation:
            raise ValueError("ROW_STANDING_RECORD_GENERATION_MISMATCH")
        # Persisted currentness remains provenance only; it never participates in head selection.
        successor = value.get("successor")
        if successor in (None, ""):
            continue
        if not isinstance(successor, str):
            raise ValueError("ROW_SUCCESSOR_MUST_BE_STRING_OR_NULL")
        if not successor.startswith(prefix):
            return receipt(SubjectVersionDisposition.HOLD_CROSS_SUBJECT_SUCCESSOR, reason="SUCCESSOR_ESCAPES_STABLE_SUBJECT")
        if successor not in subject_rows:
            return receipt(SubjectVersionDisposition.HOLD_SUPERSESSION_TARGET_MISSING, reason="SUCCESSOR_TARGET_NOT_PRESENT_IN_EXACT_STORE_GENERATION")
        successors[key] = successor

    for start in subject_rows:
        seen: set[str] = set()
        cursor = start
        while cursor in successors:
            if cursor in seen:
                return receipt(SubjectVersionDisposition.HOLD_SUPERSESSION_CYCLE, reason="EXPLICIT_SUPERSESSION_GRAPH_CONTAINS_CYCLE")
            seen.add(cursor)
            cursor = successors[cursor]

    heads = tuple(sorted(key for key in subject_rows if key not in successors))
    if len(heads) != 1:
        return receipt(SubjectVersionDisposition.HOLD_AMBIGUOUS_HEAD, heads=heads, reason="EXACTLY_ONE_UNSUPERSEDED_VERSION_REQUIRED")

    selected = heads[0]
    selected_generation = _record_generation_from_key(selected, semantic_subject_id)
    return receipt(
        SubjectVersionDisposition.SELECTED_VERSION_CANDIDATE,
        candidate_key=selected,
        candidate_generation=selected_generation,
        heads=heads,
        reason="UNIQUE_UNSUPERSEDED_VERSION_CANDIDATE_REQUIRES_READ_TIME_SOURCE_REVALIDATION",
    )


__all__ = [
    "RESOLVER_SCHEMA",
    "SubjectVersionDisposition",
    "SubjectVersionResolutionReceiptV1",
    "resolve_subject_version",
]
