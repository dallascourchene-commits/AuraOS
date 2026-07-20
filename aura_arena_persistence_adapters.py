"""Arena-specific projections into Aura's canonical temporal persistence engine.

The adapters preserve each arena's existing authority model. They checkpoint
reviewable state, emit restoration/handoff packets, and never mutate live arena
objects during restore assessment.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aura_refactor_state_identity import digest, normalize
from aura_temporal_persistence import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    TemporalCheckpointRegistry,
    checkpoint_refactor_state,
)

ARENA_PERSISTENCE_ADAPTER_VERSION = "AURA_ARENA_PERSISTENCE_ADAPTER_V1"
SUPPORTED_ARENAS = frozenset(
    {
        "coding_arena",
        "coding_workbench",
        "human_agent_arena",
        "agent_bridge_arena",
        "construction_arena",
        "spatial_arena",
    }
)


def _mapping_state(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must return a mapping")
    normalized = normalize(dict(value))
    if not isinstance(normalized, dict):
        raise ValueError(f"{name} did not normalize to an object")
    return normalized


def _session_identifier(value: Any, prefix: str) -> str:
    text = str(value or "").strip()
    if text and len(text) <= 128 and text[0].isalnum() and all(ch.isalnum() or ch in "_.:-" for ch in text):
        return text
    return f"{prefix}-{digest(text or prefix, size=12)}"


def _checkpoint_invariants(state: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    invariants: dict[str, Any] = {
        "patch_authority": state.get("patch_authority", PATCH_AUTHORITY),
        "vsa_patch_authority": state.get("vsa_patch_authority", VSA_PATCH_AUTHORITY),
    }
    for key in keys:
        if key in state:
            invariants[key] = state[key]
    return invariants


class ArenaPersistenceCoordinator:
    """Canonical persistence facade shared by Coding, Human, Bridge, Construction, and Spatial."""

    def __init__(
        self,
        repo_root: str = ".",
        *,
        memory_root: str = "Aura_Memory/checkpoints",
    ) -> None:
        self.registry = TemporalCheckpointRegistry(
            repo_root,
            memory_root=memory_root,
        )

    def checkpoint_mapping(
        self,
        *,
        arena_id: str,
        session_id: str,
        repo_head: str,
        state: Mapping[str, Any],
        invariant_values: Mapping[str, Any] | None = None,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        source_kind: str = "ARENA_STATE",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        if arena_id not in SUPPORTED_ARENAS:
            raise ValueError(f"unsupported arena_id: {arena_id}")
        result = self.registry.write_checkpoint(
            arena_id=arena_id,
            session_id=_session_identifier(session_id, "SESSION"),
            repo_head=repo_head,
            payload=state,
            invariant_values=invariant_values,
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
            source_kind=source_kind,
            created_at=created_at,
        )
        result["adapter_version"] = ARENA_PERSISTENCE_ADAPTER_VERSION
        return result

    def checkpoint_coding_workbench(
        self,
        session: Any,
        *,
        repo_head: str,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        getter = getattr(session, "get_state_without_routing", None)
        if not callable(getter):
            getter = getattr(session, "get_state", None)
        if not callable(getter):
            raise ValueError("coding session does not expose a state projection")
        state = _mapping_state(getter(), "coding session state")
        state["arena_persistence"] = {
            "checkpointed": True,
            "live_session_mutated": False,
            "automatic_resume": False,
        }
        return self.checkpoint_mapping(
            arena_id="coding_workbench",
            session_id=_session_identifier(
                state.get("session_id") or getattr(session, "session_id", ""),
                "CWFST",
            ),
            repo_head=repo_head,
            state=state,
            invariant_values=_checkpoint_invariants(
                state,
                "state",
                "objective",
                "evidence",
                "gate",
            ),
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
            source_kind="CODING_WORKBENCH_WFST",
            created_at=created_at,
        )

    def checkpoint_human_agent(
        self,
        workflow: Any,
        *,
        repo_head: str,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        getter = getattr(workflow, "get_state", None)
        if not callable(getter):
            raise ValueError("human-agent workflow does not expose get_state")
        state = _mapping_state(getter(), "human-agent workflow state")
        state["arena_persistence"] = {
            "checkpointed": True,
            "live_workflow_mutated": False,
            "automatic_resume": False,
        }
        return self.checkpoint_mapping(
            arena_id="human_agent_arena",
            session_id=_session_identifier(
                state.get("workflow_id") or state.get("session_id") or getattr(workflow, "workflow_id", ""),
                "HUMAN",
            ),
            repo_head=repo_head,
            state=state,
            invariant_values=_checkpoint_invariants(
                state,
                "current_phase",
                "objective",
                "evidence",
                "routing",
            ),
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
            source_kind="HUMAN_AGENT_WFST",
            created_at=created_at,
        )

    def checkpoint_agent_bridge(
        self,
        bridge: Any,
        *,
        plan_phase_hash: str,
        repo_head: str,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        require = getattr(bridge, "_require_session", None)
        if not callable(require):
            raise ValueError("agent bridge does not expose a prepared-session lookup")
        session = require(plan_phase_hash)
        prepared = session.get("prepared")
        plan = getattr(prepared, "plan", None)
        arena = session.get("arena")
        act_capsules = []
        for item in list(getattr(plan, "act_capsules", []) or []):
            act_capsules.append(
                {
                    "task_id": str(getattr(item, "task_id", "") or ""),
                    "target_file": str(getattr(item, "target_file", "") or ""),
                    "target_symbol": str(getattr(item, "target_symbol", "") or ""),
                    "role": str(getattr(item, "role", "") or ""),
                    "size": str(getattr(item, "size", "") or ""),
                }
            )
        stage_results = []
        for item in list(session.get("stage_results", []) or []):
            patch = getattr(item, "patch", None)
            stage_results.append(
                {
                    "ok": bool(getattr(item, "ok", False)),
                    "patch_id": str(getattr(patch, "patch_id", "") or ""),
                    "task_id": str(getattr(patch, "task_id", "") or ""),
                    "affected_files": list(getattr(patch, "affected_files", []) or []),
                    "status": str(getattr(patch, "status", "") or ""),
                }
            )
        verification = session.get("verification")
        verification_summary = {
            "present": verification is not None,
            "ok": bool(getattr(verification, "ok", False)) if verification is not None else False,
            "stage": str(getattr(verification, "stage", "") or "") if verification is not None else "",
            "hotswap_ready": bool(getattr(verification, "hotswap_ready", False)) if verification is not None else False,
            "failure_count": len(list(getattr(verification, "failures", []) or [])) if verification is not None else 0,
        }
        state = {
            "version": ARENA_PERSISTENCE_ADAPTER_VERSION,
            "plan_phase_hash": str(plan_phase_hash),
            "act_capsules": act_capsules,
            "affected_files": list(getattr(arena, "affected_files", []) or []),
            "routing_decisions": normalize(list(getattr(arena, "routing_decisions", []) or [])),
            "stage_results": stage_results,
            "verification": verification_summary,
            "hotswap_capsule_present": bool(session.get("hotswap_capsule")),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_resume": False,
            "automatic_hotswap": False,
        }
        return self.checkpoint_mapping(
            arena_id="agent_bridge_arena",
            session_id=_session_identifier(plan_phase_hash, "BRIDGE"),
            repo_head=repo_head,
            state=state,
            invariant_values=_checkpoint_invariants(
                state,
                "plan_phase_hash",
                "act_capsules",
                "affected_files",
                "verification",
            ),
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
            source_kind="AGENT_ARENA_BRIDGE",
            created_at=created_at,
        )

    def checkpoint_construction(
        self,
        state: Any,
        *,
        repo_head: str,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        from aura_construction_state import ConstructionProjectState

        if type(state) is not ConstructionProjectState:
            raise ValueError("state must be an exact ConstructionProjectState")
        payload = state.to_dict()
        payload["arena_persistence"] = {
            "checkpointed": True,
            "physical_work_authorized": False,
            "payment_released": False,
            "access_control_authorized": False,
            "professional_certification_authorized": False,
        }
        return self.checkpoint_mapping(
            arena_id="construction_arena",
            session_id=_session_identifier(state.project_id, "CONSTRUCTION"),
            repo_head=repo_head,
            state=payload,
            invariant_values={
                "state_digest": state.state_digest,
                "final_chain_digest": state.final_chain_digest,
                "project_id": state.project_id,
                "ledger_id": state.ledger_id,
                "proposal_only": state.proposal_only,
                "patch_authority": state.patch_authority,
                "vsa_patch_authority": state.vsa_patch_authority,
            },
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
            source_kind="CONSTRUCTION_PROJECT_STATE",
            created_at=created_at,
        )

    def checkpoint_spatial(
        self,
        state: Mapping[str, Any],
        *,
        repo_head: str,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        payload = _mapping_state(state, "spatial state")
        if payload.get("raw_domain_state_included") is not False:
            raise ValueError("spatial checkpoints cannot include raw domain state")
        if payload.get("raw_sensor_data_retained") is not False:
            raise ValueError("spatial checkpoints cannot retain raw sensor data")
        if payload.get("restore_mode") != "ASSESSMENT_ONLY":
            raise ValueError("spatial checkpoints must remain assessment-only")
        if payload.get("automatic_resume") is not False:
            raise ValueError("spatial checkpoints cannot resume automatically")
        return self.checkpoint_mapping(
            arena_id="spatial_arena",
            session_id=_session_identifier(payload.get("run_id"), "SPATIAL"),
            repo_head=repo_head,
            state=payload,
            invariant_values=_checkpoint_invariants(
                payload,
                "run_id",
                "phase",
                "purpose_digest",
                "domain_owner",
                "domain_state_digest",
                "scene_digest",
                "render_plan_digest",
                "raw_sensor_data_retained",
                "restore_mode",
            ),
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
            source_kind="SPATIAL_ARENA_PROJECTION",
            created_at=created_at,
        )

    def checkpoint_refactor(
        self,
        *,
        ledger: Any,
        sidecar: Mapping[str, Any],
        repo_head: str,
        arena_id: str = "coding_arena",
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        if arena_id not in {"coding_arena", "agent_bridge_arena"}:
            raise ValueError("refactor ledgers belong to Coding or Agent Bridge arenas")
        result = checkpoint_refactor_state(
            self.registry,
            ledger=ledger,
            sidecar=sidecar,
            repo_head=repo_head,
            arena_id=arena_id,
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
            created_at=created_at,
        )
        result["adapter_version"] = ARENA_PERSISTENCE_ADAPTER_VERSION
        return result

    def assess(
        self,
        checkpoint_id: str,
        *,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
        remaining_context_tokens: int = 0,
        surgeon_context_limit: int = 0,
    ) -> dict[str, Any]:
        return self.registry.assess_restore(
            checkpoint_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
            remaining_context_tokens=remaining_context_tokens,
            surgeon_context_limit=surgeon_context_limit,
        ).to_dict()

    def restoration_packet(
        self,
        checkpoint_id: str,
        *,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
        remaining_context_tokens: int = 0,
        surgeon_context_limit: int = 0,
    ) -> dict[str, Any]:
        result = self.registry.restoration_packet(
            checkpoint_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
            remaining_context_tokens=remaining_context_tokens,
            surgeon_context_limit=surgeon_context_limit,
        )
        result["adapter_version"] = ARENA_PERSISTENCE_ADAPTER_VERSION
        return result

    def handoff_packet(
        self,
        checkpoint_id: str,
        *,
        target_arena_id: str,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if target_arena_id not in SUPPORTED_ARENAS:
            raise ValueError(f"unsupported target arena: {target_arena_id}")
        checkpoint = self.registry.load_checkpoint(checkpoint_id)
        assessment = self.registry.assess_restore(
            checkpoint_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
        )
        return {
            "ok": True,
            "version": ARENA_PERSISTENCE_ADAPTER_VERSION,
            "checkpoint_id": checkpoint.checkpoint_id,
            "source_arena_id": checkpoint.arena_id,
            "target_arena_id": target_arena_id,
            "session_id": checkpoint.session_id,
            "payload_digest": checkpoint.payload_digest,
            "assessment": assessment.to_dict(),
            "payload_included": False,
            "digital_baton_only": True,
            "target_arena_mutated": False,
            "automatic_resume": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def list_checkpoints(
        self,
        *,
        arena_id: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return self.registry.list_checkpoints(
            arena_id=arena_id,
            session_id=session_id,
            limit=limit,
        )

    def observatory_projection(self, checkpoint_id: str) -> dict[str, Any]:
        result = self.registry.observatory_projection(checkpoint_id)
        result["adapter_version"] = ARENA_PERSISTENCE_ADAPTER_VERSION
        return result

    def verify_registry(self) -> dict[str, Any]:
        return self.registry.verify_registry()


__all__ = [
    "ARENA_PERSISTENCE_ADAPTER_VERSION",
    "SUPPORTED_ARENAS",
    "ArenaPersistenceCoordinator",
]
