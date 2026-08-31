#!/usr/bin/env python3
"""Replay PR635's canonical HDV1024 corpus through PR623's exact RISC-V software reference.

R3 owns only logical consequence agreement. PR635 remains the sole corpus owner and
PR623 remains the RISC-V functional-reference owner. This child deliberately does
not define byte serialization, architectural register mapping, compiler ABI,
simulator execution, RTL, timing, performance, or semantic K27 authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.k27_hdv1024_consequence_corpus import (
    DEFAULT_CORPUS,
    EXPECTED_DIGEST,
    EXPECTED_DISTANCES,
    EXPECTED_NAMES,
    load_corpus,
    validate_corpus,
)
from tools.k27_xhdv_riscv_candidate_falsifier import SOURCE_SHA256, hdist

VERSION = "AURA_K27_HDV1024_RISCV_CORPUS_REPLAY_V1"
PR635_EXACT_HEAD = "3ec21d937d6a77424d2ad771daea97fcfea34b1d"
PR635_EXACT_RUN = 33369071661
PR623_EXACT_HEAD = "84524fbe907e5d78db1bb257e448f34ff7fbfe02"
PR623_EXACT_RUN = 33366346680
R3_CONVERGENCE_COMMIT = "d41f204afb158e4eb793711d686fc40f27a3b1f6"
PR623_SOURCE_BLOB_SHA = "f0d32198c6b86bbd8ff34db260f3bf351ce54e07"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _words(raw: list[str], field: str) -> tuple[int, ...]:
    if not isinstance(raw, list) or len(raw) != 16:
        raise ValueError(field + "_REQUIRES_16_WORDS")
    out = tuple(int(value, 16) for value in raw)
    if any(value < 0 or value >= (1 << 64) for value in out):
        raise ValueError(field + "_WORD_OUT_OF_RANGE")
    return out


@dataclass(frozen=True)
class RiscvCorpusReplayReceipt:
    version: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    corpus_sha256: str
    pr623_candidate_source_sha256: str
    pr623_source_blob_sha: str
    vector_names: tuple[str, ...]
    expected_distances: tuple[int, ...]
    riscv_reference_distances: tuple[int, ...]
    all_logical_consequences_match: bool
    canonical_corpus_owner_retained: bool = True
    riscv_reference_owner_retained: bool = True
    byte_serialization_bound: bool = False
    byte_endianness_bound: bool = False
    architectural_register_mapping_bound: bool = False
    compiler_abi_bound: bool = False
    riscv_instruction_execution_proven: bool = False
    spike_or_qemu_execution_proven: bool = False
    hidden_h_register_abi_proven: bool = False
    os_context_state_proven: bool = False
    rtl_implementation_proven: bool = False
    synthesis_or_timing_proven: bool = False
    hardware_performance_proven: bool = False
    cross_isa_performance_equivalence_proven: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    deployment_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def replay_corpus_through_pr623(corpus_path: Path = DEFAULT_CORPUS) -> RiscvCorpusReplayReceipt:
    corpus = load_corpus(corpus_path)
    parent_receipt = validate_corpus(corpus)
    if parent_receipt["corpus_sha256"] != EXPECTED_DIGEST:
        raise ValueError("PR635_CORPUS_DIGEST_MISMATCH")
    if tuple(parent_receipt["expected_distances"]) != EXPECTED_DISTANCES:
        raise ValueError("PR635_DISTANCE_SEQUENCE_MISMATCH")

    names: list[str] = []
    observed: list[int] = []
    for vector in corpus["vectors"]:
        name = vector["name"]
        a = _words(vector["a"], name + "_A")
        b = _words(vector["b"], name + "_B")
        actual = hdist(a, b)
        expected = vector["expected_hamming"]
        if actual != expected:
            raise ValueError(f"PR623_REPLAY_MISMATCH:{name}:expected={expected}:actual={actual}")
        names.append(name)
        observed.append(actual)

    if tuple(names) != EXPECTED_NAMES:
        raise ValueError("PR635_VECTOR_IDENTITY_DRIFT")
    if tuple(observed) != EXPECTED_DISTANCES:
        raise ValueError("PR623_FROZEN_DISTANCE_SEQUENCE_MISMATCH")

    return RiscvCorpusReplayReceipt(
        version=VERSION,
        exact_parent_heads=(PR635_EXACT_HEAD, PR623_EXACT_HEAD),
        exact_parent_runs=(PR635_EXACT_RUN, PR623_EXACT_RUN),
        corpus_sha256=EXPECTED_DIGEST,
        pr623_candidate_source_sha256=SOURCE_SHA256,
        pr623_source_blob_sha=PR623_SOURCE_BLOB_SHA,
        vector_names=tuple(names),
        expected_distances=EXPECTED_DISTANCES,
        riscv_reference_distances=tuple(observed),
        all_logical_consequences_match=True,
    )


def portable_riscv_corpus_replay_receipt(corpus_path: Path = DEFAULT_CORPUS) -> dict[str, Any]:
    receipt = replay_corpus_through_pr623(corpus_path)
    payload = asdict(receipt)
    return {**payload, "receipt_digest": receipt.receipt_digest}


def main() -> None:
    print(json.dumps(portable_riscv_corpus_replay_receipt(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
