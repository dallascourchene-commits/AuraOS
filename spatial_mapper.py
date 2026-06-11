"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8c5-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy)
DEPENDENCIES: ast, asyncio, websockets, os, numpy, hashlib, json
FUNCTIONS: _rel_module_path, scan_and_vectorize, aura_tmm_server, main, __new__, get_cached_walk, invalidate, __init__, compute_cortical_rf_alignment, visit_FunctionDef, visit_AsyncFunctionDef, _record_callable, visit_ClassDef
SYNOPSIS: The Python module integrates AST parsing, asynchronous networking, filesystem operations, numerical computation, cryptographic hashing, and JSON serialization via `ast`, `asyncio`, `websockets`, `os`, `numpy`, `hashlib`, and `json`, exposing functions for module path resolution (`_rel_module_path`), filesystem scanning and vectorization (`scan_and_vectorize`), WebSocket server initialization (`aura_tmm_server`), CLI entry (`main`), singleton instantiation (`__new__`), filesystem traversal caching (`get_cached_walk`, `invalidate`), class and function AST analysis (`visit_FunctionDef`, `visit_AsyncFunctionDef`, `_record_callable`, `visit_ClassDef`), cortical alignment computation (`compute_cortical_rf_alignment`), and constructor logic (`__init__`).
[/AURA_MASTER_KEY]
"""
import asyncio
import ast
import hashlib
import json
import os

import numpy as np  # Ensure environment is using numpy==1.26.4 across the stack

try:
    import websockets
except ImportError:
    websockets = None  # type: ignore[assignment,misc]

class DirectoryCache:
    """
    Singleton cache to share walked directory results between the 
    topological scanner and the spatial mapper, eliminating redundant disk I/O.
    """
    _instance = None
    _cache = {}
    _ignored_dirs = {".git", ".cargo", "llama.cpp", "Aura_Memory", "Aura_Staging", "venv", "__pycache__", "aura_exports"}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_cached_walk(cls, path: str) -> list:
        key = os.path.abspath(path)
        if key not in cls._cache:
            file_paths = []
            # Only scan flat, immediate files in the project folder to prevent home directory recursion
            for file in os.listdir(key):
                if file.endswith('.py'):
                    file_paths.append(os.path.join(key, file))
            cls._cache[key] = file_paths
        return cls._cache[key]

    @classmethod
    def invalidate(cls):
        cls._cache.clear()


class CodeTopologyMapper(ast.NodeVisitor):
    def __init__(self, filepath, base_x, base_y, phase_resonance_pool=None):
        self.filepath = filepath
        self.nodes = []
        self.base_x = base_x
        self.base_y = base_y
        self.z_offset = 0
        # Incorporate her 60-80 Hz cortical simulation arrays
        self.rf_frequency_pool = phase_resonance_pool if phase_resonance_pool is not None else []

    def compute_cortical_rf_alignment(self, node_name: str) -> list:
        """
        Maps a structural component to a localized phase coordinate overlay,
        mimicking direct cortical field alignment profiles.
        """
        # Generate an ultra-fast, type-safe phase coordinate mapping
        name_hash = int(hashlib.md5(node_name.encode()).hexdigest(), 16)
        coord_x = self.base_x + (name_hash % 15)
        coord_y = self.base_y + ((name_hash >> 4) % 15)
        coord_z = self.z_offset + ((name_hash >> 8) % 30)
        return [int(coord_x), int(coord_y), int(coord_z)]

    def visit_FunctionDef(self, node):
        self._record_callable(node.name, node.lineno, "function", z_step=10)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._record_callable(node.name, node.lineno, "async_function", z_step=10)
        self.generic_visit(node)

    def _record_callable(self, name: str, lineno: int, node_type: str, z_step: int) -> None:
        vector_z = self.z_offset + z_step
        self.nodes.append({
            "type": node_type,
            "name": name,
            "file": self.filepath,
            "vector": [self.base_x, self.base_y, vector_z],
            "line": lineno,
        })
        self.z_offset += z_step

    def visit_ClassDef(self, node):
        vector_z = self.z_offset + 20
        self.nodes.append({
            "type": "class",
            "name": node.name,
            "file": self.filepath,
            "vector": [self.base_x + 5, self.base_y, vector_z],
            "line": node.lineno
        })
        self.z_offset += 20
        self.generic_visit(node)

def _rel_module_path(filepath: str) -> str:
    """Stable module key for topology (basename only — avoids Termux absolute-path drift)."""
    return os.path.basename(filepath)


def scan_and_vectorize(directory):
    topology = []
    # Only scan flat, immediate files in the project folder to prevent home directory recursion
    for file in os.listdir(directory):
        if file.endswith('.py'):
            filepath = os.path.join(directory, file)
            rel_file = _rel_module_path(filepath)
            
            # Generate stable geometric coordinates based on file path
            base_x = int(hashlib.md5(directory.encode()).hexdigest(), 16) % 100
            base_y = int(hashlib.md5(file.encode()).hexdigest(), 16) % 100
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                    mapper = CodeTopologyMapper(rel_file, base_x, base_y)
                    mapper.visit(tree)
                    topology.extend(mapper.nodes)
            except Exception as e:
                pass # Bypass non-parseable files to maintain matrix stability
    return topology

# Aura's Step 4 & 5: WebSocket and Interaction Layer
async def aura_tmm_server(websocket):
    print(f"[AURA-TMM] VR/AR Client Connected. Broadcasting Topological Map...")
    current_dir = os.getcwd()
    
    # Generate the 3D map
    code_topology = scan_and_vectorize(current_dir)
    
    # Broadcast the map to the interface
    await websocket.send(json.dumps({"action": "init_map", "data": code_topology}))
    
    # Interaction Layer (Node-Manipulation API)
    async for message in websocket:
        request = json.loads(message)
        if request.get("action") == "update_node":
            node_name = request["name"]
            new_vector = request["vector"]
            print(f"[AURA-TMM] Sovereign Override: Re-vectorizing node '{node_name}' to {new_vector}")
            # The feedback loop: future logic to rewrite the physical source file goes here

async def main():
    if websockets is None:
        raise ImportError("websockets is required for TMM server mode (pip install websockets)")

    print("[*] Aura Topological Mapping Module (TMM) Online.")
    print("[*] Broadcasting 3D Codebase Vector-Space on ws://0.0.0.0:8000")
    async with websockets.serve(aura_tmm_server, "0.0.0.0", 8000):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
