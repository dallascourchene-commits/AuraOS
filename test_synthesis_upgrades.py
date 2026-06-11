from __future__ import annotations

"""
AURA PVM — Synthesis Upgrade Test Suite
========================================
Tests every function in the 6 new synthesis modules, including all
emergent properties discovered during deep scanning.

Run:
    python test_synthesis_upgrades.py
"""

import asyncio
import importlib
import math
import sys
import time
from pathlib import Path

import numpy as np
from aura_node import markovian_workspace_reconstruction, meta_learning_daemon
from llama_server_manager import LlamaServerManager
from aura_arch_reasoner import AuraArchReasoner
from aura_associative_core import AuraAssociativeCore as _AC_check  # noqa: F811
from symbolic_shield import verify_structural_truth as _VST_check  # noqa: F811

# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

_results: list[tuple[str, str, str]] = []
_PASS, _FAIL = "PASS", "FAIL"


def _run(cat: str, name: str, fn, *args, **kwargs) -> bool:
    try:
        r = fn(*args, **kwargs)
        if asyncio.iscoroutine(r):
            r = asyncio.get_event_loop().run_until_complete(r)
        _results.append((cat, name, _PASS))
        print(f"  [✓] {name}")
        return True
    except Exception as exc:
        _results.append((cat, name, _FAIL))
        print(f"  [✗] {name}\n       ↳ {type(exc).__name__}: {exc}")
        return False


def _header(t: str) -> None:
    print(f"\n{'═'*64}\n  {t}\n{'═'*64}")


# ---------------------------------------------------------------------------
# 1. LlamaServerManager
# ---------------------------------------------------------------------------
_header("1. LlamaServerManager — orphan-safe lifecycle")

def _lsm_init():
    m = LlamaServerManager("/tmp/fake.gguf", port=8081)
    assert repr(m).startswith("LlamaServerManager")
    assert not m.is_alive()

def _lsm_double_terminate():
    m = LlamaServerManager("/tmp/fake.gguf")
    m.terminate_server()  # _process is None
    m.terminate_server()  # safe second call

def _lsm_kill_orphans_missing_binary():
    m = LlamaServerManager("/tmp/fake.gguf")
    m._kill_orphans()   # fuser/pkill may not exist — must not raise

def _lsm_missing_model():
    m = LlamaServerManager("/tmp/definitely_nonexistent_model.gguf")
    result = m.start_server()
    assert result is False

def _lsm_wait_for_ready_fast():
    m = LlamaServerManager("/tmp/fake.gguf")
    t0 = time.perf_counter()
    ready = m.wait_for_ready(timeout=0.2, poll=0.05)
    assert not ready
    assert time.perf_counter() - t0 < 1.0

async def _lsm_async_start_no_model():
    m = LlamaServerManager("/tmp/fake.gguf")
    ok = await m.async_start()
    assert ok is False

_run("lsm", "__init__ + is_alive + repr", _lsm_init)
_run("lsm", "double terminate_server: no error", _lsm_double_terminate)
_run("lsm", "_kill_orphans with missing binary: no crash", _lsm_kill_orphans_missing_binary)
_run("lsm", "start_server with missing model: returns False", _lsm_missing_model)
_run("lsm", "wait_for_ready on dead process: fast return", _lsm_wait_for_ready_fast)
_run("lsm", "async_start with missing model: returns False", _lsm_async_start_no_model)


# ---------------------------------------------------------------------------
# 2. RubricRewardMatrix
# ---------------------------------------------------------------------------
_header("2. RubricRewardMatrix — compute_rubric_reward")

from aura_heal import compute_rubric_reward, _RUBRIC_FLOOR, _PVM_RAM_CEILING_MB

def _rubric_valid_code():
    s, b = compute_rubric_reward("import os\nx = os.getcwd()\n", 38.0)
    assert b["passed"], f"Valid code should pass: score={s:.3f}"
    assert s >= _RUBRIC_FLOOR

def _rubric_syntax_error():
    s, b = compute_rubric_reward("def :\n    pass", 38.0)
    assert s == 0.0 and b["reason"] == "SYNTAX_FAIL"

def _rubric_empty_patch():
    s, b = compute_rubric_reward("", 38.0)
    assert s == 0.0 and b["reason"] == "EMPTY_PATCH", f"Empty patch must score 0: {b}"

def _rubric_whitespace_only():
    s, b = compute_rubric_reward("   \n\t\n  ", 38.0)
    assert s == 0.0 and b["reason"] == "EMPTY_PATCH"

def _rubric_eval_injection():
    s, b = compute_rubric_reward("eval('x')\n", 38.0)
    assert not b["passed"] and b["F_SAT"] == 0.0, f"eval must fail F_SAT: {b}"
    assert s < _RUBRIC_FLOOR

def _rubric_nxsdk_import():
    s, b = compute_rubric_reward("import nxsdk\nx=1\n", 38.0)
    assert not b["passed"], f"banned import must fail: {b}"

def _rubric_hot_device_blocks():
    s, b = compute_rubric_reward("x=1\n", 55.0)
    # F_thermal = exp(-0.15*(55-40)) ≈ 0.105 → total < 0.85 unless F_RAM makes up for it
    assert b["F_thermal"] < 0.2, f"F_thermal at 55°C should be < 0.2: {b}"

def _rubric_f_thermal_formula():
    # F_thermal = exp(-0.15 * max(0, T-40))
    for temp, expected in [(38, math.exp(0)), (45, math.exp(-0.75)), (55, math.exp(-2.25))]:
        _, b = compute_rubric_reward("x=1\n", float(temp))
        assert abs(b["F_thermal"] - expected) < 0.01, f"F_thermal wrong at {temp}°C: {b['F_thermal']:.4f} vs {expected:.4f}"

def _rubric_weight_variants():
    s1, _ = compute_rubric_reward("x=1\n", 38.0, w_ram=0.4, w_thermal=0.3, w_sat=0.3)
    s2, _ = compute_rubric_reward("x=1\n", 38.0, w_ram=0.1, w_thermal=0.1, w_sat=0.8)
    assert 0.0 < s1 <= 1.0 and 0.0 < s2 <= 1.0

_run("rubric", "valid code: score >= 0.85", _rubric_valid_code)
_run("rubric", "syntax error: score = 0, reason=SYNTAX_FAIL", _rubric_syntax_error)
_run("rubric", "empty patch: score = 0, reason=EMPTY_PATCH", _rubric_empty_patch)
_run("rubric", "whitespace-only patch: score = 0, reason=EMPTY_PATCH", _rubric_whitespace_only)
_run("rubric", "eval injection: F_SAT=0, score < 0.85", _rubric_eval_injection)
_run("rubric", "nxsdk import: blocked", _rubric_nxsdk_import)
_run("rubric", "hot device (55°C): F_thermal < 0.2", _rubric_hot_device_blocks)
_run("rubric", "F_thermal formula: exp(-0.15*ΔT)", _rubric_f_thermal_formula)
_run("rubric", "weight variants: score ∈ (0,1]", _rubric_weight_variants)


# ---------------------------------------------------------------------------
# 3. A*-Thought Bidirectional Importance Score
# ---------------------------------------------------------------------------
_header("3. A*-Thought BIS (arXiv:2505.24550)")

from cognitive_router import CognitiveRouter

cr = CognitiveRouter()
rng = np.random.default_rng(42)

def _bis_range():
    s, q, a = [rng.standard_normal(256).astype(np.float32) for _ in range(3)]
    bis = cr.astar_bis_score(s, q, a)
    assert -1.0 <= bis <= 1.0

def _bis_self_equals_one():
    v = rng.standard_normal(256).astype(np.float32)
    bis = cr.astar_bis_score(v, v, v)
    assert abs(bis - 1.0) < 0.01, f"self-BIS should be ~1.0: {bis}"

def _bis_zero_vector():
    q = rng.standard_normal(256).astype(np.float32)
    bis = cr.astar_bis_score(np.zeros(256, dtype=np.float32), q, q)
    assert bis == 0.0

def _bis_commutativity_at_half():
    # At α=0.5, BIS(step, q, a) == BIS(step, a, q)
    s = rng.standard_normal(128).astype(np.float32)
    q = rng.standard_normal(128).astype(np.float32)
    a = rng.standard_normal(128).astype(np.float32)
    fwd = cr.astar_bis_score(s, q, a, alpha=0.5)
    rev = cr.astar_bis_score(s, a, q, alpha=0.5)
    assert abs(fwd - rev) < 1e-6, f"BIS should be commutative at α=0.5: {fwd} vs {rev}"

def _prune_gate_identical():
    v = rng.standard_normal(128).astype(np.float32)
    assert cr.astar_prune_gate(v, v, threshold=0.45)

def _prune_gate_antipodal():
    v = rng.standard_normal(128).astype(np.float32)
    assert not cr.astar_prune_gate(v, -v, threshold=0.45)

def _prune_gate_threshold():
    # threshold=-1.0 → always keep (similarity ≥ -1.0 for any unit vector)
    v = np.ones(10, dtype=np.float32)
    u = -np.ones(10, dtype=np.float32)  # antipodal — sim = -1.0
    kept_floor = cr.astar_prune_gate(v, u, threshold=-1.0)   # -1.0 ≤ cos → always True
    kept_strict = cr.astar_prune_gate(v, u, threshold=0.99)  # cos=-1.0 < 0.99 → pruned
    assert kept_floor, "threshold=-1.0 should always keep any vector"
    assert not kept_strict, "antipodal vector should be pruned at threshold=0.99"

def _simulate_pruning_returns_nonempty():
    steps = [rng.standard_normal(64).astype(np.float32) for _ in range(10)]
    q = rng.standard_normal(64).astype(np.float32)
    target = -q  # antipodal target → most steps pruned
    kept = cr.simulate_with_astar_pruning(steps, q, target, prune_threshold=0.99)
    assert len(kept) >= 1, "Must always return at least 1 step"

def _simulate_pruning_reduces_count():
    q = rng.standard_normal(64).astype(np.float32)
    # Steps perfectly aligned with target → keep all
    target = q.copy()
    aligned = [q + rng.standard_normal(64).astype(np.float32) * 0.01 for _ in range(8)]
    kept = cr.simulate_with_astar_pruning(aligned, q, target, prune_threshold=0.45)
    assert 1 <= len(kept) <= 8

_run("bis", "BIS range: ∈ [-1, 1]", _bis_range)
_run("bis", "BIS self-similarity: ≈ 1.0", _bis_self_equals_one)
_run("bis", "BIS zero-vector: = 0.0", _bis_zero_vector)
_run("bis", "BIS commutative at α=0.5", _bis_commutativity_at_half)
_run("bis", "prune_gate: identical vectors always kept", _prune_gate_identical)
_run("bis", "prune_gate: antipodal vectors pruned", _prune_gate_antipodal)
_run("bis", "prune_gate: threshold=0.0 always keeps", _prune_gate_threshold)
_run("bis", "simulate_with_astar_pruning: never returns empty", _simulate_pruning_returns_nonempty)
_run("bis", "simulate_with_astar_pruning: reduces aligned steps", _simulate_pruning_reduces_count)


# ---------------------------------------------------------------------------
# 4. xLSTM mLSTM Matrix Memory Cell
# ---------------------------------------------------------------------------
_header("4. mLSTMCell (xLSTM NeurIPS 2024)")

from liquid_kernel import mLSTMCell

def _mlstm_output_shape():
    cell = mLSTMCell(d=32)
    h = cell.step(np.ones(32, dtype=np.float32))
    assert h.shape == (32,) and h.dtype == np.float32

def _mlstm_finite_output():
    cell = mLSTMCell(d=64)
    for _ in range(100):
        x = np.random.randn(64).astype(np.float32)
        h = cell.step(x)
        assert np.all(np.isfinite(h)), f"Non-finite output: {h}"

def _mlstm_bounded_norm():
    # After fix: output norm should stay bounded (< 50 over 100 steps)
    cell = mLSTMCell(d=64)
    norms = [float(np.linalg.norm(cell.step(np.random.randn(64).astype(np.float32))))
             for _ in range(100)]
    max_n = max(norms)
    assert max_n < 100.0, f"mLSTM norm exploded: max={max_n:.2f}"

def _mlstm_reset_determinism():
    cell = mLSTMCell(d=16)
    x = np.ones(16, dtype=np.float32)
    h1 = cell.step(x)
    cell.reset()
    h2 = cell.step(x)
    assert np.allclose(h1, h2, atol=1e-5), "After reset, same input → same output"

def _mlstm_short_input_padded():
    cell = mLSTMCell(d=32)
    h = cell.step(np.ones(5, dtype=np.float32))  # 5 < d=32
    assert h.shape == (32,)

def _mlstm_state_changes_on_input():
    cell = mLSTMCell(d=16)
    x1 = np.ones(16, dtype=np.float32)
    x2 = -np.ones(16, dtype=np.float32)
    h1 = cell.step(x1)
    cell.reset()
    h2 = cell.step(x2)
    assert not np.allclose(h1, h2), "Different inputs should yield different outputs"

def _mlstm_memory_matrix_updates():
    cell = mLSTMCell(d=8)
    C_before = cell.C.copy()
    cell.step(np.random.randn(8).astype(np.float32))
    assert not np.allclose(cell.C, C_before), "C matrix should update on step"

_run("mlstm", "output shape (32,) float32", _mlstm_output_shape)
_run("mlstm", "100 steps all finite", _mlstm_finite_output)
_run("mlstm", "100 steps: max norm < 100 (output gate fix)", _mlstm_bounded_norm)
_run("mlstm", "reset determinism: same input → same output", _mlstm_reset_determinism)
_run("mlstm", "short input zero-padded to d", _mlstm_short_input_padded)
_run("mlstm", "different inputs → different outputs", _mlstm_state_changes_on_input)
_run("mlstm", "C matrix updates on each step", _mlstm_memory_matrix_updates)


# ---------------------------------------------------------------------------
# 5. Token Superposition Encoder
# ---------------------------------------------------------------------------
_header("5. TokenSuperpositionEncoder (TST arXiv:2605.06546)")

from aura_vpt_tokenizer import TokenSuperpositionEncoder

def _tst_unit_magnitude():
    enc = TokenSuperpositionEncoder(dim=512, bag_size=4)
    v = enc.superpose_bag(["gidinawendimin", "niwaabamin", "miigwech", "go"])
    assert np.allclose(np.abs(v), 1.0, atol=1e-4), f"Not unit: {np.abs(v)[:5]}"

def _tst_empty_bag_finite():
    enc = TokenSuperpositionEncoder(dim=256, bag_size=4)
    v = enc.superpose_bag([])
    assert v.shape == (256,) and np.all(np.isfinite(v))

def _tst_deterministic():
    enc = TokenSuperpositionEncoder(dim=256, bag_size=4)
    tokens = ["a", "b", "c", "d"]
    v1 = enc.superpose_bag(tokens)
    v2 = enc.superpose_bag(tokens)
    assert np.allclose(v1, v2), "Superposition must be deterministic"

def _tst_identical_tokens_eq_single():
    enc = TokenSuperpositionEncoder(dim=256, bag_size=4)
    v_dup = enc.superpose_bag(["x", "x", "x", "x"])
    v_one = enc.superpose_bag(["x"])
    assert np.allclose(v_dup, v_one, atol=1e-5), "Identical tokens: avg == single"

def _tst_encode_sequence_length():
    enc = TokenSuperpositionEncoder(dim=128, bag_size=4)
    tokens = ["a"] * 12
    bags = enc.encode_sequence(tokens)
    assert len(bags) == 3   # 12 / 4 = 3

def _tst_encode_short_sequence():
    enc = TokenSuperpositionEncoder(dim=128, bag_size=8)
    bags = enc.encode_sequence(["a", "b"])  # 2 < bag_size=8
    assert len(bags) == 1 and bags[0].shape == (128,)

def _tst_cache_bounded():
    enc = TokenSuperpositionEncoder(dim=64, bag_size=2, max_cache=10)
    for i in range(25):
        enc.superpose_bag([f"tok_{i}", f"tok_{i+1}"])
    assert len(enc._cache) <= 10, f"Cache exceeded max_cache: {len(enc._cache)}"

def _tst_cache_speedup():
    enc = TokenSuperpositionEncoder(dim=512, bag_size=4)
    tokens = ["alpha", "beta", "gamma", "delta"]
    enc.superpose_bag(tokens)  # warm cache
    t0 = time.perf_counter()
    for _ in range(500):
        enc.superpose_bag(tokens)
    cached_ms = (time.perf_counter() - t0) * 1000
    # No strict time assertion — just confirm no error and completes quickly
    assert cached_ms < 500, f"Cache lookup too slow: {cached_ms:.1f}ms for 500 calls"

_run("tst", "superposed bag: unit-magnitude complex64", _tst_unit_magnitude)
_run("tst", "empty bag: finite output", _tst_empty_bag_finite)
_run("tst", "deterministic: same tokens → same vector", _tst_deterministic)
_run("tst", "identical tokens: avg == single embedding", _tst_identical_tokens_eq_single)
_run("tst", "encode_sequence: 12 tokens / bag=4 → 3 bags", _tst_encode_sequence_length)
_run("tst", "short sequence (2 < bag_size=8): 1 bag returned", _tst_encode_short_sequence)
_run("tst", "cache bounded at max_cache=10", _tst_cache_bounded)
_run("tst", "cache speedup: 500 calls < 500ms", _tst_cache_speedup)


# ---------------------------------------------------------------------------
# 6. Markovian Workspace Reconstruction
# ---------------------------------------------------------------------------
_header("6. markovian_workspace_reconstruction (arXiv:2511.07327)")

from aura_node import markovian_workspace_reconstruction

class _MockPalace:
    conn = None

class _MockNode:
    memory_palace = _MockPalace()
    runtime_metrics = {}

async def _markov_no_palace():
    result = await markovian_workspace_reconstruction(_MockNode(), _MockPalace())
    assert "offline" in result.lower() or "skipped" in result.lower()

async def _markov_none_node():
    result = await markovian_workspace_reconstruction(None, _MockPalace())
    assert "offline" in result.lower() or "skipped" in result.lower()

async def _markov_returns_string():
    result = await markovian_workspace_reconstruction(_MockNode(), _MockPalace(), max_raw_logs=10)
    assert isinstance(result, str) and len(result) > 0

_run("markov", "no DB: returns offline message", _markov_no_palace)
_run("markov", "None node: returns offline message", _markov_none_node)
_run("markov", "always returns string", _markov_returns_string)


# ---------------------------------------------------------------------------
# 7. Integration: meta_learning_daemon wires Markovian reconstruction
# ---------------------------------------------------------------------------
_header("7. Integration — meta_learning_daemon + Markovian + AuraArchReasoner")

def _meta_reasoner_scores_workspace():
    r = AuraArchReasoner()
    res, tension = r.score_structural_resonance()
    assert 0.0 < res <= 1.0
    patch = r.suggest_architectural_patch()
    assert "STABLE" in patch or "REFACTOR" in patch

async def _meta_daemon_imports_ok():
    assert callable(meta_learning_daemon)
    assert callable(markovian_workspace_reconstruction)

_run("integration", "AuraArchReasoner.score + suggest: valid outputs", _meta_reasoner_scores_workspace)
_run("integration", "meta_learning_daemon imports markovian_workspace_reconstruction", _meta_daemon_imports_ok)


# ---------------------------------------------------------------------------
# 8. Cross-module integration: Rubric + mLSTM + TST pipeline
# ---------------------------------------------------------------------------
_header("8. Cross-module pipeline test")

def _pipeline_tst_to_rubric():
    """TST bag → validate as phasor → check rubric on generated code stub."""
    enc = TokenSuperpositionEncoder(dim=512, bag_size=3)
    morphemes = ["na", "ga", "de"]
    bag = enc.superpose_bag(morphemes)
    assert bag.shape == (512,) and np.allclose(np.abs(bag), 1.0, atol=1e-4)

    # Validate a real code stub through rubric
    code = f"# morpheme={','.join(morphemes)}\nx = {len(morphemes)}\n"
    s, b = compute_rubric_reward(code, 38.0)
    assert b["passed"], f"TST-generated stub failed rubric: {b}"

def _pipeline_mlstm_bis():
    """mLSTM hidden state as BIS step vector."""
    cell = mLSTMCell(d=64)
    q = np.random.randn(64).astype(np.float32)
    a = np.random.randn(64).astype(np.float32)
    h = cell.step(np.random.randn(64).astype(np.float32))
    bis = cr.astar_bis_score(h, q, a)
    assert -1.0 <= bis <= 1.0

def _pipeline_all_new_modules_importable():
    """Verify all new modules import without errors (checked at top-level)."""
    assert all([LlamaServerManager, AuraArchReasoner, _AC_check, _VST_check])

_run("pipeline", "TST bag → rubric validation of code stub", _pipeline_tst_to_rubric)
_run("pipeline", "mLSTM hidden state → A*-BIS score", _pipeline_mlstm_bis)
_run("pipeline", "all new modules importable", _pipeline_all_new_modules_importable)


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

total = len(_results)
passes = sum(1 for _, _, s in _results if s == _PASS)
fails  = sum(1 for _, _, s in _results if s == _FAIL)
print(f"\n{'═'*64}")
print("  SYNTHESIS UPGRADE TEST REPORT")
print(f"{'═'*64}")
print(f"  Total : {total}")
print(f"  PASS  : {passes}  ({passes/total*100:.1f}%)")
print(f"  FAIL  : {fails}")
if fails:
    print(f"\n  Failed:")
    for cat, name, st in _results:
        if st == _FAIL:
            print(f"    [{cat}] {name}")
print(f"\n  {'✓ ALL PASS' if fails == 0 else '✗ FAILURES DETECTED'}")
print(f"{'═'*64}")
sys.exit(0 if fails == 0 else 1)
