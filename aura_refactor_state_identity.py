"""Deterministic provenance and projection identities for refactor State Ledgers."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID

IDENTITY_VERSION = "AURA_REFACTOR_STATE_IDENTITY_V2"
_MAX_DEPTH = 64


def _type(value: Any) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _key(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None or isinstance(value, (bool, int)):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, float):
        return repr(value) if math.isfinite(value) else f"nonfinite:{repr(value)}"
    return f"<{_type(value)}>"


def normalize(value: Any, *, _seen: set[int] | None = None, _depth: int = 0) -> Any:
    """Return stable JSON data without unbounded recursion or unstable object reprs."""
    if _depth > _MAX_DEPTH:
        return {"__depth_limit__": _type(value)}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"__nonfinite_float__": repr(value)}
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if isinstance(value, (date, datetime)):
        return {"__datetime__": value.isoformat()}
    if isinstance(value, UUID):
        return {"__uuid__": str(value)}
    if isinstance(value, Enum):
        return {"__enum__": _type(value), "value": normalize(value.value, _seen=_seen, _depth=_depth + 1)}
    if isinstance(value, Path):
        return {"__path__": str(value)}
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}

    seen = _seen if _seen is not None else set()
    track = is_dataclass(value) or isinstance(value, (Mapping, list, tuple, set, frozenset))
    identity = id(value)
    if track and identity in seen:
        return {"__cycle__": _type(value)}
    if track:
        seen.add(identity)
    try:
        if is_dataclass(value):
            return normalize(asdict(value), _seen=seen, _depth=_depth + 1)
        if isinstance(value, Mapping):
            try:
                pairs = list(value.items())
            except Exception:
                return {"__invalid_mapping__": _type(value)}
            pairs.sort(key=lambda pair: _key(pair[0]))
            return {
                _key(key): normalize(item, _seen=seen, _depth=_depth + 1)
                for key, item in pairs
            }
        if isinstance(value, (list, tuple)):
            return [normalize(item, _seen=seen, _depth=_depth + 1) for item in value]
        if isinstance(value, (set, frozenset)):
            items = [normalize(item, _seen=seen, _depth=_depth + 1) for item in value]
            return sorted(items, key=canonical)
        return {"__opaque_type__": _type(value)}
    finally:
        if track:
            seen.discard(identity)


def canonical(value: Any) -> str:
    return json.dumps(
        normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def digest(value: Any, *, size: int = 12) -> str:
    return hashlib.blake2b(canonical(value).encode("utf-8"), digest_size=size).hexdigest()


def tokens(value: Any) -> int:
    return (len(canonical(value).encode("utf-8")) + 3) // 4


def history_events(session: Any) -> tuple[list[dict[str, Any]], str]:
    explicit = list(getattr(session, "event_history", []) or [])
    if explicit:
        events = [
            {
                "sequence": index,
                "kind": str(item.get("kind") or "event") if isinstance(item, Mapping) else "event",
                "payload": normalize(item),
            }
            for index, item in enumerate(explicit)
        ]
        return events, "canonical_event_history"
    events: list[dict[str, Any]] = []
    groups = (
        ("turn", list(getattr(session, "turns", []) or [])),
        ("stage", list(getattr(session, "stage_results", []) or [])),
        ("verification", list(getattr(session, "verification_results", []) or [])),
    )
    for kind, values in groups:
        for item in values:
            events.append({"sequence": len(events), "kind": kind, "payload": normalize(item)})
    return events, "collection_order_fallback"


def history_identity(session_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    root = digest({"session_id": session_id, "root": "GENESIS"})
    last = ""
    for index, event in enumerate(events):
        last = digest(event)
        root = digest(
            {
                "session_id": session_id,
                "sequence": index,
                "previous_digest": root,
                "event_digest": last,
            }
        )
    return {
        "history_event_count": len(events),
        "history_root_digest": root,
        "last_event_digest": last,
        "last_sequence_number": len(events) - 1,
    }


def semantic_sets(session: Any) -> dict[str, list[Any]]:
    aliases = {
        "assumptions": ("assumptions", "assumption_set"),
        "unresolved_questions": ("unresolved_questions", "open_questions"),
        "accepted_decisions": ("accepted_decisions", "decisions"),
        "rejected_alternatives": ("rejected_alternatives", "rejected_options"),
    }
    result: dict[str, list[Any]] = {}
    for name, fields in aliases.items():
        value: Any = []
        for field in fields:
            candidate = getattr(session, field, None)
            if candidate is not None:
                value = candidate
                break
        raw = list(value) if isinstance(value, (list, tuple, set, frozenset)) else [value] if value else []
        normalized = normalize(raw)
        result[name] = normalized if isinstance(normalized, list) else [normalized]
    return result


def build_projection(*, session: Any, tasks: list[dict[str, Any]], active_index: int, dependencies: dict[str, list[str]], repairs: dict[str, int], council_replan_count: int) -> dict[str, Any]:
    completed = [str(task.get("task_id") or f"A{index + 1}") for index, task in enumerate(tasks[:active_index])]
    current = str(tasks[active_index].get("task_id") or f"A{active_index + 1}") if 0 <= active_index < len(tasks) else ""
    frontier = {task_id: deps for task_id, deps in dependencies.items() if task_id not in completed}
    return {
        "session_id": str(getattr(session, "session_id", "") or ""),
        "plan_phase_hash": str(getattr(session, "plan_phase_hash", "") or ""),
        "active_task_index": active_index,
        "task_count": len(tasks),
        "completed_task_ids": completed,
        "current_task_id": current,
        "pending_role": str(getattr(getattr(session, "pending_turn", None), "role", "") or ""),
        "task_dependencies": dependencies,
        "dependency_frontier": frontier,
        "repair_attempts_by_task": repairs,
        "council_replan_count": council_replan_count,
        "execution_status": str(getattr(session, "status", "") or ""),
        **semantic_sets(session),
    }


def build_sidecar(session: Any, projection: dict[str, Any]) -> dict[str, Any]:
    events, sequence_mode = history_events(session)
    history = history_identity(str(projection.get("session_id") or ""), events)
    body = {
        "identity_version": IDENTITY_VERSION,
        "sequence_mode": sequence_mode,
        "events": events,
        "projection": normalize(projection),
        **history,
    }
    return {**body, "sidecar_digest": digest(body, size=16)}


def verify_sidecar(sidecar: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    body = {key: value for key, value in sidecar.items() if key != "sidecar_digest"}
    if digest(body, size=16) != str(sidecar.get("sidecar_digest") or ""):
        return False, {}
    projection = sidecar.get("projection")
    if not isinstance(projection, Mapping):
        return False, {}
    events = list(sidecar.get("events") or [])
    identity = history_identity(str(projection.get("session_id") or ""), events)
    if any(sidecar.get(key) != expected for key, expected in identity.items()):
        return False, {}
    return True, dict(projection)


__all__ = [
    "IDENTITY_VERSION",
    "build_projection",
    "build_sidecar",
    "canonical",
    "digest",
    "history_events",
    "history_identity",
    "normalize",
    "semantic_sets",
    "tokens",
    "verify_sidecar",
]
