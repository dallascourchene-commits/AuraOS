"""Runtime replay and persistent bounded repair mixin for B11-B15."""
from __future__ import annotations

from collections.abc import Mapping
import json
import time
from typing import TYPE_CHECKING, Any

from aura_bilateral_live_repair_foundry_contracts import (
    MAX_ATTEMPTS, _FALSE_AUTHORITY, BilateralIdentity, BilateralLiveRepairError,
    IncidentReplayPacket, RepairCandidateResult, _digest_text, _group_passed,
    _runtime_binding_digest, canonical_sanitize, classify_repair_route,
    derive_repair_failure_class, digest,
)


class _RuntimeRepairMixin:
    if TYPE_CHECKING:
        attempt_archive: Any
        _runtime_proofs: dict[str, tuple[str, dict[str, Any]]]

        def _packet(self, packet_id: str) -> IncidentReplayPacket: ...

        def _resolve_current_identity(
            self,
            expected: BilateralIdentity,
        ) -> BilateralIdentity: ...

    def record_repair_attempt(
        self,
        *,
        packet_id: str,
        hypothesis: Mapping[str, Any],
        candidate_digest: str,
        runtime_proof_ref: str,
        minimized_counterexample: Mapping[str, Any] | None,
        current_identity: BilateralIdentity,
        arena_id: str = "coding",
    ) -> RepairCandidateResult:
        packet = self._packet(packet_id)
        packet.identity.assert_current(current_identity)
        self._resolve_current_identity(packet.identity)
        candidate = _digest_text(candidate_digest, "candidate_digest")
        proof_ref = _digest_text(runtime_proof_ref, "runtime_proof_ref")
        runtime_proof = self._runtime_proof(packet, proof_ref)
        runtime_candidate_id = runtime_proof.get("runtime_candidate_id")
        if runtime_candidate_id is None:
            raise BilateralLiveRepairError("runtime proof is missing runtime_candidate_id")
        if not isinstance(runtime_candidate_id, str) or _runtime_binding_digest(runtime_candidate_id) != candidate:
            raise BilateralLiveRepairError("repair candidate differs from the retained runtime proof")
        clean_hypothesis, _ = canonical_sanitize(hypothesis)
        hypothesis_digest = digest(clean_hypothesis)
        prior = self._prior_attempts(packet)
        if len(prior) >= MAX_ATTEMPTS:
            raise BilateralLiveRepairError("repair attempt budget exhausted")
        if any(
            row.get("hypothesis_digest") == hypothesis_digest and row.get("promotion_ready") is not True
            for row in prior
        ):
            raise BilateralLiveRepairError("repeated failed hypothesis is forbidden across sessions")

        positive = _group_passed(runtime_proof, "positive_assertions")
        negative = _group_passed(runtime_proof, "negative_assertions")
        preservation = _group_passed(runtime_proof, "preservation_assertions")
        faults = _group_passed(runtime_proof, "fault_injections")
        repository_unchanged = runtime_proof.get("repository_identity_unchanged") is True
        verifier = runtime_proof.get("independent_verifier")
        independent_exact = (
            isinstance(verifier, Mapping)
            and verifier.get("verifier_id") == packet.identity.verifier_id
            and verifier.get("source_sha256") == packet.identity.verifier_source_digest
        )
        base_receipt = runtime_proof.get("base_runtime_receipt")
        adjacent_regressions_passed = isinstance(base_receipt, Mapping) and base_receipt.get("ok") is True
        failure_class = derive_repair_failure_class(runtime_proof)
        route_class = classify_repair_route(failure_class)
        proof_ok = runtime_proof.get("ok") is True
        promotion_ready = all(
            (
                proof_ok,
                positive,
                negative,
                preservation,
                faults,
                adjacent_regressions_passed,
                repository_unchanged,
                independent_exact,
            )
        )
        counterexample, _ = canonical_sanitize(minimized_counterexample) if minimized_counterexample else (None, ())
        created_at = time.time()
        attempt_id = f"RA-{len(prior) + 1:03d}-{hypothesis_digest[:12]}"
        result_body = {
            "attempt_id": attempt_id,
            "ok": promotion_ready,
            "status": "REPAIR_VERIFIED" if promotion_ready else "REPAIR_REJECTED",
            "replay_packet_digest": packet.packet_digest,
            "hypothesis_digest": hypothesis_digest,
            "candidate_digest": candidate,
            "runtime_proof_digest": proof_ref,
            "runtime_proof_passed": proof_ok,
            "positive_passed": positive,
            "negative_passed": negative,
            "preservation_passed": preservation,
            "fault_injections_passed": faults,
            "adjacent_regressions_passed": adjacent_regressions_passed,
            "repository_unchanged": repository_unchanged,
            "independent_verifier_exact": independent_exact,
            "promotion_ready": promotion_ready,
            "failure_class": failure_class.upper(),
            "route_class": route_class,
            "minimized_counterexample": counterexample,
            "created_at": created_at,
            "authority": {**_FALSE_AUTHORITY, "human_review_required": True},
        }
        archive = self.attempt_archive.record(
            arena_id=arena_id,
            route="bilateral-live-repair/repair-attempt",
            request={
                "action_id": "verify_repair_candidate",
                "packet_id": packet.packet_id,
                "replay_packet_digest": packet.packet_digest,
                "hypothesis": clean_hypothesis,
                "hypothesis_digest": hypothesis_digest,
                "candidate_digest": candidate,
                "runtime_proof_ref": proof_ref,
            },
            result=result_body,
            workflow_state={
                "workflow_id": packet.packet_id,
                "current_phase": "B12_REPAIR_FOUNDRY",
                "objective": "Satisfy the complete confirmed bilateral runtime contract",
            },
            archive_context={
                "stage_hint": "B12",
                "incident_packet_digest": packet.packet_digest,
                "identity_digest": packet.identity.identity_digest,
            },
        )
        if archive.get("ok") is not True:
            raise BilateralLiveRepairError("canonical Attempt Archive did not retain the repair attempt")
        return RepairCandidateResult(
            attempt_id=attempt_id,
            replay_packet_digest=packet.packet_digest,
            hypothesis_digest=hypothesis_digest,
            candidate_digest=candidate,
            runtime_proof_digest=proof_ref,
            runtime_proof_passed=proof_ok,
            positive_passed=positive,
            negative_passed=negative,
            preservation_passed=preservation,
            fault_injections_passed=faults,
            adjacent_regressions_passed=adjacent_regressions_passed,
            repository_unchanged=repository_unchanged,
            independent_verifier_exact=independent_exact,
            minimized_counterexample=counterexample,
            failure_class=failure_class.upper(),
            route_class=route_class,
            promotion_ready=promotion_ready,
            archive_artifact_ref=str(archive["artifact_id"]),
            created_at=created_at,
        )

    def attempts_for_packet(self, packet_id: str) -> tuple[RepairCandidateResult, ...]:
        packet = self._packet(packet_id)
        rows: list[RepairCandidateResult] = []
        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/repair-attempt",
            limit=MAX_ATTEMPTS + 1,
        ):
            artifact_ref = str(summary.get("artifact_id") or "")
            artifact = self.attempt_archive.get(artifact_ref)
            result = dict((artifact or {}).get("result") or {})
            if result.get("replay_packet_digest") != packet.packet_digest:
                continue
            rows.append(RepairCandidateResult.from_mapping(result, archive_artifact_ref=artifact_ref))
        rows.sort(key=lambda item: (item.created_at, item.attempt_id))
        return tuple(rows)

    def _runtime_proof(self, packet: IncidentReplayPacket, proof_ref: str) -> dict[str, Any]:
        retained = self._runtime_proofs.get(proof_ref)
        if retained is not None:
            retained_packet_id, proof = retained
            if retained_packet_id != packet.packet_id:
                raise BilateralLiveRepairError("runtime proof belongs to another incident")
            return dict(proof)
        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/runtime-replay",
            limit=0,
        ):
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            result = dict((artifact or {}).get("result") or {})
            if result.get("runtime_proof_digest") != proof_ref:
                continue
            proof: Any = result.get("runtime_proof")
            proof_json = result.get("runtime_proof_json")
            if isinstance(proof_json, str) and proof_json:
                try:
                    proof = json.loads(proof_json)
                except json.JSONDecodeError as exc:
                    raise BilateralLiveRepairError("archived runtime proof JSON is invalid") from exc
            if (
                result.get("packet_digest") == packet.packet_digest
                and result.get("runtime_proof_digest") == proof_ref
                and isinstance(proof, Mapping)
                and self._runtime_proof_identity_matches(proof, proof_ref)
            ):
                normalized = dict(proof)
                self._runtime_proofs[proof_ref] = (packet.packet_id, normalized)
                self._runtime_proofs.move_to_end(proof_ref)
                while len(self._runtime_proofs) > 32:
                    self._runtime_proofs.popitem(last=False)
                return normalized
        raise BilateralLiveRepairError("runtime proof reference was not retained by Runtime Profile V2 replay")

    @staticmethod
    def _runtime_proof_identity_matches(
        proof: Mapping[str, Any],
        proof_ref: str,
    ) -> bool:
        if proof.get("version"):
            canonical = {
                key: value
                for key, value in proof.items()
                if key not in {"proof_digest", "proof_path", "output_dir"}
            }
            return (
                proof.get("proof_digest") == proof_ref
                and _runtime_binding_digest(canonical) == proof_ref
            )
        return digest(proof) == proof_ref

    def _prior_attempts(self, packet: IncidentReplayPacket) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for summary in self.attempt_archive.list(
            workflow_id=packet.packet_id,
            route="bilateral-live-repair/repair-attempt",
            limit=MAX_ATTEMPTS + 1,
        ):
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            if not artifact:
                continue
            result = dict(artifact.get("result") or {})
            if result.get("replay_packet_digest") == packet.packet_digest:
                rows.append(result)
        rows.sort(key=lambda item: (float(item.get("created_at") or 0.0), str(item.get("hypothesis_digest") or "")))
        return rows


__all__ = ["_RuntimeRepairMixin"]
