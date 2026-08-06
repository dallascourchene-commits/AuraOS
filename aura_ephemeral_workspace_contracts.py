"""Deterministic, non-operational contracts for intent-compiled spatial workspaces.

The records reference Aura's existing canonical owners. They never activate an
organ, invoke a renderer or model, persist project truth, or grant mutation,
publication, deployment, professional, payment, or merge authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
import hashlib
import json
import math
import re
import time
from types import MappingProxyType
from typing import Any

from aura_ephemeral_path_policy import FORBIDDEN_PATTERNS

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
MAX_CANONICAL_ITEMS = MAX_ITEMS
MAX_CANONICAL_SCALAR_BYTES = MAX_METADATA_BYTES
MAX_CANONICAL_NUMBER_ABS = MAX_TIMESTAMP
MAX_HANDOFF_OWNERS = 6

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
_LEGACY_CLOSED_GRANT_PROFILES = frozenset({_LEGACY_ALLOWED_CAPABILITIES, _LEGACY_REQUIRED_WORKSPACE_CAPABILITIES})
_LEGACY_CLOSED_UI_COMPONENT_TYPES = frozenset({
    "objective_header", "existing_capability_cards", "exact_function_table",
    "relationship_graph", "tests_and_docs_panel", "safety_constraints",
    "missing_capability_panel", "cost_telemetry", "lifecycle_status",
    "dissolve_control",
})
_MANIFEST_PROJECTION_VERSION = "AURA_EPHEMERAL_MANIFEST_PROJECTION_V1"
_LEGACY_SAFE_READABLE_PATHS = frozenset({
    ".aura/CODEMAP.json", ".aura/CODEMAP.md", ".aura/MODULE_MANIFEST.json",
})
_LEGACY_REQUIRED_FORBIDDEN_PATHS = frozenset({
    ".env", ".git/credentials", "*/secrets*", "*/.key",
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
_PR1_RESOURCE_CEILINGS = MappingProxyType({
    "wall_time_ms": 300_000,
    "memory_mb": 512,
    "context_tokens": 64_000,
    "output_bytes": 4_000_000,
    "tool_calls": 64,
    "model_calls": 0,
    "cost_microusd": 0,
    "network_calls": 0,
    "device_events": 100_000,
})


def _bounded_sequence_snapshot(value: Any, name: str, max_items: int) -> tuple[Any, ...]:
    """Detach a sequence once and normalize hostile iterator protocol failures."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    result: list[Any] = []
    try:
        for item in value:
            result.append(item)
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid sequence protocol") from exc
    return tuple(result)


def _bounded_pair_snapshot(value: Any, name: str) -> tuple[Any, Any]:
    """Detach one pair-like sequence while normalizing hostile callbacks."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a key/value pair")
    try:
        pair_length = len(value)
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} must be a key/value pair") from exc
    if pair_length != 2:
        raise ValueError(f"{name} must be a key/value pair")
    try:
        return value[0], value[1]
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} must be a key/value pair") from exc


def _bounded_mapping_snapshot(value: Any, name: str, max_items: int) -> tuple[tuple[Any, Any], ...]:
    """Detach a mapping once and normalize hostile export/iterator callbacks."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    try:
        if len(value) > max_items:
            raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid item count") from exc
    try:
        exported_items = value.items()
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid mapping export protocol") from exc
    result: list[tuple[Any, Any]] = []
    try:
        for item in exported_items:
            try:
                key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            except ValueError as exc:
                if exc.__cause__ is None:
                    raise
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            result.append((key, item_value))
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid mapping export protocol") from exc
    return tuple(result)


def _canonical(value: Any, *, _depth: int = 0, _active: set[int] | None = None) -> Any:
    """Return a lossless bounded canonical JSON value from one detached traversal."""
    if _depth > MAX_CANONICAL_DEPTH:
        raise ValueError("canonical JSON nesting exceeds its depth ceiling")
    active = set() if _active is None else _active
    next_depth = _depth + 1
    if isinstance(value, Enum):
        return _canonical(value.value, _depth=next_depth, _active=active)
    if is_dataclass(value):
        marker = id(value)
        if marker in active:
            raise ValueError("canonical JSON contains a recursive dataclass")
        active.add(marker)
        try:
            try:
                exporter = getattr(value, "to_dict", None)
            except ValueError:
                raise
            except RecursionError as exc:
                raise ValueError("canonical JSON dataclass nesting exceeds its depth ceiling") from exc
            except Exception as exc:
                raise ValueError("canonical JSON dataclass has an invalid export protocol") from exc
            if exporter is not None:
                if not callable(exporter):
                    raise ValueError("canonical JSON dataclass has an invalid export protocol")
                try:
                    exported = exporter()
                except ValueError:
                    raise
                except RecursionError as exc:
                    raise ValueError("canonical JSON dataclass nesting exceeds its depth ceiling") from exc
                except Exception as exc:
                    raise ValueError("canonical JSON dataclass has an invalid export protocol") from exc
            else:
                try:
                    exported = {field.name: getattr(value, field.name) for field in fields(value)}
                except ValueError:
                    raise
                except RecursionError as exc:
                    raise ValueError("canonical JSON dataclass nesting exceeds its depth ceiling") from exc
                except Exception as exc:
                    raise ValueError("canonical JSON dataclass has an invalid field export protocol") from exc
            return _canonical(exported, _depth=next_depth, _active=active)
        finally:
            active.remove(marker)
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in active:
            raise ValueError("canonical JSON contains a recursive object")
        active.add(marker)
        try:
            pairs = _bounded_mapping_snapshot(value, "canonical JSON object", MAX_CANONICAL_ITEMS)
            keys = [key for key, _ in pairs]
            if any(type(key) is not str for key in keys):
                raise ValueError("JSON object keys must be strings")
            if len(set(keys)) != len(keys):
                raise ValueError("canonical JSON object keys must be unique")
            detached: dict[str, Any] = {}
            for key, item in pairs:
                try:
                    encoded_key = key.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise ValueError(
                        "canonical JSON object keys must contain valid Unicode scalar values"
                    ) from exc
                if len(encoded_key) > MAX_CANONICAL_SCALAR_BYTES:
                    raise ValueError("canonical JSON object key exceeds its scalar byte ceiling")
                detached[key] = item
            return {
                key: _canonical(detached[key], _depth=next_depth, _active=active)
                for key in sorted(detached)
            }
        finally:
            active.remove(marker)
    if isinstance(value, (list, tuple)):
        marker = id(value)
        if marker in active:
            raise ValueError("canonical JSON contains a recursive sequence")
        active.add(marker)
        try:
            items = _bounded_sequence_snapshot(value, "canonical JSON sequence", MAX_CANONICAL_ITEMS)
            return [_canonical(item, _depth=next_depth, _active=active) for item in items]
        finally:
            active.remove(marker)
    if isinstance(value, (set, frozenset)):
        raise ValueError("sets are not JSON values")
    if type(value) is str:
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("canonical JSON strings must contain valid Unicode scalar values") from exc
        if len(encoded) > MAX_CANONICAL_SCALAR_BYTES:
            raise ValueError("canonical JSON string exceeds its scalar byte ceiling")
        return value
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON integer exceeds its numeric ceiling")
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON number exceeds its numeric ceiling")
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
    if type(value) is not str:
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


def _fixed_text(value: Any, name: str, expected: str) -> str:
    """Require one exact built-in string constant."""
    result = _text(value, name, maximum=192)
    if result != expected:
        raise ValueError(f"{name} must be {expected}")
    return result


def _enum_text(value: Any, name: str, allowed: frozenset[str]) -> str:
    """Require an exact built-in string from a closed enumeration."""
    result = _text(value, name, maximum=64)
    if result not in allowed:
        raise ValueError(f"unsupported {name}")
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
    """Validate an exact finite JSON number at or above a minimum."""
    if type(value) not in (int, float):
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
    if type(value) is not bool or value is not required:
        raise ValueError(f"{name} must be {str(required).lower()}")
    return value


def _int(value: Any, name: str, low: int, high: int) -> int:
    """Validate an exact bounded JSON integer."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")
    return value


def _prob(value: Any, name: str) -> int | float:
    """Validate an exact JSON numeric spelling in the inclusive unit interval."""
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a JSON number")
    if type(value) is float and not math.isfinite(value):
        raise ValueError(f"{name} must be between 0 and 1")
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def _seq(value: Any, name: str, *, ids: bool = False, max_items: int = MAX_ITEMS, sort: bool = False, upper: bool = False) -> tuple[str, ...]:
    """Validate a bounded unique string sequence from one detached snapshot."""
    items = _bounded_sequence_snapshot(value, name, max_items)
    normalized = []
    for item in items:
        text = _id(item, f"{name}[]") if ids else _text(item, f"{name}[]")
        if upper and text != text.upper():
            raise ValueError(f"{name} values must already use uppercase canonical spelling")
        normalized.append(text)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} values must be unique")
    result = tuple(normalized)
    return tuple(sorted(result)) if sort else result

def _source_path(value: Any, name: str) -> str:
    """Require a safe repository-relative source path under the canonical path policy."""
    path = _text(value, name, maximum=4096)
    if "\\" in path or path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(f"{name} must be a repository-relative POSIX path")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{name} contains an unsafe path segment")
    normalized = "/".join(parts).lower()
    if any(pattern.lower() in normalized for pattern in FORBIDDEN_PATTERNS):
        raise ValueError(f"{name} targets a path forbidden by aura_ephemeral_path_policy")
    return path

def _metadata(value: Any, name: str) -> tuple[tuple[str, Any], ...]:
    """Validate and recursively freeze the closed scalar metadata contract."""
    if value is None:
        raise ValueError(f"{name} must be an object")
    if type(value) is tuple and not value:
        return ()
    if isinstance(value, tuple):
        pairs = _bounded_sequence_snapshot(value, name, len(_METADATA_FIELDS))
        normalized_pairs: list[tuple[str, Any]] = []
        for item in pairs:
            try:
                key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            except ValueError as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            if type(key) is not str:
                raise ValueError(f"{name} keys must be strings")
            normalized_pairs.append((key, item_value))
        if len({key for key, _ in normalized_pairs}) != len(normalized_pairs):
            raise ValueError(f"{name} keys must be unique")
        candidate = dict(normalized_pairs)
    elif isinstance(value, Mapping):
        try:
            pairs = _bounded_mapping_snapshot(value, name, len(_METADATA_FIELDS))
        except ValueError as exc:
            if "item ceiling" in str(exc):
                raise ValueError(f"{name} exceeds its field ceiling") from exc
            raise
        if any(type(key) is not str for key, _ in pairs):
            raise ValueError(f"{name} keys must be strings")
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError(f"{name} keys must be unique")
        candidate = dict(pairs)
    else:
        raise ValueError(f"{name} must be an object")
    if any(type(key) is not str for key in candidate):
        raise ValueError(f"{name} keys must be strings")
    unknown = set(candidate) - _METADATA_FIELDS
    if unknown:
        raise ValueError(f"{name} contains unsupported fields: {sorted(unknown)}")
    validated = {}
    for key, item in candidate.items():
        field_name = f"{name}.{key}"
        if key == "manifest_version":
            validated[key] = _id(item, field_name)
        elif key == "source_path":
            validated[key] = _source_path(item, field_name)
        elif key in _METADATA_TEXT_FIELDS:
            validated[key] = _text(item, field_name, maximum=4096)
        elif key in _METADATA_BOOL_FIELDS:
            validated[key] = _bool(item, field_name, True)
        elif key in {"line_start", "line_end"}:
            validated[key] = _int(item, field_name, 1, MAX_INTEGER)
        elif key in _METADATA_INT_FIELDS:
            validated[key] = _int(item, field_name, 0, MAX_INTEGER)
        elif key == "legacy_manifest_digest":
            validated[key] = _legacy_digest(item, field_name)
        else:
            validated[key] = _digest(item, field_name)
    supplied_line_fields = {"line_start", "line_end"} & set(validated)
    if supplied_line_fields:
        if supplied_line_fields != {"line_start", "line_end"} or "source_path" not in validated:
            raise ValueError(
                f"{name} source line range requires source_path, line_start, and line_end"
            )
        if validated["line_start"] > validated["line_end"]:
            raise ValueError(f"{name} source line range is reversed")
    if len(canonical_json(validated).encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError(f"{name} exceeds its byte ceiling")
    return tuple(sorted(validated.items()))


def _strict(payload: Mapping[str, Any], expected: set[str], name: str) -> None:
    """Require an exact mapping key set without trusting custom length reports."""
    if not isinstance(payload, Mapping):
        raise ValueError(f"{name} must be an object")
    if isinstance(payload, dict) and any(type(key) is not str for key in payload):
        raise ValueError(f"{name} keys must be strings")
    try:
        if len(payload) > len(expected):
            raise ValueError(
                f"{name} keys mismatch: expected at most {len(expected)} keys"
            )
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} has an invalid key count") from exc
    pairs = _bounded_mapping_snapshot(payload, name, len(expected))
    keys = tuple(key for key, _ in pairs)
    if any(type(key) is not str for key in keys):
        raise ValueError(f"{name} keys must be strings")
    supplied = set(keys)
    if supplied != expected:
        raise ValueError(
            f"{name} keys mismatch: missing={sorted(expected-supplied)}, "
            f"extra={sorted(supplied-expected)}"
        )


def _set_record_digest(record: Any, field_name: str) -> None:
    """Compute a record digest or verify a non-empty supplied digest."""
    body = record.to_dict()
    supplied = _digest(body.pop(field_name, ""), field_name, optional=True)
    expected = stable_digest(body)
    if supplied and supplied != expected:
        raise ValueError(f"{field_name} does not match canonical bytes")
    object.__setattr__(record, field_name, expected)


def _detached_json_snapshot(
    value: Any,
    name: str,
    *,
    _depth: int = 0,
    _active: set[int] | None = None,
) -> Any:
    """Deep-detach one bounded JSON-shaped value without rereading hostile containers."""
    if _depth > MAX_CANONICAL_DEPTH:
        raise ValueError(f"{name} nesting exceeds its depth ceiling")
    active = set() if _active is None else _active
    next_depth = _depth + 1
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in active:
            raise ValueError(f"{name} contains a recursive object")
        active.add(marker)
        try:
            pairs = _bounded_mapping_snapshot(value, name, MAX_CANONICAL_ITEMS)
            result: dict[str, Any] = {}
            for key, item in pairs:
                if type(key) is not str:
                    raise ValueError(f"{name} keys must be strings")
                try:
                    encoded_key = key.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise ValueError(
                        f"{name} keys must contain valid Unicode scalar values"
                    ) from exc
                if len(encoded_key) > MAX_CANONICAL_SCALAR_BYTES:
                    raise ValueError(f"{name} key exceeds its scalar byte ceiling")
                if key in result:
                    raise ValueError(f"{name} keys must be unique")
                result[key] = _detached_json_snapshot(
                    item, f"{name}.{key}", _depth=next_depth, _active=active
                )
            return result
        finally:
            active.remove(marker)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        marker = id(value)
        if marker in active:
            raise ValueError(f"{name} contains a recursive sequence")
        active.add(marker)
        try:
            items = _bounded_sequence_snapshot(value, name, MAX_CANONICAL_ITEMS)
            return [
                _detached_json_snapshot(
                    item, f"{name}[{index}]", _depth=next_depth, _active=active
                )
                for index, item in enumerate(items)
            ]
        finally:
            active.remove(marker)
    if type(value) is str:
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{name} must contain valid Unicode scalar values") from exc
        if len(encoded) > MAX_CANONICAL_SCALAR_BYTES:
            raise ValueError(f"{name} exceeds its scalar byte ceiling")
        return value
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError(f"{name} exceeds its numeric ceiling")
        return value
    if type(value) is float:
        if not math.isfinite(value) or abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError(f"{name} exceeds its numeric ceiling")
        return value
    raise ValueError(f"{name} contains a non-JSON value: {type(value).__name__}")


def _detached_serialized_record(
    payload: Mapping[str, Any],
    expected: set[str],
    name: str,
    *,
    digest_field: str | None = None,
) -> dict[str, Any]:
    """Deep-snapshot one hostile serialized record and validate detached bytes only."""
    detached = _detached_json_snapshot(payload, name)
    if not isinstance(detached, dict):
        raise ValueError(f"{name} must be an object")
    supplied = set(detached)
    if supplied != expected:
        raise ValueError(
            f"{name} keys mismatch: missing={sorted(expected-supplied)}, "
            f"extra={sorted(supplied-expected)}"
        )
    if digest_field is not None:
        _digest(detached.get(digest_field), f"{name}.{digest_field}")
    return detached


def _require_exact_serialized_form(record: Any, payload: Mapping[str, Any]) -> None:
    """Reject detached payloads that normalize to a different public record."""
    if record.to_dict() != payload:
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
        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "authority.version", AUTHORITY_ENVELOPE_VERSION),
        )
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
        detached = _detached_serialized_record(
            payload, {field.name for field in fields(cls)}, "authority"
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
        return record


def _exact_authority_envelope(value: Any, name: str) -> AuthorityEnvelope:
    """Admit only the exact record type or one detached serialized mapping."""
    if type(value) is AuthorityEnvelope:
        return value
    if isinstance(value, Mapping):
        return AuthorityEnvelope.from_dict(value)
    raise ValueError(f"{name} must be an exact AuthorityEnvelope or serialized object")


def _exact_contract_record(value: Any, record_type: type[Any], name: str) -> Any:
    """Admit an exact contract record or parse one detached serialized mapping."""
    if type(value) is record_type:
        return value
    if isinstance(value, Mapping):
        return record_type.from_dict(value)
    raise ValueError(
        f"{name} must be an exact {record_type.__name__} or serialized object"
    )


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
        truth_class = _text(self.truth_class, "reference.truth_class", maximum=32)
        freshness_class = _text(self.freshness_class, "reference.freshness_class", maximum=32)
        if truth_class not in _TRUTH or freshness_class not in _FRESHNESS:
            raise ValueError("unsupported reference class")
        object.__setattr__(self, "truth_class", truth_class)
        object.__setattr__(self, "freshness_class", freshness_class)
        object.__setattr__(self, "metadata", _metadata(self.metadata, "reference.metadata"))
        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "reference.version", CANONICAL_REFERENCE_VERSION),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible reference mapping."""
        return {"version": self.version, "reference_id": self.reference_id, "owner": self.owner,
                "canonical_ref": self.canonical_ref, "digest": self.digest,
                "truth_class": self.truth_class, "freshness_class": self.freshness_class,
                "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalReference":
        """Parse an exact serialized canonical reference."""
        detached = _detached_serialized_record(
            payload,
            {"version", "reference_id", "owner", "canonical_ref", "digest", "truth_class", "freshness_class", "metadata"},
            "reference",
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
        return record


def _reference_map(value: Any, name: str) -> dict[str, CanonicalReference]:
    """Parse one bounded identifier-to-canonical-reference mapping."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} is required")
    result: dict[str, CanonicalReference] = {}
    for supplied_id, raw_reference in _bounded_mapping_snapshot(value, name, MAX_ITEMS):
        reference_id = _id(supplied_id, f"{name} key")
        reference = _exact_contract_record(
            raw_reference, CanonicalReference, f"{name} reference"
        )
        if reference_id != reference.reference_id:
            raise ValueError(f"{name} key/reference mismatch")
        if reference_id in result:
            raise ValueError(f"duplicate {name} reference: {reference_id}")
        result[reference_id] = reference
    return result


def _validate_reference_set(actual: Sequence[CanonicalReference], expected_value: Any,
                            name: str, *, require_current: bool = True) -> None:
    """Rebind a complete reference set from one bounded expected snapshot."""
    if not isinstance(expected_value, Mapping):
        raise ValueError(f"expected_{name}_refs is required")
    try:
        expected_pairs = _bounded_mapping_snapshot(
            expected_value, f"expected_{name}_refs", MAX_ITEMS
        )
    except ValueError as exc:
        raise ValueError(f"{name} reference set size mismatch") from exc
    if len(expected_pairs) != len(actual):
        raise ValueError(f"{name} reference set size mismatch")
    expected_payload: dict[str, Any] = {}
    for key, value in expected_pairs:
        validated_key = _id(key, f"expected_{name}_refs key")
        if validated_key in expected_payload:
            raise ValueError(
                f"duplicate expected_{name}_refs reference: {validated_key}"
            )
        expected_payload[validated_key] = value
    expected = _reference_map(expected_payload, f"expected_{name}_refs")
    actual_ids = [reference.reference_id for reference in actual]
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError(f"duplicate {name} reference IDs")
    if set(actual_ids) != set(expected):
        raise ValueError(f"{name} reference set mismatch")
    for reference in actual:
        if reference.to_dict() != expected[reference.reference_id].to_dict():
            raise ValueError(f"stale {name} reference: {reference.reference_id}")
        if require_current and reference.freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError(f"stale or unknown {name} reference: {reference.reference_id}")


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
        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "repository.version", REPOSITORY_IDENTITY_VERSION),
        )
        _set_record_digest(self, "identity_digest")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible repository identity."""
        return {"version": self.version, "repository": self.repository, "ref": self.ref,
                "commit_sha": self.commit_sha, "source_tree_digest": self.source_tree_digest,
                "identity_digest": self.identity_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RepositoryIdentity":
        """Parse and verify an exact serialized repository identity."""
        detached = _detached_serialized_record(
            payload,
            {"version", "repository", "ref", "commit_sha", "source_tree_digest", "identity_digest"},
            "repository",
            digest_field="identity_digest",
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
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
        canonical_owner = _id(self.canonical_owner, "project.canonical_owner")
        if canonical_owner != _PROJECT_CANONICAL_OWNER:
            raise ValueError("project.canonical_owner must be the unified continuity owner")
        object.__setattr__(self, "canonical_owner", canonical_owner)
        object.__setattr__(self, "objective_digest", _digest(self.objective_digest, "project.objective_digest"))
        object.__setattr__(self, "purpose_digest", _digest(self.purpose_digest, "project.purpose_digest"))
        object.__setattr__(
            self,
            "repository_identity",
            _exact_contract_record(
                self.repository_identity,
                RepositoryIdentity,
                "project.repository_identity",
            ),
        )
        seen: set[str] = set()
        for name in _REFERENCE_FIELDS:
            raw = getattr(self, name)
            items = _bounded_sequence_snapshot(raw, f"project.{name}", MAX_ITEMS)
            refs = tuple(
                _exact_contract_record(
                    item, CanonicalReference, f"project.{name} item"
                )
                for item in items
            )
            for reference in refs:
                if reference.truth_class != "EXACT":
                    raise ValueError("project references must use EXACT canonical truth")
                if reference.reference_id in seen:
                    raise ValueError(f"duplicate project reference: {reference.reference_id}")
                seen.add(reference.reference_id)
            object.__setattr__(self, name, tuple(sorted(refs, key=lambda item: item.reference_id)))
        if not self.artifact_evidence_refs:
            raise ValueError("artifact_evidence_refs must not be empty")
        object.__setattr__(self, "freshness_timestamp_ms", _int(self.freshness_timestamp_ms, "project.freshness_timestamp_ms", 0, MAX_TIMESTAMP))
        object.__setattr__(
            self,
            "freshness_class",
            _enum_text(self.freshness_class, "project.freshness_class", _FRESHNESS),
        )
        object.__setattr__(self, "completeness_warnings", _seq(self.completeness_warnings, "project.completeness_warnings", max_items=128, sort=True))
        object.__setattr__(
            self,
            "privacy_class",
            _fixed_text(self.privacy_class, "project.privacy_class", _PROJECT_PRIVACY_CLASS),
        )
        object.__setattr__(
            self,
            "egress_class",
            _fixed_text(self.egress_class, "project.egress_class", _PROJECT_EGRESS_CLASS),
        )
        _bool(self.projection_only, "project.projection_only", True)
        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "project.authority"),
        )
        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "project.version", PROJECT_CONTEXT_PROJECTION_VERSION),
        )
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
        detached = _detached_serialized_record(
            payload,
            {"version", "projection_id", "project_ref", "canonical_owner", "objective_digest", "purpose_digest", "repository_identity", "freshness_timestamp_ms", "freshness_class", "completeness_warnings", "privacy_class", "egress_class", "projection_only", "authority", "projection_digest", *_REFERENCE_FIELDS},
            "project",
            digest_field="projection_digest",
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
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
        expected = _exact_contract_record(
            expected_projection, ProjectContextProjection, "expected_projection"
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
    model_calls: int = 0
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
        detached = _detached_serialized_record(
            payload, {field.name for field in fields(cls)}, "budget"
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
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
        detached = _detached_serialized_record(
            payload, {"source_capability_id", "target_capability_id"}, "dependency"
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
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
    """Validate and canonicalize a non-empty reference set from one snapshot."""
    items = _bounded_sequence_snapshot(value, name, MAX_ITEMS)
    if not items:
        raise ValueError(f"{name} must be a non-empty bounded sequence")
    result = tuple(
        _exact_contract_record(item, CanonicalReference, f"{name} item")
        for item in items
    )
    if len({item.reference_id for item in result}) != len(result):
        raise ValueError(f"duplicate {name} IDs")
    if any(item.truth_class != "EXACT" for item in result):
        raise ValueError(f"{name} must contain only EXACT canonical references")
    if require_current and any(item.freshness_class not in _CURRENT_FRESHNESS for item in result):
        raise ValueError(f"{name} must contain only current or bounded references")
    return tuple(sorted(result, key=lambda item: (item.reference_id, item.owner, item.digest)))


def _owner_map(value: Any) -> tuple[tuple[str, str], ...]:
    """Validate and canonicalize the closed domain-owner handoff map."""
    if isinstance(value, Mapping):
        items = _bounded_mapping_snapshot(value, "handoff map", MAX_HANDOFF_OWNERS)
    else:
        items = _bounded_sequence_snapshot(value, "handoff map", MAX_HANDOFF_OWNERS)
    pairs = []
    for item in items:
        try:
            key, owner = _bounded_pair_snapshot(item, "handoff map entry")
        except ValueError as exc:
            raise ValueError("handoff map entries must be key/owner pairs") from exc
        pairs.append((_id(key, "handoff key"), _id(owner, "handoff owner")))
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
        "manifest_version", "legacy_manifest_digest", "source_digest",
        "wrapped_not_replaced",
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
    _digest(metadata["source_digest"], "base manifest reference metadata source_digest")
    manifest_identity = reference.digest[:32]
    expected_reference_id = f"organ-manifest-projection:{manifest_identity}"
    expected_canonical_ref = (
        f"ephemeral-organ-projection:{manifest_identity}@{metadata['manifest_version']}"
    )
    if (
        reference.reference_id != expected_reference_id
        or reference.canonical_ref != expected_canonical_ref
    ):
        raise ValueError("base manifest reference name does not match wrapper digest")


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
    issued_at_epoch_seconds: int
    expires_at_epoch_seconds: int
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
        object.__setattr__(
            self,
            "base_manifest_ref",
            _exact_contract_record(
                self.base_manifest_ref,
                CanonicalReference,
                "recipe.base_manifest_ref",
            ),
        )
        if self.base_manifest_ref.owner != "aura_ephemeral_manifest" or self.base_manifest_ref.truth_class != "EXACT" or self.base_manifest_ref.freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError("base manifest reference must be exact, current, and canonically owned")
        _validate_manifest_reference_metadata(self.base_manifest_ref)
        object.__setattr__(self, "canonical_intent_digest", _digest(self.canonical_intent_digest, "recipe.intent"))
        object.__setattr__(self, "project_projection_id", _id(self.project_projection_id, "recipe.project_id"))
        object.__setattr__(self, "project_projection_digest", _digest(self.project_projection_digest, "recipe.project_digest"))
        capabilities = _seq(self.capability_ids, "recipe.capabilities", ids=True, max_items=128)
        object.__setattr__(self, "capability_ids", capabilities)
        allowed = set(capabilities)
        try:
            edge_items = _bounded_sequence_snapshot(
                self.dependency_edges, "recipe.dependency_edges", MAX_DEPENDENCY_EDGES
            )
        except ValueError as exc:
            raise ValueError("recipe.dependency_edges must be a bounded sequence") from exc
        edges = tuple(
            _exact_contract_record(edge, DependencyEdge, "recipe.dependency_edges item")
            for edge in edge_items
        )
        if len({(edge.source_capability_id, edge.target_capability_id) for edge in edges}) != len(edges):
            raise ValueError("duplicate recipe dependency")
        if any(edge.source_capability_id not in allowed or edge.target_capability_id not in allowed for edge in edges):
            raise ValueError("invalid recipe dependency")
        _acyclic(capabilities, edges)
        object.__setattr__(self, "dependency_edges", tuple(sorted(edges, key=lambda edge: (edge.source_capability_id, edge.target_capability_id))))
        adapters = _refs(self.adapter_refs, "adapter_refs", require_current=True)
        evidence = _refs(self.evidence_refs, "evidence_refs", require_current=True)
        reference_ids = [
            self.base_manifest_ref.reference_id,
            *(item.reference_id for item in adapters),
            *(item.reference_id for item in evidence),
        ]
        if len(set(reference_ids)) != len(reference_ids):
            raise ValueError(
                "duplicate recipe reference IDs across manifest, adapter, and evidence roles"
            )
        object.__setattr__(self, "adapter_refs", adapters)
        object.__setattr__(self, "evidence_refs", evidence)
        object.__setattr__(self, "domain_owner_handoff_map", _owner_map(self.domain_owner_handoff_map))
        object.__setattr__(
            self,
            "budgets",
            _exact_contract_record(self.budgets, WorkspaceBudget, "recipe.budgets"),
        )
        if self.budgets.network_calls != 0:
            raise ValueError("recipe budget must keep network_calls at zero")
        if self.budgets.model_calls != 0:
            raise ValueError("recipe budget must keep model_calls at zero")
        budget_values = self.budgets.to_dict()
        for name, ceiling in _PR1_RESOURCE_CEILINGS.items():
            if budget_values[name] > ceiling:
                raise ValueError(f"budget.{name} exceeds the PR1 safe ceiling")
        for name, ids, limit, sort_values in (("renderer_requirements", False, 32, True), ("device_requirements", False, 32, True), ("allowed_interaction_actions", True, 64, False), ("required_verification_gates", True, 64, False)):
            object.__setattr__(self, name, _seq(getattr(self, name), f"recipe.{name}", ids=ids, max_items=limit, sort=sort_values))
        object.__setattr__(
            self,
            "issued_at_epoch_seconds",
            _int(
                self.issued_at_epoch_seconds,
                "recipe.issued_at_epoch_seconds",
                1,
                MAX_TIMESTAMP,
            ),
        )
        object.__setattr__(
            self,
            "expires_at_epoch_seconds",
            _int(
                self.expires_at_epoch_seconds,
                "recipe.expires_at_epoch_seconds",
                1,
                MAX_TIMESTAMP,
            ),
        )
        object.__setattr__(self, "ttl_seconds", _int(self.ttl_seconds, "recipe.ttl", 1, MAX_TTL_SECONDS))
        if self.expires_at_epoch_seconds - self.issued_at_epoch_seconds != self.ttl_seconds:
            raise ValueError("recipe absolute expiration must equal issue time plus TTL")
        if self.budgets.wall_time_ms > self.ttl_seconds * 1000:
            raise ValueError("budget.wall_time_ms cannot exceed recipe TTL")
        object.__setattr__(
            self,
            "lifecycle_policy",
            _fixed_text(self.lifecycle_policy, "recipe.lifecycle_policy", _LIFECYCLE_POLICY),
        )
        object.__setattr__(
            self,
            "dissolution_policy",
            _fixed_text(self.dissolution_policy, "recipe.dissolution_policy", _DISSOLUTION_POLICY),
        )
        for name in ("automatic_persistence", "automatic_resume", "automatic_promotion"):
            _bool(getattr(self, name), f"recipe.{name}", False)
        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "recipe.authority"),
        )
        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "recipe.version", EPHEMERAL_WORKSPACE_RECIPE_VERSION),
        )
        self._validate_frozen_demonstration()
        identity_body = self.to_dict()
        identity_body.pop("recipe_id")
        identity_body.pop("recipe_digest")
        expected_recipe_id = _compiled_recipe_id(identity_body)
        if self.recipe_id != expected_recipe_id:
            raise ValueError(
                f"recipe.recipe_id does not match behavior-defining content: expected {expected_recipe_id}, got {self.recipe_id}"
            )
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
                "issued_at_epoch_seconds": self.issued_at_epoch_seconds,
                "expires_at_epoch_seconds": self.expires_at_epoch_seconds,
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
                    "required_verification_gates", "issued_at_epoch_seconds",
                    "expires_at_epoch_seconds", "ttl_seconds", "lifecycle_policy",
                    "dissolution_policy", "automatic_persistence", "automatic_resume",
                    "automatic_promotion", "authority", "recipe_digest"}
        detached = _detached_serialized_record(
            payload, expected, "recipe", digest_field="recipe_digest"
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
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
        expected_manifest = _exact_contract_record(
            expected_base_manifest_ref,
            CanonicalReference,
            "expected_base_manifest_ref",
        )
        if self.base_manifest_ref.to_dict() != expected_manifest.to_dict():
            raise ValueError("stale base manifest canonical reference")
        if self.base_manifest_ref.freshness_class not in _CURRENT_FRESHNESS:
            raise ValueError("stale base manifest canonical reference")
        _validate_reference_set(self.adapter_refs, expected_adapter_refs, "adapter")
        _validate_reference_set(self.evidence_refs, expected_evidence_refs, "evidence")
        if expected_recipe is None:
            raise ValueError("expected_recipe is required")
        expected = _exact_contract_record(
            expected_recipe, EphemeralWorkspaceRecipe, "expected_recipe"
        )
        if self.to_dict() != expected.to_dict():
            raise ValueError("stale complete recipe identity")
        _require_unexpired_recipe(self)


def _require_unexpired_recipe(recipe: EphemeralWorkspaceRecipe) -> None:
    """Reject admission after the recipe's signed absolute expiration boundary."""
    now = _finite_number(time.time(), "current time")
    if now >= recipe.expires_at_epoch_seconds:
        raise ValueError("workspace recipe is expired")


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
        object.__setattr__(
            self,
            "evidence_ref",
            _exact_contract_record(
                self.evidence_ref,
                CanonicalReference,
                "referent.evidence_ref",
            ),
        )
        if (
            self.evidence_ref.truth_class != "EXACT"
            or self.evidence_ref.freshness_class not in _CURRENT_FRESHNESS
        ):
            raise ValueError("referent evidence must be current or bounded and EXACT")
        sources = _seq(self.input_sources, "referent.input_sources", max_items=7, sort=True, upper=True)
        if not sources or not set(sources) <= _INPUTS:
            raise ValueError("unsupported referent input source")
        object.__setattr__(self, "input_sources", sources)
        object.__setattr__(
            self,
            "version",
            _fixed_text(self.version, "referent.version", SPATIAL_REFERENT_BINDING_VERSION),
        )
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
        detached = _detached_serialized_record(
            payload,
            {"version", "binding_id", "scene_id", "scene_digest", "session_id", "session_digest", "entity_id", "entity_digest", "confidence", "evidence_ref", "input_sources", "binding_digest"},
            "referent",
            digest_field="binding_digest",
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
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
        try:
            target_items = _bounded_sequence_snapshot(
                self.target_candidates, "observation.target_candidates", 32
            )
        except ValueError as exc:
            raise ValueError("observation requires a bounded target sequence") from exc
        if not target_items:
            raise ValueError("observation requires a bounded target sequence")
        targets = tuple(
            _exact_contract_record(item, SpatialReferentBinding, "observation.target_candidates item")
            for item in target_items
        )
        if len({target.binding_id for target in targets}) != len(targets):
            raise ValueError("observation requires unique target binding IDs")
        entity_ids = [target.entity_id for target in targets]
        if len(set(entity_ids)) != len(entity_ids):
            raise ValueError("observation requires unique target entity IDs")
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
        object.__setattr__(
            self,
            "evidence_class",
            _enum_text(self.evidence_class, "observation.evidence_class", _EVIDENCE),
        )
        object.__setattr__(self, "tracking_quality", _prob(self.tracking_quality, "observation.tracking_quality"))
        _bool(self.raw_sensor_retained, "observation.raw_sensor_retained", False)
        object.__setattr__(
            self,
            "authority",
            _exact_authority_envelope(self.authority, "observation.authority"),
        )
        object.__setattr__(
            self,
            "version",
            _fixed_text(
                self.version,
                "observation.version",
                MULTIMODAL_SPATIAL_OBSERVATION_VERSION,
            ),
        )
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
        detached = _detached_serialized_record(
            payload,
            {"version", "observation_id", "scene_id", "scene_digest", "session_id", "session_digest", "input_sources", "normalized_event", "normalized_action", "target_candidates", "speech_text", "transcript_digest", "temporal_window_start_ms", "temporal_window_end_ms", "provider_class", "evidence_class", "tracking_quality", "raw_sensor_retained", "authority", "observation_digest"},
            "observation",
            digest_field="observation_digest",
        )
        record = cls(**detached)
        _require_exact_serialized_form(record, detached)
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
        try:
            entity_pairs = _bounded_mapping_snapshot(
                expected_entity_digests, "expected_entity_digests", 32
            )
        except ValueError as exc:
            raise ValueError("entity reference set mismatch") from exc
        expected_entities: dict[str, Any] = {}
        for key, value in entity_pairs:
            entity_id = _id(key, "expected entity identifier")
            if entity_id in expected_entities:
                raise ValueError(
                    f"duplicate expected entity identifier: {entity_id}"
                )
            expected_entities[entity_id] = value
        if len(expected_entities) != len(self.target_candidates):
            raise ValueError("entity reference set mismatch")
        entity_ids = {target.entity_id for target in self.target_candidates}
        if entity_ids != set(expected_entities):
            raise ValueError("entity reference set mismatch")
        for target in self.target_candidates:
            if target.entity_digest != _digest(expected_entities[target.entity_id], "expected entity"):
                raise ValueError(f"stale scene entity: {target.entity_id}")
        _validate_reference_set(
            tuple(target.evidence_ref for target in self.target_candidates),
            expected_evidence_refs,
            "referent evidence",
        )
        if expected_observation is None:
            raise ValueError("expected_observation is required")
        expected = _exact_contract_record(
            expected_observation, MultimodalSpatialObservation, "expected_observation"
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
    if cost_usd > 0:
        raise ValueError("base manifest paid cost authority must remain disabled")
    maximum_cost_usd = MAX_INTEGER / 1_000_000
    if cost_usd > maximum_cost_usd:
        raise ValueError(
            "base manifest resource_budget.cost_usd exceeds the micro-USD ceiling"
        )
    limits["cost_microusd"] = int(math.floor(cost_usd * 1_000_000))
    if limits["network_calls"] != 0:
        raise ValueError("base manifest network access must remain disabled")
    if limits["model_calls"] != 0:
        raise ValueError("base manifest model invocation must remain disabled")
    return {
        name: min(limits.get(name, ceiling), ceiling)
        for name, ceiling in _PR1_RESOURCE_CEILINGS.items()
    }


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
    lease_id = _id(lease.get("lease_id"), "base manifest arena_lease.lease_id")
    lease_identity_body = dict(lease)
    lease_identity_body.pop("phase_hash")
    lease_identity_body.pop("lease_id")
    expected_lease_id = "LEASE-" + hashlib.blake2b(
        json.dumps(
            lease_identity_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8"),
        digest_size=16,
    ).hexdigest()[:12]
    if lease_id != expected_lease_id:
        raise ValueError("base manifest arena_lease lease_id does not match content")
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
    if frozenset(granted) not in _LEGACY_CLOSED_GRANT_PROFILES:
        raise ValueError("base manifest grants do not match the closed canonical V1 profile")
    requested = _require_sequence(body.get("requested_capabilities"), "base manifest requested_capabilities")
    requested_grants: set[str] = set()
    requested_denials: dict[str, str] = {}
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
        denied_reason = _text(
            request.get("denied_reason"),
            f"base manifest requested_capabilities[{index}].denied_reason",
            optional=True,
        )
        if request["granted"]:
            if denied_reason:
                raise ValueError("granted capability requests must not carry denial reasons")
            if capability not in _LEGACY_ALLOWED_CAPABILITIES:
                raise ValueError("base manifest request grants a forbidden or unknown capability")
            requested_grants.add(capability)
        else:
            if not denied_reason:
                raise ValueError("denied capability requests require a denial reason")
            requested_denials[capability] = denied_reason
    if requested_grants != granted:
        raise ValueError("base manifest granted_capabilities disagree with capability requests")
    _validate_v1_arena_lease(
        body.get("arena_lease"),
        organ_id=body["organ_id"],
        granted_capabilities=granted,
    )

    denial_rows: dict[str, str] = {}
    for index, raw_denial in enumerate(_require_sequence(body.get("denied_capabilities"), "base manifest denied_capabilities")):
        denial = _require_mapping(raw_denial, f"base manifest denied_capabilities[{index}]")
        _strict(denial, {"capability", "reason"}, f"base manifest denied_capabilities[{index}]")
        capability = _id(
            denial.get("capability"),
            f"base manifest denied_capabilities[{index}].capability",
        )
        reason = _id(
            denial.get("reason"),
            f"base manifest denied_capabilities[{index}].reason",
        )
        if capability in denial_rows:
            raise ValueError("base manifest contains duplicate capability denials")
        if capability in granted:
            raise ValueError("base manifest cannot both grant and deny a capability")
        denial_rows[capability] = reason
    if denial_rows != requested_denials:
        raise ValueError("base manifest denied_capabilities disagree with denied requests")

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
    forbidden_paths = frozenset(_seq(
        data_policy.get("forbidden_paths"),
        "base manifest data_policy.forbidden_paths",
        max_items=32,
        sort=True,
    ))
    if forbidden_paths != _LEGACY_REQUIRED_FORBIDDEN_PATHS:
        raise ValueError("base manifest forbidden paths do not match the closed PR1 denylist")
    for name in ("private_memory_export", "raw_sidecar_dump", "secrets_access"):
        _bool(data_policy.get(name), f"base manifest data_policy.{name}", False)
    ui_manifest = _require_mapping(body.get("ui_manifest"), "base manifest ui_manifest")
    _strict(ui_manifest, {"component_types", "schema", "executable"}, "base manifest ui_manifest")
    component_types = frozenset(_seq(
        ui_manifest.get("component_types"),
        "base manifest ui_manifest.component_types",
        ids=True,
        max_items=32,
        sort=True,
    ))
    if component_types != _LEGACY_CLOSED_UI_COMPONENT_TYPES:
        raise ValueError("base manifest UI components do not match the closed canonical V1 profile")
    ui_schema = _require_mapping(ui_manifest.get("schema"), "base manifest ui_manifest.schema")
    if ui_schema:
        raise ValueError("base manifest UI schema must be empty in the non-operational PR1 wrapper")
    _bool(ui_manifest.get("executable"), "base manifest ui_manifest.executable", False)
    limits = _manifest_resource_limits(body)
    if limits["network_calls"] != 0:
        raise ValueError("base manifest network access must remain disabled")
    if limits["model_calls"] != 0:
        raise ValueError("base manifest model invocation must remain disabled")
    verifier = _require_mapping(body.get("verifier_requirements"), "base manifest verifier_requirements")
    _strict(
        verifier,
        {"must_pass", "quality_gate"},
        "base manifest verifier_requirements",
    )
    required_verifiers = {"no_production_mutation", "no_secret_access", "no_network_access"}
    must_pass = set(_seq(verifier.get("must_pass"), "base manifest verifier_requirements.must_pass", ids=True, sort=True))
    if must_pass != required_verifiers:
        raise ValueError("base manifest verifier requirements do not match the closed PR1 profile")
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


def _bounded_manifest_export(manifest: Any) -> Any:
    """Export a live V1 manifest while normalizing hostile export callbacks."""
    try:
        exporter = getattr(manifest, "to_dict", None)
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError("base manifest nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError("base manifest has an invalid export protocol") from exc
    if exporter is None:
        return manifest
    if not callable(exporter):
        raise ValueError("base manifest has an invalid export protocol")
    try:
        return exporter()
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError("base manifest nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError("base manifest has an invalid export protocol") from exc


def _manifest_snapshot(raw_manifest: Any) -> tuple[dict[str, Any], str, str]:
    """Verify one already-exported safe V1 manifest snapshot into a wrapper identity."""
    body = _canonical(raw_manifest)
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
                                             expected_project_projection: ProjectContextProjection | Mapping[str, Any],
                                             canonical_intent_digest: str,
                                             adapter_refs: Sequence[CanonicalReference | Mapping[str, Any]],
                                             evidence_refs: Sequence[CanonicalReference | Mapping[str, Any]],
                                             budgets: WorkspaceBudget | Mapping[str, Any] | None = None,
                                             ttl_seconds: int = 300,
                                             expected_manifest_timestamps: Sequence[int | float] | None = None) -> EphemeralWorkspaceRecipe:
    """Compile the frozen recipe without invoking any canonical owner."""
    exported = _bounded_manifest_export(base_manifest)
    body, legacy_digest, source_snapshot_digest = _manifest_snapshot(exported)
    project_record = _exact_contract_record(
        project_projection, ProjectContextProjection, "project_projection"
    )
    project = validate_project_semantics(
        project_record.to_dict(), expected_projection=expected_project_projection
    )
    projection_body = {
        "version": _MANIFEST_PROJECTION_VERSION,
        "source_manifest_version": body["manifest_version"],
        "source_organ_id": body["organ_id"],
        "source_manifest_digest": source_snapshot_digest,
        "source_legacy_manifest_digest": legacy_digest,
        "effective_capability_ids": sorted(_LEGACY_REQUIRED_WORKSPACE_CAPABILITIES),
        "effective_ui_component_types": [],
        "effective_resource_ceilings": _manifest_resource_limits(body),
        "authority_non_escalation": True,
    }
    projection_digest = stable_digest(projection_body)
    manifest_identity = projection_digest[:32]
    manifest_ref = CanonicalReference(
        f"organ-manifest-projection:{manifest_identity}",
        "aura_ephemeral_manifest",
        f"ephemeral-organ-projection:{manifest_identity}@{body['manifest_version']}",
        projection_digest,
        metadata={
            "manifest_version": body["manifest_version"],
            "legacy_manifest_digest": legacy_digest,
            "source_digest": source_snapshot_digest,
            "wrapped_not_replaced": True,
        },
    )
    intent = _digest(canonical_intent_digest, "canonical intent")
    requested_ttl = _int(ttl_seconds, "recipe.ttl", 1, MAX_TTL_SECONDS)
    manifest_ttl = _int(body.get("ttl_seconds"), "base manifest ttl", 1, MAX_TTL_SECONDS)
    created_at = _finite_number(body.get("created_at"), "base manifest created_at")
    expires_at = _finite_number(body.get("expires_at"), "base manifest expires_at")
    try:
        timestamp_binding = _bounded_sequence_snapshot(
            expected_manifest_timestamps,
            "expected base manifest timestamps",
            2,
        )
    except ValueError as exc:
        raise ValueError("base manifest requires trusted timestamp bindings") from exc
    if len(timestamp_binding) != 2:
        raise ValueError("base manifest requires trusted timestamp bindings")
    expected_created_at = _finite_number(
        timestamp_binding[0],
        "expected base manifest created_at",
    )
    expected_expires_at = _finite_number(
        timestamp_binding[1],
        "expected base manifest expires_at",
    )
    if (created_at, expires_at) != (expected_created_at, expected_expires_at):
        raise ValueError("base manifest timestamp binding mismatch")
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
    issued_at_epoch_seconds = _int(
        math.floor(now), "recipe issued_at_epoch_seconds", 1, MAX_TIMESTAMP
    )
    expires_at_epoch_seconds = issued_at_epoch_seconds + effective_ttl
    if expires_at_epoch_seconds > math.floor(expires_at):
        raise ValueError("recipe absolute expiration exceeds base manifest expiry")

    manifest_limits = _manifest_resource_limits(body)
    if budgets is None:
        default_values = WorkspaceBudget().to_dict()
        for name, ceiling in manifest_limits.items():
            default_values[name] = min(default_values[name], ceiling)
        default_values["wall_time_ms"] = min(default_values["wall_time_ms"], effective_ttl * 1000)
        budget = WorkspaceBudget.from_dict(default_values)
    else:
        budget = _exact_contract_record(budgets, WorkspaceBudget, "budgets")
    budget_values = budget.to_dict()
    for name, ceiling in manifest_limits.items():
        if budget_values[name] > ceiling:
            raise ValueError(f"budget.{name} exceeds base manifest resource ceiling")
    if budget.wall_time_ms > effective_ttl * 1000:
        raise ValueError("budget.wall_time_ms cannot exceed effective workspace TTL")
    adapters = _refs(adapter_refs, "adapter_refs", require_current=True)
    evidence = _refs(evidence_refs, "evidence_refs", require_current=True)
    definition = CODING_SPATIAL_WORKSPACE_V1_DEFINITION
    recipe_values = {
        "version": EPHEMERAL_WORKSPACE_RECIPE_VERSION,
        "demonstration_id": CODING_SPATIAL_WORKSPACE_V1,
        "base_manifest_ref": manifest_ref.to_dict(),
        "canonical_intent_digest": intent,
        "project_projection_id": project.projection_id,
        "project_projection_digest": project.projection_digest,
        "capability_ids": list(definition["capability_ids"]),
        "dependency_edges": [
            edge.to_dict()
            for edge in sorted(
                (DependencyEdge(source, target) for source, target in definition["dependency_edges"]),
                key=lambda edge: (edge.source_capability_id, edge.target_capability_id),
            )
        ],
        "adapter_refs": [reference.to_dict() for reference in adapters],
        "evidence_refs": [reference.to_dict() for reference in evidence],
        "domain_owner_handoff_map": dict(definition["domain_owner_handoff_map"]),
        "budgets": budget.to_dict(),
        "renderer_requirements": sorted(definition["renderer_requirements"]),
        "device_requirements": sorted(definition["device_requirements"]),
        "allowed_interaction_actions": list(definition["allowed_interaction_actions"]),
        "required_verification_gates": list(definition["required_verification_gates"]),
        "issued_at_epoch_seconds": issued_at_epoch_seconds,
        "expires_at_epoch_seconds": expires_at_epoch_seconds,
        "ttl_seconds": effective_ttl,
        "lifecycle_policy": _LIFECYCLE_POLICY,
        "dissolution_policy": _DISSOLUTION_POLICY,
        "automatic_persistence": False,
        "automatic_resume": False,
        "automatic_promotion": False,
        "authority": AuthorityEnvelope().to_dict(),
    }
    return EphemeralWorkspaceRecipe(
        recipe_id=_compiled_recipe_id(recipe_values),
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
        issued_at_epoch_seconds=issued_at_epoch_seconds,
        expires_at_epoch_seconds=expires_at_epoch_seconds,
        ttl_seconds=effective_ttl,
    )


def validate_recipe_semantics(
    payload: Mapping[str, Any],
    *,
    expected_recipe: EphemeralWorkspaceRecipe | Mapping[str, Any] | None = None,
) -> EphemeralWorkspaceRecipe:
    """Parse then admit a recipe only against an independently trusted expectation."""
    record = EphemeralWorkspaceRecipe.from_dict(payload)
    if expected_recipe is None:
        raise ValueError("expected_recipe is required for bound recipe admission")
    expected = _exact_contract_record(
        expected_recipe, EphemeralWorkspaceRecipe, "expected_recipe"
    )
    if record.to_dict() != expected.to_dict():
        raise ValueError("stale complete recipe identity")
    _require_unexpired_recipe(record)
    return record


def validate_project_semantics(
    payload: Mapping[str, Any],
    *,
    expected_projection: ProjectContextProjection | Mapping[str, Any] | None = None,
) -> ProjectContextProjection:
    """Parse then admit a project only against an independently trusted projection."""
    record = ProjectContextProjection.from_dict(payload)
    if expected_projection is None:
        raise ValueError("expected_projection is required for bound project admission")
    expected = _exact_contract_record(
        expected_projection, ProjectContextProjection, "expected_projection"
    )
    record.validate_bindings(expected_projection=expected)
    return record


def validate_observation_semantics(
    payload: Mapping[str, Any],
    *,
    expected_observation: MultimodalSpatialObservation | Mapping[str, Any] | None = None,
) -> MultimodalSpatialObservation:
    """Parse then admit an observation only against independently trusted evidence."""
    record = MultimodalSpatialObservation.from_dict(payload)
    if expected_observation is None:
        raise ValueError("expected_observation is required for bound observation admission")
    expected = _exact_contract_record(
        expected_observation, MultimodalSpatialObservation, "expected_observation"
    )
    expected_entities: dict[str, str] = {}
    for target in expected.target_candidates:
        if target.entity_id in expected_entities:
            raise ValueError("trusted observation contains duplicate entity identifiers")
        expected_entities[target.entity_id] = target.entity_digest
    expected_evidence = {
        target.evidence_ref.reference_id: target.evidence_ref.to_dict()
        for target in expected.target_candidates
    }
    record.validate_bindings(
        expected_scene_id=expected.scene_id,
        expected_scene_digest=expected.scene_digest,
        expected_session_id=expected.session_id,
        expected_session_digest=expected.session_digest,
        expected_entity_digests=expected_entities,
        expected_evidence_refs=expected_evidence,
        expected_observation=expected,
    )
    return record


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
