"""Governed execution boundary for ``AdaptiveModelRouter``.

Provider calls occur only in PAIRED_LIVE mode after a content-addressed human
authorization is validated and the Capability Connectome path plus endpoint
status are rechecked.  CASCADE advances only after call failure or verifier
rejection.  PANEL execution is delegated to AuraFusion through an injected
adapter so panel and judge observations remain native Fusion records.
"""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Callable, Mapping

from aura_adaptive_model_router import (
    ADAPTIVE_ROUTER_VERSION,
    PAIRED_LIVE,
    SHADOW,
    AdaptiveModelRouter,
    make_route_decision,
)
from aura_model_cognome import TaskContext, stable_id
from aura_model_cognome_execution_auth import ExecutionAuthorization
from aura_shadow_model_router import CASCADE, DENIED, DIRECT, PANEL, ZERO_MODEL, PolicyOption, evaluate_shadow_route

EXECUTOR_VERSION = "AURA_ADAPTIVE_MODEL_EXECUTOR_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_HIGH_RISK = frozenset({"HIGH", "CRITICAL", "CONSEQUENTIAL"})


def _default_verifier(text: str | None, error: str | None, **_kwargs: Any) -> dict[str, Any]:
    passed = bool(text and str(text).strip() and not error)
    return {
        "passed": passed,
        "format_valid": bool(text and str(text).strip()),
        "tests_passed": None,
        "tests_failed": None,
        "failure_class": "" if passed else "MODEL_CALL_FAILED",
    }


class AdaptiveModelExecutor:
    def __init__(
        self,
        *,
        router: AdaptiveModelRouter,
        egress_factory: Callable[..., Any] | None = None,
        verifier: Callable[..., Any] | None = None,
        deterministic_executor: Callable[..., Any] | None = None,
        panel_executor: Callable[..., Any] | None = None,
        persist_telemetry: bool = True,
        empirical_ledger: Any | None = None,
        logger_sink: Callable[[dict[str, Any]], Any] | None = None,
        pricing_registry: Any | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.router = router
        self.repo_root = Path(router.repo_root)
        self.store = router.store
        if egress_factory is None:
            from aura_llm_egress import ExternalLLM

            egress_factory = ExternalLLM
        self.egress_factory = egress_factory
        self.verifier = verifier
        self.deterministic_executor = deterministic_executor
        self.panel_executor = panel_executor
        self.persist_telemetry = bool(persist_telemetry)
        self._owns_ledger = False
        if self.persist_telemetry and empirical_ledger is None:
            from aura_empirical_cost_ledger import EmpiricalCostLedger

            empirical_ledger = EmpiricalCostLedger(self.repo_root)
            self._owns_ledger = True
        self.empirical_ledger = empirical_ledger
        if self.persist_telemetry and logger_sink is None:
            from aura_model_cognome_call_logger import NormalizedCallLogger

            logger_sink = NormalizedCallLogger(operation="adaptive_model_router", mode=PAIRED_LIVE)
        self.logger_sink = logger_sink
        if pricing_registry is None:
            from aura_pricing_registry import PricingRegistry

            pricing_registry = PricingRegistry(self.repo_root)
        self.pricing_registry = pricing_registry
        self.now = now
        if not hasattr(router, "_used_authorization_ids"):
            router._used_authorization_ids = set()  # type: ignore[attr-defined]

    def close(self) -> None:
        if self._owns_ledger and self.empirical_ledger is not None and hasattr(self.empirical_ledger, "close"):
            self.empirical_ledger.close()

    def _verify(
        self,
        text: str | None,
        error: str | None,
        *,
        context: TaskContext,
        candidate: Mapping[str, Any],
        objective: str,
    ) -> tuple[dict[str, Any], float]:
        started = self.now()
        if self.verifier is None and str(context.risk or "LOW").upper() in _HIGH_RISK:
            result = {
                "passed": False,
                "format_valid": False,
                "tests_passed": None,
                "tests_failed": None,
                "failure_class": "EXPLICIT_HIGH_RISK_VERIFIER_REQUIRED",
            }
        else:
            raw = (self.verifier or _default_verifier)(
                text,
                error,
                context=context,
                candidate=candidate,
                objective=objective,
            )
            if isinstance(raw, bool):
                result = {
                    "passed": raw,
                    "format_valid": bool(text),
                    "tests_passed": None,
                    "tests_failed": None,
                    "failure_class": "" if raw else "VERIFIER_REJECTED",
                }
            elif isinstance(raw, Mapping):
                result = dict(raw)
            else:
                raise TypeError("verifier must return bool or a mapping")
            if type(result.get("passed")) is not bool:
                raise ValueError("verifier result must contain a strict boolean 'passed'")
            result.setdefault("format_valid", bool(text))
            result.setdefault("tests_passed", None)
            result.setdefault("tests_failed", None)
            result.setdefault("failure_class", "" if result["passed"] else "VERIFIER_REJECTED")
        return result, max(0.0, (self.now() - started) * 1000.0)

    def _call_egress(
        self,
        *,
        candidate: Mapping[str, Any],
        objective: str,
        router_context: str,
        call_type: str,
    ) -> dict[str, Any]:
        provider = str(candidate.get("provider") or "")
        model = str(
            candidate.get("model")
            or candidate.get("returned_model")
            or candidate.get("requested_model")
            or ""
        )
        egress = self.egress_factory(
            provider=provider,
            model=model,
            task=call_type,
            aspect="adaptive_router",
        )
        started = self.now()
        raw = egress.generate(
            objective,
            router_context=router_context or None,
            call_type=call_type,
        )
        elapsed = max(0.0, self.now() - started)
        if isinstance(raw, Mapping):
            return {
                "text": raw.get("text"),
                "error": raw.get("error"),
                "latency_sec": float(raw.get("latency_sec", elapsed)),
                "usage": dict(raw.get("usage") or {}),
                "returned_model": str(raw.get("returned_model") or model),
            }
        if not isinstance(raw, tuple) or len(raw) < 3:
            raise TypeError("egress generate must return (text, error, latency) or a mapping")
        return {
            "text": raw[0],
            "error": raw[1],
            "latency_sec": float(raw[2]),
            "usage": {},
            "returned_model": model,
        }

    def _persist_call(
        self,
        *,
        context: TaskContext,
        decision: Any,
        candidate: Mapping[str, Any],
        result: Mapping[str, Any],
        verification: Mapping[str, Any],
        verifier_ms: float,
        correlation_id: str,
        attempt_index: int,
        fallback_index: int,
        comparison_id: str,
    ) -> dict[str, Any]:
        from aura_model_cognome_telemetry import (
            StageTimings,
            TelemetryLinkage,
            build_telemetry_packet,
            persist_telemetry_packet,
        )

        profile_id = str(candidate.get("profile_id") or "")
        linkage = TelemetryLinkage.create(
            correlation_id=correlation_id,
            profile_id=profile_id,
            route_decision_id=decision.route_decision_id,
            task_context_id=context.task_context_id,
            comparison_id=comparison_id,
            attempt_index=attempt_index,
            fallback_index=fallback_index,
            event_nonce=f"{decision.route_decision_id}:{profile_id}:{attempt_index}:{fallback_index}",
        )
        packet = build_telemetry_packet(
            linkage=linkage,
            provider=str(candidate.get("provider") or ""),
            model=str(result.get("returned_model") or candidate.get("model") or ""),
            raw_usage=dict(result.get("usage") or {}),
            timings=StageTimings(
                generation_ms=max(0.0, float(result.get("latency_sec") or 0.0) * 1000.0),
                verifier_ms=verifier_ms,
            ),
            pricing_registry=self.pricing_registry,
            policy_mode=decision.policy_mode,
            verifier_pass=verification.get("passed"),
            tests_passed=verification.get("tests_passed"),
            tests_failed=verification.get("tests_failed"),
            format_valid=verification.get("format_valid"),
            failure_class=str(verification.get("failure_class") or result.get("error") or ""),
            shadow_only=False,
            extra_evidence={
                "execution_mode": PAIRED_LIVE,
                "returned_model": result.get("returned_model"),
                "provider_error": str(result.get("error") or ""),
            },
        )
        persistence = None
        if self.persist_telemetry:
            persistence = persist_telemetry_packet(
                packet,
                cognome_store=self.store,
                empirical_ledger=self.empirical_ledger,
                logger_sink=self.logger_sink,
            )
        return {
            "call_id": linkage.call_id,
            "cost_run_id": linkage.cost_run_id,
            "observation_id": packet.observation.observation_id,
            "telemetry": packet.to_dict(),
            "persistence": persistence,
        }

    def _deny(self, plan: Mapping[str, Any], reasons: list[str], auth_id: str = "") -> dict[str, Any]:
        return {
            **dict(plan),
            "status": DENIED,
            "executed": False,
            "execution_mode": PAIRED_LIVE,
            "denial_reasons": list(dict.fromkeys(reasons)),
            "authorization_id": auth_id,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "executor_version": EXECUTOR_VERSION,
        }

    def execute(
        self,
        objective: str,
        *,
        purpose_digest: str,
        execution_mode: str = SHADOW,
        authorization: ExecutionAuthorization | Mapping[str, Any] | None = None,
        target_files: list[str] | None = None,
        target_symbols: list[str] | None = None,
        forced_model: str | None = None,
        task_fields: Mapping[str, Any] | None = None,
        token_budget: int = 2400,
    ) -> dict[str, Any]:
        mode = str(execution_mode or SHADOW).upper()
        if mode not in {SHADOW, PAIRED_LIVE}:
            raise ValueError(f"unknown adaptive execution mode: {mode}")
        plan = self.router.plan(
            objective,
            purpose_digest=purpose_digest,
            target_files=target_files,
            target_symbols=target_symbols,
            forced_model=forced_model,
            task_fields=task_fields,
            token_budget=token_budget,
        )
        if mode == SHADOW or plan.get("status") == DENIED:
            plan["execution_mode"] = SHADOW
            plan["executed"] = False
            return plan
        if authorization is None:
            return self._deny(plan, ["PAIRED_LIVE requires explicit authorization"])
        auth = authorization if isinstance(authorization, ExecutionAuthorization) else ExecutionAuthorization.from_mapping(authorization)
        used = self.router._used_authorization_ids  # type: ignore[attr-defined]
        if auth.authorization_id in used:
            return self._deny(plan, ["authorization has already been consumed"], auth.authorization_id)

        context = TaskContext(**dict(plan["task_context"]))
        option_data = dict(plan["selected_option"])
        policy_mode = str(option_data["policy_mode"])
        profile_ids = tuple(str(item) for item in option_data.get("profile_ids", []) or [])
        estimated_calls = 0 if policy_mode == ZERO_MODEL else len(profile_ids) + (1 if policy_mode == PANEL else 0)
        errors = auth.validate_for(
            purpose_digest=context.purpose_digest,
            graph_digest=str(plan["path_resolution"].get("graph_digest") or ""),
            policy_mode=policy_mode,
            profile_ids=profile_ids,
            call_count=estimated_calls,
            forced_override=bool(plan.get("forced_human_override")),
            verifier_id=context.verifier_id,
            now=self.now(),
        )
        errors.extend(self.router.revalidate(plan))
        if policy_mode == ZERO_MODEL and self.deterministic_executor is None:
            errors.append("ZERO_MODEL live execution requires an injected deterministic executor")
        if policy_mode == PANEL and self.panel_executor is None:
            errors.append("PANEL execution requires AuraFusion panel integration")
        if errors:
            return self._deny(plan, errors, auth.authorization_id)

        comparison_id = stable_id("paired-live", {
            "authorization_id": auth.authorization_id,
            "proposal_route_decision_id": plan["route_decision"]["route_decision_id"],
        })
        stored_comparison = self.store.record_experiment_comparison({
            "comparison_id": comparison_id,
            "measurement_mode": PAIRED_LIVE,
            "approved_live": True,
            "approved_by": auth.approved_by,
            "authorization_id": auth.authorization_id,
            "purpose_digest": context.purpose_digest,
            "capability_graph_digest": context.capability_graph_digest,
            "created_at": self.now(),
        })
        if stored_comparison != comparison_id:
            return self._deny(plan, ["experiment comparison ID mismatch"], auth.authorization_id)
        used.add(auth.authorization_id)

        fresh = evaluate_shadow_route(
            context=context,
            path_resolution=plan["path_resolution"],
            policy=self.router.policy,
            created_at=self.now(),
        )
        assessments = tuple(fresh.candidate_assessments)
        option = PolicyOption(
            policy_mode=policy_mode,
            profile_ids=profile_ids,
            expected_success=float(option_data["expected_success"]),
            expected_cost_usd=option_data.get("expected_cost_usd"),
            expected_time_to_verified_ms=option_data.get("expected_time_to_verified_ms"),
            expected_repair_burden=float(option_data.get("expected_repair_burden") or 0.0),
            expected_scope_violation_rate=float(option_data.get("expected_scope_violation_rate") or 0.0),
            expected_drift=float(option_data.get("expected_drift") or 0.0),
            expected_energy_joules=option_data.get("expected_energy_joules"),
            utility=float(option_data.get("utility") or 0.0),
            explanation=tuple(str(item) for item in option_data.get("explanation", []) or []),
        )
        live_decision = make_route_decision(
            context=context,
            option=option,
            assessments=assessments,
            graph_digest=context.capability_graph_digest,
            path_digest=str(plan["path_resolution"].get("path_digest") or ""),
            policy_version=f"{self.router.policy.policy_version}/PAIRED_LIVE",
            policy_evidence_digest=str(plan.get("policy_evidence_digest") or ""),
            proposal_only=False,
            human_override=bool(plan.get("forced_human_override")),
            created_at=self.now(),
        )
        self.store.record_route_decision(live_decision)
        correlation_id = stable_id("adaptive-execution", {
            "authorization_id": auth.authorization_id,
            "route_decision_id": live_decision.route_decision_id,
        })

        common = {
            **plan,
            "execution_mode": PAIRED_LIVE,
            "authorization_id": auth.authorization_id,
            "comparison_id": comparison_id,
            "live_route_decision": live_decision.to_dict(),
            "correlation_id": correlation_id,
            "proposal_only": False,
            "shadow_only": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "version": ADAPTIVE_ROUTER_VERSION,
            "executor_version": EXECUTOR_VERSION,
        }
        if policy_mode == ZERO_MODEL:
            output = self.deterministic_executor(objective, context=context, routing=plan["routing"])
            return {**common, "status": "EXECUTED", "executed": True, "output": output, "calls": []}
        if policy_mode == PANEL:
            panel = self.panel_executor(
                objective=objective,
                plan=plan,
                context=context,
                live_decision=live_decision,
                authorization=auth,
                comparison_id=comparison_id,
                correlation_id=correlation_id,
            )
            return {
                **common,
                "status": "EXECUTED" if bool(panel.get("ok")) else "FAILED",
                "executed": True,
                "panel_result": panel,
            }

        candidates = dict(plan.get("candidate_records", {}))
        calls: list[dict[str, Any]] = []
        final_text: str | None = None
        final_error: str | None = None
        verified = False
        for index, profile_id in enumerate(profile_ids):
            current_errors = self.router.revalidate(plan)
            if current_errors:
                final_error = "; ".join(current_errors)
                break
            candidate = dict(candidates.get(profile_id) or {})
            if not candidate:
                final_error = f"selected candidate record is unavailable: {profile_id}"
                break
            call_result = self._call_egress(
                candidate=candidate,
                objective=objective,
                router_context=str(plan.get("routing", {}).get("router_context") or ""),
                call_type=f"adaptive_{policy_mode.lower()}",
            )
            verification, verifier_ms = self._verify(
                call_result.get("text"),
                call_result.get("error"),
                context=context,
                candidate=candidate,
                objective=objective,
            )
            lineage = self._persist_call(
                context=context,
                decision=live_decision,
                candidate=candidate,
                result=call_result,
                verification=verification,
                verifier_ms=verifier_ms,
                correlation_id=correlation_id,
                attempt_index=index,
                fallback_index=index if policy_mode == CASCADE else 0,
                comparison_id=comparison_id,
            )
            calls.append({
                "profile_id": profile_id,
                "provider": candidate.get("provider"),
                "model": candidate.get("model"),
                "text": call_result.get("text"),
                "error": call_result.get("error"),
                "latency_sec": call_result.get("latency_sec"),
                "verification": verification,
                **lineage,
            })
            final_text = call_result.get("text")
            final_error = call_result.get("error")
            verified = bool(verification.get("passed"))
            if verified or policy_mode == DIRECT:
                break
            if policy_mode != CASCADE:
                break

        return {
            **common,
            "status": "EXECUTED" if verified else "FAILED",
            "executed": True,
            "output": final_text,
            "error": final_error,
            "verified": verified,
            "calls": calls,
        }
