"""Structured VSA memory for scientific papers.

The original research path stored papers and queries with different encoders.
This module provides one deterministic representation for both, compact
bit-packed storage, hierarchical routing, approximate LSH candidate retrieval,
and polarity-aware contradiction detection.
"""

from __future__ import annotations

import base64
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

import numpy as np

DIMENSIONS = 10_000
ENCODING_VERSION = "scientific-vsa-v1"
SLOT_NAMES = (
    "DOMAIN",
    "MECHANISM",
    "EFFECT",
    "POLARITY",
    "EVIDENCE",
    "ENTITY",
    "RELATION",
    "METHOD",
    "SCALE",
    "YEAR",
)

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "for",
    "from", "in", "into", "is", "it", "of", "on", "or", "our", "that",
    "the", "their", "these", "this", "to", "using", "we", "with",
}

_DOMAIN_RULES = {
    "computer_science": (
        "computer", "software", "algorithm", "network", "database", "compiler",
        "artificial intelligence", "machine learning", "cs.", "cs:",
    ),
    "physics": (
        "physics", "quantum", "particle", "superconduct", "photon", "relativity",
    ),
    "biology": (
        "biology", "biological", "protein", "cell", "genome", "coral", "ecology",
    ),
    "medicine": (
        "clinical", "patient", "therapy", "disease", "medical", "immune",
    ),
    "materials": (
        "material", "lattice", "crystal", "polymer", "alloy", "catalyst",
    ),
    "law": (
        "legal", "law", "treaty", "adjudication", "precedent", "justice",
    ),
}

_MECHANISM_RULES = {
    "conditional_selection": (
        "conditional computation", "specialist", "expert activation",
        "capability-aware", "capability based", "relevant experts",
    ),
    "routing": ("route", "routing", "next hop", "message passing", "dispatch"),
    "quantization": ("quantization", "quantize", "w4a4", "low precision"),
    "associative_memory": (
        "associative memory", "hopfield", "content addressable", "attractor",
    ),
    "vector_symbolic": (
        "vector symbolic", "hyperdimensional", "vsa", "hdc", "holographic",
    ),
    "factorization": ("factorization", "factorisation", "resonator", "unbind"),
    "compression": ("compression", "compress", "encoding", "compact"),
    "optimization": ("optimization", "optimisation", "minimize", "maximize"),
    "attention": ("attention", "transformer", "token"),
    "simulation": ("simulation", "simulate", "numerical model"),
}

_METHOD_RULES = {
    "svd": ("svd", "singular value"),
    "lsh": ("locality sensitive hash", "lsh", "random hyperplane"),
    "vsa": ("vector symbolic", "hyperdimensional", "vsa", "hdc"),
    "reinforcement_learning": ("reinforcement learning", "q-learning", "policy gradient"),
    "neural_network": ("neural network", "deep learning", "transformer"),
    "finite_state": ("finite-state", "finite state", "fst", "transducer"),
    "experiment": ("experiment", "measured", "measurement"),
}

_POSITIVE = (
    "improve", "improves", "improved", "increase", "increases", "enhance",
    "reduce", "reduces", "reduced", "outperform", "benefit", "successful",
)
_NEGATIVE = (
    "harm", "harms", "degrade", "degrades", "degraded", "worsen", "fails",
    "failure", "should not", "does not", "did not", "not improve",
    "no improvement", "unsafe", "ineffective", "negative",
)

_RELATION_RULES = {
    "select_by_capability": (
        "capability-aware", "capability based", "specialist", "relevant expert",
        "according to capability", "declared hardware capabilities",
    ),
    "causes": ("causes", "leads to", "results in", "drives"),
    "improves": _POSITIVE,
    "harms": _NEGATIVE,
    "compresses": ("compress", "quantiz", "reduce memory", "compact"),
    "predicts": ("predict", "forecast", "estimate"),
}

_EFFECT_RULES = {
    "efficient_allocation": (
        "relevant specialist", "relevant expert", "capability-aware",
        "according to capability", "small subset", "inactive experts",
    ),
    "lower_memory": ("reduce memory", "memory reduction", "compression", "compact"),
    "lower_latency": ("reduce latency", "faster", "speedup", "low latency"),
    "higher_accuracy": ("improve accuracy", "higher accuracy", "outperform"),
    "lower_accuracy": ("degrade accuracy", "harms accuracy", "lower accuracy"),
    "fault_tolerance": ("fault tolerant", "resilien", "self-heal", "recovery"),
}

_EVIDENCE_RULES = {
    "empirical": ("experiment", "measured", "dataset", "benchmark", "clinical trial"),
    "simulation": ("simulation", "simulated", "numerical model"),
    "theoretical": ("theorem", "proof", "theoretical", "analysis"),
    "review": ("survey", "review", "meta-analysis"),
}

_SCALE_RULES = {
    "nano": ("nano", "molecular", "atomic"),
    "micro": ("micro", "cellular", "device"),
    "edge": ("edge device", "mobile", "embedded", "termux", "iot"),
    "distributed": ("distributed", "swarm", "network", "mesh"),
    "macro": ("population", "ecosystem", "global", "large-scale"),
}


def _normalise_text(text: str) -> str:
    """
    Normalize text by lowercasing and extracting valid tokens.

    Returns a space-separated string of tokens containing only alphanumeric characters, hyphens, and underscores.
    """
    return " ".join(re.findall(r"[a-z0-9][a-z0-9_-]*", text.lower()))


@lru_cache(maxsize=256)
def _stable_bipolar(label: str, dimensions: int = DIMENSIONS) -> np.ndarray:
    """
    Generate a deterministic bipolar vector from a label.

    Returns:
    	np.ndarray: A read-only bipolar vector with values of ±1. Identical labels always produce identical vectors.
    """
    digest = hashlib.blake2b(label.encode("utf-8"), digest_size=8).digest()
    seed = int.from_bytes(digest, "little")
    rng = np.random.default_rng(seed)
    vector = rng.choice(np.array([-1, 1], dtype=np.int8), size=dimensions)
    vector.flags.writeable = False
    return vector


def _canonical_token(token: str) -> str:
    """
    Normalize and canonicalize a token by applying established aliases.

    Parameters:
    	token (str): The token to canonicalize.

    Returns:
    	The canonicalized token string.
    """
    value = _normalise_text(token).replace(" ", "_")
    aliases = {
        "mixture_of_experts": "expert_system",
        "specialized_experts": "expert_system",
        "specialist_neural_experts": "expert_system",
        "hardware_capability": "capability",
        "hardware_capabilities": "capability",
        "low_rank_svd": "svd",
        "singular_value_decomposition": "svd",
    }
    return aliases.get(value, value)


def _match_rules(text: str, rules: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """
    Identify rule labels whose keywords appear as substrings in the text.

    Parameters:
    	text (str): The text to scan for keyword matches
    	rules (dict[str, tuple[str, ...]]): A mapping of rule labels to tuples of keywords

    Returns:
    	tuple[str, ...]: Distinct rule labels whose keywords matched, in rule-dictionary order
    """
    matches = [
        label
        for label, needles in rules.items()
        if any(needle in text for needle in needles)
    ]
    return tuple(dict.fromkeys(matches))


def _content_terms(text: str, limit: int = 8) -> tuple[str, ...]:
    """
    Extract the most frequently occurring content words from text.

    Parameters:
    	text (str): Source text to analyze.
    	limit (int): Maximum number of words to return. Defaults to 8.

    Returns:
    	tuple[str, ...]: Up to `limit` content words, ranked by frequency (descending) then alphabetically for ties.
    """
    polarity_words = set(_POSITIVE) | set(_NEGATIVE)
    words = [
        _canonical_token(word)
        for word in re.findall(r"[a-z][a-z0-9_-]{2,}", text.lower())
        if word not in _STOPWORDS and word not in polarity_words
    ]
    counts: dict[str, int] = defaultdict(int)
    for word in words:
        counts[word] += 1
    ranked = sorted(counts, key=lambda word: (-counts[word], word))
    return tuple(ranked[:limit])


def _special_polarity_vector(value: str, dimensions: int) -> np.ndarray:
    """
    Generate a deterministic bipolar vector for the given polarity value.

    Parameters:
    	value (str): The polarity value; expected values are 'positive', 'negative', or other (treated as neutral).
    	dimensions (int): The dimensionality of the bipolar vector.

    Returns:
    	A bipolar vector corresponding to 'positive' (positive axis), 'negative' (negated axis), or neutral axis for other values.
    """
    positive = _stable_bipolar("POLARITY::AXIS", dimensions)
    if value == "positive":
        return positive
    if value == "negative":
        return -positive
    return _stable_bipolar("POLARITY::NEUTRAL", dimensions)


@dataclass(frozen=True)
class ScientificSlots:
    values: dict[str, tuple[str, ...]]

    def get(self, slot: str) -> tuple[str, ...]:
        """
        Retrieve the terms associated with a given slot.

        Parameters:
        	slot (str): The slot name.

        Returns:
        	tuple[str, ...]: The terms for the slot, or an empty tuple if the slot does not exist.
        """
        return self.values.get(slot, ())

    def without(self, *slots: str) -> ScientificSlots:
        """
        Create a new instance excluding the specified slots.

        Parameters:
        	slots (str): Slot names to exclude.

        Returns:
        	ScientificSlots: A new instance with the specified slots removed.
        """
        blocked = set(slots)
        return ScientificSlots({key: value for key, value in self.values.items() if key not in blocked})

    def to_jsonable(self) -> dict[str, list[str]]:
        """
        Serialize slot values as a JSON-compatible dictionary.

        Returns:
            Dictionary with slot names as keys and lists of slot values.
        """
        return {key: list(value) for key, value in self.values.items()}

    @classmethod
    def from_jsonable(cls, value: dict[str, list[str]]) -> ScientificSlots:
        """
        Reconstruct ScientificSlots from a JSON-compatible dictionary.

        Parameters:
        	value (dict[str, list[str]]): Dictionary mapping slot names to term lists.

        Returns:
        	ScientificSlots: A new instance, excluding slots with empty term lists.
        """
        return cls({key: tuple(items) for key, items in value.items() if items})


@dataclass
class ScientificRecord:
    record_id: str
    title: str
    abstract: str
    slots: ScientificSlots
    vector: np.ndarray | bytes
    metadata: dict = field(default_factory=dict)

    def vector_array(self) -> np.ndarray:
        """
        Return the vector as a bipolar int8 numpy array.

        Returns:
        	np.ndarray: The vector in unpacked bipolar int8 format.
        """
        if isinstance(self.vector, bytes):
            return unpack_vector(self.vector)
        return np.asarray(self.vector, dtype=np.int8)


@dataclass(frozen=True)
class SearchHit:
    record_id: str
    score: float
    vector_similarity: float
    slot_similarity: float
    record: ScientificRecord


@dataclass(frozen=True)
class Contradiction:
    left_id: str
    right_id: str
    topic_similarity: float
    left_polarity: str
    right_polarity: str


class ScientificPaperEncoder:
    """One structured encoder shared by documents and queries."""

    def __init__(self, dimensions: int = DIMENSIONS) -> None:
        """
        Initialize the encoder with deterministic slot anchor vectors.

        Parameters:
            dimensions (int): The dimensionality of the bipolar hypervectors. Defaults to DIMENSIONS.
        """
        self.dimensions = dimensions
        self._slot_anchors = {
            slot: _stable_bipolar(f"SLOT::{slot}", dimensions)
            for slot in SLOT_NAMES
        }

    def extract_slots(
        self,
        text: str,
        *,
        categories: Iterable[str] = (),
        year: int | str | None = None,
        query: bool = False,
    ) -> ScientificSlots:
        """
        Extracts structured slot annotations and inferred metadata from text.

        Parses explicit slot annotations in bracketed form (e.g., `[DOMAIN: value1, value2]`) and
        infers remaining slot values. Explicit annotations always take precedence over inferred values.

        Parameters:
            text (str): The input text to process.
            categories (Iterable[str]): Additional category terms to include in slot extraction.
            year (int | str | None): A year value for the YEAR slot. If not provided, searches the text
                for a year pattern.
            query (bool): When False, POLARITY defaults to "neutral" if not explicitly set or inferred.
                When True, POLARITY is only included if explicitly specified or inferred from text.

        Returns:
            ScientificSlots: Extracted slot values, potentially including DOMAIN, MECHANISM, EFFECT,
                EVIDENCE, RELATION, METHOD, SCALE, POLARITY, ENTITY, and YEAR.
        """
        explicit = {
            match.group(1).upper(): tuple(
                _canonical_token(part)
                for part in re.split(r"[,|]", match.group(2))
                if part.strip()
            )
            for match in re.finditer(r"\[([A-Z_]+):([^\]]+)\]", text)
        }
        lowered = _normalise_text(text + " " + " ".join(categories))
        values: dict[str, tuple[str, ...]] = {}

        def assign(slot: str, found: tuple[str, ...]) -> None:
            if slot in explicit:
                values[slot] = explicit[slot]
            elif found:
                values[slot] = found

        assign("DOMAIN", _match_rules(lowered, _DOMAIN_RULES))
        mechanisms = list(_match_rules(lowered, _MECHANISM_RULES))
        if (
            any(word in lowered for word in ("route", "assign", "select", "activate"))
            and any(word in lowered for word in ("capability", "specialist", "expert", "relevant"))
        ):
            mechanisms.insert(0, "conditional_selection")
        assign("MECHANISM", tuple(dict.fromkeys(mechanisms)))
        assign("EFFECT", _match_rules(lowered, _EFFECT_RULES))
        assign("EVIDENCE", _match_rules(lowered, _EVIDENCE_RULES))
        assign("RELATION", _match_rules(lowered, _RELATION_RULES))
        assign("METHOD", _match_rules(lowered, _METHOD_RULES))
        assign("SCALE", _match_rules(lowered, _SCALE_RULES))

        if "POLARITY" in explicit:
            values["POLARITY"] = explicit["POLARITY"]
        elif any(term in lowered for term in _NEGATIVE):
            values["POLARITY"] = ("negative",)
        elif any(term in lowered for term in _POSITIVE):
            values["POLARITY"] = ("positive",)
        elif not query:
            values["POLARITY"] = ("neutral",)

        entity_terms = _content_terms(lowered)
        if "ENTITY" in explicit:
            values["ENTITY"] = explicit["ENTITY"]
        elif entity_terms:
            values["ENTITY"] = entity_terms

        if "YEAR" in explicit:
            values["YEAR"] = explicit["YEAR"]
        elif year is not None:
            values["YEAR"] = (str(year),)
        else:
            found_year = re.search(r"\b(19|20)\d{2}\b", lowered)
            if found_year:
                values["YEAR"] = (found_year.group(0),)

        return ScientificSlots(values)

    def encode_slots(self, slots: ScientificSlots) -> np.ndarray:
        """
        Encode semantic slots into a bipolar hypervector representation.

        Returns:
            np.ndarray: A bipolar vector of dtype int8, with all values in {-1, 1}.
        """
        components: list[np.ndarray] = []
        for slot in SLOT_NAMES:
            terms = slots.get(slot)
            if not terms:
                continue
            term_vectors = []
            for term in terms:
                if slot == "POLARITY":
                    term_vector = _special_polarity_vector(term, self.dimensions)
                else:
                    term_vector = _stable_bipolar(f"VALUE::{_canonical_token(term)}", self.dimensions)
                term_vectors.append(term_vector)
            content = np.sign(np.sum(np.stack(term_vectors).astype(np.int16), axis=0))
            content[content == 0] = 1
            components.append(self._slot_anchors[slot] * content.astype(np.int8))
        if not components:
            return np.ones(self.dimensions, dtype=np.int8)
        bundled = np.sum(np.stack(components).astype(np.int16), axis=0)
        bundled[bundled == 0] = 1
        return np.sign(bundled).astype(np.int8)

    def encode_document(
        self,
        record_id: str,
        title: str,
        abstract: str,
        *,
        categories: Iterable[str] = (),
        year: int | str | None = None,
        metadata: dict | None = None,
    ) -> ScientificRecord:
        """
        Encode a scientific paper into a structured record with extracted slots and vector representation.

        Parameters:
        	categories: Additional category terms to include in slot extraction.
        	year: Publication year to use for the YEAR slot.
        	metadata: Additional metadata to attach to the record.

        Returns:
        	A ScientificRecord containing the document metadata, extracted slots, and encoded bipolar vector.
        """
        text = f"{title} {abstract}"
        slots = self.extract_slots(text, categories=categories, year=year)
        return ScientificRecord(
            record_id=record_id,
            title=title,
            abstract=abstract,
            slots=slots,
            vector=self.encode_slots(slots),
            metadata=metadata or {},
        )

    def encode_query(self, query: str) -> tuple[ScientificSlots, np.ndarray]:
        """
        Encode a query for retrieval by extracting semantic slots and computing their vector representation.

        Parameters:
        	query (str): The query string to encode

        Returns:
        	tuple: A tuple of (ScientificSlots, np.ndarray) containing the extracted slots and their bipolar vector encoding
        """
        slots = self.extract_slots(query, query=True)
        return slots, self.encode_slots(slots)


def pack_vector(vector: np.ndarray | bytes) -> bytes:
    """
    Ensure a bipolar vector is in packed byte form.

    If the input is already bytes, validates its size. If it is an array, converts
    it to a compact bit-packed representation.

    Returns:
        Packed byte representation of the bipolar vector.

    Raises:
        ValueError: If a bytes input does not match the expected packed size.
    """
    if isinstance(vector, bytes):
        if len(vector) != (DIMENSIONS + 7) // 8:
            raise ValueError("packed scientific vector has the wrong size")
        return vector
    bipolar = np.asarray(vector).reshape(-1)[:DIMENSIONS] > 0
    return np.packbits(bipolar, bitorder="little").tobytes()


def unpack_vector(raw: bytes, dimensions: int = DIMENSIONS) -> np.ndarray:
    """
    Converts packed bytes into a bipolar hypervector.

    Parameters:
        raw (bytes): Packed binary representation of a bipolar vector.
        dimensions (int): Number of dimensions to unpack. Defaults to DIMENSIONS.

    Returns:
        np.ndarray: Bipolar vector of shape (dimensions,) with values ±1 in int8 dtype.
    """
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder="little")[:dimensions]
    return np.where(bits > 0, 1, -1).astype(np.int8)


def vector_similarity(
    left: np.ndarray | bytes,
    right: np.ndarray | bytes,
) -> float:
    """
    Compute cosine similarity between two vectors.

    Returns:
        Cosine similarity score ranging from -1 to 1, or 0 if either vector has zero norm.
    """
    if isinstance(left, bytes):
        left = unpack_vector(left)
    if isinstance(right, bytes):
        right = unpack_vector(right)
    a = np.asarray(left, dtype=np.float32)
    b = np.asarray(right, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


_SLOT_WEIGHTS = {
    "DOMAIN": 0.8,
    "MECHANISM": 1.6,
    "EFFECT": 1.4,
    "POLARITY": 0.3,
    "EVIDENCE": 0.6,
    "ENTITY": 1.0,
    "RELATION": 1.5,
    "METHOD": 1.3,
    "SCALE": 0.5,
    "YEAR": 0.2,
}


def slot_similarity(query: ScientificSlots, candidate: ScientificSlots) -> float:
    """
    Measures the weighted overlap of slot terms between a query and a candidate record.

    Returns:
        A similarity score between 0.0 and 1.0, weighted by slot importance. Returns 0.0
        if the query has no requested slots.
    """
    score = 0.0
    available = 0.0
    for slot, weight in _SLOT_WEIGHTS.items():
        requested = set(query.get(slot))
        if not requested:
            continue
        available += weight
        found = set(candidate.get(slot))
        if found:
            score += weight * len(requested & found) / len(requested | found)
    return score / available if available else 0.0


class RandomHyperplaneLSH:
    """Compact random-projection LSH with bounded multi-probe lookup."""

    def __init__(
        self,
        dimensions: int = DIMENSIONS,
        tables: int = 12,
        bits: int = 14,
        samples_per_bit: int = 64,
        seed: int = 0xA8C5,
    ) -> None:
        """
        Initialize a locality-sensitive hash index using random hyperplanes.
        """
        self.dimensions = dimensions
        self.tables = tables
        self.bits = bits
        rng = np.random.default_rng(seed)
        shape = (tables, bits, samples_per_bit)
        self.indices = rng.integers(0, dimensions, size=shape, dtype=np.int32)
        self.signs = rng.choice(np.array([-1, 1], dtype=np.int8), size=shape)
        self.buckets: list[dict[int, set[str]]] = [defaultdict(set) for _ in range(tables)]

    def _keys(self, vector: np.ndarray) -> tuple[int, ...]:
        """
        Compute LSH hash keys for the vector across all hash tables.

        Returns:
            Tuple of integer keys, one per hash table.
        """
        values = np.asarray(vector, dtype=np.int16)
        keys = []
        for table in range(self.tables):
            sampled = values[self.indices[table]] * self.signs[table]
            positive = np.sum(sampled, axis=1, dtype=np.int32) >= 0
            key = 0
            for bit, enabled in enumerate(positive):
                key |= int(enabled) << bit
            keys.append(key)
        return tuple(keys)

    def add(self, record_id: str, vector: np.ndarray) -> None:
        """
        Insert a record into the LSH index buckets based on the vector's hash keys.
        """
        for table, key in enumerate(self._keys(vector)):
            self.buckets[table][key].add(record_id)

    def query(self, vector: np.ndarray, minimum: int = 16) -> set[str]:
        """
        Retrieve candidate record IDs using locality-sensitive hashing with multi-probe fallback.

        Returns record IDs matched by exact hash keys across all tables. If fewer than the minimum number of candidates are found, performs multi-probe search by checking nearby hash buckets created by bit-flipping individual key positions.

        Parameters:
            vector (np.ndarray): Bipolar hypervector to query.
            minimum (int): Minimum number of candidates to retrieve before terminating multi-probe search. Defaults to 16.

        Returns:
            set[str]: Record IDs of candidate documents.
        """
        candidates: set[str] = set()
        keys = self._keys(vector)
        for table, key in enumerate(keys):
            candidates.update(self.buckets[table].get(key, ()))
        if len(candidates) < minimum:
            for table, key in enumerate(keys):
                for bit in range(self.bits):
                    candidates.update(self.buckets[table].get(key ^ (1 << bit), ()))
                    if len(candidates) >= minimum:
                        return candidates
        return candidates


class ScientificMemoryIndex:
    """Hierarchical scientific-memory index backed by packed bipolar vectors."""

    def __init__(self, encoder: ScientificPaperEncoder | None = None) -> None:
        """
        Initialize a hierarchical memory index for scientific papers with indexed slots and approximate vector retrieval.

        Parameters:
            encoder: Slot encoder for document content. Defaults to a new ScientificPaperEncoder if not provided.
        """
        self.encoder = encoder or ScientificPaperEncoder()
        self.records: dict[str, ScientificRecord] = {}
        self.by_slot_value: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.by_domain: dict[str, set[str]] = defaultdict(set)
        self.by_mechanism: dict[str, set[str]] = defaultdict(set)
        self.by_domain_mechanism: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._domain_sums: dict[str, np.ndarray] = {}
        self._domain_mechanism_sums: dict[tuple[str, str], np.ndarray] = {}
        self.lsh = RandomHyperplaneLSH(dimensions=self.encoder.dimensions)
        self.last_candidates_considered = 0

    def add(self, record: ScientificRecord) -> None:
        """
        Add a record to the index.

        Updates all slot-based indexes, domain and mechanism aggregations, and LSH index.
        Accumulates the record's vector into domain and domain-mechanism bundles for hierarchical
        search, and converts the vector to packed bytes for compact storage.

        Parameters:
            record (ScientificRecord): The record to add.
        """
        self.records[record.record_id] = record
        domains = record.slots.get("DOMAIN")
        mechanisms = record.slots.get("MECHANISM")
        source_vector = record.vector_array()
        vector = np.asarray(source_vector, dtype=np.int32)
        for slot, values in record.slots.values.items():
            for value in values:
                self.by_slot_value[(slot, value)].add(record.record_id)
        for domain in domains:
            self.by_domain[domain].add(record.record_id)
            if domain not in self._domain_sums:
                self._domain_sums[domain] = np.zeros(
                    self.encoder.dimensions,
                    dtype=np.int32,
                )
            self._domain_sums[domain] += vector
        for mechanism in mechanisms:
            self.by_mechanism[mechanism].add(record.record_id)
        for domain in domains:
            for mechanism in mechanisms:
                key = (domain, mechanism)
                self.by_domain_mechanism[key].add(record.record_id)
                if key not in self._domain_mechanism_sums:
                    self._domain_mechanism_sums[key] = np.zeros(
                        self.encoder.dimensions,
                        dtype=np.int32,
                    )
                self._domain_mechanism_sums[key] += vector
        self.lsh.add(record.record_id, source_vector)
        record.vector = pack_vector(source_vector)

    @staticmethod
    def _bundle_from_sum(total: np.ndarray | None) -> np.ndarray | None:
        """
        Convert an accumulated sum to a normalized bipolar vector.

        Parameters:
            total: Sum array to normalize, or None to return None.

        Returns:
            Bipolar array with values ±1 (zeros forced to 1), or None.
        """
        if total is None:
            return None
        bundle = np.sign(total).astype(np.int8)
        bundle[bundle == 0] = 1
        return bundle

    def domain_bundle(self, domain: str) -> np.ndarray | None:
        """
        Retrieve the bundled bipolar vector for a domain.

        Returns:
            np.ndarray | None: The bundled bipolar vector for the domain, or None if the domain has not been indexed.
        """
        return self._bundle_from_sum(self._domain_sums.get(domain))

    def mechanism_bundle(self, domain: str, mechanism: str) -> np.ndarray | None:
        """
        Return the bundled bipolar vector for a domain-mechanism pair.

        Parameters:
        	domain (str): The domain name
        	mechanism (str): The mechanism name

        Returns:
        	np.ndarray | None: A bipolar vector representing the aggregated signal for the pair, or None if the pair does not exist in the index
        """
        return self._bundle_from_sum(
            self._domain_mechanism_sums.get((domain, mechanism))
        )

    def _hierarchical_candidates(self, slots: ScientificSlots) -> set[str]:
        """
        Return records matching the given slots through hierarchical filtering and fallback strategies.

        Returns:
        	set[str]: Record IDs satisfying the slot constraints.
        """
        domains = slots.get("DOMAIN")
        mechanisms = slots.get("MECHANISM")
        slot_groups = []
        for slot, values in slots.values.items():
            group = set().union(
                *(self.by_slot_value.get((slot, value), set()) for value in values)
            )
            if group:
                slot_groups.append(group)
        if slot_groups:
            exact_structure = set.intersection(*slot_groups)
            if exact_structure:
                return exact_structure
        if domains and mechanisms:
            paired = set().union(
                *(
                    self.by_domain_mechanism.get((domain, mechanism), set())
                    for domain in domains
                    for mechanism in mechanisms
                )
            )
            if paired:
                return paired
        groups: list[set[str]] = []
        if domains:
            groups.append(set().union(*(self.by_domain.get(value, set()) for value in domains)))
        if mechanisms:
            groups.append(set().union(*(self.by_mechanism.get(value, set()) for value in mechanisms)))
        if not groups:
            return set()
        intersection = set.intersection(*groups)
        return intersection or set.union(*groups)

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        """
        Find papers in the index matching the given query.

        Returns:
            A list of SearchHit objects sorted by relevance score in descending order.
        """
        slots, vector = self.encoder.encode_query(query)
        hierarchical = self._hierarchical_candidates(slots)
        approximate = self.lsh.query(vector, minimum=max(16, top_k * 4))
        candidate_budget = max(32, top_k * 8)
        if hierarchical and approximate:
            candidates = hierarchical & approximate
            if len(candidates) < top_k:
                candidates.update(
                    sorted(hierarchical - candidates)[
                        : candidate_budget - len(candidates)
                    ]
                )
            candidates = set(sorted(candidates)[:candidate_budget])
        elif hierarchical:
            candidates = set(sorted(hierarchical)[:candidate_budget])
        elif approximate:
            candidates = set(sorted(approximate)[:candidate_budget])
        else:
            candidates = set(sorted(self.records)[:candidate_budget])
        self.last_candidates_considered = len(candidates)

        hits = []
        for record_id in candidates:
            record = self.records[record_id]
            v_score = vector_similarity(vector, record.vector_array())
            s_score = slot_similarity(slots, record.slots)
            score = 0.35 * max(0.0, v_score) + 0.65 * s_score
            hits.append(SearchHit(record_id, score, v_score, s_score, record))
        hits.sort(key=lambda hit: (hit.score, hit.slot_similarity), reverse=True)
        return hits[:top_k]

    def save_jsonl(self, path: str | Path) -> None:
        """
        Save all records in the index to a JSONL file.

        Each record is written as a single JSON line containing the record ID, title,
        abstract, extracted slots, packed vector (base64-encoded), metadata, and encoding version.

        Parameters:
        	path (str | Path): File path where the JSONL will be written
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for record in self.records.values():
                payload = {
                    "version": ENCODING_VERSION,
                    "record_id": record.record_id,
                    "title": record.title,
                    "abstract": record.abstract,
                    "slots": record.slots.to_jsonable(),
                    "vector": base64.b64encode(pack_vector(record.vector)).decode("ascii"),
                    "metadata": record.metadata,
                }
                handle.write(json.dumps(payload, separators=(",", ":")) + "\n")

    @classmethod
    def load_jsonl(cls, path: str | Path) -> ScientificMemoryIndex:
        """
        Load scientific records from a JSONL file into a new index.

        Parameters:
        	path (str | Path): Path to the JSONL file containing serialized records.

        Returns:
        	ScientificMemoryIndex: An index containing the loaded records, or an empty index if the file does not exist.
        """
        index = cls()
        target = Path(path)
        if not target.exists():
            return index
        with target.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                index.add(
                    ScientificRecord(
                        record_id=payload["record_id"],
                        title=payload.get("title", ""),
                        abstract=payload.get("abstract", ""),
                        slots=ScientificSlots.from_jsonable(payload.get("slots", {})),
                        vector=unpack_vector(base64.b64decode(payload["vector"])),
                        metadata=payload.get("metadata", {}),
                    )
                )
        return index


def split_title_abstract(content: str) -> tuple[str, str]:
    """
    Extracts title and abstract components from a content string.

    Returns:
    	(str, str): Title and abstract strings, respectively.
    """
    text = content.strip()
    if "TITLE:" in text and "ABSTRACT:" in text:
        title_part, abstract_part = text.split("ABSTRACT:", 1)
        return title_part.replace("TITLE:", "").strip(" |"), abstract_part.split("| PUBLISHED:", 1)[0].strip()
    if "|" in text:
        title, abstract = text.split("|", 1)
        return title.strip(), abstract.strip()
    return text[:160], text


def record_from_content(
    record_id: str,
    content: str,
    blob: bytes | None = None,
    encoder: ScientificPaperEncoder | None = None,
) -> ScientificRecord:
    """
    Constructs a scientific record from content text, optionally using a pre-computed vector.

    Parameters:
        blob (bytes | None): Pre-computed packed vector; if correctly sized, replaces the encoded vector

    Returns:
        The constructed record with extracted slots and encoded vector.
    """
    codec = encoder or ScientificPaperEncoder()
    title, abstract = split_title_abstract(content)
    record = codec.encode_document(record_id, title, abstract)
    if blob and len(blob) == (DIMENSIONS + 7) // 8:
        record.vector = unpack_vector(blob)
    return record


def index_from_rows(
    rows: Iterable[tuple[str, str, bytes | None]],
    encoder: ScientificPaperEncoder | None = None,
) -> ScientificMemoryIndex:
    """
    Constructs a memory index from record tuples, filtering invalid entries.

    Iterates through rows of (record_id, content, blob) tuples, skipping entries with
    missing or empty record_id, a record_id of "ARXIV_CRAWLER_STATE", or missing/empty
    content. For valid rows, encodes each record and adds it to the index.

    Parameters:
    	rows: An iterable of tuples containing (record_id, content, blob), where
    		record_id is the document identifier, content is the title and abstract text,
    		and blob is optional packed vector data.
    	encoder: An optional ScientificPaperEncoder instance. If not provided, a new
    		encoder is created.

    Returns:
    	A populated ScientificMemoryIndex containing the valid records.
    """
    codec = encoder or ScientificPaperEncoder()
    index = ScientificMemoryIndex(codec)
    for record_id, content, blob in rows:
        if not record_id or record_id == "ARXIV_CRAWLER_STATE" or not content:
            continue
        index.add(record_from_content(record_id, content, blob, codec))
    return index


def detect_contradictions(records: Iterable[ScientificRecord], threshold: float = 0.55) -> list[Contradiction]:
    """
    Identify pairs of records that discuss similar topics with opposite polarities.

    Records are considered contradictory if they express opposing polarities (one positive, one negative) and their topic similarity meets or exceeds the specified threshold.

    Parameters:
    	threshold (float): Minimum similarity score (range 0.0 to 1.0) required to classify records as contradictory.

    Returns:
    	list[Contradiction]: Detected contradictions, each containing the two record IDs, their topic similarity, and opposing polarities.
    """
    items = list(records)
    contradictions: list[Contradiction] = []
    encoder = ScientificPaperEncoder()
    for index, left in enumerate(items):
        left_polarity = left.slots.get("POLARITY")
        if not left_polarity or left_polarity[0] not in {"positive", "negative"}:
            continue
        ignored = ("POLARITY", "RELATION", "EVIDENCE", "YEAR")
        left_topic_slots = left.slots.without(*ignored)
        left_topic = encoder.encode_slots(left_topic_slots)
        for right in items[index + 1:]:
            right_polarity = right.slots.get("POLARITY")
            if not right_polarity or right_polarity[0] not in {"positive", "negative"}:
                continue
            if left_polarity[0] == right_polarity[0]:
                continue
            right_topic_slots = right.slots.without(*ignored)
            right_topic = encoder.encode_slots(right_topic_slots)
            similarity = 0.5 * max(0.0, vector_similarity(left_topic, right_topic))
            similarity += 0.5 * slot_similarity(
                left_topic_slots,
                right_topic_slots,
            )
            if similarity >= threshold:
                contradictions.append(
                    Contradiction(
                        left.record_id,
                        right.record_id,
                        similarity,
                        left_polarity[0],
                        right_polarity[0],
                    )
                )
    return contradictions
