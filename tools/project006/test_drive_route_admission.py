from __future__ import annotations

import unittest

from drive_route_admission import (
    DEFAULT_MODEL,
    PRO_MODEL,
    ROUTE_ADMISSION_SCHEMA,
    RouteAdmissionError,
    prepare_exact_executor,
    validate_effect_route_binding,
    validate_route_admission,
)


COMMAND_DIGEST = "a" * 64
EXECUTOR_ID = "AURA_CANONICAL_EGRESS_DEEPSEEK_D0_V1"
EFFECT_CLASS = "INTERNAL_DEEPSEEK_PROVIDER_INFERENCE_EGRESS"


def _route(**overrides):
    out = {
        "schema": ROUTE_ADMISSION_SCHEMA,
        "command_digest": COMMAND_DIGEST,
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


def _admission(**overrides):
    out = {
        "command_digest": COMMAND_DIGEST,
        "policy_ref": "policy-1",
        "authority_admission_ref": "authority-1",
        "provider_cost_admission_ref": "cost-1",
    }
    out.update(overrides)
    return out


class _Executor:
    def __init__(self, provider, model):
        self.provider = provider
        self.model = model
        self.generate_calls = 0

    def generate(self, *_args, **_kwargs):
        self.generate_calls += 1
        return "ok", None, 0.001


class RouteAdmissionTests(unittest.TestCase):
    def _validate(self, raw):
        return validate_route_admission(
            raw,
            command_digest=COMMAND_DIGEST,
            executor_id=EXECUTOR_ID,
            effect_class=EFFECT_CLASS,
            expected_provider="deepseek",
            expected_model=str(raw.get("model") or ""),
        )

    def test_standard_route_is_exact_flash(self):
        out = self._validate(_route())
        self.assertEqual(DEFAULT_MODEL, out["model"])
        self.assertEqual("NOT_REQUIRED", out["escalation_decision"])

    def test_missing_route_admission_fails_closed(self):
        with self.assertRaisesRegex(RouteAdmissionError, "ROUTE_ADMISSION_REQUIRED"):
            validate_route_admission(
                None,
                command_digest=COMMAND_DIGEST,
                executor_id=EXECUTOR_ID,
                effect_class=EFFECT_CLASS,
                expected_provider="deepseek",
                expected_model=DEFAULT_MODEL,
            )

    def test_retired_alias_fails_currentness_gate(self):
        with self.assertRaisesRegex(RouteAdmissionError, "EXPECTED_MODEL_RETIRED"):
            validate_route_admission(
                _route(model="deepseek-chat"),
                command_digest=COMMAND_DIGEST,
                executor_id=EXECUTOR_ID,
                effect_class=EFFECT_CLASS,
                expected_provider="deepseek",
                expected_model="deepseek-chat",
            )

    def test_non_escalated_pro_fails(self):
        with self.assertRaisesRegex(RouteAdmissionError, "PRO_ROUTE_CLASS_REQUIRED"):
            self._validate(_route(model=PRO_MODEL))

    def test_pro_requires_typed_allow_and_ref(self):
        with self.assertRaisesRegex(RouteAdmissionError, "PRO_ESCALATION_REQUIRED"):
            self._validate(
                _route(
                    model=PRO_MODEL,
                    route_class="pro",
                    escalation_decision="BLOCKED",
                    escalation_ref="escalation-1",
                )
            )
        with self.assertRaisesRegex(RouteAdmissionError, "PRO_ESCALATION_REF_REQUIRED"):
            self._validate(
                _route(
                    model=PRO_MODEL,
                    route_class="pro",
                    escalation_decision="ALLOW",
                    escalation_ref="NONE",
                )
            )
        out = self._validate(
            _route(
                model=PRO_MODEL,
                route_class="pro",
                escalation_decision="ALLOW",
                escalation_ref="earned-escalation-1",
            )
        )
        self.assertEqual(PRO_MODEL, out["model"])

    def test_route_is_bound_to_effect_admission_refs(self):
        route = self._validate(_route())
        validate_effect_route_binding(route, _admission())
        for field in (
            "command_digest",
            "policy_ref",
            "authority_admission_ref",
            "provider_cost_admission_ref",
        ):
            with self.subTest(field=field):
                bad = _admission(**{field: "wrong"})
                with self.assertRaisesRegex(
                    RouteAdmissionError, "ROUTE_EFFECT_ADMISSION_BINDING_MISMATCH"
                ):
                    validate_effect_route_binding(route, bad)

    def test_executor_provider_mismatch_is_pre_effect_failure(self):
        route = self._validate(_route())
        executor = _Executor("anthropic", DEFAULT_MODEL)
        with self.assertRaisesRegex(
            RouteAdmissionError, "EXECUTOR_PROVIDER_ROUTE_MISMATCH"
        ):
            prepare_exact_executor(route, factory=lambda _p, _m: executor)
        self.assertEqual(0, executor.generate_calls)

    def test_executor_model_mismatch_is_pre_effect_failure(self):
        route = self._validate(_route())
        executor = _Executor("deepseek", PRO_MODEL)
        with self.assertRaisesRegex(
            RouteAdmissionError, "EXECUTOR_MODEL_ROUTE_MISMATCH"
        ):
            prepare_exact_executor(route, factory=lambda _p, _m: executor)
        self.assertEqual(0, executor.generate_calls)

    def test_route_replay_after_command_mutation_fails(self):
        with self.assertRaisesRegex(RouteAdmissionError, "ROUTE_ADMISSION_COMMAND_MISMATCH"):
            validate_route_admission(
                _route(),
                command_digest="b" * 64,
                executor_id=EXECUTOR_ID,
                effect_class=EFFECT_CLASS,
                expected_provider="deepseek",
                expected_model=DEFAULT_MODEL,
            )


if __name__ == "__main__":
    unittest.main()
