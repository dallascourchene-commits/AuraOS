"""Ephemeral, digest-bound projection sessions for Aura spatial rendering."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import threading
from typing import Any

from aura_event_contracts import stable_digest
from aura_spatial_contracts import (
    PATCH_AUTHORITY,
    SpatialDeviceProfile,
    SpatialDissolutionReceipt,
    SpatialProjectionSessionSummary,
    SpatialRenderEvidenceClass,
    SpatialRenderOutcome,
    SpatialRenderPlan,
    SpatialRenderReceipt,
    SpatialSceneSnapshot,
    SpatialSessionState,
)
from aura_spatial_receipts import (
    compile_spatial_browser_telemetry_receipt,
    compile_spatial_dissolution_receipt,
    compile_spatial_render_receipt,
)

SPATIAL_SESSION_VERSION = "AURA_SPATIAL_SESSION_V1"
MAX_ACTIVE_SPATIAL_SESSIONS = 64
MAX_SESSION_RENDER_RECEIPTS = 256
MAX_DISSOLUTION_RECEIPTS = 256

_SESSION_SUMMARY_KEYS = frozenset(
    {
        "session_id",
        "scene_id",
        "scene_digest",
        "plan_id",
        "render_plan_digest",
        "renderer",
        "state",
        "created_sequence",
        "updated_sequence",
        "render_receipt_ids",
        "cancellation_reason",
        "source_refs",
        "active",
        "ephemeral",
        "raw_sensor_data_retained",
        "renderer_authority",
        "execution_authority",
        "patch_authority",
        "version",
        "schema_version",
        "session_digest",
    }
)


@dataclass
class _SessionRecord:
    scene: SpatialSceneSnapshot
    plan: SpatialRenderPlan
    device: SpatialDeviceProfile
    summary: SpatialProjectionSessionSummary
    receipts: list[SpatialRenderReceipt]


class SpatialProjectionSessionManager:
    """Own bounded in-memory projection lifecycles and cleanup receipts only."""

    def __init__(
        self,
        *,
        max_active_sessions: int = MAX_ACTIVE_SPATIAL_SESSIONS,
        max_dissolution_receipts: int = MAX_DISSOLUTION_RECEIPTS,
    ) -> None:
        if type(max_active_sessions) is not int or not 1 <= max_active_sessions <= 1024:
            raise ValueError("max_active_sessions must be an integer in 1..1024")
        if type(max_dissolution_receipts) is not int or not 1 <= max_dissolution_receipts <= 4096:
            raise ValueError("max_dissolution_receipts must be an integer in 1..4096")
        self._max_active_sessions = max_active_sessions
        self._max_dissolution_receipts = max_dissolution_receipts
        self._sequence = 0
        self._records: dict[str, _SessionRecord] = {}
        self._dissolutions: list[SpatialDissolutionReceipt] = []
        self._lock = threading.RLock()

    @property
    def active_session_count(self) -> int:
        with self._lock:
            return len(self._records)

    def create_session(
        self,
        scene: SpatialSceneSnapshot,
        plan: SpatialRenderPlan,
        device: SpatialDeviceProfile,
    ) -> SpatialProjectionSessionSummary:
        self._validate_bindings(scene, plan, device)
        with self._lock:
            if len(self._records) >= self._max_active_sessions:
                raise ValueError("active spatial session ceiling reached")
            sequence = self._next_sequence()
            session_id = "spatial-session:" + stable_digest(
                {
                    "sequence": sequence,
                    "scene_digest": scene.scene_digest,
                    "render_plan_digest": plan.render_plan_digest,
                    "device_profile_digest": device.device_profile_digest,
                },
                digest_size=12,
            )
            summary = SpatialProjectionSessionSummary(
                session_id=session_id,
                scene_id=scene.scene_id,
                scene_digest=scene.scene_digest,
                plan_id=plan.plan_id,
                render_plan_digest=plan.render_plan_digest,
                renderer=plan.selected_renderer,
                state=SpatialSessionState.ACTIVE,
                created_sequence=sequence,
                updated_sequence=sequence,
                render_receipt_ids=(),
                cancellation_reason="",
                source_refs=tuple(
                    sorted(
                        {
                            *scene.source_refs,
                            *plan.source_refs,
                            *device.source_refs,
                            "owner:aura_spatial_session.SpatialProjectionSessionManager",
                        }
                    )
                ),
                active=True,
                ephemeral=True,
                raw_sensor_data_retained=False,
                renderer_authority=False,
                execution_authority=False,
                patch_authority=False,
            )
            self._records[session_id] = _SessionRecord(
                scene=scene,
                plan=plan,
                device=device,
                summary=summary,
                receipts=[],
            )
            return summary

    def get_summary(self, session_id: str) -> SpatialProjectionSessionSummary:
        with self._lock:
            return self._record(session_id).summary

    def get_scene(self, session_id: str) -> SpatialSceneSnapshot:
        with self._lock:
            return self._record(session_id).scene

    def get_active_scene(self, session_id: str) -> SpatialSceneSnapshot:
        """Return the scene only while its projection session is active."""

        with self._lock:
            record = self._record(session_id)
            if record.summary.state is not SpatialSessionState.ACTIVE:
                raise ValueError("spatial interaction requires an active session")
            return record.scene

    def get_plan(self, session_id: str) -> SpatialRenderPlan:
        with self._lock:
            return self._record(session_id).plan

    def get_device(self, session_id: str) -> SpatialDeviceProfile:
        with self._lock:
            return self._record(session_id).device

    def list_active_summaries(self) -> tuple[SpatialProjectionSessionSummary, ...]:
        with self._lock:
            return tuple(self._records[key].summary for key in sorted(self._records))

    def record_render(
        self,
        session_id: str,
        *,
        outcome: SpatialRenderOutcome | str,
        evidence_class: SpatialRenderEvidenceClass | str,
        metrics: dict[str, Any] | None = None,
        renderer_disposed: bool = False,
    ) -> tuple[SpatialRenderReceipt, SpatialProjectionSessionSummary]:
        with self._lock:
            record = self._record(session_id)
            if record.summary.state is not SpatialSessionState.ACTIVE:
                raise ValueError("render evidence requires an active session")
            if len(record.receipts) >= MAX_SESSION_RENDER_RECEIPTS:
                raise ValueError("session render receipt ceiling reached")
            sequence = self._next_sequence()
            receipt = compile_spatial_render_receipt(
                record.plan,
                record.device,
                outcome=outcome,
                evidence_class=evidence_class,
                sequence=sequence,
                metrics=metrics,
                renderer_disposed=renderer_disposed,
                source_refs=(f"session:{record.summary.session_id}#{record.summary.session_digest}",),
            )
            record.receipts.append(receipt)
            record.summary = replace(
                record.summary,
                updated_sequence=sequence,
                render_receipt_ids=tuple(item.receipt_id for item in record.receipts),
            )
            return receipt, record.summary

    def record_browser_telemetry(
        self,
        session_id: str,
        packet: Mapping[str, Any],
    ) -> tuple[SpatialRenderReceipt, SpatialProjectionSessionSummary]:
        """Bind one browser telemetry packet to the active session sequence."""

        if not isinstance(packet, Mapping):
            raise ValueError("browser telemetry packet must be an object")
        with self._lock:
            record = self._record(session_id)
            if record.summary.state is not SpatialSessionState.ACTIVE:
                raise ValueError("browser telemetry requires an active session")
            if len(record.receipts) >= MAX_SESSION_RENDER_RECEIPTS:
                raise ValueError("session render receipt ceiling reached")
            sequence = self._next_sequence()
            receipt = compile_spatial_browser_telemetry_receipt(
                record.plan,
                record.device,
                packet,
                sequence=sequence,
            )
            record.receipts.append(receipt)
            record.summary = replace(
                record.summary,
                updated_sequence=sequence,
                render_receipt_ids=tuple(item.receipt_id for item in record.receipts),
            )
            return receipt, record.summary

    def cancel_session(
        self,
        session_id: str,
        *,
        reason: str = "USER_CANCELLED",
    ) -> SpatialProjectionSessionSummary:
        with self._lock:
            record = self._record(session_id)
            if record.summary.state is not SpatialSessionState.ACTIVE:
                raise ValueError("only an active session can be cancelled")
            sequence = self._next_sequence()
            record.summary = replace(
                record.summary,
                state=SpatialSessionState.CANCELLED,
                updated_sequence=sequence,
                cancellation_reason=str(reason or "USER_CANCELLED"),
                active=False,
            )
            return record.summary

    def fail_session(
        self,
        session_id: str,
        *,
        reason: str = "RENDER_FAILED",
    ) -> SpatialProjectionSessionSummary:
        with self._lock:
            record = self._record(session_id)
            if record.summary.state is not SpatialSessionState.ACTIVE:
                raise ValueError("only an active session can fail")
            sequence = self._next_sequence()
            record.summary = replace(
                record.summary,
                state=SpatialSessionState.FAILED,
                updated_sequence=sequence,
                cancellation_reason=str(reason or "RENDER_FAILED"),
                active=False,
            )
            return record.summary

    def dissolve_session(
        self,
        session_id: str,
        *,
        reason_code: str = "SESSION_COMPLETE",
    ) -> SpatialDissolutionReceipt:
        with self._lock:
            record = self._record(session_id)
            sequence = self._next_sequence()
            previous_state = record.summary.state
            terminal_state = (
                previous_state
                if previous_state
                in {
                    SpatialSessionState.CANCELLED,
                    SpatialSessionState.FAILED,
                }
                else SpatialSessionState.DISSOLVED
            )
            receipt = compile_spatial_dissolution_receipt(
                record.summary,
                reason_code=reason_code,
                sequence=sequence,
                terminal_state=terminal_state,
                released_asset_ids=tuple(asset.asset_id for asset in record.scene.assets),
                source_refs=("owner:aura_spatial_session.dissolve_session",),
            )
            del self._records[session_id]
            self._dissolutions.append(receipt)
            if len(self._dissolutions) > self._max_dissolution_receipts:
                del self._dissolutions[: len(self._dissolutions) - self._max_dissolution_receipts]
            return receipt

    def dissolution_receipts(self) -> tuple[SpatialDissolutionReceipt, ...]:
        with self._lock:
            return tuple(self._dissolutions)

    def close(self) -> tuple[SpatialDissolutionReceipt, ...]:
        receipts: list[SpatialDissolutionReceipt] = []
        with self._lock:
            session_ids = tuple(sorted(self._records))
        for session_id in session_ids:
            receipts.append(
                self.dissolve_session(
                    session_id,
                    reason_code="SESSION_MANAGER_CLOSE",
                )
            )
        return tuple(receipts)

    def status_packet(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "version": SPATIAL_SESSION_VERSION,
                "active_session_count": len(self._records),
                "active_session_limit": self._max_active_sessions,
                "dissolution_receipt_count": len(self._dissolutions),
                "dissolution_receipt_limit": self._max_dissolution_receipts,
                "ephemeral": True,
                "raw_sensor_data_retained": False,
                "production_mutation": False,
                "automatic_merge": False,
                "renderer_authority": False,
                "execution_authority": False,
                "patch_authority": PATCH_AUTHORITY,
                "human_review_required": True,
            }

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _record(self, session_id: str) -> _SessionRecord:
        key = str(session_id or "").strip()
        record = self._records.get(key)
        if record is None:
            raise KeyError(f"unknown or dissolved spatial session: {key}")
        return record

    @staticmethod
    def _validate_bindings(
        scene: SpatialSceneSnapshot,
        plan: SpatialRenderPlan,
        device: SpatialDeviceProfile,
    ) -> None:
        if not isinstance(scene, SpatialSceneSnapshot):
            raise ValueError("scene must be a SpatialSceneSnapshot")
        if not isinstance(plan, SpatialRenderPlan):
            raise ValueError("plan must be a SpatialRenderPlan")
        if not isinstance(device, SpatialDeviceProfile):
            raise ValueError("device must be a SpatialDeviceProfile")
        if plan.scene_id != scene.scene_id or plan.scene_digest != scene.scene_digest:
            raise ValueError("render plan is stale or bound to another scene")
        if plan.device_profile_digest != device.device_profile_digest:
            raise ValueError("render plan is bound to another device profile")
        if plan.selected_renderer not in device.supported_renderers:
            raise ValueError("selected renderer is not supported by the device")


def validate_spatial_projection_session_summary_payload(
    payload: Mapping[str, Any],
) -> SpatialProjectionSessionSummary:
    if not isinstance(payload, Mapping):
        raise ValueError("session summary payload must be an object")
    supplied = set(payload)
    if supplied != _SESSION_SUMMARY_KEYS:
        raise ValueError(
            "session summary keys mismatch: "
            f"missing={sorted(_SESSION_SUMMARY_KEYS - supplied)}, "
            f"extra={sorted(supplied - _SESSION_SUMMARY_KEYS)}"
        )
    summary = SpatialProjectionSessionSummary(
        session_id=payload["session_id"],
        scene_id=payload["scene_id"],
        scene_digest=payload["scene_digest"],
        plan_id=payload["plan_id"],
        render_plan_digest=payload["render_plan_digest"],
        renderer=payload["renderer"],
        state=payload["state"],
        created_sequence=payload["created_sequence"],
        updated_sequence=payload["updated_sequence"],
        render_receipt_ids=tuple(payload["render_receipt_ids"]),
        cancellation_reason=payload["cancellation_reason"],
        source_refs=tuple(payload["source_refs"]),
        active=payload["active"],
        ephemeral=payload["ephemeral"],
        raw_sensor_data_retained=payload["raw_sensor_data_retained"],
        renderer_authority=payload["renderer_authority"],
        execution_authority=payload["execution_authority"],
        patch_authority=payload["patch_authority"],
        version=payload["version"],
        schema_version=payload["schema_version"],
    )
    if summary.to_dict() != dict(payload):
        raise ValueError("session summary payload is not canonical")
    return summary


__all__ = [
    "MAX_ACTIVE_SPATIAL_SESSIONS",
    "MAX_DISSOLUTION_RECEIPTS",
    "MAX_SESSION_RENDER_RECEIPTS",
    "SPATIAL_SESSION_VERSION",
    "SpatialProjectionSessionManager",
    "validate_spatial_projection_session_summary_payload",
]
