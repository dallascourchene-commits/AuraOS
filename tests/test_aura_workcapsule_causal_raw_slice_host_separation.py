from __future__ import annotations

import inspect
import unittest
from unittest.mock import Mock, patch

from scripts import aura_workcapsule_causal_raw_slice_host_separation as target


GATES = ("U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY")


def raw_slice(**overrides):
    value = {
        "version": "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_V1",
        "projection_payload_sha256": "1" * 64,
        "file_id": 77,
        "relative_path": "src/module.py",
        "source_generation": 9,
        "full_source_sha256_hex": "2" * 64,
        "full_source_byte_len": 21,
        "target_byte_start": 7,
        "target_byte_end": 13,
        "target_slice_byte_len": 6,
        "target_slice_sha256_hex": "3" * 64,
        "selected_target_semantic_handle_digest_hex": "ab" * 32,
        "portable_target_bound_to_exact_current_raw_slice": True,
        "source_currentness_revalidated_at_materialization": True,
        "synthetic_record_is_materialization_coordinate_only": True,
        "storage_node_identity_minted": False,
        "semantic_handle_carried_from_portable_owner": True,
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "producer_authenticated": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "semantic_patch_correctness_proven": False,
        "b_minus_approved": False,
        "review_authorized": False,
        "mutation_authorized": False,
        "execution_authorized": False,
        "commit_authorized": False,
        "merge_authorized": False,
        "promotion_authorized": False,
        "provider_effect_authorized": False,
        "public_effect_authorized": False,
        "human_authority": False,
    }
    value.update(overrides)
    return value


def host_receipt(*, state="UNKNOWN", disposition="HOST_OBSERVATION_REQUIRED"):
    states = {gate: state for gate in GATES}
    return {
        "causal_temporal_owner_reproved": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "host_gate_states": states,
        "disposition": disposition,
        "host_observation_set_complete": state == "PASS",
    }


class CausalRawSliceHostSeparationTests(unittest.TestCase):
    def test_raw_slice_owner_fails_before_causal_host_owner(self):
        causal = Mock(side_effect=AssertionError("causal host owner must not run"))
        with patch.object(target, "verify_raw_slice_receipt", return_value=["SENTINEL"]), patch.object(
            target, "verify_causal_temporal_host_observation_admission", causal
        ):
            violations = target.verify_causal_raw_slice_host_separation(
                raw_slice_receipt=raw_slice()
            )
        self.assertEqual(violations, ["SENTINEL"])
        causal.assert_not_called()

    def test_causal_host_owner_violation_surfaces_without_reimplementation(self):
        with patch.object(target, "verify_causal_temporal_host_observation_admission", return_value=["TEMPORAL_DRIFT"]):
            violations = target.verify_causal_raw_slice_host_separation(
                raw_slice_receipt=raw_slice()
            )
        self.assertEqual(violations, ["CAUSAL_HOST_TEMPORAL_DRIFT"])

    def test_unknown_causal_host_state_stays_unknown_with_exact_raw_slice(self):
        host = host_receipt()
        with patch.object(target, "_verify_snapshot_and_causal_host", return_value=[]), patch.object(
            target, "admit_causal_temporal_host_observation_admission", return_value=host
        ):
            out = target.admit_causal_raw_slice_host_separation(
                raw_slice_receipt=raw_slice(),
                host_observations={gate: raw_slice() for gate in GATES},
            )
        self.assertEqual(set(out["host_gate_states"].values()), {"UNKNOWN"})
        self.assertEqual(out["host_disposition"], "HOST_OBSERVATION_REQUIRED")
        self.assertFalse(out["host_observation_set_complete"])
        self.assertFalse(out["raw_slice_promoted_to_host_rank"])
        self.assertFalse(out["raw_slice_used_as_host_resolution"])
        self.assertFalse(out["host_effect_ready"])

    def test_all_pass_causal_host_state_remains_nonauthorizing(self):
        host = host_receipt(
            state="PASS",
            disposition="HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING",
        )
        with patch.object(target, "_verify_snapshot_and_causal_host", return_value=[]), patch.object(
            target, "admit_causal_temporal_host_observation_admission", return_value=host
        ):
            out = target.admit_causal_raw_slice_host_separation(
                raw_slice_receipt=raw_slice()
            )
        self.assertTrue(out["host_observation_set_complete"])
        self.assertEqual(
            out["host_disposition"], "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING"
        )
        self.assertFalse(out["raw_slice_promoted_to_host_rank"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["host_resolver_trust_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_raw_slice_semantic_widening_rejected_by_pr566_owner(self):
        violations = target.verify_causal_raw_slice_host_separation(
            raw_slice_receipt=raw_slice(semantic_identity_proven_by_raw_slice=True)
        )
        self.assertIn(
            "RAW_SLICE_CEILING_VIOLATED:semantic_identity_proven_by_raw_slice",
            violations,
        )

    def test_raw_slice_producer_auth_widening_rejected_by_pr566_owner(self):
        violations = target.verify_causal_raw_slice_host_separation(
            raw_slice_receipt=raw_slice(producer_authenticated=True)
        )
        self.assertIn(
            "RAW_SLICE_CEILING_VIOLATED:producer_authenticated",
            violations,
        )

    def test_host_states_are_exactly_the_pr567_owner_output(self):
        states = {
            "U_HEAD": "PASS",
            "U_ROUTE": "FAIL",
            "U_F2": "UNKNOWN",
            "U_CUSTODY": "PASS",
            "U_CANARY": "UNKNOWN",
        }
        host = host_receipt()
        host["host_gate_states"] = states
        host["disposition"] = "FAIL_CLOSED"
        host["host_observation_set_complete"] = False
        with patch.object(target, "_verify_snapshot_and_causal_host", return_value=[]), patch.object(
            target, "admit_causal_temporal_host_observation_admission", return_value=host
        ):
            out = target.admit_causal_raw_slice_host_separation(
                raw_slice_receipt=raw_slice()
            )
        self.assertEqual(out["host_gate_states"], states)
        self.assertEqual(out["host_disposition"], "FAIL_CLOSED")

    def test_host_callback_cannot_mutate_validated_raw_evidence_identity(self):
        original = raw_slice()
        expected_digest = target._sha256(original)
        shared = dict(original)
        host = host_receipt()

        def mutating_host_owner(**_kwargs):
            shared["producer_authenticated"] = True
            return host

        with patch.object(target, "_verify_snapshot_and_causal_host", return_value=[]), patch.object(
            target,
            "admit_causal_temporal_host_observation_admission",
            side_effect=mutating_host_owner,
        ):
            out = target.admit_causal_raw_slice_host_separation(
                raw_slice_receipt=shared,
                host_observations={"U_HEAD": shared},
            )

        self.assertTrue(shared["producer_authenticated"])
        self.assertEqual(out["raw_slice_receipt_digest"], expected_digest)
        self.assertNotEqual(out["raw_slice_receipt_digest"], target._sha256(shared))
        self.assertFalse(out["raw_slice_producer_authenticated"])
        self.assertTrue(out["raw_slice_exact_current_local_evidence_validated"])

    def test_receipt_identity_is_deterministic(self):
        host = host_receipt()
        with patch.object(target, "_verify_snapshot_and_causal_host", return_value=[]), patch.object(
            target, "admit_causal_temporal_host_observation_admission", return_value=host
        ):
            first = target.admit_causal_raw_slice_host_separation(
                raw_slice_receipt=raw_slice()
            )
            second = target.admit_causal_raw_slice_host_separation(
                raw_slice_receipt=raw_slice()
            )
        self.assertEqual(first, second)
        self.assertEqual(len(first["receipt_identity"]["value"]), 64)
        self.assertEqual(first["raw_slice_contract_owner"], "PR566.verify_raw_slice_receipt")
        self.assertEqual(
            first["causal_host_owner"],
            "PR567.admit_causal_temporal_host_observation_admission",
        )

    def test_public_boundary_has_no_rank_or_effect_override(self):
        params = inspect.signature(
            target.admit_causal_raw_slice_host_separation
        ).parameters
        for forbidden in (
            "raw_slice_host_pass",
            "promote_raw_slice_to_host",
            "raw_slice_used_as_host_resolution",
            "host_effect_ready",
            "execution_authorized",
            "provider_effect_authorized",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    unittest.main()
