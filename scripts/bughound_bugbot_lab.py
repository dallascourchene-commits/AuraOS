#!/usr/bin/env python3
"""Deterministic local BugBot ground-truth laboratory for BugHound.

The cases are synthetic/local and model cross-boundary defect families observed
in Aura review work.  They are benchmark fixtures, not exploit code and never
perform network, credential, or third-party effects.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Callable

SCHEMA = "BugBotLabV1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class BugBotCase:
    case_id: str
    family: str
    invariant: str
    trigger: dict[str, Any]
    expected_buggy: Any
    expected_fixed: Any
    causal_cone: tuple[str, ...]
    buggy_source_ref: str
    fixed_source_ref: str
    lineage_refs: tuple[str, ...] = ()

    def receipt(self) -> dict[str, Any]:
        body = asdict(self)
        return {"schema": SCHEMA, **body, "case_digest": _digest(body)}


def stale_generation_buggy(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return int(event["generation"]) <= int(state["generation"])


def stale_generation_fixed(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return int(event["generation"]) == int(state["generation"])


def replay_buggy(state: dict[str, Any], event: dict[str, Any]) -> int:
    state["balance"] += int(event["delta"])
    return state["balance"]


def replay_fixed(state: dict[str, Any], event: dict[str, Any]) -> int:
    if event["effect_id"] in state["seen"]:
        return state["balance"]
    state["seen"].add(event["effect_id"])
    state["balance"] += int(event["delta"])
    return state["balance"]


def identity_alias_buggy(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return event["display_name"].casefold() == state["owner_display_name"].casefold()


def identity_alias_fixed(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return event["principal_id"] == state["owner_principal_id"]


def authority_substitution_buggy(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return event.get("role") == "admin"


def authority_substitution_fixed(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return state["principal_roles"].get(event["principal_id"]) == "admin"


def noncommutation_buggy(state: dict[str, Any], event: dict[str, Any]) -> int:
    # Bug: a reset fallback runs after applying the delta, making order observable.
    state["value"] += int(event["delta"])
    if event.get("reset"):
        state["value"] = 0
    return state["value"]


def noncommutation_fixed(state: dict[str, Any], event: dict[str, Any]) -> int:
    if event.get("reset"):
        state["value"] = 0
    state["value"] += int(event["delta"])
    return state["value"]


def residue_consumer_buggy(state: dict[str, Any], event: dict[str, Any]) -> str:
    state["pending"] = event["candidate"]
    return state["pending"]


def residue_consumer_fixed(state: dict[str, Any], event: dict[str, Any]) -> str:
    state["pending"] = event["candidate"]
    if event.get("verified"):
        state["committed"] = state["pending"]
    return state["committed"]


def cache_invalidation_buggy(state: dict[str, Any], event: dict[str, Any]) -> str:
    key = event["key"]
    if key in state["cache"]:
        return state["cache"][key]
    state["cache"][key] = event["value"]
    return event["value"]


def cache_invalidation_fixed(state: dict[str, Any], event: dict[str, Any]) -> str:
    key = (event["key"], event["generation"])
    if key in state["cache"]:
        return state["cache"][key]
    state["cache"][key] = event["value"]
    return event["value"]


def reopen_propagation_buggy(state: dict[str, Any], event: dict[str, Any]) -> tuple[str, ...]:
    invalidated = {event["changed"]}
    invalidated.update(state["children"].get(event["changed"], ()))
    return tuple(sorted(invalidated))


def reopen_propagation_fixed(state: dict[str, Any], event: dict[str, Any]) -> tuple[str, ...]:
    reverse = state["reverse_dependencies"]
    invalidated = {event["changed"]}
    queue = [event["changed"]]
    while queue:
        current = queue.pop()
        for dependent in reverse.get(current, ()):
            if dependent not in invalidated:
                invalidated.add(dependent)
                queue.append(dependent)
    return tuple(sorted(invalidated))


def parser_boundary_buggy(state: dict[str, Any], event: dict[str, Any]) -> str:
    index = int(event["index"])
    if 0 <= index <= len(state["items"]):
        return state["items"][index] if index < len(state["items"]) else state["fallback"]
    return state["fallback"]


def parser_boundary_fixed(state: dict[str, Any], event: dict[str, Any]) -> str:
    index = int(event["index"])
    if 0 <= index < len(state["items"]):
        return state["items"][index]
    return "BOUNDARY_REJECTED"


def merge_fallback_buggy(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return bool(event.get("explicit") or state["default"])


def merge_fallback_fixed(state: dict[str, Any], event: dict[str, Any]) -> bool:
    explicit = event.get("explicit")
    return bool(state["default"] if explicit is None else explicit)


def endpoint_escape_buggy(state: dict[str, Any], event: dict[str, Any]) -> str:
    # Synthetic representation of a redirect-boundary escape: initial host only.
    if event["initial_host"] != state["admitted_host"]:
        return "BLOCKED"
    return event["redirect_host"]


def endpoint_escape_fixed(state: dict[str, Any], event: dict[str, Any]) -> str:
    if event["initial_host"] != state["admitted_host"]:
        return "BLOCKED"
    if event["redirect_host"] != state["admitted_host"]:
        return "REDIRECT_BLOCKED"
    return event["redirect_host"]


def identity_transplant_buggy(state: dict[str, Any], event: dict[str, Any]) -> bool:
    return len(event["accepted_result_identity"]) == 64


def identity_transplant_fixed(state: dict[str, Any], event: dict[str, Any]) -> bool:
    expected = _digest(event["protected_facts"])
    return event["accepted_result_identity"] == expected


RUNNERS: dict[str, tuple[Callable[..., Any], Callable[..., Any]]] = {
    "STALE_GENERATION": (stale_generation_buggy, stale_generation_fixed),
    "REPLAY_IDEMPOTENCY": (replay_buggy, replay_fixed),
    "IDENTITY_ALIAS_COLLAPSE": (identity_alias_buggy, identity_alias_fixed),
    "AUTHORITY_SUBSTITUTION": (authority_substitution_buggy, authority_substitution_fixed),
    "NONCOMMUTATION_ORDER": (noncommutation_buggy, noncommutation_fixed),
    "PRODUCER_RESIDUE_CONSUMER": (residue_consumer_buggy, residue_consumer_fixed),
    "CACHE_INVALIDATION": (cache_invalidation_buggy, cache_invalidation_fixed),
    "REOPEN_PROPAGATION": (reopen_propagation_buggy, reopen_propagation_fixed),
    "PARSER_BOUNDARY": (parser_boundary_buggy, parser_boundary_fixed),
    "MERGE_DEFAULT_FALLBACK": (merge_fallback_buggy, merge_fallback_fixed),
    "ENDPOINT_BOUNDARY_ESCAPE": (endpoint_escape_buggy, endpoint_escape_fixed),
    "IDENTITY_TRANSPLANT": (identity_transplant_buggy, identity_transplant_fixed),
}


def _cases() -> list[BugBotCase]:
    foreign_identity = "f" * 64
    return [
        BugBotCase("BB-001", "STALE_GENERATION", "only exact current generation may act", {"state": {"generation": 5}, "event": {"generation": 4}}, True, False, ("admission", "generation"), "bugbot://stale_generation_buggy", "bugbot://stale_generation_fixed"),
        BugBotCase("BB-002", "REPLAY_IDEMPOTENCY", "same effect id executes at most once", {"state": {"balance": 0, "seen": set()}, "events": [{"effect_id": "e1", "delta": 7}, {"effect_id": "e1", "delta": 7}]}, 14, 7, ("effect_id", "dedup", "balance"), "bugbot://replay_buggy", "bugbot://replay_fixed"),
        BugBotCase("BB-003", "IDENTITY_ALIAS_COLLAPSE", "display aliases never substitute for stable principal identity", {"state": {"owner_display_name": "Admin", "owner_principal_id": "p1"}, "event": {"display_name": "admin", "principal_id": "p2"}}, True, False, ("display_name", "principal_id", "authorization"), "bugbot://identity_alias_buggy", "bugbot://identity_alias_fixed"),
        BugBotCase("BB-004", "AUTHORITY_SUBSTITUTION", "caller role label cannot mint authority", {"state": {"principal_roles": {"p1": "admin", "p2": "viewer"}}, "event": {"principal_id": "p2", "role": "admin"}}, True, False, ("principal", "role", "authority"), "bugbot://authority_substitution_buggy", "bugbot://authority_substitution_fixed"),
        BugBotCase("BB-005", "NONCOMMUTATION_ORDER", "reset-before-delta semantics must be stable", {"state": {"value": 10}, "event": {"reset": True, "delta": 3}}, 0, 3, ("reset", "delta", "state"), "bugbot://noncommutation_buggy", "bugbot://noncommutation_fixed"),
        BugBotCase("BB-006", "PRODUCER_RESIDUE_CONSUMER", "unverified producer residue cannot become committed consumer state", {"state": {"pending": None, "committed": "old"}, "event": {"candidate": "new", "verified": False}}, "new", "old", ("producer", "pending", "consumer"), "bugbot://residue_consumer_buggy", "bugbot://residue_consumer_fixed"),
        BugBotCase("BB-007", "CACHE_INVALIDATION", "cache identity includes generation", {"state": {"cache": {"k": "old"}}, "event": {"key": "k", "generation": 2, "value": "new"}}, "old", "new", ("source_generation", "cache_key", "consumer"), "bugbot://cache_invalidation_buggy", "bugbot://cache_invalidation_fixed"),
        BugBotCase("BB-008", "REOPEN_PROPAGATION", "source invalidation reaches all hard dependents", {"state": {"children": {"source": ("parser",)}, "reverse_dependencies": {"source": ("parser",), "parser": ("report",)}}, "event": {"changed": "source"}}, ("parser", "source"), ("parser", "report", "source"), ("source", "parser", "report"), "bugbot://reopen_propagation_buggy", "bugbot://reopen_propagation_fixed"),
        BugBotCase("BB-009", "PARSER_BOUNDARY", "index equal to length is invalid, never fallback success", {"state": {"items": ["a", "b"], "fallback": "OK"}, "event": {"index": 2}}, "OK", "BOUNDARY_REJECTED", ("parser", "index", "fallback"), "bugbot://parser_boundary_buggy", "bugbot://parser_boundary_fixed"),
        BugBotCase("BB-010", "MERGE_DEFAULT_FALLBACK", "explicit false survives merge", {"state": {"default": True}, "event": {"explicit": False}}, True, False, ("input", "merge", "default"), "bugbot://merge_fallback_buggy", "bugbot://merge_fallback_fixed"),
        BugBotCase("BB-011", "ENDPOINT_BOUNDARY_ESCAPE", "credential-bearing route cannot cross admitted host", {"state": {"admitted_host": "provider.example"}, "event": {"initial_host": "provider.example", "redirect_host": "other.example"}}, "other.example", "REDIRECT_BLOCKED", ("registry", "transport", "redirect"), "bugbot://endpoint_escape_buggy", "bugbot://endpoint_escape_fixed", ("AuraOS#291",)),
        BugBotCase("BB-012", "IDENTITY_TRANSPLANT", "accepted result identity derives from protected facts", {"state": {}, "event": {"protected_facts": {"result": "r1", "generation": 7}, "accepted_result_identity": foreign_identity}}, True, False, ("facts", "identity", "binding"), "bugbot://identity_transplant_buggy", "bugbot://identity_transplant_fixed", ("AuraOS#295",)),
    ]


CASES: tuple[BugBotCase, ...] = tuple(_cases())
CASE_BY_ID = {case.case_id: case for case in CASES}


def run_case(case_id: str, variant: str) -> Any:
    case = CASE_BY_ID[case_id]
    buggy, fixed = RUNNERS[case.family]
    fn = {"buggy": buggy, "fixed": fixed}.get(variant)
    if fn is None:
        raise ValueError("variant must be buggy or fixed")

    trigger = case.trigger
    state = json.loads(json.dumps(trigger["state"])) if "state" in trigger else {}
    # Restore the only non-JSON fixture type used by the replay case.
    if case.family == "REPLAY_IDEMPOTENCY":
        state["seen"] = set()
        result = None
        for event in trigger["events"]:
            result = fn(state, event)
        return result
    return fn(state, trigger["event"])


def verify_ground_truth() -> dict[str, Any]:
    results = []
    for case in CASES:
        buggy = run_case(case.case_id, "buggy")
        fixed = run_case(case.case_id, "fixed")
        passed = buggy == case.expected_buggy and fixed == case.expected_fixed and buggy != fixed
        results.append({"case_id": case.case_id, "family": case.family, "passed": passed})
    return {
        "schema": SCHEMA,
        "case_count": len(CASES),
        "passed": all(row["passed"] for row in results),
        "results": results,
        "suite_digest": _digest([case.receipt() for case in CASES]),
        "claim_ceiling": "SYNTHETIC_D0_GROUND_TRUTH_ONLY",
    }


if __name__ == "__main__":
    print(json.dumps(verify_ground_truth(), indent=2, sort_keys=True))
