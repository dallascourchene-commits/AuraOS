from __future__ import annotations

import hashlib
import inspect
import unittest
from unittest.mock import patch

from scripts.aura_k27_astge_portable_raw_slice_causal_handoff import (
    CANONICALIZATION,
    PAYLOAD_FIELDS,
    RAW_SLICE_VERSION,
    SCHEMA,
    canonical_raw_slice_payload_bytes,
)
from scripts import aura_workcapsule_live_causal_raw_slice_host as target


def witness(**overrides):
    row = {
        "role": "dependency",
        "file_id": 17,
        "relative_path": "src/a.py",
        "source_generation": 43,
        "source_sha256": "22" * 32,
        "source_byte_len": 32,
        "currentness": "CURRENT",
        "witness_ref": "source-witness:post:17",
    }
    row.update(overrides)
    return row


def raw_projection(**overrides):
    payload = {
        "schema": SCHEMA,
        "version": 1,
        "canonicalization_profile": CANONICALIZATION,
        "raw_slice_version": RAW_SLICE_VERSION,
        "projection_payload_sha256": "11" * 32,
        "file_id": 17,
        "relative_path": "src/a.py",
        "source_generation": 43,
        "full_source_sha256_hex": "22" * 32,
        "full_source_byte_len": 32,
        "target_byte_start": 0,
        "target_byte_end": 6,
        "target_slice_byte_len": 6,
        "target_slice_sha256_hex": "33" * 32,
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
    payload.update(overrides)
    assert set(payload) == set(PAYLOAD_FIELDS)
    return {
        "payload": payload,
        "payload_sha256": hashlib.sha256(canonical_raw_slice_payload_bytes(payload)).hexdigest(),
    }


def post_projection(*rows):
    return {
        "source_generation_domain": "SOURCE",
        "o7_source_witnesses": list(rows or [witness()]),
        "receipt_identity": {"kind": "DIGEST", "value": "44" * 32},
    }


def causal_host_admission(**overrides):
    value = {
        "causal_temporal_owner_reproved": True,
        "pre_closure_status": "HOLD",
        "post_closure_status": "CLOSED",
        "post_closure_receipt_identity": {"kind": "DIGEST", "value": "55" * 32},
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "disposition": "HOST_OBSERVATION_REQUIRED",
        "host_gate_states": {
            "U_HEAD": "UNKNOWN", "U_ROUTE": "UNKNOWN", "U_F2": "UNKNOWN",
            "U_CUSTODY": "UNKNOWN", "U_CANARY": "UNKNOWN",
        },
        "host_observation_set_complete": False,
    }
    value.update(overrides)
    return value


class LiveCausalRawSliceHostTests(unittest.TestCase):
    def owner_context(self, *, projection=None, host=None, host_violations=None):
        projection = projection or post_projection()
        return (
            patch.object(target, "verify_causal_temporal_host_observation_admission", return_value=list(host_violations or [])),
            patch.object(target, "_derive_transition_inputs", return_value=({}, projection, {}, {})),
            patch.object(target, "admit_causal_temporal_host_observation_admission", return_value=host or causal_host_admission()),
        )

    def test_live_post_witness_closes_pr563_synthetic_ceiling(self):
        contexts = self.owner_context()
        with contexts[0], contexts[1], contexts[2]:
            out = target.admit_live_causal_raw_slice_host(raw_slice_projection=raw_projection())
        self.assertTrue(out["live_pr560_to_pr556_causal_slice_join_proven"])
        self.assertTrue(out["live_post_source_coordinate_match_proven"])
        self.assertTrue(out["causal_post_owner_reproved_by_child"])
        self.assertEqual(out["matched_live_post_source_witness_ref"], "source-witness:post:17")
        self.assertEqual(set(out["host_gate_states"].values()), {"UNKNOWN"})
        self.assertFalse(out["raw_slice_promoted_to_host_rank"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_foreign_current_source_witness_does_not_become_live_join(self):
        contexts = self.owner_context(projection=post_projection(witness(source_generation=44)))
        with contexts[0], contexts[1], contexts[2]:
            violations = target.verify_live_causal_raw_slice_host(raw_slice_projection=raw_projection())
        self.assertIn(
            "LIVE_CAUSAL_POST_BINDING_FAILED:NO_LIVE_CAUSAL_POST_SOURCE_MATCH", violations
        )

    def test_multiple_matching_post_witnesses_fail_closed(self):
        contexts = self.owner_context(projection=post_projection(witness(), witness(witness_ref="second")))
        with contexts[0], contexts[1], contexts[2]:
            violations = target.verify_live_causal_raw_slice_host(raw_slice_projection=raw_projection())
        self.assertIn(
            "LIVE_CAUSAL_POST_BINDING_FAILED:AMBIGUOUS_LIVE_CAUSAL_POST_SOURCE_MATCH", violations
        )

    def test_raw_slice_semantic_widening_rejects_before_causal_join(self):
        item = raw_projection(semantic_identity_proven_by_raw_slice=True)
        item["payload_sha256"] = hashlib.sha256(
            canonical_raw_slice_payload_bytes(item["payload"])
        ).hexdigest()
        violations = target.verify_live_causal_raw_slice_host(raw_slice_projection=item)
        self.assertIn(
            "RAW_SLICE_CEILING_VIOLATION:semantic_identity_proven_by_raw_slice", violations
        )

    def test_causal_owner_failure_blocks_raw_slice_binding_before_host_plane(self):
        contexts = self.owner_context(host_violations=["TEMPORAL_BAD_CAUSAL_O10"])
        with contexts[0], contexts[1], contexts[2]:
            violations = target.verify_live_causal_raw_slice_host(raw_slice_projection=raw_projection())
        self.assertEqual(["CAUSAL_HOST_TEMPORAL_BAD_CAUSAL_O10"], violations)

    def test_all_host_pass_still_cannot_become_effect_authority(self):
        host = causal_host_admission(
            disposition="HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING",
            host_gate_states={
                "U_HEAD": "PASS", "U_ROUTE": "PASS", "U_F2": "PASS",
                "U_CUSTODY": "PASS", "U_CANARY": "PASS",
            },
            host_observation_set_complete=True,
        )
        contexts = self.owner_context(host=host)
        with contexts[0], contexts[1], contexts[2]:
            out = target.admit_live_causal_raw_slice_host(raw_slice_projection=raw_projection())
        self.assertTrue(out["host_observation_set_complete"])
        self.assertEqual(out["host_disposition"], "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING")
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_public_boundary_has_no_caller_post_source_or_effect_override(self):
        params = inspect.signature(target.admit_live_causal_raw_slice_host).parameters
        for forbidden in (
            "post_source_witness", "post_projection", "candidate_binding", "post_closure_receipt",
            "live_join_proven", "host_effect_ready", "execution_authorized",
        ):
            self.assertNotIn(forbidden, params)

    def test_receipt_identity_is_deterministic(self):
        contexts = self.owner_context()
        with contexts[0], contexts[1], contexts[2]:
            a = target.admit_live_causal_raw_slice_host(raw_slice_projection=raw_projection())
        contexts = self.owner_context()
        with contexts[0], contexts[1], contexts[2]:
            b = target.admit_live_causal_raw_slice_host(raw_slice_projection=raw_projection())
        self.assertEqual(a, b)
        self.assertEqual(64, len(a["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
