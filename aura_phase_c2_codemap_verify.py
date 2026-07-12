"""Explicit CODEMAP verification for Phase C2 live route-capsule topology."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aura_codemap_verify import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, verify_codemap

PHASE_C2_CODEMAP_VERIFY_VERSION = "AURA_PHASE_C2_CODEMAP_VERIFY_V1"

C2_REQUIRED_PATHS = frozenset({
    "aura_route_capsule_materializer.py",
    "aura_runtime_intent_packet.py",
    "aura_route_capsule_live_runtime.py",
    "aura_coding_workbench_capsule_adapter.py",
    "aura_arena_experience.py",
    "aura_arena_experience_ledger.py",
    "aura_phase_c2_codemap_verify.py",
    "tests/test_aura_arena_experience_ledger.py",
    "tests/test_aura_phase_c2_live_route_capsules.py",
    "tests/test_aura_phase_c2_capsule_enforcement.py",
})
C2_REQUIRED_SYMBOLS = frozenset({
    "MaterializedRouteCapsule",
    "materialize_route_capsule",
    "infer_runtime_intent_packet",
    "CapsuleAwareArenaWFSTRuntime",
    "CapsuleCodingWorkbenchWFSTSession",
    "verify_phase_c2_codemap",
})


def verify_phase_c2_codemap(repo_root: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_root).resolve()
    base = verify_codemap(root)
    errors = list(base.get("errors") or [])
    try:
        payload = json.loads((root / ".aura" / "CODEMAP.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "version": PHASE_C2_CODEMAP_VERIFY_VERSION,
            "errors": [*errors, f"c2_codemap_unreadable:{type(exc).__name__}"],
            "missing_paths": sorted(C2_REQUIRED_PATHS),
            "missing_symbols": sorted(C2_REQUIRED_SYMBOLS),
            "base": base,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    file_cards = payload.get("files") or []
    indexed_paths = {
        str(card.get("path") or "")
        for card in file_cards
        if isinstance(card, dict)
    }
    symbol_index = payload.get("symbol_index") or {}
    indexed_symbols = set(symbol_index) if isinstance(symbol_index, dict) else set()
    missing_paths = sorted(C2_REQUIRED_PATHS - indexed_paths)
    missing_symbols = sorted(C2_REQUIRED_SYMBOLS - indexed_symbols)
    if missing_paths:
        errors.append("c2_required_paths_missing")
    if missing_symbols:
        errors.append("c2_required_symbols_missing")
    return {
        "ok": bool(base.get("ok")) and not errors,
        "version": PHASE_C2_CODEMAP_VERIFY_VERSION,
        "errors": errors,
        "missing_paths": missing_paths,
        "missing_symbols": missing_symbols,
        "summary": dict(base.get("summary") or {}),
        "base": base,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Phase C2 CODEMAP topology")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    result = verify_phase_c2_codemap(args.repo_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
