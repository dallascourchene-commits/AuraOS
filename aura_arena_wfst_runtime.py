"""Shared guarded-WFST runtime with post-guard route-capsule materialization."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from aura_arena_state_packet import build_arena_state_packet
from aura_arena_wfst_compiler import normalize_input_phrase
from aura_arena_wfst_registry import ArenaGrammarRegistry
from aura_arena_wfst_types import ArenaTransition, CompiledArenaGrammar, GuardResult, PATCH_AUTHORITY, RankVector, VSA_PATCH_AUTHORITY
from aura_capability_binding import resolve_capability_bindings
from aura_route_capsule_runtime import compile_transition_capsule, materialize_route_capsule

ARENA_WFST_RUNTIME_VERSION = "AURA_ARENA_WFST_RUNTIME_V3"
RISK_ORDER = {"low": 0.0, "medium": 1.0, "high": 2.0, "live": 3.0, "unknown": 4.0}
UNKNOWN_MEASUREMENT_COST = 1.0
GuardFunction = Callable[[ArenaTransition, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]], GuardResult]

class ArenaWFSTRuntime:
    def __init__(self, *, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry = ArenaGrammarRegistry()
        self._guards: dict[str, GuardFunction] = dict(DEFAULT_GUARDS)
        self._compiled_capsules: dict[tuple[str, str], Any] = {}

    def register_guard(self, guard_id: str, function: GuardFunction) -> None:
        guard_id = str(guard_id or "").strip()
        if not guard_id.startswith("GUARD."):
            raise ValueError("guard IDs must start with GUARD.")
        self._guards[guard_id] = function

    def register_manifest(self, path: str | Path) -> dict[str, Any]:
        report = self.registry.load_manifest(path, guard_ids=frozenset(self._guards))
        if not report.get("ok"):
            return report
        grammar_data = report.get("grammar") or {}
        grammar = self.registry.get(str(grammar_data.get("arena_id") or ""))
        if grammar is None:
            return report
        try:
            grammar, overlay = self._apply_capsule_overlay(grammar)
            compiled = self._compile_capsules(grammar)
        except Exception as exc:
            self.registry.remove(grammar.arena_id, meta=grammar.meta_grammar)
            report.update(ok=False, grammar=None, fail_closed=True)
            report["diagnostics"] = list(report.get("diagnostics") or []) + [{
                "severity": "error", "code": "route_capsule_registration_failed",
                "message": str(exc), "transition_id": "", "state": "",
            }]
            return report
        self.registry.register(grammar)
        self._compiled_capsules.update({(grammar.arena_id, key): value for key, value in compiled.items()})
        report["grammar"] = grammar.to_dict()
        report["route_capsule_overlay"] = overlay
        report["compiled_route_capsules"] = {key: value.to_dict() for key, value in sorted(compiled.items())}
        return report

    def _apply_capsule_overlay(self, grammar: CompiledArenaGrammar):
        path = self.repo_root / ".aura" / "arena_capsule_bindings" / f"{grammar.arena_id}.v1.json"
        if not path.exists():
            return grammar, {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("capsule overlay must be an object")
        if str(payload.get("arena_id") or "") != grammar.arena_id:
            raise ValueError("capsule overlay arena_id mismatch")
        if str(payload.get("grammar_version") or "") != grammar.grammar_version:
            raise ValueError("capsule overlay grammar_version mismatch")
        rows = payload.get("bindings") or []
        if not isinstance(rows, list):
            raise ValueError("capsule overlay bindings must be a list")
        bindings: dict[str, tuple[str, str]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("capsule overlay binding must be an object")
            transition_id = str(row.get("transition_id") or "").strip()
            morphology_ref = str(row.get("morphology_profile_ref") or "").strip()
            capsule_ref = str(row.get("route_capsule_ref") or "").strip()
            if not transition_id or not morphology_ref or not capsule_ref:
                raise ValueError("capsule overlay binding requires transition_id and both references")
            if transition_id in bindings:
                raise ValueError(f"duplicate capsule overlay transition: {transition_id}")
            if grammar.transition_by_id(transition_id) is None:
                raise ValueError(f"capsule overlay references unknown transition: {transition_id}")
            bindings[transition_id] = (morphology_ref, capsule_ref)
        transitions = tuple(
            replace(item, morphology_profile_ref=bindings[item.transition_id][0], route_capsule_ref=bindings[item.transition_id][1])
            if item.transition_id in bindings else item
            for item in grammar.transitions
        )
        digest = hashlib.blake2b(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(), digest_size=20).hexdigest()
        return replace(grammar, transitions=transitions), {
            "path": str(path.relative_to(self.repo_root)).replace("\\", "/"),
            "digest": digest,
            "binding_count": len(bindings),
        }

    def _compile_capsules(self, grammar: CompiledArenaGrammar) -> dict[str, Any]:
        compiled = {}
        for transition in grammar.transitions:
            if transition.route_capsule_ref:
                compiled[transition.transition_id] = compile_transition_capsule(transition, repo_root=self.repo_root)
        return compiled

    def register_grammar(self, grammar: CompiledArenaGrammar) -> None:
        self.registry.register(grammar)

    def grammar(self, arena_id: str) -> CompiledArenaGrammar | None:
        return self.registry.get(str(arena_id or ""))

    def route(self, *, arena_id: str, current_state: str, input_text: str = "", evidence=None, context=None, policy=None, telemetry=None, recommendation_limit: int = 4) -> dict[str, Any]:
        grammar = self.grammar(arena_id)
        if grammar is None:
            return _runtime_denial("grammar_not_registered", arena_id=arena_id, state=current_state)
        if current_state not in set(grammar.states):
            return _runtime_denial("unknown_arena_state", arena_id=arena_id, state=current_state)
        evidence, context, policy, telemetry = map(dict, (evidence or {}, context or {}, policy or {}, telemetry or {}))
        capsules_enabled = _capsules_enabled(policy)
        normalized_input = normalize_input_phrase(input_text)
        transitions = list(grammar.outgoing(current_state)) + self._meta_outgoing()
        exact_ids = {item.transition_id for item in _exact_matches(transitions, normalized_input)}
        allowed_rows, blocked_rows = [], []
        for transition in transitions:
            semantic_fit = 1.0 if transition.transition_id in exact_ids else _semantic_fit(normalized_input, transition)
            guards = self._evaluate_guards(transition, evidence, context, policy)
            failed = [item for item in guards if not item.passed]
            if failed:
                blocked_rows.append(_blocked_row(transition, failed, semantic_fit, current_state))
                continue
            binding = resolve_capability_bindings(transition.requested_capabilities, repo_root=self.repo_root)
            if not binding.get("ok"):
                failures = [GuardResult("GUARD.CAPABILITY_BOUND", False, str(item.get("reason") or "capability_unbound"), (str(item.get("capability_id") or "capability"),), dict(item)) for item in binding.get("denials", [])]
                blocked_rows.append(_blocked_row(transition, failures, semantic_fit, current_state))
                continue
            capsule_packet, resonance = None, None
            if transition.route_capsule_ref:
                compiled = self._compiled_capsules.get((grammar.arena_id, transition.transition_id))
                if compiled is None:
                    blocked_rows.append(_blocked_row(transition, [GuardResult("GUARD.ROUTE_CAPSULE_COMPILED", False, "route_capsule_not_compiled", ("route_capsule",))], semantic_fit, current_state))
                    continue
                if capsules_enabled:
                    try:
                        materialized = materialize_route_capsule(compiled, repo_root=self.repo_root, input_text=input_text, context=context)
                        capsule_packet, resonance = materialized.to_dict(), materialized.resonance
                    except Exception as exc:
                        blocked_rows.append(_blocked_row(transition, [GuardResult("GUARD.ROUTE_CAPSULE_MATERIALIZED", False, f"route_capsule_error:{type(exc).__name__}", ("route_capsule",), {"message": str(exc)})], semantic_fit, current_state))
                        continue
            effective_fit = max(semantic_fit, float(resonance)) if resonance is not None else semantic_fit
            rank = _rank_transition(transition, semantic_fit=effective_fit, evidence=evidence, telemetry=telemetry)
            allowed_rows.append({
                **_transition_projection(transition, current_state=current_state),
                "guard_results": [item.to_dict() for item in guards],
                "capability_bindings": binding.get("bindings", []),
                "semantic_fit": round(semantic_fit, 6),
                "effective_semantic_fit": round(effective_fit, 6),
                "capsule_resonance": resonance,
                "route_capsule": capsule_packet,
                "route_capsule_status": "materialized" if capsule_packet else ("disabled" if transition.route_capsule_ref else "none"),
                "exact_input_match": transition.transition_id in exact_ids,
                "rank": rank.to_dict(),
                "_sort_key": rank.sort_key(),
            })
        allowed_rows.sort(key=lambda item: item["_sort_key"])
        for item in allowed_rows:
            item.pop("_sort_key", None)
        blocked_rows.sort(key=lambda item: item["transition_id"])
        selected, abstention_reason = None, ""
        if normalized_input:
            if exact_ids:
                exact_allowed = [item for item in allowed_rows if item["transition_id"] in exact_ids]
                selected = exact_allowed[0] if exact_allowed else None
                if selected is None:
                    abstention_reason = "exact_transition_blocked"
            elif allowed_rows and allowed_rows[0].get("effective_semantic_fit", 0.0) >= 0.50:
                selected = allowed_rows[0]
            else:
                abstention_reason = "no_safe_state_local_match"
        packet, encoded = self._state_packet(grammar=grammar, current_state=current_state, selected=selected, evidence=evidence, context=context, policy=policy)
        return {
            "ok": True, "version": ARENA_WFST_RUNTIME_VERSION, "arena_id": arena_id,
            "arena_version": grammar.arena_version, "grammar_version": grammar.grammar_version,
            "grammar_digest": grammar.manifest_digest, "state": current_state,
            "normalized_input": normalized_input, "selected": selected,
            "recommended": allowed_rows[:max(0, int(recommendation_limit))], "available": allowed_rows,
            "blocked": blocked_rows, "meta": [item for item in allowed_rows if item.get("meta_transition")],
            "all_state_local_alternatives_evaluated": True, "exact_match_transition_ids": sorted(exact_ids),
            "abstained": bool(normalized_input and selected is None), "abstention_reason": abstention_reason,
            "route_capsules_enabled": capsules_enabled, "state_packet": packet.to_dict(), "state_packet_encoded": encoded,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "learned_weight_patch_authority": False, "automatic_grammar_promotion": False,
            "automatic_capsule_activation": False,
        }

    def project_state(self, *, arena_id, current_state, evidence=None, context=None, policy=None, telemetry=None, recommendation_limit=4):
        return self.route(arena_id=arena_id, current_state=current_state, evidence=evidence, context=context, policy=policy, telemetry=telemetry, recommendation_limit=recommendation_limit)

    def _meta_outgoing(self):
        rows = []
        for grammar in self.registry.meta_grammars():
            rows.extend(grammar.outgoing("*"))
        return rows

    def _evaluate_guards(self, transition, evidence, context, policy):
        results = []
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
        return build_arena_state_packet(
            arena_id=grammar.arena_id, arena_version=grammar.arena_version,
            grammar_version=grammar.grammar_version, phase=phase, substate=substate,
            state_code=current_state, focus_digest=_payload_digest(context.get("focus") or context.get("objective") or ""),
            evidence_digest=_payload_digest(evidence), policy_digest=_payload_digest(policy),
            lease_digest=_payload_digest(context.get("lease_capabilities") or ()),
            repository_commit=str(context.get("repository_commit") or ""),
            working_tree_digest=str(context.get("working_tree_digest") or ""),
            selected_transition=str((selected or {}).get("transition_id") or ""),
            next_state=str((selected or {}).get("next_state") or current_state),
            verifier_requirement=str((selected or {}).get("verifier_requirement") or "none"),
        )

def _guard_always(t,a,e,c,p): return GuardResult("GUARD.ALWAYS", True, "always_allowed")
def _guard_evidence_present(t,a,e,c,p):
    key=str(a.get("key") or "").strip(); ok=bool(key and _has_value(e.get(key))); return GuardResult("GUARD.EVIDENCE_PRESENT",ok,"evidence_present" if ok else "missing_evidence",() if ok else (key or "unspecified_evidence",))
def _guard_evidence_all(t,a,e,c,p):
    keys=a.get("keys") or t.required_evidence; keys=[keys] if isinstance(keys,str) else tuple(str(x) for x in keys or ()); missing=tuple(k for k in keys if not _has_value(e.get(k))); return GuardResult("GUARD.EVIDENCE_ALL",not missing,"all_evidence_present" if not missing else "missing_evidence",missing)
def _guard_exact_target(t,a,e,c,p):
    ok=bool(c.get("exact_target") or e.get("target_file") or e.get("target_symbol")); return GuardResult("GUARD.EXACT_TARGET",ok,"exact_target_present" if ok else "exact_target_missing",() if ok else ("exact_target",))
def _guard_source_hash_match(t,a,e,c,p):
    ok=c.get("source_hash_match") is True; return GuardResult("GUARD.SOURCE_HASH_MATCH",ok,"source_hash_match" if ok else "source_hash_mismatch",() if ok else ("matching_source_hash",))
def _guard_test_evidence(t,a,e,c,p):
    key=str(a.get("key") or "test_evidence"); value=e.get(key); ok=isinstance(value,dict) and bool(value.get("ok") or value.get("passed")) and not value.get("tests_failed"); return GuardResult("GUARD.TEST_EVIDENCE",ok,"test_evidence_passed" if ok else "passing_test_evidence_missing",() if ok else (key,))
def _guard_verifier_pass(t,a,e,c,p):
    key=str(a.get("key") or "verification_packet"); value=e.get(key); ok=isinstance(value,dict) and bool(value.get("ok") or value.get("passed") or value.get("verification_ok")); return GuardResult("GUARD.VERIFIER_PASS",ok,"verifier_passed" if ok else "verifier_evidence_missing",() if ok else (key,))
def _guard_lease_contains(t,a,e,c,p):
    granted={str(x) for x in c.get("lease_capabilities",()) or ()}; required={str(x) for x in a.get("capabilities",()) or t.requested_capabilities}; missing=tuple(sorted(required-granted)); return GuardResult("GUARD.LEASE_CONTAINS_CAPABILITY",not missing,"lease_contains_capability" if not missing else "lease_missing_capability",missing)
def _guard_human_approval(t,a,e,c,p):
    value=c.get("human_approval") or e.get("human_approval") or e.get("human_review"); ok=bool(value is True or (isinstance(value,dict) and (value.get("approved") or value.get("approved_for_next_gate")))); return GuardResult("GUARD.HUMAN_APPROVAL",ok,"human_approval_present" if ok else "human_approval_required",() if ok else ("human_approval",))
def _guard_lifecycle_allowed(t,a,e,c,p):
    ok=c.get("lifecycle_allowed") is True; return GuardResult("GUARD.LIFECYCLE_ALLOWED",ok,"lifecycle_allowed" if ok else "illegal_lifecycle_transition")
def _guard_policy_flag(t,a,e,c,p):
    key=str(a.get("key") or "").strip(); expected=a.get("expected",True); ok=bool(key and p.get(key)==expected); return GuardResult("GUARD.POLICY_FLAG",ok,"policy_flag_passed" if ok else "policy_flag_failed",details={"key":key,"expected":expected})
def _guard_repository_clean_or_snapshotted(t,a,e,c,p):
    ok=c.get("working_tree_dirty") is not True or bool(c.get("snapshot_digest")); return GuardResult("GUARD.REPOSITORY_CLEAN_OR_SNAPSHOTTED",ok,"repository_reproducible" if ok else "dirty_repository_without_snapshot",() if ok else ("snapshot_digest",))

DEFAULT_GUARDS={"GUARD.ALWAYS":_guard_always,"GUARD.EVIDENCE_PRESENT":_guard_evidence_present,"GUARD.EVIDENCE_ALL":_guard_evidence_all,"GUARD.EXACT_TARGET":_guard_exact_target,"GUARD.SOURCE_HASH_MATCH":_guard_source_hash_match,"GUARD.TEST_EVIDENCE":_guard_test_evidence,"GUARD.VERIFIER_PASS":_guard_verifier_pass,"GUARD.LEASE_CONTAINS_CAPABILITY":_guard_lease_contains,"GUARD.HUMAN_APPROVAL":_guard_human_approval,"GUARD.LIFECYCLE_ALLOWED":_guard_lifecycle_allowed,"GUARD.POLICY_FLAG":_guard_policy_flag,"GUARD.REPOSITORY_CLEAN_OR_SNAPSHOTTED":_guard_repository_clean_or_snapshotted}

def _rank_transition(t, *, semantic_fit, evidence, telemetry):
    p=t.soft_weight_profile; latency,lc=_measurement(telemetry,t.transition_id,"latency_cost",p.latency_cost); tokens,tc=_measurement(telemetry,t.transition_id,"token_cost",p.token_cost); thermal,thc=_measurement(telemetry,t.transition_id,"thermal_cost",p.thermal_cost); user=max(0.0,min(1.0,(p.user_fit+p.base_priority)/2.0)); return RankVector(RISK_ORDER.get(t.risk,RISK_ORDER["unknown"]),float(sum(1 for k in t.required_evidence if not _has_value(evidence.get(k)))),p.empirical_uncertainty,round(1.0-max(0.0,min(1.0,semantic_fit)),6),p.context_switch_cost,latency,tokens,thermal,round(-semantic_fit,6),round(-user,6),t.transition_id,{"latency":lc,"tokens":tc,"thermal":thc})
def _measurement(telemetry, transition_id, field, fallback):
    item=telemetry.get(transition_id,{}) if isinstance(telemetry.get(transition_id),dict) else {}; value=item.get(field); cls=str(item.get(f"{field}_measurement_class") or "")
    if value is not None:
        try: return max(0.0,float(value)),cls or "MEASURED"
        except (TypeError,ValueError): pass
    if fallback is not None: return max(0.0,float(fallback)),"DERIVED"
    return UNKNOWN_MEASUREMENT_COST,"UNAVAILABLE"
def _exact_matches(transitions, normalized): return [] if not normalized else [t for t in transitions if any(normalize_input_phrase(p)==normalized for p in t.input_phrases())]
def _semantic_fit(normalized, transition):
    if not normalized: return 0.0
    input_tokens=set(_tokens(normalized)); best=0.0
    for phrase in transition.input_phrases():
        normalized_phrase=normalize_input_phrase(phrase)
        if not normalized_phrase: continue
        if normalized_phrase in normalized or normalized in normalized_phrase: best=max(best,0.95)
        phrase_tokens=set(_tokens(normalized_phrase)); union=input_tokens|phrase_tokens
        if union: best=max(best,len(input_tokens&phrase_tokens)/len(union))
    return min(1.0,best)
def _tokens(value): return re.findall(r"[a-z0-9_]+",str(value).casefold())
def _transition_projection(t, *, current_state): return {"transition_id":t.transition_id,"label":t.ui_label,"description":t.ui_description,"from_state":current_state if t.from_state=="*" else t.from_state,"next_state":current_state if t.next_state=="*" else t.next_state,"output_symbol":t.output_symbol,"required_evidence":list(t.required_evidence),"produced_evidence":list(t.produced_evidence),"requested_capabilities":list(t.requested_capabilities),"verifier_requirement":t.verifier_requirement,"approval_requirement":t.approval_requirement,"risk":t.risk,"morphology_profile_ref":t.morphology_profile_ref,"route_capsule_ref":t.route_capsule_ref,"meta_transition":t.arena_id=="meta" or t.from_state=="*","provenance":dict(t.provenance)}
def _blocked_row(t, failed, semantic_fit, current_state):
    missing=sorted({x for result in failed for x in result.missing_evidence if x}); return {**_transition_projection(t,current_state=current_state),"failed_guards":[x.to_dict() for x in failed],"missing_evidence":missing,"remediation":[{"evidence":k,"action":f"provide:{k}"} for k in missing],"semantic_fit":round(semantic_fit,6),"fail_closed":True}
def _has_value(value): return False if value is None else (len(value)>0 if isinstance(value,(str,bytes,list,tuple,set,dict)) else True)
def _payload_digest(value): return hashlib.blake2b(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode(),digest_size=12).hexdigest()
def _runtime_denial(reason, *, arena_id, state): return {"ok":False,"version":ARENA_WFST_RUNTIME_VERSION,"arena_id":arena_id,"state":state,"reason":reason,"fail_closed":True,"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def _capsules_enabled(policy):
    raw=policy.get("route_capsules_enabled")
    if raw is not None: return raw is True
    return str(os.getenv("AURA_ROUTE_CAPSULES_ENABLED","0")).strip().casefold() in {"1","true","yes","on"}
