import ast
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path

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
    def state(self):
        return r.ResidentState(
            "gen-current", "currentness:1", "authority:local-owner", owner_uid=1000
        )

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
        return r.process_request(q, s, NOW, peer_uid)

    def test_01_health(self):
        self.assertEqual(
            r.process_request(req(), self.state(), NOW, 1000)["reason_code"],
            "HEALTH_OK",
        )

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
        first = r.process_request(q, s, NOW, 1000)
        second = r.process_request(q, s, NOW + 1, 1000)
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
        self.assertEqual(
            r.process_request(q, s, NOW, 1000)["reason_code"],
            "REQUEST_ID_COLLISION",
        )

    def test_08_stale_generation(self):
        self.assertEqual(
            r.process_request(
                req(generation="gen-old"), self.state(), NOW, 1000
            )["reason_code"],
            "STALE_OR_FOREIGN_GENERATION",
        )

    def test_09_currentness(self):
        self.assertEqual(
            r.process_request(
                req(currentness_ref="currentness:old"), self.state(), NOW, 1000
            )["reason_code"],
            "CURRENTNESS_MISMATCH",
        )

    def test_10_expired(self):
        self.assertEqual(
            r.process_request(
                req(expires_at_ms=NOW - 1), self.state(), NOW, 1000
            )["reason_code"],
            "REQUEST_EXPIRED",
        )

    def test_11_admin_nonowner(self):
        self.assertEqual(
            r.process_request(
                req("ADMIN_RECONCILE"), self.state(), NOW, 2000
            )["reason_code"],
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
        status = r.process_request(
            req("WORK_STATUS", "REQ-STATUS01", {"capsule_id": "capsule:001"}),
            s,
            NOW,
            1000,
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
        self.assertEqual(
            r.process_request(q, self.state(), NOW, 1000)["reason_code"],
            "WORK_DEADLINE_EXPIRED",
        )

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
        first = r.process_request(q, self.state(), NOW, 1000)
        second = r.process_request(q, self.state(), NOW, 1000)
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
            state = r.ResidentState(
                "gen-current",
                "currentness:1",
                "authority:local-owner",
                owner_uid=os.getuid(),
            )
            gate = r.ConnectionGate(1)
            errors = []

            def server():
                try:
                    conn, _ = listener.accept()
                    try:
                        r.serve_connected_once(conn, state, NOW, gate)
                    finally:
                        conn.close()
                except Exception as exc:
                    errors.append(exc)
                finally:
                    listener.close()

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
            r.process_request(
                req(authority_ref="authority:foreign"), self.state(), NOW, 1000
            )["reason_code"],
            "AUTHORITY_MISMATCH",
        )

    def test_25_not_yet_valid(self):
        self.assertEqual(
            r.process_request(
                req(issued_at_ms=NOW + 1, expires_at_ms=NOW + 1000),
                self.state(),
                NOW,
                1000,
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
            self.assertEqual(
                r.process_request(q, s, NOW, 5000)["reason_code"],
                "AUTHORITY_MISMATCH",
            )
        self.assertEqual(len(s.seen), 0)
        self.assertEqual(
            self.submit(s, "capsule:after-reject-flood", "REQ-AFTERREJ")[
                "reason_code"
            ],
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
        out = r.process_request(q, s, NOW + 2, 1000)
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
        self.assertEqual(
            r.process_request(q, s, NOW, 1000)["reason_code"],
            "WORK_CAPACITY_EXHAUSTED",
        )

    def test_29_receipt_snapshot_binds_authority(self):
        out = r.process_request(req(), self.state(), NOW, 1000)
        self.assertEqual(
            out["state_snapshot"]["authority_ref"], "authority:local-owner"
        )

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
            with self.assertRaisesRegex(
                r.IPCError, "CONNECTION_CAPACITY_EXHAUSTED"
            ):
                with gate.slot():
                    pass

    def test_33_cancel_creator_allowed(self):
        s = self.state()
        self.submit(s, "capsule:owned", "REQ-OWNED001", peer_uid=2001)
        q = req(
            "WORK_CANCEL",
            "REQ-CANCEL001",
            {"capsule_id": "capsule:owned"},
        )
        self.assertEqual(
            r.process_request(q, s, NOW, 2001)["reason_code"],
            "WORK_CANCELLED",
        )

    def test_34_cancel_nonowner_rejected(self):
        s = self.state()
        self.submit(s, "capsule:owned2", "REQ-OWNED002", peer_uid=2001)
        q = req(
            "WORK_CANCEL",
            "REQ-CANCEL002",
            {"capsule_id": "capsule:owned2"},
        )
        self.assertEqual(
            r.process_request(q, s, NOW, 2002)["reason_code"],
            "CANCEL_PEER_NOT_AUTHORIZED",
        )
        self.assertEqual(s.work_records["capsule:owned2"].state, "ACCEPTED")

    def test_35_owner_can_cancel_cross_capsule(self):
        s = self.state()
        self.submit(s, "capsule:owned3", "REQ-OWNED003", peer_uid=2001)
        q = req(
            "WORK_CANCEL",
            "REQ-CANCEL003",
            {"capsule_id": "capsule:owned3"},
        )
        self.assertEqual(
            r.process_request(q, s, NOW, 1000)["reason_code"],
            "WORK_CANCELLED",
        )

    def test_36_cross_capsule_peer_rejected(self):
        s = self.state()
        self.submit(s, "capsule:a", "REQ-SUBA0001", peer_uid=2001)
        self.submit(s, "capsule:b", "REQ-SUBB0001", peer_uid=2002)
        q = req(
            "WORK_CANCEL",
            "REQ-CANCEL004",
            {"capsule_id": "capsule:b"},
        )
        self.assertEqual(
            r.process_request(q, s, NOW, 2001)["reason_code"],
            "CANCEL_PEER_NOT_AUTHORIZED",
        )
        self.assertEqual(s.work_records["capsule:b"].state, "ACCEPTED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
