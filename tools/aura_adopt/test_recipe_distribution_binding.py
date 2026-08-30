from __future__ import annotations

import copy
import unittest

import arena_recipe as recipe
import recipe_distribution_binding as bridge


def make_recipe(*, redistribute="ALLOWED", effect_ceiling="NONE", attribution=True):
    return recipe.ArenaRecipe(
        recipe_id="creator.title-card",
        version="1.0.0",
        purpose="Render a deterministic local title card",
        publisher_ref="publisher:aura",
        source=recipe.BoundRef("source:zf01", "a" * 64, "source-gen-1", "CURRENT"),
        capabilities=(
            recipe.BoundRef("capability:canvas2d", "b" * 64, "cap-gen-1", "CURRENT"),
            recipe.BoundRef("capability:png-export", "c" * 64, "cap-gen-1", "CURRENT"),
        ),
        assets=(recipe.BoundRef("asset:title-layout", "d" * 64, "asset-gen-1", "CURRENT"),),
        parameters={"title": "hello"},
        constraints={"network": False},
        attribution=(
            (recipe.Attribution("contributor:zf01", "author", "contribution:recipe"),)
            if attribution else ()
        ),
        rights=recipe.RightsEnvelope(
            use="ALLOWED",
            modify="ALLOWED",
            redistribute=redistribute,
            commercial="RESTRICTED",
            attribution_required=True,
            license_ref="license:aura-recipe",
        ),
        effect_ceiling=effect_ceiling,
    )


def plan_for(r):
    refs = (r.source, *r.capabilities, *r.assets)
    evidence = {
        item.ref: recipe.BindingEvidence(item.digest, item.source_generation, "CURRENT")
        for item in refs
    }
    return recipe.compile_recipe_plan(r, current_bindings=evidence)


def manifest_for(r, p, **artifact_overrides):
    artifact = {
        "artifact_id": r.recipe_id,
        "version": r.version,
        "kind": "ARENA_RECIPE",
        "sha256_hex": r.digest,
        "size_bytes": len(r.export_json().encode("utf-8")),
        "origin_uri": "https://example.test/recipes/creator.title-card.json",
        "channel": "RECIPE",
        "capability_ids": list(p["capability_refs"]),
        "required_permissions": [],
        "optional_permissions": [],
    }
    artifact.update(artifact_overrides)
    row = {
        "artifact": artifact,
        "source": {
            "source_ref": "repo:aura-adopt",
            "source_generation": "repo-gen-1",
            "source_currentness_ref": "current:1",
            "source_digest_sha256": "e" * 64,
        },
        "signer": {
            "signer_id": "signer:aura",
            "key_id": "key:1",
            "key_generation": "key-gen-1",
            "algorithm": "ED25519",
        },
        "supersedes_manifest_id": None,
        "rollback_of_manifest_id": None,
        "notes": [],
        "schema_version": "TrustedDistributionManifestV1",
        "manifest_id": "",
    }
    row["manifest_id"] = bridge.manifest_id_from_view(row)
    return row


def admissible_receipt(binding, **overrides):
    row = {
        "manifest_id": binding.manifest_id,
        "artifact_id": binding.distribution_artifact_id,
        "version": binding.distribution_artifact_version,
        "status": "ADMISSIBLE",
        "reasons": [],
        "added_required_permissions": [],
        "removed_required_permissions": [],
        "install_authorized": False,
        "update_authorized": False,
        "public_distribution_authorized": False,
        "effect_authorized": False,
        "execution_proven": False,
    }
    row.update(overrides)
    return row


class RecipeDistributionBindingTests(unittest.TestCase):
    def binding(self, *, r=None, p=None, manifest=None):
        r = r or make_recipe()
        p = p or plan_for(r)
        manifest = manifest or manifest_for(r, p)
        return bridge.compile_recipe_distribution_binding(
            recipe=r,
            recipe_plan=p,
            distribution_manifest=manifest,
        )

    def test_canonical_recipe_digest_is_distribution_artifact_digest(self):
        r = make_recipe()
        p = plan_for(r)
        m = manifest_for(r, p)
        b = self.binding(r=r, p=p, manifest=m)
        self.assertEqual(r.digest, m["artifact"]["sha256_hex"])
        self.assertEqual(r.digest, b.recipe_digest)
        self.assertEqual(len(r.export_json().encode("utf-8")), b.canonical_recipe_size_bytes)
        self.assertEqual("READY_FOR_TRUSTED_DISTRIBUTION_ADMISSION", b.status)
        self.assertFalse(b.install_authorized)
        self.assertFalse(b.public_distribution_authorized)
        self.assertFalse(b.effect_authorized)

    def test_distribution_capabilities_must_match_recipe_plan_exactly(self):
        r = make_recipe()
        p = plan_for(r)
        m = manifest_for(r, p, capability_ids=["capability:canvas2d"])
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            self.binding(r=r, p=p, manifest=m)
        self.assertEqual("RECIPE_DISTRIBUTION_CAPABILITY_MISMATCH", ctx.exception.code)

    def test_recipe_distribution_cannot_smuggle_required_or_optional_permissions(self):
        r = make_recipe()
        p = plan_for(r)
        for field in ("required_permissions", "optional_permissions"):
            m = manifest_for(r, p, **{field: ["NETWORK"]})
            with self.assertRaises(bridge.RecipeDistributionError) as ctx:
                self.binding(r=r, p=p, manifest=m)
            self.assertIn(ctx.exception.code, {"RECIPE_REQUIRED_PERMISSION_FORBIDDEN", "RECIPE_OPTIONAL_PERMISSION_FORBIDDEN"})

    def test_redistribution_must_be_explicitly_allowed(self):
        for state in ("UNKNOWN", "RESTRICTED", "DENIED"):
            r = make_recipe(redistribute=state)
            p = plan_for(r)
            with self.assertRaises(bridge.RecipeDistributionError) as ctx:
                self.binding(r=r, p=p, manifest=manifest_for(r, p))
            self.assertEqual("RECIPE_REDISTRIBUTION_NOT_ALLOWED", ctx.exception.code)

    def test_required_attribution_is_bound_inside_canonical_artifact(self):
        r = make_recipe(attribution=False)
        p = plan_for(r)
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            self.binding(r=r, p=p, manifest=manifest_for(r, p))
        self.assertEqual("REQUIRED_ATTRIBUTION_MISSING", ctx.exception.code)

    def test_manifest_cannot_point_at_old_recipe_after_attribution_changes(self):
        original = make_recipe()
        p0 = plan_for(original)
        old_manifest = manifest_for(original, p0)
        changed = recipe.ArenaRecipe(
            recipe_id=original.recipe_id,
            version=original.version,
            purpose=original.purpose,
            publisher_ref=original.publisher_ref,
            source=original.source,
            capabilities=original.capabilities,
            assets=original.assets,
            parameters=original.parameters,
            constraints=original.constraints,
            attribution=original.attribution + (recipe.Attribution("contributor:new", "reviewer"),),
            rights=original.rights,
            effect_ceiling=original.effect_ceiling,
        )
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            self.binding(r=changed, p=plan_for(changed), manifest=old_manifest)
        self.assertIn(ctx.exception.code, {"RECIPE_ARTIFACT_DIGEST_MISMATCH", "DISTRIBUTION_MANIFEST_ID_MISMATCH"})

    def test_forged_recipe_plan_digest_is_rejected(self):
        r = make_recipe()
        p = dict(plan_for(r))
        p["plan_digest"] = "f" * 64
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            self.binding(r=r, p=p, manifest=manifest_for(r, plan_for(r)))
        self.assertEqual("RECIPE_PLAN_DIGEST_MISMATCH", ctx.exception.code)

    def test_nonready_recipe_plan_is_rejected(self):
        r = make_recipe()
        p = dict(plan_for(r))
        p["status"] = "BINDING_EVIDENCE_REQUIRED"
        p["blockers"] = ["MISSING_BINDING:x"]
        p["plan_digest"] = bridge.recipe_plan_digest(p)
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            self.binding(r=r, p=p, manifest=manifest_for(r, plan_for(r)))
        self.assertEqual("RECIPE_PLAN_NOT_READY", ctx.exception.code)

    def test_manifest_identity_is_recomputed(self):
        r = make_recipe()
        p = plan_for(r)
        m = manifest_for(r, p)
        m["manifest_id"] = "tdm1:forged"
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            self.binding(r=r, p=p, manifest=m)
        self.assertEqual("DISTRIBUTION_MANIFEST_ID_MISMATCH", ctx.exception.code)

    def test_trusted_distribution_admission_unlocks_only_separate_effect_gate(self):
        b = self.binding()
        receipt = admissible_receipt(b)
        result = bridge.verify_trusted_recipe_distribution(
            binding=b,
            trusted_distribution_receipt_resolver=lambda manifest_id: copy.deepcopy(receipt),
        )
        self.assertEqual("RECIPE_PACKAGE_ADMISSIBLE_FOR_SEPARATE_DISTRIBUTION_EFFECT_GATE", result["decision"])
        self.assertFalse(result["install_authorized"])
        self.assertFalse(result["public_distribution_authorized"])
        self.assertFalse(result["effect_authorized"])
        self.assertFalse(result["execution_proven"])
        self.assertFalse(result["payment_authorized"])
        self.assertFalse(result["marketplace_listed"])

    def test_refused_distribution_receipt_does_not_cross_bridge(self):
        b = self.binding()
        receipt = admissible_receipt(b, status="REFUSED", reasons=["SIGNATURE_NOT_VERIFIED"])
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            bridge.verify_trusted_recipe_distribution(
                binding=b,
                trusted_distribution_receipt_resolver=lambda _: receipt,
            )
        self.assertEqual("DISTRIBUTION_NOT_ADMISSIBLE", ctx.exception.code)

    def test_distribution_receipt_cannot_launder_effect_authority(self):
        b = self.binding()
        receipt = admissible_receipt(b, public_distribution_authorized=True)
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            bridge.verify_trusted_recipe_distribution(
                binding=b,
                trusted_distribution_receipt_resolver=lambda _: receipt,
            )
        self.assertEqual("DISTRIBUTION_ADMISSION_AUTHORITY_WIDENING", ctx.exception.code)

    def test_recipe_effect_ceiling_never_turns_into_distribution_permission(self):
        r = make_recipe(effect_ceiling="EXTERNAL_EFFECT_PROPOSAL")
        p = plan_for(r)
        b = self.binding(r=r, p=p, manifest=manifest_for(r, p))
        receipt = admissible_receipt(b)
        result = bridge.verify_trusted_recipe_distribution(
            binding=b,
            trusted_distribution_receipt_resolver=lambda _: receipt,
        )
        self.assertEqual("EXTERNAL_EFFECT_PROPOSAL", result["effect_ceiling"])
        self.assertFalse(result["effect_authorized"])
        self.assertFalse(result["public_distribution_authorized"])


if __name__ == "__main__":
    unittest.main()
