from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import unittest

from tests.test_aura_external_knowledge_coordinate_memory_candidate import current_node
from tools.aura_external_knowledge_coordinate_memory_candidate import project_external_knowledge_candidate
from tools.aura_external_cognition_resolve_adapter import SCHEMA_NAME, SCHEMA_VERSION
from tools.aura_coordinate_memory_write_admission import (
    CoordinateMemorySchemaPolicyV1,
    ResolvedWriteAdmissionEvidenceV1,
    SupersessionRelation,
    WriteAdmissionDisposition,
    WriteResolverExpectationV1,
    admit_coordinate_memory_write,
)


def candidate(*, rev: str = "abc123", content: str = "a" * 64, verifier: str = "v1"):
    result = project_external_knowledge_candidate(
        node=current_node(rev=rev, content=content, verifier=verifier)
    )
    assert result.candidate is not None
    return result.candidate


def snapshot_bytes(rows):
    return json.dumps(
        {"schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION}, "rows": list(rows)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def policy():
    return CoordinateMemorySchemaPolicyV1(
        schema_owner_ref="schema-owner:test",
        schema_owner_generation="schema-owner-generation:test:1",
        policy_generation="write-planning-policy:test:1",
    )


def resolution_bundle(
    *,
    cand,
    store_bytes,
    existing_generation=None,
    relation=SupersessionRelation.NONE,
    proposed_current=True,
    store_current=True,
    admitted=True,
    resolver_ref="resolver:test",
):
    digest = hashlib.sha256(store_bytes).hexdigest()
    expectation = WriteResolverExpectationV1(
        resolver_ref="resolver:test",
        resolver_generation="resolver-generation:test:1",
        source_currentness_ref="source-currentness:test",
        source_currentness_generation="source-currentness-generation:test:1",
        subject_key=cand.semantic_key,
        proposed_evidence_generation_key=cand.evidence_generation_key,
        candidate_id=cand.candidate_id,
        store_ref="coordinate-store:test",
        store_generation="store-generation:test:1",
        store_sha256=digest,
    )
    evidence = ResolvedWriteAdmissionEvidenceV1(
        resolver_ref=resolver_ref,
        resolver_generation="resolver-generation:test:1",
        source_currentness_ref="source-currentness:test",
        source_currentness_generation="source-currentness-generation:test:1",
        subject_key=cand.semantic_key,
        proposed_evidence_generation_key=cand.evidence_generation_key,
        candidate_id=cand.candidate_id,
        store_ref="coordinate-store:test",
        store_generation="store-generation:test:1",
        store_sha256=digest,
        existing_evidence_generation_key=existing_generation,
        supersession_relation=relation,
        proposed_source_current=proposed_current,
        observed_store_current=store_current,
        resolved_admitted=admitted,
        evidence_ref="resolved-write-evidence:test:1",
    )
    return expectation, evidence


def admit(cand, store_bytes, *, expectation, evidence, schema_policy=None, expected_sha=None):
    return admit_coordinate_memory_write(
        candidate=cand,
        snapshot_bytes=store_bytes,
        store_ref="coordinate-store:test",
        store_generation="store-generation:test:1",
        expected_store_sha256=expected_sha or hashlib.sha256(store_bytes).hexdigest(),
        schema_policy=policy() if schema_policy is None else schema_policy,
        resolver_expectation=expectation,
        resolution_evidence=evidence,
    )


class CoordinateMemoryWriteAdmissionTests(unittest.TestCase):
    def test_absent_subject_earns_insert_plan_without_mutation(self):
        cand = candidate()
        store = snapshot_bytes([])
        before = bytes(store)
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=store)
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.INSERT_NEW_PLAN)
        self.assertEqual(receipt.proposed_row, cand.proposed_row)
        self.assertEqual(store, before)
        self.assertTrue(receipt.writer_execution_required)
        self.assertTrue(receipt.canonical_writer_missing)
        self.assertFalse(receipt.store_mutated)
        self.assertFalse(receipt.write_authority)
        self.assertFalse(receipt.effect_authority)
        self.assertFalse(receipt.semantic_truth_granted)

    def test_schema_policy_is_mandatory_and_cannot_authorize_mutation(self):
        cand = candidate()
        store = snapshot_bytes([])
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=store)
        receipt = admit_coordinate_memory_write(
            candidate=cand,
            snapshot_bytes=store,
            store_ref="coordinate-store:test",
            store_generation="store-generation:test:1",
            expected_store_sha256=hashlib.sha256(store).hexdigest(),
            schema_policy=None,
            resolver_expectation=expectation,
            resolution_evidence=evidence,
        )
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.HOLD_SCHEMA_POLICY)
        with self.assertRaisesRegex(ValueError, "STORE_MUTATION_AUTHORIZED_MUST_REMAIN_FALSE"):
            replace(policy(), store_mutation_authorized=True).validate()
        with self.assertRaisesRegex(ValueError, "V1_SUPERSESSION_REPRESENTATION_NOT_AVAILABLE"):
            replace(policy(), supersession_representation_sanctioned=True).validate()

    def test_raw_presence_without_independent_resolution_cannot_admit(self):
        cand = candidate()
        store = snapshot_bytes([])
        receipt = admit_coordinate_memory_write(
            candidate=cand,
            snapshot_bytes=store,
            store_ref="coordinate-store:test",
            store_generation="store-generation:test:1",
            expected_store_sha256=hashlib.sha256(store).hexdigest(),
            schema_policy=policy(),
            resolver_expectation=None,
            resolution_evidence=None,
        )
        self.assertEqual(
            receipt.disposition,
            WriteAdmissionDisposition.HOLD_CURRENTNESS_EVIDENCE_REQUIRED,
        )

    def test_resolver_identity_mismatch_fails_closed(self):
        cand = candidate()
        store = snapshot_bytes([])
        expectation, evidence = resolution_bundle(
            cand=cand, store_bytes=store, resolver_ref="resolver:substitute"
        )
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(
            receipt.disposition,
            WriteAdmissionDisposition.HOLD_CURRENTNESS_EVIDENCE_MISMATCH,
        )

    def test_stale_source_or_store_reopens(self):
        cand = candidate()
        store = snapshot_bytes([])
        expectation, evidence = resolution_bundle(
            cand=cand, store_bytes=store, proposed_current=False
        )
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.HOLD_CURRENTNESS_REOPEN)
        expectation, evidence = resolution_bundle(
            cand=cand, store_bytes=store, store_current=False
        )
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.HOLD_CURRENTNESS_REOPEN)

    def test_store_digest_and_schema_are_exact(self):
        cand = candidate()
        store = snapshot_bytes([])
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=store)
        receipt = admit(
            cand,
            store,
            expectation=expectation,
            evidence=evidence,
            expected_sha="0" * 64,
        )
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.HOLD_STORE_INTEGRITY)

        wrong_schema = json.dumps(
            {"schema": {"name": SCHEMA_NAME, "version": "2.0.0"}, "rows": []},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=wrong_schema)
        receipt = admit(cand, wrong_schema, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.HOLD_STORE_STALE)

    def test_identical_generation_and_row_is_noop_not_rewrite(self):
        cand = candidate()
        store = snapshot_bytes([cand.proposed_row])
        expectation, evidence = resolution_bundle(
            cand=cand,
            store_bytes=store,
            existing_generation=cand.evidence_generation_key,
            relation=SupersessionRelation.IDENTICAL_GENERATION,
        )
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.NOOP_IDENTICAL_PLAN)
        self.assertIsNone(receipt.proposed_row)
        self.assertFalse(receipt.store_mutated)

    def test_same_generation_but_different_representation_is_identity_conflict(self):
        cand = candidate()
        changed = json.loads(json.dumps(cand.proposed_row))
        changed["V"]["standing"] += " tampered"
        store = snapshot_bytes([changed])
        expectation, evidence = resolution_bundle(
            cand=cand,
            store_bytes=store,
            existing_generation=cand.evidence_generation_key,
            relation=SupersessionRelation.IDENTICAL_GENERATION,
        )
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.HOLD_ROW_IDENTITY_CONFLICT)

    def test_different_generation_requires_explicit_supersession_resolution(self):
        old = candidate(rev="abc123", content="a" * 64, verifier="v1")
        new = candidate(rev="def456", content="c" * 64, verifier="v2")
        self.assertEqual(old.semantic_key, new.semantic_key)
        self.assertNotEqual(old.evidence_generation_key, new.evidence_generation_key)
        store = snapshot_bytes([old.proposed_row])
        expectation, evidence = resolution_bundle(
            cand=new,
            store_bytes=store,
            existing_generation=old.evidence_generation_key,
            relation=SupersessionRelation.NONE,
        )
        receipt = admit(new, store, expectation=expectation, evidence=evidence)
        self.assertEqual(
            receipt.disposition,
            WriteAdmissionDisposition.HOLD_SUPERSESSION_RELATION_REQUIRED,
        )

    def test_even_resolved_supersession_holds_for_v1_representation(self):
        old = candidate(rev="abc123", content="a" * 64, verifier="v1")
        new = candidate(rev="def456", content="c" * 64, verifier="v2")
        store = snapshot_bytes([old.proposed_row])
        expectation, evidence = resolution_bundle(
            cand=new,
            store_bytes=store,
            existing_generation=old.evidence_generation_key,
            relation=SupersessionRelation.PROPOSED_SUPERSEDES_EXISTING,
        )
        receipt = admit(new, store, expectation=expectation, evidence=evidence)
        self.assertEqual(
            receipt.disposition,
            WriteAdmissionDisposition.HOLD_SUPERSESSION_REPRESENTATION_REQUIRED,
        )
        self.assertEqual(receipt.existing_evidence_generation_key, old.evidence_generation_key)
        self.assertFalse(receipt.store_mutated)
        self.assertTrue(receipt.canonical_writer_missing)

    def test_duplicate_stable_key_is_ambiguous_not_last_write_wins(self):
        cand = candidate()
        store = snapshot_bytes([cand.proposed_row, cand.proposed_row])
        expectation, evidence = resolution_bundle(
            cand=cand,
            store_bytes=store,
            existing_generation=cand.evidence_generation_key,
            relation=SupersessionRelation.IDENTICAL_GENERATION,
        )
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(
            receipt.disposition,
            WriteAdmissionDisposition.HOLD_EXISTING_KEY_AMBIGUOUS,
        )

    def test_existing_row_without_generation_identity_cannot_be_replaced(self):
        cand = candidate()
        row = json.loads(json.dumps(cand.proposed_row))
        del row["V"]["cell"]["external_evidence_generation_key"]
        store = snapshot_bytes([row])
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=store)
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(
            receipt.disposition,
            WriteAdmissionDisposition.HOLD_EXISTING_GENERATION_UNRESOLVED,
        )

    def test_candidate_authority_widening_fails_before_store_admission(self):
        cand = replace(candidate(), write_authority=True)
        store = snapshot_bytes([])
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=store)
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.HOLD_CANDIDATE_CEILING)

    def test_k27_collision_does_not_block_distinct_semantic_key_insert(self):
        cand = candidate()
        foreign = json.loads(json.dumps(cand.proposed_row))
        foreign["K"] = "f" * 64
        foreign["V"]["cell"]["external_subject_key"] = "f" * 64
        # Retain the exact same k27_xyz deliberately; semantic K remains distinct.
        store = snapshot_bytes([foreign])
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=store)
        receipt = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(receipt.disposition, WriteAdmissionDisposition.INSERT_NEW_PLAN)

    def test_receipt_is_deterministic_and_nonauthorizing(self):
        cand = candidate()
        store = snapshot_bytes([])
        expectation, evidence = resolution_bundle(cand=cand, store_bytes=store)
        a = admit(cand, store, expectation=expectation, evidence=evidence)
        b = admit(cand, store, expectation=expectation, evidence=evidence)
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertFalse(a.write_authority)
        self.assertFalse(a.effect_authority)
        self.assertFalse(a.semantic_k27_authority)
        self.assertFalse(a.native_private_transformer_kv_accessed)


if __name__ == "__main__":
    unittest.main()
