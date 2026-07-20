from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_construction_adapter import (
    ConstructionAdvisoryLane,
    ConstructionArenaAdapter,
    ConstructionArenaMode,
)
from aura_construction_fixtures import build_sco_construction_demo_fixture
from aura_event_contracts import canonical_json, stable_digest
from aura_spatial_agent_bridge import AuraSpatialAgentBridge
from aura_spatial_arena import SpatialArena, SpatialEgressPolicy, SpatialPrivacyClass
from aura_spatial_construction import project_construction_state_to_scene
from aura_spatial_contracts import SpatialRenderBudget, SpatialRendererKind
from aura_spatial_mcp import SpatialArenaMCPTools
from aura_spatial_render_plan import compile_spatial_device_profile, negotiate_spatial_render_plan


def _repo(tmp_path: Path) -> Path:
    route_dir = tmp_path / ".aura" / "arena_routes"
    route_dir.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / ".aura" / "arena_routes" / "spatial.v1.json"
    (route_dir / "spatial.v1.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def _construction_packet():
    fixture = build_sco_construction_demo_fixture()
    packet = ConstructionArenaAdapter().build_runtime_packet(
        objective="coordinate safe alternative work",
        state=fixture.state,
        scope=fixture.focus_scope,
        candidates=fixture.candidates,
        now=10.0,
        mode=ConstructionArenaMode.SYNTHETIC,
        lane=ConstructionAdvisoryLane.ALTERNATIVE_WORK,
        probabilistic_signals=fixture.probabilistic_signals,
    )
    return fixture, packet


def _prepared(tmp_path: Path):
    fixture, packet = _construction_packet()
    arena = SpatialArena(_repo(tmp_path), now=lambda: 100.0)
    bridge = AuraSpatialAgentBridge(tmp_path, arena=arena)
    prepared = bridge.prepare_construction_projection(
        objective="coordinate safe alternative work",
        state=fixture.state,
        construction_runtime_packet=packet,
    )
    return fixture, packet, arena, bridge, prepared


def _external_planned(
    tmp_path: Path,
    *,
    network_allowed: bool = True,
    max_network_bytes: int = 1024 * 1024,
):
    fixture, construction_packet = _construction_packet()
    provisional_scene = project_construction_state_to_scene(
        fixture.state,
        construction_packet,
        purpose_digest="0" * 64,
        privacy_class=SpatialPrivacyClass.PROJECT,
    )
    arena = SpatialArena(_repo(tmp_path), now=lambda: 50.0)
    framed = arena.frame(
        objective="prepare a bounded external render baton",
        privacy_class=SpatialPrivacyClass.PROJECT,
        egress_policy=SpatialEgressPolicy.ADMITTED_RENDER_WORKER,
        admitted_asset_ids=tuple(asset.asset_id for asset in provisional_scene.assets),
        admitted_worker_refs=("worker:render-1",),
        admitted_worker_capability_digests={"worker:render-1": "b" * 64},
        source_refs=("fixture:external-render",),
    )
    run_id = framed["run_id"]
    arena.ground(
        run_id,
        domain_owner="aura_construction_state",
        domain_state_digest=fixture.state.state_digest,
        evidence_refs=(f"construction-state:{fixture.state.state_digest}",),
    )
    scene = project_construction_state_to_scene(
        fixture.state,
        construction_packet,
        purpose_digest=framed["purpose_digest"],
        privacy_class=SpatialPrivacyClass.PROJECT,
    )
    arena.compile_scene(run_id, scene)
    device = compile_spatial_device_profile(
        profile_id="external-render-worker",
        supported_renderers=(SpatialRendererKind.ACCESSIBLE_2D, SpatialRendererKind.HEADLESS),
        budget=SpatialRenderBudget(
            max_entities=4096,
            max_links=8192,
            max_assets=128,
            max_asset_bytes=128 * 1024 * 1024,
            max_cpu_ms_per_frame=50.0,
            max_gpu_bytes=256 * 1024 * 1024,
            max_network_bytes=max_network_bytes if network_allowed else 0,
        ),
        accessibility_required=True,
        network_allowed=network_allowed,
        source_refs=("fixture:external-render",),
    )
    plan = negotiate_spatial_render_plan(
        scene,
        device,
        preferred_renderers=(SpatialRendererKind.ACCESSIBLE_2D, SpatialRendererKind.HEADLESS),
    )
    return arena, run_id, scene, plan, device


def _cleanup(status: dict) -> dict:
    return {
        "state": "DISPOSED",
        "renderer_allocated": True,
        "evidence_class": "CLIENT_REPORTED",
        "session_id": status["session_id"],
        "scene_digest": status["scene_digest"],
        "render_plan_digest": status["render_plan_digest"],
        "renderer_authority": False,
        "execution_authority": False,
    }


def _telemetry(prepared: dict) -> dict:
    plan = prepared["render_plan"]
    return {
        "version": "AURA_SPATIAL_BROWSER_TELEMETRY_V1",
        "scene_digest": plan["scene_digest"],
        "render_plan_digest": plan["render_plan_digest"],
        "device_profile_digest": plan["device_profile_digest"],
        "fixture_digest": "f" * 64,
        "renderer": plan["selected_renderer"],
        "metrics": {
            "frame_ms": {
                "value": 8.0,
                "unit": "ms",
                "evidence_class": "MEASURED",
                "method": "performance.now",
            }
        },
        "projection_only": True,
        "renderer_authority": False,
        "execution_authority": False,
        "patch_authority": False,
        "production_mutation": False,
        "automatic_merge": False,
        "human_review_required": True,
    }


def test_spatial_route_manifest_compiles_and_has_full_governed_lifecycle(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = load_and_compile_arena_grammar(root / ".aura/arena_routes/spatial.v1.json")
    assert result.ok
    assert result.grammar is not None
    assert result.grammar.start_state == "FRAME"
    assert set(result.grammar.states) == {
        "FRAME",
        "GROUND",
        "COMPILE_SCENE",
        "PLAN_RENDER",
        "PRESENT",
        "INTERACT",
        "PROVE",
        "DECIDE",
        "DISSOLVE",
    }
    manifest = json.loads((root / ".aura/arena_routes/spatial.v1.json").read_text(encoding="utf-8"))
    transitions = {item["transition_id"]: item for item in manifest["transitions"]}
    present_guards = transitions["SPATIAL.PLAN_RENDER.PRESENT"]["hard_guards"]
    assert any(
        item.get("args", {}).get("capability") == "present through replaceable render adapters"
        for item in present_guards
    )
    assert "GUARD.HUMAN_APPROVAL" not in {item["id"] for item in transitions["SPATIAL.PROVE.DECIDE"]["hard_guards"]}
    assert manifest["terminal_states"] == ["DISSOLVE"]


def test_s5_construction_lifecycle_is_digest_bound_checkpointed_and_dissolved(tmp_path: Path) -> None:
    _, _, arena, bridge, prepared = _prepared(tmp_path)
    run_id = prepared["run_id"]
    assert prepared["status"]["phase"] == "PRESENT"
    assert prepared["status"]["lease_status"] == "active"
    assert prepared["domain_state_payload_included"] is False
    assert prepared["construction_event_payloads_included"] is False

    entity_id = prepared["scene"]["entities"][0]["entity_id"]
    interacted = bridge.interact(run_id, action="SELECT", target_entity_ids=(entity_id,))
    assert interacted["phase"] == "INTERACT"
    assert interacted["intent"]["review_only"] is True
    assert interacted["intent"]["execution_authority"] is False

    proved = bridge.prove(
        run_id,
        repo_head="a" * 40,
        metrics={"frame_ms": 4.0, "rendered_entities": len(prepared["scene"]["entities"])},
    )
    assert proved["phase"] == "PROVE"
    assert proved["checkpoint"]["checkpoint"]["arena_id"] == "spatial_arena"
    assert proved["checkpoint"]["checkpoint"]["payload"]["raw_domain_state_included"] is False
    assert proved["checkpoint"]["checkpoint"]["payload"]["restore_mode"] == "ASSESSMENT_ONLY"
    assert proved["attempt_archive"]["ok"] is True

    observatory = bridge.observatory(run_id)
    assert observatory["read_only"] is True
    assert observatory["payload_included"] is False
    assert observatory["cost_receipt"]["measurement_class"] == "CALCULATED"
    assert observatory["cost_receipt"]["network_bytes_observed"] == 0

    restore = bridge.restore_assessment(run_id, current_repo_head="a" * 40)
    assert restore["automatic_resume"] is False
    assert restore["target_arena_mutated"] is False
    assert restore["assessment"]["status"] in {"RESTORE_ADMISSIBLE", "RESTORATION_COUNCIL_REQUIRED"}

    decided = bridge.decide(run_id, decision="request authorized human Construction review")
    assert decided["phase"] == "DECIDE"
    assert decided["decision_packet"]["decision_applied"] is False
    assert decided["decision_packet"]["human_or_domain_decision_required"] is True

    status = bridge.status(run_id)
    dissolved = bridge.dissolve(run_id, renderer_cleanup_receipt=_cleanup(status))
    assert dissolved["phase"] == "DISSOLVE"
    assert dissolved["renderer_resources_released"] is True
    assert dissolved["renderer_resources_released_verified"] is False
    assert dissolved["renderer_resource_boundary_satisfied"] is True
    assert dissolved["renderer_cleanup_receipt"]["evidence_class"] == "CLIENT_REPORTED"
    assert dissolved["lease_released"] is True
    assert dissolved["raw_sensor_data_retained"] is False
    assert arena.session_manager.active_session_count == 0
    with pytest.raises(KeyError):
        bridge.status(run_id)


def test_s5_rejects_out_of_order_stale_and_networked_local_runs(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    arena = SpatialArena(root, now=lambda: 1.0)
    framed = arena.frame(objective="inspect", source_refs=("fixture",))
    with pytest.raises(ValueError, match="expected GROUND"):
        arena.compile_scene(framed["run_id"], object())
    with pytest.raises(ValueError, match="restricted or sensitive"):
        arena.frame(
            objective="inspect restricted",
            privacy_class=SpatialPrivacyClass.RESTRICTED,
            egress_policy=SpatialEgressPolicy.ADMITTED_RENDER_WORKER,
        )


def test_s5_repair_interaction_routes_to_forge_without_execution(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    entity_id = prepared["scene"]["entities"][0]["entity_id"]
    result = bridge.interact(
        prepared["run_id"],
        action="PREPARE_REPAIR_REQUEST",
        target_entity_ids=(entity_id,),
        metadata={"proposed_change_digest": "b" * 64},
    )
    handoff = result["coding_handoff"]
    assert handoff["ok"] is False
    assert handoff["next_owner"] == "aura_forge"
    assert handoff["queued"] is False
    assert handoff["success"] is False
    assert handoff["production_mutation"] is False
    assert handoff["automatic_merge"] is False


def test_generic_proof_cannot_claim_measured_browser_evidence(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    with pytest.raises(ValueError, match="validated browser telemetry"):
        bridge.prove(
            prepared["run_id"],
            repo_head="a" * 40,
            evidence_class="MEASURED",
            metrics={"frame_ms": 8.0},
        )


def test_validated_browser_telemetry_records_empirical_proof(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    proof = bridge.prove_browser_telemetry(
        prepared["run_id"],
        telemetry_packet=_telemetry(prepared),
        repo_head="a" * 40,
    )
    assert proof["render_receipt"]["evidence_class"] == "MEASURED"
    assert proof["render_receipt"]["metrics"]["fixture_digest"] == "f" * 64
    assert proof["attempt_archive"]["ok"] is True


def test_failed_construction_prepare_releases_unpresented_lease(tmp_path: Path) -> None:
    fixture, packet = _construction_packet()
    arena = SpatialArena(_repo(tmp_path), now=lambda: 100.0)
    bridge = AuraSpatialAgentBridge(tmp_path, arena=arena)
    stale = dict(packet)
    stale["state_digest"] = "0" * 32
    with pytest.raises(ValueError, match="stale"):
        bridge.prepare_construction_projection(
            objective="reject stale construction state",
            state=fixture.state,
            construction_runtime_packet=stale,
        )
    assert arena.session_manager.active_session_count == 0
    assert bridge.close() == ()


def test_present_requires_live_lease_capability(tmp_path: Path) -> None:
    arena, run_id, _scene, plan, device = _external_planned(tmp_path)
    arena.plan_render(run_id, plan=plan, device=device)
    arena._runs[run_id].lease.status = "released"
    with pytest.raises(ValueError, match="active lease"):
        arena.present(run_id)


def test_close_rejects_cleanup_for_unknown_run(tmp_path: Path) -> None:
    arena = SpatialArena(_repo(tmp_path), now=lambda: 1.0)
    with pytest.raises(ValueError, match="unknown runs"):
        arena.close(renderer_cleanup_receipts={"spatial-run:unknown": {}})


def test_s5_cleanup_receipt_must_match_exact_session_scene_and_plan(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    run_id = prepared["run_id"]
    bridge.prove(run_id, repo_head="c" * 40)
    bridge.decide(run_id, decision="review")
    status = bridge.status(run_id)
    stale = _cleanup(status)
    stale["scene_digest"] = "d" * 64
    with pytest.raises(ValueError, match="another scene"):
        bridge.dissolve(run_id, renderer_cleanup_receipt=stale)
    assert bridge.status(run_id)["lease_status"] == "active"


def test_s5_not_allocated_receipt_satisfies_boundary_without_release_claim(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    run_id = prepared["run_id"]
    bridge.prove(run_id, repo_head="e" * 40, metrics={"renderer_allocated": False})
    bridge.decide(run_id, decision="review")
    status = bridge.status(run_id)
    receipt = {
        "state": "NOT_ALLOCATED",
        "renderer_allocated": False,
        "evidence_class": "CLIENT_REPORTED",
        "session_id": status["session_id"],
        "scene_digest": status["scene_digest"],
        "render_plan_digest": status["render_plan_digest"],
        "renderer_authority": False,
        "execution_authority": False,
    }
    dissolved = bridge.dissolve(run_id, renderer_cleanup_receipt=receipt)
    assert dissolved["renderer_allocated"] is False
    assert dissolved["renderer_resources_released"] is False
    assert dissolved["renderer_resources_released_verified"] is False
    assert dissolved["renderer_resource_boundary_satisfied"] is True
    assert dissolved["lease_released"] is True


def test_s5_cleanup_receipt_rejects_unlabelled_or_inconsistent_claims(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    run_id = prepared["run_id"]
    status = bridge.status(run_id)
    receipt = _cleanup(status)
    receipt["evidence_class"] = "VERIFIED"
    with pytest.raises(ValueError, match="CLIENT_REPORTED"):
        bridge.dissolve(run_id, renderer_cleanup_receipt=receipt)
    receipt = _cleanup(status)
    receipt["renderer_allocated"] = False
    with pytest.raises(ValueError, match="renderer_allocated=true"):
        bridge.dissolve(run_id, renderer_cleanup_receipt=receipt)


def test_mcp_surface_is_narrow_and_cannot_prepare_untyped_domain_state(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    tools = SpatialArenaMCPTools(tmp_path, bridge=bridge)
    manifest = tools.tool_manifest()
    assert "spatial.status" in manifest["tools"]
    assert manifest["construction_prepare_requires_typed_python_contracts"] is True
    assert manifest["raw_sensor_payloads_accepted"] is False
    status = tools.call("spatial.status", {"run_id": prepared["run_id"]})
    assert status["phase"] == "PRESENT"
    with pytest.raises(ValueError, match="unknown Spatial MCP tool"):
        tools.call("spatial.mutate_domain", {"run_id": prepared["run_id"]})


def test_checkpoint_projection_is_payload_minimized(tmp_path: Path) -> None:
    _, _, arena, _, prepared = _prepared(tmp_path)
    projection = arena.checkpoint_projection(prepared["run_id"])
    encoded = json.dumps(projection, sort_keys=True)
    assert projection["raw_domain_state_included"] is False
    assert projection["raw_sensor_data_retained"] is False
    assert projection["restore_mode"] == "ASSESSMENT_ONLY"
    assert "events" not in projection
    assert "evidence" not in projection
    assert "actor_id" not in encoded
    assert "claimant_id" not in encoded


def test_static_clock_still_produces_unique_spatial_run_ids(tmp_path: Path) -> None:
    arena = SpatialArena(_repo(tmp_path), now=lambda: 1.0)
    first = arena.frame(objective="inspect the same projection")
    second = arena.frame(objective="inspect the same projection")
    assert first["run_id"] != second["run_id"]
    receipts = arena.close()
    assert len(receipts) == 2
    assert all(item["session_created"] is False for item in receipts)


def test_repeated_proofs_form_a_checkpoint_chain(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    run_id = prepared["run_id"]
    first = bridge.prove(run_id, repo_head="a" * 40)
    second = bridge.prove(run_id, repo_head="a" * 40)
    first_id = first["checkpoint"]["checkpoint"]["checkpoint_id"]
    assert second["checkpoint"]["checkpoint"]["parent_checkpoint_id"] == first_id
    status = bridge.status(run_id)
    bridge.dissolve(run_id, renderer_cleanup_receipt=_cleanup(status))
    bridge.close()


def test_close_never_fabricates_renderer_cleanup_evidence(tmp_path: Path) -> None:
    _, _, arena, bridge, prepared = _prepared(tmp_path)
    receipts = bridge.close()
    assert len(receipts) == 1
    assert receipts[0]["renderer_cleanup_observed"] is False
    assert receipts[0]["renderer_resources_released"] is False
    assert receipts[0]["renderer_resources_released_verified"] is False
    assert receipts[0]["renderer_resource_boundary_satisfied"] is False
    assert receipts[0]["lease_released"] is True
    assert receipts[0]["dissolution_receipt"]["renderer_disposed"] is False
    assert arena.session_manager.active_session_count == 0
    with pytest.raises(KeyError):
        bridge.status(prepared["run_id"])


def test_s5_external_egress_requires_explicit_workers_and_local_rejects_them(tmp_path: Path) -> None:
    arena = SpatialArena(_repo(tmp_path), now=lambda: 1.0)
    with pytest.raises(ValueError, match="requires at least one admitted worker"):
        arena.frame(
            objective="external render",
            egress_policy=SpatialEgressPolicy.ADMITTED_RENDER_WORKER,
        )
    with pytest.raises(ValueError, match="pre-admitted capability digest"):
        arena.frame(
            objective="external render",
            egress_policy=SpatialEgressPolicy.ADMITTED_RENDER_WORKER,
            admitted_asset_ids=("asset:one",),
            admitted_worker_refs=("worker:render-1",),
        )
    with pytest.raises(ValueError, match="pre-admitted assets"):
        arena.frame(
            objective="external render",
            egress_policy=SpatialEgressPolicy.ADMITTED_RENDER_WORKER,
            admitted_worker_refs=("worker:render-1",),
            admitted_worker_capability_digests={"worker:render-1": "b" * 64},
        )
    with pytest.raises(ValueError, match="cannot declare external workers"):
        arena.frame(
            objective="local render",
            admitted_worker_refs=("worker:render-1",),
        )


def test_s5_external_egress_requires_network_enabled_device_profile(tmp_path: Path) -> None:
    arena, run_id, _, plan, device = _external_planned(tmp_path, network_allowed=False)
    with pytest.raises(ValueError, match="network-enabled device profile"):
        arena.plan_render(run_id, plan=plan, device=device)


def test_s5_worker_baton_is_identity_bound_minimized_and_costed(tmp_path: Path) -> None:
    arena, run_id, _, plan, device = _external_planned(tmp_path)
    arena.plan_render(run_id, plan=plan, device=device)
    with pytest.raises(ValueError, match="not admitted"):
        arena.admitted_worker_packet(
            run_id,
            worker_ref="worker:other",
            worker_capability_digest="b" * 64,
        )
    with pytest.raises(ValueError, match="capability digest is not admitted"):
        arena.admitted_worker_packet(
            run_id,
            worker_ref="worker:render-1",
            worker_capability_digest="c" * 64,
        )

    packet = arena.admitted_worker_packet(
        run_id,
        worker_ref="worker:render-1",
        worker_capability_digest="b" * 64,
    )
    assert packet["worker_ref"] == "worker:render-1"
    assert packet["worker_capability_digest"] == "b" * 64
    assert packet["admitted_worker_refs"] == ["worker:render-1"]
    assert packet["admitted_worker_capability_digests"] == {"worker:render-1": "b" * 64}
    assert packet["payload_minimized"] is True
    assert packet["asset_uris_included"] is False
    assert packet["asset_metadata_included"] is False
    assert packet["asset_source_refs_included"] is False
    assert packet["asset_payloads_included"] is False
    assert packet["scene_entities_included"] is False
    assert all("uri" not in asset for asset in packet["assets"])
    assert all("metadata" not in asset for asset in packet["assets"])
    assert all("source_refs" not in asset for asset in packet["assets"])
    assert "entities" not in packet
    assert "links" not in packet
    assert "source_refs" not in packet
    assert "metadata" not in packet

    digest = packet["packet_digest"]
    body = dict(packet)
    body.pop("packet_digest")
    assert stable_digest(body, digest_size=32) == digest
    emitted_bytes = len(canonical_json(packet).encode("utf-8"))
    cost = arena.cost_receipt(run_id)
    assert cost["external_worker_packet_count"] == 1
    assert cost["external_worker_packet_bytes_calculated"] == emitted_bytes
    assert cost["network_bytes_observed"] == 0
    assert arena.status(run_id)["admitted_worker_refs"] == ["worker:render-1"]
    assert arena.checkpoint_projection(run_id)["admitted_worker_refs"] == ["worker:render-1"]


def test_s5_worker_baton_byte_ceiling_fails_before_accounting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    arena, run_id, _, plan, device = _external_planned(tmp_path)
    arena.plan_render(run_id, plan=plan, device=device)
    monkeypatch.setattr("aura_spatial_arena.MAX_SPATIAL_WORKER_PACKET_BYTES", 1)
    with pytest.raises(ValueError, match="byte ceiling"):
        arena.admitted_worker_packet(
            run_id,
            worker_ref="worker:render-1",
            worker_capability_digest="b" * 64,
        )
    cost = arena.cost_receipt(run_id)
    assert cost["external_worker_packet_count"] == 0
    assert cost["external_worker_packet_bytes_calculated"] == 0


def test_s5_worker_baton_respects_negotiated_network_budget(tmp_path: Path) -> None:
    arena, run_id, _, plan, device = _external_planned(tmp_path, max_network_bytes=512)
    arena.plan_render(run_id, plan=plan, device=device)
    with pytest.raises(ValueError, match="network byte ceiling"):
        arena.admitted_worker_packet(
            run_id,
            worker_ref="worker:render-1",
            worker_capability_digest="b" * 64,
        )
    assert arena.cost_receipt(run_id)["external_worker_packet_count"] == 0


def test_s5_external_worker_packets_enforce_cumulative_network_budget(tmp_path: Path) -> None:
    arena, run_id, _, plan, device = _external_planned(tmp_path, max_network_bytes=3500)
    arena.plan_render(run_id, plan=plan, device=device)
    first = arena.admitted_worker_packet(
        run_id,
        worker_ref="worker:render-1",
        worker_capability_digest="b" * 64,
    )
    assert len(canonical_json(first).encode("utf-8")) < 3500
    with pytest.raises(ValueError, match="network byte ceiling"):
        arena.admitted_worker_packet(
            run_id,
            worker_ref="worker:render-1",
            worker_capability_digest="b" * 64,
        )
    assert arena.cost_receipt(run_id)["external_worker_packet_count"] == 1


def test_spatial_arena_cannot_be_reused_after_close(tmp_path: Path) -> None:
    arena = SpatialArena(_repo(tmp_path), now=lambda: 1.0)
    run = arena.frame(objective="inspect once")
    receipts = arena.close()
    assert receipts[0]["phase"] == "DISSOLVE"
    assert receipts[0]["run_id"] == run["run_id"]
    assert arena.close() == ()
    with pytest.raises(RuntimeError, match="closed"):
        arena.frame(objective="inspect again")


def test_spatial_purpose_digest_binds_explicit_asset_admission(tmp_path: Path) -> None:
    first = SpatialArena(_repo(tmp_path / "first"), now=lambda: 1.0).frame(
        objective="inspect", admitted_asset_ids=("asset:one",)
    )
    second = SpatialArena(_repo(tmp_path / "second"), now=lambda: 1.0).frame(
        objective="inspect", admitted_asset_ids=("asset:two",)
    )
    assert first["purpose_digest"] != second["purpose_digest"]
