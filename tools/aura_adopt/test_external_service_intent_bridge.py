import unittest
from dataclasses import dataclass
from enum import Enum

from tools.aura_adopt.external_service_intent_bridge import (
    IntentBridgeError,
    ScopeEvidenceV1,
    compile_external_service_intent_plan,
)
from tools.aura_adopt.capability_escalation_router import (
    Availability,
    CandidateRouteEvidenceV1,
    CapabilityEscalationDecisionV1,
    CapabilityResidualV1,
    CostClass,
    CredentialRequirement,
    EscalationDisposition,
    ExecutionLocation,
    Materialization,
    RemoteAdmission,
    ResidualKind,
    RouterCurrentnessV1,
    compile_capability_escalation,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def storage(*, cloud=False, status=None, actions=None):
    if status is None:
        status = "READY_FOR_STORAGE_AUTHORITY_GATE" if cloud else "READY_FOR_LOCAL_USER_ACTION"
    if actions is None:
        actions = ["USER_CONFIRM_CLOUD_STORAGE_SCOPE"] if cloud else []
    return {
        "schema": "AuraDriveLocationPlanV1",
        "plan_digest": D1,
        "status": status,
        "primary_location": "CLOUD_SELECTED_PENDING_AUTHORITY" if cloud else "LOCAL_PERSISTENT",
        "secondary_location": "PORTABLE_EXPORT_REOPEN",
        "cloud_selected": cloud,
        "required_user_actions": actions,
        "local_write_authorized": False,
        "local_read_authorized": False,
        "portable_export_authorized": False,
        "portable_reopen_proven": False,
        "cloud_read_authorized": False,
        "cloud_write_authorized": False,
        "cloud_sync_authorized": False,
        "account_link_authorized": False,
        "network_fetch_authorized": False,
        "effect_authorized": False,
        "execution_proven": False,
    }


def model(*, disposition="LOCAL_ROUTE_READY", actions=None, provider=False):
    if actions is None:
        actions = []
    opts = []
    if provider:
        opts = [{"provider_ref": "provider:test", "candidate_evidence_digest": D3}]
    return {
        "schema": "CapabilityEscalationDecisionV1",
        "decision_digest": D2,
        "disposition": disposition,
        "selected_route_id": "route:local" if disposition == "LOCAL_ROUTE_READY" else None,
        "earned_action_classes": actions,
        "options": opts,
        "credential_prompt_performed": False,
        "credential_collected": False,
        "model_download_started": False,
        "provider_call_made": False,
        "payment_performed": False,
        "effect_authorized": False,
        "execution_proven": False,
    }


class CrossCloudIntentTests(unittest.TestCase):
    def test_local_local_has_no_external_actions(self):
        got = compile_external_service_intent_plan(storage(), model())
        self.assertEqual(got["disposition"], "NO_EXTERNAL_SERVICE_ACTIONS")
        self.assertEqual(got["presentation_groups"], [])
        self.assertFalse(got["effect_authorized"])

    def test_cloud_storage_only_is_one_separate_scope(self):
        got = compile_external_service_intent_plan(storage(cloud=True), model())
        self.assertEqual(got["disposition"], "ONE_SEPARATE_SCOPE_USER_CHOICE")
        self.assertEqual(got["presentation_groups"][0]["scope"], "AURA_DRIVE_STORAGE")
        self.assertFalse(got["presentation_groups"][0]["evidence_owner_proven"])

    def test_remote_model_only_is_one_separate_scope(self):
        got = compile_external_service_intent_plan(
            storage(),
            model(
                disposition="USER_CHOICE_REQUIRED",
                actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_CREDENTIAL_VIA_SECURE_OWNER"],
                provider=True,
            ),
        )
        self.assertEqual(got["presentation_groups"][0]["scope"], "MODEL_PROVIDER")
        self.assertFalse(got["storage_account_state_satisfies_model_credentials"])

    def test_cloud_and_remote_model_stay_two_scopes(self):
        got = compile_external_service_intent_plan(
            storage(cloud=True),
            model(
                disposition="USER_CHOICE_REQUIRED",
                actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER"],
                provider=True,
            ),
        )
        self.assertEqual(got["disposition"], "MULTI_SCOPE_USER_CHOICES_SEPARATED")
        self.assertEqual(
            [g["scope"] for g in got["presentation_groups"]],
            ["AURA_DRIVE_STORAGE", "MODEL_PROVIDER"],
        )
        self.assertFalse(got["authority_scopes_coalesced"])

    def test_storage_link_does_not_satisfy_model_account(self):
        got = compile_external_service_intent_plan(
            storage(cloud=True, actions=["USER_LINK_CLOUD_ACCOUNT"]),
            model(
                disposition="USER_CHOICE_REQUIRED",
                actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER"],
                provider=True,
            ),
        )
        self.assertIn("USER_LINK_CLOUD_ACCOUNT", got["presentation_groups"][0]["actions"])
        self.assertIn("REQUEST_PROVIDER_ACCOUNT_VIA_OWNER", got["presentation_groups"][1]["actions"])
        self.assertFalse(got["storage_account_state_satisfies_model_credentials"])

    def test_same_evidence_ref_cannot_cross_scopes(self):
        ev1 = ScopeEvidenceV1("AURA_DRIVE_STORAGE", "evidence:same", D3, "gen-1", "cur-1")
        ev2 = ScopeEvidenceV1("MODEL_PROVIDER", "evidence:same", D4, "gen-2", "cur-2")
        with self.assertRaisesRegex(IntentBridgeError, "CROSS_SCOPE_EVIDENCE_REF_REUSE"):
            compile_external_service_intent_plan(storage(cloud=True), model(), scope_evidence=(ev1, ev2))

    def test_same_evidence_digest_cannot_cross_scopes(self):
        ev1 = ScopeEvidenceV1("AURA_DRIVE_STORAGE", "evidence:a", D3, "gen-1", "cur-1")
        ev2 = ScopeEvidenceV1("MODEL_PROVIDER", "evidence:b", D3, "gen-2", "cur-2")
        with self.assertRaisesRegex(IntentBridgeError, "CROSS_SCOPE_EVIDENCE_DIGEST_REUSE"):
            compile_external_service_intent_plan(storage(cloud=True), model(), scope_evidence=(ev1, ev2))

    def test_upstream_storage_authority_widening_rejected(self):
        plan = storage(cloud=True)
        plan["cloud_write_authorized"] = True
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_AUTHORITY_WIDENING"):
            compile_external_service_intent_plan(plan, model())

    def test_upstream_model_effect_widening_rejected(self):
        decision = model()
        decision["provider_call_made"] = True
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_AUTHORITY_WIDENING"):
            compile_external_service_intent_plan(storage(), decision)

    def test_storage_action_without_cloud_is_rejected(self):
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_ACTION_WITHOUT_CLOUD_SELECTION"):
            compile_external_service_intent_plan(
                storage(cloud=False, actions=["USER_LINK_CLOUD_ACCOUNT"]), model()
            )

    def test_model_action_without_escalation_is_rejected(self):
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_ACTION_WITHOUT_ESCALATION"):
            compile_external_service_intent_plan(
                storage(),
                model(
                    disposition="NO_ESCALATION_REQUIRED",
                    actions=["EXPLICIT_MODEL_DOWNLOAD_CONSENT"],
                ),
            )

    def test_storage_evidence_required_suppresses_future_actions(self):
        got = compile_external_service_intent_plan(
            storage(
                cloud=True,
                status="STORAGE_EVIDENCE_OR_ASSISTANCE_REQUIRED",
                actions=["USER_LINK_CLOUD_ACCOUNT"],
            ),
            model(),
        )
        self.assertEqual(got["disposition"], "REBASE_OR_EVIDENCE_REQUIRED")
        self.assertIn("STORAGE_PLAN_NOT_READY", got["blockers"])
        self.assertEqual(got["presentation_groups"], [])

    def test_model_evidence_required_suppresses_future_actions(self):
        got = compile_external_service_intent_plan(
            storage(),
            model(
                disposition="EVIDENCE_REQUIRED",
                actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT"],
            ),
        )
        self.assertEqual(got["disposition"], "REBASE_OR_EVIDENCE_REQUIRED")
        self.assertIn("MODEL_DECISION_NOT_READY", got["blockers"])
        self.assertEqual(got["presentation_groups"], [])

    def test_unknown_action_surface_fails_closed(self):
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_ACTION_UNSUPPORTED"):
            compile_external_service_intent_plan(
                storage(), model(disposition="USER_CHOICE_REQUIRED", actions=["GENERIC_CLOUD_LOGIN"])
            )

    def test_plan_digest_is_stable_and_binds_both_inputs(self):
        first = compile_external_service_intent_plan(storage(), model())
        second = compile_external_service_intent_plan(storage(), model())
        self.assertEqual(first["plan_digest"], second["plan_digest"])
        decision = model()
        decision["decision_digest"] = D4
        changed = compile_external_service_intent_plan(storage(), decision)
        self.assertNotEqual(first["plan_digest"], changed["plan_digest"])

    def test_dataclass_model_projection_is_composable(self):
        class D(str, Enum):
            LOCAL_ROUTE_READY = "LOCAL_ROUTE_READY"

        @dataclass(frozen=True)
        class O:
            provider_ref: str = ""

        @dataclass(frozen=True)
        class Decision:
            schema: str = "CapabilityEscalationDecisionV1"
            decision_digest: str = D2
            disposition: D = D.LOCAL_ROUTE_READY
            selected_route_id: str = "route:local"
            earned_action_classes: tuple[str, ...] = ()
            options: tuple[O, ...] = ()
            credential_prompt_performed: bool = False
            credential_collected: bool = False
            model_download_started: bool = False
            provider_call_made: bool = False
            payment_performed: bool = False
            effect_authorized: bool = False
            execution_proven: bool = False

        got = compile_external_service_intent_plan(storage(), Decision())
        self.assertEqual(got["disposition"], "NO_EXTERNAL_SERVICE_ACTIONS")

    def test_actual_zf07_decision_dataclass_is_composable(self):
        decision = CapabilityEscalationDecisionV1(
            residual_id="residual:test",
            capability_ref="cap:test",
            recipe_plan_digest=D1,
            residual_source_generation="gen-1",
            residual_source_currentness_ref="current:model",
            router_currentness_digest=D3,
            disposition=EscalationDisposition.LOCAL_ROUTE_READY,
            selected_route_id="route:local",
            options=(),
            blockers=(),
            earned_action_classes=(),
            decision_digest=D2,
        )
        got = compile_external_service_intent_plan(storage(), decision)
        self.assertEqual(got["model_disposition"], "LOCAL_ROUTE_READY")
        self.assertEqual(got["disposition"], "NO_EXTERNAL_SERVICE_ACTIONS")

    def test_actual_zf07_producer_local_route_does_not_present_alternative_actions(self):
        currentness = RouterCurrentnessV1(
            source_currentness_ref="current:source",
            model_catalog_currentness_ref="current:model",
            provider_catalog_currentness_ref="current:provider",
            rate_catalog_currentness_ref="current:rate",
        )
        residual = CapabilityResidualV1(
            residual_id="residual:test",
            recipe_plan_digest=D1,
            capability_ref="cap:test",
            residual_kind=ResidualKind.MODEL_INFERENCE_REQUIRED,
            unresolved=True,
            source_generation="gen-1",
            source_currentness_ref="current:source",
            minimum_context_tokens=1024,
        )
        local = CandidateRouteEvidenceV1(
            route_id="route:local",
            model_ref="model:local",
            capability_refs=("cap:test",),
            execution_location=ExecutionLocation.LOCAL,
            materialization=Materialization.PRESENT,
            availability=Availability.PROVEN_AVAILABLE,
            cost_class=CostClass.INCLUDED,
            credential_requirement=CredentialRequirement.NONE,
            remote_admission=RemoteAdmission.NOT_APPLICABLE,
            source_generation="gen-1",
            model_currentness_ref="current:model",
            context_window_tokens=8192,
            evidence_ref="evidence:local",
            evidence_digest=D3,
        )
        remote = CandidateRouteEvidenceV1(
            route_id="route:remote",
            model_ref="model:remote",
            capability_refs=("cap:test",),
            execution_location=ExecutionLocation.REMOTE,
            materialization=Materialization.REMOTE_SERVICE,
            availability=Availability.PROVEN_AVAILABLE,
            cost_class=CostClass.INCLUDED,
            credential_requirement=CredentialRequirement.PROVIDER_ACCOUNT,
            remote_admission=RemoteAdmission.ADMITTED_BOUNDED,
            source_generation="gen-1",
            model_currentness_ref="current:model",
            context_window_tokens=8192,
            evidence_ref="evidence:remote",
            evidence_digest=D4,
            provider_ref="provider:test",
            provider_currentness_ref="current:provider",
            rate_currentness_ref="current:rate",
        )
        recipe_plan = {
            "schema": "ArenaRecipePlanV1",
            "plan_digest": D1,
            "capability_refs": ["cap:test"],
            "status": "READY_FOR_ADMISSION",
            "effect_authorized": False,
            "execution_proven": False,
            "publication_authorized": False,
            "payment_authorized": False,
            "marketplace_listed": False,
        }
        decision = compile_capability_escalation(
            recipe_plan,
            residual,
            (local, remote),
            currentness=currentness,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.LOCAL_ROUTE_READY)
        self.assertTrue(decision.earned_action_classes)
        got = compile_external_service_intent_plan(storage(), decision)
        self.assertEqual(got["model_disposition"], "LOCAL_ROUTE_READY")
        self.assertEqual(got["model_selected_route_id"], "route:local")
        self.assertEqual(got["presentation_groups"], [])
        self.assertEqual(got["disposition"], "NO_EXTERNAL_SERVICE_ACTIONS")

    def test_every_effect_flag_remains_false(self):
        got = compile_external_service_intent_plan(
            storage(cloud=True),
            model(
                disposition="USER_CHOICE_REQUIRED",
                actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT", "EXPLICIT_PAYMENT_CONSENT"],
                provider=True,
            ),
        )
        for key in (
            "storage_read_authorized",
            "storage_write_authorized",
            "storage_sync_authorized",
            "account_link_authorized",
            "credential_prompt_performed",
            "credential_collected",
            "model_download_started",
            "provider_call_made",
            "payment_performed",
            "network_fetch_authorized",
            "effect_authorized",
            "execution_proven",
        ):
            self.assertIs(got[key], False, key)


if __name__ == "__main__":
    unittest.main()
