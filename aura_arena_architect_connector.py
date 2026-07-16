"""Shared proposal-only Architect connector for Aura's Arena surfaces.

Native Aura, Coding Arena, Human Agent Arena, MCP clients, HTTP/container clients,
and third-party coding agents enter through this same bounded service.  Candidate
plans are frozen and recorded before selection; generated code is executed through
controlled slice-leased Surgeon sessions; all consequential promotion remains under
human authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

from aura_architect_control import (
    ArchitectControlProfile,
    control_capabilities,
    normalize_control_profile,
)
from aura_architect_council_v2 import profile_refactor_length
from aura_architect_council_v3 import select_critic_lanes
from aura_cognitive_labor_router import route_initial_refactor
from aura_controlled_refactor_session import ControlledRefactorSessionManager
from aura_native_model_gateway import AuraNativeModelGateway
from aura_refactor_output_vault import RefactorOutputVault

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
_ALL_CRITIC_LANES = ("scope", "tests", "sequence", "continuity", "rollback", "cost")


def _digest(value: Any, *, size: int = 16) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=size).hexdigest()


def _tokens(value: Any) -> int:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return (len(text) + 3) // 4


def _candidate(candidate: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    candidate_id = str(candidate.get("candidate_id") or candidate.get("plan_id") or "candidate")
    plan = dict(candidate.get("plan") or candidate)
    if len(json.dumps(plan, default=str).encode("utf-8")) > MAX_PLAN_BYTES:
        raise ValueError("candidate plan exceeds the bounded plan size")
    if len(list(plan.get("act_tasks") or [])) > MAX_TASKS:
        raise ValueError(f"candidate plan exceeds {MAX_TASKS} Act Capsules")
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

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["selected_critic_lanes"] = list(self.selected_critic_lanes)
        value["reasons"] = list(self.reasons)
        return value


class AuraArenaArchitectConnector:
    """One governed Architect/Surgeon service for every Aura access surface."""

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
        self.record_path = (
            Path(record_path)
            if record_path
            else self.repo_root / "Aura_Memory" / "benchmarks" / "architect_plan_selections.jsonl"
        )
        self.output_vault = output_vault or RefactorOutputVault(self.repo_root)
        self._surgeon_sessions: dict[str, ControlledRefactorSessionManager] = {}

    @property
    def bridge(self) -> Any:
        if self._bridge is None:
            factory = self._bridge_factory
            if factory is None:
                from aura_agent_arena_bridge import AuraAgentArenaBridge

                factory = AuraAgentArenaBridge
            self._bridge = factory(repo_root=self.repo_root)
        return self._bridge

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
    ) -> PlanAssessment:
        profile = normalize_control_profile(control, surface=surface)
        candidate_id, plan = _candidate(candidate)
        tasks = [dict(item) for item in list(plan.get("act_tasks") or []) if isinstance(item, Mapping)]
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
        return PlanAssessment(
            candidate_id,
            round(min(1.0, score), 4),
            lanes,
            length.to_dict(),
            round(coverage, 4),
            round(exact, 4),
            round(governance, 4),
            round(testability, 4),
            reuse,
            tuple(reasons),
            _digest(plan),
            _tokens(plan),
            profile.council_mode,
            len(lanes),
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
    ) -> dict[str, Any]:
        objective = str(objective or "").strip()
        if not objective:
            raise ValueError("objective is required")
        if not candidates:
            raise ValueError("at least one candidate plan is required")
        if len(candidates) > MAX_CANDIDATES:
            raise ValueError(f"at most {MAX_CANDIDATES} candidate plans are allowed")
        ids = [str(item.get("candidate_id") or item.get("plan_id") or "candidate") for item in candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate ids must be unique")
        profile = normalize_control_profile(control, surface=surface, benchmark=benchmark)
        assessments = [
            self.assess_plan(
                item,
                required_capabilities=required_capabilities,
                control=profile,
                surface=profile.surface,
            )
            for item in candidates
        ]
        assessments.sort(key=lambda item: (-item.score, item.token_proxy, item.candidate_id))
        selected = assessments[0]
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
        candidate_provenance = {
            str(item.get("candidate_id") or item.get("plan_id") or "candidate"): {
                "arm_family": item.get("arm_family") or item.get("method") or "UNKNOWN",
                "provenance": dict(item.get("provenance") or {}),
                "token_usage": dict(item.get("token_usage") or {}),
                "prompt_digest": item.get("prompt_digest") or "",
                "response_digest": item.get("response_digest") or _digest(item.get("plan") or item),
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
            "selected_provenance": candidate_provenance[selected.candidate_id],
            "selected_assessment": selected.to_dict(),
            "assessments": [item.to_dict() for item in assessments],
            "candidate_provenance": candidate_provenance,
            "cognitive_labor_route": route.to_dict(),
            "control_profile": profile.to_dict(),
            "selection_digest": _digest(
                {
                    "objective": objective,
                    "selected": selected.to_dict(),
                    "candidates": [item.to_dict() for item in assessments],
                    "provenance": candidate_provenance,
                    "control": profile.to_dict(),
                }
            ),
            "selection_method": "CONTROLLED_DETERMINISTIC_COUNCIL_PROFILE_RUBRIC",
            "proposal_only": True,
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        if record:
            self._record("architect_plan_selected", result)
        if profile.record_outputs:
            vault_run = str(run_id or f"ARCH-{time.time_ns()}-{result['selection_digest'][:8]}")
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
                "visibility": "LOCAL_PRIVATE_FULL_OUTPUT",
            }
        else:
            result["output_vault"] = {"enabled": False}
        return result

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
    ) -> dict[str, Any]:
        comparison = self.compare_plans(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            control=control,
            surface=surface,
            run_id=run_id,
            benchmark=benchmark,
        )
        selected = dict(comparison["selected_plan"])
        profile = normalize_control_profile(
            comparison.get("control_profile"), surface=surface, benchmark=benchmark
        )
        prepared = self.bridge.aura_prepare_arena(
            objective=objective,
            target_file=target_file or selected.get("target_file"),
            target_symbol=target_symbol or selected.get("target_symbol"),
            acceptance_criteria=list(selected.get("acceptance_criteria") or []),
            risk_map=list(selected.get("risk_map") or []),
            constraints=[
                *list(selected.get("constraints") or []),
                f"council_mode={profile.council_mode}",
                f"council_call_budget={profile.council_call_budget}",
                f"surgeon_mode={profile.surgeon_mode}",
                "full_generated_outputs_recorded_locally",
            ],
        )
        result = {
            "ok": bool(prepared.get("ok", True)),
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
    ) -> dict[str, Any]:
        prepared = self.prepare_refactor(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            control=control,
            surface=surface,
            run_id=run_id,
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
        vault_run = str(
            run_id
            or dict(prepared.get("comparison", {})).get("output_vault", {}).get("run_id")
            or ""
        )
        opened = manager.open_prepared_session(
            prepared_arena=dict(prepared["arena_preparation"]),
            objective=objective,
            provider=provider,
            model=model,
            run_id=vault_run,
            metadata={
                "selected_candidate_id": prepared["comparison"]["selected_candidate_id"],
                "selection_digest": prepared["comparison"]["selection_digest"],
            },
        )
        session_id = str(dict(opened.get("session") or {}).get("session_id") or "")
        if session_id:
            self._surgeon_sessions[session_id] = manager
        opened["architect_preparation"] = prepared
        return opened

    def surgeon_next(self, session_id: str) -> dict[str, Any]:
        return self._session_manager(session_id).next_turn(session_id)

    def surgeon_submit(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._session_manager(session_id).submit_response(
            session_id=session_id,
            turn_id=turn_id,
            response=response,
            provider_usage=dict(provider_usage or {}),
        )

    def surgeon_status(self, session_id: str) -> dict[str, Any]:
        return self._session_manager(session_id).get_session(session_id)

    def surgeon_replan(self, **kwargs: Any) -> dict[str, Any]:
        session_id = str(kwargs.get("session_id") or "")
        return self._session_manager(session_id).apply_council_replan(**kwargs)

    def list_refactor_outputs(self, *, limit: int = 50) -> dict[str, Any]:
        return self.output_vault.list_runs(limit=limit)

    def load_refactor_output(self, relative_path: str, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
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
            "redaction": "FULL_PLANS_AUTHORIZATIONS_GENERATED_CODE_AND_PRIVATE_EVIDENCE_OMITTED",
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
