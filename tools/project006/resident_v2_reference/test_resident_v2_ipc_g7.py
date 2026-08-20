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
    now=NOW,
    generation="gen-current",
    currentness_ref="currentness:1",
    authority_ref="authority:local-owner",
    expires_at_ms=None,
):
    if expires_at_ms is None:
        expires_at_ms = now + 1000
    return {
        "protocol_version": r.PROTOCOL_VERSION,
        "message_type": mt,
        "request_id": rid,
        "generation": generation,
        "issued_at_ms": now - 100,
        "expires_at_ms": expires_at_ms,
        "authority_ref": authority_ref,
        "currentness_ref": currentness_ref,
        "payload": payload,
    }


def submit(
    cid,
    rid,
    *,
    digest="a" * 64,
    now=NOW,
    generation="gen-current",
    currentness_ref="currentness:1",
    authority_ref="authority:local-owner",
    expires_at_ms=None,
):
    return req(
        "WORK_SUBMIT",
        rid,
        {
            "capsule_id": cid,
            "capsule_digest": digest,
            "route_ref": "route:sidecar-default",
            "deadline_ms": now + 5000,
        },
        now=now,
        generation=generation,
        currentness_ref=currentness_ref,
        authority_ref=authority_ref,
        expires_at_ms=expires_at_ms,
    )


def cancel(
    cid,
    rid,
    *,
    now=NOW,
    generation="gen-current",
    currentness_ref="currentness:1",
    authority_ref="authority:local-owner",
    expires_at_ms=None,
):
    return req(
        "WORK_CANCEL",
        rid,
        {"capsule_id": cid},
        now=now,
        generation=generation,
        currentness_ref=currentness_ref,
        authority_ref=authority_ref,
        expires_at_ms=expires_at_ms,
    )


class G7GenerationScopedIdentityFence(unittest.TestCase):
    def state(self):
        return r.ResidentState(
            "gen-current", "currentness:1", "authority:local-owner", owner_uid=1000
        )

    def process(self, q, s, *, uid=1000, now=NOW):
        with mock.patch.object(r, "get_peer_uid", return_value=uid), mock.patch.object(
            r, "_now_ms", return_value=now
        ):
            return r._process_request(q, s, object())

    def retire_transient_state(self, s, cid):
        self.process(
            submit(cid, "REQ-G7-SUB-BASE", expires_at_ms=NOW + 1), s
        )
        self.process(
            cancel(cid, "REQ-G7-CAN-BASE", expires_at_ms=NOW + 1), s
        )
        later = NOW + r.TERMINAL_WORK_RETENTION_MS + 10
        # Trigger ordinary housekeeping while preserving the generation fence.
        self.process(
            req(
                "HEALTH",
                "REQ-G7-HOUSEKEEP",
                {},
                now=later,
                expires_at_ms=later + 1000,
            ),
            s,
            now=later,
        )
        self.assertNotIn(cid, s.work_records)
        self.assertIn(cid, s.capsule_identities)
        return later

    def test_r1_currentness_only_same_generation_divergent_digest_conflicts(self):
        s = self.state()
        later = self.retire_transient_state(s, "capsule:g7-r1")
        r.rebase_identity_domain(
            s,
            generation="gen-current",
            currentness_ref="currentness:2",
            authority_ref="authority:local-owner",
        )
        out = self.process(
            submit(
                "capsule:g7-r1",
                "REQ-G7-R1-NEW",
                digest="b" * 64,
                now=later,
                currentness_ref="currentness:2",
            ),
            s,
            now=later,
        )
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_CONFLICT")

    def test_r2_authority_only_same_generation_divergent_digest_conflicts(self):
        s = self.state()
        later = self.retire_transient_state(s, "capsule:g7-r2")
        r.rebase_identity_domain(
            s,
            generation="gen-current",
            currentness_ref="currentness:1",
            authority_ref="authority:next-owner",
        )
        out = self.process(
            submit(
                "capsule:g7-r2",
                "REQ-G7-R2-NEW",
                digest="b" * 64,
                now=later,
                authority_ref="authority:next-owner",
            ),
            s,
            now=later,
        )
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_CONFLICT")

    def test_r3_same_digest_reuse_survives_currentness_and_authority_changes(self):
        s = self.state()
        later = self.retire_transient_state(s, "capsule:g7-r3")
        r.rebase_identity_domain(
            s,
            generation="gen-current",
            currentness_ref="currentness:2",
            authority_ref="authority:next-owner",
        )
        out = self.process(
            submit(
                "capsule:g7-r3",
                "REQ-G7-R3-NEW",
                digest="a" * 64,
                now=later,
                currentness_ref="currentness:2",
                authority_ref="authority:next-owner",
            ),
            s,
            now=later,
        )
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_REUSED")

    def test_r4_explicit_generation_rebase_releases_previous_fence_atomically(self):
        s = self.state()
        later = self.retire_transient_state(s, "capsule:g7-r4")
        before_epoch = s.state_epoch
        snapshot = r.rebase_identity_domain(
            s,
            generation="gen-next",
            currentness_ref="currentness:2",
            authority_ref="authority:next-owner",
        )
        self.assertEqual(snapshot["generation"], "gen-next")
        self.assertEqual(snapshot["currentness_ref"], "currentness:2")
        self.assertEqual(snapshot["authority_ref"], "authority:next-owner")
        self.assertEqual(s.state_epoch, before_epoch + 1)
        self.assertNotIn("capsule:g7-r4", s.capsule_identities)
        out = self.process(
            submit(
                "capsule:g7-r4",
                "REQ-G7-R4-NEW",
                digest="b" * 64,
                now=later,
                generation="gen-next",
                currentness_ref="currentness:2",
                authority_ref="authority:next-owner",
            ),
            s,
            now=later,
        )
        self.assertEqual(out["reason_code"], "WORK_ACCEPTED")

    def test_r5_concurrent_rebase_and_submit_never_observe_partial_identity_tuple(self):
        s = self.state()
        barrier = threading.Barrier(3)
        results = []

        new_req = submit(
            "capsule:g7-r5",
            "REQ-G7-R5-NEW",
            generation="gen-next",
            currentness_ref="currentness:2",
            authority_ref="authority:next-owner",
        )

        def rebase():
            barrier.wait()
            r.rebase_identity_domain(
                s,
                generation="gen-next",
                currentness_ref="currentness:2",
                authority_ref="authority:next-owner",
            )

        def submit_new():
            barrier.wait()
            results.append(r._process_request(new_req, s, object()))

        with mock.patch.object(r, "get_peer_uid", return_value=1000), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ):
            t1 = threading.Thread(target=rebase)
            t2 = threading.Thread(target=submit_new)
            t1.start()
            t2.start()
            barrier.wait()
            t1.join(timeout=2)
            t2.join(timeout=2)

        self.assertFalse(t1.is_alive())
        self.assertFalse(t2.is_alive())
        self.assertEqual(len(results), 1)
        self.assertIn(
            results[0]["reason_code"],
            {"STALE_OR_FOREIGN_GENERATION", "WORK_ACCEPTED"},
        )
        self.assertEqual(
            (s.generation, s.currentness_ref, s.authority_ref),
            ("gen-next", "currentness:2", "authority:next-owner"),
        )

    def test_r6_identity_capacity_stays_fail_closed_after_same_generation_rebind(self):
        s = self.state()
        with mock.patch.object(r, "MAX_CAPSULE_IDENTITIES", 1):
            self.assertEqual(
                self.process(submit("capsule:g7-cap-1", "REQ-G7-CAP-1"), s)[
                    "reason_code"
                ],
                "WORK_ACCEPTED",
            )
            r.rebase_identity_domain(
                s,
                generation="gen-current",
                currentness_ref="currentness:2",
                authority_ref="authority:local-owner",
            )
            out = self.process(
                submit(
                    "capsule:g7-cap-2",
                    "REQ-G7-CAP-2",
                    currentness_ref="currentness:2",
                ),
                s,
            )
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_CAPACITY_EXHAUSTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
