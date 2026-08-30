from __future__ import annotations

import copy
import unittest

from tools.aura_adopt.share_capsule import (
    Attribution,
    BindingEvidence,
    EvidenceRef,
    RouteEvidence,
    ShareCapsule,
)
from tools.aura_adopt import share_distribution_trust_bridge as bridge

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64


def capsule():
    return ShareCapsule(
        capsule_id="share.creator.titlecard.v1",
        version="1.0.0",
        creator_ref="creator:alice",
        purpose="Reproduce a deterministic local title-card workflow",
        source=EvidenceRef("source:zf01-witness", D1, "gen-1", "CURRENT"),
        recipe=EvidenceRef("recipe:title-card", D2, "gen-2", "CURRENT"),
        accepted_output=EvidenceRef("output:accepted-title-card", D3, "gen-3", "CURRENT"),
        distribution=EvidenceRef("distribution:web-witness", D4, "gen-4", "CURRENT"),
        entry_surface_preference="ZERO_INSTALL_WEB_PWA",
        attribution=(
            Attribution(
                "creator:alice",
                "ORIGINAL_CREATOR",
                EvidenceRef("identity:alice", D5, "idgen-1", "CURRENT"),
            ),
            Attribution(
                "creator:bob",
                "RECIPE_AUTHOR",
                EvidenceRef("identity:bob", D6, "idgen-2", "CURRENT"),
            ),
        ),
        constraints={"privacy": "NO_RECIPIENT_TRACKING"},
    )


def bindings(*, forged_distribution_trust="TRUST_READY"):
    return {
        "source:zf01-witness": BindingEvidence("source:zf01-witness", D1, "gen-1", "CURRENT"),
        "recipe:title-card": BindingEvidence("recipe:title-card", D2, "gen-2", "CURRENT"),
        "output:accepted-title-card": BindingEvidence("output:accepted-title-card", D3, "gen-3", "CURRENT"),
        "distribution:web-witness": BindingEvidence(
            "distribution:web-witness", D4, "gen-4", "CURRENT", forged_distribution_trust
        ),
        "identity:alice": BindingEvidence("identity:alice", D5, "idgen-1", "CURRENT"),
        "identity:bob": BindingEvidence("identity:bob", D6, "idgen-2", "CURRENT"),
    }


def route():
    return RouteEvidence("ZERO_INSTALL_WEB_PWA", "AVAILABLE")


def manifest_view(**artifact_overrides):
    c = capsule()
    artifact = {
        "artifact_id": "web-witness-v1",
        "kind": "WEB_APP",
        "authority_class": "USER_GESTURE_LOCAL",
        "source_ref": c.distribution.ref,
        "source_generation": c.distribution.source_generation,
        "source_currentness_ref": "currentness:dist-1",
        "content_sha256": c.distribution.digest,
        "byte_size": 1024,
        "immutable_source": True,
        "version": "1.0.0",
        "origin_uri": "https://downloads.example.test/web-witness-v1.json",
        "channel": "STABLE",
        "media_type": "application/json",
        "capability_ids": [],
        "required_permissions": [],
        "optional_permissions": [],
        "binary_signature_evidence_ref": "",
    }
    artifact.update(artifact_overrides)
    logical = {
        "schema": "TrustedDistributionManifestV1",
        "route_id": "zf01-zero-install",
        "build_ref": "github:zf01@pinned",
        "manifest_generation": "manifest-gen-1",
        "source_currentness_ref": "currentness:dist-1",
        "signer": {
            "signer_id": "signer:aura",
            "key_id": "key:aura:1",
            "key_generation": "keygen-1",
            "algorithm": "ED25519",
        },
        "supersedes_manifest_digest": "",
        "rollback_of_manifest_digest": "",
        "update_policy": "PINNED_ONLY",
        "telemetry_default_enabled": False,
        "content_upload_default_enabled": False,
        "network_code_fetch_authorized": False,
        "public_distribution_authorized": False,
        "artifacts": [artifact],
    }
    return {**logical, "manifest_digest": bridge._digest(logical)}


def receipt(view, *, disposition="TRUST_READY", blockers=None, **overrides):
    row = {
        "schema": "DistributionAdmissionReceiptV1",
        "manifest_digest": view["manifest_digest"],
        "route_id": view["route_id"],
        "disposition": disposition,
        "blockers": [] if blockers is None and disposition == "TRUST_READY" else (blockers or ["TRUST_EVIDENCE_REQUIRED"]),
        "verified_artifact_ids": ["web-witness-v1"],
        "added_required_permissions": [],
        "removed_required_permissions": [],
        "integrity_ready": disposition == "TRUST_READY",
        "signature_ready": disposition == "TRUST_READY",
        "currentness_ready": disposition != "REBASE_REQUIRED",
        "effect_authorized": False,
        "execution_authorized": False,
        "execution_proven": False,
        "install_performed": False,
        "update_performed": False,
        "network_fetch_performed": False,
        "public_distribution_performed": False,
    }
    row.update(overrides)
    return row


def resolver(row):
    def resolve(manifest_digest):
        if manifest_digest != row["manifest_digest"]:
            raise AssertionError("wrong manifest digest passed to resolver")
        return dict(row)
    return resolve


def compile_with(view, row, *, caller_trust="TRUST_READY"):
    return bridge.compile_share_launch_with_canonical_distribution(
        capsule=capsule(),
        current_bindings=bindings(forged_distribution_trust=caller_trust),
        route_evidence=route(),
        distribution_manifest_view=view,
        canonical_distribution_receipt_resolver=resolver(row),
    )


class ShareDistributionTrustBridgeTests(unittest.TestCase):
    def test_canonical_trust_ready_allows_share_launch(self):
        view = manifest_view()
        result = compile_with(view, receipt(view))
        self.assertEqual("TRUST_READY", result["canonical_distribution_trust_state"])
        self.assertEqual("READY_FOR_USER_ACTION", result["share_launch_plan"]["status"])
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["adoption_success_proven"])

    def test_caller_forged_trust_ready_is_overwritten_by_canonical_evidence_required(self):
        view = manifest_view()
        row = receipt(
            view,
            disposition="SIGNATURE_EVIDENCE_REQUIRED",
            blockers=["TRUST_EVIDENCE_REQUIRED"],
            integrity_ready=False,
            signature_ready=False,
        )
        result = compile_with(view, row, caller_trust="TRUST_READY")
        self.assertEqual("UNKNOWN", result["canonical_distribution_trust_state"])
        self.assertEqual("EVIDENCE_REQUIRED", result["share_launch_plan"]["status"])
        self.assertIn(
            "DISTRIBUTION_TRUST_NOT_READY:UNKNOWN",
            result["share_launch_plan"]["blockers"],
        )

    def test_caller_blocked_trust_is_replaced_by_canonical_ready(self):
        view = manifest_view()
        result = compile_with(view, receipt(view), caller_trust="TRUST_BLOCKED")
        self.assertEqual("READY_FOR_USER_ACTION", result["share_launch_plan"]["status"])
        self.assertEqual("TRUST_READY", result["canonical_distribution_trust_state"])

    def test_rebase_required_maps_to_stale_unknown_trust(self):
        view = manifest_view()
        row = receipt(
            view,
            disposition="REBASE_REQUIRED",
            blockers=["CURRENTNESS_MISMATCH"],
            integrity_ready=False,
            signature_ready=False,
            currentness_ready=False,
        )
        result = compile_with(view, row)
        self.assertEqual("STALE", result["canonical_distribution_currentness"])
        self.assertEqual("UNKNOWN", result["canonical_distribution_trust_state"])
        self.assertEqual("EVIDENCE_REQUIRED", result["share_launch_plan"]["status"])

    def test_policy_refused_maps_to_trust_blocked(self):
        view = manifest_view()
        row = receipt(
            view,
            disposition="POLICY_REFUSED",
            blockers=["ORIGIN_HOST_NOT_ALLOWED:web-witness-v1"],
            integrity_ready=False,
            signature_ready=False,
            currentness_ready=True,
        )
        result = compile_with(view, row)
        self.assertEqual("TRUST_BLOCKED", result["canonical_distribution_trust_state"])
        self.assertEqual("EVIDENCE_REQUIRED", result["share_launch_plan"]["status"])

    def test_manifest_content_digest_must_match_capsule_distribution(self):
        view = manifest_view(content_sha256="9" * 64)
        with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
            bridge.project_canonical_distribution_trust(
                capsule=capsule(),
                distribution_manifest_view=view,
                canonical_distribution_receipt_resolver=resolver(receipt(view)),
            )
        self.assertEqual("SHARE_DISTRIBUTION_DIGEST_MISMATCH", ctx.exception.code)

    def test_manifest_generation_must_match_capsule_distribution(self):
        view = manifest_view(source_generation="other-gen")
        with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
            bridge.project_canonical_distribution_trust(
                capsule=capsule(),
                distribution_manifest_view=view,
                canonical_distribution_receipt_resolver=resolver(receipt(view)),
            )
        self.assertEqual("SHARE_DISTRIBUTION_GENERATION_MISMATCH", ctx.exception.code)

    def test_forged_manifest_digest_fails_before_resolver(self):
        view = manifest_view()
        view["build_ref"] = "tampered"
        with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
            bridge.project_canonical_distribution_trust(
                capsule=capsule(),
                distribution_manifest_view=view,
                canonical_distribution_receipt_resolver=lambda _: (_ for _ in ()).throw(AssertionError()),
            )
        self.assertEqual("DISTRIBUTION_MANIFEST_DIGEST_MISMATCH", ctx.exception.code)

    def test_canonical_resolver_is_required(self):
        view = manifest_view()
        with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
            bridge.project_canonical_distribution_trust(
                capsule=capsule(),
                distribution_manifest_view=view,
                canonical_distribution_receipt_resolver=None,
            )
        self.assertEqual("CANONICAL_DISTRIBUTION_RECEIPT_RESOLVER_REQUIRED", ctx.exception.code)

    def test_cross_manifest_receipt_is_rejected(self):
        view = manifest_view()
        row = receipt(view)
        row["manifest_digest"] = "f" * 64
        with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
            bridge.project_canonical_distribution_trust(
                capsule=capsule(),
                distribution_manifest_view=view,
                canonical_distribution_receipt_resolver=lambda _: row,
            )
        self.assertEqual("CANONICAL_DISTRIBUTION_RECEIPT_MANIFEST_MISMATCH", ctx.exception.code)

    def test_receipt_authority_laundering_fails_closed(self):
        for field in (
            "effect_authorized",
            "execution_authorized",
            "execution_proven",
            "install_performed",
            "network_fetch_performed",
            "public_distribution_performed",
        ):
            view = manifest_view()
            row = receipt(view, **{field: True})
            with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
                bridge.project_canonical_distribution_trust(
                    capsule=capsule(),
                    distribution_manifest_view=view,
                    canonical_distribution_receipt_resolver=resolver(row),
                )
            self.assertEqual("CANONICAL_DISTRIBUTION_RECEIPT_AUTHORITY_WIDENING", ctx.exception.code)

    def test_trust_ready_requires_target_artifact_verified(self):
        view = manifest_view()
        row = receipt(view, verified_artifact_ids=[])
        with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
            bridge.project_canonical_distribution_trust(
                capsule=capsule(),
                distribution_manifest_view=view,
                canonical_distribution_receipt_resolver=resolver(row),
            )
        self.assertEqual("TRUST_READY_ARTIFACT_NOT_VERIFIED", ctx.exception.code)

    def test_trust_ready_cannot_carry_blockers(self):
        view = manifest_view()
        row = receipt(view, blockers=["SHOULD_NOT_EXIST"])
        with self.assertRaises(bridge.ShareDistributionTrustError) as ctx:
            bridge.project_canonical_distribution_trust(
                capsule=capsule(),
                distribution_manifest_view=view,
                canonical_distribution_receipt_resolver=resolver(row),
            )
        self.assertEqual("TRUST_READY_RECEIPT_HAS_BLOCKERS", ctx.exception.code)

    def test_projection_identity_is_replay_stable(self):
        view = manifest_view()
        row = receipt(view)
        a = bridge.project_canonical_distribution_trust(
            capsule=capsule(),
            distribution_manifest_view=view,
            canonical_distribution_receipt_resolver=resolver(row),
        )
        b = bridge.project_canonical_distribution_trust(
            capsule=capsule(),
            distribution_manifest_view=view,
            canonical_distribution_receipt_resolver=resolver(row),
        )
        self.assertEqual(a.projection_digest, b.projection_digest)


if __name__ == "__main__":
    unittest.main()
