import json
import unittest

from tools.project006 import creator_media_handoff as m


class FakeTransport:
    def __init__(self, polls, status_url="https://platform.higgsfield.ai/requests/r1/status"):
        self.polls = list(polls)
        self.status_url = status_url
        self.create_calls = []
        self.poll_calls = []

    def create(self, path, *, credential, prompt, timeout):
        self.create_calls.append((path, credential, prompt, timeout))
        return {"request_id": "r1", "status_url": self.status_url}

    def poll(self, status_url, *, credential, timeout):
        self.poll_calls.append((status_url, credential, timeout))
        return self.polls.pop(0)


def handoff(route="higgsfield.kling-3.0"):
    return {
        "handoff_version": m.HANDOFF_VERSION,
        "root_dispatch_id": "root-1",
        "dispatch_generation": 24,
        "intent_digest": "a" * 64,
        "validation_receipt_ref": "validation-1",
        "media_route_ref": route,
        "capsule_id": "cap-1",
        "lease_generation": 7,
        "fencing_token": "private-fence",
        "currentness_ref": "arena-gen24",
        "spend_grant_ref": "owner-chat-spend-grant-1",
        "prompt": "A paper boat crossing a rain puddle.",
        "deadline_ms": 10000,
        "poll_initial_ms": 100,
        "poll_max_ms": 100,
    }


class CreatorMediaHandoffTests(unittest.TestCase):
    def test_video_success_and_secret_not_in_receipt(self):
        tx = FakeTransport([
            {"status": "in_progress"},
            {"status": "completed", "video": {"url": "https://cdn.example/video.mp4"}},
        ])
        out = m.dispatch_media_handoff(
            handoff(),
            credential_resolver=lambda: "id:supersecret",
            transport=tx,
            sleep=lambda _: None,
        )
        self.assertEqual(out["status"], "OK")
        self.assertEqual(out["asset_url"], "https://cdn.example/video.mp4")
        self.assertEqual(out["media_kind"], "video")
        self.assertNotIn("supersecret", json.dumps(out))
        self.assertNotIn("private-fence", json.dumps(out))
        self.assertEqual(tx.create_calls[0][0], "/kling-video/v3.0/std/text-to-video")

    def test_image_success(self):
        tx = FakeTransport([
            {"status": "completed", "images": [{"url": "https://cdn.example/image.png"}]}
        ])
        out = m.dispatch_media_handoff(
            handoff("higgsfield.qwen-image-3"),
            credential_resolver=lambda: "id:secret",
            transport=tx,
            sleep=lambda _: None,
        )
        self.assertEqual(out["status"], "OK")
        self.assertEqual(out["media_kind"], "image")
        self.assertEqual(out["asset_url"], "https://cdn.example/image.png")

    def test_unknown_endpoint_or_api_key_field_fails_closed(self):
        for field in ("endpoint", "api_key", "provider", "status_url"):
            raw = handoff()
            raw[field] = "attacker-value"
            with self.assertRaises(m.MediaHandoffError):
                m.validate_handoff(raw)

    def test_unregistered_route_fails(self):
        raw = handoff("higgsfield.attacker-model")
        with self.assertRaises(m.MediaHandoffError):
            m.validate_handoff(raw)

    def test_spend_grant_required(self):
        raw = handoff()
        raw.pop("spend_grant_ref")
        with self.assertRaises(m.MediaHandoffError):
            m.validate_handoff(raw)

    def test_no_credential_is_typed_and_no_provider_call(self):
        tx = FakeTransport([])
        out = m.dispatch_media_handoff(
            handoff(), credential_resolver=lambda: None, transport=tx, sleep=lambda _: None
        )
        self.assertEqual(out["status"], "NO_CREDENTIAL")
        self.assertEqual(tx.create_calls, [])

    def test_provider_failure_is_terminal_without_asset(self):
        tx = FakeTransport([{"status": "failed", "error": "secret-ish provider detail"}])
        out = m.dispatch_media_handoff(
            handoff(),
            credential_resolver=lambda: "id:secret",
            transport=tx,
            sleep=lambda _: None,
        )
        self.assertEqual(out["status"], "PROVIDER_FAILED")
        self.assertIsNone(out["asset_url"])
        self.assertNotIn("secret-ish", json.dumps(out))

    def test_status_url_escape_is_rejected_without_sending_credential(self):
        class Tx(m.HiggsfieldTransport):
            def create(self, path, *, credential, prompt, timeout):
                return {"request_id": "r1", "status_url": "https://evil.example/steal"}

        out = m.dispatch_media_handoff(
            handoff(),
            credential_resolver=lambda: "id:secret",
            transport=Tx(opener=object()),
            sleep=lambda _: None,
        )
        self.assertEqual(out["status"], "STATUS_URL_REJECTED")

    def test_request_digest_changes_with_fence_without_exposing_it(self):
        tx1 = FakeTransport([{"status": "completed", "video": {"url": "https://cdn/v1.mp4"}}])
        tx2 = FakeTransport([{"status": "completed", "video": {"url": "https://cdn/v2.mp4"}}])
        a = handoff()
        b = handoff()
        b["fencing_token"] = "different-private-fence"
        out1 = m.dispatch_media_handoff(
            a, credential_resolver=lambda: "id:s", transport=tx1, sleep=lambda _: None
        )
        out2 = m.dispatch_media_handoff(
            b, credential_resolver=lambda: "id:s", transport=tx2, sleep=lambda _: None
        )
        self.assertNotEqual(out1["request_digest"], out2["request_digest"])
        self.assertNotIn("different-private-fence", json.dumps(out2))


if __name__ == "__main__":
    unittest.main()
