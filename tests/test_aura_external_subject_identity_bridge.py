from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_external_subject_identity_bridge import (
    CurrentExternalSubjectProjectionV1,
    IdentityBridgeDisposition,
    LegacyExternalIdentityProjectionV1,
    VOCABULARY_MAP,
    bridge_external_subject_identity,
    current_subject_key,
    legacy_semantic_id,
)


def legacy(*, source_kind="GITHUB", canonical_id="owner/repo", canonical_uri="https://github.com/owner/repo"):
    return LegacyExternalIdentityProjectionV1(
        source_kind=source_kind,
        canonical_id=canonical_id,
        canonical_uri=canonical_uri,
        semantic_id=legacy_semantic_id(source_kind=source_kind, canonical_id=canonical_id),
        artifact_class="CODE",
        source_generation_id="a" * 64,
    )


def current(*, provider="GITHUB", source_kind="REPOSITORY", canonical_id="owner/repo", canonical_uri="https://github.com/owner/repo"):
    return CurrentExternalSubjectProjectionV1(
        provider=provider,
        source_kind=source_kind,
        canonical_id=canonical_id,
        canonical_uri=canonical_uri,
        subject_key=current_subject_key(provider=provider, source_kind=source_kind, canonical_id=canonical_id),
        sector="06_RUN",
        evidence_generation_key="b" * 64,
    )


class ExternalSubjectIdentityBridgeTests(unittest.TestCase):
    def test_github_exact_mapping_matches_subject_but_not_generation(self):
        receipt = bridge_external_subject_identity(legacy=legacy(), current=current())
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.MATCHED_SUBJECT)
        self.assertTrue(receipt.same_external_subject)
        self.assertNotEqual(receipt.legacy_semantic_id, receipt.current_subject_key)
        self.assertEqual(receipt.mapping_rule, "GITHUB->GITHUB+REPOSITORY")
        self.assertFalse(receipt.version_equivalence_proven)
        self.assertFalse(receipt.generation_equivalence_proven)
        self.assertFalse(receipt.current_version_selected)
        self.assertFalse(receipt.source_currentness_proven)
        self.assertFalse(receipt.record_currentness_proven)
        self.assertFalse(receipt.write_authority)
        self.assertFalse(receipt.read_authority)
        self.assertFalse(receipt.effect_authority)

    def test_all_declared_vocabulary_rules_are_deterministically_bridgeable(self):
        fixtures = {
            "ARXIV": ("ARXIV", "PAPER", "arXiv:2606.26511", "https://arxiv.org/abs/2606.26511"),
            "GITHUB": ("GITHUB", "REPOSITORY", "owner/repo", "https://github.com/owner/repo"),
            "HUGGINGFACE_MODEL": ("HUGGING_FACE", "MODEL", "owner/model", "https://huggingface.co/owner/model"),
            "HUGGINGFACE_DATASET": ("HUGGING_FACE", "DATASET", "owner/data", "https://huggingface.co/datasets/owner/data"),
            "HUGGINGFACE_SPACE": ("HUGGING_FACE", "SPACE", "owner/space", "https://huggingface.co/spaces/owner/space"),
            "GOOGLE_SCHOLAR_DISCOVERY": ("GOOGLE_SCHOLAR", "PAPER", "doi:10.1/example", "https://doi.org/10.1/example"),
            "REDDIT": ("REDDIT", "DISCUSSION", "reddit:t3_example", "https://www.reddit.com/r/test/comments/example"),
            "WEB": ("WEB", "WEB_PAGE", "example:page", "https://example.org/page"),
        }
        self.assertEqual(set(fixtures), set(VOCABULARY_MAP))
        for legacy_kind, (provider, current_kind, cid, uri) in fixtures.items():
            with self.subTest(legacy_kind=legacy_kind):
                receipt = bridge_external_subject_identity(
                    legacy=legacy(source_kind=legacy_kind, canonical_id=cid, canonical_uri=uri),
                    current=current(provider=provider, source_kind=current_kind, canonical_id=cid, canonical_uri=uri),
                )
                self.assertEqual(receipt.disposition, IdentityBridgeDisposition.MATCHED_SUBJECT)
                self.assertTrue(receipt.same_external_subject)

    def test_unsupported_legacy_kind_holds(self):
        old = legacy(source_kind="PACKAGE_REGISTRY")
        now = current(provider="PACKAGE_REGISTRY", source_kind="PACKAGE")
        receipt = bridge_external_subject_identity(legacy=old, current=now)
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.HOLD_UNSUPPORTED_LEGACY_KIND)
        self.assertFalse(receipt.same_external_subject)

    def test_provider_kind_crosscast_holds_even_with_same_canonical_id(self):
        receipt = bridge_external_subject_identity(
            legacy=legacy(source_kind="GITHUB"),
            current=current(provider="WEB", source_kind="WEB_PAGE"),
        )
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.HOLD_VOCABULARY_MAPPING_MISMATCH)
        self.assertFalse(receipt.same_external_subject)

    def test_canonical_id_drift_holds(self):
        receipt = bridge_external_subject_identity(
            legacy=legacy(canonical_id="owner/repo"),
            current=current(canonical_id="owner/other"),
        )
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.HOLD_CANONICAL_ID_MISMATCH)

    def test_canonical_uri_alias_drift_holds_even_when_both_parent_hashes_are_valid(self):
        receipt = bridge_external_subject_identity(
            legacy=legacy(canonical_uri="https://github.com/owner/repo"),
            current=current(canonical_uri="https://github.com/owner/repo.git"),
        )
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.HOLD_CANONICAL_URI_MISMATCH)

    def test_legacy_digest_substitution_holds(self):
        receipt = bridge_external_subject_identity(
            legacy=replace(legacy(), semantic_id="0" * 64),
            current=current(),
        )
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.HOLD_LEGACY_IDENTITY_DIGEST_MISMATCH)

    def test_current_digest_substitution_holds(self):
        receipt = bridge_external_subject_identity(
            legacy=legacy(),
            current=replace(current(), subject_key="0" * 64),
        )
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.HOLD_CURRENT_IDENTITY_DIGEST_MISMATCH)

    def test_classification_and_sector_are_not_cross_schema_identity_inputs(self):
        a = bridge_external_subject_identity(legacy=legacy(), current=current())
        b = bridge_external_subject_identity(
            legacy=replace(legacy(), artifact_class="TOOL"),
            current=replace(current(), sector="08_RSH"),
        )
        self.assertEqual(a.disposition, IdentityBridgeDisposition.MATCHED_SUBJECT)
        self.assertEqual(b.disposition, IdentityBridgeDisposition.MATCHED_SUBJECT)
        self.assertEqual(a.legacy_semantic_id, b.legacy_semantic_id)
        self.assertEqual(a.current_subject_key, b.current_subject_key)

    def test_generation_values_remain_visible_but_never_become_equivalent(self):
        receipt = bridge_external_subject_identity(
            legacy=replace(legacy(), source_generation_id="c" * 64),
            current=replace(current(), evidence_generation_key="d" * 64),
        )
        self.assertEqual(receipt.disposition, IdentityBridgeDisposition.MATCHED_SUBJECT)
        self.assertEqual(receipt.legacy_source_generation_id, "c" * 64)
        self.assertEqual(receipt.current_evidence_generation_key, "d" * 64)
        self.assertFalse(receipt.generation_equivalence_proven)
        self.assertFalse(receipt.current_version_selected)

    def test_receipt_is_deterministic_and_k27_never_enters_relation(self):
        a = bridge_external_subject_identity(legacy=legacy(), current=current())
        b = bridge_external_subject_identity(legacy=legacy(), current=current())
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertFalse(a.semantic_k27_authority)
        self.assertFalse(a.native_private_transformer_kv_accessed)

    def test_matched_receipt_cannot_be_resealed_with_authority_or_current_version(self):
        receipt = bridge_external_subject_identity(legacy=legacy(), current=current())
        with self.assertRaisesRegex(ValueError, "CURRENT_VERSION_SELECTED_MUST_REMAIN_FALSE"):
            replace(receipt, current_version_selected=True).validate()
        with self.assertRaisesRegex(ValueError, "SOURCE_CURRENTNESS_PROVEN_MUST_REMAIN_FALSE"):
            replace(receipt, source_currentness_proven=True).validate()
        with self.assertRaisesRegex(ValueError, "WRITE_AUTHORITY_MUST_REMAIN_FALSE"):
            replace(receipt, write_authority=True).validate()


if __name__ == "__main__":
    unittest.main()
