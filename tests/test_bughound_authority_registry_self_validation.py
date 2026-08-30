from __future__ import annotations

from dataclasses import replace
from unittest import mock
import unittest

import tools.bughound.authority_registry as registry_mod
from tools.bughound.authority_registry import (
    LIVE_EFFECT_PLANE,
    SANITIZER_PLANE,
    AuthorityProducerRecordV2,
    AuthorityRegistryError,
    authority_registry_receipt,
    resolve_authority_producer,
)


ARTIFACT = "a" * 64


class AuthorityRegistrySelfValidationTests(unittest.TestCase):
    def live_record(self, **changes):
        record = AuthorityProducerRecordV2(
            proof_plane=LIVE_EFFECT_PLANE,
            artifact_digest=ARTIFACT,
            producer_ref="owner-v1",
            producer_generation="gen-v1",
            producer_currentness_ref="current-v1",
        )
        return replace(record, **changes)

    def sanitizer_record(self, **changes):
        record = AuthorityProducerRecordV2(
            proof_plane=SANITIZER_PLANE,
            artifact_digest=ARTIFACT,
            producer_ref="sanitizer-v1",
            producer_generation="sanitizer-gen-v1",
            producer_currentness_ref="sanitizer-current-v1",
            reviewer_ref="reviewer-v1",
            reviewer_generation="reviewer-gen-v1",
            reviewer_currentness_ref="reviewer-current-v1",
        )
        return replace(record, **changes)

    def test_valid_exact_artifact_record_resolves(self):
        record = self.live_record()
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            resolved = resolve_authority_producer(
                proof_plane=LIVE_EFFECT_PLANE,
                artifact_digest=ARTIFACT,
                producer_ref="owner-v1",
                producer_generation="gen-v1",
                producer_currentness_ref="current-v1",
            )
            self.assertEqual(record.record_digest, resolved.record_digest)
            self.assertEqual(1, authority_registry_receipt().live_effect_producer_count)

    def test_authority_widened_registry_record_fails_closed(self):
        record = self.live_record(authority=True)
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            with self.assertRaises(AuthorityRegistryError) as ctx:
                authority_registry_receipt()
        self.assertEqual("AUTHORITY_REGISTRY_AUTHORITY_WIDENING", ctx.exception.code)

    def test_non_boolean_enabled_flag_fails_closed(self):
        record = self.live_record(enabled=1)
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            with self.assertRaises(AuthorityRegistryError) as ctx:
                authority_registry_receipt()
        self.assertEqual("AUTHORITY_REGISTRY_ENABLED_FLAG_INVALID", ctx.exception.code)

    def test_record_schema_mutation_fails_closed(self):
        record = self.live_record(schema="AuthorityProducerRecordV1")
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            with self.assertRaises(AuthorityRegistryError) as ctx:
                resolve_authority_producer(
                    proof_plane=LIVE_EFFECT_PLANE,
                    artifact_digest=ARTIFACT,
                    producer_ref="owner-v1",
                    producer_generation="gen-v1",
                    producer_currentness_ref="current-v1",
                )
        self.assertEqual("AUTHORITY_REGISTRY_RECORD_SCHEMA_MISMATCH", ctx.exception.code)

    def test_malformed_artifact_digest_fails_closed(self):
        record = self.live_record(artifact_digest="not-a-sha256")
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            with self.assertRaises(AuthorityRegistryError) as ctx:
                authority_registry_receipt()
        self.assertEqual("AUTHORITY_REGISTRY_ARTIFACT_DIGEST_INVALID", ctx.exception.code)

    def test_live_effect_record_cannot_smuggle_reviewer_identity(self):
        record = self.live_record(
            reviewer_ref="unexpected-reviewer",
            reviewer_generation="unexpected-gen",
            reviewer_currentness_ref="unexpected-current",
        )
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            with self.assertRaises(AuthorityRegistryError) as ctx:
                authority_registry_receipt()
        self.assertEqual("LIVE_EFFECT_REVIEWER_FIELDS_FORBIDDEN", ctx.exception.code)

    def test_sanitizer_record_requires_complete_reviewer_identity(self):
        record = self.sanitizer_record(reviewer_currentness_ref=None)
        with mock.patch.object(registry_mod, "_CANONICAL_RECORDS", (record,)):
            with self.assertRaises(AuthorityRegistryError) as ctx:
                authority_registry_receipt()
        self.assertEqual("SANITIZER_REVIEWER_FIELDS_REQUIRED", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
