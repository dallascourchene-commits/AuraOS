#!/usr/bin/env python3
"""Verify and replay the architecture-neutral HDV1024 Hamming corpus.

The corpus owns logical 16x64-bit word consequences only. It deliberately does
not define byte serialization, architectural register order, compiler ABI,
hardware encoding, timing, performance, or semantic K27 authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

SCHEMA = "K27HammingConsequenceVectorV1"
EXPECTED_DIGEST = "30014dc3d6e16454a41c91599460dddb2b72aa947fbf297f7b6985e543884b85"
DEFAULT_CORPUS = Path("tests/fixtures/k27_hdv1024_consequence_vectors_v1.json")
HEX64 = re.compile(r"^[0-9a-f]{16}$")
EXPECTED_NAMES = (
    "ZERO_ZERO",
    "ZERO_ONES",
    "WORD0_LSB_ONE",
    "WORD15_MSB_ONE",
    "ALTERNATING_COMPLEMENTS",
    "PR613_FOUR_BIT_WITNESS",
    "PR623_REFERENCE_PAIR",
    "SHA256_FIXED_PAIR",
)
EXPECTED_DISTANCES = (0, 1024, 1, 1, 1024, 4, 472, 510)


class CorpusError(ValueError):
    pass


def canonical_bytes(corpus: dict[str, Any]) -> bytes:
    return json.dumps(corpus, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def corpus_digest(corpus: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(corpus)).hexdigest()


def _decode_words(words: Any, field: str) -> tuple[int, ...]:
    if not isinstance(words, list) or len(words) != 16:
        raise CorpusError(f"{field}_REQUIRES_16_WORDS")
    decoded: list[int] = []
    for value in words:
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            raise CorpusError(f"{field}_WORD_NOT_LOWERCASE_HEX64")
        decoded.append(int(value, 16))
    return tuple(decoded)


def hamming_words(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    if len(a) != 16 or len(b) != 16:
        raise CorpusError("HAMMING_REQUIRES_16_WORDS")
    return sum((x ^ y).bit_count() for x, y in zip(a, b))


def validate_corpus(corpus: Any) -> dict[str, Any]:
    if not isinstance(corpus, dict):
        raise CorpusError("CORPUS_MUST_BE_OBJECT")
    if set(corpus) != {"schema", "word_count", "word_bits", "distance_range", "vectors"}:
        raise CorpusError("CORPUS_SCHEMA_KEYS_MISMATCH")
    if corpus["schema"] != SCHEMA:
        raise CorpusError("SCHEMA_MISMATCH")
    if corpus["word_count"] != 16 or corpus["word_bits"] != 64:
        raise CorpusError("WIDTH_MISMATCH")
    if corpus["distance_range"] != [0, 1024]:
        raise CorpusError("DISTANCE_RANGE_MISMATCH")
    vectors = corpus["vectors"]
    if not isinstance(vectors, list) or len(vectors) != 8:
        raise CorpusError("VECTOR_COUNT_MISMATCH")

    names: list[str] = []
    observed: list[int] = []
    for vector in vectors:
        if not isinstance(vector, dict) or set(vector) != {"name", "a", "b", "expected_hamming"}:
            raise CorpusError("VECTOR_SCHEMA_MISMATCH")
        name = vector["name"]
        if not isinstance(name, str):
            raise CorpusError("VECTOR_NAME_INVALID")
        a = _decode_words(vector["a"], f"{name}_A")
        b = _decode_words(vector["b"], f"{name}_B")
        expected = vector["expected_hamming"]
        if type(expected) is not int or not 0 <= expected <= 1024:
            raise CorpusError("EXPECTED_HAMMING_OUT_OF_RANGE")
        actual = hamming_words(a, b)
        if actual != expected:
            raise CorpusError(f"{name}_EXPECTED_{expected}_ACTUAL_{actual}")
        names.append(name)
        observed.append(actual)

    if tuple(names) != EXPECTED_NAMES:
        raise CorpusError("VECTOR_ORDER_OR_IDENTITY_MISMATCH")
    if tuple(observed) != EXPECTED_DISTANCES:
        raise CorpusError("FROZEN_DISTANCE_SEQUENCE_MISMATCH")
    digest = corpus_digest(corpus)
    if digest != EXPECTED_DIGEST:
        raise CorpusError(f"CORPUS_DIGEST_MISMATCH:{digest}")

    return {
        "schema": SCHEMA,
        "corpus_sha256": digest,
        "vector_count": len(vectors),
        "expected_distances": observed,
        "logical_word_indexing_bound": True,
        "byte_endianness_bound": False,
        "architectural_register_mapping_bound": False,
        "compiler_abi_bound": False,
        "riscv_simulator_semantics_proven": False,
        "rtl_implementation_proven": False,
        "hardware_performance_proven": False,
        "semantic_k27_authority": False,
        "native_transformer_kv_accessed": False,
    }


def replay_with_pr608_adapter(corpus: dict[str, Any], executable: Path) -> list[dict[str, Any]]:
    if not executable.is_file():
        raise CorpusError("PR608_ADAPTER_NOT_FOUND")
    results: list[dict[str, Any]] = []
    for vector in corpus["vectors"]:
        args = [str(executable), *vector["a"], *vector["b"]]
        completed = subprocess.run(args, check=True, text=True, capture_output=True)
        parts = completed.stdout.strip().split()
        if len(parts) != 3:
            raise CorpusError(f"{vector['name']}_ADAPTER_OUTPUT_INVALID")
        scalar = int(parts[0])
        selected = int(parts[1])
        backend = parts[2]
        expected = vector["expected_hamming"]
        if scalar != expected or selected != expected:
            raise CorpusError(
                f"{vector['name']}_PR608_REPLAY_MISMATCH:expected={expected},scalar={scalar},selected={selected}"
            )
        results.append({"name": vector["name"], "scalar": scalar, "selected": selected, "backend": backend})
    return results


def load_corpus(path: Path = DEFAULT_CORPUS) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--pr608-adapter", type=Path)
    args = parser.parse_args()

    corpus = load_corpus(args.corpus)
    receipt = validate_corpus(corpus)
    if args.pr608_adapter is not None:
        replay = replay_with_pr608_adapter(corpus, args.pr608_adapter)
        receipt["pr608_actual_implementation_replayed"] = True
        receipt["pr608_replay_backends"] = sorted({row["backend"] for row in replay})
        receipt["pr608_replay_distances"] = [row["scalar"] for row in replay]
    else:
        receipt["pr608_actual_implementation_replayed"] = False
    print(json.dumps(receipt, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
