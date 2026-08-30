import dataclasses
import unittest

from tools.aura_adopt import adoption_friction_receipt as afr
from tools.aura_adopt import first_value_witness_adapter as bridge


def decision(**overrides):
    values = dict(
        compiler_schema="AuraAdoptionBootstrapReceiptV1",
        compiler_receipt_digest="compiler-receipt-digest",
        projection_digest="projection-digest",
        source_binding_digest="source-binding-digest",
        source_binding_authenticated=False,
        disposition="READY_BOUNDED",
        entry_surface="ZERO_INSTALL_WEB_PWA",
        compute_profile="CONSTRAINED_LOCAL",
        first_use_capability="CREATOR_STUDIO",
        required_actions=("OPEN_AURA_WEB_ENTRY",),
        blockers=(),
        claim_ceiling="D0_ROUTE_DECISION_ONLY_NO_INSTALL_PERMISSION_PROVIDER_DEPLOYMENT_EFFECT",
    )
    values.update(overrides)
    return afr.RouteDecisionBinding(**values)


def observation(**overrides):
    values = dict(
        opened=True,
        input_selected=True,
        browser_capability_available=True,
        rendered=True,
        preview_shown=True,
        acceptance_mode=bridge.AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL,
        save_mode=bridge.SaveEvidenceMode.DOWNLOAD_INITIATED,
        trust_failed=False,
    )
    values.update(overrides)
    return bridge.FirstValueWitnessObservationV1(**values)


def compile_receipt(obs=None, dec=None, **kwargs):
    return bridge.compile_first_value_receipt(
        dec or decision(), obs or observation(),
        route_id="zf01-title-card-v1",
        mission_head="AURA-ADOPT-001@20260830",
        build_refs=(
            "PR354@bece539b94096ef54686d900165f11602839eb82",
            "PR355@89c8696097f7fa3cb51aae02a6088f30ad0fad98",
            "PR357@e5f9afed5b2d414f44289a2ca85b6fb469d30b43",
        ),
        cohort={"device_class": "CI_BROWSER", "skill_class": "UNKNOWN"},
        recipe_ref="arena-recipe:aura-adopt-zf01-title-card-v1@a95b233f",
        **kwargs,
    )


class FirstValueWitnessAdapterTests(unittest.TestCase):
    def stage(self, receipt, name):
        return next(event for event in receipt.stage_events if event.stage == name)

    def test_synthetic_technical_never_becomes_user_acceptance(self):
        receipt = compile_receipt()
        self.assertIsNone(receipt.accepted_value.result)
        self.assertEqual("SYNTHETIC_TECHNICAL", receipt.accepted_value.verifier)
        self.assertEqual(afr.StageStatus.UNKNOWN, self.stage(receipt, "VERIFY_ACCEPT").status)

    def test_download_initiated_never_proves_save_or_reopen(self):
        save = self.stage(compile_receipt(), "SAVE_REOPEN")
        self.assertEqual(afr.StageStatus.UNKNOWN, save.status)
        self.assertEqual("DOWNLOAD_INITIATED_DOES_NOT_PROVE_SAVE_OR_REOPEN", save.reason)

    def test_save_observed_still_does_not_prove_reopen(self):
        receipt = compile_receipt(observation(
            save_mode=bridge.SaveEvidenceMode.SAVE_OBSERVED,
            save_evidence_ref="evidence:save-01",
        ))
        self.assertEqual(afr.StageStatus.UNKNOWN, self.stage(receipt, "SAVE_REOPEN").status)

    def test_reopen_observed_can_complete_save_reopen(self):
        receipt = compile_receipt(observation(
            save_mode=bridge.SaveEvidenceMode.REOPEN_OBSERVED,
            save_evidence_ref="evidence:reopen-01",
        ))
        self.assertEqual(afr.StageStatus.COMPLETED, self.stage(receipt, "SAVE_REOPEN").status)

    def test_user_explicit_accept_is_true_only_with_bound_ref(self):
        receipt = compile_receipt(observation(
            acceptance_mode=bridge.AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT,
            acceptance_evidence_ref="evidence:accept-01",
        ))
        self.assertIs(receipt.accepted_value.result, True)
        self.assertTrue(receipt.accepted_value.verifier.startswith("USER_EXPLICIT_REF:"))
        self.assertEqual(afr.StageStatus.COMPLETED, self.stage(receipt, "VERIFY_ACCEPT").status)

    def test_user_explicit_reject_is_preserved(self):
        receipt = compile_receipt(observation(
            acceptance_mode=bridge.AcceptanceEvidenceMode.USER_EXPLICIT_REJECT,
            acceptance_evidence_ref="evidence:reject-01",
        ))
        self.assertIs(receipt.accepted_value.result, False)

    def test_user_acceptance_without_evidence_ref_fails_closed(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(acceptance_mode=bridge.AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT)
        self.assertEqual("USER_ACCEPTANCE_EVIDENCE_REF_REQUIRED", ctx.exception.code)

    def test_reopen_without_evidence_ref_fails_closed(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(save_mode=bridge.SaveEvidenceMode.REOPEN_OBSERVED)
        self.assertEqual("SAVE_EVIDENCE_REF_REQUIRED", ctx.exception.code)

    def test_trust_is_not_completable_by_pointer_presence(self):
        receipt = compile_receipt()
        trust = self.stage(receipt, "TRUST")
        self.assertEqual(afr.StageStatus.UNKNOWN, trust.status)
        self.assertEqual("TRUST_OWNER_EVIDENCE_NOT_BOUND_BY_WITNESS_ADAPTER", trust.reason)

    def test_failed_trust_is_a_typed_blocker(self):
        receipt = compile_receipt(observation(trust_failed=True))
        trust = self.stage(receipt, "TRUST")
        self.assertEqual(afr.StageStatus.BLOCKED, trust.status)
        self.assertEqual("TRUST_ADMISSION_FAILED", trust.failure_code)

    def test_missing_browser_capability_is_visible_not_guessed(self):
        obs = observation(rendered=False, preview_shown=False, browser_capability_available=False)
        receipt = compile_receipt(obs)
        resolve = self.stage(receipt, "CAPABILITY_RESOLVE")
        self.assertEqual(afr.StageStatus.BLOCKED, resolve.status)
        self.assertEqual("BROWSER_CAPABILITY_UNAVAILABLE", resolve.failure_code)

    def test_only_ready_zero_install_route_is_admitted(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            compile_receipt(dec=decision(entry_surface="NATIVE_ANDROID_APK"))
        self.assertEqual("ZERO_INSTALL_ROUTE_REQUIRED", ctx.exception.code)
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            compile_receipt(dec=decision(disposition="PARTIAL", blockers=("X",)))
        self.assertEqual("ROUTE_NOT_READY_FOR_FIRST_VALUE_WITNESS", ctx.exception.code)

    def test_adapter_uses_canonical_zf00_identity_and_full_stage_order(self):
        receipt = compile_receipt()
        self.assertTrue(receipt.logical_id.startswith("afr-"))
        self.assertEqual(afr.STAGES, tuple(event.stage for event in receipt.stage_events))
        self.assertEqual("AdoptionFrictionReceiptV1", receipt.schema)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.execution_proven)

    def test_render_requires_open(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(opened=False)
        self.assertEqual("RENDER_REQUIRES_OPENED_WITNESS", ctx.exception.code)

    def test_render_requires_input(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(input_selected=False)
        self.assertEqual("RENDER_REQUIRES_SELECTED_INPUT", ctx.exception.code)

    def test_render_requires_proven_browser_capability(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(browser_capability_available=None)
        self.assertEqual("RENDER_REQUIRES_BROWSER_CAPABILITY", ctx.exception.code)

    def test_preview_requires_render(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(rendered=False)
        self.assertEqual("PREVIEW_REQUIRES_RENDER", ctx.exception.code)

    def test_explicit_acceptance_requires_preview(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(
                rendered=True,
                preview_shown=False,
                acceptance_mode=bridge.AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT,
                acceptance_evidence_ref="evidence:accept-02",
                save_mode=bridge.SaveEvidenceMode.NONE,
            )
        self.assertEqual("USER_ACCEPTANCE_REQUIRES_PREVIEW", ctx.exception.code)

    def test_save_observation_requires_render(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(
                rendered=False, preview_shown=False,
                save_mode=bridge.SaveEvidenceMode.DOWNLOAD_INITIATED,
            )
        self.assertEqual("SAVE_OBSERVATION_REQUIRES_RENDER", ctx.exception.code)

    def test_share_reuse_requires_render_and_evidence(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(
                rendered=False, preview_shown=False,
                save_mode=bridge.SaveEvidenceMode.NONE,
                share_or_reuse_observed=True,
                share_or_reuse_evidence_ref="evidence:share-01",
            )
        self.assertEqual("SHARE_REUSE_REQUIRES_RENDER", ctx.exception.code)
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            observation(share_or_reuse_observed=True)
        self.assertEqual("SHARE_REUSE_EVIDENCE_REF_REQUIRED", ctx.exception.code)

    def test_evidence_refs_reject_whitespace_and_secret_like_values(self):
        for bad in ("user clicked yes", "sk-abc123", "token=abc"):
            with self.subTest(bad=bad):
                with self.assertRaises(afr.FrictionReceiptError):
                    observation(
                        acceptance_mode=bridge.AcceptanceEvidenceMode.USER_EXPLICIT_ACCEPT,
                        acceptance_evidence_ref=bad,
                    )

    def test_recipe_and_capability_refs_use_same_opaque_ref_membrane(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            compile_receipt(recipe_ref="raw user content here")
        self.assertEqual("RECIPE_REF_REQUIRED", ctx.exception.code)
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            compile_receipt(capability_refs=("token=abc",))
        self.assertEqual("CAPABILITY_REF_INVALID", ctx.exception.code)

    def test_observation_is_immutable(self):
        obs = observation()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            obs.rendered = False


if __name__ == "__main__":
    unittest.main()
