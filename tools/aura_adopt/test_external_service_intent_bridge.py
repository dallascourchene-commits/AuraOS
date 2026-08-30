import hashlib
import json
import unittest

from tools.aura_adopt.external_service_intent_bridge import (
    IntentBridgeError,
    ScopeEvidenceV1,
    compile_external_service_intent_plan,
)
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
    compile_capability_escalation,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def _canonical(value, *, ensure_ascii=True):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=ensure_ascii,
        allow_nan=False,
    ).encode("utf-8")


def seal_storage(plan):
    logical = {key: value for key, value in plan.items() if key != "plan_digest"}
    plan["plan_digest"] = hashlib.sha256(
        _canonical(logical, ensure_ascii=False)
    ).hexdigest()
    return plan


def seal_model(decision):
    logical = {
        key: value for key, value in decision.items() if key != "decision_digest"
    }
    decision["decision_digest"] = hashlib.sha256(
        b"AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1\0" + _canonical(logical)
    ).hexdigest()
    return decision


def storage(*, cloud=False, status=None, actions=None):
    if status is None:
        status = "READY_FOR_STORAGE_AUTHORITY_GATE" if cloud else "READY_FOR_LOCAL_USER_ACTION"
    if actions is None:
        actions = ["USER_CONFIRM_CLOUD_STORAGE_SCOPE"] if cloud else []
    blocked = status == "STORAGE_EVIDENCE_OR_ASSISTANCE_REQUIRED"
    plan = {
        "schema": "AuraDriveLocationPlanV1",
        "request_id": "request:test",
        "request_source_digest": "a" * 64,
        "capability_source_digest": "b" * 64,
        "intent_mode": "CLOUD_BACKED" if cloud else "DEFAULT_LOCAL_FIRST",
        "intent_explicit": cloud,
        "primary_location": "CLOUD_SELECTED_PENDING_AUTHORITY" if cloud else "LOCAL_PERSISTENT",
        "secondary_location": "PORTABLE_EXPORT_REOPEN",
        "portable_export_reopen_available": True,
        "cloud_selected": cloud,
        "cloud_controls_visible": cloud,
        "account_link_prompt_visible": "USER_LINK_CLOUD_ACCOUNT" in actions,
        "advanced_storage_controls_visible": cloud,
        "required_user_actions": list(actions),
        "warnings": [],
        "blockers": ["TEST_STORAGE_BLOCKER"] if blocked else [],
        "status": status,
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
    return seal_storage(plan)


def _local_option():
    return {
        "route_id": "route:local",
        "model_ref": "model:local",
        "provider_ref": "",
        "execution_location": "LOCAL",
        "cost_class": "INCLUDED",
        "required_actions": [],
        "zero_effect_ready": True,
        "download_bytes": None,
        "candidate_evidence_ref": "evidence:local",
        "candidate_evidence_digest": D3,
        "evidence_summary": ["availability=PROVEN_AVAILABLE"],
    }


def _choice_option(actions, *, provider):
    remote = provider
    return {
        "route_id": "route:remote" if remote else "route:download",
        "model_ref": "model:remote" if remote else "model:download",
        "provider_ref": "provider:test" if remote else "",
        "execution_location": "REMOTE" if remote else "LOCAL",
        "cost_class": "INCLUDED",
        "required_actions": list(actions),
        "zero_effect_ready": not actions,
        "download_bytes": None if remote else 1234,
        "candidate_evidence_ref": "evidence:choice",
        "candidate_evidence_digest": D4,
        "evidence_summary": ["availability=PROVEN_AVAILABLE"],
    }


def model(*, disposition="LOCAL_ROUTE_READY", actions=None, provider=False):
    if actions is None:
        actions = []
    if disposition == "LOCAL_ROUTE_READY":
        selected_route_id = "route:local"
        options = [_local_option()]
    elif disposition == "USER_CHOICE_REQUIRED":
        selected_route_id = None
        options = [_choice_option(actions, provider=provider)]
    else:
        selected_route_id = None
        options = []
    decision = {
        "schema": "CapabilityEscalationDecisionV1",
        "router_schema": "CapabilityEscalationRouterV1",
        "residual_id": "residual:test",
        "capability_ref": "cap:test",
        "recipe_plan_digest": D1,
        "residual_source_generation": "gen-1",
        "residual_source_currentness_ref": "current:source",
        "router_currentness_digest": D2,
        "disposition": disposition,
        "selected_route_id": selected_route_id,
        "options": options,
        "blockers": ["TEST_MODEL_BLOCKER"] if disposition in {"EVIDENCE_REQUIRED", "UPSTREAM_BLOCKED"} else [],
        "earned_action_classes": list(actions),
        "credential_prompt_performed": False,
        "credential_collected": False,
        "model_download_started": False,
        "provider_call_made": False,
        "payment_performed": False,
        "effect_authorized": False,
        "execution_proven": False,
        "catalog_evidence_authenticated": False,
    }
    return seal_model(decision)


class CrossCloudIntentTests(unittest.TestCase):
    def test_local_local_has_no_external_actions(self):
        got = compile_external_service_intent_plan(storage(), model())
        self.assertEqual(got["disposition"], "NO_EXTERNAL_SERVICE_ACTIONS")
        self.assertEqual(got["candidate_action_groups"], [])
        self.assertEqual(got["presentation_groups"], [])
        self.assertFalse(got["owner_currentness_gate_required"])
        self.assertFalse(got["effect_authorized"])

    def test_cloud_storage_stops_at_owner_currentness_gate(self):
        got = compile_external_service_intent_plan(storage(cloud=True), model())
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")
        self.assertIn("OWNER_CURRENTNESS_RECHECK_REQUIRED", got["blockers"])
        self.assertEqual(got["presentation_groups"], [])
        self.assertEqual(got["candidate_action_groups"][0]["scope"], "AURA_DRIVE_STORAGE")
        self.assertTrue(got["owner_currentness_gate_required"])
        self.assertFalse(got["ready_for_user_presentation"])

    def test_remote_model_choice_stays_route_bound_and_nonpresentable(self):
        actions = ["EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_CREDENTIAL_VIA_SECURE_OWNER"]
        got = compile_external_service_intent_plan(
            storage(), model(disposition="USER_CHOICE_REQUIRED", actions=actions, provider=True)
        )
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")
        self.assertEqual(got["presentation_groups"], [])
        group = got["candidate_action_groups"][0]
        self.assertEqual(group["scope"], "MODEL_PROVIDER")
        self.assertEqual(group["choices"][0]["required_actions"], tuple(actions))
        self.assertEqual(group["choices"][0]["provider_ref"], "provider:test")
        self.assertFalse(got["storage_account_state_satisfies_model_credentials"])

    def test_cloud_and_remote_model_stay_two_candidate_scopes(self):
        got = compile_external_service_intent_plan(
            storage(cloud=True),
            model(
                disposition="USER_CHOICE_REQUIRED",
                actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER"],
                provider=True,
            ),
        )
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")
        self.assertEqual(
            [group["scope"] for group in got["candidate_action_groups"]],
            ["AURA_DRIVE_STORAGE", "MODEL_PROVIDER"],
        )
        self.assertEqual(got["presentation_groups"], [])
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
        storage_group, model_group = got["candidate_action_groups"]
        self.assertIn("USER_LINK_CLOUD_ACCOUNT", storage_group["actions"])
        self.assertIn("REQUEST_PROVIDER_ACCOUNT_VIA_OWNER", model_group["choices"][0]["required_actions"])
        self.assertFalse(got["storage_account_state_satisfies_model_credentials"])

    def test_scope_evidence_is_explicitly_unverified_and_never_clears_gate(self):
        evidence = ScopeEvidenceV1("AURA_DRIVE_STORAGE", "evidence:storage", D3, "gen-1", "cur-1")
        got = compile_external_service_intent_plan(
            storage(cloud=True), model(), scope_evidence=(evidence,)
        )
        group = got["candidate_action_groups"][0]
        self.assertTrue(group["evidence_ref_supplied_unverified"])
        self.assertFalse(group["evidence_owner_proven"])
        self.assertEqual(got["presentation_groups"], [])
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")

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

    def test_tampered_storage_payload_rejected_by_canonical_digest(self):
        plan = storage(cloud=True)
        plan["required_user_actions"] = ["USER_LINK_CLOUD_ACCOUNT"]
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_PLAN_DIGEST_MISMATCH"):
            compile_external_service_intent_plan(plan, model())

    def test_tampered_model_payload_rejected_by_canonical_digest(self):
        decision = model(disposition="USER_CHOICE_REQUIRED", actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT"], provider=True)
        decision["earned_action_classes"].append("EXPLICIT_PAYMENT_CONSENT")
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_DECISION_DIGEST_MISMATCH"):
            compile_external_service_intent_plan(storage(), decision)

    def test_upstream_storage_authority_widening_rejected_after_valid_identity(self):
        plan = storage(cloud=True)
        plan["cloud_write_authorized"] = True
        seal_storage(plan)
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_AUTHORITY_WIDENING"):
            compile_external_service_intent_plan(plan, model())

    def test_upstream_model_effect_widening_rejected_after_valid_identity(self):
        decision = model()
        decision["provider_call_made"] = True
        seal_model(decision)
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_AUTHORITY_WIDENING"):
            compile_external_service_intent_plan(storage(), decision)

    def test_storage_action_without_cloud_is_rejected_after_valid_identity(self):
        plan = storage(cloud=False)
        plan["required_user_actions"] = ["USER_LINK_CLOUD_ACCOUNT"]
        seal_storage(plan)
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_ACTION_WITHOUT_CLOUD_SELECTION"):
            compile_external_service_intent_plan(plan, model())

    def test_storage_authority_gate_requires_an_action(self):
        plan = storage(cloud=True)
        plan["required_user_actions"] = []
        plan["account_link_prompt_visible"] = False
        seal_storage(plan)
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_AUTHORITY_GATE_ACTION_REQUIRED"):
            compile_external_service_intent_plan(plan, model())

    def test_model_action_without_escalation_is_rejected(self):
        decision = model(
            disposition="NO_ESCALATION_REQUIRED",
            actions=["EXPLICIT_MODEL_DOWNLOAD_CONSENT"],
        )
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_ACTION_WITHOUT_ESCALATION"):
            compile_external_service_intent_plan(storage(), decision)

    def test_storage_evidence_required_suppresses_candidate_actions(self):
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
        self.assertEqual(got["candidate_action_groups"], [])
        self.assertEqual(got["presentation_groups"], [])

    def test_model_evidence_required_suppresses_candidate_actions(self):
        got = compile_external_service_intent_plan(
            storage(), model(disposition="EVIDENCE_REQUIRED")
        )
        self.assertEqual(got["disposition"], "REBASE_OR_EVIDENCE_REQUIRED")
        self.assertIn("MODEL_DECISION_NOT_READY", got["blockers"])
        self.assertEqual(got["candidate_action_groups"], [])
        self.assertEqual(got["presentation_groups"], [])

    def test_unknown_action_surface_fails_closed(self):
        decision = model(
            disposition="USER_CHOICE_REQUIRED", actions=["GENERIC_CLOUD_LOGIN"]
        )
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_ACTION_UNSUPPORTED"):
            compile_external_service_intent_plan(storage(), decision)

    def test_plan_digest_is_stable_and_binds_both_inputs(self):
        first = compile_external_service_intent_plan(storage(), model())
        second = compile_external_service_intent_plan(storage(), model())
        self.assertEqual(first["plan_digest"], second["plan_digest"])
        changed_decision = model()
        changed_decision["router_currentness_digest"] = D4
        seal_model(changed_decision)
        changed = compile_external_service_intent_plan(storage(), changed_decision)
        self.assertNotEqual(first["plan_digest"], changed["plan_digest"])

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
            recipe_plan, residual, (local, remote), currentness=currentness
        )
        self.assertEqual(decision.disposition, EscalationDisposition.LOCAL_ROUTE_READY)
        self.assertTrue(decision.earned_action_classes)
        got = compile_external_service_intent_plan(storage(), decision)
        self.assertEqual(got["model_disposition"], "LOCAL_ROUTE_READY")
        self.assertEqual(got["model_selected_route_id"], "route:local")
        self.assertEqual(got["candidate_action_groups"], [])
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
