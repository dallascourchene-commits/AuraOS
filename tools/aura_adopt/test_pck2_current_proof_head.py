import unittest

from tools.aura_adopt.owner_resolved_persistent_kv_reuse import KVAdmissionError
from tools.aura_adopt.test_owner_resolved_persistent_kv_reuse import (
    RESOLVER_KEY,
    admit,
    admit_raw,
    claim,
    observation_proof,
    path,
    resolver_proof,
    target,
)


class PCK2CurrentProofHeadTests(unittest.TestCase):
    def test_positive_control_still_admits(self):
        self.assertTrue(admit()["transformer_kv_reuse_admissible"])

    def test_resolver_registry_rejects_old_and_successor_as_simultaneously_current(self):
        t = target(); e = path(t); c = claim(t, e)
        old = resolver_proof(c)
        newer = resolver_proof(c, supersedes_proof_digest=old.proof_digest)
        op = observation_proof(t, e, c)
        rps = {c.claim_digest: (old.proof_digest, newer.proof_digest)}
        ops = {e.path_digest: (op.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError, "RESOLVER_PROOF_STATE_AMBIGUOUS"):
            admit_raw(t, c, old, e, op, rps, ops)

    def test_observation_registry_rejects_old_and_successor_as_simultaneously_current(self):
        t = target(); e = path(t); c = claim(t, e)
        rp = resolver_proof(c)
        old = observation_proof(t, e, c)
        newer = observation_proof(t, e, c, supersedes_proof_digest=old.proof_digest)
        rps = {c.claim_digest: (rp.proof_digest,)}
        ops = {e.path_digest: (old.proof_digest, newer.proof_digest)}
        with self.assertRaisesRegex(KVAdmissionError, "OBSERVATION_PROOF_STATE_AMBIGUOUS"):
            admit_raw(t, c, rp, e, old, rps, ops)

    def test_distinct_role_labels_cannot_share_signing_key(self):
        t = target(); e = path(t); c = claim(t, e)
        rp = resolver_proof(c)
        op = observation_proof(
            t,
            e,
            c,
            observer_ref="observer:alias",
            observer_generation="og:5",
            observer_currentness_ref="oc:5",
            key=RESOLVER_KEY,
        )
        rps = {c.claim_digest: (rp.proof_digest,)}
        ops = {e.path_digest: (op.proof_digest,)}
        with self.assertRaisesRegex(
            KVAdmissionError, "OBSERVER_RESOLVER_SIGNING_AUTHORITY_COLLISION"
        ):
            admit_raw(
                t,
                c,
                rp,
                e,
                op,
                rps,
                ops,
                observer_keys={"observer:alias": RESOLVER_KEY},
                observer_state={"observer:alias": ("og:5", "oc:5")},
            )

    def test_resolver_supersedes_digest_is_canonicalized_before_signing(self):
        t = target(); e = path(t); c = claim(t, e)
        rp = resolver_proof(c, supersedes_proof_digest="A" * 64)
        op = observation_proof(t, e, c)
        self.assertEqual("a" * 64, rp.supersedes_proof_digest)
        out = admit_raw(
            t, c, rp, e, op,
            {c.claim_digest: (rp.proof_digest,)},
            {e.path_digest: (op.proof_digest,)},
        )
        self.assertTrue(out["transformer_kv_reuse_admissible"])

    def test_observation_supersedes_digest_is_canonicalized_before_signing(self):
        t = target(); e = path(t); c = claim(t, e)
        rp = resolver_proof(c)
        op = observation_proof(t, e, c, supersedes_proof_digest="B" * 64)
        self.assertEqual("b" * 64, op.supersedes_proof_digest)
        out = admit_raw(
            t, c, rp, e, op,
            {c.claim_digest: (rp.proof_digest,)},
            {e.path_digest: (op.proof_digest,)},
        )
        self.assertTrue(out["transformer_kv_reuse_admissible"])


if __name__ == "__main__":
    unittest.main()
