import os
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.dirname(__file__))

from trusted_distribution import (
    AdmissionStatus,
    ArtifactDescriptorV1,
    ArtifactKind,
    DistributionChannel,
    DistributionPolicyV1,
    Permission,
    RollbackAuthorizationV1,
    SignerRequirementV1,
    SourceBindingV1,
    TrustedDistributionManifestV1,
    TrustedVerificationEvidenceV1,
    manifest_digest_sha256,
    verify_distribution_manifest,
)


A64 = "a" * 64
B64 = "b" * 64


def make_manifest(
    *,
    version="1.0.0",
    sha=A64,
    size=100,
    channel=DistributionChannel.STABLE,
    required=(),
    optional=(),
    supersedes=None,
    rollback_of=None,
    artifact_id="aura.web.studio",
    kind=ArtifactKind.WEB_BUNDLE,
    origin="https://example.invalid/aura.tgz",
):
    manifest = TrustedDistributionManifestV1(
        artifact=ArtifactDescriptorV1(
            artifact_id=artifact_id,
            version=version,
            kind=kind,
            sha256_hex=sha,
            size_bytes=size,
            origin_uri=origin,
            channel=channel,
            capability_ids=("creator.short.card",),
            required_permissions=tuple(required),
            optional_permissions=tuple(optional),
        ),
        source=SourceBindingV1(
            source_ref="repo://AuraOS@head",
            source_generation="g1",
            source_currentness_ref="src-current-1",
            source_digest_sha256=B64,
        ),
        signer=SignerRequirementV1(
            signer_id="aura-release",
            key_id="release-key",
            key_generation="k1",
        ),
        supersedes_manifest_id=supersedes,
        rollback_of_manifest_id=rollback_of,
    )
    return manifest.with_computed_id()


def evidence_for(manifest):
    return TrustedVerificationEvidenceV1(
        manifest_id=manifest.manifest_id,
        manifest_digest_sha256=manifest_digest_sha256(manifest),
        artifact_sha256_hex=manifest.artifact.sha256_hex,
        signer_id=manifest.signer.signer_id,
        key_id=manifest.signer.key_id,
        key_generation=manifest.signer.key_generation,
        trust_store_generation="trust-g1",
        verification_source_ref="host://trusted-verifier",
        verification_currentness_ref="trust-current-1",
        signature_verified=True,
    )


def policy(**kwargs):
    values = dict(
        current_source_currentness_ref="src-current-1",
        current_trust_store_generation="trust-g1",
        current_trust_currentness_ref="trust-current-1",
        allowed_channels=(DistributionChannel.STABLE,),
        allowed_required_permissions=(
            Permission.LOCAL_FILE_READ,
            Permission.LOCAL_FILE_WRITE,
            Permission.NETWORK,
        ),
        allowed_origin_hosts=("example.invalid",),
        trusted_verifier_refs=("host://trusted-verifier",),
    )
    values.update(kwargs)
    return DistributionPolicyV1(**values)


def admit(manifest, *, evidence=None, pol=None, previous=None, observed_sha=None, observed_size=None):
    return verify_distribution_manifest(
        manifest,
        observed_artifact_sha256_hex=observed_sha or manifest.artifact.sha256_hex,
        observed_artifact_size_bytes=(
            manifest.artifact.size_bytes if observed_size is None else observed_size
        ),
        evidence=evidence_for(manifest) if evidence is None else evidence,
        policy=policy() if pol is None else pol,
        previous_manifest=previous,
    )


class TrustedDistributionTests(unittest.TestCase):
    def test_positive_control(self):
        receipt = admit(make_manifest())
        self.assertEqual(receipt.status, AdmissionStatus.ADMISSIBLE)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.install_authorized)
        self.assertFalse(receipt.update_authorized)
        self.assertFalse(receipt.execution_proven)

    def test_manifest_id_tamper_refused(self):
        manifest = replace(make_manifest(), manifest_id="tdm1:" + "0" * 64)
        receipt = admit(manifest, evidence=evidence_for(manifest))
        self.assertEqual(receipt.status, AdmissionStatus.REFUSED)
        self.assertIn("MANIFEST_ID_MISMATCH", receipt.reasons)

    def test_artifact_hash_mismatch_refused(self):
        self.assertIn(
            "ARTIFACT_DIGEST_MISMATCH",
            admit(make_manifest(), observed_sha="c" * 64).reasons,
        )

    def test_artifact_size_mismatch_refused(self):
        self.assertIn("ARTIFACT_SIZE_MISMATCH", admit(make_manifest(), observed_size=99).reasons)

    def test_untrusted_origin_host_refused(self):
        manifest = make_manifest(origin="https://evil.invalid/aura.tgz")
        self.assertIn("ORIGIN_HOST_NOT_ALLOWED", admit(manifest).reasons)

    def test_untrusted_verification_source_refused(self):
        manifest = make_manifest()
        evidence = replace(evidence_for(manifest), verification_source_ref="caller://self-asserted")
        self.assertIn("UNTRUSTED_VERIFICATION_SOURCE", admit(manifest, evidence=evidence).reasons)

    def test_unsigned_refused(self):
        manifest = make_manifest()
        evidence = replace(evidence_for(manifest), signature_verified=False)
        self.assertIn("SIGNATURE_NOT_VERIFIED", admit(manifest, evidence=evidence).reasons)

    def test_no_trust_evidence_refused(self):
        manifest = make_manifest()
        receipt = verify_distribution_manifest(
            manifest,
            observed_artifact_sha256_hex=manifest.artifact.sha256_hex,
            observed_artifact_size_bytes=manifest.artifact.size_bytes,
            evidence=None,
            policy=policy(),
        )
        self.assertIn("TRUST_EVIDENCE_REQUIRED", receipt.reasons)

    def test_recipe_without_signature_evidence_is_admissible_but_non_authoritative(self):
        manifest = make_manifest(
            artifact_id="recipe.neon-amber",
            kind=ArtifactKind.ARENA_RECIPE,
            channel=DistributionChannel.RECIPE,
        )
        receipt = verify_distribution_manifest(
            manifest,
            observed_artifact_sha256_hex=manifest.artifact.sha256_hex,
            observed_artifact_size_bytes=manifest.artifact.size_bytes,
            evidence=None,
            policy=policy(allowed_channels=(DistributionChannel.RECIPE,)),
        )
        self.assertEqual(receipt.status, AdmissionStatus.ADMISSIBLE)
        self.assertFalse(receipt.effect_authorized)
        self.assertFalse(receipt.install_authorized)
        self.assertFalse(receipt.update_authorized)
        self.assertFalse(receipt.execution_proven)

    def test_recipe_integrity_still_fails_without_signature_evidence(self):
        manifest = make_manifest(
            artifact_id="recipe.neon-amber",
            kind=ArtifactKind.ARENA_RECIPE,
            channel=DistributionChannel.RECIPE,
        )
        receipt = verify_distribution_manifest(
            manifest,
            observed_artifact_sha256_hex="c" * 64,
            observed_artifact_size_bytes=manifest.artifact.size_bytes,
            evidence=None,
            policy=policy(allowed_channels=(DistributionChannel.RECIPE,)),
        )
        self.assertEqual(receipt.status, AdmissionStatus.REFUSED)
        self.assertIn("ARTIFACT_DIGEST_MISMATCH", receipt.reasons)

    def test_recipe_optional_evidence_must_not_launder_untrusted_verifier(self):
        manifest = make_manifest(
            artifact_id="recipe.neon-amber",
            kind=ArtifactKind.ARENA_RECIPE,
            channel=DistributionChannel.RECIPE,
        )
        evidence = replace(
            evidence_for(manifest),
            verification_source_ref="caller://self-asserted",
            signature_verified=False,
        )
        receipt = verify_distribution_manifest(
            manifest,
            observed_artifact_sha256_hex=manifest.artifact.sha256_hex,
            observed_artifact_size_bytes=manifest.artifact.size_bytes,
            evidence=evidence,
            policy=policy(allowed_channels=(DistributionChannel.RECIPE,)),
        )
        self.assertEqual(receipt.status, AdmissionStatus.REFUSED)
        self.assertIn("UNTRUSTED_VERIFICATION_SOURCE", receipt.reasons)
        self.assertNotIn("SIGNATURE_NOT_VERIFIED", receipt.reasons)

    def test_recipe_signature_bit_is_not_a_binary_gate(self):
        manifest = make_manifest(
            artifact_id="recipe.neon-amber",
            kind=ArtifactKind.ARENA_RECIPE,
            channel=DistributionChannel.RECIPE,
        )
        evidence = replace(evidence_for(manifest), signature_verified=False)
        receipt = verify_distribution_manifest(
            manifest,
            observed_artifact_sha256_hex=manifest.artifact.sha256_hex,
            observed_artifact_size_bytes=manifest.artifact.size_bytes,
            evidence=evidence,
            policy=policy(allowed_channels=(DistributionChannel.RECIPE,)),
        )
        self.assertEqual(receipt.status, AdmissionStatus.ADMISSIBLE)
        self.assertFalse(receipt.execution_proven)

    def test_revoked_key_refused(self):
        manifest = make_manifest()
        evidence = replace(evidence_for(manifest), key_revoked=True)
        self.assertIn("SIGNING_KEY_REVOKED", admit(manifest, evidence=evidence).reasons)

    def test_wrong_signer_refused(self):
        manifest = make_manifest()
        evidence = replace(evidence_for(manifest), signer_id="attacker")
        self.assertIn("TRUST_SIGNER_MISMATCH", admit(manifest, evidence=evidence).reasons)

    def test_stale_source_rebases(self):
        receipt = admit(make_manifest(), pol=policy(current_source_currentness_ref="src-current-2"))
        self.assertEqual(receipt.status, AdmissionStatus.REBASE_REQUIRED)
        self.assertIn("SOURCE_CURRENTNESS_STALE", receipt.reasons)

    def test_stale_trust_store_rebases(self):
        receipt = admit(make_manifest(), pol=policy(current_trust_store_generation="trust-g2"))
        self.assertEqual(receipt.status, AdmissionStatus.REBASE_REQUIRED)
        self.assertIn("TRUST_STORE_GENERATION_STALE", receipt.reasons)

    def test_stale_verification_currentness_rebases(self):
        manifest = make_manifest()
        evidence = replace(evidence_for(manifest), verification_currentness_ref="trust-current-old")
        receipt = admit(manifest, evidence=evidence)
        self.assertEqual(receipt.status, AdmissionStatus.REBASE_REQUIRED)
        self.assertIn("TRUST_CURRENTNESS_STALE", receipt.reasons)

    def test_disallowed_origin_refused(self):
        manifest = make_manifest(origin="http://example.invalid/aura.tgz")
        self.assertIn("ORIGIN_SCHEME_NOT_ALLOWED", admit(manifest).reasons)

    def test_disallowed_channel_refused(self):
        manifest = make_manifest(channel=DistributionChannel.DEV)
        self.assertIn("CHANNEL_NOT_ALLOWED", admit(manifest).reasons)

    def test_permission_above_policy_refused(self):
        manifest = make_manifest(required=(Permission.CAMERA,))
        self.assertIn("REQUIRED_PERMISSION_EXCEEDS_POLICY", admit(manifest).reasons)

    def test_permission_overlap_refused(self):
        manifest = make_manifest(required=(Permission.NETWORK,), optional=(Permission.NETWORK,))
        self.assertIn("PERMISSION_CLASS_OVERLAP", admit(manifest).reasons)

    def test_update_requires_exact_supersession(self):
        old = make_manifest(version="1.0.0")
        new = make_manifest(version="1.1.0", supersedes=None)
        self.assertIn("SUPERSESSION_BINDING_REQUIRED", admit(new, previous=old).reasons)

    def test_new_required_permission_requires_consent(self):
        old = make_manifest(version="1.0.0", required=(Permission.NETWORK,))
        new = make_manifest(
            version="1.1.0",
            required=(Permission.NETWORK, Permission.LOCAL_FILE_READ),
            supersedes=old.manifest_id,
        )
        receipt = admit(new, previous=old)
        self.assertEqual(receipt.status, AdmissionStatus.CONSENT_REQUIRED)
        self.assertEqual(receipt.added_required_permissions, (Permission.LOCAL_FILE_READ,))

    def test_permission_removal_admissible(self):
        old = make_manifest(
            version="1.0.0",
            required=(Permission.NETWORK, Permission.LOCAL_FILE_READ),
        )
        new = make_manifest(
            version="1.1.0",
            required=(Permission.NETWORK,),
            supersedes=old.manifest_id,
        )
        receipt = admit(new, previous=old)
        self.assertEqual(receipt.status, AdmissionStatus.ADMISSIBLE)
        self.assertEqual(receipt.removed_required_permissions, (Permission.LOCAL_FILE_READ,))

    def test_channel_change_refused_by_default(self):
        old = make_manifest(version="1.0.0", channel=DistributionChannel.STABLE)
        new = make_manifest(
            version="1.1.0",
            channel=DistributionChannel.BETA,
            supersedes=old.manifest_id,
        )
        pol = policy(allowed_channels=(DistributionChannel.STABLE, DistributionChannel.BETA))
        self.assertIn("CHANNEL_CHANGE_NOT_ALLOWED", admit(new, previous=old, pol=pol).reasons)

    def test_rollback_requires_binding_and_authority(self):
        old = make_manifest(version="2.0.0")
        new = make_manifest(version="1.0.0", supersedes=old.manifest_id)
        receipt = admit(new, previous=old)
        self.assertIn("ROLLBACK_BINDING_REQUIRED", receipt.reasons)
        self.assertIn("ROLLBACK_AUTHORITY_REQUIRED", receipt.reasons)

    def test_authorized_rollback_admissible(self):
        old = make_manifest(version="2.0.0")
        new = make_manifest(
            version="1.0.0",
            supersedes=old.manifest_id,
            rollback_of=old.manifest_id,
        )
        auth = RollbackAuthorizationV1(
            from_manifest_id=old.manifest_id,
            to_manifest_id=new.manifest_id,
            authority_ref="owner://rollback/1",
            authority_currentness_ref="trust-current-1",
            authorized=True,
        )
        receipt = admit(new, previous=old, pol=policy(rollback_authorization=auth))
        self.assertEqual(receipt.status, AdmissionStatus.ADMISSIBLE)

    def test_rollback_marker_on_upgrade_refused(self):
        old = make_manifest(version="1.0.0")
        new = make_manifest(
            version="2.0.0",
            supersedes=old.manifest_id,
            rollback_of=old.manifest_id,
        )
        self.assertIn("ROLLBACK_MARKER_ON_NONROLLBACK", admit(new, previous=old).reasons)

    def test_artifact_identity_change_refused(self):
        old = make_manifest(version="1.0.0")
        new = make_manifest(version="1.1.0", artifact_id="different", supersedes=old.manifest_id)
        self.assertIn("ARTIFACT_ID_CHANGED", admit(new, previous=old).reasons)

    def test_artifact_kind_change_refused(self):
        old = make_manifest(version="1.0.0")
        new = make_manifest(
            version="1.1.0",
            kind=ArtifactKind.ANDROID_APK,
            supersedes=old.manifest_id,
        )
        self.assertIn("ARTIFACT_KIND_CHANGED", admit(new, previous=old).reasons)

    def test_unresolved_supersession_without_previous_refused(self):
        manifest = make_manifest(supersedes="tdm1:" + "0" * 64)
        self.assertIn("UNRESOLVED_SUPERSESSION", admit(manifest).reasons)

    def test_trust_artifact_digest_mismatch_refused(self):
        manifest = make_manifest()
        evidence = replace(evidence_for(manifest), artifact_sha256_hex="c" * 64)
        self.assertIn("TRUST_ARTIFACT_DIGEST_MISMATCH", admit(manifest, evidence=evidence).reasons)

    def test_trust_key_generation_mismatch_refused(self):
        manifest = make_manifest()
        evidence = replace(evidence_for(manifest), key_generation="old")
        self.assertIn("TRUST_KEY_GENERATION_MISMATCH", admit(manifest, evidence=evidence).reasons)


if __name__ == "__main__":
    unittest.main()