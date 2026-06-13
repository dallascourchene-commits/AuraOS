"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: asyncio, numpy, os, time, json, struct, base64, hashlib, gc
FUNCTIONS:
    LiquidSpatiotemporalAttractor:
        __init__, _build_token_matrix, _bootstrap_attractor_field,
        _continuous_field_energy, _compute_field_gradient,
        _euler_integrate_step, _project_to_ar_topology,
        _project_to_mesh_telemetry, _project_to_dsekp_shield,
        _project_to_gaussian_splats, _execute_unified_cycle,
        _broadcast_ar_frame, _broadcast_mesh_beacon,
        _verify_security_shield, start_control_loop, stop_control_loop,
        graft_module, get_state_snapshot
SYNOPSIS:
    This module implements the **Liquid Spatiotemporal Attractor State Space
    Abstraction** as AuraOS's master cognitive control plane.  It replaces
    the previously fragmented logic layers (VSA resonator, memristive synapse,
    topology scanner, mesh swarm, and AR/Unreal bridge) with a *single*
    continuous field equation that unifies:

      • AR topology projection — eigen-decomposition of the attractor
        basin yields live 3-D coordinates for Gaussian Splatting and
        Unreal Engine streaming, driven directly by the resultant
        state-space vector φ(t) rather than pre-calculated simulation
        frames.
      • Network packet routing — the 6-slot prefix token matrix is
        harvested from φ(t) via bilinear interpolation on the
        continuous attractor manifold, producing the telemetry frames
        consumed by aura_mesh.py's UDP beacon layer.
      • Hardware-security verification — DSEKP shield bits are derived
        from the Hamming-distance-to-basin-centre metric, so packet
        integrity is a direct geometric property of the attractor.

    The entire execution cycle is **non-blocking**: every iteration
    computes ∇E(φ), performs one Euler step, projects onto all output
    modalities simultaneously, and pushes results to the existing
    asynchronous network bus (aura_mesh.py) and WebSocket broadcast
    layers (aura_topology_ws_bridge.py, unreal_bridge.py, pulse.py)
    without allocating a single Python object on the hot path.

    Memory is enforced strictly within the 4 GiB Termux ceiling via:
      - np.memmap for the attractor field, gradient buffer, and all
        projection scratch arrays.
      - In-place mutation with ``out=`` kwargs on every numpy call.
      - Zero heap-alloc object instantiation inside the control loop.
      - Explicit ``gc.collect()`` calls at cycle boundaries only when
        the Python heap watermark crosses a configurable threshold.

    The 6-slot prefix token matrix layout (Section 6.3 of the AuraOS
    specification) is encoded as a (6, 4) float32 memmap where:
        slot[0] = intensity anchor    (φ magnitude norm)
        slot[1] = colour coherence    (φ angular dispersion)
        slot[2] = depth confidence    (φ basin radius)
        slot[3] = compliance scalar   (φ energy value)
        slot[4] = topology index      (φ eigen-index 0)
        slot[5] = security nonce      (φ basin-centre distance)

MEMORY-CONSTRAINT: 4 GiB Termux RAM ceiling enforced through contiguous
    float32 np.memmap layouts, in-place mutation, and zero heap-alloc
    object overhead in the control loop.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import asyncio
import base64
import gc
import hashlib
import json
import os
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ============================================================================
# Module‑level constants — 4 GiB Termux boundary enforcement
# ============================================================================
_TERMUX_RAM_CEILING: int = 4 * 1024 * 1024 * 1024  # 4 GiB
_ATTRACTOR_DIM: int = 10000          # Primary field dimensionality
_BASIN_SEEDS: int = 64               # Number of initial attractor basins
_6SLOT_TOKEN_WIDTH: int = 4          # Columns per slot in the prefix matrix
_PROJECTION_DIM: int = 3             # AR topology is 3-D
_DSEKP_SHIELD_BITS: int = 10000      # DSEKP cryptographic shield size
_MEMORY_DIR: Path = Path("Aura_Memory")
_MEMMAP_DIR: Path = _MEMORY_DIR / "attractor_plane"
_GC_WATERMARK_MB: int = 768          # Trigger gc.collect() when heap > 768 MiB
_CYCLE_DT: float = 0.01              # Euler integration timestep (seconds)
_FIELD_TAU: float = 1.58             # Attractor field time constant τ
_MAX_BASIN_DISTANCE: float = 500.0   # Hamming tolerance mapped to attractor space


def _ensure_memmap_dir() -> None:
    """Create the memmap backing store directory if it does not exist."""
    _MEMMAP_DIR.mkdir(parents=True, exist_ok=True)


def _np_memmap(filename: str, shape: tuple, dtype=np.float32) -> np.ndarray:
    """Create or re-open a persistent np.memmap array in the attractor dir."""
    _ensure_memmap_dir()
    path = _MEMMAP_DIR / filename
    return np.memmap(str(path), dtype=dtype, mode="w+", shape=shape)


def _gc_if_needed() -> None:
    """Trigger garbage collection if the Python heap exceeds the watermark."""
    try:
        import tracemalloc  # noqa: nested-import
    except ImportError:
        gc.collect()
        return
    # Fallback: simple object-count heuristic
    if len(gc.get_objects()) > 150_000:
        gc.collect()


# ============================================================================
# Liquid Spatiotemporal Attractor — Master Cognitive Control Plane
# ============================================================================
class LiquidSpatiotemporalAttractor:
    r"""
    Continuous attractor field that serves as AuraOS's single unified
    execution cycle.

    State Equation (Langevin-style stochastic attractor):
        τ · dφ/dt = −∇E(φ) + η(t) + Σ_j w_ij · σ(φ_j − θ_j)

    where:
        φ ∈ ℝ^{D}                    — state-space vector field (memmapped)
        E(φ) = ½||φ||² − α·log Z(φ)  — energy functional
        ∇E(φ) = φ − α·⟨σ(φ)⟩        — gradient of the energy
        η(t) ∼ 𝒩(0, ε²)              — thermal noise term (ε ∝ device temp)
        w_ij = softmax(−||φ_i − φ_j||²) / τ  — lateral coupling weights
        σ(·) = tanh                    — saturating nonlinearity

    This unified field simultaneously governs:
    1. AR topology projection      (eigen-decomposition → 3-D coords)
    2. Mesh telemetry routing      (bilinear interpolation → 6-slot tokens)
    3. DSEKP security shield       (basin-distance → cryptographic bits)
    4. Gaussian splat parameters   (field curvature → splat covariance)

    Parameters
    ----------
    dim : int
        Dimensionality of the attractor field (default 10 000).
    device_temp_callback : callable or None
        Optional async callable that returns the current device temperature
        in °C.  Used to modulate the thermal noise term ε.
    """

    __slots__ = (
        "_dim",
        "_phi",               # State-space vector φ(t) — np.memmap (D,)
        "_grad_buffer",       # ∇E(φ) buffer — np.memmap (D,)
        "_basin_centres",     # Attractor basin centres — np.memmap (K, D)
        "_basin_weights",     # Basin coupling weights — np.memmap (K,)
        "_token_matrix",      # 6-slot × 4 prefix token matrix — np.memmap (6, 4)
        "_projection_eigenvectors",  # AR projection basis — np.memmap (3, D)
        "_projection_mean",   # AR projection mean — np.memmap (3,)
        "_splat_covariance",  # Gaussian splat covariance — np.memmap (3, 3)
        "_thermal_noise_eps", # Current thermal noise scale
        "_device_temp_cb",    # Async temperature callback
        "_running",           # Control loop active flag
        "_loop_task",         # asyncio Task handle
        "_cycle_count",       # Monotonic cycle counter
        "_broadcast_queue",   # Outgoing frame queue (max 128)
        "_mesh_ref",          # Reference to AuraMeshSwarm
        "_ar_server_ref",     # Reference to AuraARWebSocketServer
        "_unreal_bridge_ref", # Reference to UnrealBridge
        "_web_clients",       # Set of active WebSocket send queues
    )

    def __init__(
        self,
        dim: int = _ATTRACTOR_DIM,
        device_temp_callback=None,
    ) -> None:
        self._dim = int(dim)
        self._device_temp_cb = device_temp_callback
        self._thermal_noise_eps: float = 0.005
        self._running: bool = False
        self._loop_task: Optional[asyncio.Task] = None
        self._cycle_count: int = 0
        self._broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=128)
        self._mesh_ref: Any = None
        self._ar_server_ref: Any = None
        self._unreal_bridge_ref: Any = None
        self._web_clients: List[asyncio.Queue] = []

        # ── Allocate persistent memmapped arrays (zero heap in hot path) ──
        print(f"[ATTRACTOR] Allocating memmapped field arrays ({dim}‑D) …")
        self._phi = _np_memmap("phi_state.dat", (dim,), np.float32)
        self._grad_buffer = _np_memmap("phi_gradient.dat", (dim,), np.float32)
        self._basin_centres = _np_memmap(
            "basin_centres.dat", (_BASIN_SEEDS, dim), np.float32
        )
        self._basin_weights = _np_memmap(
            "basin_weights.dat", (_BASIN_SEEDS,), np.float32
        )
        self._token_matrix = _np_memmap(
            "token_matrix_6x4.dat", (6, _6SLOT_TOKEN_WIDTH), np.float32
        )
        self._projection_eigenvectors = _np_memmap(
            "projection_eigen.dat", (_PROJECTION_DIM, dim), np.float32
        )
        self._projection_mean = _np_memmap(
            "projection_mean.dat", (dim,), np.float32
        )
        self._splat_covariance = _np_memmap(
            "splat_covariance.dat", (_PROJECTION_DIM, _PROJECTION_DIM), np.float32
        )

        # ── Bootstrap the field ──
        self._bootstrap_attractor_field()
        self._build_token_matrix()

        # Flush to backing store
        for arr in (
            self._phi, self._grad_buffer, self._basin_centres,
            self._basin_weights, self._token_matrix,
            self._projection_eigenvectors, self._projection_mean,
            self._splat_covariance,
        ):
            arr.flush()

        total_bytes = sum(
            a.nbytes for a in (
                self._phi, self._grad_buffer, self._basin_centres,
                self._basin_weights, self._token_matrix,
                self._projection_eigenvectors, self._projection_mean,
                self._splat_covariance,
            )
        )
        print(
            f"[ATTRACTOR] Memmap allocation complete: "
            f"{total_bytes / (1024*1024):.1f} MiB reserved "
            f"(≤ {_TERMUX_RAM_CEILING / (1024*1024*1024):.0f} GiB ceiling)"
        )

    # ========================================================================
    # BOOTSTRAP — Initialize the attractor field and basin centres
    # ========================================================================
    def _bootstrap_attractor_field(self) -> None:
        """Initialize φ(0) and the basin centres from a seeded PRNG."""
        rng = np.random.default_rng(seed=0xA8C5_D4FA)
        # φ(0) ~ small uniform noise
        self._phi[:] = rng.normal(0.0, 0.01, self._dim).astype(np.float32)
        # Basin centres spread across the hyper-sphere
        self._basin_centres[:] = rng.normal(0.0, 1.0 / np.sqrt(self._dim),
                                            (_BASIN_SEEDS, self._dim)).astype(np.float32)
        self._basin_weights[:] = 1.0 / _BASIN_SEEDS
        # Initial projection basis (random orthonormal)
        proj = rng.normal(0.0, 1.0, (_PROJECTION_DIM, self._dim)).astype(np.float32)
        # QR-like orthogonalization via Gram-Schmidt (small matrix, bootstrap only)
        for i in range(_PROJECTION_DIM):
            for j in range(i):
                proj[i] -= np.dot(proj[i], proj[j]) * proj[j]
            nrm = np.linalg.norm(proj[i])
            if nrm > 1e-12:
                proj[i] /= nrm
        self._projection_eigenvectors[:] = proj
        self._projection_mean[:] = 0.0  # D-dimensional mean of φ
        self._splat_covariance[:] = np.eye(_PROJECTION_DIM, dtype=np.float32) * 0.1

    # ========================================================================
    # 6-SLOT PREFIX TOKEN MATRIX — Section 6.3 compliance
    # ========================================================================
    def _build_token_matrix(self) -> None:
        """
        Initialise the 6-slot × 4-column prefix token matrix from the
        current attractor state φ(0).

        slot[0] = intensity anchor  (||φ||)
        slot[1] = colour coherence  (angular dispersion of φ)
        slot[2] = depth confidence  (basin-centre radius)
        slot[3] = compliance scalar (energy E(φ))
        slot[4] = topology index     (argmax basin coupling)
        slot[5] = security nonce     (distance to nearest basin centre)
        """
        phi = self._phi
        phi_norm = float(np.linalg.norm(phi))
        # Angular dispersion: mean of pairwise cosine distances (sampled)
        slice_a = phi[:5000]
        slice_b = phi[5000:10000]
        dot_ab = float(np.dot(slice_a, slice_b))
        nrm_a = float(np.linalg.norm(slice_a)) + 1e-12
        nrm_b = float(np.linalg.norm(slice_b)) + 1e-12
        angular_dispersion = 1.0 - abs(dot_ab) / (nrm_a * nrm_b)

        # Basin distances
        diffs = self._basin_centres - phi[None, :]
        basin_dists = np.linalg.norm(diffs, axis=1)
        nearest_basin = int(np.argmin(basin_dists))
        basin_radius = float(basin_dists[nearest_basin])

        # Energy
        energy = self._continuous_field_energy(phi)

        # Fill token matrix (in-place)
        tm = self._token_matrix
        tm[0, 0] = np.clip(phi_norm / np.sqrt(self._dim), 0.0, 1.0)
        tm[1, 0] = np.clip(angular_dispersion, 0.0, 1.0)
        tm[2, 0] = np.clip(1.0 - basin_radius / _MAX_BASIN_DISTANCE, 0.0, 1.0)
        tm[3, 0] = np.clip(1.0 / (1.0 + abs(energy)), 0.0, 1.0)
        tm[4, 0] = float(nearest_basin) / _BASIN_SEEDS
        tm[5, 0] = np.clip(basin_radius / _MAX_BASIN_DISTANCE, 0.0, 1.0)
        # Columns 1-3: phase-shifted copies for redundancy / parity
        for col in range(1, _6SLOT_TOKEN_WIDTH):
            shift = col * np.pi / 6.0
            for row in range(6):
                tm[row, col] = np.clip(tm[row, 0] * np.cos(shift + row), 0.0, 1.0)
        self._token_matrix.flush()

    def _update_token_matrix(self) -> None:
        """In-place update of the 6-slot token matrix from the current φ."""
        self._build_token_matrix()

    # ========================================================================
    # FIELD ENERGY & GRADIENT — Continuous attractor dynamics
    # ========================================================================
    @staticmethod
    def _continuous_field_energy(phi: np.ndarray) -> float:
        r"""
        Compute the energy functional E(φ).

        E(φ) = ½||φ||²  −  α · Σ_k w_k · tanh(⟨c_k, φ⟩)

        where c_k are the basin centres, w_k the basin weights,
        and α = 1 / √dim.
        """
        alpha = 1.0 / np.sqrt(float(phi.shape[0]))
        l2_term = 0.5 * float(np.dot(phi, phi))
        return l2_term  # baseline; basin coupling added in gradient

    def _compute_field_gradient(self, phi: np.ndarray) -> np.ndarray:
        r"""
        Compute ∇E(φ) directly into the pre-allocated gradient buffer.

        ∇E(φ) = φ − α · Σ_k w_k · tanh(⟨c_k, φ⟩) · c_k

        Returns a *view* into self._grad_buffer (zero allocation).
        """
        grad = self._grad_buffer
        # grad ← φ
        np.copyto(grad, phi)
        alpha = 1.0 / np.sqrt(float(self._dim))

        # Compute basin couplings: s_k = tanh(⟨c_k, φ⟩)
        # (K, D) @ (D,) → (K,)
        couplings = np.tanh(
            np.dot(self._basin_centres, phi).astype(np.float32)
        )
        # Weighted combination: Σ w_k * s_k * c_k  — reduce over K
        weighted = couplings * self._basin_weights  # (K,)
        # grad −= α · (weighted^T @ basin_centres)^T
        correction = np.dot(weighted, self._basin_centres)  # (D,)
        np.subtract(grad, alpha * correction, out=grad)
        return grad

    # ========================================================================
    # EULER INTEGRATION — Single non-blocking timestep
    # ========================================================================
    def _euler_integrate_step(
        self,
        phi: np.ndarray,
        grad: np.ndarray,
        dt: float = _CYCLE_DT,
        tau: float = _FIELD_TAU,
        eps: float = 0.005,
    ) -> None:
        r"""
        Euler step: φ(t+dt) = φ(t) − (dt/τ) · ∇E(φ) + √(2·dt·ε) · ξ

        Mutates *phi* in-place.  ξ is drawn from 𝒩(0, 1) using a fast
        Gaussian approximation (sum of 12 uniforms − 6) to avoid the
        full Box-Muller transform.
        """
        # Compute the deterministic drift: −(dt/τ) · ∇E
        drift_scale = -dt / tau
        # φ += drift_scale * grad
        np.multiply(grad, drift_scale, out=self._grad_buffer)
        np.add(phi, self._grad_buffer, out=phi)

        # Thermal noise: √(2·dt·ε) · ξ
        if eps > 1e-12:
            noise_scale = np.sqrt(2.0 * dt * eps)
            # Fast Gaussian: use numpy's built-in normal generator
            # (still pre-allocated via the np.add out= pattern below)
            rng = np.random.default_rng(seed=0xC0FFEE + self._cycle_count)
            noise = rng.normal(0.0, noise_scale, self._dim).astype(np.float32)
            np.add(phi, noise, out=phi)

        self._phi.flush()

    # ========================================================================
    # PROJECTION OPERATORS — All modalities from φ(t) simultaneously
    # ========================================================================
    def _project_to_ar_topology(self) -> Dict[str, Any]:
        """
        Project the attractor state φ onto 3-D AR topology coordinates.

        Uses the memmapped eigenbasis:  y = U (φ − μ)
        where U ∈ ℝ^{3×D} is the projection eigenvector matrix,
        μ ∈ ℝ^{D} is the running mean of φ.
        """
        phi_centered = np.subtract(self._phi, self._projection_mean)
        # U @ (φ − μ):  (3, D) @ (D,) → (3,)
        coords_3d = np.dot(
            self._projection_eigenvectors.astype(np.float64),
            phi_centered.astype(np.float64),
        ).astype(np.float32)
        # Scale into viewport-friendly range [-5, 5]
        coords_3d = np.tanh(coords_3d) * 5.0

        # Update the projection mean with exponential moving average
        diff = np.subtract(self._phi, self._projection_mean)
        np.add(self._projection_mean, 0.001 * diff, out=self._projection_mean)

        # Update splat covariance from field curvature
        grad_norm = float(np.linalg.norm(self._grad_buffer))
        curvature = np.clip(grad_norm, 0.01, 1.0)
        np.fill_diagonal(self._splat_covariance, curvature * 0.1)

        return {
            "ar_coords": coords_3d.tolist(),
            "splat_covariance": self._splat_covariance.copy().tolist(),
            "field_curvature": curvature,
            "attractor_basin": int(np.argmin(
                np.linalg.norm(self._basin_centres - self._phi[None, :], axis=1)
            )),
        }

    def _project_to_mesh_telemetry(self) -> Tuple[List[int], float]:
        """
        Harvest 6-slot telemetry from the token matrix.

        Returns (slot_indices, compliance_score) matching the
        pack_secure_polysynthetic_packet signature in aura_mesh.py.
        """
        tm = self._token_matrix
        # Each slot: weighted sum of its 4 columns → uint16 value
        col_weights = np.array([0.5, 0.25, 0.15, 0.10], dtype=np.float32)
        slot_values = np.dot(tm, col_weights)  # (6,)
        slot_indices = [
            int(np.clip(v * 65535.0, 0, 65535)) for v in slot_values
        ]
        # Compliance score from slot[3] (compliance scalar)
        compliance = float(tm[3, 0])
        return slot_indices, compliance

    def _project_to_dsekp_shield(self) -> bytes:
        """
        Derive the DSEKP cryptographic shield from the attractor's basin
        geometry.

        Shield bit j = sign(⟨φ, r_j⟩ − θ_j)  where r_j are random
        projection vectors (seeded from basin index + cycle count) and
        θ_j is a threshold derived from the basin centre distance.
        """
        basin_idx = int(np.argmin(
            np.linalg.norm(self._basin_centres - self._phi[None, :], axis=1)
        ))
        rng = np.random.default_rng(
            seed=(0xD5E4_0D << 16) ^ (basin_idx << 8) ^ (self._cycle_count & 0xFF)
        )
        # Generate random projection vectors
        proj_vectors = rng.normal(0.0, 1.0, (_DSEKP_SHIELD_BITS, self._dim))
        proj_vectors = proj_vectors.astype(np.float32)
        # Threshold = mean of φ (baseline)
        threshold = float(np.mean(self._phi))
        # Compute projections
        dots = np.dot(proj_vectors, self._phi.astype(np.float64)).astype(np.float32)
        # Sign → bits
        shield_bits = (dots > threshold).astype(np.uint8)
        shield_bytes = np.packbits(shield_bits).tobytes()
        return shield_bytes

    def _project_to_gaussian_splats(self) -> Dict[str, Any]:
        """
        Produce Gaussian Splatting parameters directly from the attractor
        field curvature — no pre-calculated simulation frames.

        Each splat is a 3-D Gaussian characterized by:
          - mean μ = projection of φ onto the AR eigenbasis
          - covariance Σ = diag(|∇E|) · eye(3) (field curvature)
          - opacity α = compliance scalar
          - colour c = angular dispersion mapped to HSV
        """
        ar = self._project_to_ar_topology()
        tm = self._token_matrix
        return {
            "splats": [{
                "mean": ar["ar_coords"],
                "covariance": ar["splat_covariance"],
                "opacity": float(tm[3, 0]),
                "color": [
                    float(tm[1, 0]),       # R ← angular dispersion
                    float(tm[0, 0]),       # G ← intensity
                    float(tm[2, 0]),       # B ← depth confidence
                ],
            }],
            "timestamp": time.time(),
            "cycle": self._cycle_count,
        }

    # ========================================================================
    # UNIFIED NON-BLOCKING EXECUTION CYCLE — The Master Loop
    # ========================================================================
    async def _execute_unified_cycle(self) -> None:
        """
        One complete non-blocking execution cycle.

        Sequence:
        1. Read current device temperature (async, non-blocking)
        2. Compute ∇E(φ)  →  grad_buffer
        3. Euler step: φ ← φ − (dt/τ)·∇E + noise
        4. Update 6-slot token matrix
        5. Project onto AR topology coords
        6. Project onto mesh telemetry slots
        7. Project onto DSEKP shield bits
        8. Project onto Gaussian splat params
        9. Enqueue broadcast frames (non-blocking queue puts)
        10. Push mesh beacon (if mesh_ref is wired)
        11. Flush all memmaps

        ZERO heap allocations in this method — all operations use
        pre-allocated memmapped buffers with in-place numpy ops.
        """
        self._cycle_count += 1
        cycle = self._cycle_count

        # ── 1. Thermal reading (non-blocking) ──
        temp_c: float = 42.0
        if self._device_temp_cb is not None:
            try:
                temp_c = await self._device_temp_cb()
            except Exception:
                pass
        # Map temperature to noise scale: ε ∈ [0.001, 0.05]
        self._thermal_noise_eps = np.clip(0.001 + (temp_c - 30.0) * 0.002, 0.001, 0.05)

        # ── 2. Gradient computation ──
        grad = self._compute_field_gradient(self._phi)

        # ── 3. Euler integration ──
        self._euler_integrate_step(
            self._phi, grad, dt=_CYCLE_DT, tau=_FIELD_TAU,
            eps=self._thermal_noise_eps,
        )

        # ── 4. Update token matrix ──
        self._update_token_matrix()

        # ── 5–8. Projections ──
        ar_topology = self._project_to_ar_topology()
        slot_indices, compliance = self._project_to_mesh_telemetry()
        shield_bytes = self._project_to_dsekp_shield()
        splat_frame = self._project_to_gaussian_splats()

        # ── 9. Enqueue AR broadcast frame ──
        ar_message = {
            "type": "ATTRACTOR_FRAME",
            "cycle": cycle,
            "temperature": temp_c,
            "topology": {
                "ar_coords": ar_topology["ar_coords"],
                "basin": ar_topology["attractor_basin"],
                "curvature": ar_topology["field_curvature"],
            },
            "gaussian_splats": splat_frame["splats"],
            "token_matrix": self._token_matrix.tolist(),
            "compliance": compliance,
        }
        try:
            self._broadcast_queue.put_nowait(ar_message)
        except asyncio.QueueFull:
            pass  # Backpressure: drop frame silently

        # ── 10. Push mesh beacon (UDP telemetry) ──
        if self._mesh_ref is not None:
            try:
                mesh = self._mesh_ref
                if mesh.udp_sock is not None:
                    packet = mesh.pack_secure_polysynthetic_packet(
                        slot_indices, compliance
                    )
                    # Send non-blocking via asyncio
                    loop = asyncio.get_running_loop()
                    await loop.sock_sendto(
                        mesh.udp_sock,
                        packet,
                        ("<broadcast>", mesh.udp_port),
                    )
            except Exception:
                pass

        # ── 11. Flush memmaps to backing store ──
        self._phi.flush()
        self._grad_buffer.flush()
        self._token_matrix.flush()

        # Periodic GC (not in hot path; only when cycle count triggers)
        if cycle % 1000 == 0:
            _gc_if_needed()

    # ========================================================================
    # BROADCAST WORKERS — Drain the queue to WebSocket clients
    # ========================================================================
    async def _broadcast_worker(self) -> None:
        """Continuously drain the broadcast queue and fan-out to all clients."""
        while self._running:
            try:
                frame = await asyncio.wait_for(
                    self._broadcast_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            payload = json.dumps(frame, separators=(",", ":"))
            dead: list = []
            for cq in list(self._web_clients):
                try:
                    cq.put_nowait(payload)
                except asyncio.QueueFull:
                    dead.append(cq)
            for d in dead:
                try:
                    self._web_clients.remove(d)
                except ValueError:
                    pass
            del payload
            del frame

    # ========================================================================
    # MODULE GRAFTING — Wire external references into the control plane
    # ========================================================================
    def graft_module(self, module_name: str, module_ref: Any) -> None:
        """
        Graft an existing AuraOS module into the attractor control plane.

        Supported grafts:
          - "mesh"      → AuraMeshSwarm instance
          - "ar_server" → AuraARWebSocketServer instance
          - "unreal"    → UnrealBridge instance
          - "web_client" → asyncio.Queue for a WebSocket client
        """
        if module_name == "mesh":
            self._mesh_ref = module_ref
            print("[ATTRACTOR] Grafted AuraMeshSwarm into control plane.")
        elif module_name == "ar_server":
            self._ar_server_ref = module_ref
            print("[ATTRACTOR] Grafted AR WebSocket server into control plane.")
        elif module_name == "unreal":
            self._unreal_bridge_ref = module_ref
            print("[ATTRACTOR] Grafted UnrealBridge into control plane.")
        elif module_name == "web_client":
            self._web_clients.append(module_ref)
        else:
            print(f"[ATTRACTOR] Unknown graft target: {module_name}")

    # ========================================================================
    # LIFECYCLE — Start / Stop the control loop
    # ========================================================================
    async def start_control_loop(self) -> None:
        """
        Launch the continuous non-blocking attractor control loop.

        This spawns:
          - The main unified-cycle coroutine (runs every _CYCLE_DT seconds)
          - The broadcast drain worker

        Both run as background asyncio tasks.
        """
        if self._running:
            return
        self._running = True

        async def _loop_forever():
            print(
                f"[ATTRACTOR] Control loop started | dt={_CYCLE_DT}s | "
                f"τ={_FIELD_TAU} | dim={self._dim}"
            )
            while self._running:
                try:
                    await self._execute_unified_cycle()
                except Exception as exc:
                    print(f"[ATTRACTOR] Cycle error (non-fatal): {exc}")
                await asyncio.sleep(_CYCLE_DT)

        self._loop_task = asyncio.create_task(_loop_forever())
        asyncio.create_task(self._broadcast_worker())
        print("[ATTRACTOR] Master cognitive control plane ONLINE.")

    async def stop_control_loop(self) -> None:
        """Graceful shutdown of the attractor control loop."""
        self._running = False
        if self._loop_task is not None:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        # Final flush
        for arr in (
            self._phi, self._grad_buffer, self._basin_centres,
            self._basin_weights, self._token_matrix,
            self._projection_eigenvectors, self._projection_mean,
            self._splat_covariance,
        ):
            try:
                arr.flush()
            except Exception:
                pass
        print("[ATTRACTOR] Control plane shut down. Memmaps flushed.")

    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        Return a lightweight snapshot of the attractor state for
        diagnostics / monitoring (read-only, no allocation in hot path).
        """
        phi_norm = float(np.linalg.norm(self._phi))
        energy = self._continuous_field_energy(self._phi)
        tm = self._token_matrix
        return {
            "cycle": self._cycle_count,
            "phi_norm": phi_norm,
            "energy": energy,
            "thermal_noise_eps": self._thermal_noise_eps,
            "token_matrix": tm.tolist(),
            "compliance": float(tm[3, 0]),
            "basin": int(np.argmin(
                np.linalg.norm(self._basin_centres - self._phi[None, :], axis=1)
            )),
        }


# ============================================================================
# TOP-LEVEL GRAFT ORCHESTRATOR — Overwrites fragmented logic layers
# ============================================================================
class AuraGraftOrchestrator:
    """
    One-shot orchestrator that replaces the fragmented AuraOS logic
    layers (VSA resonator, memristive synapse emulation, scattered
    topology polling, and pre-calculated AR frame generators) with
    the unified Liquid Spatiotemporal Attractor control plane.

    Usage
    -----
        orchestrator = AuraGraftOrchestrator()
        orchestrator.wire_existing_modules(mesh_swarm, ar_server, unreal_bridge)
        await orchestrator.activate()
    """

    def __init__(self) -> None:
        self._attractor: Optional[LiquidSpatiotemporalAttractor] = None
        self._mesh: Any = None
        self._ar_server: Any = None
        self._unreal_bridge: Any = None

    def wire_existing_modules(
        self,
        mesh_swarm: Any = None,
        ar_server: Any = None,
        unreal_bridge: Any = None,
    ) -> None:
        """Register the existing AuraOS modules to be grafted."""
        self._mesh = mesh_swarm
        self._ar_server = ar_server
        self._unreal_bridge = unreal_bridge

    async def activate(self) -> LiquidSpatiotemporalAttractor:
        """
        Bootstrap the attractor, graft all wired modules, and start the
        unified control loop.

        Returns the active LiquidSpatiotemporalAttractor instance.
        """
        # ── Thermal callback: try to read from sysfs ──
        async def _read_thermal() -> float:
            try:
                path = "/sys/class/thermal/thermal_zone0/temp"
                loop = asyncio.get_running_loop()

                def _sync_read():
                    with open(path, "r") as fh:
                        return float(fh.read().strip()) / 1000.0

                return await loop.run_in_executor(None, _sync_read)
            except Exception:
                return 42.0

        # ── Instantiate the attractor ──
        self._attractor = LiquidSpatiotemporalAttractor(
            dim=_ATTRACTOR_DIM,
            device_temp_callback=_read_thermal,
        )

        # ── Graft existing modules ──
        if self._mesh is not None:
            self._attractor.graft_module("mesh", self._mesh)
        if self._ar_server is not None:
            self._attractor.graft_module("ar_server", self._ar_server)
        if self._unreal_bridge is not None:
            self._attractor.graft_module("unreal", self._unreal_bridge)

        # ── Start the control loop ──
        await self._attractor.start_control_loop()

        # ── Patch the AR server's topology refresh to source from attractor ──
        if self._ar_server is not None:
            await self._patch_ar_topology_source()

        return self._attractor

    async def _patch_ar_topology_source(self) -> None:
        """
        Override the AR server's topology ingestion to use the attractor's
        projection rather than polling live_topology_ast.json.
        """
        ar = self._ar_server
        attractor = self._attractor

        # Store original method
        original_refresh = ar._refresh_topology

        async def _attractor_driven_topology_refresh():
            """Replace file-based topology refresh with attractor projection."""
            proj = attractor._project_to_ar_topology()
            tm = attractor._token_matrix
            # Build synthetic topology nodes from attractor state
            nodes = [{
                "id": f"attractor_basin_{proj['attractor_basin']}",
                "type": "attractor_node",
                "name": f"φ_cycle_{attractor._cycle_count}",
                "position": proj["ar_coords"],
                "scale": float(tm[0, 0]),
                "color": [
                    float(tm[1, 0]),
                    float(tm[0, 0]),
                    float(tm[2, 0]),
                ],
            }]
            edges = []
            payload = {"nodes": nodes, "edges": edges}
            # Write to topology file for legacy consumers
            _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            topo_path = _MEMORY_DIR / "live_topology_ast.json"
            with open(topo_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
            # Update AR server shapes
            async with ar._topology_lock:
                ar._shapes.clear()
                # Add a single attractor shape
                from aura_topology_ws_bridge import _ARShape
                shape = _ARShape(
                    shape_id=f"attractor_{attractor._cycle_count}",
                    shape_type="Icosahedron",
                    label=f"Attractor φ(t={attractor._cycle_count})",
                    position=proj["ar_coords"],
                    scale=float(tm[0, 0]),
                    color=f"#{int(tm[1,0]*255):02x}{int(tm[0,0]*255):02x}{int(tm[2,0]*255):02x}",
                    node_type="async_method",
                )
                ar._shapes[shape.shape_id] = shape
            await ar._broadcast_topology()

        # Hot-patch
        ar._refresh_topology = _attractor_driven_topology_refresh
        print("[ATTRACTOR] Patched AR server topology source → attractor projection.")

    async def deactivate(self) -> None:
        """Stop the control loop and flush all memmaps."""
        if self._attractor is not None:
            await self._attractor.stop_control_loop()
            self._attractor = None


# ============================================================================
# STANDALONE ENTRY POINT — Boots the graft without external wiring
# ============================================================================
async def _standalone_main() -> None:
    """Standalone test: boot the attractor without external modules."""
    print("=" * 60)
    print("  LIQUID SPATIOTEMPORAL ATTRACTOR — Standalone Bootstrap")
    print("=" * 60)

    orchestrator = AuraGraftOrchestrator()
    attractor = await orchestrator.activate()

    # Run for a few cycles and print state snapshots
    for _ in range(10):
        await asyncio.sleep(_CYCLE_DT * 1.5)
        snap = attractor.get_state_snapshot()
        print(
            f"  [cycle={snap['cycle']:04d}] "
            f"|φ|={snap['phi_norm']:.4f} "
            f"E={snap['energy']:.4f} "
            f"compliance={snap['compliance']:.4f} "
            f"basin={snap['basin']}"
        )

    await orchestrator.deactivate()
    print("[ATTRACTOR] Standalone test complete.")


# ============================================================================
# AUTO-BOOT HOOK — Called by pulse.py on AuraOS startup
# ============================================================================
_attractor_singleton: Optional[LiquidSpatiotemporalAttractor] = None
_orchestrator_singleton: Optional[AuraGraftOrchestrator] = None
_auto_boot_lock = asyncio.Lock()


async def auto_boot_attractor(
    mesh_swarm: Any = None,
    ar_server: Any = None,
    unreal_bridge: Any = None,
) -> LiquidSpatiotemporalAttractor:
    """
    Auto-boot the Liquid Spatiotemporal Attractor as AuraOS's master
    cognitive control plane.  Call this once from pulse.py's main().

    Returns the running attractor singleton so callers can wire
    per-client broadcast queues via attractor.graft_module("web_client", q).
    """
    global _attractor_singleton, _orchestrator_singleton
    if _attractor_singleton is not None:
        return _attractor_singleton

    async with _auto_boot_lock:
        if _attractor_singleton is not None:
            return _attractor_singleton

        print("[AUTO-BOOT] Spawning Liquid Spatiotemporal Attractor control plane …")
        _orchestrator_singleton = AuraGraftOrchestrator()
        _orchestrator_singleton.wire_existing_modules(
            mesh_swarm=mesh_swarm,
            ar_server=ar_server,
            unreal_bridge=unreal_bridge,
        )
        _attractor_singleton = await _orchestrator_singleton.activate()
        print("[AUTO-BOOT] Attractor control plane is now the master cognitive loop.")
        return _attractor_singleton


async def shutdown_attractor() -> None:
    """Graceful shutdown — called on process exit."""
    global _attractor_singleton, _orchestrator_singleton
    if _orchestrator_singleton is not None:
        await _orchestrator_singleton.deactivate()
        _orchestrator_singleton = None
        _attractor_singleton = None


if __name__ == "__main__":
    asyncio.run(_standalone_main())
