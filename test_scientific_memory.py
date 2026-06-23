"""Tests for Aura's structured scientific-memory path."""

import asyncio
from datetime import datetime

import numpy as np

from arxiv_forager import EnhancedArxivForager, ForagerConfig
from aura_scientific_memory import (
    DIMENSIONS,
    ScientificMemoryIndex,
    ScientificPaperEncoder,
    detect_contradictions,
    index_from_rows,
    pack_vector,
    unpack_vector,
)
from vsa_resonator import VSAResonator


def _record(encoder, record_id, title, abstract):
    return encoder.encode_document(record_id, title, abstract)


def test_document_and_query_share_retrieval_space():
    encoder = ScientificPaperEncoder()
    index = ScientificMemoryIndex(encoder)
    index.add(
        _record(
            encoder,
            "mesh",
            "Capability-aware routing",
            "We route tasks to relevant specialists according to declared "
            "hardware capabilities, improving allocation on a distributed mesh.",
        )
    )
    index.add(
        _record(
            encoder,
            "quantum",
            "Bell-state key distribution",
            "Photon entanglement establishes secure quantum keys.",
        )
    )

    hits = index.search("capability aware specialist routing", top_k=2)

    assert hits[0].record_id == "mesh"
    assert "quantum" not in {hit.record_id for hit in hits}


def test_structural_analogy_retrieves_two_surface_forms():
    encoder = ScientificPaperEncoder()
    index = ScientificMemoryIndex(encoder)
    index.add(
        _record(
            encoder,
            "mesh",
            "Capability-aware mesh dispatch",
            "The router selects relevant specialists according to declared "
            "hardware capabilities for efficient allocation.",
        )
    )
    index.add(
        _record(
            encoder,
            "moe",
            "Sparse mixture of experts",
            "Conditional computation activates a small subset of relevant "
            "experts and leaves inactive experts idle.",
        )
    )
    index.add(
        _record(
            encoder,
            "control",
            "Quantum photon transport",
            "Bell-state entanglement transports quantum keys.",
        )
    )

    query = (
        "[MECHANISM:conditional_selection]"
        "[RELATION:select_by_capability]"
        "[EFFECT:efficient_allocation]"
    )
    identifiers = [hit.record_id for hit in index.search(query, top_k=3)]

    assert set(identifiers[:2]) == {"mesh", "moe"}
    assert "control" not in identifiers


def test_bit_packed_vector_is_1250_bytes_and_lossless():
    encoder = ScientificPaperEncoder()
    record = _record(
        encoder,
        "vsa",
        "Vector symbolic memory",
        "A benchmark improves retrieval on edge devices.",
    )

    packed = pack_vector(record.vector)
    restored = unpack_vector(packed)

    assert len(packed) == 1_250
    assert np.array_equal(restored, record.vector)


def test_hierarchy_and_lsh_reduce_exact_candidate_set():
    encoder = ScientificPaperEncoder()
    index = ScientificMemoryIndex(encoder)
    domains = ("physics", "biology", "software", "clinical")
    mechanisms = ("routing", "quantization", "associative memory", "simulation")
    for number in range(400):
        domain = domains[number % len(domains)]
        mechanism = mechanisms[number % len(mechanisms)]
        index.add(
            _record(
                encoder,
                f"paper-{number}",
                f"{domain} {mechanism} study {number}",
                f"An empirical benchmark of {mechanism} for {domain}.",
            )
        )

    hits = index.search(
        "[DOMAIN:physics][MECHANISM:routing] empirical benchmark",
        top_k=5,
    )

    assert len(hits) == 5
    assert index.last_candidates_considered <= 40
    assert all("physics" in hit.record.title for hit in hits)
    assert index.domain_bundle("physics").shape == (DIMENSIONS,)
    assert index.mechanism_bundle("physics", "routing").shape == (DIMENSIONS,)


def test_jsonl_persistence_preserves_rankings(tmp_path):
    encoder = ScientificPaperEncoder()
    index = ScientificMemoryIndex(encoder)
    index.add(
        _record(
            encoder,
            "edge",
            "Edge VSA benchmark",
            "Hyperdimensional computing improves accuracy on embedded devices.",
        )
    )
    index.add(
        _record(
            encoder,
            "biology",
            "Coral cell survey",
            "A biological review of coral cells.",
        )
    )
    path = tmp_path / "memory.jsonl"
    index.save_jsonl(path)

    restored = ScientificMemoryIndex.load_jsonl(path)

    assert restored.search("hyperdimensional edge accuracy", top_k=1)[0].record_id == "edge"
    assert path.stat().st_size < 10_000


def test_legacy_rows_are_migrated_from_text():
    legacy_complex_blob = np.ones(DIMENSIONS, dtype=np.complex64).tobytes()
    rows = [
        (
            "ARXIV_VSA",
            "TITLE: Edge HDC | ABSTRACT: Hyperdimensional computing improves "
            "accuracy on embedded devices.",
            legacy_complex_blob,
        ),
        ("ARXIV_CRAWLER_STATE", "{}", None),
    ]

    index = index_from_rows(rows)

    assert set(index.records) == {"ARXIV_VSA"}
    assert index.search("hyperdimensional edge accuracy", top_k=1)[0].record_id == "ARXIV_VSA"


def test_opposed_results_are_reported_as_contradictions():
    encoder = ScientificPaperEncoder()
    positive = _record(
        encoder,
        "positive",
        "VSA improves edge accuracy",
        "An empirical benchmark finds vector symbolic computing improves "
        "accuracy on edge devices.",
    )
    negative = _record(
        encoder,
        "negative",
        "VSA harms edge accuracy",
        "An empirical benchmark finds vector symbolic computing degrades "
        "accuracy on edge devices.",
    )
    unrelated = _record(
        encoder,
        "unrelated",
        "Coral growth",
        "Ocean warming harms coral cell growth.",
    )

    contradictions = detect_contradictions([positive, negative, unrelated])

    assert len(contradictions) == 1
    assert {contradictions[0].left_id, contradictions[0].right_id} == {
        "positive",
        "negative",
    }


def test_short_opposed_claims_share_topic_after_polarity_unbinding():
    encoder = ScientificPaperEncoder()
    improves = _record(
        encoder,
        "improves",
        "Quantization improves accuracy",
        "Quantization improves accuracy.",
    )
    harms = _record(
        encoder,
        "harms",
        "Quantization harms accuracy",
        "Quantization harms accuracy.",
    )

    contradictions = detect_contradictions([improves, harms])

    assert len(contradictions) == 1


def test_negated_improvement_is_encoded_as_negative():
    encoder = ScientificPaperEncoder()

    record = _record(
        encoder,
        "negative",
        "Quantization does not improve accuracy",
        "The benchmark found no improvement in accuracy.",
    )

    assert record.slots.get("POLARITY") == ("negative",)


def test_enhanced_forager_persists_and_reloads_searchable_vectors(tmp_path):
    config = ForagerConfig(
        query="vsa",
        max_total=1,
        storage_dir=str(tmp_path),
    )
    raw = {
        "paper_id": "2401.00001",
        "title": "Edge vector symbolic memory",
        "authors": ["A. Researcher"],
        "abstract": "Hyperdimensional computing improves retrieval on edge devices.",
        "published": datetime(2024, 1, 1),
        "categories": ["cs.AI"],
    }

    first = EnhancedArxivForager()
    asyncio.run(first._process_paper_dict(raw, config))
    second = EnhancedArxivForager()
    second._storage_dir = tmp_path
    hits = asyncio.run(second.search_similar("hyperdimensional edge retrieval", top_k=1))

    assert hits[0].paper_id == raw["paper_id"]
    assert len(pack_vector(hits[0].vector)) == 1_250


def test_resonator_exactly_recovers_large_bipolar_codebooks():
    rng = np.random.default_rng(42)
    book_a = [
        rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
        for _ in range(500)
    ]
    book_b = [
        rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
        for _ in range(500)
    ]
    resonator = VSAResonator(dim=DIMENSIONS)
    composite = resonator.bind(book_a[137], book_b[421])

    assert resonator.resonate(composite, book_a, book_b) == (137, 421)


def test_sampled_similarity_does_not_overflow_int8():
    resonator = VSAResonator(dim=DIMENSIONS)
    vector = np.ones(DIMENSIONS, dtype=np.int8)

    similarity = resonator.sampled_similarity(1.0, vector, 0.0, 1.0, vector, 0.0)

    assert similarity == 1.0
