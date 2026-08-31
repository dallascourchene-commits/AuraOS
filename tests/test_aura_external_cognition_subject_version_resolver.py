from __future__ import annotations

import hashlib
import json
import unittest

from tools import aura_external_knowledge_ingress as eki1
from tools import aura_external_knowledge_store_writer as eki2
from tools.aura_external_cognition_subject_version_resolver import (
    SubjectVersionDisposition,
    resolve_subject_version,
)
from tests.test_aura_external_knowledge_store_reader_integration import _card, _generation


def _resolve(compiled: eki2.CompiledStore, semantic_id: str):
    return resolve_subject_version(
        snapshot_bytes=compiled.snapshot_bytes,
        semantic_subject_id=semantic_id,
        expected_store_sha256=compiled.receipt.store_sha256,
        expected_store_generation=compiled.receipt.store_generation,
    )


def _rewire(compiled: eki2.CompiledStore, mutate):
    body = json.loads(compiled.snapshot_bytes.decode("utf-8"))
    mutate(body)
    snapshot = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    sha = hashlib.sha256(snapshot).hexdigest()
    generation = "EKI2::STORE::" + sha[:32]
    return snapshot, sha, generation


class ExternalCognitionSubjectVersionResolverTests(unittest.TestCase):
    def test_single_version_is_candidate_but_not_currentness_witness(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))
        receipt = _resolve(compiled, row.semantic_id)
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.SELECTED_VERSION_CANDIDATE,
        )
        self.assertEqual(receipt.candidate_record_key, row.key)
        self.assertEqual(receipt.candidate_record_generation, row.record_generation)
        self.assertFalse(receipt.source_currentness_proven)
        self.assertFalse(receipt.selected_head_is_currentness_witness)
        self.assertFalse(receipt.chronology_inferred)
        self.assertFalse(receipt.k27_used_for_version_selection)
        self.assertFalse(receipt.read_authority)
        self.assertFalse(receipt.write_authority)
        self.assertFalse(receipt.effect_authority)

    def test_explicit_supersession_selects_new_version_and_preserves_old(self):
        old = eki2.compile_row(_card(generation=_generation("rev-a", "a" * 64)))
        new = eki2.compile_row(_card(generation=_generation("rev-b", "b" * 64)))
        compiled = eki2.compile_store(
            (old, new),
            supersession_edges=((old.key, new.key),),
        )
        receipt = _resolve(compiled, old.semantic_id)
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.SELECTED_VERSION_CANDIDATE,
        )
        self.assertEqual(receipt.candidate_record_key, new.key)
        self.assertEqual(receipt.historical_record_keys, (old.key,))
        self.assertEqual(receipt.head_record_keys, (new.key,))

    def test_two_generations_without_explicit_edge_are_ambiguous_not_chronological(self):
        old = eki2.compile_row(_card(generation=_generation("rev-a", "a" * 64)))
        new = eki2.compile_row(_card(generation=_generation("rev-z", "f" * 64)))
        compiled = eki2.compile_store((old, new))
        receipt = _resolve(compiled, old.semantic_id)
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.HOLD_AMBIGUOUS_HEAD,
        )
        self.assertEqual(set(receipt.head_record_keys), {old.key, new.key})
        self.assertFalse(receipt.chronology_inferred)

    def test_unknown_subject_is_typed_hold(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))
        receipt = _resolve(compiled, "f" * 64)
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.HOLD_SUBJECT_NOT_FOUND,
        )
        self.assertEqual(receipt.subject_record_count, 0)

    def test_missing_successor_target_holds(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))

        def mutate(body):
            body["rows"][0]["V"]["successor"] = (
                f"external-cognition://{row.semantic_id}/record/" + "e" * 64
            )

        snapshot, sha, generation = _rewire(compiled, mutate)
        receipt = resolve_subject_version(
            snapshot_bytes=snapshot,
            semantic_subject_id=row.semantic_id,
            expected_store_sha256=sha,
            expected_store_generation=generation,
        )
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.HOLD_SUPERSESSION_TARGET_MISSING,
        )

    def test_cross_subject_successor_holds_before_target_lookup(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))

        def mutate(body):
            body["rows"][0]["V"]["successor"] = (
                "external-cognition://" + "d" * 64 + "/record/" + "e" * 64
            )

        snapshot, sha, generation = _rewire(compiled, mutate)
        receipt = resolve_subject_version(
            snapshot_bytes=snapshot,
            semantic_subject_id=row.semantic_id,
            expected_store_sha256=sha,
            expected_store_generation=generation,
        )
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.HOLD_CROSS_SUBJECT_SUCCESSOR,
        )

    def test_cycle_holds_even_if_store_bytes_are_well_formed(self):
        first = eki2.compile_row(_card(generation=_generation("rev-a", "a" * 64)))
        second = eki2.compile_row(_card(generation=_generation("rev-b", "b" * 64)))
        compiled = eki2.compile_store((first, second))

        def mutate(body):
            by_key = {row["K"]: row for row in body["rows"]}
            by_key[first.key]["V"]["successor"] = second.key
            by_key[second.key]["V"]["successor"] = first.key

        snapshot, sha, generation = _rewire(compiled, mutate)
        receipt = resolve_subject_version(
            snapshot_bytes=snapshot,
            semantic_subject_id=first.semantic_id,
            expected_store_sha256=sha,
            expected_store_generation=generation,
        )
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.HOLD_SUPERSESSION_CYCLE,
        )

    def test_tampered_standing_is_rejected_by_semantic_value_digest(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))

        def mutate(body):
            standing = json.loads(body["rows"][0]["V"]["standing"])
            standing["title"] = "tampered"
            body["rows"][0]["V"]["standing"] = json.dumps(
                standing,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )

        snapshot, sha, generation = _rewire(compiled, mutate)
        with self.assertRaisesRegex(ValueError, "ROW_SEMANTIC_VALUE_DIGEST_MISMATCH"):
            resolve_subject_version(
                snapshot_bytes=snapshot,
                semantic_subject_id=row.semantic_id,
                expected_store_sha256=sha,
                expected_store_generation=generation,
            )

    def test_store_sha_and_generation_are_independently_bound(self):
        row = eki2.compile_row(_card())
        compiled = eki2.compile_store((row,))
        with self.assertRaisesRegex(ValueError, "STORE_SHA256_MISMATCH"):
            resolve_subject_version(
                snapshot_bytes=compiled.snapshot_bytes,
                semantic_subject_id=row.semantic_id,
                expected_store_sha256="0" * 64,
                expected_store_generation=compiled.receipt.store_generation,
            )
        with self.assertRaisesRegex(ValueError, "STORE_GENERATION_MISMATCH"):
            resolve_subject_version(
                snapshot_bytes=compiled.snapshot_bytes,
                semantic_subject_id=row.semantic_id,
                expected_store_sha256=compiled.receipt.store_sha256,
                expected_store_generation="EKI2::STORE::" + "0" * 32,
            )

    def test_k27_relocation_does_not_change_version_selection(self):
        low = eki2.compile_row(_card(relevance=eki1.RelevanceBand.LOW))
        first = eki2.compile_store((low,))
        high = eki2.compile_row(_card(relevance=eki1.RelevanceBand.HIGH))
        second = eki2.compile_store((high,), existing_snapshot_bytes=first.snapshot_bytes)
        self.assertEqual(low.key, high.key)
        self.assertNotEqual(low.placement_generation, high.placement_generation)
        receipt = _resolve(second, high.semantic_id)
        self.assertEqual(
            receipt.disposition,
            SubjectVersionDisposition.SELECTED_VERSION_CANDIDATE,
        )
        self.assertEqual(receipt.candidate_record_key, high.key)
        self.assertFalse(receipt.k27_used_for_version_selection)


if __name__ == "__main__":
    unittest.main()
