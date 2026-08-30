import unittest

from tools.bughound.trust_boundary_seed import (
    IdentityScopeObservationV1,
    ScopeDisposition,
    memanto_namespace_drift_seed,
    modeled_current_validation_accepts,
)


SOURCE_GEN = "3bfde8e4eacea1a78b028f7f672ac285afc57b59"
PATHS = ("memanto/app/core.py", "memanto/app/services/session_service.py")


class BugHoundTrustBoundarySeedTests(unittest.TestCase):
    def test_exact_scope_matches(self):
        obs = IdentityScopeObservationV1(
            signed_agent_id="alpha",
            persisted_agent_id="alpha",
            persisted_namespace="memanto_agent_alpha",
            source_repository="moorcheh-ai/memanto",
            source_generation=SOURCE_GEN,
            source_paths=PATHS,
        )
        self.assertEqual(ScopeDisposition.SCOPE_MATCHED, obs.disposition)
        self.assertFalse(obs.vulnerability_proven)
        self.assertFalse(obs.external_effect)
        self.assertFalse(obs.authority)

    def test_signed_persisted_agent_mismatch_is_distinct(self):
        obs = IdentityScopeObservationV1(
            signed_agent_id="alpha",
            persisted_agent_id="beta",
            persisted_namespace="memanto_agent_beta",
            source_repository="moorcheh-ai/memanto",
            source_generation=SOURCE_GEN,
            source_paths=PATHS,
        )
        self.assertEqual(ScopeDisposition.SIGNED_PERSISTED_AGENT_MISMATCH, obs.disposition)

    def test_persisted_namespace_drift_is_detected(self):
        obs = memanto_namespace_drift_seed()
        self.assertEqual(ScopeDisposition.PERSISTED_NAMESPACE_DRIFT, obs.disposition)
        self.assertEqual("memanto_agent_research_agent", obs.expected_namespace)
        self.assertFalse(obs.vulnerability_proven)

    def test_modeled_current_identity_predicate_does_not_include_namespace(self):
        self.assertTrue(
            modeled_current_validation_accepts(
                signed_agent_id="research_agent",
                persisted_agent_id="research_agent",
                persisted_session_id="sess_1",
                signed_session_id="sess_1",
                persisted_active=True,
            )
        )
        self.assertEqual(
            ScopeDisposition.PERSISTED_NAMESPACE_DRIFT,
            memanto_namespace_drift_seed().disposition,
        )

    def test_source_generation_and_effect_ceiling_fail_closed(self):
        with self.assertRaises(ValueError):
            IdentityScopeObservationV1(
                signed_agent_id="alpha",
                persisted_agent_id="alpha",
                persisted_namespace="memanto_agent_alpha",
                source_repository="moorcheh-ai/memanto",
                source_generation="main",
                source_paths=PATHS,
            )
        with self.assertRaises(ValueError):
            IdentityScopeObservationV1(
                signed_agent_id="alpha",
                persisted_agent_id="alpha",
                persisted_namespace="memanto_agent_alpha",
                source_repository="moorcheh-ai/memanto",
                source_generation=SOURCE_GEN,
                source_paths=PATHS,
                vulnerability_proven=True,
            )

    def test_receipt_digest_is_deterministic(self):
        self.assertEqual(
            memanto_namespace_drift_seed().receipt_digest,
            memanto_namespace_drift_seed().receipt_digest,
        )


if __name__ == "__main__":
    unittest.main()
