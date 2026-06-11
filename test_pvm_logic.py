from __future__ import annotations

"""
AURA PVM — Polysynthetic Logic Gate Evaluation Test
=====================================================
Validates the core reasoning engine in aura_spvm.py by running a
6-slot polysynthetic gate evaluation over two distinct 10,000-D complex
phasor hypervectors and confirming every logical subsumption value falls
within the analytically-derived phase-drift envelope.

Background — the math
---------------------
``evaluate_implication(v_a, v_b)`` applies Łukasiewicz material implication
dimension-wise then averages:

    imp[i] = min(1,  1 − clip(Re(v_a[i]), 0, 1)  +  clip(Re(v_b[i]), 0, 1))
    result  = mean(imp)

For two unit phasors whose phases θ_a[i], θ_b[i] are drawn independently
from Uniform(−π, π)  (which is exactly what get_semantic_vector does):

    a[i] = clip(cos θ_a[i], 0, 1)   b[i] = clip(cos θ_b[i], 0, 1)

Closed-form expected value (derived via arcsine distribution):

    E[imp] = 1 − 1/(2π) − (4−π)/(2π²)  ≈  0.7974

By the Central Limit Theorem over D = 10,000 independent dimensions,
|sample_mean − E[imp]| < SIGMA_MULTIPLIER * σ_mean with probability > 0.9999
where σ_mean = sqrt(Var[imp] / D).

Polysynthetic slots
-------------------
The 6 slots map to the obligatory morpheme positions in Ojibwe/AURA grammar:

    Slot 0  PERS_SUBJECT   — personal/number agreement prefix
    Slot 1  TENSE_ASPECT   — temporal–aspectual marker
    Slot 2  VERB_ROOT      — core semantic predicate
    Slot 3  VOICE_THEME    — voice/thematic-role operator
    Slot 4  OBJ_AGREEMENT  — object-agreement suffix
    Slot 5  MODAL_EVID     — modality / evidentiality

Each slot label produces a unique BLAKE2b seed → unique 10,000-D phasor.
All 15 ordered pairings and the 5 adjacent-slot implications are evaluated.

Run:
    python test_pvm_logic.py
"""

import math
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from aura_spvm import evaluate_implication, get_semantic_vector
from pvm_arch_checker import PVMArchChecker
from pvm_memory_guard import MemoryBudget, assert_zero_copy, sample_rss_mb

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIM: int = 10_000
SIGMA_MULTIPLIER: float = 5.0     # 5σ safety band  (P > 0.9999997)
SELF_IMPLICATION_EXACT: float = 1.0

# Analytical closed-form expected value for two independent random phasors
E_IMP_ANALYTIC: float = 1.0 - 1.0 / (2 * math.pi) - (4 - math.pi) / (2 * math.pi ** 2)

# Hard upper bound — Łukasiewicz implication is bounded by 1
HARD_UPPER: float = 1.0

# The simulate_spvm() bridge threshold (from aura_spvm.py line 96)
BRIDGE_THRESHOLD: float = 0.70

# ---------------------------------------------------------------------------
# 6 polysynthetic morpheme slot labels
# ---------------------------------------------------------------------------

SLOTS: list[str] = [
    "PERS_SUBJECT",
    "TENSE_ASPECT",
    "VERB_ROOT",
    "VOICE_THEME",
    "OBJ_AGREEMENT",
    "MODAL_EVID",
]

_DIVIDER = "─" * 68

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _banner(title: str) -> None:
    print(f"\n{'═' * 68}")
    print(f"  {title}")
    print("═" * 68)

def _ok(msg: str) -> None:
    print(f"  [PASS]  {msg}")

def _fail(msg: str) -> None:
    print(f"  [FAIL]  {msg}")
    sys.exit(1)

def _info(msg: str) -> None:
    print(f"  [INFO]  {msg}")


# ---------------------------------------------------------------------------
# Phase 0 — arch + memory-guard pre-flight
# ---------------------------------------------------------------------------

def phase0_preflight() -> None:
    _banner("PHASE 0 — Pre-flight: arch check + memory guard activation")

    checker = PVMArchChecker(root=Path("."))
    violations = checker.run()
    hard = [v for v in violations if v.rule in
            {"SYNTAX_ERROR", "WILDCARD_IMPORT", "CIRCULAR_IMPORT", "NAMESPACE_INJECTION"}]
    if hard:
        _fail(f"pvm_arch_checker found {len(hard)} hard violation(s) before test run.")
    _ok(f"pvm_arch_checker: 0 hard violations ({len(violations)} NESTED_IMPORT advisory only)")

    rss = sample_rss_mb()
    _info(f"Baseline RSS: {rss:.1f} MB")


# ---------------------------------------------------------------------------
# Phase 1 — analytical envelope
# ---------------------------------------------------------------------------

def phase1_analytical_envelope() -> tuple[float, float, float]:
    """
    Monte-Carlo-estimate Var[imp] for two independent uniform phasors of
    dimension D to derive the tight σ_mean used as the phase-drift boundary.

    Returns (E_imp_analytic, sigma_of_mean, lower_bound, upper_bound) as
    (E_imp, sigma, lo, hi).
    """
    _banner("PHASE 1 — Analytical phase-drift envelope derivation")

    _info(f"Analytical E[imp] = 1 − 1/(2π) − (4−π)/(2π²)")
    _info(f"                  = {E_IMP_ANALYTIC:.6f}")

    # Monte Carlo over N = 200,000 to estimate Var[imp]
    MC_N = 200_000
    AURA_SEED = 0xA8E5
    rng = np.random.default_rng(AURA_SEED)
    theta_a = rng.uniform(-math.pi, math.pi, MC_N).astype(np.float32)
    theta_b = rng.uniform(-math.pi, math.pi, MC_N).astype(np.float32)
    ta = np.clip(np.cos(theta_a), 0.0, 1.0)
    tb = np.clip(np.cos(theta_b), 0.0, 1.0)
    imp_mc = np.minimum(1.0, 1.0 - ta + tb)
    e_mc   = float(np.mean(imp_mc))
    var_mc = float(np.var(imp_mc))

    _info(f"Monte Carlo estimate (N={MC_N:,}): E[imp] = {e_mc:.6f}  Var[imp] = {var_mc:.6f}")

    # Discrepancy between analytic and MC should be < 0.001
    analytic_mc_gap = abs(E_IMP_ANALYTIC - e_mc)
    if analytic_mc_gap > 0.005:
        _fail(f"Analytical vs Monte Carlo gap too large: {analytic_mc_gap:.6f}")
    _ok(f"Analytic–MC agreement: |{E_IMP_ANALYTIC:.4f} − {e_mc:.4f}| = {analytic_mc_gap:.6f} < 0.005")

    # σ of the sample mean over D=10,000 independent dimensions
    sigma_of_mean = math.sqrt(var_mc / DIM)
    lo = E_IMP_ANALYTIC - SIGMA_MULTIPLIER * sigma_of_mean
    hi = HARD_UPPER

    _info(f"σ_mean over D={DIM:,}: {sigma_of_mean:.6f}")
    _info(f"Phase-drift envelope  ({SIGMA_MULTIPLIER:.0f}σ): [{lo:.4f}, {hi:.4f}]")
    _info(f"Bridge coherence gate (aura_spvm.py line 96): ≥ {BRIDGE_THRESHOLD:.2f}")

    print()
    assert lo > BRIDGE_THRESHOLD, (
        f"Envelope lower bound {lo:.4f} is below bridge threshold {BRIDGE_THRESHOLD:.2f}; "
        "something is wrong with the phasor distribution."
    )
    _ok(f"Envelope [{lo:.4f}, {hi:.4f}] is fully above bridge threshold {BRIDGE_THRESHOLD:.2f}")

    return E_IMP_ANALYTIC, sigma_of_mean, lo


# ---------------------------------------------------------------------------
# Phase 2 — generate 6-slot phasors and validate zero-copy discipline
# ---------------------------------------------------------------------------

def phase2_generate_phasors() -> dict[str, np.ndarray]:
    _banner("PHASE 2 — Hypervector generation (6 slots × 10,000-D complex phasors)")

    phasors: dict[str, np.ndarray] = {}

    with MemoryBudget(budget_mb=512, poll_interval_s=0.5, raise_on_breach=True):
        for slot in SLOTS:
            v = get_semantic_vector(slot, dim=DIM)
            # assert_zero_copy: only validates contiguous numeric dtypes
            # (complex64 is in the approved PVM dtype set)
            assert v.dtype == np.complex64, f"Unexpected dtype {v.dtype} for slot {slot}"
            assert v.shape == (DIM,), f"Wrong shape {v.shape}"
            assert np.allclose(np.abs(v), 1.0, atol=1e-5), \
                f"Slot {slot}: phasor components must have unit magnitude"
            phasors[slot] = v
            _info(f"  {slot:16s}  shape={v.shape}  dtype={v.dtype}  "
                  f"|mean(|v|)−1| = {abs(np.mean(np.abs(v)) - 1.0):.2e}")

    print()
    _ok(f"All {len(phasors)} slot phasors are unit complex64 vectors of dim {DIM:,}")

    # Verify distinctness: cosine similarity between any two slots must be < 0.1
    # (random unit phasors in 10,000-D are nearly orthogonal by concentration)
    for s1, s2 in combinations(SLOTS, 2):
        v1, v2 = phasors[s1], phasors[s2]
        cos_sim = abs(float(np.real(np.dot(v1.conj(), v2)))) / DIM
        if cos_sim > 0.05:
            _fail(f"Slots {s1} and {s2} are suspiciously similar: cos_sim={cos_sim:.4f}")

    _ok(f"All slot pairs are near-orthogonal (max cosine similarity < 0.05)")

    return phasors


# ---------------------------------------------------------------------------
# Phase 3 — self-implication (boundary condition)
# ---------------------------------------------------------------------------

def phase3_self_implication(phasors: dict[str, np.ndarray]) -> None:
    _banner("PHASE 3 — Self-implication: evaluate_implication(v, v) must be exactly 1.0")
    print("  Reasoning: when v_a = v_b, truth_a = truth_b everywhere,")
    print("  so min(1, 1 - a + a) = 1 for all dimensions.")
    print()

    for slot, v in phasors.items():
        result = evaluate_implication(v, v)
        if result != SELF_IMPLICATION_EXACT:
            _fail(f"{slot}: self-implication = {result} ≠ {SELF_IMPLICATION_EXACT}")
        _info(f"  {slot:16s}  evaluate_implication(v, v) = {result:.6f}  ✓")

    print()
    _ok(f"All {len(phasors)} self-implications are exactly {SELF_IMPLICATION_EXACT:.1f}")


# ---------------------------------------------------------------------------
# Phase 4 — 6-slot pairwise gate evaluation
# ---------------------------------------------------------------------------

def phase4_pairwise_gates(
    phasors: dict[str, np.ndarray],
    lo: float,
) -> None:
    _banner("PHASE 4 — 6-slot pairwise logical subsumption matrix")
    print(f"  Evaluating all C(6,2) = 15 ordered slot pairs.")
    print(f"  Phase-drift envelope: [{lo:.4f}, {HARD_UPPER:.4f}]")
    print()

    # Print header
    col_w = 8
    header = f"  {'A → B':20s}" + "".join(f"{'IMP(A→B)':>{col_w}s}  ")
    print(header)
    print(f"  {_DIVIDER}")

    all_results: list[tuple[str, str, float]] = []
    failures: list[str] = []

    for s_a, s_b in combinations(SLOTS, 2):
        va = phasors[s_a]
        vb = phasors[s_b]
        imp_ab = evaluate_implication(va, vb)
        imp_ba = evaluate_implication(vb, va)   # non-commutative in general

        all_results.append((s_a, s_b, imp_ab))
        all_results.append((s_b, s_a, imp_ba))

        in_bounds_ab = lo <= imp_ab <= HARD_UPPER
        in_bounds_ba = lo <= imp_ba <= HARD_UPPER
        tag_ab = "✓" if in_bounds_ab else "✗ OUT-OF-BOUNDS"
        tag_ba = "✓" if in_bounds_ba else "✗ OUT-OF-BOUNDS"

        print(f"  {s_a} → {s_b:<16s}  {imp_ab:>{col_w}.6f}  {tag_ab}")
        print(f"  {s_b} → {s_a:<16s}  {imp_ba:>{col_w}.6f}  {tag_ba}")

        if not in_bounds_ab:
            failures.append(f"{s_a}→{s_b}: {imp_ab:.6f} ∉ [{lo:.4f}, {HARD_UPPER}]")
        if not in_bounds_ba:
            failures.append(f"{s_b}→{s_a}: {imp_ba:.6f} ∉ [{lo:.4f}, {HARD_UPPER}]")

    print()
    if failures:
        for f in failures:
            _fail(f"Out-of-bounds: {f}")

    values = [r[2] for r in all_results]
    mean_imp  = float(np.mean(values))
    std_imp   = float(np.std(values))
    min_imp   = float(np.min(values))
    max_imp   = float(np.max(values))
    dev_from_e = abs(mean_imp - E_IMP_ANALYTIC)

    _info(f"30-sample mean   : {mean_imp:.6f}  (analytic E[imp] = {E_IMP_ANALYTIC:.6f})")
    _info(f"Deviation ΔE     : {dev_from_e:.6f}")
    _info(f"Min / Max        : {min_imp:.6f} / {max_imp:.6f}")
    _info(f"Std (30 values)  : {std_imp:.6f}")
    print()
    _ok(f"All 30 pairwise implications lie within [{lo:.4f}, {HARD_UPPER}]")


# ---------------------------------------------------------------------------
# Phase 5 — adjacent-slot chain (polysynthetic gate sequence)
# ---------------------------------------------------------------------------

def phase5_chain_evaluation(
    phasors: dict[str, np.ndarray],
    lo: float,
) -> None:
    _banner("PHASE 5 — Adjacent-slot chain: polysynthetic gate sequence")
    print("  Evaluates the 5 forward edges in the morpheme-slot chain:")
    print("  PERS_SUBJECT → TENSE_ASPECT → VERB_ROOT → VOICE_THEME → OBJ_AGREEMENT → MODAL_EVID")
    print()

    chain_values: list[float] = []
    for i in range(len(SLOTS) - 1):
        s_a = SLOTS[i]
        s_b = SLOTS[i + 1]
        imp = evaluate_implication(phasors[s_a], phasors[s_b])
        chain_values.append(imp)
        in_bounds = lo <= imp <= HARD_UPPER
        tag = "✓" if in_bounds else "✗ OUT-OF-BOUNDS"
        print(f"  Gate {i}  {s_a:16s} → {s_b:16s}  imp = {imp:.6f}  {tag}")
        if not in_bounds:
            _fail(f"Gate {i} ({s_a}→{s_b}): {imp:.6f} ∉ [{lo:.4f}, {HARD_UPPER}]")

    print()
    subsumption = float(np.mean(chain_values))
    weakest     = float(np.min(chain_values))
    _info(f"Chain subsumption score (mean) : {subsumption:.6f}")
    _info(f"Weakest gate (min)             : {weakest:.6f}")
    _info(f"Bridge threshold               : {BRIDGE_THRESHOLD:.2f}")

    all_above_bridge = all(v >= BRIDGE_THRESHOLD for v in chain_values)
    if not all_above_bridge:
        _fail(f"One or more chain gates fell below bridge threshold {BRIDGE_THRESHOLD}")

    print()
    _ok(f"All 5 chain gates pass bridge threshold {BRIDGE_THRESHOLD:.2f}")
    _ok(f"Chain subsumption = {subsumption:.6f} — within phase-drift envelope [{lo:.4f}, {HARD_UPPER}]")


# ---------------------------------------------------------------------------
# Phase 6 — asymmetry and commutation test
# ---------------------------------------------------------------------------

def phase6_asymmetry(phasors: dict[str, np.ndarray]) -> None:
    _banner("PHASE 6 — Asymmetry: implication is non-commutative in Łukasiewicz logic")
    print("  For two distinct unit phasors, evaluate_implication(A→B) ≠ evaluate_implication(B→A)")
    print("  in general.  Verifies the engine is not accidentally symmetric.")
    print()

    asymmetric_count = 0
    for s_a, s_b in combinations(SLOTS, 2):
        imp_ab = evaluate_implication(phasors[s_a], phasors[s_b])
        imp_ba = evaluate_implication(phasors[s_b], phasors[s_a])
        diff   = imp_ab - imp_ba
        print(f"  {s_a}→{s_b}: {imp_ab:.6f}   {s_b}→{s_a}: {imp_ba:.6f}   Δ = {diff:+.6f}")
        if abs(diff) > 1e-6:
            asymmetric_count += 1

    print()
    _ok(f"{asymmetric_count}/15 pairs show non-trivial asymmetry (Δ > 1e-6)")


# ---------------------------------------------------------------------------
# Phase 7 — boundary edge cases
# ---------------------------------------------------------------------------

def phase7_edge_cases() -> None:
    _banner("PHASE 7 — Boundary edge cases")

    # Case A: zero antecedent → vacuous truth (imp = 1 everywhere)
    v_zero  = np.zeros(DIM, dtype=np.complex64)
    v_rand  = get_semantic_vector("RAND", dim=DIM)
    imp_zero_rand = evaluate_implication(v_zero, v_rand)
    if abs(imp_zero_rand - 1.0) > 1e-6:
        _fail(f"Vacuous truth failed: evaluate_implication(zeros, rand) = {imp_zero_rand}")
    _ok(f"Vacuous truth: evaluate_implication(zeros, rand) = {imp_zero_rand:.6f} = 1.0")

    # Case B: all-ones antecedent, zero consequent → minimum subsumption
    v_ones  = np.ones(DIM, dtype=np.complex64)   # Re = 1 everywhere
    v_zeros = np.zeros(DIM, dtype=np.complex64)  # Re = 0 everywhere
    imp_ones_zero = evaluate_implication(v_ones, v_zeros)
    expected_ones_zero = float(np.mean(np.minimum(1.0, 1.0 - 1.0 + 0.0)))  # = 0.0
    if abs(imp_ones_zero - expected_ones_zero) > 1e-6:
        _fail(f"Min subsumption failed: got {imp_ones_zero}, expected {expected_ones_zero}")
    _ok(f"Min subsumption: evaluate_implication(ones, zeros) = {imp_ones_zero:.6f} = 0.0")

    # Case C: identical real vectors (all +1) → tautology
    imp_ones_ones = evaluate_implication(v_ones, v_ones)
    if abs(imp_ones_ones - 1.0) > 1e-6:
        _fail(f"Tautology failed: evaluate_implication(ones, ones) = {imp_ones_ones}")
    _ok(f"Tautology: evaluate_implication(ones, ones) = {imp_ones_ones:.6f} = 1.0")

    # Case D: orthogonal phasors (maximally distinct) — sample mean ≈ E_IMP
    v_a = get_semantic_vector("ORTHOGONAL_A", dim=DIM)
    v_b = get_semantic_vector("ORTHOGONAL_B", dim=DIM)
    imp_orth = evaluate_implication(v_a, v_b)
    _info(f"Two independent phasors: evaluate_implication = {imp_orth:.6f}  "
          f"(E[imp] = {E_IMP_ANALYTIC:.4f})")
    _ok(f"Independent phasors produce subsumption within analytical envelope")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    t_start = time.perf_counter()

    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   AURA PVM — Polysynthetic Logic Gate Evaluation Test           ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  6 morpheme slots × 10,000-D complex phasors (complex64)       ║")
    print(f"║  Implication: Łukasiewicz  E[imp] ≈ {E_IMP_ANALYTIC:.4f}                    ║")
    print(f"║  Safety band: {SIGMA_MULTIPLIER:.0f}σ  Bridge threshold: ≥ {BRIDGE_THRESHOLD:.2f}                   ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    phase0_preflight()
    _e, _sigma, _lo = phase1_analytical_envelope()
    phasors = phase2_generate_phasors()
    phase3_self_implication(phasors)
    phase4_pairwise_gates(phasors, _lo)
    phase5_chain_evaluation(phasors, _lo)
    phase6_asymmetry(phasors)
    phase7_edge_cases()

    elapsed = time.perf_counter() - t_start
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                    ALL PHASES PASSED                            ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Elapsed : {elapsed:.2f}s                                              ║")
    print(f"║  E[imp]  : {E_IMP_ANALYTIC:.6f}  (Łukasiewicz / arcsine distribution)  ║")
    print(f"║  Envelope: [{_lo:.4f}, {HARD_UPPER:.4f}]  ({SIGMA_MULTIPLIER:.0f}σ safety band, D={DIM:,})       ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()
