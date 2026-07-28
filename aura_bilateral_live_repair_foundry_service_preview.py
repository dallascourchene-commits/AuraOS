"""Isolated preview, canonical U7 delegation, and projection mixin."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
import time
from typing import Any

from aura_bilateral_live_repair_foundry_contracts import (
    MAX_ATTEMPTS, PROJECTION_VERSION, _FALSE_AUTHORITY, BilateralIdentity,
    BilateralLiveRepairError, PreviewRollbackReceipt, RepairCandidateResult,
    _digest_text, _required_text, canonical_sanitize, digest,
)


class _PreviewLearningProjectionMixin:
    def preview_candidate(
        self,
        *,
        packet_id: str,
        current_identity: BilateralIdentity,
        candidate_digest: str,
        last_verified_digest: str,
        health_before: Mapping[str, Any],
        health_after: Mapping[str, Any],
        environment_class: str,
        rollback_preauthorized: bool,
        rollback_reason: str = "",
        restore_local: Callable[[str], str] | None = None,
    ) -> PreviewRollbackReceipt:
        packet = self._packet(packet_id)
        packet.identity.assert_current(current_identity)
        candidate = _digest_text(candidate_digest, "candidate_digest")
        verified = _digest_text(last_verified_digest, "last_verified_digest")
        environment = _required_text(environment_class, "environment_class", limit=128).upper()
        if environment not in {"LOCAL_EPHEMERAL", "CANARY_ISOLATED"}:
            raise BilateralLiveRepairError("preview must be isolated from production")
        clean_before, _ = canonical_sanitize(health_before)
        clean_after, _ = canonical_sanitize(health_after)
        degraded = clean_after != clean_before and clean_after.get("ok") is not True
        executed = False
        restored = ""
        if degraded:
            if not rollback_reason.strip():
                raise ValueError("rollback_reason is required for degraded health")
            if rollback_preauthorized:
                if restore_local is None:
                    raise BilateralLiveRepairError("pre-authorized rollback requires an isolated restore adapter")
                restored = _digest_text(restore_local(verified), "restored_digest")
                if restored != verified:
                    raise BilateralLiveRepairError("rollback did not restore the exact last verified identity")
                executed = True
        identity = {
            "replay_packet_digest": packet.packet_digest,
            "bilateral_identity_digest": packet.identity.identity_digest,
            "candidate": candidate,
            "verified": verified,
            "before": clean_before,
            "after": clean_after,
            "environment": environment,
            "degraded": degraded,
            "rollback_preauthorized": bool(rollback_preauthorized),
            "executed": executed,
            "restored": restored,
        }
        key = digest(identity)
        receipt = PreviewRollbackReceipt(
            preview_id=f"PREVIEW-{key[:24]}",
            replay_packet_digest=packet.packet_digest,
            bilateral_identity_digest=packet.identity.identity_digest,
            candidate_digest=candidate,
            last_verified_digest=verified,
            health_before_digest=digest(clean_before),
            health_after_digest=digest(clean_after),
            environment_class=environment,
            preview_isolated=True,
            degraded=degraded,
            rollback_preauthorized=bool(rollback_preauthorized),
            technical_rollback_executed=executed,
            restored_digest=restored,
            rollback_reason=str(rollback_reason)[:1000],
            human_promotion_required=True,
            production_mutation=False,
            created_at=time.time(),
        )
        archive = self.attempt_archive.record(
            arena_id="coding",
            route="bilateral-live-repair/preview-rollback",
            request={
                "action_id": "preview_repair_candidate",
                "packet_id": packet.packet_id,
                "candidate_digest": candidate,
                "last_verified_digest": verified,
            },
            result={"ok": not degraded or executed, "status": "ROLLED_BACK" if executed else "PREVIEWED", "preview": receipt.to_dict()},
            workflow_state={
                "workflow_id": packet.packet_id,
                "current_phase": "B13_PREVIEW_ROLLBACK",
                "objective": "Preview the candidate in isolation while retaining the last verified version",
            },
            archive_context={"stage_hint": "B13", "identity_digest": packet.identity.identity_digest},
        )
        if archive.get("ok") is not True:
            raise BilateralLiveRepairError("canonical Attempt Archive did not retain the preview/rollback receipt")
        self._previews[receipt.preview_id] = receipt
        return receipt

    def run_governed_u7(
        self,
        *,
        bridge: Any,
        plan_phase_hash: str,
        task_id: str,
        prediction_contract: Mapping[str, Any],
        observation_contract: Mapping[str, Any],
        finalization_contract: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Delegate the complete P0/P1/reproof/disposition path to its owner."""

        from aura_unified_memory_continuity_learning import (
            commit_bridge_prediction,
            finalize_bridge_learning,
            observe_bridge_prediction,
        )

        prediction = commit_bridge_prediction(
            bridge,
            plan_phase_hash=plan_phase_hash,
            task_id=task_id,
            contract=prediction_contract,
        )
        observation = observe_bridge_prediction(
            bridge,
            plan_phase_hash=plan_phase_hash,
            task_id=task_id,
            observation=observation_contract,
        )
        result = finalize_bridge_learning(
            bridge,
            plan_phase_hash=plan_phase_hash,
            task_id=task_id,
            contract=finalization_contract,
        )
        return {
            "ok": result.get("ok") is True,
            "prediction": prediction.to_dict(),
            "observation": observation.to_dict(),
            "finalization": result,
            "canonical_owner": "aura_unified_memory_continuity_learning",
            "automatic_crystallization": False,
            "automatic_promotion": False,
            "production_mutation": False,
        }

    def latest_preview(self, packet_id: str) -> PreviewRollbackReceipt | None:
        packet = self._packet(packet_id)
        for summary in self.attempt_archive.list(workflow_id=packet.packet_id, limit=MAX_ATTEMPTS + 8):
            if summary.get("route") != "bilateral-live-repair/preview-rollback":
                continue
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            raw = dict((artifact or {}).get("result") or {}).get("preview")
            if isinstance(raw, Mapping):
                receipt = PreviewRollbackReceipt.from_mapping(raw)
                if receipt.replay_packet_digest != packet.packet_digest:
                    raise BilateralLiveRepairError("archived preview belongs to another incident")
                self._previews[receipt.preview_id] = receipt
                return receipt
        return None

    def build_projection(
        self,
        *,
        packet_id: str,
        intent: Mapping[str, Any],
        plan: Mapping[str, Any],
        code_targets: Sequence[Mapping[str, Any]],
        attempts: Sequence[RepairCandidateResult | Mapping[str, Any]],
        preview: PreviewRollbackReceipt | Mapping[str, Any] | None,
        u7_result: Mapping[str, Any] | None,
        source_drilldown: Sequence[Mapping[str, Any]],
        receipt_drilldown: Sequence[Mapping[str, Any]],
        current_identity: BilateralIdentity,
    ) -> dict[str, Any]:
        packet = self._packet(packet_id)
        packet.identity.assert_current(current_identity)
        clean_intent, _ = canonical_sanitize(intent)
        clean_plan, _ = canonical_sanitize(plan)
        clean_targets, _ = canonical_sanitize(code_targets)
        clean_source, _ = canonical_sanitize(source_drilldown)
        clean_receipts, _ = canonical_sanitize(receipt_drilldown)
        attempt_rows = [item.to_dict() if isinstance(item, RepairCandidateResult) else dict(item) for item in attempts]
        preview_row = preview.to_dict() if isinstance(preview, PreviewRollbackReceipt) else (dict(preview) if preview else None)
        u7 = dict(u7_result or {})
        projection = {
            "version": PROJECTION_VERSION,
            "projection_only": True,
            "stale": False,
            "identity": {**asdict(packet.identity), "identity_digest": packet.identity.identity_digest},
            "confirmed_intent": clean_intent,
            "negative_intent": list(packet.expected_negative),
            "guardrails": list(packet.preservation_claims),
            "plan": clean_plan,
            "code_targets": clean_targets,
            "live_runtime": {
                "release_id": packet.release_id,
                "environment_id": packet.environment_id,
                "capture_id": packet.capture_id,
                "event_count": len(packet.events),
                "total_event_count": packet.total_event_count,
            },
            "incident": packet.to_dict(),
            "failures": [item for item in attempt_rows if item.get("promotion_ready") is not True],
            "counterexamples": [item.get("minimized_counterexample") for item in attempt_rows if item.get("minimized_counterexample")],
            "repair_attempts": attempt_rows,
            "preview_rollback": preview_row,
            "proof": {
                "incident_packet_digest": packet.packet_digest,
                "u7": u7,
                "p0": u7.get("prediction"),
                "p1": u7.get("observation"),
            },
            "human_community_disposition": (
                dict(u7.get("finalization") or {}).get("human_disposition") if u7 else None
            ),
            "source_drilldown": clean_source,
            "receipt_drilldown": clean_receipts,
            "authority": {**_FALSE_AUTHORITY, "human_review_required": True},
        }
        projection["projection_digest"] = digest(projection)
        return projection


__all__ = ["_PreviewLearningProjectionMixin"]
