"""Shared guarded-WFST runtime for Aura Arenas.

Hard guards remove inadmissible transitions before ranking. Selection remains exact
and fail-closed, while every state-local admissible alternative is projected so the
experience ledger can preserve the complete choice set and predictions.
"""
from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from aura_arena_state_packet import build_arena_state_packet
from aura_arena_wfst_compiler import normalize_input_phrase
from aura_arena_wfst_registry import ArenaGrammarRegistry
from aura_arena_wfst_types import (
    ArenaTransition,
    CompiledArenaGrammar,
    GuardResult,
    PATCH_AUTHORITY,
    RankVector,
    VSA_PATCH_AUTHORITY,
)
from aura_capability_binding import resolve_capability_bindings

ARENA_WFST_RUNTIME_VERSION = "AURA_ARENA_WFST_RUNTIME_V2"
RISK_ORDER = {"low": 0.0, "medium": 1.0, "high": 2.0, "live": 3.0, "unknown": 4.0}
UNKNOWN_MEASUREMENT_COST = 1.0
GuardFunction = Callable[[ArenaTransition, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], GuardResult]


class ArenaWFSTRuntime:
    def __init__(self, *, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry = ArenaGrammarRegistry()
        self._guards: dict[str, GuardFunction] = dict(DEFAULT_GUARDS)

    def register_guard(self, guard_id: str, function: GuardFunction) -> None:
        guard_id = str(guard_id or "").strip()
        if not guard_id.startswith("GUARD."):
            raise ValueError("guard IDs must start with GUARD.")
        self._guards[guard_id] = function

    def register_manifest(self, path: str | Path) -> dict[str, Any]:
        return self.registry.load_manifest(path, guard_ids=frozenset(self._guards))

    def register_grammar(self, grammar: CompiledArenaGrammar) -> None:
        self.registry.register(grammar)

    def grammar(self, arena_id: str) -> CompiledArenaGrammar | None:
        return self.registry.get(str(arena_id or ""))

    def route(
        self,
        *,
        arena_id: str,
        current_state: str,
        input_text: str = "",
        evidence: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        policy: dict[str, Any] | None = None,
        telemetry: dict[str, Any] | None = None,
        recommendation_limit: int = 4,
    ) -> dict[str, Any]:
        grammar = self.grammar(arena_id)
        if grammar is None:
            return _runtime_denial("grammar_not_registered", arena_id=arena_id, state=current_state)
        if current_state not in set(grammar.states):
            return _runtime_denial("unknown_arena_state", arena_id=arena_id, state=current_state)

        evidence = dict(evidence or {})
        context = dict(context or {})
        policy = dict(policy or {})
        telemetry = dict(telemetry or {})
        normalized_input = normalize_input_phrase(input_text)
        all_transitions = list(grammar.outgoing(current_state)) + self._meta_outgoing()
        exact_matches = _exact_matches(all_transitions, normalized_input)
        exact_ids = {item.transition_id for item in exact_matches}
        phrase_scores = {item.transition_id: _semantic_fit(normalized_input, item) for item in all_transitions}

        allowed_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for transition in all_transitions:
            guard_results = self._evaluate_guards(transition, evidence, context, policy)
            failed = [item for item in guard_results if not item.passed]
            semantic_fit = 1.0 if transition.transition_id in exact_ids else phrase_scores[transition.transition_id]
            if failed:
                blocked_rows.append(_blocked_row(transition, failed, semantic_fit, current_state))
                continue
            binding_packet = resolve_capability_bindings(
                transition.requested_capabilities, repo_root=self.repo_root
            )
            if not binding_packet.get("ok"):
                binding_failures = [
                    GuardResult(
                        guard_id="GUARD.CAPABILITY_BOUND",
                        passed=False,
                        reason=str(item.get("reason") or "capability_unbound"),
                        missing_evidence=(str(item.get("capability_id") or "capability"),),
                        details=dict(item),
                    )
                    for item in binding_packet.get("denials", [])
                ]
                blocked_rows.append(_blocked_row(transition, binding_failures, semantic_fit, current_state))
                continue
            rank = _rank_transition(
                transition, semantic_fit=semantic_fit, evidence=evidence, telemetry=telemetry
            )
            allowed_rows.append({
                **_transition_projection(transition, current_state=current_state),
                "guard_results": [item.to_dict() for item in guard_results],
                "capability_bindings": binding_packet.get("bindings", []),
                "semantic_fit": round(semantic_fit, 6),
                "exact_input_match": transition.transition_id in exact_ids,
                "rank": rank.to_dict(),
                "_sort_key": rank.sort_key(),
            })

        allowed_rows.sort(key=lambda item: item["_sort_key"])
        for item in allowed_rows:
            item.pop("_sort_key", None)
        blocked_rows.sort(key=lambda item: item["transition_id"])

        selected: dict[str, Any] | None = None
        abstention_reason = ""
        if normalized_input:
            if exact_ids:
                exact_allowed = [item for item in allowed_rows if item["transition_id"] in exact_ids]
                selected = exact_allowed[0] if exact_allowed else None
                if selected is None:
                    abstention_reason = "exact_transition_blocked"
            elif allowed_rows and allowed_rows[0].get("semantic_fit", 0.0) >= 0.50:
                selected = allowed_rows[0]
            else:
                abstention_reason = "no_safe_state_local_match"

        packet, encoded_packet = self._state_packet(
            grammar=grammar,
            current_state=current_state,
            selected=selected,
            evidence=evidence,
            context=context,
            policy=policy,
        )
        return {
            "ok": True,
            "version": ARENA_WFST_RUNTIME_VERSION,
            "arena_id": arena_id,
            "arena_version": grammar.arena_version,
            "grammar_version": grammar.grammar_version,
            "grammar_digest": grammar.manifest_digest,
            "state": current_state,
            "normalized_input": normalized_input,
            "selected": selected,
            "recommended": allowed_rows[:max(0, int(recommendation_limit))],
            "available": allowed_rows,
            "blocked": blocked_rows,
            "meta": [item for item in allowed_rows if item.get("meta_transition")],
            "all_state_local_alternatives_evaluated": True,
            "exact_match_transition_ids": sorted(exact_ids),
            "abstained": bool(normalized_input and selected is None),
            "abstention_reason": abstention_reason,
            "state_packet": packet.to_dict(),
            "state_packet_encoded": encoded_packet,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "learned_weight_patch_authority": False,
            "automatic_grammar_promotion": False,
        }

    def project_state(self, *, arena_id: str, current_state: str, evidence=None,
                      context=None, policy=None, telemetry=None,
                      recommendation_limit: int = 4) -> dict[str, Any]:
        return self.route(
            arena_id=arena_id,
            current_state=current_state,
            evidence=evidence,
            context=context,
            policy=policy,
            telemetry=telemetry,
            recommendation_limit=recommendation_limit,
        )

    def _meta_outgoing(self) -> list[ArenaTransition]:
        rows: list[ArenaTransition] = []
        for grammar in self.registry.meta_grammars():
            rows.extend(grammar.outgoing("*"))
        return rows

    def _evaluate_guards(self, transition, evidence, context, policy) -> list[GuardResult]:
        results: list[GuardResult] = []
        for spec in transition.hard_guards:
            function = self._guards.get(spec.guard_id)
            if function is None:
                results.append(GuardResult(spec.guard_id, False, "unknown_guard_fail_closed"))
                continue
            try:
                result = function(transition, spec.args, evidence, context, policy)
            except Exception as exc:
                result = GuardResult(spec.guard_id, False, f"guard_error:{type(exc).__name__}")
            results.append(result)
        return results

    def _state_packet(self, *, grammar, current_state, selected, evidence, context, policy):
        phase, separator, substate = current_state.partition("/")
        if not separator:
            phase, substate = current_state, ""
        next_state = str((selected or {}).get("next_state") or current_state)
        return build_arena_state_packet(
            arena_id=grammar.arena_id,
            arena_version=grammar.arena_version,
            grammar_version=grammar.grammar_version,
            phase=phase,
            substate=substate,
            state_code=current_state,
            focus_digest=_payload_digest(context.get("focus") or context.get("objective") or ""),
            evidence_digest=_payload_digest(evidence),
            policy_digest=_payload_digest(policy),
            lease_digest=_payload_digest(context.get("lease_capabilities") or ()),
            repository_commit=str(context.get("repository_commit") or ""),
            working_tree_digest=str(context.get("working_tree_digest") or ""),
            selected_transition=str((selected or {}).get("transition_id") or ""),
            next_state=next_state,
            verifier_requirement=str((selected or {}).get("verifier_requirement") or "none"),
        )


def _guard_always(transition, args, evidence, context, policy) -> GuardResult:
    return GuardResult("GUARD.ALWAYS", True, "always_allowed")


def _guard_evidence_present(transition, args, evidence, context, policy) -> GuardResult:
    key = str(args.get("key") or "").strip()
    present = bool(key and _has_value(evidence.get(key)))
    return GuardResult("GUARD.EVIDENCE_PRESENT", present, "evidence_present" if present else "missing_evidence", () if present else (key or "unspecified_evidence",))


def _guard_evidence_all(transition, args, evidence, context, policy) -> GuardResult:
    keys = args.get("keys") or transition.required_evidence
    if isinstance(keys, str):
        keys = [keys]
    keys = tuple(str(item) for item in keys or ())
    missing = tuple(key for key in keys if not _has_value(evidence.get(key)))
    return GuardResult("GUARD.EVIDENCE_ALL", not missing, "all_evidence_present" if not missing else "missing_evidence", missing)


def _guard_exact_target(transition, args, evidence, context, policy) -> GuardResult:
    present = bool(context.get("exact_target") or evidence.get("target_file") or evidence.get("target_symbol"))
    return GuardResult("GUARD.EXACT_TARGET", present, "exact_target_present" if present else "exact_target_missing", () if present else ("exact_target",))


def _guard_source_hash_match(transition, args, evidence, context, policy) -> GuardResult:
    matched = context.get("source_hash_match") is True
    return GuardResult("GUARD.SOURCE_HASH_MATCH", matched, "source_hash_match" if matched else "source_hash_mismatch", () if matched else ("matching_source_hash",))


def _guard_test_evidence(transition, args, evidence, context, policy) -> GuardResult:
    key = str(args.get("key") or "test_evidence")
    value = evidence.get(key)
    passed = isinstance(value, dict) and bool(value.get("ok") or value.get("passed")) and not value.get("tests_failed")
    return GuardResult("GUARD.TEST_EVIDENCE", passed, "test_evidence_passed" if passed else "passing_test_evidence_missing", () if passed else (key,))


def _guard_verifier_pass(transition, args, evidence, context, policy) -> GuardResult:
    key = str(args.get("key") or "verification_packet")
    value = evidence.get(key)
    passed = isinstance(value, dict) and bool(value.get("ok") or value.get("passed") or value.get("verification_ok"))
    return GuardResult("GUARD.VERIFIER_PASS", passed, "verifier_passed" if passed else "verifier_evidence_missing", () if passed else (key,))


def _guard_lease_contains(transition, args, evidence, context, policy) -> GuardResult:
    granted = {str(item) for item in context.get("lease_capabilities", ()) or ()}
    required = {str(item) for item in args.get("capabilities", ()) or transition.requested_capabilities}
    missing = tuple(sorted(required - granted))
    return GuardResult("GUARD.LEASE_CONTAINS_CAPABILITY", not missing, "lease_contains_capability" if not missing else "lease_missing_capability", missing)


def _guard_human_approval(transition, args, evidence, context, policy) -> GuardResult:
    approval = context.get("human_approval") or evidence.get("human_approval") or evidence.get("human_review")
    approved = bool(approval is True or (isinstance(approval, dict) and (approval.get("approved") or approval.get("approved_for_next_gate"))))
    return GuardResult("GUARD.HUMAN_APPROVAL", approved, "human_approval_present" if approved else "human_approval_required", () if approved else ("human_approval",))


def _guard_lifecycle_allowed(transition, args, evidence, context, policy) -> GuardResult:
    allowed = context.get("lifecycle_allowed") is True
    return GuardResult("GUARD.LIFECYCLE_ALLOWED", allowed, "lifecycle_allowed" if allowed else "illegal_lifecycle_transition")


def _guard_policy_flag(transition, args, evidence, context, policy) -> GuardResult:
    key = str(args.get("key") or "").strip()
    expected = args.get("expected", True)
    passed = bool(key and policy.get(key) == expected)
    return GuardResult("GUARD.POLICY_FLAG", passed, "policy_flag_passed" if passed else "policy_flag_failed", details={"key": key, "expected": expected})


def _guard_repository_clean_or_snapshotted(transition, args, evidence, context, policy) -> GuardResult:
    passed = context.get("working_tree_dirty") is not True or bool(context.get("snapshot_digest"))
    return GuardResult("GUARD.REPOSITORY_CLEAN_OR_SNAPSHOTTED", passed, "repository_reproducible" if passed else "dirty_repository_without_snapshot", () if passed else ("snapshot_digest",))


DEFAULT_GUARDS: dict[str, GuardFunction] = {
    "GUARD.ALWAYS": _guard_always,
    "GUARD.EVIDENCE_PRESENT": _guard_evidence_present,
    "GUARD.EVIDENCE_ALL": _guard_evidence_all,
    "GUARD.EXACT_TARGET": _guard_exact_target,
    "GUARD.SOURCE_HASH_MATCH": _guard_source_hash_match,
    "GUARD.TEST_EVIDENCE": _guard_test_evidence,
    "GUARD.VERIFIER_PASS": _guard_verifier_pass,
    "GUARD.LEASE_CONTAINS_CAPABILITY": _guard_lease_contains,
    "GUARD.HUMAN_APPROVAL": _guard_human_approval,
    "GUARD.LIFECYCLE_ALLOWED": _guard_lifecycle_allowed,
    "GUARD.POLICY_FLAG": _guard_policy_flag,
    "GUARD.REPOSITORY_CLEAN_OR_SNAPSHOTTED": _guard_repository_clean_or_snapshotted,
}


def _rank_transition(transition: ArenaTransition, *, semantic_fit: float,
                     evidence: dict[str, Any], telemetry: dict[str, Any]) -> RankVector:
    profile = transition.soft_weight_profile
    latency, latency_class = _measurement(telemetry, transition.transition_id, "latency_cost", profile.latency_cost)
    tokens, token_class = _measurement(telemetry, transition.transition_id, "token_cost", profile.token_cost)
    thermal, thermal_class = _measurement(telemetry, transition.transition_id, "thermal_cost", profile.thermal_cost)
    combined_user_fit = max(0.0, min(1.0, (profile.user_fit + profile.base_priority) / 2.0))
    return RankVector(
        unresolved_risk=RISK_ORDER.get(transition.risk, RISK_ORDER["unknown"]),
        declared_evidence_gap=float(sum(1 for key in transition.required_evidence if not _has_value(evidence.get(key)))),
        empirical_uncertainty=profile.empirical_uncertainty,
        semantic_ambiguity=round(1.0 - max(0.0, min(1.0, semantic_fit)), 6),
        context_switch_cost=profile.context_switch_cost,
        latency_cost=latency,
        token_cost=tokens,
        thermal_cost=thermal,
        negative_semantic_fit=round(-semantic_fit, 6),
        negative_user_fit=round(-combined_user_fit, 6),
        stable_transition_id=transition.transition_id,
        measurement_classes={"latency": latency_class, "tokens": token_class, "thermal": thermal_class},
    )


def _measurement(telemetry: dict[str, Any], transition_id: str, field: str,
                 fallback: float | None) -> tuple[float, str]:
    item = telemetry.get(transition_id, {}) if isinstance(telemetry.get(transition_id), dict) else {}
    value = item.get(field)
    measurement_class = str(item.get(f"{field}_measurement_class") or "")
    if value is not None:
        try:
            return max(0.0, float(value)), measurement_class or "MEASURED"
        except (TypeError, ValueError):
            pass
    if fallback is not None:
        return max(0.0, float(fallback)), "DERIVED"
    return UNKNOWN_MEASUREMENT_COST, "UNAVAILABLE"


def _exact_matches(transitions: list[ArenaTransition], normalized_input: str) -> list[ArenaTransition]:
    if not normalized_input:
        return []
    return [item for item in transitions if any(normalize_input_phrase(phrase) == normalized_input for phrase in item.input_phrases())]


def _semantic_fit(normalized_input: str, transition: ArenaTransition) -> float:
    if not normalized_input:
        return 0.0
    input_tokens = set(_tokens(normalized_input))
    best = 0.0
    for phrase in transition.input_phrases():
        normalized_phrase = normalize_input_phrase(phrase)
        if not normalized_phrase:
            continue
        if normalized_phrase in normalized_input or normalized_input in normalized_phrase:
            best = max(best, 0.95)
        phrase_tokens = set(_tokens(normalized_phrase))
        union = input_tokens | phrase_tokens
        if union:
            best = max(best, len(input_tokens & phrase_tokens) / len(union))
    return min(1.0, best)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", str(value).casefold())


def _transition_projection(transition: ArenaTransition, *, current_state: str) -> dict[str, Any]:
    return {
        "transition_id": transition.transition_id,
        "label": transition.ui_label,
        "description": transition.ui_description,
        "from_state": current_state if transition.from_state == "*" else transition.from_state,
        "next_state": current_state if transition.next_state == "*" else transition.next_state,
        "output_symbol": transition.output_symbol,
        "required_evidence": list(transition.required_evidence),
        "produced_evidence": list(transition.produced_evidence),
        "requested_capabilities": list(transition.requested_capabilities),
        "verifier_requirement": transition.verifier_requirement,
        "approval_requirement": transition.approval_requirement,
        "risk": transition.risk,
        "meta_transition": transition.arena_id == "meta" or transition.from_state == "*",
        "provenance": dict(transition.provenance),
    }


def _blocked_row(transition: ArenaTransition, failed: list[GuardResult],
                 semantic_fit: float, current_state: str) -> dict[str, Any]:
    missing = sorted({item for result in failed for item in result.missing_evidence if item})
    return {
        **_transition_projection(transition, current_state=current_state),
        "failed_guards": [item.to_dict() for item in failed],
        "missing_evidence": missing,
        "remediation": [{"evidence": key, "action": f"provide:{key}"} for key in missing],
        "semantic_fit": round(semantic_fit, 6),
        "fail_closed": True,
    }


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes, list, tuple, set, dict)):
        return len(value) > 0
    return True


def _payload_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=12).hexdigest()


def _runtime_denial(reason: str, *, arena_id: str, state: str) -> dict[str, Any]:
    return {
        "ok": False,
        "version": ARENA_WFST_RUNTIME_VERSION,
        "arena_id": arena_id,
        "state": state,
        "reason": reason,
        "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
