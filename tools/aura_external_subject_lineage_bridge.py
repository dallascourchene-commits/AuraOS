#!/usr/bin/env python3
"""EKI-3: cross-generation subject identity + version-lineage bridge.

D0 / HS1 / NONPROMOTING.

This membrane reconciles two independently owned identity contracts without
pretending their hashes are interchangeable:

* legacy EKI-2 semantic identity hashes (source_kind, canonical_id);
* current EKI/#735 stable subject identity hashes
  (provider, source_kind, canonical_id).

A typed, exact source descriptor is required to prove the bridge.  After that
identity proof, the membrane follows only explicit EKI-2 successor edges to a
terminal record key.  It never infers order from timestamps, lexical key order,
K27 placement, a persisted CURRENT label, or retrieval similarity.

The terminal record is still only a read candidate.  Currentness must arrive
from an external validation context and final row validation remains owned by
the independently authored PR #728 reader.

Coordinate memory here is an explicit source-bound representation.  No native,
private, hidden, or provider transformer KV cache is accessed or mutated.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Mapping


STORE_SCHEMA_NAME = "aura-coordinate-memory-kv-v1"
STORE_SCHEMA_VERSION = "1.0.0"
BRIDGE_SCHEMA = "AURA-EKI3-SUBJECT-IDENTITY-LINEAGE-BRIDGE-v1"
BRIDGE_IMPLEMENTATION = "ExternalSubjectLineageBridgeV1/source-ready"

# Exact independent other-Agent anchors used to derive this objective.
PR728_READER_HEAD = "9865c42f3ada2520141bd2fe30a439ce160ce2f8"
PR728_READER_BLOB = "53de9d551c81a0eb495eb180294c0aba5eb359d0"
PR728_READER_RUN = 33416056653
PR735_CANDIDATE_HEAD = "89a66cdb972d3eab19c9408356b7061d1529947d"
PR735_CANDIDATE_BLOB = "fed7003630487af41586ce07a00b83b8fbf66835"
PR735_CANDIDATE_RUN = 33417664825

LEGACY_SEMANTIC_DOMAIN = "AURA-EKI-EXTERNAL-SEMANTIC-ID-v1"
CURRENT_SUBJECT_DOMAIN = "AURA-EXTERNAL-SUBJECT-v1"

# This is a type bridge, not a synonym table for arbitrary strings.  A mapping
# exists only where the legacy source kind has one unambiguous current owner.
LEGACY_TO_CURRENT_SUBJECT_TYPE: Mapping[str, tuple[str, str]] = {
    "ARXIV": ("ARXIV", "PAPER"),
    "GITHUB": ("GITHUB", "REPOSITORY"),
    "HUGGINGFACE_MODEL": ("HUGGING_FACE", "MODEL"),
    "HUGGINGFACE_DATASET": ("HUGGING_FACE", "DATASET"),
    "HUGGINGFACE_SPACE": ("HUGGING_FACE", "SPACE"),
    "GOOGLE_SCHOLAR_DISCOVERY": ("GOOGLE_SCHOLAR", "PAPER"),
    "REDDIT": ("REDDIT", "DISCUSSION"),
    "WEB": ("WEB", "WEB_PAGE"),
}

HEX = frozenset("0123456789abcdef")


class LineageDisposition(str, Enum):
    RESOLVED_CURRENT_RECORD_CANDIDATE = "RESOLVED_CURRENT_RECORD_CANDIDATE"
    CURRENTNESS_REVALIDATION_REQUIRED = "CURRENTNESS_REVALIDATION_REQUIRED"
    CURRENTNESS_REOPEN = "CURRENTNESS_REOPEN"
    NOT_FOUND = "NOT_FOUND"
    STORE_STALE = "STORE_STALE"
    STORE_INTEGRITY_ERROR = "STORE_INTEGRITY_ERROR"
    IDENTITY_BRIDGE_HOLD = "IDENTITY_BRIDGE_HOLD"
    LINEAGE_AMBIGUOUS = "LINEAGE_AMBIGUOUS"
    LINEAGE_BROKEN = "LINEAGE_BROKEN"
    WRONG_RESPONSIBILITY_OWNER = "WRONG_RESPONSIBILITY_OWNER"


class CurrentnessStatus(str, Enum):
    RESOLVED_CURRENT = "RESOLVED_CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class SubjectLineageBridgeError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SubjectLineageBridgeError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _required(value, name).lower()
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise SubjectLineageBridgeError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def legacy_semantic_id(*, legacy_source_kind: str, canonical_id: str) -> str:
    legacy_source_kind = _required(legacy_source_kind, "LEGACY_SOURCE_KIND")
    canonical_id = _required(canonical_id, "CANONICAL_ID")
    return _sha(
        {
            "domain": LEGACY_SEMANTIC_DOMAIN,
            "source_kind": legacy_source_kind,
            "canonical_id": canonical_id,
        }
    )


def current_subject_key(*, provider: str, source_kind: str, canonical_id: str) -> str:
    provider = _required(provider, "CURRENT_PROVIDER")
    source_kind = _required(source_kind, "CURRENT_SOURCE_KIND")
    canonical_id = _required(canonical_id, "CANONICAL_ID")
    return _sha(
        {
            "domain": CURRENT_SUBJECT_DOMAIN,
            "provider": provider,
            "source_kind": source_kind,
            "canonical_id": canonical_id,
        }
    )


@dataclass(frozen=True)
class CurrentSubjectDescriptorV1:
    provider: str
    source_kind: str
    canonical_id: str
    canonical_uri: str
    claimed_subject_key: str

    def validate(self) -> None:
        _required(self.provider, "CURRENT_PROVIDER")
        _required(self.source_kind, "CURRENT_SOURCE_KIND")
        _required(self.canonical_id, "CANONICAL_ID")
        _required(self.canonical_uri, "CANONICAL_URI")
        claimed = _sha256(self.claimed_subject_key, "CLAIMED_SUBJECT_KEY")
        expected = current_subject_key(
            provider=self.provider,
            source_kind=self.source_kind,
            canonical_id=self.canonical_id,
        )
        if claimed != expected:
            raise SubjectLineageBridgeError("CURRENT_SUBJECT_KEY_DIGEST_MISMATCH")


@dataclass(frozen=True)
class SubjectLineageRequestV1:
    store_ref: str
    expected_store_generation: str
    expected_store_sha256: str
    legacy_source_kind: str
    subject: CurrentSubjectDescriptorV1
    responsibility: str = "SOURCE_BOUND_COORDINATE_MEMORY"


@dataclass(frozen=True)
class SubjectLineageValidationContextV1:
    record_currentness: Mapping[str, CurrentnessStatus] = field(default_factory=dict)
    source_resolver_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SubjectLineageReceiptV1:
    disposition: LineageDisposition
    request_digest: str
    receipt_digest: str
    observed_store_sha256: str
    observed_store_generation: str
    legacy_semantic_id: str | None
    current_subject_key: str | None
    ordered_record_keys: tuple[str, ...]
    historical_record_keys: tuple[str, ...]
    terminal_record_key: str | None
    terminal_currentness: str
    source_resolver_refs: tuple[str, ...]
    refusal_reason: str | None = None
    bridge_implementation: str = BRIDGE_IMPLEMENTATION
    candidate_only: bool = True
    currentness_minted_from_store: bool = False
    chronological_order_inferred: bool = False
    k27_semantic_authority: bool = False
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    native_private_transformer_kv_accessed: bool = False


class ExternalSubjectLineageBridgeV1:
    """Resolve a current stable subject onto an explicit EKI-2 version chain."""

    def __init__(self, *, snapshot_bytes: bytes, store_ref: str, store_generation: str) -> None:
        self.snapshot_bytes = bytes(snapshot_bytes)
        self.store_ref = _required(store_ref, "STORE_REF")
        self.store_generation = _required(store_generation, "STORE_GENERATION")
        self.store_sha256 = _sha_bytes(self.snapshot_bytes)
        try:
            parsed = json.loads(self.snapshot_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SubjectLineageBridgeError("SNAPSHOT_MUST_BE_VALID_UTF8_JSON") from exc
        if not isinstance(parsed, Mapping):
            raise SubjectLineageBridgeError("SNAPSHOT_OBJECT_REQUIRED")
        schema = parsed.get("schema")
        if not isinstance(schema, Mapping):
            raise SubjectLineageBridgeError("STORE_SCHEMA_OBJECT_REQUIRED")
        if schema.get("name") != STORE_SCHEMA_NAME or schema.get("version") != STORE_SCHEMA_VERSION:
            raise SubjectLineageBridgeError("STORE_SCHEMA_MISMATCH")
        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise SubjectLineageBridgeError("STORE_ROWS_LIST_REQUIRED")
        index: dict[str, Mapping[str, Any]] = {}
        required = {"cell", "digest", "standing", "reopen", "successor"}
        for raw in rows:
            if not isinstance(raw, Mapping) or not isinstance(raw.get("K"), str):
                raise SubjectLineageBridgeError("STORE_ROW_SHAPE_INVALID")
            key = raw["K"]
            value = raw.get("V")
            if not isinstance(value, Mapping) or set(value) != required:
                raise SubjectLineageBridgeError("STORE_ROW_VALUE_SCHEMA_INVALID")
            if key in index:
                raise SubjectLineageBridgeError("STORE_DUPLICATE_KEY")
            index[key] = dict(value)
        self._rows = index

    def _request_digest(self, request: SubjectLineageRequestV1) -> str:
        return _sha({"domain": BRIDGE_SCHEMA, "request": asdict(request)})

    def _receipt(
        self,
        *,
        request: SubjectLineageRequestV1,
        context: SubjectLineageValidationContextV1,
        disposition: LineageDisposition,
        legacy_id: str | None = None,
        current_key: str | None = None,
        ordered: tuple[str, ...] = (),
        terminal: str | None = None,
        terminal_currentness: str = CurrentnessStatus.UNKNOWN.value,
        refusal_reason: str | None = None,
    ) -> SubjectLineageReceiptV1:
        request_digest = self._request_digest(request)
        historical = ordered[:-1] if ordered and terminal == ordered[-1] else ()
        payload = {
            "disposition": disposition.value,
            "request_digest": request_digest,
            "observed_store_sha256": self.store_sha256,
            "observed_store_generation": self.store_generation,
            "legacy_semantic_id": legacy_id,
            "current_subject_key": current_key,
            "ordered_record_keys": ordered,
            "historical_record_keys": historical,
            "terminal_record_key": terminal,
            "terminal_currentness": terminal_currentness,
            "source_resolver_refs": context.source_resolver_refs,
            "refusal_reason": refusal_reason,
            "bridge_implementation": BRIDGE_IMPLEMENTATION,
            "claim_ceiling": {
                "candidate_only": True,
                "currentness_minted_from_store": False,
                "chronological_order_inferred": False,
                "k27_semantic_authority": False,
                "instruction_authority": False,
                "write_authority": False,
                "effect_authority": False,
                "native_private_transformer_kv_accessed": False,
            },
        }
        return SubjectLineageReceiptV1(
            disposition=disposition,
            request_digest=request_digest,
            receipt_digest=_sha({"domain": BRIDGE_SCHEMA, "receipt": payload}),
            observed_store_sha256=self.store_sha256,
            observed_store_generation=self.store_generation,
            legacy_semantic_id=legacy_id,
            current_subject_key=current_key,
            ordered_record_keys=ordered,
            historical_record_keys=historical,
            terminal_record_key=terminal,
            terminal_currentness=terminal_currentness,
            source_resolver_refs=context.source_resolver_refs,
            refusal_reason=refusal_reason,
        )

    def resolve(
        self,
        request: SubjectLineageRequestV1,
        context: SubjectLineageValidationContextV1,
    ) -> SubjectLineageReceiptV1:
        if request.responsibility == "MODEL_PREFIX_KV":
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.WRONG_RESPONSIBILITY_OWNER,
                refusal_reason="source-bound coordinate memory is not transformer MODEL_PREFIX_KV",
            )
        try:
            request.subject.validate()
            expected_sha = _sha256(request.expected_store_sha256, "EXPECTED_STORE_SHA256")
            legacy_kind = _required(request.legacy_source_kind, "LEGACY_SOURCE_KIND")
        except SubjectLineageBridgeError as exc:
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.IDENTITY_BRIDGE_HOLD,
                refusal_reason=str(exc),
            )
        if request.store_ref != self.store_ref or request.expected_store_generation != self.store_generation:
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.STORE_STALE,
                refusal_reason="store ref/generation mismatch",
            )
        if expected_sha != self.store_sha256:
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.STORE_INTEGRITY_ERROR,
                refusal_reason="exact store SHA-256 mismatch",
            )

        expected_type = LEGACY_TO_CURRENT_SUBJECT_TYPE.get(legacy_kind)
        actual_type = (request.subject.provider, request.subject.source_kind)
        if expected_type is None:
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.IDENTITY_BRIDGE_HOLD,
                refusal_reason="legacy source kind has no unambiguous current subject-type bridge",
            )
        if actual_type != expected_type:
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.IDENTITY_BRIDGE_HOLD,
                refusal_reason="legacy/current provider+source-kind mapping mismatch",
            )

        legacy_id = legacy_semantic_id(
            legacy_source_kind=legacy_kind,
            canonical_id=request.subject.canonical_id,
        )
        current_key = current_subject_key(
            provider=request.subject.provider,
            source_kind=request.subject.source_kind,
            canonical_id=request.subject.canonical_id,
        )
        prefix = f"external-cognition://{legacy_id}/record/"
        subject_rows = {k: v for k, v in self._rows.items() if k.startswith(prefix)}
        if not subject_rows:
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.NOT_FOUND,
                legacy_id=legacy_id,
                current_key=current_key,
            )

        successors: dict[str, str | None] = {}
        indegree = {key: 0 for key in subject_rows}
        for key, value in subject_rows.items():
            standing_raw = value.get("standing")
            if not isinstance(standing_raw, str):
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=LineageDisposition.LINEAGE_BROKEN,
                    legacy_id=legacy_id,
                    current_key=current_key,
                    refusal_reason="subject row standing must be JSON string",
                )
            try:
                standing = json.loads(standing_raw)
            except json.JSONDecodeError:
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=LineageDisposition.LINEAGE_BROKEN,
                    legacy_id=legacy_id,
                    current_key=current_key,
                    refusal_reason="subject row standing is not valid JSON",
                )
            if not isinstance(standing, Mapping):
                reason = "subject row standing object required"
            elif standing.get("semantic_id") != legacy_id:
                reason = "legacy semantic identity mismatch inside row standing"
            elif standing.get("source_kind") != legacy_kind:
                reason = "legacy source kind mismatch inside row standing"
            elif standing.get("canonical_id") != request.subject.canonical_id:
                reason = "canonical id mismatch inside row standing"
            elif standing.get("canonical_uri") != request.subject.canonical_uri:
                reason = "canonical URI drift requires explicit alias/reopen proof"
            elif not isinstance(standing.get("record_generation"), str) or not standing["record_generation"]:
                reason = "record generation missing inside row standing"
            elif key != prefix + standing["record_generation"]:
                reason = "record key does not bind exact standing record generation"
            else:
                reason = None
            if reason is not None:
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=LineageDisposition.IDENTITY_BRIDGE_HOLD,
                    legacy_id=legacy_id,
                    current_key=current_key,
                    refusal_reason=reason,
                )

            successor = value.get("successor")
            if successor in (None, ""):
                successors[key] = None
                continue
            if not isinstance(successor, str):
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=LineageDisposition.LINEAGE_BROKEN,
                    legacy_id=legacy_id,
                    current_key=current_key,
                    refusal_reason="successor must be empty/null or an exact record key",
                )
            if successor not in subject_rows:
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=LineageDisposition.LINEAGE_BROKEN,
                    legacy_id=legacy_id,
                    current_key=current_key,
                    refusal_reason="successor leaves the exact stable-subject lineage",
                )
            successors[key] = successor
            indegree[successor] += 1

        roots = tuple(sorted(key for key, degree in indegree.items() if degree == 0))
        terminals = tuple(sorted(key for key, successor in successors.items() if successor is None))
        if len(roots) != 1 or len(terminals) != 1 or any(degree > 1 for degree in indegree.values()):
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.LINEAGE_AMBIGUOUS,
                legacy_id=legacy_id,
                current_key=current_key,
                refusal_reason="explicit supersession graph must be one lossless linear lineage",
            )

        ordered_list: list[str] = []
        seen: set[str] = set()
        cursor: str | None = roots[0]
        while cursor is not None:
            if cursor in seen:
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=LineageDisposition.LINEAGE_BROKEN,
                    legacy_id=legacy_id,
                    current_key=current_key,
                    refusal_reason="supersession cycle forbidden",
                )
            seen.add(cursor)
            ordered_list.append(cursor)
            cursor = successors[cursor]
        if len(seen) != len(subject_rows):
            return self._receipt(
                request=request,
                context=context,
                disposition=LineageDisposition.LINEAGE_AMBIGUOUS,
                legacy_id=legacy_id,
                current_key=current_key,
                refusal_reason="disconnected same-subject records require explicit supersession relation",
            )

        ordered = tuple(ordered_list)
        terminal = ordered[-1]
        status = context.record_currentness.get(terminal, CurrentnessStatus.UNKNOWN)
        if not isinstance(status, CurrentnessStatus):
            try:
                status = CurrentnessStatus(str(status))
            except ValueError:
                status = CurrentnessStatus.UNKNOWN
        if status is CurrentnessStatus.STALE:
            disposition = LineageDisposition.CURRENTNESS_REOPEN
            reason = "terminal explicit-successor candidate is stale under external currentness"
        elif status is CurrentnessStatus.RESOLVED_CURRENT:
            disposition = LineageDisposition.RESOLVED_CURRENT_RECORD_CANDIDATE
            reason = None
        else:
            disposition = LineageDisposition.CURRENTNESS_REVALIDATION_REQUIRED
            reason = "explicit lineage terminal cannot self-mint source currentness"
        return self._receipt(
            request=request,
            context=context,
            disposition=disposition,
            legacy_id=legacy_id,
            current_key=current_key,
            ordered=ordered,
            terminal=terminal,
            terminal_currentness=status.value,
            refusal_reason=reason,
        )
