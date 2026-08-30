import unittest

from gemini_webchat_endpoint import (
    ArenaTurnEnvelopeV1,
    ArenaTurnResultV1,
    AuraToolRequestV1,
    BridgeLedgerV1,
    BridgeRefusal,
    EndpointBindingV1,
    admit_result,
    admit_tool_request,
    admit_turn,
    compile_bootstrap_prompt,
    sha256_text,
    stable_idempotency_key,
)


ARENA = "arena-gemini-test"
HEAD = "head-current"
CURRENTNESS = "cur-001"
CAPSULE = "cap-001"
TURN = "turn-001"


def make_binding(**changes):
    data = dict(
        endpoint_id="gemini-web-01",
        visit_id="visit-01",
        arena_sid=ARENA,
        conversation_locator_hash="convhash",
        transport_mode="ASSISTED_EXTENSION",
        max_effect_class="D0",
    )
    data.update(changes)
    return EndpointBindingV1(**data)


def make_envelope(**changes):
    idem = stable_idempotency_key(ARENA, HEAD, CURRENTNESS, CAPSULE, TURN)
    data = dict(
        turn_id=TURN,
        capsule_id=CAPSULE,
        arena_sid=ARENA,
        arena_head=HEAD,
        currentness_hash=CURRENTNESS,
        mission_id="mission-gwb",
        mission="Bridge Gemini web chat into Aura Arena",
        purpose="Provider-neutral governed cognition endpoint",
        objective="Validate one bounded turn",
        claim_id="claim-001",
        claim_lease="lease-001",
        idempotency_key=idem,
        effect_ceiling="D0",
        allowed_tools=("drive.read", "arena.status.write"),
        context_refs=("drive:front-door",),
        sibling_claim_refs=("claim-sibling",),
    )
    data.update(changes)
    return ArenaTurnEnvelopeV1(**data)


def make_result(text="done", **changes):
    data = dict(
        turn_id=TURN,
        capsule_id=CAPSULE,
        endpoint_id="gemini-web-01",
        visit_id="visit-01",
        arena_sid=ARENA,
        arena_head=HEAD,
        currentness_hash=CURRENTNESS,
        visible_text=text,
        visible_text_sha256=sha256_text(text),
        status="COMPLETE",
    )
    data.update(changes)
    return ArenaTurnResultV1(**data)


class GeminiWebchatEndpointTests(unittest.TestCase):
    def test_valid_assisted_turn_admits(self):
        admit_turn(make_binding(), make_envelope(), current_arena_head=HEAD, currentness_hash=CURRENTNESS)

    def test_guarded_auto_requires_owner_enablement(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            make_binding(transport_mode="GUARDED_AUTO").validate()
        self.assertEqual(ctx.exception.code, "AUTO_SEND_NOT_OWNER_ENABLED")

    def test_wrong_browser_origin_fails_closed(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            make_binding(browser_origin="https://example.com").validate()
        self.assertEqual(ctx.exception.code, "BROWSER_ORIGIN_NOT_ALLOWED")

    def test_stale_arena_head_refused_before_send(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            admit_turn(make_binding(), make_envelope(), current_arena_head="new-head", currentness_hash=CURRENTNESS)
        self.assertEqual(ctx.exception.code, "STALE_ARENA_HEAD")

    def test_stale_currentness_refused_before_send(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            admit_turn(make_binding(), make_envelope(), current_arena_head=HEAD, currentness_hash="cur-002")
        self.assertEqual(ctx.exception.code, "STALE_CURRENTNESS")

    def test_idempotency_key_is_bound_to_head_and_turn(self):
        bad = make_envelope(idempotency_key="wrong")
        with self.assertRaises(BridgeRefusal) as ctx:
            bad.validate()
        self.assertEqual(ctx.exception.code, "IDEMPOTENCY_KEY_MISMATCH")

    def test_duplicate_turn_send_is_refused(self):
        ledger = BridgeLedgerV1()
        ledger.mark_turn_sent(TURN)
        with self.assertRaises(BridgeRefusal) as ctx:
            ledger.mark_turn_sent(TURN)
        self.assertEqual(ctx.exception.code, "DUPLICATE_TURN_SEND")

    def test_result_must_match_endpoint_visit_and_turn(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            admit_result(
                make_binding(),
                make_envelope(),
                make_result(visit_id="other-visit"),
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
            )
        self.assertEqual(ctx.exception.code, "TURN_RESULT_BINDING_MISMATCH")

    def test_visible_result_hash_is_verified(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            make_result(visible_text_sha256="bad").validate()
        self.assertEqual(ctx.exception.code, "VISIBLE_RESULT_HASH_MISMATCH")

    def test_result_for_unsent_turn_is_refused(self):
        ledger = BridgeLedgerV1()
        with self.assertRaises(BridgeRefusal) as ctx:
            ledger.accept_result(make_result())
        self.assertEqual(ctx.exception.code, "RESULT_FOR_UNSENT_TURN")

    def test_duplicate_result_is_refused(self):
        ledger = BridgeLedgerV1()
        ledger.mark_turn_sent(TURN)
        ledger.accept_result(make_result())
        with self.assertRaises(BridgeRefusal) as ctx:
            ledger.accept_result(make_result())
        self.assertEqual(ctx.exception.code, "DUPLICATE_TURN_RESULT")

    def test_tool_request_must_be_allowlisted(self):
        request = AuraToolRequestV1(
            request_id="tool-001",
            capsule_id=CAPSULE,
            turn_id=TURN,
            tool_id="github.delete",
            args={},
            requested_effect_class="D0",
            reason="test",
        )
        with self.assertRaises(BridgeRefusal) as ctx:
            admit_tool_request(
                make_envelope(),
                request,
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                tool_effect_classes={"github.delete": "D2"},
            )
        self.assertEqual(ctx.exception.code, "TOOL_NOT_ALLOWED")

    def test_tool_effect_must_match_admitted_route(self):
        request = AuraToolRequestV1(
            request_id="tool-001",
            capsule_id=CAPSULE,
            turn_id=TURN,
            tool_id="drive.read",
            args={"id": "x"},
            requested_effect_class="READ",
            reason="hydrate source",
        )
        admit_tool_request(
            make_envelope(),
            request,
            current_arena_head=HEAD,
            currentness_hash=CURRENTNESS,
            tool_effect_classes={"drive.read": "READ"},
        )

        mismatch = AuraToolRequestV1(
            request_id="tool-002",
            capsule_id=CAPSULE,
            turn_id=TURN,
            tool_id="drive.read",
            args={"id": "x"},
            requested_effect_class="D0",
            reason="hydrate source",
        )
        with self.assertRaises(BridgeRefusal) as ctx:
            admit_tool_request(
                make_envelope(),
                mismatch,
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                tool_effect_classes={"drive.read": "READ"},
            )
        self.assertEqual(ctx.exception.code, "TOOL_EFFECT_CLASS_MISMATCH")

    def test_tool_over_capsule_effect_is_refused(self):
        request = AuraToolRequestV1(
            request_id="tool-001",
            capsule_id=CAPSULE,
            turn_id=TURN,
            tool_id="arena.status.write",
            args={},
            requested_effect_class="D1",
            reason="write",
        )
        with self.assertRaises(BridgeRefusal) as ctx:
            admit_tool_request(
                make_envelope(),
                request,
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                tool_effect_classes={"arena.status.write": "D1"},
            )
        self.assertEqual(ctx.exception.code, "TOOL_REQUEST_EXCEEDS_CAPSULE_EFFECT")

    def test_duplicate_tool_request_is_refused(self):
        request = AuraToolRequestV1(
            request_id="tool-001",
            capsule_id=CAPSULE,
            turn_id=TURN,
            tool_id="drive.read",
            args={},
            requested_effect_class="READ",
            reason="hydrate",
        )
        ledger = BridgeLedgerV1()
        ledger.accept_tool_request(request)
        with self.assertRaises(BridgeRefusal) as ctx:
            ledger.accept_tool_request(request)
        self.assertEqual(ctx.exception.code, "DUPLICATE_TOOL_REQUEST")

    def test_bootstrap_prompt_contains_arena_contract_not_credentials(self):
        prompt = compile_bootstrap_prompt(make_binding(), make_envelope())
        self.assertIn("AURA_ARENA_BOOTSTRAP_V1", prompt)
        self.assertIn("AuraToolRequestV1", prompt)
        self.assertIn("Do not expose or request credentials", prompt)
        self.assertNotIn("cookie", prompt.lower())


if __name__ == "__main__":
    unittest.main()
