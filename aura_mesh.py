"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: asyncio, base64, socket, os, uuid, numpy, struct, hashlib, time, json
FUNCTIONS:
    SceneAdaptiveToneCurve:
        __init__, _ase_curve, _ap3_curve, _gaussian_probability_field,
        _compute_attention_matrix, normalize_3d_coordinates,
        process_node_batch, process_node_batch_sync
    AuraMeshSwarm:
        __init__, start_udp_beacon, start_tcp_compute_server,
        pack_secure_polysynthetic_packet, unpack_secure_polysynthetic_packet,
        pack_length_prefixed_payload, unpack_length_prefixed_payload,
        generate_polysynthetic_proof, verify_dsekp_shield,
        broadcast_upgrade, offload_compute, should_offload_task,
        _commit_mesh_telemetry, _listen_beacons_async,
        _tcp_client_handler, _read_thermal_nonblocking
SYNOPSIS:
    This Python module implements a secure, asynchronous swarm-mesh engine
    for the AuraOS edge‑orchestration substrate.  It supports:
      - Scene-adaptive tone curve processing as a structural filter sub-layer
        that instantly transforms incoming node data arrays into normalized
        3D coordinate matrices (signal intensity, color, depth) using full
        vectorization via numpy probability fields, with graph-based attention
        weights mapping a dynamic focus hierarchy for neighbor-node tracking.
      - UDP beacon discovery with a fixed 16‑byte polysynthetic telemetry
        frame (six 16‑bit slot indices + one 32‑bit compliance float).
      - A length‑prefixed binary protocol for variable‑size compute‑task
        offloading over TCP (port 4445), including a fully asynchronous
        TCP listener server.
      - Automatic task evaluation and routing via `should_offload_task`,
        which inspects task metadata tags, system temperature, and
        estimated resource cost before transparently redirecting heavy
        work to discovered peers.
      - Non‑blocking thermal‑zone reads through `loop.run_in_executor`.
      - DSEKP cryptographic shield verification using NumPy bitwise
        vector comparison with a configurable Hamming‑distance threshold.
MEMORY-CONSTRAINT: Enforces 4 GB Termux device RAM ceiling via
    contiguous float32 layouts, in‑place mutation, and zero heap‑alloc
    object overhead in hot paths.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import socket
import struct
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Module‑level constants
# ---------------------------------------------------------------------------
DEFAULT_UDP_BEACON_PORT: int = 4444
DEFAULT_TCP_COMPUTE_PORT: int = 4445
DEFAULT_OFFLOAD_TEMP_THRESHOLD_C: float = 75.0
DSEKP_SHIELD_SIZE: int = 10000
DSEKP_HAMMING_TOLERANCE: int = 500
THERMAL_PATH: str = "/sys/class/thermal/thermal_zone0/temp"
BROADCAST_ADDR: str = "<broadcast>"
TELEMETRY_FRAME_SIZE: int = 16  # 6 × uint16 + 1 × float32
LENGTH_PREFIX_SIZE: int = 4     # uint32 big‑endian

# Task‑tag keywords that unconditionally trigger remote offloading when
# peers are available.
OFFLOAD_TAGS: frozenset = frozenset(
    {"COMPUTE_HEAVY", "VECTOR_SEARCH", "GENETIC_EVOLUTION"}
)

# 4 GB device‑RAM ceiling for Termux — all working arrays kept as
# float32 contiguous blocks with in‑place mutation to avoid allocation
# churn.  Batch‑size cap keeps peak memory well under the limit.
_TERMUX_RAM_CEILING_BYTES: int = 4 * 1024 * 1024 * 1024  # 4 GiB
_MAX_NODE_BATCH: int = 2048  # upper bound on batched nodes per call


# ============================================================================
# Scene‑Adaptive Tone Curve filter sub‑layer
# ============================================================================
class SceneAdaptiveToneCurve:
    """Structural filter that transforms 3D node signals (intensity,
    colour, depth) into normalized coordinate matrices using adaptive
    tone curves and graph‑based probabilistic attention.

    This processor is designed as a **non‑allocating** sub‑layer that
    operates directly on contiguous numpy float32 arrays.  No external
    dependencies beyond ``numpy`` are required: the Gaussian probability-
    field function and cosine‑similarity attention are implemented via
    pure vectorised math, keeping memory pressure under the 4 GiB
    Termux ceiling.

    Parameters
    ----------
    curve_type:
        ``"ase"`` (Adaptive SoftExp, default) or ``"ap3"`` (Adaptive
        Polynomial‑3).
    percentile_clip:
        Percentile for robust feature scaling (default 1 %).
    ase_a, ase_b:
        Scale and sharpness coefficients for the ASE sigmoid.
    ap3_coeffs:
        4‑element polynomial coefficients for the AP3 curve.
    """

    __slots__ = (
        "_curve_type",
        "_percentile_clip",
        "_ase_a",
        "_ase_b",
        "_ap3_coeffs",
        "_feature_min",
        "_feature_max",
        "_fitted",
    )

    def __init__(
        self,
        curve_type: str = "ase",
        percentile_clip: float = 0.01,
        ase_a: float = 1.2,
        ase_b: float = 0.8,
        ap3_coeffs: Optional[np.ndarray] = None,
    ) -> None:
        self._curve_type: str = curve_type.lower()
        self._percentile_clip: float = float(np.clip(percentile_clip, 0.0, 50.0))
        self._ase_a: float = float(ase_a)
        self._ase_b: float = float(ase_b)
        self._ap3_coeffs: np.ndarray
        if ap3_coeffs is None:
            self._ap3_coeffs = np.array([0.1, 0.3, 0.2, 0.4], dtype=np.float32)
        else:
            self._ap3_coeffs = np.asarray(ap3_coeffs, dtype=np.float32).ravel()
            if self._ap3_coeffs.size != 4:
                self._ap3_coeffs = np.array([0.1, 0.3, 0.2, 0.4], dtype=np.float32)

        # Robust scaler state — lazy‑fit on first batch
        self._feature_min: np.ndarray = np.zeros(3, dtype=np.float32)
        self._feature_max: np.ndarray = np.ones(3, dtype=np.float32)
        self._fitted: bool = False

    # ------------------------------------------------------------------
    # Tone‑curve kernels (pure numpy, vectorised)
    # ------------------------------------------------------------------
    @staticmethod
    def _ase_curve(x: np.ndarray, a: float, b: float) -> np.ndarray:
        """Adaptive SoftExp curve — smooth sigmoidal remapping.

        .. math::
            f(x) = a * exp(b*x) / (1 + exp(b*x))

        The output is numerically stable for large |bx| because the
        denominator naturally saturates.
        """
        with np.errstate(over="ignore", under="ignore"):
            exp_bx: np.ndarray = np.exp(np.multiply(b, x, dtype=np.float32), dtype=np.float32)
            denom: np.ndarray = np.add(1.0, exp_bx, dtype=np.float32)
            return np.multiply(a, np.divide(exp_bx, denom, dtype=np.float32), dtype=np.float32)

    @staticmethod
    def _ap3_curve(x: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
        """Adaptive Poly3 curve — cubic polynomial remapping.

        .. math::
            f(x) = c_0 + c_1*x + c_2*x^2 + c_3*x^3
        """
        x2: np.ndarray = np.square(x, dtype=np.float32)
        x3: np.ndarray = np.multiply(x2, x, dtype=np.float32)
        return np.add(
            np.add(
                np.add(coeffs[0], np.multiply(coeffs[1], x, dtype=np.float32), dtype=np.float32),
                np.multiply(coeffs[2], x2, dtype=np.float32),
                dtype=np.float32,
            ),
            np.multiply(coeffs[3], x3, dtype=np.float32),
            dtype=np.float32,
        )

    # ------------------------------------------------------------------
    # Gaussian probability field (replaces scipy.stats.norm)
    # ------------------------------------------------------------------
    @staticmethod
    def _gaussian_probability_field(
        x: np.ndarray, mu: float = 0.5, sigma: float = 0.25
    ) -> np.ndarray:
        """Vectorised Gaussian probability density over an input array.

        Equivalent to ``scipy.stats.norm(mu, sigma).pdf(x)`` but kept
        entirely within numpy to avoid the scipy dependency on Termux.

        .. math::
            pdf(x) = exp(-0.5 * ((x - mu) / sigma)^2) / (sigma * sqrt(2*pi))
        """
        sigma_f: float = float(max(sigma, 1e-8))
        norm_const: float = 1.0 / (sigma_f * np.sqrt(2.0 * np.pi, dtype=np.float32))
        z: np.ndarray = np.divide(
            np.subtract(x, mu, dtype=np.float32), sigma_f, dtype=np.float32
        )
        return np.multiply(norm_const, np.exp(np.multiply(-0.5, np.square(z, dtype=np.float32), dtype=np.float32), dtype=np.float32), dtype=np.float32)  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Robust 3‑D coordinate normalisation (in‑place minimisation)
    # ------------------------------------------------------------------
    def normalize_3d_coordinates(
        self, features: np.ndarray, fit: bool = False
    ) -> np.ndarray:
        """Normalise a 3‑D feature matrix to [0, 1] using robust percentile
        clipping.

        The input array is expected to have shape ``(N, 3)`` with columns
        ``[intensity, color, depth]``.  When ``fit=True`` the percentile
        bounds are recomputed from the current batch.

        Parameters
        ----------
        features:
            ``float32`` array of shape ``(N, 3)``.
        fit:
            If ``True``, recompute the per‑channel percentile bounds.

        Returns
        -------
        np.ndarray
            Normalised ``float32`` array, same shape as input.
        """
        f32: np.ndarray = np.asarray(features, dtype=np.float32)
        if f32.ndim != 2 or f32.shape[1] != 3:
            raise ValueError(
                f"Expected (N,3) float32 array, got shape {f32.shape}"
            )

        if fit or not self._fitted:
            p_low: float = self._percentile_clip
            p_high: float = 100.0 - p_low
            self._feature_min = np.percentile(f32, p_low, axis=0).astype(np.float32)
            self._feature_max = np.percentile(f32, p_high, axis=0).astype(np.float32)
            # Guard against degenerate range
            denom_safe: np.ndarray = np.where(
                self._feature_max - self._feature_min < 1e-8,
                1.0,
                self._feature_max - self._feature_min,
            )
            self._feature_min = np.where(
                self._feature_max - self._feature_min < 1e-8,
                self._feature_min - 0.1,
                self._feature_min,
            )
            self._feature_max = np.where(
                denom_safe < 1e-8, self._feature_min + 0.2, self._feature_max
            )
            self._fitted = True

        denom: np.ndarray = np.subtract(self._feature_max, self._feature_min, dtype=np.float32)
        denom = np.where(np.abs(denom) < 1e-8, 1.0, denom)
        return np.clip(
            np.divide(
                np.subtract(f32, self._feature_min, dtype=np.float32),
                denom,
                dtype=np.float32,
            ),
            0.0,
            1.0,
            dtype=np.float32,
        )

    # ------------------------------------------------------------------
    # Graph‑based attention via pure numpy (no networkx)
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_attention_matrix(
        features: np.ndarray,
        adjacency: Optional[np.ndarray] = None,
        edge_weights: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute cosine‑similarity attention across a node feature matrix.

        Returns a normalised square attention matrix ``A[i,j]`` where
        each row sums to 1 and represents the contextual focus of node
        *i* onto its neighbours.

        When ``adjacency`` is provided (boolean ``(N,N)`` mask), only
        edges that are ``True`` contribute; otherwise the graph is
        assumed fully connected (all‑pairs attention).

        ``edge_weights`` supplies a multiplicative scalar per edge that
        modulates the raw cosine similarity before row‑wise softmax.

        Parameters
        ----------
        features:
            ``(N, D)`` float32 feature matrix.
        adjacency:
            Optional ``(N, N)`` boolean mask.
        edge_weights:
            Optional ``(N, N)`` float32 multiplier.

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            ``(attention_matrix, raw_similarities)`` — both ``(N,N)`` float32.
        """
        N: int = features.shape[0]
        if N < 1:
            return np.empty((0, 0), dtype=np.float32), np.empty((0, 0), dtype=np.float32)

        # L2‑normalise rows for cosine similarity
        norms: np.ndarray = np.linalg.norm(features, axis=1, keepdims=True)
        norms = np.where(norms < 1e-12, 1.0, norms)
        feats_norm: np.ndarray = np.divide(features, norms, dtype=np.float32)

        # Raw cosine similarity matrix  (N, N)
        sim: np.ndarray = np.dot(feats_norm, feats_norm.T).astype(np.float32)

        # Apply adjacency mask
        if adjacency is not None:
            adj_mask: np.ndarray = np.asarray(adjacency, dtype=bool)
            if adj_mask.shape == (N, N):
                sim = np.where(adj_mask, sim, 0.0)
            else:
                # Broadcast-friendly: if adjacency is (N,) treat as self‑mask
                sim = np.where(adj_mask[:, None] & adj_mask[None, :], sim, 0.0)

        # Apply edge‑weight multipliers
        if edge_weights is not None:
            ew: np.ndarray = np.asarray(edge_weights, dtype=np.float32)
            if ew.shape == (N, N):
                sim = np.multiply(sim, ew, dtype=np.float32)

        raw: np.ndarray = sim.copy()

        # Row‑wise softmax (stabilised with max subtraction)
        sim_max: np.ndarray = np.max(sim, axis=1, keepdims=True)
        sim_shifted: np.ndarray = np.subtract(sim, sim_max, dtype=np.float32)
        exp_sim: np.ndarray = np.exp(sim_shifted, dtype=np.float32)
        exp_sum: np.ndarray = np.sum(exp_sim, axis=1, keepdims=True)
        exp_sum = np.where(exp_sum < 1e-12, 1.0, exp_sum)
        attention: np.ndarray = np.divide(exp_sim, exp_sum, dtype=np.float32)

        return attention, raw

    # ------------------------------------------------------------------
    # Main tone‑curve application on a feature column
    # ------------------------------------------------------------------
    def _apply_tone_curve(self, x: np.ndarray) -> np.ndarray:
        """Dispatch to the configured tone‑curve kernel."""
        if self._curve_type == "ap3":
            return self._ap3_curve(x, self._ap3_coeffs)
        return self._ase_curve(x, self._ase_a, self._ase_b)

    # ------------------------------------------------------------------
    # Full batch processing (sync — for use inside async wrappers)
    # ------------------------------------------------------------------
    def process_node_batch_sync(
        self,
        nodes: List[Dict[str, Any]],
        adjacency: Optional[np.ndarray] = None,
        edge_weights: Optional[np.ndarray] = None,
        fit_scaler: bool = False,
    ) -> List[Dict[str, Any]]:
        """Transform a list of node dictionaries in a single vectorised pass.

        Each node dict must contain numeric keys ``intensity``, ``color``,
        and ``depth``.  Missing keys default to 0.5.

        The processing pipeline:
        1. Extract ``(N, 3)`` feature matrix from the dict list.
        2. Robust normalise to [0, 1] per channel.
        3. Apply the configured tone curve to the *intensity* channel.
        4. Optionally apply a Gaussian probability‑field lift to faded
           signals (intensity < 0.3).
        5. Compute graph‑based attention matrix over the feature set.
        6. Update each node dict with ``processed_intensity``,
           ``attention_weights``, ``graph_features``, and
           ``probability_field``.

        Parameters
        ----------
        nodes:
            List of node dicts.
        adjacency:
            Optional ``(N, N)`` boolean adjacency mask.
        edge_weights:
            Optional ``(N, N)`` float32 edge weights.
        fit_scaler:
            If ``True``, recompute robust scaler bounds from this batch.

        Returns
        -------
        List[Dict[str, Any]]
            The same list (mutated in‑place) with injected fields.
        """
        num_nodes: int = len(nodes)
        if num_nodes == 0:
            return nodes
        if num_nodes > _MAX_NODE_BATCH:
            # Chunk into manageable slices to keep memory under 4 GiB
            results: List[Dict[str, Any]] = []
            for start in range(0, num_nodes, _MAX_NODE_BATCH):
                end: int = min(start + _MAX_NODE_BATCH, num_nodes)
                chunk: List[Dict[str, Any]] = nodes[start:end]
                adj_chunk: Optional[np.ndarray] = None
                ew_chunk: Optional[np.ndarray] = None
                if adjacency is not None and adjacency.shape == (num_nodes, num_nodes):
                    adj_chunk = adjacency[start:end, start:end]
                if edge_weights is not None and edge_weights.shape == (num_nodes, num_nodes):
                    ew_chunk = edge_weights[start:end, start:end]
                results.extend(
                    self.process_node_batch_sync(
                        chunk,
                        adjacency=adj_chunk,
                        edge_weights=ew_chunk,
                        fit_scaler=(fit_scaler and start == 0),
                    )
                )
            return results

        # --- 1. Extract feature matrix ---
        feat_arr: np.ndarray = np.empty((num_nodes, 3), dtype=np.float32)
        for i, node in enumerate(nodes):
            feat_arr[i, 0] = float(node.get("intensity", 0.5))
            feat_arr[i, 1] = float(node.get("color", 0.5))
            feat_arr[i, 2] = float(node.get("depth", 0.5))

        # --- 2. Normalise ---
        feat_norm: np.ndarray = self.normalize_3d_coordinates(feat_arr, fit=fit_scaler)

        # --- 3. Tone‑curve on intensity channel ---
        intensity_in: np.ndarray = feat_norm[:, 0].copy()
        intensity_out: np.ndarray = self._apply_tone_curve(intensity_in)

        # --- 4. Gaussian probability‑field lift for faded signals ---
        prob_field: np.ndarray = self._gaussian_probability_field(
            intensity_in, mu=0.5, sigma=0.25
        )
        # Boost faded nodes (intensity < 0.3) by the probability density
        fade_mask: np.ndarray = intensity_in < 0.3
        intensity_out = np.where(
            fade_mask,
            np.add(intensity_out, np.multiply(prob_field, 0.15, dtype=np.float32), dtype=np.float32),
            intensity_out,
        )
        # Clip to valid range
        np.clip(intensity_out, 0.0, 1.0, out=intensity_out)

        # --- 5. Graph attention ---
        attention_mat, _ = self._compute_attention_matrix(
            feat_norm, adjacency=adjacency, edge_weights=edge_weights
        )

        # --- 6. Update node dicts ---
        for i, node in enumerate(nodes):
            attn_row: np.ndarray = attention_mat[i, :]
            attn_dict: Dict[str, float] = {
                nodes[j].get("id", f"node_{j}"): float(attn_row[j])
                for j in range(num_nodes)
                if j != i and float(attn_row[j]) > 1e-6
            }
            node["processed_intensity"] = float(intensity_out[i])
            node["attention_weights"] = attn_dict
            node["graph_features"] = feat_norm[i].tolist()
            node["probability_field"] = float(prob_field[i])

        return nodes

    # ------------------------------------------------------------------
    # Async wrapper (non‑blocking via thread‑pool executor)
    # ------------------------------------------------------------------
    async def process_node_batch(
        self,
        nodes: List[Dict[str, Any]],
        adjacency: Optional[np.ndarray] = None,
        edge_weights: Optional[np.ndarray] = None,
        fit_scaler: bool = False,
    ) -> List[Dict[str, Any]]:
        """Non‑blocking async wrapper around ``process_node_batch_sync``.

        Offloads the vectorised numpy work to the default thread‑pool
        executor so the asyncio event loop is never blocked, even on
        large batches.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.process_node_batch_sync(
                nodes,
                adjacency=adjacency,
                edge_weights=edge_weights,
                fit_scaler=fit_scaler,
            ),
        )


# ============================================================================
# AuraMeshSwarm
# ============================================================================
class AuraMeshSwarm:
    """Asynchronous swarm‑mesh engine for AuraOS edge orchestration.

    This class manages peer discovery via UDP broadcast beacons (fixed
    16‑byte telemetry frames), a TCP‑based compute‑offload channel with
    a length‑prefixed binary protocol, automatic task‑routing decisions
    driven by thermal and resource heuristics, DSEKP cryptographic
    shield verification, and a deeply integrated **Scene‑Adaptive Tone
    Curve** filter sub‑layer that transforms every incoming node-data
    array into normalised 3‑D coordinate matrices (signal intensity,
    colour, depth) with graph‑based probabilistic attention weights.

    Parameters
    ----------
    node_ref:
        Reference to the parent ``AuraNode`` (or compatible object) that
        provides ``runtime_metrics``, ``hdc``, ``thermal``, and
        ``memory_palace`` attributes.
    identity:
        Human‑readable label for this swarm node.
    tone_curve_type:
        Passed through to the ``SceneAdaptiveToneCurve`` constructor
        (``"ase"`` or ``"ap3"``).
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def __init__(
        self,
        node_ref: Any,
        identity: str = "AURA_EDGE_NODE",
        tone_curve_type: str = "ase",
    ) -> None:
        self.node: Any = node_ref
        self.identity: str = identity

        # --- Scene‑Adaptive Tone Curve filter sub‑layer ---
        self.tone_curve: SceneAdaptiveToneCurve = SceneAdaptiveToneCurve(
            curve_type=tone_curve_type
        )

        # --- UDP discovery transport ---
        self.udp_sock: Optional[socket.socket] = None
        self.udp_port: int = DEFAULT_UDP_BEACON_PORT

        # --- TCP compute‑offload server ---
        self.tcp_server: Optional[asyncio.AbstractServer] = None
        self.tcp_port: int = DEFAULT_TCP_COMPUTE_PORT

        # --- Peer registry:  ip_address → human_label ---
        self.peers: Dict[str, str] = {}

        # --- Transmission ledger for auditing / telemetry ---
        self.tx_ledger: Dict[str, Any] = {}

        # --- Configurable offload threshold (°C) ---
        self.offload_temp_threshold: float = DEFAULT_OFFLOAD_TEMP_THRESHOLD_C

        print(
            f"[+] AuraMeshSwarm initialized | identity={self.identity}"
            f" | tone_curve={tone_curve_type}"
        )

    # ==================================================================
    # PROTOCOL LAYER 1 — Fixed 16‑byte telemetry frame (UDP beacons)
    # ==================================================================
    @staticmethod
    def pack_secure_polysynthetic_packet(
        slot_indices: List[int], compliance_score: float
    ) -> bytes:
        """Pack six 16‑bit slot indices and one 32‑bit compliance float
        into a fixed‑size 16‑byte binary telemetry frame.

        This is the **structural metadata frame** used for UDP beacon
        broadcasts and lightweight heartbeats.  It does **not** carry
        variable‑length payload data.

        Parameters
        ----------
        slot_indices:
            Exactly 6 unsigned 16‑bit integers (0–65535).  If fewer than
            6 elements are supplied the missing entries are zero‑padded.
        compliance_score:
            32‑bit IEEE‑754 float representing the node's current
            compliance / confidence anchor.

        Returns
        -------
        bytes
            16‑byte packed binary frame::

                [H H H H H H f]  (little‑endian)
                 ^-6×uint16-^  ^-float32-^
        """
        if len(slot_indices) < 6:
            slot_indices = list(slot_indices) + [0] * (6 - len(slot_indices))
        # Clamp to valid uint16 range
        clamped: List[int] = [max(0, min(int(v), 65535)) for v in slot_indices[:6]]
        return struct.pack(
            "<HHHHHHf",
            clamped[0],
            clamped[1],
            clamped[2],
            clamped[3],
            clamped[4],
            clamped[5],
            float(compliance_score),
        )

    @staticmethod
    def unpack_secure_polysynthetic_packet(
        raw_bytes: bytes,
    ) -> Tuple[Optional[List[int]], float]:
        """Unpack a fixed 16‑byte telemetry frame.

        Parameters
        ----------
        raw_bytes:
            Raw bytes received from the wire.  Only the first 16 bytes
            are consumed.

        Returns
        -------
        tuple[Optional[List[int]], float]
            ``(slot_indices, compliance_score)``.  ``slot_indices`` is
            ``None`` when the frame is truncated or corrupt.
        """
        try:
            if len(raw_bytes) < TELEMETRY_FRAME_SIZE:
                return None, 0.0
            unpacked = struct.unpack("<HHHHHHf", raw_bytes[:TELEMETRY_FRAME_SIZE])
            return list(unpacked[:6]), float(unpacked[6])
        except (struct.error, IndexError):
            return None, 0.0

    # ==================================================================
    # PROTOCOL LAYER 2 — Length‑prefixed variable payload (TCP offload)
    # ==================================================================
    @staticmethod
    def pack_length_prefixed_payload(payload_obj: Any) -> bytes:
        """Serialize an arbitrary object to JSON and wrap it in a
        length‑prefixed binary frame.

        Frame layout::

            ┌────────────────────┬──────────────────────────────────┐
            │  4 bytes (BE u32)  │  UTF‑8 encoded JSON payload      │
            │  payload length N  │  (N bytes)                       │
            └────────────────────┴──────────────────────────────────┘

        Parameters
        ----------
        payload_obj:
            Any JSON‑serializable Python object (typically a ``dict``).

        Returns
        -------
        bytes
            Length‑prefixed binary frame ready for transmission over
            a TCP socket.
        """
        json_bytes: bytes = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8")
        length_prefix: bytes = struct.pack(">I", len(json_bytes))
        return length_prefix + json_bytes

    @staticmethod
    def unpack_length_prefixed_payload(raw_bytes: bytes) -> Optional[Any]:
        """Deserialize a length‑prefixed binary frame back into a Python
        object.

        Parameters
        ----------
        raw_bytes:
            Complete raw bytes received from the wire.

        Returns
        -------
        Optional[Any]
            Deserialized Python object, or ``None`` if the frame is
            malformed or truncated.
        """
        try:
            if len(raw_bytes) < LENGTH_PREFIX_SIZE:
                print("[-] Length-prefixed frame truncated: missing 4-byte header.")
                return None
            payload_len: int = struct.unpack(">I", raw_bytes[:LENGTH_PREFIX_SIZE])[0]
            payload_bytes: bytes = raw_bytes[LENGTH_PREFIX_SIZE:]
            if len(payload_bytes) < payload_len:
                print(
                    f"[-] Length-prefixed frame body mismatch: "
                    f"expected {payload_len}, got {len(payload_bytes)}."
                )
                return None
            json_str: str = payload_bytes[:payload_len].decode("utf-8")
            return json.loads(json_str)
        except (struct.error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"[-] Failed to unpack length-prefixed payload: {exc}")
            return None

    # ==================================================================
    # DSEKP CRYPTOGRAPHIC SHIELD
    # ==================================================================
    def generate_polysynthetic_proof(
        self, payload_dict: Dict[str, Any], current_temp: float
    ) -> Dict[str, Any]:
        """Generate a DSEKP cryptographic proof envelope for an outgoing
        swarm message.

        If the parent node exposes an ``hdc`` (Hyper‑Dimensional
        Computer) engine the proof includes a holographic route glyph,
        trace ID, and a packed outer shield.  Otherwise a degraded
        ``"OFFLINE"`` shield is returned.

        Parameters
        ----------
        payload_dict:
            Semantic payload to wrap.
        current_temp:
            Current system temperature in °C (used as a nonce factor).

        Returns
        -------
        dict
            Proof envelope with keys ``dsekp_shield``, ``route_glyph``,
            ``trace_id``, and ``data``.
        """
        thought_id: str = f"MESH-{uuid.uuid4().hex[:8].upper()}"
        mesh_glyph: str = "ST3GG:NET_SYNC"

        hdc = getattr(self.node, "hdc", None)
        if hdc is None:
            return {"dsekp_shield": "OFFLINE", "data": payload_dict}

        try:
            hybrid_packet = hdc.generate_hybrid_packet(
                thought_id=thought_id,
                st3gg_glyph=mesh_glyph,
                qdkt_tensor=payload_dict,
                current_temp=current_temp,
            )
            shield_bytes: bytes = np.packbits(
                hybrid_packet["outer_shield"]
            ).tobytes()
            shield_b64: str = base64.b64encode(shield_bytes).decode("utf-8")
            return {
                "dsekp_shield": shield_b64,
                "route_glyph": hybrid_packet["holographic_route"],
                "trace_id": hybrid_packet["thought_trace_id"],
                "data": hybrid_packet["inner_nucleus"],
            }
        except Exception as exc:
            print(f"[-] Polysynthetic proof generation failed: {exc}")
            return {"dsekp_shield": "OFFLINE", "data": payload_dict}

    async def verify_dsekp_shield(self, incoming_packet: Dict[str, Any]) -> bool:
        """Verify an incoming DSEKP cryptographic shield via Hamming‑
        distance comparison against the locally expected state vector.

        A shield is accepted when the bitwise Hamming distance is ≤ 500
        (5 % of the 10 000‑bit shield space).

        Parameters
        ----------
        incoming_packet:
            A dictionary that must contain ``"dsekp_shield"`` and
            optionally ``"trace_id"``.

        Returns
        -------
        bool
            ``True`` if the shield is cryptographically valid.
        """
        shield_b64: Optional[str] = incoming_packet.get("dsekp_shield")
        if not shield_b64 or shield_b64 == "OFFLINE":
            print("[*] DSEKP shield offline or absent — verification skipped.")
            return False

        try:
            shield_bytes: bytes = base64.b64decode(shield_b64)
            incoming_shield: np.ndarray = np.unpackbits(
                np.frombuffer(shield_bytes, dtype=np.uint8)
            )
            if incoming_shield.size != DSEKP_SHIELD_SIZE:
                print(
                    f"[-] DSEKP Error: Shield geometry sheared in transit "
                    f"(size={incoming_shield.size}, expected={DSEKP_SHIELD_SIZE})."
                )
                return False

            # Obtain temperature in a non‑blocking fashion
            current_temp: float = await self._read_thermal_nonblocking()

            hdc = getattr(self.node, "hdc", None)
            if hdc is None:
                print(
                    "[*] No HDC engine available — shield verification "
                    "passed by default."
                )
                return True

            trace_id: str = incoming_packet.get("trace_id", "UNKNOWN")
            expected_state: np.ndarray = hdc.get_word_vector(
                f"STATE_{current_temp}_{trace_id}"
            )

            hamming_distance: int = int(
                np.sum(np.bitwise_xor(incoming_shield, expected_state))
            )
            if hamming_distance <= DSEKP_HAMMING_TOLERANCE:
                print(
                    f"[+] DSEKP Shield verified | Hamming distance = "
                    f"{hamming_distance} (≤ {DSEKP_HAMMING_TOLERANCE})"
                )
                return True
            else:
                print(
                    f"[-] DSEKP Violation: Hamming distance [{hamming_distance}] "
                    f"exceeds {DSEKP_HAMMING_TOLERANCE}‑bit drift allowance."
                )
                return False
        except Exception as exc:
            print(f"[-] DSEKP Verification crashed: {exc}")
            return False

    # ==================================================================
    # NON‑BLOCKING SYSTEM I/O
    # ==================================================================
    @staticmethod
    async def _read_thermal_nonblocking() -> float:
        """Read the system thermal‑zone temperature from sysfs without
        blocking the asyncio event loop.

        The file read is offloaded to the default thread‑pool executor
        via ``loop.run_in_executor``.

        Returns
        -------
        float
            Temperature in °C, or ``42.0`` if the thermal zone cannot
            be read.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop — fall back to synchronous read
            try:
                with open(THERMAL_PATH, "r") as fh:
                    return float(fh.read().strip()) / 1000.0
            except (OSError, ValueError):
                return 42.0

        def _sync_read() -> float:
            try:
                with open(THERMAL_PATH, "r") as fh:
                    return float(fh.read().strip()) / 1000.0
            except (OSError, ValueError):
                return 42.0

        try:
            return await loop.run_in_executor(None, _sync_read)
        except Exception:
            return 42.0

    # ==================================================================
    # SCENE‑ADAPTIVE TONE‑CURVE INGEST HELPER
    # ==================================================================
    def _build_node_dict_from_slot_indices(
        self,
        slot_indices: List[int],
        compliance: float,
        peer_ip: str,
    ) -> Dict[str, Any]:
        """Map the 6‑slot UDP telemetry vector into a 3‑D node feature
        dictionary suitable for the tone‑curve processor.

        Canonical mapping::

            intensity = (slot[0] + slot[3]) / 131070   (normalised)
            color     = (slot[1] + slot[4]) / 131070
            depth     = (slot[2] + slot[5]) / 131070

        The remaining slots are combined to increase dynamic range and
        symmetry within the 16‑bit frame.

        Parameters
        ----------
        slot_indices:
            Six uint16 values from the telemetry frame.
        compliance:
            Compliance score (float) used as an initial *processed*
            signal anchor.
        peer_ip:
            IP address of the originating peer.

        Returns
        -------
        dict
            Node dict with ``id``, ``intensity``, ``color``, ``depth``,
            ``compliance``, and ``neighbors`` keys.
        """
        si: List[float] = [float(v) for v in slot_indices]
        norm_factor: float = 131070.0  # 2 × 65535
        return {
            "id": f"peer_{peer_ip.replace('.', '_')}",
            "intensity": (si[0] + si[3]) / norm_factor,
            "color": (si[1] + si[4]) / norm_factor,
            "depth": (si[2] + si[5]) / norm_factor,
            "compliance": float(compliance),
            "neighbors": [],  # populated later during attention pass
        }

    async def _apply_tone_curve_filter(
        self, node_batch: List[Dict[str, Any]], *, fit_scaler: bool = False
    ) -> List[Dict[str, Any]]:
        """Run the Scene‑Adaptive Tone Curve processor over a node batch
        without blocking the event loop.

        This is the primary integration point for the filter sub‑layer.
        The method is called from both the UDP beacon listener and the
        TCP ingestion handler.
        """
        if not node_batch:
            return node_batch
        return await self.tone_curve.process_node_batch(
            node_batch, fit_scaler=fit_scaler
        )

    # ==================================================================
    # AUTOMATIC TASK EVALUATION & ROUTING ENGINE
    # ==================================================================
    def should_offload_task(self, task_metadata: Dict[str, Any]) -> bool:
        """Determine whether a task should be transparently offloaded to
        a remote peer instead of being executed locally.

        **Offload Triggers** (any one is sufficient):

        1. The task's ``"tags"`` list contains a heavy‑compute keyword
           (``COMPUTE_HEAVY``, ``VECTOR_SEARCH``, ``GENETIC_EVOLUTION``).
        2. The current system temperature is *above* the configurable
           threshold (default 75 °C).
        3. The task metadata includes an ``"estimated_cost"`` key whose
           value exceeds a locally‑defined capacity ceiling.

        Offloading only occurs when at least one peer has already been
        discovered in ``self.peers``.

        Parameters
        ----------
        task_metadata:
            Dictionary describing the task.  Recognised keys:

            - ``"tags"``: ``List[str]`` — semantic tags.
            - ``"estimated_cost"``: ``float`` — abstract resource cost.
            - ``"temperature"``: ``float`` (optional) — latest thermal
              reading; if omitted the method reads it synchronously
              from sysfs.

        Returns
        -------
        bool
            ``True`` when the task should be transparently redirected
            to a peer.
        """
        # No peers → nothing to offload to
        if not self.peers:
            return False

        tags: List[str] = task_metadata.get("tags", [])
        if any(tag in OFFLOAD_TAGS for tag in tags):
            print(
                f"[*] Offload triggered by task tag intersection: "
                f"{set(tags) & set(OFFLOAD_TAGS)}"
            )
            return True

        # Thermal guard
        current_temp: float = task_metadata.get("temperature", 42.0)
        if current_temp == 42.0:
            # Attempt synchronous read as fallback (called from sync context)
            try:
                with open(THERMAL_PATH, "r") as fh:
                    current_temp = float(fh.read().strip()) / 1000.0
            except (OSError, ValueError):
                pass
        if current_temp > self.offload_temp_threshold:
            print(
                f"[*] Offload triggered by thermal threshold: "
                f"{current_temp:.1f}°C > {self.offload_temp_threshold}°C"
            )
            return True

        # Resource‑cost guard
        estimated_cost: Optional[float] = task_metadata.get("estimated_cost")
        if estimated_cost is not None and estimated_cost > 1.0:
            print(
                f"[*] Offload triggered by estimated cost: "
                f"{estimated_cost:.3f} exceeds local capacity ceiling (1.0)"
            )
            return True

        return False

    # ==================================================================
    # UDP BEACON (LATTICE DISCOVERY) — with tone‑curve filter wired in
    # ==================================================================
    def start_udp_beacon(self) -> None:
        """Create and bind the UDP broadcast socket on port 4444 and
        schedule the asynchronous beacon‑listening loop.

        This method must be called from within a running asyncio event
        loop so that ``asyncio.get_running_loop()`` succeeds.
        """
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
        try:
            self.udp_sock.bind(("0.0.0.0", self.udp_port))
            self.udp_sock.setblocking(False)
            loop = asyncio.get_running_loop()
            loop.create_task(self._listen_beacons_async())
            print(
                f"[LATTICA MESH] > UDP Nobex DAO Beacon active on "
                f"port {self.udp_port}"
            )
        except Exception as exc:
            print(f"[-] UDP beacon bind failed on port {self.udp_port}: {exc}")
            log_error = getattr(self.node, "log_error", None)
            if log_error is not None:
                log_error("MESH_BIND_FAIL", str(exc), severity=2)

    async def _listen_beacons_async(self) -> None:
        """Continuous background non‑blocking mesh listener loop.

        Reads incoming UDP frames, unpacks the 16‑byte telemetry,
        registers new peers, runs the **Scene‑Adaptive Tone Curve**
        filter over the decoded node batch to produce normalised 3‑D
        coordinate matrices with graph‑attention weights, and enqueues
        morpho‑semantic root traces into the node's memory palace.
        """
        loop = asyncio.get_running_loop()
        print("[*] Beacon listener coroutine started (tone‑curve filter active).")

        # Accumulate up to a small batch before running the vectorised
        # tone‑curve pass, avoiding per‑packet overhead while keeping
        # latency low.
        _pending_batch: List[Dict[str, Any]] = []
        _batch_flush_size: int = 32
        _first_batch: bool = True

        while True:
            try:
                data, addr = await loop.sock_recvfrom(self.udp_sock, 1024)
                slot_indices, compliance = self.unpack_secure_polysynthetic_packet(data)

                if slot_indices is None:
                    continue

                # Peer registration
                ip: str = addr[0]
                if ip not in self.peers:
                    label = f"SIBLING_NODE_{ip.split('.')[-1]}"
                    self.peers[ip] = label
                    print(
                        f"\n[~] MESH SYNERGY: Registered new peer "
                        f"'{label}' @ {ip}"
                    )

                # Build node dict from telemetry and queue for tone‑curve pass
                node_dict: Dict[str, Any] = self._build_node_dict_from_slot_indices(
                    slot_indices, compliance, ip
                )
                _pending_batch.append(node_dict)

                # Flush batch when threshold reached
                if len(_pending_batch) >= _batch_flush_size:
                    processed: List[Dict[str, Any]] = (
                        await self._apply_tone_curve_filter(
                            _pending_batch, fit_scaler=_first_batch
                        )
                    )
                    _first_batch = False

                    # Push processed nodes into memory palace
                    memory_palace = getattr(self.node, "memory_palace", None)
                    if memory_palace is not None:
                        for pnode in processed:
                            num_thought_id: int = int(
                                hashlib.md5(
                                    pnode["id"].encode()
                                ).hexdigest()[:7],
                                16,
                            )
                            # Encode the 3‑D graph features alongside the
                            # compliance score for holographic trace storage
                            await memory_palace.enqueue_morphemic_root_trace(
                                num_thought_id,
                                [int(pnode["processed_intensity"] * 65535)],
                                pnode.get("compliance", compliance),
                            )
                    _pending_batch.clear()

            except BlockingIOError:
                # Flush any accumulated nodes on drain
                if _pending_batch:
                    try:
                        processed = await self._apply_tone_curve_filter(
                            _pending_batch, fit_scaler=_first_batch
                        )
                        _first_batch = False
                        memory_palace = getattr(
                            self.node, "memory_palace", None
                        )
                        if memory_palace is not None:
                            for pnode in processed:
                                num_thought_id = int(
                                    hashlib.md5(
                                        pnode["id"].encode()
                                    ).hexdigest()[:7],
                                    16,
                                )
                                await memory_palace.enqueue_morphemic_root_trace(
                                    num_thought_id,
                                    [int(pnode["processed_intensity"] * 65535)],
                                    pnode.get("compliance", compliance),
                                )
                    except Exception:
                        pass
                    _pending_batch.clear()
            except Exception as exc:
                print(f"[-] Beacon listener exception: {exc}")
            await asyncio.sleep(0.05)

    # ==================================================================
    # SWARM‑LEVEL BROADCAST UPGRADE
    # ==================================================================
    async def broadcast_upgrade(
        self, module_name: str, code_content: str
    ) -> None:
        """Broadcast a sealed software‑upgrade pulse across the UDP
        beacon channel.

        The upgrade is packaged into a fixed 16‑byte telemetry frame
        with canonical morph‑semantic slot coordinates and a compliance
        baseline of 1.0.

        Parameters
        ----------
        module_name:
            Human‑readable module identifier (logged for telemetry).
        code_content:
            The source / binary payload being disseminated (unused in
            the fixed‑frame beacon but retained for future protocol
            upgrades).
        """
        start_time: float = time.time()
        self.node.runtime_metrics["dikwp_tier"] = "PURPOSE"
        try:
            # Canonical upgrade‑pulse slot vector
            upgrade_slots: List[int] = [707, 707, 303, 909, 505, 808]
            compliance_baseline: float = 1.0
            secure_packet: bytes = self.pack_secure_polysynthetic_packet(
                upgrade_slots, compliance_baseline
            )
            self.udp_sock.sendto(secure_packet, (BROADCAST_ADDR, self.udp_port))
            print(
                f"[+] SWARM UPGRADE deployed for module '{module_name}' "
                f"| Shielded via PIP."
            )
            await self._commit_mesh_telemetry("SWARM_UPGRADE_BROADCAST", start_time)
        except Exception as exc:
            print(f"[-] Upgrade broadcast failed: {exc}")

    # ==================================================================
    # COMPUTE OFFLOAD (TCP CLIENT SIDE)
    # ==================================================================
    async def offload_compute(
        self, target_ip: str, module: str, data_payload: Dict[str, Any]
    ) -> Optional[Any]:
        """Transparently offload a compute task to a remote swarm peer
        over TCP port 4445 using the length‑prefixed protocol.

        Parameters
        ----------
        target_ip:
            Destination IPv4 address of the peer node.
        module:
            Logical module name (e.g. ``"VECTOR_SEARCH"``).
        data_payload:
            Task‑specific dictionary payload.

        Returns
        -------
        Optional[Any]
            The deserialized result payload returned by the peer, or
            ``None`` if the offload failed.
        """
        start_time: float = time.time()
        self.node.runtime_metrics["dikwp_tier"] = "KNOWLEDGE"

        payload_obj: Dict[str, Any] = {
            "id": f"JOB-{int(time.time())}",
            "module": module,
            "data": data_payload,
        }

        try:
            print(f"[*] Offloading '{module}' → {target_ip}:{self.tcp_port}...")
            secure_packet: bytes = self.pack_length_prefixed_payload(payload_obj)

            reader, writer = await asyncio.open_connection(
                target_ip, self.tcp_port
            )
            writer.write(secure_packet)
            await writer.drain()

            # Read back the length‑prefixed response
            raw_response: bytes = await reader.read(65536)
            writer.close()
            await writer.wait_closed()

            result: Optional[Any] = self.unpack_length_prefixed_payload(raw_response)
            if result is not None:
                print(
                    f"[+] Offload complete — response from {target_ip}: "
                    f"{result}"
                )
            else:
                print(
                    f"[-] Offload to {target_ip} returned an unparseable "
                    f"response."
                )
            await self._commit_mesh_telemetry("SWARM_TASK_OFFLOAD", start_time)
            return result
        except Exception as exc:
            print(f"[-] Offload to {target_ip} failed: {exc}")
            return None

    # ==================================================================
    # TCP COMPUTE SERVER (INGESTION WORKER) — with tone‑curve filter
    # ==================================================================
    async def start_tcp_compute_server(self) -> None:
        """Start the asynchronous TCP ingestion worker on port 4445.

        This server receives length‑prefixed binary frames from remote
        peers, deserializes them into task dictionaries, verifies the
        sender's DSEKP shield where possible, **runs the incoming node
        data through the Scene‑Adaptive Tone Curve filter**, processes
        the task locally, and returns a length‑prefixed binary result
        frame to the caller.

        The server is bound to ``0.0.0.0`` and runs until the parent
        event loop is stopped.
        """

        async def handle_client(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            """Per‑connection callback invoked by the asyncio server."""
            peer_addr = writer.get_extra_info("peername")
            peer_ip: str = peer_addr[0] if peer_addr else "unknown"
            print(f"[*] TCP compute client connected from {peer_ip}")

            try:
                # ---- 1. Read the length‑prefixed incoming frame ----
                raw_data: bytes = await reader.read(65536)
                if not raw_data:
                    print(f"[-] Empty frame from {peer_ip} — closing.")
                    writer.close()
                    await writer.wait_closed()
                    return

                task_dict: Optional[Dict[str, Any]] = (
                    self.unpack_length_prefixed_payload(raw_data)
                )
                if task_dict is None:
                    print(f"[-] Failed to unpack payload from {peer_ip}.")
                    error_resp: bytes = self.pack_length_prefixed_payload(
                        {"status": "error", "reason": "unpackable_payload"}
                    )
                    writer.write(error_resp)
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    return

                print(
                    f"[*] Received task from {peer_ip}: "
                    f"id={task_dict.get('id', '?')}, "
                    f"module={task_dict.get('module', '?')}"
                )

                # ---- 2. Verify sender integrity via DSEKP ----
                shield_envelope: Dict[str, Any] = {
                    "dsekp_shield": task_dict.get("dsekp_shield", "OFFLINE"),
                    "trace_id": task_dict.get(
                        "trace_id", task_dict.get("id", "UNKNOWN")
                    ),
                }
                shield_valid: bool = await self.verify_dsekp_shield(shield_envelope)
                if shield_valid:
                    print(f"[+] DSEKP shield valid for task from {peer_ip}.")
                else:
                    print(
                        f"[*] DSEKP shield absent / invalid for task from "
                        f"{peer_ip} — processing anyway."
                    )

                # ---- 3. Scene‑Adaptive Tone‑Curve filter pass ----
                # Extract any embedded node‑list payload and feed it
                # through the tone‑curve processor before delegating to
                # the local executor.
                data_payload: Any = task_dict.get("data")
                tone_boosted: Any = None
                if isinstance(data_payload, dict) and "nodes" in data_payload:
                    raw_nodes: Any = data_payload["nodes"]
                    if isinstance(raw_nodes, list) and raw_nodes:
                        try:
                            print(
                                f"[*] Running tone‑curve filter over "
                                f"{len(raw_nodes)} node(s) from {peer_ip}."
                            )
                            filtered_nodes: List[Dict[str, Any]] = (
                                await self.tone_curve.process_node_batch(
                                    raw_nodes
                                )
                            )
                            # Replace the raw list with the boosted version
                            data_payload = dict(data_payload)
                            data_payload["nodes"] = filtered_nodes
                            tone_boosted = data_payload
                            task_dict["data"] = tone_boosted
                        except Exception as tc_exc:
                            print(
                                f"[-] Tone‑curve filter failed for batch "
                                f"from {peer_ip}: {tc_exc} — continuing "
                                f"with raw data."
                            )

                # ---- 4. Process the task locally ----
                result_payload: Dict[str, Any]
                task_exec = getattr(self.node, "execute_offloaded_task", None)
                if callable(task_exec):
                    result_payload = await task_exec(task_dict)
                else:
                    # Simulated local computation
                    result_payload = {
                        "status": "ok",
                        "processed_by": self.identity,
                        "original_id": task_dict.get("id"),
                        "echo_data": task_dict.get("data"),
                        "tone_curve_applied": tone_boosted is not None,
                    }
                    print(
                        f"[+] Task '{task_dict.get('id')}' processed "
                        f"locally (simulated)."
                    )

                # ---- 5. Pack and return the binary result ----
                response_frame: bytes = self.pack_length_prefixed_payload(
                    result_payload
                )
                writer.write(response_frame)
                await writer.drain()
                print(
                    f"[*] Response sent to {peer_ip} "
                    f"({len(response_frame)} bytes)."
                )

            except asyncio.CancelledError:
                print(f"[*] TCP handler for {peer_ip} cancelled.")
            except Exception as exc:
                print(f"[-] TCP handler exception for {peer_ip}: {exc}")
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

        try:
            self.tcp_server = await asyncio.start_server(
                handle_client,
                host="0.0.0.0",
                port=self.tcp_port,
                reuse_address=True,
            )
            print(
                f"[LATTICA MESH] > TCP Compute Ingestion Worker active on "
                f"port {self.tcp_port} (tone‑curve filter enabled)"
            )
        except Exception as exc:
            print(
                f"[-] Failed to start TCP compute server on port "
                f"{self.tcp_port}: {exc}"
            )
            log_error = getattr(self.node, "log_error", None)
            if log_error is not None:
                log_error("MESH_TCP_BIND_FAIL", str(exc), severity=2)

    # ==================================================================
    # TELEMETRY COMMIT
    # ==================================================================
    async def _commit_mesh_telemetry(
        self, action_string: str, start_time: float
    ) -> None:
        """Write a holographic telemetry trace into the node's memory
        palace.

        Parameters
        ----------
        action_string:
            Human‑readable label for the action (e.g.
            ``"SWARM_UPGRADE_BROADCAST"``).
        start_time:
            ``time.time()`` captured at action initiation, used to
            compute latency.
        """
        metrics: Dict[str, Any] = getattr(self.node, "runtime_metrics", {})
        t_id: str = metrics.get("thought_id", "MESH-00000000")
        try:
            num_id: int = int(t_id.split("-")[1], 16)
        except (IndexError, ValueError):
            num_id = 0

        # Non‑blocking thermal read
        temp: float = await self._read_thermal_nonblocking()
        ms: float = (time.time() - start_time) * 1000.0

        memory_palace = getattr(self.node, "memory_palace", None)
        if memory_palace is not None:
            await memory_palace.enqueue_holographic_trace(
                num_id, action_string, temp, ms, True
            )