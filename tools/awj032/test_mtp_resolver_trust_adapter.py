import unittest

from tools.awj032 import mtp_resolver_trust_adapter as m


def request(**overrides):
    values = {
        "model_revision": "a" * 40,
        "index_sha256": "b" * 64,
        "num_hidden_layers": 78,
        "roles": ((78, "MTP_NON_DECODER"),),
        "evidence_ref": "drive:mtp-role-evidence",
        "evidence_digest": "c" * 64,
        "evidence_generation": "evidence:1",
        "resolver_ref": "aura:glm53-mtp-resolver",
        "resolver_generation": "resolver:1",
        "resolution_receipt_ref": "drive:mtp-resolution",
        "policy_ref": "aura:policy:glm53-mtp-role",
        "policy_generation": "policy:1",
        "policy_currentness_ref": "aura:policy-currentness:1",
        "issuer_ref": "aura:issuer:glm53-mtp",
        "issuer_generation": "issuer:1",
        "subject_ref": "zai-org/GLM-5.3@a",
    }
    values.update(overrides)
    return m.GLM53MTPResolverTrustRequest(**values)


def observation(req=None, **overrides):
    req = request() if req is None else req
    values = {
        "request_digest": req.request_digest,
        "appraiser_ref": "aura:external-appraiser:glm53-mtp",
        "appraiser_generation": "appraiser:1",
        "appraiser_currentness_ref": "aura:appraiser-currentness:1",
        "verification_receipt_ref": "aura:verification-receipt:1",
        "issuer_trusted": True,
        "owner_policy_resolved": True,
        "policy_current": True,
        "attestation_current": True,
        "state": "ACTIVE",
    }
    values.update(overrides)
    return m.ExternalAppraiserObservation(**values)


class MTPResolverTrustAdapterTests(unittest.TestCase):
    def test_no_appraiser_retains_provenance_blocker(self):
        out = m.admit_external_appraiser(request(), None)
        self.assertEqual(m.DISPOSITION_REQUIRED, out.disposition)
        self.assertEqual(m.PROVENANCE_BLOCKER, out.blocker)
        self.assertFalse(out.resolver_provenance_proven_by_this_module)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.authority)

    def test_fully_matching_appraiser_is_never_self_authenticated(self):
        req = request()
        out = m.admit_external_appraiser(req, observation(req))
        self.assertEqual(m.DISPOSITION_MATCHED, out.disposition)
        self.assertEqual(m.PROVENANCE_BLOCKER, out.blocker)
        self.assertFalse(out.resolver_provenance_proven_by_this_module)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.authority)
        self.assertFalse(out.runtime_executed)

    def test_request_digest_binds_model_and_index_source_generation(self):
        base = request()
        self.assertNotEqual(base.request_digest, request(model_revision="d" * 40).request_digest)
        self.assertNotEqual(base.request_digest, request(index_sha256="e" * 64).request_digest)

    def test_request_digest_binds_policy_issuer_and_resolver_generations(self):
        base = request()
        self.assertNotEqual(base.request_digest, request(policy_generation="policy:2").request_digest)
        self.assertNotEqual(base.request_digest, request(issuer_generation="issuer:2").request_digest)
        self.assertNotEqual(base.request_digest, request(resolver_generation="resolver:2").request_digest)

    def test_cross_domain_authority_cast_is_rejected(self):
        req = request(evidence_domain="CONSUMER_ADMISSION")
        with self.assertRaises(m.MTPResolverTrustError) as ctx:
            req.normalized()
        self.assertEqual("EVIDENCE_DOMAIN_MISMATCH", ctx.exception.code)

    def test_appraiser_request_digest_mismatch_is_rejected(self):
        req = request()
        bad = observation(req, request_digest="f" * 64)
        with self.assertRaises(m.MTPResolverTrustError) as ctx:
            m.admit_external_appraiser(req, bad)
        self.assertEqual("APPRAISER_REQUEST_DIGEST_MISMATCH", ctx.exception.code)

    def test_stale_policy_or_revoked_attestation_is_unsatisfied(self):
        req = request()
        for obs in (
            observation(req, policy_current=False),
            observation(req, state="REVOKED"),
            observation(req, state="SUPERSEDED"),
            observation(req, attestation_current=False),
            observation(req, issuer_trusted=False),
        ):
            with self.subTest(state=obs.state, policy=obs.policy_current):
                out = m.admit_external_appraiser(req, obs)
                self.assertEqual(m.DISPOSITION_UNSATISFIED, out.disposition)
                self.assertEqual(m.PROVENANCE_BLOCKER, out.blocker)
                self.assertFalse(out.resolver_provenance_proven_by_this_module)

    def test_truthy_integer_is_not_a_trust_boolean(self):
        req = request()
        obs = observation(req, issuer_trusted=1)
        with self.assertRaises(m.MTPResolverTrustError) as ctx:
            m.admit_external_appraiser(req, obs)
        self.assertEqual("ISSUER_TRUST_BOOL_REQUIRED", ctx.exception.code)

    def test_effect_ceiling_remains_hard_false_for_every_disposition(self):
        req = request()
        for obs in (None, observation(req), observation(req, policy_current=False)):
            out = m.admit_external_appraiser(req, obs)
            self.assertFalse(out.resolver_provenance_proven_by_this_module)
            self.assertFalse(out.g2_admitted)
            self.assertFalse(out.authority)
            self.assertFalse(out.runtime_executed)


if __name__ == "__main__":
    unittest.main()
