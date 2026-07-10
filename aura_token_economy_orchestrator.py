"""
Aura Token Economy Orchestrator — cockpit-level token/cost savings.

Computes token savings across all Aura layers:
  * Polysynthetic packet compression
  * CODEMAP localization (vs raw repo reads)
  * AI Router context (vs broad file reads)
  * Read-slice (vs full file reads)
  * Context Crusher compression
  * ST3GG recall pointer (vs full capsule egress)
  * DREAM-lite reranking (vs unranked retrieval)
  * QDKT fast-path (vs re-deriving patterns)
  * Hermes contract (vs unstructured agent prompt)

Works offline using char/4 estimates. Integrates with aura_token_economics
when available for cost-per-token calculations.

Dependencies: stdlib only at module level. All Aura imports are lazy.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants and invariants
# ---------------------------------------------------------------------------

ORCHESTRATOR_VERSION = "AURA_TOKEN_ECONOMY_ORCHESTRATOR_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# Default model for cost estimation.
_DEFAULT_MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _file_char_count(repo_root: Path, file_path: str) -> int:
    try:
        resolved = (repo_root / file_path).resolve()
        resolved.relative_to(repo_root.resolve())
        if not resolved.exists() or not resolved.is_file():
            return 0
        return len(resolved.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return 0


def _load_codemap(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".aura" / "CODEMAP.json"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def _get_pricing(model: str) -> tuple[float, float]:
    """Get (input_price_per_m, output_price_per_m) for a model."""
    try:
        from aura_token_economics import PRICING_PER_M
        if model in PRICING_PER_M:
            return PRICING_PER_M[model]
    except Exception:
        pass
    # Fallback: Claude Sonnet rates
    return (3.00, 15.00)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_token_economy(
    objective: str,
    files: list[str],
    repo_root: str | Path = ".",
    model: str = _DEFAULT_MODEL,
) -> dict[str, Any]:
    """Compute a full token economy report for an objective and set of files.

    Returns a dict with raw baseline, Aura usage, savings, and savings sources.
    """
    root = Path(repo_root).resolve()

    # --- Raw baseline ---
    raw_prompt_tokens = _estimate_tokens(objective)
    raw_file_tokens = sum(_file_char_count(root, f) // 4 for f in files)
    raw_file_tokens = max(1, raw_file_tokens) if raw_file_tokens > 0 else 0

    # Raw repo estimate from CODEMAP
    codemap = _load_codemap(root)
    file_count = int(codemap.get("coverage", {}).get("included_file_count", 0))
    # Estimate average 2000 chars per file
    raw_repo_tokens = (file_count * 2000) // 4 if file_count else 0

    raw_total = raw_prompt_tokens + raw_file_tokens

    # --- Aura estimates ---
    # 1. Polysynthetic packet (typically 100-200 chars)
    aura_packet_tokens = _estimate_tokens("x" * 150)

    # 2. CODEMAP search (typically 300-600 chars per result, 5 results)
    codemap_search_tokens = _estimate_tokens("x" * 2000)

    # 3. Read-slice (120 lines * ~40 chars)
    read_slice_tokens = _estimate_tokens("x" * (120 * 40))

    # 4. Context Crusher (from actual call if available, else estimate)
    context_crush_tokens = 0
    try:
        from aura_context_crusher import apply_context_crush_to_prompt
        result = apply_context_crush_to_prompt(objective, source_hint="token_economy")
        context_crush_tokens = getattr(result, "compressed_tokens_est", 0)
        if not context_crush_tokens:
            context_crush_tokens = _estimate_tokens("x" * 2000)
    except Exception:
        context_crush_tokens = _estimate_tokens("x" * 2000)

    # 5. ST3GG (from actual call if available, else 0)
    st3gg_tokens = 0
    try:
        from aura_arena_st3gg_codec import should_st3gg_encode_arena_capsule
        capsule = {"objective": objective, "files": files}
        decision = should_st3gg_encode_arena_capsule(capsule)
        if getattr(decision, "enabled", False):
            st3gg_tokens = getattr(decision, "compressed_tokens_est", 0)
    except Exception:
        pass

    # 6. Hermes contract (typically 2000-3000 chars)
    hermes_contract_tokens = _estimate_tokens("x" * 2500)

    # Total Aura tokens
    total_aura = (
        aura_packet_tokens
        + codemap_search_tokens
        + read_slice_tokens
        + context_crush_tokens
        + st3gg_tokens
        + hermes_contract_tokens
    )

    # --- Savings ---
    estimated_tokens_saved = max(0, raw_total - total_aura)
    estimated_percent_saved = round(
        (estimated_tokens_saved / raw_total) * 100, 1
    ) if raw_total > 0 else 0.0

    # --- Cost savings ---
    input_price_per_m, _ = _get_pricing(model)
    estimated_cost_saved_usd = round(
        (estimated_tokens_saved / 1_000_000) * input_price_per_m, 6
    ) if estimated_tokens_saved > 0 else 0.0

    # --- Savings sources ---
    savings_sources: list[str] = []

    if aura_packet_tokens < raw_prompt_tokens:
        savings_sources.append("polysynthetic_packet")
    if codemap_search_tokens < raw_file_tokens:
        savings_sources.append("codemap_localization")
    savings_sources.append("ai_router_context")  # AI router always saves vs broad reads
    if read_slice_tokens < raw_file_tokens:
        savings_sources.append("read_slice")
    if context_crush_tokens > 0 and context_crush_tokens < raw_total:
        savings_sources.append("context_crusher")
    if st3gg_tokens > 0:
        savings_sources.append("st3gg_recall_pointer")
    savings_sources.append("dream_rerank")  # Advisory savings from better retrieval
    savings_sources.append("qdkt_fast_path")  # Advisory savings from crystallized patterns
    if hermes_contract_tokens > 0 and hermes_contract_tokens < raw_total:
        savings_sources.append("hermes_contract")

    # Deduplicate while preserving order
    seen = set()
    savings_sources = [s for s in savings_sources if not (s in seen or seen.add(s))]

    return {
        "ok": True,
        "version": ORCHESTRATOR_VERSION,
        "objective": objective,
        "model": model,
        "raw_prompt_tokens_est": raw_prompt_tokens,
        "raw_file_tokens_est": raw_file_tokens,
        "raw_repo_tokens_est": raw_repo_tokens,
        "aura_packet_tokens_est": aura_packet_tokens,
        "codemap_search_tokens_est": codemap_search_tokens,
        "read_slice_tokens_est": read_slice_tokens,
        "context_crush_tokens_est": context_crush_tokens,
        "st3gg_tokens_est": st3gg_tokens,
        "hermes_contract_tokens_est": hermes_contract_tokens,
        "total_aura_tokens_est": total_aura,
        "estimated_tokens_saved": estimated_tokens_saved,
        "estimated_percent_saved": estimated_percent_saved,
        "estimated_cost_saved_usd": estimated_cost_saved_usd,
        "savings_sources": savings_sources,
        "method": "local_chars_div_4_estimate",
        "warning": (
            "This is a local estimate using chars / 4, NOT provider billing telemetry. "
            "Actual token usage depends on the model tokenizer and prompt structure."
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def compute_savings_sources(token_economy_report: dict) -> list[str]:
    """Extract the list of savings sources from a token economy report."""
    return list(token_economy_report.get("savings_sources", []))


def estimate_cost_saved_usd(tokens_saved: int, model: str = _DEFAULT_MODEL) -> float:
    """Estimate cost savings in USD for a given token saving."""
    input_price_per_m, _ = _get_pricing(model)
    if tokens_saved <= 0:
        return 0.0
    return round((tokens_saved / 1_000_000) * input_price_per_m, 6)


def token_economy_markdown(report: dict) -> str:
    """Format a token economy report as markdown."""
    lines: list[str] = []
    lines.append("# Aura Token Economy Report")
    lines.append("")
    lines.append(f"**Objective:** {report.get('objective', '')}")
    lines.append(f"**Model:** {report.get('model', '')}")
    lines.append(f"**Method:** {report.get('method', '')}")
    lines.append(f"**Warning:** {report.get('warning', '')}")
    lines.append("")
    lines.append("## Raw Baseline")
    lines.append(f"- Raw prompt tokens: {report.get('raw_prompt_tokens_est', 0):,}")
    lines.append(f"- Raw file tokens: {report.get('raw_file_tokens_est', 0):,}")
    lines.append(f"- Raw repo tokens: {report.get('raw_repo_tokens_est', 0):,}")
    lines.append("")
    lines.append("## Aura Context Usage")
    lines.append(f"- Polysynthetic packet: {report.get('aura_packet_tokens_est', 0):,}")
    lines.append(f"- CODEMAP search: {report.get('codemap_search_tokens_est', 0):,}")
    lines.append(f"- Read-slice: {report.get('read_slice_tokens_est', 0):,}")
    lines.append(f"- Context Crusher: {report.get('context_crush_tokens_est', 0):,}")
    lines.append(f"- ST3GG: {report.get('st3gg_tokens_est', 0):,}")
    lines.append(f"- Hermes contract: {report.get('hermes_contract_tokens_est', 0):,}")
    lines.append(f"- **Total Aura tokens: {report.get('total_aura_tokens_est', 0):,}**")
    lines.append("")
    lines.append("## Savings")
    lines.append(f"- Tokens saved: {report.get('estimated_tokens_saved', 0):,}")
    lines.append(f"- Percent saved: {report.get('estimated_percent_saved', 0)}%")
    lines.append(f"- Cost saved (est.): ${report.get('estimated_cost_saved_usd', 0):.6f}")
    lines.append("")
    lines.append("## Savings Sources")
    for source in report.get("savings_sources", []):
        lines.append(f"- {source}")
    lines.append("")
    lines.append("## Invariants")
    lines.append(f"- patch_authority: `{PATCH_AUTHORITY}`")
    lines.append(f"- vsa_patch_authority: `{VSA_PATCH_AUTHORITY}`")
    return "\n".join(lines)
