from __future__ import annotations

from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from airllm_json_process_isolation import IsolationProtocolError, IsolationWorkerError
from airllm_generation_bound_json_service import (
    _DEFAULT_WRAPPER_SYMBOL,
    bind_generation,
    launch_generation_bound_json_service,
)

HOST_MARKER = "HOST_ORIGINAL"
GEN_A = "a" * 40
GEN_B = "b" * 40
SURF_A = "1" * 64
SURF_B = "2" * 64


class TensorLike:
    def __init__(self, value):
        self.value = value
    def tolist(self):
        return self.value


class FakeLoaded:
    def generate(self, mode="json", value=None):
        if mode == "json":
            return {"pid": os.getpid(), "value": value}
        if mode == "tensor":
            return TensorLike([[1, 2], [3, 4]])
        if mode == "bad":
            return object()
        raise RuntimeError("synthetic generation failure")


class FakeWrapper:
    def __init__(self, *args, **kwargs):
        global HOST_MARKER
        HOST_MARKER = "CHILD_WRAPPER_ACTIVE"
    def load(self, model_id, model_path, *args, **kwargs):
        return FakeLoaded()


class GenerationBoundJsonServiceTests(unittest.TestCase):
    def setUp(self):
        global HOST_MARKER
        HOST_MARKER = "HOST_ORIGINAL"

    def wrapper(self):
        return ["test_airllm_generation_bound_json_service", "FakeWrapper"]

    def launch(self, **overrides):
        kwargs = dict(
            model_id="m",
            model_path="/tmp/model",
            model_allowlist={"m": ["3" * 64]},
            loader_source_allowlist=["4" * 64],
            loader_package_source_allowlist=["5" * 64],
            subject_generation=GEN_A,
            semantic_admission_surface_root=SURF_A,
            wrapper_symbol=self.wrapper(),
            timeout_seconds=5.0,
        )
        kwargs.update(overrides)
        return launch_generation_bound_json_service(**kwargs)

    def test_01_binding_is_deterministic(self):
        a = bind_generation(GEN_A, SURF_A, "m", self.wrapper())
        b = bind_generation(GEN_A, SURF_A, "m", tuple(self.wrapper()))
        self.assertEqual(a, b)
        self.assertEqual(len(a.currentness_root), 64)

    def test_02_generation_and_surface_movement_change_root(self):
        base = bind_generation(GEN_A, SURF_A, "m", self.wrapper()).currentness_root
        self.assertNotEqual(base, bind_generation(GEN_B, SURF_A, "m", self.wrapper()).currentness_root)
        self.assertNotEqual(base, bind_generation(GEN_A, SURF_B, "m", self.wrapper()).currentness_root)

    def test_03_default_wrapper_is_package_stable(self):
        self.assertEqual(_DEFAULT_WRAPPER_SYMBOL[0], "auraos.security.airllm_native_compat_wrapper")

    def test_04_child_binding_is_exact_and_host_wrapper_state_is_unchanged(self):
        with self.launch() as proxy:
            status = proxy.call("status")
            self.assertEqual(status["pid"], proxy.child_pid)
            self.assertEqual(status["subject_generation"], GEN_A)
            self.assertEqual(status["semantic_admission_surface_root"], SURF_A)
            self.assertEqual(HOST_MARKER, "HOST_ORIGINAL")

    def test_05_generate_json_runs_in_child(self):
        with self.launch() as proxy:
            result = proxy.call("generate_json", {"args": [], "kwargs": {"mode": "json", "value": "x"}})
            self.assertEqual(result["value"], "x")
            self.assertEqual(result["pid"], proxy.child_pid)
            self.assertEqual(HOST_MARKER, "HOST_ORIGINAL")

    def test_06_tensor_like_results_are_normalized_to_json_lists(self):
        with self.launch() as proxy:
            result = proxy.call("generate_json", {"args": [], "kwargs": {"mode": "tensor"}})
            self.assertEqual(result, [[1, 2], [3, 4]])

    def test_07_non_json_result_poison_worker(self):
        proxy = self.launch()
        with self.assertRaises(IsolationWorkerError):
            proxy.call("generate_json", {"args": [], "kwargs": {"mode": "bad"}})
        with self.assertRaises(IsolationWorkerError):
            proxy.start()

    def test_08_child_generation_exception_poison_worker(self):
        proxy = self.launch()
        with self.assertRaises(IsolationWorkerError):
            proxy.call("generate_json", {"args": [], "kwargs": {"mode": "boom"}})
        with self.assertRaises(IsolationWorkerError):
            proxy.start()

    def test_09_capability_allowlist_denies_other_public_methods(self):
        with self.launch() as proxy:
            with self.assertRaises(IsolationProtocolError):
                proxy.call("close")
            with self.assertRaises(IsolationProtocolError):
                proxy.call("other")

    def test_10_malformed_generation_and_surface_fail_closed(self):
        for generation in ("A" * 40, "a" * 39, ""):
            with self.subTest(generation=generation), self.assertRaises(IsolationProtocolError):
                bind_generation(generation, SURF_A, "m", self.wrapper())
        with self.assertRaises(IsolationProtocolError):
            bind_generation(GEN_A, "x" * 64, "m", self.wrapper())

    def test_11_non_json_load_config_fails_before_worker_start(self):
        with self.assertRaises(IsolationProtocolError):
            self.launch(load_kwargs={"bad": object()})

    def test_12_wrapper_identity_is_part_of_currentness(self):
        a = bind_generation(GEN_A, SURF_A, "m", self.wrapper()).currentness_root
        b = bind_generation(GEN_A, SURF_A, "m", ["test_airllm_generation_bound_json_service", "FakeLoaded"]).currentness_root
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
