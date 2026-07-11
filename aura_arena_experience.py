"""Canonical structured experience records for Aura Arenas.

Only observable inputs, decisions, evidence references, tool receipts, measurements,
and outcomes are stored. Hidden chain-of-thought is neither requested nor retained.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
import secrets
import time
from typing import Any

ARENA_EXPERIENCE_VERSION = "AURA_ARENA_EXPERIENCE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_SECRET_KEY_RE = re.compile(r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|authorization|secret|password|private[_-]?key|cookie)")
_SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{12,}"),
)
_FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "chain-of-thought",
    "hidden_reasoning",
    "private_reasoning",
    "scratchpad",
    "internal_monologue",
}


@dataclass(frozen=True)
class ArenaExperience:
    experience_id: str
    correlation_id: str
    task_id: str
    workflow_id: str
    arena_id: str
    arena_version: str
    grammar_version: str
    runtime_version: str
    compiler_version: str
    started_at: float
    completed_at: float
    state_before: str
    state_after: str
    selected_transition: str
    final_outcome: str
    repository_commit_sha: str = ""
    working_tree_digest: str = ""
    objective_hash: str = ""
    source_hash_digest: str = ""
    provider: str = ""
    model: str = ""
    measurement_class: str = "UNAVAILABLE"
    cost_run_id: str = ""
    trace_atom_ids: tuple[str, ...] = ()
    raw_evidence_refs: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    redactions: tuple[str, ...] = ()
    version: str = ARENA_EXPERIENCE_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    learned_weight_patch_authority: bool = False
    crystallization_patch_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["trace_atom_ids"] = list(self.trace_atom_ids)
        data["raw_evidence_refs"] = list(self.raw_evidence_refs)
        data["redactions"] = list(self.redactions)
        return data


def build_arena_experience(
    *,
    arena_id: str,
    arena_version: str,
    grammar_version: str,
    runtime_version: str,
    compiler_version: str,
    state_before: str,
    state_after: str,
    selected_transition: str,
    final_outcome: str,
    payload: dict[str, Any] | None = None,
    experience_id: str = "",
    correlation_id: str = "",
    task_id: str = "",
    workflow_id: str = "",
    started_at: float | None = None,
    completed_at: float | None = None,
    repository_commit_sha: str = "",
    working_tree_digest: str = "",
    objective: str = "",
    source_hashes: list[str] | tuple[str, ...] = (),
    provider: str = "",
    model: str = "",
    measurement_class: str = "UNAVAILABLE",
    cost_run_id: str = "",
    trace_atom_ids: list[str] | tuple[str, ...] = (),
    raw_evidence_refs: list[str] | tuple[str, ...] = (),
) -> ArenaExperience:
    sanitized, redactions = sanitize_experience_payload(dict(payload or {}))
    now = time.time()
    started = float(started_at if started_at is not None else now)
    completed = float(completed_at if completed_at is not None else now)
    if completed < started:
        raise ValueError("completed_at cannot be earlier than started_at")
    exp_id = experience_id or f"EXP-{secrets.token_hex(12)}"
    corr_id = correlation_id or f"CORR-{_hash_text(f'{arena_id}:{task_id}:{workflow_id}:{started}')[:16]}"
    return ArenaExperience(
        experience_id=_required(exp_id, "experience_id"),
        correlation_id=_required(corr_id, "correlation_id"),
        task_id=str(task_id or ""),
        workflow_id=str(workflow_id or ""),
        arena_id=_required(arena_id, "arena_id"),
        arena_version=_required(arena_version, "arena_version"),
        grammar_version=_required(grammar_version, "grammar_version"),
        runtime_version=_required(runtime_version, "runtime_version"),
        compiler_version=_required(compiler_version, "compiler_version"),
        started_at=started,
        completed_at=completed,
        state_before=_required(state_before, "state_before"),
        state_after=_required(state_after, "state_after"),
        selected_transition=str(selected_transition or ""),
        final_outcome=_required(final_outcome, "final_outcome"),
        repository_commit_sha=str(repository_commit_sha or "")[:128],
        working_tree_digest=str(working_tree_digest or "")[:256],
        objective_hash=_hash_text(objective) if objective else "",
        source_hash_digest=_hash_collection(source_hashes),
        provider=str(provider or "")[:120],
        model=str(model or "")[:160],
        measurement_class=str(measurement_class or "UNAVAILABLE").upper(),
        cost_run_id=str(cost_run_id or "")[:160],
        trace_atom_ids=tuple(str(item) for item in trace_atom_ids if str(item)),
        raw_evidence_refs=tuple(str(item) for item in raw_evidence_refs if str(item)),
        payload=sanitized,
        redactions=tuple(redactions),
    )


def sanitize_experience_payload(value: Any) -> tuple[Any, list[str]]:
    redactions: list[str] = []

    def walk(item: Any, path: str) -> Any:
        if isinstance(item, dict):
            output: dict[str, Any] = {}
            for raw_key, raw_value in item.items():
                key = str(raw_key)
                key_folded = key.casefold()
                child_path = f"{path}.{key}" if path else key
                if key_folded in _FORBIDDEN_REASONING_KEYS:
                    redactions.append(f"forbidden_reasoning:{child_path}")
                    continue
                if _SECRET_KEY_RE.search(key):
                    redactions.append(f"secret_key:{child_path}")
                    output[key] = "[REDACTED]"
                    continue
                output[key] = walk(raw_value, child_path)
            return output
        if isinstance(item, (list, tuple, set)):
            return [walk(value, f"{path}[{index}]") for index, value in enumerate(item)]
        if isinstance(item, bytes):
            item = item.decode("utf-8", errors="replace")
        if isinstance(item, str):
            text = item
            for pattern in _SECRET_VALUE_PATTERNS:
                replaced = pattern.sub("[REDACTED]", text)
                if replaced != text:
                    redactions.append(f"secret_value:{path or '<root>'}")
                    text = replaced
            return text
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return str(item)

    return walk(value, ""), sorted(set(redactions))


def canonical_experience_digest(experience: ArenaExperience | dict[str, Any]) -> str:
    payload = experience.to_dict() if isinstance(experience, ArenaExperience) else dict(experience)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def _required(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _hash_text(value: str) -> str:
    return hashlib.blake2b(str(value).encode("utf-8"), digest_size=16).hexdigest()


def _hash_collection(values: list[str] | tuple[str, ...]) -> str:
    normalized = sorted(str(item) for item in values if str(item))
    return _hash_text(json.dumps(normalized, separators=(",", ":"))) if normalized else ""
