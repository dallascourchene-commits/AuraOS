from __future__ import annotations

import copy
import hashlib
import inspect
import json

from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    GATES,
    TARGET_REF_MISMATCH,
    artifact_target_ref,
)
from scripts.aura_workcapsule_current_recursive_target_raw_slice_binding import (
    admit_current_recursive_target_raw_slice_binding,
)
from scripts.aura_workcapsule_live_causal_artifact_host_observation import (
    admit_live_causal_artifact_host_observation,
    live_causal_artifact_target_ref,
    verify_live_causal_artifact_host_observation,
)
from scripts.aura_workcapsule_live_causal_raw_slice_join import (
    admit_live_causal_raw_slice_join,
)
from tests.test_aura_workcapsule_live_causal_raw_slice_join import (
    WorkCapsuleLiveCausalRawSliceJoinTests,
)


def _sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _resolution(gate: str, state: str, target_ref: str) -> dict | None:
    if state == "UNKNOWN":
        return None
    out = {
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
    out["resolution_digest"] = _sha(out)
    return out


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


class WorkCapsuleLiveCausalArtifactHostObservationTests(
    WorkCapsuleLiveCausalRawSliceJoinTests
):
    def live_receipt(self) -> dict:
        return admit_live_causal_raw_slice_join(**self.o38_kwargs())

    def host_receipt(self, *, target_ref=None, all_pass=False) -> dict:
        states = {gate: ("PASS" if all_pass or gate == "U_HEAD" else "UNKNOWN") for gate in GATES}
        exact_ref = target_ref or live_causal_artifact_target_ref(self.live_receipt())
        resolutions = {gate: _resolution(gate, states[gate], exact_ref) for gate in GATES}
        unknown_mask = sum(1 << i for i, gate in enumerate(GATES) if states[gate] == "UNKNOWN")
        receipt = {
            "version": "AURA_WORKCAPSULE_TEMPORAL_HOST_OBSERVATION_ADMISSION_V1",
            "disposition": "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING" if not unknown_mask else "HOST_OBSERVATION_REQUIRED",
            "local_temporal_closure_proven": True,
            "pre_closure_status": "HOLD",
            "post_closure_status": "CLOSED",
            "exact_hold_to_closed_transition": True,
            "pre_reentry_receipt_identity": {"kind": "DIGEST", "value": "11" * 32},
            "post_closure_receipt_identity": {"kind": "DIGEST", "value": "22" * 32},
            "host_gate_states": states,
            "host_gate_resolutions": resolutions,
            "host_gate_reasons": {gate: ("RESOLVED" if states[gate] != "UNKNOWN" else "OBSERVATION_OR_RESOLVER_REQUIRED") for gate in GATES},
            "fail_mask": 0,
            "unknown_mask": unknown_mask,
            "candidate_probes_by_unknown_gate": {gate: [] for gate in GATES if states[gate] == "UNKNOWN"},
            "ordered_required_probes": [],
            "minimum_cover_computed": False,
            "minimum_cover_reason": "PROBE_COSTS_AND_WORLD_PAIR_SEPARATION_NOT_MEASURED",
            "host_observation_set_complete": unknown_mask == 0,
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
        return _seal(receipt)

    def child_kwargs(self, *, host=None) -> dict:
        kwargs = self.o38_kwargs()
        kwargs["host_admission_receipt"] = host if host is not None else self.host_receipt()
        return kwargs

    def test_resolved_gate_binds_to_exact_live_causal_artifact(self) -> None:
        self.assertEqual([], verify_live_causal_artifact_host_observation(**self.child_kwargs()))
        receipt = admit_live_causal_artifact_host_observation(**self.child_kwargs())
        self.assertTrue(receipt["live_causal_raw_slice_reproved"])
        self.assertTrue(receipt["resolved_host_gates_bound_to_live_causal_artifact"])
        self.assertEqual(["U_HEAD"], receipt["resolved_host_gates"])
        self.assertTrue(receipt["causal_post_owner_reproved_from_raw_evidence"])
        self.assertTrue(receipt["same_exact_post_source_instance_proven"])
        self.assertFalse(receipt["host_admission_reproved_by_child"])
        self.assertFalse(receipt["host_admission_producer_authenticated"])
        self.assertFalse(receipt["host_effect_ready"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_old_pr562_artifact_ref_is_stale_for_live_causal_artifact(self) -> None:
        old_local = admit_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=self.raw_receipt()))
        old_ref = artifact_target_ref(old_local)
        self.assertNotEqual(old_ref, live_causal_artifact_target_ref(self.live_receipt()))
        violations = verify_live_causal_artifact_host_observation(
            **self.child_kwargs(host=self.host_receipt(target_ref=old_ref))
        )
        self.assertIn(f"{TARGET_REF_MISMATCH}:U_HEAD", violations)

    def test_resealed_foreign_live_artifact_ref_rejects(self) -> None:
        foreign = "aura-workcapsule-target-sha256:" + "cd" * 32
        violations = verify_live_causal_artifact_host_observation(
            **self.child_kwargs(host=self.host_receipt(target_ref=foreign))
        )
        self.assertIn(f"{TARGET_REF_MISMATCH}:U_HEAD", violations)

    def test_all_pass_for_live_causal_artifact_remains_nonauthorizing(self) -> None:
        receipt = admit_live_causal_artifact_host_observation(
            **self.child_kwargs(host=self.host_receipt(all_pass=True))
        )
        self.assertTrue(receipt["all_host_gates_pass_for_live_causal_artifact"])
        self.assertTrue(receipt["host_observation_set_complete"])
        self.assertFalse(receipt["host_resolver_trust_proven"])
        self.assertFalse(receipt["host_observation_authority_proven"])
        self.assertFalse(receipt["trusted_continuation_ready"])
        self.assertFalse(receipt["host_effect_ready"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_host_receipt_tamper_rejects_before_target_binding(self) -> None:
        host = self.host_receipt()
        host["host_gate_reasons"]["U_HEAD"] = "TAMPERED"
        violations = verify_live_causal_artifact_host_observation(**self.child_kwargs(host=host))
        self.assertTrue(any("HOST_RECEIPT_IDENTITY_MISMATCH" in item for item in violations))

    def test_live_causal_source_drift_invalidates_artifact_before_host_binding(self) -> None:
        (self.causal.post_root / "src/a.py").write_bytes(b"def target(x):\n    return x + 4\n")
        violations = verify_live_causal_artifact_host_observation(**self.child_kwargs())
        self.assertTrue(any(item.startswith("LIVE_CAUSAL_ARTIFACT_") for item in violations))

    def test_public_boundary_has_no_artifact_or_authority_override(self) -> None:
        params = set(inspect.signature(verify_live_causal_artifact_host_observation).parameters)
        self.assertIn("host_admission_receipt", params)
        self.assertIn("raw_slice_projection", params)
        for forbidden in (
            "artifact_target_ref",
            "post_source_witness",
            "host_target_ref",
            "host_effect_ready",
            "trusted_continuation_ready",
            "execution_authorized",
            "provider_effect_authorized",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest
    unittest.main()
