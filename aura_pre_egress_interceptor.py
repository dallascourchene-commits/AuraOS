"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: __future__, numpy, typing, os, aura_gbnf_profiles, dataclasses, hashlib
FUNCTIONS: _seeded_hv, bind, bundle, permute, cosine, allocate_slot_matrix, _class_state_for_text, compile_intent_slots, _read_thermal_c, intercept_matrix, intercept_prompt, apply_pre_egress_profile
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from typing import Any

import numpy as np

from aura_gbnf_profiles import PROFILE_POLYSYNTHETIC, PROFILE_VSA_CODE_DEV

DIMENSIONS = 10_000
SLOTS = 6
CLASS_ROW = 2
STATE_PERMUTATION_SHIFT = 4_097


def _seeded_hv(label: str) -> np.ndarray:
    """Deterministically allocate a dense complex64 10,000-D hypervector."""
    seed = int.from_bytes(hashlib.blake2b(label.encode("utf-8"), digest_size=8).digest(), "big")
    rng = np.random.default_rng(seed)
    phases = rng.integers(0, 4, size=DIMENSIONS, dtype=np.int8)
    real = np.where((phases == 0) | (phases == 3), 1.0, -1.0).astype(np.float32, copy=False)
    imag = np.where((phases == 0) | (phases == 1), 1.0, -1.0).astype(np.float32, copy=False)
    hv = (real + 1j * imag).astype(np.complex64, copy=False)
    hv /= np.complex64(np.sqrt(2.0))
    return hv


def bind(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """VSA binding (⊗): elementwise multiplication, invertible by conjugate."""
    return np.multiply(left, right)


def bundle(*vectors: np.ndarray) -> np.ndarray:
    """VSA bundling (⊕): superposition of vectors."""
    out = np.zeros(DIMENSIONS, dtype=np.complex64)
    for vector in vectors:
        out += vector
    return out


def permute(vector: np.ndarray, steps: int = STATE_PERMUTATION_SHIFT) -> np.ndarray:
    """VSA permutation (Π): cyclic coordinate shift for ordered state tracking."""
    return np.roll(vector, steps).astype(np.complex64, copy=False)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    """Complex cosine similarity; unrelated seeded concepts are quasi-orthogonal."""
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denom == 0.0:
        return 0.0
    return float(np.real(np.vdot(left, right)) / denom)


SLOT_ANCHORS: tuple[np.ndarray, ...] = (
    _seeded_hv("SLOT::DIR"),
    _seeded_hv("SLOT::ASP"),
    _seeded_hv("SLOT::CLASS"),
    _seeded_hv("SLOT::SUBJ"),
    _seeded_hv("SLOT::VOICE"),
    _seeded_hv("SLOT::STEM"),
)
STATE_CORE = _seeded_hv("STATE::CORE_SYSTEM_BASE")
STATE_CODE_DEV = _seeded_hv("STATE::ADVANCED_CODE_DEVELOPMENT")


@dataclass(frozen=True)
class InterceptorProfile:
    profile_id: str
    trigger_anchor: np.ndarray
    system_prompt: str
    gbnf_profile: str
    thermal_ceiling_c: float


@dataclass(frozen=True)
class InterceptorDecision:
    profile_id: str
    similarity: float
    gbnf_profile: str
    system_prompt: str
    grammar_metadata: dict[str, Any]
    thermal_c: float
    throttled: bool


CORE_PROFILE = InterceptorProfile(
    profile_id="core_system_base",
    trigger_anchor=STATE_CORE,
    gbnf_profile=PROFILE_POLYSYNTHETIC,
    thermal_ceiling_c=82.0,
    system_prompt=(
        "Act as a deterministic VSA Compiler operating under RHFT. Strip all "
        "conversational filler and prose. Process tokens as geometric points in "
        "10,000-D space. If resonance falls below 0.40 against aura.lexc, declare "
        "a logical fracture and trigger a systemic healing loop immediately."
    ),
)
CODE_DEV_PROFILE = InterceptorProfile(
    profile_id="advanced_code_development",
    trigger_anchor=STATE_CODE_DEV,
    gbnf_profile=PROFILE_VSA_CODE_DEV,
    thermal_ceiling_c=78.0,
    system_prompt=(
        "Act as a high-performance AST-to-VSA Compiler and Topology Optimizer. "
        "Locate code fracture coordinates through resonance-valley analysis and "
        "perform surgical, atomic patches preserving V_NODE invariance."
    ),
)
PROFILE_REGISTRY: tuple[InterceptorProfile, ...] = (CORE_PROFILE, CODE_DEV_PROFILE)


def allocate_slot_matrix() -> np.ndarray:
    """Return a preallocated Athabaskan slot buffer V_SYSTEM ∈ C^(6x10000)."""
    return np.zeros((SLOTS, DIMENSIONS), dtype=np.complex64)


def _class_state_for_text(text: str) -> np.ndarray:
    low = text.lower()
    if any(term in low for term in ("code", "patch", "refactor", "ast", "python", "bug", "function")):
        return STATE_CODE_DEV
    return STATE_CORE


def compile_intent_slots(prompt: str, out: np.ndarray | None = None) -> np.ndarray:
    """Compile prompt intent into the 6-slot matrix using slot-anchor binding."""
    matrix = out if out is not None else allocate_slot_matrix()
    if matrix.shape != (SLOTS, DIMENSIONS) or matrix.dtype != np.complex64:
        raise ValueError("slot matrix must have shape (6, 10000) and dtype complex64")
    matrix.fill(0)
    states = (
        _seeded_hv("DIR::EGRESS"),
        permute(_seeded_hv("ASP::PRE_EGRESS")),
        _class_state_for_text(prompt),
        _seeded_hv("SUBJ::ACTIVE_THREAD"),
        _seeded_hv("VOICE::COMPILER"),
        permute(_seeded_hv("STEM::GENERATE")),
    )
    for idx, state in enumerate(states):
        matrix[idx, :] = bind(SLOT_ANCHORS[idx], state)
    return matrix


def _read_thermal_c() -> float:
    raw = os.environ.get("AURA_THERMAL_C", "0").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def intercept_matrix(matrix: np.ndarray) -> InterceptorDecision:
    """Unbind Row 2 ([CLASS]) and select the best static profile in O(1)."""
    if matrix.shape != (SLOTS, DIMENSIONS) or matrix.dtype != np.complex64:
        raise ValueError("slot matrix must have shape (6, 10000) and dtype complex64")
    class_state = bind(np.conjugate(SLOT_ANCHORS[CLASS_ROW]), matrix[CLASS_ROW])
    scored = [(cosine(class_state, profile.trigger_anchor), profile) for profile in PROFILE_REGISTRY]
    similarity, profile = max(scored, key=lambda item: item[0])
    thermal_c = _read_thermal_c()
    throttled = thermal_c >= profile.thermal_ceiling_c
    return InterceptorDecision(
        profile_id=profile.profile_id,
        similarity=round(similarity, 6),
        gbnf_profile=profile.gbnf_profile,
        system_prompt=profile.system_prompt,
        grammar_metadata={
            "vsa_dimensions": DIMENSIONS,
            "class_row": CLASS_ROW,
            "permutation_shift": STATE_PERMUTATION_SHIFT,
            "throttle": "reduce_max_tokens" if throttled else "nominal",
        },
        thermal_c=thermal_c,
        throttled=throttled,
    )


def intercept_prompt(prompt: str, slot_matrix: np.ndarray | None = None) -> InterceptorDecision:
    """Compile prompt into slots when needed, then execute the pre-egress gate."""
    if slot_matrix is not None:
        return intercept_matrix(slot_matrix)
    matrix = compile_intent_slots(prompt)
    return intercept_matrix(matrix)


def apply_pre_egress_profile(prompt: str, slot_matrix: np.ndarray | None = None) -> tuple[str, InterceptorDecision]:
    """Return prompt decorated with the selected pre-egress profile metadata."""
    decision = intercept_prompt(prompt, slot_matrix=slot_matrix)
    wrapped = (
        f"[AURA_PRE_EGRESS_PROFILE id={decision.profile_id} "
        f"gbnf={decision.gbnf_profile} resonance={decision.similarity}]\n"
        f"{decision.system_prompt}\n"
        f"[/AURA_PRE_EGRESS_PROFILE]\n\n{prompt}"
    )
    return wrapped, decision
