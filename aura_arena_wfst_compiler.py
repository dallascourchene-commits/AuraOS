"""Deterministic manifest compiler for Aura Arena guarded-WFST grammars.

The compiler validates declarative JSON only. It never executes manifest content and
never grants capability, patch, or promotion authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

from aura_arena_wfst_types import (
    ArenaTransition,
    CompiledArenaGrammar,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)

ARENA_WFST_COMPILER_VERSION = "AURA_ARENA_WFST_COMPILER_V1"
MANIFEST_SCHEMA_VERSION = "AURA_ARENA_GRAMMAR_MANIFEST_V1"

DEFAULT_GUARD_IDS = frozenset(
    {
        "GUARD.ALWAYS",
        "GUARD.EVIDENCE_PRESENT",
        "GUARD.EVIDENCE_ALL",
        "GUARD.EXACT_TARGET",
        "GUARD.SOURCE_HASH_MATCH",
        "GUARD.TEST_EVIDENCE",
        "GUARD.VERIFIER_PASS",
        "GUARD.LEASE_CONTAINS_CAPABILITY",
        "GUARD.HUMAN_APPROVAL",
        "GUARD.LIFECYCLE_ALLOWED",
        "GUARD.POLICY_FLAG",
        "GUARD.REPOSITORY_CLEAN_OR_SNAPSHOTTED",
    }
)

_ID_RE = re.compile(r"^[A-Za-z0-9_.:\-*/]+$")


@dataclass(frozen=True)
class CompileDiagnostic:
    severity: str
    code: str
    message: str
    transition_id: str = ""
    state: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "transition_id": self.transition_id,
            "state": self.state,
        }


@dataclass
class ArenaGrammarCompileResult:
    ok: bool
    grammar: CompiledArenaGrammar | None
    diagnostics: list[CompileDiagnostic] = field(default_factory=list)
    manifest_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "version": ARENA_WFST_COMPILER_VERSION,
            "manifest_digest": self.manifest_digest,
            "grammar": self.grammar.to_dict() if self.grammar else None,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_grammar_promotion": False,
        }


def load_and_compile_arena_grammar(
    path: str | Path,
    *,
    guard_ids: set[str] | frozenset[str] | None = None,
    capability_exists: Callable[[str], bool] | None = None,
) -> ArenaGrammarCompileResult:
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _failed("manifest_not_found", f"manifest not found: {manifest_path}")
    except json.JSONDecodeError as exc:
        return _failed("manifest_invalid_json", f"invalid JSON: {exc}")
    except OSError as exc:
        return _failed("manifest_read_failed", str(exc))
    return compile_arena_grammar(
        payload,
        guard_ids=guard_ids,
        capability_exists=capability_exists,
        source_path=str(manifest_path),
    )


def compile_arena_grammar(
    manifest: dict[str, Any],
    *,
    guard_ids: set[str] | frozenset[str] | None = None,
    capability_exists: Callable[[str], bool] | None = None,
    source_path: str = "",
) -> ArenaGrammarCompileResult:
    diagnostics: list[CompileDiagnostic] = []
    if not isinstance(manifest, dict):
        return _failed("manifest_not_object", "grammar manifest must be an object")

    schema_version = str(manifest.get("schema_version") or "")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        diagnostics.append(CompileDiagnostic(
            "error", "unsupported_schema_version",
            f"expected {MANIFEST_SCHEMA_VERSION}, received {schema_version or '<missing>'}",
        ))

    arena_id = _manifest_text(manifest, "arena_id", diagnostics)
    arena_version = _manifest_text(manifest, "arena_version", diagnostics)
    grammar_version = _manifest_text(manifest, "grammar_version", diagnostics)
    start_state = _manifest_text(manifest, "start_state", diagnostics)
    meta_grammar = bool(manifest.get("meta_grammar", False))

    raw_states = manifest.get("states") or []
    if not isinstance(raw_states, list):
        diagnostics.append(CompileDiagnostic("error", "states_not_list", "states must be a list"))
        raw_states = []
    states = _deduplicated_ids(raw_states, "state", diagnostics)
    state_set = set(states)

    if meta_grammar:
        if "*" not in state_set:
            diagnostics.append(CompileDiagnostic("error", "meta_missing_wildcard", "meta grammar must declare '*' state"))
    elif start_state and start_state not in state_set:
        diagnostics.append(CompileDiagnostic("error", "unknown_start_state", f"start state {start_state} is not declared"))

    terminal_states = set(_text_list(manifest.get("terminal_states") or []))
    for state in sorted(terminal_states - state_set):
        diagnostics.append(CompileDiagnostic("error", "unknown_terminal_state", f"terminal state {state} is not declared", state=state))

    allowed_guards = frozenset(guard_ids or DEFAULT_GUARD_IDS)
    transitions: list[ArenaTransition] = []
    raw_transitions = manifest.get("transitions") or []
    if not isinstance(raw_transitions, list):
        diagnostics.append(CompileDiagnostic("error", "transitions_not_list", "transitions must be a list"))
        raw_transitions = []

    transition_ids: set[str] = set()
    alias_map: dict[tuple[str, str], str] = {}
    for index, raw in enumerate(raw_transitions):
        try:
            transition = ArenaTransition.from_dict(raw, arena_id=arena_id, grammar_version=grammar_version)
        except (TypeError, ValueError) as exc:
            diagnostics.append(CompileDiagnostic("error", "invalid_transition", f"transition[{index}]: {exc}"))
            continue

        tid = transition.transition_id
        if tid in transition_ids:
            diagnostics.append(CompileDiagnostic("error", "duplicate_transition_id", f"duplicate transition id {tid}", tid))
            continue
        transition_ids.add(tid)
        transitions.append(transition)

        if transition.from_state not in state_set and not (meta_grammar and transition.from_state == "*"):
            diagnostics.append(CompileDiagnostic("error", "unknown_from_state", f"unknown from_state {transition.from_state}", tid, transition.from_state))
        if transition.next_state not in state_set and not (meta_grammar and transition.next_state == "*"):
            diagnostics.append(CompileDiagnostic("error", "unknown_next_state", f"unknown next_state {transition.next_state}", tid, transition.next_state))

        for guard in transition.hard_guards:
            if guard.guard_id not in allowed_guards:
                diagnostics.append(CompileDiagnostic("error", "unknown_guard", f"unknown guard id {guard.guard_id}", tid, transition.from_state))

        for capability in transition.requested_capabilities:
            if not _valid_id(capability):
                diagnostics.append(CompileDiagnostic("error", "invalid_capability_id", f"invalid capability id {capability!r}", tid))
            elif capability_exists is not None:
                try:
                    exists = bool(capability_exists(capability))
                except Exception as exc:
                    exists = False
                    diagnostics.append(CompileDiagnostic(
                        "error", "capability_validation_failed",
                        f"capability validation failed for {capability}: {type(exc).__name__}", tid,
                    ))
                if not exists:
                    diagnostics.append(CompileDiagnostic("error", "unbound_capability", f"capability is not grounded: {capability}", tid))

        for phrase in transition.input_phrases():
            normalized = normalize_input_phrase(phrase)
            if not normalized:
                diagnostics.append(CompileDiagnostic("error", "empty_input_phrase", "transition contains an empty normalized input phrase", tid))
                continue
            key = (transition.from_state, normalized)
            prior = alias_map.get(key)
            if prior and prior != tid:
                diagnostics.append(CompileDiagnostic(
                    "error", "ambiguous_state_local_alias",
                    f"input phrase {phrase!r} resolves to both {prior} and {tid} in {transition.from_state}",
                    tid, transition.from_state,
                ))
            else:
                alias_map[key] = tid

    for transition in transitions:
        if transition.rollback_transition and transition.rollback_transition not in transition_ids:
            diagnostics.append(CompileDiagnostic(
                "error", "unknown_rollback_transition",
                f"rollback transition {transition.rollback_transition} is not declared",
                transition.transition_id,
            ))

    if not meta_grammar and start_state in state_set:
        reachable = _reachable_states(start_state, transitions)
        for state in sorted(state_set - reachable):
            diagnostics.append(CompileDiagnostic("warning", "unreachable_state", f"state {state} is unreachable from {start_state}", state=state))
        outgoing_states = {item.from_state for item in transitions}
        for state in sorted(state_set - terminal_states):
            if state not in outgoing_states:
                diagnostics.append(CompileDiagnostic("warning", "dead_end_nonterminal", f"nonterminal state {state} has no outgoing transition", state=state))

    manifest_digest = _manifest_digest(manifest)
    has_errors = any(item.severity == "error" for item in diagnostics)
    grammar = None
    if not has_errors:
        grammar = CompiledArenaGrammar(
            arena_id=arena_id,
            arena_version=arena_version,
            grammar_version=grammar_version,
            start_state=start_state,
            states=tuple(states),
            transitions=tuple(sorted(transitions, key=lambda item: (item.from_state, item.transition_id))),
            manifest_digest=manifest_digest,
            source_path=source_path,
            meta_grammar=meta_grammar,
        )
    return ArenaGrammarCompileResult(not has_errors, grammar, diagnostics, manifest_digest)


def normalize_input_phrase(value: str) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[^a-z0-9_.:\-/*]+", " ", text)
    return " ".join(text.split())


def _reachable_states(start: str, transitions: list[ArenaTransition]) -> set[str]:
    adjacency: dict[str, set[str]] = {}
    for transition in transitions:
        adjacency.setdefault(transition.from_state, set()).add(transition.next_state)
    seen = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for target in sorted(adjacency.get(current, ())):
            if target not in seen:
                seen.add(target)
                stack.append(target)
    return seen


def _manifest_digest(manifest: dict[str, Any]) -> str:
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def _manifest_text(manifest: dict[str, Any], key: str, diagnostics: list[CompileDiagnostic]) -> str:
    value = str(manifest.get(key) or "").strip()
    if not value:
        diagnostics.append(CompileDiagnostic("error", f"missing_{key}", f"{key} is required"))
    elif not _valid_id(value):
        diagnostics.append(CompileDiagnostic("error", f"invalid_{key}", f"{key} contains unsupported characters: {value!r}"))
    return value


def _deduplicated_ids(values: list[Any], kind: str, diagnostics: list[CompileDiagnostic]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value or not _valid_id(value):
            diagnostics.append(CompileDiagnostic("error", f"invalid_{kind}_id", f"invalid {kind} id: {value!r}"))
            continue
        if value in seen:
            diagnostics.append(CompileDiagnostic("error", f"duplicate_{kind}_id", f"duplicate {kind} id: {value}"))
            continue
        seen.add(value)
        output.append(value)
    return output


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _valid_id(value: str) -> bool:
    return bool(value and _ID_RE.fullmatch(value))


def _failed(code: str, message: str) -> ArenaGrammarCompileResult:
    return ArenaGrammarCompileResult(False, None, [CompileDiagnostic("error", code, message)], "")
