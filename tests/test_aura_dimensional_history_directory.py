from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import unittest

from tools.aura_external_knowledge_store_writer import ExternalCognitionStoreRow
from tools.aura_dimensional_history_directory import (
    BitemporalStamp,
    CrossDomainEdge,
    DimensionalHistoryDirectory,
    DirectoryError,
    ExactArchiveHandle,
    QueryDisposition,
    ScaleTier,
    SubjectRecordBinding,
    entry_from_versioned_row,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def row(version: str, *, hydration_level: int = 4, current_label: str = "CURRENT") -> ExternalCognitionStoreRow:
    rg = h("record:" + version)
    pg = h("placement:" + version)
    hydration = {f"L{i}": {"version": version, "level": i} for i in range(hydration_level + 1)}
    standing = json.dumps(
        {
            "record_generation": rg,
            "admitted_hydration_level": hydration_level,
            "hydration": hydration,
            "persisted_currentness_label": current_label,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return ExternalCognitionStoreRow(
        key=f"external-cognition://semantic-A/record/{rg}",
        value={
            "cell": {
                "placement_schema": "test",
                "placement_generation": pg,
                "operational_13d": {"trits": [0] * 13},
                "k27_locality": {"xyz": [4, 5, 6]},
                "refresh_phase": {"slot": 3},
                "semantic_identity": False,
                "source_currentness_witness": False,
                "authority": False,
            },
            "digest": h("value:" + version),
            "standing": standing,
            "reopen": {
                "exact_reopen_uri": f"https://example.test/{version}",
                "content_sha256": h("content:" + version),
                "persisted_currentness_label_is_not_witness": True,
                "source_currentness_must_be_resolved_externally": True,
            },
            "successor": None,
        },
        semantic_id=h("semantic-A"),
        record_generation=rg,
        placement_generation=pg,
        source_generation_id=h("source:" + version),
    )


def binding(r: ExternalCognitionStoreRow, version: str, *, subject: str = "subject-A") -> SubjectRecordBinding:
    return SubjectRecordBinding(
        stable_subject_key=h(subject),
        evidence_generation_key=h("evidence:" + version),
        candidate_id=h("candidate:" + version),
        version_record_key=r.key,
        record_generation=r.record_generation,
        binding_ref="resolver://subject-record-binding",
        binding_generation="binding-gen-1",
    )


def entry(
    version: str,
    event_at: str,
    recorded_at: str,
    *,
    subject: str = "subject-A",
    supersedes: str | None = None,
    hydration_level: int = 4,
    scale: ScaleTier = ScaleTier.ARTIFACT,
    edges=(),
    archive=None,
):
    r = row(version, hydration_level=hydration_level)
    return entry_from_versioned_row(
        row=r,
        binding=binding(r, version, subject=subject),
        temporal=BitemporalStamp(event_at=event_at, recorded_at=recorded_at),
        sector="08_RSH",
        scale=scale,
        cross_domain_edges=edges,
        supersedes_record_key=supersedes,
        archive=archive,
    )


class DimensionalHistoryDirectoryTests(unittest.TestCase):
    def test_two_clocks_reconstruct_what_was_available_without_rewriting_history(self):
        old = entry("v1", "2026-08-01T00:00:00Z", "2026-08-02T00:00:00Z")
        new = entry(
            "v2",
            "2026-08-10T00:00:00Z",
            "2026-08-15T00:00:00Z",
            supersedes=old.version_record_key,
        )
        directory = DimensionalHistoryDirectory((old, new))

        before_ingest = directory.query(
            stable_subject_key=old.stable_subject_key,
            event_cut="2026-08-12T00:00:00Z",
            recorded_cut="2026-08-12T00:00:00Z",
            requested_hydration_level=0,
        )
        self.assertEqual(QueryDisposition.FOUND_HISTORY_CANDIDATE, before_ingest.disposition)
        self.assertEqual(old.version_record_key, before_ingest.selected_record_key)

        after_ingest = directory.query(
            stable_subject_key=old.stable_subject_key,
            event_cut="2026-08-12T00:00:00Z",
            recorded_cut="2026-08-20T00:00:00Z",
            requested_hydration_level=0,
        )
        self.assertEqual(new.version_record_key, after_ingest.selected_record_key)

        before_event = directory.query(
            stable_subject_key=old.stable_subject_key,
            event_cut="2026-08-05T00:00:00Z",
            recorded_cut="2026-08-20T00:00:00Z",
            requested_hydration_level=0,
        )
        self.assertEqual(old.version_record_key, before_event.selected_record_key)

    def test_time_order_without_explicit_supersession_does_not_choose_a_winner(self):
        a = entry("parallel-a", "2026-08-01T00:00:00Z", "2026-08-02T00:00:00Z")
        b = entry("parallel-b", "2026-08-03T00:00:00Z", "2026-08-04T00:00:00Z")
        result = DimensionalHistoryDirectory((a, b)).query(
            stable_subject_key=a.stable_subject_key,
            event_cut="2026-08-10T00:00:00Z",
            recorded_cut="2026-08-10T00:00:00Z",
            requested_hydration_level=0,
        )
        self.assertEqual(QueryDisposition.HOLD_AMBIGUOUS_PARALLEL_HISTORY, result.disposition)
        self.assertIsNone(result.selected_record_key)

    def test_hydration_z_axis_returns_only_requested_cone(self):
        e = entry("hydrate", "2026-08-01T00:00:00Z", "2026-08-01T01:00:00Z")
        directory = DimensionalHistoryDirectory((e,))
        l1 = directory.query(
            stable_subject_key=e.stable_subject_key,
            event_cut="2026-08-02T00:00:00Z",
            recorded_cut="2026-08-02T00:00:00Z",
            requested_hydration_level=1,
        )
        self.assertEqual(("L0", "L1"), tuple(l1.hydration_payload))
        self.assertIsNone(l1.exact_reopen)
        self.assertIsNone(l1.archive)

    def test_l4_may_expose_archive_handle_without_truth_or_kv_promotion(self):
        archive = ExactArchiveHandle(
            archive_ref="archive://object-v1",
            codec_generation="aura-archive-probe-v1",
            original_sha256=h("content:v1"),
        )
        e = entry(
            "v1",
            "2026-08-01T00:00:00Z",
            "2026-08-01T01:00:00Z",
            archive=archive,
        )
        result = DimensionalHistoryDirectory((e,)).query(
            stable_subject_key=e.stable_subject_key,
            event_cut="2026-08-02T00:00:00Z",
            recorded_cut="2026-08-02T00:00:00Z",
            requested_hydration_level=4,
        )
        self.assertEqual(4, result.returned_hydration_level)
        self.assertEqual("archive://object-v1", result.archive.archive_ref)
        self.assertTrue(result.source_currentness_revalidation_required)
        self.assertFalse(result.semantic_truth)
        self.assertFalse(result.native_private_transformer_kv_accessed)
        self.assertFalse(result.effect_authority)

    def test_cross_domain_x_edges_are_links_not_authority_bleed(self):
        edge = CrossDomainEdge(
            relation="GROUNDED_IN",
            target_subject_key=h("research-paper"),
            edge_ref="edge://1",
            edge_generation="edge-gen-1",
        )
        e = entry(
            "v1",
            "2026-08-01T00:00:00Z",
            "2026-08-01T01:00:00Z",
            edges=(edge,),
        )
        result = DimensionalHistoryDirectory((e,)).query(
            stable_subject_key=e.stable_subject_key,
            event_cut="2026-08-02T00:00:00Z",
            recorded_cut="2026-08-02T00:00:00Z",
            requested_hydration_level=2,
        )
        self.assertEqual("GROUNDED_IN", result.cross_domain_edges[0].relation)
        self.assertFalse(result.cross_domain_edges[0].authority)
        self.assertFalse(result.semantic_truth)

    def test_same_k27_placement_cannot_merge_distinct_stable_subjects(self):
        a = entry("a", "2026-08-01T00:00:00Z", "2026-08-01T01:00:00Z", subject="A")
        b = entry("b", "2026-08-01T00:00:00Z", "2026-08-01T01:00:00Z", subject="B")
        self.assertEqual(a.placement["k27_locality"], b.placement["k27_locality"])
        self.assertNotEqual(a.stable_subject_key, b.stable_subject_key)
        directory = DimensionalHistoryDirectory((a, b))
        ra = directory.query(
            stable_subject_key=a.stable_subject_key,
            event_cut="2026-08-02T00:00:00Z",
            recorded_cut="2026-08-02T00:00:00Z",
        )
        rb = directory.query(
            stable_subject_key=b.stable_subject_key,
            event_cut="2026-08-02T00:00:00Z",
            recorded_cut="2026-08-02T00:00:00Z",
        )
        self.assertNotEqual(ra.selected_record_key, rb.selected_record_key)
        self.assertFalse(ra.placement_is_semantic_identity)

    def test_subject_record_relation_cannot_be_inferred_from_time_similarity_or_k27(self):
        r = row("v1")
        b = binding(r, "v1")
        for field in ("inferred_from_similarity", "inferred_from_k27", "inferred_from_time"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(DirectoryError, "BINDING_MUST_BE_EXPLICIT"):
                    replace(b, **{field: True}).validate()

    def test_binding_record_identity_cross_cast_rejects(self):
        r = row("v1")
        b = binding(r, "v1")
        with self.assertRaisesRegex(DirectoryError, "BINDING_RECORD_KEY_MISMATCH"):
            entry_from_versioned_row(
                row=r,
                binding=replace(b, version_record_key="external-cognition://wrong/record/key"),
                temporal=BitemporalStamp("2026-08-01T00:00:00Z", "2026-08-01T01:00:00Z"),
                sector="00_MEM",
                scale=ScaleTier.ATOMIC,
            )

    def test_persisted_current_label_never_becomes_timeline_truth(self):
        e = entry("v1", "2026-08-01T00:00:00Z", "2026-08-01T01:00:00Z")
        self.assertEqual("CURRENT", e.persisted_currentness_label)
        self.assertFalse(e.currentness_witness)
        result = DimensionalHistoryDirectory((e,)).query(
            stable_subject_key=e.stable_subject_key,
            event_cut="2026-08-02T00:00:00Z",
            recorded_cut="2026-08-02T00:00:00Z",
        )
        self.assertTrue(result.source_currentness_revalidation_required)
        self.assertFalse(result.timeline_is_source_truth)

    def test_scale_is_independent_metadata_not_record_identity(self):
        atomic = entry(
            "v1",
            "2026-08-01T00:00:00Z",
            "2026-08-01T01:00:00Z",
            scale=ScaleTier.ATOMIC,
        )
        world = replace(atomic, scale=ScaleTier.WORLD)
        world.validate()
        self.assertEqual(atomic.version_record_key, world.version_record_key)
        self.assertEqual(atomic.stable_subject_key, world.stable_subject_key)
        self.assertNotEqual(atomic.entry_digest, world.entry_digest)

    def test_supersession_cannot_cross_stable_subject(self):
        a = entry("a", "2026-08-01T00:00:00Z", "2026-08-01T01:00:00Z", subject="A")
        b = entry(
            "b",
            "2026-08-02T00:00:00Z",
            "2026-08-02T01:00:00Z",
            subject="B",
            supersedes=a.version_record_key,
        )
        with self.assertRaisesRegex(DirectoryError, "CANNOT_CROSS_STABLE_SUBJECT"):
            DimensionalHistoryDirectory((a, b))


if __name__ == "__main__":
    unittest.main()
