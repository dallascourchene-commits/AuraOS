"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c1-[Q-SYS:RESEARCH_MANIFEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Research Grounding)
DEPENDENCIES: json, pathlib, typing, arxiv_forager
FUNCTIONS: ResearchPaperEntry, ResearchManifest, load_research_manifest, ingest_research_manifest
SYNOPSIS: Interface for loading research manifests and programmatically mass-ingesting
arxiv IDs into Aura's SQLite engram database (traces table) and ScientificMemoryIndex.
Ensures that paper ingestion is grounded by target modules, implementation lessons, and
acceptance criteria.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from arxiv_forager import ArXivForager, EnhancedArxivForager


@dataclass
class ResearchPaperEntry:
    arxiv_id: str
    label: str
    target_modules: list[str]
    implementation_lesson: str
    acceptance_test: str
    future_ingest: bool = True
    priority: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "arxiv_id": self.arxiv_id,
            "label": self.label,
            "target_modules": self.target_modules,
            "implementation_lesson": self.implementation_lesson,
            "acceptance_test": self.acceptance_test,
            "future_ingest": self.future_ingest,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ResearchPaperEntry:
        return cls(
            arxiv_id=str(d.get("arxiv_id", "")),
            label=str(d.get("label", "")),
            target_modules=list(d.get("target_modules", [])),
            implementation_lesson=str(d.get("implementation_lesson", "")),
            acceptance_test=str(d.get("acceptance_test", "")),
            future_ingest=bool(d.get("future_ingest", True)),
            priority=int(d.get("priority", 1)),
        )


@dataclass
class ResearchManifest:
    manifest_version: str
    created_for: str
    papers: list[ResearchPaperEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "created_for": self.created_for,
            "papers": [p.to_dict() for p in self.papers],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ResearchManifest:
        papers_list = [ResearchPaperEntry.from_dict(p) for p in d.get("papers", [])]
        return cls(
            manifest_version=str(d.get("manifest_version", "1.0")),
            created_for=str(d.get("created_for", "")),
            papers=papers_list,
        )


def load_research_manifest(manifest_path: str | Path) -> ResearchManifest | None:
    """Load and parse the research manifest file."""
    path = Path(manifest_path)
    if not path.exists():
        print(f"[-] Research manifest path does not exist: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ResearchManifest.from_dict(data)
    except Exception as exc:
        print(f"[-] Failed to load research manifest: {exc}")
        return None


async def ingest_research_manifest(
    manifest_path: str | Path,
    *,
    node_ref: Any = None,
    download: bool = True,
    parse_pdf: bool = True,
    summarize: bool = True,
    write_memory: bool = True,
    update_codemap: bool = False,
) -> dict[str, Any]:
    """
    Ingest papers declared in the research manifest that have future_ingest=True.
    
    Downloads, parses, and vectorizes their metadata into the sqlite database.
    """
    manifest = load_research_manifest(manifest_path)
    if not manifest:
        return {
            "status": "error",
            "message": "Failed to load manifest or manifest empty",
            "count": 0,
            "ingested": [],
            "failed": []
        }

    # Extract eligible arXiv IDs
    arxiv_ids = []
    for paper in manifest.papers:
        if paper.future_ingest and paper.arxiv_id:
            arxiv_ids.append(paper.arxiv_id)

    if not arxiv_ids:
        return {
            "status": "success",
            "message": "No papers marked for ingestion in manifest",
            "count": 0,
            "ingested": [],
            "failed": []
        }

    print(f"[*] Ingesting {len(arxiv_ids)} papers from manifest: {', '.join(arxiv_ids)}...")
    
    # Initialize the ArXivForager or EnhancedArxivForager with node_ref
    forager = ArXivForager(node_ref)
    
    # Run the mass ingestion
    result = await forager.ingest_arxiv_ids(arxiv_ids)
    
    return result
