import json
import tempfile
import unittest
from pathlib import Path

from gemini_webchat_endpoint import (
    ArenaTurnEnvelopeV1,
    ArenaTurnResultV1,
    AuraToolRequestV1,
    AuraToolResultV1,
    BridgeRefusal,
    EndpointBindingV1,
    sha256_text,
    stable_idempotency_key,
)
from gemini_webchat_relay import RelayStoreV1


ARENA = "arena-gwb"
HEAD = "head-001"
CURRENTNESS = "cur-001"
CAPSULE = "cap-001"
TURN = "turn-001"


def binding(visit_id="visit-001"):
    return EndpointBindingV1(
        endpoint_id="gemini-web-001",
        visit_id=visit_id,
        arena_sid=ARENA,
        conversation_locator_hash="conv-001",
        transport_mode="ASSISTED_EXTENSION",
        max_effect_class="D0",
    )


def envelope(turn_id=TURN, capsule_id=CAPSULE):
    return ArenaTurnEnvelopeV1(
        turn_id=turn_id,
        capsule_id=capsule_id,
        arena_sid=ARENA,
        arena_head=HEAD,
        currentness_hash=CURRENTNESS,
        mission_id="gwb",
        mission="Gemini webchat bridge",
        purpose="Arena governed browser endpoint",
        objective="one bounded turn",
        claim_id="claim-001",
        claim_lease="lease-001",
        idempotency_key=stable_idempotency_key(ARENA, HEAD, CURRENTNESS, capsule_id, turn_id),
        effect_ceiling="D0",
        allowed_tools=("drive.read", "arena.status.write"),
    )


def result(text="visible result"):
    return ArenaTurnResultV1(
        turn_id=TURN,
        capsule_id=CAPSULE,
        endpoint_id="gemini-web-001",
        visit_id="visit-001",
        arena_sid=ARENA,
        arena_head=HEAD,
        currentness_hash=CURRENTNESS,
        visible_text=text,
        visible_text_sha256=sha256_text(text),
    )


class RelayStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = RelayStoreV1(self.root)
        self.store.bind_endpoint(binding())

    def tearDown(self):
        self.tmp.cleanup()

    def test_turn_publish_is_durable_and_pending(self):
        receipt = self.store.publish_turn(envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS)
        path = Path(receipt["path"])
        self.assertTrue(path.exists())
        self.assertEqual([path], list(self.store.list_pending_turns()))
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "ArenaTurnEnvelopeV1")
        self.assertTrue(Path(receipt["receipt"]).exists())

    def test_duplicate_turn_publish_fails_closed(self):
        self.store.publish_turn(envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS)
        with self.assertRaises(BridgeRefusal) as ctx:
            self.store.publish_turn(envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS)
        self.assertEqual(ctx.exception.code, "DUPLICATE_TURN_SEND")

    def test_stale_turn_is_not_written(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            self.store.publish_turn(envelope(), current_arena_head="new-head", currentness_hash=CURRENTNESS)
        self.assertEqual(ctx.exception.code, "STALE_ARENA_HEAD")
        self.assertEqual([], list(self.store.turn_outbox.glob("*.json")))

    def test_result_requires_prior_send_and_removes_pending(self):
        self.store.publish_turn(envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS)
        out = self.store.accept_turn_result(
            envelope(), result(), current_arena_head=HEAD, currentness_hash=CURRENTNESS
        )
        self.assertTrue(Path(out["path"]).exists())
        self.assertEqual([], list(self.store.list_pending_turns()))

    def test_relay_restart_preserves_replay_state(self):
        self.store.publish_turn(envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS)
        restarted = RelayStoreV1(self.root)
        with self.assertRaises(BridgeRefusal) as ctx:
            restarted.publish_turn(envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS)
        self.assertEqual(ctx.exception.code, "DUPLICATE_TURN_SEND")

    def test_endpoint_rebind_requires_release(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            self.store.bind_endpoint(binding(visit_id="visit-other"))
        self.assertEqual(ctx.exception.code, "ENDPOINT_REBIND_REQUIRES_EXPLICIT_RELEASE")
        self.store.release_endpoint(endpoint_id="gemini-web-001", visit_id="visit-001")
        self.store.bind_endpoint(binding(visit_id="visit-other"))
        self.assertEqual(self.store.load_binding().visit_id, "visit-other")

    def test_tool_request_and_result_are_bound(self):
        env = envelope()
        request = AuraToolRequestV1(
            request_id="req-001",
            capsule_id=CAPSULE,
            turn_id=TURN,
            tool_id="drive.read",
            args={"ref": "drive:x"},
            requested_effect_class="READ",
            reason="hydrate source",
        )
        req_out = self.store.accept_tool_request(
            env,
            request,
            current_arena_head=HEAD,
            currentness_hash=CURRENTNESS,
            tool_effect_classes={"drive.read": "READ"},
        )
        self.assertTrue(Path(req_out["path"]).exists())
        tool_result = AuraToolResultV1(
            request_id="req-001",
            capsule_id=CAPSULE,
            status="OK",
            currentness_hash=CURRENTNESS,
            bounded_result={"title": "source"},
            receipt_ref="arena:receipt:req-001",
        )
        result_out = self.store.publish_tool_result(tool_result)
        self.assertTrue(Path(result_out["path"]).exists())

    def test_tool_result_without_request_fails(self):
        tool_result = AuraToolResultV1(
            request_id="req-missing",
            capsule_id=CAPSULE,
            status="OK",
            currentness_hash=CURRENTNESS,
            bounded_result={"x": 1},
        )
        with self.assertRaises(BridgeRefusal) as ctx:
            self.store.publish_tool_result(tool_result)
        self.assertEqual(ctx.exception.code, "TOOL_RESULT_WITHOUT_ACCEPTED_REQUEST")

    def test_atomic_create_rejects_existing_object(self):
        path = self.store.turn_results / "collision.json"
        path.write_text("existing\n", encoding="utf-8")
        with self.assertRaises(BridgeRefusal) as ctx:
            self.store._atomic_create_json(path, {"new": True})
        self.assertEqual(ctx.exception.code, "RELAY_OBJECT_ALREADY_EXISTS")
        self.assertEqual(path.read_text(encoding="utf-8"), "existing\n")


if __name__ == "__main__":
    unittest.main()
