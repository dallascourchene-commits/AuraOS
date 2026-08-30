from __future__ import annotations

import copy
import unittest

import recipe_distribution_binding as bridge
from test_recipe_distribution_binding import (
    admissible_receipt,
    make_recipe,
    manifest_for,
    plan_for,
)


class RecipeDistributionProvenanceSeparationTests(unittest.TestCase):
    def test_identical_recipe_bytes_do_not_collapse_distribution_provenance(self):
        recipe = make_recipe()
        plan = plan_for(recipe)

        first_manifest = manifest_for(recipe, plan)
        second_manifest = copy.deepcopy(first_manifest)
        second_manifest["artifact"]["origin_uri"] = (
            "https://mirror.example.test/recipes/creator.title-card.json"
        )
        second_manifest["source"]["source_generation"] = "repo-gen-2"
        second_manifest["signer"]["key_generation"] = "key-gen-2"
        second_manifest["manifest_id"] = bridge.manifest_id_from_view(second_manifest)

        first = bridge.compile_recipe_distribution_binding(
            recipe=recipe,
            recipe_plan=plan,
            distribution_manifest=first_manifest,
        )
        second = bridge.compile_recipe_distribution_binding(
            recipe=recipe,
            recipe_plan=plan,
            distribution_manifest=second_manifest,
        )

        # Content identity is reusable; distribution provenance is not.
        self.assertEqual(recipe.digest, first.recipe_digest)
        self.assertEqual(first.recipe_digest, second.recipe_digest)
        self.assertNotEqual(first.manifest_id, second.manifest_id)
        self.assertNotEqual(first.binding_digest, second.binding_digest)

        first_receipt = admissible_receipt(first)
        second_receipt = admissible_receipt(second)
        first_admission = bridge.verify_trusted_recipe_distribution(
            binding=first,
            trusted_distribution_receipt_resolver=lambda _: first_receipt,
        )
        second_admission = bridge.verify_trusted_recipe_distribution(
            binding=second,
            trusted_distribution_receipt_resolver=lambda _: second_receipt,
        )
        self.assertNotEqual(first_admission["admission_id"], second_admission["admission_id"])

    def test_receipt_from_other_distribution_chain_cannot_cross_bindings(self):
        recipe = make_recipe()
        plan = plan_for(recipe)
        first_manifest = manifest_for(recipe, plan)
        second_manifest = copy.deepcopy(first_manifest)
        second_manifest["signer"]["key_id"] = "key:mirror"
        second_manifest["manifest_id"] = bridge.manifest_id_from_view(second_manifest)

        first = bridge.compile_recipe_distribution_binding(
            recipe=recipe,
            recipe_plan=plan,
            distribution_manifest=first_manifest,
        )
        second = bridge.compile_recipe_distribution_binding(
            recipe=recipe,
            recipe_plan=plan,
            distribution_manifest=second_manifest,
        )
        wrong_receipt = admissible_receipt(first)
        with self.assertRaises(bridge.RecipeDistributionError) as ctx:
            bridge.verify_trusted_recipe_distribution(
                binding=second,
                trusted_distribution_receipt_resolver=lambda _: wrong_receipt,
            )
        self.assertEqual("DISTRIBUTION_ADMISSION_MANIFEST_MISMATCH", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
