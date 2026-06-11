"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8v1-[Q-SYS:VALIDATION_RUBRIC_CORE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity)
DEPENDENCIES: ast, gc, time, numpy
FUNCTIONS: calculate_rubric_score, validate_patch_candidate, ram_fitness, thermal_fitness
SYNOPSIS: Process-supervised Rubric Reward Matrix (R_rubric) for AuraOS patch validation.
          Enforces R_rubric >= 0.85 threshold before any AI-generated patch is written to
          the physical filesystem. Integrates RAM fitness, thermal fitness, and AST
          syntax-gate checks as sub-components of the multi-tiered reward matrix.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import ast
import gc
import math
import time
from typing import Any, Dict, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Constants (aligned to Section 4.4 of aura_upgrade_spec.docx)
# ---------------------------------------------------------------------------
_RUBRIC_PASS_THRESHOLD: float = 0.85   # Rub_rubric >= 0.85 required for deploy
_RAM_CEILING_MB: float = 4096.0        # 4 GB physical ceiling
_THERMAL_DECAY_OMEGA: float = 0.05     # ω for thermal fitness exp(-ω·ΔT)
_BASELINE_CPU_TEMP_C: float = 35.0     # Reference idle temperature (°C)


# ---------------------------------------------------------------------------
# Sub-fitness components
# ---------------------------------------------------------------------------

def ram_fitness(memory_peak_mb: float) -> float:
    """
    F_RAM(τ) = max(0, 1 - MemoryPeak / 4GB)

    Returns a score in [0, 1] where 1.0 means no memory pressure at all.
    Falls to 0.0 at or above the 4 GB ceiling.
    """
    return max(0.0, 1.0 - memory_peak_mb / _RAM_CEILING_MB)


def thermal_fitness(cpu_temp_c: float) -> float:
    """
    F_thermal(τ) = exp(-ω · ΔT_CPU)

    ΔT is measured relative to the baseline idle temperature.
    Higher temperatures produce lower scores.
    """
    delta_t = max(0.0, cpu_temp_c - _BASELINE_CPU_TEMP_C)
    return math.exp(-_THERMAL_DECAY_OMEGA * delta_t)


def _ast_gate(code_str: str) -> float:
    """
    Binary indicator I(Y=1): 1.0 if the code parses cleanly, 0.0 otherwise.

    The AST parse-gate from Section 4.4 — no partially-valid code is ever
    deployed to the Termux directory.
    """
    if not isinstance(code_str, str) or not code_str.strip():
        return 0.0
    try:
        ast.parse(code_str)
        return 1.0
    except SyntaxError:
        return 0.0


def _sat_score(context: Dict[str, Any]) -> float:
    """
    F_SAT(τ): Satisfiability score from truth resonance.

    Derived heuristically from context signals when no LNN reasoner is
    available: confidence, resonance_score, submodel success ratio, etc.
    Falls back to 0.5 (neutral) when signals are absent.
    """
    signals: list[float] = []

    # Confidence signal
    conf = context.get("confidence")
    if conf is not None:
        signals.append(float(np.clip(conf, 0.0, 1.0)))

    # Resonance score signal
    res = context.get("resonance_score")
    if res is not None:
        signals.append(float(np.clip(res, 0.0, 1.0)))

    # Submodel success ratio (federated HDC)
    sc = context.get("submodel_count")
    sr = context.get("total_processed")
    if sc and sr:
        signals.append(min(1.0, float(sr) / max(1, float(sc))))

    # Weight norm variance — low variance → higher coherence
    wn = context.get("weight_norms")
    if wn and len(wn) > 1:
        cv = float(np.std(wn)) / (float(np.mean(wn)) + 1e-8)
        signals.append(max(0.0, 1.0 - cv))

    # Hint quality (transparency processor)
    hints_received = context.get("hints_received", False)
    if hints_received:
        signals.append(0.8)

    return float(np.mean(signals)) if signals else 0.5


# ---------------------------------------------------------------------------
# Primary public API
# ---------------------------------------------------------------------------

def calculate_rubric_score(
    context: Dict[str, Any],
    code_str: Optional[str] = None,
    memory_peak_mb: float = 0.0,
    cpu_temp_c: float = _BASELINE_CPU_TEMP_C,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Compute the multi-tiered Rubric Reward Matrix score R_rubric(τ).

    R_rubric = I(Y=1) · [w_ram·F_RAM + w_thermal·F_thermal + w_sat·F_SAT]

    Parameters
    ----------
    context        : dict of runtime signals (confidence, resonance_score,
                     weight_norms, submodel_count, total_processed, …)
    code_str       : optional Python source to run through the AST gate
    memory_peak_mb : peak RSS in MB for the evaluated candidate
    cpu_temp_c     : CPU temperature (°C) at evaluation time
    weights        : optional override for component weights
                     default: {'ram': 0.35, 'thermal': 0.25, 'sat': 0.40}

    Returns
    -------
    float in [0.0, 1.0]
    """
    # Default weights sum to 1.0
    w = weights or {"ram": 0.35, "thermal": 0.25, "sat": 0.40}

    # AST gate is a binary indicator — a syntax failure returns 0 immediately
    if code_str is not None:
        if _ast_gate(code_str) == 0.0:
            return 0.0

    # Sub-fitness components
    f_ram     = ram_fitness(memory_peak_mb)
    f_thermal = thermal_fitness(cpu_temp_c)
    f_sat     = _sat_score(context)

    score = (
        w.get("ram", 0.35)     * f_ram
        + w.get("thermal", 0.25) * f_thermal
        + w.get("sat", 0.40)    * f_sat
    )

    return float(np.clip(score, 0.0, 1.0))


def validate_patch_candidate(
    patch_code: str,
    context: Optional[Dict[str, Any]] = None,
    memory_peak_mb: float = 0.0,
    cpu_temp_c: float = _BASELINE_CPU_TEMP_C,
) -> tuple[bool, float]:
    """
    High-level patch gate: returns (approved, score).

    A patch is approved only when R_rubric >= 0.85 AND the code
    passes the AST parse gate.  This is the mandatory pre-flight
    check for all AI-generated patches per Section 9 of the spec.

    Usage
    -----
        approved, score = validate_patch_candidate(generated_code, context)
        if approved:
            write_to_disk(generated_code)
    """
    ctx = context or {}
    score = calculate_rubric_score(
        context=ctx,
        code_str=patch_code,
        memory_peak_mb=memory_peak_mb,
        cpu_temp_c=cpu_temp_c,
    )
    approved = score >= _RUBRIC_PASS_THRESHOLD
    return approved, score
