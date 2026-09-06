from __future__ import annotations

from hashlib import sha256
import os
import unittest

from airllm_isolated_native_service import (
    bind_current_isolation_surface,
    launch_isolated_native_airllm,
)
from airllm_process_isolation import IsolationBoundaryError, RemoteInvocationError
from test_airllm_process_isolation import FakeBoundary, process_global_hard_false_patch

SUBJECT = "5" * 40
SURFACE = "a" * 64


class FakeLoadedModel:
    def generate(self, text="hello"):
        return {"text": text, "pid": os.getpid()}


class FakeNativeWrapper:
    def __init__(
        self,
        model_allowlist,
        *,
        loader_source_allowlist,
        loader_package_source_allowlist,
        loader_package_required_paths=None,
        loader=None,
        transformers_module=None,
    ):
        self.model_allowlist = model_allowlist
        self.loader = loader
        self.transformers_module = transformers_module

    def load(self, model_id, model_path, *args, **kwargs):
        if kwargs.get("trust_remote_code", False) is not False:
            raise RuntimeError("unsafe caller widening")
        with process_global_hard_false_patch():
            observed = FakeBoundary.from_pretrained(model_path, trust_remote_code=False)
            if observed["pid"] != os.getpid():
                raise AssertionError("wrapper load escaped child")
        return FakeLoadedModel()


class FakeNoGenerateWrapper(FakeNativeWrapper):
    def load(self, model_id, model_path, *args, **kwargs):
        return object()


class NativeServiceTests(unittest.TestCase):
    def _launch(self, **overrides):
        values = dict(
            model_id="glm",
            model_path="/model",
            model_allowlist={"glm": ("0" * 64,)},
            loader_source_allowlist=("1" * 64,),
            loader_package_source_allowlist=("2" * 64,),
            subject_generation=SUBJECT,
            semantic_admission_surface_root=SURFACE,
            wrapper_symbol=(__name__, "FakeNativeWrapper"),
            timeout_seconds=5.0,
        )
        values.update(overrides)
        return launch_isolated_native_airllm(**values)

    def test_01_currentness_binding_is_deterministic(self):
        a = bind_current_isolation_surface(SUBJECT, SURFACE, "glm")
        b = bind_current_isolation_surface(SUBJECT, SURFACE, "glm")
        self.assertEqual(a, b)
        self.assertEqual(len(a.currentness_root), 64)

    def test_02_subject_generation_is_noncompensatory(self):
        base = bind_current_isolation_surface(SUBJECT, SURFACE, "glm")
        changed = bind_current_isolation_surface("6" * 40, SURFACE, "glm")
        self.assertNotEqual(base.currentness_root, changed.currentness_root)

    def test_03_semantic_surface_is_noncompensatory(self):
        base = bind_current_isolation_surface(SUBJECT, SURFACE, "glm")
        changed = bind_current_isolation_surface(SUBJECT, "b" * 64, "glm")
        self.assertNotEqual(base.currentness_root, changed.currentness_root)

    def test_04_model_identity_is_noncompensatory(self):
        base = bind_current_isolation_surface(SUBJECT, SURFACE, "glm")
        changed = bind_current_isolation_surface(SUBJECT, SURFACE, "other")
        self.assertNotEqual(base.currentness_root, changed.currentness_root)

    def test_05_malformed_currentness_fails_closed(self):
        bad = (("z" * 40, SURFACE), (SUBJECT, "x" * 64), ("5" * 39, SURFACE))
        for generation, surface in bad:
            with self.subTest(generation=generation[:4], surface=surface[:4]):
                with self.assertRaises(IsolationBoundaryError):
                    bind_current_isolation_surface(generation, surface, "glm")

    def test_06_real_load_lifetime_is_owned_by_child_proxy(self):
        with self._launch() as proxy:
            status = proxy.call("status")
            self.assertEqual(status["pid"], proxy.receipt.child_pid)
            self.assertNotEqual(status["pid"], os.getpid())
            self.assertEqual(status["subject_generation"], SUBJECT)
            self.assertEqual(status["semantic_admission_surface_root"], SURFACE)

    def test_07_generation_executes_in_child(self):
        with self._launch() as proxy:
            result = proxy.generate("hello")
            self.assertEqual(result["text"], "hello")
            self.assertEqual(result["pid"], proxy.receipt.child_pid)

    def test_08_parent_transformers_bystander_remains_unchanged(self):
        with self._launch() as proxy:
            parent = FakeBoundary.from_pretrained("other", trust_remote_code=True)
            self.assertIs(parent["trust_remote_code"], True)
            self.assertEqual(parent["pid"], os.getpid())
            self.assertEqual(proxy.generate("ok")["text"], "ok")

    def test_09_caller_remote_code_widening_fails_before_ready(self):
        with self.assertRaises(RemoteInvocationError):
            self._launch(load_kwargs={"trust_remote_code": True})

    def test_10_missing_generate_fails_closed(self):
        with self._launch(wrapper_symbol=(__name__, "FakeNoGenerateWrapper")) as proxy:
            with self.assertRaises(RemoteInvocationError):
                proxy.generate("x")

    def test_11_hs1000_stale_currentness_mutations_do_not_collide(self):
        base = bind_current_isolation_surface(SUBJECT, SURFACE, "glm").currentness_root
        collisions = 0
        for i in range(1000):
            mutated = sha256(f"surface-{i}".encode("ascii")).hexdigest()
            root = bind_current_isolation_surface(SUBJECT, mutated, "glm").currentness_root
            collisions += int(root == base)
        self.assertEqual(collisions, 0)

    def test_12_100k_compound_binding_states_are_stable_and_unique_enough(self):
        roots = set()
        for i in range(100_000):
            generation = sha256(f"generation-{i // 1000}".encode()).hexdigest()[:40]
            surface = sha256(f"surface-{i}".encode()).hexdigest()
            roots.add(bind_current_isolation_surface(generation, surface, "glm").currentness_root)
        self.assertEqual(len(roots), 100_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
