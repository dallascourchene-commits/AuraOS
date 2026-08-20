import threading
import unittest
from unittest import mock

import resident_v2_ipc as r

NOW = 1_800_000_000_000


def req(
    message_type,
    request_id,
    payload,
    *,
    generation="gen-current",
    currentness_ref="currentness:1",
    authority_ref="authority:owner-a",
):
    return {
        "protocol_version": r.PROTOCOL_VERSION,
        "message_type": message_type,
        "request_id": request_id,
        "generation": generation,
        "issued_at_ms": NOW - 100,
        "expires_at_ms": NOW + 1000,
        "authority_ref": authority_ref,
        "currentness_ref": currentness_ref,
        "payload": payload,
    }


def submit(capsule_id, request_id, *, authority_ref="authority:owner-a"):
    return req(
        "WORK_SUBMIT",
        request_id,
        {
            "capsule_id": capsule_id,
            "capsule_digest": "a" * 64,
            "route_ref": "route:sidecar-default",
            "deadline_ms": NOW + 5000,
        },
        authority_ref=authority_ref,
    )


def cancel(capsule_id, request_id, *, authority_ref):
    return req(
        "WORK_CANCEL",
        request_id,
        {"capsule_id": capsule_id},
        authority_ref=authority_ref,
    )


class G9AuthorityOwnerCredentialCrossBind(unittest.TestCase):
    def state(self):
        return r.ResidentState(
            "gen-current", "currentness:1", "authority:owner-a", owner_uid=1000
        )

    def process(self, request, state, *, uid):
        with mock.patch.object(r, "get_peer_uid", return_value=uid), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ):
            return r._process_request(request, state, object())

    def transfer_owner(self, state, *, new_authority="authority:owner-b", new_uid=2000):
        return r.rebase_identity_domain(
            state,
            generation=state.generation,
            currentness_ref=state.currentness_ref,
            authority_ref=new_authority,
            owner_uid=new_uid,
            expected_authority_ref=state.authority_ref,
            expected_owner_uid=state.owner_uid,
        )

    def test_r1_authority_transition_requires_atomic_owner_binding(self):
        state = self.state()
        state.capsule_identities["capsule:g9-r1"] = (
            "a" * 64,
            state.generation,
            state.currentness_ref,
            state.authority_ref,
        )
        before = (
            state.generation,
            state.currentness_ref,
            state.authority_ref,
            state.owner_uid,
            state.state_epoch,
            dict(state.capsule_identities),
        )

        with self.assertRaisesRegex(r.IPCError, "AUTHORITY_OWNER_BINDING_REQUIRED"):
            r.rebase_identity_domain(
                state,
                generation="gen-current",
                currentness_ref="currentness:1",
                authority_ref="authority:owner-b",
            )

        self.assertEqual(
            (
                state.generation,
                state.currentness_ref,
                state.authority_ref,
                state.owner_uid,
                state.state_epoch,
                dict(state.capsule_identities),
            ),
            before,
        )

        snapshot = self.transfer_owner(state)
        self.assertEqual(snapshot["authority_ref"], "authority:owner-b")
        self.assertEqual(snapshot["owner_uid"], 2000)
        self.assertEqual(state.owner_uid, 2000)
        self.assertIn("capsule:g9-r1", state.capsule_identities)

    def test_r2_old_owner_loses_global_admin_and_new_owner_succeeds(self):
        state = self.state()
        self.transfer_owner(state)
        request_old = req(
            "ADMIN_RECONCILE",
            "REQ-G9-R2-OLD",
            {},
            authority_ref="authority:owner-b",
        )
        request_new = req(
            "ADMIN_RECONCILE",
            "REQ-G9-R2-NEW",
            {},
            authority_ref="authority:owner-b",
        )

        old_result = self.process(request_old, state, uid=1000)
        new_result = self.process(request_new, state, uid=2000)

        self.assertEqual(old_result["reason_code"], "ADMIN_PEER_NOT_OWNER")
        self.assertEqual(new_result["reason_code"], "RECONCILE_MARKED")

    def test_r3_cancel_rights_separate_current_owner_from_original_submitter(self):
        state = self.state()
        submitted = self.process(
            submit("capsule:g9-r3-foreign", "REQ-G9-R3-SUB-F"), state, uid=3000
        )
        self.assertEqual(submitted["reason_code"], "WORK_ACCEPTED")
        self.transfer_owner(state)

        old_owner_result = self.process(
            cancel(
                "capsule:g9-r3-foreign",
                "REQ-G9-R3-CAN-OLD",
                authority_ref="authority:owner-b",
            ),
            state,
            uid=1000,
        )
        self.assertEqual(old_owner_result["reason_code"], "CANCEL_PEER_NOT_AUTHORIZED")

        new_owner_result = self.process(
            cancel(
                "capsule:g9-r3-foreign",
                "REQ-G9-R3-CAN-NEW",
                authority_ref="authority:owner-b",
            ),
            state,
            uid=2000,
        )
        self.assertEqual(new_owner_result["reason_code"], "WORK_CANCELLED")

        submitter_state = self.state()
        submitted_by_old_owner = self.process(
            submit("capsule:g9-r3-submit", "REQ-G9-R3-SUB-S"),
            submitter_state,
            uid=1000,
        )
        self.assertEqual(submitted_by_old_owner["reason_code"], "WORK_ACCEPTED")
        self.transfer_owner(submitter_state)
        submitter_cancel = self.process(
            cancel(
                "capsule:g9-r3-submit",
                "REQ-G9-R3-CAN-SUBMITTER",
                authority_ref="authority:owner-b",
            ),
            submitter_state,
            uid=1000,
        )
        self.assertEqual(submitter_cancel["reason_code"], "WORK_CANCELLED")

    def test_r4_concurrent_transfer_and_privileged_request_never_authorize_hybrid(self):
        state = self.state()
        barrier = threading.Barrier(3)
        results = []
        new_owner_request = req(
            "ADMIN_RECONCILE",
            "REQ-G9-R4-NEW",
            {},
            authority_ref="authority:owner-b",
        )

        def transfer():
            barrier.wait()
            self.transfer_owner(state)

        def request_as_new_owner():
            barrier.wait()
            results.append(r._process_request(new_owner_request, state, object()))

        with mock.patch.object(r, "get_peer_uid", return_value=2000), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ):
            t1 = threading.Thread(target=transfer)
            t2 = threading.Thread(target=request_as_new_owner)
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
            {"AUTHORITY_MISMATCH", "RECONCILE_MARKED"},
        )
        self.assertEqual(
            (state.authority_ref, state.owner_uid),
            ("authority:owner-b", 2000),
        )

        old_owner_after = self.process(
            req(
                "ADMIN_RECONCILE",
                "REQ-G9-R4-OLD-AFTER",
                {},
                authority_ref="authority:owner-b",
            ),
            state,
            uid=1000,
        )
        self.assertEqual(old_owner_after["reason_code"], "ADMIN_PEER_NOT_OWNER")

    def test_r5_invalid_mismatched_and_stale_bindings_fail_before_mutation(self):
        state = self.state()
        before = state.snapshot()
        with self.assertRaisesRegex(
            AttributeError, "IDENTITY_DOMAIN_DIRECT_MUTATION_FORBIDDEN"
        ):
            state.owner_uid = 2000
        self.assertEqual(state.snapshot(), before)

        for invalid_uid in (-1, True, 0x1_0000_0000):
            with self.subTest(invalid_uid=invalid_uid):
                local = self.state()
                local_before = local.snapshot()
                with self.assertRaisesRegex(r.IPCError, "INVALID_OWNER_UID"):
                    r.rebase_identity_domain(
                        local,
                        generation="gen-current",
                        currentness_ref="currentness:1",
                        authority_ref="authority:owner-b",
                        owner_uid=invalid_uid,
                        expected_authority_ref="authority:owner-a",
                        expected_owner_uid=1000,
                    )
                self.assertEqual(local.snapshot(), local_before)

        local = self.state()
        local_before = local.snapshot()
        with self.assertRaisesRegex(r.IPCError, "OWNER_TRANSFER_REQUIRES_AUTHORITY_CHANGE"):
            r.rebase_identity_domain(
                local,
                generation="gen-current",
                currentness_ref="currentness:1",
                authority_ref="authority:owner-a",
                owner_uid=2000,
            )
        self.assertEqual(local.snapshot(), local_before)

        stale = self.state()
        self.transfer_owner(stale)
        stale_before = stale.snapshot()
        with self.assertRaisesRegex(r.IPCError, "AUTHORITY_OWNER_BINDING_STALE"):
            r.rebase_identity_domain(
                stale,
                generation="gen-current",
                currentness_ref="currentness:1",
                authority_ref="authority:owner-c",
                owner_uid=3000,
                expected_authority_ref="authority:owner-a",
                expected_owner_uid=1000,
            )
        self.assertEqual(stale.snapshot(), stale_before)

    def test_r6_generation_and_currentness_rebases_preserve_fence_law(self):
        state = self.state()
        state.capsule_identities["capsule:g9-r6"] = (
            "a" * 64,
            "gen-current",
            "currentness:1",
            "authority:owner-a",
        )
        r.rebase_identity_domain(
            state,
            generation="gen-current",
            currentness_ref="currentness:2",
            authority_ref="authority:owner-a",
        )
        self.assertIn("capsule:g9-r6", state.capsule_identities)
        self.assertEqual(state.owner_uid, 1000)

        r.rebase_identity_domain(
            state,
            generation="gen-next",
            currentness_ref="currentness:3",
            authority_ref="authority:owner-a",
        )
        self.assertNotIn("capsule:g9-r6", state.capsule_identities)
        self.assertEqual(state.owner_uid, 1000)

    def test_r7_snapshot_binds_authority_and_effective_owner_credential(self):
        state = self.state()
        before_epoch = state.state_epoch
        snapshot = self.transfer_owner(state)
        self.assertEqual(
            (snapshot["authority_ref"], snapshot["owner_uid"]),
            ("authority:owner-b", 2000),
        )
        self.assertEqual(snapshot["state_epoch"], before_epoch + 1)
        self.assertEqual(
            (state.authority_ref, state.owner_uid),
            ("authority:owner-b", 2000),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
