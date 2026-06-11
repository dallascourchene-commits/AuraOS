"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c2-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Cost Accountability)
DEPENDENCIES: __future__, json, os, time, pathlib, typing
FUNCTIONS: TokenEconomics, compute_delta, log_call, savings_summary
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Token Financial Economics & Savings Profiler
=============================================

Tracks exact per-call financial deltas between raw linear context transmission
and Aura's polysynthetically compressed packets.

Commercial rates (USD per million tokens):
    claude-sonnet-4-6   : $3.00 input / $15.00 output
    claude-opus-4-8     : $5.00 input / $25.00 output
    (all other providers use catalog rates from aura_llm_egress.PROVIDERS)

All logs are appended to Aura_Memory/token_economics.jsonl (gitignored).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
import sqlite3
from logging_kit import log_error, log_report

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Aura_Memory")
DB_PATH = os.path.join(MEMORY_DIR, "token_economics.db")

# ---------------------------------------------------------------------------
# Pricing tables  (per-million tokens — input / output)
# ---------------------------------------------------------------------------
PRICING_PER_M: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-sonnet-4-6":  (3.00,  15.00),
    "claude-opus-4-8":    (5.00,  25.00),
    "claude-3-5-haiku-latest": (0.80, 4.00),
    # Mistral
    "mistral-small-latest": (0.20,  0.60),
    "codestral-latest":     (0.30,  0.90),
    # Meta via SambaNova / Groq
    "Meta-Llama-3.3-70B-Instruct": (0.60, 1.20),
    "llama-3.3-70b-versatile":     (0.59, 0.79),
    "llama-3.3-70b-specdec":       (0.59, 0.99),
    # Gemini
    "gemini-1.5-flash": (0.07, 0.30),
    "gemini-1.5-pro":   (3.50, 10.50),
    # OpenAI
    "gpt-4o-mini": (0.15, 0.60),
}

_ECONOMICS_LOG = Path("Aura_Memory/token_economics.jsonl")

# In-memory running totals (reset on each process start)
_TOTALS: dict[str, float] = {
    "raw_cost_usd":      0.0,
    "aura_cost_usd":     0.0,
    "saved_usd":         0.0,
    "raw_in_tokens":     0.0,
    "raw_out_tokens":    0.0,
    "aura_in_tokens":    0.0,
    "aura_out_tokens":   0.0,
    "calls_logged":      0.0,
}


def _price_per_m(model: str) -> tuple[float, float]:
    """Return (price_per_m_in, price_per_m_out) for the given model name."""
    # Try exact match first
    if model in PRICING_PER_M:
        return PRICING_PER_M[model]
    # Substring fuzzy match
    for key, rate in PRICING_PER_M.items():
        if key in model or model in key:
            return rate
    # Default: Sonnet-class pricing
    return (3.00, 15.00)


def cost_usd(model: str, in_tokens: int, out_tokens: int) -> float:
    """Compute USD cost for one call."""
    p_in, p_out = _price_per_m(model)
    return round(in_tokens / 1_000_000 * p_in + out_tokens / 1_000_000 * p_out, 8)


class TokenEconomics:
    """
    Per-call financial accounting for Aura's cloud transmissions.

    Usage:
        eco = TokenEconomics()
        delta = eco.compute_delta(
            model="claude-sonnet-4-6",
            raw_in=2695, raw_out=1474,
            aura_in=539, aura_out=59,
        )
        eco.log_call(delta, task="mesh_offload")
        print(eco.savings_summary())
    """

    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    operation_name TEXT,
                    token_delta REAL,
                    cost_delta REAL
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            log_error("DB_INIT_FAIL", f"Failed to initialize token economics table: {str(e)}")

    # ------------------------------------------------------------------
    # Delta computation
    # ------------------------------------------------------------------

    def compute_delta(
        self,
        *,
        model: str,
        raw_in: int,
        raw_out: int,
        aura_in: int,
        aura_out: int,
    ) -> dict[str, Any]:
        """
        Compute the exact financial delta between raw and Aura-compressed calls.

        Parameters
        ----------
        model   : Model identifier (used for pricing lookup).
        raw_in  : Input tokens for the raw (uncompressed) prompt.
        raw_out : Output tokens expected from raw call (use ledger estimate if unknown).
        aura_in : Input tokens for the Aura compressed packet.
        aura_out: Output tokens from the compact Aura output.

        Returns a dict with costs, savings, and reduction percentages.
        """
        raw_cost = cost_usd(model, raw_in, raw_out)
        aura_cost = cost_usd(model, aura_in, aura_out)
        saved = max(0.0, raw_cost - aura_cost)

        in_reduction = round((raw_in - aura_in) / max(raw_in, 1) * 100, 2)
        out_reduction = round((raw_out - aura_out) / max(raw_out, 1) * 100, 2)
        cost_reduction = round(saved / max(raw_cost, 1e-9) * 100, 2)

        return {
            "model": model,
            "raw_in_tokens": raw_in,
            "raw_out_tokens": raw_out,
            "aura_in_tokens": aura_in,
            "aura_out_tokens": aura_out,
            "raw_cost_usd": raw_cost,
            "aura_cost_usd": aura_cost,
            "saved_usd": saved,
            "input_reduction_pct": in_reduction,
            "output_reduction_pct": out_reduction,
            "cost_reduction_pct": cost_reduction,
        }

    # ------------------------------------------------------------------
    # Persistent log
    # ------------------------------------------------------------------

    def log_call(self, token_delta: float, cost_delta: float, operation_name: str):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO token_operations (operation_name, token_delta, cost_delta)
                VALUES (?, ?, ?)
            ''', (operation_name, token_delta, cost_delta))
            
            conn.commit()
            conn.close()
            
            log_report("TOKEN_ECONOMICS", f"Logged running totals entry for {operation_name}")
        except Exception as e:
            log_error("TOKEN_LOG_FAIL", f"Failed to record execution transaction delta: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def savings_summary(self) -> dict:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('SELECT SUM(token_delta), SUM(cost_delta) FROM token_operations')
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] is not None and result[1] is not None:
                return {
                    'total_token_delta': float(result[0]),
                    'total_cost_delta': float(result[1])
                }
            
            return {'total_token_delta': 0.0, 'total_cost_delta': 0.0}
        except Exception as e:
            log_error("TOKEN_QUERY_FAIL", f"Failed to aggregate cumulative historical summary: {str(e)}")
            raise

    def historical_summary(self) -> dict[str, Any]:
        """Aggregate summary over all persisted economics log entries."""
        if not self.log_path.exists():
            return {"calls": 0, "raw_cost_usd": 0.0, "aura_cost_usd": 0.0, "saved_usd": 0.0}
        totals: dict[str, float] = {
            "calls": 0, "raw_cost_usd": 0.0, "aura_cost_usd": 0.0, "saved_usd": 0.0,
        }
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    totals["calls"] += 1
                    totals["raw_cost_usd"]  += rec.get("raw_cost_usd", 0.0)
                    totals["aura_cost_usd"] += rec.get("aura_cost_usd", 0.0)
                    totals["saved_usd"]     += rec.get("saved_usd", 0.0)
                except json.JSONDecodeError:
                    continue
        totals["cost_reduction_pct"] = round(
            totals["saved_usd"] / max(totals["raw_cost_usd"], 1e-9) * 100, 1
        )
        return totals
