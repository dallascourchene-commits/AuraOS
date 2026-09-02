import copy
import unittest

from drive_command_executor_hook import (
    CommandHookError,
    EFFECT_ADMISSION_VERSION,
    EFFECT_CLASS,
    EXECUTOR_ID,
    _canonical_digest,
    validate_admitted_command,
)
from drive_command_executor_integrity_adapter import (
    execute_integrity_checked_command,
    integrity_gate_result,
    validate_single_call_route,
)
from drive_route_admission import (
    DEFAULT_MODEL,
    PRO_MODEL,
    ROUTE_ADMISSION_SCHEMA,
)
from drive_swarm_fanout import (
    ROLE_SCHEMA,
    SWARM_SCHEMA,
    compile_role_distinct_children,
)


class _FakeExecutor:
    def __init__(self, events, provider="deepseek", model=DEFAULT_MODEL, text="Completed bounded analysis."):
        self.events = events
        self.provider = provider
        self.model = model
        self.text = text
        self.generate_calls = 0

    def generate(self, _prompt, **_kwargs):
        self.generate_calls += 1
        self.events.append("generate")
        return self.text, None, 0.003


def compiled_child():
    parent = {
        "schema": SWARM_SCHEMA,
        "parent_command_id": "parent",
        "parent_idempotency_key": "parent-idem",
        "target_size": 3,
        "base_command": {
            "schema": "AuraCommandEnvelopeV1-candidate",
            "command_id": "parent-base",
            "idempotency_key": "parent-base-idem",
            "authority_ref": "owner",
            "queue_state": "AUTHORIZED_FOR_DISPATCH_WHEN_OWNER_BOUND",
            "message_authorized": True,
            "execution_authorized": True,
            "transport": {"type": "CHATGPT"},
            "objective": {
                "text": "Investigate the bounded task.",
                "requested_effect": "D0",
                "positive_intent": [],
                "negative_intent": [],
                "success_criteria": [],
            },
            "constraints": {"workspace_scope": "AURA_DRIVE_ONLY"},
            "requested_capability": {
                "semantic_id_or_alias": "EXISTING_AURA_DEEPSEEK_EXECUTOR"
            },
        },
        "roles": [
            {"schema": ROLE_SCHEMA, "role_id": "A+", "worker_id": "W-A", "objective_suffix": "Construct."},
            {"schema": ROLE_SCHEMA, "role_id": "B-", "worker_id": "W-B", "objective_suffix": "Challenge."},
            {"schema": ROLE_SCHEMA, "role_id": "C0", "worker_id": "W-C", "objective_suffix": "Verify."},
        ],
    }
    return compile_role_distinct_children(parent)[0]


def expected_context(raw):
    return copy.deepcopy(raw["_host_child_context"])


def command_digest(raw):
    return _canonical_digest(validate_admitted_command(raw))


def route_admission(raw, **overrides):
    out = {
        "schema": ROUTE_ADMISSION_SCHEMA,
        "command_digest": command_digest(raw),
        "executor_id": EXECUTOR_ID,
        "effect_class": EFFECT_CLASS,
        "currentness": "CURRENT",
        "provider": "deepseek",
        "model": DEFAULT_MODEL,
        "route_class": "standard",
        "route_generation": "GEN25",
        "escalation_decision": "NOT_REQUIRED",
        "escalation_ref": "NONE",
        "policy_ref": "policy-1",
        "authority_admission_ref": "authority-1",
        "provider_cost_admission_ref": "cost-1",
    }
    out.update(overrides)
    return out


def effect_admission(events=None, **overrides):
    def provider(command, digest, executor_id, effect_class):
        if events is not None:
            events.append("admission")
        out = {
            "admission_version": EFFECT_ADMISSION_VERSION,
            "command_digest": digest,
            "authority_ref": command["authority_ref"],
            "workspace_scope": command["workspace_scope"],
            "executor_id": executor_id,
            "effect_class": effect_class,
            "currentness": "CURRENT",
            "authority_decision": "ALLOW",
            "cost_decision": "ALLOW",
            "policy_ref": "policy-1",
            "authority_admission_ref": "authority-1",
            "provider_cost_admission_ref": "cost-1",
        }
        out.update(overrides)
        return out
    return provider


class RouteGuardTests(unittest.TestCase):
    def test_parent_swarm_schema_fails_before_single_call(self):
        with self.assertRaisesRegex(CommandHookError, "PHYSICAL_SWARM_PARENT_REQUIRES_FANOUT_COORDINATOR"):
            validate_single_call_route({"schema": SWARM_SCHEMA})

    def test_top_level_target3_without_child_context_fails(self):
        with self.assertRaisesRegex(CommandHookError, "PHYSICAL_SWARM_PARENT_REQUIRES_FANOUT_COORDINATOR"):
            validate_single_call_route({"schema": "AuraCommandEnvelopeV1-candidate", "target_size": 3})

    def test_self_asserted_child_context_is_not_authority(self):
        with self.assertRaisesRegex(CommandHookError, "PHYSICAL_CHILD_EXPECTATION_REQUIRED"):
            validate_single_call_route(compiled_child())

    def test_child_context_must_match_host_expected_child(self):
        raw = compiled_child()
        expected = expected_context(raw)
        raw["_host_child_context"]["worker_id"] = "FORGED-WORKER"
        with self.assertRaisesRegex(CommandHookError, "PHYSICAL_CHILD_EXPECTATION_MISMATCH"):
            validate_single_call_route(raw, expected_child_context=expected)

    def test_child_context_requires_parent_payload_digest(self):
        raw = compiled_child()
        expected = expected_context(raw)
        del raw["_host_child_context"]["parent_payload_digest"]
        with self.assertRaisesRegex(CommandHookError, "PHYSICAL_CHILD_PAYLOAD_DIGEST_INVALID"):
            validate_single_call_route(raw, expected_child_context=expected)


class IntegrityGateTests(unittest.TestCase):
    def test_expected_model_is_mandatory(self):
        with self.assertRaisesRegex(CommandHookError, "EXPECTED_MODEL_REQUIRED"):
            integrity_gate_result(
                {"record_type": "RESULT", "provider": "deepseek", "model": DEFAULT_MODEL, "result": "ok"},
                expected_provider="deepseek",
                expected_model="",
            )

    def test_good_flash_transport_is_partial_not_success(self):
        out = integrity_gate_result(
            {"record_type": "RESULT", "status": "OK", "provider": "deepseek", "model": DEFAULT_MODEL, "result": "Completed bounded analysis."},
            expected_provider="deepseek",
            expected_model=DEFAULT_MODEL,
        )
        self.assertEqual("RESULT_PARTIAL", out["status"])
        self.assertEqual("EVIDENCE_REQUIRED", out["objective_adequacy"])
        self.assertFalse(out["reduction_allowed"])

    def test_missing_required_provider_is_quarantined(self):
        out = integrity_gate_result(
            {"record_type": "RESULT", "model": DEFAULT_MODEL, "result": "Completed."},
            expected_provider="deepseek",
            expected_model=DEFAULT_MODEL,
        )
        self.assertEqual("PROVIDER_IDENTITY_MISMATCH", out["status"])

    def test_missing_required_model_is_quarantined(self):
        out = integrity_gate_result(
            {"record_type": "RESULT", "provider": "deepseek", "result": "Completed."},
            expected_provider="deepseek",
            expected_model=DEFAULT_MODEL,
        )
        self.assertEqual("MODEL_IDENTITY_MISMATCH", out["status"])

    def test_refusal_is_quarantined(self):
        out = integrity_gate_result(
            {"record_type": "RESULT", "provider": "deepseek", "model": DEFAULT_MODEL, "result": "I cannot execute that work because I don't have access."},
            expected_provider="deepseek",
            expected_model=DEFAULT_MODEL,
        )
        self.assertEqual("MODEL_REFUSAL", out["status"])

    def test_deepseek_claude_contradiction_is_quarantined(self):
        out = integrity_gate_result(
            {"record_type": "RESULT", "provider": "deepseek", "model": DEFAULT_MODEL, "result": "I'm Claude, created by Anthropic, not DeepSeek."},
            expected_provider="deepseek",
            expected_model=DEFAULT_MODEL,
        )
        self.assertEqual("PROVIDER_IDENTITY_MISMATCH", out["status"])


class PreEffectRouteTests(unittest.TestCase):
    def test_exact_flash_order_is_admission_ack_attest_generate(self):
        raw = compiled_child()
        expected = expected_context(raw)
        events = []
        executor = _FakeExecutor(events)
        acks = []

        out = execute_integrity_checked_command(
            raw,
            expected_child_context=expected,
            route_admission=route_admission(raw),
            route_executor_factory=lambda provider, model: (events.append("factory") or executor),
            effect_admission=effect_admission(events),
            emit_ack=lambda record: (events.append("ack"), acks.append(dict(record))),
        )
        self.assertEqual(["admission", "ack", "factory", "generate"], events)
        self.assertEqual(1, executor.generate_calls)
        self.assertEqual(DEFAULT_MODEL, out["route_model"])
        self.assertEqual("RESULT_PARTIAL", out["status"])
        self.assertEqual("parent", out["parent_command_id"])
        self.assertEqual("A+", out["role_id"])
        self.assertFalse(out["physical_swarm_proven"])
        self.assertEqual(1, len(acks))

    def test_admitted_flash_executor_resolves_pro_zero_generate(self):
        raw = compiled_child()
        events = []
        executor = _FakeExecutor(events, model=PRO_MODEL)
        out = execute_integrity_checked_command(
            raw,
            expected_child_context=expected_context(raw),
            route_admission=route_admission(raw),
            route_executor_factory=lambda _p, _m: (events.append("factory") or executor),
            effect_admission=effect_admission(events),
            emit_ack=lambda _r: events.append("ack"),
        )
        self.assertEqual(["admission", "ack", "factory"], events)
        self.assertEqual(0, executor.generate_calls)
        self.assertEqual("EXECUTOR_UNAVAILABLE", out["status"])
        self.assertEqual("DEEPSEEK_EXECUTOR_UNAVAILABLE", out["error_code"])

    def test_wrong_provider_zero_generate(self):
        raw = compiled_child()
        events = []
        executor = _FakeExecutor(events, provider="anthropic")
        out = execute_integrity_checked_command(
            raw,
            expected_child_context=expected_context(raw),
            route_admission=route_admission(raw),
            route_executor_factory=lambda _p, _m: (events.append("factory") or executor),
            effect_admission=effect_admission(events),
            emit_ack=lambda _r: events.append("ack"),
        )
        self.assertEqual(["admission", "ack", "factory"], events)
        self.assertEqual(0, executor.generate_calls)
        self.assertEqual("EXECUTOR_UNAVAILABLE", out["status"])

    def test_pro_without_escalation_fails_before_admission_ack_factory_or_generate(self):
        raw = compiled_child()
        events = []
        with self.assertRaisesRegex(CommandHookError, "PRO_ROUTE_CLASS_REQUIRED"):
            execute_integrity_checked_command(
                raw,
                expected_child_context=expected_context(raw),
                route_admission=route_admission(raw, model=PRO_MODEL),
                route_executor_factory=lambda _p, _m: events.append("factory"),
                effect_admission=effect_admission(events),
                emit_ack=lambda _r: events.append("ack"),
            )
        self.assertEqual([], events)

    def test_retired_alias_fails_before_effect(self):
        raw = compiled_child()
        events = []
        with self.assertRaisesRegex(CommandHookError, "EXPECTED_MODEL_RETIRED"):
            execute_integrity_checked_command(
                raw,
                expected_child_context=expected_context(raw),
                route_admission=route_admission(raw, model="deepseek-chat"),
                effect_admission=effect_admission(events),
                emit_ack=lambda _r: events.append("ack"),
            )
        self.assertEqual([], events)

    def test_effect_route_ref_mismatch_fails_before_ack_factory_generate(self):
        raw = compiled_child()
        events = []
        with self.assertRaisesRegex(CommandHookError, "ROUTE_EFFECT_ADMISSION_BINDING_MISMATCH"):
            execute_integrity_checked_command(
                raw,
                expected_child_context=expected_context(raw),
                route_admission=route_admission(raw),
                effect_admission=effect_admission(events, policy_ref="other-policy"),
                emit_ack=lambda _r: events.append("ack"),
            )
        self.assertEqual(["admission"], events)

    def test_replay_after_command_mutation_fails_before_effect(self):
        raw = compiled_child()
        route = route_admission(raw)
        raw["objective"]["text"] += " Mutated."
        events = []
        with self.assertRaisesRegex(CommandHookError, "ROUTE_ADMISSION_COMMAND_MISMATCH"):
            execute_integrity_checked_command(
                raw,
                expected_child_context=expected_context(raw),
                route_admission=route,
                effect_admission=effect_admission(events),
                emit_ack=lambda _r: events.append("ack"),
            )
        self.assertEqual([], events)


if __name__ == "__main__":
    unittest.main()
