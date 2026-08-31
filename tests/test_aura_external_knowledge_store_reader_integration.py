from __future__ import annotations

from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import unittest

from tools import aura_external_knowledge_ingress as eki1
from tools import aura_external_knowledge_store_writer as eki2


def _load_pr728_reader():
    path = os.environ.get("AURA_PR728_READER_FILE")
    if not path:
        raise unittest.SkipTest("AURA_PR728_READER_FILE is required for cross-owner integration proof")
    source = Path(path)
    if not source.is_file():
        raise AssertionError(f"PR728 reader file missing: {source}")
    spec = importlib.util.spec_from_file_location("aura_pr728_reader_exact", source)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load exact PR728 reader module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generation(value: str = "rev-a", digest: str = "a" * 64):
    return eki1.SourceGeneration(
        generation_type="IMMUTABLE_REVISION",
        generation_value=value,
        checked_at="2026-08-31T17:10:00Z",
        exact_source_uri=f"https://example.org/tool/{value}",
        content_sha256=digest,
    )


def _card(*, generation=None, relevance=eki1.RelevanceBand.MEDIUM):
    observation = eki1.ExternalDiscoveryObservation(
        source_kind=eki1.SourceKind.GITHUB,
        artifact_class=eki1.ArtifactClass.TOOL,
        canonical_id="owner/tool",
        canonical_uri="https://github.com/owner/tool",
        title="Owner Tool",
        thesis="Cross-owner EKI writer-reader integration fixture.",
        currentness=eki1.Currentness.CURRENT,
        generation=generation or _generation(),
        rights=eki1.RightsMetadata(
            state=eki1.RightsState.DECLARED,
            license_expression="MIT",
        ),
        security=eki1.SecurityMetadata(
            state=eki1.SecurityState.METADATA_RECORDED,
            remote_code_requested=False,
            network_capability=False,
            write_capability=False,
            secret_capability=False,
        ),
        authors_or_owner=("owner",),
        tags=("integration",),
        relevance=relevance,
    )
    return eki1.admit_external_knowledge(
        observation=observation,
        requested_level=eki1.HydrationLevel.L1,
    )


class ExternalKnowledgeStoreReaderIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader = _load_pr728_reader()

    def _adapter(self, compiled):
        return self.reader.ExternalCognitionResolveAdapterV1(
            snapshot_bytes=compiled.snapshot_bytes,
            store_ref="eki2://cross-owner-snapshot",
            store_generation=compiled.receipt.store_generation,
        )

    def _request(self, compiled, row, **overrides):
        values = dict(
            store_ref="eki2://cross-owner-snapshot",
            expected_store_generation=compiled.receipt.store_generation,
            expected_store_sha256=compiled.receipt.store_sha256,
            semantic_key=row.key,
            consumer_ref="auraos://arena/eki2-cross-owner-proof",
            consumer_generation="EKI2-INTEGRATION-v1",
            evidence_domain="SOURCE_BOUND_COORDINATE_MEMORY",
            principal="AURA_ARENA_READER",
            required_currentness_axes=("SOURCE_GENERATION_CURRENT", "SOURCE_BODY_CURRENT"),
            expected_value_digest=row.value["digest"],
            placement_hint=None,
        )
        values.update(overrides)
        return self.reader.ExternalCognitionReadRequestV1(**values)

    def _context(self, status):
        return self.reader.ReadValidationContextV1(
            currentness={
                "SOURCE_GENERATION_CURRENT": status,
                "SOURCE_BODY_CURRENT": status,
            },
            allowed_evidence_domains=frozenset({"SOURCE_BOUND_COORDINATE_MEMORY"}),
            allowed_principals=frozenset({"AURA_ARENA_READER"}),
            source_resolver_refs=("auraos://source-currentness-owner/v1",),
        )

    def test_current_external_witness_yields_candidate_only_found_verified(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))
        receipt = self._adapter(compiled).resolve(
            self._request(compiled, row),
            self._context(self.reader.CurrentnessStatus.RESOLVED_CURRENT),
        )
        self.assertEqual(receipt.disposition, self.reader.ResolveDisposition.FOUND_VERIFIED)
        self.assertIsNotNone(receipt.candidate)
        self.assertTrue(receipt.candidate_only)
        self.assertFalse(receipt.instruction_authority)
        self.assertFalse(receipt.write_authority)
        self.assertFalse(receipt.effect_authority)
        self.assertFalse(receipt.candidate.instruction_authority)
        self.assertFalse(receipt.candidate.write_authority)
        self.assertFalse(receipt.candidate.effect_authority)

    def test_persisted_current_label_cannot_replace_unknown_currentness_witness(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))
        receipt = self._adapter(compiled).resolve(
            self._request(compiled, row),
            self._context(self.reader.CurrentnessStatus.UNKNOWN),
        )
        self.assertEqual(
            receipt.disposition,
            self.reader.ResolveDisposition.SOURCE_REVALIDATION_REQUIRED,
        )
        self.assertIsNone(receipt.candidate)

    def test_stale_external_witness_reopens_even_when_persisted_label_is_current(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))
        receipt = self._adapter(compiled).resolve(
            self._request(compiled, row),
            self._context(self.reader.CurrentnessStatus.STALE),
        )
        self.assertEqual(receipt.disposition, self.reader.ResolveDisposition.CURRENTNESS_REOPEN)
        self.assertIsNone(receipt.candidate)

    def test_placement_only_relocalization_preserves_semantic_record_but_invalidates_old_store_generation(self):
        low = eki2.compile_row(_card(relevance=eki1.RelevanceBand.LOW))
        first = eki2.compile_store((low,))
        high = eki2.compile_row(_card(relevance=eki1.RelevanceBand.HIGH))
        second = eki2.compile_store((high,), existing_snapshot_bytes=first.snapshot_bytes)

        self.assertEqual(low.key, high.key)
        self.assertEqual(low.record_generation, high.record_generation)
        self.assertEqual(low.value["digest"], high.value["digest"])
        self.assertNotEqual(low.placement_generation, high.placement_generation)
        self.assertNotEqual(first.receipt.store_generation, second.receipt.store_generation)

        adapter = self._adapter(second)
        stale_request = self._request(
            second,
            high,
            expected_store_generation=first.receipt.store_generation,
            expected_store_sha256=first.receipt.store_sha256,
        )
        stale_receipt = adapter.resolve(
            stale_request,
            self._context(self.reader.CurrentnessStatus.RESOLVED_CURRENT),
        )
        self.assertEqual(stale_receipt.disposition, self.reader.ResolveDisposition.STORE_STALE)

        fresh_receipt = adapter.resolve(
            self._request(second, high),
            self._context(self.reader.CurrentnessStatus.RESOLVED_CURRENT),
        )
        self.assertEqual(fresh_receipt.disposition, self.reader.ResolveDisposition.FOUND_VERIFIED)

    def test_explicit_supersession_is_history_only_but_new_generation_remains_current_candidate(self):
        old = eki2.compile_row(_card(generation=_generation("rev-a", "a" * 64)))
        new = eki2.compile_row(_card(generation=_generation("rev-b", "b" * 64)))
        compiled = eki2.compile_store(
            (old, new),
            supersession_edges=((old.key, new.key),),
        )
        adapter = self._adapter(compiled)
        context = self._context(self.reader.CurrentnessStatus.RESOLVED_CURRENT)
        old_receipt = adapter.resolve(self._request(compiled, old), context)
        new_receipt = adapter.resolve(self._request(compiled, new), context)
        self.assertEqual(old_receipt.disposition, self.reader.ResolveDisposition.SUPERSEDED_HISTORY_ONLY)
        self.assertEqual(new_receipt.disposition, self.reader.ResolveDisposition.FOUND_VERIFIED)
        self.assertEqual(old_receipt.candidate.successor, new.key)

    def test_transformer_prefix_kv_responsibility_is_rejected(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))
        receipt = self._adapter(compiled).resolve(
            self._request(compiled, row, responsibility="MODEL_PREFIX_KV"),
            self._context(self.reader.CurrentnessStatus.RESOLVED_CURRENT),
        )
        self.assertEqual(
            receipt.disposition,
            self.reader.ResolveDisposition.WRONG_RESPONSIBILITY_OWNER,
        )
        self.assertIsNone(receipt.candidate)


if __name__ == "__main__":
    unittest.main()
