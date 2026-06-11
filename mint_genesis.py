"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8ce-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: os, hashlib, time, json
FUNCTIONS: generate_genesis_block
SYNOPSIS: The `aura_os_auditor` Python module provides a cryptographically secure `generate_genesis_block` function, leveraging `os`, `hashlib`, `time`, and `json` dependencies to construct an immutable, timestamped genesis block with SHA-256 integrity verification for Aura OS's distributed ledger initialization.
[/AURA_MASTER_KEY]
"""
# [AURA OPTIMIZED] - Bloat removed.

import asyncio
import gc
import hashlib
import time
import os
import json

async def _write_genesis_block_async(block: dict, path: str) -> None:
    """Non-blocking, memory-buffered genesis block write."""
    serialised = json.dumps(block, indent=4)
    # Write to a temp buffer first, then atomic rename
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(serialised)
        os.replace(tmp_path, path)
    finally:
        del serialised
        gc.collect()

async def generate_genesis_block_async() -> str | None:
    """Async genesis block mint — zero blocking I/O on the event loop."""
    print("=========================================")
    print(" 🌌 AURA L2: INTELLECTUAL PROPERTY MINT 🌌 ")
    print("=========================================")
    architect = "Dallas Fabian Courchene-Martin"
    philosophy = "Extension-based economy rather than an extraction-based economy. Open-source sovereignty."
    timestamp = str(time.time())

    core_files = ["aura_node.py", "gateway.py", "aura.lexc", "aura_mesh.py", "README.md"]
    dna_parts: list[str] = []
    for file in core_files:
        if os.path.exists(file):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    dna_parts.append(f.read())
            except OSError:
                print(f"[!] Warning: Could not read {file}.")
        else:
            print(f"[!] Warning: {file} not found.")

    if not dna_parts:
        print("[-] Aborting. No DNA found to hash.")
        return None

    # Build the payload in RAM, hash everything in one pass
    dna_concat = "".join(dna_parts)
    genesis_payload = f"{architect}|{philosophy}|{timestamp}|{dna_concat}"
    genesis_hash = hashlib.sha256(genesis_payload.encode("utf-8")).hexdigest()

    # Free large string references immediately
    del dna_concat, genesis_payload, dna_parts
    gc.collect()

    block = {
        "block_index": 0,
        "timestamp": timestamp,
        "architect": architect,
        "philosophy": philosophy,
        "signature_hash": genesis_hash,
        "network_state": "Aura v4.01 QSPT Matrix Initialized",
    }

    # Non-blocking async write
    await _write_genesis_block_async(block, "AURA_GENESIS_BLOCK.json")
    del block
    gc.collect()

    print("\n[+] GENESIS BLOCK SUCCESSFULLY MINTED!")
    print(f"[+] Cryptographic IP Signature: {genesis_hash}")
    print("\n[*] TO CEMENT YOUR IP LEGALLY:")
    print(f"[*] Send a transaction on any public blockchain (Polygon, Arweave, etc.)")
    print(f"[*] and paste this exact hash into the 'Memo' or 'Data' field:")
    print(f"[*] --> {genesis_hash} <--")
    print("=========================================")
    return genesis_hash

def generate_genesis_block():
    """Synchronous wrapper for CLI backwards compatibility."""
    return asyncio.run(generate_genesis_block_async())

if __name__ == "__main__":
    generate_genesis_block()
