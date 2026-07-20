"""Governed Spatial Arena lifecycle for Aura projection sessions.

The Arena coordinates immutable scenes, render plans, review-only interactions,
receipts, checkpoints, and dissolution. It does not render, mutate domain truth,
authorize physical work, or grant patch/execution authority.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
import time
from typing import Any

from aura_arena_attempt_archive import ArenaAttemptArchive
from aura_arena_persistence_adapters import ArenaPersistenceCoordinator
from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_event_contracts import canonical_json, stable_digest
from aura_liquid_planning_arena import ActionCapsule, ArenaLease, BoundaryContract
from aura_spatial_contracts import (
    PATCH_AUTHORITY,
    SpatialDeviceProfile,
    SpatialInteractionAction,
    SpatialInteractionIntent,
    SpatialRenderEvidenceClass,
    SpatialRenderOutcome,
    SpatialRenderPlan,
    SpatialSceneSnapshot,
)
from aura_spatial_interaction import compile_hotswap_request_guard, compile_spatial_interaction
from aura_spatial_session import SpatialProjectionSessionManager

SPATIAL_ARENA_VERSION = "AURA_SPATIAL_ARENA_V1"
SPATIAL_ROUTE_PATH = ".aura/arena_routes/spatial.v1.json"
MAX_SPATIAL_ARENA_RUNS = 64
MAX_SPATIAL_GROUNDING_REFS = 256
MAX_SPATIAL_GROUNDING_BYTES = 131_072
MAX_SPATIAL_INTERACTIONS_PER_RUN = 256
MAX_SPATIAL_WORKER_PACKET_BYTES = 4_194_304

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,127}$")
_DIGEST = re.compile(r"^(?:[0-9a-f]{32}|[0-9a-f]{64})$")


class SpatialArenaPhase(str, Enum):
    FRAME = "FRAME"
    GROUND = "GROUND"
    COMPILE_SCENE = "COMPILE_SCENE"
    PLAN_RENDER = "PLAN_RENDER"
    PRESENT = "PRESENT"
    INTERACT = "INTERACT"
    PROVE = "PROVE"
    DECIDE = "DECIDE"
    DISSOLVE = "DISSOLVE"


class SpatialPrivacyClass(str, Enum):
    PUBLIC = "PUBLIC"
    PROJECT = "PROJECT"
    RESTRICTED = "RESTRICTED"
    SENSITIVE = "SENSITIVE"


class SpatialEgressPolicy(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    ADMITTED_RENDER_WORKER = "ADMITTED_RENDER_WORKER"


@dataclass
class _SpatialArenaRun:
    run_id: str
    objective: str
    purpose_digest: str
    actor_ref: str
    privacy_class: SpatialPrivacyClass
    egress_policy: SpatialEgressPolicy
    admitted_asset_ids: tuple[str, ...]
    admitted_worker_refs: tuple[str, ...]
    admitted_worker_capabilities: tuple[tuple[str, str], ...]
    source_refs: tuple[str, ...]
    action_capsule: ActionCapsule
    boundary_contract: BoundaryContract
    lease: ArenaLease
    created_at: float
    phase: SpatialArenaPhase = SpatialArenaPhase.FRAME
    domain_owner: str = ""
    domain_state_digest: str = ""
    grounding_refs: tuple[str, ...] = ()
    scene: SpatialSceneSnapshot | None = None
    device: SpatialDeviceProfile | None = None
    plan: SpatialRenderPlan | None = None
    session_id: str = ""
    interactions: list[SpatialInteractionIntent] = field(default_factory=list)
    proof_receipt_ids: list[str] = field(default_factory=list)
    checkpoint_id: str = ""
    archive_artifact_ids: list[str] = field(default_factory=list)
    decision_packet: dict[str, Any] | None = None
    worker_packet_count: int = 0
    worker_packet_bytes: int = 0


class SpatialArena:
    """One bounded owner for the S5 Spatial Arena lifecycle."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        session_manager: SpatialProjectionSessionManager | None = None,
        attempt_archive: ArenaAttemptArchive | None = None,
        persistence: ArenaPersistenceCoordinator | None = None,
        now: Callable[[], float] | None = None,
        max_runs: int = MAX_SPATIAL_ARENA_RUNS,
    ) -> None:
        root = Path(repo_root).resolve()
        if type(max_runs) is not int or not 1 <= max_runs <= 1024:
            raise ValueError("max_runs must be an integer in 1..1024")
        compiled = load_and_compile_arena_grammar(root / SPATIAL_ROUTE_PATH)
        if not compiled.ok or compiled.grammar is None:
            raise ValueError(f"Spatial Arena route manifest failed compilation: {compiled.to_dict()}")
        self.repo_root = root
        self.route_manifest_digest = compiled.manifest_digest
        self.session_manager = session_manager or SpatialProjectionSessionManager(max_active_sessions=max_runs)
        self.attempt_archive = attempt_archive or ArenaAttemptArchive(root)
        self.persistence = persistence or ArenaPersistenceCoordinator(str(root))
        self._owns_archive = attempt_archive is None
        self._now = now or time.time
        self._max_runs = max_runs
        self._runs: dict[str, _SpatialArenaRun] = {}
        self._sequence = 0
        self._dissolved: list[dict[str, Any]] = []
        self._closed = False

    def frame(
        self,
        *,
        objective: str,
        actor_ref: str = "human:local",
        privacy_class: SpatialPrivacyClass | str = SpatialPrivacyClass.PROJECT,
        egress_policy: SpatialEgressPolicy | str = SpatialEgressPolicy.LOCAL_ONLY,
        admitted_asset_ids: Iterable[str] = (),
        admitted_worker_refs: Iterable[str] = (),
        admitted_worker_capability_digests: Mapping[str, str] | None = None,
        source_refs: Iterable[str] = (),
    ) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("Spatial Arena is closed")
        if len(self._runs) >= self._max_runs:
            raise ValueError("active Spatial Arena run ceiling reached")
        objective_value = _text(objective, "objective", maximum=4096)
        actor = _identifier(actor_ref, "actor_ref")
        privacy = _enum(privacy_class, SpatialPrivacyClass, "privacy_class")
        egress = _enum(egress_policy, SpatialEgressPolicy, "egress_policy")
        assets = _identifiers(admitted_asset_ids, "admitted_asset_ids", maximum=4096)
        workers = _identifiers(admitted_worker_refs, "admitted_worker_refs", maximum=64)
        worker_capabilities = _worker_capabilities(
            admitted_worker_capability_digests,
            admitted_worker_refs=workers,
        )
        refs = _refs(source_refs, "source_refs")
        if egress is SpatialEgressPolicy.ADMITTED_RENDER_WORKER and privacy in {
            SpatialPrivacyClass.RESTRICTED,
            SpatialPrivacyClass.SENSITIVE,
        }:
            raise ValueError("restricted or sensitive spatial runs must remain local-only")
        if egress is SpatialEgressPolicy.LOCAL_ONLY and (workers or worker_capabilities):
            raise ValueError("local-only Spatial runs cannot declare external workers")
        if egress is SpatialEgressPolicy.ADMITTED_RENDER_WORKER and not workers:
            raise ValueError("external Spatial egress requires at least one admitted worker")
        if egress is SpatialEgressPolicy.ADMITTED_RENDER_WORKER and not assets:
            raise ValueError("external Spatial egress requires explicit pre-admitted assets")
        if egress is SpatialEgressPolicy.ADMITTED_RENDER_WORKER and {
            worker_ref for worker_ref, _ in worker_capabilities
        } != set(workers):
            raise ValueError("external Spatial egress requires a pre-admitted capability digest for every worker")
        purpose_digest = stable_digest(
            {
                "objective": objective_value,
                "actor_ref": actor,
                "privacy_class": privacy.value,
                "egress_policy": egress.value,
                "admitted_asset_ids": list(assets),
                "admitted_worker_refs": list(workers),
                "admitted_worker_capability_digests": dict(worker_capabilities),
            },
            digest_size=32,
        )
        self._sequence += 1
        created_at = float(self._now())
        run_id = "spatial-run:" + stable_digest(
            {
                "purpose_digest": purpose_digest,
                "created_at": created_at,
                "sequence": self._sequence,
                "route": self.route_manifest_digest,
            },
            digest_size=12,
        )
        capsule = ActionCapsule.create(
            capsule_id=run_id,
            domain="spatial",
            role="spatial_projection_coordinator",
            objective=objective_value,
            target={"purpose_digest": purpose_digest, "privacy_class": privacy.value},
            scope={
                "regions": [{"region_type": "spatial_asset", "id": item, "mode": "read_only"} for item in assets],
                "egress_policy": egress.value,
                "admitted_worker_refs": list(workers),
            },
            allowed_actions=[
                "compile immutable projection scenes",
                "negotiate bounded render plans",
                "present through replaceable render adapters",
                "compile review-only spatial interactions",
                "record evidence receipts and assessment-only checkpoints",
                "dissolve sessions and release leases",
            ],
            forbidden_actions=[
                "mutate canonical domain records",
                "retain raw private sensor payloads",
                "send unadmitted assets or state to external workers",
                "claim renderer output as authority",
                "commit push merge or promote production",
            ],
            acceptance_checks=[
                "scene purpose and domain-state digests remain bound",
                "privacy and egress policy remain satisfied",
                "all actions end at human or domain decision",
                "dissolution releases leases and session resources",
            ],
            expected_output="SPATIAL_ARENA_REVIEW_PACKET",
            escalation_triggers=["stale digest", "privacy conflict", "egress violation", "domain authority required"],
            metadata={
                "route_manifest_digest": self.route_manifest_digest,
                "proposal_only": True,
                "admitted_worker_refs": list(workers),
                "admitted_worker_capability_digests": dict(worker_capabilities),
            },
        )
        boundary = BoundaryContract.placeholder(
            domain="spatial",
            capsule_id=run_id,
            boundary_type="projection_authority_boundary",
            external_system="canonical domain owner and replaceable renderer",
            source_region={"purpose_digest": purpose_digest, "privacy_class": privacy.value},
            owned_scope=list(assets),
            assumptions=[
                "domain records remain authoritative",
                "renderer coordinates and interactions are projections only",
            ],
            required_inputs=["domain state digest", "immutable scene", "bounded device profile", "render plan"],
            promised_outputs=["review-only interaction intents", "render evidence receipts", "dissolution receipt"],
            constraints=["no raw sensor retention", f"egress:{egress.value}", f"privacy:{privacy.value}"],
            escalation_triggers=["authority decision required", "privacy downgrade", "unadmitted asset requested"],
            invariant="spatial representations never become domain, execution, renderer, or patch authority",
            metadata={
                "purpose_digest": purpose_digest,
                "proposal_only": True,
                "admitted_worker_refs": list(workers),
                "admitted_worker_capability_digests": dict(worker_capabilities),
            },
        )
        lease = ArenaLease.create(
            domain="spatial",
            capsule_id=run_id,
            holder="spatial_projection_coordinator",
            regions=[{"region_type": "spatial_asset", "id": item, "mode": "read_only"} for item in assets],
            allowed_actions=capsule.allowed_actions,
            forbidden_actions=capsule.forbidden_actions,
            mode="read_only",
            conflict_policy="deny_then_escalate",
            metadata={
                "purpose_digest": purpose_digest,
                "privacy_class": privacy.value,
                "egress_policy": egress.value,
                "admitted_worker_refs": list(workers),
                "admitted_worker_capability_digests": dict(worker_capabilities),
            },
        )
        self._runs[run_id] = _SpatialArenaRun(
            run_id=run_id,
            objective=objective_value,
            purpose_digest=purpose_digest,
            actor_ref=actor,
            privacy_class=privacy,
            egress_policy=egress,
            admitted_asset_ids=assets,
            admitted_worker_refs=workers,
            admitted_worker_capabilities=worker_capabilities,
            source_refs=refs,
            action_capsule=capsule,
            boundary_contract=boundary,
            lease=lease,
            created_at=created_at,
        )
        return self.status(run_id)

    def ground(
        self,
        run_id: str,
        *,
        domain_owner: str,
        domain_state_digest: str,
        evidence_refs: Iterable[str],
    ) -> dict[str, Any]:
        run = self._require_phase(run_id, SpatialArenaPhase.FRAME)
        owner = _identifier(domain_owner, "domain_owner")
        digest = _digest(domain_state_digest, "domain_state_digest")
        refs = _refs(evidence_refs, "evidence_refs")
        if not refs:
            raise ValueError("grounding evidence_refs must not be empty")
        run.domain_owner = owner
        run.domain_state_digest = digest
        run.grounding_refs = refs
        run.phase = SpatialArenaPhase.GROUND
        return self.status(run_id)

    def compile_scene(self, run_id: str, scene: SpatialSceneSnapshot) -> dict[str, Any]:
        run = self._require_phase(run_id, SpatialArenaPhase.GROUND)
        if not isinstance(scene, SpatialSceneSnapshot):
            raise ValueError("scene must be a SpatialSceneSnapshot")
        if scene.purpose_digest != run.purpose_digest:
            raise ValueError("scene purpose digest is stale for this Spatial Arena run")
        scene_assets = {item.asset_id for item in scene.assets}
        admitted = set(run.admitted_asset_ids)
        if not admitted:
            if run.egress_policy is not SpatialEgressPolicy.LOCAL_ONLY:
                raise ValueError("external Spatial scenes require explicit pre-admitted assets")
            run.lease.status = "released"
            run.admitted_asset_ids = tuple(sorted(scene_assets))
            run.boundary_contract = BoundaryContract.placeholder(
                domain="spatial",
                capsule_id=run.run_id,
                boundary_type="projection_authority_boundary",
                external_system="canonical domain owner and replaceable renderer",
                source_region={"purpose_digest": run.purpose_digest, "privacy_class": run.privacy_class.value},
                owned_scope=list(run.admitted_asset_ids),
                assumptions=[
                    "domain records remain authoritative",
                    "renderer coordinates and interactions are projections only",
                ],
                required_inputs=["domain state digest", "immutable scene", "bounded device profile", "render plan"],
                promised_outputs=["review-only interaction intents", "render evidence receipts", "dissolution receipt"],
                constraints=[
                    "no raw sensor retention",
                    f"egress:{run.egress_policy.value}",
                    f"privacy:{run.privacy_class.value}",
                ],
                escalation_triggers=["authority decision required", "privacy downgrade", "unadmitted asset requested"],
                invariant="spatial representations never become domain, execution, renderer, or patch authority",
                metadata={
                    "purpose_digest": run.purpose_digest,
                    "scene_admission_bound": True,
                    "proposal_only": True,
                    "admitted_worker_refs": list(run.admitted_worker_refs),
                    "admitted_worker_capability_digests": dict(run.admitted_worker_capabilities),
                },
            )
            run.lease = ArenaLease.create(
                domain="spatial",
                capsule_id=run.run_id,
                holder="spatial_projection_coordinator",
                regions=[
                    {"region_type": "spatial_asset", "id": item, "mode": "read_only"} for item in run.admitted_asset_ids
                ],
                allowed_actions=run.action_capsule.allowed_actions,
                forbidden_actions=run.action_capsule.forbidden_actions,
                mode="read_only",
                conflict_policy="deny_then_escalate",
                metadata={
                    "purpose_digest": run.purpose_digest,
                    "privacy_class": run.privacy_class.value,
                    "egress_policy": run.egress_policy.value,
                    "scene_admission_bound": True,
                    "admitted_worker_refs": list(run.admitted_worker_refs),
                    "admitted_worker_capability_digests": dict(run.admitted_worker_capabilities),
                },
            )
        elif not scene_assets.issubset(admitted):
            raise ValueError(f"scene contains unadmitted assets: {sorted(scene_assets - admitted)}")
        if f"domain-state:{run.domain_state_digest}" not in scene.source_refs:
            raise ValueError("scene is not bound to the grounded domain-state digest")
        run.scene = scene
        run.phase = SpatialArenaPhase.COMPILE_SCENE
        return self.status(run_id)

    def plan_render(
        self,
        run_id: str,
        *,
        plan: SpatialRenderPlan,
        device: SpatialDeviceProfile,
    ) -> dict[str, Any]:
        run = self._require_phase(run_id, SpatialArenaPhase.COMPILE_SCENE)
        if not isinstance(plan, SpatialRenderPlan) or not isinstance(device, SpatialDeviceProfile):
            raise ValueError("plan and device must be retained spatial contracts")
        assert run.scene is not None
        SpatialProjectionSessionManager._validate_bindings(run.scene, plan, device)
        if run.egress_policy is SpatialEgressPolicy.LOCAL_ONLY and device.network_allowed:
            raise ValueError("local-only Spatial Arena runs require a network-disabled device profile")
        if run.egress_policy is SpatialEgressPolicy.ADMITTED_RENDER_WORKER:
            if not device.network_allowed or device.budget.max_network_bytes < 1:
                raise ValueError(
                    "external Spatial egress requires a network-enabled device profile with a positive byte budget"
                )
        run.plan = plan
        run.device = device
        run.phase = SpatialArenaPhase.PLAN_RENDER
        return self.status(run_id)

    def admitted_worker_packet(
        self,
        run_id: str,
        *,
        worker_ref: str,
        worker_capability_digest: str,
    ) -> dict[str, Any]:
        run = self._get(run_id)
        if run.phase not in {
            SpatialArenaPhase.PLAN_RENDER,
            SpatialArenaPhase.PRESENT,
            SpatialArenaPhase.INTERACT,
            SpatialArenaPhase.PROVE,
            SpatialArenaPhase.DECIDE,
        }:
            raise ValueError("worker packet requires a planned Spatial Arena run")
        assert run.scene is not None and run.plan is not None and run.device is not None
        if run.egress_policy is SpatialEgressPolicy.LOCAL_ONLY:
            raise ValueError("local-only Spatial Arena runs cannot emit an external worker packet")
        worker = _identifier(worker_ref, "worker_ref")
        if worker not in set(run.admitted_worker_refs):
            raise ValueError("render worker is not admitted by this Spatial Arena purpose")
        capability_digest = _digest(worker_capability_digest, "worker_capability_digest")
        expected_capability_digest = dict(run.admitted_worker_capabilities).get(worker)
        if capability_digest != expected_capability_digest:
            raise ValueError("render worker capability digest is not admitted by this Spatial Arena purpose")
        admitted = set(run.admitted_asset_ids)
        assets = [
            {
                "asset_id": item.asset_id,
                "asset_type": item.asset_type.value,
                "media_type": item.media_type,
                "content_digest": item.content_digest,
                "byte_length": item.byte_length,
                "frame_id": item.frame_id,
                "bounds_min": list(item.bounds_min),
                "bounds_max": list(item.bounds_max),
                "truth_class": item.truth_class.value,
            }
            for item in run.scene.assets
            if item.asset_id in admitted
        ]
        plan = {
            "plan_id": run.plan.plan_id,
            "scene_id": run.plan.scene_id,
            "scene_digest": run.plan.scene_digest,
            "selected_renderer": run.plan.selected_renderer.value,
            "fallback_renderers": [item.value for item in run.plan.fallback_renderers],
            "budget": run.plan.budget.to_dict(),
            "render_plan_digest": run.plan.render_plan_digest,
        }
        packet = {
            "ok": True,
            "version": SPATIAL_ARENA_VERSION,
            "run_id": run.run_id,
            "worker_ref": worker,
            "worker_capability_digest": capability_digest,
            "lease_id": run.lease.lease_id,
            "purpose_digest": run.purpose_digest,
            "privacy_class": run.privacy_class.value,
            "egress_policy": run.egress_policy.value,
            "admitted_worker_refs": list(run.admitted_worker_refs),
            "admitted_worker_capability_digests": dict(run.admitted_worker_capabilities),
            "domain_owner": run.domain_owner,
            "domain_state_digest": run.domain_state_digest,
            "scene_id": run.scene.scene_id,
            "scene_digest": run.scene.scene_digest,
            "render_plan": plan,
            "device_profile_digest": run.device.device_profile_digest,
            "assets": assets,
            "asset_uris_included": False,
            "asset_metadata_included": False,
            "asset_source_refs_included": False,
            "asset_payloads_included": False,
            "scene_entities_included": False,
            "raw_domain_state_included": False,
            "raw_sensor_data_included": False,
            "payload_minimized": True,
            "renderer_authority": False,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
        }
        packet["packet_body_bytes"] = len(canonical_json(packet).encode("utf-8"))
        packet["packet_digest"] = stable_digest(packet, digest_size=32)
        emitted_bytes = len(canonical_json(packet).encode("utf-8"))
        if emitted_bytes > MAX_SPATIAL_WORKER_PACKET_BYTES:
            raise ValueError("Spatial render-worker packet exceeds its byte ceiling")
        if run.worker_packet_bytes + emitted_bytes > run.plan.budget.max_network_bytes:
            raise ValueError("Spatial render-worker packet exceeds its admitted network byte ceiling")
        run.worker_packet_count += 1
        run.worker_packet_bytes += emitted_bytes
        return packet

    def present(self, run_id: str) -> dict[str, Any]:
        run = self._require_phase(run_id, SpatialArenaPhase.PLAN_RENDER)
        if run.lease.status != "active":
            raise ValueError("Spatial Arena presentation requires an active lease")
        required_capability = "present through replaceable render adapters"
        if required_capability not in set(run.lease.allowed_actions):
            raise ValueError("Spatial Arena lease does not admit presentation")
        assert run.scene is not None and run.plan is not None and run.device is not None
        summary = self.session_manager.create_session(run.scene, run.plan, run.device)
        run.session_id = summary.session_id
        run.phase = SpatialArenaPhase.PRESENT
        return {**self.status(run_id), "session": summary.to_dict()}

    def interact(
        self,
        run_id: str,
        *,
        action: SpatialInteractionAction | str,
        target_entity_ids: Iterable[str],
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        run = self._get(run_id)
        if run.phase not in {SpatialArenaPhase.PRESENT, SpatialArenaPhase.INTERACT}:
            raise ValueError("Spatial Arena interactions require a presented run")
        if len(run.interactions) >= MAX_SPATIAL_INTERACTIONS_PER_RUN:
            raise ValueError("Spatial Arena interaction ceiling reached")
        scene = self.session_manager.get_active_scene(run.session_id)
        intent = compile_spatial_interaction(
            scene,
            action=action,
            target_entity_ids=target_entity_ids,
            actor_ref=run.actor_ref,
            metadata=metadata,
        )
        run.interactions.append(intent)
        run.phase = SpatialArenaPhase.INTERACT
        result: dict[str, Any] = {**self.status(run_id), "intent": intent.to_dict()}
        if intent.action is SpatialInteractionAction.PREPARE_REPAIR_REQUEST:
            proposed = dict(metadata or {}).get("proposed_change_digest")
            result["coding_handoff"] = compile_hotswap_request_guard(
                scene,
                target_entity_ids=intent.target_entity_ids,
                proposed_change_digest=str(proposed or ""),
                actor_ref=run.actor_ref,
            )
        return result

    def prove(
        self,
        run_id: str,
        *,
        outcome: SpatialRenderOutcome | str,
        evidence_class: SpatialRenderEvidenceClass | str,
        metrics: Mapping[str, Any] | None = None,
        repo_head: str,
        branch_name: str = "",
    ) -> dict[str, Any]:
        run = self._get(run_id)
        if run.phase not in {SpatialArenaPhase.PRESENT, SpatialArenaPhase.INTERACT, SpatialArenaPhase.PROVE}:
            raise ValueError("Spatial Arena proof requires a presented or interacted run")
        evidence = _enum(evidence_class, SpatialRenderEvidenceClass, "evidence_class")
        if evidence is SpatialRenderEvidenceClass.MEASURED:
            raise ValueError("MEASURED evidence requires the validated browser telemetry path")
        receipt, _ = self.session_manager.record_render(
            run.session_id,
            outcome=outcome,
            evidence_class=evidence,
            metrics=dict(metrics or {}),
            renderer_disposed=False,
        )
        return self._finalize_proof(
            run,
            receipt,
            repo_head=repo_head,
            branch_name=branch_name,
            request={
                "run_id": run.run_id,
                "proof_kind": "DECLARED_OR_DERIVED",
                "outcome": receipt.outcome.value,
                "evidence_class": receipt.evidence_class.value,
            },
        )

    def prove_browser_telemetry(
        self,
        run_id: str,
        *,
        telemetry_packet: Mapping[str, Any],
        repo_head: str,
        branch_name: str = "",
    ) -> dict[str, Any]:
        run = self._get(run_id)
        if run.phase not in {SpatialArenaPhase.PRESENT, SpatialArenaPhase.INTERACT, SpatialArenaPhase.PROVE}:
            raise ValueError("Spatial browser telemetry requires a presented or interacted run")
        if not isinstance(telemetry_packet, Mapping):
            raise ValueError("telemetry_packet must be an object")
        receipt, _ = self.session_manager.record_browser_telemetry(run.session_id, telemetry_packet)
        return self._finalize_proof(
            run,
            receipt,
            repo_head=repo_head,
            branch_name=branch_name,
            request={
                "run_id": run.run_id,
                "proof_kind": "VALIDATED_BROWSER_TELEMETRY",
                "fixture_digest": str(telemetry_packet.get("fixture_digest") or ""),
                "evidence_class": receipt.evidence_class.value,
            },
        )

    def _finalize_proof(
        self,
        run: _SpatialArenaRun,
        receipt: Any,
        *,
        repo_head: str,
        branch_name: str,
        request: Mapping[str, Any],
    ) -> dict[str, Any]:
        run.proof_receipt_ids.append(receipt.receipt_id)
        run.phase = SpatialArenaPhase.PROVE
        checkpoint = self.persistence.checkpoint_spatial(
            self.checkpoint_projection(run.run_id),
            repo_head=repo_head,
            parent_checkpoint_id=run.checkpoint_id,
            branch_name=branch_name,
            created_at=float(self._now()),
        )
        run.checkpoint_id = str(dict(checkpoint["checkpoint"])["checkpoint_id"])
        archive = self.attempt_archive.record(
            arena_id="spatial_arena",
            route="spatial/prove",
            request=dict(request),
            result={
                "ok": True,
                "status": "PROVED",
                "receipt": receipt.to_dict(),
                "checkpoint_id": run.checkpoint_id,
            },
            workflow_state={
                "workflow_id": run.run_id,
                "current_phase": run.phase.value,
                "objective": run.objective,
            },
            archive_context={
                "domain_owner": run.domain_owner,
                "domain_state_digest": run.domain_state_digest,
            },
        )
        if archive.get("ok"):
            run.archive_artifact_ids.append(str(archive["artifact_id"]))
        return {
            **self.status(run.run_id),
            "render_receipt": receipt.to_dict(),
            "checkpoint": checkpoint,
            "attempt_archive": archive,
        }

    def decide(self, run_id: str, *, decision: str, decision_ref: str = "human:pending") -> dict[str, Any]:
        run = self._require_phase(run_id, SpatialArenaPhase.PROVE)
        packet = {
            "ok": True,
            "version": SPATIAL_ARENA_VERSION,
            "run_id": run.run_id,
            "decision": _text(decision, "decision", maximum=2048),
            "decision_ref": _identifier(decision_ref, "decision_ref"),
            "domain_owner": run.domain_owner,
            "domain_state_digest": run.domain_state_digest,
            "scene_digest": run.scene.scene_digest if run.scene else "",
            "render_plan_digest": run.plan.render_plan_digest if run.plan else "",
            "proof_receipt_ids": list(run.proof_receipt_ids),
            "checkpoint_id": run.checkpoint_id,
            "human_or_domain_decision_required": True,
            "decision_applied": False,
            "domain_state_mutated": False,
            "production_mutation": False,
            "automatic_merge": False,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
        }
        packet["decision_digest"] = stable_digest(packet, digest_size=32)
        run.decision_packet = packet
        run.phase = SpatialArenaPhase.DECIDE
        return {**self.status(run_id), "decision_packet": packet}

    def dissolve(
        self,
        run_id: str,
        *,
        renderer_cleanup_receipt: Mapping[str, Any],
        reason_code: str = "SPATIAL_ARENA_COMPLETE",
    ) -> dict[str, Any]:
        run = self._get(run_id)
        if run.phase not in {
            SpatialArenaPhase.PRESENT,
            SpatialArenaPhase.INTERACT,
            SpatialArenaPhase.PROVE,
            SpatialArenaPhase.DECIDE,
        }:
            raise ValueError("Spatial Arena run cannot dissolve before presentation")
        cleanup = self._validate_renderer_cleanup(run, renderer_cleanup_receipt)
        receipt = self.session_manager.dissolve_session(
            run.session_id, reason_code=_identifier(reason_code, "reason_code")
        )
        run.lease.status = "released"
        run.phase = SpatialArenaPhase.DISSOLVE
        packet = {
            **self.status(run_id),
            "dissolution_receipt": receipt.to_dict(),
            "renderer_cleanup_receipt": cleanup,
            "renderer_cleanup_digest": stable_digest(cleanup, digest_size=32),
            "renderer_cleanup_observed": True,
            "renderer_allocated": cleanup["renderer_allocated"],
            "lease_released": run.lease.status == "released",
            "renderer_resources_released": cleanup["renderer_resources_released"],
            "renderer_resources_released_verified": False,
            "renderer_resource_boundary_satisfied": True,
            "raw_sensor_data_retained": False,
        }
        self._dissolved.append(packet)
        del self._runs[run.run_id]
        return packet

    def abort_unpresented(
        self,
        run_id: str,
        *,
        reason_code: str = "SPATIAL_PREPARATION_FAILED",
    ) -> dict[str, Any]:
        run = self._get(run_id)
        if run.session_id or run.phase in {
            SpatialArenaPhase.PRESENT,
            SpatialArenaPhase.INTERACT,
            SpatialArenaPhase.PROVE,
            SpatialArenaPhase.DECIDE,
        }:
            raise ValueError("abort_unpresented cannot discard a presented Spatial Arena run")
        run.lease.status = "released"
        run.phase = SpatialArenaPhase.DISSOLVE
        packet = {
            **self.status(run_id),
            "reason_code": _identifier(reason_code, "reason_code"),
            "renderer_cleanup_observed": False,
            "renderer_allocated": False,
            "renderer_resources_released": False,
            "renderer_resources_released_verified": False,
            "renderer_resource_boundary_satisfied": True,
            "lease_released": True,
            "session_created": False,
            "raw_sensor_data_retained": False,
        }
        self._dissolved.append(packet)
        del self._runs[run_id]
        return packet

    def checkpoint_projection(self, run_id: str) -> dict[str, Any]:
        run = self._get(run_id)
        return {
            "version": SPATIAL_ARENA_VERSION,
            "run_id": run.run_id,
            "phase": run.phase.value,
            "purpose_digest": run.purpose_digest,
            "privacy_class": run.privacy_class.value,
            "egress_policy": run.egress_policy.value,
            "admitted_worker_refs": list(run.admitted_worker_refs),
            "admitted_worker_capability_digests": dict(run.admitted_worker_capabilities),
            "domain_owner": run.domain_owner,
            "domain_state_digest": run.domain_state_digest,
            "scene_id": run.scene.scene_id if run.scene else "",
            "scene_digest": run.scene.scene_digest if run.scene else "",
            "render_plan_digest": run.plan.render_plan_digest if run.plan else "",
            "session_id": run.session_id,
            "interaction_ids": [item.interaction_id for item in run.interactions],
            "proof_receipt_ids": list(run.proof_receipt_ids),
            "admitted_asset_ids": list(run.admitted_asset_ids),
            "source_refs": list(run.source_refs),
            "grounding_refs": list(run.grounding_refs),
            "raw_domain_state_included": False,
            "raw_sensor_data_retained": False,
            "restore_mode": "ASSESSMENT_ONLY",
            "automatic_resume": False,
            "production_mutation": False,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
        }

    def observatory_projection(self, run_id: str) -> dict[str, Any]:
        run = self._get(run_id)
        checkpoint = self.persistence.observatory_projection(run.checkpoint_id) if run.checkpoint_id else None
        return {
            "ok": True,
            "version": SPATIAL_ARENA_VERSION,
            "run_id": run.run_id,
            "phase": run.phase.value,
            "route_manifest_digest": self.route_manifest_digest,
            "purpose_digest": run.purpose_digest,
            "domain_owner": run.domain_owner,
            "domain_state_digest": run.domain_state_digest,
            "scene_digest": run.scene.scene_digest if run.scene else "",
            "render_plan_digest": run.plan.render_plan_digest if run.plan else "",
            "interaction_count": len(run.interactions),
            "proof_count": len(run.proof_receipt_ids),
            "lease_status": run.lease.status,
            "checkpoint": checkpoint,
            "cost_receipt": self.cost_receipt(run_id),
            "read_only": True,
            "payload_included": False,
            "domain_state_mutated": False,
            "patch_authority": PATCH_AUTHORITY,
        }

    def cost_receipt(self, run_id: str) -> dict[str, Any]:
        run = self._get(run_id)
        scene_bytes = sum(item.byte_length for item in run.scene.assets) if run.scene else 0
        packet = {
            "version": SPATIAL_ARENA_VERSION,
            "run_id": run.run_id,
            "phase": run.phase.value,
            "scene_entity_count": len(run.scene.entities) if run.scene else 0,
            "scene_link_count": len(run.scene.links) if run.scene else 0,
            "scene_asset_count": len(run.scene.assets) if run.scene else 0,
            "scene_asset_bytes": scene_bytes,
            "interaction_count": len(run.interactions),
            "proof_receipt_count": len(run.proof_receipt_ids),
            "external_worker_packet_count": run.worker_packet_count,
            "external_worker_packet_bytes_calculated": run.worker_packet_bytes,
            "measurement_class": "CALCULATED",
            "model_tokens": 0,
            "network_bytes_observed": 0,
            "production_authority": False,
        }
        packet["cost_receipt_digest"] = stable_digest(packet, digest_size=32)
        return packet

    def status(self, run_id: str) -> dict[str, Any]:
        run = self._get(run_id)
        return {
            "ok": True,
            "version": SPATIAL_ARENA_VERSION,
            "run_id": run.run_id,
            "phase": run.phase.value,
            "objective": run.objective,
            "purpose_digest": run.purpose_digest,
            "privacy_class": run.privacy_class.value,
            "egress_policy": run.egress_policy.value,
            "admitted_worker_refs": list(run.admitted_worker_refs),
            "admitted_worker_capability_digests": dict(run.admitted_worker_capabilities),
            "domain_owner": run.domain_owner,
            "domain_state_digest": run.domain_state_digest,
            "scene_digest": run.scene.scene_digest if run.scene else "",
            "render_plan_digest": run.plan.render_plan_digest if run.plan else "",
            "session_id": run.session_id,
            "interaction_count": len(run.interactions),
            "proof_receipt_count": len(run.proof_receipt_ids),
            "checkpoint_id": run.checkpoint_id,
            "lease_id": run.lease.lease_id,
            "lease_status": run.lease.status,
            "boundary_contract_id": run.boundary_contract.contract_id,
            "action_capsule_id": run.action_capsule.capsule_id,
            "raw_sensor_data_retained": False,
            "restore_assessment_only": True,
            "human_review_required": True,
            "renderer_authority": False,
            "execution_authority": False,
            "patch_authority": PATCH_AUTHORITY,
            "automatic_merge": False,
        }

    @staticmethod
    def _validate_renderer_cleanup(run: _SpatialArenaRun, receipt: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(receipt, Mapping):
            raise ValueError("renderer_cleanup_receipt must be an object")
        packet = dict(receipt)
        required = {
            "state",
            "renderer_allocated",
            "evidence_class",
            "session_id",
            "scene_digest",
            "render_plan_digest",
            "renderer_authority",
            "execution_authority",
        }
        if not required.issubset(packet):
            raise ValueError(f"renderer cleanup receipt missing keys: {sorted(required - set(packet))}")
        if type(packet["renderer_allocated"]) is not bool:
            raise ValueError("renderer_allocated must be a boolean")
        if packet["evidence_class"] != "CLIENT_REPORTED":
            raise ValueError("renderer cleanup evidence must be labelled CLIENT_REPORTED")
        expected_state = "DISPOSED" if packet["renderer_allocated"] else "NOT_ALLOCATED"
        if packet["state"] != expected_state:
            if packet["renderer_allocated"]:
                raise ValueError("renderer_allocated=true requires DISPOSED state")
            raise ValueError("DISPOSED state requires renderer_allocated=true; otherwise use NOT_ALLOCATED")
        if packet["session_id"] != run.session_id:
            raise ValueError("renderer cleanup receipt is bound to another session")
        if run.scene is None or packet["scene_digest"] != run.scene.scene_digest:
            raise ValueError("renderer cleanup receipt is bound to another scene")
        if run.plan is None or packet["render_plan_digest"] != run.plan.render_plan_digest:
            raise ValueError("renderer cleanup receipt is bound to another render plan")
        if packet["renderer_authority"] is not False or packet["execution_authority"] is not False:
            raise ValueError("renderer cleanup receipt crossed an authority boundary")
        return {
            "state": expected_state,
            "renderer_allocated": packet["renderer_allocated"],
            "evidence_class": "CLIENT_REPORTED",
            "session_id": run.session_id,
            "scene_digest": run.scene.scene_digest,
            "render_plan_digest": run.plan.render_plan_digest,
            "renderer_authority": False,
            "execution_authority": False,
            "renderer_resources_released": packet["renderer_allocated"],
            "renderer_resources_released_verified": False,
            "raw_sensor_data_retained": False,
        }

    def close(
        self,
        *,
        renderer_cleanup_receipts: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Close owned resources without fabricating renderer-cleanup evidence.

        Runs with an observed, exact-bound renderer cleanup receipt follow the
        normal dissolution path. Other active sessions are cancelled and
        dissolved as abandoned projections, explicitly recording that renderer
        cleanup was not observed.
        """

        cleanup_by_run = dict(renderer_cleanup_receipts or {})
        unknown_cleanup_runs = set(cleanup_by_run) - set(self._runs)
        if unknown_cleanup_runs:
            raise ValueError(f"renderer cleanup receipts include unknown runs: {sorted(unknown_cleanup_runs)}")
        receipts: list[dict[str, Any]] = []
        for run_id in tuple(sorted(self._runs)):
            run = self._runs[run_id]
            cleanup = cleanup_by_run.get(run_id)
            if run.session_id and cleanup is not None:
                receipts.append(
                    self.dissolve(
                        run_id,
                        reason_code="SPATIAL_ARENA_CLOSE",
                        renderer_cleanup_receipt=cleanup,
                    )
                )
                continue
            if run.session_id:
                summary = self.session_manager.get_summary(run.session_id)
                if summary.active:
                    self.session_manager.cancel_session(
                        run.session_id,
                        reason="SPATIAL_ARENA_CLOSED_WITHOUT_RENDERER_CLEANUP_EVIDENCE",
                    )
                dissolution = self.session_manager.dissolve_session(
                    run.session_id,
                    reason_code="SPATIAL_ARENA_ABANDONED",
                )
                run.lease.status = "released"
                run.phase = SpatialArenaPhase.DISSOLVE
                packet = {
                    **self.status(run_id),
                    "dissolution_receipt": dissolution.to_dict(),
                    "renderer_cleanup_observed": False,
                    "renderer_allocation_state": "UNKNOWN",
                    "renderer_resources_released": False,
                    "renderer_resources_released_verified": False,
                    "renderer_resource_boundary_satisfied": False,
                    "lease_released": True,
                    "raw_sensor_data_retained": False,
                }
                receipts.append(packet)
                self._dissolved.append(packet)
            else:
                run.lease.status = "released"
                run.phase = SpatialArenaPhase.DISSOLVE
                receipts.append(
                    {
                        **self.status(run_id),
                        "renderer_cleanup_observed": False,
                        "renderer_allocated": False,
                        "renderer_resources_released": False,
                        "renderer_resources_released_verified": False,
                        "renderer_resource_boundary_satisfied": True,
                        "lease_released": True,
                        "session_created": False,
                    }
                )
            del self._runs[run_id]
        if self._owns_archive and not self._closed:
            self.attempt_archive.close()
        self._closed = True
        return tuple(receipts)

    def _get(self, run_id: str) -> _SpatialArenaRun:
        key = str(run_id or "").strip()
        run = self._runs.get(key)
        if run is None:
            raise KeyError(f"unknown or dissolved Spatial Arena run: {key}")
        return run

    def _require_phase(self, run_id: str, phase: SpatialArenaPhase) -> _SpatialArenaRun:
        run = self._get(run_id)
        if run.phase is not phase:
            raise ValueError(f"Spatial Arena run is in {run.phase.value}, expected {phase.value}")
        return run


def _text(value: Any, name: str, *, maximum: int) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    text = " ".join(value.split())
    if not text or len(text.encode("utf-8")) > maximum:
        raise ValueError(f"{name} is empty or exceeds {maximum} bytes")
    return text


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value.strip()):
        raise ValueError(f"{name} must be a canonical identifier")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    text = str(value or "").strip().lower()
    if not _DIGEST.fullmatch(text):
        raise ValueError(f"{name} must be a 32- or 64-character lowercase digest")
    return text


def _enum(value: Any, enum_type: type[Enum], name: str):
    try:
        return value if isinstance(value, enum_type) else enum_type(str(value))
    except ValueError as exc:
        raise ValueError(f"unsupported {name}: {value}") from exc


def _identifiers(values: Iterable[str], name: str, *, maximum: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be an iterable")
    unique: set[str] = set()
    for item in values:
        unique.add(_identifier(item, name))
        if len(unique) > maximum:
            raise ValueError(f"{name} exceeds {maximum} items")
    return tuple(sorted(unique))


def _worker_capabilities(
    values: Mapping[str, str] | None,
    *,
    admitted_worker_refs: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    if values is None:
        return ()
    if not isinstance(values, Mapping):
        raise ValueError("admitted_worker_capability_digests must be a mapping")
    if len(values) > 64:
        raise ValueError("admitted_worker_capability_digests exceeds 64 items")
    result = tuple(
        sorted(
            (
                _identifier(worker_ref, "admitted_worker_capability_digests key"),
                _digest(digest, "admitted_worker_capability_digests value"),
            )
            for worker_ref, digest in values.items()
        )
    )
    if len(result) > 64:
        raise ValueError("admitted_worker_capability_digests exceeds 64 items")
    if len({worker_ref for worker_ref, _ in result}) != len(result):
        raise ValueError("admitted_worker_capability_digests contains duplicate workers")
    return result


def _refs(values: Iterable[str], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be an iterable")
    unique: set[str] = set()
    estimated_bytes = 2
    for item in values:
        text = str(item).strip()
        if not text or text in unique:
            continue
        unique.add(text)
        if len(unique) > MAX_SPATIAL_GROUNDING_REFS:
            raise ValueError(f"{name} exceeds the reference cap")
        estimated_bytes += len(text.encode("utf-8")) + 3
        if estimated_bytes > MAX_SPATIAL_GROUNDING_BYTES:
            raise ValueError(f"{name} exceeds the byte cap")
    result = tuple(sorted(unique))
    if len(canonical_json(list(result)).encode("utf-8")) > MAX_SPATIAL_GROUNDING_BYTES:
        raise ValueError(f"{name} exceeds the byte cap")
    return result


__all__ = [
    "SPATIAL_ARENA_VERSION",
    "SPATIAL_ROUTE_PATH",
    "SpatialArena",
    "SpatialArenaPhase",
    "SpatialEgressPolicy",
    "SpatialPrivacyClass",
]
