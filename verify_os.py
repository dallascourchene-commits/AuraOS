"""
System audit — lists active core modules vs stray Python files in the workspace.

Run:
    python verify_os.py
"""
from __future__ import annotations

import os

# Files that ARE part of the active architecture
ACTIVE_CORE = {
    "aura_node.py",
    "async_palace.py",
    "aura_mesh.py",
    "quantum_dag.py",
    "aura.lexc",
    "logging_kit.py",
    "gateway.py",
    "aura_evolve.py",
    "systems_check.py",
    "pvm_arch_checker.py",
    "aura_topology_manager.py",
}

print("--- SYSTEM AUDIT ---")
for file in sorted(os.listdir(".")):
    if file.endswith(".py"):
        if file in ACTIVE_CORE:
            print(f"[ACTIVE] {file}")
        else:
            print(f"[FOSSIL/STRAY?] {file} - Consider archiving or deleting.")
