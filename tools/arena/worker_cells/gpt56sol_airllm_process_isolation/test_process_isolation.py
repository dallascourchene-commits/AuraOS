from __future__ import annotations

import os
from pathlib import Path
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from process_isolation import (
    IsolatedSessionProxy,
    IsolationProtocolError,
    IsolationTimeoutError,
    IsolationWorkerError,
)

HOST_TRANSFORMERS_BOUNDARY = "HOST_ORIGINAL"


class FakePatchedSession:
    def __init__(self, marker: str = "CHILD_PATCHED") -> None:
        global HOST_TRANSFORMERS_BOUNDARY
        HOST_TRANSFORMERS_BOUNDARY = marker
        self.marker = marker
        self.calls = 0

    def boundary(self) -> str:
        return HOST_TRANSFORMERS_BOUNDARY

    def generate_text(self, prompt: str) -> dict[str, object]:
        self.calls += 1
        return {"prompt": prompt, "marker": HOST_TRANSFORMERS_BOUNDARY, "calls": self.calls}

    def fail(self) -> None:
        raise RuntimeError("intentional child failure")

    def hang(self) -> None:
        time.sleep(2.0)

    def close(self) -> None:
        global HOST_TRANSFORMERS_BOUNDARY
        HOST_TRANSFORMERS_BOUNDARY = "CHILD_CLOSED"


class IsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        global HOST_TRANSFORMERS_BOUNDARY
        HOST_TRANSFORMERS_BOUNDARY = "HOST_ORIGINAL"

    def make_proxy(self, **kwargs):
        return IsolatedSessionProxy(
            factory_module="test_process_isolation",
            factory_qualname="FakePatchedSession",
            allowed_methods=("boundary", "generate_text", "fail", "hang"),
            **kwargs,
        )

    def test_01_child_pid_is_distinct_and_receipt_is_d0(self):
        with self.make_proxy() as proxy:
            self.assertIsInstance(proxy.child_pid, int)
            self.assertNotEqual(proxy.child_pid, os.getpid())
            self.assertEqual(proxy.receipt.authority, "D0")
            self.assertFalse(proxy.receipt.effect_authority)
            self.assertFalse(proxy.receipt.gate10)
            self.assertEqual(len(proxy.receipt.root), 64)

    def test_02_child_global_patch_is_invisible_to_host(self):
        with self.make_proxy() as proxy:
            self.assertEqual(proxy.call("boundary"), "CHILD_PATCHED")
            self.assertEqual(HOST_TRANSFORMERS_BOUNDARY, "HOST_ORIGINAL")

    def test_03_parallel_host_caller_never_observes_child_patch(self):
        observed = []
        stop = threading.Event()
        def host_reader():
            while not stop.is_set():
                observed.append(HOST_TRANSFORMERS_BOUNDARY)
        thread = threading.Thread(target=host_reader)
        thread.start()
        try:
            with self.make_proxy() as proxy:
                for i in range(50):
                    result = proxy.call("generate_text", f"p{i}")
                    self.assertEqual(result["marker"], "CHILD_PATCHED")
        finally:
            stop.set()
            thread.join()
        self.assertTrue(observed)
        self.assertEqual(set(observed), {"HOST_ORIGINAL"})

    def test_04_session_state_stays_in_child(self):
        with self.make_proxy() as proxy:
            self.assertEqual(proxy.call("generate_text", "a")["calls"], 1)
            self.assertEqual(proxy.call("generate_text", "b")["calls"], 2)
        self.assertEqual(HOST_TRANSFORMERS_BOUNDARY, "HOST_ORIGINAL")

    def test_05_private_or_unlisted_method_fails_before_ipc(self):
        with self.make_proxy() as proxy:
            with self.assertRaises(IsolationProtocolError):
                proxy.call("__dict__")
            with self.assertRaises(IsolationProtocolError):
                proxy.call("close")

    def test_06_non_json_init_payload_fails_closed(self):
        with self.assertRaises(IsolationProtocolError):
            self.make_proxy(init_kwargs={"bad": object()})

    def test_07_non_json_call_payload_fails_closed(self):
        with self.make_proxy() as proxy:
            with self.assertRaises(IsolationProtocolError):
                proxy.call("generate_text", object())

    def test_08_child_exception_is_nonreusable(self):
        proxy = self.make_proxy()
        with self.assertRaises(IsolationWorkerError):
            proxy.call("fail")
        with self.assertRaises(IsolationWorkerError):
            proxy.start()

    def test_09_timeout_terminates_child(self):
        proxy = self.make_proxy(call_timeout=0.1)
        with self.assertRaises(IsolationTimeoutError):
            proxy.call("hang")
        self.assertIsNone(proxy.child_pid)

    def test_10_close_is_idempotent_and_restores_host_state(self):
        proxy = self.make_proxy()
        proxy.start()
        proxy.close()
        proxy.close()
        self.assertEqual(HOST_TRANSFORMERS_BOUNDARY, "HOST_ORIGINAL")

    def test_11_invalid_factory_qualname_fails_closed(self):
        proxy = IsolatedSessionProxy(
            factory_module="test_process_isolation",
            factory_qualname="_PrivateFactory",
            allowed_methods=("boundary",),
        )
        with self.assertRaises(IsolationWorkerError):
            proxy.start()

    def test_12_start_is_idempotent_while_alive(self):
        proxy = self.make_proxy()
        try:
            proxy.start()
            pid = proxy.child_pid
            proxy.start()
            self.assertEqual(proxy.child_pid, pid)
        finally:
            proxy.close()

    def test_13_receipt_root_ignores_pid_and_timing(self):
        a = self.make_proxy()
        b = self.make_proxy()
        self.assertEqual(a.receipt.root, b.receipt.root)

    def test_14_spawn_is_the_only_start_method(self):
        self.assertEqual(self.make_proxy().receipt.start_method, "spawn")

    def test_15_method_allowlist_is_order_canonical(self):
        a = IsolatedSessionProxy(
            factory_module="test_process_isolation",
            factory_qualname="FakePatchedSession",
            allowed_methods=("generate_text", "boundary"),
        )
        b = IsolatedSessionProxy(
            factory_module="test_process_isolation",
            factory_qualname="FakePatchedSession",
            allowed_methods=("boundary", "generate_text"),
        )
        self.assertEqual(a.receipt.root, b.receipt.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
