"""Hardened canonical Aura event and tool-decision contracts.

Records bounded explanations beside calls without changing tool schemas or
storing private chain-of-thought. Runtime dependencies are stdlib only.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, BinaryIO

if os.name == "nt":
    import msvcrt as _file_lock_backend
else:
    import fcntl as _file_lock_backend

EVENT_CONTRACTS_VERSION = "AURA_EVENT_CONTRACTS_V1"
SCHEMA_VERSION = "1.0"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
DEFAULT_RATIONALE_LIMIT = 240
DEFAULT_EXPECTATION_LIMIT = 320
DEFAULT_ALTERNATIVE_LIMIT = 3

_SECRET_PATTERNS = (
    re.compile(
        r"""(?ix)
        ["']?
        (?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|
           authorization|secret|password|private[_-]?key|token|
           [a-z0-9_.-]+[_-]token)
        ["']?\s*[:=]\s*
        (?:bearer\s+)?
        (?:
            "(?:\\.|[^"\\])*"
          | '(?:\\.|[^'\\])*'
          | [^\s,{}&;]+
        )
        """
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=%\-]+"),
    re.compile(r"\bsk-[A-Za-z0-9._~+/=%\-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


def _normalize_field_name(value: Any) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value).strip())
    return text.lower().replace("-", "_").replace(" ", "_")


_PRIVATE_REASONING_KEYS = frozenset(
    {
        "chain_of_thought",
        "chain-of-thought",
        "cot",
        "hidden_reasoning",
        "private_reasoning",
        "inner_thought",
        "innerthought",
        "scratchpad",
        "scratch_pad",
    }
)
_NORMALIZED_PRIVATE_REASONING_KEYS = frozenset(
    _normalize_field_name(item) for item in _PRIVATE_REASONING_KEYS
)
_COMPACT_PRIVATE_REASONING_KEYS = frozenset(
    item.replace("_", "") for item in _NORMALIZED_PRIVATE_REASONING_KEYS
)
_PRIVATE_REASONING_SUFFIXES = tuple(
    f"_{item}" for item in sorted(_NORMALIZED_PRIVATE_REASONING_KEYS)
)


def _is_private_reasoning_field(normalized: str) -> bool:
    compact = normalized.replace("_", "")
    return (
        normalized in _NORMALIZED_PRIVATE_REASONING_KEYS
        or normalized.endswith(_PRIVATE_REASONING_SUFFIXES)
        or compact in _COMPACT_PRIVATE_REASONING_KEYS
        or any(compact.endswith(item) for item in _COMPACT_PRIVATE_REASONING_KEYS)
    )
_SECRET_FIELDS = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "auth_token",
        "authorization",
        "password",
        "private_key",
        "secret",
        "token",
    }
)
_SECRET_SUFFIXES = (
    "_api_key",
    "_access_token",
    "_auth_token",
    "_token",
    "_password",
    "_private_key",
    "_secret",
)
_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


class ActorType(str, Enum):
    HUMAN = "HUMAN"
    COMMUNITY = "COMMUNITY"
    AURA = "AURA"
    MODEL = "MODEL"
    TOOL = "TOOL"
    VERIFIER = "VERIFIER"


class DIKWPStage(str, Enum):
    DATA = "DATA"
    INFORMATION = "INFORMATION"
    KNOWLEDGE = "KNOWLEDGE"
    WISDOM = "WISDOM"
    PURPOSE = "PURPOSE"


class DecisionKind(str, Enum):
    SELECT = "SELECT"
    REJECT = "REJECT"
    PARALLELIZE = "PARALLELIZE"
    FALLBACK = "FALLBACK"
    ESCALATE = "ESCALATE"


class MeasurementClass(str, Enum):
    MODEL_ESTIMATED = "MODEL_ESTIMATED"
    HEURISTIC = "HEURISTIC"
    DERIVED = "DERIVED"
    EMPIRICAL = "EMPIRICAL"
    VERIFIER_BACKED = "VERIFIER_BACKED"
    UNAVAILABLE = "UNAVAILABLE"


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _canonicalize(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        items = [_canonicalize(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are not permitted in Aura event records")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_digest(value: Any, *, digest_size: int = 16) -> str:
    if not 1 <= int(digest_size) <= 64:
        raise ValueError("digest_size must be between 1 and 64 bytes")
    return hashlib.blake2b(
        canonical_json(value).encode("utf-8"), digest_size=int(digest_size)
    ).hexdigest()


def stable_id(prefix: str, value: Any, *, digest_size: int = 12) -> str:
    clean = "".join(
        ch if ch.isalnum() or ch in "-_" else "-"
        for ch in str(prefix).strip().lower()
    )
    if not clean:
        raise ValueError("stable_id prefix must not be empty")
    return f"{clean}_{stable_digest(value, digest_size=digest_size)}"


def _required(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _enum(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value)
    if raw not in {item.value for item in enum_type}:
        raise ValueError(f"unknown {field_name}: {raw}")
    return raw


def _bounded(value: Any, field_name: str, limit: int, *, required: bool = True) -> str:
    normalized = " ".join(str(value or "").split())
    if required and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) > int(limit):
        raise ValueError(f"{field_name} exceeds {limit} characters")
    return redact_secrets(normalized)


def _probability(value: float | None, field_name: str) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return number


def _nonnegative(value: float | None, field_name: str) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return number


def redact_secrets(value: str) -> str:
    redacted = str(value)
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _sanitize_payload(value: Any) -> tuple[Any, bool]:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        changed = not isinstance(value, dict)
        for key, item in value.items():
            key_text = str(key)
            changed = changed or not isinstance(key, str)
            normalized = _normalize_field_name(key_text)
            if _is_private_reasoning_field(normalized):
                raise ValueError(f"private reasoning field is prohibited: {key_text}")
            if normalized in _SECRET_FIELDS or normalized.endswith(_SECRET_SUFFIXES):
                result[key_text] = "[REDACTED]"
                changed = True
            else:
                sanitized, item_changed = _sanitize_payload(item)
                result[key_text] = sanitized
                changed = changed or item_changed
        return result, changed
    if isinstance(value, list):
        result = []
        changed = False
        for item in value:
            sanitized, item_changed = _sanitize_payload(item)
            result.append(sanitized)
            changed = changed or item_changed
        return result, changed
    if isinstance(value, tuple):
        result, _changed = _sanitize_payload(list(value))
        return result, True
    if isinstance(value, (set, frozenset)):
        result, _changed = _sanitize_payload(sorted(value, key=str))
        return result, True
    if isinstance(value, str):
        redacted = redact_secrets(value)
        return redacted, redacted != value
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}, True
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are not permitted in event payloads")
    if value is None or isinstance(value, (bool, int, float)):
        return value, False
    if isinstance(value, Enum):
        sanitized, _changed = _sanitize_payload(value.value)
        return sanitized, True
    if is_dataclass(value):
        sanitized, _changed = _sanitize_payload(asdict(value))
        return sanitized, True
    text = redact_secrets(str(value))
    return text, True


def sanitize_payload(value: Any) -> Any:
    """Redact secrets and reject fields intended for private reasoning."""
    sanitized, _changed = _sanitize_payload(value)
    return sanitized


def _thread_lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


def _acquire_process_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        if not handle.read(1):
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        _file_lock_backend.locking(handle.fileno(), _file_lock_backend.LK_LOCK, 1)
    else:
        _file_lock_backend.flock(handle.fileno(), _file_lock_backend.LOCK_EX)


def _release_process_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        _file_lock_backend.locking(handle.fileno(), _file_lock_backend.LK_UNLCK, 1)
    else:
        _file_lock_backend.flock(handle.fileno(), _file_lock_backend.LOCK_UN)


@contextmanager
def _exclusive_store_lock(path: Path) -> Iterator[None]:
    thread_lock = _thread_lock_for(path)
    with thread_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            _acquire_process_lock(handle)
            try:
                yield
            finally:
                _release_process_lock(handle)


@dataclass(frozen=True)
class ExactPayloadRef:
    ref_id: str
    kind: str
    path: str
    payload_digest: str
    byte_count: int
    redacted: bool
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class AuraEventEnvelope:
    event_id: str
    trace_id: str
    parent_event_ids: tuple[str, ...]
    event_type: str
    schema_version: str
    actor_id: str
    actor_type: str
    arena_id: str
    board_id: str
    node_id: str
    objective_id: str
    purpose_digest: str
    dikwp_stage: str
    payload_ref: str
    payload_digest: str
    evidence_refs: tuple[str, ...]
    policy_scope: str
    proposal_only: bool
    measurement_classes: dict[str, str]
    confidence: float | None
    uncertainty: float | None
    created_at: float
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        trace_id: str,
        event_type: str,
        actor_id: str,
        actor_type: str | ActorType,
        purpose_digest: str,
        dikwp_stage: str | DIKWPStage,
        payload_ref: str,
        payload_digest: str,
        parent_event_ids: Iterable[str] = (),
        arena_id: str = "",
        board_id: str = "",
        node_id: str = "",
        objective_id: str = "",
        evidence_refs: Iterable[str] = (),
        policy_scope: str = "",
        proposal_only: bool = True,
        measurement_classes: Mapping[str, str | MeasurementClass] | None = None,
        confidence: float | None = None,
        uncertainty: float | None = None,
        created_at: float | None = None,
    ) -> "AuraEventEnvelope":
        payload = {
            "trace_id": _required(trace_id, "trace_id"),
            "parent_event_ids": tuple(str(item) for item in parent_event_ids),
            "event_type": _required(event_type, "event_type"),
            "schema_version": SCHEMA_VERSION,
            "actor_id": _required(actor_id, "actor_id"),
            "actor_type": _enum(actor_type, ActorType, "actor_type"),
            "arena_id": str(arena_id),
            "board_id": str(board_id),
            "node_id": str(node_id),
            "objective_id": str(objective_id),
            "purpose_digest": _required(purpose_digest, "purpose_digest"),
            "dikwp_stage": _enum(dikwp_stage, DIKWPStage, "dikwp_stage"),
            "payload_ref": _required(payload_ref, "payload_ref"),
            "payload_digest": _required(payload_digest, "payload_digest"),
            "evidence_refs": tuple(str(item) for item in evidence_refs),
            "policy_scope": str(policy_scope),
            "proposal_only": bool(proposal_only),
            "measurement_classes": {
                str(key): _enum(value, MeasurementClass, f"measurement class for {key}")
                for key, value in dict(measurement_classes or {}).items()
            },
            "confidence": _probability(confidence, "confidence"),
            "uncertainty": _probability(uncertainty, "uncertainty"),
            "created_at": time.time() if created_at is None else float(created_at),
        }
        return cls(event_id=stable_id("event", payload), **payload)

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class ToolDecisionRecord:
    decision_id: str
    trace_id: str
    board_id: str
    node_id: str
    tool_id: str
    capability_ids: tuple[str, ...]
    decision_kind: str
    decision_rationale: str
    expected_information: str
    advantage_over_alternatives: str
    alternatives_considered: tuple[str, ...]
    confidence_estimate: float | None
    confidence_measurement_class: str
    uncertainty_reasons: tuple[str, ...]
    required_evidence_classes: tuple[str, ...]
    expected_cost: dict[str, Any]
    expected_latency_ms: float | None
    expected_risk: str
    tool_input_digest: str
    authorization_ref: str
    proposal_only: bool
    created_at: float
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        trace_id: str,
        tool_id: str,
        decision_kind: str | DecisionKind,
        decision_rationale: str,
        expected_information: str,
        tool_input: Any,
        capability_ids: Iterable[str] = (),
        board_id: str = "",
        node_id: str = "",
        advantage_over_alternatives: str = "",
        alternatives_considered: Iterable[str] = (),
        confidence_estimate: float | None = None,
        confidence_measurement_class: str | MeasurementClass = MeasurementClass.UNAVAILABLE,
        uncertainty_reasons: Iterable[str] = (),
        required_evidence_classes: Iterable[str] = (),
        expected_cost: Mapping[str, Any] | None = None,
        expected_latency_ms: float | None = None,
        expected_risk: str = "LOW",
        authorization_ref: str = "",
        proposal_only: bool = True,
        created_at: float | None = None,
        rationale_limit: int = DEFAULT_RATIONALE_LIMIT,
    ) -> "ToolDecisionRecord":
        alternatives = tuple(
            _bounded(item, "alternative", DEFAULT_RATIONALE_LIMIT)
            for item in alternatives_considered
        )
        if len(alternatives) > DEFAULT_ALTERNATIVE_LIMIT:
            raise ValueError(
                f"alternatives_considered is capped at {DEFAULT_ALTERNATIVE_LIMIT}"
            )
        confidence = _probability(confidence_estimate, "confidence_estimate")
        confidence_class = _enum(
            confidence_measurement_class,
            MeasurementClass,
            "confidence_measurement_class",
        )
        if confidence is not None and confidence_class == MeasurementClass.UNAVAILABLE.value:
            raise ValueError(
                "confidence_measurement_class must be explicit when confidence_estimate is present"
            )
        payload = {
            "trace_id": _required(trace_id, "trace_id"),
            "board_id": str(board_id),
            "node_id": str(node_id),
            "tool_id": _required(tool_id, "tool_id"),
            "capability_ids": tuple(str(item) for item in capability_ids),
            "decision_kind": _enum(decision_kind, DecisionKind, "decision_kind"),
            "decision_rationale": _bounded(
                decision_rationale, "decision_rationale", rationale_limit
            ),
            "expected_information": _bounded(
                expected_information, "expected_information", DEFAULT_EXPECTATION_LIMIT
            ),
            "advantage_over_alternatives": _bounded(
                advantage_over_alternatives,
                "advantage_over_alternatives",
                DEFAULT_EXPECTATION_LIMIT,
                required=False,
            ),
            "alternatives_considered": alternatives,
            "confidence_estimate": confidence,
            "confidence_measurement_class": confidence_class,
            "uncertainty_reasons": tuple(
                _bounded(item, "uncertainty reason", DEFAULT_RATIONALE_LIMIT)
                for item in uncertainty_reasons
            ),
            "required_evidence_classes": tuple(
                str(item) for item in required_evidence_classes
            ),
            "expected_cost": sanitize_payload(dict(expected_cost or {})),
            "expected_latency_ms": _nonnegative(
                expected_latency_ms, "expected_latency_ms"
            ),
            "expected_risk": _required(expected_risk, "expected_risk").upper(),
            "tool_input_digest": stable_digest(sanitize_payload(tool_input)),
            "authorization_ref": str(authorization_ref),
            "proposal_only": bool(proposal_only),
            "created_at": time.time() if created_at is None else float(created_at),
        }
        return cls(decision_id=stable_id("tool-decision", payload), **payload)

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


@dataclass(frozen=True)
class ToolResultRecord:
    result_id: str
    decision_id: str
    tool_id: str
    status: str
    output_ref: str
    output_digest: str
    usage_ref: str
    evidence_refs: tuple[str, ...]
    error_class: str
    started_at: float
    finished_at: float
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    @classmethod
    def create(
        cls,
        *,
        decision_id: str,
        tool_id: str,
        status: str,
        output: Any,
        output_ref: str = "",
        usage_ref: str = "",
        evidence_refs: Iterable[str] = (),
        error_class: str = "",
        started_at: float,
        finished_at: float,
    ) -> "ToolResultRecord":
        started, finished = float(started_at), float(finished_at)
        if finished < started:
            raise ValueError("finished_at must be greater than or equal to started_at")
        payload = {
            "decision_id": _required(decision_id, "decision_id"),
            "tool_id": _required(tool_id, "tool_id"),
            "status": _required(status, "status").upper(),
            "output_ref": str(output_ref),
            "output_digest": stable_digest(sanitize_payload(output)),
            "usage_ref": str(usage_ref),
            "evidence_refs": tuple(str(item) for item in evidence_refs),
            "error_class": str(error_class),
            "started_at": started,
            "finished_at": finished,
        }
        return cls(result_id=stable_id("tool-result", payload), **payload)

    def to_dict(self) -> dict[str, Any]:
        return _canonicalize(self)


class AppendOnlyEventStore:
    """Local JSONL event store with immutable, redacted exact sidecars."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.events_path = self.root / "events.jsonl"
        self.sidecars_dir = self.root / "sidecars"
        self.lock_path = self.root / ".event-store.lock"
        self.sidecars_dir.mkdir(parents=True, exist_ok=True)
        with _exclusive_store_lock(self.lock_path):
            self._event_digests = self._load_event_digests()

    def store_payload(
        self,
        payload: Any,
        *,
        kind: str,
        created_at: float | None = None,
    ) -> ExactPayloadRef:
        safe_payload, changed = _sanitize_payload(payload)
        encoded = canonical_json(safe_payload)
        digest = stable_digest(safe_payload)
        safe_kind = re.sub(
            r"[^A-Za-z0-9._-]+", "-", _required(kind, "kind")
        ).strip("-")
        ref_id = stable_id("payload", {"kind": safe_kind, "digest": digest})
        path = self.sidecars_dir / f"{ref_id}.json"
        encoded_bytes = encoded.encode("utf-8")
        with _exclusive_store_lock(self.lock_path):
            if path.exists() and path.read_bytes() != encoded_bytes:
                raise ValueError(f"sidecar collision for {ref_id}")
            if not path.exists():
                temporary = path.with_name(
                    f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
                )
                try:
                    with temporary.open("wb") as handle:
                        handle.write(encoded_bytes)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary, path)
                finally:
                    if temporary.exists():
                        temporary.unlink()
        return ExactPayloadRef(
            ref_id=ref_id,
            kind=safe_kind,
            path=str(path.relative_to(self.root)).replace("\\", "/"),
            payload_digest=digest,
            byte_count=len(encoded_bytes),
            redacted=changed,
            created_at=time.time() if created_at is None else float(created_at),
        )

    def append(self, event: AuraEventEnvelope) -> bool:
        event_payload = event.to_dict()
        encoded = canonical_json(event_payload)
        digest = stable_digest(event_payload)
        with _exclusive_store_lock(self.lock_path):
            current = self._load_event_digests()
            existing = current.get(event.event_id)
            if existing is not None:
                self._event_digests = current
                if existing != digest:
                    raise ValueError(f"event ID collision for {event.event_id}")
                return False
            self.root.mkdir(parents=True, exist_ok=True)
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            current[event.event_id] = digest
            self._event_digests = current
            return True

    def iter_events(self) -> Iterator[dict[str, Any]]:
        with _exclusive_store_lock(self.lock_path):
            if not self.events_path.exists():
                return iter(())
            events: list[dict[str, Any]] = []
            with self.events_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        events.append(json.loads(line))
        return iter(events)

    def _load_event_digests(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if not self.events_path.exists():
            return result
        with self.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                event_id = _required(payload.get("event_id"), "event_id")
                digest = stable_digest(payload)
                if event_id in result and result[event_id] != digest:
                    raise ValueError(f"conflicting duplicate event in store: {event_id}")
                result[event_id] = digest
        return result
