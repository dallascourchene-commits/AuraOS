from __future__ import annotations

from hashlib import sha256
import os
import unittest

from airllm_owner_source_attested_service import (
    bind_owner_isolation_admission,
    launch_owner_attested_airllm,
    owner_source_manifest_root,
    validate_owner_attested_status,
)
from airllm_process_isolation import IsolatedObjectProxy, IsolationBoundaryError, RemoteInvocationError
from airllm_isolated_native_service import current_implementation_source_identity
from test_airllm_process_isolation import FakeBoundary

SUBJECT = "5" * 40
IMPLEMENTATION = "7" * 40
SURFACE = "a" * 64
FAKE_OWNER_MODULES = ("test_airllm_isolated_native_service",)
WRAPPER = ("test_airllm_isolated_native_service", "FakeNativeWrapper")


class OwnerSourceAttestedTests(unittest.TestCase):
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
            owner_source_modules=FAKE_OWNER_MODULES,
            wrapper_symbol=WRAPPER,
            timeout_seconds=5.0,
        )
        values.update(overrides)
        return launch_owner_attested_airllm(**values)

    def _expected(self, *, owner_root=None, subject=SUBJECT, implementation=IMPLEMENTATION, surface=SURFACE):
        identity = current_implementation_source_identity()
        modules = ("airllm_owner_source_attested_service",) + FAKE_OWNER_MODULES
        root = owner_source_manifest_root(modules, loaded=False) if owner_root is None else owner_root
        return bind_owner_isolation_admission(
            subject,
            implementation,
            surface,
            "glm",
            identity.process_source_sha256,
            identity.service_source_sha256,
            root,
        )

    def test_01_owner_manifest_is_deterministic(self):
        modules = ("airllm_owner_source_attested_service",) + FAKE_OWNER_MODULES
        self.assertEqual(
            owner_source_manifest_root(modules, loaded=False),
            owner_source_manifest_root(modules, loaded=False),
        )

    def test_02_owner_manifest_is_noncompensatory(self):
        self.assertNotEqual(
            self._expected().currentness_root,
            self._expected(owner_root="0" * 64).currentness_root,
        )

    def test_03_subject_implementation_and_surface_are_noncompensatory(self):
        base = self._expected().currentness_root
        self.assertNotEqual(base, self._expected(subject="6" * 40).currentness_root)
        self.assertNotEqual(base, self._expected(implementation="8" * 40).currentness_root)
        self.assertNotEqual(base, self._expected(surface="b" * 64).currentness_root)

    def test_04_launch_binds_child_owner_manifest_and_direct_process(self):
        with self._launch() as proxy:
            status = proxy.call("status")
            validate_owner_attested_status(status, proxy.receipt, self._expected())
            self.assertEqual(status["pid"], proxy.receipt.child_pid)
            self.assertNotEqual(status["pid"], os.getpid())

    def test_05_extra_shared_memory_field_fails_closed(self):
        with self._launch() as proxy:
            status = proxy.call("status")
            status["corroboration_count"] = 1000
            with self.assertRaises(IsolationBoundaryError):
                validate_owner_attested_status(status, proxy.receipt, self._expected())

    def test_06_parent_bystander_unchanged_before_during_after(self):
        before = FakeBoundary.from_pretrained("before", trust_remote_code=True)
        with self._launch() as proxy:
            during = FakeBoundary.from_pretrained("during", trust_remote_code=True)
            child = proxy.generate("child")
        after = FakeBoundary.from_pretrained("after", trust_remote_code=True)
        for observed in (before, during, after):
            self.assertIs(observed["trust_remote_code"], True)
            self.assertEqual(observed["pid"], os.getpid())
        self.assertNotEqual(child["pid"], os.getpid())

    def test_07_two_workers_have_distinct_session_identity(self):
        with self._launch() as a, self._launch() as b:
            self.assertNotEqual(a.receipt.child_pid, b.receipt.child_pid)
            self.assertNotEqual(a.receipt.worker_nonce_root, b.receipt.worker_nonce_root)
            self.assertNotEqual(a.receipt.receipt_root, b.receipt.receipt_root)

    def test_08_wrong_expected_owner_manifest_rejected_before_inner_load(self):
        identity = current_implementation_source_identity()
        modules = ("airllm_owner_source_attested_service",) + FAKE_OWNER_MODULES
        with self.assertRaises(RemoteInvocationError) as caught:
            IsolatedObjectProxy(
                "airllm_owner_source_attested_service",
                "OwnerSourceAttestedService",
                "glm",
                "/model",
                {"glm": ("0" * 64,)},
                ("1" * 64,),
                ("2" * 64,),
                SUBJECT,
                IMPLEMENTATION,
                SURFACE,
                identity.process_source_sha256,
                identity.service_source_sha256,
                "0" * 64,
                modules,
                wrapper_symbol=WRAPPER,
                timeout_seconds=5.0,
            )
        self.assertEqual(caught.exception.error_type, "IsolationBoundaryError")
        self.assertIn("owner-source manifest differs", caught.exception.remote_message)

    def test_09_hs1000_owner_and_generation_mutations_do_not_collide(self):
        base = self._expected().currentness_root
        identity = current_implementation_source_identity()
        collisions = 0
        for i in range(1000):
            owner_root = sha256(f"owner-{i}".encode()).hexdigest()
            impl = sha256(f"impl-{i}".encode()).hexdigest()[:40]
            mutated = bind_owner_isolation_admission(
                SUBJECT,
                impl,
                SURFACE,
                "glm",
                identity.process_source_sha256,
                identity.service_source_sha256,
                owner_root,
            )
            collisions += int(mutated.currentness_root == base)
        self.assertEqual(collisions, 0)

    def test_10_100k_composite_currentness_roots_are_unique(self):
        identity = current_implementation_source_identity()
        roots = set()
        for i in range(100_000):
            roots.add(
                bind_owner_isolation_admission(
                    sha256(f"subject-{i // 1000}".encode()).hexdigest()[:40],
                    sha256(f"impl-{i // 100}".encode()).hexdigest()[:40],
                    sha256(f"surface-{i}".encode()).hexdigest(),
                    "glm",
                    identity.process_source_sha256,
                    identity.service_source_sha256,
                    sha256(f"owner-{i // 10}".encode()).hexdigest(),
                ).currentness_root
            )
        self.assertEqual(len(roots), 100_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
