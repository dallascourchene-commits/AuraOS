"""Temporal-persistence extension for Aura's Agent Arena Bridge."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_errors import make_error_packet
from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_coding_waboose import CodingWaboose
from aura_emergent_evidence_spine import AuraEmergentEvidenceSpine
from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY

AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION = "AURA_AGENT_ARENA_PERSISTENCE_BRIDGE_V1"


def _unique_strings(*groups: list[str] | None) -> list[str]:
    result: list[str] = []
    for group in groups:
        for value in group or []:
            text = str(value or "").strip()
            if text and text not in result:
                result.append(text)
    return result


def _primary_emergent_target(
    packet: Mapping[str, Any],
    *,
    target_file: str | None,
    target_symbol: str | None,
) -> tuple[str | None, str | None]:
    selected = list(dict(packet.get("atomic_inventory") or {}).get("selected_atomic_functions") or [])
    final_file = target_file
    final_symbol = target_symbol
    if final_file and not final_symbol:
        match = next(
            (item for item in selected if isinstance(item, Mapping) and item.get("file_path") == final_file),
            None,
        )
        if isinstance(match, Mapping):
            final_symbol = str(match.get("symbol") or "") or None
    if final_symbol and not final_file:
        match = next(
            (item for item in selected if isinstance(item, Mapping) and item.get("symbol") == final_symbol),
            None,
        )
        if isinstance(match, Mapping):
            final_file = str(match.get("file_path") or "") or None
    bridge_projection = dict(dict(packet.get("projections") or {}).get("agent_bridge") or {})
    final_file = final_file or str(bridge_projection.get("target_file") or "") or None
    final_symbol = final_symbol or str(bridge_projection.get("target_symbol") or "") or None
    return final_file, final_symbol


class PersistentAuraAgentArenaBridge(AuraAgentArenaBridge):
    """Agent Bridge with checkpoint, restoration, fork, and handoff tools."""

    def __init__(self, *, repo_root: str | None = None) -> None:
        super().__init__(repo_root=repo_root)
        self.persistence = ArenaPersistenceCoordinator(str(self.repo_root))
        self.coding_waboose = CodingWaboose(self.repo_root)
        self.emergent_spine = AuraEmergentEvidenceSpine(self.repo_root)
        self._spatial_agent_bridge: Any | None = None

    def _spatial_bridge(self) -> Any:
        if self._spatial_agent_bridge is None:
            from aura_spatial_agent_bridge import AuraSpatialAgentBridge

            self._spatial_agent_bridge = AuraSpatialAgentBridge(self.repo_root)
        return self._spatial_agent_bridge

    def aura_spatial_prepare_construction(
        self,
        *,
        objective: str,
        state: Any,
        construction_runtime_packet: Mapping[str, Any],
        privacy_class: Any = "PROJECT",
        actor_ref: str = "human:local",
        supported_renderers: Sequence[Any] = ("ACCESSIBLE_2D", "HEADLESS"),
        floor_plan_assets: Iterable[Any] = (),
    ) -> dict[str, Any]:
        """Typed Python-only Construction preparation; intentionally not MCP-exposed."""

        from aura_construction_state import ConstructionProjectState

        if type(state) is not ConstructionProjectState:
            raise ValueError("Spatial Construction preparation requires exact ConstructionProjectState")
        return self._spatial_bridge().prepare_construction_projection(
            objective=objective,
            state=state,
            construction_runtime_packet=construction_runtime_packet,
            privacy_class=privacy_class,
            actor_ref=actor_ref,
            supported_renderers=supported_renderers,
            floor_plan_assets=floor_plan_assets,
        )

    def aura_spatial_status(self, run_id: str) -> dict[str, Any]:
        return self._spatial_bridge().status(run_id)

    def aura_spatial_interact(
        self,
        run_id: str,
        *,
        action: Any,
        target_entity_ids: Iterable[str],
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._spatial_bridge().interact(
            run_id,
            action=action,
            target_entity_ids=target_entity_ids,
            metadata=metadata,
        )

    def aura_spatial_prove(
        self,
        run_id: str,
        *,
        repo_head: str,
        outcome: Any = "PRESENTED",
        evidence_class: Any = "DERIVED",
        metrics: Mapping[str, Any] | None = None,
        branch_name: str = "",
    ) -> dict[str, Any]:
        return self._spatial_bridge().prove(
            run_id,
            repo_head=repo_head,
            outcome=outcome,
            evidence_class=evidence_class,
            metrics=metrics,
            branch_name=branch_name,
        )

    def aura_spatial_prove_browser_telemetry(
        self,
        run_id: str,
        *,
        telemetry_packet: Mapping[str, Any],
        repo_head: str,
        branch_name: str = "",
    ) -> dict[str, Any]:
        return self._spatial_bridge().prove_browser_telemetry(
            run_id,
            telemetry_packet=telemetry_packet,
            repo_head=repo_head,
            branch_name=branch_name,
        )

    def aura_spatial_decide(
        self,
        run_id: str,
        *,
        decision: str,
        decision_ref: str = "human:pending",
    ) -> dict[str, Any]:
        return self._spatial_bridge().decide(
            run_id,
            decision=decision,
            decision_ref=decision_ref,
        )

    def aura_spatial_observatory(self, run_id: str) -> dict[str, Any]:
        return self._spatial_bridge().observatory(run_id)

    def aura_spatial_restore_assessment(
        self,
        run_id: str,
        *,
        current_repo_head: str,
    ) -> dict[str, Any]:
        return self._spatial_bridge().restore_assessment(
            run_id,
            current_repo_head=current_repo_head,
        )

    def aura_spatial_dissolve(
        self,
        run_id: str,
        *,
        renderer_cleanup_receipt: Mapping[str, Any],
        reason_code: str = "SPATIAL_ARENA_COMPLETE",
    ) -> dict[str, Any]:
        return self._spatial_bridge().dissolve(
            run_id,
            renderer_cleanup_receipt=renderer_cleanup_receipt,
            reason_code=reason_code,
        )

    def aura_spatial_close(self) -> tuple[dict[str, Any], ...]:
        if self._spatial_agent_bridge is None:
            return ()
        receipts = self._spatial_agent_bridge.close()
        self._spatial_agent_bridge = None
        return receipts

    def aura_atomic_function_inventory(
        self,
        *,
        query: str = "",
        target_files: list[str] | None = None,
        target_symbols: list[str] | None = None,
        limit: int | None = None,
        include_source: bool = False,
    ) -> dict[str, Any]:
        return self.emergent_spine.atomic_inventory(
            query=query,
            target_files=target_files or [],
            target_symbols=target_symbols or [],
            limit=limit,
            include_source=include_source,
        )

    def aura_emergent_evidence(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.emergent_spine.run(request)

    def aura_prepare_arena(
        self,
        *,
        objective: str,
        target_file: str | None = None,
        target_symbol: str | None = None,
        acceptance_criteria: list[str] | None = None,
        risk_map: list[str] | None = None,
        constraints: list[str] | None = None,
        use_emergent_evidence: bool = False,
        emergent_radius: int = 1,
        emergent_max_atomic_nodes: int = 48,
        emergent_include_source: bool = False,
        emergent_include_research_plan: bool = True,
    ) -> dict[str, Any]:
        if not use_emergent_evidence:
            return super().aura_prepare_arena(
                objective=objective,
                target_file=target_file,
                target_symbol=target_symbol,
                acceptance_criteria=acceptance_criteria,
                risk_map=risk_map,
                constraints=constraints,
            )

        packet = self.emergent_spine.run(
            {
                "objective": objective,
                "target_files": [target_file] if target_file else [],
                "target_symbols": [target_symbol] if target_symbol else [],
                "target_arena": "coding_arena",
                "radius": emergent_radius,
                "max_atomic_nodes": emergent_max_atomic_nodes,
                "include_source": emergent_include_source,
                "include_research_plan": emergent_include_research_plan,
            }
        )
        if not packet.get("ok"):
            return make_error_packet(
                "missing_grounding",
                "Emergent evidence preparation failed closed.",
                repair_hint=str(packet.get("error") or "Resolve the emergent evidence request."),
            )
        if not packet.get("grounding_ok"):
            return make_error_packet(
                "missing_grounding",
                "Emergent evidence is affinity-only or has no exact atomic closure.",
                repair_hint="Provide an exact target file/symbol or repair CODEMAP/topology grounding.",
            )
        projection = dict(dict(packet.get("projections") or {}).get("coding_arena") or {})
        final_file, final_symbol = _primary_emergent_target(
            packet,
            target_file=target_file,
            target_symbol=target_symbol,
        )
        result = super().aura_prepare_arena(
            objective=objective,
            target_file=final_file,
            target_symbol=final_symbol,
            acceptance_criteria=_unique_strings(
                acceptance_criteria,
                list(projection.get("acceptance_criteria") or []),
            ),
            risk_map=_unique_strings(
                risk_map,
                list(projection.get("risk_map") or []),
            ),
            constraints=_unique_strings(
                constraints,
                list(projection.get("constraints") or []),
            ),
        )
        if not result.get("ok"):
            return result
        atomic = dict(packet.get("atomic_inventory") or {})
        summary = {
            "version": packet.get("version", ""),
            "packet_id": packet.get("packet_id", ""),
            "packet_digest": packet.get("packet_digest", ""),
            "status": packet.get("status", ""),
            "grounding_ok": bool(packet.get("grounding_ok")),
            "atomic_inventory_digest": atomic.get("inventory_digest", ""),
            "atomic_inventory_total": int(atomic.get("total_count") or 0),
            "selected_atomic_count": int(atomic.get("selected_count") or 0),
            "tests": list(packet.get("tests") or []),
            "waboose_focus_directives": list(packet.get("waboose_focus_directives") or []),
            "safe_to_patch": False,
            "production_mutation": False,
            "patch_authority": packet.get("patch_authority", "exact_source_spans_and_hashes_only"),
            "vsa_patch_authority": False,
        }
        result["emergent_evidence"] = summary
        phase_hash = str(result.get("plan_phase_hash") or "")
        session = self._get_session(phase_hash) if phase_hash else None
        if session is not None:
            session["emergent_evidence"] = packet
        return result

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

    def aura_waboose_learn_coderabbit(
        self,
        review_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.coding_waboose.learn_from_coderabbit(review_payload)

    def aura_waboose_learning_summary(self) -> dict[str, Any]:
        return self.coding_waboose.learning_summary()

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
                "name": "aura_spatial_status",
                "description": "Return one governed Spatial Arena run status without payloads.",
                "required_inputs": ["run_id"],
            },
            {
                "name": "aura_spatial_interact",
                "description": "Compile a review-only interaction for an existing Spatial Arena run.",
                "required_inputs": ["run_id", "action", "target_entity_ids"],
            },
            {
                "name": "aura_spatial_prove",
                "description": "Record bounded render evidence and an assessment-only checkpoint.",
                "required_inputs": ["run_id", "repo_head"],
            },
            {
                "name": "aura_spatial_prove_browser_telemetry",
                "description": "Validate exact browser telemetry and record empirical Spatial proof.",
                "required_inputs": ["run_id", "telemetry_packet", "repo_head"],
            },
            {
                "name": "aura_spatial_decide",
                "description": "Compile a human/domain decision packet without applying the decision.",
                "required_inputs": ["run_id", "decision"],
            },
            {
                "name": "aura_spatial_observatory",
                "description": "Return a read-only Spatial Arena evidence and cost projection.",
                "required_inputs": ["run_id"],
            },
            {
                "name": "aura_spatial_restore_assessment",
                "description": "Assess a Spatial checkpoint without automatic resume.",
                "required_inputs": ["run_id", "current_repo_head"],
            },
            {
                "name": "aura_spatial_dissolve",
                "description": "Dissolve a Spatial run only with exact renderer cleanup evidence.",
                "required_inputs": ["run_id", "renderer_cleanup_receipt"],
            },
            {
                "name": "aura_atomic_function_inventory",
                "description": "List the complete or bounded exact atomic callable inventory.",
                "required_inputs": [],
            },
            {
                "name": "aura_emergent_evidence",
                "description": "Build a Connectome-guided exact atomic dependency and source-slice packet.",
                "required_inputs": ["objective"],
            },
            {
                "name": "aura_waboose_learn_coderabbit",
                "description": "Ground and learn from one successful CodeRabbit review through Connectome, DREAM-lite, and QDKT.",
                "required_inputs": ["review_payload"],
            },
            {
                "name": "aura_waboose_learning_summary",
                "description": "Report grounded CodeRabbit lessons, learned patterns, and QDKT crystals.",
                "required_inputs": [],
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
