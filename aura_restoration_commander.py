"""Review-gated Restoration Commander for Aura temporal checkpoints."""
from __future__ import annotations

from typing import Any, Mapping

from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY

RESTORATION_COMMANDER_VERSION = "AURA_RESTORATION_COMMANDER_V1"


class RestorationCommander:
    """Build restoration capsules without applying state or invoking a model."""

    def __init__(self, repo_root: str = ".") -> None:
        self.persistence = ArenaPersistenceCoordinator(repo_root)

    def resume(
        self,
        *,
        checkpoint_id: str,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
        remaining_context_tokens: int = 0,
        surgeon_context_limit: int = 0,
    ) -> dict[str, Any]:
        packet = self.persistence.restoration_packet(
            checkpoint_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
            remaining_context_tokens=remaining_context_tokens,
            surgeon_context_limit=surgeon_context_limit,
        )
        assessment = dict(packet.get("assessment") or {})
        status = str(assessment.get("status") or "")
        packet["restoration_commander"] = {
            "version": RESTORATION_COMMANDER_VERSION,
            "decision": status,
            "state_applied": False,
            "premium_model_invoked": False,
            "model_tokens": "NOT_MEASURED",
            "model_cost": "NOT_MEASURED",
            "minimal_replan_required": status == "RESTORATION_COUNCIL_REQUIRED",
            "mitosis_required": status == "MITOSIS_REQUIRED",
            "direct_resume_ready": status == "DIRECT_RESUME_REVIEW_REQUIRED",
            "next_gate": assessment.get("next_gate", ""),
            "human_review_required": True,
        }
        return packet

    def fork(
        self,
        *,
        checkpoint_id: str,
        branch_name: str,
        repo_head: str | None = None,
    ) -> dict[str, Any]:
        result = self.persistence.registry.fork_checkpoint(
            checkpoint_id,
            branch_name=branch_name,
            repo_head=repo_head,
        )
        result["restoration_commander_version"] = RESTORATION_COMMANDER_VERSION
        result["active_branch_switched"] = False
        result["human_review_required"] = True
        return result

    def handoff(
        self,
        *,
        checkpoint_id: str,
        target_arena_id: str,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.persistence.handoff_packet(
            checkpoint_id,
            target_arena_id=target_arena_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
        )
        result["restoration_commander_version"] = RESTORATION_COMMANDER_VERSION
        return result

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": RESTORATION_COMMANDER_VERSION,
            "state_applied": False,
            "automatic_resume": False,
            "premium_model_invoked": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


__all__ = ["RESTORATION_COMMANDER_VERSION", "RestorationCommander"]
