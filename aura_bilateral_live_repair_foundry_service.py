"""Canonical-owner orchestration for B11-B15 bilateral live repair."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from aura_bilateral_live_repair_foundry_contracts import (
    _FALSE_AUTHORITY,
    BilateralLiveRepairError,
    IncidentReplayPacket,
    _digest_text,
    _runtime_binding_digest,
    canonical_bytes,
    digest,
)
from aura_bilateral_live_repair_foundry_service_capture import _CapturePersistenceMixin
from aura_bilateral_live_repair_foundry_service_preview import _PreviewLearningProjectionMixin
from aura_bilateral_live_repair_foundry_service_runtime import _RuntimeRepairMixin
from scripts.aura_runtime_profile_v2_adapter import (
    PROFILE_VERSION as RUNTIME_PROFILE_VERSION,
    VERSION as RUNTIME_PROOF_VERSION,
)

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

    def close(self) -> None:
        with self._capture_lock:
            for capture in self._captures.values():
                self._scrub_capture(capture)
        super().close()

    def status(self) -> dict[str, Any]:
        self._sweep_expired_captures()
        return super().status()

    def observe(self, capture_id: str, event_type: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._capture_lock:
            capture = self._capture(capture_id)
            try:
                return super().observe(capture_id, event_type, payload)
            except BilateralLiveRepairError:
                if capture._closed:
                    self._scrub_capture(capture)
                    self._captures.pop(capture_id, None)
                    timer = self._capture_timers.pop(capture_id, None)
                    if timer is not None:
                        timer.cancel()
                raise

    def finalize_capture(self, capture_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
        capture = self._capture(capture_id)
        try:
            return super().finalize_capture(capture_id, contract)
        finally:
            with self._capture_lock:
                if capture._closed:
                    self._scrub_capture(capture)
                    self._captures.pop(capture_id, None)
                    timer = self._capture_timers.pop(capture_id, None)
                    if timer is not None:
                        timer.cancel()

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
        if (
            proof.get("version") != RUNTIME_PROOF_VERSION
            or proof.get("profile_version") != RUNTIME_PROFILE_VERSION
        ):
            raise BilateralLiveRepairError("runtime proof version or profile version is not canonical")
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

        bindings = proof.get("requirement_bindings")
        groups = (
            "positive_assertions",
            "negative_assertions",
            "preservation_assertions",
            "fault_injections",
        )
        if not isinstance(bindings, Mapping) or set(bindings) != set(groups):
            raise BilateralLiveRepairError("runtime proof omitted canonical requirement bindings")

        def _bound(group: str) -> set[str]:
            rows = bindings.get(group)
            if not isinstance(rows, list) or not rows:
                raise BilateralLiveRepairError(f"runtime proof {group} bindings are invalid")
            values: set[str] = set()
            for row in rows:
                if not isinstance(row, Mapping):
                    raise BilateralLiveRepairError(f"runtime proof {group} bindings are invalid")
                value = row.get("requirement_digest")
                if not isinstance(value, str) or not value:
                    raise BilateralLiveRepairError(f"runtime proof {group} bindings are invalid")
                values.add(value)
            return values

        expected_positive = {_runtime_binding_digest(item) for item in packet.expected_positive}
        expected_negative = {_runtime_binding_digest(item) for item in packet.expected_negative}
        expected_preservation = {_runtime_binding_digest(item) for item in packet.preservation_claims}
        confirmed_positive = set(proof.get("confirmed_positive_requirement_digests") or ())
        confirmed_negative = set(proof.get("confirmed_negative_requirement_digests") or ())
        if (
            confirmed_positive != expected_positive
            or confirmed_negative != expected_negative | expected_preservation
            or _bound("positive_assertions") != expected_positive
            or _bound("preservation_assertions") != expected_preservation
            or _bound("negative_assertions") | _bound("fault_injections") != expected_negative
        ):
            raise BilateralLiveRepairError("runtime proof requirements differ from the captured obligations")

        if packet.required_assets:
            traces = proof.get("required_trace_artifacts")
            if not isinstance(traces, list):
                raise BilateralLiveRepairError("runtime proof omitted captured required assets")
            proven_assets = {
                (row.get("path"), row.get("sha256"))
                for row in traces
                if (
                    isinstance(row, Mapping)
                    and row.get("present") is True
                    and row.get("within_size_limit") is True
                    and isinstance(row.get("path"), str)
                    and isinstance(row.get("sha256"), str)
                )
            }
            expected_assets = {(item.path, item.sha256) for item in packet.required_assets}
            if not expected_assets.issubset(proven_assets):
                raise BilateralLiveRepairError(
                    "runtime proof did not retain every captured required asset"
                )
        proof_digest = _digest_text(proof.get("proof_digest"), "proof_digest")
        canonical_proof = {
            key: value
            for key, value in proof.items()
            if key not in {"proof_digest", "proof_path", "output_dir"}
        }
        if proof_digest != _runtime_binding_digest(canonical_proof):
            raise BilateralLiveRepairError("runtime proof digest is not the canonical owner identity")

    def execute_replay(
        self,
        *,
        packet_id: str,
        profile_path: str | Path,
        confirmation_packet: str | Path,
        output_dir: str | Path,
        venv_path: str | Path | None = None,
        baseline_receipt: str | Path | None = None,
        nested_replay_context: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        packet = self._packet(packet_id)
        runner_kwargs: dict[str, Any] = dict(
            profile_path=profile_path,
            confirmation_packet=confirmation_packet,
            output_dir=output_dir,
            venv_path=venv_path,
            install_requirements=False,
            allow_dirty=False,
            baseline_receipt=baseline_receipt,
        )
        if nested_replay_context is not None:
            runner_kwargs["nested_replay_context"] = nested_replay_context
        runner_result = dict(
            self.runtime_runner(
                self.repo_root,
                **runner_kwargs,
            )
        )
        proof = {
            key: value
            for key, value in runner_result.items()
            if key not in {"proof_path", "output_dir"}
        }
        self._validate_runtime_proof(
            packet,
            proof,
            allow_reduced_fixture=self._allow_reduced_runtime_fixture,
        )
        if proof.get("version"):
            proof_digest = str(proof.get("proof_digest") or "")
        else:
            proof_digest = digest(proof)
        execution_metadata = {
            key: runner_result[key]
            for key in ("proof_path", "output_dir")
            if key in runner_result
        }
        result = {
            "ok": proof.get("ok") is True,
            "status": "INCIDENT_REPLAY_VERIFIED" if proof.get("ok") is True else "INCIDENT_REPLAY_REPRODUCED",
            "packet_id": packet.packet_id,
            "packet_digest": packet.packet_digest,
            "runtime_proof": proof,
            "runtime_proof_digest": proof_digest,
            "execution_metadata": execution_metadata,
            "authority": {**_FALSE_AUTHORITY, "human_review_required": True},
        }
        archive_result = {
            key: value for key, value in result.items() if key != "runtime_proof"
        }
        archive_result["runtime_proof_json"] = canonical_bytes(proof).decode("ascii")
        archive = self.attempt_archive.record(
            arena_id="construction",
            route="bilateral-live-repair/runtime-replay",
            request={
                "action_id": "execute_incident_replay",
                "packet_id": packet.packet_id,
                "packet_digest": packet.packet_digest,
                "runtime_profile_digest": packet.identity.runtime_profile_digest,
            },
            result=archive_result,
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
        self._runtime_proofs.move_to_end(proof_digest)
        while len(self._runtime_proofs) > 32:
            self._runtime_proofs.popitem(last=False)
        return {**result, "runtime_proof_ref": proof_digest, "attempt_artifact": archive}


__all__ = ["BilateralLiveRepairService"]
