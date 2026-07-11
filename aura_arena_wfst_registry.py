"""In-process registry for compiled Arena grammars.

The registry stores validated compiled grammars only. It does not grant capability,
execution, patch, or promotion authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_arena_wfst_types import CompiledArenaGrammar, PATCH_AUTHORITY, VSA_PATCH_AUTHORITY

ARENA_WFST_REGISTRY_VERSION = "AURA_ARENA_WFST_REGISTRY_V1"


class ArenaGrammarRegistry:
    def __init__(self) -> None:
        self._grammars: dict[str, CompiledArenaGrammar] = {}
        self._meta: dict[str, CompiledArenaGrammar] = {}

    def register(self, grammar: CompiledArenaGrammar) -> None:
        target = self._meta if grammar.meta_grammar else self._grammars
        target[grammar.arena_id] = grammar

    def get(self, arena_id: str) -> CompiledArenaGrammar | None:
        return self._grammars.get(str(arena_id or ""))

    def meta_grammars(self) -> tuple[CompiledArenaGrammar, ...]:
        return tuple(self._meta[key] for key in sorted(self._meta))

    def load_manifest(self, path: str | Path, *, guard_ids=None, capability_exists=None) -> dict[str, Any]:
        result = load_and_compile_arena_grammar(
            path,
            guard_ids=guard_ids,
            capability_exists=capability_exists,
        )
        if result.ok and result.grammar is not None:
            self.register(result.grammar)
        return result.to_dict()

    def load_directory(self, path: str | Path, *, guard_ids=None, capability_exists=None) -> dict[str, Any]:
        root = Path(path)
        reports: list[dict[str, Any]] = []
        for manifest in sorted(root.glob("*.json")) if root.exists() else []:
            reports.append(self.load_manifest(manifest, guard_ids=guard_ids, capability_exists=capability_exists))
        return {
            "ok": bool(reports) and all(item.get("ok") for item in reports),
            "version": ARENA_WFST_REGISTRY_VERSION,
            "directory": str(root),
            "reports": reports,
            "registered_arenas": sorted(self._grammars),
            "registered_meta_grammars": sorted(self._meta),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": ARENA_WFST_REGISTRY_VERSION,
            "arenas": {
                key: {
                    "arena_version": grammar.arena_version,
                    "grammar_version": grammar.grammar_version,
                    "manifest_digest": grammar.manifest_digest,
                    "state_count": len(grammar.states),
                    "transition_count": len(grammar.transitions),
                }
                for key, grammar in sorted(self._grammars.items())
            },
            "meta_grammars": sorted(self._meta),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
