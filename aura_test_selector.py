"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9c5-[Q-SYS:TEST_SELECTOR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Regression Test Selection / Optimization)
DEPENDENCIES: json, pathlib, typing
FUNCTIONS: select_relevant_tests, get_test_mapping
SYNOPSIS: Selects the smallest relevant subset of unit/regression tests associated with
the modified files, saving model context tokens and execution time.
Research basis: TestPrune (2510.18270).
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set


def get_test_mapping(repo_root: str | Path) -> dict[str, list[str]]:
    """
    Scrapes the CODEMAP to build a mapping from source file paths to test file paths.
    """
    root = Path(repo_root).resolve()
    mapping: dict[str, list[str]] = {}
    
    codemap_path = root / ".aura" / "CODEMAP.json"
    if not codemap_path.exists():
        return mapping
        
    try:
        codemap = json.loads(codemap_path.read_text(encoding="utf-8"))
        if "files" in codemap:
            for item in codemap["files"]:
                path = item.get("path", "")
                if not path:
                    continue
                
                # Check neighbors/topology to find test references
                tests = []
                # If the file path matches "test_*.py" it is a test file itself
                if path.startswith("test_") or "/test_" in path:
                    continue
                    
                # Look for matching test file in same directory
                parts = Path(path).parts
                test_name = f"test_{parts[-1]}"
                potential_test = Path(*parts[:-1]) / test_name
                if (root / potential_test).exists():
                    tests.append(potential_test.as_posix())
                    
                # Look in codemap's topology for neighbors that look like tests
                topology = item.get("topology", {})
                if isinstance(topology, dict):
                    neighbors = topology.get("neighbor_files", []) or []
                    for nb in neighbors:
                        if "test_" in nb or nb.startswith("test_"):
                            tests.append(nb)
                            
                if tests:
                    mapping[path] = list(set(tests))
    except Exception:
        pass
        
    return mapping


def select_relevant_tests(modified_files: list[str], repo_root: str | Path, limit: int = 3) -> list[str]:
    """
    Choose the smallest and most relevant subset of unit tests for the modified files.
    """
    mapping = get_test_mapping(repo_root)
    selected: set[str] = set()
    
    for file in modified_files:
        tests = mapping.get(file, [])
        for t in tests:
            selected.add(t)
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break
            
    # Fallback to general/core tests if none found
    if not selected:
        root = Path(repo_root).resolve()
        core_tests = ["test_aura_functions.py", "test_aura_integration.py"]
        for ct in core_tests:
            if (root / ct).exists():
                selected.add(ct)
                
    return sorted(list(selected))
