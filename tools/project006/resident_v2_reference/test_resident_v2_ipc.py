import ast
import inspect
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import resident_v2_ipc as r

NOW = 1_800_000_000_000


def req(mt="HEALTH", rid="REQ-00000001", payload=None, **overrides):
    value = {
        "protocol_version": r.PROTOCOL_VERSION,
        "message_type": mt,
        "request_id": rid,
        "generation": "gen-current",
        "issued_at_ms": NOW - 100,
        "expires_at_ms": NOW + 1000,
        "authority_ref": "authority:local-owner",
        "currentness_ref": "currentness:1",
        "payload": payload or {},
    }
    value.update(overrides)
    return value


class T(unittest.TestCase):
    def state(self, owner_uid=1000):
        return r.ResidentState(
            "gen-current", "currentness:1", "authority:local-owner", owner_uid=owner_uid
        )

    def process(self, q, s, uid=1000, now=NOW):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            with mock.patch.object(r, "get_peer_uid", return_value=uid), mock.patch.object(
                r, "_now_ms", return_value=now
            ):
                return r._process_request(q, s, b)
        finally:
            a.close()
            b.close()

    def submit(self, s, capsule_id, rid, peer_uid=1000, expires_at_ms=NOW + 1000):
        q = req(
            "WORK_SUBMIT",
            rid,
            {
                "capsule_id": capsule_id,
                "capsule_digest": "a" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
            expires_at_ms=expires_at_ms,
        )
        return self.process(q, s, peer_uid)

    def test_01_health(self):
        self.assertEqual(self.process(req(), self.state())["reason_code"], "HEALTH_OK")

    def test_02_truncated(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            a.sendall(struct.pack("!I", 10) + b"{}")
            a.shutdown(socket.SHUT_WR)
            with self.assertRaisesRegex(r.IPCError, "TRUNCATED_FRAME"):
                r.recv_frame(b)
        finally:
            a.close()
            b.close()

    def test_03_oversize(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            a.sendall(struct.pack("!I", r.MAX_FRAME_BYTES + 1))
            with self.assertRaisesRegex(r.IPCError, "FRAME_SIZE_INVALID"):
                r.recv_frame(b)
        finally:
            a.close()
            b.close()

    def test_04_version(self):
        with self.assertRaisesRegex(r.IPCError, "UNSUPPORTED_PROTOCOL_VERSION"):
            r.validate_envelope(req(protocol_version="V999"))

    def test_05_unknown_message(self):
        with self.assertRaisesRegex(r.IPCError, "UNKNOWN_MESSAGE_TYPE"):
            r.validate_envelope(req(message_type="PROVIDER_HTTP_CALL"))

    def test_06_effect_idempotent(self):
        s = self.state()
        q = req(
            "WORK_SUBMIT",
            "REQ-IDEMPOT01",
            {
                "capsule_id": "capsule:idempotent",
                "capsule_digest": "a" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
        )
        first = self.process(q, s)
        second = self.process(q, s, now=NOW + 1)
        self.assertEqual(first, second)
        self.assertEqual(len(s.work_records), 1)

    def test_07_request_id_collision_effect(self):
        s = self.state()
        self.submit(s, "capsule:one", "REQ-COLLIDE01")
        q = req(
            "WORK_SUBMIT",
            "REQ-COLLIDE01",
            {
                "capsule_id": "capsule:two",
                "capsule_digest": "b" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
        )
        self.assertEqual(self.process(q, s)["reason_code"], "REQUEST_ID_COLLISION")

    def test_08_stale_generation(self):
        self.assertEqual(
            self.process(req(generation="gen-old"), self.state())["reason_code"],
            "STALE_OR_FOREIGN_GENERATION",
        )

    def test_09_currentness(self):
        self.assertEqual(
            self.process(req(currentness_ref="currentness:old"), self.state())["reason_code"],
            "CURRENTNESS_MISMATCH",
        )

    def test_10_expired(self):
        self.assertEqual(
            self.process(req(expires_at_ms=NOW - 1), self.state())["reason_code"],
            "REQUEST_EXPIRED",
        )

    def test_11_admin_nonowner(self):
        self.assertEqual(
            self.process(req("ADMIN_RECONCILE"), self.state(), uid=2000)["reason_code"],
            "ADMIN_PEER_NOT_OWNER",
        )

    def test_12_secret(self):
        q = req()
        q["payload"] = {"api_key": "x"}
        with self.assertRaisesRegex(r.IPCError, "SENSITIVE_FIELD_FORBIDDEN"):
            r.validate_envelope(q)

    def test_13_provider_endpoint(self):
        q = req()
        q["payload"] = {"provider_url": "https://example.invalid"}
        with self.assertRaisesRegex(r.IPCError, "NETWORK_ENDPOINT_FIELD_FORBIDDEN"):
            r.validate_envelope(q)

    def test_14_stale_socket_not_unlinked(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "resident.sock")
            Path(path).write_text("occupied")
            with self.assertRaises(OSError):
                r.make_unix_listener(path)
            self.assertTrue(Path(path).exists())

    def test_15_partial_read(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            frame = r.encode_frame(req())
            for byte in frame:
                a.send(bytes([byte]))
            self.assertEqual(r.recv_frame(b)["request_id"], "REQ-00000001")
        finally:
            a.close()
            b.close()

    def test_16_submit_status(self):
        s = self.state()
        self.assertEqual(
            self.submit(s, "capsule:001", "REQ-SUBMIT01")["reason_code"],
            "WORK_ACCEPTED",
        )
        status = self.process(
            req("WORK_STATUS", "REQ-STATUS01", {"capsule_id": "capsule:001"}), s
        )
        self.assertEqual(status["result"]["work_state"], "ACCEPTED")

    def test_17_work_deadline(self):
        q = req(
            "WORK_SUBMIT",
            "REQ-SUBMIT02",
            {
                "capsule_id": "capsule:002",
                "capsule_digest": "b" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW - 1,
            },
        )
        self.assertEqual(self.process(q, self.state())["reason_code"], "WORK_DEADLINE_EXPIRED")

    def test_18_unknown_top(self):
        q = req()
        q["provider"] = "deepseek"
        with self.assertRaisesRegex(r.IPCError, "UNKNOWN_TOP_LEVEL_FIELD"):
            r.validate_envelope(q)

    def test_19_duplicate_json_key(self):
        with self.assertRaisesRegex(r.IPCError, "DUPLICATE_JSON_KEY"):
            r.decode_frame_payload(b'{"a":1,"a":2}')

    def test_20_no_ip_http_surface(self):
        src = Path(r.__file__).read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports |= {item.name.split(".")[0] for item in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertFalse(imports & {"requests", "urllib", "http", "aiohttp", "httpx"})
        self.assertNotIn("AF_INET", src)
        self.assertNotIn("AF_INET6", src)

    def test_21_digest_reproducible_readonly(self):
        q = req()
        first = self.process(q, self.state())
        second = self.process(q, self.state())
        self.assertEqual(first["decision_digest"], second["decision_digest"])

    def test_22_peer_credentials(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.assertEqual(r.get_peer_uid(b), os.getuid())
        finally:
            a.close()
            b.close()

    def test_23_end_to_end_unix_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "resident.sock")
            listener = r.make_unix_listener(path)
            state = self.state(owner_uid=os.getuid())
            gate = r.ConnectionGate(1)
            errors = []

            def server():
                try:
                    conn, _ = listener.accept()
                    try:
                        r.serve_connected_once(conn, state, gate)
                    finally:
                        conn.close()
                except Exception as exc:
                    errors.append(exc)
                finally:
                    listener.close()

            with mock.patch.object(r, "_now_ms", return_value=NOW):
                thread = threading.Thread(target=server)
                thread.start()
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    client.connect(path)
                    r.send_frame(client, req())
                    out = r.recv_frame(client)
                    self.assertEqual(out["reason_code"], "HEALTH_OK")
                finally:
                    client.close()
                thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])

    def test_24_authority_mismatch(self):
        self.assertEqual(
            self.process(req(authority_ref="authority:foreign"), self.state())["reason_code"],
            "AUTHORITY_MISMATCH",
        )

    def test_25_not_yet_valid(self):
        self.assertEqual(
            self.process(
                req(issued_at_ms=NOW + 1, expires_at_ms=NOW + 1000), self.state()
            )["reason_code"],
            "REQUEST_NOT_YET_VALID",
        )

    def test_26_rejected_flood_does_not_exhaust_effect_dedupe(self):
        s = self.state()
        for i in range(r.MAX_SEEN_REQUESTS + 128):
            q = req(
                rid=f"REJ-{i:08d}",
                authority_ref="authority:foreign",
                expires_at_ms=NOW + 100_000,
            )
            self.assertEqual(self.process(q, s, uid=5000)["reason_code"], "AUTHORITY_MISMATCH")
        self.assertEqual(len(s.seen), 0)
        self.assertEqual(
            self.submit(s, "capsule:after-reject-flood", "REQ-AFTERREJ")["reason_code"],
            "WORK_ACCEPTED",
        )

    def test_27_effect_dedupe_reclaims_by_expiry(self):
        s = self.state()
        for i in range(r.MAX_SEEN_REQUESTS):
            self.submit(
                s,
                f"capsule:expire:{i}",
                f"EFF-{i:08d}",
                expires_at_ms=NOW + 1,
            )
        self.assertEqual(len(s.seen), r.MAX_SEEN_REQUESTS)
        q = req(
            "ADMIN_RECONCILE",
            "REQ-RECLAIM01",
            {},
            issued_at_ms=NOW + 2,
            expires_at_ms=NOW + 100,
        )
        out = self.process(q, s, now=NOW + 2)
        self.assertEqual(out["reason_code"], "RECONCILE_MARKED")
        self.assertEqual(len(s.seen), 1)

    def test_28_work_capacity_fails_closed(self):
        s = self.state()
        for i in range(r.MAX_TRACKED_WORK):
            s.work_records[f"c{i}"] = r.WorkRecord("ACCEPTED", 1000)
        q = req(
            "WORK_SUBMIT",
            "REQ-WORKCAP01",
            {
                "capsule_id": "capsule:new",
                "capsule_digest": "c" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
        )
        self.assertEqual(self.process(q, s)["reason_code"], "WORK_CAPACITY_EXHAUSTED")

    def test_29_receipt_snapshot_binds_authority(self):
        out = self.process(req(), self.state())
        self.assertEqual(out["state_snapshot"]["authority_ref"], "authority:local-owner")

    def test_30_header_then_stall_times_out(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            a.sendall(struct.pack("!I", 10))
            start = time.monotonic()
            with self.assertRaisesRegex(r.IPCError, "FRAME_RECEIVE_TIMEOUT"):
                r.recv_frame(b, timeout_seconds=0.03)
            self.assertLess(time.monotonic() - start, 0.5)
        finally:
            a.close()
            b.close()

    def test_31_partial_body_then_stall_times_out(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            a.sendall(struct.pack("!I", 10) + b"123")
            with self.assertRaisesRegex(r.IPCError, "FRAME_RECEIVE_TIMEOUT"):
                r.recv_frame(b, timeout_seconds=0.03)
        finally:
            a.close()
            b.close()

    def test_32_connection_gate_fails_closed(self):
        gate = r.ConnectionGate(1)
        with gate.slot():
            with self.assertRaisesRegex(r.IPCError, "CONNECTION_CAPACITY_EXHAUSTED"):
                with gate.slot():
                    pass

    def test_33_cancel_creator_allowed(self):
        s = self.state()
        self.submit(s, "capsule:owned", "REQ-OWNED001", peer_uid=2001)
        q = req("WORK_CANCEL", "REQ-CANCEL001", {"capsule_id": "capsule:owned"})
        self.assertEqual(self.process(q, s, uid=2001)["reason_code"], "WORK_CANCELLED")

    def test_34_cancel_nonowner_rejected(self):
        s = self.state()
        self.submit(s, "capsule:owned2", "REQ-OWNED002", peer_uid=2001)
        q = req("WORK_CANCEL", "REQ-CANCEL002", {"capsule_id": "capsule:owned2"})
        self.assertEqual(self.process(q, s, uid=2002)["reason_code"], "CANCEL_PEER_NOT_AUTHORIZED")
        self.assertEqual(s.work_records["capsule:owned2"].state, "ACCEPTED")

    def test_35_owner_can_cancel_cross_capsule(self):
        s = self.state()
        self.submit(s, "capsule:owned3", "REQ-OWNED003", peer_uid=2001)
        q = req("WORK_CANCEL", "REQ-CANCEL003", {"capsule_id": "capsule:owned3"})
        self.assertEqual(self.process(q, s, uid=1000)["reason_code"], "WORK_CANCELLED")

    def test_36_cross_capsule_peer_rejected(self):
        s = self.state()
        self.submit(s, "capsule:a", "REQ-SUBA0001", peer_uid=2001)
        self.submit(s, "capsule:b", "REQ-SUBB0001", peer_uid=2002)
        q = req("WORK_CANCEL", "REQ-CANCEL004", {"capsule_id": "capsule:b"})
        self.assertEqual(self.process(q, s, uid=2001)["reason_code"], "CANCEL_PEER_NOT_AUTHORIZED")
        self.assertEqual(s.work_records["capsule:b"].state, "ACCEPTED")

    def test_37_authoritative_processor_has_no_uid_or_time_argument(self):
        signature = inspect.signature(r._process_request)
        self.assertEqual(list(signature.parameters), ["raw", "state", "sock"])
        self.assertFalse(hasattr(r, "PeerIdentity"))
        self.assertFalse(hasattr(r, "_trusted_peer_identity"))

    def test_38_cached_cancel_replay_reauthorizes_peer(self):
        s = self.state()
        self.submit(s, "capsule:replay", "REQ-REPLAY-SUB", peer_uid=2001)
        q = req("WORK_CANCEL", "REQ-REPLAY-CANCEL", {"capsule_id": "capsule:replay"})
        first = self.process(q, s, uid=2001)
        second = self.process(q, s, uid=2002)
        self.assertEqual(first["reason_code"], "WORK_CANCELLED")
        self.assertEqual(second["reason_code"], "REPLAY_PEER_MISMATCH")

    def test_39_cached_receipt_isolated_from_caller_mutation(self):
        s = self.state()
        q = req(
            "WORK_SUBMIT",
            "REQ-CACHEMUT1",
            {
                "capsule_id": "capsule:cachemut",
                "capsule_digest": "d" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
        )
        first = self.process(q, s)
        original_digest = first["decision_digest"]
        first["reason_code"] = "TAMPERED"
        first["state_snapshot"]["state_epoch"] = 999999
        replay = self.process(q, s)
        self.assertEqual(replay["reason_code"], "WORK_ACCEPTED")
        self.assertEqual(replay["decision_digest"], original_digest)
        self.assertNotEqual(replay["state_snapshot"]["state_epoch"], 999999)

    def test_40_state_capacity_transaction_is_atomic(self):
        s = self.state()
        q1 = req(
            "WORK_SUBMIT",
            "REQ-RACE00001",
            {
                "capsule_id": "capsule:race:1",
                "capsule_digest": "e" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
        )
        q2 = req(
            "WORK_SUBMIT",
            "REQ-RACE00002",
            {
                "capsule_id": "capsule:race:2",
                "capsule_digest": "f" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
        )
        barrier = threading.Barrier(3)
        results = []

        def run(q):
            barrier.wait()
            results.append(r._process_request(q, s, object()))

        with mock.patch.object(r, "get_peer_uid", return_value=1000), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ), mock.patch.object(r, "MAX_TRACKED_WORK", 1):
            t1 = threading.Thread(target=run, args=(q1,))
            t2 = threading.Thread(target=run, args=(q2,))
            t1.start()
            t2.start()
            barrier.wait()
            t1.join(timeout=2)
            t2.join(timeout=2)
        self.assertEqual(
            sorted(item["reason_code"] for item in results),
            ["WORK_ACCEPTED", "WORK_CAPACITY_EXHAUSTED"],
        )
        self.assertEqual(
            sum(1 for record in s.work_records.values() if record.state == "ACCEPTED"), 1
        )

    def test_41_duplicate_concurrent_effect_is_single_transition(self):
        s = self.state()
        q = req(
            "WORK_SUBMIT",
            "REQ-DUPRACE01",
            {
                "capsule_id": "capsule:dup-race",
                "capsule_digest": "1" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 5000,
            },
        )
        barrier = threading.Barrier(3)
        results = []

        def run():
            barrier.wait()
            results.append(r._process_request(q, s, object()))

        with mock.patch.object(r, "get_peer_uid", return_value=1000), mock.patch.object(
            r, "_now_ms", return_value=NOW
        ):
            t1 = threading.Thread(target=run)
            t2 = threading.Thread(target=run)
            t1.start()
            t2.start()
            barrier.wait()
            t1.join(timeout=2)
            t2.join(timeout=2)
        self.assertEqual([item["reason_code"] for item in results], ["WORK_ACCEPTED", "WORK_ACCEPTED"])
        self.assertEqual(len(s.work_records), 1)
        self.assertEqual(len(s.seen), 1)
        self.assertEqual(results[0], results[1])

    def test_42_cancelled_work_restores_active_capacity_and_terminal_store_is_bounded(self):
        s = self.state()
        with mock.patch.object(r, "MAX_TRACKED_WORK", 1), mock.patch.object(
            r, "MAX_TERMINAL_WORK_RECORDS", 2
        ):
            for i in range(4):
                self.assertEqual(
                    self.submit(s, f"capsule:term:{i}", f"REQ-TERM-SUB-{i:02d}")["reason_code"],
                    "WORK_ACCEPTED",
                )
                cancel = req(
                    "WORK_CANCEL",
                    f"REQ-TERM-CAN-{i:02d}",
                    {"capsule_id": f"capsule:term:{i}"},
                )
                self.assertEqual(self.process(cancel, s)["reason_code"], "WORK_CANCELLED")
                self.assertLessEqual(
                    sum(1 for record in s.work_records.values() if record.state != "ACCEPTED"),
                    2,
                )
            self.assertEqual(
                self.submit(s, "capsule:after-term", "REQ-AFTERTERM")["reason_code"],
                "WORK_ACCEPTED",
            )

    def test_43_processing_time_is_sampled_after_frame_receive(self):
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        state = self.state(owner_uid=os.getuid())
        gate = r.ConnectionGate(1)
        q = req(
            "WORK_SUBMIT",
            "REQ-LATEFRAME1",
            {
                "capsule_id": "capsule:late",
                "capsule_digest": "2" * 64,
                "route_ref": "route:sidecar-default",
                "deadline_ms": NOW + 1,
            },
            expires_at_ms=NOW + 1,
        )
        try:
            a.sendall(r.encode_frame(q))
            with mock.patch.object(r, "_now_ms", return_value=NOW + 2):
                out = r.serve_connected_once(b, state, gate)
            self.assertEqual(out["reason_code"], "REQUEST_EXPIRED")
        finally:
            a.close()
            b.close()

    def test_44_malformed_message_type_is_typed_rejection(self):
        q = req()
        q["message_type"] = []
        with self.assertRaisesRegex(r.IPCError, "UNKNOWN_MESSAGE_TYPE"):
            r.validate_envelope(q)

    def test_45_unicode_key_and_scalar_limits_are_typed(self):
        q = req()
        q["payload"] = {"note": "\ud800"}
        with self.assertRaisesRegex(r.IPCError, "INVALID_UNICODE_STRING"):
            r.validate_envelope(q)
        q = req()
        q["payload"] = {"x" * (r.MAX_STRING_BYTES + 1): "y"}
        with self.assertRaisesRegex(r.IPCError, "STRING_TOO_LARGE"):
            r.validate_envelope(q)

    def test_46_nonempty_extensions_fail_closed(self):
        q = req()
        q["extensions"] = {"note": "future"}
        with self.assertRaisesRegex(r.IPCError, "EXTENSIONS_UNSUPPORTED"):
            r.validate_envelope(q)
        q = req()
        q["extensions"] = {"endpoint": "https://example.invalid"}
        with self.assertRaisesRegex(r.IPCError, "NETWORK_ENDPOINT_FIELD_FORBIDDEN"):
            r.validate_envelope(q)


if __name__ == "__main__":
    unittest.main(verbosity=2)
