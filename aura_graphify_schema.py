"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f1-[Q-SYS:GRAPHIFY_SCHEMA]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: DEBWEWIN (Truth / Typed Graph Authority)
DEPENDENCIES: dataclasses, hashlib, json, pathlib, typing, enum
FUNCTIONS: GraphifyNode, GraphifyEdge, GraphifyPacket, GraphifyValidator, node_id_for, edge_id_for, validate_packet, packet_to_json, packet_from_json
SYNOPSIS: Typed graph schema, export, and validation layer for the Aura Graphify bridge.
Defines typed nodes and the 17 canonical edge types. Every node and edge carries a
``source_ref`` that must point to a real source record (sidecar, CODEMAP, QDKT DB,
savings DB, fractal ledger, verifier report, or file). The validator rejects any
graph packet that claims truth without a resolvable source record.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any

GRAPHIFY_SCHEMA_VERSION = "AURA_GRAPHIFY_SCHEMA_V1"


# ---------------------------------------------------------------------------
# Typed enumerations
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    FILE = "FILE"
    SYMBOL = "SYMBOL"
    ACTION_CAPSULE = "ACTION_CAPSULE"
    BOUNDARY_CONTRACT = "BOUNDARY_CONTRACT"
    ARENA_RUN = "ARENA_RUN"
    ARENA_LEASE = "ARENA_LEASE"
    QDKT_EVENT = "QDKT_EVENT"
    QDKT_CRYSTAL = "QDKT_CRYSTAL"
    DREAM_SCORE = "DREAM_SCORE"
    SIDECAR_REF = "SIDECAR_REF"
    VERIFIER_REPORT = "VERIFIER_REPORT"
    HOT_SWAP_CAPSULE = "HOT_SWAP_CAPSULE"
    PRICE = "PRICE"
    TRANSACTION = "TRANSACTION"
    PUBLIC_POST = "PUBLIC_POST"
    FRACTAL_BLOCK = "FRACTAL_BLOCK"


class EdgeType(str, Enum):
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    TESTS = "TESTS"
    VERIFIES = "VERIFIES"
    STORES_TRUTH_IN = "STORES_TRUTH_IN"
    POINTS_TO = "POINTS_TO"
    BLOCKS = "BLOCKS"
    DEPENDS_ON = "DEPENDS_ON"
    LEASES = "LEASES"
    APPROVES = "APPROVES"
    REJECTS = "REJECTS"
    LEARNED_FROM = "LEARNED_FROM"
    CRYSTALLIZED_AS = "CRYSTALLIZED_AS"
    RETRIEVED_BY = "RETRIEVED_BY"
    HELPED = "HELPED"
    AFFECTS = "AFFECTS"


# Convenience sets for fast membership checks
NODE_TYPES: frozenset[str] = frozenset(item.value for item in NodeType)
EDGE_TYPES: frozenset[str] = frozenset(item.value for item in EdgeType)

# Node types that carry authoritative truth and therefore *require* a source_ref
# that resolves to a real record (requirement 8).
TRUTH_BEARING_NODE_TYPES: frozenset[str] = frozenset({
    NodeType.PRICE.value,
    NodeType.TRANSACTION.value,
    NodeType.PUBLIC_POST.value,
    NodeType.SYMBOL.value,
    NodeType.VERIFIER_REPORT.value,
    NodeType.QDKT_EVENT.value,
    NodeType.QDKT_CRYSTAL.value,
    NodeType.DREAM_SCORE.value,
    NodeType.ACTION_CAPSULE.value,
    NodeType.BOUNDARY_CONTRACT.value,
    NodeType.FRACTAL_BLOCK.value,
    NodeType.HOT_SWAP_CAPSULE.value,
    NodeType.SIDECAR_REF.value,
})


# ---------------------------------------------------------------------------
# Source-ref kinds — describes *where* the truth lives
# ---------------------------------------------------------------------------

class SourceRefKind(str, Enum):
    CODEMAP = "codemap"                 # .aura/CODEMAP.json file card / symbol_index
    TOPOLOGY = "topology"               # Aura_Memory/live_topology_ast.json
    QDKT_DB = "qdkt_db"                 # Aura_Memory/qdkt_index.db or ~/.mempalace/aura_memory.db
    QDKT_CRYSTAL_JSON = "qdkt_crystal"  # Aura_Memory/qdkt_crystal_cache.json
    SAVINGS_DB = "savings_db"           # Aura_Memory/aura_savings.db
    PRICING_JSON = "pricing_json"       # .aura/pricing.json
    DREAM_LEDGER = "dream_ledger"       # Aura_Memory/dream_retrieval_ledger.jsonl
    FRACTAL_LEDGER = "fractal_ledger"   # aura_ledger.db
    ARENA_DIR = "arena_dir"             # Aura_Memory/arenas/*.json
    SIDECAR_FILE = "sidecar_file"       # travel_price_sidecar.py etc.
    VERIFIER_FILE = "verifier_file"     # aura_validation.py / travel_price_verifier.py
    SOURCE_FILE = "source_file"         # the actual .py / .rs file
    TEST_FILE = "test_file"             # test_*.py


SOURCE_REF_KINDS: frozenset[str] = frozenset(item.value for item in SourceRefKind)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceRef:
    """Pointer to the exact record that holds the truth for a node/edge.

    ``kind``  — which Aura subsystem stores the truth (see ``SourceRefKind``).
    ``path``  — filesystem path or DB path of the source record.
    ``key``   — primary key / row id / JSON pointer that identifies the record
                within the source (e.g. ``llm_calls:id=42``, ``codemap:files[3]``,
                ``qdkt:QDKT-abc123``).
    ``hash``  — optional content hash of the source record for tamper detection.
    """

    kind: str
    path: str
    key: str
    hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceRef:
        return cls(
            kind=str(data.get("kind", "")),
            path=str(data.get("path", "")),
            key=str(data.get("key", "")),
            hash=str(data.get("hash", "")),
        )


@dataclass
class GraphifyNode:
    id: str
    type: str
    label: str
    source_ref: SourceRef
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in NODE_TYPES:
            raise ValueError(f"unsupported node type: {self.type!r}")
        # Allow empty source_ref.kind so the validator can report a structured
        # error rather than crashing at construction time.
        if self.source_ref.kind and self.source_ref.kind not in SOURCE_REF_KINDS:
            raise ValueError(f"unsupported source_ref kind: {self.source_ref.kind!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "source_ref": self.source_ref.to_dict(),
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphifyNode:
        return cls(
            id=str(data["id"]),
            type=str(data["type"]),
            label=str(data.get("label", "")),
            source_ref=SourceRef.from_dict(data.get("source_ref", {})),
            properties=dict(data.get("properties", {})),
        )


@dataclass
class GraphifyEdge:
    id: str
    source: str
    target: str
    type: str
    source_ref: SourceRef | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in EDGE_TYPES:
            raise ValueError(f"unsupported edge type: {self.type!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "source_ref": self.source_ref.to_dict() if self.source_ref else None,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphifyEdge:
        ref_data = data.get("source_ref")
        return cls(
            id=str(data["id"]),
            source=str(data["source"]),
            target=str(data["target"]),
            type=str(data["type"]),
            source_ref=SourceRef.from_dict(ref_data) if ref_data else None,
            properties=dict(data.get("properties", {})),
        )


@dataclass
class GraphifyPacket:
    version: str
    generated_at: str
    project: dict[str, Any]
    nodes: list[GraphifyNode]
    edges: list[GraphifyEdge]
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "project": self.project,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphifyPacket:
        return cls(
            version=str(data.get("version", GRAPHIFY_SCHEMA_VERSION)),
            generated_at=str(data.get("generated_at", "")),
            project=dict(data.get("project", {})),
            nodes=[GraphifyNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[GraphifyEdge.from_dict(e) for e in data.get("edges", [])],
            meta=dict(data.get("meta", {})),
        )


# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

def _hash_id(payload: Any, *, size: int = 12) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def node_id_for(node_type: str, key: str) -> str:
    """Deterministic node ID: ``gf:<TYPE>:<hash12>``."""
    return f"gf:{node_type}:{_hash_id({'t': node_type, 'k': key})}"


def edge_id_for(source: str, target: str, edge_type: str) -> str:
    """Deterministic edge ID: ``gfe:<hash12>``."""
    return f"gfe:{_hash_id({'s': source, 't': target, 'e': edge_type})}"


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    code: str
    message: str
    node_id: str = ""
    edge_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GraphifyValidator:
    """Validates that a graph packet cannot claim unsupported truth.

    Every truth-bearing node (price, transaction, public post, code symbol,
    verifier claim, QDKT event/crystal, DREAM score, action capsule, boundary
    contract, fractal block, hot-swap capsule, sidecar ref) must carry a
    ``source_ref`` whose ``kind`` is a recognised Aura source and whose ``path``
    is non-empty.  Edges that assert a truth relationship (VERIFIES, APPROVES,
    REJECTS, LEARNED_FROM, CRYSTALLIZED_AS, RETRIEVED_BY) must also carry a
    ``source_ref``.

    The validator additionally checks referential integrity: every edge
    source/target must reference an existing node id.
    """

    def __init__(self, *, root: str | Path = ".") -> None:
        self.root = Path(root).resolve()

    # -- public API --

    def validate(self, packet: GraphifyPacket) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        node_ids: set[str] = set()

        for node in packet.nodes:
            node_ids.add(node.id)
            issues.extend(self._validate_node(node))

        for edge in packet.edges:
            issues.extend(self._validate_edge(edge, node_ids))

        issues.extend(self._validate_global(packet, node_ids))
        return issues

    def is_valid(self, packet: GraphifyPacket) -> bool:
        return not any(issue.severity == "error" for issue in self.validate(packet))

    # -- node validation --

    def _validate_node(self, node: GraphifyNode) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Type check (already enforced by dataclass, but double-check for
        # packets loaded from JSON that bypass __post_init__).
        if node.type not in NODE_TYPES:
            issues.append(ValidationIssue(
                severity="error", code="UNKNOWN_NODE_TYPE",
                message=f"node type {node.type!r} is not a recognised Graphify type",
                node_id=node.id,
            ))
            return issues

        # Truth-bearing nodes must have a source_ref with a recognised kind
        if node.type in TRUTH_BEARING_NODE_TYPES:
            ref = node.source_ref
            if not ref.kind or ref.kind not in SOURCE_REF_KINDS:
                issues.append(ValidationIssue(
                    severity="error", code="MISSING_SOURCE_REF_KIND",
                    message=(
                        f"truth-bearing node of type {node.type} must reference a "
                        f"recognised source kind; got {ref.kind!r}"
                    ),
                    node_id=node.id,
                ))
            if not ref.path:
                issues.append(ValidationIssue(
                    severity="error", code="MISSING_SOURCE_REF_PATH",
                    message=(
                        f"truth-bearing node of type {node.type} must reference a "
                        f"source path; node {node.id} has empty source_ref.path"
                    ),
                    node_id=node.id,
                ))
            if not ref.key:
                issues.append(ValidationIssue(
                    severity="error", code="MISSING_SOURCE_REF_KEY",
                    message=(
                        f"truth-bearing node of type {node.type} must reference a "
                        f"source key; node {node.id} has empty source_ref.key"
                    ),
                    node_id=node.id,
                ))

        return issues

    # -- edge validation --

    def _validate_edge(self, edge: GraphifyEdge, node_ids: set[str]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if edge.type not in EDGE_TYPES:
            issues.append(ValidationIssue(
                severity="error", code="UNKNOWN_EDGE_TYPE",
                message=f"edge type {edge.type!r} is not a recognised Graphify edge type",
                edge_id=edge.id,
            ))

        if edge.source not in node_ids:
            issues.append(ValidationIssue(
                severity="error", code="DANGLING_EDGE_SOURCE",
                message=f"edge {edge.id} source {edge.source!r} does not match any node",
                edge_id=edge.id,
            ))
        if edge.target not in node_ids:
            issues.append(ValidationIssue(
                severity="error", code="DANGLING_EDGE_TARGET",
                message=f"edge {edge.id} target {edge.target!r} does not match any node",
                edge_id=edge.id,
            ))

        # Edges that assert a truth relationship must carry a source_ref
        truth_edges: frozenset[str] = frozenset({
            EdgeType.VERIFIES.value,
            EdgeType.APPROVES.value,
            EdgeType.REJECTS.value,
            EdgeType.LEARNED_FROM.value,
            EdgeType.CRYSTALLIZED_AS.value,
            EdgeType.RETRIEVED_BY.value,
        })
        if edge.type in truth_edges and edge.source_ref is None:
            issues.append(ValidationIssue(
                severity="error", code="TRUTH_EDGE_MISSING_SOURCE_REF",
                message=(
                    f"edge of type {edge.type} asserts a truth relationship and "
                    f"must carry a source_ref; edge {edge.id} has none"
                ),
                edge_id=edge.id,
            ))

        return issues

    # -- global checks --

    def _validate_global(self, packet: GraphifyPacket, node_ids: set[str]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        # Duplicate node ids
        seen: set[str] = set()
        for node in packet.nodes:
            if node.id in seen:
                issues.append(ValidationIssue(
                    severity="error", code="DUPLICATE_NODE_ID",
                    message=f"duplicate node id {node.id!r}",
                    node_id=node.id,
                ))
            seen.add(node.id)
        # Duplicate edge ids
        seen_edges: set[str] = set()
        for edge in packet.edges:
            if edge.id in seen_edges:
                issues.append(ValidationIssue(
                    severity="error", code="DUPLICATE_EDGE_ID",
                    message=f"duplicate edge id {edge.id!r}",
                    edge_id=edge.id,
                ))
            seen_edges.add(edge.id)
        return issues


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def packet_to_json(packet: GraphifyPacket, *, indent: int = 2) -> str:
    return json.dumps(packet.to_dict(), indent=indent, sort_keys=False, default=str)


def packet_from_json(text: str) -> GraphifyPacket:
    return GraphifyPacket.from_dict(json.loads(text))


def validate_packet(packet: GraphifyPacket, *, root: str | Path = ".") -> list[ValidationIssue]:
    return GraphifyValidator(root=root).validate(packet)