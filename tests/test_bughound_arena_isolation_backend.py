from __future__ import annotations

from dataclasses import replace
from inspect import signature
import unittest

from tools.bughound.arena_isolation_backend import (
    CONFINED,
    DENY_BY_DEFAULT,
    NO_HOST_PRIVILEGE,
    NO_HOST_WRITABLE_MOUNTS,
    NO_SECRETS,
    TRUSTED_ISOLATION_BACKEND_REGISTRY,
    BugHoundIsolationBackendAttestationV1,
    BugHoundIsolationBackendRegistryRecordV1,
    _admit_registered_isolation_backend_with_registry,
    admit_registered_isolation_backend_for_r0,
)
from tools.bughound.arena_runtime import BugHoundArenaRuntimeR0SpecV1
from tools.bughound.target_profile import (
    AURAOS_HARDENING_PROFILE_ID,
    CASH_BOUNTY_PROFILE_ID,
    BugHoundTargetProfileV1,
)


class BugHoundArenaIsolationBackendTests(unittest.TestCase):
    def profile(self, profile_id: str = CASH_BOUNTY_PROFILE_ID) -> BugHoundTargetProfileV1:
        kind = (
            "EXTERNAL_CASH_BOUNTY"
            if profile_id == CASH_BOUNTY_PROFILE_ID
            else "INTERNAL_AURAOS_HARDENING"
        )
        return BugHoundTargetProfileV1(
            profile_id=profile_id,
            profile_kind=kind,
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
        )

    def spec(self, profile_id: str = CASH_BOUNTY_PROFILE_ID) -> BugHoundArenaRuntimeR0SpecV1:
        return BugHoundArenaRuntimeR0SpecV1(
            profile=self.profile(profile_id),
            source_digest="source-tree-1",
        )

    def attestation(self) -> BugHoundIsolationBackendAttestationV1:
        return BugHoundIsolationBackendAttestationV1(
            backend_id="isolation://fixture-1",
            backend_generation="backend-gen-1",
            backend_kind="LINUX_PROCESS_SANDBOX",
            implementation_digest="impl-1",
            policy_digest="policy-1",
            platform_ref="linux://fixture",
            filesystem_confinement=CONFINED,
            network_confinement=CONFINED,
            ipc_confinement=CONFINED,
            syscall_confinement=CONFINED,
            secrets_policy=NO_SECRETS,
            host_writable_mounts_policy=NO_HOST_WRITABLE_MOUNTS,
            privilege_policy=NO_HOST_PRIVILEGE,
            egress_policy=DENY_BY_DEFAULT,
            audit_log_digest="audit-1",
            source_currentness_ref="backend-source-1",
            attester_ref="attester://backend-producer",
            attester_generation="attester-gen-1",
            current=True,
            backend_policy_observed=True,
        )

    def record(self, att=None) -> BugHoundIsolationBackendRegistryRecordV1:
        att = att or self.attestation()
        return BugHoundIsolationBackendRegistryRecordV1(
            backend_id=att.backend_id,
            backend_generation=att.backend_generation,
            attestation_digest=att.attestation_digest,
            registry_receipt_ref="registry://isolation/1",
            observer_ref="observer://independent-1",
            observer_generation="observer-gen-1",
            current=True,
            independently_observed=True,
            revoked=False,
        )

    def registry(self, att=None, record=None):
        att = att or self.attestation()
        record = record or self.record(att)
        return {att.backend_id: (att, record)}

    def admit(self, *, spec=None, att=None, record=None):
        att = att or self.attestation()
        return _admit_registered_isolation_backend_with_registry(
            r0_spec=spec or self.spec(),
            backend_id=att.backend_id,
            registry=self.registry(att, record),
        )

    def test_production_registry_is_immutable_empty_hold(self) -> None:
        self.assertEqual(dict(TRUSTED_ISOLATION_BACKEND_REGISTRY), {})
        with self.assertRaises(TypeError):
            TRUSTED_ISOLATION_BACKEND_REGISTRY["x"] = (self.attestation(), self.record())  # type: ignore[index]

    def test_public_path_fails_closed_without_canonical_backend(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_ISOLATION_BACKEND_REQUIRED"):
            admit_registered_isolation_backend_for_r0(
                r0_spec=self.spec(), backend_id="isolation://fixture-1"
            )

    def test_public_consequence_api_has_no_caller_trust_or_isolation_override(self) -> None:
        names = set(signature(admit_registered_isolation_backend_for_r0).parameters)
        for forbidden in (
            "registry",
            "attestation",
            "trusted",
            "os_network_isolation_proven",
            "filesystem_confinement",
            "network_confinement",
            "ipc_confinement",
            "syscall_confinement",
            "observer_ref",
            "verifier_secret",
        ):
            self.assertNotIn(forbidden, names)

    def test_exact_private_fixture_proves_policy_admission_not_capsule_execution(self) -> None:
        receipt = self.admit()
        self.assertTrue(receipt.registered_backend_policy_proven)
        self.assertFalse(receipt.capsule_execution_under_backend_proven)
        self.assertFalse(receipt.os_network_isolation_for_capsule_proven)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.credential_use_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.payout_authority)
        self.assertFalse(receipt.external_effect)

    def test_both_registered_profiles_may_use_same_backend_without_authority_transfer(self) -> None:
        cash = self.admit(spec=self.spec(CASH_BOUNTY_PROFILE_ID))
        aura = self.admit(spec=self.spec(AURAOS_HARDENING_PROFILE_ID))
        self.assertEqual(cash.backend_id, aura.backend_id)
        self.assertEqual(cash.profile_id, CASH_BOUNTY_PROFILE_ID)
        self.assertEqual(aura.profile_id, AURAOS_HARDENING_PROFILE_ID)
        self.assertFalse(cash.external_effect)
        self.assertFalse(aura.external_effect)

    def test_r0_must_keep_logical_network_off(self) -> None:
        bad = replace(self.spec(), network_policy="ALLOW")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_REQUIRES_R0_LOGICAL_NETWORK_OFF"):
            self.admit(spec=bad)

    def test_r0_cannot_carry_credentials(self) -> None:
        bad = replace(self.spec(), credential_refs=("credential://forbidden",))
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_R0_CREDENTIALS_FORBIDDEN"):
            self.admit(spec=bad)

    def test_each_containment_dimension_is_required(self) -> None:
        cases = (
            ("filesystem_confinement", "LOGICAL_ONLY", "BUGHOUND_R1_FILESYSTEM_CONFINEMENT_REQUIRED"),
            ("network_confinement", "LOGICAL_ONLY", "BUGHOUND_R1_NETWORK_CONFINEMENT_REQUIRED"),
            ("ipc_confinement", "UNKNOWN", "BUGHOUND_R1_IPC_CONFINEMENT_REQUIRED"),
            ("syscall_confinement", "UNKNOWN", "BUGHOUND_R1_SYSCALL_CONFINEMENT_REQUIRED"),
        )
        for field, value, error in cases:
            with self.subTest(field=field):
                bad = replace(self.attestation(), **{field: value})
                with self.assertRaisesRegex(ValueError, error):
                    self.admit(att=bad)

    def test_secret_policy_must_expose_no_credentials(self) -> None:
        bad = replace(self.attestation(), secrets_policy="HOST_ENV_VISIBLE")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_NO_SECRETS_POLICY_REQUIRED"):
            self.admit(att=bad)

    def test_host_writable_mounts_are_forbidden(self) -> None:
        bad = replace(self.attestation(), host_writable_mounts_policy="PROJECT_RW")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_HOST_WRITABLE_MOUNTS_FORBIDDEN"):
            self.admit(att=bad)

    def test_host_privilege_is_forbidden(self) -> None:
        bad = replace(self.attestation(), privilege_policy="HOST_ROOT")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_NO_HOST_PRIVILEGE_REQUIRED"):
            self.admit(att=bad)

    def test_egress_must_be_deny_by_default(self) -> None:
        bad = replace(self.attestation(), egress_policy="ALLOW_ALL")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_DENY_BY_DEFAULT_EGRESS_REQUIRED"):
            self.admit(att=bad)

    def test_attestation_must_be_current_and_observed(self) -> None:
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_ATTESTATION_NOT_CURRENT"):
            self.admit(att=replace(self.attestation(), current=False))
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_BACKEND_POLICY_NOT_OBSERVED"):
            self.admit(att=replace(self.attestation(), backend_policy_observed=False))

    def test_attestation_external_effect_is_forbidden(self) -> None:
        bad = replace(self.attestation(), external_effect=True)
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_ATTESTATION_EXTERNAL_EFFECT_FORBIDDEN"):
            self.admit(att=bad)

    def test_registry_must_be_current_independent_and_not_revoked(self) -> None:
        att = self.attestation()
        cases = (
            (replace(self.record(att), current=False), "BUGHOUND_R1_REGISTRY_NOT_CURRENT"),
            (
                replace(self.record(att), independently_observed=False),
                "BUGHOUND_R1_REGISTRY_INDEPENDENT_OBSERVATION_REQUIRED",
            ),
            (replace(self.record(att), revoked=True), "BUGHOUND_R1_BACKEND_REVOKED"),
        )
        for record, error in cases:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ValueError, error):
                    self.admit(att=att, record=record)

    def test_registry_observer_must_be_distinct_from_attester(self) -> None:
        att = self.attestation()
        record = replace(self.record(att), observer_ref=att.attester_ref)
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_REGISTRY_OBSERVER_NOT_INDEPENDENT"):
            self.admit(att=att, record=record)

    def test_registry_attestation_digest_substitution_fails(self) -> None:
        att = self.attestation()
        record = replace(self.record(att), attestation_digest="forged")
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_REGISTRY_ATTESTATION_DIGEST_MISMATCH"):
            self.admit(att=att, record=record)

    def test_registry_backend_identity_and_generation_substitutions_fail(self) -> None:
        att = self.attestation()
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_REGISTRY_BACKEND_ID_MISMATCH"):
            self.admit(att=att, record=replace(self.record(att), backend_id="different"))
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_REGISTRY_BACKEND_GENERATION_MISMATCH"):
            self.admit(att=att, record=replace(self.record(att), backend_generation="old"))

    def test_registry_external_effect_is_forbidden(self) -> None:
        att = self.attestation()
        record = replace(self.record(att), external_effect=True)
        with self.assertRaisesRegex(ValueError, "BUGHOUND_R1_REGISTRY_EXTERNAL_EFFECT_FORBIDDEN"):
            self.admit(att=att, record=record)

    def test_admission_digest_is_deterministic(self) -> None:
        self.assertEqual(self.admit().admission_digest, self.admit().admission_digest)


if __name__ == "__main__":
    unittest.main()
