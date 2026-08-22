from __future__ import annotations

import copy
import unittest

from tools.project006.drive_command_executor_hook import (
    CommandHookError,
    EXECUTOR_ID,
    execute_admitted_command,
    validate_admitted_command,
)


class _FakeExecutor:
    provider = "deepseek"
    model = "deepseek-test"

    def __init__(
        self,
        events: list[str],
        *,
        text: str | None = "bounded-result",
        error: str | None = None,
    ):
        self.events = events
        self.text = text
        self.error = error
        self.prompts: list[str] = []
        self.kwargs: list[dict] = []

    def generate(self, prompt: str, **kwargs):
        self.events.append("generate")
        self.prompts.append(prompt)
        self.kwargs.append(dict(kwargs))
        return self.text, self.error, 0.012


def _command() -> dict:
    return {
        "schema": "AuraCommandEnvelopeV1-candidate",
        "queue_state": "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND",
        "message_authorized": True,
        "execution_authorized": True,
        "authority_ref": "owner-directive-current-1",
        "command_id": "cmd-minimal-001",
        "idempotency_key": "cmd-minimal-001",
        "received_at": "2026-08-22T10:00:00-05:00",
        "transport": {"type": "CHATGPT", "session_ref": "chat-session"},
        "caller": {
            "principal_ref": "owner-bound-chat",
            "model_signature": "visitor-model",
        },
        "objective": {
            "text": (
                "Inspect the bounded AuraOS seam and report the "
                "smallest safe next change."
            ),
            "target_ref": "tools/project006",
            "requested_effect": "D0",
            "positive_intent": [],
            "negative_intent": [],
            "success_criteria": [],
        },
        "constraints": {
            "workspace_scope": "AURA_DRIVE_ONLY",
            "source_refs": [],
            "authority_refs": [],
        },
        "requested_capability": {"semantic_id_or_alias": "optional"},
        "human_disposition": {"required": False},
    }


class DriveCommandExecutorHookTests(unittest.TestCase):
    def test_authorized_d0_emits_ack_before_one_executor_call_and_returns_result(
        self,
    ) -> None:
        events: list[str] = []
        executor = _FakeExecutor(events)
        acks: list[dict] = []

        result = execute_admitted_command(
            _command(),
            executor_factory=lambda: executor,
            emit_ack=lambda record: (
                events.append("ack"),
                acks.append(dict(record)),
            ),
        )

        self.assertEqual(events, ["ack", "generate"])
        self.assertEqual(len(acks), 1)
        self.assertEqual(acks[0]["record_type"], "ACK")
        self.assertEqual(acks[0]["command_id"], "cmd-minimal-001")
        self.assertEqual(result["record_type"], "RESULT")
        self.assertEqual(result["command_id"], "cmd-minimal-001")
        self.assertEqual(result["idempotency_key"], "cmd-minimal-001")
        self.assertEqual(result["executor_id"], EXECUTOR_ID)
        self.assertEqual(result["execution_identity"], "UNKNOWN")
        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["model"], "deepseek-test")
        self.assertEqual(result["result"], "bounded-result")
        self.assertIn(
            _command()["objective"]["text"], executor.prompts[0]
        )
        self.assertEqual(executor.kwargs[0]["temperature"], 0.0)
        self.assertFalse(executor.kwargs[0]["pre_egress"])
        self.assertFalse(executor.kwargs[0]["resonance_egress"])
        self.assertFalse(executor.kwargs[0]["context_crush"])

    def test_message_authorization_failure_never_constructs_executor(self) -> None:
        command = _command()
        command["message_authorized"] = False
        called = False

        def factory():
            nonlocal called
            called = True
            return _FakeExecutor([])

        with self.assertRaisesRegex(
            CommandHookError, "MESSAGE_NOT_AUTHORIZED"
        ):
            execute_admitted_command(command, executor_factory=factory)
        self.assertFalse(called)

    def test_execution_authorization_failure_never_constructs_executor(
        self,
    ) -> None:
        command = _command()
        command["execution_authorized"] = False
        with self.assertRaisesRegex(
            CommandHookError, "EXECUTION_NOT_AUTHORIZED"
        ):
            execute_admitted_command(
                command,
                executor_factory=lambda: self.fail("must not execute"),
            )

    def test_first_bridge_is_d0_only(self) -> None:
        command = _command()
        command["objective"]["requested_effect"] = "D1"
        with self.assertRaisesRegex(
            CommandHookError, "MINIMAL_BRIDGE_D0_ONLY"
        ):
            validate_admitted_command(command)

    def test_first_bridge_is_chatgpt_and_aura_drive_only(self) -> None:
        command = _command()
        command["transport"]["type"] = "CLI"
        with self.assertRaisesRegex(
            CommandHookError,
            "UNSUPPORTED_TRANSPORT_FOR_MINIMAL_BRIDGE",
        ):
            validate_admitted_command(command)

        command = _command()
        command["constraints"]["workspace_scope"] = "REPOSITORY_WRITE"
        with self.assertRaisesRegex(
            CommandHookError,
            "MINIMAL_BRIDGE_WORKSPACE_SCOPE_MISMATCH",
        ):
            validate_admitted_command(command)

    def test_human_gated_command_is_not_executed(self) -> None:
        command = _command()
        command["human_disposition"]["required"] = True
        with self.assertRaisesRegex(
            CommandHookError, "HUMAN_DISPOSITION_REQUIRED"
        ):
            validate_admitted_command(command)

    def test_structured_provider_control_injection_rejects(self) -> None:
        injections = {
            "provider_url": "https://evil.example/v1",
            "api_key": "secret",
            "route_ref": "attacker-route",
            "route": "attacker-route",
            "lease": "caller-lease",
            "fence": "caller-fence",
            "currentness": "caller-currentness",
            "fencing_token": "caller-fence",
            "model": "caller-model",
        }
        for field, value in injections.items():
            with self.subTest(field=field):
                command = _command()
                command["constraints"][field] = value
                with self.assertRaisesRegex(
                    CommandHookError,
                    "DRIVE_PROVIDER_CONTROL_FORBIDDEN",
                ):
                    validate_admitted_command(command)

    def test_original_canary_broad_external_denial_rejects_before_ack_or_executor(
        self,
    ) -> None:
        command = _command()
        command["objective"]["positive_intent"] = [
            "prove one bounded existing Aura/DeepSeek execution callback"
        ]
        command["objective"]["negative_intent"] = [
            "no repository mutation",
            "no external communication",
            "no credential disclosure",
            "no destructive action",
        ]
        events: list[str] = []

        with self.assertRaisesRegex(
            CommandHookError,
            "INTENT_CONTRADICTION_EXTERNAL_EGRESS_FORBIDDEN",
        ):
            execute_admitted_command(
                command,
                executor_factory=lambda: (
                    events.append("factory") or _FakeExecutor(events)
                ),
                emit_ack=lambda _record: events.append("ack"),
            )
        self.assertEqual(events, [])

    def test_narrow_unrelated_external_denial_allows_deepseek_egress(
        self,
    ) -> None:
        command = _command()
        command["objective"]["negative_intent"] = [
            "no unrelated external communication",
            "no repository mutation",
            "no credential disclosure",
        ]
        result = execute_admitted_command(
            command,
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["record_type"], "RESULT")

    def test_explicit_single_deepseek_exception_allows_broad_denial(
        self,
    ) -> None:
        command = _command()
        command["objective"]["negative_intent"] = [
            (
                "no external communication except the single "
                "current-owner-authorized DeepSeek provider egress "
                "required for this canary"
            )
        ]
        result = execute_admitted_command(
            command,
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["record_type"], "RESULT")

    def test_malformed_negative_intent_rejects(self) -> None:
        command = _command()
        command["objective"]["negative_intent"] = "no external communication"
        with self.assertRaisesRegex(
            CommandHookError, "INVALID_NEGATIVE_INTENT"
        ):
            validate_admitted_command(command)

    def test_model_signature_is_observational(self) -> None:
        command = _command()
        command["caller"]["model_signature"] = "attacker/provider-model"
        executor = _FakeExecutor([])
        result = execute_admitted_command(
            command,
            executor_factory=lambda: executor,
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["model"], "deepseek-test")

    def test_missing_ack_sink_prevents_executor_construction(self) -> None:
        called = False

        def factory():
            nonlocal called
            called = True
            return _FakeExecutor([])

        with self.assertRaisesRegex(CommandHookError, "ACK_SINK_REQUIRED"):
            execute_admitted_command(_command(), executor_factory=factory)
        self.assertFalse(called)

    def test_ack_sink_failure_prevents_executor_construction(self) -> None:
        called = False

        def factory():
            nonlocal called
            called = True
            return _FakeExecutor([])

        def bad_ack(_record):
            raise RuntimeError("writer failed with private internals")

        with self.assertRaisesRegex(CommandHookError, "ACK_EMIT_FAILED"):
            execute_admitted_command(
                _command(), executor_factory=factory, emit_ack=bad_ack
            )
        self.assertFalse(called)

    def test_provider_error_is_typed_and_raw_error_is_not_serialized(
        self,
    ) -> None:
        secret_error = "Authorization: Bearer sk-never-serialize"
        executor = _FakeExecutor([], text=None, error=secret_error)
        result = execute_admitted_command(
            _command(),
            executor_factory=lambda: executor,
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["record_type"], "ERROR")
        self.assertEqual(
            result["error_code"], "DEEPSEEK_EXECUTOR_FAILURE"
        )
        self.assertNotIn(secret_error, repr(result))
        self.assertNotIn("sk-never-serialize", repr(result))

    def test_executor_constructor_failure_is_typed_without_message(
        self,
    ) -> None:
        def factory():
            raise RuntimeError("secret path or provider detail")

        result = execute_admitted_command(
            _command(),
            executor_factory=factory,
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["record_type"], "ERROR")
        self.assertEqual(
            result["error_code"], "DEEPSEEK_EXECUTOR_UNAVAILABLE"
        )
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertNotIn("secret path", repr(result))

    def test_request_digest_binds_identity_objective_and_intent(self) -> None:
        first = execute_admitted_command(
            _command(),
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        second = execute_admitted_command(
            _command(),
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        self.assertEqual(
            first["execution_request_digest"],
            second["execution_request_digest"],
        )

        mutated = _command()
        mutated["objective"]["text"] += " Different objective."
        third = execute_admitted_command(
            mutated,
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        self.assertNotEqual(
            first["execution_request_digest"],
            third["execution_request_digest"],
        )

        mutated_id = _command()
        mutated_id["command_id"] = "cmd-minimal-002"
        mutated_id["idempotency_key"] = "cmd-minimal-002"
        fourth = execute_admitted_command(
            mutated_id,
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        self.assertNotEqual(
            first["execution_request_digest"],
            fourth["execution_request_digest"],
        )

        mutated_intent = _command()
        mutated_intent["objective"]["negative_intent"] = [
            "no unrelated external communication"
        ]
        fifth = execute_admitted_command(
            mutated_intent,
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        self.assertNotEqual(
            first["execution_request_digest"],
            fifth["execution_request_digest"],
        )

    def test_validation_and_execution_do_not_mutate_input(self) -> None:
        command = _command()
        original = copy.deepcopy(command)
        validate_admitted_command(command)
        execute_admitted_command(
            command,
            executor_factory=lambda: _FakeExecutor([]),
            emit_ack=lambda _record: None,
        )
        self.assertEqual(command, original)

    def test_empty_objective_rejects_before_executor(self) -> None:
        command = _command()
        command["objective"]["text"] = ""
        with self.assertRaisesRegex(
            CommandHookError, "INVALID_OBJECTIVE_TEXT"
        ):
            execute_admitted_command(
                command,
                executor_factory=lambda: self.fail("must not execute"),
            )


if __name__ == "__main__":
    unittest.main()
