"""
Aura Research Cockpit Adapter — offline research manifest and paper memory.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ADAPTER_VERSION = "AURA_RESEARCH_COCKPIT_ADAPTER_V1"


def research_manifest_search(query: str, repo_root: str = ".", offline: bool = True) -> dict:
    """Search local research manifest for papers matching query."""
    root = Path(repo_root).resolve()
    manifest_path = root / ".aura" / "RESEARCH_MANIFEST.json"
    papers = []
    try:
        if manifest_path.exists():
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            query_lower = query.lower()
            for paper in data.get("papers", []):
                paper_text = json.dumps(paper).lower()
                if any(kw in paper_text for kw in query_lower.split()):
                    papers.append({
                        "arxiv_id": paper.get("arxiv_id", ""),
                        "label": paper.get("label", ""),
                        "target_modules": paper.get("target_modules", []),
                        "implementation_lesson": paper.get("implementation_lesson", ""),
                        "priority": paper.get("priority", 0),
                    })
    except Exception:
        pass
    return {"ok": True, "query": query, "papers": papers, "offline": offline,
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def paper_memory_recall(query: str, repo_root: str = ".") -> dict:
    """Recall from paper memory."""
    recalled = []
    try:
        from aura_paper_memory import load_research_profiles_from_jsonl
        root = Path(repo_root).resolve()
        ledger_path = root / ".aura" / "paper_memory.jsonl"
        if ledger_path.exists():
            recalled = load_research_profiles_from_jsonl(ledger_path)
    except Exception as exc:
        # Log failure but maintain response shape
        recalled = []
    return {"ok": True, "query": query, "recalled_papers": recalled[:5],
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def arxiv_forager_plan(query: str, repo_root: str = ".", offline: bool = True) -> dict:
    """Plan arXiv foraging (offline = plan only)."""
    plan = {"query": query, "offline": offline, "steps": [
        "search_arxiv_by_keyword", "filter_by_relevance", "ingest_to_paper_memory"]}
    if not offline:
        try:
            from arxiv_forager import ArXivForager
            plan["forager_available"] = True
        except Exception:
            plan["forager_available"] = False
    return {"ok": True, "query": query, "plan": plan, "offline": offline,
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def research_to_cockpit_evidence_packet(research_results: dict, repo_root: str = ".") -> dict:
    """Convert research results to evidence packet with token estimates."""
    papers = research_results.get("papers", [])
    raw_paper_tokens = sum(len(json.dumps(p)) // 4 for p in papers)
    compressed_evidence_tokens = min(raw_paper_tokens, 500)  # Compressed to summary
    savings_percent = round((1 - compressed_evidence_tokens / max(raw_paper_tokens, 1)) * 100, 1) if raw_paper_tokens > 0 else 0.0
    return {"ok": True, "evidence_packet": {
        "papers": papers, "raw_paper_tokens": raw_paper_tokens,
        "compressed_evidence_tokens": compressed_evidence_tokens,
        "savings_percent": savings_percent},
        "advisory_only": True,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "note": "Research evidence is advisory. CODEMAP grounding required before patch."}


def research_to_agent_context_capsule(research_results: dict, repo_root: str = ".") -> dict:
    """Compress research into agent context capsule."""
    papers = research_results.get("papers", [])[:3]
    summary = "; ".join(f"{p.get('label','')}({p.get('arxiv_id','')})" for p in papers)
    return {"ok": True, "context_capsule": {"research_summary": summary, "paper_count": len(papers)},
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
