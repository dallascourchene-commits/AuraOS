from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from aura_spatial_contracts import (
    CoordinateFrame,
    SpatialEntity,
    SpatialEntityType,
    SpatialRenderEvidenceClass,
    SpatialRenderOutcome,
    SpatialSessionState,
)
from aura_spatial_receipts import (
    validate_spatial_dissolution_receipt_payload,
    validate_spatial_render_receipt_payload,
)
from aura_spatial_render_plan import (
    compile_spatial_device_profile,
    negotiate_spatial_render_plan,
)
from aura_spatial_scene import compile_spatial_scene
from aura_spatial_session import (
    SpatialProjectionSessionManager,
    validate_spatial_projection_session_summary_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _bound():
    scene = compile_spatial_scene(
        scene_id="session-scene",
        purpose_digest="purpose:session",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
        entities=(
            SpatialEntity(
                entity_id="entity:one",
                entity_type=SpatialEntityType.DOMAIN_NODE,
                label="One",
                frame_id="root",
                source_refs=("source:one",),
            ),
        ),
    )
    device = compile_spatial_device_profile(
        profile_id="device:session",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        source_refs=("source:device",),
    )
    return scene, device, negotiate_spatial_render_plan(scene, device)


def _browser_packet(plan, device):
    return {
        "version": "AURA_SPATIAL_BROWSER_TELEMETRY_V1",
        "scene_digest": plan.scene_digest,
        "render_plan_digest": plan.render_plan_digest,
        "device_profile_digest": device.device_profile_digest,
        "fixture_digest": "f" * 64,
        "renderer": "WEBGL2",
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


def test_session_binds_scene_plan_device_and_dissolves_without_retention():
    scene, device, plan = _bound()
    manager = SpatialProjectionSessionManager()
    summary = manager.create_session(scene, plan, device)
    assert summary.state is SpatialSessionState.ACTIVE
    assert summary.ephemeral is True
    assert summary.raw_sensor_data_retained is False
    session_schema = json.loads((ROOT / "schemas/aura_spatial_session_summary.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(session_schema)
    Draft202012Validator(session_schema).validate(summary.to_dict())
    assert validate_spatial_projection_session_summary_payload(summary.to_dict()) == summary

    receipt, updated = manager.record_render(
        summary.session_id,
        outcome=SpatialRenderOutcome.PRESENTED,
        evidence_class=SpatialRenderEvidenceClass.MEASURED,
        metrics={"frame_ms": 12.5, "source": "headless-fixture"},
    )
    assert updated.render_receipt_ids == (receipt.receipt_id,)
    assert validate_spatial_render_receipt_payload(receipt.to_dict()) == receipt

    dissolution = manager.dissolve_session(summary.session_id)
    assert dissolution.terminal_state is SpatialSessionState.DISSOLVED
    assert dissolution.renderer_disposed is True
    assert dissolution.leases_released is True
    assert dissolution.raw_sensor_data_retained is False
    assert manager.active_session_count == 0
    with pytest.raises(KeyError):
        manager.get_summary(summary.session_id)
    dissolution_schema = json.loads(
        (ROOT / "schemas/aura_spatial_dissolution_receipt.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(dissolution_schema)
    Draft202012Validator(dissolution_schema).validate(dissolution.to_dict())
    assert validate_spatial_dissolution_receipt_payload(dissolution.to_dict()) == dissolution


def test_cancel_then_dissolve_preserves_cancelled_terminal_evidence():
    scene, device, plan = _bound()
    manager = SpatialProjectionSessionManager()
    summary = manager.create_session(scene, plan, device)
    cancelled = manager.cancel_session(summary.session_id, reason="USER_EXIT")
    assert cancelled.state is SpatialSessionState.CANCELLED
    assert cancelled.active is False
    dissolution = manager.dissolve_session(
        summary.session_id,
        reason_code="USER_EXIT",
    )
    assert dissolution.terminal_state is SpatialSessionState.CANCELLED
    assert dissolution.production_mutation is False
    assert dissolution.automatic_merge is False


def test_stale_scene_or_device_binding_fails_closed():
    scene, device, plan = _bound()
    changed = compile_spatial_scene(
        scene_id=scene.scene_id,
        purpose_digest="purpose:changed",
        root_frame_id="root",
        frames=(CoordinateFrame(frame_id="root"),),
    )
    manager = SpatialProjectionSessionManager()
    with pytest.raises(ValueError, match="stale"):
        manager.create_session(changed, plan, device)

    other_device = compile_spatial_device_profile(
        profile_id="device:other",
        supported_renderers=("ACCESSIBLE_2D",),
    )
    with pytest.raises(ValueError, match="another device"):
        manager.create_session(scene, plan, other_device)


def test_render_metrics_cannot_smuggle_authority():
    scene, device, plan = _bound()
    manager = SpatialProjectionSessionManager()
    summary = manager.create_session(scene, plan, device)
    with pytest.raises(ValueError, match="protected authority"):
        manager.record_render(
            summary.session_id,
            outcome="PRESENTED",
            evidence_class="MEASURED",
            metrics={"automaticMerge": False},
        )


def test_render_receipt_schema_and_runtime_reject_digest_tampering():
    scene, device, plan = _bound()
    manager = SpatialProjectionSessionManager()
    summary = manager.create_session(scene, plan, device)
    receipt, _ = manager.record_render(
        summary.session_id,
        outcome="PRESENTED",
        evidence_class="DERIVED",
        metrics={},
    )
    payload = receipt.to_dict()
    schema = json.loads((ROOT / "schemas/aura_spatial_render_receipt.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    tampered = deepcopy(payload)
    tampered["sequence"] += 1
    with pytest.raises(ValueError, match="not canonical"):
        validate_spatial_render_receipt_payload(tampered)


def test_receipt_identity_uses_sanitized_metrics_and_canonical_release_sets():
    from aura_spatial_receipts import (
        compile_spatial_dissolution_receipt,
        compile_spatial_render_receipt,
    )

    scene, device, plan = _bound()
    first = compile_spatial_render_receipt(
        plan,
        device,
        outcome="PRESENTED",
        evidence_class="DERIVED",
        sequence=1,
        metrics={"api_key": "alpha-secret"},
    )
    second = compile_spatial_render_receipt(
        plan,
        device,
        outcome="PRESENTED",
        evidence_class="DERIVED",
        sequence=1,
        metrics={"api_key": "beta-secret"},
    )
    assert first.receipt_id == second.receipt_id
    assert first.render_receipt_digest == second.render_receipt_digest
    assert "alpha-secret" not in json.dumps(first.to_dict())
    assert "beta-secret" not in json.dumps(second.to_dict())

    manager = SpatialProjectionSessionManager()
    summary = manager.create_session(scene, plan, device)
    release_a = compile_spatial_dissolution_receipt(
        summary,
        reason_code="TEST_COMPLETE",
        sequence=2,
        released_asset_ids=("asset:z", "asset:a"),
    )
    release_b = compile_spatial_dissolution_receipt(
        summary,
        reason_code="TEST_COMPLETE",
        sequence=2,
        released_asset_ids=("asset:a", "asset:z"),
    )
    assert release_a.receipt_id == release_b.receipt_id
    assert release_a.released_asset_ids == ("asset:a", "asset:z")


def test_browser_telemetry_is_bound_to_active_session_and_global_sequence():
    scene, device, plan = _bound()
    manager = SpatialProjectionSessionManager()
    summary = manager.create_session(scene, plan, device)

    receipt, updated = manager.record_browser_telemetry(
        summary.session_id,
        _browser_packet(plan, device),
    )
    assert receipt.sequence > summary.updated_sequence
    assert updated.render_receipt_ids == (receipt.receipt_id,)
    assert receipt.to_dict()["metrics"]["fixture_digest"] == "f" * 64
    assert receipt.renderer_authority is False

    manager.cancel_session(summary.session_id)
    with pytest.raises(ValueError, match="active session"):
        manager.record_browser_telemetry(summary.session_id, _browser_packet(plan, device))
