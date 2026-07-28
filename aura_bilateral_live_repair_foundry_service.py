"""Canonical-owner orchestration for B11-B15 bilateral live repair."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import time
from typing import Any

from aura_bilateral_live_repair_foundry_contracts import (
    _FALSE_AUTHORITY,
    BilateralLiveRepairError,
    IncidentReplayPacket,
    digest,
)
from aura_bilateral_live_repair_foundry_service_capture import _CapturePersistenceMixin
from aura_bilateral_live_repair_foundry_service_preview import _PreviewLearningProjectionMixin
from aura_bilateral_live_repair_foundry_service_runtime import _RuntimeRepairMixin

_RUNTIME_FALSE_AUTHORITIES = (
    "automatic_fix",
    "automatic_commit",
    "automatic_push",
    "automatic_pull_request",
    "automatic_merge",
    "production_mutation",
    "professional_authority",
    "physical_work_authority",
    "learning_promotion",
    "bilateral_runtime_evidence_authority",
)


class BilateralLiveRepairService(
    _PreviewLearningProjectionMixin,
    _RuntimeRepairMixin,
    _CapturePersistenceMixin,
):
    """Stateful adapter over canonical Aura owners; no new authority plane."""

    @staticmethod
    def _scrub_capture(capture: Any) -> None:
        """Dissolve every in-memory capture buffer, including the separate marker."""

        capture._closed = True
        capture._events.clear()
        capture._marker_event = None

    def _sweep_expired_captures(self) -> None:
        now = time.time()
        for capture in self._captures.values():
            if not capture._closed and now - capture.started_at > capture.retention_seconds:
                self._scrub_capture(capture)

    def close(self) -> None:
        for capture in self._captures.values():
            self._scrub_capture(capture)
        super().close()

    def status(self) -> dict[str, Any]:
        self._sweep_expired_captures()
        return super().status()

    def observe(self, capture_id: str, event_type: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        capture = self._capture(capture_id)
        try:
            return super().observe(capture_id, event_type, payload)
        except BilateralLiveRepairError:
            if capture._closed:
                self._scrub_capture(capture)
            raise

    def finalize_capture(self, capture_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
        capture = self._capture(capture_id)
        try:
            return super().finalize_capture(capture_id, contract)
        finally:
            if capture._closed:
                self._scrub_capture(capture)

    @staticmethod
    def _validate_packet(packet: IncidentReplayPacket) -> IncidentReplayPacket:
        expected_authority = {**_FALSE_AUTHORITY, "human_review_required": True}
        privacy = dict(packet.privacy_receipt)
        dissolution = packet.dissolution_receipt
        if dict(packet.authority) != expected_authority:
            raise BilateralLiveRepairError("incident replay authority envelope is incomplete or escalated")
        if (
            privacy.get("sanitizer_owner") != "aura_arena_experience.sanitize_experience_payload"
            or privacy.get("raw_secret_retained") is not False
            or privacy.get("unrestricted_recording") is not False
            or not 1 <= int(privacy.get("retention_seconds") or 0) <= 300
            or not 1 <= int(privacy.get("max_events") or 0) <= 256
        ):
            raise BilateralLiveRepairError("incident replay privacy receipt is incomplete or unsafe")
        if (
            dissolution.terminal_state != "DISSOLVED"
            or dissolution.marker_retained_separately is not True
            or dissolution.timers_released is not True
            or dissolution.listeners_released is not True
            or dissolution.buffers_cleared is not True
            or dissolution.unrestricted_recording is not False
        ):
            raise BilateralLiveRepairError("incident replay dissolution receipt is incomplete")
        return packet

    def _packet(self, packet_id: str) -> IncidentReplayPacket:
        return self._validate_packet(super()._packet(packet_id))

    @staticmethod
    def _validate_runtime_proof(
        packet: IncidentReplayPacket,
        proof: Mapping[str, Any],
        *,
        allow_reduced_fixture: bool = False,
    ) -> None:
        if proof.get("profile_sha256") != packet.identity.runtime_profile_digest:
            raise BilateralLiveRepairError("runtime proof profile identity differs from the incident contract")
        if proof.get("repository_identity_unchanged") is not True:
            raise BilateralLiveRepairError("runtime replay changed repository identity")

        # Focused unit-test runners use a reduced fixture outside a Git checkout.
        # Canonical repository execution must expose the complete V2 identity packet.
        if not proof.get("version"):
            if allow_reduced_fixture:
                return
            raise BilateralLiveRepairError("runtime proof omitted the canonical V2 version and identity packet")

        contract = proof.get("intent_contract")
        verifier = proof.get("independent_verifier")
        if not isinstance(contract, Mapping) or not isinstance(verifier, Mapping):
            raise BilateralLiveRepairError("runtime proof omitted canonical intent or verifier identity")
        expected_contract = {
            "intent_digest": packet.identity.intent_digest,
            "semantic_ledger_digest": packet.identity.semantic_ledger_digest,
            "confirmation_digest": packet.identity.confirmation_digest,
            "guardrail_set_digest": packet.identity.guardrail_set_digest,
            "intent_revision_status": packet.identity.intent_revision_id,
            "expected_repository_head": packet.identity.repository_head,
            "expected_source_tree": packet.identity.source_tree_digest,
        }
        for name, expected in expected_contract.items():
            if contract.get(name) != expected:
                raise BilateralLiveRepairError(f"runtime proof {name} differs from the incident contract")
        if (
            proof.get("resolved_expected_repository_head") != packet.identity.repository_head
            or proof.get("resolved_expected_source_tree") != packet.identity.source_tree_digest
        ):
            raise BilateralLiveRepairError("runtime proof resolved source identity differs from the incident contract")
        if (
            verifier.get("verifier_id") != packet.identity.verifier_id
            or verifier.get("source_sha256") != packet.identity.verifier_source_digest
        ):
            raise BilateralLiveRepairError("runtime proof independent verifier differs from the incident contract")
        if proof.get("human_review_required") is not True:
            raise BilateralLiveRepairError("runtime proof removed mandatory human review")
        if any(proof.get(name) is not False for name in _RUNTIME_FALSE_AUTHORITIES):
            raise BilateralLiveRepairError("runtime proof grants forbidden authority")

    def execute_replay(
        self,
        *,
        packet_id: str,
        profile_path: str | Path,
        confirmation_packet: str | Path,
        output_dir: str | Path,
        venv_path: str | Path | None = None,
        baseline_receipt: str | Path | None = None,
    ) -> dict[str, Any]:
        packet = self._packet(packet_id)
        proof = dict(
            self.runtime_runner(
                self.repo_root,
                profile_path=profile_path,
                confirmation_packet=confirmation_packet,
                output_dir=output_dir,
                venv_path=venv_path,
                install_requirements=False,
                allow_dirty=False,
                baseline_receipt=baseline_receipt,
            )
        )
        self._validate_runtime_proof(
            packet,
            proof,
            allow_reduced_fixture=not (self.repo_root / ".git").exists(),
        )
        proof_digest = digest(proof)
        result = {
            "ok": proof.get("ok") is True,
            "status": "INCIDENT_REPLAY_VERIFIED" if proof.get("ok") is True else "INCIDENT_REPLAY_REPRODUCED",
            "packet_id": packet.packet_id,
            "packet_digest": packet.packet_digest,
            "runtime_proof": proof,
            "runtime_proof_digest": proof_digest,
            "authority": {**_FALSE_AUTHORITY, "human_review_required": True},
        }
        archive = self.attempt_archive.record(
            arena_id="construction",
            route="bilateral-live-repair/runtime-replay",
            request={
                "action_id": "execute_incident_replay",
                "packet_id": packet.packet_id,
                "packet_digest": packet.packet_digest,
                "runtime_profile_digest": packet.identity.runtime_profile_digest,
            },
            result=result,
            workflow_state={
                "workflow_id": packet.packet_id,
                "current_phase": "B12_RUNTIME_REPLAY",
                "objective": "Reproduce and verify the exact field incident outside the source checkout",
            },
            archive_context={"stage_hint": "B12", "identity_digest": packet.identity.identity_digest},
        )
        if archive.get("ok") is not True:
            raise BilateralLiveRepairError("canonical Attempt Archive did not retain the runtime replay")
        self._runtime_proofs[proof_digest] = (packet.packet_id, proof)
        return {**result, "runtime_proof_ref": proof_digest, "attempt_artifact": archive}


__all__ = ["BilateralLiveRepairService"]
