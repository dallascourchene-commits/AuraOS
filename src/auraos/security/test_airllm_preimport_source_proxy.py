from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os
import tempfile
import unittest

from airllm_preimport_source_proxy import PreimportSourceObjectProxy
from airllm_process_isolation import (
    IsolationBoundaryError,
    RemoteInvocationError,
)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


class PreimportSourceProxyTests(unittest.TestCase):
    def _target(self, root: Path, body: str) -> tuple[Path, bytes]:
        source = body.encode("utf-8")
        path = root / "preimport_target.py"
        path.write_bytes(source)
        return path, source

    def test_01_exact_bytes_execute_once_and_remain_resident(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = root / "marker.txt"
            path, source = self._target(root, f'''\nfrom pathlib import Path\nimport os\nPath({str(marker)!r}).write_text("executed")\nclass Target:\n    def __init__(self, value=1): self.value=value\n    def generate(self, amount=1):\n        self.value += amount\n        return {{"value": self.value, "pid": os.getpid()}}\n''')
            with PreimportSourceObjectProxy(
                "preimport_target", "Target", str(path), digest(source), 10,
                import_roots=(str(root),), timeout_seconds=2.0,
            ) as proxy:
                result = proxy.generate(5)
                self.assertEqual(result["value"], 15)
                self.assertEqual(result["pid"], proxy.receipt.child_pid)
                self.assertNotEqual(result["pid"], os.getpid())
                self.assertEqual(proxy.receipt.start_method, "subprocess-source-attested-v1")
                self.assertEqual(len(proxy.receipt.worker_nonce_root), 64)
            self.assertEqual(marker.read_text(), "executed")

    def test_02_mismatch_does_not_execute_target_side_effect(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            marker = root / "must_not_exist.txt"
            path, source = self._target(root, f'''\nfrom pathlib import Path\nPath({str(marker)!r}).write_text("escaped")\nclass Target: pass\n''')
            expected = digest(source)
            path.write_text(path.read_text() + "\n# drift\n")
            with self.assertRaises(RemoteInvocationError) as caught:
                PreimportSourceObjectProxy(
                    "preimport_target", "Target", str(path), expected,
                    import_roots=(str(root),), timeout_seconds=2.0,
                )
            self.assertEqual(caught.exception.error_type, "SOURCE_DIGEST_MISMATCH")
            self.assertFalse(marker.exists())

    def test_03_invalid_factory_is_rejected_after_exact_target_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "value = 3\n")
            with self.assertRaises(RemoteInvocationError) as caught:
                PreimportSourceObjectProxy(
                    "preimport_target", "Missing", str(path), digest(source),
                    import_roots=(str(root),), timeout_seconds=2.0,
                )
            self.assertEqual(caught.exception.error_type, "FACTORY_RESOLVE")

    def test_04_private_rpc_method_is_rejected_in_parent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "class Target:\n    def ok(self): return 1\n")
            with PreimportSourceObjectProxy(
                "preimport_target", "Target", str(path), digest(source),
                import_roots=(str(root),), timeout_seconds=2.0,
            ) as proxy:
                with self.assertRaises(IsolationBoundaryError):
                    proxy.call("_secret")

    def test_05_missing_method_is_sanitized_and_session_survives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "class Target:\n    def ok(self): return 7\n")
            with PreimportSourceObjectProxy(
                "preimport_target", "Target", str(path), digest(source),
                import_roots=(str(root),), timeout_seconds=2.0,
            ) as proxy:
                with self.assertRaises(RemoteInvocationError) as caught:
                    proxy.call("missing")
                self.assertEqual(caught.exception.error_type, "IsolationBoundaryError")
                self.assertEqual(proxy.call("ok"), 7)

    def test_06_child_exception_is_sanitized_and_session_survives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "class Target:\n    def boom(self): raise ValueError('boom')\n    def ok(self): return 8\n")
            with PreimportSourceObjectProxy(
                "preimport_target", "Target", str(path), digest(source),
                import_roots=(str(root),), timeout_seconds=2.0,
            ) as proxy:
                with self.assertRaises(RemoteInvocationError) as caught:
                    proxy.call("boom")
                self.assertEqual(caught.exception.error_type, "ValueError")
                self.assertEqual(proxy.call("ok"), 8)

    def test_07_unserializable_call_fails_before_send_and_session_survives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "class Target:\n    def echo(self, x): return x\n")
            with PreimportSourceObjectProxy(
                "preimport_target", "Target", str(path), digest(source),
                import_roots=(str(root),), timeout_seconds=2.0,
            ) as proxy:
                with self.assertRaises(IsolationBoundaryError):
                    proxy.call("echo", lambda x: x)
                self.assertEqual(proxy.call("echo", "alive"), "alive")

    def test_08_unserializable_result_is_sanitized_and_session_survives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "class Target:\n    def bad(self): return lambda x: x\n    def ok(self): return 9\n")
            with PreimportSourceObjectProxy(
                "preimport_target", "Target", str(path), digest(source),
                import_roots=(str(root),), timeout_seconds=2.0,
            ) as proxy:
                with self.assertRaises(RemoteInvocationError):
                    proxy.call("bad")
                self.assertEqual(proxy.call("ok"), 9)

    def test_09_timeout_kills_and_poisons_session(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "import time\nclass Target:\n    def slow(self): time.sleep(1.0); return 1\n")
            proxy = PreimportSourceObjectProxy(
                "preimport_target", "Target", str(path), digest(source),
                import_roots=(str(root),), timeout_seconds=0.1,
            )
            with self.assertRaises(IsolationBoundaryError):
                proxy.call("slow")
            self.assertTrue(proxy._closed)
            self.assertIsNotNone(proxy._process.poll())
            with self.assertRaises(IsolationBoundaryError):
                proxy.call("slow")

    def test_10_two_sessions_have_distinct_worker_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, source = self._target(root, "class Target:\n    def ok(self): return 1\n")
            args = ("preimport_target", "Target", str(path), digest(source))
            with PreimportSourceObjectProxy(*args, import_roots=(str(root),), timeout_seconds=2.0) as a, \
                 PreimportSourceObjectProxy(*args, import_roots=(str(root),), timeout_seconds=2.0) as b:
                self.assertNotEqual(a.receipt.child_pid, b.receipt.child_pid)
                self.assertNotEqual(a.receipt.worker_nonce_root, b.receipt.worker_nonce_root)
                self.assertNotEqual(a.receipt.receipt_root, b.receipt.receipt_root)

    def test_11_owner_launch_routes_through_preimport_mode(self):
        from airllm_owner_source_attested_service import launch_owner_attested_airllm
        with launch_owner_attested_airllm(
            model_id="glm",
            model_path="/model",
            model_allowlist={"glm": ("0" * 64,)},
            loader_source_allowlist=("1" * 64,),
            loader_package_source_allowlist=("2" * 64,),
            subject_generation="5" * 40,
            isolation_implementation_generation="7" * 40,
            semantic_admission_surface_root="a" * 64,
            owner_source_modules=("test_airllm_isolated_native_service",),
            wrapper_symbol=("test_airllm_isolated_native_service", "FakeNativeWrapper"),
            timeout_seconds=2.0,
        ) as proxy:
            self.assertEqual(proxy.receipt.start_method, "subprocess-source-attested-v1")
            self.assertEqual(proxy.generate("route")["text"], "route")


if __name__ == "__main__":
    unittest.main(verbosity=2)
