import unittest

from tools.aura_adopt import adoption_friction_receipt as afr
from tools.aura_adopt import first_value_witness_adapter as bridge

OUT = "a" * 64


def decision():
    return afr.RouteDecisionBinding(
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


def observation():
    return bridge.FirstValueWitnessObservationV1(
        opened=True,
        input_selected=True,
        browser_capability_available=True,
        rendered=True,
        preview_shown=True,
        acceptance_mode=bridge.AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL,
        output_artifact_sha256=OUT,
        evidence_source_generation="PR357@e5f9afed",
        evidence_currentness_ref="AURA-ADOPT-001@current",
        save_mode=bridge.SaveEvidenceMode.DOWNLOAD_INITIATED,
    )


def compile_receipt(**overrides):
    values = dict(
        route_id="zf01-title-card-v1",
        mission_head="AURA-ADOPT-001@20260830",
        build_refs=("PR354@bece539b", "PR355@89c86960", "PR357@e5f9afed"),
        cohort={"device_class": "CI_BROWSER", "skill_class": "UNKNOWN"},
        recipe_ref="arena-recipe:aura-adopt-zf01-title-card-v1@a95b233f",
        capability_refs=("capability:creator-canvas-v1",),
        evidence_class="LOCAL_TEST",
        privacy_telemetry_mode="LOCAL_NO_TELEMETRY",
    )
    values.update(overrides)
    return bridge.compile_first_value_receipt(decision(), observation(), **values)


class FirstValueWitnessScalarPrivacyTests(unittest.TestCase):
    def test_route_id_rejects_private_content(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            compile_receipt(route_id="alice@example.com")
        self.assertEqual("ROUTE_ID_NOT_PRIVACY_MINIMAL", ctx.exception.code)

    def test_mission_head_rejects_private_content(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            compile_receipt(mission_head="case-alice@example.com")
        self.assertEqual("MISSION_HEAD_NOT_PRIVACY_MINIMAL", ctx.exception.code)

    def test_privacy_telemetry_mode_is_closed_vocabulary(self):
        for value in ("LOCAL:user-alice@example.com", "LOCAL_WITH_TELEMETRY", "https://example.test/user=alice"):
            with self.subTest(value=value):
                with self.assertRaises(afr.FrictionReceiptError) as ctx:
                    compile_receipt(privacy_telemetry_mode=value)
                self.assertEqual("PRIVACY_TELEMETRY_MODE_NOT_ALLOWED", ctx.exception.code)

    def test_evidence_class_is_closed_vocabulary(self):
        with self.assertRaises(afr.FrictionReceiptError) as ctx:
            compile_receipt(evidence_class="study:alice@example.com")
        self.assertEqual("EVIDENCE_CLASS_NOT_ALLOWED", ctx.exception.code)

    def test_consented_study_mode_is_bounded_and_does_not_authenticate_consequence(self):
        receipt = compile_receipt(
            evidence_class="CONSENTED_STUDY",
            privacy_telemetry_mode="CONSENTED_STUDY_LOCAL_NO_CONTENT_UPLOAD",
        )
        verify_accept = next(event for event in receipt.stage_events if event.stage == "VERIFY_ACCEPT")
        save_reopen = next(event for event in receipt.stage_events if event.stage == "SAVE_REOPEN")
        self.assertEqual(afr.StageStatus.UNKNOWN, verify_accept.status)
        self.assertEqual(afr.StageStatus.UNKNOWN, save_reopen.status)
        self.assertIsNone(receipt.accepted_value.result)
        self.assertEqual("CONSENTED_STUDY_LOCAL_NO_CONTENT_UPLOAD", receipt.privacy_telemetry_mode)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.execution_proven)


if __name__ == "__main__":
    unittest.main()
