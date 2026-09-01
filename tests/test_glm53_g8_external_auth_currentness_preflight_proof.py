from dataclasses import replace
import unittest

from tools.awj032 import glm53_g8_external_auth_currentness_preflight as g8


class G8ExternalAuthCurrentnessPreflightProofTests(unittest.TestCase):
    def _compile(self, *, target=None, observation=None):
        progress, reuse, presented, q18, obs, default_target = g8.fixture_inputs()
        return g8.compile_external_auth_currentness_preflight(
            progress=progress,
            reuse=reuse,
            presented=presented,
            q20_q18=q18,
            q20_observation=observation or obs,
            target=target or default_target,
        )

    def test_positive_is_nonexecuting_preflight_only(self):
        receipt = self._compile()
        self.assertEqual(receipt.disposition, g8.COMPILED)
        self.assertTrue(receipt.preflight_request_compiled)
        self.assertTrue(receipt.exact_g7_parent_bound)
        self.assertTrue(receipt.exact_q20_parent_bound)
        self.assertTrue(receipt.source_view_relation_bound)
        self.assertTrue(receipt.parent_debts_preserved)
        for field in (
            "parent_producer_authenticated",
            "presented_currentness_authenticated",
            "future_read_currentness_proven",
            "effect_time_source_head_observed",
            "effect_time_source_currentness_proven",
            "q20_observation_still_current_at_effect",
            "tensor_payload_bound",
            "owner_host_execution_observed",
            "execution_authorized",
            "effect_authorized",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            self.assertFalse(getattr(receipt, field), field)

    def test_deterministic_receipt(self):
        self.assertEqual(self._compile().request_digest, self._compile().request_digest)

    def test_incomplete_external_target_holds(self):
        *_, target = g8.fixture_inputs()
        receipt = self._compile(target=replace(target, principal_ref=""))
        self.assertEqual(receipt.disposition, g8.HOLD_TARGET)
        self.assertFalse(receipt.preflight_request_compiled)

    def test_target_cannot_self_mint_authority(self):
        *_, target = g8.fixture_inputs()
        with self.assertRaisesRegex(ValueError, "G8_TARGET_CANNOT_SELF_SATISFY"):
            self._compile(target=replace(target, execution_authorized_by_request=True))

    def test_q20_head_substitution_fails_closed(self):
        progress, reuse, presented, q18, obs, target = g8.fixture_inputs()
        bad = replace(obs, observed_head_revision="0" * 40)
        with self.assertRaisesRegex(ValueError, "OBSERVED_HEAD_REVISION_REOPEN_REQUIRED"):
            g8.compile_external_auth_currentness_preflight(
                progress=progress,
                reuse=reuse,
                presented=presented,
                q20_q18=q18,
                q20_observation=bad,
                target=target,
            )

    def test_complete_different_j_lattice(self):
        self.assertEqual(g8.prove_different_j(), 128)

    def test_laws_preserve_coordinate_kv_boundary(self):
        self.assertIn("K27Coordinate!=SourceIdentity!=Currentness!=Authority", g8.LAWS)
        self.assertIn("CoordinateMemory!=MODEL_PREFIX_KV", g8.LAWS)


if __name__ == "__main__":
    unittest.main()
