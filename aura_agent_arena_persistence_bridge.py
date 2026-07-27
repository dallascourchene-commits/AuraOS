"""Temporal-persistence extension for Aura's Agent Arena Bridge."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from typing import Any

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_errors import make_error_packet
from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_coding_waboose import CodingWaboose
from aura_emergent_evidence_spine import AuraEmergentEvidenceSpine
from aura_temporal_persistence import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY

AGENT_ARENA_PERSISTENCE_BRIDGE_VERSION = "AURA_AGENT_ARENA_PERSISTENCE_BRIDGE_V1"
_COMPASS_INTERFACE_ITEM_LIMIT = 64
_COMPASS_INTERFACE_ITEM_BYTES = 192
_COMPASS_INTERFACE_SECTION_BYTES = 32_768
_COMPASS_INTERFACE_METADATA_BYTES = 8_192
_COMPASS_INTERFACE_MAX_RESPONSE_BYTES = 131_072


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")


def _bounded_interface_value(value: Any, *, max_bytes: int = _COMPASS_INTERFACE_ITEM_BYTES) -> tuple[Any, bool]:
    raw = _canonical_json_bytes(value)
    if len(raw) <= max_bytes:
        return value, False
    digest = hashlib.sha256(raw).hexdigest()
    if isinstance(value, str):
        return f"[TRUNCATED sha256:{digest} bytes:{len(raw)}]", True
    return {
        "truncated": True,
        "sha256": digest,
        "original_bytes": len(raw),
        "original_type": type(value).__name__,
    }, True


def _bounded_interface_collection(
    values: Any,
    *,
    max_items: int = _COMPASS_INTERFACE_ITEM_LIMIT,
    max_item_bytes: int = _COMPASS_INTERFACE_ITEM_BYTES,
) -> tuple[list[Any], int, int]:
    source = list(values or [])
    selected = source[: max(0, int(max_items))]
    projected: list[Any] = []
    replacements = 0
    for item in selected:
        bounded, replaced = _bounded_interface_value(item, max_bytes=max_item_bytes)
        projected.append(bounded)
        replacements += int(replaced)
    return projected, max(0, len(source) - len(selected)), replacements


def _finalize_compass_response(
    response: dict[str, Any],
    truncation: dict[str, Any],
) -> dict[str, Any]:
    """Attach a deterministic receipt and fail closed above the shared byte ceiling."""
    truncation.setdefault("max_items_per_collection", _COMPASS_INTERFACE_ITEM_LIMIT)
    truncation.setdefault("max_item_bytes", _COMPASS_INTERFACE_ITEM_BYTES)
    truncation.setdefault("max_section_bytes", _COMPASS_INTERFACE_SECTION_BYTES)
    truncation.setdefault("max_response_bytes", _COMPASS_INTERFACE_MAX_RESPONSE_BYTES)
    for field, value in list(response.items()):
        if field == "interface_truncation" or isinstance(value, (Mapping, list, tuple)):
            continue
        bounded, replaced = _bounded_interface_value(value)
        response[field] = bounded
        if replaced:
            truncation[f"{field}_oversize_replaced"] = 1
    response["interface_truncation"] = truncation
    for _ in range(8):
        response_bytes = len(_canonical_json_bytes(response))
        if truncation.get("response_bytes") == response_bytes:
            break
        truncation["response_bytes"] = response_bytes
    if truncation.get("response_bytes") != len(_canonical_json_bytes(response)):
        raise ValueError("Compass interface projection byte receipt did not stabilize")
    if int(truncation["response_bytes"]) > _COMPASS_INTERFACE_MAX_RESPONSE_BYTES:
        raise ValueError("Compass interface projection exceeded its byte budget")
    return response


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
        self._compass_runs: dict[str, dict[str, Any]] = {}

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
        bilateral_contract: Mapping[str, Any] | None = None,
        bilateral_plan_gate: Mapping[str, Any] | None = None,
        bilateral_proof_plan: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not use_emergent_evidence:
            return super().aura_prepare_arena(
                objective=objective,
                target_file=target_file,
                target_symbol=target_symbol,
                acceptance_criteria=acceptance_criteria,
                risk_map=risk_map,
                constraints=constraints,
                bilateral_contract=bilateral_contract,
                bilateral_plan_gate=bilateral_plan_gate,
                bilateral_proof_plan=bilateral_proof_plan,
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
            bilateral_contract=bilateral_contract,
            bilateral_plan_gate=bilateral_plan_gate,
            bilateral_proof_plan=bilateral_proof_plan,
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

    def aura_compass_prepare(
        self,
        *,
        objective: str,
        target_files: Sequence[str] = (),
        target_symbols: Sequence[str] = (),
        rollout_mode: str = "SHADOW",
        rollout_provider: str = "",
        rollout_budget: Mapping[str, Any] | None = None,
        rollout_nonce: str = "",
        rollout_verifier_ref: str = "",
    ) -> dict[str, Any]:
        """Prepare and retain one bounded Compass packet; return a compact receipt."""
        from aura_coding_relationship_compass import compile_coding_relationship_compass

        packet = compile_coding_relationship_compass(
            objective,
            self.repo_root,
            target_files=tuple(target_files or ()),
            target_symbols=tuple(target_symbols or ()),
            rollout_mode=rollout_mode,
            rollout_provider=rollout_provider,
            rollout_budget=rollout_budget,
            rollout_nonce=rollout_nonce,
            rollout_verifier_ref=rollout_verifier_ref,
        )
        run_id = str(packet.get("compass_digest") or "")
        if not run_id:
            raise ValueError("Compass preparation did not produce a digest")
        self._compass_runs[run_id] = packet
        if len(self._compass_runs) > 8:
            oldest = next(iter(self._compass_runs))
            if oldest != run_id:
                self._compass_runs.pop(oldest, None)
        rollout, rollout_replaced = _bounded_interface_value(
            dict(packet.get("rollout") or {}),
            max_bytes=_COMPASS_INTERFACE_METADATA_BYTES,
        )
        response = {
            "ok": True,
            "run_id": run_id,
            "route": packet.get("route"),
            "target_file": packet.get("target_file"),
            "target_symbol": packet.get("target_symbol"),
            "grounding_digest": packet.get("grounding_digest"),
            "neighborhood_digest": (packet.get("relational_neighborhood") or {}).get("neighborhood_digest"),
            "atlas_digest": (packet.get("atlas") or {}).get("snapshot_digest"),
            "rollout": rollout,
            "counts": {
                "targets": len(packet.get("recommended_targets", ()) or ()),
                "emergent_candidates": len(
                    (packet.get("bounded_emergent_discovery") or {}).get("candidates", ()) or ()
                ),
                "act_capsules": len((packet.get("act_capsules") or {}).get("act_capsules", ()) or ()),
            },
            "proposal_only": True,
            "safe_to_patch": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        return _finalize_compass_response(
            response,
            {"rollout_oversize_replaced": int(rollout_replaced)},
        )

    def _compass_packet(self, run_id: str) -> dict[str, Any]:
        packet = self._compass_runs.get(str(run_id or ""))
        if packet is None:
            raise ValueError("unknown Compass run_id")
        return packet

    def aura_compass_neighborhood(self, run_id: str) -> dict[str, Any]:
        packet = self._compass_packet(run_id)
        neighborhood = dict(packet.get("relational_neighborhood") or {})
        participants = list(neighborhood.get("participants", []) or [])
        relations = list(neighborhood.get("relations", []) or [])
        truncation_reasons = list(neighborhood.get("truncation_reasons", []) or [])
        projected_participants, participants_omitted, participants_replaced = _bounded_interface_collection(
            participants, max_items=64
        )
        projected_relations, relations_omitted, relations_replaced = _bounded_interface_collection(
            relations,
            max_items=256,
        )
        projected_reasons, reasons_omitted, reasons_replaced = _bounded_interface_collection(
            truncation_reasons,
            max_items=64,
        )
        metrics, metrics_replaced = _bounded_interface_value(
            dict(neighborhood.get("metrics") or {}),
            max_bytes=_COMPASS_INTERFACE_METADATA_BYTES,
        )
        response = {
            "ok": True,
            "run_id": run_id,
            "neighborhood_digest": neighborhood.get("neighborhood_digest"),
            "participants": projected_participants,
            "relations": projected_relations,
            "metrics": metrics,
            "truncation_reasons": projected_reasons,
            "proposal_only": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        return _finalize_compass_response(
            response,
            {
                "participants_omitted": participants_omitted,
                "participants_oversize_replaced": participants_replaced,
                "relations_omitted": relations_omitted,
                "relations_oversize_replaced": relations_replaced,
                "metrics_oversize_replaced": int(metrics_replaced),
                "truncation_reasons_omitted": reasons_omitted,
                "truncation_reasons_oversize_replaced": reasons_replaced,
            },
        )

    def aura_compass_classify(self, run_id: str) -> dict[str, Any]:
        packet = self._compass_packet(run_id)
        atlas = dict(packet.get("atlas") or {})
        bounded = dict(packet.get("bounded_emergent_verification") or {})
        field_sources = {
            "assessments": atlas.get("assessments", []) or [],
            "prohibitions": packet.get("prohibitions", []) or [],
            "missing_roles": packet.get("missing_roles", []) or [],
            "required_adapters": packet.get("required_adapters", []) or [],
            "accepted_candidates": bounded.get("accepted_candidates", []) or [],
            "rejected_candidates": bounded.get("rejected_candidates", []) or [],
            "suppressed_candidates": bounded.get("suppressed_candidates", []) or [],
        }
        projected: dict[str, list[Any]] = {}
        truncation: dict[str, Any] = {}
        for field, values in field_sources.items():
            items, omitted, replacements = _bounded_interface_collection(values)
            projected[field] = items
            truncation[f"{field}_omitted"] = omitted
            truncation[f"{field}_oversize_replaced"] = replacements

        summary, summary_replaced = _bounded_interface_value(bounded.get("summary") or {})
        truncation["bounded_emergent_summary_oversize_replaced"] = int(summary_replaced)
        response: dict[str, Any] = {
            "ok": True,
            "run_id": run_id,
            "atlas_digest": atlas.get("snapshot_digest"),
            "profile": atlas.get("profile"),
            "assessments": projected["assessments"],
            "prohibitions": projected["prohibitions"],
            "missing_roles": projected["missing_roles"],
            "required_adapters": projected["required_adapters"],
            "bounded_emergent": {
                "version": bounded.get("version"),
                "verification_digest": bounded.get("verification_digest"),
                "neighborhood_digest": bounded.get("neighborhood_digest"),
                "trusted_neighborhood_verified": bounded.get("trusted_neighborhood_verified"),
                "accepted_candidates": projected["accepted_candidates"],
                "rejected_candidates": projected["rejected_candidates"],
                "suppressed_candidates": projected["suppressed_candidates"],
                "summary": summary,
            },
            "proposal_only": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        return _finalize_compass_response(response, truncation)

    def aura_compass_breadboard(self, run_id: str) -> dict[str, Any]:
        packet = self._compass_packet(run_id)
        typed_compatibility, typed_replaced = _bounded_interface_value(
            dict(packet.get("typed_compatibility") or {}),
            max_bytes=_COMPASS_INTERFACE_SECTION_BYTES,
        )
        coding_breadboard, breadboard_replaced = _bounded_interface_value(
            dict(packet.get("coding_breadboard") or {}),
            max_bytes=_COMPASS_INTERFACE_SECTION_BYTES,
        )
        response = {
            "ok": True,
            "run_id": run_id,
            "typed_compatibility": typed_compatibility,
            "coding_breadboard": coding_breadboard,
            "proposal_only": True,
            "safe_to_patch": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        return _finalize_compass_response(
            response,
            {
                "typed_compatibility_oversize_replaced": int(typed_replaced),
                "coding_breadboard_oversize_replaced": int(breadboard_replaced),
            },
        )

    def aura_compass_plan(self, run_id: str) -> dict[str, Any]:
        packet = self._compass_packet(run_id)
        graph = dict(packet.get("change_graph") or {})
        nodes = list(graph.get("nodes", []) or [])
        phase_capsules = list(packet.get("phase_capsules", []) or [])
        projected_nodes, nodes_omitted, nodes_replaced = _bounded_interface_collection(
            nodes,
            max_items=256,
        )
        projected_phases, phases_omitted, phases_replaced = _bounded_interface_collection(
            phase_capsules,
            max_items=64,
        )
        council_route, council_replaced = _bounded_interface_value(
            dict(packet.get("council_route") or {}),
            max_bytes=_COMPASS_INTERFACE_SECTION_BYTES,
        )
        response = {
            "ok": True,
            "run_id": run_id,
            "graph_digest": graph.get("graph_digest"),
            "nodes": projected_nodes,
            "phase_capsules": projected_phases,
            "council_route": council_route,
            "proposal_only": True,
            "safe_to_patch": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        return _finalize_compass_response(
            response,
            {
                "nodes_omitted": nodes_omitted,
                "nodes_oversize_replaced": nodes_replaced,
                "phase_capsules_omitted": phases_omitted,
                "phase_capsules_oversize_replaced": phases_replaced,
                "council_route_oversize_replaced": int(council_replaced),
            },
        )

    def aura_compass_compile_capsules(self, run_id: str) -> dict[str, Any]:
        packet = self._compass_packet(run_id)
        act_capsules, capsules_replaced = _bounded_interface_value(
            dict(packet.get("act_capsules") or {}),
            max_bytes=_COMPASS_INTERFACE_SECTION_BYTES,
        )
        agent_ir, agent_ir_replaced = _bounded_interface_value(
            dict(packet.get("agent_ir") or {}),
            max_bytes=_COMPASS_INTERFACE_SECTION_BYTES,
        )
        response = {
            "ok": bool((packet.get("act_capsules") or {}).get("ok")),
            "run_id": run_id,
            "act_capsules": act_capsules,
            "agent_ir": agent_ir,
            "surgeon_handoff_required": True,
            "provider_execution_authorized": False,
            "proposal_only": True,
            "safe_to_patch": False,
            "automatic_commit": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        return _finalize_compass_response(
            response,
            {
                "act_capsules_oversize_replaced": int(capsules_replaced),
                "agent_ir_oversize_replaced": int(agent_ir_replaced),
            },
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
                "name": "aura_compass_prepare",
                "description": "Prepare an exact-head Coding Relationship Compass run.",
                "required_inputs": ["objective"],
            },
            {
                "name": "aura_compass_neighborhood",
                "description": "Return the bounded relational neighborhood for a prepared Compass run.",
                "required_inputs": ["run_id"],
            },
            {
                "name": "aura_compass_classify",
                "description": "Return objective Atlas and bounded emergent classifications.",
                "required_inputs": ["run_id"],
            },
            {
                "name": "aura_compass_breadboard",
                "description": "Return C5 typed compatibility and Breadboard receipts.",
                "required_inputs": ["run_id"],
            },
            {
                "name": "aura_compass_plan",
                "description": "Return the proposal-only Change Graph and Council route.",
                "required_inputs": ["run_id"],
            },
            {
                "name": "aura_compass_compile_capsules",
                "description": "Compile proposal-only Act Capsules and SPEC-floor Agent IR.",
                "required_inputs": ["run_id"],
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
