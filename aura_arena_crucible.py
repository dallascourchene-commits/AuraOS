"""Proposal-only background Crucible for Aura Arena experience records.

The service reads complete V2 experiences, mines OutcomeVector candidates, validates
on an independent validation dataset, replays a separate shadow dataset, and stores
only ``CRYSTALLIZATION_PROPOSED`` packets. It has no apply or promotion path.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import secrets
import time
from typing import Any, Callable

from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_crucible_miner import mine_crucible_candidates
from aura_crucible_store import CrucibleStore
from aura_crucible_types import (
    CrystallizationProposal,
    CruciblePolicy,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    canonical_digest,
)
from aura_crucible_validation import validate_crucible_candidate

ARENA_CRUCIBLE_VERSION = "AURA_ARENA_CRUCIBLE_V2"


class ArenaCrucibleService:
    """Cooperative pause/resume service with one bounded proposal cycle at a time."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        experience_db_path: str | Path | None = None,
        crucible_db_path: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.experience_db_path = Path(experience_db_path).resolve() if experience_db_path is not None else None
        self.store = CrucibleStore(self.repo_root, db_path=crucible_db_path)

    def close(self) -> None:
        self.store.close()

    def pause(self, reason: str = "operator_pause") -> dict[str, Any]:
        return self.store.pause(reason)

    def resume(self) -> dict[str, Any]:
        return self.store.resume()

    def status(self) -> dict[str, Any]:
        return {
            **self.store.status(),
            "service_version": ARENA_CRUCIBLE_VERSION,
            "experience_db_path": str(self.experience_db_path or self.repo_root / "Aura_Memory" / "arena_experience.db"),
            "experience_schema_required": "AURA_ARENA_EXPERIENCE_V2",
            "outcome_model": "OutcomeVector",
            "dataset_split": ["TRAIN", "VALIDATION", "SHADOW"],
            "threshold_scope": "PROPOSAL_ONLY",
            "active_grammar_mutation": False,
            "learned_weight_patch_authority": False,
            "crystallization_patch_authority": False,
            "automatic_grammar_promotion": False,
        }

    def run_once(
        self,
        *,
        arena_id: str = "",
        policy: CruciblePolicy | dict[str, Any] | None = None,
        experience_limit: int = 10000,
    ) -> dict[str, Any]:
        control = self.store.control_status()
        if control.get("paused"):
            return _denial("crucible_paused", pause_reason=str(control.get("pause_reason") or ""))
        resolved_policy = policy if isinstance(policy, CruciblePolicy) else CruciblePolicy.from_dict(policy)
        started = time.time()
        run_id = f"CRUN-{secrets.token_hex(10)}"
        grammar_index, grammar_diagnostics = self._load_grammar_index()
        with ArenaExperienceLedger(self.repo_root, db_path=self.experience_db_path) as ledger:
            experiences = ledger.history(arena_id=arena_id, limit=max(1, min(int(experience_limit), 10000)))
            ledger_status = ledger.status()
        candidates = mine_crucible_candidates(experiences, grammar_index, policy=resolved_policy, arena_id=arena_id)

        proposals: list[dict[str, Any]] = []
        validations: list[dict[str, Any]] = []
        for candidate in candidates:
            validation = validate_crucible_candidate(
                candidate,
                experiences,
                repo_root=self.repo_root,
                policy=resolved_policy,
            )
            validations.append(validation)
            if not validation.get("passed"):
                continue
            existing = self.store.get_proposal_by_candidate(candidate.candidate_id)
            if existing is not None:
                proposals.append({
                    **existing,
                    "storage": {
                        "ok": True,
                        "proposal_id": existing.get("proposal_id", ""),
                        "proposal_digest": existing.get("proposal_digest", ""),
                        "idempotent_replay": True,
                        "existing_candidate": True,
                    },
                })
                continue
            proposal_identity = {
                "candidate_id": candidate.candidate_id,
                "manifest_digest": candidate.manifest_digest,
                "source_digest": candidate.source_experience_digest,
                "validation_digest": canonical_digest(validation),
            }
            proposal = CrystallizationProposal(
                proposal_id=f"CPROP-{canonical_digest(proposal_identity)[:24]}",
                run_id=run_id,
                candidate_id=candidate.candidate_id,
                arena_id=candidate.arena_id,
                grammar_version=candidate.grammar_version,
                manifest_path=candidate.manifest_path,
                manifest_digest=candidate.manifest_digest,
                state_before=candidate.state_before,
                transition_id=candidate.transition_id,
                change_path=candidate.change_path,
                current_value=candidate.current_value,
                proposed_value=candidate.proposed_value,
                validation=validation,
                proposal_thresholds=candidate.proposal_thresholds,
                threshold_assessment={
                    **candidate.threshold_assessment,
                    "validation_thresholds": validation.get("proposal_threshold_checks", {}),
                    "all_proposal_thresholds_met": validation.get("all_proposal_thresholds_met", False),
                },
                train_experience_ids=candidate.train_experience_ids,
                validation_experience_ids=candidate.validation_experience_ids,
                shadow_experience_ids=candidate.shadow_experience_ids,
                source_experience_digest=candidate.source_experience_digest,
                created_at=time.time(),
            )
            stored = self.store.record_proposal(proposal)
            proposals.append({**proposal.to_dict(), "storage": stored})

        completed = time.time()
        report = {
            "ok": True,
            "version": ARENA_CRUCIBLE_VERSION,
            "run_id": run_id,
            "status": "COMPLETED",
            "arena_id": arena_id,
            "started_at": started,
            "completed_at": completed,
            "source_record_count": len(experiences),
            "v2_complete_record_count": int(ledger_status.get("v2_complete_record_count") or 0),
            "legacy_record_count": int(ledger_status.get("legacy_record_count") or 0),
            "compiled_grammar_count": len(grammar_index),
            "grammar_diagnostics": grammar_diagnostics,
            "candidate_count": len(candidates),
            "validation_count": len(validations),
            "proposal_count": len(proposals),
            "policy": resolved_policy.to_dict(),
            "threshold_scope": "PROPOSAL_ONLY",
            "thresholds_have_runtime_authority": False,
            "outcome_model": "OutcomeVector",
            "binary_outcome_used": False,
            "dataset_split": ["TRAIN", "VALIDATION", "SHADOW"],
            "candidate_ids": [item.candidate_id for item in candidates],
            "validations": validations,
            "proposals": proposals,
            "all_admissible_alternatives_preserved": True,
            "all_predictions_preserved": True,
            "active_grammar_mutated": False,
            "terminal_status": "CRYSTALLIZATION_PROPOSED",
            "required_next_gate": "VERIFIER_AND_HUMAN_REVIEW",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "learned_weight_patch_authority": False,
            "crystallization_patch_authority": False,
            "automatic_grammar_promotion": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }
        report["storage"] = self.store.record_run(report)
        return report

    def run_service(
        self,
        *,
        interval_seconds: float = 60.0,
        max_cycles: int | None = None,
        arena_id: str = "",
        policy: CruciblePolicy | dict[str, Any] | None = None,
        on_cycle: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        interval = max(1.0, float(interval_seconds))
        cycles = 0
        reports: list[dict[str, Any]] = []
        try:
            while max_cycles is None or cycles < max(0, int(max_cycles)):
                control = self.store.control_status()
                report = (
                    _denial("crucible_paused", pause_reason=str(control.get("pause_reason") or ""))
                    if control.get("paused")
                    else self.run_once(arena_id=arena_id, policy=policy)
                )
                reports.append(report)
                cycles += 1
                if on_cycle is not None:
                    on_cycle(report)
                if max_cycles is not None and cycles >= max_cycles:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            return {"ok": True, "status": "INTERRUPTED", "cycles": cycles, "reports": reports[-20:]}
        return {"ok": True, "status": "COMPLETED", "cycles": cycles, "reports": reports[-20:]}

    def _load_grammar_index(self) -> tuple[dict[tuple[str, str], Any], list[dict[str, Any]]]:
        index: dict[tuple[str, str], Any] = {}
        diagnostics: list[dict[str, Any]] = []
        route_root = self.repo_root / ".aura" / "arena_routes"
        for path in sorted(route_root.glob("*.json")):
            result = load_and_compile_arena_grammar(path)
            relative_path = path.resolve().relative_to(self.repo_root).as_posix()
            diagnostics.append({
                "path": relative_path,
                "ok": result.ok,
                "manifest_digest": result.manifest_digest,
                "diagnostics": [item.to_dict() for item in result.diagnostics],
            })
            grammar = result.grammar
            if not result.ok or grammar is None or grammar.meta_grammar:
                continue
            pinned = replace(grammar, source_path=relative_path)
            index[(pinned.arena_id, pinned.grammar_version)] = pinned
        return index, diagnostics


def _denial(reason: str, *, pause_reason: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "status": "DENIED",
        "reason": reason,
        "pause_reason": pause_reason,
        "fail_closed": True,
        "active_grammar_mutated": False,
        "threshold_scope": "PROPOSAL_ONLY",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "learned_weight_patch_authority": False,
        "crystallization_patch_authority": False,
        "automatic_grammar_promotion": False,
    }
