import random
import unittest
from hashlib import sha256
from itertools import product
from pathlib import Path

from training_admission import *

R = lambda s: sha256(s.encode()).hexdigest()
REPO = Path(__file__).resolve().parents[4] / ".awj032_airllm_upstream_fixture"


def man(
    fam="qwen3_5",
    trainer="AirLLMLoRA",
    targets=("layers.0.q_proj", "layers.0.v_proj"),
    keys=("layers.0.q_proj.lora_A", "layers.0.q_proj.lora_B"),
):
    return AdapterManifest(
        R("base"), R("config"), R("tok"), R("runtime"), AIRLLM_COMMIT,
        fam, trainer, tuple(targets), 16, 32, False,
        tuple(keys), tuple(R(k) for k in keys),
    )


def good(source, m=None, **kw):
    m = m or man()
    params = dict(
        source=source,
        manifest=m,
        observed_base_checkpoint_root=m.base_checkpoint_root,
        observed_config_root=m.base_config_root,
        observed_tokenizer_root=m.tokenizer_root,
        observed_runtime_root=m.runtime_root,
        observed_target_paths=set(m.target_paths),
        provided_adapter_keys=set(m.adapter_keys),
    )
    params.update(kw)
    return admit(**params)


class TrainingAdmissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REPO.exists():
            raise unittest.SkipTest(
                "exact AirLLM fixture absent; clone commit 55e435087d951da8c25ab3672e969025241a398e to .awj032_airllm_upstream_fixture"
            )
        cls.source = audit_source(REPO, AIRLLM_COMMIT)

    def test_source_exact(self):
        self.assertTrue(self.source.partial_load_guard_required)
        self.assertTrue(self.source.provenance_envelope_required)

    def test_source_commit_drift(self):
        with self.assertRaises(ValueError):
            audit_source(REPO, "0" * 40)

    def test_glm_hold(self):
        self.assertEqual(good(self.source, man("glm_moe_dsa", "AirLLMLoRA")).action, "HOLD_PORT_REQUIRED")

    def test_qwen35(self):
        self.assertEqual(good(self.source).action, "ADMIT_D0_ADAPTER_LOAD")

    def test_qwen4(self):
        self.assertEqual(good(self.source, man("qwen4_exp", "AirLLMLoRAQwen4Exp")).action, "ADMIT_D0_ADAPTER_LOAD")

    def test_wrong_trainer(self):
        self.assertEqual(good(self.source, man(trainer="AirLLMLoRAQwen4Exp")).action, "HOLD_FAMILY_MISMATCH")

    def test_base_drift(self):
        self.assertEqual(good(self.source, observed_base_checkpoint_root=R("x")).action, "HOLD_REBIND_REQUIRED")

    def test_config_drift(self):
        self.assertEqual(good(self.source, observed_config_root=R("x")).action, "HOLD_REBIND_REQUIRED")

    def test_tokenizer_drift(self):
        self.assertEqual(good(self.source, observed_tokenizer_root=R("x")).action, "HOLD_REBIND_REQUIRED")

    def test_runtime_drift(self):
        self.assertEqual(good(self.source, observed_runtime_root=R("x")).action, "HOLD_REBIND_REQUIRED")

    def test_target_missing(self):
        self.assertEqual(good(self.source, observed_target_paths={"layers.0.q_proj"}).action, "HOLD_TARGET_TOPOLOGY_MISMATCH")

    def test_target_extra(self):
        self.assertEqual(
            good(self.source, observed_target_paths={"layers.0.q_proj", "layers.0.v_proj", "layers.1.q_proj"}).action,
            "HOLD_TARGET_TOPOLOGY_MISMATCH",
        )

    def test_key_missing(self):
        self.assertEqual(good(self.source, provided_adapter_keys={"layers.0.q_proj.lora_A"}).action, "HOLD_ADAPTER_KEY_COVERAGE")

    def test_key_extra(self):
        self.assertEqual(
            good(self.source, provided_adapter_keys=set(man().adapter_keys) | {"evil.lora_A"}).action,
            "HOLD_ADAPTER_KEY_COVERAGE",
        )

    def test_duplicate_key_reject(self):
        with self.assertRaises(ValueError):
            man(keys=("x", "x"))

    def test_duplicate_target_reject(self):
        with self.assertRaises(ValueError):
            man(targets=("x", "x"))

    def test_bad_value_root(self):
        m = man()
        with self.assertRaises(ValueError):
            AdapterManifest(
                m.base_checkpoint_root, m.base_config_root, m.tokenizer_root, m.runtime_root,
                AIRLLM_COMMIT, m.family, m.trainer_class, m.target_paths, 16, 32, False,
                m.adapter_keys, ("bad", "bad"),
            )

    def test_hyperparams(self):
        m = man()
        with self.assertRaises(ValueError):
            AdapterManifest(
                m.base_checkpoint_root, m.base_config_root, m.tokenizer_root, m.runtime_root,
                AIRLLM_COMMIT, m.family, m.trainer_class, m.target_paths, 0, 32, False,
                m.adapter_keys, m.adapter_value_roots,
            )

    def test_manifest_identity_changes_base(self):
        a = man()
        b = AdapterManifest(
            R("other"), a.base_config_root, a.tokenizer_root, a.runtime_root, AIRLLM_COMMIT,
            a.family, a.trainer_class, a.target_paths, a.lora_r, a.lora_alpha,
            a.packed_experts, a.adapter_keys, a.adapter_value_roots,
        )
        self.assertNotEqual(a.identity_root, b.identity_root)

    def test_manifest_identity_changes_runtime(self):
        a = man()
        b = AdapterManifest(
            a.base_checkpoint_root, a.base_config_root, a.tokenizer_root, R("other"), AIRLLM_COMMIT,
            a.family, a.trainer_class, a.target_paths, a.lora_r, a.lora_alpha,
            a.packed_experts, a.adapter_keys, a.adapter_value_roots,
        )
        self.assertNotEqual(a.identity_root, b.identity_root)

    def test_manifest_identity_changes_target(self):
        self.assertNotEqual(man().identity_root, man(targets=("layers.1.q_proj",)).identity_root)

    def test_manifest_identity_changes_adapter_value(self):
        a = man()
        roots = list(a.adapter_value_roots)
        roots[0] = R("changed")
        b = AdapterManifest(
            a.base_checkpoint_root, a.base_config_root, a.tokenizer_root, a.runtime_root, AIRLLM_COMMIT,
            a.family, a.trainer_class, a.target_paths, a.lora_r, a.lora_alpha,
            a.packed_experts, a.adapter_keys, tuple(roots),
        )
        self.assertNotEqual(a.identity_root, b.identity_root)

    def test_omega8_exact(self):
        self.assertTrue(omega8((1,) * 8))

    def test_omega8_invalids(self):
        for bits in product((0, 1), repeat=8):
            if bits != (1,) * 8:
                self.assertFalse(omega8(bits))

    def test_random_key_fuzz(self):
        rng = random.Random(42)
        expected = set(man().adapter_keys)
        for _ in range(5000):
            provided = set(expected)
            mode = rng.randrange(3)
            if mode == 0:
                provided.discard(rng.choice(tuple(expected)))
            elif mode == 1:
                provided.add(f"x{rng.randrange(10000)}.lora_A")
            ok, _ = check_key_coverage(expected, provided)
            self.assertEqual(ok, provided == expected)

    def test_random_identity_fuzz(self):
        rng = random.Random(7)
        fields = {
            "base": "observed_base_checkpoint_root",
            "config": "observed_config_root",
            "tok": "observed_tokenizer_root",
            "runtime": "observed_runtime_root",
        }
        for _ in range(5000):
            key = rng.choice(tuple(fields))
            kwargs = {fields[key]: R(str(rng.random()))}
            self.assertEqual(good(self.source, **kwargs).action, "HOLD_REBIND_REQUIRED")


if __name__ == "__main__":
    unittest.main()
