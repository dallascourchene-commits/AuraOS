import unittest

from zf05b_zf07c_share_escalation_firewall import (
    EscalationDecisionProjectionV1,
    FirewallDisposition,
    FirewallError,
    RecipientCapabilityResidualV1,
    ResidualKind,
    ScopedEvidenceV1,
    ShareLaunchProjectionV1,
    compile_share_escalation_firewall,
)

D = "a" * 64
E = "b" * 64
F = "c" * 64
G = "d" * 64
H = "e" * 64
I = "f" * 64

def ev(ref, digest, scope, current="CURRENT"):
    return ScopedEvidenceV1(
        ref=ref,
        digest=digest,
        source_generation=f"gen:{ref}",
        currentness_ref=f"cur:{ref}",
        currentness_state=current,
        scope=scope,
    )

SHARE_EVIDENCE = (
    ev("source-evidence", "1"*64, "SHARE_SOURCE"),
    ev("recipe-evidence", "2"*64, "SHARE_RECIPE"),
    ev("distribution-evidence", "3"*64, "SHARE_DISTRIBUTION"),
    ev("creator-attribution", "4"*64, "SHARE_ATTRIBUTION"),
)
DERIVATION = ev("recipient-derivation", F, "RECIPIENT_CAPABILITY_PLAN")
PROVIDER_EVIDENCE = (
    ev("provider-current", H, "PROVIDER_CATALOG"),
    ev("rate-current", I, "RATE_CATALOG"),
)

def share(**kw):
    data = dict(
        capsule_digest=D,
        capsule_id="capsule-1",
        status="READY_FOR_USER_ACTION",
        creator_ref="creator:alice",
        evidence=SHARE_EVIDENCE,
        required_user_actions=("OPEN_ENTRY_SURFACE", "CONFIRM_REPRODUCTION_INTENT"),
    )
    data.update(kw)
    return ShareLaunchProjectionV1(**data)

def residual(**kw):
    data = dict(
        residual_id="residual-1",
        recipe_plan_digest=E,
        capability_ref="cap:model-inference",
        residual_kind=ResidualKind.MODEL_INFERENCE_REQUIRED,
        unresolved=True,
        derivation_origin="RECIPIENT_CAPABILITY_PLAN",
        derivation_evidence=DERIVATION,
    )
    data.update(kw)
    return RecipientCapabilityResidualV1(**data)

def escalation(**kw):
    data = dict(
        residual_id="residual-1",
        capability_ref="cap:model-inference",
        recipe_plan_digest=E,
        disposition="USER_CHOICE_REQUIRED",
        decision_digest=G,
        selected_route_id=None,
        earned_action_classes=("EXPLICIT_REMOTE_EXECUTION_CONSENT", "REQUEST_CREDENTIAL_VIA_SECURE_OWNER"),
        provider_evidence=PROVIDER_EVIDENCE,
    )
    data.update(kw)
    return EscalationDecisionProjectionV1(**data)

class FirewallTests(unittest.TestCase):
    def test_happy_path_preserves_actions_without_authorizing_effects(self):
        out = compile_share_escalation_firewall(share(), residual(), escalation())
        self.assertEqual(out.disposition, FirewallDisposition.RECIPIENT_ESCALATION_READY)
        self.assertEqual(out.presentable_action_classes, (
            "EXPLICIT_REMOTE_EXECUTION_CONSENT",
            "REQUEST_CREDENTIAL_VIA_SECURE_OWNER",
        ))
        self.assertFalse(out.provider_call_authorized)
        self.assertFalse(out.credential_authorized)
        self.assertFalse(out.network_authorized)
        self.assertFalse(out.provider_evidence_reused_from_share)

    def test_share_not_ready_blocks_escalation_presentation(self):
        out = compile_share_escalation_firewall(share(status="EVIDENCE_REQUIRED"), residual(), escalation())
        self.assertEqual(out.disposition, FirewallDisposition.SHARE_EVIDENCE_REQUIRED)
        self.assertEqual(out.presentable_action_classes, ())

    def test_non_model_residual_yields_no_escalation(self):
        r = residual(residual_kind=ResidualKind.NON_MODEL_RESIDUAL)
        e = escalation(disposition="NO_ESCALATION_REQUIRED", earned_action_classes=(), provider_evidence=())
        out = compile_share_escalation_firewall(share(), r, e)
        self.assertEqual(out.disposition, FirewallDisposition.NO_MODEL_ESCALATION)

    def test_resolved_residual_yields_no_escalation(self):
        r = residual(unresolved=False)
        e = escalation(disposition="NO_ESCALATION_REQUIRED", earned_action_classes=(), provider_evidence=())
        out = compile_share_escalation_firewall(share(), r, e)
        self.assertEqual(out.disposition, FirewallDisposition.NO_MODEL_ESCALATION)

    def test_share_cannot_mint_credential_action(self):
        with self.assertRaisesRegex(FirewallError, "SHARE_CANNOT_MINT_ESCALATION_ACTION"):
            share(required_user_actions=("REQUEST_CREDENTIAL_VIA_SECURE_OWNER",))

    def test_share_cannot_mint_model_residual_action(self):
        with self.assertRaisesRegex(FirewallError, "SHARE_CANNOT_MINT_ESCALATION_ACTION"):
            share(required_user_actions=("MODEL_INFERENCE_REQUIRED",))

    def test_residual_must_be_recipient_derived(self):
        with self.assertRaisesRegex(FirewallError, "RESIDUAL_MUST_BE_RECIPIENT_DERIVED"):
            residual(derivation_origin="SHARE_CAPSULE")

    def test_residual_derivation_must_be_current(self):
        stale = ev("recipient-stale", F, "RECIPIENT_CAPABILITY_PLAN", current="STALE")
        with self.assertRaisesRegex(FirewallError, "RECIPIENT_DERIVATION_NOT_CURRENT"):
            residual(derivation_evidence=stale)

    def test_share_ref_alias_cannot_derive_recipient_residual(self):
        alias = ev("recipe-evidence", "9"*64, "RECIPIENT_CAPABILITY_PLAN")
        with self.assertRaisesRegex(FirewallError, "SHARE_EVIDENCE_CANNOT_DERIVE_RECIPIENT_RESIDUAL"):
            compile_share_escalation_firewall(share(), residual(derivation_evidence=alias), escalation())

    def test_share_digest_alias_cannot_derive_recipient_residual(self):
        alias = ev("renamed-recipient-evidence", "2"*64, "RECIPIENT_CAPABILITY_PLAN")
        with self.assertRaisesRegex(FirewallError, "SHARE_EVIDENCE_CANNOT_DERIVE_RECIPIENT_RESIDUAL"):
            compile_share_escalation_firewall(share(), residual(derivation_evidence=alias), escalation())

    def test_share_ref_alias_cannot_satisfy_provider_evidence(self):
        alias = ev("distribution-evidence", "8"*64, "PROVIDER_CATALOG")
        with self.assertRaisesRegex(FirewallError, "SHARE_EVIDENCE_CANNOT_SATISFY_PROVIDER_EVIDENCE"):
            compile_share_escalation_firewall(share(), residual(), escalation(provider_evidence=(alias,)))

    def test_share_digest_alias_cannot_satisfy_provider_evidence(self):
        alias = ev("renamed-provider-evidence", "3"*64, "PROVIDER_CATALOG")
        with self.assertRaisesRegex(FirewallError, "SHARE_EVIDENCE_CANNOT_SATISFY_PROVIDER_EVIDENCE"):
            compile_share_escalation_firewall(share(), residual(), escalation(provider_evidence=(alias,)))

    def test_recipient_derivation_cannot_double_as_provider_evidence(self):
        alias = ev("provider-renamed", F, "PROVIDER_CATALOG")
        with self.assertRaisesRegex(FirewallError, "RECIPIENT_DERIVATION_CANNOT_SATISFY_PROVIDER_EVIDENCE"):
            compile_share_escalation_firewall(share(), residual(), escalation(provider_evidence=(alias,)))

    def test_provider_actions_require_provider_evidence(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_EVIDENCE_REQUIRED_FOR_ACTIONS"):
            escalation(provider_evidence=())

    def test_provider_evidence_must_be_current(self):
        stale = ev("provider-stale", H, "PROVIDER_CATALOG", current="STALE")
        with self.assertRaisesRegex(FirewallError, "PROVIDER_EVIDENCE_NOT_CURRENT"):
            escalation(provider_evidence=(stale,))

    def test_escalation_residual_must_match(self):
        with self.assertRaisesRegex(FirewallError, "ESCALATION_RESIDUAL_MISMATCH"):
            compile_share_escalation_firewall(share(), residual(), escalation(residual_id="residual-other"))

    def test_escalation_plan_must_match(self):
        with self.assertRaisesRegex(FirewallError, "ESCALATION_RECIPE_PLAN_MISMATCH"):
            compile_share_escalation_firewall(share(), residual(), escalation(recipe_plan_digest="e" * 64))

    def test_share_authority_widening_refused(self):
        with self.assertRaisesRegex(FirewallError, "SHARE_AUTHORITY_WIDENING"):
            share(provider_call_authorized=True)

    def test_prior_provider_effect_refused(self):
        with self.assertRaisesRegex(FirewallError, "ESCALATION_EFFECT_ALREADY_OCCURRED"):
            escalation(provider_call_made=True)

    def test_local_ready_cannot_have_actions(self):
        with self.assertRaisesRegex(FirewallError, "LOCAL_READY_CANNOT_HAVE_EARNED_ACTIONS"):
            escalation(disposition="LOCAL_ROUTE_READY")

    def test_local_ready_without_actions_is_presentable_zero_effect(self):
        e = escalation(disposition="LOCAL_ROUTE_READY", selected_route_id="local:present", earned_action_classes=(), provider_evidence=())
        out = compile_share_escalation_firewall(share(), residual(), e)
        self.assertEqual(out.disposition, FirewallDisposition.RECIPIENT_ESCALATION_READY)
        self.assertEqual(out.presentable_action_classes, ())

    def test_escalation_evidence_required_propagates(self):
        e = escalation(disposition="EVIDENCE_REQUIRED", earned_action_classes=(), provider_evidence=())
        out = compile_share_escalation_firewall(share(), residual(), e)
        self.assertEqual(out.disposition, FirewallDisposition.EVIDENCE_REQUIRED)
        self.assertEqual(out.presentable_action_classes, ())

    def test_deterministic_firewall_digest(self):
        a = compile_share_escalation_firewall(share(), residual(), escalation())
        b = compile_share_escalation_firewall(share(), residual(), escalation())
        self.assertEqual(a.firewall_digest, b.firewall_digest)

    def test_no_model_residual_cannot_carry_user_choice_escalation(self):
        r = residual(residual_kind=ResidualKind.NON_MODEL_RESIDUAL)
        with self.assertRaisesRegex(FirewallError, "ESCALATION_PRESENT_WITHOUT_MODEL_RESIDUAL"):
            compile_share_escalation_firewall(share(), r, escalation())

    def test_share_evidence_scope_must_be_share_scope(self):
        with self.assertRaisesRegex(FirewallError, "SHARE_EVIDENCE_SCOPE_INVALID"):
            share(evidence=(ev("bad-share", "7"*64, "MODEL_CATALOG"),))

    def test_provider_evidence_scope_must_be_provider_scope(self):
        with self.assertRaisesRegex(FirewallError, "PROVIDER_EVIDENCE_SCOPE_INVALID"):
            escalation(provider_evidence=(ev("bad-provider", "7"*64, "SHARE_SOURCE"),))

if __name__ == "__main__":
    unittest.main()
