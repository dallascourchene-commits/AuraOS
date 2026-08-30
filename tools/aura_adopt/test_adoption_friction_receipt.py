import unittest

import aura_adoption_bootstrap as bootstrap
from tools.aura_adopt.adoption_friction_receipt import (
    AcceptedValue,
    FRICTION_COMPONENTS,
    FrictionReceiptError,
    STAGES,
    StageEvent,
    StageStatus,
    bind_route_decision,
    build_friction_receipt,
    compare_receipts,
)


def source(generation="gen-1"):
    return bootstrap.SourceBindingV1(
        source_generation=generation,
        currentness_ref=f"currentness:{generation}",
        host_evidence_ref="fixture://host",
        host_evidence_digest="sha256:host-fixture",
    )


def compiler_receipt(generation="gen-1"):
    projection = bootstrap.BootstrapProjectionV1(
        source=source(generation),
        user_mode=bootstrap.UserMode.ORDINARY,
        platform_class=bootstrap.PlatformClass.WEB_ONLY,
        browser_available=True,
        native_install_available=False,
        cli_available=False,
        offline_required=False,
        background_required=False,
        local_compute_class=bootstrap.LocalComputeClass.CAPABLE,
        storage_class=bootstrap.StorageClass.NORMAL,
        network_state=bootstrap.NetworkState.ONLINE,
        free_remote_route_available=False,
        provider_credential_present=False,
        remote_execution_admission=bootstrap.RemoteExecutionAdmission.NOT_ADMITTED,
        desired_first_capability="creator-title-card",
    )
    return bootstrap.compile_entry_route(projection)


def native_compiler_receipt():
    projection = bootstrap.BootstrapProjectionV1(
        source=source(),
        user_mode=bootstrap.UserMode.ORDINARY,
        platform_class=bootstrap.PlatformClass.ANDROID,
        browser_available=False,
        native_install_available=True,
        cli_available=False,
        offline_required=True,
        background_required=True,
        local_compute_class=bootstrap.LocalComputeClass.CAPABLE,
        storage_class=bootstrap.StorageClass.NORMAL,
        network_state=bootstrap.NetworkState.OFFLINE,
        free_remote_route_available=False,
        provider_credential_present=False,
        remote_execution_admission=bootstrap.RemoteExecutionAdmission.NOT_ADMITTED,
        desired_first_capability="creator-camera",
    )
    return bootstrap.compile_entry_route(projection)


def decision(generation="gen-1"):
    return bind_route_decision(compiler_receipt(generation).logical())


def complete_events(
    *,
    clock_shift=0,
    blocked=None,
    account_na=True,
    key_na=True,
    install_na=True,
    permission_na=True,
    unknown_download_stage=None,
):
    blocked = blocked or {}
    events = []
    for idx, stage in enumerate(STAGES):
        clock = 1000 + idx + clock_shift
        if stage in blocked:
            events.append(
                StageEvent(
                    stage,
                    StageStatus.BLOCKED,
                    steps=1,
                    wall_time_ms=10,
                    downloaded_bytes=0,
                    retained_bytes=0,
                    monetary_cost_microunits=0,
                    reason="fixture blocker",
                    failure_code=blocked[stage],
                    observation_clock_ms=clock,
                )
            )
            continue
        if stage == "OPTIONAL_ACCOUNT" and account_na:
            events.append(
                StageEvent(
                    stage,
                    StageStatus.NOT_APPLICABLE,
                    reason="no account required",
                    observation_clock_ms=clock,
                )
            )
            continue
        if stage == "OPTIONAL_KEY" and key_na:
            events.append(
                StageEvent(
                    stage,
                    StageStatus.NOT_APPLICABLE,
                    reason="no key required",
                    observation_clock_ms=clock,
                )
            )
            continue
        if stage == "OPEN_INSTALL" and install_na:
            events.append(
                StageEvent(
                    stage,
                    StageStatus.NOT_APPLICABLE,
                    reason="zero-install route",
                    observation_clock_ms=clock,
                )
            )
            continue
        if stage == "PERMISSION" and permission_na:
            events.append(
                StageEvent(
                    stage,
                    StageStatus.NOT_APPLICABLE,
                    reason="no permission required",
                    observation_clock_ms=clock,
                )
            )
            continue
        events.append(
            StageEvent(
                stage,
                StageStatus.COMPLETED,
                steps=1,
                wall_time_ms=10,
                downloaded_bytes=None if stage == unknown_download_stage else 0,
                retained_bytes=0,
                monetary_cost_microunits=0,
                observation_clock_ms=clock,
            )
        )
    return tuple(events)


def vector(value=1.0):
    return {key: value for key in FRICTION_COMPONENTS}


def weights(value=1.0):
    return {key: value for key in FRICTION_COMPONENTS}


def default_cohort():
    return {
        "device_class": "browser-only",
        "skill_class": "nontechnical-creator",
        "connectivity_class": "normal",
    }


def make_receipt(
    *,
    route_decision=None,
    events=None,
    friction=None,
    mandatory_account=False,
    mandatory_key=False,
    permissions=(),
    starting_state=None,
    evidence_class="SYNTHETIC",
    privacy_mode="SYNTHETIC_NO_TELEMETRY",
    accepted_result=True,
    cohort=None,
    weight_map=None,
    weighting_method="fixture-equal-weights-only",
):
    return build_friction_receipt(
        route_decision or decision(),
        route_id="fixture-route",
        mission_head="AURA-ADOPT-001@fixture",
        build_refs=("sha:fixture",),
        cohort=cohort or default_cohort(),
        starting_state=starting_state or {
            "account_present": False,
            "app_installed": False,
        },
        stage_events=events or complete_events(),
        permissions=permissions,
        mandatory_account=mandatory_account,
        mandatory_key=mandatory_key,
        accepted_value=AcceptedValue(
            "deterministic useful output accepted",
            accepted_result,
            "fixture-verifier",
        ),
        friction_vector=friction or vector(),
        weights=weight_map or weights(),
        weighting_method=weighting_method,
        privacy_telemetry_mode=privacy_mode,
        invalidators=("route-source-change",),
        reopen_trigger="replay on source change",
        evidence_class=evidence_class,
    )


class AdoptionFrictionReceiptTests(unittest.TestCase):
    def test_compiler_receipt_binding_recomputes_exact_integrity_digest(self):
        receipt = compiler_receipt()
        bound = bind_route_decision(receipt.logical())
        self.assertEqual(receipt.digest, bound.compiler_receipt_digest)
        self.assertEqual("ZERO_INSTALL_WEB_PWA", bound.entry_surface)
        self.assertEqual("FULL_LOCAL", bound.compute_profile)
        self.assertFalse(bound.source_binding_authenticated)

    def test_compiler_authority_widening_fails_closed(self):
        raw = compiler_receipt().logical()
        raw["provider_call_made"] = True
        with self.assertRaises(FrictionReceiptError) as ctx:
            bind_route_decision(raw)
        self.assertEqual("COMPILER_EFFECT_AUTHORITY_WIDENING", ctx.exception.code)

    def test_compiler_shape_and_required_action_count_are_exact(self):
        raw = compiler_receipt().logical()
        raw["unexpected_future_semantics"] = False
        with self.assertRaises(FrictionReceiptError) as ctx:
            bind_route_decision(raw)
        self.assertEqual("COMPILER_RECEIPT_SHAPE_MISMATCH", ctx.exception.code)

        raw = compiler_receipt().logical()
        raw["friction"]["required_action_count"] += 1
        with self.assertRaises(FrictionReceiptError) as ctx:
            bind_route_decision(raw)
        self.assertEqual("COMPILER_REQUIRED_ACTION_COUNT_MISMATCH", ctx.exception.code)

    def test_complete_fixture_emits_canonical_schema_ready_receipt(self):
        receipt = make_receipt()
        self.assertEqual("AdoptionFrictionReceiptV1", receipt.schema)
        self.assertEqual(tuple(STAGES), tuple(e.stage for e in receipt.stage_events))
        self.assertTrue(receipt.logical_id.startswith("afr-"))
        self.assertIsInstance(receipt.total_steps, int)
        self.assertEqual(0, receipt.total_downloaded_bytes)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.execution_proven)
        serialized = receipt.to_dict()
        self.assertEqual(13, len(serialized["stage_events"]))
        self.assertNotIn("observation_clock_ms", serialized["stage_events"][0])
        self.assertEqual(False, serialized["decision"]["source_binding_authenticated"])

    def test_observation_clock_does_not_churn_logical_identity(self):
        a = make_receipt(events=complete_events(clock_shift=0))
        b = make_receipt(events=complete_events(clock_shift=999999))
        self.assertEqual(a.logical_id, b.logical_id)

    def test_compiler_source_generation_is_identity_bearing(self):
        a = make_receipt(route_decision=decision("gen-1"))
        b = make_receipt(route_decision=decision("gen-2"))
        self.assertNotEqual(
            a.decision.compiler_receipt_digest,
            b.decision.compiler_receipt_digest,
        )
        self.assertNotEqual(a.logical_id, b.logical_id)

    def test_missing_or_reordered_stage_fails(self):
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(events=complete_events()[:-1])
        self.assertEqual("CONSEQUENCE_STAGE_COVERAGE_INVALID", ctx.exception.code)
        reordered = list(complete_events())
        reordered[0], reordered[1] = reordered[1], reordered[0]
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(events=tuple(reordered))
        self.assertEqual("CONSEQUENCE_STAGE_COVERAGE_INVALID", ctx.exception.code)

    def test_noncompleted_stage_requires_reason_and_na_cannot_hide_work(self):
        for status in (
            StageStatus.NOT_APPLICABLE,
            StageStatus.UNKNOWN,
            StageStatus.BLOCKED,
        ):
            with self.assertRaises(FrictionReceiptError):
                StageEvent("TRUST", status)
        with self.assertRaises(FrictionReceiptError) as ctx:
            StageEvent(
                "OPTIONAL_KEY",
                StageStatus.NOT_APPLICABLE,
                steps=2,
                reason="incorrectly hidden work",
            )
        self.assertEqual("NOT_APPLICABLE_CONSEQUENCE_NONZERO", ctx.exception.code)

    def test_mandatory_account_and_key_cannot_be_hidden_as_na(self):
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(mandatory_account=True)
        self.assertEqual("MANDATORY_ACCOUNT_BURDEN_OMITTED", ctx.exception.code)
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(mandatory_key=True)
        self.assertEqual("MANDATORY_KEY_BURDEN_OMITTED", ctx.exception.code)

    def test_compiler_install_and_permission_actions_cannot_be_hidden(self):
        bound = bind_route_decision(native_compiler_receipt().logical())
        self.assertIn("INSTALL", " ".join(bound.required_actions))
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(route_decision=bound)
        self.assertEqual("INSTALL_BURDEN_OMITTED", ctx.exception.code)
        events = complete_events(install_na=False)
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(route_decision=bound, events=events)
        self.assertEqual("PERMISSION_BURDEN_OMITTED", ctx.exception.code)

    def test_accepted_value_true_requires_execution_and_verification(self):
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(
                events=complete_events(blocked={"EXECUTE": "RUNTIME_BLOCKED"})
            )
        self.assertEqual("ACCEPTED_VALUE_EXECUTION_NOT_COMPLETED", ctx.exception.code)
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(
                events=complete_events(blocked={"VERIFY_ACCEPT": "OUTPUT_REJECTED"})
            )
        self.assertEqual("ACCEPTED_VALUE_VERIFICATION_NOT_COMPLETED", ctx.exception.code)

    def test_unknown_friction_and_stage_metrics_never_become_zero(self):
        f = vector()
        f["storage_network"] = None
        receipt = make_receipt(
            friction=f,
            events=complete_events(unknown_download_stage="EXECUTE"),
        )
        self.assertIsNone(receipt.total_score)
        self.assertIsNone(receipt.total_downloaded_bytes)

    def test_private_starting_state_and_direct_identity_cohort_rejected(self):
        for state in (
            {"api_key": "x"},
            {"prompt": "private"},
            {"nested": {"email": "x@y"}},
        ):
            with self.assertRaises(FrictionReceiptError) as ctx:
                make_receipt(starting_state=state)
            self.assertEqual("PRIVATE_FIELD_FORBIDDEN", ctx.exception.code)
        with self.assertRaises(FrictionReceiptError) as ctx:
            build_friction_receipt(
                decision(),
                route_id="r",
                mission_head="m",
                build_refs=("b",),
                cohort={"email": "x@y"},
                starting_state={"account_present": False},
                stage_events=complete_events(),
                accepted_value=AcceptedValue("x", True, "fixture"),
                friction_vector=vector(),
                weights=weights(),
                weighting_method="fixture",
                reopen_trigger="source change",
            )
        self.assertEqual("COHORT_FIELD_NOT_PRIVACY_MINIMAL", ctx.exception.code)

    def test_comparison_preserves_failure_reasons_unknowns_and_burdens(self):
        baseline = make_receipt(
            events=complete_events(blocked={"TRUST": "UNTRUSTED_BINARY"}),
            friction=vector(2.0),
        )
        candidate_f = vector(1.0)
        candidate_f["storage_network"] = None
        candidate = make_receipt(
            events=complete_events(blocked={"VERIFY_ACCEPT": "OUTPUT_REJECTED"}),
            friction=candidate_f,
            accepted_result=False,
        )
        comparison = compare_receipts(baseline, candidate)
        self.assertIn(
            "TRUST:UNTRUSTED_BINARY", comparison.baseline_failure_signature
        )
        self.assertIn(
            "VERIFY_ACCEPT:OUTPUT_REJECTED", comparison.candidate_failure_signature
        )
        self.assertIn("storage_network", comparison.unresolved_components)
        self.assertIsNone(comparison.scalar_delta)
        self.assertTrue(comparison.comparable_without_scalar_collapse)

    def test_scalar_delta_requires_same_cohort_and_weighting_basis(self):
        baseline = make_receipt(friction=vector(2.0))
        candidate = make_receipt(friction=vector(1.0))
        self.assertEqual(-9.0, compare_receipts(baseline, candidate).scalar_delta)

        different_cohort = dict(default_cohort())
        different_cohort["skill_class"] = "expert-creator"
        candidate = make_receipt(friction=vector(1.0), cohort=different_cohort)
        self.assertIsNone(compare_receipts(baseline, candidate).scalar_delta)

        candidate = make_receipt(
            friction=vector(1.0),
            weight_map=weights(2.0),
            weighting_method="different-weights",
        )
        self.assertIsNone(compare_receipts(baseline, candidate).scalar_delta)

    def test_comparison_exposes_added_account_key_install_burdens(self):
        baseline = make_receipt()
        candidate = make_receipt(
            events=complete_events(
                account_na=False,
                key_na=False,
                install_na=False,
            ),
            mandatory_account=True,
            mandatory_key=True,
        )
        comparison = compare_receipts(baseline, candidate)
        self.assertIn("MANDATORY_ACCOUNT", comparison.added_burdens)
        self.assertIn("MANDATORY_KEY", comparison.added_burdens)
        self.assertIn("INSTALL", comparison.added_burdens)

    def test_consented_study_requires_explicit_consent_mode(self):
        with self.assertRaises(FrictionReceiptError) as ctx:
            make_receipt(
                evidence_class="CONSENTED_STUDY",
                privacy_mode="VISIBLE_TELEMETRY",
            )
        self.assertEqual("CONSENT_SCOPE_REQUIRED", ctx.exception.code)
        receipt = make_receipt(
            evidence_class="CONSENTED_STUDY",
            privacy_mode="EXPLICIT_CONSENT_VISIBLE_TELEMETRY",
        )
        self.assertEqual("CONSENTED_STUDY", receipt.evidence_class)


if __name__ == "__main__":
    unittest.main()
