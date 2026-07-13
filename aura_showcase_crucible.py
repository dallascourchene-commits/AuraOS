"""Presenter-safe facade over Aura's real Arena Crucible.

This adapter exposes observable experience summaries, manual proposal cycles, pause/resume,
and proposal review data. It never fabricates experiences from prompts and never promotes an
active grammar.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aura_arena_crucible import ArenaCrucibleService
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_crucible_types import CruciblePolicy

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SHOWCASE_CRUCIBLE_VERSION = "AURA_SHOWCASE_CRUCIBLE_V1"


class LearningArenaShowcase:
    """Small synchronous control surface over the proposal-only Crucible service."""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.service = ArenaCrucibleService(self.repo_root)

    def close(self) -> None:
        self.service.close()

    def status(self, *, intake: dict[str, Any] | None = None, arena_id: str = "") -> dict[str, Any]:
        with ArenaExperienceLedger(self.repo_root) as ledger:
            ledger_status = ledger.status()
            recent = ledger.history(arena_id=str(arena_id or ""), limit=12)
        proposals = self.service.store.list_proposals(arena_id=str(arena_id or ""), limit=12)
        service_status = self.service.status()
        return {
            "ok": True,
            "version": SHOWCASE_CRUCIBLE_VERSION,
            "identity": "LEARNING_ARENA_CRUCIBLE",
            "purpose": "Apply learning only to complete, verified ArenaExperience records.",
            "intake": dict(intake or {}),
            "service": service_status,
            "ledger": ledger_status,
            "recent_experiences": [_experience_summary(item) for item in recent],
            "recent_proposals": [_proposal_summary(item) for item in proposals],
            "experience_count": int(ledger_status.get("record_count") or 0),
            "eligible_experience_count": int(ledger_status.get("v3_complete_record_count") or 0),
            "legacy_experience_count": int(ledger_status.get("legacy_record_count") or 0),
            "proposal_count": int(service_status.get("proposal_count") or 0),
            "paused": bool(service_status.get("paused")),
            "dataset_split": ["TRAIN", "VALIDATION", "SHADOW"],
            "terminal_status": "CRYSTALLIZATION_PROPOSED",
            "required_next_gate": "VERIFIER_AND_HUMAN_REVIEW",
            "binary_outcome_used": False,
            "active_grammar_mutation": False,
            "automatic_grammar_promotion": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def run_once(
        self,
        *,
        arena_id: str = "",
        policy: dict[str, Any] | None = None,
        experience_limit: int = 1000,
    ) -> dict[str, Any]:
        try:
            resolved = CruciblePolicy.from_dict(policy)
        except (TypeError, ValueError) as exc:
            return _denial(f"invalid_crucible_policy:{type(exc).__name__}")
        return self.service.run_once(
            arena_id=str(arena_id or ""),
            policy=resolved,
            experience_limit=max(1, min(int(experience_limit), 1000)),
        )

    def pause(self, reason: str = "showcase_operator_pause") -> dict[str, Any]:
        return self.service.pause(str(reason or "showcase_operator_pause"))

    def resume(self) -> dict[str, Any]:
        return self.service.resume()


def _experience_summary(item: dict[str, Any]) -> dict[str, Any]:
    outcome = dict(item.get("outcome_vector") or {})
    return {
        "experience_id": str(item.get("experience_id") or ""),
        "arena_id": str(item.get("arena_id") or ""),
        "task_id": str(item.get("task_id") or ""),
        "workflow_id": str(item.get("workflow_id") or ""),
        "grammar_version": str(item.get("grammar_version") or ""),
        "state_before": str(item.get("state_before") or ""),
        "state_after": str(item.get("state_after") or ""),
        "selected_transition": str(item.get("selected_transition") or ""),
        "final_outcome": str(item.get("final_outcome") or ""),
        "completed_at": float(item.get("completed_at") or 0.0),
        "legacy_record": bool(item.get("legacy_record")),
        "eligible_for_crucible": not bool(item.get("legacy_record")),
        "outcome_vector": {
            key: value
            for key, value in outcome.items()
            if key in {
                "terminal_class", "task_progress", "evidence_quality", "verification_quality",
                "safety_quality", "human_alignment", "cost_efficiency", "latency_efficiency",
                "abstention_quality", "recovery_quality",
            }
        },
        "grammar_manifest_digest": str(item.get("grammar_manifest_digest") or ""),
        "route_observation_digest": str(item.get("route_observation_digest") or ""),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _proposal_summary(item: dict[str, Any]) -> dict[str, Any]:
    validation = dict(item.get("validation") or {})
    return {
        "proposal_id": str(item.get("proposal_id") or ""),
        "run_id": str(item.get("run_id") or ""),
        "arena_id": str(item.get("arena_id") or ""),
        "grammar_version": str(item.get("grammar_version") or ""),
        "transition_id": str(item.get("transition_id") or ""),
        "status": str(item.get("status") or "CRYSTALLIZATION_PROPOSED"),
        "change_path": str(item.get("change_path") or ""),
        "current_value": item.get("current_value"),
        "proposed_value": item.get("proposed_value"),
        "recommendation": str(validation.get("proposal_recommendation") or ""),
        "all_proposal_thresholds_met": bool(validation.get("all_proposal_thresholds_met")),
        "required_next_gate": str(item.get("required_next_gate") or "VERIFIER_AND_HUMAN_REVIEW"),
        "created_at": float(item.get("created_at") or 0.0),
        "proposal_digest": str(item.get("proposal_digest") or ""),
        "automatic_grammar_promotion": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _denial(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": reason,
        "fail_closed": True,
        "active_grammar_mutation": False,
        "automatic_grammar_promotion": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = ["LearningArenaShowcase"]
