from dataclasses import asdict
from types import SimpleNamespace
import unittest

import airllm_runtime_hard_false as guardmod


def fake_transformers(*, include_optional: bool = False):
    class AutoConfig:
        calls = []

        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            cls.calls.append((args, dict(kwargs)))
            return dict(kwargs)

    class AutoTokenizer:
        calls = []

        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            cls.calls.append((args, dict(kwargs)))
            return dict(kwargs)

    class AutoModelBase:
        calls = []

        @classmethod
        def from_config(cls, *args, **kwargs):
            cls.calls.append((args, dict(kwargs)))
            return dict(kwargs)

    class AutoModelForCausalLM(AutoModelBase):
        pass

    class AutoModel(AutoModelBase):
        pass

    values = {
        "AutoConfig": AutoConfig,
        "AutoTokenizer": AutoTokenizer,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoModel": AutoModel,
    }
    if include_optional:
        class AutoModelForImageTextToText(AutoModelBase):
            pass

        class AutoModelForMultimodalLM(AutoModelBase):
            pass

        values.update(
            AutoModelForImageTextToText=AutoModelForImageTextToText,
            AutoModelForMultimodalLM=AutoModelForMultimodalLM,
        )
    return SimpleNamespace(**values)


class RuntimeHardFalseGuardTests(unittest.TestCase):
    def test_omitted_flag_is_injected_false_at_all_required_boundaries(self):
        module = fake_transformers()
        guard = guardmod.RuntimeHardFalseGuard(module).install()
        try:
            self.assertIs(
                False,
                module.AutoConfig.from_pretrained("model")["trust_remote_code"],
            )
            self.assertIs(
                False,
                module.AutoTokenizer.from_pretrained("model")["trust_remote_code"],
            )
            self.assertIs(
                False,
                module.AutoModelForCausalLM.from_config(object())["trust_remote_code"],
            )
            self.assertIs(
                False,
                module.AutoModel.from_config(object())["trust_remote_code"],
            )
            self.assertEqual(4, guard.receipt().protected_call_count)
        finally:
            guard.restore()

    def test_literal_false_passes_through_as_false(self):
        module = fake_transformers()
        with guardmod.RuntimeHardFalseGuard(module) as guard:
            result = module.AutoConfig.from_pretrained(
                "model", trust_remote_code=False, revision="abc"
            )
            self.assertIs(False, result["trust_remote_code"])
            self.assertEqual("abc", result["revision"])
            self.assertEqual(0, guard.receipt().rejected_widening_count)

    def test_true_is_rejected_before_underlying_loader_runs(self):
        module = fake_transformers()
        with guardmod.RuntimeHardFalseGuard(module) as guard:
            with self.assertRaisesRegex(
                guardmod.AirLLMRemoteCodeWideningRejected,
                "AIRLLM_REMOTE_CODE_WIDENING_REJECTED:AutoConfig.from_pretrained",
            ):
                module.AutoConfig.from_pretrained("model", trust_remote_code=True)
            self.assertEqual([], module.AutoConfig.calls)
            self.assertEqual(1, guard.receipt().rejected_widening_count)

    def test_nonliteral_values_are_rejected(self):
        for value in (None, 0, 1, "false", object()):
            with self.subTest(value=repr(value)):
                module = fake_transformers()
                with guardmod.RuntimeHardFalseGuard(module):
                    with self.assertRaises(guardmod.AirLLMRemoteCodeWideningRejected):
                        module.AutoTokenizer.from_pretrained(
                            "model", trust_remote_code=value
                        )
                self.assertEqual([], module.AutoTokenizer.calls)

    def test_optional_absent_factories_are_skipped_not_inferred(self):
        module = fake_transformers()
        with guardmod.RuntimeHardFalseGuard(module) as guard:
            receipt = guard.receipt()
            self.assertIn(
                "AutoModelForImageTextToText.from_config",
                receipt.skipped_optional_boundaries,
            )
            self.assertIn(
                "AutoModelForMultimodalLM.from_config",
                receipt.skipped_optional_boundaries,
            )

    def test_optional_present_factories_are_guarded(self):
        module = fake_transformers(include_optional=True)
        with guardmod.RuntimeHardFalseGuard(module):
            with self.assertRaises(guardmod.AirLLMRemoteCodeWideningRejected):
                module.AutoModelForImageTextToText.from_config(
                    object(), trust_remote_code=True
                )
            result = module.AutoModelForMultimodalLM.from_config(object())
            self.assertIs(False, result["trust_remote_code"])

    def test_missing_required_boundary_fails_closed_and_rolls_back(self):
        module = fake_transformers()
        original = module.AutoConfig.__dict__["from_pretrained"]
        boundaries = (
            guardmod.BoundarySpec("AutoConfig", "from_pretrained"),
            guardmod.BoundarySpec("MissingAutoClass", "from_config"),
        )
        with self.assertRaisesRegex(
            guardmod.AirLLMRuntimeGuardError,
            "AIRLLM_RUNTIME_BOUNDARY_OWNER_MISSING:MissingAutoClass",
        ):
            guardmod.RuntimeHardFalseGuard(
                module, boundaries=boundaries
            ).install()
        self.assertIs(original, module.AutoConfig.__dict__["from_pretrained"])
        result = module.AutoConfig.from_pretrained("model", trust_remote_code=True)
        self.assertIs(True, result["trust_remote_code"])

    def test_context_manager_restores_exact_own_and_inherited_descriptors(self):
        module = fake_transformers()
        config_descriptor = module.AutoConfig.__dict__["from_pretrained"]
        self.assertNotIn("from_config", module.AutoModelForCausalLM.__dict__)
        with guardmod.RuntimeHardFalseGuard(module):
            self.assertIsNot(config_descriptor, module.AutoConfig.__dict__["from_pretrained"])
            self.assertIn("from_config", module.AutoModelForCausalLM.__dict__)
        self.assertIs(config_descriptor, module.AutoConfig.__dict__["from_pretrained"])
        self.assertNotIn("from_config", module.AutoModelForCausalLM.__dict__)

    def test_context_manager_restores_after_exception(self):
        module = fake_transformers()
        original = module.AutoTokenizer.__dict__["from_pretrained"]
        with self.assertRaisesRegex(RuntimeError, "fixture failure"):
            with guardmod.RuntimeHardFalseGuard(module):
                raise RuntimeError("fixture failure")
        self.assertIs(original, module.AutoTokenizer.__dict__["from_pretrained"])

    def test_receipt_contains_no_loader_arguments(self):
        module = fake_transformers()
        with guardmod.RuntimeHardFalseGuard(module) as guard:
            module.AutoConfig.from_pretrained(
                "secret-model-path", trust_remote_code=False, token="secret-token"
            )
            encoded = repr(asdict(guard.receipt()))
            self.assertNotIn("secret-model-path", encoded)
            self.assertNotIn("secret-token", encoded)
            self.assertIn(guardmod.POLICY, encoded)

    def test_second_install_fails_closed(self):
        module = fake_transformers()
        guard = guardmod.RuntimeHardFalseGuard(module).install()
        try:
            with self.assertRaisesRegex(
                guardmod.AirLLMRuntimeGuardError,
                "AIRLLM_RUNTIME_HARD_FALSE_GUARD_ALREADY_ACTIVE",
            ):
                guard.install()
        finally:
            guard.restore()


if __name__ == "__main__":
    unittest.main()
