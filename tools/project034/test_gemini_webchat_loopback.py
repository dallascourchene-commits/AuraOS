import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gemini_webchat_endpoint import (
    ArenaTurnEnvelopeV1,
    ArenaTurnResultV1,
    AuraToolRequestV1,
    BridgeRefusal,
    EndpointBindingV1,
    sha256_text,
    stable_idempotency_key,
)
from gemini_webchat_loopback import GeminiLoopbackServer, LoopbackContextV1, serve


ARENA = "arena-loopback-test"
HEAD = "head-001"
CURRENTNESS = "cur-001"
CAPSULE = "cap-001"
TURN = "turn-001"


def make_binding():
    return EndpointBindingV1(
        endpoint_id="gemini-web-001",
        visit_id="visit-001",
        arena_sid=ARENA,
        conversation_locator_hash="convhash",
        transport_mode="ASSISTED_EXTENSION",
        max_effect_class="D0",
    )


def make_envelope():
    return ArenaTurnEnvelopeV1(
        turn_id=TURN,
        capsule_id=CAPSULE,
        arena_sid=ARENA,
        arena_head=HEAD,
        currentness_hash=CURRENTNESS,
        mission_id="mission-gwb",
        mission="Bridge Gemini web chat into Aura Arena",
        purpose="Governed normal-browser endpoint",
        objective="Return one visible bounded result",
        claim_id="claim-001",
        claim_lease="lease-001",
        idempotency_key=stable_idempotency_key(ARENA, HEAD, CURRENTNESS, CAPSULE, TURN),
        effect_ceiling="D0",
        allowed_tools=("drive.read",),
    )


class LoopbackFacadeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ctx = LoopbackContextV1(self.root)
        self.ctx.store.bind_endpoint(make_binding())
        self.ctx.currentness_path.write_text(
            json.dumps(
                {
                    "arena_sid": ARENA,
                    "arena_head": HEAD,
                    "currentness_hash": CURRENTNESS,
                }
            ),
            encoding="utf-8",
        )
        self.ctx.store.publish_turn(
            make_envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS
        )
        (self.ctx.store.state_dir / "tool_effect_classes_v1.json").write_text(
            json.dumps({"drive.read": "READ"}), encoding="utf-8"
        )
        self.server = GeminiLoopbackServer(("127.0.0.1", 0), self.ctx)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def request(self, path, *, method="GET", body=None, auth=True):
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = f"Bearer {self.ctx.token}"
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_health_does_not_require_bridge_token(self):
        status, payload = self.request("/v1/health", auth=False)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "OK")

    def test_turn_poll_requires_auth(self):
        qs = urlencode({"endpoint_id": "gemini-web-001", "visit_id": "visit-001"})
        status, payload = self.request(f"/v1/turns/next?{qs}", auth=False)
        self.assertEqual(status, 401)
        self.assertEqual(payload["code"], "LOOPBACK_AUTH_REQUIRED")

    def test_next_turn_is_bound_and_returns_visible_bootstrap(self):
        qs = urlencode({"endpoint_id": "gemini-web-001", "visit_id": "visit-001"})
        status, payload = self.request(f"/v1/turns/next?{qs}")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "TURN_READY")
        self.assertEqual(payload["turn_id"], TURN)
        self.assertIn("AURA_ARENA_BOOTSTRAP_V1", payload["prompt_text"])
        self.assertEqual(payload["envelope"]["arena_head"], HEAD)

    def test_wrong_endpoint_or_visit_fails_closed(self):
        qs = urlencode({"endpoint_id": "gemini-web-other", "visit_id": "visit-001"})
        status, payload = self.request(f"/v1/turns/next?{qs}")
        self.assertEqual(status, 409)
        self.assertEqual(payload["code"], "ENDPOINT_POLL_BINDING_MISMATCH")

    def test_stale_currentness_fails_before_turn_delivery(self):
        self.ctx.currentness_path.write_text(
            json.dumps(
                {
                    "arena_sid": ARENA,
                    "arena_head": "head-new",
                    "currentness_hash": "cur-new",
                }
            ),
            encoding="utf-8",
        )
        qs = urlencode({"endpoint_id": "gemini-web-001", "visit_id": "visit-001"})
        status, payload = self.request(f"/v1/turns/next?{qs}")
        self.assertEqual(status, 409)
        self.assertEqual(payload["code"], "STALE_ARENA_HEAD")

    def test_visible_result_roundtrip_is_accepted_once(self):
        text = "Visible Gemini answer"
        result = {
            "turn_id": TURN,
            "capsule_id": CAPSULE,
            "endpoint_id": "gemini-web-001",
            "visit_id": "visit-001",
            "arena_sid": ARENA,
            "arena_head": HEAD,
            "currentness_hash": CURRENTNESS,
            "visible_text": text,
            "visible_text_sha256": sha256_text(text),
            "status": "COMPLETE",
            "residuals": [],
            "receipt_refs": [],
            "provider_id": "GEMINI_WEBCHAT",
        }
        status, payload = self.request("/v1/results", method="POST", body=result)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ACCEPTED")
        status2, payload2 = self.request("/v1/results", method="POST", body=result)
        self.assertEqual(status2, 409)
        self.assertEqual(payload2["code"], "DUPLICATE_TURN_RESULT")

    def test_tool_request_roundtrip_hits_effect_policy(self):
        request = {
            "request_id": "req-001",
            "capsule_id": CAPSULE,
            "turn_id": TURN,
            "tool_id": "drive.read",
            "args": {"ref": "drive:x"},
            "requested_effect_class": "READ",
            "reason": "Hydrate source",
        }
        status, payload = self.request("/v1/tool-requests", method="POST", body=request)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ACCEPTED")

    def test_loopback_token_is_not_provider_credential_material(self):
        token = self.ctx.token
        self.assertGreaterEqual(len(token), 32)
        self.assertNotIn("google", token.lower())
        self.assertNotIn("cookie", token.lower())
        self.assertTrue(self.ctx.token_path.exists())

    def test_non_loopback_bind_is_refused_before_server_start(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            serve(self.root, host="0.0.0.0", port=0)
        self.assertEqual(ctx.exception.code, "NON_LOOPBACK_BIND_REFUSED")


if __name__ == "__main__":
    unittest.main()
