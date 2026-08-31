from __future__ import annotations

import inspect
import unittest

from scripts import aura_workcapsule_causal_raw_slice_host_plane_separation as target
from tests.test_aura_workcapsule_causal_temporal_host_observation_admission import (
    causal_owner,
)
from tests.test_aura_workcapsule_temporal_host_observation_admission import (
    FakeResolver,
    observations,
    resolution,
)


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


class RawSliceResolver:
    def resolve(self, *, gate, observation):
        return raw_slice()


class CausalRawSliceHostPlaneSeparationTests(unittest.TestCase):
    def test_raw_slice_at_every_host_gate_stays_unknown_without_resolver(self):
        supplied = {gate: raw_slice() for gate in observations()}
        with causal_owner():
            out = target.admit_causal_raw_slice_host_plane_separation(
                raw_slice_receipt=raw_slice(),
                host_observations=supplied,
            )
        self.assertTrue(out["causal_temporal_owner_reproved"])
        self.assertTrue(out["pre_reentry_receipt_reused_for_post_o10"])
        self.assertFalse(out["fresh_post_reentry_receipt_substituted"])
        self.assertEqual(set(out["host_gate_states"].values()), {"UNKNOWN"})
        self.assertEqual(out["host_disposition"], "HOST_OBSERVATION_REQUIRED")
        self.assertFalse(out["raw_slice_promoted_to_host_rank"])
        self.assertTrue(out["host_resolution_required_for_rank_change"])
        self.assertFalse(out["host_effect_ready"])

    def test_raw_slice_receipt_still_cannot_impersonate_host_resolution(self):
        with causal_owner():
            with self.assertRaisesRegex(ValueError, "HOST_RESOLUTION_FIELDS_MISMATCH"):
                target.admit_causal_raw_slice_host_plane_separation(
                    raw_slice_receipt=raw_slice(),
                    host_observations=observations(),
                    host_observation_resolver=RawSliceResolver(),
                )

    def test_real_host_resolutions_complete_but_remain_nonauthorizing(self):
        resolver = FakeResolver({gate: resolution(gate) for gate in observations()})
        with causal_owner():
            out = target.admit_causal_raw_slice_host_plane_separation(
                raw_slice_receipt=raw_slice(),
                host_observations=observations(),
                host_observation_resolver=resolver,
            )
        self.assertTrue(out["host_observation_set_complete"])
        self.assertEqual(
            out["host_disposition"],
            "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING",
        )
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["raw_slice_promoted_to_host_rank"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_causal_owner_failure_blocks_before_host_rank(self):
        with causal_owner(violations=["PR518_TWO_PHASE_PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT"]):
            violations = target.verify_causal_raw_slice_host_plane_separation(
                raw_slice_receipt=raw_slice(),
                host_observations={},
            )
        self.assertIn(
            "CAUSAL_HOST_TEMPORAL_PR518_TWO_PHASE_PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT",
            violations,
        )

    def test_raw_slice_bool_file_id_rejects_before_host_composition(self):
        violations = target.verify_causal_raw_slice_host_plane_separation(
            raw_slice_receipt=raw_slice(file_id=True),
            host_observations={},
        )
        self.assertEqual(
            ["RAW_SLICE_RAW_SLICE_INTEGER_INVALID:file_id"],
            violations,
        )

    def test_raw_slice_semantic_widening_stays_rejected(self):
        violations = target.verify_causal_raw_slice_host_plane_separation(
            raw_slice_receipt=raw_slice(semantic_identity_proven_by_raw_slice=True),
            host_observations={},
        )
        self.assertIn(
            "RAW_SLICE_RAW_SLICE_CEILING_VIOLATED:semantic_identity_proven_by_raw_slice",
            violations,
        )

    def test_public_boundary_has_no_stale_owner_or_effect_override(self):
        params = inspect.signature(
            target.admit_causal_raw_slice_host_plane_separation
        ).parameters
        for forbidden in (
            "temporal_receipt",
            "post_closure_receipt",
            "raw_slice_host_pass",
            "promote_raw_slice_to_host",
            "host_effect_ready",
            "execution_authorized",
            "provider_effect_authorized",
        ):
            self.assertNotIn(forbidden, params)

    def test_receipt_identity_is_deterministic(self):
        with causal_owner():
            first = target.admit_causal_raw_slice_host_plane_separation(
                raw_slice_receipt=raw_slice()
            )
            second = target.admit_causal_raw_slice_host_plane_separation(
                raw_slice_receipt=raw_slice()
            )
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
