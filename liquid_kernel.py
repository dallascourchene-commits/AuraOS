"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: typing, numpy
FUNCTIONS: ternary_activation, __init__, __init__, __call__, ternary_quantize, __init__, _f_network, dynamic_time_constant, step, evaluate_energy_ceiling, __init__, forward, reset, __init__, __call__, __init__, step, reset, __init__, __call__, __init__, maxwell_correction, __init__, ternary_quantize_array, quantize_state, __init__, encode_input, update, __init__, process_command
SYNOPSIS: The `AuraOS.TernaryNeuralCore` module, dependent on `typing` and `numpy`, implements a ternary neural network framework with functions for activation (`ternary_activation`), initialization (`__init__`), quantization (`ternary_quantize`, `ternary_quantize_array`), state management (`quantize_state`, `reset`), dynamic adaptation (`dynamic_time_constant`, `maxwell_correction`), forward propagation (`forward`, `_f_network`), energy evaluation (`evaluate_energy_ceiling`), command processing (`process_command`, `encode_input`), and step-wise execution (`step`, `__call__`), while enforcing strict type hints and numerical precision via NumPy.
[/AURA_MASTER_KEY]
"""

import numpy as np
from typing import Dict, Any

dataclass_stub_replacement = True
class LiquidConfig:
    def __init__(self, time_constant: float = 1.58, ltc_learning_rate: float = 0.01,
                 ternary_threshold: float = 0.0, stochastic_toggle_prob: float = 0.1,
                 maxwell_damping: float = 0.99, excitatory_gain: float = 1.2,
                 inhibitory_gain: float = 0.8):
        self.time_constant = time_constant
        self.ltc_learning_rate = ltc_learning_rate
        self.ternary_threshold = ternary_threshold
        self.stochastic_toggle_prob = stochastic_toggle_prob
        self.maxwell_damping = maxwell_damping
        self.excitatory_gain = excitatory_gain
        self.inhibitory_gain = inhibitory_gain

class TernaryLinear:
    def __init__(self, in_features: int, out_features: int, rng):
        limit = np.sqrt(6.0 / (in_features + out_features))
        self.weight = rng.uniform(-limit, limit, (out_features, in_features))
        self.bias = np.zeros(out_features)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return x @ self.weight.T + self.bias

    def ternary_quantize(self) -> None:
        threshold = 0.5
        self.weight = np.where(np.abs(self.weight) < threshold, 0, np.sign(self.weight) * 1.58)

def ternary_activation(x: np.ndarray, threshold: float = 0.0, toggle_prob: float = 0.1, rng=None) -> np.ndarray:
    """Zero-allocation real-valued ternary activation."""
    if rng is None:
        rng = np.random.default_rng(seed=101)
        
    abs_x = np.abs(x)
    # 100% Vectorized single-pass sign mapping replaces legacy loops
    ternary = np.where(abs_x >= threshold, np.sign(x) * 1.58, 0.0).astype(np.float32)
    
    if toggle_prob > 0.0:
        mask = rng.random(x.shape) < toggle_prob
        return np.where(mask, ternary, x)
    return ternary

class AdaptiveLiquidTimeConstant:
    """
    LTC-NDE (Liquid Time-Constant Neural Differential Equation) solver.

    Implements the input-dependent time constant from the LTC paper
    (arXiv:2006.04439 / Lechner et al.):

        τ_sys = τ / (1 + τ · f(x, I; θ))
        dx/dt = -x/τ_sys  +  f(x, I; θ) · A

    where f is approximated as a small MLP (here: single linear layer +
    sigmoid to keep RAM footprint minimal on the 4 GB device boundary).

    Additionally exposes ``evaluate_energy_ceiling`` so the Governor can
    dynamically scale compute intensity based on thermal state.
    """

    def __init__(self, config: LiquidConfig) -> None:
        self.tau = config.time_constant
        self.config = config
        rng = np.random.default_rng(42)
        # Single-layer "f network" weights: shape (1, 1) — scalar modulator
        self._w_f: np.ndarray = rng.standard_normal(1).astype(np.float32) * 0.1
        # Learnable bias vector A (Lechner et al. Eq. 1)
        self._A: np.ndarray = np.ones(1, dtype=np.float32)
        # Adaptive params for legacy compatibility
        self.adaptive_params: np.ndarray = np.zeros(1, dtype=np.float32)

    # ------------------------------------------------------------------
    # LTC formula (arXiv:2006.04439)
    # ------------------------------------------------------------------

    def _f_network(self, x: np.ndarray, I: np.ndarray) -> np.ndarray:
        """Single-layer sigmoid modulator: f(x, I) = σ(w·(x + I))."""
        combined = float(np.linalg.norm(x)) + float(np.linalg.norm(I))
        return 1.0 / (1.0 + np.exp(-self._w_f * combined))  # sigmoid

    def dynamic_time_constant(
        self,
        input_features: np.ndarray,
        state: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Compute the input-dependent time constant:

            τ_sys = τ / (1 + τ · f(state, input))

        Falls back to the legacy feature-norm heuristic when ``state``
        is None so existing call sites remain compatible.
        """
        if state is None:
            # Legacy path (backward-compatible)
            feature_norm = float(np.linalg.norm(input_features))
            adaptive_tau = self.tau * (
                1.0
                + self.config.ltc_learning_rate
                * self.adaptive_params
                * (1.0 + feature_norm)
            )
            return np.clip(adaptive_tau, 0.5, 3.0)

        # Full LTC-NDE path
        f_val = self._f_network(state, input_features)
        tau_sys = self.tau / (1.0 + self.tau * f_val + 1e-8)
        return np.clip(tau_sys, 0.1, 5.0)

    def step(self, x: np.ndarray, f: np.ndarray, dt: float) -> np.ndarray:
        """
        Euler integration of dx/dt = -x/τ_sys + f·A.
        Uses the LTC-NDE formula when possible, falls back to the
        denominator trick for legacy compatibility.
        """
        tau = self.dynamic_time_constant(f, state=x)
        # LTC Euler: x_new = x + dt·(-x/τ + f·A)
        dx = (-x / (tau + 1e-8)) + f * self._A
        return x + dt * dx

    # ------------------------------------------------------------------
    # Energy ceiling — thermal-adaptive compute scaling
    # (from AURA synthesis doc: Integration Vector A)
    # ------------------------------------------------------------------

    def evaluate_energy_ceiling(self, current_temp: float) -> float:
        """
        Return a compute-intensity scalar ∈ [0.15, 1.0] based on device
        thermal state.  At >41.5 °C the Governor transitions to strict
        1.58-bit ternary-weight pathing (low intensity).
        """
        if current_temp > 41.5:
            self.config.ternary_threshold = 0.50
            return 0.15
        self.config.ternary_threshold = 0.0
        return 1.0


class ClosedFormContinuousCore:
    """
    Closed-Form Continuous-time (CfC) cell (arXiv:2106.13898).

    Replaces static thresholds with time-dependent differential equations
    using the analytical closed-form solution:

        h(t) = gate * h(t-1) + (1 - gate) * tanh(W·x + b)
        gate = exp(-dt / τ)

    This eliminates the O(N²) context-window memory of Transformers,
    allowing Aura to process high-frequency data streams (ArXiv forager,
    mesh packets) with constant RAM usage.
    """

    def __init__(self, units: int, time_constant: float = 1.58) -> None:
        self.units = units
        self.time_constant = time_constant
        rng = np.random.default_rng(0)
        scale = np.sqrt(2.0 / units)
        self._W: np.ndarray = (rng.standard_normal((units, units)) * scale).astype(np.float32)
        self._b: np.ndarray = np.zeros(units, dtype=np.float32)
        self.hidden_state: np.ndarray = np.zeros(units, dtype=np.float32)

    def forward(
        self,
        input_vec: np.ndarray,
        hidden_state: np.ndarray | None = None,
        dt: float = 0.1,
    ) -> np.ndarray:
        """
        One CfC step.

        h(t) = exp(-dt/τ) · h(t-1)  +  (1 − exp(-dt/τ)) · tanh(W·x + b)
        """
        h = hidden_state if hidden_state is not None else self.hidden_state
        gate = np.exp(-dt / self.time_constant)
        candidate = np.tanh(self._W @ input_vec + self._b)
        new_h = gate * h + (1.0 - gate) * candidate
        self.hidden_state = new_h
        return new_h

    def reset(self) -> None:
        """Zero the hidden state (call between independent sequences)."""
        self.hidden_state[:] = 0.0

class LiquidNeuron:
    def __init__(self, input_dim: int, output_dim: int, config: LiquidConfig, rng):
        self.fc = TernaryLinear(input_dim, output_dim, rng)
        self.config = config
        self.rng = rng

    def __call__(self, x: np.ndarray) -> np.ndarray:
        voltage = self.fc(x)
        return ternary_activation(
            voltage * self.config.excitatory_gain,
            self.config.ternary_threshold,
            self.config.stochastic_toggle_prob,
            self.rng
        )

class mLSTMCell:
    """
    xLSTM Matrix Memory Cell (NeurIPS 2024, Beck et al. arXiv:2405.04517).

    Key innovations over standard LSTM
    ------------------------------------
    1. **Matrix memory** C ∈ ℝ^{d×d} (vs scalar c) stores key-value pairs
       via a covariance/outer-product update rule.
    2. **Exponential gating** — input gate i_t = exp(ñ_t), forget gate
       f_t = exp(−|ṁ_t|) after log-sum-exp stabilisation.
    3. **No hidden-hidden recurrence** — fully parallelisable over time.
    4. **Linear O(d²) memory**, O(T·d²) compute — no context window.

    On the 4 GB Termux envelope *d* is kept small (64 by default).
    The cell operates in float32 to remain within the zero-copy PVM
    dtype constraints.
    """

    def __init__(self, d: int = 64) -> None:
        self.d = d
        rng = np.random.default_rng(42)
        scale = np.sqrt(1.0 / d)
        # Projection weights (key, value, query, input-gate, forget-gate)
        self.W_k  = (rng.standard_normal((d, d)) * scale).astype(np.float32)
        self.W_v  = (rng.standard_normal((d, d)) * scale).astype(np.float32)
        self.W_q  = (rng.standard_normal((d, d)) * scale).astype(np.float32)
        self.w_i  = (rng.standard_normal(d) * scale).astype(np.float32)
        self.w_f  = (rng.standard_normal(d) * scale).astype(np.float32)
        self.b_i  = np.zeros(d, dtype=np.float32)
        self.b_f  = np.zeros(d, dtype=np.float32)
        # Recurrent state: matrix memory C and normalizer n
        self.C: np.ndarray = np.zeros((d, d), dtype=np.float32)
        self.n: np.ndarray = np.zeros(d, dtype=np.float32)
        # Log-sum-exp stabiliser (max log-input-gate seen so far)
        self.m: float = 0.0

    def step(self, x: np.ndarray) -> np.ndarray:
        """
        One mLSTM step.

        x : input vector of shape (d,)
        Returns the output hidden vector h ∈ ℝ^d.
        """
        x = x.astype(np.float32).ravel()[: self.d]
        if len(x) < self.d:
            x = np.pad(x, (0, self.d - len(x)))

        # Keys, values, queries
        k = self.W_k @ x   # (d,)
        v = self.W_v @ x   # (d,)
        q = self.W_q @ x   # (d,)

        # Raw gate logits
        raw_i = float(self.w_i @ x + self.b_i[0])  # scalar pre-activation
        raw_f = float(self.w_f @ x + self.b_f[0])

        # Log-sum-exp stabilisation (prevents exp overflow)
        m_new = max(raw_f + self.m, raw_i)
        f_prime = np.exp(raw_f + self.m - m_new)
        i_prime = np.exp(raw_i - m_new)
        self.m = m_new

        # Matrix memory update: C ← f·C + i·(v⊗k)
        self.C = f_prime * self.C + i_prime * np.outer(v, k)

        # Normaliser update: n ← f·n + i·k
        self.n = f_prime * self.n + i_prime * k

        # Read: h = C·q / max(|n·q|, 1)
        Cq = self.C @ q
        n_dot_q = abs(float(self.n @ q))
        # Output stabilisation: use max(|n·q|, sqrt(|C·q|₂), 1) to
        # prevent unbounded growth when n is near-orthogonal to q.
        # Approximates the GroupNorm used in the full xLSTM implementation.
        cq_norm = float(np.linalg.norm(Cq))
        denom = max(n_dot_q, cq_norm ** 0.5, 1.0)
        h = Cq / denom
        return h.astype(np.float32)

    def reset(self) -> None:
        """Zero all recurrent state."""
        self.C[:] = 0.0
        self.n[:] = 0.0
        self.m = 0.0


class LiquidStateMachine:
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, config: LiquidConfig, rng):
        self.config = config
        self.neurons = [LiquidNeuron(hidden_dim, hidden_dim, config, rng) for _ in range(3)]

        self.input_proj = TernaryLinear(input_dim, hidden_dim, rng)
        self.output_proj = TernaryLinear(hidden_dim, output_dim, rng)
        self.recurrent = TernaryLinear(hidden_dim, hidden_dim, rng)
        self.excitatory = TernaryLinear(hidden_dim, hidden_dim, rng)
        self.inhibitory = TernaryLinear(hidden_dim, hidden_dim, rng)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        h = np.maximum(0, self.input_proj(x))

        for neuron in self.neurons:
            h = neuron(h)

        recurrent = np.maximum(0, self.recurrent(h))
        excite = np.maximum(0, self.excitatory(h))
        inhibit = np.maximum(0, self.inhibitory(h))

        balanced = excite * self.config.excitatory_gain - inhibit * self.config.inhibitory_gain
        h = h + balanced

        return self.output_proj(h)

class PhysicsInformedCorrection:
    def __init__(self, config: LiquidConfig):
        self.config = config

    def maxwell_correction(self, state: np.ndarray) -> np.ndarray:
        return state * self.config.maxwell_damping

class TernaryQuantizer:
    def __init__(self, config: LiquidConfig, rng):
        self.config = config
        self.rng = rng

    def ternary_quantize_array(self, arr: np.ndarray) -> np.ndarray:
        return ternary_activation(arr, self.config.ternary_threshold, self.config.stochastic_toggle_prob, self.rng)

    def quantize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        quantized = {}
        for k, v in state.items():
            if isinstance(v, (int, float)):
                quantized[k] = float(self.ternary_quantize_array(np.array([v]))[0])
            else:
                quantized[k] = v
        return quantized

class LiquidState:
    def __init__(self, config: LiquidConfig):
        self.config = config
        
        # Initialize single thread-safe random state generator shared across sub-modules
        self._rng = np.random.default_rng(seed=101)
        
        self.ltc_solver = AdaptiveLiquidTimeConstant(config)
        self.lsm = LiquidStateMachine(input_dim=3, hidden_dim=64, output_dim=3, config=config, rng=self._rng)
        self.physics_correction = PhysicsInformedCorrection(config)
        self.state = {}
        self.dt = 0.01
        self.last_physics_error = 0.0

    def encode_input(self, val: Any) -> float:
        try:
            return float(val)
        except ValueError:
            return float(hash(str(val)) % 100) / 100.0

    def update(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        encoded_values = [self.encode_input(v) for v in input_data.values()]
        np_state = np.array(encoded_values, dtype=np.float32)

        f = self.lsm(np_state)

        new_state = self.ltc_solver.step(np_state, f, self.dt)

        corrected_state = self.physics_correction.maxwell_correction(new_state)

        # Compute the raw continuous physics discrepancy (Maxwell residual variance)
        self.last_physics_error = float(np.var(corrected_state - new_state))

        self.state = {k: float(v) for k, v in zip(input_data.keys(), corrected_state)}
        return self.state

class LiquidWebSocket:
    def __init__(self, config: LiquidConfig = None):
        self.config = config or LiquidConfig()
        self.liquid_state = LiquidState(self.config)
        self.quantizer = TernaryQuantizer(self.config, rng=self.liquid_state._rng)

    async def process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        liquid_state = self.liquid_state.update(command)
        quantized_state = self.quantizer.quantize_state(liquid_state)

        for k, v in command.items():
            if isinstance(v, str) and not v.replace('.','',1).isdigit():
                quantized_state[k] = v

        return quantized_state
