from __future__ import annotations

import inspect
import unittest

from scripts.aura_workcapsule_current_causal_corroboration_member import (
    O10_MISMATCH,
    STATE_VECTOR_MISMATCH,
    TARGET_REF_MISMATCH,
    admit_current_causal_corroboration_member,
    verify_current_causal_corroboration_member,
)
from tests.test_aura_workcapsule_causal_artifact_qualified_host_envelope import (
    WorkCapsuleCausalArtifactQualifiedHostEnvelopeTests,
    _seal_causal,
)
from tests.test_aura_workcapsule_corroboration_qualified_host_member import (
    live_host_receipt,
)
from tests.test_aura_workcapsule_live_causal_corroboration import (
    pr568_receipt,
    pr572_receipt,
)


class CurrentCausalCorroborationMemberTests(unittest.TestCase):
    def setUp(self) -> None:
        self.host_case = WorkCapsuleCausalArtifactQualifiedHostEnvelopeTests(
            methodName="test_exact_causal_host_envelope_binds_to_exact_artifact"
        )
        self.host_case.setUp()
        self.a = pr568_receipt()
        self.b = pr572_receipt()

    def tearDown(self) -> None:
        self.host_case.tearDown()

    def causal_host(self, live: dict, *, target_ref=None, states=None, o10=None) -> dict:
        return self.host_case.causal_host_receipt(
            states=(states if states is not None else live["host_gate_states"]),
            target_ref=(target_ref or live["live_causal_artifact_target_ref"]),
            post_closure_receipt_identity=(
                o10 if o10 is not None else self.a["causal_post_closure_receipt_identity"]
            ),
        )

    def kwargs(self, *, live=None, causal=None) -> dict:
        chosen_live = live if live is not None else live_host_receipt(pr568=self.a)
        return {
            "live_host_receipt": chosen_live,
            "pr568_receipt": self.a,
            "pr572_receipt": self.b,
            "causal_host_admission_receipt": (
                causal if causal is not None else self.causal_host(chosen_live)
            ),
        }

    def test_unknown_state_vector_binds_same_member_without_host_promotion(self) -> None:
        kwargs = self.kwargs()
        self.assertEqual([], verify_current_causal_corroboration_member(**kwargs))
        out = admit_current_causal_corroboration_member(**kwargs)
        self.assertTrue(out["corroboration_qualified_pr568_member_reproved"])
        self.assertTrue(out["current_causal_host_envelope_integrity_checked"])
        self.assertTrue(out["same_causal_o10_world_proven"])
        self.assertTrue(out["same_host_gate_state_vector_proven"])
        self.assertEqual(0, out["resolved_host_gate_count"])
        self.assertFalse(out["host_observation_set_complete"])
        self.assertFalse(out["host_observation_transferred_to_pr572_sibling"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_all_pass_same_target_same_o10_remains_nonauthorizing(self) -> None:
        live = live_host_receipt(pr568=self.a, all_pass=True)
        kwargs = self.kwargs(live=live)
        self.assertEqual([], verify_current_causal_corroboration_member(**kwargs))
        out = admit_current_causal_corroboration_member(**kwargs)
        self.assertTrue(out["host_observation_set_complete"])
        self.assertEqual(5, out["resolved_host_gate_count"])
        self.assertTrue(out["resolved_host_gates_bound_to_same_pr568_host_target"])
        self.assertFalse(out["host_resolver_trust_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])

    def test_same_target_and_o10_but_different_state_vector_rejects(self) -> None:
        live = live_host_receipt(pr568=self.a)
        states = dict(live["host_gate_states"])
        states["U_HEAD"] = "PASS"
        causal = self.causal_host(live, states=states)
        self.assertIn(
            STATE_VECTOR_MISMATCH,
            verify_current_causal_corroboration_member(
                **self.kwargs(live=live, causal=causal)
            ),
        )

    def test_same_state_and_o10_but_foreign_target_rejects(self) -> None:
        live = live_host_receipt(pr568=self.a, all_pass=True)
        causal = self.causal_host(
            live,
            target_ref="aura-workcapsule-target-sha256:" + "cd" * 32,
        )
        violations = verify_current_causal_corroboration_member(
            **self.kwargs(live=live, causal=causal)
        )
        self.assertTrue(
            all(f"{TARGET_REF_MISMATCH}:{gate}" in violations for gate in (
                "U_HEAD", "U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY"
            ))
        )

    def test_same_state_and_target_but_foreign_o10_rejects(self) -> None:
        live = live_host_receipt(pr568=self.a)
        causal = self.causal_host(
            live,
            o10={"kind": "DIGEST", "value": "ef" * 32},
        )
        self.assertIn(
            O10_MISMATCH,
            verify_current_causal_corroboration_member(
                **self.kwargs(live=live, causal=causal)
            ),
        )

    def test_pr572_sibling_alias_still_rejects_before_current_relation(self) -> None:
        sibling_live = live_host_receipt(
            pr568=self.a,
            target_ref="aura-workcapsule-target-sha256:" + "00" * 32,
        )
        violations = verify_current_causal_corroboration_member(
            **self.kwargs(live=sibling_live)
        )
        self.assertTrue(any(item.startswith("CORROBORATION_MEMBER_") for item in violations))

    def test_current_causal_envelope_integrity_tamper_rejects_before_relation(self) -> None:
        live = live_host_receipt(pr568=self.a)
        causal = self.causal_host(live)
        causal["unknown_mask"] = 0
        _seal_causal(causal)
        violations = verify_current_causal_corroboration_member(
            **self.kwargs(live=live, causal=causal)
        )
        self.assertTrue(any(item.startswith("CURRENT_CAUSAL_HOST_") for item in violations))

    def test_public_boundary_is_four_closed_evidence_objects_only(self) -> None:
        params = set(inspect.signature(verify_current_causal_corroboration_member).parameters)
        self.assertEqual(
            {
                "live_host_receipt",
                "pr568_receipt",
                "pr572_receipt",
                "causal_host_admission_receipt",
            },
            params,
        )
        for forbidden in (
            "host_observation_resolver",
            "artifact_ref_override",
            "selected_lineage",
            "semantic_truth",
            "effect_ready",
            "execution_authorized",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    unittest.main()
