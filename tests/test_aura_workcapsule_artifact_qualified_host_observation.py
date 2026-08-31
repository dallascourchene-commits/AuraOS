from __future__ import annotations

import hashlib
import inspect
import json

from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    GATES,
    HOST_PREFIX,
    TARGET_REF_MISMATCH,
    admit_artifact_qualified_host_observation,
    artifact_target_ref,
    verify_artifact_qualified_host_observation,
)
from scripts.aura_workcapsule_current_recursive_target_raw_slice_binding import (
    admit_current_recursive_target_raw_slice_binding,
)
from tests.test_aura_workcapsule_current_recursive_target_raw_slice_binding import (
    WorkCapsuleCurrentRecursiveTargetRawSliceBindingTests,
)


def _sha(value) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _default_states() -> dict[str, str]:
    return {
        "U_HEAD": "PASS",
        "U_ROUTE": "UNKNOWN",
        "U_F2": "UNKNOWN",
        "U_CUSTODY": "UNKNOWN",
        "U_CANARY": "UNKNOWN",
    }


def _fixture_resolution(gate: str, state: str, target_ref: str) -> dict | None:
    if state == "UNKNOWN":
        return None
    resolution = {
        "schema": "AURA_HOST_OBSERVATION_RESOLUTION_V1",
        "version": 1,
        "gate": gate,
        "state": state,
        "observation_ref": f"obs://{gate}",
        "producer_ref": "host://producer",
        "producer_generation": "7",
        "currentness_ref": "current://7",
        "authority_ref": "authority://bounded",
        "target_ref": target_ref,
        "resolver_ref": "resolver://fixture",
        "resolver_generation": "3",
        "revoked": False,
    }
    resolution["resolution_digest"] = _sha(resolution)
    return resolution


def _gate_reason(state: str) -> str:
    return "OBSERVATION_OR_RESOLVER_REQUIRED" if state == "UNKNOWN" else "RESOLVED"


def _mask(states: dict[str, str], wanted: str) -> int:
    return sum(1 << index for index, gate in enumerate(GATES) if states[gate] == wanted)


def _disposition(fail_mask: int, unknown_mask: int) -> str:
    if fail_mask:
        return "FAIL_CLOSED"
    if unknown_mask:
        return "HOST_OBSERVATION_REQUIRED"
    return "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING"


def _seal(receipt: dict) -> dict:
    receipt["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": "AURA_WORKCAPSULE_TEMPORAL_HOST_OBSERVATION_ADMISSION_V1",
        "value": _sha(receipt),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return receipt


def _reseal(receipt: dict) -> dict:
    receipt.pop("receipt_identity", None)
    return _seal(receipt)


class WorkCapsuleArtifactQualifiedHostObservationTests(
    WorkCapsuleCurrentRecursiveTargetRawSliceBindingTests
):
    def local_receipt(self, raw=None) -> dict:
        chosen_raw = raw if raw is not None else self.raw_receipt()
        return admit_current_recursive_target_raw_slice_binding(
            **self.join_kwargs(raw=chosen_raw)
        )

    def host_receipt(self, *, states=None, target_ref=None, **overrides) -> dict:
        gate_states = dict(states or _default_states())
        exact_target_ref = target_ref or artifact_target_ref(self.local_receipt())
        resolutions = {
            gate: _fixture_resolution(gate, gate_states[gate], exact_target_ref)
            for gate in GATES
        }
        reasons = {gate: _gate_reason(gate_states[gate]) for gate in GATES}
        fail_mask = _mask(gate_states, "FAIL")
        unknown_mask = _mask(gate_states, "UNKNOWN")
        receipt = {
            "version": "AURA_WORKCAPSULE_TEMPORAL_HOST_OBSERVATION_ADMISSION_V1",
            "disposition": _disposition(fail_mask, unknown_mask),
            "local_temporal_closure_proven": True,
            "pre_closure_status": "HOLD",
            "post_closure_status": "CLOSED",
            "exact_hold_to_closed_transition": True,
            "pre_reentry_receipt_identity": {"kind": "DIGEST", "value": "11" * 32},
            "post_closure_receipt_identity": {"kind": "DIGEST", "value": "22" * 32},
            "host_gate_states": gate_states,
            "host_gate_resolutions": resolutions,
            "host_gate_reasons": reasons,
            "fail_mask": fail_mask,
            "unknown_mask": unknown_mask,
            "candidate_probes_by_unknown_gate": {
                gate: [] for gate in GATES if gate_states[gate] == "UNKNOWN"
            },
            "ordered_required_probes": [],
            "minimum_cover_computed": False,
            "minimum_cover_reason": "PROBE_COSTS_AND_WORLD_PAIR_SEPARATION_NOT_MEASURED",
            "host_observation_set_complete": fail_mask == 0 and unknown_mask == 0,
            "resolver_trust_proven_by_this_module": False,
            "host_observation_authority_proven_by_this_module": False,
            "local_evidence_promoted_to_host_rank": False,
            "drive_pointer_presence_promoted_to_pass": False,
            "cache_or_coordinate_presence_promoted_to_pass": False,
            "trusted_continuation_ready": False,
            "host_effect_ready": False,
            "source_currentness_minted": False,
            "semantic_repair_correctness_minted": False,
            "producer_identity_authenticated": False,
            "authority": {
                "review_authorized": False,
                "execution_authorized": False,
                "commit_authorized": False,
                "merge_authorized": False,
                "promotion_authorized": False,
                "provider_effect_authorized": False,
                "public_effect_authorized": False,
                "human_authority": False,
            },
        }
        receipt.update(overrides)
        return _seal(receipt)

    def child_kwargs(self, *, host=None, raw=None) -> dict:
        chosen_raw = raw if raw is not None else self.raw_receipt()
        parent = self.join_kwargs(raw=chosen_raw)
        return {
            **parent,
            "host_admission_receipt": host if host is not None else self.host_receipt(),
        }

    def test_resolved_host_gate_is_bound_to_exact_local_artifact(self) -> None:
        self.assertEqual(
            [],
            verify_artifact_qualified_host_observation(**self.child_kwargs()),
        )
        receipt = admit_artifact_qualified_host_observation(**self.child_kwargs())
        self.assertTrue(receipt["current_recursive_raw_target_reproved"])
        self.assertTrue(receipt["resolved_host_gates_bound_to_exact_artifact"])
        self.assertEqual(["U_HEAD"], receipt["resolved_host_gates"])
        self.assertFalse(receipt["host_admission_reproved_by_child"])
        self.assertFalse(receipt["host_admission_producer_authenticated"])
        self.assertFalse(receipt["host_effect_ready"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_resealed_foreign_target_ref_rejects(self) -> None:
        host = self.host_receipt(
            target_ref="aura-workcapsule-target-sha256:" + "cd" * 32
        )
        violations = verify_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertIn(f"{TARGET_REF_MISMATCH}:U_HEAD", violations)

    def test_nested_resolution_tamper_resealed_only_outside_rejects(self) -> None:
        host = self.host_receipt()
        host["host_gate_resolutions"]["U_HEAD"]["target_ref"] = (
            "aura-workcapsule-target-sha256:" + "ef" * 32
        )
        _reseal(host)
        violations = verify_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertIn(
            HOST_PREFIX + "HOST_RESOLUTION_DIGEST_MISMATCH:U_HEAD",
            violations,
        )

    def test_nested_resolution_bool_version_rejects_after_full_reseal(self) -> None:
        host = self.host_receipt()
        resolution = host["host_gate_resolutions"]["U_HEAD"]
        resolution["version"] = True
        resolution.pop("resolution_digest")
        resolution["resolution_digest"] = _sha(resolution)
        _reseal(host)
        violations = verify_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertIn(
            HOST_PREFIX + "HOST_RESOLUTION_VERSION_MISMATCH:U_HEAD",
            violations,
        )

    def test_tampered_host_receipt_without_reseal_rejects_integrity(self) -> None:
        host = self.host_receipt()
        host["host_gate_reasons"]["U_HEAD"] = "TAMPERED"
        violations = verify_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertIn(HOST_PREFIX + "HOST_RECEIPT_IDENTITY_MISMATCH", violations)

    def test_unknown_gates_need_no_target_binding_and_remain_unknown(self) -> None:
        host = self.host_receipt(states={gate: "UNKNOWN" for gate in GATES})
        receipt = admit_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertEqual(list(GATES), receipt["unknown_host_gates"])
        self.assertEqual(0, receipt["resolved_host_gate_count"])
        self.assertFalse(receipt["all_host_gates_pass_for_exact_artifact"])
        self.assertFalse(receipt["host_effect_ready"])

    def test_all_pass_for_exact_artifact_remains_nonauthorizing(self) -> None:
        host = self.host_receipt(states={gate: "PASS" for gate in GATES})
        receipt = admit_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertTrue(receipt["all_host_gates_pass_for_exact_artifact"])
        self.assertTrue(receipt["host_observation_set_complete"])
        self.assertFalse(receipt["host_resolver_trust_proven"])
        self.assertFalse(receipt["host_observation_authority_proven"])
        self.assertFalse(receipt["trusted_continuation_ready"])
        self.assertFalse(receipt["host_effect_ready"])

    def test_host_receipt_cannot_widen_effect_authority(self) -> None:
        host = self.host_receipt(host_effect_ready=True)
        violations = verify_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertIn(
            HOST_PREFIX + "HOST_CEILING_VIOLATED:host_effect_ready",
            violations,
        )

    def test_unknown_host_envelope_field_fails_closed(self) -> None:
        host = self.host_receipt()
        host["host_semantic_truth"] = True
        violations = verify_artifact_qualified_host_observation(
            **self.child_kwargs(host=host)
        )
        self.assertEqual(
            [HOST_PREFIX + "MALFORMED_HOST_ADMISSION_ENVELOPE"],
            violations,
        )

    def test_raw_slice_change_changes_artifact_target_reference(self) -> None:
        first = self.local_receipt()
        raw = self.raw_receipt(target_slice_sha256_hex="cd" * 32)
        second = self.local_receipt(raw=raw)
        self.assertNotEqual(artifact_target_ref(first), artifact_target_ref(second))

    def test_public_boundary_has_no_resolver_or_effect_override(self) -> None:
        params = inspect.signature(
            verify_artifact_qualified_host_observation
        ).parameters
        self.assertEqual(
            {
                "scoped_target_inputs",
                "higher_owner_projection",
                "raw_slice_receipt",
                "host_admission_receipt",
            },
            set(params),
        )
        for forbidden in (
            "host_resolver",
            "effect_ready",
            "producer_trusted",
            "raw_bytes",
            "source_catalog",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
