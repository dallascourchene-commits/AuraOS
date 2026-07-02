"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c7-[Q-SYS:INGEST_BRIDGE]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Research Ingestion Bridge)
DEPENDENCIES: json, pathlib, typing, aura_research_manifest
FUNCTIONS: run_manifest_ingest_bridge
SYNOPSIS: Connects the Codex Research Manifest to Aura's arXiv forager, facilitating mass ingestion of
manifest-declared papers after validation constraints are verified.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_research_manifest import ingest_research_manifest


async def run_manifest_ingest_bridge(repo_root: str | Path, node_ref: Any = None) -> dict[str, Any]:
    """
    Validates and runs the manifest-driven ingestion process for the workspace.
    """
    root = Path(repo_root).resolve()
    manifest_path = root / ".aura" / "RESEARCH_MANIFEST.json"
    
    if not manifest_path.exists():
        return {
            "status": "error",
            "message": f"Manifest file not found: {manifest_path}"
        }
        
    print(f"[*] Resolving ingestion bridge for manifest: {manifest_path}")
    result = await ingest_research_manifest(manifest_path, node_ref=node_ref)
    return result
