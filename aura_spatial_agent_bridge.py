"""Narrow Agent Bridge facade for the governed Spatial Arena."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from aura_construction_runtime_binding import require_canonical_construction_runtime_packet
from aura_construction_state import ConstructionProjectState
from aura_spatial_arena import SpatialArena, SpatialEgressPolicy, SpatialPrivacyClass
from aura_spatial_construction import project_construction_state_to_scene
from aura_spatial_contracts import (
    SpatialInteractionAction,
    SpatialRenderBudget,
    SpatialRendererKind,
    SpatialRenderEvidenceClass,
    SpatialRenderOutcome,
)
from aura_spatial_render_plan import (
    compile_spatial_device_profile,
    negotiate_spatial_render_plan,
)

SPATIAL_AGENT_BRIDGE_VERSION = "AURA_SPATIAL_AGENT_BRIDGE_V1"


class AuraSpatialAgentBridge:
    """Expose only bounded Spatial Arena lifecycle calls to agents and tools."""

    def __init__(self, repo_root: str | Path = ".", *, arena: SpatialArena | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.arena = arena or SpatialArena(self.repo_root)

    def prepare_construction_projection(
        self,
        *,
        objective: str,
        state: ConstructionProjectState,
        construction_runtime_packet: Mapping[str, Any],
        privacy_class: SpatialPrivacyClass | str = SpatialPrivacyClass.PROJECT,
        actor_ref: str = "human:local",
        supported_renderers: Sequence[SpatialRendererKind | str] = (
            SpatialRendererKind.ACCESSIBLE_2D,
            SpatialRendererKind.HEADLESS,
        ),
        floor_plan_assets: Iterable[Any] = (),
    ) -> dict[str, Any]:
        privacy = (
            privacy_class if isinstance(privacy_class, SpatialPrivacyClass) else SpatialPrivacyClass(str(privacy_class))
        )
        require_canonical_construction_runtime_packet(
            construction_runtime_packet,
            state_digest=state.state_digest,
        )
        run_id = ""
        try:
            framed = self.arena.frame(
                objective=objective,
                actor_ref=actor_ref,
                privacy_class=privacy,
                egress_policy=SpatialEgressPolicy.LOCAL_ONLY,
                source_refs=(
                    "owner:aura_construction_state.ConstructionProjectState",
                    "owner:aura_construction_adapter.ConstructionArenaAdapter",
                ),
            )
            run_id = framed["run_id"]
            self.arena.ground(
                run_id,
                domain_owner="aura_construction_state",
                domain_state_digest=state.state_digest,
                evidence_refs=(
                    f"construction-state:{state.state_digest}",
                    f"construction-chain:{state.final_chain_digest}",
                ),
            )
            scene = project_construction_state_to_scene(
                state,
                construction_runtime_packet,
                purpose_digest=framed["purpose_digest"],
                privacy_class=privacy,
                floor_plan_assets=floor_plan_assets,
            )
            self.arena.compile_scene(run_id, scene)
            device = compile_spatial_device_profile(
                profile_id="spatial-construction-local",
                supported_renderers=supported_renderers,
                budget=SpatialRenderBudget(
                    max_entities=4096,
                    max_links=8192,
                    max_assets=128,
                    max_asset_bytes=128 * 1024 * 1024,
                    max_cpu_ms_per_frame=50.0,
                    max_gpu_bytes=256 * 1024 * 1024,
                    max_network_bytes=0,
                ),
                accessibility_required=True,
                xr_user_activation=False,
                network_allowed=False,
                source_refs=("owner:aura_spatial_agent_bridge",),
                metadata={"domain": "construction", "fingerprinting": False},
            )
            plan = negotiate_spatial_render_plan(
                scene,
                device,
                preferred_renderers=supported_renderers,
                allow_xr=False,
            )
            self.arena.plan_render(run_id, plan=plan, device=device)
            presented = self.arena.present(run_id)
        except Exception:
            if run_id:
                try:
                    self.arena.abort_unpresented(run_id)
                except (KeyError, ValueError):
                    pass
            raise
        return {
            "ok": True,
            "version": SPATIAL_AGENT_BRIDGE_VERSION,
            "run_id": run_id,
            "status": presented,
            "scene": scene.to_dict(),
            "render_plan": plan.to_dict(),
            "domain_state_payload_included": False,
            "construction_event_payloads_included": False,
            "human_review_required": True,
            "automatic_execution": False,
            "automatic_merge": False,
        }

    def interact(
        self,
        run_id: str,
        *,
        action: SpatialInteractionAction | str,
        target_entity_ids: Iterable[str],
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.arena.interact(
            run_id,
            action=action,
            target_entity_ids=target_entity_ids,
            metadata=metadata,
        )

    def prove(
        self,
        run_id: str,
        *,
        repo_head: str,
        outcome: SpatialRenderOutcome | str = SpatialRenderOutcome.PRESENTED,
        evidence_class: SpatialRenderEvidenceClass | str = SpatialRenderEvidenceClass.DERIVED,
        metrics: Mapping[str, Any] | None = None,
        branch_name: str = "",
    ) -> dict[str, Any]:
        return self.arena.prove(
            run_id,
            outcome=outcome,
            evidence_class=evidence_class,
            metrics=metrics,
            repo_head=repo_head,
            branch_name=branch_name,
        )

    def prove_browser_telemetry(
        self,
        run_id: str,
        *,
        telemetry_packet: Mapping[str, Any],
        repo_head: str,
        branch_name: str = "",
    ) -> dict[str, Any]:
        return self.arena.prove_browser_telemetry(
            run_id,
            telemetry_packet=telemetry_packet,
            repo_head=repo_head,
            branch_name=branch_name,
        )

    def decide(self, run_id: str, *, decision: str, decision_ref: str = "human:pending") -> dict[str, Any]:
        return self.arena.decide(run_id, decision=decision, decision_ref=decision_ref)

    def dissolve(
        self,
        run_id: str,
        *,
        renderer_cleanup_receipt: Mapping[str, Any],
        reason_code: str = "SPATIAL_ARENA_COMPLETE",
    ) -> dict[str, Any]:
        return self.arena.dissolve(
            run_id,
            renderer_cleanup_receipt=renderer_cleanup_receipt,
            reason_code=reason_code,
        )

    def status(self, run_id: str) -> dict[str, Any]:
        return self.arena.status(run_id)

    def observatory(self, run_id: str) -> dict[str, Any]:
        return self.arena.observatory_projection(run_id)

    def restore_assessment(self, run_id: str, *, current_repo_head: str) -> dict[str, Any]:
        status = self.arena.status(run_id)
        checkpoint_id = status["checkpoint_id"]
        if not checkpoint_id:
            raise ValueError("Spatial Arena run has no proof checkpoint")
        projection = self.arena.checkpoint_projection(run_id)
        assessment = self.arena.persistence.assess(
            checkpoint_id,
            current_repo_head=current_repo_head,
            current_invariant_values={
                key: projection[key]
                for key in (
                    "run_id",
                    "phase",
                    "purpose_digest",
                    "domain_owner",
                    "domain_state_digest",
                    "scene_digest",
                    "render_plan_digest",
                    "raw_sensor_data_retained",
                    "restore_mode",
                )
            },
        )
        return {
            "ok": True,
            "version": SPATIAL_AGENT_BRIDGE_VERSION,
            "checkpoint_id": checkpoint_id,
            "assessment": assessment,
            "payload_included": False,
            "automatic_resume": False,
            "target_arena_mutated": False,
            "human_review_required": True,
        }

    def close(self) -> tuple[dict[str, Any], ...]:
        return self.arena.close()


__all__ = ["SPATIAL_AGENT_BRIDGE_VERSION", "AuraSpatialAgentBridge"]
