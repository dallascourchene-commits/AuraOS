"""Human Agent Arena cockpit integration for Aura Architect and local outputs.

This additive adapter keeps the existing deterministic Human Agent Arena intact
while attaching the canonical Architect/Surgeon runtime. It lets the human
configure Council and Surgeon budgets, compare or prepare plans, run bounded
Surgeon sessions, and load locally recorded generated code into cockpit state for
inspection and another governed refactor pass.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from aura_arena_architect_runtime import HumanAgentArenaArchitectRuntime
from aura_human_agent_arena import HumanAgentArena

HUMAN_AGENT_ARCHITECT_VERSION = "AURA_HUMAN_AGENT_ARCHITECT_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class HumanAgentArchitectCockpit:
    """One human-controlled cockpit over topology and the shared Architect service."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        demo: bool = False,
        control: Mapping[str, Any] | None = None,
        arena: HumanAgentArena | None = None,
        architect: HumanAgentArenaArchitectRuntime | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.arena = arena or HumanAgentArena(self.repo_root, demo=demo)
        self.architect = architect or HumanAgentArenaArchitectRuntime(
            self.repo_root,
            control=control,
        )
        self._record_event(
            "architect_attached",
            "Shared Architect/Surgeon controls and local output vault attached.",
        )

    def get_state(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": HUMAN_AGENT_ARCHITECT_VERSION,
            "arena": self.arena.get_state(),
            "control_profile": self.architect.control.to_dict(),
            "output_vault_root": self.architect.control.output_root,
            "human_review_required": True,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def configure_architect(self, control: Mapping[str, Any]) -> dict[str, Any]:
        result = self.architect.configure(control)
        self._record_event(
            "architect_control_updated",
            f"Control profile {result['control_profile']['control_digest']} activated.",
        )
        return result

    def compare_plans(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        run_id: str = "",
        benchmark: bool = False,
    ) -> dict[str, Any]:
        result = self.architect.compare_plans(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            run_id=run_id,
            benchmark=benchmark,
        )
        self._record_event(
            "architect_plan_selected",
            f"Selected {result['selected_candidate_id']} ({result['selection_digest']}).",
        )
        return result

    def prepare_refactor(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        target_file: str | None = None,
        target_symbol: str | None = None,
        run_id: str = "",
        benchmark: bool = False,
    ) -> dict[str, Any]:
        result = self.architect.prepare_refactor(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            target_file=target_file,
            target_symbol=target_symbol,
            run_id=run_id,
            benchmark=benchmark,
        )
        preparation = dict(result.get("arena_preparation") or {})
        self.arena.state.prepared_handoff_packets.append(
            {
                "kind": "architect_refactor_preparation",
                "selected_candidate_id": dict(result.get("comparison") or {}).get(
                    "selected_candidate_id"
                ),
                "selection_digest": dict(result.get("comparison") or {}).get(
                    "selection_digest"
                ),
                "plan_phase_hash": preparation.get("plan_phase_hash"),
                "selected_plan_digest": preparation.get("selected_plan_digest"),
                "act_capsules": list(preparation.get("act_capsules") or []),
                "blockers": list(preparation.get("blockers") or []),
                "warnings": list(preparation.get("warnings") or []),
                "proposal_only": True,
                "human_review_required": True,
                "production_mutation": False,
            }
        )
        self._record_event(
            "architect_refactor_prepared",
            f"Prepared plan phase {preparation.get('plan_phase_hash', '')} for human review.",
        )
        return result

    def open_surgeon_session(
        self,
        *,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        required_capabilities: Sequence[str] = (),
        provider: str = "native",
        model: str = "",
        run_id: str = "",
    ) -> dict[str, Any]:
        result = self.architect.open_surgeon_session(
            objective=objective,
            candidates=candidates,
            required_capabilities=required_capabilities,
            provider=provider,
            model=model,
            run_id=run_id,
        )
        session_id = str(dict(result.get("session") or {}).get("session_id") or "")
        self._record_event(
            "surgeon_session_opened",
            f"Opened bounded Surgeon session {session_id}.",
        )
        return result

    def next_surgeon_turn(self, session_id: str) -> dict[str, Any]:
        return self.architect.next_surgeon_turn(session_id)

    def submit_surgeon_output(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.architect.submit_surgeon_output(
            session_id=session_id,
            turn_id=turn_id,
            response=response,
            provider_usage=provider_usage,
        )
        self._record_event(
            "surgeon_output_submitted",
            f"Turn {turn_id} classified as {result.get('status', 'UNKNOWN')}.",
        )
        return result

    def surgeon_status(self, session_id: str) -> dict[str, Any]:
        return self.architect.surgeon_status(session_id)

    def apply_council_replan(
        self,
        *,
        session_id: str,
        remaining_act_capsules: list[dict[str, Any]],
        rationale: str,
        prompt: str = "",
        response: str = "",
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.architect.apply_council_replan(
            session_id=session_id,
            remaining_act_capsules=remaining_act_capsules,
            rationale=rationale,
            prompt=prompt,
            response=response,
            provider_usage=provider_usage,
        )
        self._record_event(
            "architect_council_replan",
            f"Council replan result: {result.get('status', result.get('error', 'UNKNOWN'))}.",
        )
        return result

    def list_refactor_outputs(self, *, limit: int = 50) -> dict[str, Any]:
        result = self.architect.list_refactor_outputs(limit=limit)
        self._record_event(
            "refactor_outputs_listed",
            f"Listed {len(result.get('runs', []))} local refactor runs.",
        )
        return result

    def load_refactor_output(
        self,
        relative_path: str,
        *,
        max_bytes: int = 2_000_000,
    ) -> dict[str, Any]:
        result = self.architect.load_refactor_output(
            relative_path,
            max_bytes=max_bytes,
        )
        artifact = {
            "kind": "local_refactor_output",
            "relative_path": result.get("relative_path"),
            "bytes": result.get("bytes"),
            "digest": result.get("digest"),
            "visibility": result.get("visibility"),
            "content": result.get("content"),
            "proposal_only": True,
            "human_review_required": True,
            "production_mutation": False,
        }
        self.arena.state.prepared_handoff_packets.append(artifact)
        self._record_event(
            "refactor_output_loaded",
            f"Loaded {result.get('relative_path', relative_path)} into cockpit review state.",
        )
        return {
            **result,
            "loaded_into_human_agent_arena": True,
            "handoff_index": len(self.arena.state.prepared_handoff_packets) - 1,
        }

    def route_topology_command(
        self,
        command: str,
        *,
        selected_node_ids: list[str] | None = None,
        mode: str = "explore",
    ) -> dict[str, Any]:
        return self.arena.route_command(
            command,
            selected_node_ids=selected_node_ids,
            mode=mode,
        )

    def _record_event(self, kind: str, detail: str) -> None:
        self.arena.state.add_event(kind, detail)


__all__ = ["HUMAN_AGENT_ARCHITECT_VERSION", "HumanAgentArchitectCockpit"]
