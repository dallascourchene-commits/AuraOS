"""AuraFusion adapter for an authorized Cognome PANEL route.

Each selected profile receives one explicit Fusion role.  The final selected
profile is the JUDGE and at least two earlier profiles form the panel.  Calls use
AuraFusion's canonical OpenAI-compatible egress, while stable Cognome call and
observation IDs are attached to every panel and judge record.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import threading
from typing import Any, Callable, Mapping

from aura_fusion import (
    JUDGE_SCHEMA,
    PANEL_SCHEMA,
    AuraFusionAgent,
    AuraFusionCoordinator,
    generate_openai_compatible_payload,
    parse_json_object,
)
from aura_model_cognome_telemetry import (
    StageTimings,
    TelemetryLinkage,
    build_telemetry_packet,
    persist_telemetry_packet,
)
from aura_provider_registry import ProviderRegistry
from aura_shadow_model_router import PANEL

ADAPTIVE_FUSION_VERSION = "AURA_ADAPTIVE_FUSION_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_PANEL_ROLES = ("THINKER", "WORKER", "VERIFIER", "RESEARCHER")


def _schema_value_valid(value: Any, schema: Mapping[str, Any]) -> bool:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        required = schema.get("required", ())
        if any(field not in value for field in required):
            return False
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            return False
        return all(
            _schema_value_valid(item, properties[key])
            for key, item in value.items()
            if key in properties
        )
    if expected == "array":
        return isinstance(value, list) and all(
            _schema_value_valid(item, schema.get("items", {})) for item in value
        )
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return type(value) is bool
    if expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        number = float(value)
        if not math.isfinite(number):
            return False
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        return (minimum is None or number >= float(minimum)) and (
            maximum is None or number <= float(maximum)
        )
    return True


class AdaptiveFusionPanelExecutor:
    def __init__(
        self,
        *,
        repo_root: str | Path = ".",
        store: Any,
        empirical_ledger: Any | None = None,
        logger_sink: Callable[[dict[str, Any]], Any] | None = None,
        pricing_registry: Any | None = None,
        provider_registry: ProviderRegistry | None = None,
        caller: Callable[..., tuple[str | None, str | None, float, bool]] | None = None,
        coordinator_factory: Callable[..., AuraFusionCoordinator] = AuraFusionCoordinator,
        secrets: dict[str, Any] | None = None,
        mock: bool = False,
        persist_telemetry: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.store = store
        self.persist_telemetry = bool(persist_telemetry)
        self._owns_ledger = False
        if self.persist_telemetry and empirical_ledger is None:
            from aura_empirical_cost_ledger import EmpiricalCostLedger

            empirical_ledger = EmpiricalCostLedger(self.repo_root)
            self._owns_ledger = True
        self.empirical_ledger = empirical_ledger
        if self.persist_telemetry and logger_sink is None:
            from aura_model_cognome_call_logger import NormalizedCallLogger

            logger_sink = NormalizedCallLogger(operation="adaptive_fusion", mode="PAIRED_LIVE")
        self.logger_sink = logger_sink
        if pricing_registry is None:
            from aura_pricing_registry import PricingRegistry

            pricing_registry = PricingRegistry(self.repo_root)
        self.pricing_registry = pricing_registry
        self.provider_registry = provider_registry or ProviderRegistry()
        self.caller = caller or generate_openai_compatible_payload
        self.coordinator_factory = coordinator_factory
        self.secrets = secrets
        self.mock = bool(mock)

    def close(self) -> None:
        if self._owns_ledger and self.empirical_ledger is not None and hasattr(self.empirical_ledger, "close"):
            self.empirical_ledger.close()

    def _agent(
        self,
        *,
        candidate: Mapping[str, Any],
        role: str,
        profile_id: str,
    ) -> AuraFusionAgent:
        provider = str(candidate.get("provider") or "").lower()
        model = str(
            candidate.get("model")
            or candidate.get("returned_model")
            or candidate.get("requested_model")
            or ""
        )
        config = self.provider_registry.get_provider_config(provider)
        if config is None and not self.mock:
            raise ValueError(f"Fusion provider is not registered: {provider}")
        config = config or {"base_url": "mock", "api_key_env": "MOCK_API_KEY"}
        return AuraFusionAgent(
            name=f"cognome_{role.lower()}_{profile_id[-8:]}",
            role=role,
            provider=provider or "mock",
            base_url=str(config["base_url"]),
            api_key_name=str(config["api_key_env"]),
            model=model or f"mock-{role.lower()}",
        )

    def _agents(
        self,
        profile_ids: tuple[str, ...],
        candidates: Mapping[str, Any],
    ) -> tuple[list[AuraFusionAgent], AuraFusionAgent, dict[str, str]]:
        if len(profile_ids) < 3:
            raise ValueError("PANEL execution requires at least two panel profiles and one judge profile")
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("PANEL execution cannot reuse the same profile")
        panel_ids = profile_ids[:-1]
        judge_id = profile_ids[-1]
        if len(panel_ids) > len(_PANEL_ROLES):
            raise ValueError("PANEL route exceeds supported distinct Fusion roles")
        name_to_profile: dict[str, str] = {}
        panel: list[AuraFusionAgent] = []
        for index, profile_id in enumerate(panel_ids):
            candidate = candidates.get(profile_id)
            if not isinstance(candidate, Mapping):
                raise ValueError(f"missing selected Fusion candidate: {profile_id}")
            agent = self._agent(candidate=candidate, role=_PANEL_ROLES[index], profile_id=profile_id)
            panel.append(agent)
            name_to_profile[agent.name] = profile_id
        judge_candidate = candidates.get(judge_id)
        if not isinstance(judge_candidate, Mapping):
            raise ValueError(f"missing selected Fusion judge candidate: {judge_id}")
        judge = self._agent(candidate=judge_candidate, role="JUDGE", profile_id=judge_id)
        name_to_profile[judge.name] = judge_id
        return panel, judge, name_to_profile

    @staticmethod
    def _agent_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            payload = json.loads(str(messages[-1].get("content") or "{}"))
        except (json.JSONDecodeError, IndexError, AttributeError):
            return {}
        return dict(payload.get("agent") or {}) if isinstance(payload, dict) else {}

    @staticmethod
    def _schema_passed(role: str, text: str | None, error: str | None) -> bool:
        if not text or error:
            return False
        try:
            parsed = parse_json_object(text)
        except Exception:
            return False
        schema = JUDGE_SCHEMA if role == "JUDGE" else PANEL_SCHEMA
        return _schema_value_valid(parsed, schema)

    def __call__(
        self,
        *,
        objective: str,
        plan: Mapping[str, Any],
        context: Any,
        live_decision: Any,
        authorization: Any,
        comparison_id: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        profile_ids = tuple(str(item) for item in plan["selected_option"]["profile_ids"])
        candidates = dict(plan.get("candidate_records", {}))
        panel, judge, name_to_profile = self._agents(profile_ids, candidates)
        role_index = {agent.name: index for index, agent in enumerate([*panel, judge])}
        links: dict[str, dict[str, Any]] = {}
        lock = threading.Lock()

        def linked_caller(**kwargs: Any):
            messages = list(kwargs.get("messages") or [])
            agent_payload = self._agent_payload(messages)
            agent_name = str(agent_payload.get("name") or "unknown")
            role = str(agent_payload.get("role") or "UNKNOWN").upper()
            profile_id = name_to_profile.get(agent_name, "")
            if not profile_id:
                raise ValueError(f"Fusion call has no selected Cognome profile: {agent_name}")
            text, error, latency, used_schema = self.caller(**kwargs)
            passed = self._schema_passed(role, text, error)
            linkage = TelemetryLinkage.create(
                correlation_id=correlation_id,
                profile_id=profile_id,
                route_decision_id=live_decision.route_decision_id,
                task_context_id=context.task_context_id,
                comparison_id=comparison_id,
                attempt_index=role_index[agent_name],
                fallback_index=0,
                event_nonce=f"fusion:{agent_name}:{role}",
            )
            with lock:
                links[agent_name] = {
                    "profile_id": profile_id,
                    "task_context_id": context.task_context_id,
                    "route_decision_id": live_decision.route_decision_id,
                    "call_id": linkage.call_id,
                    "cost_run_id": linkage.cost_run_id,
                    "linkage": linkage,
                    "provider": str(kwargs.get("provider") or ""),
                    "model": str(kwargs.get("model") or ""),
                    "latency": max(0.0, float(latency)),
                    "verifier_pass": passed,
                    "failure_class": "" if passed else str(error or "FUSION_SCHEMA_REJECTED"),
                    "used_response_schema": bool(used_schema),
                }
            return text, error, latency, used_schema

        coordinator = self.coordinator_factory(
            repo_root=str(self.repo_root),
            secrets=self.secrets,
            panel=panel,
            judge=judge,
            mock=self.mock,
            caller=linked_caller,
        )
        routing = dict(plan.get("routing", {}))
        result = coordinator.run(
            objective,
            mode="adaptive_panel",
            target_file=str(routing.get("primary_file") or "") or None,
            target_symbol=(list(routing.get("key_functions", []) or [None])[0]),
            extra_capsule={
                "task_context_id": context.task_context_id,
                "route_decision_id": live_decision.route_decision_id,
                "authorization_id": authorization.authorization_id,
                "capability_graph_digest": context.capability_graph_digest,
                "capability_path_digest": plan.get("path_resolution", {}).get("path_digest", ""),
            },
        ).to_dict()
        persistence_failed = False
        for link in links.values():
            packet = build_telemetry_packet(
                linkage=link.pop("linkage"),
                provider=link.pop("provider"),
                model=link.pop("model"),
                raw_usage={},
                timings=StageTimings(generation_ms=link.pop("latency") * 1000.0),
                pricing_registry=self.pricing_registry,
                policy_mode=PANEL,
                verifier_pass=link["verifier_pass"],
                format_valid=link["verifier_pass"],
                failure_class=link.pop("failure_class"),
                shadow_only=False,
                extra_evidence={
                    "fusion_agent": next(
                        (name for name, candidate in links.items() if candidate is link), ""
                    ),
                    "used_response_schema": link.pop("used_response_schema"),
                    "authorization_id": authorization.authorization_id,
                },
            )
            link["observation_id"] = packet.observation.observation_id
            link["persistence"] = None
            if self.persist_telemetry:
                try:
                    link["persistence"] = persist_telemetry_packet(
                        packet,
                        cognome_store=self.store,
                        empirical_ledger=self.empirical_ledger,
                        logger_sink=self.logger_sink,
                    )
                except Exception as exc:
                    persistence_failed = True
                    link["persistence_error"] = f"TELEMETRY_PERSISTENCE_EXCEPTION:{type(exc).__name__}"
        for output in result.get("panel_outputs", []):
            output.update(links.get(str(output.get("agent") or ""), {}))
        judge_output = result.get("judge_output", {})
        judge_output.update(links.get(str(judge_output.get("agent") or ""), {}))
        result["judge_output"] = judge_output
        result["ok"] = (
            bool(result.get("ok"))
            and not persistence_failed
            and len(links) == len(profile_ids)
            and all(bool(item.get("verifier_pass")) for item in links.values())
        )
        result["calls"] = [links[name] | {"agent": name} for name in sorted(links)]
        result["task_context_id"] = context.task_context_id
        result["route_decision_id"] = live_decision.route_decision_id
        result["authorization_id"] = authorization.authorization_id
        result["version"] = ADAPTIVE_FUSION_VERSION
        result["patch_authority"] = PATCH_AUTHORITY
        result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return result
