"""D0 Memory City Navigator routing/admission donor.

Projection/routing only. This package does not own K27 truth, currentness,
source memory, effect authority, or Gate 10.
"""
from .route_card_admission import (
    Admission, CapacityEnvelope, Disposition, Polarity, ProofReceipt,
    RouteIdentity, TemporalRequirement, TimingMode, UseContext, admit,
    canonical_receipt_root, temporal_contract_root,
)
from .runtime_bridge import RuntimeBridgeError, RuntimeBridgeReceipt, route_identity_from_runtime
from .route_delta_planner import (
    DeltaPlan, DeltaStrategy, RouteChange, RouteSegment, SegmentDecision,
    plan_route_delta,
)
from .minimal_evidence import (
    DecisionNode, EvidenceMode, EvidencePlan, EvidenceWorld,
    compile_minimal_evidence, evaluate,
)
from .temporal_zone import (
    DifferenceConstraint, ZoneCertificate, ZoneDisposition, compile_zone,
)
from .reflexive_topology import (
    ProbeStep, TopologyCertificate, TopologyDisposition, components,
    execute_probe_program, graph_root, program_root,
)
from .route_evidence_transaction import (
    RouteEvidenceTransaction, TransactionDisposition, certify,
)

__all__ = [
    "Admission", "CapacityEnvelope", "Disposition", "Polarity", "ProofReceipt",
    "RouteIdentity", "TemporalRequirement", "TimingMode", "UseContext", "admit",
    "canonical_receipt_root", "temporal_contract_root", "RuntimeBridgeError",
    "RuntimeBridgeReceipt", "route_identity_from_runtime", "DeltaPlan",
    "DeltaStrategy", "RouteChange", "RouteSegment", "SegmentDecision",
    "plan_route_delta", "DecisionNode", "EvidenceMode", "EvidencePlan",
    "EvidenceWorld", "compile_minimal_evidence", "evaluate",
    "DifferenceConstraint", "ZoneCertificate", "ZoneDisposition", "compile_zone",
    "ProbeStep", "TopologyCertificate", "TopologyDisposition", "components",
    "execute_probe_program", "graph_root", "program_root",
    "RouteEvidenceTransaction", "TransactionDisposition", "certify",
]
