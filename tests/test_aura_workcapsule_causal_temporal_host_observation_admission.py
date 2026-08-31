from __future__ import annotations

import inspect
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from scripts import aura_workcapsule_causal_temporal_host_observation_admission as target
from tests.test_aura_workcapsule_temporal_host_observation_admission import (
    FakeResolver,
    observations,
    resolution,
)


def causal_admission(*, post_status="CLOSED", exact=True, fresh_post=False):
    return {
        "raw_owner_pre_lifecycle_derived": True,
        "raw_owner_post_candidate_derived": True,
        "post_o10_closure_derived": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": fresh_post,
        "pre_closure_status": "HOLD",
        "post_closure_status": post_status,
        "exact_hold_to_closed_transition": exact,
        "pre_reentry_receipt_identity": {"kind": "DIGEST", "value": "1" * 64},
        "post_o10_closure_receipt_identity": {"kind": "DIGEST", "value": "2" * 64},
    }


@contextmanager
def causal_owner(*, admission=None, violations=None):
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                target,
                "verify_raw_owner_derived_post_closure_transition",
                return_value=list(violations or []),
            )
        )
        stack.enter_context(
            patch.object(
                target,
                "admit_raw_owner_derived_post_closure_transition",
                return_value=admission or causal_admission(),
            )
        )
        yield


class CausalTemporalHostObservationAdmissionTests(unittest.TestCase):
    def test_no_resolver_preserves_same_five_unknown_host_gates(self):
        with causal_owner():
            out = target.admit_causal_temporal_host_observation_admission(
                host_observations=observations()
            )
        self.assertTrue(out["causal_temporal_owner_reproved"])
        self.assertTrue(out["pre_reentry_receipt_reused_for_post_o10"])
        self.assertFalse(out["fresh_post_reentry_receipt_substituted"])
        self.assertEqual(out["disposition"], "HOST_OBSERVATION_REQUIRED")
        self.assertEqual(out["fail_mask"], 0)
        self.assertEqual(out["unknown_mask"], 31)
        self.assertEqual(set(out["host_gate_states"].values()), {"UNKNOWN"})
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(out["local_evidence_promoted_to_host_rank"])

    def test_all_resolved_pass_remains_complete_but_nonauthorizing(self):
        resolver = FakeResolver({gate: resolution(gate) for gate in target.GATES})
        with causal_owner():
            out = target.admit_causal_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=resolver,
            )
        self.assertEqual(out["disposition"], "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING")
        self.assertEqual(out["fail_mask"], 0)
        self.assertEqual(out["unknown_mask"], 0)
        self.assertTrue(out["host_observation_set_complete"])
        self.assertFalse(out["resolver_trust_proven_by_this_module"])
        self.assertFalse(out["host_observation_authority_proven_by_this_module"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_revoked_resolution_still_fails_closed(self):
        by_gate = {gate: resolution(gate) for gate in target.GATES}
        by_gate["U_ROUTE"] = resolution("U_ROUTE", revoked=True)
        with causal_owner():
            out = target.admit_causal_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=FakeResolver(by_gate),
            )
        self.assertEqual(out["disposition"], "FAIL_CLOSED")
        self.assertEqual(out["fail_mask"], 2)
        self.assertFalse(out["host_effect_ready"])

    def test_causal_temporal_failure_propagates_before_host_rank(self):
        with causal_owner(violations=["PR518_TWO_PHASE_PRE_POST_EVIDENCE_ROOTS_NOT_DISTINCT"]):
            with self.assertRaisesRegex(ValueError, "TEMPORAL_PR518_TWO_PHASE"):
                target.admit_causal_temporal_host_observation_admission(
                    host_observations={}
                )

    def test_fresh_post_reentry_substitution_cannot_be_laundered_into_host_readiness(self):
        with causal_owner(admission=causal_admission(fresh_post=True)):
            with self.assertRaisesRegex(ValueError, "CAUSAL_FRESH_POST_REENTRY_SUBSTITUTED"):
                target.admit_causal_temporal_host_observation_admission(
                    host_observations={}
                )

    def test_post_hold_cannot_be_promoted_by_host_plane(self):
        with causal_owner(admission=causal_admission(post_status="HOLD", exact=False)):
            with self.assertRaisesRegex(ValueError, "CAUSAL_POST_NOT_CLOSED"):
                target.admit_causal_temporal_host_observation_admission(
                    host_observations={}
                )

    def test_host_probe_order_is_unchanged_from_pr559(self):
        by_gate = {
            gate: resolution(gate)
            for gate in target.GATES
            if gate != "U_CUSTODY"
        }
        supplied = {
            gate: {"pointer": gate}
            for gate in target.GATES
            if gate != "U_CUSTODY"
        }
        with causal_owner():
            out = target.admit_causal_temporal_host_observation_admission(
                host_observations=supplied,
                host_observation_resolver=FakeResolver(by_gate),
            )
        self.assertEqual(out["candidate_probes_by_unknown_gate"]["U_CUSTODY"], ["P_CUSTODY", "P_ROUTE"])
        self.assertEqual(out["ordered_required_probes"], ["P_ROUTE", "P_CUSTODY"])
        self.assertFalse(out["minimum_cover_computed"])

    def test_public_boundary_accepts_no_temporal_or_effect_intermediate(self):
        params = inspect.signature(
            target.admit_causal_temporal_host_observation_admission
        ).parameters
        for forbidden in (
            "temporal_receipt",
            "post_closure_receipt",
            "reentry_receipt",
            "candidate_binding",
            "host_effect_ready",
            "execution_authorized",
            "provider_effect_authorized",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    unittest.main()
