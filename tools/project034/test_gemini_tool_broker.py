import unittest

from gemini_tool_broker import (
    ToolAdmissionV1,
    ToolRouteV1,
    execute_admitted_tool,
)
from gemini_webchat_endpoint import (
    ArenaTurnEnvelopeV1,
    AuraToolRequestV1,
    BridgeRefusal,
    stable_idempotency_key,
)


ARENA = "arena-tool-test"
HEAD = "head-001"
CURRENTNESS = "cur-001"
CAPSULE = "cap-001"
TURN = "turn-001"


def envelope():
    return ArenaTurnEnvelopeV1(
        turn_id=TURN,
        capsule_id=CAPSULE,
        arena_sid=ARENA,
        arena_head=HEAD,
        currentness_hash=CURRENTNESS,
        mission_id="gwb",
        mission="Gemini bridge",
        purpose="governed tools",
        objective="read one source",
        claim_id="claim-001",
        claim_lease="lease-001",
        idempotency_key=stable_idempotency_key(ARENA, HEAD, CURRENTNESS, CAPSULE, TURN),
        effect_ceiling="D0",
        allowed_tools=("drive.read", "arena.status.write"),
    )


def request(args=None):
    return AuraToolRequestV1(
        request_id="req-001",
        capsule_id=CAPSULE,
        turn_id=TURN,
        tool_id="drive.read",
        args=args or {"ref": "drive:source"},
        requested_effect_class="READ",
        reason="hydrate the bounded source",
    )


def route(max_result_bytes=65536):
    return ToolRouteV1(
        tool_id="drive.read",
        executor_id="aura.drive.read.v1",
        capability_ref="aura://capability/drive/read/v1",
        effect_class="READ",
        max_result_bytes=max_result_bytes,
    )


def admission_provider(env, req, rt, digest):
    return ToolAdmissionV1(
        admission_ref="arena:admission:req-001",
        request_digest=digest,
        arena_sid=env.arena_sid,
        arena_head=HEAD,
        currentness_hash=CURRENTNESS,
        capsule_id=env.capsule_id,
        turn_id=env.turn_id,
        claim_id=env.claim_id,
        claim_lease=env.claim_lease,
        tool_id=req.tool_id,
        executor_id=rt.executor_id,
        capability_ref=rt.capability_ref,
        effect_class=rt.effect_class,
        authority_ref="arena:authority:owner",
        fence_ref="arena:fence:001",
    )


class GeminiToolBrokerTests(unittest.TestCase):
    def test_valid_read_executes_after_ack(self):
        order = []

        def ack(_record):
            order.append("ack")

        def executor(args):
            order.append("effect")
            return {"title": "source", "ref": args["ref"]}

        result, receipt = execute_admitted_tool(
            envelope(),
            request(),
            current_arena_head=HEAD,
            currentness_hash=CURRENTNESS,
            routes={"drive.read": route()},
            executors={"aura.drive.read.v1": executor},
            admission_provider=admission_provider,
            emit_ack=ack,
        )
        self.assertEqual(order, ["ack", "effect"])
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.bounded_result["title"], "source")
        self.assertEqual(receipt.executor_id, "aura.drive.read.v1")
        self.assertEqual(receipt.status, "OK")
        self.assertEqual(len(receipt.receipt_id), 32)

    def test_caller_cannot_supply_credentials_or_executor_controls(self):
        called = []
        with self.assertRaises(BridgeRefusal) as ctx:
            execute_admitted_tool(
                envelope(),
                request({"ref": "drive:x", "api_key": "not-allowed"}),
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                routes={"drive.read": route()},
                executors={"aura.drive.read.v1": lambda _args: called.append(True)},
                admission_provider=admission_provider,
            )
        self.assertEqual(ctx.exception.code, "TOOL_CALLER_CONTROL_FORBIDDEN")
        self.assertEqual(called, [])

    def test_stale_context_fails_before_admission_or_executor(self):
        calls = []

        def admission(*_args):
            calls.append("admission")
            return admission_provider(*_args)

        with self.assertRaises(BridgeRefusal) as ctx:
            execute_admitted_tool(
                envelope(),
                request(),
                current_arena_head="head-new",
                currentness_hash=CURRENTNESS,
                routes={"drive.read": route()},
                executors={"aura.drive.read.v1": lambda _args: calls.append("effect")},
                admission_provider=admission,
            )
        self.assertEqual(ctx.exception.code, "STALE_TOOL_CONTEXT")
        self.assertEqual(calls, [])

    def test_mismatched_host_admission_fails_before_effect(self):
        calls = []

        def bad_admission(env, req, rt, digest):
            good = admission_provider(env, req, rt, digest)
            return ToolAdmissionV1(**{**good.__dict__, "executor_id": "wrong-executor"})

        with self.assertRaises(BridgeRefusal) as ctx:
            execute_admitted_tool(
                envelope(),
                request(),
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                routes={"drive.read": route()},
                executors={"aura.drive.read.v1": lambda _args: calls.append("effect")},
                admission_provider=bad_admission,
            )
        self.assertEqual(ctx.exception.code, "TOOL_ADMISSION_BINDING_MISMATCH")
        self.assertEqual(calls, [])

    def test_ack_failure_prevents_executor_effect(self):
        calls = []

        def bad_ack(_record):
            raise RuntimeError("sink unavailable")

        with self.assertRaises(RuntimeError):
            execute_admitted_tool(
                envelope(),
                request(),
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                routes={"drive.read": route()},
                executors={"aura.drive.read.v1": lambda _args: calls.append("effect")},
                admission_provider=admission_provider,
                emit_ack=bad_ack,
            )
        self.assertEqual(calls, [])

    def test_sensitive_structured_result_fields_are_redacted(self):
        result, _receipt = execute_admitted_tool(
            envelope(),
            request(),
            current_arena_head=HEAD,
            currentness_hash=CURRENTNESS,
            routes={"drive.read": route()},
            executors={
                "aura.drive.read.v1": lambda _args: {
                    "title": "source",
                    "nested": {"access_token": "secret-value", "safe": 1},
                }
            },
            admission_provider=admission_provider,
        )
        self.assertEqual(result.bounded_result["nested"]["access_token"], "[REDACTED]")
        self.assertEqual(result.bounded_result["nested"]["safe"], 1)

    def test_result_bound_is_enforced(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            execute_admitted_tool(
                envelope(),
                request(),
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                routes={"drive.read": route(max_result_bytes=32)},
                executors={"aura.drive.read.v1": lambda _args: {"body": "x" * 200}},
                admission_provider=admission_provider,
            )
        self.assertEqual(ctx.exception.code, "TOOL_RESULT_TOO_LARGE")

    def test_unknown_executor_fails_after_admission_but_before_effect(self):
        with self.assertRaises(BridgeRefusal) as ctx:
            execute_admitted_tool(
                envelope(),
                request(),
                current_arena_head=HEAD,
                currentness_hash=CURRENTNESS,
                routes={"drive.read": route()},
                executors={},
                admission_provider=admission_provider,
            )
        self.assertEqual(ctx.exception.code, "TOOL_EXECUTOR_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
