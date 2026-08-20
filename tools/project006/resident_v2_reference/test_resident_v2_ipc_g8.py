import threading
import unittest
from unittest import mock

import resident_v2_ipc as r

NOW = 1_800_000_000_000


def req(
    mt,
    rid,
    payload,
    *,
    generation="gen-current",
    currentness_ref="currentness:1",
    authority_ref="authority:local-owner",
):
    return {
        "protocol_version": r.PROTOCOL_VERSION,
        "message_type": mt,
        "request_id": rid,
        "generation": generation,
        "issued_at_ms": NOW - 100,
        "expires_at_ms": NOW + 1000,
        "authority_ref": authority_ref,
        "currentness_ref": currentness_ref,
        "payload": payload,
    }


def submit(
    cid,
    rid,
    *,
    digest="a" * 64,
    generation="gen-current",
    currentness_ref="currentness:1",
    authority_ref="authority:local-owner",
):
    return req(
        "WORK_SUBMIT",
        rid,
        {
            "capsule_id": cid,
            "capsule_digest": digest,
            "route_ref": "route:sidecar-default",
            "deadline_ms": NOW + 5000,
        },
        generation=generation,
        currentness_ref=currentness_ref,
        authority_ref=authority_ref,
    )


class G8EnforcedAtomicIdentityTransition(unittest.TestCase):
    def state(self):
        return r.ResidentState(
            "gen-current", "currentness:1", "authority:local-owner", owner_uid=1000
        )

    def process(self, q, s):
        with mock.patch.object(r, "get_peer_uid", return_value=1000), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ):
            return r._process_request(q, s, object())

    def assert_identity(self, s, expected):
        self.assertEqual(
            (s.generation, s.currentness_ref, s.authority_ref), expected
        )

    def test_r1_direct_generation_assignment_is_rejected_and_nonmutating(self):
        s = self.state()
        before = (s.generation, s.currentness_ref, s.authority_ref, s.state_epoch)
        with self.assertRaisesRegex(
            AttributeError, "IDENTITY_DOMAIN_DIRECT_MUTATION_FORBIDDEN"
        ):
            s.generation = "gen-next"
        self.assertEqual(
            (s.generation, s.currentness_ref, s.authority_ref, s.state_epoch), before
        )

    def test_r2_direct_currentness_assignment_is_rejected_and_nonmutating(self):
        s = self.state()
        before = (s.generation, s.currentness_ref, s.authority_ref, s.state_epoch)
        with self.assertRaisesRegex(
            AttributeError, "IDENTITY_DOMAIN_DIRECT_MUTATION_FORBIDDEN"
        ):
            s.currentness_ref = "currentness:2"
        self.assertEqual(
            (s.generation, s.currentness_ref, s.authority_ref, s.state_epoch), before
        )

    def test_r3_direct_authority_assignment_is_rejected_and_nonmutating(self):
        s = self.state()
        before = (s.generation, s.currentness_ref, s.authority_ref, s.state_epoch)
        with self.assertRaisesRegex(
            AttributeError, "IDENTITY_DOMAIN_DIRECT_MUTATION_FORBIDDEN"
        ):
            s.authority_ref = "authority:next-owner"
        self.assertEqual(
            (s.generation, s.currentness_ref, s.authority_ref, s.state_epoch), before
        )

    def test_r4_concurrent_direct_mutation_cannot_expose_hybrid_tuple(self):
        s = self.state()
        barrier = threading.Barrier(3)
        mutation_errors = []
        results = []
        current_req = submit("capsule:g8-r4", "REQ-G8-R4-CURRENT")

        def staged_mutation_attempt():
            barrier.wait()
            for field, value in (
                ("generation", "gen-next"),
                ("currentness_ref", "currentness:2"),
                ("authority_ref", "authority:next-owner"),
            ):
                try:
                    setattr(s, field, value)
                except AttributeError as exc:
                    mutation_errors.append((field, str(exc)))

        def submit_current():
            barrier.wait()
            results.append(r._process_request(current_req, s, object()))

        with mock.patch.object(r, "get_peer_uid", return_value=1000), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ):
            t1 = threading.Thread(target=staged_mutation_attempt)
            t2 = threading.Thread(target=submit_current)
            t1.start()
            t2.start()
            barrier.wait()
            t1.join(timeout=2)
            t2.join(timeout=2)

        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())
        self.assertEqual(len(mutation_errors), 3)
        self.assertTrue(
            all(
                message == "IDENTITY_DOMAIN_DIRECT_MUTATION_FORBIDDEN"
                for _field, message in mutation_errors
            )
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["reason_code"], "WORK_ACCEPTED")
        self.assert_identity(
            s, ("gen-current", "currentness:1", "authority:local-owner")
        )

    def test_r5_sanctioned_same_generation_rebase_preserves_fence_semantics(self):
        s = self.state()
        s.capsule_identities["capsule:g8-r5"] = (
            "a" * 64,
            "gen-current",
            "currentness:1",
            "authority:local-owner",
        )
        r.rebase_identity_domain(
            s,
            generation="gen-current",
            currentness_ref="currentness:2",
            authority_ref="authority:next-owner",
            owner_uid=1000,
            expected_authority_ref="authority:local-owner",
            expected_owner_uid=1000,
        )
        self.assertIn("capsule:g8-r5", s.capsule_identities)
        reused = self.process(
            submit(
                "capsule:g8-r5",
                "REQ-G8-R5-REUSED",
                currentness_ref="currentness:2",
                authority_ref="authority:next-owner",
            ),
            s,
        )
        conflict = self.process(
            submit(
                "capsule:g8-r5",
                "REQ-G8-R5-CONFLICT",
                digest="b" * 64,
                currentness_ref="currentness:2",
                authority_ref="authority:next-owner",
            ),
            s,
        )
        self.assertEqual(reused["reason_code"], "CAPSULE_IDENTITY_REUSED")
        self.assertEqual(conflict["reason_code"], "CAPSULE_IDENTITY_CONFLICT")

    def test_r6_sanctioned_generation_rebase_replaces_full_tuple_atomically(self):
        s = self.state()
        s.capsule_identities["capsule:g8-r6"] = (
            "a" * 64,
            "gen-current",
            "currentness:1",
            "authority:local-owner",
        )
        before_epoch = s.state_epoch
        snapshot = r.rebase_identity_domain(
            s,
            generation="gen-next",
            currentness_ref="currentness:2",
            authority_ref="authority:next-owner",
            owner_uid=1000,
            expected_authority_ref="authority:local-owner",
            expected_owner_uid=1000,
        )
        self.assert_identity(
            s, ("gen-next", "currentness:2", "authority:next-owner")
        )
        self.assertEqual(
            (
                snapshot["generation"],
                snapshot["currentness_ref"],
                snapshot["authority_ref"],
            ),
            ("gen-next", "currentness:2", "authority:next-owner"),
        )
        self.assertEqual(snapshot["owner_uid"], 1000)
        self.assertEqual(s.state_epoch, before_epoch + 1)
        self.assertNotIn("capsule:g8-r6", s.capsule_identities)

    def test_r7_invalid_rebase_inputs_fail_before_identity_fence_or_epoch_mutation(self):
        cases = (
            {
                "generation": "bad generation!",
                "currentness_ref": "currentness:2",
                "authority_ref": "authority:next-owner",
                "owner_uid": 1000,
                "expected_authority_ref": "authority:local-owner",
                "expected_owner_uid": 1000,
            },
            {
                "generation": "gen-next",
                "currentness_ref": "bad currentness!",
                "authority_ref": "authority:next-owner",
                "owner_uid": 1000,
                "expected_authority_ref": "authority:local-owner",
                "expected_owner_uid": 1000,
            },
            {
                "generation": "gen-next",
                "currentness_ref": "currentness:2",
                "authority_ref": "bad authority!",
                "owner_uid": 1000,
                "expected_authority_ref": "authority:local-owner",
                "expected_owner_uid": 1000,
            },
        )
        for index, proposed in enumerate(cases):
            with self.subTest(index=index):
                s = self.state()
                s.capsule_identities["capsule:g8-r7"] = (
                    "a" * 64,
                    "gen-current",
                    "currentness:1",
                    "authority:local-owner",
                )
                before_epoch = s.state_epoch
                before_fence = dict(s.capsule_identities)
                with self.assertRaises(r.IPCError):
                    r.rebase_identity_domain(s, **proposed)
                self.assert_identity(
                    s,
                    ("gen-current", "currentness:1", "authority:local-owner"),
                )
                self.assertEqual(s.owner_uid, 1000)
                self.assertEqual(s.state_epoch, before_epoch)
                self.assertEqual(s.capsule_identities, before_fence)

    def test_r8_identity_capacity_remains_fail_closed_after_rejected_bypass(self):
        s = self.state()
        s.capsule_identities["capsule:g8-cap-1"] = (
            "a" * 64,
            "gen-current",
            "currentness:1",
            "authority:local-owner",
        )
        with self.assertRaises(AttributeError):
            s.generation = "gen-next"
        with mock.patch.object(r, "MAX_CAPSULE_IDENTITIES", 1):
            out = self.process(
                submit("capsule:g8-cap-2", "REQ-G8-CAP-2"), s
            )
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_CAPACITY_EXHAUSTED")
        self.assert_identity(
            s, ("gen-current", "currentness:1", "authority:local-owner")
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
