"""Tests for Aura's structured scientific-memory path."""

import asyncio
import base64
from datetime import datetime
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import urllib.request

import numpy as np
import pytest

from arxiv_forager import (
    ArXivForager,
    ArxivPaper,
    EnhancedArxivForager,
    ForagerConfig,
)
from aura_scientific_memory import (
    DIMENSIONS,
    ScientificMemoryIndex,
    ScientificPaperEncoder,
    ScientificSlots,
    detect_contradictions,
    index_from_rows,
    pack_vector,
    record_from_content,
    slot_similarity,
    split_title_abstract,
    unpack_vector,
    vector_similarity,
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


# ---------------------------------------------------------------------------
# ScientificSlots tests
# ---------------------------------------------------------------------------

def test_scientific_slots_get_returns_empty_tuple_for_unknown_slot():
    slots = ScientificSlots({"DOMAIN": ("physics",)})
    assert slots.get("MECHANISM") == ()
    assert slots.get("DOMAIN") == ("physics",)


def test_scientific_slots_without_removes_specified_slots():
    slots = ScientificSlots({
        "DOMAIN": ("physics",),
        "MECHANISM": ("routing",),
        "POLARITY": ("positive",),
        "YEAR": ("2023",),
    })
    stripped = slots.without("POLARITY", "YEAR")
    assert stripped.get("POLARITY") == ()
    assert stripped.get("YEAR") == ()
    assert stripped.get("DOMAIN") == ("physics",)
    assert stripped.get("MECHANISM") == ("routing",)


def test_scientific_slots_jsonable_round_trip():
    original = ScientificSlots({
        "DOMAIN": ("computer_science",),
        "MECHANISM": ("routing", "quantization"),
        "YEAR": ("2024",),
    })
    jsonable = original.to_jsonable()
    assert isinstance(jsonable, dict)
    assert jsonable["DOMAIN"] == ["computer_science"]
    assert jsonable["MECHANISM"] == ["routing", "quantization"]

    restored = ScientificSlots.from_jsonable(jsonable)
    assert restored.get("DOMAIN") == ("computer_science",)
    assert restored.get("MECHANISM") == ("routing", "quantization")
    assert restored.get("YEAR") == ("2024",)


def test_scientific_slots_from_jsonable_ignores_empty_lists():
    restored = ScientificSlots.from_jsonable({"DOMAIN": ["physics"], "MECHANISM": []})
    assert restored.get("MECHANISM") == ()
    assert restored.get("DOMAIN") == ("physics",)


# ---------------------------------------------------------------------------
# ScientificRecord tests
# ---------------------------------------------------------------------------

def test_scientific_record_vector_array_with_ndarray():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("r1", "Test title", "Test abstract.")
    array = record.vector_array()
    assert array.dtype == np.int8
    assert array.shape == (DIMENSIONS,)
    assert set(np.unique(array)).issubset({-1, 1})


def test_scientific_record_vector_array_with_bytes():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("r1", "Test title", "Test abstract.")
    packed = pack_vector(record.vector)
    # Replace the vector with packed bytes to simulate post-add state.
    record.vector = packed
    restored = record.vector_array()
    assert restored.dtype == np.int8
    assert restored.shape == (DIMENSIONS,)
    assert set(np.unique(restored)).issubset({-1, 1})


# ---------------------------------------------------------------------------
# vector_similarity tests
# ---------------------------------------------------------------------------

def test_vector_similarity_identical_vectors_returns_one():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("r1", "Physics routing", "Quantum route.")
    vec = record.vector_array()
    assert abs(vector_similarity(vec, vec) - 1.0) < 1e-5


def test_vector_similarity_accepts_bytes_arguments():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("r1", "Edge VSA", "Hyperdimensional edge.")
    packed = pack_vector(record.vector)
    assert abs(vector_similarity(packed, packed) - 1.0) < 1e-5


def test_vector_similarity_zero_vector_returns_zero():
    zero = np.zeros(DIMENSIONS, dtype=np.float32)
    normal = np.ones(DIMENSIONS, dtype=np.int8)
    assert vector_similarity(zero, normal) == 0.0
    assert vector_similarity(zero, zero) == 0.0


def test_vector_similarity_opposite_vectors_is_negative():
    rng = np.random.default_rng(0)
    v = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    assert vector_similarity(v, -v) < 0


# ---------------------------------------------------------------------------
# slot_similarity tests
# ---------------------------------------------------------------------------

def test_slot_similarity_identical_slots_returns_one():
    slots = ScientificSlots({
        "MECHANISM": ("routing",),
        "DOMAIN": ("physics",),
    })
    assert abs(slot_similarity(slots, slots) - 1.0) < 1e-6


def test_slot_similarity_disjoint_slots_returns_zero():
    query = ScientificSlots({"MECHANISM": ("routing",)})
    candidate = ScientificSlots({"DOMAIN": ("biology",)})
    assert slot_similarity(query, candidate) == 0.0


def test_slot_similarity_partial_overlap():
    query = ScientificSlots({"MECHANISM": ("routing", "quantization")})
    candidate = ScientificSlots({"MECHANISM": ("routing", "compression")})
    score = slot_similarity(query, candidate)
    assert 0.0 < score < 1.0


def test_slot_similarity_empty_query_returns_zero():
    query = ScientificSlots({})
    candidate = ScientificSlots({"DOMAIN": ("physics",)})
    assert slot_similarity(query, candidate) == 0.0


# ---------------------------------------------------------------------------
# split_title_abstract tests
# ---------------------------------------------------------------------------

def test_split_title_abstract_with_title_abstract_markers():
    content = "TITLE: My Paper Title | ABSTRACT: This is the abstract text."
    title, abstract = split_title_abstract(content)
    assert title == "My Paper Title"
    assert abstract == "This is the abstract text."


def test_split_title_abstract_with_published_marker():
    content = "TITLE: Paper | ABSTRACT: Abstract text. | PUBLISHED: 2024-01-01"
    title, abstract = split_title_abstract(content)
    assert title == "Paper"
    assert abstract == "Abstract text."


def test_split_title_abstract_with_pipe_only():
    content = "Short title | short abstract"
    title, abstract = split_title_abstract(content)
    assert title == "Short title"
    assert abstract == "short abstract"


def test_split_title_abstract_plain_text():
    content = "A plain text without any marker whatsoever"
    title, abstract = split_title_abstract(content)
    assert title == content[:160]
    assert abstract == content


# ---------------------------------------------------------------------------
# record_from_content tests
# ---------------------------------------------------------------------------

def test_record_from_content_without_blob():
    record = record_from_content("ARXIV_TEST", "TITLE: VSA | ABSTRACT: Edge computing.")
    assert record.record_id == "ARXIV_TEST"
    assert record.title == "VSA"
    assert record.abstract == "Edge computing."
    assert record.vector is not None


def test_record_from_content_with_valid_packed_blob():
    encoder = ScientificPaperEncoder()
    original = encoder.encode_document("r1", "Physics", "Quantum routing.")
    packed = pack_vector(original.vector)
    record = record_from_content(
        "r1",
        "TITLE: Physics | ABSTRACT: Quantum routing.",
        blob=packed,
    )
    # When a valid packed blob is provided, its vector is used directly.
    assert np.array_equal(record.vector_array(), original.vector_array())


def test_record_from_content_with_wrong_size_blob_is_ignored():
    wrong_blob = b"\x00" * 100  # not 1250 bytes
    record = record_from_content(
        "r1",
        "TITLE: Physics | ABSTRACT: Quantum routing.",
        blob=wrong_blob,
    )
    # Falls back to text-derived vector; should still produce a valid record.
    assert record.vector is not None
    assert len(pack_vector(record.vector)) == 1_250


# ---------------------------------------------------------------------------
# pack_vector edge cases
# ---------------------------------------------------------------------------

def test_pack_vector_already_packed_bytes_passes_through():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("r", "Title", "Abstract.")
    packed = pack_vector(record.vector)
    assert pack_vector(packed) is packed


def test_pack_vector_bytes_wrong_size_raises():
    with pytest.raises(ValueError):
        pack_vector(b"\x00" * 100)


# ---------------------------------------------------------------------------
# encode_slots with empty slots returns all-ones vector
# ---------------------------------------------------------------------------

def test_encode_slots_empty_returns_ones():
    encoder = ScientificPaperEncoder()
    empty_slots = ScientificSlots({})
    vector = encoder.encode_slots(empty_slots)
    assert np.all(vector == 1)
    assert vector.shape == (DIMENSIONS,)


# ---------------------------------------------------------------------------
# extract_slots explicit bracket notation
# ---------------------------------------------------------------------------

def test_extract_slots_explicit_brackets_override_rules():
    encoder = ScientificPaperEncoder()
    text = "[DOMAIN:biology][MECHANISM:routing] Some paper about cell routing."
    slots = encoder.extract_slots(text)
    assert "biology" in slots.get("DOMAIN")
    assert "routing" in slots.get("MECHANISM")


def test_extract_slots_query_mode_no_polarity_if_neutral():
    encoder = ScientificPaperEncoder()
    # A query with no positive or negative words should not set POLARITY
    slots = encoder.extract_slots("routing algorithm performance", query=True)
    assert slots.get("POLARITY") == ()


def test_extract_slots_document_mode_sets_neutral_polarity_if_no_sentiment():
    encoder = ScientificPaperEncoder()
    slots = encoder.extract_slots("routing algorithm performance", query=False)
    assert slots.get("POLARITY") == ("neutral",)


def test_extract_slots_year_from_text():
    encoder = ScientificPaperEncoder()
    slots = encoder.extract_slots("A survey published in 2022 on routing.")
    assert slots.get("YEAR") == ("2022",)


def test_extract_slots_year_from_parameter():
    encoder = ScientificPaperEncoder()
    slots = encoder.extract_slots("routing survey", year=2021)
    assert slots.get("YEAR") == ("2021",)


# ---------------------------------------------------------------------------
# RandomHyperplaneLSH tests
# ---------------------------------------------------------------------------

def test_lsh_add_then_query_finds_exact_match():
    from aura_scientific_memory import RandomHyperplaneLSH
    lsh = RandomHyperplaneLSH(dimensions=DIMENSIONS)
    rng = np.random.default_rng(1)
    v = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    lsh.add("record_1", v)
    candidates = lsh.query(v)
    assert "record_1" in candidates


def test_lsh_multi_probe_expands_candidates_for_isolated_vector():
    from aura_scientific_memory import RandomHyperplaneLSH
    lsh = RandomHyperplaneLSH(dimensions=DIMENSIONS)
    rng = np.random.default_rng(2)
    v = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    lsh.add("only_record", v)
    # Query with exactly the same vector; minimum=1 means even one candidate suffices.
    candidates = lsh.query(v, minimum=1)
    assert "only_record" in candidates


# ---------------------------------------------------------------------------
# ScientificMemoryIndex edge cases
# ---------------------------------------------------------------------------

def test_domain_bundle_returns_none_for_unknown_domain():
    index = ScientificMemoryIndex()
    assert index.domain_bundle("nonexistent_domain") is None


def test_mechanism_bundle_returns_none_for_unknown_combination():
    index = ScientificMemoryIndex()
    assert index.mechanism_bundle("physics", "nonexistent_mechanism") is None


def test_index_search_empty_index_returns_empty():
    index = ScientificMemoryIndex()
    hits = index.search("any query", top_k=5)
    assert hits == []


def test_index_deduplicates_on_re_add():
    encoder = ScientificPaperEncoder()
    index = ScientificMemoryIndex(encoder)
    record = encoder.encode_document("dup", "Title", "Abstract.")
    index.add(record)
    # Re-encode same record and add again (simulates duplicate ingest)
    record2 = encoder.encode_document("dup", "Title", "Abstract.")
    index.add(record2)
    assert len(index.records) == 1


def test_load_jsonl_nonexistent_path_returns_empty_index(tmp_path):
    index = ScientificMemoryIndex.load_jsonl(tmp_path / "does_not_exist.jsonl")
    assert len(index.records) == 0


# ---------------------------------------------------------------------------
# index_from_rows edge cases
# ---------------------------------------------------------------------------

def test_index_from_rows_empty_input():
    index = index_from_rows([])
    assert len(index.records) == 0


def test_index_from_rows_skips_empty_record_id():
    rows = [("", "TITLE: test | ABSTRACT: abstract", None)]
    index = index_from_rows(rows)
    assert len(index.records) == 0


def test_index_from_rows_skips_empty_content():
    rows = [("ARXIV_TEST", "", None)]
    index = index_from_rows(rows)
    assert len(index.records) == 0


def test_index_from_rows_with_correct_sized_blob_uses_it():
    encoder = ScientificPaperEncoder()
    original = encoder.encode_document("r1", "Edge VSA", "Hyperdimensional computing.")
    packed = pack_vector(original.vector)
    rows = [("ARXIV_R1", "TITLE: Edge VSA | ABSTRACT: Hyperdimensional computing.", packed)]
    index = index_from_rows(rows, encoder)
    assert "ARXIV_R1" in index.records


# ---------------------------------------------------------------------------
# detect_contradictions edge cases
# ---------------------------------------------------------------------------

def test_detect_contradictions_same_polarity_not_flagged():
    encoder = ScientificPaperEncoder()
    r1 = encoder.encode_document("a", "VSA improves edge", "Empirical benchmark improves accuracy.")
    r2 = encoder.encode_document("b", "VSA also improves edge", "Benchmark improves accuracy on devices.")
    contradictions = detect_contradictions([r1, r2])
    assert all(c.left_id != c.right_id or c.left_polarity != c.right_polarity
               for c in contradictions)
    # Both are positive — should not be flagged
    assert len(contradictions) == 0


def test_detect_contradictions_neutral_records_not_flagged():
    encoder = ScientificPaperEncoder()
    r1 = encoder.encode_document("n1", "Vector routing study", "A study of routing algorithms.")
    r2 = encoder.encode_document("n2", "Another routing study", "Routing under load conditions.")
    contradictions = detect_contradictions([r1, r2])
    assert len(contradictions) == 0


def test_detect_contradictions_unrelated_topics_not_flagged():
    encoder = ScientificPaperEncoder()
    pos = encoder.encode_document("p", "VSA improves edge speed", "Benchmark improves latency on edge devices.")
    neg = encoder.encode_document("n", "Coral biology harms ocean", "Ocean warming degrades coral populations.")
    contradictions = detect_contradictions([pos, neg])
    # Different topics; similarity is low; should not reach threshold
    assert len(contradictions) == 0


def test_detect_contradictions_custom_threshold():
    encoder = ScientificPaperEncoder()
    improves = encoder.encode_document(
        "pos", "Quantization improves accuracy", "Quantization improves accuracy."
    )
    harms = encoder.encode_document(
        "neg", "Quantization harms accuracy", "Quantization harms accuracy."
    )
    # With a very high threshold, even contradictory papers might not qualify.
    contradictions_high = detect_contradictions([improves, harms], threshold=0.99)
    # With a very low threshold, they should be flagged.
    contradictions_low = detect_contradictions([improves, harms], threshold=0.01)
    assert len(contradictions_high) == 0
    assert len(contradictions_low) >= 1


# ---------------------------------------------------------------------------
# VSAResonator new method tests
# ---------------------------------------------------------------------------

def test_bipolar_digest_same_vector_same_bytes():
    rng = np.random.default_rng(10)
    v = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    resonator = VSAResonator(dim=DIMENSIONS)
    d1 = resonator._bipolar_digest(v)
    d2 = resonator._bipolar_digest(v.copy())
    assert d1 == d2


def test_bipolar_digest_different_vectors_different_bytes():
    rng = np.random.default_rng(11)
    v1 = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    v2 = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    resonator = VSAResonator(dim=DIMENSIONS)
    assert resonator._bipolar_digest(v1) != resonator._bipolar_digest(v2)


def test_bipolar_digest_returns_16_bytes():
    rng = np.random.default_rng(12)
    v = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    resonator = VSAResonator(dim=DIMENSIONS)
    assert len(resonator._bipolar_digest(v)) == 16


def test_exact_bipolar_factorization_empty_book_a_returns_none():
    rng = np.random.default_rng(13)
    book_b = [rng.choice(np.array([-1, 1], dtype=np.int8), 100) for _ in range(3)]
    resonator = VSAResonator(dim=100)
    composite = np.ones(100, dtype=np.int8)
    assert resonator._exact_bipolar_factorization(composite, [], book_b) is None


def test_exact_bipolar_factorization_empty_book_b_returns_none():
    rng = np.random.default_rng(14)
    book_a = [rng.choice(np.array([-1, 1], dtype=np.int8), 100) for _ in range(3)]
    resonator = VSAResonator(dim=100)
    composite = np.ones(100, dtype=np.int8)
    assert resonator._exact_bipolar_factorization(composite, book_a, []) is None


def test_exact_bipolar_factorization_non_bipolar_composite_returns_none():
    rng = np.random.default_rng(15)
    book_a = [rng.choice(np.array([-1, 1], dtype=np.int8), 100) for _ in range(3)]
    book_b = [rng.choice(np.array([-1, 1], dtype=np.int8), 100) for _ in range(3)]
    resonator = VSAResonator(dim=100)
    # A composite with 0 values is not strictly bipolar (-1 or 1)
    composite = np.zeros(100, dtype=np.int8)
    assert resonator._exact_bipolar_factorization(composite, book_a, book_b) is None


def test_exact_bipolar_factorization_small_codebooks():
    rng = np.random.default_rng(16)
    dim = 100
    book_a = [rng.choice(np.array([-1, 1], dtype=np.int8), dim) for _ in range(5)]
    book_b = [rng.choice(np.array([-1, 1], dtype=np.int8), dim) for _ in range(5)]
    resonator = VSAResonator(dim=dim)
    composite = resonator.bind(book_a[2], book_b[4])
    result = resonator._exact_bipolar_factorization(composite, book_a, book_b)
    assert result == (2, 4)


def test_gsb_quantize_constant_vector_gain_is_one():
    resonator = VSAResonator(dim=DIMENSIONS)
    # A constant vector has std=0 → gain should be set to 1.0
    constant = np.full(DIMENSIONS, 5.0, dtype=np.float32)
    gain, _shape, _bias = resonator.gsb_quantize(constant)
    assert gain == 1.0


def test_gsb_quantize_complex_input_uses_angle():
    resonator = VSAResonator(dim=100)
    # A purely imaginary vector: angle = pi/2 everywhere
    complex_v = np.full(100, 1j, dtype=np.complex64)
    gain, _shape, _bias = resonator.gsb_quantize(complex_v)
    # angle(1j) = pi/2 ≈ 1.5708, so the vector is constant; gain=1.0
    assert gain == 1.0


def test_gsb_quantize_no_side_effects_no_cache():
    resonator = VSAResonator(dim=DIMENSIONS)
    rng = np.random.default_rng(17)
    v = rng.standard_normal(DIMENSIONS).astype(np.float32)
    g1, s1, b1 = resonator.gsb_quantize(v)
    g2, s2, b2 = resonator.gsb_quantize(v)
    # Without caching, results should still be identical (deterministic)
    assert g1 == g2
    assert b1 == b2
    assert np.array_equal(s1, s2)
    # Cache should remain empty (the new implementation does not use id-based cache)
    assert resonator._gsb_cache == {}


def test_bind_is_self_inverse():
    resonator = VSAResonator(dim=DIMENSIONS)
    rng = np.random.default_rng(18)
    a = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    b = rng.choice(np.array([-1, 1], dtype=np.int8), DIMENSIONS)
    composite = resonator.bind(a, b)
    recovered_a = resonator.bind(composite, b)
    assert np.array_equal(recovered_a, a)


def test_bundle_tie_breaking_all_ones():
    resonator = VSAResonator(dim=4)
    # Two vectors that cancel each other → sum=0 for all dims → should all become 1
    v1 = np.array([1, 1, -1, -1], dtype=np.int8)
    v2 = np.array([-1, -1, 1, 1], dtype=np.int8)
    bundled = resonator.bundle([v1, v2])
    assert np.all(bundled == 1)


def test_resonate_falls_back_to_iterative_for_noisy_composite():
    rng = np.random.default_rng(19)
    dim = 100
    book_a = [rng.choice(np.array([-1, 1], dtype=np.int8), dim) for _ in range(10)]
    book_b = [rng.choice(np.array([-1, 1], dtype=np.int8), dim) for _ in range(10)]
    resonator = VSAResonator(dim=dim)
    # Build a noisy composite (not strictly bipolar) → exact path returns None
    composite = resonator.bind(book_a[3], book_b[7]).astype(np.float32)
    composite[0] = 0.5  # inject non-bipolar value
    # Should not raise; iterative fallback handles it
    result = resonator.resonate(composite, book_a, book_b)
    assert isinstance(result, tuple)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# ArxivPaper.to_dict changes
# ---------------------------------------------------------------------------

def test_arxiv_paper_to_dict_includes_slots_and_vector_keys():
    paper = ArxivPaper(
        paper_id="2401.99999",
        title="Test Paper",
        authors=["A. Author"],
        abstract="A test abstract.",
        published=datetime(2024, 1, 1),
        categories=["cs.AI"],
        slots={"DOMAIN": ["computer_science"]},
    )
    d = paper.to_dict()
    assert "slots" in d
    assert "vector" in d
    assert d["slots"] == {"DOMAIN": ["computer_science"]}
    assert d["vector"] is None  # vector not set


def test_arxiv_paper_to_dict_vector_is_base64_when_set():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("r", "Edge HDC", "Hyperdimensional computing on edge devices.")
    paper = ArxivPaper(
        paper_id="2401.11111",
        title="Edge HDC",
        authors=[],
        abstract="Hyperdimensional computing on edge devices.",
        published=datetime(2024, 1, 1),
        categories=["cs.AI"],
        vector=record.vector_array(),
    )
    d = paper.to_dict()
    assert d["vector"] is not None
    decoded = base64.b64decode(d["vector"])
    assert len(decoded) == 1_250
    restored = unpack_vector(decoded)
    assert np.array_equal(restored, record.vector_array())


def test_arxiv_paper_to_dict_vector_none_when_not_set():
    paper = ArxivPaper(
        paper_id="2401.22222",
        title="No vector",
        authors=[],
        abstract="No vector set.",
        published=datetime(2024, 1, 1),
        categories=[],
    )
    d = paper.to_dict()
    assert d["vector"] is None


# ---------------------------------------------------------------------------
# EnhancedArxivForager._paper_from_dict tests
# ---------------------------------------------------------------------------

def test_paper_from_dict_round_trip_preserves_vector():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("2401.33333", "VSA Edge", "HDC improves edge devices.")
    paper = ArxivPaper(
        paper_id="2401.33333",
        title="VSA Edge",
        authors=["R. Esearcher"],
        abstract="HDC improves edge devices.",
        published=datetime(2024, 6, 1),
        categories=["cs.LG"],
        vector=record.vector_array(),
        slots=record.slots.to_jsonable(),
    )
    d = paper.to_dict()
    forager = EnhancedArxivForager()
    restored = forager._paper_from_dict(d)
    assert restored.paper_id == "2401.33333"
    assert restored.vector is not None
    assert len(pack_vector(restored.vector)) == 1_250


def test_paper_from_dict_invalid_base64_vector_falls_back():
    forager = EnhancedArxivForager()
    data = {
        "paper_id": "2401.44444",
        "title": "Fallback paper",
        "authors": [],
        "abstract": "Fallback abstract.",
        "published": datetime(2024, 1, 1).isoformat(),
        "categories": [],
        "slots": {},
        "vector": "!!!invalid_base64!!!",
        "metadata": {},
    }
    paper = forager._paper_from_dict(data)
    # Should fall back gracefully to a generated vector
    assert paper.paper_id == "2401.44444"
    assert paper.vector is not None
    assert len(pack_vector(paper.vector)) == 1_250


def test_paper_from_dict_missing_slots_generates_vector():
    forager = EnhancedArxivForager()
    data = {
        "paper_id": "2401.55555",
        "title": "Physics Routing",
        "authors": [],
        "abstract": "Quantum routing in distributed networks.",
        "published": datetime(2024, 3, 1).isoformat(),
        "categories": ["quant-ph"],
        "slots": {},
        "vector": None,
        "metadata": {},
    }
    paper = forager._paper_from_dict(data)
    assert paper.vector is not None


# ---------------------------------------------------------------------------
# EnhancedArxivForager._record_for_paper tests
# ---------------------------------------------------------------------------

def test_record_for_paper_uses_cached_slots_when_available():
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("r", "Routing", "Quantum route dispatch.")
    paper = ArxivPaper(
        paper_id="r",
        title="Routing",
        authors=[],
        abstract="Quantum route dispatch.",
        published=datetime(2024, 1, 1),
        categories=[],
        vector=record.vector_array(),
        slots=record.slots.to_jsonable(),
    )
    forager = EnhancedArxivForager()
    result = forager._record_for_paper(paper)
    assert result.record_id == "r"
    # Slots should match the cached ones (same keys present)
    assert result.slots.get("DOMAIN") == record.slots.get("DOMAIN")


def test_record_for_paper_encodes_from_scratch_when_no_slots():
    paper = ArxivPaper(
        paper_id="new_paper",
        title="Edge VSA",
        authors=[],
        abstract="Hyperdimensional edge devices.",
        published=datetime(2024, 1, 1),
        categories=["cs.AI"],
    )
    forager = EnhancedArxivForager()
    result = forager._record_for_paper(paper)
    assert result.vector is not None
    assert result.record_id == "new_paper"


# ---------------------------------------------------------------------------
# EnhancedArxivForager._load_disk_cache tests
# ---------------------------------------------------------------------------

def test_load_disk_cache_skips_malformed_json(tmp_path):
    (tmp_path / "bad.json").write_text("not valid json {{", encoding="utf-8")
    forager = EnhancedArxivForager()
    forager._storage_dir = tmp_path
    forager._load_disk_cache()
    assert len(forager._paper_cache) == 0


def test_load_disk_cache_loads_valid_paper(tmp_path):
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("2401.66666", "Load Cache Test", "Hyperdimensional caching.")
    paper = ArxivPaper(
        paper_id="2401.66666",
        title="Load Cache Test",
        authors=["B. Author"],
        abstract="Hyperdimensional caching.",
        published=datetime(2024, 2, 1),
        categories=["cs.AI"],
        vector=record.vector_array(),
        slots=record.slots.to_jsonable(),
    )
    import json
    (tmp_path / "2401.66666.json").write_text(json.dumps(paper.to_dict()), encoding="utf-8")
    forager = EnhancedArxivForager()
    forager._storage_dir = tmp_path
    forager._load_disk_cache()
    assert "2401.66666" in forager._paper_cache


def test_load_disk_cache_skips_already_cached_paper(tmp_path):
    encoder = ScientificPaperEncoder()
    record = encoder.encode_document("2401.77777", "Duplicate Test", "This is a duplicate paper.")
    paper = ArxivPaper(
        paper_id="2401.77777",
        title="Duplicate Test",
        authors=[],
        abstract="This is a duplicate paper.",
        published=datetime(2024, 2, 1),
        categories=[],
        vector=record.vector_array(),
        slots=record.slots.to_jsonable(),
    )
    import json
    (tmp_path / "2401.77777.json").write_text(json.dumps(paper.to_dict()), encoding="utf-8")
    forager = EnhancedArxivForager()
    forager._storage_dir = tmp_path
    # Pre-populate the cache with this paper
    forager._paper_cache["2401.77777"] = paper
    forager._load_disk_cache()
    # Should not change the existing entry
    assert forager._paper_cache["2401.77777"] is paper


class _FakeArxivResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


def test_arxiv_request_retries_with_smaller_page(monkeypatch):
    payload = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom"></feed>"""
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        if len(calls) == 1:
            raise TimeoutError("read timed out")
        return _FakeArxivResponse(payload)

    async def no_sleep(_delay):
        return None

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    forager = ArXivForager()
    xml_data, page_size = asyncio.run(
        forager._fetch_arxiv_xml(
            "cat:cs.AI",
            max_results=100,
            max_retries=2,
            timeout=1.0,
        )
    )

    first = parse_qs(urlsplit(calls[0][0]).query)
    second = parse_qs(urlsplit(calls[1][0]).query)
    assert xml_data == payload
    assert first["max_results"] == ["100"]
    assert second["max_results"] == ["50"]
    assert page_size == 50
    assert calls[1][1] > calls[0][1]


def test_backtracker_window_upgrade_is_bounded_and_contiguous():
    state = {
        "crawl_offset_index": 900,
        "crawl_window_end": "202605232202",
    }
    forager = ArXivForager()

    start, end = forager._normalise_backtracker_window(state)
    assert start == "202605222202"
    assert end == "202605232202"

    forager._advance_backtracker_window(state)
    assert state["crawl_window_end"] == "202605222202"
    assert state["crawl_window_start"] == "202605212202"


def test_backtracker_reuses_earliest_paper_boundary_minute():
    state = {
        "crawl_window_start": "202605222202",
        "crawl_window_end": "202605232202",
    }
    forager = ArXivForager()
    forager._advance_backtracker_window(
        state, "2026-05-23T04:15:00Z"
    )

    assert state["crawl_window_end"] == "202605230415"
    assert state["crawl_window_start"] == "202605220415"


class _FakeExecuteResult:
    def __init__(self, row=None):
        self.row = row

    def __await__(self):
        async def _done():
            return self

        return _done().__await__()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def fetchone(self):
        return self.row


class _FakeBacktrackerConnection:
    def __init__(self, state):
        self.state = state
        self.saved_states = []
        self.ingested_rows = []
        self.commits = 0

    def execute(self, query, params=None):
        if query.lstrip().startswith("SELECT"):
            return _FakeExecuteResult((json.dumps(self.state),))
        if params and params[0].startswith("{"):
            self.saved_states.append(json.loads(params[0]))
        return _FakeExecuteResult()

    async def executemany(self, _query, rows):
        self.ingested_rows.extend(rows)

    async def commit(self):
        self.commits += 1


def test_backtracker_upgrades_legacy_state_before_fetch(monkeypatch):
    state = {
        "crawl_offset_index": 900,
        "last_crawl_time": 0.0,
        "crawl_window_end": "202605232202",
    }
    conn = _FakeBacktrackerConnection(state)
    node = SimpleNamespace(
        memory_palace=SimpleNamespace(conn=conn),
        runtime_metrics={},
    )
    forager = ArXivForager(node)
    captured = {}
    payload = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
      <opensearch:totalResults>1</opensearch:totalResults>
      <entry>
        <title>Bounded Backtracking</title>
        <summary>Reliable metadata harvesting.</summary>
        <published>2026-05-23T04:15:00Z</published>
      </entry>
    </feed>"""

    async def fake_fetch(search_query, **kwargs):
        captured["search_query"] = search_query
        captured.update(kwargs)
        return payload, kwargs["max_results"]

    monkeypatch.setattr(forager, "_fetch_arxiv_xml", fake_fetch)
    assert asyncio.run(
        forager.upgraded_arxiv_backtracker(max_results=100)
    )

    assert captured["start"] == 0
    assert captured["search_query"] == (
        "cat:cs.* AND "
        "submittedDate:[202605222202 TO 202605232202]"
    )
    assert len(conn.ingested_rows) == 1
    assert conn.saved_states[-1]["crawl_offset_index"] == 0
    assert conn.commits == 1


_OAI_PAYLOAD = b"""<?xml version="1.0"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
         xmlns:arXiv="http://arxiv.org/OAI/arXiv/">
  <ListRecords>
    <record>
      <header>
        <identifier>oai:arXiv.org:2601.00001</identifier>
        <datestamp>2026-01-02</datestamp>
        <setSpec>cs</setSpec>
      </header>
      <metadata>
        <arXiv:arXiv>
          <arXiv:id>2601.00001</arXiv:id>
          <arXiv:created>02-Jan-2026</arXiv:created>
          <arXiv:authors>
            <arXiv:author>
              <arXiv:keyname>Researcher</arXiv:keyname>
              <arXiv:forenames>A.</arXiv:forenames>
            </arXiv:author>
          </arXiv:authors>
          <arXiv:title>Edge Vector Symbolic Memory</arXiv:title>
          <arXiv:categories>cs.AI cs.LG</arXiv:categories>
          <arXiv:abstract>
            Hyperdimensional computing improves retrieval on edge devices.
          </arXiv:abstract>
        </arXiv:arXiv>
      </metadata>
    </record>
    <resumptionToken/>
  </ListRecords>
</OAI-PMH>"""


def test_oai_parser_returns_forager_record_shape():
    records, token = ArXivForager._parse_arxiv_oai_records(_OAI_PAYLOAD)

    assert token is None
    assert records[0]["paper_id"] == "2601.00001"
    assert records[0]["authors"] == ["A. Researcher"]
    assert records[0]["categories"] == ["cs.AI", "cs.LG"]
    assert records[0]["pdf_url"].endswith("/2601.00001")
    assert records[0]["published"] == datetime(2026, 1, 2)


def test_backtracker_falls_back_to_oai(monkeypatch):
    state = {
        "crawl_offset_index": 0,
        "last_crawl_time": 0.0,
        "crawl_window_start": "202601010000",
        "crawl_window_end": "202601030000",
    }
    conn = _FakeBacktrackerConnection(state)
    node = SimpleNamespace(
        memory_palace=SimpleNamespace(conn=conn),
        runtime_metrics={},
    )
    forager = ArXivForager(node)

    async def failed_atom(*_args, **_kwargs):
        raise TimeoutError("Atom API unavailable")

    async def healthy_oai(**_kwargs):
        return _OAI_PAYLOAD

    monkeypatch.setattr(forager, "_fetch_arxiv_xml", failed_atom)
    monkeypatch.setattr(forager, "_fetch_arxiv_oai_xml", healthy_oai)

    assert asyncio.run(forager.upgraded_arxiv_backtracker(max_results=100))
    assert len(conn.ingested_rows) == 1
    assert conn.saved_states[-1]["crawl_window_end"] == "202601010000"


def test_enhanced_search_uses_raw_query_and_safe_page_size(monkeypatch):
    payload = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
      <opensearch:totalResults>1</opensearch:totalResults>
      <entry>
        <id>https://arxiv.org/abs/2601.00001</id>
        <title>Edge VSA</title>
        <summary>Hyperdimensional retrieval on edge devices.</summary>
        <published>2026-01-02T00:00:00Z</published>
        <author><name>A. Researcher</name></author>
        <category term="cs.AI"/>
        <link href="https://arxiv.org/pdf/2601.00001" type="application/pdf"/>
      </entry>
    </feed>"""
    captured = {}

    async def fake_fetch(search_query, **kwargs):
        captured["search_query"] = search_query
        captured.update(kwargs)
        return payload, kwargs["max_results"]

    forager = EnhancedArxivForager()
    monkeypatch.setattr(forager, "_fetch_arxiv_xml", fake_fetch)
    config = ForagerConfig(
        query="vector symbolic",
        categories=["cs.AI"],
        max_results=2_000,
        max_total=500,
        max_days_old=365,
    )
    papers = asyncio.run(
        forager._search_via_urllib(
            config,
            datetime(2026, 1, 1),
            datetime(2026, 1, 3),
        )
    )

    assert captured["max_results"] == 200
    assert captured["search_query"] == (
        "(cat:cs.AI) AND (all:vector symbolic) AND "
        "submittedDate:[202601010000 TO 202601030000]"
    )
    assert papers[0]["paper_id"] == "2601.00001"
    assert papers[0]["categories"] == ["cs.AI"]


def test_enhanced_search_falls_back_to_oai(monkeypatch):
    forager = EnhancedArxivForager()

    async def failed_atom(*_args, **_kwargs):
        raise TimeoutError("Atom API unavailable")

    async def healthy_oai(**_kwargs):
        return _OAI_PAYLOAD

    monkeypatch.setattr(forager, "_fetch_arxiv_xml", failed_atom)
    monkeypatch.setattr(forager, "_fetch_arxiv_oai_xml", healthy_oai)
    config = ForagerConfig(
        query="vector symbolic",
        categories=["cs.AI"],
        max_total=1,
        max_days_old=365,
    )

    papers = asyncio.run(
        forager._search_via_urllib(
            config,
            datetime(2026, 1, 1),
            datetime(2026, 1, 3),
        )
    )

    assert papers[0]["paper_id"] == "2601.00001"
    assert forager.stats.errors == 0
