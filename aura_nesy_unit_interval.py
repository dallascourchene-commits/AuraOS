"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa895-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: typing, dataclasses, enum, os, numpy, re, __future__, aura_gbnf_profiles, time, json
FUNCTIONS: parse_unit_interval_output, classify_edge_zone, fuse_spvm_llm_scores, is_fracture, build_edge_audit_prompt, select_edges_for_llm_audit, _load_llm_cache, _save_llm_cache, llm_audit_edge, batch_llm_audit_edges, build_edge_audit_records, records_to_fractures, edge_key
SYNOPSIS: This Python module, leveraging `typing`, `dataclasses`, `enum`, `os`, `numpy`, `re`, `__future__`, `aura_gbnf_profiles`, `time`, and `json`, implements a strict audit framework for edge-zone classification and LLM-based fracture detection, featuring core functions like `parse_unit_interval_output`, `classify_edge_zone`, `fuse_spvm_llm_scores`, `is_fracture`, `build_edge_audit_prompt`, `select_edges_for_llm_audit`, `_load_llm_cache`, `_save_llm_cache`, `llm_audit_edge`, `batch_llm_audit_edges`, `build_edge_audit_records`, `records_to_fractures`, and `edge_key` to enforce deterministic validation and caching workflows.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

"""
NeSy unit-interval edge auditing (arXiv:2502.14969 + hybrid neuro-symbolic fusion).

Research basis
--------------
- Lost in Space (2502.14969): real scores in [0,1] with leading-space tokens for small LMs.
- Ontology refine loop (2504.07640): symbolic check → explain → re-prompt on borderline cases.
- DL→probabilistic circuits (2601.14894): SPVM implication as tractable numeric circuit; LLM
  calibrates uncertain edges only (asymmetric coupling per 2604.00555).
- VeriCoT (2511.04662): validate reasoning steps before accepting conclusions.
- JSONSchemaBench (2501.10868): constrained decoding for reliable structured scalars.

Design
------
1. SPVM batch implication scores every explicit edge O(E).
2. Borderline band [low, high) triggers optional LLM unit_interval audit (cap N edges).
3. fuse_spvm_llm() combines scores; fracture decision uses fused value.
"""

import json
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Awaitable

import numpy as np

from aura_gbnf_profiles import PROFILE_UNIT_INTERVAL

# Tunables (Termux-friendly defaults)
FRACTURE_FLOOR = float(os.environ.get("AURA_NESY_FRACTURE_FLOOR", "0.55"))
BORDERLINE_LOW = float(os.environ.get("AURA_NESY_BORDERLINE_LOW", "0.45"))
BORDERLINE_HIGH = float(os.environ.get("AURA_NESY_BORDERLINE_HIGH", "0.68"))
_FRACTURE_FLOOR = FRACTURE_FLOOR
_BORDERLINE_LOW = BORDERLINE_LOW
_BORDERLINE_HIGH = BORDERLINE_HIGH
_LLM_AUDIT_MAX = int(os.environ.get("AURA_NESY_LLM_AUDIT_MAX", "8"))
_SPVM_WEIGHT = float(os.environ.get("AURA_NESY_SPVM_FUSION_WEIGHT", "0.62"))
_LLM_CACHE_PATH = os.environ.get(
    "AURA_NESY_LLM_CACHE", "Aura_Memory/nesy_edge_llm_cache.json"
)

_UNIT_INTERVAL_RE = re.compile(
    r"(?:^|\s)(0\.\d{1,2}|1\.0|1\.00)\s*$"
)


class EdgeZone(str, Enum):
    CLEAR_PASS = "clear_pass"
    CLEAR_FRACTURE = "clear_fracture"
    BORDERLINE = "borderline"


@dataclass(frozen=True)
class EdgeAuditRecord:
    src: str
    tgt: str
    spvm_implication: float
    zone: EdgeZone
    llm_confidence: float | None = None
    fused_score: float | None = None
    audit_source: str = "spvm_only"

    def edge_key(self) -> str:
        return f"{self.src}→{self.tgt}"


def parse_unit_interval_output(raw: str) -> float | None:
    """
    Parse GBNF / Lost-in-Space scalar output into [0, 1].
    Accepts leading-space forms like ' 0.55' or ' 1.0'.
    """
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    match = _UNIT_INTERVAL_RE.search(text)
    if not match:
        # Fallback: first float-like token
        floats = re.findall(r"\b(0\.\d+|1\.0+)\b", text)
        if not floats:
            return None
        text = floats[0]
    else:
        text = match.group(1)
    try:
        value = float(text)
    except ValueError:
        return None
    return float(np.clip(value, 0.0, 1.0))


def classify_edge_zone(spvm_implication: float) -> EdgeZone:
    if spvm_implication >= BORDERLINE_HIGH:
        return EdgeZone.CLEAR_PASS
    if spvm_implication < BORDERLINE_LOW:
        return EdgeZone.CLEAR_FRACTURE
    return EdgeZone.BORDERLINE


def fuse_spvm_llm_scores(
    spvm: float,
    llm: float | None,
    *,
    spvm_weight: float = _SPVM_WEIGHT,
) -> float:
    """Weighted neuro-symbolic fusion; SPVM-primary on edge hardware."""
    if llm is None:
        return spvm
    w = float(np.clip(spvm_weight, 0.0, 1.0))
    return float(w * spvm + (1.0 - w) * llm)


def is_fracture(fused_score: float, floor: float = _FRACTURE_FLOOR) -> bool:
    return fused_score < floor


def build_edge_audit_prompt(src: str, tgt: str, spvm_implication: float) -> str:
    """Minimal prompt for unit_interval GBNF — score logical entailment only."""
    src_short = src.split("::")[-1]
    tgt_short = tgt.split("::")[-1]
    return (
        f"Rate how logically sound this Python call edge is from 0.0 (broken) to 1.0 (sound).\n"
        f"Caller: {src_short}\n"
        f"Callee: {tgt_short}\n"
        f"SPVM prior: {spvm_implication:.2f}\n"
        f"Reply with only one number in [0,1] using the required format.\n"
    )


def select_edges_for_llm_audit(
    edges: list[tuple[str, str, float]],
    *,
    max_audits: int = _LLM_AUDIT_MAX,
) -> list[tuple[str, str, float]]:
    """
    Pick the most uncertain borderline edges (closest to fracture floor).
    edges: (src, tgt, spvm_implication)
    """
    borderline = [
        (s, t, impl)
        for s, t, impl in edges
        if classify_edge_zone(impl) == EdgeZone.BORDERLINE
    ]
    if not borderline:
        return []
    # Uncertainty = distance from decision boundary
    borderline.sort(key=lambda x: abs(x[2] - _FRACTURE_FLOOR))
    return borderline[:max_audits]


def _load_llm_cache() -> dict[str, Any]:
    if not os.path.exists(_LLM_CACHE_PATH):
        return {}
    try:
        with open(_LLM_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_llm_cache(cache: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_LLM_CACHE_PATH) or ".", exist_ok=True)
    cache["updated_at"] = int(time.time())
    with open(_LLM_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


async def llm_audit_edge(
    invoke_fn: Callable[..., Awaitable[str]],
    src: str,
    tgt: str,
    spvm_implication: float,
    *,
    use_cache: bool = True,
) -> tuple[float | None, str]:
    """
    Request a unit_interval score via invoke_engine (GBNF) or cloud fallback.
    Returns (score, source_tag).
    """
    key = f"{src}→{tgt}"
    cache = _load_llm_cache() if use_cache else {}
    cached = cache.get("edges", {}).get(key)
    if cached and "llm_confidence" in cached:
        return float(cached["llm_confidence"]), "cache"

    prompt = build_edge_audit_prompt(src, tgt, spvm_implication)
    raw = ""
    try:
        raw = await invoke_fn(
            prompt,
            structural=True,
            gbnf_profile=PROFILE_UNIT_INTERVAL,
        )
        source = "local_gbnf"
    except TypeError:
        try:
            raw = await invoke_fn(prompt, structural=True)
            source = "local_structural"
        except TypeError:
            raw = await invoke_fn(prompt)
            source = "cloud_plain"
    except Exception:
        return None, "error"

    score = parse_unit_interval_output(raw)
    if score is not None and use_cache:
        edges = cache.setdefault("edges", {})
        edges[key] = {
            "llm_confidence": score,
            "spvm_implication": spvm_implication,
            "ts": int(time.time()),
        }
        _save_llm_cache(cache)
    return score, source if score is not None else "parse_fail"


async def batch_llm_audit_edges(
    invoke_fn: Callable[..., Awaitable[str]],
    candidates: list[tuple[str, str, float]],
    *,
    max_audits: int = _LLM_AUDIT_MAX,
) -> dict[str, tuple[float | None, str]]:
    """Audit up to max_audits borderline edges; returns edge_key → (score, source)."""
    selected = select_edges_for_llm_audit(candidates, max_audits=max_audits)
    results: dict[str, tuple[float | None, str]] = {}
    for src, tgt, impl in selected:
        key = f"{src}→{tgt}"
        score, source = await llm_audit_edge(invoke_fn, src, tgt, impl)
        results[key] = (score, source)
    return results


def build_edge_audit_records(
    production_edges: list[tuple[str, str]],
    implications: np.ndarray,
    llm_scores: dict[str, tuple[float | None, str]] | None = None,
) -> list[EdgeAuditRecord]:
    """Build per-edge audit records with optional LLM fusion."""
    llm_scores = llm_scores or {}
    records: list[EdgeAuditRecord] = []
    for (src, tgt), impl in zip(production_edges, implications):
        impl_f = float(impl)
        zone = classify_edge_zone(impl_f)
        key = f"{src}→{tgt}"
        llm_val, source = llm_scores.get(key, (None, "spvm_only"))
        fused = fuse_spvm_llm_scores(impl_f, llm_val)
        records.append(
            EdgeAuditRecord(
                src=src,
                tgt=tgt,
                spvm_implication=impl_f,
                zone=zone,
                llm_confidence=llm_val,
                fused_score=fused,
                audit_source=source if llm_val is not None else "spvm_only",
            )
        )
    return records


def records_to_fractures(
    records: list[EdgeAuditRecord],
    *,
    fracture_floor: float = _FRACTURE_FLOOR,
) -> list[dict[str, Any]]:
    """Convert audit records to fracture payloads for nesy state JSON."""
    fractures: list[dict[str, Any]] = []
    for rec in records:
        fused = rec.fused_score if rec.fused_score is not None else rec.spvm_implication
        if not is_fracture(fused, fracture_floor):
            continue
        fractures.append({
            "origin_node": rec.src,
            "destination_node": rec.tgt,
            "fracture_kind": "logical_subsumption_breach",
            "coherence_drop": max(0.0, 1.0 - fused),
            "spvm_implication": rec.spvm_implication,
            "llm_confidence": rec.llm_confidence,
            "fused_implication": fused,
            "edge_zone": rec.zone.value,
            "audit_source": rec.audit_source,
            "edge_type": "explicit_function_call",
            "rationale": (
                f"Fused implication {fused:.2%} < {fracture_floor:.0%} "
                f"(SPVM={rec.spvm_implication:.2%}"
                + (
                    f", LLM={rec.llm_confidence:.2%})"
                    if rec.llm_confidence is not None
                    else ")"
                )
            ),
        })
    return fractures
