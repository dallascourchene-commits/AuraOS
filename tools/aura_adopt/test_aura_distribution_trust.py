import unittest
from dataclasses import replace

from tools.aura_adopt.aura_distribution_trust import (
    AdmissionDisposition,
    ArtifactKind,
    AuthorityClass,
    DistributionArtifact,
    DistributionChannel,
    DistributionPolicy,
    DistributionRefusal,
    ManifestSignerRequirement,
    Permission,
    RollbackAuthorization,
    TrustedDistributionManifest,
    TrustedManifestVerificationEvidence,
    admit_distribution,
)

CUR = "board-currentness-gen-1"
TRUST_CUR = "trust-currentness-gen-1"
A64 = "a" * 64
B64 = "b" * 64


def artifact(
    artifact_id="web",
    *,
    kind=ArtifactKind.WEB_APP,
    authority=AuthorityClass.CODE_EXECUTION,
    digest=A64,
    immutable=True,
    version="1.0.0",
    origin="https://example.invalid/aura.bin",
    channel=DistributionChannel.STABLE,
    required=(),
    optional=(),
    binary_sig_ref="",
    currentness=CUR,
):
    return DistributionArtifact(
        artifact_id=artifact_id,
        kind=kind,
        authority_class=authority,
        source_ref=f"github:repo:{artifact_id}",
        source_generation="commit-" + "1" * 40,
        source_currentness_ref=currentness,
        content_sha256=digest,
        byte_size=123,
        immutable_source=immutable,
        version=version,
        origin_uri=origin,
        channel=channel,
        media_type="application/octet-stream",
        capability_ids=(f"cap:{artifact_id}",),
        required_permissions=tuple(required),
        optional_permissions=tuple(optional),
        binary_signature_evidence_ref=binary_sig_ref,
    )


def manifest(*items, supersedes="", rollback_of=""):
    return TrustedDistributionManifest(
        route_id="zero-install-web-pwa",
        build_ref="build-" + "2" * 40,
        manifest_generation="manifest-gen-1",
        source_currentness_ref=CUR,
        artifacts=tuple(items),
        signer=ManifestSignerRequirement("aura-release", "release-key", "k1"),
        supersedes_manifest_digest=supersedes,
        rollback_of_manifest_digest=rollback_of,
    )


def policy(**kwargs):
    values = dict(
        current_trust_store_generation="trust-g1",
        current_trust_currentness_ref=TRUST_CUR,
        trusted_verifier_refs=("host://trusted-verifier",),
        allowed_origin_hosts=("example.invalid",),
        allowed_channels=(DistributionChannel.STABLE,),
        allowed_required_permissions=(
            Permission.NETWORK,
            Permission.LOCAL_FILE_READ,
            Permission.LOCAL_FILE_WRITE,
        ),
    )
    values.update(kwargs)
    return DistributionPolicy(**values)


def evidence(m, **kwargs):
    values = dict(
        manifest_digest=m.manifest_digest,
        signer_id=m.signer.signer_id,
        key_id=m.signer.key_id,
        key_generation=m.signer.key_generation,
        trust_store_generation="trust-g1",
        verification_source_ref="host://trusted-verifier",
        verification_currentness_ref=TRUST_CUR,
        signature_verified=True,
        verified_binary_artifact_ids=(),
    )
    values.update(kwargs)
    return TrustedManifestVerificationEvidence(**values)


def admit(m, *, previous=None, pol=None, ev="AUTO", observed=None, expected=CUR):
    if ev == "AUTO":
        ev = evidence(m)
    if observed is None:
        observed = {a.artifact_id: a.content_sha256 for a in m.artifacts}
    return admit_distribution(
        m,
        expected_currentness_ref=expected,
        observed_digests=observed,
        trust_evidence=ev,
        policy=policy() if pol is None else pol,
        previous_manifest=previous,
    )


class DistributionTrustTests(unittest.TestCase):
    def test_01_exact_static_payload_is_trust_ready_without_effect_authority(self):
        m = manifest(artifact())
        r = admit(m)
        self.assertEqual(AdmissionDisposition.TRUST_READY, r.disposition)
        self.assertTrue(r.integrity_ready)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.execution_authorized)
        self.assertFalse(r.execution_proven)
        self.assertFalse(r.install_performed)
        self.assertFalse(r.update_performed)
        self.assertFalse(r.network_fetch_performed)
        self.assertFalse(r.public_distribution_performed)

    def test_02_manifest_currentness_mismatch_rebases(self):
        r = admit(manifest(artifact()), expected="new")
        self.assertEqual(AdmissionDisposition.REBASE_REQUIRED, r.disposition)
        self.assertIn("CURRENTNESS_MISMATCH", r.blockers)

    def test_03_artifact_currentness_mismatch_rebases(self):
        m = manifest(artifact(currentness="old"))
        r = admit(m)
        self.assertEqual(AdmissionDisposition.REBASE_REQUIRED, r.disposition)
        self.assertIn("ARTIFACT_CURRENTNESS_MISMATCH:web", r.blockers)

    def test_04_digest_mismatch_fails_integrity(self):
        m = manifest(artifact())
        r = admit(m, observed={"web": B64})
        self.assertEqual(AdmissionDisposition.INTEGRITY_MISMATCH, r.disposition)
        self.assertIn("ARTIFACT_INTEGRITY_MISMATCH:web", r.blockers)

    def test_05_missing_digest_is_evidence_required(self):
        m = manifest(artifact())
        r = admit(m, observed={})
        self.assertEqual(AdmissionDisposition.EVIDENCE_REQUIRED, r.disposition)
        self.assertIn("DIGEST_EVIDENCE_REQUIRED:web", r.blockers)

    def test_06_mutable_source_refused(self):
        m = manifest(artifact(immutable=False))
        r = admit(m)
        self.assertEqual(AdmissionDisposition.SOURCE_NOT_IMMUTABLE, r.disposition)

    def test_07_no_trust_evidence_refused(self):
        m = manifest(artifact())
        r = admit(m, ev=None)
        self.assertEqual(AdmissionDisposition.SIGNATURE_EVIDENCE_REQUIRED, r.disposition)
        self.assertIn("TRUST_EVIDENCE_REQUIRED", r.blockers)

    def test_08_untrusted_verifier_refused(self):
        m = manifest(artifact())
        r = admit(m, ev=evidence(m, verification_source_ref="caller://self"))
        self.assertIn("UNTRUSTED_VERIFICATION_SOURCE", r.blockers)

    def test_09_manifest_signature_not_verified(self):
        m = manifest(artifact())
        r = admit(m, ev=evidence(m, signature_verified=False))
        self.assertIn("MANIFEST_SIGNATURE_NOT_VERIFIED", r.blockers)

    def test_10_revoked_key_refused(self):
        m = manifest(artifact())
        r = admit(m, ev=evidence(m, key_revoked=True))
        self.assertIn("SIGNING_KEY_REVOKED", r.blockers)

    def test_11_signer_mismatch_refused(self):
        m = manifest(artifact())
        r = admit(m, ev=evidence(m, signer_id="attacker"))
        self.assertIn("TRUST_SIGNER_MISMATCH", r.blockers)

    def test_12_key_id_mismatch_refused(self):
        m = manifest(artifact())
        r = admit(m, ev=evidence(m, key_id="wrong"))
        self.assertIn("TRUST_KEY_ID_MISMATCH", r.blockers)

    def test_13_key_generation_mismatch_refused(self):
        m = manifest(artifact())
        r = admit(m, ev=evidence(m, key_generation="old"))
        self.assertIn("TRUST_KEY_GENERATION_MISMATCH", r.blockers)

    def test_14_stale_trust_store_rebases(self):
        m = manifest(artifact())
        r = admit(m, pol=policy(current_trust_store_generation="trust-g2"))
        self.assertEqual(AdmissionDisposition.REBASE_REQUIRED, r.disposition)
        self.assertIn("TRUST_STORE_GENERATION_STALE", r.blockers)

    def test_15_stale_trust_currentness_rebases(self):
        m = manifest(artifact())
        r = admit(m, ev=evidence(m, verification_currentness_ref="old"))
        self.assertEqual(AdmissionDisposition.REBASE_REQUIRED, r.disposition)
        self.assertIn("TRUST_CURRENTNESS_STALE", r.blockers)

    def test_16_untrusted_origin_scheme_refused(self):
        m = manifest(artifact(origin="http://example.invalid/aura.bin"))
        r = admit(m)
        self.assertEqual(AdmissionDisposition.POLICY_REFUSED, r.disposition)
        self.assertIn("ORIGIN_SCHEME_NOT_ALLOWED:web", r.blockers)

    def test_17_untrusted_origin_host_refused(self):
        m = manifest(artifact(origin="https://evil.invalid/aura.bin"))
        self.assertIn("ORIGIN_HOST_NOT_ALLOWED:web", admit(m).blockers)

    def test_18_disallowed_channel_refused(self):
        m = manifest(artifact(channel=DistributionChannel.DEV))
        self.assertIn("CHANNEL_NOT_ALLOWED:web", admit(m).blockers)

    def test_19_permission_above_policy_refused(self):
        m = manifest(artifact(required=(Permission.CAMERA,)))
        self.assertIn("REQUIRED_PERMISSION_EXCEEDS_POLICY:web", admit(m).blockers)

    def test_20_permission_overlap_rejected_at_construction(self):
        with self.assertRaisesRegex(DistributionRefusal, "PERMISSION_CLASS_OVERLAP"):
            artifact(required=(Permission.NETWORK,), optional=(Permission.NETWORK,))

    def test_21_privacy_unsafe_defaults_refused(self):
        with self.assertRaisesRegex(DistributionRefusal, "TELEMETRY_DEFAULT_MUST_BE_OFF"):
            replace(manifest(artifact()), telemetry_default_enabled=True)

    def test_22_network_code_fetch_authority_not_minted(self):
        with self.assertRaisesRegex(DistributionRefusal, "NETWORK_CODE_FETCH_AUTHORITY_REFUSED"):
            replace(manifest(artifact()), network_code_fetch_authorized=True)

    def test_23_public_distribution_authority_not_minted(self):
        with self.assertRaisesRegex(DistributionRefusal, "PUBLIC_DISTRIBUTION_AUTHORITY_REFUSED"):
            replace(manifest(artifact()), public_distribution_authorized=True)

    def test_24_installable_binary_requires_host_verified_binary_evidence(self):
        apk = artifact("apk", kind=ArtifactKind.APK, authority=AuthorityClass.INSTALLABLE_BINARY, binary_sig_ref="attest:apk")
        m = manifest(apk)
        r = admit(m)
        self.assertIn("BINARY_SIGNATURE_EVIDENCE_REQUIRED:apk", r.blockers)
        good = evidence(m, verified_binary_artifact_ids=("apk",))
        self.assertEqual(AdmissionDisposition.TRUST_READY, admit(m, ev=good).disposition)

    def test_25_update_requires_exact_supersession(self):
        old = manifest(artifact(version="1.0.0"))
        new = manifest(artifact(version="1.1.0"))
        self.assertIn("SUPERSESSION_BINDING_REQUIRED", admit(new, previous=old).blockers)

    def test_26_new_required_permission_requires_consent(self):
        old = manifest(artifact(version="1.0.0", required=(Permission.NETWORK,)))
        new = manifest(
            artifact(version="1.1.0", required=(Permission.NETWORK, Permission.LOCAL_FILE_READ)),
            supersedes=old.manifest_digest,
        )
        r = admit(new, previous=old)
        self.assertEqual(AdmissionDisposition.CONSENT_REQUIRED, r.disposition)
        self.assertIn("web:LOCAL_FILE_READ", r.added_required_permissions)

    def test_27_permission_removal_is_recorded(self):
        old = manifest(artifact(version="1.0.0", required=(Permission.NETWORK, Permission.LOCAL_FILE_READ)))
        new = manifest(artifact(version="1.1.0", required=(Permission.NETWORK,)), supersedes=old.manifest_digest)
        r = admit(new, previous=old)
        self.assertEqual(AdmissionDisposition.TRUST_READY, r.disposition)
        self.assertIn("web:LOCAL_FILE_READ", r.removed_required_permissions)

    def test_28_channel_change_refused_by_default(self):
        old = manifest(artifact(version="1.0.0", channel=DistributionChannel.STABLE))
        new = manifest(artifact(version="1.1.0", channel=DistributionChannel.BETA), supersedes=old.manifest_digest)
        pol = policy(allowed_channels=(DistributionChannel.STABLE, DistributionChannel.BETA))
        self.assertIn("CHANNEL_CHANGE_NOT_ALLOWED:web", admit(new, previous=old, pol=pol).blockers)

    def test_29_rollback_requires_binding_and_authority(self):
        old = manifest(artifact(version="2.0.0"))
        new = manifest(artifact(version="1.0.0"), supersedes=old.manifest_digest)
        r = admit(new, previous=old)
        self.assertIn("ROLLBACK_BINDING_REQUIRED", r.blockers)
        self.assertIn("ROLLBACK_AUTHORITY_REQUIRED", r.blockers)

    def test_30_authorized_rollback_is_trust_ready(self):
        old = manifest(artifact(version="2.0.0"))
        proto = manifest(artifact(version="1.0.0"), supersedes=old.manifest_digest, rollback_of=old.manifest_digest)
        auth = RollbackAuthorization(
            old.manifest_digest,
            proto.manifest_digest,
            "owner://rollback/1",
            TRUST_CUR,
            True,
        )
        r = admit(proto, previous=old, pol=policy(rollback_authorization=auth))
        self.assertEqual(AdmissionDisposition.TRUST_READY, r.disposition)

    def test_31_artifact_type_change_refused(self):
        old = manifest(artifact(version="1.0.0"))
        new = manifest(artifact(version="1.1.0", kind=ArtifactKind.WASM_MODULE), supersedes=old.manifest_digest)
        self.assertIn("ARTIFACT_TYPE_CHANGED:web", admit(new, previous=old).blockers)

    def test_32_artifact_removal_requires_explicit_policy(self):
        old = manifest(artifact("web"), artifact("recipe", kind=ArtifactKind.RECIPE, authority=AuthorityClass.DATA_ONLY, digest=B64))
        new = manifest(artifact("web", version="1.1.0"), supersedes=old.manifest_digest)
        self.assertIn("ARTIFACT_REMOVAL_REQUIRES_EXPLICIT_POLICY:recipe", admit(new, previous=old).blockers)

    def test_33_manifest_digest_stable_under_artifact_order_and_strict_validation(self):
        a = artifact("a", digest=A64)
        b = artifact("b", digest=B64)
        self.assertEqual(manifest(a, b).manifest_digest, manifest(b, a).manifest_digest)
        with self.assertRaisesRegex(DistributionRefusal, "INVALID_KIND"):
            replace(a, kind="WEB_APP")


if __name__ == "__main__":
    unittest.main()
