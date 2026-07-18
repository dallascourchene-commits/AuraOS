"""Temporal-persistence extension for Aura's Agent Arena Bridge."""
from __future__ import annotations

from typing import Any, Mapping

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
from aura_coding_waboose import CodingWaboose

AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION = "AURA_AGENT_ARENA_PERSISTENCE_BRIDGE_V1"


class PersistentAuraAgentArenaBridge(AuraAgentArenaBridge):
    """Agent Bridge with checkpoint, restoration, fork, and handoff tools."""

    def __init__(self, *, repo_root: str | None = None) -> None:
        super().__init__(repo_root=repo_root)
        self.persistence = ArenaPersistenceCoordinator(str(self.repo_root))
        self.coding_waboose = CodingWaboose(self.repo_root)

    def aura_checkpoint_session(
        self,
        *,
        plan_phase_hash: str,
        repo_head: str,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
    ) -> dict[str, Any]:
        return self.persistence.checkpoint_agent_bridge(
            self,
            plan_phase_hash=plan_phase_hash,
            repo_head=repo_head,
            parent_checkpoint_id=parent_checkpoint_id,
            branch_name=branch_name,
        )

    def aura_list_checkpoints(
        self,
        *,
        session_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        return self.persistence.list_checkpoints(
            arena_id="agent_bridge_arena",
            session_id=session_id,
            limit=limit,
        )

    def aura_restore_checkpoint(
        self,
        *,
        checkpoint_id: str,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
        remaining_context_tokens: int = 0,
        surgeon_context_limit: int = 0,
    ) -> dict[str, Any]:
        return self.persistence.restoration_packet(
            checkpoint_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
            remaining_context_tokens=remaining_context_tokens,
            surgeon_context_limit=surgeon_context_limit,
        )

    def aura_fork_checkpoint(
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
        result["bridge_version"] = AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION
        return result

    def aura_handoff_checkpoint(
        self,
        *,
        checkpoint_id: str,
        target_arena_id: str,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.persistence.handoff_packet(
            checkpoint_id,
            target_arena_id=target_arena_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
        )

    def aura_waboose_prepare(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self.coding_waboose.prepare(request)

    def aura_waboose_scan(self, review_id: str) -> dict[str, Any]:
        return self.coding_waboose.scan(review_id)

    def aura_waboose_agent_packet(
        self,
        review_id: str,
        *,
        include_source: bool = False,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        return self.coding_waboose.agent_packet(
            review_id,
            include_source=include_source,
            max_files=max_files,
            max_lines_per_file=max_lines_per_file,
        )

    def aura_waboose_submit_findings(
        self,
        review_id: str,
        findings: list[Mapping[str, Any]],
        *,
        agent_name: str = "external_agent",
    ) -> dict[str, Any]:
        return self.coding_waboose.submit_findings(
            review_id,
            findings,
            agent_name=agent_name,
        )

    def aura_waboose_finalize(self, review_id: str) -> dict[str, Any]:
        return self.coding_waboose.finalize(review_id)

    def aura_waboose_status(self, review_id: str) -> dict[str, Any]:
        return self.coding_waboose.status(review_id)

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        return [
            *AuraAgentArenaBridge.list_tools(),
            {
                "name": "aura_checkpoint_session",
                "description": "Persist the prepared Agent Bridge session as a verifier-bound checkpoint.",
                "required_inputs": ["plan_phase_hash", "repo_head"],
            },
            {
                "name": "aura_list_checkpoints",
                "description": "List Agent Bridge checkpoints without returning checkpoint payloads.",
                "required_inputs": [],
            },
            {
                "name": "aura_restore_checkpoint",
                "description": "Return a reviewable restoration assessment; never applies state automatically.",
                "required_inputs": ["checkpoint_id", "current_repo_head"],
            },
            {
                "name": "aura_fork_checkpoint",
                "description": "Create a named child checkpoint for a what-if branch.",
                "required_inputs": ["checkpoint_id", "branch_name"],
            },
            {
                "name": "aura_handoff_checkpoint",
                "description": "Create a payload-free digital baton for another Aura arena.",
                "required_inputs": ["checkpoint_id", "target_arena_id", "current_repo_head"],
            },
            {
                "name": "aura_waboose_prepare",
                "description": "Compile an evidence-bound Coding Waboose diagnostic contract.",
                "required_inputs": ["objective"],
            },
            {
                "name": "aura_waboose_scan",
                "description": "Run deterministic review scans for a prepared Coding Waboose run.",
                "required_inputs": ["review_id"],
            },
            {
                "name": "aura_waboose_agent_packet",
                "description": "Return a bounded impact packet for a replaceable coding agent through Coding Waboose.",
                "required_inputs": ["review_id"],
            },
            {
                "name": "aura_waboose_submit_findings",
                "description": "Submit structured agent findings for exact-source corroboration.",
                "required_inputs": ["review_id", "findings"],
            },
            {
                "name": "aura_waboose_finalize",
                "description": "Rank review findings and compile Forge repair requests.",
                "required_inputs": ["review_id"],
            },
            {
                "name": "aura_waboose_status",
                "description": "Return bounded in-process review status.",
                "required_inputs": ["review_id"],
            },
        ]


def bridge_persistence_status() -> dict[str, Any]:
    return {
        "ok": True,
        "version": AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION,
        "automatic_resume": False,
        "automatic_hotswap": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION",
    "PersistentAuraAgentArenaBridge",
    "bridge_persistence_status",
]
