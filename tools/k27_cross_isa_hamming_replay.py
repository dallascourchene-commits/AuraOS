"""Exact-generation cross-ISA replay for the frozen K27 1024-bit Hamming corpus.

This module owns only a software consequence replay and a canonical interchange
representation. It does not establish compiler ABI, native object layout,
architectural register ordering, RTL correctness, hardware performance, or
semantic K27 authority.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

PR613_SHA = "9f6d324f0b5650544310b22e13db8d3959e9b7c1"
PR613_RUN = 33365472682
PR623_SHA = "84524fbe907e5d78db1bb257e448f34ff7fbfe02"
PR623_RUN = 33366346680
CORPUS_SCHEMA = "K27HammingConsequenceVectorV1"
CORPUS_SHA256 = "30014dc3d6e16454a41c91599460dddb2b72aa947fbf297f7b6985e543884b85"
MAP_SCHEMA = "K27HammingRepresentationMapV1"
MAP_SHA256 = "471fe69d6247d90991629386a39226d3ca57a17a25890e44a83ffe8babcf0c16"
RECEIPT_SCHEMA = "AuraK27CrossISAHammingReplayV1"
MASK64 = (1 << 64) - 1
EXPECTED_DISTANCES = (0, 1024, 1, 1, 1024, 4, 472, 510)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def representation_map() -> dict[str, Any]:
    return {
        "schema": MAP_SCHEMA,
        "word_count": 16,
        "word_bits": 64,
        "logical_bit_rule": "bit_index=64*word_index+bit_in_word; bit_in_word=0 is uint64 LSB",
        "wire_bytes": 128,
        "wire_rule": "concat word_index 0..15; each uint64 encoded unsigned little-endian exactly 8 bytes",
        "decode_rule": "word[i]=uint64_le(wire[8*i:8*i+8])",
        "native_object_layout_implied": False,
        "architectural_register_order_implied": False,
        "compiler_abi_implied": False,
        "hardware_endianness_implied": False,
    }


def _strict_words(words: Sequence[int]) -> tuple[int, ...]:
    if len(words) != 16:
        raise ValueError("exactly 16 logical uint64 words are required")
    out: list[int] = []
    for word in words:
        if type(word) is not int or not 0 <= word <= MASK64:
            raise ValueError("each logical word must be an unsigned 64-bit integer")
        out.append(word)
    return tuple(out)


def encode_wire(words: Sequence[int]) -> bytes:
    logical = _strict_words(words)
    return b"".join(word.to_bytes(8, "little", signed=False) for word in logical)


def decode_wire(wire: bytes) -> tuple[int, ...]:
    if type(wire) is not bytes or len(wire) != 128:
        raise ValueError("canonical K27 Hamming wire representation is exactly 128 bytes")
    return tuple(int.from_bytes(wire[i : i + 8], "little", signed=False) for i in range(0, 128, 8))


def logical_hamming(a: Sequence[int], b: Sequence[int]) -> int:
    aa = _strict_words(a)
    bb = _strict_words(b)
    return sum((x ^ y).bit_count() for x, y in zip(aa, bb))


def _sha_word(prefix: str, index: int) -> int:
    digest = hashlib.sha256(f"{prefix}{index}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


@dataclass(frozen=True)
class HammingVector:
    name: str
    a: tuple[int, ...]
    b: tuple[int, ...]
    expected_hamming: int

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "a": [f"{word:016x}" for word in self.a],
            "b": [f"{word:016x}" for word in self.b],
            "expected_hamming": self.expected_hamming,
        }


def vectors() -> tuple[HammingVector, ...]:
    zero = tuple(0 for _ in range(16))
    ones = tuple(MASK64 for _ in range(16))
    v3 = list(zero)
    v3[0] = 1
    v4 = list(zero)
    v4[15] = 1 << 63
    v6a = tuple((0x5555555555555555 ^ ((i * 0x0101010101010101) & MASK64)) & MASK64 for i in range(16))
    v6b = list(v6a)
    v6b[0] ^= 0xF
    v7a = tuple((0x0123456789ABCDEF + i * 0x1111111111111111) & MASK64 for i in range(16))
    v7b = tuple((0xFEDCBA9876543210 ^ ((i * 0x0101010101010101) & MASK64)) & MASK64 for i in range(16))
    v8a = tuple(_sha_word("A", i) for i in range(16))
    v8b = tuple(_sha_word("B", i) for i in range(16))
    result = (
        HammingVector("ZERO_ZERO", zero, zero, 0),
        HammingVector("ZERO_ONES", zero, ones, 1024),
        HammingVector("WORD0_LSB_ONE", zero, tuple(v3), 1),
        HammingVector("WORD15_MSB_ONE", zero, tuple(v4), 1),
        HammingVector("ALTERNATING_COMPLEMENTS", tuple(0x5555555555555555 for _ in range(16)), tuple(0xAAAAAAAAAAAAAAAA for _ in range(16)), 1024),
        HammingVector("PR613_FOUR_BIT_WITNESS", v6a, tuple(v6b), 4),
        HammingVector("PR623_REFERENCE_PAIR", v7a, v7b, 472),
        HammingVector("SHA256_FIXED_PAIR", v8a, v8b, 510),
    )
    if tuple(logical_hamming(v.a, v.b) for v in result) != EXPECTED_DISTANCES:
        raise AssertionError("frozen corpus construction drifted")
    return result


def corpus_object() -> dict[str, Any]:
    return {
        "schema": CORPUS_SCHEMA,
        "word_count": 16,
        "word_bits": 64,
        "distance_range": [0, 1024],
        "vectors": [vector.canonical_dict() for vector in vectors()],
    }


def verify_frozen_identities() -> None:
    corpus_digest = hashlib.sha256(_canonical_json(corpus_object())).hexdigest()
    if corpus_digest != CORPUS_SHA256:
        raise AssertionError(f"corpus digest drift: {corpus_digest}")
    map_digest = hashlib.sha256(_canonical_json(representation_map())).hexdigest()
    if map_digest != MAP_SHA256:
        raise AssertionError(f"representation map digest drift: {map_digest}")


def emit_tsv(path: Path) -> None:
    verify_frozen_identities()
    rows = []
    for vector in vectors():
        rows.append("\t".join((vector.name, str(vector.expected_hamming), ",".join(f"{word:016x}" for word in vector.a), ",".join(f"{word:016x}" for word in vector.b))))
    path.write_text("\n".join(rows) + "\n", encoding="ascii")


def replay_pr623() -> tuple[int, ...]:
    from tools import k27_xhdv_riscv_candidate_falsifier as xhdv
    observed = tuple(xhdv.hdist(vector.a, vector.b) for vector in vectors())
    if observed != EXPECTED_DISTANCES:
        raise AssertionError(f"PR623 replay mismatch: {observed}")
    return observed


def _parse_pr613_results(path: Path) -> tuple[tuple[int, ...], tuple[int, ...], tuple[str, ...]]:
    rows = [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 8 or any(len(row) != 4 for row in rows):
        raise ValueError("PR613 replay output must contain eight four-field TSV rows")
    expected_names = tuple(vector.name for vector in vectors())
    names = tuple(row[0] for row in rows)
    if names != expected_names:
        raise ValueError(f"PR613 vector order/name mismatch: {names}")
    scalar = tuple(int(row[1]) for row in rows)
    dispatched = tuple(int(row[2]) for row in rows)
    backends = tuple(row[3] for row in rows)
    if scalar != EXPECTED_DISTANCES:
        raise AssertionError(f"PR613 scalar replay mismatch: {scalar}")
    if dispatched != scalar:
        raise AssertionError(f"PR613 dispatched replay mismatch: {dispatched}")
    allowed = {"SCALAR_PORTABLE", "AVX2_POPCNT", "AVX512F_VPOPCNTDQ"}
    if any(backend not in allowed for backend in backends):
        raise AssertionError(f"unexpected PR613 backend: {backends}")
    return scalar, dispatched, backends


def representation_roundtrip_passes() -> bool:
    for vector in vectors():
        for words in (vector.a, vector.b):
            wire = encode_wire(words)
            if len(wire) != 128 or decode_wire(wire) != words:
                return False
    return True


def build_receipt(pr613_results_path: Path) -> dict[str, Any]:
    verify_frozen_identities()
    scalar, dispatched, backends = _parse_pr613_results(pr613_results_path)
    pr623 = replay_pr623()
    payload = {
        "schema": RECEIPT_SCHEMA,
        "parent_artifacts": [
            {"pr": 613, "sha": PR613_SHA, "dedicated_run": PR613_RUN},
            {"pr": 623, "sha": PR623_SHA, "dedicated_run": PR623_RUN},
        ],
        "corpus_schema": CORPUS_SCHEMA,
        "corpus_sha256": CORPUS_SHA256,
        "representation_map_schema": MAP_SCHEMA,
        "representation_map_sha256": MAP_SHA256,
        "expected_distances": list(EXPECTED_DISTANCES),
        "pr613_scalar_distances": list(scalar),
        "pr613_dispatched_distances": list(dispatched),
        "pr613_observed_backends": list(backends),
        "pr623_reference_distances": list(pr623),
        "pr613_scalar_pass": scalar == EXPECTED_DISTANCES,
        "pr613_dispatched_pass": dispatched == EXPECTED_DISTANCES,
        "pr623_reference_pass": pr623 == EXPECTED_DISTANCES,
        "cross_isa_consequence_agreement": scalar == dispatched == pr623 == EXPECTED_DISTANCES,
        "canonical_wire_map_self_consistent": representation_roundtrip_passes(),
        "pr613_native_wire_compatibility_proven": False,
        "pr623_native_wire_compatibility_proven": False,
        "compiler_abi_compatibility_proven": False,
        "architectural_register_compatibility_proven": False,
        "riscv_simulator_execution_proven": False,
        "rtl_implementation_proven": False,
        "hardware_performance_equality_proven": False,
        "semantic_k27_authority_proven": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
    }
    digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return {**payload, "receipt_sha256": digest}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-tsv", type=Path)
    parser.add_argument("--verify-pr623", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    verify_frozen_identities()
    if args.emit_tsv:
        emit_tsv(args.emit_tsv)
    if args.verify_pr623:
        print(json.dumps({"pr623_distances": replay_pr623()}, sort_keys=True))
    if args.receipt:
        print(json.dumps(build_receipt(args.receipt), sort_keys=True, indent=2))
    if not (args.emit_tsv or args.verify_pr623 or args.receipt):
        print(json.dumps(corpus_object(), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
