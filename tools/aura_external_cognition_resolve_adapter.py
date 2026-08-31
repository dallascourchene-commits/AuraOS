from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

SCHEMA_NAME = "aura-coordinate-memory-kv-v1"
SCHEMA_VERSION = "1.0.0"
READER_IMPLEMENTATION = "ExternalCognitionResolveAdapterV1/source-ready"
READER_VERSION = "0.1.0"


class ResolveDisposition(str, Enum):
    FOUND_VERIFIED = "FOUND_VERIFIED"
    NOT_FOUND = "NOT_FOUND"
    STORE_STALE = "STORE_STALE"
    STORE_INTEGRITY_ERROR = "STORE_INTEGRITY_ERROR"
    ROW_DIGEST_MISMATCH = "ROW_DIGEST_MISMATCH"
    SOURCE_REVALIDATION_REQUIRED = "SOURCE_REVALIDATION_REQUIRED"
    CURRENTNESS_REOPEN = "CURRENTNESS_REOPEN"
    WRONG_EVIDENCE_DOMAIN = "WRONG_EVIDENCE_DOMAIN"
    WRONG_RESPONSIBILITY_OWNER = "WRONG_RESPONSIBILITY_OWNER"
    PRINCIPAL_SCOPE_MISMATCH = "PRINCIPAL_SCOPE_MISMATCH"
    SUPERSEDED_HISTORY_ONLY = "SUPERSEDED_HISTORY_ONLY"
    HYDRATION_LIMIT_EXCEEDED = "HYDRATION_LIMIT_EXCEEDED"


class CurrentnessStatus(str, Enum):
    RESOLVED_CURRENT = "RESOLVED_CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True)
class ExternalCognitionReadRequestV1:
    store_ref: str
    expected_store_generation: str
    expected_store_sha256: str
    semantic_key: str
    consumer_ref: str
    consumer_generation: str
    evidence_domain: str
    principal: str
    required_currentness_axes: tuple[str, ...] = ()
    expected_value_digest: str | None = None
    max_standing_chars: int = 4096
    placement_hint: tuple[int, int, int] | None = None
    responsibility: str = "SOURCE_BOUND_COORDINATE_MEMORY"


@dataclass(frozen=True)
class ReadValidationContextV1:
    currentness: Mapping[str, CurrentnessStatus] = field(default_factory=dict)
    allowed_evidence_domains: frozenset[str] = field(default_factory=frozenset)
    allowed_principals: frozenset[str] = field(default_factory=frozenset)
    source_resolver_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoordinateMemoryReadCandidateV1:
    semantic_key: str
    value_digest: str
    cell: Any
    standing: str
    reopen: Any
    successor: Any
    store_generation: str
    source_currentness: str
    placement_hint: tuple[int, int, int] | None
    candidate_only: bool = True
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False


@dataclass(frozen=True)
class CoordinateMemoryReadReceiptV1:
    disposition: ResolveDisposition
    request_digest: str
    receipt_digest: str
    observed_store_sha256: str
    observed_store_generation: str
    semantic_key: str
    observed_value_digest: str | None
    reader_implementation: str = READER_IMPLEMENTATION
    reader_version: str = READER_VERSION
    candidate: CoordinateMemoryReadCandidateV1 | None = None
    source_resolver_refs: tuple[str, ...] = ()
    refusal_reason: str | None = None
    candidate_only: bool = True
    instruction_authority: bool = False
    write_authority: bool = False
    effect_authority: bool = False


@dataclass(frozen=True)
class CoordinateMemoryBatchReceiptV1:
    observed_store_sha256: str
    observed_store_generation: str
    request_digests: tuple[str, ...]
    result_receipt_digests: tuple[str, ...]
    results: tuple[CoordinateMemoryReadReceiptV1, ...]
    snapshot_coherent: bool = True
    candidate_only: bool = True
    write_authority: bool = False
    effect_authority: bool = False


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
    ).encode("utf-8")


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _normalize_expected_sha256(expected: str) -> str:
    value = expected.strip().lower()
    if len(value) not in (16, 64) or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("expected_store_sha256 must be 16- or 64-character SHA-256 hex")
    return value


class ExternalCognitionResolveAdapterV1:
    """Source-ready WP03 read membrane over an exact external-cognition snapshot.

    Currentness, evidence-domain and principal admission arrive through a separate
    validation context. Persisted rows and K27 placement never self-mint truth,
    instruction authority, write authority, effect authority, or transformer KV.
    """

    def __init__(self, *, snapshot_bytes: bytes, store_ref: str, store_generation: str) -> None:
        self._snapshot_bytes = bytes(snapshot_bytes)
        self.store_ref = store_ref
        self.store_generation = store_generation
        self.store_sha256 = hashlib.sha256(self._snapshot_bytes).hexdigest()
        try:
            parsed = json.loads(self._snapshot_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("snapshot_bytes must be valid UTF-8 JSON") from exc

        schema = parsed.get("schema", {})
        if isinstance(schema, str):
            schema_name = schema
            schema_version = parsed.get("version")
        else:
            schema_name = schema.get("name")
            schema_version = schema.get("version")
        if schema_name != SCHEMA_NAME or schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"wrong store schema: expected {SCHEMA_NAME}@{SCHEMA_VERSION}, "
                f"got {schema_name!r}@{schema_version!r}"
            )

        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise ValueError("store rows must be a list")
        index: dict[str, Mapping[str, Any]] = {}
        required = {"cell", "digest", "standing", "reopen", "successor"}
        for raw_row in rows:
            if not isinstance(raw_row, dict):
                raise ValueError("each row must be an object")
            key = raw_row.get("K")
            value = raw_row.get("V")
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError("each row must have string K and object V")
            if key in index:
                raise ValueError(f"duplicate semantic key: {key}")
            if set(value) != required:
                raise ValueError(f"row {key!r} must have exactly V keys {sorted(required)}")
            if not isinstance(value.get("digest"), str) or not value["digest"]:
                raise ValueError(f"row {key!r} digest must be non-empty string")
            index[key] = value
        self._rows = index

    def _request_digest(self, request: ExternalCognitionReadRequestV1) -> str:
        return _sha256_hex(asdict(request))

    def _receipt(
        self,
        *,
        request: ExternalCognitionReadRequestV1,
        context: ReadValidationContextV1,
        disposition: ResolveDisposition,
        value_digest: str | None = None,
        candidate: CoordinateMemoryReadCandidateV1 | None = None,
        refusal_reason: str | None = None,
    ) -> CoordinateMemoryReadReceiptV1:
        request_digest = self._request_digest(request)
        payload = {
            "disposition": disposition.value,
            "request_digest": request_digest,
            "observed_store_sha256": self.store_sha256,
            "observed_store_generation": self.store_generation,
            "semantic_key": request.semantic_key,
            "observed_value_digest": value_digest,
            "candidate": asdict(candidate) if candidate else None,
            "source_resolver_refs": list(context.source_resolver_refs),
            "refusal_reason": refusal_reason,
            "reader_implementation": READER_IMPLEMENTATION,
            "reader_version": READER_VERSION,
            "candidate_only": True,
            "instruction_authority": False,
            "write_authority": False,
            "effect_authority": False,
        }
        return CoordinateMemoryReadReceiptV1(
            disposition=disposition,
            request_digest=request_digest,
            receipt_digest=_sha256_hex(payload),
            observed_store_sha256=self.store_sha256,
            observed_store_generation=self.store_generation,
            semantic_key=request.semantic_key,
            observed_value_digest=value_digest,
            candidate=candidate,
            source_resolver_refs=context.source_resolver_refs,
            refusal_reason=refusal_reason,
        )

    def resolve(
        self,
        request: ExternalCognitionReadRequestV1,
        context: ReadValidationContextV1,
    ) -> CoordinateMemoryReadReceiptV1:
        if request.responsibility == "MODEL_PREFIX_KV":
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.WRONG_RESPONSIBILITY_OWNER,
                refusal_reason="source-bound cognition is not transformer MODEL_PREFIX_KV",
            )

        try:
            expected_sha = _normalize_expected_sha256(request.expected_store_sha256)
        except ValueError as exc:
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.STORE_INTEGRITY_ERROR,
                refusal_reason=str(exc),
            )
        if request.store_ref != self.store_ref or request.expected_store_generation != self.store_generation:
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.STORE_STALE,
                refusal_reason="store ref/generation mismatch",
            )
        if not self.store_sha256.startswith(expected_sha):
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.STORE_INTEGRITY_ERROR,
                refusal_reason="exact snapshot SHA-256 does not match expected digest",
            )

        row = self._rows.get(request.semantic_key)
        if row is None:
            return self._receipt(request=request, context=context, disposition=ResolveDisposition.NOT_FOUND)

        value_digest = str(row["digest"])
        if request.expected_value_digest is not None and request.expected_value_digest != value_digest:
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.ROW_DIGEST_MISMATCH,
                value_digest=value_digest,
                refusal_reason="stored value digest differs from expected value digest",
            )
        if context.allowed_evidence_domains and request.evidence_domain not in context.allowed_evidence_domains:
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.WRONG_EVIDENCE_DOMAIN,
                value_digest=value_digest,
            )
        if context.allowed_principals and request.principal not in context.allowed_principals:
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.PRINCIPAL_SCOPE_MISMATCH,
                value_digest=value_digest,
            )

        axis_statuses: list[CurrentnessStatus] = []
        for axis in request.required_currentness_axes:
            status = context.currentness.get(axis, CurrentnessStatus.UNKNOWN)
            axis_statuses.append(status)
            if status is CurrentnessStatus.STALE:
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=ResolveDisposition.CURRENTNESS_REOPEN,
                    value_digest=value_digest,
                    refusal_reason=f"required currentness axis {axis!r} is stale",
                )
            if status is CurrentnessStatus.UNKNOWN:
                return self._receipt(
                    request=request,
                    context=context,
                    disposition=ResolveDisposition.SOURCE_REVALIDATION_REQUIRED,
                    value_digest=value_digest,
                    refusal_reason=f"required currentness axis {axis!r} is unknown",
                )

        standing = row["standing"]
        if not isinstance(standing, str):
            standing = json.dumps(standing, sort_keys=True, ensure_ascii=False)
        if request.max_standing_chars < 0 or len(standing) > request.max_standing_chars:
            return self._receipt(
                request=request,
                context=context,
                disposition=ResolveDisposition.HYDRATION_LIMIT_EXCEEDED,
                value_digest=value_digest,
                refusal_reason="standing exceeds caller hydration bound",
            )

        successor = row["successor"]
        has_successor = successor not in (None, "", [], {}, False, "NONE", "none", "N/A", "n/a")
        source_currentness = (
            CurrentnessStatus.NOT_REQUIRED.value
            if not axis_statuses
            else CurrentnessStatus.RESOLVED_CURRENT.value
        )
        candidate = CoordinateMemoryReadCandidateV1(
            semantic_key=request.semantic_key,
            value_digest=value_digest,
            cell=row["cell"],
            standing=standing,
            reopen=row["reopen"],
            successor=successor,
            store_generation=self.store_generation,
            source_currentness=source_currentness,
            placement_hint=request.placement_hint,
        )
        disposition = (
            ResolveDisposition.SUPERSEDED_HISTORY_ONLY
            if has_successor
            else ResolveDisposition.FOUND_VERIFIED
        )
        return self._receipt(
            request=request,
            context=context,
            disposition=disposition,
            value_digest=value_digest,
            candidate=candidate,
            refusal_reason="successor present; historical candidate only" if has_successor else None,
        )

    def resolve_many(
        self,
        requests: Sequence[ExternalCognitionReadRequestV1],
        contexts: Sequence[ReadValidationContextV1],
    ) -> CoordinateMemoryBatchReceiptV1:
        if len(requests) != len(contexts):
            raise ValueError("requests and contexts must have identical lengths")
        results = tuple(self.resolve(req, ctx) for req, ctx in zip(requests, contexts))
        return CoordinateMemoryBatchReceiptV1(
            observed_store_sha256=self.store_sha256,
            observed_store_generation=self.store_generation,
            request_digests=tuple(result.request_digest for result in results),
            result_receipt_digests=tuple(result.receipt_digest for result in results),
            results=results,
        )
