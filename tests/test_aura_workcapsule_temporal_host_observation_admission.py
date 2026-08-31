from __future__ import annotations

import inspect
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from scripts import aura_workcapsule_temporal_host_observation_admission as target


class FakeResolver:
    def __init__(self, by_gate=None, *, raises=False):
        self.by_gate = dict(by_gate or {})
        self.raises = raises

    def resolve(self, *, gate, observation):
        if self.raises:
            raise RuntimeError("host unavailable")
        return self.by_gate.get(gate)


def local_admission(*, post_status="CLOSED", exact=True):
    return {
        "pre_closure_status": "HOLD",
        "post_closure_status": post_status,
        "exact_hold_to_closed_transition": exact,
        "pre_reentry_receipt_identity": {
            "kind": "DIGEST",
            "value": "1" * 64,
        },
        "post_closure_receipt_identity": {
            "kind": "DIGEST",
            "value": "2" * 64,
        },
    }


@contextmanager
def local_owner(*, admission=None, violations=None):
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(
                target,
                "verify_preplan_post_observation_transition",
                return_value=list(violations or []),
            )
        )
        stack.enter_context(
            patch.object(
                target,
                "admit_preplan_post_observation_transition",
                return_value=admission or local_admission(),
            )
        )
        yield


def resolution(gate, state="PASS", *, revoked=False, **overrides):
    value = {
        "schema": target.HOST_RESOLUTION_SCHEMA,
        "version": target.HOST_RESOLUTION_VERSION,
        "gate": gate,
        "state": state,
        "observation_ref": f"obs:{gate}",
        "producer_ref": f"producer:{gate}",
        "producer_generation": "producer-gen-1",
        "currentness_ref": f"current:{gate}",
        "authority_ref": f"authority:{gate}",
        "target_ref": f"target:{gate}",
        "resolver_ref": "host-observation-resolver-v1",
        "resolver_generation": "resolver-gen-1",
        "revoked": revoked,
        "resolution_digest": "0" * 64,
    }
    value.update(overrides)
    value["resolution_digest"] = target._resolution_digest(value)
    return value


def observations():
    return {gate: {"pointer": f"opaque:{gate}"} for gate in target.GATES}


class TemporalHostObservationAdmissionTests(unittest.TestCase):
    def test_no_resolver_preserves_all_unknowns(self):
        with local_owner():
            out = target.admit_temporal_host_observation_admission(
                host_observations=observations()
            )
        self.assertEqual(out["disposition"], "HOST_OBSERVATION_REQUIRED")
        self.assertEqual(out["fail_mask"], 0)
        self.assertEqual(out["unknown_mask"], 31)
        self.assertEqual(set(out["host_gate_states"].values()), {"UNKNOWN"})
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(out["local_evidence_promoted_to_host_rank"])
        self.assertFalse(out["drive_pointer_presence_promoted_to_pass"])
        self.assertFalse(out["cache_or_coordinate_presence_promoted_to_pass"])

    def test_all_resolved_pass_is_complete_but_nonauthorizing(self):
        resolver = FakeResolver({gate: resolution(gate) for gate in target.GATES})
        with local_owner():
            out = target.admit_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=resolver,
            )
        self.assertEqual(
            out["disposition"], "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING"
        )
        self.assertEqual(out["fail_mask"], 0)
        self.assertEqual(out["unknown_mask"], 0)
        self.assertTrue(out["host_observation_set_complete"])
        self.assertFalse(out["resolver_trust_proven_by_this_module"])
        self.assertFalse(out["host_observation_authority_proven_by_this_module"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertTrue(all(v is False for v in out["authority"].values()))

    def test_revoked_resolution_fails_closed(self):
        by_gate = {gate: resolution(gate) for gate in target.GATES}
        by_gate["U_ROUTE"] = resolution("U_ROUTE", revoked=True)
        with local_owner():
            out = target.admit_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=FakeResolver(by_gate),
            )
        self.assertEqual(out["disposition"], "FAIL_CLOSED")
        self.assertEqual(out["fail_mask"], 2)
        self.assertEqual(out["host_gate_reasons"]["U_ROUTE"], "RESOLUTION_REVOKED")
        self.assertFalse(out["host_effect_ready"])

    def test_explicit_fail_fails_closed_without_authority(self):
        by_gate = {gate: resolution(gate) for gate in target.GATES}
        by_gate["U_F2"] = resolution("U_F2", state="FAIL")
        with local_owner():
            out = target.admit_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=FakeResolver(by_gate),
            )
        self.assertEqual(out["disposition"], "FAIL_CLOSED")
        self.assertEqual(out["fail_mask"], 4)
        self.assertFalse(out["host_effect_ready"])

    def test_resolver_exception_preserves_unknown(self):
        with local_owner():
            out = target.admit_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=FakeResolver(raises=True),
            )
        self.assertEqual(out["unknown_mask"], 31)
        self.assertTrue(
            all(
                reason.startswith("RESOLVER_EXCEPTION:")
                for reason in out["host_gate_reasons"].values()
            )
        )

    def test_cross_gate_resolution_replay_is_rejected(self):
        by_gate = {gate: resolution(gate) for gate in target.GATES}
        by_gate["U_ROUTE"] = resolution("U_HEAD")
        with local_owner():
            with self.assertRaisesRegex(ValueError, "HOST_RESOLUTION_GATE_MISMATCH"):
                target.admit_temporal_host_observation_admission(
                    host_observations=observations(),
                    host_observation_resolver=FakeResolver(by_gate),
                )

    def test_resolution_digest_tamper_is_rejected(self):
        bad = resolution("U_HEAD")
        bad["target_ref"] = "target:tampered-after-digest"
        by_gate = {gate: resolution(gate) for gate in target.GATES}
        by_gate["U_HEAD"] = bad
        with local_owner():
            with self.assertRaisesRegex(ValueError, "HOST_RESOLUTION_DIGEST_MISMATCH"):
                target.admit_temporal_host_observation_admission(
                    host_observations=observations(),
                    host_observation_resolver=FakeResolver(by_gate),
                )

    def test_missing_authority_binding_is_rejected(self):
        bad = resolution("U_CUSTODY", authority_ref="")
        by_gate = {gate: resolution(gate) for gate in target.GATES}
        by_gate["U_CUSTODY"] = bad
        with local_owner():
            with self.assertRaisesRegex(
                ValueError, "HOST_RESOLUTION_BINDING_MISSING:authority_ref"
            ):
                target.admit_temporal_host_observation_admission(
                    host_observations=observations(),
                    host_observation_resolver=FakeResolver(by_gate),
                )

    def test_unknown_extra_gate_is_rejected(self):
        supplied = observations()
        supplied["U_INVENTED"] = {"pointer": "invented"}
        with local_owner():
            with self.assertRaisesRegex(ValueError, "HOST_OBSERVATIONS_UNKNOWN_GATE"):
                target.admit_temporal_host_observation_admission(
                    host_observations=supplied
                )

    def test_falsey_non_mapping_observations_are_rejected(self):
        with local_owner():
            with self.assertRaisesRegex(ValueError, "HOST_OBSERVATIONS_NOT_MAPPING"):
                target.admit_temporal_host_observation_admission(
                    host_observations=[]  # type: ignore[arg-type]
                )

    def test_temporal_owner_failure_propagates(self):
        with local_owner(violations=["POST_NOT_CLOSED"]):
            with self.assertRaisesRegex(ValueError, "TEMPORAL_POST_NOT_CLOSED"):
                target.admit_temporal_host_observation_admission(
                    host_observations={}
                )

    def test_local_post_hold_cannot_be_promoted(self):
        with local_owner(admission=local_admission(post_status="HOLD", exact=False)):
            with self.assertRaisesRegex(ValueError, "O32_POST_NOT_CLOSED"):
                target.admit_temporal_host_observation_admission(
                    host_observations={}
                )

    def test_missing_only_custody_reports_candidate_probe_without_fake_optimum(self):
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
        with local_owner():
            out = target.admit_temporal_host_observation_admission(
                host_observations=supplied,
                host_observation_resolver=FakeResolver(by_gate),
            )
        self.assertEqual(out["host_gate_states"]["U_CUSTODY"], "UNKNOWN")
        self.assertEqual(
            out["candidate_probes_by_unknown_gate"]["U_CUSTODY"],
            ["P_CUSTODY", "P_ROUTE"],
        )
        self.assertEqual(out["ordered_required_probes"], ["P_ROUTE", "P_CUSTODY"])
        self.assertFalse(out["minimum_cover_computed"])

    def test_resolver_can_return_explicit_unknown(self):
        by_gate = {gate: resolution(gate) for gate in target.GATES}
        by_gate["U_CANARY"] = resolution("U_CANARY", state="UNKNOWN")
        with local_owner():
            out = target.admit_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=FakeResolver(by_gate),
            )
        self.assertEqual(out["unknown_mask"], 16)
        self.assertEqual(out["disposition"], "HOST_OBSERVATION_REQUIRED")
        self.assertEqual(out["ordered_required_probes"], ["P_CANARY"])

    def test_public_boundary_has_no_local_receipt_or_effect_override(self):
        params = inspect.signature(
            target.admit_temporal_host_observation_admission
        ).parameters
        self.assertNotIn("temporal_receipt", params)
        self.assertNotIn("post_closure_receipt", params)
        self.assertNotIn("host_effect_ready", params)
        self.assertNotIn("execution_authorized", params)
        self.assertNotIn("provider_effect_authorized", params)

    def test_receipt_identity_is_deterministic(self):
        resolver = FakeResolver({gate: resolution(gate) for gate in target.GATES})
        with local_owner():
            first = target.admit_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=resolver,
            )
            second = target.admit_temporal_host_observation_admission(
                host_observations=observations(),
                host_observation_resolver=resolver,
            )
        self.assertEqual(first, second)
        self.assertEqual(len(first["receipt_identity"]["value"]), 64)


if __name__ == "__main__":
    unittest.main()
