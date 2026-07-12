"""Opt-in live route-capsule layer over Aura's guarded Arena WFST runtime.

The base runtime performs state-local matching, hard guards, evidence checks, and
capability binding first. C2 may only remove or re-rank rows already admitted there.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from aura_arena_state_packet import build_arena_state_packet
from aura_arena_wfst_runtime import ArenaWFSTRuntime
from aura_route_capsule_binding import rank_admissible_capsules
from aura_route_capsule_compiler import compile_intent_for_capsule, compile_route_capsule
from aura_route_capsule_materializer import materialize_route_capsule
from aura_route_capsule_types import CompiledRouteCapsule
from aura_runtime_intent_packet import infer_runtime_intent_packet

ROUTE_CAPSULE_LIVE_RUNTIME_VERSION = "AURA_ROUTE_CAPSULE_LIVE_RUNTIME_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class CapsuleAwareArenaWFSTRuntime(ArenaWFSTRuntime):
    def __init__(self, *, repo_root: str | Path = ".", route_capsules_enabled: bool = False) -> None:
        super().__init__(repo_root=repo_root)
        self.route_capsules_enabled = bool(route_capsules_enabled)
        self._compiled: dict[tuple[str, str], CompiledRouteCapsule] = {}
        self._attachments: dict[tuple[str, str], dict[str, str]] = {}
        self.last_route: dict[str, Any] = {}

    def attach_capsule(
        self, *, arena_id: str, transition_id: str, route_capsule_ref: str,
        morphology_profile_ref: str = "", feature_flag: str = "",
    ) -> dict[str, Any]:
        grammar = self.grammar(arena_id)
        transition = grammar.transition_by_id(transition_id) if grammar else None
        if transition is None:
            return _deny("unknown_transition")
        result = compile_route_capsule(route_capsule_ref, repo_root=self.repo_root)
        if not result.ok or result.compiled is None:
            return _deny("route_capsule_compile_failed", diagnostics=[
                row.to_dict() for row in result.diagnostics
            ])
        compiled = result.compiled
        if compiled.capsule.transition_id != transition_id:
            return _deny("capsule_transition_mismatch")
        if transition.requested_capabilities and (
            tuple(compiled.capsule.requested_capabilities)
            != tuple(transition.requested_capabilities)
        ):
            return _deny("transition_capability_mismatch")
        if morphology_profile_ref and morphology_profile_ref != compiled.capsule.morphology_profile_ref:
            return _deny("morphology_profile_mismatch")
        key = (arena_id, transition_id)
        self._compiled[key] = compiled
        self._attachments[key] = {
            "route_capsule_ref": route_capsule_ref,
            "morphology_profile_ref": morphology_profile_ref or compiled.capsule.morphology_profile_ref,
            "feature_flag": feature_flag,
        }
        return {
            "ok": True, "transition_id": transition_id,
            "capsule_id": compiled.capsule.capsule_id,
            "capsule_digest": compiled.capsule.digest(),
            "automatic_activation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def route(self, **kwargs: Any) -> dict[str, Any]:
        route = super().route(**kwargs)
        if not route.get("ok"):
            self.last_route = dict(route)
            return route
        base_version = str(route.get("version") or "")
        enabled = bool(
            self.route_capsules_enabled
            and dict(kwargs.get("policy") or {}).get("route_capsules_enabled") is True
        )
        route.update(
            version=ROUTE_CAPSULE_LIVE_RUNTIME_VERSION,
            base_runtime_version=base_version,
            route_capsules_configured=self.route_capsules_enabled,
            route_capsules_enabled=enabled,
            capsule_ranking_authority="advisory_after_hard_guards",
            automatic_capsule_activation=False,
        )
        arena_id = str(kwargs.get("arena_id") or "")
        if not enabled:
            for row in route.get("available", []):
                attachment = self._attachments.get((arena_id, str(row.get("transition_id") or "")))
                if attachment:
                    row["route_capsule"] = {
                        "configured": True, "status": "feature_disabled",
                        "route_capsule_ref": attachment["route_capsule_ref"],
                        "automatic_activation": False,
                    }
            self.last_route = dict(route)
            return route

        evidence = dict(kwargs.get("evidence") or {})
        context = dict(kwargs.get("context") or {})
        policy = dict(kwargs.get("policy") or {})
        state = str(kwargs.get("current_state") or "")
        intent = infer_runtime_intent_packet(
            input_text=str(kwargs.get("input_text") or ""), current_state=state,
            context=context, policy=policy,
        )
        intent_view = intent.canonical_dict()
        intent_view.pop("objective_digest", None)
        intent_view["packet_digest"] = intent.digest()

        allowed: list[dict[str, Any]] = []
        blocked = list(route.get("blocked", []))
        for raw in route.get("available", []):
            row = dict(raw)
            transition_id = str(row.get("transition_id") or "")
            key = (arena_id, transition_id)
            attachment = self._attachments.get(key)
            if not attachment:
                allowed.append(row)
                continue
            flag = attachment.get("feature_flag") or ""
            if flag and policy.get(flag) is not True:
                blocked.append(_blocked(row, "capsule_feature_flag_not_enabled", [flag]))
                continue
            compiled = self._compiled.get(key)
            if compiled is None:
                blocked.append(_blocked(row, "route_capsule_not_compiled"))
                continue
            materialized = materialize_route_capsule(
                compiled, repo_root=self.repo_root, context=context, policy=policy,
            )
            if not materialized.get("ok"):
                blocked.append(_blocked(
                    row, str(materialized.get("reason") or "capsule_materialization_failed"),
                    list(materialized.get("missing") or []),
                ))
                continue
            try:
                bound = compile_intent_for_capsule(intent, compiled, repo_root=self.repo_root)
                scored = rank_admissible_capsules(
                    bound, [compiled],
                    admissible_capsule_ids={compiled.capsule.capsule_id},
                    repo_root=self.repo_root,
                )
                resonance = scored[0].resonance if scored else 0.0
            except Exception as exc:  # noqa: BLE001
                blocked.append(_blocked(row, f"capsule_resonance_failed:{type(exc).__name__}"))
                continue
            rank = dict(row.get("rank") or {})
            rank.update(
                capsule_resonance=resonance,
                negative_capsule_resonance=round(-resonance, 9),
            )
            row.update(
                rank=rank,
                intent_packet_digest=intent.digest(),
                vsa_profile_digest=compiled.vsa_profile_digest,
                route_capsule={
                    "configured": True, "status": "materialized",
                    "capsule_id": compiled.capsule.capsule_id,
                    "capsule_digest": compiled.capsule.digest(),
                    "capsule_manifest_digest": compiled.capsule_manifest_digest,
                    "route_signature_digest": compiled.route_signature_digest,
                    "vsa_profile_digest": compiled.vsa_profile_digest,
                    "route_capsule_ref": attachment["route_capsule_ref"],
                    "morphology_profile_ref": compiled.capsule.morphology_profile_ref,
                    "feature_flag": flag, "resonance": resonance,
                    "routing_authority": "advisory_after_hard_guards",
                    "automatic_activation": False,
                },
                materialized_aperture=dict(materialized["materialized"]),
            )
            allowed.append(row)

        allowed.sort(key=_sort_key)
        blocked.sort(key=lambda item: str(item.get("transition_id") or ""))
        route["available"] = allowed
        route["blocked"] = blocked
        route["recommended"] = allowed[:max(0, int(kwargs.get("recommendation_limit", 4)))]
        route["meta"] = [item for item in allowed if item.get("meta_transition")]
        route["intent_packet"] = intent_view
        exact = set(route.get("exact_match_transition_ids") or [])
        normalized = str(route.get("normalized_input") or "")
        selected = None
        reason = ""
        if normalized:
            if exact:
                rows = [item for item in allowed if item.get("transition_id") in exact]
                selected = rows[0] if rows else None
                reason = "" if selected else "exact_transition_blocked_by_capsule"
            elif allowed and float(allowed[0].get("semantic_fit", 0.0) or 0.0) >= 0.5:
                selected = allowed[0]
            else:
                reason = "no_safe_state_local_match"
        route["selected"] = selected
        route["abstained"] = bool(normalized and selected is None)
        route["abstention_reason"] = reason
        packet, encoded = _state_packet(
            self.grammar(arena_id), state, selected, evidence, context, policy,
        )
        route["state_packet"] = packet
        route["state_packet_encoded"] = encoded
        self.last_route = dict(route)
        return route


def _sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    rank = dict(row.get("rank") or {})
    fields = (
        ("unresolved_risk", 9.0), ("declared_evidence_gap", 9.0),
        ("empirical_uncertainty", 9.0), ("semantic_ambiguity", 9.0),
        ("negative_capsule_resonance", 0.0), ("context_switch_cost", 9.0),
        ("latency_cost", 9.0), ("token_cost", 9.0), ("thermal_cost", 9.0),
        ("negative_semantic_fit", 0.0), ("negative_user_fit", 0.0),
    )
    return tuple(_number(rank.get(name), default) for name, default in fields) + (
        str(row.get("transition_id") or ""),
    )


def _blocked(row: Mapping[str, Any], reason: str, missing: list[str] | None = None) -> dict[str, Any]:
    missing = list(missing or [])
    return {
        **dict(row),
        "failed_guards": [{
            "guard_id": "GUARD.ROUTE_CAPSULE_MATERIALIZED", "passed": False,
            "reason": reason, "missing_evidence": missing,
            "details": {"capsule_gate": True},
        }],
        "missing_evidence": missing,
        "remediation": [{"evidence": item, "action": f"provide:{item}"} for item in missing],
        "fail_closed": True,
        "capsule_blocked": True,
    }


def _state_packet(grammar: Any, state: str, selected: Mapping[str, Any] | None,
                  evidence: Mapping[str, Any], context: Mapping[str, Any], policy: Mapping[str, Any]):
    if grammar is None:
        return {}, ""
    phase, separator, substate = state.partition("/")
    if not separator:
        phase, substate = state, ""
    packet, encoded = build_arena_state_packet(
        arena_id=grammar.arena_id, arena_version=grammar.arena_version,
        grammar_version=grammar.grammar_version, phase=phase, substate=substate,
        state_code=state,
        focus_digest=_digest(context.get("focus") or context.get("objective") or ""),
        evidence_digest=_digest(evidence), policy_digest=_digest(policy),
        lease_digest=_digest(context.get("lease_capabilities") or ()),
        repository_commit=str(context.get("repository_commit") or ""),
        working_tree_digest=str(context.get("working_tree_digest") or ""),
        selected_transition=str((selected or {}).get("transition_id") or ""),
        next_state=str((selected or {}).get("next_state") or state),
        verifier_requirement=str((selected or {}).get("verifier_requirement") or "none"),
    )
    return packet.to_dict(), encoded


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode(), digest_size=12).hexdigest()


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _deny(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "ok": False, "reason": reason, "fail_closed": True,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_activation": False, **extra,
    }
