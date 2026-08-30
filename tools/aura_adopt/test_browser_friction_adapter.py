import unittest

from tools.aura_adopt.adoption_friction_receipt import (
    FRICTION_COMPONENTS,
    RouteDecisionBinding,
    StageStatus,
)
from tools.aura_adopt.browser_friction_adapter import (
    AcceptanceEvidenceMode,
    BrowserAdapterError,
    BrowserWitnessObservationV1,
    PersistenceEvidenceMode,
    build_browser_friction_receipt,
    project_browser_observation,
)


BUILD = "github:pr357@e5f9afed5b2d414f44289a2ca85b6fb469d30b43"
RECIPE = "recipe:aura-adopt-zf01-title-card-v1@a95b233ff6019fa6a32cc72715c2ba528b80d7d97258e8e6087948d426d3449d"


def decision(surface="ZERO_INSTALL_WEB_PWA"):
    return RouteDecisionBinding(
        compiler_schema="AuraAdoptionBootstrapReceiptV1",
        compiler_receipt_digest="c" * 64,
        projection_digest="p" * 64,
        source_binding_digest="s" * 64,
        source_binding_authenticated=False,
        disposition="ROUTE_READY",
        entry_surface=surface,
        compute_profile="CONSTRAINED_LOCAL",
        first_use_capability="CREATOR_STUDIO",
        required_actions=(),
        blockers=(),
        claim_ceiling="decision only; no effect authority",
    )


def observation(**kwargs):
    values = dict(
        route_id="zf01a-local-image-title-card",
        build_ref=BUILD,
        recipe_ref=RECIPE,
        browser_opened=True,
        trust_binding_current=True,
        capability_supported=True,
        input_observed=True,
        render_observed=True,
        output_bytes=1234,
        acceptance_mode=AcceptanceEvidenceMode.USER_EXPLICIT,
        acceptance_evidence_ref="browser:event:user-check-1",
        persistence_mode=PersistenceEvidenceMode.REOPEN_OBSERVED,
        persistence_evidence_ref="browser:save-readback-reopen-1",
    )
    values.update(kwargs)
    return BrowserWitnessObservationV1(**values)


def event(projection, stage):
    return next(item for item in projection.stage_events if item.stage == stage)


def unknown_vector():
    return {name: None for name in FRICTION_COMPONENTS}


def weights():
    return {name: 1.0 for name in FRICTION_COMPONENTS}


def build(obs, vector=None, route_decision=None):
    return build_browser_friction_receipt(
        route_decision or decision(),
        obs,
        mission_head="aura-adopt-001:current",
        cohort={"device_class": "desktop-browser"},
        starting_state={"route": "browser", "account": "NONE", "key": "NONE"},
        friction_vector=vector or unknown_vector(),
        weights=weights(),
        weighting_method="UNKNOWN_EMPIRICAL_WEIGHTS_REFERENCE_ONLY",
        reopen_trigger="browser/build/receipt ABI changes",
        invalidators=("PR357_HEAD_CHANGE", "PR355_ABI_CHANGE"),
    )


class BrowserFrictionAdapterTests(unittest.TestCase):
    def test_user_explicit_acceptance_and_reopen_observed_complete_exact_stages(self):
        p = project_browser_observation(observation())
        self.assertEqual(event(p, "VERIFY_ACCEPT").status, StageStatus.COMPLETED)
        self.assertEqual(event(p, "SAVE_REOPEN").status, StageStatus.COMPLETED)
        self.assertTrue(p.accepted_value.result)
        self.assertTrue(p.accepted_value.verifier.startswith("USER_EXPLICIT:"))
        self.assertFalse(p.effect_authorized)
        self.assertFalse(p.execution_proven)

    def test_synthetic_technical_success_cannot_become_user_acceptance(self):
        p = project_browser_observation(
            observation(
                acceptance_mode=AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL,
                acceptance_evidence_ref="",
            )
        )
        self.assertEqual(event(p, "VERIFY_ACCEPT").status, StageStatus.UNKNOWN)
        self.assertIsNone(p.accepted_value.result)
        self.assertIn("SYNTHETIC_TECHNICAL", p.accepted_value.verifier)

    def test_download_initiated_is_not_reopen_proof(self):
        p = project_browser_observation(
            observation(
                persistence_mode=PersistenceEvidenceMode.DOWNLOAD_INITIATED,
                persistence_evidence_ref="browser:download-click-1",
            )
        )
        save = event(p, "SAVE_REOPEN")
        self.assertEqual(save.status, StageStatus.UNKNOWN)
        self.assertIn("reopen not observed", save.reason)

    def test_simulated_save_is_unknown_not_complete(self):
        p = project_browser_observation(
            observation(
                persistence_mode=PersistenceEvidenceMode.SIMULATED,
                persistence_evidence_ref="",
            )
        )
        self.assertEqual(event(p, "SAVE_REOPEN").status, StageStatus.UNKNOWN)
        self.assertIn("simulated", event(p, "SAVE_REOPEN").reason)

    def test_user_rejection_is_blocked_and_false(self):
        p = project_browser_observation(
            observation(
                acceptance_mode=AcceptanceEvidenceMode.USER_REJECTED,
                acceptance_evidence_ref="browser:event:user-reject-1",
            )
        )
        verify = event(p, "VERIFY_ACCEPT")
        self.assertEqual(verify.status, StageStatus.BLOCKED)
        self.assertEqual(verify.failure_code, "VALUE_NOT_ACCEPTED")
        self.assertFalse(p.accepted_value.result)

    def test_user_acceptance_requires_typed_evidence_ref(self):
        with self.assertRaisesRegex(BrowserAdapterError, "USER_ACCEPTANCE_EVIDENCE_REQUIRED"):
            observation(acceptance_evidence_ref="")

    def test_evidence_refs_must_be_opaque_compact_refs_not_prose(self):
        with self.assertRaisesRegex(BrowserAdapterError, "ACCEPTANCE_EVIDENCE_REF_INVALID"):
            observation(acceptance_evidence_ref="the user said yes in a long sentence")

    def test_observed_persistence_requires_evidence_ref(self):
        with self.assertRaisesRegex(BrowserAdapterError, "PERSISTENCE_EVIDENCE_REQUIRED"):
            observation(persistence_evidence_ref="")

    def test_render_success_requires_output_size_evidence(self):
        with self.assertRaisesRegex(BrowserAdapterError, "RENDER_OUTPUT_BYTES_REQUIRED"):
            observation(output_bytes=None)

    def test_output_bytes_without_render_are_refused(self):
        with self.assertRaisesRegex(BrowserAdapterError, "OUTPUT_BYTES_WITHOUT_RENDER"):
            observation(
                render_observed=False,
                output_bytes=1234,
                acceptance_mode=AcceptanceEvidenceMode.UNKNOWN,
                acceptance_evidence_ref="",
                persistence_mode=PersistenceEvidenceMode.UNKNOWN,
                persistence_evidence_ref="",
            )

    def test_acceptance_cannot_exist_without_render(self):
        with self.assertRaisesRegex(BrowserAdapterError, "ACCEPTANCE_WITHOUT_RENDER"):
            observation(
                render_observed=False,
                output_bytes=None,
                acceptance_mode=AcceptanceEvidenceMode.USER_EXPLICIT,
                persistence_mode=PersistenceEvidenceMode.UNKNOWN,
                persistence_evidence_ref="",
            )

    def test_persistence_cannot_exist_without_render(self):
        with self.assertRaisesRegex(BrowserAdapterError, "PERSISTENCE_WITHOUT_RENDER"):
            observation(
                render_observed=False,
                output_bytes=None,
                acceptance_mode=AcceptanceEvidenceMode.UNKNOWN,
                acceptance_evidence_ref="",
                persistence_mode=PersistenceEvidenceMode.DOWNLOAD_INITIATED,
                persistence_evidence_ref="browser:download-click-1",
            )

    def test_render_requires_browser_capability_and_input_causal_chain(self):
        with self.assertRaisesRegex(BrowserAdapterError, "RENDER_CAUSAL_CHAIN_INVALID"):
            observation(capability_supported=False)

    def test_missing_capability_becomes_canonical_blocked_stage(self):
        p = project_browser_observation(
            observation(
                capability_supported=False,
                browser_failure_code="CANVAS_2D_UNAVAILABLE",
                render_observed=False,
                output_bytes=None,
                acceptance_mode=AcceptanceEvidenceMode.UNKNOWN,
                acceptance_evidence_ref="",
                persistence_mode=PersistenceEvidenceMode.UNKNOWN,
                persistence_evidence_ref="",
            )
        )
        cap = event(p, "CAPABILITY_RESOLVE")
        self.assertEqual(cap.status, StageStatus.BLOCKED)
        self.assertEqual(cap.failure_code, "CANVAS_2D_UNAVAILABLE")

    def test_adapter_delegates_final_identity_to_canonical_zf00_builder(self):
        receipt = build(observation())
        self.assertEqual(receipt.schema, "AdoptionFrictionReceiptV1")
        self.assertTrue(receipt.logical_id.startswith("afr-"))
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.execution_proven)
        self.assertEqual(receipt.recipe_refs, (RECIPE,))
        self.assertIsNone(receipt.total_score)

    def test_creation_value_component_must_remain_unknown_without_user_acceptance(self):
        vector = unknown_vector()
        vector["creation_time_to_value"] = 100
        with self.assertRaisesRegex(BrowserAdapterError, "CREATION_VALUE_FRICTION_REQUIRES_USER_ACCEPTANCE"):
            build(
                observation(
                    acceptance_mode=AcceptanceEvidenceMode.SYNTHETIC_TECHNICAL,
                    acceptance_evidence_ref="",
                ),
                vector=vector,
            )

    def test_reuse_recovery_component_must_remain_unknown_without_reopen(self):
        vector = unknown_vector()
        vector["reuse_recovery"] = 0
        with self.assertRaisesRegex(BrowserAdapterError, "REUSE_RECOVERY_FRICTION_REQUIRES_REOPEN"):
            build(
                observation(
                    persistence_mode=PersistenceEvidenceMode.DOWNLOAD_INITIATED,
                    persistence_evidence_ref="browser:download-click-1",
                ),
                vector=vector,
            )

    def test_non_browser_route_cannot_use_browser_adapter(self):
        with self.assertRaisesRegex(BrowserAdapterError, "BROWSER_ROUTE_DECISION_REQUIRED"):
            build(observation(), route_decision=decision("NATIVE_ANDROID_APK"))


if __name__ == "__main__":
    unittest.main()
