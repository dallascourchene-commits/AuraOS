import tempfile
import unittest
from dataclasses import replace

from tools.arena.canonical_release_installed_runtime import (
    CanonicalReleasePublication,
    InstallAttempt,
    InstallState,
    InstallationIntent,
    InstallationJournal,
    RecoveryAction,
    VerifiedInstallAdmission,
    compile_installation,
    root,
)
from tools.project006.installed_runtime_attestation import (
    HostMeasurement,
    MeasurementEvidence,
    RuntimeDisposition,
    RuntimeReleaseManifest,
)


def r(label: str) -> str:
    return root({"r": label})


def manifest(head: str = "h1", components=None) -> RuntimeReleaseManifest:
    return RuntimeReleaseManifest(
        "rel-1",
        "AuraOS",
        head,
        7,
        r("canonical-op"),
        components or {"core": r("core"), "wake": r("wake")},
    )


def publication(m=None, **changes) -> CanonicalReleasePublication:
    m = m or manifest()
    values = {
        "commit_receipt_root": r("commit"),
        "canonical_state_root": r("state"),
        "release_root": m.release_root,
        "publication_root": r("publication"),
        "canonical_commit": True,
        "published": True,
        "publication_current": True,
    }
    values.update(changes)
    return CanonicalReleasePublication(**values)


def intent(**changes) -> InstallationIntent:
    values = {
        "host_id": "laptop",
        "host_incarnation": "host-inc-7",
        "source_incarnation_root": r("source-inc"),
        "policy_root": r("policy"),
    }
    values.update(changes)
    return InstallationIntent(**values)


def attempt(installation, **changes) -> InstallAttempt:
    values = {
        "operation_root": installation.operation_root,
        "publication_root": installation.publication_root,
        "admission_root": r("admission"),
        "currentness_root": r("currentness"),
        "actor_id": "installer",
        "installer_generation": 3,
        "attempt_ordinal": 1,
        "k27": (1, 2, 3),
    }
    values.update(changes)
    return InstallAttempt(**values)


def verified(a: InstallAttempt, now_ms: int = 1000, **changes):
    values = {
        "claim_root": a.claim_root,
        "operation_root": a.operation_root,
        "publication_root": a.publication_root,
        "currentness_root": a.currentness_root,
        "verifier_id": "owner-verifier",
        "subject_id": a.actor_id,
        "authenticated": True,
        "independent": True,
        "issued_at_ms": now_ms - 10,
        "expires_at_ms": now_ms + 1000,
    }
    values.update(changes)
    return VerifiedInstallAdmission(**values)


def good_measurement(m, installation, now_ms: int = 1000):
    measurement = HostMeasurement(
        installation.host_id,
        m.expected_head,
        m.components,
        installation.host_incarnation,
        installation.source_incarnation_root,
        now_ms,
        (1, 2, 3),
    )
    evidence = MeasurementEvidence(
        measurement.technical_root,
        m.release_root,
        "runtime-verifier",
        "runtime-observer",
        True,
        True,
        True,
        True,
        now_ms - 1,
        now_ms + 1000,
    )
    return measurement, evidence


class CanonicalReleaseInstalledRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = InstallationJournal(self.temp.name + "/journal.db")

    def tearDown(self):
        self.journal.close()
        self.temp.cleanup()

    def ready(self):
        m = manifest()
        installation = compile_installation(m, publication(m), intent())
        self.journal.prepare(installation)
        a = attempt(installation)
        result = self.journal.begin_attempt(
            installation, a, lambda item: verified(item), now_ms=1000
        )
        self.assertEqual(result, a.attempt_root)
        return m, installation, a

    def test_compile_requires_canonical_current_publication(self):
        m = manifest()
        with self.assertRaises(ValueError):
            compile_installation(m, publication(m, canonical_commit=False), intent())
        with self.assertRaises(ValueError):
            compile_installation(m, publication(m, published=False), intent())

    def test_release_root_must_match_manifest(self):
        m = manifest()
        with self.assertRaises(ValueError):
            compile_installation(m, publication(m, release_root=r("other")), intent())

    def test_republication_preserves_operation_but_rotates_attempt(self):
        m = manifest()
        first = compile_installation(m, publication(m, publication_root=r("p1")), intent())
        second = compile_installation(m, publication(m, publication_root=r("p2")), intent())
        self.assertEqual(first.operation_root, second.operation_root)
        self.assertNotEqual(attempt(first).attempt_root, attempt(second).attempt_root)

    def test_commit_semantics_rotate_operation(self):
        m = manifest()
        first = compile_installation(m, publication(m), intent())
        second = compile_installation(m, publication(m, commit_receipt_root=r("commit-2")), intent())
        self.assertNotEqual(first.operation_root, second.operation_root)

    def test_host_incarnation_rotates_operation(self):
        m = manifest()
        first = compile_installation(m, publication(m), intent(host_incarnation="h1"))
        second = compile_installation(m, publication(m), intent(host_incarnation="h2"))
        self.assertNotEqual(first.operation_root, second.operation_root)

    def test_k27_rotates_attempt_not_operation(self):
        m = manifest()
        installation = compile_installation(m, publication(m), intent())
        first = attempt(installation, k27=(1, 2, 3))
        second = attempt(installation, k27=(9, 8, 7))
        self.assertEqual(first.operation_root, second.operation_root)
        self.assertNotEqual(first.attempt_root, second.attempt_root)

    def test_publication_admission_must_match_at_use(self):
        m = manifest()
        installation = compile_installation(m, publication(m), intent())
        self.journal.prepare(installation)
        a = replace(attempt(installation), publication_root=r("stale-publication"))
        result = self.journal.begin_attempt(installation, a, lambda item: verified(item), now_ms=1000)
        self.assertEqual(result, "HOLD_PUBLICATION_ADMISSION_MOVED")

    def test_publication_can_rebind_before_attempt_only(self):
        m = manifest()
        first = compile_installation(m, publication(m, publication_root=r("p1")), intent())
        second = compile_installation(m, publication(m, publication_root=r("p2")), intent())
        self.journal.prepare(first)
        self.journal.prepare(second)
        a = attempt(second)
        result = self.journal.begin_attempt(second, a, lambda item: verified(item), now_ms=1000)
        self.assertEqual(result, a.attempt_root)

    def test_publication_cannot_rebind_after_attempt_durable(self):
        m = manifest()
        first = compile_installation(m, publication(m, publication_root=r("p1")), intent())
        second = compile_installation(m, publication(m, publication_root=r("p2")), intent())
        self.journal.prepare(first)
        first_attempt = attempt(first)
        self.journal.begin_attempt(first, first_attempt, lambda item: verified(item), now_ms=1000)
        self.journal.prepare(second)
        second_attempt = attempt(second)
        result = self.journal.begin_attempt(second, second_attempt, lambda item: verified(item), now_ms=1000)
        self.assertEqual(result, "HOLD_PUBLICATION_JOURNAL_DIVERGED")

    def test_missing_admission_holds(self):
        m = manifest()
        installation = compile_installation(m, publication(m), intent())
        self.journal.prepare(installation)
        result = self.journal.begin_attempt(installation, attempt(installation), lambda _: None, now_ms=1000)
        self.assertEqual(result, "HOLD_ADMISSION_UNVERIFIED")

    def test_unauthenticated_admission_holds(self):
        m = manifest()
        installation = compile_installation(m, publication(m), intent())
        self.journal.prepare(installation)
        a = attempt(installation)
        result = self.journal.begin_attempt(installation, a, lambda item: verified(item, authenticated=False), now_ms=1000)
        self.assertEqual(result, "HOLD_ADMISSION_NOT_AUTHENTICATED_INDEPENDENT")

    def test_forged_admission_claim_holds(self):
        m = manifest()
        installation = compile_installation(m, publication(m), intent())
        self.journal.prepare(installation)
        a = attempt(installation)
        result = self.journal.begin_attempt(installation, a, lambda item: verified(item, claim_root=r("forged")), now_ms=1000)
        self.assertEqual(result, "HOLD_ADMISSION_CLAIM_DIVERGED")

    def test_expired_admission_holds(self):
        m = manifest()
        installation = compile_installation(m, publication(m), intent())
        self.journal.prepare(installation)
        a = attempt(installation)
        result = self.journal.begin_attempt(installation, a, lambda item: verified(item, issued_at_ms=1, expires_at_ms=999), now_ms=1000)
        self.assertEqual(result, "HOLD_ADMISSION_NOT_CURRENT_AT_USE")

    def test_ambiguous_apply_requires_reconcile_not_retry(self):
        _, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "UNKNOWN")
        self.assertEqual(self.journal.recovery_action(installation.operation_root), RecoveryAction.RECONCILE_BEFORE_RETRY)
        retry = replace(a, attempt_ordinal=2)
        result = self.journal.begin_attempt(installation, retry, lambda item: verified(item), now_ms=1000)
        self.assertEqual(result, "HOLD_NEVER_BLIND_REAPPLY")

    def test_confirmed_not_applied_allows_fresh_attempt(self):
        _, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "NOT_APPLIED")
        self.assertEqual(self.journal.recovery_action(installation.operation_root), RecoveryAction.START_FRESH_ATTEMPT)
        retry = replace(a, attempt_ordinal=2)
        result = self.journal.begin_attempt(installation, retry, lambda item: verified(item), now_ms=1000)
        self.assertEqual(result, retry.attempt_root)

    def test_apply_receipt_required(self):
        _, installation, a = self.ready()
        result = self.journal.observe_apply(installation.operation_root, a.attempt_root, "APPLIED")
        self.assertEqual(result, "HOLD_APPLY_RECEIPT_REQUIRED")

    def test_local_apply_is_not_currentness(self):
        m, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "APPLIED", r("apply"))
        attestation = self.journal.bind_attestation(installation, m, None, None, owner_reported_updated=True, now_ms=1000)
        self.assertFalse(attestation.current)
        self.assertEqual(self.journal.status(installation.operation_root)[0], InstallState.ATTESTATION_PENDING.value)

    def test_exact_independent_measurement_finishes(self):
        m, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "APPLIED", r("apply"))
        measurement, evidence = good_measurement(m, installation)
        attestation = self.journal.bind_attestation(installation, m, measurement, evidence, owner_reported_updated=True, now_ms=1000)
        self.assertTrue(attestation.current)
        self.assertEqual(self.journal.recovery_action(installation.operation_root), RecoveryAction.DONE)

    def test_wrong_host_incarnation_cannot_attest_other_target(self):
        m, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "APPLIED", r("apply"))
        measurement, evidence = good_measurement(m, installation)
        measurement = replace(measurement, host_incarnation="other")
        evidence = replace(evidence, measurement_root=measurement.technical_root)
        result = self.journal.bind_attestation(installation, m, measurement, evidence, owner_reported_updated=True, now_ms=1000)
        self.assertEqual(result, "HOLD_TARGET_HOST_INCARNATION_DIVERGED")

    def test_wrong_source_incarnation_cannot_attest(self):
        m, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "APPLIED", r("apply"))
        measurement, evidence = good_measurement(m, installation)
        measurement = replace(measurement, source_incarnation_root=r("other-source"))
        evidence = replace(evidence, measurement_root=measurement.technical_root)
        result = self.journal.bind_attestation(installation, m, measurement, evidence, owner_reported_updated=True, now_ms=1000)
        self.assertEqual(result, "HOLD_SOURCE_INCARNATION_DIVERGED")

    def test_mixed_generation_never_current(self):
        m, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "APPLIED", r("apply"))
        measurement, evidence = good_measurement(m, installation)
        measurement = replace(measurement, observed_components={"core": r("different"), "wake": r("wake")})
        evidence = replace(evidence, measurement_root=measurement.technical_root)
        attestation = self.journal.bind_attestation(installation, m, measurement, evidence, owner_reported_updated=True, now_ms=1000)
        self.assertEqual(attestation.disposition, RuntimeDisposition.MIXED_GENERATION)
        self.assertFalse(attestation.current)

    def test_release_manifest_move_holds_at_attestation(self):
        m, installation, a = self.ready()
        self.journal.observe_apply(installation.operation_root, a.attempt_root, "APPLIED", r("apply"))
        moved = manifest(head="other-head")
        result = self.journal.bind_attestation(installation, moved, None, None, owner_reported_updated=True, now_ms=1000)
        self.assertEqual(result, "HOLD_RELEASE_MANIFEST_MOVED")

    def test_authority_ceiling(self):
        with self.assertRaises(ValueError):
            CanonicalReleasePublication(r("c"), r("s"), r("r"), r("p"), True, True, True, "D1")
        a = attempt(compile_installation(manifest(), publication(), intent()))
        good = verified(a)
        with self.assertRaises(ValueError):
            VerifiedInstallAdmission(**{**good.__dict__, "effect_authority": True})


if __name__ == "__main__":
    unittest.main()
