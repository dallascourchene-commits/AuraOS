from __future__ import annotations

import inspect
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from scripts import aura_workcapsule_temporal_host_observation_admission as host_parent
from scripts import aura_workcapsule_raw_slice_host_plane_separation as target


def raw_slice(**overrides):
    value = {
        "version": target.RAW_SLICE_VERSION,
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


def local_admission():
    return {
        "pre_closure_status": "HOLD",
        "post_closure_status": "CLOSED",
        "exact_hold_to_closed_transition": True,
        "pre_reentry_receipt_identity": {"kind": "DIGEST", "value": "4" * 64},
        "post_closure_receipt_identity": {"kind": "DIGEST", "value": "5" * 64},
    }


@contextmanager
def local_temporal_owner():
    with patch.object(host_parent, "verify_preplan_post_observation_transition", return_value=[]), patch.object(
        host_parent, "admit_preplan_post_observation_transition", return_value=local_admission()
    ):
        yield


def resolution(gate):
    value = {
        "schema": host_parent.HOST_RESOLUTION_SCHEMA,
        "version": host_parent.HOST_RESOLUTION_VERSION,
        "gate": gate,
        "state": "PASS",
        "observation_ref": f"obs:{gate}",
        "producer_ref": f"producer:{gate}",
        "producer_generation": "producer-gen-1",
        "currentness_ref": f"current:{gate}",
        "authority_ref": f"authority:{gate}",
        "target_ref": f"target:{gate}",
        "resolver_ref": "host-resolver-v1",
        "resolver_generation": "resolver-gen-1",
        "revoked": False,
        "resolution_digest": "0" * 64,
    }
    value["resolution_digest"] = host_parent._resolution_digest(value)
    return value


class Resolver:
    def __init__(self, by_gate):
        self.by_gate = by_gate

    def resolve(self, *, gate, observation):
        return self.by_gate[gate]


class RawSliceHostPlaneSeparationTests(unittest.TestCase):
    def test_exact_raw_slice_present_at_every_host_gate_remains_unknown_without_resolver(self):
        supplied = {gate: raw_slice() for gate in host_parent.GATES}
        with local_temporal_owner():
            out = target.admit_raw_slice_host_plane_separation(
                raw_slice_receipt=raw_slice(), host_observations=supplied
            )
        self.assertEqual(set(out["host_gate_states"].values()), {"UNKNOWN"})
        self.assertEqual(out["host_disposition"], "HOST_OBSERVATION_REQUIRED")
        self.assertFalse(out["raw_slice_promoted_to_host_rank"])
        self.assertTrue(out["host_resolution_required_for_rank_change"])
        self.assertFalse(out["host_effect_ready"])

    def test_raw_slice_receipt_cannot_impersonate_host_resolution(self):
        supplied = {gate: {"raw_slice": True} for gate in host_parent.GATES}
        resolver = Resolver({gate: raw_slice() for gate in host_parent.GATES})
        with local_temporal_owner():
            with self.assertRaisesRegex(ValueError, "HOST_RESOLUTION_FIELDS_MISMATCH"):
                target.admit_raw_slice_host_plane_separation(
                    raw_slice_receipt=raw_slice(),
                    host_observations=supplied,
                    host_observation_resolver=resolver,
                )

    def test_real_host_resolution_can_complete_but_stays_nonauthorizing(self):
        supplied = {gate: {"probe": gate} for gate in host_parent.GATES}
        resolver = Resolver({gate: resolution(gate) for gate in host_parent.GATES})
        with local_temporal_owner():
            out = target.admit_raw_slice_host_plane_separation(
                raw_slice_receipt=raw_slice(),
                host_observations=supplied,
                host_observation_resolver=resolver,
            )
        self.assertTrue(out["host_observation_set_complete"])
        self.assertEqual(out["host_disposition"], "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING")
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["raw_slice_promoted_to_host_rank"])
        self.assertFalse(any(out["authority"].values()))

    def test_raw_slice_semantic_identity_widening_rejects(self):
        violations = target.verify_raw_slice_receipt(
            raw_slice(semantic_identity_proven_by_raw_slice=True)
        )
        self.assertIn(
            "RAW_SLICE_CEILING_VIOLATED:semantic_identity_proven_by_raw_slice", violations
        )

    def test_raw_slice_producer_auth_widening_rejects(self):
        violations = target.verify_raw_slice_receipt(raw_slice(producer_authenticated=True))
        self.assertIn("RAW_SLICE_CEILING_VIOLATED:producer_authenticated", violations)

    def test_unknown_raw_slice_field_rejects_closed_schema(self):
        value = raw_slice()
        value["host_gate_pass"] = True
        self.assertEqual(["RAW_SLICE_FIELDS_MISMATCH"], target.verify_raw_slice_receipt(value))

    def test_span_length_must_agree(self):
        self.assertIn(
            "RAW_SLICE_LENGTH_SPAN_MISMATCH",
            target.verify_raw_slice_receipt(raw_slice(target_slice_byte_len=5)),
        )

    def test_bool_cannot_impersonate_file_id(self):
        self.assertIn(
            "RAW_SLICE_INTEGER_INVALID:file_id",
            target.verify_raw_slice_receipt(raw_slice(file_id=True)),
        )

    def test_public_boundary_has_no_raw_to_host_or_effect_override(self):
        params = inspect.signature(target.admit_raw_slice_host_plane_separation).parameters
        for forbidden in (
            "raw_slice_host_pass", "promote_raw_slice_to_host", "host_effect_ready",
            "execution_authorized", "provider_effect_authorized",
        ):
            self.assertNotIn(forbidden, params)

    def test_receipt_identity_is_deterministic(self):
        with local_temporal_owner():
            first = target.admit_raw_slice_host_plane_separation(raw_slice_receipt=raw_slice())
            second = target.admit_raw_slice_host_plane_separation(raw_slice_receipt=raw_slice())
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
