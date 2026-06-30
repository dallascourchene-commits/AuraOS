"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:SCENE_GRAPH_SCHEMA]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Scene Graph Dataclasses)
DEPENDENCIES: __future__, dataclasses, typing
FUNCTIONS: SourceRef, HardwareProfile, SymbolicPatchRule, SceneNode, SceneEdge, SceneGraphSnapshot
SYNOPSIS: Declares immutable snapshot data models and schemas for the project's topology workspace.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

AURA_SCENE_GRAPH_SNAPSHOT_V1 = "AURA_SCENE_GRAPH_SNAPSHOT_V1"
AURA_HARDWARE_PROFILE_V1 = "AURA_HARDWARE_PROFILE_V1"


@dataclass(frozen=True)
class SourceRef:
    kind: str          # codemap, graphify, verifier, qdkt, dream, sidecar, file
    path: str
    symbol: str = ""
    digest: str = ""
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass(frozen=True)
class HardwareProfile:
    operational_intensity: float       # Arithmetic FLOPs per byte transferred
    capacity_footprint_mb: float       # Physical RAM footprint threshold
    memory_bandwidth_pressure: float   # Predicted memory bandwidth stress rating (0.0 to 1.0)
    latency_sensitivity: float         # Priority mapping (0.0: batch/async, 1.0: real-time)
    kv_cache_reuse_score: float        # Predicted hit rate of the KV cache footprint (0.0 to 1.0)
    parallelism_score: float           # Concurrency safety score
    preferred_device: str              # CPU, GPU, NPU, AIE, iGPU, REMOTE_ACCELERATOR
    reason: str
    execution_status: str = "recommended"  # "recommended" | "available" | "unavailable" | "executed"
    version: str = AURA_HARDWARE_PROFILE_V1


@dataclass(frozen=True)
class SymbolicPatchRule:
    rule_id: str
    provenance_failure_id: str
    symbolic_constraint: str           # String representation of the constraint rule
    canary_tested: bool = False
    rollback_supported: bool = True


@dataclass(frozen=True)
class SceneNode:
    node_id: str
    node_type: str                     # file, symbol, test, sidecar, verifier, contract, capsule, memory
    shape: str                         # cube, sphere, pyramid, cylinder, shield, diamond, packet, crystal
    color: str                         # green, yellow, red, blue, purple, cyan, grey, gold
    status: str                        # blocked, proposed, leased, staged, verified, stale
    source_ref: SourceRef
    hardware_profile: HardwareProfile
    
    # Validation & Grounding Vectors
    verifier_pass_score: float = 0.0
    test_coverage_score: float = 0.0
    source_grounding_score: float = 0.0
    boundary_contract_completeness: float = 0.0
    
    # Context & Memory Metric Drivers
    dream_usefulness: float = 0.0
    qdkt_confidence: float = 0.0
    concept_vector_hash: str = ""       # Bound VSA concept hash signature
    
    # Structural Penalties
    failure_penalty: float = 0.0
    stale_context_penalty: float = 0.0
    missing_symbol_penalty: float = 0.0
    overcoupling_penalty: float = 0.0
    
    luminance: float = 0.0
    allowed_actions: List[str] = field(default_factory=list)
    forbidden_actions: List[str] = field(default_factory=list)
    symbolic_rules: List[SymbolicPatchRule] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SceneEdge:
    edge_type: str                      # DEPENDENCY, PROPOSED, STAGE_LINK, BOUNDARY_CONTRACT
    source: str
    target: str
    confidence: float = 1.0
    verified: bool = False
    luminance: float = 0.2
    blocker_reason: Optional[str] = None


@dataclass(frozen=True)
class SceneGraphSnapshot:
    snapshot_id: str
    timestamp: float
    nodes: Dict[str, SceneNode] = field(default_factory=dict)
    edges: List[SceneEdge] = field(default_factory=list)
    topology_density_score: float = 0.0
    active_prior_id: Optional[str] = None
    version: str = AURA_SCENE_GRAPH_SNAPSHOT_V1
