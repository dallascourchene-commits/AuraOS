import random
import unittest

from tools import aura_structural_archive_probe as structural
from tools.aura_archive_versioned_chunk_dag import (
    ChunkingPolicy,
    VersionedArtifact,
    VersionedArchiveError,
    content_defined_chunks,
    inspect_versioned_archive,
    k27_url_coordinate,
    pack_versioned_archive,
    require_exact_reversible_transform,
    unpack_versioned_archive,
)

POLICY = ChunkingPolicy(min_size=64, avg_size=128, max_size=256)


def art(
    artifact_id,
    body,
    generation="g1",
    *,
    l0="orientation",
    k27=(1, 2, 3),
    d13=None,
    event_at="2026-08-30T00:00:00Z",
    recorded_at="2026-08-31T00:00:00Z",
    scale="ATOMIC",
):
    return VersionedArtifact(
        artifact_id=artifact_id,
        subject_key="subject:demo",
        generation_id=generation,
        source_bytes=body,
        sector="08_RSH",
        event_at=event_at,
        recorded_at=recorded_at,
        scale=scale,
        hydration_index={"L0": l0, "L1": "purpose"},
        connectome_edges=({"relation": "DERIVED_FROM", "target": "source:demo"},),
        d13=d13,
        k27=k27,
    )


class VersionedChunkDagTests(unittest.TestCase):
    def test_exact_roundtrip(self):
        body = b'{"a":1,"b":"exact"}' * 500
        archive, stats = pack_versioned_archive([art("a", body)], policy=POLICY)
        self.assertEqual(unpack_versioned_archive(archive), {"a": body})
        self.assertEqual(stats.logical_source_bytes, len(body))

    def test_cross_generation_exact_chunk_dedup(self):
        shared = bytes(range(256)) * 20
        v1 = shared + b"generation=one" + shared
        v2 = shared + b"generation=two" + shared
        archive, stats = pack_versioned_archive(
            [art("g1", v1), art("g2", v2, "g2")], policy=POLICY
        )
        self.assertLess(stats.unique_chunk_source_bytes, stats.logical_source_bytes)
        self.assertGreater(stats.referenced_chunks, stats.unique_chunks)
        self.assertEqual(unpack_versioned_archive(archive), {"g1": v1, "g2": v2})

    def test_identical_bytes_share_chunks_but_not_generation_manifest(self):
        body = b"same" * 1000
        archive, stats = pack_versioned_archive(
            [art("g1", body, "gen1"), art("g2", body, "gen2", l0="changed")],
            policy=POLICY,
        )
        info = inspect_versioned_archive(archive)
        self.assertLessEqual(stats.unique_chunk_source_bytes, len(body))
        self.assertGreater(stats.referenced_chunks, stats.unique_chunks)
        self.assertNotEqual(
            info["artifacts"][0]["manifest_identity"],
            info["artifacts"][1]["manifest_identity"],
        )
        self.assertEqual(
            info["artifacts"][0]["source_sha256"],
            info["artifacts"][1]["source_sha256"],
        )

    def test_index_changes_do_not_change_exact_source(self):
        body = b"exact source plane" * 300
        a1, _ = pack_versioned_archive([art("a", body, l0="old", k27=(1,2,3))], policy=POLICY)
        a2, _ = pack_versioned_archive([art("a", body, l0="new", k27=(9,9,9))], policy=POLICY)
        self.assertNotEqual(a1, a2)
        self.assertEqual(unpack_versioned_archive(a1)["a"], body)
        self.assertEqual(unpack_versioned_archive(a2)["a"], body)
        self.assertFalse(inspect_versioned_archive(a1)["index_plane"]["reconstruction_authority"])

    def test_semantic_similarity_is_not_dedup_authority(self):
        one = b'{"x":1, "y":2}'
        two = b'{\n "x": 1,\n "y": 2\n}'
        archive, _ = pack_versioned_archive([art("one", one), art("two", two, "g2")], policy=POLICY)
        out = unpack_versioned_archive(archive)
        self.assertEqual(out["one"], one)
        self.assertEqual(out["two"], two)
        self.assertFalse(
            inspect_versioned_archive(archive)["index_plane"]["semantic_similarity_dedup_authority"]
        )

    def test_small_insertion_retains_most_cdc_boundaries(self):
        rng = random.Random(42)
        body = bytes(rng.randrange(256) for _ in range(12000))
        edited = body[:5000] + b"INSERTION" + body[5000:]
        import hashlib
        a = {hashlib.sha256(x).hexdigest() for x in content_defined_chunks(body, POLICY)}
        b = {hashlib.sha256(x).hexdigest() for x in content_defined_chunks(edited, POLICY)}
        self.assertGreater(len(a & b), min(len(a), len(b)) // 2)

    def test_chunk_corruption_fails_closed(self):
        archive, _ = pack_versioned_archive([art("a", b"A" * 9000)], policy=POLICY)
        damaged = bytearray(archive)
        damaged[-1] ^= 1
        with self.assertRaises(VersionedArchiveError):
            unpack_versioned_archive(bytes(damaged))

    def test_ordered_chunk_refs_preserve_source_order(self):
        body = (b"left" * 1000) + (b"right" * 1000)
        archive, _ = pack_versioned_archive([art("a", body)], policy=POLICY)
        self.assertEqual(unpack_versioned_archive(archive)["a"], body)

    def test_k27_projection_does_not_change_source_identity(self):
        body = b"K27 nonauthority" * 300
        a1, _ = pack_versioned_archive([art("a", body, k27=(0,0,0))], policy=POLICY)
        a2, _ = pack_versioned_archive([art("a", body, k27=(26,26,26))], policy=POLICY)
        i1 = inspect_versioned_archive(a1)
        i2 = inspect_versioned_archive(a2)
        self.assertEqual(i1["artifacts"][0]["source_sha256"], i2["artifacts"][0]["source_sha256"])
        self.assertFalse(i1["index_plane"]["k27_identity_authority"])

    def test_time_metadata_does_not_change_source_identity_or_mint_causality(self):
        body = b"time axis" * 400
        a1, _ = pack_versioned_archive(
            [art("a", body, event_at="2024-01-01", recorded_at="2026-01-01")], policy=POLICY)
        a2, _ = pack_versioned_archive(
            [art("a", body, event_at="2020-01-01", recorded_at="2021-01-01")], policy=POLICY)
        i1, i2 = inspect_versioned_archive(a1), inspect_versioned_archive(a2)
        self.assertEqual(i1["artifacts"][0]["source_sha256"], i2["artifacts"][0]["source_sha256"])
        self.assertFalse(i1["artifacts"][0]["temporal_adjacency_is_causal_dependency"])

    def test_d13_validation_and_nonauthority(self):
        good = (0,) * 13
        archive, _ = pack_versioned_archive([art("a", b"x" * 500, d13=good)], policy=POLICY)
        self.assertFalse(inspect_versioned_archive(archive)["index_plane"]["d13_truth_authority"])
        with self.assertRaises(VersionedArchiveError):
            pack_versioned_archive([art("b", b"y", d13=(0,) * 12)], policy=POLICY)

    def test_l4_cannot_be_smuggled_into_lossy_index_plane(self):
        bad = art("a", b"exact")
        bad = VersionedArtifact(
            **{**bad.__dict__, "hydration_index": {"L0": "x", "L4": "pretend exact"}}
        )
        with self.assertRaises(VersionedArchiveError):
            pack_versioned_archive([bad], policy=POLICY)

    def test_structural_codec_owner_is_used_for_unique_chunks(self):
        body = b"A" * 5000
        archive, stats = pack_versioned_archive([art("a", body)], policy=POLICY)
        self.assertTrue(stats.structural_modes)
        self.assertEqual(
            inspect_versioned_archive(archive)["source_plane"]["per_chunk_codec_owner"],
            structural.SCHEMA,
        )

    def test_random_already_unfriendly_data_gets_no_superiority_claim(self):
        rng = random.Random(99)
        body = bytes(rng.randrange(256) for _ in range(20000))
        archive, _ = pack_versioned_archive([art("random", body)], policy=POLICY)
        self.assertEqual(unpack_versioned_archive(archive)["random"], body)
        self.assertFalse(
            inspect_versioned_archive(archive)["claim_ceiling"]["universal_compression_superiority"]
        )

    def test_exact_reversible_transform_gate(self):
        self.assertEqual(
            require_exact_reversible_transform(lambda x: x[::-1], lambda x: x[::-1], b"abc"),
            b"cba",
        )
        with self.assertRaises(VersionedArchiveError):
            require_exact_reversible_transform(lambda x: x.lower(), lambda x: x, b"ABC")

    def test_archive_is_deterministic(self):
        inputs = [art("b", b"b" * 4000, "g2"), art("a", b"a" * 4000, "g1")]
        one, _ = pack_versioned_archive(inputs, policy=POLICY)
        two, _ = pack_versioned_archive(inputs, policy=POLICY)
        self.assertEqual(one, two)

    def test_40_rack_structural_corpus_roundtrips(self):
        racks = structural.build_40_rack_matrix()
        artifacts = [
            art(f"rack-{i:02d}", body, f"g{i:02d}", k27=(i % 27, (i*3)%27, (i*7)%27))
            for i, body in enumerate(racks)
        ]
        archive, stats = pack_versioned_archive(artifacts, policy=POLICY)
        out = unpack_versioned_archive(archive)
        self.assertEqual(len(out), 40)
        for i, body in enumerate(racks):
            self.assertEqual(out[f"rack-{i:02d}"], body)
        self.assertEqual(stats.logical_source_bytes, sum(map(len, racks)))

    def test_k27_exact_url_rule(self):
        self.assertEqual(
            k27_url_coordinate("https://arxiv.org/abs/2409.06066"),
            (13, 2, 25),
        )


if __name__ == "__main__":
    unittest.main()
