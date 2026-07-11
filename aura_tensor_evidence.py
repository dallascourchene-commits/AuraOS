"""
Aura Tensor Evidence Engine — localized tensor-factor representation +
deterministic belief propagation + low-rank compression + confinement analysis.

CPU + NumPy only. No PyTorch, TensorFlow, JAX, or ITensor.
Advisory only — never becomes patch authority, test authority, or Civic decision authority.

Authority invariants:
    patch_authority: exact_source_spans_and_hashes_only
    tensor_patch_authority: false
    belief_propagation_patch_authority: false
    civic_decision_authority: false
"""
from __future__ import annotations
import hashlib, time, json
from dataclasses import dataclass, field, asdict
from typing import Any
import numpy as np

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
TENSOR_PATCH_AUTHORITY = False
BELIEF_PROPAGATION_PATCH_AUTHORITY = False
CIVIC_DECISION_AUTHORITY = False

# --- Variable states (small deterministic space) ---
SUPPORTED = "SUPPORTED"
CONTRADICTED = "CONTRADICTED"
UNRESOLVED = "UNRESOLVED"
N_STATES = 3
STATE_INDEX = {SUPPORTED: 0, CONTRADICTED: 1, UNRESOLVED: 2}
INDEX_STATE = {0: SUPPORTED, 1: CONTRADICTED, 2: UNRESOLVED}

# --- BP statuses ---
CONVERGED = "CONVERGED"
NOT_CONVERGED = "NOT_CONVERGED"
CONTRADICTORY_HARD_FACTORS = "CONTRADICTORY_HARD_FACTORS"
INVALID_GRAPH = "INVALID_GRAPH"
FALLBACK_REQUIRED = "FALLBACK_REQUIRED"

# --- Confinement levels ---
HIGH_CONFINEMENT = "HIGH_CONFINEMENT"
MODERATE_CONFINEMENT = "MODERATE_CONFINEMENT"
LOW_CONFINEMENT = "LOW_CONFINEMENT"
UNKNOWN = "UNKNOWN"

# --- Authority flags ---
AUTHORITY_FLAGS = {
    "patch_authority": PATCH_AUTHORITY,
    "tensor_patch_authority": TENSOR_PATCH_AUTHORITY,
    "belief_propagation_patch_authority": BELIEF_PROPAGATION_PATCH_AUTHORITY,
    "civic_decision_authority": CIVIC_DECISION_AUTHORITY,
}


@dataclass
class EvidenceReference:
    """Exact evidence reference — file, symbol, line, hash, test, civic ID, etc."""
    file: str = ""
    symbol: str = ""
    line_range: tuple[int, int] = (0, 0)
    source_hash: str = ""
    topology_node_id: str = ""
    test: str = ""
    civic_contribution_id: str = ""
    civic_evidence_id: str = ""
    scenario_id: str = ""
    consent_response_id: str = ""
    human_note: str = ""
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class TensorVariable:
    """A variable in the tensor evidence graph."""
    var_id: str
    states: list[str] = field(default_factory=lambda: [SUPPORTED, CONTRADICTED, UNRESOLVED])
    evidence_refs: list[EvidenceReference] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return {"var_id": self.var_id, "states": self.states,
                "evidence_refs": [r.to_dict() for r in self.evidence_refs]}


@dataclass
class TensorFactor:
    """A factor connecting variables with a NumPy potential tensor."""
    factor_id: str
    var_ids: list[str]
    tensor: np.ndarray  # shape = (N_STATES,) * len(var_ids)
    evidence_refs: list[EvidenceReference] = field(default_factory=list)
    factor_origin: str = "explicit"  # or "emergent_candidate"
    authority: str = "advisory"
    def to_dict(self) -> dict[str, Any]:
        return {"factor_id": self.factor_id, "var_ids": self.var_ids,
                "tensor_shape": list(self.tensor.shape),
                "evidence_refs": [r.to_dict() for r in self.evidence_refs],
                "factor_origin": self.factor_origin, "authority": self.authority}


@dataclass
class BeliefMessage:
    """A message from factor to variable or vice versa."""
    from_id: str
    to_id: str
    values: np.ndarray  # shape = (N_STATES,)
    def to_dict(self) -> dict[str, Any]:
        return {"from": self.from_id, "to": self.to_id, "values": self.values.tolist()}


@dataclass
class BeliefResult:
    """Belief propagation result for a single variable."""
    var_id: str
    beliefs: np.ndarray  # shape = (N_STATES,) — normalized
    state: str  # SUPPORTED, CONTRADICTED, UNRESOLVED
    confidence: float
    supporting_evidence: list[EvidenceReference] = field(default_factory=list)
    contradicting_evidence: list[EvidenceReference] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return {"var_id": self.var_id, "beliefs": self.beliefs.tolist(),
                "state": self.state, "confidence": self.confidence,
                "supporting_evidence": [r.to_dict() for r in self.supporting_evidence],
                "contradicting_evidence": [r.to_dict() for r in self.contradicting_evidence]}


@dataclass
class ConfinementResult:
    """Computational confinement analysis for a graph region."""
    confinement_score: float
    confinement_level: str
    boundary_edge_count: int
    external_effect_count: int
    test_closure: bool
    influence_radius: float
    local_recompute_allowed: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class TensorEvidenceGraph:
    """A bounded tensor evidence graph."""
    variables: list[TensorVariable] = field(default_factory=list)
    factors: list[TensorFactor] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (factor_id, var_id)

    def graph_hash(self) -> str:
        raw = json.dumps({
            "vars": sorted(v.var_id for v in self.variables),
            "factors": sorted(f.factor_id for f in self.factors),
            "edges": sorted(self.edges),
        }, sort_keys=True)
        return hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {"variables": [v.to_dict() for v in self.variables],
                "factors": [f.to_dict() for f in self.factors],
                "edges": self.edges, "graph_hash": self.graph_hash(),
                **AUTHORITY_FLAGS}


class TensorBeliefEngine:
    """Deterministic, damped, log-space belief propagation engine.

    Defaults: damping=0.5, max_iterations=20, residual_tolerance=1e-4.
    Uses NumPy only. Advisory only.
    """

    def analyze(
        self,
        variables: list[TensorVariable],
        factors: list[TensorFactor],
        evidence: dict[str, np.ndarray] | None = None,
        *,
        damping: float = 0.5,
        max_iterations: int = 20,
        residual_tolerance: float = 1e-4,
    ) -> dict[str, Any]:
        """Run belief propagation and return results + confinement + metadata.

        Returns a dict with: ok, status, iterations, max_residual, results,
        graph_hash, confinement, execution_time_ms, **AUTHORITY_FLAGS.
        """
        start = time.time()

        # --- Validate graph ---
        if not variables:
            return self._fallback("no variables", INVALID_GRAPH, 0.0, [])

        # Validate factor tensor shapes
        for f in factors:
            expected_shape = (N_STATES,) * len(f.var_ids)
            if f.tensor.shape != expected_shape:
                return self._fallback(
                    f"factor {f.factor_id} shape {f.tensor.shape} != expected {expected_shape}",
                    INVALID_GRAPH, 0.0, variables)

        # Build variable index
        var_ids = [v.var_id for v in variables]
        var_idx = {vid: i for i, vid in enumerate(var_ids)}
        n_vars = len(var_ids)

        # Build factor-to-var and var-to-factor adjacency
        factor_vars: dict[str, list[str]] = {}
        var_factors: dict[str, list[str]] = {vid: [] for vid in var_ids}
        for f in factors:
            factor_vars[f.factor_id] = f.var_ids
            for vid in f.var_ids:
                if vid in var_factors:
                    var_factors[vid].append(f.factor_id)

        # --- Check for contradictory hard factors ---
        # A hard factor (one-hot) that forces SUPPORTED and another that forces
        # CONTRADICTED on the same variable = contradictory
        hard_assignments: dict[str, int] = {}
        is_contradictory = False
        for f in factors:
            t = f.tensor
            if f.var_ids and len(f.var_ids) == 1 and t.shape == (N_STATES,):
                # Check if it's a near-one-hot
                max_idx = int(np.argmax(t))
                if t[max_idx] > 0.95 and t.sum() > 0.95:
                    vid = f.var_ids[0]
                    if vid in hard_assignments and hard_assignments[vid] != max_idx:
                        is_contradictory = True
                    hard_assignments[vid] = max_idx

        if is_contradictory:
            # Still run BP but mark as contradictory
            pass

        # --- Initialize messages ---
        # var->factor messages start uniform
        msg_var_to_factor: dict[tuple[str, str], np.ndarray] = {}
        msg_factor_to_var: dict[tuple[str, str], np.ndarray] = {}

        for f in factors:
            for vid in f.var_ids:
                msg_var_to_factor[(vid, f.factor_id)] = np.ones(N_STATES) / N_STATES
                msg_factor_to_var[(f.factor_id, vid)] = np.ones(N_STATES) / N_STATES

        # --- Apply evidence as unary factors ---
        # evidence is a dict var_id -> np.ndarray(N_STATES) log-likelihood
        log_evidence: dict[str, np.ndarray] = {}
        if evidence:
            for vid, vals in evidence.items():
                v = np.asarray(vals, dtype=np.float64)
                # Reject NaN/Inf
                if np.any(np.isnan(v)) or np.any(np.isinf(v)):
                    return self._fallback(f"NaN/Inf in evidence for {vid}", INVALID_GRAPH, 0.0, variables)
                v = np.clip(v, -50, 50)  # bound log-space
                log_evidence[vid] = v

        # --- Belief propagation iterations ---
        converged = False
        max_residual = float('inf')
        iterations = 0
        prev_messages = dict(msg_factor_to_var)

        for iteration in range(max_iterations):
            iterations = iteration + 1
            max_residual = 0.0

            # Factor-to-var update
            for f in factors:
                vids = f.var_ids
                if not vids:
                    continue
                # For each connected var, compute message
                for target_vid in vids:
                    # Product of all incoming var->factor messages except from target
                    other_vars = [v for v in vids if v != target_vid]
                    if not other_vars:
                        # Unary factor — just use the tensor directly
                        raw = f.tensor.copy()
                    else:
                        # Compute factor-to-var message
                        # Tensor contraction over other variables
                        raw = f.tensor.copy()
                        # Apply incoming messages from other vars
                        for ov in other_vars:
                            incoming = msg_var_to_factor.get((ov, f.factor_id))
                            if incoming is not None:
                                ov_idx = vids.index(ov)
                                shape = [1] * len(vids)
                                shape[ov_idx] = N_STATES
                                raw = raw * incoming.reshape(shape)
                            # Sum out the other var
                            ov_idx_in_remaining = vids.index(ov)
                            raw = np.sum(raw, axis=ov_idx_in_remaining)
                            # Adjust vids list for subsequent indexing
                            vids = [v for v in vids if v != ov]
                        # Reset vids for next target
                        vids = f.var_ids

                    # Convert to log space
                    raw = np.clip(raw, 1e-30, None)
                    log_msg = np.log(raw)
                    # Add evidence only in the final belief computation, not here (C4 fix)
                    # Normalize
                    log_msg = log_msg - np.max(log_msg)
                    msg = np.exp(log_msg)
                    msg = msg / (msg.sum() + 1e-30)

                    # Damping
                    old = prev_messages.get((f.factor_id, target_vid), msg)
                    new_msg = damping * old + (1 - damping) * msg
                    new_msg = new_msg / (new_msg.sum() + 1e-30)

                    residual = np.max(np.abs(new_msg - old))
                    max_residual = max(max_residual, float(residual))
                    msg_factor_to_var[(f.factor_id, target_vid)] = new_msg

            # Var-to-factor update
            for vid in var_ids:
                # Product of all incoming factor->var messages
                incoming_factors = var_factors.get(vid, [])
                if not incoming_factors:
                    # No factors — use evidence or uniform
                    if vid in log_evidence:
                        belief = np.exp(log_evidence[vid] - np.max(log_evidence[vid]))
                        belief = belief / (belief.sum() + 1e-30)
                    else:
                        belief = np.ones(N_STATES) / N_STATES
                else:
                    belief = np.ones(N_STATES)
                    for fid in incoming_factors:
                        msg = msg_factor_to_var.get((fid, vid))
                        if msg is not None:
                            belief = belief * msg
                    # Apply evidence
                    if vid in log_evidence:
                        belief = belief * np.exp(log_evidence[vid])
                    belief = belief / (belief.sum() + 1e-30)

                # Send to each factor
                for fid in incoming_factors:
                    # Exclude the factor's own message
                    other_incoming = [msg_factor_to_var.get((f2, vid)) for f2 in incoming_factors if f2 != fid]
                    if other_incoming:
                        outgoing = np.ones(N_STATES)
                        for m in other_incoming:
                            if m is not None:
                                outgoing = outgoing * m
                        # Evidence is applied in factor-to-var path only (C4 fix)
                        if vid in log_evidence:
                            outgoing = outgoing * np.exp(log_evidence[vid])
                        outgoing = outgoing / (outgoing.sum() + 1e-30)
                    else:
                        outgoing = belief.copy()
                    msg_var_to_factor[(vid, fid)] = outgoing

            prev_messages = dict(msg_factor_to_var)

            if max_residual < residual_tolerance:
                converged = True
                break

        # --- Compute final beliefs ---
        results: list[BeliefResult] = []
        for v in variables:
            vid = v.var_id
            incoming_factors = var_factors.get(vid, [])
            belief = np.ones(N_STATES)
            for fid in incoming_factors:
                msg = msg_factor_to_var.get((fid, vid))
                if msg is not None:
                    belief = belief * msg
            if vid in log_evidence:
                belief = belief * np.exp(log_evidence[vid])
            belief = belief / (belief.sum() + 1e-30)

            state_idx = int(np.argmax(belief))
            # Treat ties (near-uniform) as UNRESOLVED
            confidence = float(belief[state_idx])
            if confidence < 0.4:
                state = UNRESOLVED
            else:
                state = INDEX_STATE[state_idx]

            # Collect supporting/contradicting evidence
            supporting = []
            contradicting = []
            for ref in v.evidence_refs:
                if state == SUPPORTED:
                    supporting.append(ref)
                elif state == CONTRADICTED:
                    contradicting.append(ref)
            # Also check factor evidence
            for fid in incoming_factors:
                f = next((f for f in factors if f.factor_id == fid), None)
                if f:
                    for ref in f.evidence_refs:
                        if state == SUPPORTED:
                            supporting.append(ref)
                        elif state == CONTRADICTED:
                            contradicting.append(ref)

            results.append(BeliefResult(
                var_id=vid, beliefs=belief, state=state,
                confidence=confidence,
                supporting_evidence=supporting,
                contradicting_evidence=contradicting,
            ))

        # --- Determine status ---
        if is_contradictory:
            status = CONTRADICTORY_HARD_FACTORS
        elif converged:
            status = CONVERGED
        else:
            status = NOT_CONVERGED

        # --- Build graph ---
        graph = TensorEvidenceGraph(variables=variables, factors=factors,
                                    edges=[(f.factor_id, v) for f in factors for v in f.var_ids])
        graph_hash = graph.graph_hash()

        # --- Confinement analysis ---
        confinement = self._confinement_analysis(graph, results, converged, var_factors)

        exec_time = (time.time() - start) * 1000

        return {
            "ok": True,
            "status": status,
            "iterations": iterations,
            "max_residual": max_residual,
            "results": [r.to_dict() for r in results],
            "graph_hash": graph_hash,
            "confinement": confinement.to_dict(),
            "execution_time_ms": exec_time,
            "n_variables": n_vars,
            "n_factors": len(factors),
            **AUTHORITY_FLAGS,
        }

    def _fallback(self, reason: str, status: str, exec_time: float,
                  variables: list[TensorVariable]) -> dict[str, Any]:
        """Safe fallback when BP cannot run."""
        results = [BeliefResult(var_id=v.var_id, beliefs=np.ones(N_STATES)/N_STATES,
                                state=UNRESOLVED, confidence=0.0).to_dict()
                    for v in variables]
        confinement = ConfinementResult(
            confinement_score=0.0, confinement_level=UNKNOWN,
            boundary_edge_count=0, external_effect_count=0,
            test_closure=False, influence_radius=float('inf'),
            local_recompute_allowed=False,
            reasons=[reason], warnings=["Fallback invoked — results are advisory only."]
        ).to_dict()
        return {"ok": False, "status": status, "iterations": 0, "max_residual": float('inf'),
                "results": results, "graph_hash": "", "confinement": confinement,
                "execution_time_ms": exec_time, "n_variables": len(variables), "n_factors": 0,
                "fallback_reason": reason, **AUTHORITY_FLAGS}

    def _confinement_analysis(self, graph: TensorEvidenceGraph, results: list[BeliefResult],
                              converged: bool, var_factors: dict | None = None) -> ConfinementResult:
        """Bounded confinement analysis."""
        var_ids = {v.var_id for v in graph.variables}
        var_ids_list = [v.var_id for v in graph.variables]
        internal_edges = 0
        boundary_edges = 0
        boundary_vars = set()

        # Analyze edges: internal = both endpoints in graph, boundary = one endpoint outside
        for fid, vid in graph.edges:
            if vid in var_ids:
                internal_edges += 1
                # Check if this factor connects to vars outside our set
                f = next((f for f in graph.factors if f.factor_id == fid), None)
                if f:
                    for other_vid in f.var_ids:
                        if other_vid not in var_ids:
                            boundary_edges += 1
                            boundary_vars.add(vid)

        # Count unresolved variables as potential external effects
        unresolved = sum(1 for r in results if r.state == UNRESOLVED)
        contradicted = sum(1 for r in results if r.state == CONTRADICTED)
        external_effects = unresolved + contradicted + len(boundary_vars)

        # Estimate influence radius from message propagation
        if converged and internal_edges > 0:
            influence_radius = len(var_ids) / (1.0 + internal_edges)
        elif converged:
            influence_radius = float(len(var_ids))
        else:
            influence_radius = float('inf')

        # Confinement score: higher = more confined
        if not var_ids:
            score = 0.0
        else:
            score = 1.0 - (boundary_edges + external_effects) / (len(var_ids) + 1)
            score = max(0.0, min(1.0, score))

        if score > 0.7 and converged:
            level = HIGH_CONFINEMENT
        elif score > 0.4:
            level = MODERATE_CONFINEMENT
        elif converged:
            level = LOW_CONFINEMENT
        else:
            level = UNKNOWN

        local_recompute = (score > 0.5 and converged and unresolved == 0 and boundary_edges <= 2)

        reasons = []
        if converged:
            reasons.append("BP converged")
        else:
            reasons.append("BP did not converge")
        if unresolved > 0:
            reasons.append(f"{unresolved} unresolved variables")
        if contradicted > 0:
            reasons.append(f"{contradicted} contradicted variables")

        warnings = []
        if not converged:
            warnings.append("Non-converged results are advisory and should not be treated as resolved.")
        if influence_radius == float('inf'):
            warnings.append("Influence radius is unbounded due to non-convergence.")

        return ConfinementResult(
            confinement_score=round(score, 4),
            confinement_level=level,
            boundary_edge_count=boundary_edges,
            external_effect_count=unresolved + contradicted,
            test_closure=local_recompute,
            influence_radius=round(influence_radius, 4) if influence_radius != float('inf') else float('inf'),
            local_recompute_allowed=local_recompute,
            reasons=reasons,
            warnings=warnings,
        )


def compress_factor(
    tensor: np.ndarray,
    max_rank: int | None = None,
    reconstruction_tolerance: float = 1e-3,
) -> dict[str, Any]:
    """Low-rank compression of a factor tensor using NumPy SVD.

    Reports original shape, compressed rank, element counts, reconstruction error.
    Refuses compression when error exceeds the threshold.
    Preserves the original factor when compression provides no meaningful benefit.
    """
    original = np.asarray(tensor, dtype=np.float64)
    original_shape = original.shape
    original_elements = original.size

    # Only compress 2D+ tensors that are large enough
    if original.ndim < 2 or original.size < 16:
        return {"ok": True, "compressed": False, "reason": "tensor too small for meaningful compression",
                "original_shape": list(original_shape), "original_elements": original_elements,
                "compressed_rank": None, "compressed_elements": original_elements,
                "compression_ratio": 1.0, "reconstruction_error": 0.0,
                **AUTHORITY_FLAGS}

    # Reshape to 2D for SVD
    if original.ndim > 2:
        flat = original.reshape(original.shape[0], -1)
    else:
        flat = original

    try:
        u, s, vh = np.linalg.svd(flat, full_matrices=False)
    except np.linalg.LinAlgError:
        return {"ok": False, "error": "SVD failed", "compressed": False,
                "original_shape": list(original_shape), **AUTHORITY_FLAGS}

    # Determine rank
    if max_rank is not None:
        k = min(max_rank, len(s))
    else:
        # Auto-select rank based on tolerance
        s_cumulative = np.cumsum(s**2) / np.sum(s**2)
        k = int(np.searchsorted(s_cumulative, 1.0 - reconstruction_tolerance) + 1)
        k = max(1, min(k, len(s)))

    # Reconstruct
    compressed_flat = u[:, :k] @ np.diag(s[:k]) @ vh[:k, :]
    if original.ndim > 2:
        compressed = compressed_flat.reshape(original_shape)
    else:
        compressed = compressed_flat

    reconstruction_error = float(np.max(np.abs(original - compressed)))
    compressed_elements = u[:, :k].size + s[:k].size + vh[:k, :].size
    compression_ratio = compressed_elements / original_elements if original_elements > 0 else 1.0

    # Refuse if error too high
    if reconstruction_error > reconstruction_tolerance:
        return {"ok": True, "compressed": False,
                "reason": f"reconstruction_error {reconstruction_error:.6f} exceeds tolerance {reconstruction_tolerance}",
                "original_shape": list(original_shape), "original_elements": original_elements,
                "compressed_rank": k, "compressed_elements": compressed_elements,
                "compression_ratio": compression_ratio, "reconstruction_error": reconstruction_error,
                **AUTHORITY_FLAGS}

    # Refuse if no benefit
    if compression_ratio >= 1.0:
        return {"ok": True, "compressed": False, "reason": "no compression benefit",
                "original_shape": list(original_shape), "original_elements": original_elements,
                "compressed_rank": k, "compressed_elements": compressed_elements,
                "compression_ratio": compression_ratio, "reconstruction_error": reconstruction_error,
                **AUTHORITY_FLAGS}

    return {"ok": True, "compressed": True,
            "original_shape": list(original_shape), "original_elements": original_elements,
            "compressed_rank": k, "compressed_elements": compressed_elements,
            "compression_ratio": round(compression_ratio, 4),
            "reconstruction_error": round(reconstruction_error, 6),
            "compressed_tensor": compressed.tolist(),
            **AUTHORITY_FLAGS}
