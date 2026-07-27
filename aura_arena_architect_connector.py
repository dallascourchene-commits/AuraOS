"""Shared governed Architect/Surgeon connector for every Aura Arena surface.

Native Aura, Coding Arena, Human Agent Arena, MCP clients, HTTP/container clients,
and third-party coding agents enter through this same bounded service. Candidate
plans are frozen and recorded before selection. The selected plan is then passed
verbatim into ``ArchitectFusionLoop.prepare`` and checked against the resulting
Act Capsules before any Surgeon turn is leased.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Any, Callable, Mapping, Sequence

from aura_architect_control import (
    ArchitectControlProfile,
    control_capabilities,
    normalize_control_profile,
)
from aura_architect_council_v2 import profile_refactor_length
from aura_architect_council_v3 import (
    route_compass_failure_classes,
    select_critic_lanes,
)
from aura_cognitive_labor_router import route_initial_refactor
from aura_controlled_refactor_session import ControlledRefactorSessionManager
from aura_native_model_gateway import AuraNativeModelGateway
from aura_refactor_output_vault import RefactorOutputVault
from aura_relationship_contracts import (
    BilateralPlanningContract,
    evaluate_bilateral_plan,
)

ARENA_ARCHITECT_CONNECTOR_VERSION = "AURA_ARENA_ARCHITECT_CONNECTOR_V3"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
MAX_CANDIDATES = 8
MAX_TASKS = 64
MAX_PLAN_BYTES = 262_144
_REQUIRED = (
    "architecture_decision",
    "act_tasks",
    "acceptance_criteria",
    "rollback_conditions",
    "risk_map",
    "constraints",
)
_BILATERAL_REQUIRED = (
    "intent_digest",
    "semantic_ledger_digest",
    "confirmation_digest",
    "positive_requirement_coverage",
    "negative_requirement_coverage",
    "guardrail_coverage",
    "assumption_register",
    "plan_revision_policy",
)
_ALL_CRITIC_LANES = ("scope", "tests", "sequence", "continuity", "rollback", "cost")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_canonical(value).encode("utf-8"), digest_size=size).hexdigest()


def _tokens(value: Any) -> int:
    return (len(_canonical(value)) + 3) // 4


def _normalize_plan_path(value: Any) -> str:
    normalized = str(value or "").replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _candidate(candidate: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(candidate, Mapping):
        raise ValueError("every candidate must be an object")
    candidate_id = str(candidate.get("candidate_id") or candidate.get("plan_id") or "candidate")
    plan = dict(candidate.get("plan") or candidate)
    if len(json.dumps(plan, default=str).encode("utf-8")) > MAX_PLAN_BYTES:
        raise ValueError("candidate plan exceeds the bounded plan size")
    tasks = list(plan.get("act_tasks") or [])
    if len(tasks) > MAX_TASKS:
        raise ValueError(f"candidate plan exceeds {MAX_TASKS} Act Capsules")
    if any(not isinstance(item, Mapping) for item in tasks):
        raise ValueError("every Act Capsule must be an object")
    return candidate_id, plan


def _effective_lanes(
    candidate_id: str,
    plan: Mapping[str, Any],
    control: ArchitectControlProfile,
) -> tuple[str, ...]:
    if control.council_mode == "OFF":
        return ()
    if control.critic_lanes:
        lanes = list(control.critic_lanes)
    elif control.council_mode == "FULL_V2":
        lanes = list(_ALL_CRITIC_LANES)
    else:
        lanes = select_critic_lanes({"candidate_id": candidate_id, "plan": dict(plan)})
    return tuple(lanes[: control.council_call_budget])


def _task_projection(task: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(task.get("task_id") or task.get("id") or ""),
        "objective": str(task.get("objective") or "").strip(),
        "target_file": _normalize_plan_path(task.get("target_file")),
        "target_symbol": str(task.get("target_symbol") or ""),
        "related_files": [
            _normalize_plan_path(item) for item in list(task.get("related_files") or [])
        ],
        "allowed_scope": str(task.get("allowed_scope") or "single bounded edit"),
        "acceptance": str(
            task.get("acceptance") or "Return a bounded patch or a refusal reason."
        ),
        "expected_output": str(task.get("expected_output") or "UNIFIED_DIFF").upper(),
        "size": str(task.get("size") or "S").upper(),
    }


def _prepared_projection(prepared: Any) -> list[dict[str, Any]]:
    return [_task_projection(item.to_dict()) for item in prepared.plan.act_capsules]


@dataclass(frozen=True)
class PlanAssessment:
    candidate_id: str
    score: float
    selected_critic_lanes: tuple[str, ...]
    length_profile: dict[str, Any]
    coverage_fraction: float
    exact_task_fraction: float
    governance_fraction: float
    testability_fraction: float
    architecture_reuse: bool
    reasons: tuple[str, ...]
    plan_digest: str
    token_proxy: int
    council_mode: str
    planned_critic_calls: int
    eligible: bool = True
    bilateral_gate: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["selected_critic_lanes"] = list(self.selected_critic_lanes)
        value["reasons"] = list(self.reasons)
        value["actual_model_calls"] = 0
        value["planned_critic_lane_count"] = self.planned_critic_calls
        return value


class AuraArenaArchitectConnector:
    """One bounded Architect/Surgeon service for all Aura access surfaces."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        bridge: Any | None = None,
        bridge_factory: Callable[..., Any] | None = None,
        model_gateway: AuraNativeModelGateway | None = None,
        record_path: str | Path | None = None,
        output_vault: RefactorOutputVault | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._bridge = bridge
        self._bridge_factory = bridge_factory
        self.model_gateway = model_gateway or AuraNativeModelGateway(self.repo_root)
        if record_path:
            raw_record = Path(record_path)
            self.record_path = raw_record if raw_record.is_absolute() else self.repo_root / raw_record
        else:
            self.record_path = (
                self.repo_root
                / "Aura_Memory"
                / "benchmarks"
                / "architect_plan_selections.jsonl"
            )
        self.output_vault = output_vault or RefactorOutputVault(self.repo_root)
        self._surgeon_sessions: dict[str, ControlledRefactorSessionManager] = {}
        self._lock = threading.RLock()

    @property
    def bridge(self) -> Any:
        if self._bridge is None:
            factory = self._bridge_factory
            if factory is None:
                from aura_agent_arena_bridge import AuraAgentArenaBridge

                factory = AuraAgentArenaBridge
            self._bridge = factory(repo_root=self.repo_root)
        return self._bridge

    def _resolve_bilateral_contract(
        self,
        contract: BilateralPlanningContract | Mapping[str, Any] | None,
        confirmation_session_id: str,
    ) -> BilateralPlanningContract | None:
        if contract is None and not confirmation_session_id:
            return None
        if isinstance(contract, BilateralPlanningContract):
            return contract
        if not confirmation_session_id:
            raise ValueError(
                "confirmation_session_id is required for serialized bilateral contracts"
            )
        retained = self.bridge._retained_bilateral_contract(confirmation_session_id)
        resolved = BilateralPlanningContract.from_dict(retained)
        if contract is not None:
            supplied = BilateralPlanningContract.from_dict(contract)
            if supplied.contract_digest != resolved.contract_digest:
                raise ValueError(
                    "serialized bilateral contract does not match retained confirmation"
                )
        return resolved

    def validate_control(
        self,
        control: Mapping[str, Any] | ArchitectControlProfile | None = None,
        *,
        surface: str = "native",
        benchmark: bool = False,
    ) -> dict[str, Any]:
        profile = normalize_control_profile(control, surface=surface, benchmark=benchmark)
        return {
            "ok": True,
            "control_profile": profile.to_dict(),
            "capabilities": control_capabilities(profile.surface),
        }

    def assess_plan(
        self,
        candidate: Mapping[str, Any],
        *,
        required_capabilities: Sequence[str] = (),
        control: Mapping[str, Any] | ArchitectControlProfile | None = None,
        surface: str = "native",
        bilateral_contract: BilateralPlanningContract | Mapping[str, Any] | None = None,
        confirmation_session_id: str = "",
        observed_repository_head: str = "",
        observed_source_tree_digest: str = "",
        observed_at: float | None = None,
        _trusted_observation: Mapping[str, Any] | None = None,
    ) -> PlanAssessment:
        profile = normalize_control_profile(control, surface=surface)
        candidate_id, plan = _candidate(candidate)
        bilateral = self._resolve_bilateral_contract(
            bilateral_contract, confirmation_session_id
        )
        bilateral_gate = None
        eligible = True
        if bilateral is not None:
            if _trusted_observation is None:
                from aura_arena_gate_dialogue import _repository_identity

                identity = _repository_identity(self.repo_root)
                observation = {
                    "repository_head": str(identity["repository_head"]),
                    "source_tree_digest": str(identity["source_tree_digest"]),
                    "observed_at": time.time(),
                }
            else:
                observation = dict(_trusted_observation)
            gate = evaluate_bilateral_plan(
                plan,
                bilateral,
                observed_repository_head=str(observation["repository_head"]),
                observed_source_tree_digest=str(observation["source_tree_digest"]),
                observed_at=float(observation["observed_at"]),
            )
            bilateral_gate = gate.to_dict()
            eligible = gate.passed
        tasks = [dict(item) for item in list(plan.get("act_tasks") or [])]
        length = profile_refactor_length(plan)
        lanes = _effective_lanes(candidate_id, plan, profile)
        required = {str(item) for item in required_capabilities if str(item)}
        covered = {str(item) for item in list(plan.get("coverage_tags") or []) if str(item)}
        coverage = 1.0 if not required else len(required & covered) / len(required)
        exact = sum(
            bool(
                str(task.get("task_id") or "").strip()
                and str(task.get("target_file") or "").strip()
                and str(task.get("target_symbol") or "").strip()
                and str(task.get("acceptance") or "").strip()
                and str(task.get("expected_output") or "").upper() == "UNIFIED_DIFF"
            )
            for task in tasks
        ) / max(1, len(tasks))
        governance = sum(bool(plan.get(field)) for field in _REQUIRED) / len(_REQUIRED)
        if bilateral is not None:
            governance = (
                sum(bool(plan.get(field)) for field in (*_REQUIRED, *_BILATERAL_REQUIRED))
                / (len(_REQUIRED) + len(_BILATERAL_REQUIRED))
            )
        testability = min(
            1.0,
            (
                len(list(plan.get("acceptance_criteria") or []))
                + sum(bool(task.get("tests") or task.get("acceptance")) for task in tasks)
            )
            / max(1, len(tasks) + 1),
        )
        reuse = bool(plan.get("architecture_reuse") or plan.get("existing_modules"))
        reasons: list[str] = []
        if coverage == 1.0:
            reasons.append("covers_all_required_capabilities")
        if exact == 1.0:
            reasons.append("all_act_capsules_are_exact")
        if governance == 1.0:
            reasons.append("complete_governance_contract")
        if reuse:
            reasons.append("reuses_existing_aura_architecture")
        if "tests" in lanes:
            reasons.append("controlled_test_critic")
        if "sequence" in lanes or "continuity" in lanes:
            reasons.append("long_horizon_dependencies_reviewed")
        if profile.council_mode == "OFF":
            reasons.append("council_disabled_by_human_control")
        if bilateral is not None:
            reasons.append(
                "bilateral_deterministic_gate_passed"
                if eligible
                else "bilateral_deterministic_gate_failed"
            )
            reasons.extend(
                f"bilateral_blocker:{item}"
                for item in (bilateral_gate or {}).get("failure_classes", [])
            )
        score = (
            coverage * 0.34
            + exact * 0.20
            + governance * 0.16
            + testability * 0.14
            + (0.10 if reuse else 0)
            + min(0.06, len(lanes) * 0.01)
        )
        if not tasks:
            score = 0.0
            reasons.append("no_act_capsules")
        if not eligible:
            score = 0.0
        return PlanAssessment(
            candidate_id=candidate_id,
            score=round(min(1.0, score), 4),
            selected_critic_lanes=lanes,
            length_profile=length.to_dict(),
            coverage_fraction=round(coverage, 4),
            exact_task_fraction=round(exact, 4),
            governance_fraction=round(governance, 4),
            testability_fraction=round(testability, 4),
            architecture_reuse=reuse,
            reasons=tuple(reasons),
            plan_digest=_digest(plan),
            token_proxy=_tokens(plan),
            council_mode=profile.council_mode,
            planned_critic_calls=len(lanes),
            eligible=eligible,
            bilateral_gate=bilateral_gate,
        )

    def compare_plans(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        control: Mapping[str, Any] | ArchitectControlProfile | None = None,
        surface: str = "native",
        run_id: str = "",
        record: bool = True,
        benchmark: bool = False,
        bilateral_contract: BilateralPlanningContract | Mapping[str, Any] | None = None,
        confirmation_session_id: str = "",
        observed_repository_head: str = "",
        observed_source_tree_digest: str = "",
        observed_at: float | None = None,
    ) -> dict[str, Any]:
        objective = str(objective or "").strip()
        if not objective:
            raise ValueError("objective is required")
        if isinstance(candidates, (str, bytes)) or not candidates:
            raise ValueError("at least one candidate plan is required")
        if len(candidates) > MAX_CANDIDATES:
            raise ValueError(f"at most {MAX_CANDIDATES} candidate plans are allowed")
        if any(not isinstance(item, Mapping) for item in candidates):
            raise ValueError("every candidate must be an object")
        if isinstance(required_capabilities, (str, bytes)):
            raise ValueError("required_capabilities must be an array")
        ids = [
            str(item.get("candidate_id") or item.get("plan_id") or "candidate")
            for item in candidates
        ]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate ids must be unique")
        profile = normalize_control_profile(control, surface=surface, benchmark=benchmark)
        bilateral = self._resolve_bilateral_contract(
            bilateral_contract, confirmation_session_id
        )
        observation = None
        if bilateral is not None:
            from aura_arena_gate_dialogue import _repository_identity

            identity = _repository_identity(self.repo_root)
            observation = {
                "repository_head": str(identity["repository_head"]),
                "source_tree_digest": str(identity["source_tree_digest"]),
                "observed_at": time.time(),
            }
        assessments = [
            self.assess_plan(
                item,
                required_capabilities=required_capabilities,
                control=profile,
                surface=profile.surface,
                bilateral_contract=bilateral,
                confirmation_session_id="",
                _trusted_observation=observation,
            )
            for item in candidates
        ]
        assessments.sort(
            key=lambda item: (
                not item.eligible,
                -item.score,
                item.token_proxy,
                item.candidate_id,
            )
        )
        eligible_assessments = [item for item in assessments if item.eligible]
        if bilateral_contract is not None and not eligible_assessments:
            failure_classes = list(
                dict.fromkeys(
                    failure_class
                    for assessment in assessments
                    for failure_class in (
                        assessment.bilateral_gate or {}
                    ).get("council_failure_classes", [])
                )
            )
            return {
                "ok": False,
                "version": ARENA_ARCHITECT_CONNECTOR_VERSION,
                "objective": objective,
                "reason": "NO_BILATERAL_ELIGIBLE_PLAN",
                "assessments": [item.to_dict() for item in assessments],
                "failure_route": route_compass_failure_classes(failure_classes),
                "proposal_only": True,
                "production_mutation": False,
                "human_review_required": True,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }
        selected = eligible_assessments[0] if eligible_assessments else assessments[0]
        selected_candidate = next(
            item
            for item in candidates
            if str(item.get("candidate_id") or item.get("plan_id") or "candidate")
            == selected.candidate_id
        )
        selected_plan = dict(selected_candidate.get("plan") or selected_candidate)
        length = selected.length_profile
        route = route_initial_refactor(
            objective=objective,
            task_count=int(length.get("task_count") or 0),
            distinct_file_count=int(length.get("distinct_file_count") or 0),
            dependency_edge_count=int(length.get("dependency_edge_count") or 0),
            sequential_depth=int(length.get("sequential_depth_estimate") or 0),
            cross_domain_count=len(set(selected_plan.get("domains") or [])),
            large_task_count=int(length.get("large_task_count") or 0),
        )
        provenance = {
            str(item.get("candidate_id") or item.get("plan_id") or "candidate"): {
                "arm_family": item.get("arm_family") or item.get("method") or "UNKNOWN",
                "provenance": dict(item.get("provenance") or {}),
                "token_usage": dict(item.get("token_usage") or {}),
                "prompt_digest": item.get("prompt_digest") or "",
                "response_digest": item.get("response_digest")
                or _digest(item.get("plan") or item),
            }
            for item in candidates
        }
        result = {
            "ok": True,
            "version": ARENA_ARCHITECT_CONNECTOR_VERSION,
            "objective": objective,
            "required_capabilities": list(required_capabilities),
            "selected_candidate_id": selected.candidate_id,
            "selected_plan": selected_plan,
            "selected_provenance": provenance[selected.candidate_id],
            "selected_assessment": selected.to_dict(),
            "assessments": [item.to_dict() for item in assessments],
            "candidate_provenance": provenance,
            "cognitive_labor_route": route.to_dict(),
            "control_profile": profile.to_dict(),
            "selection_digest": _digest(
                {
                    "objective": objective,
                    "selected": selected.to_dict(),
                    "candidates": [item.to_dict() for item in assessments],
                    "provenance": provenance,
                    "control": profile.to_dict(),
                }
            ),
            "selection_method": "CONTROLLED_DETERMINISTIC_COUNCIL_PROFILE_RUBRIC",
            "actual_model_calls": 0,
            "bilateral_gate_required": bilateral_contract is not None,
            "proposal_only": True,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        with self._lock:
            if record:
                self._record("architect_plan_selected", result)
            if profile.record_outputs:
                vault_run = str(
                    run_id or f"ARCH-{time.time_ns()}-{result['selection_digest'][:8]}"
                )
                run = self.output_vault.start_run(
                    run_id=vault_run,
                    objective=objective,
                    surface=profile.surface,
                    control_profile=profile.to_dict(),
                    metadata={
                        "connector_version": ARENA_ARCHITECT_CONNECTOR_VERSION,
                        "benchmark": benchmark,
                    },
                )
                vault_record = self.output_vault.record_plan_candidates(
                    run_id=vault_run,
                    objective=objective,
                    candidates=candidates,
                    comparison=result,
                )
                result["output_vault"] = {
                    "enabled": True,
                    "run_id": vault_run,
                    "root": profile.output_root,
                    "run_path": run.get("relative_path"),
                    "selection_artifact": vault_record.get("selection_artifact"),
                    "comparison_digest": vault_record.get("comparison_digest"),
                    "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
                }
            else:
                result["output_vault"] = {"enabled": False}
        return result

    def _prepare_selected_plan(
        self,
        *,
        objective: str,
        selected_plan: Mapping[str, Any],
        profile: ArchitectControlProfile,
        target_file: str | None = None,
        target_symbol: str | None = None,
        bilateral_contract: BilateralPlanningContract | Mapping[str, Any] | None = None,
        bilateral_gate: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        from aura_architect_loop import ArchitectFusionLoop

        tasks = [dict(item) for item in list(selected_plan.get("act_tasks") or [])]
        if not tasks:
            raise ValueError("selected plan has no Act Capsules")
        requested_projection = [_task_projection(task) for task in tasks]
        bilateral_proof_plan = {
            key: selected_plan.get(key)
            for key in (
                "positive_requirement_coverage",
                "negative_requirement_coverage",
                "guardrail_coverage",
                "guardrail_verifiers",
                "verifier_receipts",
                "assumption_register",
                "plan_revision_policy",
                "plan_revision",
            )
        }
        prepared = ArchitectFusionLoop(repo_root=self.repo_root).prepare(
            objective,
            architecture_decision=str(
                selected_plan.get("architecture_decision") or "Bounded Architect plan."
            ),
            act_tasks=tasks,
            target_file=target_file or selected_plan.get("target_file"),
            target_symbol=target_symbol or selected_plan.get("target_symbol"),
            acceptance_criteria=list(selected_plan.get("acceptance_criteria") or []),
            rollback_conditions=list(selected_plan.get("rollback_conditions") or []),
            risk_map=list(selected_plan.get("risk_map") or []),
            constraints=[
                *list(selected_plan.get("constraints") or []),
                f"council_mode={profile.council_mode}",
                f"council_call_budget={profile.council_call_budget}",
                f"surgeon_mode={profile.surgeon_mode}",
                "full_generated_outputs_recorded_locally",
            ],
            bilateral_contract=bilateral_contract,
            bilateral_plan_gate=bilateral_gate,
            bilateral_proof_plan=bilateral_proof_plan,
        )
        actual_projection = _prepared_projection(prepared)
        if requested_projection != actual_projection:
            raise ValueError("prepared Act Capsules do not match the frozen selected plan")

        dependency_map = {
            str(task.get("task_id") or task.get("id") or ""): [
                str(item) for item in list(task.get("depends_on") or [])
            ]
            for task in tasks
        }
        for capsule in prepared.arena.agent_capsules:
            capsule["depends_on"] = dependency_map.get(
                str(capsule.get("task_id") or ""),
                [],
            )

        findings = [item.to_dict() for item in prepared.shadow_report.findings]
        routes = [dict(item) for item in prepared.arena.routing_decisions]
        blockers = [item for item in findings if item.get("severity") == "blocker"]
        warnings = [item for item in findings if item.get("severity") != "blocker"]
        builder_authorized = bool(routes) and all(
            item.get("route") == "BUILDER_PATCH" for item in routes
        )
        executable = not blockers and builder_authorized

        sessions = getattr(self.bridge, "_sessions", None)
        if executable:
            if not isinstance(sessions, dict):
                raise ValueError("Arena bridge cannot register a prepared selected-plan session")
            phase_hash = prepared.plan.phase_hash
            sessions[phase_hash] = {
                "prepared": prepared,
                "arena": prepared.arena,
                "grounding": [item.to_dict() for item in prepared.grounding],
                "verification": None,
                "stage_results": [],
                "hotswap_capsule": None,
                "selected_plan_digest": _digest(selected_plan),
                "dependency_map": dependency_map,
                "unified_execution_bindings": {},
            }
        phase_hash = prepared.plan.phase_hash
        act_capsules = [dict(item) for item in prepared.arena.agent_capsules]
        return {
            "ok": executable,
            "plan_phase_hash": phase_hash,
            "selected_plan_digest": _digest(selected_plan),
            "requested_act_projection_digest": _digest(requested_projection),
            "prepared_act_projection_digest": _digest(actual_projection),
            "act_capsules": act_capsules,
            "dependency_map": dependency_map,
            "grounding_evidence": [item.to_dict() for item in prepared.grounding],
            "shadow_findings": findings,
            "shadow_gate": prepared.shadow_report.gate,
            "routing_decisions": routes,
            "liquid_arena_lease_count": len(prepared.arena.agent_leases),
            "builder_patch_authorized": builder_authorized,
            "ready_for_incubator": prepared.arena.ready_for_incubator,
            "blockers": blockers,
            "warnings": warnings,
            "intensity": prepared.intensity,
            "proposal_only": True,
            "human_review_required": True,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "bilateral_contract": (
                bilateral_contract.to_dict()
                if isinstance(bilateral_contract, BilateralPlanningContract)
                else dict(bilateral_contract or {})
            ),
            "bilateral_plan_gate": dict(bilateral_gate or {}),
            "bilateral_proof_plan": bilateral_proof_plan,
        }

    def prepare_refactor(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        target_file: str | None = None,
        target_symbol: str | None = None,
        control: Mapping[str, Any] | ArchitectControlProfile | None = None,
        surface: str = "native",
        run_id: str = "",
        benchmark: bool = False,
        bilateral_contract: BilateralPlanningContract | Mapping[str, Any] | None = None,
        confirmation_session_id: str = "",
        observed_repository_head: str = "",
        observed_source_tree_digest: str = "",
        observed_at: float | None = None,
    ) -> dict[str, Any]:
        resolved_contract = self._resolve_bilateral_contract(
            bilateral_contract, confirmation_session_id
        )
        comparison = self.compare_plans(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            control=control,
            surface=surface,
            run_id=run_id,
            benchmark=benchmark,
            bilateral_contract=resolved_contract,
            observed_repository_head=observed_repository_head,
            observed_source_tree_digest=observed_source_tree_digest,
            observed_at=observed_at,
        )
        if not comparison.get("ok"):
            return comparison
        profile = normalize_control_profile(
            comparison.get("control_profile"),
            surface=surface,
            benchmark=benchmark,
        )
        prepared = self._prepare_selected_plan(
            objective=objective,
            selected_plan=dict(comparison["selected_plan"]),
            profile=profile,
            target_file=target_file,
            target_symbol=target_symbol,
            bilateral_contract=resolved_contract,
            bilateral_gate=dict(comparison["selected_assessment"]).get("bilateral_gate"),
        )
        result = {
            "ok": bool(prepared.get("ok")),
            "comparison": comparison,
            "arena_preparation": prepared,
            "control_profile": profile.to_dict(),
            "proposal_only": True,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        self._record("architect_arena_prepared", result)
        return result

    def open_surgeon_session(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        provider: str = "external",
        model: str = "",
        control: Mapping[str, Any] | ArchitectControlProfile | None = None,
        surface: str = "native",
        run_id: str = "",
        bilateral_contract: BilateralPlanningContract | Mapping[str, Any] | None = None,
        confirmation_session_id: str = "",
        observed_repository_head: str = "",
        observed_source_tree_digest: str = "",
        observed_at: float | None = None,
    ) -> dict[str, Any]:
        prepared = self.prepare_refactor(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            control=control,
            surface=surface,
            run_id=run_id,
            bilateral_contract=bilateral_contract,
            confirmation_session_id=confirmation_session_id,
            observed_repository_head=observed_repository_head,
            observed_source_tree_digest=observed_source_tree_digest,
            observed_at=observed_at,
        )
        if not prepared.get("ok"):
            return prepared
        profile = normalize_control_profile(prepared["control_profile"], surface=surface)
        manager = ControlledRefactorSessionManager(
            self.repo_root,
            bridge=self.bridge,
            control=profile,
            surface=profile.surface,
            output_vault=self.output_vault,
        )
        architect_run = str(
            run_id
            or dict(prepared.get("comparison", {})).get("output_vault", {}).get("run_id")
            or ""
        )
        opened = manager.open_prepared_session(
            prepared_arena=dict(prepared["arena_preparation"]),
            objective=objective,
            provider=provider,
            model=model,
            run_id=architect_run,
            metadata={
                "selected_candidate_id": prepared["comparison"]["selected_candidate_id"],
                "selection_digest": prepared["comparison"]["selection_digest"],
            },
        )
        session_id = str(dict(opened.get("session") or {}).get("session_id") or "")
        if session_id:
            with self._lock:
                self._surgeon_sessions[session_id] = manager
        opened["architect_preparation"] = prepared
        return opened

    def surgeon_next(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return self._session_manager(session_id).next_turn(session_id)

    def surgeon_submit(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            return self._session_manager(session_id).submit_response(
                session_id=session_id,
                turn_id=turn_id,
                response=response,
                provider_usage=dict(provider_usage or {}),
            )

    def surgeon_status(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return self._session_manager(session_id).get_session(session_id)

    def surgeon_replan(self, **kwargs: Any) -> dict[str, Any]:
        session_id = str(kwargs.get("session_id") or "")
        with self._lock:
            return self._session_manager(session_id).apply_council_replan(**kwargs)

    def list_refactor_outputs(self, *, limit: int = 50) -> dict[str, Any]:
        with self._lock:
            return self.output_vault.list_runs(limit=limit)

    def load_refactor_output(
        self,
        relative_path: str,
        *,
        max_bytes: int = 2_000_000,
    ) -> dict[str, Any]:
        with self._lock:
            return self.output_vault.load_artifact(relative_path, max_bytes=max_bytes)

    def route_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return self.model_gateway.plan_best(**kwargs)

    def execute_native_model(self, **kwargs: Any) -> dict[str, Any]:
        return self.model_gateway.execute_best(**kwargs)

    def _session_manager(self, session_id: str) -> ControlledRefactorSessionManager:
        manager = self._surgeon_sessions.get(str(session_id))
        if manager is None:
            raise ValueError("surgeon session not found")
        return manager

    def _record(self, event_type: str, payload: Mapping[str, Any]) -> None:
        comparison = dict(payload.get("comparison") or {})
        public = {
            "version": payload.get("version") or comparison.get("version"),
            "selected_candidate_id": payload.get("selected_candidate_id")
            or comparison.get("selected_candidate_id"),
            "selected_assessment": payload.get("selected_assessment")
            or comparison.get("selected_assessment"),
            "selection_digest": payload.get("selection_digest")
            or comparison.get("selection_digest"),
            "control_profile_digest": dict(
                payload.get("control_profile") or comparison.get("control_profile") or {}
            ).get("control_digest"),
            "proposal_only": True,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        row = {
            "event_type": event_type,
            "recorded_at": time.time(),
            "payload_digest": _digest(public),
            "payload": public,
            "redaction": "FULL_PLANS_AUTHORIZATIONS_AND_PRIVATE_EVIDENCE_OMITTED",
        }
        try:
            self.record_path.parent.mkdir(parents=True, exist_ok=True)
            with self.record_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        except OSError:
            return


__all__ = [
    "ARENA_ARCHITECT_CONNECTOR_VERSION",
    "AuraArenaArchitectConnector",
    "PlanAssessment",
]
