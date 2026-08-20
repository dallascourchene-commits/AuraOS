import threading
import unittest
from unittest import mock

import resident_v2_ipc as r

NOW = 1_800_000_000_000


def req(mt, rid, payload, *, now=NOW, generation="gen-current", expires_at_ms=None):
    if expires_at_ms is None:
        expires_at_ms = now + 1000
    return {
        "protocol_version": r.PROTOCOL_VERSION,
        "message_type": mt,
        "request_id": rid,
        "generation": generation,
        "issued_at_ms": now - 100,
        "expires_at_ms": expires_at_ms,
        "authority_ref": "authority:local-owner",
        "currentness_ref": "currentness:1",
        "payload": payload,
    }


def submit(cid, rid, *, digest="a" * 64, now=NOW, generation="gen-current", expires_at_ms=None):
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
        expires_at_ms=expires_at_ms,
    )


def cancel(cid, rid, *, now=NOW, generation="gen-current", expires_at_ms=None):
    return req(
        "WORK_CANCEL",
        rid,
        {"capsule_id": cid},
        now=now,
        generation=generation,
        expires_at_ms=expires_at_ms,
    )


class G6Lifecycle(unittest.TestCase):
    def state(self):
        return r.ResidentState(
            "gen-current", "currentness:1", "authority:local-owner", owner_uid=1000
        )

    def process(self, q, s, *, uid=1000, now=NOW):
        with mock.patch.object(r, "get_peer_uid", return_value=uid), mock.patch.object(
            r, "_now_ms", return_value=now
        ):
            return r._process_request(q, s, object())

    def test_01_second_distinct_cancel_is_nonmutating(self):
        s = self.state()
        self.assertEqual(
            self.process(submit("capsule:c", "REQ-G6-SUB-01"), s)["reason_code"],
            "WORK_ACCEPTED",
        )
        first = self.process(cancel("capsule:c", "REQ-G6-CAN-01"), s)
        self.assertEqual(first["reason_code"], "WORK_CANCELLED")
        epoch = s.state_epoch
        terminal_at = s.work_records["capsule:c"].terminal_at_ms
        second = self.process(
            cancel("capsule:c", "REQ-G6-CAN-02", now=NOW + 1), s, now=NOW + 1
        )
        self.assertEqual(second["reason_code"], "CAPSULE_NOT_ACTIVE")
        self.assertEqual(s.state_epoch, epoch)
        self.assertEqual(s.work_records["capsule:c"].terminal_at_ms, terminal_at)

    def test_02_exact_cancel_replay_remains_idempotent(self):
        s = self.state()
        self.process(submit("capsule:c", "REQ-G6-SUB-02"), s)
        q = cancel("capsule:c", "REQ-G6-CAN-03")
        first = self.process(q, s)
        epoch = s.state_epoch
        replay = self.process(q, s, now=NOW + 1)
        self.assertEqual(replay, first)
        self.assertEqual(s.state_epoch, epoch)

    def test_03_same_digest_reuse_after_housekeeping_rejects(self):
        s = self.state()
        self.process(
            submit("capsule:reuse", "REQ-G6-SUB-03", expires_at_ms=NOW + 1), s
        )
        self.process(
            cancel("capsule:reuse", "REQ-G6-CAN-04", expires_at_ms=NOW + 1), s
        )
        later = NOW + r.TERMINAL_WORK_RETENTION_MS + 10
        out = self.process(
            submit("capsule:reuse", "REQ-G6-SUB-04", now=later), s, now=later
        )
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_REUSED")
        self.assertNotIn("capsule:reuse", s.work_records)
        self.assertIn("capsule:reuse", s.capsule_identities)

    def test_04_divergent_digest_reuse_after_housekeeping_conflicts(self):
        s = self.state()
        self.process(
            submit("capsule:reuse2", "REQ-G6-SUB-05", expires_at_ms=NOW + 1), s
        )
        self.process(
            cancel("capsule:reuse2", "REQ-G6-CAN-05", expires_at_ms=NOW + 1), s
        )
        later = NOW + r.TERMINAL_WORK_RETENTION_MS + 10
        out = self.process(
            submit(
                "capsule:reuse2", "REQ-G6-SUB-06", digest="b" * 64, now=later
            ),
            s,
            now=later,
        )
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_CONFLICT")

    def test_05_identity_fence_capacity_fails_closed(self):
        s = self.state()
        with mock.patch.object(r, "MAX_CAPSULE_IDENTITIES", 1):
            self.assertEqual(
                self.process(submit("capsule:one", "REQ-G6-SUB-07"), s)[
                    "reason_code"
                ],
                "WORK_ACCEPTED",
            )
            out = self.process(submit("capsule:two", "REQ-G6-SUB-08"), s)
        self.assertEqual(out["reason_code"], "CAPSULE_IDENTITY_CAPACITY_EXHAUSTED")
        self.assertNotIn("capsule:two", s.work_records)

    def test_06_explicit_generation_rebase_releases_old_identity_domain(self):
        s = self.state()
        self.process(
            submit("capsule:rebase", "REQ-G6-SUB-09", expires_at_ms=NOW + 1), s
        )
        self.process(
            cancel("capsule:rebase", "REQ-G6-CAN-06", expires_at_ms=NOW + 1), s
        )
        later = NOW + r.TERMINAL_WORK_RETENTION_MS + 10
        r.rebase_identity_domain(
            s,
            generation="gen-next",
            currentness_ref="currentness:1",
            authority_ref="authority:local-owner",
        )
        out = self.process(
            submit(
                "capsule:rebase",
                "REQ-G6-SUB-10",
                digest="b" * 64,
                now=later,
                generation="gen-next",
            ),
            s,
            now=later,
        )
        self.assertEqual(out["reason_code"], "WORK_ACCEPTED")
        self.assertEqual(s.capsule_identities["capsule:rebase"][0], "b" * 64)

    def test_07_concurrent_distinct_cancels_make_one_transition(self):
        s = self.state()
        self.process(submit("capsule:race", "REQ-G6-SUB-11"), s)
        barrier = threading.Barrier(3)
        results = []

        def run(q):
            barrier.wait()
            results.append(r._process_request(q, s, object()))

        with mock.patch.object(r, "get_peer_uid", return_value=1000), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ):
            t1 = threading.Thread(
                target=run, args=(cancel("capsule:race", "REQ-G6-CAN-07"),)
            )
            t2 = threading.Thread(
                target=run, args=(cancel("capsule:race", "REQ-G6-CAN-08"),)
            )
            t1.start()
            t2.start()
            barrier.wait()
            t1.join(timeout=2)
            t2.join(timeout=2)
        self.assertEqual(
            sorted(item["reason_code"] for item in results),
            ["CAPSULE_NOT_ACTIVE", "WORK_CANCELLED"],
        )
        self.assertEqual(s.state_epoch, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
