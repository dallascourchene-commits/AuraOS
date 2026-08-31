from __future__ import annotations

import inspect
import unittest

from scripts.aura_workcapsule_live_causal_corroboration import (
    admit_live_causal_corroboration,
)
from scripts.aura_workcapsule_corroboration_causal_host_lineage import (
    CAUSAL_O10_WORLD_MISMATCH,
    MIXED_LINEAGES,
    TARGET_NOT_CORROBORATED,
    admit_corroboration_causal_host_lineage,
    verify_corroboration_causal_host_lineage,
)
from tests.test_aura_workcapsule_causal_artifact_qualified_host_envelope import (
    WorkCapsuleCausalArtifactQualifiedHostEnvelopeTests,
    _seal_causal,
    _sha,
)
from tests.test_aura_workcapsule_live_causal_corroboration import (
    pr568_receipt,
    pr572_receipt,
)


class CorroborationCausalHostLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.host_case = WorkCapsuleCausalArtifactQualifiedHostEnvelopeTests(
            methodName="test_exact_causal_host_envelope_binds_to_exact_artifact"
        )
        self.host_case.setUp()
        self.a = pr568_receipt()
        self.b = pr572_receipt()
        self.corroboration = admit_live_causal_corroboration(
            pr568_receipt=self.a,
            pr572_receipt=self.b,
        )

    def tearDown(self) -> None:
        self.host_case.tearDown()

    def host(self, *, target_ref=None, states=None, o10=None) -> dict:
        target = target_ref or self.corroboration["pr568_artifact_ref"]
        return self.host_case.causal_host_receipt(
            states=states,
            target_ref=target,
            post_closure_receipt_identity=(
                o10 if o10 is not None else self.a["causal_post_closure_receipt_identity"]
            ),
        )

    def kwargs(self, *, host=None) -> dict:
        return {
            "pr568_receipt": self.a,
            "pr572_receipt": self.b,
            "causal_host_admission_receipt": host if host is not None else self.host(),
        }

    def test_one_resolved_gate_may_target_exact_pr568_lineage(self) -> None:
        self.assertEqual([], verify_corroboration_causal_host_lineage(**self.kwargs()))
        out = admit_corroboration_causal_host_lineage(**self.kwargs())
        self.assertEqual(
            self.corroboration["pr568_artifact_ref"],
            out["observed_proof_artifact_ref"],
        )
        self.assertEqual(
            self.corroboration["pr572_artifact_ref"],
            out["corroborating_peer_artifact_ref"],
        )
        self.assertFalse(out["host_observation_transferred_to_peer_artifact"])
        self.assertTrue(out["proof_artifacts_remain_distinct"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_one_resolved_gate_may_target_exact_pr572_lineage(self) -> None:
        host = self.host(target_ref=self.corroboration["pr572_artifact_ref"])
        out = admit_corroboration_causal_host_lineage(**self.kwargs(host=host))
        self.assertEqual(
            self.corroboration["pr572_artifact_ref"],
            out["observed_proof_artifact_ref"],
        )
        self.assertEqual(
            self.corroboration["pr568_artifact_ref"],
            out["corroborating_peer_artifact_ref"],
        )
        self.assertFalse(out["host_observation_transferred_to_peer_artifact"])

    def test_mixed_correlated_lineages_cannot_assemble_one_host_envelope(self) -> None:
        states = {
            "U_HEAD": "PASS",
            "U_ROUTE": "PASS",
            "U_F2": "UNKNOWN",
            "U_CUSTODY": "UNKNOWN",
            "U_CANARY": "UNKNOWN",
        }
        host = self.host(
            target_ref=self.corroboration["pr568_artifact_ref"], states=states
        )
        route = host["host_gate_resolutions"]["U_ROUTE"]
        route["target_ref"] = self.corroboration["pr572_artifact_ref"]
        route.pop("resolution_digest", None)
        route["resolution_digest"] = _sha(route)
        _seal_causal(host)
        self.assertIn(
            MIXED_LINEAGES,
            verify_corroboration_causal_host_lineage(**self.kwargs(host=host)),
        )

    def test_foreign_target_is_not_laundered_by_corroboration(self) -> None:
        host = self.host(target_ref="aura-proof-artifact-sha256:" + "cd" * 32)
        violations = verify_corroboration_causal_host_lineage(**self.kwargs(host=host))
        self.assertIn(f"{TARGET_NOT_CORROBORATED}:U_HEAD", violations)

    def test_valid_causal_envelope_from_foreign_o10_world_rejects(self) -> None:
        host = self.host(o10={"kind": "DIGEST", "value": "ef" * 32})
        self.assertIn(
            CAUSAL_O10_WORLD_MISMATCH,
            verify_corroboration_causal_host_lineage(**self.kwargs(host=host)),
        )

    def test_no_resolved_host_gate_does_not_observe_either_lineage(self) -> None:
        states = {gate: "UNKNOWN" for gate in (
            "U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY"
        )}
        out = admit_corroboration_causal_host_lineage(
            **self.kwargs(host=self.host(states=states))
        )
        self.assertEqual(0, out["resolved_host_gate_count"])
        self.assertIsNone(out["observed_proof_artifact_ref"])
        self.assertIsNone(out["corroborating_peer_artifact_ref"])
        self.assertFalse(out["host_observation_set_complete"])

    def test_all_pass_for_one_lineage_remains_nonauthorizing(self) -> None:
        states = {gate: "PASS" for gate in (
            "U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY"
        )}
        out = admit_corroboration_causal_host_lineage(
            **self.kwargs(host=self.host(states=states))
        )
        self.assertTrue(out["host_observation_set_complete"])
        self.assertTrue(out["all_resolved_host_gates_share_one_proof_lineage"])
        self.assertFalse(out["host_resolver_trust_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_corroboration_parent_tamper_fails_before_host_relation(self) -> None:
        self.b["source_generation"] = 44
        violations = verify_corroboration_causal_host_lineage(**self.kwargs())
        self.assertTrue(any(item.startswith("CORROBORATION_") for item in violations))

    def test_causal_envelope_integrity_tamper_fails_before_lineage_relation(self) -> None:
        host = self.host()
        host["unknown_mask"] = 0
        _seal_causal(host)
        violations = verify_corroboration_causal_host_lineage(**self.kwargs(host=host))
        self.assertTrue(any(item.startswith("CAUSAL_HOST_ENVELOPE_") for item in violations))

    def test_public_boundary_is_three_evidence_objects_only(self) -> None:
        params = set(inspect.signature(verify_corroboration_causal_host_lineage).parameters)
        self.assertEqual(
            {"pr568_receipt", "pr572_receipt", "causal_host_admission_receipt"},
            params,
        )
        for forbidden in (
            "selected_lineage",
            "artifact_target_ref",
            "host_observation_resolver",
            "semantic_truth",
            "effect_ready",
            "execution_authorized",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    unittest.main()
