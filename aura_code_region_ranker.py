"""
Aura Code Region Ranker — rank files/symbols/line ranges under a token budget.
Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
import json, re, time
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
RANKER_VERSION = "AURA_CODE_REGION_RANKER_V1"

_CODEMAP_CACHE: dict = {}
_CODEMAP_TTL = 120.0

def _load_codemap(repo_root: Path) -> dict:
    path = repo_root / ".aura" / "CODEMAP.json"
    key = str(path)
    now = time.time()
    if key in _CODEMAP_CACHE:
        ts, data = _CODEMAP_CACHE[key]
        if now - ts < _CODEMAP_TTL: return data
    try:
        with open(path, "r", encoding="utf-8") as f: data = json.load(f)
        _CODEMAP_CACHE[key] = (now, data); return data
    except Exception: return {}

_STOP = frozenset({"the","a","an","is","to","for","of","in","on","and","or","with","by","from","that","this","it","as","at","be"})
def _kw(text): return [w for w in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower()) if w not in _STOP and len(w)>1]


def rank_code_regions(objective: str, repo_root: str | Path = ".", max_regions: int = 20, max_lines: int = 400) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    cm = _load_codemap(root)
    keywords = _kw(objective)
    si = cm.get("symbol_index", {})
    files = cm.get("files", [])
    file_list = [str(f.get("path","")) for f in files if isinstance(f, dict)] if isinstance(files, list) else list(files.keys()) if isinstance(files, dict) else []

    file_scores = []
    for fp in file_list:
        if not fp or fp.endswith((".json",".bak",".txt",".pdf")): continue
        fp_l = fp.lower()
        score = sum(1.0 for k in keywords if k in fp_l)
        if fp.endswith(".py"): score += 0.3
        if score > 0: file_scores.append((score, fp))
    file_scores.sort(key=lambda x: x[0], reverse=True)

    sym_scores = []
    for sym_name in si:
        sl = sym_name.lower()
        score = sum(1.0 for k in keywords if k in sl)
        if score > 0: sym_scores.append((score, sym_name))
    sym_scores.sort(key=lambda x: x[0], reverse=True)

    ranked = []
    total_lines = 0
    total_tokens = 0
    for score, fp in file_scores[:max_regions]:
        if total_lines >= max_lines: break
        lines = min(120, max_lines - total_lines)
        tokens = lines * 10
        ranked.append({"file": fp, "score": round(score, 2), "lines": lines, "tokens": tokens, "reason": "keyword_match"})
        total_lines += lines
        total_tokens += tokens

    for score, sym in sym_scores[:max_regions]:
        if total_lines >= max_lines: break
        occ = si.get(sym, [])
        file_for_sym = occ[0].get("file", "") if occ and isinstance(occ[0], dict) else ""
        line_start = occ[0].get("line", 0) if occ and isinstance(occ[0], dict) else 0
        line_end = occ[0].get("end_line", 0) if occ and isinstance(occ[0], dict) else 0
        sym_lines = max(1, line_end - line_start + 1) if line_end > 0 and line_start > 0 else 10
        if total_lines + sym_lines > max_lines:
            continue
        sym_tokens = sym_lines * 10
        ranked.append({"symbol": sym, "file": file_for_sym, "score": round(score, 2),
                       "line_range": [line_start, line_end], "lines": sym_lines, "tokens": sym_tokens,
                       "reason": "symbol_match"})
        total_lines += sym_lines
        total_tokens += sym_tokens

    ranked = ranked[:max_regions]
    raw_context_tokens = sum(len(json.dumps(f)) // 4 for f in files[:50]) if isinstance(files, list) else 0
    efficiency = round(total_tokens / max(raw_context_tokens, 1) * 100, 1) if raw_context_tokens > 0 else 0.0

    return {
        "ok": True, "version": RANKER_VERSION, "objective": objective,
        "ranked_regions": ranked, "files": [r.get("file","") for r in ranked],
        "symbols": [r.get("symbol","") for r in ranked if r.get("symbol")],
        "line_ranges": [r.get("line_range") for r in ranked if r.get("line_range")],
        "tests": [], "reasons": [r.get("reason","") for r in ranked],
        "confidence": round(min(1.0, len(ranked) / max(1, max_regions)), 2),
        "coverage_estimate": round(len(ranked) / max(1, len(file_scores)) * 100, 1),
        "token_budget": max_lines * 10, "estimated_tokens": total_tokens,
        "raw_context_tokens_est": raw_context_tokens,
        "context_efficiency_ratio": efficiency,
        "localization_confidence": "high" if len(ranked) >= 5 else "medium" if len(ranked) >= 2 else "low",
        "needs_more_context": len(ranked) < 3,
        "excluded_regions": [], "exclusion_reasons": [],
        "exact_source_spans": [], "source_hashes": [],
        "top_k_files": len([r for r in ranked if r.get("file")]),
        "top_k_symbols": len([r for r in ranked if r.get("symbol")]),
        "total_lines_selected": total_lines, "total_tokens_est": total_tokens,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
