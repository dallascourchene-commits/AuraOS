from __future__ import annotations

import copy
import hashlib
import inspect
import unittest

from scripts import aura_workcapsule_temporal_host_observation_admission as host_parent
from scripts import aura_workcapsule_portable_raw_slice_host_plane_separation as target
from scripts.aura_k27_astge_portable_raw_slice_causal_handoff import (
    CANONICALIZATION,
    PAYLOAD_FIELDS,
    SCHEMA,
    canonical_raw_slice_payload_bytes,
)
from tests.test_aura_workcapsule_raw_slice_host_plane_separation import (
    Resolver,
    local_temporal_owner,
    raw_slice,
    resolution,
)


def portable_projection(**raw_overrides):
    raw = raw_slice(**raw_overrides)
    payload = {}
    for field in PAYLOAD_FIELDS:
        if field == "schema":
            payload[field] = SCHEMA
        elif field == "version":
            payload[field] = 1
        elif field == "canonicalization_profile":
            payload[field] = CANONICALIZATION
        elif field == "raw_slice_version":
            payload[field] = raw["version"]
        else:
            payload[field] = raw[field]
    return {
        "payload": payload,
        "payload_sha256": hashlib.sha256(canonical_raw_slice_payload_bytes(payload)).hexdigest(),
    }


class PortableRawSliceHostPlaneSeparationTests(unittest.TestCase):
    def test_portable_projection_derives_exact_existing_raw_receipt_view(self):
        projection = portable_projection()
        view = target.portable_projection_to_raw_slice_receipt(projection)
        self.assertEqual(raw_slice(), view)

    def test_portable_envelope_at_every_host_gate_remains_unknown_without_resolver(self):
        projection = portable_projection()
        supplied = {gate: projection for gate in host_parent.GATES}
        with local_temporal_owner():
            out = target.admit_portable_raw_slice_host_plane_separation(
                raw_slice_projection=projection,
                host_observations=supplied,
            )
        self.assertTrue(out["portable_raw_slice_projection_verified"])
        self.assertTrue(out["raw_slice_receipt_view_derived"])
        self.assertEqual(set(out["host_gate_states"].values()), {"UNKNOWN"})
        self.assertEqual(out["host_disposition"], "HOST_OBSERVATION_REQUIRED")
        self.assertFalse(out["portable_envelope_promoted_to_host_rank"])
        self.assertFalse(out["portable_envelope_accepted_as_host_resolution"])
        self.assertFalse(out["host_effect_ready"])

    def test_portable_envelope_cannot_impersonate_host_resolution(self):
        projection = portable_projection()
        supplied = {gate: {"portable_raw_slice": True} for gate in host_parent.GATES}
        resolver = Resolver({gate: projection for gate in host_parent.GATES})
        with local_temporal_owner():
            with self.assertRaisesRegex(ValueError, "HOST_RESOLUTION_FIELDS_MISMATCH"):
                target.admit_portable_raw_slice_host_plane_separation(
                    raw_slice_projection=projection,
                    host_observations=supplied,
                    host_observation_resolver=resolver,
                )

    def test_real_host_resolution_can_complete_but_portable_evidence_stays_nonauthorizing(self):
        projection = portable_projection()
        supplied = {gate: {"probe": gate} for gate in host_parent.GATES}
        resolver = Resolver({gate: resolution(gate) for gate in host_parent.GATES})
        with local_temporal_owner():
            out = target.admit_portable_raw_slice_host_plane_separation(
                raw_slice_projection=projection,
                host_observations=supplied,
                host_observation_resolver=resolver,
            )
        self.assertTrue(out["host_observation_set_complete"])
        self.assertEqual(out["host_disposition"], "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING")
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["producer_authenticated"])
        self.assertFalse(any(out["authority"].values()))

    def test_portable_digest_tamper_rejects_before_host_plane(self):
        projection = portable_projection()
        projection["payload_sha256"] = "0" * 64
        violations = target.verify_portable_raw_slice_host_plane_separation(
            raw_slice_projection=projection
        )
        self.assertTrue(any("PAYLOAD_DIGEST_MISMATCH" in item for item in violations))

    def test_portable_semantic_identity_widening_rejects_even_when_resealed(self):
        projection = portable_projection()
        projection["payload"]["semantic_identity_proven_by_raw_slice"] = True
        projection["payload_sha256"] = hashlib.sha256(
            canonical_raw_slice_payload_bytes(projection["payload"])
        ).hexdigest()
        violations = target.verify_portable_raw_slice_host_plane_separation(
            raw_slice_projection=projection
        )
        self.assertTrue(
            any("CEILING_VIOLATION:semantic_identity_proven_by_raw_slice" in item for item in violations)
        )

    def test_unknown_portable_field_fails_closed(self):
        projection = portable_projection()
        projection["payload"]["host_gate_pass"] = False
        projection["payload_sha256"] = "0" * 64
        violations = target.verify_portable_raw_slice_host_plane_separation(
            raw_slice_projection=projection
        )
        self.assertTrue(any("PAYLOAD_CLOSED_SCHEMA_VIOLATION" in item for item in violations))

    def test_projection_and_view_digests_are_deterministic_but_distinct_objects(self):
        projection = portable_projection()
        with local_temporal_owner():
            first = target.admit_portable_raw_slice_host_plane_separation(
                raw_slice_projection=copy.deepcopy(projection)
            )
            second = target.admit_portable_raw_slice_host_plane_separation(
                raw_slice_projection=copy.deepcopy(projection)
            )
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["portable_raw_slice_projection_digest"]))
        self.assertEqual(64, len(first["raw_slice_receipt_view_digest"]))
        self.assertEqual(64, len(first["receipt_identity"]["value"]))

    def test_public_boundary_has_no_portable_to_host_rank_override(self):
        params = inspect.signature(target.admit_portable_raw_slice_host_plane_separation).parameters
        self.assertIn("raw_slice_projection", params)
        self.assertNotIn("raw_slice_receipt", params)
        for forbidden in (
            "portable_host_pass",
            "promote_portable_to_host",
            "host_effect_ready",
            "execution_authorized",
            "provider_effect_authorized",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    unittest.main()
