from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import hashlib
import json
import mmap
import os
import random
import statistics
import struct
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Iterable, Mapping, Sequence

NATIVE_K27_RADIX = 3
SID_TRITHASH_TRITS = 27
SID_TRITHASH_MODULUS = 3 ** SID_TRITHASH_TRITS
SID_TRITHASH_PREFIX_TRITS = 9
SID_TRITHASH_PREFIX_MASK = (1 << (SID_TRITHASH_PREFIX_TRITS * 2)) - 1
PLACEMENT_CONTIGUOUS_CSR_V1 = "CONTIGUOUS_CSR_V1"
PLACEMENT_SID_TRITHASH27_PREFIX9_V0 = "SID_TRITHASH27_PREFIX9_V0"
PLACEMENT_SCHEME_IDS = {
    PLACEMENT_CONTIGUOUS_CSR_V1: 0,
    PLACEMENT_SID_TRITHASH27_PREFIX9_V0: 1,
}
PLACEMENT_SCHEME_NAMES = {value: key for key, value in PLACEMENT_SCHEME_IDS.items()}
BLOCK_SIZE = 4096
MAX_CSR_ROWS = 256
MAX_CSR_EDGES = 384
NODE_SIZE = 64
NODE_STRUCT = struct.Struct("<QQIIIIIHH24x")
BLOCK_HEADER_STRUCT = struct.Struct("<QQHHI")
ROW_OFFSETS_STRUCT = struct.Struct("<" + "H" * MAX_CSR_ROWS)
COL_TARGETS_STRUCT = struct.Struct("<" + "Q" * MAX_CSR_EDGES)
BLOCK_PADDING = BLOCK_SIZE - (
    BLOCK_HEADER_STRUCT.size + ROW_OFFSETS_STRUCT.size + COL_TARGETS_STRUCT.size + MAX_CSR_EDGES
)
assert NODE_STRUCT.size == NODE_SIZE
assert BLOCK_HEADER_STRUCT.size == 24
assert BLOCK_PADDING == 104


class ASTGEFormatError(ValueError):
    pass


@dataclass(frozen=True)
class NativeK27Cell:
    x: int
    y: int
    z: int

    def __post_init__(self) -> None:
        if any(value not in (0, 1, 2) for value in (self.x, self.y, self.z)):
            raise ValueError("NATIVE_K27_CELL_INVALID")

    @property
    def ordinal(self) -> int:
        return self.x * 9 + self.y * 3 + self.z


@dataclass(frozen=True)
class SIDTriHash27:
    packed: int

    @classmethod
    def from_sid_and_domain(cls, sid: str, domain_axis: int) -> "SIDTriHash27":
        if not isinstance(sid, str) or not sid:
            raise ValueError("SID_REQUIRED")
        if domain_axis not in (0, 1, 2):
            raise ValueError("DOMAIN_AXIS_INVALID")
        digest = hashlib.sha256(sid.encode("utf-8") + bytes([domain_axis])).digest()
        value = int.from_bytes(digest[:16], "big") % SID_TRITHASH_MODULUS
        packed = 0
        for i in range(SID_TRITHASH_TRITS):
            trit = value % 3
            packed |= trit << (i * 2)
            value //= 3
        return cls(packed)

    def trit(self, index: int) -> int:
        if not 0 <= index < SID_TRITHASH_TRITS:
            raise IndexError(index)
        value = (self.packed >> (index * 2)) & 0b11
        if value > 2:
            raise ASTGEFormatError("INVALID_PACKED_TRIT")
        return value

    @property
    def prefix9(self) -> int:
        return self.packed & SID_TRITHASH_PREFIX_MASK


@dataclass(frozen=True)
class NodeRecord:
    node_id: int
    placement_packed: int
    type_id: int
    file_id: int
    byte_start: int
    byte_end: int
    edge_block_pbn: int
    edge_row_idx: int
    out_degree: int

    def pack(self) -> bytes:
        return NODE_STRUCT.pack(
            self.node_id,
            self.placement_packed,
            self.type_id,
            self.file_id,
            self.byte_start,
            self.byte_end,
            self.edge_block_pbn,
            self.edge_row_idx,
            self.out_degree,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "NodeRecord":
        if len(data) != NODE_SIZE:
            raise ASTGEFormatError("NODE_RECORD_SIZE_MISMATCH")
        return cls(*NODE_STRUCT.unpack(data))


@dataclass(frozen=True)
class GraphBuildReceipt:
    schema: str
    placement_scheme: str
    node_count: int
    edge_count: int
    block_count: int
    placement_group_count: int
    nodes_bytes: int
    edges_bytes: int
    semantic_digest: str


@dataclass(frozen=True)
class HydratedCone:
    root_id: int
    node_ids: tuple[int, ...]
    edge_traversals: int
    unique_blocks_accessed: int


@dataclass(frozen=True)
class BenchmarkReceipt:
    schema: str
    graph_nodes: int
    graph_edges: int
    query_count: int
    max_depth: int
    warmup_rounds: int
    measured_rounds: int
    heap_median_ns: int
    contiguous_mmap_median_ns: int
    trithash_mmap_median_ns: int
    heap_ns_per_query: float
    contiguous_mmap_ns_per_query: float
    trithash_mmap_ns_per_query: float
    ratio_contiguous_mmap_over_heap: float
    ratio_trithash_mmap_over_heap: float
    contiguous_blocks: int
    trithash_blocks: int
    contiguous_edges_bytes: int
    trithash_edges_bytes: int
    trithash_page_amplification_over_contiguous: float
    same_graph: bool
    cone_equivalence_verified: bool
    os_page_cache_coldness_proven: bool
    physical_nvme_reads_proven: bool
    performance_superiority_proven: bool


def _semantic_digest(adjacency: Mapping[int, Sequence[int]]) -> str:
    payload = [[node, list(adjacency[node])] for node in sorted(adjacency)]
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"AURA_ASTGE_REFERENCE_GRAPH_V2\0" + raw).hexdigest()


def build_balanced_tree(depth: int, branching: int) -> dict[int, tuple[int, ...]]:
    if depth < 0 or branching < 0:
        raise ValueError("GRAPH_DIMENSION_INVALID")
    adjacency: dict[int, tuple[int, ...]] = {}
    next_id = 1
    queue = deque([(0, 0)])
    while queue:
        node, level = queue.popleft()
        children: list[int] = []
        if level < depth:
            for _ in range(branching):
                child = next_id
                next_id += 1
                children.append(child)
                queue.append((child, level + 1))
        adjacency[node] = tuple(children)
    return adjacency


def _validate_graph(adjacency: Mapping[int, Sequence[int]]) -> list[int]:
    node_ids = sorted(adjacency)
    if node_ids != list(range(len(node_ids))):
        raise ValueError("NODE_IDS_MUST_BE_DENSE_FROM_ZERO")
    for targets in adjacency.values():
        if len(targets) > MAX_CSR_EDGES:
            raise ValueError("NODE_OUT_DEGREE_EXCEEDS_BLOCK_CAPACITY")
        for target in targets:
            if target not in adjacency:
                raise ValueError("EDGE_TARGET_UNKNOWN")
    return node_ids


def serialize_graph(
    nodes_path: os.PathLike[str] | str,
    edges_path: os.PathLike[str] | str,
    adjacency: Mapping[int, Sequence[int]],
    *,
    domain_axis: int = 0,
    placement_scheme: str = PLACEMENT_CONTIGUOUS_CSR_V1,
) -> GraphBuildReceipt:
    node_ids = _validate_graph(adjacency)
    if placement_scheme not in PLACEMENT_SCHEME_IDS:
        raise ValueError("PLACEMENT_SCHEME_UNSUPPORTED")
    scheme_id = PLACEMENT_SCHEME_IDS[placement_scheme]
    placement_keys = [SIDTriHash27.from_sid_and_domain(f"node:{node_id}", domain_axis) for node_id in node_ids]
    groups: dict[int, list[int]] = defaultdict(list)
    if placement_scheme == PLACEMENT_CONTIGUOUS_CSR_V1:
        groups[0].extend(node_ids)
    else:
        for node_id, key in enumerate(placement_keys):
            groups[key.prefix9].append(node_id)
    records: list[NodeRecord | None] = [None] * len(node_ids)
    blocks: list[bytes] = []
    edge_count_total = 0

    for placement_group in sorted(groups):
        current_rows: list[tuple[int, tuple[int, ...]]] = []
        current_edge_count = 0

        def flush() -> None:
            nonlocal current_rows, current_edge_count, edge_count_total
            if not current_rows:
                return
            pbn = len(blocks)
            row_offsets = [0] * MAX_CSR_ROWS
            col_targets = [0] * MAX_CSR_EDGES
            edge_kinds = bytearray(MAX_CSR_EDGES)
            cursor = 0
            for row_idx, (node_id, targets) in enumerate(current_rows):
                row_offsets[row_idx] = cursor
                for target in targets:
                    col_targets[cursor] = target
                    edge_kinds[cursor] = 0
                    cursor += 1
                records[node_id] = NodeRecord(
                    node_id=node_id,
                    placement_packed=placement_keys[node_id].packed,
                    type_id=0,
                    file_id=0,
                    byte_start=0,
                    byte_end=0,
                    edge_block_pbn=pbn,
                    edge_row_idx=row_idx,
                    out_degree=len(targets),
                )
            buf = bytearray(BLOCK_SIZE)
            offset = 0
            header = BLOCK_HEADER_STRUCT.pack(pbn, placement_group, len(current_rows), cursor, scheme_id)
            buf[offset : offset + len(header)] = header
            offset += BLOCK_HEADER_STRUCT.size
            rows_bytes = ROW_OFFSETS_STRUCT.pack(*row_offsets)
            buf[offset : offset + len(rows_bytes)] = rows_bytes
            offset += ROW_OFFSETS_STRUCT.size
            targets_bytes = COL_TARGETS_STRUCT.pack(*col_targets)
            buf[offset : offset + len(targets_bytes)] = targets_bytes
            offset += COL_TARGETS_STRUCT.size
            buf[offset : offset + MAX_CSR_EDGES] = edge_kinds
            offset += MAX_CSR_EDGES
            assert offset + BLOCK_PADDING == BLOCK_SIZE
            blocks.append(bytes(buf))
            edge_count_total += cursor
            current_rows = []
            current_edge_count = 0

        for node_id in groups[placement_group]:
            targets = tuple(adjacency[node_id])
            if current_rows and (
                len(current_rows) >= MAX_CSR_ROWS
                or current_edge_count + len(targets) > MAX_CSR_EDGES
            ):
                flush()
            current_rows.append((node_id, targets))
            current_edge_count += len(targets)
        flush()

    if any(record is None for record in records):
        raise AssertionError("UNASSIGNED_NODE_RECORD")
    nodes_blob = b"".join(record.pack() for record in records if record is not None)
    edges_blob = b"".join(blocks)
    Path(nodes_path).write_bytes(nodes_blob)
    Path(edges_path).write_bytes(edges_blob)
    return GraphBuildReceipt(
        schema="AuraASTGEGraphBuildReceiptV2",
        placement_scheme=placement_scheme,
        node_count=len(records),
        edge_count=edge_count_total,
        block_count=len(blocks),
        placement_group_count=len(groups),
        nodes_bytes=len(nodes_blob),
        edges_bytes=len(edges_blob),
        semantic_digest=_semantic_digest(adjacency),
    )


class MmapGraphReader:
    def __init__(self, nodes_path: os.PathLike[str] | str, edges_path: os.PathLike[str] | str):
        self._nodes_file = open(nodes_path, "rb")
        self._edges_file = open(edges_path, "rb")
        nodes_size = os.fstat(self._nodes_file.fileno()).st_size
        edges_size = os.fstat(self._edges_file.fileno()).st_size
        if nodes_size == 0 or nodes_size % NODE_SIZE:
            self.close()
            raise ASTGEFormatError("NODE_TABLE_SIZE_INVALID")
        if edges_size == 0 or edges_size % BLOCK_SIZE:
            self.close()
            raise ASTGEFormatError("EDGE_TABLE_SIZE_INVALID")
        self.node_count = nodes_size // NODE_SIZE
        self.block_count = edges_size // BLOCK_SIZE
        self._nodes_mmap = mmap.mmap(self._nodes_file.fileno(), 0, access=mmap.ACCESS_READ)
        self._edges_mmap = mmap.mmap(self._edges_file.fileno(), 0, access=mmap.ACCESS_READ)

    def close(self) -> None:
        for attr in ("_nodes_mmap", "_edges_mmap"):
            value = getattr(self, attr, None)
            if value is not None:
                value.close()
                setattr(self, attr, None)
        for attr in ("_nodes_file", "_edges_file"):
            value = getattr(self, attr, None)
            if value is not None:
                value.close()
                setattr(self, attr, None)

    def __enter__(self) -> "MmapGraphReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def get_node(self, node_id: int) -> NodeRecord:
        if not 0 <= node_id < self.node_count:
            raise ASTGEFormatError("NODE_ID_OUT_OF_RANGE")
        start = node_id * NODE_SIZE
        record = NodeRecord.unpack(self._nodes_mmap[start : start + NODE_SIZE])
        if record.node_id != node_id:
            raise ASTGEFormatError("NODE_TABLE_IDENTITY_MISMATCH")
        if record.edge_block_pbn >= self.block_count:
            raise ASTGEFormatError("NODE_EDGE_PBN_OUT_OF_RANGE")
        return record

    def _block_row_targets(self, record: NodeRecord) -> tuple[int, tuple[int, ...]]:
        start = record.edge_block_pbn * BLOCK_SIZE
        block = self._edges_mmap[start : start + BLOCK_SIZE]
        pbn, placement_group, entry_count, edge_count, scheme_id = BLOCK_HEADER_STRUCT.unpack_from(block, 0)
        if scheme_id not in PLACEMENT_SCHEME_NAMES:
            raise ASTGEFormatError("BLOCK_PLACEMENT_SCHEME_INVALID")
        if pbn != record.edge_block_pbn:
            raise ASTGEFormatError("BLOCK_PBN_IDENTITY_MISMATCH")
        if entry_count > MAX_CSR_ROWS or edge_count > MAX_CSR_EDGES:
            raise ASTGEFormatError("BLOCK_COUNT_OUT_OF_RANGE")
        if record.edge_row_idx >= entry_count:
            raise ASTGEFormatError("NODE_ROW_OUT_OF_RANGE")
        if scheme_id == PLACEMENT_SCHEME_IDS[PLACEMENT_SID_TRITHASH27_PREFIX9_V0]:
            if (record.placement_packed & SID_TRITHASH_PREFIX_MASK) != placement_group:
                raise ASTGEFormatError("NODE_BLOCK_TRITHASH_PREFIX_MISMATCH")
        elif placement_group != 0:
            raise ASTGEFormatError("CONTIGUOUS_BLOCK_GROUP_NONZERO")
        row_offsets_offset = BLOCK_HEADER_STRUCT.size
        row_start = struct.unpack_from("<H", block, row_offsets_offset + 2 * record.edge_row_idx)[0]
        row_end = row_start + record.out_degree
        if row_start > edge_count or row_end > edge_count or row_end > MAX_CSR_EDGES:
            raise ASTGEFormatError("NODE_EDGE_SLICE_OUT_OF_RANGE")
        targets_offset = BLOCK_HEADER_STRUCT.size + ROW_OFFSETS_STRUCT.size
        targets = tuple(
            struct.unpack_from("<Q", block, targets_offset + 8 * i)[0]
            for i in range(row_start, row_end)
        )
        if any(target >= self.node_count for target in targets):
            raise ASTGEFormatError("EDGE_TARGET_OUT_OF_RANGE")
        return record.edge_block_pbn, targets

    def query_affected_cone(self, root_node_id: int, max_depth: int) -> HydratedCone:
        if max_depth < 0:
            raise ValueError("MAX_DEPTH_INVALID")
        self.get_node(root_node_id)
        visited = {root_node_id}
        queue = deque([(root_node_id, 0)])
        ordered: list[int] = []
        accessed_blocks: set[int] = set()
        edge_traversals = 0
        while queue:
            current, depth = queue.popleft()
            ordered.append(current)
            if depth >= max_depth:
                continue
            record = self.get_node(current)
            pbn, targets = self._block_row_targets(record)
            accessed_blocks.add(pbn)
            for target in targets:
                edge_traversals += 1
                if target not in visited:
                    visited.add(target)
                    queue.append((target, depth + 1))
        return HydratedCone(
            root_id=root_node_id,
            node_ids=tuple(ordered),
            edge_traversals=edge_traversals,
            unique_blocks_accessed=len(accessed_blocks),
        )


def query_heap(adjacency: Mapping[int, Sequence[int]], root_node_id: int, max_depth: int) -> tuple[int, ...]:
    if root_node_id not in adjacency:
        raise KeyError(root_node_id)
    visited = {root_node_id}
    queue = deque([(root_node_id, 0)])
    ordered: list[int] = []
    while queue:
        current, depth = queue.popleft()
        ordered.append(current)
        if depth >= max_depth:
            continue
        for target in adjacency[current]:
            if target not in visited:
                visited.add(target)
                queue.append((target, depth + 1))
    return tuple(ordered)


def verify_equivalence(
    reader: MmapGraphReader,
    adjacency: Mapping[int, Sequence[int]],
    roots: Iterable[int],
    max_depth: int,
) -> None:
    for root in roots:
        expected = query_heap(adjacency, root, max_depth)
        observed = reader.query_affected_cone(root, max_depth).node_ids
        if observed != expected:
            raise AssertionError(f"CONE_EQUIVALENCE_FAILED root={root}")


def _time_queries(fn, roots: Sequence[int], rounds: int) -> list[int]:
    out: list[int] = []
    for _ in range(rounds):
        start = time.perf_counter_ns()
        for root in roots:
            fn(root)
        out.append(time.perf_counter_ns() - start)
    return out


def benchmark_same_graph(
    *,
    depth: int = 7,
    branching: int = 3,
    query_count: int = 2000,
    max_depth: int = 3,
    warmup_rounds: int = 1,
    measured_rounds: int = 5,
    seed: int = 27,
) -> BenchmarkReceipt:
    adjacency = build_balanced_tree(depth, branching)
    edge_count = sum(len(v) for v in adjacency.values())
    rng = random.Random(seed)
    roots = [rng.randrange(len(adjacency)) for _ in range(query_count)]
    with tempfile.TemporaryDirectory(prefix="aura-astge-") as td:
        contig_nodes = os.path.join(td, "contiguous.nodes")
        contig_edges = os.path.join(td, "contiguous.edges")
        hash_nodes = os.path.join(td, "trithash.nodes")
        hash_edges = os.path.join(td, "trithash.edges")
        contig_build = serialize_graph(
            contig_nodes, contig_edges, adjacency, placement_scheme=PLACEMENT_CONTIGUOUS_CSR_V1
        )
        hash_build = serialize_graph(
            hash_nodes,
            hash_edges,
            adjacency,
            placement_scheme=PLACEMENT_SID_TRITHASH27_PREFIX9_V0,
        )
        for build in (contig_build, hash_build):
            if build.node_count != len(adjacency) or build.edge_count != edge_count:
                raise AssertionError("BUILD_RECEIPT_GRAPH_MISMATCH")
        if contig_build.semantic_digest != hash_build.semantic_digest:
            raise AssertionError("PLACEMENT_CHANGED_SEMANTIC_GRAPH")
        with MmapGraphReader(contig_nodes, contig_edges) as contig_reader, MmapGraphReader(
            hash_nodes, hash_edges
        ) as hash_reader:
            proof_roots = roots[: min(256, len(roots))]
            verify_equivalence(contig_reader, adjacency, proof_roots, max_depth)
            verify_equivalence(hash_reader, adjacency, proof_roots, max_depth)
            for root in proof_roots:
                if (
                    contig_reader.query_affected_cone(root, max_depth).node_ids
                    != hash_reader.query_affected_cone(root, max_depth).node_ids
                ):
                    raise AssertionError("PLACEMENT_CONE_EQUIVALENCE_FAILED")
            for _ in range(warmup_rounds):
                for root in roots:
                    query_heap(adjacency, root, max_depth)
                for root in roots:
                    contig_reader.query_affected_cone(root, max_depth)
                for root in roots:
                    hash_reader.query_affected_cone(root, max_depth)
            heap_times = _time_queries(lambda root: query_heap(adjacency, root, max_depth), roots, measured_rounds)
            contig_times = _time_queries(
                lambda root: contig_reader.query_affected_cone(root, max_depth), roots, measured_rounds
            )
            hash_times = _time_queries(
                lambda root: hash_reader.query_affected_cone(root, max_depth), roots, measured_rounds
            )
    heap_med = int(statistics.median(heap_times))
    contig_med = int(statistics.median(contig_times))
    hash_med = int(statistics.median(hash_times))
    return BenchmarkReceipt(
        schema="AuraASTGESameGraphBenchmarkV2",
        graph_nodes=len(adjacency),
        graph_edges=edge_count,
        query_count=query_count,
        max_depth=max_depth,
        warmup_rounds=warmup_rounds,
        measured_rounds=measured_rounds,
        heap_median_ns=heap_med,
        contiguous_mmap_median_ns=contig_med,
        trithash_mmap_median_ns=hash_med,
        heap_ns_per_query=heap_med / query_count,
        contiguous_mmap_ns_per_query=contig_med / query_count,
        trithash_mmap_ns_per_query=hash_med / query_count,
        ratio_contiguous_mmap_over_heap=contig_med / heap_med,
        ratio_trithash_mmap_over_heap=hash_med / heap_med,
        contiguous_blocks=contig_build.block_count,
        trithash_blocks=hash_build.block_count,
        contiguous_edges_bytes=contig_build.edges_bytes,
        trithash_edges_bytes=hash_build.edges_bytes,
        trithash_page_amplification_over_contiguous=hash_build.block_count / contig_build.block_count,
        same_graph=True,
        cone_equivalence_verified=True,
        os_page_cache_coldness_proven=False,
        physical_nvme_reads_proven=False,
        performance_superiority_proven=False,
    )


def _main() -> int:
    parser = argparse.ArgumentParser(description="Aura ASTGE deterministic reference oracle")
    parser.add_argument("command", choices=("benchmark", "self-test"))
    parser.add_argument("--queries", type=int, default=1000)
    args = parser.parse_args()
    if args.command == "self-test":
        adjacency = build_balanced_tree(5, 3)
        receipts = []
        with tempfile.TemporaryDirectory(prefix="aura-astge-selftest-") as td:
            for scheme in (PLACEMENT_CONTIGUOUS_CSR_V1, PLACEMENT_SID_TRITHASH27_PREFIX9_V0):
                nodes = os.path.join(td, scheme + ".nodes")
                edges = os.path.join(td, scheme + ".edges")
                receipt = serialize_graph(nodes, edges, adjacency, placement_scheme=scheme)
                with MmapGraphReader(nodes, edges) as reader:
                    verify_equivalence(reader, adjacency, range(len(adjacency)), 3)
                receipts.append(asdict(receipt))
        print(json.dumps(receipts, sort_keys=True))
        return 0
    print(json.dumps(asdict(benchmark_same_graph(query_count=args.queries)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
