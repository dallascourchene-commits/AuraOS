"""Isolated preview, canonical U7 delegation, and projection mixin."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
import time
from typing import TYPE_CHECKING, Any, cast

from aura_bilateral_live_repair_foundry_contracts import (
    MAX_ATTEMPTS, PROJECTION_VERSION, _FALSE_AUTHORITY, BilateralIdentity,
    BilateralLiveRepairError, PreviewRollbackReceipt, RepairCandidateResult,
    _digest_text, _required_text, canonical_sanitize, digest,
)


class _PreviewLearningProjectionMixin:
    if TYPE_CHECKING:
        attempt_archive: Any
        _previews: dict[str, PreviewRollbackReceipt]

        def _packet(self, packet_id: str) -> Any: ...

        def _resolve_current_identity(
            self,
            expected: BilateralIdentity,
        ) -> BilateralIdentity: ...

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
        self._resolve_current_identity(packet.identity)
        candidate = _digest_text(candidate_digest, "candidate_digest")
        verified = _digest_text(last_verified_digest, "last_verified_digest")
        environment = _required_text(environment_class, "environment_class", limit=128).upper()
        if environment not in {"LOCAL_EPHEMERAL", "CANARY_ISOLATED"}:
            raise BilateralLiveRepairError("preview must be isolated from production")
        if type(rollback_preauthorized) is not bool:
            raise ValueError("rollback_preauthorized must be a boolean")
        clean_before, _ = canonical_sanitize(health_before)
        clean_after, _ = canonical_sanitize(health_after)
        before_digest = digest(clean_before)
        after_digest = digest(clean_after)
        degraded = clean_after != clean_before and clean_after.get("ok") is not True
        executed = False
        rollback_succeeded = False
        restored = ""
        rollback_failure = ""
        if degraded:
            if not rollback_reason.strip():
                raise ValueError("rollback_reason is required for degraded health")
            if rollback_preauthorized is True:
                if restore_local is None:
                    raise BilateralLiveRepairError("pre-authorized rollback requires an isolated restore adapter")
                executed = True
                try:
                    restored = _digest_text(restore_local(verified), "restored_digest")
                    if restored == verified:
                        rollback_succeeded = True
                    else:
                        rollback_failure = "rollback did not restore the exact last verified identity"
                except Exception as exc:
                    rollback_failure = (
                        f"{type(exc).__name__}: isolated restore adapter failed"
                    )[:1000]
        identity = {
            "replay_packet_digest": packet.packet_digest,
            "bilateral_identity_digest": packet.identity.identity_digest,
            "candidate_digest": candidate,
            "last_verified_digest": verified,
            "health_before_digest": before_digest,
            "health_after_digest": after_digest,
            "environment_class": environment,
            "degraded": degraded,
            "rollback_preauthorized": rollback_preauthorized,
            "technical_rollback_executed": executed,
            "rollback_succeeded": rollback_succeeded,
            "restored_digest": restored,
            "rollback_failure": rollback_failure,
        }
        key = digest(identity)
        receipt = PreviewRollbackReceipt(
            preview_id=f"PREVIEW-{key[:24]}",
            replay_packet_digest=packet.packet_digest,
            bilateral_identity_digest=packet.identity.identity_digest,
            candidate_digest=candidate,
            last_verified_digest=verified,
            health_before_digest=before_digest,
            health_after_digest=after_digest,
            environment_class=environment,
            preview_isolated=True,
            degraded=degraded,
            rollback_preauthorized=rollback_preauthorized,
            technical_rollback_executed=executed,
            rollback_succeeded=rollback_succeeded,
            restored_digest=restored,
            rollback_reason=str(rollback_reason)[:1000],
            rollback_failure=rollback_failure,
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
            result={
                "ok": not degraded or rollback_succeeded,
                "status": (
                    "ROLLED_BACK"
                    if rollback_succeeded
                    else "ROLLBACK_FAILED"
                    if executed
                    else "PREVIEWED"
                ),
                "preview": receipt.to_dict(),
            },
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
        if rollback_failure:
            raise BilateralLiveRepairError(rollback_failure)
        return receipt

    def run_governed_u7(
        self,
        *,
        packet_id: str,
        candidate_digest: str,
        current_identity: BilateralIdentity,
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

        packet = self._packet(packet_id)
        packet.identity.assert_current(current_identity)
        self._resolve_current_identity(packet.identity)
        candidate = _digest_text(candidate_digest, "candidate_digest")
        phase = _required_text(plan_phase_hash, "plan_phase_hash")
        task = _required_text(task_id, "task_id")
        session = None
        require_session = getattr(bridge, "_require_session", None)
        if callable(require_session):
            session = require_session(phase)
        retained_prediction = (
            dict(session.get("unified_prediction_packets") or {}).get(task)
            if isinstance(session, Mapping)
            else None
        )
        prediction = retained_prediction or commit_bridge_prediction(
            bridge,
            plan_phase_hash=phase,
            task_id=task,
            contract=prediction_contract,
        )
        retained_observation = (
            dict(session.get("unified_p1_observations") or {}).get(task)
            if isinstance(session, Mapping)
            else None
        )
        observation = retained_observation or observe_bridge_prediction(
            bridge,
            plan_phase_hash=phase,
            task_id=task,
            observation=observation_contract,
        )
        retained_result = (
            dict(session.get("unified_learning_results") or {}).get(task)
            if isinstance(session, Mapping)
            else None
        )
        result = retained_result or finalize_bridge_learning(
            bridge,
            plan_phase_hash=phase,
            task_id=task,
            contract=finalization_contract,
        )
        return {
            "ok": result.get("ok") is True,
            "prediction": (
                cast(Any, prediction).to_dict()
                if hasattr(prediction, "to_dict")
                else dict(cast(Mapping[str, Any], prediction))
            ),
            "observation": (
                cast(Any, observation).to_dict()
                if hasattr(observation, "to_dict")
                else dict(cast(Mapping[str, Any], observation))
            ),
            "finalization": result,
            "replay_packet_digest": packet.packet_digest,
            "bilateral_identity_digest": packet.identity.identity_digest,
            "candidate_digest": candidate,
            "plan_phase_hash": phase,
            "task_id": task,
            "canonical_owner": "aura_unified_memory_continuity_learning",
            "automatic_crystallization": False,
            "automatic_promotion": False,
            "production_mutation": False,
        }

    def latest_preview(self, packet_id: str) -> PreviewRollbackReceipt | None:
        packet = self._packet(packet_id)
        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/preview-rollback",
            limit=MAX_ATTEMPTS + 8,
        ):
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
        self._resolve_current_identity(packet.identity)
        # Validate caller shape, but derive displayed confirmed intent only from
        # the digest-bound incident packet rather than caller projection data.
        canonical_sanitize(intent)
        clean_intent = {
            "intent_digest": packet.identity.intent_digest,
            "expected_positive": list(packet.expected_positive),
            "expected_negative": list(packet.expected_negative),
            "preservation_claims": list(packet.preservation_claims),
        }
        clean_plan, _ = canonical_sanitize(plan)
        clean_targets, _ = canonical_sanitize(code_targets)
        clean_source, _ = canonical_sanitize(source_drilldown)
        clean_receipts, _ = canonical_sanitize(receipt_drilldown)
        parsed_attempts = [
            item if isinstance(item, RepairCandidateResult) else RepairCandidateResult.from_mapping(item)
            for item in attempts
        ]
        if any(item.replay_packet_digest != packet.packet_digest for item in parsed_attempts):
            raise BilateralLiveRepairError("repair projection includes an attempt from another incident")
        attempt_rows = [item.to_dict() for item in parsed_attempts]
        parsed_preview = (
            preview
            if isinstance(preview, PreviewRollbackReceipt)
            else PreviewRollbackReceipt.from_mapping(preview)
            if preview
            else None
        )
        if parsed_preview and parsed_preview.replay_packet_digest != packet.packet_digest:
            raise BilateralLiveRepairError("repair projection includes a preview from another incident")
        preview_row = parsed_preview.to_dict() if parsed_preview else None
        u7 = dict(u7_result or {})
        if u7:
            verified_candidates = {
                item.candidate_digest
                for item in parsed_attempts
                if item.promotion_ready is True
            }
            if (
                u7.get("replay_packet_digest") != packet.packet_digest
                or u7.get("bilateral_identity_digest") != packet.identity.identity_digest
                or u7.get("candidate_digest") not in verified_candidates
            ):
                raise BilateralLiveRepairError(
                    "U7 projection evidence is not bound to this incident and verified candidate"
                )
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
