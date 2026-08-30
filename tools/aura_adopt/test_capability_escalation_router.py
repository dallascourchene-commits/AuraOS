import unittest

from tools.aura_adopt.capability_escalation_router import (
    Availability,
    CandidateRouteEvidenceV1,
    CapabilityResidualV1,
    CostClass,
    CredentialRequirement,
    EscalationDisposition,
    ExecutionLocation,
    Materialization,
    RemoteAdmission,
    ResidualKind,
    RouterCurrentnessV1,
    RouterError,
    compile_capability_escalation,
)


PLAN = {
    "schema": "ArenaRecipePlanV1",
    "plan_digest": "a" * 64,
    "capability_refs": ["creator.caption.reason"],
    "status": "READY_FOR_ADMISSION",
    "blockers": [],
    "effect_authorized": False,
    "execution_proven": False,
    "publication_authorized": False,
    "payment_authorized": False,
}

CURRENT = RouterCurrentnessV1(
    "src-cur-1", "models-cur-1", "providers-cur-1", "rates-cur-1"
)


def residual(**kwargs):
    values = dict(
        residual_id="residual.caption.reason",
        recipe_plan_digest="a" * 64,
        capability_ref="creator.caption.reason",
        residual_kind=ResidualKind.MODEL_INFERENCE_REQUIRED,
        unresolved=True,
        source_generation="g1",
        source_currentness_ref="src-cur-1",
        minimum_context_tokens=4096,
    )
    values.update(kwargs)
    return CapabilityResidualV1(**values)


def local_present(route="local.included", **kwargs):
    values = dict(
        route_id=route,
        model_ref="model.local.small",
        capability_refs=("creator.caption.reason",),
        execution_location=ExecutionLocation.LOCAL,
        materialization=Materialization.PRESENT,
        availability=Availability.PROVEN_AVAILABLE,
        cost_class=CostClass.INCLUDED,
        credential_requirement=CredentialRequirement.NONE,
        remote_admission=RemoteAdmission.NOT_APPLICABLE,
        source_generation="mg1",
        model_currentness_ref="models-cur-1",
        context_window_tokens=8192,
    )
    values.update(kwargs)
    return CandidateRouteEvidenceV1(**values)


def local_download(**kwargs):
    values = dict(
        route_id="local.download",
        model_ref="model.local.large",
        capability_refs=("creator.caption.reason",),
        execution_location=ExecutionLocation.LOCAL,
        materialization=Materialization.DOWNLOAD_REQUIRED,
        availability=Availability.PROVEN_AVAILABLE,
        cost_class=CostClass.INCLUDED,
        credential_requirement=CredentialRequirement.NONE,
        remote_admission=RemoteAdmission.NOT_APPLICABLE,
        source_generation="mg1",
        model_currentness_ref="models-cur-1",
        context_window_tokens=32768,
        download_bytes=5_000_000_000,
    )
    values.update(kwargs)
    return CandidateRouteEvidenceV1(**values)


def remote_free(**kwargs):
    values = dict(
        route_id="remote.free",
        model_ref="provider:model-free",
        capability_refs=("creator.caption.reason",),
        execution_location=ExecutionLocation.REMOTE,
        materialization=Materialization.REMOTE_SERVICE,
        availability=Availability.PROVEN_AVAILABLE,
        cost_class=CostClass.FREE_BOUNDED,
        credential_requirement=CredentialRequirement.NONE,
        remote_admission=RemoteAdmission.ADMITTED_BOUNDED,
        source_generation="pg1",
        model_currentness_ref="models-cur-1",
        context_window_tokens=32768,
        provider_ref="provider.free",
        provider_currentness_ref="providers-cur-1",
        rate_currentness_ref="rates-cur-1",
        free_evidence_ref="ratecard:free:bounded:1",
        rate_limit_evidence_ref="ratelimit:free:bounded:1",
    )
    values.update(kwargs)
    return CandidateRouteEvidenceV1(**values)


def remote_paid(**kwargs):
    values = dict(
        route_id="remote.paid",
        model_ref="provider:model-paid",
        capability_refs=("creator.caption.reason",),
        execution_location=ExecutionLocation.REMOTE,
        materialization=Materialization.REMOTE_SERVICE,
        availability=Availability.PROVEN_AVAILABLE,
        cost_class=CostClass.PAID,
        credential_requirement=CredentialRequirement.BYOK,
        remote_admission=RemoteAdmission.ADMITTED_BOUNDED,
        source_generation="pg1",
        model_currentness_ref="models-cur-1",
        context_window_tokens=131072,
        provider_ref="provider.paid",
        provider_currentness_ref="providers-cur-1",
        rate_currentness_ref="rates-cur-1",
    )
    values.update(kwargs)
    return CandidateRouteEvidenceV1(**values)


class CapabilityEscalationRouterTests(unittest.TestCase):
    def test_startup_without_residual_never_prompts(self):
        decision = compile_capability_escalation(
            PLAN, residual(unresolved=False), [remote_paid()], currentness=CURRENT
        )
        self.assertEqual(decision.disposition, EscalationDisposition.NO_ESCALATION_REQUIRED)
        self.assertEqual(decision.earned_action_classes, ())
        self.assertFalse(decision.credential_prompt_performed)
        self.assertFalse(decision.model_download_started)

    def test_non_model_residual_never_prompts(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(residual_kind=ResidualKind.NON_MODEL_RESIDUAL),
            [remote_paid()],
            currentness=CURRENT,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.NO_ESCALATION_REQUIRED)

    def test_local_present_auto_ready_no_effect(self):
        decision = compile_capability_escalation(
            PLAN, residual(), [local_present(), remote_paid()], currentness=CURRENT
        )
        self.assertEqual(decision.disposition, EscalationDisposition.LOCAL_ROUTE_READY)
        self.assertEqual(decision.selected_route_id, "local.included")
        local = next(option for option in decision.options if option.route_id == "local.included")
        self.assertEqual(local.required_actions, ())
        self.assertFalse(decision.provider_call_made)

    def test_download_consent_only_after_model_residual(self):
        decision = compile_capability_escalation(
            PLAN, residual(), [local_download()], currentness=CURRENT
        )
        self.assertEqual(decision.disposition, EscalationDisposition.USER_CHOICE_REQUIRED)
        self.assertIn("EXPLICIT_MODEL_DOWNLOAD_CONSENT", decision.earned_action_classes)

    def test_remote_free_requires_remote_consent_but_no_payment(self):
        decision = compile_capability_escalation(
            PLAN, residual(), [remote_free()], currentness=CURRENT
        )
        self.assertEqual(decision.disposition, EscalationDisposition.USER_CHOICE_REQUIRED)
        option = decision.options[0]
        self.assertIn("EXPLICIT_REMOTE_EXECUTION_CONSENT", option.required_actions)
        self.assertNotIn("EXPLICIT_PAYMENT_CONSENT", option.required_actions)
        self.assertNotIn("REQUEST_CREDENTIAL_VIA_SECURE_OWNER", option.required_actions)

    def test_remote_byok_key_prompt_is_only_earned_not_performed(self):
        decision = compile_capability_escalation(
            PLAN, residual(), [remote_paid()], currentness=CURRENT
        )
        self.assertIn("REQUEST_CREDENTIAL_VIA_SECURE_OWNER", decision.earned_action_classes)
        self.assertIn("EXPLICIT_PAYMENT_CONSENT", decision.earned_action_classes)
        self.assertFalse(decision.credential_prompt_performed)
        self.assertFalse(decision.payment_performed)

    def test_free_rate_currentness_mismatch_not_offered(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(),
            [remote_free(rate_currentness_ref="rates-old")],
            currentness=CURRENT,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.EVIDENCE_REQUIRED)
        self.assertIn("remote.free:RATE_CURRENTNESS_STALE", decision.blockers)

    def test_unknown_cost_is_not_called_free_or_offered(self):
        candidate = remote_free(
            cost_class=CostClass.UNKNOWN,
            free_evidence_ref="",
            rate_limit_evidence_ref="",
        )
        decision = compile_capability_escalation(
            PLAN, residual(), [candidate], currentness=CURRENT
        )
        self.assertEqual(decision.disposition, EscalationDisposition.EVIDENCE_REQUIRED)
        self.assertIn("remote.free:COST_CLASSIFICATION_UNKNOWN", decision.blockers)

    def test_remote_not_admitted_not_offered(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(),
            [remote_free(remote_admission=RemoteAdmission.NOT_ADMITTED)],
            currentness=CURRENT,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.EVIDENCE_REQUIRED)
        self.assertIn("remote.free:REMOTE_NOT_ADMITTED", decision.blockers)

    def test_stale_model_not_offered(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(),
            [local_present(model_currentness_ref="models-old")],
            currentness=CURRENT,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.EVIDENCE_REQUIRED)
        self.assertIn("local.included:MODEL_CURRENTNESS_STALE", decision.blockers)

    def test_context_insufficient_not_offered(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(minimum_context_tokens=16384),
            [local_present()],
            currentness=CURRENT,
        )
        self.assertIn("local.included:CONTEXT_WINDOW_INSUFFICIENT", decision.blockers)

    def test_residual_currentness_stale_blocks_before_options(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(source_currentness_ref="src-old"),
            [local_present()],
            currentness=CURRENT,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.EVIDENCE_REQUIRED)
        self.assertEqual(decision.options, ())
        self.assertIn("RESIDUAL_SOURCE_CURRENTNESS_STALE", decision.blockers)

    def test_upstream_recipe_plan_blocked_means_no_model_prompt(self):
        plan = dict(PLAN, status="BINDING_EVIDENCE_REQUIRED", blockers=["MISSING_BINDING:x"])
        decision = compile_capability_escalation(
            plan, residual(), [remote_paid()], currentness=CURRENT
        )
        self.assertEqual(decision.disposition, EscalationDisposition.UPSTREAM_BLOCKED)
        self.assertEqual(decision.earned_action_classes, ())

    def test_plan_digest_mismatch_refused(self):
        with self.assertRaisesRegex(RouterError, "RESIDUAL_PLAN_DIGEST_MISMATCH"):
            compile_capability_escalation(
                PLAN,
                residual(recipe_plan_digest="b" * 64),
                [local_present()],
                currentness=CURRENT,
            )

    def test_capability_not_in_plan_refused(self):
        with self.assertRaisesRegex(RouterError, "RESIDUAL_CAPABILITY_NOT_IN_PLAN"):
            compile_capability_escalation(
                PLAN,
                residual(capability_ref="other.cap"),
                [local_present()],
                currentness=CURRENT,
            )

    def test_remote_provider_currentness_stale(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(),
            [remote_paid(provider_currentness_ref="providers-old")],
            currentness=CURRENT,
        )
        self.assertIn("remote.paid:PROVIDER_CURRENTNESS_STALE", decision.blockers)

    def test_deterministic_options(self):
        one = compile_capability_escalation(
            PLAN,
            residual(),
            [remote_paid(), local_download(), remote_free()],
            currentness=CURRENT,
        )
        two = compile_capability_escalation(
            PLAN,
            residual(),
            [remote_free(), remote_paid(), local_download()],
            currentness=CURRENT,
        )
        self.assertEqual(
            [option.route_id for option in one.options],
            [option.route_id for option in two.options],
        )
        self.assertEqual(one.decision_digest, two.decision_digest)

    def test_unknown_availability_not_assumed_available(self):
        decision = compile_capability_escalation(
            PLAN,
            residual(),
            [local_present(availability=Availability.UNKNOWN)],
            currentness=CURRENT,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.EVIDENCE_REQUIRED)
        self.assertIn("local.included:AVAILABILITY_UNKNOWN", decision.blockers)


if __name__ == "__main__":
    unittest.main()
