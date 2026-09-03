import ast
import random
import unittest

import airllm_source_admission as a


class BindingMutationSoundnessTests(unittest.TestCase):
    def _codes(self, source: str) -> set[str]:
        tree = ast.parse(source, filename="air_llm/airllm/mutation_fixture.py")
        return {
            finding.code
            for finding in a._scan_trust_remote_code(
                tree, "air_llm/airllm/mutation_fixture.py"
            )
        }

    def assert_loader_fails_closed(self, source: str) -> None:
        codes = self._codes(source)
        self.assertIn("REMOTE_CODE_OPAQUE_LOADER_KWARGS", codes, (source, codes))

    def test_augassign_invalidates_stale_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'trust_'\n"
            "KEY += 'remote_code'\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_namedexpr_invalidates_stale_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "if (KEY := 'trust_remote_code'):\n"
            "    pass\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_loop_target_invalidates_stale_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "for KEY in ['trust_remote_code']:\n"
            "    pass\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_with_target_invalidates_stale_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "with context() as KEY:\n"
            "    pass\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_comprehension_target_invalidates_static_key_conservatively(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "[None for KEY in ['x']]\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_destructuring_assignment_invalidates_stale_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "KEY, other = ('trust_remote_code', 1)\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_multi_target_assignment_invalidates_stale_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "KEY = other = 'trust_remote_code'\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_function_parameter_shadow_invalidates_outer_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "def load(KEY):\n"
            "    opts = {KEY: True}\n"
            "    return model.from_pretrained('x', **opts)\n"
        )

    def test_import_alias_rebind_invalidates_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "import trust_remote_code as KEY\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_definition_rebind_invalidates_static_key(self):
        self.assert_loader_fails_closed(
            "KEY = 'revision'\n"
            "def KEY():\n"
            "    pass\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )

    def test_identical_modeled_rebinding_remains_foldable(self):
        codes = self._codes(
            "KEY = 'trust_remote_code'\n"
            "if feature_flag:\n"
            "    KEY = 'trust_remote_code'\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )
        self.assertIn("REMOTE_CODE_TRUE", codes)

    def test_stable_unrelated_key_remains_admitted_by_this_scanner(self):
        codes = self._codes(
            "KEY = 'revision'\n"
            "KEY = 'revision'\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', **opts)\n"
        )
        self.assertEqual(set(), codes)

    def test_explicit_false_still_dominates_opaque_mapping(self):
        codes = self._codes(
            "KEY = 'revision'\n"
            "for KEY in ['trust_remote_code']:\n"
            "    pass\n"
            "opts = {KEY: True}\n"
            "model.from_pretrained('x', trust_remote_code=False, **opts)\n"
        )
        self.assertNotIn("REMOTE_CODE_OPAQUE_LOADER_KWARGS", codes)

    def test_randomized_unmodeled_binding_forms_never_fail_open(self):
        rng = random.Random(31118)
        forms = ("aug", "walrus", "for", "destructuring", "multi", "parameter")
        for _ in range(5000):
            form = rng.choice(forms)
            harmless = rng.choice(("revision", "other"))
            if form == "aug":
                source = "KEY = 'trust_'\nKEY += 'remote_code'\n"
            elif form == "walrus":
                source = (
                    f"KEY = {harmless!r}\n"
                    "if (KEY := 'trust_remote_code'):\n"
                    "    pass\n"
                )
            elif form == "for":
                source = (
                    f"KEY = {harmless!r}\n"
                    "for KEY in ['trust_remote_code']:\n"
                    "    pass\n"
                )
            elif form == "destructuring":
                source = (
                    f"KEY = {harmless!r}\n"
                    "KEY, other = ('trust_remote_code', 1)\n"
                )
            elif form == "multi":
                source = (
                    f"KEY = {harmless!r}\n"
                    "KEY = other = 'trust_remote_code'\n"
                )
            else:
                source = (
                    f"KEY = {harmless!r}\n"
                    "def load(KEY):\n"
                    "    opts = {KEY: True}\n"
                    "    return model.from_pretrained('x', **opts)\n"
                )
                self.assert_loader_fails_closed(source)
                continue
            source += (
                "opts = {KEY: True}\n"
                "model.from_pretrained('x', **opts)\n"
            )
            self.assert_loader_fails_closed(source)


if __name__ == "__main__":
    unittest.main()
