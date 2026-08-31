#!/usr/bin/env python3
"""Executable falsifiers for the imported Gemini K27-ASTGE draft.

The goal is not to reject the architecture. It prevents unverified draft ABI,
indexing, or benchmark claims from replacing Aura's verified S-plane owners.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
from dataclasses import dataclass

BLOCK_SIZE = 4096
MAX_CSR_ROWS = 256
MAX_CSR_EDGES = 384


class CandidateASTNode(ctypes.Structure):
    _fields_ = [
        ('node_id', ctypes.c_uint64),
        ('coord_packed', ctypes.c_uint64),
        ('type_id', ctypes.c_uint32),
        ('file_id', ctypes.c_uint32),
        ('byte_start', ctypes.c_uint32),
        ('byte_end', ctypes.c_uint32),
        ('edge_block_pbn', ctypes.c_uint32),
        ('edge_row_idx', ctypes.c_uint16),
        ('out_degree', ctypes.c_uint16),
    ]
    _align_ = 32


class CandidateCSRBlock(ctypes.Structure):
    _fields_ = [
        ('block_pbn', ctypes.c_uint64),
        ('common_prefix', ctypes.c_uint64),
        ('entry_count', ctypes.c_uint16),
        ('edge_count', ctypes.c_uint16),
        ('row_offsets', ctypes.c_uint16 * MAX_CSR_ROWS),
        ('col_targets', ctypes.c_uint64 * MAX_CSR_EDGES),
        ('edge_kinds', ctypes.c_uint8 * MAX_CSR_EDGES),
        ('padding', ctypes.c_uint8 * 120),
    ]
    _align_ = 64


def align_up(offset: int, alignment: int) -> int:
    return ((offset + alignment - 1) // alignment) * alignment


def repr_c_candidate_sizes(csr_padding: int = 120) -> dict[str, int]:
    ast_raw_end = 40
    ast_size = align_up(ast_raw_end, 32)
    off = 0
    off += 8
    off += 8
    off += 2
    off += 2
    off += 2 * MAX_CSR_ROWS
    off = align_up(off, 8)
    col_targets_offset = off
    off += 8 * MAX_CSR_EDGES
    edge_kinds_offset = off
    off += MAX_CSR_EDGES
    padding_offset = off
    off += csr_padding
    csr_size = align_up(off, 64)
    return {
        'ast_node_size': ast_size,
        'col_targets_offset': col_targets_offset,
        'edge_kinds_offset': edge_kinds_offset,
        'padding_offset': padding_offset,
        'csr_block_size': csr_size,
    }


@dataclass
class ToyNode:
    name: str
    children: list['ToyNode']


def pasted_serializer_table(root: ToyNode) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    counter = 0

    def walk(node: ToyNode) -> int:
        nonlocal counter
        node_id = counter
        counter += 1
        child_ids = [walk(child) for child in node.children]
        records.append({'node_id': node_id, 'name': node.name, 'child_ids': child_ids})
        return node_id

    walk(root)
    return records


def index_identity_holds(records: list[dict[str, object]]) -> bool:
    return all(index == record['node_id'] for index, record in enumerate(records))


def bandwidth_requirement(dataset_bytes: int, claimed_seconds: float) -> float:
    if dataset_bytes <= 0 or claimed_seconds <= 0:
        raise ValueError('positive dataset and time required')
    return dataset_bytes / claimed_seconds


def draft_report() -> dict[str, object]:
    bad = repr_c_candidate_sizes(120)
    fixed = repr_c_candidate_sizes(104)
    root = ToyNode('root', [ToyNode('a', [ToyNode('a1', [])]), ToyNode('b', [])])
    records = pasted_serializer_table(root)
    required = bandwidth_requirement(128_000_000, 0.00125)
    upper = 51_200_000_000.0
    out: dict[str, object] = {
        'schema': 'AURA_K27_ASTGE_IMPORTED_DRAFT_FALSIFIER_V1',
        'candidate_ast_node_size_bytes': bad['ast_node_size'],
        'candidate_csr_block_size_bytes': bad['csr_block_size'],
        'candidate_claimed_csr_block_size_bytes': BLOCK_SIZE,
        'candidate_csr_layout_matches_claim': bad['csr_block_size'] == BLOCK_SIZE,
        'candidate_padding_bytes': 120,
        'same_field_order_padding_for_4096_bytes': 104,
        'fixed_csr_block_size_bytes': fixed['csr_block_size'],
        'serializer_table': records,
        'node_id_equals_table_index': index_identity_holds(records),
        'million_x_1024bit_dataset_bytes': 128_000_000,
        'claimed_scan_seconds': 0.00125,
        'required_stream_bandwidth_Bps': required,
        'dual_channel_ddr4_3200_theoretical_Bps': upper,
        'claim_exceeds_theoretical_memory_payload_rate': required > upper,
        'candidate_architecture_wholesale_admission': False,
        'retain_affected_cone_idea': True,
        'retain_segmented_adjacency_idea': True,
        'retain_optional_mmap_experiment': True,
        'retain_avx2_popcnt_as_benchmark_candidate': True,
        'replace_verified_aura_splane_abi': False,
        'semantic_k27_authority': False,
    }
    raw = json.dumps(out, sort_keys=True, separators=(',', ':')).encode()
    out['receipt_sha256'] = hashlib.sha256(raw).hexdigest()
    return out


if __name__ == '__main__':
    print(json.dumps(draft_report(), indent=2, sort_keys=True))
