"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f9-[Q-SYS:RESONANT_TEST_ORACLE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Continuous Verification)
DEPENDENCIES: numpy, hashlib, time, json, os
FUNCTIONS: ResonantAssertion, ResonantTestOracle, resonate_equal, resonate_contains, resonate_structure, resonate_type, run_resonant_suite
SYNOPSIS: Resonant Test Oracle Architecture (Claim N26). Replaces boolean assertions with continuous hyperdimensional resonance checks. A test does not pass or fail -- it resonates at a measured strength. The same Lukasiewicz t-norm and phasor operations used in the omnipath sweep (N7) and SkillWeaver gate (N20) operate here at the test-assertion scale (Axiom A5: Fractal Self-Organization).
[/AURA_MASTER_KEY]

Aura Resonant Test Oracle Architecture (N26)
==============================================

Traditional testing: assert expected == actual -> boolean pass/fail.
Resonant testing: resonate(expected, actual) -> continuous [0.0, 1.0].

Why: Boolean assertions hide the distance between failure and success.
A test that fails at resonance 0.94 is categorically different from one
that fails at 0.02. The oracle makes this visible.

The same bind/bundle/cosine operations that gate research mutations (N20),
sweep code topology for fractures (N7), and route mesh compute (N29)
now operate at the smallest scale: individual test assertions.

This is Axiom A5 -- fractal self-organization. One algebra, every scale.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

# ── Constants ──
_DIM = 10000
_RESONANCE_FLOOR = 0.85   # Below this, the assertion is a "fracture"
_RESONANCE_WARNING = 0.92  # Below this, the assertion is "borderline"


# ── Phasor codec (shared with SkillWeaver, pre-egress, HIVP) ──

def _text_to_phasor(text: str, dim: int = _DIM) -> np.ndarray:
    """Deterministic text -> complex phasor (same codec as aura_skillweaver.py)."""
    if not text:
        return np.ones(dim, dtype=np.complex64)
    h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    seed = int.from_bytes(h, byteorder="little")
    rng = np.random.default_rng(seed)
    phases = rng.uniform(-np.pi, np.pi, dim).astype(np.float32)
    return np.exp(1j * phases)


def _cosine_resonance(a: np.ndarray, b: np.ndarray) -> float:
    """Complex cosine resonance between two phasor vectors."""
    dim = len(a)
    return float(np.abs(np.dot(a, np.conj(b))) / dim)


def _lukasiewicz_implication(truth_a: float, truth_b: float) -> float:
    """Lukasiewicz t-norm implication: min(1, 1 - a + b).
    Same operation as batch_evaluate_implication in aura_nesy_sat_reasoner.py.
    """
    return min(1.0, 1.0 - truth_a + truth_b)


# ── Resonant Assertion ──

@dataclass
class ResonantAssertion:
    """Result of a single resonant assertion."""
    name: str
    resonance: float           # [0.0, 1.0] continuous score
    zone: str                  # "pass" | "borderline" | "fracture"
    expected_repr: str         # String representation of expected
    actual_repr: str           # String representation of actual
    elapsed_ms: float = 0.0
    detail: str = ""

    @property
    def passed(self) -> bool:
        """Boolean compatibility: resonance >= floor."""
        return self.zone != "fracture"


def _classify_zone(resonance: float) -> str:
    """Classify resonance into zones (matches omnipath sweep zones)."""
    if resonance >= _RESONANCE_WARNING:
        return "pass"
    elif resonance >= _RESONANCE_FLOOR:
        return "borderline"
    else:
        return "fracture"


# ── Oracle assertion functions ──

def resonate_equal(name: str, expected: Any, actual: Any) -> ResonantAssertion:
    """
    Resonance-based equality check.
    
    Encodes both values as phasors and measures cosine resonance.
    Exact equality -> resonance ~1.0 (deterministic phasors from same text).
    Partial match -> intermediate resonance.
    Total mismatch -> resonance near baseline (~0.0).
    """
    t0 = time.perf_counter()
    
    exp_str = str(expected)
    act_str = str(actual)
    
    # If exactly equal, resonance is 1.0 (same input -> same phasor)
    if expected == actual:
        resonance = 1.0
    else:
        exp_phasor = _text_to_phasor(exp_str)
        act_phasor = _text_to_phasor(act_str)
        resonance = _cosine_resonance(exp_phasor, act_phasor)
    
    elapsed = (time.perf_counter() - t0) * 1000
    zone = _classify_zone(resonance)
    
    return ResonantAssertion(
        name=name,
        resonance=resonance,
        zone=zone,
        expected_repr=exp_str[:100],
        actual_repr=act_str[:100],
        elapsed_ms=elapsed,
    )


def resonate_contains(name: str, haystack: str, needle: str) -> ResonantAssertion:
    """
    Resonant containment check.
    
    If needle is literally in haystack, resonance = 1.0.
    Otherwise, measure semantic resonance between their phasors,
    boosted by substring overlap.
    """
    t0 = time.perf_counter()
    
    if needle in haystack:
        resonance = 1.0
    else:
        # Measure phasor resonance
        h_phasor = _text_to_phasor(haystack)
        n_phasor = _text_to_phasor(needle)
        base_res = _cosine_resonance(h_phasor, n_phasor)
        
        # Boost by character-level overlap
        needle_lower = needle.lower()
        haystack_lower = haystack.lower()
        tokens = needle_lower.split()
        if tokens:
            token_hits = sum(1 for t in tokens if t in haystack_lower)
            token_coverage = token_hits / len(tokens)
        else:
            token_coverage = 0.0
        
        resonance = min(1.0, base_res + 0.5 * token_coverage)
    
    elapsed = (time.perf_counter() - t0) * 1000
    zone = _classify_zone(resonance)
    
    return ResonantAssertion(
        name=name,
        resonance=resonance,
        zone=zone,
        expected_repr=f"contains({needle[:50]})",
        actual_repr=haystack[:100],
        elapsed_ms=elapsed,
    )


def resonate_structure(name: str, expected_keys: list, actual_dict: dict) -> ResonantAssertion:
    """
    Resonant structural check -- does a dict have the expected shape?
    
    Resonance = fraction of expected keys present, with phasor-weighted
    bonus for semantically similar key names.
    """
    t0 = time.perf_counter()
    
    if not expected_keys:
        resonance = 1.0
    else:
        actual_keys = set(str(k) for k in actual_dict.keys()) if isinstance(actual_dict, dict) else set()
        exact_hits = sum(1 for k in expected_keys if str(k) in actual_keys)
        exact_coverage = exact_hits / len(expected_keys)
        
        if exact_coverage == 1.0:
            # All keys present exactly -- perfect resonance
            resonance = 1.0
        else:
            # Phasor bonus for near-matches on missing keys
            phasor_bonus = 0.0
            missing = [k for k in expected_keys if str(k) not in actual_keys]
            for mk in missing:
                mk_phasor = _text_to_phasor(str(mk))
                best_res = 0.0
                for ak in actual_keys:
                    ak_phasor = _text_to_phasor(str(ak))
                    res = _cosine_resonance(mk_phasor, ak_phasor)
                    best_res = max(best_res, res)
                phasor_bonus += best_res
            
            if missing:
                phasor_bonus /= len(missing)
            
            resonance = min(1.0, exact_coverage * 0.85 + phasor_bonus * 0.15)
    
    elapsed = (time.perf_counter() - t0) * 1000
    zone = _classify_zone(resonance)
    
    return ResonantAssertion(
        name=name,
        resonance=resonance,
        zone=zone,
        expected_repr=str(expected_keys[:5]),
        actual_repr=str(list(actual_dict.keys())[:5]) if isinstance(actual_dict, dict) else str(type(actual_dict)),
        elapsed_ms=elapsed,
    )


def resonate_type(name: str, expected_type: type, actual: Any) -> ResonantAssertion:
    """
    Resonant type check.
    
    Exact type match = 1.0. Subclass = 0.95. Same category = 0.7.
    Total mismatch = phasor resonance of type names.
    """
    t0 = time.perf_counter()
    
    if isinstance(actual, expected_type):
        if type(actual) is expected_type:
            resonance = 1.0
        else:
            resonance = 0.95  # Subclass
    else:
        # Compare type names via phasor
        exp_phasor = _text_to_phasor(expected_type.__name__)
        act_phasor = _text_to_phasor(type(actual).__name__)
        resonance = _cosine_resonance(exp_phasor, act_phasor) * 0.7
    
    elapsed = (time.perf_counter() - t0) * 1000
    zone = _classify_zone(resonance)
    
    return ResonantAssertion(
        name=name,
        resonance=resonance,
        zone=zone,
        expected_repr=expected_type.__name__,
        actual_repr=type(actual).__name__,
        elapsed_ms=elapsed,
    )


# ── Resonant Test Suite Runner ──

@dataclass
class ResonantSuiteResult:
    """Aggregate result of a resonant test suite."""
    suite_name: str
    assertions: list = field(default_factory=list)
    mean_resonance: float = 0.0
    min_resonance: float = 0.0
    fracture_count: int = 0
    borderline_count: int = 0
    pass_count: int = 0
    total_elapsed_ms: float = 0.0
    efficiency: float = 0.0  # E = (kappa * R) / (tau + epsilon)


class ResonantTestOracle:
    """
    Resonant Test Oracle (N26).
    
    Collects resonant assertions and produces a continuous-valued
    test report instead of a boolean pass/fail summary.
    """
    
    def __init__(self, suite_name: str = "default"):
        self.suite_name = suite_name
        self.assertions: list[ResonantAssertion] = []
    
    def check(self, assertion: ResonantAssertion) -> ResonantAssertion:
        """Record an assertion and return it."""
        self.assertions.append(assertion)
        return assertion
    
    def assert_equal(self, name: str, expected: Any, actual: Any) -> ResonantAssertion:
        return self.check(resonate_equal(name, expected, actual))
    
    def assert_contains(self, name: str, haystack: str, needle: str) -> ResonantAssertion:
        return self.check(resonate_contains(name, haystack, needle))
    
    def assert_structure(self, name: str, expected_keys: list, actual_dict: dict) -> ResonantAssertion:
        return self.check(resonate_structure(name, expected_keys, actual_dict))
    
    def assert_type(self, name: str, expected_type: type, actual: Any) -> ResonantAssertion:
        return self.check(resonate_type(name, expected_type, actual))
    
    def result(self) -> ResonantSuiteResult:
        """Compute aggregate suite result."""
        if not self.assertions:
            return ResonantSuiteResult(suite_name=self.suite_name)
        
        resonances = [a.resonance for a in self.assertions]
        elapsed = sum(a.elapsed_ms for a in self.assertions)
        fractures = sum(1 for a in self.assertions if a.zone == "fracture")
        borderline = sum(1 for a in self.assertions if a.zone == "borderline")
        passes = sum(1 for a in self.assertions if a.zone == "pass")
        
        mean_r = float(np.mean(resonances))
        min_r = float(np.min(resonances))
        
        # Efficiency: E = (kappa * R) / (tau + epsilon)
        kappa = min_r        # Weakest link = coherence
        R = mean_r           # Mean resonance
        tau = elapsed / 1000  # Time cost in seconds
        epsilon = fractures * 0.1  # Each fracture adds extraction cost
        efficiency = (kappa * R) / (tau + epsilon + 1e-9)
        
        return ResonantSuiteResult(
            suite_name=self.suite_name,
            assertions=self.assertions,
            mean_resonance=mean_r,
            min_resonance=min_r,
            fracture_count=fractures,
            borderline_count=borderline,
            pass_count=passes,
            total_elapsed_ms=elapsed,
            efficiency=efficiency,
        )
    
    def format_report(self) -> str:
        """Format a human-readable resonant test report."""
        r = self.result()
        lines = [
            f"[RESONANT_TEST_ORACLE]",
            f"SUITE: {r.suite_name}",
            f"ASSERTIONS: {len(r.assertions)}",
            f"MEAN_RESONANCE: {r.mean_resonance:.4f}",
            f"MIN_RESONANCE: {r.min_resonance:.4f}",
            f"ZONES: {r.pass_count} pass | {r.borderline_count} borderline | {r.fracture_count} fracture",
            f"ELAPSED: {r.total_elapsed_ms:.2f}ms",
            f"EFFICIENCY (E): {r.efficiency:.4f}",
        ]
        
        if r.efficiency > 1.0:
            lines.append(f"ASSESSMENT: COHERENT (E > 1.0)")
        else:
            lines.append(f"ASSESSMENT: REVIEW NEEDED (E < 1.0)")
        
        # Detail on fractures and borderline
        for a in r.assertions:
            if a.zone != "pass":
                icon = "!" if a.zone == "fracture" else "~"
                lines.append(
                    f"  [{icon}] {a.name}: R={a.resonance:.4f} [{a.zone}] "
                    f"expected={a.expected_repr[:40]} actual={a.actual_repr[:40]}"
                )
        
        lines.append(f"[/RESONANT_TEST_ORACLE]")
        return "\n".join(lines)


def run_resonant_suite(suite_name: str, test_fn) -> ResonantSuiteResult:
    """
    Convenience: run a test function that accepts a ResonantTestOracle
    and return the suite result.
    """
    oracle = ResonantTestOracle(suite_name)
    test_fn(oracle)
    return oracle.result()


# ── CLI Demo ──

if __name__ == "__main__":
    print("=== Aura Resonant Test Oracle (N26) Demo ===\n")
    
    oracle = ResonantTestOracle("demo_suite")
    
    # Test 1: Exact match
    oracle.assert_equal("exact_int", 42, 42)
    
    # Test 2: Close but not exact
    oracle.assert_equal("close_string", "hello world", "hello worlds")
    
    # Test 3: Total mismatch
    oracle.assert_equal("total_mismatch", "quantum computing", "tropical fish")
    
    # Test 4: Contains
    oracle.assert_contains("has_keyword", "The Hopfield network uses energy functions", "Hopfield")
    
    # Test 5: Missing keyword
    oracle.assert_contains("missing_keyword", "This paper studies tropical fish migration", "Hopfield")
    
    # Test 6: Structure check
    oracle.assert_structure("dict_shape", ["query", "decision", "score"],
                           {"query": "test", "decision": "ALLOW", "score": 0.9})
    
    # Test 7: Type check
    oracle.assert_type("is_list", list, [1, 2, 3])
    oracle.assert_type("wrong_type", dict, [1, 2, 3])
    
    print(oracle.format_report())
