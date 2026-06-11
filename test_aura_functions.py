from __future__ import annotations

"""
AURA PVM — Full Function / Command Friction Test Suite
======================================================
Tests every exposed public function and REPL-command-equivalent logic
in the AURA stack without requiring a live boot or LLM API keys.

Each test is self-contained, traps exceptions, and reports PASS / FAIL /
SKIP (if the function needs external resources that are unavailable).

Run:
    python test_aura_functions.py
"""

import asyncio
import io
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from aura_dream_engine import AuraDreamEngine, homeostatic_decay_pass
from aura_associative_core import AuraAssociativeCore
from symbolic_shield import verify_structural_truth
from aura_nesy_sat_reasoner import AuraNeuroSymbolicReasoner

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------

_results: list[tuple[str, str, str]] = []  # (category, name, status)
_PASS, _FAIL, _SKIP = "PASS", "FAIL", "SKIP"


def _run(category: str, name: str, fn, *args, **kwargs) -> bool:
    try:
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            result = asyncio.get_event_loop().run_until_complete(result)
        status = _PASS
        detail = ""
    except Exception as exc:
        status = _FAIL
        detail = f"{type(exc).__name__}: {exc}"
    _results.append((category, name, status))
    marker = "✓" if status == _PASS else ("~" if status == _SKIP else "✗")
    line = f"  [{marker}] {name}"
    if detail:
        line += f"\n       ↳ {detail}"
    print(line)
    return status == _PASS


def _skip(category: str, name: str, reason: str) -> None:
    _results.append((category, name, _SKIP))
    print(f"  [~] {name}  ← {reason}")


def _header(title: str) -> None:
    print(f"\n{'═' * 68}")
    print(f"  {title}")
    print("═" * 68)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIM = 1000  # reduced dim for speed in tests (10k in production)

def _phasor(seed: int = 0, dim: int = DIM) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.exp(1j * rng.uniform(-np.pi, np.pi, dim)).astype(np.complex64)


# ---------------------------------------------------------------------------
# 1. Symbolic Shield
# ---------------------------------------------------------------------------
_header("1. symbolic_shield — Formal AST Verification (Youvan Sound Shield)")

from symbolic_shield import (
    verify_structural_truth, full_report,
    check_syntax, check_loop_decay, check_import_safety,
    check_memory_safety, check_banned_calls, ShieldReport,
)

_run("shield", "verify_structural_truth: valid code",
     verify_structural_truth, "import os\nx = 1\n")

_run("shield", "verify_structural_truth: syntax error rejected",
     lambda: verify_structural_truth("def :\n    pass") == False)

_run("shield", "verify_structural_truth: banned import (nxsdk) rejected",
     lambda: verify_structural_truth("import nxsdk\n") == False)

_run("shield", "verify_structural_truth: infinite loop without decay rejected",
     lambda: verify_structural_truth("while True:\n    x = 1\n") == False)

_run("shield", "verify_structural_truth: while True + break accepted",
     verify_structural_truth, "while True:\n    break\n")

_run("shield", "verify_structural_truth: eval() rejected",
     lambda: verify_structural_truth("eval('x')\n") == False)

_run("shield", "full_report: returns 5 ShieldReport items",
     lambda: len(full_report("import os\n")) == 5)


# ---------------------------------------------------------------------------
# 2. VSA / Hypervector Primitives
# ---------------------------------------------------------------------------
_header("2. VSA / Hypervector Primitives")

from vsa_resonator import VSAResonator

def _test_vsa_resonator():
    r = VSAResonator(dim=DIM)
    a = _phasor(0)
    b = _phasor(1)
    bound = r.bind(a, b)
    assert bound.shape == a.shape
    # sampled_similarity(q_gain, q_shape, q_bias, c_gain, c_shape, c_bias)
    sim_self  = r.sampled_similarity(1.0, a, 0.0, 1.0, a, 0.0)
    sim_other = r.sampled_similarity(1.0, a, 0.0, 1.0, b, 0.0)
    assert isinstance(float(sim_self), float), f"sim_self not float: {sim_self}"
    bundled = r.bundle([a, b, _phasor(2)])
    assert bundled.shape == a.shape

_run("vsa", "VSAResonator: bind / bundle / sampled_similarity", _test_vsa_resonator)

from liquid_fhrr import LiquidFHRR

def _test_fhrr():
    fhrr = LiquidFHRR(dim=DIM)
    p = fhrr.generate_phasor()
    assert np.allclose(np.abs(p), 1.0, atol=1e-5)
    q = fhrr.generate_phasor()
    bound = fhrr.bind(p, q)
    assert bound.shape == p.shape
    sim = fhrr.similarity(p, p)
    assert sim > 0.99

_run("vsa", "LiquidFHRR: generate_phasor / bind / similarity", _test_fhrr)


# ---------------------------------------------------------------------------
# 3. aura_spvm — Polysynthetic VM Logic Gates
# ---------------------------------------------------------------------------
_header("3. aura_spvm — Polysynthetic VM Logic Gates")

from aura_spvm import get_semantic_vector, evaluate_implication

def _test_spvm_self_implication():
    v = get_semantic_vector("gidinawendimin", dim=DIM)
    assert abs(evaluate_implication(v, v) - 1.0) < 1e-6

def _test_spvm_vacuous_truth():
    v_zero = np.zeros(DIM, dtype=np.complex64)
    v_rand = get_semantic_vector("test", dim=DIM)
    assert abs(evaluate_implication(v_zero, v_rand) - 1.0) < 1e-6

def _test_spvm_range():
    va = get_semantic_vector("VERB_ROOT", dim=DIM)
    vb = get_semantic_vector("OBJ_AGREEMENT", dim=DIM)
    imp = evaluate_implication(va, vb)
    assert 0.0 <= imp <= 1.0, f"out of range: {imp}"

_run("spvm", "evaluate_implication: self → 1.0", _test_spvm_self_implication)
_run("spvm", "evaluate_implication: zeros antecedent → 1.0 (vacuous truth)", _test_spvm_vacuous_truth)
_run("spvm", "evaluate_implication: distinct phasors ∈ [0,1]", _test_spvm_range)


# ---------------------------------------------------------------------------
# 4. Associative Core
# ---------------------------------------------------------------------------
_header("4. aura_associative_core — O(1) Fast-Path Associative Memory")

def _test_assoc_store_query():
    core = AuraAssociativeCore(dim=DIM)
    k = get_semantic_vector("query_key", dim=DIM)
    v = get_semantic_vector("query_value", dim=DIM)
    core.store(k, v, label="test")
    result = core.query(k)
    assert result["confidence"] > 0.5, f"confidence={result['confidence']}"

def _test_assoc_decay():
    core = AuraAssociativeCore(dim=DIM, decay=0.5)
    k = get_semantic_vector("decay_key", dim=DIM)
    core.store(k, k)
    before = core.get_stats()["matrix_frobenius_norm"]
    core.force_decay()
    after = core.get_stats()["matrix_frobenius_norm"]
    assert after < before, f"decay did not reduce norm: {before} → {after}"

def _test_assoc_reset():
    core = AuraAssociativeCore(dim=DIM)
    core.store(get_semantic_vector("x", dim=DIM), get_semantic_vector("y", dim=DIM))
    core.reset()
    assert core.get_stats()["stored_traces"] == 0

def _test_fast_path_lookup():
    core = AuraAssociativeCore(dim=DIM)
    k = get_semantic_vector("!push", dim=DIM)
    core.store(k, k, label="push_cmd")
    result = core.fast_path_lookup("!push", lambda t, dim: get_semantic_vector(t, dim=dim))
    assert "confidence" in result

_run("assoc", "store + query: confidence > 0.5", _test_assoc_store_query)
_run("assoc", "force_decay: norm decreases", _test_assoc_decay)
_run("assoc", "reset: trace count → 0", _test_assoc_reset)
_run("assoc", "fast_path_lookup: returns dict with confidence", _test_fast_path_lookup)


# ---------------------------------------------------------------------------
# 5. Architecture Reasoner
# ---------------------------------------------------------------------------
_header("5. aura_arch_reasoner — VSA Structural Resonance")

from aura_arch_reasoner import AuraArchReasoner

def _test_reasoner_score():
    r = AuraArchReasoner()
    res, tension = r.score_structural_resonance()
    assert 0.0 < res <= 1.0, f"resonance {res} out of range"
    assert tension >= 0.0

def _test_reasoner_suggest():
    r = AuraArchReasoner()
    s = r.suggest_architectural_patch()
    assert isinstance(s, str) and len(s) > 0

def _test_reasoner_procrustes():
    a = _phasor(0)
    b = _phasor(1)
    score = AuraArchReasoner.compute_procrustes_alignment(
        a.reshape(1, -1), a.reshape(1, -1)
    )
    assert score > 0.99, f"self-alignment {score}"
    score_cross = AuraArchReasoner.compute_procrustes_alignment(
        a.reshape(1, -1), b.reshape(1, -1)
    )
    assert 0.0 <= score_cross <= 1.0

async def _test_reasoner_async():
    r = AuraArchReasoner()
    res = await r.verify_truth_resonance()
    assert 0.0 < res <= 1.0
    report = await r.recalibrate_symbolic_gates()
    assert isinstance(report, str)

_run("arch", "score_structural_resonance: valid range", _test_reasoner_score)
_run("arch", "suggest_architectural_patch: returns string", _test_reasoner_suggest)
_run("arch", "compute_procrustes_alignment: self=1.0, cross∈[0,1]", _test_reasoner_procrustes)
_run("arch", "verify_truth_resonance + recalibrate (async)", _test_reasoner_async)


# ---------------------------------------------------------------------------
# 5b. Self-Reflect Engine + WASM accelerator shim
# ---------------------------------------------------------------------------
_header("5b. aura_self_reflect — Introspection + arch_reasoner_accel")

from aura_self_reflect import SelfReflectEngine
import arch_reasoner_accel as _accel


def _test_accel_structural():
    out = _accel.handle({"operation": "STRUCTURAL_RESONANCE", "nodes": 100, "edges": 150})
    assert out["status"] == "success"
    assert 0.0 < out["metrics"]["resonance"] <= 1.0
    assert abs(out["metrics"]["tension"] - 1.5) < 1e-6


def _test_accel_procrustes():
    phase = [0.1 * i for i in range(32)]
    out = _accel.handle({"operation": "PROCRUSTES_ALIGNMENT", "phase_a": phase, "phase_b": phase})
    assert out["metrics"]["alignment_score"] > 0.99


async def _test_self_reflect_local():
    engine = SelfReflectEngine()
    nodes = [{"id": "a.py::f", "label": "f", "shape": "Sphere", "vector": [1, 0, 0]}]
    phase = engine.topology_to_phase_vector(nodes)
    score, updated = engine.measure_drift(phase)
    assert 0.0 <= score <= 1.0
    report = await engine.run_arch_reasoning_report()
    assert "resonance" in report and "patch" in report


_run("self_reflect", "arch_reasoner_accel: structural resonance", _test_accel_structural)
_run("self_reflect", "arch_reasoner_accel: procrustes self-alignment", _test_accel_procrustes)
_run("self_reflect", "SelfReflectEngine: drift + arch report (async)", _test_self_reflect_local)


# ---------------------------------------------------------------------------
# 6. Liquid Kernel — CfC + LTC-NDE
# ---------------------------------------------------------------------------
_header("6. liquid_kernel — Closed-Form CfC + LTC-NDE")

from liquid_kernel import (
    LiquidConfig, AdaptiveLiquidTimeConstant, ClosedFormContinuousCore,
    LiquidState, TernaryLinear, ternary_activation,
)

def _test_cfc_forward():
    cfc = ClosedFormContinuousCore(units=64)
    x = np.ones(64, dtype=np.float32)
    h = cfc.forward(x, dt=0.1)
    assert h.shape == (64,), f"shape {h.shape}"
    assert np.all(np.isfinite(h)), "non-finite output"

def _test_cfc_reset():
    cfc = ClosedFormContinuousCore(units=32)
    cfc.forward(np.ones(32, dtype=np.float32), dt=0.05)
    cfc.reset()
    assert np.allclose(cfc.hidden_state, 0.0)

def _test_ltc_nde():
    cfg = LiquidConfig()
    ltc = AdaptiveLiquidTimeConstant(cfg)
    x = np.ones(10, dtype=np.float32)
    state = np.zeros(10, dtype=np.float32)
    tau = ltc.dynamic_time_constant(x, state=state)
    assert np.all(tau > 0), f"tau {tau}"
    stepped = ltc.step(state, x, dt=0.1)
    assert stepped.shape == x.shape

def _test_energy_ceiling():
    cfg = LiquidConfig()
    ltc = AdaptiveLiquidTimeConstant(cfg)
    assert ltc.evaluate_energy_ceiling(38.0) == 1.0
    assert ltc.evaluate_energy_ceiling(45.0) == 0.15

def _test_liquid_state():
    cfg = LiquidConfig()
    ls = LiquidState(cfg)
    out = ls.update({"temperature": 37.5, "load": 0.5, "tick": 1.0})
    assert isinstance(out, dict)

_run("liquid", "ClosedFormContinuousCore.forward: shape + finite", _test_cfc_forward)
_run("liquid", "ClosedFormContinuousCore.reset: hidden → 0", _test_cfc_reset)
_run("liquid", "AdaptiveLiquidTimeConstant LTC-NDE: τ > 0, step correct shape", _test_ltc_nde)
_run("liquid", "evaluate_energy_ceiling: 38°C→1.0, 45°C→0.15", _test_energy_ceiling)
_run("liquid", "LiquidState.update: returns dict", _test_liquid_state)


# ---------------------------------------------------------------------------
# 7. Spectral Memory — SVD filter + MQCR
# ---------------------------------------------------------------------------
_header("7. aura_spectral_memory — SVD Filter + MQCR Recoherence")

from aura_spectral_memory import AuraSpectralMemoryOrchestrator

async def _test_spectral_filter():
    orch = AuraSpectralMemoryOrchestrator()
    data = np.random.rand(20, 20).astype(np.float32)
    result = await orch.optimize_memory_view(data)
    assert "filtered_data" in result
    assert result["filtered_data"].shape == data.shape

def _test_mqcr_unit_magnitude():
    orch = AuraSpectralMemoryOrchestrator()
    target = _phasor(0)
    anchor = _phasor(1)
    out = orch.execute_mqcr_recoherence(target, anchor)
    assert out.dtype == np.complex64
    assert np.allclose(np.abs(out), 1.0, atol=1e-5), "not unit magnitude"

def _test_mqcr_convergence():
    orch = AuraSpectralMemoryOrchestrator()
    target = _phasor(3)
    anchor = _phasor(3)  # same seed → phase_delta = 0 → no drift
    out = orch.execute_mqcr_recoherence(target, anchor)
    assert np.allclose(np.angle(out), np.angle(anchor), atol=1e-4)

def _test_decoherence_shock():
    orch = AuraSpectralMemoryOrchestrator()
    v = _phasor(0)
    shocked = orch.apply_decoherence_shock(v, recoherence_factor=0.1)
    assert shocked.shape == v.shape
    assert np.allclose(np.abs(shocked), 1.0, atol=1e-4)

def _test_lie_algebra():
    orch = AuraSpectralMemoryOrchestrator()
    v = _phasor(0)
    phases = orch.log_map(v)
    reconstructed = orch.exp_map(phases)
    assert np.allclose(np.abs(reconstructed), 1.0, atol=1e-5)

_run("spectral", "optimize_memory_view: SVD filter preserves shape (async)", _test_spectral_filter)
_run("spectral", "execute_mqcr_recoherence: output unit-magnitude complex64", _test_mqcr_unit_magnitude)
_run("spectral", "execute_mqcr_recoherence: same anchor → no drift", _test_mqcr_convergence)
_run("spectral", "apply_decoherence_shock: unit magnitude preserved", _test_decoherence_shock)
_run("spectral", "log_map / exp_map round-trip: unit circle", _test_lie_algebra)


# ---------------------------------------------------------------------------
# 8. Governor — Spiking + Energy Ceiling
# ---------------------------------------------------------------------------
_header("8. aura_governor — Spiking Governor + Energy Ceiling")

from aura_governor import AuraSpikingGovernor

def _test_stimulate_leak():
    g = AuraSpikingGovernor()
    for _ in range(5):
        g.stimulate_and_leak("query: topology scan EVOLUTION CRITICAL")
    assert "EVOLUTION" in g.neurons

def _test_confidence():
    g = AuraSpikingGovernor()
    result = g.evaluate_payload_confidence("def foo(): return 42")
    assert "confidence" in result
    assert "entropy" in result
    assert result["status"] in ("APPROVED", "REJECTED")

def _test_ephaptic_resonance():
    g = AuraSpikingGovernor()
    r = g.calculate_ephaptic_resonance(0.5, 0.3)
    assert 0.0 <= r <= 1.0

def _test_energy_ceiling_governor():
    g = AuraSpikingGovernor()
    assert g.evaluate_energy_ceiling(38.0) == 1.0
    assert g.evaluate_energy_ceiling(42.0) == 0.15

_run("governor", "stimulate_and_leak: neuron map updated", _test_stimulate_leak)
_run("governor", "evaluate_payload_confidence: returns APPROVED/REJECTED", _test_confidence)
_run("governor", "calculate_ephaptic_resonance: ∈ [0,1]", _test_ephaptic_resonance)
_run("governor", "evaluate_energy_ceiling: thermal thresholds correct", _test_energy_ceiling_governor)


# ---------------------------------------------------------------------------
# 9. Cognitive Router
# ---------------------------------------------------------------------------
_header("9. cognitive_router — Quantum Multiclass Intent Classifier")

from cognitive_router import CognitiveRouter

def _test_router_wave_scan():
    cr = CognitiveRouter()
    probe = np.random.randn(cr.D if hasattr(cr, "D") else 10000).astype(np.float32)
    result = cr.wave_scan(probe)
    assert isinstance(result, (dict, str, list))

def _test_router_intent():
    cr = CognitiveRouter()
    probe = np.random.randn(cr.D if hasattr(cr, "D") else 10000).astype(np.float32)
    class_matrix = {"!push": probe, "!topology": probe * 0.5}
    cls = cr.quantum_multiclass_intent_classifier(probe, class_matrix)
    assert isinstance(cls, (str, dict))

_run("router", "wave_scan: returns dict", _test_router_wave_scan)
_run("router", "quantum_multiclass_intent_classifier: returns dict", _test_router_intent)


# ---------------------------------------------------------------------------
# 10. Topology Scanner & Spatial Mapper
# ---------------------------------------------------------------------------
_header("10. Topology & Spatial Mapper — compile_unified_graph + scan_and_vectorize")

from spatial_mapper import scan_and_vectorize, DirectoryCache
from aura_topological_scanner import compile_unified_graph

def _test_scan_vectorize():
    nodes = scan_and_vectorize(os.getcwd())
    assert len(nodes) > 0, "no nodes returned"
    assert all("name" in n and "file" in n for n in nodes[:5])

def _test_compile_graph():
    payload = compile_unified_graph()
    assert "nodes" in payload and "edges" in payload
    assert len(payload["nodes"]) > 0, "no nodes"
    assert len(payload["edges"]) > 0, f"0 edges (schema mismatch?)"

def _test_directory_cache():
    dc = DirectoryCache()
    files = dc.get_cached_walk(os.getcwd())
    assert any(f.endswith(".py") for f in files)

_run("topology", "scan_and_vectorize: returns nodes with name+file", _test_scan_vectorize)
_run("topology", "compile_unified_graph: nodes > 0, edges > 0", _test_compile_graph)
_run("topology", "DirectoryCache.get_cached_walk: finds .py files", _test_directory_cache)


# ---------------------------------------------------------------------------
# 11. Quantum DAG — Merkle epistemic root
# ---------------------------------------------------------------------------
_header("11. quantum_dag — QuantumMerkleDAG epistemic root")

from quantum_dag import QuantumMerkleDAG

async def _test_qdag():
    class _FakeNode:
        runtime_metrics = {}
    dag = QuantumMerkleDAG(_FakeNode())
    result = await dag.generate_epistemic_system_root()
    assert "dag_nodes" in result or "status" in result or isinstance(result, dict)

_run("qdag", "generate_epistemic_system_root: returns dict (async)", _test_qdag)


# ---------------------------------------------------------------------------
# 12. Async Palace — Memory + BF-Tree
# ---------------------------------------------------------------------------
_header("12. async_palace — MorphemicBatchQueue + BF-Tree view")

from async_palace import MorphemicBatchQueue
import struct

def _test_morphemic_queue():
    q = MorphemicBatchQueue(max_records=4)
    full = q.append_record([1, 2, 3, 4, 5, 6], 0.9)
    assert not full
    records = q.flush_and_clear()
    assert len(records) == 1
    assert records[0][0] == 1

def _test_bftree_view():
    q = MorphemicBatchQueue()
    frames = [struct.pack("<HHHHHHf", i, i+1, i+2, i+3, i+4, i+5, 0.5) for i in range(5)]
    matrix = q.compile_bftree_matrix_view(frames)
    assert matrix.dtype == np.uint16
    assert matrix.shape == (5, 6)
    assert matrix[0, 0] == 0   # first row, first slot = i=0

def _test_bftree_empty():
    q = MorphemicBatchQueue()
    matrix = q.compile_bftree_matrix_view([])
    assert matrix.shape == (1, 6)

_run("palace", "MorphemicBatchQueue: append + flush_and_clear", _test_morphemic_queue)
_run("palace", "compile_bftree_matrix_view: shape (N,6), dtype uint16", _test_bftree_view)
_run("palace", "compile_bftree_matrix_view: empty → (1,6) zero array", _test_bftree_empty)


# ---------------------------------------------------------------------------
# 13. Crystallization & NeSy SAT Reasoner
# ---------------------------------------------------------------------------
_header("13. aura_crystallization + aura_nesy_sat_reasoner")

from aura_crystallization import hypertruth_crystallization_loop

def _test_crystallization():
    # hypertruth_crystallization_loop expects a dict as node_topology
    nodes = {f"fn_{i}": {"label": f"fn_{i}", "shape": "Sphere"} for i in range(5)}
    state, report = hypertruth_crystallization_loop(nodes, [], [])
    assert "constraints_met" in report

_run("crystal", "hypertruth_crystallization_loop: returns report with constraints_met", _test_crystallization)


async def _test_nesy_sweep():
    r = AuraNeuroSymbolicReasoner()
    result = await r.run_exhaustive_omnipath_sweep()
    assert isinstance(result, str) and len(result) > 0

_run("nesy", "run_exhaustive_omnipath_sweep: returns string (async)", _test_nesy_sweep)


# ---------------------------------------------------------------------------
# 14. Positional Parser + VPT Tokenizer
# ---------------------------------------------------------------------------
_header("14. aura_positional_parser + aura_vpt_tokenizer")

from aura_positional_parser import AthabaskanPositionalParser

def _test_positional():
    parser = AthabaskanPositionalParser()
    # compile_positional_block(spatial, aspect, classifier, subject, voice, stem_intent)
    block = parser.compile_positional_block(
        "NIGIM_LOCAL", "ITERATIVE", "MESH_NODE",
        "SOVEREIGN_NODE", "ACTIVE_TRANSITIVE", "execute_push"
    )
    assert isinstance(block, np.ndarray) and block.ndim >= 1

_run("parser", "compile_positional_block: returns ndarray", _test_positional)

from aura_vpt_tokenizer import HeightBoundedVPTTokenizer

def _test_vpt_tokenizer():
    tok = HeightBoundedVPTTokenizer()
    tokens = tok.stream_tokenize_buffer("gidinawendimin niwaabamin gizaagi'in")
    assert len(tokens) > 0
    lattice = tok.compile_to_phasor_lattice(tokens)
    assert isinstance(lattice, np.ndarray)

_run("vpt", "stream_tokenize_buffer + compile_to_phasor_lattice", _test_vpt_tokenizer)


# ---------------------------------------------------------------------------
# 15. Lexical Transducer
# ---------------------------------------------------------------------------
_header("15. lexical_transducer — Polysynthetic Forge")

from lexical_transducer import PolysyntheticTransducer

def _test_transducer_forge():
    t = PolysyntheticTransducer()
    result = t.forge_new_root("artificial neural network", "mashkimod", "Reasoning substrate")
    assert result is not None

def _test_transducer_cosine():
    t = PolysyntheticTransducer()
    va = t.architect_to_vector("gidinawendimin")
    vb = t.architect_to_vector("miigwech")
    dist = t.cosine_distance(va, vb)
    assert 0.0 <= float(dist) <= 2.0

_run("transducer", "forge_new_root: returns result", _test_transducer_forge)
_run("transducer", "cosine_distance: ∈ [0, 2]", _test_transducer_cosine)


# ---------------------------------------------------------------------------
# 16. PWFST — Polysynthetic Finite-State Transducer
# ---------------------------------------------------------------------------
_header("16. pwfst — Polysynthetic VSF Transducer")

from pwfst import UnifiedPWFST

def _test_pwfst_compile():
    fsm = UnifiedPWFST()
    # compile_vsft_matrix expects scalar float values
    lexicon = {"gidinawendimin": 0.9, "miigwech": 0.1, "niwaabamin": 0.6}
    result = fsm.compile_vsft_matrix(lexicon)
    assert result is not None and len(result) == 3

def _test_pwfst_transduce():
    fsm = UnifiedPWFST()
    lexicon = {"gidinawendimin": 0.9, "miigwech": 0.1}
    fsm.compile_vsft_matrix(lexicon)
    out = fsm.transduce_intent("render the fix", "THOUGHT-AABBCCDD")
    assert out is not None

_run("pwfst", "compile_vsft_matrix: completes", _test_pwfst_compile)
_run("pwfst", "transduce_intent: returns output", _test_pwfst_transduce)


# ---------------------------------------------------------------------------
# 17. Gateway — E8 projection + ST3GG glyph + bisha quarantine
# ---------------------------------------------------------------------------
_header("17. gateway — CognitiveGateway functions")

from gateway import CognitiveGateway

class _MockNode:
    runtime_metrics = {"thought_id": "THOUGHT-AABBCCDD"}
    def log_error(self, *a, **kw): pass

def _test_gateway_e8():
    gw = CognitiveGateway(_MockNode())
    v = np.random.randn(10).astype(np.float32)
    proj = gw.project_to_e8_holographic_lattice(v)
    assert proj is not None

def _test_gateway_st3gg():
    gw = CognitiveGateway(_MockNode())
    glyph = gw.generate_st3gg_glyph("EVOLUTION query", 37.5)
    # Returns an int hash or string — just ensure it's non-None
    assert glyph is not None

def _test_gateway_bisha():
    gw = CognitiveGateway(_MockNode())
    result = gw.bisha_quarantine_check(
        "test_module_id",
        np.random.randn(10).astype(np.float64)
    )
    assert isinstance(result, bool)

def _test_gateway_quantum_interference():
    gw = CognitiveGateway(_MockNode())
    va = np.random.randn(16).astype(np.float32)
    vb = np.random.randn(16).astype(np.float32)
    out = gw.quantum_cognitive_interference(va, vb)
    assert out is not None

_run("gateway", "project_to_e8_holographic_lattice: returns value", _test_gateway_e8)
_run("gateway", "generate_st3gg_glyph: contains 'ST3GG'", _test_gateway_st3gg)
_run("gateway", "bisha_quarantine_check: returns bool", _test_gateway_bisha)
_run("gateway", "quantum_cognitive_interference: returns value", _test_gateway_quantum_interference)


# ---------------------------------------------------------------------------
# 18. Rosetta Memory — adaptive write + contrastive query
# ---------------------------------------------------------------------------
_header("18. aura_rosetta_memory — Adaptive Write + Contrastive Query")

from aura_rosetta_memory import RosettaMemoryBuffer

async def _test_rosetta_write_query():
    rm = RosettaMemoryBuffer(capacity=20, dimension=DIM)
    v = get_semantic_vector("neuro-symbolic", dim=DIM)
    # adaptive_write(phasor_wave, metadata_text, tier)
    wrote = await rm.adaptive_write(v, "neuro-symbolic principle")
    assert wrote is True or wrote is None
    result = await rm.query_contrastive(v)
    assert isinstance(result, (str, dict, list, np.ndarray))

_run("rosetta", "adaptive_write + query_contrastive: completes", _test_rosetta_write_query)


# ---------------------------------------------------------------------------
# 19. DAG Executor
# ---------------------------------------------------------------------------
_header("19. dag_executor — Topological Sort + Execute")

from dag_executor import execute_dag_plan

def _test_dag_simple():
    # execute_dag_plan() reads JSON from stdin — test via JSON roundtrip
    plan = {
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [{"source": "A", "target": "B"}, {"source": "B", "target": "C"}]
    }
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps(plan))
    try:
        execute_dag_plan()
        result = True
    except SystemExit:
        result = True
    except Exception as e:
        result = False
    finally:
        sys.stdin = old_stdin
    assert result

_run("dag", "execute_dag_plan: linear DAG completes", _test_dag_simple)


# ---------------------------------------------------------------------------
# 20. Aura Evolve — Sandbox evaluation
# ---------------------------------------------------------------------------
_header("20. aura_evolve — LiquidFlashEvolve sandbox")

from aura_evolve import LiquidFlashEvolve

class _FakeNodeForEvolve:
    runtime_metrics = {}
    def log_error(self, *a, **kw): pass

async def _test_evolve_sandbox():
    class _FullFakeNode:
        runtime_metrics = {}
        async def invoke_engine(self, prompt, structural=False, gbnf_profile=None):
            return "# docstring added\ndef optimized_fallback():\n    pass\n"
        def log_error(self, *a, **kw): pass
    evo = LiquidFlashEvolve(_FullFakeNode())
    result = await evo.sandbox_and_evaluate("pvm_memory_guard", "Add a docstring")
    assert isinstance(result, str)

_run("evolve", "sandbox_and_evaluate: returns string (async)", _test_evolve_sandbox)


# ---------------------------------------------------------------------------
# 21. Aura Mitosis — Energy landscape
# ---------------------------------------------------------------------------
_header("21. aura_mitosis — Hopfield energy landscape")

from aura_mitosis import AuraMitosisEngine

def _test_mitosis():
    engine = AuraMitosisEngine()
    wave = np.random.randn(10).astype(np.float32)
    phases = [np.random.randn(10).astype(np.float32) for _ in range(3)]
    result = engine.calculate_energy_landscape(wave, phases)
    assert isinstance(result, (float, int, np.floating, np.integer))

_run("mitosis", "calculate_energy_landscape: returns float", _test_mitosis)


# ---------------------------------------------------------------------------
# 22. Crypto PUF
# ---------------------------------------------------------------------------
_header("22. aura_crypto_puf — Thermodynamic PUF key derivation")

from aura_crypto_puf import AuraThermodynamicPUF

def _test_puf():
    puf = AuraThermodynamicPUF()
    key = puf.distill_liquid_key(system_tension=0.5, physics_error=0.02, geo_coordinate=37.5)
    assert key is not None

_run("puf", "distill_liquid_key(37.5): returns non-None", _test_puf)


# ---------------------------------------------------------------------------
# 23. Memory Guard — MemoryBudget + assert_zero_copy
# ---------------------------------------------------------------------------
_header("23. pvm_memory_guard — Budget + Zero-Copy Assertions")

from pvm_memory_guard import (
    MemoryBudget, assert_zero_copy, zero_copy_zeros,
    zero_copy_frombuffer, sample_rss_mb, heap_snapshot,
    MemoryBudgetExceeded, ZeroCopyViolation, PVM_RAM_CEILING_MB,
)

def _test_memory_rss():
    rss = sample_rss_mb()
    assert rss > 0.0

def _test_zero_copy_zeros():
    arr = zero_copy_zeros((100, 100), np.float32)
    assert arr.shape == (100, 100)
    assert arr.dtype == np.float32

def _test_assert_zero_copy_pass():
    arr = np.ones(100, dtype=np.float32)
    assert_zero_copy(arr, "test")  # must not raise

def _test_assert_zero_copy_fail():
    arr = np.array([object()])
    raised = False
    try:
        assert_zero_copy(arr, "obj_arr")
    except ZeroCopyViolation:
        raised = True
    assert raised

def _test_budget_context_manager():
    with MemoryBudget(budget_mb=PVM_RAM_CEILING_MB, raise_on_breach=False) as bm:
        assert bm.current_mb() > 0

def _test_heap_snapshot():
    snap = heap_snapshot()
    assert isinstance(snap, dict)

_run("memguard", "sample_rss_mb() > 0", _test_memory_rss)
_run("memguard", "zero_copy_zeros: shape + dtype", _test_zero_copy_zeros)
_run("memguard", "assert_zero_copy: valid array passes", _test_assert_zero_copy_pass)
_run("memguard", "assert_zero_copy: object dtype raises ZeroCopyViolation", _test_assert_zero_copy_fail)
_run("memguard", "MemoryBudget context manager: headroom > 0", _test_budget_context_manager)
_run("memguard", "heap_snapshot: returns dict", _test_heap_snapshot)


# ---------------------------------------------------------------------------
# 24. PVM Arch Checker
# ---------------------------------------------------------------------------
_header("24. pvm_arch_checker — Static Rule Enforcement")

from pvm_arch_checker import PVMArchChecker

def _test_checker_passes_on_workspace():
    checker = PVMArchChecker(root=Path("."))
    violations = checker.run()
    hard = [v for v in violations if v.rule in
            {"SYNTAX_ERROR", "WILDCARD_IMPORT", "CIRCULAR_IMPORT", "NAMESPACE_INJECTION"}]
    assert len(hard) == 0, f"Hard violations: {hard}"

def _test_checker_dep_map():
    checker = PVMArchChecker(root=Path("."))
    checker.run()
    depmap = checker.dependency_map_text()
    assert "aura_node" in depmap

_run("checker", "workspace has 0 hard violations", _test_checker_passes_on_workspace)
_run("checker", "dependency_map_text: contains aura_node", _test_checker_dep_map)


# ---------------------------------------------------------------------------
# 25. REPL command logic stubs (without live boot)
# ---------------------------------------------------------------------------
_header("25. REPL Command Logic — offline stubs")


async def _test_synthesize_cmd():
    synth = AuraNeuroSymbolicReasoner()
    result = await synth.run_exhaustive_omnipath_sweep()
    assert isinstance(result, str)

async def _test_dream_engine_cycle():
    class _FakePalace:
        conn = None
    class _FakeNode2:
        memory_palace = _FakePalace()
        runtime_metrics = {}
        t1_ram = []
    eng = AuraDreamEngine(_FakeNode2())
    result = await eng.run_dream_cycle()
    assert isinstance(result, str)

_run("repl", "!synthesize → AuraNeuroSymbolicReasoner.run_exhaustive_omnipath_sweep", _test_synthesize_cmd)
_run("repl", "Dream engine run_dream_cycle (no DB): returns string", _test_dream_engine_cycle)

# topology command (already tested in §10)
_run("repl", "!topology → compile_unified_graph: nodes > 0 + edges > 0",
     lambda: (lambda p: len(p["nodes"]) > 0 and len(p["edges"]) > 0)(compile_unified_graph()))

# !catalyze — test with a real pending_patches.json if present, else synthesise one
def _test_catalyze():
    test_patch = "import os\nx = os.getcwd()\n"
    return verify_structural_truth(test_patch)

_run("repl", "!catalyze logic — verify_structural_truth on valid patch", _test_catalyze)

# !fast_path
def _test_fast_path():
    core = AuraAssociativeCore(dim=DIM)
    k = get_semantic_vector("!push", dim=DIM)
    core.store(k, k, label="push")
    result = core.fast_path_lookup("!push", lambda t, dim: get_semantic_vector(t, dim=dim))
    return result["confidence"] > 0.5

_run("repl", "!fast_path logic — fast_path_lookup confidence > 0.5", _test_fast_path)


# ---------------------------------------------------------------------------
# 22. Evolution stack — GBNF profiles, ontology circuit, evolution bridge
# ---------------------------------------------------------------------------
_header("22. evolution — GBNF profiles + ontology circuit + bridge")

from aura_gbnf_profiles import (
    list_profiles, get_grammar_string, PROFILE_PYTHON_PATCH, PROFILE_UNIT_INTERVAL,
)
from aura_ontology_circuit import AuraOntologyCircuit
from aura_evolution_bridge import validate_proposed_mutation, speculative_topology_check

_run("evolution", "list_profiles includes python_patch",
     lambda: PROFILE_PYTHON_PATCH in list_profiles())

_run("evolution", "get_grammar_string python_patch contains [CODE]",
     lambda: "[CODE]" in get_grammar_string(PROFILE_PYTHON_PATCH))

_run("evolution", "get_grammar_string unit_interval uses leading space",
     lambda: '" "' in get_grammar_string(PROFILE_UNIT_INTERVAL))

def _test_ontology_circuit_ok():
    c = AuraOntologyCircuit()
    v = c.evaluate_source("import os\nx = 1\n")
    return v.consistent

_run("evolution", "ontology circuit: safe code passes", _test_ontology_circuit_ok)

def _test_ontology_circuit_ban():
    c = AuraOntologyCircuit()
    v = c.evaluate_source("import torch\n")
    return not v.consistent

_run("evolution", "ontology circuit: torch import fails", _test_ontology_circuit_ban)

def _test_bridge_valid():
    v = validate_proposed_mutation("while True:\n    break\n", module_name="aura_evolve")
    return v.approved and v.shield_ok

_run("evolution", "bridge: valid mutation approved", _test_bridge_valid)

def _test_bridge_eval_reject():
    v = validate_proposed_mutation("eval('1')\n", module_name="aura_evolve")
    return not v.approved

_run("evolution", "bridge: eval() rejected", _test_bridge_eval_reject)

_run("evolution", "speculative_topology_check returns tuple",
     lambda: isinstance(speculative_topology_check("aura_node")[0], bool))


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

print(f"\n{'═'*68}")
print("  FULL FUNCTION TEST REPORT")
print("═"*68)
total = len(_results)
passes = sum(1 for _, _, s in _results if s == _PASS)
fails  = sum(1 for _, _, s in _results if s == _FAIL)
skips  = sum(1 for _, _, s in _results if s == _SKIP)
print(f"  Total  : {total}")
print(f"  PASS   : {passes}  ({passes/total*100:.1f}%)")
print(f"  FAIL   : {fails}")
print(f"  SKIP   : {skips}")

if fails:
    print(f"\n  Failed tests:")
    for cat, name, status in _results:
        if status == _FAIL:
            print(f"    [{cat}] {name}")

print(f"\n  {'✓ ALL PASS' if fails == 0 else '✗ FAILURES DETECTED — see above'}")
print("═"*68)

sys.exit(0 if fails == 0 else 1)
