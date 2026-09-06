from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import os
import unittest

from airllm_isolated_native_service import (
    bind_current_isolation_admission,
    current_implementation_source_identity,
    launch_attested_isolated_native_airllm,
    validate_attested_isolation_status,
)
from airllm_process_isolation import IsolatedObjectProxy, IsolationBoundaryError, RemoteInvocationError
from test_airllm_isolated_native_service import FakeNativeWrapper
from test_airllm_process_isolation import FakeBoundary

SUBJECT = "5" * 40
IMPLEMENTATION = "7" * 40
SURFACE = "a" * 64


class AttestedIsolationTests(unittest.TestCase):
    def _launch(self, **overrides):
        values = dict(
            model_id="glm",
            model_path="/model",
            model_allowlist={"glm": ("0" * 64,)},
            loader_source_allowlist=("1" * 64,),
            loader_package_source_allowlist=("2" * 64,),
            subject_generation=SUBJECT,
            isolation_implementation_generation=IMPLEMENTATION,
            semantic_admission_surface_root=SURFACE,
            wrapper_symbol=("test_airllm_isolated_native_service", "FakeNativeWrapper"),
            timeout_seconds=5.0,
        )
        values.update(overrides)
        return launch_attested_isolated_native_airllm(**values)

    def test_01_source_identity_is_exact_and_stable(self):
        a = current_implementation_source_identity()
        b = current_implementation_source_identity()
        self.assertEqual(a, b)
        self.assertEqual(len(a.process_source_sha256), 64)
        self.assertEqual(len(a.service_source_sha256), 64)

    def test_02_attested_binding_is_deterministic(self):
        a = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm")
        b = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm")
        self.assertEqual(a, b)

    def test_03_security_parent_generation_is_noncompensatory(self):
        base = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm")
        changed = bind_current_isolation_admission("6" * 40, IMPLEMENTATION, SURFACE, "glm")
        self.assertNotEqual(base.currentness_root, changed.currentness_root)

    def test_04_isolation_implementation_generation_is_noncompensatory(self):
        base = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm")
        changed = bind_current_isolation_admission(SUBJECT, "8" * 40, SURFACE, "glm")
        self.assertNotEqual(base.currentness_root, changed.currentness_root)

    def test_05_process_source_identity_is_noncompensatory(self):
        identity = current_implementation_source_identity()
        base = bind_current_isolation_admission(
            SUBJECT,
            IMPLEMENTATION,
            SURFACE,
            "glm",
            process_source_sha256=identity.process_source_sha256,
            service_source_sha256=identity.service_source_sha256,
        )
        changed = bind_current_isolation_admission(
            SUBJECT,
            IMPLEMENTATION,
            SURFACE,
            "glm",
            process_source_sha256="0" * 64,
            service_source_sha256=identity.service_source_sha256,
        )
        self.assertNotEqual(base.currentness_root, changed.currentness_root)

    def test_06_service_source_identity_is_noncompensatory(self):
        identity = current_implementation_source_identity()
        base = bind_current_isolation_admission(
            SUBJECT,
            IMPLEMENTATION,
            SURFACE,
            "glm",
            process_source_sha256=identity.process_source_sha256,
            service_source_sha256=identity.service_source_sha256,
        )
        changed = bind_current_isolation_admission(
            SUBJECT,
            IMPLEMENTATION,
            SURFACE,
            "glm",
            process_source_sha256=identity.process_source_sha256,
            service_source_sha256="0" * 64,
        )
        self.assertNotEqual(base.currentness_root, changed.currentness_root)

    def test_07_attested_launch_binds_direct_child_and_source_identity(self):
        with self._launch() as proxy:
            status = proxy.call("status")
            expected = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm")
            validate_attested_isolation_status(status, proxy.receipt, expected)
            self.assertEqual(status["pid"], proxy.receipt.child_pid)
            self.assertNotEqual(status["pid"], os.getpid())
            self.assertEqual(status["currentness_root"], expected.currentness_root)

    def test_08_extra_shared_memory_corroboration_fields_fail_closed(self):
        with self._launch() as proxy:
            status = proxy.call("status")
            expected = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm")
            status["corroboration_count"] = 999
            with self.assertRaises(IsolationBoundaryError):
                validate_attested_isolation_status(status, proxy.receipt, expected)

    def test_09_each_hard_attestation_axis_tamper_fails_closed(self):
        with self._launch() as proxy:
            status = proxy.call("status")
            expected = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm")
            mutations = {
                "subject_generation": "6" * 40,
                "isolation_implementation_generation": "8" * 40,
                "semantic_admission_surface_root": "b" * 64,
                "model_id": "other",
                "process_source_sha256": "0" * 64,
                "service_source_sha256": "1" * 64,
                "currentness_root": "2" * 64,
                "authority_ceiling": "PROMOTED",
            }
            for field, value in mutations.items():
                with self.subTest(field=field):
                    mutated = dict(status)
                    mutated[field] = value
                    with self.assertRaises(IsolationBoundaryError):
                        validate_attested_isolation_status(mutated, proxy.receipt, expected)

    def test_10_parent_bystander_state_unchanged_during_attested_child_lifetime(self):
        before = FakeBoundary.from_pretrained("before", trust_remote_code=True)
        with self._launch() as proxy:
            during = FakeBoundary.from_pretrained("during", trust_remote_code=True)
            child = proxy.generate("child")
        after = FakeBoundary.from_pretrained("after", trust_remote_code=True)
        for observed in (before, during, after):
            self.assertIs(observed["trust_remote_code"], True)
            self.assertEqual(observed["pid"], os.getpid())
        self.assertNotEqual(child["pid"], os.getpid())

    def test_11_two_workers_do_not_share_process_or_nonce_identity(self):
        with self._launch() as a, self._launch() as b:
            self.assertNotEqual(a.receipt.child_pid, b.receipt.child_pid)
            self.assertNotEqual(a.receipt.worker_nonce_root, b.receipt.worker_nonce_root)
            self.assertNotEqual(a.receipt.receipt_root, b.receipt.receipt_root)
            self.assertEqual(a.receipt.factory_identity_root, b.receipt.factory_identity_root)

    def test_12_hs1000_implementation_and_surface_mutations_do_not_collide(self):
        base = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, "glm").currentness_root
        collisions = 0
        for i in range(1000):
            impl = sha256(f"impl-{i}".encode()).hexdigest()[:40]
            surface = sha256(f"surface-{i}".encode()).hexdigest()
            root = bind_current_isolation_admission(SUBJECT, impl, surface, "glm").currentness_root
            collisions += int(root == base)
        self.assertEqual(collisions, 0)

    def test_13_100k_composite_states_produce_unique_roots(self):
        identity = current_implementation_source_identity()
        roots = set()
        for i in range(100_000):
            subject = sha256(f"subject-{i // 1000}".encode()).hexdigest()[:40]
            impl = sha256(f"impl-{i // 100}".encode()).hexdigest()[:40]
            surface = sha256(f"surface-{i}".encode()).hexdigest()
            root = bind_current_isolation_admission(
                subject,
                impl,
                surface,
                "glm",
                process_source_sha256=identity.process_source_sha256,
                service_source_sha256=identity.service_source_sha256,
            ).currentness_root
            roots.add(root)
        self.assertEqual(len(roots), 100_000)

    def test_14_child_rejects_parent_expected_source_hash_mismatch_before_wrapper_load(self):
        identity = current_implementation_source_identity()
        with self.assertRaises(RemoteInvocationError) as caught:
            IsolatedObjectProxy(
                "airllm_isolated_native_service",
                "IsolatedNativeAirLLMService",
                "glm",
                "/model",
                {"glm": ("0" * 64,)},
                ("1" * 64,),
                ("2" * 64,),
                SUBJECT,
                SURFACE,
                isolation_implementation_generation=IMPLEMENTATION,
                expected_process_source_sha256="0" * 64,
                expected_service_source_sha256=identity.service_source_sha256,
                wrapper_symbol=("test_airllm_isolated_native_service", "FakeNativeWrapper"),
                timeout_seconds=5.0,
            )
        self.assertEqual(caught.exception.error_type, "IsolationBoundaryError")
        self.assertIn("source identity differs", caught.exception.remote_message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
