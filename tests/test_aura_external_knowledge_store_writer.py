from __future__ import annotations

from dataclasses import replace
import json
import unittest

from tools import aura_external_knowledge_ingress as eki1
from tools import aura_external_knowledge_store_writer as eki2


def generation(value="rev-a", digest="a" * 64):
    return eki1.SourceGeneration(
        generation_type="IMMUTABLE_REVISION",
        generation_value=value,
        checked_at="2026-08-31T16:50:00Z",
        exact_source_uri=f"https://example.org/source/{value}",
        content_sha256=digest,
    )


def current_card(*, source_generation=None, relevance=eki1.RelevanceBand.MEDIUM, security=None):
    source_generation = source_generation or generation()
    security = security or eki1.SecurityMetadata(
        state=eki1.SecurityState.METADATA_RECORDED,
        remote_code_requested=False,
        network_capability=False,
        write_capability=False,
        secret_capability=False,
    )
    observation = eki1.ExternalDiscoveryObservation(
        source_kind=eki1.SourceKind.GITHUB,
        artifact_class=eki1.ArtifactClass.TOOL,
        canonical_id="owner/tool",
        canonical_uri="https://github.com/owner/tool",
        title="Example Tool",
        thesis="Example tool for deterministic tests.",
        currentness=eki1.Currentness.CURRENT,
        generation=source_generation,
        rights=eki1.RightsMetadata(
            state=eki1.RightsState.DECLARED,
            license_expression="MIT",
        ),
        security=security,
        authors_or_owner=("owner",),
        tags=("agent-tool",),
        relevance=relevance,
    )
    return eki1.admit_external_knowledge(
        observation=observation,
        requested_level=eki1.HydrationLevel.L1,
    )


def discovery_card(*, title="Discovery Tool"):
    observation = eki1.ExternalDiscoveryObservation(
        source_kind=eki1.SourceKind.GOOGLE_SCHOLAR_DISCOVERY,
        artifact_class=eki1.ArtifactClass.KNOWLEDGE,
        canonical_id="scholar:discovery:abc",
        canonical_uri="https://scholar.google.com/scholar?q=external+cognition",
        title=title,
        thesis="Discovery-only pointer.",
        currentness=eki1.Currentness.UNKNOWN,
        advisory_only=True,
    )
    return eki1.admit_external_knowledge(
        observation=observation,
        requested_level=eki1.HydrationLevel.L4,
    )


class ExternalKnowledgeStoreWriterTests(unittest.TestCase):
    def test_exact_reader_abi_shape(self):
        row = eki2.compile_row(current_card())
        wire = row.to_wire()
        self.assertIsInstance(wire["K"], str)
        self.assertEqual(
            set(wire["V"]),
            {"cell", "digest", "standing", "reopen", "successor"},
        )
        self.assertFalse(wire["V"]["cell"]["semantic_identity"])
        self.assertFalse(wire["V"]["cell"]["authority"])

    def test_snapshot_exact_store_schema(self):
        row = eki2.compile_row(current_card())
        compiled = eki2.compile_store((row,))
        parsed = json.loads(compiled.snapshot_bytes)
        self.assertEqual(
            parsed["schema"],
            {"name": "aura-coordinate-memory-kv-v1", "version": "1.0.0"},
        )
        self.assertEqual(len(parsed["rows"]), 1)
        self.assertEqual(compiled.receipt.row_count, 1)

    def test_record_key_is_versioned_and_not_k27_key(self):
        card = current_card()
        row = eki2.compile_row(card)
        self.assertTrue(row.key.startswith("external-cognition://"))
        self.assertIn(card.semantic_id, row.key)
        self.assertNotEqual(row.key, card.k27_locality["key"])
        self.assertFalse(row.value["cell"]["semantic_identity"])

    def test_source_generation_change_creates_distinct_record_key(self):
        first = eki2.compile_row(current_card(source_generation=generation("rev-a", "a" * 64)))
        second = eki2.compile_row(current_card(source_generation=generation("rev-b", "b" * 64)))
        self.assertNotEqual(first.key, second.key)
        self.assertNotEqual(first.value["digest"], second.value["digest"])

    def test_placement_change_preserves_record_key_and_semantic_value_digest(self):
        low = eki2.compile_row(current_card(relevance=eki1.RelevanceBand.LOW))
        high = eki2.compile_row(current_card(relevance=eki1.RelevanceBand.HIGH))
        self.assertEqual(low.key, high.key)
        self.assertEqual(low.value["digest"], high.value["digest"])
        self.assertNotEqual(low.value["cell"], high.value["cell"])
        self.assertNotEqual(low.placement_generation, high.placement_generation)

    def test_relocation_replaces_cell_without_research_or_record_generation(self):
        low = eki2.compile_row(current_card(relevance=eki1.RelevanceBand.LOW))
        first = eki2.compile_store((low,))
        high = eki2.compile_row(current_card(relevance=eki1.RelevanceBand.HIGH))
        second = eki2.compile_store((high,), existing_snapshot_bytes=first.snapshot_bytes)
        self.assertEqual(second.receipt.inserted_keys, ())
        self.assertEqual(second.receipt.relocated_keys, (low.key,))
        parsed = json.loads(second.snapshot_bytes)
        self.assertEqual(parsed["rows"][0]["V"]["digest"], low.value["digest"])
        self.assertEqual(parsed["rows"][0]["V"]["cell"], high.value["cell"])

    def test_same_key_semantic_drift_fails_closed(self):
        row = eki2.compile_row(current_card())
        first = eki2.compile_store((row,))
        forged = eki2.ExternalCognitionStoreRow(
            key=row.key,
            value={**row.value, "standing": row.value["standing"] + " forged"},
            semantic_id=row.semantic_id,
            record_generation=row.record_generation,
            placement_generation=row.placement_generation,
            source_generation_id=row.source_generation_id,
        )
        with self.assertRaisesRegex(eki2.StoreWriterError, "SEMANTIC_DRIFT"):
            eki2.compile_store((forged,), existing_snapshot_bytes=first.snapshot_bytes)

    def test_exact_duplicate_is_idempotent_noop(self):
        row = eki2.compile_row(current_card())
        first = eki2.compile_store((row,))
        second = eki2.compile_store((row,), existing_snapshot_bytes=first.snapshot_bytes)
        self.assertEqual(second.snapshot_bytes, first.snapshot_bytes)
        self.assertEqual(second.receipt.noop_keys, (row.key,))

    def test_discovery_without_source_generation_is_persistable_but_not_currentness_witness(self):
        row = eki2.compile_row(discovery_card())
        standing = json.loads(row.value["standing"])
        self.assertIsNone(standing["source_generation_id"])
        self.assertEqual(standing["persisted_currentness_label"], "UNKNOWN")
        self.assertTrue(row.value["reopen"]["persisted_currentness_label_is_not_witness"])
        compiled = eki2.compile_store((row,))
        self.assertFalse(compiled.receipt.persisted_currentness_is_witness)

    def test_unknown_security_is_preserved_in_standing(self):
        card = discovery_card()
        row = eki2.compile_row(card)
        standing = json.loads(row.value["standing"])
        self.assertEqual(standing["security"]["state"], "UNKNOWN")
        self.assertIsNone(standing["hydration"]["L1"]["remote_code_requested"])

    def test_persisted_current_label_never_grants_reader_or_tool_authority(self):
        compiled = eki2.compile_store((eki2.compile_row(current_card()),))
        receipt = compiled.receipt
        self.assertFalse(receipt.instruction_authority)
        self.assertFalse(receipt.write_authority_granted_to_reader)
        self.assertFalse(receipt.tool_execution_authority)
        self.assertFalse(receipt.provider_effect_authority)
        self.assertFalse(receipt.semantic_k27_authority)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)

    def test_explicit_supersession_marks_old_row_history_only_shape(self):
        first = eki2.compile_row(current_card(source_generation=generation("rev-a", "a" * 64)))
        second = eki2.compile_row(current_card(source_generation=generation("rev-b", "b" * 64)))
        compiled = eki2.compile_store(
            (first, second),
            supersession_edges=((first.key, second.key),),
        )
        parsed = json.loads(compiled.snapshot_bytes)
        rows = {row["K"]: row["V"] for row in parsed["rows"]}
        self.assertEqual(rows[first.key]["successor"], second.key)
        self.assertIsNone(rows[second.key]["successor"])

    def test_supersession_is_never_inferred(self):
        first = eki2.compile_row(current_card(source_generation=generation("rev-a", "a" * 64)))
        second = eki2.compile_row(current_card(source_generation=generation("rev-b", "b" * 64)))
        compiled = eki2.compile_store((first, second))
        rows = {row["K"]: row["V"] for row in json.loads(compiled.snapshot_bytes)["rows"]}
        self.assertIsNone(rows[first.key]["successor"])
        self.assertIsNone(rows[second.key]["successor"])

    def test_supersession_cycle_fails_closed(self):
        first = eki2.compile_row(current_card(source_generation=generation("rev-a", "a" * 64)))
        second = eki2.compile_row(current_card(source_generation=generation("rev-b", "b" * 64)))
        with self.assertRaisesRegex(eki2.StoreWriterError, "CYCLE"):
            eki2.compile_store(
                (first, second),
                supersession_edges=((first.key, second.key), (second.key, first.key)),
            )

    def test_store_snapshot_is_deterministic_independent_of_input_order(self):
        first = eki2.compile_row(current_card(source_generation=generation("rev-a", "a" * 64)))
        second = eki2.compile_row(current_card(source_generation=generation("rev-b", "b" * 64)))
        a = eki2.compile_store((first, second))
        b = eki2.compile_store((second, first))
        self.assertEqual(a.snapshot_bytes, b.snapshot_bytes)
        self.assertEqual(a.receipt.store_sha256, b.receipt.store_sha256)
        self.assertEqual(a.receipt.store_generation, b.receipt.store_generation)

    def test_provider_envelope_compiles_only_cheap_l1_by_default(self):
        card = eki2.compile_card_from_envelope(
            {
                "source_kind": "GITHUB",
                "artifact_class": "CODE",
                "canonical_id": "owner/repo",
                "canonical_uri": "https://github.com/owner/repo",
                "title": "Repo",
                "thesis": "Repository metadata.",
                "currentness": "CURRENT",
                "generation": {
                    "generation_type": "GIT_COMMIT",
                    "generation_value": "deadbeef",
                    "checked_at": "2026-08-31T16:50:00Z",
                    "exact_source_uri": "https://github.com/owner/repo/tree/deadbeef",
                },
                "rights": {"state": "UNKNOWN"},
                "security": {"state": "UNKNOWN"},
            }
        )
        self.assertEqual(card.admitted_hydration_level, 1)
        self.assertNotIn("L2", card.hydration)

    def test_store_generation_changes_on_relocation_but_record_digest_does_not(self):
        low = eki2.compile_row(current_card(relevance=eki1.RelevanceBand.LOW))
        high = eki2.compile_row(current_card(relevance=eki1.RelevanceBand.HIGH))
        first = eki2.compile_store((low,))
        second = eki2.compile_store((high,), existing_snapshot_bytes=first.snapshot_bytes)
        self.assertNotEqual(first.receipt.store_generation, second.receipt.store_generation)
        self.assertNotEqual(first.receipt.store_sha256, second.receipt.store_sha256)
        self.assertEqual(low.value["digest"], high.value["digest"])


if __name__ == "__main__":
    unittest.main()
