import unittest

from tools.aura_adopt.aura_distribution_trust import (
    AdmissionDisposition,
    ArtifactKind,
    AuthorityClass,
    DistributionArtifact,
    DistributionRefusal,
    SignatureStatus,
    TrustedDistributionManifest,
    admit_distribution,
)


CUR = "board-currentness-gen-1"


def artifact(
    artifact_id="web",
    *,
    kind=ArtifactKind.WEB_APP,
    authority=AuthorityClass.CODE_EXECUTION,
    digest="a" * 64,
    immutable=True,
    signature_status=SignatureStatus.NOT_APPLICABLE,
    signature_evidence_ref="",
):
    return DistributionArtifact(
        artifact_id=artifact_id,
        kind=kind,
        authority_class=authority,
        source_ref=f"github:repo:{artifact_id}",
        source_generation="commit-" + "1" * 40,
        source_currentness_ref=CUR,
        content_sha256=digest,
        byte_size=123,
        immutable_source=immutable,
        media_type="text/plain",
        signature_status=signature_status,
        signature_evidence_ref=signature_evidence_ref,
    )


def manifest(*items):
    return TrustedDistributionManifest(
        route_id="zero-install-web-pwa",
        build_ref="build-" + "2" * 40,
        manifest_generation="manifest-gen-1",
        source_currentness_ref=CUR,
        artifacts=tuple(items),
    )


class DistributionTrustTests(unittest.TestCase):
    def test_exact_static_payloads_become_trust_ready_without_effect_authority(self):
        m = manifest(
            artifact("web"),
            artifact("recipe", kind=ArtifactKind.RECIPE, authority=AuthorityClass.DATA_ONLY, digest="b" * 64),
        )
        r = admit_distribution(
            m,
            expected_currentness_ref=CUR,
            observed_digests={"web": "a" * 64, "recipe": "b" * 64},
        )
        self.assertEqual(AdmissionDisposition.TRUST_READY, r.disposition)
        self.assertTrue(r.integrity_ready)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.execution_authorized)
        self.assertFalse(r.execution_proven)
        self.assertFalse(r.network_fetch_performed)
        self.assertFalse(r.public_distribution_performed)

    def test_manifest_currentness_mismatch_rebases_before_trust(self):
        m = manifest(artifact())
        r = admit_distribution(m, expected_currentness_ref="new-generation", observed_digests={"web": "a" * 64})
        self.assertEqual(AdmissionDisposition.REBASE_REQUIRED, r.disposition)
        self.assertEqual(("CURRENTNESS_MISMATCH",), r.blockers)

    def test_digest_mismatch_fails_integrity(self):
        m = manifest(artifact())
        r = admit_distribution(m, expected_currentness_ref=CUR, observed_digests={"web": "b" * 64})
        self.assertEqual(AdmissionDisposition.INTEGRITY_MISMATCH, r.disposition)
        self.assertIn("ARTIFACT_INTEGRITY_MISMATCH:web", r.blockers)

    def test_missing_digest_evidence_is_not_treated_as_zero_or_success(self):
        m = manifest(artifact())
        r = admit_distribution(m, expected_currentness_ref=CUR, observed_digests={})
        self.assertEqual(AdmissionDisposition.EVIDENCE_REQUIRED, r.disposition)
        self.assertIn("DIGEST_EVIDENCE_REQUIRED:web", r.blockers)

    def test_mutable_executable_source_is_refused_even_with_matching_digest(self):
        m = manifest(artifact(immutable=False))
        r = admit_distribution(m, expected_currentness_ref=CUR, observed_digests={"web": "a" * 64})
        self.assertEqual(AdmissionDisposition.SOURCE_NOT_IMMUTABLE, r.disposition)

    def test_installable_binary_requires_verified_signature_evidence(self):
        with self.assertRaisesRegex(DistributionRefusal, "SIGNATURE_EVIDENCE_REQUIRED"):
            artifact(
                "apk",
                kind=ArtifactKind.APK,
                authority=AuthorityClass.INSTALLABLE_BINARY,
                signature_status=SignatureStatus.UNKNOWN,
            )

    def test_installable_binary_signature_evidence_still_does_not_authorize_install(self):
        apk = artifact(
            "apk",
            kind=ArtifactKind.APK,
            authority=AuthorityClass.INSTALLABLE_BINARY,
            signature_status=SignatureStatus.VERIFIED,
            signature_evidence_ref="attestation:apk-signature:1",
        )
        m = manifest(apk)
        r = admit_distribution(m, expected_currentness_ref=CUR, observed_digests={"apk": "a" * 64})
        self.assertEqual(AdmissionDisposition.TRUST_READY, r.disposition)
        self.assertTrue(r.signature_ready)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.install_performed)

    def test_privacy_unsafe_defaults_are_refused(self):
        with self.assertRaisesRegex(DistributionRefusal, "TELEMETRY_DEFAULT_MUST_BE_OFF"):
            TrustedDistributionManifest(
                route_id="web",
                build_ref="build",
                manifest_generation="gen",
                source_currentness_ref=CUR,
                artifacts=(artifact(),),
                telemetry_default_enabled=True,
            )

    def test_network_code_fetch_authority_is_not_minted_by_manifest(self):
        with self.assertRaisesRegex(DistributionRefusal, "NETWORK_CODE_FETCH_AUTHORITY_REFUSED"):
            TrustedDistributionManifest(
                route_id="web",
                build_ref="build",
                manifest_generation="gen",
                source_currentness_ref=CUR,
                artifacts=(artifact(),),
                network_code_fetch_authorized=True,
            )

    def test_manifest_digest_is_stable_under_artifact_input_order(self):
        a = artifact("a", digest="a" * 64)
        b = artifact("b", digest="b" * 64)
        self.assertEqual(manifest(a, b).manifest_digest, manifest(b, a).manifest_digest)

    def test_artifact_currentness_mismatch_fails_closed(self):
        bad = DistributionArtifact(
            artifact_id="web",
            kind=ArtifactKind.WEB_APP,
            authority_class=AuthorityClass.CODE_EXECUTION,
            source_ref="github:repo:web",
            source_generation="commit",
            source_currentness_ref="old-currentness",
            content_sha256="a" * 64,
            byte_size=1,
            immutable_source=True,
        )
        m = manifest(bad)
        r = admit_distribution(m, expected_currentness_ref=CUR, observed_digests={"web": "a" * 64})
        self.assertEqual(AdmissionDisposition.REBASE_REQUIRED, r.disposition)
        self.assertIn("ARTIFACT_CURRENTNESS_MISMATCH:web", r.blockers)

    def test_strict_enum_and_sha_validation(self):
        with self.assertRaisesRegex(DistributionRefusal, "INVALID_KIND"):
            DistributionArtifact(
                artifact_id="x",
                kind="WEB_APP",
                authority_class=AuthorityClass.CODE_EXECUTION,
                source_ref="x",
                source_generation="g",
                source_currentness_ref=CUR,
                content_sha256="a" * 64,
                byte_size=1,
                immutable_source=True,
            )
        with self.assertRaisesRegex(DistributionRefusal, "INVALID_CONTENT_SHA256"):
            artifact(digest="not-a-digest")


if __name__ == "__main__":
    unittest.main()
