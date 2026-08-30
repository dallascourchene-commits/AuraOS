import json
import unittest

from tools.aura_adopt.arena_recipe import (
    ArenaRecipe, Attribution, BindingEvidence, BoundRef, RecipeError,
    RightsEnvelope, compile_recipe_plan, import_recipe_json, remix_recipe,
)

D1="1"*64; D2="2"*64; D3="3"*64

class ArenaRecipeTests(unittest.TestCase):
    def base(self):
        return ArenaRecipe(
            recipe_id="creator.neon-caption.v1", version="1.0.0",
            purpose="Apply deterministic title/caption layout to a bounded creator clip",
            publisher_ref="creator:test-publisher",
            source=BoundRef("source:recipe-spec",D1,"gen-1","CURRENT"),
            capabilities=(BoundRef("cap:caption-layout",D2,"gen-7","CURRENT"),),
            assets=(BoundRef("asset:font-metrics",D3,"gen-2","CURRENT"),),
            parameters={"title":{"text":"Top 5 Tips","align":"center"},"trim_ms":[0,8000]},
            constraints={"output":{"aspect":"9:16"},"privacy":"LOCAL_ONLY"},
            attribution=(Attribution("creator:test-publisher","ORIGINAL_RECIPE_AUTHOR"),),
            rights=RightsEnvelope("ALLOWED","RESTRICTED","RESTRICTED","UNKNOWN",True,"license:recipe-test"),
            effect_ceiling="LOCAL_DERIVATION_ONLY",
            compatibility={"client_schema":"AuraAdoptWebRouteV1"},
            reopen_conditions=("capability digest changes","rights evidence changes"),
        )
    def exact(self):
        return {"source:recipe-spec":BindingEvidence(D1,"gen-1","CURRENT"),
                "cap:caption-layout":BindingEvidence(D2,"gen-7","CURRENT"),
                "asset:font-metrics":BindingEvidence(D3,"gen-2","CURRENT")}

    def test_export_import_roundtrip_is_stable(self):
        r=self.base(); x=import_recipe_json(r.export_json()); self.assertEqual(r.digest,x.digest); self.assertEqual(r.export_json(),x.export_json())
    def test_semantic_order_does_not_churn_digest(self):
        r=self.base(); p=json.loads(r.export_json()); p["capabilities"]=list(reversed(p["capabilities"])); p["assets"]=list(reversed(p["assets"])); p["attribution"]=list(reversed(p["attribution"])); self.assertEqual(r.digest,import_recipe_json(json.dumps(p)).digest)
    def test_recursive_secret_field_is_rejected(self):
        with self.assertRaisesRegex(RecipeError,"FORBIDDEN_RECIPE_FIELD"): ArenaRecipe(**{**self.base().__dict__,"parameters":{"x":{"api_key":"no"}}})
    def test_executable_field_is_rejected(self):
        with self.assertRaisesRegex(RecipeError,"FORBIDDEN_RECIPE_FIELD"): ArenaRecipe(**{**self.base().__dict__,"constraints":{"script":"bad"}})
    def test_remix_preserves_parent_lineage(self):
        p=self.base(); c=remix_recipe(p,recipe_id="creator.remix.v1",version="1.0.1",publisher_ref="creator:remixer",parameter_patch={"trim_ms":[1,7000]},attribution_add=(Attribution("creator:remixer","REMIX_AUTHOR"),)); self.assertIn(p.digest,c.parent_recipe_digests); self.assertNotEqual(p.digest,c.digest); self.assertIn(p.attribution[0],c.attribution)
    def test_remix_cannot_widen_rights(self):
        with self.assertRaisesRegex(RecipeError,"RIGHTS_WIDENING_FORBIDDEN"): remix_recipe(self.base(),recipe_id="bad",version="2",publisher_ref="creator:x",rights=RightsEnvelope("ALLOWED","ALLOWED","ALLOWED","ALLOWED"))
    def test_remix_cannot_drop_attribution(self):
        with self.assertRaisesRegex(RecipeError,"ATTRIBUTION_REMOVAL_FORBIDDEN"): remix_recipe(self.base(),recipe_id="bad",version="2",publisher_ref="creator:x",rights=RightsEnvelope("ALLOWED","RESTRICTED","RESTRICTED","UNKNOWN",False,"license:recipe-test"))
    def test_remix_cannot_widen_effect(self):
        with self.assertRaisesRegex(RecipeError,"EFFECT_CEILING_WIDENING_FORBIDDEN"): remix_recipe(self.base(),recipe_id="bad",version="2",publisher_ref="creator:x",effect_ceiling="EXTERNAL_EFFECT_PROPOSAL")
    def test_missing_binding_is_typed_residual(self):
        p=compile_recipe_plan(self.base(),current_bindings={}); self.assertEqual("BINDING_EVIDENCE_REQUIRED",p["status"]); self.assertTrue(any(x.startswith("MISSING_BINDING:") for x in p["blockers"])); self.assertFalse(p["execution_proven"])
    def test_digest_mismatch_fails_closed(self):
        b=self.exact(); b["cap:caption-layout"]=BindingEvidence(D1,"gen-7","CURRENT"); p=compile_recipe_plan(self.base(),current_bindings=b); self.assertIn("BINDING_DIGEST_MISMATCH:cap:caption-layout",p["blockers"])
    def test_same_digest_wrong_generation_fails_closed(self):
        b=self.exact(); b["cap:caption-layout"]=BindingEvidence(D2,"gen-8","CURRENT"); p=compile_recipe_plan(self.base(),current_bindings=b); self.assertIn("BINDING_GENERATION_MISMATCH:cap:caption-layout",p["blockers"])
    def test_external_unknown_currentness_cannot_self_certify(self):
        b=self.exact(); b["cap:caption-layout"]=BindingEvidence(D2,"gen-7","UNKNOWN"); p=compile_recipe_plan(self.base(),current_bindings=b); self.assertIn("BINDING_NOT_CURRENT:cap:caption-layout:UNKNOWN",p["blockers"])
    def test_recipe_unknown_currentness_blocks(self):
        r=ArenaRecipe(**{**self.base().__dict__,"capabilities":(BoundRef("cap:caption-layout",D2,"gen-7","UNKNOWN"),)}); p=compile_recipe_plan(r,current_bindings=self.exact()); self.assertIn("RECIPE_BOUND_REF_NOT_CURRENT:cap:caption-layout:UNKNOWN",p["blockers"])
    def test_digest_only_binding_is_insufficient(self):
        p=compile_recipe_plan(self.base(),current_bindings={"source:recipe-spec":D1,"cap:caption-layout":D2,"asset:font-metrics":D3}); self.assertTrue(all(x.startswith("BINDING_EVIDENCE_INVALID:") for x in p["blockers"]))
    def test_exact_bindings_ready_only_for_admission(self):
        p=compile_recipe_plan(self.base(),current_bindings=self.exact()); self.assertEqual("READY_FOR_ADMISSION",p["status"]); [self.assertFalse(p[k]) for k in ("authority_owner_resolved","effect_authorized","execution_proven","publication_authorized","payment_authorized","marketplace_listed")]
    def test_unknown_rights_remain_unknown(self):
        r=ArenaRecipe(**{**self.base().__dict__,"rights":RightsEnvelope()}); self.assertEqual("UNKNOWN",r.rights.use); self.assertEqual("UNKNOWN",r.rights.commercial)
    def test_unknown_top_level_field_rejected(self):
        p=json.loads(self.base().export_json()); p["marketplace_rank"]=1
        with self.assertRaisesRegex(RecipeError,"UNKNOWN_TOP_LEVEL_FIELDS"): import_recipe_json(json.dumps(p))

if __name__ == "__main__": unittest.main()
