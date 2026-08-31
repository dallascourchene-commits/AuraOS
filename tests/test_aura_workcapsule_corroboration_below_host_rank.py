from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest

from scripts import aura_workcapsule_portable_raw_slice_host_plane_separation as pr569
from scripts.aura_workcapsule_corroboration_below_host_rank import (
    PR569_VERSION,
    admit_corroboration_below_host_rank,
    verify_corroboration_below_host_rank,
)
from tests.test_aura_workcapsule_live_causal_corroboration import (
    pr568_receipt,
    pr572_receipt,
)
from tests.test_aura_workcapsule_portable_raw_slice_host_plane_separation import (
    Resolver,
    local_temporal_owner,
    portable_projection,
    resolution,
)
from scripts import aura_workcapsule_temporal_host_observation_admission as host_parent


def _canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def reseal_pr569(receipt: dict) -> dict:
    receipt = copy.deepcopy(receipt)
    receipt.pop("receipt_identity", None)
    receipt["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": PR569_VERSION,
        "value": hashlib.sha256(_canonical_bytes(receipt)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return receipt


def portable_host_receipt(*, all_pass=False):
    projection = portable_projection()
    if all_pass:
        supplied = {gate: {"probe": gate} for gate in host_parent.GATES}
        resolver = Resolver({gate: resolution(gate) for gate in host_parent.GATES})
        with local_temporal_owner():
            receipt = pr569.admit_portable_raw_slice_host_plane_separation(
                raw_slice_projection=projection,
                host_observations=supplied,
                host_observation_resolver=resolver,
            )
    else:
        supplied = {gate: projection for gate in host_parent.GATES}
        with local_temporal_owner():
            receipt = pr569.admit_portable_raw_slice_host_plane_separation(
                raw_slice_projection=projection,
                host_observations=supplied,
            )
    return projection, receipt


def corroborating_receipts(projection_digest: str):
    a = pr568_receipt()
    b = pr572_receipt(raw_slice_projection_payload_sha256=projection_digest)
    return a, b


class CorroborationBelowHostRankTests(unittest.TestCase):
    def test_two_exact_corroborating_proofs_do_not_promote_unknown_host_gates(self) -> None:
        projection, portable = portable_host_receipt()
        a, b = corroborating_receipts(projection["payload_sha256"])
        self.assertEqual(
            [],
            verify_corroboration_below_host_rank(
                portable_host_receipt=portable,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )
        out = admit_corroboration_below_host_rank(
            portable_host_receipt=portable,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertEqual(set(out["host_gate_states_before_corroboration"].values()), {"UNKNOWN"})
        self.assertEqual(
            out["host_gate_states_before_corroboration"],
            out["host_gate_states_after_corroboration"],
        )
        self.assertEqual(out["independent_corroborating_proof_count"], 2)
        self.assertTrue(out["corroboration_added_without_host_rank_change"])
        self.assertFalse(out["corroboration_used_as_host_observation"])
        self.assertFalse(out["corroboration_used_as_host_resolution"])
        self.assertFalse(out["portable_evidence_promoted_to_host_rank"])
        self.assertTrue(out["explicit_host_resolution_still_required_for_rank_change"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(any(out["authority"].values()))

    def test_explicit_host_resolver_can_pass_but_corroboration_is_not_the_cause(self) -> None:
        projection, portable = portable_host_receipt(all_pass=True)
        a, b = corroborating_receipts(projection["payload_sha256"])
        out = admit_corroboration_below_host_rank(
            portable_host_receipt=portable,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertEqual(set(out["host_gate_states_before_corroboration"].values()), {"PASS"})
        self.assertEqual(
            out["host_gate_states_before_corroboration"],
            out["host_gate_states_after_corroboration"],
        )
        self.assertTrue(out["host_observation_set_complete_after_corroboration"])
        self.assertEqual(
            out["host_disposition_after_corroboration"],
            "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING",
        )
        self.assertFalse(out["corroboration_used_as_host_resolution"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["effect_authority_proven"])

    def test_corroboration_of_different_portable_projection_cannot_attach(self) -> None:
        projection, portable = portable_host_receipt()
        a, b = corroborating_receipts("99" * 32)
        violations = verify_corroboration_below_host_rank(
            portable_host_receipt=portable,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertIn("PORTABLE_EVIDENCE_NOT_PR572_CORROBORATED_PROJECTION", violations)
        self.assertNotEqual(portable["portable_raw_slice_projection_digest"], b["raw_slice_projection_payload_sha256"])
        self.assertEqual(projection["payload_sha256"], portable["portable_raw_slice_projection_digest"])

    def test_resealed_pr569_host_rank_widening_is_rejected(self) -> None:
        projection, portable = portable_host_receipt()
        portable["portable_envelope_promoted_to_host_rank"] = True
        portable = reseal_pr569(portable)
        a, b = corroborating_receipts(projection["payload_sha256"])
        self.assertIn(
            "PR569_REQUIRED_FALSE:portable_envelope_promoted_to_host_rank",
            verify_corroboration_below_host_rank(
                portable_host_receipt=portable,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )

    def test_resealed_pr569_resolution_impersonation_is_rejected(self) -> None:
        projection, portable = portable_host_receipt()
        portable["portable_envelope_accepted_as_host_resolution"] = True
        portable = reseal_pr569(portable)
        a, b = corroborating_receipts(projection["payload_sha256"])
        self.assertIn(
            "PR569_REQUIRED_FALSE:portable_envelope_accepted_as_host_resolution",
            verify_corroboration_below_host_rank(
                portable_host_receipt=portable,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )

    def test_resealed_host_state_completion_lie_is_rejected(self) -> None:
        projection, portable = portable_host_receipt()
        portable["host_observation_set_complete"] = True
        portable = reseal_pr569(portable)
        a, b = corroborating_receipts(projection["payload_sha256"])
        self.assertIn(
            "PR569_HOST_COMPLETENESS_MISMATCH",
            verify_corroboration_below_host_rank(
                portable_host_receipt=portable,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )

    def test_corrob_parent_drift_rejects_before_quorum_claim(self) -> None:
        projection, portable = portable_host_receipt()
        a = pr568_receipt()
        b = pr572_receipt(
            raw_slice_projection_payload_sha256=projection["payload_sha256"],
            source_generation=44,
        )
        self.assertIn(
            "CORROBORATION_LIVE_SOURCE_INSTANCE_MISMATCH",
            verify_corroboration_below_host_rank(
                portable_host_receipt=portable,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )

    def test_public_boundary_has_no_quorum_rank_or_resolver_override(self) -> None:
        params = set(inspect.signature(verify_corroboration_below_host_rank).parameters)
        self.assertEqual(
            {"portable_host_receipt", "pr568_receipt", "pr572_receipt"},
            params,
        )
        for forbidden in (
            "quorum_host_pass",
            "corroboration_host_pass",
            "host_observation_resolver",
            "host_effect_ready",
            "execution_authorized",
        ):
            self.assertNotIn(forbidden, params)

    def test_admission_is_deterministic(self) -> None:
        projection, portable = portable_host_receipt()
        a, b = corroborating_receipts(projection["payload_sha256"])
        first = admit_corroboration_below_host_rank(
            portable_host_receipt=portable,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        second = admit_corroboration_below_host_rank(
            portable_host_receipt=copy.deepcopy(portable),
            pr568_receipt=copy.deepcopy(a),
            pr572_receipt=copy.deepcopy(b),
        )
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
