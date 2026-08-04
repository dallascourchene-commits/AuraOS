"""Deterministic, non-operational contracts for intent-compiled spatial workspaces.

The records reference Aura's existing canonical owners. They never activate an
organ, invoke a renderer or model, persist project truth, or grant mutation,
publication, deployment, professional, payment, or merge authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields, is_dataclass, replace
from enum import Enum
import hashlib
import json
import math
import re
import time
from types import MappingProxyType
from typing import Any

WORKSPACE_CONTRACTS_VERSION = "AURA_INTENT_SPATIAL_WORKSPACE_CONTRACTS_V1"
AUTHORITY_ENVELOPE_VERSION = "AURA_WORKSPACE_AUTHORITY_ENVELOPE_V1"
CANONICAL_REFERENCE_VERSION = "AURA_CANONICAL_REFERENCE_V1"
REPOSITORY_IDENTITY_VERSION = "AURA_REPOSITORY_IDENTITY_V1"
PROJECT_CONTEXT_PROJECTION_VERSION = "AURA_PROJECT_CONTEXT_PROJECTION_V1"
EPHEMERAL_WORKSPACE_RECIPE_VERSION = "AURA_EPHEMERAL_WORKSPACE_RECIPE_V1"
SPATIAL_REFERENT_BINDING_VERSION = "AURA_SPATIAL_REFERENT_BINDING_V1"
MULTIMODAL_SPATIAL_OBSERVATION_VERSION = "AURA_MULTIMODAL_SPATIAL_OBSERVATION_V1"
CODING_SPATIAL_WORKSPACE_V1 = "CODING_SPATIAL_WORKSPACE_V1"
LEGACY_EPHEMERAL_MANIFEST_VERSION = "AURA_EPHEMERAL_ORGAN_V1"
MAX_ITEMS = 512
MAX_TEXT_BYTES = 4096
MAX_METADATA_BYTES = 65_536
MAX_TTL_SECONDS = 86_400
MAX_INTEGER = 10_000_000_000
MAX_TIMESTAMP = 2**63 - 1
MAX_DEPENDENCY_EDGES = 512
MAX_CANONICAL_DEPTH = 64

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_LEGACY_DIGEST = re.compile(r"^[0-9a-f]{32}$")
_CAPABILITY_RESOLUTION_DIGEST = re.compile(r"^[0-9a-f]{16}$")
_COMMIT_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TRUTH = frozenset({"EXACT", "DERIVED", "PRESENTATION", "HYPOTHESIS"})
_FRESHNESS = frozenset({"CURRENT", "BOUNDED", "STALE", "UNKNOWN"})
_CURRENT_FRESHNESS = frozenset({"CURRENT", "BOUNDED"})
_INPUTS = frozenset({"VOICE", "HAND", "GAZE", "RAY", "TOUCH", "KEYBOARD", "CONTROLLER"})
_EVIDENCE = frozenset({"MEASURED", "DERIVED", "ESTIMATED", "UNAVAILABLE"})
_LIFECYCLE_POLICY = "EXPLICIT_COMPLETE_CANCEL_FAILURE_OR_TTL"
_DISSOLUTION_POLICY = "MANDATORY_REVOKE_AND_REMOVE_TEMP_STATE"
_PROJECT_PRIVACY_CLASS = "MINIMUM_SUFFICIENT"
_PROJECT_EGRESS_CLASS = "LOCAL_ONLY"
_METADATA_TEXT_FIELDS = frozenset({"manifest_version", "source_path", "source_span", "symbol", "relation", "evidence_class", "media_type", "description", "note"})
_METADATA_BOOL_FIELDS = frozenset({"wrapped_not_replaced"})
_METADATA_INT_FIELDS = frozenset({"line_start", "line_end", "byte_length"})
_METADATA_DIGEST_FIELDS = frozenset({"content_digest", "source_digest", "artifact_digest", "legacy_manifest_digest"})
_METADATA_FIELDS = _METADATA_TEXT_FIELDS | _METADATA_BOOL_FIELDS | _METADATA_INT_FIELDS | _METADATA_DIGEST_FIELDS
_PROJECT_CANONICAL_OWNER = "aura_unified_memory_continuity"
_LEGACY_MANIFEST_FIELDS = frozenset({
    "manifest_version", "organ_id", "objective", "objective_hash", "creator",
    "created_at", "ttl_seconds", "expires_at", "intent_packet", "lexc_route",
    "machine_route", "capability_resolution_ref", "capability_resolution_digest",
    "requested_capabilities", "granted_capabilities", "denied_capabilities",
    "boundary_contracts", "arena_lease", "components", "resource_budget",
    "data_policy", "ui_manifest", "verifier_requirements", "human_approval_policy",
    "dissolution_policy", "crystallization_policy", "phase_hash",
    "signature_or_digest", "patch_authority", "vsa_patch_authority",
})
_LEGACY_ALLOWED_CAPABILITIES = frozenset({
    "resolve_capabilities", "search_code", "inspect_symbol", "read_slice",
    "rank_regions", "build_change_graph", "show_tests", "show_docs",
    "render_ui_schema", "write_temp_audit", "emit_telemetry", "dissolve",
})
_LEGACY_REQUIRED_WORKSPACE_CAPABILITIES = frozenset({
    "resolve_capabilities", "read_slice", "dissolve",
})
_LEGACY_SAFE_READABLE_PATHS = frozenset({
    ".aura/CODEMAP.json", ".aura/CODEMAP.md", ".aura/MODULE_MANIFEST.json",
})
_LEGACY_FORBIDDEN_CAPABILITIES = frozenset({
    "external_network", "package_install", "shell", "arbitrary_subprocess",
    "host_write_outside_temp", "production_mutation", "secret_access",
    "raw_private_memory", "commit", "push", "pr", "booking_payment",
    "permanent_plugin_install", "automatic_crystallization",
})
_LEGACY_RESOURCE_FIELDS = frozenset({
    "wall_time_ms", "memory_mb", "output_bytes", "tool_calls", "model_calls",
    "cost_usd", "network_calls",
})


def _canonical(value: Any, *, _depth: int = 0) -> Any:
    """Return a lossless bounded canonical JSON value or reject ambiguous input."""
    if _depth > MAX_CANONICAL_DEPTH:
        raise ValueError("canonical JSON nesting exceeds its depth ceiling")
    next_depth = _depth + 1
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return _canonical(value.to_dict(), _depth=next_depth)
        return _canonical(asdict(value), _depth=next_depth)
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return {
            key: _canonical(value[key], _depth=next_depth)
            for key in sorted(value)
        }
    if isinstance(value, (list, tuple)):
        return [_canonical(item, _depth=next_depth) for item in value]
    if isinstance(value, (set, frozenset)):
        raise ValueError("sets are not JSON values")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are prohibited")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(f"non-JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a value to deterministic compact JSON."""
    return json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def stable_digest(value: Any) -> str:
    """Return the 64-character BLAKE2b-256 digest of canonical JSON."""
    return hashlib.blake2b(canonical_json(value).encode("utf-8"), digest_size=32).hexdigest()


def _text(value: Any, name: str, *, optional: bool = False, maximum: int = MAX_TEXT_BYTES) -> str:
    """Validate canonical bounded text without coercion or whitespace folding."""
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    if not value and not optional:
        raise ValueError(f"{name} is required")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must contain valid Unicode scalar values") from exc
    if len(encoded) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} exceeds its bounded text contract")
    return value


def _id(value: Any, name: str) -> str:
    """Validate an Aura identifier."""
    result = _text(value, name, maximum=192)
    if not _ID.fullmatch(result):
        raise ValueError(f"{name} contains unsupported characters")
    return result


def _digest(value: Any, name: str, *, optional: bool = False) -> str:
    """Validate an exact lowercase BLAKE2b-256 digest."""
    result = _text(value, name, optional=optional, maximum=64)
    if result and not _DIGEST.fullmatch(result):
        raise ValueError(f"{name} must be 64 lowercase hex characters")
    return result


def _legacy_digest(value: Any, name: str) -> str:
    """Validate the retained lowercase 32-character V1 manifest digest."""
    result = _text(value, name, maximum=32)
    if not _LEGACY_DIGEST.fullmatch(result):
        raise ValueError(f"{name} must be a 32-character lowercase V1 digest")
    return result


def _commit_sha(value: Any, name: str) -> str:
    """Validate a complete lowercase Git SHA-1 or SHA-256 object identifier."""
    result = _text(value, name, maximum=64)
    if not _COMMIT_SHA.fullmatch(result):
        raise ValueError(f"{name} must be a complete 40- or 64-character lowercase Git object ID")
    return result


def _capability_resolution_digest(value: Any, name: str) -> str:
    """Validate the canonical resolver's optional BLAKE2b-64 CODEMAP digest."""
    result = _text(value, name, optional=True, maximum=16)
    if result and not _CAPABILITY_RESOLUTION_DIGEST.fullmatch(result):
        raise ValueError(f"{name} must be a 16-character lowercase resolver digest")
    return result


def _finite_number(value: Any, name: str, *, minimum: float = 0.0) -> float:
    """Validate a finite non-boolean numeric value at or above a minimum."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite JSON number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite JSON number") from exc
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{name} must be a finite number >= {minimum}")
    return number


def _bool(value: Any, name: str, required: bool) -> bool:
    """Require an exact boolean value."""
    if not isinstance(value, bool) or value is not required:
        raise ValueError(f"{name} must be {str(required).lower()}")
    return value


def _int(value: Any, name: str, low: int, high: int) -> int:
    """Validate a bounded integer while rejecting booleans."""
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")
    return value


def _prob(value: Any, name: str) -> int | float:
    """Validate an exact JSON numeric spelling in the inclusive unit interval."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} must be between 0 and 1")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def _seq(value: Any, name: str, *, ids: bool = False, max_items: int = MAX_ITEMS, sort: bool = False, upper: bool = False) -> tuple[str, ...]:
    """Validate a bounded unique string sequence after normalization."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(value) > max_items:
        raise ValueError(f"{name} exceeds its item ceiling")
    normalized = []
    for item in value:
        text = _id(item, f"{name}[]") if ids else _text(item, f"{name}[]")
        if upper and text != text.upper():
            raise ValueError(f"{name} values must already use uppercase canonical spelling")
        normalized.append(text)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} values must be unique")
    result = tuple(normalized)
    return tuple(sorted(result)) if sort else result


def _metadata(value: Any, name: str) -> tuple[tuple[str, Any], ...]:
    """Validate and recursively freeze the closed scalar metadata contract."""
    if value is None or value == ():
        return ()
    if isinstance(value, tuple):
        pairs: list[tuple[str, Any]] = []
        for item in value:
            if (
                isinstance(item, (str, bytes, bytearray))
                or not isinstance(item, Sequence)
                or len(item) != 2
            ):
                raise ValueError(f"{name} entries must be key/value pairs")
            key = item[0]
            if not isinstance(key, str):
                raise ValueError(f"{name} keys must be strings")
            pairs.append((key, item[1]))
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError(f"{name} keys must be unique")
        candidate = dict(pairs)
    elif isinstance(value, Mapping):
        candidate = dict(value)
    else:
        raise ValueError(f"{name} must be an object")
    if any(not isinstance(key, str) for key in candidate):
        raise ValueError(f"{name} keys must be strings")
    unknown = set(candidate) - _METADATA_FIELDS
    if unknown:
        raise ValueError(f"{name} contains unsupported fields: {sorted(unknown)}")
    validated = {}
    for key, item in candidate.items():
        field_name = f"{name}.{key}"
        if key == "manifest_version":
            validated[key] = _id(item, field_name)
        elif key in _METADATA_TEXT_FIELDS:
            validated[key] = _text(item, field_name, maximum=4096)
        elif key in _METADATA_BOOL_FIELDS:
            validated[key] = _bool(item, field_name, True)
        elif key in _METADATA_INT_FIELDS:
            validated[key] = _int(item, field_name, 0, MAX_INTEGER)
        elif key == "legacy_manifest_digest":
            validated[key] = _legacy_digest(item, field_name)
        else:
            validated[key] = _digest(item, field_name)
    if len(canonical_json(validated).encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError(f"{name} exceeds its byte ceiling")
    return tuple(sorted(validated.items()))


def _strict(payload: Mapping[str, Any], expected: set[str], name: str) -> None:
    """Require an exact mapping key set."""
    if not isinstance(payload, Mapping):
        raise ValueError(f"{name} must be an object")
    keys = tuple(payload)
    if any(not isinstance(key, str) for key in keys):
        raise ValueError(f"{name} keys must be strings")
    supplied = set(keys)
    if supplied != expected:
        raise ValueError(f"{name} keys mismatch: missing={sorted(expected-supplied)}, extra={sorted(supplied-expected)}")


def _set_record_digest(record: Any, field_name: str) -> None:
    """Compute a record digest or verify a non-empty supplied digest."""
    body = record.to_dict()
    supplied = _digest(body.pop(field_name, ""), field_name, optional=True)
    expected = stable_digest(body)
    if supplied and supplied != expected:
        raise ValueError(f"{field_name} does not match canonical bytes")
    object.__setattr__(record, field_name, expected)


def _require_serialized_digest(payload: Mapping[str, Any], field_name: str, name: str) -> None:
    """Require deserialized records to carry their original integrity digest."""
    if not isinstance(payload, Mapping):
        raise ValueError(f"{name} must be an object")
    _digest(payload.get(field_name), f"{name}.{field_name}")


def _require_exact_serialized_form(record: Any, payload: Mapping[str, Any]) -> None:
    """Reject payloads that normalize to a different public serialized record."""
    if record.to_dict() != dict(payload):
        raise ValueError(
            f"{type(record).__name__} must use canonical serialized ordering and spelling"
        )


@dataclass(frozen=True)
class AuthorityEnvelope:
    """A fixed false-authority envelope for projection-only records."""
    version: str = AUTHORITY_ENVELOPE_VERSION
    projection_only: bool = True
    review_only: bool = True
    human_review_required: bool = True
    source_mutation: bool = False
    domain_mutation: bool = False
    production_mutation: bool = False
    renderer_authority: bool = False
    sensor_authority: bool = False
    model_authority: bool = False
    execution_authority: bool = False
    persistence_authority: bool = False
    deployment_authority: bool = False
    physical_work_authority: bool = False
    payment_authority: bool = False
    professional_authority: bool = False
    patch_authority: bool = False
    vsa_patch_authority: bool = False
    automatic_persistence: bool = False
    automatic_resume: bool = False
    automatic_promotion: bool = False
    automatic_commit: bool = False
    automatic_push: bool = False
    automatic_pull_request: bool = False
    automatic_merge: bool = False

    def __post_init__(self) -> None:
        """Validate every fixed authority bit."""
        if self.version != AUTHORITY_ENVELOPE_VERSION:
            raise ValueError("unsupported authority version")
        true_fields = {"projection_only", "review_only", "human_review_required"}
        for field in fields(self):
            if field.name != "version":
                _bool(getattr(self, field.name), f"authority.{field.name}", field.name in true_fields)

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible authority mapping."""
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthorityEnvelope":
        """Parse an exact serialized authority envelope."""
        _strict(payload, {field.name for field in fields(cls)}, "authority")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record


@dataclass(frozen=True)
class CanonicalReference:
    """A digest-bound reference to an existing canonical Aura owner."""
    reference_id: str
    owner: str
    canonical_ref: str
    digest: str
    truth_class: str = "EXACT"
    freshness_class: str = "CURRENT"
    metadata: Mapping[str, Any] | tuple[tuple[str, Any], ...] = ()
    version: str = CANONICAL_REFERENCE_VERSION

    def __post_init__(self) -> None:
        """Validate identity, ownership, freshness, and closed metadata."""
        object.__setattr__(self, "reference_id", _id(self.reference_id, "reference.reference_id"))
        object.__setattr__(self, "owner", _id(self.owner, "reference.owner"))
        object.__setattr__(self, "canonical_ref", _text(self.canonical_ref, "reference.canonical_ref"))
        object.__setattr__(self, "digest", _digest(self.digest, "reference.digest"))
        if self.truth_class not in _TRUTH or self.freshness_class not in _FRESHNESS:
            raise ValueError("unsupported reference class")
        object.__setattr__(self, "metadata", _metadata(self.metadata, "reference.metadata"))
        if self.version != CANONICAL_REFERENCE_VERSION:
            raise ValueError("unsupported reference version")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible reference mapping."""
        return {"version": self.version, "reference_id": self.reference_id, "owner": self.owner,
                "canonical_ref": self.canonical_ref, "digest": self.digest,
                "truth_class": self.truth_class, "freshness_class": self.freshness_class,
                "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalReference":
        """Parse an exact serialized canonical reference."""
        _strict(payload, {"version", "reference_id", "owner", "canonical_ref", "digest", "truth_class", "freshness_class", "metadata"}, "reference")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record


def _reference_map(value: Any, name: str) -> dict[str, CanonicalReference]:
    """Parse a complete identifier-to-canonical-reference mapping."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} is required")
    result: dict[str, CanonicalReference] = {}
    for supplied_id, raw_reference in value.items():
        reference_id = _id(supplied_id, f"{name} key")
        reference = raw_reference if isinstance(raw_reference, CanonicalReference) else CanonicalReference.from_dict(raw_reference)
        if reference_id != reference.reference_id:
            raise ValueError(f"{name} key/reference mismatch: {reference_id}")
        if reference_id in result:
            raise ValueError(f"duplicate {name} reference: {reference_id}")
        result[reference_id] = reference
    return result


def _validate_reference_set(actual: Sequence[CanonicalReference], expected_value: Any,
                            name: str, *, require_current: bool = True) -> None:
    """Rebind a complete reference set, including owner and metadata identity."""
    if not isinstance(expected_value, Mapping):
        raise ValueError(f"expected_{name}_refs is required")
    if len(expected_value) != len(actual) or len(expected_value) > MAX_ITEMS:
        raise ValueError(f"{name} reference set size mismatch")
    expected = _reference_map(expected_value, f"expected_{name}_refs")
    actual_ids = [reference.reference_id for reference in actual]
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError(f"duplicate {name} reference IDs")
    current = {reference.reference_id: reference for reference in actual}
    if set(current) != set(expected):
        raise ValueError(f"{name} reference set mismatch")
    for reference_id in sorted(current):
        if current[reference_id].to_dict() != expected[reference_id].to_dict():
            raise ValueError(f"stale {name} canonical reference: {reference_id}")
        if require_current and current[reference_id].freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError(f"stale {name} canonical reference: {reference_id}")


@dataclass(frozen=True)
class RepositoryIdentity:
    """An exact repository, ref, commit, and source-tree identity."""
    repository: str
    ref: str
    commit_sha: str
    source_tree_digest: str
    identity_digest: str = ""
    version: str = REPOSITORY_IDENTITY_VERSION

    def __post_init__(self) -> None:
        """Validate the complete Git and source-tree identity."""
        repository = _text(self.repository, "repository.repository", maximum=256)
        if not _REPO.fullmatch(repository):
            raise ValueError("repository must be owner/name")
        object.__setattr__(self, "repository", repository)
        object.__setattr__(self, "ref", _text(self.ref, "repository.ref", maximum=256))
        object.__setattr__(self, "commit_sha", _commit_sha(self.commit_sha, "repository.commit_sha"))
        object.__setattr__(self, "source_tree_digest", _digest(self.source_tree_digest, "repository.source_tree_digest"))
        if self.version != REPOSITORY_IDENTITY_VERSION:
            raise ValueError("unsupported repository identity version")
        _set_record_digest(self, "identity_digest")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible repository identity."""
        return {"version": self.version, "repository": self.repository, "ref": self.ref,
                "commit_sha": self.commit_sha, "source_tree_digest": self.source_tree_digest,
                "identity_digest": self.identity_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RepositoryIdentity":
        """Parse and verify an exact serialized repository identity."""
        _strict(payload, {"version", "repository", "ref", "commit_sha", "source_tree_digest", "identity_digest"}, "repository")
        _require_serialized_digest(payload, "identity_digest", "repository")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record


_REFERENCE_FIELDS = ("artifact_evidence_refs", "decision_refs", "rejected_alternative_refs",
                     "unresolved_question_refs", "assumption_refs", "capability_refs",
                     "relationship_refs", "blocker_refs", "next_action_refs")


@dataclass(frozen=True)
class ProjectContextProjection:
    """A minimum-sufficient projection of project truth by exact references."""
    projection_id: str
    project_ref: str
    canonical_owner: str
    objective_digest: str
    purpose_digest: str
    repository_identity: RepositoryIdentity
    artifact_evidence_refs: tuple[CanonicalReference, ...]
    decision_refs: tuple[CanonicalReference, ...] = ()
    rejected_alternative_refs: tuple[CanonicalReference, ...] = ()
    unresolved_question_refs: tuple[CanonicalReference, ...] = ()
    assumption_refs: tuple[CanonicalReference, ...] = ()
    capability_refs: tuple[CanonicalReference, ...] = ()
    relationship_refs: tuple[CanonicalReference, ...] = ()
    blocker_refs: tuple[CanonicalReference, ...] = ()
    next_action_refs: tuple[CanonicalReference, ...] = ()
    freshness_timestamp_ms: int = 0
    freshness_class: str = "CURRENT"
    completeness_warnings: tuple[str, ...] = ()
    privacy_class: str = _PROJECT_PRIVACY_CLASS
    egress_class: str = _PROJECT_EGRESS_CLASS
    projection_only: bool = True
    authority: AuthorityEnvelope = AuthorityEnvelope()
    projection_digest: str = ""
    version: str = PROJECT_CONTEXT_PROJECTION_VERSION

    def __post_init__(self) -> None:
        """Validate bounded references and the fixed privacy profile."""
        object.__setattr__(self, "projection_id", _id(self.projection_id, "project.projection_id"))
        object.__setattr__(self, "project_ref", _text(self.project_ref, "project.project_ref"))
        object.__setattr__(self, "canonical_owner", _id(self.canonical_owner, "project.canonical_owner"))
        object.__setattr__(self, "objective_digest", _digest(self.objective_digest, "project.objective_digest"))
        object.__setattr__(self, "purpose_digest", _digest(self.purpose_digest, "project.purpose_digest"))
        if not isinstance(self.repository_identity, RepositoryIdentity):
            object.__setattr__(self, "repository_identity", RepositoryIdentity.from_dict(self.repository_identity))
        seen: set[str] = set()
        for name in _REFERENCE_FIELDS:
            raw = getattr(self, name)
            if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence) or len(raw) > MAX_ITEMS:
                raise ValueError(f"project.{name} must be a bounded sequence")
            refs = tuple(item if isinstance(item, CanonicalReference) else CanonicalReference.from_dict(item) for item in raw)
            for reference in refs:
                if reference.reference_id in seen:
                    raise ValueError(f"duplicate project reference: {reference.reference_id}")
                seen.add(reference.reference_id)
            object.__setattr__(self, name, tuple(sorted(refs, key=lambda item: item.reference_id)))
        if not self.artifact_evidence_refs:
            raise ValueError("artifact_evidence_refs must not be empty")
        object.__setattr__(self, "freshness_timestamp_ms", _int(self.freshness_timestamp_ms, "project.freshness_timestamp_ms", 0, MAX_TIMESTAMP))
        if self.freshness_class not in _FRESHNESS:
            raise ValueError("unsupported project freshness")
        object.__setattr__(self, "completeness_warnings", _seq(self.completeness_warnings, "project.completeness_warnings", max_items=128, sort=True))
        if self.privacy_class != _PROJECT_PRIVACY_CLASS:
            raise ValueError(f"project.privacy_class must be {_PROJECT_PRIVACY_CLASS}")
        if self.egress_class != _PROJECT_EGRESS_CLASS:
            raise ValueError(f"project.egress_class must be {_PROJECT_EGRESS_CLASS}")
        _bool(self.projection_only, "project.projection_only", True)
        if not isinstance(self.authority, AuthorityEnvelope):
            object.__setattr__(self, "authority", AuthorityEnvelope.from_dict(self.authority))
        if self.version != PROJECT_CONTEXT_PROJECTION_VERSION:
            raise ValueError("unsupported project version")
        _set_record_digest(self, "projection_digest")

    def all_references(self) -> tuple[CanonicalReference, ...]:
        """Return all project references in deterministic category order."""
        return tuple(item for name in _REFERENCE_FIELDS for item in getattr(self, name))

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible project projection."""
        result = {"version": self.version, "projection_id": self.projection_id,
                  "project_ref": self.project_ref, "canonical_owner": self.canonical_owner,
                  "objective_digest": self.objective_digest, "purpose_digest": self.purpose_digest,
                  "repository_identity": self.repository_identity.to_dict(),
                  "freshness_timestamp_ms": self.freshness_timestamp_ms,
                  "freshness_class": self.freshness_class,
                  "completeness_warnings": list(self.completeness_warnings),
                  "privacy_class": self.privacy_class, "egress_class": self.egress_class,
                  "projection_only": self.projection_only, "authority": self.authority.to_dict(),
                  "projection_digest": self.projection_digest}
        result.update({name: [item.to_dict() for item in getattr(self, name)] for name in _REFERENCE_FIELDS})
        return result

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProjectContextProjection":
        """Parse and verify an exact serialized project projection."""
        _strict(payload, {"version", "projection_id", "project_ref", "canonical_owner",
                          "objective_digest", "purpose_digest", "repository_identity",
                          "freshness_timestamp_ms", "freshness_class", "completeness_warnings",
                          "privacy_class", "egress_class", "projection_only", "authority",
                          "projection_digest", *_REFERENCE_FIELDS}, "project")
        _require_serialized_digest(payload, "projection_digest", "project")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record

    def validate_bindings(
        self,
        *,
        expected_projection: "ProjectContextProjection" | Mapping[str, Any],
        reject_stale: bool = True,
    ) -> None:
        """Rebind every projection field to one complete canonical expectation."""
        if reject_stale and (
            self.freshness_class not in _CURRENT_FRESHNESS
            or any(
                reference.freshness_class not in _CURRENT_FRESHNESS
                for reference in self.all_references()
            )
        ):
            raise ValueError("stale or unknown project projection")
        expected = (
            expected_projection
            if isinstance(expected_projection, ProjectContextProjection)
            else ProjectContextProjection.from_dict(expected_projection)
        )
        if self.to_dict() != expected.to_dict():
            raise ValueError("stale project projection identity")


@dataclass(frozen=True)
class WorkspaceBudget:
    """Bounded resource declarations for a non-operational recipe."""
    wall_time_ms: int = 300_000
    memory_mb: int = 512
    context_tokens: int = 64_000
    output_bytes: int = 4_000_000
    tool_calls: int = 64
    model_calls: int = 8
    cost_microusd: int = 0
    network_calls: int = 0
    device_events: int = 100_000

    def __post_init__(self) -> None:
        """Validate every resource as a bounded integer."""
        for field in fields(self):
            object.__setattr__(self, field.name, _int(getattr(self, field.name), f"budget.{field.name}", 0, MAX_INTEGER))

    def to_dict(self) -> dict[str, int]:
        """Return a detached JSON-compatible budget."""
        return {field.name: getattr(self, field.name) for field in fields(self)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WorkspaceBudget":
        """Parse an exact serialized workspace budget."""
        _strict(payload, {field.name for field in fields(cls)}, "budget")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record


@dataclass(frozen=True)
class DependencyEdge:
    """A directed capability dependency within a bounded recipe graph."""
    source_capability_id: str
    target_capability_id: str

    def __post_init__(self) -> None:
        """Validate endpoints and reject self-dependencies."""
        object.__setattr__(self, "source_capability_id", _id(self.source_capability_id, "dependency.source"))
        object.__setattr__(self, "target_capability_id", _id(self.target_capability_id, "dependency.target"))
        if self.source_capability_id == self.target_capability_id:
            raise ValueError("self dependency is prohibited")

    def to_dict(self) -> dict[str, str]:
        """Return the serialized dependency edge."""
        return {"source_capability_id": self.source_capability_id, "target_capability_id": self.target_capability_id}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DependencyEdge":
        """Parse an exact serialized dependency edge."""
        _strict(payload, {"source_capability_id", "target_capability_id"}, "dependency")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record


def _acyclic(nodes: Sequence[str], edges: Sequence[DependencyEdge]) -> None:
    """Reject dependency cycles with deterministic topological traversal."""
    graph = {node: [] for node in nodes}
    degree = {node: 0 for node in nodes}
    for edge in edges:
        graph[edge.source_capability_id].append(edge.target_capability_id)
        degree[edge.target_capability_id] += 1
    queue = sorted(node for node in nodes if degree[node] == 0)
    count = 0
    while queue:
        current = queue.pop(0)
        count += 1
        for target in graph[current]:
            degree[target] -= 1
            if degree[target] == 0:
                queue.append(target)
                queue.sort()
    if count != len(nodes):
        raise ValueError("recipe dependency graph contains a cycle")


def _refs(value: Any, name: str, *, require_current: bool = False) -> tuple[CanonicalReference, ...]:
    """Validate and canonicalize a non-empty reference set."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence) or not value or len(value) > MAX_ITEMS:
        raise ValueError(f"{name} must be a non-empty bounded sequence")
    result = tuple(item if isinstance(item, CanonicalReference) else CanonicalReference.from_dict(item) for item in value)
    if len({item.reference_id for item in result}) != len(result):
        raise ValueError(f"duplicate {name} IDs")
    if any(item.truth_class != "EXACT" for item in result):
        raise ValueError(f"{name} must contain only EXACT canonical references")
    if require_current and any(item.freshness_class not in _CURRENT_FRESHNESS for item in result):
        raise ValueError(f"{name} must contain only current or bounded references")
    return tuple(sorted(result, key=lambda item: (item.reference_id, item.owner, item.digest)))


def _owner_map(value: Any) -> tuple[tuple[str, str], ...]:
    """Validate and canonicalize the domain-owner handoff map."""
    if isinstance(value, Mapping):
        items = value.items()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = value
    else:
        raise ValueError("handoff map must be an object or pair sequence")
    pairs = []
    for item in items:
        if isinstance(item, (str, bytes, bytearray)) or not isinstance(item, Sequence) or len(item) != 2:
            raise ValueError("handoff map entries must be key/owner pairs")
        pairs.append((_id(item[0], "handoff key"), _id(item[1], "handoff owner")))
    result = tuple(sorted(pairs))
    if not result or len({key for key, _ in result}) != len(result):
        raise ValueError("handoff map must be non-empty and unique")
    return result


_FROZEN_DEFINITION = MappingProxyType({
    "demonstration_id": CODING_SPATIAL_WORKSPACE_V1,
    "capability_ids": ("compile_compass_packet", "fetch_bounded_neighborhood", "open_exact_source_slice", "display_tests_and_schemas", "compile_candidate_change_graph", "prepare_forge_handoff", "read_verification_status", "display_attempt_archive_evidence", "dissolve_workspace"),
    "dependency_edges": (("compile_compass_packet", "fetch_bounded_neighborhood"), ("fetch_bounded_neighborhood", "open_exact_source_slice"), ("fetch_bounded_neighborhood", "display_tests_and_schemas"), ("fetch_bounded_neighborhood", "compile_candidate_change_graph"), ("compile_candidate_change_graph", "prepare_forge_handoff"), ("prepare_forge_handoff", "read_verification_status"), ("read_verification_status", "display_attempt_archive_evidence"), ("display_attempt_archive_evidence", "dissolve_workspace")),
    "domain_owner_handoff_map": (("architecture", "aura_coding_relationship_compass"), ("code_candidate", "aura_forge"), ("continuity", "aura_unified_memory_continuity"), ("dissolution", "aura_ephemeral_runtime"), ("runtime_proof", "aura_runtime_refactor_harness"), ("semantic_review", "aura_coding_waboose")),
    "renderer_requirements": ("ACCESSIBLE_2D_REQUIRED", "WEBGL2_OPTIONAL", "WEBXR_OPTIONAL"),
    "device_requirements": ("KEYBOARD_REQUIRED", "POINTER_OPTIONAL", "XR_OPTIONAL"),
    "allowed_interaction_actions": ("SELECT", "DESELECT", "EXPAND", "CONTRACT", "FOCUS", "OPEN_SOURCE", "ISOLATE", "COMPARE", "REQUEST_RELATIONAL_SYNTHESIS", "REQUEST_SIMULATION", "DISMISS_CANDIDATE", "PREPARE_REPAIR_REQUEST", "PREPARE_DOMAIN_HANDOFF", "CONFIRM_HANDOFF"),
    "required_verification_gates": ("EXACT_REPOSITORY_IDENTITY", "EXACT_PROJECT_PROJECTION", "ADAPTER_IDENTITY", "EVIDENCE_FRESHNESS", "AUTHORITY_NON_ESCALATION", "NO_PRODUCTION_MUTATION", "MANDATORY_DISSOLUTION"),
})
CODING_SPATIAL_WORKSPACE_V1_DEFINITION = _FROZEN_DEFINITION


def _validate_manifest_reference_metadata(reference: CanonicalReference) -> None:
    """Require the exact V1 wrapper metadata carried by a manifest reference."""
    metadata = dict(reference.metadata)
    expected_fields = {
        "manifest_version", "legacy_manifest_digest", "wrapped_not_replaced",
    }
    if set(metadata) != expected_fields:
        raise ValueError("base manifest reference metadata is incomplete")
    if metadata["manifest_version"] != LEGACY_EPHEMERAL_MANIFEST_VERSION:
        raise ValueError("base manifest reference metadata version is invalid")
    _legacy_digest(
        metadata["legacy_manifest_digest"],
        "base manifest reference metadata legacy_manifest_digest",
    )
    _bool(
        metadata["wrapped_not_replaced"],
        "base manifest reference metadata wrapped_not_replaced",
        True,
    )


@dataclass(frozen=True)
class EphemeralWorkspaceRecipe:
    """An immutable compatibility recipe over an exact V1 organ manifest."""
    recipe_id: str
    demonstration_id: str
    base_manifest_ref: CanonicalReference
    canonical_intent_digest: str
    project_projection_id: str
    project_projection_digest: str
    capability_ids: tuple[str, ...]
    dependency_edges: tuple[DependencyEdge, ...]
    adapter_refs: tuple[CanonicalReference, ...]
    evidence_refs: tuple[CanonicalReference, ...]
    domain_owner_handoff_map: tuple[tuple[str, str], ...]
    budgets: WorkspaceBudget
    renderer_requirements: tuple[str, ...]
    device_requirements: tuple[str, ...]
    allowed_interaction_actions: tuple[str, ...]
    required_verification_gates: tuple[str, ...]
    ttl_seconds: int = 300
    lifecycle_policy: str = _LIFECYCLE_POLICY
    dissolution_policy: str = _DISSOLUTION_POLICY
    automatic_persistence: bool = False
    automatic_resume: bool = False
    automatic_promotion: bool = False
    authority: AuthorityEnvelope = AuthorityEnvelope()
    recipe_digest: str = ""
    version: str = EPHEMERAL_WORKSPACE_RECIPE_VERSION

    def __post_init__(self) -> None:
        """Validate graph, owners, lifecycle, resources, and frozen profile."""
        object.__setattr__(self, "recipe_id", _id(self.recipe_id, "recipe.recipe_id"))
        object.__setattr__(self, "demonstration_id", _id(self.demonstration_id, "recipe.demonstration_id"))
        if not isinstance(self.base_manifest_ref, CanonicalReference):
            object.__setattr__(self, "base_manifest_ref", CanonicalReference.from_dict(self.base_manifest_ref))
        if self.base_manifest_ref.owner != "aura_ephemeral_manifest" or self.base_manifest_ref.truth_class != "EXACT" or self.base_manifest_ref.freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError("base manifest reference must be exact, current, and canonically owned")
        _validate_manifest_reference_metadata(self.base_manifest_ref)
        object.__setattr__(self, "canonical_intent_digest", _digest(self.canonical_intent_digest, "recipe.intent"))
        object.__setattr__(self, "project_projection_id", _id(self.project_projection_id, "recipe.project_id"))
        object.__setattr__(self, "project_projection_digest", _digest(self.project_projection_digest, "recipe.project_digest"))
        capabilities = _seq(self.capability_ids, "recipe.capabilities", ids=True, max_items=128)
        object.__setattr__(self, "capability_ids", capabilities)
        allowed = set(capabilities)
        if isinstance(self.dependency_edges, (str, bytes, bytearray)) or not isinstance(self.dependency_edges, Sequence) or len(self.dependency_edges) > MAX_DEPENDENCY_EDGES:
            raise ValueError("recipe.dependency_edges must be a bounded sequence")
        edges = tuple(edge if isinstance(edge, DependencyEdge) else DependencyEdge.from_dict(edge) for edge in self.dependency_edges)
        if len({(edge.source_capability_id, edge.target_capability_id) for edge in edges}) != len(edges):
            raise ValueError("duplicate recipe dependency")
        if any(edge.source_capability_id not in allowed or edge.target_capability_id not in allowed for edge in edges):
            raise ValueError("invalid recipe dependency")
        _acyclic(capabilities, edges)
        object.__setattr__(self, "dependency_edges", tuple(sorted(edges, key=lambda edge: (edge.source_capability_id, edge.target_capability_id))))
        adapters = _refs(self.adapter_refs, "adapter_refs", require_current=True)
        evidence = _refs(self.evidence_refs, "evidence_refs", require_current=True)
        if {item.reference_id for item in adapters} & {item.reference_id for item in evidence}:
            raise ValueError("duplicate recipe reference IDs across adapter and evidence roles")
        object.__setattr__(self, "adapter_refs", adapters)
        object.__setattr__(self, "evidence_refs", evidence)
        object.__setattr__(self, "domain_owner_handoff_map", _owner_map(self.domain_owner_handoff_map))
        if not isinstance(self.budgets, WorkspaceBudget):
            object.__setattr__(self, "budgets", WorkspaceBudget.from_dict(self.budgets))
        for name, ids, limit, sort_values in (("renderer_requirements", False, 32, True), ("device_requirements", False, 32, True), ("allowed_interaction_actions", True, 64, False), ("required_verification_gates", True, 64, False)):
            object.__setattr__(self, name, _seq(getattr(self, name), f"recipe.{name}", ids=ids, max_items=limit, sort=sort_values))
        object.__setattr__(self, "ttl_seconds", _int(self.ttl_seconds, "recipe.ttl", 1, MAX_TTL_SECONDS))
        if self.budgets.wall_time_ms > self.ttl_seconds * 1000:
            raise ValueError("budget.wall_time_ms cannot exceed recipe TTL")
        if self.lifecycle_policy != _LIFECYCLE_POLICY:
            raise ValueError(f"recipe.lifecycle_policy must be {_LIFECYCLE_POLICY}")
        if self.dissolution_policy != _DISSOLUTION_POLICY:
            raise ValueError(f"recipe.dissolution_policy must be {_DISSOLUTION_POLICY}")
        for name in ("automatic_persistence", "automatic_resume", "automatic_promotion"):
            _bool(getattr(self, name), f"recipe.{name}", False)
        if not isinstance(self.authority, AuthorityEnvelope):
            object.__setattr__(self, "authority", AuthorityEnvelope.from_dict(self.authority))
        if self.version != EPHEMERAL_WORKSPACE_RECIPE_VERSION:
            raise ValueError("unsupported recipe version")
        self._validate_frozen_demonstration()
        _set_record_digest(self, "recipe_digest")

    def _validate_frozen_demonstration(self) -> None:
        """Require exact frozen capability, owner, interaction, and gate profile."""
        if self.demonstration_id != CODING_SPATIAL_WORKSPACE_V1:
            raise ValueError("unsupported workspace demonstration")
        expected_edges = tuple(sorted((DependencyEdge(source, target) for source, target in _FROZEN_DEFINITION["dependency_edges"]), key=lambda edge: (edge.source_capability_id, edge.target_capability_id)))
        checks = ((self.capability_ids, _FROZEN_DEFINITION["capability_ids"], "capability profile"), (self.dependency_edges, expected_edges, "dependency graph"), (self.domain_owner_handoff_map, _FROZEN_DEFINITION["domain_owner_handoff_map"], "handoff owners"), (self.renderer_requirements, tuple(sorted(_FROZEN_DEFINITION["renderer_requirements"])), "renderer requirements"), (self.device_requirements, tuple(sorted(_FROZEN_DEFINITION["device_requirements"])), "device requirements"), (self.allowed_interaction_actions, _FROZEN_DEFINITION["allowed_interaction_actions"], "interaction actions"), (self.required_verification_gates, _FROZEN_DEFINITION["required_verification_gates"], "verification gates"))
        for actual, expected, name in checks:
            if actual != expected:
                raise ValueError(f"frozen {name} mismatch")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible workspace recipe."""
        return {"version": self.version, "recipe_id": self.recipe_id,
                "demonstration_id": self.demonstration_id,
                "base_manifest_ref": self.base_manifest_ref.to_dict(),
                "canonical_intent_digest": self.canonical_intent_digest,
                "project_projection_id": self.project_projection_id,
                "project_projection_digest": self.project_projection_digest,
                "capability_ids": list(self.capability_ids),
                "dependency_edges": [edge.to_dict() for edge in self.dependency_edges],
                "adapter_refs": [reference.to_dict() for reference in self.adapter_refs],
                "evidence_refs": [reference.to_dict() for reference in self.evidence_refs],
                "domain_owner_handoff_map": dict(self.domain_owner_handoff_map),
                "budgets": self.budgets.to_dict(),
                "renderer_requirements": list(self.renderer_requirements),
                "device_requirements": list(self.device_requirements),
                "allowed_interaction_actions": list(self.allowed_interaction_actions),
                "required_verification_gates": list(self.required_verification_gates),
                "ttl_seconds": self.ttl_seconds,
                "lifecycle_policy": self.lifecycle_policy,
                "dissolution_policy": self.dissolution_policy,
                "automatic_persistence": self.automatic_persistence,
                "automatic_resume": self.automatic_resume,
                "automatic_promotion": self.automatic_promotion,
                "authority": self.authority.to_dict(), "recipe_digest": self.recipe_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EphemeralWorkspaceRecipe":
        """Parse and verify an exact serialized workspace recipe."""
        expected = {"version", "recipe_id", "demonstration_id", "base_manifest_ref",
                    "canonical_intent_digest", "project_projection_id", "project_projection_digest",
                    "capability_ids", "dependency_edges", "adapter_refs", "evidence_refs",
                    "domain_owner_handoff_map", "budgets", "renderer_requirements",
                    "device_requirements", "allowed_interaction_actions",
                    "required_verification_gates", "ttl_seconds", "lifecycle_policy",
                    "dissolution_policy", "automatic_persistence", "automatic_resume",
                    "automatic_promotion", "authority", "recipe_digest"}
        _strict(payload, expected, "recipe")
        _require_serialized_digest(payload, "recipe_digest", "recipe")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        identity_body = record.to_dict()
        identity_body.pop("recipe_id")
        identity_body.pop("recipe_digest")
        if record.recipe_id != _compiled_recipe_id(identity_body):
            raise ValueError("recipe.recipe_id does not match behavior-defining content")
        return record

    def validate_bindings(self, *, expected_intent_digest: str,
                          expected_project_projection_id: str,
                          expected_project_projection_digest: str,
                          expected_base_manifest_ref: CanonicalReference | Mapping[str, Any],
                          expected_adapter_refs: Mapping[str, CanonicalReference | Mapping[str, Any]],
                          expected_evidence_refs: Mapping[str, CanonicalReference | Mapping[str, Any]],
                          expected_recipe: "EphemeralWorkspaceRecipe" | Mapping[str, Any] | None = None) -> None:
        """Rebind the complete recipe to current manifest, project, and dependencies."""
        if self.canonical_intent_digest != _digest(expected_intent_digest, "expected intent"):
            raise ValueError("stale canonical intent digest")
        if self.project_projection_id != _id(expected_project_projection_id, "expected project projection id"):
            raise ValueError("stale project projection id")
        if self.project_projection_digest != _digest(expected_project_projection_digest, "expected project projection"):
            raise ValueError("stale project projection digest")
        expected_manifest = expected_base_manifest_ref if isinstance(expected_base_manifest_ref, CanonicalReference) else CanonicalReference.from_dict(expected_base_manifest_ref)
        if self.base_manifest_ref.to_dict() != expected_manifest.to_dict():
            raise ValueError("stale base manifest canonical reference")
        if self.base_manifest_ref.freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError("stale base manifest canonical reference")
        _validate_reference_set(self.adapter_refs, expected_adapter_refs, "adapter")
        _validate_reference_set(self.evidence_refs, expected_evidence_refs, "evidence")
        if expected_recipe is None:
            raise ValueError("expected_recipe is required")
        expected = (
            expected_recipe
            if isinstance(expected_recipe, EphemeralWorkspaceRecipe)
            else EphemeralWorkspaceRecipe.from_dict(expected_recipe)
        )
        if self.to_dict() != expected.to_dict():
            raise ValueError("stale complete recipe identity")


@dataclass(frozen=True)
class SpatialReferentBinding:
    """An exact scene, session, entity, and evidence referent candidate."""
    binding_id: str
    scene_id: str
    scene_digest: str
    session_id: str
    session_digest: str
    entity_id: str
    entity_digest: str
    confidence: int | float
    evidence_ref: CanonicalReference
    input_sources: tuple[str, ...]
    binding_digest: str = ""
    version: str = SPATIAL_REFERENT_BINDING_VERSION

    def __post_init__(self) -> None:
        """Validate exact identities, current evidence, and normalized inputs."""
        for name in ("binding_id", "scene_id", "session_id", "entity_id"):
            object.__setattr__(self, name, _id(getattr(self, name), f"referent.{name}"))
        for name in ("scene_digest", "session_digest", "entity_digest"):
            object.__setattr__(self, name, _digest(getattr(self, name), f"referent.{name}"))
        object.__setattr__(self, "confidence", _prob(self.confidence, "referent.confidence"))
        if not isinstance(self.evidence_ref, CanonicalReference):
            object.__setattr__(self, "evidence_ref", CanonicalReference.from_dict(self.evidence_ref))
        if (
            self.evidence_ref.truth_class != "EXACT"
            or self.evidence_ref.freshness_class not in _CURRENT_FRESHNESS
        ):
            raise ValueError("referent evidence must be current or bounded and EXACT")
        sources = _seq(self.input_sources, "referent.input_sources", max_items=7, sort=True, upper=True)
        if not sources or not set(sources) <= _INPUTS:
            raise ValueError("unsupported referent input source")
        object.__setattr__(self, "input_sources", sources)
        if self.version != SPATIAL_REFERENT_BINDING_VERSION:
            raise ValueError("unsupported referent version")
        _set_record_digest(self, "binding_digest")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible referent binding."""
        return {"version": self.version, "binding_id": self.binding_id,
                "scene_id": self.scene_id, "scene_digest": self.scene_digest,
                "session_id": self.session_id, "session_digest": self.session_digest,
                "entity_id": self.entity_id, "entity_digest": self.entity_digest,
                "confidence": self.confidence, "evidence_ref": self.evidence_ref.to_dict(),
                "input_sources": list(self.input_sources), "binding_digest": self.binding_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpatialReferentBinding":
        """Parse and verify an exact serialized referent binding."""
        _strict(payload, {"version", "binding_id", "scene_id", "scene_digest", "session_id",
                          "session_digest", "entity_id", "entity_digest", "confidence",
                          "evidence_ref", "input_sources", "binding_digest"}, "referent")
        _require_serialized_digest(payload, "binding_digest", "referent")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record


@dataclass(frozen=True)
class MultimodalSpatialObservation:
    """A privacy-minimized normalized multimodal observation."""
    observation_id: str
    scene_id: str
    scene_digest: str
    session_id: str
    session_digest: str
    input_sources: tuple[str, ...]
    normalized_event: str
    normalized_action: str
    target_candidates: tuple[SpatialReferentBinding, ...]
    speech_text: str = ""
    transcript_digest: str = ""
    temporal_window_start_ms: int = 0
    temporal_window_end_ms: int = 0
    provider_class: str = "LOCAL_NORMALIZED_PROVIDER"
    evidence_class: str = "DERIVED"
    tracking_quality: int | float = 0.0
    raw_sensor_retained: bool = False
    authority: AuthorityEnvelope = AuthorityEnvelope()
    observation_digest: str = ""
    version: str = MULTIMODAL_SPATIAL_OBSERVATION_VERSION

    def __post_init__(self) -> None:
        """Validate normalized inputs, target bindings, time, and transcript proof."""
        for name in ("observation_id", "scene_id", "session_id"):
            object.__setattr__(self, name, _id(getattr(self, name), f"observation.{name}"))
        for name in ("scene_digest", "session_digest"):
            object.__setattr__(self, name, _digest(getattr(self, name), f"observation.{name}"))
        sources = _seq(self.input_sources, "observation.input_sources", max_items=7, sort=True, upper=True)
        if not sources or not set(sources) <= _INPUTS:
            raise ValueError("unsupported observation input source")
        object.__setattr__(self, "input_sources", sources)
        object.__setattr__(self, "normalized_event", _id(self.normalized_event, "observation.event"))
        object.__setattr__(self, "normalized_action", _id(self.normalized_action, "observation.action"))
        if isinstance(self.target_candidates, (str, bytes, bytearray)) or not isinstance(self.target_candidates, Sequence) or not 1 <= len(self.target_candidates) <= 32:
            raise ValueError("observation requires a bounded target sequence")
        targets = tuple(item if isinstance(item, SpatialReferentBinding) else SpatialReferentBinding.from_dict(item) for item in self.target_candidates)
        if len({target.binding_id for target in targets}) != len(targets):
            raise ValueError("observation requires unique target binding IDs")
        evidence_ids = [target.evidence_ref.reference_id for target in targets]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("observation requires unique evidence reference IDs")
        declared_sources = set(sources)
        for target in targets:
            if (target.scene_id, target.scene_digest, target.session_id, target.session_digest) != (self.scene_id, self.scene_digest, self.session_id, self.session_digest):
                raise ValueError("stale referent scene/session")
            if not set(target.input_sources) <= declared_sources:
                raise ValueError("referent input sources must be declared by the observation")
        object.__setattr__(self, "target_candidates", tuple(sorted(targets, key=lambda target: (-target.confidence, target.binding_id))))
        speech = _text(self.speech_text, "observation.speech", optional=True, maximum=512)
        transcript = _digest(self.transcript_digest, "observation.transcript", optional=True)
        if speech and transcript != stable_digest(speech):
            raise ValueError("speech transcript digest does not match retained text")
        if not speech and transcript:
            raise ValueError("transcript digest requires retained speech")
        object.__setattr__(self, "speech_text", speech)
        object.__setattr__(self, "transcript_digest", transcript)
        start = _int(self.temporal_window_start_ms, "observation.start", 0, MAX_TIMESTAMP)
        end = _int(self.temporal_window_end_ms, "observation.end", 0, MAX_TIMESTAMP)
        if end < start or end - start > 60_000:
            raise ValueError("invalid temporal binding window")
        object.__setattr__(self, "temporal_window_start_ms", start)
        object.__setattr__(self, "temporal_window_end_ms", end)
        object.__setattr__(self, "provider_class", _id(self.provider_class, "observation.provider"))
        if self.evidence_class not in _EVIDENCE:
            raise ValueError("unsupported observation evidence class")
        object.__setattr__(self, "tracking_quality", _prob(self.tracking_quality, "observation.tracking_quality"))
        _bool(self.raw_sensor_retained, "observation.raw_sensor_retained", False)
        if not isinstance(self.authority, AuthorityEnvelope):
            object.__setattr__(self, "authority", AuthorityEnvelope.from_dict(self.authority))
        if self.version != MULTIMODAL_SPATIAL_OBSERVATION_VERSION:
            raise ValueError("unsupported observation version")
        _set_record_digest(self, "observation_digest")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible normalized observation."""
        return {"version": self.version, "observation_id": self.observation_id,
                "scene_id": self.scene_id, "scene_digest": self.scene_digest,
                "session_id": self.session_id, "session_digest": self.session_digest,
                "input_sources": list(self.input_sources),
                "normalized_event": self.normalized_event,
                "normalized_action": self.normalized_action,
                "target_candidates": [target.to_dict() for target in self.target_candidates],
                "speech_text": self.speech_text, "transcript_digest": self.transcript_digest,
                "temporal_window_start_ms": self.temporal_window_start_ms,
                "temporal_window_end_ms": self.temporal_window_end_ms,
                "provider_class": self.provider_class, "evidence_class": self.evidence_class,
                "tracking_quality": self.tracking_quality,
                "raw_sensor_retained": self.raw_sensor_retained,
                "authority": self.authority.to_dict(),
                "observation_digest": self.observation_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MultimodalSpatialObservation":
        """Parse and verify an exact serialized normalized observation."""
        _strict(payload, {"version", "observation_id", "scene_id", "scene_digest", "session_id",
                          "session_digest", "input_sources", "normalized_event", "normalized_action",
                          "target_candidates", "speech_text", "transcript_digest",
                          "temporal_window_start_ms", "temporal_window_end_ms", "provider_class",
                          "evidence_class", "tracking_quality", "raw_sensor_retained", "authority",
                          "observation_digest"}, "observation")
        _require_serialized_digest(payload, "observation_digest", "observation")
        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        return record

    def validate_bindings(self, *, expected_scene_id: str, expected_scene_digest: str,
                          expected_session_id: str, expected_session_digest: str,
                          expected_entity_digests: Mapping[str, str] | None = None,
                          expected_evidence_refs: Mapping[str, CanonicalReference | Mapping[str, Any]] | None = None,
                          expected_observation: "MultimodalSpatialObservation" | Mapping[str, Any] | None = None) -> None:
        """Rebind all scene, session, entity, and complete evidence identities."""
        if self.scene_id != _id(expected_scene_id, "expected scene id"):
            raise ValueError("stale scene id")
        if self.scene_digest != _digest(expected_scene_digest, "expected scene"):
            raise ValueError("stale scene digest")
        if self.session_id != _id(expected_session_id, "expected session id"):
            raise ValueError("stale session id")
        if self.session_digest != _digest(expected_session_digest, "expected session"):
            raise ValueError("stale session digest")
        if not isinstance(expected_entity_digests, Mapping):
            raise ValueError("expected_entity_digests is required")
        entity_ids = {target.entity_id for target in self.target_candidates}
        if entity_ids != set(expected_entity_digests):
            raise ValueError("entity reference set mismatch")
        for target in self.target_candidates:
            if target.entity_digest != _digest(expected_entity_digests[target.entity_id], "expected entity"):
                raise ValueError(f"stale scene entity: {target.entity_id}")
        _validate_reference_set(
            tuple(target.evidence_ref for target in self.target_candidates),
            expected_evidence_refs,
            "referent evidence",
        )
        if expected_observation is None:
            raise ValueError("expected_observation is required")
        expected = (
            expected_observation
            if isinstance(expected_observation, MultimodalSpatialObservation)
            else MultimodalSpatialObservation.from_dict(expected_observation)
        )
        if self.to_dict() != expected.to_dict():
            raise ValueError("stale complete observation identity")


def _legacy_manifest_body(body: Mapping[str, Any]) -> dict[str, Any]:
    """Return the fields covered by the existing V1 manifest digest."""
    result = dict(body)
    for key in ("created_at", "expires_at", "phase_hash", "signature_or_digest"):
        result.pop(key, None)
    return result


def _legacy_manifest_digest(body: Mapping[str, Any]) -> str:
    """Recompute the exact existing BLAKE2b-128 V1 manifest digest."""
    payload = json.dumps(_legacy_manifest_body(body), sort_keys=True, default=str)
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=16).hexdigest()


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    """Require a mapping at a nested V1 manifest boundary."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _require_sequence(value: Any, name: str) -> Sequence[Any]:
    """Require a non-string sequence at a nested V1 manifest boundary."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    return value


def _manifest_resource_limits(body: Mapping[str, Any]) -> dict[str, int]:
    """Return wrapper-compatible ceilings from the canonical V1 resource budget."""
    raw = _require_mapping(body.get("resource_budget"), "base manifest resource_budget")
    _strict(raw, set(_LEGACY_RESOURCE_FIELDS), "base manifest resource_budget")
    integer_fields = ("wall_time_ms", "memory_mb", "output_bytes", "tool_calls", "model_calls", "network_calls")
    limits = {name: _int(raw.get(name), f"base manifest resource_budget.{name}", 0, MAX_INTEGER) for name in integer_fields}
    cost_usd = _finite_number(raw.get("cost_usd"), "base manifest resource_budget.cost_usd")
    limits["cost_microusd"] = int(math.floor(cost_usd * 1_000_000))
    return limits


def _validate_v1_arena_lease_regions(lease: Mapping[str, Any], organ_id: str) -> None:
    """Require a bounded set of read-only regions owned by the wrapped organ."""
    regions = _require_sequence(lease.get("regions"), "base manifest arena_lease.regions")
    if not regions or len(regions) > 16:
        raise ValueError("base manifest arena_lease regions must be bounded")
    for index, raw_region in enumerate(regions):
        region = _require_mapping(raw_region, f"base manifest arena_lease.regions[{index}]")
        _strict(region, {"organ_id", "scope"}, f"base manifest arena_lease.regions[{index}]")
        if region.get("organ_id") != organ_id or region.get("scope") != "read_only":
            raise ValueError("base manifest arena_lease region is not read-only")


def _validate_v1_arena_lease_actions(
    lease: Mapping[str, Any],
    granted_capabilities: set[str],
) -> None:
    """Reconcile lease actions with manifest grants and mandatory denials."""
    allowed = set(_seq(
        lease.get("allowed_actions"),
        "base manifest arena_lease.allowed_actions",
        ids=True,
        sort=True,
    ))
    if allowed != granted_capabilities:
        raise ValueError("base manifest arena_lease allowed actions disagree with grants")
    forbidden = set(_seq(
        lease.get("forbidden_actions"),
        "base manifest arena_lease.forbidden_actions",
        ids=True,
        sort=True,
    ))
    required_forbidden = {
        "network", "install", "shell", "production_mutation", "secret_access",
        "commit", "push", "automatic_crystallization",
    }
    if not required_forbidden <= forbidden or forbidden & allowed:
        raise ValueError("base manifest arena_lease forbidden actions are incomplete")


def _validate_v1_arena_lease_digest(lease: Mapping[str, Any]) -> None:
    """Recompute and verify the canonical V1 arena-lease phase hash."""
    supplied_hash = _legacy_digest(
        lease.get("phase_hash"),
        "base manifest arena_lease.phase_hash",
    )
    hashed_body = dict(lease)
    hashed_body.pop("phase_hash")
    expected_hash = hashlib.blake2b(
        json.dumps(
            hashed_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()
    if supplied_hash != expected_hash:
        raise ValueError("base manifest arena_lease digest does not match content")


def _validate_v1_arena_lease(
    lease_value: Any,
    *,
    organ_id: str,
    granted_capabilities: set[str],
) -> None:
    """Verify that a retained V1 arena lease grants only canonical read authority."""
    lease = _require_mapping(lease_value, "base manifest arena_lease")
    if not lease:
        # An absent lease is a valid V1 state; manifest-level grants remain validated.
        return
    expected_fields = {
        "lease_version", "lease_id", "domain", "capsule_id", "holder",
        "regions", "allowed_actions", "forbidden_actions", "mode",
        "conflict_policy", "status", "metadata", "phase_hash",
    }
    _strict(lease, expected_fields, "base manifest arena_lease")
    if lease.get("lease_version") != "AURA_ARENA_LEASE_V1":
        raise ValueError("base manifest arena_lease version is unsafe")
    _id(lease.get("lease_id"), "base manifest arena_lease.lease_id")
    if lease.get("domain") != "ephemeral":
        raise ValueError("base manifest arena_lease domain is unsafe")
    if lease.get("capsule_id") != organ_id or lease.get("holder") != organ_id:
        raise ValueError("base manifest arena_lease holder identity is unsafe")
    _validate_v1_arena_lease_regions(lease, organ_id)
    _validate_v1_arena_lease_actions(lease, granted_capabilities)
    if lease.get("mode") != "read_only":
        raise ValueError("base manifest arena_lease mode is unsafe")
    if lease.get("conflict_policy") != "judge_then_reground":
        raise ValueError("base manifest arena_lease conflict policy is unsafe")
    if lease.get("status") != "active":
        raise ValueError("base manifest arena_lease status is unsafe")
    metadata = _require_mapping(lease.get("metadata"), "base manifest arena_lease.metadata")
    if metadata:
        raise ValueError("base manifest arena_lease metadata must be empty")
    _validate_v1_arena_lease_digest(lease)


def _validate_v1_manifest(body: Mapping[str, Any]) -> None:
    """Require the complete safe V1 manifest shape and authority profile."""
    _strict(body, set(_LEGACY_MANIFEST_FIELDS), "base manifest")
    if body.get("manifest_version") != LEGACY_EPHEMERAL_MANIFEST_VERSION:
        raise ValueError("unsupported base manifest version")
    _id(body.get("organ_id"), "base organ id")
    objective = _text(body.get("objective"), "base manifest objective")
    objective_hash = _text(body.get("objective_hash"), "base manifest objective_hash", maximum=24)
    expected_objective_hash = hashlib.blake2b(objective.encode("utf-8"), digest_size=12).hexdigest()
    if objective_hash != expected_objective_hash:
        raise ValueError("base manifest digest does not match objective/objective_hash binding")
    _id(body.get("creator"), "base manifest creator")
    ttl_seconds = _int(body.get("ttl_seconds"), "base manifest ttl", 1, MAX_TTL_SECONDS)
    created_at = _finite_number(body.get("created_at"), "base manifest created_at")
    expires_at = _finite_number(body.get("expires_at"), "base manifest expires_at")
    if expires_at <= created_at or abs((created_at + ttl_seconds) - expires_at) > 1e-6:
        raise ValueError("base manifest expiry is inconsistent with creation time and TTL")

    for name in ("intent_packet", "machine_route", "arena_lease", "data_policy", "ui_manifest", "verifier_requirements"):
        _require_mapping(body.get(name), f"base manifest {name}")
    for name in ("lexc_route", "requested_capabilities", "granted_capabilities", "denied_capabilities", "boundary_contracts", "components"):
        sequence = _require_sequence(body.get(name), f"base manifest {name}")
        if len(sequence) > MAX_ITEMS:
            raise ValueError(f"base manifest {name} exceeds its item ceiling")
    for name in ("intent_packet", "machine_route"):
        if body.get(name):
            raise ValueError(f"base manifest {name} must be empty in the non-operational PR1 wrapper")
    for name in ("lexc_route", "boundary_contracts"):
        if body.get(name):
            raise ValueError(f"base manifest {name} must be empty in the non-operational PR1 wrapper")
    _text(body.get("capability_resolution_ref"), "base manifest capability_resolution_ref", optional=True)
    _capability_resolution_digest(
        body.get("capability_resolution_digest"),
        "base manifest capability_resolution_digest",
    )
    _text(body.get("signature_or_digest"), "base manifest signature_or_digest", optional=True)

    granted = set(_seq(body.get("granted_capabilities"), "base manifest granted_capabilities", ids=True, max_items=MAX_ITEMS, sort=True))
    if granted & _LEGACY_FORBIDDEN_CAPABILITIES or not granted <= _LEGACY_ALLOWED_CAPABILITIES:
        raise ValueError("base manifest grants a forbidden or unknown capability")
    if not _LEGACY_REQUIRED_WORKSPACE_CAPABILITIES <= granted:
        raise ValueError("base manifest does not grant the minimum workspace capabilities")
    requested = _require_sequence(body.get("requested_capabilities"), "base manifest requested_capabilities")
    requested_grants: set[str] = set()
    requested_names: set[str] = set()
    for index, raw_request in enumerate(requested):
        request = _require_mapping(raw_request, f"base manifest requested_capabilities[{index}]")
        _strict(request, {"capability", "requested", "granted", "denied_reason"}, f"base manifest requested_capabilities[{index}]")
        capability = _id(request.get("capability"), f"base manifest requested_capabilities[{index}].capability")
        if capability in requested_names:
            raise ValueError("base manifest contains duplicate capability requests")
        requested_names.add(capability)
        _bool(request.get("requested"), f"base manifest requested_capabilities[{index}].requested", True)
        if not isinstance(request.get("granted"), bool):
            raise ValueError(f"base manifest requested_capabilities[{index}].granted must be boolean")
        _text(request.get("denied_reason"), f"base manifest requested_capabilities[{index}].denied_reason", optional=True)
        if request["granted"]:
            if capability not in _LEGACY_ALLOWED_CAPABILITIES:
                raise ValueError("base manifest request grants a forbidden or unknown capability")
            requested_grants.add(capability)
    if requested_grants != granted:
        raise ValueError("base manifest granted_capabilities disagree with capability requests")
    _validate_v1_arena_lease(
        body.get("arena_lease"),
        organ_id=body["organ_id"],
        granted_capabilities=granted,
    )

    for index, raw_denial in enumerate(_require_sequence(body.get("denied_capabilities"), "base manifest denied_capabilities")):
        denial = _require_mapping(raw_denial, f"base manifest denied_capabilities[{index}]")
        _strict(denial, {"capability", "reason"}, f"base manifest denied_capabilities[{index}]")
        _id(denial.get("capability"), f"base manifest denied_capabilities[{index}].capability")
        _id(denial.get("reason"), f"base manifest denied_capabilities[{index}].reason")

    if body.get("components"):
        raise ValueError("base manifest components must be empty for the non-operational PR1 wrapper")
    data_policy = _require_mapping(body.get("data_policy"), "base manifest data_policy")
    _strict(
        data_policy,
        {
            "readable_paths", "writable_temp_paths", "forbidden_paths",
            "private_memory_export", "raw_sidecar_dump", "secrets_access",
        },
        "base manifest data_policy",
    )
    readable_paths = set(_seq(
        data_policy.get("readable_paths"),
        "base manifest data_policy.readable_paths",
        max_items=16,
        sort=True,
    ))
    if not readable_paths or not readable_paths <= _LEGACY_SAFE_READABLE_PATHS:
        raise ValueError("base manifest readable paths exceed the closed PR1 allowlist")
    writable_paths = _seq(
        data_policy.get("writable_temp_paths"),
        "base manifest data_policy.writable_temp_paths",
        max_items=16,
        sort=True,
    )
    if writable_paths:
        raise ValueError("base manifest writable temp paths must be empty in PR1")
    _seq(
        data_policy.get("forbidden_paths"),
        "base manifest data_policy.forbidden_paths",
        max_items=32,
        sort=True,
    )
    for name in ("private_memory_export", "raw_sidecar_dump", "secrets_access"):
        _bool(data_policy.get(name), f"base manifest data_policy.{name}", False)
    ui_manifest = _require_mapping(body.get("ui_manifest"), "base manifest ui_manifest")
    _strict(ui_manifest, {"component_types", "schema", "executable"}, "base manifest ui_manifest")
    _seq(
        ui_manifest.get("component_types"),
        "base manifest ui_manifest.component_types",
        ids=True,
        max_items=32,
        sort=True,
    )
    ui_schema = _require_mapping(ui_manifest.get("schema"), "base manifest ui_manifest.schema")
    if ui_schema:
        raise ValueError("base manifest UI schema must be empty in the non-operational PR1 wrapper")
    _bool(ui_manifest.get("executable"), "base manifest ui_manifest.executable", False)
    limits = _manifest_resource_limits(body)
    if limits["network_calls"] != 0:
        raise ValueError("base manifest network access must remain disabled")
    verifier = _require_mapping(body.get("verifier_requirements"), "base manifest verifier_requirements")
    required_verifiers = {"no_production_mutation", "no_secret_access", "no_network_access"}
    must_pass = set(_seq(verifier.get("must_pass"), "base manifest verifier_requirements.must_pass", ids=True, sort=True))
    if not required_verifiers <= must_pass:
        raise ValueError("base manifest verifier requirements are incomplete")
    quality_gate = _id(verifier.get("quality_gate"), "base manifest verifier_requirements.quality_gate")
    if quality_gate != "advisory_for_read_only":
        raise ValueError("base manifest verifier quality gate is unsafe")
    if body.get("human_approval_policy") != "required_for_consequential":
        raise ValueError("base manifest human approval policy is unsafe")
    if body.get("dissolution_policy") != "mandatory":
        raise ValueError("base manifest dissolution policy is unsafe")
    if body.get("crystallization_policy") != "proposal_only":
        raise ValueError("base manifest crystallization policy is unsafe")
    if body.get("patch_authority") != "exact_source_spans_and_hashes_only":
        raise ValueError("base manifest patch authority is unsafe")
    _bool(body.get("vsa_patch_authority"), "base manifest vsa_patch_authority", False)


def _manifest_snapshot(manifest: Any) -> tuple[dict[str, Any], str, str]:
    """Verify and snapshot an exact safe V1 manifest into a wrapper identity."""
    raw = manifest.to_dict() if hasattr(manifest, "to_dict") else manifest
    body = _canonical(raw)
    if not isinstance(body, dict):
        raise ValueError("base manifest must be an object")
    _validate_v1_manifest(body)
    recomputed_legacy = _legacy_manifest_digest(body)
    supplied_legacy = _legacy_digest(body.get("phase_hash"), "base manifest phase_hash")
    if supplied_legacy != recomputed_legacy:
        raise ValueError("base manifest digest does not match serialized content")
    wrapper_digest = stable_digest({
        "manifest_version": body["manifest_version"],
        "organ_id": body["organ_id"],
        "legacy_manifest_digest": recomputed_legacy,
        "snapshot": body,
    })
    return body, recomputed_legacy, wrapper_digest


def _compiled_recipe_id(body: Mapping[str, Any]) -> str:
    """Derive the public recipe ID from every behavior-defining recipe field."""
    return f"workspace-recipe:{stable_digest(body)[:24]}"


def compile_coding_spatial_workspace_recipe(*, base_manifest: Any,
                                             project_projection: ProjectContextProjection | Mapping[str, Any],
                                             canonical_intent_digest: str,
                                             adapter_refs: Sequence[CanonicalReference | Mapping[str, Any]],
                                             evidence_refs: Sequence[CanonicalReference | Mapping[str, Any]],
                                             budgets: WorkspaceBudget | Mapping[str, Any] | None = None,
                                             ttl_seconds: int = 300,
                                             expected_manifest_timestamps: Sequence[int | float] | None = None) -> EphemeralWorkspaceRecipe:
    """Compile the frozen recipe without invoking any canonical owner."""
    serialized_manifest = isinstance(base_manifest, Mapping)
    raw_before = base_manifest.to_dict() if hasattr(base_manifest, "to_dict") else base_manifest
    before = canonical_json(raw_before)
    body, legacy_digest, wrapper_digest = _manifest_snapshot(base_manifest)
    raw_after = base_manifest.to_dict() if hasattr(base_manifest, "to_dict") else base_manifest
    if before != canonical_json(raw_after):
        raise ValueError("base V1 manifest changed while wrapping")
    project = project_projection if isinstance(project_projection, ProjectContextProjection) else ProjectContextProjection.from_dict(project_projection)
    if project.canonical_owner != _PROJECT_CANONICAL_OWNER:
        raise ValueError("project projection is not owned by the canonical continuity owner")
    if project.freshness_class not in _CURRENT_FRESHNESS or any(reference.freshness_class not in _CURRENT_FRESHNESS for reference in project.all_references()):
        raise ValueError("project projection or references are stale or unknown")
    manifest_identity = wrapper_digest[:32]
    manifest_ref = CanonicalReference(f"organ-manifest:{manifest_identity}",
                                      "aura_ephemeral_manifest",
                                      f"ephemeral-organ:{manifest_identity}@{body['manifest_version']}",
                                      wrapper_digest,
                                      metadata={"manifest_version": body["manifest_version"],
                                                "legacy_manifest_digest": legacy_digest,
                                                "wrapped_not_replaced": True})
    intent = _digest(canonical_intent_digest, "canonical intent")
    requested_ttl = _int(ttl_seconds, "recipe.ttl", 1, MAX_TTL_SECONDS)
    manifest_ttl = _int(body.get("ttl_seconds"), "base manifest ttl", 1, MAX_TTL_SECONDS)
    created_at = _finite_number(body.get("created_at"), "base manifest created_at")
    expires_at = _finite_number(body.get("expires_at"), "base manifest expires_at")
    if serialized_manifest:
        if (
            isinstance(expected_manifest_timestamps, (str, bytes, bytearray))
            or not isinstance(expected_manifest_timestamps, Sequence)
            or len(expected_manifest_timestamps) != 2
        ):
            raise ValueError("serialized base manifest requires trusted timestamp bindings")
        expected_created_at = _finite_number(
            expected_manifest_timestamps[0],
            "expected base manifest created_at",
        )
        expected_expires_at = _finite_number(
            expected_manifest_timestamps[1],
            "expected base manifest expires_at",
        )
        if (created_at, expires_at) != (expected_created_at, expected_expires_at):
            raise ValueError("serialized base manifest timestamp binding mismatch")
    elif expected_manifest_timestamps is not None:
        raise ValueError("timestamp bindings are only accepted for serialized base manifests")
    now = time.time()
    if now < created_at:
        raise ValueError("compile time precedes base manifest creation")
    remaining_seconds = expires_at - now
    if remaining_seconds <= 0:
        raise ValueError("base manifest is expired")
    if remaining_seconds < 1:
        raise ValueError("base manifest has less than one whole second remaining")
    remaining_ttl = math.floor(remaining_seconds)
    effective_ttl = min(requested_ttl, manifest_ttl, remaining_ttl)

    manifest_limits = _manifest_resource_limits(body)
    if budgets is None:
        default_values = WorkspaceBudget().to_dict()
        for name, ceiling in manifest_limits.items():
            default_values[name] = min(default_values[name], ceiling)
        default_values["wall_time_ms"] = min(default_values["wall_time_ms"], effective_ttl * 1000)
        budget = WorkspaceBudget.from_dict(default_values)
    elif isinstance(budgets, WorkspaceBudget):
        budget = budgets
    else:
        budget = WorkspaceBudget.from_dict(budgets)
    budget_values = budget.to_dict()
    for name, ceiling in manifest_limits.items():
        if budget_values[name] > ceiling:
            raise ValueError(f"budget.{name} exceeds base manifest resource ceiling")
    if budget.wall_time_ms > effective_ttl * 1000:
        raise ValueError("budget.wall_time_ms cannot exceed effective workspace TTL")
    adapters = _refs(adapter_refs, "adapter_refs", require_current=True)
    evidence = _refs(evidence_refs, "evidence_refs", require_current=True)
    definition = CODING_SPATIAL_WORKSPACE_V1_DEFINITION
    provisional = EphemeralWorkspaceRecipe(
        recipe_id="workspace-recipe:pending",
        demonstration_id=CODING_SPATIAL_WORKSPACE_V1,
        base_manifest_ref=manifest_ref,
        canonical_intent_digest=intent,
        project_projection_id=project.projection_id,
        project_projection_digest=project.projection_digest,
        capability_ids=tuple(definition["capability_ids"]),
        dependency_edges=tuple(
            DependencyEdge(source, target)
            for source, target in definition["dependency_edges"]
        ),
        adapter_refs=adapters,
        evidence_refs=evidence,
        domain_owner_handoff_map=definition["domain_owner_handoff_map"],
        budgets=budget,
        renderer_requirements=tuple(definition["renderer_requirements"]),
        device_requirements=tuple(definition["device_requirements"]),
        allowed_interaction_actions=tuple(definition["allowed_interaction_actions"]),
        required_verification_gates=tuple(definition["required_verification_gates"]),
        ttl_seconds=effective_ttl,
    )
    identity_body = provisional.to_dict()
    identity_body.pop("recipe_id")
    identity_body.pop("recipe_digest")
    return replace(
        provisional,
        recipe_id=_compiled_recipe_id(identity_body),
        recipe_digest="",
    )


def validate_recipe_semantics(payload: Mapping[str, Any]) -> EphemeralWorkspaceRecipe:
    """Run semantic graph and cross-field validation after JSON Schema validation."""
    return EphemeralWorkspaceRecipe.from_dict(payload)


def validate_project_semantics(payload: Mapping[str, Any]) -> ProjectContextProjection:
    """Run combined-reference uniqueness validation after JSON Schema validation."""
    return ProjectContextProjection.from_dict(payload)


def validate_observation_semantics(payload: Mapping[str, Any]) -> MultimodalSpatialObservation:
    """Run temporal, transcript, target, and scene/session semantic validation."""
    return MultimodalSpatialObservation.from_dict(payload)


__all__ = ["AUTHORITY_ENVELOPE_VERSION", "CANONICAL_REFERENCE_VERSION",
           "CODING_SPATIAL_WORKSPACE_V1", "CODING_SPATIAL_WORKSPACE_V1_DEFINITION",
           "EPHEMERAL_WORKSPACE_RECIPE_VERSION", "MAX_TTL_SECONDS",
           "MULTIMODAL_SPATIAL_OBSERVATION_VERSION", "PROJECT_CONTEXT_PROJECTION_VERSION",
           "REPOSITORY_IDENTITY_VERSION", "SPATIAL_REFERENT_BINDING_VERSION",
           "WORKSPACE_CONTRACTS_VERSION", "AuthorityEnvelope", "CanonicalReference",
           "DependencyEdge", "EphemeralWorkspaceRecipe", "MultimodalSpatialObservation",
           "ProjectContextProjection", "RepositoryIdentity", "SpatialReferentBinding",
           "WorkspaceBudget", "canonical_json", "compile_coding_spatial_workspace_recipe",
           "stable_digest", "validate_observation_semantics", "validate_project_semantics",
           "validate_recipe_semantics"]
