import json
import unittest

from tools.aura_adopt.share_capsule import (
    Attribution,
    BindingEvidence,
    EvidenceRef,
    RouteEvidence,
    ShareCapsule,
    ShareCapsuleError,
    compile_share_launch,
    import_share_capsule_json,
    refer_capsule,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


class ShareCapsuleTests(unittest.TestCase):
    def base(self):
        return ShareCapsule(
            capsule_id="share.creator.titlecard.v1",
            version="1.0.0",
            creator_ref="creator:alice",
            purpose="Reproduce a deterministic local title-card workflow",
            source=EvidenceRef("source:zf01-witness", D1, "gen-1", "CURRENT"),
            recipe=EvidenceRef("recipe:title-card", D2, "gen-2", "CURRENT"),
            accepted_output=EvidenceRef("output:accepted-title-card", D3, "gen-3", "CURRENT"),
            distribution=EvidenceRef("distribution:web-witness", D4, "gen-4", "CURRENT"),
            entry_surface_preference="ZERO_INSTALL_WEB_PWA",
            attribution=(
                Attribution("creator:alice", "ORIGINAL_CREATOR"),
                Attribution("creator:bob", "RECIPE_AUTHOR"),
            ),
            constraints={"privacy": "NO_RECIPIENT_TRACKING", "mode": "RECIPE_REPRODUCTION_POINTER"},
            reopen_conditions=("distribution trust changes", "recipe generation changes"),
        )

    def bindings(self, trust="TRUST_READY"):
        return {
            "source:zf01-witness": BindingEvidence("source:zf01-witness", D1, "gen-1", "CURRENT"),
            "recipe:title-card": BindingEvidence("recipe:title-card", D2, "gen-2", "CURRENT"),
            "output:accepted-title-card": BindingEvidence("output:accepted-title-card", D3, "gen-3", "CURRENT"),
            "distribution:web-witness": BindingEvidence("distribution:web-witness", D4, "gen-4", "CURRENT", trust),
        }

    def route(self, availability="AVAILABLE", surface="ZERO_INSTALL_WEB_PWA", next_surface=None):
        return RouteEvidence(surface, availability, next_surface)

    def test_roundtrip_is_stable(self):
        r = self.base()
        reopened = import_share_capsule_json(r.export_json())
        self.assertEqual(r.digest, reopened.digest)
        self.assertEqual(r.export_json(), reopened.export_json())

    def test_attribution_order_does_not_churn_digest(self):
        r = self.base()
        raw = json.loads(r.export_json())
        raw["attribution"] = list(reversed(raw["attribution"]))
        reopened = import_share_capsule_json(json.dumps(raw))
        self.assertEqual(r.digest, reopened.digest)

    def test_original_creator_attribution_required(self):
        with self.assertRaisesRegex(ShareCapsuleError, "ORIGINAL_CREATOR_ATTRIBUTION_REQUIRED"):
            ShareCapsule(**{**self.base().__dict__, "attribution": (Attribution("creator:bob", "RECIPE_AUTHOR"),)})

    def test_sensitive_recipient_identity_rejected(self):
        with self.assertRaisesRegex(ShareCapsuleError, "FORBIDDEN_SHARE_FIELD"):
            ShareCapsule(**{**self.base().__dict__, "constraints": {"recipient": {"email": "x@example.com"}}})

    def test_secret_rejected(self):
        with self.assertRaisesRegex(ShareCapsuleError, "FORBIDDEN_SHARE_FIELD"):
            ShareCapsule(**{**self.base().__dict__, "constraints": {"api_key": "nope"}})

    def test_remote_url_rejected(self):
        with self.assertRaisesRegex(ShareCapsuleError, "REMOTE_URL_FORBIDDEN"):
            ShareCapsule(**{**self.base().__dict__, "constraints": {"link": "https://example.com/latest"}})

    def test_referral_preserves_creator_and_parent_digest(self):
        parent = self.base()
        child = refer_capsule(
            parent,
            capsule_id="share.creator.titlecard.ref1",
            version="1.0.1",
            referrer_ref="creator:carol",
        )
        self.assertEqual(parent.creator_ref, child.creator_ref)
        self.assertEqual(parent.digest, child.referrals[-1].parent_capsule_digest)
        self.assertIn(parent.digest, child.parent_capsule_digests)
        self.assertIn(Attribution("creator:alice", "ORIGINAL_CREATOR"), child.attribution)
        self.assertIn(Attribution("creator:carol", "REFERRER"), child.attribution)

    def test_self_referral_rejected(self):
        with self.assertRaisesRegex(ShareCapsuleError, "SELF_REFERRAL_FORBIDDEN"):
            refer_capsule(self.base(), capsule_id="x", version="1", referrer_ref="creator:alice")

    def test_duplicate_referrer_rejected(self):
        parent = refer_capsule(
            self.base(), capsule_id="x1", version="1", referrer_ref="creator:carol"
        )
        with self.assertRaisesRegex(ShareCapsuleError, "DUPLICATE_REFERRER_FORBIDDEN"):
            refer_capsule(parent, capsule_id="x2", version="2", referrer_ref="creator:carol")

    def test_referral_cannot_claim_payment(self):
        with self.assertRaisesRegex(ShareCapsuleError, "FORBIDDEN_SHARE_FIELD"):
            ShareCapsule(**{**self.base().__dict__, "constraints": {"commission": 0.1}})

    def test_exact_current_trusted_route_ready_for_user_action_only(self):
        plan = compile_share_launch(
            self.base(), current_bindings=self.bindings(), route_evidence=self.route()
        )
        self.assertEqual("READY_FOR_USER_ACTION", plan["status"])
        for key in (
            "network_fetch_authorized",
            "install_authorized",
            "execution_authorized",
            "execution_proven",
            "publication_authorized",
            "payment_authorized",
            "telemetry_authorized",
            "recipient_tracking_authorized",
            "provider_call_authorized",
            "adoption_success_proven",
        ):
            self.assertFalse(plan[key])

    def test_wrong_generation_blocks(self):
        bindings = self.bindings()
        bindings["recipe:title-card"] = BindingEvidence(
            "recipe:title-card", D2, "wrong-gen", "CURRENT"
        )
        plan = compile_share_launch(
            self.base(), current_bindings=bindings, route_evidence=self.route()
        )
        self.assertIn("BINDING_GENERATION_MISMATCH:recipe:title-card", plan["blockers"])

    def test_unknown_currentness_blocks(self):
        bindings = self.bindings()
        bindings["output:accepted-title-card"] = BindingEvidence(
            "output:accepted-title-card", D3, "gen-3", "UNKNOWN"
        )
        plan = compile_share_launch(
            self.base(), current_bindings=bindings, route_evidence=self.route()
        )
        self.assertIn(
            "BINDING_NOT_CURRENT:output:accepted-title-card:UNKNOWN", plan["blockers"]
        )

    def test_missing_binding_blocks(self):
        bindings = self.bindings()
        del bindings["recipe:title-card"]
        plan = compile_share_launch(
            self.base(), current_bindings=bindings, route_evidence=self.route()
        )
        self.assertIn("MISSING_BINDING:recipe:title-card", plan["blockers"])

    def test_distribution_trust_unknown_blocks(self):
        plan = compile_share_launch(
            self.base(), current_bindings=self.bindings("UNKNOWN"), route_evidence=self.route()
        )
        self.assertIn("DISTRIBUTION_TRUST_NOT_READY:UNKNOWN", plan["blockers"])

    def test_route_unavailable_has_typed_residual_and_next_surface(self):
        plan = compile_share_launch(
            self.base(),
            current_bindings=self.bindings(),
            route_evidence=self.route("UNAVAILABLE", next_surface="NATIVE_ANDROID_APK"),
        )
        self.assertIn("PREFERRED_ROUTE_UNAVAILABLE", plan["blockers"])
        self.assertEqual("NATIVE_ANDROID_APK", plan["next_surface"])
        self.assertEqual("ROUTE_OR_EVIDENCE_REQUIRED", plan["status"])

    def test_route_surface_mismatch_blocks(self):
        plan = compile_share_launch(
            self.base(),
            current_bindings=self.bindings(),
            route_evidence=self.route("AVAILABLE", surface="NATIVE_ANDROID_APK"),
        )
        self.assertIn("ROUTE_EVIDENCE_SURFACE_MISMATCH", plan["blockers"])

    def test_unknown_top_level_field_rejected(self):
        raw = json.loads(self.base().export_json())
        raw["conversion"] = True
        with self.assertRaisesRegex(ShareCapsuleError, "UNKNOWN_FIELDS"):
            import_share_capsule_json(json.dumps(raw))


if __name__ == "__main__":
    unittest.main()
