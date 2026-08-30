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


def _storage_digest(payload):
    logical = {key: value for key, value in payload.items() if key != "plan_digest"}
    return hashlib.sha256(_canonical(logical, ensure_ascii=False)).hexdigest()


def _model_digest(payload):
    logical = {key: value for key, value in payload.items() if key != "decision_digest"}
    return hashlib.sha256(
        b"AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1\0" + _canonical(logical)
    ).hexdigest()


def storage(*, cloud=False, status=None, actions=None, **overrides):
    if status is None:
        status = "READY_FOR_STORAGE_AUTHORITY_GATE" if cloud else "READY_FOR_LOCAL_USER_ACTION"
    if actions is None:
        actions = ["USER_CONFIRM_CLOUD_STORAGE_SCOPE"] if cloud else []
    payload = {
        "schema": "AuraDriveLocationPlanV1",
        "request_id": "request:test",
        "request_source_digest": D3,
        "capability_source_digest": D4,
        "intent_mode": "CLOUD_BACKED" if cloud else "DEFAULT_LOCAL_FIRST",
        "intent_explicit": cloud,
        "primary_location": "CLOUD_SELECTED_PENDING_AUTHORITY" if cloud else "LOCAL_PERSISTENT",
        "secondary_location": "PORTABLE_EXPORT_REOPEN",
        "portable_export_reopen_available": True,
        "cloud_selected": cloud,
        "cloud_controls_visible": cloud,
        "account_link_prompt_visible": bool(actions and "USER_LINK_CLOUD_ACCOUNT" in actions),
        "advanced_storage_controls_visible": cloud,
        "required_user_actions": list(actions),
        "warnings": [],
        "blockers": ["TEST_STORAGE_BLOCKER"] if status == "STORAGE_EVIDENCE_OR_ASSISTANCE_REQUIRED" else [],
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
    payload.update(overrides)
    payload["plan_digest"] = _storage_digest(payload)
    return payload


def option(
    route_id="route:remote",
    *,
    model_ref="model:remote",
    provider_ref="provider:test",
    actions=("EXPLICIT_REMOTE_EXECUTION_CONSENT",),
    evidence_ref="evidence:remote",
    evidence_digest=D3,
    execution_location="REMOTE",
    cost_class="INCLUDED",
):
    return {
        "route_id": route_id,
        "model_ref": model_ref,
        "provider_ref": provider_ref,
        "execution_location": execution_location,
        "cost_class": cost_class,
        "required_actions": list(actions),
        "zero_effect_ready": not actions,
        "download_bytes": 0,
        "candidate_evidence_ref": evidence_ref,
        "candidate_evidence_digest": evidence_digest,
        "evidence_summary": ["availability=PROVEN_AVAILABLE"],
    }


def model(*, disposition="LOCAL_ROUTE_READY", actions=None, options=None, **overrides):
    if actions is None:
        actions = []
    if options is None:
        options = []
    payload = {
        "schema": "CapabilityEscalationDecisionV1",
        "router_schema": "CapabilityEscalationRouterV1",
        "residual_id": "residual:test",
        "capability_ref": "cap:test",
        "recipe_plan_digest": D1,
        "residual_source_generation": "gen-1",
        "residual_source_currentness_ref": "current:source",
        "router_currentness_digest": D4,
        "disposition": disposition,
        "selected_route_id": "route:local" if disposition == "LOCAL_ROUTE_READY" else None,
        "options": list(options),
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
    payload.update(overrides)
    payload["decision_digest"] = _model_digest(payload)
    return payload


def user_choice_model(*choices):
    earned = sorted({action for choice in choices for action in choice["required_actions"]})
    return model(disposition="USER_CHOICE_REQUIRED", actions=earned, options=choices)


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
        self.assertEqual(got["presentation_groups"], [])
        self.assertEqual(got["candidate_action_groups"][0]["scope"], "AURA_DRIVE_STORAGE")
        self.assertIn("OWNER_CURRENTNESS_RECHECK_REQUIRED", got["blockers"])
        self.assertTrue(got["owner_currentness_gate_required"])
        self.assertFalse(got["ready_for_user_presentation"])

    def test_model_choice_stops_at_gate_and_preserves_exact_choice(self):
        remote = option(
            actions=(
                "EXPLICIT_REMOTE_EXECUTION_CONSENT",
                "REQUEST_CREDENTIAL_VIA_SECURE_OWNER",
            )
        )
        got = compile_external_service_intent_plan(storage(), user_choice_model(remote))
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")
        self.assertEqual(got["presentation_groups"], [])
        group = got["candidate_action_groups"][0]
        self.assertEqual(group["scope"], "MODEL_PROVIDER")
        self.assertNotIn("actions", group)
        self.assertEqual(group["choices"][0]["route_id"], "route:remote")
        self.assertEqual(group["choices"][0]["provider_ref"], "provider:test")
        self.assertEqual(group["choices"][0]["candidate_evidence_ref"], "evidence:remote")
        self.assertEqual(
            group["choices"][0]["required_actions"],
            ("EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_CREDENTIAL_VIA_SECURE_OWNER"),
        )

    def test_cloud_and_model_candidates_stay_two_scopes(self):
        remote = option(actions=("EXPLICIT_REMOTE_EXECUTION_CONSENT",))
        got = compile_external_service_intent_plan(
            storage(cloud=True), user_choice_model(remote)
        )
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")
        self.assertEqual(
            [g["scope"] for g in got["candidate_action_groups"]],
            ["AURA_DRIVE_STORAGE", "MODEL_PROVIDER"],
        )
        self.assertEqual(got["presentation_groups"], [])
        self.assertFalse(got["authority_scopes_coalesced"])

    def test_storage_link_does_not_satisfy_model_account(self):
        remote = option(
            actions=(
                "EXPLICIT_REMOTE_EXECUTION_CONSENT",
                "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER",
            )
        )
        got = compile_external_service_intent_plan(
            storage(cloud=True, actions=["USER_LINK_CLOUD_ACCOUNT"]),
            user_choice_model(remote),
        )
        storage_group, model_group = got["candidate_action_groups"]
        self.assertIn("USER_LINK_CLOUD_ACCOUNT", storage_group["actions"])
        self.assertIn(
            "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER",
            model_group["choices"][0]["required_actions"],
        )
        self.assertFalse(got["storage_account_state_satisfies_model_credentials"])

    def test_route_bound_consequences_do_not_union_into_actionable_bundle(self):
        local_download = option(
            "route:download",
            model_ref="model:download",
            provider_ref="",
            actions=("EXPLICIT_MODEL_DOWNLOAD_CONSENT",),
            evidence_ref="evidence:download",
            evidence_digest=D2,
            execution_location="LOCAL",
        )
        remote_paid = option(
            "route:paid",
            model_ref="model:paid",
            provider_ref="provider:paid",
            actions=(
                "EXPLICIT_REMOTE_EXECUTION_CONSENT",
                "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER",
                "EXPLICIT_PAYMENT_CONSENT",
            ),
            evidence_ref="evidence:paid",
            evidence_digest=D3,
            execution_location="REMOTE",
            cost_class="PAID",
        )
        got = compile_external_service_intent_plan(
            storage(), user_choice_model(local_download, remote_paid)
        )
        group = got["candidate_action_groups"][0]
        self.assertNotIn("actions", group)
        self.assertEqual(len(group["choices"]), 2)
        choices = {choice["route_id"]: choice for choice in group["choices"]}
        self.assertEqual(
            choices["route:download"]["required_actions"],
            ("EXPLICIT_MODEL_DOWNLOAD_CONSENT",),
        )
        self.assertEqual(choices["route:download"]["provider_ref"], "")
        self.assertEqual(
            choices["route:paid"]["required_actions"],
            (
                "EXPLICIT_REMOTE_EXECUTION_CONSENT",
                "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER",
                "EXPLICIT_PAYMENT_CONSENT",
            ),
        )
        self.assertEqual(choices["route:paid"]["provider_ref"], "provider:paid")
        self.assertEqual(
            set(group["candidate_action_classes"]),
            {
                "EXPLICIT_MODEL_DOWNLOAD_CONSENT",
                "EXPLICIT_REMOTE_EXECUTION_CONSENT",
                "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER",
                "EXPLICIT_PAYMENT_CONSENT",
            },
        )
        self.assertEqual(got["presentation_groups"], [])

    def test_same_action_class_keeps_distinct_route_provider_and_evidence(self):
        one = option(
            "route:one",
            provider_ref="provider:one",
            evidence_ref="evidence:one",
            evidence_digest=D2,
        )
        two = option(
            "route:two",
            provider_ref="provider:two",
            evidence_ref="evidence:two",
            evidence_digest=D3,
        )
        got = compile_external_service_intent_plan(storage(), user_choice_model(one, two))
        choices = got["candidate_action_groups"][0]["choices"]
        self.assertEqual(
            {(c["route_id"], c["provider_ref"], c["candidate_evidence_ref"]) for c in choices},
            {
                ("route:one", "provider:one", "evidence:one"),
                ("route:two", "provider:two", "evidence:two"),
            },
        )

    def test_same_evidence_ref_cannot_cross_scopes(self):
        ev1 = ScopeEvidenceV1("AURA_DRIVE_STORAGE", "evidence:same", D3, "gen-1", "cur-1")
        ev2 = ScopeEvidenceV1("MODEL_PROVIDER", "evidence:same", D4, "gen-2", "cur-2")
        with self.assertRaisesRegex(IntentBridgeError, "CROSS_SCOPE_EVIDENCE_REF_REUSE"):
            compile_external_service_intent_plan(storage(), model(), scope_evidence=(ev1, ev2))

    def test_same_evidence_digest_cannot_cross_scopes(self):
        ev1 = ScopeEvidenceV1("AURA_DRIVE_STORAGE", "evidence:a", D3, "gen-1", "cur-1")
        ev2 = ScopeEvidenceV1("MODEL_PROVIDER", "evidence:b", D3, "gen-2", "cur-2")
        with self.assertRaisesRegex(IntentBridgeError, "CROSS_SCOPE_EVIDENCE_DIGEST_REUSE"):
            compile_external_service_intent_plan(storage(), model(), scope_evidence=(ev1, ev2))

    def test_caller_evidence_never_proves_owner_or_clears_gate(self):
        remote = option()
        ev = ScopeEvidenceV1("MODEL_PROVIDER", "evidence:ownerish", D2, "gen-1", "cur-1")
        got = compile_external_service_intent_plan(
            storage(), user_choice_model(remote), scope_evidence=(ev,)
        )
        group = got["candidate_action_groups"][0]
        self.assertTrue(group["evidence_ref_supplied_unverified"])
        self.assertFalse(group["evidence_owner_proven"])
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")
        self.assertEqual(got["presentation_groups"], [])

    def test_upstream_storage_authority_widening_rejected_after_valid_identity(self):
        plan = storage(cloud=True, cloud_write_authorized=True)
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_AUTHORITY_WIDENING"):
            compile_external_service_intent_plan(plan, model())

    def test_upstream_model_effect_widening_rejected_after_valid_identity(self):
        decision = model(provider_call_made=True)
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_AUTHORITY_WIDENING"):
            compile_external_service_intent_plan(storage(), decision)

    def test_tampered_storage_digest_is_rejected(self):
        plan = storage()
        plan["primary_location"] = "TAMPERED"
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_PLAN_DIGEST_MISMATCH"):
            compile_external_service_intent_plan(plan, model())

    def test_tampered_model_digest_is_rejected(self):
        decision = model()
        decision["residual_source_generation"] = "tampered"
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_DECISION_DIGEST_MISMATCH"):
            compile_external_service_intent_plan(storage(), decision)

    def test_storage_action_without_cloud_is_rejected(self):
        plan = storage(cloud=False, actions=["USER_LINK_CLOUD_ACCOUNT"])
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_ACTION_WITHOUT_CLOUD_SELECTION"):
            compile_external_service_intent_plan(plan, model())

    def test_storage_authority_gate_requires_an_action(self):
        plan = storage(cloud=True, actions=[])
        with self.assertRaisesRegex(IntentBridgeError, "STORAGE_AUTHORITY_GATE_ACTION_REQUIRED"):
            compile_external_service_intent_plan(plan, model())

    def test_model_action_without_escalation_is_rejected(self):
        decision = model(
            disposition="NO_ESCALATION_REQUIRED",
            actions=["EXPLICIT_MODEL_DOWNLOAD_CONSENT"],
            selected_route_id=None,
        )
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_ACTION_WITHOUT_ESCALATION"):
            compile_external_service_intent_plan(storage(), decision)

    def test_storage_evidence_required_suppresses_all_candidates(self):
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

    def test_model_evidence_required_suppresses_all_candidates(self):
        decision = model(
            disposition="EVIDENCE_REQUIRED",
            actions=["EXPLICIT_REMOTE_EXECUTION_CONSENT"],
            selected_route_id=None,
        )
        got = compile_external_service_intent_plan(storage(), decision)
        self.assertEqual(got["disposition"], "REBASE_OR_EVIDENCE_REQUIRED")
        self.assertIn("MODEL_DECISION_NOT_READY", got["blockers"])
        self.assertEqual(got["candidate_action_groups"], [])
        self.assertEqual(got["presentation_groups"], [])

    def test_unknown_action_surface_fails_closed(self):
        bad = option(actions=("GENERIC_CLOUD_LOGIN",))
        decision = model(
            disposition="USER_CHOICE_REQUIRED",
            actions=["GENERIC_CLOUD_LOGIN"],
            options=[bad],
            selected_route_id=None,
        )
        with self.assertRaisesRegex(IntentBridgeError, "MODEL_ACTION_UNSUPPORTED"):
            compile_external_service_intent_plan(storage(), decision)

    def test_plan_digest_is_stable_and_binds_inputs(self):
        first = compile_external_service_intent_plan(storage(), model())
        second = compile_external_service_intent_plan(storage(), model())
        self.assertEqual(first["plan_digest"], second["plan_digest"])
        changed_storage = storage(secondary_location="NONE")
        changed = compile_external_service_intent_plan(changed_storage, model())
        self.assertNotEqual(first["plan_digest"], changed["plan_digest"])

    def _producer_inputs(self):
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
        recipe_plan = {
            "schema": "ArenaRecipePlanV1",
            "plan_digest": D1,
            "capability_refs": ["cap:test"],
            "status": "READY_FOR_ADMISSION",
            "blockers": [],
            "effect_authorized": False,
            "execution_proven": False,
            "publication_authorized": False,
            "payment_authorized": False,
            "marketplace_listed": False,
        }
        return currentness, residual, recipe_plan

    def test_actual_zf07_producer_local_route_does_not_present_alternative_actions(self):
        currentness, residual, recipe_plan = self._producer_inputs()
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

    def test_actual_zf07_user_choice_preserves_per_route_consequences(self):
        currentness, residual, recipe_plan = self._producer_inputs()
        local_download = CandidateRouteEvidenceV1(
            route_id="route:download",
            model_ref="model:download",
            capability_refs=("cap:test",),
            execution_location=ExecutionLocation.LOCAL,
            materialization=Materialization.DOWNLOAD_REQUIRED,
            availability=Availability.PROVEN_AVAILABLE,
            cost_class=CostClass.INCLUDED,
            credential_requirement=CredentialRequirement.NONE,
            remote_admission=RemoteAdmission.NOT_APPLICABLE,
            source_generation="gen-1",
            model_currentness_ref="current:model",
            context_window_tokens=8192,
            evidence_ref="evidence:download",
            evidence_digest=D2,
            download_bytes=1024,
        )
        remote_paid = CandidateRouteEvidenceV1(
            route_id="route:paid",
            model_ref="model:paid",
            capability_refs=("cap:test",),
            execution_location=ExecutionLocation.REMOTE,
            materialization=Materialization.REMOTE_SERVICE,
            availability=Availability.PROVEN_AVAILABLE,
            cost_class=CostClass.PAID,
            credential_requirement=CredentialRequirement.PROVIDER_ACCOUNT,
            remote_admission=RemoteAdmission.ADMITTED_BOUNDED,
            source_generation="gen-1",
            model_currentness_ref="current:model",
            context_window_tokens=8192,
            evidence_ref="evidence:paid",
            evidence_digest=D3,
            provider_ref="provider:paid",
            provider_currentness_ref="current:provider",
            rate_currentness_ref="current:rate",
        )
        decision = compile_capability_escalation(
            recipe_plan,
            residual,
            (local_download, remote_paid),
            currentness=currentness,
        )
        self.assertEqual(decision.disposition, EscalationDisposition.USER_CHOICE_REQUIRED)
        got = compile_external_service_intent_plan(storage(), decision)
        self.assertEqual(got["disposition"], "OWNER_CURRENTNESS_GATE_REQUIRED")
        self.assertEqual(got["presentation_groups"], [])
        group = got["candidate_action_groups"][0]
        self.assertNotIn("actions", group)
        choices = {choice["route_id"]: choice for choice in group["choices"]}
        self.assertEqual(
            choices["route:download"]["required_actions"],
            ("EXPLICIT_MODEL_DOWNLOAD_CONSENT",),
        )
        self.assertEqual(choices["route:download"]["provider_ref"], "")
        self.assertEqual(
            choices["route:paid"]["required_actions"],
            (
                "EXPLICIT_REMOTE_EXECUTION_CONSENT",
                "REQUEST_PROVIDER_ACCOUNT_VIA_OWNER",
                "EXPLICIT_PAYMENT_CONSENT",
            ),
        )
        self.assertEqual(choices["route:paid"]["provider_ref"], "provider:paid")

    def test_every_effect_flag_remains_false(self):
        remote = option(
            actions=("EXPLICIT_REMOTE_EXECUTION_CONSENT", "EXPLICIT_PAYMENT_CONSENT")
        )
        got = compile_external_service_intent_plan(
            storage(cloud=True), user_choice_model(remote)
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
