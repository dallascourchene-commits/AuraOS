"""In-process registry for compiled Arena grammars."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_arena_wfst_types import CompiledArenaGrammar, PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
ARENA_WFST_REGISTRY_VERSION="AURA_ARENA_WFST_REGISTRY_V2"
class ArenaGrammarRegistry:
    def __init__(self): self._grammars={}; self._meta={}
    def register(self,grammar:CompiledArenaGrammar): (self._meta if grammar.meta_grammar else self._grammars)[grammar.arena_id]=grammar
    def remove(self,arena_id:str,*,meta:bool=False): (self._meta if meta else self._grammars).pop(str(arena_id or ""),None)
    def get(self,arena_id): return self._grammars.get(str(arena_id or ""))
    def meta_grammars(self): return tuple(self._meta[k] for k in sorted(self._meta))
    def load_manifest(self,path,*,guard_ids=None,capability_exists=None):
        result=load_and_compile_arena_grammar(path,guard_ids=guard_ids,capability_exists=capability_exists)
        if result.ok and result.grammar:self.register(result.grammar)
        return result.to_dict()
    def load_directory(self,path,*,guard_ids=None,capability_exists=None):
        root=Path(path); reports=[self.load_manifest(p,guard_ids=guard_ids,capability_exists=capability_exists) for p in sorted(root.glob("*.json"))] if root.exists() else []
        return {"ok":bool(reports) and all(x.get("ok") for x in reports),"version":ARENA_WFST_REGISTRY_VERSION,"directory":str(root),"reports":reports,"registered_arenas":sorted(self._grammars),"registered_meta_grammars":sorted(self._meta),"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":VSA_PATCH_AUTHORITY}
    def status(self):
        return {"ok":True,"version":ARENA_WFST_REGISTRY_VERSION,"arenas":{k:{"arena_version":g.arena_version,"grammar_version":g.grammar_version,"manifest_digest":g.manifest_digest,"state_count":len(g.states),"transition_count":len(g.transitions)} for k,g in sorted(self._grammars.items())},"meta_grammars":sorted(self._meta),"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
