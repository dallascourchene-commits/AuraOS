import json
import unittest

from tools.aura_adopt.arena_recipe import (
    ArenaRecipe,
    Attribution,
    BoundRef,
    RecipeError,
    RightsEnvelope,
    compile_recipe_plan,
    import_recipe_json,
    remix_recipe,
)


D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


class ArenaRecipeTests(unittest.TestCase):
    def base(self):
        return ArenaRecipe(
            recipe_id="creator.neon-caption.v1",
            version="1.0.0",
            purpose="Apply deterministic title/caption layout to a bounded creator clip",
            publisher_ref="creator:test-publisher",
            source=BoundRef("source:recipe-spec", D1, "gen-1", "CURRENT"),
            capabilities=(BoundRef("cap:caption-layout", D2, "gen-7", "CURRENT"),),
            assets=(BoundRef("asset:font-metrics", D3, "gen-2", "CURRENT"),),
            parameters={"title": {"text": "Top 5 Tips", "align": "center"}, "trim_ms": [0, 8000]},
            constraints={"output": {"aspect": "9:16"}, "privacy": "LOCAL_ONLY"},
            attribution=(Attribution("creator:test-publisher", "ORIGINAL_RECIPE_AUTHOR"),),
            rights=RightsEnvelope(
                use="ALLOWED",
                modify="RESTRICTED",
                redistribute="RESTRICTED",
                commercial="UNKNOWN",
                attribution_required=True,
                license_ref="license:recipe-test",
            ),
            effect_ceiling="LOCAL_DERIVATION_ONLY",
            compatibility={"client_schema": "AuraAdoptWebRouteV1"},
            reopen_conditions=("capability digest changes", "rights evidence changes"),
        )

    def test_export_import_roundtrip_is_stable(self):
        r = self.base()
        reopened = import_recipe_json(r.export_json())
        self.assertEqual(r.digest, reopened.digest)
        self.assertEqual(r.export_json(), reopened.export_json())

    def test_semantic_order_does_not_churn_digest(self):
        r = self.base()
        payload = json.loads(r.export_json())
        payload["capabilities"] = list(reversed(payload["capabilities"]))
        payload["assets"] = list(reversed(payload["assets"]))
        payload["attribution"] = list(reversed(payload["attribution"]))
        payload["parent_recipe_digests"] = list(reversed(payload["parent_recipe_digests"]))
        reopened = import_recipe_json(json.dumps(payload))
        self.assertEqual(r.digest, reopened.digest)

    def test_recursive_secret_field_is_rejected(self):
        with self.assertRaisesRegex(RecipeError, "FORBIDDEN_RECIPE_FIELD"):
            ArenaRecipe(
                **{**self.base().__dict__, "parameters": {"style": {"api_key": "nope"}}}
            )

    def test_executable_field_is_rejected(self):
        with self.assertRaisesRegex(RecipeError, "FORBIDDEN_RECIPE_FIELD"):
            ArenaRecipe(
                **{**self.base().__dict__, "constraints": {"script": "rm -rf /"}}
            )

    def test_remix_preserves_parent_lineage_and_changes_identity(self):
        parent = self.base()
        child = remix_recipe(
            parent,
            recipe_id="creator.neon-caption.remix.v1",
            version="1.0.1",
            publisher_ref="creator:remixer",
            parameter_patch={"trim_ms": [1000, 7000]},
            attribution_add=(Attribution("creator:remixer", "REMIX_AUTHOR"),),
        )
        self.assertIn(parent.digest, child.parent_recipe_digests)
        self.assertNotEqual(parent.digest, child.digest)
        self.assertIn(
            Attribution("creator:test-publisher", "ORIGINAL_RECIPE_AUTHOR"),
            child.attribution,
        )

    def test_remix_cannot_widen_rights(self):
        parent = self.base()
        widened = RightsEnvelope(
            use="ALLOWED",
            modify="ALLOWED",
            redistribute="ALLOWED",
            commercial="ALLOWED",
            attribution_required=True,
            license_ref="license:recipe-test",
        )
        with self.assertRaisesRegex(RecipeError, "RIGHTS_WIDENING_FORBIDDEN"):
            remix_recipe(
                parent,
                recipe_id="creator.bad-remix",
                version="2.0.0",
                publisher_ref="creator:remixer",
                rights=widened,
            )

    def test_remix_cannot_drop_required_attribution(self):
        parent = self.base()
        no_attr = RightsEnvelope(
            use="ALLOWED",
            modify="RESTRICTED",
            redistribute="RESTRICTED",
            commercial="UNKNOWN",
            attribution_required=False,
            license_ref="license:recipe-test",
        )
        with self.assertRaisesRegex(RecipeError, "ATTRIBUTION_REMOVAL_FORBIDDEN"):
            remix_recipe(
                parent,
                recipe_id="creator.bad-remix",
                version="2.0.0",
                publisher_ref="creator:remixer",
                rights=no_attr,
            )

    def test_remix_cannot_widen_effect_ceiling(self):
        parent = self.base()
        with self.assertRaisesRegex(RecipeError, "EFFECT_CEILING_WIDENING_FORBIDDEN"):
            remix_recipe(
                parent,
                recipe_id="creator.bad-effect",
                version="2.0.0",
                publisher_ref="creator:remixer",
                effect_ceiling="EXTERNAL_EFFECT_PROPOSAL",
            )

    def test_missing_binding_compiles_to_typed_residual_not_execution(self):
        r = self.base()
        plan = compile_recipe_plan(r, current_bindings={})
        self.assertEqual("BINDING_EVIDENCE_REQUIRED", plan["status"])
        self.assertTrue(any(x.startswith("MISSING_BINDING:") for x in plan["blockers"]))
        self.assertFalse(plan["effect_authorized"])
        self.assertFalse(plan["execution_proven"])

    def test_stale_binding_fails_closed(self):
        r = self.base()
        current = {
            "source:recipe-spec": D1,
            "cap:caption-layout": D1,
            "asset:font-metrics": D3,
        }
        plan = compile_recipe_plan(r, current_bindings=current)
        self.assertIn(
            "STALE_OR_MISMATCHED_BINDING:cap:caption-layout", plan["blockers"]
        )

    def test_current_exact_bindings_are_ready_for_admission_not_execution(self):
        r = self.base()
        current = {
            "source:recipe-spec": D1,
            "cap:caption-layout": D2,
            "asset:font-metrics": D3,
        }
        plan = compile_recipe_plan(r, current_bindings=current)
        self.assertEqual("READY_FOR_ADMISSION", plan["status"])
        for key in (
            "authority_owner_resolved",
            "effect_authorized",
            "execution_proven",
            "publication_authorized",
            "payment_authorized",
            "marketplace_listed",
        ):
            self.assertFalse(plan[key])

    def test_unknown_rights_remain_unknown(self):
        r = ArenaRecipe(**{**self.base().__dict__, "rights": RightsEnvelope()})
        self.assertEqual("UNKNOWN", r.rights.commercial)
        self.assertEqual("UNKNOWN", r.rights.use)

    def test_unknown_currentness_blocks_admission(self):
        r = ArenaRecipe(
            **{
                **self.base().__dict__,
                "capabilities": (BoundRef("cap:caption-layout", D2, "gen-7", "UNKNOWN"),),
            }
        )
        plan = compile_recipe_plan(
            r,
            current_bindings={
                "source:recipe-spec": D1,
                "cap:caption-layout": D2,
                "asset:font-metrics": D3,
            },
        )
        self.assertIn(
            "BOUND_REF_CURRENTNESS_UNKNOWN:cap:caption-layout", plan["blockers"]
        )

    def test_unknown_top_level_fields_are_rejected(self):
        raw = json.loads(self.base().export_json())
        raw["marketplace_rank"] = 1
        with self.assertRaisesRegex(RecipeError, "UNKNOWN_TOP_LEVEL_FIELDS"):
            import_recipe_json(json.dumps(raw))


if __name__ == "__main__":
    unittest.main()
