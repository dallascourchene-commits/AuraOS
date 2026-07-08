"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xaa41-[Q-SYS:ARENA_ST3GG_EGRESS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Compact Advisory Recall Handles)
DEPENDENCIES: __future__, hashlib, re, typing
FUNCTIONS: compress_report_st3gg, decompress_report_st3gg, st3gg_pointer_for, estimate_savings_ratio
SYNOPSIS: ST3GG Coding Arena egress path — produces compact visible-ASCII capsules as advisory
recall handles for emergent report output. Capsules are NOT patch authority. Exact source spans,
hashes, tests, and verifier gates remain the only patch authority.
SAFETY: NO_PATCHES | NO_CODE_WRITES | NO_UNIFIED_DIFF | REPORT_ONLY
Compact output must be ASCII-visible only (0x20-0x7E). Savings threshold required (default 20%).
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

EGRESS_VERSION = "AURA_ARENA_ST3GG_EGRESS_V1"
PATCH_AUTHORITY_POLICY = "exact_source_spans_and_hashes_only"
# Visible-ASCII range — no control characters
_ASCII_RE = re.compile(r"[^\x20-\x7e]")

# Symbol table: common Aura report words → short codes (all visible ASCII)
_SYMBOL_TABLE: dict[str, str] = {
    "Emergent Properties and Future Potential": "E|PFP",
    "Verified High-Leverage Clusters": "VHC",
    "FUTURE_PATCHABLE": "FP",
    "NEEDS_GROUNDING": "NG",
    "TOO_RISKY": "TR",
    "READY_TO_TEST": "RT",
    "DREAM_ONLY": "DO",
    "source_hash": "sh",
    "source_span": "sp",
    "missing_wire": "mw",
    "emergent_ability": "ea",
    "required_tests": "rt",
    "verifier_notes": "vn",
    "suppressed_duplicate": "sd",
    "safe_to_patch": "stp",
    "NO_PATCHES": "NP",
    "NO_CODE_WRITES": "NCW",
    "NO_UNIFIED_DIFF": "NUD",
    "NO_AUTOWIRING": "NAW",
    "REPORT_ONLY": "RO",
    "patch_authority": "pa",
    "exact_source_spans_and_hashes_only": "ESSHO",
    "J-Space advisory": "JSA",
    "ST3GG egress": "SE",
    "Trace atom": "TA",
    "Best wire": "BW",
    "Missing wire": "MW",
    "Why it matters": "WIM",
    "Alternates": "ALT",
    "Evidence": "EV",
    "Status": "ST",
    "Score": "SC",
}

# Reverse table for decompression
_REVERSE_TABLE: dict[str, str] = {v: k for k, v in _SYMBOL_TABLE.items()}


def _safe_ascii(text: str) -> str:
    """Replace non-visible-ASCII characters with '?' to keep egress safe."""
    return _ASCII_RE.sub("?", text)


def _pointer_for(compressed: str) -> str:
    """Stable visible-ASCII pointer hash for the compressed blob."""
    digest = hashlib.sha256(compressed.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"ST3GG_PTR:{digest}"


def estimate_savings_ratio(original: str, compressed: str) -> float:
    """Return the fractional byte reduction achieved by compression."""
    orig_len = len(original.encode("utf-8", errors="replace"))
    comp_len = len(compressed.encode("utf-8", errors="replace"))
    if orig_len == 0:
        return 0.0
    return max(0.0, (orig_len - comp_len) / orig_len)


def compress_report_st3gg(report_text: str) -> tuple[str, float, str]:
    """
    Compress a verified emergent report to a compact visible-ASCII capsule.

    Returns ``(compressed_text, savings_ratio, recall_pointer)``.

    Rules:
    - Visible ASCII only (0x20-0x7E).
    - Multi-space → single space; blank lines collapsed.
    - Symbol table substitution for common long strings.
    - Returns original when savings < 0 (never inflates).
    - Recall pointer is a short SHA hash for round-trip lookup.
    - Compact output is advisory ONLY — exact source spans from original are authoritative.
    """
    if not report_text:
        return "", 0.0, ""

    compressed = report_text
    # Apply symbol table
    for long_form, short_form in sorted(_SYMBOL_TABLE.items(), key=lambda kv: -len(kv[0])):
        compressed = compressed.replace(long_form, short_form)

    # Collapse multiple spaces (but preserve newlines)
    compressed = re.sub(r"[ \t]{2,}", " ", compressed)
    # Collapse 3+ blank lines to 2
    compressed = re.sub(r"\n{3,}", "\n\n", compressed)
    # Strip trailing whitespace per line
    compressed = "\n".join(line.rstrip() for line in compressed.splitlines())

    # Ensure visible-ASCII only
    compressed = _safe_ascii(compressed)

    savings = estimate_savings_ratio(report_text, compressed)
    # Return original when savings < 0 (never inflate)
    if savings < 0.0:
        pointer = _pointer_for(report_text)
        return report_text, 0.0, pointer
    pointer = _pointer_for(compressed)
    return compressed, savings, pointer


def decompress_report_st3gg(compressed: str) -> str:
    """
    Reverse the symbol-table substitution to recover human-readable text.

    Note: whitespace normalisation is lossy — exact original not guaranteed.
    Source evidence (spans, hashes) must be re-fetched from the original report
    or from the topology anchor; do NOT rely on decompressed text as patch authority.
    """
    if not compressed:
        return ""
    text = compressed
    # Apply in reverse (longer replacements first to avoid partial matches)
    for short_form, long_form in sorted(_REVERSE_TABLE.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(re.escape(short_form), long_form, text)
    return text


def st3gg_pointer_for(report_text: str) -> str:
    """
    Return a stable ST3GG recall pointer for the given report text.

    Pointer is a deterministic hash — no compression side effect.
    """
    digest = hashlib.sha256(report_text.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"ST3GG_PTR:{digest}"
