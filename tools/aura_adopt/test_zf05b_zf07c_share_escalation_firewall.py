import copy
import unittest

from zf05b_zf07c_share_escalation_firewall import (
    FirewallError,
    ProviderTargetEvidenceV1,
    _domain_digest,
    _plain_digest,
    compile_share_escalation_firewall,
    verify_router_currentness,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64


def make_share_plan(status="READY_FOR_USER_ACTION"):
    blockers = [] if status == "READY_FOR_USER_ACTION" else ["MISSING_BINDING:x"]
    raw = {
        "schema": "ShareLaunchPlanV1", "capsule_digest": A, "capsule_id": "capsule-1",
        "preferred_entry_surface": "ZERO_INSTALL_WEB_PWA", "next_surface": None,
        "creator_ref": "creator:alice", "claimed_attribution_refs": ["creator:alice"],
        "attribution_evidence_current": status == "READY_FOR_USER_ACTION",
        "attribution_identity_proven": False, "referral_depth": 0,
        "required_user_actions": ["OPEN_ENTRY_SURFACE", "REVIEW_PROVENANCE_AND_ATTRIBUTION", "CONFIRM_REPRODUCTION_INTENT"],
        "blockers": blockers, "status": status, "network_fetch_authorized": False,
        "install_authorized": False, "execution_authorized": False, "execution_proven": False,
        "publication_authorized": False, "payment_authorized": False, "telemetry_authorized": False,
        "recipient_tracking_authorized": False, "provider_call_authorized": False,
        "adoption_success_proven": False,
    }
    raw["plan_digest"] = _plain_digest(raw)
    return raw


def make_recipe_plan(status="READY_FOR_ADMISSION"):
    blockers = [] if status == "READY_FOR_ADMISSION" else ["MISSING_BINDING:cap:model"]
    raw = {
        "schema": "ArenaRecipePlanV1", "recipe_digest": B, "recipe_id": "recipe-1",
        "recipe_version": "v1", "purpose": "reproduce shared task", "capability_refs": ["cap:model"],
        "asset_refs": [], "parameters": {}, "constraints": {}, "effect_ceiling": "NONE",
        "rights": {"use": "ALLOWED", "modify": "ALLOWED", "redistribute": "ALLOWED", "commercial": "UNKNOWN", "attribution_required": True, "license_ref": None},
        "blockers": blockers, "status": status, "authority_owner_resolved": False,
        "effect_authorized": False, "execution_proven": False, "publication_authorized": False,
        "payment_authorized": False, "marketplace_listed": False,
    }
    raw["plan_digest"] = _plain_digest(raw)
    return raw


def make_currentness():
    return {"source_currentness_ref": "cur:recipe", "model_catalog_currentness_ref": "cur:model-catalog", "provider_catalog_currentness_ref": "cur:provider-catalog", "rate_catalog_currentness_ref": "cur:rate-catalog"}


def make_residual(recipe_plan=None, kind="MODEL_INFERENCE_REQUIRED", unresolved=True):
    recipe_plan = recipe_plan or make_recipe_plan()
    return {"residual_id": "residual-1", "recipe_plan_digest": recipe_plan["plan_digest"], "capability_ref": "cap:model", "residual_kind": kind, "unresolved": unresolved, "source_generation": "gen:recipe-plan", "source_currentness_ref": "cur:recipe", "minimum_context_tokens": 1024}


def local_option():
    return {"route_id": "local:present", "model_ref": "model:local", "provider_ref": "", "execution_location": "LOCAL", "cost_class": "INCLUDED", "required_actions": (), "zero_effect_ready": True, "download_bytes": None, "candidate_evidence_ref": "evidence:local", "candidate_evidence_digest": C, "evidence_summary": ("source_generation=gen:model", "model_currentness=cur:model-catalog", "availability=PROVEN_AVAILABLE", "cost=INCLUDED")}


def remote_option():
    return {"route_id": "remote:provider-a", "model_ref": "model:remote-a", "provider_ref": "provider:a", "execution_location": "REMOTE", "cost_class": "PAID", "required_actions": ("EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_CREDENTIAL_VIA_SECURE_OWNER", "EXPLICIT_PAYMENT_CONSENT"), "zero_effect_ready": False, "download_bytes": None, "candidate_evidence_ref": "evidence:remote-a", "candidate_evidence_digest": D, "evidence_summary": ("source_generation=gen:model-a", "model_currentness=cur:model-catalog", "availability=PROVEN_AVAILABLE", "cost=PAID", "provider=provider:a", "provider_currentness=cur:provider-catalog", "rate_currentness=cur:rate-catalog")}


def make_router_decision(residual=None, currentness=None, *, disposition="USER_CHOICE_REQUIRED", options=None, selected_route_id=None):
    recipe = make_recipe_plan(); residual = residual or make_residual(recipe); currentness = currentness or make_currentness()
    _, currentness_digest = verify_router_currentness(currentness)
    options = list(options if options is not None else [remote_option()])
    earned = sorted({a for o in options for a in o["required_actions"]})
    logical = {"schema": "CapabilityEscalationDecisionV1", "router_schema": "CapabilityEscalationRouterV1", "residual_id": residual["residual_id"], "capability_ref": residual["capability_ref"], "recipe_plan_digest": residual["recipe_plan_digest"], "residual_source_generation": residual["source_generation"], "residual_source_currentness_ref": residual["source_currentness_ref"], "router_currentness_digest": currentness_digest, "disposition": disposition, "selected_route_id": selected_route_id, "options": options, "blockers": (), "earned_action_classes": earned, "credential_prompt_performed": False, "credential_collected": False, "model_download_started": False, "provider_call_made": False, "payment_performed": False, "effect_authorized": False, "execution_proven": False, "catalog_evidence_authenticated": False}
    raw = copy.deepcopy(logical); raw["decision_digest"] = _domain_digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical); return raw


def provider_target(option=None, principal="recipient:1", **kw):
    option = option or remote_option()
    data = dict(evidence_ref="target-evidence:provider-a", evidence_digest=E, currentness_ref="cur:target-a", currentness_state="CURRENT", principal_ref=principal, route_id=option["route_id"], model_ref=option["model_ref"], provider_ref=option["provider_ref"], candidate_evidence_ref=option["candidate_evidence_ref"], candidate_evidence_digest=option["candidate_evidence_digest"], cost_class=option["cost_class"], provider_currentness_ref="cur:provider-catalog", rate_currentness_ref="cur:rate-catalog")
    data.update(kw); return ProviderTargetEvidenceV1(**data)


def compile_default(*, share=None, recipe=None, residual=None, currentness=None, decision=None, targets=None):
    share = share or make_share_plan(); recipe = recipe or make_recipe_plan(); currentness = currentness or make_currentness(); residual = residual or make_residual(recipe); decision = decision or make_router_decision(residual, currentness); targets = [provider_target()] if targets is None else targets
    return compile_share_escalation_firewall(share, recipe, residual, decision, router_currentness=currentness, principal_ref="recipient:1", provider_targets=targets)


class FirewallTests(unittest.TestCase):
    def test_remote_owner_projection_and_target_pass(self):
        out = compile_default(); self.assertEqual(out["disposition"], "RECIPIENT_ESCALATION_READY"); self.assertTrue(out["owner_projection_identity_recomputed"]); self.assertTrue(out["provider_targets_verified"]); self.assertFalse(out["provider_call_authorized"])

    def test_share_plan_tamper_rejected(self):
        share = make_share_plan(); share["creator_ref"] = "creator:mallory"
        with self.assertRaisesRegex(FirewallError, "SHARE_PLAN_DIGEST_MISMATCH"): compile_default(share=share)

    def test_share_authority_rejected_even_rehashed(self):
        share = make_share_plan(); share["provider_call_authorized"] = True; logical = dict(share); logical.pop("plan_digest"); share["plan_digest"] = _plain_digest(logical)
        with self.assertRaisesRegex(FirewallError, "SHARE_AUTHORITY_WIDENING"): compile_default(share=share)

    def test_share_not_ready(self):
        self.assertEqual(compile_default(share=make_share_plan("EVIDENCE_REQUIRED"))["disposition"], "SHARE_EVIDENCE_REQUIRED")

    def test_recipe_plan_tamper(self):
        recipe = make_recipe_plan(); recipe["purpose"] = "tampered"
        with self.assertRaisesRegex(FirewallError, "RECIPE_PLAN_DIGEST_MISMATCH"): compile_default(recipe=recipe)

    def test_recipe_not_ready(self):
        recipe = make_recipe_plan("BINDING_EVIDENCE_REQUIRED"); residual = make_residual(recipe); decision = make_router_decision(residual)
        self.assertEqual(compile_default(recipe=recipe, residual=residual, decision=decision)["disposition"], "EVIDENCE_REQUIRED")

    def test_residual_recipe_binding(self):
        recipe = make_recipe_plan(); residual = make_residual(recipe); residual["recipe_plan_digest"] = "9" * 64
        with self.assertRaisesRegex(FirewallError, "RESIDUAL_RECIPE_PLAN_MISMATCH"): compile_default(recipe=recipe, residual=residual)

    def test_residual_capability_binding(self):
        recipe = make_recipe_plan(); residual = make_residual(recipe); residual["capability_ref"] = "cap:not-in-plan"
        with self.assertRaisesRegex(FirewallError, "RESIDUAL_CAPABILITY_NOT_IN_RECIPE_PLAN"): compile_default(recipe=recipe, residual=residual)

    def test_residual_currentness_binding(self):
        recipe = make_recipe_plan(); residual = make_residual(recipe); residual["source_currentness_ref"] = "cur:stale"
        with self.assertRaisesRegex(FirewallError, "RESIDUAL_SOURCE_CURRENTNESS_STALE"): compile_default(recipe=recipe, residual=residual)

    def test_router_decision_digest_recomputed(self):
        recipe = make_recipe_plan(); residual = make_residual(recipe); decision = make_router_decision(residual); decision["decision_digest"] = "8" * 64
        with self.assertRaisesRegex(FirewallError, "ROUTER_DECISION_DIGEST_MISMATCH"): compile_default(recipe=recipe, residual=residual, decision=decision)

    def test_decision_source_generation_binding(self):
        recipe = make_recipe_plan(); residual = make_residual(recipe); decision = make_router_decision(residual); decision["residual_source_generation"] = "gen:other"; logical = dict(decision); logical.pop("decision_digest"); decision["decision_digest"] = _domain_digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical)
        with self.assertRaisesRegex(FirewallError, "DECISION_RESIDUAL_SOURCE_GENERATION_MISMATCH"): compile_default(recipe=recipe, residual=residual, decision=decision)

    def test_router_currentness_binding(self):
        recipe = make_recipe_plan(); currentness = make_currentness(); residual = make_residual(recipe); decision = make_router_decision(residual, currentness); changed = dict(currentness); changed["provider_catalog_currentness_ref"] = "cur:provider-new"
        with self.assertRaisesRegex(FirewallError, "DECISION_ROUTER_CURRENTNESS_MISMATCH"): compile_default(recipe=recipe, residual=residual, currentness=changed, decision=decision)

    def test_earned_action_union(self):
        recipe = make_recipe_plan(); residual = make_residual(recipe); decision = make_router_decision(residual); decision["earned_action_classes"] = []; logical = dict(decision); logical.pop("decision_digest"); decision["decision_digest"] = _domain_digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical)
        with self.assertRaisesRegex(FirewallError, "DECISION_EARNED_ACTIONS_MISMATCH"): compile_default(recipe=recipe, residual=residual, decision=decision)

    def test_decision_effect_refused(self):
        recipe = make_recipe_plan(); residual = make_residual(recipe); decision = make_router_decision(residual); decision["provider_call_made"] = True; logical = dict(decision); logical.pop("decision_digest"); decision["decision_digest"] = _domain_digest("AURA_ADOPT_CAPABILITY_ESCALATION_DECISION_V1", logical)
        with self.assertRaisesRegex(FirewallError, "ROUTER_DECISION_AUTHORITY_WIDENING"): compile_default(recipe=recipe, residual=residual, decision=decision)

    def test_remote_requires_target(self):
        out = compile_default(targets=[]); self.assertEqual(out["disposition"], "EVIDENCE_REQUIRED"); self.assertIn("PROVIDER_TARGET_EVIDENCE_REQUIRED:remote:provider-a", out["blockers"])

    def test_wrong_target_route(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_TARGET_ROUTE_NOT_IN_DECISION"): compile_default(targets=[provider_target(route_id="remote:provider-b")])

    def test_wrong_target_provider(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_TARGET_EVIDENCE_MISMATCH"): compile_default(targets=[provider_target(provider_ref="provider:b")])

    def test_wrong_target_model(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_TARGET_EVIDENCE_MISMATCH"): compile_default(targets=[provider_target(model_ref="model:other")])

    def test_wrong_target_principal(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_TARGET_EVIDENCE_MISMATCH"): compile_default(targets=[provider_target(principal_ref="recipient:2")])

    def test_wrong_candidate_digest(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_TARGET_EVIDENCE_MISMATCH"): compile_default(targets=[provider_target(candidate_evidence_digest="7" * 64)])

    def test_wrong_provider_currentness(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_TARGET_EVIDENCE_MISMATCH"): compile_default(targets=[provider_target(provider_currentness_ref="cur:other-provider")])

    def test_wrong_rate_currentness(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_TARGET_EVIDENCE_MISMATCH"): compile_default(targets=[provider_target(rate_currentness_ref="cur:other-rate")])

    def test_stale_target(self):
        with self.assertRaisesRegex(FirewallError, "TARGET_EVIDENCE_NOT_CURRENT"): provider_target(currentness_state="STALE")

    def test_local_needs_no_provider_target(self):
        recipe = make_recipe_plan(); currentness = make_currentness(); residual = make_residual(recipe); decision = make_router_decision(residual, currentness, disposition="LOCAL_ROUTE_READY", options=[local_option()], selected_route_id="local:present"); out = compile_default(recipe=recipe, residual=residual, currentness=currentness, decision=decision, targets=[]); self.assertEqual(out["disposition"], "RECIPIENT_ESCALATION_READY")

    def test_non_model_no_escalation(self):
        recipe = make_recipe_plan(); currentness = make_currentness(); residual = make_residual(recipe, kind="NON_MODEL_RESIDUAL"); decision = make_router_decision(residual, currentness, disposition="NO_ESCALATION_REQUIRED", options=[]); out = compile_default(recipe=recipe, residual=residual, currentness=currentness, decision=decision, targets=[]); self.assertEqual(out["disposition"], "NO_MODEL_ESCALATION")

    def test_router_evidence_required_propagates(self):
        recipe = make_recipe_plan(); currentness = make_currentness(); residual = make_residual(recipe); decision = make_router_decision(residual, currentness, disposition="EVIDENCE_REQUIRED", options=[]); out = compile_default(recipe=recipe, residual=residual, currentness=currentness, decision=decision, targets=[]); self.assertEqual(out["disposition"], "EVIDENCE_REQUIRED")

    def test_deterministic_firewall_digest(self):
        self.assertEqual(compile_default()["firewall_digest"], compile_default()["firewall_digest"])

    def test_owner_contract_refs(self):
        out = compile_default(); self.assertEqual(out["owner_contract_refs"]["zf07a"]["head"], "bf9de86246709003574143a847706a5c3cbc9afc"); self.assertEqual(out["owner_contract_refs"]["zf05a"]["blob"], "87a5bd403f1180c580a6352c36da9e326ce23711")


if __name__ == "__main__":
    unittest.main()
