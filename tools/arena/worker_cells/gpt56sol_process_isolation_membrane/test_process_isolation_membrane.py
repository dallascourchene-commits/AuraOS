import os
import sys
import unittest
import importlib
import tempfile
from pathlib import Path
from dataclasses import replace
from types import ModuleType, SimpleNamespace

from process_isolation_membrane import *


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = DedicatedProcessService.start("process_isolation_membrane:IsolationProbe")

    @classmethod
    def tearDownClass(cls):
        cls.service.close()

    def test_private_unregistered_module_is_safe_local_object(self):
        module = SimpleNamespace()
        self.assertEqual(registered_module_aliases(module), ())
        self.assertEqual(require_patch_isolation(module), "PRIVATE_MODULE")

    def test_registered_module_fails_closed_in_parent(self):
        module = ModuleType("_aura_parent_registered")
        sys.modules[module.__name__] = module
        try:
            self.assertEqual(patch_isolation_state(module), "HOLD")
            with self.assertRaisesRegex(ProcessIsolationRequiredError, "DedicatedProcessService"):
                require_patch_isolation(module)
        finally:
            sys.modules.pop(module.__name__, None)

    def test_worker_is_distinct_process_and_registered_module_is_admitted(self):
        state, pid, aliases = self.service.call("isolation_state")
        self.assertEqual(state, "DEDICATED_PROCESS")
        self.assertEqual(pid, self.service.worker_pid)
        self.assertNotEqual(pid, os.getpid())
        self.assertTrue(aliases)

    def test_state_remains_resident_in_worker(self):
        before, _ = self.service.call("increment", 0)
        self.assertEqual(self.service.call("increment", 2)[0], before + 2)
        value, pid = self.service.call("increment", 3)
        self.assertEqual(value, before + 5)
        self.assertEqual(pid, self.service.worker_pid)

    def test_worker_mutation_does_not_touch_parent_registered_module(self):
        parent = ModuleType("_aura_parent_independence")
        sys.modules[parent.__name__] = parent
        try:
            worker_pid, marker = self.service.call("parent_independent_marker")
            self.assertEqual(worker_pid, self.service.worker_pid)
            self.assertEqual(len(marker), 64)
            self.assertFalse(hasattr(parent, "worker_only_marker"))
        finally:
            sys.modules.pop(parent.__name__, None)

    def test_private_method_rpc_fails_closed(self):
        with self.assertRaisesRegex(WorkerProtocolError, "PRIVATE_METHOD"):
            self.service.call("_secret")

    def test_unknown_method_returns_worker_error(self):
        # Worker-level protocol errors terminate the worker by design; use a disposable service.
        service = DedicatedProcessService.start("process_isolation_membrane:IsolationProbe")
        try:
            with self.assertRaisesRegex(WorkerProtocolError, "UNKNOWN_METHOD"):
                service.call("not_here")
        finally:
            service.close()

    def test_unserializable_call_fails_before_effect(self):
        before, _ = self.service.call("increment", 0)
        with self.assertRaisesRegex(WorkerProtocolError, "UNSERIALIZABLE_CALL"):
            self.service.call("increment", lambda x: x)
        self.assertEqual(self.service.call("increment", 0)[0], before)

    def test_close_is_idempotent_and_blocks_calls(self):
        service = DedicatedProcessService.start("process_isolation_membrane:IsolationProbe")
        service.close()
        service.close()
        with self.assertRaisesRegex(WorkerProtocolError, "SERVICE_CLOSED"):
            service.call("increment")

    def test_receipt_binds_distinct_pids_and_d0(self):
        r = self.service.receipt
        self.assertNotEqual(r.parent_pid, r.worker_pid)
        self.assertEqual(r.worker_pid, self.service.worker_pid)
        self.assertEqual(r.authority_ceiling, "D0_PROCESS_ISOLATION_ONLY")
        self.assertEqual(len(r.worker_nonce_root), 64)
        self.assertEqual(len(r.factory_identity_root), 64)
        self.assertEqual(len(r.factory_module_bytes_root), 64)
        self.assertEqual(len(r.receipt_root), 64)
        self.assertTrue(r.verify())
        expected = factory_identity_for_spec("process_isolation_membrane:IsolationProbe")
        self.assertEqual(r.factory_identity_root, expected.identity_root)
        self.assertEqual(r.factory_module_bytes_root, expected.module_bytes_root)

    def test_receipt_factory_identity_tamper_fails_verification(self):
        r = self.service.receipt
        self.assertFalse(replace(r, factory_identity_root="f" * 64).verify())
        self.assertFalse(replace(r, factory_module_bytes_root="e" * 64).verify())

    def test_factory_identity_changes_when_module_bytes_move(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            module_name = "_aura_factory_identity_fixture"
            path = root / f"{module_name}.py"
            path.write_text("class Factory:\n    pass\n")
            sys.path.insert(0, td)
            try:
                importlib.invalidate_caches()
                first = factory_identity_for_spec(f"{module_name}:Factory")
                path.write_text("class Factory:\n    marker = 2\n")
                importlib.invalidate_caches()
                second = factory_identity_for_spec(f"{module_name}:Factory")
                self.assertNotEqual(first.module_bytes_root, second.module_bytes_root)
                self.assertNotEqual(first.identity_root, second.identity_root)
            finally:
                sys.path.remove(td)
                sys.modules.pop(module_name, None)

    def test_factory_identity_same_for_parent_and_worker_receipt(self):
        expected = factory_identity_for_spec("process_isolation_membrane:IsolationProbe")
        self.assertEqual(self.service.receipt.factory_identity_root, expected.identity_root)
        self.assertTrue(self.service.receipt.verify())

    def test_factory_currentness_is_exact_only_for_same_identity(self):
        current = factory_identity_for_spec("process_isolation_membrane:IsolationProbe")
        self.assertEqual(factory_identity_currentness(current, current), "EXACT")
        moved = FactoryIdentity.mint(
            factory_spec=current.factory_spec,
            module_bytes_root="a" * 64 if current.module_bytes_root != "a" * 64 else "b" * 64,
        )
        self.assertEqual(factory_identity_currentness(current, moved), "HOLD")

    def test_factory_currentness_holds_tampered_identity(self):
        current = factory_identity_for_spec("process_isolation_membrane:IsolationProbe")
        tampered = replace(current, identity_root="0" * 64)
        self.assertEqual(factory_identity_currentness(current, tampered), "HOLD")

    def test_bad_spec_fails_closed(self):
        with self.assertRaises(WorkerProtocolError):
            DedicatedProcessService.start("bad-spec")

    def test_omega8_and_13d_noncompensatory(self):
        self.assertTrue(omega8_admit((2,2,2,2,2,2,2,1)))
        self.assertFalse(omega8_admit((2,2,2,2,2,2,1,2)))
        self.assertTrue(admit13((2,2,2,2,2,2,2,2,1,2,2,2,2)))
        self.assertFalse(admit13((2,2,2,2,2,2,2,2,0,2,2,2,2)))


if __name__ == "__main__":
    unittest.main()
