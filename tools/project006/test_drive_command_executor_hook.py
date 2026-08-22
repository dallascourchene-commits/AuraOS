from __future__ import annotations

import copy
import unittest

from tools.project006.drive_command_executor_hook import (
    CommandHookError,
    EFFECT_ADMISSION_VERSION,
    EFFECT_CLASS,
    EXECUTOR_ID,
    REQUIRED_CAPABILITY,
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
        "requested_capability": {
            "semantic_id_or_alias": REQUIRED_CAPABILITY
        },
        "human_disposition": {"required": False},
    }


def _allow_admission(events: list[str] | None = None, **overrides):
    def provider(command, digest, executor_id, effect_class):
        if events is not None:
            events.append("admission")
        receipt = {
            "admission_version": EFFECT_ADMISSION_VERSION,
            "command_digest": digest,
            "authority_ref": command["authority_ref"],
            "workspace_scope": command["workspace_scope"],
            "executor_id": executor_id,
            "effect_class": effect_class,
            "currentness": "CURRENT",
            "authority_decision": "ALLOW",
            "cost_decision": "ALLOW",
            "policy_ref": "drive-policy-current-1",
            "authority_admission_ref": "authority-admission-current-1",
            "provider_cost_admission_ref": "cost-admission-current-1",
        }
        receipt.update(overrides)
        return receipt

    return provider


class DriveCommandExecutorHookTests(unittest.TestCase):
    def test_authorized_d0_requires_admission_then_ack_then_one_executor_call(
        self,
    ) -> None:
        events: list[str] = []
        executor = _FakeExecutor(events)
        acks: list[dict] = []

        result = execute_admitted_command(
            _command(),
            executor_factory=lambda: executor,
            effect_admission=_allow_admission(events),
            emit_ack=lambda record: (
                events.append("ack"),
                acks.append(dict(record)),
            ),
        )

        self.assertEqual(events, ["admission", "ack", "generate"])
        self.assertEqual(len(acks), 1)
        self.assertEqual(acks[0]["record_type"], "ACK")
        self.assertEqual(acks[0]["command_id"], "cmd-minimal-001")
        self.assertEqual(result["record_type"], "RESULT")
        self.assertEqual(result["command_id"], "cmd-minimal-001")
        self.assertEqual(result["idempotency_key"], "cmd-minimal-001")
        self.assertEqual(result["executor_id"], EXECUTOR_ID)
        self.assertEqual(result["effect_class"], EFFECT_CLASS)
        self.assertEqual(result["execution_identity"], "UNKNOWN")
        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["model"], "deepseek-test")
        self.assertEqual(result["result"], "bounded-result")
        self.assertEqual(
            result["authority_admission_ref"],
            "authority-admission-current-1",
        )
        self.assertEqual(
            result["provider_cost_admission_ref"],
            "cost-admission-current-1",
        )
        self.assertIn(_command()["objective"]["text"], executor.prompts[0])

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

    def test_requested_capability_is_a_ceiling(self) -> None:
        command = _command()
        command["requested_capability"]["semantic_id_or_alias"] = "optional"
        with self.assertRaisesRegex(
            CommandHookError, "REQUESTED_CAPABILITY_MISMATCH"
        ):
            validate_admitted_command(command)

    def test_human_gated_command_is_not_executed(self) -> None:
        command = _command()
        command["human_disposition"]["required"] = True
        with self.assertRaisesRegex(
            CommandHookError, "HUMAN_DISPOSITION_REQUIRED"
        ):
            validate_admitted_command(command)

    def test_structured_provider_and_admission_control_injection_rejects(self) -> None:
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
            "authority_admission_ref": "caller-auth-admission",
            "provider_cost_admission_ref": "caller-cost-admission",
            "effect_admission": {"authority_decision": "ALLOW"},
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

    def test_original_canary_broad_external_denial_rejects_before_all_effect_gates(
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
                effect_admission=_allow_admission(events),
                emit_ack=lambda _record: events.append("ack"),
            )
        self.assertEqual(events, [])

    def test_narrow_external_denial_can_reach_host_admission_gate(self) -> None:
        command = _command()
        command["objective"]["negative_intent"] = [
            "no unrelated external communication",
            "no repository mutation",
            "no credential disclosure",
        ]
        result = execute_admitted_command(
            command,
            executor_factory=lambda: _FakeExecutor([]),
            effect_admission=_allow_admission(),
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["record_type"], "RESULT")

    def test_explicit_single_deepseek_exception_can_reach_host_admission_gate(
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
            effect_admission=_allow_admission(),
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
            effect_admission=_allow_admission(),
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["provider"], "deepseek")
        self.assertEqual(result["model"], "deepseek-test")

    def test_missing_ack_sink_prevents_admission_and_executor(self) -> None:
        events: list[str] = []
        with self.assertRaisesRegex(CommandHookError, "ACK_SINK_REQUIRED"):
            execute_admitted_command(
                _command(),
                executor_factory=lambda: (
                    events.append("factory") or _FakeExecutor(events)
                ),
                effect_admission=_allow_admission(events),
            )
        self.assertEqual(events, [])

    def test_missing_effect_admission_prevents_ack_and_executor(self) -> None:
        events: list[str] = []
        with self.assertRaisesRegex(
            CommandHookError, "EFFECT_ADMISSION_REQUIRED"
        ):
            execute_admitted_command(
                _command(),
                executor_factory=lambda: (
                    events.append("factory") or _FakeExecutor(events)
                ),
                emit_ack=lambda _record: events.append("ack"),
            )
        self.assertEqual(events, [])

    def test_authority_not_allow_prevents_ack_and_executor(self) -> None:
        events: list[str] = []
        with self.assertRaisesRegex(
            CommandHookError, "AUTHORITY_ADMISSION_NOT_ALLOW"
        ):
            execute_admitted_command(
                _command(),
                executor_factory=lambda: (
                    events.append("factory") or _FakeExecutor(events)
                ),
                effect_admission=_allow_admission(
                    events, authority_decision="BLOCKED"
                ),
                emit_ack=lambda _record: events.append("ack"),
            )
        self.assertEqual(events, ["admission"])

    def test_cost_unknown_prevents_ack_and_executor(self) -> None:
        events: list[str] = []
        with self.assertRaisesRegex(
            CommandHookError, "PROVIDER_COST_ADMISSION_NOT_ALLOW"
        ):
            execute_admitted_command(
                _command(),
                executor_factory=lambda: (
                    events.append("factory") or _FakeExecutor(events)
                ),
                effect_admission=_allow_admission(
                    events, cost_decision="UNKNOWN"
                ),
                emit_ack=lambda _record: events.append("ack"),
            )
        self.assertEqual(events, ["admission"])

    def test_stale_effect_admission_prevents_ack_and_executor(self) -> None:
        events: list[str] = []
        with self.assertRaisesRegex(
            CommandHookError, "EFFECT_ADMISSION_NOT_CURRENT"
        ):
            execute_admitted_command(
                _command(),
                executor_factory=lambda: (
                    events.append("factory") or _FakeExecutor(events)
                ),
                effect_admission=_allow_admission(
                    events, currentness="STALE"
                ),
                emit_ack=lambda _record: events.append("ack"),
            )
        self.assertEqual(events, ["admission"])

    def test_admission_binding_mismatch_prevents_ack_and_executor(self) -> None:
        for field, value in {
            "command_digest": "0" * 64,
            "executor_id": "other-executor",
            "effect_class": "OTHER_EFFECT",
            "workspace_scope": "OTHER_SCOPE",
            "authority_ref": "other-authority",
        }.items():
            with self.subTest(field=field):
                events: list[str] = []
                with self.assertRaisesRegex(
                    CommandHookError, "EFFECT_ADMISSION_BINDING_MISMATCH"
                ):
                    execute_admitted_command(
                        _command(),
                        executor_factory=lambda: (
                            events.append("factory") or _FakeExecutor(events)
                        ),
                        effect_admission=_allow_admission(
                            events, **{field: value}
                        ),
                        emit_ack=lambda _record: events.append("ack"),
                    )
                self.assertEqual(events, ["admission"])

    def test_admission_unknown_field_rejects_fail_closed(self) -> None:
        events: list[str] = []
        with self.assertRaisesRegex(
            CommandHookError, "EFFECT_ADMISSION_SHAPE_INVALID"
        ):
            execute_admitted_command(
                _command(),
                executor_factory=lambda: _FakeExecutor(events),
                effect_admission=_allow_admission(events, surprise="x"),
                emit_ack=lambda _record: events.append("ack"),
            )
        self.assertEqual(events, ["admission"])

    def test_ack_sink_failure_prevents_executor_construction(self) -> None:
        events: list[str] = []

        def bad_ack(_record):
            events.append("ack")
            raise RuntimeError("writer failed with private internals")

        with self.assertRaisesRegex(CommandHookError, "ACK_EMIT_FAILED"):
            execute_admitted_command(
                _command(),
                executor_factory=lambda: (
                    events.append("factory") or _FakeExecutor(events)
                ),
                effect_admission=_allow_admission(events),
                emit_ack=bad_ack,
            )
        self.assertEqual(events, ["admission", "ack"])

    def test_provider_error_is_typed_and_raw_error_is_not_serialized(
        self,
    ) -> None:
        secret_error = "Authorization: Bearer sk-never-serialize"
        executor = _FakeExecutor([], text=None, error=secret_error)
        result = execute_admitted_command(
            _command(),
            executor_factory=lambda: executor,
            effect_admission=_allow_admission(),
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
            effect_admission=_allow_admission(),
            emit_ack=lambda _record: None,
        )
        self.assertEqual(result["record_type"], "ERROR")
        self.assertEqual(
            result["error_code"], "DEEPSEEK_EXECUTOR_UNAVAILABLE"
        )
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertNotIn("secret path", repr(result))

    def test_request_digest_binds_identity_objective_intent_and_capability(self) -> None:
        def run(command):
            return execute_admitted_command(
                command,
                executor_factory=lambda: _FakeExecutor([]),
                effect_admission=_allow_admission(),
                emit_ack=lambda _record: None,
            )

        first = run(_command())
        second = run(_command())
        self.assertEqual(
            first["execution_request_digest"],
            second["execution_request_digest"],
        )

        mutated = _command()
        mutated["objective"]["text"] += " Different objective."
        self.assertNotEqual(
            first["execution_request_digest"],
            run(mutated)["execution_request_digest"],
        )

        mutated_id = _command()
        mutated_id["command_id"] = "cmd-minimal-002"
        mutated_id["idempotency_key"] = "cmd-minimal-002"
        self.assertNotEqual(
            first["execution_request_digest"],
            run(mutated_id)["execution_request_digest"],
        )

        mutated_intent = _command()
        mutated_intent["objective"]["negative_intent"] = [
            "no unrelated external communication"
        ]
        self.assertNotEqual(
            first["execution_request_digest"],
            run(mutated_intent)["execution_request_digest"],
        )

    def test_validation_and_execution_do_not_mutate_input(self) -> None:
        command = _command()
        original = copy.deepcopy(command)
        validate_admitted_command(command)
        execute_admitted_command(
            command,
            executor_factory=lambda: _FakeExecutor([]),
            effect_admission=_allow_admission(),
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
