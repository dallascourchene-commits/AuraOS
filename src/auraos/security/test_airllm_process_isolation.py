from __future__ import annotations

from contextlib import contextmanager
import os
import unittest

from airllm_process_isolation import (
    IsolatedObjectProxy,
    IsolationBoundaryError,
    RemoteInvocationError,
)


class FakeBoundary:
    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        return {"pid": os.getpid(), "trust_remote_code": kwargs.get("trust_remote_code")}


@contextmanager
def process_global_hard_false_patch():
    original = FakeBoundary.__dict__["from_pretrained"]

    def guarded(cls, *args, **kwargs):
        value = kwargs.get("trust_remote_code", False)
        if value is not False:
            raise RuntimeError("only literal False is admitted")
        kwargs["trust_remote_code"] = False
        return original.__func__(cls, *args, **kwargs)

    FakeBoundary.from_pretrained = classmethod(guarded)
    try:
        yield
    finally:
        FakeBoundary.from_pretrained = original


class IsolatedPatchedTarget:
    def __init__(self):
        self._membrane = process_global_hard_false_patch()
        self._membrane.__enter__()

    def probe(self, trust_remote_code=False):
        return FakeBoundary.from_pretrained("model", trust_remote_code=trust_remote_code)

    def generate(self, text="hello"):
        result = FakeBoundary.from_pretrained("model", trust_remote_code=False)
        return {
            "text": text,
            "pid": result["pid"],
            "trust_remote_code": result["trust_remote_code"],
        }

    def crash(self):
        raise ValueError("synthetic child failure")

    def unpickleable(self):
        return lambda value: value

    def close(self):
        if self._membrane is not None:
            membrane, self._membrane = self._membrane, None
            membrane.__exit__(None, None, None)


class AirLLMProcessIsolationTests(unittest.TestCase):
    def _proxy(self):
        return IsolatedObjectProxy(__name__, "IsolatedPatchedTarget", timeout_seconds=5.0)

    def test_01_spawned_child_has_distinct_pid(self):
        with self._proxy() as proxy:
            self.assertEqual(proxy.receipt.parent_pid, os.getpid())
            self.assertNotEqual(proxy.receipt.child_pid, os.getpid())
            self.assertEqual(proxy.receipt.start_method, "spawn")
            self.assertEqual(len(proxy.receipt.worker_nonce_root), 64)
            self.assertEqual(len(proxy.receipt.factory_identity_root), 64)
            self.assertEqual(len(proxy.receipt.receipt_root), 64)

    def test_02_child_hard_false_membrane_remains_active(self):
        with self._proxy() as proxy:
            result = proxy.call("probe", False)
            self.assertIs(result["trust_remote_code"], False)
            self.assertEqual(result["pid"], proxy.receipt.child_pid)

    def test_03_child_rejects_true_without_mutating_parent(self):
        with self._proxy() as proxy:
            with self.assertRaises(RemoteInvocationError) as caught:
                proxy.call("probe", True)
            self.assertEqual(caught.exception.error_type, "RuntimeError")
            parent = FakeBoundary.from_pretrained("model", trust_remote_code=True)
            self.assertIs(parent["trust_remote_code"], True)
            self.assertEqual(parent["pid"], os.getpid())

    def test_04_parent_bystander_is_unaffected_while_child_patch_is_live(self):
        with self._proxy() as proxy:
            for value in (True, None, "yes", 1):
                with self.subTest(value=value):
                    parent = FakeBoundary.from_pretrained("unrelated", trust_remote_code=value)
                    self.assertEqual(parent["trust_remote_code"], value)
                    self.assertEqual(parent["pid"], os.getpid())
            self.assertEqual(proxy.generate("ok")["text"], "ok")

    def test_05_generate_executes_in_child(self):
        with self._proxy() as proxy:
            result = proxy.generate("hello")
            self.assertEqual(result["text"], "hello")
            self.assertEqual(result["pid"], proxy.receipt.child_pid)
            self.assertIs(result["trust_remote_code"], False)

    def test_06_private_method_names_fail_closed_in_parent(self):
        with self._proxy() as proxy:
            with self.assertRaises(IsolationBoundaryError):
                proxy.call("_secret")
            with self.assertRaises(IsolationBoundaryError):
                proxy.call("not-valid!")

    def test_07_missing_method_fails_closed_without_child_exception_pickle(self):
        with self._proxy() as proxy:
            with self.assertRaises(RemoteInvocationError) as caught:
                proxy.call("missing")
            self.assertEqual(caught.exception.error_type, "IsolationBoundaryError")

    def test_08_child_exception_crosses_as_sanitized_metadata(self):
        with self._proxy() as proxy:
            with self.assertRaises(RemoteInvocationError) as caught:
                proxy.call("crash")
            self.assertEqual(caught.exception.error_type, "ValueError")
            self.assertEqual(caught.exception.remote_message, "synthetic child failure")

    def test_09_close_is_idempotent_and_reaps_child(self):
        proxy = self._proxy()
        child_pid = proxy.receipt.child_pid
        proxy.close()
        proxy.close()
        self.assertFalse(proxy._process.is_alive(), child_pid)
        with self.assertRaises(IsolationBoundaryError):
            proxy.generate("late")

    def test_10_unimportable_or_private_symbol_fails_closed(self):
        with self.assertRaises(RemoteInvocationError):
            IsolatedObjectProxy(__name__, "_PrivateTarget", timeout_seconds=2.0)

    def test_11_unserializable_call_fails_in_parent_without_killing_child(self):
        with self._proxy() as proxy:
            with self.assertRaises(IsolationBoundaryError):
                proxy.call("generate", lambda x: x)
            self.assertEqual(proxy.generate("still-alive")["text"], "still-alive")

    def test_12_unserializable_child_result_is_sanitized_and_session_survives(self):
        with self._proxy() as proxy:
            with self.assertRaises(RemoteInvocationError) as caught:
                proxy.call("unpickleable")
            self.assertEqual(caught.exception.error_type, "IsolationBoundaryError")
            self.assertEqual(proxy.generate("after-error")["text"], "after-error")


class _PrivateTarget:
    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
